"""
Permission Monitoring API endpoints for SuperInsight Platform.

Provides REST API endpoints for monitoring permission usage, analyzing patterns,
and generating permission-related reports and alerts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.database.connection import get_db_session
from src.security.permission_audit_integration import get_permission_audit_integration
from src.security.rbac_controller import RBACController

router = APIRouter(prefix="/api/permission-monitoring", tags=["Permission Monitoring"])


# Pydantic models for request/response
class PermissionUsageAnalysisResponse(BaseModel):
    """Response model for permission usage analysis."""
    analysis_period_days: int
    total_permission_events: int
    permission_checks: Dict[str, Any]
    role_changes: Dict[str, Any]
    batch_operations: Dict[str, Any]
    most_used_permissions: Dict[str, int]
    active_users_count: int
    security_alerts: Dict[str, int]


class PermissionReportRequest(BaseModel):
    """Request model for permission report generation."""
    tenant_id: str
    report_type: str = "summary"  # summary or detailed
    days: int = 30


class PermissionReportResponse(BaseModel):
    """Response model for permission reports."""
    report_type: str
    tenant_id: str
    period_days: int
    generated_at: str
    summary: Optional[Dict[str, Any]] = None
    detailed_analysis: Optional[Dict[str, Any]] = None
    recommendations: List[Dict[str, str]]


class SecurityAlertResponse(BaseModel):
    """Response model for security alerts."""
    alert_type: str
    severity: str
    tenant_id: str
    user_id: Optional[str]
    timestamp: str
    description: str
    event_details: Dict[str, Any]


class PermissionViolationResponse(BaseModel):
    """Response model for permission violations."""
    violation_type: str
    user_id: str
    tenant_id: str
    permission_name: str
    timestamp: str
    details: Dict[str, Any]
    risk_level: str


# Initialize services
permission_audit = get_permission_audit_integration()
rbac_controller = RBACController()


@router.get("/usage-analysis/{tenant_id}", response_model=PermissionUsageAnalysisResponse)
async def get_permission_usage_analysis(
    tenant_id: str,
    days: int = Query(30, description="Analysis period in days", ge=1, le=365),
    db: Session = Depends(get_db_session)
):
    """
    Get comprehensive permission usage analysis for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        days: Analysis period in days (1-365)
        
    Returns:
        Detailed permission usage analysis
    """
    try:
        analysis = await permission_audit.analyze_permission_usage(
            tenant_id=tenant_id,
            days=days,
            db=db
        )
        
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis["error"])
        
        return PermissionUsageAnalysisResponse(**analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze permission usage: {str(e)}")


@router.post("/generate-report", response_model=PermissionReportResponse)
async def generate_permission_report(
    request: PermissionReportRequest,
    db: Session = Depends(get_db_session)
):
    """
    Generate permission usage and security report.
    
    Args:
        request: Report generation request
        
    Returns:
        Generated permission report
    """
    try:
        report = await permission_audit.generate_permission_report(
            tenant_id=request.tenant_id,
            report_type=request.report_type,
            days=request.days,
            db=db
        )
        
        if "error" in report:
            raise HTTPException(status_code=400, detail=report["error"])
        
        return PermissionReportResponse(**report)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate permission report: {str(e)}")


@router.get("/security-alerts/{tenant_id}")
async def get_permission_security_alerts(
    tenant_id: str,
    hours: int = Query(24, description="Time window in hours", ge=1, le=168),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    db: Session = Depends(get_db_session)
):
    """
    Get permission-related security alerts for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        hours: Time window in hours (1-168)
        severity: Optional severity filter
        
    Returns:
        List of security alerts
    """
    try:
        from src.security.audit_service import AuditService
        from src.security.models import AuditLogModel, AuditAction
        from sqlalchemy import and_, select
        
        audit_service = AuditService()
        
        # Get permission-related security alerts
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_time,
                AuditLogModel.resource_type == "security_alert"
            )
        )
        
        alerts = db.execute(stmt).scalars().all()
        
        # Filter by severity if specified
        if severity:
            alerts = [
                alert for alert in alerts 
                if alert.details and alert.details.get("severity") == severity
            ]
        
        # Format alerts
        formatted_alerts = []
        for alert in alerts:
            if alert.details:
                formatted_alerts.append({
                    "alert_type": alert.details.get("alert_type", "unknown"),
                    "severity": alert.details.get("severity", "unknown"),
                    "tenant_id": alert.tenant_id,
                    "user_id": str(alert.user_id) if alert.user_id else None,
                    "timestamp": alert.timestamp.isoformat(),
                    "description": alert.details.get("description", ""),
                    "event_details": {
                        k: v for k, v in alert.details.items() 
                        if k not in ["alert_type", "severity", "description"]
                    }
                })
        
        return {
            "tenant_id": tenant_id,
            "time_window_hours": hours,
            "total_alerts": len(formatted_alerts),
            "alerts": formatted_alerts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get security alerts: {str(e)}")


@router.get("/violations/{tenant_id}")
async def get_permission_violations(
    tenant_id: str,
    days: int = Query(7, description="Time window in days", ge=1, le=30),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db_session)
):
    """
    Get permission violations and denied access attempts.
    
    Args:
        tenant_id: Tenant identifier
        days: Time window in days (1-30)
        user_id: Optional user ID filter
        
    Returns:
        List of permission violations
    """
    try:
        from src.security.models import AuditLogModel, AuditAction
        from sqlalchemy import and_, select
        
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Get permission denial events
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_time,
                AuditLogModel.resource_type == "permission",
                AuditLogModel.action == AuditAction.LOGIN,  # Permission denials use LOGIN action
                AuditLogModel.details["check_result"].astext == "false"
            )
        )
        
        if user_id:
            stmt = stmt.where(AuditLogModel.user_id == UUID(user_id))
        
        violations = db.execute(stmt).scalars().all()
        
        # Format violations
        formatted_violations = []
        for violation in violations:
            if violation.details:
                # Determine risk level based on permission
                permission_name = violation.details.get("permission_name", "")
                sensitive_permissions = [
                    "admin_access", "delete_user", "modify_permissions",
                    "export_sensitive_data", "system_config"
                ]
                risk_level = "high" if permission_name in sensitive_permissions else "medium"
                
                formatted_violations.append({
                    "violation_type": "permission_denied",
                    "user_id": str(violation.user_id) if violation.user_id else "unknown",
                    "tenant_id": violation.tenant_id,
                    "permission_name": permission_name,
                    "timestamp": violation.timestamp.isoformat(),
                    "details": {
                        "resource_id": violation.details.get("resource_id"),
                        "resource_type": violation.details.get("resource_type"),
                        "ip_address": str(violation.ip_address) if violation.ip_address else None,
                        "user_agent": violation.user_agent
                    },
                    "risk_level": risk_level
                })
        
        return {
            "tenant_id": tenant_id,
            "time_window_days": days,
            "total_violations": len(formatted_violations),
            "violations": formatted_violations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get permission violations: {str(e)}")


@router.get("/user-activity/{user_id}")
async def get_user_permission_activity(
    user_id: UUID,
    tenant_id: str,
    days: int = Query(30, description="Analysis period in days", ge=1, le=90),
    db: Session = Depends(get_db_session)
):
    """
    Get detailed permission activity for a specific user.
    
    Args:
        user_id: User identifier
        tenant_id: Tenant identifier
        days: Analysis period in days (1-90)
        
    Returns:
        User permission activity analysis
    """
    try:
        from src.security.models import AuditLogModel
        from sqlalchemy import and_, select, func
        from collections import Counter
        
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Get user's permission-related activities
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.user_id == user_id,
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_time,
                AuditLogModel.resource_type.in_(["permission", "user_role", "permission_batch"])
            )
        )
        
        activities = db.execute(stmt).scalars().all()
        
        # Analyze activities
        permission_checks = [
            activity for activity in activities 
            if activity.resource_type == "permission"
        ]
        
        role_changes = [
            activity for activity in activities 
            if activity.resource_type == "user_role"
        ]
        
        batch_operations = [
            activity for activity in activities 
            if activity.resource_type == "permission_batch"
        ]
        
        # Count permissions checked
        permissions_checked = Counter()
        successful_checks = 0
        denied_checks = 0
        
        for check in permission_checks:
            if check.details:
                perm_name = check.details.get("permission_name", "unknown")
                permissions_checked[perm_name] += 1
                
                if check.details.get("check_result") is True:
                    successful_checks += 1
                else:
                    denied_checks += 1
        
        # Calculate cache efficiency
        cache_hits = sum(
            1 for check in permission_checks 
            if check.details and check.details.get("cache_hit") is True
        )
        cache_hit_rate = (cache_hits / len(permission_checks) * 100) if permission_checks else 0
        
        # Get recent role changes
        recent_role_changes = []
        for role_change in role_changes[-10:]:  # Last 10 changes
            if role_change.details:
                recent_role_changes.append({
                    "timestamp": role_change.timestamp.isoformat(),
                    "action": role_change.action.value,
                    "role_name": role_change.details.get("role_name", "unknown"),
                    "changed_by": role_change.details.get("assigned_by") or role_change.details.get("revoked_by")
                })
        
        return {
            "user_id": str(user_id),
            "tenant_id": tenant_id,
            "analysis_period_days": days,
            "summary": {
                "total_activities": len(activities),
                "permission_checks": len(permission_checks),
                "successful_checks": successful_checks,
                "denied_checks": denied_checks,
                "success_rate": (successful_checks / len(permission_checks) * 100) if permission_checks else 0,
                "cache_hit_rate": round(cache_hit_rate, 2),
                "role_changes": len(role_changes),
                "batch_operations": len(batch_operations)
            },
            "most_checked_permissions": dict(permissions_checked.most_common(10)),
            "recent_role_changes": recent_role_changes,
            "activity_timeline": [
                {
                    "timestamp": activity.timestamp.isoformat(),
                    "type": activity.resource_type,
                    "action": activity.action.value,
                    "details": activity.details
                }
                for activity in activities[-20:]  # Last 20 activities
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user permission activity: {str(e)}")


@router.get("/performance-metrics/{tenant_id}")
async def get_permission_performance_metrics(
    tenant_id: str,
    hours: int = Query(24, description="Time window in hours", ge=1, le=168),
    db: Session = Depends(get_db_session)
):
    """
    Get permission system performance metrics.
    
    Args:
        tenant_id: Tenant identifier
        hours: Time window in hours (1-168)
        
    Returns:
        Permission system performance metrics
    """
    try:
        from src.security.models import AuditLogModel
        from sqlalchemy import and_, select, func
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get permission check events
        stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_time,
                AuditLogModel.resource_type == "permission"
            )
        )
        
        permission_events = db.execute(stmt).scalars().all()
        
        if not permission_events:
            return {
                "tenant_id": tenant_id,
                "time_window_hours": hours,
                "metrics": {
                    "total_checks": 0,
                    "average_response_time_ms": 0,
                    "cache_hit_rate": 0,
                    "success_rate": 0
                }
            }
        
        # Calculate metrics
        total_checks = len(permission_events)
        cache_hits = 0
        successful_checks = 0
        total_response_time = 0
        response_time_count = 0
        
        for event in permission_events:
            if event.details:
                if event.details.get("cache_hit") is True:
                    cache_hits += 1
                
                if event.details.get("check_result") is True:
                    successful_checks += 1
                
                response_time = event.details.get("response_time_ms")
                if response_time is not None:
                    total_response_time += response_time
                    response_time_count += 1
        
        # Calculate averages
        cache_hit_rate = (cache_hits / total_checks * 100) if total_checks > 0 else 0
        success_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 0
        avg_response_time = (total_response_time / response_time_count) if response_time_count > 0 else 0
        
        # Get batch operation metrics
        batch_stmt = select(AuditLogModel).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_time,
                AuditLogModel.resource_type == "permission_batch"
            )
        )
        
        batch_events = db.execute(batch_stmt).scalars().all()
        
        total_batch_permissions = 0
        batch_cache_hits = 0
        
        for batch_event in batch_events:
            if batch_event.details:
                total_batch_permissions += batch_event.details.get("total_permissions", 0)
                batch_cache_hits += batch_event.details.get("cache_hits", 0)
        
        batch_cache_hit_rate = (batch_cache_hits / total_batch_permissions * 100) if total_batch_permissions > 0 else 0
        
        return {
            "tenant_id": tenant_id,
            "time_window_hours": hours,
            "metrics": {
                "total_checks": total_checks,
                "average_response_time_ms": round(avg_response_time, 2),
                "cache_hit_rate": round(cache_hit_rate, 2),
                "success_rate": round(success_rate, 2),
                "batch_operations": {
                    "total_batch_events": len(batch_events),
                    "total_batch_permissions": total_batch_permissions,
                    "batch_cache_hit_rate": round(batch_cache_hit_rate, 2)
                }
            },
            "performance_status": "excellent" if avg_response_time < 10 and cache_hit_rate > 90 else
                                "good" if avg_response_time < 50 and cache_hit_rate > 70 else
                                "needs_improvement"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/health/{tenant_id}")
async def check_permission_system_health(
    tenant_id: str,
    db: Session = Depends(get_db_session)
):
    """
    Check the health of the permission system for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Permission system health status
    """
    try:
        # Get cache statistics
        cache_stats = rbac_controller.get_cache_statistics()
        
        # Get recent performance metrics
        performance_metrics = await get_permission_performance_metrics(tenant_id, 1, db)  # Last hour
        
        # Determine health status
        health_issues = []
        health_status = "healthy"
        
        # Check cache performance
        if cache_stats["hit_rate"] < 70:
            health_issues.append("Low cache hit rate")
            health_status = "degraded"
        
        # Check response time
        avg_response_time = performance_metrics["metrics"]["average_response_time_ms"]
        if avg_response_time > 100:
            health_issues.append("High response time")
            health_status = "degraded"
        
        # Check Redis connectivity
        if not cache_stats["redis_connected"]:
            health_issues.append("Redis cache unavailable")
            if health_status == "healthy":
                health_status = "degraded"
        
        # Check for recent security alerts
        alerts_response = await get_permission_security_alerts(tenant_id, 1, None, db)  # Last hour
        if alerts_response["total_alerts"] > 5:
            health_issues.append("High number of security alerts")
            health_status = "critical"
        
        return {
            "tenant_id": tenant_id,
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_performance": {
                "hit_rate": cache_stats["hit_rate"],
                "redis_connected": cache_stats["redis_connected"],
                "memory_usage": f"{cache_stats['memory_cache_size']}/{cache_stats['memory_cache_limit']}"
            },
            "permission_performance": {
                "average_response_time_ms": avg_response_time,
                "success_rate": performance_metrics["metrics"]["success_rate"]
            },
            "security_status": {
                "recent_alerts": alerts_response["total_alerts"],
                "alert_severity": "normal" if alerts_response["total_alerts"] < 3 else "elevated"
            },
            "issues": health_issues,
            "recommendations": [
                "Monitor cache hit rate and consider cache warming" if cache_stats["hit_rate"] < 80 else None,
                "Investigate high response times" if avg_response_time > 50 else None,
                "Check Redis connection" if not cache_stats["redis_connected"] else None,
                "Review security alerts" if alerts_response["total_alerts"] > 3 else None
            ]
        }
        
    except Exception as e:
        return {
            "tenant_id": tenant_id,
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }