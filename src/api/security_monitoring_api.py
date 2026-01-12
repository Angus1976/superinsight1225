"""
Security Monitoring API endpoints for SuperInsight Platform.

Provides REST API endpoints for security event monitoring, threat detection,
and security analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.security.security_event_monitor import (
    security_event_monitor, SecurityEvent, SecurityEventType, ThreatLevel
)
from src.security.threat_detector import threat_detector
from src.security.audit_service import AuditService
from src.security.models import AuditLogModel


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/security-monitoring", tags=["Security Monitoring"])


# Request/Response Models

class SecurityEventResponse(BaseModel):
    """Security event response model."""
    event_id: str
    event_type: str
    threat_level: str
    tenant_id: str
    user_id: Optional[str]
    ip_address: Optional[str]
    timestamp: str
    description: str
    details: Dict[str, Any]
    resolved: bool
    resolution_notes: Optional[str]


class SecuritySummaryResponse(BaseModel):
    """Security summary response model."""
    tenant_id: str
    active_events_count: int
    threat_level_distribution: Dict[str, int]
    event_type_distribution: Dict[str, int]
    security_score: float
    last_scan_time: str
    monitoring_status: str


class ThreatDetectionRequest(BaseModel):
    """Threat detection request model."""
    tenant_id: str
    time_window_hours: int = Field(default=1, ge=1, le=168)
    detection_methods: Optional[List[str]] = None
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class SecurityAlertResponse(BaseModel):
    """Security alert response model."""
    alert_id: str
    alert_type: str
    severity: str
    tenant_id: str
    timestamp: str
    description: str
    affected_resources: List[str]
    recommended_actions: List[str]


class BehaviorProfileResponse(BaseModel):
    """User behavior profile response model."""
    user_id: str
    tenant_id: str
    profile_created: str
    last_updated: str
    action_patterns: Dict[str, float]
    resource_access_patterns: Dict[str, float]
    time_patterns: Dict[int, float]
    peak_activity_hours: List[int]
    risk_score: float
    anomaly_count: int


class SecurityMetricsResponse(BaseModel):
    """Security metrics response model."""
    total_events: int
    events_by_threat_level: Dict[str, int]
    events_by_type: Dict[str, int]
    detection_accuracy: float
    false_positive_rate: float
    response_time_avg: float
    monitoring_coverage: float


class EventResolutionRequest(BaseModel):
    """Event resolution request model."""
    resolution_notes: str
    resolved_by: str


# API Endpoints

@router.get("/events/{tenant_id}")
async def get_security_events(
    tenant_id: str = Path(..., description="Tenant ID"),
    threat_level: Optional[str] = Query(None, description="Filter by threat level"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    limit: int = Query(50, description="Maximum number of events", ge=1, le=1000),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get security events for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        threat_level: Filter by threat level (info, low, medium, high, critical)
        event_type: Filter by event type
        resolved: Filter by resolution status
        limit: Maximum number of events to return
        
    Returns:
        List of security events with metadata
    """
    try:
        # Get active events from monitor
        active_events = security_event_monitor.get_active_events(tenant_id)
        
        # Apply filters
        filtered_events = []
        for event in active_events:
            
            # Threat level filter
            if threat_level and event.threat_level.value != threat_level:
                continue
            
            # Event type filter
            if event_type and event.event_type.value != event_type:
                continue
            
            # Resolution status filter
            if resolved is not None and event.resolved != resolved:
                continue
            
            filtered_events.append(event)
        
        # Limit results
        filtered_events = filtered_events[:limit]
        
        # Format response
        events_data = []
        for event in filtered_events:
            events_data.append({
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "threat_level": event.threat_level.value,
                "tenant_id": event.tenant_id,
                "user_id": str(event.user_id) if event.user_id else None,
                "ip_address": event.ip_address,
                "timestamp": event.timestamp.isoformat(),
                "description": event.description,
                "details": event.details,
                "resolved": event.resolved,
                "resolution_notes": event.resolution_notes
            })
        
        return {
            "tenant_id": tenant_id,
            "total_events": len(events_data),
            "filters_applied": {
                "threat_level": threat_level,
                "event_type": event_type,
                "resolved": resolved
            },
            "events": events_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get security events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security events: {str(e)}")


@router.get("/events/{tenant_id}/{event_id}")
async def get_security_event_details(
    tenant_id: str = Path(..., description="Tenant ID"),
    event_id: str = Path(..., description="Event ID"),
    db: Session = Depends(get_db_session)
) -> SecurityEventResponse:
    """
    Get detailed information about a specific security event.
    
    Args:
        tenant_id: Tenant identifier
        event_id: Security event identifier
        
    Returns:
        Detailed security event information
    """
    try:
        # Find event in active events
        active_events = security_event_monitor.get_active_events(tenant_id)
        
        event = None
        for e in active_events:
            if e.event_id == event_id:
                event = e
                break
        
        if not event:
            # Check resolved events
            for e in security_event_monitor.resolved_events:
                if e.event_id == event_id and e.tenant_id == tenant_id:
                    event = e
                    break
        
        if not event:
            raise HTTPException(status_code=404, detail="Security event not found")
        
        return SecurityEventResponse(
            event_id=event.event_id,
            event_type=event.event_type.value,
            threat_level=event.threat_level.value,
            tenant_id=event.tenant_id,
            user_id=str(event.user_id) if event.user_id else None,
            ip_address=event.ip_address,
            timestamp=event.timestamp.isoformat(),
            description=event.description,
            details=event.details,
            resolved=event.resolved,
            resolution_notes=event.resolution_notes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security event details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security event details: {str(e)}")


@router.post("/events/{tenant_id}/{event_id}/resolve")
async def resolve_security_event(
    tenant_id: str = Path(..., description="Tenant ID"),
    event_id: str = Path(..., description="Event ID"),
    resolution_data: EventResolutionRequest = Body(...),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Resolve a security event.
    
    Args:
        tenant_id: Tenant identifier
        event_id: Security event identifier
        resolution_data: Resolution information
        
    Returns:
        Resolution confirmation
    """
    try:
        # Resolve the event
        success = security_event_monitor.resolve_event(
            event_id, 
            resolution_data.resolution_notes
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Security event not found or already resolved")
        
        # Log resolution to audit
        audit_service = AuditService()
        audit_service.log_system_event(
            event_type="security_event_resolution",
            description=f"Security event {event_id} resolved by {resolution_data.resolved_by}",
            tenant_id=tenant_id,
            details={
                "event_id": event_id,
                "resolved_by": resolution_data.resolved_by,
                "resolution_notes": resolution_data.resolution_notes,
                "resolution_timestamp": datetime.utcnow().isoformat()
            },
            db=db
        )
        
        return {
            "event_id": event_id,
            "status": "resolved",
            "resolved_by": resolution_data.resolved_by,
            "resolution_timestamp": datetime.utcnow().isoformat(),
            "message": "Security event successfully resolved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve security event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resolve security event: {str(e)}")


@router.get("/summary/{tenant_id}")
async def get_security_summary(
    tenant_id: str = Path(..., description="Tenant ID"),
    db: Session = Depends(get_db_session)
) -> SecuritySummaryResponse:
    """
    Get security summary for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Security summary with key metrics
    """
    try:
        summary = security_event_monitor.get_security_summary(tenant_id)
        
        return SecuritySummaryResponse(
            tenant_id=summary["tenant_id"],
            active_events_count=summary["active_events_count"],
            threat_level_distribution=summary["threat_level_distribution"],
            event_type_distribution=summary["event_type_distribution"],
            security_score=summary["security_score"],
            last_scan_time=summary["last_scan_time"],
            monitoring_status=summary["monitoring_status"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get security summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security summary: {str(e)}")


@router.post("/detect-threats")
async def detect_threats(
    request: ThreatDetectionRequest = Body(...),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Perform threat detection analysis.
    
    Args:
        request: Threat detection parameters
        
    Returns:
        Threat detection results
    """
    try:
        # Get recent audit logs
        time_threshold = datetime.utcnow() - timedelta(hours=request.time_window_hours)
        
        from sqlalchemy import select, and_
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == request.tenant_id,
                AuditLogModel.timestamp >= time_threshold
            )
        ).order_by(AuditLogModel.timestamp.desc())
        
        audit_logs = db.execute(stmt).scalars().all()
        
        # Perform threat detection
        detected_threats = await threat_detector.detect_threats(audit_logs, db)
        
        # Filter by confidence threshold
        filtered_threats = [
            (event, confidence) for event, confidence in detected_threats
            if confidence >= request.confidence_threshold
        ]
        
        # Format results
        threats_data = []
        for event, confidence in filtered_threats:
            threats_data.append({
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "threat_level": event.threat_level.value,
                "confidence_score": confidence,
                "description": event.description,
                "details": event.details,
                "timestamp": event.timestamp.isoformat()
            })
        
        return {
            "tenant_id": request.tenant_id,
            "detection_window_hours": request.time_window_hours,
            "confidence_threshold": request.confidence_threshold,
            "total_threats_detected": len(threats_data),
            "audit_logs_analyzed": len(audit_logs),
            "threats": threats_data,
            "detection_summary": {
                "high_confidence_threats": len([
                    t for t in filtered_threats if t[1] >= 0.8
                ]),
                "medium_confidence_threats": len([
                    t for t in filtered_threats if 0.5 <= t[1] < 0.8
                ]),
                "low_confidence_threats": len([
                    t for t in filtered_threats if t[1] < 0.5
                ])
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to detect threats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to detect threats: {str(e)}")


@router.get("/behavior-profile/{tenant_id}/{user_id}")
async def get_user_behavior_profile(
    tenant_id: str = Path(..., description="Tenant ID"),
    user_id: str = Path(..., description="User ID"),
    db: Session = Depends(get_db_session)
) -> Optional[BehaviorProfileResponse]:
    """
    Get user behavior profile.
    
    Args:
        tenant_id: Tenant identifier
        user_id: User identifier
        
    Returns:
        User behavior profile or None if not found
    """
    try:
        profile_data = threat_detector.get_user_behavior_profile(user_id)
        
        if not profile_data:
            raise HTTPException(status_code=404, detail="User behavior profile not found")
        
        # Verify tenant access
        if profile_data["tenant_id"] != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied to user profile")
        
        return BehaviorProfileResponse(
            user_id=profile_data["user_id"],
            tenant_id=profile_data["tenant_id"],
            profile_created=profile_data["profile_created"],
            last_updated=profile_data["last_updated"],
            action_patterns=profile_data["action_patterns"],
            resource_access_patterns=profile_data["resource_access_patterns"],
            time_patterns=profile_data["time_patterns"],
            peak_activity_hours=profile_data["peak_activity_hours"],
            risk_score=profile_data["risk_score"],
            anomaly_count=profile_data["anomaly_count"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user behavior profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user behavior profile: {str(e)}")


@router.get("/metrics/{tenant_id}")
async def get_security_metrics(
    tenant_id: str = Path(..., description="Tenant ID"),
    time_window_hours: int = Query(24, description="Time window in hours", ge=1, le=168),
    db: Session = Depends(get_db_session)
) -> SecurityMetricsResponse:
    """
    Get security metrics for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        time_window_hours: Time window for metrics calculation
        
    Returns:
        Security metrics and statistics
    """
    try:
        # Get events for the time window
        active_events = security_event_monitor.get_active_events(tenant_id)
        
        time_threshold = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_events = [
            event for event in active_events
            if event.timestamp >= time_threshold
        ]
        
        # Calculate metrics
        total_events = len(recent_events)
        
        # Events by threat level
        events_by_threat_level = {}
        for level in ThreatLevel:
            events_by_threat_level[level.value] = len([
                event for event in recent_events
                if event.threat_level == level
            ])
        
        # Events by type
        events_by_type = {}
        for event_type in SecurityEventType:
            events_by_type[event_type.value] = len([
                event for event in recent_events
                if event.event_type == event_type
            ])
        
        # Get detection statistics
        detection_stats = threat_detector.get_detection_statistics()
        
        # Calculate response time (simplified)
        resolved_events = [event for event in recent_events if event.resolved]
        avg_response_time = 0.0
        if resolved_events:
            # This would be calculated based on actual resolution times
            avg_response_time = 3600.0  # Placeholder: 1 hour average
        
        # Calculate monitoring coverage (simplified)
        monitoring_coverage = 0.95  # Placeholder: 95% coverage
        
        return SecurityMetricsResponse(
            total_events=total_events,
            events_by_threat_level=events_by_threat_level,
            events_by_type=events_by_type,
            detection_accuracy=detection_stats["detection_accuracy"],
            false_positive_rate=detection_stats["false_positives"] / max(detection_stats["total_detections"], 1),
            response_time_avg=avg_response_time,
            monitoring_coverage=monitoring_coverage
        )
        
    except Exception as e:
        logger.error(f"Failed to get security metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security metrics: {str(e)}")


@router.get("/alerts/{tenant_id}")
async def get_security_alerts(
    tenant_id: str = Path(..., description="Tenant ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    hours: int = Query(24, description="Time window in hours", ge=1, le=168),
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get security alerts for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        severity: Filter by severity level
        hours: Time window in hours
        
    Returns:
        List of security alerts
    """
    try:
        # Get recent high-priority events as alerts
        active_events = security_event_monitor.get_active_events(tenant_id)
        
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        alert_events = [
            event for event in active_events
            if (event.timestamp >= time_threshold and 
                event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL])
        ]
        
        # Apply severity filter
        if severity:
            alert_events = [
                event for event in alert_events
                if event.threat_level.value == severity
            ]
        
        # Format alerts
        alerts_data = []
        for event in alert_events:
            
            # Generate recommended actions based on event type
            recommended_actions = []
            if event.event_type == SecurityEventType.BRUTE_FORCE_ATTACK:
                recommended_actions = [
                    "Block suspicious IP addresses",
                    "Review authentication logs",
                    "Consider implementing rate limiting"
                ]
            elif event.event_type == SecurityEventType.PRIVILEGE_ESCALATION:
                recommended_actions = [
                    "Review user permissions",
                    "Audit role assignments",
                    "Investigate user activity"
                ]
            elif event.event_type == SecurityEventType.DATA_EXFILTRATION:
                recommended_actions = [
                    "Review data export logs",
                    "Check data access permissions",
                    "Notify data protection officer"
                ]
            else:
                recommended_actions = [
                    "Investigate event details",
                    "Review system logs",
                    "Consider security measures"
                ]
            
            alerts_data.append({
                "alert_id": event.event_id,
                "alert_type": event.event_type.value,
                "severity": event.threat_level.value,
                "tenant_id": event.tenant_id,
                "timestamp": event.timestamp.isoformat(),
                "description": event.description,
                "affected_resources": [event.details.get("resource_type", "unknown")],
                "recommended_actions": recommended_actions
            })
        
        return {
            "tenant_id": tenant_id,
            "time_window_hours": hours,
            "total_alerts": len(alerts_data),
            "severity_filter": severity,
            "alerts": alerts_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get security alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security alerts: {str(e)}")


@router.post("/monitoring/start")
async def start_security_monitoring(
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Start security monitoring.
    
    Returns:
        Monitoring start confirmation
    """
    try:
        await security_event_monitor.start_monitoring()
        
        return {
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Security monitoring started successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to start security monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start security monitoring: {str(e)}")


@router.post("/monitoring/stop")
async def stop_security_monitoring(
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Stop security monitoring.
    
    Returns:
        Monitoring stop confirmation
    """
    try:
        await security_event_monitor.stop_monitoring()
        
        return {
            "status": "stopped",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Security monitoring stopped successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop security monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop security monitoring: {str(e)}")


@router.get("/monitoring/status")
async def get_monitoring_status(
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get security monitoring status.
    
    Returns:
        Current monitoring status and statistics
    """
    try:
        # Get monitoring status
        monitoring_enabled = security_event_monitor.monitoring_enabled
        last_scan_time = security_event_monitor.last_scan_time
        
        # Get detection statistics
        detection_stats = threat_detector.get_detection_statistics()
        
        # Get active events count
        total_active_events = len(security_event_monitor.active_events)
        
        return {
            "monitoring_enabled": monitoring_enabled,
            "last_scan_time": last_scan_time.isoformat(),
            "total_active_events": total_active_events,
            "detection_statistics": detection_stats,
            "threat_patterns_loaded": len(security_event_monitor.threat_patterns),
            "behavior_profiles_count": len(threat_detector.behavior_profiles),
            "system_status": "healthy" if monitoring_enabled else "inactive"
        }
        
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {str(e)}")


@router.get("/health")
async def security_monitoring_health_check(
    db: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Security monitoring health check.
    
    Returns:
        Health status of security monitoring components
    """
    try:
        health_status = "healthy"
        health_issues = []
        
        # Check monitoring status
        if not security_event_monitor.monitoring_enabled:
            health_issues.append("Security monitoring is disabled")
            health_status = "degraded"
        
        # Check last scan time
        time_since_scan = (datetime.utcnow() - security_event_monitor.last_scan_time).total_seconds()
        if time_since_scan > 300:  # 5 minutes
            health_issues.append("Security scan is overdue")
            health_status = "degraded"
        
        # Check for critical events
        critical_events = [
            event for event in security_event_monitor.active_events.values()
            if event.threat_level == ThreatLevel.CRITICAL and not event.resolved
        ]
        
        if len(critical_events) > 10:
            health_issues.append("Too many unresolved critical security events")
            health_status = "critical"
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_enabled": security_event_monitor.monitoring_enabled,
            "last_scan_time": security_event_monitor.last_scan_time.isoformat(),
            "active_events_count": len(security_event_monitor.active_events),
            "critical_events_count": len(critical_events),
            "health_issues": health_issues,
            "components": {
                "event_monitor": "healthy" if security_event_monitor.monitoring_enabled else "inactive",
                "threat_detector": "healthy",
                "prometheus_metrics": "healthy"
            }
        }
        
    except Exception as e:
        logger.error(f"Security monitoring health check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "components": {
                "event_monitor": "error",
                "threat_detector": "error",
                "prometheus_metrics": "error"
            }
        }