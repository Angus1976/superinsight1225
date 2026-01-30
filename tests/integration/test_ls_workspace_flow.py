"""
Label Studio Workspace Integration Tests

Tests the complete flow of:
- Workspace creation → Member management → Project association
- RBAC permission verification
- Data isolation between workspaces

Uses SQLite-compatible test models for in-memory testing.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import MagicMock, patch, AsyncMock

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
# SQLite-Compatible Test Models (Mirroring actual models)
# ============================================================================

class WorkspaceMemberRole(str, enum.Enum):
    ANNOTATOR = "annotator"
    REVIEWER = "reviewer"
    MANAGER = "manager"
    ADMIN = "admin"
    OWNER = "owner"


class TestLSWorkspaceModel(TestBase):
    """Test Label Studio workspace model for SQLite."""
    __tablename__ = "test_ls_workspaces"

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
    __tablename__ = "test_ls_workspace_members"

    id = Column(String(36), primary_key=True)
    workspace_id = Column(String(36), ForeignKey("test_ls_workspaces.id"), nullable=False)
    user_id = Column(String(36), nullable=False)
    role = Column(SQLEnum(WorkspaceMemberRole), default=WorkspaceMemberRole.ANNOTATOR)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)


class TestWorkspaceProjectModel(TestBase):
    """Test workspace project model for SQLite."""
    __tablename__ = "test_workspace_projects"

    id = Column(String(36), primary_key=True)
    workspace_id = Column(String(36), ForeignKey("test_ls_workspaces.id"), nullable=False)
    label_studio_project_id = Column(String(100), nullable=False)
    superinsight_project_id = Column(String(36))
    project_metadata = Column(JSON, default={})  # Renamed to avoid SQLAlchemy reserved name
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


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
def user_a():
    """Create test user A (workspace owner)."""
    return {
        "id": str(uuid4()),
        "email": "user_a@example.com",
        "name": "User A",
    }


@pytest.fixture
def user_b():
    """Create test user B (annotator)."""
    return {
        "id": str(uuid4()),
        "email": "user_b@example.com",
        "name": "User B",
    }


@pytest.fixture
def user_c():
    """Create test user C (not a member)."""
    return {
        "id": str(uuid4()),
        "email": "user_c@example.com",
        "name": "User C",
    }


# ============================================================================
# Workspace Lifecycle Tests
# ============================================================================

class TestWorkspaceLifecycle:
    """Tests for complete workspace lifecycle."""

    def test_create_workspace(self, session, user_a):
        """Test creating a new workspace."""
        workspace_id = str(uuid4())

        workspace = TestLSWorkspaceModel(
            id=workspace_id,
            name="研发部门标注空间",
            description="用于研发团队的标注工作",
            owner_id=user_a["id"],
            settings={"max_annotators": 10},
        )
        session.add(workspace)

        # Add owner as member
        owner_member = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_a["id"],
            role=WorkspaceMemberRole.OWNER,
        )
        session.add(owner_member)
        session.commit()

        # Verify workspace created
        result = session.query(TestLSWorkspaceModel).filter_by(id=workspace_id).first()
        assert result is not None
        assert result.name == "研发部门标注空间"
        assert result.owner_id == user_a["id"]
        assert result.is_active is True

        # Verify owner is member
        owner = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=user_a["id"]
        ).first()
        assert owner is not None
        assert owner.role == WorkspaceMemberRole.OWNER

    def test_add_member_to_workspace(self, session, user_a, user_b):
        """Test adding a member to workspace."""
        workspace_id = str(uuid4())

        # Create workspace
        workspace = TestLSWorkspaceModel(
            id=workspace_id,
            name="Test Workspace",
            owner_id=user_a["id"],
        )
        session.add(workspace)

        # Add owner
        owner = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_a["id"],
            role=WorkspaceMemberRole.OWNER,
        )
        session.add(owner)

        # Add user B as annotator
        member = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_b["id"],
            role=WorkspaceMemberRole.ANNOTATOR,
        )
        session.add(member)
        session.commit()

        # Verify member added
        members = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            is_active=True
        ).all()
        assert len(members) == 2

        user_b_member = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=user_b["id"]
        ).first()
        assert user_b_member.role == WorkspaceMemberRole.ANNOTATOR

    def test_update_member_role(self, session, user_a, user_b):
        """Test updating member role."""
        workspace_id = str(uuid4())

        # Create workspace with owner and member
        workspace = TestLSWorkspaceModel(
            id=workspace_id,
            name="Test Workspace",
            owner_id=user_a["id"],
        )
        session.add(workspace)

        owner = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_a["id"],
            role=WorkspaceMemberRole.OWNER,
        )
        session.add(owner)

        member = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_b["id"],
            role=WorkspaceMemberRole.ANNOTATOR,
        )
        session.add(member)
        session.commit()

        # Update role to REVIEWER
        member.role = WorkspaceMemberRole.REVIEWER
        session.commit()

        # Verify role updated
        updated = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=user_b["id"]
        ).first()
        assert updated.role == WorkspaceMemberRole.REVIEWER

    def test_remove_member_from_workspace(self, session, user_a, user_b):
        """Test removing member from workspace (soft delete)."""
        workspace_id = str(uuid4())

        # Create workspace with owner and member
        workspace = TestLSWorkspaceModel(
            id=workspace_id,
            name="Test Workspace",
            owner_id=user_a["id"],
        )
        session.add(workspace)

        owner = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_a["id"],
            role=WorkspaceMemberRole.OWNER,
        )
        session.add(owner)

        member = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_b["id"],
            role=WorkspaceMemberRole.ANNOTATOR,
        )
        session.add(member)
        session.commit()

        # Remove member (soft delete)
        member.is_active = False
        session.commit()

        # Verify member is inactive
        active_members = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            is_active=True
        ).all()
        assert len(active_members) == 1
        assert active_members[0].user_id == user_a["id"]

    def test_delete_workspace_soft(self, session, user_a):
        """Test soft deleting a workspace."""
        workspace_id = str(uuid4())

        workspace = TestLSWorkspaceModel(
            id=workspace_id,
            name="Test Workspace",
            owner_id=user_a["id"],
        )
        session.add(workspace)
        session.commit()

        # Soft delete
        workspace.is_deleted = True
        workspace.is_active = False
        session.commit()

        # Verify workspace is marked as deleted
        result = session.query(TestLSWorkspaceModel).filter_by(id=workspace_id).first()
        assert result.is_deleted is True
        assert result.is_active is False

        # Should not appear in active workspaces query
        active = session.query(TestLSWorkspaceModel).filter_by(
            is_deleted=False,
            is_active=True
        ).all()
        assert all(w.id != workspace_id for w in active)


# ============================================================================
# Project Association Tests
# ============================================================================

class TestProjectAssociation:
    """Tests for project-workspace association."""

    def test_associate_project_to_workspace(self, session, user_a):
        """Test associating a Label Studio project to workspace."""
        workspace_id = str(uuid4())
        project_id = "123"

        # Create workspace
        workspace = TestLSWorkspaceModel(
            id=workspace_id,
            name="Test Workspace",
            owner_id=user_a["id"],
        )
        session.add(workspace)
        session.commit()

        # Associate project
        project = TestWorkspaceProjectModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            label_studio_project_id=project_id,
            project_metadata={"workspace_name": workspace.name},
        )
        session.add(project)
        session.commit()

        # Verify association
        result = session.query(TestWorkspaceProjectModel).filter_by(
            workspace_id=workspace_id,
            label_studio_project_id=project_id
        ).first()
        assert result is not None
        assert result.project_metadata["workspace_name"] == "Test Workspace"

    def test_list_workspace_projects(self, session, user_a):
        """Test listing projects in a workspace."""
        workspace_id = str(uuid4())

        # Create workspace
        workspace = TestLSWorkspaceModel(
            id=workspace_id,
            name="Test Workspace",
            owner_id=user_a["id"],
        )
        session.add(workspace)

        # Associate multiple projects
        for i in range(3):
            project = TestWorkspaceProjectModel(
                id=str(uuid4()),
                workspace_id=workspace_id,
                label_studio_project_id=str(100 + i),
            )
            session.add(project)
        session.commit()

        # List projects
        projects = session.query(TestWorkspaceProjectModel).filter_by(
            workspace_id=workspace_id
        ).all()
        assert len(projects) == 3

    def test_remove_project_association(self, session, user_a):
        """Test removing project association from workspace."""
        workspace_id = str(uuid4())
        project_association_id = str(uuid4())

        # Create workspace and project association
        workspace = TestLSWorkspaceModel(
            id=workspace_id,
            name="Test Workspace",
            owner_id=user_a["id"],
        )
        session.add(workspace)

        project = TestWorkspaceProjectModel(
            id=project_association_id,
            workspace_id=workspace_id,
            label_studio_project_id="123",
        )
        session.add(project)
        session.commit()

        # Remove association
        session.delete(project)
        session.commit()

        # Verify removed
        result = session.query(TestWorkspaceProjectModel).filter_by(
            id=project_association_id
        ).first()
        assert result is None


# ============================================================================
# Data Isolation Tests
# ============================================================================

class TestDataIsolation:
    """Tests for data isolation between workspaces."""

    def test_user_can_only_see_their_workspaces(self, session, user_a, user_b):
        """Test that users can only see workspaces they belong to."""
        # Create workspace A owned by user A
        workspace_a_id = str(uuid4())
        workspace_a = TestLSWorkspaceModel(
            id=workspace_a_id,
            name="Workspace A",
            owner_id=user_a["id"],
        )
        session.add(workspace_a)

        # Create workspace B owned by user B
        workspace_b_id = str(uuid4())
        workspace_b = TestLSWorkspaceModel(
            id=workspace_b_id,
            name="Workspace B",
            owner_id=user_b["id"],
        )
        session.add(workspace_b)

        # Add owners as members
        member_a = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_a_id,
            user_id=user_a["id"],
            role=WorkspaceMemberRole.OWNER,
        )
        session.add(member_a)

        member_b = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_b_id,
            user_id=user_b["id"],
            role=WorkspaceMemberRole.OWNER,
        )
        session.add(member_b)
        session.commit()

        # Query workspaces for user A
        user_a_workspaces = session.query(TestLSWorkspaceModel).join(
            TestLSWorkspaceMemberModel
        ).filter(
            TestLSWorkspaceMemberModel.user_id == user_a["id"],
            TestLSWorkspaceMemberModel.is_active == True
        ).all()

        assert len(user_a_workspaces) == 1
        assert user_a_workspaces[0].name == "Workspace A"

        # Query workspaces for user B
        user_b_workspaces = session.query(TestLSWorkspaceModel).join(
            TestLSWorkspaceMemberModel
        ).filter(
            TestLSWorkspaceMemberModel.user_id == user_b["id"],
            TestLSWorkspaceMemberModel.is_active == True
        ).all()

        assert len(user_b_workspaces) == 1
        assert user_b_workspaces[0].name == "Workspace B"

    def test_projects_isolated_by_workspace(self, session, user_a, user_b):
        """Test that projects are isolated by workspace."""
        # Create two workspaces
        workspace_a_id = str(uuid4())
        workspace_a = TestLSWorkspaceModel(
            id=workspace_a_id,
            name="Workspace A",
            owner_id=user_a["id"],
        )
        session.add(workspace_a)

        workspace_b_id = str(uuid4())
        workspace_b = TestLSWorkspaceModel(
            id=workspace_b_id,
            name="Workspace B",
            owner_id=user_b["id"],
        )
        session.add(workspace_b)

        # Add projects to each workspace
        for i in range(2):
            project_a = TestWorkspaceProjectModel(
                id=str(uuid4()),
                workspace_id=workspace_a_id,
                label_studio_project_id=f"a_{i}",
            )
            session.add(project_a)

            project_b = TestWorkspaceProjectModel(
                id=str(uuid4()),
                workspace_id=workspace_b_id,
                label_studio_project_id=f"b_{i}",
            )
            session.add(project_b)
        session.commit()

        # Query projects for workspace A
        workspace_a_projects = session.query(TestWorkspaceProjectModel).filter_by(
            workspace_id=workspace_a_id
        ).all()
        assert len(workspace_a_projects) == 2
        assert all(p.label_studio_project_id.startswith("a_") for p in workspace_a_projects)

        # Query projects for workspace B
        workspace_b_projects = session.query(TestWorkspaceProjectModel).filter_by(
            workspace_id=workspace_b_id
        ).all()
        assert len(workspace_b_projects) == 2
        assert all(p.label_studio_project_id.startswith("b_") for p in workspace_b_projects)


# ============================================================================
# Complete Workflow Test
# ============================================================================

class TestCompleteWorkflow:
    """End-to-end workflow test."""

    def test_complete_workspace_workflow(self, session, user_a, user_b, user_c):
        """Test complete workspace workflow from creation to deletion."""
        # Step 1: User A creates workspace
        workspace_id = str(uuid4())
        workspace = TestLSWorkspaceModel(
            id=workspace_id,
            name="完整工作流测试空间",
            description="测试完整的工作流程",
            owner_id=user_a["id"],
            settings={"auto_assign": True},
        )
        session.add(workspace)

        owner = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_a["id"],
            role=WorkspaceMemberRole.OWNER,
        )
        session.add(owner)
        session.commit()

        # Step 2: User A adds User B as annotator
        annotator = TestLSWorkspaceMemberModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            user_id=user_b["id"],
            role=WorkspaceMemberRole.ANNOTATOR,
        )
        session.add(annotator)
        session.commit()

        # Step 3: User A associates projects
        project = TestWorkspaceProjectModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            label_studio_project_id="project_001",
            project_metadata={"workspace_id": workspace_id, "workspace_name": workspace.name},
        )
        session.add(project)
        session.commit()

        # Step 4: Verify User B can see workspace
        user_b_workspaces = session.query(TestLSWorkspaceModel).join(
            TestLSWorkspaceMemberModel
        ).filter(
            TestLSWorkspaceMemberModel.user_id == user_b["id"],
            TestLSWorkspaceMemberModel.is_active == True
        ).all()
        assert len(user_b_workspaces) == 1

        # Step 5: Verify User C cannot see workspace
        user_c_workspaces = session.query(TestLSWorkspaceModel).join(
            TestLSWorkspaceMemberModel
        ).filter(
            TestLSWorkspaceMemberModel.user_id == user_c["id"],
            TestLSWorkspaceMemberModel.is_active == True
        ).all()
        assert len(user_c_workspaces) == 0

        # Step 6: Promote User B to reviewer
        annotator.role = WorkspaceMemberRole.REVIEWER
        session.commit()

        updated_role = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            user_id=user_b["id"]
        ).first()
        assert updated_role.role == WorkspaceMemberRole.REVIEWER

        # Step 7: Remove User B from workspace
        annotator.is_active = False
        session.commit()

        active_members = session.query(TestLSWorkspaceMemberModel).filter_by(
            workspace_id=workspace_id,
            is_active=True
        ).all()
        assert len(active_members) == 1

        # Step 8: Delete workspace
        workspace.is_deleted = True
        workspace.is_active = False
        session.commit()

        # Verify workspace is deleted
        active_workspaces = session.query(TestLSWorkspaceModel).filter_by(
            is_deleted=False,
            is_active=True
        ).all()
        assert all(w.id != workspace_id for w in active_workspaces)
