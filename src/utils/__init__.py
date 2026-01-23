# Utility functions module

from .cache_strategy import (
    CacheStrategy,
    CacheConfig,
    CacheStats,
    CacheI18nKeys,
    get_cache,
    close_cache,
    cached,
    invalidate_cache,
)

from .error_response import (
    ErrorCode,
    ErrorCodePrefix,
    ErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
    create_error_response,
    create_validation_error_response,
    get_error_message,
    get_http_status_for_error_code,
    ERROR_CODE_TO_STATUS,
    ERROR_CODE_I18N_KEYS,
)

from .exception_handler import (
    APIException,
    ValidationException,
    AuthenticationException,
    PermissionException,
    NotFoundException,
    ConflictException,
    RateLimitException,
    ServiceException,
    register_exception_handlers,
    raise_api_error,
    raise_not_found,
    raise_validation_error,
)

from .correlation_middleware import (
    CorrelationIdMiddleware,
    CorrelationIdFilter,
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
    generate_request_id,
    get_correlation_context,
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
)

from .logging_config import (
    LoggingConfig,
    StructuredLogFormatter,
    configure_logging,
    get_logging_config,
    get_logger,
    log_with_context,
    log_error_with_traceback,
)

__all__ = [
    # Cache strategy
    "CacheStrategy",
    "CacheConfig",
    "CacheStats",
    "CacheI18nKeys",
    "get_cache",
    "close_cache",
    "cached",
    "invalidate_cache",
    
    # Error response
    "ErrorCode",
    "ErrorCodePrefix",
    "ErrorResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    "create_error_response",
    "create_validation_error_response",
    "get_error_message",
    "get_http_status_for_error_code",
    "ERROR_CODE_TO_STATUS",
    "ERROR_CODE_I18N_KEYS",
    
    # Exception handler
    "APIException",
    "ValidationException",
    "AuthenticationException",
    "PermissionException",
    "NotFoundException",
    "ConflictException",
    "RateLimitException",
    "ServiceException",
    "register_exception_handlers",
    "raise_api_error",
    "raise_not_found",
    "raise_validation_error",
    
    # Correlation middleware
    "CorrelationIdMiddleware",
    "CorrelationIdFilter",
    "get_correlation_id",
    "set_correlation_id",
    "generate_correlation_id",
    "generate_request_id",
    "get_correlation_context",
    "CORRELATION_ID_HEADER",
    "REQUEST_ID_HEADER",
    
    # Logging config
    "LoggingConfig",
    "StructuredLogFormatter",
    "configure_logging",
    "get_logging_config",
    "get_logger",
    "log_with_context",
    "log_error_with_traceback",
]