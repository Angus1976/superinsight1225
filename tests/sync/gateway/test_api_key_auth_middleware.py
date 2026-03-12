"""
Tests for API Key Authentication Middleware.

Tests X-API-Key authentication, rate limiting, and call logging.
"""

import pytest
import time
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from src.sync.gateway.api_key_auth_middleware import (
    APIKeyAuthMiddleware,
    APIKeyRateLimiter
)
from src.sync.gateway.api_key_service import APIKeyService
from src.sync.models import APIKeyModel, APIKeyStatus


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    
    @app.get("/api/v1/external/test")
    async def external_endpoint(request: Request):
        return {"message": "success", "tenant_id": request.state.tenant_id}
    
    @app.get("/api/v1/internal/test")
    async def internal_endpoint():
        return {"message": "internal"}
    
    return app


@pytest.fixture
def mock_api_key():
    """Create mock API key."""
    return APIKeyModel(
        id=uuid4(),
        tenant_id="test-tenant",
        name="Test Key",
        key_prefix="sk_test12345678",
        key_hash="test_hash",
        scopes={"annotations": True, "augmented_data": True},
        rate_limit_per_minute=10,
        rate_limit_per_day=1000,
        status=APIKeyStatus.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(days=30),
        total_calls=0
    )


@pytest.fixture
def mock_api_key_service(mock_api_key):
    """Create mock API key service."""
    service = Mock(spec=APIKeyService)
    service.validate_key.return_value = mock_api_key
    service.update_usage.return_value = True
    return service


class TestAPIKeyRateLimiter:
    """Test API key rate limiter."""
    
    @pytest.mark.asyncio
    async def test_per_minute_limit_allows_requests(self, mock_api_key):
        """Test that requests under per-minute limit are allowed."""
        limiter = APIKeyRateLimiter()
        mock_api_key.rate_limit_per_minute = 5
        
        # First 5 requests should succeed
        for i in range(5):
            result = await limiter.check_rate_limit(mock_api_key)
            assert result.allowed
            assert result.remaining == 5 - i - 1

    
    @pytest.mark.asyncio
    async def test_per_minute_limit_blocks_excess(self, mock_api_key):
        """Test that requests exceeding per-minute limit are blocked."""
        limiter = APIKeyRateLimiter()
        mock_api_key.rate_limit_per_minute = 3
        
        # First 3 requests succeed
        for _ in range(3):
            result = await limiter.check_rate_limit(mock_api_key)
            assert result.allowed
        
        # 4th request should be blocked
        result = await limiter.check_rate_limit(mock_api_key)
        assert not result.allowed
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.rule_name == "api_key_per_minute"
    
    @pytest.mark.asyncio
    async def test_per_day_limit_blocks_excess(self, mock_api_key):
        """Test that requests exceeding per-day limit are blocked."""
        limiter = APIKeyRateLimiter()
        mock_api_key.rate_limit_per_minute = 1000
        mock_api_key.rate_limit_per_day = 5
        
        # First 5 requests succeed
        for _ in range(5):
            result = await limiter.check_rate_limit(mock_api_key)
            assert result.allowed
        
        # 6th request blocked by daily limit
        result = await limiter.check_rate_limit(mock_api_key)
        assert not result.allowed
        assert result.rule_name == "api_key_per_day"

    
    @pytest.mark.asyncio
    async def test_minute_window_reset(self, mock_api_key):
        """Test that minute window resets after 60 seconds."""
        limiter = APIKeyRateLimiter()
        mock_api_key.rate_limit_per_minute = 2
        
        # Use up the limit
        for _ in range(2):
            result = await limiter.check_rate_limit(mock_api_key)
            assert result.allowed
        
        # Should be blocked
        result = await limiter.check_rate_limit(mock_api_key)
        assert not result.allowed
        
        # Simulate window reset by manipulating internal state
        current_window = limiter._get_current_minute_window()
        limiter._minute_counters[mock_api_key.id]["window"] = current_window - 60
        
        # Should be allowed again
        result = await limiter.check_rate_limit(mock_api_key)
        assert result.allowed
    
    @pytest.mark.asyncio
    async def test_cleanup_removes_old_entries(self, mock_api_key):
        """Test cleanup removes expired counters."""
        limiter = APIKeyRateLimiter()
        
        # Create some requests
        await limiter.check_rate_limit(mock_api_key)
        
        # Set old window
        current_window = limiter._get_current_minute_window()
        limiter._minute_counters[mock_api_key.id]["window"] = current_window - 200
        
        # Cleanup should remove it
        cleaned = await limiter.cleanup()
        assert cleaned > 0
        assert mock_api_key.id not in limiter._minute_counters



class TestAPIKeyAuthMiddleware:
    """Test API key authentication middleware."""
    
    def test_missing_api_key_returns_401(self, app, mock_api_key_service):
        """Test that missing API key returns 401."""
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_key_service=mock_api_key_service
        )
        client = TestClient(app, raise_server_exceptions=False)
        
        response = client.get("/api/v1/external/test")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "MISSING_API_KEY" in str(data["detail"])
    
    def test_invalid_api_key_returns_401(self, app, mock_api_key_service):
        """Test that invalid API key returns 401."""
        mock_api_key_service.validate_key.return_value = None
        
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_key_service=mock_api_key_service
        )
        client = TestClient(app, raise_server_exceptions=False)
        
        response = client.get(
            "/api/v1/external/test",
            headers={"X-API-Key": "invalid_key"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "INVALID_API_KEY" in str(data["detail"])

    
    def test_valid_api_key_allows_access(self, app, mock_api_key_service):
        """Test that valid API key allows access."""
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_key_service=mock_api_key_service
        )
        client = TestClient(app)
        
        response = client.get(
            "/api/v1/external/test",
            headers={"X-API-Key": "sk_valid_key"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "success"
        assert response.json()["tenant_id"] == "test-tenant"
    
    def test_rate_limit_headers_included(self, app, mock_api_key_service):
        """Test that rate limit headers are included in response."""
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_key_service=mock_api_key_service
        )
        client = TestClient(app)
        
        response = client.get(
            "/api/v1/external/test",
            headers={"X-API-Key": "sk_valid_key"}
        )
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    
    def test_rate_limit_exceeded_returns_429(self, app, mock_api_key_service, mock_api_key):
        """Test that rate limit exceeded returns 429."""
        mock_api_key.rate_limit_per_minute = 2
        
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_key_service=mock_api_key_service
        )
        client = TestClient(app, raise_server_exceptions=False)
        
        # First 2 requests succeed
        for _ in range(2):
            response = client.get(
                "/api/v1/external/test",
                headers={"X-API-Key": "sk_valid_key"}
            )
            assert response.status_code == 200
        
        # 3rd request should be rate limited
        response = client.get(
            "/api/v1/external/test",
            headers={"X-API-Key": "sk_valid_key"}
        )
        assert response.status_code == 429
        data = response.json()
        assert "detail" in data
        assert "RATE_LIMIT_EXCEEDED" in str(data["detail"])
        assert "Retry-After" in response.headers
    
    def test_unprotected_path_skips_auth(self, app, mock_api_key_service):
        """Test that unprotected paths skip authentication."""
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_key_service=mock_api_key_service
        )
        client = TestClient(app)
        
        # Internal endpoint should not require API key
        response = client.get("/api/v1/internal/test")
        assert response.status_code == 200
        assert response.json()["message"] == "internal"

    
    @patch('src.sync.gateway.api_key_auth_middleware.db_manager')
    def test_api_call_logging(self, mock_db_manager, app, mock_api_key_service):
        """Test that API calls are logged to database."""
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_key_service=mock_api_key_service
        )
        client = TestClient(app)
        
        response = client.get(
            "/api/v1/external/test",
            headers={"X-API-Key": "sk_valid_key"}
        )
        assert response.status_code == 200
        
        # Verify log entry was created
        mock_session.add.assert_called_once()
        log_entry = mock_session.add.call_args[0][0]
        assert log_entry.endpoint == "/api/v1/external/test"
        assert log_entry.status_code == 200
        assert log_entry.response_time_ms > 0
    
    def test_usage_statistics_updated(self, app, mock_api_key_service):
        """Test that API key usage statistics are updated."""
        app.add_middleware(
            APIKeyAuthMiddleware,
            api_key_service=mock_api_key_service
        )
        client = TestClient(app)
        
        response = client.get(
            "/api/v1/external/test",
            headers={"X-API-Key": "sk_valid_key"}
        )
        assert response.status_code == 200
        
        # Verify usage was updated
        mock_api_key_service.update_usage.assert_called_once()
        call_args = mock_api_key_service.update_usage.call_args
        assert call_args[1]["increment_calls"] is True
