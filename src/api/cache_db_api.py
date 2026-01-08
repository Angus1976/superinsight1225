"""
Cache and Database Optimization API endpoints.

Provides REST API for:
- Cache management and statistics
- Database connection pool monitoring
- Query optimization recommendations
- Performance analysis and tuning
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from src.system.cache_db_optimizer import cache_db_optimizer


router = APIRouter(prefix="/api/v1/cache-db", tags=["cache-db"])


# ==================== Request/Response Models ====================

class CreateCacheRequest(BaseModel):
    """Request model for creating a cache."""
    name: str = Field(..., description="Cache name")
    redis_url: Optional[str] = Field(None, description="Redis connection URL")
    default_ttl: int = Field(3600, ge=60, le=86400, description="Default TTL in seconds")
    max_memory_mb: int = Field(100, ge=10, le=1000, description="Maximum memory in MB")


class CreateDBPoolRequest(BaseModel):
    """Request model for creating a database pool."""
    name: str = Field(..., description="Pool name")
    database_url: str = Field(..., description="Database connection URL")
    min_connections: int = Field(5, ge=1, le=50, description="Minimum connections")
    max_connections: int = Field(20, ge=5, le=100, description="Maximum connections")


class CacheSetRequest(BaseModel):
    """Request model for setting cache value."""
    key: str = Field(..., description="Cache key")
    value: Any = Field(..., description="Value to cache")
    ttl: Optional[int] = Field(None, ge=60, le=86400, description="TTL in seconds")
    namespace: str = Field("", description="Cache namespace")


class ExecuteQueryRequest(BaseModel):
    """Request model for executing database query."""
    query: str = Field(..., description="SQL query to execute")
    params: Optional[List[Any]] = Field(None, description="Query parameters")
    fetch: bool = Field(True, description="Whether to fetch results")


class CachedQueryRequest(BaseModel):
    """Request model for cached query execution."""
    cache_name: str = Field(..., description="Cache name")
    db_pool_name: str = Field(..., description="Database pool name")
    cache_key: str = Field(..., description="Cache key")
    query: str = Field(..., description="SQL query")
    params: Optional[List[Any]] = Field(None, description="Query parameters")
    ttl: Optional[int] = Field(None, description="Cache TTL")
    namespace: str = Field("query", description="Cache namespace")


# ==================== Cache Management Endpoints ====================

@router.post("/caches", response_model=Dict[str, Any])
async def create_cache(request: CreateCacheRequest) -> Dict[str, Any]:
    """
    Create a new intelligent cache.
    
    Creates a cache with adaptive TTL, performance monitoring,
    and intelligent eviction policies.
    """
    try:
        cache = cache_db_optimizer.create_cache(
            name=request.name,
            redis_url=request.redis_url,
            default_ttl=request.default_ttl,
            max_memory_mb=request.max_memory_mb
        )
        
        return {
            "status": "success",
            "message": f"Cache '{request.name}' created successfully",
            "cache": {
                "name": cache.name,
                "backend": cache.backend,
                "default_ttl": cache.default_ttl,
                "max_memory_mb": cache.max_memory_mb
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create cache: {str(e)}")


@router.get("/caches", response_model=Dict[str, Any])
async def list_caches() -> Dict[str, Any]:
    """
    List all available caches.
    
    Returns information about all registered caches including
    their configuration and current status.
    """
    try:
        caches_info = []
        
        for name, cache in cache_db_optimizer.caches.items():
            caches_info.append({
                "name": cache.name,
                "backend": cache.backend,
                "default_ttl": cache.default_ttl,
                "max_memory_mb": cache.max_memory_mb,
                "total_requests": cache.metrics.total_requests,
                "hit_rate": cache.metrics.hit_rate,
                "errors": cache.metrics.errors
            })
        
        return {
            "status": "success",
            "caches": caches_info,
            "total_caches": len(caches_info),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list caches: {str(e)}")


@router.get("/caches/{cache_name}/statistics", response_model=Dict[str, Any])
async def get_cache_statistics(cache_name: str) -> Dict[str, Any]:
    """
    Get detailed cache statistics.
    
    Returns comprehensive performance metrics including hit rates,
    response times, popular keys, and optimization insights.
    """
    try:
        cache = cache_db_optimizer.get_cache(cache_name)
        if not cache:
            raise HTTPException(status_code=404, detail="Cache not found")
        
        statistics = cache.get_cache_statistics()
        
        return {
            "status": "success",
            "statistics": statistics,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache statistics: {str(e)}")


@router.post("/caches/{cache_name}/set", response_model=Dict[str, Any])
async def set_cache_value(cache_name: str, request: CacheSetRequest) -> Dict[str, Any]:
    """
    Set a value in the cache.
    
    Stores a value in the specified cache with optional TTL and namespace.
    """
    try:
        cache = cache_db_optimizer.get_cache(cache_name)
        if not cache:
            raise HTTPException(status_code=404, detail="Cache not found")
        
        success = await cache.set(
            key=request.key,
            value=request.value,
            ttl=request.ttl,
            namespace=request.namespace
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set cache value")
        
        return {
            "status": "success",
            "message": f"Value set in cache '{cache_name}'",
            "key": request.key,
            "namespace": request.namespace,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set cache value: {str(e)}")


@router.get("/caches/{cache_name}/get/{key}", response_model=Dict[str, Any])
async def get_cache_value(
    cache_name: str,
    key: str,
    namespace: str = Query("", description="Cache namespace")
) -> Dict[str, Any]:
    """
    Get a value from the cache.
    
    Retrieves a value from the specified cache with optional namespace.
    """
    try:
        cache = cache_db_optimizer.get_cache(cache_name)
        if not cache:
            raise HTTPException(status_code=404, detail="Cache not found")
        
        value = await cache.get(key, namespace)
        
        return {
            "status": "success",
            "found": value is not None,
            "key": key,
            "namespace": namespace,
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache value: {str(e)}")


@router.delete("/caches/{cache_name}/delete/{key}", response_model=Dict[str, Any])
async def delete_cache_value(
    cache_name: str,
    key: str,
    namespace: str = Query("", description="Cache namespace")
) -> Dict[str, Any]:
    """
    Delete a value from the cache.
    
    Removes a value from the specified cache with optional namespace.
    """
    try:
        cache = cache_db_optimizer.get_cache(cache_name)
        if not cache:
            raise HTTPException(status_code=404, detail="Cache not found")
        
        success = await cache.delete(key, namespace)
        
        return {
            "status": "success",
            "deleted": success,
            "key": key,
            "namespace": namespace,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete cache value: {str(e)}")


# ==================== Database Pool Management Endpoints ====================

@router.post("/db-pools", response_model=Dict[str, Any])
async def create_db_pool(request: CreateDBPoolRequest) -> Dict[str, Any]:
    """
    Create a new database connection pool.
    
    Creates an optimized connection pool with performance monitoring
    and automatic query optimization suggestions.
    """
    try:
        pool = cache_db_optimizer.create_db_pool(
            name=request.name,
            database_url=request.database_url,
            min_connections=request.min_connections,
            max_connections=request.max_connections
        )
        
        return {
            "status": "success",
            "message": f"Database pool '{request.name}' created successfully",
            "pool": {
                "name": pool.name,
                "min_connections": pool.min_connections,
                "max_connections": pool.max_connections
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create database pool: {str(e)}")


@router.get("/db-pools", response_model=Dict[str, Any])
async def list_db_pools() -> Dict[str, Any]:
    """
    List all database connection pools.
    
    Returns information about all registered database pools including
    their configuration and current status.
    """
    try:
        pools_info = []
        
        for name, pool in cache_db_optimizer.db_pools.items():
            pools_info.append({
                "name": pool.name,
                "min_connections": pool.min_connections,
                "max_connections": pool.max_connections,
                "active_connections": pool.metrics.active_connections,
                "total_queries": pool.metrics.total_queries,
                "success_rate": pool.metrics.successful_queries / pool.metrics.total_queries if pool.metrics.total_queries > 0 else 0,
                "avg_query_time": pool.metrics.avg_query_time,
                "slow_queries": pool.metrics.slow_queries
            })
        
        return {
            "status": "success",
            "pools": pools_info,
            "total_pools": len(pools_info),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list database pools: {str(e)}")


@router.get("/db-pools/{pool_name}/statistics", response_model=Dict[str, Any])
async def get_db_pool_statistics(pool_name: str) -> Dict[str, Any]:
    """
    Get detailed database pool statistics.
    
    Returns comprehensive performance metrics including query times,
    connection usage, slow queries, and optimization suggestions.
    """
    try:
        pool = cache_db_optimizer.get_db_pool(pool_name)
        if not pool:
            raise HTTPException(status_code=404, detail="Database pool not found")
        
        statistics = pool.get_pool_statistics()
        
        return {
            "status": "success",
            "statistics": statistics,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pool statistics: {str(e)}")


@router.post("/db-pools/{pool_name}/execute", response_model=Dict[str, Any])
async def execute_query(pool_name: str, request: ExecuteQueryRequest) -> Dict[str, Any]:
    """
    Execute a query using the specified database pool.
    
    Executes a SQL query with performance monitoring and
    automatic optimization analysis.
    """
    try:
        pool = cache_db_optimizer.get_db_pool(pool_name)
        if not pool:
            raise HTTPException(status_code=404, detail="Database pool not found")
        
        start_time = datetime.now()
        result = await pool.execute_query(
            query=request.query,
            params=tuple(request.params) if request.params else None,
            fetch=request.fetch
        )
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "status": "success",
            "execution_time": execution_time,
            "result": result if request.fetch else None,
            "rows_affected": len(result) if result else 0,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute query: {str(e)}")


# ==================== Integrated Cache-DB Operations ====================

@router.post("/cached-query", response_model=Dict[str, Any])
async def execute_cached_query(request: CachedQueryRequest) -> Dict[str, Any]:
    """
    Execute a query with intelligent caching.
    
    Attempts to retrieve results from cache first, executes the query
    if not cached, and stores the result for future requests.
    """
    try:
        start_time = datetime.now()
        
        result = await cache_db_optimizer.cached_query(
            cache_name=request.cache_name,
            db_pool_name=request.db_pool_name,
            cache_key=request.cache_key,
            query=request.query,
            params=tuple(request.params) if request.params else None,
            ttl=request.ttl,
            namespace=request.namespace
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Check if result came from cache
        cache = cache_db_optimizer.get_cache(request.cache_name)
        was_cached = cache and cache.metrics.cache_hits > 0
        
        return {
            "status": "success",
            "execution_time": execution_time,
            "result": result,
            "rows_returned": len(result) if result else 0,
            "from_cache": was_cached,
            "cache_key": request.cache_key,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute cached query: {str(e)}")


# ==================== Performance Analysis Endpoints ====================

@router.get("/statistics/comprehensive", response_model=Dict[str, Any])
async def get_comprehensive_statistics() -> Dict[str, Any]:
    """
    Get comprehensive statistics for all caches and database pools.
    
    Returns detailed performance metrics, optimization opportunities,
    and system-wide analysis.
    """
    try:
        statistics = cache_db_optimizer.get_comprehensive_statistics()
        
        return {
            "status": "success",
            "statistics": statistics
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comprehensive statistics: {str(e)}")


@router.get("/optimization/recommendations", response_model=Dict[str, Any])
async def get_optimization_recommendations() -> Dict[str, Any]:
    """
    Get optimization recommendations for caches and databases.
    
    Analyzes performance patterns and provides actionable
    recommendations for improving system performance.
    """
    try:
        recommendations = cache_db_optimizer.get_optimization_recommendations()
        
        # Calculate priority summary
        all_recommendations = (
            recommendations["cache_recommendations"] +
            recommendations["database_recommendations"] +
            recommendations["integration_recommendations"]
        )
        
        priority_summary = {
            "critical": len([r for r in all_recommendations if r.get("priority") == "critical"]),
            "high": len([r for r in all_recommendations if r.get("priority") == "high"]),
            "medium": len([r for r in all_recommendations if r.get("priority") == "medium"]),
            "low": len([r for r in all_recommendations if r.get("priority") == "low"])
        }
        
        return {
            "status": "success",
            "recommendations": recommendations,
            "summary": {
                "total_recommendations": len(all_recommendations),
                "priority_breakdown": priority_summary
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get optimization recommendations: {str(e)}")


@router.get("/analysis/performance-impact", response_model=Dict[str, Any])
async def get_performance_impact_analysis() -> Dict[str, Any]:
    """
    Analyze performance impact of current cache and database configuration.
    
    Evaluates how current settings affect application performance
    and identifies optimization opportunities.
    """
    try:
        statistics = cache_db_optimizer.get_comprehensive_statistics()
        
        # Analyze cache performance impact
        cache_impact = []
        for cache_name, cache_stats in statistics["caches"].items():
            hit_rate = cache_stats["hit_rate"]
            
            if hit_rate < 0.5:
                cache_impact.append({
                    "cache": cache_name,
                    "impact_level": "high",
                    "issue": "low_hit_rate",
                    "current_value": hit_rate,
                    "performance_impact": "Frequent database queries due to cache misses",
                    "recommendation": "Review caching strategy and TTL settings"
                })
            elif hit_rate < 0.7:
                cache_impact.append({
                    "cache": cache_name,
                    "impact_level": "medium",
                    "issue": "suboptimal_hit_rate",
                    "current_value": hit_rate,
                    "performance_impact": "Moderate database load due to cache misses",
                    "recommendation": "Optimize cache key strategy and warming"
                })
        
        # Analyze database performance impact
        db_impact = []
        for pool_name, pool_stats in statistics["database_pools"].items():
            avg_query_time = pool_stats["avg_query_time"]
            success_rate = pool_stats["success_rate"]
            
            if avg_query_time > 1.0:
                db_impact.append({
                    "pool": pool_name,
                    "impact_level": "high",
                    "issue": "slow_queries",
                    "current_value": avg_query_time,
                    "performance_impact": "High response times affecting user experience",
                    "recommendation": "Optimize slow queries and add indexes"
                })
            
            if success_rate < 0.95:
                db_impact.append({
                    "pool": pool_name,
                    "impact_level": "critical",
                    "issue": "query_failures",
                    "current_value": success_rate,
                    "performance_impact": "Application errors and data inconsistency",
                    "recommendation": "Investigate and fix failing queries"
                })
        
        # Calculate overall performance score
        overall_score = 100
        
        # Deduct points for cache issues
        for impact in cache_impact:
            if impact["impact_level"] == "high":
                overall_score -= 20
            elif impact["impact_level"] == "medium":
                overall_score -= 10
        
        # Deduct points for database issues
        for impact in db_impact:
            if impact["impact_level"] == "critical":
                overall_score -= 30
            elif impact["impact_level"] == "high":
                overall_score -= 20
        
        overall_score = max(0, overall_score)
        
        return {
            "status": "success",
            "performance_analysis": {
                "overall_score": overall_score,
                "cache_impact": cache_impact,
                "database_impact": db_impact,
                "recommendations": [
                    "Implement cache warming for frequently accessed data",
                    "Monitor and optimize slow database queries",
                    "Set up proactive alerting for performance degradation",
                    "Regular review of cache hit rates and database performance"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze performance impact: {str(e)}")


# ==================== Health Check ====================

@router.get("/health", response_model=Dict[str, Any])
async def cache_db_health() -> Dict[str, Any]:
    """
    Health check for cache and database optimization service.
    """
    try:
        statistics = cache_db_optimizer.get_comprehensive_statistics()
        
        return {
            "status": "healthy",
            "service": "cache_db_optimization",
            "components": {
                "optimizer": "available",
                "caches": f"{statistics['summary']['total_caches']} active",
                "db_pools": f"{statistics['summary']['total_db_pools']} active"
            },
            "performance": {
                "overall_cache_hit_rate": statistics["summary"]["overall_cache_hit_rate"],
                "overall_query_success_rate": statistics["summary"]["overall_query_success_rate"]
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "cache_db_optimization",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }