"""
Unit Tests for UX Optimizer Module

Tests API response formatting, error handling, pagination,
data formatting, and form validation.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from quality_billing.ux_optimizer import (
    # API Response
    ResponseStatus,
    ApiMeta,
    ApiError,
    ApiResponse,
    ResponseBuilder,
    # Error Handling
    ErrorCode,
    ErrorSuggestions,
    ErrorHandler,
    # Pagination
    PaginationParams,
    PaginationMeta,
    PaginatedResponse,
    Paginator,
    # Data Formatting
    DataFormatter,
    # User Preferences
    UserPreferences,
    PreferenceManager,
    # Help System
    HelpTopic,
    ContextualHelp,
    HelpSystem,
    # Form Validation
    ValidationRule,
    ValidationResult,
    FormValidator,
)


# ============================================================================
# API Response Tests
# ============================================================================


class TestApiError:
    """Tests for ApiError class"""

    def test_api_error_creation(self):
        """Test creating an API error"""
        error = ApiError(
            code="VALIDATION_FAILED",
            message="验证失败",
            details="字段格式错误",
            field="email"
        )

        assert error.code == "VALIDATION_FAILED"
        assert error.message == "验证失败"
        assert error.field == "email"

    def test_api_error_to_dict(self):
        """Test converting error to dictionary"""
        error = ApiError(
            code="NOT_FOUND",
            message="资源不存在",
            suggestion="请检查 ID"
        )

        result = error.to_dict()

        assert result["code"] == "NOT_FOUND"
        assert result["message"] == "资源不存在"
        assert result["suggestion"] == "请检查 ID"
        assert "details" not in result  # None values not included


class TestApiResponse:
    """Tests for ApiResponse class"""

    def test_success_response(self):
        """Test creating a success response"""
        response: ApiResponse[Dict] = ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={"id": 1, "name": "test"}
        )

        assert response.is_success
        assert not response.is_error
        assert response.data == {"id": 1, "name": "test"}

    def test_error_response(self):
        """Test creating an error response"""
        response: ApiResponse[None] = ApiResponse(
            status=ResponseStatus.ERROR,
            errors=[ApiError(code="ERROR", message="Something went wrong")]
        )

        assert response.is_error
        assert not response.is_success
        assert len(response.errors) == 1

    def test_response_to_dict(self):
        """Test converting response to dictionary"""
        meta = ApiMeta(
            request_id="req-123",
            timestamp="2025-01-01T00:00:00",
            processing_time_ms=50.5
        )

        response: ApiResponse[str] = ApiResponse(
            status=ResponseStatus.SUCCESS,
            data="test data",
            meta=meta
        )

        result = response.to_dict()

        assert result["status"] == "success"
        assert result["data"] == "test data"
        assert result["meta"]["request_id"] == "req-123"
        assert result["meta"]["processing_time_ms"] == 50.5

    def test_response_to_json(self):
        """Test converting response to JSON"""
        response: ApiResponse[Dict] = ApiResponse(
            status=ResponseStatus.SUCCESS,
            data={"key": "value"}
        )

        json_str = response.to_json()

        assert '"status": "success"' in json_str
        assert '"key": "value"' in json_str


class TestResponseBuilder:
    """Tests for ResponseBuilder class"""

    def test_build_success_response(self):
        """Test building a success response"""
        response = (
            ResponseBuilder[Dict]("req-001")
            .with_data({"name": "test"})
            .build()
        )

        assert response.status == ResponseStatus.SUCCESS
        assert response.data == {"name": "test"}
        assert response.meta is not None
        assert response.meta.request_id == "req-001"

    def test_build_error_response(self):
        """Test building an error response"""
        response = (
            ResponseBuilder[None]("req-002")
            .with_error(
                code="VALIDATION_FAILED",
                message="Invalid input",
                field="email"
            )
            .build()
        )

        assert response.status == ResponseStatus.ERROR
        assert len(response.errors) == 1
        assert response.errors[0].field == "email"

    def test_build_warning_response(self):
        """Test building a response with warnings"""
        response = (
            ResponseBuilder[str]("req-003")
            .with_data("success")
            .with_warning("Some field is deprecated")
            .build()
        )

        assert response.status == ResponseStatus.WARNING
        assert len(response.warnings) == 1

    def test_processing_time_calculated(self):
        """Test that processing time is calculated"""
        import time

        builder = ResponseBuilder[str]("req-004")
        time.sleep(0.01)  # 10ms
        response = builder.with_data("test").build()

        assert response.meta is not None
        assert response.meta.processing_time_ms >= 10


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorCode:
    """Tests for ErrorCode enum"""

    def test_error_code_properties(self):
        """Test error code has code and message"""
        error = ErrorCode.VALIDATION_FAILED

        assert error.code == "VALIDATION_FAILED"
        assert "验证" in error.message

    def test_all_error_codes_have_message(self):
        """Test all error codes have messages"""
        for error_code in ErrorCode:
            assert error_code.code is not None
            assert error_code.message is not None
            assert len(error_code.message) > 0


class TestErrorSuggestions:
    """Tests for ErrorSuggestions class"""

    def test_get_suggestion(self):
        """Test getting suggestion for error code"""
        suggestion = ErrorSuggestions.get_suggestion("VALIDATION_FAILED")

        assert suggestion is not None
        assert len(suggestion) > 0

    def test_unknown_code_returns_none(self):
        """Test unknown code returns None"""
        suggestion = ErrorSuggestions.get_suggestion("UNKNOWN_CODE")

        assert suggestion is None


class TestErrorHandler:
    """Tests for ErrorHandler class"""

    @pytest.fixture
    def handler(self) -> ErrorHandler:
        return ErrorHandler()

    def test_handle_value_error(self, handler):
        """Test handling ValueError"""
        error = handler.handle(ValueError("Invalid value"))

        assert error.code == "VALIDATION_FAILED"
        assert error.suggestion is not None

    def test_handle_key_error(self, handler):
        """Test handling KeyError"""
        error = handler.handle(KeyError("missing_key"))

        assert error.code == "MISSING_REQUIRED_FIELD"

    def test_handle_unknown_exception(self, handler):
        """Test handling unknown exception"""
        error = handler.handle(RuntimeError("Unknown error"))

        assert error.code == "INTERNAL_ERROR"

    def test_wrap_response(self, handler):
        """Test wrapping exception in response"""
        response = handler.wrap_response(
            ValueError("Test error"),
            request_id="req-123"
        )

        assert response.status == ResponseStatus.ERROR
        assert len(response.errors) == 1
        assert response.meta is not None
        assert response.meta.request_id == "req-123"

    def test_register_custom_handler(self, handler):
        """Test registering custom exception handler"""
        class CustomError(Exception):
            pass

        handler.register_handler(CustomError, ErrorCode.SERVICE_UNAVAILABLE)
        error = handler.handle(CustomError("Custom error"))

        assert error.code == "SERVICE_UNAVAILABLE"


# ============================================================================
# Pagination Tests
# ============================================================================


class TestPaginationParams:
    """Tests for PaginationParams class"""

    def test_default_params(self):
        """Test default pagination parameters"""
        params = PaginationParams()

        assert params.page == 1
        assert params.page_size == 20
        assert params.offset == 0
        assert params.limit == 20

    def test_custom_params(self):
        """Test custom pagination parameters"""
        params = PaginationParams(page=3, page_size=50)

        assert params.page == 3
        assert params.page_size == 50
        assert params.offset == 100
        assert params.limit == 50

    def test_page_size_capped(self):
        """Test page size is capped at 100"""
        params = PaginationParams(page_size=200)

        assert params.page_size == 100

    def test_negative_values_corrected(self):
        """Test negative values are corrected"""
        params = PaginationParams(page=-1, page_size=-10)

        assert params.page == 1
        assert params.page_size == 20

    def test_invalid_sort_order_corrected(self):
        """Test invalid sort order is corrected"""
        params = PaginationParams(sort_order="invalid")

        assert params.sort_order == "asc"


class TestPaginationMeta:
    """Tests for PaginationMeta class"""

    def test_from_params(self):
        """Test creating meta from params"""
        params = PaginationParams(page=2, page_size=10)
        meta = PaginationMeta.from_params(params, total_items=45)

        assert meta.page == 2
        assert meta.page_size == 10
        assert meta.total_items == 45
        assert meta.total_pages == 5
        assert meta.has_previous
        assert meta.has_next

    def test_first_page(self):
        """Test first page has no previous"""
        params = PaginationParams(page=1, page_size=10)
        meta = PaginationMeta.from_params(params, total_items=100)

        assert not meta.has_previous
        assert meta.has_next

    def test_last_page(self):
        """Test last page has no next"""
        params = PaginationParams(page=10, page_size=10)
        meta = PaginationMeta.from_params(params, total_items=100)

        assert meta.has_previous
        assert not meta.has_next

    def test_to_dict(self):
        """Test converting meta to dictionary"""
        params = PaginationParams(page=1, page_size=20)
        meta = PaginationMeta.from_params(params, total_items=50)

        result = meta.to_dict()

        assert result["page"] == 1
        assert result["total_items"] == 50
        assert result["total_pages"] == 3


class TestPaginator:
    """Tests for Paginator class"""

    def test_paginate_list(self):
        """Test paginating a list"""
        items = list(range(100))
        params = PaginationParams(page=2, page_size=20)
        paginator = Paginator(items, params)

        result = paginator.paginate()

        assert len(result.items) == 20
        assert result.items[0] == 20
        assert result.items[-1] == 39
        assert result.pagination.total_items == 100

    def test_paginate_empty_list(self):
        """Test paginating empty list"""
        items: List[int] = []
        params = PaginationParams()
        paginator = Paginator(items, params)

        result = paginator.paginate()

        assert len(result.items) == 0
        assert result.pagination.total_pages == 0

    def test_paginate_with_sort(self):
        """Test paginating with sort"""
        items = [{"name": "Bob"}, {"name": "Alice"}, {"name": "Charlie"}]
        params = PaginationParams(sort_by="name", sort_order="asc")
        paginator = Paginator(items, params)

        result = paginator.paginate()

        assert result.items[0]["name"] == "Alice"
        assert result.items[-1]["name"] == "Charlie"


# ============================================================================
# Data Formatter Tests
# ============================================================================


class TestDataFormatter:
    """Tests for DataFormatter class"""

    def test_format_currency_cny(self):
        """Test formatting CNY currency"""
        result = DataFormatter.format_currency(1234.56, "CNY")

        assert result == "¥1,234.56"

    def test_format_currency_usd(self):
        """Test formatting USD currency"""
        result = DataFormatter.format_currency(1234.56, "USD")

        assert result == "$1,234.56"

    def test_format_currency_jpy(self):
        """Test formatting JPY (no decimals)"""
        result = DataFormatter.format_currency(1234.56, "JPY")

        assert result == "¥1,234"

    def test_format_percentage(self):
        """Test formatting percentage"""
        result = DataFormatter.format_percentage(0.1234)

        assert result == "12.3%"

    def test_format_percentage_with_sign(self):
        """Test formatting percentage with sign"""
        result = DataFormatter.format_percentage(0.05, include_sign=True)

        assert result == "+5.0%"

    def test_format_number(self):
        """Test formatting number"""
        result = DataFormatter.format_number(1234567.89)

        assert result == "1,234,567.89"

    def test_format_number_integer(self):
        """Test formatting integer"""
        result = DataFormatter.format_number(1234567)

        assert result == "1,234,567"

    def test_format_file_size_bytes(self):
        """Test formatting bytes"""
        result = DataFormatter.format_file_size(500)

        assert result == "500 B"

    def test_format_file_size_kb(self):
        """Test formatting kilobytes"""
        result = DataFormatter.format_file_size(1536)

        assert result == "1.50 KB"

    def test_format_file_size_mb(self):
        """Test formatting megabytes"""
        result = DataFormatter.format_file_size(5 * 1024 * 1024)

        assert result == "5.00 MB"

    def test_format_duration_ms(self):
        """Test formatting milliseconds"""
        result = DataFormatter.format_duration(0.5)

        assert result == "500ms"

    def test_format_duration_seconds(self):
        """Test formatting seconds"""
        result = DataFormatter.format_duration(45.5)

        assert result == "45.5s"

    def test_format_duration_minutes(self):
        """Test formatting minutes"""
        result = DataFormatter.format_duration(125)

        assert result == "2m 5s"

    def test_format_duration_hours(self):
        """Test formatting hours"""
        result = DataFormatter.format_duration(3725)

        assert result == "1h 2m"

    def test_format_datetime_full(self):
        """Test formatting full datetime"""
        dt = datetime(2025, 1, 15, 10, 30, 45)
        result = DataFormatter.format_datetime(dt, "full")

        assert result == "2025-01-15 10:30:45"

    def test_format_datetime_date(self):
        """Test formatting date only"""
        dt = datetime(2025, 1, 15)
        result = DataFormatter.format_datetime(dt, "date")

        assert result == "2025-01-15"

    def test_format_datetime_relative_recent(self):
        """Test formatting relative time (recent)"""
        dt = datetime.now() - timedelta(seconds=30)
        result = DataFormatter.format_datetime(dt, "relative")

        assert result == "刚刚"

    def test_format_datetime_relative_minutes(self):
        """Test formatting relative time (minutes)"""
        dt = datetime.now() - timedelta(minutes=5)
        result = DataFormatter.format_datetime(dt, "relative")

        assert "分钟前" in result

    def test_truncate_text(self):
        """Test truncating text"""
        text = "This is a very long text that needs to be truncated"
        result = DataFormatter.truncate_text(text, max_length=20)

        assert len(result) == 20
        assert result.endswith("...")

    def test_truncate_short_text(self):
        """Test truncating short text (no change)"""
        text = "Short"
        result = DataFormatter.truncate_text(text, max_length=20)

        assert result == "Short"


# ============================================================================
# User Preferences Tests
# ============================================================================


class TestUserPreferences:
    """Tests for UserPreferences class"""

    def test_default_preferences(self):
        """Test default preferences"""
        prefs = UserPreferences()

        assert prefs.theme == "light"
        assert prefs.language == "zh-CN"
        assert prefs.items_per_page == 20

    def test_custom_preferences(self):
        """Test custom preferences"""
        prefs = UserPreferences(
            theme="dark",
            language="en-US",
            items_per_page=50
        )

        assert prefs.theme == "dark"
        assert prefs.language == "en-US"

    def test_to_dict(self):
        """Test converting to dictionary"""
        prefs = UserPreferences()
        result = prefs.to_dict()

        assert "theme" in result
        assert "language" in result
        assert "items_per_page" in result

    def test_from_dict(self):
        """Test creating from dictionary"""
        data = {
            "theme": "dark",
            "language": "en-US"
        }
        prefs = UserPreferences.from_dict(data)

        assert prefs.theme == "dark"
        assert prefs.language == "en-US"


class TestPreferenceManager:
    """Tests for PreferenceManager class"""

    @pytest.fixture
    def manager(self) -> PreferenceManager:
        return PreferenceManager()

    def test_get_default_preferences(self, manager):
        """Test getting default preferences for new user"""
        prefs = manager.get_preferences("new_user")

        assert prefs.theme == "light"

    def test_set_and_get_preferences(self, manager):
        """Test setting and getting preferences"""
        custom_prefs = UserPreferences(theme="dark")
        manager.set_preferences("user1", custom_prefs)

        result = manager.get_preferences("user1")

        assert result.theme == "dark"

    def test_update_single_preference(self, manager):
        """Test updating a single preference"""
        manager.set_preferences("user1", UserPreferences())
        result = manager.update_preference("user1", "theme", "dark")

        assert result.theme == "dark"

    def test_reset_to_default(self, manager):
        """Test resetting to default"""
        manager.set_preferences("user1", UserPreferences(theme="dark"))
        result = manager.reset_to_default("user1")

        assert result.theme == "light"


# ============================================================================
# Help System Tests
# ============================================================================


class TestHelpSystem:
    """Tests for HelpSystem class"""

    @pytest.fixture
    def help_system(self) -> HelpSystem:
        system = HelpSystem()

        # Add some test topics
        system.add_topic(HelpTopic(
            id="getting-started",
            title="Getting Started",
            content="How to get started with the system",
            category="basics",
            keywords=["start", "begin", "intro"]
        ))

        system.add_topic(HelpTopic(
            id="billing",
            title="Billing Guide",
            content="Understanding the billing system",
            category="billing",
            keywords=["payment", "invoice", "cost"]
        ))

        # Add FAQ
        system.add_faq(
            "How do I reset my password?",
            "Go to Settings > Security > Reset Password"
        )

        return system

    def test_get_topic(self, help_system):
        """Test getting a help topic"""
        topic = help_system.get_topic("getting-started")

        assert topic is not None
        assert topic.title == "Getting Started"

    def test_get_nonexistent_topic(self, help_system):
        """Test getting non-existent topic"""
        topic = help_system.get_topic("nonexistent")

        assert topic is None

    def test_search_topics_by_title(self, help_system):
        """Test searching topics by title"""
        results = help_system.search_topics("billing")

        assert len(results) == 1
        assert results[0].id == "billing"

    def test_search_topics_by_keyword(self, help_system):
        """Test searching topics by keyword"""
        results = help_system.search_topics("payment")

        assert len(results) == 1
        assert results[0].id == "billing"

    def test_get_faq(self, help_system):
        """Test getting FAQ"""
        faq = help_system.get_faq()

        assert len(faq) == 1
        assert "password" in faq[0]["question"]

    def test_search_faq(self, help_system):
        """Test searching FAQ"""
        results = help_system.search_faq("password")

        assert len(results) == 1

    def test_contextual_help(self, help_system):
        """Test contextual help"""
        help_system.add_contextual_help(ContextualHelp(
            element_id="submit-button",
            title="Submit Form",
            description="Click to submit the form",
            tips=["Make sure all fields are filled"]
        ))

        help_item = help_system.get_contextual_help("submit-button")

        assert help_item is not None
        assert help_item.title == "Submit Form"


# ============================================================================
# Form Validation Tests
# ============================================================================


class TestFormValidator:
    """Tests for FormValidator class"""

    def test_required_field_valid(self):
        """Test required field validation (valid)"""
        validator = FormValidator().required("name")
        result = validator.validate({"name": "John"})

        assert result.is_valid
        assert len(result.errors) == 0

    def test_required_field_missing(self):
        """Test required field validation (missing)"""
        validator = FormValidator().required("name")
        result = validator.validate({})

        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "name"

    def test_min_length_valid(self):
        """Test min length validation (valid)"""
        validator = FormValidator().min_length("password", 8)
        result = validator.validate({"password": "secretpassword"})

        assert result.is_valid

    def test_min_length_invalid(self):
        """Test min length validation (invalid)"""
        validator = FormValidator().min_length("password", 8)
        result = validator.validate({"password": "short"})

        assert not result.is_valid
        assert "VALIDATION_MIN_LENGTH" in result.errors[0].code

    def test_max_length_valid(self):
        """Test max length validation (valid)"""
        validator = FormValidator().max_length("username", 20)
        result = validator.validate({"username": "john"})

        assert result.is_valid

    def test_max_length_invalid(self):
        """Test max length validation (invalid)"""
        validator = FormValidator().max_length("username", 5)
        result = validator.validate({"username": "verylongusername"})

        assert not result.is_valid

    def test_min_value_valid(self):
        """Test min value validation (valid)"""
        validator = FormValidator().min_value("age", 18)
        result = validator.validate({"age": 25})

        assert result.is_valid

    def test_min_value_invalid(self):
        """Test min value validation (invalid)"""
        validator = FormValidator().min_value("age", 18)
        result = validator.validate({"age": 15})

        assert not result.is_valid

    def test_max_value_valid(self):
        """Test max value validation (valid)"""
        validator = FormValidator().max_value("quantity", 100)
        result = validator.validate({"quantity": 50})

        assert result.is_valid

    def test_max_value_invalid(self):
        """Test max value validation (invalid)"""
        validator = FormValidator().max_value("quantity", 100)
        result = validator.validate({"quantity": 150})

        assert not result.is_valid

    def test_email_valid(self):
        """Test email validation (valid)"""
        validator = FormValidator().email("email")
        result = validator.validate({"email": "test@example.com"})

        assert result.is_valid

    def test_email_invalid(self):
        """Test email validation (invalid)"""
        validator = FormValidator().email("email")
        result = validator.validate({"email": "not-an-email"})

        assert not result.is_valid

    def test_pattern_valid(self):
        """Test pattern validation (valid)"""
        validator = FormValidator().pattern("phone", r"^\d{11}$")
        result = validator.validate({"phone": "13800138000"})

        assert result.is_valid

    def test_pattern_invalid(self):
        """Test pattern validation (invalid)"""
        validator = FormValidator().pattern("phone", r"^\d{11}$")
        result = validator.validate({"phone": "123"})

        assert not result.is_valid

    def test_multiple_rules(self):
        """Test multiple validation rules"""
        validator = (
            FormValidator()
            .required("username")
            .min_length("username", 3)
            .max_length("username", 20)
            .required("email")
            .email("email")
        )

        result = validator.validate({
            "username": "jo",
            "email": "invalid"
        })

        assert not result.is_valid
        assert len(result.errors) == 2  # min_length and email

    def test_chained_validation(self):
        """Test chained validation syntax"""
        validator = (
            FormValidator()
            .required("name")
            .required("age")
            .min_value("age", 0)
            .max_value("age", 150)
        )

        result = validator.validate({"name": "John", "age": 30})

        assert result.is_valid


# ============================================================================
# Property-Based Tests
# ============================================================================


class TestResponseProperties:
    """Property-based tests for API responses"""

    def test_response_builder_always_has_meta(self):
        """Test response builder always creates meta"""
        test_cases = [
            ResponseBuilder("req-1").build(),
            ResponseBuilder("req-2").with_data("test").build(),
            ResponseBuilder("req-3").with_error("ERR", "Error").build(),
        ]

        for response in test_cases:
            assert response.meta is not None
            assert response.meta.request_id is not None

    def test_pagination_total_pages_consistent(self):
        """Test total pages calculation is consistent"""
        test_cases = [
            (100, 10, 10),
            (101, 10, 11),
            (10, 10, 1),
            (0, 10, 0),
            (5, 10, 1),
        ]

        for total_items, page_size, expected_pages in test_cases:
            params = PaginationParams(page_size=page_size)
            meta = PaginationMeta.from_params(params, total_items)
            assert meta.total_pages == expected_pages


class TestFormatterProperties:
    """Property-based tests for formatters"""

    def test_currency_always_has_symbol(self):
        """Test currency format always includes symbol"""
        currencies = ["CNY", "USD", "EUR", "GBP", "JPY"]

        for currency in currencies:
            result = DataFormatter.format_currency(100, currency)
            assert len(result) > 3  # Has symbol + number

    def test_file_size_always_positive_looking(self):
        """Test file size format is always sensible"""
        test_sizes = [0, 1, 100, 1024, 1024 * 1024, 1024 * 1024 * 1024]

        for size in test_sizes:
            result = DataFormatter.format_file_size(size)
            assert result is not None
            assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
