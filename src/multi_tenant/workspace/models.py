"""
Extended database models for Multi-Tenant Workspace module.

This module extends the base multi-tenant models with additional functionality:
- Workspace hierarchy (parent-child relationships)
- Custom roles and permissions
- Cross-tenant sharing
- Quota management
- Audit logging for cross-tenant access
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    String, Text, Integer, BigInteger, DateTime, Boolean, 
    ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from typing import Optional, List

from src.database.connection import Base


# ============================================================================
# Extended Enums
# ============================================================================

class ExtendedTenantStatus(str, enum.Enum):
    """Extended tenant status with disabled state."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class ExtendedWorkspaceStatus(str, enum.Enum):
    """Extended workspace status with deleted state."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemberRole(str, enum.Enum):
    """Workspace member role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class SharePermission(str, enum.Enum):
    """Cross-tenant share permission enumeration."""
    READ_ONLY = "read_only"
    EDIT = "edit"


class EntityType(str, enum.Enum):
    """Entity type for quota management."""
    TENANT = "tenant"
    WORKSPACE = "workspace"


# ============================================================================
# Extended Tenant Models
# ============================================================================

class TenantQuotaModel(Base):
    """
    Tenant quota configuration table.
    
    Stores quota limits for each tenant separately from usage tracking.
    """
    __tablename__ = "tenant_quotas"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    
    # Quota limits
    storage_bytes: Mapped[int] = mapped_column(BigInteger, default=10737418240)  # 10GB
    project_count: Mapped[int] = mapped_column(Integer, default=100)
    user_count: Mapped[int] = mapped_column(Integer, default=50)
    api_call_count: Mapped[int] = mapped_column(Integer, default=100000)  # per month
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class QuotaUsageModel(Base):
    """
    Quota usage tracking table.
    
    Tracks current resource usage for tenants and workspaces.
    """
    __tablename__ = "quota_usage"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[EntityType] = mapped_column(SQLEnum(EntityType), nullable=False)
    
    # Usage metrics
    storage_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    project_count: Mapped[int] = mapped_column(Integer, default=0)
    user_count: Mapped[int] = mapped_column(Integer, default=0)
    api_call_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('entity_id', 'entity_type', name='uq_quota_usage_entity'),
        Index('ix_quota_usage_entity', 'entity_id', 'entity_type'),
    )


class TemporaryQuotaModel(Base):
    """
    Temporary quota increase table.
    
    Stores temporary quota increases with expiration.
    """
    __tablename__ = "temporary_quotas"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[EntityType] = mapped_column(SQLEnum(EntityType), nullable=False)
    
    # Temporary quota values
    storage_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    project_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    api_call_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Expiration
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_temporary_quota_entity', 'entity_id', 'entity_type'),
        Index('ix_temporary_quota_expires', 'expires_at'),
    )


# ============================================================================
# Extended Workspace Models
# ============================================================================

class ExtendedWorkspaceModel(Base):
    """
    Extended workspace table with hierarchy support.
    
    Adds parent-child relationships for workspace hierarchy.
    """
    __tablename__ = "extended_workspaces"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    parent_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("extended_workspaces.id"), nullable=True, index=True)
    
    # Basic info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ExtendedWorkspaceStatus] = mapped_column(
        SQLEnum(ExtendedWorkspaceStatus), 
        default=ExtendedWorkspaceStatus.ACTIVE
    )
    
    # Configuration
    config: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Self-referential relationship for hierarchy
    parent: Mapped[Optional["ExtendedWorkspaceModel"]] = relationship(
        "ExtendedWorkspaceModel",
        remote_side=[id],
        back_populates="children"
    )
    children: Mapped[List["ExtendedWorkspaceModel"]] = relationship(
        "ExtendedWorkspaceModel",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    # Members relationship
    members: Mapped[List["WorkspaceMemberModel"]] = relationship(
        "WorkspaceMemberModel",
        back_populates="workspace",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', 'parent_id', name='uq_workspace_name_in_parent'),
        Index('ix_extended_workspace_tenant', 'tenant_id'),
        Index('ix_extended_workspace_parent', 'parent_id'),
    )


class WorkspaceMemberModel(Base):
    """
    Workspace member table.
    
    Links users to workspaces with role assignments.
    """
    __tablename__ = "workspace_members"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extended_workspaces.id"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[MemberRole] = mapped_column(SQLEnum(MemberRole), default=MemberRole.MEMBER)
    custom_role_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("custom_roles.id"), nullable=True)
    
    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workspace: Mapped["ExtendedWorkspaceModel"] = relationship("ExtendedWorkspaceModel", back_populates="members")
    custom_role: Mapped[Optional["CustomRoleModel"]] = relationship("CustomRoleModel")
    
    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_member'),
        Index('ix_workspace_member_workspace', 'workspace_id'),
        Index('ix_workspace_member_user', 'user_id'),
    )


class CustomRoleModel(Base):
    """
    Custom role table.
    
    Stores custom role definitions with permissions.
    """
    __tablename__ = "custom_roles"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extended_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permissions: Mapped[list] = mapped_column(JSONB, default=[])
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('workspace_id', 'name', name='uq_custom_role_name'),
        Index('ix_custom_role_workspace', 'workspace_id'),
    )


class WorkspaceTemplateModel(Base):
    """
    Workspace template table.
    
    Stores workspace templates for quick creation.
    """
    __tablename__ = "workspace_templates"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=True, index=True)  # NULL for system templates
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default={})
    default_roles: Mapped[list] = mapped_column(JSONB, default=[])
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InvitationModel(Base):
    """
    Member invitation table.
    
    Stores pending invitations to workspaces.
    """
    __tablename__ = "workspace_invitations"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extended_workspaces.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[MemberRole] = mapped_column(SQLEnum(MemberRole), default=MemberRole.MEMBER)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Invitation status
    invited_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_invitation_workspace', 'workspace_id'),
        Index('ix_invitation_email', 'email'),
        Index('ix_invitation_token', 'token'),
    )


# ============================================================================
# Cross-Tenant Collaboration Models
# ============================================================================

class ShareLinkModel(Base):
    """
    Share link table.
    
    Stores cross-tenant sharing links.
    """
    __tablename__ = "share_links"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    permission: Mapped[SharePermission] = mapped_column(SQLEnum(SharePermission), default=SharePermission.READ_ONLY)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    
    # Expiration and status
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_share_link_resource', 'resource_id', 'resource_type'),
        Index('ix_share_link_token', 'token'),
        Index('ix_share_link_owner', 'owner_tenant_id'),
    )


class TenantWhitelistModel(Base):
    """
    Tenant whitelist table.
    
    Stores allowed tenant pairs for cross-tenant collaboration.
    """
    __tablename__ = "tenant_whitelist"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    allowed_tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('owner_tenant_id', 'allowed_tenant_id', name='uq_tenant_whitelist'),
        Index('ix_whitelist_owner', 'owner_tenant_id'),
        Index('ix_whitelist_allowed', 'allowed_tenant_id'),
    )


class CrossTenantAccessLogModel(Base):
    """
    Cross-tenant access log table.
    
    Records all cross-tenant access attempts for audit.
    """
    __tablename__ = "cross_tenant_access_logs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    accessor_tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    owner_tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    accessor_user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    resource_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Request metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_cross_tenant_log_accessor', 'accessor_tenant_id'),
        Index('ix_cross_tenant_log_owner', 'owner_tenant_id'),
        Index('ix_cross_tenant_log_time', 'created_at'),
    )


# ============================================================================
# Tenant Audit Log Model
# ============================================================================

class TenantAuditLogModel(Base):
    """
    Tenant audit log table.
    
    Records all tenant-level operations for audit.
    """
    __tablename__ = "tenant_audit_logs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Request metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_tenant_audit_tenant', 'tenant_id'),
        Index('ix_tenant_audit_user', 'user_id'),
        Index('ix_tenant_audit_action', 'action'),
        Index('ix_tenant_audit_time', 'created_at'),
    )
