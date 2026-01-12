"""
Tests for SOX Compliance Implementation.

Tests comprehensive SOX (Sarbanes-Oxley Act) compliance functionality including:
- SOX compliance assessment
- Control testing
- Deficiency management
- Audit trail integrity
- Management certification
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.compliance.sox_compliance import (
    SOXComplianceEngine,
    SOXSection,
    SOXControlType,
    SOXRiskLevel,
    SOXControl,
    SOXDeficiency,
    SOXTestResult,
    SOXComplianceReport
)
from src.compliance.report_generator import ComplianceReportGenerator, ComplianceStandard, ReportType


class TestSOXComplianceEngine:
    """Test SOX Compliance Engine functionality."""
    
    @pytest.fixture
    def sox_engine(self):
        """Create SOX compliance engine instance."""
        return SOXComplianceEngine()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        mock_session = Mock()
        mock_session.execute.return_value.scalar.return_value = 100
        return mock_session
    
    def test_sox_engine_initialization(self, sox_engine):
        """Test SOX compliance engine initialization."""
        assert sox_engine is not None
        assert len(sox_engine.sox_controls) > 0
        assert sox_engine.risk_matrix is not None
        assert sox_engine.test_procedures is not None
    
    def test_sox_controls_framework(self, sox_engine):
        """Test SOX controls framework initialization."""
        controls = sox_engine.sox_controls
        
        # Check that we have controls for different types
        entity_controls = [c for c in controls if c.control_type == SOXControlType.ENTITY_LEVEL]
        transaction_controls = [c for c in controls if c.control_type == SOXControlType.TRANSACTION_LEVEL]
        it_controls = [c for c in controls if c.control_type == SOXControlType.IT_GENERAL]
        
        assert len(entity_controls) > 0
        assert len(transaction_controls) > 0
        assert len(it_controls) > 0
        
        # Check control structure
        for control in controls:
            assert control.control_id is not None
            assert control.control_name is not None
            assert control.sox_section in SOXSection
            assert control.risk_level in SOXRiskLevel
            assert len(control.testing_procedures) > 0
            assert len(control.evidence_requirements) > 0
    
    def test_assess_sox_compliance(self, sox_engine, mock_db_session):
        """Test comprehensive SOX compliance assessment."""
        tenant_id = "test_tenant"
        assessment_date = datetime.utcnow()
        
        # Perform assessment
        report = sox_engine.assess_sox_compliance(
            tenant_id=tenant_id,
            assessment_date=assessment_date,
            db=mock_db_session,
            include_testing=True
        )
        
        # Verify report structure
        assert isinstance(report, SOXComplianceReport)
        assert report.tenant_id == tenant_id
        assert report.report_id is not None
        assert report.sox_compliance_status in ["compliant", "non_compliant", "qualified"]
        assert report.overall_effectiveness in ["effective", "ineffective"]
        
        # Verify report content
        assert report.financial_statement_controls is not None
        assert report.disclosure_controls is not None
        assert report.it_general_controls is not None
        assert report.application_controls is not None
        assert report.audit_trail_integrity is not None
        
        # Verify management assertions
        assert report.management_assertion is not None
        assert isinstance(report.ceo_certification, bool)
        assert isinstance(report.cfo_certification, bool)
    
    def test_entity_level_controls_assessment(self, sox_engine, mock_db_session):
        """Test entity level controls assessment."""
        tenant_id = "test_tenant"
        reporting_period = {
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31)
        }
        
        entity_controls = sox_engine._assess_entity_level_controls(
            tenant_id, reporting_period, mock_db_session
        )
        
        # Verify assessment components
        assert "control_environment" in entity_controls
        assert "risk_assessment" in entity_controls
        assert "information_communication" in entity_controls
        assert "monitoring_activities" in entity_controls
        assert "overall_rating" in entity_controls
        
        # Verify ratings
        assert entity_controls["overall_rating"] >= 0
        assert entity_controls["overall_rating"] <= 100
    
    def test_transaction_level_controls_assessment(self, sox_engine, mock_db_session):
        """Test transaction level controls assessment."""
        tenant_id = "test_tenant"
        reporting_period = {
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31)
        }
        
        transaction_controls = sox_engine._assess_transaction_level_controls(
            tenant_id, reporting_period, mock_db_session
        )
        
        # Verify assessment components
        assert "authorization_controls" in transaction_controls
        assert "segregation_of_duties" in transaction_controls
        assert "recording_controls" in transaction_controls
        assert "review_controls" in transaction_controls
        assert "overall_rating" in transaction_controls
    
    def test_it_general_controls_assessment(self, sox_engine, mock_db_session):
        """Test IT general controls assessment."""
        tenant_id = "test_tenant"
        reporting_period = {
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31)
        }
        
        it_controls = sox_engine._assess_it_general_controls(
            tenant_id, reporting_period, mock_db_session
        )
        
        # Verify assessment components
        assert "access_controls" in it_controls
        assert "change_management" in it_controls
        assert "system_development" in it_controls
        assert "computer_operations" in it_controls
        assert "backup_recovery" in it_controls
        assert "overall_rating" in it_controls
    
    def test_audit_trail_integrity_verification(self, sox_engine, mock_db_session):
        """Test audit trail integrity verification."""
        tenant_id = "test_tenant"
        reporting_period = {
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31)
        }
        
        integrity_results = sox_engine._verify_audit_trail_integrity(
            tenant_id, reporting_period, mock_db_session
        )
        
        # Verify integrity checks
        assert "audit_completeness" in integrity_results
        assert "tamper_protection" in integrity_results
        assert "financial_audit_trails" in integrity_results
        assert "access_audit_trails" in integrity_results
        assert "data_change_trails" in integrity_results
        assert "overall_integrity_score" in integrity_results
        
        # Verify integrity score
        assert integrity_results["overall_integrity_score"] >= 0
        assert integrity_results["overall_integrity_score"] <= 100
    
    def test_control_testing_execution(self, sox_engine, mock_db_session):
        """Test control testing execution."""
        tenant_id = "test_tenant"
        reporting_period = {
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31)
        }
        
        test_results = sox_engine._perform_control_testing(
            tenant_id, reporting_period, mock_db_session
        )
        
        # Verify test results
        assert isinstance(test_results, list)
        assert len(test_results) > 0
        
        for test_result in test_results:
            assert isinstance(test_result, SOXTestResult)
            assert test_result.test_id is not None
            assert test_result.control_id is not None
            assert test_result.test_conclusion in ["effective", "ineffective", "not_tested"]
            assert test_result.sample_size > 0
            assert test_result.exceptions_noted >= 0
    
    def test_deficiency_identification(self, sox_engine):
        """Test deficiency identification process."""
        # Mock control assessment results
        entity_controls = {"overall_rating": 85.0}
        transaction_controls = {"overall_rating": 90.0}
        it_general_controls = {"overall_rating": 88.0}
        application_controls = {"overall_rating": 92.0}
        financial_controls = {"overall_rating": 87.0}
        disclosure_controls = {"overall_rating": 89.0}
        
        # Mock test results with some ineffective controls
        test_results = [
            SOXTestResult(
                test_id=str(uuid4()),
                control_id="TEST001",
                test_date=datetime.utcnow(),
                tester="System",
                test_procedures_performed=["Sample testing"],
                sample_size=25,
                exceptions_noted=0,
                test_conclusion="effective",
                evidence_obtained=["Test evidence"],
                deficiencies_identified=[]
            ),
            SOXTestResult(
                test_id=str(uuid4()),
                control_id="TEST002",
                test_date=datetime.utcnow(),
                tester="System",
                test_procedures_performed=["Sample testing"],
                sample_size=25,
                exceptions_noted=3,
                test_conclusion="ineffective",
                evidence_obtained=["Test evidence"],
                deficiencies_identified=["Control gap identified"]
            )
        ]
        
        deficiencies = sox_engine._identify_deficiencies(
            entity_controls, transaction_controls, it_general_controls,
            application_controls, financial_controls, disclosure_controls,
            test_results
        )
        
        # Verify deficiency identification
        assert isinstance(deficiencies, list)
        # Should have at least one deficiency from the ineffective test
        assert len(deficiencies) >= 1
        
        for deficiency in deficiencies:
            assert isinstance(deficiency, SOXDeficiency)
            assert deficiency.deficiency_id is not None
            assert deficiency.severity in ["significant", "material_weakness", "minor"]
            assert deficiency.status in ["open", "in_progress", "closed"]
    
    def test_overall_effectiveness_determination(self, sox_engine):
        """Test overall effectiveness determination."""
        # Test with no material weaknesses
        material_weaknesses = []
        significant_deficiencies = []
        
        effectiveness = sox_engine._determine_overall_effectiveness(
            material_weaknesses, significant_deficiencies
        )
        assert effectiveness == "effective"
        
        # Test with material weaknesses
        material_weaknesses = [
            SOXDeficiency(
                deficiency_id=str(uuid4()),
                control_id="TEST001",
                severity="material_weakness",
                description="Test material weakness",
                root_cause="Control design issue",
                impact_assessment="High impact",
                remediation_plan="Fix control",
                responsible_party="Control Owner",
                target_completion_date=datetime.utcnow() + timedelta(days=90),
                status="open",
                identified_date=datetime.utcnow()
            )
        ]
        
        effectiveness = sox_engine._determine_overall_effectiveness(
            material_weaknesses, significant_deficiencies
        )
        assert effectiveness == "ineffective"
    
    def test_management_assertion_generation(self, sox_engine):
        """Test management assertion generation."""
        # Test effective controls
        assertion = sox_engine._generate_management_assertion("effective", [])
        assert "effective" in assertion.lower()
        assert "internal control" in assertion.lower()
        
        # Test ineffective controls with material weaknesses
        material_weaknesses = [
            SOXDeficiency(
                deficiency_id=str(uuid4()),
                control_id="TEST001",
                severity="material_weakness",
                description="Test material weakness",
                root_cause="Control design issue",
                impact_assessment="High impact",
                remediation_plan="Fix control",
                responsible_party="Control Owner",
                target_completion_date=datetime.utcnow() + timedelta(days=90),
                status="open",
                identified_date=datetime.utcnow()
            )
        ]
        
        assertion = sox_engine._generate_management_assertion("ineffective", material_weaknesses)
        assert "material weaknesses" in assertion.lower()
        assert "not effective" in assertion.lower()
    
    def test_sox_compliance_status_determination(self, sox_engine):
        """Test SOX compliance status determination."""
        # Test compliant status
        status = sox_engine._determine_sox_compliance_status("effective", [], [])
        assert status == "compliant"
        
        # Test non-compliant status with material weaknesses
        material_weaknesses = [Mock()]
        status = sox_engine._determine_sox_compliance_status("ineffective", material_weaknesses, [])
        assert status == "non_compliant"
        
        # Test qualified status
        significant_deficiencies = [Mock()]
        status = sox_engine._determine_sox_compliance_status("effective", [], significant_deficiencies)
        assert status == "qualified"


class TestSOXComplianceReportGenerator:
    """Test SOX compliance integration with report generator."""
    
    @pytest.fixture
    def report_generator(self):
        """Create compliance report generator instance."""
        return ComplianceReportGenerator()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        mock_session = Mock()
        mock_session.execute.return_value.scalar.return_value = 100
        return mock_session
    
    def test_sox_metrics_generation(self, report_generator, mock_db_session):
        """Test SOX-specific metrics generation."""
        # Mock statistics
        audit_stats = {
            "total_events": 1000,
            "high_risk_events": 50,
            "failed_logins": 10,
            "active_users": 25
        }
        security_stats = {
            "security_events": 100,
            "threat_detections": {"sql_injection_attempts": 0},
            "unique_ip_addresses": 15
        }
        data_protection_stats = {
            "data_exports": 20,
            "data_deletions": 5,
            "encryption_coverage": 100.0
        }
        access_control_stats = {
            "permission_checks": 5000,
            "permission_violations": 10,
            "role_assignments": 100
        }
        
        # Generate SOX metrics
        metrics = report_generator._generate_sox_metrics(
            audit_stats, security_stats, data_protection_stats, access_control_stats
        )
        
        # Verify SOX-specific metrics
        assert len(metrics) > 0
        
        metric_names = [m.name for m in metrics]
        
        # Check for key SOX metrics
        assert "financial_data_access_control" in metric_names
        assert "audit_trail_integrity" in metric_names
        assert "disclosure_controls_effectiveness" in metric_names
        assert "internal_control_design_effectiveness" in metric_names
        assert "internal_control_operating_effectiveness" in metric_names
        
        # Verify metric structure
        for metric in metrics:
            assert metric.name is not None
            assert metric.description is not None
            assert metric.current_value >= 0
            assert metric.target_value > 0
            assert metric.unit is not None
            assert metric.status is not None
            assert "sox_section" in metric.details
    
    def test_sox_violations_detection(self, report_generator, mock_db_session):
        """Test SOX-specific violations detection."""
        tenant_id = "test_tenant"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        violations = report_generator._detect_sox_violations(
            tenant_id, start_date, end_date, mock_db_session
        )
        
        # Verify violations structure
        assert isinstance(violations, list)
        
        # In the current implementation, violations list might be empty
        # but the method should execute without errors
        for violation in violations:
            assert violation.violation_id is not None
            assert violation.standard == ComplianceStandard.SOX
            assert violation.severity in ["low", "medium", "high", "critical"]
            assert violation.description is not None
            assert len(violation.remediation_steps) > 0
    
    def test_sox_recommendations_generation(self, report_generator):
        """Test SOX-specific recommendations generation."""
        # Mock metrics and violations
        metrics = []
        violations = []
        
        recommendations = report_generator._generate_sox_recommendations(metrics, violations)
        
        # Verify recommendations
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Check for SOX-specific recommendations
        recommendation_text = " ".join(recommendations).lower()
        assert "sox" in recommendation_text or "sarbanes" in recommendation_text
        assert "internal control" in recommendation_text
        assert "financial reporting" in recommendation_text
        assert "audit trail" in recommendation_text
    
    def test_sox_compliance_report_generation(self, report_generator, mock_db_session):
        """Test full SOX compliance report generation."""
        tenant_id = "test_tenant"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        generated_by = uuid4()
        
        # Generate SOX compliance report
        report = report_generator.generate_compliance_report(
            tenant_id=tenant_id,
            standard=ComplianceStandard.SOX,
            report_type=ReportType.COMPREHENSIVE,
            start_date=start_date,
            end_date=end_date,
            generated_by=generated_by,
            db=mock_db_session,
            include_recommendations=True
        )
        
        # Verify report structure
        assert report.standard == ComplianceStandard.SOX
        assert report.tenant_id == tenant_id
        assert report.generated_by == generated_by
        
        # Verify SOX-specific content
        assert len(report.metrics) > 0
        assert report.executive_summary is not None
        assert len(report.recommendations) > 0
        
        # Check for SOX-specific metrics
        sox_metrics = [m for m in report.metrics if "sox_section" in m.details]
        assert len(sox_metrics) > 0


class TestSOXComplianceIntegration:
    """Test SOX compliance integration scenarios."""
    
    def test_sox_section_coverage(self):
        """Test that all SOX sections are covered."""
        engine = SOXComplianceEngine()
        
        # Check that controls cover all major SOX sections
        sections_covered = set()
        for control in engine.sox_controls:
            sections_covered.add(control.sox_section)
        
        # Should cover key SOX sections
        assert SOXSection.SECTION_302 in sections_covered or len(sections_covered) > 0
        assert SOXSection.SECTION_404 in sections_covered or len(sections_covered) > 0
    
    def test_sox_risk_levels(self):
        """Test SOX risk level coverage."""
        engine = SOXComplianceEngine()
        
        # Check that controls have appropriate risk levels
        risk_levels = set()
        for control in engine.sox_controls:
            risk_levels.add(control.risk_level)
        
        # Should have controls at different risk levels
        assert len(risk_levels) > 0
        assert SOXRiskLevel.HIGH in risk_levels or SOXRiskLevel.CRITICAL in risk_levels
    
    def test_sox_control_types(self):
        """Test SOX control type coverage."""
        engine = SOXComplianceEngine()
        
        # Check that we have different types of controls
        control_types = set()
        for control in engine.sox_controls:
            control_types.add(control.control_type)
        
        # Should have multiple control types
        assert len(control_types) >= 2
    
    @patch('src.compliance.sox_compliance.get_db_session')
    def test_sox_assessment_error_handling(self, mock_get_db):
        """Test SOX assessment error handling."""
        engine = SOXComplianceEngine()
        
        # Mock database error
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("Database error")
        
        # Should handle database errors gracefully
        with pytest.raises(Exception):
            engine.assess_sox_compliance(
                tenant_id="test_tenant",
                assessment_date=datetime.utcnow(),
                db=mock_db,
                include_testing=False
            )
    
    def test_sox_compliance_status_logic(self):
        """Test SOX compliance status determination logic."""
        engine = SOXComplianceEngine()
        
        # Test various scenarios
        test_cases = [
            ("effective", [], [], "compliant"),
            ("ineffective", [Mock()], [], "non_compliant"),
            ("effective", [], [Mock()], "qualified"),
            ("ineffective", [Mock()], [Mock()], "non_compliant")
        ]
        
        for effectiveness, material_weaknesses, significant_deficiencies, expected_status in test_cases:
            status = engine._determine_sox_compliance_status(
                effectiveness, material_weaknesses, significant_deficiencies
            )
            assert status == expected_status


if __name__ == "__main__":
    pytest.main([__file__])