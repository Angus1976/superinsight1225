"""
Label Studio Workspace Service.

This module provides comprehensive workspace management for Label Studio
Enterprise Workspace extension, including:
- Workspace CRUD operations
- Member management with role-based access
- Project association management
- Soft delete support

All operations follow async patterns and use SQLAlchemy for database access.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from sqlalchemy import and_, or_, select, func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from src.label_studio.workspace_models import (
    LabelStudioWorkspaceModel,
    LabelStudioWorkspaceMemberModel,
    WorkspaceProjectModel,
    ProjectMemberModel,
    WorkspaceMemberRole,
    ProjectMemberRole,
)
from src.security.models import UserModel

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class WorkspaceServiceError(Exception):
    """Base exception for workspace service errors."""
    pass


class WorkspaceNotFoundError(WorkspaceServiceError):
    """Exception raised when workspace is not found."""
    pass


class WorkspaceAlreadyExistsError(WorkspaceServiceError):
    """Exception raised when workspace already exists."""
    pass


class MemberNotFoundError(WorkspaceServiceError):
    """Exception raised when member is not found."""
    pass


class MemberAlreadyExistsError(WorkspaceServiceError):
    """Exception raised when member already exists."""
    pass


class InsufficientPermissionError(WorkspaceServiceError):
    """Exception raised when user lacks permission."""
    pass


class CannotRemoveOwnerError(WorkspaceServiceError):
    """Exception raised when trying to remove the last owner."""
    pass


class WorkspaceHasProjectsError(WorkspaceServiceError):
    """Exception raised when trying to delete workspace with projects."""
    pass


# ============================================================================
# Pydantic-like Response Classes
# ============================================================================

class WorkspaceInfo:
    """Workspace information DTO."""

    def __init__(
        self,
        id: UUID,
        name: str,
        description: Optional[str],
        owner_id: UUID,
        settings: Dict[str, Any],
        is_active: bool,
        is_deleted: bool,
        created_at: datetime,
        updated_at: datetime,
        member_count: int = 0,
        project_count: int = 0,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.owner_id = owner_id
        self.settings = settings
        self.is_active = is_active
        self.is_deleted = is_deleted
        self.created_at = created_at
        self.updated_at = updated_at
        self.member_count = member_count
        self.project_count = project_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "owner_id": str(self.owner_id),
            "settings": self.settings,
            "is_active": self.is_active,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "member_count": self.member_count,
            "project_count": self.project_count,
        }


class MemberInfo:
    """Workspace member information DTO."""

    def __init__(
        self,
        id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceMemberRole,
        is_active: bool,
        joined_at: datetime,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
    ):
        self.id = id
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.role = role
        self.is_active = is_active
        self.joined_at = joined_at
        self.user_email = user_email
        self.user_name = user_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "workspace_id": str(self.workspace_id),
            "user_id": str(self.user_id),
            "role": self.role.value,
            "is_active": self.is_active,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "user_email": self.user_email,
            "user_name": self.user_name,
        }


# ============================================================================
# Workspace Service
# ============================================================================

class WorkspaceService:
    """
    Workspace Service for managing Label Studio workspaces.

    Provides methods for:
    - Creating, reading, updating, and deleting workspaces
    - Managing workspace members and their roles
    - Soft delete with restoration support

    Thread-safety: Methods are stateless and can be called concurrently
    with different session objects.

    Example Usage:
        service = WorkspaceService(session)

        # Create a workspace
        workspace = service.create_workspace(
            name="Research Team",
            description="Workspace for research projects",
            owner_id=user_id
        )

        # Add a member
        service.add_member(workspace.id, annotator_id, WorkspaceMemberRole.ANNOTATOR)

        # List user's workspaces
        workspaces = service.list_user_workspaces(user_id)
    """

    def __init__(self, session: Session):
        """
        Initialize WorkspaceService.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    # ========== Workspace CRUD ==========

    def create_workspace(
        self,
        name: str,
        owner_id: UUID,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> LabelStudioWorkspaceModel:
        """
        Create a new workspace.

        Creates a workspace and automatically adds the creator as owner.

        Args:
            name: Workspace name (must be unique)
            owner_id: User ID of workspace owner
            description: Optional workspace description
            settings: Optional configuration settings

        Returns:
            Created LabelStudioWorkspaceModel instance

        Raises:
            WorkspaceAlreadyExistsError: If workspace with same name exists
        """
        # Check for existing workspace with same name
        existing = self.session.query(LabelStudioWorkspaceModel).filter(
            and_(
                LabelStudioWorkspaceModel.name == name,
                LabelStudioWorkspaceModel.is_deleted == False
            )
        ).first()

        if existing:
            raise WorkspaceAlreadyExistsError(f"Workspace '{name}' already exists")

        # Create workspace
        workspace = LabelStudioWorkspaceModel(
            id=uuid4(),
            name=name,
            description=description,
            owner_id=owner_id,
            settings=settings or {},
            is_active=True,
            is_deleted=False,
        )

        self.session.add(workspace)

        # Add owner as member
        owner_member = LabelStudioWorkspaceMemberModel(
            id=uuid4(),
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceMemberRole.OWNER,
            is_active=True,
        )
        self.session.add(owner_member)

        try:
            self.session.commit()
            logger.info(f"Created workspace '{name}' with owner {owner_id}")
            return workspace
        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Failed to create workspace: {e}")
            raise WorkspaceAlreadyExistsError(f"Workspace '{name}' already exists")

    def get_workspace(
        self,
        workspace_id: UUID,
        include_deleted: bool = False,
    ) -> Optional[LabelStudioWorkspaceModel]:
        """
        Get workspace by ID.

        Args:
            workspace_id: Workspace UUID
            include_deleted: Whether to include soft-deleted workspaces

        Returns:
            LabelStudioWorkspaceModel if found, None otherwise
        """
        query = self.session.query(LabelStudioWorkspaceModel).filter(
            LabelStudioWorkspaceModel.id == workspace_id
        )

        if not include_deleted:
            query = query.filter(LabelStudioWorkspaceModel.is_deleted == False)

        return query.first()

    def get_workspace_by_name(
        self,
        name: str,
        include_deleted: bool = False,
    ) -> Optional[LabelStudioWorkspaceModel]:
        """
        Get workspace by name.

        Args:
            name: Workspace name
            include_deleted: Whether to include soft-deleted workspaces

        Returns:
            LabelStudioWorkspaceModel if found, None otherwise
        """
        query = self.session.query(LabelStudioWorkspaceModel).filter(
            LabelStudioWorkspaceModel.name == name
        )

        if not include_deleted:
            query = query.filter(LabelStudioWorkspaceModel.is_deleted == False)

        return query.first()

    def list_user_workspaces(
        self,
        user_id: UUID,
        include_inactive: bool = False,
    ) -> List[LabelStudioWorkspaceModel]:
        """
        List workspaces where user is a member.

        Args:
            user_id: User UUID
            include_inactive: Whether to include inactive memberships

        Returns:
            List of workspaces user has access to
        """
        query = self.session.query(LabelStudioWorkspaceModel).join(
            LabelStudioWorkspaceMemberModel,
            LabelStudioWorkspaceModel.id == LabelStudioWorkspaceMemberModel.workspace_id
        ).filter(
            and_(
                LabelStudioWorkspaceMemberModel.user_id == user_id,
                LabelStudioWorkspaceModel.is_deleted == False
            )
        )

        if not include_inactive:
            query = query.filter(
                and_(
                    LabelStudioWorkspaceMemberModel.is_active == True,
                    LabelStudioWorkspaceModel.is_active == True
                )
            )

        return query.all()

    def update_workspace(
        self,
        workspace_id: UUID,
        data: Dict[str, Any],
    ) -> LabelStudioWorkspaceModel:
        """
        Update workspace attributes.

        Args:
            workspace_id: Workspace UUID
            data: Dictionary of attributes to update.
                  Allowed: name, description, settings, is_active

        Returns:
            Updated LabelStudioWorkspaceModel

        Raises:
            WorkspaceNotFoundError: If workspace not found
            WorkspaceAlreadyExistsError: If new name already exists
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found")

        # Check name uniqueness if changing
        if "name" in data and data["name"] != workspace.name:
            existing = self.get_workspace_by_name(data["name"])
            if existing:
                raise WorkspaceAlreadyExistsError(
                    f"Workspace '{data['name']}' already exists"
                )

        # Update allowed fields
        allowed_fields = {"name", "description", "settings", "is_active"}
        for field, value in data.items():
            if field in allowed_fields:
                setattr(workspace, field, value)

        workspace.updated_at = datetime.utcnow()
        self.session.commit()

        logger.info(f"Updated workspace {workspace_id}")
        return workspace

    def delete_workspace(
        self,
        workspace_id: UUID,
        hard_delete: bool = False,
    ) -> bool:
        """
        Delete a workspace (soft delete by default).

        Args:
            workspace_id: Workspace UUID
            hard_delete: If True, permanently delete. If False, soft delete.

        Returns:
            True if deleted successfully

        Raises:
            WorkspaceNotFoundError: If workspace not found
            WorkspaceHasProjectsError: If workspace has associated projects
        """
        workspace = self.get_workspace(workspace_id, include_deleted=True)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found")

        # Check for associated projects
        project_count = self.session.query(WorkspaceProjectModel).filter(
            WorkspaceProjectModel.workspace_id == workspace_id
        ).count()

        if project_count > 0 and not hard_delete:
            raise WorkspaceHasProjectsError(
                f"Workspace has {project_count} associated projects. "
                "Remove projects first or use hard_delete=True"
            )

        if hard_delete:
            # Hard delete - remove from database
            self.session.delete(workspace)
            logger.info(f"Hard deleted workspace {workspace_id}")
        else:
            # Soft delete
            workspace.is_deleted = True
            workspace.is_active = False
            workspace.deleted_at = datetime.utcnow()
            logger.info(f"Soft deleted workspace {workspace_id}")

        self.session.commit()
        return True

    def restore_workspace(
        self,
        workspace_id: UUID,
    ) -> LabelStudioWorkspaceModel:
        """
        Restore a soft-deleted workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Restored workspace

        Raises:
            WorkspaceNotFoundError: If workspace not found
            WorkspaceAlreadyExistsError: If workspace name conflicts
        """
        workspace = self.get_workspace(workspace_id, include_deleted=True)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found")

        if not workspace.is_deleted:
            return workspace  # Already active

        # Check name conflict
        existing = self.get_workspace_by_name(workspace.name)
        if existing and existing.id != workspace_id:
            raise WorkspaceAlreadyExistsError(
                f"Cannot restore: workspace name '{workspace.name}' is now in use"
            )

        workspace.is_deleted = False
        workspace.is_active = True
        workspace.deleted_at = None
        workspace.updated_at = datetime.utcnow()

        self.session.commit()
        logger.info(f"Restored workspace {workspace_id}")
        return workspace

    # ========== Member Management ==========

    def add_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceMemberRole = WorkspaceMemberRole.ANNOTATOR,
    ) -> LabelStudioWorkspaceMemberModel:
        """
        Add a member to workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID to add
            role: Member role (default: ANNOTATOR)

        Returns:
            Created membership record

        Raises:
            WorkspaceNotFoundError: If workspace not found
            MemberAlreadyExistsError: If user is already a member
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found")

        # Check if already a member
        existing = self._get_membership(workspace_id, user_id)
        if existing:
            if existing.is_active:
                raise MemberAlreadyExistsError(
                    f"User '{user_id}' is already a member of workspace"
                )
            else:
                # Reactivate membership
                existing.is_active = True
                existing.role = role
                existing.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"Reactivated member {user_id} in workspace {workspace_id}")
                return existing

        # Create new membership
        member = LabelStudioWorkspaceMemberModel(
            id=uuid4(),
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            is_active=True,
        )
        self.session.add(member)
        self.session.commit()

        logger.info(f"Added member {user_id} to workspace {workspace_id} as {role.value}")
        return member

    def remove_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        hard_delete: bool = False,
    ) -> bool:
        """
        Remove a member from workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID to remove
            hard_delete: If True, permanently delete. If False, deactivate.

        Returns:
            True if removed successfully

        Raises:
            WorkspaceNotFoundError: If workspace not found
            MemberNotFoundError: If member not found
            CannotRemoveOwnerError: If trying to remove the last owner
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found")

        member = self._get_membership(workspace_id, user_id)
        if not member:
            raise MemberNotFoundError(
                f"User '{user_id}' is not a member of workspace"
            )

        # Check if removing last owner
        if member.role == WorkspaceMemberRole.OWNER:
            owner_count = self.session.query(LabelStudioWorkspaceMemberModel).filter(
                and_(
                    LabelStudioWorkspaceMemberModel.workspace_id == workspace_id,
                    LabelStudioWorkspaceMemberModel.role == WorkspaceMemberRole.OWNER,
                    LabelStudioWorkspaceMemberModel.is_active == True
                )
            ).count()

            if owner_count <= 1:
                raise CannotRemoveOwnerError(
                    "Cannot remove the last owner of workspace"
                )

        if hard_delete:
            self.session.delete(member)
        else:
            member.is_active = False
            member.updated_at = datetime.utcnow()

        self.session.commit()
        logger.info(f"Removed member {user_id} from workspace {workspace_id}")
        return True

    def update_member_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
        new_role: WorkspaceMemberRole,
    ) -> LabelStudioWorkspaceMemberModel:
        """
        Update member's role in workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID
            new_role: New role to assign

        Returns:
            Updated membership record

        Raises:
            WorkspaceNotFoundError: If workspace not found
            MemberNotFoundError: If member not found
            CannotRemoveOwnerError: If demoting the last owner
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found")

        member = self._get_membership(workspace_id, user_id)
        if not member or not member.is_active:
            raise MemberNotFoundError(
                f"User '{user_id}' is not an active member of workspace"
            )

        # Check if demoting last owner
        if member.role == WorkspaceMemberRole.OWNER and new_role != WorkspaceMemberRole.OWNER:
            owner_count = self.session.query(LabelStudioWorkspaceMemberModel).filter(
                and_(
                    LabelStudioWorkspaceMemberModel.workspace_id == workspace_id,
                    LabelStudioWorkspaceMemberModel.role == WorkspaceMemberRole.OWNER,
                    LabelStudioWorkspaceMemberModel.is_active == True
                )
            ).count()

            if owner_count <= 1:
                raise CannotRemoveOwnerError(
                    "Cannot demote the last owner of workspace"
                )

        old_role = member.role
        member.role = new_role
        member.updated_at = datetime.utcnow()
        self.session.commit()

        logger.info(
            f"Updated member {user_id} role in workspace {workspace_id}: "
            f"{old_role.value} -> {new_role.value}"
        )
        return member

    def get_member_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Optional[WorkspaceMemberRole]:
        """
        Get member's role in workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID

        Returns:
            Member's role if found and active, None otherwise
        """
        member = self._get_membership(workspace_id, user_id)
        if member and member.is_active:
            return member.role
        return None

    def list_members(
        self,
        workspace_id: UUID,
        include_inactive: bool = False,
    ) -> List[MemberInfo]:
        """
        List all members of workspace.

        Args:
            workspace_id: Workspace UUID
            include_inactive: Whether to include inactive members

        Returns:
            List of MemberInfo objects

        Raises:
            WorkspaceNotFoundError: If workspace not found
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found")

        query = self.session.query(
            LabelStudioWorkspaceMemberModel,
            UserModel.email,
            UserModel.full_name
        ).outerjoin(
            UserModel,
            LabelStudioWorkspaceMemberModel.user_id == UserModel.id
        ).filter(
            LabelStudioWorkspaceMemberModel.workspace_id == workspace_id
        )

        if not include_inactive:
            query = query.filter(LabelStudioWorkspaceMemberModel.is_active == True)

        results = query.all()

        return [
            MemberInfo(
                id=member.id,
                workspace_id=member.workspace_id,
                user_id=member.user_id,
                role=member.role,
                is_active=member.is_active,
                joined_at=member.joined_at,
                user_email=email,
                user_name=name,
            )
            for member, email, name in results
        ]

    def is_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Check if user is an active member of workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID

        Returns:
            True if user is an active member
        """
        member = self._get_membership(workspace_id, user_id)
        return member is not None and member.is_active

    # ========== Helper Methods ==========

    def _get_membership(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Optional[LabelStudioWorkspaceMemberModel]:
        """Get membership record (active or inactive)."""
        return self.session.query(LabelStudioWorkspaceMemberModel).filter(
            and_(
                LabelStudioWorkspaceMemberModel.workspace_id == workspace_id,
                LabelStudioWorkspaceMemberModel.user_id == user_id
            )
        ).first()

    def get_workspace_info(
        self,
        workspace_id: UUID,
    ) -> Optional[WorkspaceInfo]:
        """
        Get workspace information with member and project counts.

        Args:
            workspace_id: Workspace UUID

        Returns:
            WorkspaceInfo if found, None otherwise
        """
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return None

        # Count members
        member_count = self.session.query(LabelStudioWorkspaceMemberModel).filter(
            and_(
                LabelStudioWorkspaceMemberModel.workspace_id == workspace_id,
                LabelStudioWorkspaceMemberModel.is_active == True
            )
        ).count()

        # Count projects
        project_count = self.session.query(WorkspaceProjectModel).filter(
            WorkspaceProjectModel.workspace_id == workspace_id
        ).count()

        return WorkspaceInfo(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            owner_id=workspace.owner_id,
            settings=workspace.settings,
            is_active=workspace.is_active,
            is_deleted=workspace.is_deleted,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            member_count=member_count,
            project_count=project_count,
        )


# ============================================================================
# Singleton Factory
# ============================================================================

def get_workspace_service(session: Session) -> WorkspaceService:
    """
    Factory function to create WorkspaceService.

    Args:
        session: SQLAlchemy database session

    Returns:
        WorkspaceService instance
    """
    return WorkspaceService(session)
