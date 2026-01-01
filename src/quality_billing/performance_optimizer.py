"""
Performance Optimizer for Quality-Billing Loop System

Provides caching, query optimization, and batch processing utilities
to improve system performance.
"""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


T = TypeVar("T")


# ============================================================================
# Caching System
# ============================================================================


class CacheEvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out


@dataclass
class CacheEntry(Generic[T]):
    """Entry in the cache"""
    key: str
    value: T
    created_at: datetime
    accessed_at: datetime
    access_count: int = 1
    ttl_seconds: Optional[int] = None

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl_seconds is None:
            return False
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    def touch(self) -> None:
        """Update access time and count"""
        self.accessed_at = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    current_size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class PerformanceCache(Generic[T]):
    """High-performance cache with multiple eviction policies"""

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[int] = None,
        eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.eviction_policy = eviction_policy
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=max_size)

    def get(self, key: str) -> Optional[T]:
        """Get value from cache"""
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            if entry.is_expired():
                self._evict(key)
                self._stats.misses += 1
                return None

            entry.touch()
            self._stats.hits += 1

            # Move to end for LRU
            if self.eviction_policy == CacheEvictionPolicy.LRU:
                self._cache.move_to_end(key)

            return entry.value

    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None
    ) -> None:
        """Set value in cache"""
        with self._lock:
            # Evict if necessary
            while len(self._cache) >= self.max_size:
                self._evict_one()

            now = datetime.now()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                accessed_at=now,
                ttl_seconds=ttl or self.default_ttl
            )

            self._cache[key] = entry
            self._stats.current_size = len(self._cache)

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.current_size = len(self._cache)
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache"""
        with self._lock:
            self._cache.clear()
            self._stats.current_size = 0

    def _evict(self, key: str) -> None:
        """Evict specific key"""
        if key in self._cache:
            del self._cache[key]
            self._stats.evictions += 1
            self._stats.current_size = len(self._cache)

    def _evict_one(self) -> None:
        """Evict one entry based on policy"""
        if not self._cache:
            return

        if self.eviction_policy == CacheEvictionPolicy.LRU:
            # Evict least recently used (first in OrderedDict)
            key = next(iter(self._cache))
        elif self.eviction_policy == CacheEvictionPolicy.LFU:
            # Evict least frequently used
            key = min(self._cache.keys(), key=lambda k: self._cache[k].access_count)
        elif self.eviction_policy == CacheEvictionPolicy.TTL:
            # Evict oldest entry
            key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        elif self.eviction_policy == CacheEvictionPolicy.FIFO:
            # Evict first inserted
            key = next(iter(self._cache))
        else:
            key = next(iter(self._cache))

        self._evict(key)

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                current_size=len(self._cache),
                max_size=self.max_size
            )


def cached(
    cache: PerformanceCache,
    key_prefix: str = "",
    ttl: Optional[int] = None
) -> Callable:
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper
    return decorator


# ============================================================================
# Query Optimizer
# ============================================================================


@dataclass
class QueryPlan:
    """Execution plan for a query"""
    query_id: str
    original_query: str
    optimized_query: str
    estimated_cost: float
    indexes_used: List[str]
    suggestions: List[str]


@dataclass
class QueryStats:
    """Statistics for query execution"""
    query_id: str
    execution_count: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    max_time_ms: float = 0.0
    min_time_ms: float = float("inf")


class QueryOptimizer:
    """Optimizes and analyzes database queries"""

    def __init__(self):
        self._query_stats: Dict[str, QueryStats] = {}
        self._slow_query_threshold_ms = 100.0
        self._suggested_indexes: Set[str] = set()
        self._lock = threading.Lock()

    def analyze_query(self, query: str, table_name: str) -> QueryPlan:
        """Analyze a query and suggest optimizations"""
        query_id = hashlib.md5(query.encode()).hexdigest()[:8]
        suggestions = []
        indexes_used = []

        # Check for common optimization opportunities
        query_lower = query.lower()

        # Check for SELECT *
        if "select *" in query_lower:
            suggestions.append("Avoid SELECT * - specify only needed columns")

        # Check for missing WHERE clause
        if "where" not in query_lower and ("select" in query_lower or "update" in query_lower):
            suggestions.append("Consider adding WHERE clause to limit results")

        # Check for LIKE with leading wildcard
        if "like '%" in query_lower:
            suggestions.append("Leading wildcard in LIKE prevents index usage")

        # Check for ORDER BY without index hint
        if "order by" in query_lower:
            suggestions.append(f"Consider adding index on ORDER BY column for {table_name}")

        # Check for GROUP BY
        if "group by" in query_lower:
            suggestions.append(f"Consider adding index on GROUP BY columns for {table_name}")

        # Detect potential indexes
        if "where" in query_lower:
            where_pos = query_lower.find("where")
            where_clause = query[where_pos:].split("order")[0].split("group")[0]
            # Simple extraction of column names
            for word in where_clause.replace("=", " ").replace(">", " ").replace("<", " ").split():
                if word.isidentifier() and word not in ("where", "and", "or", "not", "in", "like"):
                    index_suggestion = f"{table_name}_{word}_idx"
                    self._suggested_indexes.add(index_suggestion)
                    indexes_used.append(index_suggestion)

        return QueryPlan(
            query_id=query_id,
            original_query=query,
            optimized_query=query,  # In real implementation, would rewrite query
            estimated_cost=1.0,
            indexes_used=indexes_used,
            suggestions=suggestions
        )

    def record_execution(self, query: str, execution_time_ms: float) -> None:
        """Record query execution time for analysis"""
        query_id = hashlib.md5(query.encode()).hexdigest()[:8]

        with self._lock:
            if query_id not in self._query_stats:
                self._query_stats[query_id] = QueryStats(query_id=query_id)

            stats = self._query_stats[query_id]
            stats.execution_count += 1
            stats.total_time_ms += execution_time_ms
            stats.avg_time_ms = stats.total_time_ms / stats.execution_count
            stats.max_time_ms = max(stats.max_time_ms, execution_time_ms)
            stats.min_time_ms = min(stats.min_time_ms, execution_time_ms)

    def get_slow_queries(self) -> List[QueryStats]:
        """Get queries that exceed the slow query threshold"""
        with self._lock:
            return [
                stats for stats in self._query_stats.values()
                if stats.avg_time_ms > self._slow_query_threshold_ms
            ]

    def get_suggested_indexes(self) -> List[str]:
        """Get list of suggested indexes"""
        return list(self._suggested_indexes)

    def get_query_stats(self, query: str) -> Optional[QueryStats]:
        """Get statistics for a specific query"""
        query_id = hashlib.md5(query.encode()).hexdigest()[:8]
        return self._query_stats.get(query_id)


# ============================================================================
# Batch Processor
# ============================================================================


@dataclass
class BatchResult(Generic[T]):
    """Result of batch processing"""
    batch_id: str
    total_items: int
    processed_items: int
    failed_items: int
    results: List[T]
    errors: List[Tuple[int, str]]
    processing_time_ms: float


class BatchProcessor(Generic[T]):
    """Efficient batch processing with parallelism"""

    def __init__(
        self,
        batch_size: int = 100,
        max_workers: int = 4,
        retry_count: int = 3,
        retry_delay_seconds: float = 1.0
    ):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.retry_count = retry_count
        self.retry_delay_seconds = retry_delay_seconds
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def process_batch(
        self,
        items: List[Any],
        processor: Callable[[Any], T],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> BatchResult[T]:
        """Process items in batches"""
        batch_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        start_time = time.time()

        results: List[T] = []
        errors: List[Tuple[int, str]] = []
        processed_count = 0

        # Split into batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

        for batch_idx, batch in enumerate(batches):
            batch_results = self._process_single_batch(batch, processor)

            for idx, (success, result, error) in enumerate(batch_results):
                global_idx = batch_idx * self.batch_size + idx
                if success:
                    results.append(result)
                    processed_count += 1
                else:
                    errors.append((global_idx, error))

            if on_progress:
                on_progress(processed_count, len(items))

        processing_time_ms = (time.time() - start_time) * 1000

        return BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            processed_items=processed_count,
            failed_items=len(errors),
            results=results,
            errors=errors,
            processing_time_ms=processing_time_ms
        )

    def _process_single_batch(
        self,
        batch: List[Any],
        processor: Callable[[Any], T]
    ) -> List[Tuple[bool, Optional[T], str]]:
        """Process a single batch with parallel execution"""
        results: List[Tuple[bool, Optional[T], str]] = []
        futures = {}

        for idx, item in enumerate(batch):
            future = self._executor.submit(
                self._process_with_retry, item, processor
            )
            futures[future] = idx

        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                results.append((True, result, ""))
            except Exception as e:
                results.append((False, None, str(e)))

        # Sort by original order
        results.sort(key=lambda x: futures.get(x, 0))
        return results

    def _process_with_retry(
        self,
        item: Any,
        processor: Callable[[Any], T]
    ) -> T:
        """Process item with retry logic"""
        last_error = None

        for attempt in range(self.retry_count):
            try:
                return processor(item)
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay_seconds * (attempt + 1))

        raise last_error or Exception("Processing failed")

    async def process_batch_async(
        self,
        items: List[Any],
        processor: Callable[[Any], T],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> BatchResult[T]:
        """Async version of batch processing"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.process_batch(items, processor, on_progress)
        )

    def shutdown(self) -> None:
        """Shutdown the executor"""
        self._executor.shutdown(wait=True)


# ============================================================================
# Performance Monitor
# ============================================================================


@dataclass
class PerformanceMetric:
    """Single performance metric"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceSummary:
    """Summary of performance metrics"""
    period_start: datetime
    period_end: datetime
    metrics: Dict[str, Dict[str, float]]  # name -> {avg, min, max, count}


class PerformanceMonitor:
    """Monitors and tracks system performance"""

    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self._metrics: List[PerformanceMetric] = []
        self._lock = threading.Lock()

    def record(
        self,
        name: str,
        value: float,
        unit: str = "ms",
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            tags=tags or {}
        )

        with self._lock:
            self._metrics.append(metric)
            self._cleanup_old_metrics()

    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period"""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        self._metrics = [m for m in self._metrics if m.timestamp > cutoff]

    def get_summary(
        self,
        period_minutes: int = 60,
        metric_names: Optional[List[str]] = None
    ) -> PerformanceSummary:
        """Get performance summary for the specified period"""
        period_end = datetime.now()
        period_start = period_end - timedelta(minutes=period_minutes)

        with self._lock:
            relevant_metrics = [
                m for m in self._metrics
                if m.timestamp >= period_start
                and (metric_names is None or m.name in metric_names)
            ]

        # Group by metric name
        grouped: Dict[str, List[float]] = {}
        for metric in relevant_metrics:
            if metric.name not in grouped:
                grouped[metric.name] = []
            grouped[metric.name].append(metric.value)

        # Calculate statistics
        metrics_summary: Dict[str, Dict[str, float]] = {}
        for name, values in grouped.items():
            if values:
                metrics_summary[name] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }

        return PerformanceSummary(
            period_start=period_start,
            period_end=period_end,
            metrics=metrics_summary
        )

    def get_recent_metrics(
        self,
        name: str,
        count: int = 100
    ) -> List[PerformanceMetric]:
        """Get recent metrics by name"""
        with self._lock:
            matching = [m for m in self._metrics if m.name == name]
            return matching[-count:]


def timed(monitor: PerformanceMonitor, metric_name: str) -> Callable:
    """Decorator to time function execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                monitor.record(metric_name, elapsed_ms, "ms")

        return wrapper
    return decorator


# ============================================================================
# Connection Pool Manager
# ============================================================================


@dataclass
class PooledConnection:
    """A pooled connection wrapper"""
    connection: Any
    created_at: datetime
    last_used_at: datetime
    in_use: bool = False

    def is_stale(self, max_age_seconds: int) -> bool:
        """Check if connection is stale"""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > max_age_seconds


class ConnectionPool:
    """Generic connection pool manager"""

    def __init__(
        self,
        factory: Callable[[], Any],
        min_size: int = 2,
        max_size: int = 10,
        max_age_seconds: int = 3600
    ):
        self.factory = factory
        self.min_size = min_size
        self.max_size = max_size
        self.max_age_seconds = max_age_seconds
        self._pool: List[PooledConnection] = []
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the connection pool"""
        with self._lock:
            if self._initialized:
                return

            for _ in range(self.min_size):
                self._create_connection()

            self._initialized = True

    def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection"""
        now = datetime.now()
        conn = PooledConnection(
            connection=self.factory(),
            created_at=now,
            last_used_at=now
        )
        self._pool.append(conn)
        return conn

    def acquire(self) -> Any:
        """Acquire a connection from the pool"""
        with self._lock:
            # Find available connection
            for pooled_conn in self._pool:
                if not pooled_conn.in_use and not pooled_conn.is_stale(self.max_age_seconds):
                    pooled_conn.in_use = True
                    pooled_conn.last_used_at = datetime.now()
                    return pooled_conn.connection

            # Create new connection if under max
            if len(self._pool) < self.max_size:
                pooled_conn = self._create_connection()
                pooled_conn.in_use = True
                return pooled_conn.connection

            # Wait for available connection
            raise RuntimeError("Connection pool exhausted")

    def release(self, connection: Any) -> None:
        """Release a connection back to the pool"""
        with self._lock:
            for pooled_conn in self._pool:
                if pooled_conn.connection is connection:
                    pooled_conn.in_use = False
                    pooled_conn.last_used_at = datetime.now()
                    return

    def cleanup(self) -> None:
        """Remove stale connections and maintain minimum pool size"""
        with self._lock:
            # Remove stale unused connections
            self._pool = [
                pc for pc in self._pool
                if pc.in_use or not pc.is_stale(self.max_age_seconds)
            ]

            # Maintain minimum size
            while len(self._pool) < self.min_size:
                self._create_connection()

    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics"""
        with self._lock:
            in_use = sum(1 for pc in self._pool if pc.in_use)
            return {
                "total": len(self._pool),
                "in_use": in_use,
                "available": len(self._pool) - in_use,
                "max_size": self.max_size
            }

    def shutdown(self) -> None:
        """Shutdown the pool and close all connections"""
        with self._lock:
            for pooled_conn in self._pool:
                try:
                    if hasattr(pooled_conn.connection, "close"):
                        pooled_conn.connection.close()
                except Exception:
                    pass
            self._pool.clear()
            self._initialized = False


# ============================================================================
# Preloader for Frequently Accessed Data
# ============================================================================


class DataPreloader:
    """Preloads frequently accessed data into cache"""

    def __init__(self, cache: PerformanceCache):
        self.cache = cache
        self._preload_tasks: Dict[str, Callable[[], Any]] = {}
        self._preload_schedule: Dict[str, int] = {}  # key -> refresh interval seconds
        self._last_preload: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register(
        self,
        key: str,
        loader: Callable[[], Any],
        refresh_interval_seconds: int = 300
    ) -> None:
        """Register a preload task"""
        with self._lock:
            self._preload_tasks[key] = loader
            self._preload_schedule[key] = refresh_interval_seconds

    def unregister(self, key: str) -> None:
        """Unregister a preload task"""
        with self._lock:
            self._preload_tasks.pop(key, None)
            self._preload_schedule.pop(key, None)
            self._last_preload.pop(key, None)

    def preload_all(self) -> Dict[str, bool]:
        """Preload all registered data"""
        results = {}

        with self._lock:
            tasks = dict(self._preload_tasks)

        for key, loader in tasks.items():
            try:
                data = loader()
                self.cache.set(key, data)
                self._last_preload[key] = datetime.now()
                results[key] = True
            except Exception:
                results[key] = False

        return results

    def start_background_refresh(self, check_interval_seconds: int = 60) -> None:
        """Start background refresh thread"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._refresh_loop,
            args=(check_interval_seconds,),
            daemon=True
        )
        self._thread.start()

    def stop_background_refresh(self) -> None:
        """Stop background refresh"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _refresh_loop(self, check_interval: int) -> None:
        """Background refresh loop"""
        while self._running:
            now = datetime.now()

            with self._lock:
                tasks = dict(self._preload_tasks)
                schedules = dict(self._preload_schedule)
                last_preloads = dict(self._last_preload)

            for key, loader in tasks.items():
                interval = schedules.get(key, 300)
                last = last_preloads.get(key)

                if last is None or (now - last).total_seconds() > interval:
                    try:
                        data = loader()
                        self.cache.set(key, data)
                        with self._lock:
                            self._last_preload[key] = now
                    except Exception:
                        pass

            time.sleep(check_interval)


# ============================================================================
# Rate Limiter
# ============================================================================


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after_seconds: Optional[float] = None


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int = 20
    ):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self._tokens: Dict[str, float] = {}
        self._last_update: Dict[str, datetime] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> RateLimitResult:
        """Check if request is allowed under rate limit"""
        now = datetime.now()

        with self._lock:
            # Initialize if new key
            if key not in self._tokens:
                self._tokens[key] = float(self.burst_size)
                self._last_update[key] = now

            # Refill tokens
            last_update = self._last_update[key]
            elapsed = (now - last_update).total_seconds()
            refill = elapsed * self.requests_per_second

            self._tokens[key] = min(
                self.burst_size,
                self._tokens[key] + refill
            )
            self._last_update[key] = now

            # Check if request is allowed
            if self._tokens[key] >= 1.0:
                self._tokens[key] -= 1.0
                return RateLimitResult(
                    allowed=True,
                    remaining=int(self._tokens[key]),
                    reset_at=now + timedelta(seconds=1 / self.requests_per_second)
                )
            else:
                retry_after = (1.0 - self._tokens[key]) / self.requests_per_second
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=now + timedelta(seconds=retry_after),
                    retry_after_seconds=retry_after
                )

    def reset(self, key: str) -> None:
        """Reset rate limit for a key"""
        with self._lock:
            self._tokens[key] = float(self.burst_size)
            self._last_update[key] = datetime.now()


def rate_limited(
    limiter: RateLimiter,
    key_func: Optional[Callable[..., str]] = None
) -> Callable:
    """Decorator for rate limiting"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = func.__name__

            result = limiter.check(key)

            if not result.allowed:
                raise RuntimeError(
                    f"Rate limit exceeded. Retry after {result.retry_after_seconds:.2f} seconds"
                )

            return func(*args, **kwargs)

        return wrapper
    return decorator
