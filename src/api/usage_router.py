"""
Usage API Router for SuperInsight Platform.

Provides REST API endpoints for license usage monitoring.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db
from src.license.concurrent_user_controller import ConcurrentUserController
from src.license.resource_controller import ResourceController
from src.license.license_audit_logger import LicenseAuditLogger
from src.license.license_report_generator import LicenseReportGenerator
from src.license.license_manager import LicenseManager
from src.models.license import LicenseEventType
from src.schemas.license import (
    ConcurrentUsageInfo, ResourceUsageInfo, UserSession,
    RegisterSessionRequest, ForceLogoutRequest, LicenseUsageReport,
    UsageReportRequest, AuditLogFilter, AuditLogResponse
)


router = APIRouter(prefix="/api/v1/usage", tags=["Usage"])


def get_concurrent_controller(db: AsyncSession = Depends(get_db)) -> ConcurrentUserController:
    """Get concurrent user controller instance."""
    return ConcurrentUserController(db)


def get_resource_controller(db: AsyncSession = Depends(get_db)) -> ResourceController:
    """Get resource controller instance."""
    return ResourceController(db)


def get_audit_logger(db: AsyncSession = Depends(get_db)) -> LicenseAuditLogger:
    """Get audit logger instance."""
    return LicenseAuditLogger(db)


def get_report_generator(db: AsyncSession = Depends(get_db)) -> LicenseReportGenerator:
    """Get report generator instance."""
    return LicenseReportGenerator(db)


def get_license_manager(db: AsyncSession = Depends(get_db)) -> LicenseManager:
    """Get license manager instance."""
    return LicenseManager(db)


# ============================================================================
# Concurrent User Endpoints
# ============================================================================

@router.get("/concurrent", response_model=ConcurrentUsageInfo)
async def get_concurrent_usage(
    controller: ConcurrentUserController = Depends(get_concurrent_controller),
    manager: LicenseManager = Depends(get_license_manager),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Get concurrent user usage information.
    
    Returns current concurrent user count, maximum allowed, and active sessions.
    """
    license = await manager.get_current_license()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active license found"
        )
    
    current_count = await controller.get_current_user_count()
    max_users = license.max_concurrent_users
    sessions = await controller.get_active_sessions()
    
    # Log usage check
    await audit_logger.log_concurrent_usage(
        current_users=current_count,
        max_users=max_users,
        license_id=license.id,
    )
    
    return ConcurrentUsageInfo(
        current_users=current_count,
        max_users=max_users,
        utilization_percent=round((current_count / max_users * 100) if max_users > 0 else 0, 2),
        active_sessions=sessions,
    )


@router.get("/sessions", response_model=List[UserSession])
async def get_active_sessions(
    controller: ConcurrentUserController = Depends(get_concurrent_controller),
):
    """Get list of all active sessions."""
    return await controller.get_active_sessions()


@router.get("/sessions/user/{user_id}", response_model=List[UserSession])
async def get_user_sessions(
    user_id: str,
    controller: ConcurrentUserController = Depends(get_concurrent_controller),
):
    """Get all sessions for a specific user."""
    return await controller.get_user_sessions(user_id)


@router.post("/sessions/register", response_model=UserSession)
async def register_session(
    request: RegisterSessionRequest,
    http_request: Request,
    controller: ConcurrentUserController = Depends(get_concurrent_controller),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Register a new user session.
    
    Creates a new session for concurrent user tracking.
    """
    # Add IP if not provided
    if not request.ip_address:
        forwarded = http_request.headers.get("X-Forwarded-For")
        if forwarded:
            request.ip_address = forwarded.split(",")[0].strip()
        elif http_request.client:
            request.ip_address = http_request.client.host
    
    session = await controller.register_user_session(request)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Concurrent user limit reached"
        )
    
    await audit_logger.log_session_event(
        event_type=LicenseEventType.SESSION_CREATED,
        user_id=request.user_id,
        session_id=request.session_id,
        ip_address=request.ip_address,
    )
    
    return session


@router.post("/sessions/{session_id}/release")
async def release_session(
    session_id: str,
    user_id: str,
    controller: ConcurrentUserController = Depends(get_concurrent_controller),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Release a user session."""
    success = await controller.release_user_session(user_id, session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    await audit_logger.log_session_event(
        event_type=LicenseEventType.SESSION_RELEASED,
        user_id=user_id,
        session_id=session_id,
    )
    
    return {"success": True, "message": "Session released"}


@router.post("/sessions/{session_id}/terminate")
async def terminate_session(
    session_id: str,
    reason: str = "Administrative action",
    controller: ConcurrentUserController = Depends(get_concurrent_controller),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Force terminate a specific session."""
    success = await controller.force_logout_session(session_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    await audit_logger.log_session_event(
        event_type=LicenseEventType.SESSION_FORCED_LOGOUT,
        user_id="admin",
        session_id=session_id,
        details={"reason": reason},
    )
    
    return {"success": True, "message": "Session terminated"}


@router.post("/sessions/user/{user_id}/logout")
async def force_logout_user(
    user_id: str,
    request: ForceLogoutRequest,
    controller: ConcurrentUserController = Depends(get_concurrent_controller),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Force logout all sessions for a user."""
    count = await controller.force_logout_user(user_id, request.reason)
    
    await audit_logger.log_session_event(
        event_type=LicenseEventType.SESSION_FORCED_LOGOUT,
        user_id=user_id,
        session_id="all",
        details={"reason": request.reason, "sessions_terminated": count},
    )
    
    return {"success": True, "sessions_terminated": count}


# ============================================================================
# Resource Usage Endpoints
# ============================================================================

@router.get("/resources", response_model=ResourceUsageInfo)
async def get_resource_usage(
    controller: ResourceController = Depends(get_resource_controller),
    manager: LicenseManager = Depends(get_license_manager),
    audit_logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """
    Get resource usage information.
    
    Returns CPU and storage usage with limits.
    """
    license = await manager.get_current_license()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active license found"
        )
    
    cpu_cores = controller.detect_cpu_cores()
    storage_gb = controller.detect_storage_usage_gb()
    
    # Log resource check
    await audit_logger.log_resource_usage(
        resource_type="cpu",
        current_value=cpu_cores,
        max_value=license.max_cpu_cores,
        license_id=license.id,
    )
    
    await audit_logger.log_resource_usage(
        resource_type="storage",
        current_value=int(storage_gb),
        max_value=license.max_storage_gb,
        license_id=license.id,
    )
    
    return ResourceUsageInfo(
        cpu_cores=cpu_cores,
        max_cpu_cores=license.max_cpu_cores,
        cpu_utilization_percent=round((cpu_cores / license.max_cpu_cores * 100) if license.max_cpu_cores > 0 else 0, 2),
        storage_gb=round(storage_gb, 2),
        max_storage_gb=license.max_storage_gb,
        storage_utilization_percent=round((storage_gb / license.max_storage_gb * 100) if license.max_storage_gb > 0 else 0, 2),
    )


@router.get("/resources/check")
async def check_all_resources(
    controller: ResourceController = Depends(get_resource_controller),
):
    """Check all resource limits."""
    return await controller.check_all_resources()


# ============================================================================
# Report Endpoints
# ============================================================================

@router.post("/report", response_model=LicenseUsageReport)
async def generate_usage_report(
    request: UsageReportRequest,
    license_id: Optional[UUID] = None,
    generator: LicenseReportGenerator = Depends(get_report_generator),
):
    """
    Generate license usage report.
    
    Creates a comprehensive report of license usage for the specified period.
    """
    try:
        return await generator.generate_usage_report(request, license_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/report/daily")
async def get_daily_summary(
    date: Optional[datetime] = None,
    generator: LicenseReportGenerator = Depends(get_report_generator),
):
    """Get daily usage summary."""
    if not date:
        date = datetime.utcnow()
    
    try:
        return await generator.generate_daily_summary(date)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/report/trend")
async def get_usage_trend(
    days: int = 30,
    generator: LicenseReportGenerator = Depends(get_report_generator),
):
    """Get usage trend for the last N days."""
    return await generator.generate_trend_report(days)


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.post("/audit/query", response_model=List[AuditLogResponse])
async def query_audit_logs(
    filter: AuditLogFilter,
    logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Query audit logs with filters."""
    return await logger.query_logs(filter)


@router.get("/audit/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: UUID,
    logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Get a specific audit log entry."""
    log = await logger.get_log_by_id(log_id)
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )
    
    return log


@router.get("/audit/stats")
async def get_audit_stats(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    license_id: Optional[UUID] = None,
    logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Get audit event statistics."""
    return await logger.get_event_counts(start_time, end_time, license_id)


@router.get("/audit/export")
async def export_audit_logs(
    start_time: datetime,
    end_time: datetime,
    format: str = "csv",
    license_id: Optional[UUID] = None,
    logger: LicenseAuditLogger = Depends(get_audit_logger),
):
    """Export audit logs to file."""
    data = await logger.export_logs(start_time, end_time, format, license_id)
    
    media_type = "application/json" if format == "json" else "text/csv"
    filename = f"audit_logs_{start_time.date()}_{end_time.date()}.{format}"
    
    return StreamingResponse(
        iter([data]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
