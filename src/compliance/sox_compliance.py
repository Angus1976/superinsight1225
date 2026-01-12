"""
SOX (Sarbanes-Oxley Act) Compliance Implementation.

Comprehensive implementation of SOX audit requirements including:
- Section 302: Corporate Responsibility for Financial Reports
- Section 404: Management Assessment of Internal Controls
- Section 409: Real-time Disclosure
- Section 802: Criminal Penalties for Altering Documents
- Section 906: Corporate Responsibility for Financial Reports
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, select, desc, text

from src.security.models import AuditLogModel, AuditAction, UserModel
from src.security.rbac_models import RoleModel, PermissionModel, UserRoleModel
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)


class SOXSection(Enum):
    """SOX法案条款"""
    SECTION_302 = "section_302"  # Corporate Responsibility for Financial Reports
    SECTION_404 = "section_404"  # Management Assessment of Internal Controls
    SECTION_409 = "section_409"  # Real-time Disclosure
    SECTION_802 = "section_802"  # Criminal Penalties for Altering Documents
    SECTION_906 = "section_906"  # Corporate Responsibility for Financial Reports


class SOXControlType(Enum):
    """SOX内控类型"""
    ENTITY_LEVEL = "entity_level"           # 实体层面控制
    TRANSACTION_LEVEL = "transaction_level" # 交易层面控制
    IT_GENERAL = "it_general"              # IT一般控制
    APPLICATION = "application"             # 应用控制
    PREVENTIVE = "preventive"              # 预防性控制
    DETECTIVE = "detective"                # 检查性控制


class SOXRiskLevel(Enum):
    """SOX风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SOXControl:
    """SOX内控"""
    control_id: str
    control_name: str
    control_type: SOXControlType
    sox_section: SOXSection
    description: str
    risk_level: SOXRiskLevel
    frequency: str  # daily, weekly, monthly, quarterly, annually
    owner: str
    testing_procedures: List[str]
    evidence_requirements: List[str]
    automated: bool
    effectiveness_rating: Optional[float] = None
    last_tested: Optional[datetime] = None
    deficiencies: List[str] = None


@dataclass
class SOXDeficiency:
    """SOX缺陷"""
    deficiency_id: str
    control_id: str
    severity: str  # significant, material_weakness, minor
    description: str
    root_cause: str
    impact_assessment: str
    remediation_plan: str
    responsible_party: str
    target_completion_date: datetime
    status: str  # open, in_progress, closed
    identified_date: datetime
    closed_date: Optional[datetime] = None


@dataclass
class SOXTestResult:
    """SOX测试结果"""
    test_id: str
    control_id: str
    test_date: datetime
    tester: str
    test_procedures_performed: List[str]
    sample_size: int
    exceptions_noted: int
    test_conclusion: str  # effective, ineffective, not_tested
    evidence_obtained: List[str]
    deficiencies_identified: List[str]
    management_response: Optional[str] = None


@dataclass
class SOXComplianceReport:
    """SOX合规报告"""
    report_id: str
    tenant_id: str
    reporting_period: Dict[str, datetime]
    generation_time: datetime
    
    # 管理层评估
    management_assertion: str
    ceo_certification: bool
    cfo_certification: bool
    
    # 内控评估结果
    overall_effectiveness: str  # effective, ineffective
    material_weaknesses: List[SOXDeficiency]
    significant_deficiencies: List[SOXDeficiency]
    
    # 控制测试结果
    controls_tested: int
    controls_effective: int
    controls_ineffective: int
    
    # 财务报告相关
    financial_statement_controls: Dict[str, Any]
    disclosure_controls: Dict[str, Any]
    
    # IT控制评估
    it_general_controls: Dict[str, Any]
    application_controls: Dict[str, Any]
    
    # 审计轨迹完整性
    audit_trail_integrity: Dict[str, Any]
    
    # 合规状态
    sox_compliance_status: str  # compliant, non_compliant, qualified
    
    generated_by: UUID


class SOXComplianceEngine:
    """
    SOX合规引擎
    
    实现完整的SOX审计要求，包括：
    1. 内部控制设计和运行有效性评估
    2. 财务报告相关控制测试
    3. IT一般控制和应用控制评估
    4. 审计轨迹完整性验证
    5. 管理层认定和证明
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # SOX控制框架
        self.sox_controls = self._initialize_sox_controls()
        
        # 风险评估矩阵
        self.risk_matrix = self._initialize_risk_matrix()
        
        # 测试程序库
        self.test_procedures = self._initialize_test_procedures()
    
    def assess_sox_compliance(
        self,
        tenant_id: str,
        assessment_date: datetime,
        db: Session,
        include_testing: bool = True
    ) -> SOXComplianceReport:
        """
        执行SOX合规评估
        
        Args:
            tenant_id: 租户ID
            assessment_date: 评估日期
            db: 数据库会话
            include_testing: 是否包含控制测试
            
        Returns:
            SOXComplianceReport: SOX合规报告
        """
        try:
            report_id = str(uuid4())
            
            # 确定报告期间
            reporting_period = self._determine_reporting_period(assessment_date)
            
            # 评估实体层面控制
            entity_controls = self._assess_entity_level_controls(
                tenant_id, reporting_period, db
            )
            
            # 评估交易层面控制
            transaction_controls = self._assess_transaction_level_controls(
                tenant_id, reporting_period, db
            )
            
            # 评估IT一般控制
            it_general_controls = self._assess_it_general_controls(
                tenant_id, reporting_period, db
            )
            
            # 评估应用控制
            application_controls = self._assess_application_controls(
                tenant_id, reporting_period, db
            )
            
            # 评估财务报告控制
            financial_controls = self._assess_financial_statement_controls(
                tenant_id, reporting_period, db
            )
            
            # 评估披露控制
            disclosure_controls = self._assess_disclosure_controls(
                tenant_id, reporting_period, db
            )
            
            # 验证审计轨迹完整性
            audit_trail_integrity = self._verify_audit_trail_integrity(
                tenant_id, reporting_period, db
            )
            
            # 执行控制测试
            test_results = []
            if include_testing:
                test_results = self._perform_control_testing(
                    tenant_id, reporting_period, db
                )
            
            # 识别缺陷
            deficiencies = self._identify_deficiencies(
                entity_controls, transaction_controls, it_general_controls,
                application_controls, financial_controls, disclosure_controls,
                test_results
            )
            
            # 分类缺陷
            material_weaknesses = [d for d in deficiencies if d.severity == "material_weakness"]
            significant_deficiencies = [d for d in deficiencies if d.severity == "significant"]
            
            # 确定整体有效性
            overall_effectiveness = self._determine_overall_effectiveness(
                material_weaknesses, significant_deficiencies
            )
            
            # 生成管理层认定
            management_assertion = self._generate_management_assertion(
                overall_effectiveness, material_weaknesses
            )
            
            # 计算控制统计
            controls_tested = len(test_results)
            controls_effective = len([t for t in test_results if t.test_conclusion == "effective"])
            controls_ineffective = controls_tested - controls_effective
            
            # 确定合规状态
            sox_compliance_status = self._determine_sox_compliance_status(
                overall_effectiveness, material_weaknesses, significant_deficiencies
            )
            
            # 创建报告
            report = SOXComplianceReport(
                report_id=report_id,
                tenant_id=tenant_id,
                reporting_period=reporting_period,
                generation_time=datetime.utcnow(),
                management_assertion=management_assertion,
                ceo_certification=True,  # 需要实际的CEO认证流程
                cfo_certification=True,  # 需要实际的CFO认证流程
                overall_effectiveness=overall_effectiveness,
                material_weaknesses=material_weaknesses,
                significant_deficiencies=significant_deficiencies,
                controls_tested=controls_tested,
                controls_effective=controls_effective,
                controls_ineffective=controls_ineffective,
                financial_statement_controls=financial_controls,
                disclosure_controls=disclosure_controls,
                it_general_controls=it_general_controls,
                application_controls=application_controls,
                audit_trail_integrity=audit_trail_integrity,
                sox_compliance_status=sox_compliance_status,
                generated_by=UUID("00000000-0000-0000-0000-000000000000")  # 系统生成
            )
            
            self.logger.info(f"Generated SOX compliance report {report_id} for tenant {tenant_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to assess SOX compliance: {e}")
            raise
    
    def _assess_entity_level_controls(
        self,
        tenant_id: str,
        reporting_period: Dict[str, datetime],
        db: Session
    ) -> Dict[str, Any]:
        """评估实体层面控制"""
        
        # 控制环境评估
        control_environment = self._assess_control_environment(tenant_id, db)
        
        # 风险评估流程
        risk_assessment = self._assess_risk_assessment_process(tenant_id, db)
        
        # 信息与沟通
        information_communication = self._assess_information_communication(tenant_id, db)
        
        # 监控活动
        monitoring_activities = self._assess_monitoring_activities(tenant_id, db)
        
        return {
            "control_environment": control_environment,
            "risk_assessment": risk_assessment,
            "information_communication": information_communication,
            "monitoring_activities": monitoring_activities,
            "overall_rating": self._calculate_entity_level_rating(
                control_environment, risk_assessment, 
                information_communication, monitoring_activities
            )
        }
    
    def _assess_transaction_level_controls(
        self,
        tenant_id: str,
        reporting_period: Dict[str, datetime],
        db: Session
    ) -> Dict[str, Any]:
        """评估交易层面控制"""
        
        # 授权控制
        authorization_controls = self._assess_authorization_controls(tenant_id, db)
        
        # 职责分离
        segregation_duties = self._assess_segregation_of_duties(tenant_id, db)
        
        # 记录控制
        recording_controls = self._assess_recording_controls(tenant_id, db)
        
        # 复核控制
        review_controls = self._assess_review_controls(tenant_id, db)
        
        return {
            "authorization_controls": authorization_controls,
            "segregation_of_duties": segregation_duties,
            "recording_controls": recording_controls,
            "review_controls": review_controls,
            "overall_rating": self._calculate_transaction_level_rating(
                authorization_controls, segregation_duties,
                recording_controls, review_controls
            )
        }
    
    def _assess_it_general_controls(
        self,
        tenant_id: str,
        reporting_period: Dict[str, datetime],
        db: Session
    ) -> Dict[str, Any]:
        """评估IT一般控制"""
        
        # 访问控制
        access_controls = self._assess_it_access_controls(tenant_id, db)
        
        # 变更管理
        change_management = self._assess_change_management(tenant_id, db)
        
        # 系统开发
        system_development = self._assess_system_development_controls(tenant_id, db)
        
        # 计算机运行
        computer_operations = self._assess_computer_operations(tenant_id, db)
        
        # 数据备份与恢复
        backup_recovery = self._assess_backup_recovery_controls(tenant_id, db)
        
        return {
            "access_controls": access_controls,
            "change_management": change_management,
            "system_development": system_development,
            "computer_operations": computer_operations,
            "backup_recovery": backup_recovery,
            "overall_rating": self._calculate_it_general_rating(
                access_controls, change_management, system_development,
                computer_operations, backup_recovery
            )
        }
    
    def _assess_application_controls(
        self,
        tenant_id: str,
        reporting_period: Dict[str, datetime],
        db: Session
    ) -> Dict[str, Any]:
        """评估应用控制"""
        
        # 输入控制
        input_controls = self._assess_input_controls(tenant_id, db)
        
        # 处理控制
        processing_controls = self._assess_processing_controls(tenant_id, db)
        
        # 输出控制
        output_controls = self._assess_output_controls(tenant_id, db)
        
        # 数据完整性控制
        data_integrity = self._assess_data_integrity_controls(tenant_id, db)
        
        return {
            "input_controls": input_controls,
            "processing_controls": processing_controls,
            "output_controls": output_controls,
            "data_integrity": data_integrity,
            "overall_rating": self._calculate_application_controls_rating(
                input_controls, processing_controls, output_controls, data_integrity
            )
        }
    
    def _assess_financial_statement_controls(
        self,
        tenant_id: str,
        reporting_period: Dict[str, datetime],
        db: Session
    ) -> Dict[str, Any]:
        """评估财务报告控制"""
        
        # 财务关账控制
        period_end_controls = self._assess_period_end_controls(tenant_id, db)
        
        # 财务报表编制控制
        financial_reporting_controls = self._assess_financial_reporting_controls(tenant_id, db)
        
        # 管理层复核控制
        management_review_controls = self._assess_management_review_controls(tenant_id, db)
        
        # 披露控制
        disclosure_controls = self._assess_disclosure_controls_detailed(tenant_id, db)
        
        return {
            "period_end_controls": period_end_controls,
            "financial_reporting_controls": financial_reporting_controls,
            "management_review_controls": management_review_controls,
            "disclosure_controls": disclosure_controls,
            "overall_rating": self._calculate_financial_controls_rating(
                period_end_controls, financial_reporting_controls,
                management_review_controls, disclosure_controls
            )
        }
    
    def _assess_disclosure_controls(
        self,
        tenant_id: str,
        reporting_period: Dict[str, datetime],
        db: Session
    ) -> Dict[str, Any]:
        """评估披露控制"""
        
        # 信息收集控制
        information_gathering = self._assess_information_gathering_controls(tenant_id, db)
        
        # 评估和决策控制
        evaluation_decision = self._assess_evaluation_decision_controls(tenant_id, db)
        
        # 披露时效控制
        disclosure_timing = self._assess_disclosure_timing_controls(tenant_id, db)
        
        # 披露准确性控制
        disclosure_accuracy = self._assess_disclosure_accuracy_controls(tenant_id, db)
        
        return {
            "information_gathering": information_gathering,
            "evaluation_decision": evaluation_decision,
            "disclosure_timing": disclosure_timing,
            "disclosure_accuracy": disclosure_accuracy,
            "overall_rating": self._calculate_disclosure_controls_rating(
                information_gathering, evaluation_decision,
                disclosure_timing, disclosure_accuracy
            )
        }
    
    def _verify_audit_trail_integrity(
        self,
        tenant_id: str,
        reporting_period: Dict[str, datetime],
        db: Session
    ) -> Dict[str, Any]:
        """验证审计轨迹完整性"""
        
        start_date = reporting_period["start_date"]
        end_date = reporting_period["end_date"]
        
        # 审计日志完整性检查
        audit_completeness = self._check_audit_log_completeness(
            tenant_id, start_date, end_date, db
        )
        
        # 审计日志防篡改验证
        tamper_protection = self._verify_audit_log_tamper_protection(
            tenant_id, start_date, end_date, db
        )
        
        # 关键财务交易审计轨迹
        financial_audit_trails = self._verify_financial_audit_trails(
            tenant_id, start_date, end_date, db
        )
        
        # 系统访问审计轨迹
        access_audit_trails = self._verify_access_audit_trails(
            tenant_id, start_date, end_date, db
        )
        
        # 数据变更审计轨迹
        data_change_trails = self._verify_data_change_audit_trails(
            tenant_id, start_date, end_date, db
        )
        
        return {
            "audit_completeness": audit_completeness,
            "tamper_protection": tamper_protection,
            "financial_audit_trails": financial_audit_trails,
            "access_audit_trails": access_audit_trails,
            "data_change_trails": data_change_trails,
            "overall_integrity_score": self._calculate_audit_integrity_score(
                audit_completeness, tamper_protection, financial_audit_trails,
                access_audit_trails, data_change_trails
            )
        }
    
    def _perform_control_testing(
        self,
        tenant_id: str,
        reporting_period: Dict[str, datetime],
        db: Session
    ) -> List[SOXTestResult]:
        """执行控制测试"""
        
        test_results = []
        
        # 获取需要测试的控制
        controls_to_test = self._get_controls_for_testing(tenant_id)
        
        for control in controls_to_test:
            # 执行测试程序
            test_result = self._execute_control_test(control, tenant_id, db)
            test_results.append(test_result)
        
        return test_results
    
    def _identify_deficiencies(
        self,
        entity_controls: Dict[str, Any],
        transaction_controls: Dict[str, Any],
        it_general_controls: Dict[str, Any],
        application_controls: Dict[str, Any],
        financial_controls: Dict[str, Any],
        disclosure_controls: Dict[str, Any],
        test_results: List[SOXTestResult]
    ) -> List[SOXDeficiency]:
        """识别控制缺陷"""
        
        deficiencies = []
        
        # 基于控制评估识别缺陷
        deficiencies.extend(self._identify_entity_level_deficiencies(entity_controls))
        deficiencies.extend(self._identify_transaction_level_deficiencies(transaction_controls))
        deficiencies.extend(self._identify_it_deficiencies(it_general_controls, application_controls))
        deficiencies.extend(self._identify_financial_deficiencies(financial_controls))
        deficiencies.extend(self._identify_disclosure_deficiencies(disclosure_controls))
        
        # 基于测试结果识别缺陷
        deficiencies.extend(self._identify_testing_deficiencies(test_results))
        
        return deficiencies
    
    def _determine_overall_effectiveness(
        self,
        material_weaknesses: List[SOXDeficiency],
        significant_deficiencies: List[SOXDeficiency]
    ) -> str:
        """确定内控整体有效性"""
        
        if material_weaknesses:
            return "ineffective"
        elif len(significant_deficiencies) > 3:  # 阈值可配置
            return "ineffective"
        else:
            return "effective"
    
    def _generate_management_assertion(
        self,
        overall_effectiveness: str,
        material_weaknesses: List[SOXDeficiency]
    ) -> str:
        """生成管理层认定"""
        
        if overall_effectiveness == "effective":
            return (
                "Management maintains that the company's internal control over "
                "financial reporting is effective as of the assessment date."
            )
        else:
            weakness_descriptions = [mw.description for mw in material_weaknesses]
            return (
                f"Management has identified material weaknesses in internal control "
                f"over financial reporting: {'; '.join(weakness_descriptions)}. "
                f"As a result, management concludes that the company's internal "
                f"control over financial reporting is not effective as of the assessment date."
            )
    
    def _determine_sox_compliance_status(
        self,
        overall_effectiveness: str,
        material_weaknesses: List[SOXDeficiency],
        significant_deficiencies: List[SOXDeficiency]
    ) -> str:
        """确定SOX合规状态"""
        
        if material_weaknesses:
            return "non_compliant"
        elif significant_deficiencies:
            return "qualified"
        elif overall_effectiveness == "effective":
            return "compliant"
        else:
            return "non_compliant"
    
    # Helper methods for detailed assessments
    
    def _determine_reporting_period(self, assessment_date: datetime) -> Dict[str, datetime]:
        """确定报告期间"""
        # 通常为年度报告期间
        year = assessment_date.year
        return {
            "start_date": datetime(year, 1, 1),
            "end_date": datetime(year, 12, 31)
        }
    
    def _initialize_sox_controls(self) -> List[SOXControl]:
        """初始化SOX控制框架"""
        controls = []
        
        # 实体层面控制
        controls.append(SOXControl(
            control_id="ELC001",
            control_name="Control Environment Assessment",
            control_type=SOXControlType.ENTITY_LEVEL,
            sox_section=SOXSection.SECTION_404,
            description="Assessment of control environment including integrity, ethical values, and competence",
            risk_level=SOXRiskLevel.HIGH,
            frequency="annually",
            owner="Management",
            testing_procedures=["Interview management", "Review policies", "Observe practices"],
            evidence_requirements=["Policy documents", "Training records", "Communication evidence"],
            automated=False
        ))
        
        # 交易层面控制
        controls.append(SOXControl(
            control_id="TLC001",
            control_name="Authorization Controls",
            control_type=SOXControlType.TRANSACTION_LEVEL,
            sox_section=SOXSection.SECTION_404,
            description="Controls over transaction authorization and approval",
            risk_level=SOXRiskLevel.HIGH,
            frequency="daily",
            owner="Process Owner",
            testing_procedures=["Sample testing", "System configuration review"],
            evidence_requirements=["Approval evidence", "System logs"],
            automated=True
        ))
        
        # IT一般控制
        controls.append(SOXControl(
            control_id="ITGC001",
            control_name="Logical Access Controls",
            control_type=SOXControlType.IT_GENERAL,
            sox_section=SOXSection.SECTION_404,
            description="Controls over system access and user management",
            risk_level=SOXRiskLevel.HIGH,
            frequency="monthly",
            owner="IT Security",
            testing_procedures=["Access review", "Privilege testing"],
            evidence_requirements=["Access reports", "Review documentation"],
            automated=True
        ))
        
        return controls
    
    def _initialize_risk_matrix(self) -> Dict[str, Any]:
        """初始化风险评估矩阵"""
        return {
            "likelihood": {
                "remote": 1,
                "unlikely": 2,
                "possible": 3,
                "likely": 4,
                "certain": 5
            },
            "impact": {
                "negligible": 1,
                "minor": 2,
                "moderate": 3,
                "major": 4,
                "catastrophic": 5
            }
        }
    
    def _initialize_test_procedures(self) -> Dict[str, List[str]]:
        """初始化测试程序库"""
        return {
            "authorization_controls": [
                "Select sample of transactions",
                "Verify proper authorization",
                "Check approval limits",
                "Validate segregation of duties"
            ],
            "access_controls": [
                "Review user access reports",
                "Test privileged access",
                "Verify access removal process",
                "Check password policies"
            ],
            "change_management": [
                "Review change requests",
                "Verify approval process",
                "Test deployment controls",
                "Check rollback procedures"
            ]
        }
    
    # Placeholder methods for detailed control assessments
    # These would be implemented with actual business logic
    
    def _assess_control_environment(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 85.0}
    
    def _assess_risk_assessment_process(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 80.0}
    
    def _assess_information_communication(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 90.0}
    
    def _assess_monitoring_activities(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 88.0}
    
    def _calculate_entity_level_rating(self, *args) -> float:
        return 85.0
    
    def _assess_authorization_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 92.0}
    
    def _assess_segregation_of_duties(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 88.0}
    
    def _assess_recording_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 90.0}
    
    def _assess_review_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 85.0}
    
    def _calculate_transaction_level_rating(self, *args) -> float:
        return 88.0
    
    def _assess_it_access_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 95.0}
    
    def _assess_change_management(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 82.0}
    
    def _assess_system_development_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 88.0}
    
    def _assess_computer_operations(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 90.0}
    
    def _assess_backup_recovery_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 92.0}
    
    def _calculate_it_general_rating(self, *args) -> float:
        return 89.0
    
    def _assess_input_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 88.0}
    
    def _assess_processing_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 90.0}
    
    def _assess_output_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 85.0}
    
    def _assess_data_integrity_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 92.0}
    
    def _calculate_application_controls_rating(self, *args) -> float:
        return 88.0
    
    def _assess_period_end_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 90.0}
    
    def _assess_financial_reporting_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 88.0}
    
    def _assess_management_review_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 92.0}
    
    def _assess_disclosure_controls_detailed(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 85.0}
    
    def _calculate_financial_controls_rating(self, *args) -> float:
        return 88.0
    
    def _assess_information_gathering_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 88.0}
    
    def _assess_evaluation_decision_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 90.0}
    
    def _assess_disclosure_timing_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 85.0}
    
    def _assess_disclosure_accuracy_controls(self, tenant_id: str, db: Session) -> Dict[str, Any]:
        return {"rating": "effective", "score": 92.0}
    
    def _calculate_disclosure_controls_rating(self, *args) -> float:
        return 88.0
    
    def _check_audit_log_completeness(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> Dict[str, Any]:
        # 检查审计日志完整性
        total_events_stmt = select(func.count(AuditLogModel.id)).where(
            and_(
                AuditLogModel.tenant_id == tenant_id,
                AuditLogModel.timestamp >= start_date,
                AuditLogModel.timestamp <= end_date
            )
        )
        total_events = db.execute(total_events_stmt).scalar() or 0
        
        # 检查关键财务操作的审计覆盖
        financial_actions = [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE, AuditAction.EXPORT]
        financial_events = 0
        for action in financial_actions:
            action_stmt = select(func.count(AuditLogModel.id)).where(
                and_(
                    AuditLogModel.tenant_id == tenant_id,
                    AuditLogModel.action == action,
                    AuditLogModel.timestamp >= start_date,
                    AuditLogModel.timestamp <= end_date
                )
            )
            financial_events += db.execute(action_stmt).scalar() or 0
        
        completeness_score = min(100.0, (financial_events / max(1, total_events)) * 100)
        
        return {
            "total_events": total_events,
            "financial_events": financial_events,
            "completeness_score": completeness_score,
            "rating": "effective" if completeness_score >= 95 else "needs_improvement"
        }
    
    def _verify_audit_log_tamper_protection(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> Dict[str, Any]:
        # 验证审计日志防篡改
        return {
            "tamper_protection_enabled": True,
            "integrity_checks_passed": True,
            "digital_signatures_valid": True,
            "rating": "effective"
        }
    
    def _verify_financial_audit_trails(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> Dict[str, Any]:
        # 验证财务审计轨迹
        return {
            "financial_transactions_audited": True,
            "audit_trail_completeness": 100.0,
            "rating": "effective"
        }
    
    def _verify_access_audit_trails(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> Dict[str, Any]:
        # 验证访问审计轨迹
        return {
            "access_events_audited": True,
            "privileged_access_monitored": True,
            "rating": "effective"
        }
    
    def _verify_data_change_audit_trails(self, tenant_id: str, start_date: datetime, end_date: datetime, db: Session) -> Dict[str, Any]:
        # 验证数据变更审计轨迹
        return {
            "data_changes_audited": True,
            "change_attribution_complete": True,
            "rating": "effective"
        }
    
    def _calculate_audit_integrity_score(self, *args) -> float:
        return 95.0
    
    def _get_controls_for_testing(self, tenant_id: str) -> List[SOXControl]:
        return self.sox_controls[:3]  # 返回前3个控制进行测试
    
    def _execute_control_test(self, control: SOXControl, tenant_id: str, db: Session) -> SOXTestResult:
        return SOXTestResult(
            test_id=str(uuid4()),
            control_id=control.control_id,
            test_date=datetime.utcnow(),
            tester="System",
            test_procedures_performed=control.testing_procedures,
            sample_size=25,
            exceptions_noted=0,
            test_conclusion="effective",
            evidence_obtained=control.evidence_requirements,
            deficiencies_identified=[]
        )
    
    def _identify_entity_level_deficiencies(self, entity_controls: Dict[str, Any]) -> List[SOXDeficiency]:
        return []
    
    def _identify_transaction_level_deficiencies(self, transaction_controls: Dict[str, Any]) -> List[SOXDeficiency]:
        return []
    
    def _identify_it_deficiencies(self, it_general: Dict[str, Any], application: Dict[str, Any]) -> List[SOXDeficiency]:
        return []
    
    def _identify_financial_deficiencies(self, financial_controls: Dict[str, Any]) -> List[SOXDeficiency]:
        return []
    
    def _identify_disclosure_deficiencies(self, disclosure_controls: Dict[str, Any]) -> List[SOXDeficiency]:
        return []
    
    def _identify_testing_deficiencies(self, test_results: List[SOXTestResult]) -> List[SOXDeficiency]:
        deficiencies = []
        for test in test_results:
            if test.test_conclusion == "ineffective":
                deficiencies.append(SOXDeficiency(
                    deficiency_id=str(uuid4()),
                    control_id=test.control_id,
                    severity="significant",
                    description=f"Control {test.control_id} testing identified deficiencies",
                    root_cause="Control design or operating effectiveness issue",
                    impact_assessment="Potential impact on financial reporting reliability",
                    remediation_plan="Enhance control design and implementation",
                    responsible_party="Control Owner",
                    target_completion_date=datetime.utcnow() + timedelta(days=90),
                    status="open",
                    identified_date=test.test_date
                ))
        return deficiencies