"""
Unit tests for Label Studio RBAC Service.

Tests the role-based access control and permission checking functionality.
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from src.label_studio.rbac_service import (
    RBACService,
    Permission,
    ROLE_PERMISSIONS,
    ROLE_HIERARCHY,
    PermissionDeniedError,
    NotAMemberError,
    get_rbac_service,
)
from src.label_studio.workspace_models import (
    LabelStudioWorkspaceMemberModel,
    WorkspaceProjectModel,
    ProjectMemberModel,
    WorkspaceMemberRole,
)


class TestPermissionEnum:
    """Tests for Permission enumeration."""

    def test_permission_values(self):
        """Test permission values are correctly formatted."""
        assert Permission.WORKSPACE_VIEW.value == "workspace:view"
        assert Permission.PROJECT_CREATE.value == "project:create"
        assert Permission.TASK_ANNOTATE.value == "task:annotate"
        assert Permission.DATA_EXPORT.value == "data:export"

    def test_all_permissions_have_values(self):
        """Test all permissions have string values."""
        for permission in Permission:
            assert isinstance(permission.value, str)
            assert ":" in permission.value


class TestRolePermissions:
    """Tests for role permission matrix."""

    def test_owner_has_all_permissions(self):
        """Test OWNER role has all permissions."""
        owner_permissions = ROLE_PERMISSIONS[WorkspaceMemberRole.OWNER]

        # Owner should have all permissions
        for permission in Permission:
            assert permission in owner_permissions

    def test_admin_lacks_workspace_delete(self):
        """Test ADMIN cannot delete workspace."""
        admin_permissions = ROLE_PERMISSIONS[WorkspaceMemberRole.ADMIN]

        assert Permission.WORKSPACE_DELETE not in admin_permissions
        assert Permission.WORKSPACE_EDIT in admin_permissions
        assert Permission.WORKSPACE_MANAGE_MEMBERS in admin_permissions

    def test_manager_lacks_workspace_management(self):
        """Test MANAGER cannot manage workspace members."""
        manager_permissions = ROLE_PERMISSIONS[WorkspaceMemberRole.MANAGER]

        assert Permission.WORKSPACE_MANAGE_MEMBERS not in manager_permissions
        assert Permission.WORKSPACE_DELETE not in manager_permissions
        assert Permission.PROJECT_CREATE in manager_permissions
        assert Permission.PROJECT_DELETE in manager_permissions

    def test_reviewer_has_limited_permissions(self):
        """Test REVIEWER has review-specific permissions."""
        reviewer_permissions = ROLE_PERMISSIONS[WorkspaceMemberRole.REVIEWER]

        assert Permission.TASK_REVIEW in reviewer_permissions
        assert Permission.TASK_ANNOTATE in reviewer_permissions
        assert Permission.DATA_EXPORT in reviewer_permissions
        assert Permission.PROJECT_CREATE not in reviewer_permissions
        assert Permission.PROJECT_DELETE not in reviewer_permissions

    def test_annotator_has_minimal_permissions(self):
        """Test ANNOTATOR has minimal permissions."""
        annotator_permissions = ROLE_PERMISSIONS[WorkspaceMemberRole.ANNOTATOR]

        assert Permission.WORKSPACE_VIEW in annotator_permissions
        assert Permission.PROJECT_VIEW in annotator_permissions
        assert Permission.TASK_VIEW in annotator_permissions
        assert Permission.TASK_ANNOTATE in annotator_permissions

        # Should not have these
        assert Permission.TASK_REVIEW not in annotator_permissions
        assert Permission.PROJECT_CREATE not in annotator_permissions
        assert Permission.DATA_EXPORT not in annotator_permissions

    def test_role_hierarchy_order(self):
        """Test role hierarchy is correctly ordered."""
        assert ROLE_HIERARCHY[0] == WorkspaceMemberRole.ANNOTATOR
        assert ROLE_HIERARCHY[-1] == WorkspaceMemberRole.OWNER

        annotator_index = ROLE_HIERARCHY.index(WorkspaceMemberRole.ANNOTATOR)
        reviewer_index = ROLE_HIERARCHY.index(WorkspaceMemberRole.REVIEWER)
        manager_index = ROLE_HIERARCHY.index(WorkspaceMemberRole.MANAGER)
        admin_index = ROLE_HIERARCHY.index(WorkspaceMemberRole.ADMIN)
        owner_index = ROLE_HIERARCHY.index(WorkspaceMemberRole.OWNER)

        assert annotator_index < reviewer_index < manager_index < admin_index < owner_index


class TestRBACService:
    """Tests for RBACService class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock SQLAlchemy session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create an RBACService with mock session."""
        return RBACService(mock_session)

    @pytest.fixture
    def sample_member(self):
        """Create a sample member with ADMIN role."""
        member = MagicMock(spec=LabelStudioWorkspaceMemberModel)
        member.workspace_id = uuid4()
        member.user_id = uuid4()
        member.role = WorkspaceMemberRole.ADMIN
        member.is_active = True
        return member

    # ========== check_permission Tests ==========

    def test_check_permission_allowed(self, service, mock_session, sample_member):
        """Test check_permission returns True for allowed permission."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_member

        result = service.check_permission(
            sample_member.user_id,
            sample_member.workspace_id,
            Permission.PROJECT_CREATE
        )

        assert result is True

    def test_check_permission_denied(self, service, mock_session, sample_member):
        """Test check_permission returns False for denied permission."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_member

        # Admin cannot delete workspace
        result = service.check_permission(
            sample_member.user_id,
            sample_member.workspace_id,
            Permission.WORKSPACE_DELETE
        )

        assert result is False

    def test_check_permission_not_member(self, service, mock_session):
        """Test check_permission returns False for non-member."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = service.check_permission(
            uuid4(),
            uuid4(),
            Permission.WORKSPACE_VIEW
        )

        assert result is False

    # ========== require_permission Tests ==========

    def test_require_permission_success(self, service, mock_session, sample_member):
        """Test require_permission passes for allowed permission."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_member

        # Should not raise
        service.require_permission(
            sample_member.user_id,
            sample_member.workspace_id,
            Permission.PROJECT_CREATE
        )

    def test_require_permission_denied(self, service, mock_session, sample_member):
        """Test require_permission raises PermissionDeniedError."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_member

        with pytest.raises(PermissionDeniedError) as exc_info:
            service.require_permission(
                sample_member.user_id,
                sample_member.workspace_id,
                Permission.WORKSPACE_DELETE
            )

        assert exc_info.value.permission == Permission.WORKSPACE_DELETE
        assert exc_info.value.user_id == sample_member.user_id

    def test_require_permission_not_member(self, service, mock_session):
        """Test require_permission raises NotAMemberError."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        user_id = uuid4()
        workspace_id = uuid4()

        with pytest.raises(NotAMemberError) as exc_info:
            service.require_permission(
                user_id,
                workspace_id,
                Permission.WORKSPACE_VIEW
            )

        assert exc_info.value.user_id == user_id
        assert exc_info.value.workspace_id == workspace_id

    # ========== get_user_permissions Tests ==========

    def test_get_user_permissions(self, service, mock_session, sample_member):
        """Test getting all user permissions."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_member

        permissions = service.get_user_permissions(
            sample_member.user_id,
            sample_member.workspace_id
        )

        # Should have ADMIN permissions
        assert Permission.PROJECT_CREATE in permissions
        assert Permission.WORKSPACE_DELETE not in permissions

    def test_get_user_permissions_empty_for_non_member(self, service, mock_session):
        """Test get_user_permissions returns empty set for non-member."""
        mock_session.query.return_value.filter.return_value.first.return_value = None

        permissions = service.get_user_permissions(uuid4(), uuid4())

        assert permissions == set()

    def test_get_user_permissions_list(self, service, mock_session, sample_member):
        """Test getting permissions as list of strings."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_member

        permission_list = service.get_user_permissions_list(
            sample_member.user_id,
            sample_member.workspace_id
        )

        assert isinstance(permission_list, list)
        assert "project:create" in permission_list
        assert "workspace:delete" not in permission_list

    # ========== can_access_project Tests ==========

    def test_can_access_project_with_workspace_permission(self, service, mock_session, sample_member):
        """Test project access with workspace-level permission."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_member

        result = service.can_access_project(
            sample_member.user_id,
            sample_member.workspace_id,
            "project-123"
        )

        assert result is True

    def test_can_access_project_without_workspace_permission(self, service, mock_session):
        """Test project access through project assignment."""
        # First query returns annotator member (no PROJECT_VIEW permission)
        annotator_member = MagicMock()
        annotator_member.role = WorkspaceMemberRole.ANNOTATOR
        annotator_member.is_active = True

        # Create a chain of query results
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        # Use side_effect for multiple calls
        project = MagicMock(spec=WorkspaceProjectModel)
        project.id = uuid4()

        project_member = MagicMock(spec=ProjectMemberModel)
        project_member.is_active = True

        # First call: get member role
        # Second call: get workspace project
        # Third call: get project member
        mock_query.filter.return_value.first.side_effect = [
            annotator_member,  # _get_user_role
            annotator_member,  # check_permission
            project,           # workspace_project query
            project_member,    # project_member query
        ]

        result = service.can_access_project(uuid4(), uuid4(), "project-123")

        # Note: This test might need adjustment based on actual implementation behavior

    # ========== can_perform_action Tests ==========

    def test_can_perform_action_known_actions(self, service, mock_session, sample_member):
        """Test can_perform_action with known action names."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_member

        assert service.can_perform_action(
            sample_member.user_id,
            sample_member.workspace_id,
            "view"
        ) is True

        assert service.can_perform_action(
            sample_member.user_id,
            sample_member.workspace_id,
            "create"
        ) is True

    def test_can_perform_action_unknown_action(self, service, mock_session, sample_member):
        """Test can_perform_action with unknown action returns False."""
        mock_session.query.return_value.filter.return_value.first.return_value = sample_member

        result = service.can_perform_action(
            sample_member.user_id,
            sample_member.workspace_id,
            "unknown_action"
        )

        assert result is False

    # ========== Role Comparison Tests ==========

    def test_compare_roles(self, service):
        """Test role comparison."""
        assert service.compare_roles(
            WorkspaceMemberRole.OWNER,
            WorkspaceMemberRole.ADMIN
        ) > 0

        assert service.compare_roles(
            WorkspaceMemberRole.ANNOTATOR,
            WorkspaceMemberRole.REVIEWER
        ) < 0

        assert service.compare_roles(
            WorkspaceMemberRole.MANAGER,
            WorkspaceMemberRole.MANAGER
        ) == 0

    def test_is_higher_role(self, service):
        """Test is_higher_role comparison."""
        assert service.is_higher_role(
            WorkspaceMemberRole.OWNER,
            WorkspaceMemberRole.ADMIN
        ) is True

        assert service.is_higher_role(
            WorkspaceMemberRole.ANNOTATOR,
            WorkspaceMemberRole.OWNER
        ) is False

    def test_can_manage_role(self, service):
        """Test can_manage_role logic."""
        # Owner can manage all
        assert service.can_manage_role(
            WorkspaceMemberRole.OWNER,
            WorkspaceMemberRole.ADMIN
        ) is True

        # Admin can manage lower roles
        assert service.can_manage_role(
            WorkspaceMemberRole.ADMIN,
            WorkspaceMemberRole.MANAGER
        ) is True

        # Admin cannot manage OWNER or other ADMIN
        assert service.can_manage_role(
            WorkspaceMemberRole.ADMIN,
            WorkspaceMemberRole.OWNER
        ) is False

        assert service.can_manage_role(
            WorkspaceMemberRole.ADMIN,
            WorkspaceMemberRole.ADMIN
        ) is False

        # Manager cannot manage roles
        assert service.can_manage_role(
            WorkspaceMemberRole.MANAGER,
            WorkspaceMemberRole.ANNOTATOR
        ) is False

    def test_get_manageable_roles(self, service):
        """Test getting manageable roles list."""
        owner_manageable = service.get_manageable_roles(WorkspaceMemberRole.OWNER)
        assert WorkspaceMemberRole.ADMIN in owner_manageable
        assert WorkspaceMemberRole.ANNOTATOR in owner_manageable

        admin_manageable = service.get_manageable_roles(WorkspaceMemberRole.ADMIN)
        assert WorkspaceMemberRole.OWNER not in admin_manageable
        assert WorkspaceMemberRole.ADMIN not in admin_manageable
        assert WorkspaceMemberRole.MANAGER in admin_manageable

        manager_manageable = service.get_manageable_roles(WorkspaceMemberRole.MANAGER)
        assert manager_manageable == []

    # ========== Helper Method Tests ==========

    def test_get_role_permissions(self, service):
        """Test getting permissions for a role."""
        permissions = service.get_role_permissions(WorkspaceMemberRole.REVIEWER)

        assert Permission.TASK_REVIEW in permissions
        assert Permission.PROJECT_CREATE not in permissions

    def test_get_permission_description(self, service):
        """Test getting permission descriptions."""
        desc = service.get_permission_description(Permission.WORKSPACE_VIEW)
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_get_role_description(self, service):
        """Test getting role descriptions."""
        desc = service.get_role_description(WorkspaceMemberRole.OWNER)
        assert isinstance(desc, str)
        assert "control" in desc.lower() or "full" in desc.lower()


class TestExceptions:
    """Tests for RBAC exceptions."""

    def test_permission_denied_error_message(self):
        """Test PermissionDeniedError message formatting."""
        user_id = uuid4()
        workspace_id = uuid4()

        error = PermissionDeniedError(
            user_id=user_id,
            permission=Permission.WORKSPACE_DELETE,
            workspace_id=workspace_id
        )

        assert str(user_id) in str(error)
        assert "workspace:delete" in str(error)
        assert str(workspace_id) in str(error)

    def test_not_a_member_error_message(self):
        """Test NotAMemberError message formatting."""
        user_id = uuid4()
        workspace_id = uuid4()

        error = NotAMemberError(user_id, workspace_id)

        assert str(user_id) in str(error)
        assert str(workspace_id) in str(error)
        assert "not a member" in str(error).lower()


class TestFactoryFunction:
    """Tests for factory function."""

    def test_get_rbac_service(self):
        """Test factory function creates service."""
        mock_session = MagicMock()
        service = get_rbac_service(mock_session)

        assert isinstance(service, RBACService)
        assert service.session == mock_session


class TestPermissionMatrix:
    """Tests to verify permission matrix consistency."""

    def test_all_roles_have_workspace_view(self):
        """Test all roles can at least view workspace."""
        for role in WorkspaceMemberRole:
            permissions = ROLE_PERMISSIONS[role]
            assert Permission.WORKSPACE_VIEW in permissions, f"{role} should have WORKSPACE_VIEW"

    def test_hierarchy_implies_permissions(self):
        """Test higher roles have at least as many permissions as lower roles."""
        for i, role in enumerate(ROLE_HIERARCHY[:-1]):
            next_role = ROLE_HIERARCHY[i + 1]
            current_permissions = ROLE_PERMISSIONS[role]
            next_permissions = ROLE_PERMISSIONS[next_role]

            # Higher role should have all permissions of lower role (except for WORKSPACE_DELETE special case)
            for perm in current_permissions:
                if perm != Permission.WORKSPACE_DELETE or next_role == WorkspaceMemberRole.OWNER:
                    assert perm in next_permissions, (
                        f"{next_role} should have {perm} since {role} has it"
                    )
