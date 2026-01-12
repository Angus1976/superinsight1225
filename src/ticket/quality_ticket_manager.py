"""
Quality Ticket Manager for SuperInsight Platform.

Extends the base ticket system with quality-specific functionality:
- Quality issue ticket creation
- Intelligent assignment engine
- Escalation management
- SLA tracking for quality issues
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


class QualityTicketType(str, Enum):
    """Types of quality tickets."""
    ANOMALY = "anomaly"
    LOW_QUALITY = "low_quality"
    DISAGREEMENT = "disagreement"
    REANNOTATION = "reannotation"
    REVIEW_REQUEST = "review_request"
    ESCALATION = "escalation"
    COMPLIANCE = "compliance"
    TRAINING = "training"


class QualityTicketPriority(str, Enum):
    """Priority levels for quality tickets."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QualityTicketStatus(str, Enum):
    """Status of quality tickets."""
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class QualityTicket:
    """Represents a quality-related ticket."""
    ticket_id: str
    ticket_type: QualityTicketType
    priority: QualityTicketPriority
    status: QualityTicketStatus
    title: str
    description: str
    project_id: str
    anomaly_id: Optional[str] = None
    task_id: Optional[str] = None
    annotation_id: Optional[str] = None
    affected_entity_id: Optional[str] = None
    affected_entity_type: Optional[str] = None
    quality_score: Optional[float] = None
    quality_threshold: Optional[float] = None
    assigned_to: Optional[str] = None
    assigned_by: Optional[str] = None
    escalation_level: int = 0
    sla_deadline: Optional[datetime] = None
    sla_breached: bool = False
    resolution_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "ticket_type": self.ticket_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "project_id": self.project_id,
            "anomaly_id": self.anomaly_id,
            "task_id": self.task_id,
            "annotation_id": self.annotation_id,
            "affected_entity_id": self.affected_entity_id,
            "affected_entity_type": self.affected_entity_type,
            "quality_score": self.quality_score,
            "quality_threshold": self.quality_threshold,
            "assigned_to": self.assigned_to,
            "assigned_by": self.assigned_by,
            "escalation_level": self.escalation_level,
            "sla_deadline": self.sla_deadline.isoformat() if self.sla_deadline else None,
            "sla_breached": self.sla_breached,
            "resolution_notes": self.resolution_notes,
            "metadata": self.metadata,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None
        }


@dataclass
class ExpertProfile:
    """Profile of a quality expert for assignment."""
    expert_id: str
    name: str
    skills: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)
    quality_score: float = 0.8
    availability: float = 1.0
    current_workload: int = 0
    max_workload: int = 10
    completed_tickets: int = 0
    avg_resolution_time: float = 0.0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expert_id": self.expert_id,
            "name": self.name,
            "skills": self.skills,
            "specializations": self.specializations,
            "quality_score": self.quality_score,
            "availability": self.availability,
            "current_workload": self.current_workload,
            "max_workload": self.max_workload,
            "completed_tickets": self.completed_tickets,
            "avg_resolution_time": self.avg_resolution_time,
            "is_active": self.is_active
        }


class SLAConfiguration:
    """SLA configuration for quality tickets."""
    
    DEFAULT_SLA = {
        QualityTicketPriority.CRITICAL: timedelta(hours=4),
        QualityTicketPriority.HIGH: timedelta(hours=24),
        QualityTicketPriority.MEDIUM: timedelta(hours=72),
        QualityTicketPriority.LOW: timedelta(days=7)
    }

    @classmethod
    def get_deadline(
        cls,
        priority: QualityTicketPriority,
        created_at: Optional[datetime] = None
    ) -> datetime:
        """Get SLA deadline for a priority level."""
        base_time = created_at or datetime.now()
        duration = cls.DEFAULT_SLA.get(priority, timedelta(days=7))
        return base_time + duration


class IntelligentAssignmentEngine:
    """Intelligent assignment engine for quality tickets."""

    def __init__(self):
        self.experts: Dict[str, ExpertProfile] = {}
        self.assignment_history: List[Dict[str, Any]] = []
        self.skill_weights: Dict[str, float] = {}

    def register_expert(self, expert: ExpertProfile):
        """Register a quality expert."""
        self.experts[expert.expert_id] = expert
        logger.info(f"Registered expert: {expert.name}")

    def unregister_expert(self, expert_id: str) -> bool:
        """Unregister an expert."""
        if expert_id in self.experts:
            del self.experts[expert_id]
            return True
        return False

    def update_expert(self, expert_id: str, **updates) -> bool:
        """Update expert profile."""
        expert = self.experts.get(expert_id)
        if not expert:
            return False
        
        for key, value in updates.items():
            if hasattr(expert, key):
                setattr(expert, key, value)
        return True

    def find_best_expert(
        self,
        ticket: QualityTicket,
        required_skills: Optional[List[str]] = None,
        exclude_experts: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Find the best expert for a ticket.
        
        Args:
            ticket: The quality ticket
            required_skills: Required skills
            exclude_experts: Experts to exclude
            
        Returns:
            Best expert ID or None
        """
        candidates = []
        exclude_set = set(exclude_experts or [])
        
        for expert_id, expert in self.experts.items():
            # Skip excluded experts
            if expert_id in exclude_set:
                continue
            
            # Check availability
            if not expert.is_active or expert.availability <= 0:
                continue
            
            # Check workload capacity
            if expert.current_workload >= expert.max_workload:
                continue
            
            # Check required skills
            if required_skills:
                if not all(s in expert.skills for s in required_skills):
                    continue
            
            # Calculate assignment score
            score = self._calculate_assignment_score(expert, ticket)
            candidates.append((expert_id, score))
        
        if not candidates:
            return None
        
        # Sort by score and return best
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _calculate_assignment_score(
        self,
        expert: ExpertProfile,
        ticket: QualityTicket
    ) -> float:
        """Calculate assignment score for an expert."""
        score = 0.0
        
        # Quality score weight (40%)
        score += expert.quality_score * 0.4
        
        # Availability weight (20%)
        score += expert.availability * 0.2
        
        # Workload factor (20%) - prefer less loaded experts
        workload_ratio = 1 - (expert.current_workload / max(expert.max_workload, 1))
        score += workload_ratio * 0.2
        
        # Specialization match (15%)
        if ticket.ticket_type.value in expert.specializations:
            score += 0.15
        
        # Experience factor (5%)
        experience_factor = min(expert.completed_tickets / 100, 1.0)
        score += experience_factor * 0.05
        
        return score

    def assign_ticket(
        self,
        ticket: QualityTicket,
        expert_id: Optional[str] = None,
        assigned_by: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Assign a ticket to an expert.
        
        Args:
            ticket: The ticket to assign
            expert_id: Specific expert ID (optional)
            assigned_by: User making the assignment
            
        Returns:
            Tuple of (success, assigned_expert_id)
        """
        # Find expert if not specified
        if not expert_id:
            expert_id = self.find_best_expert(ticket)
        
        if not expert_id:
            return False, None
        
        expert = self.experts.get(expert_id)
        if not expert:
            return False, None
        
        # Update ticket
        ticket.assigned_to = expert_id
        ticket.assigned_by = assigned_by or "system"
        ticket.assigned_at = datetime.now()
        ticket.status = QualityTicketStatus.ASSIGNED
        
        # Update expert workload
        expert.current_workload += 1
        
        # Record assignment
        self.assignment_history.append({
            "ticket_id": ticket.ticket_id,
            "expert_id": expert_id,
            "assigned_by": assigned_by,
            "assigned_at": datetime.now().isoformat(),
            "ticket_type": ticket.ticket_type.value,
            "priority": ticket.priority.value
        })
        
        logger.info(f"Assigned ticket {ticket.ticket_id} to expert {expert_id}")
        return True, expert_id

    def release_assignment(self, ticket: QualityTicket) -> bool:
        """Release a ticket assignment."""
        if not ticket.assigned_to:
            return False
        
        expert = self.experts.get(ticket.assigned_to)
        if expert:
            expert.current_workload = max(0, expert.current_workload - 1)
        
        ticket.assigned_to = None
        ticket.assigned_at = None
        ticket.status = QualityTicketStatus.OPEN
        
        return True


class EscalationManager:
    """Manages ticket escalation workflows."""

    def __init__(self):
        self.escalation_rules: Dict[str, Dict[str, Any]] = {}
        self.escalation_history: List[Dict[str, Any]] = []
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default escalation rules."""
        self.escalation_rules = {
            "sla_breach": {
                "name": "SLA违规升级",
                "description": "SLA即将或已经违规时自动升级",
                "trigger": "sla_breach",
                "escalation_levels": [
                    {"level": 1, "notify": ["team_lead"], "deadline_hours": 2},
                    {"level": 2, "notify": ["manager"], "deadline_hours": 4},
                    {"level": 3, "notify": ["director"], "deadline_hours": 8}
                ]
            },
            "critical_quality": {
                "name": "关键质量问题升级",
                "description": "关键质量问题自动升级",
                "trigger": "critical_priority",
                "escalation_levels": [
                    {"level": 1, "notify": ["quality_lead"], "deadline_hours": 1},
                    {"level": 2, "notify": ["quality_manager"], "deadline_hours": 2}
                ]
            },
            "unassigned": {
                "name": "未分配工单升级",
                "description": "长时间未分配的工单升级",
                "trigger": "unassigned_timeout",
                "timeout_hours": 4,
                "escalation_levels": [
                    {"level": 1, "notify": ["dispatcher"], "deadline_hours": 2}
                ]
            }
        }

    def add_rule(self, rule_id: str, rule: Dict[str, Any]):
        """Add an escalation rule."""
        self.escalation_rules[rule_id] = rule

    def check_escalation(self, ticket: QualityTicket) -> Optional[Dict[str, Any]]:
        """
        Check if a ticket needs escalation.
        
        Returns escalation action if needed, None otherwise.
        """
        now = datetime.now()
        
        # Check SLA breach
        if ticket.sla_deadline and now > ticket.sla_deadline:
            if not ticket.sla_breached:
                ticket.sla_breached = True
            return self._get_escalation_action(ticket, "sla_breach")
        
        # Check critical priority
        if ticket.priority == QualityTicketPriority.CRITICAL:
            if ticket.status == QualityTicketStatus.OPEN:
                return self._get_escalation_action(ticket, "critical_quality")
        
        # Check unassigned timeout
        if ticket.status == QualityTicketStatus.OPEN and not ticket.assigned_to:
            rule = self.escalation_rules.get("unassigned", {})
            timeout_hours = rule.get("timeout_hours", 4)
            if (now - ticket.created_at).total_seconds() > timeout_hours * 3600:
                return self._get_escalation_action(ticket, "unassigned")
        
        return None

    def _get_escalation_action(
        self,
        ticket: QualityTicket,
        rule_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get escalation action for a rule."""
        rule = self.escalation_rules.get(rule_id)
        if not rule:
            return None
        
        levels = rule.get("escalation_levels", [])
        current_level = ticket.escalation_level
        
        # Find next escalation level
        for level_config in levels:
            if level_config["level"] > current_level:
                return {
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "new_level": level_config["level"],
                    "notify": level_config["notify"],
                    "deadline_hours": level_config["deadline_hours"]
                }
        
        return None

    async def escalate_ticket(
        self,
        ticket: QualityTicket,
        escalation_action: Dict[str, Any],
        escalated_by: Optional[str] = None
    ) -> bool:
        """Execute ticket escalation."""
        new_level = escalation_action["new_level"]
        
        ticket.escalation_level = new_level
        ticket.status = QualityTicketStatus.ESCALATED
        ticket.metadata["last_escalation"] = {
            "level": new_level,
            "rule": escalation_action["rule_id"],
            "escalated_at": datetime.now().isoformat(),
            "escalated_by": escalated_by or "system"
        }
        
        # Record history
        self.escalation_history.append({
            "ticket_id": ticket.ticket_id,
            "rule_id": escalation_action["rule_id"],
            "old_level": new_level - 1,
            "new_level": new_level,
            "notify": escalation_action["notify"],
            "escalated_at": datetime.now().isoformat()
        })
        
        logger.info(f"Escalated ticket {ticket.ticket_id} to level {new_level}")
        
        # TODO: Send notifications to escalation_action["notify"]
        
        return True


class QualityTicketManager:
    """
    Quality-specific ticket management system.
    
    Extends base ticket functionality with:
    - Quality issue tracking
    - Intelligent assignment
    - Escalation management
    - SLA monitoring
    """

    def __init__(self):
        self.tickets: Dict[str, QualityTicket] = {}
        self.assignment_engine = IntelligentAssignmentEngine()
        self.escalation_manager = EscalationManager()
        self.ticket_history: List[Dict[str, Any]] = []
        self.stats: Dict[str, int] = defaultdict(int)

    async def create_ticket(
        self,
        ticket_type: QualityTicketType,
        title: str,
        description: str,
        project_id: str,
        priority: QualityTicketPriority = QualityTicketPriority.MEDIUM,
        anomaly_id: Optional[str] = None,
        task_id: Optional[str] = None,
        annotation_id: Optional[str] = None,
        affected_entity_id: Optional[str] = None,
        affected_entity_type: Optional[str] = None,
        quality_score: Optional[float] = None,
        quality_threshold: Optional[float] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_assign: bool = True
    ) -> QualityTicket:
        """
        Create a new quality ticket.
        
        Args:
            ticket_type: Type of quality ticket
            title: Ticket title
            description: Detailed description
            project_id: Project ID
            priority: Ticket priority
            anomaly_id: Related anomaly ID
            task_id: Related task ID
            annotation_id: Related annotation ID
            affected_entity_id: Affected entity ID
            affected_entity_type: Type of affected entity
            quality_score: Current quality score
            quality_threshold: Required quality threshold
            created_by: User creating the ticket
            metadata: Additional metadata
            auto_assign: Whether to auto-assign
            
        Returns:
            Created QualityTicket
        """
        ticket = QualityTicket(
            ticket_id=str(uuid.uuid4()),
            ticket_type=ticket_type,
            priority=priority,
            status=QualityTicketStatus.OPEN,
            title=title,
            description=description,
            project_id=project_id,
            anomaly_id=anomaly_id,
            task_id=task_id,
            annotation_id=annotation_id,
            affected_entity_id=affected_entity_id,
            affected_entity_type=affected_entity_type,
            quality_score=quality_score,
            quality_threshold=quality_threshold,
            sla_deadline=SLAConfiguration.get_deadline(priority),
            created_by=created_by,
            metadata=metadata or {}
        )
        
        self.tickets[ticket.ticket_id] = ticket
        self.stats["created"] += 1
        
        # Record history
        self._record_history(ticket, "created", created_by)
        
        logger.info(f"Created quality ticket {ticket.ticket_id}: {title}")
        
        # Auto-assign if requested
        if auto_assign:
            await self.assign_ticket(ticket.ticket_id)
        
        return ticket

    async def create_from_anomaly(
        self,
        anomaly_id: str,
        anomaly_type: str,
        severity: str,
        entity_id: str,
        entity_type: str,
        metric_name: str,
        metric_value: float,
        expected_range: Tuple[float, float],
        project_id: str,
        recommendations: Optional[List[str]] = None
    ) -> QualityTicket:
        """Create a ticket from a detected anomaly."""
        # Map severity to priority
        priority_map = {
            "critical": QualityTicketPriority.CRITICAL,
            "high": QualityTicketPriority.HIGH,
            "medium": QualityTicketPriority.MEDIUM,
            "low": QualityTicketPriority.LOW
        }
        priority = priority_map.get(severity.lower(), QualityTicketPriority.MEDIUM)
        
        title = f"质量异常: {metric_name} = {metric_value:.3f}"
        description = (
            f"检测到质量异常:\n"
            f"- 异常类型: {anomaly_type}\n"
            f"- 影响实体: {entity_type}/{entity_id}\n"
            f"- 指标名称: {metric_name}\n"
            f"- 当前值: {metric_value:.3f}\n"
            f"- 期望范围: {expected_range[0]:.3f} - {expected_range[1]:.3f}\n"
        )
        
        if recommendations:
            description += "\n建议操作:\n"
            for rec in recommendations:
                description += f"- {rec}\n"
        
        return await self.create_ticket(
            ticket_type=QualityTicketType.ANOMALY,
            title=title,
            description=description,
            project_id=project_id,
            priority=priority,
            anomaly_id=anomaly_id,
            affected_entity_id=entity_id,
            affected_entity_type=entity_type,
            quality_score=metric_value,
            metadata={
                "anomaly_type": anomaly_type,
                "metric_name": metric_name,
                "expected_range": list(expected_range),
                "recommendations": recommendations or []
            }
        )

    async def assign_ticket(
        self,
        ticket_id: str,
        expert_id: Optional[str] = None,
        assigned_by: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Assign a ticket to an expert."""
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return False, None
        
        success, assigned_id = self.assignment_engine.assign_ticket(
            ticket, expert_id, assigned_by
        )
        
        if success:
            self._record_history(ticket, "assigned", assigned_by, {
                "assigned_to": assigned_id
            })
            self.stats["assigned"] += 1
        
        return success, assigned_id

    async def start_ticket(self, ticket_id: str, started_by: str) -> bool:
        """Mark a ticket as started."""
        ticket = self.tickets.get(ticket_id)
        if not ticket or ticket.status != QualityTicketStatus.ASSIGNED:
            return False
        
        ticket.status = QualityTicketStatus.IN_PROGRESS
        ticket.started_at = datetime.now()
        
        self._record_history(ticket, "started", started_by)
        self.stats["started"] += 1
        
        return True

    async def submit_for_review(
        self,
        ticket_id: str,
        submitted_by: str,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Submit a ticket for review."""
        ticket = self.tickets.get(ticket_id)
        if not ticket or ticket.status != QualityTicketStatus.IN_PROGRESS:
            return False
        
        ticket.status = QualityTicketStatus.PENDING_REVIEW
        if resolution_notes:
            ticket.resolution_notes = resolution_notes
        
        self._record_history(ticket, "submitted_for_review", submitted_by)
        
        return True

    async def resolve_ticket(
        self,
        ticket_id: str,
        resolved_by: str,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Resolve a ticket."""
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return False
        
        if ticket.status not in [
            QualityTicketStatus.IN_PROGRESS,
            QualityTicketStatus.PENDING_REVIEW,
            QualityTicketStatus.ESCALATED
        ]:
            return False
        
        ticket.status = QualityTicketStatus.RESOLVED
        ticket.resolved_at = datetime.now()
        if resolution_notes:
            ticket.resolution_notes = resolution_notes
        
        # Update expert stats
        if ticket.assigned_to:
            expert = self.assignment_engine.experts.get(ticket.assigned_to)
            if expert:
                expert.current_workload = max(0, expert.current_workload - 1)
                expert.completed_tickets += 1
                
                # Update average resolution time
                if ticket.started_at:
                    resolution_time = (ticket.resolved_at - ticket.started_at).total_seconds()
                    if expert.avg_resolution_time == 0:
                        expert.avg_resolution_time = resolution_time
                    else:
                        expert.avg_resolution_time = (
                            expert.avg_resolution_time * (expert.completed_tickets - 1) +
                            resolution_time
                        ) / expert.completed_tickets
        
        self._record_history(ticket, "resolved", resolved_by, {
            "resolution_notes": resolution_notes
        })
        self.stats["resolved"] += 1
        
        return True

    async def close_ticket(
        self,
        ticket_id: str,
        closed_by: str,
        close_notes: Optional[str] = None
    ) -> bool:
        """Close a resolved ticket."""
        ticket = self.tickets.get(ticket_id)
        if not ticket or ticket.status != QualityTicketStatus.RESOLVED:
            return False
        
        ticket.status = QualityTicketStatus.CLOSED
        ticket.closed_at = datetime.now()
        if close_notes:
            ticket.metadata["close_notes"] = close_notes
        
        self._record_history(ticket, "closed", closed_by)
        self.stats["closed"] += 1
        
        return True

    async def check_escalations(self) -> List[QualityTicket]:
        """Check all tickets for needed escalations."""
        escalated = []
        
        for ticket in self.tickets.values():
            if ticket.status in [QualityTicketStatus.RESOLVED, QualityTicketStatus.CLOSED]:
                continue
            
            action = self.escalation_manager.check_escalation(ticket)
            if action:
                await self.escalation_manager.escalate_ticket(ticket, action)
                escalated.append(ticket)
                self.stats["escalated"] += 1
        
        return escalated

    def get_ticket(self, ticket_id: str) -> Optional[QualityTicket]:
        """Get a ticket by ID."""
        return self.tickets.get(ticket_id)

    def list_tickets(
        self,
        project_id: Optional[str] = None,
        status: Optional[QualityTicketStatus] = None,
        priority: Optional[QualityTicketPriority] = None,
        ticket_type: Optional[QualityTicketType] = None,
        assigned_to: Optional[str] = None,
        sla_breached: Optional[bool] = None,
        limit: int = 100
    ) -> List[QualityTicket]:
        """List tickets with filters."""
        tickets = list(self.tickets.values())
        
        if project_id:
            tickets = [t for t in tickets if t.project_id == project_id]
        if status:
            tickets = [t for t in tickets if t.status == status]
        if priority:
            tickets = [t for t in tickets if t.priority == priority]
        if ticket_type:
            tickets = [t for t in tickets if t.ticket_type == ticket_type]
        if assigned_to:
            tickets = [t for t in tickets if t.assigned_to == assigned_to]
        if sla_breached is not None:
            tickets = [t for t in tickets if t.sla_breached == sla_breached]
        
        # Sort by priority and creation time
        tickets.sort(key=lambda t: (
            -list(QualityTicketPriority).index(t.priority),
            t.created_at
        ))
        
        return tickets[:limit]

    def _record_history(
        self,
        ticket: QualityTicket,
        action: str,
        performed_by: Optional[str],
        details: Optional[Dict[str, Any]] = None
    ):
        """Record ticket history."""
        self.ticket_history.append({
            "ticket_id": ticket.ticket_id,
            "action": action,
            "performed_by": performed_by or "system",
            "timestamp": datetime.now().isoformat(),
            "status": ticket.status.value,
            "details": details or {}
        })

    def get_ticket_history(self, ticket_id: str) -> List[Dict[str, Any]]:
        """Get history for a ticket."""
        return [h for h in self.ticket_history if h["ticket_id"] == ticket_id]

    def get_statistics(
        self,
        project_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get ticket statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        
        tickets = list(self.tickets.values())
        if project_id:
            tickets = [t for t in tickets if t.project_id == project_id]
        
        recent = [t for t in tickets if t.created_at >= cutoff]
        
        by_status = defaultdict(int)
        by_priority = defaultdict(int)
        by_type = defaultdict(int)
        resolution_times = []
        
        for ticket in recent:
            by_status[ticket.status.value] += 1
            by_priority[ticket.priority.value] += 1
            by_type[ticket.ticket_type.value] += 1
            
            if ticket.resolved_at and ticket.started_at:
                resolution_times.append(
                    (ticket.resolved_at - ticket.started_at).total_seconds()
                )
        
        avg_resolution = (
            sum(resolution_times) / len(resolution_times)
            if resolution_times else 0
        )
        
        sla_breached = len([t for t in recent if t.sla_breached])
        
        return {
            "period_days": days,
            "total_tickets": len(recent),
            "by_status": dict(by_status),
            "by_priority": dict(by_priority),
            "by_type": dict(by_type),
            "sla_breached": sla_breached,
            "sla_compliance_rate": (
                (len(recent) - sla_breached) / len(recent)
                if recent else 1.0
            ),
            "avg_resolution_time_seconds": avg_resolution,
            "global_stats": dict(self.stats),
            "generated_at": datetime.now().isoformat()
        }


# Global instance
quality_ticket_manager = QualityTicketManager()
