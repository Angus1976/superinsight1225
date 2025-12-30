"""
Performance Optimization Module for Knowledge Graph.

Provides caching, query optimization, batch processing, and performance monitoring.
"""

import asyncio
import functools
import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata."""
    value: T
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: Optional[int] = None

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds

    def access(self) -> T:
        """Access the entry and update metadata."""
        self.last_accessed = datetime.now()
        self.access_count += 1
        return self.value


class QueryCache:
    """
    LRU/TTL query cache for knowledge graph queries.

    Supports multiple eviction strategies and automatic cleanup.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl_seconds: int = 300,
        strategy: CacheStrategy = CacheStrategy.LRU,
        cleanup_interval_seconds: int = 60,
    ):
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.strategy = strategy
        self.cleanup_interval = cleanup_interval_seconds

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = CacheStats()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Query cache started")

    async def stop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Query cache stopped")

    def _generate_key(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key from query and parameters."""
        key_data = query
        if params:
            key_data += str(sorted(params.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Get cached result for query."""
        key = self._generate_key(query, params)

        async with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.expirations += 1
                return None

            # Update access for LRU
            if self.strategy == CacheStrategy.LRU:
                self._cache.move_to_end(key)

            self._stats.hits += 1
            return entry.access()

    async def set(
        self,
        query: str,
        result: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Cache query result."""
        key = self._generate_key(query, params)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds

        async with self._lock:
            # Evict if necessary
            if len(self._cache) >= self.max_size:
                await self._evict()

            self._cache[key] = CacheEntry(
                value=result,
                ttl_seconds=ttl,
            )
            self._stats.sets += 1

    async def invalidate(self, query: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Invalidate cached result."""
        key = self._generate_key(query, params)

        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.invalidations += 1
                return True
            return False

    async def clear(self) -> int:
        """Clear all cached entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.clears += 1
            return count

    async def _evict(self) -> None:
        """Evict entries based on strategy."""
        if not self._cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # Remove oldest (first) item
            self._cache.popitem(last=False)

        elif self.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            min_key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
            del self._cache[min_key]

        elif self.strategy == CacheStrategy.FIFO:
            # Remove first item
            self._cache.popitem(last=False)

        elif self.strategy == CacheStrategy.TTL:
            # Remove expired items first, then oldest
            expired = [k for k, v in self._cache.items() if v.is_expired()]
            if expired:
                del self._cache[expired[0]]
            else:
                self._cache.popitem(last=False)

        self._stats.evictions += 1

    async def _cleanup_loop(self) -> None:
        """Background cleanup of expired entries."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    async def _cleanup_expired(self) -> int:
        """Remove expired entries."""
        async with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired:
                del self._cache[key]

            if expired:
                self._stats.expirations += len(expired)
                logger.debug(f"Cleaned up {len(expired)} expired cache entries")

            return len(expired)

    def get_stats(self) -> 'CacheStats':
        """Get cache statistics."""
        self._stats.size = len(self._cache)
        self._stats.max_size = self.max_size
        return self._stats


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    expirations: int = 0
    invalidations: int = 0
    clears: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "invalidations": self.invalidations,
            "clears": self.clears,
            "size": self.size,
            "max_size": self.max_size,
            "hit_rate": self.hit_rate,
        }


@dataclass
class QueryMetrics:
    """Metrics for a single query execution."""
    query_hash: str
    query_template: str
    execution_time_ms: float
    result_count: int
    timestamp: datetime = field(default_factory=datetime.now)
    cache_hit: bool = False
    error: Optional[str] = None


class QueryPerformanceTracker:
    """
    Tracks query performance metrics for optimization.

    Collects execution times, identifies slow queries, and provides
    recommendations for optimization.
    """

    def __init__(
        self,
        slow_query_threshold_ms: float = 1000.0,
        max_history_size: int = 10000,
    ):
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.max_history_size = max_history_size

        self._history: List[QueryMetrics] = []
        self._query_stats: Dict[str, QueryStats] = {}
        self._lock = asyncio.Lock()

    async def record(self, metrics: QueryMetrics) -> None:
        """Record query metrics."""
        async with self._lock:
            # Add to history
            self._history.append(metrics)

            # Trim history if needed
            if len(self._history) > self.max_history_size:
                self._history = self._history[-self.max_history_size:]

            # Update aggregated stats
            if metrics.query_hash not in self._query_stats:
                self._query_stats[metrics.query_hash] = QueryStats(
                    query_template=metrics.query_template,
                )

            stats = self._query_stats[metrics.query_hash]
            stats.record_execution(
                execution_time_ms=metrics.execution_time_ms,
                result_count=metrics.result_count,
                cache_hit=metrics.cache_hit,
                error=metrics.error,
            )

            # Log slow queries
            if metrics.execution_time_ms > self.slow_query_threshold_ms:
                logger.warning(
                    f"Slow query detected: {metrics.execution_time_ms:.2f}ms "
                    f"(threshold: {self.slow_query_threshold_ms}ms)"
                )

    async def get_slow_queries(
        self,
        limit: int = 10,
        since: Optional[datetime] = None,
    ) -> List[QueryMetrics]:
        """Get slow queries."""
        async with self._lock:
            filtered = [
                m for m in self._history
                if m.execution_time_ms > self.slow_query_threshold_ms
                and (since is None or m.timestamp >= since)
            ]

            # Sort by execution time descending
            filtered.sort(key=lambda m: m.execution_time_ms, reverse=True)

            return filtered[:limit]

    async def get_query_stats(self) -> Dict[str, 'QueryStats']:
        """Get aggregated query statistics."""
        async with self._lock:
            return dict(self._query_stats)

    async def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        async with self._lock:
            if not self._history:
                return {"message": "No queries recorded"}

            total_queries = len(self._history)
            total_time = sum(m.execution_time_ms for m in self._history)
            avg_time = total_time / total_queries

            cache_hits = sum(1 for m in self._history if m.cache_hit)
            errors = sum(1 for m in self._history if m.error)
            slow_queries = sum(
                1 for m in self._history
                if m.execution_time_ms > self.slow_query_threshold_ms
            )

            return {
                "total_queries": total_queries,
                "total_time_ms": total_time,
                "avg_time_ms": avg_time,
                "cache_hits": cache_hits,
                "cache_hit_rate": cache_hits / total_queries,
                "errors": errors,
                "error_rate": errors / total_queries,
                "slow_queries": slow_queries,
                "slow_query_rate": slow_queries / total_queries,
                "unique_query_types": len(self._query_stats),
            }


@dataclass
class QueryStats:
    """Aggregated statistics for a query type."""
    query_template: str
    execution_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    cache_hits: int = 0
    error_count: int = 0
    total_results: int = 0

    @property
    def avg_time_ms(self) -> float:
        """Average execution time."""
        return self.total_time_ms / self.execution_count if self.execution_count > 0 else 0.0

    def record_execution(
        self,
        execution_time_ms: float,
        result_count: int,
        cache_hit: bool,
        error: Optional[str],
    ) -> None:
        """Record a query execution."""
        self.execution_count += 1
        self.total_time_ms += execution_time_ms
        self.min_time_ms = min(self.min_time_ms, execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, execution_time_ms)
        self.total_results += result_count

        if cache_hit:
            self.cache_hits += 1
        if error:
            self.error_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query_template": self.query_template,
            "execution_count": self.execution_count,
            "total_time_ms": self.total_time_ms,
            "avg_time_ms": self.avg_time_ms,
            "min_time_ms": self.min_time_ms if self.min_time_ms != float('inf') else 0.0,
            "max_time_ms": self.max_time_ms,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / self.execution_count if self.execution_count > 0 else 0.0,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.execution_count if self.execution_count > 0 else 0.0,
            "total_results": self.total_results,
            "avg_results": self.total_results / self.execution_count if self.execution_count > 0 else 0.0,
        }


class BatchProcessor:
    """
    Batch processor for efficient bulk operations.

    Accumulates operations and executes them in batches for
    better performance and reduced database load.
    """

    def __init__(
        self,
        batch_size: int = 100,
        flush_interval_seconds: float = 1.0,
        max_retries: int = 3,
    ):
        self.batch_size = batch_size
        self.flush_interval = flush_interval_seconds
        self.max_retries = max_retries

        self._pending: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._processor: Optional[Callable] = None
        self._stats = BatchStats()

    def set_processor(self, processor: Callable) -> None:
        """Set the batch processor function."""
        self._processor = processor

    async def start(self) -> None:
        """Start background flush task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info("Batch processor started")

    async def stop(self) -> None:
        """Stop and flush remaining items."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

        # Flush remaining items
        await self.flush()
        logger.info("Batch processor stopped")

    async def add(self, item: Dict[str, Any]) -> None:
        """Add item to batch."""
        async with self._lock:
            self._pending.append(item)
            self._stats.items_added += 1

            # Auto-flush if batch is full
            if len(self._pending) >= self.batch_size:
                await self._flush_batch()

    async def add_many(self, items: List[Dict[str, Any]]) -> None:
        """Add multiple items to batch."""
        for item in items:
            await self.add(item)

    async def flush(self) -> int:
        """Flush all pending items."""
        async with self._lock:
            return await self._flush_batch()

    async def _flush_batch(self) -> int:
        """Flush current batch (must hold lock)."""
        if not self._pending or not self._processor:
            return 0

        batch = self._pending[:self.batch_size]
        self._pending = self._pending[self.batch_size:]

        start_time = time.time()
        success = False

        for attempt in range(self.max_retries):
            try:
                await self._processor(batch)
                success = True
                break
            except Exception as e:
                logger.warning(f"Batch processing attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Batch processing failed after {self.max_retries} attempts")
                    self._stats.failed_batches += 1
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

        elapsed = (time.time() - start_time) * 1000

        if success:
            self._stats.successful_batches += 1
            self._stats.items_processed += len(batch)
            self._stats.total_processing_time_ms += elapsed

        return len(batch) if success else 0

    async def _flush_loop(self) -> None:
        """Background flush loop."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                if self._pending:
                    await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch flush error: {e}")

    def get_stats(self) -> 'BatchStats':
        """Get batch processing statistics."""
        self._stats.pending_items = len(self._pending)
        return self._stats


@dataclass
class BatchStats:
    """Batch processing statistics."""
    items_added: int = 0
    items_processed: int = 0
    successful_batches: int = 0
    failed_batches: int = 0
    total_processing_time_ms: float = 0.0
    pending_items: int = 0

    @property
    def avg_batch_time_ms(self) -> float:
        """Average batch processing time."""
        total = self.successful_batches + self.failed_batches
        return self.total_processing_time_ms / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "items_added": self.items_added,
            "items_processed": self.items_processed,
            "successful_batches": self.successful_batches,
            "failed_batches": self.failed_batches,
            "total_processing_time_ms": self.total_processing_time_ms,
            "avg_batch_time_ms": self.avg_batch_time_ms,
            "pending_items": self.pending_items,
        }


class ConnectionPoolMonitor:
    """
    Monitors database connection pool health and performance.
    """

    def __init__(self):
        self._metrics: List[PoolMetrics] = []
        self._max_history = 1000

    def record(
        self,
        active_connections: int,
        idle_connections: int,
        max_connections: int,
        wait_time_ms: float = 0.0,
    ) -> None:
        """Record pool metrics."""
        self._metrics.append(PoolMetrics(
            active_connections=active_connections,
            idle_connections=idle_connections,
            max_connections=max_connections,
            wait_time_ms=wait_time_ms,
        ))

        # Trim history
        if len(self._metrics) > self._max_history:
            self._metrics = self._metrics[-self._max_history:]

        # Check for pool exhaustion
        utilization = active_connections / max_connections if max_connections > 0 else 0
        if utilization > 0.9:
            logger.warning(
                f"Connection pool near exhaustion: {active_connections}/{max_connections} "
                f"({utilization:.1%})"
            )

    def get_current(self) -> Optional['PoolMetrics']:
        """Get current pool metrics."""
        return self._metrics[-1] if self._metrics else None

    def get_summary(self) -> Dict[str, Any]:
        """Get pool monitoring summary."""
        if not self._metrics:
            return {"message": "No metrics recorded"}

        recent = self._metrics[-100:]  # Last 100 samples

        avg_active = sum(m.active_connections for m in recent) / len(recent)
        avg_idle = sum(m.idle_connections for m in recent) / len(recent)
        avg_wait = sum(m.wait_time_ms for m in recent) / len(recent)
        max_active = max(m.active_connections for m in recent)
        max_wait = max(m.wait_time_ms for m in recent)

        return {
            "samples": len(recent),
            "avg_active_connections": avg_active,
            "avg_idle_connections": avg_idle,
            "avg_wait_time_ms": avg_wait,
            "max_active_connections": max_active,
            "max_wait_time_ms": max_wait,
            "current": self._metrics[-1].to_dict() if self._metrics else None,
        }


@dataclass
class PoolMetrics:
    """Connection pool metrics."""
    active_connections: int
    idle_connections: int
    max_connections: int
    wait_time_ms: float
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def utilization(self) -> float:
        """Pool utilization percentage."""
        return self.active_connections / self.max_connections if self.max_connections > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "max_connections": self.max_connections,
            "wait_time_ms": self.wait_time_ms,
            "utilization": self.utilization,
            "timestamp": self.timestamp.isoformat(),
        }


# Global instances
_query_cache: Optional[QueryCache] = None
_performance_tracker: Optional[QueryPerformanceTracker] = None
_batch_processor: Optional[BatchProcessor] = None
_pool_monitor: Optional[ConnectionPoolMonitor] = None


def get_query_cache() -> QueryCache:
    """Get global query cache instance."""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache


def get_performance_tracker() -> QueryPerformanceTracker:
    """Get global performance tracker instance."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = QueryPerformanceTracker()
    return _performance_tracker


def get_batch_processor() -> BatchProcessor:
    """Get global batch processor instance."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor


def get_pool_monitor() -> ConnectionPoolMonitor:
    """Get global pool monitor instance."""
    global _pool_monitor
    if _pool_monitor is None:
        _pool_monitor = ConnectionPoolMonitor()
    return _pool_monitor


def cached_query(ttl_seconds: int = 300):
    """Decorator for caching query results."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_query_cache()

            # Generate cache key
            key_parts = [func.__name__, str(args), str(sorted(kwargs.items()))]
            cache_key = hashlib.md5("".join(key_parts).encode()).hexdigest()

            # Try cache
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute and cache
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl_seconds=ttl_seconds)

            return result
        return wrapper
    return decorator


def tracked_query(query_name: str):
    """Decorator for tracking query performance."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracker = get_performance_tracker()

            start_time = time.time()
            error = None
            result_count = 0

            try:
                result = await func(*args, **kwargs)
                if isinstance(result, list):
                    result_count = len(result)
                elif hasattr(result, '__len__'):
                    result_count = len(result)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                execution_time = (time.time() - start_time) * 1000

                await tracker.record(QueryMetrics(
                    query_hash=hashlib.md5(query_name.encode()).hexdigest(),
                    query_template=query_name,
                    execution_time_ms=execution_time,
                    result_count=result_count,
                    error=error,
                ))
        return wrapper
    return decorator
