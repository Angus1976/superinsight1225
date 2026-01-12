"""
Security Dashboard API endpoints for SuperInsight Platform.

Provides REST API and WebSocket endpoints for security dashboard data,
real-time updates, and visualization support.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, Path
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.middleware import get_current_active_user, require_role, audit_action
from src.security.models import AuditAction, UserModel
from src.security.security_dashboard_service import (
    security_dashboard_service,
    DashboardTimeRange,
    DashboardData,
    SecurityMetrics,
    ComplianceMetrics
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/security-dashboard", tags=["Security Dashboard"])


# Request/Response Models

class DashboardDataResponse(BaseModel):
    """Dashboard data response model."""
    timestamp: str
    tenant_id: str
    time_range: str
    security_metrics: Dict[str, Any]
    compliance_metrics: Dict[str, Any]
    recent_events: List[Dict[str, Any]]
    active_alerts: List[Dict[str, Any]]
    system_status: Dict[str, Any]
    security_trends: List[Dict[str, Any]]
    threat_heatmap: Dict[str, Any]
    user_activity_map: Dict[str, Any]


class SecurityMetricsResponse(BaseModel):
    """Security metrics response model."""
    total_events: int
    critical_events: int
    high_risk_events: int
    resolved_events: int
    active_threats: int
    security_score: float
    compliance_score: float
    events_by_type: Dict[str, int]
    events_by_threat_level: Dict[str, int]
    events_by_hour: List[Dict[str, Any]]
    top_threats: List[Dict[str, Any]]
    threat_trends: List[Dict[str, Any]]
    active_users: int
    suspicious_users: List[Dict[str, Any]]
    failed_logins: int
    monitoring_status: str
    last_scan_time: str
    system_health: str


class ComplianceMetricsResponse(BaseModel):
    """Compliance metrics response model."""
    overall_score: float
    gdpr_score: float
    sox_score: float
    iso27001_score: float
    compliant_controls: int
    total_controls: int
    violations: int
    critical_violations: int
    audit_coverage: float
    data_protection_score: float
    access_control_score: float
    compliance_trends: List[Dict[str, Any]]
    violation_trends: List[Dict[str, Any]]


class DashboardSummaryResponse(BaseModel):
    """Dashboard summary response model."""
    tenant_id: str
    last_updated: str
    security_score: float
    compliance_score: float
    active_threats: int
    critical_events: int
    total_violations: int
    monitoring_status: str


class RealTimeUpdateRequest(BaseModel):
    """Real-time update request model."""
    tenant_id: str
    update_interval: int = Field(default=30, ge=10, le=300, description="Update interval in seconds")
    metrics_filter: Optional[List[str]] = Field(default=None, description="Specific metrics to include")


# API Endpoints

@router.get("/summary/{tenant_id}", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    tenant_id: str = Path(..., description="Tenant ID"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    获取安全仪表盘摘要数据。
    
    快速获取关键安全指标，适用于概览页面。
    """
    try:
        # 权限检查
        if not require_role(current_user, ["admin", "security_officer"], tenant_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # 审计日志
        await audit_action(
            user_id=current_user.id,
            action=AuditAction.VIEW,
            resource="security_dashboard_summary",
            resource_id=tenant_id,
            db=db
        )
        
        # 获取摘要数据
        summary = security_dashboard_service.get_dashboard_summary(tenant_id)
        
        return DashboardSummaryResponse(**summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{tenant_id}", response_model=DashboardDataResponse)
async def get_dashboard_data(
    tenant_id: str = Path(..., description="Tenant ID"),
    time_range: DashboardTimeRange = Query(DashboardTimeRange.LAST_24_HOURS, description="Time range"),
    force_refresh: bool = Query(False, description="Force refresh cache"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    获取完整的安全仪表盘数据。
    
    包含所有安全指标、合规数据、趋势分析和可视化数据。
    """
    try:
        # 权限检查
        if not require_role(current_user, ["admin", "security_officer", "auditor"], tenant_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # 审计日志
        await audit_action(
            user_id=current_user.id,
            action=AuditAction.VIEW,
            resource="security_dashboard_data",
            resource_id=tenant_id,
            details={"time_range": time_range.value, "force_refresh": force_refresh},
            db=db
        )
        
        # 获取仪表盘数据
        dashboard_data = await security_dashboard_service.get_dashboard_data(
            tenant_id=tenant_id,
            time_range=time_range,
            force_refresh=force_refresh
        )
        
        # 转换为响应格式
        response_data = {
            "timestamp": dashboard_data.timestamp.isoformat(),
            "tenant_id": dashboard_data.tenant_id,
            "time_range": dashboard_data.time_range.value,
            "security_metrics": {
                "total_events": dashboard_data.security_metrics.total_events,
                "critical_events": dashboard_data.security_metrics.critical_events,
                "high_risk_events": dashboard_data.security_metrics.high_risk_events,
                "resolved_events": dashboard_data.security_metrics.resolved_events,
                "active_threats": dashboard_data.security_metrics.active_threats,
                "security_score": dashboard_data.security_metrics.security_score,
                "compliance_score": dashboard_data.security_metrics.compliance_score,
                "events_by_type": dashboard_data.security_metrics.events_by_type,
                "events_by_threat_level": dashboard_data.security_metrics.events_by_threat_level,
                "events_by_hour": dashboard_data.security_metrics.events_by_hour,
                "top_threats": dashboard_data.security_metrics.top_threats,
                "threat_trends": dashboard_data.security_metrics.threat_trends,
                "active_users": dashboard_data.security_metrics.active_users,
                "suspicious_users": dashboard_data.security_metrics.suspicious_users,
                "failed_logins": dashboard_data.security_metrics.failed_logins,
                "monitoring_status": dashboard_data.security_metrics.monitoring_status,
                "last_scan_time": dashboard_data.security_metrics.last_scan_time.isoformat(),
                "system_health": dashboard_data.security_metrics.system_health
            },
            "compliance_metrics": {
                "overall_score": dashboard_data.compliance_metrics.overall_score,
                "gdpr_score": dashboard_data.compliance_metrics.gdpr_score,
                "sox_score": dashboard_data.compliance_metrics.sox_score,
                "iso27001_score": dashboard_data.compliance_metrics.iso27001_score,
                "compliant_controls": dashboard_data.compliance_metrics.compliant_controls,
                "total_controls": dashboard_data.compliance_metrics.total_controls,
                "violations": dashboard_data.compliance_metrics.violations,
                "critical_violations": dashboard_data.compliance_metrics.critical_violations,
                "audit_coverage": dashboard_data.compliance_metrics.audit_coverage,
                "data_protection_score": dashboard_data.compliance_metrics.data_protection_score,
                "access_control_score": dashboard_data.compliance_metrics.access_control_score,
                "compliance_trends": dashboard_data.compliance_metrics.compliance_trends,
                "violation_trends": dashboard_data.compliance_metrics.violation_trends
            },
            "recent_events": dashboard_data.recent_events,
            "active_alerts": dashboard_data.active_alerts,
            "system_status": dashboard_data.system_status,
            "security_trends": dashboard_data.security_trends,
            "threat_heatmap": dashboard_data.threat_heatmap,
            "user_activity_map": dashboard_data.user_activity_map
        }
        
        return DashboardDataResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/security/{tenant_id}", response_model=SecurityMetricsResponse)
async def get_security_metrics(
    tenant_id: str = Path(..., description="Tenant ID"),
    time_range: DashboardTimeRange = Query(DashboardTimeRange.LAST_24_HOURS, description="Time range"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    获取安全指标数据。
    
    专门用于安全监控的详细指标。
    """
    try:
        # 权限检查
        if not require_role(current_user, ["admin", "security_officer"], tenant_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # 审计日志
        await audit_action(
            user_id=current_user.id,
            action=AuditAction.VIEW,
            resource="security_metrics",
            resource_id=tenant_id,
            db=db
        )
        
        # 获取仪表盘数据
        dashboard_data = await security_dashboard_service.get_dashboard_data(
            tenant_id=tenant_id,
            time_range=time_range
        )
        
        # 返回安全指标
        security_metrics = dashboard_data.security_metrics
        return SecurityMetricsResponse(
            total_events=security_metrics.total_events,
            critical_events=security_metrics.critical_events,
            high_risk_events=security_metrics.high_risk_events,
            resolved_events=security_metrics.resolved_events,
            active_threats=security_metrics.active_threats,
            security_score=security_metrics.security_score,
            compliance_score=security_metrics.compliance_score,
            events_by_type=security_metrics.events_by_type,
            events_by_threat_level=security_metrics.events_by_threat_level,
            events_by_hour=security_metrics.events_by_hour,
            top_threats=security_metrics.top_threats,
            threat_trends=security_metrics.threat_trends,
            active_users=security_metrics.active_users,
            suspicious_users=security_metrics.suspicious_users,
            failed_logins=security_metrics.failed_logins,
            monitoring_status=security_metrics.monitoring_status,
            last_scan_time=security_metrics.last_scan_time.isoformat(),
            system_health=security_metrics.system_health
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/compliance/{tenant_id}", response_model=ComplianceMetricsResponse)
async def get_compliance_metrics(
    tenant_id: str = Path(..., description="Tenant ID"),
    time_range: DashboardTimeRange = Query(DashboardTimeRange.LAST_24_HOURS, description="Time range"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    获取合规指标数据。
    
    专门用于合规监控的详细指标。
    """
    try:
        # 权限检查
        if not require_role(current_user, ["admin", "security_officer", "auditor"], tenant_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # 审计日志
        await audit_action(
            user_id=current_user.id,
            action=AuditAction.VIEW,
            resource="compliance_metrics",
            resource_id=tenant_id,
            db=db
        )
        
        # 获取仪表盘数据
        dashboard_data = await security_dashboard_service.get_dashboard_data(
            tenant_id=tenant_id,
            time_range=time_range
        )
        
        # 返回合规指标
        compliance_metrics = dashboard_data.compliance_metrics
        return ComplianceMetricsResponse(
            overall_score=compliance_metrics.overall_score,
            gdpr_score=compliance_metrics.gdpr_score,
            sox_score=compliance_metrics.sox_score,
            iso27001_score=compliance_metrics.iso27001_score,
            compliant_controls=compliance_metrics.compliant_controls,
            total_controls=compliance_metrics.total_controls,
            violations=compliance_metrics.violations,
            critical_violations=compliance_metrics.critical_violations,
            audit_coverage=compliance_metrics.audit_coverage,
            data_protection_score=compliance_metrics.data_protection_score,
            access_control_score=compliance_metrics.access_control_score,
            compliance_trends=compliance_metrics.compliance_trends,
            violation_trends=compliance_metrics.violation_trends
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting compliance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/security/{tenant_id}")
async def get_security_trends(
    tenant_id: str = Path(..., description="Tenant ID"),
    time_range: DashboardTimeRange = Query(DashboardTimeRange.LAST_7_DAYS, description="Time range"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    获取安全趋势数据。
    
    用于趋势图表和分析。
    """
    try:
        # 权限检查
        if not require_role(current_user, ["admin", "security_officer"], tenant_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # 审计日志
        await audit_action(
            user_id=current_user.id,
            action=AuditAction.VIEW,
            resource="security_trends",
            resource_id=tenant_id,
            db=db
        )
        
        # 获取仪表盘数据
        dashboard_data = await security_dashboard_service.get_dashboard_data(
            tenant_id=tenant_id,
            time_range=time_range
        )
        
        return {
            "security_trends": dashboard_data.security_trends,
            "threat_trends": dashboard_data.security_metrics.threat_trends,
            "events_by_hour": dashboard_data.security_metrics.events_by_hour
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap/threats/{tenant_id}")
async def get_threat_heatmap(
    tenant_id: str = Path(..., description="Tenant ID"),
    time_range: DashboardTimeRange = Query(DashboardTimeRange.LAST_24_HOURS, description="Time range"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    获取威胁热力图数据。
    
    用于威胁分布可视化。
    """
    try:
        # 权限检查
        if not require_role(current_user, ["admin", "security_officer"], tenant_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # 审计日志
        await audit_action(
            user_id=current_user.id,
            action=AuditAction.VIEW,
            resource="threat_heatmap",
            resource_id=tenant_id,
            db=db
        )
        
        # 获取仪表盘数据
        dashboard_data = await security_dashboard_service.get_dashboard_data(
            tenant_id=tenant_id,
            time_range=time_range
        )
        
        return dashboard_data.threat_heatmap
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting threat heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity/users/{tenant_id}")
async def get_user_activity_map(
    tenant_id: str = Path(..., description="Tenant ID"),
    time_range: DashboardTimeRange = Query(DashboardTimeRange.LAST_24_HOURS, description="Time range"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    获取用户活动地图数据。
    
    用于用户行为分析和可视化。
    """
    try:
        # 权限检查
        if not require_role(current_user, ["admin", "security_officer"], tenant_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # 审计日志
        await audit_action(
            user_id=current_user.id,
            action=AuditAction.VIEW,
            resource="user_activity_map",
            resource_id=tenant_id,
            db=db
        )
        
        # 获取仪表盘数据
        dashboard_data = await security_dashboard_service.get_dashboard_data(
            tenant_id=tenant_id,
            time_range=time_range
        )
        
        return dashboard_data.user_activity_map
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user activity map: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh/{tenant_id}")
async def refresh_dashboard_data(
    tenant_id: str = Path(..., description="Tenant ID"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db_session)
):
    """
    强制刷新仪表盘数据。
    
    清除缓存并重新计算所有指标。
    """
    try:
        # 权限检查
        if not require_role(current_user, ["admin", "security_officer"], tenant_id):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # 审计日志
        await audit_action(
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            resource="security_dashboard_refresh",
            resource_id=tenant_id,
            db=db
        )
        
        # 强制刷新数据
        dashboard_data = await security_dashboard_service.get_dashboard_data(
            tenant_id=tenant_id,
            time_range=DashboardTimeRange.LAST_24_HOURS,
            force_refresh=True
        )
        
        return {
            "success": True,
            "message": "Dashboard data refreshed successfully",
            "timestamp": dashboard_data.timestamp.isoformat(),
            "tenant_id": tenant_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket Endpoints

@router.websocket("/ws/{tenant_id}")
async def websocket_dashboard_updates(
    websocket: WebSocket,
    tenant_id: str = Path(..., description="Tenant ID")
):
    """
    WebSocket连接用于实时仪表盘更新。
    
    客户端连接后将接收实时的安全和合规数据更新。
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for tenant {tenant_id}")
    
    try:
        # 添加连接到服务
        await security_dashboard_service.add_websocket_connection(tenant_id, websocket)
        
        # 发送初始数据
        try:
            dashboard_data = await security_dashboard_service.get_dashboard_data(
                tenant_id=tenant_id,
                time_range=DashboardTimeRange.LAST_24_HOURS
            )
            
            initial_data = {
                "type": "initial_data",
                "timestamp": dashboard_data.timestamp.isoformat(),
                "data": {
                    "security_score": dashboard_data.security_metrics.security_score,
                    "compliance_score": dashboard_data.compliance_metrics.overall_score,
                    "active_threats": dashboard_data.security_metrics.active_threats,
                    "critical_events": dashboard_data.security_metrics.critical_events
                }
            }
            
            await websocket.send_text(json.dumps(initial_data))
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
        
        # 保持连接活跃
        while True:
            try:
                # 等待客户端消息（心跳或配置更新）
                message = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                
                # 处理客户端消息
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message from client: {message}")
                    
            except asyncio.TimeoutError:
                # 发送心跳
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"WebSocket error for tenant {tenant_id}: {e}")
    finally:
        # 清理连接
        await security_dashboard_service.remove_websocket_connection(tenant_id, websocket)


@router.get("/status")
async def get_dashboard_service_status():
    """
    获取仪表盘服务状态。
    
    用于健康检查和监控。
    """
    try:
        return {
            "service": "security_dashboard",
            "status": "healthy",
            "real_time_updates_active": security_dashboard_service.is_running,
            "active_connections": sum(
                len(connections) 
                for connections in security_dashboard_service.active_connections.values()
            ),
            "active_tenants": len(security_dashboard_service.active_connections),
            "cache_entries": len(security_dashboard_service.dashboard_cache),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard service status: {e}")
        return {
            "service": "security_dashboard",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }