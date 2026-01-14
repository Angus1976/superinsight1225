"""
Data Permission API Router for SuperInsight Platform.

Provides REST API endpoints for data permission management.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.security.data_permission_engine import get_data_permission_engine, DataPermissionEngine
from src.schemas.data_permission import (
    PermissionCheckRequest, PermissionResult, GrantPermissionRequest,
    RevokePermissionRequest, DataPermissionResponse, TemporaryGrant,
    DataPermissionAction
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data-permissions", tags=["Data Permissions"])


def get_permission_engine() -> DataPermissionEngine:
    """Dependency to get permission engine."""
    return get_data_permission_engine()


def get_current_user_id() -> UUID:
    """Placeholder for getting current user ID from auth context."""
    # In production, this would extract from JWT token
    return UUID("00000000-0000-0000-0000-000000000001")


def get_current_tenant_id() -> str:
    """Placeholder for getting current tenant ID from auth context."""
    # In production, this would extract from JWT token or request context
    return "default"


# ============================================================================
# Permission Check Endpoints
# ============================================================================

@router.post("/check", response_model=PermissionResult)
async def check_permission(
    request: PermissionCheckRequest,
    db: Session = Depends(get_db),
    engine: DataPermissionEngine = Depends(get_permission_engine),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Check if user has permission for a resource.
    
    Supports dataset, record, and field level permission checks.
    """
    try:
        # Determine check type based on request
        if request.field_name:
            result = await engine.check_field_permission(
                user_id=str(request.user_id),
                dataset_id=request.resource_id,
                field_name=request.field_name,
                action=request.action.value,
                tenant_id=tenant_id,
                db=db
            )
        else:
            result = await engine.check_dataset_permission(
                user_id=str(request.user_id),
                dataset_id=request.resource_id,
                action=request.action.value,
                tenant_id=tenant_id,
                db=db
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Permission check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Permission check failed: {str(e)}"
        )


@router.post("/check/record", response_model=PermissionResult)
async def check_record_permission(
    user_id: UUID,
    dataset_id: str,
    record_id: str,
    action: DataPermissionAction,
    db: Session = Depends(get_db),
    engine: DataPermissionEngine = Depends(get_permission_engine),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Check record-level (row-level) permission."""
    try:
        result = await engine.check_record_permission(
            user_id=str(user_id),
            dataset_id=dataset_id,
            record_id=record_id,
            action=action.value,
            tenant_id=tenant_id,
            db=db
        )
        return result
        
    except Exception as e:
        logger.error(f"Record permission check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Permission check failed: {str(e)}"
        )


@router.post("/check/tags", response_model=PermissionResult)
async def check_tag_permission(
    user_id: UUID,
    tags: List[str],
    action: DataPermissionAction,
    db: Session = Depends(get_db),
    engine: DataPermissionEngine = Depends(get_permission_engine),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """Check tag-based (ABAC) permission."""
    try:
        result = await engine.check_tag_based_permission(
            user_id=str(user_id),
            resource_tags=tags,
            action=action.value,
            tenant_id=tenant_id,
            db=db
        )
        return result
        
    except Exception as e:
        logger.error(f"Tag permission check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Permission check failed: {str(e)}"
        )


# ============================================================================
# Permission Grant/Revoke Endpoints
# ============================================================================

@router.post("/grant", response_model=DataPermissionResponse)
async def grant_permission(
    request: GrantPermissionRequest,
    db: Session = Depends(get_db),
    engine: DataPermissionEngine = Depends(get_permission_engine),
    current_user: UUID = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Grant a permission to a user or role.
    
    Supports dataset, record, and field level permissions.
    """
    try:
        if not request.user_id and not request.role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either user_id or role_id must be provided"
            )
        
        permission = await engine.grant_permission(
            request=request,
            tenant_id=tenant_id,
            granted_by=current_user,
            db=db
        )
        
        return DataPermissionResponse.model_validate(permission)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Grant permission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grant permission failed: {str(e)}"
        )


@router.post("/grant/temporary", response_model=TemporaryGrant)
async def grant_temporary_permission(
    user_id: UUID,
    resource: str,
    action: DataPermissionAction,
    expires_at: datetime,
    db: Session = Depends(get_db),
    engine: DataPermissionEngine = Depends(get_permission_engine),
    current_user: UUID = Depends(get_current_user_id),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Grant a temporary permission that expires automatically.
    """
    try:
        if expires_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expiration time must be in the future"
            )
        
        grant = await engine.grant_temporary_permission(
            user_id=str(user_id),
            resource=resource,
            action=action.value,
            expires_at=expires_at,
            tenant_id=tenant_id,
            granted_by=current_user,
            db=db
        )
        
        return grant
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Grant temporary permission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grant temporary permission failed: {str(e)}"
        )


@router.post("/revoke")
async def revoke_permission(
    request: RevokePermissionRequest,
    db: Session = Depends(get_db),
    engine: DataPermissionEngine = Depends(get_permission_engine),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Revoke a permission from a user or role.
    """
    try:
        if not request.user_id and not request.role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either user_id or role_id must be provided"
            )
        
        success = await engine.revoke_permission(
            user_id=str(request.user_id) if request.user_id else None,
            role_id=str(request.role_id) if request.role_id else None,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            action=request.action.value,
            tenant_id=tenant_id,
            db=db,
            field_name=request.field_name
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        return {"success": True, "message": "Permission revoked"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Revoke permission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Revoke permission failed: {str(e)}"
        )


# ============================================================================
# Permission Query Endpoints
# ============================================================================

@router.get("/user/{user_id}", response_model=List[DataPermissionResponse])
async def get_user_permissions(
    user_id: UUID,
    resource_type: Optional[str] = None,
    include_role_permissions: bool = True,
    db: Session = Depends(get_db),
    engine: DataPermissionEngine = Depends(get_permission_engine),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Get all permissions for a user.
    """
    try:
        permissions = await engine.get_user_permissions(
            user_id=str(user_id),
            tenant_id=tenant_id,
            db=db,
            resource_type=resource_type,
            include_role_permissions=include_role_permissions
        )
        
        return [DataPermissionResponse.model_validate(p) for p in permissions]
        
    except Exception as e:
        logger.error(f"Get user permissions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get user permissions failed: {str(e)}"
        )


@router.get("/resource/{resource_type}/{resource_id}", response_model=List[DataPermissionResponse])
async def get_resource_permissions(
    resource_type: str,
    resource_id: str,
    db: Session = Depends(get_db),
    engine: DataPermissionEngine = Depends(get_permission_engine),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Get all permissions for a resource.
    """
    try:
        permissions = await engine.get_resource_permissions(
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            db=db
        )
        
        return [DataPermissionResponse.model_validate(p) for p in permissions]
        
    except Exception as e:
        logger.error(f"Get resource permissions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get resource permissions failed: {str(e)}"
        )


# ============================================================================
# Cache Management Endpoints
# ============================================================================

@router.post("/cache/invalidate")
async def invalidate_cache(
    engine: DataPermissionEngine = Depends(get_permission_engine)
):
    """
    Invalidate all permission cache entries.
    
    Admin only endpoint.
    """
    try:
        count = engine.invalidate_all_cache()
        return {"success": True, "invalidated_count": count}
        
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache invalidation failed: {str(e)}"
        )


@router.get("/cache/stats")
async def get_cache_stats(
    engine: DataPermissionEngine = Depends(get_permission_engine)
):
    """
    Get permission cache statistics.
    
    Admin only endpoint.
    """
    try:
        return engine.get_cache_stats()
        
    except Exception as e:
        logger.error(f"Get cache stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get cache stats failed: {str(e)}"
        )
