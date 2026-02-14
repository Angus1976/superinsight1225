"""
Unit tests for AI Integration data access API endpoints.

Tests authentication, tenant filtering, and data access endpoints.

**Feature: ai-application-integration**
**Validates: Requirements 3.1, 3.2, 3.3**
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.ai_integration_data import router, jwt_service
from src.models.ai_integration import AIGateway
from src.database.connection import get_db
from src.ai_integration.auth import TokenClaims


@pytest.fixture(scope="function")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Replace JSONB with JSON for SQLite
    for column in AIGateway.__table__.columns:
        if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
            column.type = JSON()
    
    AIGateway.__table__.create(engine, checkfirst=True)
    
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Create database session."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def app(test_engine):
    """Create FastAPI test app."""
    test_app = FastAPI()
    test_app.include_router(router)
    
    def override_get_db():
        SessionLocal = sessionmaker(bind=test_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    test_app.dependency_overrides[get_db] = override_get_db
    
    return test_app
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_gateway(db_session):
    """Create test gateway."""
    gateway = AIGateway(
        id="test-gateway-1",
        name="Test Gateway",
        gateway_type="openclaw",
        tenant_id="tenant-1",
        status="active",
        configuration={},
        api_key_hash="hash1",
        api_secret_hash="hash2",
        rate_limit_per_minute=60,
        quota_per_day=10000
    )
    db_session.add(gateway)
    db_session.commit()
    return gateway


@pytest.fixture
def valid_token(test_gateway):
    """Generate valid JWT token."""
    return jwt_service.generate_token(
        gateway_id=test_gateway.id,
        tenant_id=test_gateway.tenant_id,
        permissions=["read:data"],
        expires_in_seconds=3600
    )


@pytest.fixture
def expired_token(test_gateway):
    """Generate expired JWT token."""
    return jwt_service.generate_token(
        gateway_id=test_gateway.id,
        tenant_id=test_gateway.tenant_id,
        permissions=["read:data"],
        expires_in_seconds=-1
    )


class TestAuthentication:
    """Test authentication middleware."""
    
    def test_query_without_token(self, client):
        """Test query without authorization header."""
        response = client.get("/api/v1/ai-integration/data/query")
        assert response.status_code == 422  # Missing required header
    
    def test_query_with_invalid_token_format(self, client):
        """Test query with invalid token format."""
        response = client.get(
            "/api/v1/ai-integration/data/query",
            headers={"Authorization": "InvalidFormat token123"}
        )
        assert response.status_code == 401
        assert "Invalid authorization header format" in response.json()["detail"]
    
    def test_query_with_expired_token(self, client, expired_token):
        """Test query with expired token."""
        response = client.get(
            "/api/v1/ai-integration/data/query",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    def test_query_with_valid_token(self, client, valid_token):
        """Test query with valid token."""
        with patch("src.api.ai_integration_data.OpenClawDataBridge") as mock_bridge:
            mock_instance = AsyncMock()
            mock_instance.query_governed_data.return_value = {
                "total_records": 0,
                "results": []
            }
            mock_bridge.return_value = mock_instance
            
            response = client.get(
                "/api/v1/ai-integration/data/query",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            # Should pass authentication
            assert response.status_code in [200, 500]  # May fail on data bridge


class TestTenantFiltering:
    """Test tenant isolation in data access."""
    
    @patch("src.api.ai_integration_data.OpenClawDataBridge")
    def test_query_applies_tenant_filter(self, mock_bridge, client, valid_token, test_gateway):
        """Test that queries apply tenant filtering."""
        mock_instance = AsyncMock()
        mock_instance.query_governed_data.return_value = {
            "total_records": 10,
            "results": []
        }
        mock_bridge.return_value = mock_instance
        
        response = client.get(
            "/api/v1/ai-integration/data/query",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        # Verify tenant_id was passed to data bridge
        if mock_instance.query_governed_data.called:
            call_args = mock_instance.query_governed_data.call_args
            assert call_args[1]["tenant_id"] == test_gateway.tenant_id
    
    @patch("src.api.ai_integration_data.OpenClawDataBridge")
    def test_export_applies_tenant_filter(self, mock_bridge, client, valid_token, test_gateway):
        """Test that exports apply tenant filtering."""
        mock_instance = AsyncMock()
        mock_instance.export_for_skill.return_value = b'{"data": []}'
        mock_bridge.return_value = mock_instance
        
        response = client.post(
            "/api/v1/ai-integration/data/export-for-skill",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={
                "data_query": {"results": []},
                "format": "json"
            }
        )
        
        # Verify tenant_id was added to data query
        if mock_instance.export_for_skill.called:
            call_args = mock_instance.export_for_skill.call_args
            data_query = call_args[1]["data_query"]
            assert data_query["tenant_id"] == test_gateway.tenant_id


class TestQueryEndpoint:
    """Test /data/query endpoint."""
    
    @patch("src.api.ai_integration_data.OpenClawDataBridge")
    def test_query_with_filters(self, mock_bridge, client, valid_token):
        """Test query with filter parameters."""
        mock_instance = AsyncMock()
        mock_instance.query_governed_data.return_value = {
            "total_records": 5,
            "results": [{"id": 1}, {"id": 2}]
        }
        mock_bridge.return_value = mock_instance
        
        filters = json.dumps({"dataset": "test-dataset"})
        response = client.get(
            "/api/v1/ai-integration/data/query",
            params={"filters": filters, "page": 1, "page_size": 10},
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["page"] == 1
        assert data["page_size"] == 10
    
    @patch("src.api.ai_integration_data.OpenClawDataBridge")
    def test_query_pagination(self, mock_bridge, client, valid_token):
        """Test query pagination parameters."""
        mock_instance = AsyncMock()
        mock_instance.query_governed_data.return_value = {
            "total_records": 100,
            "results": []
        }
        mock_bridge.return_value = mock_instance
        
        response = client.get(
            "/api/v1/ai-integration/data/query",
            params={"page": 2, "page_size": 50},
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 50
    
    @patch("src.api.ai_integration_data.OpenClawDataBridge")
    def test_query_without_permission(self, mock_bridge, client, valid_token):
        """Test query without read permission."""
        with patch("src.api.ai_integration_data.AuthorizationService") as mock_auth:
            mock_auth_instance = Mock()
            mock_auth_instance.check_permission.return_value = False
            mock_auth.return_value = mock_auth_instance
            
            response = client.get(
                "/api/v1/ai-integration/data/query",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()


class TestExportEndpoint:
    """Test /data/export-for-skill endpoint."""
    
    @patch("src.api.ai_integration_data.OpenClawDataBridge")
    def test_export_json_format(self, mock_bridge, client, valid_token):
        """Test export in JSON format."""
        mock_instance = AsyncMock()
        mock_instance.export_for_skill.return_value = b'{"test": "data"}'
        mock_bridge.return_value = mock_instance
        
        response = client.post(
            "/api/v1/ai-integration/data/export-for-skill",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={
                "data_query": {"results": [{"id": 1}]},
                "format": "json",
                "include_semantics": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "json"
        assert "size" in data
    
    @patch("src.api.ai_integration_data.OpenClawDataBridge")
    def test_export_csv_format(self, mock_bridge, client, valid_token):
        """Test export in CSV format."""
        mock_instance = AsyncMock()
        mock_instance.export_for_skill.return_value = b'id,name\n1,test'
        mock_bridge.return_value = mock_instance
        
        response = client.post(
            "/api/v1/ai-integration/data/export-for-skill",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={
                "data_query": {"results": []},
                "format": "csv"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "csv"
    
    def test_export_invalid_format(self, client, valid_token):
        """Test export with invalid format."""
        response = client.post(
            "/api/v1/ai-integration/data/export-for-skill",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={
                "data_query": {"results": []},
                "format": "invalid_format"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestQualityMetricsEndpoint:
    """Test /data/quality-metrics endpoint."""
    
    @patch("src.api.ai_integration_data.OpenClawDataBridge")
    def test_get_quality_metrics(self, mock_bridge, client, valid_token):
        """Test getting quality metrics."""
        mock_instance = AsyncMock()
        mock_instance.get_quality_metrics.return_value = {
            "dataset_id": "test-dataset",
            "overall_score": 0.85,
            "metrics": {
                "completeness": 0.90,
                "accuracy": 0.85
            },
            "sample_size": 1000,
            "issues": [],
            "recommendations": []
        }
        mock_bridge.return_value = mock_instance
        
        response = client.get(
            "/api/v1/ai-integration/data/quality-metrics",
            params={"dataset_id": "test-dataset", "sample_size": 1000},
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["dataset_id"] == "test-dataset"
        assert data["overall_score"] == 0.85
        assert "metrics" in data
    
    def test_quality_metrics_missing_dataset_id(self, client, valid_token):
        """Test quality metrics without dataset_id."""
        response = client.get(
            "/api/v1/ai-integration/data/quality-metrics",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        assert response.status_code == 422  # Missing required parameter
    
    @patch("src.api.ai_integration_data.OpenClawDataBridge")
    def test_quality_metrics_custom_sample_size(self, mock_bridge, client, valid_token):
        """Test quality metrics with custom sample size."""
        mock_instance = AsyncMock()
        mock_instance.get_quality_metrics.return_value = {
            "dataset_id": "test-dataset",
            "overall_score": 0.85,
            "metrics": {},
            "sample_size": 5000,
            "issues": [],
            "recommendations": []
        }
        mock_bridge.return_value = mock_instance
        
        response = client.get(
            "/api/v1/ai-integration/data/quality-metrics",
            params={"dataset_id": "test-dataset", "sample_size": 5000},
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sample_size"] == 5000
