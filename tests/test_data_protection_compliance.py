"""
Tests for Data Protection Compliance System.

Comprehensive test suite for the data protection regulation compliance
assessment and reporting functionality.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.compliance.data_protection_compliance import (
    DataProtectionComplianceEngine,
    DataProtectionRegulation,
    DataProtectionPrinciple,
    DataSubjectRight,
    ComplianceStatus,
    RegulationRequirement,
    ComplianceAssessment,
    DataProtectionComplianceReport
)


class TestDataProtectionComplianceEngine:
    """Test suite for DataProtectionComplianceEngine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = DataProtectionComplianceEngine()
        self.mock_db = Mock(spec=Session)
        self.tenant_id = "test_tenant_123"
        self.assessed_by = uuid4()
        self.assessment_date = datetime.utcnow()
    
    def test_engine_initialization(self):
        """Test compliance engine initialization"""
        assert self.engine is not None
        assert hasattr(self.engine, 'regulation_requirements')
        assert hasattr(self.engine, 'regulation_mappings')
        assert hasattr(self.engine, 'compliance_thresholds')
        
        # Check that requirements are loaded for key regulations
        assert DataProtectionRegulation.GDPR in self.engine.regulation_requirements
        assert DataProtectionRegulation.CCPA in self.engine.regulation_requirements
        assert len(self.engine.regulation_requirements[DataProtectionRegulation.GDPR]) > 0
    
    def test_assess_data_protection_compliance_single_regulation(self):
        """Test compliance assessment for single regulation"""
        regulations = [DataProtectionRegulation.GDPR]
        
        # Mock database queries
        self.mock_db.execute.return_value.scalar.return_value = 10
        
        report = self.engine.assess_data_protection_compliance(
            tenant_id=self.tenant_id,
            regulations=regulations,
            assessment_date=self.assessment_date,
            assessed_by=self.assessed_by,
            db=self.mock_db
        )
        
        assert isinstance(report, DataProtectionComplianceReport)
        assert report.tenant_id == self.tenant_id
        assert report.regulations_assessed == regulations
        assert report.overall_compliance_score >= 0
        assert report.overall_compliance_score <= 100
        assert isinstance(report.overall_status, ComplianceStatus)
        assert len(report.regulation_assessments) == 1
        assert DataProtectionRegulation.GDPR.value in report.regulation_assessments
    
    def test_assess_data_protection_compliance_multiple_regulations(self):
        """Test compliance assessment for multiple regulations"""
        regulations = [
            DataProtectionRegulation.GDPR,
            DataProtectionRegulation.CCPA,
            DataProtectionRegulation.PIPEDA
        ]
        
        # Mock database queries
        self.mock_db.execute.return_value.scalar.return_value = 15
        
        report = self.engine.assess_data_protection_compliance(
            tenant_id=self.tenant_id,
            regulations=regulations,
            assessment_date=self.assessment_date,
            assessed_by=self.assessed_by,
            db=self.mock_db
        )
        
        assert len(report.regulations_assessed) == 3
        assert len(report.regulation_assessments) == 3
        assert len(report.regulation_scores) == 3
        
        # Check that all regulations are assessed
        for regulation in regulations:
            assert regulation.value in report.regulation_assessments
            assert regulation.value in report.regulation_scores
    
    def test_assess_regulation_compliance(self):
        """Test assessment of specific regulation compliance"""
        regulation = DataProtectionRegulation.GDPR
        
        # Mock database queries
        self.mock_db.execute.return_value.scalar.return_value = 5
        
        assessments = self.engine._assess_regulation_compliance(
            regulation=regulation,
            tenant_id=self.tenant_id,
            assessment_date=self.assessment_date,
            db=self.mock_db
        )
        
        assert isinstance(assessments, list)
        assert len(assessments) > 0
        
        for assessment in assessments:
            assert isinstance(assessment, ComplianceAssessment)
            assert assessment.regulation == regulation
            assert assessment.compliance_score >= 0
            assert assessment.compliance_score <= 100
            assert isinstance(assessment.status, ComplianceStatus)
    
    def test_assess_single_requirement_lawfulness(self):
        """Test assessment of lawfulness principle requirement"""
        requirement = RegulationRequirement(
            regulation=DataProtectionRegulation.GDPR,
            requirement_id="TEST-LAWFULNESS",
            title="Test Lawfulness Requirement",
            description="Test requirement for lawfulness principle",
            principle=DataProtectionPrinciple.LAWFULNESS,
            mandatory=True,
            applicable_rights=[],
            verification_criteria=["Test criteria"],
            penalty_severity="high"
        )
        
        # Mock database queries
        self.mock_db.execute.return_value.scalar.return_value = 8
        
        assessment = self.engine._assess_single_requirement(
            requirement=requirement,
            tenant_id=self.tenant_id,
            assessment_date=self.assessment_date,
            db=self.mock_db
        )
        
        assert isinstance(assessment, ComplianceAssessment)
        assert assessment.requirement_id == "TEST-LAWFULNESS"
        assert assessment.regulation == DataProtectionRegulation.GDPR
        assert assessment.compliance_score > 0
        assert len(assessment.evidence_found) >= 0
        assert len(assessment.recommendations) >= 0
    
    def test_assess_single_requirement_transparency(self):
        """Test assessment of transparency principle requirement"""
        requirement = RegulationRequirement(
            regulation=DataProtectionRegulation.GDPR,
            requirement_id="TEST-TRANSPARENCY",
            title="Test Transparency Requirement",
            description="Test requirement for transparency principle",
            principle=DataProtectionPrinciple.TRANSPARENCY,
            mandatory=True,
            applicable_rights=[],
            verification_criteria=["Test criteria"],
            penalty_severity="medium"
        )
        
        assessment = self.engine._assess_single_requirement(
            requirement=requirement,
            tenant_id=self.tenant_id,
            assessment_date=self.assessment_date,
            db=self.mock_db
        )
        
        assert isinstance(assessment, ComplianceAssessment)
        assert assessment.requirement_id == "TEST-TRANSPARENCY"
        assert assessment.compliance_score > 0
    
    def test_assess_lawfulness_principle(self):
        """Test lawfulness principle assessment"""
        requirement = Mock()
        requirement.regulation = DataProtectionRegulation.GDPR
        
        # Mock database queries
        self.mock_db.execute.return_value.scalar.return_value = 12
        
        result = self.engine._assess_lawfulness_principle(
            requirement=requirement,
            tenant_id=self.tenant_id,
            db=self.mock_db
        )
        
        assert isinstance(result, dict)
        assert "compliance_score" in result
        assert "evidence_found" in result
        assert "gaps_identified" in result
        assert "recommendations" in result
        assert result["compliance_score"] >= 0
        assert result["compliance_score"] <= 100
    
    def test_assess_transparency_principle(self):
        """Test transparency principle assessment"""
        requirement = Mock()
        requirement.regulation = DataProtectionRegulation.GDPR
        
        result = self.engine._assess_transparency_principle(
            requirement=requirement,
            tenant_id=self.tenant_id,
            db=self.mock_db
        )
        
        assert isinstance(result, dict)
        assert "compliance_score" in result
        assert result["compliance_score"] >= 0
        assert result["compliance_score"] <= 100
    
    def test_assess_data_subject_rights(self):
        """Test data subject rights assessment"""
        regulations = [DataProtectionRegulation.GDPR, DataProtectionRegulation.CCPA]
        
        # Mock database queries
        self.mock_db.execute.return_value.scalar.return_value = 3
        
        rights_implementation = self.engine._assess_data_subject_rights(
            tenant_id=self.tenant_id,
            regulations=regulations,
            db=self.mock_db
        )
        
        assert isinstance(rights_implementation, dict)
        
        # Check that all data subject rights are assessed
        for right in DataSubjectRight:
            assert right.value in rights_implementation
            right_status = rights_implementation[right.value]
            assert "implemented" in right_status
            assert "effectiveness_score" in right_status
            assert "applicable_regulations" in right_status
            assert isinstance(right_status["implemented"], bool)
            assert isinstance(right_status["effectiveness_score"], (int, float))
    
    def test_check_right_implementation_access(self):
        """Test access right implementation check"""
        # Mock database queries
        self.mock_db.execute.return_value.scalar.return_value = 5
        
        result = self.engine._check_right_implementation(
            right=DataSubjectRight.ACCESS,
            tenant_id=self.tenant_id,
            db=self.mock_db
        )
        
        assert isinstance(result, dict)
        assert "implemented" in result
        assert "effectiveness_score" in result
        assert "response_time_hours" in result
        assert result["implemented"] is True
        assert result["effectiveness_score"] > 0
    
    def test_check_right_implementation_erasure(self):
        """Test erasure right implementation check"""
        # Mock database queries
        self.mock_db.execute.return_value.scalar.return_value = 3
        
        result = self.engine._check_right_implementation(
            right=DataSubjectRight.ERASURE,
            tenant_id=self.tenant_id,
            db=self.mock_db
        )
        
        assert isinstance(result, dict)
        assert "implemented" in result
        assert "effectiveness_score" in result
        assert result["implemented"] is True
    
    def test_is_right_required_by_regulation(self):
        """Test checking if right is required by regulation"""
        # GDPR requires access right
        assert self.engine._is_right_required_by_regulation(
            DataSubjectRight.ACCESS, DataProtectionRegulation.GDPR
        ) is True
        
        # CCPA requires access right
        assert self.engine._is_right_required_by_regulation(
            DataSubjectRight.ACCESS, DataProtectionRegulation.CCPA
        ) is True
        
        # PIPEDA requires access right
        assert self.engine._is_right_required_by_regulation(
            DataSubjectRight.ACCESS, DataProtectionRegulation.PIPEDA
        ) is True
        
        # GDPR requires portability right
        assert self.engine._is_right_required_by_regulation(
            DataSubjectRight.PORTABILITY, DataProtectionRegulation.GDPR
        ) is True
        
        # PIPEDA does not require portability right
        assert self.engine._is_right_required_by_regulation(
            DataSubjectRight.PORTABILITY, DataProtectionRegulation.PIPEDA
        ) is False
    
    def test_calculate_regulation_score(self):
        """Test regulation score calculation"""
        assessments = [
            ComplianceAssessment(
                requirement_id="REQ1",
                regulation=DataProtectionRegulation.GDPR,
                status=ComplianceStatus.COMPLIANT,
                compliance_score=90.0,
                evidence_found=[],
                gaps_identified=[],
                risk_level="low",
                recommendations=[],
                assessment_date=datetime.utcnow()
            ),
            ComplianceAssessment(
                requirement_id="REQ2",
                regulation=DataProtectionRegulation.GDPR,
                status=ComplianceStatus.PARTIALLY_COMPLIANT,
                compliance_score=75.0,
                evidence_found=[],
                gaps_identified=[],
                risk_level="medium",
                recommendations=[],
                assessment_date=datetime.utcnow()
            )
        ]
        
        score = self.engine._calculate_regulation_score(assessments)
        assert score == 82.5  # (90 + 75) / 2
    
    def test_calculate_overall_compliance_score(self):
        """Test overall compliance score calculation"""
        regulation_scores = {
            "gdpr": 85.0,
            "ccpa": 78.0,
            "pipeda": 92.0
        }
        
        overall_score = self.engine._calculate_overall_compliance_score(regulation_scores)
        assert overall_score == 85.0  # (85 + 78 + 92) / 3
    
    def test_determine_compliance_status(self):
        """Test compliance status determination"""
        # Test compliant status
        assert self.engine._determine_compliance_status(95.0) == ComplianceStatus.COMPLIANT
        
        # Test partially compliant status
        assert self.engine._determine_compliance_status(80.0) == ComplianceStatus.PARTIALLY_COMPLIANT
        
        # Test non-compliant status
        assert self.engine._determine_compliance_status(60.0) == ComplianceStatus.NON_COMPLIANT
    
    def test_assess_risk_level(self):
        """Test risk level assessment"""
        # Critical risk: low score, mandatory, high penalty
        risk = self.engine._assess_risk_level(40.0, "critical", True)
        assert risk == "critical"
        
        # High risk: medium score, high penalty
        risk = self.engine._assess_risk_level(65.0, "high", True)
        assert risk == "high"
        
        # Medium risk: good score but some gaps
        risk = self.engine._assess_risk_level(80.0, "medium", True)
        assert risk == "medium"
        
        # Low risk: high score
        risk = self.engine._assess_risk_level(95.0, "low", False)
        assert risk == "low"
    
    def test_identify_high_risk_gaps(self):
        """Test high risk gaps identification"""
        regulation_assessments = {
            "gdpr": [
                ComplianceAssessment(
                    requirement_id="REQ1",
                    regulation=DataProtectionRegulation.GDPR,
                    status=ComplianceStatus.NON_COMPLIANT,
                    compliance_score=40.0,
                    evidence_found=[],
                    gaps_identified=["Major gap"],
                    risk_level="critical",
                    recommendations=["Fix immediately"],
                    assessment_date=datetime.utcnow()
                ),
                ComplianceAssessment(
                    requirement_id="REQ2",
                    regulation=DataProtectionRegulation.GDPR,
                    status=ComplianceStatus.COMPLIANT,
                    compliance_score=95.0,
                    evidence_found=["Good evidence"],
                    gaps_identified=[],
                    risk_level="low",
                    recommendations=[],
                    assessment_date=datetime.utcnow()
                )
            ]
        }
        
        high_risk_gaps = self.engine._identify_high_risk_gaps(regulation_assessments)
        assert len(high_risk_gaps) == 1
        assert high_risk_gaps[0].requirement_id == "REQ1"
        assert high_risk_gaps[0].risk_level == "critical"
    
    def test_identify_critical_violations(self):
        """Test critical violations identification"""
        # Mock database queries for violations
        self.mock_db.execute.return_value.scalar.side_effect = [2, 15]  # 2 breaches, 15 unauthorized access
        
        violations = self.engine._identify_critical_violations(
            tenant_id=self.tenant_id,
            regulations=[DataProtectionRegulation.GDPR],
            assessment_date=self.assessment_date,
            db=self.mock_db
        )
        
        assert isinstance(violations, list)
        assert len(violations) == 2  # data breach + unauthorized access
        
        # Check data breach violation
        breach_violation = next((v for v in violations if v["type"] == "data_breach"), None)
        assert breach_violation is not None
        assert breach_violation["severity"] == "critical"
        assert breach_violation["count"] == 2
        
        # Check unauthorized access violation
        access_violation = next((v for v in violations if v["type"] == "unauthorized_access"), None)
        assert access_violation is not None
        assert access_violation["severity"] == "high"
        assert access_violation["count"] == 15
    
    def test_generate_priority_recommendations(self):
        """Test priority recommendations generation"""
        regulation_assessments = {
            "gdpr": [
                ComplianceAssessment(
                    requirement_id="REQ1",
                    regulation=DataProtectionRegulation.GDPR,
                    status=ComplianceStatus.NON_COMPLIANT,
                    compliance_score=40.0,
                    evidence_found=[],
                    gaps_identified=[],
                    risk_level="high",
                    recommendations=["Implement consent management", "Improve documentation"],
                    assessment_date=datetime.utcnow()
                )
            ]
        }
        
        high_risk_gaps = [regulation_assessments["gdpr"][0]]
        critical_violations = [
            {"type": "data_breach", "severity": "critical"}
        ]
        
        recommendations = self.engine._generate_priority_recommendations(
            regulation_assessments, high_risk_gaps, critical_violations
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("data breach" in rec.lower() for rec in recommendations)
    
    def test_create_implementation_roadmap(self):
        """Test implementation roadmap creation"""
        high_risk_gaps = [
            ComplianceAssessment(
                requirement_id="REQ1",
                regulation=DataProtectionRegulation.GDPR,
                status=ComplianceStatus.NON_COMPLIANT,
                compliance_score=30.0,
                evidence_found=[],
                gaps_identified=[],
                risk_level="critical",
                recommendations=["Critical fix needed"],
                assessment_date=datetime.utcnow()
            ),
            ComplianceAssessment(
                requirement_id="REQ2",
                regulation=DataProtectionRegulation.GDPR,
                status=ComplianceStatus.PARTIALLY_COMPLIANT,
                compliance_score=65.0,
                evidence_found=[],
                gaps_identified=[],
                risk_level="high",
                recommendations=["High priority improvement"],
                assessment_date=datetime.utcnow()
            )
        ]
        
        priority_recommendations = ["Fix critical issues", "Improve processes"]
        
        roadmap = self.engine._create_implementation_roadmap(
            high_risk_gaps, priority_recommendations
        )
        
        assert isinstance(roadmap, list)
        assert len(roadmap) >= 1
        
        # Check that phases are properly structured
        for phase in roadmap:
            assert "phase" in phase
            assert "timeline" in phase
            assert "priority" in phase
            assert "items" in phase
            assert "success_criteria" in phase
    
    def test_find_requirement_by_id(self):
        """Test finding requirement by ID"""
        # Test with existing requirement
        requirement = self.engine._find_requirement_by_id("GDPR-ART6")
        assert requirement is not None
        assert requirement.requirement_id == "GDPR-ART6"
        
        # Test with non-existing requirement
        requirement = self.engine._find_requirement_by_id("NON-EXISTENT")
        assert requirement is None
    
    def test_group_assessments_by_principle(self):
        """Test grouping assessments by principle"""
        regulation_assessments = {
            "gdpr": [
                ComplianceAssessment(
                    requirement_id="GDPR-ART6",  # Lawfulness principle
                    regulation=DataProtectionRegulation.GDPR,
                    status=ComplianceStatus.COMPLIANT,
                    compliance_score=90.0,
                    evidence_found=[],
                    gaps_identified=[],
                    risk_level="low",
                    recommendations=[],
                    assessment_date=datetime.utcnow()
                ),
                ComplianceAssessment(
                    requirement_id="GDPR-ART12",  # Transparency principle
                    regulation=DataProtectionRegulation.GDPR,
                    status=ComplianceStatus.PARTIALLY_COMPLIANT,
                    compliance_score=75.0,
                    evidence_found=[],
                    gaps_identified=[],
                    risk_level="medium",
                    recommendations=[],
                    assessment_date=datetime.utcnow()
                )
            ]
        }
        
        principle_assessments = self.engine._group_assessments_by_principle(regulation_assessments)
        
        assert isinstance(principle_assessments, dict)
        # Should have assessments grouped by principle
        assert len(principle_assessments) >= 1
    
    def test_calculate_principle_scores(self):
        """Test principle scores calculation"""
        principle_assessments = {
            "lawfulness": [
                ComplianceAssessment(
                    requirement_id="REQ1",
                    regulation=DataProtectionRegulation.GDPR,
                    status=ComplianceStatus.COMPLIANT,
                    compliance_score=90.0,
                    evidence_found=[],
                    gaps_identified=[],
                    risk_level="low",
                    recommendations=[],
                    assessment_date=datetime.utcnow()
                ),
                ComplianceAssessment(
                    requirement_id="REQ2",
                    regulation=DataProtectionRegulation.CCPA,
                    status=ComplianceStatus.PARTIALLY_COMPLIANT,
                    compliance_score=80.0,
                    evidence_found=[],
                    gaps_identified=[],
                    risk_level="medium",
                    recommendations=[],
                    assessment_date=datetime.utcnow()
                )
            ]
        }
        
        principle_scores = self.engine._calculate_principle_scores(principle_assessments)
        
        assert isinstance(principle_scores, dict)
        assert "lawfulness" in principle_scores
        assert principle_scores["lawfulness"] == 85.0  # (90 + 80) / 2
    
    def test_error_handling_in_assessment(self):
        """Test error handling during assessment"""
        # Mock database to raise an exception
        self.mock_db.execute.side_effect = Exception("Database error")
        
        regulations = [DataProtectionRegulation.GDPR]
        
        # Assessment should handle the error gracefully
        report = self.engine.assess_data_protection_compliance(
            tenant_id=self.tenant_id,
            regulations=regulations,
            assessment_date=self.assessment_date,
            assessed_by=self.assessed_by,
            db=self.mock_db
        )
        
        # Should still return a report with error information
        assert isinstance(report, DataProtectionComplianceReport)
        assert report.overall_compliance_score >= 0


class TestDataProtectionRegulationEnum:
    """Test suite for DataProtectionRegulation enum"""
    
    def test_regulation_enum_values(self):
        """Test regulation enum values"""
        assert DataProtectionRegulation.GDPR.value == "gdpr"
        assert DataProtectionRegulation.CCPA.value == "ccpa"
        assert DataProtectionRegulation.PIPEDA.value == "pipeda"
        assert DataProtectionRegulation.LGPD.value == "lgpd"
        assert DataProtectionRegulation.PDPA_SG.value == "pdpa_sg"
        assert DataProtectionRegulation.DPA_UK.value == "dpa_uk"
        assert DataProtectionRegulation.PRIVACY_ACT_AU.value == "privacy_act_au"
        assert DataProtectionRegulation.APPI.value == "appi"
    
    def test_regulation_enum_count(self):
        """Test that all expected regulations are defined"""
        regulations = list(DataProtectionRegulation)
        assert len(regulations) == 8  # Expected number of supported regulations


class TestDataProtectionPrincipleEnum:
    """Test suite for DataProtectionPrinciple enum"""
    
    def test_principle_enum_values(self):
        """Test principle enum values"""
        assert DataProtectionPrinciple.LAWFULNESS.value == "lawfulness"
        assert DataProtectionPrinciple.FAIRNESS.value == "fairness"
        assert DataProtectionPrinciple.TRANSPARENCY.value == "transparency"
        assert DataProtectionPrinciple.PURPOSE_LIMITATION.value == "purpose_limitation"
        assert DataProtectionPrinciple.DATA_MINIMIZATION.value == "data_minimization"
        assert DataProtectionPrinciple.ACCURACY.value == "accuracy"
        assert DataProtectionPrinciple.STORAGE_LIMITATION.value == "storage_limitation"
        assert DataProtectionPrinciple.SECURITY.value == "security"
        assert DataProtectionPrinciple.ACCOUNTABILITY.value == "accountability"


class TestDataSubjectRightEnum:
    """Test suite for DataSubjectRight enum"""
    
    def test_right_enum_values(self):
        """Test data subject right enum values"""
        assert DataSubjectRight.ACCESS.value == "access"
        assert DataSubjectRight.RECTIFICATION.value == "rectification"
        assert DataSubjectRight.ERASURE.value == "erasure"
        assert DataSubjectRight.RESTRICTION.value == "restriction"
        assert DataSubjectRight.PORTABILITY.value == "portability"
        assert DataSubjectRight.OBJECTION.value == "objection"
        assert DataSubjectRight.AUTOMATED_DECISION.value == "automated_decision"
        assert DataSubjectRight.CONSENT_WITHDRAWAL.value == "consent_withdrawal"


class TestComplianceDataClasses:
    """Test suite for compliance data classes"""
    
    def test_regulation_requirement_creation(self):
        """Test RegulationRequirement data class"""
        requirement = RegulationRequirement(
            regulation=DataProtectionRegulation.GDPR,
            requirement_id="TEST-REQ",
            title="Test Requirement",
            description="Test description",
            principle=DataProtectionPrinciple.LAWFULNESS,
            mandatory=True,
            applicable_rights=[DataSubjectRight.ACCESS],
            verification_criteria=["Test criteria"],
            penalty_severity="high"
        )
        
        assert requirement.regulation == DataProtectionRegulation.GDPR
        assert requirement.requirement_id == "TEST-REQ"
        assert requirement.title == "Test Requirement"
        assert requirement.mandatory is True
        assert DataSubjectRight.ACCESS in requirement.applicable_rights
    
    def test_compliance_assessment_creation(self):
        """Test ComplianceAssessment data class"""
        assessment = ComplianceAssessment(
            requirement_id="TEST-REQ",
            regulation=DataProtectionRegulation.GDPR,
            status=ComplianceStatus.COMPLIANT,
            compliance_score=85.0,
            evidence_found=["Evidence 1"],
            gaps_identified=[],
            risk_level="low",
            recommendations=["Recommendation 1"],
            assessment_date=datetime.utcnow()
        )
        
        assert assessment.requirement_id == "TEST-REQ"
        assert assessment.regulation == DataProtectionRegulation.GDPR
        assert assessment.status == ComplianceStatus.COMPLIANT
        assert assessment.compliance_score == 85.0
        assert "Evidence 1" in assessment.evidence_found
    
    def test_compliance_report_creation(self):
        """Test DataProtectionComplianceReport data class"""
        report = DataProtectionComplianceReport(
            report_id="test-report-123",
            tenant_id="test-tenant",
            assessment_date=datetime.utcnow(),
            regulations_assessed=[DataProtectionRegulation.GDPR],
            overall_compliance_score=85.0,
            overall_status=ComplianceStatus.PARTIALLY_COMPLIANT,
            regulation_assessments={},
            regulation_scores={},
            principle_assessments={},
            principle_scores={},
            rights_implementation={},
            high_risk_gaps=[],
            critical_violations=[],
            priority_recommendations=[],
            implementation_roadmap=[],
            assessed_by=uuid4(),
            next_assessment_due=datetime.utcnow() + timedelta(days=90)
        )
        
        assert report.report_id == "test-report-123"
        assert report.tenant_id == "test-tenant"
        assert DataProtectionRegulation.GDPR in report.regulations_assessed
        assert report.overall_compliance_score == 85.0
        assert report.overall_status == ComplianceStatus.PARTIALLY_COMPLIANT


if __name__ == "__main__":
    pytest.main([__file__])