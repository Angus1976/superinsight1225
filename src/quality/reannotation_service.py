"""
Re-annotation Service for SuperInsight Platform.

Provides automatic re-annotation functionality:
- Quality-triggered re-annotation
- Task management integration
- Quality verification
- Workflow automation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid
import asyncio

logger = logging.getLogger(__name__)


class ReannotationReason(str, Enum):
    """Reasons for re-annotation."""
    LOW_QUALITY = "low_quality"
    LOW_AGREEMENT = "low_agreement"
    ANOMALY_DETECTED = "anomaly_detected"
    EXPERT_REVIEW = "expert_review"
    GUIDELINE_UPDATE = "guideline_update"
    DATA_CORRECTION = "data_correction"
    RANDOM_SAMPLE = "random_sample"
    USER_REQUEST = "user_request"


class ReannotationStatus(str, Enum):
    """Status of re-annotation tasks."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReannotationPriority(str, Enum):
    """Priority levels for re-annotation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ReannotationTask:
    """Represents a re-annotation task."""
    task_id: str
    original_task_id: str
    original_annotation_id: Optional[str]
    reason: ReannotationReason
    priority: ReannotationPriority
    status: ReannotationStatus
    project_id: str
    data_item_id: str
    original_annotator_id: Optional[str] = None
    assigned_annotator_id: Optional[str] = None
    quality_threshold: float = 0.8
    original_quality_score: Optional[float] = None
    new_quality_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "original_task_id": self.original_task_id,
            "original_annotation_id": self.original_annotation_id,
            "reason": self.reason.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "project_id": self.project_id,
            "data_item_id": self.data_item_id,
            "original_annotator_id": self.original_annotator_id,
            "assigned_annotator_id": self.assigned_annotator_id,
            "quality_threshold": self.quality_threshold,
            "original_quality_score": self.original_quality_score,
            "new_quality_score": self.new_quality_score,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verification_notes": self.verification_notes
        }


@dataclass
class ReannotationBatch:
    """Represents a batch of re-annotation tasks."""
    batch_id: str
    name: str
    description: str
    reason: ReannotationReason
    project_id: str
    task_ids: List[str] = field(default_factory=list)
    total_tasks: int = 0
    completed_tasks: int = 0
    verified_tasks: int = 0
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "name": self.name,
            "description": self.description,
            "reason": self.reason.value,
            "project_id": self.project_id,
            "task_ids": self.task_ids,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "verified_tasks": self.verified_tasks,
            "status": self.status,
            "progress": self.completed_tasks / self.total_tasks if self.total_tasks > 0 else 0,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class AnnotatorSelector:
    """Selects appropriate annotators for re-annotation."""

    def __init__(self):
        self.annotator_profiles: Dict[str, Dict[str, Any]] = {}
        self.skill_requirements: Dict[str, List[str]] = {}

    def register_annotator(
        self,
        annotator_id: str,
        skills: List[str],
        quality_score: float,
        availability: float = 1.0
    ):
        """Register an annotator with their profile."""
        self.annotator_profiles[annotator_id] = {
            "skills": skills,
            "quality_score": quality_score,
            "availability": availability,
            "current_workload": 0,
            "completed_reannotations": 0
        }

    def select_annotator(
        self,
        task: ReannotationTask,
        exclude_original: bool = True,
        required_skills: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Select the best annotator for a re-annotation task.
        
        Args:
            task: The re-annotation task
            exclude_original: Whether to exclude the original annotator
            required_skills: Required skills for the task
            
        Returns:
            Selected annotator ID or None
        """
        candidates = []
        
        for annotator_id, profile in self.annotator_profiles.items():
            # Exclude original annotator if requested
            if exclude_original and annotator_id == task.original_annotator_id:
                continue
            
            # Check availability
            if profile["availability"] <= 0:
                continue
            
            # Check skills
            if required_skills:
                if not all(s in profile["skills"] for s in required_skills):
                    continue
            
            # Calculate score
            score = self._calculate_selection_score(profile, task)
            candidates.append((annotator_id, score))
        
        if not candidates:
            return None
        
        # Sort by score and return best
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _calculate_selection_score(
        self,
        profile: Dict[str, Any],
        task: ReannotationTask
    ) -> float:
        """Calculate selection score for an annotator."""
        score = 0.0
        
        # Quality score weight
        score += profile["quality_score"] * 0.5
        
        # Availability weight
        score += profile["availability"] * 0.3
        
        # Workload penalty
        workload_penalty = min(profile["current_workload"] * 0.05, 0.2)
        score -= workload_penalty
        
        # Experience bonus
        if profile["completed_reannotations"] > 10:
            score += 0.1
        
        return score


class QualityVerifier:
    """Verifies quality of re-annotations."""

    def __init__(self, default_threshold: float = 0.8):
        self.default_threshold = default_threshold
        self.verification_history: List[Dict[str, Any]] = []

    async def verify_reannotation(
        self,
        task: ReannotationTask,
        new_annotation: Dict[str, Any],
        original_annotation: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Verify the quality of a re-annotation.
        
        Args:
            task: The re-annotation task
            new_annotation: The new annotation data
            original_annotation: The original annotation for comparison
            
        Returns:
            Tuple of (passed, quality_score, details)
        """
        details = {
            "task_id": task.task_id,
            "verified_at": datetime.now().isoformat()
        }
        
        # Calculate quality metrics
        quality_score = await self._calculate_quality_score(
            new_annotation, original_annotation
        )
        
        details["quality_score"] = quality_score
        details["threshold"] = task.quality_threshold
        
        # Check if passes threshold
        passed = quality_score >= task.quality_threshold
        details["passed"] = passed
        
        # Compare with original if available
        if original_annotation:
            improvement = quality_score - (task.original_quality_score or 0)
            details["improvement"] = improvement
            details["improved"] = improvement > 0
        
        # Record verification
        self.verification_history.append(details)
        
        return passed, quality_score, details

    async def _calculate_quality_score(
        self,
        new_annotation: Dict[str, Any],
        original_annotation: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate quality score for annotation."""
        # Placeholder for actual quality calculation
        # In production, this would integrate with the quality assessment system
        
        score = 0.85  # Default score
        
        # Check completeness
        if new_annotation.get("labels"):
            score += 0.05
        
        # Check confidence
        confidence = new_annotation.get("confidence", 0.5)
        score += confidence * 0.1
        
        return min(score, 1.0)


class ReannotationService:
    """
    Service for managing re-annotation workflows.
    
    Provides:
    - Re-annotation task creation
    - Annotator assignment
    - Quality verification
    - Workflow automation
    """

    def __init__(self):
        self.tasks: Dict[str, ReannotationTask] = {}
        self.batches: Dict[str, ReannotationBatch] = {}
        self.annotator_selector = AnnotatorSelector()
        self.quality_verifier = QualityVerifier()
        self.task_history: List[ReannotationTask] = []
        self.stats: Dict[str, int] = defaultdict(int)

    async def create_reannotation_task(
        self,
        original_task_id: str,
        project_id: str,
        data_item_id: str,
        reason: ReannotationReason,
        priority: ReannotationPriority = ReannotationPriority.MEDIUM,
        original_annotation_id: Optional[str] = None,
        original_annotator_id: Optional[str] = None,
        original_quality_score: Optional[float] = None,
        quality_threshold: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
        auto_assign: bool = True
    ) -> ReannotationTask:
        """
        Create a new re-annotation task.
        
        Args:
            original_task_id: ID of the original task
            project_id: Project ID
            data_item_id: Data item ID
            reason: Reason for re-annotation
            priority: Task priority
            original_annotation_id: Original annotation ID
            original_annotator_id: Original annotator ID
            original_quality_score: Original quality score
            quality_threshold: Required quality threshold
            metadata: Additional metadata
            auto_assign: Whether to auto-assign annotator
            
        Returns:
            Created ReannotationTask
        """
        task = ReannotationTask(
            task_id=str(uuid.uuid4()),
            original_task_id=original_task_id,
            original_annotation_id=original_annotation_id,
            reason=reason,
            priority=priority,
            status=ReannotationStatus.PENDING,
            project_id=project_id,
            data_item_id=data_item_id,
            original_annotator_id=original_annotator_id,
            quality_threshold=quality_threshold,
            original_quality_score=original_quality_score,
            metadata=metadata or {}
        )
        
        self.tasks[task.task_id] = task
        self.stats["created"] += 1
        
        logger.info(f"Created re-annotation task {task.task_id} for {original_task_id}")
        
        # Auto-assign if requested
        if auto_assign:
            await self.assign_task(task.task_id)
        
        return task

    async def create_batch(
        self,
        name: str,
        description: str,
        project_id: str,
        reason: ReannotationReason,
        task_configs: List[Dict[str, Any]]
    ) -> ReannotationBatch:
        """
        Create a batch of re-annotation tasks.
        
        Args:
            name: Batch name
            description: Batch description
            project_id: Project ID
            reason: Reason for re-annotation
            task_configs: List of task configurations
            
        Returns:
            Created ReannotationBatch
        """
        batch = ReannotationBatch(
            batch_id=str(uuid.uuid4()),
            name=name,
            description=description,
            reason=reason,
            project_id=project_id,
            total_tasks=len(task_configs)
        )
        
        # Create individual tasks
        for config in task_configs:
            task = await self.create_reannotation_task(
                original_task_id=config["original_task_id"],
                project_id=project_id,
                data_item_id=config["data_item_id"],
                reason=reason,
                priority=config.get("priority", ReannotationPriority.MEDIUM),
                original_annotation_id=config.get("original_annotation_id"),
                original_annotator_id=config.get("original_annotator_id"),
                original_quality_score=config.get("original_quality_score"),
                quality_threshold=config.get("quality_threshold", 0.8),
                metadata={"batch_id": batch.batch_id},
                auto_assign=False
            )
            batch.task_ids.append(task.task_id)
        
        self.batches[batch.batch_id] = batch
        batch.status = "created"
        
        logger.info(f"Created re-annotation batch {batch.batch_id} with {len(task_configs)} tasks")
        
        return batch

    async def assign_task(
        self,
        task_id: str,
        annotator_id: Optional[str] = None,
        exclude_original: bool = True
    ) -> bool:
        """
        Assign a re-annotation task to an annotator.
        
        Args:
            task_id: Task ID
            annotator_id: Specific annotator ID (optional)
            exclude_original: Whether to exclude original annotator
            
        Returns:
            True if assigned successfully
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False
        
        if task.status != ReannotationStatus.PENDING:
            logger.warning(f"Task {task_id} is not pending")
            return False
        
        # Select annotator if not specified
        if not annotator_id:
            annotator_id = self.annotator_selector.select_annotator(
                task, exclude_original=exclude_original
            )
        
        if not annotator_id:
            logger.warning(f"No suitable annotator found for task {task_id}")
            return False
        
        task.assigned_annotator_id = annotator_id
        task.assigned_at = datetime.now()
        task.status = ReannotationStatus.ASSIGNED
        
        # Update annotator workload
        if annotator_id in self.annotator_selector.annotator_profiles:
            self.annotator_selector.annotator_profiles[annotator_id]["current_workload"] += 1
        
        self.stats["assigned"] += 1
        logger.info(f"Assigned task {task_id} to annotator {annotator_id}")
        
        return True

    async def start_task(self, task_id: str) -> bool:
        """Mark a task as started."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status != ReannotationStatus.ASSIGNED:
            return False
        
        task.status = ReannotationStatus.IN_PROGRESS
        task.started_at = datetime.now()
        
        self.stats["started"] += 1
        return True

    async def complete_task(
        self,
        task_id: str,
        new_annotation: Dict[str, Any],
        auto_verify: bool = True
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Complete a re-annotation task.
        
        Args:
            task_id: Task ID
            new_annotation: The new annotation data
            auto_verify: Whether to auto-verify quality
            
        Returns:
            Tuple of (success, verification_result)
        """
        task = self.tasks.get(task_id)
        if not task:
            return False, None
        
        if task.status != ReannotationStatus.IN_PROGRESS:
            return False, None
        
        task.status = ReannotationStatus.COMPLETED
        task.completed_at = datetime.now()
        task.metadata["new_annotation"] = new_annotation
        
        self.stats["completed"] += 1
        
        # Update annotator stats
        if task.assigned_annotator_id:
            profile = self.annotator_selector.annotator_profiles.get(
                task.assigned_annotator_id
            )
            if profile:
                profile["current_workload"] = max(0, profile["current_workload"] - 1)
                profile["completed_reannotations"] += 1
        
        # Auto-verify if requested
        verification_result = None
        if auto_verify:
            passed, score, details = await self.quality_verifier.verify_reannotation(
                task, new_annotation
            )
            task.new_quality_score = score
            verification_result = details
            
            if passed:
                task.status = ReannotationStatus.VERIFIED
                task.verified_at = datetime.now()
                self.stats["verified"] += 1
        
        # Update batch progress
        batch_id = task.metadata.get("batch_id")
        if batch_id and batch_id in self.batches:
            batch = self.batches[batch_id]
            batch.completed_tasks += 1
            if task.status == ReannotationStatus.VERIFIED:
                batch.verified_tasks += 1
            
            # Check if batch is complete
            if batch.completed_tasks >= batch.total_tasks:
                batch.status = "completed"
                batch.completed_at = datetime.now()
        
        logger.info(f"Completed task {task_id} with quality score {task.new_quality_score}")
        
        return True, verification_result

    async def verify_task(
        self,
        task_id: str,
        verifier_id: str,
        passed: bool,
        notes: Optional[str] = None
    ) -> bool:
        """
        Manually verify a completed task.
        
        Args:
            task_id: Task ID
            verifier_id: ID of the verifier
            passed: Whether verification passed
            notes: Verification notes
            
        Returns:
            True if verified successfully
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status != ReannotationStatus.COMPLETED:
            return False
        
        task.verified_at = datetime.now()
        task.verification_notes = notes
        task.metadata["verifier_id"] = verifier_id
        
        if passed:
            task.status = ReannotationStatus.VERIFIED
            self.stats["verified"] += 1
        else:
            task.status = ReannotationStatus.REJECTED
            self.stats["rejected"] += 1
        
        return True

    async def cancel_task(self, task_id: str, reason: str) -> bool:
        """Cancel a re-annotation task."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [ReannotationStatus.VERIFIED, ReannotationStatus.CANCELLED]:
            return False
        
        task.status = ReannotationStatus.CANCELLED
        task.metadata["cancellation_reason"] = reason
        
        # Update annotator workload
        if task.assigned_annotator_id:
            profile = self.annotator_selector.annotator_profiles.get(
                task.assigned_annotator_id
            )
            if profile and task.status in [ReannotationStatus.ASSIGNED, ReannotationStatus.IN_PROGRESS]:
                profile["current_workload"] = max(0, profile["current_workload"] - 1)
        
        self.stats["cancelled"] += 1
        return True

    def get_task(self, task_id: str) -> Optional[ReannotationTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_batch(self, batch_id: str) -> Optional[ReannotationBatch]:
        """Get a batch by ID."""
        return self.batches.get(batch_id)

    def list_tasks(
        self,
        project_id: Optional[str] = None,
        status: Optional[ReannotationStatus] = None,
        annotator_id: Optional[str] = None,
        reason: Optional[ReannotationReason] = None,
        limit: int = 100
    ) -> List[ReannotationTask]:
        """List tasks with filters."""
        tasks = list(self.tasks.values())
        
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        if annotator_id:
            tasks = [t for t in tasks if t.assigned_annotator_id == annotator_id]
        if reason:
            tasks = [t for t in tasks if t.reason == reason]
        
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]

    def list_batches(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ReannotationBatch]:
        """List batches with filters."""
        batches = list(self.batches.values())
        
        if project_id:
            batches = [b for b in batches if b.project_id == project_id]
        if status:
            batches = [b for b in batches if b.status == status]
        
        return sorted(batches, key=lambda b: b.created_at, reverse=True)

    def get_statistics(
        self,
        project_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get re-annotation statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        
        tasks = list(self.tasks.values())
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        
        recent_tasks = [t for t in tasks if t.created_at >= cutoff]
        
        by_status = defaultdict(int)
        by_reason = defaultdict(int)
        quality_improvements = []
        
        for task in recent_tasks:
            by_status[task.status.value] += 1
            by_reason[task.reason.value] += 1
            
            if task.original_quality_score and task.new_quality_score:
                improvement = task.new_quality_score - task.original_quality_score
                quality_improvements.append(improvement)
        
        avg_improvement = (
            sum(quality_improvements) / len(quality_improvements)
            if quality_improvements else 0
        )
        
        return {
            "period_days": days,
            "total_tasks": len(recent_tasks),
            "by_status": dict(by_status),
            "by_reason": dict(by_reason),
            "average_quality_improvement": avg_improvement,
            "verification_rate": (
                by_status.get("verified", 0) / len(recent_tasks)
                if recent_tasks else 0
            ),
            "rejection_rate": (
                by_status.get("rejected", 0) / len(recent_tasks)
                if recent_tasks else 0
            ),
            "global_stats": dict(self.stats),
            "generated_at": datetime.now().isoformat()
        }


# Global instance
reannotation_service = ReannotationService()
