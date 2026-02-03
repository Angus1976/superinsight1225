# Async/Sync Safety - Quick Reference Guide

**Last Updated**: 2026-02-03  
**Status**: ✅ Active  
**Priority**: CRITICAL

## The 3 Golden Rules

### Rule 1: Use asyncio.Lock in Async Code

```python
# ❌ WRONG - Causes deadlock
import threading
lock = threading.Lock()

async def my_function():
    with lock:  # DEADLOCK!
        pass

# ✅ CORRECT - Non-blocking
import asyncio
lock = asyncio.Lock()

async def my_function():
    async with lock:  # Safe
        pass
```

### Rule 2: Use await asyncio.sleep() in Async Code

```python
# ❌ WRONG - Blocks event loop
import time
async def wait_for_service():
    time.sleep(5)  # Blocks 5 seconds!

# ✅ CORRECT - Non-blocking
import asyncio
async def wait_for_service():
    await asyncio.sleep(5)  # Safe
```

### Rule 3: Use run_in_executor for Blocking Operations

```python
# ❌ WRONG - Blocks event loop for 1 second
import psutil
async def collect_metrics():
    cpu = psutil.cpu_percent(interval=1)  # Blocks!

# ✅ CORRECT - Non-blocking
import asyncio
import psutil
async def collect_metrics():
    loop = asyncio.get_event_loop()
    cpu = await loop.run_in_executor(None, psutil.cpu_percent, 1)
```

## Quick Checklist

When writing async code, verify:

- [ ] Using `asyncio.Lock()` not `threading.Lock()`
- [ ] Using `async with lock:` not `with lock:`
- [ ] Using `await asyncio.sleep()` not `time.sleep()`
- [ ] Using `run_in_executor()` for blocking I/O
- [ ] All methods marked `async def` if they use await
- [ ] All calls to async functions use `await`
- [ ] No blocking operations in request handlers

## Common Patterns

### Pattern 1: Async Lock

```python
import asyncio

class MyService:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.data = {}
    
    async def update(self, key, value):
        async with self._lock:
            self.data[key] = value
```

### Pattern 2: Blocking Operation in Executor

```python
import asyncio
import psutil

async def get_cpu_usage():
    loop = asyncio.get_event_loop()
    cpu = await loop.run_in_executor(None, psutil.cpu_percent, 1)
    return cpu
```

### Pattern 3: Async Sleep

```python
import asyncio

async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

### Pattern 4: Concurrent Tasks

```python
import asyncio

async def main():
    # Run multiple tasks concurrently
    results = await asyncio.gather(
        task1(),
        task2(),
        task3()
    )
    return results
```

## What to Look For in Code Review

### ❌ Red Flags

1. `threading.Lock()` in async function
2. `time.sleep()` in async function
3. `with lock:` in async function (should be `async with`)
4. Blocking I/O without `run_in_executor`
5. Missing `await` on async function calls
6. Missing `async def` on functions that use `await`

### ✅ Green Flags

1. `asyncio.Lock()` for async synchronization
2. `await asyncio.sleep()` for delays
3. `async with lock:` for lock acquisition
4. `run_in_executor()` for blocking operations
5. `await` on all async function calls
6. `async def` on all functions using `await`

## Files with Fixes (2026-02-03)

These files have been updated to follow async/sync safety rules:

- ✅ `src/monitoring/health_check.py`
- ✅ `src/monitoring/service_alert.py`
- ✅ `src/system/prometheus_integration.py`
- ✅ `src/system/monitoring.py`
- ✅ `src/system/resource_optimizer.py`
- ✅ `src/system/health_monitor.py`

## Testing

Run async safety tests:
```bash
python3 -m pytest tests/async_safety/test_async_locks.py -v
```

## Resources

- Full Rules: `.kiro/steering/async-sync-safety.md`
- Implementation Details: `.kiro/specs/async-sync-safety-fixes/IMPLEMENTATION_SUMMARY.md`
- Completion Report: `.kiro/specs/async-sync-safety-fixes/COMPLETION_REPORT.md`
- Test Suite: `tests/async_safety/test_async_locks.py`

## Need Help?

1. Check the full rules: `.kiro/steering/async-sync-safety.md`
2. Look at fixed examples in the files listed above
3. Run the test suite to verify your changes
4. Ask for code review before merging

---

**Remember**: Async code is fast code. Blocking operations make it slow. Use the right tools for the job!
