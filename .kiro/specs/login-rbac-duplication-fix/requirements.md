# Login RBAC Duplication Fix - Requirements

## 1. Overview

**Feature Name**: Login RBAC Duplication Fix  
**Priority**: P0 (Critical - Blocking login functionality)  
**Created**: 2026-01-19  
**Status**: Planning

## 2. Problem Statement

The login functionality is broken due to duplicate `RoleModel` class definitions in the codebase, causing SQLAlchemy registry conflicts. Additionally, the tenant selection feature is not working as the backend returns a hardcoded single tenant.

### 2.1 Current Issues

1. **Login returns 500 Internal Server Error**
   - Error message: "Multiple classes found for path 'RoleModel' in the registry"
   - Root cause: Two `RoleModel` classes with same `__tablename__` registered in SQLAlchemy

2. **Tenant selection not displayed**
   - Frontend has tenant selection UI but it's hidden when `tenants.length === 0`
   - Backend `/auth/tenants` endpoint returns hardcoded single tenant
   - Users cannot select their organization during login

## 3. User Stories

### 3.1 As a System Administrator
**I want** the login system to work without internal server errors  
**So that** users can authenticate and access the platform

**Priority**: P0  
**Acceptance Criteria** (EARS):
- WHEN a user submits valid credentials, THEN the system authenticates successfully without 500 errors
- WHEN SQLAlchemy initializes, THEN no duplicate model registration errors occur
- WHEN the application starts, THEN all RBAC models are properly registered once

### 3.2 As a User
**I want** to select my organization during login  
**So that** I can access the correct tenant's data

**Priority**: P1  
**Acceptance Criteria** (EARS):
- WHEN I navigate to the login page, THEN I see a tenant/organization selector if multiple tenants exist
- WHEN I select a tenant and login, THEN I am authenticated to that specific tenant
- WHEN only one tenant exists, THEN the tenant is auto-selected and selector is hidden

### 3.3 As a Developer
**I want** a single source of truth for RBAC models  
**So that** the codebase is maintainable and consistent

**Priority**: P1  
**Acceptance Criteria** (EARS):
- WHEN importing RoleModel, THEN there is only one canonical import path
- WHEN reviewing RBAC code, THEN all models are in a single, well-documented location
- WHEN adding new RBAC features, THEN the model location is clear and unambiguous

## 4. Technical Context

### 4.1 Duplicate RoleModel Locations

**Location 1**: `src/sync/rbac/models.py` (line 67)
- Uses `UUID(as_uuid=True)` and `JSONB`
- Part of data sync system's RBAC implementation
- More comprehensive with field-level permissions

**Location 2**: `src/security/rbac_models.py` (line 44)
- Uses `PostgresUUID(as_uuid=True)` and `JSON`
- Part of core security system
- More focused on role hierarchy and permission groups

**Common Issues**:
- Both use `__tablename__ = "rbac_roles"`
- Both inherit from `src.database.connection.Base`
- Both get registered in SQLAlchemy's model registry
- Conflict occurs during application initialization

### 4.2 Tenant Selection Implementation

**Frontend**: `frontend/src/components/Auth/LoginForm.tsx`
- Has tenant selection UI implemented
- Calls `authService.getTenants()` on mount
- Shows selector only when `tenants.length > 0`

**Backend**: `src/api/auth.py` (line 208)
- Endpoint: `GET /auth/tenants`
- Currently returns hardcoded single tenant:
  ```python
  return [{"id": "default_tenant", "name": "Default Tenant", "logo": None}]
  ```
- Needs database query implementation

## 5. Dependencies

### 5.1 Related Specs
- `.kiro/specs/api-registration-fix` - Work in progress when issue appeared
- `.kiro/specs/audit-security` - Contains RBAC audit functionality
- `.kiro/specs/multi-tenant-workspace` - Multi-tenant architecture

### 5.2 Database Tables
- `rbac_roles` - Role definitions
- `rbac_permissions` - Permission definitions
- `rbac_user_roles` - User-role assignments
- `tenants` or equivalent - Tenant/organization data

### 5.3 Affected Components
- Authentication system (`src/api/auth.py`)
- Security controller (`src/security/controller.py`)
- RBAC models (both locations)
- Login form (`frontend/src/components/Auth/LoginForm.tsx`)

## 6. Non-Functional Requirements

### 6.1 Performance
- Login response time: < 500ms
- Tenant list loading: < 200ms
- No performance degradation from model consolidation

### 6.2 Security
- No security vulnerabilities introduced during refactoring
- Maintain existing authentication and authorization logic
- Preserve audit logging functionality

### 6.3 Compatibility
- Backward compatible with existing database schema
- No breaking changes to API contracts
- Existing user sessions remain valid

### 6.4 Maintainability
- Clear documentation of model location
- Single import path for all RBAC models
- Consistent naming conventions

## 7. Constraints

### 7.1 Technical Constraints
- Must not break existing functionality
- Must maintain database schema compatibility
- Must preserve all existing RBAC features from both implementations

### 7.2 Timeline Constraints
- Critical priority - should be fixed immediately
- Blocking user access to the system

### 7.3 Resource Constraints
- Must be implementable without database migration
- Should minimize code changes to reduce risk

## 8. Success Criteria

### 8.1 Login Functionality
- ✅ Users can login without 500 errors
- ✅ All three test accounts work: admin_user, business_expert, tech_expert
- ✅ JWT tokens are generated correctly
- ✅ User sessions are maintained properly

### 8.2 Tenant Selection
- ✅ Tenant selector appears when multiple tenants exist
- ✅ Users can select their organization
- ✅ Login succeeds with selected tenant
- ✅ Single tenant auto-selects without showing selector

### 8.3 Code Quality
- ✅ No duplicate model definitions
- ✅ Single canonical import path for RoleModel
- ✅ All imports updated consistently
- ✅ No SQLAlchemy registry warnings or errors

### 8.4 Testing
- ✅ All existing tests pass
- ✅ New tests cover the fix
- ✅ Manual testing confirms login works
- ✅ No regression in other features

## 9. Out of Scope

The following are explicitly out of scope for this fix:

- Adding new RBAC features
- Modifying permission logic
- Changing database schema
- Implementing new tenant management features
- Refactoring unrelated authentication code

## 10. References

### 10.1 Related Documents
- `PROBLEM_ANALYSIS_2026_01_19.md` - Detailed problem analysis
- `LOGIN_CREDENTIALS_2026_01_19.md` - Test account credentials
- `.kiro/steering/async-sync-safety.md` - Async/sync safety rules
- `.kiro/steering/structure.md` - Project structure guidelines

### 10.2 Related Code
- `src/sync/rbac/models.py` - Duplicate RoleModel location 1
- `src/security/rbac_models.py` - Duplicate RoleModel location 2
- `src/api/auth.py` - Authentication endpoints
- `frontend/src/components/Auth/LoginForm.tsx` - Login form UI

### 10.3 Test Accounts
- admin_user / Admin@123456
- business_expert / Business@123456
- tech_expert / Tech@123456
