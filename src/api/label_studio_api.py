"""
Label Studio API endpoints for SuperInsight Platform.
Provides integration with Label Studio for project and task management.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.api.auth import get_current_user
from src.security.models import UserModel
from src.label_studio.integration import LabelStudioIntegration

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/label-studio", tags=["Label Studio"])


# Response models
class LabelStudioProject(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    task_count: int = 0
    annotation_count: int = 0
    
    class Config:
        from_attributes = True


class LabelStudioProjectList(BaseModel):
    projects: List[LabelStudioProject]
    total: int


class LabelStudioTask(BaseModel):
    id: int
    data: Dict[str, Any]
    annotations: List[Dict[str, Any]] = []
    predictions: List[Dict[str, Any]] = []
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class LabelStudioTaskList(BaseModel):
    tasks: List[LabelStudioTask]
    total: int


# Helper function to get Label Studio integration
def get_label_studio() -> LabelStudioIntegration:
    """Get Label Studio integration instance."""
    try:
        return LabelStudioIntegration()
    except Exception as e:
        logger.error(f"Failed to initialize Label Studio integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Label Studio service is not available"
        )


# Label Studio endpoints
@router.get("/projects", response_model=LabelStudioProjectList)
def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get list of Label Studio projects."""
    try:
        ls = get_label_studio()
        
        # Get projects from Label Studio
        projects_data = ls.list_projects()
        
        # Convert to response format
        projects = []
        for proj in projects_data:
            projects.append(LabelStudioProject(
                id=proj.get('id'),
                title=proj.get('title', 'Untitled Project'),
                description=proj.get('description'),
                created_at=proj.get('created_at', ''),
                updated_at=proj.get('updated_at', ''),
                task_count=proj.get('task_number', 0),
                annotation_count=proj.get('num_tasks_with_annotations', 0)
            ))
        
        # Apply pagination
        total = len(projects)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_projects = projects[start_idx:end_idx]
        
        return LabelStudioProjectList(
            projects=paginated_projects,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing Label Studio projects: {e}")
        # Return empty list instead of error for better UX
        return LabelStudioProjectList(projects=[], total=0)


@router.get("/projects/{project_id}")
def get_project(
    project_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get Label Studio project by ID."""
    try:
        ls = get_label_studio()
        project_data = ls.get_project(project_id)
        
        if not project_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        return LabelStudioProject(
            id=project_data.get('id'),
            title=project_data.get('title', 'Untitled Project'),
            description=project_data.get('description'),
            created_at=project_data.get('created_at', ''),
            updated_at=project_data.get('updated_at', ''),
            task_count=project_data.get('task_number', 0),
            annotation_count=project_data.get('num_tasks_with_annotations', 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Label Studio project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project"
        )


@router.get("/projects/{project_id}/tasks", response_model=LabelStudioTaskList)
def list_project_tasks(
    project_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get list of tasks for a Label Studio project."""
    try:
        ls = get_label_studio()
        
        # Get tasks from Label Studio
        tasks_data = ls.get_project_tasks(project_id)
        
        # Convert to response format
        tasks = []
        for task in tasks_data:
            tasks.append(LabelStudioTask(
                id=task.get('id'),
                data=task.get('data', {}),
                annotations=task.get('annotations', []),
                predictions=task.get('predictions', []),
                created_at=task.get('created_at', ''),
                updated_at=task.get('updated_at', '')
            ))
        
        # Apply pagination
        total = len(tasks)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tasks = tasks[start_idx:end_idx]
        
        return LabelStudioTaskList(
            tasks=paginated_tasks,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tasks for project {project_id}: {e}")
        # Return empty list instead of error for better UX
        return LabelStudioTaskList(tasks=[], total=0)


@router.get("/health")
def check_health(
    current_user: UserModel = Depends(get_current_user)
):
    """Check Label Studio service health."""
    try:
        ls = get_label_studio()
        # Try to list projects as a health check
        ls.list_projects()
        return {"status": "healthy", "message": "Label Studio is accessible"}
    except Exception as e:
        logger.error(f"Label Studio health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": "Label Studio is not accessible",
            "error": str(e)
        }
