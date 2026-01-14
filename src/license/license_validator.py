"""
License Validator for SuperInsight Platform.

Validates license integrity, signatures, and hardware binding.
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from src.models.license import LicenseModel, LicenseStatus
from src.schemas.license import ValidationResult, LicenseType


class LicenseValidator:
    """
    License Validator.
    
    Validates license signatures, integrity, and hardware binding.
    """
    
    def __init__(self, signing_key: str = "default_signing_key"):
        """
        Initialize License Validator.
        
        Args:
            signing_key: Key used for signature verification
        """
        self.signing_key = signing_key
    
    def _compute_signature(self, license_data: Dict[str, Any]) -> str:
        """Compute expected signature for license data."""
        data_str = "|".join([
            str(license_data.get("license_key", "")),
            str(license_data.get("license_type", "")),
            str(license_data.get("validity_start", "")),
            str(license_data.get("validity_end", "")),
            str(license_data.get("max_concurrent_users", "")),
            str(license_data.get("hardware_id", "")),
        ])
        
        return hashlib.sha256(
            f"{data_str}|{self.signing_key}".encode()
        ).hexdigest()
    
    def verify_signature(self, license: LicenseModel) -> bool:
        """
        Verify license signature.
        
        Args:
            license: License model to verify
            
        Returns:
            True if signature is valid
        """
        license_data = {
            "license_key": license.license_key,
            "license_type": license.license_type.value,
            "validity_start": license.validity_start.isoformat(),
            "validity_end": license.validity_end.isoformat(),
            "max_concurrent_users": license.max_concurrent_users,
            "hardware_id": license.hardware_id,
        }
        
        expected_signature = self._compute_signature(license_data)
        return license.signature == expected_signature
    
    def check_validity(self, license: LicenseModel) -> bool:
        """
        Check if license is within validity period.
        
        Args:
            license: License model to check
            
        Returns:
            True if license is valid (including grace period)
        """
        now = datetime.now(timezone.utc)
        
        # Ensure timezone-aware comparison
        validity_start = license.validity_start
        validity_end = license.validity_end
        
        if validity_start.tzinfo is None:
            validity_start = validity_start.replace(tzinfo=timezone.utc)
        if validity_end.tzinfo is None:
            validity_end = validity_end.replace(tzinfo=timezone.utc)
        
        # Check if not started
        if now < validity_start:
            return False
        
        # Check if expired (with grace period)
        from datetime import timedelta
        grace_end = validity_end + timedelta(days=license.grace_period_days)
        
        return now <= grace_end
    
    def check_hardware_binding(
        self,
        license: LicenseModel,
        current_hardware_id: Optional[str] = None
    ) -> bool:
        """
        Check hardware binding.
        
        Args:
            license: License model to check
            current_hardware_id: Current hardware fingerprint
            
        Returns:
            True if hardware matches or no binding required
        """
        # No hardware binding required
        if not license.hardware_id:
            return True
        
        # No current hardware provided
        if not current_hardware_id:
            return False
        
        return license.hardware_id == current_hardware_id
    
    def detect_tampering(self, license: LicenseModel) -> bool:
        """
        Detect if license has been tampered with.
        
        Args:
            license: License model to check
            
        Returns:
            True if tampering detected
        """
        # Verify signature
        if not self.verify_signature(license):
            return True
        
        # Check for impossible states
        if license.status == LicenseStatus.ACTIVE and not license.activated_at:
            return True
        
        if license.status == LicenseStatus.REVOKED and not license.revoked_at:
            return True
        
        # Check validity dates
        if license.validity_end < license.validity_start:
            return True
        
        return False
    
    async def validate_license(
        self,
        license: LicenseModel,
        current_hardware_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Perform full license validation.
        
        Args:
            license: License model to validate
            current_hardware_id: Current hardware fingerprint
            
        Returns:
            Validation result
        """
        warnings = []
        
        # Check status
        if license.status == LicenseStatus.REVOKED:
            return ValidationResult(
                valid=False,
                reason="License has been revoked",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        if license.status == LicenseStatus.SUSPENDED:
            return ValidationResult(
                valid=False,
                reason="License is suspended",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        if license.status == LicenseStatus.PENDING:
            return ValidationResult(
                valid=False,
                reason="License has not been activated",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        # Verify signature
        if not self.verify_signature(license):
            return ValidationResult(
                valid=False,
                reason="Invalid license signature - possible tampering detected",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        # Check validity period
        now = datetime.now(timezone.utc)
        validity_start = license.validity_start
        validity_end = license.validity_end
        
        if validity_start.tzinfo is None:
            validity_start = validity_start.replace(tzinfo=timezone.utc)
        if validity_end.tzinfo is None:
            validity_end = validity_end.replace(tzinfo=timezone.utc)
        
        if now < validity_start:
            days_until = (validity_start - now).days
            return ValidationResult(
                valid=False,
                reason=f"License validity period has not started (starts in {days_until} days)",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        if now > validity_end:
            from datetime import timedelta
            grace_end = validity_end + timedelta(days=license.grace_period_days)
            
            if now <= grace_end:
                days_remaining = (grace_end - now).days
                warnings.append(
                    f"License expired, in grace period ({days_remaining} days remaining)"
                )
            else:
                return ValidationResult(
                    valid=False,
                    reason="License has expired",
                    license_id=license.id,
                    license_type=license.license_type,
                    status=license.status
                )
        else:
            # Check for upcoming expiry
            days_remaining = (validity_end - now).days
            if days_remaining <= 30:
                warnings.append(f"License expires in {days_remaining} days")
        
        # Check hardware binding
        if not self.check_hardware_binding(license, current_hardware_id):
            return ValidationResult(
                valid=False,
                reason="Hardware mismatch - license is bound to different hardware",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        # Check for tampering
        if self.detect_tampering(license):
            return ValidationResult(
                valid=False,
                reason="License integrity check failed - possible tampering",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        return ValidationResult(
            valid=True,
            warnings=warnings,
            license_id=license.id,
            license_type=license.license_type,
            status=license.status
        )
    
    def validate_license_sync(
        self,
        license: LicenseModel,
        current_hardware_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Synchronous license validation (for non-async contexts).
        
        Args:
            license: License model to validate
            current_hardware_id: Current hardware fingerprint
            
        Returns:
            Validation result
        """
        warnings = []
        
        # Check status
        if license.status == LicenseStatus.REVOKED:
            return ValidationResult(
                valid=False,
                reason="License has been revoked",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        if license.status == LicenseStatus.SUSPENDED:
            return ValidationResult(
                valid=False,
                reason="License is suspended",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        if license.status == LicenseStatus.PENDING:
            return ValidationResult(
                valid=False,
                reason="License has not been activated",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        # Verify signature
        if not self.verify_signature(license):
            return ValidationResult(
                valid=False,
                reason="Invalid license signature",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        # Check validity
        if not self.check_validity(license):
            return ValidationResult(
                valid=False,
                reason="License has expired",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        # Check hardware
        if not self.check_hardware_binding(license, current_hardware_id):
            return ValidationResult(
                valid=False,
                reason="Hardware mismatch",
                license_id=license.id,
                license_type=license.license_type,
                status=license.status
            )
        
        return ValidationResult(
            valid=True,
            warnings=warnings,
            license_id=license.id,
            license_type=license.license_type,
            status=license.status
        )
