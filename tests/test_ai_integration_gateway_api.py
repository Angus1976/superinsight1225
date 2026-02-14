"""
Unit tests for AI Gateway Management API endpoints.

Tests registration, listing, updating, deactivation, deployment,
and health check endpoints with tenant isolation.

**Feature: ai-application-integration**
**Validates: Requirements 2.1, 2.3, 2.4**
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine, JSON, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.ai_integration_gateways import router
from src.models.ai_integration import AIGateway, AISkill
from src.database.connection import Base, get_db
from src.ai_integration.gateway_manager import (
    GatewayRegistrationError,
    GatewayNotFoundError,
    ConfigurationValidationError
)


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine shared across the test."""
    # Use StaticPool to ensure single connection for in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool  # Use StaticPool for single connection
    )
    
    # Replace JSONB with JSON for SQLite compatibility
    from src.models.ai_integration import AIGateway, AISkill, AIAuditLog
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for column in table.columns:
            if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                column.type = JSON()
    
    # Create all tables
    AIGateway.__table__.create(engine, checkfirst=True)
    AISkill.__table__.create(engine, checkfirst=True)
    AIAuditLog.__table__.create(engine, checkfirst=True)
    
    yield engine
    
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Create a database session for testing."""
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
    
    # Override database dependency to use the same engine
    def override_get_db():
        SessionLocal = sessionmaker(bind=test_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    test_app.dependency_overrides[get_db] = override_get_db
    
    return test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_gateway_config():
    """Provide valid gateway configuration."""
    return {
        'channels': [
            {
                'channel_type': 'whatsapp',
                'enabled': True,
                'credentials': {'api_key': 'test_key'},
                'settings': {}
            }
        ],
        'network_settings': {
            'host': 'localhost',
            'port': 3000,
            'protocol': 'http'
        },
        'custom_settings': {}
    }


@pytest.fixture
def sample_gateway(db_session, valid_gateway_config):
    """Create a sample gateway in the database."""
    gateway = AIGateway(
        name="Test Gateway",
        gateway_type="openclaw",
        tenant_id="tenant_123",
        configuration=valid_gateway_config,
        api_key_hash="hashed_key",
        api_secret_hash="hashed_secret",
        status="inactive"
    )
    db_session.add(gateway)
    db_session.commit()
    db_session.refresh(gateway)
    return gateway


class TestRegisterGateway:
    """Test POST /api/v1/ai-integration/gateways endpoint."""
    
    def test_register_gateway_success(self, client, valid_gateway_config):
        """Test successful gateway registration."""
        request_data = {
            'name': 'New Gateway',
            'gateway_type': 'openclaw',
            'tenant_id': 'tenant_456',
            'configuration': valid_gateway_config,
            'rate_limit_per_minute': 100,
            'quota_per_day': 50000
        }
        
        response = client.post('/api/v1/ai-integration/gateways', json=request_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert 'gateway' in data
        assert 'credentials' in data
        
        gateway = data['gateway']
        assert gateway['name'] == 'New Gateway'
        assert gateway['gateway_type'] == 'openclaw'
        assert gateway['tenant_id'] == 'tenant_456'
        assert gateway['status'] == 'inactive'
        assert gateway['rate_limit_per_minute'] == 100
        assert gateway['quota_per_day'] == 50000
        
        credentials = data['credentials']
        assert 'api_key' in credentials
        assert 'api_secret' in credentials
        assert len(credentials['api_key']) > 0
        assert len(credentials['api_secret']) > 0
    
    def test_register_gateway_invalid_config(self, client):
        """Test registration with invalid configuration."""
        request_data = {
            'name': 'Invalid Gateway',
            'gateway_type': 'openclaw',
            'tenant_id': 'tenant_789',
            'configuration': {'invalid': 'config'}  # Missing required fields
        }
        
        response = client.post('/api/v1/ai-integration/gateways', json=request_data)
        
        assert response.status_code == 400
        assert 'Configuration validation failed' in response.json()['detail']
    
    def test_register_gateway_duplicate_name(self, client, sample_gateway, valid_gateway_config):
        """Test registration with duplicate gateway name in same tenant."""
        request_data = {
            'name': 'Test Gateway',  # Same as sample_gateway
            'gateway_type': 'openclaw',
            'tenant_id': 'tenant_123',  # Same tenant
            'configuration': valid_gateway_config
        }
        
        response = client.post('/api/v1/ai-integration/gateways', json=request_data)
        
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']
    
    def test_register_gateway_empty_name(self, client, valid_gateway_config):
        """Test registration with empty name."""
        request_data = {
            'name': '',
            'gateway_type': 'openclaw',
            'tenant_id': 'tenant_123',
            'configuration': valid_gateway_config
        }
        
        response = client.post('/api/v1/ai-integration/gateways', json=request_data)
        
        # FastAPI returns 422 for validation errors
        assert response.status_code == 422


class TestListGateways:
    """Test GET /api/v1/ai-integration/gateways endpoint."""
    
    def test_list_all_gateways(self, client, db_session, valid_gateway_config):
        """Test listing all gateways."""
        # Create multiple gateways
        for i in range(3):
            gateway = AIGateway(
                name=f"Gateway {i}",
                gateway_type="openclaw",
                tenant_id=f"tenant_{i}",
                configuration=valid_gateway_config,
                api_key_hash=f"hash_{i}",
                api_secret_hash=f"secret_{i}"
            )
            db_session.add(gateway)
        db_session.commit()
        
        response = client.get('/api/v1/ai-integration/gateways')
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all('id' in g for g in data)
        assert all('name' in g for g in data)
    
    def test_list_gateways_with_tenant_filter(self, client, db_session, valid_gateway_config):
        """Test listing gateways filtered by tenant."""
        # Create gateways for different tenants
        for i in range(3):
            gateway = AIGateway(
                name=f"Gateway {i}",
                gateway_type="openclaw",
                tenant_id="tenant_123" if i < 2 else "tenant_456",
                configuration=valid_gateway_config,
                api_key_hash=f"hash_{i}",
                api_secret_hash=f"secret_{i}"
            )
            db_session.add(gateway)
        db_session.commit()
        
        response = client.get('/api/v1/ai-integration/gateways?tenant_id=tenant_123')
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(g['tenant_id'] == 'tenant_123' for g in data)
    
    def test_list_gateways_with_type_filter(self, client, db_session, valid_gateway_config):
        """Test listing gateways filtered by type."""
        # Create gateways of different types
        types = ['openclaw', 'openclaw', 'custom']
        for i, gw_type in enumerate(types):
            gateway = AIGateway(
                name=f"Gateway {i}",
                gateway_type=gw_type,
                tenant_id="tenant_123",
                configuration=valid_gateway_config,
                api_key_hash=f"hash_{i}",
                api_secret_hash=f"secret_{i}"
            )
            db_session.add(gateway)
        db_session.commit()
        
        response = client.get('/api/v1/ai-integration/gateways?gateway_type=openclaw')
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(g['gateway_type'] == 'openclaw' for g in data)
    
    def test_list_gateways_with_pagination(self, client, db_session, valid_gateway_config):
        """Test listing gateways with pagination."""
        # Create 5 gateways
        for i in range(5):
            gateway = AIGateway(
                name=f"Gateway {i}",
                gateway_type="openclaw",
                tenant_id="tenant_123",
                configuration=valid_gateway_config,
                api_key_hash=f"hash_{i}",
                api_secret_hash=f"secret_{i}"
            )
            db_session.add(gateway)
        db_session.commit()
        
        response = client.get('/api/v1/ai-integration/gateways?skip=2&limit=2')
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestGetGateway:
    """Test GET /api/v1/ai-integration/gateways/{gateway_id} endpoint."""
    
    def test_get_gateway_success(self, client, sample_gateway):
        """Test getting gateway details."""
        response = client.get(f'/api/v1/ai-integration/gateways/{sample_gateway.id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == sample_gateway.id
        assert data['name'] == sample_gateway.name
        assert data['gateway_type'] == sample_gateway.gateway_type
        assert data['tenant_id'] == sample_gateway.tenant_id
    
    def test_get_gateway_not_found(self, client):
        """Test getting non-existent gateway."""
        response = client.get('/api/v1/ai-integration/gateways/nonexistent_id')
        
        assert response.status_code == 404
        assert 'not found' in response.json()['detail']


class TestUpdateGateway:
    """Test PUT /api/v1/ai-integration/gateways/{gateway_id} endpoint."""
    
    def test_update_gateway_success(self, client, sample_gateway):
        """Test successful gateway configuration update."""
        new_config = {
            'channels': [
                {
                    'channel_type': 'telegram',
                    'enabled': True,
                    'credentials': {'bot_token': 'new_token'},
                    'settings': {}
                }
            ],
            'network_settings': {
                'host': 'newhost',
                'port': 4000,
                'protocol': 'https'
            }
        }
        
        request_data = {
            'configuration': new_config,
            'updated_by': 'admin_user'
        }
        
        response = client.put(
            f'/api/v1/ai-integration/gateways/{sample_gateway.id}',
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == sample_gateway.id
        
        # Verify configuration was updated
        assert 'telegram' in str(data['configuration'])
    
    def test_update_gateway_invalid_config(self, client, sample_gateway):
        """Test update with invalid configuration."""
        request_data = {
            'configuration': {'invalid': 'config'}
        }
        
        response = client.put(
            f'/api/v1/ai-integration/gateways/{sample_gateway.id}',
            json=request_data
        )
        
        assert response.status_code == 400
        assert 'Configuration validation failed' in response.json()['detail']
    
    def test_update_gateway_not_found(self, client):
        """Test updating non-existent gateway."""
        request_data = {
            'configuration': {
                'channels': [{'channel_type': 'test', 'enabled': True}]
            }
        }
        
        response = client.put(
            '/api/v1/ai-integration/gateways/nonexistent_id',
            json=request_data
        )
        
        assert response.status_code == 404


class TestDeactivateGateway:
    """Test DELETE /api/v1/ai-integration/gateways/{gateway_id} endpoint."""
    
    def test_deactivate_gateway_success(self, client, sample_gateway, db_session):
        """Test successful gateway deactivation."""
        # Add a skill to verify it gets disabled
        skill = AISkill(
            gateway_id=sample_gateway.id,
            name="Test Skill",
            version="1.0.0",
            code_path="/path/to/skill",
            configuration={},
            dependencies=[],
            status="deployed"
        )
        db_session.add(skill)
        db_session.commit()
        
        response = client.delete(f'/api/v1/ai-integration/gateways/{sample_gateway.id}')
        
        assert response.status_code == 204
        
        # Verify gateway was deactivated
        db_session.refresh(sample_gateway)
        assert sample_gateway.status == "inactive"
        assert sample_gateway.api_key_hash == "REVOKED"
        assert sample_gateway.api_secret_hash == "REVOKED"
        
        # Verify skill was disabled
        db_session.refresh(skill)
        assert skill.status == "disabled"
    
    def test_deactivate_gateway_not_found(self, client):
        """Test deactivating non-existent gateway."""
        response = client.delete('/api/v1/ai-integration/gateways/nonexistent_id')
        
        assert response.status_code == 404


class TestDeployGateway:
    """Test POST /api/v1/ai-integration/gateways/{gateway_id}/deploy endpoint."""
    
    def test_deploy_gateway_success(self, client, sample_gateway, db_session):
        """Test successful gateway deployment."""
        response = client.post(f'/api/v1/ai-integration/gateways/{sample_gateway.id}/deploy')
        
        assert response.status_code == 200
        data = response.json()
        assert data['gateway_id'] == sample_gateway.id
        assert data['status'] == 'deployed'
        assert 'deployed successfully' in data['message']
        
        # Verify gateway status was updated
        db_session.refresh(sample_gateway)
        assert sample_gateway.status == "active"
        assert sample_gateway.last_active_at is not None
    
    def test_deploy_gateway_not_found(self, client):
        """Test deploying non-existent gateway."""
        response = client.post('/api/v1/ai-integration/gateways/nonexistent_id/deploy')
        
        assert response.status_code == 404


class TestGatewayHealth:
    """Test GET /api/v1/ai-integration/gateways/{gateway_id}/health endpoint."""
    
    def test_health_check_active_gateway(self, client, sample_gateway, db_session):
        """Test health check for active gateway."""
        sample_gateway.status = "active"
        db_session.commit()
        
        response = client.get(f'/api/v1/ai-integration/gateways/{sample_gateway.id}/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['gateway_id'] == sample_gateway.id
        assert data['status'] == 'active'
        assert data['healthy'] is True
        assert 'last_check' in data
    
    def test_health_check_inactive_gateway(self, client, sample_gateway):
        """Test health check for inactive gateway."""
        response = client.get(f'/api/v1/ai-integration/gateways/{sample_gateway.id}/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['gateway_id'] == sample_gateway.id
        assert data['status'] == 'inactive'
        assert data['healthy'] is False
    
    def test_health_check_not_found(self, client):
        """Test health check for non-existent gateway."""
        response = client.get('/api/v1/ai-integration/gateways/nonexistent_id/health')
        
        assert response.status_code == 404
