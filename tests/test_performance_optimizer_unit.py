"""
Unit Tests for Performance Optimizer Module

Tests caching, query optimization, batch processing,
and performance monitoring functionality.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from quality_billing.performance_optimizer import (
    # Caching
    CacheEvictionPolicy,
    CacheEntry,
    CacheStats,
    PerformanceCache,
    cached,
    # Query Optimization
    QueryPlan,
    QueryStats,
    QueryOptimizer,
    # Batch Processing
    BatchResult,
    BatchProcessor,
    # Performance Monitoring
    PerformanceMetric,
    PerformanceSummary,
    PerformanceMonitor,
    timed,
    # Connection Pool
    PooledConnection,
    ConnectionPool,
    # Data Preloader
    DataPreloader,
    # Rate Limiter
    RateLimitResult,
    RateLimiter,
    rate_limited,
)


# ============================================================================
# Cache Entry Tests
# ============================================================================

class TestCacheEntry:
    """Tests for CacheEntry class"""

    def test_cache_entry_creation(self):
        """Test creating a cache entry"""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            created_at=now,
            accessed_at=now
        )

        assert entry.key == "test_key"
        assert entry.value == {"data": "test"}
        assert entry.access_count == 1
        assert not entry.is_expired()

    def test_cache_entry_with_ttl(self):
        """Test cache entry with TTL"""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=now - timedelta(seconds=10),
            accessed_at=now,
            ttl_seconds=5
        )

        assert entry.is_expired()

    def test_cache_entry_touch(self):
        """Test updating access time and count"""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=now,
            accessed_at=now
        )

        original_count = entry.access_count
        entry.touch()

        assert entry.access_count == original_count + 1
        assert entry.accessed_at >= now


# ============================================================================
# Performance Cache Tests
# ============================================================================

class TestPerformanceCache:
    """Tests for PerformanceCache class"""

    def test_cache_set_and_get(self):
        """Test basic set and get operations"""
        cache: PerformanceCache[str] = PerformanceCache(max_size=100)
        cache.set("key1", "value1")

        assert cache.get("key1") == "value1"

    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache: PerformanceCache[str] = PerformanceCache(max_size=100)

        assert cache.get("nonexistent") is None

    def test_cache_delete(self):
        """Test deleting cache entry"""
        cache: PerformanceCache[str] = PerformanceCache(max_size=100)
        cache.set("key1", "value1")
        result = cache.delete("key1")

        assert result is True
        assert cache.get("key1") is None

    def test_cache_clear(self):
        """Test clearing all cache entries"""
        cache: PerformanceCache[str] = PerformanceCache(max_size=100)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_ttl_expiration(self):
        """Test TTL-based expiration"""
        cache: PerformanceCache[str] = PerformanceCache(
            max_size=100,
            default_ttl=1
        )
        cache.set("key1", "value1")

        # Should be accessible immediately
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired
        assert cache.get("key1") is None

    def test_cache_lru_eviction(self):
        """Test LRU eviction policy"""
        cache: PerformanceCache[int] = PerformanceCache(
            max_size=3,
            eviction_policy=CacheEvictionPolicy.LRU
        )

        cache.set("key1", 1)
        cache.set("key2", 2)
        cache.set("key3", 3)

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key4, should evict key2 (least recently used)
        cache.set("key4", 4)

        assert cache.get("key1") == 1
        assert cache.get("key2") is None
        assert cache.get("key3") == 3
        assert cache.get("key4") == 4

    def test_cache_lfu_eviction(self):
        """Test LFU eviction policy"""
        cache: PerformanceCache[int] = PerformanceCache(
            max_size=3,
            eviction_policy=CacheEvictionPolicy.LFU
        )

        cache.set("key1", 1)
        cache.set("key2", 2)
        cache.set("key3", 3)

        # Access key1 multiple times
        cache.get("key1")
        cache.get("key1")
        cache.get("key3")

        # Add key4, should evict key2 (least frequently used)
        cache.set("key4", 4)

        assert cache.get("key1") == 1
        assert cache.get("key2") is None
        assert cache.get("key3") == 3
        assert cache.get("key4") == 4

    def test_cache_stats(self):
        """Test cache statistics"""
        cache: PerformanceCache[str] = PerformanceCache(max_size=100)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()

        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.hit_rate == 2 / 3

    def test_cache_thread_safety(self):
        """Test thread safety of cache operations"""
        cache: PerformanceCache[int] = PerformanceCache(max_size=1000)
        errors = []

        def worker(thread_id: int):
            try:
                for i in range(100):
                    key = f"thread_{thread_id}_key_{i}"
                    cache.set(key, i)
                    value = cache.get(key)
                    if value != i:
                        errors.append(f"Value mismatch: expected {i}, got {value}")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestCacheDecorator:
    """Tests for cached decorator"""

    def test_cached_decorator(self):
        """Test cached decorator caches function results"""
        cache: PerformanceCache = PerformanceCache(max_size=100)
        call_count = 0

        @cached(cache, key_prefix="test")
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call with same argument (should use cache)
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increase

        # Call with different argument
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2


# ============================================================================
# Query Optimizer Tests
# ============================================================================

class TestQueryOptimizer:
    """Tests for QueryOptimizer class"""

    @pytest.fixture
    def optimizer(self) -> QueryOptimizer:
        return QueryOptimizer()

    def test_analyze_select_star(self, optimizer):
        """Test detection of SELECT * usage"""
        query = "SELECT * FROM users WHERE id = 1"
        plan = optimizer.analyze_query(query, "users")

        assert any("SELECT *" in s for s in plan.suggestions)

    def test_analyze_missing_where(self, optimizer):
        """Test detection of missing WHERE clause"""
        query = "SELECT name FROM users"
        plan = optimizer.analyze_query(query, "users")

        assert any("WHERE" in s for s in plan.suggestions)

    def test_analyze_leading_wildcard(self, optimizer):
        """Test detection of leading wildcard in LIKE"""
        query = "SELECT * FROM users WHERE name LIKE '%john'"
        plan = optimizer.analyze_query(query, "users")

        assert any("wildcard" in s.lower() for s in plan.suggestions)

    def test_analyze_order_by(self, optimizer):
        """Test detection of ORDER BY without index"""
        query = "SELECT id FROM orders WHERE status = 'pending' ORDER BY created_at"
        plan = optimizer.analyze_query(query, "orders")

        assert any("ORDER BY" in s for s in plan.suggestions)

    def test_record_execution(self, optimizer):
        """Test recording query execution"""
        query = "SELECT * FROM users"
        optimizer.record_execution(query, 50.0)
        optimizer.record_execution(query, 150.0)

        stats = optimizer.get_query_stats(query)

        assert stats is not None
        assert stats.execution_count == 2
        assert stats.avg_time_ms == 100.0
        assert stats.max_time_ms == 150.0
        assert stats.min_time_ms == 50.0

    def test_get_slow_queries(self, optimizer):
        """Test getting slow queries"""
        optimizer.record_execution("SELECT * FROM users", 50.0)
        optimizer.record_execution("SELECT * FROM orders", 200.0)

        slow_queries = optimizer.get_slow_queries()

        # orders query should be slow (>100ms threshold)
        assert len(slow_queries) == 1
        assert slow_queries[0].avg_time_ms == 200.0

    def test_suggested_indexes(self, optimizer):
        """Test index suggestions from WHERE clause"""
        query = "SELECT * FROM users WHERE email = 'test@example.com'"
        optimizer.analyze_query(query, "users")

        indexes = optimizer.get_suggested_indexes()

        assert len(indexes) > 0
        assert any("email" in idx for idx in indexes)


# ============================================================================
# Batch Processor Tests
# ============================================================================

class TestBatchProcessor:
    """Tests for BatchProcessor class"""

    @pytest.fixture
    def processor(self) -> BatchProcessor:
        return BatchProcessor(batch_size=10, max_workers=2)

    def test_process_batch_success(self, processor):
        """Test successful batch processing"""
        items = list(range(25))
        result = processor.process_batch(items, lambda x: x * 2)

        assert result.total_items == 25
        assert result.processed_items == 25
        assert result.failed_items == 0
        assert len(result.results) == 25

    def test_process_batch_with_failures(self, processor):
        """Test batch processing with some failures"""
        items = list(range(10))

        def processor_func(x):
            if x == 5:
                raise ValueError("Failed item")
            return x * 2

        result = processor.process_batch(items, processor_func)

        assert result.total_items == 10
        assert result.processed_items == 9
        assert result.failed_items == 1

    def test_process_batch_with_progress(self, processor):
        """Test batch processing with progress callback"""
        items = list(range(20))
        progress_calls = []

        def on_progress(processed: int, total: int):
            progress_calls.append((processed, total))

        processor.process_batch(items, lambda x: x, on_progress=on_progress)

        assert len(progress_calls) > 0
        # Last call should show all items processed
        assert progress_calls[-1][0] == 20

    def test_batch_result_attributes(self, processor):
        """Test BatchResult attributes"""
        items = [1, 2, 3]
        result = processor.process_batch(items, lambda x: x * 10)

        assert result.batch_id is not None
        assert result.processing_time_ms > 0
        assert result.results == [10, 20, 30]

    def test_batch_processor_shutdown(self, processor):
        """Test processor shutdown"""
        processor.shutdown()
        # Should not raise exception


# ============================================================================
# Performance Monitor Tests
# ============================================================================

class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class"""

    @pytest.fixture
    def monitor(self) -> PerformanceMonitor:
        return PerformanceMonitor(retention_hours=1)

    def test_record_metric(self, monitor):
        """Test recording a metric"""
        monitor.record("api_latency", 50.0, "ms")

        recent = monitor.get_recent_metrics("api_latency", count=10)

        assert len(recent) == 1
        assert recent[0].name == "api_latency"
        assert recent[0].value == 50.0

    def test_record_with_tags(self, monitor):
        """Test recording a metric with tags"""
        monitor.record("api_latency", 50.0, "ms", tags={"endpoint": "/users"})

        recent = monitor.get_recent_metrics("api_latency", count=10)

        assert recent[0].tags == {"endpoint": "/users"}

    def test_get_summary(self, monitor):
        """Test getting performance summary"""
        monitor.record("api_latency", 50.0)
        monitor.record("api_latency", 100.0)
        monitor.record("api_latency", 150.0)

        summary = monitor.get_summary(period_minutes=60)

        assert "api_latency" in summary.metrics
        stats = summary.metrics["api_latency"]
        assert stats["avg"] == 100.0
        assert stats["min"] == 50.0
        assert stats["max"] == 150.0
        assert stats["count"] == 3

    def test_filter_by_metric_names(self, monitor):
        """Test filtering summary by metric names"""
        monitor.record("api_latency", 50.0)
        monitor.record("db_query_time", 100.0)

        summary = monitor.get_summary(metric_names=["api_latency"])

        assert "api_latency" in summary.metrics
        assert "db_query_time" not in summary.metrics


class TestTimedDecorator:
    """Tests for timed decorator"""

    def test_timed_decorator(self):
        """Test timed decorator records execution time"""
        monitor = PerformanceMonitor()

        @timed(monitor, "test_function")
        def slow_function():
            time.sleep(0.1)
            return "done"

        result = slow_function()

        assert result == "done"

        recent = monitor.get_recent_metrics("test_function", count=10)
        assert len(recent) == 1
        assert recent[0].value >= 100.0  # At least 100ms


# ============================================================================
# Connection Pool Tests
# ============================================================================

class TestConnectionPool:
    """Tests for ConnectionPool class"""

    def test_pool_initialization(self):
        """Test pool initialization"""
        connections_created = []

        def factory():
            conn = {"id": len(connections_created)}
            connections_created.append(conn)
            return conn

        pool = ConnectionPool(
            factory=factory,
            min_size=2,
            max_size=5
        )
        pool.initialize()

        stats = pool.get_stats()
        assert stats["total"] == 2
        assert stats["available"] == 2
        assert stats["in_use"] == 0

    def test_acquire_and_release(self):
        """Test acquiring and releasing connections"""
        counter = [0]

        def factory():
            counter[0] += 1
            return {"id": counter[0]}

        pool = ConnectionPool(factory=factory, min_size=1, max_size=3)
        pool.initialize()

        conn1 = pool.acquire()
        stats = pool.get_stats()
        assert stats["in_use"] == 1

        pool.release(conn1)
        stats = pool.get_stats()
        assert stats["in_use"] == 0

    def test_pool_grows_on_demand(self):
        """Test pool grows when connections are needed"""
        counter = [0]

        def factory():
            counter[0] += 1
            return {"id": counter[0]}

        pool = ConnectionPool(factory=factory, min_size=1, max_size=3)
        pool.initialize()

        conn1 = pool.acquire()
        conn2 = pool.acquire()
        conn3 = pool.acquire()

        stats = pool.get_stats()
        assert stats["total"] == 3
        assert stats["in_use"] == 3

        pool.release(conn1)
        pool.release(conn2)
        pool.release(conn3)

    def test_pool_exhaustion(self):
        """Test pool exhaustion raises error"""
        def factory():
            return {"id": 1}

        pool = ConnectionPool(factory=factory, min_size=1, max_size=2)
        pool.initialize()

        conn1 = pool.acquire()
        conn2 = pool.acquire()

        with pytest.raises(RuntimeError, match="exhausted"):
            pool.acquire()

        pool.release(conn1)
        pool.release(conn2)

    def test_pool_shutdown(self):
        """Test pool shutdown"""
        class MockConnection:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        connections = []

        def factory():
            conn = MockConnection()
            connections.append(conn)
            return conn

        pool = ConnectionPool(factory=factory, min_size=2, max_size=5)
        pool.initialize()
        pool.shutdown()

        for conn in connections:
            assert conn.closed


# ============================================================================
# Data Preloader Tests
# ============================================================================

class TestDataPreloader:
    """Tests for DataPreloader class"""

    def test_register_and_preload(self):
        """Test registering and preloading data"""
        cache: PerformanceCache = PerformanceCache(max_size=100)
        preloader = DataPreloader(cache)

        preloader.register("users", lambda: ["user1", "user2"])
        preloader.register("config", lambda: {"key": "value"})

        results = preloader.preload_all()

        assert results["users"] is True
        assert results["config"] is True
        assert cache.get("users") == ["user1", "user2"]
        assert cache.get("config") == {"key": "value"}

    def test_preload_with_failure(self):
        """Test preloading with one loader failing"""
        cache: PerformanceCache = PerformanceCache(max_size=100)
        preloader = DataPreloader(cache)

        preloader.register("good", lambda: "success")
        preloader.register("bad", lambda: 1 / 0)  # Will raise

        results = preloader.preload_all()

        assert results["good"] is True
        assert results["bad"] is False
        assert cache.get("good") == "success"

    def test_unregister(self):
        """Test unregistering a preload task"""
        cache: PerformanceCache = PerformanceCache(max_size=100)
        preloader = DataPreloader(cache)

        preloader.register("test", lambda: "data")
        preloader.unregister("test")

        results = preloader.preload_all()

        assert "test" not in results


# ============================================================================
# Rate Limiter Tests
# ============================================================================

class TestRateLimiter:
    """Tests for RateLimiter class"""

    def test_rate_limit_allows_burst(self):
        """Test that burst requests are allowed"""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=5)

        # Should allow burst_size requests immediately
        for _ in range(5):
            result = limiter.check("user1")
            assert result.allowed is True

    def test_rate_limit_blocks_excess(self):
        """Test that excess requests are blocked"""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=3)

        # Use up burst
        for _ in range(3):
            limiter.check("user1")

        # Next request should be blocked
        result = limiter.check("user1")
        assert result.allowed is False
        assert result.retry_after_seconds is not None

    def test_rate_limit_refills(self):
        """Test that tokens refill over time"""
        limiter = RateLimiter(requests_per_second=100.0, burst_size=1)

        # Use the token
        result1 = limiter.check("user1")
        assert result1.allowed is True

        # Wait for refill
        time.sleep(0.02)

        # Should be allowed again
        result2 = limiter.check("user1")
        assert result2.allowed is True

    def test_rate_limit_per_key(self):
        """Test that rate limits are per key"""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=1)

        result1 = limiter.check("user1")
        result2 = limiter.check("user2")

        assert result1.allowed is True
        assert result2.allowed is True

    def test_rate_limit_reset(self):
        """Test resetting rate limit for a key"""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=1)

        # Use up token
        limiter.check("user1")
        result1 = limiter.check("user1")
        assert result1.allowed is False

        # Reset
        limiter.reset("user1")

        # Should be allowed
        result2 = limiter.check("user1")
        assert result2.allowed is True


class TestRateLimitedDecorator:
    """Tests for rate_limited decorator"""

    def test_rate_limited_allows_normal(self):
        """Test rate limited decorator allows normal usage"""
        limiter = RateLimiter(requests_per_second=100.0, burst_size=10)

        @rate_limited(limiter)
        def my_function(x: int) -> int:
            return x * 2

        result = my_function(5)
        assert result == 10

    def test_rate_limited_blocks_excess(self):
        """Test rate limited decorator blocks excess calls"""
        limiter = RateLimiter(requests_per_second=100.0, burst_size=2)

        @rate_limited(limiter)
        def my_function(x: int) -> int:
            return x * 2

        my_function(1)
        my_function(2)

        with pytest.raises(RuntimeError, match="Rate limit exceeded"):
            my_function(3)


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestCacheProperties:
    """Property-based tests for cache"""

    def test_cache_never_exceeds_max_size(self):
        """Test cache never exceeds max size"""
        max_size = 10
        cache: PerformanceCache[int] = PerformanceCache(max_size=max_size)

        for i in range(100):
            cache.set(f"key_{i}", i)

        stats = cache.get_stats()
        assert stats.current_size <= max_size

    def test_cache_hit_rate_valid_range(self):
        """Test cache hit rate is always between 0 and 1"""
        cache: PerformanceCache[int] = PerformanceCache(max_size=100)

        for i in range(50):
            cache.set(f"key_{i}", i)
            cache.get(f"key_{i}")
            cache.get(f"nonexistent_{i}")

        stats = cache.get_stats()
        assert 0.0 <= stats.hit_rate <= 1.0


class TestBatchProcessorProperties:
    """Property-based tests for batch processor"""

    def test_batch_result_counts_are_consistent(self):
        """Test batch result counts are consistent"""
        processor = BatchProcessor(batch_size=5, max_workers=2)

        def sometimes_fail(x):
            if x % 3 == 0:
                raise ValueError("Failed")
            return x * 2

        items = list(range(20))
        result = processor.process_batch(items, sometimes_fail)

        assert result.total_items == len(items)
        assert result.processed_items + result.failed_items == result.total_items
        assert len(result.results) == result.processed_items
        assert len(result.errors) == result.failed_items


class TestRateLimiterProperties:
    """Property-based tests for rate limiter"""

    def test_remaining_never_negative(self):
        """Test remaining tokens is never negative"""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=5)

        for _ in range(20):
            result = limiter.check("test")
            assert result.remaining >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
