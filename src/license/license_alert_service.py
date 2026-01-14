"""
License Alert Service for SuperInsight Platform.

Manages license-related alerts and notifications.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Callable
from uuid import UUID, uuid4
from enum import Enum

from src.models.license import LicenseModel, LicenseStatus
from src.schemas.license import AlertType, AlertConfig, Alert, ValidityStatus
from src.license.time_controller import TimeController


logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LicenseAlertService:
    """
    License Alert Service.
    
    Monitors license status and generates alerts.
    """
    
    # Default alert configurations
    DEFAULT_CONFIGS = {
        AlertType.EXPIRY_WARNING: AlertConfig(
            alert_type=AlertType.EXPIRY_WARNING,
            enabled=True,
            threshold=30,  # Days before expiry
            notification_channels=["email", "dashboard"],
        ),
        AlertType.CONCURRENT_LIMIT: AlertConfig(
            alert_type=AlertType.CONCURRENT_LIMIT,
            enabled=True,
            threshold=80,  # Percentage utilization
            notification_channels=["dashboard"],
        ),
        AlertType.RESOURCE_LIMIT: AlertConfig(
            alert_type=AlertType.RESOURCE_LIMIT,
            enabled=True,
            threshold=80,  # Percentage utilization
            notification_channels=["dashboard"],
        ),
        AlertType.LICENSE_VIOLATION: AlertConfig(
            alert_type=AlertType.LICENSE_VIOLATION,
            enabled=True,
            notification_channels=["email", "dashboard"],
        ),
        AlertType.ACTIVATION_FAILED: AlertConfig(
            alert_type=AlertType.ACTIVATION_FAILED,
            enabled=True,
            notification_channels=["email", "dashboard"],
        ),
    }
    
    def __init__(
        self,
        configs: Optional[Dict[AlertType, AlertConfig]] = None,
        notification_handlers: Optional[Dict[str, Callable]] = None,
    ):
        """
        Initialize License Alert Service.
        
        Args:
            configs: Alert configurations
            notification_handlers: Handlers for notification channels
        """
        self.configs = configs or self.DEFAULT_CONFIGS.copy()
        self.notification_handlers = notification_handlers or {}
        self.time_controller = TimeController()
        self._active_alerts: List[Alert] = []
        self._alert_history: List[Alert] = []
    
    def configure_alert(self, config: AlertConfig) -> None:
        """Configure an alert type."""
        self.configs[config.alert_type] = config
    
    def get_config(self, alert_type: AlertType) -> Optional[AlertConfig]:
        """Get configuration for an alert type."""
        return self.configs.get(alert_type)
    
    def register_notification_handler(
        self,
        channel: str,
        handler: Callable[[Alert], None]
    ) -> None:
        """Register a notification handler for a channel."""
        self.notification_handlers[channel] = handler
    
    def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Dict[str, Any]
    ) -> Alert:
        """Create a new alert."""
        return Alert(
            id=uuid4(),
            alert_type=alert_type,
            severity=severity.value,
            message=message,
            details=details,
            created_at=datetime.now(timezone.utc),
            acknowledged=False,
        )
    
    def _send_notifications(self, alert: Alert) -> None:
        """Send notifications for an alert."""
        config = self.configs.get(alert.alert_type)
        if not config or not config.enabled:
            return
        
        for channel in config.notification_channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel}: {e}")
    
    def check_expiry_warning(
        self,
        license: LicenseModel
    ) -> Optional[Alert]:
        """
        Check for license expiry warning.
        
        Args:
            license: License to check
            
        Returns:
            Alert if warning should be raised
        """
        config = self.configs.get(AlertType.EXPIRY_WARNING)
        if not config or not config.enabled:
            return None
        
        validity = self.time_controller.check_license_validity(license)
        
        if validity.status == ValidityStatus.EXPIRED:
            alert = self._create_alert(
                alert_type=AlertType.EXPIRY_WARNING,
                severity=AlertSeverity.CRITICAL,
                message="License has expired",
                details={
                    "license_id": str(license.id),
                    "expired_at": license.validity_end.isoformat(),
                }
            )
            self._active_alerts.append(alert)
            self._send_notifications(alert)
            return alert
        
        if validity.status == ValidityStatus.GRACE_PERIOD:
            alert = self._create_alert(
                alert_type=AlertType.EXPIRY_WARNING,
                severity=AlertSeverity.ERROR,
                message=f"License expired, {validity.grace_days_remaining} grace days remaining",
                details={
                    "license_id": str(license.id),
                    "grace_days_remaining": validity.grace_days_remaining,
                }
            )
            self._active_alerts.append(alert)
            self._send_notifications(alert)
            return alert
        
        if validity.days_remaining and validity.days_remaining <= config.threshold:
            severity = AlertSeverity.WARNING
            if validity.days_remaining <= 7:
                severity = AlertSeverity.ERROR
            elif validity.days_remaining <= 3:
                severity = AlertSeverity.CRITICAL
            
            alert = self._create_alert(
                alert_type=AlertType.EXPIRY_WARNING,
                severity=severity,
                message=f"License expires in {validity.days_remaining} days",
                details={
                    "license_id": str(license.id),
                    "days_remaining": validity.days_remaining,
                    "expires_at": license.validity_end.isoformat(),
                }
            )
            self._active_alerts.append(alert)
            self._send_notifications(alert)
            return alert
        
        return None
    
    def check_concurrent_limit(
        self,
        current_users: int,
        max_users: int,
        license_id: Optional[UUID] = None
    ) -> Optional[Alert]:
        """
        Check for concurrent user limit warning.
        
        Args:
            current_users: Current concurrent users
            max_users: Maximum allowed users
            license_id: License ID
            
        Returns:
            Alert if warning should be raised
        """
        config = self.configs.get(AlertType.CONCURRENT_LIMIT)
        if not config or not config.enabled:
            return None
        
        if max_users == 0:
            return None
        
        utilization = (current_users / max_users) * 100
        
        if utilization >= 100:
            alert = self._create_alert(
                alert_type=AlertType.CONCURRENT_LIMIT,
                severity=AlertSeverity.CRITICAL,
                message=f"Concurrent user limit reached ({current_users}/{max_users})",
                details={
                    "license_id": str(license_id) if license_id else None,
                    "current_users": current_users,
                    "max_users": max_users,
                    "utilization_percent": utilization,
                }
            )
            self._active_alerts.append(alert)
            self._send_notifications(alert)
            return alert
        
        if utilization >= config.threshold:
            alert = self._create_alert(
                alert_type=AlertType.CONCURRENT_LIMIT,
                severity=AlertSeverity.WARNING,
                message=f"Concurrent user utilization at {utilization:.1f}%",
                details={
                    "license_id": str(license_id) if license_id else None,
                    "current_users": current_users,
                    "max_users": max_users,
                    "utilization_percent": utilization,
                }
            )
            self._active_alerts.append(alert)
            self._send_notifications(alert)
            return alert
        
        return None
    
    def check_resource_limit(
        self,
        resource_type: str,
        current_value: float,
        max_value: float,
        license_id: Optional[UUID] = None
    ) -> Optional[Alert]:
        """
        Check for resource limit warning.
        
        Args:
            resource_type: Type of resource (cpu, storage, etc.)
            current_value: Current usage
            max_value: Maximum allowed
            license_id: License ID
            
        Returns:
            Alert if warning should be raised
        """
        config = self.configs.get(AlertType.RESOURCE_LIMIT)
        if not config or not config.enabled:
            return None
        
        if max_value == 0:
            return None
        
        utilization = (current_value / max_value) * 100
        
        if utilization >= 100:
            alert = self._create_alert(
                alert_type=AlertType.RESOURCE_LIMIT,
                severity=AlertSeverity.CRITICAL,
                message=f"{resource_type.upper()} limit reached ({current_value}/{max_value})",
                details={
                    "license_id": str(license_id) if license_id else None,
                    "resource_type": resource_type,
                    "current_value": current_value,
                    "max_value": max_value,
                    "utilization_percent": utilization,
                }
            )
            self._active_alerts.append(alert)
            self._send_notifications(alert)
            return alert
        
        if utilization >= config.threshold:
            alert = self._create_alert(
                alert_type=AlertType.RESOURCE_LIMIT,
                severity=AlertSeverity.WARNING,
                message=f"{resource_type.upper()} utilization at {utilization:.1f}%",
                details={
                    "license_id": str(license_id) if license_id else None,
                    "resource_type": resource_type,
                    "current_value": current_value,
                    "max_value": max_value,
                    "utilization_percent": utilization,
                }
            )
            self._active_alerts.append(alert)
            self._send_notifications(alert)
            return alert
        
        return None
    
    def raise_violation_alert(
        self,
        violation_type: str,
        message: str,
        details: Dict[str, Any],
        license_id: Optional[UUID] = None
    ) -> Alert:
        """
        Raise a license violation alert.
        
        Args:
            violation_type: Type of violation
            message: Alert message
            details: Violation details
            license_id: License ID
            
        Returns:
            Created alert
        """
        alert = self._create_alert(
            alert_type=AlertType.LICENSE_VIOLATION,
            severity=AlertSeverity.CRITICAL,
            message=message,
            details={
                "license_id": str(license_id) if license_id else None,
                "violation_type": violation_type,
                **details,
            }
        )
        self._active_alerts.append(alert)
        self._send_notifications(alert)
        return alert
    
    def raise_activation_failed_alert(
        self,
        license_key: str,
        error: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Raise an activation failed alert.
        
        Args:
            license_key: License key that failed
            error: Error message
            details: Additional details
            
        Returns:
            Created alert
        """
        alert = self._create_alert(
            alert_type=AlertType.ACTIVATION_FAILED,
            severity=AlertSeverity.ERROR,
            message=f"License activation failed: {error}",
            details={
                "license_key": license_key[:8] + "...",  # Partial key for security
                "error": error,
                **(details or {}),
            }
        )
        self._active_alerts.append(alert)
        self._send_notifications(alert)
        return alert
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unacknowledged) alerts."""
        return [a for a in self._active_alerts if not a.acknowledged]
    
    def get_alerts_by_type(self, alert_type: AlertType) -> List[Alert]:
        """Get alerts by type."""
        return [a for a in self._active_alerts if a.alert_type == alert_type]
    
    def acknowledge_alert(
        self,
        alert_id: UUID,
        acknowledged_by: str
    ) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: User who acknowledged
            
        Returns:
            True if alert was found and acknowledged
        """
        for alert in self._active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now(timezone.utc)
                self._alert_history.append(alert)
                return True
        return False
    
    def clear_acknowledged_alerts(self) -> int:
        """Clear acknowledged alerts from active list."""
        before = len(self._active_alerts)
        self._active_alerts = [a for a in self._active_alerts if not a.acknowledged]
        return before - len(self._active_alerts)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alerts."""
        active = self.get_active_alerts()
        
        by_type = {}
        by_severity = {}
        
        for alert in active:
            by_type[alert.alert_type.value] = by_type.get(alert.alert_type.value, 0) + 1
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
        
        return {
            "total_active": len(active),
            "by_type": by_type,
            "by_severity": by_severity,
            "critical_count": by_severity.get("critical", 0),
            "error_count": by_severity.get("error", 0),
            "warning_count": by_severity.get("warning", 0),
        }
