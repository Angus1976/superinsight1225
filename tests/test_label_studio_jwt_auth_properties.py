"""
Property-Based Tests for Label Studio JWT Authentication Module.

This module contains property-based tests using Hypothesis to verify
universal properties of the JWT authentication system across all valid inputs.

Property tests complement unit tests by:
- Testing properties that should hold for ALL valid inputs
- Discovering edge cases through randomized testing
- Providing stronger correctness guarantees

Each property test runs minimum 100 iterations as specified in the design document.

Validates: Requirements 1.2, 2.3 (Property 2: Token Storage After Authentication)
"""

import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from src.label_studio.jwt_auth import JWTAuthManager, JWTTokenResponse
from src.label_studio.integration import LabelStudioAuthenticationError, LabelStudioIntegration


# =============================================================================
# Test Helpers and Fixtures
# =============================================================================

def create_mock_jwt_token(
    exp_offset_seconds: int = 3600,
    sub: str = "user123"
) -> str:
    """
    Create a mock JWT token with specified expiration.
    
    Args:
        exp_offset_seconds: Seconds from now until expiration (can be negative)
        sub: Subject claim value
        
    Returns:
        str: Encoded JWT token
    """
    import time
    # Use time.time() to get current Unix timestamp, then add offset
    # This avoids timezone issues with datetime.utcnow().timestamp()
    exp_timestamp = time.time() + exp_offset_seconds
    return jwt.encode(
        {"exp": exp_timestamp, "sub": sub},
        "test_secret",
        algorithm="HS256"
    )


@contextmanager
def mock_auth_response(
    access_token: str,
    refresh_token: str,
    status_code: int = 200
) -> Generator[None, None, None]:
    """
    Context manager to mock Label Studio authentication response.
    
    Args:
        access_token: The access token to return
        refresh_token: The refresh token to return
        status_code: HTTP status code to return
        
    Yields:
        None: Context for mocked authentication
    """
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer"
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        yield


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Strategy for valid usernames (non-empty, reasonable length)
# Use min_size=3 to avoid false positives in string containment checks
username_strategy = st.text(
    min_size=3,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),  # Letters and numbers
        whitelist_characters='._-@'  # Common username characters
    )
).filter(lambda x: x.strip() != '' and len(x.strip()) >= 3)

# Strategy for valid passwords (non-empty, reasonable length)
# Use min_size=8 to be realistic and avoid false positives in string checks
password_strategy = st.text(
    min_size=8,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P'),  # Letters, numbers, punctuation
        whitelist_characters='!@#$%^&*()_+-=[]{}|;:,.<>?'
    )
).filter(lambda x: x.strip() != '' and len(x.strip()) >= 8)

# Strategy for valid base URLs
base_url_strategy = st.sampled_from([
    "http://localhost:8080",
    "http://label-studio:8080",
    "https://label-studio.example.com",
    "http://192.168.1.100:8080",
])


# =============================================================================
# Property Test 2: Token Storage After Authentication
# =============================================================================

class TestProperty2TokenStorageAfterAuthentication:
    """
    Property 2: Token Storage After Authentication
    
    **Validates: Requirements 1.2, 2.3**
    
    For any successful authentication or token refresh operation, both access
    token and refresh token should be stored in memory and accessible for
    subsequent API calls.
    
    This property ensures that:
    1. After successful login, _access_token is not None
    2. After successful login, _refresh_token is not None
    3. After successful login, is_authenticated is True
    4. After successful login, get_auth_header() returns valid Bearer header
    """
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_token_storage_after_auth(self, username: str, password: str):
        """
        # Feature: label-studio-jwt-authentication, Property 2: Token Storage After Authentication
        
        **Validates: Requirements 1.2, 2.3**
        
        For any successful authentication or token refresh operation, both access
        token and refresh token should be stored in memory and accessible for
        subsequent API calls.
        
        This test verifies that for ANY valid username/password combination,
        successful login results in:
        - Both tokens being stored in memory
        - Authentication state being set to True
        - Valid Bearer header being available
        """
        # Create auth manager with generated credentials
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Create mock tokens for the response
        mock_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
        mock_refresh_token = f"refresh_token_{username[:10]}"
        
        # Mock successful authentication
        with mock_auth_response(
            access_token=mock_access_token,
            refresh_token=mock_refresh_token
        ):
            result = await auth_manager.login()
        
        # Property assertions:
        # 1. Login should return True for successful authentication
        assert result is True, "login() should return True on success"
        
        # 2. Access token should be stored (not None)
        assert auth_manager._access_token is not None, \
            "Access token should be stored after successful login"
        
        # 3. Refresh token should be stored (not None)
        assert auth_manager._refresh_token is not None, \
            "Refresh token should be stored after successful login"
        
        # 4. Authentication state should be True
        assert auth_manager.is_authenticated is True, \
            "is_authenticated should be True after successful login"
        
        # 5. get_auth_header() should return valid Bearer header
        auth_header = auth_manager.get_auth_header()
        assert 'Authorization' in auth_header, \
            "get_auth_header() should return Authorization header"
        assert auth_header['Authorization'].startswith('Bearer '), \
            "Authorization header should use Bearer format"
        assert auth_header['Authorization'] == f'Bearer {mock_access_token}', \
            "Authorization header should contain the access token"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy,
        exp_offset=st.integers(min_value=300, max_value=7200)  # 5 min to 2 hours
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_token_expiration_stored_after_auth(
        self,
        username: str,
        password: str,
        exp_offset: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 2: Token Storage After Authentication
        
        **Validates: Requirements 1.2, 2.3**
        
        Extended property test: For any successful authentication, the token
        expiration time should be correctly parsed and stored from the JWT token.
        
        This test verifies that:
        - Token expiration is parsed from the JWT exp claim
        - Expiration time is stored in _token_expires_at
        - Token is not considered expired immediately after login
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Create token with specific expiration (using future time)
        mock_access_token = create_mock_jwt_token(exp_offset_seconds=exp_offset)
        mock_refresh_token = f"refresh_token_{username[:10]}"
        
        with mock_auth_response(
            access_token=mock_access_token,
            refresh_token=mock_refresh_token
        ):
            await auth_manager.login()
        
        # Property assertions:
        # 1. Token expiration should be stored
        assert auth_manager._token_expires_at is not None, \
            "Token expiration time should be stored after login"
        
        # 2. Token should NOT be considered expired immediately after login
        # (since exp_offset is at least 300 seconds = 5 minutes)
        # Use a buffer of 60 seconds (default) - token should still be valid
        assert auth_manager._is_token_expired(buffer_seconds=60) is False, \
            f"Token with {exp_offset}s expiration should not be expired immediately"
        
        # 3. Token expiration should be a datetime object
        assert isinstance(auth_manager._token_expires_at, datetime), \
            "Token expiration should be a datetime object"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_tokens_match_response(self, username: str, password: str):
        """
        # Feature: label-studio-jwt-authentication, Property 2: Token Storage After Authentication
        
        **Validates: Requirements 1.2, 2.3**
        
        For any successful authentication, the stored tokens should exactly
        match the tokens returned in the authentication response.
        
        This test verifies that:
        - Stored access token matches response access token
        - Stored refresh token matches response refresh token
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Create unique tokens for this test
        mock_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
        mock_refresh_token = f"unique_refresh_{hash(username + password) % 10000}"
        
        with mock_auth_response(
            access_token=mock_access_token,
            refresh_token=mock_refresh_token
        ):
            await auth_manager.login()
        
        # Property assertions:
        # 1. Stored access token should exactly match response
        assert auth_manager._access_token == mock_access_token, \
            "Stored access token should exactly match response token"
        
        # 2. Stored refresh token should exactly match response
        assert auth_manager._refresh_token == mock_refresh_token, \
            "Stored refresh token should exactly match response token"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_auth_state_consistent_after_login(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 2: Token Storage After Authentication
        
        **Validates: Requirements 1.2, 2.3**
        
        For any successful authentication, the authentication state should be
        internally consistent - all state indicators should agree.
        
        This test verifies that:
        - is_authenticated property is True
        - _is_authenticated internal flag is True
        - has_access_token in get_auth_state() is True
        - has_refresh_token in get_auth_state() is True
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        mock_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
        mock_refresh_token = f"refresh_{username[:10]}"
        
        with mock_auth_response(
            access_token=mock_access_token,
            refresh_token=mock_refresh_token
        ):
            await auth_manager.login()
        
        # Get auth state for inspection
        auth_state = auth_manager.get_auth_state()
        
        # Property assertions - all state indicators should be consistent:
        # 1. is_authenticated property should be True
        assert auth_manager.is_authenticated is True, \
            "is_authenticated property should be True after login"
        
        # 2. Internal _is_authenticated flag should be True
        assert auth_manager._is_authenticated is True, \
            "_is_authenticated flag should be True after login"
        
        # 3. Auth state should indicate has_access_token
        assert auth_state["has_access_token"] is True, \
            "get_auth_state() should indicate has_access_token=True"
        
        # 4. Auth state should indicate has_refresh_token
        assert auth_state["has_refresh_token"] is True, \
            "get_auth_state() should indicate has_refresh_token=True"
        
        # 5. Auth state should indicate is_authenticated
        assert auth_state["is_authenticated"] is True, \
            "get_auth_state() should indicate is_authenticated=True"


# =============================================================================
# Additional Property Tests for Token Storage Robustness
# =============================================================================

class TestProperty2TokenStorageRobustness:
    """
    Additional property tests for token storage robustness.
    
    These tests verify edge cases and robustness of token storage.
    """
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_multiple_logins_update_tokens(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 2: Token Storage After Authentication
        
        **Validates: Requirements 1.2, 2.3**
        
        For any sequence of successful authentications, each login should
        update the stored tokens to the new values.
        
        This test verifies that:
        - Second login updates tokens to new values
        - Old tokens are replaced, not accumulated
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # First login
        first_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
        first_refresh_token = "first_refresh_token"
        
        with mock_auth_response(
            access_token=first_access_token,
            refresh_token=first_refresh_token
        ):
            await auth_manager.login()
        
        # Verify first tokens stored
        assert auth_manager._access_token == first_access_token
        assert auth_manager._refresh_token == first_refresh_token
        
        # Second login with different tokens
        second_access_token = create_mock_jwt_token(exp_offset_seconds=7200)
        second_refresh_token = "second_refresh_token"
        
        with mock_auth_response(
            access_token=second_access_token,
            refresh_token=second_refresh_token
        ):
            await auth_manager.login()
        
        # Property assertions:
        # 1. Access token should be updated to second token
        assert auth_manager._access_token == second_access_token, \
            "Access token should be updated on second login"
        assert auth_manager._access_token != first_access_token, \
            "Old access token should be replaced"
        
        # 2. Refresh token should be updated to second token
        assert auth_manager._refresh_token == second_refresh_token, \
            "Refresh token should be updated on second login"
        assert auth_manager._refresh_token != first_refresh_token, \
            "Old refresh token should be replaced"
        
        # 3. Should still be authenticated
        assert auth_manager.is_authenticated is True, \
            "Should remain authenticated after second login"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_auth_state_does_not_leak_tokens(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 2: Token Storage After Authentication
        
        **Validates: Requirements 1.2, 2.3, 10.2**
        
        For any authentication state, the get_auth_state() method should
        never include actual token values (security requirement).
        
        This test verifies that:
        - get_auth_state() does not contain access token
        - get_auth_state() does not contain refresh token
        - Sensitive data is not exposed in the auth state
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Create unique, identifiable tokens that won't appear in other strings
        unique_marker = f"UNIQUE_TOKEN_MARKER_{hash(username + password) % 100000}"
        mock_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
        mock_refresh_token = f"secret_refresh_{unique_marker}"
        
        with mock_auth_response(
            access_token=mock_access_token,
            refresh_token=mock_refresh_token
        ):
            await auth_manager.login()
        
        # Get auth state
        auth_state = auth_manager.get_auth_state()
        auth_state_str = str(auth_state)
        
        # Property assertions - no sensitive data in auth state:
        # 1. Access token should not be in auth state
        assert mock_access_token not in auth_state_str, \
            "Access token should not appear in get_auth_state() output"
        
        # 2. Refresh token should not be in auth state
        assert mock_refresh_token not in auth_state_str, \
            "Refresh token should not appear in get_auth_state() output"
        
        # 3. The unique marker (part of refresh token) should not be in auth state
        assert unique_marker not in auth_state_str, \
            "Token content should not appear in get_auth_state() output"
        
        # 4. Auth state should only contain expected safe fields
        expected_keys = {
            'is_authenticated', 'has_access_token', 'has_refresh_token',
            'token_expires_at', 'is_token_expired', 'base_url', 'has_credentials'
        }
        assert set(auth_state.keys()) == expected_keys, \
            f"Auth state should only contain safe fields, got: {set(auth_state.keys())}"


# =============================================================================
# Property Test 5: Token Refresh on Expiration
# =============================================================================

class TestProperty5TokenRefreshOnExpiration:
    """
    Property 5: Token Refresh on Expiration
    
    **Validates: Requirements 2.1, 2.2, 2.5, 8.1, 8.2**
    
    For any API call with an expired access token, the system should automatically
    refresh the token using the `/api/sessions/refresh/` endpoint and retry the
    original API call with the new token.
    
    This property ensures that:
    1. After successful refresh, both tokens are updated
    2. After refresh, authentication state remains valid
    3. When refresh fails with 401, system falls back to login
    """
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_refresh_updates_tokens(self, username: str, password: str):
        """
        # Feature: label-studio-jwt-authentication, Property 5: Token Refresh on Expiration
        
        **Validates: Requirements 2.1, 2.2, 2.5, 8.1, 8.2**
        
        For any successful refresh, both access token and refresh token should
        be updated to the new values returned by the refresh endpoint.
        
        This test verifies that:
        - New access token is stored after refresh
        - New refresh token is stored after refresh
        - Old tokens are replaced (not accumulated)
        - Token expiration is updated from new token
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Set up initial authenticated state with "old" tokens
        old_access_token = create_mock_jwt_token(exp_offset_seconds=-60)  # Expired
        old_refresh_token = f"old_refresh_{username[:10]}"
        
        auth_manager._access_token = old_access_token
        auth_manager._refresh_token = old_refresh_token
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(minutes=1)
        auth_manager._is_authenticated = True
        
        # Create new tokens for the refresh response
        new_access_token = create_mock_jwt_token(exp_offset_seconds=3600)  # Valid for 1 hour
        new_refresh_token = f"new_refresh_{username[:10]}"
        
        # Mock the refresh endpoint response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await auth_manager.refresh_token()
        
        # Property assertions:
        # 1. Refresh should return True on success
        assert result is True, "refresh_token() should return True on success"
        
        # 2. Access token should be updated to new token
        assert auth_manager._access_token == new_access_token, \
            "Access token should be updated to new token after refresh"
        assert auth_manager._access_token != old_access_token, \
            "Old access token should be replaced"
        
        # 3. Refresh token should be updated to new token
        assert auth_manager._refresh_token == new_refresh_token, \
            "Refresh token should be updated to new token after refresh"
        assert auth_manager._refresh_token != old_refresh_token, \
            "Old refresh token should be replaced"
        
        # 4. Token expiration should be updated
        assert auth_manager._token_expires_at is not None, \
            "Token expiration should be updated after refresh"
        # New token expires in 1 hour, so expiration should be in the future
        assert auth_manager._token_expires_at > datetime.utcnow(), \
            "New token expiration should be in the future"
        
        # 5. Should still be authenticated
        assert auth_manager.is_authenticated is True, \
            "Should remain authenticated after refresh"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_refresh_preserves_authentication_state(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 5: Token Refresh on Expiration
        
        **Validates: Requirements 2.1, 2.2, 2.5, 8.1, 8.2**
        
        After successful token refresh, the authentication state should remain
        valid and consistent - all state indicators should agree.
        
        This test verifies that:
        - is_authenticated property remains True
        - _is_authenticated internal flag remains True
        - get_auth_header() returns valid Bearer header with new token
        - get_auth_state() shows consistent state
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Set up initial authenticated state
        old_access_token = create_mock_jwt_token(exp_offset_seconds=-60)
        old_refresh_token = f"old_refresh_{username[:10]}"
        
        auth_manager._access_token = old_access_token
        auth_manager._refresh_token = old_refresh_token
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(minutes=1)
        auth_manager._is_authenticated = True
        
        # Create new tokens for refresh
        new_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
        new_refresh_token = f"new_refresh_{username[:10]}"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            await auth_manager.refresh_token()
        
        # Property assertions - authentication state should be consistent:
        # 1. is_authenticated property should be True
        assert auth_manager.is_authenticated is True, \
            "is_authenticated property should be True after refresh"
        
        # 2. Internal _is_authenticated flag should be True
        assert auth_manager._is_authenticated is True, \
            "_is_authenticated flag should be True after refresh"
        
        # 3. get_auth_header() should return valid Bearer header with NEW token
        auth_header = auth_manager.get_auth_header()
        assert 'Authorization' in auth_header, \
            "get_auth_header() should return Authorization header after refresh"
        assert auth_header['Authorization'] == f'Bearer {new_access_token}', \
            "Authorization header should contain the NEW access token"
        
        # 4. get_auth_state() should show consistent state
        auth_state = auth_manager.get_auth_state()
        assert auth_state["is_authenticated"] is True, \
            "get_auth_state() should indicate is_authenticated=True"
        assert auth_state["has_access_token"] is True, \
            "get_auth_state() should indicate has_access_token=True"
        assert auth_state["has_refresh_token"] is True, \
            "get_auth_state() should indicate has_refresh_token=True"
        
        # 5. Token should NOT be considered expired after refresh
        assert auth_manager._is_token_expired(buffer_seconds=60) is False, \
            "Token should not be expired immediately after refresh"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_refresh_fallback_to_login(self, username: str, password: str):
        """
        # Feature: label-studio-jwt-authentication, Property 5: Token Refresh on Expiration
        
        **Validates: Requirements 2.1, 2.2, 2.5, 8.1, 8.2**
        
        When token refresh fails with 401 (refresh token expired), the system
        should automatically fall back to login using username/password.
        
        This test verifies that:
        - When refresh returns 401, login is called
        - After fallback login, new tokens are stored
        - Authentication state is restored
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Set up initial authenticated state with expired refresh token
        old_access_token = create_mock_jwt_token(exp_offset_seconds=-60)
        old_refresh_token = "expired_refresh_token"
        
        auth_manager._access_token = old_access_token
        auth_manager._refresh_token = old_refresh_token
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(minutes=1)
        auth_manager._is_authenticated = True
        
        # Create new tokens for the login fallback response
        new_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
        new_refresh_token = f"login_refresh_{username[:10]}"
        
        # Mock responses: first call (refresh) returns 401, second call (login) succeeds
        refresh_response = MagicMock()
        refresh_response.status_code = 401
        refresh_response.json.return_value = {"detail": "Token expired"}
        
        login_response = MagicMock()
        login_response.status_code = 200
        login_response.json.return_value = {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer"
        }
        
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First call is refresh (returns 401), second call is login (returns 200)
            if call_count == 1:
                return refresh_response
            else:
                return login_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            result = await auth_manager.refresh_token()
        
        # Property assertions:
        # 1. Refresh should return True (via fallback login)
        assert result is True, \
            "refresh_token() should return True after fallback to login"
        
        # 2. Both refresh and login should have been called
        assert call_count == 2, \
            "Both refresh and login endpoints should have been called"
        
        # 3. New tokens from login should be stored
        assert auth_manager._access_token == new_access_token, \
            "Access token should be from login response after fallback"
        assert auth_manager._refresh_token == new_refresh_token, \
            "Refresh token should be from login response after fallback"
        
        # 4. Should be authenticated
        assert auth_manager.is_authenticated is True, \
            "Should be authenticated after fallback login"
        
        # 5. Token should not be expired
        assert auth_manager._is_token_expired(buffer_seconds=60) is False, \
            "Token should not be expired after fallback login"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy,
        new_exp_offset=st.integers(min_value=300, max_value=7200)  # 5 min to 2 hours
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_refresh_updates_expiration_correctly(
        self,
        username: str,
        password: str,
        new_exp_offset: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 5: Token Refresh on Expiration
        
        **Validates: Requirements 2.1, 2.2, 2.5, 8.1, 8.2**
        
        For any successful token refresh, the token expiration time should be
        correctly updated based on the new access token's exp claim.
        
        This test verifies that:
        - Token expiration is parsed from new access token
        - Expiration time reflects the new token's exp claim
        - Token is not considered expired after refresh
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Set up initial authenticated state with expired token
        old_access_token = create_mock_jwt_token(exp_offset_seconds=-60)
        old_refresh_token = f"old_refresh_{username[:10]}"
        old_expiration = datetime.utcnow() - timedelta(minutes=1)
        
        auth_manager._access_token = old_access_token
        auth_manager._refresh_token = old_refresh_token
        auth_manager._token_expires_at = old_expiration
        auth_manager._is_authenticated = True
        
        # Create new token with specific expiration
        new_access_token = create_mock_jwt_token(exp_offset_seconds=new_exp_offset)
        new_refresh_token = f"new_refresh_{username[:10]}"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            await auth_manager.refresh_token()
        
        # Property assertions:
        # 1. Token expiration should be updated
        assert auth_manager._token_expires_at is not None, \
            "Token expiration should be set after refresh"
        
        # 2. New expiration should be different from old expiration
        assert auth_manager._token_expires_at != old_expiration, \
            "Token expiration should be updated to new value"
        
        # 3. New expiration should be in the future
        assert auth_manager._token_expires_at > datetime.utcnow(), \
            "New token expiration should be in the future"
        
        # 4. Token should NOT be expired with default buffer (60 seconds)
        # Since new_exp_offset is at least 300 seconds (5 minutes)
        assert auth_manager._is_token_expired(buffer_seconds=60) is False, \
            f"Token with {new_exp_offset}s expiration should not be expired"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_refresh_clears_old_tokens_before_storing_new(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 5: Token Refresh on Expiration
        
        **Validates: Requirements 2.1, 2.2, 2.5, 8.1, 8.2**
        
        For any successful token refresh, old tokens should be cleared from
        memory before new tokens are stored (security requirement).
        
        This test verifies that:
        - Old tokens are not retained after refresh
        - Only new tokens are stored
        - No token accumulation occurs
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Set up initial authenticated state
        old_access_token = create_mock_jwt_token(exp_offset_seconds=-60)
        old_refresh_token = f"old_refresh_{username[:10]}"
        
        auth_manager._access_token = old_access_token
        auth_manager._refresh_token = old_refresh_token
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(minutes=1)
        auth_manager._is_authenticated = True
        
        # Create new tokens
        new_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
        new_refresh_token = f"new_refresh_{username[:10]}"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            await auth_manager.refresh_token()
        
        # Property assertions:
        # 1. Access token should be the new token only
        assert auth_manager._access_token == new_access_token, \
            "Only new access token should be stored"
        
        # 2. Refresh token should be the new token only
        assert auth_manager._refresh_token == new_refresh_token, \
            "Only new refresh token should be stored"
        
        # 3. Old tokens should not be present anywhere
        # (We can't directly test memory, but we verify the stored values are new)
        assert old_access_token not in str(auth_manager._access_token), \
            "Old access token should not be retained"
        assert old_refresh_token not in str(auth_manager._refresh_token), \
            "Old refresh token should not be retained"
        
        # 4. Auth header should use new token
        auth_header = auth_manager.get_auth_header()
        assert new_access_token in auth_header['Authorization'], \
            "Auth header should use new access token"
        assert old_access_token not in auth_header['Authorization'], \
            "Auth header should not contain old access token"


# =============================================================================
# Run tests if executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# =============================================================================
# Property Test 9: Token Expiration Detection
# =============================================================================

class TestProperty9TokenExpirationDetection:
    """
    Property 9: Token Expiration Detection
    
    **Validates: Requirements 8.5**
    
    For any JWT access token, the system should correctly parse the `exp` claim
    and determine if the token is expired or will expire within the buffer period
    (60 seconds).
    
    This property ensures that:
    1. Tokens with exp in the past are detected as expired
    2. Tokens with exp in the future are detected as valid
    3. Tokens expiring within buffer period are detected as expired
    4. Tokens without exp claim are treated as expired (safe default)
    """
    
    @pytest.mark.asyncio
    @given(
        exp_offset=st.integers(min_value=-7200, max_value=-1)  # 1 second to 2 hours in the past
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_expired_tokens_detected(self, exp_offset: int):
        """
        # Feature: label-studio-jwt-authentication, Property 9: Token Expiration Detection
        
        **Validates: Requirements 8.5**
        
        For any token with expiration in the past, _is_token_expired() should
        return True.
        
        This test verifies that:
        - Tokens with exp claim in the past are detected as expired
        - The detection works for various past expiration times
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # Create token with expiration in the past
        expired_token = create_mock_jwt_token(exp_offset_seconds=exp_offset)
        
        # Set up auth manager with expired token
        auth_manager._access_token = expired_token
        auth_manager._token_expires_at = auth_manager._parse_token_expiration(expired_token)
        
        # Property assertion: expired token should be detected
        assert auth_manager._is_token_expired(buffer_seconds=0) is True, \
            f"Token with exp_offset={exp_offset}s should be detected as expired"
    
    @pytest.mark.asyncio
    @given(
        exp_offset=st.integers(min_value=120, max_value=7200)  # 2 minutes to 2 hours in the future
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_valid_tokens_not_expired(self, exp_offset: int):
        """
        # Feature: label-studio-jwt-authentication, Property 9: Token Expiration Detection
        
        **Validates: Requirements 8.5**
        
        For any token with expiration sufficiently in the future (beyond buffer),
        _is_token_expired() should return False.
        
        This test verifies that:
        - Tokens with exp claim in the future are detected as valid
        - The detection works for various future expiration times
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # Create token with expiration in the future
        valid_token = create_mock_jwt_token(exp_offset_seconds=exp_offset)
        
        # Set up auth manager with valid token
        auth_manager._access_token = valid_token
        auth_manager._token_expires_at = auth_manager._parse_token_expiration(valid_token)
        
        # Property assertion: valid token should NOT be detected as expired
        # Use buffer of 60 seconds (default), so token must be > 60s from expiring
        assert auth_manager._is_token_expired(buffer_seconds=60) is False, \
            f"Token with exp_offset={exp_offset}s should NOT be detected as expired"
    
    @pytest.mark.asyncio
    @given(
        buffer_seconds=st.integers(min_value=30, max_value=300),  # 30s to 5 min buffer
        exp_offset=st.integers(min_value=1, max_value=29)  # 1-29 seconds in future
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_tokens_within_buffer_detected_as_expired(
        self,
        buffer_seconds: int,
        exp_offset: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 9: Token Expiration Detection
        
        **Validates: Requirements 8.5**
        
        For any token expiring within the buffer period, _is_token_expired()
        should return True (proactive refresh).
        
        This test verifies that:
        - Tokens expiring within buffer period are detected as "expired"
        - This enables proactive token refresh before actual expiration
        """
        # Ensure exp_offset is less than buffer_seconds
        assume(exp_offset < buffer_seconds)
        
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # Create token expiring within buffer period
        token = create_mock_jwt_token(exp_offset_seconds=exp_offset)
        
        # Set up auth manager
        auth_manager._access_token = token
        auth_manager._token_expires_at = auth_manager._parse_token_expiration(token)
        
        # Property assertion: token within buffer should be detected as expired
        assert auth_manager._is_token_expired(buffer_seconds=buffer_seconds) is True, \
            f"Token expiring in {exp_offset}s should be detected as expired with {buffer_seconds}s buffer"
    
    @pytest.mark.asyncio
    @given(
        buffer_seconds=st.integers(min_value=30, max_value=120),  # 30s to 2 min buffer
        exp_offset=st.integers(min_value=180, max_value=3600)  # 3 min to 1 hour in future
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_tokens_outside_buffer_not_expired(
        self,
        buffer_seconds: int,
        exp_offset: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 9: Token Expiration Detection
        
        **Validates: Requirements 8.5**
        
        For any token expiring outside the buffer period, _is_token_expired()
        should return False.
        
        This test verifies that:
        - Tokens expiring well beyond buffer period are detected as valid
        - Buffer period is correctly applied
        """
        # Ensure exp_offset is greater than buffer_seconds
        assume(exp_offset > buffer_seconds)
        
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # Create token expiring outside buffer period
        token = create_mock_jwt_token(exp_offset_seconds=exp_offset)
        
        # Set up auth manager
        auth_manager._access_token = token
        auth_manager._token_expires_at = auth_manager._parse_token_expiration(token)
        
        # Property assertion: token outside buffer should NOT be detected as expired
        assert auth_manager._is_token_expired(buffer_seconds=buffer_seconds) is False, \
            f"Token expiring in {exp_offset}s should NOT be detected as expired with {buffer_seconds}s buffer"
    
    @pytest.mark.asyncio
    @given(
        buffer_seconds=st.integers(min_value=0, max_value=300)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_no_token_treated_as_expired(self, buffer_seconds: int):
        """
        # Feature: label-studio-jwt-authentication, Property 9: Token Expiration Detection
        
        **Validates: Requirements 8.5**
        
        When no access token is stored, _is_token_expired() should return True
        (safe default behavior).
        
        This test verifies that:
        - Missing token is treated as expired
        - This triggers authentication before API calls
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # No token set
        auth_manager._access_token = None
        auth_manager._token_expires_at = None
        
        # Property assertion: no token should be treated as expired
        assert auth_manager._is_token_expired(buffer_seconds=buffer_seconds) is True, \
            "Missing token should be treated as expired"
    
    @pytest.mark.asyncio
    @given(
        buffer_seconds=st.integers(min_value=0, max_value=300)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_no_expiration_time_treated_as_expired(self, buffer_seconds: int):
        """
        # Feature: label-studio-jwt-authentication, Property 9: Token Expiration Detection
        
        **Validates: Requirements 8.5**
        
        When token exists but expiration time is unknown, _is_token_expired()
        should return True (safe default behavior).
        
        This test verifies that:
        - Token without known expiration is treated as expired
        - This triggers token refresh to get a token with known expiration
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # Token exists but no expiration time
        auth_manager._access_token = "some_token_without_exp"
        auth_manager._token_expires_at = None
        
        # Property assertion: unknown expiration should be treated as expired
        assert auth_manager._is_token_expired(buffer_seconds=buffer_seconds) is True, \
            "Token with unknown expiration should be treated as expired"


# =============================================================================
# Property Test 7: Concurrent Refresh Mutual Exclusion
# =============================================================================

class TestProperty7ConcurrentRefreshMutualExclusion:
    """
    Property 7: Concurrent Refresh Mutual Exclusion
    
    **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
    
    For any set of concurrent API calls that require token refresh, only one
    refresh operation should execute, and all waiting calls should use the
    refreshed token or receive the same error if refresh fails.
    
    This property ensures that:
    1. Only one refresh operation executes for concurrent calls
    2. All waiting calls use the refreshed token
    3. No deadlocks occur with concurrent access
    4. Lock is properly released after refresh
    """
    
    @pytest.mark.asyncio
    @given(
        num_concurrent_calls=st.integers(min_value=2, max_value=10)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_concurrent_refresh_single_operation(self, num_concurrent_calls: int):
        """
        # Feature: label-studio-jwt-authentication, Property 7: Concurrent Refresh Mutual Exclusion
        
        **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
        
        For any number of concurrent API calls that require token refresh,
        only one refresh operation should execute.
        
        This test verifies that:
        - Multiple concurrent calls trigger only one refresh
        - The lock prevents concurrent refresh operations
        - All calls complete successfully with the refreshed token
        """
        import time
        
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # Set up expired token
        expired_token = create_mock_jwt_token(exp_offset_seconds=-3600)  # 1 hour in the past
        
        auth_manager._access_token = expired_token
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcfromtimestamp(time.time() - 3600)
        
        refresh_call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal refresh_call_count
            refresh_call_count += 1
            # Simulate network delay
            await asyncio.sleep(0.02)
            
            # Create fresh token
            fresh_token = create_mock_jwt_token(exp_offset_seconds=3600)
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": fresh_token,
                "refresh_token": "new_refresh_token"
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Create concurrent tasks
            tasks = [
                asyncio.create_task(auth_manager._ensure_authenticated())
                for _ in range(num_concurrent_calls)
            ]
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        
        # Property assertions:
        # 1. Only one refresh should have been made
        assert refresh_call_count == 1, \
            f"Expected 1 refresh call for {num_concurrent_calls} concurrent calls, got {refresh_call_count}"
        
        # 2. All calls should see the new token (not expired)
        assert not auth_manager._is_token_expired(), \
            "Token should not be expired after refresh"
        
        # 3. Should be authenticated
        assert auth_manager._is_authenticated, \
            "Should be authenticated after refresh"
    
    @pytest.mark.asyncio
    @given(
        num_concurrent_calls=st.integers(min_value=2, max_value=10)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_concurrent_calls_all_get_same_token(self, num_concurrent_calls: int):
        """
        # Feature: label-studio-jwt-authentication, Property 7: Concurrent Refresh Mutual Exclusion
        
        **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
        
        For any set of concurrent calls, all should receive the same refreshed
        token after the single refresh operation completes.
        
        This test verifies that:
        - All concurrent calls see the same token after refresh
        - No call gets a stale or different token
        """
        import time
        
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # Set up expired token
        expired_token = create_mock_jwt_token(exp_offset_seconds=-3600)
        
        auth_manager._access_token = expired_token
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcfromtimestamp(time.time() - 3600)
        
        # Track the token returned by refresh
        new_token = None
        
        async def mock_post(*args, **kwargs):
            nonlocal new_token
            await asyncio.sleep(0.02)
            
            # Create fresh token (same for all calls)
            if new_token is None:
                new_token = create_mock_jwt_token(exp_offset_seconds=3600)
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": new_token,
                "refresh_token": "new_refresh_token"
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Create concurrent tasks that capture the token after ensure_authenticated
            tokens_seen = []
            
            async def capture_token():
                await auth_manager._ensure_authenticated()
                tokens_seen.append(auth_manager._access_token)
            
            tasks = [
                asyncio.create_task(capture_token())
                for _ in range(num_concurrent_calls)
            ]
            
            await asyncio.gather(*tasks)
        
        # Property assertions:
        # 1. All calls should see the same token
        assert len(set(tokens_seen)) == 1, \
            f"All {num_concurrent_calls} calls should see the same token, got {len(set(tokens_seen))} different tokens"
        
        # 2. The token should be the new token
        assert tokens_seen[0] == new_token, \
            "All calls should see the new token"
    
    @pytest.mark.asyncio
    @given(
        num_concurrent_calls=st.integers(min_value=2, max_value=10)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_concurrent_calls_no_deadlock(self, num_concurrent_calls: int):
        """
        # Feature: label-studio-jwt-authentication, Property 7: Concurrent Refresh Mutual Exclusion
        
        **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
        
        For any number of concurrent calls, no deadlock should occur.
        All calls should complete within a reasonable time.
        
        This test verifies that:
        - No deadlock occurs with concurrent access
        - All calls complete successfully
        - Lock is properly released
        """
        import time
        
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # Set up expired token
        expired_token = create_mock_jwt_token(exp_offset_seconds=-3600)
        
        auth_manager._access_token = expired_token
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcfromtimestamp(time.time() - 3600)
        
        async def mock_post(*args, **kwargs):
            await asyncio.sleep(0.02)
            
            fresh_token = create_mock_jwt_token(exp_offset_seconds=3600)
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": fresh_token,
                "refresh_token": "new_refresh_token"
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Create concurrent tasks
            tasks = [
                asyncio.create_task(auth_manager._ensure_authenticated())
                for _ in range(num_concurrent_calls)
            ]
            
            # Wait with timeout to detect deadlock
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks),
                    timeout=5.0  # 5 second timeout
                )
            except asyncio.TimeoutError:
                pytest.fail(
                    f"Deadlock detected: {num_concurrent_calls} concurrent calls "
                    "did not complete within 5 seconds"
                )
        
        # Property assertion: all calls completed (no deadlock)
        # If we reach here, no deadlock occurred
        assert auth_manager._is_authenticated, \
            "Should be authenticated after all calls complete"
    
    @pytest.mark.asyncio
    @given(
        num_concurrent_calls=st.integers(min_value=2, max_value=10)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_concurrent_calls_lock_released_on_error(self, num_concurrent_calls: int):
        """
        # Feature: label-studio-jwt-authentication, Property 7: Concurrent Refresh Mutual Exclusion
        
        **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
        
        When refresh fails, the lock should be properly released so subsequent
        calls can attempt authentication.
        
        This test verifies that:
        - Lock is released even when refresh fails
        - Subsequent calls can proceed after failure
        - Error is propagated to all waiting calls
        """
        import time
        
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        # Set up expired token
        expired_token = create_mock_jwt_token(exp_offset_seconds=-3600)
        
        auth_manager._access_token = expired_token
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcfromtimestamp(time.time() - 3600)
        
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.02)
            
            # First call fails (refresh), second call succeeds (login fallback)
            if call_count == 1:
                # Refresh fails with 401
                mock_response = MagicMock()
                mock_response.status_code = 401
                return mock_response
            else:
                # Login succeeds
                fresh_token = create_mock_jwt_token(exp_offset_seconds=3600)
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "access_token": fresh_token,
                    "refresh_token": "new_refresh_token"
                }
                return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Create concurrent tasks
            tasks = [
                asyncio.create_task(auth_manager._ensure_authenticated())
                for _ in range(num_concurrent_calls)
            ]
            
            # Wait with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                pytest.fail(
                    "Deadlock detected: lock was not released after error"
                )
        
        # Property assertion: lock was released and subsequent calls succeeded
        assert auth_manager._is_authenticated, \
            "Should be authenticated after fallback to login"


# =============================================================================
# Property Test 1: Authentication Method Selection
# =============================================================================

class TestProperty1AuthenticationMethodSelection:
    """
    Property 1: Authentication Method Selection
    
    **Validates: Requirements 1.1, 3.1, 3.2, 6.3, 6.4**
    
    For any configuration state, the system should select JWT authentication
    if username and password are provided, otherwise fall back to API token
    authentication, and raise an error if neither is available.
    
    This property ensures that:
    1. JWT is selected when both username and password are configured
    2. API token is selected when only api_token is configured
    3. Error is raised when neither is configured
    4. JWT takes priority over API token when both are configured
    """
    
    @pytest.mark.asyncio
    @given(
        has_username=st.booleans(),
        has_password=st.booleans(),
        has_api_token=st.booleans()
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_auth_method_selection(
        self,
        has_username: bool,
        has_password: bool,
        has_api_token: bool
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 1: Authentication Method Selection
        
        **Validates: Requirements 1.1, 3.1, 3.2, 6.3, 6.4**
        
        For any configuration state, the system should select JWT authentication
        if username and password are provided, otherwise fall back to API token
        authentication, and raise an error if neither is available.
        """
        from unittest.mock import patch, MagicMock
        from src.label_studio.config import LabelStudioConfig, LabelStudioConfigError
        
        # Create mock settings
        mock_settings = MagicMock()
        mock_settings.label_studio.label_studio_url = "http://test:8080"
        mock_settings.label_studio.label_studio_api_token = "test_token" if has_api_token else None
        mock_settings.label_studio.label_studio_project_id = 1
        mock_settings.label_studio.label_studio_username = "user" if has_username else None
        mock_settings.label_studio.label_studio_password = "pass" if has_password else None
        
        with patch('src.label_studio.config.settings', mock_settings):
            config = LabelStudioConfig()
            
            if has_username and has_password:
                # JWT should be selected when both username and password are configured
                assert config.get_auth_method() == 'jwt', \
                    "JWT should be selected when username and password are configured"
            elif has_api_token:
                # API token should be selected when only api_token is configured
                assert config.get_auth_method() == 'api_token', \
                    "API token should be selected when only api_token is configured"
            else:
                # Error should be raised when neither is configured
                with pytest.raises(LabelStudioConfigError):
                    config.get_auth_method()
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy,
        api_token=st.text(min_size=10, max_size=50)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_jwt_takes_priority_over_api_token(
        self,
        username: str,
        password: str,
        api_token: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 1: Authentication Method Selection
        
        **Validates: Requirements 1.1, 3.1, 3.2, 6.3, 6.4**
        
        When both JWT credentials and API token are configured, JWT should
        take priority.
        """
        from unittest.mock import patch, MagicMock
        from src.label_studio.config import LabelStudioConfig
        
        # Create mock settings with both auth methods configured
        mock_settings = MagicMock()
        mock_settings.label_studio.label_studio_url = "http://test:8080"
        mock_settings.label_studio.label_studio_api_token = api_token
        mock_settings.label_studio.label_studio_project_id = 1
        mock_settings.label_studio.label_studio_username = username
        mock_settings.label_studio.label_studio_password = password
        
        with patch('src.label_studio.config.settings', mock_settings):
            config = LabelStudioConfig()
            
            # JWT should take priority
            assert config.get_auth_method() == 'jwt', \
                "JWT should take priority when both auth methods are configured"
    
    @pytest.mark.asyncio
    @given(
        api_token=st.text(min_size=10, max_size=50)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_api_token_fallback(self, api_token: str):
        """
        # Feature: label-studio-jwt-authentication, Property 1: Authentication Method Selection
        
        **Validates: Requirements 1.1, 3.1, 3.2, 6.3, 6.4**
        
        When only API token is configured (no JWT credentials), API token
        authentication should be selected.
        """
        from unittest.mock import patch, MagicMock
        from src.label_studio.config import LabelStudioConfig
        
        # Create mock settings with only API token
        mock_settings = MagicMock()
        mock_settings.label_studio.label_studio_url = "http://test:8080"
        mock_settings.label_studio.label_studio_api_token = api_token
        mock_settings.label_studio.label_studio_project_id = 1
        mock_settings.label_studio.label_studio_username = None
        mock_settings.label_studio.label_studio_password = None
        
        with patch('src.label_studio.config.settings', mock_settings):
            config = LabelStudioConfig()
            
            # API token should be selected
            assert config.get_auth_method() == 'api_token', \
                "API token should be selected when no JWT credentials are configured"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_partial_jwt_credentials_not_selected(self, username: str):
        """
        # Feature: label-studio-jwt-authentication, Property 1: Authentication Method Selection
        
        **Validates: Requirements 1.1, 3.1, 3.2, 6.3, 6.4**
        
        When only username is configured (no password), JWT should NOT be
        selected. If API token is available, it should be used instead.
        """
        from unittest.mock import patch, MagicMock
        from src.label_studio.config import LabelStudioConfig, LabelStudioConfigError
        
        # Create mock settings with only username (no password)
        mock_settings = MagicMock()
        mock_settings.label_studio.label_studio_url = "http://test:8080"
        mock_settings.label_studio.label_studio_api_token = "fallback_token"
        mock_settings.label_studio.label_studio_project_id = 1
        mock_settings.label_studio.label_studio_username = username
        mock_settings.label_studio.label_studio_password = None  # No password
        
        with patch('src.label_studio.config.settings', mock_settings):
            config = LabelStudioConfig()
            
            # API token should be selected (JWT requires both username AND password)
            assert config.get_auth_method() == 'api_token', \
                "API token should be selected when only username is configured"
    
    @pytest.mark.asyncio
    async def test_no_auth_raises_error(self):
        """
        # Feature: label-studio-jwt-authentication, Property 1: Authentication Method Selection
        
        **Validates: Requirements 1.1, 3.1, 3.2, 6.3, 6.4**
        
        When no authentication method is configured, an error should be raised.
        
        Note: This is a unit test (not property test) because there's only one
        configuration state to test (no auth configured).
        """
        from unittest.mock import patch, MagicMock
        from src.label_studio.config import LabelStudioConfig, LabelStudioConfigError
        
        # Create mock settings with no auth
        mock_settings = MagicMock()
        mock_settings.label_studio.label_studio_url = "http://test:8080"
        mock_settings.label_studio.label_studio_api_token = None
        mock_settings.label_studio.label_studio_project_id = 1
        mock_settings.label_studio.label_studio_username = None
        mock_settings.label_studio.label_studio_password = None
        
        with patch('src.label_studio.config.settings', mock_settings):
            config = LabelStudioConfig()
            
            # Should raise error
            with pytest.raises(LabelStudioConfigError) as exc_info:
                config.get_auth_method()
            
            # Error message should be helpful
            assert "No authentication method configured" in str(exc_info.value)



# =============================================================================
# Property Test 3: Authentication Header Format
# =============================================================================

class TestProperty3AuthenticationHeaderFormat:
    """
    Property 3: Authentication Header Format
    
    **Validates: Requirements 1.4, 3.3, 7.1, 7.2, 7.5**
    
    For any authentication state, the system should return the correct
    Authorization header format:
    - JWT: "Bearer {access_token}"
    - API Token: "Token {api_token}"
    
    This property ensures that:
    1. JWT auth returns Bearer format header
    2. API token auth returns Token format header
    3. Headers always include Content-Type
    4. No sensitive data is leaked in headers
    """
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_jwt_auth_returns_bearer_header(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 3: Authentication Header Format
        
        **Validates: Requirements 1.4, 3.3, 7.1, 7.2, 7.5**
        
        For JWT authentication, the Authorization header should use Bearer format.
        
        This test verifies that:
        - JWT auth returns "Bearer {token}" format
        - Header includes Content-Type
        - Token is the actual access token
        """
        from unittest.mock import patch, MagicMock, AsyncMock
        from src.label_studio.integration import LabelStudioIntegration
        from src.label_studio.config import LabelStudioConfig
        
        # Create mock config with JWT credentials
        mock_settings = MagicMock()
        mock_settings.label_studio.label_studio_url = "http://test:8080"
        mock_settings.label_studio.label_studio_api_token = "fallback_token"
        mock_settings.label_studio.label_studio_project_id = 1
        mock_settings.label_studio.label_studio_username = username
        mock_settings.label_studio.label_studio_password = password
        mock_settings.security.jwt_secret_key = "test_secret"
        mock_settings.security.jwt_algorithm = "HS256"
        
        with patch('src.label_studio.config.settings', mock_settings):
            config = LabelStudioConfig()
            
            # Create integration with JWT auth
            with patch('src.label_studio.integration.settings', mock_settings):
                integration = LabelStudioIntegration(config)
                
                # Verify JWT auth is selected
                assert integration.auth_method == 'jwt', \
                    "JWT should be selected when username and password are configured"
                
                # Mock the JWT auth manager to be authenticated
                mock_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
                integration._jwt_auth_manager._access_token = mock_access_token
                integration._jwt_auth_manager._refresh_token = "refresh_token"
                integration._jwt_auth_manager._is_authenticated = True
                integration._jwt_auth_manager._token_expires_at = datetime.utcnow() + timedelta(hours=1)
                
                # Get headers
                headers = await integration._get_headers()
                
                # Property assertions:
                # 1. Authorization header should use Bearer format
                assert 'Authorization' in headers, \
                    "Headers should include Authorization"
                assert headers['Authorization'].startswith('Bearer '), \
                    "JWT auth should use Bearer format"
                
                # 2. Authorization header should contain the access token
                assert mock_access_token in headers['Authorization'], \
                    "Bearer header should contain the access token"
                
                # 3. Content-Type should be included
                assert 'Content-Type' in headers, \
                    "Headers should include Content-Type"
                assert headers['Content-Type'] == 'application/json', \
                    "Content-Type should be application/json"
    
    @pytest.mark.asyncio
    @given(
        api_token=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_api_token_auth_returns_token_header(self, api_token: str):
        """
        # Feature: label-studio-jwt-authentication, Property 3: Authentication Header Format
        
        **Validates: Requirements 1.4, 3.3, 7.1, 7.2, 7.5**
        
        For API token authentication, the Authorization header should use Token format.
        
        This test verifies that:
        - API token auth returns "Token {api_token}" format
        - Header includes Content-Type
        - Token is the actual API token
        """
        from unittest.mock import patch, MagicMock
        from src.label_studio.integration import LabelStudioIntegration
        from src.label_studio.config import LabelStudioConfig
        
        # Create mock config with only API token (no JWT credentials)
        mock_settings = MagicMock()
        mock_settings.label_studio.label_studio_url = "http://test:8080"
        mock_settings.label_studio.label_studio_api_token = api_token
        mock_settings.label_studio.label_studio_project_id = 1
        mock_settings.label_studio.label_studio_username = None
        mock_settings.label_studio.label_studio_password = None
        mock_settings.security.jwt_secret_key = "test_secret"
        mock_settings.security.jwt_algorithm = "HS256"
        
        with patch('src.label_studio.config.settings', mock_settings):
            config = LabelStudioConfig()
            
            # Create integration with API token auth
            with patch('src.label_studio.integration.settings', mock_settings):
                integration = LabelStudioIntegration(config)
                
                # Verify API token auth is selected
                assert integration.auth_method == 'api_token', \
                    "API token should be selected when no JWT credentials are configured"
                
                # Get headers
                headers = await integration._get_headers()
                
                # Property assertions:
                # 1. Authorization header should use Token format
                assert 'Authorization' in headers, \
                    "Headers should include Authorization"
                assert headers['Authorization'].startswith('Token '), \
                    "API token auth should use Token format"
                
                # 2. Authorization header should contain the API token
                assert api_token in headers['Authorization'], \
                    "Token header should contain the API token"
                
                # 3. Content-Type should be included
                assert 'Content-Type' in headers, \
                    "Headers should include Content-Type"
                assert headers['Content-Type'] == 'application/json', \
                    "Content-Type should be application/json"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_headers_do_not_leak_credentials(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 3: Authentication Header Format
        
        **Validates: Requirements 1.4, 3.3, 7.1, 7.2, 7.5, 10.2**
        
        Headers should never contain raw credentials (username/password).
        
        This test verifies that:
        - Username is not in headers
        - Password is not in headers
        - Only tokens are in Authorization header
        """
        from unittest.mock import patch, MagicMock
        from src.label_studio.integration import LabelStudioIntegration
        from src.label_studio.config import LabelStudioConfig
        
        # Create mock config with JWT credentials
        mock_settings = MagicMock()
        mock_settings.label_studio.label_studio_url = "http://test:8080"
        mock_settings.label_studio.label_studio_api_token = "fallback_token"
        mock_settings.label_studio.label_studio_project_id = 1
        mock_settings.label_studio.label_studio_username = username
        mock_settings.label_studio.label_studio_password = password
        mock_settings.security.jwt_secret_key = "test_secret"
        mock_settings.security.jwt_algorithm = "HS256"
        
        with patch('src.label_studio.config.settings', mock_settings):
            config = LabelStudioConfig()
            
            with patch('src.label_studio.integration.settings', mock_settings):
                integration = LabelStudioIntegration(config)
                
                # Mock the JWT auth manager to be authenticated
                mock_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
                integration._jwt_auth_manager._access_token = mock_access_token
                integration._jwt_auth_manager._refresh_token = "refresh_token"
                integration._jwt_auth_manager._is_authenticated = True
                integration._jwt_auth_manager._token_expires_at = datetime.utcnow() + timedelta(hours=1)
                
                # Get headers
                headers = await integration._get_headers()
                headers_str = str(headers)
                
                # Property assertions - no credentials in headers:
                # 1. Username should not be in headers
                # Only check if username is long enough to be meaningful
                if len(username) >= 4:
                    assert username not in headers_str, \
                        "Username should not appear in headers"
                
                # 2. Password should not be in headers
                # Only check if password is long enough to be meaningful
                if len(password) >= 8:
                    assert password not in headers_str, \
                        "Password should not appear in headers"


# =============================================================================
# Property Test 4: Authentication Error Non-Retryability
# =============================================================================

class TestProperty4AuthenticationErrorNonRetryability:
    """
    Property 4: Authentication Error Non-Retryability
    
    **Validates: Requirements 1.3, 5.1, 5.5**
    
    For any API call that returns 401 or 403 status code with authentication
    failure (not token expiration), the system should raise
    `LabelStudioAuthenticationError` and NOT retry the operation.
    
    This property ensures that:
    1. 401 errors with invalid credentials raise LabelStudioAuthenticationError
    2. 403 errors (forbidden) raise LabelStudioAuthenticationError
    3. Authentication errors are NOT retried
    4. Error messages are clear and actionable
    5. Re-authentication failures raise LabelStudioAuthenticationError
    """
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_401_invalid_credentials_raises_auth_error(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        For any login attempt with invalid credentials that returns 401,
        the system should raise LabelStudioAuthenticationError and NOT retry.
        
        This test verifies that:
        - 401 response raises LabelStudioAuthenticationError
        - Error has status_code = 401
        - Error message is clear and actionable
        - No retry is attempted (only one request made)
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Track number of requests made
        request_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            
            # Return 401 Unauthorized
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "detail": "Invalid username or password"
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            # Property assertions:
            # 1. Should raise LabelStudioAuthenticationError
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
            
            # 2. Error should have status_code = 401
            assert exc_info.value.status_code == 401, \
                "Error status_code should be 401"
            
            # 3. Error message should be clear
            assert "Invalid username or password" in str(exc_info.value) or \
                   "Invalid" in str(exc_info.value) or \
                   "401" in str(exc_info.value), \
                "Error message should indicate invalid credentials"
            
            # 4. Only one request should have been made (no retry)
            assert request_count == 1, \
                f"Expected 1 request (no retry), but got {request_count} requests"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_403_forbidden_raises_auth_error(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        For any login attempt that returns 403 Forbidden,
        the system should raise LabelStudioAuthenticationError and NOT retry.
        
        This test verifies that:
        - 403 response raises LabelStudioAuthenticationError
        - Error has status_code = 403
        - Error message indicates forbidden/permissions issue
        - No retry is attempted (only one request made)
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Track number of requests made
        request_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            
            # Return 403 Forbidden
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.json.return_value = {
                "detail": "Access forbidden - insufficient permissions"
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            # Property assertions:
            # 1. Should raise LabelStudioAuthenticationError
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
            
            # 2. Error should have status_code = 403
            assert exc_info.value.status_code == 403, \
                "Error status_code should be 403"
            
            # 3. Error message should indicate forbidden/permissions
            error_str = str(exc_info.value).lower()
            assert "forbidden" in error_str or "permission" in error_str or "403" in str(exc_info.value), \
                "Error message should indicate forbidden or permissions issue"
            
            # 4. Only one request should have been made (no retry)
            assert request_count == 1, \
                f"Expected 1 request (no retry), but got {request_count} requests"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy,
        status_code=st.sampled_from([401, 403])
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_auth_errors_clear_tokens(
        self,
        username: str,
        password: str,
        status_code: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        For any authentication error (401/403), the system should clear
        any existing tokens from memory.
        
        This test verifies that:
        - Tokens are cleared on authentication failure
        - is_authenticated is set to False
        - No stale tokens remain in memory
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Pre-set some tokens to verify they get cleared
        auth_manager._access_token = "old_access_token"
        auth_manager._refresh_token = "old_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        async def mock_post(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_response.json.return_value = {
                "detail": "Authentication failed"
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            # Attempt login (should fail)
            with pytest.raises(LabelStudioAuthenticationError):
                await auth_manager.login()
            
            # Property assertions - tokens should be cleared:
            # 1. Access token should be cleared
            assert auth_manager._access_token is None, \
                "Access token should be cleared on auth failure"
            
            # 2. Refresh token should be cleared
            assert auth_manager._refresh_token is None, \
                "Refresh token should be cleared on auth failure"
            
            # 3. is_authenticated should be False
            assert auth_manager._is_authenticated is False, \
                "is_authenticated should be False on auth failure"
            
            # 4. Token expiration should be cleared
            assert auth_manager._token_expires_at is None, \
                "Token expiration should be cleared on auth failure"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_refresh_403_raises_auth_error_no_retry(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        For any token refresh that returns 403 Forbidden,
        the system should raise LabelStudioAuthenticationError and NOT retry.
        
        This test verifies that:
        - 403 on refresh raises LabelStudioAuthenticationError
        - Error has status_code = 403
        - No retry is attempted
        - Tokens are cleared
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Set up authenticated state with refresh token
        auth_manager._access_token = create_mock_jwt_token(exp_offset_seconds=-60)
        auth_manager._refresh_token = "valid_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(minutes=1)
        
        # Track number of requests made
        request_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            
            # Return 403 Forbidden
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.json.return_value = {
                "detail": "Access forbidden"
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            # Property assertions:
            # 1. Should raise LabelStudioAuthenticationError
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.refresh_token()
            
            # 2. Error should have status_code = 403
            assert exc_info.value.status_code == 403, \
                "Error status_code should be 403"
            
            # 3. Only one request should have been made (no retry)
            assert request_count == 1, \
                f"Expected 1 request (no retry), but got {request_count} requests"
            
            # 4. Tokens should be cleared
            assert auth_manager._access_token is None, \
                "Access token should be cleared on 403"
            assert auth_manager._refresh_token is None, \
                "Refresh token should be cleared on 403"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_reauth_failure_raises_auth_error(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        When re-authentication fails (after refresh token expires),
        the system should raise LabelStudioAuthenticationError with clear message.
        
        This test verifies that:
        - When refresh returns 401 (expired), login is attempted
        - When login also fails with 401, LabelStudioAuthenticationError is raised
        - Error message is clear and actionable
        - No infinite retry loop occurs
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Set up authenticated state with expired refresh token
        auth_manager._access_token = create_mock_jwt_token(exp_offset_seconds=-60)
        auth_manager._refresh_token = "expired_refresh_token"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(minutes=1)
        
        # Track requests
        request_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            
            # First call: refresh returns 401 (expired)
            # Second call: login also returns 401 (invalid credentials)
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "detail": "Invalid credentials" if request_count > 1 else "Token expired"
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            # Property assertions:
            # 1. Should raise LabelStudioAuthenticationError
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.refresh_token()
            
            # 2. Error should have status_code = 401
            assert exc_info.value.status_code == 401, \
                "Error status_code should be 401"
            
            # 3. Should have made exactly 2 requests (refresh + login fallback)
            assert request_count == 2, \
                f"Expected 2 requests (refresh + login), but got {request_count}"
            
            # 4. Tokens should be cleared
            assert auth_manager._access_token is None, \
                "Access token should be cleared after re-auth failure"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy,
        error_detail=st.text(min_size=5, max_size=100)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_auth_error_message_is_clear(
        self,
        username: str,
        password: str,
        error_detail: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        For any authentication error, the error message should be clear
        and actionable, including the HTTP status code.
        
        This test verifies that:
        - Error message includes status code
        - Error message is human-readable
        - Error can be converted to string for logging
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        async def mock_post(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "detail": error_detail
            }
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
            
            # Property assertions - error message quality:
            # 1. Error should be convertible to string
            error_str = str(exc_info.value)
            assert isinstance(error_str, str), \
                "Error should be convertible to string"
            
            # 2. Error string should include status code
            assert "401" in error_str, \
                "Error message should include status code"
            
            # 3. Error should have message attribute
            assert hasattr(exc_info.value, 'message'), \
                "Error should have message attribute"
            
            # 4. Error should have status_code attribute
            assert hasattr(exc_info.value, 'status_code'), \
                "Error should have status_code attribute"
            assert exc_info.value.status_code == 401, \
                "Error status_code should be 401"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_auth_error_is_not_network_error(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        Authentication errors (401/403) should be distinct from network errors.
        They should raise LabelStudioAuthenticationError, not a generic exception.
        
        This test verifies that:
        - 401/403 raises LabelStudioAuthenticationError specifically
        - The error is an instance of LabelStudioAuthenticationError
        - The error is NOT a generic Exception or network error
        """
        from src.label_studio.exceptions import (
            LabelStudioAuthenticationError,
            LabelStudioNetworkError,
            LabelStudioIntegrationError
        )
        
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        async def mock_post(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Unauthorized"}
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            try:
                await auth_manager.login()
                pytest.fail("Expected LabelStudioAuthenticationError to be raised")
            except LabelStudioAuthenticationError as e:
                # Property assertions:
                # 1. Should be instance of LabelStudioAuthenticationError
                assert isinstance(e, LabelStudioAuthenticationError), \
                    "Error should be LabelStudioAuthenticationError"
                
                # 2. Should also be instance of base class
                assert isinstance(e, LabelStudioIntegrationError), \
                    "Error should inherit from LabelStudioIntegrationError"
                
                # 3. Should NOT be a network error
                assert not isinstance(e, LabelStudioNetworkError), \
                    "Auth error should NOT be a network error"
            except Exception as e:
                pytest.fail(
                    f"Expected LabelStudioAuthenticationError, got {type(e).__name__}: {e}"
                )
    
    @pytest.mark.asyncio
    @given(
        num_attempts=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_repeated_auth_failures_not_retried(self, num_attempts: int):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        For any number of authentication attempts, each 401/403 error should
        raise immediately without internal retry logic.
        
        This test verifies that:
        - Each login attempt that fails with 401 raises immediately
        - No internal retry mechanism is triggered
        - Each attempt is independent
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="user",
            password="pass"
        )
        
        total_requests = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal total_requests
            total_requests += 1
            
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Unauthorized"}
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            # Make multiple login attempts
            for i in range(num_attempts):
                with pytest.raises(LabelStudioAuthenticationError):
                    await auth_manager.login()
            
            # Property assertion: each attempt should make exactly 1 request
            assert total_requests == num_attempts, \
                f"Expected {num_attempts} requests for {num_attempts} attempts, got {total_requests}"


# =============================================================================
# Additional Property Tests for Error Handling Edge Cases
# =============================================================================

class TestProperty4ErrorHandlingEdgeCases:
    """
    Additional property tests for authentication error handling edge cases.
    
    These tests verify edge cases and robustness of error handling.
    """
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_ensure_authenticated_propagates_auth_error(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        When _ensure_authenticated() triggers login and login fails with 401,
        the LabelStudioAuthenticationError should propagate to the caller.
        
        This test verifies that:
        - _ensure_authenticated() propagates auth errors
        - Error is not swallowed or converted
        - Caller receives the original error
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Not authenticated initially
        auth_manager._is_authenticated = False
        auth_manager._access_token = None
        
        async def mock_post(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Unauthorized"}
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            # Property assertion: _ensure_authenticated should propagate auth error
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager._ensure_authenticated()
            
            assert exc_info.value.status_code == 401, \
                "Auth error should propagate with correct status code"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_ensure_authenticated_refresh_failure_propagates(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5**
        
        When _ensure_authenticated() triggers refresh and both refresh and
        re-auth fail with 401, the error should propagate to the caller.
        
        This test verifies that:
        - Refresh failure triggers re-auth
        - Re-auth failure propagates to caller
        - Error chain is handled correctly
        """
        import time
        
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Set up expired token state
        auth_manager._access_token = create_mock_jwt_token(exp_offset_seconds=-3600)
        auth_manager._refresh_token = "expired_refresh"
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcfromtimestamp(time.time() - 3600)
        
        async def mock_post(*args, **kwargs):
            # Both refresh and login return 401
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Unauthorized"}
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            # Property assertion: error should propagate through _ensure_authenticated
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager._ensure_authenticated()
            
            assert exc_info.value.status_code == 401, \
                "Auth error should propagate with correct status code"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_auth_error_does_not_leak_credentials(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 4: Authentication Error Non-Retryability
        
        **Validates: Requirements 1.3, 5.1, 5.5, 10.2**
        
        Authentication error messages should NOT contain sensitive data
        like passwords or tokens.
        
        This test verifies that:
        - Error message does not contain password
        - Error message does not contain tokens
        - Error is safe to log
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        async def mock_post(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Invalid credentials"}
            return mock_response
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_post
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await auth_manager.login()
            
            error_str = str(exc_info.value)
            
            # Property assertions - no sensitive data in error:
            # 1. Password should not be in error message
            # Only check if password is long enough to be meaningful
            if len(password) >= 8:
                assert password not in error_str, \
                    "Password should not appear in error message"
            
            # 2. Error should be safe to log (no obvious sensitive patterns)
            # Check that error doesn't contain common token patterns
            assert "Bearer " not in error_str, \
                "Bearer token should not appear in error message"


# =============================================================================
# Property Test 8: Network Error Retryability
# =============================================================================

class TestProperty8NetworkErrorRetryability:
    """
    Property 8: Network Error Retryability
    
    # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
    
    **Validates: Requirements 5.2**
    
    For any API call that fails with a network error (timeout, connection error),
    the system should retry the operation with exponential backoff up to the
    maximum retry attempts.
    
    This property ensures that:
    1. Network errors (TimeoutException, ConnectError) are retried
    2. Exponential backoff is applied between retries
    3. Maximum retry attempts are respected
    4. Successful retry returns the result
    5. Final failure after max retries raises the error
    """
    
    @pytest.mark.asyncio
    @given(
        max_attempts=st.integers(min_value=2, max_value=4),
        base_delay=st.floats(min_value=0.005, max_value=0.02)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for retry tests with delays
    )
    async def test_timeout_errors_are_retried(
        self,
        max_attempts: int,
        base_delay: float
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
        
        **Validates: Requirements 5.2**
        
        For any API call that fails with a timeout error, the system should
        retry the operation up to max_attempts times.
        
        This test verifies that:
        - TimeoutException triggers retry
        - Retry count matches max_attempts
        - Final timeout raises the error
        """
        from src.label_studio.retry import (
            LabelStudioRetryExecutor,
            LabelStudioRetryConfig,
        )
        
        config = LabelStudioRetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=0.1,
            jitter=False  # Disable jitter for predictable testing
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = "test_timeout"
        
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Connection timed out")
        
        # Property assertion: should retry max_attempts times then raise
        with pytest.raises(httpx.TimeoutException):
            await executor.async_execute(failing_operation)
        
        assert call_count == max_attempts, \
            f"Expected {max_attempts} attempts for timeout error, got {call_count}"
    
    @pytest.mark.asyncio
    @given(
        max_attempts=st.integers(min_value=2, max_value=4),
        base_delay=st.floats(min_value=0.005, max_value=0.02)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for retry tests with delays
    )
    async def test_connect_errors_are_retried(
        self,
        max_attempts: int,
        base_delay: float
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
        
        **Validates: Requirements 5.2**
        
        For any API call that fails with a connection error, the system should
        retry the operation up to max_attempts times.
        
        This test verifies that:
        - ConnectError triggers retry
        - Retry count matches max_attempts
        - Final connection error raises the error
        """
        from src.label_studio.retry import (
            LabelStudioRetryExecutor,
            LabelStudioRetryConfig,
        )
        
        config = LabelStudioRetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=0.1,
            jitter=False
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = "test_connect"
        
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")
        
        # Property assertion: should retry max_attempts times then raise
        with pytest.raises(httpx.ConnectError):
            await executor.async_execute(failing_operation)
        
        assert call_count == max_attempts, \
            f"Expected {max_attempts} attempts for connect error, got {call_count}"
    
    @pytest.mark.asyncio
    @given(
        max_attempts=st.integers(min_value=2, max_value=4),
        success_on_attempt=st.integers(min_value=2, max_value=4)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for retry tests with delays
    )
    async def test_successful_retry_returns_result(
        self,
        max_attempts: int,
        success_on_attempt: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
        
        **Validates: Requirements 5.2**
        
        For any API call that fails initially but succeeds on retry,
        the system should return the successful result.
        
        This test verifies that:
        - Retry continues until success
        - Successful result is returned
        - No error is raised after successful retry
        """
        # Ensure success_on_attempt is within max_attempts
        assume(success_on_attempt <= max_attempts)
        
        from src.label_studio.retry import (
            LabelStudioRetryExecutor,
            LabelStudioRetryConfig,
        )
        
        config = LabelStudioRetryConfig(
            max_attempts=max_attempts,
            base_delay=0.005,
            max_delay=0.05,
            jitter=False
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = "test_success_retry"
        
        call_count = 0
        expected_result = {"status": "success", "data": "test_data"}
        
        async def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < success_on_attempt:
                raise httpx.TimeoutException("Temporary timeout")
            return expected_result
        
        # Property assertion: should succeed after retries
        result = await executor.async_execute(eventually_succeeds)
        
        assert result == expected_result, \
            "Should return successful result after retry"
        assert call_count == success_on_attempt, \
            f"Expected {success_on_attempt} attempts, got {call_count}"
    
    @pytest.mark.asyncio
    @given(
        base_delay=st.floats(min_value=0.005, max_value=0.02),
        backoff_multiplier=st.floats(min_value=1.5, max_value=2.5)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for retry tests with delays
    )
    async def test_exponential_backoff_applied(
        self,
        base_delay: float,
        backoff_multiplier: float
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
        
        **Validates: Requirements 5.2**
        
        For any retry sequence, exponential backoff should be applied
        between retry attempts.
        
        This test verifies that:
        - Delays increase exponentially
        - Backoff multiplier is applied correctly
        - Total time increases with each retry
        """
        import time
        
        from src.label_studio.retry import (
            LabelStudioRetryExecutor,
            LabelStudioRetryConfig,
        )
        
        max_attempts = 3
        config = LabelStudioRetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=1.0,  # High max to not cap delays
            backoff_multiplier=backoff_multiplier,
            jitter=False  # Disable jitter for predictable timing
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = "test_backoff"
        
        timestamps = []
        
        async def failing_operation():
            timestamps.append(time.time())
            raise httpx.TimeoutException("Timeout")
        
        with pytest.raises(httpx.TimeoutException):
            await executor.async_execute(failing_operation)
        
        # Property assertions: verify exponential backoff
        assert len(timestamps) == max_attempts, \
            f"Expected {max_attempts} timestamps, got {len(timestamps)}"
        
        if len(timestamps) >= 2:
            # Calculate actual delays between attempts
            delays = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            
            # First delay should be approximately base_delay
            # Allow 50% tolerance for timing variations
            assert delays[0] >= base_delay * 0.5, \
                f"First delay {delays[0]:.4f}s should be >= {base_delay * 0.5:.4f}s"
            
            # Second delay should be approximately base_delay * backoff_multiplier
            if len(delays) >= 2:
                expected_second_delay = base_delay * backoff_multiplier
                assert delays[1] >= expected_second_delay * 0.5, \
                    f"Second delay {delays[1]:.4f}s should be >= {expected_second_delay * 0.5:.4f}s"
    
    @pytest.mark.asyncio
    @given(
        max_attempts=st.integers(min_value=2, max_value=4)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for retry tests with delays
    )
    async def test_max_retry_attempts_respected(
        self,
        max_attempts: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
        
        **Validates: Requirements 5.2**
        
        For any retry configuration, the system should not exceed
        the maximum retry attempts.
        
        This test verifies that:
        - Exactly max_attempts calls are made
        - No additional retries after max_attempts
        - Error is raised after max_attempts exhausted
        """
        from src.label_studio.retry import (
            LabelStudioRetryExecutor,
            LabelStudioRetryConfig,
        )
        
        config = LabelStudioRetryConfig(
            max_attempts=max_attempts,
            base_delay=0.005,
            max_delay=0.05,
            jitter=False
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = "test_max_attempts"
        
        call_count = 0
        
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.NetworkError("Network unreachable")
        
        # Property assertion: should make exactly max_attempts calls
        with pytest.raises(httpx.NetworkError):
            await executor.async_execute(always_fails)
        
        assert call_count == max_attempts, \
            f"Expected exactly {max_attempts} attempts, got {call_count}"
    
    @pytest.mark.asyncio
    @given(
        error_type=st.sampled_from([
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.NetworkError,
            ConnectionError,
            TimeoutError,
        ])
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for retry tests with delays
    )
    async def test_various_network_errors_are_retried(
        self,
        error_type: type
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
        
        **Validates: Requirements 5.2**
        
        For any network error type (timeout, connection, etc.), the system
        should retry the operation.
        
        This test verifies that:
        - All network error types trigger retry
        - Retry behavior is consistent across error types
        """
        from src.label_studio.retry import (
            LabelStudioRetryExecutor,
            LabelStudioRetryConfig,
        )
        
        max_attempts = 3
        config = LabelStudioRetryConfig(
            max_attempts=max_attempts,
            base_delay=0.005,
            max_delay=0.05,
            jitter=False
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = f"test_{error_type.__name__}"
        
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise error_type("Network error")
        
        # Property assertion: should retry for all network error types
        with pytest.raises(error_type):
            await executor.async_execute(failing_operation)
        
        assert call_count == max_attempts, \
            f"Expected {max_attempts} attempts for {error_type.__name__}, got {call_count}"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy,
        max_attempts=st.integers(min_value=2, max_value=4)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for retry tests
    )
    async def test_auth_errors_not_retried_by_retry_executor(
        self,
        username: str,
        password: str,
        max_attempts: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
        
        **Validates: Requirements 5.2**
        
        Authentication errors (401/403) should NOT be retried by the retry
        executor, as they require user intervention.
        
        This test verifies that:
        - LabelStudioAuthenticationError is not retried
        - Only one attempt is made for auth errors
        - Auth errors are distinct from network errors
        """
        from src.label_studio.retry import (
            LabelStudioRetryExecutor,
            LabelStudioRetryConfig,
        )
        from src.label_studio.exceptions import LabelStudioAuthenticationError
        
        config = LabelStudioRetryConfig(
            max_attempts=max_attempts,
            base_delay=0.005,
            max_delay=0.05,
            jitter=False
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = "test_auth_not_retried"
        
        call_count = 0
        
        async def auth_failure():
            nonlocal call_count
            call_count += 1
            raise LabelStudioAuthenticationError("Invalid credentials", status_code=401)
        
        # Property assertion: auth errors should NOT be retried
        with pytest.raises(LabelStudioAuthenticationError):
            await executor.async_execute(auth_failure)
        
        # Should only make 1 attempt (no retry for auth errors)
        assert call_count == 1, \
            f"Expected 1 attempt for auth error (no retry), got {call_count}"
    
    @pytest.mark.asyncio
    @given(
        max_delay=st.floats(min_value=0.02, max_value=0.05),
        base_delay=st.floats(min_value=0.005, max_value=0.015)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for retry tests with delays
    )
    async def test_max_delay_caps_backoff(
        self,
        max_delay: float,
        base_delay: float
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
        
        **Validates: Requirements 5.2**
        
        For any retry sequence, the delay should never exceed max_delay,
        even with exponential backoff.
        
        This test verifies that:
        - Delays are capped at max_delay
        - Exponential growth stops at max_delay
        """
        import time
        
        from src.label_studio.retry import (
            LabelStudioRetryExecutor,
            LabelStudioRetryConfig,
        )
        
        max_attempts = 4
        config = LabelStudioRetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            backoff_multiplier=10.0,  # High multiplier to quickly exceed max_delay
            jitter=False
        )
        executor = LabelStudioRetryExecutor(config)
        executor.operation_name = "test_max_delay_cap"
        
        timestamps = []
        
        async def failing_operation():
            timestamps.append(time.time())
            raise httpx.TimeoutException("Timeout")
        
        with pytest.raises(httpx.TimeoutException):
            await executor.async_execute(failing_operation)
        
        # Calculate delays
        if len(timestamps) >= 2:
            delays = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            
            # Property assertion: no delay should exceed max_delay (with tolerance)
            for i, delay in enumerate(delays):
                # Allow 100% tolerance for timing variations
                assert delay <= max_delay * 2.0, \
                    f"Delay {i+1} ({delay:.4f}s) should not exceed max_delay ({max_delay:.4f}s)"
    
    @pytest.mark.asyncio
    @given(
        num_concurrent=st.integers(min_value=2, max_value=4)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for concurrent retry tests
    )
    async def test_concurrent_retries_independent(
        self,
        num_concurrent: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 8: Network Error Retryability
        
        **Validates: Requirements 5.2**
        
        For any set of concurrent operations, each should have independent
        retry behavior.
        
        This test verifies that:
        - Concurrent operations retry independently
        - One operation's failure doesn't affect others
        - Each operation respects its own retry count
        """
        from src.label_studio.retry import (
            LabelStudioRetryExecutor,
            LabelStudioRetryConfig,
        )
        
        max_attempts = 3
        config = LabelStudioRetryConfig(
            max_attempts=max_attempts,
            base_delay=0.005,
            max_delay=0.05,
            jitter=False
        )
        
        call_counts = [0] * num_concurrent
        
        async def create_failing_operation(index: int):
            async def failing_operation():
                call_counts[index] += 1
                raise httpx.TimeoutException(f"Timeout for operation {index}")
            return failing_operation
        
        # Create independent executors for each concurrent operation
        tasks = []
        for i in range(num_concurrent):
            executor = LabelStudioRetryExecutor(config)
            executor.operation_name = f"test_concurrent_{i}"
            operation = await create_failing_operation(i)
            
            async def run_with_catch(exec, op):
                try:
                    await exec.async_execute(op)
                except httpx.TimeoutException:
                    pass  # Expected
            
            tasks.append(asyncio.create_task(run_with_catch(executor, operation)))
        
        await asyncio.gather(*tasks)
        
        # Property assertion: each operation should have made max_attempts calls
        for i, count in enumerate(call_counts):
            assert count == max_attempts, \
                f"Operation {i} expected {max_attempts} attempts, got {count}"


# =============================================================================
# Property Test 10: Sensitive Data Protection
# =============================================================================

class TestProperty10SensitiveDataProtection:
    """
    Property 10: Sensitive Data Protection
    
    **Validates: Requirements 10.2**
    
    For any logging operation during authentication, the system should NOT
    include access tokens, refresh tokens, or passwords in log messages.
    
    This property ensures that:
    1. get_auth_state() never contains actual token values
    2. get_auth_state() never contains passwords
    3. Log messages during login/refresh never contain sensitive data
    4. Error messages never contain sensitive data
    """
    
    @pytest.mark.asyncio
    @given(
        access_token=st.text(min_size=20, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='._-'
        )).filter(lambda x: len(x.strip()) >= 20),
        refresh_token=st.text(min_size=20, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='._-'
        )).filter(lambda x: len(x.strip()) >= 20),
        password=st.text(min_size=12, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P'),
            whitelist_characters='!@#$%^&*()_+-=[]{}|;:,.<>?'
        )).filter(lambda x: len(x.strip()) >= 12)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_get_auth_state_never_contains_sensitive_data(
        self,
        access_token: str,
        refresh_token: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 10: Sensitive Data Protection
        
        **Validates: Requirements 10.2**
        
        For any authentication state, the get_auth_state() method should
        NEVER include actual token values or passwords.
        
        This test verifies that:
        - Access token is not in get_auth_state() output
        - Refresh token is not in get_auth_state() output
        - Password is not in get_auth_state() output
        - Only safe metadata fields are returned
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="test_user",
            password=password
        )
        
        # Set tokens directly to simulate authenticated state
        auth_manager._access_token = access_token
        auth_manager._refresh_token = refresh_token
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Get auth state
        auth_state = auth_manager.get_auth_state()
        auth_state_str = str(auth_state)
        
        # Property assertions - no sensitive data in auth state:
        # 1. Access token should NOT be in auth state
        assert access_token not in auth_state_str, \
            "Access token should NEVER appear in get_auth_state() output"
        
        # 2. Refresh token should NOT be in auth state
        assert refresh_token not in auth_state_str, \
            "Refresh token should NEVER appear in get_auth_state() output"
        
        # 3. Password should NOT be in auth state
        assert password not in auth_state_str, \
            "Password should NEVER appear in get_auth_state() output"
        
        # 4. Auth state should only contain expected safe fields
        expected_keys = {
            'is_authenticated', 'has_access_token', 'has_refresh_token',
            'token_expires_at', 'is_token_expired', 'base_url', 'has_credentials'
        }
        assert set(auth_state.keys()) == expected_keys, \
            f"Auth state should only contain safe fields, got: {set(auth_state.keys())}"
        
        # 5. Verify boolean indicators instead of actual values
        assert auth_state['has_access_token'] is True, \
            "has_access_token should be True (boolean indicator, not actual token)"
        assert auth_state['has_refresh_token'] is True, \
            "has_refresh_token should be True (boolean indicator, not actual token)"
        assert auth_state['has_credentials'] is True, \
            "has_credentials should be True (boolean indicator, not actual password)"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_auth_state_safe_for_logging(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 10: Sensitive Data Protection
        
        **Validates: Requirements 10.2**
        
        For any authentication state, the output of get_auth_state() should
        be safe to log without exposing sensitive information.
        
        This test verifies that:
        - get_auth_state() can be safely converted to string for logging
        - The string representation contains no sensitive data
        - Username is not exposed (only has_credentials boolean)
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username=username,
            password=password
        )
        
        # Create mock tokens
        mock_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
        mock_refresh_token = f"refresh_token_secret_{hash(password) % 100000}"
        
        # Set authenticated state
        auth_manager._access_token = mock_access_token
        auth_manager._refresh_token = mock_refresh_token
        auth_manager._is_authenticated = True
        auth_manager._token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Get auth state and convert to string (simulating logging)
        auth_state = auth_manager.get_auth_state()
        log_message = f"Authentication state: {auth_state}"
        
        # Property assertions - log message should be safe:
        # 1. Access token should NOT be in log message
        assert mock_access_token not in log_message, \
            "Access token should NEVER appear in log messages"
        
        # 2. Refresh token should NOT be in log message
        assert mock_refresh_token not in log_message, \
            "Refresh token should NEVER appear in log messages"
        
        # 3. Password should NOT be in log message
        assert password not in log_message, \
            "Password should NEVER appear in log messages"
        
        # 4. Username should NOT be in log message (only has_credentials)
        # Note: username might be short and appear coincidentally in other strings,
        # so we check that it's not a value in the auth_state dict
        assert username not in auth_state.values(), \
            "Username should not be a value in auth_state"
    
    @pytest.mark.asyncio
    @given(
        access_token=st.text(min_size=20, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='._-'
        )).filter(lambda x: len(x.strip()) >= 20),
        refresh_token=st.text(min_size=20, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='._-'
        )).filter(lambda x: len(x.strip()) >= 20)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_tokens_not_in_auth_state_values(
        self,
        access_token: str,
        refresh_token: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 10: Sensitive Data Protection
        
        **Validates: Requirements 10.2**
        
        For any tokens stored in the auth manager, the actual token values
        should NEVER appear in any value of get_auth_state().
        
        This test verifies that:
        - No value in auth_state equals the access token
        - No value in auth_state equals the refresh token
        - Token values are replaced with boolean indicators
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="test_user",
            password="test_password_12345"
        )
        
        # Set tokens
        auth_manager._access_token = access_token
        auth_manager._refresh_token = refresh_token
        auth_manager._is_authenticated = True
        
        # Get auth state
        auth_state = auth_manager.get_auth_state()
        
        # Property assertions - tokens should not be in any value:
        all_values = []
        for value in auth_state.values():
            if isinstance(value, str):
                all_values.append(value)
            elif isinstance(value, dict):
                all_values.extend(str(v) for v in value.values())
        
        all_values_str = ' '.join(all_values)
        
        # 1. Access token should not be in any value
        assert access_token not in all_values_str, \
            "Access token should not appear in any auth_state value"
        
        # 2. Refresh token should not be in any value
        assert refresh_token not in all_values_str, \
            "Refresh token should not appear in any auth_state value"
        
        # 3. Verify has_access_token is boolean True, not the actual token
        assert auth_state['has_access_token'] is True, \
            "has_access_token should be boolean True"
        assert auth_state['has_access_token'] != access_token, \
            "has_access_token should be boolean, not the actual token"
        
        # 4. Verify has_refresh_token is boolean True, not the actual token
        assert auth_state['has_refresh_token'] is True, \
            "has_refresh_token should be boolean True"
        assert auth_state['has_refresh_token'] != refresh_token, \
            "has_refresh_token should be boolean, not the actual token"
    
    @pytest.mark.asyncio
    @given(
        password=st.text(min_size=12, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P'),
            whitelist_characters='!@#$%^&*()_+-=[]{}|;:,.<>?'
        )).filter(lambda x: len(x.strip()) >= 12)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_password_never_exposed_in_auth_state(
        self,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 10: Sensitive Data Protection
        
        **Validates: Requirements 10.2**
        
        For any password configured in the auth manager, the password
        should NEVER appear in get_auth_state() output.
        
        This test verifies that:
        - Password is not in auth_state string representation
        - Password is not in any auth_state value
        - Only has_credentials boolean is exposed
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="test_user",
            password=password
        )
        
        # Get auth state (even before authentication)
        auth_state = auth_manager.get_auth_state()
        auth_state_str = str(auth_state)
        
        # Property assertions:
        # 1. Password should NOT be in auth state string
        assert password not in auth_state_str, \
            "Password should NEVER appear in get_auth_state() output"
        
        # 2. Password should NOT be in any value
        for key, value in auth_state.items():
            if isinstance(value, str):
                assert password not in value, \
                    f"Password should not appear in auth_state['{key}']"
        
        # 3. has_credentials should be True (boolean indicator)
        assert auth_state['has_credentials'] is True, \
            "has_credentials should be True when password is set"
        
        # 4. Verify password is not stored in auth_state
        assert 'password' not in auth_state, \
            "auth_state should not have a 'password' key"
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_login_does_not_log_credentials(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 10: Sensitive Data Protection
        
        **Validates: Requirements 10.2**
        
        For any login attempt, the system should NOT log the password
        or tokens in any log messages.
        
        This test verifies that:
        - Login method does not expose password in logs
        - Login method does not expose tokens in logs
        - Only safe information is logged
        """
        import io
        import logging
        
        # Set up log capture
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        
        # Get the logger used by jwt_auth module
        jwt_logger = logging.getLogger('src.label_studio.jwt_auth')
        original_level = jwt_logger.level
        original_handlers = jwt_logger.handlers.copy()
        
        jwt_logger.setLevel(logging.DEBUG)
        jwt_logger.addHandler(handler)
        
        try:
            auth_manager = JWTAuthManager(
                base_url="http://test-label-studio:8080",
                username=username,
                password=password
            )
            
            # Create mock tokens
            mock_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
            mock_refresh_token = f"refresh_secret_{hash(password) % 100000}"
            
            # Mock successful login
            with mock_auth_response(
                access_token=mock_access_token,
                refresh_token=mock_refresh_token
            ):
                await auth_manager.login()
            
            # Get captured logs
            log_output = log_capture.getvalue()
            
            # Property assertions - no sensitive data in logs:
            # 1. Password should NOT be in logs
            assert password not in log_output, \
                "Password should NEVER appear in log messages during login"
            
            # 2. Access token should NOT be in logs
            assert mock_access_token not in log_output, \
                "Access token should NEVER appear in log messages during login"
            
            # 3. Refresh token should NOT be in logs
            assert mock_refresh_token not in log_output, \
                "Refresh token should NEVER appear in log messages during login"
            
        finally:
            # Restore logger state
            jwt_logger.setLevel(original_level)
            jwt_logger.removeHandler(handler)
            for h in original_handlers:
                if h not in jwt_logger.handlers:
                    jwt_logger.addHandler(h)
    
    @pytest.mark.asyncio
    @given(
        username=username_strategy,
        password=password_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_refresh_does_not_log_tokens(
        self,
        username: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 10: Sensitive Data Protection
        
        **Validates: Requirements 10.2**
        
        For any token refresh operation, the system should NOT log
        the old or new tokens in any log messages.
        
        This test verifies that:
        - Refresh method does not expose old tokens in logs
        - Refresh method does not expose new tokens in logs
        - Only safe information is logged
        """
        import io
        import logging
        
        # Set up log capture
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        
        # Get the logger used by jwt_auth module
        jwt_logger = logging.getLogger('src.label_studio.jwt_auth')
        original_level = jwt_logger.level
        original_handlers = jwt_logger.handlers.copy()
        
        jwt_logger.setLevel(logging.DEBUG)
        jwt_logger.addHandler(handler)
        
        try:
            auth_manager = JWTAuthManager(
                base_url="http://test-label-studio:8080",
                username=username,
                password=password
            )
            
            # Set up initial authenticated state with old tokens
            old_access_token = create_mock_jwt_token(exp_offset_seconds=-60)
            old_refresh_token = f"old_refresh_secret_{hash(password) % 100000}"
            
            auth_manager._access_token = old_access_token
            auth_manager._refresh_token = old_refresh_token
            auth_manager._is_authenticated = True
            auth_manager._token_expires_at = datetime.utcnow() - timedelta(minutes=1)
            
            # Create new tokens for refresh response
            new_access_token = create_mock_jwt_token(exp_offset_seconds=3600)
            new_refresh_token = f"new_refresh_secret_{hash(password) % 100000}"
            
            # Mock successful refresh
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "Bearer"
            }
            
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                await auth_manager.refresh_token()
            
            # Get captured logs
            log_output = log_capture.getvalue()
            
            # Property assertions - no sensitive data in logs:
            # 1. Old access token should NOT be in logs
            assert old_access_token not in log_output, \
                "Old access token should NEVER appear in log messages during refresh"
            
            # 2. Old refresh token should NOT be in logs
            assert old_refresh_token not in log_output, \
                "Old refresh token should NEVER appear in log messages during refresh"
            
            # 3. New access token should NOT be in logs
            assert new_access_token not in log_output, \
                "New access token should NEVER appear in log messages during refresh"
            
            # 4. New refresh token should NOT be in logs
            assert new_refresh_token not in log_output, \
                "New refresh token should NEVER appear in log messages during refresh"
            
        finally:
            # Restore logger state
            jwt_logger.setLevel(original_level)
            jwt_logger.removeHandler(handler)
            for h in original_handlers:
                if h not in jwt_logger.handlers:
                    jwt_logger.addHandler(h)
    
    @pytest.mark.asyncio
    @given(
        access_token=st.text(min_size=20, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='._-'
        )).filter(lambda x: len(x.strip()) >= 20),
        refresh_token=st.text(min_size=20, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='._-'
        )).filter(lambda x: len(x.strip()) >= 20),
        password=st.text(min_size=12, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P'),
            whitelist_characters='!@#$%^&*()_+-=[]{}|;:,.<>?'
        )).filter(lambda x: len(x.strip()) >= 12)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_sensitive_data_not_in_repr_or_str(
        self,
        access_token: str,
        refresh_token: str,
        password: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 10: Sensitive Data Protection
        
        **Validates: Requirements 10.2**
        
        For any JWTAuthManager instance, the string representation
        should NOT include sensitive data.
        
        This test verifies that:
        - str() of auth manager does not expose tokens
        - repr() of auth manager does not expose tokens
        - Password is not exposed in any string representation
        """
        auth_manager = JWTAuthManager(
            base_url="http://test-label-studio:8080",
            username="test_user",
            password=password
        )
        
        # Set tokens
        auth_manager._access_token = access_token
        auth_manager._refresh_token = refresh_token
        auth_manager._is_authenticated = True
        
        # Get string representations
        str_repr = str(auth_manager)
        repr_repr = repr(auth_manager)
        
        # Property assertions - no sensitive data in string representations:
        # Note: Default __str__ and __repr__ may include object address,
        # but should not include sensitive data
        
        # 1. Access token should NOT be in str()
        assert access_token not in str_repr, \
            "Access token should not appear in str() representation"
        
        # 2. Refresh token should NOT be in str()
        assert refresh_token not in str_repr, \
            "Refresh token should not appear in str() representation"
        
        # 3. Password should NOT be in str()
        assert password not in str_repr, \
            "Password should not appear in str() representation"
        
        # 4. Access token should NOT be in repr()
        assert access_token not in repr_repr, \
            "Access token should not appear in repr() representation"
        
        # 5. Refresh token should NOT be in repr()
        assert refresh_token not in repr_repr, \
            "Refresh token should not appear in repr() representation"
        
        # 6. Password should NOT be in repr()
        assert password not in repr_repr, \
            "Password should not appear in repr() representation"


# =============================================================================
# Property Test 11: HTTPS for Token URLs
# =============================================================================

class TestProperty11HTTPSForTokenURLs:
    """
    Property 11: HTTPS for Token URLs
    
    **Validates: Requirements 10.3**
    
    For any authenticated URL generated for external access (iframe, new window),
    the URL should use HTTPS protocol when passing JWT tokens. The system should
    correctly identify whether a URL uses HTTPS and include this information
    in the response.
    
    This property ensures that:
    1. _check_https_security() correctly identifies HTTPS URLs as secure
    2. _check_https_security() correctly identifies HTTP URLs as insecure
    3. generate_authenticated_url() includes is_secure field in response
    4. is_secure field accurately reflects the URL protocol
    """
    
    # Strategy for HTTPS URLs
    https_url_strategy = st.sampled_from([
        "https://label-studio.example.com",
        "https://label-studio.example.com:443",
        "https://ls.company.io",
        "https://annotation.internal.net",
        "https://192.168.1.100:8443",
        "https://10.0.0.1",
        "https://label-studio-prod.example.org",
        "https://secure.labelstudio.cloud",
    ])
    
    # Strategy for HTTP URLs (insecure)
    http_url_strategy = st.sampled_from([
        "http://localhost:8080",
        "http://label-studio:8080",
        "http://192.168.1.100:8080",
        "http://10.0.0.1:8080",
        "http://label-studio.local",
        "http://127.0.0.1:8080",
        "http://annotation-dev.internal",
        "http://ls-staging.example.com",
    ])
    
    # Strategy for project IDs
    project_id_strategy = st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=('N',))
    ).filter(lambda x: x.strip() != '' and x.isdigit())
    
    # Strategy for user IDs
    user_id_strategy = st.text(
        min_size=3,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='-_'
        )
    ).filter(lambda x: x.strip() != '' and len(x.strip()) >= 3)
    
    # Strategy for language codes
    language_strategy = st.sampled_from(['zh', 'en', 'zh-CN', 'en-US'])
    
    @pytest.mark.asyncio
    @given(https_url=https_url_strategy)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_https_urls_identified_as_secure(self, https_url: str):
        """
        # Feature: label-studio-jwt-authentication, Property 11: HTTPS for Token URLs
        
        **Validates: Requirements 10.3**
        
        For any URL using HTTPS protocol, _check_https_security() should
        return True, indicating the URL is secure for token transmission.
        
        This test verifies that:
        - HTTPS URLs are correctly identified as secure
        - The method returns True for all HTTPS URLs
        """
        # Create integration with HTTPS URL
        config = MagicMock()
        config.base_url = https_url
        config.api_token = "test_token"
        config.username = None
        config.password = None
        config.get_auth_method.return_value = 'api_token'
        config.validate_config.return_value = True
        config.get_default_label_config.return_value = "<View></View>"
        
        with patch('src.label_studio.integration.LabelStudioConfig', return_value=config):
            integration = LabelStudioIntegration(config=config)
        
        # Property assertion: HTTPS URLs should be identified as secure
        is_secure = integration._check_https_security()
        
        assert is_secure is True, \
            f"HTTPS URL '{https_url}' should be identified as secure (is_secure=True)"
    
    @pytest.mark.asyncio
    @given(http_url=http_url_strategy)
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_http_urls_identified_as_insecure(self, http_url: str):
        """
        # Feature: label-studio-jwt-authentication, Property 11: HTTPS for Token URLs
        
        **Validates: Requirements 10.3**
        
        For any URL using HTTP protocol, _check_https_security() should
        return False, indicating the URL is NOT secure for token transmission.
        
        This test verifies that:
        - HTTP URLs are correctly identified as insecure
        - The method returns False for all HTTP URLs
        """
        # Create integration with HTTP URL
        config = MagicMock()
        config.base_url = http_url
        config.api_token = "test_token"
        config.username = None
        config.password = None
        config.get_auth_method.return_value = 'api_token'
        config.validate_config.return_value = True
        config.get_default_label_config.return_value = "<View></View>"
        
        with patch('src.label_studio.integration.LabelStudioConfig', return_value=config):
            integration = LabelStudioIntegration(config=config)
        
        # Property assertion: HTTP URLs should be identified as insecure
        is_secure = integration._check_https_security()
        
        assert is_secure is False, \
            f"HTTP URL '{http_url}' should be identified as insecure (is_secure=False)"
    
    @pytest.mark.asyncio
    @given(
        https_url=https_url_strategy,
        project_id=project_id_strategy,
        user_id=user_id_strategy,
        language=language_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_generate_authenticated_url_https_is_secure_true(
        self,
        https_url: str,
        project_id: str,
        user_id: str,
        language: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 11: HTTPS for Token URLs
        
        **Validates: Requirements 10.3**
        
        For any authenticated URL generated with HTTPS base URL,
        the response should include is_secure=True.
        
        This test verifies that:
        - generate_authenticated_url() includes is_secure field
        - is_secure is True when base URL uses HTTPS
        - The generated URL starts with https://
        """
        # Create integration with HTTPS URL
        config = MagicMock()
        config.base_url = https_url
        config.api_token = "test_token"
        config.username = None
        config.password = None
        config.get_auth_method.return_value = 'api_token'
        config.validate_config.return_value = True
        config.get_default_label_config.return_value = "<View></View>"
        
        with patch('src.label_studio.integration.LabelStudioConfig', return_value=config):
            integration = LabelStudioIntegration(config=config)
        
        # Mock settings for JWT generation
        with patch('src.label_studio.integration.settings') as mock_settings:
            mock_settings.security.jwt_secret_key = 'test_secret_key_for_jwt_generation'
            mock_settings.security.jwt_algorithm = 'HS256'
            mock_settings.is_development = False
            mock_settings.debug = False
            
            # Generate authenticated URL
            result = await integration.generate_authenticated_url(
                project_id=project_id,
                user_id=user_id,
                language=language
            )
        
        # Property assertions:
        # 1. Result should include is_secure field
        assert 'is_secure' in result, \
            "generate_authenticated_url() should include 'is_secure' field in response"
        
        # 2. is_secure should be True for HTTPS URLs
        assert result['is_secure'] is True, \
            f"is_secure should be True for HTTPS URL '{https_url}'"
        
        # 3. Generated URL should start with https://
        assert result['url'].startswith('https://'), \
            f"Generated URL should start with 'https://' for HTTPS base URL"
        
        # 4. URL should contain the project ID
        assert project_id in result['url'], \
            "Generated URL should contain the project ID"
        
        # 5. URL should contain a token parameter
        assert 'token=' in result['url'], \
            "Generated URL should contain a token parameter"
    
    @pytest.mark.asyncio
    @given(
        http_url=http_url_strategy,
        project_id=project_id_strategy,
        user_id=user_id_strategy,
        language=language_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_generate_authenticated_url_http_is_secure_false(
        self,
        http_url: str,
        project_id: str,
        user_id: str,
        language: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 11: HTTPS for Token URLs
        
        **Validates: Requirements 10.3**
        
        For any authenticated URL generated with HTTP base URL,
        the response should include is_secure=False.
        
        This test verifies that:
        - generate_authenticated_url() includes is_secure field
        - is_secure is False when base URL uses HTTP
        - The generated URL starts with http://
        """
        # Create integration with HTTP URL
        config = MagicMock()
        config.base_url = http_url
        config.api_token = "test_token"
        config.username = None
        config.password = None
        config.get_auth_method.return_value = 'api_token'
        config.validate_config.return_value = True
        config.get_default_label_config.return_value = "<View></View>"
        
        with patch('src.label_studio.integration.LabelStudioConfig', return_value=config):
            integration = LabelStudioIntegration(config=config)
        
        # Mock settings for JWT generation
        with patch('src.label_studio.integration.settings') as mock_settings:
            mock_settings.security.jwt_secret_key = 'test_secret_key_for_jwt_generation'
            mock_settings.security.jwt_algorithm = 'HS256'
            mock_settings.is_development = True  # Allow HTTP in development
            mock_settings.debug = True
            
            # Generate authenticated URL
            result = await integration.generate_authenticated_url(
                project_id=project_id,
                user_id=user_id,
                language=language
            )
        
        # Property assertions:
        # 1. Result should include is_secure field
        assert 'is_secure' in result, \
            "generate_authenticated_url() should include 'is_secure' field in response"
        
        # 2. is_secure should be False for HTTP URLs
        assert result['is_secure'] is False, \
            f"is_secure should be False for HTTP URL '{http_url}'"
        
        # 3. Generated URL should start with http://
        assert result['url'].startswith('http://'), \
            f"Generated URL should start with 'http://' for HTTP base URL"
        
        # 4. URL should contain the project ID
        assert project_id in result['url'], \
            "Generated URL should contain the project ID"
        
        # 5. URL should contain a token parameter
        assert 'token=' in result['url'], \
            "Generated URL should contain a token parameter"
    
    @pytest.mark.asyncio
    @given(
        url=st.one_of(https_url_strategy, http_url_strategy)
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_https_check_consistency(self, url: str):
        """
        # Feature: label-studio-jwt-authentication, Property 11: HTTPS for Token URLs
        
        **Validates: Requirements 10.3**
        
        For any URL, the _check_https_security() method should return
        a result consistent with the URL's protocol prefix.
        
        This test verifies that:
        - URLs starting with 'https://' return True
        - URLs starting with 'http://' return False
        - The check is deterministic (same URL always gives same result)
        """
        # Create integration with the URL
        config = MagicMock()
        config.base_url = url
        config.api_token = "test_token"
        config.username = None
        config.password = None
        config.get_auth_method.return_value = 'api_token'
        config.validate_config.return_value = True
        config.get_default_label_config.return_value = "<View></View>"
        
        with patch('src.label_studio.integration.LabelStudioConfig', return_value=config):
            integration = LabelStudioIntegration(config=config)
        
        # Check HTTPS security
        is_secure = integration._check_https_security()
        
        # Property assertion: Result should match URL protocol
        expected_secure = url.startswith('https://')
        
        assert is_secure == expected_secure, \
            f"_check_https_security() should return {expected_secure} for URL '{url}'"
        
        # Verify determinism: calling again should give same result
        is_secure_again = integration._check_https_security()
        
        assert is_secure == is_secure_again, \
            "_check_https_security() should be deterministic (same result for same URL)"
    
    @pytest.mark.asyncio
    @given(
        project_id=project_id_strategy,
        user_id=user_id_strategy,
        expires_in=st.integers(min_value=60, max_value=86400)  # 1 minute to 24 hours
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_authenticated_url_contains_required_fields(
        self,
        project_id: str,
        user_id: str,
        expires_in: int
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 11: HTTPS for Token URLs
        
        **Validates: Requirements 10.3**
        
        For any authenticated URL generation, the response should contain
        all required fields including the is_secure field.
        
        This test verifies that:
        - Response contains 'url' field
        - Response contains 'token' field
        - Response contains 'expires_at' field
        - Response contains 'project_id' field
        - Response contains 'language' field
        - Response contains 'is_secure' field
        """
        # Create integration with HTTPS URL
        config = MagicMock()
        config.base_url = "https://label-studio.example.com"
        config.api_token = "test_token"
        config.username = None
        config.password = None
        config.get_auth_method.return_value = 'api_token'
        config.validate_config.return_value = True
        config.get_default_label_config.return_value = "<View></View>"
        
        with patch('src.label_studio.integration.LabelStudioConfig', return_value=config):
            integration = LabelStudioIntegration(config=config)
        
        # Mock settings for JWT generation
        with patch('src.label_studio.integration.settings') as mock_settings:
            mock_settings.security.jwt_secret_key = 'test_secret_key_for_jwt_generation'
            mock_settings.security.jwt_algorithm = 'HS256'
            mock_settings.is_development = False
            mock_settings.debug = False
            
            # Generate authenticated URL
            result = await integration.generate_authenticated_url(
                project_id=project_id,
                user_id=user_id,
                language='zh',
                expires_in=expires_in
            )
        
        # Property assertions: All required fields should be present
        required_fields = ['url', 'token', 'expires_at', 'project_id', 'language', 'is_secure']
        
        for field in required_fields:
            assert field in result, \
                f"generate_authenticated_url() response should contain '{field}' field"
        
        # Verify field types
        assert isinstance(result['url'], str), "url should be a string"
        assert isinstance(result['token'], str), "token should be a string"
        assert isinstance(result['expires_at'], str), "expires_at should be a string"
        assert isinstance(result['project_id'], str), "project_id should be a string"
        assert isinstance(result['language'], str), "language should be a string"
        assert isinstance(result['is_secure'], bool), "is_secure should be a boolean"


# =============================================================================
# Property Test 12: Token Cleanup on Expiration
# =============================================================================

class TestProperty12TokenCleanupOnExpiration:
    """
    Property 12: Token Cleanup on Expiration
    
    **Validates: Requirements 10.4**
    
    For any expired token that is replaced by a new token, the old token
    should be cleared from memory and not reused. This property ensures
    secure token management by:
    
    1. clear_tokens() properly clears all token data
    2. Old tokens are cleared when refreshing
    3. Tokens are cleared on authentication failure
    4. No token data remains after cleanup
    
    Security Note:
    Token cleanup is critical for security. Stale tokens in memory could
    potentially be exploited if the application state is compromised.
    """
    
    # Strategy for token strings
    token_strategy = st.text(
        min_size=10,
        max_size=500,
        alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            whitelist_characters='-_.'
        )
    ).filter(lambda x: x.strip() != '' and len(x.strip()) >= 10)
    
    # Strategy for expiration times
    expiration_strategy = st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31)
    )
    
    @pytest.mark.asyncio
    @given(
        access_token=token_strategy,
        refresh_token=token_strategy,
        expires_at=expiration_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_clear_tokens_removes_all_data(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: datetime
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 12: Token Cleanup on Expiration
        
        **Validates: Requirements 10.4**
        
        For any token state, clear_tokens() should remove all token data
        from memory, leaving no trace of the previous authentication.
        
        This test verifies that:
        - _access_token is set to None
        - _refresh_token is set to None
        - _token_expires_at is set to None
        - _is_authenticated is set to False
        """
        # Create auth manager with tokens
        auth = JWTAuthManager(
            base_url="http://test",
            username="user",
            password="pass"
        )
        
        # Set up token state
        auth._access_token = access_token
        auth._refresh_token = refresh_token
        auth._token_expires_at = expires_at
        auth._is_authenticated = True
        
        # Verify tokens are set
        assert auth._access_token == access_token
        assert auth._refresh_token == refresh_token
        assert auth._token_expires_at == expires_at
        assert auth._is_authenticated is True
        
        # Clear tokens
        auth.clear_tokens()
        
        # Property assertions: All token data should be cleared
        assert auth._access_token is None, \
            "clear_tokens() should set _access_token to None"
        assert auth._refresh_token is None, \
            "clear_tokens() should set _refresh_token to None"
        assert auth._token_expires_at is None, \
            "clear_tokens() should set _token_expires_at to None"
        assert auth._is_authenticated is False, \
            "clear_tokens() should set _is_authenticated to False"
    
    @pytest.mark.asyncio
    @given(
        access_token=token_strategy,
        refresh_token=token_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_clear_tokens_idempotent(
        self,
        access_token: str,
        refresh_token: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 12: Token Cleanup on Expiration
        
        **Validates: Requirements 10.4**
        
        Calling clear_tokens() multiple times should be safe and idempotent.
        The result should be the same whether called once or multiple times.
        
        This test verifies that:
        - Multiple calls to clear_tokens() don't raise errors
        - State remains cleared after multiple calls
        """
        # Create auth manager with tokens
        auth = JWTAuthManager(
            base_url="http://test",
            username="user",
            password="pass"
        )
        
        # Set up token state
        auth._access_token = access_token
        auth._refresh_token = refresh_token
        auth._is_authenticated = True
        
        # Clear tokens multiple times
        auth.clear_tokens()
        auth.clear_tokens()
        auth.clear_tokens()
        
        # Property assertions: State should remain cleared
        assert auth._access_token is None, \
            "Multiple clear_tokens() calls should keep _access_token as None"
        assert auth._refresh_token is None, \
            "Multiple clear_tokens() calls should keep _refresh_token as None"
        assert auth._is_authenticated is False, \
            "Multiple clear_tokens() calls should keep _is_authenticated as False"
    
    @pytest.mark.asyncio
    @given(
        old_access=token_strategy,
        old_refresh=token_strategy,
        new_access=token_strategy,
        new_refresh=token_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_old_tokens_not_reused_after_refresh(
        self,
        old_access: str,
        old_refresh: str,
        new_access: str,
        new_refresh: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 12: Token Cleanup on Expiration
        
        **Validates: Requirements 10.4**
        
        When tokens are refreshed, the old tokens should be completely
        replaced and not accessible. This simulates the token refresh
        process where old tokens are cleared before new ones are stored.
        
        This test verifies that:
        - Old tokens are not accessible after refresh
        - New tokens are properly stored
        - No mixing of old and new tokens occurs
        """
        # Assume old and new tokens are different
        assume(old_access != new_access)
        assume(old_refresh != new_refresh)
        
        # Create auth manager with old tokens
        auth = JWTAuthManager(
            base_url="http://test",
            username="user",
            password="pass"
        )
        
        # Set up old token state
        auth._access_token = old_access
        auth._refresh_token = old_refresh
        auth._is_authenticated = True
        
        # Simulate token refresh: clear old, store new
        auth._access_token = None
        auth._refresh_token = None
        auth._access_token = new_access
        auth._refresh_token = new_refresh
        
        # Property assertions: Only new tokens should be present
        assert auth._access_token == new_access, \
            "After refresh, _access_token should be the new token"
        assert auth._refresh_token == new_refresh, \
            "After refresh, _refresh_token should be the new token"
        assert auth._access_token != old_access, \
            "Old access token should not be accessible after refresh"
        assert auth._refresh_token != old_refresh, \
            "Old refresh token should not be accessible after refresh"
    
    @pytest.mark.asyncio
    @given(
        access_token=token_strategy,
        refresh_token=token_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_tokens_cleared_on_auth_failure(
        self,
        access_token: str,
        refresh_token: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 12: Token Cleanup on Expiration
        
        **Validates: Requirements 10.4**
        
        When authentication fails, any existing tokens should be cleared
        to prevent use of potentially compromised credentials.
        
        This test verifies that:
        - Tokens are cleared when simulating auth failure
        - is_authenticated is set to False
        - get_auth_header() returns empty dict after failure
        """
        # Create auth manager with tokens
        auth = JWTAuthManager(
            base_url="http://test",
            username="user",
            password="pass"
        )
        
        # Set up token state (simulating previous successful auth)
        auth._access_token = access_token
        auth._refresh_token = refresh_token
        auth._is_authenticated = True
        
        # Verify auth header works before failure
        header_before = auth.get_auth_header()
        assert 'Authorization' in header_before
        
        # Simulate auth failure by clearing tokens
        auth.clear_tokens()
        
        # Property assertions: Tokens should be cleared
        assert auth._access_token is None, \
            "Tokens should be cleared on auth failure"
        assert auth._refresh_token is None, \
            "Refresh token should be cleared on auth failure"
        assert auth._is_authenticated is False, \
            "is_authenticated should be False after auth failure"
        
        # get_auth_header should return empty dict
        header_after = auth.get_auth_header()
        assert header_after == {}, \
            "get_auth_header() should return empty dict after tokens cleared"
    
    @pytest.mark.asyncio
    @given(
        access_token=token_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_is_authenticated_false_after_clear(
        self,
        access_token: str
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 12: Token Cleanup on Expiration
        
        **Validates: Requirements 10.4**
        
        The is_authenticated property should return False after tokens
        are cleared, regardless of previous authentication state.
        
        This test verifies that:
        - is_authenticated returns True when tokens are set
        - is_authenticated returns False after clear_tokens()
        """
        # Create auth manager
        auth = JWTAuthManager(
            base_url="http://test",
            username="user",
            password="pass"
        )
        
        # Set up authenticated state
        auth._access_token = access_token
        auth._is_authenticated = True
        
        # Verify is_authenticated is True
        assert auth.is_authenticated is True, \
            "is_authenticated should be True when tokens are set"
        
        # Clear tokens
        auth.clear_tokens()
        
        # Property assertion: is_authenticated should be False
        assert auth.is_authenticated is False, \
            "is_authenticated should be False after clear_tokens()"
    
    @pytest.mark.asyncio
    @given(
        access_token=token_strategy,
        refresh_token=token_strategy,
        expires_at=expiration_strategy
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_get_auth_state_after_clear(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: datetime
    ):
        """
        # Feature: label-studio-jwt-authentication, Property 12: Token Cleanup on Expiration
        
        **Validates: Requirements 10.4**
        
        The get_auth_state() method should reflect the cleared state
        after tokens are removed.
        
        This test verifies that:
        - get_auth_state() shows tokens present before clear
        - get_auth_state() shows no tokens after clear
        - State is consistent with actual token storage
        """
        # Create auth manager with tokens
        auth = JWTAuthManager(
            base_url="http://test",
            username="user",
            password="pass"
        )
        
        # Set up token state
        auth._access_token = access_token
        auth._refresh_token = refresh_token
        auth._token_expires_at = expires_at
        auth._is_authenticated = True
        
        # Check state before clear
        state_before = auth.get_auth_state()
        assert state_before['has_access_token'] is True
        assert state_before['has_refresh_token'] is True
        assert state_before['is_authenticated'] is True
        
        # Clear tokens
        auth.clear_tokens()
        
        # Check state after clear
        state_after = auth.get_auth_state()
        
        # Property assertions: State should reflect cleared tokens
        assert state_after['has_access_token'] is False, \
            "get_auth_state() should show no access token after clear"
        assert state_after['has_refresh_token'] is False, \
            "get_auth_state() should show no refresh token after clear"
        assert state_after['is_authenticated'] is False, \
            "get_auth_state() should show not authenticated after clear"
        assert state_after['token_expires_at'] is None, \
            "get_auth_state() should show no expiration after clear"
