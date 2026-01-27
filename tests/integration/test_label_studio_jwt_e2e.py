"""
End-to-End Integration Tests for Label Studio JWT Authentication.

This module tests the complete JWT authentication flow with a real or mocked
Label Studio 1.22.0+ instance, including:
- Initial authentication
- Token refresh
- API operations with JWT
- Error handling and recovery

These tests validate Requirements: All (comprehensive integration testing)
"""

import asyncio
import logging
import os
import pytest
from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt as pyjwt

from src.label_studio.integration import LabelStudioIntegration, ProjectConfig
from src.label_studio.config import LabelStudioConfig
from src.label_studio.jwt_auth import JWTAuthManager
from src.label_studio.exceptions import (
    LabelStudioAuthenticationError,
    LabelStudioIntegrationError,
)

logger = logging.getLogger(__name__)


# Test configuration
LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")
LABEL_STUDIO_USERNAME = os.getenv("LABEL_STUDIO_USERNAME", "admin@example.com")
LABEL_STUDIO_PASSWORD = os.getenv("LABEL_STUDIO_PASSWORD", "admin")
USE_REAL_LABEL_STUDIO = os.getenv("USE_REAL_LABEL_STUDIO", "false").lower() == "true"


def generate_test_jwt_token(exp_minutes: int = 60) -> str:
    """Generate a test JWT token with specified expiration."""
    payload = {
        "user_id": 1,
        "email": LABEL_STUDIO_USERNAME,
        "exp": datetime.utcnow() + timedelta(minutes=exp_minutes),
        "iat": datetime.utcnow(),
    }
    return pyjwt.encode(payload, "test-secret", algorithm="HS256")


def generate_expired_jwt_token() -> str:
    """Generate an expired JWT token for testing."""
    payload = {
        "user_id": 1,
        "email": LABEL_STUDIO_USERNAME,
        "exp": datetime.utcnow() - timedelta(minutes=5),
        "iat": datetime.utcnow() - timedelta(minutes=65),
    }
    return pyjwt.encode(payload, "test-secret", algorithm="HS256")


class MockLabelStudioServer:
    """Mock Label Studio server for testing without real instance."""
    
    def __init__(self):
        self.token_counter = 0
        self.access_token = self._generate_unique_token(60)
        self.refresh_token = self._generate_unique_token(7 * 24 * 60)
        self.projects = {}
        self.next_project_id = 1
        self.login_count = 0
        self.refresh_count = 0
        self.api_call_count = 0
    
    def _generate_unique_token(self, exp_minutes: int) -> str:
        """Generate a unique JWT token."""
        self.token_counter += 1
        payload = {
            "user_id": 1,
            "email": LABEL_STUDIO_USERNAME,
            "exp": datetime.utcnow() + timedelta(minutes=exp_minutes),
            "iat": datetime.utcnow(),
            "counter": self.token_counter,  # Make each token unique
        }
        return pyjwt.encode(payload, "test-secret", algorithm="HS256")
    
    def reset(self):
        """Reset server state."""
        self.token_counter = 0
        self.access_token = self._generate_unique_token(60)
        self.refresh_token = self._generate_unique_token(7 * 24 * 60)
        self.projects = {}
        self.next_project_id = 1
        self.login_count = 0
        self.refresh_count = 0
        self.api_call_count = 0
    
    async def handle_login(self, request_data: dict) -> dict:
        """Handle /api/sessions/ login request."""
        self.login_count += 1
        
        email = request_data.get("email")
        password = request_data.get("password")
        
        if email == LABEL_STUDIO_USERNAME and password == LABEL_STUDIO_PASSWORD:
            # Generate new tokens
            self.access_token = self._generate_unique_token(60)
            self.refresh_token = self._generate_unique_token(7 * 24 * 60)
            
            return {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        else:
            raise httpx.HTTPStatusError(
                "Invalid credentials",
                request=MagicMock(),
                response=MagicMock(status_code=401, text="Invalid credentials"),
            )
    
    async def handle_refresh(self, request_data: dict) -> dict:
        """Handle /api/sessions/refresh/ token refresh request."""
        self.refresh_count += 1
        
        refresh_token = request_data.get("refresh")
        
        if refresh_token == self.refresh_token:
            # Generate new tokens
            self.access_token = self._generate_unique_token(60)
            self.refresh_token = self._generate_unique_token(7 * 24 * 60)
            
            return {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        else:
            raise httpx.HTTPStatusError(
                "Invalid refresh token",
                request=MagicMock(),
                response=MagicMock(status_code=401, text="Invalid refresh token"),
            )
    
    async def handle_create_project(self, request_data: dict, auth_header: str) -> dict:
        """Handle /api/projects/ create project request."""
        self.api_call_count += 1
        
        # Verify Bearer token
        if not auth_header.startswith("Bearer "):
            raise httpx.HTTPStatusError(
                "Invalid authorization header",
                request=MagicMock(),
                response=MagicMock(status_code=401, text="Invalid authorization header"),
            )
        
        token = auth_header.replace("Bearer ", "")
        if token != self.access_token:
            raise httpx.HTTPStatusError(
                "Invalid or expired token",
                request=MagicMock(),
                response=MagicMock(status_code=401, text="Token has expired"),
            )
        
        # Create project
        project_id = self.next_project_id
        self.next_project_id += 1
        
        project = {
            "id": project_id,
            "title": request_data.get("title", "Test Project"),
            "description": request_data.get("description", ""),
            "label_config": request_data.get("label_config", ""),
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self.projects[project_id] = project
        return project
    
    async def handle_get_project(self, project_id: int, auth_header: str) -> dict:
        """Handle /api/projects/{id}/ get project request."""
        self.api_call_count += 1
        
        # Verify Bearer token
        if not auth_header.startswith("Bearer "):
            raise httpx.HTTPStatusError(
                "Invalid authorization header",
                request=MagicMock(),
                response=MagicMock(status_code=401, text="Invalid authorization header"),
            )
        
        token = auth_header.replace("Bearer ", "")
        if token != self.access_token:
            raise httpx.HTTPStatusError(
                "Invalid or expired token",
                request=MagicMock(),
                response=MagicMock(status_code=401, text="Token has expired"),
            )
        
        # Get project
        if project_id not in self.projects:
            raise httpx.HTTPStatusError(
                "Project not found",
                request=MagicMock(),
                response=MagicMock(status_code=404, text="Project not found"),
            )
        
        return self.projects[project_id]


@pytest.fixture
def mock_label_studio():
    """Fixture providing a mock Label Studio server."""
    server = MockLabelStudioServer()
    yield server
    server.reset()


@pytest.fixture
def jwt_config():
    """Fixture providing JWT authentication configuration."""
    config = LabelStudioConfig()
    config.base_url = LABEL_STUDIO_URL
    config.username = LABEL_STUDIO_USERNAME
    config.password = LABEL_STUDIO_PASSWORD
    config.api_token = None  # Force JWT authentication
    return config


@pytest.mark.asyncio
@pytest.mark.skipif(not USE_REAL_LABEL_STUDIO, reason="Requires real Label Studio instance")
class TestRealLabelStudioJWT:
    """
    Tests with real Label Studio 1.22.0+ instance.
    
    These tests require:
    - Label Studio 1.22.0+ running at LABEL_STUDIO_URL
    - Valid credentials in LABEL_STUDIO_USERNAME and LABEL_STUDIO_PASSWORD
    - Environment variable USE_REAL_LABEL_STUDIO=true
    
    Run with: USE_REAL_LABEL_STUDIO=true pytest tests/integration/test_label_studio_jwt_e2e.py::TestRealLabelStudioJWT -v
    """
    
    async def test_complete_authentication_flow(self, jwt_config):
        """
        Test complete authentication flow with real Label Studio.
        
        Flow:
        1. Initial authentication with username/password
        2. Create a project using JWT token
        3. Verify project was created
        4. Clean up
        
        Validates: Requirements 1.1, 1.2, 1.4, 7.1
        """
        integration = LabelStudioIntegration(config=jwt_config)
        
        # Verify JWT authentication is being used
        assert integration.auth_method == 'jwt'
        assert integration._jwt_auth_manager is not None
        
        # Create a test project
        project_config = ProjectConfig(
            title=f"JWT E2E Test {datetime.utcnow().isoformat()}",
            description="End-to-end test project for JWT authentication",
            annotation_type="text_classification"
        )
        
        project = await integration.create_project(project_config)
        
        # Verify project was created
        assert project is not None
        assert project.id is not None
        assert project.title == project_config.title
        
        logger.info(f"Successfully created project {project.id} with JWT authentication")
        
        # Verify we're authenticated
        assert integration.is_jwt_authenticated
        
        # Clean up - delete project
        try:
            await integration.delete_project(str(project.id))
            logger.info(f"Cleaned up test project {project.id}")
        except Exception as e:
            logger.warning(f"Failed to clean up test project: {e}")
    
    async def test_token_refresh_flow(self, jwt_config):
        """
        Test automatic token refresh with real Label Studio.
        
        This test verifies that tokens are automatically refreshed
        when they expire or are about to expire.
        
        Note: This test may take time as it waits for token expiration.
        
        Validates: Requirements 2.1, 2.2, 2.5, 8.1, 8.2
        """
        integration = LabelStudioIntegration(config=jwt_config)
        auth_manager = integration._jwt_auth_manager
        
        # Initial authentication
        await auth_manager.login()
        initial_token = auth_manager._access_token
        
        logger.info("Initial authentication successful")
        
        # Force token to be considered expired by setting expiration to past
        auth_manager._token_expires_at = datetime.utcnow() - timedelta(minutes=5)
        
        # Make an API call that should trigger token refresh
        project_config = ProjectConfig(
            title=f"JWT Refresh Test {datetime.utcnow().isoformat()}",
            description="Test project for token refresh",
            annotation_type="text_classification"
        )
        
        project = await integration.create_project(project_config)
        
        # Verify token was refreshed
        refreshed_token = auth_manager._access_token
        assert refreshed_token != initial_token
        
        logger.info("Token was successfully refreshed")
        
        # Clean up
        try:
            await integration.delete_project(str(project.id))
        except Exception as e:
            logger.warning(f"Failed to clean up test project: {e}")
    
    async def test_multiple_api_calls(self, jwt_config):
        """
        Test multiple API calls with JWT authentication.
        
        Validates: Requirements 7.1, 7.2, 7.5
        """
        integration = LabelStudioIntegration(config=jwt_config)
        
        # Create multiple projects
        projects = []
        for i in range(3):
            project_config = ProjectConfig(
                title=f"JWT Multi-Call Test {i} {datetime.utcnow().isoformat()}",
                description=f"Test project {i}",
                annotation_type="text_classification"
            )
            
            project = await integration.create_project(project_config)
            projects.append(project)
            
            logger.info(f"Created project {i+1}/3: {project.id}")
        
        # Verify all projects were created
        assert len(projects) == 3
        for project in projects:
            assert project.id is not None
        
        # Get project info for each
        for project in projects:
            info = await integration.get_project_info(str(project.id))
            assert info is not None
            assert info.id == project.id
            
            logger.info(f"Retrieved info for project {project.id}")
        
        # Clean up
        for project in projects:
            try:
                await integration.delete_project(str(project.id))
                logger.info(f"Cleaned up project {project.id}")
            except Exception as e:
                logger.warning(f"Failed to clean up project {project.id}: {e}")


@pytest.mark.asyncio
class TestMockedLabelStudioJWT:
    """
    Tests with mocked Label Studio server.
    
    These tests don't require a real Label Studio instance and can run
    in CI/CD environments.
    """
    
    async def test_complete_flow_with_mock(self, mock_label_studio, jwt_config):
        """
        Test complete authentication flow with mocked server.
        
        Validates: Requirements 1.1, 1.2, 1.4, 2.1, 2.5, 7.1
        """
        with patch("httpx.AsyncClient") as mock_client:
            # Setup mock responses
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock()
            
            # Mock login response
            async def mock_post(url, **kwargs):
                mock_response = MagicMock()
                
                if "/api/sessions/" in url and "/refresh" not in url:
                    # Login request
                    request_data = kwargs.get("json", {})
                    response_data = await mock_label_studio.handle_login(request_data)
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(return_value=response_data)
                    return mock_response
                elif "/api/sessions/refresh/" in url:
                    # Refresh request
                    request_data = kwargs.get("json", {})
                    response_data = await mock_label_studio.handle_refresh(request_data)
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(return_value=response_data)
                    return mock_response
                elif "/api/projects/" in url:
                    # Create project request
                    request_data = kwargs.get("json", {})
                    auth_header = kwargs.get("headers", {}).get("Authorization", "")
                    response_data = await mock_label_studio.handle_create_project(
                        request_data, auth_header
                    )
                    mock_response.status_code = 201
                    mock_response.json = MagicMock(return_value=response_data)
                    return mock_response
                
                mock_response.status_code = 404
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post
            
            # Create integration and test
            integration = LabelStudioIntegration(config=jwt_config)
            
            # Verify JWT authentication is being used
            assert integration.auth_method == 'jwt'
            
            # Create a project
            project_config = ProjectConfig(
                title="Mock Test Project",
                description="Test project with mocked server",
                annotation_type="text_classification"
            )
            
            project = await integration.create_project(project_config)
            
            # Verify project was created
            assert project is not None
            assert project.id is not None
            
            # Verify authentication happened
            assert mock_label_studio.login_count == 1
            assert mock_label_studio.api_call_count == 1
    
    async def test_token_refresh_with_mock(self, mock_label_studio, jwt_config):
        """
        Test token refresh with mocked server.
        
        Validates: Requirements 2.1, 2.2, 2.3, 8.1, 8.2
        """
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            
            # Track which tokens were used
            tokens_used = []
            
            # Setup mock responses
            async def mock_post(url, **kwargs):
                mock_response = MagicMock()
                
                if "/api/sessions/" in url and "/refresh" not in url:
                    request_data = kwargs.get("json", {})
                    response_data = await mock_label_studio.handle_login(request_data)
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(return_value=response_data)
                    tokens_used.append(("login", response_data["access_token"]))
                    return mock_response
                elif "/api/sessions/refresh/" in url:
                    request_data = kwargs.get("json", {})
                    response_data = await mock_label_studio.handle_refresh(request_data)
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(return_value=response_data)
                    tokens_used.append(("refresh", response_data["access_token"]))
                    return mock_response
                elif "/api/projects/" in url:
                    request_data = kwargs.get("json", {})
                    auth_header = kwargs.get("headers", {}).get("Authorization", "")
                    response_data = await mock_label_studio.handle_create_project(
                        request_data, auth_header
                    )
                    mock_response.status_code = 201
                    mock_response.json = MagicMock(return_value=response_data)
                    return mock_response
                
                mock_response.status_code = 404
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post
            
            # Create integration
            integration = LabelStudioIntegration(config=jwt_config)
            auth_manager = integration._jwt_auth_manager
            
            # Initial authentication
            await auth_manager.login()
            initial_token = auth_manager._access_token
            
            # Verify initial login happened
            assert len(tokens_used) == 1
            assert tokens_used[0][0] == "login"
            
            # Force token to be expired
            auth_manager._token_expires_at = datetime.utcnow() - timedelta(minutes=5)
            
            # Manually call refresh_token to test it
            await auth_manager.refresh_token()
            
            # Verify token was refreshed
            refreshed_token = auth_manager._access_token
            assert refreshed_token != initial_token
            assert len(tokens_used) == 2
            assert tokens_used[1][0] == "refresh"
            assert mock_label_studio.refresh_count == 1
    
    async def test_error_handling_with_mock(self, mock_label_studio, jwt_config):
        """
        Test error handling with mocked server.
        
        Validates: Requirements 1.3, 5.1, 5.5
        """
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            
            # Mock invalid credentials
            async def mock_post_invalid(url, **kwargs):
                mock_response = MagicMock()
                
                if "/api/sessions/" in url:
                    mock_response.status_code = 401
                    mock_response.text = "Invalid credentials"
                    mock_response.json = MagicMock(return_value={"detail": "Invalid credentials"})
                    return mock_response
                
                mock_response.status_code = 404
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post_invalid
            
            # Create integration with invalid credentials
            invalid_config = LabelStudioConfig()
            invalid_config.base_url = LABEL_STUDIO_URL
            invalid_config.username = "invalid"
            invalid_config.password = "invalid"
            invalid_config.api_token = None
            
            integration = LabelStudioIntegration(config=invalid_config)
            
            # Attempt to create project should fail with authentication error
            project_config = ProjectConfig(
                title="Should Fail",
                description="This should fail",
                annotation_type="text_classification"
            )
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await integration.create_project(project_config)
            
            # Verify error message is clear
            assert "Invalid credentials" in str(exc_info.value) or "401" in str(exc_info.value)


@pytest.mark.asyncio
class TestConcurrentRequests:
    """Test concurrent API requests with JWT authentication."""
    
    async def test_concurrent_project_creation(self, mock_label_studio, jwt_config):
        """
        Test multiple concurrent project creation requests.
        
        Validates: Requirements 4.1, 4.2, 4.4, 4.5
        """
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            
            # Setup mock responses
            async def mock_post(url, **kwargs):
                mock_response = MagicMock()
                
                if "/api/sessions/" in url and "/refresh" not in url:
                    request_data = kwargs.get("json", {})
                    response_data = await mock_label_studio.handle_login(request_data)
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(return_value=response_data)
                    return mock_response
                elif "/api/projects/" in url:
                    request_data = kwargs.get("json", {})
                    auth_header = kwargs.get("headers", {}).get("Authorization", "")
                    response_data = await mock_label_studio.handle_create_project(
                        request_data, auth_header
                    )
                    mock_response.status_code = 201
                    mock_response.json = MagicMock(return_value=response_data)
                    return mock_response
                
                mock_response.status_code = 404
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post
            
            # Create integration
            integration = LabelStudioIntegration(config=jwt_config)
            
            # Create multiple projects concurrently
            async def create_project(i):
                project_config = ProjectConfig(
                    title=f"Concurrent Test {i}",
                    description=f"Concurrent project {i}",
                    annotation_type="text_classification"
                )
                return await integration.create_project(project_config)
            
            # Run 10 concurrent requests
            projects = await asyncio.gather(*[create_project(i) for i in range(10)])
            
            # Verify all projects were created
            assert len(projects) == 10
            for project in projects:
                assert project is not None
                assert project.id is not None
            
            # Verify only one login occurred (not 10)
            assert mock_label_studio.login_count == 1


if __name__ == "__main__":
    # Run tests with real Label Studio if configured
    if USE_REAL_LABEL_STUDIO:
        print(f"Running tests with real Label Studio at {LABEL_STUDIO_URL}")
        print(f"Username: {LABEL_STUDIO_USERNAME}")
        pytest.main([__file__, "-v", "-k", "TestRealLabelStudioJWT"])
    else:
        print("Running tests with mocked Label Studio")
        print("Set USE_REAL_LABEL_STUDIO=true to test with real instance")
        pytest.main([__file__, "-v", "-k", "TestMockedLabelStudioJWT"])
