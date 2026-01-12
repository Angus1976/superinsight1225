"""
Progress Tracker for SuperInsight Platform.

Provides quality issue resolution progress tracking:
- Milestone management
- Progress visualization data
- Timeline tracking
- Notification integration
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


class MilestoneStatus(str, Enum):
    """Status of milestones."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    SKIPPED = "skipped"


class ProgressStatus(str, Enum):
    """Overall progress status."""
    NOT_STARTED = "not_started"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    DELAYED = "delayed"
    COMPLETED = "completed"


@dataclass
class Milestone:
    """Represents a progress milestone."""
    milestone_id: str
    name: str
    description: str
    target_date: datetime
    status: MilestoneStatus = MilestoneStatus.PENDING
    progress_percent: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    completed_deliverables: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "name": self.name,
            "description": self.description,
            "target_date": self.target_date.isoformat(),
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "dependencies": self.dependencies,
            "deliverables": self.deliverables,
            "completed_deliverables": self.completed_deliverables,
            "owner": self.owner,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class ProgressRecord:
    """Represents a progress tracking record."""
    record_id: str
    entity_id: str
    entity_type: str  # project, ticket, batch, task
    name: str
    description: Optional[str] = None
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    progress_percent: float = 0.0
    milestones: List[str] = field(default_factory=list)
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    owner: Optional[str] = None
    team_members: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "milestones": self.milestones,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "actual_end_date": self.actual_end_date.isoformat() if self.actual_end_date else None,
            "owner": self.owner,
            "team_members": self.team_members,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ProgressUpdate:
    """Represents a progress update event."""
    update_id: str
    record_id: str
    previous_progress: float
    new_progress: float
    previous_status: ProgressStatus
    new_status: ProgressStatus
    update_type: str  # manual, automatic, milestone_completed
    updated_by: Optional[str] = None
    notes: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "update_id": self.update_id,
            "record_id": self.record_id,
            "previous_progress": self.previous_progress,
            "new_progress": self.new_progress,
            "previous_status": self.previous_status.value,
            "new_status": self.new_status.value,
            "update_type": self.update_type,
            "updated_by": self.updated_by,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat()
        }


class MilestoneManager:
    """Manages milestones for progress tracking."""

    def __init__(self):
        self.milestones: Dict[str, Milestone] = {}
        self.milestone_templates: Dict[str, List[Dict[str, Any]]] = {}
        self._initialize_templates()

    def _initialize_templates(self):
        """Initialize milestone templates."""
        self.milestone_templates = {
            "quality_improvement": [
                {"name": "问题识别", "description": "识别和分析质量问题", "days_offset": 0},
                {"name": "方案制定", "description": "制定改进方案", "days_offset": 2},
                {"name": "实施改进", "description": "执行改进措施", "days_offset": 5},
                {"name": "验证效果", "description": "验证改进效果", "days_offset": 7},
                {"name": "总结归档", "description": "总结经验并归档", "days_offset": 10}
            ],
            "reannotation_batch": [
                {"name": "任务分配", "description": "分配重新标注任务", "days_offset": 0},
                {"name": "标注进行", "description": "执行重新标注", "days_offset": 3},
                {"name": "质量审核", "description": "审核标注质量", "days_offset": 5},
                {"name": "完成验收", "description": "完成验收确认", "days_offset": 7}
            ],
            "anomaly_resolution": [
                {"name": "异常确认", "description": "确认异常情况", "days_offset": 0},
                {"name": "原因分析", "description": "分析异常原因", "days_offset": 1},
                {"name": "修复实施", "description": "实施修复措施", "days_offset": 3},
                {"name": "验证关闭", "description": "验证并关闭", "days_offset": 5}
            ]
        }

    def create_milestone(
        self,
        name: str,
        description: str,
        target_date: datetime,
        owner: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        deliverables: Optional[List[str]] = None
    ) -> Milestone:
        """Create a new milestone."""
        milestone = Milestone(
            milestone_id=str(uuid.uuid4()),
            name=name,
            description=description,
            target_date=target_date,
            owner=owner,
            dependencies=dependencies or [],
            deliverables=deliverables or []
        )
        self.milestones[milestone.milestone_id] = milestone
        return milestone

    def create_from_template(
        self,
        template_name: str,
        start_date: Optional[datetime] = None,
        owner: Optional[str] = None
    ) -> List[Milestone]:
        """Create milestones from a template."""
        template = self.milestone_templates.get(template_name)
        if not template:
            return []
        
        base_date = start_date or datetime.now()
        milestones = []
        prev_milestone_id = None
        
        for config in template:
            target_date = base_date + timedelta(days=config["days_offset"])
            dependencies = [prev_milestone_id] if prev_milestone_id else []
            
            milestone = self.create_milestone(
                name=config["name"],
                description=config["description"],
                target_date=target_date,
                owner=owner,
                dependencies=dependencies
            )
            milestones.append(milestone)
            prev_milestone_id = milestone.milestone_id
        
        return milestones

    def update_milestone(
        self,
        milestone_id: str,
        **updates
    ) -> Optional[Milestone]:
        """Update a milestone."""
        milestone = self.milestones.get(milestone_id)
        if not milestone:
            return None
        
        for key, value in updates.items():
            if hasattr(milestone, key):
                setattr(milestone, key, value)
        
        return milestone

    def start_milestone(self, milestone_id: str) -> bool:
        """Mark a milestone as started."""
        milestone = self.milestones.get(milestone_id)
        if not milestone:
            return False
        
        # Check dependencies
        for dep_id in milestone.dependencies:
            dep = self.milestones.get(dep_id)
            if dep and dep.status != MilestoneStatus.COMPLETED:
                logger.warning(f"Dependency {dep_id} not completed")
                return False
        
        milestone.status = MilestoneStatus.IN_PROGRESS
        milestone.started_at = datetime.now()
        return True

    def complete_milestone(
        self,
        milestone_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Mark a milestone as completed."""
        milestone = self.milestones.get(milestone_id)
        if not milestone:
            return False
        
        milestone.status = MilestoneStatus.COMPLETED
        milestone.completed_at = datetime.now()
        milestone.progress_percent = 100.0
        if notes:
            milestone.notes = notes
        
        return True

    def complete_deliverable(
        self,
        milestone_id: str,
        deliverable: str
    ) -> bool:
        """Mark a deliverable as completed."""
        milestone = self.milestones.get(milestone_id)
        if not milestone:
            return False
        
        if deliverable in milestone.deliverables:
            if deliverable not in milestone.completed_deliverables:
                milestone.completed_deliverables.append(deliverable)
            
            # Update progress
            if milestone.deliverables:
                milestone.progress_percent = (
                    len(milestone.completed_deliverables) /
                    len(milestone.deliverables) * 100
                )
            
            return True
        return False

    def check_overdue(self) -> List[Milestone]:
        """Check for overdue milestones."""
        now = datetime.now()
        overdue = []
        
        for milestone in self.milestones.values():
            if milestone.status in [MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS]:
                if milestone.target_date < now:
                    milestone.status = MilestoneStatus.OVERDUE
                    overdue.append(milestone)
        
        return overdue

    def get_milestone(self, milestone_id: str) -> Optional[Milestone]:
        """Get a milestone by ID."""
        return self.milestones.get(milestone_id)

    def list_milestones(
        self,
        status: Optional[MilestoneStatus] = None,
        owner: Optional[str] = None
    ) -> List[Milestone]:
        """List milestones with filters."""
        milestones = list(self.milestones.values())
        
        if status:
            milestones = [m for m in milestones if m.status == status]
        if owner:
            milestones = [m for m in milestones if m.owner == owner]
        
        return sorted(milestones, key=lambda m: m.target_date)


class ProgressTracker:
    """
    Progress tracking system for quality improvements.
    
    Provides:
    - Progress record management
    - Milestone tracking
    - Timeline visualization data
    - Progress notifications
    """

    def __init__(self):
        self.records: Dict[str, ProgressRecord] = {}
        self.milestone_manager = MilestoneManager()
        self.updates: List[ProgressUpdate] = []
        self.notifications_enabled = True

    def create_progress_record(
        self,
        entity_id: str,
        entity_type: str,
        name: str,
        description: Optional[str] = None,
        start_date: Optional[datetime] = None,
        target_date: Optional[datetime] = None,
        owner: Optional[str] = None,
        team_members: Optional[List[str]] = None,
        milestone_template: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProgressRecord:
        """
        Create a new progress record.
        
        Args:
            entity_id: ID of the entity being tracked
            entity_type: Type of entity (project, ticket, batch)
            name: Name of the progress record
            description: Description
            start_date: Start date
            target_date: Target completion date
            owner: Owner of the progress
            team_members: Team members involved
            milestone_template: Template for auto-creating milestones
            metadata: Additional metadata
            
        Returns:
            Created ProgressRecord
        """
        record = ProgressRecord(
            record_id=str(uuid.uuid4()),
            entity_id=entity_id,
            entity_type=entity_type,
            name=name,
            description=description,
            start_date=start_date or datetime.now(),
            target_date=target_date,
            owner=owner,
            team_members=team_members or [],
            metadata=metadata or {}
        )
        
        # Create milestones from template if specified
        if milestone_template:
            milestones = self.milestone_manager.create_from_template(
                milestone_template,
                start_date=record.start_date,
                owner=owner
            )
            record.milestones = [m.milestone_id for m in milestones]
        
        self.records[record.record_id] = record
        logger.info(f"Created progress record {record.record_id} for {entity_type}/{entity_id}")
        
        return record

    def update_progress(
        self,
        record_id: str,
        progress_percent: float,
        updated_by: Optional[str] = None,
        notes: Optional[str] = None,
        update_type: str = "manual"
    ) -> Optional[ProgressUpdate]:
        """
        Update progress for a record.
        
        Args:
            record_id: Record ID
            progress_percent: New progress percentage (0-100)
            updated_by: User making the update
            notes: Update notes
            update_type: Type of update
            
        Returns:
            ProgressUpdate if successful
        """
        record = self.records.get(record_id)
        if not record:
            return None
        
        # Clamp progress
        progress_percent = max(0, min(100, progress_percent))
        
        # Determine new status
        previous_status = record.status
        new_status = self._determine_status(record, progress_percent)
        
        # Create update record
        update = ProgressUpdate(
            update_id=str(uuid.uuid4()),
            record_id=record_id,
            previous_progress=record.progress_percent,
            new_progress=progress_percent,
            previous_status=previous_status,
            new_status=new_status,
            update_type=update_type,
            updated_by=updated_by,
            notes=notes
        )
        
        # Apply update
        record.progress_percent = progress_percent
        record.status = new_status
        record.updated_at = datetime.now()
        
        if progress_percent >= 100:
            record.actual_end_date = datetime.now()
        
        self.updates.append(update)
        
        # Send notification if status changed
        if self.notifications_enabled and previous_status != new_status:
            self._send_status_notification(record, previous_status, new_status)
        
        return update

    def _determine_status(
        self,
        record: ProgressRecord,
        progress_percent: float
    ) -> ProgressStatus:
        """Determine progress status based on progress and timeline."""
        if progress_percent >= 100:
            return ProgressStatus.COMPLETED
        
        if progress_percent == 0:
            return ProgressStatus.NOT_STARTED
        
        if not record.target_date:
            return ProgressStatus.ON_TRACK
        
        now = datetime.now()
        
        # Calculate expected progress
        if record.start_date:
            total_duration = (record.target_date - record.start_date).total_seconds()
            elapsed = (now - record.start_date).total_seconds()
            expected_progress = (elapsed / total_duration * 100) if total_duration > 0 else 0
        else:
            expected_progress = 50  # Default assumption
        
        # Determine status based on progress vs expected
        if now > record.target_date:
            return ProgressStatus.DELAYED
        elif progress_percent < expected_progress - 20:
            return ProgressStatus.AT_RISK
        else:
            return ProgressStatus.ON_TRACK

    def _send_status_notification(
        self,
        record: ProgressRecord,
        old_status: ProgressStatus,
        new_status: ProgressStatus
    ):
        """Send notification for status change."""
        # TODO: Integrate with notification system
        logger.info(
            f"Progress status changed for {record.entity_type}/{record.entity_id}: "
            f"{old_status.value} -> {new_status.value}"
        )

    def complete_milestone(
        self,
        record_id: str,
        milestone_id: str,
        completed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Complete a milestone and update progress."""
        record = self.records.get(record_id)
        if not record or milestone_id not in record.milestones:
            return False
        
        # Complete the milestone
        success = self.milestone_manager.complete_milestone(milestone_id, notes)
        if not success:
            return False
        
        # Calculate new progress based on milestones
        completed_count = sum(
            1 for mid in record.milestones
            if self.milestone_manager.get_milestone(mid) and
            self.milestone_manager.get_milestone(mid).status == MilestoneStatus.COMPLETED
        )
        
        new_progress = (completed_count / len(record.milestones) * 100) if record.milestones else 0
        
        # Update progress
        self.update_progress(
            record_id,
            new_progress,
            updated_by=completed_by,
            notes=f"Milestone completed: {milestone_id}",
            update_type="milestone_completed"
        )
        
        return True

    def get_record(self, record_id: str) -> Optional[ProgressRecord]:
        """Get a progress record by ID."""
        return self.records.get(record_id)

    def get_record_by_entity(
        self,
        entity_id: str,
        entity_type: str
    ) -> Optional[ProgressRecord]:
        """Get progress record by entity."""
        for record in self.records.values():
            if record.entity_id == entity_id and record.entity_type == entity_type:
                return record
        return None

    def list_records(
        self,
        entity_type: Optional[str] = None,
        status: Optional[ProgressStatus] = None,
        owner: Optional[str] = None,
        limit: int = 100
    ) -> List[ProgressRecord]:
        """List progress records with filters."""
        records = list(self.records.values())
        
        if entity_type:
            records = [r for r in records if r.entity_type == entity_type]
        if status:
            records = [r for r in records if r.status == status]
        if owner:
            records = [r for r in records if r.owner == owner]
        
        return sorted(records, key=lambda r: r.updated_at, reverse=True)[:limit]

    def get_timeline_data(self, record_id: str) -> Dict[str, Any]:
        """Get timeline visualization data for a record."""
        record = self.records.get(record_id)
        if not record:
            return {}
        
        milestones_data = []
        for mid in record.milestones:
            milestone = self.milestone_manager.get_milestone(mid)
            if milestone:
                milestones_data.append(milestone.to_dict())
        
        updates_data = [
            u.to_dict() for u in self.updates
            if u.record_id == record_id
        ]
        
        return {
            "record": record.to_dict(),
            "milestones": milestones_data,
            "updates": updates_data,
            "timeline": self._generate_timeline(record, milestones_data)
        }

    def _generate_timeline(
        self,
        record: ProgressRecord,
        milestones: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate timeline events."""
        events = []
        
        # Add start event
        if record.start_date:
            events.append({
                "type": "start",
                "date": record.start_date.isoformat(),
                "title": "开始",
                "description": f"开始跟踪 {record.name}"
            })
        
        # Add milestone events
        for m in milestones:
            events.append({
                "type": "milestone",
                "date": m["target_date"],
                "title": m["name"],
                "description": m["description"],
                "status": m["status"]
            })
        
        # Add target date
        if record.target_date:
            events.append({
                "type": "target",
                "date": record.target_date.isoformat(),
                "title": "目标完成日期",
                "description": "计划完成时间"
            })
        
        # Add completion event
        if record.actual_end_date:
            events.append({
                "type": "completed",
                "date": record.actual_end_date.isoformat(),
                "title": "完成",
                "description": "实际完成时间"
            })
        
        return sorted(events, key=lambda e: e["date"])

    def get_statistics(
        self,
        entity_type: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get progress tracking statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        
        records = list(self.records.values())
        if entity_type:
            records = [r for r in records if r.entity_type == entity_type]
        
        recent = [r for r in records if r.created_at >= cutoff]
        
        by_status = defaultdict(int)
        by_type = defaultdict(int)
        completion_times = []
        
        for record in recent:
            by_status[record.status.value] += 1
            by_type[record.entity_type] += 1
            
            if record.actual_end_date and record.start_date:
                completion_times.append(
                    (record.actual_end_date - record.start_date).total_seconds()
                )
        
        avg_completion = (
            sum(completion_times) / len(completion_times)
            if completion_times else 0
        )
        
        # Check overdue milestones
        overdue_milestones = self.milestone_manager.check_overdue()
        
        return {
            "period_days": days,
            "total_records": len(recent),
            "by_status": dict(by_status),
            "by_type": dict(by_type),
            "avg_completion_time_seconds": avg_completion,
            "on_track_rate": (
                by_status.get("on_track", 0) / len(recent)
                if recent else 0
            ),
            "completion_rate": (
                by_status.get("completed", 0) / len(recent)
                if recent else 0
            ),
            "overdue_milestones": len(overdue_milestones),
            "generated_at": datetime.now().isoformat()
        }


# Global instance
progress_tracker = ProgressTracker()
