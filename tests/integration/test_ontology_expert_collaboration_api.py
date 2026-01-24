"""
Integration Tests for Ontology Expert Collaboration API

Tests the REST API endpoints for ontology expert collaboration including:
- Expert Management API
- Template API
- Collaboration API
- Approval Workflow API
- Validation API
- Impact Analysis API
- I18n API

Requirements: Task 15.8 - Write integration tests for API endpoints
"""

import pytest
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the FastAPI app
from src.app import app


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def expert_data() -> Dict[str, Any]:
    """Sample expert profile data."""
    return {
        "name": "张三",
        "email": f"zhangsan_{uuid4().hex[:8]}@example.com",
        "expertise_areas": ["finance", "compliance"],
        "certifications": ["ontology_engineer"],
        "languages": ["zh-CN", "en-US"],
        "department": "数据治理部",
        "title": "高级本体工程师",
        "bio": "10年金融行业数据治理经验"
    }


@pytest.fixture
def template_data() -> Dict[str, Any]:
    """Sample template data."""
    return {
        "name": "金融行业本体模板",
        "industry": "金融",
        "description": "适用于金融行业的标准本体模板",
        "entity_types": [
            {
                "name": "客户",
                "description": "金融客户实体",
                "attributes": [
                    {"name": "客户ID", "data_type": "string", "required": True},
                    {"name": "客户名称", "data_type": "string", "required": True}
                ]
            }
        ],
        "relation_types": [
            {
                "name": "持有",
                "description": "客户持有账户关系",
                "source_entity_type": "客户",
                "target_entity_type": "账户"
            }
        ],
        "validation_rules": []
    }


@pytest.fixture
def validation_rule_data() -> Dict[str, Any]:
    """Sample validation rule data."""
    return {
        "name": "统一社会信用代码验证",
        "rule_type": "FORMAT",
        "target_entity_type": "企业",
        "target_field": "统一社会信用代码",
        "validation_logic": r"^[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}$",
        "error_message_key": "validation.uscc.invalid_format",
        "region": "CN",
        "industry": "金融"
    }


# =============================================================================
# Expert Management API Tests
# =============================================================================

class TestExpertManagementAPI:
    """Tests for Expert Management API endpoints."""
    
    def test_create_expert_success(self, client, expert_data):
        """Test creating an expert profile successfully."""
        response = client.post(
            "/api/v1/ontology-collaboration/experts",
            json=expert_data
        )
        
        # Should return 201 Created
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == expert_data["name"]
        assert data["email"] == expert_data["email"]
        assert "id" in data
        assert "created_at" in data
    
    def test_create_expert_invalid_expertise_area(self, client, expert_data):
        """Test creating an expert with invalid expertise area."""
        expert_data["expertise_areas"] = ["invalid_area"]
        
        response = client.post(
            "/api/v1/ontology-collaboration/experts",
            json=expert_data
        )
        
        # Should return 400 Bad Request
        assert response.status_code == 400
    
    def test_create_expert_missing_required_fields(self, client):
        """Test creating an expert with missing required fields."""
        response = client.post(
            "/api/v1/ontology-collaboration/experts",
            json={"name": "Test"}  # Missing email and expertise_areas
        )
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
    
    def test_get_expert_not_found(self, client):
        """Test getting a non-existent expert."""
        response = client.get(
            f"/api/v1/ontology-collaboration/experts/{uuid4()}"
        )
        
        # Should return 404 Not Found
        assert response.status_code == 404
    
    def test_list_experts(self, client):
        """Test listing experts with pagination."""
        response = client.get(
            "/api/v1/ontology-collaboration/experts",
            params={"offset": 0, "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "experts" in data
        assert "offset" in data
        assert "limit" in data
        assert "total" in data
    
    def test_list_experts_filter_by_expertise(self, client):
        """Test listing experts filtered by expertise area."""
        response = client.get(
            "/api/v1/ontology-collaboration/experts",
            params={"expertise_area": "finance"}
        )
        
        assert response.status_code == 200
    
    def test_recommend_experts(self, client):
        """Test expert recommendation endpoint."""
        response = client.get(
            "/api/v1/ontology-collaboration/experts/recommend",
            params={"ontology_area": "finance", "limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "experts" in data
        assert "ontology_area" in data
        assert data["ontology_area"] == "finance"


# =============================================================================
# Template API Tests
# =============================================================================

class TestTemplateAPI:
    """Tests for Template API endpoints."""
    
    def test_list_templates(self, client):
        """Test listing templates."""
        response = client.get(
            "/api/v1/ontology-collaboration/templates"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "total" in data
    
    def test_list_templates_filter_by_industry(self, client):
        """Test listing templates filtered by industry."""
        response = client.get(
            "/api/v1/ontology-collaboration/templates",
            params={"industry": "金融"}
        )
        
        assert response.status_code == 200
    
    def test_get_template_not_found(self, client):
        """Test getting a non-existent template."""
        response = client.get(
            f"/api/v1/ontology-collaboration/templates/{uuid4()}"
        )
        
        # Should return 404 Not Found
        assert response.status_code == 404
    
    def test_export_template_not_found(self, client):
        """Test exporting a non-existent template."""
        response = client.get(
            f"/api/v1/ontology-collaboration/templates/{uuid4()}/export"
        )
        
        # Should return 404 Not Found
        assert response.status_code == 404


# =============================================================================
# Collaboration API Tests
# =============================================================================

class TestCollaborationAPI:
    """Tests for Collaboration API endpoints."""
    
    def test_create_session(self, client):
        """Test creating a collaboration session."""
        response = client.post(
            "/api/v1/ontology-collaboration/collaboration/sessions",
            json={"ontology_id": str(uuid4())},
            params={"expert_id": str(uuid4())}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "ontology_id" in data
    
    def test_join_session_not_found(self, client):
        """Test joining a non-existent session."""
        response = client.post(
            f"/api/v1/ontology-collaboration/collaboration/sessions/{uuid4()}/join",
            json={"expert_id": str(uuid4())}
        )
        
        # Should return 404 Not Found
        assert response.status_code == 404
    
    def test_create_change_request(self, client):
        """Test creating a change request."""
        response = client.post(
            "/api/v1/ontology-collaboration/collaboration/change-requests",
            json={
                "ontology_id": str(uuid4()),
                "change_type": "MODIFY",
                "target_element": "entity_customer",
                "proposed_changes": {"name": "客户_v2"},
                "description": "更新客户实体名称"
            },
            params={"requester_id": str(uuid4())}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "status" in data


# =============================================================================
# Approval Workflow API Tests
# =============================================================================

class TestApprovalWorkflowAPI:
    """Tests for Approval Workflow API endpoints."""
    
    def test_create_approval_chain(self, client):
        """Test creating an approval chain."""
        response = client.post(
            "/api/v1/ontology-collaboration/workflow/approval-chains",
            json={
                "name": "金融本体审批链",
                "ontology_area": "finance",
                "levels": [
                    {
                        "level_number": 1,
                        "approvers": [str(uuid4())],
                        "deadline_hours": 24
                    },
                    {
                        "level_number": 2,
                        "approvers": [str(uuid4())],
                        "deadline_hours": 48
                    }
                ],
                "approval_type": "SEQUENTIAL"
            },
            params={"created_by": str(uuid4())}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "金融本体审批链"
    
    def test_create_approval_chain_invalid_levels(self, client):
        """Test creating an approval chain with invalid level count."""
        response = client.post(
            "/api/v1/ontology-collaboration/workflow/approval-chains",
            json={
                "name": "无效审批链",
                "ontology_area": "finance",
                "levels": [],  # Empty levels - invalid
                "approval_type": "SEQUENTIAL"
            },
            params={"created_by": str(uuid4())}
        )
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
    
    def test_list_approval_chains(self, client):
        """Test listing approval chains."""
        response = client.get(
            "/api/v1/ontology-collaboration/workflow/approval-chains"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "approval_chains" in data
    
    def test_get_pending_approvals(self, client):
        """Test getting pending approvals for an expert."""
        response = client.get(
            "/api/v1/ontology-collaboration/workflow/pending-approvals",
            params={"expert_id": str(uuid4())}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "pending_approvals" in data
    
    def test_reject_without_reason(self, client):
        """Test rejecting a change request without a reason."""
        response = client.post(
            f"/api/v1/ontology-collaboration/workflow/change-requests/{uuid4()}/reject",
            json={
                "expert_id": str(uuid4()),
                "action": "reject"
                # Missing reason
            }
        )
        
        # Should return 400 Bad Request
        assert response.status_code == 400


# =============================================================================
# Validation API Tests
# =============================================================================

class TestValidationAPI:
    """Tests for Validation API endpoints."""
    
    def test_list_validation_rules(self, client):
        """Test listing validation rules."""
        response = client.get(
            "/api/v1/ontology-collaboration/validation/rules"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data
    
    def test_list_validation_rules_filter_by_region(self, client):
        """Test listing validation rules filtered by region."""
        response = client.get(
            "/api/v1/ontology-collaboration/validation/rules",
            params={"region": "CN"}
        )
        
        assert response.status_code == 200
    
    def test_create_validation_rule(self, client, validation_rule_data):
        """Test creating a validation rule."""
        response = client.post(
            "/api/v1/ontology-collaboration/validation/rules",
            json=validation_rule_data,
            params={"created_by": str(uuid4())}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == validation_rule_data["name"]
    
    def test_validate_entity(self, client):
        """Test validating an entity."""
        response = client.post(
            "/api/v1/ontology-collaboration/validation/validate",
            json={
                "entity": {
                    "统一社会信用代码": "91110000100000000X",
                    "企业名称": "测试企业"
                },
                "entity_type": "企业",
                "region": "CN"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "errors" in data
    
    def test_get_chinese_business_validators(self, client):
        """Test getting Chinese business validators."""
        response = client.get(
            "/api/v1/ontology-collaboration/validation/chinese-business"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "validators" in data


# =============================================================================
# Impact Analysis API Tests
# =============================================================================

class TestImpactAnalysisAPI:
    """Tests for Impact Analysis API endpoints."""
    
    def test_analyze_impact(self, client):
        """Test analyzing change impact."""
        response = client.post(
            "/api/v1/ontology-collaboration/impact/analyze",
            json={
                "ontology_id": str(uuid4()),
                "element_id": str(uuid4()),
                "change_type": "MODIFY",
                "proposed_changes": {"name": "新名称"}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "affected_entity_count" in data
        assert "impact_level" in data
        assert "recommendations" in data
    
    def test_count_affected_entities(self, client):
        """Test counting affected entities."""
        response = client.get(
            "/api/v1/ontology-collaboration/impact/affected-entities",
            params={"entity_type": "客户"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "entity_type" in data
        assert "affected_count" in data
    
    def test_count_affected_relations(self, client):
        """Test counting affected relations."""
        response = client.get(
            "/api/v1/ontology-collaboration/impact/affected-relations",
            params={"relation_type": "持有"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "relation_type" in data
        assert "affected_count" in data


# =============================================================================
# I18n API Tests
# =============================================================================

class TestI18nAPI:
    """Tests for I18n API endpoints."""
    
    def test_add_translation(self, client):
        """Test adding a translation."""
        element_id = str(uuid4())
        response = client.post(
            f"/api/v1/ontology-collaboration/i18n/ontology/{element_id}/translations",
            json={
                "language": "zh-CN",
                "name": "客户",
                "description": "金融客户实体",
                "help_text": "用于表示金融机构的客户"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["element_id"] == element_id
        assert data["language"] == "zh-CN"
    
    def test_add_translation_invalid_language(self, client):
        """Test adding a translation with invalid language."""
        response = client.post(
            f"/api/v1/ontology-collaboration/i18n/ontology/{uuid4()}/translations",
            json={
                "language": "invalid-lang",
                "name": "Test"
            }
        )
        
        # Should return 400 Bad Request
        assert response.status_code == 400
    
    def test_get_translation_not_found(self, client):
        """Test getting a non-existent translation."""
        response = client.get(
            f"/api/v1/ontology-collaboration/i18n/ontology/{uuid4()}/translations/zh-CN"
        )
        
        # Should return 404 Not Found
        assert response.status_code == 404
    
    def test_get_missing_translations(self, client):
        """Test getting missing translations."""
        response = client.get(
            f"/api/v1/ontology-collaboration/i18n/ontology/{uuid4()}/missing/en-US"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "missing_elements" in data
    
    def test_get_translation_coverage(self, client):
        """Test getting translation coverage."""
        response = client.get(
            f"/api/v1/ontology-collaboration/i18n/ontology/{uuid4()}/coverage"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "coverage_by_language" in data


# =============================================================================
# Audit API Tests
# =============================================================================

class TestAuditAPI:
    """Tests for Audit API endpoints."""
    
    def test_get_audit_logs(self, client):
        """Test getting audit logs."""
        response = client.get(
            "/api/v1/ontology-collaboration/audit/logs"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
    
    def test_get_audit_logs_filter_by_user(self, client):
        """Test getting audit logs filtered by user."""
        response = client.get(
            "/api/v1/ontology-collaboration/audit/logs",
            params={"user_id": str(uuid4())}
        )
        
        assert response.status_code == 200
    
    def test_verify_audit_log_integrity_not_found(self, client):
        """Test verifying integrity of non-existent audit log."""
        response = client.get(
            f"/api/v1/ontology-collaboration/audit/logs/{uuid4()}/verify"
        )
        
        # Should return 404 Not Found
        assert response.status_code == 404
    
    def test_export_audit_logs(self, client):
        """Test exporting audit logs."""
        response = client.get(
            "/api/v1/ontology-collaboration/audit/export",
            params={
                "ontology_id": str(uuid4()),
                "format": "json"
            }
        )
        
        assert response.status_code == 200


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for API error handling."""
    
    def test_invalid_json_body(self, client):
        """Test handling of invalid JSON body."""
        response = client.post(
            "/api/v1/ontology-collaboration/experts",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
    
    def test_missing_required_query_param(self, client):
        """Test handling of missing required query parameter."""
        response = client.get(
            "/api/v1/ontology-collaboration/experts/recommend"
            # Missing required ontology_area parameter
        )
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
    
    def test_invalid_uuid_format(self, client):
        """Test handling of invalid UUID format."""
        response = client.get(
            "/api/v1/ontology-collaboration/experts/not-a-uuid"
        )
        
        # Should return 500 or 422 depending on validation
        assert response.status_code in [422, 500]


# =============================================================================
# Pagination Tests
# =============================================================================

class TestPagination:
    """Tests for API pagination."""
    
    def test_pagination_defaults(self, client):
        """Test default pagination values."""
        response = client.get(
            "/api/v1/ontology-collaboration/experts"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 0
        assert data["limit"] == 20
    
    def test_pagination_custom_values(self, client):
        """Test custom pagination values."""
        response = client.get(
            "/api/v1/ontology-collaboration/experts",
            params={"offset": 10, "limit": 50}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == 10
        assert data["limit"] == 50
    
    def test_pagination_limit_exceeded(self, client):
        """Test pagination limit exceeded."""
        response = client.get(
            "/api/v1/ontology-collaboration/experts",
            params={"limit": 1000}  # Exceeds max limit of 100
        )
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422
