"""
Property-based tests for audit trail completeness.

Validates: Requirement 8.3
"""

from datetime import datetime

from hypothesis import given, settings, strategies as st

from src.toolkit.models.security import AuditEntry
from src.toolkit.security.audit import AuditLogger

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_alnum = st.characters(whitelist_categories=("L", "N"))

user_ids = st.text(min_size=1, max_size=20, alphabet=_alnum)
operation_types = st.sampled_from(
    ["read", "write", "delete", "update", "upload", "download"]
)
resource_ids = st.text(min_size=1, max_size=20, alphabet=_alnum)


# ---------------------------------------------------------------------------
# Property 14: Audit Trail Completeness
# ---------------------------------------------------------------------------


class TestAuditTrailCompleteness:
    """
    **Validates: Requirements 8.3**

    Any operation logged via AuditLogger must produce a complete,
    retrievable audit entry with user, type, and timestamp.
    """

    @given(user_id=user_ids, op=operation_types, resource=resource_ids)
    @settings(deadline=5000)
    def test_log_operation_produces_audit_entry(
        self, user_id: str, op: str, resource: str
    ):
        """Logging an operation always returns an AuditEntry."""
        logger = AuditLogger()
        entry = logger.log_operation(user_id, op, resource)

        assert isinstance(entry, AuditEntry)

    @given(user_id=user_ids, op=operation_types, resource=resource_ids)
    @settings(deadline=5000)
    def test_entry_contains_correct_fields(
        self, user_id: str, op: str, resource: str
    ):
        """The entry records the exact user_id, operation_type, and resource_id."""
        logger = AuditLogger()
        entry = logger.log_operation(user_id, op, resource)

        assert entry.user_id == user_id
        assert entry.operation_type == op
        assert entry.resource_id == resource

    @given(user_id=user_ids, op=operation_types, resource=resource_ids)
    @settings(deadline=5000)
    def test_entry_has_timestamp_and_id(
        self, user_id: str, op: str, resource: str
    ):
        """Every entry has a non-null timestamp and a non-empty entry_id."""
        logger = AuditLogger()
        entry = logger.log_operation(user_id, op, resource)

        assert entry.timestamp is not None
        assert isinstance(entry.timestamp, datetime)
        assert entry.entry_id
        assert len(entry.entry_id) > 0

    @given(user_id=user_ids, op=operation_types, resource=resource_ids)
    @settings(deadline=5000)
    def test_entry_retrievable_from_trail(
        self, user_id: str, op: str, resource: str
    ):
        """A logged entry is retrievable via get_audit_trail filters."""
        logger = AuditLogger()
        entry = logger.log_operation(user_id, op, resource)

        trail = logger.get_audit_trail(
            resource_id=resource, user_id=user_id, operation_type=op
        )
        entry_ids = [e.entry_id for e in trail]
        assert entry.entry_id in entry_ids

    @given(
        data=st.lists(
            st.tuples(user_ids, operation_types, resource_ids),
            min_size=2,
            max_size=10,
        )
    )
    @settings(deadline=5000)
    def test_multiple_operations_all_recorded(self, data):
        """Multiple operations by different users are all recorded — no lost entries."""
        logger = AuditLogger()
        logged_ids = []

        for uid, op, rid in data:
            entry = logger.log_operation(uid, op, rid)
            logged_ids.append(entry.entry_id)

        assert logger.entry_count == len(data)

        all_entries = logger.get_audit_trail()
        trail_ids = {e.entry_id for e in all_entries}
        for eid in logged_ids:
            assert eid in trail_ids
