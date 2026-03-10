"""
Transfer Permission Middleware for Data Transfer Integration.

Provides FastAPI dependency functions for checking data transfer permissions
based on user roles and target states.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_user
from src.database.connection import get_db_session
from src.security.models import UserModel
from src.services.permission_service import PermissionService, PermissionResult


async def check_transfer_permission(
    target_state: str,
    record_count: int = 1,
    is_cross_project: bool = False,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
) -> PermissionResult:
    """
    Check data transfer permission for the current user.
    
    This dependency function validates whether the authenticated user has
    permission to perform a data transfer operation based on their role,
    the target state, and operation characteristics.
    
    Args:
        target_state: Target state for data transfer (temp_stored, 
                     in_sample_library, annotation_pending)
        record_count: Number of records to transfer (default: 1)
        is_cross_project: Whether this is a cross-project transfer (default: False)
        current_user: Current authenticated user (injected by dependency)
        db: Database session (injected by dependency)
    
    Returns:
        PermissionResult with permission details including:
        - allowed: Whether the operation is allowed
        - requires_approval: Whether approval is required
        - current_role: User's current role
        - required_role: Required role if permission denied
        - reason: Reason for denial if applicable
    
    Raises:
        HTTPException: 403 Forbidden if user doesn't have permission
    
    Example:
        @router.post("/transfer")
        async def transfer_data(
            request: DataTransferRequest,
            permission: PermissionResult = Depends(check_transfer_permission)
        ):
            # Permission already checked, proceed with transfer
            ...
    """
    permission_service = PermissionService()
    
    result = permission_service.check_permission(
        user_role=current_user.role,
        target_state=target_state,
        record_count=record_count,
        is_cross_project=is_cross_project
    )
    
    if not result.allowed:
        # Build detailed error response with i18n support
        error_detail = {
            "error_code": "PERMISSION_DENIED",
            "message": "You don't have permission for this operation",
            "message_zh": "您没有权限执行此操作",
            "current_role": result.current_role.value,
            "target_state": target_state,
            "required_permission": "data_manager or admin"
        }
        
        # Add specific reason if available
        if result.reason:
            error_detail["reason"] = result.reason
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_detail
        )
    
    return result


def get_permission_service(db: Session = Depends(get_db_session)) -> PermissionService:
    """
    Dependency to get PermissionService instance.
    
    Args:
        db: Database session (injected by dependency)
    
    Returns:
        PermissionService instance
    
    Example:
        @router.get("/permissions/check")
        async def check_permissions(
            service: PermissionService = Depends(get_permission_service)
        ):
            result = service.check_permission(...)
            return result
    """
    return PermissionService()


async def require_admin_or_data_manager(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    Require user to be admin or data_manager.
    
    This dependency ensures only users with admin or data_manager roles
    can access the endpoint. Useful for approval operations and batch transfers.
    
    Args:
        current_user: Current authenticated user (injected by dependency)
    
    Returns:
        UserModel if user has required role
    
    Raises:
        HTTPException: 403 Forbidden if user doesn't have required role
    
    Example:
        @router.post("/approvals/{approval_id}/approve")
        async def approve_transfer(
            approval_id: str,
            user: UserModel = Depends(require_admin_or_data_manager)
        ):
            # Only admin or data_manager can reach here
            ...
    """
    from src.services.permission_service import UserRole
    
    if current_user.role not in [UserRole.ADMIN, UserRole.DATA_MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "INSUFFICIENT_PRIVILEGES",
                "message": "Only admin or data_manager can perform this operation",
                "message_zh": "只有管理员或数据管理员可以执行此操作",
                "current_role": current_user.role.value,
                "required_roles": ["admin", "data_manager"]
            }
        )
    
    return current_user


async def require_admin(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    Require user to be admin.
    
    This dependency ensures only users with admin role can access the endpoint.
    
    Args:
        current_user: Current authenticated user (injected by dependency)
    
    Returns:
        UserModel if user is admin
    
    Raises:
        HTTPException: 403 Forbidden if user is not admin
    
    Example:
        @router.post("/permissions/configure")
        async def configure_permissions(
            user: UserModel = Depends(require_admin)
        ):
            # Only admin can reach here
            ...
    """
    from src.services.permission_service import UserRole
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "ADMIN_REQUIRED",
                "message": "Only admin can perform this operation",
                "message_zh": "只有管理员可以执行此操作",
                "current_role": current_user.role.value,
                "required_role": "admin"
            }
        )
    
    return current_user
