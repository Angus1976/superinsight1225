"""
Real-time Security Alert System for SuperInsight Platform.

Provides comprehensive real-time alerting capabilities for security events,
including multiple notification channels, alert aggregation, and escalation.
"""

import asyncio
import logging
import json
import smtplib
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib

from src.security.security_event_monitor import SecurityEvent, SecurityEventType, ThreatLevel


class AlertChannel(Enum):
    """告警通道类型"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH_NOTIFICATION = "push_notification"
    SYSTEM_LOG = "system_log"


class AlertPriority(Enum):
    """告警优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """告警状态"""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FAILED = "failed"


@dataclass
class AlertRule:
    """告警规则配置"""
    rule_id: str
    name: str
    description: str
    event_types: List[SecurityEventType]
    threat_levels: List[ThreatLevel]
    channels: List[AlertChannel]
    priority: AlertPriority
    enabled: bool = True
    cooldown_minutes: int = 5  # 冷却时间，避免重复告警
    escalation_minutes: int = 30  # 升级时间
    conditions: Dict[str, Any] = field(default_factory=dict)
    recipients: List[str] = field(default_factory=list)


@dataclass
class AlertNotification:
    """告警通知"""
    notification_id: str
    alert_id: str
    rule_id: str
    channel: AlertChannel
    recipient: str
    subject: str
    message: str
    priority: AlertPriority
    created_at: datetime
    sent_at: Optional[datetime] = None
    status: AlertStatus = AlertStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None


@dataclass
class AlertAggregation:
    """告警聚合"""
    aggregation_id: str
    rule_id: str
    event_count: int
    first_event_time: datetime
    last_event_time: datetime
    events: List[SecurityEvent] = field(default_factory=list)
    notifications_sent: List[AlertNotification] = field(default_factory=list)


class AlertChannelHandler:
    """告警通道处理器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def send_notification(
        self,
        recipient: str,
        subject: str,
        message: str,
        priority: AlertPriority,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """发送通知，返回是否成功"""
        raise NotImplementedError


class EmailAlertHandler(AlertChannelHandler):
    """邮件告警处理器"""
    
    async def send_notification(
        self,
        recipient: str,
        subject: str,
        message: str,
        priority: AlertPriority,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """发送邮件通知"""
        
        try:
            # 配置SMTP服务器
            smtp_server = self.config.get('smtp_server', 'localhost')
            smtp_port = self.config.get('smtp_port', 587)
            username = self.config.get('username')
            password = self.config.get('password')
            sender_email = self.config.get('sender_email', username)
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = f"[{priority.value.upper()}] {subject}"
            
            # 添加优先级标识
            if priority in [AlertPriority.CRITICAL, AlertPriority.EMERGENCY]:
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
            
            # 邮件正文
            body = f"""
安全告警通知

优先级: {priority.value.upper()}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{message}

---
SuperInsight 安全监控系统
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 发送邮件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if username and password:
                    server.starttls()
                    server.login(username, password)
                
                server.send_message(msg)
            
            self.logger.info(f"Email alert sent to {recipient}: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert to {recipient}: {e}")
            return False


class SlackAlertHandler(AlertChannelHandler):
    """Slack告警处理器"""
    
    async def send_notification(
        self,
        recipient: str,
        subject: str,
        message: str,
        priority: AlertPriority,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """发送Slack通知"""
        
        try:
            webhook_url = self.config.get('webhook_url')
            if not webhook_url:
                self.logger.error("Slack webhook URL not configured")
                return False
            
            # 根据优先级设置颜色
            color_map = {
                AlertPriority.LOW: "#36a64f",      # 绿色
                AlertPriority.MEDIUM: "#ff9500",   # 橙色
                AlertPriority.HIGH: "#ff0000",     # 红色
                AlertPriority.CRITICAL: "#8b0000", # 深红色
                AlertPriority.EMERGENCY: "#ff1493" # 深粉色
            }
            
            # 构建Slack消息
            payload = {
                "channel": recipient,
                "username": "SuperInsight Security",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": color_map.get(priority, "#ff0000"),
                        "title": f"🚨 安全告警 - {priority.value.upper()}",
                        "text": subject,
                        "fields": [
                            {
                                "title": "详细信息",
                                "value": message,
                                "short": False
                            },
                            {
                                "title": "时间",
                                "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "short": True
                            },
                            {
                                "title": "优先级",
                                "value": priority.value.upper(),
                                "short": True
                            }
                        ],
                        "footer": "SuperInsight 安全监控系统",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # 发送到Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Slack alert sent to {recipient}: {subject}")
                        return True
                    else:
                        self.logger.error(f"Slack API error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert to {recipient}: {e}")
            return False


class WebhookAlertHandler(AlertChannelHandler):
    """Webhook告警处理器"""
    
    async def send_notification(
        self,
        recipient: str,
        subject: str,
        message: str,
        priority: AlertPriority,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """发送Webhook通知"""
        
        try:
            # recipient 是 webhook URL
            webhook_url = recipient
            
            # 构建webhook payload
            payload = {
                "alert_type": "security_event",
                "priority": priority.value,
                "subject": subject,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # 发送webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 201, 202]:
                        self.logger.info(f"Webhook alert sent to {webhook_url}: {subject}")
                        return True
                    else:
                        self.logger.error(f"Webhook error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert to {recipient}: {e}")
            return False


class SystemLogAlertHandler(AlertChannelHandler):
    """系统日志告警处理器"""
    
    async def send_notification(
        self,
        recipient: str,
        subject: str,
        message: str,
        priority: AlertPriority,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """记录到系统日志"""
        
        try:
            log_message = f"SECURITY ALERT [{priority.value.upper()}] {subject}: {message}"
            
            if priority == AlertPriority.EMERGENCY:
                self.logger.critical(log_message)
            elif priority == AlertPriority.CRITICAL:
                self.logger.error(log_message)
            elif priority == AlertPriority.HIGH:
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log alert: {e}")
            return False


class RealTimeAlertSystem:
    """实时告警系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 告警规则
        self.alert_rules: Dict[str, AlertRule] = {}
        
        # 通道处理器
        self.channel_handlers: Dict[AlertChannel, AlertChannelHandler] = {}
        
        # 告警历史和状态
        self.pending_notifications: deque = deque(maxlen=10000)
        self.sent_notifications: List[AlertNotification] = []
        self.alert_aggregations: Dict[str, AlertAggregation] = {}
        
        # 冷却时间跟踪
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        # 运行状态
        self.running = False
        self.notification_task: Optional[asyncio.Task] = None
        
        # 初始化通道处理器
        self._initialize_channel_handlers()
        
        # 初始化默认规则
        self._initialize_default_rules()
    
    def _initialize_channel_handlers(self):
        """初始化通道处理器"""
        
        # 邮件处理器
        email_config = self.config.get('email', {})
        if email_config.get('enabled', False):
            self.channel_handlers[AlertChannel.EMAIL] = EmailAlertHandler(email_config)
        
        # Slack处理器
        slack_config = self.config.get('slack', {})
        if slack_config.get('enabled', False):
            self.channel_handlers[AlertChannel.SLACK] = SlackAlertHandler(slack_config)
        
        # Webhook处理器
        webhook_config = self.config.get('webhook', {})
        if webhook_config.get('enabled', False):
            self.channel_handlers[AlertChannel.WEBHOOK] = WebhookAlertHandler(webhook_config)
        
        # 系统日志处理器（总是启用）
        self.channel_handlers[AlertChannel.SYSTEM_LOG] = SystemLogAlertHandler({})
    
    def _initialize_default_rules(self):
        """初始化默认告警规则"""
        
        # 关键威胁告警
        self.add_alert_rule(AlertRule(
            rule_id="critical_threats",
            name="关键威胁告警",
            description="检测到关键级别的安全威胁时立即告警",
            event_types=[
                SecurityEventType.BRUTE_FORCE_ATTACK,
                SecurityEventType.PRIVILEGE_ESCALATION,
                SecurityEventType.DATA_EXFILTRATION
            ],
            threat_levels=[ThreatLevel.CRITICAL, ThreatLevel.HIGH],
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SYSTEM_LOG],
            priority=AlertPriority.CRITICAL,
            cooldown_minutes=1,  # 关键威胁冷却时间短
            escalation_minutes=15,
            recipients=self.config.get('critical_alert_recipients', ['admin@example.com'])
        ))
        
        # 异常行为告警
        self.add_alert_rule(AlertRule(
            rule_id="anomalous_behavior",
            name="异常行为告警",
            description="检测到异常用户行为时告警",
            event_types=[
                SecurityEventType.ANOMALOUS_BEHAVIOR,
                SecurityEventType.SUSPICIOUS_ACTIVITY
            ],
            threat_levels=[ThreatLevel.MEDIUM, ThreatLevel.HIGH],
            channels=[AlertChannel.EMAIL, AlertChannel.SYSTEM_LOG],
            priority=AlertPriority.MEDIUM,
            cooldown_minutes=10,
            escalation_minutes=60,
            recipients=self.config.get('security_alert_recipients', ['security@example.com'])
        ))
        
        # 认证失败告警
        self.add_alert_rule(AlertRule(
            rule_id="authentication_failures",
            name="认证失败告警",
            description="检测到大量认证失败时告警",
            event_types=[SecurityEventType.AUTHENTICATION_FAILURE],
            threat_levels=[ThreatLevel.MEDIUM, ThreatLevel.HIGH],
            channels=[AlertChannel.SYSTEM_LOG],
            priority=AlertPriority.LOW,
            cooldown_minutes=15,
            escalation_minutes=120,
            recipients=self.config.get('auth_alert_recipients', ['admin@example.com'])
        ))
    
    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.alert_rules[rule.rule_id] = rule
        self.logger.info(f"Added alert rule: {rule.name} ({rule.rule_id})")
    
    def remove_alert_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self.alert_rules:
            rule = self.alert_rules.pop(rule_id)
            self.logger.info(f"Removed alert rule: {rule.name} ({rule_id})")
    
    def enable_alert_rule(self, rule_id: str):
        """启用告警规则"""
        if rule_id in self.alert_rules:
            self.alert_rules[rule_id].enabled = True
            self.logger.info(f"Enabled alert rule: {rule_id}")
    
    def disable_alert_rule(self, rule_id: str):
        """禁用告警规则"""
        if rule_id in self.alert_rules:
            self.alert_rules[rule_id].enabled = False
            self.logger.info(f"Disabled alert rule: {rule_id}")
    
    async def process_security_event(self, event: SecurityEvent):
        """处理安全事件，生成告警"""
        
        # 检查匹配的告警规则
        matching_rules = self._find_matching_rules(event)
        
        for rule in matching_rules:
            if not rule.enabled:
                continue
            
            # 检查冷却时间
            cooldown_key = f"{rule.rule_id}_{event.tenant_id}_{event.event_type.value}"
            if self._is_in_cooldown(cooldown_key, rule.cooldown_minutes):
                continue
            
            # 生成告警
            await self._generate_alert(event, rule)
            
            # 设置冷却时间
            self.alert_cooldowns[cooldown_key] = datetime.now()
    
    def _find_matching_rules(self, event: SecurityEvent) -> List[AlertRule]:
        """查找匹配的告警规则"""
        
        matching_rules = []
        
        for rule in self.alert_rules.values():
            # 检查事件类型匹配
            if event.event_type not in rule.event_types:
                continue
            
            # 检查威胁等级匹配
            if event.threat_level not in rule.threat_levels:
                continue
            
            # 检查其他条件
            if not self._check_rule_conditions(event, rule):
                continue
            
            matching_rules.append(rule)
        
        return matching_rules
    
    def _check_rule_conditions(self, event: SecurityEvent, rule: AlertRule) -> bool:
        """检查规则条件"""
        
        conditions = rule.conditions
        
        # 检查租户条件
        if 'tenant_ids' in conditions:
            if event.tenant_id not in conditions['tenant_ids']:
                return False
        
        # 检查用户条件
        if 'user_ids' in conditions and event.user_id:
            if str(event.user_id) not in conditions['user_ids']:
                return False
        
        # 检查IP条件
        if 'ip_patterns' in conditions and event.ip_address:
            import re
            patterns = conditions['ip_patterns']
            if not any(re.match(pattern, event.ip_address) for pattern in patterns):
                return False
        
        return True
    
    def _is_in_cooldown(self, cooldown_key: str, cooldown_minutes: int) -> bool:
        """检查是否在冷却时间内"""
        
        if cooldown_key not in self.alert_cooldowns:
            return False
        
        last_alert_time = self.alert_cooldowns[cooldown_key]
        cooldown_period = timedelta(minutes=cooldown_minutes)
        
        return datetime.now() - last_alert_time < cooldown_period
    
    async def _generate_alert(self, event: SecurityEvent, rule: AlertRule):
        """生成告警通知"""
        
        alert_id = self._generate_alert_id(event, rule)
        
        # 构建告警消息
        subject = f"安全告警: {event.event_type.value} - {event.threat_level.value}"
        message = self._build_alert_message(event, rule)
        
        # 为每个通道和接收者创建通知
        for channel in rule.channels:
            if channel not in self.channel_handlers:
                self.logger.warning(f"Channel handler not available: {channel}")
                continue
            
            for recipient in rule.recipients:
                notification = AlertNotification(
                    notification_id=self._generate_notification_id(),
                    alert_id=alert_id,
                    rule_id=rule.rule_id,
                    channel=channel,
                    recipient=recipient,
                    subject=subject,
                    message=message,
                    priority=rule.priority,
                    created_at=datetime.now()
                )
                
                self.pending_notifications.append(notification)
        
        self.logger.info(f"Generated alert for event {event.event_id} using rule {rule.rule_id}")
    
    def _build_alert_message(self, event: SecurityEvent, rule: AlertRule) -> str:
        """构建告警消息"""
        
        message = f"""
安全事件详情:

事件ID: {event.event_id}
事件类型: {event.event_type.value}
威胁等级: {event.threat_level.value}
租户ID: {event.tenant_id}
用户ID: {event.user_id or 'N/A'}
IP地址: {event.ip_address or 'N/A'}
发生时间: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

描述: {event.description}

详细信息:
"""
        
        # 添加事件详情
        for key, value in event.details.items():
            message += f"- {key}: {value}\n"
        
        message += f"""
告警规则: {rule.name}
优先级: {rule.priority.value}

请及时处理此安全事件。
        """
        
        return message.strip()
    
    def _generate_alert_id(self, event: SecurityEvent, rule: AlertRule) -> str:
        """生成告警ID"""
        content = f"{event.event_id}_{rule.rule_id}_{datetime.now().isoformat()}"
        return f"ALERT_{hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]}"
    
    def _generate_notification_id(self) -> str:
        """生成通知ID"""
        content = f"{datetime.now().isoformat()}_{id(self)}"
        return f"NOTIF_{hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]}"
    
    async def start_notification_processing(self):
        """启动通知处理"""
        
        if self.running:
            return
        
        self.running = True
        self.notification_task = asyncio.create_task(self._notification_processing_loop())
        self.logger.info("Real-time alert system started")
    
    async def stop_notification_processing(self):
        """停止通知处理"""
        
        self.running = False
        
        if self.notification_task:
            self.notification_task.cancel()
            try:
                await self.notification_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Real-time alert system stopped")
    
    async def _notification_processing_loop(self):
        """通知处理循环"""
        
        while self.running:
            try:
                # 处理待发送的通知
                await self._process_pending_notifications()
                
                # 检查需要重试的通知
                await self._retry_failed_notifications()
                
                # 清理过期数据
                await self._cleanup_old_data()
                
                # 等待下次处理
                await asyncio.sleep(5)  # 5秒处理间隔
                
            except Exception as e:
                self.logger.error(f"Notification processing error: {e}")
                await asyncio.sleep(10)
    
    async def _process_pending_notifications(self):
        """处理待发送的通知"""
        
        batch_size = 10  # 批量处理
        processed = 0
        
        while self.pending_notifications and processed < batch_size:
            notification = self.pending_notifications.popleft()
            
            try:
                # 获取通道处理器
                handler = self.channel_handlers.get(notification.channel)
                if not handler:
                    notification.status = AlertStatus.FAILED
                    notification.error_message = f"Handler not available for channel: {notification.channel}"
                    self.sent_notifications.append(notification)
                    continue
                
                # 发送通知
                success = await handler.send_notification(
                    recipient=notification.recipient,
                    subject=notification.subject,
                    message=notification.message,
                    priority=notification.priority,
                    metadata={
                        'alert_id': notification.alert_id,
                        'rule_id': notification.rule_id,
                        'notification_id': notification.notification_id
                    }
                )
                
                # 更新通知状态
                notification.sent_at = datetime.now()
                if success:
                    notification.status = AlertStatus.SENT
                else:
                    notification.status = AlertStatus.FAILED
                    notification.retry_count += 1
                
                self.sent_notifications.append(notification)
                processed += 1
                
            except Exception as e:
                notification.status = AlertStatus.FAILED
                notification.error_message = str(e)
                notification.retry_count += 1
                self.sent_notifications.append(notification)
                self.logger.error(f"Failed to process notification {notification.notification_id}: {e}")
    
    async def _retry_failed_notifications(self):
        """重试失败的通知"""
        
        retry_notifications = [
            notif for notif in self.sent_notifications
            if (notif.status == AlertStatus.FAILED and 
                notif.retry_count < notif.max_retries and
                notif.sent_at and 
                datetime.now() - notif.sent_at > timedelta(minutes=5))  # 5分钟后重试
        ]
        
        for notification in retry_notifications:
            # 重新加入待发送队列
            notification.status = AlertStatus.PENDING
            self.pending_notifications.append(notification)
            
            # 从已发送列表中移除
            self.sent_notifications.remove(notification)
    
    async def _cleanup_old_data(self):
        """清理过期数据"""
        
        cutoff_time = datetime.now() - timedelta(days=7)  # 保留7天
        
        # 清理旧的通知记录
        self.sent_notifications = [
            notif for notif in self.sent_notifications
            if notif.created_at > cutoff_time
        ]
        
        # 清理旧的冷却记录
        self.alert_cooldowns = {
            key: timestamp for key, timestamp in self.alert_cooldowns.items()
            if timestamp > cutoff_time
        }
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计信息"""
        
        total_notifications = len(self.sent_notifications)
        successful_notifications = len([
            notif for notif in self.sent_notifications
            if notif.status == AlertStatus.SENT
        ])
        failed_notifications = len([
            notif for notif in self.sent_notifications
            if notif.status == AlertStatus.FAILED
        ])
        
        # 按优先级统计
        priority_stats = defaultdict(int)
        for notif in self.sent_notifications:
            priority_stats[notif.priority.value] += 1
        
        # 按通道统计
        channel_stats = defaultdict(int)
        for notif in self.sent_notifications:
            channel_stats[notif.channel.value] += 1
        
        return {
            'total_notifications': total_notifications,
            'successful_notifications': successful_notifications,
            'failed_notifications': failed_notifications,
            'success_rate': successful_notifications / total_notifications if total_notifications > 0 else 0,
            'pending_notifications': len(self.pending_notifications),
            'active_rules': len([rule for rule in self.alert_rules.values() if rule.enabled]),
            'total_rules': len(self.alert_rules),
            'priority_distribution': dict(priority_stats),
            'channel_distribution': dict(channel_stats),
            'active_cooldowns': len(self.alert_cooldowns)
        }


# 全局实例
real_time_alert_system = RealTimeAlertSystem()


# 便捷函数
async def start_real_time_alerting(config: Dict[str, Any] = None):
    """启动实时告警系统"""
    global real_time_alert_system
    
    if config:
        real_time_alert_system = RealTimeAlertSystem(config)
    
    await real_time_alert_system.start_notification_processing()


async def stop_real_time_alerting():
    """停止实时告警系统"""
    await real_time_alert_system.stop_notification_processing()


async def send_security_alert(event: SecurityEvent):
    """发送安全事件告警"""
    await real_time_alert_system.process_security_event(event)


def get_alert_system() -> RealTimeAlertSystem:
    """获取告警系统实例"""
    return real_time_alert_system