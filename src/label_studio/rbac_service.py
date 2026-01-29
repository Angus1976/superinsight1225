"""
Role-Based Access Control (RBAC) Service for Label Studio Enterprise Workspace.

This module provides permission management based on workspace member roles,
implementing a hierarchical permission system.

Role Hierarchy (highest to lowest):
1. OWNER - Full control over workspace
2. ADMIN - All permissions except delete workspace
3. MANAGER - Manage projects and view members
4. REVIEWER - Review annotations
5. ANNOTATOR - Basic annotation permissions

Permission Categories:
- Workspace: view, edit, delete, manage_members
- Project: view, create, edit, delete, manage_members
- Task: view, annotate, review, assign
- Data: export, import
"""

import logging
from enum import Enum, auto
from typing import Optional, Set, List, Dict, Any
from uuid import UUID
from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.label_studio.workspace_models import (
    LabelStudioWorkspaceModel,
    LabelStudioWorkspaceMemberModel,
    WorkspaceProjectModel,
    ProjectMemberModel,
    WorkspaceMemberRole,
    ProjectMemberRole,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Permission Enumeration
# ============================================================================

class Permission(str, Enum):
    """
    Permission enumeration for RBAC system.

    Permissions are grouped by resource type:
    - WORKSPACE_*: Workspace-level operations
    - PROJECT_*: Project-level operations
    - TASK_*: Task-level operations
    - DATA_*: Data import/export operations
    """
    # Workspace permissions
    WORKSPACE_VIEW = "workspace:view"
    WORKSPACE_EDIT = "workspace:edit"
    WORKSPACE_DELETE = "workspace:delete"
    WORKSPACE_MANAGE_MEMBERS = "workspace:manage_members"

    # Project permissions
    PROJECT_VIEW = "project:view"
    PROJECT_CREATE = "project:create"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"
    PROJECT_MANAGE_MEMBERS = "project:manage_members"

    # Task permissions
    TASK_VIEW = "task:view"
    TASK_ANNOTATE = "task:annotate"
    TASK_REVIEW = "task:review"
    TASK_ASSIGN = "task:assign"

    # Data permissions
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"


# ============================================================================
# Role Permission Matrix
# ============================================================================

# Define permissions for each workspace role
ROLE_PERMISSIONS: Dict[WorkspaceMemberRole, Set[Permission]] = {
    WorkspaceMemberRole.OWNER: {
        # Owner has ALL permissions
        Permission.WORKSPACE_VIEW,
        Permission.WORKSPACE_EDIT,
        Permission.WORKSPACE_DELETE,
        Permission.WORKSPACE_MANAGE_MEMBERS,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_MANAGE_MEMBERS,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
        Permission.TASK_REVIEW,
        Permission.TASK_ASSIGN,
        Permission.DATA_EXPORT,
        Permission.DATA_IMPORT,
    },
    WorkspaceMemberRole.ADMIN: {
        # Admin has all except WORKSPACE_DELETE
        Permission.WORKSPACE_VIEW,
        Permission.WORKSPACE_EDIT,
        Permission.WORKSPACE_MANAGE_MEMBERS,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_MANAGE_MEMBERS,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
        Permission.TASK_REVIEW,
        Permission.TASK_ASSIGN,
        Permission.DATA_EXPORT,
        Permission.DATA_IMPORT,
    },
    WorkspaceMemberRole.MANAGER: {
        # Manager can manage projects but not workspace members
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_MANAGE_MEMBERS,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
        Permission.TASK_REVIEW,
        Permission.TASK_ASSIGN,
        Permission.DATA_EXPORT,
        Permission.DATA_IMPORT,
    },
    WorkspaceMemberRole.REVIEWER: {
        # Reviewer can view and review annotations
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
        Permission.TASK_REVIEW,
        Permission.DATA_EXPORT,
    },
    WorkspaceMemberRole.ANNOTATOR: {
        # Annotator has basic view and annotate permissions
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
    },
}

# Role hierarchy for comparison (higher index = higher rank)
ROLE_HIERARCHY: List[WorkspaceMemberRole] = [
    WorkspaceMemberRole.ANNOTATOR,
    WorkspaceMemberRole.REVIEWER,
    WorkspaceMemberRole.MANAGER,
    WorkspaceMemberRole.ADMIN,
    WorkspaceMemberRole.OWNER,
]


# ============================================================================
# Exceptions
# ============================================================================

class RBACError(Exception):
    """Base exception for RBAC errors."""
    pass


class PermissionDeniedError(RBACError):
    """Exception raised when permission is denied."""

    def __init__(
        self,
        user_id: UUID,
        permission: Permission,
        workspace_id: Optional[UUID] = None,
        project_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.permission = permission
        self.workspace_id = workspace_id
        self.project_id = project_id

        message = f"User '{user_id}' lacks permission '{permission.value}'"
        if workspace_id:
            message += f" in workspace '{workspace_id}'"
        if project_id:
            message += f" for project '{project_id}'"

        super().__init__(message)


class NotAMemberError(RBACError):
    """Exception raised when user is not a member."""

    def __init__(self, user_id: UUID, workspace_id: UUID):
        self.user_id = user_id
        self.workspace_id = workspace_id
        super().__init__(
            f"User '{user_id}' is not a member of workspace '{workspace_id}'"
        )


# ============================================================================
# RBAC Service
# ============================================================================

class RBACService:
    """
    Role-Based Access Control Service.

    Provides permission checking and management based on workspace member roles.

    Thread-safety: Methods are stateless and can be called concurrently
    with different session objects.

    Example Usage:
        rbac = RBACService(session)

        # Check if user can edit workspace
        if rbac.check_permission(user_id, workspace_id, Permission.WORKSPACE_EDIT):
            # User has permission
            pass

        # Get all user permissions
        permissions = rbac.get_user_permissions(user_id, workspace_id)

        # Check project access
        can_access = rbac.can_access_project(user_id, workspace_id, project_id)
    """

    def __init__(self, session: Session):
        """
        Initialize RBACService.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def check_permission(
        self,
        user_id: UUID,
        workspace_id: UUID,
        permission: Permission,
    ) -> bool:
        """
        Check if user has a specific permission in workspace.

        Args:
            user_id: User UUID
            workspace_id: Workspace UUID
            permission: Permission to check

        Returns:
            True if user has the permission, False otherwise
        """
        role = self._get_user_role(workspace_id, user_id)
        if role is None:
            return False

        user_permissions = ROLE_PERMISSIONS.get(role, set())
        return permission in user_permissions

    def require_permission(
        self,
        user_id: UUID,
        workspace_id: UUID,
        permission: Permission,
    ) -> None:
        """
        Require user to have a specific permission.

        Args:
            user_id: User UUID
            workspace_id: Workspace UUID
            permission: Required permission

        Raises:
            NotAMemberError: If user is not a member
            PermissionDeniedError: If user lacks the permission
        """
        role = self._get_user_role(workspace_id, user_id)
        if role is None:
            raise NotAMemberError(user_id, workspace_id)

        if not self.check_permission(user_id, workspace_id, permission):
            raise PermissionDeniedError(
                user_id=user_id,
                permission=permission,
                workspace_id=workspace_id
            )

    def get_user_permissions(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> Set[Permission]:
        """
        Get all permissions for user in workspace.

        Args:
            user_id: User UUID
            workspace_id: Workspace UUID

        Returns:
            Set of permissions the user has, empty set if not a member
        """
        role = self._get_user_role(workspace_id, user_id)
        if role is None:
            return set()

        return ROLE_PERMISSIONS.get(role, set()).copy()

    def get_user_permissions_list(
        self,
        user_id: UUID,
        workspace_id: UUID,
    ) -> List[str]:
        """
        Get all permission values as list of strings.

        Args:
            user_id: User UUID
            workspace_id: Workspace UUID

        Returns:
            List of permission value strings
        """
        permissions = self.get_user_permissions(user_id, workspace_id)
        return [p.value for p in permissions]

    def can_access_project(
        self,
        user_id: UUID,
        workspace_id: UUID,
        project_id: str,
    ) -> bool:
        """
        Check if user can access a specific project.

        Access is granted if:
        1. User has PROJECT_VIEW permission in workspace, OR
        2. User is specifically assigned to the project

        Args:
            user_id: User UUID
            workspace_id: Workspace UUID
            project_id: Label Studio project ID

        Returns:
            True if user can access the project
        """
        # Check workspace-level permission
        if self.check_permission(user_id, workspace_id, Permission.PROJECT_VIEW):
            return True

        # Check project-level assignment
        workspace_project = self.session.query(WorkspaceProjectModel).filter(
            and_(
                WorkspaceProjectModel.workspace_id == workspace_id,
                WorkspaceProjectModel.label_studio_project_id == project_id
            )
        ).first()

        if not workspace_project:
            return False

        # Check if user is assigned to project
        project_member = self.session.query(ProjectMemberModel).filter(
            and_(
                ProjectMemberModel.workspace_project_id == workspace_project.id,
                ProjectMemberModel.user_id == user_id,
                ProjectMemberModel.is_active == True
            )
        ).first()

        return project_member is not None

    def can_perform_action(
        self,
        user_id: UUID,
        workspace_id: UUID,
        action: str,
    ) -> bool:
        """
        Check if user can perform a named action.

        Maps common action names to permissions:
        - "view", "read" -> PROJECT_VIEW
        - "create" -> PROJECT_CREATE
        - "edit", "update" -> PROJECT_EDIT
        - "delete" -> PROJECT_DELETE
        - "annotate" -> TASK_ANNOTATE
        - "review" -> TASK_REVIEW

        Args:
            user_id: User UUID
            workspace_id: Workspace UUID
            action: Action name

        Returns:
            True if user can perform the action
        """
        action_permission_map = {
            "view": Permission.PROJECT_VIEW,
            "read": Permission.PROJECT_VIEW,
            "create": Permission.PROJECT_CREATE,
            "edit": Permission.PROJECT_EDIT,
            "update": Permission.PROJECT_EDIT,
            "delete": Permission.PROJECT_DELETE,
            "annotate": Permission.TASK_ANNOTATE,
            "review": Permission.TASK_REVIEW,
            "export": Permission.DATA_EXPORT,
            "import": Permission.DATA_IMPORT,
        }

        permission = action_permission_map.get(action.lower())
        if permission is None:
            logger.warning(f"Unknown action: {action}")
            return False

        return self.check_permission(user_id, workspace_id, permission)

    def get_role_permissions(
        self,
        role: WorkspaceMemberRole,
    ) -> Set[Permission]:
        """
        Get all permissions for a role.

        Args:
            role: Workspace member role

        Returns:
            Set of permissions for the role
        """
        return ROLE_PERMISSIONS.get(role, set()).copy()

    def get_role_permissions_list(
        self,
        role: WorkspaceMemberRole,
    ) -> List[str]:
        """
        Get all permission values for a role as list of strings.

        Args:
            role: Workspace member role

        Returns:
            List of permission value strings
        """
        return [p.value for p in self.get_role_permissions(role)]

    def compare_roles(
        self,
        role1: WorkspaceMemberRole,
        role2: WorkspaceMemberRole,
    ) -> int:
        """
        Compare two roles in the hierarchy.

        Args:
            role1: First role
            role2: Second role

        Returns:
            - Positive if role1 > role2
            - Negative if role1 < role2
            - Zero if equal
        """
        index1 = ROLE_HIERARCHY.index(role1)
        index2 = ROLE_HIERARCHY.index(role2)
        return index1 - index2

    def is_higher_role(
        self,
        role1: WorkspaceMemberRole,
        role2: WorkspaceMemberRole,
    ) -> bool:
        """
        Check if role1 is higher than role2 in hierarchy.

        Args:
            role1: First role
            role2: Second role

        Returns:
            True if role1 > role2
        """
        return self.compare_roles(role1, role2) > 0

    def can_manage_role(
        self,
        manager_role: WorkspaceMemberRole,
        target_role: WorkspaceMemberRole,
    ) -> bool:
        """
        Check if a role can manage (add/remove/modify) another role.

        Rules:
        - OWNER can manage all roles
        - ADMIN can manage MANAGER, REVIEWER, ANNOTATOR
        - MANAGER cannot manage roles
        - Lower roles cannot manage any roles

        Args:
            manager_role: Role of the user performing management
            target_role: Role being managed

        Returns:
            True if manager_role can manage target_role
        """
        if manager_role == WorkspaceMemberRole.OWNER:
            return True

        if manager_role == WorkspaceMemberRole.ADMIN:
            # Admin cannot manage OWNER or other ADMIN
            return target_role not in {
                WorkspaceMemberRole.OWNER,
                WorkspaceMemberRole.ADMIN
            }

        return False

    def get_manageable_roles(
        self,
        manager_role: WorkspaceMemberRole,
    ) -> List[WorkspaceMemberRole]:
        """
        Get list of roles that can be managed by a given role.

        Args:
            manager_role: Role of the manager

        Returns:
            List of roles that can be managed
        """
        if manager_role == WorkspaceMemberRole.OWNER:
            return list(WorkspaceMemberRole)

        if manager_role == WorkspaceMemberRole.ADMIN:
            return [
                WorkspaceMemberRole.MANAGER,
                WorkspaceMemberRole.REVIEWER,
                WorkspaceMemberRole.ANNOTATOR,
            ]

        return []

    # ========== Helper Methods ==========

    def _get_user_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Optional[WorkspaceMemberRole]:
        """Get user's role in workspace."""
        member = self.session.query(LabelStudioWorkspaceMemberModel).filter(
            and_(
                LabelStudioWorkspaceMemberModel.workspace_id == workspace_id,
                LabelStudioWorkspaceMemberModel.user_id == user_id,
                LabelStudioWorkspaceMemberModel.is_active == True
            )
        ).first()

        if member:
            return member.role
        return None

    def get_permission_description(
        self,
        permission: Permission,
    ) -> str:
        """
        Get human-readable description of a permission.

        Args:
            permission: Permission to describe

        Returns:
            Description string
        """
        descriptions = {
            Permission.WORKSPACE_VIEW: "View workspace details",
            Permission.WORKSPACE_EDIT: "Edit workspace settings",
            Permission.WORKSPACE_DELETE: "Delete workspace",
            Permission.WORKSPACE_MANAGE_MEMBERS: "Manage workspace members",
            Permission.PROJECT_VIEW: "View projects",
            Permission.PROJECT_CREATE: "Create new projects",
            Permission.PROJECT_EDIT: "Edit project settings",
            Permission.PROJECT_DELETE: "Delete projects",
            Permission.PROJECT_MANAGE_MEMBERS: "Manage project members",
            Permission.TASK_VIEW: "View tasks",
            Permission.TASK_ANNOTATE: "Create annotations",
            Permission.TASK_REVIEW: "Review and approve annotations",
            Permission.TASK_ASSIGN: "Assign tasks to members",
            Permission.DATA_EXPORT: "Export annotation data",
            Permission.DATA_IMPORT: "Import data for annotation",
        }
        return descriptions.get(permission, permission.value)

    def get_role_description(
        self,
        role: WorkspaceMemberRole,
    ) -> str:
        """
        Get human-readable description of a role.

        Args:
            role: Role to describe

        Returns:
            Description string
        """
        descriptions = {
            WorkspaceMemberRole.OWNER: "Full control over workspace including deletion",
            WorkspaceMemberRole.ADMIN: "Manage workspace settings and members",
            WorkspaceMemberRole.MANAGER: "Manage projects and assign tasks",
            WorkspaceMemberRole.REVIEWER: "Review and approve annotations",
            WorkspaceMemberRole.ANNOTATOR: "Create annotations on assigned tasks",
        }
        return descriptions.get(role, role.value)


# ============================================================================
# Singleton Factory
# ============================================================================

def get_rbac_service(session: Session) -> RBACService:
    """
    Factory function to create RBACService.

    Args:
        session: SQLAlchemy database session

    Returns:
        RBACService instance
    """
    return RBACService(session)


# ============================================================================
# Permission Decorators
# ============================================================================

def require_permission_decorator(permission: Permission):
    """
    Decorator to require a permission for a function.

    Usage:
        @require_permission_decorator(Permission.PROJECT_CREATE)
        def create_project(self, user_id, workspace_id, ...):
            ...

    Note: The decorated function must have user_id and workspace_id parameters.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract parameters
            user_id = kwargs.get('user_id') or (args[1] if len(args) > 1 else None)
            workspace_id = kwargs.get('workspace_id') or (args[2] if len(args) > 2 else None)
            session = kwargs.get('session') or getattr(args[0], 'session', None)

            if not all([user_id, workspace_id, session]):
                raise ValueError(
                    "Function must have user_id, workspace_id parameters "
                    "and access to session"
                )

            rbac = RBACService(session)
            rbac.require_permission(user_id, workspace_id, permission)

            return func(*args, **kwargs)

        return wrapper
    return decorator
