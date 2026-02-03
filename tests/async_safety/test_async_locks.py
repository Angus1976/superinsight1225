"""
Simple tests for async lock usage without complex imports.
"""

import asyncio
import pytest
import inspect


def test_asyncio_lock_is_available():
    """Verify asyncio.Lock is available"""
    lock = asyncio.Lock()
    assert isinstance(lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_asyncio_lock_basic_usage():
    """Test basic asyncio.Lock usage"""
    lock = asyncio.Lock()
    
    async with lock:
        value = 42
    
    assert value == 42


@pytest.mark.asyncio
async def test_asyncio_lock_concurrent_access():
    """Test concurrent access with asyncio.Lock"""
    lock = asyncio.Lock()
    counter = 0
    
    async def increment():
        nonlocal counter
        async with lock:
            temp = counter
            await asyncio.sleep(0.001)
            counter = temp + 1
    
    # Run 10 concurrent increments
    await asyncio.gather(*[increment() for _ in range(10)])
    
    # Should be 10, not less due to race conditions
    assert counter == 10, f"Expected 10, got {counter}"


@pytest.mark.asyncio
async def test_no_blocking_with_asyncio_sleep():
    """Verify asyncio.sleep doesn't block event loop"""
    import time
    
    start = time.time()
    
    async def task1():
        await asyncio.sleep(0.1)
        return "task1"
    
    async def task2():
        await asyncio.sleep(0.1)
        return "task2"
    
    # Run both concurrently
    results = await asyncio.gather(task1(), task2())
    
    elapsed = time.time() - start
    
    # Should take ~0.1s, not 0.2s (which would indicate blocking)
    assert elapsed < 0.15, f"Took {elapsed:.2f}s, should be ~0.1s"
    assert results == ["task1", "task2"]


@pytest.mark.asyncio
async def test_executor_for_blocking_operations():
    """Test run_in_executor for blocking operations"""
    import time
    
    def blocking_operation():
        time.sleep(0.05)
        return 42
    
    loop = asyncio.get_event_loop()
    
    start = time.time()
    
    # Run blocking operation in executor
    result = await loop.run_in_executor(None, blocking_operation)
    
    elapsed = time.time() - start
    
    assert result == 42
    assert elapsed >= 0.05, "Should take at least 50ms"


@pytest.mark.asyncio
async def test_executor_doesnt_block_event_loop():
    """Verify executor doesn't block event loop"""
    import time
    
    def blocking_operation():
        time.sleep(0.1)
        return "blocked"
    
    loop = asyncio.get_event_loop()
    
    async def concurrent_task():
        await asyncio.sleep(0.05)
        return "concurrent"
    
    start = time.time()
    
    # Run blocking operation and concurrent task together
    results = await asyncio.gather(
        loop.run_in_executor(None, blocking_operation),
        concurrent_task()
    )
    
    elapsed = time.time() - start
    
    # Should take ~0.1s (max of both), not 0.15s (sum)
    assert elapsed < 0.15, f"Took {elapsed:.2f}s, should be ~0.1s"
    assert results == ["blocked", "concurrent"]


def test_async_function_detection():
    """Test that we can detect async functions"""
    
    async def async_func():
        pass
    
    def sync_func():
        pass
    
    assert inspect.iscoroutinefunction(async_func)
    assert not inspect.iscoroutinefunction(sync_func)


@pytest.mark.asyncio
async def test_multiple_concurrent_locks():
    """Test multiple concurrent lock acquisitions"""
    lock = asyncio.Lock()
    results = []
    
    async def worker(n):
        async with lock:
            results.append(f"start_{n}")
            await asyncio.sleep(0.01)
            results.append(f"end_{n}")
    
    # Run 5 workers concurrently
    await asyncio.gather(*[worker(i) for i in range(5)])
    
    # Verify no interleaving (lock worked)
    for i in range(5):
        start_idx = results.index(f"start_{i}")
        end_idx = results.index(f"end_{i}")
        assert end_idx == start_idx + 1, f"Lock not working for worker {i}"


@pytest.mark.asyncio
async def test_timeout_protection():
    """Test timeout protection for async operations"""
    
    async def slow_operation():
        await asyncio.sleep(10)
        return "done"
    
    try:
        result = await asyncio.wait_for(slow_operation(), timeout=0.1)
        assert False, "Should have timed out"
    except asyncio.TimeoutError:
        pass  # Expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
