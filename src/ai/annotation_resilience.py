"""Annotation Error Handling and Resilience Service.

This module provides comprehensive error handling and resilience mechanisms
for AI annotation operations, including retry logic, failure queuing, transaction
management, input validation, and error notifications.

Features:
- LLM API retry with exponential backoff (1s, 2s, 4s)
- Network failure queuing and recovery
- Database transaction rollback
- Input validation with detailed error messages
- Error logging and notification system

Requirements:
- 10.1: LLM API retry logic with exponential backoff
- 10.2: Network failure queuing
- 10.4: Database transaction rollback
- 10.5: Input validation
- 10.6: Error logging and notification
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# Data Models
# ============================================================================

class ErrorSeverity(str, Enum):
    """Error severity level."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error category."""
    NETWORK = "network"
    LLM_API = "llm_api"
    DATABASE = "database"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"


class RetryPolicy(BaseModel):
    """Retry policy configuration."""
    max_retries: int = 3
    backoff_base: float = 1.0  # Base delay in seconds
    backoff_multiplier: float = 2.0  # Multiplier for exponential backoff
    max_backoff: float = 60.0  # Maximum backoff in seconds
    jitter: bool = True  # Add random jitter to avoid thundering herd


class ErrorRecord(BaseModel):
    """Error record for logging and tracking."""
    error_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    category: ErrorCategory
    severity: ErrorSeverity
    operation: str
    error_message: str
    error_type: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class QueuedOperation(BaseModel):
    """Queued operation for retry after network failure."""
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    operation_type: str
    operation_func: Any  # Callable
    operation_args: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    retry_count: int = 0
    last_error: Optional[str] = None
    next_retry_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True


class ValidationError(BaseModel):
    """Input validation error."""
    field: str
    message: str
    invalid_value: Any
    constraint: Optional[str] = None


class ValidationResult(BaseModel):
    """Validation result."""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)

    def add_error(self, field: str, message: str, invalid_value: Any, constraint: Optional[str] = None):
        """Add validation error."""
        self.valid = False
        self.errors.append(ValidationError(
            field=field,
            message=message,
            invalid_value=invalid_value,
            constraint=constraint,
        ))


# ============================================================================
# LLM API Retry Service
# ============================================================================

class LLMRetryService:
    """Service for retrying LLM API calls with exponential backoff.

    Implements exponential backoff retry strategy: 1s, 2s, 4s, 8s, ...
    with optional jitter to avoid thundering herd problem.

    Attributes:
        policy: Retry policy configuration
    """

    def __init__(self, policy: Optional[RetryPolicy] = None):
        """Initialize retry service.

        Args:
            policy: Retry policy (uses default if not provided)
        """
        self.policy = policy or RetryPolicy()
        logger.info(
            f"Initialized LLM Retry Service: max_retries={self.policy.max_retries}, "
            f"backoff_base={self.policy.backoff_base}s"
        )

    async def retry_with_backoff(
        self,
        func: Callable[..., T],
        *args,
        operation_name: str = "LLM API call",
        **kwargs
    ) -> T:
        """Retry function with exponential backoff.

        Args:
            func: Async function to retry
            *args: Positional arguments for func
            operation_name: Name of operation for logging
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            Exception: Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.policy.max_retries + 1):
            try:
                logger.debug(f"{operation_name}: attempt {attempt + 1}/{self.policy.max_retries + 1}")
                result = await func(*args, **kwargs)

                if attempt > 0:
                    logger.info(f"{operation_name}: succeeded after {attempt} retries")

                return result

            except Exception as e:
                last_exception = e

                if attempt < self.policy.max_retries:
                    # Calculate backoff delay
                    delay = self._calculate_backoff(attempt)

                    logger.warning(
                        f"{operation_name}: attempt {attempt + 1} failed: {str(e)}, "
                        f"retrying in {delay:.2f}s"
                    )

                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"{operation_name}: all {self.policy.max_retries + 1} attempts failed: {str(e)}"
                    )

        # All retries exhausted
        raise last_exception

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base * (multiplier ^ attempt)
        delay = self.policy.backoff_base * (self.policy.backoff_multiplier ** attempt)

        # Cap at max_backoff
        delay = min(delay, self.policy.max_backoff)

        # Add jitter if enabled
        if self.policy.jitter:
            import random
            jitter = random.uniform(0, delay * 0.1)  # Up to 10% jitter
            delay += jitter

        return delay


# ============================================================================
# Network Failure Queue Service
# ============================================================================

class NetworkFailureQueue:
    """Queue for operations that failed due to network issues.

    Operations are queued and automatically retried when connectivity is restored.

    Attributes:
        queue: Dictionary of queued operations
        retry_interval: Interval for retry attempts (seconds)
        max_queue_size: Maximum queue size
    """

    def __init__(
        self,
        retry_interval: int = 60,
        max_queue_size: int = 1000,
    ):
        """Initialize network failure queue.

        Args:
            retry_interval: Retry interval in seconds
            max_queue_size: Maximum operations in queue
        """
        self.retry_interval = retry_interval
        self.max_queue_size = max_queue_size

        self.queue: Dict[str, QueuedOperation] = {}
        self._retry_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()

        logger.info(
            f"Initialized Network Failure Queue: "
            f"retry_interval={retry_interval}s, max_size={max_queue_size}"
        )

    async def enqueue(
        self,
        operation_type: str,
        operation_func: Callable,
        **operation_kwargs
    ) -> str:
        """Enqueue failed operation for retry.

        Args:
            operation_type: Type of operation
            operation_func: Async function to retry
            **operation_kwargs: Arguments for function

        Returns:
            Operation ID

        Raises:
            ValueError: If queue is full
        """
        async with self._lock:
            if len(self.queue) >= self.max_queue_size:
                raise ValueError(f"Queue full (max {self.max_queue_size})")

            operation = QueuedOperation(
                operation_type=operation_type,
                operation_func=operation_func,
                operation_args=operation_kwargs,
                next_retry_at=datetime.now() + timedelta(seconds=self.retry_interval),
            )

            self.queue[operation.operation_id] = operation

        logger.info(f"Queued operation {operation.operation_id} ({operation_type})")
        return operation.operation_id

    async def start_retry_loop(self):
        """Start background retry loop."""
        if self._running:
            logger.warning("Retry loop already running")
            return

        self._running = True
        self._retry_task = asyncio.create_task(self._retry_loop())
        logger.info("Started network failure queue retry loop")

    async def stop_retry_loop(self):
        """Stop background retry loop."""
        if not self._running:
            return

        self._running = False
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped network failure queue retry loop")

    async def _retry_loop(self):
        """Background retry loop."""
        while self._running:
            try:
                await self._process_queue()
                await asyncio.sleep(self.retry_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retry loop error: {e}")
                await asyncio.sleep(5)

    async def _process_queue(self):
        """Process queued operations."""
        now = datetime.now()
        operations_to_retry = []

        async with self._lock:
            for op_id, operation in list(self.queue.items()):
                if operation.next_retry_at and now >= operation.next_retry_at:
                    operations_to_retry.append((op_id, operation))

        for op_id, operation in operations_to_retry:
            try:
                logger.debug(f"Retrying operation {op_id} ({operation.operation_type})")

                # Execute operation
                await operation.operation_func(**operation.operation_args)

                # Success - remove from queue
                async with self._lock:
                    if op_id in self.queue:
                        del self.queue[op_id]

                logger.info(f"Operation {op_id} succeeded, removed from queue")

            except Exception as e:
                # Failed - update retry info
                async with self._lock:
                    if op_id in self.queue:
                        operation.retry_count += 1
                        operation.last_error = str(e)
                        operation.next_retry_at = now + timedelta(
                            seconds=self.retry_interval * (2 ** operation.retry_count)
                        )

                logger.warning(
                    f"Operation {op_id} failed (attempt {operation.retry_count}): {e}"
                )

    async def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.queue)

    async def get_queued_operations(self) -> List[QueuedOperation]:
        """Get list of queued operations."""
        return list(self.queue.values())


# ============================================================================
# Database Transaction Service
# ============================================================================

class DatabaseTransactionManager:
    """Manager for database transactions with automatic rollback on failure.

    Provides context manager for transactions with automatic rollback.
    """

    @staticmethod
    async def execute_with_rollback(
        session: AsyncSession,
        operation: Callable,
        *args,
        operation_name: str = "Database operation",
        **kwargs
    ) -> Any:
        """Execute database operation with automatic rollback on failure.

        Args:
            session: SQLAlchemy async session
            operation: Async function to execute
            *args: Positional arguments for operation
            operation_name: Name for logging
            **kwargs: Keyword arguments for operation

        Returns:
            Result from operation

        Raises:
            Exception: Original exception after rollback
        """
        try:
            # Execute operation
            result = await operation(session, *args, **kwargs)

            # Commit transaction
            await session.commit()

            logger.debug(f"{operation_name}: committed")
            return result

        except Exception as e:
            # Rollback on any error
            await session.rollback()

            logger.error(
                f"{operation_name}: rolled back due to error: {str(e)}"
            )

            raise


# ============================================================================
# Input Validation Service
# ============================================================================

class InputValidationService:
    """Service for validating input data with detailed error messages.

    Provides comprehensive validation for annotation inputs.
    """

    @staticmethod
    def validate_annotation_task(
        text: str,
        annotation_type: str,
        project_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None,
    ) -> ValidationResult:
        """Validate annotation task input.

        Args:
            text: Text to annotate
            annotation_type: Type of annotation
            project_id: Optional project ID
            tenant_id: Optional tenant ID

        Returns:
            Validation result
        """
        result = ValidationResult(valid=True)

        # Validate text
        if not text or not text.strip():
            result.add_error(
                field="text",
                message="Text cannot be empty",
                invalid_value=text,
                constraint="required",
            )
        elif len(text) > 100000:
            result.add_error(
                field="text",
                message="Text exceeds maximum length of 100,000 characters",
                invalid_value=len(text),
                constraint="max_length",
            )

        # Validate annotation_type
        valid_types = [
            "entity_recognition",
            "classification",
            "sentiment",
            "relation_extraction",
            "text_generation",
        ]
        if annotation_type not in valid_types:
            result.add_error(
                field="annotation_type",
                message=f"Invalid annotation type. Must be one of: {', '.join(valid_types)}",
                invalid_value=annotation_type,
                constraint="enum",
            )

        return result

    @staticmethod
    def validate_batch_size(batch_size: int) -> ValidationResult:
        """Validate batch size.

        Args:
            batch_size: Batch size to validate

        Returns:
            Validation result
        """
        result = ValidationResult(valid=True)

        if batch_size < 1:
            result.add_error(
                field="batch_size",
                message="Batch size must be at least 1",
                invalid_value=batch_size,
                constraint="min_value",
            )
        elif batch_size > 1000:
            result.add_error(
                field="batch_size",
                message="Batch size cannot exceed 1000",
                invalid_value=batch_size,
                constraint="max_value",
            )

        return result

    @staticmethod
    def validate_confidence_threshold(threshold: float) -> ValidationResult:
        """Validate confidence threshold.

        Args:
            threshold: Confidence threshold (0.0 to 1.0)

        Returns:
            Validation result
        """
        result = ValidationResult(valid=True)

        if not isinstance(threshold, (int, float)):
            result.add_error(
                field="confidence_threshold",
                message="Confidence threshold must be a number",
                invalid_value=threshold,
                constraint="type",
            )
        elif threshold < 0.0 or threshold > 1.0:
            result.add_error(
                field="confidence_threshold",
                message="Confidence threshold must be between 0.0 and 1.0",
                invalid_value=threshold,
                constraint="range",
            )

        return result


# ============================================================================
# Error Logging and Notification Service
# ============================================================================

class ErrorNotificationService:
    """Service for logging errors and sending notifications.

    Tracks all errors and sends notifications for critical issues.

    Attributes:
        error_log: Dictionary of error records
        notification_callbacks: List of notification callbacks
    """

    def __init__(self):
        """Initialize error notification service."""
        self.error_log: Dict[str, ErrorRecord] = {}
        self.notification_callbacks: List[Callable] = []
        self._lock = asyncio.Lock()

        logger.info("Initialized Error Notification Service")

    async def log_error(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        operation: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> str:
        """Log error with full context.

        Args:
            category: Error category
            severity: Error severity
            operation: Operation that failed
            error: Exception that occurred
            context: Optional additional context
            retry_count: Number of retries attempted

        Returns:
            Error ID
        """
        import traceback

        record = ErrorRecord(
            category=category,
            severity=severity,
            operation=operation,
            error_message=str(error),
            error_type=type(error).__name__,
            stack_trace=traceback.format_exc(),
            context=context or {},
            retry_count=retry_count,
        )

        async with self._lock:
            self.error_log[record.error_id] = record

        logger.log(
            self._severity_to_log_level(severity),
            f"[{category.value}] {operation}: {str(error)} (error_id={record.error_id})"
        )

        # Send notifications for critical errors
        if severity == ErrorSeverity.CRITICAL:
            await self._send_notifications(record)

        return record.error_id

    async def register_notification_callback(self, callback: Callable):
        """Register callback for error notifications.

        Args:
            callback: Async function to call on critical errors
        """
        async with self._lock:
            self.notification_callbacks.append(callback)

    async def _send_notifications(self, record: ErrorRecord):
        """Send notifications for error.

        Args:
            record: Error record
        """
        for callback in self.notification_callbacks:
            try:
                await callback(record)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")

    def _severity_to_log_level(self, severity: ErrorSeverity) -> int:
        """Convert severity to logging level.

        Args:
            severity: Error severity

        Returns:
            Logging level constant
        """
        mapping = {
            ErrorSeverity.DEBUG: logging.DEBUG,
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(severity, logging.ERROR)

    async def get_errors(
        self,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        unresolved_only: bool = False,
    ) -> List[ErrorRecord]:
        """Get errors from log.

        Args:
            category: Optional filter by category
            severity: Optional filter by severity
            unresolved_only: Only return unresolved errors

        Returns:
            List of error records
        """
        errors = list(self.error_log.values())

        if category:
            errors = [e for e in errors if e.category == category]

        if severity:
            errors = [e for e in errors if e.severity == severity]

        if unresolved_only:
            errors = [e for e in errors if not e.resolved]

        return errors

    async def mark_resolved(self, error_id: str):
        """Mark error as resolved.

        Args:
            error_id: Error ID
        """
        async with self._lock:
            if error_id in self.error_log:
                self.error_log[error_id].resolved = True
                self.error_log[error_id].resolved_at = datetime.now()


# ============================================================================
# Global Instances
# ============================================================================

_retry_service: Optional[LLMRetryService] = None
_failure_queue: Optional[NetworkFailureQueue] = None
_notification_service: Optional[ErrorNotificationService] = None
_services_lock = asyncio.Lock()


async def get_retry_service(policy: Optional[RetryPolicy] = None) -> LLMRetryService:
    """Get global retry service instance.

    Args:
        policy: Optional retry policy

    Returns:
        LLMRetryService instance
    """
    global _retry_service

    async with _services_lock:
        if _retry_service is None:
            _retry_service = LLMRetryService(policy)

        return _retry_service


async def get_failure_queue() -> NetworkFailureQueue:
    """Get global network failure queue instance.

    Returns:
        NetworkFailureQueue instance
    """
    global _failure_queue

    async with _services_lock:
        if _failure_queue is None:
            _failure_queue = NetworkFailureQueue()

        return _failure_queue


async def get_notification_service() -> ErrorNotificationService:
    """Get global error notification service instance.

    Returns:
        ErrorNotificationService instance
    """
    global _notification_service

    async with _services_lock:
        if _notification_service is None:
            _notification_service = ErrorNotificationService()

        return _notification_service


async def reset_resilience_services():
    """Reset all resilience services (for testing)."""
    global _retry_service, _failure_queue, _notification_service

    async with _services_lock:
        if _failure_queue:
            await _failure_queue.stop_retry_loop()

        _retry_service = None
        _failure_queue = None
        _notification_service = None
