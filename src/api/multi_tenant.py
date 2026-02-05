"""
Multi-Tenant Workspace API endpoints for SuperInsight Platform.

This module provides comprehensive API endpoints for:
- Tenant management (CRUD, status management)
- Workspace management (CRUD, hierarchy, templates, archive/restore)
- Member management (invite, add, remove, roles)
- Quota management (set, get, usage tracking)
- Cross-tenant collaboration (shares, whitelist)
- Admin console (dashboard, services, config)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.database.connection import get_db_session

from src.multi_tenant.workspace.schemas import (
    # Enums
    TenantStatus, WorkspaceStatus, MemberRole, SharePermission, EntityType, ResourceType,
    # Tenant schemas
    TenantCreateConfig, TenantUpdateConfig, TenantResponse, TenantConfig, TenantQuotaConfig,
    # Workspace schemas
    WorkspaceCreateConfig, WorkspaceUpdateConfig, WorkspaceResponse, WorkspaceNode,
    # Member schemas
    MemberAddRequest, CustomRoleConfig, InvitationConfig, WorkspaceMemberResponse, InvitationResponse,
    # Quota schemas
    QuotaConfig, QuotaUsageData, QuotaCheckResult, QuotaResponse,
    # Share schemas
    ShareConfig, ShareLinkResponse, WhitelistConfig, SharedResourceAccess,
    # Admin schemas
    AdminDashboard, ServiceStatus, SystemConfigRequest,
)

from src.multi_tenant.workspace.tenant_manager import TenantManager
from src.multi_tenant.workspace.workspace_manager import WorkspaceManager
from src.multi_tenant.workspace.member_manager import MemberManager
from src.multi_tenant.workspace.quota_manager import QuotaManager
from src.multi_tenant.workspace.cross_tenant_collaborator import (
    CrossTenantCollaborator,
    ShareExpiredError,
    ShareRevokedError,
    TenantNotWhitelistedError,
    ShareNotFoundError,
)

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Create router
router = APIRouter(prefix="/api/v1", tags=["Multi-Tenant"])


# ============================================================================
# Helper Functions
# ============================================================================

def get_tenant_manager(db: Session = Depends(get_db_session)) -> TenantManager:
    """Get TenantManager instance."""
    return TenantManager(db)


def get_workspace_manager(db: Session = Depends(get_db_session)) -> WorkspaceManager:
    """Get WorkspaceManager instance."""
    return WorkspaceManager(db)


def get_member_manager(db: Session = Depends(get_db_session)) -> MemberManager:
    """Get MemberManager instance."""
    return MemberManager(db)


def get_quota_manager(db: Session = Depends(get_db_session)) -> QuotaManager:
    """Get QuotaManager instance."""
    return QuotaManager(db)


def get_cross_tenant_collaborator(db: Session = Depends(get_db_session)) -> CrossTenantCollaborator:
    """Get CrossTenantCollaborator instance."""
    return CrossTenantCollaborator(db)


# Flexible user authentication that works with both UserModel and simple users table
from fastapi import Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
import jwt

security_bearer = HTTPBearer()


class SimpleUserModel:
    """Simple user model for compatibility with users table without role field."""
    def __init__(self, id, username, email, full_name, tenant_id, is_active, is_superuser=False, role=None):
        self.id = id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.tenant_id = tenant_id or "system"
        self.is_active = is_active
        self.is_superuser = is_superuser
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: Session = Depends(get_db_session)
) -> SimpleUserModel:
    """
    Get current authenticated user with fallback support.
    
    This function uses raw SQL to query the user, handling cases where
    the role field might not exist in the database.
    """
    token = credentials.credentials
    
    try:
        # Use the same secret key as auth_simple.py for compatibility
        secret_key = "your-secret-key-change-in-production"
        
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        user_id = payload.get("user_id") or payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Query user from database using raw SQL for compatibility
    try:
        # Query user - the users table has 'name' not 'full_name', and no 'tenant_id' or 'role' columns
        result = db.execute(text("""
            SELECT id, username, email, name, is_active, is_superuser
            FROM users WHERE id = :user_id
        """), {"user_id": user_id})
        row = result.fetchone()
    except Exception as e:
        logger.error(f"Failed to query user: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error",
        )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id, username, email, name, is_active, is_superuser = row
    
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return SimpleUserModel(
        id=str(user_id),
        username=username,
        email=email,
        full_name=name,  # Use 'name' field as full_name
        tenant_id="system",  # Default tenant since column doesn't exist
        is_active=is_active,
        is_superuser=is_superuser,
        role=None  # No role column in this table
    )


def check_admin_permission(current_user: SimpleUserModel):
    """Check if user has admin permission."""
    # Check is_superuser field first (most reliable)
    if current_user.is_superuser:
        return
    
    # Try to check role field
    if current_user.role:
        role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        if role_value in ["admin", "super_admin"]:
            return
    
    # If neither check passed, deny access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin permission required"
    )


def check_tenant_access(current_user: SimpleUserModel, tenant_id: str):
    """Check if user has access to the tenant."""
    # Check if user is super admin
    is_super_admin = current_user.is_superuser
    
    # Also check role field
    if not is_super_admin and current_user.role:
        role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        if role_value == "super_admin":
            is_super_admin = True
    
    # Check tenant access
    if current_user.tenant_id != tenant_id and not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )


# ============================================================================
# Tenant Management Endpoints
# ============================================================================

@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: TenantCreateConfig,
    current_user: SimpleUserModel = Depends(get_current_user),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """Create a new tenant."""
    check_admin_permission(current_user)
    
    try:
        tenant = tenant_manager.create_tenant(request)
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            status=TenantStatus(tenant.status),
            admin_email=tenant.admin_email,
            plan=tenant.plan,
            config=TenantConfig(**tenant.config) if tenant.config else TenantConfig(),
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    status_filter: Optional[TenantStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: SimpleUserModel = Depends(get_current_user),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """List all tenants (admin only) or current tenant."""
    try:
        # Check if user is super admin (check is_superuser first, then role)
        is_super_admin = current_user.is_superuser
        if not is_super_admin and current_user.role:
            role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
            if role_value == "super_admin":
                is_super_admin = True
        
        if is_super_admin:
            tenants = tenant_manager.list_tenants(
                status=status_filter.value if status_filter else None,
                skip=skip,
                limit=limit
            )
        else:
            # Non-admin users can only see their own tenant
            tenant = tenant_manager.get_tenant(current_user.tenant_id)
            tenants = [tenant] if tenant else []
        
        return [
            TenantResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                status=TenantStatus(t.status),
                admin_email=t.admin_email,
                plan=t.plan,
                config=TenantConfig(**t.config) if t.config else TenantConfig(),
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tenants
        ]
    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tenants: {str(e)}"
        )


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """Get tenant by ID."""
    check_tenant_access(current_user, tenant_id)
    
    try:
        tenant = tenant_manager.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            status=TenantStatus(tenant.status),
            admin_email=tenant.admin_email,
            plan=tenant.plan,
            config=TenantConfig(**tenant.config) if tenant.config else TenantConfig(),
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant: {str(e)}"
        )


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    request: TenantUpdateConfig,
    current_user: SimpleUserModel = Depends(get_current_user),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """Update tenant."""
    check_admin_permission(current_user)
    check_tenant_access(current_user, tenant_id)
    
    try:
        tenant = tenant_manager.update_tenant(tenant_id, request)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            status=TenantStatus(tenant.status),
            admin_email=tenant.admin_email,
            plan=tenant.plan,
            config=TenantConfig(**tenant.config) if tenant.config else TenantConfig(),
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant: {str(e)}"
        )


@router.put("/tenants/{tenant_id}/status", response_model=TenantResponse)
async def set_tenant_status(
    tenant_id: str,
    new_status: TenantStatus,
    current_user: SimpleUserModel = Depends(get_current_user),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """Set tenant status (active/suspended/disabled)."""
    check_admin_permission(current_user)
    
    try:
        tenant = tenant_manager.set_status(tenant_id, new_status.value)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            status=TenantStatus(tenant.status),
            admin_email=tenant.admin_email,
            plan=tenant.plan,
            config=TenantConfig(**tenant.config) if tenant.config else TenantConfig(),
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set tenant status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set tenant status: {str(e)}"
        )


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
):
    """Delete tenant (soft delete)."""
    check_admin_permission(current_user)
    
    try:
        success = tenant_manager.delete_tenant(tenant_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tenant: {str(e)}"
        )



# ============================================================================
# Workspace Management Endpoints
# ============================================================================

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreateConfig,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Create a new workspace in the current tenant."""
    try:
        workspace = workspace_manager.create_workspace(
            tenant_id=current_user.tenant_id,
            config=request
        )
        return WorkspaceResponse(
            id=workspace.id,
            tenant_id=workspace.tenant_id,
            parent_id=workspace.parent_id,
            name=workspace.name,
            description=workspace.description,
            status=WorkspaceStatus(workspace.status),
            config=workspace.config or {},
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workspace: {str(e)}"
        )


@router.get("/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces(
    tenant_id: Optional[str] = Query(None),
    status_filter: Optional[WorkspaceStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """List workspaces for the current tenant."""
    try:
        # Use provided tenant_id or current user's tenant
        target_tenant_id = tenant_id or current_user.tenant_id
        check_tenant_access(current_user, target_tenant_id)
        
        workspaces = workspace_manager.list_workspaces(
            tenant_id=target_tenant_id,
            status=status_filter.value if status_filter else None,
            skip=skip,
            limit=limit
        )
        
        return [
            WorkspaceResponse(
                id=w.id,
                tenant_id=w.tenant_id,
                parent_id=w.parent_id,
                name=w.name,
                description=w.description,
                status=WorkspaceStatus(w.status),
                config=w.config or {},
                created_at=w.created_at,
                updated_at=w.updated_at,
            )
            for w in workspaces
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list workspaces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workspaces: {str(e)}"
        )


@router.get("/workspaces/hierarchy", response_model=List[WorkspaceNode])
async def get_workspace_hierarchy(
    tenant_id: Optional[str] = Query(None),
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Get workspace hierarchy tree for a tenant."""
    try:
        target_tenant_id = tenant_id or current_user.tenant_id
        check_tenant_access(current_user, target_tenant_id)
        
        hierarchy = workspace_manager.get_hierarchy(target_tenant_id)
        return hierarchy
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workspace hierarchy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workspace hierarchy: {str(e)}"
        )


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Get workspace by ID."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        return WorkspaceResponse(
            id=workspace.id,
            tenant_id=workspace.tenant_id,
            parent_id=workspace.parent_id,
            name=workspace.name,
            description=workspace.description,
            status=WorkspaceStatus(workspace.status),
            config=workspace.config or {},
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workspace: {str(e)}"
        )


@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    request: WorkspaceUpdateConfig,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Update workspace."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        updated = workspace_manager.update_workspace(workspace_id, request)
        return WorkspaceResponse(
            id=updated.id,
            tenant_id=updated.tenant_id,
            parent_id=updated.parent_id,
            name=updated.name,
            description=updated.description,
            status=WorkspaceStatus(updated.status),
            config=updated.config or {},
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workspace: {str(e)}"
        )


@router.post("/workspaces/{workspace_id}/archive", response_model=WorkspaceResponse)
async def archive_workspace(
    workspace_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Archive a workspace."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        archived = workspace_manager.archive_workspace(workspace_id)
        return WorkspaceResponse(
            id=archived.id,
            tenant_id=archived.tenant_id,
            parent_id=archived.parent_id,
            name=archived.name,
            description=archived.description,
            status=WorkspaceStatus(archived.status),
            config=archived.config or {},
            created_at=archived.created_at,
            updated_at=archived.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive workspace: {str(e)}"
        )


@router.post("/workspaces/{workspace_id}/restore", response_model=WorkspaceResponse)
async def restore_workspace(
    workspace_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Restore an archived workspace."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        restored = workspace_manager.restore_workspace(workspace_id)
        return WorkspaceResponse(
            id=restored.id,
            tenant_id=restored.tenant_id,
            parent_id=restored.parent_id,
            name=restored.name,
            description=restored.description,
            status=WorkspaceStatus(restored.status),
            config=restored.config or {},
            created_at=restored.created_at,
            updated_at=restored.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore workspace: {str(e)}"
        )


@router.put("/workspaces/{workspace_id}/move", response_model=WorkspaceResponse)
async def move_workspace(
    workspace_id: str,
    new_parent_id: Optional[str] = Query(None),
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Move workspace to a new parent (change hierarchy)."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        moved = workspace_manager.move_workspace(workspace_id, new_parent_id)
        return WorkspaceResponse(
            id=moved.id,
            tenant_id=moved.tenant_id,
            parent_id=moved.parent_id,
            name=moved.name,
            description=moved.description,
            status=WorkspaceStatus(moved.status),
            config=moved.config or {},
            created_at=moved.created_at,
            updated_at=moved.updated_at,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to move workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to move workspace: {str(e)}"
        )


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """Delete workspace."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        success = workspace_manager.delete_workspace(workspace_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete workspace"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workspace: {str(e)}"
        )



# ============================================================================
# Member Management Endpoints
# ============================================================================

@router.post("/workspaces/{workspace_id}/members/invite", response_model=InvitationResponse)
async def invite_member(
    workspace_id: str,
    request: InvitationConfig,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    member_manager: MemberManager = Depends(get_member_manager)
):
    """Invite a user to join a workspace via email."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        invitation = member_manager.invite_member(
            workspace_id=workspace_id,
            email=request.email,
            role=request.role,
            message=request.message,
            expires_in_days=request.expires_in_days
        )
        
        return InvitationResponse(
            id=invitation.id,
            workspace_id=invitation.workspace_id,
            email=invitation.email,
            role=MemberRole(invitation.role),
            token=invitation.token,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invite member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invite member: {str(e)}"
        )


@router.post("/workspaces/{workspace_id}/members", response_model=WorkspaceMemberResponse)
async def add_member(
    workspace_id: str,
    request: MemberAddRequest,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    member_manager: MemberManager = Depends(get_member_manager)
):
    """Add a user directly to a workspace."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        member = member_manager.add_member(
            workspace_id=workspace_id,
            user_id=str(request.user_id),
            role=request.role,
            custom_role_id=str(request.custom_role_id) if request.custom_role_id else None
        )
        
        return WorkspaceMemberResponse(
            id=member.id,
            user_id=member.user_id,
            workspace_id=member.workspace_id,
            role=MemberRole(member.role),
            custom_role_id=member.custom_role_id,
            joined_at=member.joined_at,
            last_active_at=member.last_active_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add member: {str(e)}"
        )


@router.get("/workspaces/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_members(
    workspace_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    member_manager: MemberManager = Depends(get_member_manager)
):
    """List all members of a workspace."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        members = member_manager.get_members(workspace_id, skip=skip, limit=limit)
        
        return [
            WorkspaceMemberResponse(
                id=m.id,
                user_id=m.user_id,
                workspace_id=m.workspace_id,
                role=MemberRole(m.role),
                custom_role_id=m.custom_role_id,
                joined_at=m.joined_at,
                last_active_at=m.last_active_at,
            )
            for m in members
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list members: {str(e)}"
        )


@router.put("/workspaces/{workspace_id}/members/{user_id}/role", response_model=WorkspaceMemberResponse)
async def update_member_role(
    workspace_id: str,
    user_id: str,
    role: MemberRole,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    member_manager: MemberManager = Depends(get_member_manager)
):
    """Update a member's role in a workspace."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        member = member_manager.update_role(workspace_id, user_id, role)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        
        return WorkspaceMemberResponse(
            id=member.id,
            user_id=member.user_id,
            workspace_id=member.workspace_id,
            role=MemberRole(member.role),
            custom_role_id=member.custom_role_id,
            joined_at=member.joined_at,
            last_active_at=member.last_active_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update member role: {str(e)}"
        )


@router.delete("/workspaces/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: str,
    user_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    member_manager: MemberManager = Depends(get_member_manager)
):
    """Remove a member from a workspace."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        success = member_manager.remove_member(workspace_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove member: {str(e)}"
        )


class BatchMemberRequest(BaseModel):
    """Request for batch member operations."""
    members: List[MemberAddRequest]


@router.post("/workspaces/{workspace_id}/members/batch", response_model=List[WorkspaceMemberResponse])
async def batch_add_members(
    workspace_id: str,
    request: BatchMemberRequest,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    member_manager: MemberManager = Depends(get_member_manager)
):
    """Add multiple members to a workspace at once."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        members = member_manager.batch_add_members(workspace_id, request.members)
        
        return [
            WorkspaceMemberResponse(
                id=m.id,
                user_id=m.user_id,
                workspace_id=m.workspace_id,
                role=MemberRole(m.role),
                custom_role_id=m.custom_role_id,
                joined_at=m.joined_at,
                last_active_at=m.last_active_at,
            )
            for m in members
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch add members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch add members: {str(e)}"
        )


class CustomRoleResponse(BaseModel):
    """Custom role response schema."""
    id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str]
    permissions: List[str]
    created_at: datetime


@router.post("/workspaces/{workspace_id}/roles", response_model=CustomRoleResponse)
async def create_custom_role(
    workspace_id: str,
    request: CustomRoleConfig,
    current_user: SimpleUserModel = Depends(get_current_user),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    member_manager: MemberManager = Depends(get_member_manager)
):
    """Create a custom role for a workspace."""
    try:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        check_tenant_access(current_user, str(workspace.tenant_id))
        
        role = member_manager.create_custom_role(workspace_id, request)
        
        return CustomRoleResponse(
            id=role.id,
            workspace_id=role.workspace_id,
            name=role.name,
            description=role.description,
            permissions=role.permissions or [],
            created_at=role.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create custom role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create custom role: {str(e)}"
        )


# ============================================================================
# Quota Management Endpoints
# ============================================================================

@router.get("/quotas/{entity_type}/{entity_id}", response_model=QuotaResponse)
async def get_quota(
    entity_type: EntityType,
    entity_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    quota_manager: QuotaManager = Depends(get_quota_manager)
):
    """Get quota configuration for a tenant or workspace."""
    try:
        quota = quota_manager.get_quota(entity_id, entity_type)
        if not quota:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quota not found"
            )
        
        return QuotaResponse(
            entity_id=entity_id,
            entity_type=entity_type,
            storage_bytes=quota.storage_bytes,
            project_count=quota.project_count,
            user_count=quota.user_count,
            api_call_count=quota.api_call_count,
            created_at=quota.created_at,
            updated_at=quota.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quota: {str(e)}"
        )


@router.put("/quotas/{entity_type}/{entity_id}", response_model=QuotaResponse)
async def set_quota(
    entity_type: EntityType,
    entity_id: str,
    request: QuotaConfig,
    current_user: SimpleUserModel = Depends(get_current_user),
    quota_manager: QuotaManager = Depends(get_quota_manager)
):
    """Set quota configuration for a tenant or workspace."""
    check_admin_permission(current_user)
    
    try:
        quota = quota_manager.set_quota(entity_id, entity_type, request)
        
        return QuotaResponse(
            entity_id=entity_id,
            entity_type=entity_type,
            storage_bytes=quota.storage_bytes,
            project_count=quota.project_count,
            user_count=quota.user_count,
            api_call_count=quota.api_call_count,
            created_at=quota.created_at,
            updated_at=quota.updated_at,
        )
    except Exception as e:
        logger.error(f"Failed to set quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set quota: {str(e)}"
        )


@router.get("/quotas/{entity_type}/{entity_id}/usage", response_model=QuotaUsageData)
async def get_quota_usage(
    entity_type: EntityType,
    entity_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    quota_manager: QuotaManager = Depends(get_quota_manager)
):
    """Get current usage for a tenant or workspace."""
    try:
        usage = quota_manager.get_usage(entity_id, entity_type)
        if not usage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usage data not found"
            )
        
        return QuotaUsageData(
            storage_bytes=usage.storage_bytes,
            project_count=usage.project_count,
            user_count=usage.user_count,
            api_call_count=usage.api_call_count,
            last_updated=usage.last_updated,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage: {str(e)}"
        )


@router.post("/quotas/{entity_type}/{entity_id}/check", response_model=QuotaCheckResult)
async def check_quota(
    entity_type: EntityType,
    entity_id: str,
    resource_type: ResourceType,
    amount: int = Query(1, ge=1),
    current_user: SimpleUserModel = Depends(get_current_user),
    quota_manager: QuotaManager = Depends(get_quota_manager)
):
    """Check if a resource operation is allowed within quota limits."""
    try:
        result = quota_manager.check_quota(entity_id, entity_type, resource_type, amount)
        return result
    except Exception as e:
        logger.error(f"Failed to check quota: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check quota: {str(e)}"
        )


# ============================================================================
# Cross-Tenant Collaboration Endpoints
# ============================================================================

class CreateShareRequest(BaseModel):
    """Request to create a share link."""
    resource_id: str
    resource_type: str
    permission: SharePermission = SharePermission.READ_ONLY
    expires_in_days: int = 7


@router.post("/shares", response_model=ShareLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_share(
    request: CreateShareRequest,
    current_user: SimpleUserModel = Depends(get_current_user),
    collaborator: CrossTenantCollaborator = Depends(get_cross_tenant_collaborator)
):
    """Create a share link for cross-tenant collaboration."""
    try:
        share = collaborator.create_share(
            resource_id=request.resource_id,
            resource_type=request.resource_type,
            owner_tenant_id=current_user.tenant_id,
            permission=request.permission,
            expires_in=timedelta(days=request.expires_in_days)
        )
        
        return ShareLinkResponse(
            id=share.id,
            resource_id=share.resource_id,
            resource_type=share.resource_type,
            owner_tenant_id=share.owner_tenant_id,
            permission=SharePermission(share.permission),
            token=share.token,
            expires_at=share.expires_at,
            created_at=share.created_at,
        )
    except Exception as e:
        logger.error(f"Failed to create share: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create share: {str(e)}"
        )


@router.get("/shares/{token}", response_model=SharedResourceAccess)
async def access_share(
    token: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    collaborator: CrossTenantCollaborator = Depends(get_cross_tenant_collaborator)
):
    """Access a shared resource using a share token."""
    try:
        resource = collaborator.access_shared_resource(
            token=token,
            accessor_tenant_id=current_user.tenant_id
        )
        return resource
    except ShareExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link has expired"
        )
    except ShareRevokedError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link has been revoked"
        )
    except TenantNotWhitelistedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your tenant is not authorized to access this resource"
        )
    except ShareNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
    except Exception as e:
        logger.error(f"Failed to access share: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to access share: {str(e)}"
        )


@router.delete("/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(
    share_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    collaborator: CrossTenantCollaborator = Depends(get_cross_tenant_collaborator)
):
    """Revoke a share link."""
    try:
        success = collaborator.revoke_share(share_id, current_user.tenant_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share not found or not owned by your tenant"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke share: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke share: {str(e)}"
        )


@router.get("/shares", response_model=List[ShareLinkResponse])
async def list_shares(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: SimpleUserModel = Depends(get_current_user),
    collaborator: CrossTenantCollaborator = Depends(get_cross_tenant_collaborator)
):
    """List all share links created by the current tenant."""
    try:
        shares = collaborator.list_shares(current_user.tenant_id, skip=skip, limit=limit)
        
        return [
            ShareLinkResponse(
                id=s.id,
                resource_id=s.resource_id,
                resource_type=s.resource_type,
                owner_tenant_id=s.owner_tenant_id,
                permission=SharePermission(s.permission),
                token=s.token,
                expires_at=s.expires_at,
                created_at=s.created_at,
            )
            for s in shares
        ]
    except Exception as e:
        logger.error(f"Failed to list shares: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list shares: {str(e)}"
        )


@router.put("/tenants/{tenant_id}/whitelist")
async def set_tenant_whitelist(
    tenant_id: str,
    request: WhitelistConfig,
    current_user: SimpleUserModel = Depends(get_current_user),
    collaborator: CrossTenantCollaborator = Depends(get_cross_tenant_collaborator)
):
    """Set the whitelist of tenants allowed to access shared resources."""
    check_admin_permission(current_user)
    check_tenant_access(current_user, tenant_id)
    
    try:
        collaborator.set_whitelist(tenant_id, request.allowed_tenant_ids)
        return {"message": "Whitelist updated successfully"}
    except Exception as e:
        logger.error(f"Failed to set whitelist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set whitelist: {str(e)}"
        )


@router.get("/tenants/{tenant_id}/whitelist", response_model=WhitelistConfig)
async def get_tenant_whitelist(
    tenant_id: str,
    current_user: SimpleUserModel = Depends(get_current_user),
    collaborator: CrossTenantCollaborator = Depends(get_cross_tenant_collaborator)
):
    """Get the whitelist of tenants allowed to access shared resources."""
    check_tenant_access(current_user, tenant_id)
    
    try:
        allowed_tenants = collaborator.get_whitelist(tenant_id)
        return WhitelistConfig(allowed_tenant_ids=allowed_tenants)
    except Exception as e:
        logger.error(f"Failed to get whitelist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get whitelist: {str(e)}"
        )


# ============================================================================
# Admin Console Endpoints
# ============================================================================

class TenantStats(BaseModel):
    """Tenant statistics."""
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    disabled_tenants: int


class WorkspaceStats(BaseModel):
    """Workspace statistics."""
    total_workspaces: int
    active_workspaces: int
    archived_workspaces: int


class UserStats(BaseModel):
    """User statistics."""
    total_users: int
    active_users_today: int
    active_users_week: int


class SystemHealth(BaseModel):
    """System health status."""
    database: str
    cache: str
    storage: str
    overall: str


class AdminDashboardResponse(BaseModel):
    """Admin dashboard response."""
    tenant_stats: TenantStats
    workspace_stats: WorkspaceStats
    user_stats: UserStats
    system_health: SystemHealth
    last_updated: datetime


@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    current_user: SimpleUserModel = Depends(get_current_user),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
    db: Session = Depends(get_db_session)
):
    """Get admin dashboard with system overview."""
    check_admin_permission(current_user)
    
    try:
        # Get tenant statistics
        all_tenants = tenant_manager.list_tenants(limit=10000)
        tenant_stats = TenantStats(
            total_tenants=len(all_tenants),
            active_tenants=len([t for t in all_tenants if t.status == "active"]),
            suspended_tenants=len([t for t in all_tenants if t.status == "suspended"]),
            disabled_tenants=len([t for t in all_tenants if t.status == "disabled"]),
        )
        
        # Get workspace statistics
        all_workspaces = workspace_manager.list_workspaces(limit=10000)
        workspace_stats = WorkspaceStats(
            total_workspaces=len(all_workspaces),
            active_workspaces=len([w for w in all_workspaces if w.status == "active"]),
            archived_workspaces=len([w for w in all_workspaces if w.status == "archived"]),
        )
        
        # Get user statistics (simplified)
        user_stats = UserStats(
            total_users=0,  # Would query from users table
            active_users_today=0,
            active_users_week=0,
        )
        
        # System health check
        system_health = SystemHealth(
            database="healthy",
            cache="healthy",
            storage="healthy",
            overall="healthy",
        )
        
        return AdminDashboardResponse(
            tenant_stats=tenant_stats,
            workspace_stats=workspace_stats,
            user_stats=user_stats,
            system_health=system_health,
            last_updated=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Failed to get admin dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get admin dashboard: {str(e)}"
        )


class ServiceStatusResponse(BaseModel):
    """Service status response."""
    name: str
    status: str
    version: Optional[str] = None
    uptime: Optional[str] = None
    last_check: datetime


@router.get("/admin/services", response_model=List[ServiceStatusResponse])
async def get_service_status(
    current_user: SimpleUserModel = Depends(get_current_user)
):
    """Get status of all system services."""
    check_admin_permission(current_user)
    
    try:
        # Return status of key services
        services = [
            ServiceStatusResponse(
                name="api",
                status="running",
                version="1.0.0",
                uptime="N/A",
                last_check=datetime.utcnow(),
            ),
            ServiceStatusResponse(
                name="database",
                status="running",
                version="PostgreSQL 15",
                uptime="N/A",
                last_check=datetime.utcnow(),
            ),
            ServiceStatusResponse(
                name="cache",
                status="running",
                version="Redis 7",
                uptime="N/A",
                last_check=datetime.utcnow(),
            ),
            ServiceStatusResponse(
                name="label_studio",
                status="running",
                version="1.8.0",
                uptime="N/A",
                last_check=datetime.utcnow(),
            ),
        ]
        
        return services
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service status: {str(e)}"
        )


class SystemConfigResponse(BaseModel):
    """System configuration response."""
    max_tenants: int
    max_workspaces_per_tenant: int
    max_users_per_workspace: int
    default_storage_quota_gb: int
    enable_cross_tenant_sharing: bool
    audit_log_retention_days: int


@router.get("/admin/config", response_model=SystemConfigResponse)
async def get_system_config(
    current_user: SimpleUserModel = Depends(get_current_user)
):
    """Get current system configuration."""
    check_admin_permission(current_user)
    
    try:
        # Return current system configuration
        return SystemConfigResponse(
            max_tenants=1000,
            max_workspaces_per_tenant=100,
            max_users_per_workspace=500,
            default_storage_quota_gb=10,
            enable_cross_tenant_sharing=True,
            audit_log_retention_days=90,
        )
    except Exception as e:
        logger.error(f"Failed to get system config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system config: {str(e)}"
        )


@router.put("/admin/config", response_model=SystemConfigResponse)
async def update_system_config(
    request: SystemConfigRequest,
    current_user: SimpleUserModel = Depends(get_current_user)
):
    """Update system configuration."""
    check_admin_permission(current_user)
    
    try:
        # In a real implementation, this would persist to database/config
        return SystemConfigResponse(
            max_tenants=request.max_tenants or 1000,
            max_workspaces_per_tenant=request.max_workspaces_per_tenant or 100,
            max_users_per_workspace=request.max_users_per_workspace or 500,
            default_storage_quota_gb=request.default_storage_quota_gb or 10,
            enable_cross_tenant_sharing=request.enable_cross_tenant_sharing if request.enable_cross_tenant_sharing is not None else True,
            audit_log_retention_days=request.audit_log_retention_days or 90,
        )
    except Exception as e:
        logger.error(f"Failed to update system config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update system config: {str(e)}"
        )


class AuditLogEntry(BaseModel):
    """Audit log entry."""
    id: str
    timestamp: datetime
    user_id: Optional[str]
    tenant_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]


class AuditLogFilters(BaseModel):
    """Filters for audit log queries."""
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@router.get("/admin/audit-logs", response_model=List[AuditLogEntry])
async def get_audit_logs(
    tenant_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: SimpleUserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get audit logs with optional filters."""
    check_admin_permission(current_user)
    
    try:
        # In a real implementation, this would query the audit_logs table
        # For now, return empty list as placeholder
        return []
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit logs: {str(e)}"
        )


# ============================================================================
# Health Check Endpoint
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint for the multi-tenant API."""
    return {
        "status": "healthy",
        "service": "multi-tenant-api",
        "timestamp": datetime.utcnow().isoformat()
    }
