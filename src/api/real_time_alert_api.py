"""
Real-time Alert System API for SuperInsight Platform.

Provides REST API endpoints for managing real-time security alerting,
including alert rules, notification channels, and alert statistics.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from src.security.real_time_alert_system import (
    RealTimeAlertSystem, AlertRule, AlertChannel, AlertPriority,
    AlertStatus, SecurityEventType, ThreatLevel, get_alert_system
)
from src.database.connection import get_db_session
from sqlalchemy.orm import Session


router = APIRouter(prefix="/api/alerts", tags=["Real-time Alerts"])


# Pydantic models for API
class AlertRuleCreate(BaseModel):
    """创建告警规则的请求模型"""
    name: str = Field(..., description="规则名称")
    description: str = Field(..., description="规则描述")
    event_types: List[str] = Field(..., description="事件类型列表")
    threat_levels: List[str] = Field(..., description="威胁等级列表")
    channels: List[str] = Field(..., description="通知通道列表")
    priority: str = Field(..., description="告警优先级")
    enabled: bool = Field(True, description="是否启用")
    cooldown_minutes: int = Field(5, description="冷却时间（分钟）")
    escalation_minutes: int = Field(30, description="升级时间（分钟）")
    recipients: List[str] = Field(..., description="接收者列表")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="额外条件")


class AlertRuleUpdate(BaseModel):
    """更新告警规则的请求模型"""
    name: Optional[str] = Field(None, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    event_types: Optional[List[str]] = Field(None, description="事件类型列表")
    threat_levels: Optional[List[str]] = Field(None, description="威胁等级列表")
    channels: Optional[List[str]] = Field(None, description="通知通道列表")
    priority: Optional[str] = Field(None, description="告警优先级")
    enabled: Optional[bool] = Field(None, description="是否启用")
    cooldown_minutes: Optional[int] = Field(None, description="冷却时间（分钟）")
    escalation_minutes: Optional[int] = Field(None, description="升级时间（分钟）")
    recipients: Optional[List[str]] = Field(None, description="接收者列表")
    conditions: Optional[Dict[str, Any]] = Field(None, description="额外条件")


class AlertChannelConfig(BaseModel):
    """告警通道配置模型"""
    channel_type: str = Field(..., description="通道类型")
    enabled: bool = Field(..., description="是否启用")
    config: Dict[str, Any] = Field(..., description="通道配置")


class TestAlertRequest(BaseModel):
    """测试告警请求模型"""
    channel: str = Field(..., description="测试通道")
    recipient: str = Field(..., description="接收者")
    subject: str = Field("测试告警", description="主题")
    message: str = Field("这是一条测试告警消息", description="消息内容")
    priority: str = Field("medium", description="优先级")


@router.get("/rules")
async def get_alert_rules() -> Dict[str, Any]:
    """获取所有告警规则"""
    
    try:
        alert_system = get_alert_system()
        
        rules_data = []
        for rule_id, rule in alert_system.alert_rules.items():
            rules_data.append({
                "rule_id": rule_id,
                "name": rule.name,
                "description": rule.description,
                "event_types": [et.value for et in rule.event_types],
                "threat_levels": [tl.value for tl in rule.threat_levels],
                "channels": [ch.value for ch in rule.channels],
                "priority": rule.priority.value,
                "enabled": rule.enabled,
                "cooldown_minutes": rule.cooldown_minutes,
                "escalation_minutes": rule.escalation_minutes,
                "recipients": rule.recipients,
                "conditions": rule.conditions
            })
        
        return {
            "success": True,
            "rules": rules_data,
            "total_rules": len(rules_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert rules: {str(e)}")


@router.post("/rules")
async def create_alert_rule(rule_data: AlertRuleCreate) -> Dict[str, Any]:
    """创建新的告警规则"""
    
    try:
        alert_system = get_alert_system()
        
        # 生成规则ID
        rule_id = f"rule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 转换枚举类型
        event_types = [SecurityEventType(et) for et in rule_data.event_types]
        threat_levels = [ThreatLevel(tl) for tl in rule_data.threat_levels]
        channels = [AlertChannel(ch) for ch in rule_data.channels]
        priority = AlertPriority(rule_data.priority)
        
        # 创建规则
        rule = AlertRule(
            rule_id=rule_id,
            name=rule_data.name,
            description=rule_data.description,
            event_types=event_types,
            threat_levels=threat_levels,
            channels=channels,
            priority=priority,
            enabled=rule_data.enabled,
            cooldown_minutes=rule_data.cooldown_minutes,
            escalation_minutes=rule_data.escalation_minutes,
            recipients=rule_data.recipients,
            conditions=rule_data.conditions
        )
        
        alert_system.add_alert_rule(rule)
        
        return {
            "success": True,
            "message": "Alert rule created successfully",
            "rule_id": rule_id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid rule data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create alert rule: {str(e)}")


@router.get("/rules/{rule_id}")
async def get_alert_rule(rule_id: str) -> Dict[str, Any]:
    """获取特定告警规则"""
    
    try:
        alert_system = get_alert_system()
        
        if rule_id not in alert_system.alert_rules:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        
        rule = alert_system.alert_rules[rule_id]
        
        return {
            "success": True,
            "rule": {
                "rule_id": rule_id,
                "name": rule.name,
                "description": rule.description,
                "event_types": [et.value for et in rule.event_types],
                "threat_levels": [tl.value for tl in rule.threat_levels],
                "channels": [ch.value for ch in rule.channels],
                "priority": rule.priority.value,
                "enabled": rule.enabled,
                "cooldown_minutes": rule.cooldown_minutes,
                "escalation_minutes": rule.escalation_minutes,
                "recipients": rule.recipients,
                "conditions": rule.conditions
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert rule: {str(e)}")


@router.put("/rules/{rule_id}")
async def update_alert_rule(rule_id: str, rule_data: AlertRuleUpdate) -> Dict[str, Any]:
    """更新告警规则"""
    
    try:
        alert_system = get_alert_system()
        
        if rule_id not in alert_system.alert_rules:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        
        rule = alert_system.alert_rules[rule_id]
        
        # 更新规则属性
        if rule_data.name is not None:
            rule.name = rule_data.name
        if rule_data.description is not None:
            rule.description = rule_data.description
        if rule_data.event_types is not None:
            rule.event_types = [SecurityEventType(et) for et in rule_data.event_types]
        if rule_data.threat_levels is not None:
            rule.threat_levels = [ThreatLevel(tl) for tl in rule_data.threat_levels]
        if rule_data.channels is not None:
            rule.channels = [AlertChannel(ch) for ch in rule_data.channels]
        if rule_data.priority is not None:
            rule.priority = AlertPriority(rule_data.priority)
        if rule_data.enabled is not None:
            rule.enabled = rule_data.enabled
        if rule_data.cooldown_minutes is not None:
            rule.cooldown_minutes = rule_data.cooldown_minutes
        if rule_data.escalation_minutes is not None:
            rule.escalation_minutes = rule_data.escalation_minutes
        if rule_data.recipients is not None:
            rule.recipients = rule_data.recipients
        if rule_data.conditions is not None:
            rule.conditions = rule_data.conditions
        
        return {
            "success": True,
            "message": "Alert rule updated successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid rule data: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update alert rule: {str(e)}")


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: str) -> Dict[str, Any]:
    """删除告警规则"""
    
    try:
        alert_system = get_alert_system()
        
        if rule_id not in alert_system.alert_rules:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        
        alert_system.remove_alert_rule(rule_id)
        
        return {
            "success": True,
            "message": "Alert rule deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete alert rule: {str(e)}")


@router.post("/rules/{rule_id}/enable")
async def enable_alert_rule(rule_id: str) -> Dict[str, Any]:
    """启用告警规则"""
    
    try:
        alert_system = get_alert_system()
        
        if rule_id not in alert_system.alert_rules:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        
        alert_system.enable_alert_rule(rule_id)
        
        return {
            "success": True,
            "message": "Alert rule enabled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable alert rule: {str(e)}")


@router.post("/rules/{rule_id}/disable")
async def disable_alert_rule(rule_id: str) -> Dict[str, Any]:
    """禁用告警规则"""
    
    try:
        alert_system = get_alert_system()
        
        if rule_id not in alert_system.alert_rules:
            raise HTTPException(status_code=404, detail="Alert rule not found")
        
        alert_system.disable_alert_rule(rule_id)
        
        return {
            "success": True,
            "message": "Alert rule disabled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable alert rule: {str(e)}")


@router.get("/channels")
async def get_alert_channels() -> Dict[str, Any]:
    """获取可用的告警通道"""
    
    try:
        alert_system = get_alert_system()
        
        channels_data = []
        for channel in AlertChannel:
            handler_available = channel in alert_system.channel_handlers
            channels_data.append({
                "channel": channel.value,
                "name": channel.value.replace('_', ' ').title(),
                "available": handler_available,
                "description": _get_channel_description(channel)
            })
        
        return {
            "success": True,
            "channels": channels_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert channels: {str(e)}")


@router.post("/test")
async def test_alert(test_request: TestAlertRequest) -> Dict[str, Any]:
    """发送测试告警"""
    
    try:
        alert_system = get_alert_system()
        
        # 验证通道
        try:
            channel = AlertChannel(test_request.channel)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid alert channel")
        
        # 验证优先级
        try:
            priority = AlertPriority(test_request.priority)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid alert priority")
        
        # 检查通道处理器是否可用
        if channel not in alert_system.channel_handlers:
            raise HTTPException(status_code=400, detail=f"Channel handler not available: {channel.value}")
        
        # 发送测试通知
        handler = alert_system.channel_handlers[channel]
        success = await handler.send_notification(
            recipient=test_request.recipient,
            subject=test_request.subject,
            message=test_request.message,
            priority=priority,
            metadata={"test": True, "timestamp": datetime.now().isoformat()}
        )
        
        if success:
            return {
                "success": True,
                "message": "Test alert sent successfully"
            }
        else:
            return {
                "success": False,
                "message": "Failed to send test alert"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test alert: {str(e)}")


@router.get("/statistics")
async def get_alert_statistics() -> Dict[str, Any]:
    """获取告警统计信息"""
    
    try:
        alert_system = get_alert_system()
        stats = alert_system.get_alert_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert statistics: {str(e)}")


@router.get("/notifications")
async def get_recent_notifications(
    limit: int = Query(50, description="返回的通知数量限制"),
    status: Optional[str] = Query(None, description="按状态过滤")
) -> Dict[str, Any]:
    """获取最近的通知记录"""
    
    try:
        alert_system = get_alert_system()
        
        notifications = alert_system.sent_notifications
        
        # 按状态过滤
        if status:
            try:
                status_enum = AlertStatus(status)
                notifications = [n for n in notifications if n.status == status_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status value")
        
        # 按时间排序并限制数量
        notifications = sorted(notifications, key=lambda x: x.created_at, reverse=True)[:limit]
        
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                "notification_id": notif.notification_id,
                "alert_id": notif.alert_id,
                "rule_id": notif.rule_id,
                "channel": notif.channel.value,
                "recipient": notif.recipient,
                "subject": notif.subject,
                "priority": notif.priority.value,
                "status": notif.status.value,
                "created_at": notif.created_at.isoformat(),
                "sent_at": notif.sent_at.isoformat() if notif.sent_at else None,
                "retry_count": notif.retry_count,
                "error_message": notif.error_message
            })
        
        return {
            "success": True,
            "notifications": notifications_data,
            "total_count": len(notifications_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get notifications: {str(e)}")


@router.post("/start")
async def start_alert_system() -> Dict[str, Any]:
    """启动实时告警系统"""
    
    try:
        alert_system = get_alert_system()
        
        if alert_system.running:
            return {
                "success": True,
                "message": "Alert system is already running"
            }
        
        await alert_system.start_notification_processing()
        
        return {
            "success": True,
            "message": "Alert system started successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start alert system: {str(e)}")


@router.post("/stop")
async def stop_alert_system() -> Dict[str, Any]:
    """停止实时告警系统"""
    
    try:
        alert_system = get_alert_system()
        
        if not alert_system.running:
            return {
                "success": True,
                "message": "Alert system is already stopped"
            }
        
        await alert_system.stop_notification_processing()
        
        return {
            "success": True,
            "message": "Alert system stopped successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop alert system: {str(e)}")


@router.get("/status")
async def get_alert_system_status() -> Dict[str, Any]:
    """获取告警系统状态"""
    
    try:
        alert_system = get_alert_system()
        
        return {
            "success": True,
            "status": {
                "running": alert_system.running,
                "total_rules": len(alert_system.alert_rules),
                "active_rules": len([r for r in alert_system.alert_rules.values() if r.enabled]),
                "available_channels": len(alert_system.channel_handlers),
                "pending_notifications": len(alert_system.pending_notifications),
                "active_cooldowns": len(alert_system.alert_cooldowns)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert system status: {str(e)}")


def _get_channel_description(channel: AlertChannel) -> str:
    """获取通道描述"""
    descriptions = {
        AlertChannel.EMAIL: "通过SMTP发送邮件通知",
        AlertChannel.SLACK: "通过Webhook发送Slack消息",
        AlertChannel.WEBHOOK: "发送HTTP POST请求到指定URL",
        AlertChannel.SMS: "发送短信通知（需要SMS服务提供商）",
        AlertChannel.PUSH_NOTIFICATION: "发送推送通知到移动设备",
        AlertChannel.SYSTEM_LOG: "记录到系统日志文件"
    }
    return descriptions.get(channel, "未知通道类型")