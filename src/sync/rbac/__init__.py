"""
Role-Based Access Control (RBAC) module for data sync system.

This module provides fine-grained permission control with tenant-level data isolation,
field-level permissions, and comprehensive audit logging.

NOTE: Core RBAC models (RoleModel, PermissionModel, etc.) are imported from
src.security.rbac_models to avoid duplicate model registration issues.
"""

from .models import (
    # Re-exported from security module
    RoleModel,
    PermissionModel,
    RolePermissionModel,
    UserRoleModel,
    ResourcePermissionModel,
    ResourceType,
    PermissionScope,
    # Sync-specific enums
    PermissionAction,
    SyncResourceType,
    FieldAccessLevel,
    AuditEventType,
    # Sync-specific models
    FieldPermissionModel,
    DataAccessAuditModel,
)

from .permission_manager import PermissionManager
from .rbac_service import RBACService
from .tenant_isolation import TenantIsolationService
from .field_access_control import FieldAccessController
from .audit_service import DataAccessAuditService

__all__ = [
    # Models (re-exported from security module)
    "RoleModel",
    "PermissionModel", 
    "RolePermissionModel",
    "UserRoleModel",
    "ResourcePermissionModel",
    # Enums
    "ResourceType",
    "PermissionScope",
    "PermissionAction",
    "SyncResourceType",
    "FieldAccessLevel",
    "AuditEventType",
    # Sync-specific models
    "FieldPermissionModel",
    "DataAccessAuditModel",
    # Services
    "PermissionManager",
    "RBACService",
    "TenantIsolationService",
    "FieldAccessController",
    "DataAccessAuditService",
]
