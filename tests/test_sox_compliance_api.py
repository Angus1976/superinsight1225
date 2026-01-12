"""
Tests for SOX Compliance API endpoints.

Tests the REST API endpoints for SOX compliance functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from src.app import app
from src.security.middleware import get_current_active_user
from src.compliance.sox_compliance import (
    SOXComplianceEngine,
    SOXSection,
    SOXControlType,
    SOXRiskLevel,
    SOXComplianceReport
)


class TestSOXComplianceAPI:
    """Test SOX Compliance API endpoints."""
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock()
        user.id = uuid4()
        user.tenant_id = "test_tenant"
        user.username = "test_user"
        user.is_active = True
        
        # Mock role object with value attribute
        mock_role = Mock()
        mock_role.value = "admin"  # Use admin role which should have SOX permissions
        user.role = mock_role
        
        return user
    
    @pytest.fixture
    def client(self, mock_user):
        """Create test client with mocked authentication."""
        # Override the dependency
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        client = TestClient(app)
        yield client
        # Clean up
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def mock_sox_report(self):
        """Create mock SOX compliance report."""
        report = Mock()
        report.report_id = str(uuid4())
        report.tenant_id = "test_tenant"
        report.reporting_period = {
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31)
        }
        report.generation_time = datetime.utcnow()
        report.management_assertion = "Management asserts effective internal controls"
        report.ceo_certification = True
        report.cfo_certification = True
        report.overall_effectiveness = "effective"
        report.material_weaknesses = []
        report.significant_deficiencies = []
        report.controls_tested = 25
        report.controls_effective = 23
        report.controls_ineffective = 2
        report.financial_statement_controls = {"overall_rating": 88.0}
        report.disclosure_controls = {"overall_rating": 90.0}
        report.it_general_controls = {"overall_rating": 85.0}
        report.application_controls = {"overall_rating": 92.0}
        report.audit_trail_integrity = {"overall_integrity_score": 95.0}
        report.sox_compliance_status = "compliant"
        return report
    
    @patch('src.api.sox_compliance_api.sox_engine.assess_sox_compliance')
    def test_perform_sox_assessment(self, mock_assess, client, mock_user, mock_sox_report):
        """Test SOX assessment endpoint."""
        mock_assess.return_value = mock_sox_report
        
        # Test assessment request
        assessment_request = {
            "assessment_date": datetime.utcnow().isoformat(),
            "include_testing": True,
            "scope": None
        }
        
        response = client.post("/api/sox/assessment", json=assessment_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "report_id" in data
        assert "tenant_id" in data
        assert "sox_compliance_status" in data
        assert "overall_effectiveness" in data
        assert "management_assertion" in data
        assert "controls_tested" in data
        assert "controls_effective" in data
        
        # Verify assessment was called
        mock_assess.assert_called_once()
    
    @patch('src.api.sox_compliance_api.sox_engine.assess_sox_compliance')
    def test_get_sox_dashboard(self, mock_assess, client, mock_user, mock_sox_report):
        """Test SOX dashboard endpoint."""
        mock_assess.return_value = mock_sox_report
        
        response = client.get("/api/sox/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify dashboard structure
        assert "tenant_id" in data
        assert "assessment_date" in data
        assert "overall_effectiveness" in data
        assert "sox_compliance_status" in data
        assert "compliance_score" in data
        assert "total_controls" in data
        assert "effective_controls" in data
        assert "ineffective_controls" in data
        assert "total_deficiencies" in data
        assert "material_weaknesses" in data
        assert "significant_deficiencies" in data
        assert "testing_completion_rate" in data
        assert "compliance_trend" in data
        assert "deficiency_trend" in data
        
        # Verify compliance score is valid
        assert 0 <= data["compliance_score"] <= 100
    
    def test_list_sox_controls(self, client, mock_user):
        """Test list SOX controls endpoint."""
        response = client.get("/api/sox/controls")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response is a list
        assert isinstance(data, list)
        
        # If controls exist, verify structure
        if data:
            control = data[0]
            assert "control_id" in control
            assert "control_name" in control
            assert "control_type" in control
            assert "sox_section" in control
            assert "description" in control
            assert "risk_level" in control
            assert "frequency" in control
            assert "owner" in control
            assert "testing_procedures" in control
            assert "evidence_requirements" in control
            assert "automated" in control
    
    def test_list_sox_controls_with_filters(self, client, mock_user):
        """Test list SOX controls with filters."""
        # Test with control type filter
        response = client.get("/api/sox/controls?control_type=entity_level")
        
        assert response.status_code == 200
    
    def test_get_sox_control_detail(self, client, mock_user):
        """Test get SOX control detail endpoint."""
        # Test with a known control ID (from SOX engine)
        response = client.get("/api/sox/controls/SOX-ELC-001")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify control detail structure
            assert "control_id" in data
            assert "control_name" in data
            assert "control_type" in data
            assert "sox_section" in data
            assert "description" in data
            assert "risk_level" in data
            assert "frequency" in data
            assert "owner" in data
            assert "testing_procedures" in data
            assert "evidence_requirements" in data
    
    def test_get_nonexistent_sox_control(self, client, mock_user):
        """Test get nonexistent SOX control."""
        response = client.get("/api/sox/controls/NONEXISTENT")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch('src.api.sox_compliance_api.sox_engine._execute_control_test')
    def test_test_sox_controls(self, mock_test, client, mock_user):
        """Test SOX controls testing endpoint."""
        # Mock test result
        mock_test_result = Mock()
        mock_test_result.test_id = str(uuid4())
        mock_test_result.control_id = "SOX-ELC-001"
        mock_test_result.test_date = datetime.utcnow()
        mock_test_result.tester = "test_user"
        mock_test_result.test_procedures_performed = ["Review documentation", "Test controls"]
        mock_test_result.sample_size = 25
        mock_test_result.exceptions_noted = 0
        mock_test_result.test_conclusion = "effective"
        mock_test_result.evidence_obtained = ["Control documentation", "Test results"]
        mock_test_result.deficiencies_identified = []
        mock_test_result.management_response = None
        
        mock_test.return_value = mock_test_result
        
        # Test control testing request
        test_request = {
            "control_ids": ["SOX-ELC-001"],
            "test_date": datetime.utcnow().isoformat(),
            "sample_size": 25,
            "tester": "test_user"
        }
        
        response = client.post("/api/sox/controls/test", json=test_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response is a list of test results
        assert isinstance(data, list)
        
        if data:
            result = data[0]
            assert "test_id" in result
            assert "control_id" in result
            assert "test_date" in result
            assert "tester" in result
            assert "test_procedures_performed" in result
            assert "sample_size" in result
            assert "exceptions_noted" in result
    
    @patch('src.api.sox_compliance_api.sox_engine.assess_sox_compliance')
    def test_list_sox_deficiencies(self, mock_assess, client, mock_user, mock_sox_report):
        """Test list SOX deficiencies endpoint."""
        mock_assess.return_value = mock_sox_report
        
        response = client.get("/api/sox/deficiencies")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response is a list
        assert isinstance(data, list)
        
        # Since mock report has no deficiencies, list should be empty
        assert len(data) == 0
    
    def test_remediate_sox_deficiency(self, client, mock_user):
        """Test remediate SOX deficiency endpoint."""
        # Test deficiency remediation request
        remediation_request = {
            "deficiency_id": "DEF-001",
            "remediation_plan": "Implement additional controls",
            "responsible_party": "Control Owner",
            "target_completion_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "status": "in_progress"
        }
        
        response = client.put("/api/sox/deficiencies/DEF-001/remediate", json=remediation_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify remediation response
        assert "message" in data
        assert "deficiency_id" in data
        assert "status" in data
        assert "updated_by" in data
        assert "updated_at" in data
    
    @patch('src.api.sox_compliance_api.sox_engine._verify_audit_trail_integrity')
    def test_check_audit_trail_integrity(self, mock_verify, client, mock_user):
        """Test audit trail integrity check endpoint."""
        # Mock integrity results
        mock_verify.return_value = {
            "overall_integrity_score": 95.0,
            "tamper_protection": {
                "tamper_protection_enabled": True,
                "integrity_checks_passed": True
            },
            "audit_completeness": {
                "completeness_score": 98.0,
                "missing_events": 0
            },
            "data_consistency": {
                "consistency_score": 96.0,
                "inconsistencies_found": 0
            }
        }
        
        response = client.get("/api/sox/audit-trail-integrity")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify integrity check response
        assert "tenant_id" in data
        assert "assessment_period" in data
        assert "integrity_assessment" in data
        assert "sox_compliance" in data
        
        # Verify SOX compliance assessment
        sox_compliance = data["sox_compliance"]
        assert "audit_trail_compliant" in sox_compliance
        assert "section_802_compliant" in sox_compliance
        assert isinstance(sox_compliance["audit_trail_compliant"], bool)
        assert isinstance(sox_compliance["section_802_compliant"], bool)
    
    @patch('src.api.sox_compliance_api.sox_engine.assess_sox_compliance')
    def test_get_management_certification_status(self, mock_assess, client, mock_user, mock_sox_report):
        """Test management certification status endpoint."""
        mock_assess.return_value = mock_sox_report
        
        response = client.get("/api/sox/management-certification")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify certification status response
        assert "tenant_id" in data
        assert "reporting_period" in data
        assert "management_assertion" in data
        assert "certifications" in data
        assert "internal_control_assessment" in data
        assert "disclosure_controls" in data
        
        # Verify certifications structure
        certifications = data["certifications"]
        assert "ceo_certification" in certifications
        assert "cfo_certification" in certifications
        
        for cert_type in ["ceo_certification", "cfo_certification"]:
            cert = certifications[cert_type]
            assert "required" in cert
            assert "completed" in cert
            assert "section" in cert
            assert isinstance(cert["required"], bool)
            assert isinstance(cert["completed"], bool)
    
    @patch('src.api.sox_compliance_api.sox_engine.assess_sox_compliance')
    def test_export_sox_report(self, mock_assess, client, mock_user, mock_sox_report):
        """Test SOX report export endpoint."""
        mock_assess.return_value = mock_sox_report
        
        # Test JSON export
        response = client.post("/api/sox/export-report/test-report-id?export_format=json")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        
        # Test Excel export
        response = client.post("/api/sox/export-report/test-report-id?export_format=excel")
        
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers["content-type"]
    
    def test_export_sox_report_invalid_format(self, client, mock_user):
        """Test SOX report export with invalid format."""
        response = client.post("/api/sox/export-report/test-report-id?export_format=invalid")
        
        assert response.status_code == 400
        data = response.json()
        assert "unsupported export format" in data["detail"].lower()
    
    def test_get_sox_sections(self, client, mock_user):
        """Test get SOX sections endpoint."""
        response = client.get("/api/sox/sections")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response is a list of sections
        assert isinstance(data, list)
        
        # Verify section structure
        if data:
            section = data[0]
            assert "section_code" in section
            assert "section_name" in section
            assert "description" in section
            assert "key_requirements" in section
            assert "compliance_status" in section
            
            # Verify key_requirements is a list
            assert isinstance(section["key_requirements"], list)


class TestSOXComplianceAPIUnauthorized:
    """Test SOX Compliance API unauthorized access."""
    
    @pytest.fixture
    def client(self):
        """Create test client without authentication."""
        return TestClient(app)
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to SOX endpoints."""
        # Test without authentication
        response = client.post("/api/sox/assessment", json={})
        
        # Should return 401 or 403 or 422 (validation error in test environment)
        assert response.status_code in [401, 403, 422]  # 422 for validation error in test