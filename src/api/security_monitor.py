"""
Security Monitor API Router for SuperInsight Platform.

Provides REST API endpoints for security monitoring and event management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from src.security.security_monitor import SecurityMonitor, SecurityEvent, SecurityPostureReport
from src.security.audit_logger import AuditLogger


router = APIRouter(prefix="/api/v1/security", tags=["Security Monitor"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class SecurityEventResponse(BaseModel):
    """Security event response."""
    id: str
    event_type: str
    severity: str
    user_id: str
    details: Dict[str, Any]
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    resolution_notes: Optional[str]


class SecurityEventListResponse(BaseModel):
    """Security event list response."""
    events: List[SecurityEventResponse]
    total: int
    offset: int
    limit: int


class ResolveEventRequest(BaseModel):
    """Resolve security event request."""
    resolution_notes: str = Field(..., min_length=1, max_length=2000, description="Resolution notes")
    resolved_by: str = Field(..., description="User ID who resolved the event")


class SecurityPostureResponse(BaseModel):
    """Security posture response."""
    risk_score: float
    events_by_type: Dict[str, int]
    trend: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime


class SecurityThresholdsRequest(BaseModel):
    """Security thresholds configuration request."""
    failed_login_attempts: Optional[int] = Field(None, ge=1, le=100)
    failed_login_window_minutes: Optional[int] = Field(None, ge=1, le=1440)
    mass_download_threshold: Optional[int] = Field(None, ge=1, le=10000)
    mass_download_window_minutes: Optional[int] = Field(None, ge=1, le=1440)
    high_privilege_roles: Optional[List[str]] = None


class SecurityThresholdsResponse(BaseModel):
    """Security thresholds response."""
    failed_login_attempts: int
    failed_login_window_minutes: int
    mass_download_threshold: int
    mass_download_window_minutes: int
    high_privilege_roles: List[str]


class SecurityAlertResponse(BaseModel):
    """Security alert response."""
    id: str
    event_id: str
    alert_type: str
    severity: str
    message: str
    sent_at: datetime
    recipients: List[str]


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_security_monitor() -> SecurityMonitor:
    """Get security monitor instance."""
    from src.database.connection import get_db_session
    
    db = await get_db_session()
    audit_logger = AuditLogger(db)
    return SecurityMonitor(db, audit_logger)


# ============================================================================
# Security Event Endpoints
# ============================================================================

@router.get("/events", response_model=SecurityEventListResponse)
async def list_security_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    status: Optional[str] = Query(None, description="Filter by status: open, investigating, resolved"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    security_monitor: SecurityMonitor = Depends(get_security_monitor)
):
    """
    List security events with filtering.
    
    Supports filtering by event type, severity, status, user, and time range.
    """
    try:
        from sqlalchemy import select, and_, desc
        from src.models.security import SecurityEventModel
        
        stmt = select(SecurityEventModel)
        conditions = []
        
        if event_type:
            conditions.append(SecurityEventModel.event_type == event_type)
        if severity:
            conditions.append(SecurityEventModel.severity == severity)
        if status:
            conditions.append(SecurityEventModel.status == status)
        if user_id:
            conditions.append(SecurityEventModel.user_id == user_id)
        if start_time:
            conditions.append(SecurityEventModel.created_at >= start_time)
        if end_time:
            conditions.append(SecurityEventModel.created_at <= end_time)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(desc(SecurityEventModel.created_at))
        stmt = stmt.limit(limit).offset(offset)
        
        result = await security_monitor.db.execute(stmt)
        events = list(result.scalars().all())
        
        event_responses = [
            SecurityEventResponse(
                id=str(e.id),
                event_type=e.event_type,
                severity=e.severity,
                user_id=e.user_id,
                details=e.details or {},
                status=e.status,
                created_at=e.created_at,
                resolved_at=e.resolved_at,
                resolved_by=e.resolved_by,
                resolution_notes=e.resolution_notes
            )
            for e in events
        ]
        
        return SecurityEventListResponse(
            events=event_responses,
            total=len(event_responses),
            offset=offset,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/events/{event_id}", response_model=SecurityEventResponse)
async def get_security_event(
    event_id: str,
    security_monitor: SecurityMonitor = Depends(get_security_monitor)
):
    """
    Get a specific security event.
    """
    try:
        from sqlalchemy import select
        from src.models.security import SecurityEventModel
        
        stmt = select(SecurityEventModel).where(SecurityEventModel.id == event_id)
        result = await security_monitor.db.execute(stmt)
        event = result.scalar_one_or_none()
        
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        
        return SecurityEventResponse(
            id=str(event.id),
            event_type=event.event_type,
            severity=event.severity,
            user_id=event.user_id,
            details=event.details or {},
            status=event.status,
            created_at=event.created_at,
            resolved_at=event.resolved_at,
            resolved_by=event.resolved_by,
            resolution_notes=event.resolution_notes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/events/{event_id}/resolve", response_model=SecurityEventResponse)
async def resolve_security_event(
    event_id: str,
    request: ResolveEventRequest,
    security_monitor: SecurityMonitor = Depends(get_security_monitor)
):
    """
    Resolve a security event.
    
    Marks the event as resolved with resolution notes.
    """
    try:
        from sqlalchemy import select
        from src.models.security import SecurityEventModel
        
        stmt = select(SecurityEventModel).where(SecurityEventModel.id == event_id)
        result = await security_monitor.db.execute(stmt)
        event = result.scalar_one_or_none()
        
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        
        # Update event
        event.status = "resolved"
        event.resolved_at = datetime.utcnow()
        event.resolved_by = request.resolved_by
        event.resolution_notes = request.resolution_notes
        
        await security_monitor.db.commit()
        
        # Log the resolution
        await security_monitor.audit_logger.log(
            event_type="security_event_resolved",
            user_id=request.resolved_by,
            resource=f"security_event:{event_id}",
            action="resolve",
            result=True,
            details={
                "event_type": event.event_type,
                "severity": event.severity,
                "resolution_notes": request.resolution_notes
            }
        )
        
        return SecurityEventResponse(
            id=str(event.id),
            event_type=event.event_type,
            severity=event.severity,
            user_id=event.user_id,
            details=event.details or {},
            status=event.status,
            created_at=event.created_at,
            resolved_at=event.resolved_at,
            resolved_by=event.resolved_by,
            resolution_notes=event.resolution_notes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/events/{event_id}/investigate", response_model=SecurityEventResponse)
async def mark_event_investigating(
    event_id: str,
    investigator_id: str = Query(..., description="User ID of investigator"),
    security_monitor: SecurityMonitor = Depends(get_security_monitor)
):
    """
    Mark a security event as under investigation.
    """
    try:
        from sqlalchemy import select
        from src.models.security import SecurityEventModel
        
        stmt = select(SecurityEventModel).where(SecurityEventModel.id == event_id)
        result = await security_monitor.db.execute(stmt)
        event = result.scalar_one_or_none()
        
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        
        # Update event
        event.status = "investigating"
        
        await security_monitor.db.commit()
        
        # Log the status change
        await security_monitor.audit_logger.log(
            event_type="security_event_investigating",
            user_id=investigator_id,
            resource=f"security_event:{event_id}",
            action="investigate",
            result=True,
            details={
                "event_type": event.event_type,
                "severity": event.severity
            }
        )
        
        return SecurityEventResponse(
            id=str(event.id),
            event_type=event.event_type,
            severity=event.severity,
            user_id=event.user_id,
            details=event.details or {},
            status=event.status,
            created_at=event.created_at,
            resolved_at=event.resolved_at,
            resolved_by=event.resolved_by,
            resolution_notes=event.resolution_notes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Security Posture Endpoints
# ============================================================================

@router.get("/posture", response_model=SecurityPostureResponse)
async def get_security_posture(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    security_monitor: SecurityMonitor = Depends(get_security_monitor)
):
    """
    Get current security posture report.
    
    Provides risk score, event analysis, trends, and recommendations.
    """
    try:
        report = await security_monitor.generate_security_posture_report(days=days)
        
        return SecurityPostureResponse(
            risk_score=report.risk_score,
            events_by_type=report.events_by_type,
            trend=report.trend,
            recommendations=report.recommendations,
            generated_at=report.generated_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/posture/summary")
async def get_security_summary(
    security_monitor: SecurityMonitor = Depends(get_security_monitor)
):
    """
    Get quick security summary.
    
    Returns key metrics for dashboard display.
    """
    try:
        from sqlalchemy import select, func, and_
        from src.models.security import SecurityEventModel
        from datetime import timedelta
        
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        # Count open events
        open_stmt = select(func.count(SecurityEventModel.id)).where(
            SecurityEventModel.status == "open"
        )
        result = await security_monitor.db.execute(open_stmt)
        open_events = result.scalar()
        
        # Count critical events in last 24h
        critical_stmt = select(func.count(SecurityEventModel.id)).where(
            and_(
                SecurityEventModel.severity == "critical",
                SecurityEventModel.created_at >= last_24h
            )
        )
        result = await security_monitor.db.execute(critical_stmt)
        critical_24h = result.scalar()
        
        # Count events in last 7 days
        week_stmt = select(func.count(SecurityEventModel.id)).where(
            SecurityEventModel.created_at >= last_7d
        )
        result = await security_monitor.db.execute(week_stmt)
        events_7d = result.scalar()
        
        # Get posture report for risk score
        report = await security_monitor.generate_security_posture_report(days=7)
        
        return {
            "open_events": open_events,
            "critical_events_24h": critical_24h,
            "events_last_7_days": events_7d,
            "risk_score": report.risk_score,
            "risk_level": "critical" if report.risk_score > 70 else "high" if report.risk_score > 40 else "medium" if report.risk_score > 20 else "low",
            "generated_at": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Security Configuration Endpoints
# ============================================================================

@router.get("/thresholds", response_model=SecurityThresholdsResponse)
async def get_security_thresholds(
    security_monitor: SecurityMonitor = Depends(get_security_monitor)
):
    """
    Get current security monitoring thresholds.
    """
    return SecurityThresholdsResponse(
        failed_login_attempts=security_monitor.thresholds["failed_login_attempts"],
        failed_login_window_minutes=security_monitor.thresholds["failed_login_window_minutes"],
        mass_download_threshold=security_monitor.thresholds["mass_download_threshold"],
        mass_download_window_minutes=security_monitor.thresholds["mass_download_window_minutes"],
        high_privilege_roles=security_monitor.thresholds["high_privilege_roles"]
    )


@router.put("/thresholds", response_model=SecurityThresholdsResponse)
async def update_security_thresholds(
    request: SecurityThresholdsRequest,
    admin_user_id: str = Query(..., description="Admin user ID making the change"),
    security_monitor: SecurityMonitor = Depends(get_security_monitor)
):
    """
    Update security monitoring thresholds.
    
    Requires admin privileges.
    """
    try:
        # Update thresholds
        if request.failed_login_attempts is not None:
            security_monitor.thresholds["failed_login_attempts"] = request.failed_login_attempts
        if request.failed_login_window_minutes is not None:
            security_monitor.thresholds["failed_login_window_minutes"] = request.failed_login_window_minutes
        if request.mass_download_threshold is not None:
            security_monitor.thresholds["mass_download_threshold"] = request.mass_download_threshold
        if request.mass_download_window_minutes is not None:
            security_monitor.thresholds["mass_download_window_minutes"] = request.mass_download_window_minutes
        if request.high_privilege_roles is not None:
            security_monitor.thresholds["high_privilege_roles"] = request.high_privilege_roles
        
        # Log the change
        await security_monitor.audit_logger.log(
            event_type="security_thresholds_updated",
            user_id=admin_user_id,
            resource="security_thresholds",
            action="update",
            result=True,
            details={
                "new_thresholds": security_monitor.thresholds
            }
        )
        
        return SecurityThresholdsResponse(
            failed_login_attempts=security_monitor.thresholds["failed_login_attempts"],
            failed_login_window_minutes=security_monitor.thresholds["failed_login_window_minutes"],
            mass_download_threshold=security_monitor.thresholds["mass_download_threshold"],
            mass_download_window_minutes=security_monitor.thresholds["mass_download_window_minutes"],
            high_privilege_roles=security_monitor.thresholds["high_privilege_roles"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Event Statistics Endpoints
# ============================================================================

@router.get("/statistics")
async def get_security_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    security_monitor: SecurityMonitor = Depends(get_security_monitor)
):
    """
    Get security event statistics.
    """
    try:
        from sqlalchemy import select, func, and_
        from src.models.security import SecurityEventModel
        from datetime import timedelta
        
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Events by severity
        severity_stmt = select(
            SecurityEventModel.severity,
            func.count(SecurityEventModel.id).label('count')
        ).where(
            SecurityEventModel.created_at >= start_time
        ).group_by(SecurityEventModel.severity)
        
        result = await security_monitor.db.execute(severity_stmt)
        by_severity = {row.severity: row.count for row in result}
        
        # Events by type
        type_stmt = select(
            SecurityEventModel.event_type,
            func.count(SecurityEventModel.id).label('count')
        ).where(
            SecurityEventModel.created_at >= start_time
        ).group_by(SecurityEventModel.event_type)
        
        result = await security_monitor.db.execute(type_stmt)
        by_type = {row.event_type: row.count for row in result}
        
        # Events by status
        status_stmt = select(
            SecurityEventModel.status,
            func.count(SecurityEventModel.id).label('count')
        ).where(
            SecurityEventModel.created_at >= start_time
        ).group_by(SecurityEventModel.status)
        
        result = await security_monitor.db.execute(status_stmt)
        by_status = {row.status: row.count for row in result}
        
        # Total count
        total_stmt = select(func.count(SecurityEventModel.id)).where(
            SecurityEventModel.created_at >= start_time
        )
        result = await security_monitor.db.execute(total_stmt)
        total = result.scalar()
        
        return {
            "period_days": days,
            "total_events": total,
            "by_severity": by_severity,
            "by_type": by_type,
            "by_status": by_status,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
