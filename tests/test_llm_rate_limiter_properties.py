"""
Property-based tests for LLM Rate Limiter.

Tests Property 29 from the LLM Integration design specification.

Property 29: Rate Limiting
- For any time window, the number of requests sent to a provider should not
  exceed the configured rate limit for that provider.

**Validates: Requirements 10.3**
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from collections import defaultdict

from src.ai.llm_schemas import LLMMethod
from src.ai.llm.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitExceededError,
    TokenBucket,
    get_rate_limiter,
    reset_rate_limiter,
    DEFAULT_RATE_LIMITS,
)


# Test constants
TEST_TIMEOUT = 10.0  # Maximum test duration in seconds

# Strategies for property-based testing
method_strategy = st.sampled_from(list(LLMMethod))
positive_float_strategy = st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False)
positive_int_strategy = st.integers(min_value=1, max_value=100)
rate_config_strategy = st.builds(
    RateLimitConfig,
    max_tokens=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    refill_rate=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    tokens_per_request=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
    enabled=st.just(True),
)


# ==================== Helper Functions ====================

def create_test_rate_limiter(
    method: LLMMethod,
    max_tokens: float = 10.0,
    refill_rate: float = 1.0,
    tokens_per_request: float = 1.0,
    enabled: bool = True,
) -> RateLimiter:
    """Create a rate limiter with specific configuration for testing."""
    config = RateLimitConfig(
        max_tokens=max_tokens,
        refill_rate=refill_rate,
        tokens_per_request=tokens_per_request,
        enabled=enabled,
    )
    return RateLimiter(
        default_config=config,
        provider_configs={method: config},
    )


# ==================== Property 29: Rate Limiting ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    method=method_strategy,
    max_tokens=st.integers(min_value=5, max_value=20),
    num_requests=st.integers(min_value=1, max_value=30),
)
def test_property_29_rate_limit_enforced(method, max_tokens, num_requests):
    """
    Property 29: Rate Limiting
    
    For any time window, the number of requests sent to a provider should not
    exceed the configured rate limit for that provider.
    
    This test verifies that when we make more requests than the bucket capacity,
    the excess requests are rejected.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        # Create rate limiter with specific capacity
        # Use a very small refill rate to effectively disable refill during test
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=float(max_tokens),
            refill_rate=0.001,  # Very slow refill (effectively none during test)
            tokens_per_request=1.0,
        )
        
        allowed_count = 0
        rejected_count = 0
        
        # Try to make num_requests requests
        for _ in range(num_requests):
            try:
                await rate_limiter.acquire(method, wait=False)
                allowed_count += 1
            except RateLimitExceededError:
                rejected_count += 1
        
        # Verify: allowed requests should not exceed max_tokens
        assert allowed_count <= max_tokens, \
            f"Allowed {allowed_count} requests but max_tokens is {max_tokens}"
        
        # Verify: if we made more requests than capacity, some should be rejected
        if num_requests > max_tokens:
            assert rejected_count > 0, \
                f"Expected some rejections when {num_requests} > {max_tokens}"
        
        # Verify: total should equal num_requests
        assert allowed_count + rejected_count == num_requests, \
            f"Total {allowed_count + rejected_count} != {num_requests}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    method=method_strategy,
    max_tokens=st.integers(min_value=5, max_value=15),  # Use integers to avoid floating point issues
)
def test_property_29_burst_capacity_respected(method, max_tokens):
    """
    Property 29: Burst capacity is respected.
    
    The rate limiter should allow up to max_tokens requests in a burst,
    then reject additional requests until tokens are replenished.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=float(max_tokens),
            refill_rate=0.001,  # Very slow refill (effectively none during test)
            tokens_per_request=1.0,
        )
        
        # Make exactly max_tokens requests - all should succeed
        for i in range(max_tokens):
            try:
                await rate_limiter.acquire(method, wait=False)
            except RateLimitExceededError:
                pytest.fail(f"Request {i+1} should have been allowed (max_tokens={max_tokens})")
        
        # Next request should be rejected
        with pytest.raises(RateLimitExceededError):
            await rate_limiter.acquire(method, wait=False)
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    method=method_strategy,
    refill_rate=st.floats(min_value=10.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_property_29_token_replenishment(method, refill_rate):
    """
    Property 29: Tokens are replenished over time.
    
    After depleting tokens, waiting should allow new requests.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        max_tokens = 5.0
        
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=max_tokens,
            refill_rate=refill_rate,
            tokens_per_request=1.0,
        )
        
        # Deplete all tokens
        for _ in range(int(max_tokens)):
            await rate_limiter.acquire(method, wait=False)
        
        # Verify bucket is empty
        with pytest.raises(RateLimitExceededError):
            await rate_limiter.acquire(method, wait=False)
        
        # Wait for at least one token to replenish
        wait_time = 1.0 / refill_rate + 0.01  # Time for 1 token + buffer
        await asyncio.sleep(wait_time)
        
        # Should be able to make at least one request now
        try:
            await rate_limiter.acquire(method, wait=False)
        except RateLimitExceededError:
            pytest.fail("Token should have been replenished after waiting")
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    method=method_strategy,
    tokens_per_request=st.integers(min_value=1, max_value=5),  # Use integers to avoid floating point issues
)
def test_property_29_tokens_per_request_respected(method, tokens_per_request):
    """
    Property 29: Tokens per request configuration is respected.
    
    Each request should consume the configured number of tokens.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        max_tokens = 10.0
        
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=max_tokens,
            refill_rate=0.001,  # Very slow refill (effectively none during test)
            tokens_per_request=float(tokens_per_request),
        )
        
        # Calculate expected number of requests
        expected_requests = int(max_tokens / tokens_per_request)
        
        # Make requests until rejected
        allowed_count = 0
        for _ in range(expected_requests + 5):  # Try more than expected
            try:
                await rate_limiter.acquire(method, wait=False)
                allowed_count += 1
            except RateLimitExceededError:
                break
        
        # Verify allowed count matches expected
        assert allowed_count == expected_requests, \
            f"Expected {expected_requests} requests with tokens_per_request={tokens_per_request}, got {allowed_count}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_29_disabled_rate_limiting_allows_all(method):
    """
    Property 29: Disabled rate limiting allows all requests.
    
    When rate limiting is disabled for a provider, all requests should be allowed.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=1.0,  # Very low limit
            refill_rate=0.0,
            tokens_per_request=1.0,
            enabled=False,  # Disabled
        )
        
        # All requests should succeed even though limit is 1
        for _ in range(100):
            try:
                await rate_limiter.acquire(method, wait=False)
            except RateLimitExceededError:
                pytest.fail("Rate limiting should be disabled")
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    method=method_strategy,
    max_tokens=st.integers(min_value=5, max_value=20),
)
def test_property_29_retry_after_accuracy(method, max_tokens):
    """
    Property 29: Retry-after time is accurate.
    
    When rate limit is exceeded, the retry_after value should indicate
    when tokens will be available.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        # Use a very slow refill rate to prevent tokens from replenishing during test
        refill_rate = 0.1  # 0.1 tokens per second (very slow)
        
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=float(max_tokens),
            refill_rate=refill_rate,
            tokens_per_request=1.0,
        )
        
        # Deplete all tokens
        for _ in range(max_tokens):
            await rate_limiter.acquire(method, wait=False)
        
        # Get retry_after from exception
        try:
            await rate_limiter.acquire(method, wait=False)
            pytest.fail("Should have raised RateLimitExceededError")
        except RateLimitExceededError as e:
            retry_after = e.retry_after
        
        # Verify retry_after is reasonable
        # Should be approximately 1/refill_rate for 1 token
        expected_wait = 1.0 / refill_rate
        
        assert retry_after >= 0, "retry_after should be non-negative"
        assert retry_after <= expected_wait * 2, \
            f"retry_after {retry_after} seems too long (expected ~{expected_wait})"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    method=method_strategy,
    max_tokens=st.floats(min_value=5.0, max_value=15.0, allow_nan=False, allow_infinity=False),
)
def test_property_29_wait_mode_eventually_succeeds(method, max_tokens):
    """
    Property 29: Wait mode eventually succeeds when tokens replenish.
    
    When using wait=True, the request should eventually succeed
    after tokens are replenished.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        refill_rate = 100.0  # Fast refill for testing
        
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=max_tokens,
            refill_rate=refill_rate,
            tokens_per_request=1.0,
        )
        
        # Deplete all tokens
        for _ in range(int(max_tokens)):
            await rate_limiter.acquire(method, wait=False)
        
        # This should wait and eventually succeed
        start_time = time.time()
        await rate_limiter.acquire(method, wait=True, max_wait=1.0)
        elapsed = time.time() - start_time
        
        # Should have waited some time
        assert elapsed > 0, "Should have waited for token replenishment"
        assert elapsed < 1.0, f"Wait time {elapsed}s exceeded max_wait"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    method=method_strategy,
    num_requests=st.integers(min_value=5, max_value=20),
)
def test_property_29_statistics_tracking(method, num_requests):
    """
    Property 29: Statistics are tracked correctly.
    
    The rate limiter should accurately track requests, allowed, and rejected counts.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        max_tokens = 5.0
        
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=max_tokens,
            refill_rate=0.001,  # Very slow refill (effectively none during test)
            tokens_per_request=1.0,
        )
        
        allowed_count = 0
        rejected_count = 0
        
        for _ in range(num_requests):
            try:
                await rate_limiter.acquire(method, wait=False)
                allowed_count += 1
            except RateLimitExceededError:
                rejected_count += 1
        
        # Get statistics
        stats = await rate_limiter.get_statistics()
        
        # Verify statistics match actual counts
        assert stats["requests"].get(method.value, 0) == num_requests, \
            f"Request count mismatch"
        assert stats["allowed"].get(method.value, 0) == allowed_count, \
            f"Allowed count mismatch"
        assert stats["rejected"].get(method.value, 0) == rejected_count, \
            f"Rejected count mismatch"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    methods=st.lists(method_strategy, min_size=2, max_size=4, unique=True),
)
def test_property_29_per_provider_isolation(methods):
    """
    Property 29: Rate limits are isolated per provider.
    
    Depleting tokens for one provider should not affect other providers.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        max_tokens = 5.0
        
        # Create rate limiter with same config for all providers
        provider_configs = {
            m: RateLimitConfig(
                max_tokens=max_tokens,
                refill_rate=0.001,  # Very slow refill (effectively none during test)
                tokens_per_request=1.0,
            )
            for m in methods
        }
        
        rate_limiter = RateLimiter(provider_configs=provider_configs)
        
        # Deplete tokens for first provider
        first_method = methods[0]
        for _ in range(int(max_tokens)):
            await rate_limiter.acquire(first_method, wait=False)
        
        # Verify first provider is rate limited
        with pytest.raises(RateLimitExceededError):
            await rate_limiter.acquire(first_method, wait=False)
        
        # Other providers should still have tokens
        for other_method in methods[1:]:
            try:
                await rate_limiter.acquire(other_method, wait=False)
            except RateLimitExceededError:
                pytest.fail(f"Provider {other_method.value} should not be rate limited")
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_29_check_available_does_not_consume(method):
    """
    Property 29: check_available does not consume tokens.
    
    Checking availability should not affect the token count.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        max_tokens = 5.0
        
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=max_tokens,
            refill_rate=0.001,  # Very slow refill (effectively none during test)
            tokens_per_request=1.0,
        )
        
        # Check availability multiple times
        for _ in range(10):
            available = await rate_limiter.check_available(method)
            assert available, "Should be available"
        
        # All tokens should still be available
        for _ in range(int(max_tokens)):
            await rate_limiter.acquire(method, wait=False)
        
        # Now should be rate limited
        with pytest.raises(RateLimitExceededError):
            await rate_limiter.acquire(method, wait=False)
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(method=method_strategy)
def test_property_29_reset_bucket_restores_capacity(method):
    """
    Property 29: Resetting bucket restores full capacity.
    
    After reset, the bucket should have max_tokens available.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        max_tokens = 5.0
        
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=max_tokens,
            refill_rate=0.001,  # Very slow refill (effectively none during test)
            tokens_per_request=1.0,
        )
        
        # Deplete all tokens
        for _ in range(int(max_tokens)):
            await rate_limiter.acquire(method, wait=False)
        
        # Verify depleted
        with pytest.raises(RateLimitExceededError):
            await rate_limiter.acquire(method, wait=False)
        
        # Reset bucket
        await rate_limiter.reset_bucket(method)
        
        # Should have full capacity again
        for _ in range(int(max_tokens)):
            await rate_limiter.acquire(method, wait=False)
    
    asyncio.run(run_test())


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    method=method_strategy,
    max_tokens=st.floats(min_value=10.0, max_value=30.0, allow_nan=False, allow_infinity=False),
    refill_rate=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
)
def test_property_29_concurrent_requests_respect_limit(method, max_tokens, refill_rate):
    """
    Property 29: Concurrent requests respect rate limit.
    
    Even with concurrent requests, the total allowed should not exceed
    the rate limit.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=max_tokens,
            refill_rate=refill_rate,
            tokens_per_request=1.0,
        )
        
        num_concurrent = int(max_tokens * 2)  # More than capacity
        
        async def try_acquire():
            try:
                await rate_limiter.acquire(method, wait=False)
                return True
            except RateLimitExceededError:
                return False
        
        # Make concurrent requests
        tasks = [try_acquire() for _ in range(num_concurrent)]
        results = await asyncio.gather(*tasks)
        
        allowed_count = sum(1 for r in results if r)
        
        # Allowed should not exceed max_tokens (with small buffer for refill)
        max_allowed = max_tokens + (refill_rate * 0.1)  # Allow for some refill during test
        assert allowed_count <= max_allowed, \
            f"Allowed {allowed_count} concurrent requests but limit is {max_tokens}"
    
    asyncio.run(run_test())


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    method=method_strategy,
    new_max_tokens=st.integers(min_value=5, max_value=20),  # Use integers to avoid floating point issues
)
def test_property_29_reconfiguration_takes_effect(method, new_max_tokens):
    """
    Property 29: Reconfiguring rate limit takes effect immediately.
    
    After reconfiguration, the new limits should be enforced.
    
    **Validates: Requirements 10.3**
    """
    async def run_test():
        # Start with high limit
        rate_limiter = create_test_rate_limiter(
            method=method,
            max_tokens=100.0,
            refill_rate=0.001,  # Very slow refill (effectively none during test)
            tokens_per_request=1.0,
        )
        
        # Reconfigure with new limit
        new_config = RateLimitConfig(
            max_tokens=float(new_max_tokens),
            refill_rate=0.001,  # Very slow refill (effectively none during test)
            tokens_per_request=1.0,
        )
        rate_limiter.configure_provider(method, new_config)
        
        # Make requests until rejected
        allowed_count = 0
        for _ in range(new_max_tokens + 10):
            try:
                await rate_limiter.acquire(method, wait=False)
                allowed_count += 1
            except RateLimitExceededError:
                break
        
        # Should match new limit
        assert allowed_count == new_max_tokens, \
            f"Expected {new_max_tokens} requests after reconfiguration, got {allowed_count}"
    
    asyncio.run(run_test())


# ==================== Token Bucket Unit Tests ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(config=rate_config_strategy)
def test_token_bucket_initialization(config):
    """Test that token bucket initializes with max tokens."""
    bucket = TokenBucket(config=config)
    
    assert bucket.tokens == config.max_tokens, \
        f"Bucket should start with {config.max_tokens} tokens, got {bucket.tokens}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    max_tokens=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    refill_rate=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    tokens_per_request=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
)
def test_token_bucket_try_acquire_consumes_tokens(max_tokens, refill_rate, tokens_per_request):
    """Test that try_acquire consumes the correct number of tokens."""
    # Ensure tokens_per_request <= max_tokens for valid test
    assume(tokens_per_request <= max_tokens)
    
    config = RateLimitConfig(
        max_tokens=max_tokens,
        refill_rate=refill_rate,
        tokens_per_request=tokens_per_request,
        enabled=True,
    )
    bucket = TokenBucket(config=config)
    initial_tokens = bucket.tokens
    
    # Acquire tokens
    result = bucket.try_acquire()
    
    assert result == True, "Should succeed with full bucket when tokens_per_request <= max_tokens"
    expected_tokens = initial_tokens - config.tokens_per_request
    # Allow small floating point tolerance
    assert abs(bucket.tokens - expected_tokens) < 0.01, \
        f"Expected {expected_tokens} tokens, got {bucket.tokens}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    max_tokens=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    refill_rate=st.floats(min_value=1.0, max_value=10.0, allow_nan=False, allow_infinity=False),
)
def test_token_bucket_time_until_available(max_tokens, refill_rate):
    """Test that time_until_available returns correct wait time."""
    config = RateLimitConfig(
        max_tokens=max_tokens,
        refill_rate=refill_rate,
        tokens_per_request=1.0,
    )
    bucket = TokenBucket(config=config)
    
    # Deplete all tokens
    while bucket.try_acquire():
        pass
    
    # Get wait time
    wait_time = bucket.time_until_available()
    
    # Should be approximately 1/refill_rate
    expected_wait = 1.0 / refill_rate
    
    assert wait_time >= 0, "Wait time should be non-negative"
    # Allow some tolerance for timing
    assert wait_time <= expected_wait * 1.5, \
        f"Wait time {wait_time} seems too long (expected ~{expected_wait})"


# ==================== Integration Tests ====================

def test_default_rate_limits_configured():
    """Test that default rate limits are configured for all providers."""
    for method in LLMMethod:
        if method in DEFAULT_RATE_LIMITS:
            config = DEFAULT_RATE_LIMITS[method]
            assert config.max_tokens > 0, f"Invalid max_tokens for {method}"
            assert config.refill_rate >= 0, f"Invalid refill_rate for {method}"
            assert config.tokens_per_request > 0, f"Invalid tokens_per_request for {method}"


def test_singleton_rate_limiter():
    """Test that get_rate_limiter returns singleton instance."""
    async def run_test():
        reset_rate_limiter()
        
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        
        assert limiter1 is limiter2, "Should return same instance"
        
        reset_rate_limiter()
    
    asyncio.run(run_test())


def test_rate_limit_exceeded_error_attributes():
    """Test RateLimitExceededError has correct attributes."""
    error = RateLimitExceededError(
        provider="test_provider",
        retry_after=30.0,
        message="Custom message",
    )
    
    assert error.provider == "test_provider"
    assert error.retry_after == 30.0
    assert error.message == "Custom message"
    # The str() of the exception is the message
    assert str(error) == "Custom message"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
