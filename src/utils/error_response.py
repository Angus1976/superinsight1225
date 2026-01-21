"""
Standard Error Response Models for SuperInsight Platform.

Provides standardized error response models and error code enumerations
for consistent API error handling across all endpoints.

Validates: Requirements 10.5
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.i18n.translations import get_translation

logger = logging.getLogger(__name__)


class ErrorCodePrefix(str, Enum):
    """Error code prefixes for different error categories."""
    
    # Validation errors (400)
    VALIDATION = "VAL"
    
    # Authentication errors (401)
    AUTHENTICATION = "AUTH"
    
    # Authorization/Permission errors (403)
    PERMISSION = "PERM"
    
    # Resource not found errors (404)
    NOT_FOUND = "NOT_FOUND"
    
    # Conflict errors (409)
    CONFLICT = "CONFLICT"
    
    # Rate limit errors (429)
    RATE_LIMIT = "RATE_LIMIT"
    
    # Internal server errors (500)
    INTERNAL = "INTERNAL"
    
    # Service unavailable errors (503)
    SERVICE = "SERVICE"


class ErrorCode(str, Enum):
    """
    Standardized error codes for the SuperInsight platform.
    
    Format: {PREFIX}_{SPECIFIC_ERROR}
    """
    
    # Validation errors (400)
    VAL_INVALID_INPUT = "VAL_INVALID_INPUT"
    VAL_MISSING_FIELD = "VAL_MISSING_FIELD"
    VAL_INVALID_FORMAT = "VAL_INVALID_FORMAT"
    VAL_INVALID_VALUE = "VAL_INVALID_VALUE"
    VAL_FIELD_TOO_LONG = "VAL_FIELD_TOO_LONG"
    VAL_FIELD_TOO_SHORT = "VAL_FIELD_TOO_SHORT"
    VAL_INVALID_TYPE = "VAL_INVALID_TYPE"
    VAL_INVALID_RANGE = "VAL_INVALID_RANGE"
    VAL_INVALID_ENUM = "VAL_INVALID_ENUM"
    VAL_INVALID_JSON = "VAL_INVALID_JSON"
    
    # Authentication errors (401)
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    AUTH_ACCOUNT_LOCKED = "AUTH_ACCOUNT_LOCKED"
    AUTH_ACCOUNT_DISABLED = "AUTH_ACCOUNT_DISABLED"
    
    # Permission errors (403)
    PERM_ACCESS_DENIED = "PERM_ACCESS_DENIED"
    PERM_INSUFFICIENT_ROLE = "PERM_INSUFFICIENT_ROLE"
    PERM_RESOURCE_FORBIDDEN = "PERM_RESOURCE_FORBIDDEN"
    PERM_OPERATION_FORBIDDEN = "PERM_OPERATION_FORBIDDEN"
    PERM_TENANT_MISMATCH = "PERM_TENANT_MISMATCH"
    
    # Not found errors (404)
    NOT_FOUND_RESOURCE = "NOT_FOUND_RESOURCE"
    NOT_FOUND_USER = "NOT_FOUND_USER"
    NOT_FOUND_TASK = "NOT_FOUND_TASK"
    NOT_FOUND_PROJECT = "NOT_FOUND_PROJECT"
    NOT_FOUND_ANNOTATION = "NOT_FOUND_ANNOTATION"
    NOT_FOUND_DATA_SOURCE = "NOT_FOUND_DATA_SOURCE"
    NOT_FOUND_EVALUATION = "NOT_FOUND_EVALUATION"
    NOT_FOUND_RULE = "NOT_FOUND_RULE"
    NOT_FOUND_ENDPOINT = "NOT_FOUND_ENDPOINT"
    
    # Conflict errors (409)
    CONFLICT_RESOURCE_EXISTS = "CONFLICT_RESOURCE_EXISTS"
    CONFLICT_VERSION_MISMATCH = "CONFLICT_VERSION_MISMATCH"
    CONFLICT_STATE_INVALID = "CONFLICT_STATE_INVALID"
    CONFLICT_DUPLICATE_KEY = "CONFLICT_DUPLICATE_KEY"
    CONFLICT_CONCURRENT_UPDATE = "CONFLICT_CONCURRENT_UPDATE"
    
    # Rate limit errors (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    RATE_LIMIT_API_QUOTA = "RATE_LIMIT_API_QUOTA"
    RATE_LIMIT_USER_QUOTA = "RATE_LIMIT_USER_QUOTA"
    
    # Internal errors (500)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    INTERNAL_DATABASE_ERROR = "INTERNAL_DATABASE_ERROR"
    INTERNAL_CACHE_ERROR = "INTERNAL_CACHE_ERROR"
    INTERNAL_PROCESSING_ERROR = "INTERNAL_PROCESSING_ERROR"
    INTERNAL_CONFIGURATION_ERROR = "INTERNAL_CONFIGURATION_ERROR"
    INTERNAL_UNEXPECTED_ERROR = "INTERNAL_UNEXPECTED_ERROR"
    
    # Service unavailable errors (503)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_MAINTENANCE = "SERVICE_MAINTENANCE"
    SERVICE_OVERLOADED = "SERVICE_OVERLOADED"
    SERVICE_DEPENDENCY_FAILED = "SERVICE_DEPENDENCY_FAILED"
    SERVICE_TIMEOUT = "SERVICE_TIMEOUT"


# Error code to HTTP status code mapping
ERROR_CODE_TO_STATUS: Dict[str, int] = {
    # Validation errors -> 400
    ErrorCode.VAL_INVALID_INPUT.value: 400,
    ErrorCode.VAL_MISSING_FIELD.value: 400,
    ErrorCode.VAL_INVALID_FORMAT.value: 400,
    ErrorCode.VAL_INVALID_VALUE.value: 400,
    ErrorCode.VAL_FIELD_TOO_LONG.value: 400,
    ErrorCode.VAL_FIELD_TOO_SHORT.value: 400,
    ErrorCode.VAL_INVALID_TYPE.value: 400,
    ErrorCode.VAL_INVALID_RANGE.value: 400,
    ErrorCode.VAL_INVALID_ENUM.value: 400,
    ErrorCode.VAL_INVALID_JSON.value: 400,
    
    # Authentication errors -> 401
    ErrorCode.AUTH_INVALID_CREDENTIALS.value: 401,
    ErrorCode.AUTH_TOKEN_EXPIRED.value: 401,
    ErrorCode.AUTH_TOKEN_INVALID.value: 401,
    ErrorCode.AUTH_TOKEN_MISSING.value: 401,
    ErrorCode.AUTH_SESSION_EXPIRED.value: 401,
    ErrorCode.AUTH_ACCOUNT_LOCKED.value: 401,
    ErrorCode.AUTH_ACCOUNT_DISABLED.value: 401,
    
    # Permission errors -> 403
    ErrorCode.PERM_ACCESS_DENIED.value: 403,
    ErrorCode.PERM_INSUFFICIENT_ROLE.value: 403,
    ErrorCode.PERM_RESOURCE_FORBIDDEN.value: 403,
    ErrorCode.PERM_OPERATION_FORBIDDEN.value: 403,
    ErrorCode.PERM_TENANT_MISMATCH.value: 403,
    
    # Not found errors -> 404
    ErrorCode.NOT_FOUND_RESOURCE.value: 404,
    ErrorCode.NOT_FOUND_USER.value: 404,
    ErrorCode.NOT_FOUND_TASK.value: 404,
    ErrorCode.NOT_FOUND_PROJECT.value: 404,
    ErrorCode.NOT_FOUND_ANNOTATION.value: 404,
    ErrorCode.NOT_FOUND_DATA_SOURCE.value: 404,
    ErrorCode.NOT_FOUND_EVALUATION.value: 404,
    ErrorCode.NOT_FOUND_RULE.value: 404,
    ErrorCode.NOT_FOUND_ENDPOINT.value: 404,
    
    # Conflict errors -> 409
    ErrorCode.CONFLICT_RESOURCE_EXISTS.value: 409,
    ErrorCode.CONFLICT_VERSION_MISMATCH.value: 409,
    ErrorCode.CONFLICT_STATE_INVALID.value: 409,
    ErrorCode.CONFLICT_DUPLICATE_KEY.value: 409,
    ErrorCode.CONFLICT_CONCURRENT_UPDATE.value: 409,
    
    # Rate limit errors -> 429
    ErrorCode.RATE_LIMIT_EXCEEDED.value: 429,
    ErrorCode.RATE_LIMIT_API_QUOTA.value: 429,
    ErrorCode.RATE_LIMIT_USER_QUOTA.value: 429,
    
    # Internal errors -> 500
    ErrorCode.INTERNAL_SERVER_ERROR.value: 500,
    ErrorCode.INTERNAL_DATABASE_ERROR.value: 500,
    ErrorCode.INTERNAL_CACHE_ERROR.value: 500,
    ErrorCode.INTERNAL_PROCESSING_ERROR.value: 500,
    ErrorCode.INTERNAL_CONFIGURATION_ERROR.value: 500,
    ErrorCode.INTERNAL_UNEXPECTED_ERROR.value: 500,
    
    # Service unavailable errors -> 503
    ErrorCode.SERVICE_UNAVAILABLE.value: 503,
    ErrorCode.SERVICE_MAINTENANCE.value: 503,
    ErrorCode.SERVICE_OVERLOADED.value: 503,
    ErrorCode.SERVICE_DEPENDENCY_FAILED.value: 503,
    ErrorCode.SERVICE_TIMEOUT.value: 503,
}


# i18n translation keys for error codes
ERROR_CODE_I18N_KEYS: Dict[str, str] = {
    # Validation errors
    ErrorCode.VAL_INVALID_INPUT.value: "error.validation.invalid_input",
    ErrorCode.VAL_MISSING_FIELD.value: "error.validation.missing_field",
    ErrorCode.VAL_INVALID_FORMAT.value: "error.validation.invalid_format",
    ErrorCode.VAL_INVALID_VALUE.value: "error.validation.invalid_value",
    ErrorCode.VAL_FIELD_TOO_LONG.value: "error.validation.field_too_long",
    ErrorCode.VAL_FIELD_TOO_SHORT.value: "error.validation.field_too_short",
    ErrorCode.VAL_INVALID_TYPE.value: "error.validation.invalid_type",
    ErrorCode.VAL_INVALID_RANGE.value: "error.validation.invalid_range",
    ErrorCode.VAL_INVALID_ENUM.value: "error.validation.invalid_enum",
    ErrorCode.VAL_INVALID_JSON.value: "error.validation.invalid_json",
    
    # Authentication errors
    ErrorCode.AUTH_INVALID_CREDENTIALS.value: "error.auth.invalid_credentials",
    ErrorCode.AUTH_TOKEN_EXPIRED.value: "error.auth.token_expired",
    ErrorCode.AUTH_TOKEN_INVALID.value: "error.auth.token_invalid",
    ErrorCode.AUTH_TOKEN_MISSING.value: "error.auth.token_missing",
    ErrorCode.AUTH_SESSION_EXPIRED.value: "error.auth.session_expired",
    ErrorCode.AUTH_ACCOUNT_LOCKED.value: "error.auth.account_locked",
    ErrorCode.AUTH_ACCOUNT_DISABLED.value: "error.auth.account_disabled",
    
    # Permission errors
    ErrorCode.PERM_ACCESS_DENIED.value: "error.permission.access_denied",
    ErrorCode.PERM_INSUFFICIENT_ROLE.value: "error.permission.insufficient_role",
    ErrorCode.PERM_RESOURCE_FORBIDDEN.value: "error.permission.resource_forbidden",
    ErrorCode.PERM_OPERATION_FORBIDDEN.value: "error.permission.operation_forbidden",
    ErrorCode.PERM_TENANT_MISMATCH.value: "error.permission.tenant_mismatch",
    
    # Not found errors
    ErrorCode.NOT_FOUND_RESOURCE.value: "error.not_found.resource",
    ErrorCode.NOT_FOUND_USER.value: "error.not_found.user",
    ErrorCode.NOT_FOUND_TASK.value: "error.not_found.task",
    ErrorCode.NOT_FOUND_PROJECT.value: "error.not_found.project",
    ErrorCode.NOT_FOUND_ANNOTATION.value: "error.not_found.annotation",
    ErrorCode.NOT_FOUND_DATA_SOURCE.value: "error.not_found.data_source",
    ErrorCode.NOT_FOUND_EVALUATION.value: "error.not_found.evaluation",
    ErrorCode.NOT_FOUND_RULE.value: "error.not_found.rule",
    ErrorCode.NOT_FOUND_ENDPOINT.value: "error.not_found.endpoint",
    
    # Conflict errors
    ErrorCode.CONFLICT_RESOURCE_EXISTS.value: "error.conflict.resource_exists",
    ErrorCode.CONFLICT_VERSION_MISMATCH.value: "error.conflict.version_mismatch",
    ErrorCode.CONFLICT_STATE_INVALID.value: "error.conflict.state_invalid",
    ErrorCode.CONFLICT_DUPLICATE_KEY.value: "error.conflict.duplicate_key",
    ErrorCode.CONFLICT_CONCURRENT_UPDATE.value: "error.conflict.concurrent_update",
    
    # Rate limit errors
    ErrorCode.RATE_LIMIT_EXCEEDED.value: "error.rate_limit.exceeded",
    ErrorCode.RATE_LIMIT_API_QUOTA.value: "error.rate_limit.api_quota",
    ErrorCode.RATE_LIMIT_USER_QUOTA.value: "error.rate_limit.user_quota",
    
    # Internal errors
    ErrorCode.INTERNAL_SERVER_ERROR.value: "error.internal.server_error",
    ErrorCode.INTERNAL_DATABASE_ERROR.value: "error.internal.database_error",
    ErrorCode.INTERNAL_CACHE_ERROR.value: "error.internal.cache_error",
    ErrorCode.INTERNAL_PROCESSING_ERROR.value: "error.internal.processing_error",
    ErrorCode.INTERNAL_CONFIGURATION_ERROR.value: "error.internal.configuration_error",
    ErrorCode.INTERNAL_UNEXPECTED_ERROR.value: "error.internal.unexpected_error",
    
    # Service unavailable errors
    ErrorCode.SERVICE_UNAVAILABLE.value: "error.service.unavailable",
    ErrorCode.SERVICE_MAINTENANCE.value: "error.service.maintenance",
    ErrorCode.SERVICE_OVERLOADED.value: "error.service.overloaded",
    ErrorCode.SERVICE_DEPENDENCY_FAILED.value: "error.service.dependency_failed",
    ErrorCode.SERVICE_TIMEOUT.value: "error.service.timeout",
}


class ErrorResponse(BaseModel):
    """
    Standard error response model for API endpoints.
    
    This model provides a consistent structure for all API error responses,
    including error code, message, request ID, and optional details.
    
    Validates: Requirements 10.5
    """
    
    success: bool = Field(
        default=False,
        description="Indicates whether the request was successful"
    )
    error_code: str = Field(
        ...,
        description="Standardized error code (e.g., VAL_INVALID_INPUT)"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details (validation errors, resource info, etc.)"
    )
    request_id: str = Field(
        ...,
        description="Unique request identifier for tracing"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the error occurred"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "error_code": "VAL_INVALID_INPUT",
                "message": "输入数据无效",
                "details": {
                    "field": "email",
                    "reason": "格式不正确"
                },
                "request_id": "req_1234567890",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    }


class ValidationErrorDetail(BaseModel):
    """Detail model for validation errors."""
    
    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(default=None, description="The invalid value")
    constraint: Optional[str] = Field(default=None, description="The constraint that was violated")


class ValidationErrorResponse(ErrorResponse):
    """Extended error response for validation errors with field-level details."""
    
    validation_errors: Optional[list[ValidationErrorDetail]] = Field(
        default=None,
        description="List of field-level validation errors"
    )


def get_error_message(error_code: str, language: Optional[str] = None, **kwargs) -> str:
    """
    Get the localized error message for an error code.
    
    Args:
        error_code: The error code to get the message for
        language: Optional language code (defaults to current language)
        **kwargs: Format parameters for the message
        
    Returns:
        Localized error message
    """
    i18n_key = ERROR_CODE_I18N_KEYS.get(error_code)
    
    if i18n_key:
        try:
            return get_translation(i18n_key, language, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to get translation for {i18n_key}: {e}")
    
    # Fallback to default messages
    return _get_default_error_message(error_code, **kwargs)


def _get_default_error_message(error_code: str, **kwargs) -> str:
    """Get default error message when translation is not available."""
    default_messages = {
        # Validation errors
        ErrorCode.VAL_INVALID_INPUT.value: "输入数据无效",
        ErrorCode.VAL_MISSING_FIELD.value: "缺少必填字段",
        ErrorCode.VAL_INVALID_FORMAT.value: "格式无效",
        ErrorCode.VAL_INVALID_VALUE.value: "值无效",
        ErrorCode.VAL_FIELD_TOO_LONG.value: "字段过长",
        ErrorCode.VAL_FIELD_TOO_SHORT.value: "字段过短",
        ErrorCode.VAL_INVALID_TYPE.value: "类型无效",
        ErrorCode.VAL_INVALID_RANGE.value: "值超出范围",
        ErrorCode.VAL_INVALID_ENUM.value: "枚举值无效",
        ErrorCode.VAL_INVALID_JSON.value: "JSON格式无效",
        
        # Authentication errors
        ErrorCode.AUTH_INVALID_CREDENTIALS.value: "用户名或密码错误",
        ErrorCode.AUTH_TOKEN_EXPIRED.value: "令牌已过期",
        ErrorCode.AUTH_TOKEN_INVALID.value: "令牌无效",
        ErrorCode.AUTH_TOKEN_MISSING.value: "缺少认证令牌",
        ErrorCode.AUTH_SESSION_EXPIRED.value: "会话已过期",
        ErrorCode.AUTH_ACCOUNT_LOCKED.value: "账户已锁定",
        ErrorCode.AUTH_ACCOUNT_DISABLED.value: "账户已禁用",
        
        # Permission errors
        ErrorCode.PERM_ACCESS_DENIED.value: "访问被拒绝",
        ErrorCode.PERM_INSUFFICIENT_ROLE.value: "权限不足",
        ErrorCode.PERM_RESOURCE_FORBIDDEN.value: "禁止访问该资源",
        ErrorCode.PERM_OPERATION_FORBIDDEN.value: "禁止执行该操作",
        ErrorCode.PERM_TENANT_MISMATCH.value: "租户不匹配",
        
        # Not found errors
        ErrorCode.NOT_FOUND_RESOURCE.value: "资源未找到",
        ErrorCode.NOT_FOUND_USER.value: "用户未找到",
        ErrorCode.NOT_FOUND_TASK.value: "任务未找到",
        ErrorCode.NOT_FOUND_PROJECT.value: "项目未找到",
        ErrorCode.NOT_FOUND_ANNOTATION.value: "标注未找到",
        ErrorCode.NOT_FOUND_DATA_SOURCE.value: "数据源未找到",
        ErrorCode.NOT_FOUND_EVALUATION.value: "评估结果未找到",
        ErrorCode.NOT_FOUND_RULE.value: "规则未找到",
        ErrorCode.NOT_FOUND_ENDPOINT.value: "端点未找到",
        
        # Conflict errors
        ErrorCode.CONFLICT_RESOURCE_EXISTS.value: "资源已存在",
        ErrorCode.CONFLICT_VERSION_MISMATCH.value: "版本不匹配",
        ErrorCode.CONFLICT_STATE_INVALID.value: "状态无效",
        ErrorCode.CONFLICT_DUPLICATE_KEY.value: "键值重复",
        ErrorCode.CONFLICT_CONCURRENT_UPDATE.value: "并发更新冲突",
        
        # Rate limit errors
        ErrorCode.RATE_LIMIT_EXCEEDED.value: "请求频率超限",
        ErrorCode.RATE_LIMIT_API_QUOTA.value: "API配额已用尽",
        ErrorCode.RATE_LIMIT_USER_QUOTA.value: "用户配额已用尽",
        
        # Internal errors
        ErrorCode.INTERNAL_SERVER_ERROR.value: "服务器内部错误",
        ErrorCode.INTERNAL_DATABASE_ERROR.value: "数据库错误",
        ErrorCode.INTERNAL_CACHE_ERROR.value: "缓存错误",
        ErrorCode.INTERNAL_PROCESSING_ERROR.value: "处理错误",
        ErrorCode.INTERNAL_CONFIGURATION_ERROR.value: "配置错误",
        ErrorCode.INTERNAL_UNEXPECTED_ERROR.value: "未知错误",
        
        # Service unavailable errors
        ErrorCode.SERVICE_UNAVAILABLE.value: "服务不可用",
        ErrorCode.SERVICE_MAINTENANCE.value: "服务维护中",
        ErrorCode.SERVICE_OVERLOADED.value: "服务过载",
        ErrorCode.SERVICE_DEPENDENCY_FAILED.value: "依赖服务失败",
        ErrorCode.SERVICE_TIMEOUT.value: "服务超时",
    }
    
    message = default_messages.get(error_code, "发生错误")
    
    # Apply format parameters if any
    if kwargs:
        try:
            message = message.format(**kwargs)
        except (KeyError, ValueError):
            pass
    
    return message


def get_http_status_for_error_code(error_code: str) -> int:
    """
    Get the HTTP status code for an error code.
    
    Args:
        error_code: The error code
        
    Returns:
        HTTP status code (defaults to 500 if not found)
    """
    return ERROR_CODE_TO_STATUS.get(error_code, 500)


def create_error_response(
    error_code: str,
    request_id: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    language: Optional[str] = None,
    **format_kwargs
) -> ErrorResponse:
    """
    Create a standardized error response.
    
    Args:
        error_code: The error code
        request_id: The request ID for tracing
        message: Optional custom message (uses i18n if not provided)
        details: Optional additional details
        language: Optional language code for i18n
        **format_kwargs: Format parameters for the message
        
    Returns:
        ErrorResponse instance
    """
    if message is None:
        message = get_error_message(error_code, language, **format_kwargs)
    
    return ErrorResponse(
        success=False,
        error_code=error_code,
        message=message,
        details=details,
        request_id=request_id,
        timestamp=datetime.utcnow()
    )


def create_validation_error_response(
    request_id: str,
    validation_errors: list[ValidationErrorDetail],
    message: Optional[str] = None,
    language: Optional[str] = None
) -> ValidationErrorResponse:
    """
    Create a validation error response with field-level details.
    
    Args:
        request_id: The request ID for tracing
        validation_errors: List of validation error details
        message: Optional custom message
        language: Optional language code for i18n
        
    Returns:
        ValidationErrorResponse instance
    """
    if message is None:
        message = get_error_message(ErrorCode.VAL_INVALID_INPUT.value, language)
    
    return ValidationErrorResponse(
        success=False,
        error_code=ErrorCode.VAL_INVALID_INPUT.value,
        message=message,
        details={"error_count": len(validation_errors)},
        request_id=request_id,
        timestamp=datetime.utcnow(),
        validation_errors=validation_errors
    )
