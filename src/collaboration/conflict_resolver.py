"""
Conflict Resolver (冲突解决器)

Handles annotation conflicts and disagreements.
"""

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ConflictResolver:
    """冲突解决器 - 处理标注冲突和分歧"""
    
    def __init__(self, db: "AsyncSession" = None, notification_service=None):
        self.db = db
        self.notification_service = notification_service
        self._conflicts: Dict[str, dict] = {}  # conflict_id -> conflict
        self._votes: Dict[str, List[dict]] = {}  # conflict_id -> votes
        self._resolutions: Dict[str, dict] = {}  # conflict_id -> resolution
    
    async def detect_conflicts(self, task_id: str, versions: List[dict]) -> List[dict]:
        """检测标注冲突
        
        Args:
            task_id: 任务ID
            versions: 标注版本列表
            
        Returns:
            冲突列表
        """
        conflicts = []
        
        for i, v1 in enumerate(versions):
            for v2 in versions[i+1:]:
                if self._has_conflict(v1.get("annotation", {}), v2.get("annotation", {})):
                    conflict = {
                        "id": str(uuid4()),
                        "task_id": task_id,
                        "version1_id": v1.get("id"),
                        "version2_id": v2.get("id"),
                        "conflict_type": self._get_conflict_type(v1, v2),
                        "status": "unresolved",
                        "created_at": datetime.utcnow()
                    }
                    self._conflicts[conflict["id"]] = conflict
                    conflicts.append(conflict)
        
        if conflicts and self.notification_service:
            await self._notify_conflicts(task_id, conflicts)
        
        return conflicts
    
    def _has_conflict(self, annotation1: Dict[str, Any], annotation2: Dict[str, Any]) -> bool:
        """检查两个标注是否存在冲突"""
        # 简单比较：如果标注内容不同则认为有冲突
        return annotation1 != annotation2
    
    def _get_conflict_type(self, v1: dict, v2: dict) -> str:
        """获取冲突类型"""
        a1 = v1.get("annotation", {})
        a2 = v2.get("annotation", {})
        
        # 检查标签冲突
        if a1.get("label") != a2.get("label"):
            return "label_mismatch"
        
        # 检查边界冲突
        if a1.get("start") != a2.get("start") or a1.get("end") != a2.get("end"):
            return "boundary_mismatch"
        
        return "content_mismatch"
    
    async def _notify_conflicts(self, task_id: str, conflicts: List[dict]) -> None:
        """通知相关人员存在冲突"""
        if self.notification_service:
            await self.notification_service.notify_conflicts(task_id, len(conflicts))
    
    async def get_conflict(self, conflict_id: str) -> Optional[dict]:
        """获取冲突详情"""
        return self._conflicts.get(conflict_id)
    
    async def vote(self, conflict_id: str, voter_id: str, choice: str) -> dict:
        """投票
        
        Args:
            conflict_id: 冲突ID
            voter_id: 投票者ID
            choice: 选择（version1/version2/other）
            
        Returns:
            Vote dict
        """
        vote = {
            "conflict_id": conflict_id,
            "voter_id": voter_id,
            "choice": choice,
            "voted_at": datetime.utcnow()
        }
        
        if conflict_id not in self._votes:
            self._votes[conflict_id] = []
        
        # 检查是否已投票
        existing = [v for v in self._votes[conflict_id] if v["voter_id"] == voter_id]
        if existing:
            # 更新投票
            existing[0]["choice"] = choice
            existing[0]["voted_at"] = datetime.utcnow()
        else:
            self._votes[conflict_id].append(vote)
        
        # 更新冲突状态
        conflict = self._conflicts.get(conflict_id)
        if conflict:
            conflict["status"] = "voting"
        
        return vote
    
    async def get_votes(self, conflict_id: str) -> List[dict]:
        """获取投票列表"""
        return self._votes.get(conflict_id, [])
    
    async def resolve_by_voting(self, conflict_id: str, min_votes: int = 3) -> dict:
        """投票解决冲突
        
        Args:
            conflict_id: 冲突ID
            min_votes: 最少投票数
            
        Returns:
            ConflictResolution dict
        """
        votes = self._votes.get(conflict_id, [])
        
        if len(votes) < min_votes:
            raise ValueError(f"Not enough votes. Need at least {min_votes}, got {len(votes)}")
        
        # 统计投票
        vote_counts = Counter(v["choice"] for v in votes)
        winner = vote_counts.most_common(1)[0][0]
        
        resolution = {
            "id": str(uuid4()),
            "conflict_id": conflict_id,
            "method": "voting",
            "result": {"winner": winner},
            "vote_counts": dict(vote_counts),
            "expert_id": None,
            "resolved_at": datetime.utcnow()
        }
        
        self._resolutions[conflict_id] = resolution
        
        # 更新冲突状态
        conflict = self._conflicts.get(conflict_id)
        if conflict:
            conflict["status"] = "resolved"
        
        return resolution
    
    async def resolve_by_expert(
        self,
        conflict_id: str,
        expert_id: str,
        decision: Dict[str, Any]
    ) -> dict:
        """专家仲裁解决冲突
        
        Args:
            conflict_id: 冲突ID
            expert_id: 专家ID
            decision: 专家决策
            
        Returns:
            ConflictResolution dict
        """
        resolution = {
            "id": str(uuid4()),
            "conflict_id": conflict_id,
            "method": "expert",
            "result": decision,
            "vote_counts": None,
            "expert_id": expert_id,
            "resolved_at": datetime.utcnow()
        }
        
        self._resolutions[conflict_id] = resolution
        
        # 更新冲突状态
        conflict = self._conflicts.get(conflict_id)
        if conflict:
            conflict["status"] = "resolved"
        
        return resolution
    
    async def get_resolution(self, conflict_id: str) -> Optional[dict]:
        """获取冲突解决结果"""
        return self._resolutions.get(conflict_id)
    
    async def generate_conflict_report(self, project_id: str) -> dict:
        """生成冲突分析报告
        
        Args:
            project_id: 项目ID
            
        Returns:
            ConflictReport dict
        """
        # 筛选项目相关的冲突
        project_conflicts = [c for c in self._conflicts.values()]
        
        resolved = [c for c in project_conflicts if c["status"] == "resolved"]
        unresolved = [c for c in project_conflicts if c["status"] != "resolved"]
        
        # 统计解决方法
        resolution_methods = Counter()
        for conflict_id, resolution in self._resolutions.items():
            resolution_methods[resolution["method"]] += 1
        
        # 统计冲突类型
        conflict_types = Counter(c["conflict_type"] for c in project_conflicts)
        
        return {
            "project_id": project_id,
            "total_conflicts": len(project_conflicts),
            "resolved_conflicts": len(resolved),
            "unresolved_conflicts": len(unresolved),
            "resolution_methods": dict(resolution_methods),
            "conflict_types": dict(conflict_types),
            "generated_at": datetime.utcnow()
        }
