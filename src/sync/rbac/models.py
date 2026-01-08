"""
RBAC models for fine-grained permission control in data sync system.

Provides comprehensive role-based access control with tenant isolation,
field-level permissions, and audit logging.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from typing import Optional, List, Dict, Any

from src.database.connection import Base


class PermissionAction(str, enum.Enum):
    """Permission action enumeration."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    EXECUTE = "execute"
    APPROVE = "approve"
    AUDIT = "audit"


class ResourceType(str, enum.Enum):
    """Resource type enumeration."""
    SYNC_JOB = "sync_job"
    DATA_SOURCE = "data_source"
    SYNC_EXECUTION = "sync_execution"
    CONFLICT_RESOLUTION = "conflict_resolution"
    TRANSFORMATION_RULE = "transformation_rule"
    AUDIT_LOG = "audit_log"
    SYSTEM_CONFIG = "system_config"
    USER_MANAGEMENT = "user_management"
    TENANT_MANAGEMENT = "tenant_management"


class FieldAccessLevel(str, enum.Enum):
    """Field access level enumeration."""
    FULL = "full"          # Full access to field
    MASKED = "masked"      # Access to masked/anonymized field
    HASHED = "hashed"      # Access to hashed field
    DENIED = "denied"      # No access to field


class AuditEventType(str, enum.Enum):
    """Audit event type enumeration."""
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    FIELD_ACCESS = "field_access"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"


class RoleModel(Base):
    """
    Role definition table for RBAC system.
    
    Defines roles with hierarchical structure and tenant isolation.
    """
    __tablename__ = "rbac_roles"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Role hierarchy
    parent_role_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("rbac_roles.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0)  # 0 = root level
    
    # Role properties
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)  # System-defined roles
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Max users for this role
    
    # Role metadata
    role_metadata: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    parent_role: Mapped[Optional["RoleModel"]] = relationship("RoleModel", remote_side=[id], back_populates="child_roles")
    child_roles: Mapped[List["RoleModel"]] = relationship("RoleModel", back_populates="parent_role")
    role_permissions: Mapped[List["RolePermissionModel"]] = relationship("RolePermissionModel", back_populates="role")
    user_roles: Mapped[List["UserRoleModel"]] = relationship("UserRoleModel", back_populates="role")


class PermissionModel(Base):
    """
    Permission definition table.
    
    Defines granular permissions for different actions and resources.
    """
    __tablename__ = "rbac_permissions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Permission scope
    resource_type: Mapped[ResourceType] = mapped_column(SQLEnum(ResourceType), nullable=False)
    action: Mapped[PermissionAction] = mapped_column(SQLEnum(PermissionAction), nullable=False)
    
    # Permission properties
    is_system_permission: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Conditions (JSON query format for dynamic conditions)
    conditions: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    role_permissions: Mapped[List["RolePermissionModel"]] = relationship("RolePermissionModel", back_populates="permission")


class RolePermissionModel(Base):
    """
    Role-Permission mapping table.
    
    Associates roles with permissions, including conditional grants.
    """
    __tablename__ = "rbac_role_permissions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    role_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rbac_roles.id"), nullable=False)
    permission_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rbac_permissions.id"), nullable=False)
    
    # Grant properties
    is_granted: Mapped[bool] = mapped_column(Boolean, default=True)
    is_inherited: Mapped[bool] = mapped_column(Boolean, default=False)  # Inherited from parent role
    
    # Conditional grants
    conditions: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Validity period
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    granted_by: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    role: Mapped["RoleModel"] = relationship("RoleModel", back_populates="role_permissions")
    permission: Mapped["PermissionModel"] = relationship("PermissionModel", back_populates="role_permissions")


class UserRoleModel(Base):
    """
    User-Role assignment table.
    
    Assigns roles to users with tenant isolation and validity periods.
    """
    __tablename__ = "rbac_user_roles"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    role_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rbac_roles.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Assignment properties
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)  # Primary role for user
    
    # Validity period
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Assignment context
    assigned_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assignment_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    role: Mapped["RoleModel"] = relationship("RoleModel", back_populates="user_roles")


class ResourcePermissionModel(Base):
    """
    Resource-specific permission overrides.
    
    Provides fine-grained permissions for specific resources.
    """
    __tablename__ = "rbac_resource_permissions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Resource identification
    resource_type: Mapped[ResourceType] = mapped_column(SQLEnum(ResourceType), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Permission details
    action: Mapped[PermissionAction] = mapped_column(SQLEnum(PermissionAction), nullable=False)
    is_granted: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Override properties
    overrides_role: Mapped[bool] = mapped_column(Boolean, default=False)  # Overrides role-based permission
    
    # Conditions
    conditions: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Validity period
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Grant context
    granted_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    grant_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FieldPermissionModel(Base):
    """
    Field-level access control table.
    
    Controls access to specific fields with different access levels.
    """
    __tablename__ = "rbac_field_permissions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Field identification
    table_name: Mapped[str] = mapped_column(String(200), nullable=False)
    field_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Role or user specific
    role_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("rbac_roles.id"), nullable=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Access control
    access_level: Mapped[FieldAccessLevel] = mapped_column(SQLEnum(FieldAccessLevel), nullable=False)
    
    # Masking configuration (for MASKED access level)
    masking_config: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Conditions for dynamic field access
    conditions: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class DataAccessAuditModel(Base):
    """
    Data access audit log table.
    
    Records all data access events for compliance and security monitoring.
    """
    __tablename__ = "rbac_data_access_audit"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Actor information
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Event details
    event_type: Mapped[AuditEventType] = mapped_column(SQLEnum(AuditEventType), nullable=False)
    
    # Resource information
    resource_type: Mapped[Optional[ResourceType]] = mapped_column(SQLEnum(ResourceType), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    table_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    field_names: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    
    # Action details
    action: Mapped[Optional[PermissionAction]] = mapped_column(SQLEnum(PermissionAction), nullable=True)
    permission_granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    
    # Context information
    request_context: Mapped[dict] = mapped_column(JSONB, default={})
    response_context: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Performance metrics
    execution_time_ms: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Risk assessment
    risk_score: Mapped[Optional[float]] = mapped_column(nullable=True)  # 0-1 risk score
    anomaly_flags: Mapped[List[str]] = mapped_column(JSONB, default=[])
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)