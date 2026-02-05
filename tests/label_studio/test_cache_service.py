"""
Tests for Label Studio Workspace Cache Service.

Tests cover:
- In-memory cache operations
- Cache TTL expiration
- Cache invalidation
- Statistics tracking
- Redis fallback (mocked)
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.label_studio.cache_service import (
    WorkspaceCacheService,
    WorkspaceCacheConfig,
    CacheStats,
    InMemoryCacheBackend,
    RedisCacheBackend,
    get_workspace_cache,
    clear_cache_instance,
    cache_workspace,
    cache_permissions,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cache_config():
    """Create test cache configuration with short TTLs."""
    return WorkspaceCacheConfig(
        workspace_ttl=2,  # 2 seconds for testing
        members_ttl=1,
        permissions_ttl=1,
        projects_ttl=2,
        max_entries=100,
    )


@pytest.fixture
def cache_service(cache_config):
    """Create cache service with in-memory backend only."""
    return WorkspaceCacheService(
        config=cache_config,
        use_redis=False,
    )


@pytest.fixture
def workspace_data():
    """Sample workspace data."""
    return {
        "id": str(uuid4()),
        "name": "Test Workspace",
        "description": "Test description",
        "owner_id": str(uuid4()),
        "is_active": True,
        "member_count": 5,
        "project_count": 3,
    }


@pytest.fixture
def members_data():
    """Sample members data."""
    return [
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "role": "owner",
            "is_active": True,
        },
        {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "role": "annotator",
            "is_active": True,
        },
    ]


@pytest.fixture
def permissions_data():
    """Sample permissions data."""
    return {
        "role": "admin",
        "permissions": [
            "workspace:view",
            "workspace:edit",
            "project:view",
            "project:create",
        ],
    }


# ============================================================================
# InMemoryCacheBackend Tests
# ============================================================================

class TestInMemoryCacheBackend:
    """Tests for in-memory cache backend."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        backend = InMemoryCacheBackend()

        backend.set("key1", {"data": "value"}, ttl=60)
        result = backend.get("key1")

        assert result == {"data": "value"}

    def test_get_nonexistent_key(self):
        """Test getting non-existent key."""
        backend = InMemoryCacheBackend()

        result = backend.get("nonexistent")

        assert result is None

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        backend = InMemoryCacheBackend()

        backend.set("key1", "value", ttl=1)
        assert backend.get("key1") == "value"

        time.sleep(1.1)
        assert backend.get("key1") is None

    def test_delete(self):
        """Test delete operation."""
        backend = InMemoryCacheBackend()

        backend.set("key1", "value", ttl=60)
        assert backend.exists("key1")

        backend.delete("key1")
        assert not backend.exists("key1")

    def test_delete_pattern(self):
        """Test pattern-based deletion."""
        backend = InMemoryCacheBackend()

        backend.set("prefix:key1", "v1", ttl=60)
        backend.set("prefix:key2", "v2", ttl=60)
        backend.set("other:key3", "v3", ttl=60)

        count = backend.delete_pattern("prefix:")

        assert count == 2
        assert not backend.exists("prefix:key1")
        assert not backend.exists("prefix:key2")
        assert backend.exists("other:key3")

    def test_exists(self):
        """Test exists check."""
        backend = InMemoryCacheBackend()

        assert not backend.exists("key1")

        backend.set("key1", "value", ttl=60)
        assert backend.exists("key1")

    def test_clear(self):
        """Test clearing all entries."""
        backend = InMemoryCacheBackend()

        backend.set("key1", "v1", ttl=60)
        backend.set("key2", "v2", ttl=60)

        backend.clear()

        assert not backend.exists("key1")
        assert not backend.exists("key2")

    def test_lru_eviction(self):
        """Test LRU eviction when max size reached."""
        backend = InMemoryCacheBackend(max_size=3)

        backend.set("key1", "v1", ttl=60)
        backend.set("key2", "v2", ttl=60)
        backend.set("key3", "v3", ttl=60)

        # Access key1 to make it recently used
        backend.get("key1")

        # Add key4, should evict key2 (least recently used)
        backend.set("key4", "v4", ttl=60)

        assert backend.exists("key1")
        assert not backend.exists("key2")  # Evicted
        assert backend.exists("key3")
        assert backend.exists("key4")

    def test_keys_pattern(self):
        """Test getting keys by pattern."""
        backend = InMemoryCacheBackend()

        backend.set("ls:ws:1", "v1", ttl=60)
        backend.set("ls:ws:2", "v2", ttl=60)
        backend.set("ls:perms:1", "v3", ttl=60)

        keys = backend.keys("ls:ws:*")

        assert len(keys) == 2
        assert "ls:ws:1" in keys
        assert "ls:ws:2" in keys


# ============================================================================
# WorkspaceCacheService Tests
# ============================================================================

class TestWorkspaceCacheService:
    """Tests for workspace cache service."""

    def test_workspace_cache_hit(self, cache_service, workspace_data):
        """Test workspace cache hit."""
        ws_id = workspace_data["id"]

        cache_service.set_workspace(ws_id, workspace_data)
        result = cache_service.get_workspace(ws_id)

        assert result == workspace_data
        assert cache_service.stats.hits == 1
        assert cache_service.stats.sets == 1

    def test_workspace_cache_miss(self, cache_service):
        """Test workspace cache miss."""
        result = cache_service.get_workspace(str(uuid4()))

        assert result is None
        assert cache_service.stats.misses == 1

    def test_workspace_invalidation(self, cache_service, workspace_data):
        """Test workspace cache invalidation."""
        ws_id = workspace_data["id"]

        cache_service.set_workspace(ws_id, workspace_data)
        assert cache_service.get_workspace(ws_id) is not None

        cache_service.invalidate_workspace(ws_id)
        assert cache_service.get_workspace(ws_id) is None
        assert cache_service.stats.invalidations == 1

    def test_members_cache(self, cache_service, members_data):
        """Test members caching."""
        ws_id = str(uuid4())

        cache_service.set_members(ws_id, members_data)
        result = cache_service.get_members(ws_id)

        assert result == members_data
        assert len(result) == 2

    def test_members_invalidation(self, cache_service, members_data):
        """Test members cache invalidation."""
        ws_id = str(uuid4())

        cache_service.set_members(ws_id, members_data)
        cache_service.invalidate_members(ws_id)

        assert cache_service.get_members(ws_id) is None

    def test_permissions_cache(self, cache_service, permissions_data):
        """Test permissions caching."""
        ws_id = str(uuid4())
        user_id = str(uuid4())

        cache_service.set_permissions(ws_id, user_id, permissions_data)
        result = cache_service.get_permissions(ws_id, user_id)

        assert result == permissions_data
        assert result["role"] == "admin"

    def test_permissions_invalidation_specific_user(self, cache_service, permissions_data):
        """Test permissions invalidation for specific user."""
        ws_id = str(uuid4())
        user1 = str(uuid4())
        user2 = str(uuid4())

        cache_service.set_permissions(ws_id, user1, permissions_data)
        cache_service.set_permissions(ws_id, user2, permissions_data)

        cache_service.invalidate_permissions(ws_id, user1)

        assert cache_service.get_permissions(ws_id, user1) is None
        assert cache_service.get_permissions(ws_id, user2) is not None

    def test_permissions_invalidation_all(self, cache_service, permissions_data):
        """Test permissions invalidation for all users in workspace."""
        ws_id = str(uuid4())
        user1 = str(uuid4())
        user2 = str(uuid4())

        cache_service.set_permissions(ws_id, user1, permissions_data)
        cache_service.set_permissions(ws_id, user2, permissions_data)

        count = cache_service.invalidate_permissions(ws_id)

        assert count == 2
        assert cache_service.get_permissions(ws_id, user1) is None
        assert cache_service.get_permissions(ws_id, user2) is None

    def test_user_workspaces_cache(self, cache_service, workspace_data):
        """Test user workspaces list caching."""
        user_id = str(uuid4())
        workspaces = [workspace_data, workspace_data]

        cache_service.set_user_workspaces(user_id, workspaces)
        result = cache_service.get_user_workspaces(user_id)

        assert result == workspaces
        assert len(result) == 2

    def test_projects_cache(self, cache_service):
        """Test projects caching."""
        ws_id = str(uuid4())
        projects = [
            {"id": str(uuid4()), "name": "Project 1"},
            {"id": str(uuid4()), "name": "Project 2"},
        ]

        cache_service.set_projects(ws_id, projects)
        result = cache_service.get_projects(ws_id)

        assert result == projects

    def test_invalidate_workspace_all(self, cache_service, workspace_data, members_data, permissions_data):
        """Test complete workspace invalidation."""
        ws_id = str(uuid4())
        user_id = str(uuid4())

        # Cache all types of data
        cache_service.set_workspace(ws_id, workspace_data)
        cache_service.set_members(ws_id, members_data)
        cache_service.set_permissions(ws_id, user_id, permissions_data)
        cache_service.set_projects(ws_id, [{"id": "p1"}])

        # Invalidate all
        count = cache_service.invalidate_workspace_all(ws_id)

        assert count >= 3  # At least workspace, members, projects
        assert cache_service.get_workspace(ws_id) is None
        assert cache_service.get_members(ws_id) is None
        assert cache_service.get_permissions(ws_id, user_id) is None
        assert cache_service.get_projects(ws_id) is None

    def test_invalidate_user_all(self, cache_service, workspace_data, permissions_data):
        """Test complete user invalidation."""
        user_id = str(uuid4())
        ws_id = str(uuid4())

        cache_service.set_user_workspaces(user_id, [workspace_data])
        cache_service.set_permissions(ws_id, user_id, permissions_data)

        count = cache_service.invalidate_user_all(user_id)

        assert count >= 1
        assert cache_service.get_user_workspaces(user_id) is None

    def test_ttl_expiration(self, cache_config):
        """Test that cached data expires after TTL."""
        config = WorkspaceCacheConfig(workspace_ttl=1)
        service = WorkspaceCacheService(config=config, use_redis=False)

        ws_id = str(uuid4())
        service.set_workspace(ws_id, {"name": "test"})

        assert service.get_workspace(ws_id) is not None

        time.sleep(1.1)
        assert service.get_workspace(ws_id) is None

    def test_custom_ttl(self, cache_service, workspace_data):
        """Test custom TTL override."""
        ws_id = workspace_data["id"]

        cache_service.set_workspace(ws_id, workspace_data, ttl=1)

        assert cache_service.get_workspace(ws_id) is not None
        time.sleep(1.1)
        assert cache_service.get_workspace(ws_id) is None

    def test_get_stats(self, cache_service, workspace_data):
        """Test statistics tracking."""
        ws_id = workspace_data["id"]

        # Generate some activity
        cache_service.get_workspace(str(uuid4()))  # Miss
        cache_service.set_workspace(ws_id, workspace_data)  # Set
        cache_service.get_workspace(ws_id)  # Hit
        cache_service.invalidate_workspace(ws_id)  # Invalidation

        stats = cache_service.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["invalidations"] == 1
        assert "hit_rate" in stats

    def test_clear(self, cache_service, workspace_data):
        """Test clearing all cache."""
        ws_id = workspace_data["id"]

        cache_service.set_workspace(ws_id, workspace_data)
        cache_service.clear()

        assert cache_service.get_workspace(ws_id) is None


# ============================================================================
# CacheStats Tests
# ============================================================================

class TestCacheStats:
    """Tests for cache statistics."""

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=75, misses=25)
        assert stats.hit_rate == 75.0

    def test_hit_rate_zero_operations(self):
        """Test hit rate with no operations."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_to_dict(self):
        """Test converting stats to dictionary."""
        stats = CacheStats(hits=10, misses=5, sets=8, deletes=2, invalidations=3)
        result = stats.to_dict()

        assert result["hits"] == 10
        assert result["misses"] == 5
        assert result["sets"] == 8
        assert result["deletes"] == 2
        assert result["invalidations"] == 3
        assert result["hit_rate"] == pytest.approx(66.67, rel=0.1)


# ============================================================================
# Global Instance Tests
# ============================================================================

class TestGlobalInstance:
    """Tests for global cache instance management."""

    def teardown_method(self):
        """Clean up after each test."""
        clear_cache_instance()

    def test_get_workspace_cache(self):
        """Test getting global cache instance."""
        cache1 = get_workspace_cache(use_redis=False)
        cache2 = get_workspace_cache(use_redis=False)

        assert cache1 is cache2  # Same instance

    def test_clear_cache_instance(self):
        """Test clearing global cache instance."""
        cache1 = get_workspace_cache(use_redis=False)
        clear_cache_instance()
        cache2 = get_workspace_cache(use_redis=False)

        assert cache1 is not cache2  # New instance after clear


# ============================================================================
# Redis Backend Tests (Mocked)
# ============================================================================

class TestRedisCacheBackend:
    """Tests for Redis cache backend with mocked Redis client."""

    def test_redis_fallback_on_connection_error(self):
        """Test that cache falls back to memory when Redis unavailable."""
        service = WorkspaceCacheService(use_redis=True, redis_url="redis://invalid:6379")

        # Should fall back to in-memory backend
        ws_id = str(uuid4())
        result = service.set_workspace(ws_id, {"name": "test"})

        assert result is True
        assert service.get_workspace(ws_id) is not None

    @patch('src.label_studio.cache_service.RedisCacheBackend.client', new_callable=lambda: MagicMock())
    def test_redis_get_with_mock(self, mock_client):
        """Test Redis get operation with mocked client."""
        mock_client.get.return_value = '{"name": "test"}'
        mock_client.ping.return_value = True

        backend = RedisCacheBackend()
        backend._client = mock_client

        result = backend.get("test_key")

        assert result == {"name": "test"}
        mock_client.get.assert_called_once_with("test_key")

    @patch('src.label_studio.cache_service.RedisCacheBackend.client', new_callable=lambda: MagicMock())
    def test_redis_set_with_mock(self, mock_client):
        """Test Redis set operation with mocked client."""
        mock_client.setex.return_value = True
        mock_client.ping.return_value = True

        backend = RedisCacheBackend()
        backend._client = mock_client

        result = backend.set("test_key", {"name": "test"}, ttl=60)

        assert result is True
        mock_client.setex.assert_called_once()


# ============================================================================
# Cache Decorators Tests
# ============================================================================

class TestCacheDecorators:
    """Tests for cache decorators."""

    def test_cache_workspace_decorator(self, cache_service, workspace_data):
        """Test @cache_workspace decorator."""
        ws_id = workspace_data["id"]
        call_count = 0

        class MockService:
            _cache = cache_service

            @cache_workspace(ttl=60)
            def get_workspace(self, workspace_id):
                nonlocal call_count
                call_count += 1
                return workspace_data

        service = MockService()

        # First call - should call the actual method
        result1 = service.get_workspace(ws_id)
        assert call_count == 1
        assert result1 == workspace_data

        # Second call - should return from cache
        result2 = service.get_workspace(ws_id)
        assert call_count == 1  # Still 1, didn't call method again
        assert result2 == workspace_data

    def test_cache_permissions_decorator(self, cache_service, permissions_data):
        """Test @cache_permissions decorator."""
        ws_id = str(uuid4())
        user_id = str(uuid4())
        call_count = 0

        class MockService:
            _cache = cache_service

            @cache_permissions(ttl=60)
            def get_user_permissions(self, workspace_id, user_id):
                nonlocal call_count
                call_count += 1
                return permissions_data

        service = MockService()

        # First call
        result1 = service.get_user_permissions(ws_id, user_id)
        assert call_count == 1

        # Second call - from cache
        result2 = service.get_user_permissions(ws_id, user_id)
        assert call_count == 1


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_cache_with_uuid_objects(self, cache_service, workspace_data):
        """Test caching with UUID objects (not strings)."""
        ws_id = uuid4()  # UUID object, not string

        cache_service.set_workspace(ws_id, workspace_data)
        result = cache_service.get_workspace(ws_id)

        assert result == workspace_data

    def test_cache_empty_list(self, cache_service):
        """Test caching empty lists."""
        ws_id = str(uuid4())

        cache_service.set_members(ws_id, [])
        result = cache_service.get_members(ws_id)

        assert result == []

    def test_cache_none_value(self, cache_service):
        """Test that None values are not cached (cache miss)."""
        ws_id = str(uuid4())

        # Attempting to set None should be handled gracefully
        cache_service.set_workspace(ws_id, None)
        result = cache_service.get_workspace(ws_id)

        # Should retrieve the None that was set
        assert result is None

    def test_cache_large_data(self, cache_service):
        """Test caching large data structures."""
        ws_id = str(uuid4())
        large_members = [
            {"id": str(uuid4()), "name": f"User {i}", "data": "x" * 1000}
            for i in range(100)
        ]

        cache_service.set_members(ws_id, large_members)
        result = cache_service.get_members(ws_id)

        assert len(result) == 100

    def test_is_redis_available(self, cache_service):
        """Test Redis availability check."""
        # With use_redis=False, should return False
        assert not cache_service.is_redis_available()
