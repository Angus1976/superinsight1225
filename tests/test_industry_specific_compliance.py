"""
Tests for Industry-Specific Compliance Module.

Tests HIPAA, PCI-DSS, PIPL, and other industry-specific compliance checkers.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.compliance.industry_specific_compliance import (
    IndustryComplianceManager,
    IndustryType,
    ComplianceFramework,
    ComplianceStatus,
    RiskLevel,
    HIPAAComplianceChecker,
    PCIDSSComplianceChecker,
    PIPLComplianceChecker,
    assess_industry_compliance,
    get_applicable_frameworks
)


class TestHIPAAComplianceChecker:
    """HIPAA合规检查器测试"""
    
    def test_hipaa_checker_initialization(self):
        """测试HIPAA检查器初始化"""
        checker = HIPAAComplianceChecker()
        assert checker is not None
        assert len(checker.requirements) > 0
    
    def test_hipaa_compliance_assessment(self):
        """测试HIPAA合规评估"""
        checker = HIPAAComplianceChecker()
        
        # 创建模拟数据库会话
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 100
        
        assessment = checker.assess_hipaa_compliance(
            tenant_id="test-tenant",
            assessment_date=datetime.utcnow(),
            db=mock_db
        )
        
        assert assessment is not None
        assert "framework" in assessment
        assert assessment["framework"] == "hipaa"
        assert "overall_score" in assessment
        assert 0 <= assessment["overall_score"] <= 100
        assert "status" in assessment
        assert "privacy_rule" in assessment
        assert "security_rule" in assessment
        assert "breach_notification_rule" in assessment
    
    def test_hipaa_privacy_rule_assessment(self):
        """测试HIPAA隐私规则评估"""
        checker = HIPAAComplianceChecker()
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 50
        
        result = checker._assess_privacy_rule("test-tenant", mock_db)
        
        assert result is not None
        assert "category" in result
        assert result["category"] == "Privacy Rule"
        assert "controls" in result
        assert len(result["controls"]) > 0
        assert "score" in result
    
    def test_hipaa_security_rule_assessment(self):
        """测试HIPAA安全规则评估"""
        checker = HIPAAComplianceChecker()
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 100
        
        result = checker._assess_security_rule("test-tenant", mock_db)
        
        assert result is not None
        assert "category" in result
        assert result["category"] == "Security Rule"
        assert "controls" in result
        assert "score" in result
    
    def test_hipaa_breach_notification_assessment(self):
        """测试HIPAA违规通知规则评估"""
        checker = HIPAAComplianceChecker()
        mock_db = MagicMock()
        
        result = checker._assess_breach_notification_rule("test-tenant", mock_db)
        
        assert result is not None
        assert "category" in result
        assert result["category"] == "Breach Notification Rule"
        assert "controls" in result


class TestPCIDSSComplianceChecker:
    """PCI-DSS合规检查器测试"""
    
    def test_pci_checker_initialization(self):
        """测试PCI-DSS检查器初始化"""
        checker = PCIDSSComplianceChecker()
        assert checker is not None
        assert len(checker.requirements) > 0
    
    def test_pci_compliance_assessment(self):
        """测试PCI-DSS合规评估"""
        checker = PCIDSSComplianceChecker()
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 100
        
        assessment = checker.assess_pci_compliance(
            tenant_id="test-tenant",
            assessment_date=datetime.utcnow(),
            db=mock_db
        )
        
        assert assessment is not None
        assert "framework" in assessment
        assert assessment["framework"] == "pci_dss"
        assert "overall_score" in assessment
        assert "network_security" in assessment
        assert "cardholder_data_protection" in assessment
        assert "vulnerability_management" in assessment
        assert "access_control" in assessment
        assert "monitoring_testing" in assessment
        assert "security_policy" in assessment
    
    def test_pci_network_security_assessment(self):
        """测试PCI-DSS网络安全评估"""
        checker = PCIDSSComplianceChecker()
        mock_db = MagicMock()
        
        result = checker._assess_network_security("test-tenant", mock_db)
        
        assert result is not None
        assert "category" in result
        assert "Build and Maintain a Secure Network" in result["category"]
        assert "controls" in result
        assert len(result["controls"]) == 2  # Requirements 1-2
    
    def test_pci_access_control_assessment(self):
        """测试PCI-DSS访问控制评估"""
        checker = PCIDSSComplianceChecker()
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 50
        
        result = checker._assess_access_control_measures("test-tenant", mock_db)
        
        assert result is not None
        assert "category" in result
        assert "controls" in result
        assert len(result["controls"]) == 3  # Requirements 7-9


class TestPIPLComplianceChecker:
    """PIPL合规检查器测试"""
    
    def test_pipl_checker_initialization(self):
        """测试PIPL检查器初始化"""
        checker = PIPLComplianceChecker()
        assert checker is not None
        assert len(checker.requirements) > 0
    
    def test_pipl_compliance_assessment(self):
        """测试PIPL合规评估"""
        checker = PIPLComplianceChecker()
        mock_db = MagicMock()
        
        assessment = checker.assess_pipl_compliance(
            tenant_id="test-tenant",
            assessment_date=datetime.utcnow(),
            db=mock_db
        )
        
        assert assessment is not None
        assert "framework" in assessment
        assert assessment["framework"] == "pipl"
        assert "overall_score" in assessment
        assert "processing_rules" in assessment
        assert "sensitive_data_handling" in assessment
        assert "cross_border_transfer" in assessment
        assert "subject_rights" in assessment
        assert "processor_obligations" in assessment
    
    def test_pipl_processing_rules_assessment(self):
        """测试PIPL个人信息处理规则评估"""
        checker = PIPLComplianceChecker()
        mock_db = MagicMock()
        
        result = checker._assess_processing_rules("test-tenant", mock_db)
        
        assert result is not None
        assert "category" in result
        assert result["category"] == "个人信息处理规则"
        assert "controls" in result
        assert len(result["controls"]) == 4
    
    def test_pipl_subject_rights_assessment(self):
        """测试PIPL个人信息主体权利评估"""
        checker = PIPLComplianceChecker()
        mock_db = MagicMock()
        
        result = checker._assess_subject_rights("test-tenant", mock_db)
        
        assert result is not None
        assert "category" in result
        assert result["category"] == "个人信息主体权利"
        assert "controls" in result
        assert len(result["controls"]) == 5  # 知情权、查阅权、更正权、删除权、可携带权


class TestIndustryComplianceManager:
    """行业合规管理器测试"""
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = IndustryComplianceManager()
        assert manager is not None
        assert manager.hipaa_checker is not None
        assert manager.pci_checker is not None
        assert manager.pipl_checker is not None
    
    def test_industry_frameworks_mapping(self):
        """测试行业到框架的映射"""
        manager = IndustryComplianceManager()
        
        # 医疗保健行业应该映射到HIPAA
        healthcare_frameworks = manager.industry_frameworks.get(IndustryType.HEALTHCARE)
        assert ComplianceFramework.HIPAA in healthcare_frameworks
        
        # 金融服务行业应该映射到PCI-DSS
        financial_frameworks = manager.industry_frameworks.get(IndustryType.FINANCIAL_SERVICES)
        assert ComplianceFramework.PCI_DSS in financial_frameworks
    
    def test_assess_industry_compliance(self):
        """测试行业合规评估"""
        manager = IndustryComplianceManager()
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 100
        
        assessment = manager.assess_industry_compliance(
            tenant_id="test-tenant",
            industry_type=IndustryType.HEALTHCARE,
            assessment_date=datetime.utcnow(),
            db=mock_db
        )
        
        assert assessment is not None
        assert assessment.tenant_id == "test-tenant"
        assert assessment.industry_type == IndustryType.HEALTHCARE
        assert assessment.overall_compliance_score >= 0
        assert assessment.overall_status in ComplianceStatus
    
    def test_get_applicable_frameworks_healthcare(self):
        """测试获取医疗保健行业适用框架"""
        manager = IndustryComplianceManager()
        
        frameworks = manager.get_applicable_frameworks(
            industry_type=IndustryType.HEALTHCARE
        )
        
        assert ComplianceFramework.HIPAA in frameworks
    
    def test_get_applicable_frameworks_with_data_types(self):
        """测试根据数据类型获取适用框架"""
        manager = IndustryComplianceManager()
        
        # 包含健康数据应该添加HIPAA
        frameworks = manager.get_applicable_frameworks(
            industry_type=IndustryType.TECHNOLOGY,
            data_types=["health_data"]
        )
        assert ComplianceFramework.HIPAA in frameworks
        
        # 包含支付卡数据应该添加PCI-DSS
        frameworks = manager.get_applicable_frameworks(
            industry_type=IndustryType.TECHNOLOGY,
            data_types=["payment_card"]
        )
        assert ComplianceFramework.PCI_DSS in frameworks
    
    def test_get_applicable_frameworks_with_regions(self):
        """测试根据地区获取适用框架"""
        manager = IndustryComplianceManager()
        
        # 中国地区应该添加PIPL
        frameworks = manager.get_applicable_frameworks(
            industry_type=IndustryType.TECHNOLOGY,
            geographic_regions=["china"]
        )
        assert ComplianceFramework.PIPL in frameworks
    
    def test_generate_compliance_summary(self):
        """测试生成合规摘要"""
        manager = IndustryComplianceManager()
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 100
        
        assessment = manager.assess_industry_compliance(
            tenant_id="test-tenant",
            industry_type=IndustryType.HEALTHCARE,
            assessment_date=datetime.utcnow(),
            db=mock_db
        )
        
        summary = manager.generate_compliance_summary(assessment)
        
        assert summary is not None
        assert "assessment_id" in summary
        assert "tenant_id" in summary
        assert "overall_score" in summary
        assert "overall_status" in summary
        assert "frameworks_assessed" in summary
    
    def test_identify_risks(self):
        """测试风险识别"""
        manager = IndustryComplianceManager()
        
        # 创建低分评估
        framework_assessments = {
            "hipaa": {"overall_score": 65.0},
            "pci_dss": {"overall_score": 85.0}
        }
        
        risks = manager._identify_risks(framework_assessments)
        
        assert len(risks) > 0
        # 低于80分的框架应该被识别为风险
        hipaa_risk = next((r for r in risks if r["framework"] == "hipaa"), None)
        assert hipaa_risk is not None
        assert hipaa_risk["risk_level"] == RiskLevel.HIGH.value
    
    def test_generate_risk_mitigation_plan(self):
        """测试风险缓解计划生成"""
        manager = IndustryComplianceManager()
        
        risks = [
            {
                "risk_id": str(uuid4()),
                "framework": "hipaa",
                "risk_level": RiskLevel.HIGH.value,
                "description": "Test risk"
            }
        ]
        
        plan = manager._generate_risk_mitigation_plan(risks)
        
        assert len(plan) == 1
        assert "mitigation_action" in plan[0]
        assert "priority" in plan[0]
    
    def test_create_implementation_roadmap(self):
        """测试实施路线图创建"""
        manager = IndustryComplianceManager()
        
        roadmap = manager._create_implementation_roadmap({}, [])
        
        assert len(roadmap) == 3  # 短期、中期、长期
        assert roadmap[0]["phase"] == "Short-term"
        assert roadmap[1]["phase"] == "Medium-term"
        assert roadmap[2]["phase"] == "Long-term"


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_assess_industry_compliance_function(self):
        """测试便捷评估函数"""
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar.return_value = 100
        
        assessment = assess_industry_compliance(
            tenant_id="test-tenant",
            industry_type=IndustryType.HEALTHCARE,
            db=mock_db
        )
        
        assert assessment is not None
        assert assessment.industry_type == IndustryType.HEALTHCARE
    
    def test_get_applicable_frameworks_function(self):
        """测试便捷获取框架函数"""
        frameworks = get_applicable_frameworks(
            industry_type=IndustryType.HEALTHCARE
        )
        
        assert ComplianceFramework.HIPAA in frameworks


class TestComplianceStatus:
    """合规状态测试"""
    
    def test_status_determination_compliant(self):
        """测试合规状态判定 - 合规"""
        checker = HIPAAComplianceChecker()
        status = checker._determine_status(95.0)
        assert status == ComplianceStatus.COMPLIANT.value
    
    def test_status_determination_partially_compliant(self):
        """测试合规状态判定 - 部分合规"""
        checker = HIPAAComplianceChecker()
        status = checker._determine_status(75.0)
        assert status == ComplianceStatus.PARTIALLY_COMPLIANT.value
    
    def test_status_determination_non_compliant(self):
        """测试合规状态判定 - 不合规"""
        checker = HIPAAComplianceChecker()
        status = checker._determine_status(50.0)
        assert status == ComplianceStatus.NON_COMPLIANT.value


class TestIndustryTypes:
    """行业类型测试"""
    
    def test_all_industry_types_have_frameworks(self):
        """测试所有行业类型都有对应框架"""
        manager = IndustryComplianceManager()
        
        for industry in IndustryType:
            frameworks = manager.industry_frameworks.get(industry, [])
            # 每个行业至少应该有一个框架
            assert len(frameworks) >= 1, f"Industry {industry.value} has no frameworks"


class TestComplianceFrameworks:
    """合规框架测试"""
    
    def test_framework_enum_values(self):
        """测试框架枚举值"""
        assert ComplianceFramework.HIPAA.value == "hipaa"
        assert ComplianceFramework.PCI_DSS.value == "pci_dss"
        assert ComplianceFramework.PIPL.value == "pipl"
        assert ComplianceFramework.FERPA.value == "ferpa"
        assert ComplianceFramework.GLBA.value == "glba"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
