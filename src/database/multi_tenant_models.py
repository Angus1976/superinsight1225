"""
Multi-tenant database models for SuperInsight Platform.

Defines tenant, workspace, and user association models for multi-tenancy support.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, Enum as SQLEnum, JSON, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from typing import Optional, List, Dict, Any

from src.database.connection import Base


class TenantStatus(str, enum.Enum):
    """Tenant status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class WorkspaceStatus(str, enum.Enum):
    """Workspace status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class TenantRole(str, enum.Enum):
    """Tenant-level role enumeration."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class WorkspaceRole(str, enum.Enum):
    """Workspace-level role enumeration."""
    ADMIN = "admin"
    ANNOTATOR = "annotator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class TenantModel(Base):
    """
    Tenant table for multi-tenant organization management.
    
    Represents a tenant organization with configuration and quota settings.
    """
    __tablename__ = "tenants"
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # Human-readable tenant ID
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TenantStatus] = mapped_column(SQLEnum(TenantStatus), default=TenantStatus.ACTIVE)
    
    # Configuration and settings
    configuration: Mapped[dict] = mapped_column(JSONB, default={})
    label_studio_org_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Resource quotas
    max_users: Mapped[int] = mapped_column(Integer, default=100)
    max_workspaces: Mapped[int] = mapped_column(Integer, default=10)
    max_storage_gb: Mapped[float] = mapped_column(Float, default=100.0)
    max_api_calls_per_hour: Mapped[int] = mapped_column(Integer, default=10000)
    
    # Current usage (updated by background jobs)
    current_users: Mapped[int] = mapped_column(Integer, default=0)
    current_workspaces: Mapped[int] = mapped_column(Integer, default=0)
    current_storage_gb: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Billing information
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    billing_plan: Mapped[str] = mapped_column(String(50), default="basic")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    workspaces: Mapped[List["WorkspaceModel"]] = relationship("WorkspaceModel", back_populates="tenant", cascade="all, delete-orphan")
    user_associations: Mapped[List["UserTenantAssociationModel"]] = relationship("UserTenantAssociationModel", back_populates="tenant", cascade="all, delete-orphan")


class WorkspaceModel(Base):
    """
    Workspace table for project organization within tenants.
    
    Represents a workspace within a tenant for organizing projects and users.
    """
    __tablename__ = "workspaces"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[WorkspaceStatus] = mapped_column(SQLEnum(WorkspaceStatus), default=WorkspaceStatus.ACTIVE)
    
    # Configuration
    configuration: Mapped[dict] = mapped_column(JSONB, default={})
    label_studio_project_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Settings
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant: Mapped["TenantModel"] = relationship("TenantModel", back_populates="workspaces")
    user_associations: Mapped[List["UserWorkspaceAssociationModel"]] = relationship("UserWorkspaceAssociationModel", back_populates="workspace", cascade="all, delete-orphan")


class UserTenantAssociationModel(Base):
    """
    User-tenant association table for managing tenant membership.
    
    Links users to tenants with role assignments.
    """
    __tablename__ = "user_tenant_associations"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    role: Mapped[TenantRole] = mapped_column(SQLEnum(TenantRole), default=TenantRole.MEMBER)
    
    # Status and permissions
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default_tenant: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Invitation tracking
    invited_by: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant: Mapped["TenantModel"] = relationship("TenantModel", back_populates="user_associations")
    user: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[user_id])
    inviter: Mapped[Optional["UserModel"]] = relationship("UserModel", foreign_keys=[invited_by])
    
    # Unique constraint
    __table_args__ = (
        {"schema": None}  # Ensure no schema conflicts
    )


class UserWorkspaceAssociationModel(Base):
    """
    User-workspace association table for workspace-level permissions.
    
    Links users to workspaces with role assignments within a tenant.
    """
    __tablename__ = "user_workspace_associations"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    workspace_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    role: Mapped[WorkspaceRole] = mapped_column(SQLEnum(WorkspaceRole), default=WorkspaceRole.ANNOTATOR)
    
    # Status and permissions
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    workspace: Mapped["WorkspaceModel"] = relationship("WorkspaceModel", back_populates="user_associations")
    user: Mapped["UserModel"] = relationship("UserModel")
    
    # Unique constraint
    __table_args__ = (
        {"schema": None}  # Ensure no schema conflicts
    )


class TenantResourceUsageModel(Base):
    """
    Tenant resource usage tracking table.
    
    Tracks resource usage for billing and quota management.
    """
    __tablename__ = "tenant_resource_usage"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Usage metrics
    api_calls: Mapped[int] = mapped_column(Integer, default=0)
    storage_bytes: Mapped[int] = mapped_column(Integer, default=0)
    annotation_count: Mapped[int] = mapped_column(Integer, default=0)
    user_count: Mapped[int] = mapped_column(Integer, default=0)
    workspace_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Time period
    usage_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_date())
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    tenant: Mapped["TenantModel"] = relationship("TenantModel")


# Import UserModel to ensure proper relationships
from src.security.models import UserModel