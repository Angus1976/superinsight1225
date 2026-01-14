"""
Permission Performance API for SuperInsight Platform.

Provides REST API endpoints for monitoring and managing permission check performance,
including the <10ms response time optimization features.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.security.rbac_controller_optimized import get_optimized_rbac_controller
from src.security.permission_performance_optimizer import (
    get_permission_performance_optimizer,
    OptimizationConfig
)
from src.api.auth import get_current_user
from src.security.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/permission-performance", tags=["Permission Performance"])


# Pydantic models for API requests/responses

class PerformanceStatsResponse(BaseModel):
    """Performance statistics response model."""
    total_checks: int
    cache_hit_rate: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    target_compliance_rate: float
    checks_under_10ms: int
    checks_over_10ms: int
    optimization_enabled: bool
    target_response_time_ms: float


class OptimizationConfigRequest(BaseModel):
    """Optimization configuration request model."""
    target_response_time_ms: float = Field(default=10.0, ge=1.0, le=100.0)
    cache_preload_enabled: bool = True
    query_optimization_enabled: bool = True
    batch_processing_enabled: bool = True
    async_logging_enabled: bool = True
    memory_cache_size: int = Field(default=5000, ge=100, le=50000)
    redis_cache_ttl: int = Field(default=600, ge=60, le=3600)


class PerformanceTestRequest(BaseModel):
    """Performance test request model."""
    user_id: Optional[UUID] = None
    permissions: List[str] = Field(default=["read_data", "write_data", "view_dashboard"])
    test_iterations: int = Field(default=100, ge=10, le=1000)
    concurrent_users: int = Field(default=1, ge=1, le=50)


class PerformanceTestResult(BaseModel):
    """Performance test result model."""
    test_id: str
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    target_compliance_rate: float
    total_checks: int
    successful_checks: int
    failed_checks: int
    test_duration_ms: float


class PreloadRequest(BaseModel):
    """Permission preload request model."""
    user_ids: List[UUID]
    permissions: Optional[List[str]] = None


# API Endpoints

@router.get("/stats", response_model=PerformanceStatsResponse)
async def get_performance_statistics(
    time_window_minutes: int = Query(default=60, ge=1, le=1440),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get permission check performance statistics.
    
    Args:
        time_window_minutes: Time window for statistics (1-1440 minutes)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Performance statistics including response times and compliance rates
    """
    try:
        # Check if user has permission to view performance stats
        controller = get_optimized_rbac_controller()
        has_permission = controller.check_user_permission(
            user_id=current_user.id,
            permission_name="view_performance_stats",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get performance statistics
        optimizer = get_permission_performance_optimizer()
        stats = optimizer.monitor.get_performance_stats(time_window_minutes)
        
        # Get controller statistics
        controller_stats = controller.get_performance_statistics()
        
        return PerformanceStatsResponse(
            total_checks=stats.total_checks,
            cache_hit_rate=(stats.cache_hits / stats.total_checks * 100) if stats.total_checks > 0 else 0,
            avg_response_time_ms=stats.avg_response_time_ms,
            p95_response_time_ms=stats.p95_response_time_ms,
            p99_response_time_ms=stats.p99_response_time_ms,
            target_compliance_rate=stats.target_compliance_rate,
            checks_under_10ms=stats.checks_under_10ms,
            checks_over_10ms=stats.checks_over_10ms,
            optimization_enabled=controller.performance_optimizer.is_optimization_enabled(),
            target_response_time_ms=controller.performance_optimizer.config.target_response_time_ms
        )
        
    except Exception as e:
        logger.error(f"Failed to get performance statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance statistics")


@router.get("/recommendations")
async def get_performance_recommendations(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get performance optimization recommendations.
    
    Returns:
        List of optimization recommendations and current performance analysis
    """
    try:
        # Check permissions
        controller = get_optimized_rbac_controller()
        has_permission = controller.check_user_permission(
            user_id=current_user.id,
            permission_name="view_performance_stats",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get recommendations
        recommendations = controller.get_performance_recommendations()
        optimizer = get_permission_performance_optimizer()
        performance_report = optimizer.get_performance_report()
        
        return {
            "recommendations": recommendations,
            "performance_report": performance_report,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recommendations")


@router.post("/config")
async def update_optimization_config(
    config: OptimizationConfigRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update performance optimization configuration.
    
    Args:
        config: New optimization configuration
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated configuration and status
    """
    try:
        # Check permissions
        controller = get_optimized_rbac_controller()
        has_permission = controller.check_user_permission(
            user_id=current_user.id,
            permission_name="manage_performance_config",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Update configuration
        optimizer = get_permission_performance_optimizer()
        new_config = OptimizationConfig(
            target_response_time_ms=config.target_response_time_ms,
            cache_preload_enabled=config.cache_preload_enabled,
            query_optimization_enabled=config.query_optimization_enabled,
            batch_processing_enabled=config.batch_processing_enabled,
            async_logging_enabled=config.async_logging_enabled,
            memory_cache_size=config.memory_cache_size,
            redis_cache_ttl=config.redis_cache_ttl
        )
        
        optimizer.config = new_config
        
        # Log configuration change
        logger.info(f"Performance optimization config updated by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Optimization configuration updated successfully",
            "config": {
                "target_response_time_ms": new_config.target_response_time_ms,
                "cache_preload_enabled": new_config.cache_preload_enabled,
                "query_optimization_enabled": new_config.query_optimization_enabled,
                "batch_processing_enabled": new_config.batch_processing_enabled,
                "memory_cache_size": new_config.memory_cache_size,
                "redis_cache_ttl": new_config.redis_cache_ttl
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update optimization config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.post("/test", response_model=PerformanceTestResult)
async def run_performance_test(
    test_request: PerformanceTestRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run a performance test to validate <10ms response time requirement.
    
    Args:
        test_request: Performance test configuration
        background_tasks: Background task manager
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Performance test results
    """
    try:
        # Check permissions
        controller = get_optimized_rbac_controller()
        has_permission = controller.check_user_permission(
            user_id=current_user.id,
            permission_name="run_performance_tests",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Use current user if no user_id specified
        test_user_id = test_request.user_id or current_user.id
        
        # Run performance test
        test_result = await _run_permission_performance_test(
            user_id=test_user_id,
            permissions=test_request.permissions,
            iterations=test_request.test_iterations,
            concurrent_users=test_request.concurrent_users,
            db=db
        )
        
        # Log test execution
        logger.info(f"Performance test completed by user {current_user.id}: {test_result.target_compliance_rate:.1f}% compliance")
        
        return test_result
        
    except Exception as e:
        logger.error(f"Failed to run performance test: {e}")
        raise HTTPException(status_code=500, detail="Failed to run performance test")


@router.post("/preload")
async def preload_user_permissions(
    preload_request: PreloadRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Preload permissions for specified users to improve cache hit rates.
    
    Args:
        preload_request: Preload configuration
        background_tasks: Background task manager
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Preload operation status
    """
    try:
        # Check permissions
        controller = get_optimized_rbac_controller()
        has_permission = controller.check_user_permission(
            user_id=current_user.id,
            permission_name="manage_permission_cache",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Validate user count
        if len(preload_request.user_ids) > 100:
            raise HTTPException(status_code=400, detail="Cannot preload more than 100 users at once")
        
        # Schedule preload operation in background
        background_tasks.add_task(
            _preload_users_background,
            preload_request.user_ids,
            preload_request.permissions,
            db
        )
        
        return {
            "status": "accepted",
            "message": f"Preload operation scheduled for {len(preload_request.user_ids)} users",
            "user_count": len(preload_request.user_ids),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to schedule preload operation: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule preload operation")


@router.post("/optimization/enable")
async def enable_optimization(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Enable performance optimization features."""
    try:
        # Check permissions
        controller = get_optimized_rbac_controller()
        has_permission = controller.check_user_permission(
            user_id=current_user.id,
            permission_name="manage_performance_config",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Enable optimization
        controller.enable_performance_optimization()
        
        logger.info(f"Performance optimization enabled by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Performance optimization enabled",
            "optimization_enabled": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to enable optimization: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable optimization")


@router.post("/optimization/disable")
async def disable_optimization(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Disable performance optimization features."""
    try:
        # Check permissions
        controller = get_optimized_rbac_controller()
        has_permission = controller.check_user_permission(
            user_id=current_user.id,
            permission_name="manage_performance_config",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Disable optimization
        controller.disable_performance_optimization()
        
        logger.info(f"Performance optimization disabled by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Performance optimization disabled",
            "optimization_enabled": False,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to disable optimization: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable optimization")


@router.get("/cache/stats")
async def get_cache_statistics(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get permission cache statistics."""
    try:
        # Check permissions
        controller = get_optimized_rbac_controller()
        has_permission = controller.check_user_permission(
            user_id=current_user.id,
            permission_name="view_performance_stats",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get cache statistics
        cache_stats = controller.get_cache_statistics()
        
        return {
            "cache_statistics": cache_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")


@router.post("/cache/clear")
async def clear_permission_cache(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Clear all permission cache."""
    try:
        # Check permissions
        controller = get_optimized_rbac_controller()
        has_permission = controller.check_user_permission(
            user_id=current_user.id,
            permission_name="manage_permission_cache",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Clear cache
        controller.clear_all_permission_cache()
        
        logger.info(f"Permission cache cleared by user {current_user.id}")
        
        return {
            "status": "success",
            "message": "Permission cache cleared successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


# Helper functions

async def _run_permission_performance_test(
    user_id: UUID,
    permissions: List[str],
    iterations: int,
    concurrent_users: int,
    db: Session
) -> PerformanceTestResult:
    """Run a comprehensive permission performance test."""
    import time
    import statistics
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    controller = get_optimized_rbac_controller()
    test_id = f"perf_test_{int(time.time())}"
    
    def single_permission_check(permission: str) -> tuple:
        """Single permission check with timing."""
        start_time = time.perf_counter()
        try:
            result = controller.check_user_permission(
                user_id=user_id,
                permission_name=permission,
                db=db
            )
            end_time = time.perf_counter()
            return True, (end_time - start_time) * 1000, result
        except Exception as e:
            end_time = time.perf_counter()
            return False, (end_time - start_time) * 1000, False
    
    # Run performance test
    test_start = time.perf_counter()
    response_times = []
    successful_checks = 0
    failed_checks = 0
    
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = []
        
        for i in range(iterations):
            permission = permissions[i % len(permissions)]
            future = executor.submit(single_permission_check, permission)
            futures.append(future)
        
        for future in as_completed(futures):
            success, response_time_ms, result = future.result()
            response_times.append(response_time_ms)
            
            if success:
                successful_checks += 1
            else:
                failed_checks += 1
    
    test_end = time.perf_counter()
    test_duration_ms = (test_end - test_start) * 1000
    
    # Calculate statistics
    avg_response_time = statistics.mean(response_times)
    p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
    p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 1 else response_times[0]
    max_response_time = max(response_times)
    
    # Calculate compliance rate
    under_target = sum(1 for t in response_times if t < 10.0)
    compliance_rate = (under_target / len(response_times)) * 100 if response_times else 0
    
    return PerformanceTestResult(
        test_id=test_id,
        avg_response_time_ms=avg_response_time,
        p95_response_time_ms=p95_response_time,
        p99_response_time_ms=p99_response_time,
        max_response_time_ms=max_response_time,
        target_compliance_rate=compliance_rate,
        total_checks=len(response_times),
        successful_checks=successful_checks,
        failed_checks=failed_checks,
        test_duration_ms=test_duration_ms
    )


async def _preload_users_background(
    user_ids: List[UUID],
    permissions: Optional[List[str]],
    db: Session
):
    """Background task to preload user permissions."""
    try:
        controller = get_optimized_rbac_controller()
        
        for user_id in user_ids:
            try:
                await controller.preload_user_permissions(user_id, db, permissions)
                logger.debug(f"Preloaded permissions for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to preload permissions for user {user_id}: {e}")
        
        logger.info(f"Completed preloading permissions for {len(user_ids)} users")
        
    except Exception as e:
        logger.error(f"Background preload operation failed: {e}")