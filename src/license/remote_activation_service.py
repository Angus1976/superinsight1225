"""
Remote Activation Service for SuperInsight Platform.

Handles online and offline license activation.
"""

import base64
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.license import (
    LicenseModel, LicenseActivationModel, LicenseStatus,
    ActivationType, ActivationStatus
)
from src.schemas.license import (
    ActivationResult, OfflineActivationResponse, LicenseResponse, LicenseLimits
)
from src.license.hardware_fingerprint import HardwareFingerprint


class RemoteActivationService:
    """
    Remote Activation Service.
    
    Handles online and offline license activation workflows.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        license_server_url: Optional[str] = None,
        api_key: Optional[str] = None,
        signing_key: str = "default_signing_key"
    ):
        """
        Initialize Remote Activation Service.
        
        Args:
            db: Database session
            license_server_url: URL of license server (for online activation)
            api_key: API key for license server
            signing_key: Key for signing offline requests
        """
        self.db = db
        self.license_server_url = license_server_url
        self.api_key = api_key
        self.signing_key = signing_key
        self.fingerprint_generator = HardwareFingerprint()
    
    def get_hardware_fingerprint(self) -> str:
        """Get current hardware fingerprint."""
        return self.fingerprint_generator.generate_fingerprint()
    
    async def activate_online(
        self,
        license_key: str,
        hardware_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ActivationResult:
        """
        Activate license online.
        
        Args:
            license_key: License key to activate
            hardware_fingerprint: Hardware fingerprint (auto-generated if not provided)
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Activation result
        """
        # Get hardware fingerprint
        if not hardware_fingerprint:
            hardware_fingerprint = self.get_hardware_fingerprint()
        
        # Find license in local database
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.license_key == license_key)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            # If license server is configured, try remote activation
            if self.license_server_url:
                return await self._activate_from_server(
                    license_key, hardware_fingerprint, ip_address, user_agent
                )
            
            return ActivationResult(
                success=False,
                error="License not found"
            )
        
        # Check if already activated
        if license_model.status == LicenseStatus.ACTIVE:
            if license_model.hardware_id and license_model.hardware_id != hardware_fingerprint:
                return ActivationResult(
                    success=False,
                    error="License is bound to different hardware"
                )
            
            return ActivationResult(
                success=True,
                license=self._to_response(license_model),
                error="License already activated"
            )
        
        # Check if revoked
        if license_model.status == LicenseStatus.REVOKED:
            return ActivationResult(
                success=False,
                error="License has been revoked"
            )
        
        # Check validity
        now = datetime.now(timezone.utc)
        if now < license_model.validity_start:
            return ActivationResult(
                success=False,
                error="License validity period has not started"
            )
        
        if now > license_model.validity_end:
            return ActivationResult(
                success=False,
                error="License has expired"
            )
        
        # Activate
        license_model.status = LicenseStatus.ACTIVE
        license_model.activated_at = now
        license_model.hardware_id = hardware_fingerprint
        
        # Update signature
        license_model.signature = self._generate_signature(license_model)
        
        # Create activation record
        activation = LicenseActivationModel(
            id=uuid4(),
            license_id=license_model.id,
            hardware_fingerprint=hardware_fingerprint,
            activation_type=ActivationType.ONLINE,
            status=ActivationStatus.ACTIVE,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self.db.add(activation)
        await self.db.commit()
        await self.db.refresh(license_model)
        
        return ActivationResult(
            success=True,
            license=self._to_response(license_model),
            activation_id=activation.id
        )
    
    async def _activate_from_server(
        self,
        license_key: str,
        hardware_fingerprint: str,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> ActivationResult:
        """Activate license from remote server."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.license_server_url}/api/v1/activate",
                    json={
                        "license_key": license_key,
                        "hardware_fingerprint": hardware_fingerprint,
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "X-Forwarded-For": ip_address or "",
                        "User-Agent": user_agent or "",
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Store license locally
                    # ... (would create local license record)
                    return ActivationResult(
                        success=True,
                        activation_id=UUID(data.get("activation_id"))
                    )
                else:
                    return ActivationResult(
                        success=False,
                        error=response.json().get("error", "Activation failed")
                    )
        except Exception as e:
            return ActivationResult(
                success=False,
                error=f"Failed to connect to license server: {str(e)}"
            )
    
    def generate_offline_request(
        self,
        license_key: str,
        hardware_fingerprint: Optional[str] = None
    ) -> OfflineActivationResponse:
        """
        Generate offline activation request.
        
        Args:
            license_key: License key
            hardware_fingerprint: Hardware fingerprint (auto-generated if not provided)
            
        Returns:
            Offline activation request data
        """
        if not hardware_fingerprint:
            hardware_fingerprint = self.get_hardware_fingerprint()
        
        # Create request data
        request_data = {
            "license_key": license_key,
            "hardware_fingerprint": hardware_fingerprint,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Sign the request
        data_str = json.dumps(request_data, sort_keys=True)
        signature = hashlib.sha256(
            f"{data_str}|{self.signing_key}".encode()
        ).hexdigest()
        
        request_data["signature"] = signature
        
        # Encode as base64
        request_code = base64.b64encode(
            json.dumps(request_data).encode()
        ).decode()
        
        return OfflineActivationResponse(
            request_code=request_code,
            hardware_fingerprint=hardware_fingerprint,
            license_key=license_key,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
    
    async def activate_offline(
        self,
        activation_code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ActivationResult:
        """
        Complete offline activation with activation code.
        
        Args:
            activation_code: Activation code from license server
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Activation result
        """
        try:
            # Decode activation code
            decoded = base64.b64decode(activation_code.encode())
            activation_data = json.loads(decoded.decode())
        except Exception:
            return ActivationResult(
                success=False,
                error="Invalid activation code format"
            )
        
        # Verify signature
        signature = activation_data.pop("signature", None)
        if not signature:
            return ActivationResult(
                success=False,
                error="Missing signature in activation code"
            )
        
        data_str = json.dumps(activation_data, sort_keys=True)
        expected_signature = hashlib.sha256(
            f"{data_str}|{self.signing_key}".encode()
        ).hexdigest()
        
        if signature != expected_signature:
            return ActivationResult(
                success=False,
                error="Invalid activation code signature"
            )
        
        # Check expiration
        expires_at = datetime.fromisoformat(activation_data.get("expires_at", ""))
        if datetime.now(timezone.utc) > expires_at:
            return ActivationResult(
                success=False,
                error="Activation code has expired"
            )
        
        # Verify hardware fingerprint
        expected_fingerprint = activation_data.get("hardware_fingerprint")
        current_fingerprint = self.get_hardware_fingerprint()
        
        if expected_fingerprint != current_fingerprint:
            return ActivationResult(
                success=False,
                error="Hardware fingerprint mismatch"
            )
        
        # Find and activate license
        license_key = activation_data.get("license_key")
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.license_key == license_key)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return ActivationResult(
                success=False,
                error="License not found"
            )
        
        # Activate
        now = datetime.now(timezone.utc)
        license_model.status = LicenseStatus.ACTIVE
        license_model.activated_at = now
        license_model.hardware_id = current_fingerprint
        license_model.signature = self._generate_signature(license_model)
        
        # Create activation record
        activation = LicenseActivationModel(
            id=uuid4(),
            license_id=license_model.id,
            hardware_fingerprint=current_fingerprint,
            activation_type=ActivationType.OFFLINE,
            activation_code=activation_code[:100],  # Store truncated
            status=ActivationStatus.ACTIVE,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self.db.add(activation)
        await self.db.commit()
        await self.db.refresh(license_model)
        
        return ActivationResult(
            success=True,
            license=self._to_response(license_model),
            activation_id=activation.id
        )
    
    async def verify_activation_status(
        self,
        license_id: UUID
    ) -> Dict[str, Any]:
        """
        Verify activation status (periodic check).
        
        Args:
            license_id: License ID to verify
            
        Returns:
            Verification result
        """
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.id == license_id)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return {"valid": False, "reason": "License not found"}
        
        # Check status
        if license_model.status != LicenseStatus.ACTIVE:
            return {"valid": False, "reason": f"License status: {license_model.status.value}"}
        
        # Check hardware binding
        if license_model.hardware_id:
            current_fingerprint = self.get_hardware_fingerprint()
            if license_model.hardware_id != current_fingerprint:
                return {"valid": False, "reason": "Hardware mismatch"}
        
        # Check validity period
        now = datetime.now(timezone.utc)
        if now > license_model.validity_end:
            return {"valid": False, "reason": "License expired"}
        
        return {
            "valid": True,
            "license_id": str(license_model.id),
            "license_type": license_model.license_type.value,
            "expires_at": license_model.validity_end.isoformat(),
        }
    
    async def remote_revoke(
        self,
        license_id: UUID,
        reason: str
    ) -> bool:
        """
        Revoke license (can be triggered remotely).
        
        Args:
            license_id: License ID to revoke
            reason: Revocation reason
            
        Returns:
            True if revoked successfully
        """
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.id == license_id)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return False
        
        license_model.status = LicenseStatus.REVOKED
        license_model.revoked_at = datetime.now(timezone.utc)
        
        metadata = license_model.metadata or {}
        metadata["revocation_reason"] = reason
        metadata["revoked_remotely"] = True
        license_model.metadata = metadata
        
        # Revoke all activations
        await self.db.execute(
            update(LicenseActivationModel)
            .where(LicenseActivationModel.license_id == license_id)
            .where(LicenseActivationModel.status == ActivationStatus.ACTIVE)
            .values(
                status=ActivationStatus.REVOKED,
                revoked_at=datetime.now(timezone.utc)
            )
        )
        
        await self.db.commit()
        return True
    
    def _generate_signature(self, license: LicenseModel) -> str:
        """Generate signature for license."""
        data_str = "|".join([
            license.license_key,
            license.license_type.value,
            license.validity_start.isoformat(),
            license.validity_end.isoformat(),
            str(license.max_concurrent_users),
            license.hardware_id or "",
        ])
        
        return hashlib.sha256(
            f"{data_str}|{self.signing_key}".encode()
        ).hexdigest()
    
    def _to_response(self, model: LicenseModel) -> LicenseResponse:
        """Convert model to response."""
        return LicenseResponse(
            id=model.id,
            license_key=model.license_key,
            license_type=model.license_type,
            features=model.features,
            limits=LicenseLimits(
                max_concurrent_users=model.max_concurrent_users,
                max_cpu_cores=model.max_cpu_cores,
                max_storage_gb=model.max_storage_gb,
                max_projects=model.max_projects,
                max_datasets=model.max_datasets,
            ),
            validity_start=model.validity_start,
            validity_end=model.validity_end,
            subscription_type=model.subscription_type,
            grace_period_days=model.grace_period_days,
            auto_renew=model.auto_renew,
            hardware_id=model.hardware_id,
            status=model.status,
            created_at=model.created_at,
            activated_at=model.activated_at,
            metadata=model.metadata,
        )
