"""
Property-Based Tests for History Tracker.

Tests the configuration history tracking functionality using Hypothesis
for property-based testing.

**Feature: admin-configuration**
**Property 4: 配置回滚一致性**
**Property 5: 配置历史完整性**
**Validates: Requirements 6.2, 6.4**
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume
from uuid import uuid4

from src.admin.history_tracker import HistoryTracker, get_history_tracker
from src.admin.schemas import ConfigType, ConfigDiff


# ========== Custom Strategies ==========

def config_value_strategy():
    """Strategy for generating configuration values."""
    return st.fixed_dictionaries({
        'name': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        'enabled': st.booleans(),
        'value': st.one_of(
            st.integers(min_value=0, max_value=10000),
            st.text(min_size=0, max_size=100),
            st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
        ),
        'settings': st.fixed_dictionaries({
            'option1': st.booleans(),
            'option2': st.integers(min_value=0, max_value=100),
        }),
    })


def config_type_strategy():
    """Strategy for generating config types."""
    return st.sampled_from([t.value for t in ConfigType])


def user_id_strategy():
    """Strategy for generating user IDs."""
    return st.uuids().map(str)


class TestHistoryTrackerProperties:
    """Property-based tests for HistoryTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create a fresh tracker for each test."""
        tracker = HistoryTracker()
        tracker.clear_in_memory_history()
        return tracker
    
    # ========== Property 4: 配置回滚一致性 ==========
    
    @given(
        config_type=config_type_strategy(),
        old_value=config_value_strategy(),
        new_value=config_value_strategy(),
        user_id=user_id_strategy(),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_rollback_restores_old_value(
        self,
        config_type: str,
        old_value: dict,
        new_value: dict,
        user_id: str,
    ):
        """
        **Feature: admin-configuration, Property 4: 配置回滚一致性**
        **Validates: Requirements 6.4**
        
        For any configuration rollback, the rolled-back value should
        match the old_value from the history record.
        """
        # Skip if old and new are the same (no meaningful change)
        assume(old_value != new_value)
        
        tracker = HistoryTracker()
        tracker.clear_in_memory_history()
        
        # Record a change
        history = await tracker.record_change(
            config_type=config_type,
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
            user_name="Test User",
        )
        
        # Rollback to the old value
        rollback_user_id = str(uuid4())
        rolled_back = await tracker.rollback(
            history_id=history.id,
            user_id=rollback_user_id,
            user_name="Rollback User",
        )
        
        # Verify rollback value matches old_value (with sanitization)
        assert rolled_back is not None, "Rollback should return a value"
        
        # Check that the rolled back value matches the sanitized old value
        sanitized_old = tracker._sanitize_for_history(old_value)
        assert rolled_back == sanitized_old, (
            f"Rolled back value should match old value: "
            f"got {rolled_back}, expected {sanitized_old}"
        )
    
    # ========== Property 5: 配置历史完整性 ==========
    
    @given(
        config_type=config_type_strategy(),
        old_value=config_value_strategy(),
        new_value=config_value_strategy(),
        user_id=user_id_strategy(),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_history_records_complete_change(
        self,
        config_type: str,
        old_value: dict,
        new_value: dict,
        user_id: str,
    ):
        """
        **Feature: admin-configuration, Property 5: 配置历史完整性**
        **Validates: Requirements 6.2**
        
        For any configuration change, the history record should contain
        complete information: config_type, old_value, new_value, user_id, timestamp.
        """
        tracker = HistoryTracker()
        tracker.clear_in_memory_history()
        
        before_time = datetime.utcnow()
        
        # Record a change
        history = await tracker.record_change(
            config_type=config_type,
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
            user_name="Test User",
        )
        
        after_time = datetime.utcnow()
        
        # Verify all required fields are present
        assert history.id is not None, "History should have an ID"
        assert history.config_type.value == config_type, "Config type should match"
        assert history.user_id == user_id, "User ID should match"
        assert history.user_name == "Test User", "User name should match"
        assert history.created_at is not None, "Created_at should be set"
        
        # Verify timestamp is reasonable
        assert before_time <= history.created_at <= after_time, (
            "Created_at should be between before and after times"
        )
        
        # Verify values are recorded (sanitized)
        sanitized_old = tracker._sanitize_for_history(old_value)
        sanitized_new = tracker._sanitize_for_history(new_value)
        assert history.old_value == sanitized_old, "Old value should match (sanitized)"
        assert history.new_value == sanitized_new, "New value should match (sanitized)"
    
    @given(
        num_changes=st.integers(min_value=1, max_value=10),
        config_type=config_type_strategy(),
        user_id=user_id_strategy(),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_history_preserves_all_changes(
        self,
        num_changes: int,
        config_type: str,
        user_id: str,
    ):
        """
        **Feature: admin-configuration, Property 5: 配置历史完整性**
        **Validates: Requirements 6.2**
        
        All configuration changes should be preserved in history.
        """
        tracker = HistoryTracker()
        tracker.clear_in_memory_history()
        
        # Record multiple changes
        recorded_ids = []
        for i in range(num_changes):
            history = await tracker.record_change(
                config_type=config_type,
                old_value={"version": i},
                new_value={"version": i + 1},
                user_id=user_id,
                user_name=f"User {i}",
            )
            recorded_ids.append(history.id)
        
        # Retrieve history
        history_list = await tracker.get_history(config_type=config_type)
        
        # Verify all changes are recorded
        assert len(history_list) == num_changes, (
            f"Should have {num_changes} history records, got {len(history_list)}"
        )
        
        # Verify all IDs are present
        retrieved_ids = [h.id for h in history_list]
        for rid in recorded_ids:
            assert rid in retrieved_ids, f"History ID {rid} should be in retrieved list"
    
    # ========== Diff Calculation Properties ==========
    
    @given(
        old_value=config_value_strategy(),
        new_value=config_value_strategy(),
    )
    @settings(max_examples=100)
    def test_diff_captures_all_changes(
        self,
        old_value: dict,
        new_value: dict,
    ):
        """
        Diff should capture all added, removed, and modified fields.
        """
        tracker = HistoryTracker()
        
        diff = tracker.get_diff(old_value, new_value)
        
        # Verify diff structure
        assert isinstance(diff, ConfigDiff)
        assert isinstance(diff.added, dict)
        assert isinstance(diff.removed, dict)
        assert isinstance(diff.modified, dict)
        
        # Verify added fields are in new but not old
        for key in diff.added:
            assert key in new_value, f"Added key {key} should be in new_value"
            assert key not in old_value, f"Added key {key} should not be in old_value"
        
        # Verify removed fields are in old but not new
        for key in diff.removed:
            assert key in old_value, f"Removed key {key} should be in old_value"
            assert key not in new_value, f"Removed key {key} should not be in new_value"
        
        # Verify modified fields are in both with different values
        for key in diff.modified:
            assert key in old_value, f"Modified key {key} should be in old_value"
            assert key in new_value, f"Modified key {key} should be in new_value"
            assert old_value[key] != new_value[key], (
                f"Modified key {key} should have different values"
            )
    
    @given(config_value=config_value_strategy())
    @settings(max_examples=100)
    def test_diff_from_none_shows_all_added(self, config_value: dict):
        """
        Diff from None should show all fields as added.
        """
        tracker = HistoryTracker()
        
        diff = tracker.get_diff(None, config_value)
        
        assert diff.added == config_value, "All fields should be added"
        assert diff.removed == {}, "No fields should be removed"
        assert diff.modified == {}, "No fields should be modified"
    
    @given(config_value=config_value_strategy())
    @settings(max_examples=100)
    def test_diff_identical_values_empty(self, config_value: dict):
        """
        Diff of identical values should be empty.
        """
        tracker = HistoryTracker()
        
        diff = tracker.get_diff(config_value, config_value.copy())
        
        assert diff.added == {}, "No fields should be added"
        assert diff.removed == {}, "No fields should be removed"
        assert diff.modified == {}, "No fields should be modified"


class TestHistoryTrackerUnit:
    """Unit tests for HistoryTracker edge cases."""
    
    @pytest.fixture
    def tracker(self):
        """Create a fresh tracker for each test."""
        tracker = HistoryTracker()
        tracker.clear_in_memory_history()
        return tracker
    
    @pytest.mark.asyncio
    async def test_record_change_with_none_old_value(self, tracker):
        """Recording a change with None old_value should work (new config)."""
        history = await tracker.record_change(
            config_type=ConfigType.LLM,
            old_value=None,
            new_value={"name": "test"},
            user_id="user-1",
            user_name="Test User",
        )
        
        assert history.old_value is None
        assert history.new_value == {"name": "test"}
    
    @pytest.mark.asyncio
    async def test_record_change_sanitizes_sensitive_fields(self, tracker):
        """Sensitive fields should be sanitized in history."""
        history = await tracker.record_change(
            config_type=ConfigType.DATABASE,
            old_value={"password": "secret123", "name": "db1"},
            new_value={"password": "newsecret", "name": "db1"},
            user_id="user-1",
            user_name="Test User",
        )
        
        assert history.old_value["password"] == "[REDACTED]"
        assert history.new_value["password"] == "[REDACTED]"
        assert history.old_value["name"] == "db1"
        assert history.new_value["name"] == "db1"
    
    @pytest.mark.asyncio
    async def test_get_history_filters_by_config_type(self, tracker):
        """History should be filterable by config type."""
        # Record changes for different types
        await tracker.record_change(
            config_type=ConfigType.LLM,
            old_value=None,
            new_value={"name": "llm1"},
            user_id="user-1",
        )
        await tracker.record_change(
            config_type=ConfigType.DATABASE,
            old_value=None,
            new_value={"name": "db1"},
            user_id="user-1",
        )
        
        # Filter by LLM type
        llm_history = await tracker.get_history(config_type=ConfigType.LLM)
        assert len(llm_history) == 1
        assert llm_history[0].config_type == ConfigType.LLM
        
        # Filter by DATABASE type
        db_history = await tracker.get_history(config_type=ConfigType.DATABASE)
        assert len(db_history) == 1
        assert db_history[0].config_type == ConfigType.DATABASE
    
    @pytest.mark.asyncio
    async def test_get_history_filters_by_user_id(self, tracker):
        """History should be filterable by user ID."""
        await tracker.record_change(
            config_type=ConfigType.LLM,
            old_value=None,
            new_value={"name": "config1"},
            user_id="user-1",
        )
        await tracker.record_change(
            config_type=ConfigType.LLM,
            old_value=None,
            new_value={"name": "config2"},
            user_id="user-2",
        )
        
        user1_history = await tracker.get_history(user_id="user-1")
        assert len(user1_history) == 1
        assert user1_history[0].user_id == "user-1"
    
    @pytest.mark.asyncio
    async def test_get_history_filters_by_time_range(self, tracker):
        """History should be filterable by time range."""
        # Record a change
        await tracker.record_change(
            config_type=ConfigType.LLM,
            old_value=None,
            new_value={"name": "config1"},
            user_id="user-1",
        )
        
        now = datetime.utcnow()
        
        # Filter with time range that includes the change
        history = await tracker.get_history(
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        assert len(history) == 1
        
        # Filter with time range that excludes the change
        history = await tracker.get_history(
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )
        assert len(history) == 0
    
    @pytest.mark.asyncio
    async def test_get_history_pagination(self, tracker):
        """History should support pagination."""
        # Record multiple changes
        for i in range(5):
            await tracker.record_change(
                config_type=ConfigType.LLM,
                old_value=None,
                new_value={"name": f"config{i}"},
                user_id="user-1",
            )
        
        # Get first page
        page1 = await tracker.get_history(limit=2, offset=0)
        assert len(page1) == 2
        
        # Get second page
        page2 = await tracker.get_history(limit=2, offset=2)
        assert len(page2) == 2
        
        # Get third page (partial)
        page3 = await tracker.get_history(limit=2, offset=4)
        assert len(page3) == 1
        
        # Verify no overlap
        all_ids = [h.id for h in page1 + page2 + page3]
        assert len(all_ids) == len(set(all_ids)), "Pages should not overlap"
    
    @pytest.mark.asyncio
    async def test_get_history_by_id(self, tracker):
        """Should be able to retrieve specific history by ID."""
        history = await tracker.record_change(
            config_type=ConfigType.LLM,
            old_value=None,
            new_value={"name": "test"},
            user_id="user-1",
        )
        
        retrieved = await tracker.get_history_by_id(history.id)
        assert retrieved is not None
        assert retrieved.id == history.id
        assert retrieved.new_value == history.new_value
    
    @pytest.mark.asyncio
    async def test_get_history_by_id_not_found(self, tracker):
        """Should return None for non-existent history ID."""
        retrieved = await tracker.get_history_by_id("non-existent-id")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_rollback_not_found(self, tracker):
        """Rollback should return None for non-existent history."""
        result = await tracker.rollback(
            history_id="non-existent-id",
            user_id="user-1",
        )
        assert result is None
    
    @pytest.mark.asyncio
    async def test_rollback_creates_new_history(self, tracker):
        """Rollback should create a new history record."""
        # Record initial change
        history = await tracker.record_change(
            config_type=ConfigType.LLM,
            old_value={"version": 1},
            new_value={"version": 2},
            user_id="user-1",
        )
        
        # Perform rollback
        await tracker.rollback(
            history_id=history.id,
            user_id="user-2",
            user_name="Rollback User",
        )
        
        # Check that a new history record was created
        all_history = await tracker.get_history(config_type=ConfigType.LLM)
        assert len(all_history) == 2
        
        # The most recent should be the rollback
        latest = all_history[0]
        assert latest.user_id == "user-2"
        assert latest.user_name == "Rollback User"
    
    @pytest.mark.asyncio
    async def test_get_diff_by_history_id(self, tracker):
        """Should be able to get diff for a specific history record."""
        history = await tracker.record_change(
            config_type=ConfigType.LLM,
            old_value={"name": "old", "value": 1},
            new_value={"name": "new", "value": 1, "extra": True},
            user_id="user-1",
        )
        
        diff = await tracker.get_diff_by_history_id(history.id)
        assert diff is not None
        assert "extra" in diff.added
        assert "name" in diff.modified
    
    @pytest.mark.asyncio
    async def test_get_diff_by_history_id_not_found(self, tracker):
        """Should return None for non-existent history ID."""
        diff = await tracker.get_diff_by_history_id("non-existent-id")
        assert diff is None
    
    def test_get_history_tracker_singleton(self):
        """get_history_tracker should return the same instance."""
        tracker1 = get_history_tracker()
        tracker2 = get_history_tracker()
        assert tracker1 is tracker2


class TestHistoryTrackerSanitization:
    """Tests for sensitive data sanitization."""
    
    @pytest.fixture
    def tracker(self):
        """Create a fresh tracker for each test."""
        tracker = HistoryTracker()
        tracker.clear_in_memory_history()
        return tracker
    
    @pytest.mark.parametrize("sensitive_field", [
        "password",
        "api_key",
        "secret",
        "token",
        "password_encrypted",
        "api_key_encrypted",
    ])
    @pytest.mark.asyncio
    async def test_sanitizes_sensitive_field(self, tracker, sensitive_field):
        """Each sensitive field should be sanitized."""
        history = await tracker.record_change(
            config_type=ConfigType.DATABASE,
            old_value={sensitive_field: "sensitive_value"},
            new_value={sensitive_field: "new_sensitive_value"},
            user_id="user-1",
        )
        
        assert history.old_value[sensitive_field] == "[REDACTED]"
        assert history.new_value[sensitive_field] == "[REDACTED]"
    
    @pytest.mark.asyncio
    async def test_preserves_non_sensitive_fields(self, tracker):
        """Non-sensitive fields should be preserved."""
        history = await tracker.record_change(
            config_type=ConfigType.LLM,
            old_value={"name": "test", "model": "gpt-4", "temperature": 0.7},
            new_value={"name": "test2", "model": "gpt-4", "temperature": 0.8},
            user_id="user-1",
        )
        
        assert history.old_value["name"] == "test"
        assert history.old_value["model"] == "gpt-4"
        assert history.old_value["temperature"] == 0.7
        assert history.new_value["name"] == "test2"
        assert history.new_value["temperature"] == 0.8
