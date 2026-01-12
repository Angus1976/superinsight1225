"""
Advanced Permission Caching System for SuperInsight Platform.

Provides high-performance permission caching with Redis integration,
intelligent cache invalidation, and performance monitoring.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from uuid import UUID
import hashlib
import redis
from sqlalchemy.orm import Session

from src.security.rbac_models import PermissionScope, ResourceType

logger = logging.getLogger(__name__)


class PermissionCache:
    """
    Advanced permission caching system with Redis backend.
    
    Features:
    - Multi-level caching (memory + Redis)
    - Intelligent cache invalidation
    - Performance monitoring
    - Cache warming strategies
    - Distributed cache consistency
    """
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        default_ttl: int = 300,  # 5 minutes
        memory_cache_size: int = 1000
    ):
        self.redis_client = None
        self.memory_cache = {}
        # Track cache keys by user and tenant for efficient invalidation
        self.user_cache_keys = {}  # user_id -> set of cache keys
        self.tenant_cache_keys = {}  # tenant_id -> set of cache keys
        self.permission_cache_keys = {}  # permission_name -> set of cache keys
        
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "memory_hits": 0,
            "redis_hits": 0
        }
        self.default_ttl = default_ttl
        self.memory_cache_size = memory_cache_size
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established for permission cache")
        except Exception as e:
            logger.warning(f"Redis connection failed, using memory-only cache: {e}")
            self.redis_client = None
    
    def _generate_cache_key(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        tenant_id: Optional[str] = None
    ) -> str:
        """Generate a consistent cache key for permission checks."""
        key_parts = [
            "perm",
            str(user_id),
            permission_name,
            resource_id or "global",
            resource_type.value if resource_type else "none",
            tenant_id or "default"
        ]
        key = ":".join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()
    
    def get_permission(
        self,
        user_id: UUID,
        permission_name: str,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        tenant_id: Optional[str] = None
    ) -> Optional[bool]:
        """
        Get cached permission result.
        
        Returns:
            True/False if cached, None if not in cache
        """
        cache_key = self._generate_cache_key(
            user_id, permission_name, resource_id, resource_type, tenant_id
        )
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            result, timestamp = self.memory_cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.default_ttl):
                self.cache_stats["hits"] += 1
                self.cache_stats["memory_hits"] += 1
                return result
            else:
                # Expired, remove from memory cache
                del self.memory_cache[cache_key]
        
        # Check Redis cache
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    result = data["result"]
                    
                    # Store in memory cache for faster access
                    self._store_in_memory_cache(cache_key, result)
                    
                    self.cache_stats["hits"] += 1
                    self.cache_stats["redis_hits"] += 1
                    return result
            except Exception as e:
                logger.error(f"Redis cache read error: {e}")
        
        self.cache_stats["misses"] += 1
        return None
    
    def set_permission(
        self,
        user_id: UUID,
        permission_name: str,
        result: bool,
        resource_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        tenant_id: Optional[str] = None,
        ttl: Optional[int] = None
    ):
        """Cache a permission result."""
        cache_key = self._generate_cache_key(
            user_id, permission_name, resource_id, resource_type, tenant_id
        )
        
        ttl = ttl or self.default_ttl
        
        # Track cache key for efficient invalidation
        user_id_str = str(user_id)
        if user_id_str not in self.user_cache_keys:
            self.user_cache_keys[user_id_str] = set()
        self.user_cache_keys[user_id_str].add(cache_key)
        
        if tenant_id:
            if tenant_id not in self.tenant_cache_keys:
                self.tenant_cache_keys[tenant_id] = set()
            self.tenant_cache_keys[tenant_id].add(cache_key)
        
        if permission_name not in self.permission_cache_keys:
            self.permission_cache_keys[permission_name] = set()
        self.permission_cache_keys[permission_name].add(cache_key)
        
        # Store in memory cache
        self._store_in_memory_cache(cache_key, result)
        
        # Store in Redis cache
        if self.redis_client:
            try:
                cache_data = {
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": str(user_id),
                    "permission": permission_name,
                    "resource_id": resource_id,
                    "resource_type": resource_type.value if resource_type else None,
                    "tenant_id": tenant_id
                }
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(cache_data)
                )
            except Exception as e:
                logger.error(f"Redis cache write error: {e}")
    
    def _store_in_memory_cache(self, cache_key: str, result: bool):
        """Store result in memory cache with LRU eviction."""
        # Implement LRU by removing oldest entries when at capacity
        if len(self.memory_cache) >= self.memory_cache_size:
            # Remove 10% of oldest entries or at least 1
            sorted_items = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1][1]  # Sort by timestamp
            )
            items_to_remove = max(1, len(sorted_items) // 10)
            for i in range(items_to_remove):
                del self.memory_cache[sorted_items[i][0]]
        
        self.memory_cache[cache_key] = (result, datetime.utcnow())
    
    def invalidate_user_permissions(self, user_id: UUID, tenant_id: Optional[str] = None):
        """Invalidate all cached permissions for a user."""
        try:
            user_id_str = str(user_id)
            
            # Get cache keys for this user
            keys_to_remove = set()
            if user_id_str in self.user_cache_keys:
                keys_to_remove = self.user_cache_keys[user_id_str].copy()
            
            # Remove from memory cache
            for key in keys_to_remove:
                if key in self.memory_cache:
                    del self.memory_cache[key]
            
            # Remove from Redis cache
            if self.redis_client and keys_to_remove:
                try:
                    self.redis_client.delete(*keys_to_remove)
                except Exception as e:
                    logger.error(f"Redis invalidation error: {e}")
            
            # Clean up tracking
            if user_id_str in self.user_cache_keys:
                # Remove keys from other tracking sets
                for key in keys_to_remove:
                    # Remove from tenant tracking
                    for tenant_keys in self.tenant_cache_keys.values():
                        tenant_keys.discard(key)
                    # Remove from permission tracking
                    for perm_keys in self.permission_cache_keys.values():
                        perm_keys.discard(key)
                
                # Clear user tracking
                del self.user_cache_keys[user_id_str]
            
            self.cache_stats["invalidations"] += len(keys_to_remove)
            logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for user {user_id}")
            
        except Exception as e:
            logger.error(f"Cache invalidation error for user {user_id}: {e}")
    
    def invalidate_tenant_permissions(self, tenant_id: str):
        """Invalidate all cached permissions for a tenant."""
        try:
            # Get cache keys for this tenant
            keys_to_remove = set()
            if tenant_id in self.tenant_cache_keys:
                keys_to_remove = self.tenant_cache_keys[tenant_id].copy()
            
            # Remove from memory cache
            for key in keys_to_remove:
                if key in self.memory_cache:
                    del self.memory_cache[key]
            
            # Remove from Redis cache
            if self.redis_client and keys_to_remove:
                try:
                    self.redis_client.delete(*keys_to_remove)
                except Exception as e:
                    logger.error(f"Redis tenant invalidation error: {e}")
            
            # Clean up tracking
            if tenant_id in self.tenant_cache_keys:
                # Remove keys from other tracking sets
                for key in keys_to_remove:
                    # Remove from user tracking
                    for user_keys in self.user_cache_keys.values():
                        user_keys.discard(key)
                    # Remove from permission tracking
                    for perm_keys in self.permission_cache_keys.values():
                        perm_keys.discard(key)
                
                # Clear tenant tracking
                del self.tenant_cache_keys[tenant_id]
            
            self.cache_stats["invalidations"] += len(keys_to_remove)
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for tenant {tenant_id}")
            
        except Exception as e:
            logger.error(f"Cache invalidation error for tenant {tenant_id}: {e}")
    
    def invalidate_permission(self, permission_name: str, tenant_id: Optional[str] = None):
        """Invalidate all cached results for a specific permission."""
        try:
            # Get cache keys for this permission
            keys_to_remove = set()
            if permission_name in self.permission_cache_keys:
                keys_to_remove = self.permission_cache_keys[permission_name].copy()
            
            # Remove from memory cache
            for key in keys_to_remove:
                if key in self.memory_cache:
                    del self.memory_cache[key]
            
            # Remove from Redis cache
            if self.redis_client and keys_to_remove:
                try:
                    self.redis_client.delete(*keys_to_remove)
                except Exception as e:
                    logger.error(f"Redis permission invalidation error: {e}")
            
            # Clean up tracking
            if permission_name in self.permission_cache_keys:
                # Remove keys from other tracking sets
                for key in keys_to_remove:
                    # Remove from user tracking
                    for user_keys in self.user_cache_keys.values():
                        user_keys.discard(key)
                    # Remove from tenant tracking
                    for tenant_keys in self.tenant_cache_keys.values():
                        tenant_keys.discard(key)
                
                # Clear permission tracking
                del self.permission_cache_keys[permission_name]
            
            self.cache_stats["invalidations"] += len(keys_to_remove)
            logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for permission {permission_name}")
            
        except Exception as e:
            logger.error(f"Cache invalidation error for permission {permission_name}: {e}")
    
    def warm_user_permissions(
        self,
        user_id: UUID,
        permissions: List[str],
        tenant_id: str,
        db: Session,
        rbac_controller
    ):
        """Pre-warm cache with user's common permissions."""
        try:
            for permission_name in permissions:
                # Check permission and cache result
                result = rbac_controller._check_permission_through_roles(
                    user_id, permission_name, None, None, db
                )
                self.set_permission(
                    user_id, permission_name, result, tenant_id=tenant_id
                )
            
            logger.debug(f"Warmed cache with {len(permissions)} permissions for user {user_id}")
            
        except Exception as e:
            logger.error(f"Cache warming error for user {user_id}: {e}")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        memory_usage = len(self.memory_cache)
        redis_info = {}
        
        if self.redis_client:
            try:
                redis_info = self.redis_client.info("memory")
            except Exception as e:
                logger.error(f"Failed to get Redis info: {e}")
        
        return {
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
            "cache_hits": self.cache_stats["hits"],
            "cache_misses": self.cache_stats["misses"],
            "memory_hits": self.cache_stats["memory_hits"],
            "redis_hits": self.cache_stats["redis_hits"],
            "invalidations": self.cache_stats["invalidations"],
            "memory_cache_size": memory_usage,
            "memory_cache_limit": self.memory_cache_size,
            "redis_connected": self.redis_client is not None,
            "redis_memory_usage": redis_info.get("used_memory_human", "N/A") if redis_info else "N/A"
        }
    
    def clear_all_cache(self):
        """Clear all cached permissions."""
        try:
            # Clear memory cache
            self.memory_cache.clear()
            
            # Clear tracking
            self.user_cache_keys.clear()
            self.tenant_cache_keys.clear()
            self.permission_cache_keys.clear()
            
            # Clear Redis cache
            if self.redis_client:
                # Delete all permission cache keys (those starting with our hash pattern)
                keys = self.redis_client.keys("*")
                if keys:
                    # Filter to only delete our cache keys (could be more specific)
                    self.redis_client.delete(*keys)
            
            # Reset stats
            self.cache_stats = {
                "hits": 0,
                "misses": 0,
                "invalidations": 0,
                "memory_hits": 0,
                "redis_hits": 0
            }
            
            logger.info("Cleared all permission cache")
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Analyze and optimize cache performance."""
        stats = self.get_cache_statistics()
        recommendations = []
        
        # Analyze hit rate
        if stats["hit_rate"] < 80:
            recommendations.append("Consider increasing cache TTL or warming more permissions")
        
        # Analyze memory usage
        memory_usage_percent = (stats["memory_cache_size"] / stats["memory_cache_limit"]) * 100
        if memory_usage_percent > 90:
            recommendations.append("Consider increasing memory cache size")
        
        # Analyze Redis connection
        if not stats["redis_connected"]:
            recommendations.append("Redis connection failed - using memory-only cache")
        
        # Analyze request patterns
        if stats["memory_hits"] < stats["redis_hits"]:
            recommendations.append("Consider increasing memory cache size for better performance")
        
        return {
            "current_performance": stats,
            "recommendations": recommendations,
            "optimization_applied": False
        }


class PermissionCacheManager:
    """
    Manager for coordinating permission cache operations across the application.
    """
    
    def __init__(self, cache: PermissionCache):
        self.cache = cache
        self.invalidation_strategies = {
            "user_role_change": self._handle_user_role_change,
            "role_permission_change": self._handle_role_permission_change,
            "permission_update": self._handle_permission_update,
            "tenant_update": self._handle_tenant_update
        }
    
    def handle_cache_invalidation(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """Handle cache invalidation based on system events."""
        if event_type in self.invalidation_strategies:
            self.invalidation_strategies[event_type](event_data)
        else:
            logger.warning(f"Unknown cache invalidation event: {event_type}")
    
    def _handle_user_role_change(self, event_data: Dict[str, Any]):
        """Handle user role assignment/revocation."""
        user_id = event_data.get("user_id")
        tenant_id = event_data.get("tenant_id")
        
        if user_id:
            self.cache.invalidate_user_permissions(UUID(user_id), tenant_id)
    
    def _handle_role_permission_change(self, event_data: Dict[str, Any]):
        """Handle role permission assignment/revocation."""
        role_id = event_data.get("role_id")
        tenant_id = event_data.get("tenant_id")
        
        # For now, invalidate entire tenant cache
        # Could be optimized to only invalidate affected users
        if tenant_id:
            self.cache.invalidate_tenant_permissions(tenant_id)
    
    def _handle_permission_update(self, event_data: Dict[str, Any]):
        """Handle permission definition changes."""
        permission_name = event_data.get("permission_name")
        tenant_id = event_data.get("tenant_id")
        
        if permission_name:
            self.cache.invalidate_permission(permission_name, tenant_id)
    
    def _handle_tenant_update(self, event_data: Dict[str, Any]):
        """Handle tenant-wide changes."""
        tenant_id = event_data.get("tenant_id")
        
        if tenant_id:
            self.cache.invalidate_tenant_permissions(tenant_id)
    
    def schedule_cache_maintenance(self):
        """Schedule periodic cache maintenance tasks."""
        # This would integrate with a task scheduler
        # For now, just log the intention
        logger.info("Cache maintenance scheduled")
        
        # Perform optimization analysis
        optimization_result = self.cache.optimize_cache()
        if optimization_result["recommendations"]:
            logger.info(f"Cache optimization recommendations: {optimization_result['recommendations']}")
        
        return optimization_result


# Global cache instance
_permission_cache = None
_cache_manager = None


def get_permission_cache() -> PermissionCache:
    """Get the global permission cache instance."""
    global _permission_cache
    if _permission_cache is None:
        _permission_cache = PermissionCache()
    return _permission_cache


def get_cache_manager() -> PermissionCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = PermissionCacheManager(get_permission_cache())
    return _cache_manager