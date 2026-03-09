"""
Data Lifecycle Error Handler

Specialized error classes and handlers for the data lifecycle system.
Each error provides structured response data with actionable suggestions.

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5, 25.6
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.models.data_lifecycle import DataState

logger = logging.getLogger(__name__)


# ============================================================================
# Base Error Class
# ============================================================================

class DataLifecycleError(Exception):
    """Base error class for all data lifecycle errors."""

    def __init__(
        self,
        message: str,
        error_type: str = "DATA_LIFECYCLE_ERROR",
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        status_code: int = 400,
    ):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.suggestions = suggestions or []
        self.status_code = status_code
        super().__init__(message)

    def to_response_dict(self) -> Dict[str, Any]:
        """Convert error to a structured JSON response dict."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============================================================================
# Invalid State Transition Error
# ============================================================================

class InvalidStateTransitionError(DataLifecycleError):
    """
    Raised when an invalid state transition is attempted.

    Includes current state, attempted target, and valid transitions.
    Validates: Requirement 25.1
    """

    def __init__(
        self,
        current_state: str,
        attempted_state: str,
        valid_transitions: Optional[List[str]] = None,
        resource_id: Optional[str] = None,
    ):
        self.current_state = current_state
        self.attempted_state = attempted_state
        self.valid_transitions = valid_transitions or []
        self.resource_id = resource_id

        message = (
            f"Cannot transition from '{current_state}' to '{attempted_state}'"
        )
        details = {
            "current_state": current_state,
            "attempted_state": attempted_state,
            "valid_transitions": self.valid_transitions,
        }
        if resource_id:
            details["resource_id"] = resource_id

        suggestions = self._build_suggestions()

        super().__init__(
            message=message,
            error_type="INVALID_STATE_TRANSITION",
            details=details,
            suggestions=suggestions,
            status_code=409,
        )

    def _build_suggestions(self) -> List[str]:
        if not self.valid_transitions:
            return [f"State '{self.current_state}' is a terminal state."]
        transitions_str = ", ".join(self.valid_transitions)
        return [f"Valid transitions from '{self.current_state}': {transitions_str}"]


# ============================================================================
# Permission Denied Error
# ============================================================================

class PermissionDeniedError(DataLifecycleError):
    """
    Raised when a user lacks required permissions.

    Includes required permissions and user's current permissions.
    Validates: Requirement 25.2
    """

    def __init__(
        self,
        required_permissions: List[str],
        user_permissions: Optional[List[str]] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.required_permissions = required_permissions
        self.user_permissions = user_permissions or []
        self.resource_id = resource_id
        self.user_id = user_id

        message = (
            f"Permission denied. Required: {', '.join(required_permissions)}"
        )
        details: Dict[str, Any] = {
            "required_permissions": required_permissions,
            "user_permissions": self.user_permissions,
        }
        if resource_id:
            details["resource_id"] = resource_id
        if user_id:
            details["user_id"] = user_id

        missing = set(required_permissions) - set(self.user_permissions)
        suggestions = [
            f"Missing permissions: {', '.join(sorted(missing))}",
            "Contact an administrator to request the required permissions.",
        ]

        super().__init__(
            message=message,
            error_type="PERMISSION_DENIED",
            details=details,
            suggestions=suggestions,
            status_code=403,
        )


# ============================================================================
# Data Validation Error
# ============================================================================

class DataValidationError(DataLifecycleError):
    """
    Raised when data validation fails.

    Includes specific validation errors with field names.
    Validates: Requirement 25.3
    """

    def __init__(
        self,
        validation_errors: List[Dict[str, Any]],
        resource_id: Optional[str] = None,
    ):
        self.validation_errors = validation_errors
        self.resource_id = resource_id

        error_count = len(validation_errors)
        message = f"Data validation failed with {error_count} error(s)"

        details: Dict[str, Any] = {
            "validation_errors": validation_errors,
            "error_count": error_count,
        }
        if resource_id:
            details["resource_id"] = resource_id

        suggestions = self._build_suggestions()

        super().__init__(
            message=message,
            error_type="DATA_VALIDATION_ERROR",
            details=details,
            suggestions=suggestions,
            status_code=400,
        )

    def _build_suggestions(self) -> List[str]:
        suggestions = []
        for err in self.validation_errors:
            field = err.get("field", "unknown")
            msg = err.get("message", "invalid value")
            suggestions.append(f"Fix field '{field}': {msg}")
        return suggestions


# ============================================================================
# Enhancement Job Error
# ============================================================================

class EnhancementJobError(DataLifecycleError):
    """
    Raised when an enhancement job fails.

    Includes job ID, failure reason, and retry options.
    Validates: Requirements 25.4, 25.5
    """

    def __init__(
        self,
        job_id: str,
        reason: str,
        enhancement_type: Optional[str] = None,
        retry_with_params: Optional[Dict[str, Any]] = None,
        supports_rollback: bool = True,
    ):
        self.job_id = job_id
        self.reason = reason
        self.enhancement_type = enhancement_type
        self.retry_with_params = retry_with_params
        self.supports_rollback = supports_rollback

        message = f"Enhancement job '{job_id}' failed: {reason}"

        details: Dict[str, Any] = {
            "job_id": job_id,
            "reason": reason,
            "supports_rollback": supports_rollback,
        }
        if enhancement_type:
            details["enhancement_type"] = enhancement_type
        if retry_with_params:
            details["retry_with_params"] = retry_with_params

        suggestions = self._build_suggestions()

        super().__init__(
            message=message,
            error_type="ENHANCEMENT_JOB_ERROR",
            details=details,
            suggestions=suggestions,
            status_code=500,
        )

    def _build_suggestions(self) -> List[str]:
        suggestions = []
        if self.retry_with_params:
            suggestions.append(
                "Retry the job with suggested parameters: "
                f"{self.retry_with_params}"
            )
        else:
            suggestions.append("Retry the job with different parameters.")
        if self.supports_rollback:
            suggestions.append(
                f"Rollback enhancement job '{self.job_id}' to restore "
                "original data."
            )
        return suggestions


# ============================================================================
# Error Logging Helpers
# ============================================================================

def log_lifecycle_error(
    error: DataLifecycleError,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Log a data lifecycle error with sufficient context.

    Validates: Requirement 25.6
    """
    log_context = {
        "error_type": error.error_type,
        "status_code": error.status_code,
    }
    if resource_id:
        log_context["resource_id"] = resource_id
    if user_id:
        log_context["user_id"] = user_id
    log_context["details"] = error.details

    logger.error(
        f"DataLifecycle error [{error.error_type}]: {error.message}",
        extra=log_context,
    )


# ============================================================================
# FastAPI Exception Handlers
# ============================================================================

async def data_lifecycle_error_handler(
    request: Request, exc: DataLifecycleError
) -> JSONResponse:
    """Handle DataLifecycleError and all subclasses."""
    user_id = getattr(request.state, "user_id", None)
    resource_id = exc.details.get("resource_id")

    log_lifecycle_error(exc, resource_id=resource_id, user_id=user_id)

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response_dict(),
    )


def register_lifecycle_error_handlers(app: FastAPI) -> None:
    """Register data lifecycle exception handlers with a FastAPI app."""
    app.add_exception_handler(
        DataLifecycleError, data_lifecycle_error_handler
    )
    logger.info("Registered data lifecycle error handlers")
