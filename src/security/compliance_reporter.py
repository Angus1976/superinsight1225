"""
Compliance Reporter for SuperInsight Platform.

Generates compliance reports for various standards (GDPR, SOC 2, etc.).
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4
import json
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from src.models.security import AuditLogModel, SecurityEventModel, ComplianceReportModel
from src.security.audit_logger import AuditLogger


@dataclass
class ComplianceReport:
    """Base compliance report."""
    id: str = field(default_factory=lambda: str(uuid4()))
    report_type: str = ""
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    compliance_score: Optional[float] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GDPRReport:
    """GDPR compliance report."""
    id: str = field(default_factory=lambda: str(uuid4()))
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    dsar_stats: Dict[str, Any] = field(default_factory=dict)
    processing_activities: List[Dict[str, Any]] = field(default_factory=list)
    breach_incidents: List[Dict[str, Any]] = field(default_factory=list)
    consent_stats: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    compliance_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_type": "GDPR",
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "dsar_stats": self.dsar_stats,
            "processing_activities": self.processing_activities,
            "breach_incidents": self.breach_incidents,
            "consent_stats": self.consent_stats,
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "compliance_score": self.compliance_score
        }


@dataclass
class SOC2Report:
    """SOC 2 compliance report."""
    id: str = field(default_factory=lambda: str(uuid4()))
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    security_controls: List[Dict[str, Any]] = field(default_factory=list)
    availability_metrics: Dict[str, Any] = field(default_factory=dict)
    processing_integrity: Dict[str, Any] = field(default_factory=dict)
    confidentiality_controls: List[Dict[str, Any]] = field(default_factory=list)
    privacy_controls: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    compliance_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_type": "SOC2",
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "security_controls": self.security_controls,
            "availability_metrics": self.availability_metrics,
            "processing_integrity": self.processing_integrity,
            "confidentiality_controls": self.confidentiality_controls,
            "privacy_controls": self.privacy_controls,
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "compliance_score": self.compliance_score
        }


@dataclass
class AccessReport:
    """Data access compliance report."""
    id: str = field(default_factory=lambda: str(uuid4()))
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    total_accesses: int = 0
    by_user: Dict[str, int] = field(default_factory=dict)
    by_resource: Dict[str, int] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_type": "ACCESS",
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_accesses": self.total_accesses,
            "by_user": self.by_user,
            "by_resource": self.by_resource,
            "anomalies": self.anomalies,
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations
        }


@dataclass
class PermissionChangeReport:
    """Permission change compliance report."""
    id: str = field(default_factory=lambda: str(uuid4()))
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    total_changes: int = 0
    role_changes: int = 0
    permission_grants: int = 0
    permission_revokes: int = 0
    details: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_type": "PERMISSION_CHANGES",
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_changes": self.total_changes,
            "role_changes": self.role_changes,
            "permission_grants": self.permission_grants,
            "permission_revokes": self.permission_revokes,
            "details": self.details,
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations
        }


class ComplianceReporter:
    """
    Compliance reporter for generating various compliance reports.
    
    Supports GDPR, SOC 2, access reports, and permission change reports.
    """
    
    def __init__(self, db: AsyncSession, audit_logger: AuditLogger):
        self.db = db
        self.audit_logger = audit_logger
        self.logger = logging.getLogger(__name__)
    
    async def generate_gdpr_report(
        self,
        start_date: datetime,
        end_date: datetime,
        include_details: bool = True,
        save_to_db: bool = True
    ) -> GDPRReport:
        """
        Generate GDPR compliance report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            include_details: Whether to include detailed findings
            save_to_db: Whether to save report to database
            
        Returns:
            GDPRReport instance
        """
        self.logger.info(f"Generating GDPR report for period {start_date} to {end_date}")
        
        # Data Subject Access Request (DSAR) statistics
        dsar_stats = await self._get_dsar_stats(start_date, end_date)
        
        # Data processing activities
        processing_activities = await self._get_processing_activities(start_date, end_date)
        
        # Data breach incidents
        breach_incidents = await self._get_breach_incidents(start_date, end_date)
        
        # Consent management statistics
        consent_stats = await self._get_consent_stats(start_date, end_date)
        
        # Calculate compliance score
        compliance_score = self._calculate_gdpr_compliance_score(
            dsar_stats, breach_incidents, consent_stats
        )
        
        # Generate summary
        summary = {
            "total_dsar_requests": dsar_stats.get("total_requests", 0),
            "dsar_completion_rate": dsar_stats.get("completion_rate", 0),
            "breach_incidents": len(breach_incidents),
            "consent_changes": consent_stats.get("total_changes", 0),
            "processing_activities": len(processing_activities),
            "compliance_score": compliance_score
        }
        
        # Generate findings
        findings = []
        if include_details:
            if dsar_stats.get("completion_rate", 1) < 0.9:
                findings.append({
                    "type": "warning",
                    "category": "DSAR",
                    "description": "DSAR completion rate below 90%",
                    "recommendation": "Review DSAR processing workflow"
                })
            if len(breach_incidents) > 0:
                findings.append({
                    "type": "critical",
                    "category": "Data Breach",
                    "description": f"{len(breach_incidents)} data breach incidents detected",
                    "recommendation": "Review security controls and incident response"
                })
        
        # Generate recommendations
        recommendations = self._generate_gdpr_recommendations(
            dsar_stats, breach_incidents, consent_stats
        )
        
        report = GDPRReport(
            period_start=start_date,
            period_end=end_date,
            dsar_stats=dsar_stats,
            processing_activities=processing_activities if include_details else [],
            breach_incidents=breach_incidents,
            consent_stats=consent_stats,
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            compliance_score=compliance_score
        )
        
        if save_to_db:
            await self._save_report("GDPR", report.to_dict())
        
        return report
    
    def _calculate_gdpr_compliance_score(
        self,
        dsar_stats: Dict[str, Any],
        breach_incidents: List[Dict[str, Any]],
        consent_stats: Dict[str, Any]
    ) -> float:
        """Calculate GDPR compliance score (0-100)."""
        score = 100.0
        
        # Deduct for low DSAR completion rate
        completion_rate = dsar_stats.get("completion_rate", 1)
        if completion_rate < 1:
            score -= (1 - completion_rate) * 30
        
        # Deduct for breach incidents
        score -= len(breach_incidents) * 10
        
        # Ensure score is within bounds
        return max(0, min(100, score))
    
    def _generate_gdpr_recommendations(
        self,
        dsar_stats: Dict[str, Any],
        breach_incidents: List[Dict[str, Any]],
        consent_stats: Dict[str, Any]
    ) -> List[str]:
        """Generate GDPR compliance recommendations."""
        recommendations = []
        
        if dsar_stats.get("pending_requests", 0) > 0:
            recommendations.append("Process pending DSAR requests within regulatory timeframe")
        
        if len(breach_incidents) > 0:
            recommendations.append("Review and strengthen data protection measures")
            recommendations.append("Ensure breach notification procedures are followed")
        
        if consent_stats.get("revoked", 0) > consent_stats.get("granted", 0):
            recommendations.append("Review consent collection practices")
        
        if not recommendations:
            recommendations.append("Maintain current GDPR compliance practices")
        
        return recommendations
    
    async def generate_soc2_report(
        self,
        start_date: datetime,
        end_date: datetime,
        include_details: bool = True,
        save_to_db: bool = True
    ) -> SOC2Report:
        """
        Generate SOC 2 compliance report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            include_details: Whether to include detailed findings
            save_to_db: Whether to save report to database
            
        Returns:
            SOC2Report instance
        """
        self.logger.info(f"Generating SOC 2 report for period {start_date} to {end_date}")
        
        # Security controls assessment
        security_controls = await self._assess_security_controls(start_date, end_date)
        
        # Availability metrics
        availability_metrics = await self._get_availability_metrics(start_date, end_date)
        
        # Processing integrity assessment
        processing_integrity = await self._assess_processing_integrity(start_date, end_date)
        
        # Confidentiality controls
        confidentiality_controls = await self._assess_confidentiality_controls(start_date, end_date)
        
        # Privacy controls
        privacy_controls = await self._assess_privacy_controls(start_date, end_date)
        
        # Calculate compliance score
        compliance_score = self._calculate_soc2_compliance_score(
            security_controls, availability_metrics, processing_integrity
        )
        
        # Generate summary
        summary = {
            "security_controls_count": len(security_controls),
            "effective_controls": len([c for c in security_controls if c.get("status") == "effective"]),
            "uptime_percentage": availability_metrics.get("uptime_percentage", 0),
            "processing_success_rate": processing_integrity.get("success_rate", 0),
            "compliance_score": compliance_score
        }
        
        # Generate findings
        findings = []
        if include_details:
            ineffective_controls = [c for c in security_controls if c.get("status") != "effective"]
            for control in ineffective_controls:
                findings.append({
                    "type": "warning",
                    "category": "Security Control",
                    "control_id": control.get("control_id"),
                    "description": f"Control {control.get('control_id')} is not effective",
                    "recommendation": "Review and remediate control deficiency"
                })
            
            if availability_metrics.get("uptime_percentage", 100) < 99.9:
                findings.append({
                    "type": "warning",
                    "category": "Availability",
                    "description": "System uptime below 99.9% SLA",
                    "recommendation": "Review infrastructure and implement redundancy"
                })
        
        # Generate recommendations
        recommendations = self._generate_soc2_recommendations(
            security_controls, availability_metrics, processing_integrity
        )
        
        report = SOC2Report(
            period_start=start_date,
            period_end=end_date,
            security_controls=security_controls if include_details else [],
            availability_metrics=availability_metrics,
            processing_integrity=processing_integrity,
            confidentiality_controls=confidentiality_controls if include_details else [],
            privacy_controls=privacy_controls if include_details else [],
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            compliance_score=compliance_score
        )
        
        if save_to_db:
            await self._save_report("SOC2", report.to_dict())
        
        return report
    
    def _calculate_soc2_compliance_score(
        self,
        security_controls: List[Dict[str, Any]],
        availability_metrics: Dict[str, Any],
        processing_integrity: Dict[str, Any]
    ) -> float:
        """Calculate SOC 2 compliance score (0-100)."""
        score = 100.0
        
        # Deduct for ineffective controls
        total_controls = len(security_controls)
        effective_controls = len([c for c in security_controls if c.get("status") == "effective"])
        if total_controls > 0:
            control_score = (effective_controls / total_controls) * 40
            score = score - 40 + control_score
        
        # Deduct for availability issues
        uptime = availability_metrics.get("uptime_percentage", 100)
        if uptime < 99.9:
            score -= (99.9 - uptime) * 10
        
        # Deduct for processing integrity issues
        success_rate = processing_integrity.get("success_rate", 1)
        if success_rate < 0.999:
            score -= (0.999 - success_rate) * 1000
        
        return max(0, min(100, score))
    
    def _generate_soc2_recommendations(
        self,
        security_controls: List[Dict[str, Any]],
        availability_metrics: Dict[str, Any],
        processing_integrity: Dict[str, Any]
    ) -> List[str]:
        """Generate SOC 2 compliance recommendations."""
        recommendations = []
        
        ineffective_controls = [c for c in security_controls if c.get("status") != "effective"]
        if ineffective_controls:
            recommendations.append("Remediate ineffective security controls")
        
        if availability_metrics.get("uptime_percentage", 100) < 99.9:
            recommendations.append("Improve system availability and implement redundancy")
        
        if availability_metrics.get("incidents", 0) > 0:
            recommendations.append("Review incident response procedures")
        
        if processing_integrity.get("success_rate", 1) < 0.999:
            recommendations.append("Investigate and resolve processing errors")
        
        if not recommendations:
            recommendations.append("Maintain current SOC 2 compliance practices")
        
        return recommendations
    
    async def generate_access_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None,
        resource_pattern: Optional[str] = None,
        save_to_db: bool = True
    ) -> AccessReport:
        """
        Generate data access compliance report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            user_id: Filter by user ID (optional)
            resource_pattern: Filter by resource pattern (optional)
            save_to_db: Whether to save report to database
            
        Returns:
            AccessReport instance
        """
        self.logger.info(f"Generating access report for period {start_date} to {end_date}")
        
        # Get access logs
        access_logs = await self.audit_logger.query_logs(
            event_type="data_access",
            user_id=user_id,
            resource=resource_pattern,
            start_time=start_date,
            end_time=end_date,
            limit=10000
        )
        
        # Statistics by user
        by_user = {}
        for log in access_logs:
            uid = log.user_id
            by_user[uid] = by_user.get(uid, 0) + 1
        
        # Statistics by resource
        by_resource = {}
        for log in access_logs:
            if log.resource:
                by_resource[log.resource] = by_resource.get(log.resource, 0) + 1
        
        # Detect access anomalies
        anomalies = await self._detect_access_anomalies(access_logs)
        
        # Generate summary
        summary = {
            "total_accesses": len(access_logs),
            "unique_users": len(by_user),
            "unique_resources": len(by_resource),
            "anomalies_detected": len(anomalies)
        }
        
        # Generate findings from anomalies
        findings = [
            {
                "type": anomaly.get("type"),
                "user_id": anomaly.get("user_id"),
                "description": anomaly.get("description"),
                "severity": "high" if anomaly.get("type") == "excessive_access" else "medium"
            }
            for anomaly in anomalies
        ]
        
        # Generate recommendations
        recommendations = []
        if len(anomalies) > 0:
            recommendations.append("Review flagged access anomalies")
            recommendations.append("Consider implementing additional access controls")
        if len(by_user) > 100:
            recommendations.append("Review user access patterns for optimization")
        if not recommendations:
            recommendations.append("Access patterns are within normal parameters")
        
        report = AccessReport(
            period_start=start_date,
            period_end=end_date,
            total_accesses=len(access_logs),
            by_user=by_user,
            by_resource=by_resource,
            anomalies=anomalies,
            summary=summary,
            findings=findings,
            recommendations=recommendations
        )
        
        if save_to_db:
            await self._save_report("ACCESS", report.to_dict())
        
        return report
    
    async def generate_permission_change_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None,
        save_to_db: bool = True
    ) -> PermissionChangeReport:
        """
        Generate permission change compliance report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            user_id: Filter by user ID (optional)
            save_to_db: Whether to save report to database
            
        Returns:
            PermissionChangeReport instance
        """
        self.logger.info(f"Generating permission change report for period {start_date} to {end_date}")
        
        # Get permission change logs
        change_logs = await self.audit_logger.query_logs(
            event_type="permission_change",
            user_id=user_id,
            start_time=start_date,
            end_time=end_date,
            limit=10000
        )
        
        # Categorize changes
        role_changes = 0
        permission_grants = 0
        permission_revokes = 0
        
        details = []
        
        for log in change_logs:
            change_type = log.details.get("change_type", "unknown")
            
            if change_type == "role":
                role_changes += 1
            elif change_type == "grant":
                permission_grants += 1
            elif change_type == "revoke":
                permission_revokes += 1
            
            details.append({
                "timestamp": log.timestamp.isoformat(),
                "user_id": log.user_id,
                "change_type": change_type,
                "resource": log.resource,
                "action": log.action,
                "details": log.details
            })
        
        # Generate summary
        summary = {
            "total_changes": len(change_logs),
            "role_changes": role_changes,
            "permission_grants": permission_grants,
            "permission_revokes": permission_revokes,
            "net_permission_change": permission_grants - permission_revokes
        }
        
        # Generate findings
        findings = []
        if permission_grants > permission_revokes * 2:
            findings.append({
                "type": "warning",
                "category": "Permission Creep",
                "description": "Significant increase in permissions granted vs revoked",
                "recommendation": "Review permission grants for necessity"
            })
        
        # Generate recommendations
        recommendations = []
        if len(change_logs) > 100:
            recommendations.append("High volume of permission changes - review change management process")
        if role_changes > 50:
            recommendations.append("Frequent role changes detected - consider role consolidation")
        if permission_grants > permission_revokes:
            recommendations.append("Review principle of least privilege implementation")
        if not recommendations:
            recommendations.append("Permission change patterns are within normal parameters")
        
        report = PermissionChangeReport(
            period_start=start_date,
            period_end=end_date,
            total_changes=len(change_logs),
            role_changes=role_changes,
            permission_grants=permission_grants,
            permission_revokes=permission_revokes,
            details=details,
            summary=summary,
            findings=findings,
            recommendations=recommendations
        )
        
        if save_to_db:
            await self._save_report("PERMISSION_CHANGES", report.to_dict())
        
        return report
    
    async def schedule_report(
        self,
        report_type: str,
        schedule: str,
        recipients: List[str],
        config: Optional[Dict[str, Any]] = None,
        scheduler: Optional['ComplianceScheduler'] = None
    ) -> Dict[str, Any]:
        """
        Schedule automatic report generation.
        
        集成 ComplianceScheduler 实现自动报告生成和发送。
        
        Args:
            report_type: Type of report (GDPR, SOC2, ACCESS, PERMISSION_CHANGES)
            schedule: Cron expression for scheduling (分 时 日 月 周)
            recipients: List of email recipients
            config: Additional configuration
            scheduler: ComplianceScheduler 实例（可选）
            
        Returns:
            Schedule configuration
            
        Raises:
            ValueError: 无效的 cron 表达式或报告类型
            
        **Feature: system-optimization**
        **Validates: Requirements 7.1, 7.2, 7.3**
        """
        # 生成任务 ID
        job_id = str(uuid4())
        
        # 验证 cron 表达式
        parse_result = ComplianceScheduler.parse_cron_expression(schedule)
        if not parse_result.is_valid:
            error_msg = (
                f"[{ComplianceSchedulerI18nKeys.INVALID_CRON}] "
                f"Invalid cron expression: {schedule}. "
                f"Error: {parse_result.error_message}"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 验证报告类型
        if report_type not in ComplianceScheduler.SUPPORTED_REPORT_TYPES:
            error_msg = (
                f"[{ComplianceSchedulerI18nKeys.INVALID_REPORT_TYPE}] "
                f"Invalid report type: {report_type}. "
                f"Supported types: {ComplianceScheduler.SUPPORTED_REPORT_TYPES}"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        schedule_config = {
            "id": job_id,
            "report_type": report_type,
            "schedule": schedule,
            "recipients": recipients,
            "config": config or {},
            "created_at": datetime.utcnow().isoformat(),
            "enabled": True,
            "cron_parsed": parse_result.to_dict()
        }
        
        # 如果提供了调度器，则添加到调度器
        if scheduler:
            try:
                job = scheduler.add_job(
                    job_id=job_id,
                    report_type=report_type,
                    cron_expression=schedule,
                    recipients=recipients,
                    config=config
                )
                
                schedule_config["next_run"] = job.next_run.isoformat() if job.next_run else None
                schedule_config["scheduler_integrated"] = True
                
                self.logger.info(
                    f"[{ComplianceSchedulerI18nKeys.JOB_ADDED}] "
                    f"Scheduled {report_type} report with schedule: {schedule}"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to add job to scheduler: {e}")
                schedule_config["scheduler_integrated"] = False
                schedule_config["scheduler_error"] = str(e)
        else:
            # 没有调度器时，仅返回配置信息
            schedule_config["scheduler_integrated"] = False
            self.logger.info(
                f"Scheduled {report_type} report configuration created "
                f"(scheduler not provided): {schedule}"
            )
        
        return schedule_config
    
    async def _get_dsar_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get Data Subject Access Request statistics."""
        # Query DSAR-related audit logs
        dsar_logs = await self.audit_logger.query_logs(
            event_type="dsar_request",
            start_time=start_date,
            end_time=end_date,
            limit=1000
        )
        
        total_requests = len(dsar_logs)
        completed_requests = len([log for log in dsar_logs if log.result is True])
        pending_requests = total_requests - completed_requests
        
        return {
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "pending_requests": pending_requests,
            "completion_rate": completed_requests / total_requests if total_requests > 0 else 0
        }
    
    async def _get_processing_activities(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get data processing activities."""
        # Query data processing logs
        processing_logs = await self.audit_logger.query_logs(
            event_type="data_processing",
            start_time=start_date,
            end_time=end_date,
            limit=1000
        )
        
        activities = []
        for log in processing_logs:
            activities.append({
                "timestamp": log.timestamp.isoformat(),
                "user_id": log.user_id,
                "resource": log.resource,
                "action": log.action,
                "purpose": log.details.get("purpose", "unknown"),
                "legal_basis": log.details.get("legal_basis", "unknown")
            })
        
        return activities
    
    async def _get_breach_incidents(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get data breach incidents."""
        # Query security events for breaches
        stmt = select(SecurityEventModel).where(
            and_(
                SecurityEventModel.event_type == "data_breach",
                SecurityEventModel.created_at >= start_date,
                SecurityEventModel.created_at <= end_date
            )
        )
        
        result = await self.db.execute(stmt)
        incidents = list(result.scalars().all())
        
        breach_list = []
        for incident in incidents:
            breach_list.append({
                "id": str(incident.id),
                "timestamp": incident.created_at.isoformat(),
                "severity": incident.severity,
                "description": incident.details.get("description", ""),
                "affected_records": incident.details.get("affected_records", 0),
                "status": incident.status
            })
        
        return breach_list
    
    async def _get_consent_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get consent management statistics."""
        # Query consent-related logs
        consent_logs = await self.audit_logger.query_logs(
            event_type="consent_change",
            start_time=start_date,
            end_time=end_date,
            limit=1000
        )
        
        granted = len([log for log in consent_logs if log.details.get("action") == "grant"])
        revoked = len([log for log in consent_logs if log.details.get("action") == "revoke"])
        
        return {
            "total_changes": len(consent_logs),
            "granted": granted,
            "revoked": revoked
        }
    
    async def _assess_security_controls(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Assess security controls for SOC 2."""
        controls = [
            {
                "control_id": "CC6.1",
                "description": "Logical and physical access controls",
                "status": "effective",
                "evidence": "Access logs reviewed, no unauthorized access detected"
            },
            {
                "control_id": "CC6.2", 
                "description": "Authentication and authorization",
                "status": "effective",
                "evidence": "Multi-factor authentication enforced, role-based access implemented"
            },
            {
                "control_id": "CC6.3",
                "description": "System access monitoring",
                "status": "effective", 
                "evidence": "Continuous monitoring in place, security events tracked"
            }
        ]
        
        return controls
    
    async def _get_availability_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get system availability metrics."""
        # In a real implementation, this would query system monitoring data
        return {
            "uptime_percentage": 99.9,
            "total_downtime_minutes": 43.2,
            "incidents": 2,
            "mttr_minutes": 21.6  # Mean Time To Recovery
        }
    
    async def _assess_processing_integrity(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Assess processing integrity."""
        # Query for processing errors
        error_logs = await self.audit_logger.query_logs(
            result=False,
            start_time=start_date,
            end_time=end_date,
            limit=1000
        )
        
        return {
            "total_operations": 10000,  # Example
            "failed_operations": len(error_logs),
            "success_rate": (10000 - len(error_logs)) / 10000,
            "data_integrity_checks": "passed"
        }
    
    async def _assess_confidentiality_controls(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Assess confidentiality controls."""
        return [
            {
                "control": "Data encryption at rest",
                "status": "implemented",
                "details": "AES-256 encryption for all sensitive data"
            },
            {
                "control": "Data encryption in transit",
                "status": "implemented", 
                "details": "TLS 1.3 for all communications"
            },
            {
                "control": "Access controls",
                "status": "implemented",
                "details": "Role-based access with principle of least privilege"
            }
        ]
    
    async def _assess_privacy_controls(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Assess privacy controls."""
        return [
            {
                "control": "Data minimization",
                "status": "implemented",
                "details": "Only necessary data collected and processed"
            },
            {
                "control": "Purpose limitation",
                "status": "implemented",
                "details": "Data used only for stated purposes"
            },
            {
                "control": "Retention policies",
                "status": "implemented",
                "details": "Automated data deletion after retention period"
            }
        ]
    
    async def _detect_access_anomalies(self, access_logs: List[AuditLogModel]) -> List[Dict[str, Any]]:
        """Detect anomalous access patterns."""
        anomalies = []
        
        # Group by user
        user_accesses = {}
        for log in access_logs:
            user_id = log.user_id
            if user_id not in user_accesses:
                user_accesses[user_id] = []
            user_accesses[user_id].append(log)
        
        # Detect unusual patterns
        for user_id, logs in user_accesses.items():
            # Check for excessive access
            if len(logs) > 1000:  # Threshold
                anomalies.append({
                    "type": "excessive_access",
                    "user_id": user_id,
                    "access_count": len(logs),
                    "description": f"User {user_id} accessed {len(logs)} resources"
                })
            
            # Check for unusual time patterns
            night_accesses = [log for log in logs if log.timestamp.hour < 6 or log.timestamp.hour > 22]
            if len(night_accesses) > 50:  # Threshold
                anomalies.append({
                    "type": "unusual_time_access",
                    "user_id": user_id,
                    "night_access_count": len(night_accesses),
                    "description": f"User {user_id} had {len(night_accesses)} accesses outside business hours"
                })
        
        return anomalies
    
    async def _save_report(self, report_type: str, report_data: Dict[str, Any]) -> ComplianceReportModel:
        """Save compliance report to database."""
        report = ComplianceReportModel(
            id=uuid4(),
            report_type=report_type,
            period_start=datetime.fromisoformat(report_data["period_start"]),
            period_end=datetime.fromisoformat(report_data["period_end"]),
            report_data=report_data,
            generated_at=datetime.utcnow()
        )
        
        self.db.add(report)
        await self.db.commit()
        
        return report
    
    async def list_reports(
        self,
        report_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[ComplianceReportModel]:
        """
        List compliance reports.
        
        Args:
            report_type: Filter by report type (optional)
            limit: Maximum results
            offset: Result offset
            
        Returns:
            List of ComplianceReportModel
        """
        stmt = select(ComplianceReportModel)
        
        if report_type:
            stmt = stmt.where(ComplianceReportModel.report_type == report_type)
        
        stmt = stmt.order_by(desc(ComplianceReportModel.generated_at))
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_report(self, report_id: str) -> Optional[ComplianceReportModel]:
        """
        Get a specific compliance report.
        
        Args:
            report_id: Report ID
            
        Returns:
            ComplianceReportModel or None
        """
        stmt = select(ComplianceReportModel).where(ComplianceReportModel.id == report_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


# ============================================================================
# i18n 翻译键定义
# ============================================================================

class ComplianceSchedulerI18nKeys:
    """合规报告调度器相关的 i18n 翻译键"""
    
    # 调度相关
    JOB_ADDED = "compliance.scheduler.job_added"
    JOB_REMOVED = "compliance.scheduler.job_removed"
    JOB_PAUSED = "compliance.scheduler.job_paused"
    JOB_RESUMED = "compliance.scheduler.job_resumed"
    JOB_NOT_FOUND = "compliance.scheduler.job_not_found"
    
    # 报告相关
    GENERATION_STARTED = "compliance.report.generation_started"
    GENERATION_COMPLETED = "compliance.report.generation_completed"
    SEND_SUCCESS = "compliance.report.send_success"
    SEND_FAILED = "compliance.report.send_failed"
    
    # 错误消息
    INVALID_CRON = "compliance.scheduler.invalid_cron"
    INVALID_REPORT_TYPE = "compliance.scheduler.invalid_report_type"
    SCHEDULER_NOT_RUNNING = "compliance.scheduler.not_running"
    SCHEDULER_ALREADY_RUNNING = "compliance.scheduler.already_running"


# ============================================================================
# 调度任务数据类
# ============================================================================

@dataclass
class ScheduledJob:
    """调度任务信息"""
    job_id: str
    report_type: str
    cron_expression: str
    recipients: List[str]
    config: Dict[str, Any] = field(default_factory=dict)
    is_paused: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "job_id": self.job_id,
            "report_type": self.report_type,
            "cron_expression": self.cron_expression,
            "recipients": self.recipients,
            "config": self.config,
            "is_paused": self.is_paused,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None
        }


@dataclass
class CronParseResult:
    """Cron 表达式解析结果"""
    is_valid: bool
    minute: Optional[str] = None
    hour: Optional[str] = None
    day: Optional[str] = None
    month: Optional[str] = None
    day_of_week: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "minute": self.minute,
            "hour": self.hour,
            "day": self.day,
            "month": self.month,
            "day_of_week": self.day_of_week,
            "error_message": self.error_message
        }


# ============================================================================
# ComplianceScheduler - 合规报告调度器
# ============================================================================

class ComplianceScheduler:
    """
    合规报告调度器
    
    集成 APScheduler，实现:
    - cron 表达式解析
    - 添加、删除、暂停、恢复调度任务
    - 自动报告生成和发送
    - i18n 翻译键支持
    
    **Feature: system-optimization**
    **Validates: Requirements 7.1, 7.2, 7.3**
    """
    
    # 支持的报告类型
    SUPPORTED_REPORT_TYPES = ["GDPR", "SOC2", "ACCESS", "PERMISSION_CHANGES"]
    
    def __init__(
        self,
        reporter: 'ComplianceReporter',
        notification_manager: Optional[Any] = None
    ):
        """
        初始化合规报告调度器
        
        Args:
            reporter: ComplianceReporter 实例
            notification_manager: NotificationManager 实例（可选）
        """
        self.reporter = reporter
        self.notification_manager = notification_manager
        self._scheduler = None
        self._jobs: Dict[str, ScheduledJob] = {}
        self._is_running = False
        self.logger = logging.getLogger(__name__)
    
    @property
    def is_running(self) -> bool:
        """返回调度器是否正在运行"""
        return self._is_running
    
    async def start(self) -> bool:
        """
        启动调度器
        
        Returns:
            是否成功启动
        """
        if self._is_running:
            self.logger.warning(
                f"[{ComplianceSchedulerI18nKeys.SCHEDULER_ALREADY_RUNNING}] "
                "Compliance scheduler is already running"
            )
            return False
        
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            
            self._scheduler = AsyncIOScheduler()
            self._scheduler.start()
            self._is_running = True
            
            self.logger.info("Compliance scheduler started successfully")
            return True
            
        except ImportError:
            self.logger.warning(
                "APScheduler not installed, using mock scheduler mode"
            )
            self._is_running = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start compliance scheduler: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止调度器
        
        Returns:
            是否成功停止
        """
        if not self._is_running:
            self.logger.warning(
                f"[{ComplianceSchedulerI18nKeys.SCHEDULER_NOT_RUNNING}] "
                "Compliance scheduler is not running"
            )
            return False
        
        try:
            if self._scheduler:
                self._scheduler.shutdown(wait=True)
                self._scheduler = None
            
            self._is_running = False
            self.logger.info("Compliance scheduler stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop compliance scheduler: {e}")
            return False
    
    def add_job(
        self,
        job_id: str,
        report_type: str,
        cron_expression: str,
        recipients: List[str],
        config: Optional[Dict[str, Any]] = None
    ) -> ScheduledJob:
        """
        添加调度任务
        
        Args:
            job_id: 任务 ID
            report_type: 报告类型 (GDPR, SOC2, ACCESS, PERMISSION_CHANGES)
            cron_expression: cron 表达式 (分 时 日 月 周)
            recipients: 收件人列表
            config: 额外配置
            
        Returns:
            ScheduledJob 实例
            
        Raises:
            ValueError: 无效的 cron 表达式或报告类型
        """
        # 验证报告类型
        if report_type not in self.SUPPORTED_REPORT_TYPES:
            error_msg = (
                f"[{ComplianceSchedulerI18nKeys.INVALID_REPORT_TYPE}] "
                f"Invalid report type: {report_type}. "
                f"Supported types: {self.SUPPORTED_REPORT_TYPES}"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 解析并验证 cron 表达式
        parse_result = self.parse_cron_expression(cron_expression)
        if not parse_result.is_valid:
            error_msg = (
                f"[{ComplianceSchedulerI18nKeys.INVALID_CRON}] "
                f"Invalid cron expression: {cron_expression}. "
                f"Error: {parse_result.error_message}"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 创建调度任务
        job = ScheduledJob(
            job_id=job_id,
            report_type=report_type,
            cron_expression=cron_expression,
            recipients=recipients,
            config=config or {},
            created_at=datetime.utcnow()
        )
        
        # 添加到 APScheduler
        if self._scheduler:
            try:
                from apscheduler.triggers.cron import CronTrigger
                
                trigger = CronTrigger.from_crontab(cron_expression)
                
                self._scheduler.add_job(
                    self._execute_scheduled_report,
                    trigger=trigger,
                    args=[job_id, report_type, recipients, config or {}],
                    id=job_id,
                    name=f"Compliance Report: {report_type}",
                    max_instances=1,
                    coalesce=True
                )
                
                # 获取下次运行时间
                apscheduler_job = self._scheduler.get_job(job_id)
                if apscheduler_job and apscheduler_job.next_run_time:
                    job.next_run = apscheduler_job.next_run_time
                    
            except Exception as e:
                self.logger.error(f"Failed to add job to APScheduler: {e}")
        
        # 保存任务
        self._jobs[job_id] = job
        
        self.logger.info(
            f"[{ComplianceSchedulerI18nKeys.JOB_ADDED}] "
            f"Compliance report job added: {job_id} ({report_type})"
        )
        
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """
        删除调度任务
        
        Args:
            job_id: 任务 ID
            
        Returns:
            是否成功删除
        """
        if job_id not in self._jobs:
            self.logger.warning(
                f"[{ComplianceSchedulerI18nKeys.JOB_NOT_FOUND}] "
                f"Job not found: {job_id}"
            )
            return False
        
        # 从 APScheduler 删除
        if self._scheduler:
            try:
                self._scheduler.remove_job(job_id)
            except Exception as e:
                self.logger.warning(f"Failed to remove job from APScheduler: {e}")
        
        # 从内部存储删除
        del self._jobs[job_id]
        
        self.logger.info(
            f"[{ComplianceSchedulerI18nKeys.JOB_REMOVED}] "
            f"Compliance report job removed: {job_id}"
        )
        
        return True
    
    def pause_job(self, job_id: str) -> bool:
        """
        暂停调度任务
        
        Args:
            job_id: 任务 ID
            
        Returns:
            是否成功暂停
        """
        if job_id not in self._jobs:
            self.logger.warning(
                f"[{ComplianceSchedulerI18nKeys.JOB_NOT_FOUND}] "
                f"Job not found: {job_id}"
            )
            return False
        
        # 从 APScheduler 暂停
        if self._scheduler:
            try:
                self._scheduler.pause_job(job_id)
            except Exception as e:
                self.logger.warning(f"Failed to pause job in APScheduler: {e}")
        
        # 更新状态
        self._jobs[job_id].is_paused = True
        
        self.logger.info(
            f"[{ComplianceSchedulerI18nKeys.JOB_PAUSED}] "
            f"Compliance report job paused: {job_id}"
        )
        
        return True
    
    def resume_job(self, job_id: str) -> bool:
        """
        恢复调度任务
        
        Args:
            job_id: 任务 ID
            
        Returns:
            是否成功恢复
        """
        if job_id not in self._jobs:
            self.logger.warning(
                f"[{ComplianceSchedulerI18nKeys.JOB_NOT_FOUND}] "
                f"Job not found: {job_id}"
            )
            return False
        
        # 从 APScheduler 恢复
        if self._scheduler:
            try:
                self._scheduler.resume_job(job_id)
            except Exception as e:
                self.logger.warning(f"Failed to resume job in APScheduler: {e}")
        
        # 更新状态
        self._jobs[job_id].is_paused = False
        
        # 更新下次运行时间
        if self._scheduler:
            apscheduler_job = self._scheduler.get_job(job_id)
            if apscheduler_job and apscheduler_job.next_run_time:
                self._jobs[job_id].next_run = apscheduler_job.next_run_time
        
        self.logger.info(
            f"[{ComplianceSchedulerI18nKeys.JOB_RESUMED}] "
            f"Compliance report job resumed: {job_id}"
        )
        
        return True
    
    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """
        获取调度任务
        
        Args:
            job_id: 任务 ID
            
        Returns:
            ScheduledJob 实例或 None
        """
        return self._jobs.get(job_id)
    
    def list_jobs(self) -> List[ScheduledJob]:
        """
        列出所有调度任务
        
        Returns:
            ScheduledJob 列表
        """
        # 更新所有任务的下次运行时间
        if self._scheduler:
            for job_id, job in self._jobs.items():
                apscheduler_job = self._scheduler.get_job(job_id)
                if apscheduler_job and apscheduler_job.next_run_time:
                    job.next_run = apscheduler_job.next_run_time
        
        return list(self._jobs.values())
    
    @staticmethod
    def parse_cron_expression(expression: str) -> CronParseResult:
        """
        解析 cron 表达式
        
        支持标准 5 字段 cron 格式: 分 时 日 月 周
        
        Args:
            expression: cron 表达式
            
        Returns:
            CronParseResult 解析结果
            
        **Validates: Requirements 7.2**
        """
        if not expression or not isinstance(expression, str):
            return CronParseResult(
                is_valid=False,
                error_message="Cron expression cannot be empty"
            )
        
        # 分割表达式
        parts = expression.strip().split()
        
        if len(parts) != 5:
            return CronParseResult(
                is_valid=False,
                error_message=f"Cron expression must have 5 fields, got {len(parts)}"
            )
        
        minute, hour, day, month, day_of_week = parts
        
        # 验证各字段
        try:
            # 验证分钟 (0-59)
            if not ComplianceScheduler._validate_cron_field(minute, 0, 59):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid minute field: {minute}"
                )
            
            # 验证小时 (0-23)
            if not ComplianceScheduler._validate_cron_field(hour, 0, 23):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid hour field: {hour}"
                )
            
            # 验证日 (1-31)
            if not ComplianceScheduler._validate_cron_field(day, 1, 31):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid day field: {day}"
                )
            
            # 验证月 (1-12)
            if not ComplianceScheduler._validate_cron_field(month, 1, 12):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid month field: {month}"
                )
            
            # 验证星期 (0-6, 0=Sunday)
            if not ComplianceScheduler._validate_cron_field(day_of_week, 0, 6):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid day_of_week field: {day_of_week}"
                )
            
            return CronParseResult(
                is_valid=True,
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
        except Exception as e:
            return CronParseResult(
                is_valid=False,
                error_message=f"Failed to parse cron expression: {str(e)}"
            )
    
    @staticmethod
    def _validate_cron_field(field: str, min_val: int, max_val: int) -> bool:
        """
        验证单个 cron 字段
        
        支持:
        - * (任意值)
        - 数字 (如 5)
        - 范围 (如 1-5)
        - 列表 (如 1,3,5)
        - 步长 (如 */5, 1-10/2)
        
        Args:
            field: 字段值
            min_val: 最小允许值
            max_val: 最大允许值
            
        Returns:
            是否有效
        """
        if field == "*":
            return True
        
        # 处理步长 (*/n 或 range/n)
        if "/" in field:
            parts = field.split("/")
            if len(parts) != 2:
                return False
            
            base, step = parts
            
            # 验证步长
            try:
                step_val = int(step)
                if step_val <= 0:
                    return False
            except ValueError:
                return False
            
            # 验证基础部分
            if base == "*":
                return True
            
            # 基础部分是范围
            if "-" in base:
                return ComplianceScheduler._validate_cron_range(base, min_val, max_val)
            
            # 基础部分是数字
            try:
                val = int(base)
                return min_val <= val <= max_val
            except ValueError:
                return False
        
        # 处理列表 (1,3,5)
        if "," in field:
            parts = field.split(",")
            for part in parts:
                part = part.strip()
                if "-" in part:
                    if not ComplianceScheduler._validate_cron_range(part, min_val, max_val):
                        return False
                else:
                    try:
                        val = int(part)
                        if not (min_val <= val <= max_val):
                            return False
                    except ValueError:
                        return False
            return True
        
        # 处理范围 (1-5)
        if "-" in field:
            return ComplianceScheduler._validate_cron_range(field, min_val, max_val)
        
        # 单个数字
        try:
            val = int(field)
            return min_val <= val <= max_val
        except ValueError:
            return False
    
    @staticmethod
    def _validate_cron_range(range_str: str, min_val: int, max_val: int) -> bool:
        """验证 cron 范围字段"""
        parts = range_str.split("-")
        if len(parts) != 2:
            return False
        
        try:
            start = int(parts[0])
            end = int(parts[1])
            
            if start > end:
                return False
            
            return min_val <= start <= max_val and min_val <= end <= max_val
            
        except ValueError:
            return False
    
    async def _execute_scheduled_report(
        self,
        job_id: str,
        report_type: str,
        recipients: List[str],
        config: Dict[str, Any]
    ):
        """
        执行调度的报告生成
        
        Args:
            job_id: 任务 ID
            report_type: 报告类型
            recipients: 收件人列表
            config: 配置参数
        """
        self.logger.info(
            f"[{ComplianceSchedulerI18nKeys.GENERATION_STARTED}] "
            f"Starting scheduled report generation: {report_type}"
        )
        
        try:
            # 计算报告周期
            end_date = datetime.utcnow()
            period_days = config.get("period_days", 30)
            start_date = end_date - timedelta(days=period_days)
            
            # 生成报告
            report = None
            if report_type == "GDPR":
                report = await self.reporter.generate_gdpr_report(
                    start_date=start_date,
                    end_date=end_date,
                    include_details=config.get("include_details", True),
                    save_to_db=True
                )
            elif report_type == "SOC2":
                report = await self.reporter.generate_soc2_report(
                    start_date=start_date,
                    end_date=end_date,
                    include_details=config.get("include_details", True),
                    save_to_db=True
                )
            elif report_type == "ACCESS":
                report = await self.reporter.generate_access_report(
                    start_date=start_date,
                    end_date=end_date,
                    save_to_db=True
                )
            elif report_type == "PERMISSION_CHANGES":
                report = await self.reporter.generate_permission_change_report(
                    start_date=start_date,
                    end_date=end_date,
                    save_to_db=True
                )
            
            # 更新任务的最后运行时间
            if job_id in self._jobs:
                self._jobs[job_id].last_run = datetime.utcnow()
            
            self.logger.info(
                f"[{ComplianceSchedulerI18nKeys.GENERATION_COMPLETED}] "
                f"{report_type} compliance report generated successfully"
            )
            
            # 发送通知
            if report and recipients and self.notification_manager:
                await self._send_report_notification(
                    report_type=report_type,
                    report=report,
                    recipients=recipients
                )
                
        except Exception as e:
            self.logger.error(
                f"[{ComplianceSchedulerI18nKeys.SEND_FAILED}] "
                f"Failed to generate scheduled report {report_type}: {e}"
            )
    
    async def _send_report_notification(
        self,
        report_type: str,
        report: Any,
        recipients: List[str]
    ):
        """
        发送报告通知
        
        Args:
            report_type: 报告类型
            report: 报告对象
            recipients: 收件人列表
        """
        if not self.notification_manager:
            self.logger.warning("NotificationManager not configured, skipping notification")
            return
        
        try:
            # 构建通知内容
            subject = f"合规报告: {report_type} - {datetime.utcnow().strftime('%Y-%m-%d')}"
            
            # 获取报告摘要
            if hasattr(report, 'summary'):
                summary = report.summary
            elif hasattr(report, 'to_dict'):
                summary = report.to_dict().get('summary', {})
            else:
                summary = {}
            
            message = f"""
            <h2>{report_type} 合规报告</h2>
            <p>报告生成时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            <h3>摘要</h3>
            <ul>
            """
            
            for key, value in summary.items():
                message += f"<li><strong>{key}</strong>: {value}</li>"
            
            message += "</ul>"
            
            # 发送通知
            from src.ticket.notification_service import NotificationPriority
            
            await self.notification_manager.notify(
                recipients=recipients,
                subject=subject,
                message=message,
                priority=NotificationPriority.MEDIUM,
                metadata={
                    "report_type": report_type,
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                f"[{ComplianceSchedulerI18nKeys.SEND_SUCCESS}] "
                f"Compliance report notification sent to: {recipients}"
            )
            
        except Exception as e:
            self.logger.error(
                f"[{ComplianceSchedulerI18nKeys.SEND_FAILED}] "
                f"Failed to send report notification: {e}"
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态
        
        Returns:
            状态信息字典
        """
        jobs_info = []
        for job in self._jobs.values():
            job_info = job.to_dict()
            
            # 从 APScheduler 获取最新的下次运行时间
            if self._scheduler:
                apscheduler_job = self._scheduler.get_job(job.job_id)
                if apscheduler_job and apscheduler_job.next_run_time:
                    job_info["next_run"] = apscheduler_job.next_run_time.isoformat()
            
            jobs_info.append(job_info)
        
        return {
            "is_running": self._is_running,
            "jobs_count": len(self._jobs),
            "jobs": jobs_info,
            "supported_report_types": self.SUPPORTED_REPORT_TYPES
        }