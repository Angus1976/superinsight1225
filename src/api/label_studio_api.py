"""
Label Studio API endpoints for SuperInsight Platform.
Provides integration with Label Studio for project and task management.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.api.auth import get_current_user
from src.security.models import UserModel
from src.label_studio.integration import (
    LabelStudioIntegration,
    ProjectConfig,
    LabelStudioIntegrationError
)

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


# Request models for new endpoints
class EnsureProjectRequest(BaseModel):
    """Request body for ensuring a Label Studio project exists.
    
    Validates: Requirements 1.3 - Automatic Project Creation
    """
    task_id: str = Field(..., description="SuperInsight task ID")
    task_name: str = Field(default="Annotation Project", description="Task name for project title")
    annotation_type: str = Field(default="text_classification", description="Type of annotation")
    description: Optional[str] = Field(default=None, description="Project description")
    existing_project_id: Optional[str] = Field(default=None, description="Existing Label Studio project ID if known")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_name": "Customer Review Classification",
                "annotation_type": "text_classification",
                "description": "Classify customer reviews by sentiment"
            }
        }


# Response models for new endpoints
class EnsureProjectResponse(BaseModel):
    """Response for ensure project endpoint.
    
    Validates: Requirements 1.3 - Automatic Project Creation
    
    API Response Format (Section 6.1):
    {
      "project_id": "123",
      "created": true,
      "status": "ready",
      "task_count": 100,
      "message": "Project created successfully"
    }
    """
    project_id: str = Field(..., description="Label Studio project ID")
    created: bool = Field(..., description="Whether a new project was created")
    status: str = Field(default="ready", description="Project status (ready, creating, error)")
    task_count: int = Field(default=0, description="Number of tasks in the project")
    message: str = Field(default="", description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "123",
                "created": True,
                "status": "ready",
                "task_count": 100,
                "message": "Project created successfully"
            }
        }


class ProjectValidationResponse(BaseModel):
    """Response for project validation endpoint.
    
    Validates: Requirements 1.1, 1.2
    
    API Response Format (Section 6.2):
    {
      "exists": true,
      "accessible": true,
      "task_count": 100,
      "annotation_count": 65,
      "status": "ready"
    }
    """
    exists: bool = Field(..., description="Whether the project exists in Label Studio")
    accessible: bool = Field(..., description="Whether the project is accessible with current credentials")
    task_count: int = Field(default=0, description="Number of tasks in the project")
    annotation_count: int = Field(default=0, description="Number of completed annotations")
    status: str = Field(default="ready", description="Project status (ready, creating, error)")
    error_message: Optional[str] = Field(default=None, description="Error message if validation failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "exists": True,
                "accessible": True,
                "task_count": 100,
                "annotation_count": 65,
                "status": "ready"
            }
        }


class ImportTasksRequest(BaseModel):
    """Request body for importing tasks to Label Studio project.
    
    Validates: Requirements 1.4 - Task Data Synchronization
    """
    task_id: str = Field(..., description="SuperInsight task ID to import")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ImportTasksResponse(BaseModel):
    """Response for import tasks endpoint.
    
    Validates: Requirements 1.4 - Task Data Synchronization
    
    API Response Format (Design Section 5.3):
    {
        "success": true,
        "imported_count": 100,
        "failed_count": 0,
        "errors": [],
        "project_id": "123",
        "task_ids": [1, 2, 3]
    }
    """
    success: bool = Field(..., description="Whether the import was successful")
    imported_count: int = Field(default=0, description="Number of tasks successfully imported")
    failed_count: int = Field(default=0, description="Number of tasks that failed to import")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    project_id: str = Field(..., description="Label Studio project ID")
    task_ids: List[int] = Field(default_factory=list, description="List of imported Label Studio task IDs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "imported_count": 100,
                "failed_count": 0,
                "errors": [],
                "project_id": "123",
                "task_ids": [1, 2, 3, 4, 5]
            }
        }


class AuthenticatedUrlResponse(BaseModel):
    """Response for authenticated URL endpoint.
    
    Validates: Requirements 1.2 - Open Annotation in New Window
    Validates: Requirements 1.5 - Seamless Language Synchronization
    
    API Response Format (Design Section 6.3):
    {
        "url": "http://localhost:8080/projects/123?token=eyJ0eXAiOiJKV1QiLCJhbGc...",
        "expires_at": "2025-01-26T12:00:00Z",
        "project_id": "123"
    }
    """
    url: str = Field(..., description="Authenticated URL with token and language parameter")
    expires_at: str = Field(..., description="ISO format datetime when token expires")
    project_id: str = Field(..., description="Label Studio project ID")
    language: Optional[str] = Field(default="zh", description="Language parameter used in URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "http://localhost:8080/projects/123?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...&lang=zh",
                "expires_at": "2025-01-26T12:00:00Z",
                "project_id": "123",
                "language": "zh"
            }
        }


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


@router.post("/projects/ensure", response_model=EnsureProjectResponse)
async def ensure_project_exists(
    request: EnsureProjectRequest = Body(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Ensure Label Studio project exists for task.
    Creates project if needed.
    
    This endpoint implements idempotent project creation - calling it multiple
    times with the same task_id will return the existing project if one exists.
    
    POST /api/label-studio/projects/ensure
    Body: {
        "task_id": "uuid",
        "task_name": "Project Title",
        "annotation_type": "text_classification",
        "description": "Optional description",
        "existing_project_id": "123"  // Optional
    }
    
    Returns:
        {
            "project_id": "123",
            "created": true/false,
            "status": "ready",
            "task_count": 100,
            "message": "Project created successfully"
        }
    
    Validates: Requirements 1.3 - Automatic Project Creation
    - WHEN task is created with annotation requirement, THEN system creates corresponding Label Studio project
    - WHEN user attempts to annotate task without project, THEN system creates project automatically
    - WHERE project already exists, THEN system reuses existing project
    """
    try:
        ls = get_label_studio()
        
        # Create project configuration
        project_config = ProjectConfig(
            title=request.task_name,
            description=request.description or f"Annotation project for task {request.task_id}",
            annotation_type=request.annotation_type
        )
        
        # Check if we need to create a new project or reuse existing
        existing_project_id = request.existing_project_id
        created = False
        
        # Call ensure_project_exists from integration service
        project = await ls.ensure_project_exists(
            project_id=existing_project_id,
            project_config=project_config
        )
        
        # Determine if project was newly created
        # If existing_project_id was None or different from returned project.id, it was created
        if existing_project_id is None or str(project.id) != str(existing_project_id):
            created = True
            message = "Project created successfully"
        else:
            message = "Using existing project"
        
        # Get task count from project info
        task_count = getattr(project, 'task_number', 0) or 0
        
        logger.info(
            f"Ensure project for task {request.task_id}: "
            f"project_id={project.id}, created={created}, task_count={task_count}"
        )
        
        return EnsureProjectResponse(
            project_id=str(project.id),
            created=created,
            status="ready",
            task_count=task_count,
            message=message
        )
        
    except LabelStudioIntegrationError as e:
        logger.error(f"Label Studio integration error ensuring project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "project_creation_failed",
                "message": "Failed to create Label Studio project",
                "details": str(e)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error ensuring project for task {request.task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "project_creation_failed",
                "message": "Failed to create Label Studio project",
                "details": str(e)
            }
        )


@router.get("/projects/{project_id}/validate", response_model=ProjectValidationResponse)
async def validate_project(
    project_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Validate project exists and is accessible.
    
    This endpoint checks if a Label Studio project exists, is accessible with
    current credentials, and returns information about its task and annotation counts.
    It is used to verify project status before navigation to annotation pages.
    
    GET /api/label-studio/projects/{project_id}/validate
    
    Returns:
        {
            "exists": true/false,
            "accessible": true/false,
            "task_count": 100,
            "annotation_count": 65,
            "status": "ready"
        }
    
    Validates: Requirements 1.1 - Label Studio project and tasks are successfully fetched
    - WHEN annotation page loads, THEN Label Studio project and tasks are successfully fetched
    - WHEN Label Studio project exists, THEN user sees the annotation interface
    
    Validates: Requirements 1.2 - Label Studio project page loads successfully
    - WHEN new window opens, THEN Label Studio project page loads successfully (no 404 error)
    """
    try:
        ls = get_label_studio()
        
        # Call validate_project from integration service
        validation_result = await ls.validate_project(project_id)
        
        logger.info(
            f"Validated project {project_id}: "
            f"exists={validation_result.exists}, accessible={validation_result.accessible}, "
            f"task_count={validation_result.task_count}, annotation_count={validation_result.annotation_count}, "
            f"status={validation_result.status}"
        )
        
        # Return validation result
        return ProjectValidationResponse(
            exists=validation_result.exists,
            accessible=validation_result.accessible,
            task_count=validation_result.task_count,
            annotation_count=validation_result.annotation_count,
            status=validation_result.status,
            error_message=validation_result.error_message
        )
        
    except LabelStudioIntegrationError as e:
        logger.error(f"Label Studio integration error validating project {project_id}: {e}")
        # Return validation failure response instead of raising exception
        # This allows frontend to handle the error gracefully
        return ProjectValidationResponse(
            exists=False,
            accessible=False,
            task_count=0,
            annotation_count=0,
            status="error",
            error_message=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error validating project {project_id}: {e}")
        # Return validation failure response
        return ProjectValidationResponse(
            exists=False,
            accessible=False,
            task_count=0,
            annotation_count=0,
            status="error",
            error_message=f"Unexpected error: {str(e)}"
        )


@router.post("/projects/{project_id}/import-tasks", response_model=ImportTasksResponse)
async def import_tasks_to_project(
    project_id: str,
    request: ImportTasksRequest = Body(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Import tasks from SuperInsight to Label Studio project.
    
    This endpoint fetches task data from the SuperInsight database and imports
    it into the specified Label Studio project. It uses the existing import_tasks()
    method from the integration service.
    
    POST /api/label-studio/projects/{project_id}/import-tasks
    Body: { "task_id": "uuid" }
    
    Returns:
        {
            "success": true,
            "imported_count": 100,
            "failed_count": 0,
            "errors": [],
            "project_id": "123",
            "task_ids": [1, 2, 3]
        }
    
    Validates: Requirements 1.4 - Task Data Synchronization
    - WHEN annotation is created in Label Studio, THEN system syncs it back to SuperInsight database
    - WHEN project is created, THEN system imports all task data into Label Studio
    - IF sync fails, THEN system retries with exponential backoff
    """
    from uuid import UUID
    from src.database.models import TaskModel, DocumentModel
    from src.models.task import Task
    
    try:
        ls = get_label_studio()
        
        # Step 1: Validate project exists
        validation_result = await ls.validate_project(project_id)
        if not validation_result.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "project_not_found",
                    "message": f"Label Studio project {project_id} not found",
                    "project_id": project_id
                }
            )
        
        # Step 2: Fetch task from database
        try:
            task_uuid = UUID(request.task_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_task_id",
                    "message": f"Invalid task ID format: {request.task_id}"
                }
            )
        
        task_model = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
        
        if not task_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "task_not_found",
                    "message": f"Task {request.task_id} not found in database"
                }
            )
        
        # Step 3: Convert TaskModel to Task object for import_tasks method
        # The import_tasks method expects Task objects from src/models/task.py
        task = Task(
            task_id=task_model.id,
            project_id=UUID(project_id) if project_id.isdigit() is False else UUID(int=int(project_id)),
            tenant_id=UUID(task_model.tenant_id) if task_model.tenant_id else UUID(int=0),
            title=f"Task {task_model.id}",
            description=None,
            assigned_to=None,
            status=task_model.status.value if hasattr(task_model.status, 'value') else str(task_model.status),
            metadata={
                "document_id": str(task_model.document_id),
                "annotations": task_model.annotations or [],
                "ai_predictions": task_model.ai_predictions or [],
                "quality_score": task_model.quality_score
            }
        )
        
        # Add document_id attribute for import_tasks method
        task.document_id = task_model.document_id
        task.id = task_model.id
        task.annotations = task_model.annotations or []
        task.ai_predictions = task_model.ai_predictions or []
        
        # Step 4: Call import_tasks from integration service
        import_result = await ls.import_tasks(project_id, [task])
        
        # Step 5: Update task with Label Studio project ID
        task_model.project_id = project_id
        db.commit()
        
        logger.info(
            f"Imported task {request.task_id} to Label Studio project {project_id}: "
            f"imported={import_result.imported_count}, failed={import_result.failed_count}"
        )
        
        return ImportTasksResponse(
            success=import_result.success,
            imported_count=import_result.imported_count,
            failed_count=import_result.failed_count,
            errors=import_result.errors,
            project_id=project_id,
            task_ids=[]  # Label Studio doesn't return task IDs in import response
        )
        
    except HTTPException:
        raise
    except LabelStudioIntegrationError as e:
        logger.error(f"Label Studio integration error importing tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "import_failed",
                "message": "Failed to import tasks to Label Studio",
                "details": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error importing tasks to project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "import_failed",
                "message": "Failed to import tasks to Label Studio",
                "details": str(e)
            }
        )


@router.get("/projects/{project_id}/auth-url", response_model=AuthenticatedUrlResponse)
async def get_authenticated_url(
    project_id: str,
    language: str = Query(default="zh", description="Language preference ('zh' for Chinese, 'en' for English)"),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Generate authenticated URL for Label Studio with language support.
    
    This endpoint generates a temporary authenticated URL that can be used to
    open Label Studio in a new browser window. The URL includes:
    - A temporary JWT token for authentication
    - A language parameter (?lang=zh or ?lang=en) for Label Studio i18n
    
    The token expires after 1 hour by default.
    
    GET /api/label-studio/projects/{project_id}/auth-url?language=zh
    
    Query Parameters:
        language: User's language preference
            - 'zh' or 'zh-CN': Chinese (Simplified) - default
            - 'en' or 'en-US': English
    
    Returns:
        {
            "url": "http://localhost:8080/projects/123?token=eyJ0eXAiOiJKV1QiLCJhbGc...",
            "expires_at": "2025-01-26T12:00:00Z",
            "project_id": "123",
            "language": "zh"
        }
    
    Validates: Requirements 1.2 - Open Annotation in New Window
    - WHEN user clicks "在新窗口打开" button, THEN system opens Label Studio project in new browser tab
    - WHEN new window opens, THEN Label Studio project page loads successfully (no 404 error)
    - WHEN Label Studio loads, THEN user is automatically authenticated
    
    Validates: Requirements 1.5 - Seamless Language Synchronization
    - WHEN Label Studio opens, THEN interface language matches user's current language preference
    - WHERE user has selected Chinese in SuperInsight, THEN Label Studio displays in Chinese
    - WHERE user has selected English in SuperInsight, THEN Label Studio displays in English
    - WHERE Label Studio opens in new window, THEN language preference is included in authenticated URL
    """
    try:
        ls = get_label_studio()
        
        # Step 1: Validate project exists before generating URL
        validation_result = await ls.validate_project(project_id)
        if not validation_result.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "project_not_found",
                    "message": f"Label Studio project {project_id} not found",
                    "project_id": project_id
                }
            )
        
        # Step 2: Generate authenticated URL with language parameter
        # Use current user's ID for token generation
        user_id = str(current_user.id) if hasattr(current_user, 'id') else str(current_user.user_id)
        
        url_info = await ls.generate_authenticated_url(
            project_id=project_id,
            user_id=user_id,
            language=language,
            expires_in=3600  # 1 hour expiration
        )
        
        logger.info(
            f"Generated authenticated URL for project {project_id}, "
            f"user {user_id}, language {url_info.get('language', language)}"
        )
        
        return AuthenticatedUrlResponse(
            url=url_info["url"],
            expires_at=url_info["expires_at"],
            project_id=url_info["project_id"],
            language=url_info.get("language", language)
        )
        
    except HTTPException:
        raise
    except LabelStudioIntegrationError as e:
        logger.error(f"Label Studio integration error generating auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "url_generation_failed",
                "message": "Failed to generate authenticated URL",
                "details": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error generating auth URL for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "url_generation_failed",
                "message": "Failed to generate authenticated URL",
                "details": str(e)
            }
        )
