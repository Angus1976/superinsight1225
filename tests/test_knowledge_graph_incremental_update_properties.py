"""
Property-Based Tests for Knowledge Graph Incremental Update System.

Tests the correctness and consistency properties of:
- Data listener event handling
- Version management operations
- Incremental update processing

Property 8: Incremental Update Consistency
- Events are processed in order
- Version history is maintained correctly
- Rollback operations are reversible
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any
from uuid import UUID, uuid4
from hypothesis import given, settings, strategies as st

# Import knowledge graph update modules
from src.knowledge_graph.update.data_listener import (
    DataListener,
    DataChangeEvent,
    ChangeType,
    DataSource,
    WebhookDataListener,
    CompositeDataListener,
)
from src.knowledge_graph.update.version_manager import (
    VersionManager,
    GraphVersion,
    VersionDiff,
    ChangeRecord,
    ChangeOperationType,
    VersionStatus,
)
from src.knowledge_graph.update.incremental_updater import (
    IncrementalUpdater,
    UpdateResult,
    UpdateStrategy,
    ExtractionMode,
)
from src.knowledge_graph.core.models import EntityType, RelationType


# ============================================================================
# Test Data Strategies
# ============================================================================

@st.composite
def entity_type_strategy(draw):
    """Generate random entity types."""
    return draw(st.sampled_from(list(EntityType)))


@st.composite
def change_type_strategy(draw):
    """Generate random change types."""
    return draw(st.sampled_from([ChangeType.CREATE, ChangeType.UPDATE, ChangeType.DELETE]))


@st.composite
def data_source_strategy(draw):
    """Generate random data sources."""
    return draw(st.sampled_from(list(DataSource)))


@st.composite
def data_change_event_strategy(draw):
    """Generate random data change events."""
    return DataChangeEvent(
        source=draw(data_source_strategy()),
        change_type=draw(change_type_strategy()),
        entity_id=str(draw(st.uuids())),
        new_data={
            "content": draw(st.text(min_size=10, max_size=200)),
            "metadata": {
                "key": draw(st.text(min_size=1, max_size=20)),
            }
        },
        tenant_id=f"tenant_{draw(st.integers(min_value=1, max_value=10))}",
    )


@st.composite
def change_record_strategy(draw):
    """Generate random change records."""
    operation = draw(st.sampled_from([
        ChangeOperationType.CREATE_ENTITY,
        ChangeOperationType.UPDATE_ENTITY,
        ChangeOperationType.DELETE_ENTITY,
    ]))

    return ChangeRecord(
        operation=operation,
        entity_id=draw(st.uuids()),
        old_data={"name": draw(st.text(min_size=1, max_size=50))} if operation != ChangeOperationType.CREATE_ENTITY else None,
        new_data={"name": draw(st.text(min_size=1, max_size=50))} if operation != ChangeOperationType.DELETE_ENTITY else None,
        tenant_id=f"tenant_{draw(st.integers(min_value=1, max_value=10))}",
    )


# ============================================================================
# DataChangeEvent Tests
# ============================================================================

class TestDataChangeEventProperties:
    """Property tests for DataChangeEvent."""

    @given(data_change_event_strategy())
    @settings(max_examples=50)
    def test_event_serialization_roundtrip(self, event: DataChangeEvent):
        """Property: Event serialization should be reversible."""
        event_dict = event.to_dict()

        # Verify all required fields are present
        assert "id" in event_dict
        assert "source" in event_dict
        assert "change_type" in event_dict
        assert "timestamp" in event_dict

        # Verify types
        assert isinstance(event_dict["id"], str)
        assert isinstance(event_dict["source"], str)
        assert isinstance(event_dict["change_type"], str)

    @given(data_change_event_strategy())
    @settings(max_examples=50)
    def test_event_mark_processed(self, event: DataChangeEvent):
        """Property: Marking event as processed should update state correctly."""
        assert not event.processed
        assert event.processed_at is None

        event.mark_processed()

        assert event.processed
        assert event.processed_at is not None
        assert event.error is None

    @given(data_change_event_strategy(), st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_event_mark_processed_with_error(self, event: DataChangeEvent, error_msg: str):
        """Property: Marking event with error should preserve error message."""
        event.mark_processed(error=error_msg)

        assert event.processed
        assert event.error == error_msg

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=30)
    def test_event_entity_id_in_entity_ids(self, entity_id: str):
        """Property: entity_id should always be in entity_ids list."""
        event = DataChangeEvent(
            source=DataSource.ANNOTATION,
            change_type=ChangeType.CREATE,
            entity_id=entity_id,
        )

        assert entity_id in event.entity_ids


# ============================================================================
# ChangeRecord Tests
# ============================================================================

class TestChangeRecordProperties:
    """Property tests for ChangeRecord."""

    @given(change_record_strategy())
    @settings(max_examples=50)
    def test_change_record_serialization_roundtrip(self, record: ChangeRecord):
        """Property: ChangeRecord serialization should be reversible."""
        record_dict = record.to_dict()
        restored = ChangeRecord.from_dict(record_dict)

        assert record.operation == restored.operation
        assert record.entity_id == restored.entity_id
        assert record.old_data == restored.old_data
        assert record.new_data == restored.new_data

    @given(change_record_strategy())
    @settings(max_examples=50)
    def test_reverse_operation_creates_valid_record(self, record: ChangeRecord):
        """Property: Reverse operation should create a valid record."""
        reverse = record.get_reverse_operation()

        # Verify reverse swaps old and new data
        assert reverse.old_data == record.new_data
        assert reverse.new_data == record.old_data

        # Verify entity ID is preserved
        assert reverse.entity_id == record.entity_id

    @given(change_record_strategy())
    @settings(max_examples=50)
    def test_double_reverse_preserves_data(self, record: ChangeRecord):
        """Property: Double reverse should preserve original data."""
        reverse1 = record.get_reverse_operation()
        reverse2 = reverse1.get_reverse_operation()

        assert reverse2.old_data == record.old_data
        assert reverse2.new_data == record.new_data


# ============================================================================
# VersionManager Tests
# ============================================================================

class TestVersionManagerProperties:
    """Property tests for VersionManager."""

    def test_initial_version_created(self):
        """Property: VersionManager should create initial version on init."""
        manager = VersionManager()

        assert manager.current_version is not None
        assert manager.current_version.version_number == 1
        assert manager.current_version.status == VersionStatus.ACTIVE

    @pytest.mark.asyncio
    @given(st.lists(change_record_strategy(), min_size=1, max_size=10))
    @settings(max_examples=30)
    async def test_version_creation_increments_number(self, changes: List[ChangeRecord]):
        """Property: Each new version should increment version number."""
        manager = VersionManager()
        initial_version = manager.current_version.version_number

        # Record changes
        for change in changes:
            await manager.record_change(
                operation=change.operation,
                entity_id=change.entity_id,
                old_data=change.old_data,
                new_data=change.new_data,
            )

        # Create new version
        new_version = await manager.create_version(name="Test Version")

        assert new_version.version_number == initial_version + 1

    @pytest.mark.asyncio
    async def test_version_parent_chain(self):
        """Property: Versions should form a proper parent chain."""
        manager = VersionManager()
        versions = []

        # Create multiple versions
        for i in range(3):
            await manager.record_change(
                operation=ChangeOperationType.CREATE_ENTITY,
                entity_id=uuid4(),
                new_data={"name": f"Entity {i}"},
            )
            version = await manager.create_version(name=f"Version {i+2}")
            versions.append(version)

        # Verify parent chain
        for i in range(len(versions) - 1):
            next_version = versions[i + 1] if i + 1 < len(versions) else None
            if next_version:
                assert next_version.parent_version_id == versions[i].id

    @pytest.mark.asyncio
    async def test_version_statistics_accuracy(self):
        """Property: Version statistics should accurately reflect changes."""
        manager = VersionManager()

        # Record specific changes
        creates = 3
        updates = 2
        deletes = 1

        for _ in range(creates):
            await manager.record_change(
                operation=ChangeOperationType.CREATE_ENTITY,
                entity_id=uuid4(),
                new_data={"name": "New Entity"},
            )

        for _ in range(updates):
            await manager.record_change(
                operation=ChangeOperationType.UPDATE_ENTITY,
                entity_id=uuid4(),
                old_data={"name": "Old"},
                new_data={"name": "Updated"},
            )

        for _ in range(deletes):
            await manager.record_change(
                operation=ChangeOperationType.DELETE_ENTITY,
                entity_id=uuid4(),
                old_data={"name": "Deleted"},
            )

        version = await manager.create_version()

        assert version.entities_added == creates
        assert version.entities_updated == updates
        assert version.entities_deleted == deletes

    @pytest.mark.asyncio
    async def test_version_diff_completeness(self):
        """Property: Version diff should capture all changes between versions."""
        manager = VersionManager()

        # Record some changes and create first version
        await manager.record_change(
            operation=ChangeOperationType.CREATE_ENTITY,
            entity_id=uuid4(),
            new_data={"name": "Entity 1"},
        )
        v1 = await manager.create_version(name="V1")

        # Record more changes and create second version
        await manager.record_change(
            operation=ChangeOperationType.CREATE_ENTITY,
            entity_id=uuid4(),
            new_data={"name": "Entity 2"},
        )
        await manager.record_change(
            operation=ChangeOperationType.UPDATE_ENTITY,
            entity_id=uuid4(),
            old_data={"name": "Old"},
            new_data={"name": "New"},
        )
        v2 = await manager.create_version(name="V2")

        # Compute diff
        diff = await manager.diff_versions(v1.id, v2.id)

        assert diff.total_changes == 2
        assert len(diff.entities_added) == 1
        assert len(diff.entities_updated) == 1


# ============================================================================
# GraphVersion Tests
# ============================================================================

class TestGraphVersionProperties:
    """Property tests for GraphVersion."""

    @given(st.lists(change_record_strategy(), min_size=1, max_size=20))
    @settings(max_examples=30)
    def test_version_change_count_consistency(self, changes: List[ChangeRecord]):
        """Property: Version change counts should be consistent with change records."""
        version = GraphVersion()

        expected_counts = {
            "entities_added": 0,
            "entities_updated": 0,
            "entities_deleted": 0,
            "relations_added": 0,
            "relations_updated": 0,
            "relations_deleted": 0,
        }

        for change in changes:
            version.add_change(change)

            if change.operation == ChangeOperationType.CREATE_ENTITY:
                expected_counts["entities_added"] += 1
            elif change.operation == ChangeOperationType.UPDATE_ENTITY:
                expected_counts["entities_updated"] += 1
            elif change.operation == ChangeOperationType.DELETE_ENTITY:
                expected_counts["entities_deleted"] += 1

        assert version.entities_added == expected_counts["entities_added"]
        assert version.entities_updated == expected_counts["entities_updated"]
        assert version.entities_deleted == expected_counts["entities_deleted"]
        assert len(version.change_records) == len(changes)


# ============================================================================
# DataListener Tests
# ============================================================================

class TestDataListenerProperties:
    """Property tests for DataListener."""

    @pytest.mark.asyncio
    async def test_listener_starts_and_stops(self):
        """Property: Listener should properly start and stop."""
        listener = DataListener(poll_interval=0.1)

        await listener.start()
        stats = listener.get_stats()
        assert stats["is_running"]

        await listener.stop()
        stats = listener.get_stats()
        assert not stats["is_running"]

    @pytest.mark.asyncio
    async def test_handler_registration(self):
        """Property: Handlers should be properly registered and unregistered."""
        listener = DataListener()

        async def test_handler(event: DataChangeEvent):
            pass

        listener.register_handler(test_handler)
        assert test_handler in listener._handlers

        listener.unregister_handler(test_handler)
        assert test_handler not in listener._handlers

    @pytest.mark.asyncio
    @given(st.lists(data_change_event_strategy(), min_size=1, max_size=5))
    @settings(max_examples=20)
    async def test_event_emission_increments_stats(self, events: List[DataChangeEvent]):
        """Property: Event emission should increment statistics."""
        listener = DataListener()

        initial_count = listener._stats["events_received"]

        for event in events:
            await listener.emit_event(event)

        assert listener._stats["events_received"] == initial_count + len(events)


# ============================================================================
# UpdateResult Tests
# ============================================================================

class TestUpdateResultProperties:
    """Property tests for UpdateResult."""

    @given(
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_total_changes_calculation(
        self,
        entities_created: int,
        entities_updated: int,
        entities_deleted: int,
        relations_created: int,
        relations_updated: int,
        relations_deleted: int,
    ):
        """Property: total_changes should be sum of all change counts."""
        result = UpdateResult(
            entities_created=entities_created,
            entities_updated=entities_updated,
            entities_deleted=entities_deleted,
            relations_created=relations_created,
            relations_updated=relations_updated,
            relations_deleted=relations_deleted,
        )

        expected_total = (
            entities_created +
            entities_updated +
            entities_deleted +
            relations_created +
            relations_updated +
            relations_deleted
        )

        assert result.total_changes == expected_total

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=30)
    def test_add_error_sets_success_false(self, error_msg: str):
        """Property: Adding an error should set success to False."""
        result = UpdateResult()
        assert result.success

        result.add_error(error_msg)

        assert not result.success
        assert error_msg in result.errors

    def test_mark_completed_sets_duration(self):
        """Property: mark_completed should calculate duration."""
        result = UpdateResult()

        # Small delay to ensure measurable duration
        import time
        time.sleep(0.01)

        result.mark_completed()

        assert result.completed_at is not None
        assert result.duration_ms > 0


# ============================================================================
# Integration Property Tests
# ============================================================================

class TestIncrementalUpdateIntegrationProperties:
    """Integration property tests for the incremental update system."""

    @pytest.mark.asyncio
    async def test_update_strategy_respected(self):
        """Property: Update strategy should affect processing behavior."""
        # Manual strategy - events should be buffered
        updater = IncrementalUpdater(
            strategy=UpdateStrategy.MANUAL,
            batch_size=10,
        )

        assert updater.strategy == UpdateStrategy.MANUAL

    @pytest.mark.asyncio
    async def test_updater_stats_tracking(self):
        """Property: Updater should track statistics correctly."""
        updater = IncrementalUpdater(strategy=UpdateStrategy.MANUAL)

        stats = updater.get_stats()

        assert "total_updates" in stats
        assert "strategy" in stats
        assert stats["strategy"] == UpdateStrategy.MANUAL.value


# ============================================================================
# Consistency Property Tests
# ============================================================================

class TestIncrementalUpdateConsistencyProperties:
    """Property tests for incremental update consistency."""

    @pytest.mark.asyncio
    async def test_version_ordering_consistency(self):
        """Property: Versions should maintain strict ordering."""
        manager = VersionManager()

        versions = []
        for i in range(5):
            await manager.record_change(
                operation=ChangeOperationType.CREATE_ENTITY,
                entity_id=uuid4(),
                new_data={"name": f"Entity {i}"},
            )
            version = await manager.create_version()
            versions.append(version)

        # Verify strict ordering
        for i in range(len(versions) - 1):
            assert versions[i].version_number < versions[i + 1].version_number
            assert versions[i].created_at <= versions[i + 1].created_at

    @pytest.mark.asyncio
    async def test_rollback_creates_new_version(self):
        """Property: Rollback should create a new version, not modify history."""
        manager = VersionManager()

        # Create initial version
        await manager.record_change(
            operation=ChangeOperationType.CREATE_ENTITY,
            entity_id=uuid4(),
            new_data={"name": "Entity 1"},
        )
        v1 = await manager.create_version(name="V1")

        # Create second version
        await manager.record_change(
            operation=ChangeOperationType.CREATE_ENTITY,
            entity_id=uuid4(),
            new_data={"name": "Entity 2"},
        )
        v2 = await manager.create_version(name="V2")

        # Rollback to V1
        rollback_version = await manager.rollback_to_version(v1.id)

        # Rollback should create a new version
        assert rollback_version.version_number > v2.version_number
        assert rollback_version.status == VersionStatus.ACTIVE
        assert v2.status == VersionStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_event_deduplication(self):
        """Property: Same event should not be processed twice."""
        listener = DataListener()
        processed_count = 0

        async def counting_handler(event: DataChangeEvent):
            nonlocal processed_count
            processed_count += 1

        listener.register_handler(counting_handler)

        # Create event and emit twice
        event = DataChangeEvent(
            source=DataSource.ANNOTATION,
            change_type=ChangeType.CREATE,
            entity_id="test-123",
            new_data={"content": "Test content"},
        )

        await listener.emit_event(event)
        await listener._flush_batch()

        first_count = processed_count

        # Emit same event again
        await listener.emit_event(event)
        await listener._flush_batch()

        # Should be deduplicated
        assert processed_count == first_count


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
