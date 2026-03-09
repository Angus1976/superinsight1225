"""
Annotation Task API Router for Data Lifecycle Management.

Provides REST API endpoints for managing annotation tasks,
including task creation, annotator assignment, annotation submission,
progress tracking, and task completion.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 14.1, 14.2
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from src.database.connection import get_db_session
from src.services.annotation_task_service import (
    AnnotationTaskService,
    TaskConfig,
    Annotation,
    TaskProgress
)
from src.models.data_lifecycle import AnnotationType, TaskStatus


router = APIRouter(prefix="/api/annotation-tasks", tags=["Annotation Tasks"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class CreateTaskRequest(BaseModel):
    """Create annotation task request."""
    name: str = Field(..., min_length=1, description="Task name (required)")
    description: Optional[str] = Field(None, description="Task description")
    sample_ids: List[str] = Field(..., min_items=1, description="List of sample IDs to annotate")
    annotation_type: AnnotationType = Field(..., description="Type of annotation")
    instructions: str = Field(..., min_length=1, description="Annotation instructions (required)")
    deadline: Optional[datetime] = Field(None, description="Task deadline (must be future date)")
    assigned_to: Optional[List[str]] = Field(None, description="List of annotator user IDs")
    created_by: str = Field(..., description="User ID who is creating the task")


class TaskResponse(BaseModel):
    """Annotation task response."""
    id: UUID = Field(..., description="Task ID")
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    sample_ids: List[str] = Field(..., description="List of sample IDs")
    annotation_type: AnnotationType = Field(..., description="Annotation type")
    instructions: str = Field(..., description="Annotation instructions")
    status: TaskStatus = Field(..., description="Task status")
    created_by: str = Field(..., description="Creator user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    assigned_to: List[str] = Field(..., description="List of assigned annotator IDs")
    deadline: Optional[datetime] = Field(None, description="Task deadline")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    progress: Dict[str, Any] = Field(..., description="Task progress details")
    annotations: List[Dict[str, Any]] = Field(..., description="List of annotations")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")


class AssignAnnotatorRequest(BaseModel):
    """Assign annotator request."""
    annotator_id: str = Field(..., description="User ID of the annotator to assign")
    assigned_by: str = Field(..., description="User ID who is assigning the annotator")


class SubmitAnnotationRequest(BaseModel):
    """Submit annotation request."""
    sample_id: str = Field(..., description="Sample ID being annotated")
    annotator_id: str = Field(..., description="Annotator user ID")
    labels: List[Dict[str, Any]] = Field(..., min_items=1, description="Annotation labels (required)")
    comments: Optional[str] = Field(None, description="Optional annotation comments")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score (0-1)")


class AnnotationResultResponse(BaseModel):
    """Annotation submission result response."""
    annotation_id: UUID = Field(..., description="Annotation ID")
    task_id: UUID = Field(..., description="Task ID")
    sample_id: str = Field(..., description="Sample ID")
    annotator_id: str = Field(..., description="Annotator user ID")
    submitted_at: datetime = Field(..., description="Submission timestamp")


class TaskProgressResponse(BaseModel):
    """Task progress response."""
    total: int = Field(..., description="Total number of samples")
    completed: int = Field(..., description="Number of completed annotations")
    in_progress: int = Field(..., description="Number of in-progress annotations")
    percentage: float = Field(..., description="Completion percentage")


class CompleteTaskRequest(BaseModel):
    """Complete task request."""
    completed_by: str = Field(..., description="User ID who is completing the task")


class ListTasksResponse(BaseModel):
    """List tasks response."""
    items: List[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_annotation_task_service(db: DBSession = Depends(get_db_session)) -> AnnotationTaskService:
    """Get annotation task service instance."""
    return AnnotationTaskService(db)


# ============================================================================
# Helper Functions
# ============================================================================

def _task_dict_to_response(task_dict: Dict[str, Any]) -> TaskResponse:
    """Convert task dictionary to TaskResponse."""
    return TaskResponse(
        id=UUID(task_dict['id']),
        name=task_dict['name'],
        description=task_dict['description'],
        sample_ids=task_dict['sample_ids'],
        annotation_type=AnnotationType(task_dict['annotation_type']),
        instructions=task_dict['instructions'],
        status=TaskStatus(task_dict['status']),
        created_by=task_dict['created_by'],
        created_at=datetime.fromisoformat(task_dict['created_at']),
        assigned_to=task_dict['assigned_to'],
        deadline=datetime.fromisoformat(task_dict['deadline']) if task_dict['deadline'] else None,
        completed_at=datetime.fromisoformat(task_dict['completed_at']) if task_dict['completed_at'] else None,
        progress=task_dict['progress'],
        annotations=task_dict['annotations'],
        metadata=task_dict['metadata']
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_annotation_task(
    request: CreateTaskRequest,
    service: AnnotationTaskService = Depends(get_annotation_task_service)
):
    """
    Create a new annotation task from sample library data.
    
    Creates an annotation task with specified samples, annotation type,
    instructions, and optional deadline. Optionally assigns annotators.
    
    Validates: Requirements 5.1, 14.2
    
    Args:
        request: Create task request with name, samples, type, instructions, etc.
        service: Annotation task service instance
    
    Returns:
        TaskResponse with created task details
    
    Raises:
        HTTPException 400: If validation fails or samples not found
        HTTPException 500: If task creation fails
    """
    try:
        config = TaskConfig(
            name=request.name,
            description=request.description,
            sample_ids=request.sample_ids,
            annotation_type=request.annotation_type,
            instructions=request.instructions,
            deadline=request.deadline,
            assigned_to=request.assigned_to
        )
        
        task_dict = service.create_task(
            config=config,
            created_by=request.created_by
        )
        
        return _task_dict_to_response(task_dict)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create annotation task: {str(e)}"
        )


@router.put("/{task_id}/assign", status_code=status.HTTP_200_OK)
async def assign_annotator(
    task_id: UUID,
    request: AssignAnnotatorRequest,
    service: AnnotationTaskService = Depends(get_annotation_task_service)
):
    """
    Assign an annotator to a task.
    
    Adds an annotator to the task's assigned list. If the task status is CREATED,
    it will be transitioned to IN_PROGRESS.
    
    Validates: Requirements 5.2, 14.2
    
    Args:
        task_id: Task ID
        request: Assign annotator request with annotator ID and assigner ID
        service: Annotation task service instance
    
    Returns:
        Success message
    
    Raises:
        HTTPException 400: If task not found or in invalid state
        HTTPException 404: If task not found
        HTTPException 500: If assignment fails
    """
    try:
        service.assign_annotator(
            task_id=str(task_id),
            annotator_id=request.annotator_id,
            assigned_by=request.assigned_by
        )
        
        return {
            "message": "Annotator assigned successfully",
            "task_id": str(task_id),
            "annotator_id": request.annotator_id
        }
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign annotator: {str(e)}"
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_details(
    task_id: UUID,
    service: AnnotationTaskService = Depends(get_annotation_task_service)
):
    """
    Get detailed information about a specific task.
    
    Returns complete task details including progress, annotations,
    assigned annotators, and metadata.
    
    Validates: Requirements 5.3, 14.1
    
    Args:
        task_id: Task ID
        service: Annotation task service instance
    
    Returns:
        TaskResponse with task details
    
    Raises:
        HTTPException 404: If task not found
        HTTPException 500: If retrieval fails
    """
    try:
        task_dict = service.get_task(str(task_id))
        
        return _task_dict_to_response(task_dict)
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task details: {str(e)}"
        )


@router.post("/{task_id}/annotations", response_model=AnnotationResultResponse, status_code=status.HTTP_201_CREATED)
async def submit_annotation(
    task_id: UUID,
    request: SubmitAnnotationRequest,
    service: AnnotationTaskService = Depends(get_annotation_task_service)
):
    """
    Submit an annotation for a sample in a task.
    
    Records annotation labels, comments, and confidence for a specific sample.
    Updates task progress automatically.
    
    Validates: Requirements 5.3, 14.2
    
    Args:
        task_id: Task ID
        request: Submit annotation request with sample ID, labels, etc.
        service: Annotation task service instance
    
    Returns:
        AnnotationResultResponse with submission details
    
    Raises:
        HTTPException 400: If validation fails or annotator not assigned
        HTTPException 404: If task not found
        HTTPException 500: If submission fails
    """
    try:
        annotation = Annotation(
            task_id=str(task_id),
            sample_id=request.sample_id,
            annotator_id=request.annotator_id,
            labels=request.labels,
            comments=request.comments,
            confidence=request.confidence
        )
        
        result = service.submit_annotation(annotation)
        
        return AnnotationResultResponse(
            annotation_id=UUID(result.annotation_id),
            task_id=UUID(result.task_id),
            sample_id=result.sample_id,
            annotator_id=result.annotator_id,
            submitted_at=result.submitted_at
        )
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit annotation: {str(e)}"
        )


@router.get("/{task_id}/progress", response_model=TaskProgressResponse)
async def get_task_progress(
    task_id: UUID,
    service: AnnotationTaskService = Depends(get_annotation_task_service)
):
    """
    Get current progress of a task.
    
    Returns progress statistics including total samples, completed annotations,
    in-progress annotations, and completion percentage.
    
    Validates: Requirements 5.4, 14.3
    
    Args:
        task_id: Task ID
        service: Annotation task service instance
    
    Returns:
        TaskProgressResponse with progress details
    
    Raises:
        HTTPException 404: If task not found
        HTTPException 500: If retrieval fails
    """
    try:
        progress = service.get_task_progress(str(task_id))
        
        return TaskProgressResponse(
            total=progress.total,
            completed=progress.completed,
            in_progress=progress.in_progress,
            percentage=progress.percentage
        )
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task progress: {str(e)}"
        )


@router.post("/{task_id}/complete", status_code=status.HTTP_200_OK)
async def complete_task(
    task_id: UUID,
    request: CompleteTaskRequest,
    service: AnnotationTaskService = Depends(get_annotation_task_service)
):
    """
    Mark a task as complete.
    
    Validates that all samples have been annotated before marking the task
    as complete. Transitions task status to COMPLETED.
    
    Validates: Requirements 5.5, 5.6, 14.2
    
    Args:
        task_id: Task ID
        request: Complete task request with completer user ID
        service: Annotation task service instance
    
    Returns:
        Success message with completion details
    
    Raises:
        HTTPException 400: If task not in valid state or not all samples annotated
        HTTPException 404: If task not found
        HTTPException 500: If completion fails
    """
    try:
        service.complete_task(
            task_id=str(task_id),
            completed_by=request.completed_by
        )
        
        return {
            "message": "Task completed successfully",
            "task_id": str(task_id),
            "completed_by": request.completed_by,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete task: {str(e)}"
        )


@router.get("", response_model=ListTasksResponse)
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    annotation_type: Optional[AnnotationType] = Query(None, description="Filter by annotation type"),
    created_by: Optional[str] = Query(None, description="Filter by creator user ID"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned annotator user ID"),
    service: AnnotationTaskService = Depends(get_annotation_task_service)
):
    """
    List annotation tasks with pagination and filters.
    
    Returns a paginated list of annotation tasks with optional filtering
    by status, annotation type, creator, or assigned annotator.
    
    Validates: Requirements 14.1, 14.2
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        status_filter: Filter by task status
        annotation_type: Filter by annotation type
        created_by: Filter by creator user ID
        assigned_to: Filter by assigned annotator user ID
        service: Annotation task service instance
    
    Returns:
        ListTasksResponse with paginated task list
    
    Raises:
        HTTPException 500: If listing fails
    """
    try:
        from src.models.data_lifecycle import AnnotationTaskModel
        
        # Build query
        query = service.db.query(AnnotationTaskModel)
        
        # Apply filters
        if status_filter:
            query = query.filter(AnnotationTaskModel.status == status_filter)
        if annotation_type:
            query = query.filter(AnnotationTaskModel.annotation_type == annotation_type)
        if created_by:
            query = query.filter(AnnotationTaskModel.created_by == created_by)
        if assigned_to:
            # Filter tasks where assigned_to array contains the user ID
            query = query.filter(AnnotationTaskModel.assigned_to.contains([assigned_to]))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        tasks = query.order_by(AnnotationTaskModel.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        # Convert to response models
        task_dicts = [service._task_to_dict(task) for task in tasks]
        response_items = [_task_dict_to_response(task_dict) for task_dict in task_dicts]
        
        return ListTasksResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
        )
