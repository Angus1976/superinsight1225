"""
Collaboration Engine (协作引擎)

Supports multi-user collaboration with real-time synchronization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CollaborationEngine:
    """协作引擎 - 支持多人同时协作标注"""
    
    def __init__(self, db: "AsyncSession" = None, cache=None, ws_manager=None, notification_service=None):
        self.db = db
        self.cache = cache
        self.ws_manager = ws_manager
        self.notification_service = notification_service
        self._locks: Dict[str, str] = {}  # task_id -> annotator_id (in-memory fallback)
        self._versions: Dict[str, List[dict]] = {}  # task_id -> versions (in-memory fallback)
    
    async def acquire_task_lock(self, task_id: str, annotator_id: str) -> bool:
        """获取任务锁，防止重复标注
        
        Args:
            task_id: 任务ID
            annotator_id: 标注员ID
            
        Returns:
            是否成功获取锁
        """
        lock_key = f"task_lock:{task_id}"
        
        if self.cache:
            # 使用 Redis 实现分布式锁
            result = await self.cache.set(lock_key, annotator_id, nx=True, ex=3600)
            return result is not None
        else:
            # 内存锁（仅用于测试）
            if task_id in self._locks:
                return False
            self._locks[task_id] = annotator_id
            return True
    
    async def release_task_lock(self, task_id: str, annotator_id: str) -> bool:
        """释放任务锁
        
        Args:
            task_id: 任务ID
            annotator_id: 标注员ID
            
        Returns:
            是否成功释放锁
        """
        lock_key = f"task_lock:{task_id}"
        
        if self.cache:
            current_holder = await self.cache.get(lock_key)
            if current_holder == annotator_id:
                await self.cache.delete(lock_key)
                return True
            return False
        else:
            if self._locks.get(task_id) == annotator_id:
                del self._locks[task_id]
                return True
            return False
    
    async def get_lock_holder(self, task_id: str) -> Optional[str]:
        """获取任务锁持有者"""
        lock_key = f"task_lock:{task_id}"
        
        if self.cache:
            return await self.cache.get(lock_key)
        else:
            return self._locks.get(task_id)
    
    async def sync_progress(self, project_id: str, progress: dict) -> None:
        """同步标注进度
        
        Args:
            project_id: 项目ID
            progress: 进度更新信息
        """
        if self.ws_manager:
            await self.ws_manager.broadcast(
                f"project:{project_id}",
                {"type": "progress_update", "data": progress}
            )
    
    async def save_annotation_version(
        self,
        task_id: str,
        annotator_id: str,
        annotation: Dict[str, Any]
    ) -> dict:
        """保存标注版本
        
        Args:
            task_id: 任务ID
            annotator_id: 标注员ID
            annotation: 标注内容
            
        Returns:
            AnnotationVersion dict
        """
        version_num = await self._get_next_version(task_id)
        
        version = {
            "id": str(uuid4()),
            "task_id": task_id,
            "annotator_id": annotator_id,
            "annotation": annotation,
            "version": version_num,
            "created_at": datetime.utcnow()
        }
        
        # 保存到内存（实际实现会保存到数据库）
        if task_id not in self._versions:
            self._versions[task_id] = []
        self._versions[task_id].append(version)
        
        return version
    
    async def _get_next_version(self, task_id: str) -> int:
        """获取下一个版本号"""
        versions = self._versions.get(task_id, [])
        if not versions:
            return 1
        return max(v["version"] for v in versions) + 1
    
    async def get_annotation_versions(self, task_id: str) -> List[dict]:
        """获取所有标注版本
        
        Args:
            task_id: 任务ID
            
        Returns:
            标注版本列表
        """
        return self._versions.get(task_id, [])
    
    async def get_online_members(self, project_id: str) -> List[dict]:
        """获取在线成员
        
        Args:
            project_id: 项目ID
            
        Returns:
            在线成员列表
        """
        # 实际实现会从 WebSocket 连接管理器获取
        return []
    
    async def send_message(
        self,
        project_id: str,
        sender_id: str,
        sender_name: str,
        message: str
    ) -> dict:
        """发送消息
        
        Args:
            project_id: 项目ID
            sender_id: 发送者ID
            sender_name: 发送者名称
            message: 消息内容
            
        Returns:
            ChatMessage dict
        """
        chat_message = {
            "id": str(uuid4()),
            "project_id": project_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "message": message,
            "created_at": datetime.utcnow()
        }
        
        if self.ws_manager:
            await self.ws_manager.broadcast(
                f"project:{project_id}",
                {"type": "chat_message", "data": chat_message}
            )
        
        return chat_message
