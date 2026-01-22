"""
Alert Service for SuperInsight Platform.

Manages alert configuration, threshold monitoring, and alert channel integrations.
Supports multiple notification channels including email, webhook, and SMS.

This module follows async-first architecture using asyncio.
All I/O operations are non-blocking to prevent event loop blocking.

Validates Requirements: 10.2, 10.3
"""

import asyncio
import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from enum import Enum

import aiohttp
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# ============== Alert Models ==============

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert notification channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"


class ThresholdOperator(str, Enum):
    """Threshold comparison operators."""
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "neq"


class AlertThreshold(BaseModel):
    """Alert threshold configuration."""
    id: str = Field(..., description="Threshold ID")
    metric_name: str = Field(..., description="Metric name to monitor")
    operator: ThresholdOperator = Field(..., description="Comparison operator")
    value: float = Field(..., description="Threshold value")
    duration_seconds: int = Field(default=60, ge=0, description="Duration threshold must be exceeded")
    severity: AlertSeverity = Field(default=AlertSeverity.WARNING, description="Alert severity")
    enabled: bool = Field(default=True, description="Whether threshold is active")
    channels: List[AlertChannel] = Field(default_factory=list, description="Notification channels")
    tenant_id: str = Field(..., description="Tenant ID")
    config_id: Optional[str] = Field(default=None, description="Related config ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('value')
    def validate_value(cls, v):
        """Validate threshold value is a valid number."""
        if not isinstance(v, (int, float)):
            raise ValueError("Threshold value must be a number")
        return float(v)

    @validator('duration_seconds')
    def validate_duration(cls, v):
        """Validate duration is non-negative."""
        if v < 0:
            raise ValueError("Duration must be non-negative")
        return v


class Alert(BaseModel):
    """Alert instance."""
    id: str = Field(..., description="Alert ID")
    threshold_id: str = Field(..., description="Threshold that triggered alert")
    metric_name: str = Field(..., description="Metric name")
    current_value: float = Field(..., description="Current metric value")
    threshold_value: float = Field(..., description="Threshold value")
    operator: ThresholdOperator = Field(..., description="Comparison operator")
    severity: AlertSeverity = Field(..., description="Alert severity")
    message: str = Field(..., description="Alert message")
    tenant_id: str = Field(..., description="Tenant ID")
    config_id: Optional[str] = Field(default=None, description="Related config ID")
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(default=None, description="Resolution time")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Acknowledgement time")
    acknowledged_by: Optional[str] = Field(default=None, description="User who acknowledged")
    notification_sent: bool = Field(default=False, description="Whether notification was sent")
    notification_channels: List[AlertChannel] = Field(default_factory=list)


class EmailConfig(BaseModel):
    """Email notification configuration."""
    smtp_host: str = Field(..., description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(..., description="SMTP username")
    smtp_password: str = Field(..., description="SMTP password")
    from_address: str = Field(..., description="From email address")
    to_addresses: List[str] = Field(..., description="Recipient email addresses")
    use_tls: bool = Field(default=True, description="Use TLS encryption")


class WebhookConfig(BaseModel):
    """Webhook notification configuration."""
    url: str = Field(..., description="Webhook URL")
    method: str = Field(default="POST", description="HTTP method")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retries")


class SMSConfig(BaseModel):
    """SMS notification configuration."""
    provider: str = Field(..., description="SMS provider (twilio, alibaba, tencent)")
    api_key: str = Field(..., description="API key")
    api_secret: Optional[str] = Field(default=None, description="API secret")
    from_number: str = Field(..., description="From phone number")
    to_numbers: List[str] = Field(..., description="Recipient phone numbers")


class ChannelConfig(BaseModel):
    """Alert channel configuration."""
    tenant_id: str = Field(..., description="Tenant ID")
    email: Optional[EmailConfig] = Field(default=None, description="Email config")
    webhook: Optional[WebhookConfig] = Field(default=None, description="Webhook config")
    sms: Optional[SMSConfig] = Field(default=None, description="SMS config")


# ============== Alert Service ==============

class AlertService:
    """
    Manages alert configuration and notification delivery.

    Features:
    - Threshold monitoring and evaluation
    - Alert deduplication to prevent alert storms
    - Multi-channel notification (email, webhook, SMS)
    - Alert acknowledgement and resolution tracking
    - Async notification delivery

    Validates Requirements: 10.2, 10.3
    """

    def __init__(self):
        """Initialize the alert service."""
        self._thresholds: Dict[str, AlertThreshold] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._channel_configs: Dict[str, ChannelConfig] = {}
        self._alert_history: List[Alert] = []
        self._dedup_cache: Dict[str, datetime] = {}
        self._dedup_window_seconds: int = 300  # 5 minutes
        self._lock = asyncio.Lock()
        self._alert_handlers: List[Callable[[Alert], None]] = []
        self._metric_values: Dict[str, List[tuple]] = {}  # metric_name -> [(timestamp, value)]
        self._metric_window_seconds: int = 300  # Keep 5 minutes of metrics
        logger.info("AlertService initialized")

    def _generate_alert_id(self, threshold: AlertThreshold, current_value: float) -> str:
        """Generate a unique alert ID."""
        data = f"{threshold.id}:{threshold.metric_name}:{threshold.tenant_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _generate_dedup_key(self, threshold: AlertThreshold) -> str:
        """Generate a deduplication key for an alert."""
        return f"{threshold.tenant_id}:{threshold.metric_name}:{threshold.id}"

    async def create_threshold(self, threshold: AlertThreshold) -> AlertThreshold:
        """
        Create a new alert threshold.

        Args:
            threshold: Threshold configuration

        Returns:
            Created threshold

        Validates Requirements: 10.2
        """
        async with self._lock:
            self._thresholds[threshold.id] = threshold
            logger.info(f"Created threshold {threshold.id} for metric {threshold.metric_name}")
            return threshold

    async def update_threshold(self, threshold_id: str, updates: Dict[str, Any]) -> Optional[AlertThreshold]:
        """
        Update an existing threshold.

        Args:
            threshold_id: Threshold ID
            updates: Dictionary of updates

        Returns:
            Updated threshold or None if not found
        """
        async with self._lock:
            if threshold_id not in self._thresholds:
                logger.warning(f"Threshold {threshold_id} not found")
                return None

            threshold = self._thresholds[threshold_id]

            for key, value in updates.items():
                if hasattr(threshold, key):
                    setattr(threshold, key, value)

            threshold.updated_at = datetime.utcnow()
            logger.info(f"Updated threshold {threshold_id}")
            return threshold

    async def delete_threshold(self, threshold_id: str) -> bool:
        """
        Delete a threshold.

        Args:
            threshold_id: Threshold ID

        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if threshold_id in self._thresholds:
                del self._thresholds[threshold_id]
                logger.info(f"Deleted threshold {threshold_id}")
                return True
            return False

    async def get_threshold(self, threshold_id: str) -> Optional[AlertThreshold]:
        """Get a threshold by ID."""
        async with self._lock:
            return self._thresholds.get(threshold_id)

    async def list_thresholds(self, tenant_id: str) -> List[AlertThreshold]:
        """List all thresholds for a tenant."""
        async with self._lock:
            return [t for t in self._thresholds.values() if t.tenant_id == tenant_id]

    def evaluate_threshold(
        self,
        threshold: AlertThreshold,
        current_value: float
    ) -> bool:
        """
        Evaluate if a threshold is violated.

        Args:
            threshold: Threshold configuration
            current_value: Current metric value

        Returns:
            True if threshold is violated

        Validates Requirements: 10.2
        """
        if not threshold.enabled:
            return False

        operator_map = {
            ThresholdOperator.GREATER_THAN: lambda c, t: c > t,
            ThresholdOperator.GREATER_THAN_OR_EQUAL: lambda c, t: c >= t,
            ThresholdOperator.LESS_THAN: lambda c, t: c < t,
            ThresholdOperator.LESS_THAN_OR_EQUAL: lambda c, t: c <= t,
            ThresholdOperator.EQUAL: lambda c, t: c == t,
            ThresholdOperator.NOT_EQUAL: lambda c, t: c != t,
        }

        compare_fn = operator_map.get(threshold.operator)
        if compare_fn is None:
            logger.warning(f"Unknown operator: {threshold.operator}")
            return False

        return compare_fn(current_value, threshold.value)

    async def record_metric(
        self,
        metric_name: str,
        value: float,
        tenant_id: str,
        config_id: Optional[str] = None
    ) -> List[Alert]:
        """
        Record a metric value and evaluate all relevant thresholds.

        Args:
            metric_name: Metric name
            value: Metric value
            tenant_id: Tenant ID
            config_id: Optional config ID

        Returns:
            List of triggered alerts

        Validates Requirements: 10.3
        """
        now = datetime.utcnow()
        triggered_alerts: List[Alert] = []

        async with self._lock:
            # Store metric value for duration-based thresholds
            metric_key = f"{tenant_id}:{metric_name}"
            if metric_key not in self._metric_values:
                self._metric_values[metric_key] = []

            self._metric_values[metric_key].append((now, value))

            # Clean up old metric values
            cutoff = now - timedelta(seconds=self._metric_window_seconds)
            self._metric_values[metric_key] = [
                (ts, val) for ts, val in self._metric_values[metric_key]
                if ts > cutoff
            ]

            # Find relevant thresholds
            relevant_thresholds = [
                t for t in self._thresholds.values()
                if t.tenant_id == tenant_id
                and t.metric_name == metric_name
                and t.enabled
                and (t.config_id is None or t.config_id == config_id)
            ]

            # Evaluate each threshold
            for threshold in relevant_thresholds:
                violated = self.evaluate_threshold(threshold, value)

                if violated:
                    # Check duration requirement
                    if threshold.duration_seconds > 0:
                        duration_violated = self._check_duration_violation(
                            metric_key, threshold, now
                        )
                        if not duration_violated:
                            continue

                    # Check deduplication
                    dedup_key = self._generate_dedup_key(threshold)
                    if dedup_key in self._dedup_cache:
                        last_alert_time = self._dedup_cache[dedup_key]
                        if (now - last_alert_time).total_seconds() < self._dedup_window_seconds:
                            logger.debug(f"Skipping duplicate alert for {dedup_key}")
                            continue

                    # Create alert
                    alert = await self._create_alert(threshold, value, tenant_id, config_id)
                    triggered_alerts.append(alert)

                    # Update dedup cache
                    self._dedup_cache[dedup_key] = now

        # Send notifications outside lock
        for alert in triggered_alerts:
            await self._send_notifications(alert)
            await self._call_alert_handlers(alert)

        return triggered_alerts

    def _check_duration_violation(
        self,
        metric_key: str,
        threshold: AlertThreshold,
        now: datetime
    ) -> bool:
        """Check if threshold has been violated for required duration."""
        if metric_key not in self._metric_values:
            return False

        cutoff = now - timedelta(seconds=threshold.duration_seconds)
        recent_values = [
            (ts, val) for ts, val in self._metric_values[metric_key]
            if ts >= cutoff
        ]

        if not recent_values:
            return False

        # All values in duration window must violate threshold
        for ts, val in recent_values:
            if not self.evaluate_threshold(threshold, val):
                return False

        return True

    async def _create_alert(
        self,
        threshold: AlertThreshold,
        current_value: float,
        tenant_id: str,
        config_id: Optional[str]
    ) -> Alert:
        """Create a new alert instance."""
        alert_id = self._generate_alert_id(threshold, current_value)

        operator_desc = {
            ThresholdOperator.GREATER_THAN: "exceeded",
            ThresholdOperator.GREATER_THAN_OR_EQUAL: "reached or exceeded",
            ThresholdOperator.LESS_THAN: "dropped below",
            ThresholdOperator.LESS_THAN_OR_EQUAL: "reached or dropped below",
            ThresholdOperator.EQUAL: "equals",
            ThresholdOperator.NOT_EQUAL: "no longer equals",
        }

        message = (
            f"{threshold.metric_name} {operator_desc.get(threshold.operator, 'violated')} "
            f"threshold: {current_value} (threshold: {threshold.value})"
        )

        alert = Alert(
            id=alert_id,
            threshold_id=threshold.id,
            metric_name=threshold.metric_name,
            current_value=current_value,
            threshold_value=threshold.value,
            operator=threshold.operator,
            severity=threshold.severity,
            message=message,
            tenant_id=tenant_id,
            config_id=config_id or threshold.config_id,
            notification_channels=threshold.channels
        )

        self._active_alerts[alert_id] = alert
        self._alert_history.append(alert)

        logger.warning(
            f"Alert triggered: {alert.message} "
            f"(severity: {alert.severity.value}, tenant: {tenant_id})"
        )

        return alert

    async def _send_notifications(self, alert: Alert) -> None:
        """
        Send notifications through all configured channels.

        Validates Requirements: 10.3
        """
        tenant_config = self._channel_configs.get(alert.tenant_id)
        if not tenant_config:
            logger.warning(f"No channel config for tenant {alert.tenant_id}")
            return

        notification_tasks = []

        for channel in alert.notification_channels:
            if channel == AlertChannel.EMAIL and tenant_config.email:
                notification_tasks.append(
                    self._send_email_notification(alert, tenant_config.email)
                )
            elif channel == AlertChannel.WEBHOOK and tenant_config.webhook:
                notification_tasks.append(
                    self._send_webhook_notification(alert, tenant_config.webhook)
                )
            elif channel == AlertChannel.SMS and tenant_config.sms:
                notification_tasks.append(
                    self._send_sms_notification(alert, tenant_config.sms)
                )

        if notification_tasks:
            results = await asyncio.gather(*notification_tasks, return_exceptions=True)

            success_count = sum(1 for r in results if r is True)
            if success_count > 0:
                alert.notification_sent = True
                logger.info(
                    f"Sent {success_count}/{len(notification_tasks)} notifications "
                    f"for alert {alert.id}"
                )

    async def _send_email_notification(
        self,
        alert: Alert,
        config: EmailConfig
    ) -> bool:
        """Send email notification."""
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.metric_name} Alert"
            msg['From'] = config.from_address
            msg['To'] = ', '.join(config.to_addresses)

            body = f"""
Alert Details:
- Metric: {alert.metric_name}
- Current Value: {alert.current_value}
- Threshold: {alert.threshold_value}
- Severity: {alert.severity.value}
- Message: {alert.message}
- Time: {alert.triggered_at.isoformat()}
- Tenant: {alert.tenant_id}
"""
            msg.attach(MIMEText(body, 'plain'))

            await aiosmtplib.send(
                msg,
                hostname=config.smtp_host,
                port=config.smtp_port,
                username=config.smtp_user,
                password=config.smtp_password,
                use_tls=config.use_tls
            )

            logger.info(f"Email notification sent for alert {alert.id}")
            return True

        except ImportError:
            logger.warning("aiosmtplib not installed, email notifications disabled")
            return False

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    async def _send_webhook_notification(
        self,
        alert: Alert,
        config: WebhookConfig
    ) -> bool:
        """Send webhook notification."""
        payload = {
            "alert_id": alert.id,
            "threshold_id": alert.threshold_id,
            "metric_name": alert.metric_name,
            "current_value": alert.current_value,
            "threshold_value": alert.threshold_value,
            "operator": alert.operator.value,
            "severity": alert.severity.value,
            "message": alert.message,
            "tenant_id": alert.tenant_id,
            "config_id": alert.config_id,
            "triggered_at": alert.triggered_at.isoformat()
        }

        headers = {
            "Content-Type": "application/json",
            **config.headers
        }

        for attempt in range(config.retry_count):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=config.method,
                        url=config.url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=config.timeout)
                    ) as response:
                        if response.status < 400:
                            logger.info(f"Webhook notification sent for alert {alert.id}")
                            return True
                        else:
                            logger.warning(
                                f"Webhook returned {response.status}, "
                                f"attempt {attempt + 1}/{config.retry_count}"
                            )

            except Exception as e:
                logger.warning(
                    f"Webhook attempt {attempt + 1}/{config.retry_count} failed: {e}"
                )

            # Wait before retry with exponential backoff
            if attempt < config.retry_count - 1:
                await asyncio.sleep(2 ** attempt)

        logger.error(f"Failed to send webhook notification after {config.retry_count} attempts")
        return False

    async def _send_sms_notification(
        self,
        alert: Alert,
        config: SMSConfig
    ) -> bool:
        """Send SMS notification."""
        message = f"[{alert.severity.value.upper()}] {alert.metric_name}: {alert.message}"

        try:
            if config.provider.lower() == "twilio":
                return await self._send_twilio_sms(config, message)
            elif config.provider.lower() in ["alibaba", "aliyun"]:
                return await self._send_alibaba_sms(config, message)
            elif config.provider.lower() == "tencent":
                return await self._send_tencent_sms(config, message)
            else:
                logger.warning(f"Unsupported SMS provider: {config.provider}")
                return False

        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            return False

    async def _send_twilio_sms(self, config: SMSConfig, message: str) -> bool:
        """Send SMS via Twilio."""
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{config.api_key}/Messages.json"

            async with aiohttp.ClientSession() as session:
                for to_number in config.to_numbers:
                    async with session.post(
                        url,
                        data={
                            "From": config.from_number,
                            "To": to_number,
                            "Body": message[:160]  # SMS length limit
                        },
                        auth=aiohttp.BasicAuth(config.api_key, config.api_secret or ""),
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status >= 400:
                            logger.warning(f"Twilio SMS to {to_number} failed: {response.status}")

            logger.info("Twilio SMS notifications sent")
            return True

        except Exception as e:
            logger.error(f"Twilio SMS error: {e}")
            return False

    async def _send_alibaba_sms(self, config: SMSConfig, message: str) -> bool:
        """Send SMS via Alibaba Cloud."""
        # Placeholder for Alibaba Cloud SMS integration
        logger.info("Alibaba SMS notification requested (not implemented)")
        return False

    async def _send_tencent_sms(self, config: SMSConfig, message: str) -> bool:
        """Send SMS via Tencent Cloud."""
        # Placeholder for Tencent Cloud SMS integration
        logger.info("Tencent SMS notification requested (not implemented)")
        return False

    async def _call_alert_handlers(self, alert: Alert) -> None:
        """Call all registered alert handlers."""
        for handler in self._alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a callback handler for alerts."""
        self._alert_handlers.append(handler)
        logger.info(f"Added alert handler: {handler.__name__}")

    def remove_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Remove a callback handler."""
        if handler in self._alert_handlers:
            self._alert_handlers.remove(handler)
            logger.info(f"Removed alert handler: {handler.__name__}")

    async def configure_channels(
        self,
        tenant_id: str,
        config: ChannelConfig
    ) -> None:
        """
        Configure notification channels for a tenant.

        Args:
            tenant_id: Tenant ID
            config: Channel configuration
        """
        async with self._lock:
            self._channel_configs[tenant_id] = config
            logger.info(f"Configured alert channels for tenant {tenant_id}")

    async def get_active_alerts(self, tenant_id: str) -> List[Alert]:
        """Get all active (unresolved) alerts for a tenant."""
        async with self._lock:
            return [
                a for a in self._active_alerts.values()
                if a.tenant_id == tenant_id and a.resolved_at is None
            ]

    async def get_alert_history(
        self,
        tenant_id: str,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get alert history for a tenant."""
        async with self._lock:
            alerts = [a for a in self._alert_history if a.tenant_id == tenant_id]

            if severity:
                alerts = [a for a in alerts if a.severity == severity]

            # Sort by triggered time, most recent first
            alerts.sort(key=lambda a: a.triggered_at, reverse=True)

            return alerts[:limit]

    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> Optional[Alert]:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            acknowledged_by: User who acknowledged

        Returns:
            Updated alert or None if not found
        """
        async with self._lock:
            if alert_id not in self._active_alerts:
                return None

            alert = self._active_alerts[alert_id]
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by

            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return alert

    async def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID

        Returns:
            Resolved alert or None if not found
        """
        async with self._lock:
            if alert_id not in self._active_alerts:
                return None

            alert = self._active_alerts[alert_id]
            alert.resolved_at = datetime.utcnow()

            # Move from active to resolved (keep in history)
            del self._active_alerts[alert_id]

            logger.info(f"Alert {alert_id} resolved")
            return alert

    async def get_alert_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get alert statistics for a tenant."""
        async with self._lock:
            tenant_alerts = [a for a in self._alert_history if a.tenant_id == tenant_id]
            active_alerts = [a for a in self._active_alerts.values() if a.tenant_id == tenant_id]

            # Count by severity
            by_severity = {}
            for severity in AlertSeverity:
                by_severity[severity.value] = len(
                    [a for a in tenant_alerts if a.severity == severity]
                )

            # Count by metric
            by_metric: Dict[str, int] = {}
            for alert in tenant_alerts:
                by_metric[alert.metric_name] = by_metric.get(alert.metric_name, 0) + 1

            # Time-based stats
            now = datetime.utcnow()
            last_24h = [
                a for a in tenant_alerts
                if (now - a.triggered_at).total_seconds() < 86400
            ]
            last_7d = [
                a for a in tenant_alerts
                if (now - a.triggered_at).total_seconds() < 604800
            ]

            return {
                "total_alerts": len(tenant_alerts),
                "active_alerts": len(active_alerts),
                "resolved_alerts": len(tenant_alerts) - len(active_alerts),
                "by_severity": by_severity,
                "by_metric": by_metric,
                "last_24h": len(last_24h),
                "last_7d": len(last_7d),
                "threshold_count": len([
                    t for t in self._thresholds.values() if t.tenant_id == tenant_id
                ])
            }

    async def cleanup_old_alerts(self, days: int = 30) -> int:
        """
        Clean up alerts older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of alerts cleaned up
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        async with self._lock:
            old_count = len(self._alert_history)
            self._alert_history = [
                a for a in self._alert_history
                if a.triggered_at > cutoff
            ]
            cleaned = old_count - len(self._alert_history)

            # Also clean dedup cache
            old_dedup_keys = [
                k for k, v in self._dedup_cache.items()
                if v < cutoff
            ]
            for key in old_dedup_keys:
                del self._dedup_cache[key]

            logger.info(f"Cleaned up {cleaned} old alerts")
            return cleaned
