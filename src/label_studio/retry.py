"""
Label Studio API Retry Decorator Module.

Provides specialized retry functionality for Label Studio API calls with
exponential backoff, configurable max retries, and error logging.

This module extends the base retry utilities from src/utils/retry.py with
Label Studio-specific configurations and exception handling.

Validates: Requirements 1.4 - IF sync fails, THEN system retries with exponential backoff
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

import httpx

from src.utils.retry import (
    RetryConfig,
    RetryExecutor,
    RetryStrategy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    get_circuit_breaker,
)

logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar('T')


# Label Studio specific exceptions that should trigger retry
LABEL_STUDIO_RETRYABLE_EXCEPTIONS: List[Type[Exception]] = [
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.NetworkError,
    ConnectionError,
    TimeoutError,
    OSError,  # Includes socket errors
]

# Exceptions that should NOT trigger retry (permanent failures)
LABEL_STUDIO_NON_RETRYABLE_EXCEPTIONS: List[Type[Exception]] = [
    httpx.HTTPStatusError,  # 4xx errors should not be retried
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
]

# Import Label Studio specific exceptions for non-retryable list
# These are imported lazily to avoid circular imports
def _get_label_studio_non_retryable_exceptions() -> List[Type[Exception]]:
    """
    Get the complete list of non-retryable exceptions including Label Studio specific ones.
    
    This function is used to lazily import Label Studio specific exceptions
    to avoid circular import issues.
    """
    from src.label_studio.integration import (
        LabelStudioAuthenticationError,
        LabelStudioProjectNotFoundError,
    )
    return LABEL_STUDIO_NON_RETRYABLE_EXCEPTIONS + [
        LabelStudioAuthenticationError,
        LabelStudioProjectNotFoundError,
    ]


class LabelStudioRetryConfig(RetryConfig):
    """
    Label Studio specific retry configuration.
    
    Extends the base RetryConfig with defaults optimized for Label Studio API calls:
    - Exponential backoff starting at 1 second
    - Maximum 3 retry attempts
    - Maximum delay of 30 seconds
    - Jitter enabled to prevent thundering herd
    
    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 30.0)
        strategy: Retry strategy (default: EXPONENTIAL)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter (default: True)
        jitter_range: Range of jitter as fraction of delay (default: 0.1)
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        jitter_range: float = 0.1,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        non_retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        super().__init__(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            strategy=strategy,
            backoff_multiplier=backoff_multiplier,
            jitter=jitter,
            jitter_range=jitter_range,
            retryable_exceptions=retryable_exceptions or LABEL_STUDIO_RETRYABLE_EXCEPTIONS.copy(),
            non_retryable_exceptions=non_retryable_exceptions or LABEL_STUDIO_NON_RETRYABLE_EXCEPTIONS.copy(),
        )


class LabelStudioRetryExecutor(RetryExecutor):
    """
    Label Studio specific retry executor with enhanced logging.
    
    Extends the base RetryExecutor with Label Studio-specific logging
    and error handling for better debugging and monitoring.
    """
    
    def __init__(self, config: Optional[LabelStudioRetryConfig] = None):
        super().__init__(config or LabelStudioRetryConfig())
        self.operation_name: Optional[str] = None
    
    def _log_retry_attempt(
        self,
        attempt: int,
        exception: Exception,
        delay: float
    ) -> None:
        """Log retry attempt with Label Studio context."""
        operation = self.operation_name or "Label Studio API call"
        
        # Determine error type for better logging
        if isinstance(exception, httpx.TimeoutException):
            error_type = "timeout"
        elif isinstance(exception, (httpx.ConnectError, httpx.NetworkError)):
            error_type = "network error"
        elif isinstance(exception, ConnectionError):
            error_type = "connection error"
        else:
            error_type = type(exception).__name__
        
        logger.warning(
            f"[Label Studio Retry] {operation} failed (attempt {attempt + 1}/{self.config.max_attempts}): "
            f"{error_type} - {str(exception)}. "
            f"Retrying in {delay:.2f}s..."
        )
    
    def _log_final_failure(self, exception: Exception) -> None:
        """Log final failure after all retries exhausted."""
        operation = self.operation_name or "Label Studio API call"
        
        logger.error(
            f"[Label Studio Retry] {operation} failed after {self.config.max_attempts} attempts. "
            f"Final error: {type(exception).__name__} - {str(exception)}"
        )
    
    def _log_success_after_retry(self, attempt: int) -> None:
        """Log successful operation after retry."""
        if attempt > 0:
            operation = self.operation_name or "Label Studio API call"
            logger.info(
                f"[Label Studio Retry] {operation} succeeded after {attempt + 1} attempts"
            )
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with retry logic and enhanced logging.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: The last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                result = func(*args, **kwargs)
                self._log_success_after_retry(attempt)
                return result
            except Exception as e:
                last_exception = e
                
                if not self._should_retry(e, attempt):
                    logger.debug(
                        f"[Label Studio Retry] Not retrying after attempt {attempt + 1}: "
                        f"{type(e).__name__} is not retryable"
                    )
                    raise
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self._log_retry_attempt(attempt, e, delay)
                    import time
                    time.sleep(delay)
        
        # All attempts failed
        self._log_final_failure(last_exception)
        raise last_exception
    
    async def async_execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute async function with retry logic and enhanced logging.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: The last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                self._log_success_after_retry(attempt)
                return result
            except Exception as e:
                last_exception = e
                
                if not self._should_retry(e, attempt):
                    logger.debug(
                        f"[Label Studio Retry] Not retrying after attempt {attempt + 1}: "
                        f"{type(e).__name__} is not retryable"
                    )
                    raise
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self._log_retry_attempt(attempt, e, delay)
                    await asyncio.sleep(delay)
        
        # All attempts failed
        self._log_final_failure(last_exception)
        raise last_exception


def label_studio_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    operation_name: Optional[str] = None,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    non_retryable_exceptions: Optional[List[Type[Exception]]] = None,
):
    """
    Decorator for adding retry logic to Label Studio API calls.
    
    This decorator provides exponential backoff retry functionality specifically
    designed for Label Studio API operations. It handles network errors, timeouts,
    and transient failures while logging retry attempts for debugging.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
                   Delays follow pattern: 1s, 2s, 4s, 8s... (exponential)
        max_delay: Maximum delay cap in seconds (default: 30.0)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter to prevent thundering herd (default: True)
        operation_name: Optional name for logging (default: function name)
        retryable_exceptions: List of exception types to retry (default: network/timeout errors)
        non_retryable_exceptions: List of exception types to NOT retry (default: value/type errors)
    
    Returns:
        Decorated function with retry logic
        
    Example:
        >>> @label_studio_retry(max_attempts=3, base_delay=1.0)
        ... async def create_project(self, config):
        ...     # API call that may fail transiently
        ...     pass
        
        >>> @label_studio_retry(operation_name="import_tasks")
        ... async def import_tasks(self, project_id, tasks):
        ...     # API call with custom operation name for logging
        ...     pass
    
    Validates: Requirements 1.4 - IF sync fails, THEN system retries with exponential backoff
    """
    config = LabelStudioRetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=RetryStrategy.EXPONENTIAL,
        backoff_multiplier=backoff_multiplier,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        non_retryable_exceptions=non_retryable_exceptions,
    )
    
    executor = LabelStudioRetryExecutor(config)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Set operation name for logging
        executor.operation_name = operation_name or func.__name__
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await executor.async_execute(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return executor.execute(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


def label_studio_retry_with_circuit_breaker(
    circuit_name: str = "label_studio",
    max_attempts: int = 3,
    base_delay: float = 1.0,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    operation_name: Optional[str] = None,
):
    """
    Decorator combining retry logic with circuit breaker for Label Studio API calls.
    
    This decorator provides both retry functionality and circuit breaker protection.
    The circuit breaker prevents cascading failures by temporarily stopping calls
    to Label Studio when it appears to be unavailable.
    
    Args:
        circuit_name: Name for the circuit breaker (default: "label_studio")
        max_attempts: Maximum retry attempts per call (default: 3)
        base_delay: Initial retry delay in seconds (default: 1.0)
        failure_threshold: Number of failures before circuit opens (default: 5)
        recovery_timeout: Time in seconds before attempting recovery (default: 60.0)
        operation_name: Optional name for logging
    
    Returns:
        Decorated function with retry and circuit breaker logic
        
    Example:
        >>> @label_studio_retry_with_circuit_breaker(
        ...     circuit_name="label_studio_projects",
        ...     max_attempts=3,
        ...     failure_threshold=5
        ... )
        ... async def create_project(self, config):
        ...     pass
    
    Validates: Requirements 1.4 - IF sync fails, THEN system retries with exponential backoff
    Validates: Requirements 1.7 - Error Handling and Recovery
    """
    # Configure retry
    retry_config = LabelStudioRetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        strategy=RetryStrategy.EXPONENTIAL,
    )
    
    # Configure circuit breaker
    cb_config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
    )
    
    executor = LabelStudioRetryExecutor(retry_config)
    cb = get_circuit_breaker(circuit_name, cb_config)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        executor.operation_name = operation_name or func.__name__
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                async def protected_func():
                    return await cb.async_call(func, *args, **kwargs)
                return await executor.async_execute(protected_func)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                def protected_func():
                    return cb.call(func, *args, **kwargs)
                return executor.execute(protected_func)
            return sync_wrapper
    
    return decorator


# Convenience function for creating retry executor with default config
def create_label_studio_retry_executor(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    operation_name: Optional[str] = None,
) -> LabelStudioRetryExecutor:
    """
    Create a Label Studio retry executor with custom configuration.
    
    This is useful when you need more control over retry behavior
    or want to reuse the same executor for multiple operations.
    
    Args:
        max_attempts: Maximum retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        operation_name: Optional name for logging
        
    Returns:
        Configured LabelStudioRetryExecutor instance
        
    Example:
        >>> executor = create_label_studio_retry_executor(
        ...     max_attempts=5,
        ...     base_delay=0.5,
        ...     operation_name="batch_import"
        ... )
        >>> result = await executor.async_execute(import_batch, project_id, tasks)
    """
    config = LabelStudioRetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
    )
    executor = LabelStudioRetryExecutor(config)
    executor.operation_name = operation_name
    return executor


# Export public API
__all__ = [
    'LabelStudioRetryConfig',
    'LabelStudioRetryExecutor',
    'label_studio_retry',
    'label_studio_retry_with_circuit_breaker',
    'create_label_studio_retry_executor',
    'LABEL_STUDIO_RETRYABLE_EXCEPTIONS',
    'LABEL_STUDIO_NON_RETRYABLE_EXCEPTIONS',
    'CircuitBreakerError',
]
