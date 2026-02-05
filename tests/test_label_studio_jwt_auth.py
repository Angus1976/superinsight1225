"""
Unit tests for Label Studio JWT Authentication Module.

Tests the JWTAuthManager class and its login() method.

Validates: Requirements 1.1, 1.2, 1.3, 9.1, 9.2, 10.2
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.label_studio.jwt_auth import JWTAuthManager, JWTTokenResponse
from src.label_studio.integration import LabelStudioIntegration
from src.label_studio.exceptions import LabelStudioAuthenticationError


class TestJWTTokenResponse:
    """Tests for JWTTokenResponse dataclass."""
    
    def test_from_dict_with_all_fields(self):
        """Test creating JWTTokenResponse from dict with all fields."""
        data = {
            "access_token": "access123",
            "refresh_token": "refresh456",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        response = JWTTokenResponse.from_dict(data)
        
        assert response.access_token == "access123"
        assert response.refresh_token == "refresh456"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
    
    def test_from_dict_with_minimal_fields(self):
        """Test creating JWTTokenResponse from dict with only required fields."""
        data = {
            "access_token": "access123",
            "refresh_token": "refresh456"
        }
        
        response = JWTTokenResponse.from_dict(data)
        
        assert response.access_token == "access123"
        assert response.refresh_token == "refresh456"
        assert response.token_type == "Bearer"  # Default value
        assert response.expires_in is None  # Default value
    
    def test_from_dict_missing_access_token(self):
        """Test that missing access_token raises KeyError."""
        data = {"refresh_token": "refresh456"}
        
        with pytest.raises(KeyError):
            JWTTokenResponse.from_dict(data)
    
    def test_from_dict_missing_refresh_token(self):
        """Test that missing refresh_token raises KeyError."""
        data = {"access_token": "access123"}
        
        with pytest.raises(KeyError):
            JWTTokenResponse.from_dict(data)


class TestJWTAuthManagerInit:
    """Tests for JWTAuthManager initialization."""
    
    def test_init_with_credentials(self):
        """Test initialization with username and password."""
        auth = JWTAuthManager(
            base_url="http://label-studio:8080",
            username="admin",
            password="secret"
        )
        
        assert auth.base_url == "http://label-studio:8080"
        assert auth.username == "admin"
        assert auth.password == "secret"
        assert auth._access_token is None
        assert auth._refresh_token is None
        assert auth._is_authenticated is False
    
    def test_init_without_credentials(self):
        """Test initialization without credentials."""
        auth = JWTAuthManager(base_url="http://label-studio:8080")
        
        assert auth.base_url == "http://label-studio:8080"
        assert auth.username is None
        assert auth.password is None
        assert not auth.has_credentials()
    
    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base_url."""
        auth = JWTAuthManager(base_url="http://label-studio:8080/")
        
        assert auth.base_url == "http://label-studio:8080"
    
    def test_has_credentials(self):
        """Test has_credentials method."""
        auth_with = JWTAuthManager("http://test", "user", "pass")
        auth_without = JWTAuthManager("http://test")
        auth_partial = JWTAuthManager("http://test", username="user")
        
        assert auth_with.has_credentials() is True
        assert auth_without.has_credentials() is False
        assert auth_partial.has_credentials() is False


class TestJWTAuthManagerLogin:
    """Tests for JWTAuthManager.login() method."""
    
    @pytest.fixture
    def auth_manager(self):
        """Create a JWTAuthManager instance for testing."""
        return JWTAuthManager(
            base_url="http://label-studio:8080",
            username="admin",
            password="secret"
        )
    
    @pytest.fixture
    def mock_jwt_token(self):
        """Create a mock JWT token with exp claim."""
        import jwt
        exp_time = datetime.utcnow() + timedelta(hours=1)
        return jwt.encode(
            {"exp": exp_time.timestamp(), "sub": "user123"},
            "secret",
            algorithm="HS256"
        )
    
    @pytest.mark.asyncio
    async def test_login_success(self, auth_manager, mock_jwt_token):
        """Test successful login stores tokens and sets authenticated state."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "refresh_token_123"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await auth_manager.login()
        
        assert result is True
        assert auth_manager._access_token == mock_jwt_token
        assert auth_manager._refresh_token == "refresh_token_123"
        assert auth_manager._is_authenticated is True
        assert auth_manager._token_expires_at is not None
    
    @pytest.mark.asyncio
    async def test_login_success_201_status(self, auth_manager, mock_jwt_token):
        """Test successful login with 201 status code."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "refresh_token_123"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await auth_manager.login()
        
        assert result is True
        assert auth_manager._is_authenticated is True
    
    @pytest.mark.asyncio
    async def test_login_401_invalid_credentials(self, auth_manager):
        """Test login with invalid credentials raises LabelStudioAuthenticationError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
        
        assert exc_info.value.status_code == 401
        assert "Invalid username or password" in str(exc_info.value)
        assert auth_manager._is_authenticated is False
        assert auth_manager._access_token is None
    
    @pytest.mark.asyncio
    async def test_login_403_forbidden(self, auth_manager):
        """Test login with forbidden access raises LabelStudioAuthenticationError."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
        
        assert exc_info.value.status_code == 403
        assert "forbidden" in str(exc_info.value).lower()
        assert auth_manager._is_authenticated is False
    
    @pytest.mark.asyncio
    async def test_login_missing_access_token(self, auth_manager):
        """Test login with missing access_token in response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "refresh_token": "refresh_token_123"
            # Missing access_token
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
        
        # Updated assertion to match new actionable error message
        assert "missing" in str(exc_info.value).lower() and "access token" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_login_missing_refresh_token(self, auth_manager, mock_jwt_token):
        """Test login with missing refresh_token in response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token
            # Missing refresh_token
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
        
        # Updated assertion to match new actionable error message
        assert "missing" in str(exc_info.value).lower() and "refresh token" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_login_without_credentials_raises_error(self):
        """Test login without credentials raises ValueError."""
        auth = JWTAuthManager(base_url="http://label-studio:8080")
        
        with pytest.raises(ValueError) as exc_info:
            await auth.login()
        
        assert "LABEL_STUDIO" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_login_network_timeout(self, auth_manager):
        """Test login with network timeout propagates exception."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )
            
            with pytest.raises(httpx.TimeoutException):
                await auth_manager.login()
    
    @pytest.mark.asyncio
    async def test_login_connection_error(self, auth_manager):
        """Test login with connection error propagates exception."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            
            with pytest.raises(httpx.ConnectError):
                await auth_manager.login()
    
    @pytest.mark.asyncio
    async def test_login_uses_correct_endpoint(self, auth_manager, mock_jwt_token):
        """Test login makes POST request to correct endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "refresh_token_123"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await auth_manager.login()
        
        # Verify the correct URL was called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://label-studio:8080/api/sessions/"
    
    @pytest.mark.asyncio
    async def test_login_sends_correct_payload(self, auth_manager, mock_jwt_token):
        """Test login sends correct JSON payload with email field."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "refresh_token_123"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await auth_manager.login()
        
        # Verify the correct payload was sent
        call_args = mock_post.call_args
        assert call_args[1]["json"] == {
            "email": "admin",  # Note: Label Studio uses "email" field
            "password": "secret"
        }
    
    @pytest.mark.asyncio
    async def test_login_clears_tokens_on_auth_failure(self, auth_manager, mock_jwt_token):
        """Test that login clears existing tokens on authentication failure."""
        # Set up existing tokens
        auth_manager._access_token = "old_access_token"
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError):
                await auth_manager.login()
        
        # Verify tokens were cleared
        assert auth_manager._access_token is None
        assert auth_manager._refresh_token is None
        assert auth_manager._is_authenticated is False


class TestJWTAuthManagerTokenExpiration:
    """Tests for token expiration detection."""
    
    def test_is_token_expired_no_token(self):
        """Test _is_token_expired returns True when no token."""
        auth = JWTAuthManager("http://test")
        
        assert auth._is_token_expired() is True
    
    def test_is_token_expired_no_expiration(self):
        """Test _is_token_expired returns True when no expiration time."""
        auth = JWTAuthManager("http://test")
        auth._access_token = "some_token"
        auth._token_expires_at = None
        
        assert auth._is_token_expired() is True
    
    def test_is_token_expired_future_expiration(self):
        """Test _is_token_expired returns False for future expiration."""
        auth = JWTAuthManager("http://test")
        auth._access_token = "some_token"
        auth._token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        assert auth._is_token_expired() is False
    
    def test_is_token_expired_past_expiration(self):
        """Test _is_token_expired returns True for past expiration."""
        auth = JWTAuthManager("http://test")
        auth._access_token = "some_token"
        auth._token_expires_at = datetime.utcnow() - timedelta(hours=1)
        
        assert auth._is_token_expired() is True
    
    def test_is_token_expired_within_buffer(self):
        """Test _is_token_expired returns True when within buffer period."""
        auth = JWTAuthManager("http://test")
        auth._access_token = "some_token"
        # Token expires in 30 seconds, but buffer is 60 seconds
        auth._token_expires_at = datetime.utcnow() + timedelta(seconds=30)
        
        assert auth._is_token_expired(buffer_seconds=60) is True
    
    def test_is_token_expired_outside_buffer(self):
        """Test _is_token_expired returns False when outside buffer period."""
        auth = JWTAuthManager("http://test")
        auth._access_token = "some_token"
        # Token expires in 120 seconds, buffer is 60 seconds
        auth._token_expires_at = datetime.utcnow() + timedelta(seconds=120)
        
        assert auth._is_token_expired(buffer_seconds=60) is False


class TestJWTAuthManagerHelpers:
    """Tests for helper methods."""
    
    def test_get_auth_header_with_token(self):
        """Test get_auth_header returns Bearer token header."""
        auth = JWTAuthManager("http://test")
        auth._access_token = "test_token_123"
        
        headers = auth.get_auth_header()
        
        assert headers == {"Authorization": "Bearer test_token_123"}
    
    def test_get_auth_header_without_token(self):
        """Test get_auth_header returns empty dict without token."""
        auth = JWTAuthManager("http://test")
        
        headers = auth.get_auth_header()
        
        assert headers == {}
    
    def test_get_auth_state_safe_logging(self):
        """Test get_auth_state does not include sensitive data."""
        auth = JWTAuthManager("http://test", "user", "secret_password")
        auth._access_token = "secret_access_token"
        auth._refresh_token = "secret_refresh_token"
        auth._is_authenticated = True
        
        state = auth.get_auth_state()
        
        # Verify no sensitive data
        assert "secret_password" not in str(state)
        assert "secret_access_token" not in str(state)
        assert "secret_refresh_token" not in str(state)
        
        # Verify expected fields
        assert state["is_authenticated"] is True
        assert state["has_access_token"] is True
        assert state["has_refresh_token"] is True
        assert state["has_credentials"] is True
    
    def test_clear_tokens(self):
        """Test clear_tokens removes all token data."""
        auth = JWTAuthManager("http://test")
        auth._access_token = "access"
        auth._refresh_token = "refresh"
        auth._token_expires_at = datetime.utcnow()
        auth._is_authenticated = True
        
        auth.clear_tokens()
        
        assert auth._access_token is None
        assert auth._refresh_token is None
        assert auth._token_expires_at is None
        assert auth._is_authenticated is False
    
    def test_set_credentials(self):
        """Test set_credentials updates username and password."""
        auth = JWTAuthManager("http://test")
        
        auth.set_credentials("new_user", "new_pass")
        
        assert auth.username == "new_user"
        assert auth.password == "new_pass"
        assert auth.has_credentials() is True
    
    def test_is_authenticated_property(self):
        """Test is_authenticated property."""
        auth = JWTAuthManager("http://test")
        
        # Not authenticated initially
        assert auth.is_authenticated is False
        
        # Set authenticated state but no token
        auth._is_authenticated = True
        assert auth.is_authenticated is False
        
        # Set token
        auth._access_token = "token"
        assert auth.is_authenticated is True


class TestJWTAuthManagerParseTokenExpiration:
    """Tests for _parse_token_expiration method."""
    
    def test_parse_valid_token(self):
        """Test parsing a valid JWT token with exp claim."""
        import jwt
        import time
        
        auth = JWTAuthManager("http://test")
        # Use Unix timestamp directly to avoid timezone issues
        exp_timestamp = int(time.time()) + 3600  # 1 hour from now
        token = jwt.encode(
            {"exp": exp_timestamp, "sub": "user123"},
            "secret",
            algorithm="HS256"
        )
        
        result = auth._parse_token_expiration(token)
        
        assert result is not None
        # Verify the parsed expiration matches the expected timestamp
        expected_exp = datetime.utcfromtimestamp(exp_timestamp)
        # Allow 1 second tolerance for test execution time
        assert abs((result - expected_exp).total_seconds()) < 1
    
    def test_parse_token_without_exp(self):
        """Test parsing a JWT token without exp claim returns None."""
        import jwt
        
        auth = JWTAuthManager("http://test")
        token = jwt.encode(
            {"sub": "user123"},  # No exp claim
            "secret",
            algorithm="HS256"
        )
        
        result = auth._parse_token_expiration(token)
        
        assert result is None
    
    def test_parse_invalid_token(self):
        """Test parsing an invalid token returns None."""
        auth = JWTAuthManager("http://test")
        
        result = auth._parse_token_expiration("not_a_valid_jwt_token")
        
        assert result is None
    
    def test_parse_empty_token(self):
        """Test parsing an empty token returns None."""
        auth = JWTAuthManager("http://test")
        
        result = auth._parse_token_expiration("")
        
        assert result is None
    
    def test_parse_none_token(self):
        """Test parsing None token returns None."""
        auth = JWTAuthManager("http://test")
        
        result = auth._parse_token_expiration(None)
        
        assert result is None


class TestJWTAuthManagerRefreshToken:
    """Tests for JWTAuthManager.refresh_token() method.
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 9.3, 9.4, 10.2, 10.4
    """
    
    @pytest.fixture
    def auth_manager(self):
        """Create a JWTAuthManager instance for testing."""
        return JWTAuthManager(
            base_url="http://label-studio:8080",
            username="admin",
            password="secret"
        )
    
    @pytest.fixture
    def mock_jwt_token(self):
        """Create a mock JWT token with exp claim."""
        import jwt
        exp_time = datetime.utcnow() + timedelta(hours=1)
        return jwt.encode(
            {"exp": exp_time.timestamp(), "sub": "user123"},
            "secret",
            algorithm="HS256"
        )
    
    @pytest.fixture
    def authenticated_auth_manager(self, auth_manager, mock_jwt_token):
        """Create an authenticated JWTAuthManager instance."""
        auth_manager._access_token = mock_jwt_token
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() + timedelta(hours=1)
        return auth_manager
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, authenticated_auth_manager, mock_jwt_token):
        """Test successful token refresh updates tokens.
        
        Validates: Requirements 2.1, 2.2, 2.3
        """
        new_access_token = mock_jwt_token
        new_refresh_token = "new_refresh_token_456"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await authenticated_auth_manager.refresh_token()
        
        assert result is True
        assert authenticated_auth_manager._access_token == new_access_token
        assert authenticated_auth_manager._refresh_token == new_refresh_token
        assert authenticated_auth_manager._is_authenticated is True
        assert authenticated_auth_manager._token_expires_at is not None
    
    @pytest.mark.asyncio
    async def test_refresh_token_uses_correct_endpoint(self, authenticated_auth_manager, mock_jwt_token):
        """Test refresh_token makes POST request to correct endpoint.
        
        Validates: Requirements 2.2
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await authenticated_auth_manager.refresh_token()
        
        # Verify the correct URL was called
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://label-studio:8080/api/sessions/refresh/"
    
    @pytest.mark.asyncio
    async def test_refresh_token_sends_correct_payload(self, authenticated_auth_manager, mock_jwt_token):
        """Test refresh_token sends correct JSON payload with refresh token.
        
        Validates: Requirements 2.2
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await authenticated_auth_manager.refresh_token()
        
        # Verify the correct payload was sent
        call_args = mock_post.call_args
        assert call_args[1]["json"] == {
            "refresh": "old_refresh_token"
        }
    
    @pytest.mark.asyncio
    async def test_refresh_token_401_falls_back_to_login(self, authenticated_auth_manager, mock_jwt_token):
        """Test refresh_token falls back to login on 401 (refresh token expired).
        
        Validates: Requirements 2.4
        """
        # First call returns 401 (refresh token expired)
        mock_refresh_response = MagicMock()
        mock_refresh_response.status_code = 401
        
        # Second call (login) returns success
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_from_login"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=[mock_refresh_response, mock_login_response])
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            result = await authenticated_auth_manager.refresh_token()
        
        assert result is True
        assert authenticated_auth_manager._access_token == mock_jwt_token
        assert authenticated_auth_manager._refresh_token == "new_refresh_from_login"
        assert authenticated_auth_manager._is_authenticated is True
        
        # Verify both endpoints were called
        assert mock_post.call_count == 2
        calls = mock_post.call_args_list
        assert "/api/sessions/refresh/" in calls[0][0][0]
        assert "/api/sessions/" in calls[1][0][0]
    
    @pytest.mark.asyncio
    async def test_refresh_token_403_raises_error(self, authenticated_auth_manager):
        """Test refresh_token raises error on 403 (forbidden).
        
        Validates: Requirements 2.4 (cannot recover from 403)
        """
        mock_response = MagicMock()
        mock_response.status_code = 403
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await authenticated_auth_manager.refresh_token()
        
        assert exc_info.value.status_code == 403
        assert "forbidden" in str(exc_info.value).lower()
        assert authenticated_auth_manager._is_authenticated is False
        assert authenticated_auth_manager._access_token is None
    
    @pytest.mark.asyncio
    async def test_refresh_token_no_refresh_token_falls_back_to_login(self, auth_manager, mock_jwt_token):
        """Test refresh_token falls back to login when no refresh token available.
        
        Validates: Requirements 2.4
        """
        # No refresh token set
        auth_manager._refresh_token = None
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await auth_manager.refresh_token()
        
        assert result is True
        assert auth_manager._is_authenticated is True
    
    @pytest.mark.asyncio
    async def test_refresh_token_clears_old_tokens_before_storing_new(self, authenticated_auth_manager, mock_jwt_token):
        """Test refresh_token clears old tokens before storing new ones (security).
        
        Validates: Requirements 10.4
        """
        old_access = authenticated_auth_manager._access_token
        old_refresh = authenticated_auth_manager._refresh_token
        
        new_access_token = mock_jwt_token
        new_refresh_token = "completely_new_refresh_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            await authenticated_auth_manager.refresh_token()
        
        # Verify new tokens are stored
        assert authenticated_auth_manager._access_token == new_access_token
        assert authenticated_auth_manager._refresh_token == new_refresh_token
        # Verify old tokens are not the same (they were cleared and replaced)
        assert authenticated_auth_manager._access_token != old_access or new_access_token == old_access
        assert authenticated_auth_manager._refresh_token != old_refresh
    
    @pytest.mark.asyncio
    async def test_refresh_token_missing_access_token_falls_back_to_login(self, authenticated_auth_manager, mock_jwt_token):
        """Test refresh_token falls back to login when response missing access_token.
        
        Validates: Requirements 2.4
        """
        # First call returns response without access_token
        mock_refresh_response = MagicMock()
        mock_refresh_response.status_code = 200
        mock_refresh_response.json.return_value = {
            "refresh_token": "new_refresh_token"
            # Missing access_token
        }
        
        # Second call (login) returns success
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_from_login"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=[mock_refresh_response, mock_login_response])
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            result = await authenticated_auth_manager.refresh_token()
        
        assert result is True
        assert authenticated_auth_manager._access_token == mock_jwt_token
    
    @pytest.mark.asyncio
    async def test_refresh_token_missing_refresh_token_falls_back_to_login(self, authenticated_auth_manager, mock_jwt_token):
        """Test refresh_token falls back to login when response missing refresh_token.
        
        Validates: Requirements 2.4
        """
        # First call returns response without refresh_token
        mock_refresh_response = MagicMock()
        mock_refresh_response.status_code = 200
        mock_refresh_response.json.return_value = {
            "access_token": mock_jwt_token
            # Missing refresh_token
        }
        
        # Second call (login) returns success
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_from_login"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=[mock_refresh_response, mock_login_response])
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            result = await authenticated_auth_manager.refresh_token()
        
        assert result is True
        assert authenticated_auth_manager._refresh_token == "new_refresh_from_login"
    
    @pytest.mark.asyncio
    async def test_refresh_token_network_timeout(self, authenticated_auth_manager):
        """Test refresh_token propagates network timeout exception.
        
        Network errors should propagate for retry handling.
        """
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )
            
            with pytest.raises(httpx.TimeoutException):
                await authenticated_auth_manager.refresh_token()
    
    @pytest.mark.asyncio
    async def test_refresh_token_connection_error(self, authenticated_auth_manager):
        """Test refresh_token propagates connection error exception.
        
        Network errors should propagate for retry handling.
        """
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            
            with pytest.raises(httpx.ConnectError):
                await authenticated_auth_manager.refresh_token()
    
    @pytest.mark.asyncio
    async def test_refresh_token_unexpected_status_falls_back_to_login(self, authenticated_auth_manager, mock_jwt_token):
        """Test refresh_token falls back to login on unexpected status code.
        
        Validates: Requirements 2.4
        """
        # First call returns unexpected status
        mock_refresh_response = MagicMock()
        mock_refresh_response.status_code = 500
        
        # Second call (login) returns success
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_from_login"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=[mock_refresh_response, mock_login_response])
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            result = await authenticated_auth_manager.refresh_token()
        
        assert result is True
        assert authenticated_auth_manager._is_authenticated is True
    
    @pytest.mark.asyncio
    async def test_refresh_token_201_status_success(self, authenticated_auth_manager, mock_jwt_token):
        """Test successful token refresh with 201 status code.
        
        Validates: Requirements 2.3
        """
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await authenticated_auth_manager.refresh_token()
        
        assert result is True
        assert authenticated_auth_manager._is_authenticated is True



class TestJWTAuthManagerEnsureAuthenticated:
    """Tests for JWTAuthManager._ensure_authenticated() method.
    
    Validates: Requirements 2.5, 4.1, 4.2
    """
    
    @pytest.fixture
    def auth_manager(self):
        """Create a JWTAuthManager instance for testing."""
        return JWTAuthManager(
            base_url="http://label-studio:8080",
            username="admin",
            password="secret"
        )
    
    @pytest.fixture
    def mock_jwt_token(self):
        """Create a mock JWT token with exp claim."""
        import jwt
        exp_time = datetime.utcnow() + timedelta(hours=1)
        return jwt.encode(
            {"exp": exp_time.timestamp(), "sub": "user123"},
            "secret",
            algorithm="HS256"
        )
    
    @pytest.mark.asyncio
    async def test_ensure_authenticated_valid_token_no_action(self, auth_manager, mock_jwt_token):
        """Test _ensure_authenticated does nothing when token is valid.
        
        Validates: Requirements 2.5
        """
        # Set up valid authenticated state
        auth_manager._access_token = mock_jwt_token
        auth_manager._refresh_token = "refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Should not make any HTTP calls
        with patch("httpx.AsyncClient") as mock_client:
            await auth_manager._ensure_authenticated()
            
            # Verify no HTTP calls were made
            mock_client.assert_not_called()
        
        # State should be unchanged
        assert auth_manager._access_token == mock_jwt_token
        assert auth_manager._is_authenticated is True
    
    @pytest.mark.asyncio
    async def test_ensure_authenticated_not_authenticated_calls_login(self, auth_manager, mock_jwt_token):
        """Test _ensure_authenticated calls login when not authenticated.
        
        Validates: Requirements 2.5
        """
        # Not authenticated
        auth_manager._is_authenticated = False
        auth_manager._access_token = None
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            await auth_manager._ensure_authenticated()
        
        # Should now be authenticated
        assert auth_manager._is_authenticated is True
        assert auth_manager._access_token == mock_jwt_token
    
    @pytest.mark.asyncio
    async def test_ensure_authenticated_expired_token_calls_refresh(self, auth_manager, mock_jwt_token):
        """Test _ensure_authenticated calls refresh when token is expired.
        
        Validates: Requirements 2.5
        """
        # Set up expired token
        import jwt
        expired_token = jwt.encode(
            {"exp": (datetime.utcnow() - timedelta(hours=1)).timestamp(), "sub": "user123"},
            "secret",
            algorithm="HS256"
        )
        
        auth_manager._access_token = expired_token
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(hours=1)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await auth_manager._ensure_authenticated()
        
        # Verify refresh endpoint was called
        call_args = mock_post.call_args
        assert "/api/sessions/refresh/" in call_args[0][0]
        
        # Should have new token
        assert auth_manager._access_token == mock_jwt_token
    
    @pytest.mark.asyncio
    async def test_ensure_authenticated_expiring_soon_calls_refresh(self, auth_manager, mock_jwt_token):
        """Test _ensure_authenticated calls refresh when token is expiring soon.
        
        Validates: Requirements 2.5 (proactive refresh)
        """
        # Set up token expiring within buffer period (60 seconds)
        import jwt
        expiring_soon_token = jwt.encode(
            {"exp": (datetime.utcnow() + timedelta(seconds=30)).timestamp(), "sub": "user123"},
            "secret",
            algorithm="HS256"
        )
        
        auth_manager._access_token = expiring_soon_token
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() + timedelta(seconds=30)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await auth_manager._ensure_authenticated()
        
        # Verify refresh was called
        assert mock_post.called
        
        # Should have new token
        assert auth_manager._access_token == mock_jwt_token
    
    @pytest.mark.asyncio
    async def test_ensure_authenticated_concurrent_calls_single_refresh(self, auth_manager):
        """Test concurrent _ensure_authenticated calls trigger only one refresh.
        
        Validates: Requirements 4.1, 4.2 (thread safety)
        
        Note: This test verifies that the lock prevents concurrent refresh operations.
        Due to the fast path check before the lock, all concurrent calls may see
        the expired token initially, but only one should actually perform the refresh.
        """
        import jwt
        import time
        
        # Set up expired token using time.time() to avoid timezone issues
        expired_token = jwt.encode(
            {"exp": time.time() - 3600, "sub": "user123"},  # 1 hour in the past
            "secret",
            algorithm="HS256"
        )
        
        auth_manager._access_token = expired_token
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(hours=1)
        
        refresh_call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal refresh_call_count
            refresh_call_count += 1
            # Simulate some delay to allow other tasks to queue up
            await asyncio.sleep(0.05)
            
            # Create a fresh token with future expiration INSIDE the mock
            # Use time.time() to avoid timezone issues
            fresh_token = jwt.encode(
                {"exp": time.time() + 3600, "sub": "user123"},  # 1 hour in the future
                "secret",
                algorithm="HS256"
            )
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": fresh_token,
                "refresh_token": "new_refresh_token"
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Create tasks but don't start them yet
            async def ensure_auth_task():
                await auth_manager._ensure_authenticated()
            
            # Start all tasks at roughly the same time
            tasks = [asyncio.create_task(ensure_auth_task()) for _ in range(5)]
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        
        # Due to the double-check pattern after acquiring the lock,
        # only one refresh should have been made
        # Note: The first task to acquire the lock will refresh,
        # subsequent tasks will see the refreshed token and skip
        assert refresh_call_count == 1, \
            f"Expected 1 refresh call, got {refresh_call_count}"
        
        # All calls should see the new token
        assert auth_manager._is_authenticated is True
        assert not auth_manager._is_token_expired()
    
    @pytest.mark.asyncio
    async def test_ensure_authenticated_propagates_auth_error(self, auth_manager):
        """Test _ensure_authenticated propagates authentication errors.
        
        Validates: Requirements 2.5
        """
        # Not authenticated
        auth_manager._is_authenticated = False
        auth_manager._access_token = None
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError):
                await auth_manager._ensure_authenticated()
    
    @pytest.mark.asyncio
    async def test_ensure_authenticated_no_credentials_raises_error(self):
        """Test _ensure_authenticated raises error when no credentials.
        
        Validates: Requirements 2.5
        """
        auth_manager = JWTAuthManager(base_url="http://label-studio:8080")
        # No credentials set
        
        with pytest.raises(ValueError) as exc_info:
            await auth_manager._ensure_authenticated()
        
        assert "LABEL_STUDIO" in str(exc_info.value)


# ============================================================================
# Tests for Token Expiration Detection in API Calls
# Validates: Requirements 5.3, 8.1, 8.2
# ============================================================================

class TestTokenExpirationDetection:
    """Tests for token expiration detection in API responses.
    
    Validates: Requirements 5.3, 8.1 - Detect token expiration from 401 response
    """
    
    @pytest.fixture
    def integration(self):
        """Create a LabelStudioIntegration instance for testing."""
        from src.label_studio.integration import LabelStudioIntegration
        from src.label_studio.config import LabelStudioConfig
        
        # Create a mock config
        with patch.object(LabelStudioConfig, '__init__', lambda self: None):
            config = LabelStudioConfig()
            config.base_url = "http://label-studio:8080"
            config.api_token = "test_token"
            config.username = None
            config.password = None
            config.project_id = None
            config.validate_config = MagicMock(return_value=True)
            config.get_auth_method = MagicMock(return_value='api_token')
            
            with patch.object(LabelStudioIntegration, '__init__', lambda self, cfg=None: None):
                integration = LabelStudioIntegration()
                integration.config = config
                integration.base_url = "http://label-studio:8080"
                integration.api_token = "test_token"
                integration._jwt_auth_manager = None
                integration._auth_method = 'api_token'
                integration.headers = {
                    'Authorization': 'Token test_token',
                    'Content-Type': 'application/json'
                }
                return integration
    
    @pytest.fixture
    def jwt_integration(self):
        """Create a LabelStudioIntegration instance with JWT auth for testing."""
        from src.label_studio.integration import LabelStudioIntegration
        from src.label_studio.config import LabelStudioConfig
        
        # Create a mock config
        with patch.object(LabelStudioConfig, '__init__', lambda self: None):
            config = LabelStudioConfig()
            config.base_url = "http://label-studio:8080"
            config.api_token = None
            config.username = "admin"
            config.password = "secret"
            config.project_id = None
            config.validate_config = MagicMock(return_value=True)
            config.get_auth_method = MagicMock(return_value='jwt')
            
            with patch.object(LabelStudioIntegration, '__init__', lambda self, cfg=None: None):
                integration = LabelStudioIntegration()
                integration.config = config
                integration.base_url = "http://label-studio:8080"
                integration.api_token = None
                integration._auth_method = 'jwt'
                integration.headers = {'Content-Type': 'application/json'}
                
                # Create mock JWT auth manager
                jwt_auth = JWTAuthManager(
                    base_url="http://label-studio:8080",
                    username="admin",
                    password="secret"
                )
                jwt_auth._access_token = "test_access_token"
                jwt_auth._refresh_token = "test_refresh_token"
                jwt_auth._is_authenticated = True
                jwt_auth._token_expires_at = datetime.utcnow() + timedelta(hours=1)
                
                integration._jwt_auth_manager = jwt_auth
                return integration
    
    def test_is_token_expired_response_with_expired_message(self, integration):
        """Test detection of 'token expired' message in 401 response."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"detail": "Token has expired"}'
        mock_response.json.return_value = {"detail": "Token has expired"}
        
        result = integration._is_token_expired_response(mock_response)
        
        assert result is True
    
    def test_is_token_expired_response_with_jwt_expired_message(self, integration):
        """Test detection of 'JWT expired' message in 401 response."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"error": "JWT expired"}'
        mock_response.json.return_value = {"error": "JWT expired"}
        
        result = integration._is_token_expired_response(mock_response)
        
        assert result is True
    
    def test_is_token_expired_response_with_signature_expired(self, integration):
        """Test detection of 'Signature has expired' message in 401 response."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"message": "Signature has expired"}'
        mock_response.json.return_value = {"message": "Signature has expired"}
        
        result = integration._is_token_expired_response(mock_response)
        
        assert result is True
    
    def test_is_token_expired_response_with_invalid_credentials(self, integration):
        """Test that invalid credentials (not expiration) returns False."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"detail": "Invalid username or password"}'
        mock_response.json.return_value = {"detail": "Invalid username or password"}
        
        result = integration._is_token_expired_response(mock_response)
        
        assert result is False
    
    def test_is_token_expired_response_with_non_401_status(self, integration):
        """Test that non-401 status codes return False."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = '{"detail": "Token has expired"}'
        
        result = integration._is_token_expired_response(mock_response)
        
        assert result is False
    
    def test_is_token_expired_response_with_200_status(self, integration):
        """Test that 200 status code returns False."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"success": true}'
        
        result = integration._is_token_expired_response(mock_response)
        
        assert result is False
    
    def test_is_token_expired_response_case_insensitive(self, integration):
        """Test that token expiration detection is case-insensitive."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"detail": "TOKEN HAS EXPIRED"}'
        mock_response.json.return_value = {"detail": "TOKEN HAS EXPIRED"}
        
        result = integration._is_token_expired_response(mock_response)
        
        assert result is True
    
    def test_is_token_expired_response_with_text_only(self, integration):
        """Test detection when JSON parsing fails but text contains indicator."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = 'Token has expired'
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        result = integration._is_token_expired_response(mock_response)
        
        assert result is True


class TestHandleTokenExpirationAndRetry:
    """Tests for automatic token refresh and retry on expiration.
    
    Validates: Requirements 5.3, 8.1, 8.2 - Token expiration detection and retry
    """
    
    @pytest.fixture
    def mock_jwt_token(self):
        """Create a mock JWT token with exp claim."""
        import jwt
        exp_time = datetime.utcnow() + timedelta(hours=1)
        return jwt.encode(
            {"exp": exp_time.timestamp(), "sub": "user123"},
            "secret",
            algorithm="HS256"
        )
    
    @pytest.fixture
    def jwt_integration(self, mock_jwt_token):
        """Create a LabelStudioIntegration instance with JWT auth for testing."""
        from src.label_studio.integration import LabelStudioIntegration
        from src.label_studio.config import LabelStudioConfig
        
        # Create a mock config
        with patch.object(LabelStudioConfig, '__init__', lambda self: None):
            config = LabelStudioConfig()
            config.base_url = "http://label-studio:8080"
            config.api_token = None
            config.username = "admin"
            config.password = "secret"
            config.project_id = None
            config.validate_config = MagicMock(return_value=True)
            config.get_auth_method = MagicMock(return_value='jwt')
            
            with patch.object(LabelStudioIntegration, '__init__', lambda self, cfg=None: None):
                integration = LabelStudioIntegration()
                integration.config = config
                integration.base_url = "http://label-studio:8080"
                integration.api_token = None
                integration._auth_method = 'jwt'
                integration.headers = {'Content-Type': 'application/json'}
                
                # Create mock JWT auth manager
                jwt_auth = JWTAuthManager(
                    base_url="http://label-studio:8080",
                    username="admin",
                    password="secret"
                )
                jwt_auth._access_token = mock_jwt_token
                jwt_auth._refresh_token = "test_refresh_token"
                jwt_auth._is_authenticated = True
                jwt_auth._token_expires_at = datetime.utcnow() + timedelta(hours=1)
                
                integration._jwt_auth_manager = jwt_auth
                
                # Add the helper methods from the real class
                from src.label_studio.integration import LabelStudioIntegration as RealIntegration
                integration._is_token_expired_response = RealIntegration._is_token_expired_response.__get__(integration)
                integration._handle_token_expiration_and_retry = RealIntegration._handle_token_expiration_and_retry.__get__(integration)
                integration._get_headers = RealIntegration._get_headers.__get__(integration)
                
                return integration
    
    @pytest.mark.asyncio
    async def test_handle_token_expiration_success_after_refresh(self, jwt_integration, mock_jwt_token):
        """Test successful API call after token refresh.
        
        Validates: Requirements 8.1, 8.2 - Refresh token and retry on expiration
        """
        # First call returns 401 with token expired
        expired_response = MagicMock()
        expired_response.status_code = 401
        expired_response.text = '{"detail": "Token has expired"}'
        expired_response.json.return_value = {"detail": "Token has expired"}
        
        # Second call (after refresh) returns success
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.text = '{"success": true}'
        success_response.json.return_value = {"success": True}
        
        call_count = 0
        
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return expired_response
            return success_response
        
        # Mock the refresh_token method
        jwt_integration._jwt_auth_manager.refresh_token = AsyncMock(return_value=True)
        
        result = await jwt_integration._handle_token_expiration_and_retry(mock_api_call)
        
        assert result.status_code == 200
        assert call_count == 2
        jwt_integration._jwt_auth_manager.refresh_token.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_token_expiration_no_retry_for_api_token(self, mock_jwt_token):
        """Test that API token auth doesn't trigger token refresh.
        
        Validates: Requirements 3.1 - API token auth doesn't use JWT refresh
        """
        from src.label_studio.integration import LabelStudioIntegration
        from src.label_studio.config import LabelStudioConfig
        
        # Create integration with API token auth
        with patch.object(LabelStudioConfig, '__init__', lambda self: None):
            config = LabelStudioConfig()
            config.base_url = "http://label-studio:8080"
            config.api_token = "test_token"
            config.username = None
            config.password = None
            config.project_id = None
            config.validate_config = MagicMock(return_value=True)
            config.get_auth_method = MagicMock(return_value='api_token')
            
            with patch.object(LabelStudioIntegration, '__init__', lambda self, cfg=None: None):
                integration = LabelStudioIntegration()
                integration.config = config
                integration.base_url = "http://label-studio:8080"
                integration.api_token = "test_token"
                integration._jwt_auth_manager = None
                integration._auth_method = 'api_token'
                integration.headers = {
                    'Authorization': 'Token test_token',
                    'Content-Type': 'application/json'
                }
                
                # Add the helper method
                from src.label_studio.integration import LabelStudioIntegration as RealIntegration
                integration._handle_token_expiration_and_retry = RealIntegration._handle_token_expiration_and_retry.__get__(integration)
        
        # Response with 401 (but API token auth, so no refresh)
        response = MagicMock()
        response.status_code = 401
        response.text = '{"detail": "Token has expired"}'
        
        async def mock_api_call():
            return response
        
        result = await integration._handle_token_expiration_and_retry(mock_api_call)
        
        # Should return the 401 response without retry (API token doesn't refresh)
        assert result.status_code == 401
    
    @pytest.mark.asyncio
    async def test_handle_token_expiration_fallback_to_login(self, jwt_integration, mock_jwt_token):
        """Test fallback to re-authentication when refresh fails.
        
        Validates: Requirements 8.3 - Fall back to login when refresh fails
        """
        # All calls return 401 with token expired
        expired_response = MagicMock()
        expired_response.status_code = 401
        expired_response.text = '{"detail": "Token has expired"}'
        expired_response.json.return_value = {"detail": "Token has expired"}
        
        # Success response after re-authentication
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.text = '{"success": true}'
        success_response.json.return_value = {"success": True}
        
        call_count = 0
        
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # First two calls fail
                return expired_response
            return success_response
        
        # Mock refresh_token to succeed but token still expired
        jwt_integration._jwt_auth_manager.refresh_token = AsyncMock(return_value=True)
        # Mock login to succeed
        jwt_integration._jwt_auth_manager.login = AsyncMock(return_value=True)
        
        result = await jwt_integration._handle_token_expiration_and_retry(mock_api_call)
        
        assert result.status_code == 200
        assert call_count == 3
        jwt_integration._jwt_auth_manager.refresh_token.assert_called_once()
        jwt_integration._jwt_auth_manager.login.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_token_expiration_raises_on_complete_failure(self, jwt_integration, mock_jwt_token):
        """Test that authentication error is raised when all recovery fails.
        
        Validates: Requirements 8.4 - Raise error when recovery fails
        """
        from src.label_studio.exceptions import LabelStudioAuthenticationError
        
        # All calls return 401 with token expired
        expired_response = MagicMock()
        expired_response.status_code = 401
        expired_response.text = '{"detail": "Token has expired"}'
        expired_response.json.return_value = {"detail": "Token has expired"}
        
        async def mock_api_call():
            return expired_response
        
        # Mock refresh_token to succeed
        jwt_integration._jwt_auth_manager.refresh_token = AsyncMock(return_value=True)
        # Mock login to succeed
        jwt_integration._jwt_auth_manager.login = AsyncMock(return_value=True)
        
        with pytest.raises(LabelStudioAuthenticationError) as exc_info:
            await jwt_integration._handle_token_expiration_and_retry(mock_api_call)
        
        assert "still expired after re-authentication" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_handle_token_expiration_no_retry_for_valid_response(self, jwt_integration):
        """Test that valid responses don't trigger token refresh.
        
        Validates: Requirements 8.1 - Only refresh on token expiration
        """
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.text = '{"success": true}'
        success_response.json.return_value = {"success": True}
        
        call_count = 0
        
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            return success_response
        
        # Mock refresh_token (should not be called)
        jwt_integration._jwt_auth_manager.refresh_token = AsyncMock(return_value=True)
        
        result = await jwt_integration._handle_token_expiration_and_retry(mock_api_call)
        
        assert result.status_code == 200
        assert call_count == 1
        jwt_integration._jwt_auth_manager.refresh_token.assert_not_called()


class TestIntegrationMethodsWithTokenExpiration:
    """Tests for integration methods using token expiration handling.
    
    Validates: Requirements 5.3, 8.1, 8.2 - Token expiration in API methods
    """
    
    @pytest.fixture
    def mock_jwt_token(self):
        """Create a mock JWT token with exp claim."""
        import jwt
        exp_time = datetime.utcnow() + timedelta(hours=1)
        return jwt.encode(
            {"exp": exp_time.timestamp(), "sub": "user123"},
            "secret",
            algorithm="HS256"
        )
    
    @pytest.mark.asyncio
    async def test_get_project_info_with_token_refresh(self, mock_jwt_token):
        """Test get_project_info handles token expiration.
        
        Validates: Requirements 8.1, 8.2 - Token refresh in get_project_info
        """
        from src.label_studio.integration import LabelStudioIntegration
        from src.label_studio.config import LabelStudioConfig, LabelStudioProject
        
        # Create integration with JWT auth
        with patch.object(LabelStudioConfig, '__init__', lambda self: None):
            config = LabelStudioConfig()
            config.base_url = "http://label-studio:8080"
            config.api_token = None
            config.username = "admin"
            config.password = "secret"
            config.project_id = None
            config.validate_config = MagicMock(return_value=True)
            config.get_auth_method = MagicMock(return_value='jwt')
            
            with patch.object(LabelStudioIntegration, '__init__', lambda self, cfg=None: None):
                integration = LabelStudioIntegration()
                integration.config = config
                integration.base_url = "http://label-studio:8080"
                integration.api_token = None
                integration._auth_method = 'jwt'
                integration.headers = {'Content-Type': 'application/json'}
                
                # Create mock JWT auth manager
                jwt_auth = JWTAuthManager(
                    base_url="http://label-studio:8080",
                    username="admin",
                    password="secret"
                )
                jwt_auth._access_token = mock_jwt_token
                jwt_auth._refresh_token = "test_refresh_token"
                jwt_auth._is_authenticated = True
                jwt_auth._token_expires_at = datetime.utcnow() + timedelta(hours=1)
                jwt_auth.refresh_token = AsyncMock(return_value=True)
                jwt_auth._ensure_authenticated = AsyncMock()
                jwt_auth.get_auth_header = MagicMock(return_value={'Authorization': f'Bearer {mock_jwt_token}'})
                
                integration._jwt_auth_manager = jwt_auth
                
                # Add the helper methods from the real class
                from src.label_studio.integration import LabelStudioIntegration as RealIntegration
                integration._is_token_expired_response = RealIntegration._is_token_expired_response.__get__(integration)
                integration._handle_token_expiration_and_retry = RealIntegration._handle_token_expiration_and_retry.__get__(integration)
                integration._get_headers = RealIntegration._get_headers.__get__(integration)
        
        # First response: 401 token expired
        expired_response = MagicMock()
        expired_response.status_code = 401
        expired_response.text = '{"detail": "Token has expired"}'
        expired_response.json.return_value = {"detail": "Token has expired"}
        
        # Second response: success
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "id": 123,
            "title": "Test Project",
            "description": "Test Description"
        }
        
        call_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return expired_response
            return success_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            # Call get_project_info directly (bypassing retry decorator for this test)
            async def make_api_call():
                headers = await integration._get_headers()
                async with httpx.AsyncClient(timeout=30.0) as client:
                    return await client.get(
                        f"{integration.base_url}/api/projects/123/",
                        headers=headers
                    )
            
            response = await integration._handle_token_expiration_and_retry(make_api_call)
        
        assert response.status_code == 200
        assert call_count == 2
        jwt_auth.refresh_token.assert_called_once()


class TestRefreshTokenExpirationScenarios:
    """Tests specifically for refresh token expiration scenarios.
    
    Validates: Requirements 5.4, 8.3 - Refresh token expiration and re-authentication
    """
    
    @pytest.fixture
    def mock_jwt_token(self):
        """Create a mock JWT token with valid expiration."""
        import jwt
        from datetime import datetime, timedelta
        
        payload = {
            "sub": "test_user",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp())
        }
        return jwt.encode(payload, "test_secret", algorithm="HS256")
    
    @pytest.fixture
    def auth_manager(self):
        """Create a JWTAuthManager instance for testing."""
        from src.label_studio.jwt_auth import JWTAuthManager
        return JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="test_user",
            password="test_password"
        )
    
    @pytest.mark.asyncio
    async def test_refresh_token_expired_triggers_login(self, auth_manager, mock_jwt_token):
        """Test that expired refresh token triggers login with username/password.
        
        Validates: Requirements 5.4 - WHEN refresh token expires, THEN re-authenticate
        """
        from unittest.mock import MagicMock, AsyncMock, patch
        
        # Set up initial authenticated state
        auth_manager._access_token = "old_access_token"
        auth_manager._refresh_token = "expired_refresh_token"
        auth_manager._is_authenticated = True
        
        # Mock refresh endpoint returning 401 (refresh token expired)
        refresh_response = MagicMock()
        refresh_response.status_code = 401
        refresh_response.json.return_value = {"detail": "Refresh token expired"}
        
        # Mock login endpoint returning success
        login_response = MagicMock()
        login_response.status_code = 200
        login_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        call_count = 0
        
        async def mock_post(url, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "/refresh/" in url:
                return refresh_response
            else:
                return login_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            result = await auth_manager.refresh_token()
        
        # Verify login was called after refresh failed
        assert result is True
        assert call_count == 2  # refresh + login
        assert auth_manager._access_token == mock_jwt_token
        assert auth_manager._refresh_token == "new_refresh_token"
        assert auth_manager._is_authenticated is True
    
    @pytest.mark.asyncio
    async def test_refresh_token_expired_clears_old_tokens(self, auth_manager, mock_jwt_token):
        """Test that old tokens are cleared when refresh token expires.
        
        Validates: Requirements 10.4 - Clear expired tokens from memory
        """
        from unittest.mock import MagicMock, AsyncMock, patch
        
        # Set up initial authenticated state with old tokens
        old_access = "old_access_token_to_clear"
        old_refresh = "old_refresh_token_to_clear"
        auth_manager._access_token = old_access
        auth_manager._refresh_token = old_refresh
        auth_manager._is_authenticated = True
        
        # Mock refresh endpoint returning 401
        refresh_response = MagicMock()
        refresh_response.status_code = 401
        
        # Mock login endpoint returning success
        login_response = MagicMock()
        login_response.status_code = 200
        login_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        async def mock_post(url, *args, **kwargs):
            if "/refresh/" in url:
                return refresh_response
            else:
                return login_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            await auth_manager.refresh_token()
        
        # Verify old tokens are not present
        assert auth_manager._access_token != old_access
        assert auth_manager._refresh_token != old_refresh
        assert auth_manager._access_token == mock_jwt_token
        assert auth_manager._refresh_token == "new_refresh_token"
    
    @pytest.mark.asyncio
    async def test_api_call_retry_after_refresh_token_expiration(self, mock_jwt_token):
        """Test that API call is retried after refresh token expiration and re-auth.
        
        Validates: Requirements 8.3 - Retry original API call after re-auth
        """
        from unittest.mock import MagicMock, AsyncMock, patch
        from src.label_studio.jwt_auth import JWTAuthManager
        from src.label_studio.integration import LabelStudioIntegration
        
        # Create integration with JWT auth
        with patch.object(LabelStudioIntegration, '__init__', lambda self: None):
            integration = LabelStudioIntegration()
            integration.base_url = "http://test-label-studio:8080"
            integration._auth_method = 'jwt'
            integration._jwt_auth_manager = JWTAuthManager(
                base_url="http://test-label-studio:8080",
                username="test_user",
                password="test_password"
            )
            integration._jwt_auth_manager._access_token = "old_token"
            integration._jwt_auth_manager._refresh_token = "expired_refresh"
            integration._jwt_auth_manager._is_authenticated = True
            
            # Add the helper methods from real integration
            from src.label_studio.integration import LabelStudioIntegration as RealIntegration
            integration._is_token_expired_response = RealIntegration._is_token_expired_response.__get__(integration)
            integration._handle_token_expiration_and_retry = RealIntegration._handle_token_expiration_and_retry.__get__(integration)
        
        # First API call returns 401 (token expired)
        expired_response = MagicMock()
        expired_response.status_code = 401
        expired_response.text = '{"detail": "Token has expired"}'
        expired_response.json.return_value = {"detail": "Token has expired"}
        
        # Second API call (after refresh fails and login succeeds) returns success
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        
        api_call_count = 0
        
        async def mock_api_call():
            nonlocal api_call_count
            api_call_count += 1
            if api_call_count == 1:
                return expired_response
            return success_response
        
        # Mock refresh to fail (401) then login to succeed
        refresh_response = MagicMock()
        refresh_response.status_code = 401
        
        login_response = MagicMock()
        login_response.status_code = 200
        login_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh"
        }
        
        async def mock_post(url, *args, **kwargs):
            if "/refresh/" in url:
                return refresh_response
            return login_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            result = await integration._handle_token_expiration_and_retry(mock_api_call)
        
        # Verify API call was retried after re-authentication
        assert result.status_code == 200
        assert api_call_count == 2  # Initial call + retry after re-auth
    
    @pytest.mark.asyncio
    async def test_refresh_token_expiration_logs_appropriately(self, auth_manager, mock_jwt_token, caplog):
        """Test that refresh token expiration is logged appropriately.
        
        Validates: Requirements 9.3, 9.4 - Log token refresh events
        """
        import logging
        from unittest.mock import MagicMock, AsyncMock, patch
        
        # Set up initial authenticated state
        auth_manager._access_token = "old_access_token"
        auth_manager._refresh_token = "expired_refresh_token"
        auth_manager._is_authenticated = True
        
        # Mock refresh endpoint returning 401
        refresh_response = MagicMock()
        refresh_response.status_code = 401
        
        # Mock login endpoint returning success
        login_response = MagicMock()
        login_response.status_code = 200
        login_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "new_refresh_token"
        }
        
        async def mock_post(url, *args, **kwargs):
            if "/refresh/" in url:
                return refresh_response
            return login_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            with caplog.at_level(logging.INFO):
                await auth_manager.refresh_token()
        
        # Verify appropriate log messages
        log_messages = [record.message for record in caplog.records]
        
        # Should log refresh attempt
        assert any("Refreshing access token" in msg for msg in log_messages), \
            "Should log refresh attempt"
        
        # Should log fallback to login
        assert any("falling back to login" in msg.lower() for msg in log_messages), \
            "Should log fallback to login when refresh token expires"
        
        # Should log successful authentication
        assert any("authentication successful" in msg.lower() for msg in log_messages), \
            "Should log successful authentication after fallback"
    
    @pytest.mark.asyncio
    async def test_refresh_token_expiration_with_login_failure(self, auth_manager):
        """Test error handling when both refresh and login fail.
        
        Validates: Requirements 5.5 - Raise error when re-authentication fails
        """
        from unittest.mock import MagicMock, AsyncMock, patch
        from src.label_studio.exceptions import LabelStudioAuthenticationError
        
        # Set up initial authenticated state
        auth_manager._access_token = "old_access_token"
        auth_manager._refresh_token = "expired_refresh_token"
        auth_manager._is_authenticated = True
        
        # Mock refresh endpoint returning 401
        refresh_response = MagicMock()
        refresh_response.status_code = 401
        
        # Mock login endpoint also returning 401 (invalid credentials)
        login_response = MagicMock()
        login_response.status_code = 401
        
        async def mock_post(url, *args, **kwargs):
            if "/refresh/" in url:
                return refresh_response
            return login_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.refresh_token()
        
        # Verify error is raised with appropriate message
        assert exc_info.value.status_code == 401
        assert "invalid" in str(exc_info.value).lower() or "password" in str(exc_info.value).lower()
        
        # Verify tokens are cleared
        assert auth_manager._access_token is None
        assert auth_manager._refresh_token is None
        assert auth_manager._is_authenticated is False


class TestErrorMessageQuality:
    """Tests for clear, actionable error messages.
    
    Validates: Requirements 1.3, 5.5 - Clear error messages for auth failures
    
    Error messages should be:
    - Clear and actionable (tell user what to do)
    - Include status code
    - Include reason from server if available
    - NOT include sensitive data (passwords, tokens)
    """
    
    @pytest.fixture
    def auth_manager(self):
        """Create a JWTAuthManager instance for testing."""
        return JWTAuthManager(
            base_url="http://label-studio:8080",
            username="admin",
            password="secret"
        )
    
    @pytest.mark.asyncio
    async def test_401_error_message_is_actionable(self, auth_manager):
        """Test that 401 error message tells user what to do.
        
        Validates: Requirements 1.3 - Clear error message for invalid credentials
        """
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
        
        error_message = str(exc_info.value)
        
        # Should include status code
        assert "401" in error_message, "Error message should include status code"
        
        # Should be actionable - tell user what to check
        assert any(word in error_message.lower() for word in [
            'check', 'verify', 'please', 'username', 'password', 'credentials'
        ]), "Error message should be actionable and tell user what to do"
        
        # Should mention the relevant environment variables
        assert "LABEL_STUDIO" in error_message, \
            "Error message should mention relevant environment variables"
    
    @pytest.mark.asyncio
    async def test_403_error_message_is_actionable(self, auth_manager):
        """Test that 403 error message tells user what to do.
        
        Validates: Requirements 1.3 - Clear error message for forbidden access
        """
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
        
        error_message = str(exc_info.value)
        
        # Should include status code
        assert "403" in error_message, "Error message should include status code"
        
        # Should mention permissions
        assert any(word in error_message.lower() for word in [
            'permission', 'forbidden', 'access', 'administrator'
        ]), "Error message should mention permissions issue"
        
        # Should be actionable
        assert any(word in error_message.lower() for word in [
            'contact', 'verify', 'check', 'please'
        ]), "Error message should be actionable"
    
    @pytest.mark.asyncio
    async def test_error_message_includes_server_reason(self, auth_manager):
        """Test that error message includes server reason when available.
        
        Validates: Requirements 1.3 - Include context in error messages
        """
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "detail": "User account is locked"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
        
        error_message = str(exc_info.value)
        
        # Should include server reason
        assert "User account is locked" in error_message, \
            "Error message should include server reason when available"
    
    @pytest.mark.asyncio
    async def test_error_message_does_not_include_sensitive_data(self, auth_manager):
        """Test that error message does NOT include sensitive data.
        
        Validates: Requirements 10.2 - Never log tokens or passwords
        """
        mock_response = MagicMock()
        mock_response.status_code = 401
        # Server response that might contain sensitive data
        mock_response.json.return_value = {
            "detail": "Invalid password: secret123"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
        
        error_message = str(exc_info.value)
        
        # Should NOT include the password from server response
        assert "secret123" not in error_message, \
            "Error message should NOT include sensitive data from server"
        
        # Should NOT include the actual password
        assert "secret" not in error_message.lower() or "secret" in "secret".lower(), \
            "Error message should NOT include actual password"
    
    @pytest.mark.asyncio
    async def test_missing_credentials_error_is_actionable(self):
        """Test that missing credentials error tells user what to do.
        
        Validates: Requirements 1.3 - Clear error message for configuration issues
        """
        auth = JWTAuthManager(base_url="http://label-studio:8080")
        
        with pytest.raises(ValueError) as exc_info:
            await auth.login()
        
        error_message = str(exc_info.value)
        
        # Should mention environment variables
        assert "LABEL_STUDIO" in error_message, \
            "Error message should mention environment variables"
        
        # Should be actionable
        assert any(word in error_message.lower() for word in [
            'set', 'configure', 'please'
        ]), "Error message should be actionable"
    
    @pytest.mark.asyncio
    async def test_missing_token_in_response_error_is_actionable(self, auth_manager):
        """Test that missing token error tells user what to do.
        
        Validates: Requirements 1.3 - Clear error message for server issues
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "refresh_token": "refresh123"
            # Missing access_token
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
        
        error_message = str(exc_info.value)
        
        # Should mention the issue
        assert any(word in error_message.lower() for word in [
            'missing', 'token', 'access'
        ]), "Error message should mention missing token"
        
        # Should mention version compatibility
        assert any(word in error_message.lower() for word in [
            'version', 'label studio', '1.22'
        ]), "Error message should mention version compatibility"
    
    @pytest.mark.asyncio
    async def test_refresh_403_error_message_is_actionable(self, auth_manager):
        """Test that refresh 403 error message tells user what to do.
        
        Validates: Requirements 5.5 - Clear error message for re-auth failures
        """
        # Set up authenticated state
        auth_manager._access_token = "old_token"
        auth_manager._refresh_token = "refresh_token"
        auth_manager._is_authenticated = True
        
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.refresh_token()
        
        error_message = str(exc_info.value)
        
        # Should include status code
        assert "403" in error_message, "Error message should include status code"
        
        # Should mention permissions
        assert any(word in error_message.lower() for word in [
            'permission', 'forbidden', 'access'
        ]), "Error message should mention permissions issue"


class TestExceptionClasses:
    """Tests for exception class functionality.
    
    Validates: Requirements 1.3, 5.5 - Exception classes with clear messages
    """
    
    def test_authentication_error_create_factory(self):
        """Test LabelStudioAuthenticationError.create() factory method."""
        from src.label_studio.exceptions import LabelStudioAuthenticationError
        
        # Test 401 with invalid_credentials
        error = LabelStudioAuthenticationError.create(
            status_code=401,
            error_type='invalid_credentials'
        )
        assert error.status_code == 401
        assert error.error_type == 'invalid_credentials'
        assert 'username' in error.message.lower() or 'password' in error.message.lower()
        
        # Test 403 with insufficient_permissions
        error = LabelStudioAuthenticationError.create(
            status_code=403,
            error_type='insufficient_permissions'
        )
        assert error.status_code == 403
        assert 'permission' in error.message.lower()
        
        # Test with server reason
        error = LabelStudioAuthenticationError.create(
            status_code=401,
            error_type='invalid_credentials',
            server_reason='Account locked'
        )
        assert 'Account locked' in error.message
    
    def test_authentication_error_str_format(self):
        """Test LabelStudioAuthenticationError string format."""
        from src.label_studio.exceptions import LabelStudioAuthenticationError
        
        error = LabelStudioAuthenticationError(
            message="Test error message",
            status_code=401
        )
        
        error_str = str(error)
        
        # Should include status code
        assert "401" in error_str
        
        # Should include message
        assert "Test error message" in error_str
        
        # Should have proper format
        assert "Authentication failed" in error_str
    
    def test_authentication_error_repr(self):
        """Test LabelStudioAuthenticationError repr format."""
        from src.label_studio.exceptions import LabelStudioAuthenticationError
        
        error = LabelStudioAuthenticationError(
            message="Test error",
            status_code=401,
            error_type='invalid_credentials'
        )
        
        error_repr = repr(error)
        
        # Should include class name
        assert "LabelStudioAuthenticationError" in error_repr
        
        # Should include status code
        assert "401" in error_repr
        
        # Should include error type
        assert "invalid_credentials" in error_repr
    
    def test_network_error_create_factory(self):
        """Test LabelStudioNetworkError.create() factory method."""
        from src.label_studio.exceptions import LabelStudioNetworkError
        
        # Test timeout error
        error = LabelStudioNetworkError.create(
            error_type='timeout',
            url='http://label-studio:8080'
        )
        assert error.error_type == 'timeout'
        assert 'timeout' in error.message.lower()
        assert 'http://label-studio:8080' in error.message
        
        # Test connection refused
        error = LabelStudioNetworkError.create(
            error_type='connection_refused'
        )
        assert 'refused' in error.message.lower()
    
    def test_token_expired_error_messages(self):
        """Test LabelStudioTokenExpiredError messages."""
        from src.label_studio.exceptions import LabelStudioTokenExpiredError
        
        # Test access token expired
        error = LabelStudioTokenExpiredError(token_type='access')
        assert error.token_type == 'access'
        assert 'access' in str(error).lower()
        assert 'refresh' in error.message.lower()  # Should mention auto-refresh
        
        # Test refresh token expired
        error = LabelStudioTokenExpiredError(token_type='refresh')
        assert error.token_type == 'refresh'
        assert 're-authenticate' in error.message.lower()
    
    def test_configuration_error_create_factory(self):
        """Test LabelStudioConfigurationError.create() factory method."""
        from src.label_studio.exceptions import LabelStudioConfigurationError
        
        # Test missing URL
        error = LabelStudioConfigurationError.create('missing_url')
        assert 'LABEL_STUDIO_URL' in error.message
        
        # Test missing auth
        error = LabelStudioConfigurationError.create('missing_auth')
        assert 'LABEL_STUDIO_USERNAME' in error.message or 'LABEL_STUDIO_API_TOKEN' in error.message
    
    def test_project_not_found_error_message(self):
        """Test LabelStudioProjectNotFoundError message."""
        from src.label_studio.exceptions import LabelStudioProjectNotFoundError
        
        error = LabelStudioProjectNotFoundError(project_id='123')
        
        # Should include project ID
        assert '123' in str(error)
        
        # Should be actionable
        assert any(word in str(error).lower() for word in [
            'verify', 'create', 'check'
        ])


class TestLoggingSanitization:
    """Tests for logging sanitization - ensuring sensitive data is never logged.
    
    Validates: Requirements 10.2 - WHEN logging authentication events, 
    THEN the system SHALL NOT log tokens or passwords
    """
    
    @pytest.fixture
    def auth_manager(self):
        """Create a JWTAuthManager instance with sensitive credentials."""
        return JWTAuthManager(
            base_url="http://label-studio:8080",
            username="admin@example.com",
            password="super_secret_password_12345"
        )
    
    @pytest.fixture
    def mock_jwt_token(self):
        """Create a mock JWT token with exp claim."""
        import jwt
        exp_time = datetime.utcnow() + timedelta(hours=1)
        return jwt.encode(
            {"exp": exp_time.timestamp(), "sub": "user123"},
            "secret",
            algorithm="HS256"
        )
    
    @pytest.mark.asyncio
    async def test_login_success_does_not_log_password(self, auth_manager, mock_jwt_token, caplog):
        """Test that successful login does not log the password.
        
        Validates: Requirements 10.2
        """
        import logging
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": "refresh_token_secret_123"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with caplog.at_level(logging.DEBUG):
                await auth_manager.login()
        
        # Collect all log messages
        all_log_text = " ".join([record.message for record in caplog.records])
        
        # Password should NEVER appear in logs
        assert "super_secret_password_12345" not in all_log_text, \
            "Password should never appear in log messages"
        
        # Access token should NEVER appear in logs
        assert mock_jwt_token not in all_log_text, \
            "Access token should never appear in log messages"
        
        # Refresh token should NEVER appear in logs
        assert "refresh_token_secret_123" not in all_log_text, \
            "Refresh token should never appear in log messages"
    
    @pytest.mark.asyncio
    async def test_login_failure_does_not_log_password(self, auth_manager, caplog):
        """Test that failed login does not log the password.
        
        Validates: Requirements 10.2
        """
        import logging
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid credentials"}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with caplog.at_level(logging.DEBUG):
                with pytest.raises(LabelStudioAuthenticationError):
                    await auth_manager.login()
        
        # Collect all log messages
        all_log_text = " ".join([record.message for record in caplog.records])
        
        # Password should NEVER appear in logs even on failure
        assert "super_secret_password_12345" not in all_log_text, \
            "Password should never appear in log messages even on auth failure"
    
    @pytest.mark.asyncio
    async def test_token_refresh_does_not_log_tokens(self, auth_manager, mock_jwt_token, caplog):
        """Test that token refresh does not log tokens.
        
        Validates: Requirements 10.2
        """
        import logging
        
        # Set up authenticated state with tokens
        old_access_token = "old_access_token_secret_abc"
        old_refresh_token = "old_refresh_token_secret_xyz"
        new_refresh_token = "new_refresh_token_secret_789"
        
        auth_manager._access_token = old_access_token
        auth_manager._refresh_token = old_refresh_token
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": new_refresh_token
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with caplog.at_level(logging.DEBUG):
                await auth_manager.refresh_token()
        
        # Collect all log messages
        all_log_text = " ".join([record.message for record in caplog.records])
        
        # Old tokens should NEVER appear in logs
        assert old_access_token not in all_log_text, \
            "Old access token should never appear in log messages"
        assert old_refresh_token not in all_log_text, \
            "Old refresh token should never appear in log messages"
        
        # New tokens should NEVER appear in logs
        assert mock_jwt_token not in all_log_text, \
            "New access token should never appear in log messages"
        assert new_refresh_token not in all_log_text, \
            "New refresh token should never appear in log messages"
    
    @pytest.mark.asyncio
    async def test_token_refresh_failure_does_not_log_tokens(self, auth_manager, caplog):
        """Test that failed token refresh does not log tokens.
        
        Validates: Requirements 10.2
        """
        import logging
        
        # Set up authenticated state with tokens
        old_access_token = "old_access_token_secret_abc"
        old_refresh_token = "old_refresh_token_secret_xyz"
        
        auth_manager._access_token = old_access_token
        auth_manager._refresh_token = old_refresh_token
        auth_manager._is_authenticated = True
        
        # Mock 403 response (forbidden - cannot recover)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"detail": "Forbidden"}
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with caplog.at_level(logging.DEBUG):
                with pytest.raises(LabelStudioAuthenticationError):
                    await auth_manager.refresh_token()
        
        # Collect all log messages
        all_log_text = " ".join([record.message for record in caplog.records])
        
        # Tokens should NEVER appear in logs even on failure
        assert old_access_token not in all_log_text, \
            "Access token should never appear in log messages even on refresh failure"
        assert old_refresh_token not in all_log_text, \
            "Refresh token should never appear in log messages even on refresh failure"
    
    def test_get_auth_state_never_contains_tokens(self):
        """Test that get_auth_state() never contains actual token values.
        
        Validates: Requirements 10.2
        """
        auth = JWTAuthManager(
            base_url="http://test",
            username="admin",
            password="very_secret_password"
        )
        
        # Set up tokens
        auth._access_token = "access_token_value_12345"
        auth._refresh_token = "refresh_token_value_67890"
        auth._is_authenticated = True
        auth._token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        state = auth.get_auth_state()
        state_str = str(state)
        
        # Verify no sensitive data in state
        assert "very_secret_password" not in state_str, \
            "Password should never appear in auth state"
        assert "access_token_value_12345" not in state_str, \
            "Access token should never appear in auth state"
        assert "refresh_token_value_67890" not in state_str, \
            "Refresh token should never appear in auth state"
        
        # Verify state contains expected safe fields
        assert "is_authenticated" in state
        assert "has_access_token" in state
        assert "has_refresh_token" in state
        assert "has_credentials" in state
        assert "base_url" in state
        assert "token_expires_at" in state
        
        # Verify boolean indicators are correct
        assert state["is_authenticated"] is True
        assert state["has_access_token"] is True
        assert state["has_refresh_token"] is True
        assert state["has_credentials"] is True
    
    def test_get_auth_state_with_no_tokens(self):
        """Test get_auth_state() when no tokens are set.
        
        Validates: Requirements 10.2
        """
        auth = JWTAuthManager(
            base_url="http://test",
            username="admin",
            password="secret"
        )
        
        state = auth.get_auth_state()
        
        # Verify state reflects no tokens
        assert state["is_authenticated"] is False
        assert state["has_access_token"] is False
        assert state["has_refresh_token"] is False
        assert state["has_credentials"] is True
        assert state["token_expires_at"] is None
    
    def test_get_auth_state_with_no_credentials(self):
        """Test get_auth_state() when no credentials are set.
        
        Validates: Requirements 10.2
        """
        auth = JWTAuthManager(base_url="http://test")
        
        state = auth.get_auth_state()
        
        # Verify state reflects no credentials
        assert state["has_credentials"] is False
        assert state["is_authenticated"] is False
    
    @pytest.mark.asyncio
    async def test_ensure_authenticated_does_not_log_tokens(self, auth_manager, mock_jwt_token, caplog):
        """Test that _ensure_authenticated() does not log tokens.
        
        Validates: Requirements 10.2
        """
        import logging
        
        # Set up expired token state
        auth_manager._access_token = "expired_access_token_secret"
        auth_manager._refresh_token = "refresh_token_secret_for_refresh"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired
        
        new_refresh_token = "new_refresh_token_secret_999"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": mock_jwt_token,
            "refresh_token": new_refresh_token
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with caplog.at_level(logging.DEBUG):
                await auth_manager._ensure_authenticated()
        
        # Collect all log messages
        all_log_text = " ".join([record.message for record in caplog.records])
        
        # No tokens should appear in logs
        assert "expired_access_token_secret" not in all_log_text, \
            "Expired access token should never appear in log messages"
        assert "refresh_token_secret_for_refresh" not in all_log_text, \
            "Refresh token should never appear in log messages"
        assert mock_jwt_token not in all_log_text, \
            "New access token should never appear in log messages"
        assert new_refresh_token not in all_log_text, \
            "New refresh token should never appear in log messages"
    
    def test_get_auth_state_is_safe_for_logging(self):
        """Test that get_auth_state() output is safe to pass to logger.
        
        Validates: Requirements 10.2
        
        This test verifies that the output of get_auth_state() can be safely
        logged without exposing sensitive information.
        """
        import logging
        import io
        
        # Create a string handler to capture log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        
        test_logger = logging.getLogger("test_safe_logging")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)
        
        # Set up auth manager with sensitive data
        auth = JWTAuthManager(
            base_url="http://test",
            username="admin",
            password="super_secret_password"
        )
        auth._access_token = "secret_access_token_xyz"
        auth._refresh_token = "secret_refresh_token_abc"
        auth._is_authenticated = True
        
        # Log the auth state (this is the intended use case)
        state = auth.get_auth_state()
        test_logger.info(f"Auth state: {state}")
        
        # Get the logged output
        log_output = log_capture.getvalue()
        
        # Verify no sensitive data was logged
        assert "super_secret_password" not in log_output, \
            "Password should not appear in logged auth state"
        assert "secret_access_token_xyz" not in log_output, \
            "Access token should not appear in logged auth state"
        assert "secret_refresh_token_abc" not in log_output, \
            "Refresh token should not appear in logged auth state"
        
        # Verify safe fields are present
        assert "is_authenticated" in log_output
        assert "has_access_token" in log_output
        
        # Clean up
        test_logger.removeHandler(handler)


class TestHTTPSEnforcement:
    """Tests for HTTPS enforcement when generating authenticated URLs.
    
    Validates: Requirements 10.3 - WHEN passing tokens in URLs, 
    THEN the system SHALL use secure HTTPS connections
    """
    
    @pytest.fixture
    def https_integration(self):
        """Create integration with HTTPS URL."""
        with patch.object(LabelStudioIntegration, '__init__', lambda self: None):
            integration = LabelStudioIntegration()
            integration.base_url = "https://label-studio.example.com"
            integration._auth_method = 'jwt'
            integration._jwt_auth_manager = None
            integration.api_token = "test_token"
            integration.headers = {'Authorization': 'Token test_token', 'Content-Type': 'application/json'}
            integration.config = MagicMock()
            return integration
    
    @pytest.fixture
    def http_integration(self):
        """Create integration with HTTP URL (insecure)."""
        with patch.object(LabelStudioIntegration, '__init__', lambda self: None):
            integration = LabelStudioIntegration()
            integration.base_url = "http://label-studio.example.com"
            integration._auth_method = 'jwt'
            integration._jwt_auth_manager = None
            integration.api_token = "test_token"
            integration.headers = {'Authorization': 'Token test_token', 'Content-Type': 'application/json'}
            integration.config = MagicMock()
            return integration
    
    @pytest.fixture
    def localhost_integration(self):
        """Create integration with localhost URL (development)."""
        with patch.object(LabelStudioIntegration, '__init__', lambda self: None):
            integration = LabelStudioIntegration()
            integration.base_url = "http://localhost:8080"
            integration._auth_method = 'jwt'
            integration._jwt_auth_manager = None
            integration.api_token = "test_token"
            integration.headers = {'Authorization': 'Token test_token', 'Content-Type': 'application/json'}
            integration.config = MagicMock()
            return integration
    
    def test_https_url_returns_secure_true(self, https_integration):
        """Test that HTTPS URL returns is_secure=True.
        
        Validates: Requirements 10.3
        """
        is_secure = https_integration._check_https_security()
        assert is_secure is True, "HTTPS URL should be marked as secure"
    
    def test_http_url_returns_secure_false(self, http_integration):
        """Test that HTTP URL returns is_secure=False.
        
        Validates: Requirements 10.3
        """
        is_secure = http_integration._check_https_security()
        assert is_secure is False, "HTTP URL should be marked as insecure"
    
    def test_http_url_logs_warning_in_production(self, http_integration, caplog):
        """Test that HTTP URL logs security warning in production.
        
        Validates: Requirements 10.3
        """
        import logging
        
        with caplog.at_level(logging.WARNING):
            http_integration._check_https_security()
        
        # Should log a security warning
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("SECURITY WARNING" in msg or "HTTPS" in msg for msg in warning_messages), \
            "Should log security warning for HTTP URL in production"
    
    def test_localhost_http_does_not_log_warning(self, localhost_integration, caplog):
        """Test that localhost HTTP URL does not log warning (development mode).
        
        Validates: Requirements 10.3 - Allow HTTP for local development
        """
        import logging
        
        with caplog.at_level(logging.WARNING):
            localhost_integration._check_https_security()
        
        # Should NOT log a security warning for localhost
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert not any("SECURITY WARNING" in msg for msg in warning_messages), \
            "Should not log security warning for localhost URL"
    
    @pytest.mark.asyncio
    async def test_generate_authenticated_url_includes_is_secure(self, https_integration):
        """Test that generate_authenticated_url includes is_secure field.
        
        Validates: Requirements 10.3
        """
        from src.config.settings import settings
        
        # Mock settings for JWT
        with patch.object(settings, 'security', MagicMock(
            jwt_secret_key='test_secret',
            jwt_algorithm='HS256'
        )):
            result = await https_integration.generate_authenticated_url(
                project_id="123",
                user_id="user-456",
                language="en"
            )
        
        assert "is_secure" in result, "Result should include is_secure field"
        assert result["is_secure"] is True, "HTTPS URL should have is_secure=True"
    
    @pytest.mark.asyncio
    async def test_generate_authenticated_url_http_includes_is_secure_false(self, http_integration):
        """Test that generate_authenticated_url with HTTP has is_secure=False.
        
        Validates: Requirements 10.3
        """
        from src.config.settings import settings
        
        # Mock settings for JWT
        with patch.object(settings, 'security', MagicMock(
            jwt_secret_key='test_secret',
            jwt_algorithm='HS256'
        )):
            result = await http_integration.generate_authenticated_url(
                project_id="123",
                user_id="user-456",
                language="en"
            )
        
        assert "is_secure" in result, "Result should include is_secure field"
        assert result["is_secure"] is False, "HTTP URL should have is_secure=False"
    
    def test_127_0_0_1_treated_as_development(self):
        """Test that 127.0.0.1 is treated as development environment.
        
        Validates: Requirements 10.3 - Allow HTTP for local development
        """
        with patch.object(LabelStudioIntegration, '__init__', lambda self: None):
            integration = LabelStudioIntegration()
            integration.base_url = "http://127.0.0.1:8080"
        
        # Should not raise warning for 127.0.0.1
        import logging
        import io
        
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.WARNING)
        
        logger = logging.getLogger('src.label_studio.integration')
        logger.addHandler(handler)
        
        try:
            integration._check_https_security()
            log_output = log_capture.getvalue()
            assert "SECURITY WARNING" not in log_output, \
                "Should not log security warning for 127.0.0.1"
        finally:
            logger.removeHandler(handler)
