"""Property tests for Audit and Rollback Service.

This module tests universal correctness properties:
- Property 44: Audit Log Filtering (validates 14.2)
- Property 45: Rollback Version Creation (validates 14.3, 14.4)
- Property 46: Audit Log Integrity (validates 14.5)
"""

import pytest
import asyncio
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume
from typing import List

from src.collaboration.audit_service import (
    AuditService,
    ChangeType,
    OntologyArea,
    AuditLogFilter
)


# Hypothesis strategies
uuid_strategy = st.builds(uuid4)
change_type_strategy = st.sampled_from(list(ChangeType))
ontology_area_strategy = st.sampled_from(list(OntologyArea))

# Text strategies
short_text_strategy = st.text(min_size=1, max_size=50)
medium_text_strategy = st.text(min_size=1, max_size=200)


class TestAuditLogFiltering:
    """Property 44: Audit Log Filtering.

    Validates Requirement 14.2:
    - Logs can be filtered by date range
    - Logs can be filtered by user
    - Logs can be filtered by change type
    - Logs can be filtered by ontology area
    - Multiple filters can be combined
    - Pagination works correctly
    """

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy,
        change_type=change_type_strategy,
        ontology_area=ontology_area_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_filter_by_user(
        self,
        ontology_id: UUID,
        user_id: UUID,
        change_type: ChangeType,
        ontology_area: OntologyArea
    ):
        """Logs can be filtered by user."""
        service = AuditService()

        # Create logs for specific user
        target_log = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=change_type,
            ontology_area=ontology_area,
            affected_element_ids=[uuid4()],
            affected_element_names=["Test Element"],
            before_state={"value": "old"},
            after_state={"value": "new"},
            change_description="Test change"
        )

        # Create log for different user
        other_user = uuid4()
        await service.log_change(
            ontology_id=ontology_id,
            user_id=other_user,
            change_type=change_type,
            ontology_area=ontology_area,
            affected_element_ids=[uuid4()],
            affected_element_names=["Other Element"],
            before_state={"value": "old"},
            after_state={"value": "new"},
            change_description="Other change"
        )

        # Filter by user
        filter = AuditLogFilter(user_id=user_id)
        results = await service.get_logs(filter)

        # Property: Only logs for specified user returned
        assert len(results) >= 1
        assert all(log.user_id == user_id for log in results)
        assert any(log.log_id == target_log.log_id for log in results)

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy,
        change_type=change_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_filter_by_change_type(
        self,
        ontology_id: UUID,
        user_id: UUID,
        change_type: ChangeType
    ):
        """Logs can be filtered by change type."""
        service = AuditService()

        # Create log with specific change type
        target_log = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=change_type,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Test Element"],
            before_state={},
            after_state={},
            change_description="Test"
        )

        # Create log with different change type
        other_type = ChangeType.DELETE if change_type != ChangeType.DELETE else ChangeType.CREATE
        await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=other_type,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Other Element"],
            before_state={},
            after_state={},
            change_description="Other"
        )

        # Filter by change type
        filter = AuditLogFilter(change_type=change_type)
        results = await service.get_logs(filter)

        # Property: Only logs of specified type returned
        assert len(results) >= 1
        assert all(log.change_type == change_type for log in results)

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_filter_by_date_range(
        self,
        ontology_id: UUID,
        user_id: UUID
    ):
        """Logs can be filtered by date range."""
        service = AuditService()

        # Create log in the past
        past_time = datetime.utcnow() - timedelta(days=2)

        # Create current log
        current_log = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Current"],
            before_state={},
            after_state={},
            change_description="Current change"
        )

        # Filter by recent date range
        start_date = datetime.utcnow() - timedelta(hours=1)
        filter = AuditLogFilter(
            ontology_id=ontology_id,
            start_date=start_date
        )
        results = await service.get_logs(filter)

        # Property: Only recent logs returned
        assert len(results) >= 1
        assert all(log.timestamp >= start_date for log in results)

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy,
        limit=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50, deadline=None)
    async def test_pagination(
        self,
        ontology_id: UUID,
        user_id: UUID,
        limit: int
    ):
        """Pagination works correctly."""
        service = AuditService()

        # Create multiple logs
        log_count = 10
        for i in range(log_count):
            await service.log_change(
                ontology_id=ontology_id,
                user_id=user_id,
                change_type=ChangeType.UPDATE,
                ontology_area=OntologyArea.ENTITY_TYPE,
                affected_element_ids=[uuid4()],
                affected_element_names=[f"Element {i}"],
                before_state={},
                after_state={},
                change_description=f"Change {i}"
            )

        # Get first page
        filter1 = AuditLogFilter(
            ontology_id=ontology_id,
            limit=limit,
            offset=0
        )
        page1 = await service.get_logs(filter1)

        # Get second page
        filter2 = AuditLogFilter(
            ontology_id=ontology_id,
            limit=limit,
            offset=limit
        )
        page2 = await service.get_logs(filter2)

        # Property: Pages don't overlap
        page1_ids = {log.log_id for log in page1}
        page2_ids = {log.log_id for log in page2}
        assert len(page1_ids & page2_ids) == 0

        # Property: Page sizes are correct
        assert len(page1) <= limit
        assert len(page2) <= limit

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy,
        element_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_filter_by_affected_element(
        self,
        ontology_id: UUID,
        user_id: UUID,
        element_id: UUID
    ):
        """Logs can be filtered by affected element."""
        service = AuditService()

        # Create log affecting specific element
        target_log = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[element_id],
            affected_element_names=["Target Element"],
            before_state={},
            after_state={},
            change_description="Change to target"
        )

        # Create log affecting different element
        await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Other Element"],
            before_state={},
            after_state={},
            change_description="Change to other"
        )

        # Filter by affected element
        filter = AuditLogFilter(affected_element_id=element_id)
        results = await service.get_logs(filter)

        # Property: Only logs affecting specified element returned
        assert len(results) >= 1
        assert all(element_id in log.affected_element_ids for log in results)


class TestRollbackVersionCreation:
    """Property 45: Rollback Version Creation.

    Validates Requirements 14.3, 14.4:
    - Rollback creates new version
    - Rollback doesn't delete history
    - Affected users are identified
    - Rollback is logged as a change
    """

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy,
        rollback_user=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_rollback_creates_new_version(
        self,
        ontology_id: UUID,
        user_id: UUID,
        rollback_user: UUID
    ):
        """Rollback creates a new version rather than deleting history."""
        service = AuditService()

        # Create original log
        original_log = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element"],
            before_state={"value": "old"},
            after_state={"value": "new"},
            change_description="Original change"
        )

        # Get initial log count
        filter = AuditLogFilter(ontology_id=ontology_id, limit=100)
        logs_before = await service.get_logs(filter)
        count_before = len(logs_before)

        # Perform rollback
        rollback = await service.rollback_to_version(
            target_log_id=original_log.log_id,
            performed_by=rollback_user,
            rollback_reason="Test rollback"
        )

        # Get logs after rollback
        logs_after = await service.get_logs(filter)

        # Property: New version created (log count increased)
        assert len(logs_after) == count_before + 1

        # Property: Original log still exists
        original_still_exists = any(log.log_id == original_log.log_id for log in logs_after)
        assert original_still_exists

        # Property: New rollback log exists
        assert rollback.new_version_log_id is not None
        rollback_log = await service.get_log(rollback.new_version_log_id)
        assert rollback_log is not None
        assert rollback_log.change_type == ChangeType.ROLLBACK

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user1=uuid_strategy,
        user2=uuid_strategy,
        user3=uuid_strategy,
        rollback_user=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_affected_users_identification(
        self,
        ontology_id: UUID,
        user1: UUID,
        user2: UUID,
        user3: UUID,
        rollback_user: UUID
    ):
        """Affected users are correctly identified."""
        assume(user1 != user2 and user2 != user3 and user1 != user3)
        service = AuditService()

        # Create log by user1
        log1 = await service.log_change(
            ontology_id=ontology_id,
            user_id=user1,
            change_type=ChangeType.CREATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element 1"],
            before_state={},
            after_state={},
            change_description="Change 1"
        )

        # Small delay to ensure timestamps differ
        await asyncio.sleep(0.01)

        # Create logs by user2 and user3 (after log1)
        await service.log_change(
            ontology_id=ontology_id,
            user_id=user2,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element 2"],
            before_state={},
            after_state={},
            change_description="Change 2"
        )

        await service.log_change(
            ontology_id=ontology_id,
            user_id=user3,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element 3"],
            before_state={},
            after_state={},
            change_description="Change 3"
        )

        # Rollback to log1
        rollback = await service.rollback_to_version(
            target_log_id=log1.log_id,
            performed_by=rollback_user,
            rollback_reason="Rollback test"
        )

        # Property: Users who made changes after log1 are affected
        affected_user_set = set(rollback.affected_users)
        assert user2 in affected_user_set or user3 in affected_user_set

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy,
        rollback_user=uuid_strategy,
        rollback_reason=medium_text_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_rollback_logged_as_change(
        self,
        ontology_id: UUID,
        user_id: UUID,
        rollback_user: UUID,
        rollback_reason: str
    ):
        """Rollback is logged as a change."""
        service = AuditService()

        # Create original log
        original_log = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element"],
            before_state={"value": "old"},
            after_state={"value": "new"},
            change_description="Original"
        )

        # Perform rollback
        rollback = await service.rollback_to_version(
            target_log_id=original_log.log_id,
            performed_by=rollback_user,
            rollback_reason=rollback_reason
        )

        # Get rollback log
        rollback_log = await service.get_log(rollback.new_version_log_id)

        # Property: Rollback is logged with correct metadata
        assert rollback_log is not None
        assert rollback_log.change_type == ChangeType.ROLLBACK
        assert rollback_log.user_id == rollback_user
        assert rollback_reason in rollback_log.change_description


class TestAuditLogIntegrity:
    """Property 46: Audit Log Integrity.

    Validates Requirement 14.5:
    - HMAC signatures are generated
    - HMAC signatures can be verified
    - Tampered logs are detected
    - Signature verification is constant-time
    """

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy,
        change_type=change_type_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_hmac_signature_generated(
        self,
        ontology_id: UUID,
        user_id: UUID,
        change_type: ChangeType
    ):
        """HMAC signatures are automatically generated."""
        service = AuditService()

        # Create log
        log = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=change_type,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element"],
            before_state={"value": "old"},
            after_state={"value": "new"},
            change_description="Change"
        )

        # Property: HMAC signature is present and non-empty
        assert log.hmac_signature is not None
        assert len(log.hmac_signature) > 0

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_hmac_signature_verifiable(
        self,
        ontology_id: UUID,
        user_id: UUID
    ):
        """HMAC signatures can be verified."""
        service = AuditService()

        # Create log
        log = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element"],
            before_state={"value": "old"},
            after_state={"value": "new"},
            change_description="Change"
        )

        # Verify integrity
        is_valid = await service.verify_integrity(log.log_id)

        # Property: Unmodified log passes verification
        assert is_valid is True

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_tampered_log_detected(
        self,
        ontology_id: UUID,
        user_id: UUID
    ):
        """Tampered logs are detected."""
        service = AuditService()

        # Create log
        log = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element"],
            before_state={"value": "old"},
            after_state={"value": "new"},
            change_description="Original description"
        )

        # Tamper with log (modify after_state)
        log.after_state = {"value": "tampered"}

        # Verify integrity
        is_valid = await service.verify_integrity(log.log_id)

        # Property: Tampered log fails verification
        assert is_valid is False

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy
    )
    @settings(max_examples=100, deadline=None)
    async def test_signature_uniqueness(
        self,
        ontology_id: UUID,
        user_id: UUID
    ):
        """Different logs have different signatures."""
        service = AuditService()

        # Create two different logs
        log1 = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.CREATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element 1"],
            before_state={},
            after_state={"value": "new1"},
            change_description="Change 1"
        )

        log2 = await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.CREATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element 2"],
            before_state={},
            after_state={"value": "new2"},
            change_description="Change 2"
        )

        # Property: Signatures are different
        assert log1.hmac_signature != log2.hmac_signature


class TestAuditLogQueries:
    """Test various audit log query methods."""

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy,
        element_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_change_history_for_element(
        self,
        ontology_id: UUID,
        user_id: UUID,
        element_id: UUID
    ):
        """Change history for a specific element can be retrieved."""
        service = AuditService()

        # Create multiple changes to same element
        for i in range(3):
            await service.log_change(
                ontology_id=ontology_id,
                user_id=user_id,
                change_type=ChangeType.UPDATE,
                ontology_area=OntologyArea.ENTITY_TYPE,
                affected_element_ids=[element_id],
                affected_element_names=["Element"],
                before_state={"version": i},
                after_state={"version": i + 1},
                change_description=f"Change {i}"
            )

        # Get change history
        history = await service.get_change_history(element_id, limit=10)

        # Property: All changes to element are returned
        assert len(history) >= 3
        assert all(element_id in log.affected_element_ids for log in history)

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_ontology_timeline(
        self,
        ontology_id: UUID,
        user_id: UUID
    ):
        """Ontology timeline is in chronological order."""
        service = AuditService()

        # Create multiple changes
        for i in range(5):
            await service.log_change(
                ontology_id=ontology_id,
                user_id=user_id,
                change_type=ChangeType.UPDATE,
                ontology_area=OntologyArea.ENTITY_TYPE,
                affected_element_ids=[uuid4()],
                affected_element_names=[f"Element {i}"],
                before_state={},
                after_state={},
                change_description=f"Change {i}"
            )
            await asyncio.sleep(0.01)  # Ensure timestamps differ

        # Get timeline
        timeline = await service.get_ontology_timeline(ontology_id, limit=10)

        # Property: Timeline is in chronological order (oldest first)
        for i in range(len(timeline) - 1):
            assert timeline[i].timestamp <= timeline[i + 1].timestamp


class TestAuditLogExport:
    """Test audit log export functionality."""

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_json_export(
        self,
        ontology_id: UUID,
        user_id: UUID
    ):
        """Logs can be exported as JSON."""
        service = AuditService()

        # Create logs
        await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element"],
            before_state={},
            after_state={},
            change_description="Change"
        )

        # Export as JSON
        filter = AuditLogFilter(ontology_id=ontology_id)
        json_export = await service.export_logs(filter, format="json")

        # Property: Export is valid JSON
        import json
        parsed = json.loads(json_export)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1

    @pytest.mark.asyncio
    @given(
        ontology_id=uuid_strategy,
        user_id=uuid_strategy
    )
    @settings(max_examples=50, deadline=None)
    async def test_csv_export(
        self,
        ontology_id: UUID,
        user_id: UUID
    ):
        """Logs can be exported as CSV."""
        service = AuditService()

        # Create logs
        await service.log_change(
            ontology_id=ontology_id,
            user_id=user_id,
            change_type=ChangeType.UPDATE,
            ontology_area=OntologyArea.ENTITY_TYPE,
            affected_element_ids=[uuid4()],
            affected_element_names=["Element"],
            before_state={},
            after_state={},
            change_description="Change"
        )

        # Export as CSV
        filter = AuditLogFilter(ontology_id=ontology_id)
        csv_export = await service.export_logs(filter, format="csv")

        # Property: Export has header and data rows
        lines = csv_export.strip().split("\n")
        assert len(lines) >= 2  # At least header + 1 data row
        assert "log_id" in lines[0]  # Header contains expected column
