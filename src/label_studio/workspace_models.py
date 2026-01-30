"""
Label Studio Enterprise Workspace Database Models.

This module defines the database models for Label Studio Enterprise Workspace extension,
enabling workspace-based project organization and fine-grained access control.

Models:
- LabelStudioWorkspaceModel: Workspace for organizing Label Studio projects
- LabelStudioWorkspaceMemberModel: Workspace membership with role-based access
- WorkspaceProjectModel: Links workspaces to Label Studio projects
- ProjectMemberModel: Project-level member assignments

Role Hierarchy:
- owner: Full control, can delete workspace
- admin: Manage members and projects (except delete workspace)
- manager: Manage projects, view members
- reviewer: Review annotations
- annotator: Create annotations
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    String, Text, Integer, DateTime, Boolean,
    ForeignKey, Enum as SQLEnum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum
from typing import Optional, List, Dict, Any

from src.database.connection import Base


# ============================================================================
# Enumerations
# ============================================================================

class WorkspaceMemberRole(str, enum.Enum):
    """
    Workspace member role enumeration.

    Role Hierarchy (highest to lowest):
    - OWNER: Full control, only one per workspace, can delete workspace
    - ADMIN: Full control except deleting workspace and changing owner
    - MANAGER: Can manage projects and view members
    - REVIEWER: Can review and approve annotations
    - ANNOTATOR: Can annotate tasks assigned to them
    """
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    REVIEWER = "reviewer"
    ANNOTATOR = "annotator"


class ProjectMemberRole(str, enum.Enum):
    """
    Project-level member role enumeration.

    These roles are specific to project-level assignments:
    - ANNOTATOR: Can annotate tasks in this project
    - REVIEWER: Can review and approve annotations in this project
    """
    ANNOTATOR = "annotator"
    REVIEWER = "reviewer"


# ============================================================================
# Workspace Model
# ============================================================================

class LabelStudioWorkspaceModel(Base):
    """
    Label Studio Workspace table.

    Represents a workspace for organizing Label Studio projects with
    role-based access control and soft delete support.

    Attributes:
        id: Unique workspace identifier (UUID)
        name: Workspace name (unique, required)
        description: Optional workspace description
        owner_id: User ID of workspace owner (FK to users)
        settings: JSONB configuration settings
        is_active: Whether workspace is active
        is_deleted: Soft delete flag
        created_at: Creation timestamp
        updated_at: Last update timestamp
        deleted_at: Soft delete timestamp

    Relationships:
        owner: User who owns the workspace
        members: WorkspaceMember associations
        projects: WorkspaceProject associations
    """
    __tablename__ = "label_studio_workspaces"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Configuration settings (JSONB)
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default={},
        nullable=False
    )

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    owner: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys=[owner_id],
        lazy="joined"
    )
    members: Mapped[List["LabelStudioWorkspaceMemberModel"]] = relationship(
        "LabelStudioWorkspaceMemberModel",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    projects: Mapped[List["WorkspaceProjectModel"]] = relationship(
        "WorkspaceProjectModel",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        Index('ix_ls_workspace_owner', 'owner_id'),
        Index('ix_ls_workspace_active', 'is_active', 'is_deleted'),
    )

    def __repr__(self) -> str:
        return f"<LabelStudioWorkspace(id={self.id}, name='{self.name}')>"


# ============================================================================
# Workspace Member Model
# ============================================================================

class LabelStudioWorkspaceMemberModel(Base):
    """
    Workspace member table.

    Links users to workspaces with role-based access control.

    Attributes:
        id: Unique member record identifier (UUID)
        workspace_id: FK to workspace (UUID)
        user_id: FK to user (UUID)
        role: Member role (owner, admin, manager, reviewer, annotator)
        is_active: Whether membership is active
        joined_at: When user joined the workspace
        updated_at: Last update timestamp

    Constraints:
        - (workspace_id, user_id) must be unique
    """
    __tablename__ = "label_studio_workspace_members"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("label_studio_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[WorkspaceMemberRole] = mapped_column(
        SQLEnum(WorkspaceMemberRole),
        default=WorkspaceMemberRole.ANNOTATOR,
        nullable=False
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    workspace: Mapped["LabelStudioWorkspaceModel"] = relationship(
        "LabelStudioWorkspaceModel",
        back_populates="members"
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        lazy="joined"
    )

    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='uq_ls_workspace_member'),
        Index('ix_ls_wm_workspace', 'workspace_id'),
        Index('ix_ls_wm_user', 'user_id'),
        Index('ix_ls_wm_role', 'role'),
    )

    def __repr__(self) -> str:
        return f"<WorkspaceMember(workspace_id={self.workspace_id}, user_id={self.user_id}, role={self.role})>"


# ============================================================================
# Workspace Project Model
# ============================================================================

class WorkspaceProjectModel(Base):
    """
    Workspace project association table.

    Links workspaces to Label Studio projects, enabling workspace-based
    project organization and filtering.

    Attributes:
        id: Unique record identifier (UUID)
        workspace_id: FK to workspace (UUID)
        label_studio_project_id: Label Studio project ID (string)
        superinsight_project_id: Optional SuperInsight project ID (UUID)
        project_metadata: Additional project metadata (JSONB)
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Constraints:
        - (workspace_id, label_studio_project_id) must be unique
    """
    __tablename__ = "workspace_projects"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("label_studio_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    label_studio_project_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    superinsight_project_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )

    # Additional metadata (JSONB) - renamed from 'metadata' to avoid SQLAlchemy reserved name
    project_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default={},
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    workspace: Mapped["LabelStudioWorkspaceModel"] = relationship(
        "LabelStudioWorkspaceModel",
        back_populates="projects"
    )
    members: Mapped[List["ProjectMemberModel"]] = relationship(
        "ProjectMemberModel",
        back_populates="workspace_project",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint('workspace_id', 'label_studio_project_id', name='uq_workspace_ls_project'),
        Index('ix_wp_workspace', 'workspace_id'),
        Index('ix_wp_ls_project', 'label_studio_project_id'),
        Index('ix_wp_si_project', 'superinsight_project_id'),
    )

    def __repr__(self) -> str:
        return f"<WorkspaceProject(workspace_id={self.workspace_id}, ls_project={self.label_studio_project_id})>"


# ============================================================================
# Project Member Model
# ============================================================================

class ProjectMemberModel(Base):
    """
    Project member assignment table.

    Links users to specific projects within a workspace with project-level
    role assignments (annotator or reviewer).

    Attributes:
        id: Unique record identifier (UUID)
        workspace_project_id: FK to workspace_projects (UUID)
        user_id: FK to user (UUID)
        project_role: Project-level role (annotator, reviewer)
        is_active: Whether assignment is active
        assigned_at: When user was assigned to project
        updated_at: Last update timestamp

    Constraints:
        - (workspace_project_id, user_id) must be unique
    """
    __tablename__ = "project_members"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    workspace_project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_role: Mapped[ProjectMemberRole] = mapped_column(
        SQLEnum(ProjectMemberRole),
        default=ProjectMemberRole.ANNOTATOR,
        nullable=False
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # Timestamps
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    workspace_project: Mapped["WorkspaceProjectModel"] = relationship(
        "WorkspaceProjectModel",
        back_populates="members"
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        lazy="joined"
    )

    __table_args__ = (
        UniqueConstraint('workspace_project_id', 'user_id', name='uq_project_member'),
        Index('ix_pm_project', 'workspace_project_id'),
        Index('ix_pm_user', 'user_id'),
        Index('ix_pm_role', 'project_role'),
    )

    def __repr__(self) -> str:
        return f"<ProjectMember(project_id={self.workspace_project_id}, user_id={self.user_id}, role={self.project_role})>"


# ============================================================================
# Import UserModel to resolve relationships
# ============================================================================

# Note: Import at the end to avoid circular imports
from src.security.models import UserModel
