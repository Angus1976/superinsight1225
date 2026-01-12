"""
RBAC (Role-Based Access Control) Models for SuperInsight Platform.

Defines enhanced security models for fine-grained role and permission management.
"""

import enum
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, DateTime, String, Text, JSON, ForeignKey, 
    UniqueConstraint, Index, func, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from src.database.models import Base


class PermissionScope(str, enum.Enum):
    """Permission scope enumeration."""
    GLOBAL = "global"      # Permission applies globally
    TENANT = "tenant"      # Permission applies within tenant
    RESOURCE = "resource"  # Permission applies to specific resources


class ResourceType(str, enum.Enum):
    """Resource type enumeration for fine-grained permissions."""
    PROJECT = "project"
    DATASET = "dataset"
    MODEL = "model"
    PIPELINE = "pipeline"
    REPORT = "report"
    DASHBOARD = "dashboard"
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    AUDIT_LOG = "audit_log"
    SYSTEM_CONFIG = "system_config"


class RoleModel(Base):
    """
    Enhanced role model for RBAC system.
    
    Supports dynamic role creation, hierarchies, and tenant isolation.
    """
    __tablename__ = "rbac_roles"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Role hierarchy support
    parent_role_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("rbac_roles.id"), 
        nullable=True
    )
    
    # Metadata and status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)  # System-defined roles
    role_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Audit fields
    created_by: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    parent_role: Mapped[Optional["RoleModel"]] = relationship(
        "RoleModel", 
        remote_side=[id], 
        back_populates="child_roles"
    )
    child_roles: Mapped[List["RoleModel"]] = relationship(
        "RoleModel", 
        back_populates="parent_role"
    )
    
    permissions: Mapped[List["RolePermissionModel"]] = relationship(
        "RolePermissionModel", 
        back_populates="role",
        cascade="all, delete-orphan"
    )
    
    user_assignments: Mapped[List["UserRoleModel"]] = relationship(
        "UserRoleModel", 
        back_populates="role",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('name', 'tenant_id', name='uq_role_name_tenant'),
        Index('idx_role_tenant_active', 'tenant_id', 'is_active'),
        Index('idx_role_parent', 'parent_role_id'),
    )


class PermissionModel(Base):
    """
    Permission model for fine-grained access control.
    
    Defines specific permissions that can be assigned to roles.
    """
    __tablename__ = "rbac_permissions"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Permission scope and resource type
    scope: Mapped[PermissionScope] = mapped_column(SQLEnum(PermissionScope), nullable=False)
    resource_type: Mapped[Optional[ResourceType]] = mapped_column(SQLEnum(ResourceType), nullable=True)
    
    # Permission metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system_permission: Mapped[bool] = mapped_column(Boolean, default=False)
    permission_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Audit fields
    created_by: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    role_assignments: Mapped[List["RolePermissionModel"]] = relationship(
        "RolePermissionModel", 
        back_populates="permission",
        cascade="all, delete-orphan"
    )
    
    resource_assignments: Mapped[List["ResourcePermissionModel"]] = relationship(
        "ResourcePermissionModel", 
        back_populates="permission",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        Index('idx_permission_scope_resource', 'scope', 'resource_type'),
        Index('idx_permission_active', 'is_active'),
    )


class RolePermissionModel(Base):
    """
    Role-Permission assignment model.
    
    Links roles to their assigned permissions.
    """
    __tablename__ = "rbac_role_permissions"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    role_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("rbac_roles.id", ondelete="CASCADE"), 
        nullable=False
    )
    permission_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("rbac_permissions.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Assignment metadata
    granted_by: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Conditional permissions (future enhancement)
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    role: Mapped["RoleModel"] = relationship("RoleModel", back_populates="permissions")
    permission: Mapped["PermissionModel"] = relationship("PermissionModel", back_populates="role_assignments")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
        Index('idx_role_permission_role', 'role_id'),
        Index('idx_role_permission_permission', 'permission_id'),
    )


class UserRoleModel(Base):
    """
    User-Role assignment model.
    
    Links users to their assigned roles with audit information.
    """
    __tablename__ = "rbac_user_roles"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    role_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("rbac_roles.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Assignment metadata
    assigned_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Expiration support (future enhancement)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Assignment conditions (future enhancement)
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    role: Mapped["RoleModel"] = relationship("RoleModel", back_populates="user_assignments")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
        Index('idx_user_role_user', 'user_id'),
        Index('idx_user_role_role', 'role_id'),
        Index('idx_user_role_active', 'is_active'),
    )


class ResourceModel(Base):
    """
    Resource model for resource-level permissions.
    
    Represents resources that can have specific permissions assigned.
    """
    __tablename__ = "rbac_resources"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)  # External resource ID
    resource_type: Mapped[ResourceType] = mapped_column(SQLEnum(ResourceType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Resource hierarchy support
    parent_resource_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("rbac_resources.id"), 
        nullable=True
    )
    
    # Tenant isolation
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Resource metadata
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    resource_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    parent_resource: Mapped[Optional["ResourceModel"]] = relationship(
        "ResourceModel", 
        remote_side=[id], 
        back_populates="child_resources"
    )
    child_resources: Mapped[List["ResourceModel"]] = relationship(
        "ResourceModel", 
        back_populates="parent_resource"
    )
    
    # Note: Permissions are accessed via ResourcePermissionModel queries, not direct relationships
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('resource_id', 'resource_type', 'tenant_id', name='uq_resource_tenant'),
        Index('idx_resource_type_tenant', 'resource_type', 'tenant_id'),
        Index('idx_resource_owner', 'owner_id'),
        Index('idx_resource_parent', 'parent_resource_id'),
    )


class ResourcePermissionModel(Base):
    """
    Resource-specific permission assignments.
    
    Allows granting specific permissions to users for individual resources.
    """
    __tablename__ = "rbac_resource_permissions"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[ResourceType] = mapped_column(SQLEnum(ResourceType), nullable=False)
    permission_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("rbac_permissions.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Assignment metadata
    granted_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Expiration support
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Permission conditions
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    permission: Mapped["PermissionModel"] = relationship("PermissionModel", back_populates="resource_assignments")
    # Note: Resource relationship is handled via foreign keys, not direct relationship
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'resource_id', 'resource_type', 'permission_id', name='uq_user_resource_permission'),
        Index('idx_resource_permission_user', 'user_id'),
        Index('idx_resource_permission_resource', 'resource_id', 'resource_type'),
        Index('idx_resource_permission_permission', 'permission_id'),
        Index('idx_resource_permission_active', 'is_active'),
    )


class PermissionGroupModel(Base):
    """
    Permission groups for easier permission management.
    
    Allows grouping related permissions together for bulk assignment.
    """
    __tablename__ = "rbac_permission_groups"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Group metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system_group: Mapped[bool] = mapped_column(Boolean, default=False)
    group_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Audit fields
    created_by: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('name', name='uq_permission_group_name'),
        Index('idx_permission_group_active', 'is_active'),
    )


class PermissionGroupMemberModel(Base):
    """
    Permission group membership model.
    
    Links permissions to permission groups.
    """
    __tablename__ = "rbac_permission_group_members"
    
    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("rbac_permission_groups.id", ondelete="CASCADE"), 
        nullable=False
    )
    permission_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("rbac_permissions.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Membership metadata
    added_by: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('group_id', 'permission_id', name='uq_group_permission'),
        Index('idx_group_member_group', 'group_id'),
        Index('idx_group_member_permission', 'permission_id'),
    )