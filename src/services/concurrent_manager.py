"""
Concurrent modification handling with optimistic locking.

Provides version conflict detection, 409 Conflict error generation,
and retry logic for conflict resolution.

Validates: Requirements 22.1, 22.2, 22.3, 22.4
"""

import time
import logging
from typing import Any, Callable, Dict, Optional, TypeVar

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConcurrentModificationError(Exception):
    """Raised when a version conflict is detected during optimistic locking.

    Attributes:
        resource_id: ID of the conflicting resource.
        resource_type: Type name of the resource.
        expected_version: Version the caller expected.
        actual_version: Current version in the database.
    """

    def __init__(
        self,
        resource_id: str,
        resource_type: str,
        expected_version: int,
        actual_version: int,
    ):
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Conflict: {resource_type} '{resource_id}' was modified. "
            f"Expected version {expected_version}, found {actual_version}."
        )

    def to_conflict_detail(self) -> Dict[str, Any]:
        """Return a dict suitable for a 409 JSON response body."""
        return {
            "error": "conflict",
            "message": str(self),
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "expected_version": self.expected_version,
            "actual_version": self.actual_version,
        }


class OptimisticLockManager:
    """Manages optimistic locking for database models.

    Uses an integer version column to detect concurrent modifications.
    Before committing an update the caller must supply the version they
    read; if it no longer matches the row in the database the update is
    rejected with a ``ConcurrentModificationError``.
    """

    def __init__(self, db: Session):
        self.db = db

    def check_and_increment_version(
        self,
        model_instance: Any,
        expected_version: int,
        version_field: str = "lock_version",
        resource_type: Optional[str] = None,
    ) -> None:
        """Verify the version matches and bump it atomically.

        Args:
            model_instance: SQLAlchemy model instance to update.
            expected_version: The version the caller last read.
            version_field: Name of the integer version column.
            resource_type: Human-readable type for error messages.

        Raises:
            ConcurrentModificationError: When versions do not match.
            ValueError: When the model lacks the version field.
        """
        if not hasattr(model_instance, version_field):
            raise ValueError(
                f"Model {type(model_instance).__name__} has no "
                f"'{version_field}' attribute"
            )

        actual_version = getattr(model_instance, version_field)
        resource_id = str(getattr(model_instance, "id", "unknown"))
        rtype = resource_type or type(model_instance).__name__

        if actual_version != expected_version:
            raise ConcurrentModificationError(
                resource_id=resource_id,
                resource_type=rtype,
                expected_version=expected_version,
                actual_version=actual_version,
            )

        setattr(model_instance, version_field, actual_version + 1)

    def safe_update(
        self,
        model_instance: Any,
        expected_version: int,
        updates: Dict[str, Any],
        version_field: str = "lock_version",
        resource_type: Optional[str] = None,
    ) -> Any:
        """Apply *updates* to *model_instance* with optimistic locking.

        Checks the version, applies the field updates, increments the
        version, and flushes (but does not commit) so the caller can
        bundle this inside a larger transaction.

        Returns:
            The updated model instance.

        Raises:
            ConcurrentModificationError: On version mismatch.
        """
        self.check_and_increment_version(
            model_instance,
            expected_version,
            version_field=version_field,
            resource_type=resource_type,
        )

        for field, value in updates.items():
            if hasattr(model_instance, field):
                setattr(model_instance, field, value)

        self.db.flush()
        return model_instance


def retry_on_conflict(
    fn: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 0.1,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Retry *fn* when a ``ConcurrentModificationError`` is raised.

    Uses exponential back-off between attempts.

    Args:
        fn: Callable to execute.
        max_retries: Maximum number of retry attempts (excluding the
            initial call).
        base_delay: Initial delay in seconds; doubled each retry.
        *args, **kwargs: Forwarded to *fn*.

    Returns:
        The return value of *fn* on success.

    Raises:
        ConcurrentModificationError: If all retries are exhausted.
    """
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    last_error: Optional[ConcurrentModificationError] = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except ConcurrentModificationError as exc:
            last_error = exc
            if attempt < max_retries:
                logger.warning(
                    "Conflict on attempt %d/%d for %s '%s' "
                    "(expected v%d, found v%d). Retrying in %.2fs…",
                    attempt + 1,
                    max_retries + 1,
                    exc.resource_type,
                    exc.resource_id,
                    exc.expected_version,
                    exc.actual_version,
                    delay,
                )
                time.sleep(delay)
                delay *= 2

    # All retries exhausted
    raise last_error  # type: ignore[misc]
