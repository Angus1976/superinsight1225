"""
Tasks API endpoints for SuperInsight Platform.
Handles task management, assignment, and progress tracking.
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.api.auth import get_current_user
from src.database.models import TaskModel, TaskStatus
from src.database.task_extensions import TaskPriority, AnnotationType, TaskAdapter
from src.security.models import UserModel
from src.api.label_studio_sync import label_studio_sync_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

# In-memory storage for development (will be replaced with database later)
_tasks_storage: Dict[str, Dict[str, Any]] = {}


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
    # Label Studio sync tracking fields
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
def get_task_or_404(task_id: str, db: Session, user: UserModel) -> Dict[str, Any]:
    """Get task by ID or raise 404 if not found or no access."""
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )
    
    # Check in-memory storage first
    if task_id in _tasks_storage:
        return _tasks_storage[task_id]
    
    # Fall back to mock data
    mock_tasks = TaskAdapter.create_mock_tasks(10)
    for task in mock_tasks:
        if task["id"] == task_id:
            return task
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Task not found"
    )


def task_to_response(task: Dict[str, Any]) -> TaskResponse:
    """Convert task dict to TaskResponse."""
    return TaskResponse(**task)


# Task endpoints
@router.get("", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assignee_id: Optional[str] = Query(None, description="Filter by assignee"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get list of tasks with pagination and filtering."""
    try:
        # Combine in-memory tasks with mock data
        all_tasks = list(_tasks_storage.values()) + TaskAdapter.create_mock_tasks(20)
        
        # Apply filters
        filtered_tasks = all_tasks
        if status:
            filtered_tasks = [t for t in filtered_tasks if t["status"] == status]
        if priority:
            filtered_tasks = [t for t in filtered_tasks if t["priority"] == priority]
        if assignee_id:
            filtered_tasks = [t for t in filtered_tasks if t["assignee_id"] == assignee_id]
        if search:
            search_lower = search.lower()
            filtered_tasks = [
                t for t in filtered_tasks 
                if search_lower in t["name"].lower() or 
                (t["description"] and search_lower in t["description"].lower())
            ]
        
        # Apply pagination
        total = len(filtered_tasks)
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_tasks = filtered_tasks[start_idx:end_idx]
        
        # Convert to response format
        task_responses = [task_to_response(task) for task in paginated_tasks]
        
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


async def _sync_task_to_label_studio(task_id: str, task_data: Dict[str, Any]):
    """
    Background task to sync task to Label Studio.
    
    This runs asynchronously after task creation to avoid blocking the API response.
    """
    try:
        logger.info(f"Starting Label Studio sync for task {task_id}")
        
        # Create Label Studio project
        sync_result = await label_studio_sync_service.create_project_for_task(
            task_id=task_id,
            task_name=task_data["name"],
            task_description=task_data.get("description"),
            annotation_type=task_data["annotation_type"]
        )
        
        # Update task with sync result
        if task_id in _tasks_storage:
            _tasks_storage[task_id].update({
                "label_studio_project_id": sync_result.get("project_id"),
                "label_studio_sync_status": sync_result["sync_status"],
                "label_studio_last_sync": sync_result["synced_at"],
                "label_studio_project_created_at": sync_result["synced_at"] if sync_result["success"] else None,
            })
            
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
        
    except Exception as e:
        logger.error(f"Error in background sync for task {task_id}: {str(e)}")
        # Update task with error status
        if task_id in _tasks_storage:
            _tasks_storage[task_id].update({
                "label_studio_sync_status": "failed",
                "label_studio_last_sync": datetime.utcnow().isoformat() + "Z",
            })


@router.post("", response_model=TaskResponse)
async def create_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new task and sync to Label Studio."""
    try:
        # Create new task
        task_id = str(uuid4())
        new_task = {
            "id": task_id,
            "name": request.name,
            "description": request.description,
            "status": "pending",
            "priority": request.priority,
            "annotation_type": request.annotation_type,
            "assignee_id": request.assignee_id,
            "assignee_name": None,  # Would be populated from DB lookup
            "created_by": current_user.username,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "due_date": request.due_date,
            "progress": 0,
            "total_items": request.total_items,
            "completed_items": 0,
            "tenant_id": current_user.tenant_id,
            "label_studio_project_id": None,
            # Label Studio sync tracking fields
            "label_studio_project_created_at": None,
            "label_studio_sync_status": "pending",
            "label_studio_last_sync": None,
            "label_studio_task_count": 0,
            "label_studio_annotation_count": 0,
            "tags": request.tags or [],
            "data_source": request.data_source.dict() if request.data_source else None
        }
        
        # Store in memory
        _tasks_storage[task_id] = new_task
        
        logger.info(f"Task created: {task_id} by {current_user.username}")
        
        # Schedule background sync to Label Studio
        background_tasks.add_task(_sync_task_to_label_studio, task_id, new_task)
        logger.info(f"Scheduled Label Studio sync for task {task_id}")
        
        return task_to_response(new_task)
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.get("/stats", response_model=TaskStatsResponse)
def get_task_stats(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get task statistics."""
    try:
        # Use mock data for stats
        all_tasks = TaskAdapter.create_mock_tasks(50)
        
        total = len(all_tasks)
        pending = len([t for t in all_tasks if t["status"] == "pending"])
        in_progress = len([t for t in all_tasks if t["status"] == "in_progress"])
        completed = len([t for t in all_tasks if t["status"] == "completed"])
        cancelled = len([t for t in all_tasks if t["status"] == "cancelled"])
        
        # Count overdue tasks
        now = datetime.utcnow()
        overdue = len([
            t for t in all_tasks 
            if t["due_date"] and t["due_date"] < now and t["status"] != "completed"
        ])
        
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
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get task by ID."""
    task = get_task_or_404(task_id, db, current_user)
    return task_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update task."""
    try:
        task = get_task_or_404(task_id, db, current_user)
        
        # Update fields
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            task[field] = value
        
        task["updated_at"] = datetime.utcnow()
        
        logger.info(f"Task updated: {task_id} by {current_user.username}")
        
        return task_to_response(task)
        
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete task."""
    try:
        task = get_task_or_404(task_id, db, current_user)
        
        # Remove from storage if it exists
        if task_id in _tasks_storage:
            del _tasks_storage[task_id]
        
        logger.info(f"Task deleted: {task_id} by {current_user.username}")
        
        return {"message": "Task deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )


@router.post("/batch/delete")
def batch_delete_tasks(
    task_ids: List[str],
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Delete multiple tasks."""
    try:
        # For mock implementation, just return success
        deleted_count = len(task_ids)
        
        logger.info(f"Batch deleted {deleted_count} tasks by {current_user.username}")
        
        return {"message": f"Successfully deleted {deleted_count} tasks"}
        
    except Exception as e:
        logger.error(f"Error batch deleting tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tasks"
        )


@router.post("/{task_id}/sync-label-studio")
async def sync_task_to_label_studio(
    task_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Manually sync a task to Label Studio.
    
    This endpoint can be used to:
    - Create a Label Studio project for a task that failed to sync
    - Re-sync a task after Label Studio configuration changes
    """
    try:
        # Get task
        task = get_task_or_404(task_id, db, current_user)
        
        # Check if already synced
        if task.get("label_studio_project_id") and task.get("label_studio_sync_status") == "synced":
            return {
                "message": "Task already synced to Label Studio",
                "project_id": task["label_studio_project_id"],
                "sync_status": "synced"
            }
        
        # Sync to Label Studio
        sync_result = await label_studio_sync_service.create_project_for_task(
            task_id=task_id,
            task_name=task["name"],
            task_description=task.get("description"),
            annotation_type=task["annotation_type"]
        )
        
        # Update task with sync result
        if task_id in _tasks_storage:
            _tasks_storage[task_id].update({
                "label_studio_project_id": sync_result.get("project_id"),
                "label_studio_sync_status": sync_result["sync_status"],
                "label_studio_last_sync": sync_result["synced_at"],
                "label_studio_project_created_at": sync_result["synced_at"] if sync_result["success"] else None,
            })
        
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
    current_user: UserModel = Depends(get_current_user)
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