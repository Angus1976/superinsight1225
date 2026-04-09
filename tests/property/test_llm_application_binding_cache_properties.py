"""
Property-based tests for LLM Application Binding - CacheManager.

Uses Hypothesis library for property testing with minimum 100 iterations.
Tests Property 10 from the LLM Application Binding design document.

Feature: llm-application-binding
Property: 10 - Cache TTL Expiration
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import AsyncMock, MagicMock

from src.ai.cache_manager import CacheManager, CacheEntry


# ==================== Custom Strategies ====================

# Strategy for cache keys (realistic configuration cache keys)
cache_key_strategy = st.one_of(
    # Application-specific config keys
    st.builds(
        lambda app: f"llm:config:{app}",
        st.sampled_from(['structuring', 'knowledge_graph', 'ai_assistant', 
                        'semantic_analysis', 'rag_agent', 'text_to_sql'])
    ),
    # Tenant-specific config keys
    st.builds(
        lambda tenant, app: f"llm:config:{tenant}:{app}",
        st.uuids().map(str),
        st.sampled_from(['structuring', 'knowledge_graph', 'ai_assistant'])
    ),
    # Generic cache keys
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=':-_'),
        min_size=5,
        max_size=50
    )
)

# Strategy for cache values (configuration data)
cache_value_strategy = st.one_of(
    # Simple string values
    st.text(min_size=1, max_size=100),
    # Dictionary values (like CloudConfig)
    st.fixed_dictionaries({
        'provider': st.sampled_from(['openai', 'azure', 'anthropic', 'ollama']),
        'model_name': st.sampled_from(['gpt-4', 'gpt-3.5-turbo', 'claude-3', 'llama2']),
        'api_key': st.text(min_size=10, max_size=50),
    }),
    # List values
    st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5),
    # Integer values
    st.integers(min_value=1, max_value=1000),
)

# Strategy for TTL values (in seconds)
ttl_strategy = st.integers(min_value=1, max_value=600)


# ==================== Fixtures ====================

@pytest.fixture
def cache_manager():
    """Create a CacheManager instance without Redis."""
    return CacheManager(redis_client=None, local_ttl=300, max_memory_mb=100)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.publish = AsyncMock()
    return redis


# ==================== Property 10: Cache TTL Expiration ====================

class TestCacheTTLExpiration:
    """
    Property 10: Cache TTL Expiration
    
    For any cached configuration entry, if the current time exceeds the entry's 
    creation time plus TTL, the entry should be considered expired and not 
    returned from cache.
    
    **Validates: Requirements 4.4, 4.5**
    
    Requirements:
    - 4.4: THE System SHALL cache LLM configurations in memory with a configurable 
           TTL (default 300 seconds)
    - 4.5: WHEN configuration is retrieved from cache, THE System SHALL validate 
           that the cached entry has not expired
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        key=cache_key_strategy,
        value=cache_value_strategy,
        ttl=ttl_strategy
    )
    @pytest.mark.asyncio
    async def test_property_10_cache_entry_expires_after_ttl(
        self,
        key: str,
        value,
        ttl: int
    ):
        """
        Feature: llm-application-binding, Property 10: Cache TTL Expiration
        
        For any cached entry, if current time exceeds creation time + TTL,
        the entry should be considered expired and not returned.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Skip empty keys
        assume(len(key.strip()) > 0)
        
        # Create cache manager with specified TTL
        cache = CacheManager(redis_client=None, local_ttl=ttl, max_memory_mb=100)
        
        # Set value in cache
        await cache.set(key, value)
        
        # Immediately retrieve - should succeed
        cached_value = await cache.get(key)
        assert cached_value == value, "Freshly cached value should be retrievable"
        
        # Manually expire the entry by manipulating its expires_at timestamp
        if key in cache.local_cache:
            entry = cache.local_cache[key]
            # Set expiration to the past
            entry.expires_at = datetime.utcnow() - timedelta(seconds=1)
        
        # Retrieve again - should return None (expired)
        expired_value = await cache.get(key)
        assert expired_value is None, \
            "Expired cache entry should not be returned"
        
        # Verify entry was removed from cache
        assert key not in cache.local_cache, \
            "Expired entry should be removed from cache"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        key=cache_key_strategy,
        value=cache_value_strategy,
        ttl=st.integers(min_value=1, max_value=10)
    )
    @pytest.mark.asyncio
    async def test_property_10_cache_entry_valid_before_ttl(
        self,
        key: str,
        value,
        ttl: int
    ):
        """
        Feature: llm-application-binding, Property 10: Cache TTL Expiration
        
        For any cached entry, if current time is before creation time + TTL,
        the entry should be valid and returned from cache.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Skip empty keys
        assume(len(key.strip()) > 0)
        
        # Create cache manager with specified TTL
        cache = CacheManager(redis_client=None, local_ttl=ttl, max_memory_mb=100)
        
        # Set value in cache
        await cache.set(key, value)
        
        # Retrieve immediately - should succeed
        cached_value = await cache.get(key)
        assert cached_value == value, \
            "Cache entry should be valid before TTL expires"
        
        # Verify entry is still in cache
        assert key in cache.local_cache, \
            "Valid entry should remain in cache"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        key=cache_key_strategy,
        value=cache_value_strategy
    )
    @pytest.mark.asyncio
    async def test_property_10_cache_entry_class_expiration_check(
        self,
        key: str,
        value
    ):
        """
        Feature: llm-application-binding, Property 10: Cache TTL Expiration
        
        The CacheEntry.is_expired() method should correctly identify expired entries.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Skip empty keys
        assume(len(key.strip()) > 0)
        
        # Create entry with short TTL
        entry = CacheEntry(value, ttl_seconds=1)
        
        # Should not be expired immediately
        assert not entry.is_expired(), \
            "Freshly created entry should not be expired"
        
        # Manually set expiration to the past
        entry.expires_at = datetime.utcnow() - timedelta(seconds=1)
        
        # Should now be expired
        assert entry.is_expired(), \
            "Entry with past expiration time should be expired"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        key=cache_key_strategy,
        value=cache_value_strategy,
        ttl=ttl_strategy
    )
    @pytest.mark.asyncio
    async def test_property_10_multiple_entries_independent_expiration(
        self,
        key: str,
        value,
        ttl: int
    ):
        """
        Feature: llm-application-binding, Property 10: Cache TTL Expiration
        
        Multiple cache entries should have independent TTL expiration.
        Expiring one entry should not affect others.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Skip empty keys
        assume(len(key.strip()) > 0)
        
        # Create cache manager
        cache = CacheManager(redis_client=None, local_ttl=ttl, max_memory_mb=100)
        
        # Create multiple keys
        key1 = f"{key}_1"
        key2 = f"{key}_2"
        value1 = f"{value}_1" if isinstance(value, str) else value
        value2 = f"{value}_2" if isinstance(value, str) else value
        
        # Set both values
        await cache.set(key1, value1)
        await cache.set(key2, value2)
        
        # Expire only the first entry
        if key1 in cache.local_cache:
            cache.local_cache[key1].expires_at = datetime.utcnow() - timedelta(seconds=1)
        
        # First entry should be expired
        expired_value = await cache.get(key1)
        assert expired_value is None, \
            "Expired entry should not be returned"
        
        # Second entry should still be valid
        valid_value = await cache.get(key2)
        assert valid_value == value2, \
            "Non-expired entry should still be retrievable"
    
    @settings(
        max_examples=20, 
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], 
        deadline=None
    )
    @given(
        key=cache_key_strategy,
        value=cache_value_strategy,
        ttl=ttl_strategy
    )
    @pytest.mark.asyncio
    async def test_property_10_redis_cache_respects_ttl(
        self,
        key: str,
        value,
        ttl: int
    ):
        """
        Feature: llm-application-binding, Property 10: Cache TTL Expiration
        
        When Redis is available, cache entries should be set with TTL in Redis.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Skip empty keys
        assume(len(key.strip()) > 0)
        
        # Create a fresh mock Redis for each iteration
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis.publish = AsyncMock()
        
        # Create cache manager with Redis
        cache = CacheManager(redis_client=mock_redis, local_ttl=ttl, max_memory_mb=100)
        
        # Set value in cache
        await cache.set(key, value)
        
        # Verify Redis setex was called with correct TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        
        # Check that TTL was passed to Redis
        assert call_args[0][1] == ttl, \
            f"Redis setex should be called with TTL {ttl}"


# ==================== Additional TTL Properties ====================

class TestCacheTTLBehavior:
    """
    Additional tests for cache TTL behavior and edge cases.
    
    **Validates: Requirements 4.4, 4.5**
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        key=cache_key_strategy,
        value=cache_value_strategy
    )
    @pytest.mark.asyncio
    async def test_cache_entry_updates_lru_on_access(
        self,
        key: str,
        value
    ):
        """
        Accessing a cache entry should update its position in LRU order.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Skip empty keys
        assume(len(key.strip()) > 0)
        
        cache = CacheManager(redis_client=None, local_ttl=300, max_memory_mb=100)
        
        # Set value
        await cache.set(key, value)
        
        # Access the value multiple times
        for _ in range(3):
            cached_value = await cache.get(key)
            assert cached_value == value
        
        # Key should be at the end of access order (most recently used)
        assert cache._access_order[-1] == key, \
            "Accessed key should be at end of LRU order"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        key=cache_key_strategy,
        value=cache_value_strategy
    )
    @pytest.mark.asyncio
    async def test_expired_entry_removed_from_lru_order(
        self,
        key: str,
        value
    ):
        """
        When an expired entry is accessed, it should be removed from LRU order.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Skip empty keys
        assume(len(key.strip()) > 0)
        
        cache = CacheManager(redis_client=None, local_ttl=1, max_memory_mb=100)
        
        # Set value
        await cache.set(key, value)
        
        # Verify it's in LRU order
        assert key in cache._access_order
        
        # Expire the entry
        if key in cache.local_cache:
            cache.local_cache[key].expires_at = datetime.utcnow() - timedelta(seconds=1)
        
        # Access expired entry
        result = await cache.get(key)
        assert result is None
        
        # Should be removed from LRU order
        assert key not in cache._access_order, \
            "Expired entry should be removed from LRU order"
    
    @pytest.mark.asyncio
    async def test_default_ttl_is_300_seconds(self):
        """
        Default TTL should be 300 seconds as specified in requirements.
        
        **Validates: Requirements 4.4**
        """
        cache = CacheManager(redis_client=None)
        
        assert cache.local_ttl == 300, \
            "Default TTL should be 300 seconds"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        key=cache_key_strategy,
        value=cache_value_strategy,
        ttl=st.integers(min_value=1, max_value=10)
    )
    @pytest.mark.asyncio
    async def test_cache_entry_expiration_timestamp_calculation(
        self,
        key: str,
        value,
        ttl: int
    ):
        """
        Cache entry expiration timestamp should be creation time + TTL.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Skip empty keys
        assume(len(key.strip()) > 0)
        
        # Record time before creating entry
        before_time = datetime.utcnow()
        
        # Create entry
        entry = CacheEntry(value, ttl_seconds=ttl)
        
        # Record time after creating entry
        after_time = datetime.utcnow()
        
        # Expected expiration should be within the time window + TTL
        expected_min = before_time + timedelta(seconds=ttl)
        expected_max = after_time + timedelta(seconds=ttl)
        
        # Verify expiration is in expected range
        assert expected_min <= entry.expires_at <= expected_max, \
            f"Expiration time should be creation time + {ttl} seconds"


# ==================== Edge Cases ====================

class TestCacheTTLEdgeCases:
    """
    Edge case tests for cache TTL expiration.
    
    **Validates: Requirements 4.4, 4.5**
    """
    
    @pytest.mark.asyncio
    async def test_zero_ttl_entry_immediately_expired(self):
        """
        Entry with TTL of 0 should be immediately expired.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Create entry with 0 TTL
        entry = CacheEntry("test_value", ttl_seconds=0)
        
        # Should be expired immediately (or very soon)
        # Allow small time window for execution
        await asyncio.sleep(0.01)
        assert entry.is_expired(), \
            "Entry with 0 TTL should be expired"
    
    @pytest.mark.asyncio
    async def test_very_long_ttl_entry_not_expired(self):
        """
        Entry with very long TTL should not expire quickly.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Create entry with 1 year TTL
        entry = CacheEntry("test_value", ttl_seconds=365 * 24 * 3600)
        
        # Should not be expired
        assert not entry.is_expired(), \
            "Entry with very long TTL should not be expired"
    
    @pytest.mark.asyncio
    async def test_cache_get_nonexistent_key_returns_none(self):
        """
        Getting a non-existent key should return None.
        
        **Validates: Requirements 4.5**
        """
        cache = CacheManager(redis_client=None, local_ttl=300, max_memory_mb=100)
        
        result = await cache.get("nonexistent_key")
        
        assert result is None, \
            "Non-existent key should return None"
    
    @pytest.mark.asyncio
    async def test_cache_set_overwrites_existing_entry(self):
        """
        Setting a value for an existing key should overwrite and reset TTL.
        
        **Validates: Requirements 4.4, 4.5**
        """
        cache = CacheManager(redis_client=None, local_ttl=300, max_memory_mb=100)
        
        key = "test_key"
        value1 = "value1"
        value2 = "value2"
        
        # Set first value
        await cache.set(key, value1)
        
        # Expire the entry
        if key in cache.local_cache:
            cache.local_cache[key].expires_at = datetime.utcnow() - timedelta(seconds=1)
        
        # Set new value (should reset TTL)
        await cache.set(key, value2)
        
        # Should be able to retrieve new value
        result = await cache.get(key)
        assert result == value2, \
            "Overwritten entry should have new value and reset TTL"
    
    @pytest.mark.asyncio
    async def test_redis_unavailable_falls_back_to_local_cache(self, mock_redis):
        """
        If Redis operations fail, local cache should still work.
        
        **Validates: Requirements 4.4, 4.5**
        """
        # Make Redis operations fail
        mock_redis.setex.side_effect = Exception("Redis connection failed")
        mock_redis.get.side_effect = Exception("Redis connection failed")
        
        cache = CacheManager(redis_client=mock_redis, local_ttl=300, max_memory_mb=100)
        
        key = "test_key"
        value = "test_value"
        
        # Set should still work (local cache)
        await cache.set(key, value)
        
        # Get should still work (local cache)
        result = await cache.get(key)
        assert result == value, \
            "Local cache should work even if Redis fails"


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
