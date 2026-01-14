"""
Crowdsource Manager (众包管理器)

Manages crowdsourcing annotation tasks.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SensitivityFilter:
    """敏感数据过滤器"""
    
    async def filter(self, data: List[dict], max_level: int) -> List[dict]:
        """过滤敏感数据
        
        Args:
            data: 数据列表
            max_level: 最大敏感级别 (1=公开, 2=内部, 3=敏感)
            
        Returns:
            过滤后的数据列表
        """
        return [d for d in data if d.get("sensitivity_level", 1) <= max_level]


class CrowdsourceManager:
    """众包管理器 - 管理众包标注任务"""
    
    def __init__(
        self,
        db: "AsyncSession" = None,
        sensitivity_filter: SensitivityFilter = None,
        platform_adapter=None
    ):
        self.db = db
        self.sensitivity_filter = sensitivity_filter or SensitivityFilter()
        self.platform_adapter = platform_adapter
        self._tasks: Dict[str, dict] = {}  # task_id -> task
        self._claims: Dict[str, dict] = {}  # claim_key -> claim
        self._submissions: Dict[str, dict] = {}  # submission_id -> submission
    
    async def create_crowdsource_task(
        self,
        project_id: str,
        config: dict,
        data: List[dict] = None
    ) -> dict:
        """创建众包任务
        
        Args:
            project_id: 项目ID
            config: 众包任务配置
            data: 项目数据列表
            
        Returns:
            CrowdsourceTask dict
        """
        # 获取项目数据
        if data is None:
            data = await self._get_project_data(project_id)
        
        # 过滤敏感数据
        sensitivity_level = config.get("sensitivity_level", 1)
        filtered_data = await self.sensitivity_filter.filter(data, sensitivity_level)
        
        task = {
            "id": str(uuid4()),
            "project_id": project_id,
            "data_ids": [d.get("id", str(uuid4())) for d in filtered_data],
            "config": config,
            "platform": config.get("platform", "internal"),
            "status": "open",
            "created_at": datetime.utcnow()
        }
        
        self._tasks[task["id"]] = task
        
        # 如果使用第三方平台，同步任务
        if config.get("platform") != "internal" and self.platform_adapter:
            await self.platform_adapter.sync_task(task)
        
        return task
    
    async def _get_project_data(self, project_id: str) -> List[dict]:
        """获取项目数据"""
        # 实际实现会从数据库获取
        return []
    
    async def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    async def claim_task(
        self,
        task_id: str,
        annotator_id: str,
        claim_duration_hours: int = 2
    ) -> dict:
        """领取任务
        
        Args:
            task_id: 任务ID
            annotator_id: 标注员ID
            claim_duration_hours: 领取有效时长（小时）
            
        Returns:
            TaskClaim dict
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if task["status"] != "open":
            raise ValueError(f"Task {task_id} is not open for claiming")
        
        # 检查是否已领取
        claim_key = f"{task_id}:{annotator_id}"
        if claim_key in self._claims:
            existing = self._claims[claim_key]
            if existing["expires_at"] > datetime.utcnow():
                return existing
        
        # 检查任务是否已达到最大标注人数
        config = task.get("config", {})
        max_annotators = config.get("max_annotators", 3)
        current_claims = sum(
            1 for k, v in self._claims.items()
            if k.startswith(f"{task_id}:") and v["expires_at"] > datetime.utcnow()
        )
        
        if current_claims >= max_annotators:
            raise ValueError(f"Task {task_id} has reached maximum annotators")
        
        claim = {
            "task_id": task_id,
            "annotator_id": annotator_id,
            "claimed_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=claim_duration_hours)
        }
        
        self._claims[claim_key] = claim
        return claim
    
    async def submit_annotation(
        self,
        task_id: str,
        annotator_id: str,
        annotation: Dict[str, Any]
    ) -> dict:
        """提交标注
        
        Args:
            task_id: 任务ID
            annotator_id: 标注员ID
            annotation: 标注内容
            
        Returns:
            CrowdsourceSubmission dict
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # 检查是否已领取
        claim_key = f"{task_id}:{annotator_id}"
        claim = self._claims.get(claim_key)
        if not claim or claim["expires_at"] < datetime.utcnow():
            raise ValueError("Task not claimed or claim expired")
        
        config = task.get("config", {})
        price = config.get("price_per_task", 0.1)
        
        submission = {
            "id": str(uuid4()),
            "task_id": task_id,
            "annotator_id": annotator_id,
            "annotation": annotation,
            "status": "pending",
            "price": price,
            "created_at": datetime.utcnow()
        }
        
        self._submissions[submission["id"]] = submission
        return submission
    
    async def get_submission(self, submission_id: str) -> Optional[dict]:
        """获取提交"""
        return self._submissions.get(submission_id)
    
    async def approve_submission(self, submission_id: str) -> dict:
        """审核通过提交"""
        submission = self._submissions.get(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        submission["status"] = "approved"
        submission["approved_at"] = datetime.utcnow()
        return submission
    
    async def reject_submission(self, submission_id: str, reason: str) -> dict:
        """驳回提交"""
        submission = self._submissions.get(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        submission["status"] = "rejected"
        submission["rejection_reason"] = reason
        submission["rejected_at"] = datetime.utcnow()
        return submission
    
    async def get_available_tasks(
        self,
        annotator_id: str,
        ability_tags: List[str] = None
    ) -> List[dict]:
        """获取可领取任务
        
        Args:
            annotator_id: 标注员ID
            ability_tags: 能力标签（用于匹配）
            
        Returns:
            可领取任务列表
        """
        available = []
        for task in self._tasks.values():
            if task["status"] != "open":
                continue
            
            # 检查是否已领取
            claim_key = f"{task['id']}:{annotator_id}"
            if claim_key in self._claims:
                claim = self._claims[claim_key]
                if claim["expires_at"] > datetime.utcnow():
                    continue  # 已领取且未过期
            
            # 检查是否已达到最大标注人数
            config = task.get("config", {})
            max_annotators = config.get("max_annotators", 3)
            current_claims = sum(
                1 for k, v in self._claims.items()
                if k.startswith(f"{task['id']}:") and v["expires_at"] > datetime.utcnow()
            )
            
            if current_claims < max_annotators:
                available.append(task)
        
        return available
    
    async def get_annotator_submissions(
        self,
        annotator_id: str,
        status: str = None
    ) -> List[dict]:
        """获取标注员的提交"""
        submissions = [
            s for s in self._submissions.values()
            if s["annotator_id"] == annotator_id
        ]
        if status:
            submissions = [s for s in submissions if s["status"] == status]
        return submissions
