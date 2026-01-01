"""
Unit tests for the Performance Caching System.

Tests cover:
- Task 17.1: Response cache, multi-strategy caching (LRU/LFU/TTL/FIFO),
  cache hit rate, cache expiration and cleanup
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json
import hashlib

from hypothesis import given, strategies as st, settings, assume

from src.agent.performance import (
    CacheStrategy,
    CacheEntry,
    CacheMetrics,
    InMemoryCache,
    ResponseCache,
    cached_response,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def lru_cache():
    """Create an LRU cache instance."""
    return InMemoryCache(max_size=5, strategy=CacheStrategy.LRU)


@pytest.fixture
def lfu_cache():
    """Create an LFU cache instance."""
    return InMemoryCache(max_size=5, strategy=CacheStrategy.LFU)


@pytest.fixture
def ttl_cache():
    """Create a TTL cache instance."""
    return InMemoryCache(max_size=5, strategy=CacheStrategy.TTL, default_ttl=1.0)


@pytest.fixture
def fifo_cache():
    """Create a FIFO cache instance."""
    return InMemoryCache(max_size=5, strategy=CacheStrategy.FIFO)


@pytest.fixture
def response_cache():
    """Create a response cache instance."""
    return ResponseCache(max_size=10, default_ttl=60.0)


# =============================================================================
# Test: CacheEntry
# =============================================================================


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(key="test", value="value")
        assert entry.key == "test"
        assert entry.value == "value"
        assert entry.access_count == 0

    def test_cache_entry_access(self):
        """Test accessing a cache entry."""
        entry = CacheEntry(key="test", value="value")
        result = entry.access()
        assert result == "value"
        assert entry.access_count == 1

    def test_cache_entry_multiple_accesses(self):
        """Test multiple accesses."""
        entry = CacheEntry(key="test", value="value")
        for _ in range(5):
            entry.access()
        assert entry.access_count == 5

    def test_cache_entry_last_accessed_updated(self):
        """Test that last_accessed is updated on access."""
        entry = CacheEntry(key="test", value="value")
        initial_access = entry.last_accessed
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.01))
        entry.access()
        assert entry.last_accessed >= initial_access

    def test_cache_entry_not_expired(self):
        """Test entry not expired."""
        entry = CacheEntry(key="test", value="value", ttl_seconds=100.0)
        assert not entry.is_expired

    def test_cache_entry_expired(self):
        """Test entry expired."""
        entry = CacheEntry(key="test", value="value", ttl_seconds=0.0)
        assert entry.is_expired

    def test_cache_entry_no_ttl(self):
        """Test entry with no TTL never expires."""
        entry = CacheEntry(key="test", value="value", ttl_seconds=None)
        assert not entry.is_expired


# =============================================================================
# Test: CacheMetrics
# =============================================================================


class TestCacheMetrics:
    """Tests for CacheMetrics model."""

    def test_metrics_creation(self):
        """Test creating cache metrics."""
        metrics = CacheMetrics(hits=10, misses=5, evictions=2, size=50, max_size=100)
        assert metrics.hits == 10
        assert metrics.misses == 5

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        metrics = CacheMetrics(hits=80, misses=20)
        assert metrics.hit_rate == pytest.approx(0.8)

    def test_hit_rate_zero_requests(self):
        """Test hit rate with zero requests."""
        metrics = CacheMetrics(hits=0, misses=0)
        assert metrics.hit_rate == 0.0

    def test_hit_rate_all_hits(self):
        """Test hit rate with all hits."""
        metrics = CacheMetrics(hits=100, misses=0)
        assert metrics.hit_rate == 1.0

    def test_hit_rate_all_misses(self):
        """Test hit rate with all misses."""
        metrics = CacheMetrics(hits=0, misses=100)
        assert metrics.hit_rate == 0.0


# =============================================================================
# Test: InMemoryCache - LRU Strategy
# =============================================================================


class TestInMemoryCacheLRU:
    """Tests for InMemoryCache with LRU strategy."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, lru_cache):
        """Test setting and getting values."""
        await lru_cache.set("key1", "value1")
        result = await lru_cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, lru_cache):
        """Test getting nonexistent key."""
        result = await lru_cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self, lru_cache):
        """Test LRU eviction when cache is full."""
        # Fill cache
        for i in range(5):
            await lru_cache.set(f"key{i}", f"value{i}")

        # Access key0 to make it recently used
        await lru_cache.get("key0")

        # Add new key, should evict key1 (least recently used)
        await lru_cache.set("key5", "value5")

        # key1 should be evicted
        assert await lru_cache.get("key1") is None
        # key0 should still exist
        assert await lru_cache.get("key0") == "value0"
        # key5 should exist
        assert await lru_cache.get("key5") == "value5"

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, lru_cache):
        """Test that metrics are tracked correctly."""
        await lru_cache.set("key1", "value1")

        # Hit
        await lru_cache.get("key1")
        # Miss
        await lru_cache.get("nonexistent")

        metrics = lru_cache.get_metrics()
        assert metrics.hits == 1
        assert metrics.misses == 1

    @pytest.mark.asyncio
    async def test_delete(self, lru_cache):
        """Test deleting a key."""
        await lru_cache.set("key1", "value1")
        result = await lru_cache.delete("key1")
        assert result is True
        assert await lru_cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, lru_cache):
        """Test deleting nonexistent key."""
        result = await lru_cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self, lru_cache):
        """Test clearing the cache."""
        for i in range(3):
            await lru_cache.set(f"key{i}", f"value{i}")

        count = await lru_cache.clear()
        assert count == 3

        metrics = lru_cache.get_metrics()
        assert metrics.size == 0


# =============================================================================
# Test: InMemoryCache - LFU Strategy
# =============================================================================


class TestInMemoryCacheLFU:
    """Tests for InMemoryCache with LFU strategy."""

    @pytest.mark.asyncio
    async def test_lfu_eviction(self, lfu_cache):
        """Test LFU eviction based on access frequency."""
        # Fill cache
        for i in range(5):
            await lfu_cache.set(f"key{i}", f"value{i}")

        # Access key0 multiple times
        for _ in range(5):
            await lfu_cache.get("key0")

        # Access key1 a few times
        for _ in range(3):
            await lfu_cache.get("key1")

        # key2, key3, key4 have access_count=0

        # Add new key, should evict one of the least accessed
        await lfu_cache.set("key5", "value5")

        # key0 and key1 should still exist (most accessed)
        assert await lfu_cache.get("key0") == "value0"
        assert await lfu_cache.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_lfu_evicts_least_frequent(self, lfu_cache):
        """Test that LFU evicts the least frequently used."""
        await lfu_cache.set("frequent", "value")
        await lfu_cache.set("infrequent", "value")

        # Access frequent multiple times
        for _ in range(10):
            await lfu_cache.get("frequent")

        # Fill remaining cache slots
        for i in range(3):
            await lfu_cache.set(f"key{i}", f"value{i}")

        # Add one more to trigger eviction
        await lfu_cache.set("new", "value")

        # Frequent should still exist
        assert await lfu_cache.get("frequent") == "value"


# =============================================================================
# Test: InMemoryCache - TTL Strategy
# =============================================================================


class TestInMemoryCacheTTL:
    """Tests for InMemoryCache with TTL strategy."""

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, ttl_cache):
        """Test TTL-based expiration."""
        await ttl_cache.set("key1", "value1", ttl=0.1)

        # Should exist immediately
        assert await ttl_cache.get("key1") == "value1"

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired
        assert await ttl_cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_ttl_not_expired(self, ttl_cache):
        """Test TTL-based non-expiration."""
        await ttl_cache.set("key1", "value1", ttl=10.0)

        # Should still exist
        assert await ttl_cache.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_ttl_eviction_prefers_expired(self, ttl_cache):
        """Test that TTL eviction prefers expired entries."""
        # Add entries with different TTLs
        await ttl_cache.set("short_ttl", "value", ttl=0.05)
        await ttl_cache.set("long_ttl", "value", ttl=100.0)

        # Wait for short TTL to expire
        await asyncio.sleep(0.1)

        # Fill cache
        for i in range(4):
            await ttl_cache.set(f"key{i}", f"value{i}", ttl=100.0)

        # short_ttl should be expired and evicted
        assert await ttl_cache.get("short_ttl") is None
        # long_ttl might still exist if not evicted
        # (depends on exact eviction order)


# =============================================================================
# Test: InMemoryCache - FIFO Strategy
# =============================================================================


class TestInMemoryCacheFIFO:
    """Tests for InMemoryCache with FIFO strategy."""

    @pytest.mark.asyncio
    async def test_fifo_eviction(self, fifo_cache):
        """Test FIFO eviction order."""
        # Fill cache in order
        for i in range(5):
            await fifo_cache.set(f"key{i}", f"value{i}")

        # Add new key, should evict key0 (first in)
        await fifo_cache.set("key5", "value5")

        # key0 should be evicted (first in, first out)
        assert await fifo_cache.get("key0") is None
        # key1-key5 should exist
        for i in range(1, 6):
            assert await fifo_cache.get(f"key{i}") == f"value{i}"

    @pytest.mark.asyncio
    async def test_fifo_ignores_access(self, fifo_cache):
        """Test that FIFO ignores access patterns."""
        # Fill cache
        for i in range(5):
            await fifo_cache.set(f"key{i}", f"value{i}")

        # Access key0 many times (should not affect eviction)
        for _ in range(10):
            await fifo_cache.get("key0")

        # Add new key
        await fifo_cache.set("key5", "value5")

        # key0 should still be evicted despite many accesses
        assert await fifo_cache.get("key0") is None


# =============================================================================
# Test: ResponseCache
# =============================================================================


class TestResponseCache:
    """Tests for ResponseCache class."""

    @pytest.mark.asyncio
    async def test_cache_response(self, response_cache):
        """Test caching a response."""
        await response_cache.cache_response(
            query="test query",
            response={"answer": "test answer"},
        )

        result = await response_cache.get_response(query="test query")
        assert result == {"answer": "test answer"}

    @pytest.mark.asyncio
    async def test_cache_with_context(self, response_cache):
        """Test caching with context."""
        context = {"tenant": "test", "user": "alice"}

        await response_cache.cache_response(
            query="test query",
            response={"answer": "with context"},
            context=context,
        )

        # Same query without context should miss
        result = await response_cache.get_response(query="test query")
        assert result is None

        # Same query with context should hit
        result = await response_cache.get_response(query="test query", context=context)
        assert result == {"answer": "with context"}

    @pytest.mark.asyncio
    async def test_cache_with_tenant_id(self, response_cache):
        """Test caching with tenant ID."""
        await response_cache.cache_response(
            query="test query",
            response={"answer": "tenant1"},
            tenant_id="tenant1",
        )

        await response_cache.cache_response(
            query="test query",
            response={"answer": "tenant2"},
            tenant_id="tenant2",
        )

        # Different tenants should have different cached values
        result1 = await response_cache.get_response(query="test query", tenant_id="tenant1")
        result2 = await response_cache.get_response(query="test query", tenant_id="tenant2")

        assert result1 == {"answer": "tenant1"}
        assert result2 == {"answer": "tenant2"}

    @pytest.mark.asyncio
    async def test_query_normalization(self, response_cache):
        """Test query normalization (case insensitive, whitespace trimmed)."""
        await response_cache.cache_response(
            query="Test Query",
            response={"answer": "original"},
        )

        # Should match despite different case and whitespace
        result = await response_cache.get_response(query="  test query  ")
        assert result == {"answer": "original"}

    @pytest.mark.asyncio
    async def test_invalidate(self, response_cache):
        """Test invalidating a cached response."""
        await response_cache.cache_response(
            query="test query",
            response={"answer": "test"},
        )

        result = await response_cache.invalidate(query="test query")
        assert result is True

        # Should be gone
        assert await response_cache.get_response(query="test query") is None

    @pytest.mark.asyncio
    async def test_clear_all(self, response_cache):
        """Test clearing all cached responses."""
        for i in range(5):
            await response_cache.cache_response(
                query=f"query{i}",
                response={"answer": f"answer{i}"},
            )

        count = await response_cache.clear_all()
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_metrics(self, response_cache):
        """Test getting cache metrics."""
        await response_cache.cache_response(query="q1", response={"a": 1})
        await response_cache.get_response(query="q1")  # Hit
        await response_cache.get_response(query="q2")  # Miss

        metrics = response_cache.get_metrics()
        assert metrics.hits == 1
        assert metrics.misses == 1

    @pytest.mark.asyncio
    async def test_custom_ttl(self, response_cache):
        """Test custom TTL for a response."""
        await response_cache.cache_response(
            query="test",
            response={"answer": "test"},
            ttl=0.1,
        )

        # Should exist initially
        assert await response_cache.get_response(query="test") is not None

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired
        assert await response_cache.get_response(query="test") is None


# =============================================================================
# Test: cached_response Decorator
# =============================================================================


class TestCachedResponseDecorator:
    """Tests for cached_response decorator."""

    @pytest.mark.asyncio
    async def test_decorator_caches_result(self):
        """Test that decorator caches function results."""
        call_count = 0

        @cached_response(ttl=60.0)
        async def slow_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = await slow_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = await slow_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

    @pytest.mark.asyncio
    async def test_decorator_different_args(self):
        """Test that different arguments get different cache entries."""
        call_count = 0

        @cached_response(ttl=60.0)
        async def compute(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        result1 = await compute(1, 2)
        result2 = await compute(3, 4)

        assert result1 == 3
        assert result2 == 7
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_with_custom_key_builder(self):
        """Test decorator with custom key builder."""
        @cached_response(
            ttl=60.0,
            key_builder=lambda x, **kw: f"custom:{x}"
        )
        async def function_with_key(x):
            return x * 10

        result = await function_with_key(5)
        assert result == 50

    @pytest.mark.asyncio
    async def test_decorator_expiration(self):
        """Test that cached results expire."""
        call_count = 0

        @cached_response(ttl=0.1)
        async def expiring_function(x):
            nonlocal call_count
            call_count += 1
            return x

        # First call
        await expiring_function(1)
        assert call_count == 1

        # Second call before expiration
        await expiring_function(1)
        assert call_count == 1

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should call again
        await expiring_function(1)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_cache_accessible(self):
        """Test that cache is accessible on decorated function."""
        @cached_response(ttl=60.0)
        async def my_function(x):
            return x

        assert hasattr(my_function, 'cache')
        assert isinstance(my_function.cache, InMemoryCache)


# =============================================================================
# Property-Based Tests: Cache Consistency
# =============================================================================


class TestPropertyCacheConsistency:
    """Property-based tests for cache consistency."""

    @given(
        key=st.text(min_size=1, max_size=50),
        value=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_property_set_get_consistency(self, key, value):
        """Property: Get should return what was set."""
        assume(key.strip())  # Non-empty key

        cache = InMemoryCache(max_size=100, strategy=CacheStrategy.LRU)
        await cache.set(key, value)
        result = await cache.get(key)

        assert result == value

    @given(
        keys=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=20, unique=True),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_property_all_sets_retrievable(self, keys):
        """Property: All set values should be retrievable (within cache size)."""
        assume(all(k.strip() for k in keys))

        cache = InMemoryCache(max_size=100, strategy=CacheStrategy.LRU)

        # Set all
        for key in keys:
            await cache.set(key, f"value_{key}")

        # All should be retrievable
        for key in keys:
            result = await cache.get(key)
            assert result == f"value_{key}"

    @given(
        max_size=st.integers(min_value=1, max_value=10),
        num_items=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_property_size_never_exceeds_max(self, max_size, num_items):
        """Property: Cache size should never exceed max_size."""
        cache = InMemoryCache(max_size=max_size, strategy=CacheStrategy.LRU)

        for i in range(num_items):
            await cache.set(f"key{i}", f"value{i}")

        metrics = cache.get_metrics()
        assert metrics.size <= max_size


# =============================================================================
# Property-Based Tests: Hit Rate Monotonicity
# =============================================================================


class TestPropertyHitRate:
    """Property-based tests for cache hit rate."""

    @given(
        num_unique=st.integers(min_value=1, max_value=10),
        num_repeats=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_property_hit_rate_increases_with_repeats(self, num_unique, num_repeats):
        """Property: Hit rate should increase with repeated access patterns."""
        cache = InMemoryCache(max_size=100, strategy=CacheStrategy.LRU)

        # Set unique items
        for i in range(num_unique):
            await cache.set(f"key{i}", f"value{i}")

        # Access each item multiple times
        for _ in range(num_repeats):
            for i in range(num_unique):
                await cache.get(f"key{i}")

        metrics = cache.get_metrics()

        # All accesses should be hits after initial set
        total_accesses = num_unique * num_repeats
        assert metrics.hits == total_accesses
        assert metrics.hit_rate == 1.0

    @given(
        hit_count=st.integers(min_value=0, max_value=100),
        miss_count=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=50)
    def test_property_hit_rate_bounded(self, hit_count, miss_count):
        """Property: Hit rate should always be between 0 and 1."""
        metrics = CacheMetrics(hits=hit_count, misses=miss_count)
        assert 0.0 <= metrics.hit_rate <= 1.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestCacheIntegration:
    """Integration tests for caching system."""

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent cache access."""
        cache = InMemoryCache(max_size=100, strategy=CacheStrategy.LRU)

        async def worker(worker_id):
            for i in range(10):
                key = f"worker{worker_id}_key{i}"
                await cache.set(key, f"value{i}")
                result = await cache.get(key)
                assert result == f"value{i}"

        # Run multiple workers concurrently
        await asyncio.gather(*[worker(i) for i in range(5)])

        # All operations should succeed
        metrics = cache.get_metrics()
        assert metrics.hits == 50  # 5 workers * 10 gets

    @pytest.mark.asyncio
    async def test_response_cache_workflow(self):
        """Test complete response cache workflow."""
        cache = ResponseCache(max_size=10, default_ttl=60.0)

        # Simulate query -> cache -> response flow
        queries = [
            ("SELECT * FROM users", {"tenant": "t1"}),
            ("SELECT * FROM orders", {"tenant": "t1"}),
            ("SELECT * FROM users", {"tenant": "t2"}),
        ]

        # First pass: all misses, cache responses
        for query, context in queries:
            result = await cache.get_response(query, context)
            assert result is None
            await cache.cache_response(
                query, {"data": f"result for {query}"}, context
            )

        # Second pass: all hits
        for query, context in queries:
            result = await cache.get_response(query, context)
            assert result is not None
            assert "data" in result

        metrics = cache.get_metrics()
        assert metrics.hits == 3
        assert metrics.misses == 3

    @pytest.mark.asyncio
    async def test_eviction_with_mixed_strategies(self):
        """Test eviction behavior across different strategies."""
        strategies = [
            CacheStrategy.LRU,
            CacheStrategy.LFU,
            CacheStrategy.FIFO,
            CacheStrategy.TTL,
        ]

        for strategy in strategies:
            cache = InMemoryCache(max_size=3, strategy=strategy, default_ttl=60.0)

            # Fill cache
            for i in range(3):
                await cache.set(f"key{i}", f"value{i}")

            # Add one more to trigger eviction
            await cache.set("key3", "value3")

            # Size should still be max_size
            metrics = cache.get_metrics()
            assert metrics.size == 3

            # At least one original key should be evicted
            evicted = sum(
                1 for i in range(3)
                if await cache.get(f"key{i}") is None
            )
            assert evicted >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
