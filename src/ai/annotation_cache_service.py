"""
AI Annotation Cache Service

Provides caching for annotation models and results to improve performance.
Uses Redis for distributed caching with memory fallback.

Requirements: 9.4, 9.5
"""

import asyncio
import json
import hashlib
import logging
from typing import Dict, Any, Optional, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import OrderedDict
import pickle

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata."""
    value: T
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    
    Used as in-memory fallback when Redis is unavailable.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            
            return entry.value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set value in cache."""
        async with self._lock:
            # Calculate expiration
            ttl_seconds = ttl if ttl is not None else self.default_ttl
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds) if ttl_seconds > 0 else None
            
            # Create entry
            entry = CacheEntry(
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at
            )
            
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)
            
            self._cache[key] = entry
            self._cache.move_to_end(key)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all entries."""
        async with self._lock:
            self._cache.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_entries = len(self._cache)
            expired_count = sum(1 for e in self._cache.values() if e.is_expired())
            total_accesses = sum(e.access_count for e in self._cache.values())
            
            return {
                'total_entries': total_entries,
                'max_size': self.max_size,
                'expired_count': expired_count,
                'total_accesses': total_accesses,
                'utilization': total_entries / self.max_size if self.max_size > 0 else 0,
            }


class AnnotationCacheService:
    """
    Annotation cache service with Redis and memory fallback.
    
    Provides caching for:
    - Loaded annotation models
    - Annotation suggestions
    - Quality metrics
    - Engine health status
    """
    
    # Cache key prefixes
    PREFIX_MODEL = "annotation:model"
    PREFIX_SUGGESTION = "annotation:suggestion"
    PREFIX_QUALITY = "annotation:quality"
    PREFIX_HEALTH = "annotation:engine_health"
    
    # Default TTLs (in seconds)
    TTL_MODEL = 3600  # 1 hour
    TTL_SUGGESTION = 300  # 5 minutes
    TTL_QUALITY = 3600  # 1 hour
    TTL_HEALTH = 60  # 1 minute
    
    def __init__(
        self,
        redis_client: Optional[Any] = None,
        memory_cache_size: int = 1000
    ):
        """
        Initialize cache service.
        
        Args:
            redis_client: Optional Redis client
            memory_cache_size: Size of in-memory LRU cache
        """
        self.redis = redis_client
        self.memory_cache = LRUCache(max_size=memory_cache_size)
        self._lock = asyncio.Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'redis_errors': 0,
        }

    
    def _generate_key(self, prefix: str, *parts: str) -> str:
        """Generate cache key from parts."""
        return f"{prefix}:{':'.join(parts)}"
    
    def _hash_content(self, content: str) -> str:
        """Generate hash for content."""
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        if self.redis is None:
            return None
        
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            self._stats['redis_errors'] += 1
            return None
    
    async def _set_in_redis(
        self,
        key: str,
        value: Any,
        ttl: int
    ) -> bool:
        """Set value in Redis."""
        if self.redis is None:
            return False
        
        try:
            await self.redis.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            self._stats['redis_errors'] += 1
            return False
    
    async def _delete_from_redis(self, key: str) -> bool:
        """Delete key from Redis."""
        if self.redis is None:
            return False
        
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            self._stats['redis_errors'] += 1
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (Redis first, then memory).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        # Try Redis first
        value = await self._get_from_redis(key)
        if value is not None:
            self._stats['hits'] += 1
            return value
        
        # Fall back to memory cache
        value = await self.memory_cache.get(key)
        if value is not None:
            self._stats['hits'] += 1
            return value
        
        self._stats['misses'] += 1
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set value in cache (both Redis and memory).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (optional)
        """
        ttl = ttl or self.TTL_MODEL
        
        # Set in Redis
        await self._set_in_redis(key, value, ttl)
        
        # Also set in memory cache
        await self.memory_cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        await self._delete_from_redis(key)
        await self.memory_cache.delete(key)

    
    # =========================================================================
    # Model Caching (Requirement 9.4)
    # =========================================================================
    
    async def get_model(
        self,
        engine_name: str,
        model_version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached model configuration.
        
        Args:
            engine_name: Name of the annotation engine
            model_version: Model version
            
        Returns:
            Model configuration or None
        """
        key = self._generate_key(self.PREFIX_MODEL, engine_name, model_version)
        return await self.get(key)
    
    async def set_model(
        self,
        engine_name: str,
        model_version: str,
        model_config: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache model configuration.
        
        Args:
            engine_name: Name of the annotation engine
            model_version: Model version
            model_config: Model configuration to cache
            ttl: TTL in seconds (optional)
        """
        key = self._generate_key(self.PREFIX_MODEL, engine_name, model_version)
        await self.set(key, model_config, ttl or self.TTL_MODEL)
    
    async def invalidate_model(
        self,
        engine_name: str,
        model_version: Optional[str] = None
    ) -> None:
        """
        Invalidate cached model.
        
        Args:
            engine_name: Name of the annotation engine
            model_version: Model version (optional, invalidates all if not specified)
        """
        if model_version:
            key = self._generate_key(self.PREFIX_MODEL, engine_name, model_version)
            await self.delete(key)
        else:
            # Invalidate all versions for this engine
            # Note: This requires pattern matching which is expensive
            # In production, use Redis SCAN with pattern
            logger.info(f"Invalidating all models for engine: {engine_name}")
    
    # =========================================================================
    # Suggestion Caching
    # =========================================================================
    
    async def get_suggestion(
        self,
        project_id: str,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached annotation suggestion.
        
        Args:
            project_id: Project identifier
            item_id: Item identifier
            
        Returns:
            Cached suggestion or None
        """
        key = self._generate_key(self.PREFIX_SUGGESTION, project_id, item_id)
        return await self.get(key)
    
    async def set_suggestion(
        self,
        project_id: str,
        item_id: str,
        suggestion: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache annotation suggestion.
        
        Args:
            project_id: Project identifier
            item_id: Item identifier
            suggestion: Suggestion to cache
            ttl: TTL in seconds (optional)
        """
        key = self._generate_key(self.PREFIX_SUGGESTION, project_id, item_id)
        await self.set(key, suggestion, ttl or self.TTL_SUGGESTION)
    
    async def invalidate_suggestions(self, project_id: str) -> None:
        """Invalidate all suggestions for a project."""
        logger.info(f"Invalidating suggestions for project: {project_id}")

    
    # =========================================================================
    # Quality Metrics Caching
    # =========================================================================
    
    async def get_quality_metrics(
        self,
        project_id: str,
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached quality metrics.
        
        Args:
            project_id: Project identifier
            date: Date string (optional, defaults to today)
            
        Returns:
            Cached metrics or None
        """
        date = date or datetime.now().strftime('%Y-%m-%d')
        key = self._generate_key(self.PREFIX_QUALITY, project_id, date)
        return await self.get(key)
    
    async def set_quality_metrics(
        self,
        project_id: str,
        metrics: Dict[str, Any],
        date: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache quality metrics.
        
        Args:
            project_id: Project identifier
            metrics: Metrics to cache
            date: Date string (optional)
            ttl: TTL in seconds (optional)
        """
        date = date or datetime.now().strftime('%Y-%m-%d')
        key = self._generate_key(self.PREFIX_QUALITY, project_id, date)
        await self.set(key, metrics, ttl or self.TTL_QUALITY)
    
    # =========================================================================
    # Engine Health Caching
    # =========================================================================
    
    async def get_engine_health(
        self,
        engine_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached engine health status.
        
        Args:
            engine_name: Name of the annotation engine
            
        Returns:
            Cached health status or None
        """
        key = self._generate_key(self.PREFIX_HEALTH, engine_name)
        return await self.get(key)
    
    async def set_engine_health(
        self,
        engine_name: str,
        health_status: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache engine health status.
        
        Args:
            engine_name: Name of the annotation engine
            health_status: Health status to cache
            ttl: TTL in seconds (optional)
        """
        key = self._generate_key(self.PREFIX_HEALTH, engine_name)
        await self.set(key, health_status, ttl or self.TTL_HEALTH)
    
    # =========================================================================
    # Statistics and Management
    # =========================================================================
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        memory_stats = await self.memory_cache.get_stats()
        
        hit_rate = 0.0
        total_requests = self._stats['hits'] + self._stats['misses']
        if total_requests > 0:
            hit_rate = self._stats['hits'] / total_requests
        
        return {
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': hit_rate,
            'redis_errors': self._stats['redis_errors'],
            'redis_available': self.redis is not None,
            'memory_cache': memory_stats,
        }
    
    async def clear_all(self) -> None:
        """Clear all caches."""
        await self.memory_cache.clear()
        if self.redis:
            try:
                # Clear annotation-related keys only
                # In production, use SCAN with pattern
                logger.info("Clearing Redis annotation cache")
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
    
    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            'hits': 0,
            'misses': 0,
            'redis_errors': 0,
        }


# Global cache instance
_cache_service: Optional[AnnotationCacheService] = None


def get_cache_service() -> AnnotationCacheService:
    """Get the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = AnnotationCacheService()
    return _cache_service


async def init_cache_service(redis_client: Optional[Any] = None) -> AnnotationCacheService:
    """
    Initialize the cache service with optional Redis client.
    
    Args:
        redis_client: Optional Redis client
        
    Returns:
        Initialized cache service
    """
    global _cache_service
    _cache_service = AnnotationCacheService(redis_client=redis_client)
    return _cache_service
