"""
Property-Based Tests for Error Handling and Logging.

Tests the correctness properties of the error handling and logging system:
- Property 21: Structured log format
- Property 22: API error response standardization

Validates: Requirements 10.1, 10.2, 10.5
"""

import json
import logging
import re
import time
from datetime import datetime
from io import StringIO
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st, assume
from pydantic import ValidationError

# Import the modules under test
from src.utils.error_response import (
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
)
from src.utils.correlation_middleware import (
    CorrelationIdFilter,
    generate_correlation_id,
    generate_request_id,
    get_correlation_id,
    set_correlation_id,
)
from src.utils.logging_config import (
    StructuredLogFormatter,
    LoggingConfig,
    configure_logging,
    get_logger,
    log_with_context,
    log_error_with_traceback,
)


# =============================================================================
# Test Strategies
# =============================================================================

# Strategy for generating valid error codes
error_code_strategy = st.sampled_from([e.value for e in ErrorCode])

# Strategy for generating request IDs
request_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=5,
    max_size=50
).map(lambda s: f"req_{s}")

# Strategy for generating correlation IDs
correlation_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=5,
    max_size=50
).map(lambda s: f"corr_{s}")

# Strategy for generating error messages
message_strategy = st.text(min_size=1, max_size=500).filter(lambda s: s.strip())

# Strategy for generating log levels
log_level_strategy = st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

# Strategy for generating module names
module_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L",), whitelist_characters="._"),
    min_size=3,
    max_size=50
).filter(lambda s: s and not s.startswith(".") and not s.endswith("."))

# Strategy for generating extra log fields
extra_fields_strategy = st.dictionaries(
    keys=st.text(alphabet=st.characters(whitelist_categories=("L",)), min_size=1, max_size=20),
    values=st.one_of(
        st.text(max_size=100),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
    ),
    max_size=5
)

# Strategy for validation error details
validation_error_strategy = st.builds(
    ValidationErrorDetail,
    field=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    message=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    value=st.one_of(st.none(), st.text(max_size=50), st.integers()),
    constraint=st.one_of(st.none(), st.text(min_size=1, max_size=50))
)


# =============================================================================
# Property 21: Structured Log Format
# =============================================================================

class TestStructuredLogFormatProperty:
    """
    Property 21: 结构化日志格式
    
    *对于任意*日志记录，应该包含时间戳、级别、模块名、关联 ID（如果在请求上下文中）和消息。
    
    **Validates: Requirements 10.1, 10.2**
    """
    
    @given(
        level=log_level_strategy,
        message=message_strategy,
        module_name=module_name_strategy,
        correlation_id=st.one_of(st.none(), correlation_id_strategy),
        extra_fields=extra_fields_strategy
    )
    @settings(max_examples=100, deadline=None)
    def test_structured_log_contains_required_fields(
        self,
        level: str,
        message: str,
        module_name: str,
        correlation_id: Optional[str],
        extra_fields: Dict[str, Any]
    ):
        """
        Property: All log records contain required fields.
        
        **Validates: Requirements 10.1, 10.2**
        """
        # Assume valid inputs
        assume(message.strip())
        assume(module_name.strip())
        
        # Set correlation ID in context if provided
        if correlation_id:
            set_correlation_id(correlation_id)
        else:
            set_correlation_id(None)
        
        # Create formatter with JSON output for easy parsing
        formatter = StructuredLogFormatter(
            include_extra=True,
            include_traceback=True,
            json_output=True
        )
        
        # Create a log record
        record = logging.LogRecord(
            name=module_name,
            level=getattr(logging, level),
            pathname=f"{module_name.replace('.', '/')}.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        for key, value in extra_fields.items():
            setattr(record, key, value)
        
        # Apply correlation filter
        correlation_filter = CorrelationIdFilter()
        correlation_filter.filter(record)
        
        # Format the record
        formatted = formatter.format(record)
        
        # Parse the JSON output
        log_data = json.loads(formatted)
        
        # Property: Log must contain timestamp
        assert "timestamp" in log_data, "Log must contain timestamp"
        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(log_data["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {log_data['timestamp']}")
        
        # Property: Log must contain level
        assert "level" in log_data, "Log must contain level"
        assert log_data["level"] == level, f"Level mismatch: {log_data['level']} != {level}"
        
        # Property: Log must contain logger/module name
        assert "logger" in log_data, "Log must contain logger name"
        assert log_data["logger"] == module_name
        
        # Property: Log must contain correlation ID
        assert "correlation_id" in log_data, "Log must contain correlation_id"
        if correlation_id:
            assert log_data["correlation_id"] == correlation_id
        else:
            assert log_data["correlation_id"] == "-"
        
        # Property: Log must contain message
        assert "message" in log_data, "Log must contain message"
        assert log_data["message"] == message
    
    @given(
        message=message_strategy,
        exception_type=st.sampled_from([ValueError, TypeError, RuntimeError]),
        exception_message=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
            min_size=1,
            max_size=100
        ).filter(lambda s: s.strip() and s.isprintable())
    )
    @settings(max_examples=50, deadline=None)
    def test_error_log_contains_traceback(
        self,
        message: str,
        exception_type: type,
        exception_message: str
    ):
        """
        Property: Error logs with exceptions contain full traceback.
        
        **Validates: Requirements 10.3**
        """
        assume(message.strip())
        assume(exception_message.strip())
        
        # Create formatter with JSON output
        formatter = StructuredLogFormatter(
            include_extra=True,
            include_traceback=True,
            json_output=True
        )
        
        # Create an exception
        try:
            raise exception_type(exception_message)
        except Exception:
            import sys
            exc_info = sys.exc_info()
        
        # Create a log record with exception
        record = logging.LogRecord(
            name="test.module",
            level=logging.ERROR,
            pathname="test/module.py",
            lineno=100,
            msg=message,
            args=(),
            exc_info=exc_info
        )
        
        # Apply correlation filter
        correlation_filter = CorrelationIdFilter()
        correlation_filter.filter(record)
        
        # Format the record
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        # Property: Error log must contain exception info
        assert "exception" in log_data, "Error log must contain exception info"
        assert "type" in log_data["exception"], "Exception must have type"
        assert "message" in log_data["exception"], "Exception must have message"
        assert "traceback" in log_data["exception"], "Exception must have traceback"
        
        # Verify exception details
        assert log_data["exception"]["type"] == exception_type.__name__
        # The exception message should be present (may be wrapped for some exception types)
        assert log_data["exception"]["message"] is not None
        assert len(log_data["exception"]["message"]) > 0
        assert "Traceback" in log_data["exception"]["traceback"]
    
    @given(
        level=log_level_strategy,
        message=message_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_log_level_classification(self, level: str, message: str):
        """
        Property: Logs are correctly classified by severity.
        
        **Validates: Requirements 10.4**
        """
        assume(message.strip())
        
        # Create formatter
        formatter = StructuredLogFormatter(json_output=True)
        
        # Create log record
        record = logging.LogRecord(
            name="test.module",
            level=getattr(logging, level),
            pathname="test/module.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None
        )
        
        # Apply correlation filter
        CorrelationIdFilter().filter(record)
        
        # Format and parse
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        # Property: Level must match
        assert log_data["level"] == level
        
        # Property: Level must be one of the standard levels
        assert log_data["level"] in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


# =============================================================================
# Property 22: API Error Response Standardization
# =============================================================================

class TestAPIErrorResponseProperty:
    """
    Property 22: API 错误响应标准化
    
    *对于任意* API 端点的未处理异常，应该返回包含 error_code、message 和 request_id 的标准化 JSON 响应。
    
    **Validates: Requirements 10.5**
    """
    
    @given(
        error_code=error_code_strategy,
        request_id=request_id_strategy,
        message=st.one_of(st.none(), message_strategy),
        details=st.one_of(st.none(), st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(max_size=50),
            max_size=3
        ))
    )
    @settings(max_examples=100, deadline=None)
    def test_error_response_contains_required_fields(
        self,
        error_code: str,
        request_id: str,
        message: Optional[str],
        details: Optional[Dict[str, Any]]
    ):
        """
        Property: All error responses contain required fields.
        
        **Validates: Requirements 10.5**
        """
        # Create error response
        response = create_error_response(
            error_code=error_code,
            request_id=request_id,
            message=message,
            details=details
        )
        
        # Property: Response must have success=False
        assert response.success is False, "Error response must have success=False"
        
        # Property: Response must have error_code
        assert response.error_code is not None, "Response must have error_code"
        assert response.error_code == error_code
        
        # Property: Response must have message
        assert response.message is not None, "Response must have message"
        assert len(response.message) > 0, "Message must not be empty"
        
        # Property: Response must have request_id
        assert response.request_id is not None, "Response must have request_id"
        assert response.request_id == request_id
        
        # Property: Response must have timestamp
        assert response.timestamp is not None, "Response must have timestamp"
        assert isinstance(response.timestamp, datetime)
        
        # Property: Details should match if provided
        if details:
            assert response.details == details
    
    @given(
        error_code=error_code_strategy,
        request_id=request_id_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_error_code_maps_to_correct_http_status(
        self,
        error_code: str,
        request_id: str
    ):
        """
        Property: Error codes map to correct HTTP status codes.
        
        **Validates: Requirements 10.5**
        """
        # Get HTTP status for error code
        status_code = get_http_status_for_error_code(error_code)
        
        # Property: Status code must be valid HTTP error code
        assert 400 <= status_code <= 599, f"Invalid HTTP status: {status_code}"
        
        # Property: Status code must match expected mapping
        expected_status = ERROR_CODE_TO_STATUS.get(error_code, 500)
        assert status_code == expected_status
        
        # Property: Error code prefix should match status code range
        if error_code.startswith("VAL_"):
            assert status_code == 400
        elif error_code.startswith("AUTH_"):
            assert status_code == 401
        elif error_code.startswith("PERM_"):
            assert status_code == 403
        elif error_code.startswith("NOT_FOUND_"):
            assert status_code == 404
        elif error_code.startswith("CONFLICT_"):
            assert status_code == 409
        elif error_code.startswith("RATE_LIMIT_"):
            assert status_code == 429
        elif error_code.startswith("INTERNAL_"):
            assert status_code == 500
        elif error_code.startswith("SERVICE_"):
            assert status_code == 503
    
    @given(
        request_id=request_id_strategy,
        validation_errors=st.lists(validation_error_strategy, min_size=1, max_size=5)
    )
    @settings(max_examples=50, deadline=None)
    def test_validation_error_response_contains_field_details(
        self,
        request_id: str,
        validation_errors: list
    ):
        """
        Property: Validation error responses contain field-level details.
        
        **Validates: Requirements 10.5**
        """
        # Create validation error response
        response = create_validation_error_response(
            request_id=request_id,
            validation_errors=validation_errors
        )
        
        # Property: Response must be ValidationErrorResponse
        assert isinstance(response, ValidationErrorResponse)
        
        # Property: Response must have validation_errors
        assert response.validation_errors is not None
        assert len(response.validation_errors) == len(validation_errors)
        
        # Property: Each validation error must have field and message
        for error in response.validation_errors:
            assert error.field is not None
            assert len(error.field) > 0
            assert error.message is not None
            assert len(error.message) > 0
        
        # Property: Error code must be VAL_INVALID_INPUT
        assert response.error_code == ErrorCode.VAL_INVALID_INPUT.value
    
    @given(
        error_code=error_code_strategy,
        request_id=request_id_strategy
    )
    @settings(max_examples=50, deadline=None)
    def test_error_response_serializes_to_valid_json(
        self,
        error_code: str,
        request_id: str
    ):
        """
        Property: Error responses serialize to valid JSON.
        
        **Validates: Requirements 10.5**
        """
        # Create error response
        response = create_error_response(
            error_code=error_code,
            request_id=request_id
        )
        
        # Serialize to JSON
        json_data = response.model_dump(mode="json")
        
        # Property: Must be valid JSON
        json_str = json.dumps(json_data)
        parsed = json.loads(json_str)
        
        # Property: Parsed JSON must contain required fields
        assert "success" in parsed
        assert "error_code" in parsed
        assert "message" in parsed
        assert "request_id" in parsed
        assert "timestamp" in parsed
        
        # Property: Values must match
        assert parsed["success"] is False
        assert parsed["error_code"] == error_code
        assert parsed["request_id"] == request_id
    
    @given(error_code=error_code_strategy)
    @settings(max_examples=50, deadline=None)
    def test_error_message_is_localized(self, error_code: str):
        """
        Property: Error messages are localized (have i18n support).
        
        **Validates: Requirements 10.5**
        """
        # Get error message
        message = get_error_message(error_code)
        
        # Property: Message must not be empty
        assert message is not None
        assert len(message) > 0
        
        # Property: Message should not be the raw error code
        assert message != error_code


# =============================================================================
# Additional Property Tests
# =============================================================================

class TestCorrelationIdProperties:
    """Tests for correlation ID generation and propagation."""
    
    @given(st.integers(min_value=1, max_value=1000))
    @settings(max_examples=50, deadline=None)
    def test_correlation_id_uniqueness(self, count: int):
        """
        Property: Generated correlation IDs are unique.
        """
        ids = set()
        for _ in range(count):
            corr_id = generate_correlation_id()
            assert corr_id not in ids, "Correlation IDs must be unique"
            ids.add(corr_id)
            # Small delay to ensure timestamp difference
            time.sleep(0.001)
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20, deadline=None)
    def test_request_id_uniqueness(self, count: int):
        """
        Property: Generated request IDs are unique.
        """
        ids = set()
        for _ in range(count):
            req_id = generate_request_id()
            assert req_id not in ids, "Request IDs must be unique"
            ids.add(req_id)
            # Small delay to ensure timestamp difference
            time.sleep(0.000001)  # 1 microsecond
    
    def test_correlation_id_format(self):
        """
        Property: Correlation IDs follow expected format.
        """
        for _ in range(10):
            corr_id = generate_correlation_id()
            # Should start with "corr_"
            assert corr_id.startswith("corr_")
            # Should contain timestamp and unique part
            parts = corr_id.split("_")
            assert len(parts) >= 3
            time.sleep(0.001)
    
    def test_request_id_format(self):
        """
        Property: Request IDs follow expected format.
        """
        for _ in range(10):
            req_id = generate_request_id()
            # Should start with "req_"
            assert req_id.startswith("req_")
            # Should contain timestamp
            parts = req_id.split("_")
            assert len(parts) >= 2


class TestErrorCodeEnumProperties:
    """Tests for error code enumeration properties."""
    
    def test_all_error_codes_have_http_status(self):
        """
        Property: All error codes have a mapped HTTP status.
        """
        for error_code in ErrorCode:
            status = get_http_status_for_error_code(error_code.value)
            assert status is not None
            assert 400 <= status <= 599
    
    def test_error_code_prefix_consistency(self):
        """
        Property: Error codes follow prefix naming convention.
        """
        prefix_to_codes = {}
        for error_code in ErrorCode:
            # Extract prefix (everything before the last underscore segment)
            parts = error_code.value.split("_")
            if len(parts) >= 2:
                prefix = parts[0]
                if prefix not in prefix_to_codes:
                    prefix_to_codes[prefix] = []
                prefix_to_codes[prefix].append(error_code.value)
        
        # Verify each prefix maps to consistent HTTP status range
        prefix_to_status_range = {
            "VAL": (400, 400),
            "AUTH": (401, 401),
            "PERM": (403, 403),
            "NOT": (404, 404),  # NOT_FOUND
            "CONFLICT": (409, 409),
            "RATE": (429, 429),  # RATE_LIMIT
            "INTERNAL": (500, 500),
            "SERVICE": (503, 503),
        }
        
        for prefix, codes in prefix_to_codes.items():
            if prefix in prefix_to_status_range:
                expected_min, expected_max = prefix_to_status_range[prefix]
                for code in codes:
                    status = get_http_status_for_error_code(code)
                    assert expected_min <= status <= expected_max, \
                        f"Code {code} has status {status}, expected {expected_min}-{expected_max}"


# =============================================================================
# Integration Tests
# =============================================================================

class TestLoggingIntegration:
    """Integration tests for the logging system."""
    
    def test_configure_logging_creates_valid_config(self):
        """Test that configure_logging creates a valid configuration."""
        config = configure_logging(
            log_level="DEBUG",
            json_output=False
        )
        
        assert config is not None
        assert config.log_level == "DEBUG"
        assert config.json_output is False
    
    def test_get_logger_returns_configured_logger(self):
        """Test that get_logger returns a properly configured logger."""
        logger = get_logger("test.module")
        
        assert logger is not None
        assert logger.name == "test.module"
        
        # Should have correlation filter
        has_correlation_filter = any(
            isinstance(f, CorrelationIdFilter) for f in logger.filters
        )
        assert has_correlation_filter


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
