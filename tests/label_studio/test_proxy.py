"""
Unit tests for Label Studio Proxy.

Tests the proxy request forwarding, permission verification,
metadata injection, and metadata extraction functionality.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from src.label_studio.proxy import (
    LabelStudioProxy,
    ProxyResponse,
    ProxyError,
    LabelStudioConnectionError,
    LabelStudioAPIError,
    ProxyPermissionError,
    create_label_studio_proxy,
)
from src.label_studio.rbac_service import Permission, PermissionDeniedError, NotAMemberError
from src.label_studio.metadata_codec import WorkspaceMetadata, get_metadata_codec


class TestProxyResponse:
    """Tests for ProxyResponse class."""

    def test_success_response(self):
        """Test successful response properties."""
        response = ProxyResponse(
            status_code=200,
            body={"id": 1, "name": "Project"},
            headers={"Content-Type": "application/json"}
        )

        assert response.is_success is True
        assert response.is_error is False
        assert response.status_code == 200

    def test_error_response(self):
        """Test error response properties."""
        response = ProxyResponse(
            status_code=403,
            body={"detail": "Permission denied"}
        )

        assert response.is_success is False
        assert response.is_error is True

    def test_to_dict(self):
        """Test response serialization."""
        response = ProxyResponse(
            status_code=200,
            body={"data": "test"},
            headers={"X-Custom": "value"}
        )

        result = response.to_dict()

        assert result["status_code"] == 200
        assert result["body"]["data"] == "test"
        assert result["headers"]["X-Custom"] == "value"


class TestLabelStudioProxy:
    """Tests for LabelStudioProxy class."""

    @pytest.fixture
    def mock_workspace_service(self):
        """Create mock workspace service."""
        service = MagicMock()
        workspace = MagicMock()
        workspace.id = uuid4()
        workspace.name = "Test Workspace"
        workspace.owner_id = uuid4()
        workspace.is_active = True
        service.get_workspace.return_value = workspace
        return service

    @pytest.fixture
    def mock_rbac_service(self):
        """Create mock RBAC service."""
        service = MagicMock()
        service.require_permission.return_value = None
        service.check_permission.return_value = True
        return service

    @pytest.fixture
    def proxy(self, mock_workspace_service, mock_rbac_service):
        """Create proxy with mocked dependencies."""
        return LabelStudioProxy(
            label_studio_url="http://localhost:8080",
            api_token="test-token",
            workspace_service=mock_workspace_service,
            rbac_service=mock_rbac_service,
        )

    # ========== Permission Mapping Tests ==========

    def test_get_required_permission_project_get(self, proxy):
        """Test permission mapping for GET /api/projects."""
        perm = proxy._get_required_permission("GET", "/api/projects")
        assert perm == Permission.PROJECT_VIEW

    def test_get_required_permission_project_post(self, proxy):
        """Test permission mapping for POST /api/projects."""
        perm = proxy._get_required_permission("POST", "/api/projects")
        assert perm == Permission.PROJECT_CREATE

    def test_get_required_permission_project_delete(self, proxy):
        """Test permission mapping for DELETE /api/projects/1."""
        perm = proxy._get_required_permission("DELETE", "/api/projects/1")
        assert perm == Permission.PROJECT_DELETE

    def test_get_required_permission_task_annotate(self, proxy):
        """Test permission mapping for POST /api/tasks."""
        perm = proxy._get_required_permission("POST", "/api/tasks")
        assert perm == Permission.TASK_ANNOTATE

    def test_get_required_permission_export(self, proxy):
        """Test permission mapping for export endpoints."""
        perm = proxy._get_required_permission("GET", "/api/projects/1/export")
        assert perm == Permission.DATA_EXPORT

    def test_get_required_permission_import(self, proxy):
        """Test permission mapping for import endpoints."""
        perm = proxy._get_required_permission("POST", "/api/projects/1/import")
        assert perm == Permission.DATA_IMPORT

    # ========== Permission Verification Tests ==========

    @pytest.mark.asyncio
    async def test_verify_permissions_success(self, proxy, mock_rbac_service):
        """Test permission verification succeeds."""
        user_id = uuid4()
        workspace_id = uuid4()

        # Should not raise
        await proxy._verify_permissions(
            user_id, workspace_id, "GET", "/api/projects"
        )

        mock_rbac_service.require_permission.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_permissions_denied(self, proxy, mock_rbac_service):
        """Test permission verification raises error when denied."""
        user_id = uuid4()
        workspace_id = uuid4()

        mock_rbac_service.require_permission.side_effect = PermissionDeniedError(
            user_id=user_id,
            permission=Permission.PROJECT_CREATE,
            workspace_id=workspace_id
        )

        with pytest.raises(ProxyPermissionError) as exc_info:
            await proxy._verify_permissions(
                user_id, workspace_id, "POST", "/api/projects"
            )

        assert exc_info.value.permission == Permission.PROJECT_CREATE

    @pytest.mark.asyncio
    async def test_verify_permissions_not_member(self, proxy, mock_rbac_service):
        """Test permission verification raises error for non-member."""
        user_id = uuid4()
        workspace_id = uuid4()

        mock_rbac_service.require_permission.side_effect = NotAMemberError(
            user_id, workspace_id
        )

        with pytest.raises(ProxyPermissionError):
            await proxy._verify_permissions(
                user_id, workspace_id, "GET", "/api/projects"
            )

    # ========== Metadata Injection Tests ==========

    @pytest.mark.asyncio
    async def test_inject_metadata(self, proxy, mock_workspace_service):
        """Test metadata injection into project description."""
        user_id = uuid4()
        workspace_id = uuid4()
        body = {
            "title": "Test Project",
            "description": "Original description"
        }

        result = await proxy._inject_metadata(body, user_id, workspace_id)

        # Description should be modified
        assert result["description"] != "Original description"
        assert "[SUPERINSIGHT_META:" in result["description"]
        assert "Original description" in result["description"]

    @pytest.mark.asyncio
    async def test_inject_metadata_empty_description(self, proxy, mock_workspace_service):
        """Test metadata injection with empty description."""
        user_id = uuid4()
        workspace_id = uuid4()
        body = {"title": "Test Project"}

        result = await proxy._inject_metadata(body, user_id, workspace_id)

        assert "[SUPERINSIGHT_META:" in result["description"]

    @pytest.mark.asyncio
    async def test_inject_metadata_workspace_not_found(self, proxy, mock_workspace_service):
        """Test metadata injection when workspace not found."""
        mock_workspace_service.get_workspace.return_value = None
        user_id = uuid4()
        workspace_id = uuid4()
        body = {"title": "Test", "description": "Desc"}

        result = await proxy._inject_metadata(body, user_id, workspace_id)

        # Should return original body
        assert result["description"] == "Desc"

    # ========== Metadata Extraction Tests ==========

    @pytest.mark.asyncio
    async def test_enhance_project_with_metadata(self, proxy, mock_workspace_service):
        """Test project enhancement extracts metadata."""
        # Create encoded description
        codec = get_metadata_codec()
        metadata = WorkspaceMetadata(
            workspace_id=str(uuid4()),
            workspace_name="Test Workspace",
            created_by=str(uuid4()),
        )
        encoded_desc = codec.encode("Original desc", metadata)

        project = {
            "id": 1,
            "title": "Project",
            "description": encoded_desc
        }

        result = await proxy._enhance_project(project)

        assert result["description"] == "Original desc"
        assert "workspace" in result
        assert result["workspace"]["name"] == "Test Workspace"

    @pytest.mark.asyncio
    async def test_enhance_project_without_metadata(self, proxy):
        """Test project enhancement with no metadata."""
        project = {
            "id": 1,
            "title": "Project",
            "description": "Plain description"
        }

        result = await proxy._enhance_project(project)

        assert result["description"] == "Plain description"
        assert "workspace" not in result

    @pytest.mark.asyncio
    async def test_extract_metadata_from_list(self, proxy, mock_workspace_service):
        """Test metadata extraction from project list."""
        codec = get_metadata_codec()
        metadata = WorkspaceMetadata(
            workspace_id=str(uuid4()),
            workspace_name="WS",
            created_by=str(uuid4()),
        )

        projects = [
            {"id": 1, "description": codec.encode("Desc 1", metadata)},
            {"id": 2, "description": "No metadata"},
        ]

        result = await proxy._extract_metadata(projects)

        assert len(result) == 2
        assert result[0]["description"] == "Desc 1"
        assert "workspace" in result[0]
        assert "workspace" not in result[1]

    @pytest.mark.asyncio
    async def test_extract_metadata_paginated_response(self, proxy, mock_workspace_service):
        """Test metadata extraction from paginated response."""
        codec = get_metadata_codec()
        metadata = WorkspaceMetadata(
            workspace_id=str(uuid4()),
            workspace_name="WS",
            created_by=str(uuid4()),
        )

        body = {
            "count": 1,
            "results": [
                {"id": 1, "description": codec.encode("Desc", metadata)}
            ]
        }

        result = await proxy._extract_metadata(body)

        assert result["count"] == 1
        assert result["results"][0]["description"] == "Desc"
        assert "workspace" in result["results"][0]

    # ========== Request Preprocessing Tests ==========

    @pytest.mark.asyncio
    async def test_preprocess_request_project_creation(self, proxy, mock_workspace_service):
        """Test preprocessing injects metadata for project creation."""
        user_id = uuid4()
        workspace_id = uuid4()
        body = {"title": "New Project", "description": "Desc"}

        result = await proxy._preprocess_request(
            "POST", "/api/projects", body, user_id, workspace_id
        )

        assert "[SUPERINSIGHT_META:" in result["description"]

    @pytest.mark.asyncio
    async def test_preprocess_request_no_workspace(self, proxy):
        """Test preprocessing without workspace context."""
        user_id = uuid4()
        body = {"title": "New Project", "description": "Desc"}

        result = await proxy._preprocess_request(
            "POST", "/api/projects", body, user_id, None
        )

        # Should return unmodified body
        assert result["description"] == "Desc"

    @pytest.mark.asyncio
    async def test_preprocess_request_non_project(self, proxy):
        """Test preprocessing for non-project endpoints."""
        user_id = uuid4()
        workspace_id = uuid4()
        body = {"data": "task data"}

        result = await proxy._preprocess_request(
            "POST", "/api/tasks", body, user_id, workspace_id
        )

        # Should return unmodified body
        assert result == body


class TestProxyForwarding:
    """Tests for request forwarding functionality."""

    @pytest.fixture
    def mock_workspace_service(self):
        service = MagicMock()
        workspace = MagicMock()
        workspace.id = uuid4()
        workspace.name = "Test"
        workspace.owner_id = uuid4()
        workspace.is_active = True
        service.get_workspace.return_value = workspace
        return service

    @pytest.fixture
    def mock_rbac_service(self):
        service = MagicMock()
        service.require_permission.return_value = None
        return service

    @pytest.fixture
    def proxy(self, mock_workspace_service, mock_rbac_service):
        return LabelStudioProxy(
            label_studio_url="http://localhost:8080",
            api_token="test-token",
            workspace_service=mock_workspace_service,
            rbac_service=mock_rbac_service,
        )

    @pytest.mark.asyncio
    async def test_forward_request_success(self, proxy):
        """Test successful request forwarding."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "title": "Project"}
        mock_response.headers = {"Content-Type": "application/json"}

        with patch.object(proxy, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_get_client.return_value = mock_client

            response = await proxy._forward_request(
                "GET", "/api/projects", None, None
            )

            assert response.status_code == 200
            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_forward_request_connection_error(self, proxy):
        """Test handling of connection errors."""
        with patch.object(proxy, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.side_effect = httpx.ConnectError("Connection refused")
            mock_get_client.return_value = mock_client

            with pytest.raises(LabelStudioConnectionError):
                await proxy._forward_request("GET", "/api/projects", None, None)

    @pytest.mark.asyncio
    async def test_forward_request_timeout(self, proxy):
        """Test handling of timeout errors."""
        with patch.object(proxy, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.request.side_effect = httpx.TimeoutException("Timeout")
            mock_get_client.return_value = mock_client

            with pytest.raises(LabelStudioConnectionError) as exc_info:
                await proxy._forward_request("GET", "/api/projects", None, None)

            assert "timed out" in str(exc_info.value).lower()


class TestConvenienceMethods:
    """Tests for convenience methods."""

    @pytest.fixture
    def mock_workspace_service(self):
        service = MagicMock()
        workspace = MagicMock()
        workspace.id = uuid4()
        workspace.name = "Test"
        workspace.owner_id = uuid4()
        workspace.is_active = True
        service.get_workspace.return_value = workspace
        return service

    @pytest.fixture
    def mock_rbac_service(self):
        service = MagicMock()
        service.require_permission.return_value = None
        return service

    @pytest.fixture
    def proxy(self, mock_workspace_service, mock_rbac_service):
        return LabelStudioProxy(
            label_studio_url="http://localhost:8080",
            api_token="test-token",
            workspace_service=mock_workspace_service,
            rbac_service=mock_rbac_service,
        )

    @pytest.mark.asyncio
    async def test_get_projects(self, proxy):
        """Test get_projects convenience method."""
        user_id = uuid4()

        with patch.object(proxy, 'proxy_request', new_callable=AsyncMock) as mock_proxy:
            mock_proxy.return_value = ProxyResponse(200, [{"id": 1}])

            await proxy.get_projects(user_id)

            mock_proxy.assert_called_once_with(
                method="GET",
                path="/api/projects",
                user_id=user_id,
                workspace_id=None,
            )

    @pytest.mark.asyncio
    async def test_create_project(self, proxy):
        """Test create_project convenience method."""
        user_id = uuid4()
        workspace_id = uuid4()
        project_data = {"title": "New Project"}

        with patch.object(proxy, 'proxy_request', new_callable=AsyncMock) as mock_proxy:
            mock_proxy.return_value = ProxyResponse(201, {"id": 1})

            await proxy.create_project(project_data, user_id, workspace_id)

            mock_proxy.assert_called_once_with(
                method="POST",
                path="/api/projects",
                user_id=user_id,
                workspace_id=workspace_id,
                body=project_data,
            )

    @pytest.mark.asyncio
    async def test_delete_project(self, proxy):
        """Test delete_project convenience method."""
        user_id = uuid4()

        with patch.object(proxy, 'proxy_request', new_callable=AsyncMock) as mock_proxy:
            mock_proxy.return_value = ProxyResponse(204, None)

            await proxy.delete_project(123, user_id)

            mock_proxy.assert_called_once_with(
                method="DELETE",
                path="/api/projects/123",
                user_id=user_id,
                workspace_id=None,
            )


class TestFactoryFunction:
    """Tests for factory function."""

    def test_create_label_studio_proxy(self):
        """Test factory function creates proxy."""
        mock_ws = MagicMock()
        mock_rbac = MagicMock()

        proxy = create_label_studio_proxy(
            label_studio_url="http://localhost:8080",
            api_token="token",
            workspace_service=mock_ws,
            rbac_service=mock_rbac,
        )

        assert isinstance(proxy, LabelStudioProxy)
        assert proxy.label_studio_url == "http://localhost:8080"
        assert proxy.api_token == "token"


class TestExceptions:
    """Tests for proxy exceptions."""

    def test_proxy_permission_error(self):
        """Test ProxyPermissionError message."""
        user_id = uuid4()
        workspace_id = uuid4()

        error = ProxyPermissionError(
            user_id, Permission.PROJECT_CREATE, workspace_id
        )

        assert str(user_id) in str(error)
        assert "project:create" in str(error)
        assert str(workspace_id) in str(error)

    def test_label_studio_api_error(self):
        """Test LabelStudioAPIError."""
        error = LabelStudioAPIError(
            status_code=404,
            detail="Project not found",
            response_body={"detail": "Project not found"}
        )

        assert error.status_code == 404
        assert "Project not found" in str(error)
        assert error.response_body is not None
