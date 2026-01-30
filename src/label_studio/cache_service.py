"""
Label Studio Workspace Cache Service.

This module provides caching functionality for workspace data to improve
performance and reduce database load. Supports both Redis and in-memory
caching with automatic fallback.

Features:
- Workspace information caching
- User permissions caching
- Member list caching
- TTL-based expiration
- Cache invalidation on updates
- Statistics tracking
"""

import json
import logging
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from uuid import UUID
from functools import wraps

logger = logging.getLogger(__name__)


# ============================================================================
# Cache Configuration
# ============================================================================

@dataclass
class WorkspaceCacheConfig:
    """Cache configuration for workspace data."""

    # TTL settings (in seconds)
    workspace_ttl: int = 300  # 5 minutes
    members_ttl: int = 180  # 3 minutes
    permissions_ttl: int = 60  # 1 minute (permissions change frequently)
    projects_ttl: int = 300  # 5 minutes

    # Cache key prefixes
    workspace_prefix: str = "ls:ws:"
    members_prefix: str = "ls:ws:members:"
    permissions_prefix: str = "ls:ws:perms:"
    projects_prefix: str = "ls:ws:projects:"
    user_workspaces_prefix: str = "ls:user:ws:"

    # Size limits
    max_entries: int = 10000
    max_members_per_workspace: int = 1000


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    invalidations: int = 0
    errors: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "invalidations": self.invalidations,
            "errors": self.errors,
            "hit_rate": round(self.hit_rate, 2),
        }


# ============================================================================
# In-Memory Cache Backend
# ============================================================================

class InMemoryCacheBackend:
    """In-memory cache backend with TTL support."""

    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.access_times: Dict[str, datetime] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry['expires_at']:
                self.access_times[key] = datetime.now()
                return entry['value']
            else:
                self._remove(key)
        return None

    def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in cache with TTL."""
        try:
            if len(self.cache) >= self.max_size:
                self._evict_lru()

            self.cache[key] = {
                'value': value,
                'expires_at': datetime.now() + timedelta(seconds=ttl),
            }
            self.access_times[key] = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.cache:
            self._remove(key)
            return True
        return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern (prefix matching)."""
        count = 0
        keys_to_delete = [k for k in self.cache.keys() if k.startswith(pattern)]
        for key in keys_to_delete:
            self._remove(key)
            count += 1
        return count

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        if key in self.cache:
            if datetime.now() < self.cache[key]['expires_at']:
                return True
            self._remove(key)
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self.cache.clear()
        self.access_times.clear()

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        if pattern == "*":
            return list(self.cache.keys())
        prefix = pattern.rstrip("*")
        return [k for k in self.cache.keys() if k.startswith(prefix)]

    def _remove(self, key: str) -> None:
        """Remove key from cache."""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self.access_times:
            oldest = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            self._remove(oldest)


# ============================================================================
# Redis Cache Backend
# ============================================================================

class RedisCacheBackend:
    """Redis cache backend."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._client = None

    @property
    def client(self):
        """Lazy-load Redis client."""
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                self._client.ping()
                logger.info("Redis cache backend connected")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._client = None
        return self._client

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        try:
            if self.client:
                value = self.client.get(key)
                if value:
                    return json.loads(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None

    def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in Redis with TTL."""
        try:
            if self.client:
                serialized = json.dumps(value, default=str)
                return bool(self.client.setex(key, ttl, serialized))
        except Exception as e:
            logger.error(f"Redis set error: {e}")
        return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            if self.client:
                return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
        return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        try:
            if self.client:
                keys = self.client.keys(pattern + "*")
                if keys:
                    return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete_pattern error: {e}")
        return 0

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            if self.client:
                return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
        return False

    def clear(self) -> None:
        """Clear all workspace-related keys."""
        try:
            if self.client:
                self.delete_pattern("ls:")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        try:
            if self.client:
                return self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
        return []


# ============================================================================
# Workspace Cache Service
# ============================================================================

class WorkspaceCacheService:
    """
    Cache service for Label Studio workspace data.

    Provides caching for:
    - Workspace information
    - User permissions
    - Member lists
    - Project associations

    Automatically handles cache invalidation when data changes.

    Example Usage:
        cache = WorkspaceCacheService()

        # Cache workspace
        cache.set_workspace(workspace_id, workspace_data)

        # Get cached workspace
        workspace = cache.get_workspace(workspace_id)

        # Invalidate on update
        cache.invalidate_workspace(workspace_id)
    """

    def __init__(
        self,
        config: Optional[WorkspaceCacheConfig] = None,
        use_redis: bool = True,
        redis_url: Optional[str] = None,
    ):
        """
        Initialize cache service.

        Args:
            config: Cache configuration
            use_redis: Whether to use Redis (with fallback to in-memory)
            redis_url: Redis connection URL
        """
        self.config = config or WorkspaceCacheConfig()
        self.stats = CacheStats()

        # Initialize backend
        self._redis_backend: Optional[RedisCacheBackend] = None
        self._memory_backend = InMemoryCacheBackend(max_size=self.config.max_entries)

        if use_redis:
            url = redis_url or "redis://localhost:6379/0"
            self._redis_backend = RedisCacheBackend(url)

    @property
    def backend(self):
        """Get active cache backend (Redis with fallback to memory)."""
        if self._redis_backend and self._redis_backend.client:
            return self._redis_backend
        return self._memory_backend

    # ========== Workspace Caching ==========

    def get_workspace(self, workspace_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """
        Get cached workspace data.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Workspace data dict if cached, None otherwise
        """
        key = f"{self.config.workspace_prefix}{workspace_id}"
        value = self.backend.get(key)

        if value is not None:
            self.stats.hits += 1
            logger.debug(f"Cache hit for workspace {workspace_id}")
            return value

        self.stats.misses += 1
        return None

    def set_workspace(
        self,
        workspace_id: Union[str, UUID],
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache workspace data.

        Args:
            workspace_id: Workspace UUID
            data: Workspace data to cache
            ttl: Time to live in seconds (default: config.workspace_ttl)

        Returns:
            True if cached successfully
        """
        key = f"{self.config.workspace_prefix}{workspace_id}"
        ttl = ttl or self.config.workspace_ttl

        if self.backend.set(key, data, ttl):
            self.stats.sets += 1
            logger.debug(f"Cached workspace {workspace_id}")
            return True

        self.stats.errors += 1
        return False

    def invalidate_workspace(self, workspace_id: Union[str, UUID]) -> bool:
        """
        Invalidate cached workspace data.

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if invalidated
        """
        key = f"{self.config.workspace_prefix}{workspace_id}"
        if self.backend.delete(key):
            self.stats.invalidations += 1
            logger.debug(f"Invalidated workspace cache {workspace_id}")
            return True
        return False

    # ========== Members Caching ==========

    def get_members(self, workspace_id: Union[str, UUID]) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached workspace members.

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of member dicts if cached, None otherwise
        """
        key = f"{self.config.members_prefix}{workspace_id}"
        value = self.backend.get(key)

        if value is not None:
            self.stats.hits += 1
            return value

        self.stats.misses += 1
        return None

    def set_members(
        self,
        workspace_id: Union[str, UUID],
        members: List[Dict[str, Any]],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache workspace members.

        Args:
            workspace_id: Workspace UUID
            members: List of member data
            ttl: Time to live in seconds

        Returns:
            True if cached successfully
        """
        key = f"{self.config.members_prefix}{workspace_id}"
        ttl = ttl or self.config.members_ttl

        if self.backend.set(key, members, ttl):
            self.stats.sets += 1
            return True

        self.stats.errors += 1
        return False

    def invalidate_members(self, workspace_id: Union[str, UUID]) -> bool:
        """Invalidate cached members for workspace."""
        key = f"{self.config.members_prefix}{workspace_id}"
        if self.backend.delete(key):
            self.stats.invalidations += 1
            return True
        return False

    # ========== Permissions Caching ==========

    def get_permissions(
        self,
        workspace_id: Union[str, UUID],
        user_id: Union[str, UUID],
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached user permissions for workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID

        Returns:
            Permissions dict if cached, None otherwise
        """
        key = f"{self.config.permissions_prefix}{workspace_id}:{user_id}"
        value = self.backend.get(key)

        if value is not None:
            self.stats.hits += 1
            return value

        self.stats.misses += 1
        return None

    def set_permissions(
        self,
        workspace_id: Union[str, UUID],
        user_id: Union[str, UUID],
        permissions: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache user permissions for workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID
            permissions: Permissions data
            ttl: Time to live in seconds

        Returns:
            True if cached successfully
        """
        key = f"{self.config.permissions_prefix}{workspace_id}:{user_id}"
        ttl = ttl or self.config.permissions_ttl

        if self.backend.set(key, permissions, ttl):
            self.stats.sets += 1
            return True

        self.stats.errors += 1
        return False

    def invalidate_permissions(
        self,
        workspace_id: Union[str, UUID],
        user_id: Optional[Union[str, UUID]] = None,
    ) -> int:
        """
        Invalidate cached permissions.

        Args:
            workspace_id: Workspace UUID
            user_id: User UUID (if None, invalidates all permissions for workspace)

        Returns:
            Number of entries invalidated
        """
        if user_id:
            key = f"{self.config.permissions_prefix}{workspace_id}:{user_id}"
            if self.backend.delete(key):
                self.stats.invalidations += 1
                return 1
            return 0
        else:
            pattern = f"{self.config.permissions_prefix}{workspace_id}:"
            count = self.backend.delete_pattern(pattern)
            self.stats.invalidations += count
            return count

    # ========== User Workspaces Caching ==========

    def get_user_workspaces(self, user_id: Union[str, UUID]) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached list of workspaces for user.

        Args:
            user_id: User UUID

        Returns:
            List of workspace dicts if cached, None otherwise
        """
        key = f"{self.config.user_workspaces_prefix}{user_id}"
        value = self.backend.get(key)

        if value is not None:
            self.stats.hits += 1
            return value

        self.stats.misses += 1
        return None

    def set_user_workspaces(
        self,
        user_id: Union[str, UUID],
        workspaces: List[Dict[str, Any]],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache list of workspaces for user.

        Args:
            user_id: User UUID
            workspaces: List of workspace data
            ttl: Time to live in seconds

        Returns:
            True if cached successfully
        """
        key = f"{self.config.user_workspaces_prefix}{user_id}"
        ttl = ttl or self.config.workspace_ttl

        if self.backend.set(key, workspaces, ttl):
            self.stats.sets += 1
            return True

        self.stats.errors += 1
        return False

    def invalidate_user_workspaces(self, user_id: Union[str, UUID]) -> bool:
        """Invalidate cached workspaces for user."""
        key = f"{self.config.user_workspaces_prefix}{user_id}"
        if self.backend.delete(key):
            self.stats.invalidations += 1
            return True
        return False

    # ========== Projects Caching ==========

    def get_projects(self, workspace_id: Union[str, UUID]) -> Optional[List[Dict[str, Any]]]:
        """Get cached workspace projects."""
        key = f"{self.config.projects_prefix}{workspace_id}"
        value = self.backend.get(key)

        if value is not None:
            self.stats.hits += 1
            return value

        self.stats.misses += 1
        return None

    def set_projects(
        self,
        workspace_id: Union[str, UUID],
        projects: List[Dict[str, Any]],
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache workspace projects."""
        key = f"{self.config.projects_prefix}{workspace_id}"
        ttl = ttl or self.config.projects_ttl

        if self.backend.set(key, projects, ttl):
            self.stats.sets += 1
            return True

        self.stats.errors += 1
        return False

    def invalidate_projects(self, workspace_id: Union[str, UUID]) -> bool:
        """Invalidate cached projects for workspace."""
        key = f"{self.config.projects_prefix}{workspace_id}"
        if self.backend.delete(key):
            self.stats.invalidations += 1
            return True
        return False

    # ========== Bulk Invalidation ==========

    def invalidate_workspace_all(self, workspace_id: Union[str, UUID]) -> int:
        """
        Invalidate all cached data for a workspace.

        Use when workspace is deleted or significantly changed.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Number of entries invalidated
        """
        count = 0
        ws_id = str(workspace_id)

        # Invalidate workspace
        if self.invalidate_workspace(ws_id):
            count += 1

        # Invalidate members
        if self.invalidate_members(ws_id):
            count += 1

        # Invalidate all permissions
        count += self.invalidate_permissions(ws_id)

        # Invalidate projects
        if self.invalidate_projects(ws_id):
            count += 1

        logger.info(f"Invalidated {count} cache entries for workspace {ws_id}")
        return count

    def invalidate_user_all(self, user_id: Union[str, UUID]) -> int:
        """
        Invalidate all cached data for a user.

        Use when user permissions change globally.

        Args:
            user_id: User UUID

        Returns:
            Number of entries invalidated
        """
        count = 0

        # Invalidate user workspaces
        if self.invalidate_user_workspaces(user_id):
            count += 1

        # Invalidate permissions (pattern match)
        pattern = f"{self.config.permissions_prefix}*:{user_id}"
        count += self.backend.delete_pattern(pattern)

        logger.info(f"Invalidated {count} cache entries for user {user_id}")
        return count

    # ========== Statistics & Management ==========

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.stats.to_dict()

    def clear(self) -> None:
        """Clear all cached workspace data."""
        self.backend.clear()
        logger.info("Cleared all workspace cache")

    def is_redis_available(self) -> bool:
        """Check if Redis backend is available."""
        return self._redis_backend is not None and self._redis_backend.client is not None


# ============================================================================
# Cache Decorators
# ============================================================================

def cache_workspace(ttl: Optional[int] = None):
    """
    Decorator to cache workspace fetch results.

    Usage:
        @cache_workspace(ttl=300)
        def get_workspace(self, workspace_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, workspace_id, *args, **kwargs):
            cache = getattr(self, '_cache', None)
            if cache:
                cached = cache.get_workspace(workspace_id)
                if cached:
                    return cached

            result = func(self, workspace_id, *args, **kwargs)

            if result and cache:
                cache.set_workspace(workspace_id, result, ttl)

            return result
        return wrapper
    return decorator


def cache_permissions(ttl: Optional[int] = None):
    """
    Decorator to cache permission check results.

    Usage:
        @cache_permissions(ttl=60)
        def get_user_permissions(self, workspace_id, user_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, workspace_id, user_id, *args, **kwargs):
            cache = getattr(self, '_cache', None)
            if cache:
                cached = cache.get_permissions(workspace_id, user_id)
                if cached:
                    return cached

            result = func(self, workspace_id, user_id, *args, **kwargs)

            if result and cache:
                cache.set_permissions(workspace_id, user_id, result, ttl)

            return result
        return wrapper
    return decorator


# ============================================================================
# Global Instance
# ============================================================================

_cache_instance: Optional[WorkspaceCacheService] = None


def get_workspace_cache(
    use_redis: bool = True,
    redis_url: Optional[str] = None,
) -> WorkspaceCacheService:
    """
    Get or create global workspace cache service instance.

    Args:
        use_redis: Whether to use Redis backend
        redis_url: Redis connection URL

    Returns:
        WorkspaceCacheService instance
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = WorkspaceCacheService(
            use_redis=use_redis,
            redis_url=redis_url,
        )

    return _cache_instance


def clear_cache_instance() -> None:
    """Clear global cache instance (for testing)."""
    global _cache_instance
    if _cache_instance:
        _cache_instance.clear()
    _cache_instance = None
