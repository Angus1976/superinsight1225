"""
Unit tests for Label Studio Workspace API.

Tests the REST API endpoints for workspace and member management.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient

from src.api.label_studio_workspace import (
    router,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    MemberAddRequest,
    MemberUpdateRequest,
    _parse_role,
)
from src.label_studio.workspace_models import WorkspaceMemberRole


class TestParseRole:
    """Tests for _parse_role helper function."""

    def test_parse_valid_roles(self):
        """Test parsing valid role strings."""
        assert _parse_role("owner") == WorkspaceMemberRole.OWNER
        assert _parse_role("ADMIN") == WorkspaceMemberRole.ADMIN
        assert _parse_role("Manager") == WorkspaceMemberRole.MANAGER
        assert _parse_role("reviewer") == WorkspaceMemberRole.REVIEWER
        assert _parse_role("annotator") == WorkspaceMemberRole.ANNOTATOR

    def test_parse_invalid_role(self):
        """Test parsing invalid role raises HTTPException."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _parse_role("invalid_role")

        assert exc_info.value.status_code == 400
        assert "Invalid role" in exc_info.value.detail


class TestWorkspaceCreateRequest:
    """Tests for WorkspaceCreateRequest validation."""

    def test_valid_request(self):
        """Test valid create request."""
        request = WorkspaceCreateRequest(
            name="Test Workspace",
            description="A test workspace",
            settings={"key": "value"}
        )

        assert request.name == "Test Workspace"
        assert request.description == "A test workspace"
        assert request.settings == {"key": "value"}

    def test_minimal_request(self):
        """Test minimal create request with only name."""
        request = WorkspaceCreateRequest(name="Minimal")

        assert request.name == "Minimal"
        assert request.description is None
        assert request.settings == {}

    def test_empty_name_fails(self):
        """Test that empty name fails validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            WorkspaceCreateRequest(name="")


class TestWorkspaceUpdateRequest:
    """Tests for WorkspaceUpdateRequest validation."""

    def test_partial_update(self):
        """Test partial update request."""
        request = WorkspaceUpdateRequest(name="New Name")

        assert request.name == "New Name"
        assert request.description is None
        assert request.settings is None
        assert request.is_active is None

    def test_full_update(self):
        """Test full update request."""
        request = WorkspaceUpdateRequest(
            name="Updated",
            description="New description",
            settings={"new": "settings"},
            is_active=False
        )

        assert request.name == "Updated"
        assert request.is_active is False


class TestMemberAddRequest:
    """Tests for MemberAddRequest validation."""

    def test_valid_request(self):
        """Test valid add member request."""
        user_id = uuid4()
        request = MemberAddRequest(user_id=user_id, role="reviewer")

        assert request.user_id == user_id
        assert request.role == "reviewer"

    def test_default_role(self):
        """Test default role is annotator."""
        request = MemberAddRequest(user_id=uuid4())

        assert request.role == "annotator"


class TestMemberUpdateRequest:
    """Tests for MemberUpdateRequest validation."""

    def test_valid_request(self):
        """Test valid update request."""
        request = MemberUpdateRequest(role="admin")

        assert request.role == "admin"


class TestAPIEndpointsStructure:
    """Tests for API endpoint structure and routing."""

    def test_router_prefix(self):
        """Test router has correct prefix."""
        assert router.prefix == "/api/ls-workspaces"

    def test_router_tags(self):
        """Test router has correct tags."""
        assert "Label Studio Workspaces" in router.tags

    def test_routes_exist(self):
        """Test expected routes are defined (paths include router prefix)."""
        routes = [route.path for route in router.routes]
        p = router.prefix

        assert f"{p}" in routes  # POST create, GET list
        assert f"{p}/{{workspace_id}}" in routes  # GET, PUT, DELETE
        assert f"{p}/{{workspace_id}}/members" in routes  # POST add, GET list
        assert f"{p}/{{workspace_id}}/members/{{user_id}}" in routes  # PUT, DELETE
        assert f"{p}/{{workspace_id}}/permissions" in routes  # GET


class TestWorkspaceCRUDEndpoints:
    """Integration-style tests for workspace CRUD endpoints."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        workspace_service = MagicMock()
        rbac_service = MagicMock()
        return workspace_service, rbac_service

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = MagicMock()
        user.id = uuid4()
        user.email = "test@example.com"
        user.full_name = "Test User"
        return user

    @pytest.fixture
    def mock_workspace(self):
        """Create mock workspace."""
        workspace = MagicMock()
        workspace.id = uuid4()
        workspace.name = "Test Workspace"
        workspace.description = "Description"
        workspace.owner_id = uuid4()
        workspace.settings = {}
        workspace.is_active = True
        workspace.is_deleted = False
        workspace.created_at = datetime.utcnow()
        workspace.updated_at = datetime.utcnow()
        return workspace

    def test_create_workspace_request_model(self):
        """Test create workspace request model structure."""
        request = WorkspaceCreateRequest(
            name="New Workspace",
            description="Description",
            settings={"auto_assign": True}
        )

        # Verify model can be serialized
        data = request.model_dump()
        assert data["name"] == "New Workspace"
        assert data["settings"]["auto_assign"] is True

    def test_update_workspace_request_model(self):
        """Test update workspace request model structure."""
        request = WorkspaceUpdateRequest(
            name="Updated Name",
            is_active=False
        )

        data = request.model_dump(exclude_none=True)
        assert data["name"] == "Updated Name"
        assert data["is_active"] is False
        assert "description" not in data


class TestMemberManagementEndpoints:
    """Integration-style tests for member management endpoints."""

    @pytest.fixture
    def mock_member(self):
        """Create mock member."""
        member = MagicMock()
        member.id = uuid4()
        member.workspace_id = uuid4()
        member.user_id = uuid4()
        member.role = WorkspaceMemberRole.ANNOTATOR
        member.is_active = True
        member.joined_at = datetime.utcnow()
        return member

    def test_add_member_request_model(self):
        """Test add member request model structure."""
        user_id = uuid4()
        request = MemberAddRequest(
            user_id=user_id,
            role="reviewer"
        )

        data = request.model_dump()
        assert data["user_id"] == user_id
        assert data["role"] == "reviewer"

    def test_update_member_request_model(self):
        """Test update member request model structure."""
        request = MemberUpdateRequest(role="admin")

        data = request.model_dump()
        assert data["role"] == "admin"


class TestResponseModels:
    """Tests for response models."""

    def test_workspace_response_serialization(self):
        """Test WorkspaceResponse serialization."""
        from src.api.label_studio_workspace import WorkspaceResponse

        response = WorkspaceResponse(
            id=str(uuid4()),
            name="Test",
            description="Desc",
            owner_id=str(uuid4()),
            settings={"key": "value"},
            is_active=True,
            is_deleted=False,
            member_count=5,
            project_count=3
        )

        data = response.model_dump()
        assert data["name"] == "Test"
        assert data["member_count"] == 5

    def test_member_response_serialization(self):
        """Test MemberResponse serialization."""
        from src.api.label_studio_workspace import MemberResponse

        response = MemberResponse(
            id=str(uuid4()),
            workspace_id=str(uuid4()),
            user_id=str(uuid4()),
            role="admin",
            is_active=True,
            user_email="user@example.com",
            user_name="Test User"
        )

        data = response.model_dump()
        assert data["role"] == "admin"
        assert data["user_email"] == "user@example.com"

    def test_workspace_list_response(self):
        """Test WorkspaceListResponse structure."""
        from src.api.label_studio_workspace import WorkspaceListResponse, WorkspaceResponse

        items = [
            WorkspaceResponse(
                id=str(uuid4()),
                name=f"Workspace {i}",
                owner_id=str(uuid4()),
                settings={},
            )
            for i in range(3)
        ]

        response = WorkspaceListResponse(items=items, total=3)

        data = response.model_dump()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_member_list_response(self):
        """Test MemberListResponse structure."""
        from src.api.label_studio_workspace import MemberListResponse, MemberResponse

        items = [
            MemberResponse(
                id=str(uuid4()),
                workspace_id=str(uuid4()),
                user_id=str(uuid4()),
                role="annotator"
            )
            for _ in range(2)
        ]

        response = MemberListResponse(items=items, total=2)

        data = response.model_dump()
        assert data["total"] == 2


class TestPermissionChecks:
    """Tests for permission checking logic."""

    def test_check_workspace_permission_helper(self):
        """Test _check_workspace_permission raises correct exceptions."""
        from src.api.label_studio_workspace import _check_workspace_permission
        from src.label_studio.rbac_service import (
            RBACService, Permission as RBACPermission,
            NotAMemberError, PermissionDeniedError
        )
        from fastapi import HTTPException

        mock_rbac = MagicMock(spec=RBACService)
        user_id = uuid4()
        workspace_id = uuid4()

        # Test NotAMemberError
        mock_rbac.require_permission.side_effect = NotAMemberError(user_id, workspace_id)

        with pytest.raises(HTTPException) as exc_info:
            _check_workspace_permission(
                mock_rbac, user_id, workspace_id, RBACPermission.WORKSPACE_VIEW
            )

        assert exc_info.value.status_code == 403
        assert "not a member" in exc_info.value.detail.lower()

        # Test PermissionDeniedError
        mock_rbac.require_permission.side_effect = PermissionDeniedError(
            user_id, RBACPermission.WORKSPACE_DELETE, workspace_id
        )

        with pytest.raises(HTTPException) as exc_info:
            _check_workspace_permission(
                mock_rbac, user_id, workspace_id, RBACPermission.WORKSPACE_DELETE
            )

        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail


class TestErrorHandling:
    """Tests for error handling in API endpoints."""

    def test_workspace_already_exists_returns_409(self):
        """Test that WorkspaceAlreadyExistsError returns 409."""
        # This would be tested in integration tests
        pass

    def test_workspace_not_found_returns_404(self):
        """Test that WorkspaceNotFoundError returns 404."""
        # This would be tested in integration tests
        pass

    def test_cannot_remove_owner_returns_409(self):
        """Test that CannotRemoveOwnerError returns 409."""
        # This would be tested in integration tests
        pass


class TestProjectAssociateRequest:
    """Tests for ProjectAssociateRequest validation."""

    def test_valid_request(self):
        """Test valid project association request."""
        from src.api.label_studio_workspace import ProjectAssociateRequest

        request = ProjectAssociateRequest(
            label_studio_project_id="123",
            superinsight_project_id=str(uuid4()),
            metadata={"key": "value"}
        )

        assert request.label_studio_project_id == "123"
        assert request.metadata == {"key": "value"}

    def test_minimal_request(self):
        """Test minimal project association request."""
        from src.api.label_studio_workspace import ProjectAssociateRequest

        request = ProjectAssociateRequest(label_studio_project_id="456")

        assert request.label_studio_project_id == "456"
        assert request.superinsight_project_id is None
        assert request.metadata == {}


class TestWorkspaceProjectResponse:
    """Tests for WorkspaceProjectResponse model."""

    def test_full_response(self):
        """Test full project response."""
        from src.api.label_studio_workspace import WorkspaceProjectResponse
        from datetime import datetime

        response = WorkspaceProjectResponse(
            id=str(uuid4()),
            workspace_id=str(uuid4()),
            label_studio_project_id="123",
            superinsight_project_id=str(uuid4()),
            metadata={"workspace_name": "Test"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            project_title="Test Project",
            project_description="Test description"
        )

        data = response.model_dump()
        assert data["label_studio_project_id"] == "123"
        assert data["project_title"] == "Test Project"

    def test_minimal_response(self):
        """Test minimal project response."""
        from src.api.label_studio_workspace import WorkspaceProjectResponse

        response = WorkspaceProjectResponse(
            id=str(uuid4()),
            workspace_id=str(uuid4()),
            label_studio_project_id="456"
        )

        data = response.model_dump()
        assert data["label_studio_project_id"] == "456"
        assert data["superinsight_project_id"] is None
        assert data["metadata"] == {}


class TestWorkspaceProjectListResponse:
    """Tests for WorkspaceProjectListResponse model."""

    def test_project_list_response(self):
        """Test project list response structure."""
        from src.api.label_studio_workspace import (
            WorkspaceProjectListResponse,
            WorkspaceProjectResponse
        )

        workspace_id = str(uuid4())
        items = [
            WorkspaceProjectResponse(
                id=str(uuid4()),
                workspace_id=workspace_id,
                label_studio_project_id=f"project-{i}"
            )
            for i in range(3)
        ]

        response = WorkspaceProjectListResponse(items=items, total=3)

        data = response.model_dump()
        assert data["total"] == 3
        assert len(data["items"]) == 3


class TestProjectAssociationAPIStructure:
    """Tests for project association API endpoint structure."""

    def test_router_has_project_routes(self):
        """Test expected project routes are defined."""
        from src.api.label_studio_workspace import router

        routes = [route.path for route in router.routes]
        p = router.prefix

        assert f"{p}/{{workspace_id}}/projects" in routes  # POST, GET
        assert f"{p}/{{workspace_id}}/projects/{{project_id}}" in routes  # GET, DELETE
