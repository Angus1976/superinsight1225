"""
Intelligent Notification Service for Data Sync System.

Provides multi-channel alert notifications with aggregation, deduplication,
escalation, and intelligent routing.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable, Any
from enum import Enum
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import hashlib

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    TEAMS = "teams"
    DISCORD = "discord"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationRule:
    """Notification routing rule."""
    name: str
    channels: List[NotificationChannel]
    conditions: Dict[str, Any]  # Alert matching conditions
    priority: NotificationPriority = NotificationPriority.NORMAL
    enabled: bool = True
    escalation_delay: Optional[int] = None  # seconds
    max_frequency: Optional[int] = None  # max notifications per hour


@dataclass
class NotificationTemplate:
    """Notification message template."""
    channel: NotificationChannel
    subject_template: str
    body_template: str
    format_type: str = "text"  # text, html, markdown


@dataclass
class PendingNotification:
    """A notification waiting to be sent."""
    id: str
    alert_id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    message: str
    priority: NotificationPriority
    created_at: datetime
    scheduled_at: datetime
    attempts: int = 0
    max_attempts: int = 3


@dataclass
class NotificationHistory:
    """Notification delivery history."""
    notification_id: str
    alert_id: str
    channel: NotificationChannel
    recipient: str
    status: str  # sent, failed, pending
    sent_at: Optional[datetime] = None
    error: Optional[str] = None


class NotificationAggregator:
    """
    Aggregates similar alerts to reduce notification noise.
    """

    def __init__(self, window_seconds: int = 300):  # 5 minutes
        self.window_seconds = window_seconds
        self.alert_groups: Dict[str, List[Dict]] = {}
        self.last_cleanup = datetime.now()

    def add_alert(self, alert: Dict[str, Any]) -> Optional[str]:
        """
        Add alert to aggregation. Returns group key if should be aggregated.
        """
        self._cleanup_old_groups()
        
        group_key = self._get_group_key(alert)
        now = datetime.now()
        
        if group_key not in self.alert_groups:
            self.alert_groups[group_key] = []
        
        # Check if we should aggregate
        group = self.alert_groups[group_key]
        if group:
            # Check if last alert in group is within window
            last_alert_time = datetime.fromisoformat(group[-1]['timestamp'])
            if (now - last_alert_time).total_seconds() <= self.window_seconds:
                group.append({
                    'alert': alert,
                    'timestamp': now.isoformat()
                })
                return group_key
        
        # Start new group
        self.alert_groups[group_key] = [{
            'alert': alert,
            'timestamp': now.isoformat()
        }]
        return None

    def get_aggregated_alerts(self, group_key: str) -> List[Dict]:
        """Get all alerts in a group."""
        return self.alert_groups.get(group_key, [])

    def _get_group_key(self, alert: Dict[str, Any]) -> str:
        """Generate grouping key for alert."""
        # Group by rule name, severity, and similar labels
        key_parts = [
            alert.get('rule_name', ''),
            alert.get('severity', ''),
            alert.get('category', ''),
        ]
        
        # Add relevant labels
        labels = alert.get('labels', {})
        for label in ['connector_type', 'operation', 'instance']:
            if label in labels:
                key_parts.append(f"{label}={labels[label]}")
        
        return hashlib.md5('|'.join(key_parts).encode()).hexdigest()

    def _cleanup_old_groups(self):
        """Remove old alert groups."""
        now = datetime.now()
        if (now - self.last_cleanup).total_seconds() < 60:  # Cleanup every minute
            return
        
        cutoff = now - timedelta(seconds=self.window_seconds * 2)
        
        for group_key in list(self.alert_groups.keys()):
            group = self.alert_groups[group_key]
            if group:
                last_alert_time = datetime.fromisoformat(group[-1]['timestamp'])
                if last_alert_time < cutoff:
                    del self.alert_groups[group_key]
        
        self.last_cleanup = now


class NotificationDeduplicator:
    """
    Prevents duplicate notifications within a time window.
    """

    def __init__(self, window_seconds: int = 3600):  # 1 hour
        self.window_seconds = window_seconds
        self.sent_notifications: Dict[str, datetime] = {}

    def should_send(self, alert_id: str, recipient: str, channel: NotificationChannel) -> bool:
        """Check if notification should be sent (not a duplicate)."""
        key = f"{alert_id}:{recipient}:{channel.value}"
        now = datetime.now()
        
        if key in self.sent_notifications:
            last_sent = self.sent_notifications[key]
            if (now - last_sent).total_seconds() < self.window_seconds:
                return False
        
        self.sent_notifications[key] = now
        return True

    def mark_sent(self, alert_id: str, recipient: str, channel: NotificationChannel):
        """Mark notification as sent."""
        key = f"{alert_id}:{recipient}:{channel.value}"
        self.sent_notifications[key] = datetime.now()


class NotificationEscalator:
    """
    Handles notification escalation based on acknowledgment and time.
    """

    def __init__(self):
        self.escalation_rules: Dict[str, List[Dict]] = {}
        self.pending_escalations: Dict[str, datetime] = {}

    def add_escalation_rule(
        self,
        alert_pattern: str,
        escalation_chain: List[Dict[str, Any]]
    ):
        """
        Add escalation rule.
        
        escalation_chain format:
        [
            {"delay": 300, "channels": ["email"], "recipients": ["team@company.com"]},
            {"delay": 900, "channels": ["slack", "sms"], "recipients": ["manager@company.com"]}
        ]
        """
        self.escalation_rules[alert_pattern] = escalation_chain

    def schedule_escalation(self, alert_id: str, rule_name: str):
        """Schedule escalation for an alert."""
        if rule_name in self.escalation_rules:
            self.pending_escalations[alert_id] = datetime.now()

    def get_due_escalations(self) -> List[Dict[str, Any]]:
        """Get escalations that are due."""
        now = datetime.now()
        due_escalations = []
        
        for alert_id, start_time in list(self.pending_escalations.items()):
            # Find matching escalation rule
            for pattern, chain in self.escalation_rules.items():
                for step in chain:
                    delay = step.get('delay', 0)
                    if (now - start_time).total_seconds() >= delay:
                        due_escalations.append({
                            'alert_id': alert_id,
                            'step': step,
                            'pattern': pattern
                        })
        
        return due_escalations

    def acknowledge_alert(self, alert_id: str):
        """Acknowledge alert and stop escalation."""
        if alert_id in self.pending_escalations:
            del self.pending_escalations[alert_id]


class NotificationChannelHandler:
    """Base class for notification channel handlers."""

    async def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
        """Send notification. Returns True if successful."""
        raise NotImplementedError


class EmailHandler(NotificationChannelHandler):
    """Email notification handler."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls

    async def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
        """Send email notification."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'html' if kwargs.get('html') else 'plain'))
            
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_email, msg)
            
            logger.info(f"Email sent to {recipient}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False

    def _send_email(self, msg):
        """Send email synchronously."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)


class SlackHandler(NotificationChannelHandler):
    """Slack notification handler."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
        """Send Slack notification."""
        try:
            payload = {
                "channel": recipient,
                "text": f"*{subject}*\n{message}",
                "username": "Sync Monitor",
                "icon_emoji": ":warning:"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack message sent to {recipient}: {subject}")
                        return True
                    else:
                        logger.error(f"Slack API error: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Slack message to {recipient}: {e}")
            return False


class WebhookHandler(NotificationChannelHandler):
    """Generic webhook notification handler."""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}

    async def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
        """Send webhook notification."""
        try:
            payload = {
                "recipient": recipient,
                "subject": subject,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                **kwargs
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status < 400:
                        logger.info(f"Webhook sent to {recipient}: {subject}")
                        return True
                    else:
                        logger.error(f"Webhook error: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send webhook to {recipient}: {e}")
            return False


class IntelligentNotificationService:
    """
    Intelligent notification service with aggregation, deduplication,
    escalation, and multi-channel support.
    """

    def __init__(self):
        self.handlers: Dict[NotificationChannel, NotificationChannelHandler] = {}
        self.rules: List[NotificationRule] = []
        self.templates: Dict[str, NotificationTemplate] = {}
        
        self.aggregator = NotificationAggregator()
        self.deduplicator = NotificationDeduplicator()
        self.escalator = NotificationEscalator()
        
        self.pending_notifications: List[PendingNotification] = []
        self.notification_history: List[NotificationHistory] = []
        
        self.frequency_limits: Dict[str, List[datetime]] = {}
        
        # Default templates
        self._setup_default_templates()
        
        # Default rules
        self._setup_default_rules()

    def add_handler(self, channel: NotificationChannel, handler: NotificationChannelHandler):
        """Add notification channel handler."""
        self.handlers[channel] = handler
        logger.info(f"Added {channel.value} notification handler")

    def add_rule(self, rule: NotificationRule):
        """Add notification rule."""
        self.rules.append(rule)
        logger.info(f"Added notification rule: {rule.name}")

    def add_template(self, key: str, template: NotificationTemplate):
        """Add notification template."""
        self.templates[key] = template

    async def process_alert(self, alert: Dict[str, Any]):
        """Process an alert and send appropriate notifications."""
        alert_id = alert.get('rule_name', 'unknown')
        
        # Check for aggregation
        group_key = self.aggregator.add_alert(alert)
        if group_key:
            # Alert was aggregated, don't send individual notification
            logger.debug(f"Alert {alert_id} aggregated into group {group_key}")
            return
        
        # Find matching rules
        matching_rules = self._find_matching_rules(alert)
        
        for rule in matching_rules:
            if not rule.enabled:
                continue
            
            # Check frequency limits
            if not self._check_frequency_limit(rule, alert):
                continue
            
            # Generate notifications for each channel
            for channel in rule.channels:
                recipients = self._get_recipients(channel, alert, rule)
                
                for recipient in recipients:
                    # Check deduplication
                    if not self.deduplicator.should_send(alert_id, recipient, channel):
                        logger.debug(f"Skipping duplicate notification to {recipient}")
                        continue
                    
                    # Create notification
                    notification = await self._create_notification(
                        alert, channel, recipient, rule.priority
                    )
                    
                    if notification:
                        self.pending_notifications.append(notification)
                        
                        # Schedule escalation if configured
                        if rule.escalation_delay:
                            self.escalator.schedule_escalation(alert_id, rule.name)

    async def process_aggregated_alerts(self):
        """Process aggregated alerts and send summary notifications."""
        # This would be called periodically to send aggregated notifications
        for group_key, alerts in self.aggregator.alert_groups.items():
            if len(alerts) > 1:  # Only send if multiple alerts
                summary_alert = self._create_summary_alert(alerts)
                await self.process_alert(summary_alert)

    async def process_escalations(self):
        """Process due escalations."""
        due_escalations = self.escalator.get_due_escalations()
        
        for escalation in due_escalations:
            alert_id = escalation['alert_id']
            step = escalation['step']
            
            # Create escalation notification
            escalation_alert = {
                'rule_name': f"escalation_{alert_id}",
                'severity': 'critical',
                'message': f"Alert {alert_id} requires attention - escalating",
                'timestamp': datetime.now().isoformat()
            }
            
            await self.process_alert(escalation_alert)

    async def send_pending_notifications(self):
        """Send all pending notifications."""
        for notification in list(self.pending_notifications):
            success = await self._send_notification(notification)
            
            if success:
                self.pending_notifications.remove(notification)
                self.deduplicator.mark_sent(
                    notification.alert_id,
                    notification.recipient,
                    notification.channel
                )
                
                # Record history
                self.notification_history.append(NotificationHistory(
                    notification_id=notification.id,
                    alert_id=notification.alert_id,
                    channel=notification.channel,
                    recipient=notification.recipient,
                    status="sent",
                    sent_at=datetime.now()
                ))
            else:
                notification.attempts += 1
                if notification.attempts >= notification.max_attempts:
                    self.pending_notifications.remove(notification)
                    
                    # Record failure
                    self.notification_history.append(NotificationHistory(
                        notification_id=notification.id,
                        alert_id=notification.alert_id,
                        channel=notification.channel,
                        recipient=notification.recipient,
                        status="failed",
                        error="Max attempts exceeded"
                    ))

    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert and stop escalation."""
        self.escalator.acknowledge_alert(alert_id)

    def _setup_default_templates(self):
        """Setup default notification templates."""
        # Email template
        self.add_template("email_alert", NotificationTemplate(
            channel=NotificationChannel.EMAIL,
            subject_template="[{severity}] Sync Alert: {rule_name}",
            body_template="""
            <h2>Data Sync System Alert</h2>
            <p><strong>Alert:</strong> {rule_name}</p>
            <p><strong>Severity:</strong> {severity}</p>
            <p><strong>Category:</strong> {category}</p>
            <p><strong>Message:</strong> {message}</p>
            <p><strong>Value:</strong> {value}</p>
            <p><strong>Threshold:</strong> {threshold}</p>
            <p><strong>Time:</strong> {timestamp}</p>
            
            <h3>Labels</h3>
            <ul>
            {labels_html}
            </ul>
            """,
            format_type="html"
        ))
        
        # Slack template
        self.add_template("slack_alert", NotificationTemplate(
            channel=NotificationChannel.SLACK,
            subject_template="{severity} Alert: {rule_name}",
            body_template="""
            :warning: *{rule_name}*
            
            *Severity:* {severity}
            *Category:* {category}
            *Message:* {message}
            *Value:* {value} (threshold: {threshold})
            *Time:* {timestamp}
            
            Labels: {labels_text}
            """,
            format_type="markdown"
        ))

    def _setup_default_rules(self):
        """Setup default notification rules."""
        # Critical alerts - immediate notification
        self.add_rule(NotificationRule(
            name="critical_alerts",
            channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
            conditions={"severity": "critical"},
            priority=NotificationPriority.URGENT,
            escalation_delay=300  # 5 minutes
        ))
        
        # Warning alerts - normal notification
        self.add_rule(NotificationRule(
            name="warning_alerts",
            channels=[NotificationChannel.EMAIL],
            conditions={"severity": "warning"},
            priority=NotificationPriority.NORMAL,
            max_frequency=10  # Max 10 per hour
        ))

    def _find_matching_rules(self, alert: Dict[str, Any]) -> List[NotificationRule]:
        """Find notification rules that match the alert."""
        matching_rules = []
        
        for rule in self.rules:
            if self._rule_matches_alert(rule, alert):
                matching_rules.append(rule)
        
        return matching_rules

    def _rule_matches_alert(self, rule: NotificationRule, alert: Dict[str, Any]) -> bool:
        """Check if a rule matches an alert."""
        for key, expected_value in rule.conditions.items():
            alert_value = alert.get(key)
            
            if isinstance(expected_value, list):
                if alert_value not in expected_value:
                    return False
            else:
                if alert_value != expected_value:
                    return False
        
        return True

    def _check_frequency_limit(self, rule: NotificationRule, alert: Dict[str, Any]) -> bool:
        """Check if notification frequency limit is exceeded."""
        if not rule.max_frequency:
            return True
        
        rule_key = f"{rule.name}:{alert.get('rule_name', '')}"
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        if rule_key not in self.frequency_limits:
            self.frequency_limits[rule_key] = []
        
        # Clean old entries
        self.frequency_limits[rule_key] = [
            ts for ts in self.frequency_limits[rule_key] if ts > hour_ago
        ]
        
        # Check limit
        if len(self.frequency_limits[rule_key]) >= rule.max_frequency:
            return False
        
        # Record this notification
        self.frequency_limits[rule_key].append(now)
        return True

    def _get_recipients(
        self,
        channel: NotificationChannel,
        alert: Dict[str, Any],
        rule: NotificationRule
    ) -> List[str]:
        """Get recipients for a channel based on alert and rule."""
        # This would typically be configured per rule or looked up from a directory
        # For now, return default recipients
        
        if channel == NotificationChannel.EMAIL:
            return ["admin@company.com", "ops-team@company.com"]
        elif channel == NotificationChannel.SLACK:
            return ["#alerts", "#ops-team"]
        else:
            return ["default-recipient"]

    async def _create_notification(
        self,
        alert: Dict[str, Any],
        channel: NotificationChannel,
        recipient: str,
        priority: NotificationPriority
    ) -> Optional[PendingNotification]:
        """Create a notification from an alert."""
        template_key = f"{channel.value}_alert"
        template = self.templates.get(template_key)
        
        if not template:
            logger.warning(f"No template found for {template_key}")
            return None
        
        # Format message
        context = self._create_template_context(alert)
        
        try:
            subject = template.subject_template.format(**context)
            message = template.body_template.format(**context)
            
            notification_id = hashlib.md5(
                f"{alert.get('rule_name', '')}:{recipient}:{datetime.now().isoformat()}".encode()
            ).hexdigest()
            
            return PendingNotification(
                id=notification_id,
                alert_id=alert.get('rule_name', 'unknown'),
                channel=channel,
                recipient=recipient,
                subject=subject,
                message=message,
                priority=priority,
                created_at=datetime.now(),
                scheduled_at=datetime.now()
            )
            
        except KeyError as e:
            logger.error(f"Template formatting error: {e}")
            return None

    def _create_template_context(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Create template context from alert."""
        labels = alert.get('labels', {})
        
        # Format labels for different outputs
        labels_html = '\n'.join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in labels.items())
        labels_text = ', '.join(f"{k}={v}" for k, v in labels.items())
        
        context = {
            'rule_name': alert.get('rule_name', 'Unknown'),
            'severity': alert.get('severity', 'unknown'),
            'category': alert.get('category', 'unknown'),
            'message': alert.get('message', 'No message'),
            'value': alert.get('value', 'N/A'),
            'threshold': alert.get('threshold', 'N/A'),
            'timestamp': alert.get('timestamp', datetime.now().isoformat()),
            'labels_html': labels_html,
            'labels_text': labels_text,
            **labels  # Include individual labels
        }
        
        return context

    def _create_summary_alert(self, alerts: List[Dict]) -> Dict[str, Any]:
        """Create a summary alert from multiple aggregated alerts."""
        if not alerts:
            return {}
        
        first_alert = alerts[0]['alert']
        count = len(alerts)
        
        return {
            'rule_name': f"aggregated_{first_alert.get('rule_name', 'unknown')}",
            'severity': first_alert.get('severity', 'warning'),
            'category': first_alert.get('category', 'unknown'),
            'message': f"{count} similar alerts occurred in the last few minutes",
            'value': count,
            'threshold': 1,
            'timestamp': datetime.now().isoformat(),
            'labels': first_alert.get('labels', {})
        }

    async def _send_notification(self, notification: PendingNotification) -> bool:
        """Send a single notification."""
        handler = self.handlers.get(notification.channel)
        if not handler:
            logger.error(f"No handler for channel {notification.channel}")
            return False
        
        try:
            return await handler.send(
                notification.recipient,
                notification.subject,
                notification.message
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        total_sent = len([h for h in self.notification_history if h.status == "sent"])
        total_failed = len([h for h in self.notification_history if h.status == "failed"])
        pending_count = len(self.pending_notifications)
        
        return {
            "total_sent": total_sent,
            "total_failed": total_failed,
            "pending_count": pending_count,
            "success_rate": total_sent / (total_sent + total_failed) if (total_sent + total_failed) > 0 else 0,
            "active_rules": len([r for r in self.rules if r.enabled])
        }


# Global notification service
notification_service = IntelligentNotificationService()


def setup_email_notifications(
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    from_email: str
):
    """Setup email notifications."""
    handler = EmailHandler(smtp_host, smtp_port, username, password, from_email)
    notification_service.add_handler(NotificationChannel.EMAIL, handler)


def setup_slack_notifications(webhook_url: str):
    """Setup Slack notifications."""
    handler = SlackHandler(webhook_url)
    notification_service.add_handler(NotificationChannel.SLACK, handler)


def setup_webhook_notifications(webhook_url: str, headers: Optional[Dict[str, str]] = None):
    """Setup webhook notifications."""
    handler = WebhookHandler(webhook_url, headers)
    notification_service.add_handler(NotificationChannel.WEBHOOK, handler)


async def start_notification_processor():
    """Start the notification processing loop."""
    while True:
        try:
            await notification_service.send_pending_notifications()
            await notification_service.process_escalations()
            await asyncio.sleep(10)  # Process every 10 seconds
        except Exception as e:
            logger.error(f"Notification processor error: {e}")
            await asyncio.sleep(30)  # Wait longer on error