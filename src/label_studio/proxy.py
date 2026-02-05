"""
Label Studio Proxy for Enterprise Workspace.

This module provides a proxy layer for Label Studio API requests with:
- Permission verification before forwarding requests
- Metadata injection on project creation
- Metadata extraction on project retrieval
- Audit logging for all operations
- Error handling and retry logic

The proxy intercepts requests to Label Studio and adds workspace-aware
functionality while maintaining backward compatibility.
"""

import logging
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List, Union
from uuid import UUID
from enum import Enum

from src.label_studio.workspace_service import WorkspaceService, WorkspaceNotFoundError
from src.label_studio.rbac_service import RBACService, Permission, PermissionDeniedError, NotAMemberError
from src.label_studio.metadata_codec import (
    MetadataCodec,
    WorkspaceMetadata,
    get_metadata_codec,
    MetadataDecodeError,
)
from src.label_studio.workspace_models import LabelStudioWorkspaceModel

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_TIMEOUT = 60.0  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds


class HTTPMethod(str, Enum):
    """HTTP method enumeration."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


# ============================================================================
# Exceptions
# ============================================================================

class ProxyError(Exception):
    """Base exception for proxy errors."""
    pass


class LabelStudioConnectionError(ProxyError):
    """Exception raised when connection to Label Studio fails."""
    pass


class LabelStudioAPIError(ProxyError):
    """Exception raised when Label Studio returns an error."""

    def __init__(self, status_code: int, detail: str, response_body: Optional[Dict] = None):
        self.status_code = status_code
        self.detail = detail
        self.response_body = response_body
        super().__init__(f"Label Studio API error ({status_code}): {detail}")


class ProxyPermissionError(ProxyError):
    """Exception raised when user lacks permission."""

    def __init__(self, user_id: UUID, permission: Permission, workspace_id: UUID):
        self.user_id = user_id
        self.permission = permission
        self.workspace_id = workspace_id
        super().__init__(
            f"User '{user_id}' lacks permission '{permission.value}' "
            f"in workspace '{workspace_id}'"
        )


# ============================================================================
# Proxy Response
# ============================================================================

class ProxyResponse:
    """Response wrapper for proxy requests."""

    def __init__(
        self,
        status_code: int,
        body: Any,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "body": self.body,
            "headers": self.headers,
        }


# ============================================================================
# Label Studio Proxy
# ============================================================================

class LabelStudioProxy:
    """
    Proxy for Label Studio API requests.

    Intercepts requests to Label Studio and adds workspace-aware functionality:
    - Permission verification before forwarding
    - Metadata injection on project creation
    - Metadata extraction on project retrieval
    - Audit logging

    Example Usage:
        proxy = LabelStudioProxy(
            label_studio_url="http://localhost:8080",
            api_token="your-token",
            workspace_service=workspace_service,
            rbac_service=rbac_service
        )

        # Forward a request with permission checking
        response = await proxy.proxy_request(
            method="GET",
            path="/api/projects",
            user_id=user_uuid,
            workspace_id=workspace_uuid
        )
    """

    def __init__(
        self,
        label_studio_url: str,
        api_token: str,
        workspace_service: WorkspaceService,
        rbac_service: RBACService,
        timeout: float = DEFAULT_TIMEOUT,
        metadata_codec: Optional[MetadataCodec] = None,
    ):
        """
        Initialize LabelStudioProxy.

        Args:
            label_studio_url: Base URL for Label Studio (e.g., "http://localhost:8080")
            api_token: Label Studio API token for authentication
            workspace_service: WorkspaceService instance for workspace operations
            rbac_service: RBACService instance for permission checking
            timeout: Request timeout in seconds (default: 60)
            metadata_codec: Optional MetadataCodec instance (default: singleton)
        """
        self.label_studio_url = label_studio_url.rstrip("/")
        self.api_token = api_token
        self.workspace_service = workspace_service
        self.rbac_service = rbac_service
        self.timeout = timeout
        self.metadata_codec = metadata_codec or get_metadata_codec()

        # HTTP client (created lazily)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.label_studio_url,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Token {self.api_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def proxy_request(
        self,
        method: str,
        path: str,
        user_id: UUID,
        workspace_id: Optional[UUID] = None,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        skip_permission_check: bool = False,
    ) -> ProxyResponse:
        """
        Proxy a request to Label Studio.

        This method:
        1. Verifies user permissions (if workspace_id provided)
        2. Preprocesses the request (e.g., inject metadata)
        3. Forwards the request to Label Studio
        4. Postprocesses the response (e.g., extract metadata)
        5. Logs the operation

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: API path (e.g., "/api/projects")
            user_id: User making the request
            workspace_id: Optional workspace context for permission checking
            body: Optional request body (for POST/PUT/PATCH)
            params: Optional query parameters
            skip_permission_check: Skip permission verification (for internal use)

        Returns:
            ProxyResponse with status code and body

        Raises:
            ProxyPermissionError: If user lacks required permission
            LabelStudioConnectionError: If connection fails
            LabelStudioAPIError: If Label Studio returns an error
        """
        method = method.upper()
        logger.info(f"Proxying {method} {path} for user {user_id}")

        # Step 1: Verify permissions
        if workspace_id and not skip_permission_check:
            await self._verify_permissions(user_id, workspace_id, method, path)

        # Step 2: Preprocess request
        processed_body = await self._preprocess_request(
            method, path, body, user_id, workspace_id
        )

        # Step 3: Forward request to Label Studio
        response = await self._forward_request(method, path, processed_body, params)

        # Step 4: Postprocess response
        processed_response = await self._postprocess_response(
            method, path, response, workspace_id
        )

        # Step 5: Log operation
        self._log_operation(user_id, workspace_id, method, path, processed_response.status_code)

        return processed_response

    async def _verify_permissions(
        self,
        user_id: UUID,
        workspace_id: UUID,
        method: str,
        path: str,
    ) -> None:
        """
        Verify user has required permissions for the request.

        Args:
            user_id: User making the request
            workspace_id: Workspace context
            method: HTTP method
            path: API path

        Raises:
            ProxyPermissionError: If permission denied
        """
        required_permission = self._get_required_permission(method, path)

        if required_permission is None:
            # No permission required for this endpoint
            return

        try:
            self.rbac_service.require_permission(user_id, workspace_id, required_permission)
        except (PermissionDeniedError, NotAMemberError) as e:
            logger.warning(f"Permission denied for user {user_id}: {e}")
            raise ProxyPermissionError(user_id, required_permission, workspace_id) from e

    def _get_required_permission(
        self,
        method: str,
        path: str,
    ) -> Optional[Permission]:
        """
        Determine required permission based on method and path.

        Args:
            method: HTTP method
            path: API path

        Returns:
            Required permission or None if no permission required
        """
        # Normalize path
        path = path.lower().rstrip("/")

        # Project endpoints
        if "/api/projects" in path:
            if method == "GET":
                return Permission.PROJECT_VIEW
            elif method == "POST":
                return Permission.PROJECT_CREATE
            elif method in ("PUT", "PATCH"):
                return Permission.PROJECT_EDIT
            elif method == "DELETE":
                return Permission.PROJECT_DELETE

        # Task endpoints
        if "/api/tasks" in path:
            if method == "GET":
                return Permission.TASK_VIEW
            elif method == "POST":
                return Permission.TASK_ANNOTATE
            elif method in ("PUT", "PATCH"):
                return Permission.TASK_ANNOTATE
            elif method == "DELETE":
                return Permission.PROJECT_EDIT

        # Annotation endpoints
        if "/api/annotations" in path:
            if method == "GET":
                return Permission.TASK_VIEW
            elif method == "POST":
                return Permission.TASK_ANNOTATE
            elif method in ("PUT", "PATCH"):
                return Permission.TASK_ANNOTATE
            elif method == "DELETE":
                return Permission.TASK_REVIEW

        # Export endpoints
        if "/export" in path:
            return Permission.DATA_EXPORT

        # Import endpoints
        if "/import" in path:
            return Permission.DATA_IMPORT

        # Default: require view permission
        return Permission.PROJECT_VIEW

    async def _preprocess_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]],
        user_id: UUID,
        workspace_id: Optional[UUID],
    ) -> Optional[Dict[str, Any]]:
        """
        Preprocess request before forwarding.

        Handles:
        - Metadata injection for project creation

        Args:
            method: HTTP method
            path: API path
            body: Request body
            user_id: User making the request
            workspace_id: Workspace context

        Returns:
            Processed body (may be modified)
        """
        if body is None:
            return None

        # Inject metadata on project creation
        if method == "POST" and "/api/projects" in path.lower() and workspace_id:
            return await self._inject_metadata(body, user_id, workspace_id)

        return body

    async def _inject_metadata(
        self,
        body: Dict[str, Any],
        user_id: UUID,
        workspace_id: UUID,
    ) -> Dict[str, Any]:
        """
        Inject workspace metadata into project description.

        Args:
            body: Request body with project data
            user_id: User creating the project
            workspace_id: Workspace context

        Returns:
            Body with metadata injected into description
        """
        try:
            # Get workspace info
            workspace = self.workspace_service.get_workspace(workspace_id)
            if not workspace:
                logger.warning(f"Workspace {workspace_id} not found, skipping metadata injection")
                return body

            # Get original description
            original_description = body.get("description", "") or ""

            # Create metadata
            metadata = WorkspaceMetadata(
                workspace_id=str(workspace_id),
                workspace_name=workspace.name,
                created_by=str(user_id),
                created_at=datetime.utcnow().isoformat(),
            )

            # Encode metadata into description
            encoded_description = self.metadata_codec.encode(original_description, metadata)

            # Update body
            body = body.copy()
            body["description"] = encoded_description

            logger.info(f"Injected metadata for workspace '{workspace.name}' into project")
            return body

        except Exception as e:
            logger.error(f"Failed to inject metadata: {e}")
            return body  # Return original body on error

    async def _forward_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
    ) -> httpx.Response:
        """
        Forward request to Label Studio.

        Args:
            method: HTTP method
            path: API path
            body: Request body
            params: Query parameters

        Returns:
            httpx Response object

        Raises:
            LabelStudioConnectionError: If connection fails
        """
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=path,
                json=body,
                params=params,
            )
            return response

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Label Studio: {e}")
            raise LabelStudioConnectionError(
                f"Failed to connect to Label Studio at {self.label_studio_url}"
            ) from e

        except httpx.TimeoutException as e:
            logger.error(f"Request to Label Studio timed out: {e}")
            raise LabelStudioConnectionError(
                f"Request to Label Studio timed out after {self.timeout}s"
            ) from e

        except httpx.HTTPError as e:
            logger.error(f"HTTP error communicating with Label Studio: {e}")
            raise LabelStudioConnectionError(
                f"HTTP error: {e}"
            ) from e

    async def _postprocess_response(
        self,
        method: str,
        path: str,
        response: httpx.Response,
        workspace_id: Optional[UUID],
    ) -> ProxyResponse:
        """
        Postprocess response from Label Studio.

        Handles:
        - Metadata extraction from project responses
        - Error handling

        Args:
            method: HTTP method
            path: API path
            response: Raw response from Label Studio
            workspace_id: Workspace context

        Returns:
            Processed ProxyResponse
        """
        # Parse response body
        try:
            body = response.json()
        except Exception:
            body = response.text

        # Handle errors
        if response.status_code >= 400:
            detail = body.get("detail", str(body)) if isinstance(body, dict) else str(body)
            logger.warning(f"Label Studio returned error {response.status_code}: {detail}")
            return ProxyResponse(
                status_code=response.status_code,
                body=body,
                headers=dict(response.headers),
            )

        # Extract metadata from project responses
        if method == "GET" and "/api/projects" in path.lower() and isinstance(body, (dict, list)):
            body = await self._extract_metadata(body)

        return ProxyResponse(
            status_code=response.status_code,
            body=body,
            headers=dict(response.headers),
        )

    async def _extract_metadata(
        self,
        body: Union[Dict[str, Any], List[Dict[str, Any]]],
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extract workspace metadata from project response(s).

        Args:
            body: Response body (single project or list)

        Returns:
            Body with metadata extracted and workspace info added
        """
        if isinstance(body, list):
            # List of projects
            return [await self._enhance_project(p) for p in body]
        elif isinstance(body, dict):
            # Check if it's a paginated response
            if "results" in body and isinstance(body["results"], list):
                body = body.copy()
                body["results"] = [await self._enhance_project(p) for p in body["results"]]
                return body
            else:
                # Single project
                return await self._enhance_project(body)
        return body

    async def _enhance_project(
        self,
        project: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enhance project with workspace information.

        Extracts metadata from description and adds workspace field.

        Args:
            project: Project data dictionary

        Returns:
            Enhanced project with workspace info
        """
        if not isinstance(project, dict):
            return project

        description = project.get("description", "")
        if not description or not self.metadata_codec.has_metadata(description):
            return project

        try:
            # Decode metadata
            original_description, metadata = self.metadata_codec.decode(description)

            # Create enhanced project
            enhanced = project.copy()
            enhanced["description"] = original_description

            if metadata:
                # Add workspace info
                enhanced["workspace"] = {
                    "id": metadata.workspace_id,
                    "name": metadata.workspace_name,
                    "created_by": metadata.created_by,
                    "created_at": metadata.created_at,
                }

                # Try to get full workspace info
                try:
                    workspace_uuid = UUID(metadata.workspace_id)
                    workspace = self.workspace_service.get_workspace(workspace_uuid)
                    if workspace:
                        enhanced["workspace"]["owner_id"] = str(workspace.owner_id)
                        enhanced["workspace"]["is_active"] = workspace.is_active
                except (ValueError, WorkspaceNotFoundError):
                    pass

            return enhanced

        except MetadataDecodeError as e:
            logger.warning(f"Failed to decode metadata from project: {e}")
            return project

    def _log_operation(
        self,
        user_id: UUID,
        workspace_id: Optional[UUID],
        method: str,
        path: str,
        status_code: int,
    ) -> None:
        """
        Log proxy operation for audit.

        Args:
            user_id: User who made the request
            workspace_id: Workspace context
            method: HTTP method
            path: API path
            status_code: Response status code
        """
        log_data = {
            "user_id": str(user_id),
            "workspace_id": str(workspace_id) if workspace_id else None,
            "method": method,
            "path": path,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if status_code >= 400:
            logger.warning(f"Proxy operation failed: {log_data}")
        else:
            logger.info(f"Proxy operation completed: {log_data}")

    # ========== Convenience Methods ==========

    async def get_projects(
        self,
        user_id: UUID,
        workspace_id: Optional[UUID] = None,
    ) -> ProxyResponse:
        """
        Get list of projects.

        Args:
            user_id: User making the request
            workspace_id: Optional workspace filter

        Returns:
            ProxyResponse with projects list
        """
        return await self.proxy_request(
            method="GET",
            path="/api/projects",
            user_id=user_id,
            workspace_id=workspace_id,
        )

    async def get_project(
        self,
        project_id: int,
        user_id: UUID,
        workspace_id: Optional[UUID] = None,
    ) -> ProxyResponse:
        """
        Get single project by ID.

        Args:
            project_id: Label Studio project ID
            user_id: User making the request
            workspace_id: Optional workspace context

        Returns:
            ProxyResponse with project data
        """
        return await self.proxy_request(
            method="GET",
            path=f"/api/projects/{project_id}",
            user_id=user_id,
            workspace_id=workspace_id,
        )

    async def create_project(
        self,
        project_data: Dict[str, Any],
        user_id: UUID,
        workspace_id: UUID,
    ) -> ProxyResponse:
        """
        Create a new project in workspace.

        Args:
            project_data: Project creation data
            user_id: User creating the project
            workspace_id: Target workspace

        Returns:
            ProxyResponse with created project
        """
        return await self.proxy_request(
            method="POST",
            path="/api/projects",
            user_id=user_id,
            workspace_id=workspace_id,
            body=project_data,
        )

    async def update_project(
        self,
        project_id: int,
        project_data: Dict[str, Any],
        user_id: UUID,
        workspace_id: Optional[UUID] = None,
    ) -> ProxyResponse:
        """
        Update an existing project.

        Args:
            project_id: Label Studio project ID
            project_data: Update data
            user_id: User making the update
            workspace_id: Optional workspace context

        Returns:
            ProxyResponse with updated project
        """
        return await self.proxy_request(
            method="PATCH",
            path=f"/api/projects/{project_id}",
            user_id=user_id,
            workspace_id=workspace_id,
            body=project_data,
        )

    async def delete_project(
        self,
        project_id: int,
        user_id: UUID,
        workspace_id: Optional[UUID] = None,
    ) -> ProxyResponse:
        """
        Delete a project.

        Args:
            project_id: Label Studio project ID
            user_id: User making the deletion
            workspace_id: Optional workspace context

        Returns:
            ProxyResponse
        """
        return await self.proxy_request(
            method="DELETE",
            path=f"/api/projects/{project_id}",
            user_id=user_id,
            workspace_id=workspace_id,
        )


# ============================================================================
# Factory Function
# ============================================================================

def create_label_studio_proxy(
    label_studio_url: str,
    api_token: str,
    workspace_service: WorkspaceService,
    rbac_service: RBACService,
    **kwargs,
) -> LabelStudioProxy:
    """
    Factory function to create LabelStudioProxy.

    Args:
        label_studio_url: Label Studio base URL
        api_token: API authentication token
        workspace_service: WorkspaceService instance
        rbac_service: RBACService instance
        **kwargs: Additional arguments for LabelStudioProxy

    Returns:
        Configured LabelStudioProxy instance
    """
    return LabelStudioProxy(
        label_studio_url=label_studio_url,
        api_token=api_token,
        workspace_service=workspace_service,
        rbac_service=rbac_service,
        **kwargs,
    )
