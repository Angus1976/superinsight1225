"""
Compliance Report Generator for SuperInsight Platform.

Generates comprehensive compliance reports for various regulatory standards
including GDPR, SOX, ISO 27001, HIPAA, and CCPA.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, select, desc

from src.security.models import AuditLogModel, AuditAction, UserModel
from src.security.rbac_models import RoleModel, PermissionModel, UserRoleModel
from src.sync.desensitization.models import DatasetClassification, SensitivityLevel
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)


class ComplianceStandard(Enum):
    """支持的合规标准"""
    GDPR = "gdpr"  # General Data Protection Regulation
    SOX = "sox"    # Sarbanes-Oxley Act
    ISO_27001 = "iso_27001"  # Information Security Management
    HIPAA = "hipaa"  # Health Insurance Portability and Accountability Act
    CCPA = "ccpa"   # California Consumer Privacy Act
    PCI_DSS = "pci_dss"  # Payment Card Industry Data Security Standard


class ReportType(Enum):
    """报告类型"""
    AUDIT_SUMMARY = "audit_summary"
    DATA_PROTECTION = "data_protection"
    ACCESS_CONTROL = "access_control"
    SECURITY_MONITORING = "security_monitoring"
    COMPREHENSIVE = "comprehensive"


class ComplianceStatus(Enum):
    """合规状态"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNDER_REVIEW = "under_review"


@dataclass
class ComplianceMetric:
    """合规指标"""
    name: str
    description: str
    current_value: float
    target_value: float
    unit: str
    status: ComplianceStatus
    details: Dict[str, Any]


@dataclass
class ComplianceViolation:
    """合规违规"""
    violation_id: str
    standard: ComplianceStandard
    severity: str  # low, medium, high, critical
    description: str
    affected_resources: List[str]
    detection_time: datetime
    remediation_required: bool
    remediation_steps: List[str]


@dataclass
class ComplianceReport:
    """合规报告"""
    report_id: str
    tenant_id: str
    standard: ComplianceStandard
    report_type: ReportType
    generation_time: datetime
    reporting_period: Dict[str, datetime]
    overall_compliance_score: float
    compliance_status: ComplianceStatus
    
    # 报告内容
    executive_summary: str
    metrics: List[ComplianceMetric]
    violations: List[ComplianceViolation]
    recommendations: List[str]
    
    # 详细数据
    audit_statistics: Dict[str, Any]
    security_statistics: Dict[str, Any]
    data_protection_statistics: Dict[str, Any]
    access_control_statistics: Dict[str, Any]
    
    # 元数据
    generated_by: UUID
    report_format: str
    file_path: Optional[str] = None


class ComplianceReportGenerator:
    """
    企业级合规报告生成器
    
    支持多种合规标准的报告生成，包括：
    - GDPR数据保护报告
    - SOX财务合规报告
    - ISO 27001信息安全报告
    - HIPAA医疗数据保护报告
    - CCPA消费者隐私报告
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 合规标准配置
        self.compliance_standards = self._initialize_compliance_standards()
        
        # 报告模板
        self.report_templates = self._initialize_report_templates()
        
        # 合规阈值
        self.compliance_thresholds = self._initialize_compliance_thresholds()
    
    def generate_compliance_report(
        self,
        tenant_id: str,
        standard: ComplianceStandard,
        report_type: ReportType,
        start_date: datetime,
        end_date: datetime,
        generated_by: UUID,
        db: Session,
        include_recommendations: bool = True
    ) -> ComplianceReport:
        """
        生成合规报告
        
        Args:
            tenant_id: 租户ID
            standard: 合规标准
            report_type: 报告类型
            start_date: 报告开始日期
            end_date: 报告结束日期
            generated_by: 报告生成者
            db: 数据库会话
            include_recommendations: 是否包含建议
            
        Returns:
            ComplianceReport: 生成的合规报告
        """
        try:
            report_id = str(uuid4())
            
            # 收集审计数据
            audit_stats = self._collect_audit_statistics(
                tenant_id, start_date, end_date, db
            )
            
            # 收集安全数据
            security_stats = self._collect_security_statistics(
                tenant_id, start_date, end_date, db
            )
            
            # 收集数据保护数据
            data_protection_stats = self._collect_data_protection_statistics(
                tenant_id, start_date, end_date, db
            )
            
            # 收集访问控制数据
            access_control_stats = self._collect_access_control_statistics(
                tenant_id, start_date, end_date, db
            )
            
            # 生成合规指标
            metrics = self._generate_compliance_metrics(
                standard, audit_stats, security_stats, 
                data_protection_stats, access_control_stats
            )
            
            # 检测合规违规
            violations = self._detect_compliance_violations(
                standard, tenant_id, start_date, end_date, db
            )
            
            # 计算总体合规分数
            overall_score = self._calculate_overall_compliance_score(metrics, violations)
            
            # 确定合规状态
            compliance_status = self._determine_compliance_status(overall_score, violations)
            
            # 生成执行摘要
            executive_summary = self._generate_executive_summary(
                standard, overall_score, compliance_status, metrics, violations
            )
            
            # 生成建议
            recommendations = []
            if include_recommendations:
                recommendations = self._generate_recommendations(
                    standard, metrics, violations
                )
            
            # 创建报告
            report = ComplianceReport(
                report_id=report_id,
                tenant_id=tenant_id,
                standard=standard,
                report_type=report_type,
                generation_time=datetime.utcnow(),
                reporting_period={
                    "start_date": start_date,
                    "end_date": end_date
                },
                overall_compliance_score=overall_score,
                compliance_status=compliance_status,
                executive_summary=executive_summary,
                metrics=metrics,
                violations=violations,
                recommendations=recommendations,
                audit_statistics=audit_stats,
                security_statistics=security_stats,
                data_protection_statistics=data_protection_stats,
                access_control_statistics=access_control_stats,
                generated_by=generated_by,
                report_format="json"
            )
            
            self.logger.info(f"Generated compliance report {report_id} for tenant {tenant_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate compliance report: {e}")
            raise
    
    def _collect_audit_statistics(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """收集审计统计数据"""
        
        # 基础审计统计
        total_events_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date
            )
        )
        total_events = db.execute(total_events_stmt).scalar() or 0
        
        # 按操作类型统计
        action_stats = {}
        for action in AuditAction:
            action_stmt = select(func.count(AuditLogModel.id)).where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.action == action,
                    AuditLogModel.timestamp >= start_date,
                    AuditLogModel.timestamp <= end_date
                )
            )
            action_stats[action.value] = db.execute(action_stmt).scalar() or 0
        
        # 高风险事件统计
        high_risk_events_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date,
                AuditLogModel.details["risk_level"].astext.in_(["high", "critical"])
            )
        )
        high_risk_events = db.execute(high_risk_events_stmt).scalar() or 0
        
        # 失败登录统计
        failed_logins_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.action == AuditAction.LOGIN,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date,
                AuditLogModel.details["status"].astext == "failed"
            )
        )
        failed_logins = db.execute(failed_logins_stmt).scalar() or 0
        
        # 活跃用户统计
        active_users_stmt = select(func.count(func.distinct(AuditLogModel.user_id))).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date,
                AuditLogModel.user_id.isnot(None)
            )
        )
        active_users = db.execute(active_users_stmt).scalar() or 0
        
        return {
            "total_events": total_events,
            "action_statistics": action_stats,
            "high_risk_events": high_risk_events,
            "failed_logins": failed_logins,
            "active_users": active_users,
            "audit_coverage": self._calculate_audit_coverage(total_events, start_date, end_date)
        }
    
    def _collect_security_statistics(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """收集安全统计数据"""
        
        # 安全事件统计
        security_events_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date,
                AuditLogModel.details["risk_factors"].astext.isnot(None)
            )
        )
        security_events = db.execute(security_events_stmt).scalar() or 0
        
        # 威胁检测统计
        threat_detections = self._count_threat_detections(tenant_id, start_date, end_date, db)
        
        # IP地址统计
        unique_ips_stmt = select(func.count(func.distinct(AuditLogModel.ip_address))).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date,
                AuditLogModel.ip_address.isnot(None)
            )
        )
        unique_ips = db.execute(unique_ips_stmt).scalar() or 0
        
        return {
            "security_events": security_events,
            "threat_detections": threat_detections,
            "unique_ip_addresses": unique_ips,
            "security_incidents": self._count_security_incidents(tenant_id, start_date, end_date, db),
            "response_times": self._calculate_security_response_times(tenant_id, start_date, end_date, db)
        }
    
    def _collect_data_protection_statistics(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """收集数据保护统计数据"""
        
        # 数据导出统计
        export_events_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.action == AuditAction.EXPORT,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date
            )
        )
        export_events = db.execute(export_events_stmt).scalar() or 0
        
        # 数据删除统计
        delete_events_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.action == AuditAction.DELETE,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date
            )
        )
        delete_events = db.execute(delete_events_stmt).scalar() or 0
        
        # 脱敏操作统计
        desensitization_stats = self._collect_desensitization_statistics(
            tenant_id, start_date, end_date, db
        )
        
        return {
            "data_exports": export_events,
            "data_deletions": delete_events,
            "desensitization_operations": desensitization_stats,
            "data_retention_compliance": self._check_data_retention_compliance(tenant_id, db),
            "encryption_coverage": self._calculate_encryption_coverage(tenant_id, db)
        }
    
    def _collect_access_control_statistics(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """收集访问控制统计数据"""
        
        # 权限检查统计
        permission_checks = self._count_permission_checks(tenant_id, start_date, end_date, db)
        
        # 角色分配统计
        role_assignments = self._count_role_assignments(tenant_id, start_date, end_date, db)
        
        # 权限违规统计
        permission_violations = self._count_permission_violations(tenant_id, start_date, end_date, db)
        
        # 用户会话统计
        user_sessions = self._collect_user_session_statistics(tenant_id, start_date, end_date, db)
        
        return {
            "permission_checks": permission_checks,
            "role_assignments": role_assignments,
            "permission_violations": permission_violations,
            "user_sessions": user_sessions,
            "access_control_effectiveness": self._calculate_access_control_effectiveness(
                permission_checks, permission_violations
            )
        }
    
    def _generate_compliance_metrics(
        self,
        standard: ComplianceStandard,
        audit_stats: Dict[str, Any],
        security_stats: Dict[str, Any],
        data_protection_stats: Dict[str, Any],
        access_control_stats: Dict[str, Any]
    ) -> List[ComplianceMetric]:
        """生成合规指标"""
        
        metrics = []
        
        if standard == ComplianceStandard.GDPR:
            metrics.extend(self._generate_gdpr_metrics(
                audit_stats, security_stats, data_protection_stats, access_control_stats
            ))
        elif standard == ComplianceStandard.SOX:
            metrics.extend(self._generate_sox_metrics(
                audit_stats, security_stats, data_protection_stats, access_control_stats
            ))
        elif standard == ComplianceStandard.ISO_27001:
            metrics.extend(self._generate_iso27001_metrics(
                audit_stats, security_stats, data_protection_stats, access_control_stats
            ))
        elif standard == ComplianceStandard.HIPAA:
            metrics.extend(self._generate_hipaa_metrics(
                audit_stats, security_stats, data_protection_stats, access_control_stats
            ))
        elif standard == ComplianceStandard.CCPA:
            metrics.extend(self._generate_ccpa_metrics(
                audit_stats, security_stats, data_protection_stats, access_control_stats
            ))
        
        return metrics
    
    def _generate_gdpr_metrics(
        self,
        audit_stats: Dict[str, Any],
        security_stats: Dict[str, Any],
        data_protection_stats: Dict[str, Any],
        access_control_stats: Dict[str, Any]
    ) -> List[ComplianceMetric]:
        """生成GDPR合规指标"""
        
        metrics = []
        
        # 审计日志完整性
        audit_coverage = audit_stats.get("audit_coverage", 0)
        metrics.append(ComplianceMetric(
            name="audit_log_completeness",
            description="Audit log completeness for GDPR compliance",
            current_value=audit_coverage,
            target_value=95.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if audit_coverage >= 95 else ComplianceStatus.NON_COMPLIANT,
            details={"total_events": audit_stats.get("total_events", 0)}
        ))
        
        # 数据保护措施
        encryption_coverage = data_protection_stats.get("encryption_coverage", 0)
        metrics.append(ComplianceMetric(
            name="data_encryption_coverage",
            description="Percentage of sensitive data encrypted",
            current_value=encryption_coverage,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if encryption_coverage >= 100 else ComplianceStatus.PARTIALLY_COMPLIANT,
            details={"desensitization_ops": data_protection_stats.get("desensitization_operations", {})}
        ))
        
        # 访问控制有效性
        access_effectiveness = access_control_stats.get("access_control_effectiveness", 0)
        metrics.append(ComplianceMetric(
            name="access_control_effectiveness",
            description="Effectiveness of access control measures",
            current_value=access_effectiveness,
            target_value=98.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if access_effectiveness >= 98 else ComplianceStatus.NON_COMPLIANT,
            details=access_control_stats
        ))
        
        # 数据主体权利响应时间
        response_times = security_stats.get("response_times", {})
        avg_response_time = response_times.get("average_hours", 0)
        metrics.append(ComplianceMetric(
            name="data_subject_response_time",
            description="Average response time to data subject requests",
            current_value=avg_response_time,
            target_value=72.0,  # 72 hours for GDPR
            unit="hours",
            status=ComplianceStatus.COMPLIANT if avg_response_time <= 72 else ComplianceStatus.NON_COMPLIANT,
            details=response_times
        ))
        
        return metrics
    
    def _generate_sox_metrics(
        self,
        audit_stats: Dict[str, Any],
        security_stats: Dict[str, Any],
        data_protection_stats: Dict[str, Any],
        access_control_stats: Dict[str, Any]
    ) -> List[ComplianceMetric]:
        """生成SOX合规指标"""
        
        metrics = []
        
        # Section 302 & 906: Corporate Responsibility Metrics
        
        # 财务数据访问控制 (Section 302)
        financial_access_control = self._calculate_financial_access_control(access_control_stats)
        metrics.append(ComplianceMetric(
            name="financial_data_access_control",
            description="Access control for financial data (SOX Section 302)",
            current_value=financial_access_control,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if financial_access_control >= 100 else ComplianceStatus.NON_COMPLIANT,
            details={**access_control_stats, "sox_section": "302"}
        ))
        
        # 披露控制有效性 (Section 302)
        disclosure_control_effectiveness = self._calculate_disclosure_control_effectiveness(audit_stats)
        metrics.append(ComplianceMetric(
            name="disclosure_controls_effectiveness",
            description="Effectiveness of disclosure controls and procedures (SOX Section 302)",
            current_value=disclosure_control_effectiveness,
            target_value=95.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if disclosure_control_effectiveness >= 95 else ComplianceStatus.NON_COMPLIANT,
            details={**audit_stats, "sox_section": "302"}
        ))
        
        # Section 404: Internal Control Metrics
        
        # 内控设计有效性 (Section 404)
        internal_control_design = self._calculate_internal_control_design_effectiveness(access_control_stats)
        metrics.append(ComplianceMetric(
            name="internal_control_design_effectiveness",
            description="Design effectiveness of internal controls over financial reporting (SOX Section 404)",
            current_value=internal_control_design,
            target_value=95.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if internal_control_design >= 95 else ComplianceStatus.NON_COMPLIANT,
            details={**access_control_stats, "sox_section": "404"}
        ))
        
        # 内控运行有效性 (Section 404)
        internal_control_operating = self._calculate_internal_control_operating_effectiveness(audit_stats)
        metrics.append(ComplianceMetric(
            name="internal_control_operating_effectiveness",
            description="Operating effectiveness of internal controls over financial reporting (SOX Section 404)",
            current_value=internal_control_operating,
            target_value=95.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if internal_control_operating >= 95 else ComplianceStatus.NON_COMPLIANT,
            details={**audit_stats, "sox_section": "404"}
        ))
        
        # Section 409: Real-time Disclosure Metrics
        
        # 实时披露及时性 (Section 409)
        realtime_disclosure_timeliness = self._calculate_realtime_disclosure_timeliness(audit_stats)
        metrics.append(ComplianceMetric(
            name="realtime_disclosure_timeliness",
            description="Timeliness of real-time disclosure of material changes (SOX Section 409)",
            current_value=realtime_disclosure_timeliness,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if realtime_disclosure_timeliness >= 100 else ComplianceStatus.NON_COMPLIANT,
            details={**audit_stats, "sox_section": "409"}
        ))
        
        # Section 802: Document Integrity Metrics
        
        # 审计轨迹完整性 (Section 802)
        audit_integrity = self._calculate_audit_integrity(audit_stats)
        metrics.append(ComplianceMetric(
            name="audit_trail_integrity",
            description="Integrity of audit trails and document retention (SOX Section 802)",
            current_value=audit_integrity,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if audit_integrity >= 100 else ComplianceStatus.NON_COMPLIANT,
            details={**audit_stats, "sox_section": "802"}
        ))
        
        # 文档保留合规性 (Section 802)
        document_retention_compliance = self._calculate_document_retention_compliance(audit_stats)
        metrics.append(ComplianceMetric(
            name="document_retention_compliance",
            description="Compliance with document retention requirements (SOX Section 802)",
            current_value=document_retention_compliance,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if document_retention_compliance >= 100 else ComplianceStatus.NON_COMPLIANT,
            details={**audit_stats, "sox_section": "802"}
        ))
        
        # IT General Controls (Supporting Section 404)
        
        # IT一般控制有效性
        it_general_control_effectiveness = self._calculate_it_general_control_effectiveness(security_stats)
        metrics.append(ComplianceMetric(
            name="it_general_controls_effectiveness",
            description="Effectiveness of IT general controls supporting financial reporting (SOX Section 404)",
            current_value=it_general_control_effectiveness,
            target_value=95.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if it_general_control_effectiveness >= 95 else ComplianceStatus.NON_COMPLIANT,
            details={**security_stats, "sox_section": "404"}
        ))
        
        # 职责分离控制
        segregation_of_duties = self._calculate_segregation_of_duties_compliance(access_control_stats)
        metrics.append(ComplianceMetric(
            name="segregation_of_duties_compliance",
            description="Compliance with segregation of duties requirements (SOX Section 404)",
            current_value=segregation_of_duties,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if segregation_of_duties >= 100 else ComplianceStatus.NON_COMPLIANT,
            details={**access_control_stats, "sox_section": "404"}
        ))
        
        # 管理层监督控制
        management_oversight = self._calculate_management_oversight_effectiveness(audit_stats)
        metrics.append(ComplianceMetric(
            name="management_oversight_effectiveness",
            description="Effectiveness of management oversight controls (SOX Section 302/404)",
            current_value=management_oversight,
            target_value=95.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if management_oversight >= 95 else ComplianceStatus.NON_COMPLIANT,
            details={**audit_stats, "sox_section": "302/404"}
        ))
        
        return metrics
    
    def _generate_iso27001_metrics(
        self,
        audit_stats: Dict[str, Any],
        security_stats: Dict[str, Any],
        data_protection_stats: Dict[str, Any],
        access_control_stats: Dict[str, Any]
    ) -> List[ComplianceMetric]:
        """生成ISO 27001合规指标"""
        
        metrics = []
        
        # 导入ISO 27001合规检查器
        from src.compliance.iso27001_compliance import ISO27001ComplianceChecker, ISO27001ControlStatus
        
        try:
            # 创建ISO 27001合规检查器实例
            iso_checker = ISO27001ComplianceChecker()
            
            # 执行快速评估（不包含风险评估以提高性能）
            from src.database.connection import get_db_session
            with get_db_session() as db:
                assessment = iso_checker.assess_iso27001_compliance(
                    tenant_id="default",  # 使用默认租户进行评估
                    assessment_date=datetime.utcnow(),
                    db=db,
                    include_risk_assessment=False
                )
            
            # A.5 信息安全策略指标
            policy_score = assessment.domain_scores.get("A.5", 0)
            metrics.append(ComplianceMetric(
                name="information_security_policy_compliance",
                description="Compliance with information security policy requirements (ISO 27001 A.5)",
                current_value=policy_score,
                target_value=85.0,
                unit="percentage",
                status=ComplianceStatus.COMPLIANT if policy_score >= 85 else ComplianceStatus.PARTIALLY_COMPLIANT,
                details={"domain": "A.5", "controls_assessed": len([c for c in assessment.control_assessments if c.domain.value == "A.5"])}
            ))
            
            # A.9 访问控制指标
            access_control_score = assessment.domain_scores.get("A.9", 0)
            metrics.append(ComplianceMetric(
                name="access_control_effectiveness",
                description="Effectiveness of access control measures (ISO 27001 A.9)",
                current_value=access_control_score,
                target_value=90.0,
                unit="percentage",
                status=ComplianceStatus.COMPLIANT if access_control_score >= 90 else ComplianceStatus.PARTIALLY_COMPLIANT,
                details={"domain": "A.9", "controls_assessed": len([c for c in assessment.control_assessments if c.domain.value == "A.9"])}
            ))
            
            # A.12 运营安全指标
            operations_score = assessment.domain_scores.get("A.12", 0)
            metrics.append(ComplianceMetric(
                name="operations_security_compliance",
                description="Compliance with operations security requirements (ISO 27001 A.12)",
                current_value=operations_score,
                target_value=85.0,
                unit="percentage",
                status=ComplianceStatus.COMPLIANT if operations_score >= 85 else ComplianceStatus.PARTIALLY_COMPLIANT,
                details={"domain": "A.12", "controls_assessed": len([c for c in assessment.control_assessments if c.domain.value == "A.12"])}
            ))
            
            # A.16 事件管理指标
            incident_score = assessment.domain_scores.get("A.16", 0)
            metrics.append(ComplianceMetric(
                name="incident_management_effectiveness",
                description="Effectiveness of information security incident management (ISO 27001 A.16)",
                current_value=incident_score,
                target_value=80.0,
                unit="percentage",
                status=ComplianceStatus.COMPLIANT if incident_score >= 80 else ComplianceStatus.PARTIALLY_COMPLIANT,
                details={"domain": "A.16", "controls_assessed": len([c for c in assessment.control_assessments if c.domain.value == "A.16"])}
            ))
            
            # 总体成熟度指标
            metrics.append(ComplianceMetric(
                name="isms_maturity_level",
                description="Information Security Management System maturity level",
                current_value=float(assessment.overall_maturity_level),
                target_value=4.0,  # 目标成熟度等级4
                unit="level",
                status=ComplianceStatus.COMPLIANT if assessment.overall_maturity_level >= 4 else ComplianceStatus.PARTIALLY_COMPLIANT,
                details={"maturity_description": iso_checker.maturity_levels.get(assessment.overall_maturity_level, "Unknown")}
            ))
            
            # 控制项实施率指标
            implemented_controls = sum(1 for c in assessment.control_assessments if c.status == ISO27001ControlStatus.IMPLEMENTED)
            total_controls = len(assessment.control_assessments)
            implementation_rate = (implemented_controls / total_controls * 100) if total_controls > 0 else 0
            
            metrics.append(ComplianceMetric(
                name="control_implementation_rate",
                description="Percentage of ISO 27001 controls fully implemented",
                current_value=implementation_rate,
                target_value=90.0,
                unit="percentage",
                status=ComplianceStatus.COMPLIANT if implementation_rate >= 90 else ComplianceStatus.PARTIALLY_COMPLIANT,
                details={"implemented_controls": implemented_controls, "total_controls": total_controls}
            ))
            
            # 信息安全事件响应时间（从现有安全统计）
            incident_response_time = security_stats.get("response_times", {}).get("average_hours", 0)
            metrics.append(ComplianceMetric(
                name="security_incident_response_time",
                description="Average response time to security incidents",
                current_value=incident_response_time,
                target_value=24.0,  # 24 hours for ISO 27001
                unit="hours",
                status=ComplianceStatus.COMPLIANT if incident_response_time <= 24 else ComplianceStatus.NON_COMPLIANT,
                details=security_stats.get("response_times", {})
            ))
            
            # 审计日志完整性（从现有审计统计）
            audit_coverage = audit_stats.get("audit_coverage", 0)
            metrics.append(ComplianceMetric(
                name="audit_log_completeness",
                description="Completeness of audit logging for security monitoring",
                current_value=audit_coverage,
                target_value=95.0,
                unit="percentage",
                status=ComplianceStatus.COMPLIANT if audit_coverage >= 95 else ComplianceStatus.PARTIALLY_COMPLIANT,
                details={"total_events": audit_stats.get("total_events", 0)}
            ))
            
        except Exception as e:
            logger.error(f"Failed to generate ISO 27001 metrics: {e}")
            # 提供基本的后备指标
            metrics.extend([
                ComplianceMetric(
                    name="security_incident_response_time",
                    description="Average response time to security incidents",
                    current_value=security_stats.get("response_times", {}).get("average_hours", 0),
                    target_value=24.0,
                    unit="hours",
                    status=ComplianceStatus.PARTIALLY_COMPLIANT,
                    details=security_stats
                ),
                ComplianceMetric(
                    name="security_control_effectiveness",
                    description="Effectiveness of implemented security controls",
                    current_value=self._calculate_security_control_effectiveness(security_stats),
                    target_value=95.0,
                    unit="percentage",
                    status=ComplianceStatus.PARTIALLY_COMPLIANT,
                    details=security_stats
                )
            ])
        
        return metrics
    
    def _generate_hipaa_metrics(
        self,
        audit_stats: Dict[str, Any],
        security_stats: Dict[str, Any],
        data_protection_stats: Dict[str, Any],
        access_control_stats: Dict[str, Any]
    ) -> List[ComplianceMetric]:
        """生成HIPAA合规指标"""
        
        metrics = []
        
        # PHI访问控制
        phi_access_control = self._calculate_phi_access_control(access_control_stats)
        metrics.append(ComplianceMetric(
            name="phi_access_control",
            description="Access control for Protected Health Information",
            current_value=phi_access_control,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if phi_access_control >= 100 else ComplianceStatus.NON_COMPLIANT,
            details=access_control_stats
        ))
        
        # PHI加密覆盖率
        phi_encryption = data_protection_stats.get("encryption_coverage", 0)
        metrics.append(ComplianceMetric(
            name="phi_encryption_coverage",
            description="Encryption coverage for PHI data",
            current_value=phi_encryption,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if phi_encryption >= 100 else ComplianceStatus.NON_COMPLIANT,
            details=data_protection_stats
        ))
        
        return metrics
    
    def _generate_ccpa_metrics(
        self,
        audit_stats: Dict[str, Any],
        security_stats: Dict[str, Any],
        data_protection_stats: Dict[str, Any],
        access_control_stats: Dict[str, Any]
    ) -> List[ComplianceMetric]:
        """生成CCPA合规指标"""
        
        metrics = []
        
        # 消费者数据权利
        consumer_rights_compliance = self._calculate_consumer_rights_compliance(data_protection_stats)
        metrics.append(ComplianceMetric(
            name="consumer_rights_compliance",
            description="Compliance with consumer data rights",
            current_value=consumer_rights_compliance,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if consumer_rights_compliance >= 100 else ComplianceStatus.NON_COMPLIANT,
            details=data_protection_stats
        ))
        
        # 数据销售透明度
        data_sale_transparency = self._calculate_data_sale_transparency(audit_stats)
        metrics.append(ComplianceMetric(
            name="data_sale_transparency",
            description="Transparency in data sale disclosures",
            current_value=data_sale_transparency,
            target_value=100.0,
            unit="percentage",
            status=ComplianceStatus.COMPLIANT if data_sale_transparency >= 100 else ComplianceStatus.NON_COMPLIANT,
            details=audit_stats
        ))
        
        return metrics
    
    def _detect_compliance_violations(
        self,
        standard: ComplianceStandard,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> List[ComplianceViolation]:
        """检测合规违规"""
        
        violations = []
        
        # 通用违规检测
        violations.extend(self._detect_general_violations(tenant_id, start_date, end_date, db))
        
        # 标准特定违规检测
        if standard == ComplianceStandard.GDPR:
            violations.extend(self._detect_gdpr_violations(tenant_id, start_date, end_date, db))
        elif standard == ComplianceStandard.SOX:
            violations.extend(self._detect_sox_violations(tenant_id, start_date, end_date, db))
        elif standard == ComplianceStandard.ISO_27001:
            violations.extend(self._detect_iso27001_violations(tenant_id, start_date, end_date, db))
        elif standard == ComplianceStandard.HIPAA:
            violations.extend(self._detect_hipaa_violations(tenant_id, start_date, end_date, db))
        elif standard == ComplianceStandard.CCPA:
            violations.extend(self._detect_ccpa_violations(tenant_id, start_date, end_date, db))
        
        return violations
    
    def _calculate_overall_compliance_score(
        self,
        metrics: List[ComplianceMetric],
        violations: List[ComplianceViolation]
    ) -> float:
        """计算总体合规分数"""
        
        if not metrics:
            return 0.0
        
        # 基础分数：基于指标达标情况
        compliant_metrics = sum(1 for m in metrics if m.status == ComplianceStatus.COMPLIANT)
        partially_compliant = sum(1 for m in metrics if m.status == ComplianceStatus.PARTIALLY_COMPLIANT)
        
        base_score = (compliant_metrics + partially_compliant * 0.5) / len(metrics) * 100
        
        # 违规扣分
        violation_penalty = 0
        for violation in violations:
            if violation.severity == "critical":
                violation_penalty += 20
            elif violation.severity == "high":
                violation_penalty += 10
            elif violation.severity == "medium":
                violation_penalty += 5
            elif violation.severity == "low":
                violation_penalty += 2
        
        final_score = max(0, base_score - violation_penalty)
        return round(final_score, 2)
    
    def _determine_compliance_status(
        self,
        overall_score: float,
        violations: List[ComplianceViolation]
    ) -> ComplianceStatus:
        """确定合规状态"""
        
        # 检查是否有关键违规
        critical_violations = [v for v in violations if v.severity == "critical"]
        if critical_violations:
            return ComplianceStatus.NON_COMPLIANT
        
        # 基于分数确定状态
        if overall_score >= 95:
            return ComplianceStatus.COMPLIANT
        elif overall_score >= 70:
            return ComplianceStatus.PARTIALLY_COMPLIANT
        else:
            return ComplianceStatus.NON_COMPLIANT
    
    def _generate_executive_summary(
        self,
        standard: ComplianceStandard,
        overall_score: float,
        compliance_status: ComplianceStatus,
        metrics: List[ComplianceMetric],
        violations: List[ComplianceViolation]
    ) -> str:
        """生成执行摘要"""
        
        summary_parts = []
        
        # 总体状态
        summary_parts.append(f"Overall Compliance Status: {compliance_status.value.upper()}")
        summary_parts.append(f"Compliance Score: {overall_score}%")
        summary_parts.append(f"Standard: {standard.value.upper()}")
        
        # 指标摘要
        compliant_count = sum(1 for m in metrics if m.status == ComplianceStatus.COMPLIANT)
        summary_parts.append(f"Compliant Metrics: {compliant_count}/{len(metrics)}")
        
        # 违规摘要
        if violations:
            critical_count = sum(1 for v in violations if v.severity == "critical")
            high_count = sum(1 for v in violations if v.severity == "high")
            summary_parts.append(f"Critical Violations: {critical_count}")
            summary_parts.append(f"High Severity Violations: {high_count}")
        else:
            summary_parts.append("No compliance violations detected.")
        
        # 关键发现
        key_findings = self._generate_key_findings(metrics, violations)
        if key_findings:
            summary_parts.append("Key Findings:")
            summary_parts.extend([f"- {finding}" for finding in key_findings])
        
        return "\n".join(summary_parts)
    
    def _generate_recommendations(
        self,
        standard: ComplianceStandard,
        metrics: List[ComplianceMetric],
        violations: List[ComplianceViolation]
    ) -> List[str]:
        """生成改进建议"""
        
        recommendations = []
        
        # 基于违规的建议
        for violation in violations:
            recommendations.extend(violation.remediation_steps)
        
        # 基于指标的建议
        for metric in metrics:
            if metric.status != ComplianceStatus.COMPLIANT:
                recommendations.append(
                    f"Improve {metric.name}: Current {metric.current_value}{metric.unit}, "
                    f"Target {metric.target_value}{metric.unit}"
                )
        
        # 标准特定建议
        if standard == ComplianceStandard.GDPR:
            recommendations.extend(self._generate_gdpr_recommendations(metrics, violations))
        elif standard == ComplianceStandard.SOX:
            recommendations.extend(self._generate_sox_recommendations(metrics, violations))
        
        # 去重并排序
        return list(set(recommendations))
    
    # Helper methods for statistics collection
    
    def _calculate_audit_coverage(
        self,
        total_events: int,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """计算审计覆盖率"""
        # 简化计算：基于事件数量和时间范围
        days = (end_date - start_date).days
        expected_events = days * 100  # 假设每天100个事件
        
        if expected_events == 0:
            return 100.0
        
        coverage = min(100.0, (total_events / expected_events) * 100)
        return round(coverage, 2)
    
    def _count_threat_detections(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, int]:
        """统计威胁检测"""
        # 这里会集成实际的威胁检测系统
        return {
            "sql_injection_attempts": 0,
            "brute_force_attacks": 0,
            "data_exfiltration_attempts": 0,
            "privilege_escalation_attempts": 0
        }
    
    def _count_security_incidents(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> int:
        """统计安全事件"""
        # 基于高风险审计事件
        incidents_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date,
                AuditLogModel.details["risk_level"].astext == "critical"
            )
        )
        return db.execute(incidents_stmt).scalar() or 0
    
    def _calculate_security_response_times(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, float]:
        """计算安全响应时间"""
        # 简化实现
        return {
            "average_hours": 12.0,
            "median_hours": 8.0,
            "max_hours": 48.0
        }
    
    def _collect_desensitization_statistics(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """收集脱敏统计数据"""
        # 这里会集成实际的脱敏系统统计
        return {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "entities_processed": 0,
            "accuracy_rate": 95.0
        }
    
    def _check_data_retention_compliance(
        self,
        tenant_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """检查数据保留合规性"""
        return {
            "compliant": True,
            "retention_policy_applied": True,
            "overdue_deletions": 0
        }
    
    def _calculate_encryption_coverage(
        self,
        tenant_id: str,
        db: Session
    ) -> float:
        """计算加密覆盖率"""
        # 简化实现
        return 100.0
    
    # Additional helper methods would be implemented here...
    
    def _initialize_compliance_standards(self) -> Dict[ComplianceStandard, Dict[str, Any]]:
        """初始化合规标准配置"""
        return {
            ComplianceStandard.GDPR: {
                "name": "General Data Protection Regulation",
                "description": "EU data protection regulation",
                "key_requirements": ["data_protection", "audit_trails", "consent_management"]
            },
            ComplianceStandard.SOX: {
                "name": "Sarbanes-Oxley Act",
                "description": "US financial reporting regulation",
                "key_requirements": ["financial_controls", "audit_trails", "access_controls"]
            },
            ComplianceStandard.ISO_27001: {
                "name": "Information Security Management",
                "description": "International security standard",
                "key_requirements": ["security_controls", "risk_management", "incident_response"]
            }
        }
    
    def _initialize_report_templates(self) -> Dict[str, str]:
        """初始化报告模板"""
        return {
            "executive_summary": "Executive Summary Template",
            "detailed_analysis": "Detailed Analysis Template",
            "recommendations": "Recommendations Template"
        }
    
    def _initialize_compliance_thresholds(self) -> Dict[str, float]:
        """初始化合规阈值"""
        return {
            "audit_coverage_threshold": 95.0,
            "encryption_coverage_threshold": 100.0,
            "access_control_effectiveness_threshold": 98.0,
            "incident_response_time_threshold": 24.0
        }
    
    # Placeholder methods for specific compliance checks
    def _detect_general_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        return []
    
    def _detect_gdpr_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        return []
    
    def _detect_sox_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        """检测SOX合规违规"""
        violations = []
        
        # Section 302 违规检测
        violations.extend(self._detect_section_302_violations(tenant_id, start_date, end_date, db))
        
        # Section 404 违规检测
        violations.extend(self._detect_section_404_violations(tenant_id, start_date, end_date, db))
        
        # Section 409 违规检测
        violations.extend(self._detect_section_409_violations(tenant_id, start_date, end_date, db))
        
        # Section 802 违规检测
        violations.extend(self._detect_section_802_violations(tenant_id, start_date, end_date, db))
        
        # Section 906 违规检测
        violations.extend(self._detect_section_906_violations(tenant_id, start_date, end_date, db))
        
        return violations
    
    def _detect_section_302_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        """检测Section 302违规 - Corporate Responsibility for Financial Reports"""
        violations = []
        
        # 检测未经授权的财务数据访问
        unauthorized_financial_access = self._check_unauthorized_financial_access(tenant_id, start_date, end_date, db)
        if unauthorized_financial_access > 0:
            violations.append(ComplianceViolation(
                violation_id=str(uuid4()),
                standard=ComplianceStandard.SOX,
                severity="high",
                description=f"Detected {unauthorized_financial_access} unauthorized access attempts to financial data",
                affected_resources=["financial_data_systems"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=[
                    "Review and strengthen access controls for financial systems",
                    "Implement additional monitoring for financial data access",
                    "Conduct security awareness training for financial personnel",
                    "Review user access rights and remove unnecessary privileges"
                ]
            ))
        
        # 检测披露控制缺陷
        disclosure_control_deficiencies = self._check_disclosure_control_deficiencies(tenant_id, start_date, end_date, db)
        if disclosure_control_deficiencies:
            violations.append(ComplianceViolation(
                violation_id=str(uuid4()),
                standard=ComplianceStandard.SOX,
                severity="medium",
                description="Deficiencies identified in disclosure controls and procedures",
                affected_resources=["disclosure_systems", "reporting_processes"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=[
                    "Enhance disclosure control procedures",
                    "Implement additional review processes",
                    "Provide training on disclosure requirements",
                    "Establish clear escalation procedures"
                ]
            ))
        
        return violations
    
    def _detect_section_404_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        """检测Section 404违规 - Management Assessment of Internal Controls"""
        violations = []
        
        # 检测内控设计缺陷
        design_deficiencies = self._check_internal_control_design_deficiencies(tenant_id, start_date, end_date, db)
        if design_deficiencies:
            violations.append(ComplianceViolation(
                violation_id=str(uuid4()),
                standard=ComplianceStandard.SOX,
                severity="high",
                description="Material weaknesses identified in internal control design",
                affected_resources=["internal_control_framework"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=[
                    "Redesign deficient controls",
                    "Implement compensating controls",
                    "Enhance control documentation",
                    "Conduct control effectiveness testing"
                ]
            ))
        
        # 检测内控运行缺陷
        operating_deficiencies = self._check_internal_control_operating_deficiencies(tenant_id, start_date, end_date, db)
        if operating_deficiencies:
            violations.append(ComplianceViolation(
                violation_id=str(uuid4()),
                standard=ComplianceStandard.SOX,
                severity="high",
                description="Deficiencies identified in internal control operating effectiveness",
                affected_resources=["control_operations"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=[
                    "Retrain control operators",
                    "Enhance control monitoring",
                    "Implement automated controls where possible",
                    "Establish regular control testing procedures"
                ]
            ))
        
        return violations
    
    def _detect_section_409_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        """检测Section 409违规 - Real-time Disclosure"""
        violations = []
        
        # 检测披露延迟
        disclosure_delays = self._check_disclosure_delays(tenant_id, start_date, end_date, db)
        if disclosure_delays > 0:
            violations.append(ComplianceViolation(
                violation_id=str(uuid4()),
                standard=ComplianceStandard.SOX,
                severity="medium",
                description=f"Identified {disclosure_delays} instances of delayed material disclosures",
                affected_resources=["disclosure_systems"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=[
                    "Implement real-time monitoring for material events",
                    "Establish automated disclosure triggers",
                    "Enhance event identification procedures",
                    "Provide training on disclosure timing requirements"
                ]
            ))
        
        return violations
    
    def _detect_section_802_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        """检测Section 802违规 - Criminal Penalties for Altering Documents"""
        violations = []
        
        # 检测审计轨迹完整性问题
        audit_integrity_issues = self._check_audit_trail_integrity_issues(tenant_id, start_date, end_date, db)
        if audit_integrity_issues:
            violations.append(ComplianceViolation(
                violation_id=str(uuid4()),
                standard=ComplianceStandard.SOX,
                severity="critical",
                description="Audit trail integrity issues detected - potential document alteration",
                affected_resources=["audit_systems", "document_management"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=[
                    "Investigate potential document alterations",
                    "Strengthen audit trail protection mechanisms",
                    "Implement digital signatures for critical documents",
                    "Enhance access controls for audit systems",
                    "Conduct forensic analysis if necessary"
                ]
            ))
        
        # 检测文档保留违规
        document_retention_violations = self._check_document_retention_violations(tenant_id, start_date, end_date, db)
        if document_retention_violations > 0:
            violations.append(ComplianceViolation(
                violation_id=str(uuid4()),
                standard=ComplianceStandard.SOX,
                severity="high",
                description=f"Identified {document_retention_violations} document retention policy violations",
                affected_resources=["document_management_systems"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=[
                    "Review and update document retention policies",
                    "Implement automated retention management",
                    "Conduct document retention training",
                    "Establish regular compliance monitoring"
                ]
            ))
        
        return violations
    
    def _detect_section_906_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        """检测Section 906违规 - Corporate Responsibility for Financial Reports"""
        violations = []
        
        # 检测管理层认证缺失
        certification_issues = self._check_management_certification_issues(tenant_id, start_date, end_date, db)
        if certification_issues:
            violations.append(ComplianceViolation(
                violation_id=str(uuid4()),
                standard=ComplianceStandard.SOX,
                severity="critical",
                description="Management certification requirements not met",
                affected_resources=["management_certification_process"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=[
                    "Ensure CEO and CFO certifications are completed",
                    "Review certification process and requirements",
                    "Implement certification tracking system",
                    "Provide training on certification responsibilities"
                ]
            ))
        
        return violations
    
    def _detect_iso27001_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        """检测ISO 27001合规违规"""
        violations = []
        
        # 导入ISO 27001合规检查器
        from src.compliance.iso27001_compliance import ISO27001ComplianceChecker
        
        try:
            # 创建ISO 27001合规检查器实例
            iso_checker = ISO27001ComplianceChecker()
            
            # 执行ISO 27001评估
            assessment = iso_checker.assess_iso27001_compliance(
                tenant_id=tenant_id,
                assessment_date=end_date,
                db=db,
                include_risk_assessment=True
            )
            
            # 将ISO 27001风险转换为合规违规
            for risk in assessment.identified_risks:
                severity_mapping = {
                    "Very High": "critical",
                    "High": "high", 
                    "Medium": "medium",
                    "Low": "low",
                    "Very Low": "low"
                }
                
                severity = severity_mapping.get(risk.get("risk_level", "Medium"), "medium")
                
                violations.append(ComplianceViolation(
                    violation_id=risk.get("risk_id", str(uuid4())),
                    standard=ComplianceStandard.ISO_27001,
                    severity=severity,
                    description=risk.get("description", "ISO 27001 control implementation gap"),
                    affected_resources=risk.get("affected_assets", ["Information systems"]),
                    detection_time=datetime.utcnow(),
                    remediation_required=True,
                    remediation_steps=[
                        f"Implement control {risk.get('control_reference', 'N/A')}",
                        "Conduct risk assessment",
                        "Develop mitigation plan",
                        "Monitor implementation progress"
                    ]
                ))
            
            # 检测关键控制项缺失
            critical_controls = [c for c in assessment.control_assessments if c.effectiveness_score < 50]
            for control in critical_controls:
                violations.append(ComplianceViolation(
                    violation_id=str(uuid4()),
                    standard=ComplianceStandard.ISO_27001,
                    severity="high",
                    description=f"Critical control {control.control_id} not adequately implemented",
                    affected_resources=["Information security management system"],
                    detection_time=datetime.utcnow(),
                    remediation_required=True,
                    remediation_steps=control.recommendations
                ))
            
            # 检测成熟度不足
            if assessment.overall_maturity_level < 3:
                violations.append(ComplianceViolation(
                    violation_id=str(uuid4()),
                    standard=ComplianceStandard.ISO_27001,
                    severity="medium",
                    description=f"Information security maturity level {assessment.overall_maturity_level} below recommended level 3",
                    affected_resources=["Information security management system"],
                    detection_time=datetime.utcnow(),
                    remediation_required=True,
                    remediation_steps=[
                        "Develop formal ISMS processes",
                        "Implement documented procedures",
                        "Establish measurement and monitoring",
                        "Conduct regular management reviews"
                    ]
                ))
            
        except Exception as e:
            logger.error(f"Failed to detect ISO 27001 violations: {e}")
            # 添加一个通用违规以指示检查失败
            violations.append(ComplianceViolation(
                violation_id=str(uuid4()),
                standard=ComplianceStandard.ISO_27001,
                severity="medium",
                description="ISO 27001 compliance assessment could not be completed",
                affected_resources=["Compliance monitoring system"],
                detection_time=datetime.utcnow(),
                remediation_required=True,
                remediation_steps=[
                    "Review compliance monitoring system",
                    "Ensure proper data collection",
                    "Verify system integration"
                ]
            ))
        
        return violations
    
    def _detect_hipaa_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        return []
    
    def _detect_ccpa_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> List[ComplianceViolation]:
        return []
    
    def _calculate_financial_access_control(self, access_control_stats: Dict[str, Any]) -> float:
        """计算财务数据访问控制有效性"""
        # 基于访问控制统计计算财务数据访问控制得分
        permission_checks = access_control_stats.get("permission_checks", 0)
        permission_violations = access_control_stats.get("permission_violations", 0)
        
        if permission_checks == 0:
            return 100.0
        
        violation_rate = (permission_violations / permission_checks) * 100
        return max(0, 100 - violation_rate)
    
    def _calculate_audit_integrity(self, audit_stats: Dict[str, Any]) -> float:
        """计算审计轨迹完整性"""
        # 基于审计统计计算完整性得分
        total_events = audit_stats.get("total_events", 0)
        high_risk_events = audit_stats.get("high_risk_events", 0)
        
        if total_events == 0:
            return 100.0
        
        # 简化计算：基于高风险事件比例
        risk_ratio = (high_risk_events / total_events) * 100
        return max(0, 100 - risk_ratio)
    
    def _calculate_disclosure_control_effectiveness(self, audit_stats: Dict[str, Any]) -> float:
        """计算披露控制有效性"""
        # 基于审计事件分析披露控制有效性
        return 95.0  # 简化实现
    
    def _calculate_internal_control_design_effectiveness(self, access_control_stats: Dict[str, Any]) -> float:
        """计算内控设计有效性"""
        return 92.0  # 简化实现
    
    def _calculate_internal_control_operating_effectiveness(self, audit_stats: Dict[str, Any]) -> float:
        """计算内控运行有效性"""
        return 88.0  # 简化实现
    
    def _calculate_realtime_disclosure_timeliness(self, audit_stats: Dict[str, Any]) -> float:
        """计算实时披露及时性"""
        return 95.0  # 简化实现
    
    def _calculate_document_retention_compliance(self, audit_stats: Dict[str, Any]) -> float:
        """计算文档保留合规性"""
        return 100.0  # 简化实现
    
    def _calculate_it_general_control_effectiveness(self, security_stats: Dict[str, Any]) -> float:
        """计算IT一般控制有效性"""
        return 90.0  # 简化实现
    
    def _calculate_segregation_of_duties_compliance(self, access_control_stats: Dict[str, Any]) -> float:
        """计算职责分离合规性"""
        return 95.0  # 简化实现
    
    def _calculate_management_oversight_effectiveness(self, audit_stats: Dict[str, Any]) -> float:
        """计算管理层监督有效性"""
        return 88.0  # 简化实现
    
    # SOX违规检测辅助方法
    
    def _check_unauthorized_financial_access(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> int:
        """检查未经授权的财务数据访问"""
        # 查询失败的财务系统访问尝试
        failed_financial_access_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date,
                AuditLogModel.details["status"].astext == "failed",
                AuditLogModel.details["resource_type"].astext.in_(["financial_data", "accounting_system", "erp_system"])
            )
        )
        return db.execute(failed_financial_access_stmt).scalar() or 0
    
    def _check_disclosure_control_deficiencies(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> bool:
        """检查披露控制缺陷"""
        # 简化实现：检查是否有披露相关的高风险事件
        disclosure_issues_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date,
                AuditLogModel.details["risk_level"].astext == "high",
                AuditLogModel.details["category"].astext == "disclosure"
            )
        )
        issues_count = db.execute(disclosure_issues_stmt).scalar() or 0
        return issues_count > 0
    
    def _check_internal_control_design_deficiencies(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> bool:
        """检查内控设计缺陷"""
        # 简化实现
        return False
    
    def _check_internal_control_operating_deficiencies(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> bool:
        """检查内控运行缺陷"""
        # 简化实现
        return False
    
    def _check_disclosure_delays(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> int:
        """检查披露延迟"""
        # 简化实现
        return 0
    
    def _check_audit_trail_integrity_issues(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> bool:
        """检查审计轨迹完整性问题"""
        # 简化实现
        return False
    
    def _check_document_retention_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> int:
        """检查文档保留违规"""
        # 简化实现
        return 0
    
    def _check_management_certification_issues(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> bool:
        """检查管理层认证问题"""
        # 简化实现
        return False
    
    def _calculate_security_control_effectiveness(self, security_stats: Dict[str, Any]) -> float:
        return 95.0
    
    def _calculate_phi_access_control(self, access_control_stats: Dict[str, Any]) -> float:
        return 100.0
    
    def _calculate_consumer_rights_compliance(self, data_protection_stats: Dict[str, Any]) -> float:
        return 100.0
    
    def _calculate_data_sale_transparency(self, audit_stats: Dict[str, Any]) -> float:
        return 100.0
    
    def _count_permission_checks(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> int:
        return 0
    
    def _count_role_assignments(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> int:
        return 0
    
    def _count_permission_violations(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> int:
        return 0
    
    def _collect_user_session_statistics(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> Dict[str, Any]:
        return {}
    
    def _calculate_access_control_effectiveness(self, permission_checks: int, permission_violations: int) -> float:
        if permission_checks == 0:
            return 100.0
        return max(0, 100 - (permission_violations / permission_checks * 100))
    
    def _generate_key_findings(self, metrics: List[ComplianceMetric], violations: List[ComplianceViolation]) -> List[str]:
        findings = []
        
        # 基于指标的发现
        non_compliant_metrics = [m for m in metrics if m.status == ComplianceStatus.NON_COMPLIANT]
        if non_compliant_metrics:
            findings.append(f"{len(non_compliant_metrics)} metrics are non-compliant")
        
        # 基于违规的发现
        if violations:
            critical_violations = [v for v in violations if v.severity == "critical"]
            if critical_violations:
                findings.append(f"{len(critical_violations)} critical violations require immediate attention")
        
        return findings
    
    def _generate_gdpr_recommendations(self, metrics: List[ComplianceMetric], violations: List[ComplianceViolation]) -> List[str]:
        return [
            "Implement data subject request automation",
            "Enhance consent management system",
            "Improve data retention policies"
        ]
    
    def _generate_sox_recommendations(self, metrics: List[ComplianceMetric], violations: List[ComplianceViolation]) -> List[str]:
        """生成SOX合规改进建议"""
        recommendations = []
        
        # Section 302 建议
        recommendations.extend([
            "Implement comprehensive CEO and CFO certification processes for all financial reports",
            "Establish robust disclosure controls and procedures with regular effectiveness testing",
            "Enhance management oversight of financial reporting processes",
            "Implement real-time monitoring of material changes affecting financial condition"
        ])
        
        # Section 404 建议
        recommendations.extend([
            "Conduct annual assessment of internal control over financial reporting effectiveness",
            "Document all key financial reporting controls with clear testing procedures",
            "Implement continuous monitoring of control effectiveness",
            "Establish formal deficiency identification and remediation processes",
            "Enhance IT general controls supporting financial applications",
            "Strengthen segregation of duties in financial processes"
        ])
        
        # Section 409 建议
        recommendations.extend([
            "Implement automated systems for real-time identification of material events",
            "Establish clear criteria and procedures for determining disclosure requirements",
            "Create rapid response teams for material event assessment and disclosure",
            "Implement monitoring systems for disclosure timing compliance"
        ])
        
        # Section 802 建议
        recommendations.extend([
            "Implement comprehensive audit trail systems with tamper protection",
            "Establish document retention policies compliant with SOX requirements",
            "Implement digital signatures and encryption for critical financial documents",
            "Create automated backup and archival systems for audit evidence",
            "Establish regular audit trail integrity verification procedures"
        ])
        
        # Section 906 建议
        recommendations.extend([
            "Establish formal management certification processes with legal review",
            "Implement training programs for executives on SOX certification requirements",
            "Create certification tracking and reminder systems",
            "Establish clear accountability frameworks for financial reporting accuracy"
        ])
        
        # 基于指标的具体建议
        for metric in metrics:
            if metric.status != ComplianceStatus.COMPLIANT:
                if "financial_data_access_control" in metric.name:
                    recommendations.append("Strengthen access controls for financial data systems and implement regular access reviews")
                elif "audit_trail_integrity" in metric.name:
                    recommendations.append("Enhance audit trail protection mechanisms and implement continuous integrity monitoring")
                elif "internal_control" in metric.name:
                    recommendations.append("Redesign and strengthen internal controls over financial reporting")
                elif "disclosure_controls" in metric.name:
                    recommendations.append("Improve disclosure controls and procedures effectiveness")
                elif "segregation_of_duties" in metric.name:
                    recommendations.append("Implement proper segregation of duties in financial processes")
        
        # 基于违规的具体建议
        for violation in violations:
            if violation.severity == "critical":
                recommendations.append(f"URGENT: Address critical SOX violation - {violation.description}")
            elif violation.severity == "high":
                recommendations.append(f"HIGH PRIORITY: Remediate SOX deficiency - {violation.description}")
        
        # 通用SOX最佳实践建议
        recommendations.extend([
            "Establish a SOX compliance program with dedicated resources and clear governance",
            "Implement regular SOX readiness assessments and gap analyses",
            "Create comprehensive SOX training programs for all relevant personnel",
            "Establish continuous monitoring and testing of SOX controls",
            "Implement risk-based approach to SOX compliance with regular risk assessments",
            "Create clear escalation procedures for SOX compliance issues",
            "Establish regular communication with external auditors on SOX matters",
            "Implement technology solutions to automate SOX compliance processes where possible"
        ])
        
        # 去重并返回
        return list(set(recommendations))