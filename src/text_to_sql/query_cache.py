"""
Query Cache for Text-to-SQL Methods module.

Provides caching for SQL generation results including:
- Redis-based caching with TTL
- LRU eviction policy
- Schema-aware cache invalidation
- Cache statistics and monitoring
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_TTL_SECONDS = 3600  # 1 hour
DEFAULT_MAX_SIZE = 10000
CACHE_KEY_PREFIX = "text2sql"


# =============================================================================
# Data Models
# =============================================================================

class CacheEntryStatus(str, Enum):
    """Cache entry status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    EVICTED = "evicted"


class CacheEntry(BaseModel):
    """Cache entry for query-SQL pair."""
    key: str = Field(..., description="Cache key")
    query: str = Field(..., description="Original natural language query")
    sql: str = Field(..., description="Generated SQL")
    method_used: str = Field(..., description="Generation method used")
    confidence: float = Field(default=0.0, description="Confidence score")
    database_type: str = Field(..., description="Database type")
    schema_hash: str = Field(..., description="Schema version hash")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=1)
    ttl_seconds: int = Field(default=DEFAULT_TTL_SECONDS)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry_time


class CacheConfig(BaseModel):
    """Cache configuration."""
    max_size: int = Field(default=DEFAULT_MAX_SIZE, description="Maximum cache entries")
    default_ttl_seconds: int = Field(default=DEFAULT_TTL_SECONDS, description="Default TTL")
    redis_url: Optional[str] = Field(None, description="Redis URL for distributed caching")
    enable_lru: bool = Field(default=True, description="Enable LRU eviction")
    enable_stats: bool = Field(default=True, description="Enable statistics tracking")
    schema_aware: bool = Field(default=True, description="Invalidate on schema changes")


class CacheStats(BaseModel):
    """Cache statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    expirations: int = 0
    current_size: int = 0
    max_size: int = DEFAULT_MAX_SIZE

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate


# =============================================================================
# Query Cache Class
# =============================================================================

class QueryCache:
    """
    Query Cache for Text-to-SQL results.

    Features:
    - In-memory LRU cache with configurable size
    - Optional Redis backend for distributed caching
    - TTL-based expiration
    - Schema-aware invalidation
    - Statistics tracking
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize Query Cache.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()

        # In-memory LRU cache (OrderedDict for LRU behavior)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = CacheStats(max_size=self.config.max_size)

        # Schema hashes for invalidation
        self._schema_hashes: Dict[str, str] = {}

        # Redis client (lazy initialization)
        self._redis_client = None

        logger.info(f"QueryCache initialized with max_size={self.config.max_size}")

    async def _get_redis_client(self):
        """Get or create Redis client."""
        if self._redis_client is None and self.config.redis_url:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(self.config.redis_url)
                logger.info("Redis client initialized for distributed caching")
            except ImportError:
                logger.warning("redis package not installed, using in-memory cache only")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
        return self._redis_client

    # =========================================================================
    # Cache Key Generation
    # =========================================================================

    def generate_key(
        self,
        query: str,
        database_type: str,
        schema_hash: str,
    ) -> str:
        """
        Generate cache key from query, database type, and schema.

        Format: text2sql:{db_type}:{schema_hash}:{query_hash}

        Args:
            query: Natural language query
            database_type: Database type
            schema_hash: Schema version hash

        Returns:
            Cache key string
        """
        # Normalize query
        normalized_query = self._normalize_query(query)

        # Generate query hash
        query_hash = hashlib.md5(normalized_query.encode()).hexdigest()

        # Build key
        key = f"{CACHE_KEY_PREFIX}:{database_type}:{schema_hash[:8]}:{query_hash}"

        return key

    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent hashing."""
        # Lowercase
        normalized = query.lower().strip()

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        # Remove punctuation at end
        normalized = normalized.rstrip('?.,!')

        return normalized

    # =========================================================================
    # Cache Operations
    # =========================================================================

    async def get(
        self,
        query: str,
        database_type: str,
        schema_hash: str,
    ) -> Optional[CacheEntry]:
        """
        Get cached SQL for a query.

        Args:
            query: Natural language query
            database_type: Database type
            schema_hash: Schema version hash

        Returns:
            CacheEntry if found and valid, None otherwise
        """
        key = self.generate_key(query, database_type, schema_hash)

        if self.config.enable_stats:
            self._stats.total_requests += 1

        # Try Redis first
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                data = await redis_client.get(key)
                if data:
                    entry = CacheEntry.model_validate_json(data)
                    if not entry.is_expired:
                        # Update access time
                        entry.last_accessed_at = datetime.utcnow()
                        entry.access_count += 1
                        await redis_client.set(
                            key,
                            entry.model_dump_json(),
                            ex=entry.ttl_seconds
                        )

                        if self.config.enable_stats:
                            self._stats.cache_hits += 1

                        logger.debug(f"Cache hit (Redis): {key[:50]}")
                        return entry
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # Try in-memory cache
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]

                # Check expiration
                if entry.is_expired:
                    del self._cache[key]
                    if self.config.enable_stats:
                        self._stats.expirations += 1
                        self._stats.cache_misses += 1
                    return None

                # Update access (LRU)
                entry.last_accessed_at = datetime.utcnow()
                entry.access_count += 1

                # Move to end (most recently used)
                if self.config.enable_lru:
                    self._cache.move_to_end(key)

                if self.config.enable_stats:
                    self._stats.cache_hits += 1

                logger.debug(f"Cache hit (memory): {key[:50]}")
                return entry

        if self.config.enable_stats:
            self._stats.cache_misses += 1

        logger.debug(f"Cache miss: {key[:50]}")
        return None

    async def set(
        self,
        query: str,
        sql: str,
        database_type: str,
        schema_hash: str,
        method_used: str,
        confidence: float = 0.0,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Cache a query-SQL pair.

        Args:
            query: Natural language query
            sql: Generated SQL
            database_type: Database type
            schema_hash: Schema version hash
            method_used: Generation method used
            confidence: Confidence score
            ttl_seconds: TTL override
            metadata: Additional metadata

        Returns:
            Cache key
        """
        key = self.generate_key(query, database_type, schema_hash)
        ttl = ttl_seconds or self.config.default_ttl_seconds

        entry = CacheEntry(
            key=key,
            query=query,
            sql=sql,
            method_used=method_used,
            confidence=confidence,
            database_type=database_type,
            schema_hash=schema_hash,
            ttl_seconds=ttl,
            metadata=metadata or {},
        )

        # Store in Redis
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                await redis_client.set(key, entry.model_dump_json(), ex=ttl)
                logger.debug(f"Cached in Redis: {key[:50]}")
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")

        # Store in memory
        async with self._lock:
            # Check if we need to evict
            if len(self._cache) >= self.config.max_size:
                await self._evict_lru()

            self._cache[key] = entry

            if self.config.enable_stats:
                self._stats.current_size = len(self._cache)

        # Update schema hash tracking
        self._schema_hashes[database_type] = schema_hash

        logger.debug(f"Cached: {key[:50]}")
        return key

    async def delete(self, key: str) -> bool:
        """
        Delete a cache entry.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        deleted = False

        # Delete from Redis
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                result = await redis_client.delete(key)
                deleted = result > 0
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

        # Delete from memory
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                deleted = True
                if self.config.enable_stats:
                    self._stats.current_size = len(self._cache)

        return deleted

    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        if self.config.enable_lru:
            # Pop first item (least recently used)
            key, _ = self._cache.popitem(last=False)
        else:
            # Pop random item
            key = next(iter(self._cache))
            del self._cache[key]

        if self.config.enable_stats:
            self._stats.evictions += 1
            self._stats.current_size = len(self._cache)

        logger.debug(f"Evicted: {key[:50]}")

    # =========================================================================
    # Schema-Aware Invalidation
    # =========================================================================

    async def invalidate_by_schema(
        self,
        database_type: str,
        new_schema_hash: Optional[str] = None,
    ) -> int:
        """
        Invalidate all cache entries for a schema change.

        Args:
            database_type: Database type
            new_schema_hash: Optional new schema hash to set

        Returns:
            Number of entries invalidated
        """
        old_hash = self._schema_hashes.get(database_type)

        if new_schema_hash:
            self._schema_hashes[database_type] = new_schema_hash

        invalidated = 0
        prefix = f"{CACHE_KEY_PREFIX}:{database_type}:"

        # Invalidate Redis entries
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = await redis_client.scan(
                        cursor, match=f"{prefix}*", count=100
                    )
                    if keys:
                        await redis_client.delete(*keys)
                        invalidated += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis invalidation failed: {e}")

        # Invalidate memory entries
        async with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys()
                if k.startswith(prefix)
            ]
            for key in keys_to_delete:
                del self._cache[key]
                invalidated += 1

            if self.config.enable_stats:
                self._stats.current_size = len(self._cache)

        logger.info(
            f"Invalidated {invalidated} entries for schema change "
            f"(db_type={database_type}, old_hash={old_hash[:8] if old_hash else 'None'})"
        )
        return invalidated

    async def invalidate_by_pattern(self, pattern: str) -> int:
        """
        Invalidate entries matching a pattern.

        Args:
            pattern: Key pattern (with *)

        Returns:
            Number of entries invalidated
        """
        invalidated = 0

        # Invalidate Redis entries
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = await redis_client.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await redis_client.delete(*keys)
                        invalidated += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis pattern invalidation failed: {e}")

        # Invalidate memory entries
        import fnmatch
        async with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys()
                if fnmatch.fnmatch(k, pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
                invalidated += 1

            if self.config.enable_stats:
                self._stats.current_size = len(self._cache)

        return invalidated

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        async with self._lock:
            self._stats.current_size = len(self._cache)
        return self._stats

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = CacheStats(max_size=self.config.max_size)

    async def get_entry_stats(self) -> Dict[str, Any]:
        """Get detailed entry statistics."""
        async with self._lock:
            entries = list(self._cache.values())

        if not entries:
            return {
                "count": 0,
                "avg_access_count": 0,
                "methods": {},
                "databases": {},
            }

        methods: Dict[str, int] = {}
        databases: Dict[str, int] = {}
        total_access = 0

        for entry in entries:
            methods[entry.method_used] = methods.get(entry.method_used, 0) + 1
            databases[entry.database_type] = databases.get(entry.database_type, 0) + 1
            total_access += entry.access_count

        return {
            "count": len(entries),
            "avg_access_count": total_access / len(entries),
            "methods": methods,
            "databases": databases,
        }

    # =========================================================================
    # Maintenance
    # =========================================================================

    async def cleanup_expired(self) -> int:
        """
        Clean up expired entries.

        Returns:
            Number of entries cleaned up
        """
        cleaned = 0

        async with self._lock:
            now = datetime.utcnow()
            keys_to_delete = []

            for key, entry in self._cache.items():
                if entry.is_expired:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self._cache[key]
                cleaned += 1

            if self.config.enable_stats:
                self._stats.expirations += cleaned
                self._stats.current_size = len(self._cache)

        logger.info(f"Cleaned up {cleaned} expired entries")
        return cleaned

    async def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        cleared = 0

        # Clear Redis
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                cursor = 0
                while True:
                    cursor, keys = await redis_client.scan(
                        cursor, match=f"{CACHE_KEY_PREFIX}:*", count=100
                    )
                    if keys:
                        await redis_client.delete(*keys)
                        cleared += len(keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")

        # Clear memory
        async with self._lock:
            cleared += len(self._cache)
            self._cache.clear()

            if self.config.enable_stats:
                self._stats.current_size = 0

        logger.info(f"Cleared {cleared} cache entries")
        return cleared

    async def warm_up(
        self,
        entries: List[Dict[str, Any]],
    ) -> int:
        """
        Warm up cache with pre-computed entries.

        Args:
            entries: List of cache entries to add

        Returns:
            Number of entries added
        """
        added = 0

        for entry_data in entries:
            try:
                await self.set(
                    query=entry_data["query"],
                    sql=entry_data["sql"],
                    database_type=entry_data["database_type"],
                    schema_hash=entry_data.get("schema_hash", "default"),
                    method_used=entry_data.get("method_used", "warmup"),
                    confidence=entry_data.get("confidence", 0.0),
                    ttl_seconds=entry_data.get("ttl_seconds"),
                    metadata=entry_data.get("metadata"),
                )
                added += 1
            except Exception as e:
                logger.warning(f"Failed to warm up entry: {e}")

        logger.info(f"Warmed up cache with {added} entries")
        return added


# =============================================================================
# Singleton Instance
# =============================================================================

_cache_instance: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get or create the query cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = QueryCache()
    return _cache_instance


def set_query_cache(cache: QueryCache) -> None:
    """Set the query cache instance."""
    global _cache_instance
    _cache_instance = cache


__all__ = [
    "QueryCache",
    "CacheEntry",
    "CacheConfig",
    "CacheStats",
    "CacheEntryStatus",
    "get_query_cache",
    "set_query_cache",
]
