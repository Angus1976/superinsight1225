"""
Correlation ID Middleware for SuperInsight Platform.

Provides request correlation ID generation and propagation for
distributed tracing and log correlation across services.

Validates: Requirements 10.2
"""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variable for storing correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Header names for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from context.
    
    Returns:
        The correlation ID if set, None otherwise
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID in context.
    
    Args:
        correlation_id: The correlation ID to set
    """
    _correlation_id.set(correlation_id)


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.
    
    Returns:
        A unique correlation ID string
    """
    # Format: timestamp_uuid4_short
    timestamp = int(time.time() * 1000)
    unique_id = uuid.uuid4().hex[:12]
    return f"corr_{timestamp}_{unique_id}"


def generate_request_id() -> str:
    """
    Generate a new request ID.
    
    Returns:
        A unique request ID string
    """
    timestamp = int(time.time() * 1000000)
    return f"req_{timestamp}"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling correlation IDs in requests.
    
    This middleware:
    1. Extracts correlation ID from incoming request headers
    2. Generates a new correlation ID if not present
    3. Stores the correlation ID in context for logging
    4. Adds the correlation ID to response headers
    
    Validates: Requirements 10.2
    """
    
    def __init__(self, app, header_name: str = CORRELATION_ID_HEADER):
        """
        Initialize the middleware.
        
        Args:
            app: The ASGI application
            header_name: The header name to use for correlation ID
        """
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and add correlation ID.
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler
            
        Returns:
            The response with correlation ID header
        """
        # Try to get correlation ID from request headers
        correlation_id = request.headers.get(self.header_name)
        
        # Also check for X-Request-ID as fallback
        if not correlation_id:
            correlation_id = request.headers.get(REQUEST_ID_HEADER)
        
        # Generate new correlation ID if not present
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Store in request state for easy access
        request.state.correlation_id = correlation_id
        request.state.request_id = generate_request_id()
        
        # Log request start with correlation ID
        logger.debug(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
            }
        )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Add correlation ID to response headers
        response.headers[self.header_name] = correlation_id
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        
        # Log request completion
        logger.debug(
            f"Request completed: {request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                "correlation_id": correlation_id,
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        
        return response


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds correlation ID to log records.
    
    This filter ensures that all log records include the current
    correlation ID for request tracing.
    
    Validates: Requirements 10.2
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add correlation ID to the log record.
        
        Args:
            record: The log record to modify
            
        Returns:
            True (always allow the record)
        """
        # Add correlation ID to record
        correlation_id = get_correlation_id()
        record.correlation_id = correlation_id or "-"
        
        # Ensure other common fields exist
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        
        return True


def get_correlation_context() -> dict:
    """
    Get the current correlation context for logging.
    
    Returns:
        Dictionary with correlation context fields
    """
    return {
        "correlation_id": get_correlation_id() or "-",
    }
