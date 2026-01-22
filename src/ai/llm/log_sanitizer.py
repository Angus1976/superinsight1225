"""
Log Sanitizer for LLM Integration module.

Provides functionality to remove sensitive data from logs including:
- API keys (sk-*, api_key=*, etc.)
- Passwords
- Email addresses
- Phone numbers
- Credit card numbers

This module ensures that sensitive information is never logged,
maintaining compliance with security requirements.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SanitizationPattern:
    """Defines a pattern for sanitizing sensitive data."""
    name: str
    pattern: re.Pattern
    replacement: str = "[REDACTED]"
    description: str = ""


@dataclass
class SanitizationResult:
    """Result of a sanitization operation."""
    sanitized: Union[str, Dict[str, Any]]
    patterns_matched: List[str] = field(default_factory=list)
    redaction_count: int = 0


class LogSanitizer:
    """
    Sanitizes log entries by removing sensitive data.
    
    Supports both string logs and dictionary logs, removing:
    - API keys (various formats)
    - Passwords
    - Email addresses
    - Phone numbers
    - Credit card numbers
    - Other PII patterns
    
    Example usage:
        sanitizer = LogSanitizer()
        
        # Sanitize a string
        safe_log = sanitizer.sanitize_string("API key: sk-abc123xyz")
        # Result: "API key: [REDACTED_API_KEY]"
        
        # Sanitize a dict
        safe_dict = sanitizer.sanitize_dict({"api_key": "sk-abc123", "user": "john"})
        # Result: {"api_key": "[REDACTED_API_KEY]", "user": "john"}
    """
    
    # Default patterns for sensitive data
    DEFAULT_PATTERNS: List[SanitizationPattern] = [
        # API Keys - OpenAI style (sk-...)
        SanitizationPattern(
            name="openai_api_key",
            pattern=re.compile(r'\bsk-[a-zA-Z0-9]{20,}', re.IGNORECASE),
            replacement="[REDACTED_API_KEY]",
            description="OpenAI-style API keys starting with sk-"
        ),
        # API Keys - Generic patterns (handles JSON format with quotes)
        SanitizationPattern(
            name="api_key_param_json",
            pattern=re.compile(r'(["\']api[_-]?key["\']\s*:\s*)["\']([^"\']+)["\']', re.IGNORECASE),
            replacement=r'\1"[REDACTED_API_KEY]"',
            description="API key parameters in JSON format"
        ),
        # API Keys - Generic patterns (handles key=value format)
        SanitizationPattern(
            name="api_key_param",
            pattern=re.compile(r'(api[_-]?key\s*=\s*)([^\s,;]+)', re.IGNORECASE),
            replacement=r'\1[REDACTED_API_KEY]',
            description="API key parameters in key=value format"
        ),
        # API Keys - Generic patterns (handles key: value format)
        SanitizationPattern(
            name="api_key_param_colon",
            pattern=re.compile(r'(api[_-]?key\s*:\s*)([^\s,;]+)', re.IGNORECASE),
            replacement=r'\1[REDACTED_API_KEY]',
            description="API key parameters in key: value format"
        ),
        # API Keys - Bearer tokens
        SanitizationPattern(
            name="bearer_token",
            pattern=re.compile(r'(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}', re.IGNORECASE),
            replacement=r'\1[REDACTED_TOKEN]',
            description="Bearer authentication tokens"
        ),
        # API Keys - Authorization headers
        SanitizationPattern(
            name="auth_header",
            pattern=re.compile(r'(Authorization\s*[=:]\s*)["\']?[a-zA-Z0-9_\-\.\s]{20,}["\']?', re.IGNORECASE),
            replacement=r'\1[REDACTED_AUTH]',
            description="Authorization header values"
        ),
        # Secret keys (JSON format)
        SanitizationPattern(
            name="secret_key_json",
            pattern=re.compile(r'(["\']secret[_-]?key["\']\s*:\s*)["\']([^"\']+)["\']', re.IGNORECASE),
            replacement=r'\1"[REDACTED_SECRET]"',
            description="Secret key parameters in JSON format"
        ),
        # Secret keys (key=value format)
        SanitizationPattern(
            name="secret_key",
            pattern=re.compile(r'(secret[_-]?key\s*[=:]\s*)([^\s,;]+)', re.IGNORECASE),
            replacement=r'\1[REDACTED_SECRET]',
            description="Secret key parameters"
        ),
        # Passwords (JSON format)
        SanitizationPattern(
            name="password_json",
            pattern=re.compile(r'(["\']password["\']\s*:\s*)["\']([^"\']*)["\']', re.IGNORECASE),
            replacement=r'\1"[REDACTED_PASSWORD]"',
            description="Password fields in JSON format"
        ),
        # Passwords (key=value format) - match anything after = until whitespace/comma/semicolon/end
        SanitizationPattern(
            name="password",
            pattern=re.compile(r'(password\s*=\s*)(\S+)', re.IGNORECASE),
            replacement=r'\1[REDACTED_PASSWORD]',
            description="Password fields in key=value format"
        ),
        # Passwords (key: value format) - match anything after : until whitespace/comma/semicolon/end
        SanitizationPattern(
            name="password_colon",
            pattern=re.compile(r'(password\s*:\s*)(\S+)', re.IGNORECASE),
            replacement=r'\1[REDACTED_PASSWORD]',
            description="Password fields in key: value format"
        ),
        # Email addresses
        SanitizationPattern(
            name="email",
            pattern=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            replacement="[REDACTED_EMAIL]",
            description="Email addresses"
        ),
        # Phone numbers (various formats)
        SanitizationPattern(
            name="phone_us",
            pattern=re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            replacement="[REDACTED_PHONE]",
            description="US phone numbers"
        ),
        SanitizationPattern(
            name="phone_intl",
            pattern=re.compile(r'\b\+[0-9]{1,3}[-.\s]?[0-9]{6,14}\b'),
            replacement="[REDACTED_PHONE]",
            description="International phone numbers"
        ),
        # Credit card numbers (basic patterns)
        SanitizationPattern(
            name="credit_card",
            pattern=re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'),
            replacement="[REDACTED_CC]",
            description="Credit card numbers (Visa, MC, Amex, Discover)"
        ),
        SanitizationPattern(
            name="credit_card_formatted",
            pattern=re.compile(r'\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b'),
            replacement="[REDACTED_CC]",
            description="Formatted credit card numbers"
        ),
        # SSN (US Social Security Numbers)
        SanitizationPattern(
            name="ssn",
            pattern=re.compile(r'\b[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{4}\b'),
            replacement="[REDACTED_SSN]",
            description="US Social Security Numbers"
        ),
        # Chinese ID numbers
        SanitizationPattern(
            name="chinese_id",
            pattern=re.compile(r'\b[1-9][0-9]{5}(?:19|20)[0-9]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01])[0-9]{3}[0-9Xx]\b'),
            replacement="[REDACTED_ID]",
            description="Chinese ID card numbers"
        ),
        # AWS Access Keys
        SanitizationPattern(
            name="aws_access_key",
            pattern=re.compile(r'\b(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}\b'),
            replacement="[REDACTED_AWS_KEY]",
            description="AWS Access Key IDs"
        ),
        # Generic long alphanumeric tokens (likely API keys)
        SanitizationPattern(
            name="generic_token",
            pattern=re.compile(r'(token\s*[=:]\s*)["\']?([a-zA-Z0-9_\-]{32,})["\']?', re.IGNORECASE),
            replacement=r'\1[REDACTED_TOKEN]',
            description="Generic tokens"
        ),
    ]
    
    # Keys that should always be redacted in dictionaries
    SENSITIVE_KEYS = {
        'api_key', 'apikey', 'api-key',
        'secret', 'secret_key', 'secretkey', 'secret-key',
        'password', 'passwd', 'pwd',
        'token', 'access_token', 'refresh_token', 'auth_token',
        'authorization', 'auth',
        'credential', 'credentials',
        'private_key', 'privatekey', 'private-key',
        'openai_api_key', 'azure_api_key',
        'qwen_api_key', 'zhipu_api_key', 'baidu_api_key', 'baidu_secret_key',
        'hunyuan_secret_id', 'hunyuan_secret_key',
    }
    
    def __init__(
        self,
        patterns: Optional[List[SanitizationPattern]] = None,
        sensitive_keys: Optional[set] = None,
        custom_replacement: str = "[REDACTED]"
    ):
        """
        Initialize the log sanitizer.
        
        Args:
            patterns: Custom sanitization patterns (uses defaults if None)
            sensitive_keys: Custom set of sensitive dictionary keys
            custom_replacement: Default replacement string for sensitive keys
        """
        self.patterns = patterns or self.DEFAULT_PATTERNS.copy()
        self.sensitive_keys = sensitive_keys or self.SENSITIVE_KEYS.copy()
        self.custom_replacement = custom_replacement
    
    def add_pattern(self, pattern: SanitizationPattern) -> None:
        """Add a custom sanitization pattern."""
        self.patterns.append(pattern)
    
    def add_sensitive_key(self, key: str) -> None:
        """Add a key to the sensitive keys set."""
        self.sensitive_keys.add(key.lower())
    
    def sanitize_string(self, text: str) -> SanitizationResult:
        """
        Sanitize a string by removing sensitive data.
        
        Args:
            text: The string to sanitize
            
        Returns:
            SanitizationResult with sanitized string and metadata
        """
        if not text:
            return SanitizationResult(sanitized="", patterns_matched=[], redaction_count=0)
        
        sanitized = text
        patterns_matched = []
        redaction_count = 0
        
        for pattern in self.patterns:
            matches = pattern.pattern.findall(sanitized)
            if matches:
                patterns_matched.append(pattern.name)
                redaction_count += len(matches) if isinstance(matches[0], str) else len(matches)
                sanitized = pattern.pattern.sub(pattern.replacement, sanitized)
        
        return SanitizationResult(
            sanitized=sanitized,
            patterns_matched=patterns_matched,
            redaction_count=redaction_count
        )
    
    def sanitize_dict(
        self,
        data: Dict[str, Any],
        recursive: bool = True
    ) -> SanitizationResult:
        """
        Sanitize a dictionary by removing sensitive data.
        
        Args:
            data: The dictionary to sanitize
            recursive: Whether to recursively sanitize nested dicts
            
        Returns:
            SanitizationResult with sanitized dictionary and metadata
        """
        if not data:
            return SanitizationResult(sanitized={}, patterns_matched=[], redaction_count=0)
        
        sanitized = {}
        patterns_matched = []
        redaction_count = 0
        
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key is sensitive
            if key_lower in self.sensitive_keys:
                sanitized[key] = self.custom_replacement
                patterns_matched.append(f"sensitive_key:{key}")
                redaction_count += 1
                continue
            
            # Handle nested dictionaries
            if isinstance(value, dict) and recursive:
                nested_result = self.sanitize_dict(value, recursive=True)
                sanitized[key] = nested_result.sanitized
                patterns_matched.extend(nested_result.patterns_matched)
                redaction_count += nested_result.redaction_count
                
            # Handle lists
            elif isinstance(value, list):
                sanitized_list = []
                for item in value:
                    if isinstance(item, dict) and recursive:
                        nested_result = self.sanitize_dict(item, recursive=True)
                        sanitized_list.append(nested_result.sanitized)
                        patterns_matched.extend(nested_result.patterns_matched)
                        redaction_count += nested_result.redaction_count
                    elif isinstance(item, str):
                        str_result = self.sanitize_string(item)
                        sanitized_list.append(str_result.sanitized)
                        patterns_matched.extend(str_result.patterns_matched)
                        redaction_count += str_result.redaction_count
                    else:
                        sanitized_list.append(item)
                sanitized[key] = sanitized_list
                
            # Handle string values
            elif isinstance(value, str):
                str_result = self.sanitize_string(value)
                sanitized[key] = str_result.sanitized
                patterns_matched.extend(str_result.patterns_matched)
                redaction_count += str_result.redaction_count
                
            # Pass through other types unchanged
            else:
                sanitized[key] = value
        
        return SanitizationResult(
            sanitized=sanitized,
            patterns_matched=list(set(patterns_matched)),  # Deduplicate
            redaction_count=redaction_count
        )
    
    def sanitize(self, data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """
        Sanitize data (string or dict) and return only the sanitized result.
        
        This is a convenience method that returns just the sanitized data
        without the metadata.
        
        Args:
            data: String or dictionary to sanitize
            
        Returns:
            Sanitized string or dictionary
        """
        if isinstance(data, str):
            return self.sanitize_string(data).sanitized
        elif isinstance(data, dict):
            return self.sanitize_dict(data).sanitized
        else:
            return data
    
    def sanitize_for_logging(
        self,
        data: Union[str, Dict[str, Any]],
        max_length: int = 1000
    ) -> str:
        """
        Sanitize data and format it for logging.
        
        Args:
            data: Data to sanitize
            max_length: Maximum length of the output string
            
        Returns:
            Sanitized string suitable for logging
        """
        sanitized = self.sanitize(data)
        
        if isinstance(sanitized, dict):
            try:
                result = json.dumps(sanitized, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                result = str(sanitized)
        else:
            result = str(sanitized)
        
        # Truncate if too long
        if len(result) > max_length:
            result = result[:max_length - 3] + "..."
        
        return result


# Global sanitizer instance for convenience
_default_sanitizer: Optional[LogSanitizer] = None


def get_sanitizer() -> LogSanitizer:
    """Get or create the default log sanitizer instance."""
    global _default_sanitizer
    if _default_sanitizer is None:
        _default_sanitizer = LogSanitizer()
    return _default_sanitizer


def sanitize_log(data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
    """
    Convenience function to sanitize log data using the default sanitizer.
    
    Args:
        data: String or dictionary to sanitize
        
    Returns:
        Sanitized data
    """
    return get_sanitizer().sanitize(data)


def sanitize_for_audit(
    data: Dict[str, Any],
    include_metadata: bool = False
) -> Dict[str, Any]:
    """
    Sanitize data specifically for audit logging.
    
    This function ensures that sensitive data is removed before
    being written to audit logs.
    
    Args:
        data: Dictionary to sanitize
        include_metadata: Whether to include sanitization metadata
        
    Returns:
        Sanitized dictionary, optionally with metadata
    """
    sanitizer = get_sanitizer()
    result = sanitizer.sanitize_dict(data)
    
    if include_metadata:
        return {
            "data": result.sanitized,
            "sanitization": {
                "patterns_matched": result.patterns_matched,
                "redaction_count": result.redaction_count
            }
        }
    
    return result.sanitized
