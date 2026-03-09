"""
Permission Middleware for FastAPI

Validates user permissions before executing operations and returns
403 Forbidden errors for unauthorized access.
"""

from typing import Callable, Optional, List
from functools import wraps
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from src.models.data_lifecycle import ResourceType, Action
from src.services.permission_manager import PermissionManager, Resource


class PermissionDeniedError(HTTPException):
    """Custom exception for permission denied errors"""
    def __init__(
        self,
        resource_type: ResourceType,
        resource_id: str,
        action: Action,
        required_permissions: Optional[List[Action]] = None
    ):
        detail = {
            'error': 'Permission denied',
            'message': f'You do not have permission to {action.value} {resource_type.value} {resource_id}',
            'resource_type': resource_type.value,
            'resource_id': resource_id,
            'action': action.value,
            'required_permissions': [p.value for p in (required_permissions or [action])]
        }
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


def require_permission(
    resource_type: ResourceType,
    action: Action,
    resource_id_param: str = 'resource_id',
    user_id_param: str = 'user_id'
):
    """
    Decorator to require permission for an endpoint.
    
    Args:
        resource_type: Type of resource being accessed
        action: Action being performed
        resource_id_param: Name of the parameter containing resource ID
        user_id_param: Name of the parameter containing user ID
    
    Usage:
        @router.get("/samples/{sample_id}")
        @require_permission(ResourceType.SAMPLE, Action.VIEW, resource_id_param='sample_id')
        async def get_sample(sample_id: str, user_id: str, db: Session = Depends(get_db)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract resource_id and user_id from kwargs
            resource_id = kwargs.get(resource_id_param)
            user_id = kwargs.get(user_id_param)
            db = kwargs.get('db')
            
            if not resource_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required parameter: {resource_id_param}"
                )
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User authentication required"
                )
            
            if not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session not available"
                )
            
            # Check permission
            permission_manager = PermissionManager(db)
            resource = Resource(type=resource_type, id=resource_id)
            
            # Get user roles from request if available
            user_roles = kwargs.get('user_roles', [])
            
            has_permission = permission_manager.check_permission(
                user_id=user_id,
                resource=resource,
                action=action,
                user_roles=user_roles
            )
            
            if not has_permission:
                raise PermissionDeniedError(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    action=action
                )
            
            # Permission granted, execute the function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_permission_sync(
    db: Session,
    user_id: str,
    resource_type: ResourceType,
    resource_id: str,
    action: Action,
    user_roles: Optional[List[str]] = None
) -> bool:
    """
    Synchronous permission check helper function.
    
    Args:
        db: Database session
        user_id: User ID to check
        resource_type: Type of resource
        resource_id: Resource ID
        action: Action to perform
        user_roles: Optional list of user roles
    
    Returns:
        True if user has permission, False otherwise
    
    Raises:
        PermissionDeniedError: If permission is denied
    """
    permission_manager = PermissionManager(db)
    resource = Resource(type=resource_type, id=resource_id)
    
    has_permission = permission_manager.check_permission(
        user_id=user_id,
        resource=resource,
        action=action,
        user_roles=user_roles
    )
    
    if not has_permission:
        raise PermissionDeniedError(
            resource_type=resource_type,
            resource_id=resource_id,
            action=action
        )
    
    return True


async def check_permission_async(
    db: Session,
    user_id: str,
    resource_type: ResourceType,
    resource_id: str,
    action: Action,
    user_roles: Optional[List[str]] = None
) -> bool:
    """
    Asynchronous permission check helper function.
    
    Args:
        db: Database session
        user_id: User ID to check
        resource_type: Type of resource
        resource_id: Resource ID
        action: Action to perform
        user_roles: Optional list of user roles
    
    Returns:
        True if user has permission, False otherwise
    
    Raises:
        PermissionDeniedError: If permission is denied
    """
    return check_permission_sync(db, user_id, resource_type, resource_id, action, user_roles)


class PermissionMiddleware:
    """
    Middleware class for permission validation in FastAPI.
    
    Can be used as a dependency or middleware to validate permissions
    before executing endpoint handlers.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.permission_manager = PermissionManager(db)
    
    def validate_permission(
        self,
        user_id: str,
        resource_type: ResourceType,
        resource_id: str,
        action: Action,
        user_roles: Optional[List[str]] = None
    ) -> bool:
        """
        Validate user permission for a resource action.
        
        Args:
            user_id: User ID to check
            resource_type: Type of resource
            resource_id: Resource ID
            action: Action to perform
            user_roles: Optional list of user roles
        
        Returns:
            True if permission is granted
        
        Raises:
            PermissionDeniedError: If permission is denied
        """
        resource = Resource(type=resource_type, id=resource_id)
        
        has_permission = self.permission_manager.check_permission(
            user_id=user_id,
            resource=resource,
            action=action,
            user_roles=user_roles
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                resource_type=resource_type,
                resource_id=resource_id,
                action=action
            )
        
        return True
    
    def validate_multiple_permissions(
        self,
        user_id: str,
        permissions: List[tuple[ResourceType, str, Action]],
        user_roles: Optional[List[str]] = None
    ) -> bool:
        """
        Validate multiple permissions at once.
        
        Args:
            user_id: User ID to check
            permissions: List of (resource_type, resource_id, action) tuples
            user_roles: Optional list of user roles
        
        Returns:
            True if all permissions are granted
        
        Raises:
            PermissionDeniedError: If any permission is denied
        """
        for resource_type, resource_id, action in permissions:
            self.validate_permission(
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                user_roles=user_roles
            )
        
        return True
