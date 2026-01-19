"""
RBAC models for fine-grained permission control in data sync system.

This module re-exports RBAC models from src.security.rbac_models and adds
sync-specific models for field-level permissions and data access auditing.

NOTE: The core RBAC models (RoleModel, PermissionModel, etc.) are defined in
src/security/rbac_models.py to avoid duplicate model registration issues.
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

# Re-export core RBAC models from security module to avoid duplicate registration
from src.security.rbac_models import (
    RoleModel,
    PermissionModel,
    RolePermissionModel,
    UserRoleModel,
    ResourcePermissionModel,
    ResourceType,
    PermissionScope,
)


# Sync-specific enums
class PermissionAction(str, enum.Enum):
    """Permission action enumeration for sync operations."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    EXECUTE = "execute"
    APPROVE = "approve"
    AUDIT = "audit"


class SyncResourceType(str, enum.Enum):
    """Resource type enumeration for sync-specific resources."""
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
    resource_type: Mapped[Optional[SyncResourceType]] = mapped_column(SQLEnum(SyncResourceType), nullable=True)
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


# Export all models and enums for backward compatibility
__all__ = [
    # Re-exported from security module
    "RoleModel",
    "PermissionModel",
    "RolePermissionModel",
    "UserRoleModel",
    "ResourcePermissionModel",
    "ResourceType",
    "PermissionScope",
    # Sync-specific enums
    "PermissionAction",
    "SyncResourceType",
    "FieldAccessLevel",
    "AuditEventType",
    # Sync-specific models
    "FieldPermissionModel",
    "DataAccessAuditModel",
]
