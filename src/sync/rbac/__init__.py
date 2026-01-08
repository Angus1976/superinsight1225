"""
Role-Based Access Control (RBAC) module for data sync system.

This module provides fine-grained permission control with tenant-level data isolation,
field-level permissions, and comprehensive audit logging.
"""

from .models import (
    RoleModel,
    PermissionModel,
    RolePermissionModel,
    UserRoleModel,
    ResourcePermissionModel,
    FieldPermissionModel,
    DataAccessAuditModel
)

from .permission_manager import PermissionManager
from .rbac_service import RBACService
from .tenant_isolation import TenantIsolationService
from .field_access_control import FieldAccessController
from .audit_service import DataAccessAuditService

__all__ = [
    # Models
    "RoleModel",
    "PermissionModel", 
    "RolePermissionModel",
    "UserRoleModel",
    "ResourcePermissionModel",
    "FieldPermissionModel",
    "DataAccessAuditModel",
    
    # Services
    "PermissionManager",
    "RBACService",
    "TenantIsolationService",
    "FieldAccessController",
    "DataAccessAuditService"
]