"""
Cache Management API endpoints for SuperInsight Platform.

Provides REST API endpoints for managing and monitoring the permission cache system.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.rbac_controller import RBACController
from src.security.permission_cache import get_permission_cache, get_cache_manager
from src.security.models import UserModel

router = APIRouter(prefix="/api/cache", tags=["Cache Management"])


# Pydantic models for request/response
class CacheStatisticsResponse(BaseModel):
    """Response model for cache statistics."""
    hit_rate: float
    total_requests: int
    cache_hits: int
    cache_misses: int
    memory_hits: int
    redis_hits: int
    invalidations: int
    memory_cache_size: int
    memory_cache_limit: int
    redis_connected: bool
    redis_memory_usage: str
    legacy_cache_size: int
    cache_system: str


class CacheOptimizationResponse(BaseModel):
    """Response model for cache optimization analysis."""
    current_performance: Dict[str, Any]
    recommendations: List[str]
    optimization_applied: bool


class CacheWarmingRequest(BaseModel):
    """Request model for cache warming."""
    user_id: UUID
    permissions: Optional[List[str]] = None


class BatchPermissionCheckRequest(BaseModel):
    """Request model for batch permission checking."""
    user_id: UUID
    permissions: List[str]
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None


class BatchPermissionCheckResponse(BaseModel):
    """Response model for batch permission checking."""
    user_id: UUID
    results: Dict[str, bool]
    cache_hits: int
    cache_misses: int


class CacheInvalidationRequest(BaseModel):
    """Request model for cache invalidation."""
    event_type: str
    event_data: Dict[str, Any]


# Initialize controllers
rbac_controller = RBACController()
permission_cache = get_permission_cache()
cache_manager = get_cache_manager()


@router.get("/statistics", response_model=CacheStatisticsResponse)
async def get_cache_statistics():
    """
    Get comprehensive cache performance statistics.
    
    Returns detailed information about cache performance including:
    - Hit rates and request counts
    - Memory and Redis usage
    - Performance metrics
    """
    try:
        stats = rbac_controller.get_cache_statistics()
        return CacheStatisticsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache statistics: {str(e)}")


@router.get("/optimization", response_model=CacheOptimizationResponse)
async def analyze_cache_optimization():
    """
    Analyze cache performance and provide optimization recommendations.
    
    Returns:
    - Current performance metrics
    - Optimization recommendations
    - Applied optimizations status
    """
    try:
        optimization_result = rbac_controller.optimize_permission_cache()
        return CacheOptimizationResponse(**optimization_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze cache optimization: {str(e)}")


@router.post("/warm")
async def warm_user_cache(
    request: CacheWarmingRequest,
    db: Session = Depends(get_db_session)
):
    """
    Pre-warm cache with user's common permissions.
    
    Args:
        request: Cache warming request with user ID and optional permissions list
        
    Returns:
        Success status and warming details
    """
    try:
        success = rbac_controller.warm_user_cache(
            request.user_id,
            request.permissions,
            db
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found or cache warming failed")
        
        return {
            "success": True,
            "user_id": str(request.user_id),
            "permissions_warmed": request.permissions or "default_common_permissions",
            "message": "Cache warming completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache warming failed: {str(e)}")


@router.post("/check-batch", response_model=BatchPermissionCheckResponse)
async def batch_check_permissions(
    request: BatchPermissionCheckRequest,
    db: Session = Depends(get_db_session)
):
    """
    Check multiple permissions at once for better performance.
    
    Args:
        request: Batch permission check request
        
    Returns:
        Permission check results and cache performance metrics
    """
    try:
        # Get initial cache stats
        initial_stats = permission_cache.get_cache_statistics()
        initial_hits = initial_stats["cache_hits"]
        initial_misses = initial_stats["cache_misses"]
        
        # Perform batch permission check
        results = rbac_controller.batch_check_permissions(
            request.user_id,
            request.permissions,
            request.resource_id,
            None,  # Convert resource_type string to enum if needed
            db
        )
        
        # Get final cache stats
        final_stats = permission_cache.get_cache_statistics()
        cache_hits = final_stats["cache_hits"] - initial_hits
        cache_misses = final_stats["cache_misses"] - initial_misses
        
        return BatchPermissionCheckResponse(
            user_id=request.user_id,
            results=results,
            cache_hits=cache_hits,
            cache_misses=cache_misses
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch permission check failed: {str(e)}")


@router.delete("/invalidate/user/{user_id}")
async def invalidate_user_cache(
    user_id: UUID,
    tenant_id: Optional[str] = Query(None, description="Optional tenant ID for scoped invalidation")
):
    """
    Invalidate all cached permissions for a specific user.
    
    Args:
        user_id: User identifier
        tenant_id: Optional tenant ID for scoped invalidation
        
    Returns:
        Invalidation success status
    """
    try:
        permission_cache.invalidate_user_permissions(user_id, tenant_id)
        
        return {
            "success": True,
            "user_id": str(user_id),
            "tenant_id": tenant_id,
            "message": "User cache invalidated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}")


@router.delete("/invalidate/tenant/{tenant_id}")
async def invalidate_tenant_cache(tenant_id: str):
    """
    Invalidate all cached permissions for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Invalidation success status
    """
    try:
        permission_cache.invalidate_tenant_permissions(tenant_id)
        
        return {
            "success": True,
            "tenant_id": tenant_id,
            "message": "Tenant cache invalidated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}")


@router.delete("/invalidate/permission/{permission_name}")
async def invalidate_permission_cache(
    permission_name: str,
    tenant_id: Optional[str] = Query(None, description="Optional tenant ID for scoped invalidation")
):
    """
    Invalidate all cached results for a specific permission.
    
    Args:
        permission_name: Permission name
        tenant_id: Optional tenant ID for scoped invalidation
        
    Returns:
        Invalidation success status
    """
    try:
        permission_cache.invalidate_permission(permission_name, tenant_id)
        
        return {
            "success": True,
            "permission_name": permission_name,
            "tenant_id": tenant_id,
            "message": "Permission cache invalidated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}")


@router.delete("/clear")
async def clear_all_cache():
    """
    Clear all cached permissions.
    
    WARNING: This will clear all cached data and may impact performance
    until the cache is rebuilt.
    
    Returns:
        Clear operation success status
    """
    try:
        rbac_controller.clear_all_permission_cache()
        
        return {
            "success": True,
            "message": "All cache cleared successfully",
            "warning": "Cache performance may be impacted until rebuilt"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")


@router.post("/invalidate")
async def handle_cache_invalidation(request: CacheInvalidationRequest):
    """
    Handle cache invalidation based on system events.
    
    Args:
        request: Cache invalidation request with event type and data
        
    Returns:
        Invalidation handling success status
    """
    try:
        cache_manager.handle_cache_invalidation(
            request.event_type,
            request.event_data
        )
        
        return {
            "success": True,
            "event_type": request.event_type,
            "message": "Cache invalidation handled successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache invalidation handling failed: {str(e)}")


@router.post("/maintenance")
async def schedule_cache_maintenance():
    """
    Schedule cache maintenance and optimization.
    
    Returns:
        Maintenance scheduling status and optimization recommendations
    """
    try:
        maintenance_result = cache_manager.schedule_cache_maintenance()
        
        return {
            "success": True,
            "maintenance_scheduled": True,
            "optimization_analysis": maintenance_result,
            "message": "Cache maintenance scheduled successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache maintenance scheduling failed: {str(e)}")


@router.get("/health")
async def check_cache_health():
    """
    Check cache system health and connectivity.
    
    Returns:
        Cache system health status
    """
    try:
        stats = permission_cache.get_cache_statistics()
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        if not stats["redis_connected"]:
            health_status = "degraded"
            issues.append("Redis connection unavailable - using memory-only cache")
        
        if stats["hit_rate"] < 50:
            health_status = "degraded"
            issues.append("Low cache hit rate - consider cache warming")
        
        if stats["memory_cache_size"] >= stats["memory_cache_limit"]:
            health_status = "warning"
            issues.append("Memory cache at capacity - consider increasing size")
        
        return {
            "status": health_status,
            "redis_connected": stats["redis_connected"],
            "hit_rate": stats["hit_rate"],
            "memory_usage": f"{stats['memory_cache_size']}/{stats['memory_cache_limit']}",
            "issues": issues,
            "timestamp": "2026-01-11T00:00:00Z"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2026-01-11T00:00:00Z"
        }


@router.get("/performance")
async def get_cache_performance_metrics():
    """
    Get detailed cache performance metrics for monitoring.
    
    Returns:
        Comprehensive performance metrics
    """
    try:
        stats = permission_cache.get_cache_statistics()
        optimization = permission_cache.optimize_cache()
        
        return {
            "performance_metrics": {
                "hit_rate": stats["hit_rate"],
                "total_requests": stats["total_requests"],
                "average_response_time": "< 1ms",  # Estimated for cache operations
                "memory_efficiency": (stats["memory_cache_size"] / stats["memory_cache_limit"]) * 100,
                "redis_status": "connected" if stats["redis_connected"] else "disconnected"
            },
            "optimization_recommendations": optimization["recommendations"],
            "cache_distribution": {
                "memory_hits": stats["memory_hits"],
                "redis_hits": stats["redis_hits"],
                "cache_misses": stats["cache_misses"]
            },
            "system_info": {
                "cache_system": stats["cache_system"],
                "redis_memory_usage": stats["redis_memory_usage"],
                "invalidations_count": stats["invalidations"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")