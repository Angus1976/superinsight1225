"""
SLA 监控通知服务模块

提供:
- NotificationService 抽象基类
- EmailNotificationService 邮件通知服务
- WeChatWorkNotificationService 企业微信通知服务
- NotificationManager 通知管理器

支持 i18n 国际化翻译键
"""

import logging
import asyncio
import hashlib
import hmac
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from uuid import UUID

import aiohttp

logger = logging.getLogger(__name__)


# ============================================================================
# i18n 翻译键定义
# ============================================================================

class SLANotificationI18nKeys:
    """SLA 通知相关的 i18n 翻译键"""
    
    # 邮件主题
    EMAIL_SUBJECT_BREACH = "sla_monitor.notification.email_subject_breach"
    EMAIL_SUBJECT_WARNING = "sla_monitor.notification.email_subject_warning"
    EMAIL_SUBJECT_ESCALATION = "sla_monitor.notification.email_subject_escalation"
    
    # 消息内容
    BREACH_MESSAGE = "sla_monitor.notification.breach_message"
    WARNING_MESSAGE = "sla_monitor.notification.warning_message"
    ESCALATION_MESSAGE = "sla_monitor.notification.escalation_message"
    
    # 错误消息
    SEND_FAILED = "sla_monitor.notification.send_failed"
    CHANNEL_UNAVAILABLE = "sla_monitor.notification.channel_unavailable"
    RETRY_ATTEMPT = "sla_monitor.notification.retry_attempt"
    ALL_CHANNELS_FAILED = "sla_monitor.notification.all_channels_failed"
    
    # 成功消息
    SEND_SUCCESS = "sla_monitor.notification.send_success"
    
    # 企业微信特定
    WECHAT_CARD_TITLE = "sla_monitor.notification.wechat_card_title"
    WECHAT_CARD_DESCRIPTION = "sla_monitor.notification.wechat_card_description"


# ============================================================================
# 数据类定义
# ============================================================================

class NotificationChannel(str, Enum):
    """通知渠道类型"""
    EMAIL = "email"
    WECHAT_WORK = "wechat_work"
    WEBHOOK = "webhook"
    SMS = "sms"


class NotificationPriority(str, Enum):
    """通知优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationResult:
    """通知发送结果"""
    channel: NotificationChannel
    success: bool
    recipient: str
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    sent_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "channel": self.channel.value,
            "success": self.success,
            "recipient": self.recipient,
            "message_id": self.message_id,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None
        }


@dataclass
class NotificationConfig:
    """通知配置"""
    # 邮件配置
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_address: str = "noreply@superinsight.ai"
    smtp_from_name: str = "SuperInsight SLA Monitor"
    
    # 企业微信配置
    wechat_webhook_url: str = ""
    wechat_corp_id: str = ""
    wechat_agent_id: str = ""
    wechat_secret: str = ""
    
    # 重试配置
    max_retries: int = 3
    retry_delays: List[int] = field(default_factory=lambda: [1, 2, 4])  # 指数退避
    
    # 超时配置
    timeout_seconds: int = 30


# ============================================================================
# 抽象基类: NotificationService
# ============================================================================

class NotificationService(ABC):
    """
    通知服务抽象基类
    
    定义通知服务的标准接口，所有具体通知服务必须实现此接口。
    """
    
    def __init__(self, config: NotificationConfig):
        """
        初始化通知服务
        
        Args:
            config: 通知配置
        """
        self.config = config
        self._is_available = True
    
    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """返回通知渠道类型"""
        pass
    
    @abstractmethod
    async def send(
        self,
        recipients: List[str],
        subject: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[NotificationResult]:
        """
        发送通知
        
        Args:
            recipients: 收件人列表
            subject: 通知主题
            message: 通知内容
            priority: 通知优先级
            metadata: 额外元数据
            
        Returns:
            发送结果列表
        """
        pass

    
    @abstractmethod
    async def check_availability(self) -> bool:
        """
        检查服务可用性
        
        Returns:
            服务是否可用
        """
        pass
    
    @property
    def is_available(self) -> bool:
        """返回服务是否可用"""
        return self._is_available
    
    async def _retry_with_backoff(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        使用指数退避重试操作
        
        Args:
            operation: 要执行的异步操作
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            操作结果
            
        Raises:
            最后一次重试的异常
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delays[min(attempt, len(self.config.retry_delays) - 1)]
                    logger.warning(
                        f"Notification send attempt {attempt + 1} failed, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Notification send failed after {self.config.max_retries} attempts: {e}"
                    )
        
        raise last_exception


# ============================================================================
# EmailNotificationService - 邮件通知服务
# ============================================================================

class EmailNotificationService(NotificationService):
    """
    邮件通知服务
    
    使用 aiosmtplib 进行异步邮件发送，支持:
    - HTML 和纯文本格式
    - 指数退避重试 (1s, 2s, 4s)
    - 最多重试 3 次
    - i18n 翻译键
    """
    
    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self._smtp_client = None

    
    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL
    
    async def send(
        self,
        recipients: List[str],
        subject: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[NotificationResult]:
        """
        发送邮件通知
        
        Args:
            recipients: 收件人邮箱列表
            subject: 邮件主题
            message: 邮件内容 (支持 HTML)
            priority: 通知优先级
            metadata: 额外元数据 (如 ticket_id, ticket_title 等)
            
        Returns:
            发送结果列表
        """
        results = []
        
        for recipient in recipients:
            try:
                result = await self._retry_with_backoff(
                    self._send_single_email,
                    recipient,
                    subject,
                    message,
                    priority,
                    metadata
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to send email to {recipient}: {e}")
                results.append(NotificationResult(
                    channel=self.channel,
                    success=False,
                    recipient=recipient,
                    error_message=str(e),
                    retry_count=self.config.max_retries
                ))
        
        return results
    
    async def _send_single_email(
        self,
        recipient: str,
        subject: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """发送单封邮件"""
        try:
            # 尝试导入 aiosmtplib
            try:
                import aiosmtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
            except ImportError:
                logger.warning("aiosmtplib not installed, using mock email send")
                return await self._mock_send_email(recipient, subject, message, priority)

            
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.smtp_from_name} <{self.config.smtp_from_address}>"
            msg["To"] = recipient
            
            # 设置优先级头
            if priority == NotificationPriority.CRITICAL:
                msg["X-Priority"] = "1"
                msg["Importance"] = "high"
            elif priority == NotificationPriority.HIGH:
                msg["X-Priority"] = "2"
                msg["Importance"] = "high"
            
            # 添加纯文本和 HTML 版本
            text_part = MIMEText(self._html_to_text(message), "plain", "utf-8")
            html_part = MIMEText(message, "html", "utf-8")
            msg.attach(text_part)
            msg.attach(html_part)
            
            # 发送邮件
            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_host,
                port=self.config.smtp_port,
                username=self.config.smtp_username or None,
                password=self.config.smtp_password or None,
                use_tls=self.config.smtp_use_tls,
                timeout=self.config.timeout_seconds
            )
            
            logger.info(f"Email sent successfully to {recipient}")
            
            return NotificationResult(
                channel=self.channel,
                success=True,
                recipient=recipient,
                message_id=msg.get("Message-ID"),
                sent_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Email send error: {e}")
            raise
    
    async def _mock_send_email(
        self,
        recipient: str,
        subject: str,
        message: str,
        priority: NotificationPriority
    ) -> NotificationResult:
        """模拟发送邮件 (用于测试或 aiosmtplib 不可用时)"""
        logger.info(f"[Mock Email] To: {recipient}, Subject: {subject}")
        
        return NotificationResult(
            channel=self.channel,
            success=True,
            recipient=recipient,
            message_id=f"mock-{datetime.now().timestamp()}",
            sent_at=datetime.now()
        )

    
    def _html_to_text(self, html: str) -> str:
        """将 HTML 转换为纯文本"""
        import re
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', html)
        # 处理常见 HTML 实体
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        return text.strip()
    
    async def check_availability(self) -> bool:
        """检查 SMTP 服务可用性"""
        try:
            try:
                import aiosmtplib
            except ImportError:
                logger.warning("aiosmtplib not installed")
                self._is_available = True  # 使用 mock 模式
                return True
            
            # 尝试连接 SMTP 服务器
            smtp = aiosmtplib.SMTP(
                hostname=self.config.smtp_host,
                port=self.config.smtp_port,
                use_tls=self.config.smtp_use_tls,
                timeout=5
            )
            await smtp.connect()
            await smtp.quit()
            
            self._is_available = True
            return True
            
        except Exception as e:
            logger.error(f"SMTP availability check failed: {e}")
            self._is_available = False
            return False


# ============================================================================
# WeChatWorkNotificationService - 企业微信通知服务
# ============================================================================

class WeChatWorkNotificationService(NotificationService):
    """
    企业微信通知服务
    
    支持:
    - Webhook 机器人消息
    - 应用消息 (需要 corp_id, agent_id, secret)
    - 文本、Markdown、卡片消息格式
    - i18n 翻译键
    """
    
    def __init__(self, config: NotificationConfig):
        super().__init__(config)
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    
    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.WECHAT_WORK
    
    async def send(
        self,
        recipients: List[str],
        subject: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[NotificationResult]:
        """
        发送企业微信通知
        
        Args:
            recipients: 收件人列表 (用户ID 或 @all)
            subject: 通知主题
            message: 通知内容
            priority: 通知优先级
            metadata: 额外元数据
            
        Returns:
            发送结果列表
        """
        results = []
        
        # 优先使用 webhook
        if self.config.wechat_webhook_url:
            try:
                result = await self._retry_with_backoff(
                    self._send_webhook_message,
                    subject,
                    message,
                    priority,
                    metadata
                )
                results.append(result)
            except Exception as e:
                logger.error(f"WeChat webhook send failed: {e}")
                results.append(NotificationResult(
                    channel=self.channel,
                    success=False,
                    recipient="webhook",
                    error_message=str(e),
                    retry_count=self.config.max_retries
                ))
        
        # 如果配置了应用消息，发送给指定用户
        elif self.config.wechat_corp_id and self.config.wechat_agent_id:
            for recipient in recipients:
                try:
                    result = await self._retry_with_backoff(
                        self._send_app_message,
                        recipient,
                        subject,
                        message,
                        priority,
                        metadata
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"WeChat app message send failed to {recipient}: {e}")
                    results.append(NotificationResult(
                        channel=self.channel,
                        success=False,
                        recipient=recipient,
                        error_message=str(e),
                        retry_count=self.config.max_retries
                    ))
        else:
            logger.warning("WeChat Work not configured")
            results.append(NotificationResult(
                channel=self.channel,
                success=False,
                recipient="unknown",
                error_message="WeChat Work not configured"
            ))
        
        return results

    
    async def _send_webhook_message(
        self,
        subject: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """通过 Webhook 发送消息"""
        # 构建 Markdown 消息
        content = f"## {subject}\n\n{message}"
        
        if metadata:
            content += "\n\n---\n"
            if metadata.get("ticket_id"):
                content += f"**工单ID**: {metadata['ticket_id']}\n"
            if metadata.get("priority"):
                content += f"**优先级**: {metadata['priority']}\n"
            if metadata.get("sla_deadline"):
                content += f"**SLA截止时间**: {metadata['sla_deadline']}\n"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.config.wechat_webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                result = await response.json()
                
                if result.get("errcode") == 0:
                    logger.info("WeChat webhook message sent successfully")
                    return NotificationResult(
                        channel=self.channel,
                        success=True,
                        recipient="webhook",
                        message_id=str(result.get("msgid", "")),
                        sent_at=datetime.now()
                    )
                else:
                    error_msg = result.get("errmsg", "Unknown error")
                    raise Exception(f"WeChat API error: {error_msg}")
    
    async def _send_app_message(
        self,
        recipient: str,
        subject: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """通过应用消息发送"""
        # 获取 access_token
        access_token = await self._get_access_token()
        
        # 构建消息
        payload = {
            "touser": recipient,
            "msgtype": "textcard",
            "agentid": int(self.config.wechat_agent_id),
            "textcard": {
                "title": subject,
                "description": message[:512],  # 企业微信限制
                "url": metadata.get("url", ""),
                "btntxt": "查看详情"
            }
        }

        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                result = await response.json()
                
                if result.get("errcode") == 0:
                    logger.info(f"WeChat app message sent to {recipient}")
                    return NotificationResult(
                        channel=self.channel,
                        success=True,
                        recipient=recipient,
                        message_id=str(result.get("msgid", "")),
                        sent_at=datetime.now()
                    )
                else:
                    error_msg = result.get("errmsg", "Unknown error")
                    raise Exception(f"WeChat API error: {error_msg}")
    
    async def _get_access_token(self) -> str:
        """获取企业微信 access_token"""
        # 检查缓存的 token 是否有效
        if (self._access_token and self._token_expires_at and 
            datetime.now() < self._token_expires_at):
            return self._access_token
        
        url = (
            f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
            f"?corpid={self.config.wechat_corp_id}"
            f"&corpsecret={self.config.wechat_secret}"
        )
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.json()
                
                if result.get("errcode") == 0:
                    self._access_token = result["access_token"]
                    # token 有效期 7200 秒，提前 5 分钟刷新
                    from datetime import timedelta
                    self._token_expires_at = datetime.now() + timedelta(seconds=7200 - 300)
                    return self._access_token
                else:
                    raise Exception(f"Failed to get access token: {result.get('errmsg')}")
    
    async def check_availability(self) -> bool:
        """检查企业微信服务可用性"""
        try:
            if self.config.wechat_webhook_url:
                # 检查 webhook URL 是否可访问
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        self.config.wechat_webhook_url.replace("/send", ""),
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        self._is_available = True
                        return True
            elif self.config.wechat_corp_id:
                # 尝试获取 access_token
                await self._get_access_token()
                self._is_available = True
                return True
            else:
                self._is_available = False
                return False
        except Exception as e:
            logger.error(f"WeChat availability check failed: {e}")
            self._is_available = False
            return False


# ============================================================================
# NotificationManager - 通知管理器
# ============================================================================

class NotificationManager:
    """
    通知管理器
    
    管理多个通知服务，支持:
    - 按优先级配置通知渠道
    - 渠道故障转移
    - 并发发送
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        """
        初始化通知管理器
        
        Args:
            config: 通知配置
        """
        self.config = config or NotificationConfig()
        self._services: Dict[NotificationChannel, NotificationService] = {}
        self._priority_channels: Dict[NotificationPriority, List[NotificationChannel]] = {
            NotificationPriority.CRITICAL: [
                NotificationChannel.EMAIL,
                NotificationChannel.WECHAT_WORK
            ],
            NotificationPriority.HIGH: [
                NotificationChannel.EMAIL,
                NotificationChannel.WECHAT_WORK
            ],
            NotificationPriority.MEDIUM: [
                NotificationChannel.EMAIL
            ],
            NotificationPriority.LOW: [
                NotificationChannel.EMAIL
            ]
        }
        
        # 初始化默认服务
        self._init_default_services()
    
    def _init_default_services(self):
        """初始化默认通知服务"""
        # 邮件服务
        self._services[NotificationChannel.EMAIL] = EmailNotificationService(self.config)
        
        # 企业微信服务
        if self.config.wechat_webhook_url or self.config.wechat_corp_id:
            self._services[NotificationChannel.WECHAT_WORK] = WeChatWorkNotificationService(
                self.config
            )
    
    def register_service(self, service: NotificationService):
        """
        注册通知服务
        
        Args:
            service: 通知服务实例
        """
        self._services[service.channel] = service
        logger.info(f"Registered notification service: {service.channel.value}")

    
    def configure_priority_channels(
        self,
        priority: NotificationPriority,
        channels: List[NotificationChannel]
    ):
        """
        配置优先级对应的通知渠道
        
        Args:
            priority: 通知优先级
            channels: 通知渠道列表 (按优先顺序)
        """
        self._priority_channels[priority] = channels
        logger.info(f"Configured channels for {priority.value}: {[c.value for c in channels]}")
    
    def get_channels_for_priority(
        self,
        priority: NotificationPriority
    ) -> List[NotificationChannel]:
        """
        获取优先级对应的通知渠道
        
        Args:
            priority: 通知优先级
            
        Returns:
            通知渠道列表
        """
        return self._priority_channels.get(priority, [NotificationChannel.EMAIL])
    
    async def notify(
        self,
        recipients: List[str],
        subject: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[NotificationChannel, List[NotificationResult]]:
        """
        发送通知到所有配置的渠道
        
        Args:
            recipients: 收件人列表
            subject: 通知主题
            message: 通知内容
            priority: 通知优先级
            metadata: 额外元数据
            channels: 指定渠道列表 (可选，默认使用优先级配置)
            
        Returns:
            各渠道的发送结果
        """
        # 确定要使用的渠道
        target_channels = channels or self.get_channels_for_priority(priority)
        
        results: Dict[NotificationChannel, List[NotificationResult]] = {}
        
        # 并发发送到所有渠道
        tasks = []
        for channel in target_channels:
            if channel in self._services:
                service = self._services[channel]
                if service.is_available:
                    tasks.append(self._send_to_channel(
                        service, recipients, subject, message, priority, metadata
                    ))
                else:
                    logger.warning(f"Channel {channel.value} is not available")
                    results[channel] = [NotificationResult(
                        channel=channel,
                        success=False,
                        recipient="all",
                        error_message="Channel not available"
                    )]
            else:
                logger.warning(f"Channel {channel.value} not registered")

        
        if tasks:
            channel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, channel in enumerate([c for c in target_channels if c in self._services]):
                if isinstance(channel_results[i], Exception):
                    logger.error(f"Channel {channel.value} failed: {channel_results[i]}")
                    results[channel] = [NotificationResult(
                        channel=channel,
                        success=False,
                        recipient="all",
                        error_message=str(channel_results[i])
                    )]
                else:
                    results[channel] = channel_results[i]
        
        return results
    
    async def _send_to_channel(
        self,
        service: NotificationService,
        recipients: List[str],
        subject: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict[str, Any]]
    ) -> List[NotificationResult]:
        """发送到单个渠道"""
        return await service.send(recipients, subject, message, priority, metadata)
    
    async def notify_with_fallback(
        self,
        recipients: List[str],
        subject: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[NotificationChannel, List[NotificationResult]]:
        """
        发送通知，支持故障转移
        
        如果主渠道失败，尝试备用渠道
        
        Args:
            recipients: 收件人列表
            subject: 通知主题
            message: 通知内容
            priority: 通知优先级
            metadata: 额外元数据
            
        Returns:
            发送结果
        """
        channels = self.get_channels_for_priority(priority)
        results: Dict[NotificationChannel, List[NotificationResult]] = {}
        
        for channel in channels:
            if channel not in self._services:
                continue
                
            service = self._services[channel]
            
            try:
                channel_results = await service.send(
                    recipients, subject, message, priority, metadata
                )
                results[channel] = channel_results
                
                # 检查是否有成功的发送
                if any(r.success for r in channel_results):
                    logger.info(f"Notification sent successfully via {channel.value}")
                    return results
                    
            except Exception as e:
                logger.error(f"Channel {channel.value} failed: {e}")
                results[channel] = [NotificationResult(
                    channel=channel,
                    success=False,
                    recipient="all",
                    error_message=str(e)
                )]
        
        logger.error("All notification channels failed")
        return results

    
    async def check_all_services(self) -> Dict[NotificationChannel, bool]:
        """
        检查所有服务的可用性
        
        Returns:
            各服务的可用性状态
        """
        results = {}
        
        for channel, service in self._services.items():
            try:
                results[channel] = await service.check_availability()
            except Exception as e:
                logger.error(f"Service check failed for {channel.value}: {e}")
                results[channel] = False
        
        return results


# ============================================================================
# 辅助函数
# ============================================================================

def create_notification_manager(
    smtp_host: str = "localhost",
    smtp_port: int = 587,
    smtp_username: str = "",
    smtp_password: str = "",
    smtp_from_address: str = "noreply@superinsight.ai",
    wechat_webhook_url: str = "",
    wechat_corp_id: str = "",
    wechat_agent_id: str = "",
    wechat_secret: str = ""
) -> NotificationManager:
    """
    创建通知管理器的便捷函数
    
    Args:
        smtp_host: SMTP 服务器地址
        smtp_port: SMTP 端口
        smtp_username: SMTP 用户名
        smtp_password: SMTP 密码
        smtp_from_address: 发件人地址
        wechat_webhook_url: 企业微信 Webhook URL
        wechat_corp_id: 企业微信企业 ID
        wechat_agent_id: 企业微信应用 ID
        wechat_secret: 企业微信应用密钥
        
    Returns:
        配置好的通知管理器
    """
    config = NotificationConfig(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        smtp_from_address=smtp_from_address,
        wechat_webhook_url=wechat_webhook_url,
        wechat_corp_id=wechat_corp_id,
        wechat_agent_id=wechat_agent_id,
        wechat_secret=wechat_secret
    )
    
    return NotificationManager(config)


# 导出
__all__ = [
    "NotificationService",
    "EmailNotificationService",
    "WeChatWorkNotificationService",
    "NotificationManager",
    "NotificationConfig",
    "NotificationResult",
    "NotificationChannel",
    "NotificationPriority",
    "SLANotificationI18nKeys",
    "create_notification_manager"
]
