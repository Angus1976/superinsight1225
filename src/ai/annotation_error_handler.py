"""
AI Annotation Error Handler

Provides comprehensive error handling for the AI annotation system including:
- Transaction rollback
- Input validation
- Error logging and notification
- Retry logic with exponential backoff

Requirements: 10.1, 10.2, 10.4, 10.5, 10.6
"""

import asyncio
import logging
import traceback
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    LLM_API = "llm_api"
    DATABASE = "database"
    NETWORK = "network"
    VALIDATION = "validation"
    ENGINE = "engine"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for an error."""
    error_type: str
    error_message: str
    error_category: ErrorCategory
    severity: ErrorSeverity
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    operation: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'error_type': self.error_type,
            'error_message': self.error_message,
            'error_category': self.error_category.value,
            'severity': self.severity.value,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'project_id': self.project_id,
            'operation': self.operation,
            'timestamp': self.timestamp.isoformat(),
            'stack_trace': self.stack_trace,
            'additional_data': self.additional_data,
        }


# =============================================================================
# Custom Exceptions
# =============================================================================

class AnnotationError(Exception):
    """Base exception for annotation errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}


class ValidationError(AnnotationError):
    """Validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            details=details
        )
        self.field = field


class LLMAPIError(AnnotationError):
    """LLM API error."""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.LLM_API,
            severity=ErrorSeverity.ERROR,
            details=details
        )
        self.provider = provider


class DatabaseError(AnnotationError):
    """Database error."""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.ERROR,
            details=details
        )
        self.operation = operation


class NetworkError(AnnotationError):
    """Network error."""
    
    def __init__(self, message: str, endpoint: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.ERROR,
            details=details
        )
        self.endpoint = endpoint


class EngineError(AnnotationError):
    """Annotation engine error."""
    
    def __init__(self, message: str, engine_name: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.ENGINE,
            severity=ErrorSeverity.ERROR,
            details=details
        )
        self.engine_name = engine_name


class PermissionError(AnnotationError):
    """Permission error."""
    
    def __init__(self, message: str, required_role: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.PERMISSION,
            severity=ErrorSeverity.WARNING,
            details=details
        )
        self.required_role = required_role


class TimeoutError(AnnotationError):
    """Timeout error."""
    
    def __init__(self, message: str, timeout_seconds: Optional[float] = None, details: Optional[Dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.ERROR,
            details=details
        )
        self.timeout_seconds = timeout_seconds


# =============================================================================
# Input Validation (Requirement 10.5)
# =============================================================================

class InputValidator:
    """
    Input validator for annotation operations.
    
    Validates inputs before processing to catch errors early.
    """
    
    SUPPORTED_ANNOTATION_TYPES = {
        'NER', 'classification', 'sentiment', 
        'relation_extraction', 'summarization', 'qa', 'translation'
    }
    
    MAX_BATCH_SIZE = 10000
    MAX_CONTENT_LENGTH = 100000
    
    @classmethod
    def validate_confidence(cls, confidence: float, field_name: str = "confidence") -> None:
        """
        Validate confidence score.
        
        Args:
            confidence: Confidence value to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If confidence is invalid
        """
        import math
        
        if math.isnan(confidence) or math.isinf(confidence):
            raise ValidationError(
                f"Invalid {field_name}: must be a finite number",
                field=field_name,
                details={'value': str(confidence)}
            )
        
        if not 0.0 <= confidence <= 1.0:
            raise ValidationError(
                f"Invalid {field_name}: must be between 0.0 and 1.0",
                field=field_name,
                details={'value': confidence, 'valid_range': [0.0, 1.0]}
            )
    
    @classmethod
    def validate_batch_size(cls, size: int, field_name: str = "batch_size") -> None:
        """
        Validate batch size.
        
        Args:
            size: Batch size to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If batch size is invalid
        """
        if size <= 0:
            raise ValidationError(
                f"Invalid {field_name}: must be positive",
                field=field_name,
                details={'value': size}
            )
        
        if size > cls.MAX_BATCH_SIZE:
            raise ValidationError(
                f"Invalid {field_name}: exceeds maximum of {cls.MAX_BATCH_SIZE}",
                field=field_name,
                details={'value': size, 'max_allowed': cls.MAX_BATCH_SIZE}
            )
    
    @classmethod
    def validate_annotation_type(cls, annotation_type: str) -> None:
        """
        Validate annotation type.
        
        Args:
            annotation_type: Type to validate
            
        Raises:
            ValidationError: If type is not supported
        """
        if annotation_type not in cls.SUPPORTED_ANNOTATION_TYPES:
            raise ValidationError(
                f"Unsupported annotation type: {annotation_type}",
                field="annotation_type",
                details={
                    'value': annotation_type,
                    'supported_types': list(cls.SUPPORTED_ANNOTATION_TYPES)
                }
            )
    
    @classmethod
    def validate_content(cls, content: str, field_name: str = "content") -> None:
        """
        Validate content string.
        
        Args:
            content: Content to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If content is invalid
        """
        if not content or not content.strip():
            raise ValidationError(
                f"Invalid {field_name}: cannot be empty",
                field=field_name
            )
        
        if len(content) > cls.MAX_CONTENT_LENGTH:
            raise ValidationError(
                f"Invalid {field_name}: exceeds maximum length of {cls.MAX_CONTENT_LENGTH}",
                field=field_name,
                details={'length': len(content), 'max_allowed': cls.MAX_CONTENT_LENGTH}
            )
    
    @classmethod
    def validate_id(cls, id_value: str, field_name: str = "id") -> None:
        """
        Validate ID string.
        
        Args:
            id_value: ID to validate
            field_name: Name of the field for error messages
            
        Raises:
            ValidationError: If ID is invalid
        """
        if not id_value or not id_value.strip():
            raise ValidationError(
                f"Invalid {field_name}: cannot be empty",
                field=field_name
            )
        
        if len(id_value) > 255:
            raise ValidationError(
                f"Invalid {field_name}: exceeds maximum length of 255",
                field=field_name,
                details={'length': len(id_value)}
            )


# =============================================================================
# Error Logging and Notification (Requirement 10.6)
# =============================================================================

class ErrorNotifier:
    """
    Error notification service.
    
    Routes error notifications based on severity.
    """
    
    SEVERITY_CHANNELS = {
        ErrorSeverity.CRITICAL: ['email', 'slack', 'pagerduty'],
        ErrorSeverity.ERROR: ['email', 'slack'],
        ErrorSeverity.WARNING: ['slack'],
        ErrorSeverity.INFO: [],
    }
    
    def __init__(self):
        """Initialize notifier."""
        self._handlers: Dict[str, Callable] = {}
        self._error_counts: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    def register_handler(self, channel: str, handler: Callable) -> None:
        """
        Register notification handler for a channel.
        
        Args:
            channel: Channel name (email, slack, etc.)
            handler: Async handler function
        """
        self._handlers[channel] = handler
    
    async def notify(self, context: ErrorContext) -> None:
        """
        Send error notification.
        
        Args:
            context: Error context
        """
        channels = self.SEVERITY_CHANNELS.get(context.severity, [])
        
        for channel in channels:
            handler = self._handlers.get(channel)
            if handler:
                try:
                    await handler(context)
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel}: {e}")
    
    async def track_error(self, category: ErrorCategory) -> int:
        """
        Track error occurrence.
        
        Args:
            category: Error category
            
        Returns:
            Current error count for category
        """
        async with self._lock:
            key = category.value
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
            return self._error_counts[key]
    
    async def get_error_counts(self) -> Dict[str, int]:
        """Get error counts by category."""
        async with self._lock:
            return self._error_counts.copy()
    
    async def reset_counts(self) -> None:
        """Reset error counts."""
        async with self._lock:
            self._error_counts.clear()


class ErrorLogger:
    """
    Structured error logger.
    
    Logs errors with full context for debugging.
    """
    
    def __init__(self, notifier: Optional[ErrorNotifier] = None):
        """
        Initialize logger.
        
        Args:
            notifier: Optional error notifier
        """
        self.notifier = notifier or ErrorNotifier()
    
    async def log_error(
        self,
        error: Exception,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        operation: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """
        Log error with full context.
        
        Args:
            error: The exception
            user_id: User ID
            tenant_id: Tenant ID
            project_id: Project ID
            operation: Operation name
            additional_data: Additional context data
            
        Returns:
            Error context
        """
        # Determine category and severity
        if isinstance(error, AnnotationError):
            category = error.category
            severity = error.severity
        else:
            category = ErrorCategory.UNKNOWN
            severity = ErrorSeverity.ERROR
        
        # Create context
        context = ErrorContext(
            error_type=type(error).__name__,
            error_message=str(error),
            error_category=category,
            severity=severity,
            user_id=user_id,
            tenant_id=tenant_id,
            project_id=project_id,
            operation=operation,
            stack_trace=traceback.format_exc(),
            additional_data=additional_data or {}
        )
        
        # Log based on severity
        log_data = context.to_dict()
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {context.error_message}", extra=log_data)
        elif severity == ErrorSeverity.ERROR:
            logger.error(f"Error: {context.error_message}", extra=log_data)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(f"Warning: {context.error_message}", extra=log_data)
        else:
            logger.info(f"Info: {context.error_message}", extra=log_data)
        
        # Track and notify
        await self.notifier.track_error(category)
        await self.notifier.notify(context)
        
        return context


# =============================================================================
# Transaction Rollback (Requirement 10.4)
# =============================================================================

class TransactionManager:
    """
    Transaction manager for database operations.
    
    Provides rollback capability on failures.
    """
    
    def __init__(self, db_session: Optional[Any] = None):
        """
        Initialize transaction manager.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
        self._operations: List[Dict[str, Any]] = []
        self._committed = False
    
    async def add_operation(
        self,
        operation_type: str,
        data: Dict[str, Any],
        rollback_fn: Optional[Callable] = None
    ) -> None:
        """
        Add operation to transaction.
        
        Args:
            operation_type: Type of operation
            data: Operation data
            rollback_fn: Optional rollback function
        """
        self._operations.append({
            'type': operation_type,
            'data': data,
            'rollback_fn': rollback_fn,
            'timestamp': datetime.now(),
        })
    
    async def commit(self) -> None:
        """Commit transaction."""
        if self.db_session:
            try:
                await self.db_session.commit()
                self._committed = True
            except Exception as e:
                await self.rollback()
                raise DatabaseError(
                    f"Transaction commit failed: {e}",
                    operation="commit"
                )
    
    async def rollback(self) -> None:
        """Rollback transaction."""
        if self.db_session:
            try:
                await self.db_session.rollback()
            except Exception as e:
                logger.error(f"Database rollback failed: {e}")
        
        # Execute rollback functions in reverse order
        for op in reversed(self._operations):
            rollback_fn = op.get('rollback_fn')
            if rollback_fn:
                try:
                    if asyncio.iscoroutinefunction(rollback_fn):
                        await rollback_fn(op['data'])
                    else:
                        rollback_fn(op['data'])
                except Exception as e:
                    logger.error(f"Rollback function failed: {e}")
        
        self._operations.clear()
        self._committed = False
    
    def get_operations(self) -> List[Dict[str, Any]]:
        """Get list of operations in transaction."""
        return self._operations.copy()


# =============================================================================
# Retry Logic (Requirement 10.1)
# =============================================================================

@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt.
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        import random
        
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        return delay


def with_retry(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: tuple = (LLMAPIError, NetworkError, TimeoutError)
):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        config: Retry configuration
        retryable_exceptions: Exceptions that trigger retry
        
    Returns:
        Decorated function
    """
    config = config or RetryConfig()
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts - 1:
                        delay = config.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {config.max_attempts} attempts failed: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


# =============================================================================
# Request Queue for Network Failures (Requirement 10.2)
# =============================================================================

@dataclass
class QueuedRequest:
    """A queued request."""
    id: str
    operation: str
    data: Dict[str, Any]
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3


class RequestQueue:
    """
    Request queue for handling network failures.
    
    Queues requests during outages and processes them when connectivity restored.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize request queue.
        
        Args:
            max_size: Maximum queue size
        """
        self.max_size = max_size
        self._queue: List[QueuedRequest] = []
        self._lock = asyncio.Lock()
        self._processing = False
    
    async def enqueue(self, request: QueuedRequest) -> bool:
        """
        Add request to queue.
        
        Args:
            request: Request to queue
            
        Returns:
            True if queued, False if queue full
        """
        async with self._lock:
            if len(self._queue) >= self.max_size:
                logger.warning(f"Request queue full, rejecting request: {request.id}")
                return False
            
            self._queue.append(request)
            logger.info(f"Request queued: {request.id}")
            return True
    
    async def dequeue(self) -> Optional[QueuedRequest]:
        """
        Get next request from queue.
        
        Returns:
            Next request or None if empty
        """
        async with self._lock:
            if not self._queue:
                return None
            return self._queue.pop(0)
    
    async def process_queue(
        self,
        processor: Callable[[QueuedRequest], Any]
    ) -> Dict[str, Any]:
        """
        Process all queued requests.
        
        Args:
            processor: Async function to process each request
            
        Returns:
            Processing results
        """
        if self._processing:
            return {'status': 'already_processing'}
        
        self._processing = True
        results = {
            'processed': 0,
            'failed': 0,
            'requeued': 0,
        }
        
        try:
            while True:
                request = await self.dequeue()
                if request is None:
                    break
                
                try:
                    await processor(request)
                    results['processed'] += 1
                except Exception as e:
                    logger.error(f"Failed to process queued request {request.id}: {e}")
                    
                    # Requeue if retries remaining
                    if request.retry_count < request.max_retries:
                        request.retry_count += 1
                        await self.enqueue(request)
                        results['requeued'] += 1
                    else:
                        results['failed'] += 1
        finally:
            self._processing = False
        
        return results
    
    async def get_size(self) -> int:
        """Get current queue size."""
        async with self._lock:
            return len(self._queue)
    
    async def clear(self) -> int:
        """
        Clear the queue.
        
        Returns:
            Number of cleared requests
        """
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count


# =============================================================================
# Global Instances
# =============================================================================

_error_logger: Optional[ErrorLogger] = None
_request_queue: Optional[RequestQueue] = None


def get_error_logger() -> ErrorLogger:
    """Get the global error logger instance."""
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger()
    return _error_logger


def get_request_queue() -> RequestQueue:
    """Get the global request queue instance."""
    global _request_queue
    if _request_queue is None:
        _request_queue = RequestQueue()
    return _request_queue


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    'ErrorSeverity',
    'ErrorCategory',
    
    # Data classes
    'ErrorContext',
    'RetryConfig',
    'QueuedRequest',
    
    # Exceptions
    'AnnotationError',
    'ValidationError',
    'LLMAPIError',
    'DatabaseError',
    'NetworkError',
    'EngineError',
    'PermissionError',
    'TimeoutError',
    
    # Classes
    'InputValidator',
    'ErrorNotifier',
    'ErrorLogger',
    'TransactionManager',
    'RequestQueue',
    
    # Decorators
    'with_retry',
    
    # Functions
    'get_error_logger',
    'get_request_queue',
]
