"""
Cache manager with two-tier caching (local memory + optional Redis).

Provides fast configuration caching with TTL, LRU eviction, and Redis pub/sub
for multi-instance cache invalidation.
"""

import json
import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from fnmatch import fnmatch

logger = logging.getLogger(__name__)


class CacheEntry:
    """A single cache entry with TTL."""
    
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return datetime.utcnow() > self.expires_at


class CacheManager:
    """
    Two-tier cache manager with local memory and optional Redis.
    
    Features:
    - Local memory cache with TTL and LRU eviction
    - Optional Redis cache for multi-instance synchronization
    - Redis pub/sub for cache invalidation broadcasting
    - Memory limit enforcement
    """
    
    INVALIDATION_CHANNEL = "llm:config:invalidate"
    
    def __init__(
        self,
        redis_client: Optional[Any] = None,
        local_ttl: int = 300,
        max_memory_mb: int = 100
    ):
        """
        Initialize the cache manager.
        
        Args:
            redis_client: Optional Redis client for distributed caching.
            local_ttl: TTL for local cache entries in seconds (default 300).
            max_memory_mb: Maximum memory for local cache in MB (default 100).
        """
        self.local_cache: Dict[str, CacheEntry] = {}
        self.redis = redis_client
        self.local_ttl = local_ttl
        self.max_memory_mb = max_memory_mb
        self._access_order: list[str] = []  # For LRU tracking
        
        if redis_client:
            self._subscribe_task: Optional[asyncio.Task] = None
            self._running = False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache with TTL validation.
        
        Args:
            key: Cache key.
        
        Returns:
            Cached value or None if not found/expired.
        """
        # Try local cache first
        if key in self.local_cache:
            entry = self.local_cache[key]
            if not entry.is_expired():
                # Update LRU order
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return entry.value
            else:
                # Remove expired entry
                del self.local_cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
        
        # Try Redis if available
        if self.redis:
            try:
                value_json = await self.redis.get(key)
                if value_json:
                    value = json.loads(value_json)
                    # Populate local cache
                    self.local_cache[key] = CacheEntry(value, self.local_ttl)
                    self._access_order.append(key)
                    return value
            except Exception as e:
                logger.warning(f"Redis cache read failed for key {key}: {e}")
        
        return None
    
    async def set(self, key: str, value: Any) -> None:
        """
        Set value in both cache tiers.
        
        Args:
            key: Cache key.
            value: Value to cache (must be JSON-serializable).
        """
        # Set in local cache
        self.local_cache[key] = CacheEntry(value, self.local_ttl)
        if key not in self._access_order:
            self._access_order.append(key)
        
        # Set in Redis if available
        if self.redis:
            try:
                value_json = json.dumps(value)
                await self.redis.setex(key, self.local_ttl, value_json)
            except Exception as e:
                logger.warning(f"Redis cache write failed for key {key}: {e}")
        
        # Evict if memory limit exceeded
        self._evict_if_needed()
    
    async def invalidate(self, pattern: str, broadcast: bool = True) -> None:
        """
        Invalidate cache entries matching pattern.
        
        Args:
            pattern: Glob pattern for keys to invalidate (e.g., "llm:config:*").
            broadcast: If True and Redis available, broadcast to other instances.
        """
        # Invalidate local cache
        keys_to_delete = [k for k in self.local_cache.keys() if fnmatch(k, pattern)]
        for key in keys_to_delete:
            del self.local_cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
        
        logger.info(f"Invalidated {len(keys_to_delete)} local cache entries matching '{pattern}'")
        
        # Invalidate Redis and broadcast
        if self.redis:
            try:
                # Delete from Redis
                if keys_to_delete:
                    await self.redis.delete(*keys_to_delete)
                
                # Broadcast invalidation event
                if broadcast:
                    await self.redis.publish(
                        self.INVALIDATION_CHANNEL,
                        json.dumps({"pattern": pattern})
                    )
                    logger.debug(f"Broadcasted cache invalidation for pattern '{pattern}'")
            except Exception as e:
                logger.warning(f"Redis cache invalidation failed: {e}")
    
    def _evict_if_needed(self) -> None:
        """Evict least recently used entries if memory limit exceeded."""
        # Simple heuristic: assume each entry is ~1KB
        estimated_size_mb = len(self.local_cache) / 1024
        
        if estimated_size_mb > self.max_memory_mb:
            # Evict 10% of entries (LRU)
            num_to_evict = max(1, len(self.local_cache) // 10)
            for _ in range(num_to_evict):
                if self._access_order:
                    lru_key = self._access_order.pop(0)
                    if lru_key in self.local_cache:
                        del self.local_cache[lru_key]
            
            logger.info(f"Evicted {num_to_evict} LRU cache entries (memory limit: {self.max_memory_mb}MB)")
    
    async def start_invalidation_listener(self) -> None:
        """Start listening for Redis pub/sub invalidation events."""
        if not self.redis:
            return
        
        self._running = True
        self._subscribe_task = asyncio.create_task(self._listen_for_invalidations())
        logger.info("Started cache invalidation listener")
    
    async def stop_invalidation_listener(self) -> None:
        """Stop listening for Redis pub/sub invalidation events."""
        self._running = False
        if self._subscribe_task:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped cache invalidation listener")
    
    async def _listen_for_invalidations(self) -> None:
        """Background task to listen for cache invalidation events."""
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(self.INVALIDATION_CHANNEL)
            
            while self._running:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        pattern = data.get('pattern')
                        if pattern:
                            # Invalidate local cache only (don't broadcast again)
                            await self.invalidate(pattern, broadcast=False)
                    except Exception as e:
                        logger.error(f"Error processing invalidation message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Cache invalidation listener error: {e}")


# Global singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(redis_client: Optional[Any] = None) -> CacheManager:
    """
    Get or create the global CacheManager instance.
    
    Args:
        redis_client: Optional Redis client.
    
    Returns:
        CacheManager instance.
    """
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager(redis_client=redis_client)
    elif redis_client is not None and _cache_manager.redis is None:
        _cache_manager.redis = redis_client
    
    return _cache_manager
