"""
Permission Performance Validation API for SuperInsight Platform.

Provides REST API endpoints for monitoring and validating permission check performance
to ensure the <10ms requirement is consistently met.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.security.permission_performance_validator import (
    get_performance_validator,
    PerformanceValidationResult,
    PerformanceThresholds
)
from src.security.rbac_controller_optimized import get_optimized_rbac_controller
from src.database.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/performance", tags=["Performance Validation"])


# Pydantic models for API
class PerformanceValidationResponse(BaseModel):
    """Response model for performance validation."""
    meets_target: bool
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    compliance_rate: float
    total_checks: int
    issues: List[str]
    recommendations: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PerformanceThresholdsModel(BaseModel):
    """Model for performance thresholds."""
    target_avg_ms: float = 10.0
    target_p95_ms: float = 10.0
    target_p99_ms: float = 15.0
    min_compliance_rate: float = 95.0
    warning_avg_ms: float = 8.0
    warning_p95_ms: float = 8.0


class PerformanceReportResponse(BaseModel):
    """Response model for comprehensive performance report."""
    current_performance: Dict[str, Any]
    validation_history: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    thresholds: Dict[str, Any]
    issues: List[str]
    recommendations: List[str]
    optimization_status: Dict[str, Any]


class StressTestRequest(BaseModel):
    """Request model for stress testing."""
    num_checks: int = Field(default=1000, ge=100, le=10000)
    concurrent_users: int = Field(default=10, ge=1, le=100)


class PerformanceMetricRequest(BaseModel):
    """Request model for recording performance metrics."""
    response_time_ms: float
    cache_hit: bool = False
    user_id: Optional[UUID] = None
    permission_name: Optional[str] = None


@router.get("/validation/current", response_model=PerformanceValidationResponse)
async def get_current_performance_validation(
    time_window_minutes: int = Query(default=60, ge=1, le=1440),
    validator = Depends(get_performance_validator)
):
    """
    Get current performance validation results.
    
    Args:
        time_window_minutes: Time window for analysis (1-1440 minutes)
        
    Returns:
        Current performance validation results
    """
    try:
        result = validator.validate_current_performance(time_window_minutes)
        
        return PerformanceValidationResponse(
            meets_target=result.meets_target,
            avg_response_time_ms=result.avg_response_time_ms,
            p95_response_time_ms=result.p95_response_time_ms,
            p99_response_time_ms=result.p99_response_time_ms,
            compliance_rate=result.compliance_rate,
            total_checks=result.total_checks,
            issues=result.issues,
            recommendations=result.recommendations
        )
        
    except Exception as e:
        logger.error(f"Failed to get performance validation: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate performance")


@router.get("/report", response_model=PerformanceReportResponse)
async def get_performance_report(
    validator = Depends(get_performance_validator)
):
    """
    Get comprehensive performance report.
    
    Returns:
        Detailed performance report with trends and recommendations
    """
    try:
        report = validator.generate_performance_report()
        
        return PerformanceReportResponse(
            current_performance=report['current_performance'],
            validation_history=report['validation_history'],
            trend_analysis=report['trend_analysis'],
            thresholds=report['thresholds'],
            issues=report['issues'],
            recommendations=report['recommendations'],
            optimization_status=report['optimization_status']
        )
        
    except Exception as e:
        logger.error(f"Failed to generate performance report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate performance report")


@router.get("/trend")
async def get_performance_trend(
    days: int = Query(default=7, ge=1, le=30),
    validator = Depends(get_performance_validator)
):
    """
    Get performance trend analysis.
    
    Args:
        days: Number of days to analyze (1-30)
        
    Returns:
        Performance trend data
    """
    try:
        trend_data = validator.get_performance_trend(days)
        
        return {
            "status": "success",
            "data": trend_data,
            "analysis_period_days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance trend: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance trend")


@router.post("/stress-test", response_model=PerformanceValidationResponse)
async def run_stress_test(
    request: StressTestRequest,
    background_tasks: BackgroundTasks,
    validator = Depends(get_performance_validator)
):
    """
    Run performance stress test.
    
    Args:
        request: Stress test configuration
        
    Returns:
        Stress test results
    """
    try:
        # Get optimized RBAC controller for testing
        rbac_controller = get_optimized_rbac_controller()
        
        # Run stress test in background to avoid timeout
        def run_test():
            return validator.run_performance_stress_test(
                rbac_controller=rbac_controller,
                num_checks=request.num_checks,
                concurrent_users=request.concurrent_users
            )
        
        # For now, run synchronously (could be moved to background task)
        result = run_test()
        
        return PerformanceValidationResponse(
            meets_target=result.meets_target,
            avg_response_time_ms=result.avg_response_time_ms,
            p95_response_time_ms=result.p95_response_time_ms,
            p99_response_time_ms=result.p99_response_time_ms,
            compliance_rate=result.compliance_rate,
            total_checks=result.total_checks,
            issues=result.issues,
            recommendations=result.recommendations
        )
        
    except Exception as e:
        logger.error(f"Failed to run stress test: {e}")
        raise HTTPException(status_code=500, detail="Failed to run stress test")


@router.post("/metrics/record")
async def record_performance_metric(
    request: PerformanceMetricRequest,
    validator = Depends(get_performance_validator)
):
    """
    Record a performance metric.
    
    Args:
        request: Performance metric data
        
    Returns:
        Success confirmation
    """
    try:
        validator.record_permission_check(
            response_time_ms=request.response_time_ms,
            cache_hit=request.cache_hit,
            user_id=request.user_id,
            permission_name=request.permission_name
        )
        
        return {
            "status": "success",
            "message": "Performance metric recorded",
            "response_time_ms": request.response_time_ms
        }
        
    except Exception as e:
        logger.error(f"Failed to record performance metric: {e}")
        raise HTTPException(status_code=500, detail="Failed to record performance metric")


@router.get("/thresholds", response_model=PerformanceThresholdsModel)
async def get_performance_thresholds(
    validator = Depends(get_performance_validator)
):
    """
    Get current performance thresholds.
    
    Returns:
        Current performance thresholds
    """
    try:
        thresholds = validator.thresholds
        
        return PerformanceThresholdsModel(
            target_avg_ms=thresholds.target_avg_ms,
            target_p95_ms=thresholds.target_p95_ms,
            target_p99_ms=thresholds.target_p99_ms,
            min_compliance_rate=thresholds.min_compliance_rate,
            warning_avg_ms=thresholds.warning_avg_ms,
            warning_p95_ms=thresholds.warning_p95_ms
        )
        
    except Exception as e:
        logger.error(f"Failed to get performance thresholds: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance thresholds")


@router.put("/thresholds")
async def update_performance_thresholds(
    thresholds: PerformanceThresholdsModel,
    validator = Depends(get_performance_validator)
):
    """
    Update performance thresholds.
    
    Args:
        thresholds: New performance thresholds
        
    Returns:
        Success confirmation
    """
    try:
        # Update validator thresholds
        validator.thresholds.target_avg_ms = thresholds.target_avg_ms
        validator.thresholds.target_p95_ms = thresholds.target_p95_ms
        validator.thresholds.target_p99_ms = thresholds.target_p99_ms
        validator.thresholds.min_compliance_rate = thresholds.min_compliance_rate
        validator.thresholds.warning_avg_ms = thresholds.warning_avg_ms
        validator.thresholds.warning_p95_ms = thresholds.warning_p95_ms
        
        return {
            "status": "success",
            "message": "Performance thresholds updated",
            "thresholds": thresholds.dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to update performance thresholds: {e}")
        raise HTTPException(status_code=500, detail="Failed to update performance thresholds")


@router.post("/optimization/apply")
async def apply_performance_optimization(
    validator = Depends(get_performance_validator)
):
    """
    Mark performance optimization as applied.
    
    Returns:
        Success confirmation
    """
    try:
        validator.mark_optimization_applied()
        
        return {
            "status": "success",
            "message": "Performance optimization marked as applied",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to mark optimization as applied: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark optimization as applied")


@router.get("/health")
async def get_performance_health():
    """
    Get performance monitoring health status.
    
    Returns:
        Health status of performance monitoring
    """
    try:
        validator = get_performance_validator()
        current_validation = validator.validate_current_performance(time_window_minutes=5)
        
        # Determine health status
        if current_validation.total_checks == 0:
            health_status = "no_data"
            health_message = "No recent performance data available"
        elif current_validation.meets_target:
            health_status = "healthy"
            health_message = "Performance targets are being met"
        else:
            health_status = "degraded"
            health_message = f"Performance issues detected: {', '.join(current_validation.issues[:2])}"
        
        return {
            "status": health_status,
            "message": health_message,
            "meets_target": current_validation.meets_target,
            "avg_response_time_ms": current_validation.avg_response_time_ms,
            "compliance_rate": current_validation.compliance_rate,
            "total_checks": current_validation.total_checks,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance health: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/statistics")
async def get_performance_statistics(
    validator = Depends(get_performance_validator)
):
    """
    Get detailed performance statistics.
    
    Returns:
        Detailed performance statistics
    """
    try:
        # Get current validation
        current_validation = validator.validate_current_performance()
        
        # Get trend data
        trend_data = validator.get_performance_trend()
        
        # Calculate additional statistics
        with validator._lock:
            total_measurements = len(validator.performance_history)
            recent_measurements = list(validator.performance_history)[-1000:]  # Last 1000
        
        if recent_measurements:
            cache_hits = sum(1 for m in recent_measurements if m['cache_hit'])
            cache_hit_rate = (cache_hits / len(recent_measurements)) * 100
            
            response_times = [m['response_time_ms'] for m in recent_measurements]
            min_time = min(response_times)
            max_time = max(response_times)
        else:
            cache_hit_rate = 0.0
            min_time = 0.0
            max_time = 0.0
        
        return {
            "current_performance": {
                "meets_target": current_validation.meets_target,
                "avg_response_time_ms": current_validation.avg_response_time_ms,
                "p95_response_time_ms": current_validation.p95_response_time_ms,
                "p99_response_time_ms": current_validation.p99_response_time_ms,
                "min_response_time_ms": min_time,
                "max_response_time_ms": max_time,
                "compliance_rate": current_validation.compliance_rate,
                "cache_hit_rate": cache_hit_rate
            },
            "measurement_counts": {
                "total_measurements": total_measurements,
                "recent_measurements": len(recent_measurements),
                "validation_history_size": len(validator.validation_history)
            },
            "trend_analysis": trend_data,
            "target_thresholds": {
                "target_avg_ms": validator.thresholds.target_avg_ms,
                "target_p95_ms": validator.thresholds.target_p95_ms,
                "min_compliance_rate": validator.thresholds.min_compliance_rate
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance statistics")