"""
Unit tests for Data Lifecycle Error Handler

Tests error classes, response formatting, logging, and FastAPI handlers.

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5, 25.6
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.error_handler import (
    DataLifecycleError,
    DataValidationError,
    EnhancementJobError,
    InvalidStateTransitionError,
    PermissionDeniedError,
    log_lifecycle_error,
    data_lifecycle_error_handler,
    register_lifecycle_error_handlers,
)


# ============================================================================
# Test: DataLifecycleError (base class)
# ============================================================================

class TestDataLifecycleError:
    """Tests for the base DataLifecycleError class."""

    def test_default_values(self):
        err = DataLifecycleError("something broke")
        assert err.message == "something broke"
        assert err.error_type == "DATA_LIFECYCLE_ERROR"
        assert err.details == {}
        assert err.suggestions == []
        assert err.status_code == 400

    def test_custom_values(self):
        err = DataLifecycleError(
            message="custom",
            error_type="CUSTOM",
            details={"key": "val"},
            suggestions=["try again"],
            status_code=500,
        )
        assert err.error_type == "CUSTOM"
        assert err.details == {"key": "val"}
        assert err.suggestions == ["try again"]
        assert err.status_code == 500

    def test_to_response_dict_structure(self):
        err = DataLifecycleError(
            message="test",
            error_type="TEST_ERROR",
            details={"foo": "bar"},
            suggestions=["fix it"],
        )
        resp = err.to_response_dict()
        assert resp["error_type"] == "TEST_ERROR"
        assert resp["message"] == "test"
        assert resp["details"] == {"foo": "bar"}
        assert resp["suggestions"] == ["fix it"]
        assert "timestamp" in resp

    def test_is_exception(self):
        err = DataLifecycleError("boom")
        assert isinstance(err, Exception)
        assert str(err) == "boom"


# ============================================================================
# Test: InvalidStateTransitionError
# ============================================================================

class TestInvalidStateTransitionError:
    """Tests for invalid state transition errors. Validates: Req 25.1"""

    def test_basic_transition_error(self):
        err = InvalidStateTransitionError(
            current_state="raw",
            attempted_state="enhanced",
            valid_transitions=["structured"],
        )
        assert err.status_code == 409
        assert err.error_type == "INVALID_STATE_TRANSITION"
        assert "raw" in err.message
        assert "enhanced" in err.message

    def test_details_include_valid_transitions(self):
        err = InvalidStateTransitionError(
            current_state="raw",
            attempted_state="approved",
            valid_transitions=["structured"],
            resource_id="res-123",
        )
        details = err.details
        assert details["current_state"] == "raw"
        assert details["attempted_state"] == "approved"
        assert details["valid_transitions"] == ["structured"]
        assert details["resource_id"] == "res-123"

    def test_suggestions_with_valid_transitions(self):
        err = InvalidStateTransitionError(
            current_state="temp_stored",
            attempted_state="enhanced",
            valid_transitions=["under_review"],
        )
        assert any("under_review" in s for s in err.suggestions)

    def test_terminal_state_suggestions(self):
        err = InvalidStateTransitionError(
            current_state="archived",
            attempted_state="raw",
            valid_transitions=[],
        )
        assert any("terminal" in s.lower() for s in err.suggestions)

    def test_response_dict_completeness(self):
        err = InvalidStateTransitionError(
            current_state="raw",
            attempted_state="enhanced",
            valid_transitions=["structured"],
        )
        resp = err.to_response_dict()
        assert resp["error_type"] == "INVALID_STATE_TRANSITION"
        assert "valid_transitions" in resp["details"]
        assert len(resp["suggestions"]) > 0

    def test_no_resource_id(self):
        err = InvalidStateTransitionError(
            current_state="raw",
            attempted_state="enhanced",
        )
        assert "resource_id" not in err.details


# ============================================================================
# Test: PermissionDeniedError
# ============================================================================

class TestPermissionDeniedError:
    """Tests for permission denied errors. Validates: Req 25.2"""

    def test_basic_permission_error(self):
        err = PermissionDeniedError(
            required_permissions=["edit", "delete"],
            user_permissions=["view"],
        )
        assert err.status_code == 403
        assert err.error_type == "PERMISSION_DENIED"
        assert "edit" in err.message

    def test_details_include_permissions(self):
        err = PermissionDeniedError(
            required_permissions=["review"],
            user_permissions=["view"],
            resource_id="data-456",
            user_id="user-789",
        )
        details = err.details
        assert details["required_permissions"] == ["review"]
        assert details["user_permissions"] == ["view"]
        assert details["resource_id"] == "data-456"
        assert details["user_id"] == "user-789"

    def test_suggestions_show_missing_permissions(self):
        err = PermissionDeniedError(
            required_permissions=["edit", "delete"],
            user_permissions=["view"],
        )
        suggestions_text = " ".join(err.suggestions)
        assert "delete" in suggestions_text
        assert "edit" in suggestions_text

    def test_empty_user_permissions(self):
        err = PermissionDeniedError(
            required_permissions=["admin"],
        )
        assert err.details["user_permissions"] == []
        assert any("admin" in s for s in err.suggestions)

    def test_no_optional_fields(self):
        err = PermissionDeniedError(required_permissions=["view"])
        assert "resource_id" not in err.details
        assert "user_id" not in err.details


# ============================================================================
# Test: DataValidationError
# ============================================================================

class TestDataValidationError:
    """Tests for data validation errors. Validates: Req 25.3"""

    def test_single_validation_error(self):
        errors = [{"field": "quality_score", "message": "must be between 0 and 1"}]
        err = DataValidationError(validation_errors=errors)
        assert err.status_code == 400
        assert err.error_type == "DATA_VALIDATION_ERROR"
        assert "1 error" in err.message

    def test_multiple_validation_errors(self):
        errors = [
            {"field": "id", "message": "invalid UUID"},
            {"field": "version", "message": "must be positive"},
        ]
        err = DataValidationError(validation_errors=errors)
        assert "2 error" in err.message
        assert err.details["error_count"] == 2

    def test_details_include_all_errors(self):
        errors = [{"field": "name", "message": "required"}]
        err = DataValidationError(
            validation_errors=errors, resource_id="res-1"
        )
        assert err.details["validation_errors"] == errors
        assert err.details["resource_id"] == "res-1"

    def test_suggestions_per_field(self):
        errors = [
            {"field": "score", "message": "out of range"},
            {"field": "id", "message": "bad format"},
        ]
        err = DataValidationError(validation_errors=errors)
        assert len(err.suggestions) == 2
        assert any("score" in s for s in err.suggestions)
        assert any("id" in s for s in err.suggestions)

    def test_empty_errors_list(self):
        err = DataValidationError(validation_errors=[])
        assert err.details["error_count"] == 0
        assert err.suggestions == []


# ============================================================================
# Test: EnhancementJobError
# ============================================================================

class TestEnhancementJobError:
    """Tests for enhancement job errors. Validates: Reqs 25.4, 25.5"""

    def test_basic_job_error(self):
        err = EnhancementJobError(
            job_id="job-001",
            reason="algorithm timeout",
        )
        assert err.status_code == 500
        assert err.error_type == "ENHANCEMENT_JOB_ERROR"
        assert "job-001" in err.message
        assert "algorithm timeout" in err.message

    def test_details_include_job_info(self):
        err = EnhancementJobError(
            job_id="job-002",
            reason="out of memory",
            enhancement_type="data_augmentation",
            supports_rollback=True,
        )
        details = err.details
        assert details["job_id"] == "job-002"
        assert details["reason"] == "out of memory"
        assert details["enhancement_type"] == "data_augmentation"
        assert details["supports_rollback"] is True

    def test_retry_params_in_details(self):
        retry_params = {"batch_size": 50, "timeout": 120}
        err = EnhancementJobError(
            job_id="job-003",
            reason="timeout",
            retry_with_params=retry_params,
        )
        assert err.details["retry_with_params"] == retry_params
        assert any("Retry" in s for s in err.suggestions)

    def test_rollback_suggestion(self):
        err = EnhancementJobError(
            job_id="job-004",
            reason="failed",
            supports_rollback=True,
        )
        assert any("Rollback" in s for s in err.suggestions)

    def test_no_rollback_suggestion_when_unsupported(self):
        err = EnhancementJobError(
            job_id="job-005",
            reason="failed",
            supports_rollback=False,
        )
        assert not any("Rollback" in s for s in err.suggestions)

    def test_default_retry_suggestion(self):
        err = EnhancementJobError(
            job_id="job-006",
            reason="unknown",
        )
        assert any("Retry" in s or "retry" in s for s in err.suggestions)


# ============================================================================
# Test: log_lifecycle_error
# ============================================================================

class TestLogLifecycleError:
    """Tests for error logging. Validates: Req 25.6"""

    @patch("src.services.error_handler.logger")
    def test_logs_error_with_context(self, mock_logger):
        err = DataLifecycleError("test error", error_type="TEST")
        log_lifecycle_error(err, resource_id="r-1", user_id="u-1")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "TEST" in call_args[0][0]
        extra = call_args[1]["extra"]
        assert extra["resource_id"] == "r-1"
        assert extra["user_id"] == "u-1"
        assert extra["error_type"] == "TEST"

    @patch("src.services.error_handler.logger")
    def test_logs_without_optional_context(self, mock_logger):
        err = DataLifecycleError("minimal")
        log_lifecycle_error(err)

        mock_logger.error.assert_called_once()
        extra = mock_logger.error.call_args[1]["extra"]
        assert "resource_id" not in extra
        assert "user_id" not in extra

    @patch("src.services.error_handler.logger")
    def test_logs_details(self, mock_logger):
        err = InvalidStateTransitionError(
            current_state="raw",
            attempted_state="enhanced",
            valid_transitions=["structured"],
        )
        log_lifecycle_error(err)

        extra = mock_logger.error.call_args[1]["extra"]
        assert "valid_transitions" in extra["details"]


# ============================================================================
# Test: FastAPI Exception Handler
# ============================================================================

class TestDataLifecycleErrorHandler:
    """Tests for the FastAPI exception handler."""

    @pytest.mark.asyncio
    async def test_handler_returns_json_response(self):
        request = MagicMock()
        request.state = MagicMock()
        request.state.user_id = "user-1"

        err = InvalidStateTransitionError(
            current_state="raw",
            attempted_state="enhanced",
            valid_transitions=["structured"],
            resource_id="data-1",
        )

        with patch("src.services.error_handler.log_lifecycle_error"):
            response = await data_lifecycle_error_handler(request, err)

        assert response.status_code == 409
        assert response.body is not None

    @pytest.mark.asyncio
    async def test_handler_calls_log(self):
        request = MagicMock()
        request.state = MagicMock(spec=[])

        err = DataLifecycleError("test")

        with patch("src.services.error_handler.log_lifecycle_error") as mock_log:
            await data_lifecycle_error_handler(request, err)
            mock_log.assert_called_once()


# ============================================================================
# Test: register_lifecycle_error_handlers
# ============================================================================

class TestRegisterHandlers:
    """Tests for handler registration."""

    def test_registers_handler_on_app(self):
        app = MagicMock(spec=["add_exception_handler"])
        register_lifecycle_error_handlers(app)
        app.add_exception_handler.assert_called_once_with(
            DataLifecycleError, data_lifecycle_error_handler
        )
