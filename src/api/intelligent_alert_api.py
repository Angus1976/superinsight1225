"""
智能告警系统 API

提供告警规则管理、告警查询、通知配置等 REST API 接口。
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
import logging

from ..quality_billing.intelligent_alert_system import (
    IntelligentAlertSystem,
    AlertDimension,
    AlertLevel,
    AlertRuleType,
    AlertPriority,
    AlertStatus
)
from ..quality_billing.alert_notification_system import (
    AlertNotificationSystem,
    NotificationChannel,
    NotificationStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["智能告警"])

# 全局实例
alert_system = IntelligentAlertSystem()
notification_system = AlertNotificationSystem()


@router.post("/rules/quality")
async def create_quality_alert_rule(
    name: str = Body(..., description="规则名称"),
    quality_threshold: float = Body(0.8, description="质量阈值"),
    trend_window: int = Body(10, description="趋势窗口大小"),
    level: AlertLevel = Body(AlertLevel.WARNING, description="告警级别")
):
    """创建质量告警规则"""
    try:
        rule = alert_system.rule_engine.create_quality_alert_rule(
            name=name,
            quality_threshold=quality_threshold,
            trend_window=trend_window,
            level=level
        )
        
        return {
            "success": True,
            "message": "质量告警规则创建成功",
            "data": rule.to_dict()
        }
    except Exception as e:
        logger.error(f"Failed to create quality alert rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/efficiency")
async def create_efficiency_alert_rule(
    name: str = Body(..., description="规则名称"),
    efficiency_threshold: float = Body(0.7, description="效率阈值"),
    workload_threshold: int = Body(100, description="工作负载阈值"),
    level: AlertLevel = Body(AlertLevel.WARNING, description="告警级别")
):
    """创建效率告警规则"""
    try:
        rule = alert_system.rule_engine.create_efficiency_alert_rule(
            name=name,
            efficiency_threshold=efficiency_threshold,
            workload_threshold=workload_threshold,
            level=level
        )
        
        return {
            "success": True,
            "message": "效率告警规则创建成功",
            "data": rule.to_dict()
        }
    except Exception as e:
        logger.error(f"Failed to create efficiency alert rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/cost")
async def create_cost_alert_rule(
    name: str = Body(..., description="规则名称"),
    cost_threshold: float = Body(1000.0, description="成本阈值"),
    budget_percentage: float = Body(0.8, description="预算百分比"),
    level: AlertLevel = Body(AlertLevel.HIGH, description="告警级别")
):
    """创建成本告警规则"""
    try:
        rule = alert_system.rule_engine.create_cost_alert_rule(
            name=name,
            cost_threshold=cost_threshold,
            budget_percentage=budget_percentage,
            level=level
        )
        
        return {
            "success": True,
            "message": "成本告警规则创建成功",
            "data": rule.to_dict()
        }
    except Exception as e:
        logger.error(f"Failed to create cost alert rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/anomaly")
async def create_anomaly_detection_rule(
    name: str = Body(..., description="规则名称"),
    metric_name: str = Body(..., description="指标名称"),
    dimension: AlertDimension = Body(..., description="告警维度"),
    sensitivity: float = Body(2.0, description="敏感度"),
    level: AlertLevel = Body(AlertLevel.WARNING, description="告警级别")
):
    """创建异常检测规则"""
    try:
        rule = alert_system.rule_engine.create_anomaly_detection_rule(
            name=name,
            metric_name=metric_name,
            dimension=dimension,
            sensitivity=sensitivity,
            level=level
        )
        
        return {
            "success": True,
            "message": "异常检测规则创建成功",
            "data": rule.to_dict()
        }
    except Exception as e:
        logger.error(f"Failed to create anomaly detection rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules")
async def list_alert_rules(
    dimension: Optional[AlertDimension] = Query(None, description="按维度过滤"),
    enabled_only: bool = Query(False, description="仅显示启用的规则")
):
    """列出告警规则"""
    try:
        rules = alert_system.rule_engine.list_rules(
            dimension=dimension,
            enabled_only=enabled_only
        )
        
        return {
            "success": True,
            "message": "获取告警规则成功",
            "data": rules,
            "total": len(rules)
        }
    except Exception as e:
        logger.error(f"Failed to list alert rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}")
async def get_alert_rule(rule_id: str):
    """获取告警规则详情"""
    try:
        rule = alert_system.rule_engine.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        
        return {
            "success": True,
            "message": "获取告警规则成功",
            "data": rule.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: str,
    updates: Dict[str, Any] = Body(..., description="更新内容")
):
    """更新告警规则"""
    try:
        success = alert_system.rule_engine.update_rule(rule_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        
        return {
            "success": True,
            "message": "告警规则更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alert rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """删除告警规则"""
    try:
        success = alert_system.rule_engine.delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        
        return {
            "success": True,
            "message": "告警规则删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete alert rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-metrics")
async def process_metrics(
    metrics: Dict[str, Any] = Body(..., description="指标数据")
):
    """处理指标并生成告警"""
    try:
        alerts = await alert_system.process_metrics(metrics)
        
        # 发送通知
        notifications = []
        for alert in alerts:
            alert_notifications = await notification_system.send_alert_notifications(alert)
            notifications.extend(alert_notifications)
        
        return {
            "success": True,
            "message": "指标处理完成",
            "data": {
                "alerts_generated": len(alerts),
                "notifications_sent": len(notifications),
                "alerts": [alert.to_dict() for alert in alerts]
            }
        }
    except Exception as e:
        logger.error(f"Failed to process metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_alerts(
    dimension: Optional[AlertDimension] = Query(None, description="按维度过滤"),
    level: Optional[AlertLevel] = Query(None, description="按级别过滤"),
    limit: int = Query(100, description="返回数量限制")
):
    """获取活跃告警"""
    try:
        alerts = alert_system.get_active_alerts(
            dimension=dimension,
            level=level,
            limit=limit
        )
        
        return {
            "success": True,
            "message": "获取活跃告警成功",
            "data": alerts,
            "total": len(alerts)
        }
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/acknowledge/{alert_id}")
async def acknowledge_alert(
    alert_id: UUID,
    acknowledged_by: str = Body(..., description="确认人")
):
    """确认告警"""
    try:
        success = await alert_system.acknowledge_alert(alert_id, acknowledged_by)
        if not success:
            raise HTTPException(status_code=404, detail="告警不存在或已处理")
        
        return {
            "success": True,
            "message": "告警确认成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve/{alert_id}")
async def resolve_alert(
    alert_id: UUID,
    resolved_by: str = Body(..., description="解决人"),
    resolution_notes: Optional[str] = Body(None, description="解决备注")
):
    """解决告警"""
    try:
        success = await alert_system.resolve_alert(alert_id, resolved_by, resolution_notes)
        if not success:
            raise HTTPException(status_code=404, detail="告警不存在")
        
        return {
            "success": True,
            "message": "告警解决成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_alert_statistics(
    days: int = Query(7, description="统计天数")
):
    """获取告警统计"""
    try:
        stats = alert_system.get_alert_statistics(days=days)
        
        return {
            "success": True,
            "message": "获取告警统计成功",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get alert statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 通知配置相关接口

@router.post("/notifications/config")
async def add_notification_config(
    config_name: str = Body(..., description="配置名称"),
    channel: NotificationChannel = Body(..., description="通知渠道"),
    recipients: List[str] = Body(..., description="接收者列表"),
    alert_levels: Optional[List[AlertLevel]] = Body(None, description="告警级别过滤"),
    alert_dimensions: Optional[List[AlertDimension]] = Body(None, description="告警维度过滤"),
    template_id: Optional[str] = Body(None, description="模板ID"),
    enabled: bool = Body(True, description="是否启用")
):
    """添加通知配置"""
    try:
        notification_system.add_notification_config(
            config_name=config_name,
            channel=channel,
            recipients=recipients,
            alert_levels=alert_levels,
            alert_dimensions=alert_dimensions,
            template_id=template_id,
            enabled=enabled
        )
        
        return {
            "success": True,
            "message": "通知配置添加成功"
        }
    except Exception as e:
        logger.error(f"Failed to add notification config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/handlers/email")
async def configure_email_handler(
    config: Dict[str, Any] = Body(..., description="邮件配置")
):
    """配置邮件处理器"""
    try:
        notification_system.configure_email_handler(config)
        
        return {
            "success": True,
            "message": "邮件处理器配置成功"
        }
    except Exception as e:
        logger.error(f"Failed to configure email handler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/handlers/wechat-work")
async def configure_wechat_work_handler(
    config: Dict[str, Any] = Body(..., description="企业微信配置")
):
    """配置企业微信处理器"""
    try:
        notification_system.configure_wechat_work_handler(config)
        
        return {
            "success": True,
            "message": "企业微信处理器配置成功"
        }
    except Exception as e:
        logger.error(f"Failed to configure WeChat Work handler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/handlers/dingtalk")
async def configure_dingtalk_handler(
    config: Dict[str, Any] = Body(..., description="钉钉配置")
):
    """配置钉钉处理器"""
    try:
        notification_system.configure_dingtalk_handler(config)
        
        return {
            "success": True,
            "message": "钉钉处理器配置成功"
        }
    except Exception as e:
        logger.error(f"Failed to configure DingTalk handler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/handlers/webhook")
async def configure_webhook_handler(
    config: Dict[str, Any] = Body(..., description="Webhook配置")
):
    """配置Webhook处理器"""
    try:
        notification_system.configure_webhook_handler(config)
        
        return {
            "success": True,
            "message": "Webhook处理器配置成功"
        }
    except Exception as e:
        logger.error(f"Failed to configure webhook handler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/rate-limit")
async def set_notification_rate_limit(
    channel: NotificationChannel = Body(..., description="通知渠道"),
    max_notifications: int = Body(..., description="最大通知数"),
    time_window_minutes: int = Body(..., description="时间窗口(分钟)")
):
    """设置通知限流"""
    try:
        notification_system.set_rate_limit(
            channel=channel,
            max_notifications=max_notifications,
            time_window_minutes=time_window_minutes
        )
        
        return {
            "success": True,
            "message": "通知限流设置成功"
        }
    except Exception as e:
        logger.error(f"Failed to set rate limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/statistics")
async def get_notification_statistics(
    days: int = Query(7, description="统计天数")
):
    """获取通知统计"""
    try:
        stats = notification_system.get_notification_statistics(days=days)
        
        return {
            "success": True,
            "message": "获取通知统计成功",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get notification statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/records")
async def list_notification_records(
    alert_id: Optional[UUID] = Query(None, description="告警ID"),
    channel: Optional[NotificationChannel] = Query(None, description="通知渠道"),
    status: Optional[NotificationStatus] = Query(None, description="通知状态"),
    limit: int = Query(100, description="返回数量限制")
):
    """列出通知记录"""
    try:
        records = notification_system.list_notification_records(
            alert_id=alert_id,
            channel=channel,
            status=status,
            limit=limit
        )
        
        return {
            "success": True,
            "message": "获取通知记录成功",
            "data": records,
            "total": len(records)
        }
    except Exception as e:
        logger.error(f"Failed to list notification records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/records/{notification_id}")
async def get_notification_record(notification_id: UUID):
    """获取通知记录详情"""
    try:
        record = notification_system.get_notification_record(notification_id)
        if not record:
            raise HTTPException(status_code=404, detail="通知记录不存在")
        
        return {
            "success": True,
            "message": "获取通知记录成功",
            "data": record
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get notification record: {e}")
        raise HTTPException(status_code=500, detail=str(e))