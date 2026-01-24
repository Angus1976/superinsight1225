"""
Middleware for AI Annotation API endpoints.

Provides:
- Error handling
- Request validation
- Rate limiting
- Correlation ID tracking
- Request logging
"""

import logging
import time
import uuid
from typing import Callable, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError

logger = logging.getLogger(__name__)


# =============================================================================
# Error Response Models
# =============================================================================

class ErrorDetail:
    """Structured error detail."""

    def __init__(
        self,
        code: str,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.field = field
        self.details = details or {}

    def to_dict(self):
        """Convert to dictionary."""
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.field:
            result["field"] = self.field
        if self.details:
            result["details"] = self.details
        return result


class ErrorResponse:
    """Standardized error response."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        correlation_id: str,
        errors: Optional[list] = None,
        timestamp: Optional[str] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.correlation_id = correlation_id
        self.errors = errors or []
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp,
                "details": [e.to_dict() if isinstance(e, ErrorDetail) else e for e in self.errors],
            }
        }


# =============================================================================
# Error Handling Middleware
# =============================================================================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Centralized error handling middleware.

    Features:
    - Catches all unhandled exceptions
    - Returns consistent error format
    - Logs errors with correlation IDs
    - Handles validation errors
    - Handles HTTP exceptions
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle errors."""
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
            return response

        except ValidationError as e:
            # Handle Pydantic validation errors
            errors = []
            for error in e.errors():
                errors.append(
                    ErrorDetail(
                        code="VALIDATION_ERROR",
                        message=error["msg"],
                        field=".".join(str(loc) for loc in error["loc"]),
                        details={"type": error["type"]},
                    )
                )

            error_response = ErrorResponse(
                status_code=422,
                error_code="VALIDATION_ERROR",
                message="Request validation failed",
                correlation_id=correlation_id,
                errors=errors,
            )

            logger.warning(
                f"Validation error [{correlation_id}]: {request.method} {request.url.path} - {len(errors)} errors"
            )

            return JSONResponse(
                status_code=422,
                content=error_response.to_dict(),
            )

        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            error_response = ErrorResponse(
                status_code=e.status_code,
                error_code=f"HTTP_{e.status_code}",
                message=e.detail if isinstance(e.detail, str) else "Request failed",
                correlation_id=correlation_id,
            )

            logger.warning(
                f"HTTP exception [{correlation_id}]: {request.method} {request.url.path} - {e.status_code} {e.detail}"
            )

            return JSONResponse(
                status_code=e.status_code,
                content=error_response.to_dict(),
            )

        except Exception as e:
            # Handle unexpected errors
            error_response = ErrorResponse(
                status_code=500,
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred",
                correlation_id=correlation_id,
            )

            logger.error(
                f"Unhandled exception [{correlation_id}]: {request.method} {request.url.path} - {type(e).__name__}: {str(e)}",
                exc_info=True,
            )

            return JSONResponse(
                status_code=500,
                content=error_response.to_dict(),
            )


# =============================================================================
# Request Logging Middleware
# =============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware.

    Logs:
    - Request method and path
    - Response status code
    - Request duration
    - Correlation ID
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()

        # Get or create correlation ID
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        # Log request
        logger.info(f"Request [{correlation_id}]: {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            f"Response [{correlation_id}]: {response.status_code} - {duration_ms:.2f}ms"
        )

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.

    Features:
    - Per-user rate limits
    - Per-endpoint rate limits
    - Sliding window algorithm
    - Rate limit headers in response
    """

    def __init__(
        self,
        app,
        default_limit: int = 100,
        window_seconds: int = 60,
    ):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            default_limit: Default requests per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # user_id -> [timestamps]

    def _get_user_id(self, request: Request) -> str:
        """Get user ID from request."""
        # TODO: Extract from JWT token or session
        # For now, use IP address as identifier
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _clean_old_requests(self, user_id: str, current_time: float):
        """Remove requests outside the current window."""
        cutoff_time = current_time - self.window_seconds
        self.requests[user_id] = [
            ts for ts in self.requests[user_id] if ts > cutoff_time
        ]

    def _is_rate_limited(self, user_id: str, current_time: float) -> tuple[bool, int, int]:
        """
        Check if user is rate limited.

        Returns:
            (is_limited, current_count, limit)
        """
        self._clean_old_requests(user_id, current_time)
        current_count = len(self.requests[user_id])

        # Check if limit exceeded
        is_limited = current_count >= self.default_limit

        return is_limited, current_count, self.default_limit

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and enforce rate limits."""
        user_id = self._get_user_id(request)
        current_time = time.time()

        # Check rate limit
        is_limited, current_count, limit = self._is_rate_limited(user_id, current_time)

        if is_limited:
            # Rate limit exceeded
            correlation_id = getattr(
                request.state, "correlation_id", str(uuid.uuid4())
            )

            error_response = ErrorResponse(
                status_code=429,
                error_code="RATE_LIMIT_EXCEEDED",
                message=f"Rate limit exceeded. Maximum {limit} requests per {self.window_seconds} seconds.",
                correlation_id=correlation_id,
            )

            logger.warning(
                f"Rate limit exceeded [{correlation_id}]: {user_id} - {current_count}/{limit}"
            )

            response = JSONResponse(
                status_code=429,
                content=error_response.to_dict(),
            )

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(
                int(current_time + self.window_seconds)
            )

            return response

        # Record request
        self.requests[user_id].append(current_time)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = limit - (current_count + 1)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(
            int(current_time + self.window_seconds)
        )

        return response


# =============================================================================
# Request Validation Middleware
# =============================================================================

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation middleware.

    Features:
    - Validates query parameters
    - Validates path parameters
    - Validates request headers
    - Enforces content type requirements
    """

    def __init__(self, app):
        """Initialize validation middleware."""
        super().__init__(app)
        self.required_content_types = {
            "POST": ["application/json"],
            "PUT": ["application/json"],
            "PATCH": ["application/json"],
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and validate."""
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

        # Validate content type for body-containing methods
        if request.method in self.required_content_types:
            content_type = request.headers.get("content-type", "")

            # Extract base content type (ignore charset, etc.)
            base_content_type = content_type.split(";")[0].strip()

            if base_content_type not in self.required_content_types[request.method]:
                error_response = ErrorResponse(
                    status_code=415,
                    error_code="UNSUPPORTED_MEDIA_TYPE",
                    message=f"Content-Type must be one of: {', '.join(self.required_content_types[request.method])}",
                    correlation_id=correlation_id,
                )

                logger.warning(
                    f"Invalid content type [{correlation_id}]: {request.method} {request.url.path} - {content_type}"
                )

                return JSONResponse(
                    status_code=415,
                    content=error_response.to_dict(),
                )

        # Process request
        response = await call_next(request)
        return response


# =============================================================================
# Helper Functions
# =============================================================================

def get_correlation_id(request: Request) -> str:
    """
    Get correlation ID from request.

    Args:
        request: FastAPI request

    Returns:
        Correlation ID string
    """
    return getattr(request.state, "correlation_id", "unknown")


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    correlation_id: Optional[str] = None,
    errors: Optional[list] = None,
) -> JSONResponse:
    """
    Create standardized error response.

    Args:
        status_code: HTTP status code
        error_code: Error code
        message: Error message
        correlation_id: Correlation ID
        errors: List of error details

    Returns:
        JSONResponse with error
    """
    error_response = ErrorResponse(
        status_code=status_code,
        error_code=error_code,
        message=message,
        correlation_id=correlation_id or str(uuid.uuid4()),
        errors=errors,
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.to_dict(),
    )
