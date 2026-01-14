"""
Notification Service (通知服务)

Multi-channel notification service for task and review notifications.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class NotificationChannel(str, Enum):
    """通知渠道"""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationService:
    """通知服务 - 发送任务和审核通知"""
    
    def __init__(self, db: "AsyncSession" = None, email_service=None, webhook_client=None):
        self.db = db
        self.email_service = email_service
        self.webhook_client = webhook_client
        self._notifications: List[dict] = []
        self._preferences: Dict[str, dict] = {}  # user_id -> preferences
    
    async def set_preferences(self, user_id: str, preferences: dict) -> dict:
        """设置通知偏好
        
        Args:
            user_id: 用户ID
            preferences: 通知偏好配置
            
        Returns:
            NotificationPreference dict
        """
        pref = {
            "user_id": user_id,
            "channels": preferences.get("channels", [NotificationChannel.IN_APP.value]),
            "task_assigned": preferences.get("task_assigned", True),
            "review_completed": preferences.get("review_completed", True),
            "deadline_reminder": preferences.get("deadline_reminder", True),
            "quality_warning": preferences.get("quality_warning", True)
        }
        self._preferences[user_id] = pref
        return pref
    
    async def get_preferences(self, user_id: str) -> dict:
        """获取通知偏好"""
        return self._preferences.get(user_id, {
            "user_id": user_id,
            "channels": [NotificationChannel.IN_APP.value],
            "task_assigned": True,
            "review_completed": True,
            "deadline_reminder": True,
            "quality_warning": True
        })
    
    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        data: Dict[str, Any] = None,
        channels: List[NotificationChannel] = None
    ) -> List[dict]:
        """发送通知
        
        Args:
            user_id: 用户ID
            title: 标题
            message: 消息内容
            data: 附加数据
            channels: 通知渠道列表
            
        Returns:
            发送的通知列表
        """
        if channels is None:
            prefs = await self.get_preferences(user_id)
            channels = [NotificationChannel(c) for c in prefs.get("channels", [NotificationChannel.IN_APP.value])]
        
        notifications = []
        for channel in channels:
            notification = {
                "id": str(uuid4()),
                "user_id": user_id,
                "channel": channel.value,
                "title": title,
                "message": message,
                "data": data,
                "read": False,
                "created_at": datetime.utcnow()
            }
            
            self._notifications.append(notification)
            notifications.append(notification)
            
            # 根据渠道发送
            if channel == NotificationChannel.EMAIL and self.email_service:
                await self._send_email(user_id, title, message)
            elif channel == NotificationChannel.WEBHOOK and self.webhook_client:
                await self._send_webhook(user_id, title, message, data)
        
        return notifications
    
    async def _send_email(self, user_id: str, title: str, message: str) -> None:
        """发送邮件"""
        if self.email_service:
            await self.email_service.send(user_id, title, message)
    
    async def _send_webhook(
        self,
        user_id: str,
        title: str,
        message: str,
        data: Dict[str, Any] = None
    ) -> None:
        """发送 Webhook"""
        if self.webhook_client:
            await self.webhook_client.post({
                "user_id": user_id,
                "title": title,
                "message": message,
                "data": data
            })
    
    async def notify_task_assigned(self, user_id: str, task_id: str) -> List[dict]:
        """通知任务分配
        
        Args:
            user_id: 用户ID
            task_id: 任务ID
            
        Returns:
            发送的通知列表
        """
        prefs = await self.get_preferences(user_id)
        if not prefs.get("task_assigned", True):
            return []
        
        return await self.send_notification(
            user_id=user_id,
            title="新任务分配",
            message=f"您有一个新的标注任务 {task_id}",
            data={"task_id": task_id, "type": "task_assigned"}
        )
    
    async def notify_review_completed(
        self,
        user_id: str,
        annotation_id: str,
        status: str
    ) -> List[dict]:
        """通知审核完成
        
        Args:
            user_id: 用户ID
            annotation_id: 标注ID
            status: 审核状态
            
        Returns:
            发送的通知列表
        """
        prefs = await self.get_preferences(user_id)
        if not prefs.get("review_completed", True):
            return []
        
        status_text = "通过" if status == "approved" else "驳回"
        return await self.send_notification(
            user_id=user_id,
            title="审核结果通知",
            message=f"您的标注 {annotation_id} 已{status_text}",
            data={"annotation_id": annotation_id, "status": status, "type": "review_completed"}
        )
    
    async def notify_rejection(
        self,
        annotation_id: str,
        reason: str
    ) -> List[dict]:
        """通知审核驳回（需要获取标注员ID）"""
        # 实际实现会从数据库获取标注员ID
        return []
    
    async def notify_deadline_reminder(
        self,
        user_id: str,
        task_id: str,
        deadline: datetime
    ) -> List[dict]:
        """通知截止提醒
        
        Args:
            user_id: 用户ID
            task_id: 任务ID
            deadline: 截止时间
            
        Returns:
            发送的通知列表
        """
        prefs = await self.get_preferences(user_id)
        if not prefs.get("deadline_reminder", True):
            return []
        
        time_left = deadline - datetime.utcnow()
        hours_left = int(time_left.total_seconds() / 3600)
        
        return await self.send_notification(
            user_id=user_id,
            title="任务截止提醒",
            message=f"任务 {task_id} 将在 {hours_left} 小时后截止",
            data={"task_id": task_id, "deadline": deadline.isoformat(), "type": "deadline_reminder"}
        )
    
    async def send_quality_warning(
        self,
        user_id: str,
        accuracy: float,
        threshold: float
    ) -> List[dict]:
        """发送质量预警
        
        Args:
            user_id: 用户ID
            accuracy: 当前准确率
            threshold: 阈值
            
        Returns:
            发送的通知列表
        """
        prefs = await self.get_preferences(user_id)
        if not prefs.get("quality_warning", True):
            return []
        
        return await self.send_notification(
            user_id=user_id,
            title="质量预警",
            message=f"您的标注准确率 ({accuracy:.1%}) 低于阈值 ({threshold:.1%})，请注意提高质量",
            data={"accuracy": accuracy, "threshold": threshold, "type": "quality_warning"}
        )
    
    async def notify_conflicts(self, task_id: str, conflict_count: int) -> None:
        """通知存在冲突"""
        # 实际实现会通知相关人员
        pass
    
    async def batch_notify(
        self,
        user_ids: List[str],
        title: str,
        message: str,
        data: Dict[str, Any] = None
    ) -> List[dict]:
        """批量通知
        
        Args:
            user_ids: 用户ID列表
            title: 标题
            message: 消息内容
            data: 附加数据
            
        Returns:
            发送的通知列表
        """
        all_notifications = []
        for user_id in user_ids:
            notifications = await self.send_notification(user_id, title, message, data)
            all_notifications.extend(notifications)
        return all_notifications
    
    async def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False
    ) -> List[dict]:
        """获取用户通知
        
        Args:
            user_id: 用户ID
            unread_only: 是否只返回未读
            
        Returns:
            通知列表
        """
        notifications = [n for n in self._notifications if n["user_id"] == user_id]
        if unread_only:
            notifications = [n for n in notifications if not n["read"]]
        return sorted(notifications, key=lambda x: x["created_at"], reverse=True)
    
    async def mark_as_read(self, notification_id: str) -> bool:
        """标记为已读"""
        for n in self._notifications:
            if n["id"] == notification_id:
                n["read"] = True
                return True
        return False
