"""
Audit Middleware for FastAPI

Automatically logs all state-changing operations with timestamp, user,
operation details, duration, and result for compliance and traceability.

Validates: Requirements 3.6, 10.1, 10.2
"""

import time
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.orm import Session

from src.models.data_lifecycle import (
    OperationType,
    OperationResult,
    ResourceType,
    Action
)
from src.services.audit_logger import AuditLogger


# HTTP methods that are considered state-changing
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Mapping of HTTP methods to operation types
METHOD_TO_OPERATION_TYPE = {
    "POST": OperationType.CREATE,
    "PUT": OperationType.UPDATE,
    "PATCH": OperationType.UPDATE,
    "DELETE": OperationType.DELETE,
    "GET": OperationType.READ
}

# Mapping of URL patterns to resource types
# This can be extended based on your API structure
URL_PATTERN_TO_RESOURCE_TYPE = {
    "/temp-data": ResourceType.TEMP_DATA,
    "/samples": ResourceType.SAMPLE,
    "/annotation-tasks": ResourceType.ANNOTATION_TASK,
    "/annotated-data": ResourceType.ANNOTATED_DATA,
    "/enhanced-data": ResourceType.ENHANCED_DATA,
    "/trials": ResourceType.TRIAL
}

# Mapping of URL patterns to actions
URL_PATTERN_TO_ACTION = {
    "review": Action.REVIEW,
    "approve": Action.TRANSFER,
    "reject": Action.REVIEW,
    "annotate": Action.ANNOTATE,
    "enhance": Action.ENHANCE,
    "trial": Action.TRIAL
}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic audit logging of state-changing operations.
    
    This middleware intercepts all FastAPI requests, extracts operation details,
    measures execution duration, and automatically logs state-changing operations
    to the audit trail.
    
    Features:
    - Automatic logging of POST, PUT, PATCH, DELETE operations
    - Records timestamp, user, operation details, duration, and result
    - Extracts resource type and action from URL patterns
    - Handles errors and logs operation failures
    - Minimal performance overhead
    
    Validates: Requirements 3.6, 10.1, 10.2
    """
    
    def __init__(
        self,
        app: ASGIApp,
        get_db: Callable[[], Session],
        excluded_paths: Optional[list[str]] = None
    ):
        """
        Initialize the audit middleware.
        
        Args:
            app: ASGI application
            get_db: Function to get database session
            excluded_paths: List of URL paths to exclude from audit logging
        """
        super().__init__(app)
        self.get_db = get_db
        self.excluded_paths = excluded_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/static",
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and log state-changing operations.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware or endpoint handler
            
        Returns:
            Response from the endpoint handler
        """
        # Skip excluded paths
        if self._should_skip_logging(request):
            return await call_next(request)
        
        # Skip non-state-changing operations (GET requests)
        if request.method not in STATE_CHANGING_METHODS:
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Extract operation details
        user_id = self._extract_user_id(request)
        resource_type = self._extract_resource_type(request)
        resource_id = self._extract_resource_id(request)
        action = self._extract_action(request)
        operation_type = METHOD_TO_OPERATION_TYPE.get(request.method, OperationType.UPDATE)
        
        # Execute the request
        response = None
        error = None
        result = OperationResult.SUCCESS
        
        try:
            response = await call_next(request)
            
            # Determine result based on status code
            if response.status_code >= 500:
                result = OperationResult.FAILURE
                error = f"Server error: {response.status_code}"
            elif response.status_code >= 400:
                result = OperationResult.FAILURE
                error = f"Client error: {response.status_code}"
            elif response.status_code >= 200 and response.status_code < 300:
                result = OperationResult.SUCCESS
            else:
                result = OperationResult.PARTIAL
                
        except Exception as e:
            result = OperationResult.FAILURE
            error = str(e)
            raise
        finally:
            # Calculate duration in milliseconds
            duration = int((time.time() - start_time) * 1000)
            
            # Log the operation
            if user_id and resource_type and resource_id:
                self._log_operation(
                    operation_type=operation_type,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action,
                    result=result,
                    duration=duration,
                    error=error,
                    request=request
                )
        
        return response
    
    def _should_skip_logging(self, request: Request) -> bool:
        """
        Check if the request should be skipped from audit logging.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if logging should be skipped, False otherwise
        """
        path = request.url.path
        
        # Check excluded paths
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        
        return False
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from the request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User ID if available, None otherwise
        """
        # Try to get user from request state (set by auth middleware)
        if hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, "id"):
                return str(user.id)
            elif isinstance(user, dict) and "id" in user:
                return str(user["id"])
        
        # Try to get from headers
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # Default to anonymous if no user found
        return "anonymous"
    
    def _extract_resource_type(self, request: Request) -> Optional[ResourceType]:
        """
        Extract resource type from the request URL.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Resource type if identifiable, None otherwise
        """
        path = request.url.path
        
        # Check URL patterns
        for pattern, resource_type in URL_PATTERN_TO_RESOURCE_TYPE.items():
            if pattern in path:
                return resource_type
        
        # Default to TEMP_DATA if not identifiable
        return ResourceType.TEMP_DATA
    
    def _extract_resource_id(self, request: Request) -> Optional[str]:
        """
        Extract resource ID from the request URL or body.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Resource ID if available, None otherwise
        """
        # Try to extract from path parameters
        path_params = request.path_params
        
        # Common ID parameter names
        id_param_names = ["id", "sample_id", "task_id", "data_id", "resource_id"]
        
        for param_name in id_param_names:
            if param_name in path_params:
                return str(path_params[param_name])
        
        # Try to extract from URL path segments
        # Pattern: /resource-type/{id}/...
        path_segments = request.url.path.strip('/').split('/')
        if len(path_segments) >= 2:
            # Return the second segment (typically the ID)
            return path_segments[1]
        
        # If no ID found, use the full path as identifier
        return request.url.path
    
    def _extract_action(self, request: Request) -> Action:
        """
        Extract action from the request URL and method.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Action type
        """
        path = request.url.path.lower()
        
        # Check URL patterns for specific actions
        for pattern, action in URL_PATTERN_TO_ACTION.items():
            if pattern in path:
                return action
        
        # Default actions based on HTTP method
        method_to_action = {
            "POST": Action.EDIT,
            "PUT": Action.EDIT,
            "PATCH": Action.EDIT,
            "DELETE": Action.DELETE,
            "GET": Action.VIEW
        }
        
        return method_to_action.get(request.method, Action.EDIT)
    
    def _log_operation(
        self,
        operation_type: OperationType,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
        action: Action,
        result: OperationResult,
        duration: int,
        error: Optional[str],
        request: Request
    ):
        """
        Log the operation to the audit trail.
        
        Args:
            operation_type: Type of operation
            user_id: User ID
            resource_type: Resource type
            resource_id: Resource ID
            action: Action performed
            result: Operation result
            duration: Duration in milliseconds
            error: Error message if failed
            request: FastAPI request object
        """
        try:
            # Get database session
            db = next(self.get_db())
            
            # Create audit logger
            audit_logger = AuditLogger(db)
            
            # Extract additional details
            details = {
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
            }
            
            # Log the operation
            audit_logger.log_operation(
                operation_type=operation_type,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                result=result,
                duration=duration,
                error=error,
                details=details,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            
            db.close()
            
        except Exception as e:
            # Log error but don't fail the request
            # In production, you might want to use a proper logger
            print(f"Failed to log audit operation: {e}")


def create_audit_middleware(
    get_db: Callable[[], Session],
    excluded_paths: Optional[list[str]] = None
) -> type[AuditMiddleware]:
    """
    Factory function to create audit middleware with dependencies.
    
    Args:
        get_db: Function to get database session
        excluded_paths: List of URL paths to exclude from audit logging
        
    Returns:
        Configured AuditMiddleware class
        
    Usage:
        from src.middleware.audit_middleware import create_audit_middleware
        from src.database import get_db
        
        app = FastAPI()
        app.add_middleware(
            create_audit_middleware(get_db=get_db)
        )
    """
    class ConfiguredAuditMiddleware(AuditMiddleware):
        def __init__(self, app: ASGIApp):
            super().__init__(app, get_db, excluded_paths)
    
    return ConfiguredAuditMiddleware
