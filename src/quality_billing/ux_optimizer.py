"""
UX Optimizer for Quality-Billing Loop System

Provides utilities for better API responses, error handling,
pagination, and user-friendly interfaces.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
import json
import traceback


T = TypeVar("T")


# ============================================================================
# Standard API Response Format
# ============================================================================


class ResponseStatus(Enum):
    """API response status codes"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"


@dataclass
class ApiMeta:
    """Metadata for API responses"""
    request_id: str
    timestamp: str
    version: str = "1.0"
    processing_time_ms: Optional[float] = None
    rate_limit_remaining: Optional[int] = None


@dataclass
class ApiError:
    """Structured API error"""
    code: str
    message: str
    details: Optional[str] = None
    field: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "code": self.code,
            "message": self.message
        }
        if self.details:
            result["details"] = self.details
        if self.field:
            result["field"] = self.field
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


@dataclass
class ApiResponse(Generic[T]):
    """Standard API response wrapper"""
    status: ResponseStatus
    data: Optional[T] = None
    errors: List[ApiError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    meta: Optional[ApiMeta] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "status": self.status.value,
        }

        if self.data is not None:
            result["data"] = self.data

        if self.errors:
            result["errors"] = [e.to_dict() for e in self.errors]

        if self.warnings:
            result["warnings"] = self.warnings

        if self.meta:
            result["meta"] = {
                "request_id": self.meta.request_id,
                "timestamp": self.meta.timestamp,
                "version": self.meta.version,
            }
            if self.meta.processing_time_ms is not None:
                result["meta"]["processing_time_ms"] = self.meta.processing_time_ms
            if self.meta.rate_limit_remaining is not None:
                result["meta"]["rate_limit_remaining"] = self.meta.rate_limit_remaining

        return result

    def to_json(self, indent: Optional[int] = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @property
    def is_success(self) -> bool:
        return self.status == ResponseStatus.SUCCESS

    @property
    def is_error(self) -> bool:
        return self.status == ResponseStatus.ERROR


class ResponseBuilder(Generic[T]):
    """Builder for creating API responses"""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self._start_time = datetime.now()
        self._data: Optional[T] = None
        self._errors: List[ApiError] = []
        self._warnings: List[str] = []
        self._rate_limit_remaining: Optional[int] = None

    def with_data(self, data: T) -> "ResponseBuilder[T]":
        self._data = data
        return self

    def with_error(
        self,
        code: str,
        message: str,
        details: Optional[str] = None,
        field: Optional[str] = None,
        suggestion: Optional[str] = None
    ) -> "ResponseBuilder[T]":
        self._errors.append(ApiError(
            code=code,
            message=message,
            details=details,
            field=field,
            suggestion=suggestion
        ))
        return self

    def with_warning(self, message: str) -> "ResponseBuilder[T]":
        self._warnings.append(message)
        return self

    def with_rate_limit(self, remaining: int) -> "ResponseBuilder[T]":
        self._rate_limit_remaining = remaining
        return self

    def build(self) -> ApiResponse[T]:
        processing_time = (datetime.now() - self._start_time).total_seconds() * 1000

        if self._errors:
            status = ResponseStatus.ERROR
        elif self._warnings:
            status = ResponseStatus.WARNING
        else:
            status = ResponseStatus.SUCCESS

        meta = ApiMeta(
            request_id=self.request_id,
            timestamp=datetime.now().isoformat(),
            processing_time_ms=processing_time,
            rate_limit_remaining=self._rate_limit_remaining
        )

        return ApiResponse(
            status=status,
            data=self._data,
            errors=self._errors,
            warnings=self._warnings,
            meta=meta
        )


# ============================================================================
# Error Handling and User-Friendly Messages
# ============================================================================


class ErrorCode(Enum):
    """Standard error codes"""
    # Validation errors (400)
    VALIDATION_FAILED = ("VALIDATION_FAILED", "请求数据验证失败")
    MISSING_REQUIRED_FIELD = ("MISSING_REQUIRED_FIELD", "缺少必需字段")
    INVALID_FORMAT = ("INVALID_FORMAT", "数据格式无效")
    VALUE_OUT_OF_RANGE = ("VALUE_OUT_OF_RANGE", "值超出有效范围")

    # Authentication errors (401)
    UNAUTHORIZED = ("UNAUTHORIZED", "未授权访问")
    TOKEN_EXPIRED = ("TOKEN_EXPIRED", "认证令牌已过期")
    INVALID_CREDENTIALS = ("INVALID_CREDENTIALS", "用户名或密码错误")

    # Permission errors (403)
    PERMISSION_DENIED = ("PERMISSION_DENIED", "没有权限执行此操作")
    RESOURCE_FORBIDDEN = ("RESOURCE_FORBIDDEN", "禁止访问此资源")

    # Not found errors (404)
    RESOURCE_NOT_FOUND = ("RESOURCE_NOT_FOUND", "请求的资源不存在")
    ENDPOINT_NOT_FOUND = ("ENDPOINT_NOT_FOUND", "API 端点不存在")

    # Conflict errors (409)
    RESOURCE_CONFLICT = ("RESOURCE_CONFLICT", "资源冲突")
    DUPLICATE_ENTRY = ("DUPLICATE_ENTRY", "数据重复")

    # Rate limit errors (429)
    RATE_LIMIT_EXCEEDED = ("RATE_LIMIT_EXCEEDED", "请求频率超限")

    # Server errors (500)
    INTERNAL_ERROR = ("INTERNAL_ERROR", "服务器内部错误")
    DATABASE_ERROR = ("DATABASE_ERROR", "数据库操作失败")
    SERVICE_UNAVAILABLE = ("SERVICE_UNAVAILABLE", "服务暂时不可用")

    def __init__(self, code: str, message: str):
        self._code = code
        self._message = message

    @property
    def code(self) -> str:
        return self._code

    @property
    def message(self) -> str:
        return self._message


class ErrorSuggestions:
    """Provides helpful suggestions for common errors"""

    SUGGESTIONS: Dict[str, str] = {
        "VALIDATION_FAILED": "请检查请求数据格式是否正确",
        "MISSING_REQUIRED_FIELD": "请确保提供所有必需的字段",
        "INVALID_FORMAT": "请参考 API 文档了解正确的数据格式",
        "VALUE_OUT_OF_RANGE": "请确保数值在有效范围内",
        "UNAUTHORIZED": "请登录后再试",
        "TOKEN_EXPIRED": "请重新登录获取新的认证令牌",
        "INVALID_CREDENTIALS": "请检查用户名和密码是否正确",
        "PERMISSION_DENIED": "请联系管理员获取相应权限",
        "RESOURCE_NOT_FOUND": "请检查资源 ID 是否正确",
        "RATE_LIMIT_EXCEEDED": "请稍后重试，或考虑升级服务计划",
        "INTERNAL_ERROR": "请稍后重试，如问题持续请联系技术支持",
        "DATABASE_ERROR": "请稍后重试",
        "SERVICE_UNAVAILABLE": "服务正在维护中，请稍后重试",
    }

    @classmethod
    def get_suggestion(cls, error_code: str) -> Optional[str]:
        return cls.SUGGESTIONS.get(error_code)


class ErrorHandler:
    """Handles exceptions and converts them to user-friendly errors"""

    def __init__(self, include_trace: bool = False):
        self.include_trace = include_trace
        self._error_handlers: Dict[type, ErrorCode] = {
            ValueError: ErrorCode.VALIDATION_FAILED,
            KeyError: ErrorCode.MISSING_REQUIRED_FIELD,
            PermissionError: ErrorCode.PERMISSION_DENIED,
            FileNotFoundError: ErrorCode.RESOURCE_NOT_FOUND,
            TimeoutError: ErrorCode.SERVICE_UNAVAILABLE,
        }

    def register_handler(self, exception_type: type, error_code: ErrorCode) -> None:
        """Register a custom exception handler"""
        self._error_handlers[exception_type] = error_code

    def handle(self, exception: Exception) -> ApiError:
        """Convert exception to ApiError"""
        error_code = self._error_handlers.get(type(exception), ErrorCode.INTERNAL_ERROR)

        details = str(exception) if str(exception) else None
        if self.include_trace:
            details = traceback.format_exc()

        return ApiError(
            code=error_code.code,
            message=error_code.message,
            details=details,
            suggestion=ErrorSuggestions.get_suggestion(error_code.code)
        )

    def wrap_response(
        self,
        exception: Exception,
        request_id: str
    ) -> ApiResponse[None]:
        """Create an error response from exception"""
        error = self.handle(exception)
        return ResponseBuilder[None](request_id).with_error(
            code=error.code,
            message=error.message,
            details=error.details,
            suggestion=error.suggestion
        ).build()


# ============================================================================
# Pagination Support
# ============================================================================


@dataclass
class PaginationParams:
    """Pagination parameters"""
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "asc"  # "asc" or "desc"

    def __post_init__(self):
        if self.page < 1:
            self.page = 1
        if self.page_size < 1:
            self.page_size = 20
        if self.page_size > 100:
            self.page_size = 100
        if self.sort_order not in ("asc", "desc"):
            self.sort_order = "asc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass
class PaginationMeta:
    """Pagination metadata"""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_previous: bool
    has_next: bool

    @classmethod
    def from_params(
        cls,
        params: PaginationParams,
        total_items: int
    ) -> "PaginationMeta":
        total_pages = (total_items + params.page_size - 1) // params.page_size
        return cls(
            page=params.page,
            page_size=params.page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_previous=params.page > 1,
            has_next=params.page < total_pages
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_items": self.total_items,
            "total_pages": self.total_pages,
            "has_previous": self.has_previous,
            "has_next": self.has_next
        }


@dataclass
class PaginatedResponse(Generic[T]):
    """Paginated response wrapper"""
    items: List[T]
    pagination: PaginationMeta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": self.items,
            "pagination": self.pagination.to_dict()
        }


class Paginator(Generic[T]):
    """Handles list pagination"""

    def __init__(self, items: List[T], params: PaginationParams):
        self.items = items
        self.params = params
        self.total_items = len(items)

    def paginate(self) -> PaginatedResponse[T]:
        """Apply pagination to items"""
        # Sort if specified
        sorted_items = self._sort(self.items)

        # Apply offset and limit
        start = self.params.offset
        end = start + self.params.limit
        page_items = sorted_items[start:end]

        pagination = PaginationMeta.from_params(self.params, self.total_items)

        return PaginatedResponse(
            items=page_items,
            pagination=pagination
        )

    def _sort(self, items: List[T]) -> List[T]:
        """Sort items if sort_by is specified"""
        if not self.params.sort_by:
            return items

        try:
            reverse = self.params.sort_order == "desc"

            if hasattr(items[0] if items else None, self.params.sort_by):
                return sorted(
                    items,
                    key=lambda x: getattr(x, self.params.sort_by, None),
                    reverse=reverse
                )
            elif isinstance(items[0] if items else None, dict):
                return sorted(
                    items,
                    key=lambda x: x.get(self.params.sort_by),  # type: ignore
                    reverse=reverse
                )
        except (TypeError, AttributeError):
            pass

        return items


# ============================================================================
# Data Formatting Utilities
# ============================================================================


class DataFormatter:
    """Utilities for formatting data for display"""

    @staticmethod
    def format_currency(
        amount: float,
        currency: str = "CNY",
        decimal_places: int = 2
    ) -> str:
        """Format amount as currency"""
        symbols = {
            "CNY": "¥",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥"
        }
        symbol = symbols.get(currency, currency + " ")

        if currency == "JPY":
            return f"{symbol}{int(amount):,}"

        return f"{symbol}{amount:,.{decimal_places}f}"

    @staticmethod
    def format_percentage(
        value: float,
        decimal_places: int = 1,
        include_sign: bool = False
    ) -> str:
        """Format value as percentage"""
        percentage = value * 100
        sign = "+" if include_sign and percentage > 0 else ""
        return f"{sign}{percentage:.{decimal_places}f}%"

    @staticmethod
    def format_number(
        value: Union[int, float],
        decimal_places: int = 2,
        use_grouping: bool = True
    ) -> str:
        """Format number with grouping and decimals"""
        if isinstance(value, int):
            if use_grouping:
                return f"{value:,}"
            return str(value)

        if use_grouping:
            return f"{value:,.{decimal_places}f}"
        return f"{value:.{decimal_places}f}"

    @staticmethod
    def format_file_size(bytes_size: int) -> str:
        """Format bytes as human-readable file size"""
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(bytes_size)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        return f"{size:.2f} {units[unit_index]}"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.0f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    @staticmethod
    def format_datetime(
        dt: datetime,
        format_type: str = "full"
    ) -> str:
        """Format datetime in various styles"""
        formats = {
            "full": "%Y-%m-%d %H:%M:%S",
            "date": "%Y-%m-%d",
            "time": "%H:%M:%S",
            "short": "%m/%d %H:%M",
            "relative": None  # Handled separately
        }

        if format_type == "relative":
            now = datetime.now()
            diff = now - dt

            if diff.total_seconds() < 60:
                return "刚刚"
            elif diff.total_seconds() < 3600:
                minutes = int(diff.total_seconds() // 60)
                return f"{minutes}分钟前"
            elif diff.total_seconds() < 86400:
                hours = int(diff.total_seconds() // 3600)
                return f"{hours}小时前"
            elif diff.days < 7:
                return f"{diff.days}天前"
            else:
                return dt.strftime("%Y-%m-%d")

        fmt = formats.get(format_type, formats["full"])
        return dt.strftime(fmt)  # type: ignore

    @staticmethod
    def truncate_text(
        text: str,
        max_length: int = 100,
        suffix: str = "..."
    ) -> str:
        """Truncate text to max length"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix


# ============================================================================
# User Preference Management
# ============================================================================


@dataclass
class UserPreferences:
    """User interface preferences"""
    theme: str = "light"  # "light" or "dark"
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    date_format: str = "YYYY-MM-DD"
    items_per_page: int = 20
    notifications_enabled: bool = True
    dashboard_layout: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme": self.theme,
            "language": self.language,
            "timezone": self.timezone,
            "date_format": self.date_format,
            "items_per_page": self.items_per_page,
            "notifications_enabled": self.notifications_enabled,
            "dashboard_layout": self.dashboard_layout
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        return cls(
            theme=data.get("theme", "light"),
            language=data.get("language", "zh-CN"),
            timezone=data.get("timezone", "Asia/Shanghai"),
            date_format=data.get("date_format", "YYYY-MM-DD"),
            items_per_page=data.get("items_per_page", 20),
            notifications_enabled=data.get("notifications_enabled", True),
            dashboard_layout=data.get("dashboard_layout", {})
        )


class PreferenceManager:
    """Manages user preferences"""

    def __init__(self):
        self._preferences: Dict[str, UserPreferences] = {}
        self._default = UserPreferences()

    def get_preferences(self, user_id: str) -> UserPreferences:
        """Get preferences for a user"""
        return self._preferences.get(user_id, self._default)

    def set_preferences(self, user_id: str, preferences: UserPreferences) -> None:
        """Set preferences for a user"""
        self._preferences[user_id] = preferences

    def update_preference(
        self,
        user_id: str,
        key: str,
        value: Any
    ) -> UserPreferences:
        """Update a single preference"""
        prefs = self.get_preferences(user_id)

        if hasattr(prefs, key):
            setattr(prefs, key, value)
            self._preferences[user_id] = prefs

        return prefs

    def reset_to_default(self, user_id: str) -> UserPreferences:
        """Reset preferences to default"""
        self._preferences[user_id] = UserPreferences()
        return self._preferences[user_id]


# ============================================================================
# Help and Guidance System
# ============================================================================


@dataclass
class HelpTopic:
    """Help topic with content"""
    id: str
    title: str
    content: str
    category: str
    keywords: List[str] = field(default_factory=list)
    related_topics: List[str] = field(default_factory=list)


@dataclass
class ContextualHelp:
    """Contextual help for UI elements"""
    element_id: str
    title: str
    description: str
    tips: List[str] = field(default_factory=list)
    learn_more_url: Optional[str] = None


class HelpSystem:
    """Provides help and guidance content"""

    def __init__(self):
        self._topics: Dict[str, HelpTopic] = {}
        self._contextual_help: Dict[str, ContextualHelp] = {}
        self._faq: List[Dict[str, str]] = []

    def add_topic(self, topic: HelpTopic) -> None:
        """Add a help topic"""
        self._topics[topic.id] = topic

    def get_topic(self, topic_id: str) -> Optional[HelpTopic]:
        """Get a help topic by ID"""
        return self._topics.get(topic_id)

    def search_topics(self, query: str) -> List[HelpTopic]:
        """Search help topics by query"""
        query_lower = query.lower()
        results = []

        for topic in self._topics.values():
            # Check title
            if query_lower in topic.title.lower():
                results.append(topic)
                continue

            # Check keywords
            for keyword in topic.keywords:
                if query_lower in keyword.lower():
                    results.append(topic)
                    break

        return results

    def add_contextual_help(self, help_item: ContextualHelp) -> None:
        """Add contextual help for a UI element"""
        self._contextual_help[help_item.element_id] = help_item

    def get_contextual_help(self, element_id: str) -> Optional[ContextualHelp]:
        """Get contextual help for a UI element"""
        return self._contextual_help.get(element_id)

    def add_faq(self, question: str, answer: str) -> None:
        """Add a FAQ entry"""
        self._faq.append({"question": question, "answer": answer})

    def get_faq(self) -> List[Dict[str, str]]:
        """Get all FAQ entries"""
        return self._faq

    def search_faq(self, query: str) -> List[Dict[str, str]]:
        """Search FAQ by query"""
        query_lower = query.lower()
        return [
            faq for faq in self._faq
            if query_lower in faq["question"].lower()
            or query_lower in faq["answer"].lower()
        ]


# ============================================================================
# Form Validation
# ============================================================================


@dataclass
class ValidationRule:
    """Validation rule for a field"""
    field: str
    rule_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    errors: List[ApiError] = field(default_factory=list)


class FormValidator:
    """Validates form data"""

    def __init__(self):
        self._rules: List[ValidationRule] = []

    def add_rule(
        self,
        field: str,
        rule_type: str,
        params: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ) -> "FormValidator":
        """Add a validation rule"""
        self._rules.append(ValidationRule(
            field=field,
            rule_type=rule_type,
            params=params or {},
            message=message or ""
        ))
        return self

    def required(self, field: str, message: str = "") -> "FormValidator":
        """Add required field rule"""
        return self.add_rule(field, "required", message=message or f"{field} 是必填项")

    def min_length(self, field: str, length: int, message: str = "") -> "FormValidator":
        """Add minimum length rule"""
        return self.add_rule(
            field, "min_length",
            params={"length": length},
            message=message or f"{field} 至少需要 {length} 个字符"
        )

    def max_length(self, field: str, length: int, message: str = "") -> "FormValidator":
        """Add maximum length rule"""
        return self.add_rule(
            field, "max_length",
            params={"length": length},
            message=message or f"{field} 不能超过 {length} 个字符"
        )

    def min_value(self, field: str, value: float, message: str = "") -> "FormValidator":
        """Add minimum value rule"""
        return self.add_rule(
            field, "min_value",
            params={"value": value},
            message=message or f"{field} 不能小于 {value}"
        )

    def max_value(self, field: str, value: float, message: str = "") -> "FormValidator":
        """Add maximum value rule"""
        return self.add_rule(
            field, "max_value",
            params={"value": value},
            message=message or f"{field} 不能大于 {value}"
        )

    def pattern(self, field: str, pattern: str, message: str = "") -> "FormValidator":
        """Add regex pattern rule"""
        return self.add_rule(
            field, "pattern",
            params={"pattern": pattern},
            message=message or f"{field} 格式不正确"
        )

    def email(self, field: str, message: str = "") -> "FormValidator":
        """Add email format rule"""
        return self.add_rule(
            field, "email",
            message=message or f"{field} 必须是有效的邮箱地址"
        )

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate data against rules"""
        import re

        errors = []

        for rule in self._rules:
            value = data.get(rule.field)

            if rule.rule_type == "required":
                if value is None or value == "":
                    errors.append(ApiError(
                        code="VALIDATION_REQUIRED",
                        message=rule.message,
                        field=rule.field
                    ))

            elif rule.rule_type == "min_length":
                if value and len(str(value)) < rule.params["length"]:
                    errors.append(ApiError(
                        code="VALIDATION_MIN_LENGTH",
                        message=rule.message,
                        field=rule.field
                    ))

            elif rule.rule_type == "max_length":
                if value and len(str(value)) > rule.params["length"]:
                    errors.append(ApiError(
                        code="VALIDATION_MAX_LENGTH",
                        message=rule.message,
                        field=rule.field
                    ))

            elif rule.rule_type == "min_value":
                if value is not None and float(value) < rule.params["value"]:
                    errors.append(ApiError(
                        code="VALIDATION_MIN_VALUE",
                        message=rule.message,
                        field=rule.field
                    ))

            elif rule.rule_type == "max_value":
                if value is not None and float(value) > rule.params["value"]:
                    errors.append(ApiError(
                        code="VALIDATION_MAX_VALUE",
                        message=rule.message,
                        field=rule.field
                    ))

            elif rule.rule_type == "pattern":
                if value and not re.match(rule.params["pattern"], str(value)):
                    errors.append(ApiError(
                        code="VALIDATION_PATTERN",
                        message=rule.message,
                        field=rule.field
                    ))

            elif rule.rule_type == "email":
                email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                if value and not re.match(email_pattern, str(value)):
                    errors.append(ApiError(
                        code="VALIDATION_EMAIL",
                        message=rule.message,
                        field=rule.field
                    ))

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
