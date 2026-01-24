"""
WebSocket Authentication Middleware

Provides authentication and authorization for WebSocket connections.
Validates JWT tokens and enforces permissions before establishing connections.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import WebSocket, WebSocketException, status
from jose import jwt, JWTError

logger = logging.getLogger(__name__)


class WebSocketAuthError(Exception):
    """Base exception for WebSocket authentication errors."""

    def __init__(self, code: int, reason: str):
        self.code = code
        self.reason = reason
        super().__init__(reason)


class WebSocketAuthenticator:
    """
    Authenticates WebSocket connections using JWT tokens.

    Usage:
        authenticator = WebSocketAuthenticator(secret_key="your-secret")
        user_id, user_data = await authenticator.authenticate(websocket)
    """

    def __init__(
        self,
        secret_key: str = "your-secret-key-here",  # TODO: Load from config
        algorithm: str = "HS256",
        token_query_param: str = "token",
    ):
        """
        Initialize WebSocket authenticator.

        Args:
            secret_key: JWT secret key for token verification
            algorithm: JWT algorithm (default: HS256)
            token_query_param: Query parameter name for token (default: "token")
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_query_param = token_query_param

    async def authenticate(
        self,
        websocket: WebSocket,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Authenticate WebSocket connection.

        Args:
            websocket: WebSocket connection to authenticate

        Returns:
            Tuple of (user_id, user_data) if authentication succeeds

        Raises:
            WebSocketAuthError: If authentication fails
        """
        # Extract token from query parameters
        token = websocket.query_params.get(self.token_query_param)

        if not token:
            raise WebSocketAuthError(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Missing authentication token"
            )

        try:
            # Verify and decode JWT token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # Extract user information
            user_id = payload.get("sub")
            if not user_id:
                raise WebSocketAuthError(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Invalid token: missing user ID"
                )

            # Check token expiration
            exp = payload.get("exp")
            if exp:
                exp_datetime = datetime.fromtimestamp(exp)
                if exp_datetime < datetime.utcnow():
                    raise WebSocketAuthError(
                        code=status.WS_1008_POLICY_VIOLATION,
                        reason="Token expired"
                    )

            # Extract additional user data
            user_data = {
                "user_id": user_id,
                "username": payload.get("username"),
                "email": payload.get("email"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
            }

            logger.info(f"WebSocket authenticated: user_id={user_id}")
            return user_id, user_data

        except JWTError as e:
            logger.warning(f"WebSocket JWT verification failed: {e}")
            raise WebSocketAuthError(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            raise WebSocketAuthError(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="Authentication failed"
            )

    async def authenticate_with_fallback(
        self,
        websocket: WebSocket,
        allow_anonymous: bool = False,
    ) -> tuple[Optional[str], Dict[str, Any]]:
        """
        Authenticate WebSocket with optional anonymous fallback.

        Args:
            websocket: WebSocket connection
            allow_anonymous: If True, allows anonymous connections

        Returns:
            Tuple of (user_id, user_data). user_id is None for anonymous.
        """
        try:
            return await self.authenticate(websocket)
        except WebSocketAuthError as e:
            if allow_anonymous:
                logger.info("WebSocket connecting anonymously")
                return None, {"user_id": None, "anonymous": True}
            raise


class WebSocketAuthorizer:
    """
    Authorizes WebSocket connections based on permissions and resources.

    Usage:
        authorizer = WebSocketAuthorizer()
        authorizer.check_project_access(user_data, project_id)
    """

    def check_permission(
        self,
        user_data: Dict[str, Any],
        required_permission: str,
    ) -> bool:
        """
        Check if user has required permission.

        Args:
            user_data: User data from authentication
            required_permission: Permission to check (e.g., "annotation.view")

        Returns:
            True if user has permission
        """
        permissions = user_data.get("permissions", [])
        roles = user_data.get("roles", [])

        # Check explicit permission
        if required_permission in permissions:
            return True

        # Check admin role (has all permissions)
        if "admin" in roles:
            return True

        return False

    def check_project_access(
        self,
        user_data: Dict[str, Any],
        project_id: str,
        required_permission: str = "project.view",
    ) -> bool:
        """
        Check if user has access to specific project.

        Args:
            user_data: User data from authentication
            project_id: Project ID to check access for
            required_permission: Permission required for access

        Returns:
            True if user has access

        Raises:
            WebSocketAuthError: If access denied
        """
        # TODO: Implement actual project-level permission checking
        # This would query the database to check project membership

        # For now, check basic permission
        if not self.check_permission(user_data, required_permission):
            raise WebSocketAuthError(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=f"Access denied: missing {required_permission} permission"
            )

        logger.debug(
            f"User {user_data.get('user_id')} authorized for project {project_id}"
        )
        return True

    def check_task_access(
        self,
        user_data: Dict[str, Any],
        task_id: int,
        required_permission: str = "annotation.view",
    ) -> bool:
        """
        Check if user has access to specific task.

        Args:
            user_data: User data from authentication
            task_id: Task ID to check access for
            required_permission: Permission required for access

        Returns:
            True if user has access

        Raises:
            WebSocketAuthError: If access denied
        """
        # TODO: Implement actual task-level permission checking
        # This would query the database to check task assignment

        if not self.check_permission(user_data, required_permission):
            raise WebSocketAuthError(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=f"Access denied: missing {required_permission} permission"
            )

        logger.debug(
            f"User {user_data.get('user_id')} authorized for task {task_id}"
        )
        return True


# Global instances (can be configured per application)
_default_authenticator: Optional[WebSocketAuthenticator] = None
_default_authorizer: Optional[WebSocketAuthorizer] = None


def get_ws_authenticator() -> WebSocketAuthenticator:
    """Get default WebSocket authenticator instance."""
    global _default_authenticator
    if _default_authenticator is None:
        _default_authenticator = WebSocketAuthenticator()
    return _default_authenticator


def get_ws_authorizer() -> WebSocketAuthorizer:
    """Get default WebSocket authorizer instance."""
    global _default_authorizer
    if _default_authorizer is None:
        _default_authorizer = WebSocketAuthorizer()
    return _default_authorizer


async def authenticate_websocket(
    websocket: WebSocket,
    allow_anonymous: bool = False,
) -> tuple[Optional[str], Dict[str, Any]]:
    """
    Convenience function to authenticate WebSocket connection.

    Args:
        websocket: WebSocket connection
        allow_anonymous: If True, allows anonymous connections

    Returns:
        Tuple of (user_id, user_data)

    Raises:
        WebSocketAuthError: If authentication fails and anonymous not allowed
    """
    authenticator = get_ws_authenticator()
    return await authenticator.authenticate_with_fallback(
        websocket,
        allow_anonymous=allow_anonymous
    )


async def authorize_project_access(
    user_data: Dict[str, Any],
    project_id: str,
    required_permission: str = "project.view",
) -> bool:
    """
    Convenience function to check project access.

    Args:
        user_data: User data from authentication
        project_id: Project ID to check
        required_permission: Permission required

    Returns:
        True if authorized

    Raises:
        WebSocketAuthError: If not authorized
    """
    authorizer = get_ws_authorizer()
    return authorizer.check_project_access(
        user_data,
        project_id,
        required_permission
    )
