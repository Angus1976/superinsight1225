"""
Security Middleware for FastAPI

Provides JWT authentication, input sanitization, and rate limiting
middleware for the data lifecycle management system.

Validates: Requirements 24.1, 24.2, 24.3, 24.4, 24.5, 24.6
"""

import time
import asyncio
import logging
from typing import Callable, Optional

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.services.security_service import (
    JWTManager,
    sanitize_input,
    RowLevelSecurity,
    TokenPayload,
    SanitizationResult,
)

logger = logging.getLogger(__name__)


# --- Paths excluded from auth ---

DEFAULT_PUBLIC_PATHS = [
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",
    "/api/auth/register",
]


# --- JWT Authentication Middleware ---

class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Validates JWT tokens on incoming requests.

    Sets request.state.user with decoded token payload on success.
    Returns 401 for missing/invalid/expired tokens.
    """

    def __init__(
        self,
        app: ASGIApp,
        jwt_manager: Optional[JWTManager] = None,
        public_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.jwt_manager = jwt_manager or JWTManager()
        self.public_paths = public_paths or DEFAULT_PUBLIC_PATHS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate JWT token before passing to handler."""
        if self._is_public_path(request.url.path):
            return await call_next(request)

        token = self._extract_token(request)
        if not token:
            return self._unauthorized_response("Missing authentication token")

        try:
            payload = self.jwt_manager.validate_token(token)
        except ValueError as e:
            return self._unauthorized_response(str(e))

        # Attach user info to request state
        request.state.user = {
            "id": payload.user_id,
            "roles": payload.roles,
            "token_issued_at": payload.issued_at,
            "token_expires_at": payload.expires_at,
        }

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required)."""
        return any(path.startswith(p) for p in self.public_paths)

    @staticmethod
    def _extract_token(request: Request) -> Optional[str]:
        """Extract Bearer token from Authorization header."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header[7:].strip()

    @staticmethod
    def _unauthorized_response(detail: str) -> Response:
        """Build a 401 JSON response."""
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": detail},
            headers={"WWW-Authenticate": "Bearer"},
        )


# --- Input Sanitization Middleware ---

class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Sanitizes user inputs on state-changing requests (POST/PUT/PATCH).

    Strips script tags, event handlers, and javascript: URIs from
    query parameters and logs sanitization violations.
    """

    SANITIZE_METHODS = {"POST", "PUT", "PATCH"}

    def __init__(
        self,
        app: ASGIApp,
        max_input_length: int = 10000,
        excluded_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.max_input_length = max_input_length
        self.excluded_paths = excluded_paths or ["/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Sanitize query params on mutating requests."""
        if self._should_skip(request):
            return await call_next(request)

        # Sanitize query parameters
        violations = self._sanitize_query_params(request)
        if violations:
            logger.warning(
                "Input sanitization violations on %s %s: %s",
                request.method, request.url.path, violations,
            )

        return await call_next(request)

    def _should_skip(self, request: Request) -> bool:
        """Check if request should skip sanitization."""
        if request.method not in self.SANITIZE_METHODS:
            return True
        return any(
            request.url.path.startswith(p) for p in self.excluded_paths
        )

    def _sanitize_query_params(self, request: Request) -> list:
        """Sanitize query parameters and return violations."""
        violations = []
        for key, value in request.query_params.items():
            result = sanitize_input(value, self.max_input_length)
            if result.was_modified:
                violations.append({
                    "param": key,
                    "violations": result.violations,
                })
        return violations


# --- Rate Limiting Middleware ---

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter per client IP/user.

    Returns 429 Too Many Requests when limit is exceeded.
    Configurable requests-per-minute with per-identifier tracking.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        excluded_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self._requests: dict = {}
        self._lock = asyncio.Lock()
        self.excluded_paths = excluded_paths or [
            "/health", "/docs", "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request."""
        if self._is_excluded(request.url.path):
            return await call_next(request)

        identifier = self._get_identifier(request)
        allowed, remaining, reset_at = await self._check_limit(identifier)

        if not allowed:
            return self._rate_limit_response(remaining, reset_at)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_at))
        return response

    def _is_excluded(self, path: str) -> bool:
        """Check if path is excluded from rate limiting."""
        return any(path.startswith(p) for p in self.excluded_paths)

    @staticmethod
    def _get_identifier(request: Request) -> str:
        """Extract client identifier: user_id > IP."""
        if hasattr(request.state, "user"):
            user = request.state.user
            if isinstance(user, dict) and "id" in user:
                return f"user:{user['id']}"
        if request.client:
            return f"ip:{request.client.host}"
        return "ip:unknown"

    async def _check_limit(self, identifier: str) -> tuple:
        """
        Check if request is within rate limit.

        Returns (allowed, remaining, reset_at).
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            if identifier not in self._requests:
                self._requests[identifier] = []

            timestamps = self._requests[identifier]
            # Prune expired entries
            timestamps[:] = [ts for ts in timestamps if ts > window_start]

            if len(timestamps) >= self.requests_per_minute:
                return False, 0, now + self.window_seconds

            timestamps.append(now)
            remaining = self.requests_per_minute - len(timestamps)
            return True, remaining, now + self.window_seconds

    @staticmethod
    def _rate_limit_response(remaining: int, reset_at: float) -> Response:
        """Build a 429 JSON response."""
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": {
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60,
                }
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(reset_at)),
            },
        )


# --- Row-Level Security Dependency ---

def get_row_level_filter(request: Request, resource_type: str) -> dict:
    """
    FastAPI dependency that returns row-level security filters.

    Usage in endpoints:
        filters = get_row_level_filter(request, "sample")
        if "__deny_all__" in filters:
            raise HTTPException(403, "Access denied")
    """
    user = getattr(request.state, "user", None)
    if not user:
        return {"__deny_all__": True}

    user_id = user.get("id", "")
    user_roles = user.get("roles", [])

    return RowLevelSecurity.filter_query_by_access(
        user_id=user_id,
        user_roles=user_roles,
        resource_type=resource_type,
    )
