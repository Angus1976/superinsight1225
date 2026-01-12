"""
Tests for ISO 27001 Compliance Module.

Tests the comprehensive ISO 27001 compliance assessment functionality,
including control evaluation, risk assessment, and reporting.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.compliance.iso27001_compliance import (
    ISO27001ComplianceChecker,
    ISO27001Assessment,
    ISO27001Control,
    ISO27001ControlDomain,
    ISO27001ControlStatus
)


class TestISO27001ComplianceChecker:
    """Test ISO 27001 compliance checker functionality"""
    
    @pytest.fixture
    def compliance_checker(self):
        """Create ISO 27001 compliance checker instance"""
        return ISO27001ComplianceChecker()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        mock_session = Mock(spec=Session)
        
        # Mock query results for audit logs
        mock_session.execute.return_value.scalar.return_value = 100
        
        return mock_session
    
    def test_compliance_checker_initialization(self, compliance_checker):
        """Test compliance checker initialization"""
        assert compliance_checker is not None
        assert hasattr(compliance_checker, 'control_definitions')
        assert hasattr(compliance_checker, 'maturity_levels')
        assert hasattr(compliance_checker, 'risk_criteria')
        
        # Check that control definitions are loaded
        assert len(compliance_checker.control_definitions) > 0
        
        # Check that maturity levels are defined
        assert len(compliance_checker.maturity_levels) == 5
        
    def test_assess_iso27001_compliance(self, compliance_checker, mock_db_session):
        """Test complete ISO 27001 compliance assessment"""
        tenant_id = "test-tenant"
        assessment_date = datetime.utcnow()
        
        assessment = compliance_checker.assess_iso27001_compliance(
            tenant_id=tenant_id,
            assessment_date=assessment_date,
            db=mock_db_session,
            include_risk_assessment=True
        )
        
        # Verify assessment structure
        assert isinstance(assessment, ISO27001Assessment)
        assert assessment.tenant_id == tenant_id
        assert assessment.assessment_date == assessment_date
        assert assessment.overall_maturity_level >= 1
        assert assessment.overall_maturity_level <= 5
        assert 0 <= assessment.overall_compliance_score <= 100
        
        # Verify control assessments
        assert len(assessment.control_assessments) > 0
        assert all(isinstance(control, ISO27001Control) for control in assessment.control_assessments)
        
        # Verify domain scores
        assert isinstance(assessment.domain_scores, dict)
        assert len(assessment.domain_scores) > 0
        
        # Verify risk assessment components
        assert isinstance(assessment.identified_risks, list)
        assert isinstance(assessment.risk_treatment_plan, list)
        assert isinstance(assessment.priority_recommendations, list)
        assert isinstance(assessment.implementation_roadmap, list)
    
    def test_assess_all_controls(self, compliance_checker, mock_db_session):
        """Test assessment of all control domains"""
        tenant_id = "test-tenant"
        assessment_date = datetime.utcnow()
        
        control_assessments = compliance_checker._assess_all_controls(
            tenant_id, assessment_date, mock_db_session
        )
        
        # Verify controls from multiple domains are assessed
        assert len(control_assessments) > 0
        
        # Check that we have controls from different domains
        domains_represented = set(control.domain for control in control_assessments)
        assert len(domains_represented) > 1
        
        # Verify control structure
        for control in control_assessments:
            assert isinstance(control, ISO27001Control)
            assert control.control_id is not None
            assert control.domain in ISO27001ControlDomain
            assert control.status in ISO27001ControlStatus
            assert 0 <= control.effectiveness_score <= 100
            assert isinstance(control.evidence, list)
            assert isinstance(control.gaps, list)
            assert isinstance(control.recommendations, list)
    
    def test_assess_information_security_policies(self, compliance_checker, mock_db_session):
        """Test A.5 Information Security Policies assessment"""
        tenant_id = "test-tenant"
        assessment_date = datetime.utcnow()
        
        controls = compliance_checker._assess_information_security_policies(
            tenant_id, assessment_date, mock_db_session
        )
        
        assert len(controls) > 0
        
        # Check A.5.1 control
        policy_control = next((c for c in controls if c.control_id == "A.5.1"), None)
        assert policy_control is not None
        assert policy_control.domain == ISO27001ControlDomain.INFORMATION_SECURITY_POLICIES
        assert policy_control.title == "Information Security Policy"
        assert policy_control.status in ISO27001ControlStatus
    
    def test_assess_access_control(self, compliance_checker, mock_db_session):
        """Test A.9 Access Control assessment"""
        tenant_id = "test-tenant"
        assessment_date = datetime.utcnow()
        
        controls = compliance_checker._assess_access_control(
            tenant_id, assessment_date, mock_db_session
        )
        
        assert len(controls) > 0
        
        # Check A.9.2 control
        user_access_control = next((c for c in controls if c.control_id == "A.9.2"), None)
        assert user_access_control is not None
        assert user_access_control.domain == ISO27001ControlDomain.ACCESS_CONTROL
        assert user_access_control.title == "User Access Management"
    
    def test_assess_operations_security(self, compliance_checker, mock_db_session):
        """Test A.12 Operations Security assessment"""
        tenant_id = "test-tenant"
        assessment_date = datetime.utcnow()
        
        controls = compliance_checker._assess_operations_security(
            tenant_id, assessment_date, mock_db_session
        )
        
        assert len(controls) > 0
        
        # Check A.12.4 control
        logging_control = next((c for c in controls if c.control_id == "A.12.4"), None)
        assert logging_control is not None
        assert logging_control.domain == ISO27001ControlDomain.OPERATIONS_SECURITY
        assert logging_control.title == "Logging and Monitoring"
    
    def test_assess_incident_management(self, compliance_checker, mock_db_session):
        """Test A.16 Incident Management assessment"""
        tenant_id = "test-tenant"
        assessment_date = datetime.utcnow()
        
        controls = compliance_checker._assess_incident_management(
            tenant_id, assessment_date, mock_db_session
        )
        
        assert len(controls) > 0
        
        # Check A.16.1 control
        incident_control = next((c for c in controls if c.control_id == "A.16.1"), None)
        assert incident_control is not None
        assert incident_control.domain == ISO27001ControlDomain.INFORMATION_SECURITY_INCIDENT_MANAGEMENT
        assert incident_control.title == "Information Security Incident Management"
    
    def test_calculate_domain_scores(self, compliance_checker):
        """Test domain score calculation"""
        # Create sample control assessments
        control_assessments = [
            ISO27001Control(
                control_id="A.5.1",
                domain=ISO27001ControlDomain.INFORMATION_SECURITY_POLICIES,
                title="Test Control 1",
                description="Test",
                implementation_guidance="Test",
                status=ISO27001ControlStatus.IMPLEMENTED,
                effectiveness_score=85.0,
                evidence=[],
                gaps=[],
                recommendations=[]
            ),
            ISO27001Control(
                control_id="A.9.1",
                domain=ISO27001ControlDomain.ACCESS_CONTROL,
                title="Test Control 2",
                description="Test",
                implementation_guidance="Test",
                status=ISO27001ControlStatus.PARTIALLY_IMPLEMENTED,
                effectiveness_score=65.0,
                evidence=[],
                gaps=[],
                recommendations=[]
            )
        ]
        
        domain_scores = compliance_checker._calculate_domain_scores(control_assessments)
        
        assert isinstance(domain_scores, dict)
        assert "A.5" in domain_scores
        assert "A.9" in domain_scores
        assert domain_scores["A.5"] == 85.0
        assert domain_scores["A.9"] == 65.0
    
    def test_calculate_overall_compliance_score(self, compliance_checker):
        """Test overall compliance score calculation"""
        domain_scores = {
            "A.5": 85.0,
            "A.9": 75.0,
            "A.12": 80.0,
            "A.16": 70.0
        }
        
        overall_score = compliance_checker._calculate_overall_compliance_score(domain_scores)
        
        assert isinstance(overall_score, float)
        assert 0 <= overall_score <= 100
        assert overall_score == 77.5  # Average of domain scores
    
    def test_assess_maturity_level(self, compliance_checker):
        """Test maturity level assessment"""
        # Test different score ranges
        test_cases = [
            ({"A.5": 95.0, "A.9": 92.0}, 5),  # Optimizing
            ({"A.5": 85.0, "A.9": 82.0}, 4),  # Managed
            ({"A.5": 75.0, "A.9": 72.0}, 3),  # Defined
            ({"A.5": 55.0, "A.9": 52.0}, 2),  # Repeatable
            ({"A.5": 35.0, "A.9": 32.0}, 1),  # Initial
        ]
        
        for domain_scores, expected_level in test_cases:
            maturity_level = compliance_checker._assess_maturity_level([], domain_scores)
            assert maturity_level == expected_level
    
    def test_identify_security_risks(self, compliance_checker, mock_db_session):
        """Test security risk identification"""
        tenant_id = "test-tenant"
        
        # Create control assessments with gaps
        control_assessments = [
            ISO27001Control(
                control_id="A.5.1",
                domain=ISO27001ControlDomain.INFORMATION_SECURITY_POLICIES,
                title="Information Security Policy",
                description="Test",
                implementation_guidance="Test",
                status=ISO27001ControlStatus.NOT_IMPLEMENTED,
                effectiveness_score=30.0,
                evidence=[],
                gaps=["No policy document"],
                recommendations=["Create policy"]
            ),
            ISO27001Control(
                control_id="A.9.2",
                domain=ISO27001ControlDomain.ACCESS_CONTROL,
                title="User Access Management",
                description="Test",
                implementation_guidance="Test",
                status=ISO27001ControlStatus.PARTIALLY_IMPLEMENTED,
                effectiveness_score=60.0,
                evidence=["Some processes"],
                gaps=["Incomplete procedures"],
                recommendations=["Enhance procedures"]
            )
        ]
        
        risks = compliance_checker._identify_security_risks(
            tenant_id, control_assessments, mock_db_session
        )
        
        assert isinstance(risks, list)
        assert len(risks) == 2  # One risk per control with gaps
        
        # Verify risk structure
        for risk in risks:
            assert "risk_id" in risk
            assert "title" in risk
            assert "description" in risk
            assert "risk_level" in risk
            assert "control_reference" in risk
    
    def test_develop_risk_treatment_plan(self, compliance_checker):
        """Test risk treatment plan development"""
        identified_risks = [
            {
                "risk_id": "risk-1",
                "title": "High Risk",
                "risk_level": "High",
                "control_reference": "A.5.1"
            },
            {
                "risk_id": "risk-2", 
                "title": "Medium Risk",
                "risk_level": "Medium",
                "control_reference": "A.9.2"
            }
        ]
        
        treatment_plan = compliance_checker._develop_risk_treatment_plan(identified_risks)
        
        assert isinstance(treatment_plan, list)
        assert len(treatment_plan) == 2
        
        # Verify treatment plan structure
        for plan_item in treatment_plan:
            assert "risk_id" in plan_item
            assert "treatment_option" in plan_item
            assert "action_plan" in plan_item
            assert "responsible_party" in plan_item
            assert "target_completion" in plan_item
        
        # High risk should be mitigated, medium risk might be accepted
        high_risk_plan = next(p for p in treatment_plan if p["risk_id"] == "risk-1")
        assert high_risk_plan["treatment_option"] == "Mitigate"
    
    def test_generate_priority_recommendations(self, compliance_checker):
        """Test priority recommendations generation"""
        control_assessments = [
            ISO27001Control(
                control_id="A.5.1",
                domain=ISO27001ControlDomain.INFORMATION_SECURITY_POLICIES,
                title="Critical Control",
                description="Test",
                implementation_guidance="Test",
                status=ISO27001ControlStatus.NOT_IMPLEMENTED,
                effectiveness_score=30.0,  # Critical
                evidence=[],
                gaps=[],
                recommendations=[]
            )
        ]
        
        domain_scores = {
            "A.5": 40.0,  # Low score
            "A.9": 85.0   # High score
        }
        
        recommendations = compliance_checker._generate_priority_recommendations(
            control_assessments, domain_scores
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should include domain improvement and critical control recommendations
        domain_rec = any("A.5" in rec for rec in recommendations)
        control_rec = any("A.5.1" in rec for rec in recommendations)
        assert domain_rec or control_rec
    
    def test_create_implementation_roadmap(self, compliance_checker):
        """Test implementation roadmap creation"""
        control_assessments = [
            ISO27001Control(
                control_id="A.5.1",
                domain=ISO27001ControlDomain.INFORMATION_SECURITY_POLICIES,
                title="Critical Control",
                description="Test",
                implementation_guidance="Test",
                status=ISO27001ControlStatus.NOT_IMPLEMENTED,
                effectiveness_score=30.0,  # Critical - Phase 1
                evidence=[],
                gaps=[],
                recommendations=[]
            ),
            ISO27001Control(
                control_id="A.9.2",
                domain=ISO27001ControlDomain.ACCESS_CONTROL,
                title="Important Control",
                description="Test",
                implementation_guidance="Test",
                status=ISO27001ControlStatus.PARTIALLY_IMPLEMENTED,
                effectiveness_score=65.0,  # Important - Phase 2
                evidence=[],
                gaps=[],
                recommendations=[]
            )
        ]
        
        identified_risks = []
        
        roadmap = compliance_checker._create_implementation_roadmap(
            control_assessments, identified_risks
        )
        
        assert isinstance(roadmap, list)
        assert len(roadmap) > 0
        
        # Verify roadmap structure
        for phase in roadmap:
            assert "phase" in phase
            assert "duration" in phase
            assert "priority" in phase
            assert "controls" in phase
            assert "objectives" in phase
            assert "success_criteria" in phase
        
        # Critical controls should be in Phase 1
        phase1 = next((p for p in roadmap if "Phase 1" in p["phase"]), None)
        if phase1:
            assert "A.5.1" in phase1["controls"]
    
    def test_control_assessment_helper_methods(self, compliance_checker, mock_db_session):
        """Test control assessment helper methods"""
        tenant_id = "test-tenant"
        
        # Test various helper methods
        assert isinstance(compliance_checker._check_security_policy_exists(tenant_id, mock_db_session), bool)
        assert isinstance(compliance_checker._check_policy_review_process(tenant_id, mock_db_session), bool)
        assert isinstance(compliance_checker._check_user_provisioning_process(tenant_id, mock_db_session), bool)
        assert isinstance(compliance_checker._check_access_rights_review(tenant_id, mock_db_session), bool)
        assert isinstance(compliance_checker._check_logging_policy(tenant_id, mock_db_session), bool)
        assert isinstance(compliance_checker._check_incident_response_procedures(tenant_id, mock_db_session), bool)
    
    def test_initialization_methods(self, compliance_checker):
        """Test initialization methods"""
        # Test control definitions initialization
        control_definitions = compliance_checker._initialize_control_definitions()
        assert isinstance(control_definitions, dict)
        assert len(control_definitions) > 0
        
        # Test maturity levels initialization
        maturity_levels = compliance_checker._initialize_maturity_levels()
        assert isinstance(maturity_levels, dict)
        assert len(maturity_levels) == 5
        assert all(isinstance(k, int) and isinstance(v, str) for k, v in maturity_levels.items())
        
        # Test risk criteria initialization
        risk_criteria = compliance_checker._initialize_risk_criteria()
        assert isinstance(risk_criteria, dict)
        assert "likelihood_levels" in risk_criteria
        assert "impact_levels" in risk_criteria
        assert "risk_matrix" in risk_criteria


class TestISO27001Integration:
    """Test ISO 27001 integration with existing systems"""
    
    def test_compliance_report_generator_integration(self):
        """Test integration with compliance report generator"""
        from src.compliance.report_generator import ComplianceReportGenerator, ComplianceStandard
        
        generator = ComplianceReportGenerator()
        
        # Verify ISO 27001 is supported
        assert ComplianceStandard.ISO_27001 in generator.compliance_standards
        
        # Test that ISO 27001 methods exist
        assert hasattr(generator, '_generate_iso27001_metrics')
        assert hasattr(generator, '_detect_iso27001_violations')
    
    @patch('src.compliance.iso27001_compliance.get_db_session')
    def test_metrics_generation_integration(self, mock_get_db):
        """Test ISO 27001 metrics generation integration"""
        from src.compliance.report_generator import ComplianceReportGenerator
        
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.execute.return_value.scalar.return_value = 100
        
        generator = ComplianceReportGenerator()
        
        # Test metrics generation
        audit_stats = {"total_events": 1000, "audit_coverage": 95.0}
        security_stats = {"response_times": {"average_hours": 12.0}}
        data_protection_stats = {"encryption_coverage": 100.0}
        access_control_stats = {"permission_checks": 500, "permission_violations": 5}
        
        metrics = generator._generate_iso27001_metrics(
            audit_stats, security_stats, data_protection_stats, access_control_stats
        )
        
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        
        # Verify metric structure
        for metric in metrics:
            assert hasattr(metric, 'name')
            assert hasattr(metric, 'current_value')
            assert hasattr(metric, 'target_value')
            assert hasattr(metric, 'status')


if __name__ == "__main__":
    pytest.main([__file__])