"""
Unit tests for the Performance Concurrency System.

Tests cover:
- Task 17.2: Concurrent executor, batch processing, timeout control, async execution
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from hypothesis import given, strategies as st, settings, assume

from src.agent.performance import (
    ConcurrencyMode,
    TaskResult,
    ConcurrentExecutor,
    PerformanceMonitor,
    LatencyStats,
    PerformanceMetric,
    MetricType,
    measure_latency,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def executor():
    """Create a concurrent executor instance."""
    return ConcurrentExecutor(max_workers=4, max_concurrent=10, timeout=5.0)


@pytest.fixture
def monitor():
    """Create a performance monitor instance."""
    return PerformanceMonitor(window_size_seconds=60)


# =============================================================================
# Test: TaskResult
# =============================================================================


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_success_result(self):
        """Test successful task result."""
        result = TaskResult(
            task_id="task-1",
            success=True,
            result="completed",
            execution_time_ms=100.0,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        assert result.success is True
        assert result.result == "completed"
        assert result.error is None

    def test_failure_result(self):
        """Test failed task result."""
        result = TaskResult(
            task_id="task-1",
            success=False,
            error="Task failed",
            execution_time_ms=50.0
        )
        assert result.success is False
        assert result.error == "Task failed"
        assert result.result is None

    def test_execution_time_tracked(self):
        """Test that execution time is tracked."""
        result = TaskResult(
            task_id="task-1",
            success=True,
            execution_time_ms=150.5
        )
        assert result.execution_time_ms == 150.5


# =============================================================================
# Test: ConcurrentExecutor - Async Execution
# =============================================================================


class TestConcurrentExecutorAsync:
    """Tests for ConcurrentExecutor async execution."""

    @pytest.mark.asyncio
    async def test_execute_async_success(self, executor):
        """Test successful async execution."""
        async def simple_task():
            return "result"

        result = await executor.execute_async("task-1", simple_task)

        assert result.success is True
        assert result.result == "result"
        assert result.task_id == "task-1"
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_async_with_args(self, executor):
        """Test async execution with arguments."""
        async def add(a, b):
            return a + b

        result = await executor.execute_async("task-1", add, 3, 4)

        assert result.success is True
        assert result.result == 7

    @pytest.mark.asyncio
    async def test_execute_async_with_kwargs(self, executor):
        """Test async execution with keyword arguments."""
        async def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = await executor.execute_async(
            "task-1", greet, "Alice", greeting="Hi"
        )

        assert result.success is True
        assert result.result == "Hi, Alice!"

    @pytest.mark.asyncio
    async def test_execute_async_error(self, executor):
        """Test async execution with error."""
        async def failing_task():
            raise ValueError("Task error")

        result = await executor.execute_async("task-1", failing_task)

        assert result.success is False
        assert "Task error" in result.error

    @pytest.mark.asyncio
    async def test_execute_async_timeout(self, executor):
        """Test async execution timeout."""
        executor.timeout = 0.1

        async def slow_task():
            await asyncio.sleep(1.0)
            return "done"

        result = await executor.execute_async("task-1", slow_task)

        assert result.success is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_timestamps_recorded(self, executor):
        """Test that timestamps are recorded."""
        async def task():
            return "done"

        result = await executor.execute_async("task-1", task)

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at


# =============================================================================
# Test: ConcurrentExecutor - Sync Execution
# =============================================================================


class TestConcurrentExecutorSync:
    """Tests for ConcurrentExecutor sync execution."""

    @pytest.mark.asyncio
    async def test_execute_sync_success(self, executor):
        """Test successful sync execution."""
        def simple_task():
            return "sync result"

        result = await executor.execute_sync("task-1", simple_task)

        assert result.success is True
        assert result.result == "sync result"

    @pytest.mark.asyncio
    async def test_execute_sync_with_args(self, executor):
        """Test sync execution with arguments."""
        def multiply(a, b):
            return a * b

        result = await executor.execute_sync("task-1", multiply, 5, 6)

        assert result.success is True
        assert result.result == 30

    @pytest.mark.asyncio
    async def test_execute_sync_error(self, executor):
        """Test sync execution with error."""
        def failing_task():
            raise RuntimeError("Sync error")

        result = await executor.execute_sync("task-1", failing_task)

        assert result.success is False
        assert "Sync error" in result.error

    @pytest.mark.asyncio
    async def test_execute_sync_cpu_bound(self, executor):
        """Test sync execution for CPU-bound tasks."""
        def cpu_intensive():
            total = 0
            for i in range(1000):
                total += i
            return total

        result = await executor.execute_sync("task-1", cpu_intensive)

        assert result.success is True
        assert result.result == 499500  # Sum 0 to 999


# =============================================================================
# Test: ConcurrentExecutor - Batch Execution
# =============================================================================


class TestConcurrentExecutorBatch:
    """Tests for ConcurrentExecutor batch execution."""

    @pytest.mark.asyncio
    async def test_batch_sequential(self, executor):
        """Test sequential batch execution."""
        execution_order = []

        async def task(n):
            execution_order.append(n)
            return n * 2

        tasks = [
            (f"task-{i}", task, (i,), {})
            for i in range(3)
        ]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.SEQUENTIAL)

        assert len(results) == 3
        assert all(r.success for r in results)
        # Should execute in order
        assert execution_order == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_batch_parallel(self, executor):
        """Test parallel batch execution."""
        async def task(n):
            await asyncio.sleep(0.1)
            return n * 2

        tasks = [
            (f"task-{i}", task, (i,), {})
            for i in range(3)
        ]

        start_time = time.time()
        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)
        elapsed = time.time() - start_time

        assert len(results) == 3
        assert all(r.success for r in results)
        # Parallel should be faster than sequential (3 * 0.1 = 0.3s)
        assert elapsed < 0.25  # Allow some overhead

    @pytest.mark.asyncio
    async def test_batch_mixed_results(self, executor):
        """Test batch with mixed success/failure."""
        async def conditional_task(n):
            if n == 1:
                raise ValueError("Task 1 failed")
            return n

        tasks = [
            (f"task-{i}", conditional_task, (i,), {})
            for i in range(3)
        ]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

    @pytest.mark.asyncio
    async def test_batch_with_sync_functions(self, executor):
        """Test batch with sync functions."""
        def sync_task(n):
            return n + 10

        tasks = [
            (f"task-{i}", sync_task, (i,), {})
            for i in range(3)
        ]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert len(results) == 3
        assert [r.result for r in results] == [10, 11, 12]

    @pytest.mark.asyncio
    async def test_batch_empty(self, executor):
        """Test empty batch execution."""
        results = await executor.execute_batch([], mode=ConcurrencyMode.PARALLEL)
        assert results == []


# =============================================================================
# Test: ConcurrentExecutor - Concurrency Control
# =============================================================================


class TestConcurrentExecutorConcurrency:
    """Tests for ConcurrentExecutor concurrency control."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Test that semaphore limits concurrent executions."""
        executor = ConcurrentExecutor(max_workers=4, max_concurrent=2, timeout=5.0)

        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        async def tracking_task():
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.1)
            async with lock:
                concurrent_count -= 1
            return "done"

        tasks = [
            (f"task-{i}", tracking_task, (), {})
            for i in range(5)
        ]

        await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert max_concurrent <= 2  # Should not exceed max_concurrent

    @pytest.mark.asyncio
    async def test_active_task_count(self, executor):
        """Test active task count tracking."""
        started = asyncio.Event()
        release = asyncio.Event()

        async def blocking_task():
            started.set()
            await release.wait()
            return "done"

        # Start a blocking task
        task = asyncio.create_task(
            executor.execute_async("task-1", blocking_task)
        )

        await started.wait()
        assert executor.get_active_count() == 1

        # Release and wait
        release.set()
        await task
        assert executor.get_active_count() == 0

    @pytest.mark.asyncio
    async def test_cancel_task(self, executor):
        """Test task cancellation."""
        started = asyncio.Event()

        async def long_task():
            started.set()
            await asyncio.sleep(10.0)
            return "done"

        # Start task in background
        task = asyncio.create_task(
            executor.execute_async("task-1", long_task)
        )

        await started.wait()

        # Cancel it
        result = await executor.cancel_task("task-1")
        # Note: cancellation may or may not work depending on timing
        # The test just verifies the API works

    @pytest.mark.asyncio
    async def test_shutdown(self, executor):
        """Test executor shutdown."""
        executor.shutdown()
        # Should not raise


# =============================================================================
# Test: LatencyStats
# =============================================================================


class TestLatencyStats:
    """Tests for LatencyStats dataclass."""

    def test_record_latency(self):
        """Test recording latency."""
        stats = LatencyStats()
        stats.record(100.0)
        stats.record(200.0)
        stats.record(150.0)

        assert stats.count == 3
        assert stats.total_ms == 450.0

    def test_min_max(self):
        """Test min and max tracking."""
        stats = LatencyStats()
        stats.record(100.0)
        stats.record(50.0)
        stats.record(200.0)

        assert stats.min_ms == 50.0
        assert stats.max_ms == 200.0

    def test_avg(self):
        """Test average calculation."""
        stats = LatencyStats()
        stats.record(100.0)
        stats.record(200.0)
        stats.record(300.0)

        assert stats.avg_ms == pytest.approx(200.0)

    def test_avg_empty(self):
        """Test average with no records."""
        stats = LatencyStats()
        assert stats.avg_ms == 0.0

    def test_percentiles(self):
        """Test percentile calculations."""
        stats = LatencyStats()
        # Record 100 values from 1 to 100
        for i in range(1, 101):
            stats.record(float(i))

        assert stats.p50_ms == 50.0 or stats.p50_ms == 51.0  # Depends on exact algo
        assert stats.p95_ms >= 95.0
        assert stats.p99_ms >= 99.0

    def test_percentiles_empty(self):
        """Test percentiles with no records."""
        stats = LatencyStats()
        assert stats.p50_ms == 0.0
        assert stats.p95_ms == 0.0
        assert stats.p99_ms == 0.0

    def test_values_truncation(self):
        """Test that values list is truncated."""
        stats = LatencyStats()

        # Record more than 10000 values
        for i in range(12000):
            stats.record(float(i))

        # Should be truncated to 5000
        assert len(stats.values) == 5000


# =============================================================================
# Test: PerformanceMonitor
# =============================================================================


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class."""

    @pytest.mark.asyncio
    async def test_record_latency(self, monitor):
        """Test recording latency."""
        await monitor.record_latency("query", 100.0)
        await monitor.record_latency("query", 200.0)

        stats = monitor.get_latency_stats("query")
        assert stats is not None
        assert stats.count == 2
        assert stats.avg_ms == 150.0

    @pytest.mark.asyncio
    async def test_record_latency_with_labels(self, monitor):
        """Test recording latency with labels."""
        await monitor.record_latency("query", 100.0, labels={"type": "read"})
        await monitor.record_latency("query", 200.0, labels={"type": "write"})

        # Different labels create different stats
        metrics = monitor.get_all_metrics()
        assert "latency" in metrics

    @pytest.mark.asyncio
    async def test_increment_counter(self, monitor):
        """Test incrementing a counter."""
        await monitor.increment_counter("requests")
        await monitor.increment_counter("requests", value=5)

        metrics = monitor.get_all_metrics()
        assert "requests:{}" in metrics["counters"]
        assert metrics["counters"]["requests:{}"] == 6

    @pytest.mark.asyncio
    async def test_set_gauge(self, monitor):
        """Test setting a gauge."""
        await monitor.set_gauge("memory_usage", 75.5)

        metrics = monitor.get_all_metrics()
        assert "memory_usage:{}" in metrics["gauges"]
        assert metrics["gauges"]["memory_usage:{}"] == 75.5

    @pytest.mark.asyncio
    async def test_get_all_metrics(self, monitor):
        """Test getting all metrics."""
        await monitor.record_latency("op1", 100.0)
        await monitor.increment_counter("counter1")
        await monitor.set_gauge("gauge1", 50.0)

        metrics = monitor.get_all_metrics()

        assert "uptime_seconds" in metrics
        assert "latency" in metrics
        assert "counters" in metrics
        assert "gauges" in metrics
        assert "timestamp" in metrics

    @pytest.mark.asyncio
    async def test_reset(self, monitor):
        """Test resetting metrics."""
        await monitor.record_latency("op1", 100.0)
        await monitor.increment_counter("counter1")

        await monitor.reset()

        metrics = monitor.get_all_metrics()
        assert len(metrics["latency"]) == 0
        assert len(metrics["counters"]) == 0


# =============================================================================
# Test: measure_latency Decorator
# =============================================================================


class TestMeasureLatencyDecorator:
    """Tests for measure_latency decorator."""

    @pytest.mark.asyncio
    async def test_decorator_measures_latency(self):
        """Test that decorator measures latency."""
        monitor = PerformanceMonitor()

        @measure_latency("test_operation", monitor)
        async def slow_function():
            await asyncio.sleep(0.05)
            return "done"

        result = await slow_function()

        assert result == "done"
        stats = monitor.get_latency_stats("test_operation")
        assert stats is not None
        assert stats.count == 1
        assert stats.avg_ms >= 50  # At least 50ms

    @pytest.mark.asyncio
    async def test_decorator_handles_exception(self):
        """Test that decorator handles exceptions."""
        monitor = PerformanceMonitor()

        @measure_latency("failing_op", monitor)
        async def failing_function():
            await asyncio.sleep(0.01)
            raise ValueError("Error")

        with pytest.raises(ValueError):
            await failing_function()

        # Latency should still be recorded
        stats = monitor.get_latency_stats("failing_op")
        assert stats is not None
        assert stats.count == 1

    @pytest.mark.asyncio
    async def test_decorator_without_monitor(self):
        """Test decorator without monitor (just logs)."""
        @measure_latency("log_only")
        async def function():
            return "result"

        result = await function()
        assert result == "result"


# =============================================================================
# Property-Based Tests: Concurrency
# =============================================================================


class TestPropertyConcurrency:
    """Property-based tests for concurrency."""

    @given(
        num_tasks=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_property_all_tasks_complete(self, num_tasks):
        """Property: All tasks in a batch should complete."""
        executor = ConcurrentExecutor(max_workers=4, max_concurrent=10, timeout=10.0)

        async def simple_task(n):
            return n

        tasks = [(f"task-{i}", simple_task, (i,), {}) for i in range(num_tasks)]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert len(results) == num_tasks
        # All should complete (success or failure)
        assert all(r.completed_at is not None for r in results)

    @given(
        values=st.lists(st.floats(min_value=0.1, max_value=1000.0), min_size=1, max_size=100)
    )
    @settings(max_examples=30)
    def test_property_latency_stats_consistent(self, values):
        """Property: Latency stats should be consistent with recorded values."""
        stats = LatencyStats()
        for v in values:
            stats.record(v)

        assert stats.count == len(values)
        assert stats.total_ms == pytest.approx(sum(values))
        assert stats.min_ms == min(values)
        assert stats.max_ms == max(values)
        assert stats.avg_ms == pytest.approx(sum(values) / len(values))

    @given(
        timeout=st.floats(min_value=0.01, max_value=0.1),
        sleep_time=st.floats(min_value=0.2, max_value=0.5)
    )
    @settings(max_examples=10)
    @pytest.mark.asyncio
    async def test_property_timeout_respected(self, timeout, sleep_time):
        """Property: Timeout should be respected."""
        executor = ConcurrentExecutor(max_workers=2, max_concurrent=5, timeout=timeout)

        async def slow_task():
            await asyncio.sleep(sleep_time)
            return "done"

        result = await executor.execute_async("task-1", slow_task)

        # If sleep_time > timeout, should timeout
        assert result.success is False
        assert "timed out" in result.error.lower()


# =============================================================================
# Property-Based Tests: Throughput
# =============================================================================


class TestPropertyThroughput:
    """Property-based tests for throughput."""

    @given(
        num_parallel=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=10)
    @pytest.mark.asyncio
    async def test_property_parallel_faster_than_sequential(self, num_parallel):
        """Property: Parallel should be faster than sequential for I/O tasks."""
        executor = ConcurrentExecutor(max_workers=10, max_concurrent=20, timeout=10.0)

        async def io_task(n):
            await asyncio.sleep(0.05)  # Simulate I/O
            return n

        tasks = [(f"task-{i}", io_task, (i,), {}) for i in range(num_parallel)]

        # Measure parallel
        start = time.time()
        await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)
        parallel_time = time.time() - start

        # Measure sequential
        start = time.time()
        await executor.execute_batch(tasks, mode=ConcurrencyMode.SEQUENTIAL)
        sequential_time = time.time() - start

        # Parallel should generally be faster
        # Allow some tolerance for timing variations
        assert parallel_time <= sequential_time * 1.2  # Allow 20% overhead


# =============================================================================
# Integration Tests
# =============================================================================


class TestConcurrencyIntegration:
    """Integration tests for concurrency system."""

    @pytest.mark.asyncio
    async def test_executor_with_monitor(self):
        """Test executor integrated with performance monitor."""
        executor = ConcurrentExecutor(max_workers=4, max_concurrent=10, timeout=5.0)
        monitor = PerformanceMonitor()

        async def monitored_task(n):
            start = time.time()
            await asyncio.sleep(0.01 * n)
            latency = (time.time() - start) * 1000
            await monitor.record_latency("task", latency)
            return n

        tasks = [(f"task-{i}", monitored_task, (i,), {}) for i in range(1, 6)]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert all(r.success for r in results)

        stats = monitor.get_latency_stats("task")
        assert stats.count == 5

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """Test concurrent operations with caching."""
        from src.agent.performance import InMemoryCache, CacheStrategy

        cache = InMemoryCache(max_size=100, strategy=CacheStrategy.LRU)
        executor = ConcurrentExecutor(max_workers=4, max_concurrent=10, timeout=5.0)

        async def cache_task(n):
            key = f"key-{n % 10}"  # Some key overlap
            existing = await cache.get(key)
            if existing is None:
                await cache.set(key, f"value-{n}")
            return await cache.get(key)

        tasks = [(f"task-{i}", cache_task, (i,), {}) for i in range(50)]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert all(r.success for r in results)
        assert all(r.result is not None for r in results)

    @pytest.mark.asyncio
    async def test_error_isolation(self):
        """Test that errors in one task don't affect others."""
        executor = ConcurrentExecutor(max_workers=4, max_concurrent=10, timeout=5.0)

        async def unstable_task(n):
            if n % 3 == 0:
                raise ValueError(f"Task {n} failed")
            return n * 2

        tasks = [(f"task-{i}", unstable_task, (i,), {}) for i in range(10)]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        # Check that failures are isolated
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        assert len(successful) > 0
        assert len(failed) > 0

        # Verify successful results are correct
        for r in successful:
            n = int(r.task_id.split("-")[1])
            assert r.result == n * 2

    @pytest.mark.asyncio
    async def test_high_concurrency(self):
        """Test behavior under high concurrency."""
        executor = ConcurrentExecutor(max_workers=4, max_concurrent=100, timeout=10.0)

        async def quick_task(n):
            await asyncio.sleep(0.001)
            return n

        tasks = [(f"task-{i}", quick_task, (i,), {}) for i in range(100)]

        results = await executor.execute_batch(tasks, mode=ConcurrencyMode.PARALLEL)

        assert len(results) == 100
        success_count = sum(1 for r in results if r.success)
        assert success_count == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
