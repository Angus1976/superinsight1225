"""
Annotation Task Service for Data Lifecycle Management

Manages annotation task creation, assignment, progress tracking, and completion.
Integrates with State Manager for state transitions and Audit Logger for task operations.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, cast, String, or_

from src.models.data_lifecycle import (
    AnnotationTaskModel,
    SampleModel,
    TaskStatus,
    AnnotationType,
    DataState,
    ResourceType,
    OperationType,
    OperationResult,
    Action
)
from src.services.data_lifecycle_state_manager import (
    DataStateManager,
    StateTransitionContext
)
from src.services.audit_logger import AuditLogger


def _ensure_uuid(value: Union[str, UUID]) -> UUID:
    """Bind UUID columns correctly (e.g. SQLite + PGUUID(as_uuid=True) vs str path params)."""
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _pk_id_eq(model_class, value: Union[str, UUID]):
    """UUID PK filter for plain SQLite and SQLiteUUID property tests."""
    u = _ensure_uuid(value)
    return or_(
        model_class.id == u,
        cast(model_class.id, String) == str(u),
    )


class TaskConfig:
    """Configuration for creating an annotation task"""
    def __init__(
        self,
        name: str,
        description: Optional[str],
        sample_ids: List[str],
        annotation_type: AnnotationType,
        instructions: str,
        deadline: Optional[datetime] = None,
        assigned_to: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.sample_ids = sample_ids
        self.annotation_type = annotation_type
        self.instructions = instructions
        self.deadline = deadline
        self.assigned_to = assigned_to or []


class Annotation:
    """Annotation submission model"""
    def __init__(
        self,
        task_id: str,
        sample_id: str,
        annotator_id: str,
        labels: List[Dict[str, Any]],
        comments: Optional[str] = None,
        confidence: Optional[float] = None
    ):
        self.task_id = task_id
        self.sample_id = sample_id
        self.annotator_id = annotator_id
        self.labels = labels
        self.comments = comments
        self.confidence = confidence


class TaskProgress:
    """Task progress tracking model"""
    def __init__(
        self,
        total: int,
        completed: int,
        in_progress: int,
        percentage: float
    ):
        self.total = total
        self.completed = completed
        self.in_progress = in_progress
        self.percentage = percentage


class AnnotationResult:
    """Result of annotation submission"""
    def __init__(
        self,
        annotation_id: str,
        task_id: str,
        sample_id: str,
        annotator_id: str,
        submitted_at: datetime
    ):
        self.annotation_id = annotation_id
        self.task_id = task_id
        self.sample_id = sample_id
        self.annotator_id = annotator_id
        self.submitted_at = submitted_at


class AnnotationTaskService:
    """
    Annotation Task Service for managing annotation tasks.
    
    Responsibilities:
    - Create annotation tasks from sample library
    - Assign tasks to annotators
    - Track annotation progress
    - Store annotation results
    - Validate annotation quality
    - Integrate with State Manager for state transitions
    - Integrate with Audit Logger for task operations
    
    Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
    """
    
    def __init__(self, db: Session):
        """
        Initialize the Annotation Task Service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.state_manager = DataStateManager(db)
        self.audit_logger = AuditLogger(db)
    
    def create_task(
        self,
        config: TaskConfig,
        created_by: str
    ) -> Dict[str, Any]:
        """
        Create a new annotation task from sample library data.
        
        Args:
            config: Task configuration with sample IDs, type, instructions, deadline
            created_by: User ID who is creating the task
        
        Returns:
            Dictionary with task details
        
        Raises:
            ValueError: If samples not found or invalid configuration
        
        Validates: Requirements 5.1
        """
        # Validate sample IDs exist
        id_strings = [str(_ensure_uuid(sid)) for sid in config.sample_ids]
        uuid_list = [_ensure_uuid(sid) for sid in config.sample_ids]
        samples = self.db.query(SampleModel).filter(
            or_(
                SampleModel.id.in_(uuid_list),
                cast(SampleModel.id, String).in_(id_strings),
            )
        ).all()
        
        if len(samples) != len(config.sample_ids):
            found_ids = {str(s.id) for s in samples}
            missing_ids = set(config.sample_ids) - found_ids
            raise ValueError(f"Samples not found: {missing_ids}")
        
        # Validate deadline is in the future if provided
        if config.deadline and config.deadline <= datetime.utcnow():
            raise ValueError("Deadline must be a future date")
        
        # Validate name is not empty
        if not config.name or not config.name.strip():
            raise ValueError("Task name is required and cannot be empty")
        
        # Validate instructions are not empty
        if not config.instructions or not config.instructions.strip():
            raise ValueError("Task instructions are required and cannot be empty")
        
        # Create annotation task
        task = AnnotationTaskModel(
            id=uuid4(),
            name=config.name.strip(),
            description=config.description,
            sample_ids=config.sample_ids,
            annotation_type=config.annotation_type,
            instructions=config.instructions.strip(),
            status=TaskStatus.CREATED,
            created_by=created_by,
            created_at=datetime.utcnow(),
            assigned_to=config.assigned_to,
            deadline=config.deadline,
            completed_at=None,
            progress_total=len(config.sample_ids),
            progress_completed=0,
            progress_in_progress=0,
            annotations=[],
            metadata_={
                'sample_count': len(config.sample_ids),
                'created_from': 'sample_library'
            }
        )
        
        self.db.add(task)
        
        # Update sample usage tracking
        for sample in samples:
            sample.usage_count += 1
            sample.last_used_at = datetime.utcnow()
        
        # Log task creation
        self.audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=created_by,
            resource_type=ResourceType.ANNOTATION_TASK,
            resource_id=str(task.id),
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'create_task',
                'task_name': config.name,
                'annotation_type': config.annotation_type.value,
                'sample_count': len(config.sample_ids),
                'assigned_to': config.assigned_to
            }
        )
        
        self.db.commit()
        self.db.refresh(task)
        
        return self._task_to_dict(task)
    
    def assign_annotator(
        self,
        task_id: str,
        annotator_id: str,
        assigned_by: str
    ) -> None:
        """
        Assign an annotator to a task.
        
        Args:
            task_id: ID of the task
            annotator_id: User ID of the annotator to assign
            assigned_by: User ID who is assigning the annotator
        
        Raises:
            ValueError: If task not found or already completed
        
        Validates: Requirements 5.2
        """
        # Get task
        task = self.db.query(AnnotationTaskModel).filter(
            _pk_id_eq(AnnotationTaskModel, task_id)
        ).first()
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Validate task is not completed or cancelled
        if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            raise ValueError(
                f"Cannot assign annotator to {task.status.value} task"
            )
        
        # Add annotator if not already assigned
        if annotator_id not in task.assigned_to:
            task.assigned_to = task.assigned_to + [annotator_id]
            
            # Update task status to IN_PROGRESS if it was CREATED
            if task.status == TaskStatus.CREATED:
                task.status = TaskStatus.IN_PROGRESS
        
        # Log annotator assignment
        self.audit_logger.log_operation(
            operation_type=OperationType.UPDATE,
            user_id=assigned_by,
            resource_type=ResourceType.ANNOTATION_TASK,
            resource_id=task_id,
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'assign_annotator',
                'annotator_id': annotator_id,
                'assigned_by': assigned_by,
                'total_annotators': len(task.assigned_to)
            }
        )
        
        self.db.commit()
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        Retrieve task details.
        
        Args:
            task_id: ID of the task
        
        Returns:
            Dictionary with task details
        
        Raises:
            ValueError: If task not found
        """
        task = self.db.query(AnnotationTaskModel).filter(
            _pk_id_eq(AnnotationTaskModel, task_id)
        ).first()
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        return self._task_to_dict(task)
    
    def submit_annotation(
        self,
        annotation: Annotation
    ) -> AnnotationResult:
        """
        Submit an annotation for a sample in a task.
        
        Args:
            annotation: Annotation data with task_id, sample_id, labels, etc.
        
        Returns:
            AnnotationResult with submission details
        
        Raises:
            ValueError: If task not found, sample not in task, or annotator not assigned
        
        Validates: Requirements 5.3
        """
        # Get task
        task = self.db.query(AnnotationTaskModel).filter(
            _pk_id_eq(AnnotationTaskModel, annotation.task_id)
        ).first()
        
        if not task:
            raise ValueError(f"Task {annotation.task_id} not found")
        
        # Validate task is in progress
        if task.status not in [TaskStatus.CREATED, TaskStatus.IN_PROGRESS]:
            raise ValueError(
                f"Cannot submit annotation for {task.status.value} task"
            )
        
        # Validate sample is in task
        if annotation.sample_id not in task.sample_ids:
            raise ValueError(
                f"Sample {annotation.sample_id} is not part of task {annotation.task_id}"
            )
        
        # Validate annotator is assigned to task
        if annotation.annotator_id not in task.assigned_to:
            raise ValueError(
                f"Annotator {annotation.annotator_id} is not assigned to task {annotation.task_id}"
            )
        
        # Validate labels are provided
        if not annotation.labels:
            raise ValueError("Annotation labels are required and cannot be empty")
        
        submitted_at = datetime.utcnow()
        annotation_id = str(uuid4())
        
        # Create annotation record
        annotation_record = {
            'id': annotation_id,
            'sample_id': annotation.sample_id,
            'annotator_id': annotation.annotator_id,
            'labels': annotation.labels,
            'comments': annotation.comments,
            'confidence': annotation.confidence,
            'submitted_at': submitted_at.isoformat()
        }
        
        # Check if annotation already exists for this sample
        existing_annotations = task.annotations or []
        sample_annotation_exists = any(
            a['sample_id'] == annotation.sample_id 
            for a in existing_annotations
        )
        
        if sample_annotation_exists:
            # Update existing annotation
            task.annotations = [
                annotation_record if a['sample_id'] == annotation.sample_id else a
                for a in existing_annotations
            ]
        else:
            # Add new annotation
            task.annotations = existing_annotations + [annotation_record]
            # Increment completed count
            task.progress_completed += 1
        
        # Update task status to IN_PROGRESS if it was CREATED
        if task.status == TaskStatus.CREATED:
            task.status = TaskStatus.IN_PROGRESS
        
        # Log annotation submission
        self.audit_logger.log_operation(
            operation_type=OperationType.CREATE,
            user_id=annotation.annotator_id,
            resource_type=ResourceType.ANNOTATION_TASK,
            resource_id=annotation.task_id,
            action=Action.ANNOTATE,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'submit_annotation',
                'annotation_id': annotation_id,
                'sample_id': annotation.sample_id,
                'label_count': len(annotation.labels),
                'confidence': annotation.confidence
            }
        )
        
        self.db.commit()
        
        return AnnotationResult(
            annotation_id=annotation_id,
            task_id=annotation.task_id,
            sample_id=annotation.sample_id,
            annotator_id=annotation.annotator_id,
            submitted_at=submitted_at
        )
    
    def get_task_progress(self, task_id: str) -> TaskProgress:
        """
        Get current task progress.
        
        Args:
            task_id: ID of the task
        
        Returns:
            TaskProgress with total, completed, in_progress counts and percentage
        
        Raises:
            ValueError: If task not found
        
        Validates: Requirements 5.4
        """
        task = self.db.query(AnnotationTaskModel).filter(
            _pk_id_eq(AnnotationTaskModel, task_id)
        ).first()
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Calculate progress
        total = task.progress_total
        completed = task.progress_completed
        in_progress = task.progress_in_progress
        
        # Calculate percentage
        percentage = (completed / total * 100) if total > 0 else 0.0
        
        return TaskProgress(
            total=total,
            completed=completed,
            in_progress=in_progress,
            percentage=round(percentage, 2)
        )
    
    def complete_task(
        self,
        task_id: str,
        completed_by: str
    ) -> None:
        """
        Mark task as complete after validating all samples are annotated.
        
        Args:
            task_id: ID of the task
            completed_by: User ID who is completing the task
        
        Raises:
            ValueError: If task not found or not all samples are annotated
        
        Validates: Requirements 5.5, 5.6
        """
        # Get task
        task = self.db.query(AnnotationTaskModel).filter(
            _pk_id_eq(AnnotationTaskModel, task_id)
        ).first()
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Validate task is in progress
        if task.status != TaskStatus.IN_PROGRESS:
            raise ValueError(
                f"Cannot complete task in {task.status.value} status. "
                f"Task must be IN_PROGRESS"
            )
        
        # Validate all samples are annotated
        if task.progress_completed < task.progress_total:
            raise ValueError(
                f"Cannot complete task: {task.progress_completed}/{task.progress_total} "
                f"samples annotated. All samples must be annotated before completion"
            )
        
        # Mark task as completed
        completed_at = datetime.utcnow()
        task.status = TaskStatus.COMPLETED
        task.completed_at = completed_at
        
        # Transition annotated data to ANNOTATED state
        # In a real implementation, this would create annotated data records
        # For now, we just log the completion
        
        # Log task completion
        self.audit_logger.log_operation(
            operation_type=OperationType.UPDATE,
            user_id=completed_by,
            resource_type=ResourceType.ANNOTATION_TASK,
            resource_id=task_id,
            action=Action.EDIT,
            result=OperationResult.SUCCESS,
            duration=0,
            details={
                'action': 'complete_task',
                'completed_by': completed_by,
                'total_annotations': task.progress_completed,
                'duration_days': (completed_at - task.created_at).days
            }
        )
        
        self.db.commit()
    
    def _task_to_dict(self, task: AnnotationTaskModel) -> Dict[str, Any]:
        """Convert task model to dictionary"""
        return {
            'id': str(task.id),
            'name': task.name,
            'description': task.description,
            'sample_ids': task.sample_ids,
            'annotation_type': task.annotation_type.value,
            'instructions': task.instructions,
            'status': task.status.value,
            'created_by': task.created_by,
            'created_at': task.created_at.isoformat(),
            'assigned_to': task.assigned_to,
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'progress': {
                'total': task.progress_total,
                'completed': task.progress_completed,
                'in_progress': task.progress_in_progress,
                'percentage': round(
                    (task.progress_completed / task.progress_total * 100) 
                    if task.progress_total > 0 else 0.0,
                    2
                )
            },
            'annotations': task.annotations,
            'metadata': task.metadata_
        }
