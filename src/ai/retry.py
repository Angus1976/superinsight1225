"""
Shared async retry utility with exponential backoff for LLM calls.

Retries only on transient errors (API errors, timeouts, rate limits),
not on validation errors or programming errors.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds


def _is_transient_error(exc: Exception) -> bool:
    """Return True if the exception is transient and worth retrying.

    Transient errors include API errors, timeouts, rate limits, and
    connection issues. Validation errors (ValueError, TypeError,
    pydantic ValidationError) are NOT retried.
    """
    # Never retry validation / programming errors
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return False

    # Check for pydantic ValidationError (avoid hard import)
    exc_type_name = type(exc).__name__
    if exc_type_name == "ValidationError":
        return False
    
    # Never retry JSON parsing errors
    if "JSONDecodeError" in exc_type_name:
        return False
    
    # Never retry instructor parsing errors
    if "InstructorRetryException" in exc_type_name:
        return False

    # OpenAI-specific transient errors (lazy check by class name to
    # avoid hard dependency on openai at module level)
    transient_names = {
        "APITimeoutError",
        "RateLimitError",
        "APIConnectionError",
        "InternalServerError",
        "ServiceUnavailableError",
    }
    if exc_type_name in transient_names:
        return True

    # Generic network / IO errors
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True

    # Default: do NOT retry unknown errors (safer to fail fast)
    logger.warning(f"Unknown error type {exc_type_name}, not retrying: {exc}")
    return False


async def retry_with_backoff(
    fn: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    operation_name: str = "LLM call",
    **kwargs: Any,
) -> T:
    """Execute an async function with exponential backoff retry.

    Args:
        fn: Async callable to execute.
        *args: Positional arguments forwarded to *fn*.
        max_retries: Maximum number of retry attempts (default 3).
        base_delay: Base delay in seconds (doubles each retry: 1s, 2s, 4s).
        operation_name: Label used in log messages.
        **kwargs: Keyword arguments forwarded to *fn*.

    Returns:
        The return value of *fn*.

    Raises:
        The last exception raised by *fn* if all retries are exhausted,
        or immediately if the error is non-transient.
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc

            if not _is_transient_error(exc):
                logger.error(
                    "%s: non-transient error, not retrying: %s", operation_name, exc,
                )
                raise

            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "%s: attempt %d/%d failed (%s), retrying in %.1fs",
                    operation_name, attempt + 1, max_retries + 1, exc, delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "%s: all %d attempts exhausted: %s",
                    operation_name, max_retries + 1, exc,
                )

    # Should not reach here, but satisfy type checker
    raise last_exc  # type: ignore[misc]
