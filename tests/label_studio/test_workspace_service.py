"""
Unit tests for Label Studio Workspace Service.

Tests the workspace CRUD operations and member management functionality.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import MagicMock, patch, PropertyMock

from src.label_studio.workspace_service import (
    WorkspaceService,
    WorkspaceInfo,
    MemberInfo,
    WorkspaceNotFoundError,
    WorkspaceAlreadyExistsError,
    MemberNotFoundError,
    MemberAlreadyExistsError,
    CannotRemoveOwnerError,
    WorkspaceHasProjectsError,
    get_workspace_service,
)
from src.label_studio.workspace_models import (
    LabelStudioWorkspaceModel,
    LabelStudioWorkspaceMemberModel,
    WorkspaceMemberRole,
)


class TestWorkspaceService:
    """Tests for WorkspaceService class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock SQLAlchemy session."""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        session.delete = MagicMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create a WorkspaceService with mock session."""
        return WorkspaceService(mock_session)

    @pytest.fixture
    def sample_workspace(self):
        """Create a sample workspace for testing."""
        workspace = MagicMock(spec=LabelStudioWorkspaceModel)
        workspace.id = uuid4()
        workspace.name = "Test Workspace"
        workspace.description = "Test description"
        workspace.owner_id = uuid4()
        workspace.settings = {}
        workspace.is_active = True
        workspace.is_deleted = False
        workspace.created_at = datetime.utcnow()
        workspace.updated_at = datetime.utcnow()
        return workspace

    @pytest.fixture
    def sample_member(self, sample_workspace):
        """Create a sample member for testing."""
        member = MagicMock(spec=LabelStudioWorkspaceMemberModel)
        member.id = uuid4()
        member.workspace_id = sample_workspace.id
        member.user_id = uuid4()
        member.role = WorkspaceMemberRole.ANNOTATOR
        member.is_active = True
        member.joined_at = datetime.utcnow()
        return member

    # ========== Create Workspace Tests ==========

    def test_create_workspace_success(self, service, mock_session):
        """Test successful workspace creation."""
        owner_id = uuid4()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        workspace = service.create_workspace(
            name="New Workspace",
            owner_id=owner_id,
            description="Description"
        )

        assert mock_session.add.called
        assert mock_session.commit.called
        assert workspace.name == "New Workspace"
        assert workspace.owner_id == owner_id

    def test_create_workspace_already_exists(self, service, mock_session, sample_workspace):
        """Test creating workspace with existing name raises error."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = sample_workspace
        mock_session.query.return_value = mock_query

        with pytest.raises(WorkspaceAlreadyExistsError):
            service.create_workspace(
                name="Existing Workspace",
                owner_id=uuid4()
            )

    def test_create_workspace_with_settings(self, service, mock_session):
        """Test creating workspace with custom settings."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        settings = {"max_annotators": 10, "auto_assign": True}
        workspace = service.create_workspace(
            name="Custom Workspace",
            owner_id=uuid4(),
            settings=settings
        )

        assert workspace.settings == settings

    # ========== Get Workspace Tests ==========

    def test_get_workspace_found(self, service, mock_session, sample_workspace):
        """Test getting existing workspace."""
        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.first.return_value = sample_workspace
        mock_session.query.return_value = mock_query

        result = service.get_workspace(sample_workspace.id)

        assert result == sample_workspace

    def test_get_workspace_not_found(self, service, mock_session):
        """Test getting non-existent workspace returns None."""
        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        result = service.get_workspace(uuid4())

        assert result is None

    def test_get_workspace_include_deleted(self, service, mock_session, sample_workspace):
        """Test getting workspace including deleted ones."""
        sample_workspace.is_deleted = True
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = sample_workspace
        mock_session.query.return_value = mock_query

        result = service.get_workspace(sample_workspace.id, include_deleted=True)

        assert result == sample_workspace

    # ========== Update Workspace Tests ==========

    def test_update_workspace_success(self, service, mock_session, sample_workspace):
        """Test successful workspace update."""
        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.first.return_value = sample_workspace
        mock_session.query.return_value = mock_query

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, 'get_workspace_by_name', return_value=None):
                result = service.update_workspace(
                    sample_workspace.id,
                    {"description": "Updated description"}
                )

        assert mock_session.commit.called

    def test_update_workspace_not_found(self, service, mock_session):
        """Test updating non-existent workspace raises error."""
        with patch.object(service, 'get_workspace', return_value=None):
            with pytest.raises(WorkspaceNotFoundError):
                service.update_workspace(uuid4(), {"name": "New Name"})

    def test_update_workspace_name_conflict(self, service, mock_session, sample_workspace):
        """Test updating workspace with conflicting name raises error."""
        other_workspace = MagicMock()
        other_workspace.id = uuid4()
        other_workspace.name = "Existing Name"

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, 'get_workspace_by_name', return_value=other_workspace):
                with pytest.raises(WorkspaceAlreadyExistsError):
                    service.update_workspace(
                        sample_workspace.id,
                        {"name": "Existing Name"}
                    )

    # ========== Delete Workspace Tests ==========

    def test_delete_workspace_soft(self, service, mock_session, sample_workspace):
        """Test soft deleting workspace."""
        mock_project_query = MagicMock()
        mock_project_query.filter.return_value.count.return_value = 0

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            mock_session.query.return_value = mock_project_query
            result = service.delete_workspace(sample_workspace.id)

        assert result is True
        assert sample_workspace.is_deleted is True
        assert mock_session.commit.called

    def test_delete_workspace_with_projects_error(self, service, mock_session, sample_workspace):
        """Test deleting workspace with projects raises error."""
        mock_project_query = MagicMock()
        mock_project_query.filter.return_value.count.return_value = 3

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            mock_session.query.return_value = mock_project_query

            with pytest.raises(WorkspaceHasProjectsError):
                service.delete_workspace(sample_workspace.id)

    def test_delete_workspace_hard(self, service, mock_session, sample_workspace):
        """Test hard deleting workspace."""
        mock_project_query = MagicMock()
        mock_project_query.filter.return_value.count.return_value = 0

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            mock_session.query.return_value = mock_project_query
            result = service.delete_workspace(sample_workspace.id, hard_delete=True)

        assert result is True
        assert mock_session.delete.called

    # ========== Member Management Tests ==========

    def test_add_member_success(self, service, mock_session, sample_workspace):
        """Test adding member to workspace."""
        user_id = uuid4()

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, '_get_membership', return_value=None):
                member = service.add_member(
                    sample_workspace.id,
                    user_id,
                    WorkspaceMemberRole.ANNOTATOR
                )

        assert mock_session.add.called
        assert mock_session.commit.called
        assert member.user_id == user_id
        assert member.role == WorkspaceMemberRole.ANNOTATOR

    def test_add_member_already_exists(self, service, mock_session, sample_workspace, sample_member):
        """Test adding existing member raises error."""
        sample_member.is_active = True

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, '_get_membership', return_value=sample_member):
                with pytest.raises(MemberAlreadyExistsError):
                    service.add_member(
                        sample_workspace.id,
                        sample_member.user_id,
                        WorkspaceMemberRole.ANNOTATOR
                    )

    def test_add_member_reactivate(self, service, mock_session, sample_workspace, sample_member):
        """Test reactivating inactive member."""
        sample_member.is_active = False

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, '_get_membership', return_value=sample_member):
                result = service.add_member(
                    sample_workspace.id,
                    sample_member.user_id,
                    WorkspaceMemberRole.REVIEWER
                )

        assert result.is_active is True
        assert result.role == WorkspaceMemberRole.REVIEWER

    def test_remove_member_success(self, service, mock_session, sample_workspace, sample_member):
        """Test removing member from workspace."""
        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, '_get_membership', return_value=sample_member):
                result = service.remove_member(
                    sample_workspace.id,
                    sample_member.user_id
                )

        assert result is True
        assert sample_member.is_active is False

    def test_remove_member_not_found(self, service, mock_session, sample_workspace):
        """Test removing non-existent member raises error."""
        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, '_get_membership', return_value=None):
                with pytest.raises(MemberNotFoundError):
                    service.remove_member(sample_workspace.id, uuid4())

    def test_remove_last_owner_error(self, service, mock_session, sample_workspace, sample_member):
        """Test removing last owner raises error."""
        sample_member.role = WorkspaceMemberRole.OWNER

        mock_owner_query = MagicMock()
        mock_owner_query.filter.return_value.count.return_value = 1

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, '_get_membership', return_value=sample_member):
                mock_session.query.return_value = mock_owner_query

                with pytest.raises(CannotRemoveOwnerError):
                    service.remove_member(sample_workspace.id, sample_member.user_id)

    def test_update_member_role_success(self, service, mock_session, sample_workspace, sample_member):
        """Test updating member role."""
        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, '_get_membership', return_value=sample_member):
                result = service.update_member_role(
                    sample_workspace.id,
                    sample_member.user_id,
                    WorkspaceMemberRole.REVIEWER
                )

        assert result.role == WorkspaceMemberRole.REVIEWER

    def test_demote_last_owner_error(self, service, mock_session, sample_workspace, sample_member):
        """Test demoting last owner raises error."""
        sample_member.role = WorkspaceMemberRole.OWNER

        mock_owner_query = MagicMock()
        mock_owner_query.filter.return_value.count.return_value = 1

        with patch.object(service, 'get_workspace', return_value=sample_workspace):
            with patch.object(service, '_get_membership', return_value=sample_member):
                mock_session.query.return_value = mock_owner_query

                with pytest.raises(CannotRemoveOwnerError):
                    service.update_member_role(
                        sample_workspace.id,
                        sample_member.user_id,
                        WorkspaceMemberRole.ADMIN
                    )

    def test_get_member_role(self, service, mock_session, sample_member):
        """Test getting member role."""
        with patch.object(service, '_get_membership', return_value=sample_member):
            role = service.get_member_role(uuid4(), sample_member.user_id)

        assert role == sample_member.role

    def test_get_member_role_not_member(self, service, mock_session):
        """Test getting role for non-member returns None."""
        with patch.object(service, '_get_membership', return_value=None):
            role = service.get_member_role(uuid4(), uuid4())

        assert role is None

    def test_is_member_true(self, service, sample_member):
        """Test is_member returns True for active member."""
        sample_member.is_active = True

        with patch.object(service, '_get_membership', return_value=sample_member):
            result = service.is_member(uuid4(), sample_member.user_id)

        assert result is True

    def test_is_member_false(self, service):
        """Test is_member returns False for non-member."""
        with patch.object(service, '_get_membership', return_value=None):
            result = service.is_member(uuid4(), uuid4())

        assert result is False


class TestWorkspaceInfo:
    """Tests for WorkspaceInfo DTO."""

    def test_workspace_info_to_dict(self):
        """Test WorkspaceInfo serialization."""
        workspace_id = uuid4()
        owner_id = uuid4()
        created_at = datetime.utcnow()
        updated_at = datetime.utcnow()

        info = WorkspaceInfo(
            id=workspace_id,
            name="Test",
            description="Desc",
            owner_id=owner_id,
            settings={"key": "value"},
            is_active=True,
            is_deleted=False,
            created_at=created_at,
            updated_at=updated_at,
            member_count=5,
            project_count=3,
        )

        result = info.to_dict()

        assert result["id"] == str(workspace_id)
        assert result["name"] == "Test"
        assert result["member_count"] == 5
        assert result["project_count"] == 3


class TestMemberInfo:
    """Tests for MemberInfo DTO."""

    def test_member_info_to_dict(self):
        """Test MemberInfo serialization."""
        member_id = uuid4()
        workspace_id = uuid4()
        user_id = uuid4()
        joined_at = datetime.utcnow()

        info = MemberInfo(
            id=member_id,
            workspace_id=workspace_id,
            user_id=user_id,
            role=WorkspaceMemberRole.ADMIN,
            is_active=True,
            joined_at=joined_at,
            user_email="test@example.com",
            user_name="Test User",
        )

        result = info.to_dict()

        assert result["id"] == str(member_id)
        assert result["role"] == "admin"
        assert result["user_email"] == "test@example.com"


class TestFactoryFunction:
    """Tests for factory function."""

    def test_get_workspace_service(self):
        """Test factory function creates service."""
        mock_session = MagicMock()
        service = get_workspace_service(mock_session)

        assert isinstance(service, WorkspaceService)
        assert service.session == mock_session
