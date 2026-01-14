"""
Property-based tests for Data Puller.

Tests Property 4: Incremental pull checkpoint persistence
Tests Property 5: Pull retry mechanism
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from src.sync.pipeline.schemas import (
    DataSourceConfig,
    DataPage,
    PullConfig,
    Checkpoint,
    PullResult,
)
from src.sync.pipeline.enums import DatabaseType
from src.sync.pipeline.checkpoint_store import CheckpointStore
from src.sync.pipeline.data_puller import DataPuller, CronExpressionError


# ============================================================================
# Test Helpers
# ============================================================================

def create_mock_data_reader(pages: List[DataPage]):
    """Create a mock data reader that returns specified pages."""
    reader = MagicMock()
    reader.connect = AsyncMock()
    reader.disconnect = AsyncMock()
    
    async def mock_read(*args, **kwargs):
        for page in pages:
            yield page
    
    reader.read_by_query = mock_read
    return reader


def create_sample_config():
    """Create a sample data source configuration."""
    return DataSourceConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        database="test_db",
        username="test_user",
        password="test_pass"
    )


def create_pull_config(incremental: bool = True):
    """Create a sample pull configuration."""
    return PullConfig(
        cron_expression="0 * * * *",
        incremental=incremental,
        checkpoint_field="updated_at",
        table_name="test_table",
        page_size=100
    )


# ============================================================================
# Property 4: Incremental Pull Checkpoint Persistence
# Validates: Requirements 2.2, 2.3
# ============================================================================

@settings(max_examples=100)
@given(
    source_id=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
        min_size=1,
        max_size=20
    ),
    last_value=st.integers(min_value=1, max_value=1000000)
)
def test_checkpoint_persistence(source_id: str, last_value: int):
    """
    Property 4: Incremental pull checkpoint persistence
    
    For any incremental pull operation, the checkpoint should be saved
    and retrievable for the next pull.
    
    **Validates: Requirements 2.2, 2.3**
    """
    async def run_test():
        checkpoint_store = CheckpointStore()
        
        # Save checkpoint
        checkpoint = Checkpoint(
            source_id=source_id,
            last_value=last_value,
            last_pull_at=datetime.utcnow(),
            rows_pulled=100
        )
        await checkpoint_store.save(checkpoint)
        
        # Retrieve checkpoint
        retrieved = await checkpoint_store.get(source_id)
        
        assert retrieved is not None, "Checkpoint should be retrievable"
        assert retrieved.source_id == source_id
        assert retrieved.last_value == last_value
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    initial_value=st.integers(min_value=1, max_value=500000),
    new_value=st.integers(min_value=500001, max_value=1000000)
)
def test_checkpoint_update(initial_value: int, new_value: int):
    """
    Property 4 (extension): Checkpoint updates correctly
    
    When a new pull completes, the checkpoint should be updated
    with the new last value.
    
    **Validates: Requirements 2.2, 2.3**
    """
    async def run_test():
        checkpoint_store = CheckpointStore()
        source_id = "test_source"
        
        # Save initial checkpoint
        initial_checkpoint = Checkpoint(
            source_id=source_id,
            last_value=initial_value,
            last_pull_at=datetime.utcnow(),
            rows_pulled=100
        )
        await checkpoint_store.save(initial_checkpoint)
        
        # Update checkpoint
        updated = await checkpoint_store.update_last_value(
            source_id, new_value, rows_pulled=50
        )
        
        assert updated is not None
        assert updated.last_value == new_value
        assert updated.rows_pulled == 150  # 100 + 50
        
        # Verify persistence
        retrieved = await checkpoint_store.get(source_id)
        assert retrieved.last_value == new_value
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    num_pulls=st.integers(min_value=2, max_value=10)
)
def test_checkpoint_incremental_accumulation(num_pulls: int):
    """
    Property 4 (extension): Checkpoint accumulates rows correctly
    
    After multiple incremental pulls, the total rows_pulled should
    be the sum of all individual pulls.
    
    **Validates: Requirements 2.2, 2.3**
    """
    async def run_test():
        checkpoint_store = CheckpointStore()
        source_id = "test_source"
        
        total_rows = 0
        for i in range(num_pulls):
            rows_in_pull = (i + 1) * 10
            total_rows += rows_in_pull
            
            await checkpoint_store.update_last_value(
                source_id, i + 1, rows_pulled=rows_in_pull
            )
        
        checkpoint = await checkpoint_store.get(source_id)
        assert checkpoint.rows_pulled == total_rows
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Property 5: Pull Retry Mechanism
# Validates: Requirements 2.5
# ============================================================================

@settings(max_examples=100)
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    fail_count=st.integers(min_value=0, max_value=5)
)
def test_retry_mechanism(max_retries: int, fail_count: int):
    """
    Property 5: Pull retry mechanism
    
    For any failed pull operation, the system should retry up to
    max_retries times before giving up.
    
    **Validates: Requirements 2.5**
    """
    async def run_test():
        checkpoint_store = CheckpointStore()
        
        # Track call count
        call_count = [0]
        
        # Create mock reader that fails first N times
        async def mock_read(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= fail_count:
                raise Exception(f"Simulated failure {call_count[0]}")
            # Return empty page on success
            yield DataPage(
                page_number=0,
                rows=[{"id": 1, "updated_at": 123}],
                row_count=1,
                has_more=False
            )
        
        reader = MagicMock()
        reader.connect = AsyncMock()
        reader.disconnect = AsyncMock()
        reader.read_by_query = mock_read
        
        puller = DataPuller(reader, checkpoint_store)
        
        # Patch asyncio.sleep to speed up test
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await puller.pull_with_retry(
                "test_source",
                create_pull_config(),
                create_sample_config(),
                max_retries=max_retries
            )
        
        if fail_count <= max_retries:
            # Should succeed after retries
            assert result.success, f"Should succeed after {fail_count} failures with {max_retries} retries"
            assert result.retries_used == fail_count
        else:
            # Should fail after exhausting retries
            assert not result.success, f"Should fail after {max_retries} retries"
            assert result.retries_used == max_retries + 1
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_retry_records_attempt_count():
    """
    Property 5 (extension): Retry count is recorded
    
    The result should include the number of retries used.
    
    **Validates: Requirements 2.5**
    """
    async def run_test():
        checkpoint_store = CheckpointStore()
        
        # Create mock reader that succeeds immediately
        async def mock_read(*args, **kwargs):
            yield DataPage(
                page_number=0,
                rows=[{"id": 1, "updated_at": 123}],
                row_count=1,
                has_more=False
            )
        
        reader = MagicMock()
        reader.connect = AsyncMock()
        reader.disconnect = AsyncMock()
        reader.read_by_query = mock_read
        
        puller = DataPuller(reader, checkpoint_store)
        
        result = await puller.pull_with_retry(
            "test_source",
            create_pull_config(),
            create_sample_config(),
            max_retries=3
        )
        
        assert result.success
        assert result.retries_used == 0  # No retries needed
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Cron Expression Validation Tests
# ============================================================================

@settings(max_examples=100)
@given(
    minute=st.integers(min_value=0, max_value=59),
    hour=st.integers(min_value=0, max_value=23),
    day=st.integers(min_value=1, max_value=31),
    month=st.integers(min_value=1, max_value=12),
    weekday=st.integers(min_value=0, max_value=6)
)
def test_valid_cron_expressions(minute, hour, day, month, weekday):
    """
    Test that valid cron expressions are accepted.
    
    **Validates: Requirements 2.1, 2.4**
    """
    checkpoint_store = CheckpointStore()
    reader = MagicMock()
    puller = DataPuller(reader, checkpoint_store)
    
    cron = f"{minute} {hour} {day} {month} {weekday}"
    
    # Should not raise
    puller._validate_cron_expression(cron)


def test_invalid_cron_expressions():
    """
    Test that invalid cron expressions are rejected.
    
    **Validates: Requirements 2.1, 2.4**
    """
    checkpoint_store = CheckpointStore()
    reader = MagicMock()
    puller = DataPuller(reader, checkpoint_store)
    
    invalid_expressions = [
        "60 * * * *",      # minute > 59
        "* 24 * * *",      # hour > 23
        "* * 32 * *",      # day > 31
        "* * * 13 *",      # month > 12
        "* * * * 7",       # weekday > 6
        "* * * *",         # too few fields
        "* * * * * * *",   # too many fields
    ]
    
    for expr in invalid_expressions:
        with pytest.raises(CronExpressionError):
            puller._validate_cron_expression(expr)


def test_cron_special_characters():
    """
    Test cron expressions with special characters.
    
    **Validates: Requirements 2.1, 2.4**
    """
    checkpoint_store = CheckpointStore()
    reader = MagicMock()
    puller = DataPuller(reader, checkpoint_store)
    
    valid_expressions = [
        "*/5 * * * *",     # every 5 minutes
        "0 */2 * * *",     # every 2 hours
        "0 0 1-15 * *",    # days 1-15
        "0 0 * * 1,3,5",   # Mon, Wed, Fri
        "0 0 * * *",       # daily at midnight
    ]
    
    for expr in valid_expressions:
        # Should not raise
        puller._validate_cron_expression(expr)
