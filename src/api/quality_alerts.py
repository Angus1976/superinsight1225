"""
Quality Alerts API - 质量预警 API
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.quality.quality_alert_service import (
    QualityAlertService,
    QualityAlert,
    AlertConfig
)


router = APIRouter(prefix="/api/v1/quality-alerts", tags=["Quality Alerts"])


# 全局实例
_alert_service: Optional[QualityAlertService] = None


def get_alert_service() -> QualityAlertService:
    global _alert_service
    if _alert_service is None:
        _alert_service = QualityAlertService()
    return _alert_service


# Request/Response Models
class AlertConfigRequest(BaseModel):
    """预警配置请求"""
    project_id: str
    thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "accuracy": 0.8,
        "completeness": 0.9,
        "timeliness": 0.7
    })
    notification_channels: List[str] = Field(default_factory=lambda: ["in_app"])
    recipients: List[str] = Field(default_factory=list)
    escalation_rules: Dict[str, Any] = Field(default_factory=dict)


class AlertConfigResponse(BaseModel):
    """预警配置响应"""
    id: str
    project_id: str
    thresholds: Dict[str, float]
    enabled: bool
    notification_channels: List[str]
    recipients: List[str]
    silence_duration: int
    silence_until: Optional[datetime] = None
    escalation_rules: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AlertResponse(BaseModel):
    """预警响应"""
    id: str
    project_id: str
    annotation_id: Optional[str] = None
    triggered_dimensions: List[str]
    scores: Dict[str, float]
    thresholds: Dict[str, float]
    severity: str
    escalation_level: int
    status: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime


class AlertListResponse(BaseModel):
    """预警列表响应"""
    alerts: List[AlertResponse]
    total: int


class AcknowledgeRequest(BaseModel):
    """确认预警请求"""
    user_id: str


class ResolveRequest(BaseModel):
    """解决预警请求"""
    user_id: str
    resolution_notes: Optional[str] = None


class SilenceRequest(BaseModel):
    """静默期请求"""
    project_id: str
    duration_minutes: int


class UpdateConfigRequest(BaseModel):
    """更新配置请求"""
    thresholds: Optional[Dict[str, float]] = None
    enabled: Optional[bool] = None
    notification_channels: Optional[List[str]] = None
    recipients: Optional[List[str]] = None
    escalation_rules: Optional[Dict[str, Any]] = None


# API Endpoints
@router.post("/configure", response_model=AlertConfigResponse)
async def configure_alerts(
    request: AlertConfigRequest,
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertConfigResponse:
    """
    配置质量预警
    
    - **project_id**: 项目ID
    - **thresholds**: 各维度阈值
    - **notification_channels**: 通知渠道
    - **recipients**: 接收人列表
    - **escalation_rules**: 升级规则
    """
    config = await alert_service.configure_thresholds(
        project_id=request.project_id,
        thresholds=request.thresholds,
        notification_channels=request.notification_channels,
        recipients=request.recipients,
        escalation_rules=request.escalation_rules
    )
    
    return AlertConfigResponse(
        id=config.id,
        project_id=config.project_id,
        thresholds=config.thresholds,
        enabled=config.enabled,
        notification_channels=config.notification_channels,
        recipients=config.recipients,
        silence_duration=config.silence_duration,
        silence_until=config.silence_until,
        escalation_rules=config.escalation_rules,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.get("/config/{project_id}", response_model=AlertConfigResponse)
async def get_alert_config(
    project_id: str,
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertConfigResponse:
    """
    获取预警配置
    
    - **project_id**: 项目ID
    """
    config = await alert_service.get_alert_config(project_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Alert config not found")
    
    return AlertConfigResponse(
        id=config.id,
        project_id=config.project_id,
        thresholds=config.thresholds,
        enabled=config.enabled,
        notification_channels=config.notification_channels,
        recipients=config.recipients,
        silence_duration=config.silence_duration,
        silence_until=config.silence_until,
        escalation_rules=config.escalation_rules,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.put("/config/{project_id}", response_model=AlertConfigResponse)
async def update_alert_config(
    project_id: str,
    request: UpdateConfigRequest,
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertConfigResponse:
    """
    更新预警配置
    
    - **project_id**: 项目ID
    """
    updates = request.dict(exclude_unset=True)
    config = await alert_service.update_config(project_id, updates)
    
    if not config:
        raise HTTPException(status_code=404, detail="Alert config not found")
    
    return AlertConfigResponse(
        id=config.id,
        project_id=config.project_id,
        thresholds=config.thresholds,
        enabled=config.enabled,
        notification_channels=config.notification_channels,
        recipients=config.recipients,
        silence_duration=config.silence_duration,
        silence_until=config.silence_until,
        escalation_rules=config.escalation_rules,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    project_id: str = Query(..., description="项目ID"),
    status: Optional[str] = Query(None, description="状态过滤"),
    severity: Optional[str] = Query(None, description="严重程度过滤"),
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertListResponse:
    """
    获取预警列表
    
    - **project_id**: 项目ID
    - **status**: 状态过滤 (open/acknowledged/resolved)
    - **severity**: 严重程度过滤 (critical/high/medium/low)
    """
    alerts = await alert_service.get_alerts(
        project_id=project_id,
        status=status,
        severity=severity
    )
    
    alert_responses = [
        AlertResponse(
            id=a.id,
            project_id=a.project_id,
            annotation_id=a.annotation_id,
            triggered_dimensions=a.triggered_dimensions,
            scores=a.scores,
            thresholds=a.thresholds,
            severity=a.severity,
            escalation_level=a.escalation_level,
            status=a.status,
            acknowledged_by=a.acknowledged_by,
            acknowledged_at=a.acknowledged_at,
            resolved_by=a.resolved_by,
            resolved_at=a.resolved_at,
            resolution_notes=a.resolution_notes,
            created_at=a.created_at
        )
        for a in alerts
    ]
    
    return AlertListResponse(alerts=alert_responses, total=len(alert_responses))


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertResponse:
    """
    获取单个预警
    
    - **alert_id**: 预警ID
    """
    alert = await alert_service.get_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(
        id=alert.id,
        project_id=alert.project_id,
        annotation_id=alert.annotation_id,
        triggered_dimensions=alert.triggered_dimensions,
        scores=alert.scores,
        thresholds=alert.thresholds,
        severity=alert.severity,
        escalation_level=alert.escalation_level,
        status=alert.status,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolved_by=alert.resolved_by,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        created_at=alert.created_at
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    request: AcknowledgeRequest,
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertResponse:
    """
    确认预警
    
    - **alert_id**: 预警ID
    - **user_id**: 用户ID
    """
    alert = await alert_service.acknowledge_alert(alert_id, request.user_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(
        id=alert.id,
        project_id=alert.project_id,
        annotation_id=alert.annotation_id,
        triggered_dimensions=alert.triggered_dimensions,
        scores=alert.scores,
        thresholds=alert.thresholds,
        severity=alert.severity,
        escalation_level=alert.escalation_level,
        status=alert.status,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolved_by=alert.resolved_by,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        created_at=alert.created_at
    )


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    request: ResolveRequest,
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertResponse:
    """
    解决预警
    
    - **alert_id**: 预警ID
    - **user_id**: 用户ID
    - **resolution_notes**: 解决备注
    """
    alert = await alert_service.resolve_alert(
        alert_id,
        request.user_id,
        request.resolution_notes
    )
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(
        id=alert.id,
        project_id=alert.project_id,
        annotation_id=alert.annotation_id,
        triggered_dimensions=alert.triggered_dimensions,
        scores=alert.scores,
        thresholds=alert.thresholds,
        severity=alert.severity,
        escalation_level=alert.escalation_level,
        status=alert.status,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolved_by=alert.resolved_by,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        created_at=alert.created_at
    )


@router.post("/{alert_id}/escalate", response_model=AlertResponse)
async def escalate_alert(
    alert_id: str,
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertResponse:
    """
    升级预警
    
    - **alert_id**: 预警ID
    """
    alert = await alert_service.escalate_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(
        id=alert.id,
        project_id=alert.project_id,
        annotation_id=alert.annotation_id,
        triggered_dimensions=alert.triggered_dimensions,
        scores=alert.scores,
        thresholds=alert.thresholds,
        severity=alert.severity,
        escalation_level=alert.escalation_level,
        status=alert.status,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolved_by=alert.resolved_by,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        created_at=alert.created_at
    )


@router.post("/silence", response_model=AlertConfigResponse)
async def set_silence_period(
    request: SilenceRequest,
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertConfigResponse:
    """
    设置静默期
    
    - **project_id**: 项目ID
    - **duration_minutes**: 静默时长 (分钟)
    """
    config = await alert_service.set_silence_period(
        request.project_id,
        request.duration_minutes
    )
    
    return AlertConfigResponse(
        id=config.id,
        project_id=config.project_id,
        thresholds=config.thresholds,
        enabled=config.enabled,
        notification_channels=config.notification_channels,
        recipients=config.recipients,
        silence_duration=config.silence_duration,
        silence_until=config.silence_until,
        escalation_rules=config.escalation_rules,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.delete("/silence/{project_id}", response_model=AlertConfigResponse)
async def clear_silence_period(
    project_id: str,
    alert_service: QualityAlertService = Depends(get_alert_service)
) -> AlertConfigResponse:
    """
    清除静默期
    
    - **project_id**: 项目ID
    """
    config = await alert_service.clear_silence_period(project_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Alert config not found")
    
    return AlertConfigResponse(
        id=config.id,
        project_id=config.project_id,
        thresholds=config.thresholds,
        enabled=config.enabled,
        notification_channels=config.notification_channels,
        recipients=config.recipients,
        silence_duration=config.silence_duration,
        silence_until=config.silence_until,
        escalation_rules=config.escalation_rules,
        created_at=config.created_at,
        updated_at=config.updated_at
    )
