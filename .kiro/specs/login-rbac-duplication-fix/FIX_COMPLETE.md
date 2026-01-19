# Login RBAC Duplication Fix - Complete

**Date**: 2026-01-19  
**Status**: ✅ Fixed

## Problem Summary

Login was returning 500 Internal Server Error with message:
> "Multiple classes found for path 'RoleModel' in the registry of this declarative base"

## Root Cause

Three `RoleModel` classes were being registered in SQLAlchemy's declarative base registry:

1. `src/security/rbac_models.py` - `RoleModel` with `__tablename__ = "rbac_roles"` (canonical)
2. `src/sync/rbac/models.py` - `RoleModel` with `__tablename__ = "rbac_roles"` (duplicate)
3. `src/models/security.py` - `RoleModel` with `__tablename__ = "security_roles"` (naming conflict)

Even though #3 used a different table name, SQLAlchemy's registry complained about multiple classes with the same name "RoleModel".

## Solution Applied

### Fix 1: Consolidated sync/rbac/models.py
Modified `src/sync/rbac/models.py` to re-export models from `src/security/rbac_models.py` instead of defining its own:

```python
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
```

Only sync-specific models (`FieldPermissionModel`, `DataAccessAuditModel`) are defined locally.

### Fix 2: Renamed RoleModel in models/security.py
Renamed `RoleModel` to `SecurityRoleModel` in `src/models/security.py` to avoid naming conflict:

```python
class SecurityRoleModel(Base):
    """
    Enhanced role model for RBAC system.
    NOTE: This is a separate security-specific role model with table 'security_roles'.
    The main RBAC RoleModel is in src/security/rbac_models.py with table 'rbac_roles'.
    """
    __tablename__ = "security_roles"
```

### Fix 3: Updated tenant_permissions.py import
Changed import in `src/security/tenant_permissions.py` from `src.sync.rbac.models` to `src.security.rbac_models`.

### Fix 4: Implemented real tenant query
Updated `src/api/auth.py` `/auth/tenants` endpoint to query tenants from database with fallback to default tenant.

## Files Modified

1. `src/sync/rbac/models.py` - Re-export from security module
2. `src/sync/rbac/__init__.py` - Updated exports
3. `src/sync/rbac/permission_manager.py` - Updated imports
4. `src/sync/rbac/rbac_service.py` - Updated imports
5. `src/sync/rbac/audit_service.py` - Updated imports
6. `src/models/security.py` - Renamed RoleModel to SecurityRoleModel
7. `src/security/tenant_permissions.py` - Fixed import path
8. `src/api/auth.py` - Implemented real tenant query

## Verification

### Login Test Results
```bash
# admin_user login - SUCCESS
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}'

# Response: JWT token and user info returned successfully
```

### Tenants Endpoint
```bash
curl http://localhost:8000/auth/tenants
# Response: [{"id": "default_tenant", "name": "Default Tenant", "logo": null}]
```

## Architecture After Fix

```
src/security/rbac_models.py (CANONICAL)
├── RoleModel (__tablename__ = "rbac_roles")
├── PermissionModel
├── RolePermissionModel
├── UserRoleModel
└── ResourcePermissionModel

src/sync/rbac/models.py (RE-EXPORTS + SYNC-SPECIFIC)
├── Re-exports from src.security.rbac_models
├── FieldPermissionModel (sync-specific)
└── DataAccessAuditModel (sync-specific)

src/models/security.py (SEPARATE SECURITY MODELS)
├── SecurityRoleModel (__tablename__ = "security_roles")
├── UserRoleAssignmentModel
├── DynamicPolicyModel
├── SSOProviderModel
├── AuditLogModel
├── SecurityEventModel
└── ... other security models
```

## Lessons Learned

1. **Single Source of Truth**: Always have one canonical location for shared models
2. **Naming Conventions**: Use unique class names even if table names differ
3. **Import Consolidation**: Re-export from canonical location rather than duplicate
4. **SQLAlchemy Registry**: The registry tracks class names, not just table names
