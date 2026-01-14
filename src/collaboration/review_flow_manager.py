"""
Review Flow Manager (审核流管理器)

Manages multi-level review processes.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ReviewStatus(str, Enum):
    """审核状态"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewFlowManager:
    """审核流管理器 - 管理多级审核流程"""
    
    def __init__(self, db: "AsyncSession" = None, notification_service=None):
        self.db = db
        self.notification_service = notification_service
        self._flows: Dict[str, dict] = {}  # project_id -> flow config
        self._review_tasks: Dict[str, dict] = {}  # review_task_id -> review task
        self._history: Dict[str, List[dict]] = {}  # annotation_id -> history
    
    async def configure_flow(self, project_id: str, config: dict) -> dict:
        """配置审核流程
        
        Args:
            project_id: 项目ID
            config: 审核流程配置 (levels, pass_threshold, auto_approve)
            
        Returns:
            ReviewFlow dict
        """
        flow = {
            "project_id": project_id,
            "levels": config.get("levels", 2),
            "pass_threshold": config.get("pass_threshold", 0.8),
            "auto_approve": config.get("auto_approve", False),
            "created_at": datetime.utcnow()
        }
        self._flows[project_id] = flow
        return flow
    
    async def get_flow(self, project_id: str) -> Optional[dict]:
        """获取审核流程配置"""
        return self._flows.get(project_id, {
            "project_id": project_id,
            "levels": 2,
            "pass_threshold": 0.8,
            "auto_approve": False
        })
    
    async def submit_for_review(self, annotation_id: str, project_id: str = None) -> dict:
        """提交审核
        
        Args:
            annotation_id: 标注ID
            project_id: 项目ID
            
        Returns:
            ReviewTask dict
        """
        flow = await self.get_flow(project_id) if project_id else {"levels": 2}
        
        review_task = {
            "id": str(uuid4()),
            "annotation_id": annotation_id,
            "current_level": 1,
            "max_level": flow.get("levels", 2),
            "status": ReviewStatus.PENDING.value,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        self._review_tasks[review_task["id"]] = review_task
        return review_task
    
    async def get_review_task(self, review_task_id: str) -> Optional[dict]:
        """获取审核任务"""
        return self._review_tasks.get(review_task_id)
    
    async def approve(self, review_task_id: str, reviewer_id: str) -> dict:
        """审核通过
        
        Args:
            review_task_id: 审核任务ID
            reviewer_id: 审核员ID
            
        Returns:
            ReviewResult dict
        """
        task = self._review_tasks.get(review_task_id)
        if not task:
            raise ValueError(f"Review task {review_task_id} not found")
        
        if task["current_level"] < task["max_level"]:
            # 进入下一级审核
            task["current_level"] += 1
            task["status"] = ReviewStatus.PENDING.value
            action = "approve_to_next_level"
        else:
            # 终审通过
            task["status"] = ReviewStatus.APPROVED.value
            action = "final_approve"
        
        task["updated_at"] = datetime.utcnow()
        
        # 记录历史
        await self._record_history(task, reviewer_id, "approve")
        
        return {
            "task_id": review_task_id,
            "action": action,
            "status": ReviewStatus(task["status"]),
            "level": task["current_level"],
            "reviewer_id": reviewer_id,
            "reviewed_at": datetime.utcnow()
        }
    
    async def reject(self, review_task_id: str, reviewer_id: str, reason: str) -> dict:
        """审核驳回
        
        Args:
            review_task_id: 审核任务ID
            reviewer_id: 审核员ID
            reason: 驳回原因
            
        Returns:
            ReviewResult dict
        """
        task = self._review_tasks.get(review_task_id)
        if not task:
            raise ValueError(f"Review task {review_task_id} not found")
        
        task["status"] = ReviewStatus.REJECTED.value
        task["updated_at"] = datetime.utcnow()
        
        # 记录历史
        await self._record_history(task, reviewer_id, "reject", reason)
        
        # 通知原标注员
        if self.notification_service:
            await self.notification_service.notify_rejection(
                task["annotation_id"], reason
            )
        
        return {
            "task_id": review_task_id,
            "action": "reject",
            "status": ReviewStatus.REJECTED,
            "level": task["current_level"],
            "reviewer_id": reviewer_id,
            "reason": reason,
            "reviewed_at": datetime.utcnow()
        }
    
    async def batch_approve(self, review_task_ids: List[str], reviewer_id: str) -> List[dict]:
        """批量审核
        
        Args:
            review_task_ids: 审核任务ID列表
            reviewer_id: 审核员ID
            
        Returns:
            ReviewResult列表
        """
        results = []
        for task_id in review_task_ids:
            try:
                result = await self.approve(task_id, reviewer_id)
                results.append(result)
            except ValueError as e:
                results.append({
                    "task_id": task_id,
                    "action": "error",
                    "error": str(e)
                })
        return results
    
    async def _record_history(
        self,
        task: dict,
        reviewer_id: str,
        action: str,
        reason: str = None
    ) -> dict:
        """记录审核历史"""
        history_entry = {
            "id": str(uuid4()),
            "review_task_id": task["id"],
            "annotation_id": task["annotation_id"],
            "reviewer_id": reviewer_id,
            "action": action,
            "reason": reason,
            "level": task["current_level"],
            "created_at": datetime.utcnow()
        }
        
        annotation_id = task["annotation_id"]
        if annotation_id not in self._history:
            self._history[annotation_id] = []
        self._history[annotation_id].append(history_entry)
        
        return history_entry
    
    async def get_review_history(self, annotation_id: str) -> List[dict]:
        """获取审核历史
        
        Args:
            annotation_id: 标注ID
            
        Returns:
            审核历史列表
        """
        return self._history.get(annotation_id, [])
    
    async def get_pending_reviews(self, reviewer_id: str = None, level: int = None) -> List[dict]:
        """获取待审核任务"""
        pending = []
        for task in self._review_tasks.values():
            if task["status"] == ReviewStatus.PENDING.value:
                if level is None or task["current_level"] == level:
                    pending.append(task)
        return pending
