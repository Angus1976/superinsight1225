"""
Multi-tenant API endpoints for tenant and workspace management.

This module provides REST API endpoints for managing tenants, workspaces,
and user associations in a multi-tenant environment.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.multi_tenant.services import (
    TenantManager, WorkspaceManager, UserTenantManager, UserWorkspaceManager,
    PermissionService, ResourceQuotaManager, TenantRole, WorkspaceRole
)
from src.multi_tenant.middleware import (
    get_tenant_context, get_tenant_aware_session,
    require_tenant_permission, require_workspace_permission
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["multi-tenant"])


# Pydantic models for request/response
class TenantCreateRequest(BaseModel):
    tenant_id: str = Field(..., description="Unique tenant identifier")
    name: str = Field(..., description="Tenant name")
    display_name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Tenant description")
    max_users: int = Field(100, description="Maximum number of users")
    max_workspaces: int = Field(10, description="Maximum number of workspaces")
    max_storage_gb: float = Field(100.0, description="Maximum storage in GB")
    max_api_calls_per_hour: int = Field(10000, description="Maximum API calls per hour")
    billing_email: Optional[str] = Field(None, description="Billing contact email")
    billing_plan: str = Field("basic", description="Billing plan")


class TenantResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    status: str
    max_users: int
    max_workspaces: int
    max_storage_gb: float
    current_users: int
    current_workspaces: int
    current_storage_gb: float
    billing_plan: str
    created_at: str
    updated_at: str


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., description="Workspace name")
    display_name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Workspace description")
    configuration: Optional[Dict[str, Any]] = Field({}, description="Workspace configuration")


class WorkspaceResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    display_name: str
    description: Optional[str]
    status: str
    is_default: bool
    created_at: str
    updated_at: str


class UserTenantInviteRequest(BaseModel):
    user_id: str = Field(..., description="User ID to invite")
    role: str = Field("member", description="Role to assign")
    is_default_tenant: bool = Field(False, description="Set as default tenant")


class UserWorkspaceAssignRequest(BaseModel):
    user_id: str = Field(..., description="User ID to assign")
    role: str = Field("annotator", description="Role to assign")


class TenantUsageResponse(BaseModel):
    tenant_id: str
    current_users: int
    current_workspaces: int
    current_storage_gb: float
    max_users: int
    max_workspaces: int
    max_storage_gb: float
    usage_stats: Dict[str, Any]


# Tenant Management Endpoints

@router.post("/tenants", response_model=TenantResponse)
@require_tenant_permission("admin")  # Only admins can create tenants
async def create_tenant(
    request: Request,
    tenant_data: TenantCreateRequest,
    session: Session = Depends(get_db_session)
):
    """Create a new tenant (admin only)."""
    try:
        tenant_manager = TenantManager(session)
        tenant = tenant_manager.create_tenant(
            tenant_id=tenant_data.tenant_id,
            name=tenant_data.name,
            display_name=tenant_data.display_name,
            description=tenant_data.description,
            max_users=tenant_data.max_users,
            max_workspaces=tenant_data.max_workspaces,
            max_storage_gb=tenant_data.max_storage_gb,
            max_api_calls_per_hour=tenant_data.max_api_calls_per_hour,
            billing_email=tenant_data.billing_email,
            billing_plan=tenant_data.billing_plan
        )
        
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            display_name=tenant.display_name,
            description=tenant.description,
            status=tenant.status.value,
            max_users=tenant.max_users,
            max_workspaces=tenant.max_workspaces,
            max_storage_gb=tenant.max_storage_gb,
            current_users=tenant.current_users,
            current_workspaces=tenant.current_workspaces,
            current_storage_gb=tenant.current_storage_gb,
            billing_plan=tenant.billing_plan,
            created_at=tenant.created_at.isoformat(),
            updated_at=tenant.updated_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating tenant: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create tenant")


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
@require_tenant_permission("member")
async def get_tenant(
    request: Request,
    tenant_id: str,
    session: Session = Depends(get_db_session)
):
    """Get tenant details."""
    tenant_manager = TenantManager(session)
    tenant = tenant_manager.get_tenant(tenant_id)
    
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        display_name=tenant.display_name,
        description=tenant.description,
        status=tenant.status.value,
        max_users=tenant.max_users,
        max_workspaces=tenant.max_workspaces,
        max_storage_gb=tenant.max_storage_gb,
        current_users=tenant.current_users,
        current_workspaces=tenant.current_workspaces,
        current_storage_gb=tenant.current_storage_gb,
        billing_plan=tenant.billing_plan,
        created_at=tenant.created_at.isoformat(),
        updated_at=tenant.updated_at.isoformat()
    )


@router.get("/tenants/{tenant_id}/usage", response_model=TenantUsageResponse)
@require_tenant_permission("member")
async def get_tenant_usage(
    request: Request,
    tenant_id: str,
    session: Session = Depends(get_db_session)
):
    """Get tenant resource usage."""
    tenant_manager = TenantManager(session)
    usage = tenant_manager.get_tenant_usage(tenant_id)
    
    if not usage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    
    return TenantUsageResponse(**usage)


# Workspace Management Endpoints

@router.post("/tenants/{tenant_id}/workspaces", response_model=WorkspaceResponse)
@require_tenant_permission("admin")
async def create_workspace(
    request: Request,
    tenant_id: str,
    workspace_data: WorkspaceCreateRequest,
    session: Session = Depends(get_db_session)
):
    """Create a new workspace within a tenant."""
    try:
        workspace_manager = WorkspaceManager(session)
        workspace = workspace_manager.create_workspace(
            tenant_id=tenant_id,
            name=workspace_data.name,
            display_name=workspace_data.display_name,
            description=workspace_data.description,
            configuration=workspace_data.configuration
        )
        
        return WorkspaceResponse(
            id=str(workspace.id),
            tenant_id=workspace.tenant_id,
            name=workspace.name,
            display_name=workspace.display_name,
            description=workspace.description,
            status=workspace.status.value,
            is_default=workspace.is_default,
            created_at=workspace.created_at.isoformat(),
            updated_at=workspace.updated_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create workspace")


@router.get("/tenants/{tenant_id}/workspaces", response_model=List[WorkspaceResponse])
@require_tenant_permission("member")
async def list_workspaces(
    request: Request,
    tenant_id: str,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_db_session)
):
    """List workspaces within a tenant."""
    workspace_manager = WorkspaceManager(session)
    workspaces = workspace_manager.list_workspaces(tenant_id, limit=limit, offset=offset)
    
    return [
        WorkspaceResponse(
            id=str(workspace.id),
            tenant_id=workspace.tenant_id,
            name=workspace.name,
            display_name=workspace.display_name,
            description=workspace.description,
            status=workspace.status.value,
            is_default=workspace.is_default,
            created_at=workspace.created_at.isoformat(),
            updated_at=workspace.updated_at.isoformat()
        )
        for workspace in workspaces
    ]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
@require_workspace_permission("viewer")
async def get_workspace(
    request: Request,
    workspace_id: UUID,
    session: Session = Depends(get_db_session)
):
    """Get workspace details."""
    workspace_manager = WorkspaceManager(session)
    workspace = workspace_manager.get_workspace(workspace_id)
    
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    
    return WorkspaceResponse(
        id=str(workspace.id),
        tenant_id=workspace.tenant_id,
        name=workspace.name,
        display_name=workspace.display_name,
        description=workspace.description,
        status=workspace.status.value,
        is_default=workspace.is_default,
        created_at=workspace.created_at.isoformat(),
        updated_at=workspace.updated_at.isoformat()
    )


# User Management Endpoints

@router.post("/tenants/{tenant_id}/users")
@require_tenant_permission("admin")
async def invite_user_to_tenant(
    request: Request,
    tenant_id: str,
    invite_data: UserTenantInviteRequest,
    session: Session = Depends(get_db_session)
):
    """Invite a user to a tenant."""
    try:
        user_tenant_manager = UserTenantManager(session)
        
        # Map role string to enum
        role_map = {
            "viewer": TenantRole.VIEWER,
            "member": TenantRole.MEMBER,
            "admin": TenantRole.ADMIN,
            "owner": TenantRole.OWNER
        }
        role = role_map.get(invite_data.role.lower(), TenantRole.MEMBER)
        
        context = get_tenant_context(request)
        invited_by = context.get("user_id")
        
        association = user_tenant_manager.invite_user_to_tenant(
            user_id=UUID(invite_data.user_id),
            tenant_id=tenant_id,
            role=role,
            invited_by=invited_by,
            is_default_tenant=invite_data.is_default_tenant
        )
        
        return {
            "message": "User invited successfully",
            "user_id": str(association.user_id),
            "tenant_id": association.tenant_id,
            "role": association.role.value
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error inviting user to tenant: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to invite user")


@router.post("/workspaces/{workspace_id}/users")
@require_workspace_permission("admin")
async def assign_user_to_workspace(
    request: Request,
    workspace_id: UUID,
    assign_data: UserWorkspaceAssignRequest,
    session: Session = Depends(get_db_session)
):
    """Assign a user to a workspace."""
    try:
        user_workspace_manager = UserWorkspaceManager(session)
        
        # Map role string to enum
        role_map = {
            "viewer": WorkspaceRole.VIEWER,
            "annotator": WorkspaceRole.ANNOTATOR,
            "reviewer": WorkspaceRole.REVIEWER,
            "admin": WorkspaceRole.ADMIN
        }
        role = role_map.get(assign_data.role.lower(), WorkspaceRole.ANNOTATOR)
        
        association = user_workspace_manager.add_user_to_workspace(
            user_id=UUID(assign_data.user_id),
            workspace_id=workspace_id,
            role=role
        )
        
        return {
            "message": "User assigned successfully",
            "user_id": str(association.user_id),
            "workspace_id": str(association.workspace_id),
            "role": association.role.value
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning user to workspace: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign user")


# Context and Permission Endpoints

@router.get("/auth/context")
async def get_user_context(
    request: Request,
    session: Session = Depends(get_db_session)
):
    """Get current user's tenant and workspace context."""
    context = get_tenant_context(request)
    user_id = context.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    permission_service = PermissionService(session)
    user_context = permission_service.get_user_context(user_id)
    
    return {
        "current_context": context,
        "user_context": user_context
    }


@router.post("/auth/switch-tenant")
async def switch_tenant(
    request: Request,
    tenant_id: str,
    workspace_id: Optional[str] = None,
    session: Session = Depends(get_db_session)
):
    """Switch user's current tenant context."""
    context = get_tenant_context(request)
    user_id = context.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    # Validate user has access to the tenant
    permission_service = PermissionService(session)
    if not permission_service.has_tenant_permission(user_id, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to tenant"
        )
    
    # Validate workspace if provided
    if workspace_id:
        workspace_uuid = UUID(workspace_id)
        if not permission_service.can_access_workspace(user_id, workspace_uuid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to workspace"
            )
    
    return {
        "message": "Tenant context switched successfully",
        "tenant_id": tenant_id,
        "workspace_id": workspace_id
    }


@router.get("/auth/available-tenants")
async def get_available_tenants(
    request: Request,
    session: Session = Depends(get_db_session)
):
    """Get list of tenants available to the current user."""
    context = get_tenant_context(request)
    user_id = context.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    user_tenant_manager = UserTenantManager(session)
    associations = user_tenant_manager.get_user_tenants(user_id)
    
    return [
        {
            "tenant_id": assoc.tenant_id,
            "role": assoc.role.value,
            "is_default": assoc.is_default_tenant,
            "tenant_name": assoc.tenant.display_name if assoc.tenant else assoc.tenant_id
        }
        for assoc in associations
    ]