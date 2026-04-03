"""
Data Lifecycle API

Provides unified data transfer endpoints for moving data from various sources
(structuring, augmentation, sync) to different target states (temp_stored,
in_sample_library, annotation_pending) with permission checks and approval workflow.
"""

import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Header, status as status_code
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.models.data_transfer import DataTransferRequest
from src.services.data_transfer_service import DataTransferService, User
from src.services.permission_service import UserRole
from src.services.transfer_messages import get_message, parse_accept_language
from src.database.connection import get_db_session
from src.api.auth_simple import get_current_user, SimpleUser
from src.security.data_transfer_security import (
    DataTransferSecurityMiddleware,
    SecurityException
)


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response models for OpenAPI documentation
# ---------------------------------------------------------------------------


class TransferSuccessResponse(BaseModel):
    """转存成功响应 / Transfer success response"""
    success: bool = Field(True, description="操作是否成功")
    transferred_count: int = Field(..., description="成功转存的记录数")
    lifecycle_ids: List[str] = Field(..., description="转存后的数据生命周期 ID 列表")
    target_state: str = Field(..., description="目标状态")
    message: str = Field(..., description="国际化提示消息")
    navigation_url: str = Field(..., description="转存后跳转 URL")

    model_config = {"json_schema_extra": {"examples": [{
        "success": True,
        "transferred_count": 15,
        "lifecycle_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
        "target_state": "temp_stored",
        "message": "成功转存 15 条记录到临时存储",
        "navigation_url": "/data-lifecycle/temp-data",
    }]}}


class ApprovalRequiredResponse(BaseModel):
    """需要审批响应 / Approval required response"""
    success: bool = Field(True)
    approval_required: bool = Field(True)
    approval_id: str = Field(..., description="审批工单 ID")
    message: str = Field(..., description="国际化提示消息")
    estimated_approval_time: str = Field(..., description="预计审批时间")

    model_config = {"json_schema_extra": {"examples": [{
        "success": True,
        "approval_required": True,
        "approval_id": "approval-uuid-1234",
        "message": "转存请求已提交，等待审批",
        "estimated_approval_time": "2-3 个工作日",
    }]}}


class ErrorResponse(BaseModel):
    """通用错误响应 / Generic error response"""
    success: bool = Field(False)
    error_code: str = Field(..., description="错误代码")
    message: str = Field(..., description="国际化错误消息")
    details: Optional[str] = Field(None, description="详细错误信息")


class ApprovalItemResponse(BaseModel):
    """审批条目 / Single approval item"""
    id: str
    requester_id: str
    requester_role: str
    status: str
    created_at: str
    expires_at: str
    approver_id: Optional[str] = None
    approved_at: Optional[str] = None
    comment: Optional[str] = None
    transfer_request: Dict[str, Any]


class ApprovalListResponse(BaseModel):
    """审批列表响应 / Approval list response"""
    success: bool = Field(True)
    approvals: List[ApprovalItemResponse] = Field(..., description="审批列表")
    total: int = Field(..., description="总数")
    limit: int = Field(..., description="每页数量")
    offset: int = Field(..., description="偏移量")
    has_more: bool = Field(..., description="是否有更多数据")


class ApprovalActionResponse(BaseModel):
    """审批操作响应 / Approval action response"""
    success: bool = Field(True)
    approval: Dict[str, Any] = Field(..., description="审批详情")
    message: str = Field(..., description="国际化提示消息")

    model_config = {"json_schema_extra": {"examples": [{
        "success": True,
        "approval": {
            "id": "approval-uuid-1234",
            "status": "approved",
            "approver_id": "user-admin-001",
            "approved_at": "2026-03-10T12:00:00",
            "comment": "数据质量合格，批准转存",
        },
        "message": "审批已通过",
    }]}}


class PermissionCheckResponse(BaseModel):
    """权限检查响应 / Permission check response"""
    allowed: bool = Field(..., description="是否允许操作")
    requires_approval: bool = Field(..., description="是否需要审批")
    user_role: str = Field(..., description="当前用户角色")
    reason: Optional[str] = Field(None, description="原因说明")

    model_config = {"json_schema_extra": {"examples": [{
        "allowed": True,
        "requires_approval": False,
        "user_role": "admin",
    }]}}


class BatchTransferResponse(BaseModel):
    """批量转存响应 / Batch transfer response"""
    success: bool = Field(True)
    total_transfers: int = Field(..., description="总请求数")
    successful_transfers: int = Field(..., description="成功数")
    failed_transfers: int = Field(..., description="失败数")
    results: List[Dict[str, Any]] = Field(..., description="各请求结果")

    model_config = {"json_schema_extra": {"examples": [{
        "success": True,
        "total_transfers": 3,
        "successful_transfers": 2,
        "failed_transfers": 1,
        "results": [
            {"success": True, "index": 0, "source_id": "src-1", "transferred_count": 10},
            {"success": True, "index": 1, "source_id": "src-2", "transferred_count": 5},
            {"success": False, "index": 2, "source_id": "src-3", "error_code": "INVALID_SOURCE", "message": "源数据不存在"},
        ],
    }]}}


# ---------------------------------------------------------------------------
# Shared response examples for error codes
# ---------------------------------------------------------------------------

_RESPONSE_400 = {
    "description": "请求参数无效 / Invalid request parameters",
    "content": {"application/json": {"example": {
        "success": False,
        "error_code": "INVALID_SOURCE",
        "message": "源数据不存在或未完成",
        "details": "Source structuring:abc-123 not found",
    }}},
}

_RESPONSE_403 = {
    "description": "权限不足 / Permission denied",
    "content": {"application/json": {"example": {
        "success": False,
        "error_code": "PERMISSION_DENIED",
        "message": "您没有权限执行此操作",
        "details": "Required role: data_manager",
    }}},
}

_RESPONSE_404 = {
    "description": "资源未找到 / Resource not found",
    "content": {"application/json": {"example": {
        "success": False,
        "error_code": "APPROVAL_NOT_FOUND",
        "message": "审批请求未找到",
        "details": "Approval request approval-xyz not found",
    }}},
}

_RESPONSE_500 = {
    "description": "服务器内部错误 / Internal server error",
    "content": {"application/json": {"example": {
        "success": False,
        "error_code": "INTERNAL_ERROR",
        "message": "服务器内部错误，请稍后重试",
    }}},
}


router = APIRouter(
    prefix="/api/data-lifecycle",
    tags=["数据生命周期管理 / Data Lifecycle"],
)


@router.post(
    "/transfer",
    summary="统一数据转存 / Unified Data Transfer",
    description=(
        "将数据从各来源（结构化、增强、同步等）转存到目标状态"
        "（临时存储、样本库、待标注），内置权限检查与审批流程。\n\n"
        "Transfer data from various sources to target states with "
        "integrated permission checking and approval workflow."
    ),
    status_code=status_code.HTTP_200_OK,
    responses={
        200: {"description": "转存成功 / Transfer successful", "model": TransferSuccessResponse},
        202: {"description": "需要审批 / Approval required", "model": ApprovalRequiredResponse},
        400: _RESPONSE_400,
        403: _RESPONSE_403,
        500: _RESPONSE_500,
    },
)
async def transfer_data(
    request: DataTransferRequest,
    db: Session = Depends(get_db_session),
    current_user: SimpleUser = Depends(get_current_user),
    accept_language: Optional[str] = Header(
        None, description="语言偏好，如 zh-CN 或 en-US"
    ),
) -> Dict[str, Any]:
    """统一数据转存接口。

    支持的 source_type: structuring, augmentation, sync, annotation, ai_assistant, manual。
    支持的 target_state: temp_stored, in_sample_library, annotation_pending。
    当用户权限不足时自动触发审批流程并返回 202。
    """
    lang = parse_accept_language(accept_language)
    
    try:
        # Determine user role based on is_superuser flag
        # In a real implementation, this would come from a role field or RBAC system
        if current_user.is_superuser:
            user_role = UserRole.ADMIN
        else:
            # Default to USER role for non-superusers
            # In production, this should be retrieved from a proper RBAC system
            user_role = UserRole.USER
        
        # Security middleware: verify no privilege escalation attempts
        security_middleware = DataTransferSecurityMiddleware()
        await security_middleware.verify_no_privilege_escalation(
            request=request,
            current_user_id=str(current_user.id),
            current_user_role=user_role
        )
        
        # Validate request integrity
        await security_middleware.validate_request_integrity(request)
        
        # Create service instance
        service = DataTransferService(db)
        
        service_user = User(
            id=str(current_user.id),
            role=user_role
        )
        
        # Execute transfer
        result = await service.transfer(request, service_user)
        
        # Internationalize response message
        if result.get("success") and not result.get("approval_required"):
            state_name = get_message(
                f"states.{result['target_state']}",
                lang
            )
            result["message"] = get_message(
                "success",
                lang,
                count=result["transferred_count"],
                state=state_name
            )
        elif result.get("approval_required"):
            result["message"] = get_message("approval_required", lang)
        
        # Return appropriate status code
        if result.get("approval_required"):
            return result
        
        return result
        
    except SecurityException as e:
        # Security violation detected
        logger.error(f"Security violation in transfer: {e}")
        raise HTTPException(
            status_code=status_code.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error_code": "SECURITY_VIOLATION",
                "message": get_message("security_violation", lang),
                "details": str(e)
            }
        )
    
    except ValueError as e:
        # Invalid source or validation error
        logger.warning(f"Transfer validation error: {e}")
        raise HTTPException(
            status_code=status_code.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error_code": "INVALID_SOURCE",
                "message": get_message("invalid_source", lang),
                "details": str(e)
            }
        )
    
    except PermissionError as e:
        # Permission denied
        logger.warning(f"Transfer permission denied: {e}")
        raise HTTPException(
            status_code=status_code.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error_code": "PERMISSION_DENIED",
                "message": get_message("permission_denied", lang),
                "details": str(e)
            }
        )
    
    except Exception as e:
        # Internal server error
        logger.error(f"Transfer internal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": get_message("internal_error", lang),
                "details": str(e)
            }
        )


@router.get(
    "/approvals",
    summary="查询审批列表 / List Approvals",
    description=(
        "查询转存审批请求列表，支持按状态和用户筛选。"
        "普通用户只能查看自己的审批，管理员可查看全部。\n\n"
        "List approval requests with filtering. Regular users see only "
        "their own requests; admins and data managers see all."
    ),
    status_code=status_code.HTTP_200_OK,
    response_model=ApprovalListResponse,
    responses={
        400: _RESPONSE_400,
        403: _RESPONSE_403,
        500: _RESPONSE_500,
    },
)
async def list_approvals(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db_session),
    current_user: SimpleUser = Depends(get_current_user),
    accept_language: Optional[str] = Header(
        None, description="语言偏好，如 zh-CN 或 en-US"
    ),
) -> Dict[str, Any]:
    """查询审批列表，支持分页和状态筛选。

    可选 status 值: pending, approved, rejected, expired。
    """
    from src.services.approval_service import ApprovalService, ApprovalStatus
    from src.services.permission_service import UserRole
    
    lang = parse_accept_language(accept_language)
    
    # Validate and limit pagination parameters
    limit = min(limit, 100)
    if limit < 1:
        limit = 50
    if offset < 0:
        offset = 0
    
    # Validate status parameter if provided
    approval_status = None
    if status:
        try:
            approval_status = ApprovalStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=status_code.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error_code": "INVALID_STATUS",
                    "message": get_message("invalid_status", lang),
                    "valid_statuses": ["pending", "approved", "rejected", "expired"]
                }
            )
    
    # Determine user role
    if current_user.is_superuser:
        user_role = UserRole.ADMIN
    else:
        user_role = UserRole.USER
    
    # Create service instance
    service = ApprovalService(db)
    
    try:
        # Permission check: regular users can only see their own requests
        if user_role not in [UserRole.ADMIN, UserRole.DATA_MANAGER]:
            # Regular users can only query their own requests
            if user_id and user_id != str(current_user.id):
                raise HTTPException(
                    status_code=status_code.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "error_code": "PERMISSION_DENIED",
                        "message": get_message("permission_denied", lang),
                        "details": "Regular users can only view their own approval requests"
                    }
                )
            
            # Force user_id to current user for regular users
            approvals = service.get_user_approval_requests(
                user_id=str(current_user.id),
                status=approval_status,
                limit=limit,
                offset=offset
            )
        else:
            # Admin and data_manager can see all or filter by user_id
            if user_id:
                approvals = service.get_user_approval_requests(
                    user_id=user_id,
                    status=approval_status,
                    limit=limit,
                    offset=offset
                )
            else:
                approvals = service.get_pending_approvals(
                    limit=limit,
                    offset=offset
                )
                # Apply status filter if provided and not pending
                if approval_status and approval_status != ApprovalStatus.PENDING:
                    # For non-pending statuses, we need to query differently
                    # This is a limitation of the current service design
                    # For now, we'll get all user requests without user_id filter
                    from sqlalchemy import text
                    import json
                    
                    query = text("""
                        SELECT id, transfer_request, requester_id, requester_role,
                               status, created_at, expires_at, approver_id, approved_at, comment
                        FROM approval_requests
                        WHERE status = :status
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                    """)
                    
                    results = db.execute(query, {
                        "status": approval_status.value,
                        "limit": limit,
                        "offset": offset
                    }).fetchall()
                    
                    from src.models.data_transfer import DataTransferRequest
                    from src.models.approval import ApprovalRequest
                    
                    approvals = []
                    for result in results:
                        transfer_request_data = json.loads(result[1]) if isinstance(result[1], str) else result[1]
                        transfer_request = DataTransferRequest(**transfer_request_data)
                        
                        approval = ApprovalRequest(
                            id=result[0],
                            transfer_request=transfer_request,
                            requester_id=result[2],
                            requester_role=result[3],
                            status=ApprovalStatus(result[4]),
                            created_at=result[5],
                            expires_at=result[6],
                            approver_id=result[7],
                            approved_at=result[8],
                            comment=result[9]
                        )
                        approvals.append(approval)
        
        # Get total count for pagination metadata
        # Note: This is a simplified count, in production you'd want a separate count query
        total = len(approvals) if len(approvals) < limit else offset + len(approvals) + 1
        
        # Convert approvals to dict format
        approval_list = []
        for approval in approvals:
            approval_dict = {
                "id": approval.id,
                "requester_id": approval.requester_id,
                "requester_role": approval.requester_role,
                "status": approval.status.value,
                "created_at": approval.created_at.isoformat(),
                "expires_at": approval.expires_at.isoformat(),
                "approver_id": approval.approver_id,
                "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
                "comment": approval.comment,
                "transfer_request": {
                    "source_type": approval.transfer_request.source_type,
                    "source_id": approval.transfer_request.source_id,
                    "target_state": approval.transfer_request.target_state,
                    "record_count": len(approval.transfer_request.records)
                }
            }
            approval_list.append(approval_dict)
        
        return {
            "success": True,
            "approvals": approval_list,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": len(approvals) == limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing approvals: {e}", exc_info=True)
        raise HTTPException(
            status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": get_message("internal_error", lang),
                "details": str(e)
            }
        )


@router.post(
    "/approvals/{approval_id}/approve",
    summary="审批转存请求 / Approve or Reject Transfer",
    description=(
        "批准或拒绝一个转存审批请求。仅 data_manager 和 admin 角色可操作。\n\n"
        "Approve or reject a pending transfer approval request. "
        "Only data_manager and admin roles are allowed."
    ),
    status_code=status_code.HTTP_200_OK,
    response_model=ApprovalActionResponse,
    responses={
        400: {
            "description": "审批已过期或无效 / Approval expired or invalid",
            "content": {"application/json": {"example": {
                "success": False,
                "error_code": "APPROVAL_EXPIRED",
                "message": "审批请求已过期",
            }}},
        },
        403: _RESPONSE_403,
        404: _RESPONSE_404,
        500: _RESPONSE_500,
    },
)
async def approve_transfer(
    approval_id: str,
    approved: bool,
    comment: Optional[str] = None,
    db: Session = Depends(get_db_session),
    current_user: SimpleUser = Depends(get_current_user),
    accept_language: Optional[str] = Header(
        None, description="语言偏好，如 zh-CN 或 en-US"
    ),
) -> Dict[str, Any]:
    """审批或拒绝转存请求。

    approved=true 表示批准，approved=false 表示拒绝。
    可附带 comment 说明审批意见。
    """
    from src.services.approval_service import ApprovalService
    from src.services.permission_service import UserRole
    
    lang = parse_accept_language(accept_language)
    
    # Determine user role
    if current_user.is_superuser:
        user_role = UserRole.ADMIN
    else:
        user_role = UserRole.USER
    
    # Check approval permission
    if user_role not in [UserRole.ADMIN, UserRole.DATA_MANAGER]:
        logger.warning(
            f"User {current_user.id} with role {user_role.value} attempted to approve request"
        )
        raise HTTPException(
            status_code=status_code.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error_code": "PERMISSION_DENIED",
                "message": get_message("permission_denied", lang),
                "details": "Only admin or data_manager can approve requests"
            }
        )
    
    # Create service instance
    service = ApprovalService(db)
    
    try:
        # Process approval
        approval = await service.approve_request(
            approval_id=approval_id,
            approver_id=str(current_user.id),
            approver_role=user_role,
            approved=approved,
            comment=comment
        )
        
        # Build response
        approval_message_key = "approval_approved" if approved else "approval_rejected"
        return {
            "success": True,
            "approval": {
                "id": approval.id,
                "status": approval.status.value,
                "approver_id": approval.approver_id,
                "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
                "comment": approval.comment
            },
            "message": get_message(approval_message_key, lang)
        }
        
    except ValueError as e:
        # Invalid approval ID or expired approval
        error_msg = str(e)
        logger.warning(f"Approval validation error: {error_msg}")
        
        # Determine if it's a not found or expired error
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status_code.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error_code": "APPROVAL_NOT_FOUND",
                    "message": get_message("approval_not_found", lang, approval_id=approval_id),
                    "details": error_msg
                }
            )
        elif "expired" in error_msg.lower():
            raise HTTPException(
                status_code=status_code.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error_code": "APPROVAL_EXPIRED",
                    "message": get_message("approval_expired", lang),
                    "details": error_msg
                }
            )
        else:
            raise HTTPException(
                status_code=status_code.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error_code": "INVALID_APPROVAL",
                    "message": "Invalid approval request",
                    "details": error_msg
                }
            )
    
    except PermissionError as e:
        # Permission denied (shouldn't happen due to earlier check, but just in case)
        logger.warning(f"Approval permission error: {e}")
        raise HTTPException(
            status_code=status_code.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error_code": "PERMISSION_DENIED",
                "message": get_message("permission_denied", lang),
                "details": str(e)
            }
        )
    
    except Exception as e:
        # Internal server error
        logger.error(f"Approval internal error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": get_message("internal_error", lang),
                "details": str(e)
            }
        )


@router.get(
    "/permissions/check",
    summary="检查用户权限 / Check User Permissions",
    description=(
        "检查当前用户对指定数据操作的权限，返回是否允许及是否需要审批。"
        "前端可在操作前调用此接口以展示可用选项。\n\n"
        "Check the current user's permission for a specific data transfer "
        "operation. Useful for pre-flight checks in the UI."
    ),
    status_code=status_code.HTTP_200_OK,
    response_model=PermissionCheckResponse,
    responses={
        400: _RESPONSE_400,
        500: _RESPONSE_500,
    },
)
async def check_permissions(
    source_type: str,
    target_state: str,
    operation: str = "transfer",
    current_user: SimpleUser = Depends(get_current_user),
    accept_language: Optional[str] = Header(
        None, description="语言偏好，如 zh-CN 或 en-US"
    ),
) -> Dict[str, Any]:
    """检查用户对特定转存操作的权限。

    source_type: structuring, augmentation, sync, annotation, ai_assistant, manual。
    target_state: temp_stored, in_sample_library, annotation_pending。
    operation: transfer（默认）或 batch_transfer。
    """
    from src.services.permission_service import PermissionService, UserRole
    
    lang = parse_accept_language(accept_language)
    
    # Validate source_type
    valid_source_types = ["structuring", "augmentation", "sync", "annotation", "ai_assistant", "manual"]
    if source_type not in valid_source_types:
        raise HTTPException(
            status_code=status_code.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error_code": "INVALID_SOURCE_TYPE",
                "message": f"Invalid source_type: {source_type}",
                "valid_source_types": valid_source_types
            }
        )
    
    # Validate target_state
    valid_target_states = ["temp_stored", "in_sample_library", "annotation_pending"]
    if target_state not in valid_target_states:
        raise HTTPException(
            status_code=status_code.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error_code": "INVALID_TARGET_STATE",
                "message": f"Invalid target_state: {target_state}",
                "valid_target_states": valid_target_states
            }
        )
    
    # Validate operation
    valid_operations = ["transfer", "batch_transfer"]
    if operation not in valid_operations:
        raise HTTPException(
            status_code=status_code.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error_code": "INVALID_OPERATION",
                "message": f"Invalid operation: {operation}",
                "valid_operations": valid_operations
            }
        )
    
    try:
        # Determine user role
        if current_user.is_superuser:
            user_role = UserRole.ADMIN
        else:
            # Default to USER role for non-superusers
            # In production, this should be retrieved from a proper RBAC system
            user_role = UserRole.USER
        
        # Create permission service
        permission_service = PermissionService()
        
        # Determine record count based on operation type
        record_count = 1001 if operation == "batch_transfer" else 1
        
        # Check permission
        result = permission_service.check_permission(
            user_role=user_role,
            target_state=target_state,
            record_count=record_count,
            is_cross_project=False
        )
        
        # Build response
        response = {
            "allowed": result.allowed,
            "requires_approval": result.requires_approval,
            "user_role": result.current_role.value
        }
        
        # Add reason if not allowed or requires approval
        if not result.allowed:
            if result.reason:
                response["reason"] = result.reason
            else:
                response["reason"] = get_message("permission_denied", lang)
        elif result.requires_approval:
            response["reason"] = get_message("approval_required", lang)
        
        return response
        
    except Exception as e:
        logger.error(f"Permission check error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status_code.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": get_message("internal_error", lang),
                "details": str(e)
            }
        )


@router.post(
    "/batch-transfer",
    summary="批量数据转存 / Batch Data Transfer",
    description=(
        "批量转存多个数据源，需要 data_manager 或 admin 角色。"
        "每个请求独立处理，返回汇总结果。\n\n"
        "Batch transfer multiple data sources in a single request. "
        "Requires data_manager or admin role. Each transfer is processed "
        "independently with aggregated results."
    ),
    status_code=status_code.HTTP_200_OK,
    response_model=BatchTransferResponse,
    responses={
        403: _RESPONSE_403,
        500: _RESPONSE_500,
    },
)
async def batch_transfer_data(
    requests: list[DataTransferRequest],
    db: Session = Depends(get_db_session),
    current_user: SimpleUser = Depends(get_current_user),
    accept_language: Optional[str] = Header(
        None, description="语言偏好，如 zh-CN 或 en-US"
    ),
) -> Dict[str, Any]:
    """批量转存接口，一次提交多个转存请求。

    每个请求独立执行，部分失败不影响其他请求。
    返回汇总的成功/失败计数及各请求详细结果。
    """
    lang = parse_accept_language(accept_language)
    
    # Check batch transfer permission
    if not current_user.is_superuser:
        logger.warning(
            f"User {current_user.id} attempted batch transfer without permission"
        )
        raise HTTPException(
            status_code=status_code.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "error_code": "PERMISSION_DENIED",
                "message": get_message("permission_denied", lang),
                "details": "Batch transfer requires data_manager or admin role"
            }
        )
    
    # Create service instance
    service = DataTransferService(db)
    service_user = User(
        id=str(current_user.id),
        role=UserRole.ADMIN
    )
    
    # Security middleware for batch validation
    security_middleware = DataTransferSecurityMiddleware()
    
    # Process each transfer request
    results = []
    successful_count = 0
    failed_count = 0
    
    for idx, request in enumerate(requests):
        try:
            # Security check for each request
            await security_middleware.verify_no_privilege_escalation(
                request=request,
                current_user_id=str(current_user.id),
                current_user_role=UserRole.ADMIN
            )
            
            # Validate request integrity
            await security_middleware.validate_request_integrity(request)
            
            result = await service.transfer(request, service_user)
            
            # Internationalize success message
            if result.get("success") and not result.get("approval_required"):
                state_name = get_message(
                    f"states.{result['target_state']}",
                    lang
                )
                result["message"] = get_message(
                    "success",
                    lang,
                    count=result["transferred_count"],
                    state=state_name
                )
            elif result.get("approval_required"):
                result["message"] = get_message("approval_required", lang)
            
            results.append({
                "success": True,
                "index": idx,
                "source_id": request.source_id,
                **result
            })
            successful_count += 1
            
        except SecurityException as e:
            logger.error(f"Batch transfer security violation at index {idx}: {e}")
            results.append({
                "success": False,
                "index": idx,
                "source_id": request.source_id,
                "error_code": "SECURITY_VIOLATION",
                "message": "Security violation detected",
                "error": str(e)
            })
            failed_count += 1
            
        except ValueError as e:
            logger.warning(f"Batch transfer validation error at index {idx}: {e}")
            results.append({
                "success": False,
                "index": idx,
                "source_id": request.source_id,
                "error_code": "INVALID_SOURCE",
                "message": get_message("invalid_source", lang),
                "error": str(e)
            })
            failed_count += 1
            
        except PermissionError as e:
            logger.warning(f"Batch transfer permission error at index {idx}: {e}")
            results.append({
                "success": False,
                "index": idx,
                "source_id": request.source_id,
                "error_code": "PERMISSION_DENIED",
                "message": get_message("permission_denied", lang),
                "error": str(e)
            })
            failed_count += 1
            
        except Exception as e:
            logger.error(
                f"Batch transfer internal error at index {idx}: {e}",
                exc_info=True
            )
            results.append({
                "success": False,
                "index": idx,
                "source_id": request.source_id,
                "error_code": "INTERNAL_ERROR",
                "message": get_message("internal_error", lang),
                "error": str(e)
            })
            failed_count += 1
    
    return {
        "success": True,
        "total_transfers": len(requests),
        "successful_transfers": successful_count,
        "failed_transfers": failed_count,
        "results": results
    }
