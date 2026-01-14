"""
Task Dispatcher (任务分配器)

Intelligent task assignment based on skills and workload.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4
import statistics

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AssignmentMode(str, Enum):
    """任务分配模式"""
    AUTO = "auto"
    MANUAL = "manual"


class TaskDispatcher:
    """任务分配器 - 智能分配标注任务给合适的标注员"""
    
    def __init__(self, db: "AsyncSession" = None, notification_service=None):
        self.db = db
        self.notification_service = notification_service
        self._tasks: Dict[str, dict] = {}  # task_id -> task (in-memory for testing)
        self._annotators: Dict[str, dict] = {}  # annotator_id -> annotator
        self._assignments: Dict[str, dict] = {}  # assignment_id -> assignment
    
    # ============== Task Management ==============
    
    def add_task(self, task: dict) -> None:
        """添加任务（用于测试）"""
        self._tasks[task["id"]] = task
    
    def add_annotator(self, annotator: dict) -> None:
        """添加标注员（用于测试）"""
        self._annotators[annotator["id"]] = annotator
    
    async def assign_task(
        self,
        task_id: str,
        mode: AssignmentMode = AssignmentMode.AUTO,
        annotator_id: str = None,
        priority: int = 0,
        deadline: datetime = None
    ) -> dict:
        """分配任务
        
        Args:
            task_id: 任务ID
            mode: 分配模式 (auto/manual)
            annotator_id: 手动分配时的标注员ID
            priority: 优先级
            deadline: 截止时间
            
        Returns:
            TaskAssignment dict
        """
        if mode == AssignmentMode.MANUAL:
            return await self._manual_assign(task_id, annotator_id, priority, deadline)
        else:
            return await self._auto_assign(task_id, priority, deadline)
    
    async def _auto_assign(self, task_id: str, priority: int = 0, deadline: datetime = None) -> dict:
        """自动分配"""
        # 获取任务信息
        task = await self._get_task(task_id)
        required_skills = task.get("required_skills", [])
        
        # 获取匹配技能的标注员
        candidates = await self._get_skill_matched_annotators(required_skills)
        
        if not candidates:
            raise ValueError("No matching annotators found for task skills")
        
        # 按工作负载排序
        candidates = await self._sort_by_workload(candidates)
        
        # 选择最佳候选人（负载最低的）
        annotator = candidates[0]
        
        # 创建分配记录
        assignment = await self._create_assignment(task_id, annotator["id"], priority, deadline)
        
        # 更新标注员工作负载
        annotator["current_workload"] = annotator.get("current_workload", 0) + 1
        
        # 发送通知
        if self.notification_service:
            await self.notification_service.notify_task_assigned(annotator["id"], task_id)
        
        return assignment
    
    async def _manual_assign(
        self, 
        task_id: str, 
        annotator_id: str,
        priority: int = 0,
        deadline: datetime = None
    ) -> dict:
        """手动分配"""
        if not annotator_id:
            raise ValueError("annotator_id is required for manual assignment")
        
        assignment = await self._create_assignment(task_id, annotator_id, priority, deadline)
        
        # 更新标注员工作负载
        if annotator_id in self._annotators:
            self._annotators[annotator_id]["current_workload"] = \
                self._annotators[annotator_id].get("current_workload", 0) + 1
        
        if self.notification_service:
            await self.notification_service.notify_task_assigned(annotator_id, task_id)
        
        return assignment
    
    async def _get_task(self, task_id: str) -> dict:
        """获取任务信息"""
        if task_id in self._tasks:
            return self._tasks[task_id]
        # 实际实现会从数据库获取
        return {"id": task_id, "required_skills": []}
    
    async def _get_skill_matched_annotators(self, required_skills: List[str]) -> List[dict]:
        """获取技能匹配的标注员
        
        Args:
            required_skills: 所需技能列表
            
        Returns:
            匹配的标注员列表
        """
        if not required_skills:
            # 无技能要求，返回所有可用标注员
            return [a for a in self._annotators.values() if a.get("status") != "disabled"]
        
        required_set = set(required_skills)
        matched = []
        
        for annotator in self._annotators.values():
            if annotator.get("status") == "disabled":
                continue
            
            annotator_skills = set(annotator.get("skills", []))
            if required_set.issubset(annotator_skills):
                matched.append(annotator)
        
        return matched
    
    async def _sort_by_workload(self, annotators: List[dict]) -> List[dict]:
        """按工作负载排序（负载低的优先）"""
        return sorted(annotators, key=lambda x: x.get("current_workload", 0))
    
    async def _create_assignment(
        self,
        task_id: str,
        annotator_id: str,
        priority: int = 0,
        deadline: datetime = None
    ) -> dict:
        """创建分配记录"""
        assignment = {
            "id": str(uuid4()),
            "task_id": task_id,
            "annotator_id": annotator_id,
            "priority": priority,
            "deadline": deadline,
            "status": "assigned",
            "assigned_at": datetime.utcnow()
        }
        self._assignments[assignment["id"]] = assignment
        return assignment
    
    # ============== Priority and Deadline ==============
    
    async def set_priority(self, task_id: str, priority: int) -> dict:
        """设置任务优先级"""
        if task_id in self._tasks:
            self._tasks[task_id]["priority"] = priority
        
        # 更新相关分配记录
        for assignment in self._assignments.values():
            if assignment["task_id"] == task_id:
                assignment["priority"] = priority
        
        return {"task_id": task_id, "priority": priority}
    
    async def set_deadline(self, task_id: str, deadline: datetime) -> dict:
        """设置截止时间"""
        if task_id in self._tasks:
            self._tasks[task_id]["deadline"] = deadline
        
        # 更新相关分配记录
        for assignment in self._assignments.values():
            if assignment["task_id"] == task_id:
                assignment["deadline"] = deadline
        
        return {"task_id": task_id, "deadline": deadline}
    
    # ============== Query Methods ==============
    
    async def get_pending_tasks(self, annotator_id: str) -> List[dict]:
        """获取待处理任务"""
        pending = []
        for assignment in self._assignments.values():
            if assignment["annotator_id"] == annotator_id and assignment["status"] == "assigned":
                task = self._tasks.get(assignment["task_id"], {"id": assignment["task_id"]})
                pending.append({
                    **task,
                    "assignment_id": assignment["id"],
                    "priority": assignment["priority"],
                    "deadline": assignment["deadline"]
                })
        return sorted(pending, key=lambda x: (-x.get("priority", 0), x.get("deadline") or datetime.max))
    
    async def get_assignment(self, assignment_id: str) -> Optional[dict]:
        """获取分配记录"""
        return self._assignments.get(assignment_id)
    
    async def get_task_assignment(self, task_id: str) -> Optional[dict]:
        """获取任务的分配记录"""
        for assignment in self._assignments.values():
            if assignment["task_id"] == task_id:
                return assignment
        return None
    
    # ============== Skill Matching ==============
    
    def is_skill_matched(self, task: dict, annotator: dict) -> bool:
        """检查标注员是否具备任务所需技能
        
        Args:
            task: 任务信息（包含 required_skills）
            annotator: 标注员信息（包含 skills）
            
        Returns:
            是否匹配
        """
        required_skills = set(task.get("required_skills", []))
        annotator_skills = set(annotator.get("skills", []))
        return required_skills.issubset(annotator_skills)
    
    # ============== Workload Balancing ==============
    
    def calculate_workload_balance(self, annotator_ids: List[str] = None) -> dict:
        """计算工作负载均衡度
        
        Args:
            annotator_ids: 标注员ID列表（可选）
            
        Returns:
            包含 mean, std, cv (变异系数) 的字典
        """
        if annotator_ids is None:
            annotators = list(self._annotators.values())
        else:
            annotators = [self._annotators[aid] for aid in annotator_ids if aid in self._annotators]
        
        if not annotators:
            return {"mean": 0, "std": 0, "cv": 0}
        
        workloads = [a.get("current_workload", 0) for a in annotators]
        
        mean = statistics.mean(workloads)
        
        if len(workloads) < 2:
            std = 0
        else:
            std = statistics.stdev(workloads)
        
        # 变异系数 (Coefficient of Variation)
        cv = std / mean if mean > 0 else 0
        
        return {
            "mean": mean,
            "std": std,
            "cv": cv,
            "workloads": workloads
        }
    
    async def batch_assign_tasks(
        self,
        task_ids: List[str],
        mode: AssignmentMode = AssignmentMode.AUTO
    ) -> List[dict]:
        """批量分配任务
        
        Args:
            task_ids: 任务ID列表
            mode: 分配模式
            
        Returns:
            分配结果列表
        """
        results = []
        for task_id in task_ids:
            try:
                assignment = await self.assign_task(task_id, mode=mode)
                results.append({"task_id": task_id, "success": True, "assignment": assignment})
            except Exception as e:
                results.append({"task_id": task_id, "success": False, "error": str(e)})
        return results
    
    # ============== Status Management ==============
    
    async def complete_task(self, assignment_id: str) -> dict:
        """完成任务"""
        assignment = self._assignments.get(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")
        
        assignment["status"] = "completed"
        assignment["completed_at"] = datetime.utcnow()
        
        # 减少标注员工作负载
        annotator_id = assignment["annotator_id"]
        if annotator_id in self._annotators:
            self._annotators[annotator_id]["current_workload"] = \
                max(0, self._annotators[annotator_id].get("current_workload", 0) - 1)
        
        return assignment
    
    async def cancel_assignment(self, assignment_id: str) -> dict:
        """取消分配"""
        assignment = self._assignments.get(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")
        
        assignment["status"] = "cancelled"
        
        # 减少标注员工作负载
        annotator_id = assignment["annotator_id"]
        if annotator_id in self._annotators:
            self._annotators[annotator_id]["current_workload"] = \
                max(0, self._annotators[annotator_id].get("current_workload", 0) - 1)
        
        return assignment
