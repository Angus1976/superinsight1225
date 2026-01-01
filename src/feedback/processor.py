"""
Feedback processing for SuperInsight Platform.

Provides:
- Automatic feedback assignment and tracking
- SLA management with ticket system integration
- Solution library and keyword extraction
- Customer satisfaction tracking
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
import re
from collections import Counter

from .collector import (
    Feedback, FeedbackSource, FeedbackCategory,
    SentimentType, FeedbackStatus, FeedbackCollector
)

logger = logging.getLogger(__name__)


class ProcessingStatus(str, Enum):
    """Feedback processing status."""
    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    AWAITING_RESPONSE = "awaiting_response"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class ProcessingPriority(str, Enum):
    """Processing priority levels."""
    URGENT = "urgent"      # 4 hours SLA
    HIGH = "high"          # 8 hours SLA
    MEDIUM = "medium"      # 24 hours SLA
    LOW = "low"            # 72 hours SLA


@dataclass
class ProcessingTask:
    """Feedback processing task."""
    id: UUID
    feedback_id: UUID
    status: ProcessingStatus = ProcessingStatus.QUEUED
    priority: ProcessingPriority = ProcessingPriority.MEDIUM
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    sla_deadline: Optional[datetime] = None
    sla_breached: bool = False
    resolution: Optional[str] = None
    resolution_time: Optional[int] = None  # seconds
    satisfaction_score: Optional[float] = None
    ticket_id: Optional[UUID] = None  # linked ticket
    keywords: List[str] = field(default_factory=list)
    suggested_solutions: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "feedback_id": str(self.feedback_id),
            "status": self.status.value,
            "priority": self.priority.value,
            "assigned_to": self.assigned_to,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "sla_deadline": self.sla_deadline.isoformat() if self.sla_deadline else None,
            "sla_breached": self.sla_breached,
            "resolution": self.resolution,
            "resolution_time": self.resolution_time,
            "satisfaction_score": self.satisfaction_score,
            "ticket_id": str(self.ticket_id) if self.ticket_id else None,
            "keywords": self.keywords,
            "suggested_solutions": self.suggested_solutions,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class Solution:
    """Solution entry in the solution library."""
    id: UUID
    category: FeedbackCategory
    title: str
    description: str
    steps: List[str]
    keywords: List[str]
    effectiveness_score: float = 0.0  # 0-1
    usage_count: int = 0
    success_rate: float = 0.0  # 0-1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "steps": self.steps,
            "keywords": self.keywords,
            "effectiveness_score": self.effectiveness_score,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class SatisfactionSurvey:
    """Customer satisfaction survey result."""
    id: UUID
    feedback_id: UUID
    task_id: UUID
    overall_score: float  # 1-5
    response_speed_score: float  # 1-5
    solution_quality_score: float  # 1-5
    communication_score: float  # 1-5
    comments: Optional[str] = None
    submitted_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "feedback_id": str(self.feedback_id),
            "task_id": str(self.task_id),
            "overall_score": self.overall_score,
            "response_speed_score": self.response_speed_score,
            "solution_quality_score": self.solution_quality_score,
            "communication_score": self.communication_score,
            "comments": self.comments,
            "submitted_at": self.submitted_at.isoformat()
        }


class FeedbackProcessor:
    """
    Feedback processing engine.

    Handles automatic assignment, SLA management, solution matching,
    and customer satisfaction tracking.
    """

    # SLA hours by priority
    SLA_HOURS = {
        ProcessingPriority.URGENT: 4,
        ProcessingPriority.HIGH: 8,
        ProcessingPriority.MEDIUM: 24,
        ProcessingPriority.LOW: 72
    }

    # Priority mapping from sentiment and category
    PRIORITY_RULES = {
        (SentimentType.NEGATIVE, FeedbackCategory.COMPLAINT): ProcessingPriority.URGENT,
        (SentimentType.NEGATIVE, FeedbackCategory.QUALITY): ProcessingPriority.HIGH,
        (SentimentType.NEGATIVE, FeedbackCategory.TOOL): ProcessingPriority.HIGH,
        (SentimentType.NEUTRAL, FeedbackCategory.COMPLAINT): ProcessingPriority.HIGH,
        (SentimentType.NEGATIVE, FeedbackCategory.EFFICIENCY): ProcessingPriority.MEDIUM,
        (SentimentType.NEUTRAL, FeedbackCategory.QUALITY): ProcessingPriority.MEDIUM,
    }

    # Keyword patterns for extraction
    KEYWORD_PATTERNS = [
        r'\b(?:标注|annotation|label)\w*\b',
        r'\b(?:质量|quality)\w*\b',
        r'\b(?:错误|error|bug|issue)\w*\b',
        r'\b(?:速度|slow|fast|效率|efficiency)\w*\b',
        r'\b(?:系统|system|工具|tool)\w*\b',
        r'\b(?:审核|review)\w*\b',
        r'\b(?:数据|data)\w*\b',
        r'\b(?:模型|model|AI)\w*\b',
    ]

    def __init__(self, feedback_collector: Optional[FeedbackCollector] = None):
        """Initialize the feedback processor."""
        self._collector = feedback_collector or FeedbackCollector()
        self._tasks: Dict[UUID, ProcessingTask] = {}
        self._solutions: Dict[UUID, Solution] = {}
        self._surveys: Dict[UUID, SatisfactionSurvey] = {}
        self._handlers: Dict[str, Dict[str, Any]] = {}  # handler_id -> handler info
        self._initialize_default_solutions()

    def _initialize_default_solutions(self):
        """Initialize default solution library."""
        default_solutions = [
            {
                "category": FeedbackCategory.QUALITY,
                "title": "Quality Issue Resolution Guide",
                "description": "Standard process for resolving annotation quality issues",
                "steps": [
                    "Review the specific quality issue identified",
                    "Analyze root cause (guidelines unclear, annotator training gap, etc.)",
                    "Apply correction to affected data",
                    "Update guidelines if necessary",
                    "Provide feedback to relevant annotator"
                ],
                "keywords": ["quality", "accuracy", "error", "mistake", "wrong"]
            },
            {
                "category": FeedbackCategory.TOOL,
                "title": "Tool/System Issue Resolution",
                "description": "Process for handling tool and system related feedback",
                "steps": [
                    "Verify the reported issue",
                    "Check system logs for errors",
                    "Create bug report if confirmed",
                    "Provide workaround if available",
                    "Follow up after fix deployment"
                ],
                "keywords": ["tool", "system", "bug", "interface", "crash"]
            },
            {
                "category": FeedbackCategory.EFFICIENCY,
                "title": "Efficiency Improvement Process",
                "description": "Handle feedback related to efficiency concerns",
                "steps": [
                    "Identify bottleneck or slow process",
                    "Analyze workflow for optimization",
                    "Propose improvements",
                    "Implement changes if approved",
                    "Monitor improvement results"
                ],
                "keywords": ["slow", "speed", "efficiency", "waiting", "delay"]
            },
            {
                "category": FeedbackCategory.GUIDELINE,
                "title": "Guideline Clarification Process",
                "description": "Process for handling guideline-related questions",
                "steps": [
                    "Review the guideline question",
                    "Consult with quality team",
                    "Provide clarification",
                    "Update documentation if needed",
                    "Communicate updates to team"
                ],
                "keywords": ["guideline", "rule", "standard", "unclear", "confusion"]
            },
            {
                "category": FeedbackCategory.COMPLAINT,
                "title": "Customer Complaint Resolution",
                "description": "Handle customer complaints with care",
                "steps": [
                    "Acknowledge receipt immediately",
                    "Investigate the complaint thoroughly",
                    "Identify responsible parties",
                    "Propose resolution and compensation if applicable",
                    "Follow up to ensure satisfaction"
                ],
                "keywords": ["complaint", "unhappy", "dissatisfied", "problem"]
            }
        ]

        for sol_data in default_solutions:
            solution = Solution(
                id=uuid4(),
                category=sol_data["category"],
                title=sol_data["title"],
                description=sol_data["description"],
                steps=sol_data["steps"],
                keywords=sol_data["keywords"],
                effectiveness_score=0.8
            )
            self._solutions[solution.id] = solution

    async def create_processing_task(
        self,
        feedback: Feedback,
        auto_assign: bool = True
    ) -> ProcessingTask:
        """
        Create a processing task for feedback.

        Args:
            feedback: Feedback to process
            auto_assign: Auto-assign to handler

        Returns:
            Created processing task
        """
        # Determine priority
        priority = self._determine_priority(feedback)

        # Calculate SLA deadline
        sla_hours = self.SLA_HOURS[priority]
        sla_deadline = datetime.now() + timedelta(hours=sla_hours)

        # Extract keywords
        keywords = self._extract_keywords(feedback.content)

        # Find suggested solutions
        suggested_solutions = await self._find_solutions(feedback.category, keywords)

        task = ProcessingTask(
            id=uuid4(),
            feedback_id=feedback.id,
            priority=priority,
            sla_deadline=sla_deadline,
            keywords=keywords,
            suggested_solutions=[s.to_dict() for s in suggested_solutions[:3]]
        )

        # Auto-assign if enabled
        if auto_assign:
            handler = await self._find_best_handler(feedback.category, keywords)
            if handler:
                task.assigned_to = handler["id"]
                task.assigned_at = datetime.now()
                task.status = ProcessingStatus.ASSIGNED

        self._tasks[task.id] = task

        logger.info(
            f"Processing task created: {task.id} for feedback {feedback.id} "
            f"- priority: {priority.value}, SLA: {sla_deadline.isoformat()}"
        )

        return task

    def _determine_priority(self, feedback: Feedback) -> ProcessingPriority:
        """Determine processing priority based on feedback characteristics."""
        # Check priority rules
        key = (feedback.sentiment, feedback.category)
        if key in self.PRIORITY_RULES:
            return self.PRIORITY_RULES[key]

        # Check for urgent tags
        if "urgent" in feedback.tags:
            return ProcessingPriority.URGENT

        # Default by sentiment
        if feedback.sentiment == SentimentType.NEGATIVE:
            return ProcessingPriority.HIGH
        elif feedback.sentiment == SentimentType.NEUTRAL:
            return ProcessingPriority.MEDIUM
        else:
            return ProcessingPriority.LOW

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from feedback text."""
        keywords = []
        text_lower = text.lower()

        for pattern in self.KEYWORD_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            keywords.extend(matches)

        # Remove duplicates and return
        return list(set(keywords))

    async def _find_solutions(
        self,
        category: FeedbackCategory,
        keywords: List[str]
    ) -> List[Solution]:
        """Find matching solutions from the library."""
        scored_solutions = []

        for solution in self._solutions.values():
            score = 0.0

            # Category match
            if solution.category == category:
                score += 0.5

            # Keyword overlap
            keyword_overlap = len(set(solution.keywords) & set(keywords))
            score += keyword_overlap * 0.2

            # Effectiveness weight
            score += solution.effectiveness_score * 0.3

            if score > 0.3:
                scored_solutions.append((solution, score))

        # Sort by score descending
        scored_solutions.sort(key=lambda x: x[1], reverse=True)

        return [s[0] for s in scored_solutions]

    async def _find_best_handler(
        self,
        category: FeedbackCategory,
        keywords: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Find the best handler for the feedback."""
        if not self._handlers:
            return None

        best_handler = None
        best_score = 0.0

        for handler_id, handler in self._handlers.items():
            if not handler.get("available", True):
                continue

            score = 0.0

            # Category expertise
            if category.value in handler.get("expertise", []):
                score += 0.5

            # Current workload (lower is better)
            workload = handler.get("current_workload", 0)
            max_workload = handler.get("max_workload", 10)
            if workload < max_workload:
                score += 0.3 * (1 - workload / max_workload)

            # Success rate
            score += handler.get("success_rate", 0.5) * 0.2

            if score > best_score:
                best_score = score
                best_handler = {**handler, "id": handler_id}

        return best_handler

    async def register_handler(
        self,
        handler_id: str,
        name: str,
        expertise: List[str],
        max_workload: int = 10
    ) -> bool:
        """
        Register a feedback handler.

        Args:
            handler_id: Unique handler ID
            name: Handler name
            expertise: List of categories they handle
            max_workload: Maximum concurrent tasks

        Returns:
            True if registered
        """
        self._handlers[handler_id] = {
            "name": name,
            "expertise": expertise,
            "max_workload": max_workload,
            "current_workload": 0,
            "success_rate": 0.8,
            "available": True,
            "total_handled": 0,
            "avg_resolution_time": 0
        }

        logger.info(f"Handler registered: {handler_id} - {name}")
        return True

    async def assign_task(
        self,
        task_id: UUID,
        handler_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Assign a task to a handler.

        Args:
            task_id: Task UUID
            handler_id: Handler to assign to
            notes: Assignment notes

        Returns:
            True if assigned
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False

        handler = self._handlers.get(handler_id)
        if not handler:
            logger.error(f"Handler not found: {handler_id}")
            return False

        task.assigned_to = handler_id
        task.assigned_at = datetime.now()
        task.status = ProcessingStatus.ASSIGNED
        task.updated_at = datetime.now()

        if notes:
            task.notes.append({
                "action": "assigned",
                "content": notes,
                "timestamp": datetime.now().isoformat()
            })

        # Update handler workload
        handler["current_workload"] += 1

        logger.info(f"Task {task_id} assigned to handler {handler_id}")
        return True

    async def update_task_status(
        self,
        task_id: UUID,
        status: ProcessingStatus,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update task status.

        Args:
            task_id: Task UUID
            status: New status
            notes: Status update notes

        Returns:
            True if updated
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        old_status = task.status
        task.status = status
        task.updated_at = datetime.now()

        if notes:
            task.notes.append({
                "action": "status_changed",
                "old_status": old_status.value,
                "new_status": status.value,
                "content": notes,
                "timestamp": datetime.now().isoformat()
            })

        # Update handler workload if resolved
        if status in [ProcessingStatus.RESOLVED, ProcessingStatus.CLOSED]:
            if task.assigned_to and task.assigned_to in self._handlers:
                self._handlers[task.assigned_to]["current_workload"] -= 1
                self._handlers[task.assigned_to]["total_handled"] += 1

            # Calculate resolution time
            task.resolution_time = int((datetime.now() - task.created_at).total_seconds())

        logger.info(f"Task {task_id} status updated: {old_status.value} -> {status.value}")
        return True

    async def resolve_task(
        self,
        task_id: UUID,
        resolution: str,
        solution_id: Optional[UUID] = None
    ) -> bool:
        """
        Resolve a processing task.

        Args:
            task_id: Task UUID
            resolution: Resolution description
            solution_id: Used solution ID

        Returns:
            True if resolved
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.resolution = resolution
        task.status = ProcessingStatus.RESOLVED
        task.updated_at = datetime.now()
        task.resolution_time = int((datetime.now() - task.created_at).total_seconds())

        # Update solution usage if provided
        if solution_id and solution_id in self._solutions:
            solution = self._solutions[solution_id]
            solution.usage_count += 1
            solution.updated_at = datetime.now()

        # Update feedback status
        await self._collector.update_feedback_status(
            task.feedback_id,
            FeedbackStatus.ACTIONED,
            action_taken=resolution
        )

        logger.info(f"Task {task_id} resolved with: {resolution[:100]}...")
        return True

    async def check_sla_breaches(self) -> List[ProcessingTask]:
        """
        Check for SLA breaches and return affected tasks.

        Returns:
            List of tasks that breached SLA
        """
        now = datetime.now()
        breached_tasks = []

        for task in self._tasks.values():
            if task.status not in [ProcessingStatus.RESOLVED, ProcessingStatus.CLOSED]:
                if task.sla_deadline and now > task.sla_deadline and not task.sla_breached:
                    task.sla_breached = True
                    task.updated_at = now
                    breached_tasks.append(task)

                    task.notes.append({
                        "action": "sla_breached",
                        "timestamp": now.isoformat(),
                        "content": f"SLA deadline exceeded: {task.sla_deadline.isoformat()}"
                    })

                    logger.warning(f"SLA breach detected for task {task.id}")

        return breached_tasks

    async def escalate_task(
        self,
        task_id: UUID,
        reason: str,
        escalate_to: Optional[str] = None
    ) -> bool:
        """
        Escalate a task.

        Args:
            task_id: Task UUID
            reason: Escalation reason
            escalate_to: Escalate to specific handler

        Returns:
            True if escalated
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = ProcessingStatus.ESCALATED
        task.priority = ProcessingPriority.URGENT  # Escalated tasks become urgent
        task.updated_at = datetime.now()

        # Recalculate SLA
        task.sla_deadline = datetime.now() + timedelta(hours=self.SLA_HOURS[ProcessingPriority.URGENT])

        task.notes.append({
            "action": "escalated",
            "reason": reason,
            "escalate_to": escalate_to,
            "timestamp": datetime.now().isoformat()
        })

        if escalate_to:
            task.assigned_to = escalate_to
            task.assigned_at = datetime.now()

        logger.warning(f"Task {task_id} escalated: {reason}")
        return True

    async def submit_satisfaction_survey(
        self,
        feedback_id: UUID,
        task_id: UUID,
        overall_score: float,
        response_speed_score: float,
        solution_quality_score: float,
        communication_score: float,
        comments: Optional[str] = None
    ) -> SatisfactionSurvey:
        """
        Submit customer satisfaction survey.

        Args:
            feedback_id: Related feedback UUID
            task_id: Processing task UUID
            overall_score: Overall satisfaction (1-5)
            response_speed_score: Response speed rating (1-5)
            solution_quality_score: Solution quality rating (1-5)
            communication_score: Communication rating (1-5)
            comments: Optional comments

        Returns:
            Created survey
        """
        survey = SatisfactionSurvey(
            id=uuid4(),
            feedback_id=feedback_id,
            task_id=task_id,
            overall_score=max(1.0, min(5.0, overall_score)),
            response_speed_score=max(1.0, min(5.0, response_speed_score)),
            solution_quality_score=max(1.0, min(5.0, solution_quality_score)),
            communication_score=max(1.0, min(5.0, communication_score)),
            comments=comments
        )

        self._surveys[survey.id] = survey

        # Update task satisfaction score
        task = self._tasks.get(task_id)
        if task:
            task.satisfaction_score = overall_score

            # Update handler success rate
            if task.assigned_to and task.assigned_to in self._handlers:
                handler = self._handlers[task.assigned_to]
                total = handler["total_handled"]
                old_rate = handler["success_rate"]
                # Positive if score >= 3.5
                is_success = overall_score >= 3.5
                handler["success_rate"] = (old_rate * total + (1.0 if is_success else 0.0)) / (total + 1)

        logger.info(f"Satisfaction survey submitted: {survey.id} - overall: {overall_score}")
        return survey

    async def add_solution(
        self,
        category: FeedbackCategory,
        title: str,
        description: str,
        steps: List[str],
        keywords: List[str]
    ) -> Solution:
        """
        Add a solution to the library.

        Args:
            category: Feedback category
            title: Solution title
            description: Solution description
            steps: Resolution steps
            keywords: Related keywords

        Returns:
            Created solution
        """
        solution = Solution(
            id=uuid4(),
            category=category,
            title=title,
            description=description,
            steps=steps,
            keywords=keywords
        )

        self._solutions[solution.id] = solution

        logger.info(f"Solution added: {solution.id} - {title}")
        return solution

    async def get_task(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a processing task."""
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    async def list_tasks(
        self,
        status: Optional[ProcessingStatus] = None,
        priority: Optional[ProcessingPriority] = None,
        assigned_to: Optional[str] = None,
        sla_breached: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List processing tasks with filters.

        Args:
            status: Filter by status
            priority: Filter by priority
            assigned_to: Filter by handler
            sla_breached: Filter by SLA breach
            limit: Max results
            offset: Pagination offset

        Returns:
            Tuple of (tasks, total_count)
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        if sla_breached is not None:
            tasks = [t for t in tasks if t.sla_breached == sla_breached]

        # Sort by priority and SLA deadline
        priority_order = {
            ProcessingPriority.URGENT: 0,
            ProcessingPriority.HIGH: 1,
            ProcessingPriority.MEDIUM: 2,
            ProcessingPriority.LOW: 3
        }
        tasks.sort(key=lambda x: (priority_order.get(x.priority, 4), x.sla_deadline or datetime.max))

        total = len(tasks)
        tasks = tasks[offset:offset + limit]

        return [t.to_dict() for t in tasks], total

    async def get_processing_statistics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get processing statistics.

        Args:
            days: Analysis period

        Returns:
            Statistics dictionary
        """
        cutoff = datetime.now() - timedelta(days=days)
        tasks = [t for t in self._tasks.values() if t.created_at >= cutoff]

        total = len(tasks)
        if total == 0:
            return {
                "period_days": days,
                "total_tasks": 0,
                "avg_resolution_time": 0,
                "sla_compliance_rate": 0,
                "avg_satisfaction": 0
            }

        # Resolution time stats
        resolved_tasks = [t for t in tasks if t.resolution_time]
        avg_resolution_time = (
            sum(t.resolution_time for t in resolved_tasks) / len(resolved_tasks)
            if resolved_tasks else 0
        )

        # SLA compliance
        sla_breached = len([t for t in tasks if t.sla_breached])
        sla_compliance_rate = 1 - (sla_breached / total)

        # Satisfaction scores
        satisfied_tasks = [t for t in tasks if t.satisfaction_score]
        avg_satisfaction = (
            sum(t.satisfaction_score for t in satisfied_tasks) / len(satisfied_tasks)
            if satisfied_tasks else 0
        )

        # By status
        by_status = Counter(t.status.value for t in tasks)

        # By priority
        by_priority = Counter(t.priority.value for t in tasks)

        # Handler performance
        handler_stats = {}
        for handler_id, handler in self._handlers.items():
            handler_tasks = [t for t in tasks if t.assigned_to == handler_id]
            handler_stats[handler_id] = {
                "name": handler["name"],
                "total_tasks": len(handler_tasks),
                "resolved": len([t for t in handler_tasks if t.status in [ProcessingStatus.RESOLVED, ProcessingStatus.CLOSED]]),
                "success_rate": handler["success_rate"]
            }

        return {
            "period_days": days,
            "total_tasks": total,
            "avg_resolution_time_seconds": round(avg_resolution_time),
            "avg_resolution_time_hours": round(avg_resolution_time / 3600, 2),
            "sla_compliance_rate": round(sla_compliance_rate, 4),
            "sla_breached_count": sla_breached,
            "avg_satisfaction_score": round(avg_satisfaction, 2),
            "by_status": dict(by_status),
            "by_priority": dict(by_priority),
            "handler_performance": handler_stats,
            "generated_at": datetime.now().isoformat()
        }

    async def get_satisfaction_statistics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get satisfaction survey statistics.

        Args:
            days: Analysis period

        Returns:
            Statistics dictionary
        """
        cutoff = datetime.now() - timedelta(days=days)
        surveys = [s for s in self._surveys.values() if s.submitted_at >= cutoff]

        total = len(surveys)
        if total == 0:
            return {
                "period_days": days,
                "total_surveys": 0,
                "avg_overall": 0,
                "avg_response_speed": 0,
                "avg_solution_quality": 0,
                "avg_communication": 0
            }

        return {
            "period_days": days,
            "total_surveys": total,
            "avg_overall": round(sum(s.overall_score for s in surveys) / total, 2),
            "avg_response_speed": round(sum(s.response_speed_score for s in surveys) / total, 2),
            "avg_solution_quality": round(sum(s.solution_quality_score for s in surveys) / total, 2),
            "avg_communication": round(sum(s.communication_score for s in surveys) / total, 2),
            "satisfaction_distribution": {
                "excellent": len([s for s in surveys if s.overall_score >= 4.5]),
                "good": len([s for s in surveys if 3.5 <= s.overall_score < 4.5]),
                "fair": len([s for s in surveys if 2.5 <= s.overall_score < 3.5]),
                "poor": len([s for s in surveys if s.overall_score < 2.5])
            },
            "generated_at": datetime.now().isoformat()
        }

    async def link_to_ticket(self, task_id: UUID, ticket_id: UUID) -> bool:
        """
        Link a processing task to a ticket.

        Args:
            task_id: Processing task UUID
            ticket_id: Ticket UUID

        Returns:
            True if linked
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.ticket_id = ticket_id
        task.updated_at = datetime.now()

        task.notes.append({
            "action": "ticket_linked",
            "ticket_id": str(ticket_id),
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"Task {task_id} linked to ticket {ticket_id}")
        return True
