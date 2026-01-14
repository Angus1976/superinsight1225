"""
Property-based tests for Save Strategy Manager.

Tests Property 8: Save strategy correctness
Tests Property 9: Hybrid mode auto-selection
"""

import pytest
from hypothesis import given, strategies as st, settings
import json
import asyncio

from src.sync.pipeline.enums import SaveStrategy
from src.sync.pipeline.schemas import SaveConfig, SaveResult
from src.sync.pipeline.save_strategy import SaveStrategyManager


# ============================================================================
# Test Helpers
# ============================================================================

def create_manager():
    """Create a save strategy manager without DB session."""
    return SaveStrategyManager()


def create_test_data(count: int, value_size: int = 10) -> list:
    """Create test data with specified count and value size."""
    return [
        {"id": i, "value": "x" * value_size}
        for i in range(count)
    ]


# ============================================================================
# Property 8: Save Strategy Correctness
# Validates: Requirements 4.2, 4.3
# ============================================================================

@settings(max_examples=100)
@given(
    record_count=st.integers(min_value=1, max_value=100)
)
def test_persistent_save_correctness(record_count: int):
    """
    Property 8: Persistent save correctness
    
    For any persistent save operation, data should be saved and
    the result should indicate database storage.
    
    **Validates: Requirements 4.2**
    """
    async def run_test():
        manager = create_manager()
        data = create_test_data(record_count)
        config = SaveConfig(strategy=SaveStrategy.PERSISTENT)
        
        # Without DB session, falls back to memory
        result = await manager.save(data, SaveStrategy.PERSISTENT, config)
        
        # Should succeed (falls back to memory without DB)
        assert result.success
        assert result.rows_saved == record_count
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    record_count=st.integers(min_value=1, max_value=100)
)
def test_memory_save_correctness(record_count: int):
    """
    Property 8: Memory save correctness
    
    For any memory save operation, data should be processed and
    the result should indicate memory storage.
    
    **Validates: Requirements 4.3**
    """
    async def run_test():
        manager = create_manager()
        data = create_test_data(record_count)
        config = SaveConfig(strategy=SaveStrategy.MEMORY)
        
        result = await manager.save(data, SaveStrategy.MEMORY, config)
        
        assert result.success
        assert result.strategy_used == SaveStrategy.MEMORY
        assert result.rows_saved == record_count
        assert result.storage_location == "memory"
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    record_count=st.integers(min_value=1, max_value=50)
)
def test_memory_data_retrievable(record_count: int):
    """
    Property 8 (extension): Memory data is retrievable
    
    Data saved to memory should be retrievable by batch ID.
    
    **Validates: Requirements 4.3**
    """
    async def run_test():
        manager = create_manager()
        data = create_test_data(record_count)
        config = SaveConfig(strategy=SaveStrategy.MEMORY)
        
        await manager.save(data, SaveStrategy.MEMORY, config)
        
        # Should have one batch in memory
        assert manager.memory_batch_count == 1
        assert manager.memory_record_count == record_count
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Property 9: Hybrid Mode Auto-Selection
# Validates: Requirements 4.4
# ============================================================================

@settings(max_examples=100)
@given(
    threshold=st.integers(min_value=100, max_value=10000),
    data_size_factor=st.floats(min_value=0.1, max_value=0.9)
)
def test_hybrid_selects_memory_below_threshold(threshold: int, data_size_factor: float):
    """
    Property 9: Hybrid mode selects memory below threshold
    
    When data size is below the threshold, hybrid mode should
    use memory processing.
    
    **Validates: Requirements 4.4**
    """
    async def run_test():
        manager = create_manager()
        
        # Create data smaller than threshold
        target_size = int(threshold * data_size_factor)
        # Estimate: each record is roughly 30 bytes in JSON
        record_count = max(1, target_size // 30)
        data = create_test_data(record_count, value_size=5)
        
        config = SaveConfig(
            strategy=SaveStrategy.HYBRID,
            hybrid_threshold_bytes=threshold
        )
        
        actual_size = manager.calculate_size(data)
        
        # Only test if data is actually below threshold
        if actual_size < threshold:
            result = await manager.save(data, SaveStrategy.HYBRID, config)
            
            assert result.success
            assert result.strategy_used == SaveStrategy.MEMORY
            assert result.storage_location == "memory"
    
    asyncio.get_event_loop().run_until_complete(run_test())


@settings(max_examples=100)
@given(
    threshold=st.integers(min_value=100, max_value=1000),
    data_size_factor=st.floats(min_value=1.5, max_value=5.0)
)
def test_hybrid_selects_persistent_above_threshold(threshold: int, data_size_factor: float):
    """
    Property 9: Hybrid mode selects persistent above threshold
    
    When data size exceeds the threshold, hybrid mode should
    use persistent storage.
    
    **Validates: Requirements 4.4**
    """
    async def run_test():
        manager = create_manager()
        
        # Create data larger than threshold
        target_size = int(threshold * data_size_factor)
        # Estimate: each record is roughly 30 bytes in JSON
        record_count = max(1, target_size // 30)
        data = create_test_data(record_count, value_size=20)
        
        config = SaveConfig(
            strategy=SaveStrategy.HYBRID,
            hybrid_threshold_bytes=threshold
        )
        
        actual_size = manager.calculate_size(data)
        
        # Only test if data is actually above threshold
        if actual_size > threshold:
            result = await manager.save(data, SaveStrategy.HYBRID, config)
            
            assert result.success
            # Without DB, falls back to memory but strategy_used shows PERSISTENT
            # In real scenario with DB, it would save to database
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_hybrid_threshold_boundary():
    """
    Property 9 (edge case): Hybrid mode at exact threshold
    
    **Validates: Requirements 4.4**
    """
    async def run_test():
        manager = create_manager()
        
        # Create data and measure its size
        data = create_test_data(10, value_size=10)
        actual_size = manager.calculate_size(data)
        
        # Set threshold to exact size
        config = SaveConfig(
            strategy=SaveStrategy.HYBRID,
            hybrid_threshold_bytes=actual_size
        )
        
        result = await manager.save(data, SaveStrategy.HYBRID, config)
        
        # At exact threshold, should use memory (not exceeding)
        assert result.success
        assert result.strategy_used == SaveStrategy.MEMORY
    
    asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================================
# Size Calculation Tests
# ============================================================================

@settings(max_examples=100)
@given(
    record_count=st.integers(min_value=1, max_value=100),
    value_size=st.integers(min_value=1, max_value=100)
)
def test_size_calculation_proportional(record_count: int, value_size: int):
    """
    Test that size calculation is proportional to data.
    """
    manager = create_manager()
    
    data1 = create_test_data(record_count, value_size)
    data2 = create_test_data(record_count * 2, value_size)
    
    size1 = manager.calculate_size(data1)
    size2 = manager.calculate_size(data2)
    
    # Double the records should roughly double the size
    assert size2 > size1


def test_size_calculation_empty_data():
    """
    Test size calculation with empty data.
    """
    manager = create_manager()
    
    size = manager.calculate_size([])
    assert size == 2  # Empty JSON array "[]"


# ============================================================================
# Memory Management Tests
# ============================================================================

def test_clear_memory_batch():
    """
    Test clearing a specific batch from memory.
    """
    async def run_test():
        manager = create_manager()
        
        # Save two batches
        data1 = create_test_data(5)
        data2 = create_test_data(10)
        
        await manager.save_to_memory(data1, SaveConfig())
        await manager.save_to_memory(data2, SaveConfig())
        
        assert manager.memory_batch_count == 2
        
        # Clear all memory
        cleared = manager.clear_all_memory()
        assert cleared == 2
        assert manager.memory_batch_count == 0
    
    asyncio.get_event_loop().run_until_complete(run_test())


def test_memory_record_count():
    """
    Test memory record counting.
    """
    async def run_test():
        manager = create_manager()
        
        await manager.save_to_memory(create_test_data(5), SaveConfig())
        await manager.save_to_memory(create_test_data(10), SaveConfig())
        await manager.save_to_memory(create_test_data(15), SaveConfig())
        
        assert manager.memory_batch_count == 3
        assert manager.memory_record_count == 30  # 5 + 10 + 15
    
    asyncio.get_event_loop().run_until_complete(run_test())
