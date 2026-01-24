"""
Text-to-SQL i18n Error Handler Module

Provides internationalized error handling for Text-to-SQL operations.
Integrates with the platform i18n system to deliver error messages
in Chinese (zh) and English (en).
"""

from typing import Optional, Dict, Any, List
from fastapi import HTTPException
import logging

from src.i18n.translations import get_translation, get_current_language
from src.i18n.api_error_handler import (
    I18nAPIError,
    ValidationAPIError,
    InternalServerAPIError,
    safe_api_call
)
from src.i18n.error_handler import log_translation_error

logger = logging.getLogger(__name__)


class TextToSQLError(I18nAPIError):
    """Base exception for Text-to-SQL errors with i18n support."""

    def __init__(
        self,
        message_key: str,
        status_code: int = 500,
        error_code: str = "TEXT_TO_SQL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        **params
    ):
        """
        Initialize Text-to-SQL error with i18n support.

        Args:
            message_key: Translation key for error message
            status_code: HTTP status code
            error_code: Error code identifier
            details: Additional error details
            **params: Parameters for message formatting
        """
        # Get translated message
        try:
            message = get_translation(message_key, **params)
        except Exception as e:
            # Fallback to key if translation fails
            logger.warning(f"Translation failed for {message_key}: {e}")
            message = message_key

            # If we have params, try to format them into the message
            if params:
                try:
                    message = message.format(**params)
                except:
                    # If format fails, append params to message
                    message = f"{message} {params}"

        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            details=details or {}
        )
        self.message_key = message_key


class SQLGenerationError(TextToSQLError):
    """SQL generation failed error."""

    def __init__(self, reason: Optional[str] = None, **params):
        details = {"reason": reason} if reason else {}
        super().__init__(
            message_key="text_to_sql.error.generation_failed",
            status_code=500,
            error_code="SQL_GENERATION_FAILED",
            details=details,
            **params
        )


class SQLExecutionError(TextToSQLError):
    """SQL execution failed error."""

    def __init__(self, reason: Optional[str] = None, **params):
        details = {"reason": reason} if reason else {}
        super().__init__(
            message_key="text_to_sql.error.execution_failed",
            status_code=500,
            error_code="SQL_EXECUTION_FAILED",
            details=details,
            **params
        )


class SQLValidationError(TextToSQLError):
    """SQL validation failed error."""

    def __init__(self, reason: Optional[str] = None, **params):
        details = {"reason": reason} if reason else {}
        super().__init__(
            message_key="text_to_sql.error.validation_failed",
            status_code=400,
            error_code="SQL_VALIDATION_FAILED",
            details=details,
            **params
        )


class InvalidQueryError(TextToSQLError):
    """Invalid query request error."""

    def __init__(self, reason: Optional[str] = None, **params):
        details = {"reason": reason} if reason else {}
        super().__init__(
            message_key="text_to_sql.error.invalid_query",
            status_code=400,
            error_code="INVALID_QUERY",
            details=details,
            **params
        )


class EmptyQueryError(TextToSQLError):
    """Empty query error."""

    def __init__(self, param: Optional[str] = None, **params):
        if param:
            message_key = "text_to_sql.error.param.query_empty"
            params['param'] = param
        else:
            message_key = "text_to_sql.error.empty_query"

        super().__init__(
            message_key=message_key,
            status_code=400,
            error_code="EMPTY_QUERY",
            **params
        )


class ForbiddenSQLOperationError(TextToSQLError):
    """Forbidden SQL operation error."""

    def __init__(self, keyword: Optional[str] = None, **params):
        if keyword:
            message_key = "text_to_sql.error.param.keyword_detected"
            params['keyword'] = keyword
        else:
            message_key = "text_to_sql.error.forbidden_operation"

        super().__init__(
            message_key=message_key,
            status_code=403,
            error_code="FORBIDDEN_SQL_OPERATION",
            details={"keyword": keyword} if keyword else {},
            **params
        )


class DatabaseConnectionError(TextToSQLError):
    """Database connection error."""

    def __init__(self, reason: Optional[str] = None, **params):
        details = {"reason": reason} if reason else {}
        super().__init__(
            message_key="text_to_sql.error.connection_failed",
            status_code=503,
            error_code="DATABASE_CONNECTION_FAILED",
            details=details,
            **params
        )


class TableNotFoundError(TextToSQLError):
    """Table not found error."""

    def __init__(self, table: str, **params):
        params['table'] = table
        super().__init__(
            message_key="text_to_sql.error.param.table_missing",
            status_code=404,
            error_code="TABLE_NOT_FOUND",
            details={"table": table},
            **params
        )


class ColumnNotFoundError(TextToSQLError):
    """Column not found error."""

    def __init__(self, column: str, table: str, **params):
        params.update({'column': column, 'table': table})
        super().__init__(
            message_key="text_to_sql.error.param.column_missing",
            status_code=404,
            error_code="COLUMN_NOT_FOUND",
            details={"column": column, "table": table},
            **params
        )


class SQLTimeoutError(TextToSQLError):
    """SQL query timeout error."""

    def __init__(self, timeout: Optional[int] = None, **params):
        if timeout:
            message_key = "text_to_sql.error.param.timeout_value"
            params['timeout'] = timeout
        else:
            message_key = "text_to_sql.error.timeout"

        super().__init__(
            message_key=message_key,
            status_code=504,
            error_code="SQL_TIMEOUT",
            details={"timeout": timeout} if timeout else {},
            **params
        )


class MaxRowsExceededError(TextToSQLError):
    """Maximum rows exceeded error."""

    def __init__(self, actual: int, limit: int, **params):
        params.update({'actual': actual, 'limit': limit})
        super().__init__(
            message_key="text_to_sql.error.param.rows_exceeded",
            status_code=400,
            error_code="MAX_ROWS_EXCEEDED",
            details={"actual": actual, "limit": limit},
            **params
        )


class UnsupportedDialectError(TextToSQLError):
    """Unsupported SQL dialect error."""

    def __init__(self, dialect: str, **params):
        params['dialect'] = dialect
        super().__init__(
            message_key="text_to_sql.error.param.invalid_dialect",
            status_code=400,
            error_code="UNSUPPORTED_DIALECT",
            details={"dialect": dialect},
            **params
        )


class ModelNotAvailableError(TextToSQLError):
    """AI model not available error."""

    def __init__(self, model: Optional[str] = None, error: Optional[str] = None, **params):
        if model and error:
            message_key = "text_to_sql.error.param.model_error"
            params.update({'model': model, 'error': error})
            details = {"model": model, "error": error}
        else:
            message_key = "text_to_sql.error.model_not_available"
            details = {}

        super().__init__(
            message_key=message_key,
            status_code=503,
            error_code="MODEL_NOT_AVAILABLE",
            details=details,
            **params
        )


# ============================================================================
# Error Handler Helper Functions
# ============================================================================

def validate_query_input(query: str, max_length: int = 10000) -> None:
    """
    Validate query input.

    Args:
        query: Query string to validate
        max_length: Maximum allowed query length

    Raises:
        EmptyQueryError: If query is empty
        InvalidQueryError: If query exceeds max length
    """
    if not query or not query.strip():
        raise EmptyQueryError()

    if len(query) > max_length:
        raise InvalidQueryError(
            reason=get_translation("text_to_sql.error.query_too_long")
        )


def validate_sql_safety(sql: str) -> None:
    """
    Validate SQL safety by checking for forbidden operations.

    Args:
        sql: SQL string to validate

    Raises:
        ForbiddenSQLOperationError: If forbidden operation detected
    """
    sql_upper = sql.upper().strip()

    # Check if it's a SELECT query
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        raise ForbiddenSQLOperationError(
            keyword=sql_upper.split()[0] if sql_upper else "UNKNOWN"
        )

    # Check for dangerous operations
    forbidden_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
        "ALTER", "TRUNCATE", "REPLACE", "MERGE"
    ]

    for keyword in forbidden_keywords:
        if keyword in sql_upper:
            raise ForbiddenSQLOperationError(keyword=keyword)


def handle_text_to_sql_exception(
    error: Exception,
    operation: str = "unknown",
    context: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Handle Text-to-SQL exceptions and convert to HTTPException.

    Args:
        error: Original exception
        operation: Operation being performed
        context: Additional context information

    Returns:
        Formatted HTTPException with i18n message
    """
    context = context or {}

    # Log the error
    log_translation_error(
        f'text_to_sql_{operation}_error',
        {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            **context
        },
        'error' if not isinstance(error, TextToSQLError) else 'warning'
    )

    # Convert to HTTPException
    if isinstance(error, TextToSQLError):
        return HTTPException(
            status_code=error.status_code,
            detail={
                "error": error.error_code,
                "message": error.message,
                "details": error.details
            }
        )
    else:
        # Unknown error - wrap in generic error
        return HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": get_translation("text_to_sql.error.generation_failed"),
                "details": {
                    "original_error": str(error),
                    "error_type": type(error).__name__
                }
            }
        )


def log_text_to_sql_success(
    operation: str,
    details: Optional[Dict[str, Any]] = None
):
    """
    Log Text-to-SQL successful operations.

    Args:
        operation: Operation name (generate, execute, validate, etc.)
        details: Additional details to log
    """
    log_translation_error(
        f'text_to_sql_{operation}_success',
        {
            'operation': operation,
            **(details or {})
        },
        'info'
    )


# ============================================================================
# Export
# ============================================================================

__all__ = [
    # Base exception
    'TextToSQLError',

    # Specific exceptions
    'SQLGenerationError',
    'SQLExecutionError',
    'SQLValidationError',
    'InvalidQueryError',
    'EmptyQueryError',
    'ForbiddenSQLOperationError',
    'DatabaseConnectionError',
    'TableNotFoundError',
    'ColumnNotFoundError',
    'SQLTimeoutError',
    'MaxRowsExceededError',
    'UnsupportedDialectError',
    'ModelNotAvailableError',

    # Helper functions
    'validate_query_input',
    'validate_sql_safety',
    'handle_text_to_sql_exception',
    'log_text_to_sql_success',
]
