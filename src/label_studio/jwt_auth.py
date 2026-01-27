"""
Label Studio JWT Authentication Module.

Provides JWT-based authentication support for Label Studio 1.22.0+.
This module manages JWT tokens (access and refresh) for authenticating
with Label Studio's /api/sessions/ endpoint.

Key Features:
- Username/password authentication via /api/sessions/
- Automatic token refresh via /api/sessions/refresh/
- Thread-safe token management using asyncio.Lock()
- Token expiration detection via JWT exp claim
- Secure token storage (in-memory only)

CRITICAL: Uses asyncio.Lock() for thread safety, NOT threading.Lock()
         threading.Lock() causes deadlocks in async context.

Validates: Requirements 1.1, 1.2, 4.3, 10.1
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
import jwt

from src.label_studio.exceptions import LabelStudioAuthenticationError

logger = logging.getLogger(__name__)


@dataclass
class JWTTokenResponse:
    """
    Response from Label Studio JWT authentication.
    
    This dataclass represents the token response from Label Studio's
    /api/sessions/ and /api/sessions/refresh/ endpoints.
    
    Attributes:
        access_token: Short-lived JWT token for API authentication
        refresh_token: Long-lived JWT token for obtaining new access tokens
        token_type: Token type, typically "Bearer"
        expires_in: Optional seconds until access token expiration
        
    Validates: Requirements 1.2 - Store both access token and refresh token
    """
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JWTTokenResponse':
        """
        Create JWTTokenResponse from API response dictionary.
        
        Args:
            data: Dictionary from Label Studio API response containing:
                - access_token (required): The JWT access token
                - refresh_token (required): The JWT refresh token
                - token_type (optional): Token type, defaults to "Bearer"
                - expires_in (optional): Seconds until expiration
                
        Returns:
            JWTTokenResponse: Parsed token response
            
        Raises:
            KeyError: If required fields are missing
        """
        return cls(
            access_token=data['access_token'],
            refresh_token=data['refresh_token'],
            token_type=data.get('token_type', 'Bearer'),
            expires_in=data.get('expires_in')
        )


class JWTAuthManager:
    """
    Manages JWT authentication for Label Studio.
    
    This class handles all aspects of JWT-based authentication with Label Studio:
    - Authenticate with username/password via /api/sessions/
    - Store access and refresh tokens in memory (security requirement)
    - Refresh expired access tokens via /api/sessions/refresh/
    - Provide thread-safe token access using asyncio.Lock()
    - Detect token expiration by parsing JWT exp claim
    
    CRITICAL: This class uses asyncio.Lock() for thread safety.
              DO NOT use threading.Lock() as it causes deadlocks in async context.
    
    Attributes:
        base_url: Label Studio base URL (without trailing slash)
        username: Username for authentication (optional, can be set later)
        password: Password for authentication (optional, can be set later)
        
    Security Notes:
        - Tokens are stored in memory only (not persisted)
        - Tokens and passwords are NEVER logged
        - Old tokens are cleared when refreshed
        
    Validates: Requirements 1.1, 1.2, 4.3, 10.1
    
    Example:
        >>> auth_manager = JWTAuthManager(
        ...     base_url="http://label-studio:8080",
        ...     username="admin",
        ...     password="secret"
        ... )
        >>> await auth_manager.login()
        >>> headers = auth_manager.get_auth_header()
        >>> # headers = {'Authorization': 'Bearer <token>'}
    """
    
    # Buffer time before token expiration to trigger refresh (seconds)
    REFRESH_BUFFER_SECONDS = 60
    
    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize JWT auth manager.
        
        Args:
            base_url: Label Studio base URL (e.g., "http://label-studio:8080")
            username: Username for authentication (optional)
            password: Password for authentication (optional)
            
        Note:
            Username and password can be provided later before calling login().
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        
        # Token storage (in-memory only - security requirement)
        # NEVER persist tokens to disk, database, or logs
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Thread safety - CRITICAL: Use asyncio.Lock(), NOT threading.Lock()
        # threading.Lock() causes deadlocks in async context
        # Note: Lock is created lazily to avoid event loop issues
        self._lock: Optional[asyncio.Lock] = None
        
        # Authentication state
        self._is_authenticated = False
        
        logger.debug(
            f"JWTAuthManager initialized for {self.base_url} "
            f"(username configured: {username is not None})"
        )
    
    def _get_lock(self) -> asyncio.Lock:
        """
        Get or create the asyncio.Lock for thread-safe operations.
        
        The lock is created lazily to ensure it's created in the correct
        event loop context.
        
        Returns:
            asyncio.Lock: The lock for thread-safe token operations
        """
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
    
    def _parse_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Parse JWT token to extract expiration time.
        
        This method decodes the JWT token WITHOUT verifying the signature
        to extract the 'exp' claim. We don't need to verify the signature
        because we're just checking expiration, not validating authenticity.
        
        Args:
            token: JWT token string
            
        Returns:
            datetime: Token expiration time in UTC, or None if parsing fails
            
        Note:
            This method never logs the token content for security.
            
        Validates: Requirements 8.5 - Parse JWT token to check exp claim
        """
        if not token:
            return None
            
        try:
            # Decode without verification - we just need the exp claim
            # The signature verification is done by Label Studio server
            decoded = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_exp": False,  # We'll check exp ourselves
                    "verify_aud": False,
                    "verify_iss": False,
                }
            )
            
            # Extract exp claim (Unix timestamp)
            exp_timestamp = decoded.get('exp')
            if exp_timestamp is None:
                logger.warning("JWT token missing 'exp' claim")
                return None
            
            # Convert Unix timestamp to datetime
            exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
            
            logger.debug(f"Parsed token expiration: {exp_datetime.isoformat()}")
            return exp_datetime
            
        except jwt.DecodeError as e:
            logger.error(f"Failed to decode JWT token: {e}")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT token format: {e}")
            return None
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing token expiration: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing JWT token: {e}")
            return None
    
    def _is_token_expired(self, buffer_seconds: Optional[int] = None) -> bool:
        """
        Check if access token is expired or will expire soon.
        
        This method checks if the current access token has expired or will
        expire within the buffer period. This allows proactive token refresh
        before the token actually expires, preventing API call failures.
        
        Args:
            buffer_seconds: Refresh token this many seconds before expiration.
                          Defaults to REFRESH_BUFFER_SECONDS (60 seconds).
                          
        Returns:
            bool: True if token is expired or will expire within buffer period,
                  False if token is still valid
                  
        Note:
            Returns True if:
            - No access token is stored
            - No expiration time is known
            - Token has expired
            - Token will expire within buffer_seconds
            
        Validates: Requirements 8.5 - Check token expiration with buffer
        """
        if buffer_seconds is None:
            buffer_seconds = self.REFRESH_BUFFER_SECONDS
            
        # No token means "expired"
        if not self._access_token:
            return True
            
        # No expiration time known - assume expired to be safe
        if not self._token_expires_at:
            logger.debug("Token expiration unknown, treating as expired")
            return True
        
        # Check if token is expired or will expire within buffer
        now = datetime.utcnow()
        buffer = timedelta(seconds=buffer_seconds)
        expires_with_buffer = self._token_expires_at - buffer
        
        is_expired = now >= expires_with_buffer
        
        if is_expired:
            logger.debug(
                f"Token expired or expiring soon "
                f"(expires_at={self._token_expires_at.isoformat()}, "
                f"buffer={buffer_seconds}s)"
            )
        
        return is_expired
    
    def get_auth_header(self) -> Dict[str, str]:
        """
        Get authentication header for API requests.
        
        Returns the Authorization header with Bearer token format
        for use in HTTP requests to Label Studio API.
        
        Returns:
            Dict[str, str]: Dictionary with Authorization header.
                           Returns empty dict if not authenticated.
                           
        Example:
            >>> headers = auth_manager.get_auth_header()
            >>> # {'Authorization': 'Bearer eyJ...'}
            
        Note:
            This method does NOT check token expiration. Use
            _ensure_authenticated() before making API calls to
            ensure the token is valid.
            
        Validates: Requirements 1.4 - Use Bearer token format
        """
        if not self._access_token:
            logger.warning("get_auth_header called but no access token available")
            return {}
            
        return {
            'Authorization': f'Bearer {self._access_token}'
        }
    
    def get_auth_state(self) -> Dict[str, Any]:
        """
        Get authentication state for safe logging.
        
        Returns a dictionary representation of the current authentication
        state WITHOUT including sensitive data (tokens, passwords).
        This is safe to log and useful for debugging.
        
        Returns:
            Dict[str, Any]: Authentication state containing:
                - is_authenticated: Whether currently authenticated
                - has_access_token: Whether access token is stored
                - has_refresh_token: Whether refresh token is stored
                - token_expires_at: ISO datetime of token expiration (or None)
                - is_token_expired: Whether token is currently expired
                - base_url: Label Studio base URL
                - has_credentials: Whether username/password are configured
                
        Note:
            This method NEVER includes tokens or passwords in the output.
            It is safe to log the returned dictionary.
            
        Validates: Requirements 10.2 - Never log tokens or passwords
        
        Example:
            >>> state = auth_manager.get_auth_state()
            >>> logger.info(f"Auth state: {state}")
            # Safe to log - no sensitive data
        """
        return {
            "is_authenticated": self._is_authenticated,
            "has_access_token": self._access_token is not None,
            "has_refresh_token": self._refresh_token is not None,
            "token_expires_at": (
                self._token_expires_at.isoformat() 
                if self._token_expires_at else None
            ),
            "is_token_expired": self._is_token_expired(),
            "base_url": self.base_url,
            "has_credentials": (
                self.username is not None and self.password is not None
            ),
        }
    
    @property
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.
        
        Returns True if the auth manager has successfully authenticated
        and has a valid access token stored.
        
        Returns:
            bool: True if authenticated with valid token, False otherwise
            
        Note:
            This property does NOT check token expiration. A True value
            means we have a token, but it may be expired. Use
            _is_token_expired() to check expiration.
        """
        return self._is_authenticated and self._access_token is not None
    
    def clear_tokens(self) -> None:
        """
        Clear all stored tokens from memory.
        
        This method securely clears all token data from memory.
        It should be called when:
        - Authentication fails
        - User logs out
        - Tokens are replaced with new ones
        
        Note:
            This method is synchronous and does not require the lock
            because it only sets values to None.
            
        Validates: Requirements 10.4 - Clear tokens from memory
        """
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._is_authenticated = False
        
        logger.debug("Cleared all JWT tokens from memory")
    
    def set_credentials(self, username: str, password: str) -> None:
        """
        Set authentication credentials.
        
        This method allows setting or updating the username and password
        after the JWTAuthManager has been initialized.
        
        Args:
            username: Label Studio username
            password: Label Studio password
            
        Note:
            Setting new credentials does NOT automatically re-authenticate.
            Call login() after setting credentials to authenticate.
        """
        self.username = username
        self.password = password
        
        logger.debug("JWT authentication credentials updated")
    
    def has_credentials(self) -> bool:
        """
        Check if authentication credentials are configured.
        
        Returns:
            bool: True if both username and password are set
        """
        return self.username is not None and self.password is not None
    
    async def _ensure_authenticated(self) -> None:
        """
        Ensure valid authentication before API calls.
        
        This method checks if the current access token is valid and refreshes
        it if needed. It uses asyncio.Lock() to ensure thread-safe token
        refresh - only one refresh operation will execute even if multiple
        concurrent API calls trigger refresh.
        
        The method performs the following checks:
        1. If not authenticated at all, perform initial login
        2. If token is expired or expiring soon, refresh the token
        3. If refresh fails, fall back to re-authentication
        
        This method should be called before every API request to ensure
        the request will use a valid token.
        
        Raises:
            LabelStudioAuthenticationError: If authentication fails and
                cannot be recovered
            ValueError: If credentials are not configured
            
        Note:
            - Uses asyncio.Lock() for thread safety (NOT threading.Lock())
            - Only one refresh operation executes for concurrent calls
            - Waiting calls will use the refreshed token
            
        Validates: Requirements 2.5, 4.1, 4.2
        
        Example:
            >>> # Before making an API call
            >>> await auth_manager._ensure_authenticated()
            >>> headers = auth_manager.get_auth_header()
            >>> # Now make the API call with valid headers
        """
        # Fast path: if token is valid, no lock needed
        if self._is_authenticated and not self._is_token_expired():
            logger.debug("[Label Studio] Token is valid, no refresh needed")
            return
        
        # Acquire lock for token refresh/login
        # This ensures only one refresh operation executes for concurrent calls
        async with self._get_lock():
            # Double-check after acquiring lock (another coroutine may have refreshed)
            if self._is_authenticated and not self._is_token_expired():
                logger.debug(
                    "[Label Studio] Token was refreshed by another coroutine"
                )
                return
            
            # Check if we need initial authentication or token refresh
            if not self._is_authenticated or not self._access_token:
                # Not authenticated at all - perform initial login
                logger.info("[Label Studio] Not authenticated, performing login")
                await self.login()
            else:
                # Token is expired or expiring soon - refresh it
                logger.info(
                    "[Label Studio] Token expired or expiring soon, refreshing"
                )
                await self.refresh_token()
    
    async def refresh_token(self) -> bool:
        """
        Refresh access token using refresh token.
        
        Makes POST request to /api/sessions/refresh/ endpoint with the
        current refresh token. Updates access_token and refresh_token
        in memory on success. Falls back to login() if refresh token
        is expired.
        
        The Label Studio API expects the following JSON body:
        {
            "refresh": "<refresh_token>"
        }
        
        Returns:
            bool: True if refresh successful
            
        Raises:
            LabelStudioAuthenticationError: If refresh and re-auth both fail
            
        Note:
            - This method does NOT log tokens (security requirement)
            - Old tokens are cleared before storing new ones
            - Falls back to login() if refresh token is expired (401)
            - On success, updates _token_expires_at from new access token
            
        Validates: Requirements 2.1, 2.2, 2.3, 2.4, 9.3, 9.4, 10.2, 10.4
        
        Example:
            >>> # Assuming auth_manager is already authenticated
            >>> success = await auth_manager.refresh_token()
            >>> if success:
            ...     print("Token refreshed successfully")
        """
        # Check if we have a refresh token
        if not self._refresh_token:
            logger.warning(
                "[Label Studio] No refresh token available, falling back to login"
            )
            return await self.login()
        
        # Build the refresh URL
        refresh_url = f"{self.base_url}/api/sessions/refresh/"
        
        # Build request payload
        payload = {
            "refresh": self._refresh_token
        }
        
        logger.info("[Label Studio] Refreshing access token")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    refresh_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                # Handle refresh token expired (401) - fall back to login
                if response.status_code == 401:
                    logger.warning(
                        "[Label Studio] Refresh token expired, falling back to login"
                    )
                    # Clear old tokens before re-authenticating
                    self.clear_tokens()
                    return await self.login()
                
                # Handle forbidden (403) - cannot recover
                if response.status_code == 403:
                    # Try to extract server reason from response
                    server_reason = None
                    try:
                        error_data = response.json()
                        server_reason = error_data.get('detail') or error_data.get('message') or error_data.get('error')
                        # Sanitize: don't include if it might contain sensitive data
                        if server_reason and any(word in str(server_reason).lower() for word in ['password', 'token', 'secret', 'key']):
                            server_reason = None
                    except Exception:
                        pass
                    
                    error = LabelStudioAuthenticationError.create(
                        status_code=403,
                        error_type='insufficient_permissions',
                        server_reason=server_reason
                    )
                    logger.error(
                        f"[Label Studio] Token refresh failed: {error.message} "
                        f"(status_code=403)"
                    )
                    self.clear_tokens()
                    raise error
                
                # Handle other non-success status codes
                if response.status_code not in (200, 201):
                    error_msg = f"Unexpected response from Label Studio: HTTP {response.status_code}"
                    logger.error(f"[Label Studio] Token refresh failed: {error_msg}")
                    # Try to fall back to login for unexpected errors
                    logger.warning(
                        "[Label Studio] Attempting to re-authenticate after refresh failure"
                    )
                    self.clear_tokens()
                    return await self.login()
                
                # Parse response JSON
                try:
                    response_data = response.json()
                except Exception as e:
                    error_msg = f"Failed to parse refresh response: {e}"
                    logger.error(f"[Label Studio] {error_msg}")
                    # Try to fall back to login
                    self.clear_tokens()
                    return await self.login()
                
                # Extract tokens from response
                new_access_token = response_data.get('access_token')
                new_refresh_token = response_data.get('refresh_token')
                
                if not new_access_token:
                    error_msg = "Refresh response missing access_token"
                    logger.error(f"[Label Studio] {error_msg}")
                    # Try to fall back to login
                    self.clear_tokens()
                    return await self.login()
                
                if not new_refresh_token:
                    error_msg = "Refresh response missing refresh_token"
                    logger.error(f"[Label Studio] {error_msg}")
                    # Try to fall back to login
                    self.clear_tokens()
                    return await self.login()
                
                # Clear old tokens before storing new ones (security requirement)
                old_expires_at = self._token_expires_at
                self._access_token = None
                self._refresh_token = None
                self._token_expires_at = None
                
                # Store new tokens in memory
                self._access_token = new_access_token
                self._refresh_token = new_refresh_token
                
                # Parse new token expiration from JWT
                self._token_expires_at = self._parse_token_expiration(new_access_token)
                
                # Ensure we're still marked as authenticated
                self._is_authenticated = True
                
                # Log success WITHOUT logging tokens (security requirement)
                logger.info(
                    f"[Label Studio] Token refresh successful "
                    f"(new_expires_at={self._token_expires_at.isoformat() if self._token_expires_at else 'unknown'})"
                )
                
                return True
                
        except LabelStudioAuthenticationError:
            # Re-raise authentication errors as-is
            raise
        except httpx.TimeoutException as e:
            error_msg = f"Token refresh request timed out: {e}"
            logger.error(f"[Label Studio] {error_msg}")
            # Let network errors propagate for retry handling
            raise
        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to Label Studio for token refresh: {e}"
            logger.error(f"[Label Studio] {error_msg}")
            # Let network errors propagate for retry handling
            raise
        except httpx.HTTPError as e:
            error_msg = f"HTTP error during token refresh: {e}"
            logger.error(f"[Label Studio] {error_msg}")
            # Let network errors propagate for retry handling
            raise
        except Exception as e:
            error_msg = f"Unexpected error during token refresh: {e}"
            logger.error(f"[Label Studio] {error_msg}")
            raise

    async def login(self) -> bool:
        """
        Authenticate with Label Studio using username/password.
        
        Makes POST request to /api/sessions/ endpoint with credentials.
        Stores access_token and refresh_token in memory.
        
        The Label Studio API expects the following JSON body:
        {
            "email": "<username>",
            "password": "<password>"
        }
        
        Note: Label Studio uses "email" field for the username.
        
        Returns:
            bool: True if authentication successful
            
        Raises:
            LabelStudioAuthenticationError: If authentication fails (401/403)
            ValueError: If username or password is not configured
            
        Note:
            - This method does NOT log tokens or passwords (security requirement)
            - Tokens are stored in memory only (not persisted)
            - On success, sets _is_authenticated = True
            
        Validates: Requirements 1.1, 1.2, 1.3, 9.1, 9.2, 10.2
        
        Example:
            >>> auth_manager = JWTAuthManager(
            ...     base_url="http://label-studio:8080",
            ...     username="admin",
            ...     password="secret"
            ... )
            >>> success = await auth_manager.login()
            >>> if success:
            ...     print("Authenticated successfully")
        """
        # Validate credentials are configured
        if not self.username or not self.password:
            raise ValueError(
                "Label Studio credentials are not configured. "
                "Please set LABEL_STUDIO_USERNAME and LABEL_STUDIO_PASSWORD environment variables, "
                "or call set_credentials(username, password) before attempting to authenticate."
            )
        
        # Build the login URL
        login_url = f"{self.base_url}/api/sessions/"
        
        # Build request payload
        # Note: Label Studio uses "email" field for username
        payload = {
            "email": self.username,
            "password": self.password
        }
        
        logger.info(f"Attempting JWT authentication with Label Studio at {self.base_url}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    login_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                # Handle authentication errors (401/403)
                if response.status_code == 401:
                    # Try to extract server reason from response
                    server_reason = None
                    try:
                        error_data = response.json()
                        # Common error response fields
                        server_reason = error_data.get('detail') or error_data.get('message') or error_data.get('error')
                        # Sanitize: don't include if it might contain sensitive data
                        if server_reason and any(word in str(server_reason).lower() for word in ['password', 'token', 'secret', 'key']):
                            server_reason = None
                    except Exception:
                        pass
                    
                    error = LabelStudioAuthenticationError.create(
                        status_code=401,
                        error_type='invalid_credentials',
                        server_reason=server_reason
                    )
                    logger.error(
                        f"[Label Studio] JWT authentication failed: {error.message} "
                        f"(status_code=401)"
                    )
                    # Clear any existing tokens on auth failure
                    self.clear_tokens()
                    raise error
                
                if response.status_code == 403:
                    # Try to extract server reason from response
                    server_reason = None
                    try:
                        error_data = response.json()
                        server_reason = error_data.get('detail') or error_data.get('message') or error_data.get('error')
                        # Sanitize: don't include if it might contain sensitive data
                        if server_reason and any(word in str(server_reason).lower() for word in ['password', 'token', 'secret', 'key']):
                            server_reason = None
                    except Exception:
                        pass
                    
                    error = LabelStudioAuthenticationError.create(
                        status_code=403,
                        error_type='insufficient_permissions',
                        server_reason=server_reason
                    )
                    logger.error(
                        f"[Label Studio] JWT authentication failed: {error.message} "
                        f"(status_code=403)"
                    )
                    # Clear any existing tokens on auth failure
                    self.clear_tokens()
                    raise error
                
                # Handle other non-success status codes
                if response.status_code not in (200, 201):
                    # Try to extract server reason from response
                    server_reason = None
                    try:
                        error_data = response.json()
                        server_reason = error_data.get('detail') or error_data.get('message') or error_data.get('error')
                        # Sanitize: don't include if it might contain sensitive data
                        if server_reason and any(word in str(server_reason).lower() for word in ['password', 'token', 'secret', 'key']):
                            server_reason = None
                    except Exception:
                        pass
                    
                    error = LabelStudioAuthenticationError.create(
                        status_code=response.status_code,
                        server_reason=server_reason
                    )
                    logger.error(f"[Label Studio] JWT authentication failed: {error.message}")
                    self.clear_tokens()
                    raise error
                
                # Parse response JSON
                try:
                    response_data = response.json()
                except Exception as e:
                    error = LabelStudioAuthenticationError(
                        message=(
                            "Failed to parse authentication response from Label Studio. "
                            "The server returned an invalid JSON response. "
                            "Please verify Label Studio is running correctly and try again."
                        ),
                        status_code=response.status_code,
                        error_type='invalid_response'
                    )
                    logger.error(f"[Label Studio] {error.message} (parse error: {e})")
                    self.clear_tokens()
                    raise error
                
                # Extract tokens from response
                access_token = response_data.get('access_token')
                refresh_token = response_data.get('refresh_token')
                
                if not access_token:
                    error = LabelStudioAuthenticationError(
                        message=(
                            "Authentication response from Label Studio is missing the access token. "
                            "This may indicate a Label Studio version incompatibility or server issue. "
                            "Please verify you are using Label Studio 1.22.0 or later."
                        ),
                        status_code=response.status_code,
                        error_type='missing_token'
                    )
                    logger.error(f"[Label Studio] {error.message}")
                    self.clear_tokens()
                    raise error
                
                if not refresh_token:
                    error = LabelStudioAuthenticationError(
                        message=(
                            "Authentication response from Label Studio is missing the refresh token. "
                            "This may indicate a Label Studio version incompatibility or server issue. "
                            "Please verify you are using Label Studio 1.22.0 or later."
                        ),
                        status_code=response.status_code,
                        error_type='missing_token'
                    )
                    logger.error(f"[Label Studio] {error.message}")
                    self.clear_tokens()
                    raise error
                
                # Store tokens in memory (security: never persist to disk)
                self._access_token = access_token
                self._refresh_token = refresh_token
                
                # Parse token expiration from JWT
                self._token_expires_at = self._parse_token_expiration(access_token)
                
                # Mark as authenticated
                self._is_authenticated = True
                
                # Log success WITHOUT logging tokens (security requirement)
                logger.info(
                    f"[Label Studio] JWT authentication successful "
                    f"(expires_at={self._token_expires_at.isoformat() if self._token_expires_at else 'unknown'})"
                )
                
                return True
                
        except LabelStudioAuthenticationError:
            # Re-raise authentication errors as-is
            raise
        except httpx.TimeoutException as e:
            error_msg = f"Authentication request timed out: {e}"
            logger.error(f"[Label Studio] {error_msg}")
            # Don't clear tokens on network errors - let retry logic handle it
            raise  # Let network errors propagate for retry handling
        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to Label Studio: {e}"
            logger.error(f"[Label Studio] {error_msg}")
            # Don't clear tokens on network errors - let retry logic handle it
            raise  # Let network errors propagate for retry handling
        except httpx.HTTPError as e:
            error_msg = f"HTTP error during authentication: {e}"
            logger.error(f"[Label Studio] {error_msg}")
            raise  # Let network errors propagate for retry handling
        except Exception as e:
            error_msg = f"Unexpected error during authentication: {e}"
            logger.error(f"[Label Studio] {error_msg}")
            raise


# Export public API
__all__ = [
    'JWTAuthManager',
    'JWTTokenResponse',
]
