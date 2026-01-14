"""
Audit and Compliance API Router for SuperInsight Platform.

Provides REST API endpoints for audit log management and compliance reporting.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io

from src.security.audit_logger import AuditLogger, IntegrityResult
from src.security.compliance_reporter import ComplianceReporter


router = APIRouter(prefix="/api/v1", tags=["Audit & Compliance"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    id: str
    event_type: str
    user_id: str
    resource: Optional[str]
    action: Optional[str]
    result: Optional[bool]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    timestamp: datetime
    hash: Optional[str]


class AuditLogQueryResponse(BaseModel):
    """Audit log query response."""
    logs: List[AuditLogResponse]
    total: int
    offset: int
    limit: int


class AuditLogExportRequest(BaseModel):
    """Audit log export request."""
    start_time: datetime = Field(..., description="Export start time")
    end_time: datetime = Field(..., description="Export end time")
    format: str = Field("json", description="Export format: json, csv")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    event_type: Optional[str] = Field(None, description="Filter by event type")


class IntegrityVerificationRequest(BaseModel):
    """Integrity verification request."""
    start_id: Optional[str] = Field(None, description="Starting log entry ID")
    end_id: Optional[str] = Field(None, description="Ending log entry ID")
    start_time: Optional[datetime] = Field(None, description="Starting timestamp")
    end_time: Optional[datetime] = Field(None, description="Ending timestamp")


class IntegrityVerificationResponse(BaseModel):
    """Integrity verification response."""
    valid: bool
    verified_count: int
    error: Optional[str]
    message: Optional[str]
    corrupted_entry_id: Optional[str]


class AuditStatisticsResponse(BaseModel):
    """Audit statistics response."""
    total_logs: int
    event_types: Dict[str, int]
    results: Dict[str, int]
    period: Dict[str, Optional[str]]


class ComplianceReportRequest(BaseModel):
    """Compliance report request."""
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    include_details: bool = Field(True, description="Include detailed findings")


class ComplianceReportResponse(BaseModel):
    """Compliance report response."""
    report_id: str
    report_type: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    summary: Dict[str, Any]
    findings: Optional[List[Dict[str, Any]]]
    recommendations: Optional[List[str]]
    compliance_score: Optional[float]


class AccessReportRequest(BaseModel):
    """Access report request."""
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    resource_pattern: Optional[str] = Field(None, description="Filter by resource pattern")


class PermissionChangeReportRequest(BaseModel):
    """Permission change report request."""
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    user_id: Optional[str] = Field(None, description="Filter by user ID")


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_audit_logger() -> AuditLogger:
    """Get audit logger instance."""
    from src.database.connection import get_db_session
    
    db = await get_db_session()
    return AuditLogger(db)


async def get_compliance_reporter() -> ComplianceReporter:
    """Get compliance reporter instance."""
    from src.database.connection import get_db_session
    
    db = await get_db_session()
    audit_logger = AuditLogger(db)
    return ComplianceReporter(db, audit_logger)


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.get("/audit/logs", response_model=AuditLogQueryResponse)
async def query_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    action: Optional[str] = Query(None, description="Filter by action"),
    result: Optional[bool] = Query(None, description="Filter by result"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time"),
    end_time: Optional[datetime] = Query(None, description="Filter by end time"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Query audit logs with filtering.
    
    Supports filtering by user, event type, resource, action, result,
    time range, IP address, and session ID.
    """
    try:
        logs = await audit_logger.query_logs(
            user_id=user_id,
            event_type=event_type,
            resource=resource,
            action=action,
            result=result,
            start_time=start_time,
            end_time=end_time,
            ip_address=ip_address,
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        log_responses = [
            AuditLogResponse(
                id=str(log.id),
                event_type=log.event_type,
                user_id=log.user_id,
                resource=log.resource,
                action=log.action,
                result=log.result,
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                session_id=log.session_id,
                timestamp=log.timestamp,
                hash=log.hash
            )
            for log in logs
        ]
        
        return AuditLogQueryResponse(
            logs=log_responses,
            total=len(log_responses),  # In production, get actual total count
            offset=offset,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/audit/logs/export")
async def export_audit_logs(
    request: AuditLogExportRequest,
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Export audit logs in specified format.
    
    Supports JSON and CSV formats.
    """
    try:
        if request.format.lower() not in ["json", "csv"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid format. Supported: json, csv"
            )
        
        data = await audit_logger.export_logs(
            start_time=request.start_time,
            end_time=request.end_time,
            format=request.format,
            user_id=request.user_id,
            event_type=request.event_type
        )
        
        # Determine content type
        content_type = "application/json" if request.format.lower() == "json" else "text/csv"
        filename = f"audit_logs_{request.start_time.date()}_{request.end_time.date()}.{request.format.lower()}"
        
        return StreamingResponse(
            io.BytesIO(data),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/audit/verify-integrity", response_model=IntegrityVerificationResponse)
async def verify_audit_integrity(
    request: IntegrityVerificationRequest,
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Verify integrity of audit log chain.
    
    Checks hash chain to detect any tampering with audit logs.
    """
    try:
        result = await audit_logger.verify_integrity(
            start_id=request.start_id,
            end_id=request.end_id,
            start_time=request.start_time,
            end_time=request.end_time
        )
        
        return IntegrityVerificationResponse(
            valid=result.valid,
            verified_count=result.verified_count,
            error=result.error,
            message=result.message,
            corrupted_entry_id=result.corrupted_entry_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/audit/statistics", response_model=AuditStatisticsResponse)
async def get_audit_statistics(
    start_time: Optional[datetime] = Query(None, description="Statistics start time"),
    end_time: Optional[datetime] = Query(None, description="Statistics end time"),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Get audit log statistics.
    """
    try:
        stats = await audit_logger.get_statistics(
            start_time=start_time,
            end_time=end_time
        )
        
        return AuditStatisticsResponse(
            total_logs=stats["total_logs"],
            event_types=stats["event_types"],
            results=stats["results"],
            period=stats["period"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/audit/retention")
async def apply_retention_policy(
    retention_days: int = Query(..., ge=1, le=3650, description="Retention period in days"),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Apply audit log retention policy.
    
    Archives or removes logs older than the specified retention period.
    """
    try:
        archived_count = await audit_logger.apply_retention_policy(retention_days)
        
        return {
            "success": True,
            "archived_count": archived_count,
            "retention_days": retention_days
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# Compliance Report Endpoints
# ============================================================================

@router.post("/compliance/reports/gdpr", response_model=ComplianceReportResponse)
async def generate_gdpr_report(
    request: ComplianceReportRequest,
    compliance_reporter: ComplianceReporter = Depends(get_compliance_reporter)
):
    """
    Generate GDPR compliance report.
    
    Analyzes data access patterns, consent management, and data subject rights.
    """
    try:
        report = await compliance_reporter.generate_gdpr_report(
            start_date=request.start_date,
            end_date=request.end_date,
            include_details=request.include_details
        )
        
        return ComplianceReportResponse(
            report_id=str(report.id),
            report_type="gdpr",
            generated_at=report.generated_at,
            period_start=request.start_date,
            period_end=request.end_date,
            summary=report.summary,
            findings=report.findings if request.include_details else None,
            recommendations=report.recommendations,
            compliance_score=report.compliance_score
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/compliance/reports/soc2", response_model=ComplianceReportResponse)
async def generate_soc2_report(
    request: ComplianceReportRequest,
    compliance_reporter: ComplianceReporter = Depends(get_compliance_reporter)
):
    """
    Generate SOC 2 compliance report.
    
    Analyzes security controls, availability, processing integrity,
    confidentiality, and privacy.
    """
    try:
        report = await compliance_reporter.generate_soc2_report(
            start_date=request.start_date,
            end_date=request.end_date,
            include_details=request.include_details
        )
        
        return ComplianceReportResponse(
            report_id=str(report.id),
            report_type="soc2",
            generated_at=report.generated_at,
            period_start=request.start_date,
            period_end=request.end_date,
            summary=report.summary,
            findings=report.findings if request.include_details else None,
            recommendations=report.recommendations,
            compliance_score=report.compliance_score
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/compliance/reports/access", response_model=ComplianceReportResponse)
async def generate_access_report(
    request: AccessReportRequest,
    compliance_reporter: ComplianceReporter = Depends(get_compliance_reporter)
):
    """
    Generate data access report.
    
    Provides detailed analysis of who accessed what data and when.
    """
    try:
        report = await compliance_reporter.generate_access_report(
            start_date=request.start_date,
            end_date=request.end_date,
            user_id=request.user_id,
            resource_pattern=request.resource_pattern
        )
        
        return ComplianceReportResponse(
            report_id=str(report.id),
            report_type="access",
            generated_at=report.generated_at,
            period_start=request.start_date,
            period_end=request.end_date,
            summary=report.summary,
            findings=report.findings,
            recommendations=report.recommendations,
            compliance_score=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/compliance/reports/permission-changes", response_model=ComplianceReportResponse)
async def generate_permission_change_report(
    request: PermissionChangeReportRequest,
    compliance_reporter: ComplianceReporter = Depends(get_compliance_reporter)
):
    """
    Generate permission change report.
    
    Tracks all permission and role changes for audit purposes.
    """
    try:
        report = await compliance_reporter.generate_permission_change_report(
            start_date=request.start_date,
            end_date=request.end_date,
            user_id=request.user_id
        )
        
        return ComplianceReportResponse(
            report_id=str(report.id),
            report_type="permission_changes",
            generated_at=report.generated_at,
            period_start=request.start_date,
            period_end=request.end_date,
            summary=report.summary,
            findings=report.findings,
            recommendations=report.recommendations,
            compliance_score=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/compliance/reports")
async def list_compliance_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    compliance_reporter: ComplianceReporter = Depends(get_compliance_reporter)
):
    """
    List generated compliance reports.
    """
    try:
        reports = await compliance_reporter.list_reports(
            report_type=report_type,
            limit=limit,
            offset=offset
        )
        
        return {
            "reports": [
                {
                    "id": str(r.id),
                    "report_type": r.report_type,
                    "generated_at": r.generated_at.isoformat(),
                    "period_start": r.period_start.isoformat(),
                    "period_end": r.period_end.isoformat(),
                    "compliance_score": r.compliance_score
                }
                for r in reports
            ],
            "total": len(reports),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/compliance/reports/{report_id}")
async def get_compliance_report(
    report_id: str,
    compliance_reporter: ComplianceReporter = Depends(get_compliance_reporter)
):
    """
    Get a specific compliance report.
    """
    try:
        report = await compliance_reporter.get_report(report_id)
        
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        
        return ComplianceReportResponse(
            report_id=str(report.id),
            report_type=report.report_type,
            generated_at=report.generated_at,
            period_start=report.period_start,
            period_end=report.period_end,
            summary=report.summary,
            findings=report.findings,
            recommendations=report.recommendations,
            compliance_score=report.compliance_score
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
