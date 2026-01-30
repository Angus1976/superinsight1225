"""
Tasks API endpoints for SuperInsight Platform.
Handles task management, assignment, and progress tracking with full database persistence.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, func as sql_func

from src.database.connection import get_db_session
from src.api.auth_simple import get_current_user, SimpleUser
from src.database.models import TaskModel, TaskStatus, TaskPriority, AnnotationType, LabelStudioSyncStatus
from src.api.label_studio_sync import label_studio_sync_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


# Request/Response models
class DataSourceConfig(BaseModel):
    """Data source configuration for task"""
    type: str = Field(..., description="Data source type: file, api, or database")
    config: Dict[str, Any] = Field(default_factory=dict, description="Data source configuration")


class TaskCreateRequest(BaseModel):
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    annotation_type: str = Field("custom", description="Type of annotation")
    priority: str = Field("medium", description="Task priority")
    assignee_id: Optional[str] = Field(None, description="Assigned user ID")
    due_date: Optional[datetime] = Field(None, description="Due date")
    total_items: int = Field(1, description="Total items to annotate")
    tags: Optional[List[str]] = Field(None, description="Task tags")
    data_source: Optional[DataSourceConfig] = Field(None, description="Data source configuration")


class TaskUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    progress: Optional[int] = None
    completed_items: Optional[int] = None
    tags: Optional[List[str]] = None
    data_source: Optional[DataSourceConfig] = None


class TaskResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    priority: str
    annotation_type: str
    assignee_id: Optional[str]
    assignee_name: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime]
    progress: int
    total_items: int
    completed_items: int
    tenant_id: str
    label_studio_project_id: Optional[str]
    label_studio_project_created_at: Optional[datetime] = None
    label_studio_sync_status: Optional[str] = None
    label_studio_last_sync: Optional[datetime] = None
    label_studio_task_count: int = 0
    label_studio_annotation_count: int = 0
    tags: Optional[List[str]]
    data_source: Optional[DataSourceConfig] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: List[TaskResponse]
    total: int
    page: int
    size: int


class TaskStatsResponse(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    cancelled: int
    overdue: int


# Helper functions
def task_model_to_response(task: TaskModel) -> TaskResponse:
    """Convert TaskModel to TaskResponse."""
    return TaskResponse(
        id=str(task.id),
        name=task.name,
        description=task.description,
        status=task.status.value if hasattr(task.status, 'value') else str(task.status),
        priority=task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
        annotation_type=task.annotation_type.value if hasattr(task.annotation_type, 'value') else str(task.annotation_type),
        assignee_id=str(task.assignee_id) if task.assignee_id else None,
        assignee_name=task.assignee.username if task.assignee else None,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at or task.created_at,
        due_date=task.due_date,
        progress=task.progress or 0,
        total_items=task.total_items or 1,
        completed_items=task.completed_items or 0,
        tenant_id=task.tenant_id,
        label_studio_project_id=task.label_studio_project_id,
        label_studio_project_created_at=task.label_studio_project_created_at,
        label_studio_sync_status=task.label_studio_sync_status.value if task.label_studio_sync_status else None,
        label_studio_last_sync=task.label_studio_last_sync,
        label_studio_task_count=task.label_studio_task_count or 0,
        label_studio_annotation_count=task.label_studio_annotation_count or 0,
        tags=task.tags or [],
        data_source=task.task_metadata.get("data_source") if task.task_metadata else None
    )


def get_task_or_404(task_id: str, db: Session, tenant_id: str) -> TaskModel:
    """Get task by ID or raise 404 if not found or no access."""
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )

    task = db.query(TaskModel).filter(
        TaskModel.id == task_uuid,
        TaskModel.tenant_id == tenant_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


# Task endpoints
@router.get("", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assignee_id: Optional[str] = Query(None, description="Filter by assignee"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get list of tasks with pagination and filtering from database."""
    try:
        # Build base query with tenant filter
        query = db.query(TaskModel).filter(TaskModel.tenant_id == current_user.tenant_id)

        # Apply filters
        if status:
            query = query.filter(TaskModel.status == status)
        if priority:
            query = query.filter(TaskModel.priority == priority)
        if assignee_id:
            try:
                assignee_uuid = UUID(assignee_id)
                query = query.filter(TaskModel.assignee_id == assignee_uuid)
            except ValueError:
                pass
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    TaskModel.name.ilike(search_pattern),
                    TaskModel.description.ilike(search_pattern)
                )
            )

        # Count total before pagination
        total = query.count()

        # Apply ordering and pagination
        tasks = query.order_by(TaskModel.created_at.desc()) \
                     .offset((page - 1) * size) \
                     .limit(size) \
                     .all()

        # Convert to response format
        task_responses = [task_model_to_response(task) for task in tasks]

        return TaskListResponse(
            items=task_responses,
            total=total,
            page=page,
            size=size
        )

    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks"
        )


async def _sync_task_to_label_studio(task_id: str, db: Session, task_name: str, annotation_type: str, description: Optional[str] = None):
    """
    Background task to sync task to Label Studio.

    This runs asynchronously after task creation to avoid blocking the API response.
    """
    try:
        logger.info(f"Starting Label Studio sync for task {task_id}")

        # Create Label Studio project
        sync_result = await label_studio_sync_service.create_project_for_task(
            task_id=task_id,
            task_name=task_name,
            task_description=description,
            annotation_type=annotation_type
        )

        # Update task with sync result in database
        try:
            task_uuid = UUID(task_id)
            task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
            if task:
                task.label_studio_project_id = sync_result.get("project_id")
                task.label_studio_sync_status = LabelStudioSyncStatus.SYNCED if sync_result["success"] else LabelStudioSyncStatus.FAILED
                task.label_studio_last_sync = datetime.utcnow()
                if sync_result["success"]:
                    task.label_studio_project_created_at = datetime.utcnow()
                db.commit()

                if sync_result["success"]:
                    logger.info(
                        f"Successfully synced task {task_id} to Label Studio "
                        f"project {sync_result['project_id']}"
                    )
                else:
                    logger.error(
                        f"Failed to sync task {task_id} to Label Studio: "
                        f"{sync_result.get('error')}"
                    )
        except Exception as db_error:
            logger.error(f"Error updating task sync status in database: {db_error}")

    except Exception as e:
        logger.error(f"Error in background sync for task {task_id}: {str(e)}")
        # Update task with error status
        try:
            task_uuid = UUID(task_id)
            task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
            if task:
                task.label_studio_sync_status = LabelStudioSyncStatus.FAILED
                task.label_studio_last_sync = datetime.utcnow()
                db.commit()
        except Exception:
            pass


@router.post("", response_model=TaskResponse)
async def create_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new task and save to database."""
    try:
        # Parse assignee_id if provided
        assignee_uuid = None
        if request.assignee_id:
            try:
                assignee_uuid = UUID(request.assignee_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid assignee ID format"
                )

        # Parse priority and annotation_type enums
        try:
            priority = TaskPriority(request.priority)
        except ValueError:
            priority = TaskPriority.MEDIUM

        try:
            annotation_type = AnnotationType(request.annotation_type)
        except ValueError:
            annotation_type = AnnotationType.CUSTOM

        # Create task model
        task = TaskModel(
            id=uuid4(),
            name=request.name,
            description=request.description,
            status=TaskStatus.PENDING,
            priority=priority,
            annotation_type=annotation_type,
            assignee_id=assignee_uuid,
            created_by=current_user.username,
            tenant_id=current_user.tenant_id,
            project_id=f"project_{uuid4()}",
            due_date=request.due_date,
            total_items=request.total_items,
            progress=0,
            completed_items=0,
            tags=request.tags or [],
            task_metadata={"data_source": request.data_source.dict() if request.data_source else None},
            label_studio_sync_status=LabelStudioSyncStatus.PENDING
        )

        # Save to database
        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(f"Task created: {task.id} by {current_user.username}")

        # Schedule background sync to Label Studio
        background_tasks.add_task(
            _sync_task_to_label_studio,
            str(task.id),
            db,
            task.name,
            annotation_type.value,
            task.description
        )
        logger.info(f"Scheduled Label Studio sync for task {task.id}")

        return task_model_to_response(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.get("/stats", response_model=TaskStatsResponse)
def get_task_stats(
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get task statistics from database."""
    try:
        # Base query with tenant filter
        base_query = db.query(TaskModel).filter(TaskModel.tenant_id == current_user.tenant_id)

        # Count tasks by status
        total = base_query.count()
        pending = base_query.filter(TaskModel.status == TaskStatus.PENDING).count()
        in_progress = base_query.filter(TaskModel.status == TaskStatus.IN_PROGRESS).count()
        completed = base_query.filter(TaskModel.status == TaskStatus.COMPLETED).count()
        cancelled = base_query.filter(TaskModel.status == TaskStatus.CANCELLED).count()

        # Count overdue tasks (due_date < now and status not completed/cancelled)
        now = datetime.utcnow()
        overdue = base_query.filter(
            TaskModel.due_date < now,
            TaskModel.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED])
        ).count()

        return TaskStatsResponse(
            total=total,
            pending=pending,
            in_progress=in_progress,
            completed=completed,
            cancelled=cancelled,
            overdue=overdue
        )

    except Exception as e:
        logger.error(f"Error getting task stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task statistics"
        )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get task by ID from database."""
    task = get_task_or_404(task_id, db, current_user.tenant_id)
    return task_model_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update task in database."""
    try:
        task = get_task_or_404(task_id, db, current_user.tenant_id)

        # Update fields from request
        update_data = request.dict(exclude_unset=True)

        for field, value in update_data.items():
            if field == "status" and value:
                try:
                    task.status = TaskStatus(value)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status: {value}"
                    )
            elif field == "priority" and value:
                try:
                    task.priority = TaskPriority(value)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid priority: {value}"
                    )
            elif field == "assignee_id":
                if value:
                    try:
                        task.assignee_id = UUID(value)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid assignee ID format"
                        )
                else:
                    task.assignee_id = None
            elif field == "data_source":
                if task.task_metadata is None:
                    task.task_metadata = {}
                task.task_metadata["data_source"] = value
            elif hasattr(task, field):
                setattr(task, field, value)

        # Auto-calculate progress if completed_items changed
        if "completed_items" in update_data and task.total_items > 0:
            task.progress = int((task.completed_items / task.total_items) * 100)

        # Commit changes
        db.commit()
        db.refresh(task)

        logger.info(f"Task updated: {task_id} by {current_user.username}")

        return task_model_to_response(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete task from database."""
    try:
        task = get_task_or_404(task_id, db, current_user.tenant_id)

        # Delete from database
        db.delete(task)
        db.commit()

        logger.info(f"Task deleted: {task_id} by {current_user.username}")

        return {"message": "Task deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )


@router.post("/batch/delete")
def batch_delete_tasks(
    task_ids: List[str],
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete multiple tasks from database."""
    try:
        deleted_count = 0

        for task_id in task_ids:
            try:
                task_uuid = UUID(task_id)
                task = db.query(TaskModel).filter(
                    TaskModel.id == task_uuid,
                    TaskModel.tenant_id == current_user.tenant_id
                ).first()

                if task:
                    db.delete(task)
                    deleted_count += 1
            except ValueError:
                continue

        db.commit()

        logger.info(f"Batch deleted {deleted_count} tasks by {current_user.username}")

        return {"message": f"Successfully deleted {deleted_count} tasks"}

    except Exception as e:
        logger.error(f"Error batch deleting tasks: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tasks"
        )


@router.post("/{task_id}/sync-label-studio")
async def sync_task_to_label_studio(
    task_id: str,
    current_user: SimpleUser = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Manually sync a task to Label Studio.

    This endpoint can be used to:
    - Create a Label Studio project for a task that failed to sync
    - Re-sync a task after Label Studio configuration changes
    """
    try:
        task = get_task_or_404(task_id, db, current_user.tenant_id)

        # Check if already synced
        if task.label_studio_project_id and task.label_studio_sync_status == LabelStudioSyncStatus.SYNCED:
            return {
                "message": "Task already synced to Label Studio",
                "project_id": task.label_studio_project_id,
                "sync_status": "synced"
            }

        # Sync to Label Studio
        sync_result = await label_studio_sync_service.create_project_for_task(
            task_id=task_id,
            task_name=task.name,
            task_description=task.description,
            annotation_type=task.annotation_type.value if hasattr(task.annotation_type, 'value') else str(task.annotation_type)
        )

        # Update task with sync result
        task.label_studio_project_id = sync_result.get("project_id")
        task.label_studio_sync_status = LabelStudioSyncStatus.SYNCED if sync_result["success"] else LabelStudioSyncStatus.FAILED
        task.label_studio_last_sync = datetime.utcnow()
        if sync_result["success"]:
            task.label_studio_project_created_at = datetime.utcnow()

        db.commit()

        if sync_result["success"]:
            return {
                "message": "Task successfully synced to Label Studio",
                "project_id": sync_result["project_id"],
                "project_url": sync_result["project_url"],
                "sync_status": sync_result["sync_status"],
                "synced_at": sync_result["synced_at"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync task: {sync_result.get('error')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing task {task_id} to Label Studio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync task: {str(e)}"
        )


@router.get("/label-studio/test-connection")
async def test_label_studio_connection(
    current_user: SimpleUser = Depends(get_current_user)
):
    """
    Test Label Studio connection and authentication.

    This endpoint can be used to verify that:
    - Label Studio is accessible
    - Authentication credentials are valid
    - API token has proper permissions
    """
    try:
        result = await label_studio_sync_service.test_connection()

        if result["connected"]:
            return {
                "status": "success",
                "message": "Successfully connected to Label Studio",
                "details": result
            }
        else:
            return {
                "status": "error",
                "message": "Failed to connect to Label Studio",
                "details": result
            }

    except Exception as e:
        logger.error(f"Error testing Label Studio connection: {e}")
        return {
            "status": "error",
            "message": f"Error testing connection: {str(e)}",
            "details": {
                "connected": False,
                "authenticated": False,
                "error": str(e)
            }
        }
