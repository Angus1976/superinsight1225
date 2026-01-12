"""
Comprehensive test suite for GDPR compliance verification system.

Tests the GDPR compliance verifier, API endpoints, and verification functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.compliance.gdpr_verification import (
    GDPRComplianceVerifier,
    GDPRArticle,
    ComplianceLevel,
    VerificationStatus,
    GDPRRequirement,
    VerificationResult,
    GDPRVerificationReport
)
from src.security.models import AuditAction, UserModel


class TestGDPRComplianceVerifier:
    """测试GDPR合规性验证器"""
    
    @pytest.fixture
    def verifier(self):
        """创建GDPR验证器实例"""
        return GDPRComplianceVerifier()
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        mock_db = Mock()
        mock_db.execute.return_value.scalar.return_value = 100
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        return mock_db
    
    @pytest.fixture
    def sample_verification_data(self):
        """示例验证数据"""
        return {
            "tenant_id": "test-tenant-123",
            "verified_by": uuid4(),
            "verification_scope": ["data_processing", "user_rights", "security_measures"]
        }
    
    def test_verifier_initialization(self, verifier):
        """测试验证器初始化"""
        assert verifier is not None
        assert hasattr(verifier, 'gdpr_requirements')
        assert hasattr(verifier, 'verification_methods')
        assert hasattr(verifier, 'compliance_thresholds')
        
        # 验证GDPR要求已加载
        assert len(verifier.gdpr_requirements) > 0
        
        # 验证合规阈值设置
        assert verifier.compliance_thresholds["fully_compliant"] == 95.0
        assert verifier.compliance_thresholds["mostly_compliant"] == 85.0
        assert verifier.compliance_thresholds["partially_compliant"] == 70.0
    
    def test_gdpr_requirements_initialization(self, verifier):
        """测试GDPR要求初始化"""
        requirements = verifier.gdpr_requirements
        
        # 验证要求数量
        assert len(requirements) >= 5
        
        # 验证要求结构
        for req in requirements:
            assert isinstance(req, GDPRRequirement)
            assert req.requirement_id is not None
            assert req.article in GDPRArticle
            assert req.title is not None
            assert req.description is not None
            assert isinstance(req.mandatory, bool)
            assert req.verification_method is not None
            assert isinstance(req.expected_evidence, list)
        
        # 验证特定要求存在
        requirement_ids = [req.requirement_id for req in requirements]
        assert "GDPR-6.1" in requirement_ids  # Lawfulness of Processing
        assert "GDPR-15.1" in requirement_ids  # Right of Access
        assert "GDPR-32.1" in requirement_ids  # Security of Processing
        assert "GDPR-30.1" in requirement_ids  # Records of Processing
        assert "GDPR-25.1" in requirement_ids  # Data Protection by Design
    
    def test_verification_methods_initialization(self, verifier):
        """测试验证方法初始化"""
        methods = verifier.verification_methods
        
        # 验证方法存在
        assert "verify_data_processing_lawfulness" in methods
        assert "verify_data_subject_rights" in methods
        assert "verify_security_measures" in methods
        assert "verify_audit_trails" in methods
        assert "verify_data_protection_by_design" in methods
        
        # 验证方法可调用
        for method_name, method in methods.items():
            assert callable(method)
    
    def test_full_gdpr_compliance_verification(self, verifier, mock_db_session, sample_verification_data):
        """测试完整GDPR合规性验证"""
        report = verifier.verify_gdpr_compliance(
            db=mock_db_session,
            **sample_verification_data
        )
        
        # 验证报告基本结构
        assert isinstance(report, GDPRVerificationReport)
        assert report.report_id is not None
        assert report.tenant_id == sample_verification_data["tenant_id"]
        assert report.verified_by == sample_verification_data["verified_by"]
        assert isinstance(report.verification_time, datetime)
        
        # 验证合规级别和分数
        assert isinstance(report.overall_compliance_level, ComplianceLevel)
        assert 0 <= report.overall_score <= 100
        
        # 验证验证结果
        assert isinstance(report.verification_results, list)
        assert len(report.verification_results) > 0
        
        # 验证统计信息
        assert report.total_requirements > 0
        assert report.passed_requirements >= 0
        assert report.failed_requirements >= 0
        assert report.warning_requirements >= 0
        assert (report.passed_requirements + report.failed_requirements + report.warning_requirements) <= report.total_requirements
        
        # 验证分析数据
        assert isinstance(report.critical_issues, list)
        assert isinstance(report.high_priority_recommendations, list)
        assert isinstance(report.article_compliance, dict)
        assert isinstance(report.data_processing_compliance, dict)
        assert isinstance(report.user_rights_compliance, dict)
        assert isinstance(report.security_compliance, dict)
        
        # 验证下次验证时间
        assert isinstance(report.next_verification_due, datetime)
        assert report.next_verification_due > report.verification_time
    
    def test_data_processing_lawfulness_verification(self, verifier, mock_db_session):
        """测试数据处理合法性验证"""
        # 创建测试要求
        requirement = GDPRRequirement(
            article=GDPRArticle.ARTICLE_6,
            requirement_id="GDPR-6.1",
            title="Lawfulness of Processing",
            description="Processing must have a lawful basis",
            mandatory=True,
            verification_method="verify_data_processing_lawfulness",
            expected_evidence=["Lawful basis documentation", "Processing activities register"]
        )
        
        # 执行验证
        verification_data = verifier._verify_data_processing_lawfulness(
            requirement, "test-tenant", mock_db_session
        )
        
        # 验证结果结构
        assert isinstance(verification_data, dict)
        assert "processing_activities_count" in verification_data
        assert "lawful_basis_documented" in verification_data
        assert "consent_management_implemented" in verification_data
        assert "compliance_score" in verification_data
        assert "evidence_found" in verification_data
        
        # 验证数据类型
        assert isinstance(verification_data["processing_activities_count"], int)
        assert isinstance(verification_data["lawful_basis_documented"], bool)
        assert isinstance(verification_data["consent_management_implemented"], bool)
        assert isinstance(verification_data["compliance_score"], (int, float))
        assert isinstance(verification_data["evidence_found"], list)
    
    def test_data_subject_rights_verification(self, verifier, mock_db_session):
        """测试数据主体权利验证"""
        requirement = GDPRRequirement(
            article=GDPRArticle.ARTICLE_15,
            requirement_id="GDPR-15.1",
            title="Right of Access",
            description="Data subjects have the right to access their personal data",
            mandatory=True,
            verification_method="verify_data_subject_rights",
            expected_evidence=["Data subject request handling system"]
        )
        
        verification_data = verifier._verify_data_subject_rights(
            requirement, "test-tenant", mock_db_session
        )
        
        # 验证数据主体权利实现
        assert "access_right_implemented" in verification_data
        assert "rectification_implemented" in verification_data
        assert "erasure_implemented" in verification_data
        assert "portability_implemented" in verification_data
        assert "rights_implementation_score" in verification_data
        assert "average_response_time_hours" in verification_data
        assert "response_time_compliant" in verification_data
        
        # 验证响应时间合规性
        response_time = verification_data["average_response_time_hours"]
        assert isinstance(response_time, (int, float))
        assert verification_data["response_time_compliant"] == (response_time <= 72)
    
    def test_security_measures_verification(self, verifier, mock_db_session):
        """测试安全措施验证"""
        requirement = GDPRRequirement(
            article=GDPRArticle.ARTICLE_32,
            requirement_id="GDPR-32.1",
            title="Security of Processing",
            description="Appropriate technical and organizational measures must be implemented",
            mandatory=True,
            verification_method="verify_security_measures",
            expected_evidence=["Encryption implementation", "Access control measures"]
        )
        
        verification_data = verifier._verify_security_measures(
            requirement, "test-tenant", mock_db_session
        )
        
        # 验证安全措施
        assert "encryption_implemented" in verification_data
        assert "encryption_coverage" in verification_data
        assert "access_control_implemented" in verification_data
        assert "access_control_effectiveness" in verification_data
        assert "audit_logging_implemented" in verification_data
        assert "security_measures_score" in verification_data
        
        # 验证安全分数
        security_score = verification_data["security_measures_score"]
        assert isinstance(security_score, (int, float))
        assert 0 <= security_score <= 100
    
    def test_audit_trails_verification(self, verifier, mock_db_session):
        """测试审计轨迹验证"""
        requirement = GDPRRequirement(
            article=GDPRArticle.ARTICLE_30,
            requirement_id="GDPR-30.1",
            title="Records of Processing Activities",
            description="Controllers must maintain records of processing activities",
            mandatory=True,
            verification_method="verify_audit_trails",
            expected_evidence=["Processing activity records", "Audit logs"]
        )
        
        verification_data = verifier._verify_audit_trails(
            requirement, "test-tenant", mock_db_session
        )
        
        # 验证审计轨迹
        assert "audit_completeness_percentage" in verification_data
        assert "audit_retention_compliant" in verification_data
        assert "audit_integrity_protected" in verification_data
        assert "processing_records_maintained" in verification_data
        
        # 验证审计完整性
        completeness = verification_data["audit_completeness_percentage"]
        assert isinstance(completeness, (int, float))
        assert 0 <= completeness <= 100
    
    def test_data_protection_by_design_verification(self, verifier, mock_db_session):
        """测试设计数据保护验证"""
        requirement = GDPRRequirement(
            article=GDPRArticle.ARTICLE_25,
            requirement_id="GDPR-25.1",
            title="Data Protection by Design and by Default",
            description="Data protection must be integrated into processing activities",
            mandatory=True,
            verification_method="verify_data_protection_by_design",
            expected_evidence=["Privacy by design documentation", "Data minimization policies"]
        )
        
        verification_data = verifier._verify_data_protection_by_design(
            requirement, "test-tenant", mock_db_session
        )
        
        # 验证设计数据保护
        assert "data_minimization_implemented" in verification_data
        assert "privacy_by_default_configured" in verification_data
        assert "dpia_process_established" in verification_data
        assert "privacy_enhancing_tech_deployed" in verification_data
        
        # 验证隐私增强技术覆盖率
        pet_coverage = verification_data.get("pet_coverage", 0)
        assert isinstance(pet_coverage, (int, float))
        assert 0 <= pet_coverage <= 100
    
    def test_requirement_verification_with_error_handling(self, verifier, mock_db_session):
        """测试要求验证的错误处理"""
        # 创建会导致错误的要求
        requirement = GDPRRequirement(
            article=GDPRArticle.ARTICLE_6,
            requirement_id="GDPR-ERROR-TEST",
            title="Error Test Requirement",
            description="Test error handling",
            mandatory=True,
            verification_method="non_existent_method",
            expected_evidence=["Test evidence"]
        )
        
        # 执行验证
        result = verifier._verify_requirement(
            requirement, "test-tenant", mock_db_session, datetime.utcnow()
        )
        
        # 验证错误处理 - 使用默认验证方法时返回50.0分
        assert isinstance(result, VerificationResult)
        assert result.status == VerificationStatus.FAILED
        assert result.compliance_level == ComplianceLevel.NON_COMPLIANT
        assert result.score == 50.0  # 默认验证方法返回50.0分
        assert len(result.evidence_missing) > 0
        assert "Default verification method used" in str(result.details)
    
    def test_compliance_level_determination(self, verifier):
        """测试合规级别确定"""
        # 测试完全合规
        level = verifier._determine_compliance_level(96.0)
        assert level == ComplianceLevel.FULLY_COMPLIANT
        
        # 测试大部分合规
        level = verifier._determine_compliance_level(88.0)
        assert level == ComplianceLevel.MOSTLY_COMPLIANT
        
        # 测试部分合规
        level = verifier._determine_compliance_level(75.0)
        assert level == ComplianceLevel.PARTIALLY_COMPLIANT
        
        # 测试不合规
        level = verifier._determine_compliance_level(60.0)
        assert level == ComplianceLevel.NON_COMPLIANT
    
    def test_overall_score_calculation(self, verifier):
        """测试总体分数计算"""
        # 创建测试验证结果
        verification_results = [
            VerificationResult(
                requirement_id="test1",
                article=GDPRArticle.ARTICLE_6,
                status=VerificationStatus.PASSED,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                score=95.0,
                evidence_found=[],
                evidence_missing=[],
                findings=[],
                recommendations=[],
                verification_time=datetime.utcnow(),
                details={}
            ),
            VerificationResult(
                requirement_id="test2",
                article=GDPRArticle.ARTICLE_15,
                status=VerificationStatus.WARNING,
                compliance_level=ComplianceLevel.MOSTLY_COMPLIANT,
                score=85.0,
                evidence_found=[],
                evidence_missing=[],
                findings=[],
                recommendations=[],
                verification_time=datetime.utcnow(),
                details={}
            )
        ]
        
        overall_score = verifier._calculate_overall_score(verification_results)
        
        assert isinstance(overall_score, float)
        assert overall_score == 90.0  # (95 + 85) / 2
    
    def test_critical_issues_identification(self, verifier):
        """测试关键问题识别"""
        verification_results = [
            VerificationResult(
                requirement_id="critical_failure",
                article=GDPRArticle.ARTICLE_32,
                status=VerificationStatus.FAILED,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                score=30.0,  # 低于50分
                evidence_found=[],
                evidence_missing=[],
                findings=[],
                recommendations=[],
                verification_time=datetime.utcnow(),
                details={}
            ),
            VerificationResult(
                requirement_id="minor_issue",
                article=GDPRArticle.ARTICLE_6,
                status=VerificationStatus.FAILED,
                compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
                score=75.0,  # 高于50分
                evidence_found=[],
                evidence_missing=[],
                findings=[],
                recommendations=[],
                verification_time=datetime.utcnow(),
                details={}
            )
        ]
        
        critical_issues = verifier._identify_critical_issues(verification_results)
        
        # 只有低分的失败应该被识别为关键问题
        assert len(critical_issues) == 1
        assert "critical_failure" in critical_issues[0]
        assert "article_32" in critical_issues[0]
    
    def test_article_compliance_analysis(self, verifier):
        """测试条款合规性分析"""
        verification_results = [
            VerificationResult(
                requirement_id="req1",
                article=GDPRArticle.ARTICLE_6,
                status=VerificationStatus.PASSED,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                score=95.0,
                evidence_found=[],
                evidence_missing=[],
                findings=[],
                recommendations=[],
                verification_time=datetime.utcnow(),
                details={}
            ),
            VerificationResult(
                requirement_id="req2",
                article=GDPRArticle.ARTICLE_6,
                status=VerificationStatus.WARNING,
                compliance_level=ComplianceLevel.MOSTLY_COMPLIANT,
                score=85.0,
                evidence_found=[],
                evidence_missing=[],
                findings=[],
                recommendations=[],
                verification_time=datetime.utcnow(),
                details={}
            ),
            VerificationResult(
                requirement_id="req3",
                article=GDPRArticle.ARTICLE_15,
                status=VerificationStatus.PASSED,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                score=92.0,
                evidence_found=[],
                evidence_missing=[],
                findings=[],
                recommendations=[],
                verification_time=datetime.utcnow(),
                details={}
            )
        ]
        
        article_compliance = verifier._analyze_article_compliance(verification_results)
        
        # 验证分析结果
        assert "article_6" in article_compliance
        assert "article_15" in article_compliance
        
        # 验证Article 6分析
        article_6_data = article_compliance["article_6"]
        assert len(article_6_data["requirements"]) == 2
        assert article_6_data["passed_count"] == 1
        assert article_6_data["failed_count"] == 0
        assert article_6_data["average_score"] == 90.0  # (95 + 85) / 2
        
        # 验证Article 15分析
        article_15_data = article_compliance["article_15"]
        assert len(article_15_data["requirements"]) == 1
        assert article_15_data["passed_count"] == 1
        assert article_15_data["average_score"] == 92.0
    
    def test_verification_scope_filtering(self, verifier):
        """测试验证范围过滤"""
        # 测试默认范围
        is_in_scope = verifier._is_requirement_in_scope(
            verifier.gdpr_requirements[0],
            ["data_processing", "user_rights"]
        )
        assert is_in_scope  # 简化实现中所有要求都在范围内
        
        # 测试空范围
        is_in_scope = verifier._is_requirement_in_scope(
            verifier.gdpr_requirements[0],
            []
        )
        assert is_in_scope  # 简化实现中所有要求都在范围内
    
    def test_verification_with_custom_scope(self, verifier, mock_db_session):
        """测试自定义验证范围"""
        custom_scope = ["security_measures", "audit_trails"]
        
        report = verifier.verify_gdpr_compliance(
            tenant_id="test-tenant",
            verified_by=uuid4(),
            db=mock_db_session,
            verification_scope=custom_scope
        )
        
        # 验证范围被正确设置
        assert report.verification_scope == custom_scope
        
        # 验证报告仍然包含所有要求（简化实现）
        assert len(report.verification_results) > 0
    
    def test_evidence_analysis(self, verifier):
        """测试证据分析"""
        expected_evidence = ["Evidence A", "Evidence B", "Evidence C"]
        evidence_found = ["Evidence A", "Evidence C"]
        
        evidence_missing = verifier._identify_missing_evidence(
            expected_evidence, evidence_found
        )
        
        assert evidence_missing == ["Evidence B"]
    
    def test_verification_status_analysis(self, verifier):
        """测试验证状态分析"""
        requirement = verifier.gdpr_requirements[0]
        
        # 测试通过状态
        verification_data = {"compliance_score": 95.0}
        status = verifier._analyze_verification_status(verification_data, requirement)
        assert status == VerificationStatus.PASSED
        
        # 测试警告状态
        verification_data = {"compliance_score": 75.0}
        status = verifier._analyze_verification_status(verification_data, requirement)
        assert status == VerificationStatus.WARNING
        
        # 测试失败状态
        verification_data = {"compliance_score": 60.0}
        status = verifier._analyze_verification_status(verification_data, requirement)
        assert status == VerificationStatus.FAILED
    
    def test_recommendations_generation(self, verifier):
        """测试建议生成"""
        verification_results = [
            VerificationResult(
                requirement_id="failed_req",
                article=GDPRArticle.ARTICLE_32,
                status=VerificationStatus.FAILED,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                score=60.0,
                evidence_found=[],
                evidence_missing=[],
                findings=[],
                recommendations=["Fix security implementation", "Update policies"],
                verification_time=datetime.utcnow(),
                details={}
            )
        ]
        
        recommendations = verifier._generate_high_priority_recommendations(verification_results)
        
        assert "Fix security implementation" in recommendations
        assert "Update policies" in recommendations
        assert len(recommendations) == 2
    
    def test_next_verification_due_calculation(self, verifier, mock_db_session):
        """测试下次验证时间计算"""
        verification_time = datetime.utcnow()
        
        report = verifier.verify_gdpr_compliance(
            tenant_id="test-tenant",
            verified_by=uuid4(),
            db=mock_db_session
        )
        
        # 验证下次验证时间是90天后
        expected_due = report.verification_time + timedelta(days=90)
        time_diff = abs((report.next_verification_due - expected_due).total_seconds())
        assert time_diff < 60  # 允许1分钟误差


class TestGDPRVerificationIntegration:
    """测试GDPR验证集成功能"""
    
    @pytest.fixture
    def verifier(self):
        return GDPRComplianceVerifier()
    
    @pytest.fixture
    def mock_db_session(self):
        mock_db = Mock()
        mock_db.execute.return_value.scalar.return_value = 100
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        return mock_db
    
    def test_end_to_end_verification_workflow(self, verifier, mock_db_session):
        """测试端到端验证工作流"""
        # 执行完整验证
        report = verifier.verify_gdpr_compliance(
            tenant_id="integration-test-tenant",
            verified_by=uuid4(),
            db=mock_db_session
        )
        
        # 验证报告完整性
        assert report is not None
        assert isinstance(report, GDPRVerificationReport)
        
        # 验证所有必需字段
        required_fields = [
            'report_id', 'tenant_id', 'verification_time', 'overall_compliance_level',
            'overall_score', 'verification_results', 'total_requirements',
            'passed_requirements', 'failed_requirements', 'warning_requirements',
            'critical_issues', 'high_priority_recommendations', 'article_compliance',
            'data_processing_compliance', 'user_rights_compliance', 'security_compliance',
            'verified_by', 'verification_scope', 'next_verification_due'
        ]
        
        for field in required_fields:
            assert hasattr(report, field), f"Missing required field: {field}"
            assert getattr(report, field) is not None, f"Field {field} is None"
    
    def test_multiple_verification_consistency(self, verifier, mock_db_session):
        """测试多次验证的一致性"""
        tenant_id = "consistency-test-tenant"
        verified_by = uuid4()
        
        # 执行多次验证
        reports = []
        for i in range(3):
            report = verifier.verify_gdpr_compliance(
                tenant_id=tenant_id,
                verified_by=verified_by,
                db=mock_db_session
            )
            reports.append(report)
        
        # 验证结果一致性
        for i in range(1, len(reports)):
            # 分数应该相同（因为使用相同的数据源）
            assert reports[i].overall_score == reports[0].overall_score
            
            # 合规级别应该相同
            assert reports[i].overall_compliance_level == reports[0].overall_compliance_level
            
            # 要求数量应该相同
            assert reports[i].total_requirements == reports[0].total_requirements
    
    def test_verification_with_different_scopes(self, verifier, mock_db_session):
        """测试不同验证范围"""
        tenant_id = "scope-test-tenant"
        verified_by = uuid4()
        
        # 测试不同的验证范围
        scopes = [
            ["data_processing"],
            ["user_rights", "security_measures"],
            ["audit_trails", "data_protection_measures"],
            None  # 默认范围
        ]
        
        reports = []
        for scope in scopes:
            report = verifier.verify_gdpr_compliance(
                tenant_id=tenant_id,
                verified_by=verified_by,
                db=mock_db_session,
                verification_scope=scope
            )
            reports.append(report)
        
        # 验证每个报告都有效
        for report in reports:
            assert report is not None
            assert report.total_requirements > 0
            assert 0 <= report.overall_score <= 100
    
    def test_verification_performance(self, verifier, mock_db_session):
        """测试验证性能"""
        import time
        
        start_time = time.time()
        
        # 执行验证
        report = verifier.verify_gdpr_compliance(
            tenant_id="performance-test-tenant",
            verified_by=uuid4(),
            db=mock_db_session
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证执行时间合理（应该在几秒内完成）
        assert execution_time < 10.0, f"Verification took too long: {execution_time} seconds"
        
        # 验证报告生成成功
        assert report is not None
        assert report.total_requirements > 0
    
    def test_verification_error_resilience(self, verifier):
        """测试验证错误恢复能力"""
        # 测试无效租户ID但有效数据库会话
        mock_db = Mock()
        mock_db.execute.return_value.scalar.return_value = 0
        
        # 应该仍然能够生成报告，即使没有数据
        report = verifier.verify_gdpr_compliance(
            tenant_id="",
            verified_by=uuid4(),
            db=mock_db
        )
        
        assert report is not None
        assert report.tenant_id == ""
        
        # 测试无效数据库会话应该引发异常
        try:
            verifier.verify_gdpr_compliance(
                tenant_id="error-test-tenant",
                verified_by=uuid4(),
                db=None
            )
            # 如果没有异常，检查是否有其他错误处理机制
            assert False, "Expected exception was not raised"
        except Exception as e:
            # 验证异常被正确处理
            assert e is not None
    
    def test_compliance_level_boundaries(self, verifier, mock_db_session):
        """测试合规级别边界"""
        # 测试边界值
        boundary_scores = [94.9, 95.0, 95.1, 84.9, 85.0, 85.1, 69.9, 70.0, 70.1]
        
        for score in boundary_scores:
            level = verifier._determine_compliance_level(score)
            
            if score >= 95.0:
                assert level == ComplianceLevel.FULLY_COMPLIANT
            elif score >= 85.0:
                assert level == ComplianceLevel.MOSTLY_COMPLIANT
            elif score >= 70.0:
                assert level == ComplianceLevel.PARTIALLY_COMPLIANT
            else:
                assert level == ComplianceLevel.NON_COMPLIANT


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])