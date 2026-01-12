"""
Comprehensive test suite for permission caching and optimization system.

Tests the advanced permission caching functionality including:
- Redis integration
- Cache performance
- Invalidation strategies
- Memory management
- Performance optimization
"""

import pytest
import time
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, MagicMock

from src.security.permission_cache import (
    PermissionCache, PermissionCacheManager,
    get_permission_cache, get_cache_manager
)
from src.security.rbac_controller import RBACController
from src.security.rbac_models import PermissionScope, ResourceType


class TestPermissionCache:
    """Test the PermissionCache class functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = PermissionCache(
            redis_host="localhost",
            redis_port=6379,
            default_ttl=60,
            memory_cache_size=100
        )
        self.user_id = uuid4()
        self.tenant_id = "test_tenant"
        self.permission_name = "read_data"
    
    def test_cache_initialization(self):
        """Test cache initialization with and without Redis."""
        # Test with Redis (may fail if Redis not available)
        cache_with_redis = PermissionCache()
        assert cache_with_redis.default_ttl == 300
        assert cache_with_redis.memory_cache_size == 1000
        
        # Test memory-only cache
        with patch('redis.Redis') as mock_redis:
            mock_redis.side_effect = Exception("Redis not available")
            cache_memory_only = PermissionCache()
            assert cache_memory_only.redis_client is None
    
    def test_cache_key_generation(self):
        """Test cache key generation consistency."""
        key1 = self.cache._generate_cache_key(
            self.user_id, self.permission_name, None, None, self.tenant_id
        )
        key2 = self.cache._generate_cache_key(
            self.user_id, self.permission_name, None, None, self.tenant_id
        )
        assert key1 == key2
        
        # Different parameters should generate different keys
        key3 = self.cache._generate_cache_key(
            self.user_id, "write_data", None, None, self.tenant_id
        )
        assert key1 != key3
    
    def test_memory_cache_operations(self):
        """Test memory cache set and get operations."""
        # Test cache miss
        result = self.cache.get_permission(
            self.user_id, self.permission_name, tenant_id=self.tenant_id
        )
        assert result is None
        assert self.cache.cache_stats["misses"] == 1
        
        # Test cache set and hit
        self.cache.set_permission(
            self.user_id, self.permission_name, True, tenant_id=self.tenant_id
        )
        
        result = self.cache.get_permission(
            self.user_id, self.permission_name, tenant_id=self.tenant_id
        )
        assert result is True
        assert self.cache.cache_stats["hits"] == 1
        assert self.cache.cache_stats["memory_hits"] == 1
    
    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        # Set short TTL for testing
        self.cache.default_ttl = 1
        
        self.cache.set_permission(
            self.user_id, self.permission_name, True, tenant_id=self.tenant_id
        )
        
        # Should hit immediately
        result = self.cache.get_permission(
            self.user_id, self.permission_name, tenant_id=self.tenant_id
        )
        assert result is True
        
        # Wait for expiration
        time.sleep(2)
        
        # Should miss after expiration
        result = self.cache.get_permission(
            self.user_id, self.permission_name, tenant_id=self.tenant_id
        )
        assert result is None
    
    def test_memory_cache_lru_eviction(self):
        """Test LRU eviction in memory cache."""
        # Set small cache size
        self.cache.memory_cache_size = 5
        
        # Fill cache beyond capacity
        for i in range(10):
            user_id = uuid4()
            self.cache.set_permission(
                user_id, f"permission_{i}", True, tenant_id=self.tenant_id
            )
        
        # Cache should not exceed size limit
        assert len(self.cache.memory_cache) <= self.cache.memory_cache_size
    
    def test_user_permission_invalidation(self):
        """Test invalidating permissions for a specific user."""
        # Set multiple permissions for user
        permissions = ["read_data", "write_data", "delete_data"]
        for perm in permissions:
            self.cache.set_permission(
                self.user_id, perm, True, tenant_id=self.tenant_id
            )
        
        # Verify all are cached
        for perm in permissions:
            result = self.cache.get_permission(
                self.user_id, perm, tenant_id=self.tenant_id
            )
            assert result is True
        
        # Invalidate user permissions
        self.cache.invalidate_user_permissions(self.user_id, self.tenant_id)
        
        # Verify all are invalidated
        for perm in permissions:
            result = self.cache.get_permission(
                self.user_id, perm, tenant_id=self.tenant_id
            )
            assert result is None
    
    def test_tenant_permission_invalidation(self):
        """Test invalidating permissions for an entire tenant."""
        # Set permissions for multiple users in tenant
        users = [uuid4() for _ in range(3)]
        for user_id in users:
            self.cache.set_permission(
                user_id, self.permission_name, True, tenant_id=self.tenant_id
            )
        
        # Verify all are cached
        for user_id in users:
            result = self.cache.get_permission(
                user_id, self.permission_name, tenant_id=self.tenant_id
            )
            assert result is True
        
        # Invalidate tenant permissions
        self.cache.invalidate_tenant_permissions(self.tenant_id)
        
        # Verify all are invalidated
        for user_id in users:
            result = self.cache.get_permission(
                user_id, self.permission_name, tenant_id=self.tenant_id
            )
            assert result is None
    
    def test_permission_invalidation(self):
        """Test invalidating specific permission across users."""
        # Set same permission for multiple users
        users = [uuid4() for _ in range(3)]
        for user_id in users:
            self.cache.set_permission(
                user_id, self.permission_name, True, tenant_id=self.tenant_id
            )
        
        # Invalidate specific permission
        self.cache.invalidate_permission(self.permission_name, self.tenant_id)
        
        # Verify all instances are invalidated
        for user_id in users:
            result = self.cache.get_permission(
                user_id, self.permission_name, tenant_id=self.tenant_id
            )
            assert result is None
    
    def test_cache_statistics(self):
        """Test cache statistics collection."""
        # Perform some cache operations
        self.cache.set_permission(
            self.user_id, self.permission_name, True, tenant_id=self.tenant_id
        )
        
        # Hit
        self.cache.get_permission(
            self.user_id, self.permission_name, tenant_id=self.tenant_id
        )
        
        # Miss
        self.cache.get_permission(
            uuid4(), "nonexistent_permission", tenant_id=self.tenant_id
        )
        
        stats = self.cache.get_cache_statistics()
        
        assert "hit_rate" in stats
        assert "total_requests" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "memory_cache_size" in stats
        assert stats["cache_hits"] >= 1
        assert stats["cache_misses"] >= 1
    
    def test_cache_warming(self):
        """Test cache warming functionality."""
        # Mock RBAC controller and database
        mock_rbac = Mock()
        mock_rbac._check_permission_through_roles.return_value = True
        mock_db = Mock()
        
        permissions = ["read_data", "write_data", "view_dashboard"]
        
        self.cache.warm_user_permissions(
            self.user_id, permissions, self.tenant_id, mock_db, mock_rbac
        )
        
        # Verify permissions are cached
        for perm in permissions:
            result = self.cache.get_permission(
                self.user_id, perm, tenant_id=self.tenant_id
            )
            assert result is True
    
    def test_cache_optimization(self):
        """Test cache optimization analysis."""
        # Perform operations to generate statistics
        for i in range(10):
            self.cache.set_permission(
                uuid4(), f"permission_{i}", True, tenant_id=self.tenant_id
            )
        
        optimization_result = self.cache.optimize_cache()
        
        assert "current_performance" in optimization_result
        assert "recommendations" in optimization_result
        assert isinstance(optimization_result["recommendations"], list)
    
    @patch('redis.Redis')
    def test_redis_integration(self, mock_redis_class):
        """Test Redis integration functionality."""
        # Mock Redis client
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis_class.return_value = mock_redis
        
        cache = PermissionCache()
        
        # Test Redis operations
        cache.set_permission(
            self.user_id, self.permission_name, True, tenant_id=self.tenant_id
        )
        
        # Verify Redis was called
        assert mock_redis.setex.called
    
    def test_clear_all_cache(self):
        """Test clearing all cache data."""
        # Set some cache data
        self.cache.set_permission(
            self.user_id, self.permission_name, True, tenant_id=self.tenant_id
        )
        
        # Verify data exists
        result = self.cache.get_permission(
            self.user_id, self.permission_name, tenant_id=self.tenant_id
        )
        assert result is True
        
        # Clear all cache
        self.cache.clear_all_cache()
        
        # Verify data is cleared
        result = self.cache.get_permission(
            self.user_id, self.permission_name, tenant_id=self.tenant_id
        )
        assert result is None
        
        # Verify stats are reset
        stats = self.cache.get_cache_statistics()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 1  # From the check above


class TestPermissionCacheManager:
    """Test the PermissionCacheManager class functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = PermissionCache()
        self.manager = PermissionCacheManager(self.cache)
        self.user_id = uuid4()
        self.tenant_id = "test_tenant"
    
    def test_cache_invalidation_events(self):
        """Test handling of different cache invalidation events."""
        # Test user role change event
        self.manager.handle_cache_invalidation(
            "user_role_change",
            {"user_id": str(self.user_id), "tenant_id": self.tenant_id}
        )
        
        # Test role permission change event
        self.manager.handle_cache_invalidation(
            "role_permission_change",
            {"role_id": str(uuid4()), "tenant_id": self.tenant_id}
        )
        
        # Test permission update event
        self.manager.handle_cache_invalidation(
            "permission_update",
            {"permission_name": "read_data", "tenant_id": self.tenant_id}
        )
        
        # Test tenant update event
        self.manager.handle_cache_invalidation(
            "tenant_update",
            {"tenant_id": self.tenant_id}
        )
        
        # Test unknown event (should log warning)
        self.manager.handle_cache_invalidation(
            "unknown_event",
            {"data": "test"}
        )
    
    def test_cache_maintenance_scheduling(self):
        """Test cache maintenance scheduling."""
        result = self.manager.schedule_cache_maintenance()
        
        assert "current_performance" in result
        assert "recommendations" in result


class TestRBACControllerCacheIntegration:
    """Test RBAC controller integration with advanced caching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.controller = RBACController()
        self.user_id = uuid4()
        self.tenant_id = "test_tenant"
        
        # Mock database session
        self.mock_db = Mock()
        
        # Mock user
        self.mock_user = Mock()
        self.mock_user.id = self.user_id
        self.mock_user.tenant_id = self.tenant_id
        self.mock_user.is_active = True
        self.mock_user.role = "USER"
    
    def test_enhanced_permission_checking(self):
        """Test enhanced permission checking with caching."""
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            with patch.object(self.controller, '_check_permission_through_roles') as mock_check:
                mock_check.return_value = True
                
                # First call should miss cache and check database
                result1 = self.controller.check_user_permission(
                    self.user_id, "read_data", db=self.mock_db
                )
                assert result1 is True
                assert mock_check.called
                
                # Reset mock
                mock_check.reset_mock()
                
                # Second call should hit cache
                result2 = self.controller.check_user_permission(
                    self.user_id, "read_data", db=self.mock_db
                )
                assert result2 is True
                # Should not call database check again
                assert not mock_check.called
    
    def test_cache_statistics_integration(self):
        """Test cache statistics integration."""
        stats = self.controller.get_cache_statistics()
        
        assert "hit_rate" in stats
        assert "cache_system" in stats
        assert "legacy_cache_size" in stats
        assert stats["cache_system"] == "advanced_with_redis"
    
    def test_cache_optimization_integration(self):
        """Test cache optimization integration."""
        optimization_result = self.controller.optimize_permission_cache()
        
        assert "current_performance" in optimization_result
        assert "recommendations" in optimization_result
    
    def test_cache_warming_integration(self):
        """Test cache warming integration."""
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            result = self.controller.warm_user_cache(
                self.user_id, ["read_data", "write_data"], self.mock_db
            )
            assert result is True
    
    def test_batch_permission_checking(self):
        """Test batch permission checking functionality."""
        permissions = ["read_data", "write_data", "delete_data"]
        
        with patch.object(self.controller, 'check_user_permission') as mock_check:
            mock_check.return_value = True
            
            results = self.controller.batch_check_permissions(
                self.user_id, permissions, db=self.mock_db
            )
            
            assert len(results) == len(permissions)
            for perm in permissions:
                assert results[perm] is True
            
            # Should have called check_user_permission for each permission
            assert mock_check.call_count == len(permissions)
    
    def test_cache_invalidation_on_role_changes(self):
        """Test cache invalidation when roles change."""
        with patch.object(self.controller.cache_manager, 'handle_cache_invalidation') as mock_invalidate:
            with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
                mock_get_user.return_value = self.mock_user
                
                with patch.object(self.controller, 'get_role_by_id') as mock_get_role:
                    mock_role = Mock()
                    mock_role.tenant_id = self.tenant_id
                    mock_get_role.return_value = mock_role
                    
                    # Mock database operations
                    self.mock_db.query.return_value.filter.return_value.first.return_value = None
                    self.mock_db.add = Mock()
                    self.mock_db.commit = Mock()
                    
                    # Assign role to user
                    result = self.controller.assign_role_to_user(
                        self.user_id, uuid4(), uuid4(), self.mock_db
                    )
                    
                    # Should have called cache invalidation
                    assert mock_invalidate.called
                    call_args = mock_invalidate.call_args
                    assert call_args[0][0] == "user_role_change"


class TestCachePerformance:
    """Test cache performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = PermissionCache(memory_cache_size=1000)
        self.controller = RBACController()
    
    def test_cache_performance_under_load(self):
        """Test cache performance under high load."""
        num_operations = 1000
        users = [uuid4() for _ in range(100)]
        permissions = ["read_data", "write_data", "delete_data", "admin_access"]
        
        start_time = time.time()
        
        # Perform many cache operations
        for i in range(num_operations):
            user_id = users[i % len(users)]
            permission = permissions[i % len(permissions)]
            
            # Set permission
            self.cache.set_permission(
                user_id, permission, True, tenant_id="test_tenant"
            )
            
            # Get permission
            self.cache.get_permission(
                user_id, permission, tenant_id="test_tenant"
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert total_time < 5.0  # 5 seconds for 1000 operations
        
        # Check cache statistics
        stats = self.cache.get_cache_statistics()
        assert stats["hit_rate"] > 0
        assert stats["total_requests"] >= num_operations
    
    def test_memory_usage_efficiency(self):
        """Test memory usage efficiency of cache."""
        initial_cache_size = len(self.cache.memory_cache)
        
        # Add many entries
        for i in range(500):
            user_id = uuid4()
            self.cache.set_permission(
                user_id, f"permission_{i}", True, tenant_id="test_tenant"
            )
        
        final_cache_size = len(self.cache.memory_cache)
        
        # Should not exceed memory limit
        assert final_cache_size <= self.cache.memory_cache_size
        
        # Should have grown from initial size
        assert final_cache_size > initial_cache_size


def test_global_cache_instances():
    """Test global cache instance management."""
    cache1 = get_permission_cache()
    cache2 = get_permission_cache()
    
    # Should return same instance
    assert cache1 is cache2
    
    manager1 = get_cache_manager()
    manager2 = get_cache_manager()
    
    # Should return same instance
    assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])