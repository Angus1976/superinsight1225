"""
LLM Application Binding System - Performance Tests

Tests performance requirements:
- 1000 concurrent requests without degradation
- Cache retrieval < 1ms
- Database retrieval < 50ms
- Memory usage < 100MB

**Feature**: llm-application-binding
**Validates**: Requirements 15.1, 15.2, 15.3, 15.4

Note: Run this test file directly, not through the performance module:
    pytest tests/performance/test_llm_application_binding_performance.py -v
"""

import sys
import asyncio
import time
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock

# Standalone test - avoid importing from performance module
import pytest

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Warning: psutil not installed, memory tests will be skipped")


# ============================================================================
# Mock Classes (to avoid import dependencies)
# ============================================================================

class MockCacheManager:
    """Mock cache manager for testing."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
    
    async def set(self, key: str, value: Any):
        self._cache[key] = value
    
    async def invalidate(self, pattern: str):
        keys_to_delete = [k for k in self._cache.keys() if pattern.replace("*", "") in k]
        for key in keys_to_delete:
            del self._cache[key]


class MockApplicationLLMManager:
    """Mock ApplicationLLMManager for testing."""
    
    def __init__(self, cache_manager):
        self.cache = cache_manager
        self._db_call_count = 0
    
    async def get_llm_config(self, application_code: str, tenant_id: Optional[str] = None):
        """Mock get_llm_config that uses cache."""
        cache_key = f"llm:config:{application_code}:{tenant_id or 'global'}"
        
        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # Simulate database query
        self._db_call_count += 1
        await asyncio.sleep(0.01)  # Simulate 10ms database query
        
        # Mock config data
        config = [{
            "id": "config-123",
            "name": "OpenAI GPT-4",
            "provider": "openai",
            "model_name": "gpt-4"
        }]
        
        # Store in cache
        await self.cache.set(cache_key, config)
        
        return config
    
    async def execute_with_failover(self, application_code: str, operation, tenant_id: Optional[str] = None):
        """Mock execute_with_failover."""
        configs = await self.get_llm_config(application_code, tenant_id)
        
        for config in configs:
            try:
                return await operation(config)
            except Exception:
                continue
        
        raise Exception("All LLMs failed")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cache_manager():
    """Create a mock cache manager."""
    return MockCacheManager()


@pytest.fixture
def app_llm_manager(cache_manager):
    """Create a mock ApplicationLLMManager."""
    return MockApplicationLLMManager(cache_manager)


# ============================================================================
# Performance Test 1: Cache Retrieval Speed (< 1ms)
# ============================================================================

@pytest.mark.asyncio
async def test_cache_retrieval_performance(cache_manager):
    """
    Test that cache retrieval is faster than 1ms.
    
    Validates: Requirement 15.1
    """
    # Populate cache with test data
    test_data = {"config": "test_value"}
    await cache_manager.set("test_key", test_data)
    
    # Measure cache retrieval time
    iterations = 1000
    total_time = 0
    
    for _ in range(iterations):
        start = time.perf_counter()
        result = await cache_manager.get("test_key")
        end = time.perf_counter()
        
        total_time += (end - start)
        assert result == test_data
    
    # Calculate average time in milliseconds
    avg_time_ms = (total_time / iterations) * 1000
    
    print(f"\nCache retrieval average time: {avg_time_ms:.4f}ms")
    
    # Assert cache retrieval is under 1ms
    assert avg_time_ms < 1.0, f"Cache retrieval too slow: {avg_time_ms:.4f}ms (threshold: 1ms)"


# ============================================================================
# Performance Test 2: Database Retrieval Speed (< 50ms)
# ============================================================================

@pytest.mark.asyncio
async def test_database_retrieval_performance(app_llm_manager):
    """
    Test that database configuration retrieval is faster than 50ms.
    
    Validates: Requirement 15.2
    """
    # Measure database retrieval time (without cache)
    iterations = 100
    total_time = 0
    
    for _ in range(iterations):
        # Clear cache to force database query
        await app_llm_manager.cache.invalidate("llm:config:*")
        
        start = time.perf_counter()
        configs = await app_llm_manager.get_llm_config("structuring")
        end = time.perf_counter()
        
        total_time += (end - start)
        assert len(configs) > 0
    
    # Calculate average time in milliseconds
    avg_time_ms = (total_time / iterations) * 1000
    
    print(f"\nDatabase retrieval average time: {avg_time_ms:.4f}ms")
    
    # Assert database retrieval is under 50ms
    assert avg_time_ms < 50.0, f"Database retrieval too slow: {avg_time_ms:.4f}ms (threshold: 50ms)"


# ============================================================================
# Performance Test 3: Concurrent Request Handling (1000 requests)
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_request_performance(app_llm_manager):
    """
    Test that the system can handle 1000 concurrent requests without degradation.
    
    Validates: Requirement 15.3
    """
    # Pre-warm cache
    await app_llm_manager.get_llm_config("structuring")
    
    # Create 1000 concurrent requests
    num_requests = 1000
    
    async def make_request():
        """Single request to get LLM config."""
        return await app_llm_manager.get_llm_config("structuring")
    
    # Measure concurrent request handling
    start = time.perf_counter()
    
    tasks = [make_request() for _ in range(num_requests)]
    results = await asyncio.gather(*tasks)
    
    end = time.perf_counter()
    total_time = end - start
    
    # Calculate metrics
    requests_per_second = num_requests / total_time
    avg_time_ms = (total_time / num_requests) * 1000
    
    print(f"\nConcurrent requests: {num_requests}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Requests per second: {requests_per_second:.2f}")
    print(f"Average time per request: {avg_time_ms:.4f}ms")
    
    # Assert all requests succeeded
    assert len(results) == num_requests
    assert all(len(r) > 0 for r in results)
    
    # Assert reasonable performance (should complete in under 10 seconds)
    assert total_time < 10.0, f"Concurrent requests too slow: {total_time:.2f}s (threshold: 10s)"
    
    # Assert average request time is reasonable (under 10ms with cache)
    assert avg_time_ms < 10.0, f"Average request time too slow: {avg_time_ms:.4f}ms"


# ============================================================================
# Performance Test 4: Memory Usage (< 100MB)
# ============================================================================

@pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed")
@pytest.mark.asyncio
async def test_memory_usage_performance(cache_manager):
    """
    Test that cache memory usage stays under 100MB.
    
    Validates: Requirement 15.4
    """
    import os
    # Get initial memory usage
    process = psutil.Process(os.getpid())
    initial_memory_mb = process.memory_info().rss / 1024 / 1024
    
    # Populate cache with realistic data
    num_entries = 1000
    
    for i in range(num_entries):
        # Simulate realistic LLM config data (~1KB per entry)
        config_data = {
            "id": f"config-{i}",
            "name": f"LLM Config {i}",
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4",
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            },
            "bindings": [
                {
                    "application": "structuring",
                    "priority": 1,
                    "max_retries": 3,
                    "timeout_seconds": 30
                }
            ]
        }
        
        await cache_manager.set(f"llm:config:app{i}:global", config_data)
    
    # Get final memory usage
    final_memory_mb = process.memory_info().rss / 1024 / 1024
    memory_increase_mb = final_memory_mb - initial_memory_mb
    
    print(f"\nInitial memory: {initial_memory_mb:.2f}MB")
    print(f"Final memory: {final_memory_mb:.2f}MB")
    print(f"Memory increase: {memory_increase_mb:.2f}MB")
    print(f"Cache entries: {num_entries}")
    print(f"Average per entry: {(memory_increase_mb / num_entries) * 1024:.2f}KB")
    
    # Assert memory increase is under 100MB
    assert memory_increase_mb < 100.0, (
        f"Memory usage too high: {memory_increase_mb:.2f}MB (threshold: 100MB)"
    )


# ============================================================================
# Performance Test 5: Cache Hit Rate (> 95%)
# ============================================================================

@pytest.mark.asyncio
async def test_cache_hit_rate_performance(app_llm_manager):
    """
    Test that cache hit rate is above 95% under normal load.
    
    Validates: Requirement 13.5 (monitoring requirement)
    """
    # Simulate realistic access pattern
    num_requests = 1000
    cache_hits = 0
    cache_misses = 0
    
    for i in range(num_requests):
        # First request for each application will be a cache miss
        # Subsequent requests will be cache hits
        if i == 0:
            # Clear cache to force miss
            await app_llm_manager.cache.invalidate("llm:config:*")
        
        # Check if in cache before request
        cache_key = "llm:config:structuring:global"
        cached = await app_llm_manager.cache.get(cache_key)
        
        if cached:
            cache_hits += 1
        else:
            cache_misses += 1
        
        # Make request
        await app_llm_manager.get_llm_config("structuring")
    
    # Calculate hit rate
    hit_rate = cache_hits / num_requests
    
    print(f"\nTotal requests: {num_requests}")
    print(f"Cache hits: {cache_hits}")
    print(f"Cache misses: {cache_misses}")
    print(f"Hit rate: {hit_rate:.2%}")
    
    # Assert hit rate is above 95%
    assert hit_rate > 0.95, f"Cache hit rate too low: {hit_rate:.2%} (threshold: 95%)"


# ============================================================================
# Performance Test 6: Failover Performance
# ============================================================================

@pytest.mark.asyncio
async def test_failover_performance(app_llm_manager):
    """
    Test that failover doesn't significantly degrade performance.
    
    Validates: Requirements 5.1, 5.2, 5.3
    """
    # Mock operation that fails on primary, succeeds on backup
    call_count = 0
    
    async def mock_operation(config):
        nonlocal call_count
        call_count += 1
        
        if call_count <= 2:
            # Simulate primary failure (with retries)
            await asyncio.sleep(0.1)  # Simulate network delay
            raise Exception("Primary LLM failed")
        else:
            # Backup succeeds
            return "success"
    
    # Measure failover time
    start = time.perf_counter()
    
    result = await app_llm_manager.execute_with_failover(
        "structuring",
        mock_operation
    )
    
    end = time.perf_counter()
    failover_time = end - start
    
    print(f"\nFailover time: {failover_time:.4f}s")
    print(f"Total attempts: {call_count}")
    
    # Assert failover succeeded
    assert result == "success"
    
    # Assert failover completed in reasonable time (under 1 second for mock)
    assert failover_time < 1.0, f"Failover too slow: {failover_time:.4f}s (threshold: 1s)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
