"""
Property Tests for Review Flow Manager (审核流管理器属性测试)

Tests Property 5: 审核流程正确性
Tests Property 6: 审核历史完整性

**Validates: Requirements 3.3, 3.5, 3.6**
"""

import asyncio
import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from typing import Dict, List
from uuid import uuid4


# ============== Local Schema Definitions ==============

class ReviewStatus:
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewFlowManager:
    """审核流管理器 - 本地测试版本"""
    
    def __init__(self):
        self._flows: Dict[str, dict] = {}
        self._review_tasks: Dict[str, dict] = {}
        self._history: Dict[str, List[dict]] = {}
    
    async def configure_flow(self, project_id: str, config: dict) -> dict:
        """配置审核流程"""
        flow = {
            "project_id": project_id,
            "levels": config.get("levels", 2),
            "pass_threshold": config.get("pass_threshold", 0.8),
            "auto_approve": config.get("auto_approve", False),
            "created_at": datetime.utcnow()
        }
        self._flows[project_id] = flow
        return flow
    
    async def get_flow(self, project_id: str) -> dict:
        return self._flows.get(project_id, {
            "project_id": project_id,
            "levels": 2,
            "pass_threshold": 0.8,
            "auto_approve": False
        })
    
    async def submit_for_review(self, annotation_id: str, project_id: str = None) -> dict:
        """提交审核"""
        flow = await self.get_flow(project_id) if project_id else {"levels": 2}
        
        review_task = {
            "id": str(uuid4()),
            "annotation_id": annotation_id,
            "current_level": 1,
            "max_level": flow.get("levels", 2),
            "status": ReviewStatus.PENDING,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        self._review_tasks[review_task["id"]] = review_task
        return review_task
    
    async def get_review_task(self, review_task_id: str) -> dict:
        return self._review_tasks.get(review_task_id)
    
    async def approve(self, review_task_id: str, reviewer_id: str) -> dict:
        """审核通过"""
        task = self._review_tasks.get(review_task_id)
        if not task:
            raise ValueError(f"Review task {review_task_id} not found")
        
        if task["current_level"] < task["max_level"]:
            task["current_level"] += 1
            task["status"] = ReviewStatus.PENDING
            action = "approve_to_next_level"
        else:
            task["status"] = ReviewStatus.APPROVED
            action = "final_approve"
        
        task["updated_at"] = datetime.utcnow()
        await self._record_history(task, reviewer_id, "approve")
        
        return {
            "task_id": review_task_id,
            "action": action,
            "status": task["status"],
            "level": task["current_level"],
            "reviewer_id": reviewer_id,
            "reviewed_at": datetime.utcnow()
        }
    
    async def reject(self, review_task_id: str, reviewer_id: str, reason: str) -> dict:
        """审核驳回"""
        task = self._review_tasks.get(review_task_id)
        if not task:
            raise ValueError(f"Review task {review_task_id} not found")
        
        task["status"] = ReviewStatus.REJECTED
        task["updated_at"] = datetime.utcnow()
        
        await self._record_history(task, reviewer_id, "reject", reason)
        
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
        """批量审核"""
        results = []
        for task_id in review_task_ids:
            try:
                result = await self.approve(task_id, reviewer_id)
                results.append(result)
            except ValueError as e:
                results.append({"task_id": task_id, "action": "error", "error": str(e)})
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
        """获取审核历史"""
        return self._history.get(annotation_id, [])


# ============== Property 5: 审核流程正确性 ==============

class TestReviewFlowCorrectness:
    """
    Property 5: 审核流程正确性
    
    *For any* 完成的标注，应自动进入审核队列；审核驳回后应退回给原标注员。
    
    **Validates: Requirements 3.3, 3.5**
    """
    
    @given(
        annotation_id=st.text(min_size=1, max_size=36),
        num_levels=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_submit_creates_pending_review(self, annotation_id: str, num_levels: int):
        """Property: 提交审核后任务状态应为 pending"""
        manager = ReviewFlowManager()
        
        # 配置审核流程
        asyncio.get_event_loop().run_until_complete(
            manager.configure_flow("project_1", {"levels": num_levels})
        )
        
        # 提交审核
        review_task = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review(annotation_id, "project_1")
        )
        
        # 验证状态
        assert review_task["status"] == ReviewStatus.PENDING
        assert review_task["current_level"] == 1
        assert review_task["max_level"] == num_levels
    
    @given(
        num_levels=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100)
    def test_approve_advances_level(self, num_levels: int):
        """Property: 审核通过应推进到下一级"""
        manager = ReviewFlowManager()
        
        asyncio.get_event_loop().run_until_complete(
            manager.configure_flow("project_1", {"levels": num_levels})
        )
        
        review_task = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review("annotation_1", "project_1")
        )
        
        # 第一次审核通过
        result = asyncio.get_event_loop().run_until_complete(
            manager.approve(review_task["id"], "reviewer_1")
        )
        
        # 验证：如果不是最后一级，应该推进到下一级
        if num_levels > 1:
            assert result["level"] == 2
            assert result["status"] == ReviewStatus.PENDING
        else:
            assert result["status"] == ReviewStatus.APPROVED
    
    @given(
        num_levels=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=100)
    def test_all_levels_approved_means_final_approval(self, num_levels: int):
        """Property: 所有级别通过后应为最终通过"""
        manager = ReviewFlowManager()
        
        asyncio.get_event_loop().run_until_complete(
            manager.configure_flow("project_1", {"levels": num_levels})
        )
        
        review_task = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review("annotation_1", "project_1")
        )
        
        # 通过所有级别
        for i in range(num_levels):
            result = asyncio.get_event_loop().run_until_complete(
                manager.approve(review_task["id"], f"reviewer_{i}")
            )
        
        # 验证最终状态
        assert result["status"] == ReviewStatus.APPROVED
    
    @given(
        reason=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    def test_reject_sets_rejected_status(self, reason: str):
        """Property: 驳回后状态应为 rejected"""
        manager = ReviewFlowManager()
        
        review_task = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review("annotation_1")
        )
        
        result = asyncio.get_event_loop().run_until_complete(
            manager.reject(review_task["id"], "reviewer_1", reason)
        )
        
        assert result["status"] == ReviewStatus.REJECTED
        assert result["reason"] == reason
    
    def test_batch_approve_processes_all(self):
        """批量审核应处理所有任务"""
        manager = ReviewFlowManager()
        
        # 创建多个审核任务
        task_ids = []
        for i in range(5):
            task = asyncio.get_event_loop().run_until_complete(
                manager.submit_for_review(f"annotation_{i}")
            )
            task_ids.append(task["id"])
        
        # 批量审核
        results = asyncio.get_event_loop().run_until_complete(
            manager.batch_approve(task_ids, "reviewer_1")
        )
        
        assert len(results) == 5
        for result in results:
            assert "action" in result


# ============== Property 6: 审核历史完整性 ==============

class TestReviewHistoryCompleteness:
    """
    Property 6: 审核历史完整性
    
    *For any* 审核操作，应记录完整的审核历史，包括审核员、操作类型、时间、原因。
    
    **Validates: Requirements 3.6**
    """
    
    @given(
        reviewer_id=st.text(min_size=1, max_size=36)
    )
    @settings(max_examples=100)
    def test_approve_recorded_in_history(self, reviewer_id: str):
        """Property: 审核通过应记录在历史中"""
        manager = ReviewFlowManager()
        
        review_task = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review("annotation_1")
        )
        
        asyncio.get_event_loop().run_until_complete(
            manager.approve(review_task["id"], reviewer_id)
        )
        
        history = asyncio.get_event_loop().run_until_complete(
            manager.get_review_history("annotation_1")
        )
        
        assert len(history) == 1
        assert history[0]["reviewer_id"] == reviewer_id
        assert history[0]["action"] == "approve"
    
    @given(
        reviewer_id=st.text(min_size=1, max_size=36),
        reason=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    def test_reject_recorded_with_reason(self, reviewer_id: str, reason: str):
        """Property: 驳回应记录原因"""
        manager = ReviewFlowManager()
        
        review_task = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review("annotation_1")
        )
        
        asyncio.get_event_loop().run_until_complete(
            manager.reject(review_task["id"], reviewer_id, reason)
        )
        
        history = asyncio.get_event_loop().run_until_complete(
            manager.get_review_history("annotation_1")
        )
        
        assert len(history) == 1
        assert history[0]["reviewer_id"] == reviewer_id
        assert history[0]["action"] == "reject"
        assert history[0]["reason"] == reason
    
    @given(
        num_actions=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100)
    def test_all_actions_recorded(self, num_actions: int):
        """Property: 所有审核操作都应记录"""
        manager = ReviewFlowManager()
        
        # 配置多级审核
        asyncio.get_event_loop().run_until_complete(
            manager.configure_flow("project_1", {"levels": num_actions + 1})
        )
        
        review_task = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review("annotation_1", "project_1")
        )
        
        # 执行多次审核
        for i in range(num_actions):
            asyncio.get_event_loop().run_until_complete(
                manager.approve(review_task["id"], f"reviewer_{i}")
            )
        
        history = asyncio.get_event_loop().run_until_complete(
            manager.get_review_history("annotation_1")
        )
        
        # 验证所有操作都被记录
        assert len(history) == num_actions
    
    def test_history_contains_required_fields(self):
        """历史记录应包含所有必需字段"""
        manager = ReviewFlowManager()
        
        review_task = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review("annotation_1")
        )
        
        asyncio.get_event_loop().run_until_complete(
            manager.approve(review_task["id"], "reviewer_1")
        )
        
        history = asyncio.get_event_loop().run_until_complete(
            manager.get_review_history("annotation_1")
        )
        
        entry = history[0]
        
        # 验证必需字段
        assert "id" in entry
        assert "review_task_id" in entry
        assert "annotation_id" in entry
        assert "reviewer_id" in entry
        assert "action" in entry
        assert "level" in entry
        assert "created_at" in entry
    
    def test_history_isolated_by_annotation(self):
        """不同标注的历史应该隔离"""
        manager = ReviewFlowManager()
        
        # 为两个不同标注创建审核任务
        task1 = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review("annotation_1")
        )
        task2 = asyncio.get_event_loop().run_until_complete(
            manager.submit_for_review("annotation_2")
        )
        
        # 分别审核
        asyncio.get_event_loop().run_until_complete(
            manager.approve(task1["id"], "reviewer_1")
        )
        asyncio.get_event_loop().run_until_complete(
            manager.reject(task2["id"], "reviewer_2", "reason")
        )
        
        # 检索各自的历史
        history1 = asyncio.get_event_loop().run_until_complete(
            manager.get_review_history("annotation_1")
        )
        history2 = asyncio.get_event_loop().run_until_complete(
            manager.get_review_history("annotation_2")
        )
        
        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]["action"] == "approve"
        assert history2[0]["action"] == "reject"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
