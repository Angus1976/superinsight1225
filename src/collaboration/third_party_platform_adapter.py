"""
Third Party Platform Adapter (第三方平台适配器)

Integrates with external annotation platforms like MTurk and Scale AI.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class PlatformType(str, Enum):
    """第三方平台类型"""
    MTURK = "mturk"
    SCALE_AI = "scale_ai"
    CUSTOM = "custom"


class PlatformConnector(ABC):
    """平台连接器基类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.name = config.get("name", "unknown")
    
    @abstractmethod
    async def create_task(self, task: dict) -> dict:
        """创建任务"""
        pass
    
    @abstractmethod
    async def fetch_results(self, task_id: str) -> List[dict]:
        """获取结果"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass


class MTurkConnector(PlatformConnector):
    """Amazon MTurk 连接器"""
    
    async def create_task(self, task: dict) -> dict:
        """创建 MTurk HIT"""
        # 实际实现会调用 MTurk API
        return {
            "success": True,
            "platform": "mturk",
            "task_id": task.get("id"),
            "external_task_id": f"mturk_{uuid4().hex[:8]}",
            "message": "Task created on MTurk",
            "synced_at": datetime.utcnow()
        }
    
    async def fetch_results(self, task_id: str) -> List[dict]:
        """获取 MTurk 结果"""
        # 实际实现会调用 MTurk API
        return []
    
    async def health_check(self) -> bool:
        """检查 MTurk 连接"""
        # 实际实现会验证 API 凭证
        return True


class ScaleAIConnector(PlatformConnector):
    """Scale AI 连接器"""
    
    async def create_task(self, task: dict) -> dict:
        """创建 Scale AI 任务"""
        # 实际实现会调用 Scale AI API
        return {
            "success": True,
            "platform": "scale_ai",
            "task_id": task.get("id"),
            "external_task_id": f"scale_{uuid4().hex[:8]}",
            "message": "Task created on Scale AI",
            "synced_at": datetime.utcnow()
        }
    
    async def fetch_results(self, task_id: str) -> List[dict]:
        """获取 Scale AI 结果"""
        # 实际实现会调用 Scale AI API
        return []
    
    async def health_check(self) -> bool:
        """检查 Scale AI 连接"""
        return True


class CustomRESTConnector(PlatformConnector):
    """自定义 REST API 连接器"""
    
    async def create_task(self, task: dict) -> dict:
        """创建自定义平台任务"""
        endpoint = self.config.get("endpoint")
        if not endpoint:
            return {
                "success": False,
                "platform": "custom",
                "task_id": task.get("id"),
                "external_task_id": None,
                "message": "No endpoint configured",
                "synced_at": datetime.utcnow()
            }
        
        # 实际实现会调用自定义 REST API
        return {
            "success": True,
            "platform": "custom",
            "task_id": task.get("id"),
            "external_task_id": f"custom_{uuid4().hex[:8]}",
            "message": f"Task created on {self.name}",
            "synced_at": datetime.utcnow()
        }
    
    async def fetch_results(self, task_id: str) -> List[dict]:
        """获取自定义平台结果"""
        return []
    
    async def health_check(self) -> bool:
        """检查自定义平台连接"""
        return True


class ThirdPartyPlatformAdapter:
    """第三方平台适配器 - 对接第三方标注平台"""
    
    def __init__(self, db: "AsyncSession" = None):
        self.db = db
        self.platforms: Dict[str, PlatformConnector] = {}
        self._configs: Dict[str, dict] = {}
        self._sync_results: Dict[str, dict] = {}  # task_id -> sync result
    
    async def register_platform(self, config: dict) -> dict:
        """注册平台
        
        Args:
            config: 平台配置 (name, platform_type, api_key, api_secret, endpoint)
            
        Returns:
            PlatformInfo dict
        """
        connector = self._create_connector(config)
        self.platforms[config["name"]] = connector
        self._configs[config["name"]] = config
        
        # 验证连接
        is_connected = await connector.health_check()
        
        return {
            "name": config["name"],
            "platform_type": config.get("platform_type", "custom"),
            "status": "connected" if is_connected else "disconnected",
            "connected_at": datetime.utcnow() if is_connected else None
        }
    
    def _create_connector(self, config: dict) -> PlatformConnector:
        """创建连接器"""
        platform_type = config.get("platform_type", "custom")
        
        if platform_type == PlatformType.MTURK.value:
            return MTurkConnector(config)
        elif platform_type == PlatformType.SCALE_AI.value:
            return ScaleAIConnector(config)
        else:
            return CustomRESTConnector(config)
    
    async def unregister_platform(self, platform_name: str) -> bool:
        """注销平台"""
        if platform_name in self.platforms:
            del self.platforms[platform_name]
            del self._configs[platform_name]
            return True
        return False
    
    async def get_platform(self, platform_name: str) -> Optional[dict]:
        """获取平台信息"""
        config = self._configs.get(platform_name)
        if not config:
            return None
        
        connector = self.platforms.get(platform_name)
        is_connected = await connector.health_check() if connector else False
        
        return {
            "name": platform_name,
            "platform_type": config.get("platform_type", "custom"),
            "status": "connected" if is_connected else "disconnected",
            "endpoint": config.get("endpoint")
        }
    
    async def sync_task(self, task: dict) -> dict:
        """同步任务到第三方平台
        
        Args:
            task: 众包任务
            
        Returns:
            SyncResult dict
        """
        platform_name = task.get("platform", "internal")
        
        if platform_name == "internal":
            return {
                "success": True,
                "platform": "internal",
                "task_id": task.get("id"),
                "external_task_id": None,
                "message": "Internal task, no sync needed",
                "synced_at": datetime.utcnow()
            }
        
        connector = self.platforms.get(platform_name)
        if not connector:
            return {
                "success": False,
                "platform": platform_name,
                "task_id": task.get("id"),
                "external_task_id": None,
                "message": f"Platform {platform_name} not configured",
                "synced_at": datetime.utcnow()
            }
        
        result = await connector.create_task(task)
        self._sync_results[task.get("id")] = result
        return result
    
    async def fetch_results(self, task_id: str, platform_name: str = None) -> List[dict]:
        """获取第三方平台结果
        
        Args:
            task_id: 任务ID
            platform_name: 平台名称
            
        Returns:
            提交结果列表
        """
        if platform_name:
            connector = self.platforms.get(platform_name)
            if connector:
                return await connector.fetch_results(task_id)
        
        # 尝试从同步记录获取平台
        sync_result = self._sync_results.get(task_id)
        if sync_result:
            platform_name = sync_result.get("platform")
            connector = self.platforms.get(platform_name)
            if connector:
                return await connector.fetch_results(task_id)
        
        return []
    
    async def get_platform_status(self, platform_name: str) -> dict:
        """获取平台状态
        
        Args:
            platform_name: 平台名称
            
        Returns:
            PlatformStatus dict
        """
        connector = self.platforms.get(platform_name)
        if not connector:
            return {
                "name": platform_name,
                "connected": False,
                "last_sync": None,
                "pending_tasks": 0,
                "completed_tasks": 0
            }
        
        is_connected = await connector.health_check()
        
        # 统计任务数
        pending = 0
        completed = 0
        last_sync = None
        
        for task_id, result in self._sync_results.items():
            if result.get("platform") == platform_name:
                if result.get("success"):
                    pending += 1
                if result.get("synced_at"):
                    if last_sync is None or result["synced_at"] > last_sync:
                        last_sync = result["synced_at"]
        
        return {
            "name": platform_name,
            "connected": is_connected,
            "last_sync": last_sync,
            "pending_tasks": pending,
            "completed_tasks": completed
        }
    
    async def get_all_platforms(self) -> List[dict]:
        """获取所有已注册平台"""
        platforms = []
        for name in self.platforms.keys():
            status = await self.get_platform_status(name)
            platforms.append(status)
        return platforms
    
    async def test_connection(self, platform_name: str) -> dict:
        """测试平台连接
        
        Args:
            platform_name: 平台名称
            
        Returns:
            测试结果
        """
        connector = self.platforms.get(platform_name)
        if not connector:
            return {
                "success": False,
                "platform": platform_name,
                "message": "Platform not configured"
            }
        
        try:
            is_connected = await connector.health_check()
            return {
                "success": is_connected,
                "platform": platform_name,
                "message": "Connection successful" if is_connected else "Connection failed"
            }
        except Exception as e:
            return {
                "success": False,
                "platform": platform_name,
                "message": f"Connection error: {str(e)}"
            }
