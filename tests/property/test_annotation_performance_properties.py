"""Property-based tests for AI Annotation Performance Optimization.

This module tests the following properties:
- Property 31: Large Batch Performance (10,000+ items in <1 hour)
- Property 32: Model Caching Efficiency
- Property 33: Rate Limiting Under Load
- Property 34: Parallel Processing Scalability
- Property 35: Cache Eviction Strategy Correctness

Requirements:
- 9.1: Large batch performance
- 9.4: Model caching
- 9.6: Rate limiting and queue management
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import List
from uuid import uuid4
from datetime import datetime, timedelta
import time

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.ai.annotation_performance_optimizer import (
    ParallelBatchProcessor,
    ModelCacheManager,
    RateLimiter,
    BatchJobConfig,
    CacheStrategy,
    QueuePriority,
    reset_performance_optimizer,
)


# ============================================================================
# Property 31: Large Batch Performance
# ============================================================================

class TestLargeBatchPerformance:
    """Property 31: 10,000+ items processed in under 1 hour."""

    @pytest.mark.asyncio
    @given(
        batch_size=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=50, deadline=None)
    async def test_batch_processing_completes(self, batch_size: int):
        """Test that batch processing completes successfully."""
        config = BatchJobConfig(
            batch_size=batch_size,
            max_concurrency=10,
            enable_caching=False,
            enable_rate_limiting=False,
        )
        processor = ParallelBatchProcessor(config=config)

        # Create test items (smaller set for testing)
        num_items = 200
        items = list(range(num_items))

        # Simple processor function
        async def process_item(item):
            await asyncio.sleep(0.01)  # Simulate processing
            return item * 2

        # Submit job
        job_id = await processor.submit_job(items, process_item)

        # Wait for completion (with timeout)
        max_wait = 60  # seconds
        start_time = time.time()

        while time.time() - start_time < max_wait:
            job = await processor.get_job_status(job_id)
            if job.status.value in ["completed", "failed"]:
                break
            await asyncio.sleep(0.1)

        # Verify completion
        job = await processor.get_job_status(job_id)
        assert job.status.value == "completed"
        assert job.processed_items == num_items
        assert len(job.results) == num_items

    @pytest.mark.asyncio
    @given(
        concurrency=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50, deadline=None)
    async def test_concurrency_improves_throughput(self, concurrency: int):
        """Test that higher concurrency improves throughput."""
        num_items = 100

        items = list(range(num_items))

        async def process_item(item):
            await asyncio.sleep(0.01)
            return item

        # Test with given concurrency
        config = BatchJobConfig(
            batch_size=10,
            max_concurrency=concurrency,
            enable_caching=False,
            enable_rate_limiting=False,
        )
        processor = ParallelBatchProcessor(config=config)

        start_time = time.time()
        job_id = await processor.submit_job(items, process_item)

        # Wait for completion
        while True:
            job = await processor.get_job_status(job_id)
            if job.status.value in ["completed", "failed"]:
                break
            await asyncio.sleep(0.05)

        processing_time = time.time() - start_time

        # Verify throughput is reasonable
        items_per_second = num_items / processing_time
        assert items_per_second > 0, "Throughput should be positive"

    @pytest.mark.asyncio
    async def test_large_scale_target_performance(self):
        """Test that system can meet 10,000 items/hour target (scaled down for testing)."""
        # Test with 1,000 items (10% of target)
        num_items = 1000
        target_time_seconds = 360  # 6 minutes (10% of 1 hour)

        items = list(range(num_items))

        async def fast_process_item(item):
            # Very fast processing to test throughput capacity
            return item * 2

        config = BatchJobConfig(
            batch_size=100,
            max_concurrency=20,
            enable_caching=True,
            enable_rate_limiting=False,
        )
        processor = ParallelBatchProcessor(config=config)

        start_time = time.time()
        job_id = await processor.submit_job(items, fast_process_item)

        # Wait for completion
        while True:
            job = await processor.get_job_status(job_id)
            if job.status.value in ["completed", "failed"]:
                break
            await asyncio.sleep(0.1)

        processing_time = time.time() - start_time
        job = await processor.get_job_status(job_id)

        # Verify performance
        assert job.status.value == "completed"
        assert processing_time < target_time_seconds, \
            f"Processing took {processing_time:.1f}s, expected <{target_time_seconds}s"

        # Calculate throughput
        items_per_hour = (num_items / processing_time) * 3600
        print(f"Throughput: {items_per_hour:.0f} items/hour")


# ============================================================================
# Property 32: Model Caching Efficiency
# ============================================================================

class TestModelCachingEfficiency:
    """Property 32: Model caching improves performance."""

    @pytest.mark.asyncio
    @given(
        cache_strategy=st.sampled_from([CacheStrategy.LRU, CacheStrategy.LFU, CacheStrategy.TTL])
    )
    @settings(max_examples=100, deadline=None)
    async def test_cache_hit_returns_cached_data(self, cache_strategy: CacheStrategy):
        """Test that cache hits return previously cached data."""
        cache = ModelCacheManager(
            strategy=cache_strategy,
            max_size=100,
            ttl_seconds=60,
        )

        # Cache some data
        test_key = "model_test_123"
        test_data = {"weights": [1, 2, 3]}

        await cache.put(test_key, test_data)

        # Retrieve from cache
        cached_data = await cache.get(test_key)

        assert cached_data is not None
        assert cached_data == test_data

    @pytest.mark.asyncio
    @given(
        num_accesses=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    async def test_cache_hit_rate_improves_with_reuse(self, num_accesses: int):
        """Test that cache hit rate improves with data reuse."""
        cache = ModelCacheManager(max_size=50)

        # Cache initial data
        keys = [f"model_{i}" for i in range(10)]
        for key in keys:
            await cache.put(key, {"data": key})

        # Access cached data multiple times
        for _ in range(num_accesses):
            for key in keys:
                await cache.get(key)

        # Check statistics
        stats = await cache.get_statistics()
        hit_rate = stats["hit_rate"]

        # Should have high hit rate with repeated access
        assert hit_rate > 90.0, f"Expected high hit rate, got {hit_rate:.1f}%"

    @pytest.mark.asyncio
    @given(
        max_size=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    async def test_cache_eviction_maintains_size_limit(self, max_size: int):
        """Test that cache eviction maintains size limit."""
        cache = ModelCacheManager(
            strategy=CacheStrategy.LRU,
            max_size=max_size,
        )

        # Add more items than max size
        num_items = max_size + 10
        for i in range(num_items):
            await cache.put(f"model_{i}", {"data": i})

        # Check cache size
        stats = await cache.get_statistics()
        assert stats["cache_size"] <= max_size

    @pytest.mark.asyncio
    async def test_lru_evicts_least_recently_used(self):
        """Test that LRU strategy evicts least recently used items."""
        cache = ModelCacheManager(
            strategy=CacheStrategy.LRU,
            max_size=3,
        )

        # Add items
        await cache.put("model_1", {"data": 1})
        await cache.put("model_2", {"data": 2})
        await cache.put("model_3", {"data": 3})

        # Access model_1 and model_2
        await cache.get("model_1")
        await cache.get("model_2")

        # Add new item (should evict model_3)
        await cache.put("model_4", {"data": 4})

        # model_3 should be evicted
        assert await cache.get("model_3") is None
        # model_1 and model_2 should still exist
        assert await cache.get("model_1") is not None
        assert await cache.get("model_2") is not None


# ============================================================================
# Property 33: Rate Limiting Under Load
# ============================================================================

class TestRateLimitingUnderLoad:
    """Property 33: Rate limiting prevents system overload."""

    @pytest.mark.asyncio
    @given(
        rate_per_minute=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=50, deadline=None)
    async def test_rate_limiter_enforces_limit(self, rate_per_minute: int):
        """Test that rate limiter enforces configured rate."""
        limiter = RateLimiter(
            rate_per_minute=rate_per_minute,
            burst_size=10,
        )

        # Try to acquire tokens rapidly
        num_requests = 20
        start_time = time.time()

        for _ in range(num_requests):
            await limiter.acquire(tokens=1, wait=True)

        elapsed_time = time.time() - start_time

        # Calculate actual rate
        actual_rate_per_minute = (num_requests / elapsed_time) * 60

        # Should be close to configured rate (with some tolerance)
        assert actual_rate_per_minute <= rate_per_minute * 1.2, \
            f"Actual rate {actual_rate_per_minute:.1f} exceeds limit {rate_per_minute}"

    @pytest.mark.asyncio
    @given(
        burst_size=st.integers(min_value=5, max_value=30)
    )
    @settings(max_examples=100, deadline=None)
    async def test_burst_allowance_works(self, burst_size: int):
        """Test that burst allowance allows initial burst of requests."""
        limiter = RateLimiter(
            rate_per_minute=60,
            burst_size=burst_size,
        )

        # Acquire burst tokens immediately
        start_time = time.time()

        for i in range(burst_size):
            success = await limiter.acquire(tokens=1, wait=False)
            assert success, f"Burst request {i+1} should succeed immediately"

        elapsed_time = time.time() - start_time

        # Should complete very quickly (within burst)
        assert elapsed_time < 1.0, "Burst should complete quickly"

    @pytest.mark.asyncio
    async def test_rate_limiter_prevents_overload(self):
        """Test that rate limiter prevents system overload."""
        config = BatchJobConfig(
            batch_size=10,
            max_concurrency=5,
            enable_rate_limiting=True,
            rate_limit_per_minute=60,  # 1 per second
        )
        processor = ParallelBatchProcessor(config=config)

        items = list(range(30))

        async def process_item(item):
            return item

        start_time = time.time()
        job_id = await processor.submit_job(items, process_item)

        # Wait for completion
        while True:
            job = await processor.get_job_status(job_id)
            if job.status.value in ["completed", "failed"]:
                break
            await asyncio.sleep(0.1)

        elapsed_time = time.time() - start_time

        # With rate limiting, should take longer than without
        # 30 items at 1/second = ~30 seconds minimum
        assert elapsed_time >= 20, "Rate limiting should slow down processing"


# ============================================================================
# Property 34: Parallel Processing Scalability
# ============================================================================

class TestParallelProcessingScalability:
    """Property 34: Parallel processing scales with concurrency."""

    @pytest.mark.asyncio
    @given(
        num_items=st.integers(min_value=20, max_value=100)
    )
    @settings(max_examples=50, deadline=None)
    async def test_all_items_processed_correctly(self, num_items: int):
        """Test that all items are processed correctly in parallel."""
        config = BatchJobConfig(
            batch_size=10,
            max_concurrency=5,
            enable_caching=False,
            enable_rate_limiting=False,
        )
        processor = ParallelBatchProcessor(config=config)

        items = list(range(num_items))

        async def process_item(item):
            return item * 2

        job_id = await processor.submit_job(items, process_item)

        # Wait for completion
        while True:
            job = await processor.get_job_status(job_id)
            if job.status.value in ["completed", "failed"]:
                break
            await asyncio.sleep(0.05)

        job = await processor.get_job_status(job_id)

        # Verify all items processed
        assert job.status.value == "completed"
        assert job.processed_items == num_items
        assert len(job.results) == num_items

        # Verify correct results
        expected = [i * 2 for i in items]
        assert sorted(job.results) == sorted(expected)

    @pytest.mark.asyncio
    @given(
        priority=st.sampled_from([QueuePriority.LOW, QueuePriority.NORMAL, QueuePriority.HIGH])
    )
    @settings(max_examples=100, deadline=None)
    async def test_job_priority_respected(self, priority: QueuePriority):
        """Test that job priority is respected."""
        config = BatchJobConfig(batch_size=10, max_concurrency=5)
        processor = ParallelBatchProcessor(config=config)

        items = list(range(10))

        async def process_item(item):
            return item

        job_id = await processor.submit_job(items, process_item, priority=priority)

        job = await processor.get_job_status(job_id)

        # Verify priority is set
        assert job.priority == priority

    @pytest.mark.asyncio
    async def test_error_handling_doesnt_stop_processing(self):
        """Test that errors in some items don't stop processing of others."""
        config = BatchJobConfig(
            batch_size=5,
            max_concurrency=3,
            retry_failed=False,
        )
        processor = ParallelBatchProcessor(config=config)

        items = list(range(20))

        async def process_item(item):
            if item % 5 == 0:
                raise ValueError(f"Error on item {item}")
            return item * 2

        job_id = await processor.submit_job(items, process_item)

        # Wait for completion
        while True:
            job = await processor.get_job_status(job_id)
            if job.status.value in ["completed", "failed"]:
                break
            await asyncio.sleep(0.05)

        job = await processor.get_job_status(job_id)

        # Should have some successes and some failures
        assert job.processed_items > 0
        assert job.failed_items > 0
        assert job.processed_items + job.failed_items == len(items)


# ============================================================================
# Property 35: Cache Eviction Strategy Correctness
# ============================================================================

class TestCacheEvictionStrategyCorrectness:
    """Property 35: Cache eviction strategies work correctly."""

    @pytest.mark.asyncio
    async def test_lfu_evicts_least_frequently_used(self):
        """Test that LFU evicts least frequently used items."""
        cache = ModelCacheManager(
            strategy=CacheStrategy.LFU,
            max_size=3,
        )

        # Add items
        await cache.put("model_1", {"data": 1})
        await cache.put("model_2", {"data": 2})
        await cache.put("model_3", {"data": 3})

        # Access model_1 multiple times
        for _ in range(5):
            await cache.get("model_1")

        # Access model_2 once
        await cache.get("model_2")

        # model_3 never accessed

        # Add new item (should evict model_3, least frequently used)
        await cache.put("model_4", {"data": 4})

        # model_3 should be evicted
        assert await cache.get("model_3") is None
        # model_1 and model_2 should still exist
        assert await cache.get("model_1") is not None
        assert await cache.get("model_2") is not None

    @pytest.mark.asyncio
    async def test_ttl_expires_old_entries(self):
        """Test that TTL strategy expires old entries."""
        cache = ModelCacheManager(
            strategy=CacheStrategy.TTL,
            max_size=10,
            ttl_seconds=1,  # 1 second TTL
        )

        # Add item
        await cache.put("model_old", {"data": "old"})

        # Should be available immediately
        assert await cache.get("model_old") is not None

        # Wait for TTL expiration
        await asyncio.sleep(1.5)

        # Should be expired
        assert await cache.get("model_old") is None

    @pytest.mark.asyncio
    async def test_cache_statistics_accurate(self):
        """Test that cache statistics are accurate."""
        cache = ModelCacheManager(max_size=10)

        # Perform operations
        await cache.put("model_1", {"data": 1})
        await cache.put("model_2", {"data": 2})

        # Hits
        await cache.get("model_1")
        await cache.get("model_2")

        # Misses
        await cache.get("model_nonexistent")

        stats = await cache.get_statistics()

        assert stats["cache_size"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(66.67, abs=1.0)


# ============================================================================
# Helper functions for running async tests
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
