"""
Admin API Rate Limiting Middleware.

Provides rate limiting for admin configuration API endpoints using Redis
for distributed rate limiting across multiple instances.

This implementation follows async-safety rules:
- Uses asyncio.Lock() instead of threading.Lock()
- All I/O operations are async
- No blocking operations in async context
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from src.config.settings import Settings

logger = logging.getLogger(__name__)


class RateLimitResult:
    """Result of rate limit check."""

    def __init__(
        self,
        allowed: bool,
        remaining: int,
        limit: int,
        reset_at: float,
        retry_after: Optional[int] = None
    ):
        self.allowed = allowed
        self.remaining = remaining
        self.limit = limit
        self.reset_at = reset_at
        self.retry_after = retry_after


class RedisRateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.

    Features:
    - Distributed rate limiting across multiple instances
    - Sliding window for accurate rate limiting
    - Automatic cleanup of expired entries
    - Async-safe implementation
    """

    def __init__(
        self,
        redis_client,
        limit: int = 100,
        window_seconds: int = 60,
        key_prefix: str = "rate_limit"
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Async Redis client instance
            limit: Maximum requests per window
            window_seconds: Time window in seconds
            key_prefix: Prefix for Redis keys
        """
        self.redis_client = redis_client
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self._lock = asyncio.Lock()  # Async-safe lock

    def _make_key(self, identifier: str) -> str:
        """Generate Redis key for rate limit tracking."""
        return f"{self.key_prefix}:{identifier}"

    async def check_rate_limit(self, identifier: str) -> RateLimitResult:
        """
        Check rate limit for an identifier using sliding window.

        Args:
            identifier: Unique identifier (IP, user ID, etc.)

        Returns:
            RateLimitResult with check outcome
        """
        key = self._make_key(identifier)
        now = time.time()
        window_start = now - self.window_seconds

        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiration
            pipe.expire(key, self.window_seconds + 10)

            # Execute pipeline
            results = await pipe.execute()

            # Get count (before adding current request)
            count = results[1]

            # Check if limit exceeded
            allowed = count < self.limit
            remaining = max(0, self.limit - count - 1)
            reset_at = now + self.window_seconds

            # If limit exceeded, remove the request we just added
            if not allowed:
                await self.redis_client.zrem(key, str(now))
                retry_after = int(self.window_seconds)
            else:
                retry_after = None

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                limit=self.limit,
                reset_at=reset_at,
                retry_after=retry_after
            )

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if Redis is unavailable
            return RateLimitResult(
                allowed=True,
                remaining=self.limit,
                limit=self.limit,
                reset_at=now + self.window_seconds,
                retry_after=None
            )

    async def reset(self, identifier: str) -> bool:
        """
        Reset rate limit for an identifier.

        Args:
            identifier: Unique identifier to reset

        Returns:
            True if reset successful
        """
        try:
            key = self._make_key(identifier)
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Rate limit reset failed: {e}")
            return False


class InMemoryRateLimiter:
    """
    Fallback in-memory rate limiter when Redis is unavailable.

    Uses sliding window algorithm with async-safe implementation.
    """

    def __init__(
        self,
        limit: int = 100,
        window_seconds: int = 60
    ):
        """
        Initialize in-memory rate limiter.

        Args:
            limit: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
        self._lock = asyncio.Lock()  # Async-safe lock

    async def check_rate_limit(self, identifier: str) -> RateLimitResult:
        """
        Check rate limit for an identifier.

        Args:
            identifier: Unique identifier (IP, user ID, etc.)

        Returns:
            RateLimitResult with check outcome
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Initialize or get request list
            if identifier not in self._requests:
                self._requests[identifier] = []

            requests = self._requests[identifier]

            # Remove expired requests
            requests[:] = [ts for ts in requests if ts > window_start]

            # Check if limit exceeded
            allowed = len(requests) < self.limit

            if allowed:
                requests.append(now)
                remaining = self.limit - len(requests)
                retry_after = None
            else:
                remaining = 0
                retry_after = int(self.window_seconds)

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                limit=self.limit,
                reset_at=now + self.window_seconds,
                retry_after=retry_after
            )

    async def reset(self, identifier: str) -> bool:
        """
        Reset rate limit for an identifier.

        Args:
            identifier: Unique identifier to reset

        Returns:
            True if reset successful
        """
        async with self._lock:
            if identifier in self._requests:
                del self._requests[identifier]
            return True

    async def cleanup(self) -> int:
        """
        Clean up expired entries.

        Returns:
            Number of cleaned entries
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            cleaned = 0

            for identifier in list(self._requests.keys()):
                requests = self._requests[identifier]
                original_len = len(requests)
                requests[:] = [ts for ts in requests if ts > window_start]

                if not requests:
                    del self._requests[identifier]
                    cleaned += 1
                elif len(requests) < original_len:
                    cleaned += 1

            return cleaned


class AdminRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for admin configuration API.

    Enforces 100 requests per minute per client (IP or user).
    Returns 429 Too Many Requests when limit exceeded.
    Includes rate limit headers in all responses.
    """

    def __init__(
        self,
        app: ASGIApp,
        redis_client=None,
        limit: int = 100,
        window_seconds: int = 60,
        exclude_paths: Optional[list] = None
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: ASGI application
            redis_client: Async Redis client (optional)
            limit: Maximum requests per window (default: 100)
            window_seconds: Time window in seconds (default: 60)
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)

        # Initialize rate limiter (Redis or in-memory fallback)
        if redis_client:
            self.rate_limiter = RedisRateLimiter(
                redis_client=redis_client,
                limit=limit,
                window_seconds=window_seconds,
                key_prefix="admin_rate_limit"
            )
            logger.info("Admin rate limiter initialized with Redis backend")
        else:
            self.rate_limiter = InMemoryRateLimiter(
                limit=limit,
                window_seconds=window_seconds
            )
            logger.warning("Admin rate limiter initialized with in-memory fallback")

        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/api/v1/health",
            "/api/v1/system/status"
        ]

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.

        Priority:
        1. User ID from request state (if authenticated)
        2. Tenant ID from request state
        3. Client IP address

        Args:
            request: FastAPI request

        Returns:
            Unique identifier string
        """
        # Try to get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Try to get tenant ID from request state or headers
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return f"tenant:{tenant_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _create_rate_limit_headers(self, result: RateLimitResult) -> Dict[str, str]:
        """
        Create rate limit response headers.

        Args:
            result: Rate limit check result

        Returns:
            Dictionary of headers
        """
        headers = {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(int(result.reset_at))
        }

        if result.retry_after:
            headers["Retry-After"] = str(result.retry_after)

        return headers

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Apply rate limiting to request.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response with rate limit headers

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        # Skip excluded paths
        path = str(request.url.path)
        for exclude in self.exclude_paths:
            if path.startswith(exclude):
                return await call_next(request)

        # Get client identifier
        identifier = self._get_client_identifier(request)

        # Check rate limit
        result = await self.rate_limiter.check_rate_limit(identifier)

        # If limit exceeded, return 429
        if not result.allowed:
            headers = self._create_rate_limit_headers(result)
            logger.warning(
                f"Rate limit exceeded for {identifier} on {request.method} {path}"
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "limit": result.limit,
                    "window_seconds": 60,
                    "retry_after": result.retry_after
                },
                headers=headers
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        headers = self._create_rate_limit_headers(result)
        for key, value in headers.items():
            response.headers[key] = value

        return response


async def create_admin_rate_limiter(
    settings: Optional[Settings] = None,
    limit: int = 100,
    window_seconds: int = 60
) -> AdminRateLimitMiddleware:
    """
    Factory function to create admin rate limit middleware.

    Args:
        settings: Application settings (optional)
        limit: Maximum requests per window
        window_seconds: Time window in seconds

    Returns:
        Configured AdminRateLimitMiddleware instance
    """
    redis_client = None

    # Try to initialize Redis client
    if settings:
        try:
            import redis.asyncio as redis

            redis_client = redis.Redis(
                host=settings.redis.redis_host,
                port=settings.redis.redis_port,
                db=settings.redis.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # Test connection
            await redis_client.ping()
            logger.info("Redis connection established for rate limiting")

        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            redis_client = None

    # Return middleware (will use in-memory if Redis unavailable)
    return lambda app: AdminRateLimitMiddleware(
        app=app,
        redis_client=redis_client,
        limit=limit,
        window_seconds=window_seconds
    )
