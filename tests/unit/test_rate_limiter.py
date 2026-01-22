"""
Unit tests for Admin API Rate Limiter.

Tests the rate limiting middleware with both Redis and in-memory backends.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from src.api.middleware.rate_limiter import (
    AdminRateLimitMiddleware,
    InMemoryRateLimiter,
    RateLimitResult,
    RedisRateLimiter,
)


class TestRateLimitResult:
    """Test RateLimitResult class."""

    def test_rate_limit_result_creation(self):
        """Test creating a rate limit result."""
        result = RateLimitResult(
            allowed=True,
            remaining=99,
            limit=100,
            reset_at=time.time() + 60,
            retry_after=None
        )

        assert result.allowed is True
        assert result.remaining == 99
        assert result.limit == 100
        assert result.reset_at > time.time()
        assert result.retry_after is None

    def test_rate_limit_result_exceeded(self):
        """Test rate limit result when limit exceeded."""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            limit=100,
            reset_at=time.time() + 60,
            retry_after=60
        )

        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 60


class TestInMemoryRateLimiter:
    """Test in-memory rate limiter."""

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = InMemoryRateLimiter(limit=5, window_seconds=60)

        # Make 5 requests
        for i in range(5):
            result = await limiter.check_rate_limit("test_client")
            assert result.allowed is True
            assert result.remaining == 4 - i

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = InMemoryRateLimiter(limit=3, window_seconds=60)

        # Make 3 requests (should all succeed)
        for _ in range(3):
            result = await limiter.check_rate_limit("test_client")
            assert result.allowed is True

        # 4th request should be blocked
        result = await limiter.check_rate_limit("test_client")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 60

    @pytest.mark.asyncio
    async def test_sliding_window_expiration(self):
        """Test that old requests expire from the window."""
        limiter = InMemoryRateLimiter(limit=2, window_seconds=1)

        # Make 2 requests
        result1 = await limiter.check_rate_limit("test_client")
        result2 = await limiter.check_rate_limit("test_client")
        assert result1.allowed is True
        assert result2.allowed is True

        # 3rd request should be blocked
        result3 = await limiter.check_rate_limit("test_client")
        assert result3.allowed is False

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Should be allowed again
        result4 = await limiter.check_rate_limit("test_client")
        assert result4.allowed is True

    @pytest.mark.asyncio
    async def test_different_identifiers_independent(self):
        """Test that different identifiers have independent limits."""
        limiter = InMemoryRateLimiter(limit=2, window_seconds=60)

        # Client 1 makes 2 requests
        result1 = await limiter.check_rate_limit("client1")
        result2 = await limiter.check_rate_limit("client1")
        assert result1.allowed is True
        assert result2.allowed is True

        # Client 1's 3rd request should be blocked
        result3 = await limiter.check_rate_limit("client1")
        assert result3.allowed is False

        # Client 2 should still be allowed
        result4 = await limiter.check_rate_limit("client2")
        assert result4.allowed is True

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test resetting rate limit for an identifier."""
        limiter = InMemoryRateLimiter(limit=2, window_seconds=60)

        # Make 2 requests
        await limiter.check_rate_limit("test_client")
        await limiter.check_rate_limit("test_client")

        # 3rd should be blocked
        result = await limiter.check_rate_limit("test_client")
        assert result.allowed is False

        # Reset
        success = await limiter.reset("test_client")
        assert success is True

        # Should be allowed again
        result = await limiter.check_rate_limit("test_client")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup of expired entries."""
        limiter = InMemoryRateLimiter(limit=5, window_seconds=1)

        # Make requests for multiple clients
        await limiter.check_rate_limit("client1")
        await limiter.check_rate_limit("client2")
        await limiter.check_rate_limit("client3")

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Cleanup
        cleaned = await limiter.cleanup()
        assert cleaned >= 3

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test thread-safety with concurrent requests."""
        limiter = InMemoryRateLimiter(limit=10, window_seconds=60)

        async def make_request():
            return await limiter.check_rate_limit("test_client")

        # Make 10 concurrent requests
        results = await asyncio.gather(*[make_request() for _ in range(10)])

        # All should be allowed
        assert all(r.allowed for r in results)

        # 11th should be blocked
        result = await limiter.check_rate_limit("test_client")
        assert result.allowed is False


class TestRedisRateLimiter:
    """Test Redis-based rate limiter."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = AsyncMock()
        redis.pipeline.return_value = redis
        redis.zremrangebyscore = AsyncMock()
        redis.zcard = AsyncMock()
        redis.zadd = AsyncMock()
        redis.expire = AsyncMock()
        redis.zrem = AsyncMock()
        redis.delete = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, mock_redis):
        """Test that requests under limit are allowed."""
        # Mock Redis responses
        mock_redis.execute = AsyncMock(return_value=[1, 2, 1, 1])

        limiter = RedisRateLimiter(
            redis_client=mock_redis,
            limit=5,
            window_seconds=60
        )

        result = await limiter.check_rate_limit("test_client")
        assert result.allowed is True
        assert result.remaining >= 0

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self, mock_redis):
        """Test that requests over limit are blocked."""
        # Mock Redis responses - count is at limit
        mock_redis.execute = AsyncMock(return_value=[1, 5, 1, 1])

        limiter = RedisRateLimiter(
            redis_client=mock_redis,
            limit=5,
            window_seconds=60
        )

        result = await limiter.check_rate_limit("test_client")
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 60

        # Verify the request was removed
        mock_redis.zrem.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_failure_fails_open(self, mock_redis):
        """Test that Redis failures allow requests (fail open)."""
        # Mock Redis to raise exception
        mock_redis.execute = AsyncMock(side_effect=Exception("Redis error"))

        limiter = RedisRateLimiter(
            redis_client=mock_redis,
            limit=5,
            window_seconds=60
        )

        result = await limiter.check_rate_limit("test_client")
        # Should allow request when Redis fails
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_reset(self, mock_redis):
        """Test resetting rate limit for an identifier."""
        mock_redis.delete = AsyncMock(return_value=1)

        limiter = RedisRateLimiter(
            redis_client=mock_redis,
            limit=5,
            window_seconds=60
        )

        success = await limiter.reset("test_client")
        assert success is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_failure(self, mock_redis):
        """Test reset failure handling."""
        mock_redis.delete = AsyncMock(side_effect=Exception("Redis error"))

        limiter = RedisRateLimiter(
            redis_client=mock_redis,
            limit=5,
            window_seconds=60
        )

        success = await limiter.reset("test_client")
        assert success is False

    @pytest.mark.asyncio
    async def test_key_generation(self, mock_redis):
        """Test Redis key generation."""
        mock_redis.execute = AsyncMock(return_value=[1, 0, 1, 1])

        limiter = RedisRateLimiter(
            redis_client=mock_redis,
            limit=5,
            window_seconds=60,
            key_prefix="test_prefix"
        )

        await limiter.check_rate_limit("client123")

        # Verify key format
        key = limiter._make_key("client123")
        assert key == "test_prefix:client123"


class TestAdminRateLimitMiddleware:
    """Test Admin rate limit middleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        return app

    @pytest.fixture
    def client_with_middleware(self, app):
        """Create test client with rate limit middleware."""
        middleware = AdminRateLimitMiddleware(
            app=app,
            redis_client=None,  # Use in-memory
            limit=3,
            window_seconds=60
        )
        app.add_middleware(lambda app: middleware)
        return TestClient(app)

    def test_allows_requests_under_limit(self, client_with_middleware):
        """Test that requests under limit are allowed."""
        # Make 3 requests
        for i in range(3):
            response = client_with_middleware.get("/test")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

    def test_blocks_requests_over_limit(self, client_with_middleware):
        """Test that requests over limit return 429."""
        # Make 3 requests (should succeed)
        for _ in range(3):
            response = client_with_middleware.get("/test")
            assert response.status_code == 200

        # 4th request should be blocked
        response = client_with_middleware.get("/test")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

        data = response.json()
        assert data["detail"]["error"] == "rate_limit_exceeded"
        assert "retry_after" in data["detail"]

    def test_excludes_health_endpoints(self, client_with_middleware):
        """Test that health endpoints are excluded from rate limiting."""
        # Make many requests to health endpoint
        for _ in range(10):
            response = client_with_middleware.get("/health")
            assert response.status_code == 200

        # Should not affect rate limit for other endpoints
        response = client_with_middleware.get("/test")
        assert response.status_code == 200

    def test_rate_limit_headers(self, client_with_middleware):
        """Test that rate limit headers are included."""
        response = client_with_middleware.get("/test")
        assert response.status_code == 200

        # Check headers
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "3"

        assert "X-RateLimit-Remaining" in response.headers
        remaining = int(response.headers["X-RateLimit-Remaining"])
        assert 0 <= remaining <= 3

        assert "X-RateLimit-Reset" in response.headers
        reset_at = int(response.headers["X-RateLimit-Reset"])
        assert reset_at > time.time()

    @pytest.mark.asyncio
    async def test_client_identifier_priority(self):
        """Test client identifier priority (user > tenant > IP)."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        middleware = AdminRateLimitMiddleware(
            app=app,
            redis_client=None,
            limit=5,
            window_seconds=60
        )

        # Test with user ID
        request = MagicMock(spec=Request)
        request.url.path = "/test"
        request.state.user_id = "user123"
        request.state.tenant_id = "tenant456"
        request.client.host = "192.168.1.1"

        identifier = middleware._get_client_identifier(request)
        assert identifier == "user:user123"

        # Test with tenant ID only
        request.state.user_id = None
        identifier = middleware._get_client_identifier(request)
        assert identifier == "tenant:tenant456"

        # Test with IP only
        request.state.tenant_id = None
        identifier = middleware._get_client_identifier(request)
        assert identifier == "ip:192.168.1.1"

    def test_custom_limit_and_window(self):
        """Test custom limit and window configuration."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        middleware = AdminRateLimitMiddleware(
            app=app,
            redis_client=None,
            limit=10,
            window_seconds=120
        )

        assert middleware.rate_limiter.limit == 10
        assert middleware.rate_limiter.window_seconds == 120

    def test_custom_exclude_paths(self):
        """Test custom exclude paths configuration."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        @app.get("/custom/excluded")
        async def excluded_endpoint():
            return {"message": "excluded"}

        middleware = AdminRateLimitMiddleware(
            app=app,
            redis_client=None,
            limit=1,
            window_seconds=60,
            exclude_paths=["/custom/excluded"]
        )

        client = TestClient(app)
        app.add_middleware(lambda app: middleware)

        # Make multiple requests to excluded path
        for _ in range(5):
            response = client.get("/custom/excluded")
            assert response.status_code == 200

        # Regular path should still be rate limited
        response = client.get("/test")
        assert response.status_code == 200

        response = client.get("/test")
        assert response.status_code == 429


class TestCreateAdminRateLimiter:
    """Test factory function for creating rate limiter."""

    @pytest.mark.asyncio
    async def test_creates_with_redis(self):
        """Test creating rate limiter with Redis."""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis_class.return_value = mock_redis

            from src.config.settings import Settings, RedisSettings

            settings = Settings()
            settings.redis = RedisSettings(
                redis_host="localhost",
                redis_port=6379,
                redis_db=0
            )

            from src.api.middleware.rate_limiter import create_admin_rate_limiter

            middleware_factory = await create_admin_rate_limiter(
                settings=settings,
                limit=100,
                window_seconds=60
            )

            assert middleware_factory is not None

    @pytest.mark.asyncio
    async def test_falls_back_to_memory_on_redis_failure(self):
        """Test fallback to in-memory when Redis fails."""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.side_effect = Exception("Redis connection failed")

            from src.config.settings import Settings

            settings = Settings()

            from src.api.middleware.rate_limiter import create_admin_rate_limiter

            middleware_factory = await create_admin_rate_limiter(
                settings=settings,
                limit=100,
                window_seconds=60
            )

            # Should still create middleware (with in-memory fallback)
            assert middleware_factory is not None

    @pytest.mark.asyncio
    async def test_creates_without_settings(self):
        """Test creating rate limiter without settings."""
        from src.api.middleware.rate_limiter import create_admin_rate_limiter

        middleware_factory = await create_admin_rate_limiter(
            settings=None,
            limit=50,
            window_seconds=30
        )

        assert middleware_factory is not None
