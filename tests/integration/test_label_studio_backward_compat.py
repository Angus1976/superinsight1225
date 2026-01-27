"""
Backward Compatibility Tests for Label Studio Authentication.

This module tests backward compatibility between JWT authentication and
legacy API token authentication, ensuring:
- API token authentication still works
- Switching between auth methods works correctly
- No breaking changes for existing deployments

Validates: Requirements 3.1, 3.2, 3.3, 3.4
"""

import asyncio
import logging
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.label_studio.integration import LabelStudioIntegration, ProjectConfig
from src.label_studio.config import LabelStudioConfig
from src.label_studio.exceptions import LabelStudioAuthenticationError

logger = logging.getLogger(__name__)


# Test configuration
LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")
LABEL_STUDIO_API_TOKEN = os.getenv("LABEL_STUDIO_API_TOKEN", "test-api-token")
LABEL_STUDIO_USERNAME = os.getenv("LABEL_STUDIO_USERNAME", "admin@example.com")
LABEL_STUDIO_PASSWORD = os.getenv("LABEL_STUDIO_PASSWORD", "admin")


@pytest.fixture
def api_token_config():
    """Fixture providing API token authentication configuration."""
    config = LabelStudioConfig()
    config.base_url = LABEL_STUDIO_URL
    config.api_token = LABEL_STUDIO_API_TOKEN
    config.username = None  # Force API token authentication
    config.password = None
    return config


@pytest.fixture
def jwt_config():
    """Fixture providing JWT authentication configuration."""
    config = LabelStudioConfig()
    config.base_url = LABEL_STUDIO_URL
    config.username = LABEL_STUDIO_USERNAME
    config.password = LABEL_STUDIO_PASSWORD
    config.api_token = None  # Force JWT authentication
    return config


@pytest.fixture
def both_auth_config():
    """Fixture providing both authentication methods (JWT should be preferred)."""
    config = LabelStudioConfig()
    config.base_url = LABEL_STUDIO_URL
    config.username = LABEL_STUDIO_USERNAME
    config.password = LABEL_STUDIO_PASSWORD
    config.api_token = LABEL_STUDIO_API_TOKEN
    return config


@pytest.mark.asyncio
class TestAPITokenAuthentication:
    """Test legacy API token authentication still works."""
    
    async def test_api_token_auth_method_detection(self, api_token_config):
        """
        Test that API token authentication is correctly detected.
        
        Validates: Requirements 3.1, 3.2
        """
        integration = LabelStudioIntegration(config=api_token_config)
        
        # Verify API token authentication is being used
        assert integration.auth_method == 'api_token'
        assert integration._jwt_auth_manager is None
        assert integration.api_token == LABEL_STUDIO_API_TOKEN
        
        logger.info("API token authentication correctly detected")
    
    async def test_api_token_header_format(self, api_token_config):
        """
        Test that API token uses correct header format.
        
        Validates: Requirements 3.3
        """
        integration = LabelStudioIntegration(config=api_token_config)
        
        # Get headers
        headers = await integration._get_headers()
        
        # Verify Token format (not Bearer)
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('Token ')
        assert headers['Authorization'] == f'Token {LABEL_STUDIO_API_TOKEN}'
        
        logger.info(f"API token header format correct: {headers['Authorization'][:20]}...")
    
    async def test_api_token_project_creation(self, api_token_config):
        """
        Test project creation with API token authentication.
        
        Validates: Requirements 3.1, 3.3
        """
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            
            # Mock successful project creation
            async def mock_post(url, **kwargs):
                if "/api/projects/" in url:
                    # Verify Token header format
                    auth_header = kwargs.get("headers", {}).get("Authorization", "")
                    assert auth_header.startswith("Token ")
                    
                    mock_response.status_code = 201
                    mock_response.json = MagicMock(return_value={
                        "id": 1,
                        "title": "Test Project",
                        "description": "Test",
                        "label_config": "",
                        "created_at": "2024-01-01T00:00:00Z",
                    })
                    return mock_response
                
                mock_response.status_code = 404
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post
            
            # Create integration and project
            integration = LabelStudioIntegration(config=api_token_config)
            
            project_config = ProjectConfig(
                title="API Token Test Project",
                description="Test with API token",
                annotation_type="text_classification"
            )
            
            project = await integration.create_project(project_config)
            
            # Verify project was created
            assert project is not None
            assert project.id == 1
            
            logger.info("Project creation with API token successful")


@pytest.mark.asyncio
class TestJWTAuthentication:
    """Test JWT authentication works correctly."""
    
    async def test_jwt_auth_method_detection(self, jwt_config):
        """
        Test that JWT authentication is correctly detected.
        
        Validates: Requirements 3.1, 3.2
        """
        integration = LabelStudioIntegration(config=jwt_config)
        
        # Verify JWT authentication is being used
        assert integration.auth_method == 'jwt'
        assert integration._jwt_auth_manager is not None
        assert integration.api_token is None
        
        logger.info("JWT authentication correctly detected")
    
    async def test_jwt_header_format(self, jwt_config):
        """
        Test that JWT uses correct header format.
        
        Validates: Requirements 3.3
        """
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            
            # Mock login response
            async def mock_post(url, **kwargs):
                if "/api/sessions/" in url:
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(return_value={
                        "access_token": "test-jwt-token",
                        "refresh_token": "test-refresh-token",
                        "token_type": "Bearer",
                        "expires_in": 3600,
                    })
                    return mock_response
                
                mock_response.status_code = 404
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post
            
            # Create integration
            integration = LabelStudioIntegration(config=jwt_config)
            
            # Get headers (this will trigger authentication)
            headers = await integration._get_headers()
            
            # Verify Bearer format (not Token)
            assert 'Authorization' in headers
            assert headers['Authorization'].startswith('Bearer ')
            assert headers['Authorization'] == 'Bearer test-jwt-token'
            
            logger.info(f"JWT header format correct: {headers['Authorization'][:20]}...")


@pytest.mark.asyncio
class TestAuthMethodSwitching:
    """Test switching between authentication methods."""
    
    async def test_jwt_preferred_when_both_configured(self, both_auth_config):
        """
        Test that JWT is preferred when both auth methods are configured.
        
        Validates: Requirements 3.2
        """
        integration = LabelStudioIntegration(config=both_auth_config)
        
        # Verify JWT is preferred
        assert integration.auth_method == 'jwt'
        assert integration._jwt_auth_manager is not None
        
        logger.info("JWT correctly preferred when both auth methods configured")
    
    async def test_fallback_to_api_token(self):
        """
        Test fallback to API token when JWT credentials are invalid.
        
        Validates: Requirements 3.2, 3.4
        """
        # Create config with invalid JWT credentials but valid API token
        config = LabelStudioConfig()
        config.base_url = LABEL_STUDIO_URL
        config.username = None  # Invalid JWT credentials
        config.password = None
        config.api_token = LABEL_STUDIO_API_TOKEN  # Valid API token
        
        integration = LabelStudioIntegration(config=config)
        
        # Should fall back to API token
        assert integration.auth_method == 'api_token'
        assert integration._jwt_auth_manager is None
        
        logger.info("Successfully fell back to API token")
    
    async def test_no_breaking_changes_for_api_token_users(self, api_token_config):
        """
        Test that existing API token users experience no breaking changes.
        
        This test verifies that code written for API token authentication
        continues to work without modification.
        
        Validates: Requirements 3.4
        """
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock()
            
            # Mock API responses
            async def mock_post(url, **kwargs):
                if "/api/projects/" in url:
                    mock_response.status_code = 201
                    mock_response.json = MagicMock(return_value={
                        "id": 1,
                        "title": "Test",
                        "description": "",
                        "label_config": "",
                        "created_at": "2024-01-01T00:00:00Z",
                    })
                    return mock_response
                
                mock_response.status_code = 404
                return mock_response
            
            async def mock_get(url, **kwargs):
                if "/api/projects/1/" in url:
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(return_value={
                        "id": 1,
                        "title": "Test",
                        "description": "",
                        "label_config": "",
                        "created_at": "2024-01-01T00:00:00Z",
                    })
                    return mock_response
                
                mock_response.status_code = 404
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post
            mock_client.return_value.__aenter__.return_value.get.side_effect = mock_get
            
            # Create integration (old way - just with API token)
            integration = LabelStudioIntegration(config=api_token_config)
            
            # Old code patterns should still work
            project_config = ProjectConfig(
                title="Backward Compat Test",
                description="Test backward compatibility",
                annotation_type="text_classification"
            )
            
            # Create project (old method)
            project = await integration.create_project(project_config)
            assert project is not None
            
            # Get project info (old method)
            info = await integration.get_project_info("1")
            assert info is not None
            
            logger.info("No breaking changes detected for API token users")


@pytest.mark.asyncio
class TestAuthMethodLogging:
    """Test that authentication method is logged correctly."""
    
    async def test_jwt_auth_logging(self, jwt_config, caplog):
        """
        Test that JWT authentication is logged.
        
        Validates: Requirements 3.2
        """
        with caplog.at_level(logging.INFO):
            integration = LabelStudioIntegration(config=jwt_config)
            
            # Check that JWT authentication was logged
            assert any("JWT authentication" in record.message for record in caplog.records)
            
            logger.info("JWT authentication logging verified")
    
    async def test_api_token_auth_logging(self, api_token_config, caplog):
        """
        Test that API token authentication is logged.
        
        Validates: Requirements 3.2
        """
        with caplog.at_level(logging.INFO):
            integration = LabelStudioIntegration(config=api_token_config)
            
            # Check that API token authentication was logged
            assert any("API token authentication" in record.message for record in caplog.records)
            
            logger.info("API token authentication logging verified")


@pytest.mark.asyncio
class TestConfigValidation:
    """Test configuration validation with different auth methods."""
    
    async def test_valid_jwt_config(self, jwt_config):
        """Test that valid JWT config passes validation."""
        assert jwt_config.validate_config() is True
        logger.info("Valid JWT config passed validation")
    
    async def test_valid_api_token_config(self, api_token_config):
        """Test that valid API token config passes validation."""
        assert api_token_config.validate_config() is True
        logger.info("Valid API token config passed validation")
    
    async def test_invalid_config_no_auth(self):
        """Test that config with no auth method fails validation."""
        config = LabelStudioConfig()
        config.base_url = LABEL_STUDIO_URL
        config.username = None
        config.password = None
        config.api_token = None
        
        assert config.validate_config() is False
        logger.info("Invalid config (no auth) correctly failed validation")
    
    async def test_get_auth_method_with_jwt(self, jwt_config):
        """Test get_auth_method returns 'jwt' for JWT config."""
        assert jwt_config.get_auth_method() == 'jwt'
        logger.info("get_auth_method correctly returned 'jwt'")
    
    async def test_get_auth_method_with_api_token(self, api_token_config):
        """Test get_auth_method returns 'api_token' for API token config."""
        assert api_token_config.get_auth_method() == 'api_token'
        logger.info("get_auth_method correctly returned 'api_token'")


if __name__ == "__main__":
    # Run backward compatibility tests
    pytest.main([__file__, "-v", "-s"])
