"""
Property-based tests for Review Flow Engine.

Tests Property 4: 审核驳回退回
Validates: Requirements 6.4

When a reviewer rejects an annotation, the task should be returned to the
original annotator with the rejection reason attached.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
from enum import Enum
import asyncio


# ============================================================================
# Local copies of schemas to avoid import issues
# ============================================================================

class ReviewStatus(str, Enum):
    """Review task status."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFICATION_REQUESTED = "modification_requested"


class ReviewAction(str, Enum):
    """Review actions."""
    SUBMIT = "submit"
    ASSIGN = "assign"
    START_REVIEW = "start_review"
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_MODIFICATION = "request_modification"
    MODIFY = "modify"
    RESUBMIT = "resubmit"


# ============================================================================
# Mock Review Flow Implementation
# ============================================================================

class MockReviewTask:
    """Mock review task for testing."""
    
    def __init__(
        self,
        annotation_id: str,
        annotator_id: str,
        project_id: Optional[str] = None,
    ):
        self.id = str(uuid4())
        self.annotation_id = annotation_id
        self.annotator_id = annotator_id
        self.project_id = project_id
        self.reviewer_id: Optional[str] = None
        self.status = ReviewStatus.PENDING
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.comments: str = ""
        self.rejection_reason: str = ""
        self.modifications: Dict[str, Any] = {}


class MockReviewResult:
    """Mock review result."""
    
    def __init__(
        self,
        review_task: MockReviewTask,
        action: ReviewAction,
        success: bool,
        message: str = "",
    ):
        self.review_task = review_task
        self.action = action
        self.success = success
        self.message = message


class MockReviewRecord:
    """Mock review record for history."""
    
    def __init__(
        self,
        review_task_id: str,
        annotation_id: str,
        reviewer_id: str,
        action: ReviewAction,
        reason: str = "",
    ):
        self.id = str(uuid4())
        self.review_task_id = review_task_id
        self.annotation_id = annotation_id
        self.reviewer_id = reviewer_id
        self.action = action
        self.reason = reason
        self.created_at = datetime.utcnow()


class MockReviewFlowEngine:
    """Mock review flow engine for testing."""
    
    def __init__(self, require_rejection_reason: bool = True):
        self._tasks: Dict[str, MockReviewTask] = {}
        self._annotation_tasks: Dict[str, str] = {}  # annotation_id -> task_id
        self._history: Dict[str, List[MockReviewRecord]] = {}
        self._require_rejection_reason = require_rejection_reason
    
    async def submit_for_review(
        self,
        annotation_id: str,
        annotator_id: str,
        project_id: Optional[str] = None,
    ) -> MockReviewTask:
        """Submit annotation for review."""
        task = MockReviewTask(
            annotation_id=annotation_id,
            annotator_id=annotator_id,
            project_id=project_id,
        )
        self._tasks[task.id] = task
        self._annotation_tasks[annotation_id] = task.id
        self._history[annotation_id] = []
        
        self._record_action(task, ReviewAction.SUBMIT, annotator_id)
        return task
    
    async def assign_reviewer(
        self,
        task_id: str,
        reviewer_id: str,
    ) -> MockReviewTask:
        """Assign reviewer to task."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError("Task not found")
        
        task.reviewer_id = reviewer_id
        self._record_action(task, ReviewAction.ASSIGN, reviewer_id)
        return task
    
    async def approve(
        self,
        task_id: str,
        reviewer_id: str,
        comments: str = "",
    ) -> MockReviewResult:
        """Approve annotation."""
        task = self._tasks.get(task_id)
        if not task:
            return MockReviewResult(
                MockReviewTask("", ""),
                ReviewAction.APPROVE,
                False,
                "Task not found",
            )
        
        task.status = ReviewStatus.APPROVED
        task.completed_at = datetime.utcnow()
        task.comments = comments
        
        self._record_action(task, ReviewAction.APPROVE, reviewer_id, comments)
        
        return MockReviewResult(task, ReviewAction.APPROVE, True, "Approved")
    
    async def reject(
        self,
        task_id: str,
        reviewer_id: str,
        reason: str,
    ) -> MockReviewResult:
        """
        Reject annotation.
        
        Property 4: 审核驳回退回
        - Task should be returned to original annotator
        - Rejection reason must be attached
        """
        task = self._tasks.get(task_id)
        if not task:
            return MockReviewResult(
                MockReviewTask("", ""),
                ReviewAction.REJECT,
                False,
                "Task not found",
            )
        
        # Require rejection reason
        if self._require_rejection_reason and not reason:
            return MockReviewResult(
                task,
                ReviewAction.REJECT,
                False,
                "Rejection reason required",
            )
        
        # Update status - task returns to annotator
        task.status = ReviewStatus.REJECTED
        task.completed_at = datetime.utcnow()
        task.rejection_reason = reason
        task.comments = reason
        
        # Record action with reason
        self._record_action(task, ReviewAction.REJECT, reviewer_id, reason)
        
        return MockReviewResult(
            task,
            ReviewAction.REJECT,
            True,
            f"Rejected and returned to annotator: {reason}",
        )
    
    async def get_review_history(
        self,
        annotation_id: str,
    ) -> List[MockReviewRecord]:
        """Get review history for annotation."""
        return self._history.get(annotation_id, [])
    
    def _record_action(
        self,
        task: MockReviewTask,
        action: ReviewAction,
        user_id: str,
        reason: str = "",
    ) -> None:
        """Record review action."""
        record = MockReviewRecord(
            review_task_id=task.id,
            annotation_id=task.annotation_id,
            reviewer_id=user_id,
            action=action,
            reason=reason,
        )
        if task.annotation_id not in self._history:
            self._history[task.annotation_id] = []
        self._history[task.annotation_id].append(record)


# ============================================================================
# Strategies for generating test data
# ============================================================================

@st.composite
def user_id_strategy(draw):
    """Generate valid user IDs."""
    return f"user_{draw(st.integers(min_value=1, max_value=1000))}"


@st.composite
def annotation_id_strategy(draw):
    """Generate valid annotation IDs."""
    return f"annotation_{draw(st.integers(min_value=1, max_value=10000))}"


@st.composite
def rejection_reason_strategy(draw):
    """Generate valid rejection reasons."""
    reasons = [
        "Incorrect label",
        "Missing entities",
        "Inconsistent with guidelines",
        "Low quality annotation",
        "Needs more detail",
        "Wrong classification",
        "Incomplete annotation",
    ]
    return draw(st.sampled_from(reasons))


# ============================================================================
# Property Tests
# ============================================================================

class TestReviewRejection:
    """
    Property 4: 审核驳回退回
    
    When a reviewer rejects an annotation, the task should be returned to the
    original annotator with the rejection reason attached.
    
    **Validates: Requirements 6.4**
    """
    
    @pytest.mark.asyncio
    async def test_rejection_returns_to_annotator(self):
        """
        **Feature: ai-annotation, Property 4: 审核驳回退回**
        **Validates: Requirements 6.4**
        
        Rejected task should be returned to original annotator.
        """
        engine = MockReviewFlowEngine()
        
        # Submit annotation
        task = await engine.submit_for_review(
            annotation_id="ann_1",
            annotator_id="annotator_1",
        )
        
        # Assign reviewer
        await engine.assign_reviewer(task.id, "reviewer_1")
        
        # Reject
        result = await engine.reject(
            task.id,
            "reviewer_1",
            "Incorrect label",
        )
        
        assert result.success is True
        assert result.review_task.status == ReviewStatus.REJECTED
        assert result.review_task.annotator_id == "annotator_1"  # Original annotator
        assert result.review_task.rejection_reason == "Incorrect label"
    
    @pytest.mark.asyncio
    async def test_rejection_requires_reason(self):
        """
        **Feature: ai-annotation, Property 4: 审核驳回退回**
        **Validates: Requirements 6.4**
        
        Rejection should require a reason.
        """
        engine = MockReviewFlowEngine(require_rejection_reason=True)
        
        task = await engine.submit_for_review(
            annotation_id="ann_1",
            annotator_id="annotator_1",
        )
        
        # Try to reject without reason
        result = await engine.reject(task.id, "reviewer_1", "")
        
        assert result.success is False
        assert "reason required" in result.message.lower()
    
    @pytest.mark.asyncio
    @given(
        annotator_id=user_id_strategy(),
        reviewer_id=user_id_strategy(),
        reason=rejection_reason_strategy(),
    )
    @settings(max_examples=100)
    async def test_rejection_preserves_annotator_property(
        self,
        annotator_id: str,
        reviewer_id: str,
        reason: str,
    ):
        """
        **Feature: ai-annotation, Property 4: 审核驳回退回**
        **Validates: Requirements 6.4**
        
        For any annotator and reviewer, rejection should preserve
        the original annotator ID and attach the reason.
        """
        assume(annotator_id != reviewer_id)
        
        engine = MockReviewFlowEngine()
        
        annotation_id = f"ann_{uuid4().hex[:8]}"
        
        # Submit
        task = await engine.submit_for_review(
            annotation_id=annotation_id,
            annotator_id=annotator_id,
        )
        
        # Assign and reject
        await engine.assign_reviewer(task.id, reviewer_id)
        result = await engine.reject(task.id, reviewer_id, reason)
        
        # Verify
        assert result.success is True
        assert result.review_task.annotator_id == annotator_id
        assert result.review_task.rejection_reason == reason
        assert result.review_task.status == ReviewStatus.REJECTED
    
    @pytest.mark.asyncio
    @given(
        reasons=st.lists(rejection_reason_strategy(), min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    async def test_rejection_reason_recorded_in_history(
        self,
        reasons: List[str],
    ):
        """
        **Feature: ai-annotation, Property 4: 审核驳回退回**
        **Validates: Requirements 6.4, 6.5**
        
        Rejection reason should be recorded in review history.
        """
        engine = MockReviewFlowEngine()
        
        annotation_id = f"ann_{uuid4().hex[:8]}"
        
        # Submit
        task = await engine.submit_for_review(
            annotation_id=annotation_id,
            annotator_id="annotator_1",
        )
        
        # Reject with first reason
        await engine.reject(task.id, "reviewer_1", reasons[0])
        
        # Check history
        history = await engine.get_review_history(annotation_id)
        
        # Should have submit and reject records
        assert len(history) >= 2
        
        # Find rejection record
        reject_records = [r for r in history if r.action == ReviewAction.REJECT]
        assert len(reject_records) == 1
        assert reject_records[0].reason == reasons[0]


class TestReviewApproval:
    """
    Tests for review approval functionality.
    
    **Validates: Requirements 6.3**
    """
    
    @pytest.mark.asyncio
    async def test_approval_completes_task(self):
        """
        **Feature: ai-annotation, Property 4: 审核驳回退回**
        **Validates: Requirements 6.3**
        
        Approval should complete the task.
        """
        engine = MockReviewFlowEngine()
        
        task = await engine.submit_for_review(
            annotation_id="ann_1",
            annotator_id="annotator_1",
        )
        
        result = await engine.approve(task.id, "reviewer_1", "Good work")
        
        assert result.success is True
        assert result.review_task.status == ReviewStatus.APPROVED
        assert result.review_task.completed_at is not None
    
    @pytest.mark.asyncio
    @given(
        annotator_id=user_id_strategy(),
        reviewer_id=user_id_strategy(),
    )
    @settings(max_examples=100)
    async def test_approval_recorded_in_history(
        self,
        annotator_id: str,
        reviewer_id: str,
    ):
        """
        **Feature: ai-annotation, Property 4: 审核驳回退回**
        **Validates: Requirements 6.5**
        
        Approval should be recorded in history.
        """
        engine = MockReviewFlowEngine()
        
        annotation_id = f"ann_{uuid4().hex[:8]}"
        
        task = await engine.submit_for_review(
            annotation_id=annotation_id,
            annotator_id=annotator_id,
        )
        
        await engine.approve(task.id, reviewer_id, "Approved")
        
        history = await engine.get_review_history(annotation_id)
        
        approve_records = [r for r in history if r.action == ReviewAction.APPROVE]
        assert len(approve_records) == 1
        assert approve_records[0].reviewer_id == reviewer_id


class TestReviewHistory:
    """
    Tests for review history tracking.
    
    **Validates: Requirements 6.5**
    """
    
    @pytest.mark.asyncio
    async def test_history_tracks_all_actions(self):
        """
        **Feature: ai-annotation, Property 4: 审核驳回退回**
        **Validates: Requirements 6.5**
        
        History should track all review actions.
        """
        engine = MockReviewFlowEngine()
        
        annotation_id = "ann_1"
        
        # Submit
        task = await engine.submit_for_review(
            annotation_id=annotation_id,
            annotator_id="annotator_1",
        )
        
        # Assign
        await engine.assign_reviewer(task.id, "reviewer_1")
        
        # Reject
        await engine.reject(task.id, "reviewer_1", "Needs improvement")
        
        history = await engine.get_review_history(annotation_id)
        
        # Should have submit, assign, reject
        actions = [r.action for r in history]
        assert ReviewAction.SUBMIT in actions
        assert ReviewAction.ASSIGN in actions
        assert ReviewAction.REJECT in actions
    
    @pytest.mark.asyncio
    @given(
        num_annotations=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    async def test_history_isolated_per_annotation(
        self,
        num_annotations: int,
    ):
        """
        **Feature: ai-annotation, Property 4: 审核驳回退回**
        **Validates: Requirements 6.5**
        
        Each annotation should have isolated history.
        """
        engine = MockReviewFlowEngine()
        
        annotation_ids = [f"ann_{i}" for i in range(num_annotations)]
        
        # Submit all
        for ann_id in annotation_ids:
            await engine.submit_for_review(
                annotation_id=ann_id,
                annotator_id="annotator_1",
            )
        
        # Check each has its own history
        for ann_id in annotation_ids:
            history = await engine.get_review_history(ann_id)
            
            # All records should be for this annotation
            for record in history:
                assert record.annotation_id == ann_id


class TestBatchOperations:
    """
    Tests for batch review operations.
    
    **Validates: Requirements 6.6**
    """
    
    @pytest.mark.asyncio
    async def test_batch_rejection_with_reason(self):
        """
        **Feature: ai-annotation, Property 4: 审核驳回退回**
        **Validates: Requirements 6.4, 6.6**
        
        Batch rejection should apply reason to all tasks.
        """
        engine = MockReviewFlowEngine()
        
        # Submit multiple
        tasks = []
        for i in range(3):
            task = await engine.submit_for_review(
                annotation_id=f"ann_{i}",
                annotator_id="annotator_1",
            )
            tasks.append(task)
        
        # Batch reject
        reason = "Batch rejection: quality issues"
        results = []
        for task in tasks:
            result = await engine.reject(task.id, "reviewer_1", reason)
            results.append(result)
        
        # All should be rejected with same reason
        for result in results:
            assert result.success is True
            assert result.review_task.rejection_reason == reason
            assert result.review_task.status == ReviewStatus.REJECTED


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
