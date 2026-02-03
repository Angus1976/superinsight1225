# Async/Sync Safety Rules for FastAPI Development

**Version**: 1.0  
**Status**: ✅ Active  
**Last Updated**: 2026-01-16  
**Priority**: CRITICAL

## Overview

This document establishes mandatory rules for writing async-safe code in FastAPI applications to prevent deadlocks, blocking, and performance issues caused by mixing synchronous and asynchronous code incorrectly.

## Critical Issue Identified

**Date**: 2026-01-16  
**Problem**: API endpoints hanging/timing out due to threading.Lock usage in async context  
**Root Cause**: `threading.Lock` used with `with` statement in async middleware/handlers  
**Impact**: Complete API unresponsiveness, requests timing out after 5-10 seconds

### Specific Code Pattern That Caused Deadlock

```python
# ❌ WRONG - This causes deadlock in async context
class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()  # Synchronous lock
    
    def increment_counter(self, name: str, value: float = 1.0):
        with self._lock:  # Blocks async event loop
            # ... operations ...
            pass

# Used in async middleware
class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # This calls increment_counter which uses threading.Lock
        metrics_collector.increment_counter("requests.total")  # DEADLOCK!
        response = await call_next(request)
        return response
```

**Why This Fails**:
1. `threading.Lock` is designed for multi-threaded synchronous code
2. In async context, when one coroutine acquires the lock, it blocks the entire event loop
3. Other coroutines waiting for the lock cannot proceed, causing deadlock
4. FastAPI runs on a single-threaded async event loop by default

## Mandatory Rules

### Rule 1: NEVER Use threading.Lock in Async Code

**❌ FORBIDDEN**:
```python
import threading

class MyClass:
    def __init__(self):
        self._lock = threading.Lock()  # WRONG for async
    
    def my_method(self):
        with self._lock:  # Will deadlock in async context
            pass
```

**✅ CORRECT**:
```python
import asyncio

class MyClass:
    def __init__(self):
        self._lock = asyncio.Lock()  # Correct for async
    
    async def my_method(self):
        async with self._lock:  # Async-safe
            pass
```

### Rule 2: Use Async Locks for Async Code

**Lock Types by Context**:

| Context | Correct Lock Type | Usage Pattern |
|---------|------------------|---------------|
| Async functions/coroutines | `asyncio.Lock()` | `async with lock:` |
| Async functions/coroutines | `asyncio.Semaphore()` | `async with semaphore:` |
| Sync functions (threads) | `threading.Lock()` | `with lock:` |
| Sync functions (threads) | `threading.RLock()` | `with lock:` |

**Example - Async Lock**:
```python
import asyncio

class AsyncSafeCollector:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.data = {}
    
    async def update_data(self, key: str, value: Any):
        async with self._lock:
            self.data[key] = value
    
    async def get_data(self, key: str):
        async with self._lock:
            return self.data.get(key)
```

### Rule 3: Avoid Blocking Operations in Async Context

**❌ FORBIDDEN in Async Functions**:
```python
async def my_handler():
    # Blocking I/O
    with open('file.txt', 'r') as f:  # BLOCKS event loop
        data = f.read()
    
    # Blocking sleep
    time.sleep(1)  # BLOCKS event loop
    
    # Synchronous database query
    result = db.execute(query)  # BLOCKS event loop
    
    # CPU-intensive operation
    result = heavy_computation()  # BLOCKS event loop
```

**✅ CORRECT**:
```python
import asyncio
import aiofiles

async def my_handler():
    # Async I/O
    async with aiofiles.open('file.txt', 'r') as f:
        data = await f.read()
    
    # Async sleep
    await asyncio.sleep(1)
    
    # Async database query
    result = await db.execute_async(query)
    
    # CPU-intensive operation in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, heavy_computation)
```

### Rule 4: Use run_in_executor for Blocking Operations

When you MUST use blocking operations (legacy libraries, CPU-intensive tasks):

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class MyService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def blocking_operation(self, data):
        """Synchronous blocking operation"""
        # Heavy computation or blocking I/O
        return process_data(data)
    
    async def async_wrapper(self, data):
        """Async wrapper for blocking operation"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self.blocking_operation,
            data
        )
        return result
```

### Rule 5: FastAPI Middleware Must Be Fully Async

**❌ WRONG - Mixed sync/async**:
```python
class MyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Calling sync function with blocking lock
        self.sync_tracker.start()  # Uses threading.Lock internally
        response = await call_next(request)
        self.sync_tracker.end()    # Uses threading.Lock internally
        return response
```

**✅ CORRECT - Fully async**:
```python
class MyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._lock = asyncio.Lock()
        self.data = {}
    
    async def dispatch(self, request: Request, call_next):
        # All operations are async-safe
        async with self._lock:
            self.data[request.url.path] = time.time()
        
        response = await call_next(request)
        
        async with self._lock:
            del self.data[request.url.path]
        
        return response
```

### Rule 6: Database Operations Must Be Async

**❌ WRONG - Sync database in async context**:
```python
async def get_user(user_id: str):
    # Synchronous database session
    db = next(get_db_session())  # BLOCKS event loop
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user
    finally:
        db.close()
```

**✅ CORRECT - Async database**:
```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(user_id: str, db: AsyncSession):
    # Async database session
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    return user
```

### Rule 7: Avoid psutil Blocking Calls in Hot Paths

**❌ WRONG - Blocking psutil in request handler**:
```python
async def get_system_status():
    # These block for 1 second EACH
    cpu_percent = psutil.cpu_percent(interval=1)  # BLOCKS 1s
    cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)  # BLOCKS 1s
    return {"cpu": cpu_percent}
```

**✅ CORRECT - Background collection**:
```python
class MetricsCollector:
    def __init__(self):
        self.cached_metrics = {}
        self._lock = asyncio.Lock()
    
    async def _collect_loop(self):
        """Background task for metrics collection"""
        while True:
            # Collect in background, not in request path
            cpu_percent = await asyncio.get_event_loop().run_in_executor(
                None, psutil.cpu_percent, 1
            )
            
            async with self._lock:
                self.cached_metrics['cpu'] = cpu_percent
            
            await asyncio.sleep(10)  # Collect every 10 seconds
    
    async def get_metrics(self):
        """Fast read from cache"""
        async with self._lock:
            return self.cached_metrics.copy()

# In FastAPI endpoint
async def get_system_status():
    # Returns immediately from cache
    return await metrics_collector.get_metrics()
```

## Detection and Prevention

### Code Review Checklist

Before merging any async code, verify:

- [ ] No `threading.Lock`, `threading.RLock`, or `threading.Semaphore` in async functions
- [ ] All locks use `asyncio.Lock()` with `async with` syntax
- [ ] No `time.sleep()` in async functions (use `await asyncio.sleep()`)
- [ ] No synchronous file I/O in async functions (use `aiofiles`)
- [ ] No synchronous database queries in async functions
- [ ] No `psutil` calls with `interval` parameter in request handlers
- [ ] All middleware is fully async
- [ ] Blocking operations wrapped in `run_in_executor()`

### Static Analysis Tools

Use these tools to detect async/sync issues:

```bash
# Install async linters
pip install pylint-async asyncio-lint

# Run checks
pylint --load-plugins=pylint_async your_module.py
python -m asyncio_lint your_module.py
```

### Testing for Deadlocks

```python
import asyncio
import pytest

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test that concurrent requests don't deadlock"""
    async def make_request():
        # Simulate API request
        return await client.get("/api/endpoint")
    
    # Run 100 concurrent requests
    tasks = [make_request() for _ in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # All should succeed without timeout
    assert all(r.status_code == 200 for r in results if not isinstance(r, Exception))
```

## Migration Guide

### Converting Sync Code to Async

**Step 1: Identify Blocking Operations**
```python
# Find all instances of:
- threading.Lock()
- time.sleep()
- open() / file I/O
- requests.get() / requests.post()
- db.query() / db.execute()
- psutil calls with interval parameter
```

**Step 2: Replace with Async Equivalents**
```python
# Before
import threading
import time

class SyncService:
    def __init__(self):
        self._lock = threading.Lock()
    
    def process(self, data):
        with self._lock:
            time.sleep(1)
            return data

# After
import asyncio

class AsyncService:
    def __init__(self):
        self._lock = asyncio.Lock()
    
    async def process(self, data):
        async with self._lock:
            await asyncio.sleep(1)
            return data
```

**Step 3: Update Function Signatures**
```python
# Before
def my_function():
    pass

# After
async def my_function():
    pass
```

**Step 4: Update All Callers**
```python
# Before
result = my_function()

# After
result = await my_function()
```

## Performance Considerations

### Lock Contention

**Problem**: Too many coroutines waiting for the same lock

**Solution**: Use lock-free data structures or reduce critical section size

```python
# ❌ Large critical section
async def update_metrics(self, key, value):
    async with self._lock:
        # Long operation inside lock
        processed = await process_data(value)  # BAD
        self.metrics[key] = processed

# ✅ Minimal critical section
async def update_metrics(self, key, value):
    # Process outside lock
    processed = await process_data(value)
    
    # Only lock for the write
    async with self._lock:
        self.metrics[key] = processed
```

### Lock-Free Alternatives

For simple counters and flags, consider lock-free approaches:

```python
import asyncio
from collections import defaultdict

class LockFreeCounter:
    """Lock-free counter using asyncio-safe operations"""
    def __init__(self):
        self.counts = defaultdict(int)
    
    def increment(self, key: str):
        # Dict operations are atomic in CPython
        self.counts[key] += 1
    
    def get(self, key: str) -> int:
        return self.counts[key]
```

## Common Patterns

### Pattern 1: Async Context Manager

```python
class AsyncResource:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.resource = None
    
    async def __aenter__(self):
        async with self._lock:
            self.resource = await acquire_resource()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            await release_resource(self.resource)

# Usage
async with AsyncResource() as resource:
    await resource.do_something()
```

### Pattern 2: Async Iterator

```python
class AsyncDataStream:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.data = []
    
    async def __aiter__(self):
        return self
    
    async def __anext__(self):
        async with self._lock:
            if not self.data:
                raise StopAsyncIteration
            return self.data.pop(0)

# Usage
async for item in AsyncDataStream():
    await process(item)
```

### Pattern 3: Background Task with Shared State

```python
class BackgroundProcessor:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.queue = asyncio.Queue()
        self.results = {}
        self._task = None
    
    async def start(self):
        self._task = asyncio.create_task(self._process_loop())
    
    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _process_loop(self):
        while True:
            item = await self.queue.get()
            result = await process_item(item)
            
            async with self._lock:
                self.results[item.id] = result
    
    async def get_result(self, item_id: str):
        async with self._lock:
            return self.results.get(item_id)
```

## Debugging Async Issues

### Enable Async Debug Mode

```python
import asyncio
import logging

# Enable debug mode
asyncio.get_event_loop().set_debug(True)

# Enable asyncio logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('asyncio').setLevel(logging.DEBUG)
```

### Detect Blocking Calls

```python
import asyncio
import warnings

# Warn about slow callbacks
asyncio.get_event_loop().slow_callback_duration = 0.1  # 100ms

# This will warn if any callback takes > 100ms
```

### Timeout Protection

```python
async def safe_operation():
    try:
        async with asyncio.timeout(5.0):  # Python 3.11+
            result = await potentially_slow_operation()
        return result
    except asyncio.TimeoutError:
        logger.error("Operation timed out")
        return None

# For Python < 3.11
async def safe_operation_legacy():
    try:
        result = await asyncio.wait_for(
            potentially_slow_operation(),
            timeout=5.0
        )
        return result
    except asyncio.TimeoutError:
        logger.error("Operation timed out")
        return None
```

## References

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [FastAPI Async/Await](https://fastapi.tiangolo.com/async/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [aiofiles documentation](https://github.com/Tinche/aiofiles)

## Enforcement

**This document is MANDATORY for all SuperInsight development.**

Violations will result in:
1. PR rejection
2. Required code rework
3. Additional code review

---

**Last Incident**: 2026-01-16 - API deadlock due to threading.Lock in async middleware  
**Resolution**: Removed all threading.Lock usage, simplified middleware to avoid locks  
**Prevention**: This document created to prevent future occurrences
