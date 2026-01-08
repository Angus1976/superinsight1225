"""
APM (Application Performance Monitoring) API endpoints.

Provides REST API for:
- Request tracing and distributed tracing
- API performance metrics
- Database query performance
- User experience monitoring
- Business transaction tracking
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from src.system.apm_monitor import apm_monitor, UserExperienceMetrics


router = APIRouter(prefix="/api/v1/apm", tags=["apm"])


# ==================== Request/Response Models ====================

class RecordUserExperienceRequest(BaseModel):
    """Request model for recording user experience metrics."""
    page_url: str = Field(..., description="Page URL")
    user_agent: str = Field(..., description="User agent string")
    page_load_time: float = Field(0.0, ge=0, description="Page load time in seconds")
    dom_content_loaded: float = Field(0.0, ge=0, description="DOM content loaded time")
    first_contentful_paint: float = Field(0.0, ge=0, description="First contentful paint time")
    largest_contentful_paint: float = Field(0.0, ge=0, description="Largest contentful paint time")
    cumulative_layout_shift: float = Field(0.0, ge=0, description="Cumulative layout shift score")
    first_input_delay: float = Field(0.0, ge=0, description="First input delay in ms")
    time_to_interactive: float = Field(0.0, ge=0, description="Time to interactive")
    session_duration: float = Field(0.0, ge=0, description="Session duration")
    error_count: int = Field(0, ge=0, description="Number of errors")


class StartTransactionRequest(BaseModel):
    """Request model for starting a business transaction."""
    transaction_name: str = Field(..., description="Transaction name")
    user_id: Optional[str] = Field(None, description="User ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AddTransactionStepRequest(BaseModel):
    """Request model for adding a transaction step."""
    step_name: str = Field(..., description="Step name")
    duration: float = Field(..., ge=0, description="Step duration in seconds")
    success: bool = Field(True, description="Whether step was successful")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Step metadata")


class FinishTransactionRequest(BaseModel):
    """Request model for finishing a transaction."""
    success: bool = Field(True, description="Whether transaction was successful")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Final metadata")


# ==================== Performance Metrics Endpoints ====================

@router.get("/metrics/api", response_model=Dict[str, Any])
async def get_api_performance_metrics() -> Dict[str, Any]:
    """
    Get API performance metrics summary.
    
    Returns comprehensive API performance data including response times,
    error rates, throughput, and status code distributions.
    """
    try:
        summary = apm_monitor.get_api_performance_summary()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "api_performance": summary
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get API metrics: {str(e)}")


@router.get("/metrics/database", response_model=Dict[str, Any])
async def get_database_performance_metrics() -> Dict[str, Any]:
    """
    Get database performance metrics summary.
    
    Returns database query performance data including execution times,
    slow query counts, and success rates.
    """
    try:
        summary = apm_monitor.get_database_performance_summary()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "database_performance": summary
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database metrics: {str(e)}")


@router.get("/metrics/user-experience", response_model=Dict[str, Any])
async def get_user_experience_metrics() -> Dict[str, Any]:
    """
    Get user experience metrics summary.
    
    Returns Real User Monitoring (RUM) data including Core Web Vitals,
    page load times, and user experience scores.
    """
    try:
        summary = apm_monitor.get_user_experience_summary()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "user_experience": summary
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get UX metrics: {str(e)}")


@router.get("/metrics/transactions", response_model=Dict[str, Any])
async def get_business_transaction_metrics() -> Dict[str, Any]:
    """
    Get business transaction metrics summary.
    
    Returns business transaction performance data including success rates,
    durations, and transaction breakdowns by type.
    """
    try:
        summary = apm_monitor.get_business_transaction_summary()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "business_transactions": summary
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transaction metrics: {str(e)}")


# ==================== Distributed Tracing Endpoints ====================

@router.get("/traces/recent", response_model=Dict[str, Any])
async def get_recent_traces(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of traces")
) -> Dict[str, Any]:
    """
    Get recent distributed traces.
    
    Returns recent completed traces with basic information.
    """
    try:
        traces = apm_monitor.tracer.get_recent_traces(limit)
        
        trace_summaries = []
        for trace_spans in traces:
            if not trace_spans:
                continue
            
            root_span = next((s for s in trace_spans if s.parent_span_id is None), trace_spans[0])
            total_duration = max(s.end_time for s in trace_spans if s.end_time) - min(s.start_time for s in trace_spans)
            error_count = len([s for s in trace_spans if s.status == "error"])
            
            trace_summaries.append({
                "trace_id": root_span.trace_id,
                "operation_name": root_span.operation_name,
                "start_time": root_span.start_time,
                "total_duration": total_duration,
                "span_count": len(trace_spans),
                "error_count": error_count,
                "status": "error" if error_count > 0 else "ok"
            })
        
        return {
            "status": "success",
            "traces": trace_summaries,
            "count": len(trace_summaries)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get traces: {str(e)}")


@router.get("/traces/{trace_id}", response_model=Dict[str, Any])
async def get_trace_details(trace_id: str) -> Dict[str, Any]:
    """
    Get detailed trace analysis.
    
    Returns comprehensive trace information including span hierarchy,
    performance bottlenecks, and detailed timing information.
    """
    try:
        analysis = apm_monitor.get_trace_analysis(trace_id)
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        return {
            "status": "success",
            "trace_analysis": analysis
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trace details: {str(e)}")


# ==================== User Experience Monitoring Endpoints ====================

@router.post("/user-experience", response_model=Dict[str, Any])
async def record_user_experience(request: RecordUserExperienceRequest) -> Dict[str, Any]:
    """
    Record user experience metrics.
    
    Accepts Real User Monitoring (RUM) data from client-side JavaScript
    to track Core Web Vitals and user experience metrics.
    """
    try:
        metrics = UserExperienceMetrics(
            page_url=request.page_url,
            user_agent=request.user_agent,
            page_load_time=request.page_load_time,
            dom_content_loaded=request.dom_content_loaded,
            first_contentful_paint=request.first_contentful_paint,
            largest_contentful_paint=request.largest_contentful_paint,
            cumulative_layout_shift=request.cumulative_layout_shift,
            first_input_delay=request.first_input_delay,
            time_to_interactive=request.time_to_interactive,
            session_duration=request.session_duration,
            error_count=request.error_count
        )
        
        apm_monitor.record_user_experience(metrics)
        
        return {
            "status": "success",
            "message": "User experience metrics recorded"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record UX metrics: {str(e)}")


# ==================== Business Transaction Endpoints ====================

@router.post("/transactions/start", response_model=Dict[str, Any])
async def start_business_transaction(request: StartTransactionRequest) -> Dict[str, Any]:
    """
    Start tracking a business transaction.
    
    Begins monitoring a business-level transaction that may span
    multiple API calls and system components.
    """
    try:
        transaction_id = apm_monitor.start_business_transaction(
            transaction_name=request.transaction_name,
            user_id=request.user_id,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "transaction_id": transaction_id,
            "message": f"Started tracking transaction: {request.transaction_name}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start transaction: {str(e)}")


@router.post("/transactions/{transaction_id}/steps", response_model=Dict[str, Any])
async def add_transaction_step(
    transaction_id: str,
    request: AddTransactionStepRequest
) -> Dict[str, Any]:
    """
    Add a step to a business transaction.
    
    Records a step within a business transaction with timing
    and success information.
    """
    try:
        apm_monitor.add_transaction_step(
            transaction_id=transaction_id,
            step_name=request.step_name,
            duration=request.duration,
            success=request.success,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "message": f"Added step '{request.step_name}' to transaction {transaction_id}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add transaction step: {str(e)}")


@router.post("/transactions/{transaction_id}/finish", response_model=Dict[str, Any])
async def finish_business_transaction(
    transaction_id: str,
    request: FinishTransactionRequest
) -> Dict[str, Any]:
    """
    Finish a business transaction.
    
    Completes tracking of a business transaction and records
    final success status and metadata.
    """
    try:
        apm_monitor.finish_business_transaction(
            transaction_id=transaction_id,
            success=request.success,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "message": f"Finished transaction {transaction_id}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to finish transaction: {str(e)}")


@router.get("/transactions/{transaction_id}", response_model=Dict[str, Any])
async def get_transaction_details(transaction_id: str) -> Dict[str, Any]:
    """
    Get business transaction details.
    
    Returns detailed information about a specific business transaction
    including all steps and performance metrics.
    """
    try:
        if transaction_id not in apm_monitor.business_transactions:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        transaction = apm_monitor.business_transactions[transaction_id]
        
        return {
            "status": "success",
            "transaction": transaction
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transaction: {str(e)}")


# ==================== Performance Analysis Endpoints ====================

@router.get("/analysis/bottlenecks", response_model=Dict[str, Any])
async def get_performance_bottlenecks() -> Dict[str, Any]:
    """
    Get performance bottleneck analysis.
    
    Returns analysis of current performance bottlenecks across
    API endpoints, database queries, and user experience.
    """
    try:
        api_summary = apm_monitor.get_api_performance_summary()
        db_summary = apm_monitor.get_database_performance_summary()
        ux_summary = apm_monitor.get_user_experience_summary()
        
        bottlenecks = []
        
        # Analyze API bottlenecks
        for endpoint, metrics in api_summary.get("endpoints", {}).items():
            if metrics["avg_response_time"] > 2.0:  # Slow endpoint
                bottlenecks.append({
                    "type": "api_endpoint",
                    "component": endpoint,
                    "issue": "slow_response_time",
                    "value": metrics["avg_response_time"],
                    "threshold": 2.0,
                    "severity": "high" if metrics["avg_response_time"] > 5.0 else "medium"
                })
            
            if metrics["error_rate"] > 0.05:  # High error rate
                bottlenecks.append({
                    "type": "api_endpoint",
                    "component": endpoint,
                    "issue": "high_error_rate",
                    "value": metrics["error_rate"],
                    "threshold": 0.05,
                    "severity": "critical"
                })
        
        # Analyze database bottlenecks
        for query, metrics in db_summary.get("queries", {}).items():
            if metrics["avg_execution_time"] > 1.0:  # Slow query
                bottlenecks.append({
                    "type": "database_query",
                    "component": query,
                    "issue": "slow_execution",
                    "value": metrics["avg_execution_time"],
                    "threshold": 1.0,
                    "severity": "high" if metrics["avg_execution_time"] > 3.0 else "medium"
                })
        
        # Analyze UX bottlenecks
        if ux_summary.get("avg_page_load_time", 0) > 3.0:
            bottlenecks.append({
                "type": "user_experience",
                "component": "page_load",
                "issue": "slow_page_load",
                "value": ux_summary["avg_page_load_time"],
                "threshold": 3.0,
                "severity": "medium"
            })
        
        if ux_summary.get("core_web_vitals_score", 100) < 75:
            bottlenecks.append({
                "type": "user_experience",
                "component": "core_web_vitals",
                "issue": "poor_cwv_score",
                "value": ux_summary["core_web_vitals_score"],
                "threshold": 75,
                "severity": "medium"
            })
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "bottlenecks": bottlenecks,
            "total_issues": len(bottlenecks),
            "severity_breakdown": {
                "critical": len([b for b in bottlenecks if b["severity"] == "critical"]),
                "high": len([b for b in bottlenecks if b["severity"] == "high"]),
                "medium": len([b for b in bottlenecks if b["severity"] == "medium"])
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze bottlenecks: {str(e)}")


@router.get("/analysis/recommendations", response_model=Dict[str, Any])
async def get_performance_recommendations() -> Dict[str, Any]:
    """
    Get performance optimization recommendations.
    
    Returns actionable recommendations for improving application
    performance based on current metrics and analysis.
    """
    try:
        api_summary = apm_monitor.get_api_performance_summary()
        db_summary = apm_monitor.get_database_performance_summary()
        ux_summary = apm_monitor.get_user_experience_summary()
        
        recommendations = []
        
        # API recommendations
        for endpoint, metrics in api_summary.get("endpoints", {}).items():
            if metrics["avg_response_time"] > 2.0:
                recommendations.append({
                    "category": "api_performance",
                    "priority": "high",
                    "title": f"Optimize slow endpoint: {endpoint}",
                    "description": f"Endpoint has average response time of {metrics['avg_response_time']:.2f}s",
                    "suggestions": [
                        "Add caching for frequently accessed data",
                        "Optimize database queries",
                        "Consider request batching",
                        "Review business logic efficiency"
                    ]
                })
            
            if metrics["error_rate"] > 0.05:
                recommendations.append({
                    "category": "reliability",
                    "priority": "critical",
                    "title": f"Fix high error rate: {endpoint}",
                    "description": f"Endpoint has error rate of {metrics['error_rate']:.1%}",
                    "suggestions": [
                        "Review error logs for common failure patterns",
                        "Add input validation and error handling",
                        "Implement circuit breaker pattern",
                        "Add monitoring and alerting"
                    ]
                })
        
        # Database recommendations
        for query, metrics in db_summary.get("queries", {}).items():
            if metrics["avg_execution_time"] > 1.0:
                recommendations.append({
                    "category": "database_performance",
                    "priority": "high",
                    "title": f"Optimize slow query: {query}",
                    "description": f"Query has average execution time of {metrics['avg_execution_time']:.2f}s",
                    "suggestions": [
                        "Add database indexes for frequently queried columns",
                        "Optimize query structure and joins",
                        "Consider query result caching",
                        "Review data model for normalization issues"
                    ]
                })
            
            if metrics["slow_query_count"] > 10:
                recommendations.append({
                    "category": "database_performance",
                    "priority": "medium",
                    "title": f"Multiple slow queries detected: {query}",
                    "description": f"Query type has {metrics['slow_query_count']} slow executions",
                    "suggestions": [
                        "Implement query performance monitoring",
                        "Set up slow query logging",
                        "Consider connection pooling optimization",
                        "Review query patterns for optimization opportunities"
                    ]
                })
        
        # UX recommendations
        if ux_summary.get("avg_page_load_time", 0) > 3.0:
            recommendations.append({
                "category": "user_experience",
                "priority": "medium",
                "title": "Improve page load performance",
                "description": f"Average page load time is {ux_summary['avg_page_load_time']:.2f}s",
                "suggestions": [
                    "Optimize images and static assets",
                    "Implement lazy loading for non-critical content",
                    "Use CDN for static asset delivery",
                    "Minimize and compress JavaScript/CSS files"
                ]
            })
        
        if ux_summary.get("core_web_vitals_score", 100) < 75:
            recommendations.append({
                "category": "user_experience",
                "priority": "medium",
                "title": "Improve Core Web Vitals",
                "description": f"Core Web Vitals score is {ux_summary['core_web_vitals_score']:.1f}/100",
                "suggestions": [
                    "Optimize Largest Contentful Paint (LCP) by improving server response times",
                    "Reduce First Input Delay (FID) by minimizing JavaScript execution",
                    "Improve Cumulative Layout Shift (CLS) by setting dimensions for images",
                    "Implement performance budgets and monitoring"
                ]
            })
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "priority_breakdown": {
                "critical": len([r for r in recommendations if r["priority"] == "critical"]),
                "high": len([r for r in recommendations if r["priority"] == "high"]),
                "medium": len([r for r in recommendations if r["priority"] == "medium"])
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


# ==================== Health Check ====================

@router.get("/health", response_model=Dict[str, Any])
async def apm_health() -> Dict[str, Any]:
    """
    Health check for APM service.
    """
    try:
        api_summary = apm_monitor.get_api_performance_summary()
        db_summary = apm_monitor.get_database_performance_summary()
        
        return {
            "status": "healthy",
            "service": "apm",
            "components": {
                "tracer": "available",
                "api_metrics": f"{api_summary['total_endpoints']} endpoints tracked",
                "db_metrics": f"{db_summary['total_query_types']} query types tracked",
                "user_metrics": f"{len(apm_monitor.user_metrics)} sessions recorded"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "apm",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }