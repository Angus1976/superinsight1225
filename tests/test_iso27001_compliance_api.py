"""
Tests for ISO 27001 Compliance API endpoints.

Tests the REST API endpoints for ISO 27001 compliance assessment,
control evaluation, and reporting functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.iso27001_compliance_api import router
from src.compliance.iso27001_compliance import (
    ISO27001Assessment,
    ISO27001Control,
    ISO27001ControlDomain,
    ISO27001ControlStatus
)


class TestISO27001ComplianceAPI:
    """Test ISO 27001 compliance API endpoints"""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI test application"""
        app = FastAPI()
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user"""
        user = Mock()
        user.id = "user-123"
        user.username = "testuser"
        return user
    
    @pytest.fixture
    def mock_assessment(self):
        """Create mock ISO 27001 assessment"""
        assessment = ISO27001Assessment(
            assessment_id="assessment-123",
            tenant_id="tenant-123",
            assessment_date=datetime.utcnow(),
            overall_maturity_level=3,
            overall_compliance_score=75.5,
            domain_scores={
                "A.5": 80.0,
                "A.9": 75.0,
                "A.12": 70.0,
                "A.16": 77.0
            },
            control_assessments=[
                ISO27001Control(
                    control_id="A.5.1",
                    domain=ISO27001ControlDomain.INFORMATION_SECURITY_POLICIES,
                    title="Information Security Policy",
                    description="Test control",
                    implementation_guidance="Test guidance",
                    status=ISO27001ControlStatus.IMPLEMENTED,
                    effectiveness_score=85.0,
                    evidence=["Policy document exists"],
                    gaps=[],
                    recommendations=[]
                ),
                ISO27001Control(
                    control_id="A.9.2",
                    domain=ISO27001ControlDomain.ACCESS_CONTROL,
                    title="User Access Management",
                    description="Test control",
                    implementation_guidance="Test guidance",
                    status=ISO27001ControlStatus.PARTIALLY_IMPLEMENTED,
                    effectiveness_score=65.0,
                    evidence=["Basic processes"],
                    gaps=["Incomplete procedures"],
                    recommendations=["Enhance procedures"]
                )
            ],
            identified_risks=[
                {
                    "risk_id": "risk-1",
                    "title": "Access Control Gap",
                    "risk_level": "Medium",
                    "control_reference": "A.9.2"
                }
            ],
            risk_treatment_plan=[
                {
                    "risk_id": "risk-1",
                    "treatment_option": "Mitigate",
                    "action_plan": "Enhance access control procedures"
                }
            ],
            priority_recommendations=[
                "Improve access control procedures",
                "Enhance logging and monitoring"
            ],
            implementation_roadmap=[
                {
                    "phase": "Phase 1",
                    "duration": "0-3 months",
                    "controls": ["A.9.2"]
                }
            ]
        )
        return assessment
    
    @patch('src.api.iso27001_compliance_api.get_current_user')
    @patch('src.api.iso27001_compliance_api.rbac_controller')
    @patch('src.api.iso27001_compliance_api.compliance_checker')
    def test_conduct_iso27001_assessment(self, mock_checker, mock_rbac, mock_get_user, client, mock_user, mock_assessment):
        """Test ISO 27001 assessment endpoint"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_rbac.check_permission.return_value = True
        mock_checker.assess_iso27001_compliance.return_value = mock_assessment
        
        # Test request
        request_data = {
            "tenant_id": "tenant-123",
            "include_risk_assessment": True
        }
        
        response = client.post("/api/iso27001/assessment", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["assessment_id"] == "assessment-123"
        assert data["tenant_id"] == "tenant-123"
        assert data["overall_maturity_level"] == 3
        assert data["overall_compliance_score"] == 75.5
        assert data["control_count"] == 2
        assert data["implemented_controls"] == 1
        assert data["partially_implemented_controls"] == 1
        assert data["not_implemented_controls"] == 0
        assert len(data["high_priority_recommendations"]) > 0
        
        # Verify domain scores
        assert "A.5" in data["domain_scores"]
        assert "A.9" in data["domain_scores"]
        assert data["domain_scores"]["A.5"] == 80.0
    
    @patch('src.api.iso27001_compliance_api.get_current_user')
    @patch('src.api.iso27001_compliance_api.rbac_controller')
    def test_conduct_assessment_permission_denied(self, mock_rbac, mock_get_user, client, mock_user):
        """Test assessment endpoint with insufficient permissions"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_rbac.check_permission.return_value = False
        
        request_data = {
            "tenant_id": "tenant-123",
            "include_risk_assessment": True
        }
        
        response = client.post("/api/iso27001/assessment", json=request_data)
        
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
    
    @patch('src.api.iso27001_compliance_api.get_current_user')
    @patch('src.api.iso27001_compliance_api.rbac_controller')
    @patch('src.api.iso27001_compliance_api.compliance_checker')
    def test_get_domain_summary(self, mock_checker, mock_rbac, mock_get_user, client, mock_user, mock_assessment):
        """Test domain summary endpoint"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_rbac.check_permission.return_value = True
        mock_checker.assess_iso27001_compliance.return_value = mock_assessment
        
        response = client.get("/api/iso27001/domains?tenant_id=tenant-123")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check domain summary structure
        for domain_summary in data:
            assert "domain_code" in domain_summary
            assert "domain_name" in domain_summary
            assert "control_count" in domain_summary
            assert "average_score" in domain_summary
            assert "implemented_count" in domain_summary
            assert "gaps_count" in domain_summary
            assert "priority_level" in domain_summary
    
    @patch('src.api.iso27001_compliance_api.get_current_user')
    @patch('src.api.iso27001_compliance_api.rbac_controller')
    @patch('src.api.iso27001_compliance_api.compliance_checker')
    def test_get_domain_controls(self, mock_checker, mock_rbac, mock_get_user, client, mock_user, mock_assessment):
        """Test domain controls endpoint"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_rbac.check_permission.return_value = True
        mock_checker.assess_iso27001_compliance.return_value = mock_assessment
        
        response = client.get("/api/iso27001/controls/A.5?tenant_id=tenant-123")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # Should return A.5 controls only
        for control in data:
            assert control["domain"] == "A.5"
            assert "control_id" in control
            assert "title" in control
            assert "description" in control
            assert "status" in control
            assert "effectiveness_score" in control
            assert "evidence" in control
            assert "gaps" in control
            assert "recommendations" in control
    
    def test_get_domain_controls_invalid_domain(self, client):
        """Test domain controls endpoint with invalid domain"""
        with patch('src.api.iso27001_compliance_api.get_current_user') as mock_get_user, \
             patch('src.api.iso27001_compliance_api.rbac_controller') as mock_rbac:
            
            mock_user = Mock()
            mock_get_user.return_value = mock_user
            mock_rbac.check_permission.return_value = True
            
            response = client.get("/api/iso27001/controls/INVALID?tenant_id=tenant-123")
            
            assert response.status_code == 400
            assert "Invalid domain code" in response.json()["detail"]
    
    @patch('src.api.iso27001_compliance_api.get_current_user')
    @patch('src.api.iso27001_compliance_api.rbac_controller')
    @patch('src.api.iso27001_compliance_api.compliance_checker')
    def test_get_maturity_assessment(self, mock_checker, mock_rbac, mock_get_user, client, mock_user, mock_assessment):
        """Test maturity assessment endpoint"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_rbac.check_permission.return_value = True
        mock_checker.assess_iso27001_compliance.return_value = mock_assessment
        mock_checker.maturity_levels = {
            1: "Initial",
            2: "Repeatable", 
            3: "Defined",
            4: "Managed",
            5: "Optimizing"
        }
        
        response = client.get("/api/iso27001/maturity-assessment?tenant_id=tenant-123")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["overall_maturity_level"] == 3
        assert "maturity_description" in data
        assert "dimension_maturity" in data
        assert "improvement_roadmap" in data
        assert "next_level_requirements" in data
        
        # Check dimension maturity structure
        dimensions = data["dimension_maturity"]
        assert "policy_governance" in dimensions
        assert "access_control" in dimensions
        assert "operations_security" in dimensions
        assert "incident_management" in dimensions
        
        for dimension in dimensions.values():
            assert "level" in dimension
            assert "score" in dimension
            assert "description" in dimension
    
    @patch('src.api.iso27001_compliance_api.get_current_user')
    @patch('src.api.iso27001_compliance_api.rbac_controller')
    @patch('src.api.iso27001_compliance_api.compliance_checker')
    def test_get_risk_assessment(self, mock_checker, mock_rbac, mock_get_user, client, mock_user, mock_assessment):
        """Test risk assessment endpoint"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_rbac.check_permission.return_value = True
        mock_checker.assess_iso27001_compliance.return_value = mock_assessment
        
        response = client.get("/api/iso27001/risk-assessment?tenant_id=tenant-123")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert "assessment_id" in data
        assert "risk_summary" in data
        assert "identified_risks" in data
        assert "risk_treatment_plan" in data
        assert "risk_heat_map" in data
        assert "recommendations" in data
        
        # Check risk summary structure
        risk_summary = data["risk_summary"]
        assert "total_risks" in risk_summary
        assert "high_risks" in risk_summary
        assert "medium_risks" in risk_summary
        assert "low_risks" in risk_summary
        
        # Check risk heat map
        heat_map = data["risk_heat_map"]
        assert "critical_areas" in heat_map
        assert "improvement_areas" in heat_map
    
    @patch('src.api.iso27001_compliance_api.get_current_user')
    @patch('src.api.iso27001_compliance_api.rbac_controller')
    @patch('src.api.iso27001_compliance_api.compliance_checker')
    def test_generate_compliance_report_summary(self, mock_checker, mock_rbac, mock_get_user, client, mock_user, mock_assessment):
        """Test compliance report generation (summary format)"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_rbac.check_permission.return_value = True
        mock_checker.assess_iso27001_compliance.return_value = mock_assessment
        
        response = client.get("/api/iso27001/compliance-report?tenant_id=tenant-123&format=summary")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert "executive_summary" in data
        assert "key_findings" in data
        assert "next_steps" in data
        
        # Check executive summary structure
        exec_summary = data["executive_summary"]
        assert "assessment_date" in exec_summary
        assert "overall_compliance_score" in exec_summary
        assert "maturity_level" in exec_summary
        assert "total_controls_assessed" in exec_summary
        assert "compliant_controls" in exec_summary
        assert "critical_gaps" in exec_summary
    
    @patch('src.api.iso27001_compliance_api.get_current_user')
    @patch('src.api.iso27001_compliance_api.rbac_controller')
    @patch('src.api.iso27001_compliance_api.compliance_checker')
    def test_generate_compliance_report_full(self, mock_checker, mock_rbac, mock_get_user, client, mock_user, mock_assessment):
        """Test compliance report generation (full format)"""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_rbac.check_permission.return_value = True
        mock_checker.assess_iso27001_compliance.return_value = mock_assessment
        
        response = client.get("/api/iso27001/compliance-report?tenant_id=tenant-123&format=json")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert "assessment_metadata" in data
        assert "compliance_summary" in data
        assert "control_assessment" in data
        assert "risk_assessment" in data
        assert "improvement_plan" in data
        
        # Check assessment metadata
        metadata = data["assessment_metadata"]
        assert "assessment_id" in metadata
        assert "tenant_id" in metadata
        assert "assessment_date" in metadata
        assert "assessor" in metadata
        assert "scope" in metadata
        
        # Check compliance summary
        compliance_summary = data["compliance_summary"]
        assert "overall_score" in compliance_summary
        assert "maturity_level" in compliance_summary
        assert "domain_scores" in compliance_summary
        
        # Check control assessment
        control_assessment = data["control_assessment"]
        assert isinstance(control_assessment, list)
        if control_assessment:
            control = control_assessment[0]
            assert "control_id" in control
            assert "title" in control
            assert "domain" in control
            assert "status" in control
            assert "effectiveness_score" in control
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/iso27001/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["module"] == "ISO 27001 Compliance"
        assert "checker_status" in data
        assert "control_definitions_loaded" in data
        assert "supported_domains" in data
        assert "timestamp" in data
    
    @patch('src.api.iso27001_compliance_api.get_current_user')
    @patch('src.api.iso27001_compliance_api.rbac_controller')
    @patch('src.api.iso27001_compliance_api.compliance_checker')
    def test_api_error_handling(self, mock_checker, mock_rbac, mock_get_user, client, mock_user):
        """Test API error handling"""
        # Setup mocks to raise exception
        mock_get_user.return_value = mock_user
        mock_rbac.check_permission.return_value = True
        mock_checker.assess_iso27001_compliance.side_effect = Exception("Test error")
        
        request_data = {
            "tenant_id": "tenant-123",
            "include_risk_assessment": True
        }
        
        response = client.post("/api/iso27001/assessment", json=request_data)
        
        assert response.status_code == 500
        assert "Assessment failed" in response.json()["detail"]
    
    def test_request_validation(self, client):
        """Test request validation"""
        # Test missing required fields
        response = client.post("/api/iso27001/assessment", json={})
        
        assert response.status_code == 422  # Validation error
        
        # Test invalid field types
        invalid_request = {
            "tenant_id": 123,  # Should be string
            "include_risk_assessment": "yes"  # Should be boolean
        }
        
        response = client.post("/api/iso27001/assessment", json=invalid_request)
        assert response.status_code == 422


class TestISO27001APIIntegration:
    """Test ISO 27001 API integration with other systems"""
    
    def test_api_router_registration(self):
        """Test that API router is properly configured"""
        from src.api.iso27001_compliance_api import router
        
        # Verify router configuration
        assert router.prefix == "/api/iso27001"
        assert "ISO 27001 Compliance" in router.tags
        
        # Verify routes are registered
        route_paths = [route.path for route in router.routes]
        expected_paths = [
            "/assessment",
            "/domains", 
            "/controls/{domain}",
            "/maturity-assessment",
            "/risk-assessment",
            "/compliance-report",
            "/health"
        ]
        
        for expected_path in expected_paths:
            assert any(expected_path in path for path in route_paths)
    
    def test_pydantic_models(self):
        """Test Pydantic model definitions"""
        from src.api.iso27001_compliance_api import (
            ISO27001ControlResponse,
            ISO27001AssessmentResponse,
            ISO27001DomainSummary,
            ISO27001ComplianceRequest
        )
        
        # Test request model
        request_data = {
            "tenant_id": "test-tenant",
            "include_risk_assessment": True
        }
        request = ISO27001ComplianceRequest(**request_data)
        assert request.tenant_id == "test-tenant"
        assert request.include_risk_assessment is True
        
        # Test response models can be instantiated
        control_response = ISO27001ControlResponse(
            control_id="A.5.1",
            domain="A.5",
            title="Test Control",
            description="Test",
            status="implemented",
            effectiveness_score=85.0,
            evidence=["Evidence"],
            gaps=[],
            recommendations=[]
        )
        assert control_response.control_id == "A.5.1"
        
        assessment_response = ISO27001AssessmentResponse(
            assessment_id="test-id",
            tenant_id="test-tenant",
            assessment_date=datetime.utcnow(),
            overall_maturity_level=3,
            overall_compliance_score=75.0,
            domain_scores={"A.5": 80.0},
            control_count=10,
            implemented_controls=8,
            partially_implemented_controls=2,
            not_implemented_controls=0,
            high_priority_recommendations=["Recommendation"]
        )
        assert assessment_response.overall_maturity_level == 3


if __name__ == "__main__":
    pytest.main([__file__])