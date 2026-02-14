"""
Unit tests for AI Integration Workflow Designer API endpoints.

Tests workflow parsing, saving, listing, execution, and comparison endpoints.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.ai_integration_workflows import router
from src.models.ai_integration import AIGateway
from src.database.connection import Base, get_db
from src.ai_integration.auth import TokenClaims
from src.ai_integration.workflow_designer import (
    WorkflowDefinition,
    ValidationResult,
    WorkflowResult,
    ComparisonResult
)

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_claims():
    """Create test token claims."""
    from datetime import datetime, timedelta
    return TokenClaims(
        gateway_id="test-gateway-1",
        tenant_id="tenant-1",
        permissions=["data:read", "workflow:execute"],
        issued_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )


@pytest.fixture
def mock_workflow_designer():
    """Create mock workflow designer."""
    designer = MagicMock()
    designer._workflows = {}
    return designer


@pytest.fixture
def sample_workflow():
    """Create sample workflow definition."""
    return WorkflowDefinition(
        id="workflow-1",
        name="Test Workflow",
        description="Test workflow description",
        tenant_id="tenant-1",
        data_sources=[
            {
                "type": "dataset",
                "identifier": "dataset-1",
                "filters": {},
                "use_governed": True
            }
        ],
        steps=[
            {
                "step_type": "filter",
                "parameters": {"field": "status", "operator": "equals", "value": "active"},
                "description": "Filter active records"
            }
        ],
        output={"format": "json", "destination": "api_response"},
        quality_requirements={
            "min_completeness": 0.8,
            "min_accuracy": 0.9,
            "min_consistency": 0.85
        }
    )


class TestParseWorkflow:
    """Test POST /api/v1/ai-integration/workflows/parse endpoint."""
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_parse_workflow_success(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims,
        mock_workflow_designer,
        sample_workflow
    ):
        """Test successful workflow parsing."""
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        mock_workflow_designer.parse_workflow_description = AsyncMock(
            return_value=sample_workflow
        )
        mock_get_designer.return_value = mock_workflow_designer
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request
        response = client.post(
            "/api/v1/ai-integration/workflows/parse",
            json={
                "description": "Create a workflow to filter active records",
                "tenant_id": "tenant-1"
            }
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "workflow-1"
        assert data["name"] == "Test Workflow"
        assert data["tenant_id"] == "tenant-1"
        assert len(data["data_sources"]) == 1
        assert len(data["steps"]) == 1
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_parse_workflow_tenant_mismatch(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims
    ):
        """Test workflow parsing with tenant mismatch."""
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request with different tenant
        response = client.post(
            "/api/v1/ai-integration/workflows/parse",
            json={
                "description": "Create a workflow",
                "tenant_id": "different-tenant"
            }
        )
        
        # Assertions
        assert response.status_code == 403
        assert "tenant mismatch" in response.json()["detail"].lower()


class TestSaveWorkflow:
    """Test POST /api/v1/ai-integration/workflows endpoint."""
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_save_workflow_success(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims,
        mock_workflow_designer
    ):
        """Test successful workflow saving."""
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        mock_workflow_designer.validate_workflow = AsyncMock(
            return_value=ValidationResult(is_valid=True)
        )
        mock_get_designer.return_value = mock_workflow_designer
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request
        response = client.post(
            "/api/v1/ai-integration/workflows",
            json={
                "workflow": {
                    "id": "workflow-1",
                    "name": "Test Workflow",
                    "description": "Test description",
                    "tenant_id": "tenant-1",
                    "data_sources": [],
                    "steps": [],
                    "output": {"format": "json"}
                }
            }
        )
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "workflow-1"
        assert data["name"] == "Test Workflow"
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_save_workflow_validation_failure(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims,
        mock_workflow_designer
    ):
        """Test workflow saving with validation failure."""
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        mock_workflow_designer.validate_workflow = AsyncMock(
            return_value=ValidationResult(
                is_valid=False,
                errors=["Missing required field: output"]
            )
        )
        mock_get_designer.return_value = mock_workflow_designer
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request
        response = client.post(
            "/api/v1/ai-integration/workflows",
            json={
                "workflow": {
                    "id": "workflow-1",
                    "name": "Invalid Workflow",
                    "description": "Test",
                    "tenant_id": "tenant-1",
                    "data_sources": [],
                    "steps": []
                }
            }
        )
        
        # Assertions
        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"].lower()


class TestListWorkflows:
    """Test GET /api/v1/ai-integration/workflows endpoint."""
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_list_workflows_success(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims,
        mock_workflow_designer,
        sample_workflow
    ):
        """Test successful workflow listing."""
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        mock_workflow_designer._workflows = {"workflow-1": sample_workflow}
        mock_get_designer.return_value = mock_workflow_designer
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request
        response = client.get("/api/v1/ai-integration/workflows")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "workflow-1"
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_list_workflows_tenant_filtering(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims,
        mock_workflow_designer
    ):
        """Test workflow listing with tenant filtering."""
        # Create workflows for different tenants
        workflow1 = WorkflowDefinition(
            id="workflow-1",
            name="Workflow 1",
            description="Test",
            tenant_id="tenant-1",
            data_sources=[],
            steps=[],
            output={}
        )
        workflow2 = WorkflowDefinition(
            id="workflow-2",
            name="Workflow 2",
            description="Test",
            tenant_id="tenant-2",
            data_sources=[],
            steps=[],
            output={}
        )
        
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        mock_workflow_designer._workflows = {
            "workflow-1": workflow1,
            "workflow-2": workflow2
        }
        mock_get_designer.return_value = mock_workflow_designer
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request
        response = client.get("/api/v1/ai-integration/workflows")
        
        # Assertions - should only return tenant-1 workflows
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["tenant_id"] == "tenant-1"


class TestGetWorkflow:
    """Test GET /api/v1/ai-integration/workflows/{id} endpoint."""
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_get_workflow_success(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims,
        mock_workflow_designer,
        sample_workflow
    ):
        """Test successful workflow retrieval."""
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        mock_workflow_designer._workflows = {"workflow-1": sample_workflow}
        mock_get_designer.return_value = mock_workflow_designer
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request
        response = client.get("/api/v1/ai-integration/workflows/workflow-1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "workflow-1"
        assert data["name"] == "Test Workflow"
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_get_workflow_not_found(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims,
        mock_workflow_designer
    ):
        """Test workflow retrieval with non-existent ID."""
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        mock_workflow_designer._workflows = {}
        mock_get_designer.return_value = mock_workflow_designer
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request
        response = client.get("/api/v1/ai-integration/workflows/nonexistent")
        
        # Assertions
        assert response.status_code == 404


class TestExecuteWorkflow:
    """Test POST /api/v1/ai-integration/workflows/{id}/execute endpoint."""
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_execute_workflow_success(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims,
        mock_workflow_designer,
        sample_workflow
    ):
        """Test successful workflow execution."""
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        mock_workflow_designer._workflows = {"workflow-1": sample_workflow}
        
        result = WorkflowResult(
            workflow_id="workflow-1",
            execution_id="exec-1",
            status="completed",
            data=[{"id": 1, "status": "active"}],
            quality_metrics={
                "completeness": 0.95,
                "accuracy": 0.92,
                "consistency": 0.90
            },
            execution_time_ms=150.5
        )
        mock_workflow_designer.execute_workflow = AsyncMock(return_value=result)
        mock_get_designer.return_value = mock_workflow_designer
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request
        response = client.post(
            "/api/v1/ai-integration/workflows/workflow-1/execute",
            json={"use_governed_data": True}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "workflow-1"
        assert data["status"] == "completed"
        assert data["quality_metrics"]["completeness"] == 0.95


class TestCompareWorkflowResults:
    """Test POST /api/v1/ai-integration/workflows/{id}/compare endpoint."""
    
    @patch("src.api.ai_integration_workflows.get_current_gateway")
    @patch("src.api.ai_integration_workflows.get_workflow_designer")
    def test_compare_workflow_results_success(
        self,
        mock_get_designer,
        mock_get_gateway,
        test_claims,
        mock_workflow_designer,
        sample_workflow
    ):
        """Test successful workflow comparison."""
        # Setup mocks
        mock_get_gateway.return_value = test_claims
        mock_workflow_designer._workflows = {"workflow-1": sample_workflow}
        
        governed_result = WorkflowResult(
            workflow_id="workflow-1",
            execution_id="exec-1",
            status="completed",
            data=[{"id": 1}],
            quality_metrics={
                "completeness": 0.95,
                "accuracy": 0.92,
                "overall_quality": 0.93
            }
        )
        
        raw_result = WorkflowResult(
            workflow_id="workflow-1",
            execution_id="exec-2",
            status="completed",
            data=[{"id": 1}],
            quality_metrics={
                "completeness": 0.75,
                "accuracy": 0.78,
                "overall_quality": 0.76
            }
        )
        
        comparison = ComparisonResult(
            workflow_id="workflow-1",
            governed_result=governed_result,
            raw_result=raw_result,
            comparison_metrics={
                "governed_metrics": governed_result.quality_metrics,
                "raw_metrics": raw_result.quality_metrics,
                "improvements": {
                    "completeness": 0.20,
                    "accuracy": 0.14,
                    "overall": 0.17
                },
                "improvement_percentage": 17.0
            }
        )
        
        mock_workflow_designer.compare_results = AsyncMock(return_value=comparison)
        mock_get_designer.return_value = mock_workflow_designer
        
        # Create test client
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Make request
        response = client.post(
            "/api/v1/ai-integration/workflows/workflow-1/compare"
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "workflow-1"
        assert "governed_result" in data
        assert "raw_result" in data
        assert "comparison_metrics" in data
        assert data["comparison_metrics"]["improvement_percentage"] == 17.0
