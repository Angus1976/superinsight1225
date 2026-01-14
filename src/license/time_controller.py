"""
Time Controller for SuperInsight Platform.

Manages license validity periods and expiration handling.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from src.models.license import LicenseModel, LicenseStatus, SubscriptionType
from src.schemas.license import ValidityStatus


class ValidityStatusResult:
    """Result of validity status check."""
    
    def __init__(
        self,
        status: ValidityStatus,
        days_remaining: Optional[int] = None,
        days_until_start: Optional[int] = None,
        grace_days_remaining: Optional[int] = None,
        message: Optional[str] = None
    ):
        self.status = status
        self.days_remaining = days_remaining
        self.days_until_start = days_until_start
        self.grace_days_remaining = grace_days_remaining
        self.message = message


class TimeController:
    """
    Time Controller.
    
    Manages license validity periods, expiration, and grace periods.
    """
    
    # Default reminder days before expiry
    REMINDER_DAYS = [30, 14, 7, 3, 1]
    
    def __init__(self):
        """Initialize Time Controller."""
        pass
    
    def _ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def check_license_validity(
        self,
        license: LicenseModel
    ) -> ValidityStatusResult:
        """
        Check license validity status.
        
        Args:
            license: License model to check
            
        Returns:
            Validity status result
        """
        now = datetime.now(timezone.utc)
        validity_start = self._ensure_timezone(license.validity_start)
        validity_end = self._ensure_timezone(license.validity_end)
        
        # Check if not started
        if now < validity_start:
            days_until = (validity_start - now).days
            return ValidityStatusResult(
                status=ValidityStatus.NOT_STARTED,
                days_until_start=days_until,
                message=f"License validity starts in {days_until} days"
            )
        
        # Check if expired
        if now > validity_end:
            grace_end = validity_end + timedelta(days=license.grace_period_days)
            
            if now <= grace_end:
                grace_remaining = (grace_end - now).days
                return ValidityStatusResult(
                    status=ValidityStatus.GRACE_PERIOD,
                    days_remaining=0,
                    grace_days_remaining=grace_remaining,
                    message=f"License expired, {grace_remaining} grace days remaining"
                )
            
            return ValidityStatusResult(
                status=ValidityStatus.EXPIRED,
                days_remaining=0,
                message="License has expired"
            )
        
        # Active
        days_remaining = (validity_end - now).days
        return ValidityStatusResult(
            status=ValidityStatus.ACTIVE,
            days_remaining=days_remaining,
            message=f"License active, {days_remaining} days remaining"
        )
    
    def is_valid(self, license: LicenseModel) -> bool:
        """
        Check if license is currently valid.
        
        Args:
            license: License model to check
            
        Returns:
            True if license is valid (active or in grace period)
        """
        status = self.check_license_validity(license)
        return status.status in [ValidityStatus.ACTIVE, ValidityStatus.GRACE_PERIOD]
    
    def is_in_grace_period(self, license: LicenseModel) -> bool:
        """Check if license is in grace period."""
        status = self.check_license_validity(license)
        return status.status == ValidityStatus.GRACE_PERIOD
    
    def get_days_remaining(self, license: LicenseModel) -> int:
        """Get days remaining until expiry."""
        status = self.check_license_validity(license)
        return status.days_remaining or 0
    
    def should_send_reminder(
        self,
        license: LicenseModel,
        reminder_days: Optional[List[int]] = None
    ) -> Optional[int]:
        """
        Check if expiry reminder should be sent.
        
        Args:
            license: License model to check
            reminder_days: List of days before expiry to send reminders
            
        Returns:
            Days remaining if reminder should be sent, None otherwise
        """
        if reminder_days is None:
            reminder_days = self.REMINDER_DAYS
        
        status = self.check_license_validity(license)
        
        if status.status != ValidityStatus.ACTIVE:
            return None
        
        days = status.days_remaining or 0
        
        if days in reminder_days:
            return days
        
        return None
    
    def get_expiry_restrictions(
        self,
        license: LicenseModel
    ) -> List[str]:
        """
        Get list of restrictions to apply based on validity status.
        
        Args:
            license: License model to check
            
        Returns:
            List of restriction identifiers
        """
        status = self.check_license_validity(license)
        restrictions = []
        
        if status.status == ValidityStatus.NOT_STARTED:
            restrictions.extend([
                "all_features_disabled",
                "read_only_mode",
            ])
        elif status.status == ValidityStatus.GRACE_PERIOD:
            restrictions.extend([
                "export_disabled",
                "new_projects_disabled",
                "ai_features_disabled",
            ])
        elif status.status == ValidityStatus.EXPIRED:
            restrictions.extend([
                "all_features_disabled",
                "read_only_mode",
                "login_disabled",
            ])
        
        return restrictions
    
    def calculate_renewal_date(
        self,
        license: LicenseModel,
        subscription_type: Optional[SubscriptionType] = None
    ) -> datetime:
        """
        Calculate new end date for renewal.
        
        Args:
            license: License model
            subscription_type: Override subscription type
            
        Returns:
            New end date
        """
        sub_type = subscription_type or license.subscription_type
        validity_end = self._ensure_timezone(license.validity_end)
        now = datetime.now(timezone.utc)
        
        # Start from current end date or now, whichever is later
        start_from = max(validity_end, now)
        
        if sub_type == SubscriptionType.MONTHLY:
            return start_from + timedelta(days=30)
        elif sub_type == SubscriptionType.YEARLY:
            return start_from + timedelta(days=365)
        else:  # PERPETUAL
            return start_from + timedelta(days=36500)  # ~100 years
    
    def get_subscription_info(
        self,
        license: LicenseModel
    ) -> Dict[str, Any]:
        """
        Get subscription information.
        
        Args:
            license: License model
            
        Returns:
            Subscription info dictionary
        """
        status = self.check_license_validity(license)
        
        return {
            "subscription_type": license.subscription_type.value,
            "validity_start": license.validity_start.isoformat(),
            "validity_end": license.validity_end.isoformat(),
            "grace_period_days": license.grace_period_days,
            "auto_renew": license.auto_renew,
            "status": status.status.value,
            "days_remaining": status.days_remaining,
            "days_until_start": status.days_until_start,
            "grace_days_remaining": status.grace_days_remaining,
            "message": status.message,
        }
