"""
License Manager for SuperInsight Platform.

Manages the complete license lifecycle including creation, activation,
renewal, upgrade, and revocation.
"""

import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.license import (
    LicenseModel, LicenseActivationModel, LicenseStatus, LicenseType,
    SubscriptionType, ActivationType, ActivationStatus, LicenseEventType
)
from src.schemas.license import (
    LicenseLimits, LicenseValidity, LicenseResponse, ActivationResult,
    CreateLicenseRequest, RenewLicenseRequest, UpgradeLicenseRequest
)


class LicenseManager:
    """
    License Manager.
    
    Manages license lifecycle including creation, activation, renewal,
    upgrade, and revocation.
    """
    
    # Feature matrix by license type
    FEATURE_MATRIX = {
        LicenseType.TRIAL: ["api_access", "basic_annotation"],
        LicenseType.BASIC: ["api_access", "basic_annotation", "export"],
        LicenseType.PROFESSIONAL: [
            "api_access", "basic_annotation", "export",
            "ai_annotation", "quality_assessment"
        ],
        LicenseType.ENTERPRISE: [
            "api_access", "basic_annotation", "export",
            "ai_annotation", "quality_assessment",
            "knowledge_graph", "advanced_analytics",
            "multi_tenant", "custom_integrations"
        ],
    }
    
    # Default limits by license type
    DEFAULT_LIMITS = {
        LicenseType.TRIAL: LicenseLimits(
            max_concurrent_users=2,
            max_cpu_cores=2,
            max_storage_gb=10,
            max_projects=2,
            max_datasets=10
        ),
        LicenseType.BASIC: LicenseLimits(
            max_concurrent_users=5,
            max_cpu_cores=4,
            max_storage_gb=50,
            max_projects=5,
            max_datasets=50
        ),
        LicenseType.PROFESSIONAL: LicenseLimits(
            max_concurrent_users=20,
            max_cpu_cores=8,
            max_storage_gb=200,
            max_projects=20,
            max_datasets=200
        ),
        LicenseType.ENTERPRISE: LicenseLimits(
            max_concurrent_users=100,
            max_cpu_cores=32,
            max_storage_gb=1000,
            max_projects=100,
            max_datasets=1000
        ),
    }
    
    # Valid status transitions
    VALID_TRANSITIONS = {
        LicenseStatus.PENDING: [LicenseStatus.ACTIVE, LicenseStatus.REVOKED],
        LicenseStatus.ACTIVE: [LicenseStatus.EXPIRED, LicenseStatus.SUSPENDED, LicenseStatus.REVOKED],
        LicenseStatus.EXPIRED: [LicenseStatus.ACTIVE, LicenseStatus.REVOKED],  # Can renew
        LicenseStatus.SUSPENDED: [LicenseStatus.ACTIVE, LicenseStatus.REVOKED],
        LicenseStatus.REVOKED: [],  # Terminal state
    }
    
    def __init__(
        self,
        db: AsyncSession,
        signing_key: str = "default_signing_key"
    ):
        """
        Initialize License Manager.
        
        Args:
            db: Database session
            signing_key: Key for signing licenses
        """
        self.db = db
        self.signing_key = signing_key
        self._license_cache: Optional[LicenseModel] = None
    
    def _generate_license_key(self) -> str:
        """Generate a unique license key."""
        # Format: XXXX-XXXX-XXXX-XXXX
        parts = [secrets.token_hex(2).upper() for _ in range(4)]
        return "-".join(parts)
    
    def _generate_signature(self, license_data: Dict[str, Any]) -> str:
        """Generate signature for license data."""
        # Create deterministic string from license data
        data_str = "|".join([
            str(license_data.get("license_key", "")),
            str(license_data.get("license_type", "")),
            str(license_data.get("validity_start", "")),
            str(license_data.get("validity_end", "")),
            str(license_data.get("max_concurrent_users", "")),
            str(license_data.get("hardware_id", "")),
        ])
        
        # Sign with HMAC-SHA256
        signature = hashlib.sha256(
            f"{data_str}|{self.signing_key}".encode()
        ).hexdigest()
        
        return signature
    
    async def create_license(
        self,
        request: CreateLicenseRequest
    ) -> LicenseResponse:
        """
        Create a new license.
        
        Args:
            request: License creation request
            
        Returns:
            Created license response
        """
        # Generate license key
        license_key = self._generate_license_key()
        
        # Get default features if not specified
        features = request.features or self.FEATURE_MATRIX.get(
            request.license_type, []
        )
        
        # Get default limits if not specified
        limits = request.limits or self.DEFAULT_LIMITS.get(
            request.license_type, LicenseLimits()
        )
        
        # Prepare license data for signing
        license_data = {
            "license_key": license_key,
            "license_type": request.license_type.value,
            "validity_start": request.validity.start_date.isoformat(),
            "validity_end": request.validity.end_date.isoformat(),
            "max_concurrent_users": limits.max_concurrent_users,
            "hardware_id": None,
        }
        
        # Generate signature
        signature = self._generate_signature(license_data)
        
        # Create license record
        license_model = LicenseModel(
            id=uuid4(),
            license_key=license_key,
            license_type=request.license_type,
            features=features,
            max_concurrent_users=limits.max_concurrent_users,
            max_cpu_cores=limits.max_cpu_cores,
            max_storage_gb=limits.max_storage_gb,
            max_projects=limits.max_projects,
            max_datasets=limits.max_datasets,
            validity_start=request.validity.start_date,
            validity_end=request.validity.end_date,
            subscription_type=request.validity.subscription_type,
            grace_period_days=request.validity.grace_period_days,
            auto_renew=request.validity.auto_renew,
            status=LicenseStatus.PENDING,
            signature=signature,
            metadata=request.metadata,
        )
        
        self.db.add(license_model)
        await self.db.commit()
        await self.db.refresh(license_model)
        
        return self._to_response(license_model)
    
    async def activate_license(
        self,
        license_key: str,
        hardware_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ActivationResult:
        """
        Activate a license.
        
        Args:
            license_key: License key to activate
            hardware_id: Hardware fingerprint for binding
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Activation result
        """
        # Find license
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.license_key == license_key)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return ActivationResult(
                success=False,
                error="License not found"
            )
        
        # Check if already activated
        if license_model.status == LicenseStatus.ACTIVE:
            # Check hardware binding
            if license_model.hardware_id and hardware_id:
                if license_model.hardware_id != hardware_id:
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
        
        # Check validity period
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
        
        # Update license
        license_model.status = LicenseStatus.ACTIVE
        license_model.activated_at = now
        if hardware_id:
            license_model.hardware_id = hardware_id
            # Re-sign with hardware binding
            license_data = {
                "license_key": license_model.license_key,
                "license_type": license_model.license_type.value,
                "validity_start": license_model.validity_start.isoformat(),
                "validity_end": license_model.validity_end.isoformat(),
                "max_concurrent_users": license_model.max_concurrent_users,
                "hardware_id": hardware_id,
            }
            license_model.signature = self._generate_signature(license_data)
        
        # Create activation record
        activation = LicenseActivationModel(
            id=uuid4(),
            license_id=license_model.id,
            hardware_fingerprint=hardware_id or "none",
            activation_type=ActivationType.ONLINE,
            status=ActivationStatus.ACTIVE,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self.db.add(activation)
        await self.db.commit()
        await self.db.refresh(license_model)
        
        # Clear cache
        self._license_cache = None
        
        return ActivationResult(
            success=True,
            license=self._to_response(license_model),
            activation_id=activation.id
        )
    
    async def renew_license(
        self,
        license_id: UUID,
        request: RenewLicenseRequest
    ) -> Optional[LicenseResponse]:
        """
        Renew a license.
        
        Args:
            license_id: License ID to renew
            request: Renewal request
            
        Returns:
            Updated license response or None if not found
        """
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.id == license_id)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return None
        
        # Check if can be renewed
        if license_model.status == LicenseStatus.REVOKED:
            return None
        
        # Update validity
        license_model.validity_end = request.new_end_date
        if request.subscription_type:
            license_model.subscription_type = request.subscription_type
        
        # Reactivate if expired
        if license_model.status == LicenseStatus.EXPIRED:
            license_model.status = LicenseStatus.ACTIVE
        
        # Re-sign
        license_data = {
            "license_key": license_model.license_key,
            "license_type": license_model.license_type.value,
            "validity_start": license_model.validity_start.isoformat(),
            "validity_end": license_model.validity_end.isoformat(),
            "max_concurrent_users": license_model.max_concurrent_users,
            "hardware_id": license_model.hardware_id,
        }
        license_model.signature = self._generate_signature(license_data)
        
        await self.db.commit()
        await self.db.refresh(license_model)
        
        # Clear cache
        self._license_cache = None
        
        return self._to_response(license_model)
    
    async def upgrade_license(
        self,
        license_id: UUID,
        request: UpgradeLicenseRequest
    ) -> Optional[LicenseResponse]:
        """
        Upgrade a license.
        
        Args:
            license_id: License ID to upgrade
            request: Upgrade request
            
        Returns:
            Updated license response or None if not found
        """
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.id == license_id)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return None
        
        # Check if can be upgraded
        if license_model.status == LicenseStatus.REVOKED:
            return None
        
        # Update type
        if request.new_type:
            license_model.license_type = request.new_type
            # Add default features for new type
            default_features = self.FEATURE_MATRIX.get(request.new_type, [])
            license_model.features = list(set(license_model.features + default_features))
        
        # Update features
        if request.new_features:
            license_model.features = list(set(license_model.features + request.new_features))
        
        # Update limits
        if request.new_limits:
            license_model.max_concurrent_users = request.new_limits.max_concurrent_users
            license_model.max_cpu_cores = request.new_limits.max_cpu_cores
            license_model.max_storage_gb = request.new_limits.max_storage_gb
            license_model.max_projects = request.new_limits.max_projects
            license_model.max_datasets = request.new_limits.max_datasets
        
        # Re-sign
        license_data = {
            "license_key": license_model.license_key,
            "license_type": license_model.license_type.value,
            "validity_start": license_model.validity_start.isoformat(),
            "validity_end": license_model.validity_end.isoformat(),
            "max_concurrent_users": license_model.max_concurrent_users,
            "hardware_id": license_model.hardware_id,
        }
        license_model.signature = self._generate_signature(license_data)
        
        await self.db.commit()
        await self.db.refresh(license_model)
        
        # Clear cache
        self._license_cache = None
        
        return self._to_response(license_model)
    
    async def revoke_license(
        self,
        license_id: UUID,
        reason: str
    ) -> bool:
        """
        Revoke a license.
        
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
        
        # Check if already revoked
        if license_model.status == LicenseStatus.REVOKED:
            return True
        
        # Revoke
        license_model.status = LicenseStatus.REVOKED
        license_model.revoked_at = datetime.now(timezone.utc)
        
        # Store reason in metadata
        metadata = license_model.metadata or {}
        metadata["revocation_reason"] = reason
        license_model.metadata = metadata
        
        await self.db.commit()
        
        # Clear cache
        self._license_cache = None
        
        return True
    
    async def suspend_license(self, license_id: UUID) -> bool:
        """Suspend a license."""
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.id == license_id)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return False
        
        if license_model.status not in [LicenseStatus.ACTIVE]:
            return False
        
        license_model.status = LicenseStatus.SUSPENDED
        await self.db.commit()
        
        self._license_cache = None
        return True
    
    async def reactivate_license(self, license_id: UUID) -> bool:
        """Reactivate a suspended license."""
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.id == license_id)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return False
        
        if license_model.status != LicenseStatus.SUSPENDED:
            return False
        
        license_model.status = LicenseStatus.ACTIVE
        await self.db.commit()
        
        self._license_cache = None
        return True
    
    async def get_license(self, license_id: UUID) -> Optional[LicenseResponse]:
        """Get license by ID."""
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.id == license_id)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return None
        
        return self._to_response(license_model)
    
    async def get_license_by_key(self, license_key: str) -> Optional[LicenseResponse]:
        """Get license by key."""
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.license_key == license_key)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return None
        
        return self._to_response(license_model)
    
    async def get_current_license(self) -> Optional[LicenseModel]:
        """
        Get the current active license.
        
        Returns cached license if available.
        """
        if self._license_cache:
            return self._license_cache
        
        result = await self.db.execute(
            select(LicenseModel)
            .where(LicenseModel.status == LicenseStatus.ACTIVE)
            .order_by(LicenseModel.activated_at.desc())
            .limit(1)
        )
        license_model = result.scalar_one_or_none()
        
        if license_model:
            self._license_cache = license_model
        
        return license_model
    
    async def list_licenses(
        self,
        status: Optional[LicenseStatus] = None,
        license_type: Optional[LicenseType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[LicenseResponse]:
        """List licenses with optional filters."""
        query = select(LicenseModel)
        
        if status:
            query = query.where(LicenseModel.status == status)
        if license_type:
            query = query.where(LicenseModel.license_type == license_type)
        
        query = query.order_by(LicenseModel.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        licenses = result.scalars().all()
        
        return [self._to_response(lic) for lic in licenses]
    
    def can_transition(
        self,
        current_status: LicenseStatus,
        new_status: LicenseStatus
    ) -> bool:
        """Check if status transition is valid."""
        valid_targets = self.VALID_TRANSITIONS.get(current_status, [])
        return new_status in valid_targets
    
    async def transition_status(
        self,
        license_id: UUID,
        new_status: LicenseStatus
    ) -> bool:
        """
        Transition license to new status.
        
        Args:
            license_id: License ID
            new_status: Target status
            
        Returns:
            True if transition successful
        """
        result = await self.db.execute(
            select(LicenseModel).where(LicenseModel.id == license_id)
        )
        license_model = result.scalar_one_or_none()
        
        if not license_model:
            return False
        
        if not self.can_transition(license_model.status, new_status):
            return False
        
        license_model.status = new_status
        
        if new_status == LicenseStatus.REVOKED:
            license_model.revoked_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        self._license_cache = None
        
        return True
    
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
