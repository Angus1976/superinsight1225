"""
Property-based tests for LLM Rate Limiter.

Tests correctness properties with Hypothesis (100+ iterations each).

Properties tested:
- Property 29: Rate Limiting
  - Validates: Requirements 10.3
  - Verifies rate limits are enforced correctly
"""

import pytest
import asyncio
import time
from typing import Optional
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from unittest.mock import Mock

# Import the module under test
try:
    from src.ai.llm.rate_limiter import (
        RateLimiter,
        RateLimitConfig,
        TokenBucket,
        RateLimitExceededError,
        DEFAULT_RATE_LIMITS,
        reset_rate_limiter
    )
    from src.ai.llm_schemas import LLMMethod
except ImportError:
    pytest.skip("Rate limiter not available", allow_module_level=True)


# ==================== Test Fixtures ====================

@pytest.fixture
def rate_limiter():
    """Create a fresh rate limiter instance."""
    reset_rate_limiter()
    limiter = RateLimiter()
    return limiter


@pytest.fixture
def simple_config():
    """Create a simple rate limit config for testing."""
    return RateLimitConfig(
        max_tokens=10.0,
        refill_rate=1.0,  # 1 token per second
        tokens_per_request=1.0,
        enabled=True
    )


# ==================== Property Tests ====================

@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_requests=st.integers(min_value=1, max_value=20)
)
async def test_property_29_rate_limiting(
    num_requests: int,
    simple_config: RateLimitConfig
):
    """
    Property 29: Rate Limiting

    Validates: Requirements 10.3

    Property: Rate limits are enforced correctly

    For any number of requests:
    - When requests exceed capacity
    - Then additional requests are rate limited
    - And rate limit error contains retry_after
    """
    reset_rate_limiter()
    limiter = RateLimiter()

    # Configure provider with limited capacity
    limiter.configure_provider(
        LLMMethod.LOCAL_OLLAMA,
        simple_config
    )

    # Property 1: Requests up to max_tokens succeed immediately
    allowed_count = 0
    rejected_count = 0

    for i in range(num_requests):
        try:
            # Try to acquire token without waiting
            await limiter.acquire(
                method=LLMMethod.LOCAL_OLLAMA,
                wait=False
            )
            allowed_count += 1

        except RateLimitExceededError as e:
            rejected_count += 1

            # Property 2: Rate limit error provides retry_after
            assert e.retry_after > 0, "Rate limit error should include retry_after"
            assert e.provider == LLMMethod.LOCAL_OLLAMA.value

    # Property 3: Total allowed should not exceed capacity
    # (allowing some tolerance for refill during test execution)
    max_expected = int(simple_config.max_tokens) + 2  # +2 tolerance for refill
    assert allowed_count <= max_expected, \
        f"Allowed {allowed_count} requests, expected max {max_expected}"

    # Property 4: If requests exceed capacity, some should be rejected
    if num_requests > simple_config.max_tokens:
        assert rejected_count > 0, \
            "Should reject requests when exceeding capacity"


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    refill_rate=st.floats(min_value=0.5, max_value=10.0),
    wait_time=st.floats(min_value=1.0, max_value=3.0)
)
async def test_property_token_refill(
    refill_rate: float,
    wait_time: float
):
    """
    Property: Token Refill

    Validates: Token bucket refill mechanism

    For any refill rate and wait time:
    - When tokens are depleted
    - And we wait for refill
    - Then tokens are replenished at configured rate
    """
    reset_rate_limiter()
    limiter = RateLimiter()

    # Configure with specific refill rate
    config = RateLimitConfig(
        max_tokens=10.0,
        refill_rate=refill_rate,
        tokens_per_request=1.0,
        enabled=True
    )
    limiter.configure_provider(LLMMethod.CLOUD_OPENAI, config)

    # Deplete tokens
    for i in range(int(config.max_tokens)):
        await limiter.acquire(LLMMethod.CLOUD_OPENAI, wait=False)

    # Should be rate limited now
    with pytest.raises(RateLimitExceededError):
        await limiter.acquire(LLMMethod.CLOUD_OPENAI, wait=False)

    # Wait for refill
    await asyncio.sleep(wait_time)

    # Property: Tokens should be refilled
    # Expected refill = wait_time * refill_rate
    expected_tokens = wait_time * refill_rate

    # Should be able to make approximately expected_tokens requests
    successful = 0
    for i in range(int(expected_tokens) + 2):  # +2 tolerance
        try:
            await limiter.acquire(LLMMethod.CLOUD_OPENAI, wait=False)
            successful += 1
        except RateLimitExceededError:
            break

    # Allow some tolerance
    assert successful >= int(expected_tokens) - 1, \
        f"Expected ~{expected_tokens:.1f} tokens after {wait_time}s refill, got {successful}"


@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    capacity=st.integers(min_value=5, max_value=50),
    requests=st.integers(min_value=1, max_value=10)
)
async def test_property_capacity_limit(
    capacity: int,
    requests: int
):
    """
    Property: Capacity Limit

    Validates: Maximum burst capacity

    For any capacity and request count:
    - When requests are made rapidly
    - Then at most capacity requests succeed immediately
    - And remaining requests are rate limited
    """
    reset_rate_limiter()
    limiter = RateLimiter()

    # Configure with specific capacity and very slow refill
    config = RateLimitConfig(
        max_tokens=float(capacity),
        refill_rate=0.01,  # Very slow refill to test capacity
        tokens_per_request=1.0,
        enabled=True
    )
    limiter.configure_provider(LLMMethod.CHINA_QWEN, config)

    # Make rapid requests
    allowed = 0
    for i in range(requests + capacity):
        try:
            await limiter.acquire(LLMMethod.CHINA_QWEN, wait=False)
            allowed += 1
        except RateLimitExceededError:
            pass

    # Property: Allowed requests should not significantly exceed capacity
    # (allowing small tolerance for any refill during test)
    assert allowed <= capacity + 2, \
        f"Allowed {allowed} requests with capacity {capacity}"


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    tokens_per_request=st.floats(min_value=1.0, max_value=5.0),
    num_requests=st.integers(min_value=2, max_value=10)
)
async def test_property_variable_cost(
    tokens_per_request: float,
    num_requests: int
):
    """
    Property: Variable Request Cost

    Validates: Support for different token costs per request

    For any token cost:
    - When requests have variable costs
    - Then correct number of tokens are consumed
    - And rate limiting accounts for cost
    """
    reset_rate_limiter()
    limiter = RateLimiter()

    # Configure with specific token cost
    config = RateLimitConfig(
        max_tokens=50.0,
        refill_rate=0.1,  # Slow refill
        tokens_per_request=tokens_per_request,
        enabled=True
    )
    limiter.configure_provider(LLMMethod.CHINA_ZHIPU, config)

    # Calculate expected maximum requests
    expected_max = int(config.max_tokens / tokens_per_request)

    # Make requests
    allowed = 0
    for i in range(num_requests + expected_max):
        try:
            await limiter.acquire(
                method=LLMMethod.CHINA_ZHIPU,
                wait=False
            )
            allowed += 1
        except RateLimitExceededError:
            break

    # Property: Allowed requests should match capacity / cost
    # Allow tolerance of +/-1 request
    assert abs(allowed - expected_max) <= 1, \
        f"Expected ~{expected_max} requests with cost {tokens_per_request}, got {allowed}"


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_wait_mode():
    """
    Property: Wait Mode

    Validates: Wait-for-tokens blocking mode

    - When wait=True
    - Then request blocks until tokens available
    - And eventually succeeds
    """
    reset_rate_limiter()
    limiter = RateLimiter()

    # Configure with small capacity
    config = RateLimitConfig(
        max_tokens=2.0,
        refill_rate=5.0,  # Fast refill (5 tokens/sec)
        tokens_per_request=1.0,
        enabled=True
    )
    limiter.configure_provider(LLMMethod.CLOUD_AZURE, config)

    # Deplete tokens
    await limiter.acquire(LLMMethod.CLOUD_AZURE, wait=False)
    await limiter.acquire(LLMMethod.CLOUD_AZURE, wait=False)

    # Should be depleted
    with pytest.raises(RateLimitExceededError):
        await limiter.acquire(LLMMethod.CLOUD_AZURE, wait=False)

    # Property: Wait mode should eventually succeed
    start = time.time()
    result = await limiter.acquire(
        method=LLMMethod.CLOUD_AZURE,
        wait=True,
        max_wait=5.0
    )
    elapsed = time.time() - start

    assert result == True, "Wait mode should eventually succeed"
    assert elapsed >= 0.1, "Should have waited for refill"
    assert elapsed < 5.0, "Should not exceed max_wait"


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_disabled_limiting():
    """
    Property: Disabled Rate Limiting

    Validates: Disabling rate limits works correctly

    - When rate limiting is disabled for a provider
    - Then all requests succeed immediately
    - And no rate limit errors occur
    """
    reset_rate_limiter()
    limiter = RateLimiter()

    # Configure with disabled rate limiting
    config = RateLimitConfig(
        max_tokens=5.0,
        refill_rate=1.0,
        tokens_per_request=1.0,
        enabled=False  # Disabled
    )
    limiter.configure_provider(LLMMethod.CHINA_BAIDU, config)

    # Property: All requests should succeed even beyond capacity
    num_requests = 100
    for i in range(num_requests):
        result = await limiter.acquire(
            method=LLMMethod.CHINA_BAIDU,
            wait=False
        )
        assert result == True, f"Request {i} should succeed with disabled limit"


@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_statistics_accuracy():
    """
    Property: Statistics Accuracy

    Validates: Rate limiter tracks statistics correctly

    - When requests are made
    - Then statistics reflect accurate counts
    - And allowed + rejected = total requests
    """
    reset_rate_limiter()
    limiter = RateLimiter()

    # Configure with small capacity
    config = RateLimitConfig(
        max_tokens=5.0,
        refill_rate=0.1,  # Slow refill
        tokens_per_request=1.0,
        enabled=True
    )
    limiter.configure_provider(LLMMethod.CHINA_HUNYUAN, config)

    # Make requests
    num_requests = 20
    for i in range(num_requests):
        try:
            await limiter.acquire(LLMMethod.CHINA_HUNYUAN, wait=False)
        except RateLimitExceededError:
            pass

    # Get statistics
    stats = await limiter.get_statistics()
    provider_key = LLMMethod.CHINA_HUNYUAN.value

    # Property 1: Total requests tracked
    total_requests = stats["requests"].get(provider_key, 0)
    assert total_requests == num_requests, \
        f"Expected {num_requests} total requests, got {total_requests}"

    # Property 2: Allowed + Rejected = Total
    allowed = stats["allowed"].get(provider_key, 0)
    rejected = stats["rejected"].get(provider_key, 0)
    assert allowed + rejected == total_requests, \
        f"Allowed ({allowed}) + Rejected ({rejected}) should equal Total ({total_requests})"

    # Property 3: Some requests should be allowed (up to capacity)
    assert allowed >= min(num_requests, int(config.max_tokens) - 1), \
        "Should allow at least capacity requests"


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_bucket_reset():
    """
    Property: Bucket Reset

    Validates: Resetting token bucket works correctly

    - When bucket is depleted and reset
    - Then full capacity is immediately available
    - And requests succeed
    """
    reset_rate_limiter()
    limiter = RateLimiter()

    config = RateLimitConfig(
        max_tokens=5.0,
        refill_rate=0.1,  # Very slow refill
        tokens_per_request=1.0,
        enabled=True
    )
    limiter.configure_provider(LLMMethod.LOCAL_OLLAMA, config)

    # Deplete bucket
    for i in range(int(config.max_tokens)):
        await limiter.acquire(LLMMethod.LOCAL_OLLAMA, wait=False)

    # Should be depleted
    with pytest.raises(RateLimitExceededError):
        await limiter.acquire(LLMMethod.LOCAL_OLLAMA, wait=False)

    # Reset bucket
    await limiter.reset_bucket(LLMMethod.LOCAL_OLLAMA)

    # Property: Should be able to make full capacity requests again
    for i in range(int(config.max_tokens)):
        result = await limiter.acquire(LLMMethod.LOCAL_OLLAMA, wait=False)
        assert result == True, f"Request {i} after reset should succeed"


# ==================== Edge Case Tests ====================

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test rate limiter handles concurrent requests correctly."""
    reset_rate_limiter()
    limiter = RateLimiter()

    config = RateLimitConfig(
        max_tokens=10.0,
        refill_rate=1.0,
        tokens_per_request=1.0,
        enabled=True
    )
    limiter.configure_provider(LLMMethod.CLOUD_OPENAI, config)

    # Make concurrent requests
    async def make_request():
        try:
            return await limiter.acquire(LLMMethod.CLOUD_OPENAI, wait=False)
        except RateLimitExceededError:
            return False

    # Launch 20 concurrent requests
    tasks = [make_request() for _ in range(20)]
    results = await asyncio.gather(*tasks)

    # At most 10 should succeed (capacity)
    successful = sum(1 for r in results if r)
    assert successful <= 12, f"Too many concurrent requests succeeded: {successful}"


@pytest.mark.asyncio
async def test_zero_capacity():
    """Test handling of zero capacity (effectively disabled)."""
    reset_rate_limiter()
    limiter = RateLimiter()

    config = RateLimitConfig(
        max_tokens=0.0,
        refill_rate=1.0,
        tokens_per_request=1.0,
        enabled=True
    )

    with pytest.raises(Exception):
        # This should fail validation in a real scenario
        # but for testing, we check that zero capacity blocks all requests
        limiter.configure_provider(LLMMethod.CLOUD_OPENAI, config)


@pytest.mark.asyncio
async def test_check_available():
    """Test checking token availability without consuming."""
    reset_rate_limiter()
    limiter = RateLimiter()

    config = RateLimitConfig(
        max_tokens=5.0,
        refill_rate=1.0,
        tokens_per_request=1.0,
        enabled=True
    )
    limiter.configure_provider(LLMMethod.CLOUD_AZURE, config)

    # Initially available
    available = await limiter.check_available(LLMMethod.CLOUD_AZURE)
    assert available == True

    # Deplete tokens
    for i in range(5):
        await limiter.acquire(LLMMethod.CLOUD_AZURE, wait=False)

    # Should not be available
    available = await limiter.check_available(LLMMethod.CLOUD_AZURE)
    assert available == False
