"""
Label Studio Workspace Permission Flow Integration Tests

Tests the RBAC (Role-Based Access Control) system including:
- Permission matrix verification for each role
- Permission inheritance and hierarchy
- Permission changes propagation
- Access control validation

Uses SQLite-compatible test models for in-memory testing.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.sqlite import JSON
import enum


# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test-specific base for SQLite compatibility
TestBase = declarative_base()


# ============================================================================
# Permission and Role Definitions
# ============================================================================

class WorkspaceMemberRole(str, enum.Enum):
    ANNOTATOR = "annotator"
    REVIEWER = "reviewer"
    MANAGER = "manager"
    ADMIN = "admin"
    OWNER = "owner"


class Permission(str, enum.Enum):
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


# Permission matrix - maps roles to their permissions
ROLE_PERMISSIONS = {
    WorkspaceMemberRole.OWNER: [
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
    ],
    WorkspaceMemberRole.ADMIN: [
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
    ],
    WorkspaceMemberRole.MANAGER: [
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_MANAGE_MEMBERS,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
        Permission.TASK_REVIEW,
        Permission.TASK_ASSIGN,
        Permission.DATA_EXPORT,
    ],
    WorkspaceMemberRole.REVIEWER: [
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
        Permission.TASK_REVIEW,
        Permission.DATA_EXPORT,
    ],
    WorkspaceMemberRole.ANNOTATOR: [
        Permission.WORKSPACE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.TASK_VIEW,
        Permission.TASK_ANNOTATE,
    ],
}

# Role hierarchy - higher index means more permissions
ROLE_HIERARCHY = [
    WorkspaceMemberRole.ANNOTATOR,
    WorkspaceMemberRole.REVIEWER,
    WorkspaceMemberRole.MANAGER,
    WorkspaceMemberRole.ADMIN,
    WorkspaceMemberRole.OWNER,
]


# ============================================================================
# SQLite-Compatible Test Models
# ============================================================================

class TestLSWorkspaceModel(TestBase):
    """Test Label Studio workspace model for SQLite."""
    __tablename__ = "test_ls_workspaces_perm"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(String(36), nullable=False)
    settings = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TestLSWorkspaceMemberModel(TestBase):
    """Test Label Studio workspace member model for SQLite."""
    __tablename__ = "test_ls_workspace_members_perm"

    id = Column(String(36), primary_key=True)
    workspace_id = Column(String(36), ForeignKey("test_ls_workspaces_perm.id"), nullable=False)
    user_id = Column(String(36), nullable=False)
    role = Column(SQLEnum(WorkspaceMemberRole), default=WorkspaceMemberRole.ANNOTATOR)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# Helper Functions
# ============================================================================

def has_permission(role: WorkspaceMemberRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, [])


def get_user_permissions(role: WorkspaceMemberRole) -> list[Permission]:
    """Get all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, [])


def is_higher_role(role1: WorkspaceMemberRole, role2: WorkspaceMemberRole) -> bool:
    """Check if role1 is higher than role2 in hierarchy."""
    return ROLE_HIERARCHY.index(role1) > ROLE_HIERARCHY.index(role2)


def can_manage_role(manager_role: WorkspaceMemberRole, target_role: WorkspaceMemberRole) -> bool:
    """Check if manager role can manage target role."""
    if manager_role == WorkspaceMemberRole.OWNER:
        return True
    if manager_role == WorkspaceMemberRole.ADMIN:
        return target_role not in [WorkspaceMemberRole.OWNER, WorkspaceMemberRole.ADMIN]
    return False


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestBase.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def users():
    """Create test users for different roles."""
    return {
        "owner": {"id": str(uuid4()), "name": "Owner User"},
        "admin": {"id": str(uuid4()), "name": "Admin User"},
        "manager": {"id": str(uuid4()), "name": "Manager User"},
        "reviewer": {"id": str(uuid4()), "name": "Reviewer User"},
        "annotator": {"id": str(uuid4()), "name": "Annotator User"},
        "non_member": {"id": str(uuid4()), "name": "Non-Member User"},
    }


@pytest.fixture
def workspace_with_members(session, users):
    """Create workspace with all role types."""
    workspace_id = str(uuid4())

    # Create workspace
    workspace = TestLSWorkspaceModel(
        id=workspace_id,
        name="Permission Test Workspace",
        owner_id=users["owner"]["id"],
    )
    session.add(workspace)

    # Add members with different roles
    role_mapping = {
        "owner": WorkspaceMemberRole.OWNER,
        "admin": WorkspaceMemberRole.ADMIN,
        "manager": WorkspaceMemberRole.MANAGER,
        "reviewer": WorkspaceMemberRole.REVIEWER,
        "annotator": WorkspaceMemberRole.ANNOTATOR,
    }

    for key, role in role_mapping.items():
        member = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=users[key]["id"],
            role=role,
        )
        session.add(member)

    session.commit()
    return workspace_id


# ============================================================================
# Permission Matrix Tests
# ============================================================================

class TestPermissionMatrix:
    """Tests for permission matrix verification."""

    @pytest.mark.parametrize("role,expected_count", [
        (WorkspaceMemberRole.OWNER, 15),
        (WorkspaceMemberRole.ADMIN, 14),
        (WorkspaceMemberRole.MANAGER, 10),
        (WorkspaceMemberRole.REVIEWER, 6),
        (WorkspaceMemberRole.ANNOTATOR, 4),
    ])
    def test_role_permission_count(self, role, expected_count):
        """Test each role has expected number of permissions."""
        permissions = get_user_permissions(role)
        assert len(permissions) == expected_count

    def test_owner_has_all_permissions(self):
        """Test owner has all defined permissions."""
        owner_permissions = get_user_permissions(WorkspaceMemberRole.OWNER)
        for permission in Permission:
            assert permission in owner_permissions, f"Owner missing permission: {permission}"

    def test_admin_cannot_delete_workspace(self):
        """Test admin cannot delete workspace."""
        assert not has_permission(WorkspaceMemberRole.ADMIN, Permission.WORKSPACE_DELETE)

    def test_manager_cannot_manage_workspace_members(self):
        """Test manager cannot manage workspace members."""
        assert not has_permission(WorkspaceMemberRole.MANAGER, Permission.WORKSPACE_MANAGE_MEMBERS)

    def test_reviewer_can_view_and_review(self):
        """Test reviewer can view and review tasks."""
        assert has_permission(WorkspaceMemberRole.REVIEWER, Permission.TASK_VIEW)
        assert has_permission(WorkspaceMemberRole.REVIEWER, Permission.TASK_REVIEW)
        assert has_permission(WorkspaceMemberRole.REVIEWER, Permission.TASK_ANNOTATE)

    def test_annotator_minimal_permissions(self):
        """Test annotator has minimal permissions."""
        annotator_permissions = get_user_permissions(WorkspaceMemberRole.ANNOTATOR)

        # Should have
        assert Permission.WORKSPACE_VIEW in annotator_permissions
        assert Permission.PROJECT_VIEW in annotator_permissions
        assert Permission.TASK_VIEW in annotator_permissions
        assert Permission.TASK_ANNOTATE in annotator_permissions

        # Should not have
        assert Permission.TASK_REVIEW not in annotator_permissions
        assert Permission.DATA_EXPORT not in annotator_permissions
        assert Permission.PROJECT_EDIT not in annotator_permissions


# ============================================================================
# Role Hierarchy Tests
# ============================================================================

class TestRoleHierarchy:
    """Tests for role hierarchy."""

    def test_owner_is_highest(self):
        """Test owner is highest in hierarchy."""
        assert is_higher_role(WorkspaceMemberRole.OWNER, WorkspaceMemberRole.ADMIN)
        assert is_higher_role(WorkspaceMemberRole.OWNER, WorkspaceMemberRole.MANAGER)
        assert is_higher_role(WorkspaceMemberRole.OWNER, WorkspaceMemberRole.REVIEWER)
        assert is_higher_role(WorkspaceMemberRole.OWNER, WorkspaceMemberRole.ANNOTATOR)

    def test_admin_above_manager(self):
        """Test admin is above manager."""
        assert is_higher_role(WorkspaceMemberRole.ADMIN, WorkspaceMemberRole.MANAGER)
        assert is_higher_role(WorkspaceMemberRole.ADMIN, WorkspaceMemberRole.REVIEWER)
        assert is_higher_role(WorkspaceMemberRole.ADMIN, WorkspaceMemberRole.ANNOTATOR)

    def test_manager_above_reviewer(self):
        """Test manager is above reviewer."""
        assert is_higher_role(WorkspaceMemberRole.MANAGER, WorkspaceMemberRole.REVIEWER)
        assert is_higher_role(WorkspaceMemberRole.MANAGER, WorkspaceMemberRole.ANNOTATOR)

    def test_reviewer_above_annotator(self):
        """Test reviewer is above annotator."""
        assert is_higher_role(WorkspaceMemberRole.REVIEWER, WorkspaceMemberRole.ANNOTATOR)

    def test_annotator_is_lowest(self):
        """Test annotator is lowest in hierarchy."""
        assert not is_higher_role(WorkspaceMemberRole.ANNOTATOR, WorkspaceMemberRole.REVIEWER)
        assert not is_higher_role(WorkspaceMemberRole.ANNOTATOR, WorkspaceMemberRole.MANAGER)
        assert not is_higher_role(WorkspaceMemberRole.ANNOTATOR, WorkspaceMemberRole.ADMIN)
        assert not is_higher_role(WorkspaceMemberRole.ANNOTATOR, WorkspaceMemberRole.OWNER)


# ============================================================================
# Role Management Tests
# ============================================================================

class TestRoleManagement:
    """Tests for role management permissions."""

    def test_owner_can_manage_all_roles(self):
        """Test owner can manage all roles."""
        assert can_manage_role(WorkspaceMemberRole.OWNER, WorkspaceMemberRole.ADMIN)
        assert can_manage_role(WorkspaceMemberRole.OWNER, WorkspaceMemberRole.MANAGER)
        assert can_manage_role(WorkspaceMemberRole.OWNER, WorkspaceMemberRole.REVIEWER)
        assert can_manage_role(WorkspaceMemberRole.OWNER, WorkspaceMemberRole.ANNOTATOR)

    def test_admin_can_manage_lower_roles(self):
        """Test admin can manage roles below admin."""
        assert can_manage_role(WorkspaceMemberRole.ADMIN, WorkspaceMemberRole.MANAGER)
        assert can_manage_role(WorkspaceMemberRole.ADMIN, WorkspaceMemberRole.REVIEWER)
        assert can_manage_role(WorkspaceMemberRole.ADMIN, WorkspaceMemberRole.ANNOTATOR)

    def test_admin_cannot_manage_owner_or_admin(self):
        """Test admin cannot manage owner or other admins."""
        assert not can_manage_role(WorkspaceMemberRole.ADMIN, WorkspaceMemberRole.OWNER)
        assert not can_manage_role(WorkspaceMemberRole.ADMIN, WorkspaceMemberRole.ADMIN)

    def test_manager_cannot_manage_roles(self):
        """Test manager cannot manage any roles."""
        assert not can_manage_role(WorkspaceMemberRole.MANAGER, WorkspaceMemberRole.ADMIN)
        assert not can_manage_role(WorkspaceMemberRole.MANAGER, WorkspaceMemberRole.REVIEWER)
        assert not can_manage_role(WorkspaceMemberRole.MANAGER, WorkspaceMemberRole.ANNOTATOR)

    def test_reviewer_cannot_manage_roles(self):
        """Test reviewer cannot manage any roles."""
        assert not can_manage_role(WorkspaceMemberRole.REVIEWER, WorkspaceMemberRole.ANNOTATOR)

    def test_annotator_cannot_manage_roles(self):
        """Test annotator cannot manage any roles."""
        assert not can_manage_role(WorkspaceMemberRole.ANNOTATOR, WorkspaceMemberRole.ANNOTATOR)


# ============================================================================
# Access Control Tests with Database
# ============================================================================

class TestAccessControl:
    """Tests for access control with database."""

    def test_member_has_correct_role(self, session, workspace_with_members, users):
        """Test members have correct roles assigned."""
        workspace_id = workspace_with_members

        role_mapping = {
            "owner": WorkspaceMemberRole.OWNER,
            "admin": WorkspaceMemberRole.ADMIN,
            "manager": WorkspaceMemberRole.MANAGER,
            "reviewer": WorkspaceMemberRole.REVIEWER,
            "annotator": WorkspaceMemberRole.ANNOTATOR,
        }

        for key, expected_role in role_mapping.items():
            member = session.query(TestLSWorkspaceMemberModel).filter_by(
                workspace_id=workspace_id,
                user_id=users[key]["id"]
            ).first()
            assert member is not None
            assert member.role == expected_role

    def test_non_member_has_no_access(self, session, workspace_with_members, users):
        """Test non-member has no access to workspace."""
        workspace_id = workspace_with_members

        # Query for non-member
        member = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=users["non_member"]["id"]
        ).first()

        assert member is None

    def test_inactive_member_no_access(self, session, workspace_with_members, users):
        """Test inactive member has no access."""
        workspace_id = workspace_with_members

        # Deactivate annotator
        member = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=users["annotator"]["id"]
        ).first()
        member.is_active = False
        session.commit()

        # Query active members
        active_members = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            is_active=True
        ).all()

        user_ids = [m.user_id for m in active_members]
        assert users["annotator"]["id"] not in user_ids

    def test_role_upgrade_preserves_membership(self, session, workspace_with_members, users):
        """Test role upgrade preserves membership."""
        workspace_id = workspace_with_members

        # Upgrade annotator to reviewer
        member = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=users["annotator"]["id"]
        ).first()

        old_id = member.id
        member.role = WorkspaceMemberRole.REVIEWER
        session.commit()

        # Verify same membership record
        updated = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=users["annotator"]["id"]
        ).first()

        assert updated.id == old_id
        assert updated.role == WorkspaceMemberRole.REVIEWER


# ============================================================================
# Permission Verification Tests
# ============================================================================

class TestPermissionVerification:
    """Tests for verifying permissions in database context."""

    def test_verify_workspace_edit_permission(self, session, workspace_with_members, users):
        """Test verifying workspace edit permission for different roles."""
        workspace_id = workspace_with_members

        # Owner and Admin can edit
        for key in ["owner", "admin"]:
            member = session.query(TestLSWorkspaceMemberModel).filter_by(
                workspace_id=workspace_id,
                user_id=users[key]["id"]
            ).first()
            assert has_permission(member.role, Permission.WORKSPACE_EDIT)

        # Manager, Reviewer, Annotator cannot edit workspace
        for key in ["manager", "reviewer", "annotator"]:
            member = session.query(TestLSWorkspaceMemberModel).filter_by(
                workspace_id=workspace_id,
                user_id=users[key]["id"]
            ).first()
            assert not has_permission(member.role, Permission.WORKSPACE_EDIT)

    def test_verify_task_annotate_permission(self, session, workspace_with_members, users):
        """Test all members can annotate tasks."""
        workspace_id = workspace_with_members

        for key in ["owner", "admin", "manager", "reviewer", "annotator"]:
            member = session.query(TestLSWorkspaceMemberModel).filter_by(
                workspace_id=workspace_id,
                user_id=users[key]["id"]
            ).first()
            assert has_permission(member.role, Permission.TASK_ANNOTATE)

    def test_verify_data_export_permission(self, session, workspace_with_members, users):
        """Test data export permission varies by role."""
        workspace_id = workspace_with_members

        # Can export
        for key in ["owner", "admin", "manager", "reviewer"]:
            member = session.query(TestLSWorkspaceMemberModel).filter_by(
                workspace_id=workspace_id,
                user_id=users[key]["id"]
            ).first()
            assert has_permission(member.role, Permission.DATA_EXPORT)

        # Cannot export
        member = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=users["annotator"]["id"]
        ).first()
        assert not has_permission(member.role, Permission.DATA_EXPORT)


# ============================================================================
# Permission Change Propagation Tests
# ============================================================================

class TestPermissionChanges:
    """Tests for permission changes and propagation."""

    def test_role_change_updates_permissions(self, session, workspace_with_members, users):
        """Test changing role updates permissions."""
        workspace_id = workspace_with_members

        # Get annotator member
        member = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=users["annotator"]["id"]
        ).first()

        # Initially cannot review
        assert not has_permission(member.role, Permission.TASK_REVIEW)

        # Upgrade to reviewer
        member.role = WorkspaceMemberRole.REVIEWER
        session.commit()

        # Now can review
        updated = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=users["annotator"]["id"]
        ).first()
        assert has_permission(updated.role, Permission.TASK_REVIEW)

    def test_role_downgrade_removes_permissions(self, session, workspace_with_members, users):
        """Test downgrading role removes permissions."""
        workspace_id = workspace_with_members

        # Get admin member
        member = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=users["admin"]["id"]
        ).first()

        # Initially can manage members
        assert has_permission(member.role, Permission.WORKSPACE_MANAGE_MEMBERS)

        # Downgrade to manager
        member.role = WorkspaceMemberRole.MANAGER
        session.commit()

        # Now cannot manage members
        updated = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=users["admin"]["id"]
        ).first()
        assert not has_permission(updated.role, Permission.WORKSPACE_MANAGE_MEMBERS)
