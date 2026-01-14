"""
Review Flow Engine for SuperInsight platform.

Manages the annotation review workflow including submission, approval,
rejection, modification, and history tracking.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import uuid4
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================================
# Review Status and Actions
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
# Data Models
# ============================================================================

class ReviewTask:
    """Review task record."""
    
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
        self.assigned_at: Optional[datetime] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.comments: str = ""
        self.modifications: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "annotation_id": self.annotation_id,
            "annotator_id": self.annotator_id,
            "project_id": self.project_id,
            "reviewer_id": self.reviewer_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "comments": self.comments,
            "modifications": self.modifications,
            "metadata": self.metadata,
        }


class ReviewRecord:
    """Individual review action record."""
    
    def __init__(
        self,
        review_task_id: str,
        annotation_id: str,
        reviewer_id: str,
        action: ReviewAction,
        reason: str = "",
        modifications: Optional[Dict[str, Any]] = None,
    ):
        self.id = str(uuid4())
        self.review_task_id = review_task_id
        self.annotation_id = annotation_id
        self.reviewer_id = reviewer_id
        self.action = action
        self.reason = reason
        self.modifications = modifications or {}
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "review_task_id": self.review_task_id,
            "annotation_id": self.annotation_id,
            "reviewer_id": self.reviewer_id,
            "action": self.action.value,
            "reason": self.reason,
            "modifications": self.modifications,
            "created_at": self.created_at.isoformat(),
        }


class ReviewResult:
    """Result of a review action."""
    
    def __init__(
        self,
        review_task: ReviewTask,
        action: ReviewAction,
        success: bool,
        message: str = "",
    ):
        self.review_task = review_task
        self.action = action
        self.success = success
        self.message = message
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "review_task": self.review_task.to_dict(),
            "action": self.action.value,
            "success": self.success,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# Review Flow Configuration
# ============================================================================

class ReviewFlowConfig:
    """Configuration for review flow."""
    
    def __init__(
        self,
        require_reviewer_assignment: bool = True,
        auto_assign_reviewer: bool = True,
        allow_self_review: bool = False,
        require_rejection_reason: bool = True,
        max_rejection_count: int = 3,
    ):
        self.require_reviewer_assignment = require_reviewer_assignment
        self.auto_assign_reviewer = auto_assign_reviewer
        self.allow_self_review = allow_self_review
        self.require_rejection_reason = require_rejection_reason
        self.max_rejection_count = max_rejection_count


# ============================================================================
# Review Flow Engine
# ============================================================================

class ReviewFlowEngine:
    """
    Review Flow Engine for annotation review workflow.
    
    Features:
    - Submit annotations for review
    - Assign reviewers
    - Approve/reject/modify annotations
    - Track review history
    - Batch operations
    """
    
    def __init__(self, config: Optional[ReviewFlowConfig] = None):
        """Initialize the review flow engine."""
        self.config = config or ReviewFlowConfig()
        self._review_tasks: Dict[str, ReviewTask] = {}
        self._annotation_reviews: Dict[str, str] = {}  # annotation_id -> review_task_id
        self._review_history: Dict[str, List[ReviewRecord]] = defaultdict(list)
        self._available_reviewers: List[str] = []
        self._lock = asyncio.Lock()
    
    # ========================================================================
    # Reviewer Management
    # ========================================================================
    
    def register_reviewer(self, reviewer_id: str) -> None:
        """Register a reviewer."""
        if reviewer_id not in self._available_reviewers:
            self._available_reviewers.append(reviewer_id)
            logger.info(f"Registered reviewer: {reviewer_id}")
    
    def unregister_reviewer(self, reviewer_id: str) -> None:
        """Unregister a reviewer."""
        if reviewer_id in self._available_reviewers:
            self._available_reviewers.remove(reviewer_id)
            logger.info(f"Unregistered reviewer: {reviewer_id}")
    
    # ========================================================================
    # Review Submission
    # ========================================================================
    
    async def submit_for_review(
        self,
        annotation_id: str,
        annotator_id: str,
        project_id: Optional[str] = None,
    ) -> ReviewTask:
        """
        Submit an annotation for review.
        
        Args:
            annotation_id: Annotation ID
            annotator_id: Annotator ID
            project_id: Optional project ID
            
        Returns:
            ReviewTask
        """
        async with self._lock:
            # Check if already submitted
            if annotation_id in self._annotation_reviews:
                existing_id = self._annotation_reviews[annotation_id]
                existing = self._review_tasks.get(existing_id)
                if existing and existing.status == ReviewStatus.PENDING:
                    return existing
            
            # Create review task
            task = ReviewTask(
                annotation_id=annotation_id,
                annotator_id=annotator_id,
                project_id=project_id,
            )
            
            # Store task
            self._review_tasks[task.id] = task
            self._annotation_reviews[annotation_id] = task.id
            
            # Record action
            self._record_action(
                task.id, annotation_id, annotator_id,
                ReviewAction.SUBMIT
            )
            
            # Auto-assign reviewer if configured
            if self.config.auto_assign_reviewer:
                await self._auto_assign_reviewer(task)
            
            logger.info(f"Submitted annotation {annotation_id} for review")
            
            return task
    
    async def assign_reviewer(
        self,
        review_task_id: str,
        reviewer_id: Optional[str] = None,
    ) -> ReviewTask:
        """
        Assign a reviewer to a review task.
        
        Args:
            review_task_id: Review task ID
            reviewer_id: Optional specific reviewer ID
            
        Returns:
            Updated ReviewTask
        """
        async with self._lock:
            task = self._review_tasks.get(review_task_id)
            if not task:
                raise ValueError(f"Review task not found: {review_task_id}")
            
            # Select reviewer
            if not reviewer_id:
                reviewer_id = self._select_reviewer(task.annotator_id)
            
            if not reviewer_id:
                raise ValueError("No available reviewer")
            
            # Check self-review
            if not self.config.allow_self_review and reviewer_id == task.annotator_id:
                raise ValueError("Self-review not allowed")
            
            # Assign
            task.reviewer_id = reviewer_id
            task.assigned_at = datetime.utcnow()
            
            # Record action
            self._record_action(
                task.id, task.annotation_id, reviewer_id,
                ReviewAction.ASSIGN
            )
            
            logger.info(f"Assigned reviewer {reviewer_id} to task {review_task_id}")
            
            return task
    
    # ========================================================================
    # Review Actions
    # ========================================================================
    
    async def approve(
        self,
        review_task_id: str,
        reviewer_id: str,
        comments: str = "",
    ) -> ReviewResult:
        """
        Approve an annotation.
        
        Args:
            review_task_id: Review task ID
            reviewer_id: Reviewer ID
            comments: Optional comments
            
        Returns:
            ReviewResult
        """
        async with self._lock:
            task = self._review_tasks.get(review_task_id)
            if not task:
                return ReviewResult(
                    ReviewTask("", ""), ReviewAction.APPROVE,
                    False, "Review task not found"
                )
            
            # Validate reviewer
            if task.reviewer_id and task.reviewer_id != reviewer_id:
                return ReviewResult(
                    task, ReviewAction.APPROVE,
                    False, "Not assigned reviewer"
                )
            
            # Update status
            task.status = ReviewStatus.APPROVED
            task.completed_at = datetime.utcnow()
            task.comments = comments
            
            # Record action
            self._record_action(
                task.id, task.annotation_id, reviewer_id,
                ReviewAction.APPROVE, comments
            )
            
            logger.info(f"Approved annotation {task.annotation_id}")
            
            return ReviewResult(task, ReviewAction.APPROVE, True, "Approved")
    
    async def reject(
        self,
        review_task_id: str,
        reviewer_id: str,
        reason: str,
    ) -> ReviewResult:
        """
        Reject an annotation.
        
        Property 4: 审核驳回退回
        - Task should be returned to original annotator
        - Rejection reason must be attached
        
        Args:
            review_task_id: Review task ID
            reviewer_id: Reviewer ID
            reason: Rejection reason (required)
            
        Returns:
            ReviewResult
        """
        async with self._lock:
            task = self._review_tasks.get(review_task_id)
            if not task:
                return ReviewResult(
                    ReviewTask("", ""), ReviewAction.REJECT,
                    False, "Review task not found"
                )
            
            # Validate reviewer
            if task.reviewer_id and task.reviewer_id != reviewer_id:
                return ReviewResult(
                    task, ReviewAction.REJECT,
                    False, "Not assigned reviewer"
                )
            
            # Require rejection reason
            if self.config.require_rejection_reason and not reason:
                return ReviewResult(
                    task, ReviewAction.REJECT,
                    False, "Rejection reason required"
                )
            
            # Update status - task returns to annotator
            task.status = ReviewStatus.REJECTED
            task.completed_at = datetime.utcnow()
            task.comments = reason
            
            # Record action with reason
            self._record_action(
                task.id, task.annotation_id, reviewer_id,
                ReviewAction.REJECT, reason
            )
            
            logger.info(
                f"Rejected annotation {task.annotation_id}, "
                f"returning to annotator {task.annotator_id}"
            )
            
            return ReviewResult(
                task, ReviewAction.REJECT, True,
                f"Rejected and returned to annotator: {reason}"
            )
    
    async def modify(
        self,
        review_task_id: str,
        reviewer_id: str,
        modifications: Dict[str, Any],
        comments: str = "",
    ) -> ReviewResult:
        """
        Modify an annotation during review.
        
        Args:
            review_task_id: Review task ID
            reviewer_id: Reviewer ID
            modifications: Modifications to apply
            comments: Optional comments
            
        Returns:
            ReviewResult
        """
        async with self._lock:
            task = self._review_tasks.get(review_task_id)
            if not task:
                return ReviewResult(
                    ReviewTask("", ""), ReviewAction.MODIFY,
                    False, "Review task not found"
                )
            
            # Validate reviewer
            if task.reviewer_id and task.reviewer_id != reviewer_id:
                return ReviewResult(
                    task, ReviewAction.MODIFY,
                    False, "Not assigned reviewer"
                )
            
            # Store modifications
            task.modifications = modifications
            task.comments = comments
            task.status = ReviewStatus.APPROVED  # Modified and approved
            task.completed_at = datetime.utcnow()
            
            # Record action
            self._record_action(
                task.id, task.annotation_id, reviewer_id,
                ReviewAction.MODIFY, comments, modifications
            )
            
            logger.info(f"Modified and approved annotation {task.annotation_id}")
            
            return ReviewResult(
                task, ReviewAction.MODIFY, True,
                "Modified and approved"
            )
    
    async def request_modification(
        self,
        review_task_id: str,
        reviewer_id: str,
        comments: str,
    ) -> ReviewResult:
        """
        Request modification from annotator.
        
        Args:
            review_task_id: Review task ID
            reviewer_id: Reviewer ID
            comments: Modification request comments
            
        Returns:
            ReviewResult
        """
        async with self._lock:
            task = self._review_tasks.get(review_task_id)
            if not task:
                return ReviewResult(
                    ReviewTask("", ""), ReviewAction.REQUEST_MODIFICATION,
                    False, "Review task not found"
                )
            
            # Update status
            task.status = ReviewStatus.MODIFICATION_REQUESTED
            task.comments = comments
            
            # Record action
            self._record_action(
                task.id, task.annotation_id, reviewer_id,
                ReviewAction.REQUEST_MODIFICATION, comments
            )
            
            logger.info(
                f"Requested modification for annotation {task.annotation_id}"
            )
            
            return ReviewResult(
                task, ReviewAction.REQUEST_MODIFICATION, True,
                "Modification requested"
            )
    
    # ========================================================================
    # Batch Operations
    # ========================================================================
    
    async def batch_approve(
        self,
        review_task_ids: List[str],
        reviewer_id: str,
        comments: str = "",
    ) -> List[ReviewResult]:
        """
        Batch approve multiple annotations.
        
        Args:
            review_task_ids: List of review task IDs
            reviewer_id: Reviewer ID
            comments: Optional comments
            
        Returns:
            List of ReviewResult
        """
        results = []
        for task_id in review_task_ids:
            result = await self.approve(task_id, reviewer_id, comments)
            results.append(result)
        return results
    
    async def batch_reject(
        self,
        review_task_ids: List[str],
        reviewer_id: str,
        reason: str,
    ) -> List[ReviewResult]:
        """
        Batch reject multiple annotations.
        
        Args:
            review_task_ids: List of review task IDs
            reviewer_id: Reviewer ID
            reason: Rejection reason
            
        Returns:
            List of ReviewResult
        """
        results = []
        for task_id in review_task_ids:
            result = await self.reject(task_id, reviewer_id, reason)
            results.append(result)
        return results
    
    # ========================================================================
    # History and Queries
    # ========================================================================
    
    async def get_review_history(
        self,
        annotation_id: str,
    ) -> List[ReviewRecord]:
        """
        Get review history for an annotation.
        
        Args:
            annotation_id: Annotation ID
            
        Returns:
            List of ReviewRecord
        """
        return self._review_history.get(annotation_id, [])
    
    async def get_review_task(
        self,
        review_task_id: str,
    ) -> Optional[ReviewTask]:
        """
        Get a review task by ID.
        
        Args:
            review_task_id: Review task ID
            
        Returns:
            ReviewTask or None
        """
        return self._review_tasks.get(review_task_id)
    
    async def get_pending_reviews(
        self,
        reviewer_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ReviewTask]:
        """
        Get pending review tasks.
        
        Args:
            reviewer_id: Optional filter by reviewer
            limit: Maximum number of tasks
            
        Returns:
            List of ReviewTask
        """
        tasks = []
        for task in self._review_tasks.values():
            if task.status != ReviewStatus.PENDING:
                continue
            if reviewer_id and task.reviewer_id != reviewer_id:
                continue
            tasks.append(task)
        
        # Sort by creation time
        tasks.sort(key=lambda t: t.created_at)
        return tasks[:limit]
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _auto_assign_reviewer(self, task: ReviewTask) -> None:
        """Auto-assign a reviewer to a task."""
        reviewer_id = self._select_reviewer(task.annotator_id)
        if reviewer_id:
            task.reviewer_id = reviewer_id
            task.assigned_at = datetime.utcnow()
    
    def _select_reviewer(
        self,
        exclude_user_id: Optional[str] = None,
    ) -> Optional[str]:
        """Select an available reviewer."""
        candidates = [
            r for r in self._available_reviewers
            if r != exclude_user_id or self.config.allow_self_review
        ]
        
        if not candidates:
            return None
        
        # Simple round-robin selection
        return candidates[0]
    
    def _record_action(
        self,
        review_task_id: str,
        annotation_id: str,
        user_id: str,
        action: ReviewAction,
        reason: str = "",
        modifications: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a review action."""
        record = ReviewRecord(
            review_task_id=review_task_id,
            annotation_id=annotation_id,
            reviewer_id=user_id,
            action=action,
            reason=reason,
            modifications=modifications,
        )
        self._review_history[annotation_id].append(record)


# ============================================================================
# Singleton Instance
# ============================================================================

_engine_instance: Optional[ReviewFlowEngine] = None


def get_review_flow_engine() -> ReviewFlowEngine:
    """
    Get or create the review flow engine instance.
    
    Returns:
        ReviewFlowEngine instance
    """
    global _engine_instance
    
    if _engine_instance is None:
        _engine_instance = ReviewFlowEngine()
    
    return _engine_instance
