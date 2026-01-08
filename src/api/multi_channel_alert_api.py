"""
Multi-Channel Alert Notification API

Provides REST API endpoints for the multi-channel alert notification system,
including alert rule management, notification configuration, and intelligent analysis.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from enum import Enum

from ..monitoring.alert_rule_engine import (
    alert_rule_engine, AlertLevel, AlertCategory, AlertRuleType, AlertPriority, AlertStatus
)
from ..monitoring.multi_channel_notification import (
    multi_channel_notification_system, NotificationChannel, NotificationStatus
)
from ..monitoring.intelligent_alert_analysis import intelligent_alert_analysis_system

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["Multi-Channel Alerts"])


# Pydantic models for API requests/responses

class AlertLevelEnum(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertCategoryEnum(str, Enum):
    SYSTEM = "system"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BUSINESS = "business"
    QUALITY = "quality"
    COST = "cost"


class AlertRuleTypeEnum(str, Enum):
    THRESHOLD = "threshold"
    TREND = "trend"
    ANOMALY = "anomaly"
    COMPOSITE = "composite"
    PATTERN = "pattern"
    FREQUENCY = "frequency"


class NotificationChannelEnum(str, Enum):
    EMAIL = "email"
    WECHAT_WORK = "wechat_work"
    DINGTALK = "dingtalk"
    SMS = "sms"
    WEBHOOK = "webhook"
    PHONE = "phone"


class CreateThresholdRuleRequest(BaseModel):
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    category: AlertCategoryEnum = Field(..., description="Alert category")
    metric_name: str = Field(..., description="Metric name to monitor")
    threshold: float = Field(..., description="Threshold value")
    operator: str = Field("gt", description="Comparison operator (gt, gte, lt, lte, eq, ne)")
    level: AlertLevelEnum = Field(AlertLevelEnum.WARNING, description="Alert level")
    priority: int = Field(2, description="Alert priority (1-5)")
    duration_minutes: int = Field(1, description="Duration before triggering")
    tags: Optional[Dict[str, str]] = Field(None, description="Additional tags")


class CreateCompositeRuleRequest(BaseModel):
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    category: AlertCategoryEnum = Field(..., description="Alert category")
    conditions: List[Dict[str, Any]] = Field(..., description="Rule conditions")
    logic: str = Field("AND", description="Logic operator (AND, OR)")
    level: AlertLevelEnum = Field(AlertLevelEnum.WARNING, description="Alert level")
    priority: int = Field(2, description="Alert priority (1-5)")
    tags: Optional[Dict[str, str]] = Field(None, description="Additional tags")


class CreateNotificationConfigRequest(BaseModel):
    config_name: str = Field(..., description="Configuration name")
    channel: NotificationChannelEnum = Field(..., description="Notification channel")
    recipients: List[str] = Field(..., description="List of recipients")
    alert_levels: Optional[List[AlertLevelEnum]] = Field(None, description="Alert levels to notify")
    alert_categories: Optional[List[AlertCategoryEnum]] = Field(None, description="Alert categories to notify")
    template_id: Optional[str] = Field(None, description="Template ID to use")
    enabled: bool = Field(True, description="Whether configuration is enabled")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Additional conditions")


class ConfigureHandlerRequest(BaseModel):
    channel: NotificationChannelEnum = Field(..., description="Notification channel")
    config: Dict[str, Any] = Field(..., description="Handler configuration")


class EvaluateRulesRequest(BaseModel):
    metrics: Dict[str, Any] = Field(..., description="Current metrics to evaluate")


class AnalyzeAlertsRequest(BaseModel):
    alert_ids: Optional[List[str]] = Field(None, description="Specific alert IDs to analyze")
    time_window_hours: int = Field(1, description="Time window for analysis")
    current_metrics: Optional[Dict[str, Any]] = Field(None, description="Current metrics")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    prediction_horizon_hours: int = Field(4, description="Prediction horizon")


class AlertResponse(BaseModel):
    id: str
    rule_id: str
    category: str
    level: str
    priority: int
    title: str
    message: str
    source: str
    status: str
    created_at: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None


class RuleResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    rule_type: str
    level: str
    priority: int
    enabled: bool
    created_at: str
    updated_at: str


class NotificationResponse(BaseModel):
    id: str
    alert_id: str
    channel: str
    recipient: str
    subject: str
    status: str
    created_at: str
    sent_at: Optional[str] = None


# Alert Rule Management Endpoints

@router.post("/rules/threshold", response_model=RuleResponse)
async def create_threshold_rule(request: CreateThresholdRuleRequest):
    """Create a threshold-based alert rule."""
    try:
        # Convert enum values
        category = AlertCategory(request.category.value)
        level = AlertLevel(request.level.value)
        priority = AlertPriority(request.priority)
        
        rule = alert_rule_engine.create_threshold_rule(
            name=request.name,
            description=request.description,
            category=category,
            metric_name=request.metric_name,
            threshold=request.threshold,
            operator=request.operator,
            level=level,
            priority=priority,
            duration_minutes=request.duration_minutes,
            tags=request.tags or {}
        )
        
        return RuleResponse(**rule.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to create threshold rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/composite", response_model=RuleResponse)
async def create_composite_rule(request: CreateCompositeRuleRequest):
    """Create a composite alert rule."""
    try:
        # Convert enum values
        category = AlertCategory(request.category.value)
        level = AlertLevel(request.level.value)
        priority = AlertPriority(request.priority)
        
        rule = alert_rule_engine.create_composite_rule(
            name=request.name,
            description=request.description,
            category=category,
            conditions=request.conditions,
            logic=request.logic,
            level=level,
            priority=priority,
            tags=request.tags or {}
        )
        
        return RuleResponse(**rule.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to create composite rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", response_model=List[RuleResponse])
async def list_rules(
    category: Optional[AlertCategoryEnum] = None,
    rule_type: Optional[AlertRuleTypeEnum] = None,
    enabled_only: bool = False
):
    """List alert rules with optional filtering."""
    try:
        # Convert enum values if provided
        category_filter = AlertCategory(category.value) if category else None
        rule_type_filter = AlertRuleType(rule_type.value) if rule_type else None
        
        rules = alert_rule_engine.list_rules(
            category=category_filter,
            rule_type=rule_type_filter,
            enabled_only=enabled_only
        )
        
        return [RuleResponse(**rule) for rule in rules]
        
    except Exception as e:
        logger.error(f"Failed to list rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: str):
    """Get a specific alert rule."""
    try:
        rule = alert_rule_engine.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return RuleResponse(**rule.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}/enable")
async def enable_rule(rule_id: str):
    """Enable an alert rule."""
    try:
        success = alert_rule_engine.enable_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"message": "Rule enabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}/disable")
async def disable_rule(rule_id: str):
    """Disable an alert rule."""
    try:
        success = alert_rule_engine.disable_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"message": "Rule disabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete an alert rule."""
    try:
        success = alert_rule_engine.delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {"message": "Rule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Alert Management Endpoints

@router.post("/evaluate", response_model=List[AlertResponse])
async def evaluate_rules(request: EvaluateRulesRequest, background_tasks: BackgroundTasks):
    """Evaluate alert rules against current metrics."""
    try:
        alerts = await alert_rule_engine.evaluate_rules(request.metrics)
        
        # Send notifications in background
        if alerts:
            background_tasks.add_task(send_alert_notifications, alerts)
        
        return [AlertResponse(**alert.to_dict()) for alert in alerts]
        
    except Exception as e:
        logger.error(f"Failed to evaluate rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(
    category: Optional[AlertCategoryEnum] = None,
    level: Optional[AlertLevelEnum] = None,
    limit: int = 100
):
    """Get active alerts."""
    try:
        # Convert enum values if provided
        category_filter = AlertCategory(category.value) if category else None
        level_filter = AlertLevel(level.value) if level else None
        
        alerts = alert_rule_engine.get_active_alerts(
            category=category_filter,
            level=level_filter,
            limit=limit
        )
        
        return [AlertResponse(**alert) for alert in alerts]
        
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str):
    """Acknowledge an alert."""
    try:
        alert_uuid = UUID(alert_id)
        success = await alert_rule_engine.acknowledge_alert(alert_uuid, acknowledged_by)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {"message": "Alert acknowledged successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, resolved_by: str, resolution_notes: Optional[str] = None):
    """Resolve an alert."""
    try:
        alert_uuid = UUID(alert_id)
        success = await alert_rule_engine.resolve_alert(alert_uuid, resolved_by, resolution_notes)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {"message": "Alert resolved successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Notification Configuration Endpoints

@router.post("/notifications/handlers/configure")
async def configure_notification_handler(request: ConfigureHandlerRequest):
    """Configure a notification handler."""
    try:
        channel = NotificationChannel(request.channel.value)
        
        if channel == NotificationChannel.EMAIL:
            multi_channel_notification_system.configure_email_handler(request.config)
        elif channel == NotificationChannel.WECHAT_WORK:
            multi_channel_notification_system.configure_wechat_work_handler(request.config)
        elif channel == NotificationChannel.DINGTALK:
            multi_channel_notification_system.configure_dingtalk_handler(request.config)
        elif channel == NotificationChannel.SMS:
            multi_channel_notification_system.configure_sms_handler(request.config)
        elif channel == NotificationChannel.WEBHOOK:
            multi_channel_notification_system.configure_webhook_handler(request.config)
        elif channel == NotificationChannel.PHONE:
            multi_channel_notification_system.configure_phone_handler(request.config)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported channel: {channel}")
        
        return {"message": f"Handler configured successfully for {channel.value}"}
        
    except Exception as e:
        logger.error(f"Failed to configure handler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/configs")
async def create_notification_config(request: CreateNotificationConfigRequest):
    """Create a notification configuration."""
    try:
        # Convert enum values
        channel = NotificationChannel(request.channel.value)
        alert_levels = [AlertLevel(level.value) for level in request.alert_levels] if request.alert_levels else None
        alert_categories = [AlertCategory(cat.value) for cat in request.alert_categories] if request.alert_categories else None
        
        multi_channel_notification_system.add_notification_config(
            config_name=request.config_name,
            channel=channel,
            recipients=request.recipients,
            alert_levels=alert_levels,
            alert_categories=alert_categories,
            template_id=request.template_id,
            enabled=request.enabled,
            conditions=request.conditions
        )
        
        return {"message": "Notification configuration created successfully"}
        
    except Exception as e:
        logger.error(f"Failed to create notification config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/records", response_model=List[NotificationResponse])
async def list_notification_records(
    alert_id: Optional[str] = None,
    channel: Optional[NotificationChannelEnum] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """List notification records."""
    try:
        # Convert parameters
        alert_uuid = UUID(alert_id) if alert_id else None
        channel_filter = NotificationChannel(channel.value) if channel else None
        status_filter = NotificationStatus(status) if status else None
        
        records = multi_channel_notification_system.list_notification_records(
            alert_id=alert_uuid,
            channel=channel_filter,
            status=status_filter,
            limit=limit
        )
        
        return [NotificationResponse(**record) for record in records]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")
    except Exception as e:
        logger.error(f"Failed to list notification records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notifications/{notification_id}/confirm")
async def confirm_notification(notification_id: str, confirmed_by: str):
    """Confirm notification receipt."""
    try:
        notification_uuid = UUID(notification_id)
        success = await multi_channel_notification_system.confirm_notification(notification_uuid, confirmed_by)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"message": "Notification confirmed successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm notification {notification_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Intelligent Analysis Endpoints

@router.post("/analyze")
async def analyze_alerts(request: AnalyzeAlertsRequest):
    """Perform intelligent alert analysis."""
    try:
        # Get alerts to analyze
        if request.alert_ids:
            # Get specific alerts by ID
            alerts = []
            for alert_id in request.alert_ids:
                alert_uuid = UUID(alert_id)
                alert = alert_rule_engine.active_alerts.get(alert_uuid)
                if alert:
                    alerts.append(alert)
        else:
            # Get recent alerts within time window
            cutoff = datetime.now() - timedelta(hours=request.time_window_hours)
            alerts = [
                alert for alert in alert_rule_engine.active_alerts.values()
                if alert.created_at >= cutoff
            ]
        
        # Perform analysis
        analysis_result = await intelligent_alert_analysis_system.analyze_alerts(
            alerts=alerts,
            current_metrics=request.current_metrics,
            context=request.context,
            prediction_horizon_hours=request.prediction_horizon_hours
        )
        
        return analysis_result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")
    except Exception as e:
        logger.error(f"Failed to analyze alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/patterns")
async def get_alert_patterns(
    pattern_type: Optional[str] = None,
    days: int = 7
):
    """Get alert pattern history."""
    try:
        from ..monitoring.intelligent_alert_analysis import AlertPattern
        
        pattern_filter = AlertPattern(pattern_type) if pattern_type else None
        patterns = intelligent_alert_analysis_system.pattern_recognizer.get_pattern_history(
            pattern_type=pattern_filter,
            days=days
        )
        
        return {"patterns": patterns}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid pattern type: {e}")
    except Exception as e:
        logger.error(f"Failed to get alert patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/root-causes")
async def get_root_cause_analyses(
    category: Optional[str] = None,
    days: int = 30
):
    """Get root cause analysis history."""
    try:
        from ..monitoring.intelligent_alert_analysis import RootCauseCategory
        
        category_filter = RootCauseCategory(category) if category else None
        analyses = intelligent_alert_analysis_system.root_cause_analyzer.get_analysis_history(
            category=category_filter,
            days=days
        )
        
        return {"root_cause_analyses": analyses}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid category: {e}")
    except Exception as e:
        logger.error(f"Failed to get root cause analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/predictions")
async def get_alert_predictions(days: int = 7):
    """Get alert prediction history."""
    try:
        predictions = intelligent_alert_analysis_system.alert_predictor.get_prediction_history(days=days)
        return {"predictions": predictions}
        
    except Exception as e:
        logger.error(f"Failed to get alert predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/prediction-accuracy")
async def get_prediction_accuracy(days: int = 7):
    """Get prediction accuracy metrics."""
    try:
        accuracy = intelligent_alert_analysis_system.alert_predictor.get_prediction_accuracy(days=days)
        return accuracy
        
    except Exception as e:
        logger.error(f"Failed to get prediction accuracy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Statistics and Monitoring Endpoints

@router.get("/statistics/rules")
async def get_rule_statistics():
    """Get alert rule evaluation statistics."""
    try:
        stats = alert_rule_engine.get_evaluation_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get rule statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/notifications")
async def get_notification_statistics(days: int = 7):
    """Get notification statistics."""
    try:
        stats = multi_channel_notification_system.get_notification_statistics(days=days)
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get notification statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/analysis")
async def get_analysis_statistics():
    """Get intelligent analysis statistics."""
    try:
        stats = intelligent_alert_analysis_system.get_analysis_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get analysis statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health Check Endpoint

@router.get("/health")
async def health_check():
    """Health check for the multi-channel alert system."""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "alert_rule_engine": "operational",
                "notification_system": "operational",
                "analysis_system": "operational"
            },
            "statistics": {
                "total_rules": len(alert_rule_engine.rules),
                "active_alerts": len(alert_rule_engine.active_alerts),
                "notification_configs": len(multi_channel_notification_system.notification_configs)
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


# Background task functions

async def send_alert_notifications(alerts):
    """Background task to send notifications for alerts."""
    try:
        for alert in alerts:
            await multi_channel_notification_system.send_alert_notifications(alert)
    except Exception as e:
        logger.error(f"Failed to send alert notifications: {e}")


# Rate limiting configuration endpoint

@router.post("/notifications/rate-limits")
async def configure_rate_limit(
    channel: NotificationChannelEnum,
    max_notifications: int,
    time_window_minutes: int
):
    """Configure rate limiting for a notification channel."""
    try:
        channel_obj = NotificationChannel(channel.value)
        multi_channel_notification_system.set_rate_limit(
            channel=channel_obj,
            max_notifications=max_notifications,
            time_window_minutes=time_window_minutes
        )
        
        return {"message": f"Rate limit configured for {channel.value}"}
        
    except Exception as e:
        logger.error(f"Failed to configure rate limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))