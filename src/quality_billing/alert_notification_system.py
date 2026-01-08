"""
告警通知和处理系统

提供多渠道告警通知、告警确认和处理机制、告警统计和分析功能。
支持邮件、钉钉、企业微信、短信、Webhook等多种通知渠道。
"""

import logging
import asyncio
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import requests
from collections import defaultdict, deque

from .intelligent_alert_system import Alert, AlertLevel, AlertDimension, AlertStatus

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """通知渠道"""
    EMAIL = "email"
    WECHAT_WORK = "wechat_work"      # 企业微信
    DINGTALK = "dingtalk"            # 钉钉
    SMS = "sms"                      # 短信
    WEBHOOK = "webhook"              # Webhook
    SLACK = "slack"                  # Slack
    TEAMS = "teams"                  # Microsoft Teams
    INTERNAL = "internal"            # 内部通知


class NotificationStatus(str, Enum):
    """通知状态"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    READ = "read"


class NotificationPriority(int, Enum):
    """通知优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class NotificationTemplate:
    """通知模板"""
    id: str
    name: str
    channel: NotificationChannel
    alert_level: AlertLevel
    subject_template: str
    body_template: str
    format_type: str = "text"  # text, html, markdown
    enabled: bool = True
    
    def render_subject(self, alert: Alert, context: Dict[str, Any] = None) -> str:
        """渲染主题"""
        template_vars = {
            "alert_id": str(alert.id),
            "alert_title": alert.title,
            "alert_level": alert.level.value,
            "alert_dimension": alert.dimension.value,
            "alert_source": alert.source,
            "metric_name": alert.metric_name or "",
            "metric_value": alert.metric_value or "",
            "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            **(context or {})
        }
        
        try:
            return self.subject_template.format(**template_vars)
        except KeyError as e:
            logger.warning(f"Template variable missing: {e}")
            return self.subject_template
    
    def render_body(self, alert: Alert, context: Dict[str, Any] = None) -> str:
        """渲染内容"""
        template_vars = {
            "alert_id": str(alert.id),
            "alert_title": alert.title,
            "alert_message": alert.message,
            "alert_level": alert.level.value,
            "alert_dimension": alert.dimension.value,
            "alert_source": alert.source,
            "alert_priority": alert.priority.value,
            "metric_name": alert.metric_name or "",
            "metric_value": alert.metric_value or "",
            "threshold_value": alert.threshold_value or "",
            "tenant_id": alert.tenant_id or "",
            "project_id": alert.project_id or "",
            "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "context": json.dumps(alert.context, indent=2, ensure_ascii=False),
            **(context or {})
        }
        
        try:
            return self.body_template.format(**template_vars)
        except KeyError as e:
            logger.warning(f"Template variable missing: {e}")
            return self.body_template


@dataclass
class NotificationRecord:
    """通知记录"""
    id: UUID
    alert_id: UUID
    channel: NotificationChannel
    recipient: str
    subject: str
    content: str
    status: NotificationStatus = NotificationStatus.PENDING
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
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
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata
        }


class EmailNotificationHandler:
    """邮件通知处理器"""
    
    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_host = smtp_config.get("host", "localhost")
        self.smtp_port = smtp_config.get("port", 587)
        self.smtp_username = smtp_config.get("username")
        self.smtp_password = smtp_config.get("password")
        self.smtp_use_tls = smtp_config.get("use_tls", True)
        self.from_email = smtp_config.get("from_email", "noreply@superinsight.com")
        self.from_name = smtp_config.get("from_name", "SuperInsight Alert System")
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """发送邮件通知"""
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = record.recipient
            msg["Subject"] = record.subject
            
            # 添加邮件内容
            if record.metadata.get("format") == "html":
                msg.attach(MIMEText(record.content, "html", "utf-8"))
            else:
                msg.attach(MIMEText(record.content, "plain", "utf-8"))
            
            # 发送邮件
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
    """企业微信通知处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_key = config.get("webhook_key")
        self.corp_id = config.get("corp_id")
        self.corp_secret = config.get("corp_secret")
        self.agent_id = config.get("agent_id")
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """发送企业微信通知"""
        if not self.webhook_key:
            record.status = NotificationStatus.FAILED
            record.error_message = "WeChat Work webhook key not configured"
            return False
        
        try:
            # 格式化消息
            level_emoji = {
                "info": "ℹ️",
                "warning": "⚠️",
                "high": "🔴",
                "critical": "🚨",
                "emergency": "🆘"
            }
            
            # 获取告警级别对应的emoji
            alert_level = record.metadata.get("alert_level", "info")
            emoji = level_emoji.get(alert_level, "📢")
            
            # 构建Markdown消息
            content = f"{emoji} **{record.subject}**\n\n{record.content}"
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }
            
            # 发送请求
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
    """钉钉通知处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("webhook_url")
        self.secret = config.get("secret")
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """发送钉钉通知"""
        if not self.webhook_url:
            record.status = NotificationStatus.FAILED
            record.error_message = "DingTalk webhook URL not configured"
            return False
        
        try:
            # 构建消息
            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"{record.subject}\n\n{record.content}"
                }
            }
            
            # 如果配置了密钥，需要计算签名
            if self.secret:
                import time
                import hmac
                import hashlib
                import base64
                import urllib.parse
                
                timestamp = str(round(time.time() * 1000))
                secret_enc = self.secret.encode('utf-8')
                string_to_sign = f'{timestamp}\n{self.secret}'
                string_to_sign_enc = string_to_sign.encode('utf-8')
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                
                webhook_url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
            else:
                webhook_url = self.webhook_url
            
            # 发送请求
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


class WebhookNotificationHandler:
    """Webhook通知处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("url")
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 30)
    
    async def send_notification(self, record: NotificationRecord) -> bool:
        """发送Webhook通知"""
        if not self.webhook_url:
            record.status = NotificationStatus.FAILED
            record.error_message = "Webhook URL not configured"
            return False
        
        try:
            # 构建payload
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
            
            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
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


class AlertNotificationSystem:
    """告警通知系统"""
    
    def __init__(self):
        self.templates: Dict[str, NotificationTemplate] = {}
        self.handlers: Dict[NotificationChannel, Any] = {}
        self.notification_records: Dict[UUID, NotificationRecord] = {}
        self.notification_queue: deque = deque()
        
        # 通知配置
        self.notification_configs: Dict[str, Dict[str, Any]] = {}
        
        # 限流配置
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.rate_limit_counters: Dict[str, deque] = defaultdict(lambda: deque())
        
        # 初始化默认模板
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """初始化默认通知模板"""
        # 邮件模板
        self.add_template(NotificationTemplate(
            id="email_critical",
            name="邮件-严重告警",
            channel=NotificationChannel.EMAIL,
            alert_level=AlertLevel.CRITICAL,
            subject_template="[严重告警] {alert_title}",
            body_template="""
告警详情：

告警ID: {alert_id}
告警标题: {alert_title}
告警级别: {alert_level}
告警维度: {alert_dimension}
告警来源: {alert_source}
告警时间: {created_at}

告警消息:
{alert_message}

指标信息:
- 指标名称: {metric_name}
- 当前值: {metric_value}
- 阈值: {threshold_value}

项目信息:
- 租户ID: {tenant_id}
- 项目ID: {project_id}

请及时处理此告警。

---
SuperInsight 告警系统
            """.strip(),
            format_type="text"
        ))
        
        # 企业微信模板
        self.add_template(NotificationTemplate(
            id="wechat_warning",
            name="企业微信-警告告警",
            channel=NotificationChannel.WECHAT_WORK,
            alert_level=AlertLevel.WARNING,
            subject_template="⚠️ {alert_title}",
            body_template="""
**告警级别**: {alert_level}
**告警维度**: {alert_dimension}
**告警来源**: {alert_source}
**告警时间**: {created_at}

**告警消息**:
{alert_message}

**指标信息**:
- 指标: {metric_name}
- 当前值: {metric_value}
- 阈值: {threshold_value}
            """.strip(),
            format_type="markdown"
        ))
        
        logger.info("Initialized default notification templates")
    
    def configure_email_handler(self, config: Dict[str, Any]):
        """配置邮件处理器"""
        self.handlers[NotificationChannel.EMAIL] = EmailNotificationHandler(config)
        logger.info("Configured email notification handler")
    
    def configure_wechat_work_handler(self, config: Dict[str, Any]):
        """配置企业微信处理器"""
        self.handlers[NotificationChannel.WECHAT_WORK] = WeChatWorkNotificationHandler(config)
        logger.info("Configured WeChat Work notification handler")
    
    def configure_dingtalk_handler(self, config: Dict[str, Any]):
        """配置钉钉处理器"""
        self.handlers[NotificationChannel.DINGTALK] = DingTalkNotificationHandler(config)
        logger.info("Configured DingTalk notification handler")
    
    def configure_webhook_handler(self, config: Dict[str, Any]):
        """配置Webhook处理器"""
        self.handlers[NotificationChannel.WEBHOOK] = WebhookNotificationHandler(config)
        logger.info("Configured webhook notification handler")
    
    def add_template(self, template: NotificationTemplate):
        """添加通知模板"""
        self.templates[template.id] = template
        logger.info(f"Added notification template: {template.id}")
    
    def add_notification_config(
        self,
        config_name: str,
        channel: NotificationChannel,
        recipients: List[str],
        alert_levels: List[AlertLevel] = None,
        alert_dimensions: List[AlertDimension] = None,
        template_id: Optional[str] = None,
        enabled: bool = True
    ):
        """添加通知配置"""
        self.notification_configs[config_name] = {
            "channel": channel,
            "recipients": recipients,
            "alert_levels": alert_levels or list(AlertLevel),
            "alert_dimensions": alert_dimensions or list(AlertDimension),
            "template_id": template_id,
            "enabled": enabled
        }
        logger.info(f"Added notification config: {config_name}")
    
    def set_rate_limit(
        self,
        channel: NotificationChannel,
        max_notifications: int,
        time_window_minutes: int
    ):
        """设置限流规则"""
        self.rate_limits[channel.value] = {
            "max_notifications": max_notifications,
            "time_window_minutes": time_window_minutes
        }
        logger.info(f"Set rate limit for {channel.value}: {max_notifications} per {time_window_minutes} minutes")
    
    def _check_rate_limit(self, channel: NotificationChannel, recipient: str) -> bool:
        """检查限流"""
        rate_limit = self.rate_limits.get(channel.value)
        if not rate_limit:
            return True
        
        key = f"{channel.value}:{recipient}"
        now = datetime.now()
        window = timedelta(minutes=rate_limit["time_window_minutes"])
        
        # 清理过期记录
        counter = self.rate_limit_counters[key]
        while counter and now - counter[0] > window:
            counter.popleft()
        
        # 检查是否超限
        if len(counter) >= rate_limit["max_notifications"]:
            logger.warning(f"Rate limit exceeded for {key}")
            return False
        
        # 记录当前通知
        counter.append(now)
        return True
    
    async def send_alert_notifications(self, alert: Alert) -> List[NotificationRecord]:
        """发送告警通知"""
        notifications = []
        
        for config_name, config in self.notification_configs.items():
            if not config["enabled"]:
                continue
            
            # 检查告警级别匹配
            if alert.level not in config["alert_levels"]:
                continue
            
            # 检查告警维度匹配
            if alert.dimension not in config["alert_dimensions"]:
                continue
            
            # 获取处理器
            handler = self.handlers.get(config["channel"])
            if not handler:
                logger.warning(f"No handler configured for channel: {config['channel']}")
                continue
            
            # 为每个接收者创建通知
            for recipient in config["recipients"]:
                # 检查限流
                if not self._check_rate_limit(config["channel"], recipient):
                    continue
                
                # 创建通知记录
                notification = await self._create_notification_record(
                    alert, config["channel"], recipient, config.get("template_id")
                )
                
                if notification:
                    notifications.append(notification)
                    self.notification_queue.append(notification)
        
        # 异步发送通知
        asyncio.create_task(self._process_notification_queue())
        
        return notifications
    
    async def _create_notification_record(
        self,
        alert: Alert,
        channel: NotificationChannel,
        recipient: str,
        template_id: Optional[str] = None
    ) -> Optional[NotificationRecord]:
        """创建通知记录"""
        try:
            # 选择模板
            template = None
            if template_id:
                template = self.templates.get(template_id)
            
            if not template:
                # 查找匹配的默认模板
                for t in self.templates.values():
                    if t.channel == channel and t.alert_level == alert.level and t.enabled:
                        template = t
                        break
            
            if not template:
                logger.warning(f"No template found for channel {channel} and level {alert.level}")
                return None
            
            # 渲染模板
            subject = template.render_subject(alert)
            content = template.render_body(alert)
            
            # 创建通知记录
            notification = NotificationRecord(
                id=uuid4(),
                alert_id=alert.id,
                channel=channel,
                recipient=recipient,
                subject=subject,
                content=content,
                priority=self._map_alert_to_notification_priority(alert.level),
                metadata={
                    "template_id": template.id,
                    "alert_level": alert.level.value,
                    "alert_dimension": alert.dimension.value,
                    "format": template.format_type
                }
            )
            
            self.notification_records[notification.id] = notification
            return notification
            
        except Exception as e:
            logger.error(f"Failed to create notification record: {e}")
            return None
    
    def _map_alert_to_notification_priority(self, alert_level: AlertLevel) -> NotificationPriority:
        """映射告警级别到通知优先级"""
        mapping = {
            AlertLevel.INFO: NotificationPriority.LOW,
            AlertLevel.WARNING: NotificationPriority.NORMAL,
            AlertLevel.HIGH: NotificationPriority.HIGH,
            AlertLevel.CRITICAL: NotificationPriority.URGENT,
            AlertLevel.EMERGENCY: NotificationPriority.URGENT
        }
        return mapping.get(alert_level, NotificationPriority.NORMAL)
    
    async def _process_notification_queue(self):
        """处理通知队列"""
        while self.notification_queue:
            notification = self.notification_queue.popleft()
            
            try:
                handler = self.handlers.get(notification.channel)
                if handler:
                    success = await handler.send_notification(notification)
                    if not success and notification.retry_count < notification.max_retries:
                        # 重试
                        notification.retry_count += 1
                        await asyncio.sleep(2 ** notification.retry_count)  # 指数退避
                        self.notification_queue.append(notification)
                else:
                    notification.status = NotificationStatus.FAILED
                    notification.error_message = f"No handler for channel: {notification.channel}"
                    
            except Exception as e:
                logger.error(f"Error processing notification {notification.id}: {e}")
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)
    
    def get_notification_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取通知统计"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_notifications = [
            n for n in self.notification_records.values()
            if n.created_at >= cutoff
        ]
        
        # 按渠道统计
        by_channel = defaultdict(int)
        for notification in recent_notifications:
            by_channel[notification.channel.value] += 1
        
        # 按状态统计
        by_status = defaultdict(int)
        for notification in recent_notifications:
            by_status[notification.status.value] += 1
        
        # 成功率统计
        total_sent = len([n for n in recent_notifications if n.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED]])
        success_rate = (total_sent / len(recent_notifications)) * 100 if recent_notifications else 0
        
        return {
            "period_days": days,
            "total_notifications": len(recent_notifications),
            "by_channel": dict(by_channel),
            "by_status": dict(by_status),
            "success_rate": round(success_rate, 2),
            "generated_at": datetime.now().isoformat()
        }
    
    def get_notification_record(self, notification_id: UUID) -> Optional[Dict[str, Any]]:
        """获取通知记录"""
        record = self.notification_records.get(notification_id)
        return record.to_dict() if record else None
    
    def list_notification_records(
        self,
        alert_id: Optional[UUID] = None,
        channel: Optional[NotificationChannel] = None,
        status: Optional[NotificationStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """列出通知记录"""
        records = list(self.notification_records.values())
        
        if alert_id:
            records = [r for r in records if r.alert_id == alert_id]
        
        if channel:
            records = [r for r in records if r.channel == channel]
        
        if status:
            records = [r for r in records if r.status == status]
        
        # 按创建时间倒序排序
        records.sort(key=lambda x: x.created_at, reverse=True)
        
        return [record.to_dict() for record in records[:limit]]