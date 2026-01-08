"""
Resource Optimization API endpoints.

Provides REST API for:
- Resource usage monitoring and statistics
- Resource usage predictions and capacity planning
- Scaling recommendations and cost optimization
- Resource bottleneck analysis and resolution
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from src.system.resource_optimizer import (
    resource_monitor,
    resource_predictor,
    resource_optimizer
)


router = APIRouter(prefix="/api/v1/resources", tags=["resources"])


# ==================== Request/Response Models ====================

class ResourceThresholdUpdate(BaseModel):
    """Request model for updating resource thresholds."""
    cpu_warning: Optional[float] = Field(None, ge=0, le=100, description="CPU warning threshold")
    cpu_critical: Optional[float] = Field(None, ge=0, le=100, description="CPU critical threshold")
    memory_warning: Optional[float] = Field(None, ge=0, le=100, description="Memory warning threshold")
    memory_critical: Optional[float] = Field(None, ge=0, le=100, description="Memory critical threshold")
    disk_warning: Optional[float] = Field(None, ge=0, le=100, description="Disk warning threshold")
    disk_critical: Optional[float] = Field(None, ge=0, le=100, description="Disk critical threshold")


# ==================== Resource Monitoring Endpoints ====================

@router.get("/current", response_model=Dict[str, Any])
async def get_current_resource_usage() -> Dict[str, Any]:
    """
    Get current resource usage metrics.
    
    Returns real-time CPU, memory, disk, and network usage information.
    """
    try:
        current_metrics = resource_monitor.get_current_metrics()
        
        if not current_metrics:
            raise HTTPException(status_code=503, detail="Resource monitoring not available")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "metrics": current_metrics.to_dict()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current metrics: {str(e)}")


@router.get("/statistics", response_model=Dict[str, Any])
async def get_resource_statistics(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to analyze")
) -> Dict[str, Any]:
    """
    Get resource usage statistics over a specified time period.
    
    Returns statistical analysis including averages, percentiles, and trends.
    """
    try:
        statistics = resource_monitor.get_resource_statistics(hours)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "statistics": statistics
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/history", response_model=Dict[str, Any])
async def get_resource_history(
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve")
) -> Dict[str, Any]:
    """
    Get detailed resource usage history.
    
    Returns time-series data for resource usage over the specified period.
    """
    try:
        history = resource_monitor.get_metrics_history(hours)
        
        return {
            "status": "success",
            "period_hours": hours,
            "data_points": len(history),
            "history": [metrics.to_dict() for metrics in history]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.post("/monitoring/start", response_model=Dict[str, Any])
async def start_resource_monitoring() -> Dict[str, Any]:
    """
    Start resource monitoring.
    
    Begins continuous collection of resource usage metrics.
    """
    try:
        await resource_monitor.start_monitoring()
        
        return {
            "status": "success",
            "message": "Resource monitoring started",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/monitoring/stop", response_model=Dict[str, Any])
async def stop_resource_monitoring() -> Dict[str, Any]:
    """
    Stop resource monitoring.
    
    Stops continuous collection of resource usage metrics.
    """
    try:
        await resource_monitor.stop_monitoring()
        
        return {
            "status": "success",
            "message": "Resource monitoring stopped",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")


@router.put("/thresholds", response_model=Dict[str, Any])
async def update_resource_thresholds(request: ResourceThresholdUpdate) -> Dict[str, Any]:
    """
    Update resource alert thresholds.
    
    Configures warning and critical thresholds for resource usage alerts.
    """
    try:
        updated_thresholds = {}
        
        if request.cpu_warning is not None:
            resource_monitor.cpu_warning_threshold = request.cpu_warning
            updated_thresholds["cpu_warning"] = request.cpu_warning
        
        if request.cpu_critical is not None:
            resource_monitor.cpu_critical_threshold = request.cpu_critical
            updated_thresholds["cpu_critical"] = request.cpu_critical
        
        if request.memory_warning is not None:
            resource_monitor.memory_warning_threshold = request.memory_warning
            updated_thresholds["memory_warning"] = request.memory_warning
        
        if request.memory_critical is not None:
            resource_monitor.memory_critical_threshold = request.memory_critical
            updated_thresholds["memory_critical"] = request.memory_critical
        
        if request.disk_warning is not None:
            resource_monitor.disk_warning_threshold = request.disk_warning
            updated_thresholds["disk_warning"] = request.disk_warning
        
        if request.disk_critical is not None:
            resource_monitor.disk_critical_threshold = request.disk_critical
            updated_thresholds["disk_critical"] = request.disk_critical
        
        return {
            "status": "success",
            "message": "Resource thresholds updated",
            "updated_thresholds": updated_thresholds,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update thresholds: {str(e)}")


# ==================== Resource Prediction Endpoints ====================

@router.get("/predictions/{resource_type}", response_model=Dict[str, Any])
async def get_resource_prediction(
    resource_type: str,
    hours_ahead: int = Query(24, ge=1, le=168, description="Hours ahead to predict")
) -> Dict[str, Any]:
    """
    Get resource usage prediction for a specific resource type.
    
    Predicts future resource usage based on historical patterns and trends.
    """
    try:
        if resource_type not in ["cpu", "memory", "disk"]:
            raise HTTPException(status_code=400, detail="Invalid resource type. Must be cpu, memory, or disk")
        
        prediction = resource_predictor.predict_resource_usage(resource_type, hours_ahead)
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Insufficient data for prediction")
        
        return {
            "status": "success",
            "prediction": prediction.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prediction: {str(e)}")


@router.get("/predictions", response_model=Dict[str, Any])
async def get_all_resource_predictions(
    hours_ahead: int = Query(24, ge=1, le=168, description="Hours ahead to predict")
) -> Dict[str, Any]:
    """
    Get resource usage predictions for all resource types.
    
    Returns comprehensive predictions for CPU, memory, and disk usage.
    """
    try:
        predictions = {}
        
        for resource_type in ["cpu", "memory", "disk"]:
            prediction = resource_predictor.predict_resource_usage(resource_type, hours_ahead)
            if prediction:
                predictions[resource_type] = prediction.to_dict()
        
        return {
            "status": "success",
            "predictions": predictions,
            "hours_ahead": hours_ahead,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get predictions: {str(e)}")


# ==================== Resource Optimization Endpoints ====================

@router.get("/bottlenecks", response_model=Dict[str, Any])
async def get_resource_bottlenecks() -> Dict[str, Any]:
    """
    Analyze current resource bottlenecks.
    
    Identifies performance bottlenecks and provides detailed analysis
    including root causes and resolution recommendations.
    """
    try:
        bottlenecks = resource_optimizer.analyze_bottlenecks()
        
        return {
            "status": "success",
            "bottlenecks": [b.to_dict() for b in bottlenecks],
            "total_bottlenecks": len(bottlenecks),
            "severity_breakdown": {
                "critical": len([b for b in bottlenecks if b.severity == "critical"]),
                "high": len([b for b in bottlenecks if b.severity == "high"]),
                "medium": len([b for b in bottlenecks if b.severity == "medium"])
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze bottlenecks: {str(e)}")


@router.get("/scaling-recommendations", response_model=Dict[str, Any])
async def get_scaling_recommendations() -> Dict[str, Any]:
    """
    Get intelligent scaling recommendations.
    
    Provides data-driven recommendations for scaling resources up or down
    based on usage patterns and predictions.
    """
    try:
        recommendations = resource_optimizer.generate_scaling_recommendations()
        
        return {
            "status": "success",
            "recommendations": [r.to_dict() for r in recommendations],
            "total_recommendations": len(recommendations),
            "priority_breakdown": {
                "critical": len([r for r in recommendations if r.priority == "critical"]),
                "high": len([r for r in recommendations if r.priority == "high"]),
                "medium": len([r for r in recommendations if r.priority == "medium"]),
                "low": len([r for r in recommendations if r.priority == "low"])
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


@router.get("/cost-optimization", response_model=Dict[str, Any])
async def get_cost_optimization_analysis() -> Dict[str, Any]:
    """
    Get cost optimization analysis and recommendations.
    
    Analyzes resource usage patterns to identify cost optimization
    opportunities and potential savings.
    """
    try:
        analysis = resource_optimizer.get_cost_optimization_analysis()
        
        return {
            "status": "success",
            "cost_analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze cost optimization: {str(e)}")


# ==================== Resource Analysis Endpoints ====================

@router.get("/analysis/capacity-planning", response_model=Dict[str, Any])
async def get_capacity_planning_analysis() -> Dict[str, Any]:
    """
    Get comprehensive capacity planning analysis.
    
    Combines predictions, bottleneck analysis, and scaling recommendations
    to provide a complete capacity planning overview.
    """
    try:
        # Get predictions for all resources
        predictions = {}
        for resource_type in ["cpu", "memory", "disk"]:
            prediction = resource_predictor.predict_resource_usage(resource_type, 168)  # 7 days
            if prediction:
                predictions[resource_type] = prediction.to_dict()
        
        # Get bottlenecks and recommendations
        bottlenecks = resource_optimizer.analyze_bottlenecks()
        scaling_recommendations = resource_optimizer.generate_scaling_recommendations()
        cost_analysis = resource_optimizer.get_cost_optimization_analysis()
        
        # Generate capacity planning summary
        capacity_status = "healthy"
        critical_issues = []
        
        for bottleneck in bottlenecks:
            if bottleneck.severity == "critical":
                capacity_status = "critical"
                critical_issues.append(f"{bottleneck.resource_type}: {bottleneck.current_usage:.1f}%")
        
        if capacity_status != "critical":
            for resource_type, prediction in predictions.items():
                if prediction["predicted_7d"] > 90:
                    capacity_status = "warning"
                    critical_issues.append(f"{resource_type}: predicted to reach {prediction['predicted_7d']:.1f}% in 7 days")
        
        return {
            "status": "success",
            "capacity_planning": {
                "overall_status": capacity_status,
                "critical_issues": critical_issues,
                "predictions": predictions,
                "current_bottlenecks": [b.to_dict() for b in bottlenecks],
                "scaling_recommendations": [r.to_dict() for r in scaling_recommendations],
                "cost_optimization": cost_analysis,
                "next_review_recommended": (datetime.now() + timedelta(days=7)).isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate capacity planning: {str(e)}")


@router.get("/analysis/performance-impact", response_model=Dict[str, Any])
async def get_performance_impact_analysis() -> Dict[str, Any]:
    """
    Analyze performance impact of current resource usage.
    
    Evaluates how current resource usage patterns affect application
    performance and user experience.
    """
    try:
        current_metrics = resource_monitor.get_current_metrics()
        statistics = resource_monitor.get_resource_statistics(hours=24)
        
        if not current_metrics or "error" in statistics:
            raise HTTPException(status_code=503, detail="Insufficient monitoring data")
        
        performance_impacts = []
        overall_score = 100  # Start with perfect score
        
        # CPU performance impact
        cpu_avg = statistics["cpu"]["average"]
        if cpu_avg > 80:
            impact = {
                "resource": "cpu",
                "impact_level": "high",
                "current_usage": cpu_avg,
                "performance_impact": "Significant response time degradation",
                "user_experience_impact": "Slow page loads, timeouts",
                "score_reduction": 30
            }
            performance_impacts.append(impact)
            overall_score -= 30
        elif cpu_avg > 60:
            impact = {
                "resource": "cpu",
                "impact_level": "medium",
                "current_usage": cpu_avg,
                "performance_impact": "Moderate response time increase",
                "user_experience_impact": "Slightly slower interactions",
                "score_reduction": 15
            }
            performance_impacts.append(impact)
            overall_score -= 15
        
        # Memory performance impact
        memory_avg = statistics["memory"]["average"]
        if memory_avg > 90:
            impact = {
                "resource": "memory",
                "impact_level": "high",
                "current_usage": memory_avg,
                "performance_impact": "Memory pressure, potential swapping",
                "user_experience_impact": "Application instability, crashes",
                "score_reduction": 25
            }
            performance_impacts.append(impact)
            overall_score -= 25
        elif memory_avg > 75:
            impact = {
                "resource": "memory",
                "impact_level": "medium",
                "current_usage": memory_avg,
                "performance_impact": "Increased garbage collection overhead",
                "user_experience_impact": "Occasional slowdowns",
                "score_reduction": 10
            }
            performance_impacts.append(impact)
            overall_score -= 10
        
        # Disk performance impact
        disk_current = current_metrics.disk_percent
        if disk_current > 95:
            impact = {
                "resource": "disk",
                "impact_level": "critical",
                "current_usage": disk_current,
                "performance_impact": "Storage full, write operations failing",
                "user_experience_impact": "Application errors, data loss risk",
                "score_reduction": 40
            }
            performance_impacts.append(impact)
            overall_score -= 40
        elif disk_current > 85:
            impact = {
                "resource": "disk",
                "impact_level": "medium",
                "current_usage": disk_current,
                "performance_impact": "Slower I/O operations",
                "user_experience_impact": "Delayed file operations",
                "score_reduction": 10
            }
            performance_impacts.append(impact)
            overall_score -= 10
        
        # Determine overall performance grade
        if overall_score >= 90:
            performance_grade = "A"
            grade_description = "Excellent performance"
        elif overall_score >= 80:
            performance_grade = "B"
            grade_description = "Good performance"
        elif overall_score >= 70:
            performance_grade = "C"
            grade_description = "Acceptable performance"
        elif overall_score >= 60:
            performance_grade = "D"
            grade_description = "Poor performance"
        else:
            performance_grade = "F"
            grade_description = "Critical performance issues"
        
        return {
            "status": "success",
            "performance_analysis": {
                "overall_score": max(0, overall_score),
                "performance_grade": performance_grade,
                "grade_description": grade_description,
                "impacts": performance_impacts,
                "recommendations": [
                    "Monitor resource usage trends closely",
                    "Implement auto-scaling for peak loads",
                    "Optimize resource-intensive operations",
                    "Set up proactive alerting for resource thresholds"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze performance impact: {str(e)}")


# ==================== Health Check ====================

@router.get("/health", response_model=Dict[str, Any])
async def resource_health() -> Dict[str, Any]:
    """
    Health check for resource optimization service.
    """
    try:
        current_metrics = resource_monitor.get_current_metrics()
        is_monitoring = resource_monitor.is_monitoring
        
        return {
            "status": "healthy",
            "service": "resource_optimization",
            "components": {
                "monitor": "running" if is_monitoring else "stopped",
                "predictor": "available",
                "optimizer": "available",
                "current_metrics": "available" if current_metrics else "unavailable"
            },
            "monitoring_status": {
                "is_active": is_monitoring,
                "collection_interval": resource_monitor.collection_interval,
                "history_size": len(resource_monitor.metrics_history)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "resource_optimization",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }