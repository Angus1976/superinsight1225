"""
Pydantic schemas for Multi-Tenant Workspace module.

This module defines all data transfer objects (DTOs) and validation schemas
for the multi-tenant workspace system.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, validator


# ============================================================================
# Enums
# ============================================================================

class TenantStatus(str, Enum):
    """Tenant status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class WorkspaceStatus(str, Enum):
    """Workspace status enumeration."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemberRole(str, Enum):
    """Workspace member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class SharePermission(str, Enum):
    """Cross-tenant share permission enumeration."""
    READ_ONLY = "read_only"
    EDIT = "edit"


class EntityType(str, Enum):
    """Entity type for quota management."""
    TENANT = "tenant"
    WORKSPACE = "workspace"


class ResourceType(str, Enum):
    """Resource type for quota tracking."""
    STORAGE = "storage_bytes"
    PROJECTS = "project_count"
    USERS = "user_count"
    API_CALLS = "api_call_count"


# ============================================================================
# Tenant Schemas
# ============================================================================

class TenantConfig(BaseModel):
    """Tenant configuration schema."""
    features: Dict[str, bool] = Field(default_factory=lambda: {
        "ai_annotation": True,
        "quality_assessment": True,
        "billing": True,
        "cross_tenant_sharing": False,
    })
    security: Dict[str, Any] = Field(default_factory=lambda: {
        "mfa_required": False,
        "session_timeout_minutes": 60,
        "ip_whitelist_enabled": False,
        "ip_whitelist": [],
    })
    workspace_defaults: Dict[str, Any] = Field(default_factory=dict)
    custom_settings: Dict[str, Any] = Field(default_factory=dict)


class TenantQuotaConfig(BaseModel):
    """Tenant quota configuration schema."""
    storage_bytes: int = Field(default=10 * 1024 * 1024 * 1024, description="Storage quota in bytes (default 10GB)")
    project_count: int = Field(default=100, description="Maximum number of projects")
    user_count: int = Field(default=50, description="Maximum number of users")
    api_call_count: int = Field(default=100000, description="Maximum API calls per month")


class TenantCreateConfig(BaseModel):
    """Configuration for creating a new tenant."""
    name: str = Field(..., min_length=1, max_length=200, description="Tenant name")
    description: Optional[str] = Field(None, max_length=1000, description="Tenant description")
    admin_email: EmailStr = Field(..., description="Admin email address")
    plan: str = Field(default="free", description="Billing plan")
    config: Optional[TenantConfig] = Field(default=None, description="Tenant configuration")
    quota: Optional[TenantQuotaConfig] = Field(default=None, description="Tenant quota")


class TenantUpdateConfig(BaseModel):
    """Configuration for updating a tenant."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    admin_email: Optional[EmailStr] = None
    plan: Optional[str] = None
    config: Optional[TenantConfig] = None


class TenantResponse(BaseModel):
    """Tenant response schema."""
    id: UUID
    name: str
    description: Optional[str]
    status: TenantStatus
    admin_email: str
    plan: str
    config: TenantConfig
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Workspace Schemas
# ============================================================================

class WorkspaceCreateConfig(BaseModel):
    """Configuration for creating a new workspace."""
    name: str = Field(..., min_length=1, max_length=200, description="Workspace name")
    description: Optional[str] = Field(None, max_length=1000, description="Workspace description")
    parent_id: Optional[UUID] = Field(None, description="Parent workspace ID for hierarchy")
    template_id: Optional[UUID] = Field(None, description="Template ID to create from")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Workspace configuration")


class WorkspaceUpdateConfig(BaseModel):
    """Configuration for updating a workspace."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    config: Optional[Dict[str, Any]] = None


class WorkspaceNode(BaseModel):
    """Workspace hierarchy node schema."""
    id: UUID
    tenant_id: UUID
    parent_id: Optional[UUID]
    name: str
    description: Optional[str]
    status: WorkspaceStatus
    config: Dict[str, Any]
    created_at: datetime
    children: List["WorkspaceNode"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class WorkspaceTemplate(BaseModel):
    """Workspace template schema."""
    id: UUID
    name: str
    description: Optional[str]
    config: Dict[str, Any]
    default_roles: List[str] = Field(default_factory=list)
    created_at: datetime


class WorkspaceResponse(BaseModel):
    """Workspace response schema."""
    id: UUID
    tenant_id: UUID
    parent_id: Optional[UUID]
    name: str
    description: Optional[str]
    status: WorkspaceStatus
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Member Schemas
# ============================================================================

class MemberAddRequest(BaseModel):
    """Request to add a member to workspace."""
    user_id: UUID = Field(..., description="User ID to add")
    role: MemberRole = Field(default=MemberRole.MEMBER, description="Role to assign")
    custom_role_id: Optional[UUID] = Field(None, description="Custom role ID if applicable")


class CustomRoleConfig(BaseModel):
    """Configuration for creating a custom role."""
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, max_length=500, description="Role description")
    permissions: List[str] = Field(..., description="List of permission strings")


class InvitationConfig(BaseModel):
    """Configuration for member invitation."""
    email: EmailStr = Field(..., description="Email to invite")
    role: MemberRole = Field(default=MemberRole.MEMBER, description="Role to assign")
    message: Optional[str] = Field(None, max_length=500, description="Invitation message")
    expires_in_days: int = Field(default=7, ge=1, le=30, description="Invitation expiry in days")


class WorkspaceMemberResponse(BaseModel):
    """Workspace member response schema."""
    id: UUID
    user_id: UUID
    workspace_id: UUID
    role: MemberRole
    custom_role_id: Optional[UUID]
    joined_at: datetime
    last_active_at: Optional[datetime]

    class Config:
        from_attributes = True


class InvitationResponse(BaseModel):
    """Invitation response schema."""
    id: UUID
    workspace_id: UUID
    email: str
    role: MemberRole
    token: str
    expires_at: datetime
    created_at: datetime


# ============================================================================
# Quota Schemas
# ============================================================================

class QuotaConfig(BaseModel):
    """Quota configuration schema."""
    storage_bytes: int = Field(default=10 * 1024 * 1024 * 1024, ge=0, description="Storage quota in bytes")
    project_count: int = Field(default=100, ge=0, description="Maximum projects")
    user_count: int = Field(default=50, ge=0, description="Maximum users")
    api_call_count: int = Field(default=100000, ge=0, description="Maximum API calls per month")


class QuotaUsageData(BaseModel):
    """Quota usage data schema."""
    storage_bytes: int = Field(default=0, ge=0)
    project_count: int = Field(default=0, ge=0)
    user_count: int = Field(default=0, ge=0)
    api_call_count: int = Field(default=0, ge=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class QuotaCheckResult(BaseModel):
    """Result of quota check operation."""
    allowed: bool = Field(..., description="Whether the operation is allowed")
    percentage: float = Field(default=0.0, ge=0, le=100, description="Current usage percentage")
    reason: Optional[str] = Field(None, description="Reason if not allowed")
    warning: Optional[str] = Field(None, description="Warning message if approaching limit")


class TemporaryQuotaConfig(BaseModel):
    """Configuration for temporary quota increase."""
    quota: QuotaConfig = Field(..., description="Temporary quota values")
    expires_at: datetime = Field(..., description="When the temporary quota expires")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for temporary increase")


class QuotaResponse(BaseModel):
    """Quota response schema."""
    entity_id: str
    entity_type: EntityType
    storage_bytes: int
    project_count: int
    user_count: int
    api_call_count: int
    created_at: datetime
    updated_at: datetime


class QuotaFullResponse(BaseModel):
    """Full quota response with usage data."""
    entity_id: UUID
    entity_type: EntityType
    quota: QuotaConfig
    usage: QuotaUsageData
    temporary_quota: Optional[TemporaryQuotaConfig]


# ============================================================================
# Share Schemas
# ============================================================================

class ShareConfig(BaseModel):
    """Configuration for creating a share link."""
    resource_id: UUID = Field(..., description="Resource ID to share")
    resource_type: str = Field(..., description="Type of resource (workspace, project, etc.)")
    permission: SharePermission = Field(default=SharePermission.READ_ONLY, description="Share permission level")
    expires_in: timedelta = Field(default=timedelta(days=7), description="Share expiration time")
    allowed_tenants: Optional[List[UUID]] = Field(None, description="Specific tenants allowed to access")


class SharedResourceAccess(BaseModel):
    """Shared resource access response."""
    share_id: UUID
    resource_id: UUID
    resource_type: str
    permission: SharePermission
    owner_tenant_id: UUID
    expires_at: datetime
    accessed_at: datetime


class ShareLinkResponse(BaseModel):
    """Share link response schema."""
    id: UUID
    resource_id: str
    resource_type: str
    permission: SharePermission
    token: str
    owner_tenant_id: str
    expires_at: datetime
    created_at: datetime
    revoked: bool = False


class WhitelistConfig(BaseModel):
    """Configuration for tenant whitelist."""
    allowed_tenant_ids: List[str] = Field(..., description="List of allowed tenant IDs")


# ============================================================================
# Admin Console Schemas
# ============================================================================

class AdminDashboard(BaseModel):
    """Admin dashboard data schema."""
    total_tenants: int
    active_tenants: int
    total_workspaces: int
    total_users: int
    storage_used_bytes: int
    api_calls_today: int
    system_health: str
    alerts: List[Dict[str, Any]] = Field(default_factory=list)


class ServiceStatus(BaseModel):
    """Service status schema."""
    name: str
    status: str  # healthy, degraded, down
    latency_ms: Optional[float]
    last_check: datetime
    details: Optional[Dict[str, Any]]


class SystemConfigRequest(BaseModel):
    """System configuration update request."""
    max_tenants: Optional[int] = Field(None, ge=1, description="Maximum number of tenants")
    max_workspaces_per_tenant: Optional[int] = Field(None, ge=1, description="Maximum workspaces per tenant")
    max_users_per_workspace: Optional[int] = Field(None, ge=1, description="Maximum users per workspace")
    default_storage_quota_gb: Optional[int] = Field(None, ge=1, description="Default storage quota in GB")
    enable_cross_tenant_sharing: Optional[bool] = Field(None, description="Enable cross-tenant sharing")
    audit_log_retention_days: Optional[int] = Field(None, ge=1, description="Audit log retention in days")


# Update forward references
WorkspaceNode.model_rebuild()
