"""
增强的 API 输入验证模块

提供企业级输入验证功能，包括：
- 自定义 Pydantic 验证器
- XSS/SQL注入检测
- 常见格式验证
- 安全字符串处理

Validates: 需求 14.2
"""

import re
import html
import logging
from typing import Any, Optional, List, Dict, Pattern
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated
from functools import lru_cache

from src.i18n.translations import get_translation

logger = logging.getLogger(__name__)


# ============================================================================
# 安全模式定义
# ============================================================================

# XSS 攻击模式
XSS_PATTERNS: List[Pattern] = [
    re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),
    re.compile(r'<iframe[^>]*>', re.IGNORECASE),
    re.compile(r'<object[^>]*>', re.IGNORECASE),
    re.compile(r'<embed[^>]*>', re.IGNORECASE),
    re.compile(r'<link[^>]*>', re.IGNORECASE),
    re.compile(r'expression\s*\(', re.IGNORECASE),
    re.compile(r'vbscript:', re.IGNORECASE),
    re.compile(r'data:text/html', re.IGNORECASE),
]

# SQL 注入模式
SQL_INJECTION_PATTERNS: List[Pattern] = [
    re.compile(r"'\s*or\s+'", re.IGNORECASE),
    re.compile(r"'\s*or\s+1\s*=\s*1", re.IGNORECASE),
    re.compile(r";\s*drop\s+", re.IGNORECASE),
    re.compile(r";\s*delete\s+", re.IGNORECASE),
    re.compile(r";\s*update\s+", re.IGNORECASE),
    re.compile(r";\s*insert\s+", re.IGNORECASE),
    re.compile(r"union\s+select", re.IGNORECASE),
    re.compile(r"--\s*$", re.MULTILINE),
    re.compile(r"/\*.*?\*/", re.DOTALL),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"execute\s*\(", re.IGNORECASE),
]

# 路径遍历模式
PATH_TRAVERSAL_PATTERNS: List[Pattern] = [
    re.compile(r'\.\./', re.IGNORECASE),
    re.compile(r'\.\.\\', re.IGNORECASE),
    re.compile(r'%2e%2e%2f', re.IGNORECASE),
    re.compile(r'%2e%2e/', re.IGNORECASE),
    re.compile(r'\.%2e/', re.IGNORECASE),
    re.compile(r'%2e\./', re.IGNORECASE),
]

# 常用正则表达式
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)
PHONE_PATTERN = re.compile(
    r'^(\+?86)?1[3-9]\d{9}$|^\d{3,4}-?\d{7,8}$'
)
URL_PATTERN = re.compile(
    r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE
)
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)
IP_V4_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)
IP_V6_PATTERN = re.compile(
    r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|'
    r'^(?:[0-9a-fA-F]{1,4}:){1,7}:$|'
    r'^(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}$'
)


# ============================================================================
# 验证异常
# ============================================================================

class ValidationError(Exception):
    """验证错误"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class XSSDetectedError(ValidationError):
    """XSS 攻击检测错误"""
    pass


class SQLInjectionDetectedError(ValidationError):
    """SQL 注入检测错误"""
    pass


class PathTraversalDetectedError(ValidationError):
    """路径遍历攻击检测错误"""
    pass


# ============================================================================
# 验证函数
# ============================================================================

def detect_xss(value: str) -> bool:
    """
    检测 XSS 攻击
    
    Args:
        value: 要检测的字符串
        
    Returns:
        如果检测到 XSS 攻击返回 True
    """
    if not value:
        return False
    
    for pattern in XSS_PATTERNS:
        if pattern.search(value):
            logger.warning(f"security.validation.xss_detected: {value[:100]}")
            return True
    return False


def detect_sql_injection(value: str) -> bool:
    """
    检测 SQL 注入
    
    Args:
        value: 要检测的字符串
        
    Returns:
        如果检测到 SQL 注入返回 True
    """
    if not value:
        return False
    
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(value):
            logger.warning(f"security.validation.sql_injection_detected: {value[:100]}")
            return True
    return False


def detect_path_traversal(value: str) -> bool:
    """
    检测路径遍历攻击
    
    Args:
        value: 要检测的字符串
        
    Returns:
        如果检测到路径遍历攻击返回 True
    """
    if not value:
        return False
    
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern.search(value):
            logger.warning(f"security.validation.path_traversal_detected: {value[:100]}")
            return True
    return False


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    清理字符串，移除潜在危险内容
    
    Args:
        value: 要清理的字符串
        max_length: 最大长度
        
    Returns:
        清理后的字符串
    """
    if not value:
        return value
    
    # 截断过长字符串
    if len(value) > max_length:
        value = value[:max_length]
    
    # HTML 转义
    value = html.escape(value)
    
    # 移除控制字符（保留换行和制表符）
    value = ''.join(
        char for char in value
        if char in '\n\r\t' or (ord(char) >= 32 and ord(char) != 127)
    )
    
    return value.strip()


def validate_email(value: str) -> bool:
    """验证邮箱格式"""
    return bool(EMAIL_PATTERN.match(value)) if value else False


def validate_phone(value: str) -> bool:
    """验证电话号码格式（支持中国大陆号码）"""
    return bool(PHONE_PATTERN.match(value)) if value else False


def validate_url(value: str) -> bool:
    """验证 URL 格式"""
    return bool(URL_PATTERN.match(value)) if value else False


def validate_uuid(value: str) -> bool:
    """验证 UUID 格式"""
    return bool(UUID_PATTERN.match(value)) if value else False


def validate_ip_address(value: str) -> bool:
    """验证 IP 地址格式（支持 IPv4 和 IPv6）"""
    if not value:
        return False
    return bool(IP_V4_PATTERN.match(value) or IP_V6_PATTERN.match(value))


# ============================================================================
# Pydantic 验证器
# ============================================================================

def safe_string_validator(value: Any) -> str:
    """
    安全字符串验证器
    
    检测并阻止 XSS 和 SQL 注入攻击
    """
    if value is None:
        return value
    
    if not isinstance(value, str):
        value = str(value)
    
    # 检测 XSS
    if detect_xss(value):
        raise ValueError(
            get_translation("security.validation.xss_detected", "zh")
        )
    
    # 检测 SQL 注入
    if detect_sql_injection(value):
        raise ValueError(
            get_translation("security.validation.sql_injection_detected", "zh")
        )
    
    return value


def safe_path_validator(value: Any) -> str:
    """
    安全路径验证器
    
    检测并阻止路径遍历攻击
    """
    if value is None:
        return value
    
    if not isinstance(value, str):
        value = str(value)
    
    # 检测路径遍历
    if detect_path_traversal(value):
        raise ValueError(
            get_translation("security.validation.path_traversal_detected", "zh")
        )
    
    return value


# 类型别名
SafeString = Annotated[str, BeforeValidator(safe_string_validator)]
SafePath = Annotated[str, BeforeValidator(safe_path_validator)]


# ============================================================================
# 通用验证模型
# ============================================================================

class SecureBaseModel(BaseModel):
    """
    安全基础模型
    
    所有需要安全验证的模型应继承此类
    """
    
    class Config:
        str_strip_whitespace = True
        str_max_length = 10000
        validate_assignment = True
    
    @model_validator(mode='before')
    @classmethod
    def validate_all_strings(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """验证所有字符串字段"""
        if not isinstance(values, dict):
            return values
        
        for key, value in values.items():
            if isinstance(value, str):
                # 检测 XSS
                if detect_xss(value):
                    raise ValueError(
                        get_translation(
                            "security.validation.xss_detected", "zh"
                        )
                    )
                # 检测 SQL 注入
                if detect_sql_injection(value):
                    raise ValueError(
                        get_translation(
                            "security.validation.sql_injection_detected", "zh"
                        )
                    )
        
        return values


class EmailField(BaseModel):
    """邮箱字段验证模型"""
    email: str
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        if not validate_email(v):
            raise ValueError(
                get_translation("security.validation.invalid_email", "zh")
            )
        return v.lower()


class PhoneField(BaseModel):
    """电话字段验证模型"""
    phone: str
    
    @field_validator('phone')
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        # 移除空格和连字符
        cleaned = re.sub(r'[\s-]', '', v)
        if not validate_phone(cleaned):
            raise ValueError(
                get_translation("security.validation.invalid_phone", "zh")
            )
        return cleaned


class URLField(BaseModel):
    """URL 字段验证模型"""
    url: str
    
    @field_validator('url')
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        if not validate_url(v):
            raise ValueError(
                get_translation("security.validation.invalid_url", "zh")
            )
        return v


class UUIDField(BaseModel):
    """UUID 字段验证模型"""
    uuid: str
    
    @field_validator('uuid')
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        if not validate_uuid(v):
            raise ValueError(
                get_translation("security.validation.invalid_uuid", "zh")
            )
        return v.lower()


class IPAddressField(BaseModel):
    """IP 地址字段验证模型"""
    ip_address: str
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip_format(cls, v: str) -> str:
        if not validate_ip_address(v):
            raise ValueError(
                get_translation("security.validation.invalid_ip", "zh")
            )
        return v


# ============================================================================
# 输入验证服务
# ============================================================================

class InputValidationService:
    """
    输入验证服务
    
    提供统一的输入验证接口
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_and_sanitize(
        self,
        value: str,
        field_name: str = "input",
        max_length: Optional[int] = None,
        min_length: Optional[int] = None,
        pattern: Optional[Pattern] = None,
        allow_html: bool = False,
        check_xss: bool = True,
        check_sql_injection: bool = True,
        check_path_traversal: bool = False
    ) -> str:
        """
        验证并清理输入
        
        Args:
            value: 输入值
            field_name: 字段名称（用于错误消息）
            max_length: 最大长度
            min_length: 最小长度
            pattern: 正则表达式模式
            allow_html: 是否允许 HTML
            check_xss: 是否检查 XSS
            check_sql_injection: 是否检查 SQL 注入
            check_path_traversal: 是否检查路径遍历
            
        Returns:
            清理后的值
            
        Raises:
            ValidationError: 验证失败时抛出
        """
        if value is None:
            raise ValidationError(
                get_translation(
                    "security.validation.field_required",
                    "zh",
                    field=field_name
                ),
                field_name
            )
        
        # 长度检查
        if max_length and len(value) > max_length:
            raise ValidationError(
                get_translation(
                    "security.validation.field_too_long",
                    "zh",
                    field=field_name,
                    max_length=max_length
                ),
                field_name
            )
        
        if min_length and len(value) < min_length:
            raise ValidationError(
                get_translation(
                    "security.validation.field_too_short",
                    "zh",
                    field=field_name,
                    min_length=min_length
                ),
                field_name
            )
        
        # 安全检查
        if check_xss and detect_xss(value):
            raise XSSDetectedError(
                get_translation("security.validation.xss_detected", "zh"),
                field_name
            )
        
        if check_sql_injection and detect_sql_injection(value):
            raise SQLInjectionDetectedError(
                get_translation("security.validation.sql_injection_detected", "zh"),
                field_name
            )
        
        if check_path_traversal and detect_path_traversal(value):
            raise PathTraversalDetectedError(
                get_translation("security.validation.path_traversal_detected", "zh"),
                field_name
            )
        
        # 模式匹配
        if pattern and not pattern.match(value):
            raise ValidationError(
                get_translation(
                    "security.validation.field_invalid_pattern",
                    "zh",
                    field=field_name
                ),
                field_name
            )
        
        # 清理
        if not allow_html:
            value = sanitize_string(value, max_length or 10000)
        
        return value
    
    def validate_email(self, value: str) -> str:
        """验证邮箱"""
        if not validate_email(value):
            raise ValidationError(
                get_translation("security.validation.invalid_email", "zh"),
                "email"
            )
        return value.lower()
    
    def validate_phone(self, value: str) -> str:
        """验证电话"""
        cleaned = re.sub(r'[\s-]', '', value)
        if not validate_phone(cleaned):
            raise ValidationError(
                get_translation("security.validation.invalid_phone", "zh"),
                "phone"
            )
        return cleaned
    
    def validate_url(self, value: str) -> str:
        """验证 URL"""
        if not validate_url(value):
            raise ValidationError(
                get_translation("security.validation.invalid_url", "zh"),
                "url"
            )
        return value
    
    def validate_uuid(self, value: str) -> str:
        """验证 UUID"""
        if not validate_uuid(value):
            raise ValidationError(
                get_translation("security.validation.invalid_uuid", "zh"),
                "uuid"
            )
        return value.lower()
    
    def validate_ip_address(self, value: str) -> str:
        """验证 IP 地址"""
        if not validate_ip_address(value):
            raise ValidationError(
                get_translation("security.validation.invalid_ip", "zh"),
                "ip_address"
            )
        return value


# 全局实例
_validation_service: Optional[InputValidationService] = None


def get_validation_service() -> InputValidationService:
    """获取验证服务实例"""
    global _validation_service
    if _validation_service is None:
        _validation_service = InputValidationService()
    return _validation_service
