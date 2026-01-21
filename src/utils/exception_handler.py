"""
Global Exception Handler for SuperInsight Platform.

Provides centralized exception handling for FastAPI applications,
converting exceptions to standardized error responses.

Validates: Requirements 10.5
"""

import logging
import traceback
import time
from typing import Any, Callable, Dict, Optional, Type, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.utils.error_response import (
    ErrorCode,
    ErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
    create_error_response,
    create_validation_error_response,
    get_http_status_for_error_code,
)
from src.utils.correlation_middleware import get_correlation_id

logger = logging.getLogger(__name__)


class APIException(Exception):
    """
    Base exception class for API errors.
    
    Provides a standardized way to raise API errors with error codes,
    messages, and additional details.
    """
    
    def __init__(
        self,
        error_code: Union[str, ErrorCode],
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None
    ):
        """
        Initialize API exception.
        
        Args:
            error_code: The error code (string or ErrorCode enum)
            message: Optional custom error message
            details: Optional additional error details
            status_code: Optional HTTP status code override
        """
        self.error_code = error_code.value if isinstance(error_code, ErrorCode) else error_code
        self.message = message
        self.details = details
        self.status_code = status_code or get_http_status_for_error_code(self.error_code)
        super().__init__(message or self.error_code)


class ValidationException(APIException):
    """Exception for validation errors."""
    
    def __init__(
        self,
        message: Optional[str] = None,
        validation_errors: Optional[list[ValidationErrorDetail]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=ErrorCode.VAL_INVALID_INPUT,
            message=message,
            details=details,
            status_code=400
        )
        self.validation_errors = validation_errors or []


class AuthenticationException(APIException):
    """Exception for authentication errors."""
    
    def __init__(
        self,
        error_code: Union[str, ErrorCode] = ErrorCode.AUTH_INVALID_CREDENTIALS,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            status_code=401
        )


class PermissionException(APIException):
    """Exception for permission/authorization errors."""
    
    def __init__(
        self,
        error_code: Union[str, ErrorCode] = ErrorCode.PERM_ACCESS_DENIED,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            status_code=403
        )


class NotFoundException(APIException):
    """Exception for resource not found errors."""
    
    def __init__(
        self,
        error_code: Union[str, ErrorCode] = ErrorCode.NOT_FOUND_RESOURCE,
        message: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            error_code=error_code,
            message=message,
            details=details if details else None,
            status_code=404
        )


class ConflictException(APIException):
    """Exception for conflict errors."""
    
    def __init__(
        self,
        error_code: Union[str, ErrorCode] = ErrorCode.CONFLICT_RESOURCE_EXISTS,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            status_code=409
        )


class RateLimitException(APIException):
    """Exception for rate limit errors."""
    
    def __init__(
        self,
        error_code: Union[str, ErrorCode] = ErrorCode.RATE_LIMIT_EXCEEDED,
        message: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        
        super().__init__(
            error_code=error_code,
            message=message,
            details=details if details else None,
            status_code=429
        )
        self.retry_after = retry_after


class ServiceException(APIException):
    """Exception for service unavailable errors."""
    
    def __init__(
        self,
        error_code: Union[str, ErrorCode] = ErrorCode.SERVICE_UNAVAILABLE,
        message: Optional[str] = None,
        estimated_recovery_time: Optional[int] = None
    ):
        details = {}
        if estimated_recovery_time:
            details["estimated_recovery_seconds"] = estimated_recovery_time
        
        super().__init__(
            error_code=error_code,
            message=message,
            details=details if details else None,
            status_code=503
        )


def _get_request_id(request: Request) -> str:
    """Get or generate request ID from request."""
    # Try to get correlation ID from middleware
    correlation_id = get_correlation_id()
    if correlation_id:
        return correlation_id
    
    # Try to get from request state
    if hasattr(request.state, "request_id"):
        return request.state.request_id
    
    # Try to get from headers
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        return request_id
    
    # Generate a new one
    return f"req_{int(time.time() * 1000000)}"


def _log_exception(
    request: Request,
    request_id: str,
    exception: Exception,
    status_code: int,
    include_traceback: bool = True
) -> None:
    """Log exception with request context."""
    log_data = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
    }
    
    # Add client info if available
    if request.client:
        log_data["client_ip"] = request.client.host
    
    # Add user info if available
    if hasattr(request.state, "user_id"):
        log_data["user_id"] = request.state.user_id
    
    # Log based on status code severity
    if status_code >= 500:
        if include_traceback:
            log_data["traceback"] = traceback.format_exc()
        logger.error(
            f"Server error: {type(exception).__name__}: {exception}",
            extra=log_data
        )
    elif status_code >= 400:
        logger.warning(
            f"Client error: {type(exception).__name__}: {exception}",
            extra=log_data
        )
    else:
        logger.info(
            f"Request completed with exception: {type(exception).__name__}",
            extra=log_data
        )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle APIException and its subclasses."""
    request_id = _get_request_id(request)
    
    _log_exception(request, request_id, exc, exc.status_code, include_traceback=False)
    
    # Handle validation exceptions specially
    if isinstance(exc, ValidationException) and exc.validation_errors:
        response = create_validation_error_response(
            request_id=request_id,
            validation_errors=exc.validation_errors,
            message=exc.message
        )
    else:
        response = create_error_response(
            error_code=exc.error_code,
            request_id=request_id,
            message=exc.message,
            details=exc.details
        )
    
    headers = {}
    if isinstance(exc, RateLimitException) and exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode="json"),
        headers=headers if headers else None
    )


async def http_exception_handler(
    request: Request,
    exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """Handle FastAPI/Starlette HTTPException."""
    request_id = _get_request_id(request)
    
    _log_exception(request, request_id, exc, exc.status_code, include_traceback=False)
    
    # Map HTTP status codes to error codes
    status_to_error_code = {
        400: ErrorCode.VAL_INVALID_INPUT.value,
        401: ErrorCode.AUTH_TOKEN_INVALID.value,
        403: ErrorCode.PERM_ACCESS_DENIED.value,
        404: ErrorCode.NOT_FOUND_ENDPOINT.value,
        405: ErrorCode.VAL_INVALID_INPUT.value,
        409: ErrorCode.CONFLICT_RESOURCE_EXISTS.value,
        422: ErrorCode.VAL_INVALID_INPUT.value,
        429: ErrorCode.RATE_LIMIT_EXCEEDED.value,
        500: ErrorCode.INTERNAL_SERVER_ERROR.value,
        502: ErrorCode.SERVICE_DEPENDENCY_FAILED.value,
        503: ErrorCode.SERVICE_UNAVAILABLE.value,
        504: ErrorCode.SERVICE_TIMEOUT.value,
    }
    
    error_code = status_to_error_code.get(exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR.value)
    
    response = create_error_response(
        error_code=error_code,
        request_id=request_id,
        message=str(exc.detail) if exc.detail else None,
        details=None
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode="json")
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors from request parsing."""
    request_id = _get_request_id(request)
    
    _log_exception(request, request_id, exc, 422, include_traceback=False)
    
    # Convert Pydantic errors to our format
    validation_errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error.get("loc", []))
        validation_errors.append(
            ValidationErrorDetail(
                field=field_path,
                message=error.get("msg", "Validation error"),
                value=error.get("input"),
                constraint=error.get("type")
            )
        )
    
    response = create_validation_error_response(
        request_id=request_id,
        validation_errors=validation_errors
    )
    
    return JSONResponse(
        status_code=422,
        content=response.model_dump(mode="json")
    )


async def pydantic_validation_handler(
    request: Request,
    exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic ValidationError (from manual validation)."""
    request_id = _get_request_id(request)
    
    _log_exception(request, request_id, exc, 400, include_traceback=False)
    
    # Convert Pydantic errors to our format
    validation_errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error.get("loc", []))
        validation_errors.append(
            ValidationErrorDetail(
                field=field_path,
                message=error.get("msg", "Validation error"),
                value=error.get("input"),
                constraint=error.get("type")
            )
        )
    
    response = create_validation_error_response(
        request_id=request_id,
        validation_errors=validation_errors
    )
    
    return JSONResponse(
        status_code=400,
        content=response.model_dump(mode="json")
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions.
    
    This is the catch-all handler that ensures all exceptions
    return a standardized error response.
    
    Validates: Requirements 10.5
    """
    request_id = _get_request_id(request)
    
    # Log with full traceback for server errors
    _log_exception(request, request_id, exc, 500, include_traceback=True)
    
    # In debug mode, include more details
    from src.config.settings import settings
    
    details = None
    message = None
    
    if settings.app.debug:
        details = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }
        message = f"{type(exc).__name__}: {str(exc)}"
    
    response = create_error_response(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR.value,
        request_id=request_id,
        message=message,
        details=details
    )
    
    return JSONResponse(
        status_code=500,
        content=response.model_dump(mode="json")
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with a FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    # Register custom exception handlers
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(ValidationException, api_exception_handler)
    app.add_exception_handler(AuthenticationException, api_exception_handler)
    app.add_exception_handler(PermissionException, api_exception_handler)
    app.add_exception_handler(NotFoundException, api_exception_handler)
    app.add_exception_handler(ConflictException, api_exception_handler)
    app.add_exception_handler(RateLimitException, api_exception_handler)
    app.add_exception_handler(ServiceException, api_exception_handler)
    
    # Register built-in exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_handler)
    
    # Register catch-all handler
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Registered global exception handlers")


# Convenience function for raising API exceptions
def raise_api_error(
    error_code: Union[str, ErrorCode],
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Raise an API exception with the given error code.
    
    Args:
        error_code: The error code
        message: Optional custom message
        details: Optional additional details
        
    Raises:
        APIException: Always raises this exception
    """
    raise APIException(error_code=error_code, message=message, details=details)


def raise_not_found(
    resource_type: str,
    resource_id: Optional[str] = None,
    message: Optional[str] = None
) -> None:
    """
    Raise a not found exception.
    
    Args:
        resource_type: Type of resource not found
        resource_id: Optional ID of the resource
        message: Optional custom message
        
    Raises:
        NotFoundException: Always raises this exception
    """
    raise NotFoundException(
        message=message,
        resource_type=resource_type,
        resource_id=resource_id
    )


def raise_validation_error(
    message: Optional[str] = None,
    field: Optional[str] = None,
    error_message: Optional[str] = None,
    value: Optional[Any] = None
) -> None:
    """
    Raise a validation exception.
    
    Args:
        message: Overall error message
        field: Field that failed validation
        error_message: Field-specific error message
        value: The invalid value
        
    Raises:
        ValidationException: Always raises this exception
    """
    validation_errors = []
    if field and error_message:
        validation_errors.append(
            ValidationErrorDetail(
                field=field,
                message=error_message,
                value=value
            )
        )
    
    raise ValidationException(
        message=message,
        validation_errors=validation_errors if validation_errors else None
    )
