"""
Label Studio Integration Module

Provides comprehensive integration with Label Studio for project management,
task import/export, webhook configuration, and PostgreSQL synchronization.

Validates: Requirements 1.5 - Error handling with retry for network errors, timeouts
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import httpx
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.label_studio.config import LabelStudioConfig, LabelStudioProject
from src.label_studio.jwt_auth import JWTAuthManager
from src.label_studio.exceptions import (
    LabelStudioIntegrationError,
    LabelStudioAuthenticationError,
    LabelStudioProjectNotFoundError,
    LabelStudioNetworkError,
    LabelStudioTokenExpiredError,
)
from src.label_studio.retry import (
    label_studio_retry,
    LabelStudioRetryConfig,
    LABEL_STUDIO_RETRYABLE_EXCEPTIONS,
)
from src.database.connection import get_db_session
from src.database.models import TaskModel, DocumentModel
from src.models.task import Task, TaskStatus
from src.models.document import Document
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ProjectConfig:
    """Project configuration for Label Studio"""
    
    def __init__(self, 
                 title: str,
                 description: str = "",
                 annotation_type: str = "text_classification",
                 label_config: Optional[str] = None):
        self.title = title
        self.description = description
        self.annotation_type = annotation_type
        self.label_config = label_config


class ImportResult:
    """Result of task import operation"""
    
    def __init__(self, 
                 success: bool,
                 imported_count: int = 0,
                 failed_count: int = 0,
                 errors: List[str] = None):
        self.success = success
        self.imported_count = imported_count
        self.failed_count = failed_count
        self.errors = errors or []


class ExportResult:
    """Result of annotation export operation"""
    
    def __init__(self,
                 success: bool,
                 exported_count: int = 0,
                 data: List[Dict[str, Any]] = None,
                 errors: List[str] = None):
        self.success = success
        self.exported_count = exported_count
        self.data = data or []
        self.errors = errors or []


class ProjectValidationResult:
    """
    Result of project validation.
    
    This class represents the validation status of a Label Studio project,
    including whether it exists, is accessible, and contains tasks/annotations.
    
    Attributes:
        exists: Whether the project exists in Label Studio
        accessible: Whether the project is accessible with current credentials
        task_count: Number of tasks in the project
        annotation_count: Number of completed annotations
        status: Project status ('ready', 'creating', 'error')
        error_message: Optional error message if validation failed
        
    Validates: Requirements 1.1, 1.2
    """
    
    def __init__(
        self,
        exists: bool,
        accessible: bool,
        task_count: int = 0,
        annotation_count: int = 0,
        status: str = "ready",
        error_message: Optional[str] = None
    ):
        self.exists = exists
        self.accessible = accessible
        self.task_count = task_count
        self.annotation_count = annotation_count
        self.status = status
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "exists": self.exists,
            "accessible": self.accessible,
            "task_count": self.task_count,
            "annotation_count": self.annotation_count,
            "status": self.status,
            "error_message": self.error_message
        }
    
    def __repr__(self) -> str:
        return (
            f"ProjectValidationResult(exists={self.exists}, accessible={self.accessible}, "
            f"task_count={self.task_count}, annotation_count={self.annotation_count}, "
            f"status='{self.status}', error_message={self.error_message!r})"
        )


class LabelStudioIntegration:
    """
    Main integration class for Label Studio operations.
    
    Handles project creation, task management, webhook configuration,
    and data synchronization with PostgreSQL.
    
    Supports both JWT authentication (Label Studio 1.22.0+) and legacy
    API token authentication. JWT is preferred when both username and
    password are configured.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4 - Backward compatibility with API token
    """
    
    def __init__(self, config: Optional[LabelStudioConfig] = None):
        """
        Initialize Label Studio integration with configuration.
        
        Detects authentication method from config and initializes the
        appropriate auth manager. JWT authentication is preferred when
        both username and password are configured.
        
        Args:
            config: Optional LabelStudioConfig. If not provided, creates
                   a new config from environment variables.
                   
        Raises:
            LabelStudioIntegrationError: If configuration is invalid
            
        Validates: Requirements 3.1, 3.2 - Detect auth method from config
        """
        self.config = config or LabelStudioConfig()
        self.base_url = self.config.base_url.rstrip('/')
        self.api_token = self.config.api_token
        
        # Initialize JWT auth manager if JWT credentials are configured
        # JWT authentication is preferred over API token when both are available
        self._jwt_auth_manager: Optional[JWTAuthManager] = None
        self._auth_method: str = 'api_token'  # Default to API token
        
        try:
            auth_method = self.config.get_auth_method()
            self._auth_method = auth_method
            
            if auth_method == 'jwt':
                # Initialize JWT auth manager
                self._jwt_auth_manager = JWTAuthManager(
                    base_url=self.base_url,
                    username=self.config.username,
                    password=self.config.password
                )
                logger.info("Label Studio integration initialized with JWT authentication")
            else:
                logger.info("Label Studio integration initialized with API token authentication")
        except Exception as e:
            # If auth method detection fails, fall back to API token if available
            if self.api_token:
                logger.warning(f"Auth method detection failed ({e}), falling back to API token")
                self._auth_method = 'api_token'
            else:
                raise LabelStudioIntegrationError(f"No valid authentication method available: {e}")
        
        # Legacy headers for backward compatibility (used when JWT is not available)
        self.headers = {
            'Authorization': f'Token {self.api_token}' if self.api_token else '',
            'Content-Type': 'application/json'
        }
        
        # Validate configuration
        if not self.config.validate_config():
            raise LabelStudioIntegrationError("Invalid Label Studio configuration")
    
    async def _get_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        For JWT authentication, this method ensures the token is valid
        (refreshing if necessary) and returns Bearer token headers.
        For API token authentication, returns Token headers.
        
        This method is async because JWT authentication may require
        token refresh which involves network calls.
        
        Returns:
            Dict[str, str]: Headers dictionary with Authorization and Content-Type
            
        Raises:
            LabelStudioAuthenticationError: If authentication fails
            
        Validates: Requirements 1.4, 3.3 - Return appropriate auth header format
        """
        if self._auth_method == 'jwt' and self._jwt_auth_manager:
            # Ensure JWT token is valid (refresh if needed)
            await self._jwt_auth_manager._ensure_authenticated()
            
            # Get JWT auth header
            jwt_headers = self._jwt_auth_manager.get_auth_header()
            jwt_headers['Content-Type'] = 'application/json'
            return jwt_headers
        else:
            # Use legacy API token headers
            return self.headers
    
    def _check_https_security(self) -> bool:
        """
        Check if the Label Studio URL uses HTTPS for secure token transmission.
        
        This method verifies that the base URL uses HTTPS protocol when
        tokens will be transmitted. In production environments, using HTTP
        with tokens is a security risk as tokens may be intercepted.
        
        Returns:
            bool: True if URL uses HTTPS, False if HTTP
            
        Side Effects:
            Logs a warning if HTTP is used in non-development environments
            
        Validates: Requirements 10.3 - HTTPS enforcement for token URLs
        
        Example:
            >>> integration = LabelStudioIntegration()
            >>> is_secure = integration._check_https_security()
            >>> if not is_secure:
            ...     print("Warning: Using HTTP for token transmission")
        """
        is_https = self.base_url.startswith('https://')
        
        if not is_https:
            # Check if we're in development mode
            is_development = getattr(settings, 'is_development', False) or \
                             getattr(settings, 'debug', False) or \
                             'localhost' in self.base_url or \
                             '127.0.0.1' in self.base_url
            
            if not is_development:
                logger.warning(
                    "[Label Studio] SECURITY WARNING: Label Studio URL does not use HTTPS. "
                    "Tokens transmitted over HTTP may be intercepted. "
                    "Please configure LABEL_STUDIO_URL with an HTTPS URL for production use. "
                    f"Current URL: {self.base_url}"
                )
            else:
                logger.debug(
                    "[Label Studio] Using HTTP for Label Studio URL in development mode. "
                    "This is acceptable for local development but should use HTTPS in production."
                )
        
        return is_https
    
    def _is_token_expired_response(self, response: httpx.Response) -> bool:
        """
        Check if an HTTP response indicates token expiration.
        
        This method examines a 401 response to determine if it's due to
        token expiration (which can be recovered by refreshing the token)
        versus invalid credentials (which cannot be recovered).
        
        Label Studio may return various messages indicating token expiration:
        - "Token has expired"
        - "token expired"
        - "Signature has expired"
        - "Token is expired"
        - "JWT expired"
        
        Args:
            response: The HTTP response to check
            
        Returns:
            bool: True if the response indicates token expiration,
                  False otherwise
                  
        Validates: Requirements 5.3, 8.1 - Detect token expiration from 401 response
        """
        if response.status_code != 401:
            return False
        
        # Try to parse the response body for expiration indicators
        try:
            response_text = response.text.lower()
            
            # Common token expiration messages from Label Studio and JWT libraries
            expiration_indicators = [
                "token has expired",
                "token expired",
                "signature has expired",
                "token is expired",
                "jwt expired",
                "expired token",
                "access token expired",
                "token_expired",
                "exp claim",
            ]
            
            for indicator in expiration_indicators:
                if indicator in response_text:
                    logger.debug(
                        f"[Label Studio] Detected token expiration indicator: '{indicator}'"
                    )
                    return True
            
            # Also check JSON response if available
            try:
                response_json = response.json()
                detail = str(response_json.get('detail', '')).lower()
                message = str(response_json.get('message', '')).lower()
                error = str(response_json.get('error', '')).lower()
                
                for field in [detail, message, error]:
                    for indicator in expiration_indicators:
                        if indicator in field:
                            logger.debug(
                                f"[Label Studio] Detected token expiration in JSON: '{indicator}'"
                            )
                            return True
            except (ValueError, KeyError):
                # JSON parsing failed, continue with text-based detection
                pass
                
        except Exception as e:
            logger.debug(f"[Label Studio] Error checking token expiration: {e}")
        
        return False
    
    async def _handle_token_expiration_and_retry(
        self,
        api_call: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Handle token expiration by refreshing and retrying the API call.
        
        This method wraps an API call and handles 401 token expiration errors
        by automatically refreshing the JWT token and retrying the original
        call with the new token.
        
        The flow is:
        1. Execute the API call
        2. If 401 with token expiration detected:
           a. Refresh the JWT token
           b. Retry the original API call with new token
        3. If refresh fails, fall back to re-authentication
        4. If re-authentication fails, raise LabelStudioAuthenticationError
        
        Args:
            api_call: The async callable to execute (should return httpx.Response)
            *args: Positional arguments for the API call
            **kwargs: Keyword arguments for the API call
            
        Returns:
            The result of the API call (httpx.Response)
            
        Raises:
            LabelStudioAuthenticationError: If authentication cannot be recovered
            
        Validates: Requirements 5.3, 8.1, 8.2 - Token expiration detection and retry
        """
        # Only handle token expiration for JWT authentication
        if self._auth_method != 'jwt' or not self._jwt_auth_manager:
            return await api_call(*args, **kwargs)
        
        # First attempt
        response = await api_call(*args, **kwargs)
        
        # Check if token expired
        if self._is_token_expired_response(response):
            logger.info(
                "[Label Studio] Token expiration detected in API response, "
                "attempting token refresh and retry"
            )
            
            try:
                # Refresh the token
                await self._jwt_auth_manager.refresh_token()
                logger.info("[Label Studio] Token refreshed successfully, retrying API call")
                
                # Retry the API call with new token
                # Note: The caller should call _get_headers() again to get new headers
                response = await api_call(*args, **kwargs)
                
                # Check if still getting token expiration after refresh
                if self._is_token_expired_response(response):
                    logger.warning(
                        "[Label Studio] Token still expired after refresh, "
                        "attempting re-authentication"
                    )
                    
                    # Try re-authentication
                    await self._jwt_auth_manager.login()
                    logger.info(
                        "[Label Studio] Re-authentication successful, retrying API call"
                    )
                    
                    # Final retry after re-authentication
                    response = await api_call(*args, **kwargs)
                    
                    if self._is_token_expired_response(response):
                        # This shouldn't happen after fresh login
                        error_msg = (
                            "Token still expired after re-authentication. "
                            "This may indicate a server-side issue."
                        )
                        logger.error(f"[Label Studio] {error_msg}")
                        raise LabelStudioAuthenticationError(error_msg, status_code=401)
                        
            except LabelStudioAuthenticationError:
                # Re-raise authentication errors
                raise
            except Exception as e:
                error_msg = f"Failed to recover from token expiration: {str(e)}"
                logger.error(f"[Label Studio] {error_msg}")
                raise LabelStudioAuthenticationError(error_msg, status_code=401)
        
        return response
    
    @property
    def auth_method(self) -> str:
        """
        Get the current authentication method.
        
        Returns:
            str: 'jwt' or 'api_token'
        """
        return self._auth_method
    
    @property
    def is_jwt_authenticated(self) -> bool:
        """
        Check if JWT authentication is being used and is authenticated.
        
        Returns:
            bool: True if JWT auth is active and authenticated
        """
        if self._jwt_auth_manager:
            return self._jwt_auth_manager.is_authenticated
        return False
    
    @label_studio_retry(
        max_attempts=3,
        base_delay=1.0,
        operation_name="create_project"
    )
    async def create_project(self, project_config: ProjectConfig) -> LabelStudioProject:
        """
        Create a new Label Studio project.
        
        This method is decorated with @label_studio_retry to automatically retry
        on network errors and timeouts with exponential backoff.
        
        Args:
            project_config: Project configuration settings
            
        Returns:
            LabelStudioProject: Created project information
            
        Raises:
            LabelStudioAuthenticationError: If authentication fails (not retried)
            LabelStudioIntegrationError: If project creation fails after retries
            
        Validates: Requirements 1.5 - Handle network errors, timeouts, authentication failures
        Validates: Requirements 7.1 - Use JWT authentication for API calls
        Validates: Requirements 5.3, 8.1, 8.2 - Token expiration detection and retry
        """
        # Prepare project data
        label_config = (project_config.label_config or 
                      self.config.get_default_label_config(project_config.annotation_type))
        
        project_data = {
            "title": project_config.title,
            "description": project_config.description,
            "label_config": label_config,
            "expert_instruction": "请根据标注指南进行数据标注。",
            "show_instruction": True,
            "show_skip_button": True,
            "enable_empty_annotation": False,
            "show_annotation_history": True,
            "color": "#1f77b4",
            "maximum_annotations": 1,
            "is_published": False,
            "is_draft": False,
            "sampling": "Sequential sampling",
            "show_collab_predictions": True,
            "reveal_preannotations_interactively": True
        }
        
        async def make_api_call():
            """Inner function to make the API call with fresh headers."""
            headers = await self._get_headers()
            async with httpx.AsyncClient(timeout=30.0) as client:
                return await client.post(
                    f"{self.base_url}/api/projects/",
                    headers=headers,
                    json=project_data
                )
        
        # Make API request with token expiration handling
        response = await self._handle_token_expiration_and_retry(make_api_call)
        
        # Handle authentication errors (should not be retried)
        if response.status_code == 401:
            error_msg = "Invalid API token or unauthorized access"
            logger.error(f"[Label Studio] Authentication failed: {error_msg}")
            raise LabelStudioAuthenticationError(error_msg, status_code=401)
        
        if response.status_code == 403:
            error_msg = "Access forbidden - insufficient permissions"
            logger.error(f"[Label Studio] Authorization failed: {error_msg}")
            raise LabelStudioAuthenticationError(error_msg, status_code=403)
        
        if response.status_code == 201:
            project_info = response.json()
            logger.info(f"Created Label Studio project: {project_info['id']}")
            
            # Convert to LabelStudioProject - avoid duplicate parameters
            project_kwargs = {k: v for k, v in project_info.items() 
                            if k in LabelStudioProject.__dataclass_fields__}
            
            return LabelStudioProject(**project_kwargs)
        else:
            error_msg = f"Failed to create project: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise LabelStudioIntegrationError(error_msg)
    
    @label_studio_retry(
        max_attempts=3,
        base_delay=1.0,
        operation_name="import_tasks"
    )
    async def import_tasks(self, project_id: str, tasks: List[Task]) -> ImportResult:
        """
        Import tasks into a Label Studio project.
        
        This method is decorated with @label_studio_retry to automatically retry
        on network errors and timeouts with exponential backoff.
        
        Args:
            project_id: Label Studio project ID
            tasks: List of tasks to import
            
        Returns:
            ImportResult: Import operation results
            
        Raises:
            LabelStudioAuthenticationError: If authentication fails (not retried)
            
        Validates: Requirements 1.5 - Handle network errors, timeouts, authentication failures
        Validates: Requirements 7.2 - Use JWT authentication for API calls
        """
        try:
            imported_count = 0
            failed_count = 0
            errors = []
            
            # Convert tasks to Label Studio format
            ls_tasks = []
            for task in tasks:
                try:
                    # Get document content
                    with get_db_session() as db:
                        stmt = select(DocumentModel).where(
                            DocumentModel.id == task.document_id
                        )
                        doc_model = db.execute(stmt).scalar_one_or_none()
                        
                        if not doc_model:
                            errors.append(f"Document not found for task {task.id}")
                            failed_count += 1
                            continue
                    
                    # Prepare task data for Label Studio
                    ls_task = {
                        "data": {
                            "text": doc_model.content,
                            "document_id": str(task.document_id),
                            "task_id": str(task.id)
                        },
                        "meta": {
                            "superinsight_task_id": str(task.id),
                            "document_id": str(task.document_id),
                            "created_at": task.created_at.isoformat()
                        }
                    }
                    
                    # Add AI predictions if available
                    if task.ai_predictions:
                        ls_task["predictions"] = []
                        for pred in task.ai_predictions:
                            ls_task["predictions"].append({
                                "model_version": pred.get("model", "unknown"),
                                "result": pred.get("result", []),
                                "score": pred.get("confidence", 0.0)
                            })
                    
                    ls_tasks.append(ls_task)
                    
                except Exception as e:
                    errors.append(f"Error processing task {task.id}: {str(e)}")
                    failed_count += 1
            
            # Get authentication headers (JWT or API token)
            headers = await self._get_headers()
            
            # Import tasks in batches
            batch_size = 100
            for i in range(0, len(ls_tasks), batch_size):
                batch = ls_tasks[i:i + batch_size]
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/api/projects/{project_id}/import",
                        headers=headers,
                        json=batch
                    )
                    
                    if response.status_code == 201:
                        result = response.json()
                        imported_count += len(batch)
                        logger.info(f"Imported batch of {len(batch)} tasks to project {project_id}")
                    else:
                        error_msg = f"Failed to import batch: {response.status_code} - {response.text}"
                        errors.append(error_msg)
                        failed_count += len(batch)
                        logger.error(error_msg)
            
            # Update task status in database
            await self._sync_tasks_to_db(project_id, tasks)
            
            return ImportResult(
                success=failed_count == 0,
                imported_count=imported_count,
                failed_count=failed_count,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Error importing tasks: {str(e)}"
            logger.error(error_msg)
            return ImportResult(
                success=False,
                failed_count=len(tasks),
                errors=[error_msg]
            )
    
    async def export_annotations(self, project_id: str, export_format: str = "JSON") -> ExportResult:
        """
        Export annotations from a Label Studio project.
        
        Args:
            project_id: Label Studio project ID
            export_format: Export format (JSON, CSV, etc.)
            
        Returns:
            ExportResult: Export operation results
            
        Validates: Requirements 7.2 - Use JWT authentication for API calls
        """
        try:
            # Get authentication headers (JWT or API token)
            headers = await self._get_headers()
            
            # Get annotations from Label Studio
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/projects/{project_id}/export",
                    headers=headers,
                    params={"exportType": export_format}
                )
                
                if response.status_code == 200:
                    annotations_data = response.json()
                    
                    # Sync annotations back to PostgreSQL
                    await self._sync_annotations_to_db(project_id, annotations_data)
                    
                    logger.info(f"Exported {len(annotations_data)} annotations from project {project_id}")
                    
                    return ExportResult(
                        success=True,
                        exported_count=len(annotations_data),
                        data=annotations_data
                    )
                else:
                    error_msg = f"Failed to export annotations: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return ExportResult(
                        success=False,
                        errors=[error_msg]
                    )
                    
        except Exception as e:
            error_msg = f"Error exporting annotations: {str(e)}"
            logger.error(error_msg)
            return ExportResult(
                success=False,
                errors=[error_msg]
            )
    
    async def setup_webhooks(self, project_id: str, webhook_urls: List[str]) -> bool:
        """
        Configure webhooks for quality check triggers.
        
        Args:
            project_id: Label Studio project ID
            webhook_urls: List of webhook URLs to configure
            
        Returns:
            bool: True if webhooks were configured successfully
            
        Validates: Requirements 7.2 - Use JWT authentication for API calls
        """
        try:
            # Get authentication headers (JWT or API token)
            headers = await self._get_headers()
            
            for webhook_url in webhook_urls:
                webhook_config = self.config.get_webhook_config(webhook_url)
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/api/projects/{project_id}/webhooks/",
                        headers=headers,
                        json=webhook_config
                    )
                    
                    if response.status_code == 201:
                        logger.info(f"Configured webhook for project {project_id}: {webhook_url}")
                    else:
                        logger.error(f"Failed to configure webhook: {response.status_code} - {response.text}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error configuring webhooks: {str(e)}")
            return False
    
    async def configure_ml_backend(self, project_id: str, ml_backend_url: str) -> bool:
        """
        Configure ML backend for AI predictions.
        
        Args:
            project_id: Label Studio project ID
            ml_backend_url: ML backend service URL
            
        Returns:
            bool: True if ML backend was configured successfully
            
        Validates: Requirements 7.2 - Use JWT authentication for API calls
        """
        try:
            # Get authentication headers (JWT or API token)
            headers = await self._get_headers()
            
            ml_config = self.config.get_ml_backend_config(ml_backend_url)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/ml/",
                    headers=headers,
                    json={**ml_config, "project": project_id}
                )
                
                if response.status_code == 201:
                    logger.info(f"Configured ML backend for project {project_id}: {ml_backend_url}")
                    return True
                else:
                    logger.error(f"Failed to configure ML backend: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error configuring ML backend: {str(e)}")
            return False
    
    async def _sync_tasks_to_db(self, project_id: str, tasks: List[Task]) -> None:
        """Synchronize tasks to PostgreSQL database"""
        try:
            with get_db_session() as db:
                for task in tasks:
                    # Update or create task in database
                    stmt = select(TaskModel).where(TaskModel.id == task.id)
                    task_model = db.execute(stmt).scalar_one_or_none()
                    
                    if task_model:
                        task_model.project_id = project_id
                        task_model.status = TaskStatus.PENDING
                    else:
                        task_model = TaskModel(
                            id=task.id,
                            document_id=task.document_id,
                            project_id=project_id,
                            status=TaskStatus.PENDING,
                            annotations=task.annotations,
                            ai_predictions=task.ai_predictions,
                            quality_score=task.quality_score
                        )
                        db.add(task_model)
                
                db.commit()
                logger.info(f"Synchronized {len(tasks)} tasks to database")
                
        except Exception as e:
            logger.error(f"Error syncing tasks to database: {str(e)}")
            raise
    
    async def _sync_annotations_to_db(self, project_id: str, annotations_data: List[Dict[str, Any]]) -> None:
        """Synchronize annotations from Label Studio to PostgreSQL"""
        try:
            with get_db_session() as db:
                for annotation in annotations_data:
                    # Extract task ID from annotation metadata
                    task_id = None
                    if 'meta' in annotation and 'superinsight_task_id' in annotation['meta']:
                        task_id = UUID(annotation['meta']['superinsight_task_id'])
                    elif 'data' in annotation and 'task_id' in annotation['data']:
                        task_id = UUID(annotation['data']['task_id'])
                    
                    if not task_id:
                        logger.warning(f"Could not find task ID for annotation: {annotation.get('id')}")
                        continue
                    
                    # Update task with annotation data
                    stmt = select(TaskModel).where(TaskModel.id == task_id)
                    task_model = db.execute(stmt).scalar_one_or_none()
                    if task_model:
                        # Add annotation to task
                        if not task_model.annotations:
                            task_model.annotations = []
                        
                        task_model.annotations.append({
                            "id": annotation.get("id"),
                            "result": annotation.get("annotations", [{}])[0].get("result", []),
                            "created_at": annotation.get("created_at"),
                            "updated_at": annotation.get("updated_at"),
                            "lead_time": annotation.get("lead_time", 0),
                            "annotator": annotation.get("completed_by", {}).get("id")
                        })
                        
                        # Update task status
                        if annotation.get("annotations"):
                            task_model.status = TaskStatus.COMPLETED
                        
                        db.add(task_model)
                
                db.commit()
                logger.info(f"Synchronized {len(annotations_data)} annotations to database")
                
        except Exception as e:
            logger.error(f"Error syncing annotations to database: {str(e)}")
            raise
    
    async def test_connection(self, timeout: float = 10.0) -> bool:
        """
        Test Label Studio API connectivity.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            bool: True if connection is successful, False otherwise
            
        Validates: Requirements 7.5 - Use JWT authentication for API calls
        Validates: Requirements 5.3, 8.1, 8.2 - Token expiration detection and retry
        """
        try:
            async def make_api_call():
                """Inner function to make the API call with fresh headers."""
                headers = await self._get_headers()
                async with httpx.AsyncClient(timeout=timeout) as client:
                    return await client.get(
                        f"{self.base_url}/api/current-user/whoami/",
                        headers=headers
                    )
            
            # Make API request with token expiration handling
            response = await self._handle_token_expiration_and_retry(make_api_call)

            if response.status_code == 200:
                logger.info("Label Studio connection test successful")
                return True
            elif response.status_code == 401:
                logger.warning("Label Studio authentication failed")
                return False
            else:
                logger.warning(f"Label Studio returned status code: {response.status_code}")
                return False

        except httpx.TimeoutException:
            logger.error("Label Studio connection timed out")
            return False
        except httpx.RequestError as e:
            logger.error(f"Label Studio connection error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing Label Studio connection: {str(e)}")
            return False

    @label_studio_retry(
        max_attempts=3,
        base_delay=1.0,
        operation_name="get_project_info"
    )
    async def get_project_info(self, project_id: str) -> Optional[LabelStudioProject]:
        """
        Get project information from Label Studio.
        
        This method is decorated with @label_studio_retry to automatically retry
        on network errors and timeouts with exponential backoff.
        
        Args:
            project_id: Label Studio project ID
            
        Returns:
            LabelStudioProject: Project information, or None if not found
            
        Raises:
            LabelStudioAuthenticationError: If authentication fails (not retried)
            
        Validates: Requirements 1.5 - Handle network errors, timeouts, authentication failures
        Validates: Requirements 7.5 - Use JWT authentication for API calls
        Validates: Requirements 5.3, 8.1, 8.2 - Token expiration detection and retry
        """
        async def make_api_call():
            """Inner function to make the API call with fresh headers."""
            headers = await self._get_headers()
            async with httpx.AsyncClient(timeout=30.0) as client:
                return await client.get(
                    f"{self.base_url}/api/projects/{project_id}/",
                    headers=headers
                )
        
        # Make API request with token expiration handling
        response = await self._handle_token_expiration_and_retry(make_api_call)
        
        # Handle authentication errors (should not be retried)
        if response.status_code == 401:
            error_msg = "Invalid API token or unauthorized access"
            logger.error(f"[Label Studio] Authentication failed: {error_msg}")
            raise LabelStudioAuthenticationError(error_msg, status_code=401)
        
        if response.status_code == 403:
            error_msg = "Access forbidden - insufficient permissions"
            logger.error(f"[Label Studio] Authorization failed: {error_msg}")
            raise LabelStudioAuthenticationError(error_msg, status_code=403)
        
        # Handle project not found (should not be retried)
        if response.status_code == 404:
            logger.warning(f"Project {project_id} not found in Label Studio")
            return None
        
        if response.status_code == 200:
            project_data = response.json()
            return LabelStudioProject(**project_data)
        else:
            logger.error(f"Failed to get project info: {response.status_code}")
            return None

    @label_studio_retry(
        max_attempts=3,
        base_delay=1.0,
        operation_name="validate_project"
    )
    async def validate_project(self, project_id: str) -> ProjectValidationResult:
        """
        Validate that a Label Studio project exists and is accessible.
        
        This method checks if a project exists in Label Studio, retrieves its
        task and annotation counts, and returns a comprehensive validation result.
        It is used to verify project status before navigation to annotation pages.
        
        The method is decorated with @label_studio_retry to automatically retry
        on network errors and timeouts with exponential backoff.
        
        Args:
            project_id: Label Studio project ID to validate
            
        Returns:
            ProjectValidationResult: Validation result containing:
                - exists: Whether the project exists
                - accessible: Whether the project is accessible
                - task_count: Number of tasks in the project
                - annotation_count: Number of completed annotations
                - status: Project status ('ready', 'creating', 'error')
                - error_message: Optional error message if validation failed
                
        Validates: Requirements 1.1 - Label Studio project and tasks are successfully fetched
        Validates: Requirements 1.2 - Label Studio project page loads successfully (no 404 error)
        Validates: Requirements 1.5 - Handle network errors, timeouts, authentication failures
        
        Example:
            >>> result = await integration.validate_project("123")
            >>> if result.exists and result.accessible:
            ...     print(f"Project ready with {result.task_count} tasks")
            ... else:
            ...     print(f"Project validation failed: {result.error_message}")
        """
        try:
            # Step 1: Check if project exists using get_project_info
            # Note: get_project_info has its own retry decorator, but we catch
            # exceptions here to return a proper validation result
            project_info = await self.get_project_info(project_id)
            
            if project_info is None:
                logger.warning(f"Project {project_id} not found in Label Studio")
                return ProjectValidationResult(
                    exists=False,
                    accessible=False,
                    task_count=0,
                    annotation_count=0,
                    status="error",
                    error_message=f"Project {project_id} not found in Label Studio"
                )
            
            # Step 2: Get task and annotation counts from project info
            # Label Studio project info includes task_number and num_tasks_with_annotations
            task_count = getattr(project_info, 'task_number', 0) or 0
            annotation_count = getattr(project_info, 'num_tasks_with_annotations', 0) or 0
            
            # Step 3: Determine project status
            # Check if project is in a valid state for annotation
            is_published = getattr(project_info, 'is_published', False)
            is_draft = getattr(project_info, 'is_draft', False)
            
            if is_draft:
                status = "creating"
            elif task_count == 0:
                status = "ready"  # Project exists but has no tasks yet
            else:
                status = "ready"
            
            logger.info(
                f"Project {project_id} validated: exists=True, accessible=True, "
                f"task_count={task_count}, annotation_count={annotation_count}, status={status}"
            )
            
            return ProjectValidationResult(
                exists=True,
                accessible=True,
                task_count=task_count,
                annotation_count=annotation_count,
                status=status,
                error_message=None
            )
            
        except LabelStudioAuthenticationError as e:
            # Authentication errors - return validation result with auth error
            error_msg = f"Authentication failed for project {project_id}: {str(e)}"
            logger.error(error_msg)
            return ProjectValidationResult(
                exists=False,
                accessible=False,
                task_count=0,
                annotation_count=0,
                status="error",
                error_message=error_msg
            )
            
        except (httpx.TimeoutException, httpx.RequestError, httpx.NetworkError) as e:
            # Network errors - let them propagate for retry decorator
            # But if we're here after retries, return error result
            error_msg = f"Network error validating project {project_id}: {str(e)}"
            logger.error(error_msg)
            # Re-raise to let retry decorator handle it
            raise
            
        except Exception as e:
            error_msg = f"Unexpected error validating project {project_id}: {str(e)}"
            logger.error(error_msg)
            return ProjectValidationResult(
                exists=False,
                accessible=False,
                task_count=0,
                annotation_count=0,
                status="error",
                error_message=error_msg
            )

    @label_studio_retry(
        max_attempts=3,
        base_delay=1.0,
        operation_name="ensure_project_exists"
    )
    async def ensure_project_exists(
        self,
        project_id: Optional[str],
        project_config: ProjectConfig
    ) -> LabelStudioProject:
        """
        Ensure Label Studio project exists for a task.
        Creates project if it doesn't exist.
        
        This method implements idempotent project creation - calling it multiple
        times with the same project_id will return the existing project.
        
        The method is decorated with @label_studio_retry to automatically retry
        on network errors and timeouts with exponential backoff.
        
        Args:
            project_id: Existing Label Studio project ID (can be None)
            project_config: Project configuration for creating new project
            
        Returns:
            LabelStudioProject: Project information (existing or newly created)
            
        Raises:
            LabelStudioAuthenticationError: If authentication fails (not retried)
            LabelStudioIntegrationError: If project creation fails after retries
            
        Validates: Requirements 1.3 - Automatic Project Creation
        Validates: Requirements 1.5 - Handle network errors, timeouts, authentication failures
        """
        # If project_id is provided, check if project exists
        if project_id:
            try:
                existing_project = await self.get_project_info(project_id)
                if existing_project:
                    logger.info(f"Project {project_id} already exists, reusing")
                    return existing_project
                else:
                    logger.warning(f"Project {project_id} not found, will create new project")
            except LabelStudioAuthenticationError:
                # Re-raise authentication errors - user needs to re-authenticate
                raise
            except (httpx.TimeoutException, httpx.RequestError, httpx.NetworkError) as e:
                # Network errors during check - let them propagate for retry
                logger.warning(f"Network error checking project {project_id}: {str(e)}, will create new project")
            except Exception as e:
                logger.warning(f"Error checking project {project_id}: {str(e)}, will create new project")
        
        # Project doesn't exist or project_id is None, create new project
        logger.info(f"Creating new Label Studio project: {project_config.title}")
        
        try:
            new_project = await self.create_project(project_config)
            logger.info(f"Successfully created Label Studio project: {new_project.id}")
            return new_project
        except LabelStudioAuthenticationError:
            # Re-raise authentication errors - user needs to re-authenticate
            logger.error(f"Authentication failed while creating project: {project_config.title}")
            raise
        except LabelStudioIntegrationError as e:
            logger.error(f"Failed to create project: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error ensuring project exists: {str(e)}"
            logger.error(error_msg)
            raise LabelStudioIntegrationError(error_msg)

    async def generate_authenticated_url(
        self,
        project_id: str,
        user_id: str,
        language: str = "zh",
        expires_in: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate authenticated URL with temporary token and language parameter.
        
        This method creates a temporary JWT token for Label Studio access and
        constructs a URL with the token and language preference. The URL can
        be used to open Label Studio in a new window with automatic authentication
        and the user's preferred language.
        
        Security Note:
            This method checks if the URL uses HTTPS when tokens are included.
            In production environments, HTTP URLs will trigger a security warning
            as tokens may be exposed in transit.
        
        Args:
            project_id: Label Studio project ID to access
            user_id: User identifier for token generation
            language: User's language preference ('zh' for Chinese, 'en' for English)
                     Defaults to 'zh' (Chinese)
            expires_in: Token expiration time in seconds (default: 3600 = 1 hour)
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - url: Complete authenticated URL with token and language
                - token: The generated temporary token
                - expires_at: ISO format datetime when token expires
                - project_id: The project ID
                - language: The language parameter used
                - is_secure: Whether the URL uses HTTPS
                
        Raises:
            LabelStudioIntegrationError: If URL generation fails
            
        Validates: Requirements 1.2 - Language matches user preference
        Validates: Requirements 1.5 - Language preference included in authenticated URL
        Validates: Requirements 10.3 - HTTPS enforcement for token URLs
        
        Example:
            >>> url_info = await integration.generate_authenticated_url(
            ...     project_id="123",
            ...     user_id="user-456",
            ...     language="zh"
            ... )
            >>> print(url_info['url'])
            'https://label-studio:8080/projects/123?token=eyJ...&lang=zh'
        """
        try:
            # HTTPS Security Check (Requirement 10.3)
            is_secure = self._check_https_security()
            # Validate language parameter - only 'zh' and 'en' are supported
            # Map common language codes to Label Studio supported codes
            language_map = {
                'zh': 'zh',
                'zh-CN': 'zh',
                'zh-Hans': 'zh',
                'zh-TW': 'zh',
                'en': 'en',
                'en-US': 'en',
                'en-GB': 'en',
            }
            
            # Normalize language code, default to 'zh' if not recognized
            normalized_language = language_map.get(language, 'zh')
            
            if language not in language_map:
                logger.warning(
                    f"Unsupported language '{language}', defaulting to 'zh'. "
                    f"Supported languages: {list(language_map.keys())}"
                )
            
            # Create temporary token with expiration
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            token_payload = {
                "sub": user_id,
                "project_id": project_id,
                "purpose": "label_studio_access",
                "lang": normalized_language,
                "exp": expires_at,
                "iat": datetime.utcnow(),
                "jti": str(uuid4())  # Unique token ID for potential revocation
            }
            
            # Generate JWT token using security settings
            temp_token = jwt.encode(
                token_payload,
                settings.security.jwt_secret_key,
                algorithm=settings.security.jwt_algorithm
            )
            
            # Construct authenticated URL with token and language parameter
            # Label Studio supports ?lang=zh or ?lang=en for language switching
            authenticated_url = (
                f"{self.base_url}/projects/{project_id}"
                f"?token={temp_token}&lang={normalized_language}"
            )
            
            logger.info(
                f"Generated authenticated URL for project {project_id}, "
                f"user {user_id}, language {normalized_language}, "
                f"expires at {expires_at.isoformat()}"
            )
            
            return {
                "url": authenticated_url,
                "token": temp_token,
                "expires_at": expires_at.isoformat() + "Z",
                "project_id": project_id,
                "language": normalized_language,
                "is_secure": is_secure
            }
            
        except jwt.PyJWTError as e:
            error_msg = f"Failed to generate JWT token: {str(e)}"
            logger.error(error_msg)
            raise LabelStudioIntegrationError(error_msg)
        except Exception as e:
            error_msg = f"Failed to generate authenticated URL: {str(e)}"
            logger.error(error_msg)
            raise LabelStudioIntegrationError(error_msg)

    def _create_temporary_token(
        self,
        user_id: str,
        project_id: str,
        language: str = "zh",
        expires_in: int = 3600
    ) -> str:
        """
        Create a temporary JWT token for Label Studio access.
        
        This is a synchronous helper method for token generation.
        
        Args:
            user_id: User identifier
            project_id: Label Studio project ID
            language: Language preference
            expires_in: Token expiration time in seconds
            
        Returns:
            str: JWT token string
        """
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        payload = {
            "sub": user_id,
            "project_id": project_id,
            "purpose": "label_studio_access",
            "lang": language,
            "exp": expires_at,
            "iat": datetime.utcnow(),
            "jti": str(uuid4())
        }
        
        return jwt.encode(
            payload,
            settings.security.jwt_secret_key,
            algorithm=settings.security.jwt_algorithm
        )

    async def delete_project(self, project_id: str) -> bool:
        """
        Delete a Label Studio project.
        
        Args:
            project_id: Label Studio project ID
            
        Returns:
            bool: True if project was deleted successfully
            
        Validates: Requirements 7.2 - Use JWT authentication for API calls
        """
        try:
            # Get authentication headers (JWT or API token)
            headers = await self._get_headers()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.base_url}/api/projects/{project_id}/",
                    headers=headers
                )
                
                if response.status_code == 204:
                    logger.info(f"Deleted Label Studio project: {project_id}")
                    return True
                else:
                    logger.error(f"Failed to delete project: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting project: {str(e)}")
            return False


# Global integration instance
label_studio_integration = LabelStudioIntegration()