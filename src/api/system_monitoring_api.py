"""
System Monitoring API Endpoints.

Provides HTTP endpoints for system monitoring, metrics collection,
and Prometheus/Grafana integration.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends, Response
from fastapi.responses import PlainTextResponse, JSONResponse
import time

from src.system.prometheus_integration import (
    prometheus_exporter, 
    start_prometheus_collection,
    stop_prometheus_collection,
    PrometheusConfig
)
from src.system.grafana_dashboards import dashboard_generator
from src.system.monitoring import metrics_collector, performance_monitor, health_monitor
from src.system.business_metrics import business_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus format for scraping.
    
    Returns metrics in the standard Prometheus exposition format
    that can be scraped by Prometheus server.
    """
    try:
        metrics_data = prometheus_exporter.get_metrics()
        
        # Record the metrics request
        prometheus_exporter.record_http_request("GET", "/metrics", 200, 0.001)
        
        return Response(
            content=metrics_data,
            media_type=prometheus_exporter.get_content_type()
        )
    
    except Exception as e:
        logger.error(f"Error serving Prometheus metrics: {e}")
        prometheus_exporter.record_http_request("GET", "/metrics", 500, 0.001)
        raise HTTPException(status_code=500, detail=f"Error serving metrics: {str(e)}")


@router.get("/health")
async def get_system_health():
    """
    Get comprehensive system health status.
    
    Returns detailed health information including system status,
    performance metrics, and predictive analysis.
    """
    try:
        start_time = time.time()
        
        # Get comprehensive health status
        health_status = await health_monitor.check_system_health()
        
        # Add additional context
        health_status.update({
            "timestamp": datetime.now().isoformat(),
            "response_time_ms": (time.time() - start_time) * 1000,
            "metrics_collection_active": prometheus_exporter.is_collecting,
            "business_metrics_active": business_metrics_collector.is_collecting
        })
        
        # Determine HTTP status code based on health
        status_code = 200
        if health_status["overall_status"] == "critical":
            status_code = 503
        elif health_status["overall_status"] == "warning":
            status_code = 200  # Still operational
        
        # Record the health check request
        duration = time.time() - start_time
        prometheus_exporter.record_http_request("GET", "/health", status_code, duration)
        
        return JSONResponse(content=health_status, status_code=status_code)
    
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        prometheus_exporter.record_http_request("GET", "/health", 500, 0.001)
        raise HTTPException(status_code=500, detail=f"Error getting health status: {str(e)}")


@router.get("/status")
async def get_monitoring_status():
    """
    Get monitoring system status and configuration.
    
    Returns information about the monitoring system including
    collection status, configuration, and available metrics.
    """
    try:
        # Get metrics summary
        metrics_summary = metrics_collector.get_all_metrics_summary()
        
        # Get performance summary
        performance_summary = performance_monitor.get_performance_summary()
        
        # Get business metrics summary
        business_summary = business_metrics_collector.get_business_summary()
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": prometheus_exporter.is_collecting,
            "business_metrics_active": business_metrics_collector.is_collecting,
            "configuration": {
                "collection_interval": prometheus_exporter.config.collection_interval,
                "metrics_port": prometheus_exporter.config.metrics_port,
                "system_metrics_enabled": prometheus_exporter.config.enable_system_metrics,
                "business_metrics_enabled": prometheus_exporter.config.enable_business_metrics,
                "performance_metrics_enabled": prometheus_exporter.config.enable_performance_metrics
            },
            "metrics_count": {
                "system_metrics": len([k for k in prometheus_exporter.system_metrics.keys()]),
                "business_metrics": len([k for k in prometheus_exporter.business_metrics.keys()]),
                "performance_metrics": len([k for k in prometheus_exporter.performance_metrics.keys()]),
                "custom_metrics": len([k for k in prometheus_exporter.custom_metrics.keys()])
            },
            "recent_performance": {
                "active_requests": performance_summary.get("active_requests", 0),
                "avg_response_time": performance_summary.get("avg_request_duration", {}).get("latest"),
                "error_rate": performance_summary.get("error_rate", 0)
            },
            "business_metrics": business_summary
        }
        
        return status
    
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.post("/start")
async def start_monitoring(
    config: Optional[Dict[str, Any]] = None
):
    """
    Start monitoring system with optional configuration.
    
    Args:
        config: Optional monitoring configuration parameters
    """
    try:
        # Create config if provided
        prometheus_config = None
        if config:
            prometheus_config = PrometheusConfig(
                metrics_port=config.get("metrics_port", 9090),
                collection_interval=config.get("collection_interval", 15.0),
                enable_system_metrics=config.get("enable_system_metrics", True),
                enable_business_metrics=config.get("enable_business_metrics", True),
                enable_performance_metrics=config.get("enable_performance_metrics", True)
            )
        
        # Start Prometheus collection
        await start_prometheus_collection(prometheus_config)
        
        # Start business metrics collection
        await business_metrics_collector.start_collection()
        
        # Start system metrics collection
        await metrics_collector.start_collection()
        
        return {
            "status": "started",
            "timestamp": datetime.now().isoformat(),
            "message": "Monitoring system started successfully"
        }
    
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting monitoring: {str(e)}")


@router.post("/stop")
async def stop_monitoring():
    """
    Stop monitoring system.
    
    Stops all metrics collection and monitoring processes.
    """
    try:
        # Stop Prometheus collection
        await stop_prometheus_collection()
        
        # Stop business metrics collection
        await business_metrics_collector.stop_collection()
        
        # Stop system metrics collection
        await metrics_collector.stop_collection()
        
        return {
            "status": "stopped",
            "timestamp": datetime.now().isoformat(),
            "message": "Monitoring system stopped successfully"
        }
    
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Error stopping monitoring: {str(e)}")


@router.get("/metrics/summary")
async def get_metrics_summary(
    hours: int = Query(1, ge=1, le=168, description="Number of hours to include in summary")
):
    """
    Get comprehensive metrics summary.
    
    Args:
        hours: Number of hours to include in the summary (1-168)
    
    Returns:
        Comprehensive metrics summary including system, performance,
        and business metrics.
    """
    try:
        # Calculate time range
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        
        # Get metrics summaries
        system_metrics = {}
        for metric_name in ["system.cpu.usage_percent", "system.memory.usage_percent", 
                           "system.disk.usage_percent", "requests.duration"]:
            summary = metrics_collector.get_metric_summary(metric_name, since=start_time)
            if summary["count"] > 0:
                system_metrics[metric_name] = summary
        
        # Get performance summary
        performance_summary = performance_monitor.get_performance_summary()
        
        # Get business summary
        business_summary = business_metrics_collector.get_business_summary()
        
        # Get performance insights
        performance_insights = metrics_collector.get_performance_insights()
        
        return {
            "period": {
                "hours": hours,
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat()
            },
            "system_metrics": system_metrics,
            "performance_summary": performance_summary,
            "business_summary": business_summary,
            "performance_insights": performance_insights,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting summary: {str(e)}")


@router.get("/dashboards")
async def get_dashboard_configs():
    """
    Get Grafana dashboard configurations.
    
    Returns all available dashboard configurations that can be
    imported into Grafana for monitoring visualization.
    """
    try:
        dashboards = dashboard_generator.get_all_dashboards()
        
        # Add metadata
        dashboard_info = {}
        for name, config in dashboards.items():
            dashboard_config = config["dashboard"]
            dashboard_info[name] = {
                "title": dashboard_config["title"],
                "uid": dashboard_config["uid"],
                "tags": dashboard_config.get("tags", []),
                "panels_count": len(dashboard_config.get("panels", [])),
                "refresh": dashboard_config.get("refresh", "30s"),
                "config": config  # Full configuration
            }
        
        return {
            "dashboards": dashboard_info,
            "total_count": len(dashboard_info),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard configs: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboards: {str(e)}")


@router.get("/dashboards/{dashboard_name}")
async def get_dashboard_config(dashboard_name: str):
    """
    Get specific dashboard configuration.
    
    Args:
        dashboard_name: Name of the dashboard to retrieve
    
    Returns:
        Dashboard configuration in Grafana format.
    """
    try:
        dashboards = dashboard_generator.get_all_dashboards()
        
        if dashboard_name not in dashboards:
            raise HTTPException(
                status_code=404, 
                detail=f"Dashboard '{dashboard_name}' not found. Available: {list(dashboards.keys())}"
            )
        
        return dashboards[dashboard_name]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard config for {dashboard_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard: {str(e)}")


@router.post("/metrics/custom")
async def add_custom_metric(
    name: str,
    metric_type: str,
    description: str,
    labelnames: Optional[List[str]] = None
):
    """
    Add a custom metric to the monitoring system.
    
    Args:
        name: Metric name
        metric_type: Type of metric (counter, gauge, histogram, summary)
        description: Metric description
        labelnames: Optional list of label names
    """
    try:
        metric = prometheus_exporter.add_custom_metric(
            name=name,
            metric_type=metric_type,
            description=description,
            labelnames=labelnames or []
        )
        
        return {
            "status": "created",
            "metric_name": name,
            "metric_type": metric_type,
            "description": description,
            "labelnames": labelnames or [],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error adding custom metric {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding metric: {str(e)}")


@router.get("/alerts")
async def get_active_alerts():
    """
    Get active performance alerts.
    
    Returns current performance alerts and health warnings
    from the monitoring system.
    """
    try:
        # Get recent alerts from metrics collector
        recent_alerts = metrics_collector.alerts[-50:]  # Last 50 alerts
        
        # Get health status for current alerts
        health_status = await health_monitor.check_system_health()
        current_alerts = health_status.get("alerts", [])
        
        # Get bottleneck analyses
        bottlenecks = metrics_collector.detect_bottlenecks()
        
        return {
            "current_alerts": current_alerts,
            "recent_alerts": [
                {
                    "metric_name": alert.metric_name,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "timestamp": alert.timestamp,
                    "value": alert.value,
                    "threshold": alert.threshold
                }
                for alert in recent_alerts
            ],
            "bottlenecks": [
                {
                    "component": b.component,
                    "severity": b.severity,
                    "description": b.description,
                    "metrics": b.metrics,
                    "recommendations": b.recommendations,
                    "timestamp": b.timestamp
                }
                for b in bottlenecks
            ],
            "alert_count": len(current_alerts),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting alerts: {str(e)}")


@router.get("/performance/insights")
async def get_performance_insights():
    """
    Get performance insights and recommendations.
    
    Returns comprehensive performance analysis including
    bottleneck detection, trend analysis, and optimization recommendations.
    """
    try:
        # Get performance insights
        insights = metrics_collector.get_performance_insights()
        
        # Get performance summary
        performance_summary = performance_monitor.get_performance_summary()
        
        # Combine insights
        combined_insights = {
            "performance_insights": insights,
            "performance_summary": performance_summary,
            "recommendations": insights.get("recommendations", []) + 
                            performance_summary.get("recommendations", []),
            "timestamp": datetime.now().isoformat()
        }
        
        return combined_insights
    
    except Exception as e:
        logger.error(f"Error getting performance insights: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting insights: {str(e)}")


@router.post("/track/request")
async def track_request_metric(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float
):
    """
    Manually track a request metric.
    
    Args:
        method: HTTP method
        endpoint: Request endpoint
        status_code: Response status code
        duration: Request duration in seconds
    """
    try:
        prometheus_exporter.record_http_request(method, endpoint, status_code, duration)
        
        return {
            "status": "recorded",
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error tracking request metric: {e}")
        raise HTTPException(status_code=500, detail=f"Error tracking request: {str(e)}")


@router.post("/track/database")
async def track_database_metric(
    query_type: str,
    success: bool,
    duration: float
):
    """
    Manually track a database query metric.
    
    Args:
        query_type: Type of database query
        success: Whether the query was successful
        duration: Query duration in seconds
    """
    try:
        prometheus_exporter.record_database_query(query_type, success, duration)
        
        return {
            "status": "recorded",
            "query_type": query_type,
            "success": success,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error tracking database metric: {e}")
        raise HTTPException(status_code=500, detail=f"Error tracking database query: {str(e)}")


@router.post("/track/ai")
async def track_ai_metric(
    model_name: str,
    success: bool,
    duration: float,
    confidence: Optional[float] = None
):
    """
    Manually track an AI inference metric.
    
    Args:
        model_name: Name of the AI model
        success: Whether the inference was successful
        duration: Inference duration in seconds
        confidence: Optional confidence score
    """
    try:
        prometheus_exporter.record_ai_inference(model_name, success, duration, confidence)
        
        return {
            "status": "recorded",
            "model_name": model_name,
            "success": success,
            "duration": duration,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error tracking AI metric: {e}")
        raise HTTPException(status_code=500, detail=f"Error tracking AI inference: {str(e)}")


# Note: Middleware functionality moved to application level
# to avoid router-level middleware issues during testing