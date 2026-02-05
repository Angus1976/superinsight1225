"""
Error Scenario Tests for Label Studio JWT Authentication.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""

import asyncio
import logging
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt as pyjwt

from src.label_studio.integration import LabelStudioIntegration, ProjectConfig
from src.label_studio.config import LabelStudioConfig
from src.label_studio.jwt_auth import JWTAuthManager
from src.label_studio.exceptions import LabelStudioAuthenticationError

logger = logging.getLogger(__name__)

LABEL_STUDIO_URL = "http://localhost:8080"
LABEL_STUDIO_USERNAME = "admin@example.com"
LABEL_STUDIO_PASSWORD = "admin"


def generate_test_jwt_token(exp_minutes: int = 60, counter: int = 0) -> str:
    """Generate a test JWT token."""
    payload = {
        "user_id": 1,
        "email": LABEL_STUDIO_USERNAME,
        "exp": datetime.utcnow() + timedelta(minutes=exp_minutes),
        "iat": datetime.utcnow(),
        "counter": counter,
    }
    return pyjwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture
def jwt_config():
    """JWT authentication configuration."""
    config = LabelStudioConfig()
    config.base_url = LABEL_STUDIO_URL
    config.username = LABEL_STUDIO_USERNAME
    config.password = LABEL_STUDIO_PASSWORD
    config.api_token = None
    return config


@pytest.mark.asyncio
class TestInvalidCredentials:
    """Test handling of invalid credentials."""
    
    async def test_invalid_username_password(self, jwt_config):
        """Test authentication failure with invalid credentials."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            
            async def mock_post(url, **kwargs):
                if "/api/sessions/" in url:
                    mock_response.status_code = 401
                    mock_response.text = "Invalid credentials"
                    mock_response.json = MagicMock(return_value={"detail": "Invalid email or password"})
                    return mock_response
                mock_response.status_code = 404
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post
            
            invalid_config = LabelStudioConfig()
            invalid_config.base_url = LABEL_STUDIO_URL
            invalid_config.username = "invalid@example.com"
            invalid_config.password = "wrongpassword"
            invalid_config.api_token = None
            
            integration = LabelStudioIntegration(config=invalid_config)
            project_config = ProjectConfig(title="Should Fail", description="Test", annotation_type="text_classification")
            
            with pytest.raises(LabelStudioAuthenticationError) as exc_info:
                await integration.create_project(project_config)
            
            error = exc_info.value
            assert error.status_code == 401
            logger.info(f"Invalid credentials correctly rejected: {error.message}")


@pytest.mark.asyncio
class TestNetworkFailures:
    """Test handling of network failures."""
    
    async def test_connection_timeout(self, jwt_config):
        """Test handling of connection timeout."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            
            async def mock_post_timeout(url, **kwargs):
                raise httpx.TimeoutException("Connection timeout")
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post_timeout
            
            integration = LabelStudioIntegration(config=jwt_config)
            project_config = ProjectConfig(title="Timeout Test", description="Test", annotation_type="text_classification")
            
            with pytest.raises(httpx.TimeoutException):
                await integration.create_project(project_config)
            
            logger.info("Connection timeout correctly raised")


@pytest.mark.asyncio
class TestTokenExpiration:
    """Test handling of token expiration."""
    
    async def test_token_expiration_detection(self, jwt_config):
        """Test detection of expired token from 401 response."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock()
            
            call_count = {"login": 0, "refresh": 0, "project": 0}
            
            async def mock_post(url, **kwargs):
                if "/api/sessions/" in url and "/refresh" not in url:
                    call_count["login"] += 1
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(return_value={
                        "access_token": generate_test_jwt_token(60, call_count["login"]),
                        "refresh_token": generate_test_jwt_token(7*24*60, call_count["login"]),
                        "token_type": "Bearer",
                        "expires_in": 3600,
                    })
                    return mock_response
                elif "/api/sessions/refresh/" in url:
                    call_count["refresh"] += 1
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(return_value={
                        "access_token": generate_test_jwt_token(60, 100 + call_count["refresh"]),
                        "refresh_token": generate_test_jwt_token(7*24*60, 100 + call_count["refresh"]),
                        "token_type": "Bearer",
                        "expires_in": 3600,
                    })
                    return mock_response
                elif "/api/projects/" in url:
                    call_count["project"] += 1
                    if call_count["project"] == 1:
                        mock_response.status_code = 401
                        mock_response.text = "Token has expired"
                        mock_response.json = MagicMock(return_value={"detail": "Token has expired"})
                        return mock_response
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
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = mock_post
            
            integration = LabelStudioIntegration(config=jwt_config)
            project_config = ProjectConfig(title="Expiration Test", description="Test", annotation_type="text_classification")
            
            project = await integration.create_project(project_config)
            
            assert project is not None
            assert project.id == 1
            assert call_count["refresh"] == 1
            assert call_count["project"] == 2
            
            logger.info("Token expiration correctly handled with automatic refresh")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
