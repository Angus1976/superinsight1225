"""
i18n API 错误处理模块
提供 API 端点的错误处理、验证和响应格式化
"""

from typing import Dict, Any, Optional, Union, List
from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError
import traceback

from .error_handler import log_translation_error
from .translations import get_translation


class APIErrorDetail(BaseModel):
    """API 错误详情模型"""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class APIErrorResponse(BaseModel):
    """API 错误响应模型"""
    error: str
    message: str
    details: Optional[List[APIErrorDetail]] = None
    request_id: Optional[str] = None
    timestamp: Optional[str] = None


class I18nAPIError(Exception):
    """i18n API 基础异常"""
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class ValidationAPIError(I18nAPIError):
    """API 验证错误"""
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details or {}
        )
        self.field = field


class LanguageNotSupportedAPIError(I18nAPIError):
    """不支持的语言 API 错误"""
    def __init__(self, language: str, supported_languages: List[str]):
        message = get_translation("unsupported_language")
        super().__init__(
            message=message,
            status_code=400,
            error_code="UNSUPPORTED_LANGUAGE",
            details={
                "requested_language": language,
                "supported_languages": supported_languages
            }
        )


class ResourceNotFoundAPIError(I18nAPIError):
    """资源未找到 API 错误"""
    def __init__(self, resource_type: str, resource_id: str = None):
        message = get_translation("resource_not_found")
        super().__init__(
            message=message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            }
        )


class InternalServerAPIError(I18nAPIError):
    """内部服务器 API 错误"""
    def __init__(self, original_error: Exception = None):
        message = get_translation("internal_server_error")
        details = {}
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__
        
        super().__init__(
            message=message,
            status_code=500,
            error_code="INTERNAL_SERVER_ERROR",
            details=details
        )


def validate_language_parameter(language: str, supported_languages: List[str]) -> str:
    """
    验证语言参数
    
    Args:
        language: 语言代码
        supported_languages: 支持的语言列表
        
    Returns:
        验证后的语言代码
        
    Raises:
        ValidationAPIError: 当参数无效时
        LanguageNotSupportedAPIError: 当语言不被支持时
    """
    if not language:
        raise ValidationAPIError(
            message=get_translation("missing_required_parameter"),
            field="language",
            details={"parameter": "language"}
        )
    
    if not isinstance(language, str):
        raise ValidationAPIError(
            message=get_translation("invalid_parameter_value"),
            field="language",
            details={
                "parameter": "language",
                "expected_type": "string",
                "actual_type": type(language).__name__
            }
        )
    
    language = language.strip().lower()
    
    if not language:
        raise ValidationAPIError(
            message=get_translation("invalid_parameter_value"),
            field="language",
            details={
                "parameter": "language",
                "reason": "empty_after_strip"
            }
        )
    
    if language not in supported_languages:
        raise LanguageNotSupportedAPIError(language, supported_languages)
    
    return language


def validate_query_parameters(
    request: Request,
    required_params: List[str] = None,
    optional_params: List[str] = None
) -> Dict[str, Any]:
    """
    验证查询参数
    
    Args:
        request: FastAPI 请求对象
        required_params: 必需参数列表
        optional_params: 可选参数列表
        
    Returns:
        验证后的参数字典
        
    Raises:
        ValidationAPIError: 当参数验证失败时
    """
    required_params = required_params or []
    optional_params = optional_params or []
    all_allowed_params = set(required_params + optional_params)
    
    validated_params = {}
    
    # 检查必需参数
    for param in required_params:
        if param not in request.query_params:
            raise ValidationAPIError(
                message=get_translation("missing_required_parameter"),
                field=param,
                details={"parameter": param}
            )
        
        value = request.query_params.get(param)
        if not value or not value.strip():
            raise ValidationAPIError(
                message=get_translation("invalid_parameter_value"),
                field=param,
                details={
                    "parameter": param,
                    "reason": "empty_value"
                }
            )
        
        validated_params[param] = value.strip()
    
    # 检查可选参数
    for param in optional_params:
        if param in request.query_params:
            value = request.query_params.get(param)
            if value is not None:
                validated_params[param] = value.strip() if isinstance(value, str) else value
    
    # 检查未知参数
    unknown_params = set(request.query_params.keys()) - all_allowed_params
    if unknown_params:
        log_translation_error(
            'unknown_query_parameters',
            {
                'unknown_params': list(unknown_params),
                'allowed_params': list(all_allowed_params),
                'request_url': str(request.url)
            },
            'warning'
        )
    
    return validated_params


def format_validation_error(validation_error: ValidationError) -> List[APIErrorDetail]:
    """
    格式化 Pydantic 验证错误
    
    Args:
        validation_error: Pydantic 验证错误
        
    Returns:
        格式化的错误详情列表
    """
    error_details = []
    
    for error in validation_error.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        error_detail = APIErrorDetail(
            code="VALIDATION_ERROR",
            message=error["msg"],
            field=field_path,
            details={
                "type": error["type"],
                "input": error.get("input"),
                "ctx": error.get("ctx", {})
            }
        )
        error_details.append(error_detail)
    
    return error_details


def create_error_response(
    error: Union[Exception, I18nAPIError],
    request_id: str = None
) -> APIErrorResponse:
    """
    创建标准化的错误响应
    
    Args:
        error: 异常对象
        request_id: 请求 ID
        
    Returns:
        格式化的错误响应
    """
    from datetime import datetime
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    if isinstance(error, I18nAPIError):
        # 自定义 API 错误
        details = []
        if error.details:
            detail = APIErrorDetail(
                code=error.error_code,
                message=error.message,
                details=error.details
            )
            details.append(detail)
        
        return APIErrorResponse(
            error=error.error_code,
            message=error.message,
            details=details if details else None,
            request_id=request_id,
            timestamp=timestamp
        )
    
    elif isinstance(error, ValidationError):
        # Pydantic 验证错误
        details = format_validation_error(error)
        return APIErrorResponse(
            error="VALIDATION_ERROR",
            message=get_translation("validation_failed"),
            details=details,
            request_id=request_id,
            timestamp=timestamp
        )
    
    elif isinstance(error, HTTPException):
        # FastAPI HTTP 异常
        return APIErrorResponse(
            error="HTTP_ERROR",
            message=str(error.detail),
            details=[APIErrorDetail(
                code=f"HTTP_{error.status_code}",
                message=str(error.detail),
                details={"status_code": error.status_code}
            )],
            request_id=request_id,
            timestamp=timestamp
        )
    
    else:
        # 未知异常
        log_translation_error(
            'unexpected_api_error',
            {
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc()
            },
            'error'
        )
        
        return APIErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message=get_translation("internal_server_error"),
            details=[APIErrorDetail(
                code="UNEXPECTED_ERROR",
                message=get_translation("internal_server_error"),
                details={
                    "error_type": type(error).__name__,
                    "error_message": str(error)
                }
            )],
            request_id=request_id,
            timestamp=timestamp
        )


def handle_api_exception(
    error: Exception,
    request: Request = None,
    request_id: str = None
) -> HTTPException:
    """
    处理 API 异常并转换为 HTTPException
    
    Args:
        error: 原始异常
        request: FastAPI 请求对象
        request_id: 请求 ID
        
    Returns:
        格式化的 HTTPException
    """
    # 记录错误
    log_translation_error(
        'api_exception_handled',
        {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'request_url': str(request.url) if request else None,
            'request_id': request_id
        },
        'error' if not isinstance(error, (ValidationAPIError, LanguageNotSupportedAPIError)) else 'warning'
    )
    
    # 创建错误响应
    error_response = create_error_response(error, request_id)
    
    # 确定状态码
    if isinstance(error, I18nAPIError):
        status_code = error.status_code
    elif isinstance(error, HTTPException):
        status_code = error.status_code
    elif isinstance(error, ValidationError):
        status_code = 400
    else:
        status_code = 500
    
    # 返回 HTTPException
    return HTTPException(
        status_code=status_code,
        detail=error_response.dict()
    )


def safe_api_call(func):
    """
    API 调用安全包装器装饰器
    自动处理异常并返回标准化的错误响应
    """
    from functools import wraps
    import uuid
    import inspect
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request_id = str(uuid.uuid4())
        
        try:
            # 检查函数是否接受 request_id 参数
            sig = inspect.signature(func)
            if 'request_id' in sig.parameters:
                kwargs['request_id'] = request_id
            
            return await func(*args, **kwargs)
            
        except (I18nAPIError, ValidationError, HTTPException) as e:
            # 已知的 API 错误
            raise handle_api_exception(e, kwargs.get('request'), request_id)
            
        except Exception as e:
            # 未知错误
            log_translation_error(
                'unexpected_api_error',
                {
                    'function': func.__name__,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'request_id': request_id,
                    'traceback': traceback.format_exc()
                },
                'critical'
            )
            
            # 创建内部服务器错误
            internal_error = InternalServerAPIError(e)
            raise handle_api_exception(internal_error, kwargs.get('request'), request_id)
    
    return wrapper


# HTTP 状态码映射
HTTP_STATUS_CODES = {
    200: "OK",
    201: "Created", 
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout"
}


def get_http_status_message(status_code: int) -> str:
    """
    获取 HTTP 状态码对应的消息
    
    Args:
        status_code: HTTP 状态码
        
    Returns:
        状态码消息
    """
    return HTTP_STATUS_CODES.get(status_code, "Unknown Status")


def validate_http_status_code(status_code: int) -> bool:
    """
    验证 HTTP 状态码是否合适
    
    Args:
        status_code: HTTP 状态码
        
    Returns:
        是否为合适的状态码
    """
    # 检查是否为有效的 HTTP 状态码范围
    if not (100 <= status_code <= 599):
        return False
    
    # 检查是否为常用的状态码
    return status_code in HTTP_STATUS_CODES


# 导出的类和函数
__all__ = [
    'APIErrorDetail',
    'APIErrorResponse', 
    'I18nAPIError',
    'ValidationAPIError',
    'LanguageNotSupportedAPIError',
    'ResourceNotFoundAPIError',
    'InternalServerAPIError',
    'validate_language_parameter',
    'validate_query_parameters',
    'format_validation_error',
    'create_error_response',
    'handle_api_exception',
    'safe_api_call',
    'get_http_status_message',
    'validate_http_status_code'
]