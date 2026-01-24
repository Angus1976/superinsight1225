"""Annotation RBAC Service for role-based access control.

This module provides comprehensive role-based access control for AI annotation operations:
- Permission definitions for all annotation operations
- Role-based permission checks
- Project-level and tenant-level permissions
- Permission inheritance and delegation
- Integration with audit logging

Requirements:
- 7.2: Role-based access control for annotations
- 7.6: Multi-tenant isolation
"""

import asyncio
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum


class AnnotationPermission(str, Enum):
    """Permissions for annotation operations."""
    # Annotation permissions
    ANNOTATION_CREATE = "annotation:create"
    ANNOTATION_READ = "annotation:read"
    ANNOTATION_UPDATE = "annotation:update"
    ANNOTATION_DELETE = "annotation:delete"
    ANNOTATION_SUBMIT = "annotation:submit"
    ANNOTATION_APPROVE = "annotation:approve"
    ANNOTATION_REJECT = "annotation:reject"
    ANNOTATION_EXPORT = "annotation:export"
    ANNOTATION_ROLLBACK = "annotation:rollback"

    # Task permissions
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"

    # Project permissions
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_MANAGE_USERS = "project:manage_users"
    PROJECT_MANAGE_SETTINGS = "project:manage_settings"

    # AI engine permissions
    ENGINE_USE = "engine:use"
    ENGINE_CONFIGURE = "engine:configure"
    ENGINE_MANAGE = "engine:manage"

    # Quality and validation permissions
    VALIDATION_RUN = "validation:run"
    VALIDATION_VIEW_REPORTS = "validation:view_reports"
    QUALITY_REVIEW = "quality:review"

    # Admin permissions
    ADMIN_AUDIT_VIEW = "admin:audit_view"
    ADMIN_AUDIT_EXPORT = "admin:audit_export"
    ADMIN_MANAGE_ROLES = "admin:manage_roles"
    ADMIN_MANAGE_PERMISSIONS = "admin:manage_permissions"


class AnnotationRole(str, Enum):
    """Predefined roles for annotation operations."""
    # System roles
    SYSTEM_ADMIN = "system_admin"
    TENANT_ADMIN = "tenant_admin"

    # Project roles
    PROJECT_MANAGER = "project_manager"
    PROJECT_REVIEWER = "project_reviewer"
    PROJECT_ANNOTATOR = "project_annotator"
    PROJECT_VIEWER = "project_viewer"

    # AI roles
    AI_ENGINEER = "ai_engineer"


@dataclass
class RoleDefinition:
    """Definition of a role with its permissions."""
    role_id: UUID = field(default_factory=uuid4)
    role_name: AnnotationRole = AnnotationRole.PROJECT_VIEWER
    display_name: str = ""
    description: str = ""
    permissions: Set[AnnotationPermission] = field(default_factory=set)
    is_system_role: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserRole:
    """User role assignment."""
    assignment_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    role: AnnotationRole = AnnotationRole.PROJECT_VIEWER
    scope: str = "tenant"  # "tenant", "project", "task"
    scope_id: Optional[UUID] = None  # Project ID or Task ID
    assigned_by: Optional[UUID] = None
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass
class PermissionCheck:
    """Result of a permission check."""
    allowed: bool = False
    user_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    permission: AnnotationPermission = AnnotationPermission.ANNOTATION_READ
    scope: str = "tenant"
    scope_id: Optional[UUID] = None
    matched_roles: List[AnnotationRole] = field(default_factory=list)
    reason: str = ""
    checked_at: datetime = field(default_factory=datetime.utcnow)


class AnnotationRBACService:
    """Service for role-based access control of annotation operations."""

    def __init__(self):
        """Initialize annotation RBAC service."""
        self._role_definitions: Dict[AnnotationRole, RoleDefinition] = {}
        self._user_roles: Dict[UUID, List[UserRole]] = {}  # user_id -> roles
        self._tenant_users: Dict[UUID, Set[UUID]] = {}  # tenant_id -> user_ids
        self._lock = asyncio.Lock()

        # Initialize default roles
        self._initialize_default_roles()

    def _initialize_default_roles(self):
        """Initialize default role definitions."""
        # System Admin - all permissions
        self._role_definitions[AnnotationRole.SYSTEM_ADMIN] = RoleDefinition(
            role_name=AnnotationRole.SYSTEM_ADMIN,
            display_name="System Administrator",
            description="Full access to all annotation operations",
            permissions=set(AnnotationPermission),
            is_system_role=True
        )

        # Tenant Admin - all tenant-scoped permissions
        self._role_definitions[AnnotationRole.TENANT_ADMIN] = RoleDefinition(
            role_name=AnnotationRole.TENANT_ADMIN,
            display_name="Tenant Administrator",
            description="Full access within tenant",
            permissions={
                AnnotationPermission.ANNOTATION_CREATE,
                AnnotationPermission.ANNOTATION_READ,
                AnnotationPermission.ANNOTATION_UPDATE,
                AnnotationPermission.ANNOTATION_DELETE,
                AnnotationPermission.ANNOTATION_SUBMIT,
                AnnotationPermission.ANNOTATION_APPROVE,
                AnnotationPermission.ANNOTATION_REJECT,
                AnnotationPermission.ANNOTATION_EXPORT,
                AnnotationPermission.ANNOTATION_ROLLBACK,
                AnnotationPermission.TASK_CREATE,
                AnnotationPermission.TASK_READ,
                AnnotationPermission.TASK_UPDATE,
                AnnotationPermission.TASK_DELETE,
                AnnotationPermission.TASK_ASSIGN,
                AnnotationPermission.PROJECT_CREATE,
                AnnotationPermission.PROJECT_READ,
                AnnotationPermission.PROJECT_UPDATE,
                AnnotationPermission.PROJECT_DELETE,
                AnnotationPermission.PROJECT_MANAGE_USERS,
                AnnotationPermission.PROJECT_MANAGE_SETTINGS,
                AnnotationPermission.ENGINE_USE,
                AnnotationPermission.ENGINE_CONFIGURE,
                AnnotationPermission.VALIDATION_RUN,
                AnnotationPermission.VALIDATION_VIEW_REPORTS,
                AnnotationPermission.QUALITY_REVIEW,
                AnnotationPermission.ADMIN_AUDIT_VIEW,
                AnnotationPermission.ADMIN_AUDIT_EXPORT,
                AnnotationPermission.ADMIN_MANAGE_ROLES,
                AnnotationPermission.ADMIN_MANAGE_PERMISSIONS,
            },
            is_system_role=True
        )

        # Project Manager
        self._role_definitions[AnnotationRole.PROJECT_MANAGER] = RoleDefinition(
            role_name=AnnotationRole.PROJECT_MANAGER,
            display_name="Project Manager",
            description="Manage project and its annotations",
            permissions={
                AnnotationPermission.ANNOTATION_CREATE,
                AnnotationPermission.ANNOTATION_READ,
                AnnotationPermission.ANNOTATION_UPDATE,
                AnnotationPermission.ANNOTATION_DELETE,
                AnnotationPermission.ANNOTATION_SUBMIT,
                AnnotationPermission.ANNOTATION_APPROVE,
                AnnotationPermission.ANNOTATION_REJECT,
                AnnotationPermission.ANNOTATION_EXPORT,
                AnnotationPermission.TASK_CREATE,
                AnnotationPermission.TASK_READ,
                AnnotationPermission.TASK_UPDATE,
                AnnotationPermission.TASK_DELETE,
                AnnotationPermission.TASK_ASSIGN,
                AnnotationPermission.PROJECT_READ,
                AnnotationPermission.PROJECT_UPDATE,
                AnnotationPermission.PROJECT_MANAGE_USERS,
                AnnotationPermission.PROJECT_MANAGE_SETTINGS,
                AnnotationPermission.ENGINE_USE,
                AnnotationPermission.ENGINE_CONFIGURE,
                AnnotationPermission.VALIDATION_RUN,
                AnnotationPermission.VALIDATION_VIEW_REPORTS,
                AnnotationPermission.QUALITY_REVIEW,
            },
            is_system_role=True
        )

        # Project Reviewer
        self._role_definitions[AnnotationRole.PROJECT_REVIEWER] = RoleDefinition(
            role_name=AnnotationRole.PROJECT_REVIEWER,
            display_name="Project Reviewer",
            description="Review and approve annotations",
            permissions={
                AnnotationPermission.ANNOTATION_READ,
                AnnotationPermission.ANNOTATION_APPROVE,
                AnnotationPermission.ANNOTATION_REJECT,
                AnnotationPermission.TASK_READ,
                AnnotationPermission.PROJECT_READ,
                AnnotationPermission.ENGINE_USE,
                AnnotationPermission.VALIDATION_RUN,
                AnnotationPermission.VALIDATION_VIEW_REPORTS,
                AnnotationPermission.QUALITY_REVIEW,
            },
            is_system_role=True
        )

        # Project Annotator
        self._role_definitions[AnnotationRole.PROJECT_ANNOTATOR] = RoleDefinition(
            role_name=AnnotationRole.PROJECT_ANNOTATOR,
            display_name="Project Annotator",
            description="Create and update annotations",
            permissions={
                AnnotationPermission.ANNOTATION_CREATE,
                AnnotationPermission.ANNOTATION_READ,
                AnnotationPermission.ANNOTATION_UPDATE,
                AnnotationPermission.ANNOTATION_SUBMIT,
                AnnotationPermission.TASK_READ,
                AnnotationPermission.PROJECT_READ,
                AnnotationPermission.ENGINE_USE,
            },
            is_system_role=True
        )

        # Project Viewer
        self._role_definitions[AnnotationRole.PROJECT_VIEWER] = RoleDefinition(
            role_name=AnnotationRole.PROJECT_VIEWER,
            display_name="Project Viewer",
            description="View annotations and projects",
            permissions={
                AnnotationPermission.ANNOTATION_READ,
                AnnotationPermission.TASK_READ,
                AnnotationPermission.PROJECT_READ,
                AnnotationPermission.VALIDATION_VIEW_REPORTS,
            },
            is_system_role=True
        )

        # AI Engineer
        self._role_definitions[AnnotationRole.AI_ENGINEER] = RoleDefinition(
            role_name=AnnotationRole.AI_ENGINEER,
            display_name="AI Engineer",
            description="Configure and manage AI engines",
            permissions={
                AnnotationPermission.ANNOTATION_READ,
                AnnotationPermission.ANNOTATION_EXPORT,
                AnnotationPermission.PROJECT_READ,
                AnnotationPermission.ENGINE_USE,
                AnnotationPermission.ENGINE_CONFIGURE,
                AnnotationPermission.ENGINE_MANAGE,
                AnnotationPermission.VALIDATION_RUN,
                AnnotationPermission.VALIDATION_VIEW_REPORTS,
            },
            is_system_role=True
        )

    async def assign_role(
        self,
        tenant_id: UUID,
        user_id: UUID,
        role: AnnotationRole,
        scope: str = "tenant",
        scope_id: Optional[UUID] = None,
        assigned_by: Optional[UUID] = None,
        expires_at: Optional[datetime] = None
    ) -> UserRole:
        """Assign a role to a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            role: Role to assign
            scope: Scope of the role ("tenant", "project", "task")
            scope_id: ID of the scope (project ID or task ID)
            assigned_by: User who assigned this role
            expires_at: Optional expiration date

        Returns:
            Created user role assignment
        """
        async with self._lock:
            user_role = UserRole(
                tenant_id=tenant_id,
                user_id=user_id,
                role=role,
                scope=scope,
                scope_id=scope_id,
                assigned_by=assigned_by,
                expires_at=expires_at
            )

            if user_id not in self._user_roles:
                self._user_roles[user_id] = []
            self._user_roles[user_id].append(user_role)

            if tenant_id not in self._tenant_users:
                self._tenant_users[tenant_id] = set()
            self._tenant_users[tenant_id].add(user_id)

            return user_role

    async def revoke_role(
        self,
        tenant_id: UUID,
        user_id: UUID,
        assignment_id: UUID
    ) -> bool:
        """Revoke a role assignment.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            assignment_id: Assignment ID to revoke

        Returns:
            True if revoked, False if not found
        """
        async with self._lock:
            if user_id not in self._user_roles:
                return False

            roles = self._user_roles[user_id]
            for i, role in enumerate(roles):
                if role.assignment_id == assignment_id and role.tenant_id == tenant_id:
                    roles.pop(i)
                    return True

            return False

    async def get_user_roles(
        self,
        tenant_id: UUID,
        user_id: UUID,
        scope: Optional[str] = None,
        scope_id: Optional[UUID] = None
    ) -> List[UserRole]:
        """Get all roles for a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            scope: Optional scope filter
            scope_id: Optional scope ID filter

        Returns:
            List of user role assignments
        """
        async with self._lock:
            if user_id not in self._user_roles:
                return []

            roles = [
                r for r in self._user_roles[user_id]
                if r.tenant_id == tenant_id
            ]

            # Filter by scope
            if scope:
                roles = [r for r in roles if r.scope == scope]

            # Filter by scope_id
            if scope_id:
                roles = [r for r in roles if r.scope_id == scope_id]

            # Remove expired roles
            now = datetime.utcnow()
            roles = [
                r for r in roles
                if r.expires_at is None or r.expires_at > now
            ]

            return roles

    async def check_permission(
        self,
        tenant_id: UUID,
        user_id: UUID,
        permission: AnnotationPermission,
        scope: str = "tenant",
        scope_id: Optional[UUID] = None
    ) -> PermissionCheck:
        """Check if a user has a specific permission.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            permission: Permission to check
            scope: Scope to check ("tenant", "project", "task")
            scope_id: Scope ID (project ID or task ID)

        Returns:
            Permission check result
        """
        async with self._lock:
            # Get user roles
            user_roles = await self.get_user_roles(
                tenant_id=tenant_id,
                user_id=user_id
            )

            matched_roles = []
            allowed = False

            # Check each role
            for user_role in user_roles:
                role_def = self._role_definitions.get(user_role.role)
                if not role_def:
                    continue

                # Check if role has the permission
                if permission not in role_def.permissions:
                    continue

                # Check scope hierarchy
                # Tenant-level roles grant access to all projects and tasks
                if user_role.scope == "tenant":
                    matched_roles.append(user_role.role)
                    allowed = True
                    break

                # Project-level roles grant access to the specific project and its tasks
                elif user_role.scope == "project":
                    if scope == "project" and scope_id == user_role.scope_id:
                        matched_roles.append(user_role.role)
                        allowed = True
                        break
                    elif scope == "task":
                        # Would need to check if task belongs to project
                        # For now, grant access
                        matched_roles.append(user_role.role)
                        allowed = True
                        break

                # Task-level roles grant access only to the specific task
                elif user_role.scope == "task":
                    if scope == "task" and scope_id == user_role.scope_id:
                        matched_roles.append(user_role.role)
                        allowed = True
                        break

            reason = ""
            if not allowed:
                if not user_roles:
                    reason = f"User has no roles in tenant {tenant_id}"
                else:
                    reason = f"None of user's roles grant permission {permission.value}"

            return PermissionCheck(
                allowed=allowed,
                user_id=user_id,
                tenant_id=tenant_id,
                permission=permission,
                scope=scope,
                scope_id=scope_id,
                matched_roles=matched_roles,
                reason=reason
            )

    async def check_permissions(
        self,
        tenant_id: UUID,
        user_id: UUID,
        permissions: List[AnnotationPermission],
        scope: str = "tenant",
        scope_id: Optional[UUID] = None,
        require_all: bool = True
    ) -> PermissionCheck:
        """Check if a user has multiple permissions.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            permissions: List of permissions to check
            scope: Scope to check
            scope_id: Scope ID
            require_all: If True, user must have all permissions; if False, any permission is sufficient

        Returns:
            Permission check result
        """
        checks = []
        for permission in permissions:
            check = await self.check_permission(
                tenant_id=tenant_id,
                user_id=user_id,
                permission=permission,
                scope=scope,
                scope_id=scope_id
            )
            checks.append(check)

        if require_all:
            allowed = all(c.allowed for c in checks)
            matched_roles = list(set(
                role
                for check in checks
                for role in check.matched_roles
            ))
            reason = "; ".join(c.reason for c in checks if not c.allowed)
        else:
            allowed = any(c.allowed for c in checks)
            matched_roles = list(set(
                role
                for check in checks
                if check.allowed
                for role in check.matched_roles
            ))
            reason = "No matching permissions found" if not allowed else ""

        return PermissionCheck(
            allowed=allowed,
            user_id=user_id,
            tenant_id=tenant_id,
            permission=permissions[0] if permissions else AnnotationPermission.ANNOTATION_READ,
            scope=scope,
            scope_id=scope_id,
            matched_roles=matched_roles,
            reason=reason
        )

    async def get_role_definition(
        self,
        role: AnnotationRole
    ) -> Optional[RoleDefinition]:
        """Get role definition.

        Args:
            role: Role name

        Returns:
            Role definition or None
        """
        async with self._lock:
            return self._role_definitions.get(role)

    async def get_user_permissions(
        self,
        tenant_id: UUID,
        user_id: UUID,
        scope: Optional[str] = None,
        scope_id: Optional[UUID] = None
    ) -> Set[AnnotationPermission]:
        """Get all permissions for a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            scope: Optional scope filter
            scope_id: Optional scope ID filter

        Returns:
            Set of permissions
        """
        async with self._lock:
            user_roles = await self.get_user_roles(
                tenant_id=tenant_id,
                user_id=user_id,
                scope=scope,
                scope_id=scope_id
            )

            permissions = set()
            for user_role in user_roles:
                role_def = self._role_definitions.get(user_role.role)
                if role_def:
                    permissions.update(role_def.permissions)

            return permissions

    async def enforce_permission(
        self,
        tenant_id: UUID,
        user_id: UUID,
        permission: AnnotationPermission,
        scope: str = "tenant",
        scope_id: Optional[UUID] = None
    ) -> PermissionCheck:
        """Enforce a permission check, raising an exception if denied.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            permission: Permission to check
            scope: Scope to check
            scope_id: Scope ID

        Returns:
            Permission check result (only if allowed)

        Raises:
            PermissionError: If permission is denied
        """
        check = await self.check_permission(
            tenant_id=tenant_id,
            user_id=user_id,
            permission=permission,
            scope=scope,
            scope_id=scope_id
        )

        if not check.allowed:
            raise PermissionError(
                f"Permission denied: {check.reason}"
            )

        return check


# Global instance
_annotation_rbac_service: Optional[AnnotationRBACService] = None
_rbac_lock = asyncio.Lock()


async def get_annotation_rbac_service() -> AnnotationRBACService:
    """Get or create the global annotation RBAC service.

    Returns:
        Annotation RBAC service instance
    """
    global _annotation_rbac_service

    async with _rbac_lock:
        if _annotation_rbac_service is None:
            _annotation_rbac_service = AnnotationRBACService()
        return _annotation_rbac_service


async def reset_annotation_rbac_service():
    """Reset the global annotation RBAC service (for testing)."""
    global _annotation_rbac_service

    async with _rbac_lock:
        _annotation_rbac_service = None
