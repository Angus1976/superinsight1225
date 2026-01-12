"""
Complete Event Capture API endpoints for SuperInsight Platform.

Provides REST API endpoints for managing and monitoring the complete
security event capture system.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from uuid import UUID

from src.database.connection import get_db_session
from src.security.complete_event_capture_system import (
    get_complete_capture_system, CompleteEventCaptureSystem,
    EventSource, CaptureStatus
)
from src.security.audit_service import AuditService
from src.api.auth import get_current_user_with_permissions


router = APIRouter(prefix="/api/v1/security/capture", tags=["Complete Event Capture"])


# Pydantic模型

class CaptureStatisticsResponse(BaseModel):
    """捕获统计响应模型"""
    overall_metrics: Dict[str, Any]
    source_metrics: Dict[str, Dict[str, Any]]
    system_status: Dict[str, Any]


class FailedEventResponse(BaseModel):
    """失败事件响应模型"""
    event_id: str
    source: str
    timestamp: str
    status: str
    attempts: int
    error_message: Optional[str]
    metadata: Dict[str, Any]


class EventCaptureRequest(BaseModel):
    """事件捕获请求模型"""
    event_data: Dict[str, Any] = Field(..., description="Event data to capture")
    force_capture: bool = Field(False, description="Force capture even if validation fails")


class CaptureConfigurationRequest(BaseModel):
    """捕获配置请求模型"""
    capture_enabled: Optional[bool] = Field(None, description="Enable/disable event capture")
    max_retry_attempts: Optional[int] = Field(None, description="Maximum retry attempts")
    retry_delay_seconds: Optional[int] = Field(None, description="Retry delay in seconds")
    validation_enabled: Optional[bool] = Field(None, description="Enable/disable event validation")
    alert_threshold: Optional[float] = Field(None, description="Capture rate alert threshold")


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    capture_enabled: bool
    overall_health: str
    components: Dict[str, str]
    capture_rate: float
    queue_status: Dict[str, Any]
    last_check: str


# API端点

@router.get("/statistics", response_model=CaptureStatisticsResponse)
async def get_capture_statistics(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user_with_permissions(["security:read"]))
):
    """
    获取事件捕获统计信息
    
    返回完整的事件捕获系统统计信息，包括：
    - 总体捕获指标
    - 各事件源指标
    - 系统状态信息
    """
    
    capture_system = get_complete_capture_system()
    if not capture_system:
        raise HTTPException(status_code=503, detail="Event capture system not available")
    
    try:
        statistics = capture_system.get_capture_statistics()
        
        # 记录审计日志
        audit_service = AuditService()
        await audit_service.log_system_event(
            user_id=current_user.get("user_id"),
            tenant_id=tenant_id,
            action="get_capture_statistics",
            resource_type="capture_system",
            details={"statistics_requested": True}
        )
        
        return CaptureStatisticsResponse(**statistics)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get capture statistics: {str(e)}")


@router.get("/failed-events", response_model=List[FailedEventResponse])
async def get_failed_events(
    tenant_id: str = Query(..., description="Tenant ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of failed events to return"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user_with_permissions(["security:read"]))
):
    """
    获取失败的事件列表
    
    返回最近失败的事件，用于故障排查和分析。
    """
    
    capture_system = get_complete_capture_system()
    if not capture_system:
        raise HTTPException(status_code=503, detail="Event capture system not available")
    
    try:
        failed_events = capture_system.get_failed_events(limit=limit)
        
        # 过滤租户相关的事件
        tenant_failed_events = [
            event for event in failed_events
            if event.get('metadata', {}).get('tenant_id') == tenant_id
        ]
        
        # 记录审计日志
        audit_service = AuditService()
        await audit_service.log_system_event(
            user_id=current_user.get("user_id"),
            tenant_id=tenant_id,
            action="get_failed_events",
            resource_type="capture_system",
            details={"failed_events_count": len(tenant_failed_events)}
        )
        
        return [FailedEventResponse(**event) for event in tenant_failed_events]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get failed events: {str(e)}")


@router.post("/force-capture")
async def force_event_capture(
    tenant_id: str = Query(..., description="Tenant ID"),
    request: EventCaptureRequest = ...,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user_with_permissions(["security:write"]))
):
    """
    强制捕获事件
    
    手动提交事件到捕获系统，用于测试或补充遗漏的事件。
    """
    
    capture_system = get_complete_capture_system()
    if not capture_system:
        raise HTTPException(status_code=503, detail="Event capture system not available")
    
    try:
        # 添加租户ID到事件数据
        event_data = request.event_data.copy()
        event_data['tenant_id'] = tenant_id
        event_data['forced_capture'] = True
        event_data['captured_by'] = current_user.get("user_id")
        
        # 强制捕获事件
        success = await capture_system.force_event_capture(event_data)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to capture event")
        
        # 记录审计日志
        audit_service = AuditService()
        await audit_service.log_system_event(
            user_id=current_user.get("user_id"),
            tenant_id=tenant_id,
            action="force_event_capture",
            resource_type="capture_system",
            details={
                "event_id": event_data.get('event_id'),
                "force_capture": request.force_capture
            }
        )
        
        return {
            "status": "success",
            "message": "Event captured successfully",
            "event_id": event_data.get('event_id'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to force capture event: {str(e)}")


@router.get("/health", response_model=HealthCheckResponse)
async def capture_system_health_check(
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user_with_permissions(["security:read"]))
):
    """
    事件捕获系统健康检查
    
    检查事件捕获系统的整体健康状态和各组件状态。
    """
    
    capture_system = get_complete_capture_system()
    if not capture_system:
        return HealthCheckResponse(
            status="unavailable",
            capture_enabled=False,
            overall_health="critical",
            components={"capture_system": "not_initialized"},
            capture_rate=0.0,
            queue_status={"size": 0, "status": "unknown"},
            last_check=datetime.utcnow().isoformat()
        )
    
    try:
        # 执行健康检查
        health_status = await capture_system._perform_health_checks()
        statistics = capture_system.get_capture_statistics()
        
        # 确定总体健康状态
        overall_health = "healthy"
        if any(status in ["degraded", "overloaded"] for status in health_status.values()):
            overall_health = "degraded"
        if any(status in ["critical", "failed"] for status in health_status.values()):
            overall_health = "critical"
        
        # 队列状态
        queue_size = capture_system.event_queue.qsize()
        queue_status = {
            "size": queue_size,
            "max_size": 10000,
            "utilization": queue_size / 10000,
            "status": "healthy" if queue_size < 8000 else "overloaded"
        }
        
        return HealthCheckResponse(
            status="healthy" if capture_system.capture_enabled else "disabled",
            capture_enabled=capture_system.capture_enabled,
            overall_health=overall_health,
            components=health_status,
            capture_rate=statistics['overall_metrics']['capture_rate'],
            queue_status=queue_status,
            last_check=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        return HealthCheckResponse(
            status="error",
            capture_enabled=False,
            overall_health="critical",
            components={"error": str(e)},
            capture_rate=0.0,
            queue_status={"size": 0, "status": "error"},
            last_check=datetime.utcnow().isoformat()
        )


@router.get("/coverage-analysis")
async def get_capture_coverage_analysis(
    tenant_id: str = Query(..., description="Tenant ID"),
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user_with_permissions(["security:read"]))
):
    """
    获取事件捕获覆盖率分析
    
    分析指定时间窗口内的事件捕获覆盖情况，识别可能的遗漏。
    """
    
    capture_system = get_complete_capture_system()
    if not capture_system:
        raise HTTPException(status_code=503, detail="Event capture system not available")
    
    try:
        # 获取时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # 分析各事件源的覆盖情况
        coverage_analysis = {}
        
        for source in EventSource:
            source_metrics = capture_system.source_metrics[source]
            
            coverage_analysis[source.value] = {
                "total_events": source_metrics.total_events,
                "captured_events": source_metrics.captured_events,
                "failed_events": source_metrics.failed_events,
                "capture_rate": source_metrics.capture_rate,
                "coverage_status": "good" if source_metrics.capture_rate >= 0.95 else "needs_attention"
            }
        
        # 计算总体覆盖率
        overall_stats = capture_system.capture_metrics
        overall_coverage = {
            "total_events": overall_stats.total_events,
            "captured_events": overall_stats.captured_events,
            "overall_capture_rate": overall_stats.capture_rate,
            "coverage_grade": "A" if overall_stats.capture_rate >= 0.98 else 
                           "B" if overall_stats.capture_rate >= 0.95 else
                           "C" if overall_stats.capture_rate >= 0.90 else "D"
        }
        
        # 识别问题区域
        problem_areas = []
        for source, analysis in coverage_analysis.items():
            if analysis["capture_rate"] < 0.90:
                problem_areas.append({
                    "source": source,
                    "issue": "low_capture_rate",
                    "capture_rate": analysis["capture_rate"],
                    "recommendation": "Check source listener and processing pipeline"
                })
        
        # 记录审计日志
        audit_service = AuditService()
        await audit_service.log_system_event(
            user_id=current_user.get("user_id"),
            tenant_id=tenant_id,
            action="get_coverage_analysis",
            resource_type="capture_system",
            details={
                "time_window_hours": time_window_hours,
                "overall_capture_rate": overall_stats.capture_rate
            }
        )
        
        return {
            "tenant_id": tenant_id,
            "analysis_period": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_hours": time_window_hours
            },
            "overall_coverage": overall_coverage,
            "source_coverage": coverage_analysis,
            "problem_areas": problem_areas,
            "recommendations": [
                "Monitor capture rates regularly",
                "Investigate sources with <95% capture rate",
                "Ensure all event sources are properly configured",
                "Review failed events for patterns"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze capture coverage: {str(e)}")


@router.post("/retry-failed-events")
async def retry_failed_events(
    tenant_id: str = Query(..., description="Tenant ID"),
    event_ids: Optional[List[str]] = Query(None, description="Specific event IDs to retry"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user_with_permissions(["security:write"]))
):
    """
    重试失败的事件
    
    手动触发失败事件的重试处理。
    """
    
    capture_system = get_complete_capture_system()
    if not capture_system:
        raise HTTPException(status_code=503, detail="Event capture system not available")
    
    try:
        # 获取要重试的事件
        if event_ids:
            # 重试指定的事件
            retry_records = [
                record for record in capture_system.capture_records.values()
                if (record.event_id in event_ids and 
                    record.status == CaptureStatus.FAILED and
                    record.metadata.get('tenant_id') == tenant_id)
            ]
        else:
            # 重试所有失败的事件
            retry_records = [
                record for record in capture_system.capture_records.values()
                if (record.status == CaptureStatus.FAILED and
                    record.metadata.get('tenant_id') == tenant_id)
            ]
        
        if not retry_records:
            return {
                "status": "no_events",
                "message": "No failed events found to retry",
                "retry_count": 0
            }
        
        # 后台任务重试事件
        async def retry_events_task():
            retry_count = 0
            for record in retry_records:
                try:
                    await capture_system._retry_event_capture(record)
                    retry_count += 1
                except Exception as e:
                    capture_system.logger.error(f"Failed to retry event {record.event_id}: {e}")
            
            capture_system.logger.info(f"Retried {retry_count} failed events for tenant {tenant_id}")
        
        background_tasks.add_task(retry_events_task)
        
        # 记录审计日志
        audit_service = AuditService()
        await audit_service.log_system_event(
            user_id=current_user.get("user_id"),
            tenant_id=tenant_id,
            action="retry_failed_events",
            resource_type="capture_system",
            details={
                "retry_count": len(retry_records),
                "specific_events": event_ids is not None
            }
        )
        
        return {
            "status": "success",
            "message": f"Initiated retry for {len(retry_records)} failed events",
            "retry_count": len(retry_records),
            "event_ids": [record.event_id for record in retry_records]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry failed events: {str(e)}")


@router.get("/performance-metrics")
async def get_capture_performance_metrics(
    tenant_id: str = Query(..., description="Tenant ID"),
    time_window_hours: int = Query(1, ge=1, le=24, description="Time window in hours"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user_with_permissions(["security:read"]))
):
    """
    获取事件捕获性能指标
    
    返回事件捕获系统的性能指标和趋势分析。
    """
    
    capture_system = get_complete_capture_system()
    if not capture_system:
        raise HTTPException(status_code=503, detail="Event capture system not available")
    
    try:
        statistics = capture_system.get_capture_statistics()
        
        # 计算性能指标
        performance_metrics = {
            "capture_throughput": {
                "events_per_second": statistics['overall_metrics']['total_events'] / (time_window_hours * 3600),
                "successful_captures_per_second": statistics['overall_metrics']['captured_events'] / (time_window_hours * 3600),
                "failed_captures_per_second": statistics['overall_metrics']['failed_events'] / (time_window_hours * 3600)
            },
            "system_efficiency": {
                "capture_success_rate": statistics['overall_metrics']['capture_rate'],
                "retry_rate": statistics['overall_metrics']['retry_events'] / max(statistics['overall_metrics']['total_events'], 1),
                "validation_failure_rate": statistics['overall_metrics']['validation_failures'] / max(statistics['overall_metrics']['total_events'], 1)
            },
            "queue_performance": {
                "current_queue_size": statistics['system_status']['queue_size'],
                "queue_utilization": statistics['system_status']['queue_size'] / 10000,
                "processing_capacity": "normal" if statistics['system_status']['queue_size'] < 5000 else "high"
            },
            "source_performance": {}
        }
        
        # 各源性能指标
        for source, metrics in statistics['source_metrics'].items():
            if metrics['total_events'] > 0:
                performance_metrics["source_performance"][source] = {
                    "capture_rate": metrics['capture_rate'],
                    "events_per_hour": metrics['total_events'] / time_window_hours,
                    "reliability_score": min(metrics['capture_rate'] * 100, 100)
                }
        
        # 性能评级
        overall_score = (
            performance_metrics["system_efficiency"]["capture_success_rate"] * 0.5 +
            (1 - performance_metrics["system_efficiency"]["retry_rate"]) * 0.3 +
            (1 - performance_metrics["system_efficiency"]["validation_failure_rate"]) * 0.2
        ) * 100
        
        performance_grade = "A" if overall_score >= 95 else \
                          "B" if overall_score >= 90 else \
                          "C" if overall_score >= 80 else "D"
        
        return {
            "tenant_id": tenant_id,
            "time_window_hours": time_window_hours,
            "performance_metrics": performance_metrics,
            "overall_performance_score": overall_score,
            "performance_grade": performance_grade,
            "recommendations": [
                "Maintain capture rate above 95%" if performance_metrics["system_efficiency"]["capture_success_rate"] < 0.95 else "Capture rate is optimal",
                "Monitor queue utilization" if performance_metrics["queue_performance"]["queue_utilization"] > 0.8 else "Queue utilization is healthy",
                "Review retry patterns" if performance_metrics["system_efficiency"]["retry_rate"] > 0.1 else "Retry rate is acceptable"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.post("/configuration")
async def update_capture_configuration(
    tenant_id: str = Query(..., description="Tenant ID"),
    config: CaptureConfigurationRequest = ...,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_user_with_permissions(["security:admin"]))
):
    """
    更新事件捕获配置
    
    允许管理员调整事件捕获系统的配置参数。
    """
    
    capture_system = get_complete_capture_system()
    if not capture_system:
        raise HTTPException(status_code=503, detail="Event capture system not available")
    
    try:
        updated_settings = {}
        
        # 更新配置
        if config.capture_enabled is not None:
            capture_system.capture_enabled = config.capture_enabled
            updated_settings['capture_enabled'] = config.capture_enabled
        
        if config.max_retry_attempts is not None:
            capture_system.max_retry_attempts = config.max_retry_attempts
            updated_settings['max_retry_attempts'] = config.max_retry_attempts
        
        if config.retry_delay_seconds is not None:
            capture_system.retry_delay_seconds = config.retry_delay_seconds
            updated_settings['retry_delay_seconds'] = config.retry_delay_seconds
        
        if config.validation_enabled is not None:
            capture_system.validation_enabled = config.validation_enabled
            updated_settings['validation_enabled'] = config.validation_enabled
        
        if config.alert_threshold is not None:
            capture_system.alert_threshold = config.alert_threshold
            updated_settings['alert_threshold'] = config.alert_threshold
        
        # 记录审计日志
        audit_service = AuditService()
        await audit_service.log_system_event(
            user_id=current_user.get("user_id"),
            tenant_id=tenant_id,
            action="update_capture_configuration",
            resource_type="capture_system",
            details={"updated_settings": updated_settings}
        )
        
        return {
            "status": "success",
            "message": "Capture configuration updated successfully",
            "updated_settings": updated_settings,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


# 导出路由器
__all__ = ["router"]