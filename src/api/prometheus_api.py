"""
Prometheus API endpoints for Quality Billing System.

Provides HTTP endpoints for Prometheus metrics scraping and
system monitoring integration.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
import asyncio

from ..quality_billing.prometheus_metrics import quality_billing_metrics
from ..quality_billing.prometheus_integration import prometheus_service
from ..quality_billing.system_metrics_collector import system_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prometheus", tags=["prometheus"])


@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus format for scraping.
    
    Returns metrics in the standard Prometheus exposition format
    that can be scraped by Prometheus server.
    """
    try:
        # Export metrics in Prometheus format
        metrics_data = quality_billing_metrics.export_prometheus()
        
        # Record the metrics request
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/metrics", "method": "GET", "status_code": "200"}
        )
        
        return metrics_data
    
    except Exception as e:
        logger.error(f"Error exporting Prometheus metrics: {e}")
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/metrics", "method": "GET", "status_code": "500"}
        )
        
        raise HTTPException(status_code=500, detail=f"Error exporting metrics: {str(e)}")


@router.get("/health")
async def get_health_status():
    """
    Get system health status for monitoring.
    
    Returns comprehensive health information including:
    - Overall system status
    - Metrics collection status
    - Recent performance indicators
    """
    try:
        # Get metrics summary
        metrics_summary = quality_billing_metrics.get_metric_summary(hours=1)
        
        # Get collection task status
        task_status = system_metrics_collector.get_task_status()
        
        # Determine overall health
        active_tasks = sum(1 for task in task_status.values() if task["enabled"])
        total_tasks = len(task_status)
        
        # Check for recent activity
        recent_requests = quality_billing_metrics.get_counter("quality_billing_api_requests_total")
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "collection_tasks_active": active_tasks,
                "collection_tasks_total": total_tasks,
                "recent_api_requests": recent_requests,
                "metrics_collector_running": system_metrics_collector.running
            },
            "summary": metrics_summary,
            "uptime_seconds": _get_uptime_seconds()
        }
        
        # Determine status based on health indicators
        if not system_metrics_collector.running:
            health_status["status"] = "degraded"
            health_status["issues"] = ["Metrics collector not running"]
        elif active_tasks < total_tasks * 0.8:  # Less than 80% of tasks active
            health_status["status"] = "degraded"
            health_status["issues"] = ["Some collection tasks disabled"]
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/health", "method": "GET", "status_code": str(status_code)}
        )
        
        return JSONResponse(content=health_status, status_code=status_code)
    
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting health status: {str(e)}")


@router.get("/config")
async def get_prometheus_config():
    """
    Get Prometheus configuration for the quality billing system.
    
    Returns the complete Prometheus configuration including:
    - Scrape configurations
    - Alert rules
    - Service discovery targets
    """
    try:
        # Get Prometheus service configuration
        config_data = {
            "prometheus_config": await prometheus_service._generate_prometheus_config(),
            "alert_rules": prometheus_service.alert_rules,
            "service_targets": prometheus_service.service_targets,
            "scrape_configs": await prometheus_service._get_scrape_configs()
        }
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/config", "method": "GET", "status_code": "200"}
        )
        
        return config_data
    
    except Exception as e:
        logger.error(f"Error getting Prometheus config: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting config: {str(e)}")


@router.get("/targets")
async def get_service_targets():
    """
    Get service discovery targets for Prometheus.
    
    Returns the list of targets that Prometheus should scrape
    for the quality billing system.
    """
    try:
        targets = {
            "quality_billing_targets": [
                {
                    "targets": [f"localhost:{prometheus_service.config['metrics_port']}"],
                    "labels": {
                        "job": "quality-billing",
                        "service": "quality-billing-loop",
                        "environment": "production",
                        "component": "metrics"
                    }
                }
            ] + prometheus_service.service_targets
        }
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/targets", "method": "GET", "status_code": "200"}
        )
        
        return targets
    
    except Exception as e:
        logger.error(f"Error getting service targets: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting targets: {str(e)}")


@router.post("/reload")
async def reload_prometheus_config():
    """
    Reload Prometheus configuration.
    
    Triggers a reload of the Prometheus configuration file
    and alert rules.
    """
    try:
        # Reload Prometheus configuration
        success = await prometheus_service._reload_prometheus_config()
        
        if success:
            result = {
                "status": "reloaded",
                "timestamp": datetime.now().isoformat(),
                "message": "Prometheus configuration reloaded successfully"
            }
            status_code = 200
        else:
            result = {
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
                "error": "Failed to reload Prometheus configuration"
            }
            status_code = 500
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/reload", "method": "POST", "status_code": str(status_code)}
        )
        
        return JSONResponse(content=result, status_code=status_code)
    
    except Exception as e:
        logger.error(f"Error reloading Prometheus config: {e}")
        raise HTTPException(status_code=500, detail=f"Error reloading config: {str(e)}")


@router.get("/metrics/summary")
async def get_metrics_summary(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to include in summary")
):
    """
    Get a summary of metrics over the specified time period.
    
    Args:
        hours: Number of hours to include in the summary (1-168)
    
    Returns:
        Comprehensive metrics summary including work time, quality,
        billing, performance, and system metrics.
    """
    try:
        summary = quality_billing_metrics.get_metric_summary(hours=hours)
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/metrics/summary", "method": "GET", "status_code": "200"}
        )
        
        return summary
    
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting summary: {str(e)}")


@router.get("/metrics/time-series/{metric_name}")
async def get_metric_time_series(
    metric_name: str,
    start_time: Optional[datetime] = Query(None, description="Start time for time series"),
    end_time: Optional[datetime] = Query(None, description="End time for time series"),
    labels: Optional[str] = Query(None, description="Labels filter (key1=value1,key2=value2)")
):
    """
    Get time series data for a specific metric.
    
    Args:
        metric_name: Name of the metric to retrieve
        start_time: Start time for the time series (optional)
        end_time: End time for the time series (optional)
        labels: Labels filter in key=value format (optional)
    
    Returns:
        Time series data points for the specified metric.
    """
    try:
        # Parse labels if provided
        labels_dict = {}
        if labels:
            for label_pair in labels.split(','):
                if '=' in label_pair:
                    key, value = label_pair.split('=', 1)
                    labels_dict[key.strip()] = value.strip()
        
        # Get time series data
        time_series = quality_billing_metrics.get_time_series(
            metric_name=metric_name,
            labels=labels_dict if labels_dict else None,
            start_time=start_time,
            end_time=end_time
        )
        
        # Convert to JSON-serializable format
        series_data = [
            {
                "timestamp": point.timestamp,
                "value": point.value,
                "labels": point.labels
            }
            for point in time_series
        ]
        
        result = {
            "metric_name": metric_name,
            "labels": labels_dict,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "data_points": len(series_data),
            "series": series_data
        }
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/metrics/time-series", "method": "GET", "status_code": "200"}
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting time series for {metric_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting time series: {str(e)}")


@router.get("/collection/status")
async def get_collection_status():
    """
    Get status of all metrics collection tasks.
    
    Returns information about each collection task including
    whether it's enabled, last run time, and next scheduled run.
    """
    try:
        task_status = system_metrics_collector.get_task_status()
        
        # Add summary information
        summary = {
            "total_tasks": len(task_status),
            "enabled_tasks": sum(1 for task in task_status.values() if task["enabled"]),
            "collector_running": system_metrics_collector.running,
            "last_updated": datetime.now().isoformat()
        }
        
        result = {
            "summary": summary,
            "tasks": task_status
        }
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/collection/status", "method": "GET", "status_code": "200"}
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting collection status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting collection status: {str(e)}")


@router.post("/collection/tasks/{task_name}/enable")
async def enable_collection_task(task_name: str):
    """
    Enable a specific metrics collection task.
    
    Args:
        task_name: Name of the collection task to enable
    """
    try:
        system_metrics_collector.enable_task(task_name)
        
        result = {
            "status": "enabled",
            "task_name": task_name,
            "timestamp": datetime.now().isoformat()
        }
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/collection/tasks/enable", "method": "POST", "status_code": "200"}
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error enabling task {task_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error enabling task: {str(e)}")


@router.post("/collection/tasks/{task_name}/disable")
async def disable_collection_task(task_name: str):
    """
    Disable a specific metrics collection task.
    
    Args:
        task_name: Name of the collection task to disable
    """
    try:
        system_metrics_collector.disable_task(task_name)
        
        result = {
            "status": "disabled",
            "task_name": task_name,
            "timestamp": datetime.now().isoformat()
        }
        
        quality_billing_metrics.inc_counter(
            "quality_billing_api_requests_total",
            1.0,
            {"endpoint": "/collection/tasks/disable", "method": "POST", "status_code": "200"}
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error disabling task {task_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error disabling task: {str(e)}")


def _get_uptime_seconds() -> float:
    """Get service uptime in seconds."""
    # This would typically track actual start time
    # For now, return a placeholder value
    return 3600.0  # 1 hour


# Middleware to record API metrics
@router.middleware("http")
async def record_api_metrics(request, call_next):
    """Middleware to record API request metrics."""
    start_time = asyncio.get_event_loop().time()
    
    try:
        response = await call_next(request)
        
        # Record response time and request count
        response_time = asyncio.get_event_loop().time() - start_time
        
        quality_billing_metrics.record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            response_time_seconds=response_time
        )
        
        return response
    
    except Exception as e:
        # Record error metrics
        response_time = asyncio.get_event_loop().time() - start_time
        
        quality_billing_metrics.record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            response_time_seconds=response_time
        )
        
        raise