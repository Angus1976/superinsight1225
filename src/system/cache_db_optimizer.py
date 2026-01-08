"""
Cache and Database Optimization for SuperInsight Platform.

Provides comprehensive optimization including:
- Intelligent caching strategies with adaptive TTL and cache warming
- Database query optimization with index recommendations
- Connection pool management and optimization
- Data access performance monitoring and analysis
- Cache hit rate optimization and cache eviction policies
"""

import asyncio
import logging
import time
import hashlib
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
import statistics
from contextlib import asynccontextmanager
import weakref

# Optional dependencies
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import psycopg2
    from psycopg2 import pool
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

from src.config.settings import settings


logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    cache_name: str
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    avg_response_time: float = 0.0
    total_size_bytes: int = 0
    evictions: int = 0
    errors: int = 0
    last_updated: float = field(default_factory=time.time)
    
    def update_hit(self, response_time: float):
        """Update metrics for cache hit."""
        self.total_requests += 1
        self.cache_hits += 1
        self.hit_rate = self.cache_hits / self.total_requests
        self._update_avg_response_time(response_time)
    
    def update_miss(self, response_time: float):
        """Update metrics for cache miss."""
        self.total_requests += 1
        self.cache_misses += 1
        self.hit_rate = self.cache_hits / self.total_requests
        self._update_avg_response_time(response_time)
    
    def _update_avg_response_time(self, response_time: float):
        """Update average response time."""
        if self.total_requests == 1:
            self.avg_response_time = response_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.avg_response_time = alpha * response_time + (1 - alpha) * self.avg_response_time
        
        self.last_updated = time.time()


@dataclass
class DatabaseMetrics:
    """Database performance metrics."""
    connection_pool_name: str
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    slow_queries: int = 0
    active_connections: int = 0
    max_connections: int = 0
    connection_wait_time: float = 0.0
    deadlocks: int = 0
    last_updated: float = field(default_factory=time.time)
    
    def update_query(self, query_time: float, success: bool, slow_threshold: float = 1.0):
        """Update metrics for database query."""
        self.total_queries += 1
        
        if success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1
        
        if query_time > slow_threshold:
            self.slow_queries += 1
        
        # Update average query time
        if self.total_queries == 1:
            self.avg_query_time = query_time
        else:
            alpha = 0.1
            self.avg_query_time = alpha * query_time + (1 - alpha) * self.avg_query_time
        
        self.last_updated = time.time()


@dataclass
class QueryOptimizationSuggestion:
    """Database query optimization suggestion."""
    query_pattern: str
    issue_type: str  # slow_execution, missing_index, inefficient_join, etc.
    severity: str    # low, medium, high, critical
    description: str
    recommendations: List[str]
    estimated_improvement: str
    implementation_effort: str  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query_pattern": self.query_pattern,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "recommendations": self.recommendations,
            "estimated_improvement": self.estimated_improvement,
            "implementation_effort": self.implementation_effort
        }


class IntelligentCache:
    """
    Intelligent caching system with adaptive strategies.
    
    Features:
    - Adaptive TTL based on access patterns
    - Cache warming for frequently accessed data
    - Intelligent eviction policies
    - Performance monitoring and optimization
    """
    
    def __init__(
        self,
        name: str,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        max_memory_mb: int = 100
    ):
        self.name = name
        self.default_ttl = default_ttl
        self.max_memory_mb = max_memory_mb
        self.metrics = CacheMetrics(cache_name=name)
        
        # Access pattern tracking
        self.access_patterns: Dict[str, List[float]] = defaultdict(list)
        self.key_popularity: Dict[str, int] = defaultdict(int)
        self.adaptive_ttls: Dict[str, int] = {}
        
        # Initialize cache backend
        if redis_url and REDIS_AVAILABLE:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                self.redis_client.ping()
                self.backend = "redis"
                logger.info(f"Cache '{name}' using Redis backend")
            except Exception as e:
                logger.warning(f"Redis connection failed for cache '{name}': {e}")
                self._init_memory_cache()
        else:
            self._init_memory_cache()
        
        self._lock = threading.Lock()
    
    def _init_memory_cache(self):
        """Initialize in-memory cache backend."""
        self.memory_cache: Dict[str, Tuple[Any, float, float]] = {}  # key -> (value, expiry, access_time)
        self.backend = "memory"
        logger.info(f"Cache '{self.name}' using memory backend")
    
    def _generate_cache_key(self, key: str, namespace: str = "") -> str:
        """Generate cache key with namespace."""
        if namespace:
            return f"{self.name}:{namespace}:{key}"
        return f"{self.name}:{key}"
    
    async def get(self, key: str, namespace: str = "") -> Optional[Any]:
        """Get value from cache with performance tracking."""
        start_time = time.time()
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            if self.backend == "redis":
                value = await self._redis_get(cache_key)
            else:
                value = self._memory_get(cache_key)
            
            response_time = time.time() - start_time
            
            if value is not None:
                self.metrics.update_hit(response_time)
                self._update_access_pattern(cache_key)
                return value
            else:
                self.metrics.update_miss(response_time)
                return None
        
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache get error for key '{cache_key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = ""
    ) -> bool:
        """Set value in cache with adaptive TTL."""
        cache_key = self._generate_cache_key(key, namespace)
        
        # Determine TTL (adaptive or default)
        if ttl is None:
            ttl = self._get_adaptive_ttl(cache_key)
        
        try:
            if self.backend == "redis":
                success = await self._redis_set(cache_key, value, ttl)
            else:
                success = self._memory_set(cache_key, value, ttl)
            
            if success:
                self._update_popularity(cache_key)
            
            return success
        
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache set error for key '{cache_key}': {e}")
            return False
    
    async def delete(self, key: str, namespace: str = "") -> bool:
        """Delete value from cache."""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            if self.backend == "redis":
                return await self._redis_delete(cache_key)
            else:
                return self._memory_delete(cache_key)
        
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache delete error for key '{cache_key}': {e}")
            return False
    
    async def warm_cache(self, warm_func: Callable, keys: List[str], namespace: str = ""):
        """Warm cache with frequently accessed data."""
        logger.info(f"Warming cache '{self.name}' with {len(keys)} keys")
        
        for key in keys:
            try:
                cache_key = self._generate_cache_key(key, namespace)
                
                # Check if already cached
                if await self.get(key, namespace) is not None:
                    continue
                
                # Generate and cache value
                value = await warm_func(key)
                if value is not None:
                    await self.set(key, value, namespace=namespace)
            
            except Exception as e:
                logger.error(f"Cache warming error for key '{key}': {e}")
    
    def _get_adaptive_ttl(self, cache_key: str) -> int:
        """Calculate adaptive TTL based on access patterns."""
        if cache_key in self.adaptive_ttls:
            return self.adaptive_ttls[cache_key]
        
        # Base TTL on popularity and access frequency
        popularity = self.key_popularity.get(cache_key, 0)
        
        if popularity > 100:  # Very popular
            ttl = self.default_ttl * 2
        elif popularity > 50:  # Popular
            ttl = int(self.default_ttl * 1.5)
        elif popularity > 10:  # Moderately popular
            ttl = self.default_ttl
        else:  # Low popularity
            ttl = int(self.default_ttl * 0.5)
        
        self.adaptive_ttls[cache_key] = ttl
        return ttl
    
    def _update_access_pattern(self, cache_key: str):
        """Update access pattern for key."""
        current_time = time.time()
        
        with self._lock:
            self.access_patterns[cache_key].append(current_time)
            
            # Keep only recent access times (last 1000)
            if len(self.access_patterns[cache_key]) > 1000:
                self.access_patterns[cache_key] = self.access_patterns[cache_key][-1000:]
    
    def _update_popularity(self, cache_key: str):
        """Update key popularity score."""
        with self._lock:
            self.key_popularity[cache_key] += 1
    
    # Redis backend methods
    async def _redis_get(self, cache_key: str) -> Optional[Any]:
        """Get value from Redis."""
        try:
            import pickle
            data = self.redis_client.get(cache_key)
            return pickle.loads(data) if data else None
        except Exception:
            return None
    
    async def _redis_set(self, cache_key: str, value: Any, ttl: int) -> bool:
        """Set value in Redis."""
        try:
            import pickle
            data = pickle.dumps(value)
            return self.redis_client.setex(cache_key, ttl, data)
        except Exception:
            return False
    
    async def _redis_delete(self, cache_key: str) -> bool:
        """Delete value from Redis."""
        try:
            return bool(self.redis_client.delete(cache_key))
        except Exception:
            return False
    
    # Memory backend methods
    def _memory_get(self, cache_key: str) -> Optional[Any]:
        """Get value from memory cache."""
        with self._lock:
            if cache_key in self.memory_cache:
                value, expiry, _ = self.memory_cache[cache_key]
                
                if time.time() < expiry:
                    # Update access time
                    self.memory_cache[cache_key] = (value, expiry, time.time())
                    return value
                else:
                    # Expired, remove
                    del self.memory_cache[cache_key]
                    self.metrics.evictions += 1
            
            return None
    
    def _memory_set(self, cache_key: str, value: Any, ttl: int) -> bool:
        """Set value in memory cache."""
        expiry = time.time() + ttl
        
        with self._lock:
            # Check memory usage and evict if necessary
            self._evict_if_needed()
            
            self.memory_cache[cache_key] = (value, expiry, time.time())
            return True
    
    def _memory_delete(self, cache_key: str) -> bool:
        """Delete value from memory cache."""
        with self._lock:
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
                return True
            return False
    
    def _evict_if_needed(self):
        """Evict least recently used items if memory limit exceeded."""
        # Simple LRU eviction based on access time
        if len(self.memory_cache) > 1000:  # Simple size limit
            # Sort by access time and remove oldest
            sorted_items = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1][2]  # Sort by access time
            )
            
            # Remove oldest 10%
            to_remove = len(sorted_items) // 10
            for i in range(to_remove):
                key = sorted_items[i][0]
                del self.memory_cache[key]
                self.metrics.evictions += 1
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self._lock:
            # Calculate additional metrics
            popular_keys = sorted(
                self.key_popularity.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            access_frequency = {}
            for key, access_times in self.access_patterns.items():
                if len(access_times) > 1:
                    # Calculate access frequency (accesses per hour)
                    time_span = access_times[-1] - access_times[0]
                    if time_span > 0:
                        frequency = len(access_times) / (time_span / 3600)
                        access_frequency[key] = frequency
            
            return {
                "cache_name": self.name,
                "backend": self.backend,
                "total_requests": self.metrics.total_requests,
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "hit_rate": self.metrics.hit_rate,
                "avg_response_time": self.metrics.avg_response_time,
                "evictions": self.metrics.evictions,
                "errors": self.metrics.errors,
                "popular_keys": popular_keys,
                "high_frequency_keys": sorted(
                    access_frequency.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10],
                "adaptive_ttl_count": len(self.adaptive_ttls),
                "memory_cache_size": len(self.memory_cache) if self.backend == "memory" else None
            }


class DatabaseConnectionPool:
    """
    Optimized database connection pool with monitoring.
    
    Features:
    - Connection pool optimization
    - Query performance monitoring
    - Automatic query optimization suggestions
    - Deadlock detection and handling
    """
    
    def __init__(
        self,
        name: str,
        database_url: str,
        min_connections: int = 5,
        max_connections: int = 20
    ):
        self.name = name
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.metrics = DatabaseMetrics(
            connection_pool_name=name,
            max_connections=max_connections
        )
        
        # Query analysis
        self.query_patterns: Dict[str, List[float]] = defaultdict(list)
        self.slow_queries: List[Dict[str, Any]] = []
        self.optimization_suggestions: List[QueryOptimizationSuggestion] = []
        
        # Initialize connection pool
        self.pool = None
        self._lock = threading.Lock()
        
        if POSTGRES_AVAILABLE:
            self._init_postgres_pool()
        else:
            logger.warning(f"PostgreSQL not available for pool '{name}'")
    
    def _init_postgres_pool(self):
        """Initialize PostgreSQL connection pool."""
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                self.min_connections,
                self.max_connections,
                self.database_url
            )
            logger.info(f"Database pool '{self.name}' initialized with {self.min_connections}-{self.max_connections} connections")
        except Exception as e:
            logger.error(f"Failed to initialize database pool '{self.name}': {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool with monitoring."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        start_time = time.time()
        connection = None
        
        try:
            connection = self.pool.getconn()
            wait_time = time.time() - start_time
            
            with self._lock:
                self.metrics.active_connections += 1
                if wait_time > 0.1:  # Log slow connection acquisition
                    self.metrics.connection_wait_time = wait_time
            
            yield connection
        
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        
        finally:
            if connection:
                self.pool.putconn(connection)
                with self._lock:
                    self.metrics.active_connections -= 1
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: bool = True
    ) -> Optional[List[Tuple]]:
        """Execute query with performance monitoring."""
        start_time = time.time()
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        
        try:
            async with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    
                    result = None
                    if fetch:
                        result = cursor.fetchall()
                    
                    conn.commit()
                    
                    query_time = time.time() - start_time
                    self.metrics.update_query(query_time, True)
                    
                    # Track query patterns
                    self._analyze_query_performance(query, query_time, query_hash)
                    
                    return result
        
        except Exception as e:
            query_time = time.time() - start_time
            self.metrics.update_query(query_time, False)
            
            # Check for deadlock
            if "deadlock" in str(e).lower():
                self.metrics.deadlocks += 1
            
            logger.error(f"Query execution failed: {e}")
            raise
    
    def _analyze_query_performance(self, query: str, query_time: float, query_hash: str):
        """Analyze query performance and generate optimization suggestions."""
        with self._lock:
            self.query_patterns[query_hash].append(query_time)
            
            # Keep only recent query times
            if len(self.query_patterns[query_hash]) > 100:
                self.query_patterns[query_hash] = self.query_patterns[query_hash][-100:]
            
            # Check for slow queries
            if query_time > 1.0:  # Slow query threshold
                slow_query = {
                    "query": query[:200] + "..." if len(query) > 200 else query,
                    "query_hash": query_hash,
                    "execution_time": query_time,
                    "timestamp": time.time()
                }
                
                self.slow_queries.append(slow_query)
                
                # Keep only recent slow queries
                if len(self.slow_queries) > 100:
                    self.slow_queries = self.slow_queries[-100:]
                
                # Generate optimization suggestion
                suggestion = self._generate_optimization_suggestion(query, query_time)
                if suggestion:
                    self.optimization_suggestions.append(suggestion)
    
    def _generate_optimization_suggestion(self, query: str, query_time: float) -> Optional[QueryOptimizationSuggestion]:
        """Generate query optimization suggestion."""
        query_lower = query.lower().strip()
        
        # Detect common optimization opportunities
        if "select *" in query_lower:
            return QueryOptimizationSuggestion(
                query_pattern=query[:100] + "...",
                issue_type="inefficient_select",
                severity="medium",
                description="Query uses SELECT * which may fetch unnecessary columns",
                recommendations=[
                    "Specify only required columns in SELECT clause",
                    "Consider creating a view for commonly used column sets",
                    "Use column aliases for better readability"
                ],
                estimated_improvement="10-30% performance improvement",
                implementation_effort="low"
            )
        
        elif "where" not in query_lower and "select" in query_lower:
            return QueryOptimizationSuggestion(
                query_pattern=query[:100] + "...",
                issue_type="missing_where_clause",
                severity="high",
                description="Query lacks WHERE clause, potentially scanning entire table",
                recommendations=[
                    "Add appropriate WHERE clause to filter results",
                    "Consider adding LIMIT clause if full table scan is intended",
                    "Review if this query is necessary"
                ],
                estimated_improvement="50-90% performance improvement",
                implementation_effort="medium"
            )
        
        elif query_time > 5.0:
            return QueryOptimizationSuggestion(
                query_pattern=query[:100] + "...",
                issue_type="very_slow_query",
                severity="critical",
                description=f"Query execution time ({query_time:.2f}s) is extremely slow",
                recommendations=[
                    "Analyze query execution plan with EXPLAIN",
                    "Check for missing indexes on WHERE/JOIN columns",
                    "Consider query rewriting or breaking into smaller queries",
                    "Review table statistics and consider ANALYZE"
                ],
                estimated_improvement="Significant performance improvement possible",
                implementation_effort="high"
            )
        
        elif "join" in query_lower and query_time > 2.0:
            return QueryOptimizationSuggestion(
                query_pattern=query[:100] + "...",
                issue_type="slow_join",
                severity="high",
                description="JOIN operation is slow, possibly due to missing indexes",
                recommendations=[
                    "Ensure indexes exist on JOIN columns",
                    "Consider using INNER JOIN instead of WHERE for better performance",
                    "Review JOIN order and consider query hints",
                    "Check for proper foreign key relationships"
                ],
                estimated_improvement="30-70% performance improvement",
                implementation_effort="medium"
            )
        
        return None
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics."""
        with self._lock:
            # Calculate query performance statistics
            all_query_times = []
            for times in self.query_patterns.values():
                all_query_times.extend(times)
            
            avg_query_time = statistics.mean(all_query_times) if all_query_times else 0
            p95_query_time = statistics.quantiles(all_query_times, n=20)[18] if len(all_query_times) > 20 else 0
            
            return {
                "pool_name": self.name,
                "min_connections": self.min_connections,
                "max_connections": self.max_connections,
                "active_connections": self.metrics.active_connections,
                "total_queries": self.metrics.total_queries,
                "successful_queries": self.metrics.successful_queries,
                "failed_queries": self.metrics.failed_queries,
                "success_rate": self.metrics.successful_queries / self.metrics.total_queries if self.metrics.total_queries > 0 else 0,
                "avg_query_time": avg_query_time,
                "p95_query_time": p95_query_time,
                "slow_queries_count": self.metrics.slow_queries,
                "deadlocks": self.metrics.deadlocks,
                "connection_wait_time": self.metrics.connection_wait_time,
                "recent_slow_queries": self.slow_queries[-10:],
                "optimization_suggestions": [s.to_dict() for s in self.optimization_suggestions[-10:]]
            }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get database optimization recommendations."""
        recommendations = []
        
        # Connection pool recommendations
        if self.metrics.connection_wait_time > 0.5:
            recommendations.append({
                "category": "connection_pool",
                "priority": "high",
                "title": "Increase connection pool size",
                "description": f"Connection wait time is {self.metrics.connection_wait_time:.2f}s",
                "recommendation": f"Consider increasing max_connections from {self.max_connections} to {self.max_connections + 5}"
            })
        
        # Query performance recommendations
        if self.metrics.slow_queries > 10:
            recommendations.append({
                "category": "query_performance",
                "priority": "high",
                "title": "Optimize slow queries",
                "description": f"Found {self.metrics.slow_queries} slow queries",
                "recommendation": "Review and optimize queries taking more than 1 second"
            })
        
        # Deadlock recommendations
        if self.metrics.deadlocks > 0:
            recommendations.append({
                "category": "concurrency",
                "priority": "critical",
                "title": "Address database deadlocks",
                "description": f"Detected {self.metrics.deadlocks} deadlocks",
                "recommendation": "Review transaction isolation levels and query ordering"
            })
        
        # Success rate recommendations
        success_rate = self.metrics.successful_queries / self.metrics.total_queries if self.metrics.total_queries > 0 else 1
        if success_rate < 0.95:
            recommendations.append({
                "category": "reliability",
                "priority": "high",
                "title": "Improve query success rate",
                "description": f"Query success rate is {success_rate:.1%}",
                "recommendation": "Investigate and fix failing queries"
            })
        
        return recommendations


class CacheDBOptimizer:
    """
    Comprehensive cache and database optimization system.
    
    Coordinates caching strategies with database optimization
    to provide optimal data access performance.
    """
    
    def __init__(self):
        self.caches: Dict[str, IntelligentCache] = {}
        self.db_pools: Dict[str, DatabaseConnectionPool] = {}
        self._lock = threading.Lock()
    
    def create_cache(
        self,
        name: str,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        max_memory_mb: int = 100
    ) -> IntelligentCache:
        """Create and register a new intelligent cache."""
        with self._lock:
            if name in self.caches:
                return self.caches[name]
            
            cache = IntelligentCache(name, redis_url, default_ttl, max_memory_mb)
            self.caches[name] = cache
            
            logger.info(f"Created cache '{name}'")
            return cache
    
    def create_db_pool(
        self,
        name: str,
        database_url: str,
        min_connections: int = 5,
        max_connections: int = 20
    ) -> DatabaseConnectionPool:
        """Create and register a new database connection pool."""
        with self._lock:
            if name in self.db_pools:
                return self.db_pools[name]
            
            pool = DatabaseConnectionPool(name, database_url, min_connections, max_connections)
            self.db_pools[name] = pool
            
            logger.info(f"Created database pool '{name}'")
            return pool
    
    def get_cache(self, name: str) -> Optional[IntelligentCache]:
        """Get cache by name."""
        return self.caches.get(name)
    
    def get_db_pool(self, name: str) -> Optional[DatabaseConnectionPool]:
        """Get database pool by name."""
        return self.db_pools.get(name)
    
    async def cached_query(
        self,
        cache_name: str,
        db_pool_name: str,
        cache_key: str,
        query: str,
        params: Optional[Tuple] = None,
        ttl: Optional[int] = None,
        namespace: str = "query"
    ) -> Optional[List[Tuple]]:
        """Execute query with intelligent caching."""
        cache = self.get_cache(cache_name)
        db_pool = self.get_db_pool(db_pool_name)
        
        if not cache or not db_pool:
            raise ValueError("Cache or database pool not found")
        
        # Try cache first
        cached_result = await cache.get(cache_key, namespace)
        if cached_result is not None:
            return cached_result
        
        # Execute query and cache result
        result = await db_pool.execute_query(query, params)
        if result is not None:
            await cache.set(cache_key, result, ttl, namespace)
        
        return result
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all caches and database pools."""
        with self._lock:
            cache_stats = {}
            for name, cache in self.caches.items():
                cache_stats[name] = cache.get_cache_statistics()
            
            db_stats = {}
            for name, pool in self.db_pools.items():
                db_stats[name] = pool.get_pool_statistics()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "caches": cache_stats,
                "database_pools": db_stats,
                "summary": {
                    "total_caches": len(self.caches),
                    "total_db_pools": len(self.db_pools),
                    "overall_cache_hit_rate": self._calculate_overall_hit_rate(),
                    "overall_query_success_rate": self._calculate_overall_success_rate()
                }
            }
    
    def _calculate_overall_hit_rate(self) -> float:
        """Calculate overall cache hit rate across all caches."""
        total_requests = 0
        total_hits = 0
        
        for cache in self.caches.values():
            total_requests += cache.metrics.total_requests
            total_hits += cache.metrics.cache_hits
        
        return total_hits / total_requests if total_requests > 0 else 0
    
    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall query success rate across all pools."""
        total_queries = 0
        total_successful = 0
        
        for pool in self.db_pools.values():
            total_queries += pool.metrics.total_queries
            total_successful += pool.metrics.successful_queries
        
        return total_successful / total_queries if total_queries > 0 else 0
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Get comprehensive optimization recommendations."""
        recommendations = {
            "cache_recommendations": [],
            "database_recommendations": [],
            "integration_recommendations": []
        }
        
        # Cache recommendations
        for name, cache in self.caches.items():
            stats = cache.get_cache_statistics()
            
            if stats["hit_rate"] < 0.7:
                recommendations["cache_recommendations"].append({
                    "cache": name,
                    "priority": "high",
                    "title": "Improve cache hit rate",
                    "description": f"Hit rate is {stats['hit_rate']:.1%}",
                    "recommendation": "Review caching strategy and TTL settings"
                })
            
            if stats["errors"] > 10:
                recommendations["cache_recommendations"].append({
                    "cache": name,
                    "priority": "critical",
                    "title": "Address cache errors",
                    "description": f"Found {stats['errors']} cache errors",
                    "recommendation": "Investigate cache backend connectivity and error handling"
                })
        
        # Database recommendations
        for name, pool in self.db_pools.items():
            pool_recommendations = pool.get_optimization_recommendations()
            for rec in pool_recommendations:
                rec["pool"] = name
                recommendations["database_recommendations"].append(rec)
        
        # Integration recommendations
        overall_hit_rate = self._calculate_overall_hit_rate()
        if overall_hit_rate < 0.8:
            recommendations["integration_recommendations"].append({
                "priority": "medium",
                "title": "Implement cache warming strategy",
                "description": f"Overall cache hit rate is {overall_hit_rate:.1%}",
                "recommendation": "Implement proactive cache warming for frequently accessed data"
            })
        
        return recommendations


# Global optimizer instance
cache_db_optimizer = CacheDBOptimizer()


# Convenience functions
async def get_cached_data(
    cache_name: str,
    key: str,
    data_loader: Callable,
    ttl: Optional[int] = None,
    namespace: str = ""
) -> Any:
    """Get data with caching, loading from source if not cached."""
    cache = cache_db_optimizer.get_cache(cache_name)
    if not cache:
        # No cache available, load directly
        return await data_loader()
    
    # Try cache first
    cached_data = await cache.get(key, namespace)
    if cached_data is not None:
        return cached_data
    
    # Load from source and cache
    data = await data_loader()
    if data is not None:
        await cache.set(key, data, ttl, namespace)
    
    return data


@asynccontextmanager
async def database_transaction(pool_name: str):
    """Context manager for database transactions."""
    pool = cache_db_optimizer.get_db_pool(pool_name)
    if not pool:
        raise ValueError(f"Database pool '{pool_name}' not found")
    
    async with pool.get_connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise