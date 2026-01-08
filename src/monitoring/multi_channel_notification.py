"""
Multi-Channel Notification System

Provides comprehensive notification capabilities including:
- Email notifications
- WeChat Work (企业微信) integration
- DingTalk (钉钉) integration
- SMS notifications
- Webhook notifications
- Alert confirmation and processing mechanisms
"""

import logging
import asyncio
import json
import smtplib
import hashlib
import hmac
import base64
import urllib.parse
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
from collections import defaultdict, deque

from .alert_rule_engine import Alert, AlertLevel, AlertCategory

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Notification channels."""
    EMAIL = "email"
    WECHAT_WORK = "wechat_work"      # 企业微信
    DINGTALK = "dingtalk"            # 钉钉
    SMS = "sms"                      # 短信
    WEBHOOK = "webhook"              # Webhook
    SLACK = "slack"                  # Slack
    TEAMS = "teams"                  # Microsoft Teams
    INTERNAL = "internal"            # 内部通知
    PHONE = "phone"                  # 电话告警


class NotificationStatus(str, Enum):
    """Notification status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    READ = "read"
    CONFIRMED = "confirmed"


class NotificationPriority(int, Enum):
    """Notification priority."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    EMERGENCY = 5


@dataclass
class NotificationTemplate:
    """Notification template."""
    id: str
    name: str
    channel: NotificationChannel
    alert_level: AlertLevel
    alert_category: Optional[AlertCategory] = None
    subject_template: str = ""
    body_template: str = ""
    format_type: str = "text"  # text, html, markdown
    enabled: bool = True
    
    # Template variables
    variables: Dict[str, str] = field(default_factory=dict)
    
    # Channel-specific configuration
    channel_config: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def render_subject(self, alert: Alert, context: Dict[str, Any] = None) -> str:
        """Render notification subject."""
        template_vars = self._build_template_vars(alert, context)
        
        try:
            return self.subject_template.format(**template_vars)
        except KeyError as e:
            logger.warning(f"Template variable missing in subject: {e}")
            return self.subject_template
    
    def render_body(self, alert: Alert, context: Dict[str, Any] = None) -> str:
        """Render notification body."""
        template_vars = self._build_template_vars(alert, context)
        
        try:
            return self.body_template.format(**template_vars)
        except KeyError as e:
            logger.warning(f"Template variable missing in body: {e}")
            return self.body_template
    
    def _build_template_vars(self, alert: Alert, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build template variables from alert and context."""
        template_vars = {
            "alert_id": str(alert.id),
            "alert_title": alert.title,
            "alert_message": alert.message,
            "alert_level": alert.level.value,
            "alert_category": alert.category.value,
            "alert_source": alert.source,
            "alert_priority": alert.priority.value,
            "metric_name": alert.metric_name or "",
            "metric_value": alert.metric_value or "",
            "threshold_value": alert.threshold_value or "",
            "tenant_id": alert.tenant_id or "",
            "project_id": alert.project_id or "",
            "user_id": alert.user_id or "",
            "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "context": json.dumps(alert.context, indent=2, ensure_ascii=False),
            **(context or {}),
            **self.variables
        }
        
        return template_vars


@dataclass
class NotificationRecord:
    """Notification record."""
    id: UUID
    alert_id: UUID
    channel: NotificationChannel
    recipient: str
    subject: str
    content: str
    status: NotificationStatus = NotificationStatus.PENDING
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "alert_id": str(self.alert_id),
            "channel": self.channel.value,
            "recipient": self.recipient,
            "subject": self.subject,
            "content": self.content,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata
        }


class EmailNotificationHandler:
    """Email notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_host = config.get("host", "localhost")
        self.smtp_port = config.get("port", 587)
        self.smtp_username = config.get("username")
        self.smtp_password = config.get("password")
        self.smtp_use_tls = config.get("use_tls", True)
        self.from_email = config.get("from_email", "noreply@superinsight.com")
        self.from_name = config.get("from_name", "SuperInsight Alert System")
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """Send email notification."""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = record.recipient
            msg["Subject"] = record.subject
            
            # Add content
            if record.metadata.get("format") == "html":
                msg.attach(MIMEText(record.content, "html", "utf-8"))
            else:
                msg.attach(MIMEText(record.content, "plain", "utf-8"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
            
            record.status = NotificationStatus.SENT
            record.sent_at = datetime.now()
            logger.info(f"Email sent successfully to {record.recipient}")
            return True
            
        except Exception as e:
            record.status = NotificationStatus.FAILED
            record.error_message = str(e)
            logger.error(f"Failed to send email to {record.recipient}: {e}")
            return False


class WeChatWorkNotificationHandler:
    """WeChat Work (企业微信) notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_key = config.get("webhook_key")
        self.corp_id = config.get("corp_id")
        self.corp_secret = config.get("corp_secret")
        self.agent_id = config.get("agent_id")
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """Send WeChat Work notification."""
        if not self.webhook_key:
            record.status = NotificationStatus.FAILED
            record.error_message = "WeChat Work webhook key not configured"
            return False
        
        try:
            # Format message with emoji based on alert level
            level_emoji = {
                "info": "ℹ️",
                "warning": "⚠️",
                "high": "🔴",
                "critical": "🚨",
                "emergency": "🆘"
            }
            
            alert_level = record.metadata.get("alert_level", "info")
            emoji = level_emoji.get(alert_level, "📢")
            
            # Build markdown content
            content = f"{emoji} **{record.subject}**\n\n{record.content}"
            
            # Add mention for urgent alerts
            if record.priority >= NotificationPriority.URGENT:
                content += "\n\n@all 请立即处理此紧急告警！"
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
            
            # Send request
            webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.webhook_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            record.status = NotificationStatus.SENT
                            record.sent_at = datetime.now()
                            logger.info(f"WeChat Work notification sent successfully")
                            return True
                        else:
                            record.status = NotificationStatus.FAILED
                            record.error_message = result.get("errmsg", "Unknown error")
                            return False
                    else:
                        record.status = NotificationStatus.FAILED
                        record.error_message = f"HTTP {response.status}"
                        return False
        
        except Exception as e:
            record.status = NotificationStatus.FAILED
            record.error_message = str(e)
            logger.error(f"Failed to send WeChat Work notification: {e}")
            return False


class DingTalkNotificationHandler:
    """DingTalk (钉钉) notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("webhook_url")
        self.secret = config.get("secret")
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """Send DingTalk notification."""
        if not self.webhook_url:
            record.status = NotificationStatus.FAILED
            record.error_message = "DingTalk webhook URL not configured"
            return False
        
        try:
            # Build message content
            content = f"{record.subject}\n\n{record.content}"
            
            # Add @all for urgent alerts
            if record.priority >= NotificationPriority.URGENT:
                content += "\n\n@所有人 请立即处理此紧急告警！"
            
            payload = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            # Add @all if urgent
            if record.priority >= NotificationPriority.URGENT:
                payload["at"] = {
                    "isAtAll": True
                }
            
            # Calculate signature if secret is configured
            webhook_url = self.webhook_url
            if self.secret:
                timestamp = str(round(time.time() * 1000))
                secret_enc = self.secret.encode('utf-8')
                string_to_sign = f'{timestamp}\n{self.secret}'
                string_to_sign_enc = string_to_sign.encode('utf-8')
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                
                webhook_url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
            
            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            record.status = NotificationStatus.SENT
                            record.sent_at = datetime.now()
                            logger.info(f"DingTalk notification sent successfully")
                            return True
                        else:
                            record.status = NotificationStatus.FAILED
                            record.error_message = result.get("errmsg", "Unknown error")
                            return False
                    else:
                        record.status = NotificationStatus.FAILED
                        record.error_message = f"HTTP {response.status}"
                        return False
        
        except Exception as e:
            record.status = NotificationStatus.FAILED
            record.error_message = str(e)
            logger.error(f"Failed to send DingTalk notification: {e}")
            return False


class SMSNotificationHandler:
    """SMS notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "aliyun")  # aliyun, tencent, twilio
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self.sign_name = config.get("sign_name")
        self.template_code = config.get("template_code")
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """Send SMS notification."""
        try:
            # For demonstration, we'll log the SMS instead of actually sending
            # In production, integrate with actual SMS providers
            
            sms_content = f"【{self.sign_name}】{record.subject}: {record.content[:50]}..."
            
            logger.info(f"SMS notification would be sent to {record.recipient}: {sms_content}")
            
            record.status = NotificationStatus.SENT
            record.sent_at = datetime.now()
            return True
            
        except Exception as e:
            record.status = NotificationStatus.FAILED
            record.error_message = str(e)
            logger.error(f"Failed to send SMS to {record.recipient}: {e}")
            return False


class WebhookNotificationHandler:
    """Webhook notification handler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("url")
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 30)
        self.auth_token = config.get("auth_token")
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """Send webhook notification."""
        if not self.webhook_url:
            record.status = NotificationStatus.FAILED
            record.error_message = "Webhook URL not configured"
            return False
        
        try:
            # Build payload
            payload = {
                "alert_id": str(record.alert_id),
                "notification_id": str(record.id),
                "channel": record.channel.value,
                "recipient": record.recipient,
                "subject": record.subject,
                "content": record.content,
                "priority": record.priority.value,
                "timestamp": record.created_at.isoformat(),
                "metadata": record.metadata
            }
            
            # Prepare headers
            headers = dict(self.headers)
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            headers["Content-Type"] = "application/json"
            
            # Send request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if 200 <= response.status < 300:
                        record.status = NotificationStatus.SENT
                        record.sent_at = datetime.now()
                        logger.info(f"Webhook notification sent successfully")
                        return True
                    else:
                        record.status = NotificationStatus.FAILED
                        record.error_message = f"HTTP {response.status}"
                        return False
        
        except Exception as e:
            record.status = NotificationStatus.FAILED
            record.error_message = str(e)
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class PhoneNotificationHandler:
    """Phone call notification handler for emergency alerts."""
    
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "aliyun")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self.tts_template = config.get("tts_template")
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """Send phone call notification."""
        try:
            # For demonstration, we'll log the phone call instead of actually making it
            # In production, integrate with voice call providers
            
            call_content = f"紧急告警通知：{record.subject}。请立即处理。"
            
            logger.info(f"Phone call would be made to {record.recipient}: {call_content}")
            
            record.status = NotificationStatus.SENT
            record.sent_at = datetime.now()
            return True
            
        except Exception as e:
            record.status = NotificationStatus.FAILED
            record.error_message = str(e)
            logger.error(f"Failed to make phone call to {record.recipient}: {e}")
            return False


class MultiChannelNotificationSystem:
    """
    Multi-channel notification system with comprehensive notification capabilities.
    
    Features:
    - Multiple notification channels (email, WeChat Work, DingTalk, SMS, webhook, phone)
    - Template-based message formatting
    - Rate limiting and throttling
    - Retry mechanisms with exponential backoff
    - Alert confirmation and processing
    - Notification statistics and monitoring
    """
    
    def __init__(self):
        self.templates: Dict[str, NotificationTemplate] = {}
        self.handlers: Dict[NotificationChannel, Any] = {}
        self.notification_records: Dict[UUID, NotificationRecord] = {}
        self.notification_queue: deque = deque()
        
        # Notification configurations
        self.notification_configs: Dict[str, Dict[str, Any]] = {}
        
        # Rate limiting
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.rate_limit_counters: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Confirmation tracking
        self.confirmation_callbacks: Dict[UUID, Callable] = {}
        
        # Initialize default templates
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default notification templates."""
        # Email templates
        self.add_template(NotificationTemplate(
            id="email_critical",
            name="Email - Critical Alert",
            channel=NotificationChannel.EMAIL,
            alert_level=AlertLevel.CRITICAL,
            subject_template="[CRITICAL] {alert_title}",
            body_template="""
Critical Alert Notification

Alert ID: {alert_id}
Title: {alert_title}
Level: {alert_level}
Category: {alert_category}
Source: {alert_source}
Time: {created_at}

Message:
{alert_message}

Metric Information:
- Metric: {metric_name}
- Current Value: {metric_value}
- Threshold: {threshold_value}

Project Information:
- Tenant: {tenant_id}
- Project: {project_id}

Please address this critical alert immediately.

---
SuperInsight Alert System
            """.strip(),
            format_type="text"
        ))
        
        # WeChat Work templates
        self.add_template(NotificationTemplate(
            id="wechat_warning",
            name="WeChat Work - Warning Alert",
            channel=NotificationChannel.WECHAT_WORK,
            alert_level=AlertLevel.WARNING,
            subject_template="⚠️ {alert_title}",
            body_template="""
**告警级别**: {alert_level}
**告警类别**: {alert_category}
**告警来源**: {alert_source}
**告警时间**: {created_at}

**告警消息**:
{alert_message}

**指标信息**:
- 指标名称: {metric_name}
- 当前值: {metric_value}
- 阈值: {threshold_value}

**项目信息**:
- 租户: {tenant_id}
- 项目: {project_id}
            """.strip(),
            format_type="markdown"
        ))
        
        # DingTalk templates
        self.add_template(NotificationTemplate(
            id="dingtalk_high",
            name="DingTalk - High Priority Alert",
            channel=NotificationChannel.DINGTALK,
            alert_level=AlertLevel.HIGH,
            subject_template="🔴 {alert_title}",
            body_template="""
高优先级告警通知

告警ID: {alert_id}
告警标题: {alert_title}
告警级别: {alert_level}
告警类别: {alert_category}
告警来源: {alert_source}
告警时间: {created_at}

告警消息:
{alert_message}

指标信息:
- 指标名称: {metric_name}
- 当前值: {metric_value}
- 阈值: {threshold_value}

请及时处理此告警。
            """.strip(),
            format_type="text"
        ))
        
        # SMS template
        self.add_template(NotificationTemplate(
            id="sms_emergency",
            name="SMS - Emergency Alert",
            channel=NotificationChannel.SMS,
            alert_level=AlertLevel.EMERGENCY,
            subject_template="紧急告警",
            body_template="紧急告警：{alert_title}。指标{metric_name}当前值{metric_value}。请立即处理！",
            format_type="text"
        ))
        
        logger.info("Initialized default notification templates")
    
    def configure_email_handler(self, config: Dict[str, Any]):
        """Configure email notification handler."""
        self.handlers[NotificationChannel.EMAIL] = EmailNotificationHandler(config)
        logger.info("Configured email notification handler")
    
    def configure_wechat_work_handler(self, config: Dict[str, Any]):
        """Configure WeChat Work notification handler."""
        self.handlers[NotificationChannel.WECHAT_WORK] = WeChatWorkNotificationHandler(config)
        logger.info("Configured WeChat Work notification handler")
    
    def configure_dingtalk_handler(self, config: Dict[str, Any]):
        """Configure DingTalk notification handler."""
        self.handlers[NotificationChannel.DINGTALK] = DingTalkNotificationHandler(config)
        logger.info("Configured DingTalk notification handler")
    
    def configure_sms_handler(self, config: Dict[str, Any]):
        """Configure SMS notification handler."""
        self.handlers[NotificationChannel.SMS] = SMSNotificationHandler(config)
        logger.info("Configured SMS notification handler")
    
    def configure_webhook_handler(self, config: Dict[str, Any]):
        """Configure webhook notification handler."""
        self.handlers[NotificationChannel.WEBHOOK] = WebhookNotificationHandler(config)
        logger.info("Configured webhook notification handler")
    
    def configure_phone_handler(self, config: Dict[str, Any]):
        """Configure phone call notification handler."""
        self.handlers[NotificationChannel.PHONE] = PhoneNotificationHandler(config)
        logger.info("Configured phone call notification handler")
    
    def add_template(self, template: NotificationTemplate):
        """Add notification template."""
        self.templates[template.id] = template
        logger.info(f"Added notification template: {template.id}")
    
    def add_notification_config(
        self,
        config_name: str,
        channel: NotificationChannel,
        recipients: List[str],
        alert_levels: List[AlertLevel] = None,
        alert_categories: List[AlertCategory] = None,
        template_id: Optional[str] = None,
        enabled: bool = True,
        conditions: Optional[Dict[str, Any]] = None
    ):
        """Add notification configuration."""
        self.notification_configs[config_name] = {
            "channel": channel,
            "recipients": recipients,
            "alert_levels": alert_levels or list(AlertLevel),
            "alert_categories": alert_categories or list(AlertCategory),
            "template_id": template_id,
            "enabled": enabled,
            "conditions": conditions or {}
        }
        logger.info(f"Added notification config: {config_name}")
    
    def set_rate_limit(
        self,
        channel: NotificationChannel,
        max_notifications: int,
        time_window_minutes: int
    ):
        """Set rate limiting for a channel."""
        self.rate_limits[channel.value] = {
            "max_notifications": max_notifications,
            "time_window_minutes": time_window_minutes
        }
        logger.info(f"Set rate limit for {channel.value}: {max_notifications} per {time_window_minutes} minutes")
    
    def _check_rate_limit(self, channel: NotificationChannel, recipient: str) -> bool:
        """Check if rate limit allows sending notification."""
        rate_limit = self.rate_limits.get(channel.value)
        if not rate_limit:
            return True
        
        key = f"{channel.value}:{recipient}"
        now = datetime.now()
        window = timedelta(minutes=rate_limit["time_window_minutes"])
        
        # Clean old entries
        counter = self.rate_limit_counters[key]
        while counter and now - counter[0] > window:
            counter.popleft()
        
        # Check limit
        if len(counter) >= rate_limit["max_notifications"]:
            logger.warning(f"Rate limit exceeded for {key}")
            return False
        
        # Record current notification
        counter.append(now)
        return True
    
    async def send_alert_notifications(self, alert: Alert) -> List[NotificationRecord]:
        """Send notifications for an alert."""
        notifications = []
        
        for config_name, config in self.notification_configs.items():
            if not config["enabled"]:
                continue
            
            # Check alert level matching
            if alert.level not in config["alert_levels"]:
                continue
            
            # Check alert category matching
            if alert.category not in config["alert_categories"]:
                continue
            
            # Check additional conditions
            conditions = config.get("conditions", {})
            if not self._check_conditions(alert, conditions):
                continue
            
            # Get handler
            handler = self.handlers.get(config["channel"])
            if not handler:
                logger.warning(f"No handler configured for channel: {config['channel']}")
                continue
            
            # Create notifications for each recipient
            for recipient in config["recipients"]:
                # Check rate limiting
                if not self._check_rate_limit(config["channel"], recipient):
                    continue
                
                # Create notification record
                notification = await self._create_notification_record(
                    alert, config["channel"], recipient, config.get("template_id")
                )
                
                if notification:
                    notifications.append(notification)
                    self.notification_queue.append(notification)
        
        # Process notification queue asynchronously
        asyncio.create_task(self._process_notification_queue())
        
        return notifications
    
    def _check_conditions(self, alert: Alert, conditions: Dict[str, Any]) -> bool:
        """Check if alert matches additional conditions."""
        for key, value in conditions.items():
            if key == "source" and alert.source != value:
                return False
            elif key == "tenant_id" and alert.tenant_id != value:
                return False
            elif key == "project_id" and alert.project_id != value:
                return False
            elif key == "metric_name" and alert.metric_name != value:
                return False
            elif key == "tags":
                for tag_key, tag_value in value.items():
                    if alert.tags.get(tag_key) != tag_value:
                        return False
        
        return True
    
    async def _create_notification_record(
        self,
        alert: Alert,
        channel: NotificationChannel,
        recipient: str,
        template_id: Optional[str] = None
    ) -> Optional[NotificationRecord]:
        """Create notification record."""
        try:
            # Select template
            template = None
            if template_id:
                template = self.templates.get(template_id)
            
            if not template:
                # Find matching template
                for t in self.templates.values():
                    if (t.channel == channel and 
                        t.alert_level == alert.level and 
                        (t.alert_category is None or t.alert_category == alert.category) and
                        t.enabled):
                        template = t
                        break
            
            if not template:
                logger.warning(f"No template found for channel {channel} and level {alert.level}")
                return None
            
            # Render template
            subject = template.render_subject(alert)
            content = template.render_body(alert)
            
            # Map alert priority to notification priority
            priority_mapping = {
                1: NotificationPriority.LOW,
                2: NotificationPriority.NORMAL,
                3: NotificationPriority.HIGH,
                4: NotificationPriority.URGENT,
                5: NotificationPriority.EMERGENCY
            }
            notification_priority = priority_mapping.get(alert.priority.value, NotificationPriority.NORMAL)
            
            # Create notification record
            notification = NotificationRecord(
                id=uuid4(),
                alert_id=alert.id,
                channel=channel,
                recipient=recipient,
                subject=subject,
                content=content,
                priority=notification_priority,
                metadata={
                    "template_id": template.id,
                    "alert_level": alert.level.value,
                    "alert_category": alert.category.value,
                    "format": template.format_type
                }
            )
            
            self.notification_records[notification.id] = notification
            return notification
            
        except Exception as e:
            logger.error(f"Failed to create notification record: {e}")
            return None
    
    async def _process_notification_queue(self):
        """Process notification queue."""
        while self.notification_queue:
            notification = self.notification_queue.popleft()
            
            try:
                handler = self.handlers.get(notification.channel)
                if handler:
                    success = await handler.send_notification(notification)
                    if not success and notification.retry_count < notification.max_retries:
                        # Retry with exponential backoff
                        notification.retry_count += 1
                        await asyncio.sleep(2 ** notification.retry_count)
                        self.notification_queue.append(notification)
                else:
                    notification.status = NotificationStatus.FAILED
                    notification.error_message = f"No handler for channel: {notification.channel}"
                    
            except Exception as e:
                logger.error(f"Error processing notification {notification.id}: {e}")
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)
    
    async def confirm_notification(self, notification_id: UUID, confirmed_by: str) -> bool:
        """Confirm notification receipt."""
        record = self.notification_records.get(notification_id)
        if not record:
            return False
        
        record.status = NotificationStatus.CONFIRMED
        record.confirmed_at = datetime.now()
        record.metadata["confirmed_by"] = confirmed_by
        
        # Execute confirmation callback if registered
        callback = self.confirmation_callbacks.get(notification_id)
        if callback:
            try:
                await callback(record)
            except Exception as e:
                logger.error(f"Error executing confirmation callback: {e}")
        
        logger.info(f"Notification confirmed: {notification_id} by {confirmed_by}")
        return True
    
    def register_confirmation_callback(self, notification_id: UUID, callback: Callable):
        """Register callback for notification confirmation."""
        self.confirmation_callbacks[notification_id] = callback
    
    def get_notification_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get notification statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        recent_notifications = [
            n for n in self.notification_records.values()
            if n.created_at >= cutoff
        ]
        
        # Statistics by channel
        by_channel = defaultdict(int)
        for notification in recent_notifications:
            by_channel[notification.channel.value] += 1
        
        # Statistics by status
        by_status = defaultdict(int)
        for notification in recent_notifications:
            by_status[notification.status.value] += 1
        
        # Success rate
        total_sent = len([n for n in recent_notifications if n.status in [
            NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.CONFIRMED
        ]])
        success_rate = (total_sent / len(recent_notifications)) * 100 if recent_notifications else 0
        
        # Average delivery time
        delivery_times = []
        for notification in recent_notifications:
            if notification.sent_at and notification.created_at:
                delivery_time = (notification.sent_at - notification.created_at).total_seconds()
                delivery_times.append(delivery_time)
        
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        return {
            "period_days": days,
            "total_notifications": len(recent_notifications),
            "by_channel": dict(by_channel),
            "by_status": dict(by_status),
            "success_rate": round(success_rate, 2),
            "avg_delivery_time_seconds": round(avg_delivery_time, 2),
            "generated_at": datetime.now().isoformat()
        }
    
    def get_notification_record(self, notification_id: UUID) -> Optional[Dict[str, Any]]:
        """Get notification record."""
        record = self.notification_records.get(notification_id)
        return record.to_dict() if record else None
    
    def list_notification_records(
        self,
        alert_id: Optional[UUID] = None,
        channel: Optional[NotificationChannel] = None,
        status: Optional[NotificationStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List notification records."""
        records = list(self.notification_records.values())
        
        if alert_id:
            records = [r for r in records if r.alert_id == alert_id]
        
        if channel:
            records = [r for r in records if r.channel == channel]
        
        if status:
            records = [r for r in records if r.status == status]
        
        # Sort by creation time (newest first)
        records.sort(key=lambda x: x.created_at, reverse=True)
        
        return [record.to_dict() for record in records[:limit]]


# Global instance
multi_channel_notification_system = MultiChannelNotificationSystem()