"""
Example usage of Transfer Permission Middleware.

This file demonstrates how to use the transfer permission middleware
in FastAPI endpoints for data transfer operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from src.database.connection import get_db_session
from src.security.models import UserModel
from src.api.auth import get_current_user
from src.middleware.transfer_permission_middleware import (
    check_transfer_permission,
    require_admin_or_data_manager,
    require_admin,
    get_permission_service
)
from src.services.permission_service import PermissionResult, PermissionService


# Example router
router = APIRouter(prefix="/api/data-transfer", tags=["Data Transfer Examples"])


# Example 1: Basic transfer endpoint with permission check
@router.post("/transfer")
async def transfer_data_basic(
    target_state: str,
    record_count: int = 1,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Basic transfer endpoint with inline permission check.
    
    This approach manually checks permissions before executing the transfer.
    """
    # Check permission using the middleware function
    permission = await check_transfer_permission(
        target_state=target_state,
        record_count=record_count,
        is_cross_project=False,
        current_user=current_user,
        db=db
    )
    
    # If we reach here, permission is granted
    # Check if approval is required
    if permission.requires_approval:
        return {
            "success": True,
            "approval_required": True,
            "message": "Transfer request submitted for approval"
        }
    
    # Execute transfer
    return {
        "success": True,
        "transferred_count": record_count,
        "message": f"Successfully transferred {record_count} records"
    }


# Example 2: Approval endpoint requiring admin or data manager
@router.post("/approvals/{approval_id}/approve")
async def approve_transfer(
    approval_id: str,
    approved: bool,
    comment: str = None,
    current_user: UserModel = Depends(require_admin_or_data_manager)
) -> Dict[str, Any]:
    """
    Approval endpoint that requires admin or data_manager role.
    
    The require_admin_or_data_manager dependency automatically checks
    the user's role and raises 403 if insufficient.
    """
    # Only admin or data_manager can reach here
    return {
        "success": True,
        "approval_id": approval_id,
        "approved": approved,
        "approver": current_user.username,
        "comment": comment
    }


# Example 3: Admin-only configuration endpoint
@router.post("/permissions/configure")
async def configure_permissions(
    config: Dict[str, Any],
    current_user: UserModel = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Configuration endpoint that requires admin role.
    
    The require_admin dependency ensures only admins can access this.
    """
    # Only admin can reach here
    return {
        "success": True,
        "message": "Permission configuration updated",
        "updated_by": current_user.username
    }


# Example 4: Permission check endpoint
@router.get("/permissions/check")
async def check_user_permissions(
    target_state: str,
    record_count: int = 1,
    service: PermissionService = Depends(get_permission_service),
    current_user: UserModel = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check user permissions without executing transfer.
    
    This endpoint allows users to check their permissions before
    attempting a transfer operation.
    """
    result = service.check_permission(
        user_role=current_user.role,
        target_state=target_state,
        record_count=record_count
    )
    
    return {
        "has_permission": result.allowed,
        "requires_approval": result.requires_approval,
        "current_role": result.current_role.value,
        "target_state": target_state
    }


# Example 5: Batch transfer with automatic permission check
@router.post("/batch-transfer")
async def batch_transfer(
    transfers: list,
    current_user: UserModel = Depends(require_admin_or_data_manager),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Batch transfer endpoint requiring admin or data_manager.
    
    Batch transfers are restricted to users with elevated privileges.
    """
    results = []
    for transfer in transfers:
        # Check permission for each transfer
        try:
            permission = await check_transfer_permission(
                target_state=transfer["target_state"],
                record_count=len(transfer["records"]),
                is_cross_project=transfer.get("is_cross_project", False),
                current_user=current_user,
                db=db
            )
            
            results.append({
                "success": True,
                "transfer_id": transfer["id"],
                "requires_approval": permission.requires_approval
            })
        except HTTPException as e:
            results.append({
                "success": False,
                "transfer_id": transfer["id"],
                "error": e.detail
            })
    
    return {
        "total": len(transfers),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


# Example 6: Cross-project transfer (admin only)
@router.post("/cross-project-transfer")
async def cross_project_transfer(
    source_project: str,
    target_project: str,
    target_state: str,
    record_count: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Cross-project transfer endpoint.
    
    This operation requires admin role and will be automatically
    checked by the permission middleware.
    """
    # Check permission with cross_project flag
    permission = await check_transfer_permission(
        target_state=target_state,
        record_count=record_count,
        is_cross_project=True,  # This will require admin role
        current_user=current_user,
        db=db
    )
    
    # Only admin can reach here
    return {
        "success": True,
        "source_project": source_project,
        "target_project": target_project,
        "transferred_count": record_count,
        "message": "Cross-project transfer completed"
    }
