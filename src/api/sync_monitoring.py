"""
Data Sync System Monitoring API.

Provides comprehensive monitoring endpoints for the data synchronization system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
import json

from ..sync.monitoring.sync_metrics import sync_metrics
from ..sync.monitoring.alert_rules import sync_alert_manager, AlertSeverity, AlertCategory
from ..sync.monitoring.notification_service import notification_service
from ..sync.monitoring.grafana_integration import grafana_service
from ..utils.auth import get_current_user
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sync/monitoring", tags=["sync-monitoring"])


# Pydantic models
class MetricQuery(BaseModel):
    """Metric query parameters."""
    metric_name: str
    labels: Optional[Dict[str, str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class AlertRuleCreate(BaseModel):
    """Alert rule creation model."""
    name: str
    description: str
    metric: str
    condition: str
    threshold: float
    severity: AlertSeverity
    category: AlertCategory
    duration_seconds: int = 0
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class NotificationRuleCreate(BaseModel):
    """Notification rule creation model."""
    name: str
    channels: List[str]
    conditions: Dict[str, Any]
    priority: str = "normal"
    enabled: bool = True
    escalation_delay: Optional[int] = None
    max_frequency: Optional[int] = None


class DashboardConfig(BaseModel):
    """Dashboard configuration model."""
    grafana_url: str
    api_key: str
    prometheus_url: str = "http://localhost:9090"


# Metrics endpoints
@router.get("/metrics")
async def get_all_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all current metrics."""
    try:
        return sync_metrics.get_all_metrics()
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/metrics/prometheus")
async def get_prometheus_metrics(
    current_user: User = Depends(get_current_user)
) -> str:
    """Get metrics in Prometheus format."""
    try:
        return sync_metrics.export_prometheus()
    except Exception as e:
        logger.error(f"Failed to export Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to export metrics")


@router.get("/metrics/throughput")
async def get_throughput_stats(
    window_seconds: int = Query(60, ge=1, le=3600),
    current_user: User = Depends(get_current_user)
) -> Dict[str, float]:
    """Get throughput statistics for the specified time window."""
    try:
        return sync_metrics.get_throughput_stats(window_seconds)
    except Exception as e:
        logger.error(f"Failed to get throughput stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get throughput statistics")


@router.get("/metrics/latency")
async def get_latency_percentiles(
    metric_name: str = Query("sync_latency_seconds"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, float]:
    """Get latency percentiles."""
    try:
        return sync_metrics.get_latency_percentiles(metric_name)
    except Exception as e:
        logger.error(f"Failed to get latency percentiles: {e}")
        raise HTTPException(status_code=500, detail="Failed to get latency statistics")


@router.post("/metrics/query")
async def query_metrics(
    query: MetricQuery,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Query specific metrics with filters."""
    try:
        # Get metric value
        if query.metric_name.endswith("_total"):
            value = sync_metrics.get_counter(query.metric_name, query.labels)
        else:
            value = sync_metrics.get_gauge(query.metric_name, query.labels)
        
        return {
            "metric": query.metric_name,
            "value": value,
            "labels": query.labels or {},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to query metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to query metrics")


# Alert endpoints
@router.get("/alerts")
async def get_active_alerts(
    severity: Optional[AlertSeverity] = None,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get active alerts, optionally filtered by severity."""
    try:
        alerts = sync_alert_manager.get_active_alerts(severity)
        return [
            {
                "rule_name": alert.rule_name,
                "severity": alert.severity,
                "category": alert.category,
                "message": alert.message,
                "value": alert.value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp,
                "labels": alert.labels,
                "acknowledged": alert.acknowledged
            }
            for alert in alerts
        ]
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.get("/alerts/summary")
async def get_alert_summary(
    current_user: User = Depends(get_current_user)
) -> Dict[str, int]:
    """Get alert summary by severity."""
    try:
        return sync_alert_manager.get_alert_summary()
    except Exception as e:
        logger.error(f"Failed to get alert summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert summary")


@router.post("/alerts/acknowledge/{rule_name}")
async def acknowledge_alert(
    rule_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Acknowledge an active alert."""
    try:
        sync_alert_manager.acknowledge_alert(rule_name)
        notification_service.acknowledge_alert(rule_name)
        return {"status": "acknowledged", "rule_name": rule_name}
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/alerts/rules")
async def get_alert_rules(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get all alert rules."""
    try:
        return [
            {
                "name": rule.name,
                "description": rule.description,
                "metric": rule.metric,
                "condition": rule.condition,
                "threshold": rule.threshold,
                "severity": rule.severity,
                "category": rule.category,
                "duration_seconds": rule.duration_seconds,
                "labels": rule.labels,
                "annotations": rule.annotations,
                "enabled": rule.enabled
            }
            for rule in sync_alert_manager.rules.values()
        ]
    except Exception as e:
        logger.error(f"Failed to get alert rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alert rules")


@router.post("/alerts/rules")
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Create a new alert rule."""
    try:
        from ..sync.monitoring.alert_rules import AlertRule
        
        rule = AlertRule(
            name=rule_data.name,
            description=rule_data.description,
            metric=rule_data.metric,
            condition=rule_data.condition,
            threshold=rule_data.threshold,
            severity=rule_data.severity,
            category=rule_data.category,
            duration_seconds=rule_data.duration_seconds,
            labels=rule_data.labels,
            annotations=rule_data.annotations,
            enabled=rule_data.enabled
        )
        
        sync_alert_manager.add_rule(rule)
        return {"status": "created", "rule_name": rule.name}
    except Exception as e:
        logger.error(f"Failed to create alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert rule")


@router.put("/alerts/rules/{rule_name}/enable")
async def enable_alert_rule(
    rule_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Enable an alert rule."""
    try:
        sync_alert_manager.enable_rule(rule_name)
        return {"status": "enabled", "rule_name": rule_name}
    except Exception as e:
        logger.error(f"Failed to enable alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable alert rule")


@router.put("/alerts/rules/{rule_name}/disable")
async def disable_alert_rule(
    rule_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Disable an alert rule."""
    try:
        sync_alert_manager.disable_rule(rule_name)
        return {"status": "disabled", "rule_name": rule_name}
    except Exception as e:
        logger.error(f"Failed to disable alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable alert rule")


@router.delete("/alerts/rules/{rule_name}")
async def delete_alert_rule(
    rule_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete an alert rule."""
    try:
        sync_alert_manager.remove_rule(rule_name)
        return {"status": "deleted", "rule_name": rule_name}
    except Exception as e:
        logger.error(f"Failed to delete alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete alert rule")


# Notification endpoints
@router.get("/notifications/stats")
async def get_notification_stats(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get notification statistics."""
    try:
        return notification_service.get_notification_stats()
    except Exception as e:
        logger.error(f"Failed to get notification stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notification statistics")


@router.post("/notifications/rules")
async def create_notification_rule(
    rule_data: NotificationRuleCreate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Create a new notification rule."""
    try:
        from ..sync.monitoring.notification_service import NotificationRule, NotificationChannel, NotificationPriority
        
        channels = [NotificationChannel(ch) for ch in rule_data.channels]
        priority = NotificationPriority(rule_data.priority)
        
        rule = NotificationRule(
            name=rule_data.name,
            channels=channels,
            conditions=rule_data.conditions,
            priority=priority,
            enabled=rule_data.enabled,
            escalation_delay=rule_data.escalation_delay,
            max_frequency=rule_data.max_frequency
        )
        
        notification_service.add_rule(rule)
        return {"status": "created", "rule_name": rule.name}
    except Exception as e:
        logger.error(f"Failed to create notification rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create notification rule")


@router.post("/notifications/test")
async def test_notification(
    channel: str,
    recipient: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Send a test notification."""
    try:
        test_alert = {
            "rule_name": "test_alert",
            "severity": "info",
            "category": "test",
            "message": "This is a test notification from the sync monitoring system",
            "value": 1,
            "threshold": 0,
            "timestamp": datetime.now().isoformat(),
            "labels": {"test": "true"}
        }
        
        await notification_service.process_alert(test_alert)
        return {"status": "sent", "channel": channel, "recipient": recipient}
    except Exception as e:
        logger.error(f"Failed to send test notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test notification")


# Dashboard endpoints
@router.post("/dashboards/deploy")
async def deploy_dashboards(
    config: DashboardConfig,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Deploy Grafana dashboards."""
    try:
        if not grafana_service:
            from ..sync.monitoring.grafana_integration import initialize_grafana_integration
            initialize_grafana_integration(
                config.grafana_url,
                config.api_key,
                config.prometheus_url
            )
        
        # Deploy dashboards in background
        background_tasks.add_task(deploy_dashboards_task)
        
        return {"status": "deploying", "message": "Dashboard deployment started"}
    except Exception as e:
        logger.error(f"Failed to deploy dashboards: {e}")
        raise HTTPException(status_code=500, detail="Failed to deploy dashboards")


@router.get("/dashboards/urls")
async def get_dashboard_urls(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Get URLs for deployed dashboards."""
    try:
        if not grafana_service:
            return {"error": "Grafana service not configured"}
        
        urls = await grafana_service.get_dashboard_urls()
        return urls
    except Exception as e:
        logger.error(f"Failed to get dashboard URLs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard URLs")


# Health and status endpoints
@router.get("/health")
async def get_monitoring_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get monitoring system health."""
    try:
        # Check various components
        health_status = {
            "metrics_collector": "healthy",
            "alert_manager": "healthy",
            "notification_service": "healthy",
            "grafana_integration": "unknown"
        }
        
        # Check Grafana connection if configured
        if grafana_service:
            try:
                from ..sync.monitoring.grafana_integration import GrafanaClient
                async with GrafanaClient(grafana_service.grafana_url, grafana_service.api_key) as client:
                    await client.get_health()
                health_status["grafana_integration"] = "healthy"
            except Exception:
                health_status["grafana_integration"] = "unhealthy"
        
        overall_status = "healthy" if all(
            status in ["healthy", "unknown"] for status in health_status.values()
        ) else "degraded"
        
        return {
            "status": overall_status,
            "components": health_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get monitoring health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitoring health")


@router.get("/status")
async def get_monitoring_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive monitoring status."""
    try:
        # Get metrics summary
        throughput = sync_metrics.get_throughput_stats(300)  # 5 minutes
        latency = sync_metrics.get_latency_percentiles()
        
        # Get alert summary
        alert_summary = sync_alert_manager.get_alert_summary()
        
        # Get notification stats
        notification_stats = notification_service.get_notification_stats()
        
        return {
            "throughput": throughput,
            "latency": latency,
            "alerts": alert_summary,
            "notifications": notification_stats,
            "active_jobs": sync_metrics.get_gauge("sync_active_jobs"),
            "queue_depth": sync_metrics.get_gauge("sync_queue_depth"),
            "active_connections": sync_metrics.get_gauge("sync_active_connections"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitoring status")


# Background tasks
async def deploy_dashboards_task():
    """Background task to deploy Grafana dashboards."""
    try:
        if grafana_service:
            await grafana_service.initialize()
            await grafana_service.deploy_dashboards()
            logger.info("Dashboards deployed successfully")
    except Exception as e:
        logger.error(f"Failed to deploy dashboards: {e}")


# Metrics collection endpoint for Prometheus scraping
@router.get("/metrics/export", response_class=str)
async def export_metrics_for_prometheus():
    """Export metrics in Prometheus format for scraping."""
    try:
        return sync_metrics.export_prometheus()
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to export metrics")


# Real-time metrics streaming (WebSocket would be better, but this is a simple polling endpoint)
@router.get("/metrics/realtime")
async def get_realtime_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get real-time metrics snapshot."""
    try:
        return {
            "timestamp": datetime.now().isoformat(),
            "throughput": sync_metrics.get_throughput_stats(60),
            "latency": sync_metrics.get_latency_percentiles(),
            "active_jobs": sync_metrics.get_gauge("sync_active_jobs"),
            "queue_depth": sync_metrics.get_gauge("sync_queue_depth"),
            "error_rate": sync_metrics.get_counter("sync_errors_total") / max(sync_metrics.get_counter("sync_operations_total"), 1),
            "active_connections": sync_metrics.get_gauge("sync_active_connections"),
            "websocket_connections": sync_metrics.get_gauge("websocket_active_connections")
        }
    except Exception as e:
        logger.error(f"Failed to get real-time metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get real-time metrics")


# Configuration endpoints
@router.post("/config/grafana")
async def configure_grafana(
    config: DashboardConfig,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Configure Grafana integration."""
    try:
        from ..sync.monitoring.grafana_integration import initialize_grafana_integration
        
        global grafana_service
        grafana_service = initialize_grafana_integration(
            config.grafana_url,
            config.api_key,
            config.prometheus_url
        )
        
        return {"status": "configured", "grafana_url": config.grafana_url}
    except Exception as e:
        logger.error(f"Failed to configure Grafana: {e}")
        raise HTTPException(status_code=500, detail="Failed to configure Grafana")


@router.post("/config/notifications/email")
async def configure_email_notifications(
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    from_email: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Configure email notifications."""
    try:
        from ..sync.monitoring.notification_service import setup_email_notifications
        
        setup_email_notifications(smtp_host, smtp_port, username, password, from_email)
        return {"status": "configured", "channel": "email"}
    except Exception as e:
        logger.error(f"Failed to configure email notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to configure email notifications")


@router.post("/config/notifications/slack")
async def configure_slack_notifications(
    webhook_url: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Configure Slack notifications."""
    try:
        from ..sync.monitoring.notification_service import setup_slack_notifications
        
        setup_slack_notifications(webhook_url)
        return {"status": "configured", "channel": "slack"}
    except Exception as e:
        logger.error(f"Failed to configure Slack notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to configure Slack notifications")