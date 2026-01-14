"""
Collaboration Manager for SuperInsight platform.

Manages human-AI collaboration including task assignment, role-based access,
workload tracking, and team statistics.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from uuid import uuid4
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================================
# User Roles
# ============================================================================

class UserRole(str, Enum):
    """User roles in the annotation workflow."""
    ANNOTATOR = "annotator"      # 标注员
    EXPERT = "expert"            # 专家
    CONTRACTOR = "contractor"    # 外包
    REVIEWER = "reviewer"        # 审核员
    ADMIN = "admin"              # 管理员


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Task assignment status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEW_PENDING = "review_pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ============================================================================
# Data Models
# ============================================================================

class TaskAssignment:
    """Task assignment record."""
    
    def __init__(
        self,
        task_id: str,
        user_id: str,
        role: UserRole,
        priority: TaskPriority = TaskPriority.NORMAL,
        deadline: Optional[datetime] = None,
    ):
        self.id = str(uuid4())
        self.task_id = task_id
        self.user_id = user_id
        self.role = role
        self.priority = priority
        self.deadline = deadline
        self.status = TaskStatus.ASSIGNED
        self.assigned_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "role": self.role.value,
            "priority": self.priority.value,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status.value,
            "assigned_at": self.assigned_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class WorkloadStatistics:
    """Workload statistics for a user."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.assigned_tasks = 0
        self.in_progress_tasks = 0
        self.completed_tasks = 0
        self.pending_review_tasks = 0
        self.total_time_spent_minutes = 0.0
        self.avg_task_time_minutes = 0.0
        self.tasks_by_priority: Dict[str, int] = defaultdict(int)
        self.tasks_by_type: Dict[str, int] = defaultdict(int)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "assigned_tasks": self.assigned_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "completed_tasks": self.completed_tasks,
            "pending_review_tasks": self.pending_review_tasks,
            "total_time_spent_minutes": self.total_time_spent_minutes,
            "avg_task_time_minutes": self.avg_task_time_minutes,
            "tasks_by_priority": dict(self.tasks_by_priority),
            "tasks_by_type": dict(self.tasks_by_type),
        }


class TeamStatistics:
    """Team-level statistics."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.total_tasks = 0
        self.assigned_tasks = 0
        self.completed_tasks = 0
        self.pending_review_tasks = 0
        self.approved_tasks = 0
        self.rejected_tasks = 0
        self.active_annotators = 0
        self.active_reviewers = 0
        self.avg_completion_time_minutes = 0.0
        self.completion_rate = 0.0
        self.approval_rate = 0.0
        self.member_stats: Dict[str, WorkloadStatistics] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "total_tasks": self.total_tasks,
            "assigned_tasks": self.assigned_tasks,
            "completed_tasks": self.completed_tasks,
            "pending_review_tasks": self.pending_review_tasks,
            "approved_tasks": self.approved_tasks,
            "rejected_tasks": self.rejected_tasks,
            "active_annotators": self.active_annotators,
            "active_reviewers": self.active_reviewers,
            "avg_completion_time_minutes": self.avg_completion_time_minutes,
            "completion_rate": self.completion_rate,
            "approval_rate": self.approval_rate,
            "member_count": len(self.member_stats),
        }


# ============================================================================
# Collaboration Manager
# ============================================================================

class CollaborationManager:
    """
    Collaboration Manager for human-AI annotation workflow.
    
    Features:
    - Role-based task assignment
    - Automatic reviewer assignment
    - Workload tracking and balancing
    - Team statistics
    """
    
    def __init__(self):
        """Initialize the collaboration manager."""
        self._assignments: Dict[str, TaskAssignment] = {}
        self._user_assignments: Dict[str, Set[str]] = defaultdict(set)
        self._task_assignments: Dict[str, str] = {}  # task_id -> assignment_id
        self._user_roles: Dict[str, UserRole] = {}
        self._reviewers: Set[str] = set()
        self._lock = asyncio.Lock()
    
    # ========================================================================
    # User Management
    # ========================================================================
    
    def register_user(self, user_id: str, role: UserRole) -> None:
        """
        Register a user with a role.
        
        Args:
            user_id: User ID
            role: User role
        """
        self._user_roles[user_id] = role
        if role == UserRole.REVIEWER:
            self._reviewers.add(user_id)
        logger.info(f"Registered user {user_id} with role {role}")
    
    def get_user_role(self, user_id: str) -> Optional[UserRole]:
        """
        Get user's role.
        
        Args:
            user_id: User ID
            
        Returns:
            UserRole or None
        """
        return self._user_roles.get(user_id)
    
    def check_role_permission(
        self,
        user_id: str,
        required_roles: List[UserRole],
    ) -> bool:
        """
        Check if user has required role.
        
        Args:
            user_id: User ID
            required_roles: List of allowed roles
            
        Returns:
            True if user has permission
        """
        user_role = self._user_roles.get(user_id)
        if not user_role:
            return False
        return user_role in required_roles or user_role == UserRole.ADMIN
    
    # ========================================================================
    # Task Assignment
    # ========================================================================
    
    async def assign_task(
        self,
        task_id: str,
        user_id: Optional[str] = None,
        role: Optional[UserRole] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        deadline: Optional[datetime] = None,
    ) -> TaskAssignment:
        """
        Assign a task to a user.
        
        Args:
            task_id: Task ID
            user_id: Optional specific user ID
            role: Optional role to assign to
            priority: Task priority
            deadline: Optional deadline
            
        Returns:
            TaskAssignment
        """
        async with self._lock:
            # Determine user
            if not user_id:
                user_id = await self._find_available_user(role or UserRole.ANNOTATOR)
            
            if not user_id:
                raise ValueError("No available user for assignment")
            
            # Get user role
            user_role = self._user_roles.get(user_id, role or UserRole.ANNOTATOR)
            
            # Create assignment
            assignment = TaskAssignment(
                task_id=task_id,
                user_id=user_id,
                role=user_role,
                priority=priority,
                deadline=deadline,
            )
            
            # Store assignment
            self._assignments[assignment.id] = assignment
            self._user_assignments[user_id].add(assignment.id)
            self._task_assignments[task_id] = assignment.id
            
            logger.info(f"Assigned task {task_id} to user {user_id}")
            
            return assignment
    
    async def auto_assign_to_reviewer(
        self,
        task_id: str,
        original_annotator_id: Optional[str] = None,
    ) -> TaskAssignment:
        """
        Automatically assign task to a reviewer.
        
        Args:
            task_id: Task ID
            original_annotator_id: Original annotator to exclude
            
        Returns:
            TaskAssignment
        """
        async with self._lock:
            # Find available reviewer (not the original annotator)
            available_reviewers = [
                r for r in self._reviewers
                if r != original_annotator_id
            ]
            
            if not available_reviewers:
                raise ValueError("No available reviewers")
            
            # Select reviewer with lowest workload
            reviewer_id = await self._find_least_loaded_user(available_reviewers)
            
            # Create assignment
            assignment = TaskAssignment(
                task_id=task_id,
                user_id=reviewer_id,
                role=UserRole.REVIEWER,
                priority=TaskPriority.NORMAL,
            )
            assignment.status = TaskStatus.REVIEW_PENDING
            
            # Store assignment
            self._assignments[assignment.id] = assignment
            self._user_assignments[reviewer_id].add(assignment.id)
            
            logger.info(f"Auto-assigned task {task_id} to reviewer {reviewer_id}")
            
            return assignment
    
    async def reassign_task(
        self,
        task_id: str,
        new_user_id: str,
        reason: str = "",
    ) -> TaskAssignment:
        """
        Reassign a task to a different user.
        
        Args:
            task_id: Task ID
            new_user_id: New user ID
            reason: Reason for reassignment
            
        Returns:
            New TaskAssignment
        """
        async with self._lock:
            # Get current assignment
            current_assignment_id = self._task_assignments.get(task_id)
            if current_assignment_id:
                current = self._assignments.get(current_assignment_id)
                if current:
                    # Remove from old user
                    self._user_assignments[current.user_id].discard(current_assignment_id)
            
            # Create new assignment
            user_role = self._user_roles.get(new_user_id, UserRole.ANNOTATOR)
            
            assignment = TaskAssignment(
                task_id=task_id,
                user_id=new_user_id,
                role=user_role,
            )
            assignment.metadata["reassignment_reason"] = reason
            
            # Store assignment
            self._assignments[assignment.id] = assignment
            self._user_assignments[new_user_id].add(assignment.id)
            self._task_assignments[task_id] = assignment.id
            
            logger.info(f"Reassigned task {task_id} to user {new_user_id}")
            
            return assignment
    
    # ========================================================================
    # Task Status Updates
    # ========================================================================
    
    async def start_task(self, task_id: str, user_id: str) -> bool:
        """
        Mark task as started.
        
        Args:
            task_id: Task ID
            user_id: User ID
            
        Returns:
            True if successful
        """
        async with self._lock:
            assignment_id = self._task_assignments.get(task_id)
            if not assignment_id:
                return False
            
            assignment = self._assignments.get(assignment_id)
            if not assignment or assignment.user_id != user_id:
                return False
            
            assignment.status = TaskStatus.IN_PROGRESS
            assignment.started_at = datetime.utcnow()
            
            return True
    
    async def complete_task(self, task_id: str, user_id: str) -> bool:
        """
        Mark task as completed.
        
        Args:
            task_id: Task ID
            user_id: User ID
            
        Returns:
            True if successful
        """
        async with self._lock:
            assignment_id = self._task_assignments.get(task_id)
            if not assignment_id:
                return False
            
            assignment = self._assignments.get(assignment_id)
            if not assignment or assignment.user_id != user_id:
                return False
            
            assignment.status = TaskStatus.COMPLETED
            assignment.completed_at = datetime.utcnow()
            
            return True
    
    # ========================================================================
    # Task Queries
    # ========================================================================
    
    async def get_available_tasks(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[TaskAssignment]:
        """
        Get available tasks for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of tasks
            
        Returns:
            List of TaskAssignment
        """
        async with self._lock:
            user_assignment_ids = self._user_assignments.get(user_id, set())
            
            tasks = []
            for assignment_id in user_assignment_ids:
                assignment = self._assignments.get(assignment_id)
                if assignment and assignment.status in [
                    TaskStatus.ASSIGNED,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.REVIEW_PENDING,
                ]:
                    tasks.append(assignment)
            
            # Sort by priority and deadline
            tasks.sort(
                key=lambda t: (
                    -list(TaskPriority).index(t.priority),
                    t.deadline or datetime.max,
                )
            )
            
            return tasks[:limit]
    
    async def get_task_assignment(
        self,
        task_id: str,
    ) -> Optional[TaskAssignment]:
        """
        Get assignment for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            TaskAssignment or None
        """
        assignment_id = self._task_assignments.get(task_id)
        if assignment_id:
            return self._assignments.get(assignment_id)
        return None
    
    # ========================================================================
    # Statistics
    # ========================================================================
    
    async def get_workload(self, user_id: str) -> WorkloadStatistics:
        """
        Get workload statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            WorkloadStatistics
        """
        async with self._lock:
            stats = WorkloadStatistics(user_id)
            
            user_assignment_ids = self._user_assignments.get(user_id, set())
            
            total_time = 0.0
            completed_count = 0
            
            for assignment_id in user_assignment_ids:
                assignment = self._assignments.get(assignment_id)
                if not assignment:
                    continue
                
                stats.assigned_tasks += 1
                stats.tasks_by_priority[assignment.priority.value] += 1
                
                if assignment.status == TaskStatus.IN_PROGRESS:
                    stats.in_progress_tasks += 1
                elif assignment.status == TaskStatus.COMPLETED:
                    stats.completed_tasks += 1
                    completed_count += 1
                    
                    if assignment.started_at and assignment.completed_at:
                        time_spent = (
                            assignment.completed_at - assignment.started_at
                        ).total_seconds() / 60
                        total_time += time_spent
                elif assignment.status == TaskStatus.REVIEW_PENDING:
                    stats.pending_review_tasks += 1
            
            stats.total_time_spent_minutes = total_time
            if completed_count > 0:
                stats.avg_task_time_minutes = total_time / completed_count
            
            return stats
    
    async def get_team_statistics(self, project_id: str) -> TeamStatistics:
        """
        Get team-level statistics.
        
        Args:
            project_id: Project ID
            
        Returns:
            TeamStatistics
        """
        async with self._lock:
            stats = TeamStatistics(project_id)
            
            active_annotators = set()
            active_reviewers = set()
            total_completion_time = 0.0
            completed_count = 0
            
            for assignment in self._assignments.values():
                stats.total_tasks += 1
                
                if assignment.status == TaskStatus.ASSIGNED:
                    stats.assigned_tasks += 1
                elif assignment.status == TaskStatus.COMPLETED:
                    stats.completed_tasks += 1
                    completed_count += 1
                    
                    if assignment.started_at and assignment.completed_at:
                        time_spent = (
                            assignment.completed_at - assignment.started_at
                        ).total_seconds() / 60
                        total_completion_time += time_spent
                elif assignment.status == TaskStatus.REVIEW_PENDING:
                    stats.pending_review_tasks += 1
                elif assignment.status == TaskStatus.APPROVED:
                    stats.approved_tasks += 1
                elif assignment.status == TaskStatus.REJECTED:
                    stats.rejected_tasks += 1
                
                # Track active users
                if assignment.role == UserRole.REVIEWER:
                    active_reviewers.add(assignment.user_id)
                else:
                    active_annotators.add(assignment.user_id)
            
            stats.active_annotators = len(active_annotators)
            stats.active_reviewers = len(active_reviewers)
            
            if completed_count > 0:
                stats.avg_completion_time_minutes = total_completion_time / completed_count
            
            if stats.total_tasks > 0:
                stats.completion_rate = stats.completed_tasks / stats.total_tasks
            
            reviewed = stats.approved_tasks + stats.rejected_tasks
            if reviewed > 0:
                stats.approval_rate = stats.approved_tasks / reviewed
            
            return stats
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _find_available_user(self, role: UserRole) -> Optional[str]:
        """Find an available user with the specified role."""
        candidates = [
            user_id for user_id, user_role in self._user_roles.items()
            if user_role == role
        ]
        
        if not candidates:
            return None
        
        return await self._find_least_loaded_user(candidates)
    
    async def _find_least_loaded_user(
        self,
        candidates: List[str],
    ) -> Optional[str]:
        """Find the user with the lowest workload."""
        if not candidates:
            return None
        
        min_load = float('inf')
        selected = candidates[0]
        
        for user_id in candidates:
            assignment_ids = self._user_assignments.get(user_id, set())
            active_count = sum(
                1 for aid in assignment_ids
                if self._assignments.get(aid) and
                self._assignments[aid].status in [
                    TaskStatus.ASSIGNED,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.REVIEW_PENDING,
                ]
            )
            
            if active_count < min_load:
                min_load = active_count
                selected = user_id
        
        return selected


# ============================================================================
# Singleton Instance
# ============================================================================

_manager_instance: Optional[CollaborationManager] = None


def get_collaboration_manager() -> CollaborationManager:
    """
    Get or create the collaboration manager instance.
    
    Returns:
        CollaborationManager instance
    """
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = CollaborationManager()
    
    return _manager_instance
