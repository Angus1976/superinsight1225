"""
Unit tests for RateLimiter class.

Tests rate limiting with sliding window algorithm and quota management.
"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import time

from src.ai_integration.rate_limiter import (
    RateLimiter,
    RateLimitResult,
    QuotaResult
)


@pytest_asyncio.fixture
async def mock_redis():
    """Create mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.zremrangebyscore = AsyncMock(return_value=0)
    redis_mock.zcard = AsyncMock(return_value=0)
    redis_mock.zrange = AsyncMock(return_value=[])
    redis_mock.zadd = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest_asyncio.fixture
async def rate_limiter(mock_redis):
    """Create RateLimiter instance with mock Redis."""
    return RateLimiter(redis_client=mock_redis)


class TestRateLimiter:
    """Test suite for RateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit check when request is allowed."""
        mock_redis.zcard.return_value = 5
        
        result = await rate_limiter.check_rate_limit("gateway-1", 60)
        
        assert result.allowed is True
        assert result.remaining == 54  # 60 - 5 - 1
        assert isinstance(result.reset_at, datetime)
        assert result.retry_after_seconds is None
        
        # Verify Redis calls
        mock_redis.zremrangebyscore.assert_called_once()
        mock_redis.zcard.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test rate limit check when limit is exceeded."""
        now = time.time()
        mock_redis.zcard.return_value = 60
        mock_redis.zrange.return_value = [(b"timestamp", now - 30)]  # 30 seconds ago
        
        result = await rate_limiter.check_rate_limit("gateway-1", 60)
        
        assert result.allowed is False
        assert result.remaining == 0
        assert isinstance(result.reset_at, datetime)
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0
        assert result.retry_after_seconds <= 60  # Should be within window
    
    @pytest.mark.asyncio
    async def test_check_quota_daily_allowed(self, rate_limiter, mock_redis):
        """Test daily quota check when request is allowed."""
        mock_redis.get.return_value = "500"
        
        result = await rate_limiter.check_quota("gateway-1", 1000, "day")
        
        assert result.allowed is True
        assert result.used == 500
        assert result.limit == 1000
        assert isinstance(result.reset_at, datetime)
        
        # Verify key format
        call_args = mock_redis.get.call_args[0][0]
        assert "quota:gateway-1:day:" in call_args
    
    @pytest.mark.asyncio
    async def test_check_quota_daily_exceeded(self, rate_limiter, mock_redis):
        """Test daily quota check when quota is exceeded."""
        mock_redis.get.return_value = "1000"
        
        result = await rate_limiter.check_quota("gateway-1", 1000, "day")
        
        assert result.allowed is False
        assert result.used == 1000
        assert result.limit == 1000
    
    @pytest.mark.asyncio
    async def test_check_quota_monthly(self, rate_limiter, mock_redis):
        """Test monthly quota check."""
        mock_redis.get.return_value = "5000"
        
        result = await rate_limiter.check_quota("gateway-1", 10000, "month")
        
        assert result.allowed is True
        assert result.used == 5000
        assert result.limit == 10000
        
        # Verify key format
        call_args = mock_redis.get.call_args[0][0]
        assert "quota:gateway-1:month:" in call_args
    
    @pytest.mark.asyncio
    async def test_check_quota_no_usage(self, rate_limiter, mock_redis):
        """Test quota check when no usage recorded."""
        mock_redis.get.return_value = None
        
        result = await rate_limiter.check_quota("gateway-1", 1000, "day")
        
        assert result.allowed is True
        assert result.used == 0
        assert result.limit == 1000
    
    @pytest.mark.asyncio
    async def test_record_request_rate_limit_only(self, rate_limiter, mock_redis):
        """Test recording request for rate limiting only."""
        await rate_limiter.record_request("gateway-1", 60)
        
        # Verify rate limit recording
        assert mock_redis.zadd.call_count == 1
        assert mock_redis.expire.call_count == 1
        
        # Verify no quota recording
        assert mock_redis.incr.call_count == 0
    
    @pytest.mark.asyncio
    async def test_record_request_with_quotas(self, rate_limiter, mock_redis):
        """Test recording request with daily and monthly quotas."""
        await rate_limiter.record_request(
            "gateway-1",
            60,
            quota_per_day=1000,
            quota_per_month=10000
        )
        
        # Verify rate limit recording
        assert mock_redis.zadd.call_count == 1
        
        # Verify quota recording (daily + monthly)
        assert mock_redis.incr.call_count == 2
        assert mock_redis.expire.call_count == 3  # rate + daily + monthly
    
    @pytest.mark.asyncio
    async def test_reset_counters(self, rate_limiter, mock_redis):
        """Test resetting all counters for a gateway."""
        await rate_limiter.reset_counters("gateway-1")
        
        # Verify deletion of all keys
        assert mock_redis.delete.call_count == 3
        
        # Verify key patterns
        delete_calls = [call[0][0] for call in mock_redis.delete.call_args_list]
        assert any("rate_limit:gateway-1" in key for key in delete_calls)
        assert any("quota:gateway-1:day:" in key for key in delete_calls)
        assert any("quota:gateway-1:month:" in key for key in delete_calls)
    
    @pytest.mark.asyncio
    async def test_get_usage_stats(self, rate_limiter, mock_redis):
        """Test getting usage statistics."""
        mock_redis.zcard.return_value = 10
        mock_redis.get.side_effect = ["500", "5000"]
        
        current_rate, daily, monthly = await rate_limiter.get_usage_stats("gateway-1")
        
        assert current_rate == 10
        assert daily == 500
        assert monthly == 5000
        
        # Verify cleanup of old entries
        mock_redis.zremrangebyscore.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_usage_stats_no_data(self, rate_limiter, mock_redis):
        """Test getting usage statistics when no data exists."""
        mock_redis.zcard.return_value = 0
        mock_redis.get.return_value = None
        
        current_rate, daily, monthly = await rate_limiter.get_usage_stats("gateway-1")
        
        assert current_rate == 0
        assert daily == 0
        assert monthly == 0
    
    @pytest.mark.asyncio
    async def test_close(self, rate_limiter, mock_redis):
        """Test closing Redis connection."""
        await rate_limiter.close()
        
        mock_redis.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sliding_window_cleanup(self, rate_limiter, mock_redis):
        """Test that old entries are cleaned up in sliding window."""
        await rate_limiter.check_rate_limit("gateway-1", 60)
        
        # Verify cleanup was called
        call_args = mock_redis.zremrangebyscore.call_args
        assert call_args is not None
        
        # Verify key and score range
        key = call_args[0][0]
        assert key == "rate_limit:gateway-1"
        assert call_args[0][1] == 0  # min score
        # max score should be approximately (now - 60)
    
    @pytest.mark.asyncio
    async def test_multiple_gateways_isolation(self, rate_limiter, mock_redis):
        """Test that different gateways have isolated counters."""
        await rate_limiter.record_request("gateway-1", 60)
        await rate_limiter.record_request("gateway-2", 60)
        
        # Verify different keys were used
        zadd_calls = [call[0][0] for call in mock_redis.zadd.call_args_list]
        assert "rate_limit:gateway-1" in zadd_calls[0]
        assert "rate_limit:gateway-2" in zadd_calls[1]
    
    @pytest.mark.asyncio
    async def test_quota_reset_time_calculation(self, rate_limiter, mock_redis):
        """Test that quota reset times are calculated correctly."""
        mock_redis.get.return_value = "0"
        
        # Test daily reset
        result_day = await rate_limiter.check_quota("gateway-1", 1000, "day")
        assert result_day.reset_at.hour == 0
        assert result_day.reset_at.minute == 0
        assert result_day.reset_at.second == 0
        
        # Test monthly reset
        result_month = await rate_limiter.check_quota("gateway-1", 10000, "month")
        assert result_month.reset_at.day == 1
        assert result_month.reset_at.hour == 0


class TestRateLimiterIntegration:
    """Integration tests for RateLimiter with timing."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_timing(self, rate_limiter, mock_redis):
        """Test rate limit with realistic timing."""
        # Simulate 5 requests
        mock_redis.zcard.return_value = 5
        
        result = await rate_limiter.check_rate_limit("gateway-1", 10)
        
        assert result.allowed is True
        assert result.remaining == 4
    
    @pytest.mark.asyncio
    async def test_quota_expiry_times(self, rate_limiter, mock_redis):
        """Test that quota keys have correct expiry times."""
        await rate_limiter.record_request(
            "gateway-1",
            60,
            quota_per_day=1000,
            quota_per_month=10000
        )
        
        # Verify expiry times
        expire_calls = mock_redis.expire.call_args_list
        
        # Rate limit: 60 seconds
        assert expire_calls[0][0][1] == 60
        
        # Daily quota: 86400 seconds (1 day)
        assert expire_calls[1][0][1] == 86400
        
        # Monthly quota: 2678400 seconds (~31 days)
        assert expire_calls[2][0][1] == 2678400


class TestRateLimiterEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_zero_limit(self, rate_limiter, mock_redis):
        """Test behavior with zero rate limit."""
        mock_redis.zcard.return_value = 0
        
        result = await rate_limiter.check_rate_limit("gateway-1", 0)
        
        assert result.allowed is False
        assert result.remaining == 0
    
    @pytest.mark.asyncio
    async def test_negative_usage(self, rate_limiter, mock_redis):
        """Test handling of invalid negative usage values."""
        mock_redis.get.return_value = "-1"
        
        result = await rate_limiter.check_quota("gateway-1", 1000, "day")
        
        # Should handle gracefully
        assert result.used == -1
        assert result.allowed is True  # -1 < 1000
    
    @pytest.mark.asyncio
    async def test_very_high_limits(self, rate_limiter, mock_redis):
        """Test with very high rate limits."""
        mock_redis.zcard.return_value = 1000
        
        result = await rate_limiter.check_rate_limit("gateway-1", 1000000)
        
        assert result.allowed is True
        assert result.remaining == 998999


class TestRateLimiterProperties:
    """Property-based tests for RateLimiter correctness."""
    
    def test_property_usage_counter_management(self, mock_redis):
        """
        Property 35: Usage Counter Management
        **Validates: Requirements 12.5**
        
        For any gateway, usage counters should reset based on the configured time
        window (sliding or fixed), and historical usage data should be persisted
        for reporting.
        
        Property: For all (gateway_id, period, usage_count):
                  1. After recording usage, get_usage_stats returns the correct count
                  2. Counters persist across multiple queries
                  3. Daily counters reset at day boundaries
                  4. Monthly counters reset at month boundaries
                  5. Rate limit counters use sliding window (60 seconds)
        """
        import hypothesis.strategies as st
        from hypothesis import given, settings
        import asyncio
        from datetime import datetime, timedelta
        from unittest.mock import AsyncMock
        
        @given(
            gateway_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'), 
                whitelist_characters='-_'
            )),
            rate_limit=st.integers(min_value=1, max_value=100),
            daily_quota=st.integers(min_value=100, max_value=10000),
            monthly_quota=st.integers(min_value=1000, max_value=100000),
            request_count=st.integers(min_value=1, max_value=50)
        )
        @settings(max_examples=20, deadline=None)
        def property_test(gateway_id, rate_limit, daily_quota, monthly_quota, request_count):
            """Test that usage counters are managed correctly across time windows."""
            # Create fresh mock for each test iteration
            fresh_redis = AsyncMock()
            fresh_redis.zremrangebyscore = AsyncMock(return_value=0)
            fresh_redis.zcard = AsyncMock(return_value=0)
            fresh_redis.zrange = AsyncMock(return_value=[])
            fresh_redis.zadd = AsyncMock(return_value=1)
            fresh_redis.expire = AsyncMock(return_value=True)
            fresh_redis.get = AsyncMock(return_value=None)
            fresh_redis.incr = AsyncMock(return_value=1)
            fresh_redis.delete = AsyncMock(return_value=1)
            fresh_redis.close = AsyncMock()
            
            # Create fresh rate limiter for each test
            test_rate_limiter = RateLimiter(redis_client=fresh_redis)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Setup: Configure mock to track increments
                increment_counts = {'rate': 0, 'daily': 0, 'monthly': 0}
                
                async def mock_incr(key):
                    if 'rate_limit' in key:
                        increment_counts['rate'] += 1
                    elif ':day:' in key:
                        increment_counts['daily'] += 1
                    elif ':month:' in key:
                        increment_counts['monthly'] += 1
                    return increment_counts.get('daily', 1)
                
                fresh_redis.incr = AsyncMock(side_effect=mock_incr)
                
                # Property 1: Record multiple requests and verify persistence
                async def test_persistence():
                    for _ in range(request_count):
                        await test_rate_limiter.record_request(
                            gateway_id,
                            rate_limit,
                            quota_per_day=daily_quota,
                            quota_per_month=monthly_quota
                        )
                    
                    # Verify all requests were recorded
                    assert fresh_redis.zadd.call_count == request_count, \
                        f"Rate limit should record {request_count} requests"
                    
                    # Verify daily quota increments
                    assert increment_counts['daily'] == request_count, \
                        f"Daily quota should increment {request_count} times"
                    
                    # Verify monthly quota increments
                    assert increment_counts['monthly'] == request_count, \
                        f"Monthly quota should increment {request_count} times"
                
                loop.run_until_complete(test_persistence())
                
                # Property 2: Verify usage stats persistence
                fresh_redis.zcard.return_value = request_count
                fresh_redis.get.side_effect = [str(request_count), str(request_count)]
                
                async def test_stats_retrieval():
                    current_rate, daily, monthly = await test_rate_limiter.get_usage_stats(gateway_id)
                    
                    # Verify stats match recorded usage
                    assert current_rate == request_count, \
                        f"Current rate should be {request_count}"
                    assert daily == request_count, \
                        f"Daily usage should be {request_count}"
                    assert monthly == request_count, \
                        f"Monthly usage should be {request_count}"
                
                loop.run_until_complete(test_stats_retrieval())
                
                # Property 3: Verify daily quota reset time
                # Reset the get mock for this test
                fresh_redis.get = AsyncMock(return_value="0")
                
                async def test_daily_reset():
                    result = await test_rate_limiter.check_quota(gateway_id, daily_quota, "day")
                    
                    # Verify reset time is at midnight
                    assert result.reset_at.hour == 0, \
                        "Daily quota should reset at midnight (hour=0)"
                    assert result.reset_at.minute == 0, \
                        "Daily quota should reset at midnight (minute=0)"
                    assert result.reset_at.second == 0, \
                        "Daily quota should reset at midnight (second=0)"
                    
                    # Verify reset time is in the future
                    assert result.reset_at > datetime.utcnow(), \
                        "Daily reset time should be in the future"
                    
                    # Verify reset time is within 24 hours
                    time_until_reset = result.reset_at - datetime.utcnow()
                    assert time_until_reset <= timedelta(days=1), \
                        "Daily reset should be within 24 hours"
                
                loop.run_until_complete(test_daily_reset())
                
                # Property 4: Verify monthly quota reset time
                # Reset the get mock for this test
                fresh_redis.get = AsyncMock(return_value="0")
                
                async def test_monthly_reset():
                    result = await test_rate_limiter.check_quota(gateway_id, monthly_quota, "month")
                    
                    # Verify reset time is at first day of month
                    assert result.reset_at.day == 1, \
                        "Monthly quota should reset on day 1"
                    assert result.reset_at.hour == 0, \
                        "Monthly quota should reset at midnight (hour=0)"
                    assert result.reset_at.minute == 0, \
                        "Monthly quota should reset at midnight (minute=0)"
                    
                    # Verify reset time is in the future
                    assert result.reset_at > datetime.utcnow(), \
                        "Monthly reset time should be in the future"
                    
                    # Verify reset time is within reasonable range (max 32 days)
                    time_until_reset = result.reset_at - datetime.utcnow()
                    assert time_until_reset <= timedelta(days=32), \
                        "Monthly reset should be within 32 days"
                
                loop.run_until_complete(test_monthly_reset())
                
                # Property 5: Verify rate limit uses sliding window (60 seconds)
                async def test_sliding_window():
                    await test_rate_limiter.check_rate_limit(gateway_id, rate_limit)
                    
                    # Verify old entries are cleaned up (sliding window behavior)
                    fresh_redis.zremrangebyscore.assert_called()
                    
                    # Verify cleanup parameters
                    call_args = fresh_redis.zremrangebyscore.call_args
                    key = call_args[0][0]
                    min_score = call_args[0][1]
                    max_score = call_args[0][2]
                    
                    assert key == f"rate_limit:{gateway_id}", \
                        "Should clean up correct rate limit key"
                    assert min_score == 0, \
                        "Should remove entries from score 0"
                    
                    # max_score should be approximately (now - 60)
                    now = time.time()
                    assert abs(max_score - (now - 60)) < 2, \
                        "Should remove entries older than 60 seconds (sliding window)"
                
                loop.run_until_complete(test_sliding_window())
                
                # Property 6: Verify counter reset functionality
                async def test_counter_reset():
                    await test_rate_limiter.reset_counters(gateway_id)
                    
                    # Verify all counter types are deleted
                    delete_calls = [call[0][0] for call in fresh_redis.delete.call_args_list]
                    
                    # Should delete rate limit counter
                    assert any(f"rate_limit:{gateway_id}" in key for key in delete_calls), \
                        "Should delete rate limit counter"
                    
                    # Should delete daily quota counter
                    assert any(f"quota:{gateway_id}:day:" in key for key in delete_calls), \
                        "Should delete daily quota counter"
                    
                    # Should delete monthly quota counter
                    assert any(f"quota:{gateway_id}:month:" in key for key in delete_calls), \
                        "Should delete monthly quota counter"
                
                loop.run_until_complete(test_counter_reset())
                
            finally:
                loop.close()
        
        # Run the property test
        property_test()
    
    def test_property_rate_limit_enforcement(self, rate_limiter, mock_redis):
        """
        Property 33: Rate Limit Enforcement
        **Validates: Requirements 12.2**
        
        For any gateway, when the number of requests in the current time window
        exceeds the configured rate limit, subsequent requests should be rejected
        with HTTP 429 status and Retry-After header.
        
        Property: For all (gateway_id, rate_limit, request_count) where
                  request_count > rate_limit:
                  check_rate_limit returns allowed=False AND
                  retry_after_seconds is not None AND
                  retry_after_seconds > 0 AND
                  retry_after_seconds <= 60
        """
        import hypothesis.strategies as st
        from hypothesis import given, settings
        import asyncio
        
        @given(
            gateway_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'), 
                whitelist_characters='-_'
            )),
            rate_limit=st.integers(min_value=1, max_value=1000),
            excess_requests=st.integers(min_value=1, max_value=100)
        )
        @settings(max_examples=20, deadline=None)
        def property_test(gateway_id, rate_limit, excess_requests):
            """Test that exceeding rate limit always results in rejection with retry info."""
            # Setup: simulate requests exceeding the limit
            current_count = rate_limit + excess_requests
            mock_redis.zcard.return_value = current_count
            
            # Simulate oldest request timestamp (30 seconds ago)
            now = time.time()
            mock_redis.zrange.return_value = [(b"timestamp", now - 30)]
            
            # Execute: check rate limit (create new event loop for sync context)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    rate_limiter.check_rate_limit(gateway_id, rate_limit)
                )
            finally:
                loop.close()
            
            # Verify: request should be rejected
            assert result.allowed is False, \
                f"Request should be rejected when count ({current_count}) exceeds limit ({rate_limit})"
            
            # Verify: remaining should be 0
            assert result.remaining == 0, \
                "Remaining requests should be 0 when limit exceeded"
            
            # Verify: retry_after_seconds should be present
            assert result.retry_after_seconds is not None, \
                "Retry-After header value should be present when rate limit exceeded"
            
            # Verify: retry_after_seconds should be positive
            assert result.retry_after_seconds > 0, \
                "Retry-After should be positive (time until window resets)"
            
            # Verify: retry_after_seconds should be within window (60 seconds)
            assert result.retry_after_seconds <= 60, \
                "Retry-After should not exceed window size (60 seconds)"
            
            # Verify: reset_at should be in the future
            assert result.reset_at > datetime.utcnow(), \
                "Reset time should be in the future"
        
        # Run the property test
        property_test()
    
    def test_property_rate_limit_allows_within_limit(self, rate_limiter, mock_redis):
        """
        Property: Rate limit allows requests within limit.
        
        For any gateway, when the number of requests in the current time window
        is below the configured rate limit, the request should be allowed.
        
        Property: For all (gateway_id, rate_limit, request_count) where
                  request_count < rate_limit:
                  check_rate_limit returns allowed=True AND
                  remaining = rate_limit - request_count - 1
        """
        import hypothesis.strategies as st
        from hypothesis import given, settings
        import asyncio
        
        @given(
            gateway_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'), 
                whitelist_characters='-_'
            )),
            rate_limit=st.integers(min_value=2, max_value=1000),
            current_count=st.integers(min_value=0, max_value=999)
        )
        @settings(max_examples=20, deadline=None)
        def property_test(gateway_id, rate_limit, current_count):
            """Test that requests within limit are always allowed."""
            # Ensure current_count is below rate_limit
            if current_count >= rate_limit:
                current_count = rate_limit - 1
            
            # Setup: simulate requests below the limit
            mock_redis.zcard.return_value = current_count
            
            # Execute: check rate limit (create new event loop for sync context)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    rate_limiter.check_rate_limit(gateway_id, rate_limit)
                )
            finally:
                loop.close()
            
            # Verify: request should be allowed
            assert result.allowed is True, \
                f"Request should be allowed when count ({current_count}) is below limit ({rate_limit})"
            
            # Verify: remaining should be correct
            expected_remaining = rate_limit - current_count - 1
            assert result.remaining == expected_remaining, \
                f"Remaining should be {expected_remaining}, got {result.remaining}"
            
            # Verify: retry_after_seconds should be None when allowed
            assert result.retry_after_seconds is None, \
                "Retry-After should not be set when request is allowed"
            
            # Verify: reset_at should be present
            assert result.reset_at is not None, \
                "Reset time should always be present"
        
        # Run the property test
        property_test()
