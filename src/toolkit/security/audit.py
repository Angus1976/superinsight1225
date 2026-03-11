"""
Audit logging service for tracking all data operations.

Thread-safe in-memory audit trail that records user actions
with filtering and retrieval capabilities.
"""

import threading
from datetime import datetime
from typing import Dict, List, Optional

from ..models.security import AuditEntry


class AuditLogger:
    """
    Thread-safe audit logger that records all data operations.

    Stores entries in-memory with support for filtering by
    user, operation type, and resource.
    """

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()

    def log_operation(
        self,
        user_id: str,
        operation_type: str,
        resource_id: str,
        details: Optional[Dict] = None,
        timestamp: Optional[datetime] = None,
        status: str = "success",
    ) -> AuditEntry:
        """Record a data operation in the audit trail."""
        if not user_id or not operation_type or not resource_id:
            raise ValueError("user_id, operation_type, and resource_id are required")

        entry = AuditEntry(
            user_id=user_id,
            operation_type=operation_type,
            resource_id=resource_id,
            details=details or {},
            timestamp=timestamp or datetime.utcnow(),
            status=status,
        )

        with self._lock:
            self._entries.append(entry)

        return entry

    def get_audit_trail(
        self,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        operation_type: Optional[str] = None,
    ) -> List[AuditEntry]:
        """Retrieve audit entries with optional filters."""
        with self._lock:
            results = list(self._entries)

        if resource_id is not None:
            results = [e for e in results if e.resource_id == resource_id]
        if user_id is not None:
            results = [e for e in results if e.user_id == user_id]
        if operation_type is not None:
            results = [e for e in results if e.operation_type == operation_type]

        return results

    def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Retrieve a single audit entry by its ID."""
        with self._lock:
            for entry in self._entries:
                if entry.entry_id == entry_id:
                    return entry
        return None

    @property
    def entry_count(self) -> int:
        """Return the total number of audit entries."""
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        """Remove all audit entries (useful for testing)."""
        with self._lock:
            self._entries.clear()
