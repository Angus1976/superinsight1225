"""
Unit tests for AI Skill Management API endpoints.

Tests skill package creation, listing, deployment, and hot-reloading
endpoints with proper error handling.

**Feature: ai-application-integration**
**Validates: Requirements 5.1, 5.6**
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.ai_integration_skills import router
from src.models.ai_integration import AIGateway, AISkill
from src.database.connection import Base, get_db
from src.ai_integration.skill_manager import (
    SkillPackageError,
    SkillDeploymentError,
    SkillNotFoundError
)


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Replace JSONB with JSON for SQLite
    from src.models.ai_integration import AIGateway, AISkill, AIAuditLog
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for column in table.columns:
            if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                column.type = JSON()
    
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
def temp_skills_dir(tmp_path):
    """Create temporary skills directory."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return str(skills_dir)


@pytest.fixture
def app(test_engine, temp_skills_dir, monkeypatch):
    """Create FastAPI test app."""
    # Patch SkillManager to use temp directory
    from src.ai_integration import skill_manager
    original_init = skill_manager.SkillManager.__init__
    
    def patched_init(self, db, skills_base_path=None):
        original_init(self, db, temp_skills_dir)
    
    monkeypatch.setattr(skill_manager.SkillManager, '__init__', patched_init)
    
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


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_gateway(db_session):
    """Create a sample gateway for testing."""
    gateway = AIGateway(
        id="test-gateway-1",
        name="Test Gateway",
        gateway_type="openclaw",
        tenant_id="tenant-1",
        status="active",
        configuration={"channels": []},
        api_key_hash="hash1",
        api_secret_hash="hash2",
        rate_limit_per_minute=60,
        quota_per_day=10000
    )
    db_session.add(gateway)
    db_session.commit()
    return gateway


@pytest.fixture
def valid_skill_request():
    """Provide valid skill creation request."""
    return {
        "name": "superinsight-skill",
        "version": "1.0.0",
        "skill_code": "module.exports = { handle: async (msg) => 'Hello' };",
        "dependencies": ["axios@1.0.0"],
        "configuration": {
            "name": "superinsight-skill",
            "description": "SuperInsight data access skill",
            "entry_point": "index.js",
            "environment_variables": {"API_URL": "http://localhost:18080"},
            "permissions": ["data:read"],
            "timeout_seconds": 30
        }
    }


# ============================================================================
# Test: Create Skill Package
# ============================================================================

def test_create_skill_package_success(client, valid_skill_request):
    """Test successful skill package creation."""
    response = client.post(
        "/api/v1/ai-integration/skills",
        json=valid_skill_request
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "superinsight-skill"
    assert data["version"] == "1.0.0"
    assert "code_path" in data
    assert data["message"] == "Skill package created successfully"


def test_create_skill_package_empty_name(client, valid_skill_request):
    """Test skill creation with empty name."""
    valid_skill_request["name"] = ""
    
    response = client.post(
        "/api/v1/ai-integration/skills",
        json=valid_skill_request
    )
    
    # Pydantic validation returns 422
    assert response.status_code == 422


def test_create_skill_package_empty_code(client, valid_skill_request):
    """Test skill creation with empty code."""
    valid_skill_request["skill_code"] = ""
    
    response = client.post(
        "/api/v1/ai-integration/skills",
        json=valid_skill_request
    )
    
    # Pydantic validation returns 422
    assert response.status_code == 422


# ============================================================================
# Test: List Skills
# ============================================================================

def test_list_skills_empty(client):
    """Test listing skills when none exist."""
    response = client.get("/api/v1/ai-integration/skills")
    
    assert response.status_code == 200
    assert response.json() == []


def test_list_skills_with_data(client, db_session, sample_gateway):
    """Test listing skills with existing data."""
    skill1 = AISkill(
        id="skill-1",
        gateway_id=sample_gateway.id,
        name="skill-1",
        version="1.0.0",
        code_path="/app/skills/skill-1",
        configuration={"name": "skill-1"},
        dependencies=[],
        status="deployed"
    )
    skill2 = AISkill(
        id="skill-2",
        gateway_id=sample_gateway.id,
        name="skill-2",
        version="1.0.0",
        code_path="/app/skills/skill-2",
        configuration={"name": "skill-2"},
        dependencies=[],
        status="deployed"
    )
    db_session.add_all([skill1, skill2])
    db_session.commit()
    
    response = client.get("/api/v1/ai-integration/skills")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_skills_filter_by_gateway(client, db_session, sample_gateway):
    """Test filtering skills by gateway ID."""
    gateway2 = AIGateway(
        id="test-gateway-2",
        name="Test Gateway 2",
        gateway_type="openclaw",
        tenant_id="tenant-1",
        status="active",
        configuration={},
        api_key_hash="hash3",
        api_secret_hash="hash4"
    )
    db_session.add(gateway2)
    
    skill1 = AISkill(
        id="skill-1",
        gateway_id=sample_gateway.id,
        name="skill-1",
        version="1.0.0",
        code_path="/app/skills/skill-1",
        configuration={},
        dependencies=[],
        status="deployed"
    )
    skill2 = AISkill(
        id="skill-2",
        gateway_id=gateway2.id,
        name="skill-2",
        version="1.0.0",
        code_path="/app/skills/skill-2",
        configuration={},
        dependencies=[],
        status="deployed"
    )
    db_session.add_all([skill1, skill2])
    db_session.commit()
    
    response = client.get(
        f"/api/v1/ai-integration/skills?gateway_id={sample_gateway.id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["gateway_id"] == sample_gateway.id


def test_list_skills_pagination(client, db_session, sample_gateway):
    """Test skill listing pagination."""
    for i in range(5):
        skill = AISkill(
            id=f"skill-{i}",
            gateway_id=sample_gateway.id,
            name=f"skill-{i}",
            version="1.0.0",
            code_path=f"/app/skills/skill-{i}",
            configuration={},
            dependencies=[],
            status="deployed"
        )
        db_session.add(skill)
    db_session.commit()
    
    response = client.get("/api/v1/ai-integration/skills?skip=2&limit=2")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


# ============================================================================
# Test: Deploy Skill
# ============================================================================

def test_deploy_skill_success(client, db_session, sample_gateway):
    """Test successful skill deployment."""
    skill = AISkill(
        id="skill-1",
        gateway_id="other-gateway",
        name="test-skill",
        version="1.0.0",
        code_path="/app/skills/test-skill",
        configuration={"name": "test-skill"},
        dependencies=[],
        status="packaged"
    )
    db_session.add(skill)
    db_session.commit()
    
    response = client.post(
        "/api/v1/ai-integration/skills/skill-1/deploy",
        json={"gateway_id": sample_gateway.id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deployed"
    assert data["gateway_id"] == sample_gateway.id


def test_deploy_skill_not_found(client, sample_gateway):
    """Test deploying non-existent skill."""
    response = client.post(
        "/api/v1/ai-integration/skills/nonexistent/deploy",
        json={"gateway_id": sample_gateway.id}
    )
    
    assert response.status_code == 404


def test_deploy_skill_inactive_gateway(client, db_session):
    """Test deploying to inactive gateway."""
    gateway = AIGateway(
        id="inactive-gateway",
        name="Inactive Gateway",
        gateway_type="openclaw",
        tenant_id="tenant-1",
        status="inactive",
        configuration={},
        api_key_hash="hash",
        api_secret_hash="hash"
    )
    db_session.add(gateway)
    
    skill = AISkill(
        id="skill-1",
        gateway_id="other-gateway",
        name="test-skill",
        version="1.0.0",
        code_path="/app/skills/test-skill",
        configuration={},
        dependencies=[],
        status="packaged"
    )
    db_session.add(skill)
    db_session.commit()
    
    response = client.post(
        "/api/v1/ai-integration/skills/skill-1/deploy",
        json={"gateway_id": "inactive-gateway"}
    )
    
    assert response.status_code == 400


# ============================================================================
# Test: Hot Reload Skill
# ============================================================================

def test_hot_reload_skill_success(client, db_session, sample_gateway):
    """Test successful skill hot reload."""
    skill = AISkill(
        id="skill-1",
        gateway_id=sample_gateway.id,
        name="test-skill",
        version="1.0.0",
        code_path="/app/skills/test-skill",
        configuration={},
        dependencies=[],
        status="deployed",
        deployed_at=datetime.utcnow()
    )
    db_session.add(skill)
    db_session.commit()
    
    response = client.post(
        f"/api/v1/ai-integration/skills/skill-1/reload?gateway_id={sample_gateway.id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reloaded"
    assert data["skill_id"] == "skill-1"
    assert data["gateway_id"] == sample_gateway.id


def test_hot_reload_skill_not_found(client, sample_gateway):
    """Test hot reloading non-existent skill."""
    response = client.post(
        f"/api/v1/ai-integration/skills/nonexistent/reload?gateway_id={sample_gateway.id}"
    )
    
    assert response.status_code == 404


def test_hot_reload_skill_wrong_gateway(client, db_session, sample_gateway):
    """Test hot reloading skill with wrong gateway ID."""
    skill = AISkill(
        id="skill-1",
        gateway_id="other-gateway",
        name="test-skill",
        version="1.0.0",
        code_path="/app/skills/test-skill",
        configuration={},
        dependencies=[],
        status="deployed"
    )
    db_session.add(skill)
    db_session.commit()
    
    response = client.post(
        f"/api/v1/ai-integration/skills/skill-1/reload?gateway_id={sample_gateway.id}"
    )
    
    assert response.status_code == 404
    assert "not found for gateway" in response.json()["detail"]


# ============================================================================
# Test: Additional Edge Cases
# ============================================================================

def test_create_skill_package_with_complex_config(client, valid_skill_request):
    """Test skill creation with complex configuration."""
    valid_skill_request["configuration"]["environment_variables"] = {
        "API_URL": "http://localhost:18080",
        "API_KEY": "test-key",
        "TIMEOUT": "30"
    }
    valid_skill_request["configuration"]["permissions"] = [
        "data:read",
        "data:write",
        "gateway:manage"
    ]
    
    response = client.post(
        "/api/v1/ai-integration/skills",
        json=valid_skill_request
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "environment_variables" in data["configuration"]
    assert len(data["configuration"]["permissions"]) == 3


def test_create_skill_package_with_multiple_dependencies(client, valid_skill_request):
    """Test skill creation with multiple dependencies."""
    valid_skill_request["dependencies"] = [
        "axios@1.0.0",
        "lodash@4.17.21",
        "@types/node@18.0.0",
        "express"
    ]
    
    response = client.post(
        "/api/v1/ai-integration/skills",
        json=valid_skill_request
    )
    
    assert response.status_code == 201
    data = response.json()
    assert len(data["dependencies"]) == 4


def test_list_skills_filter_by_status(client, db_session, sample_gateway):
    """Test filtering skills by status."""
    deployed_skill = AISkill(
        id="skill-1",
        gateway_id=sample_gateway.id,
        name="deployed-skill",
        version="1.0.0",
        code_path="/app/skills/deployed",
        configuration={},
        dependencies=[],
        status="deployed"
    )
    packaged_skill = AISkill(
        id="skill-2",
        gateway_id=sample_gateway.id,
        name="packaged-skill",
        version="1.0.0",
        code_path="/app/skills/packaged",
        configuration={},
        dependencies=[],
        status="packaged"
    )
    db_session.add_all([deployed_skill, packaged_skill])
    db_session.commit()
    
    response = client.get("/api/v1/ai-integration/skills?status=deployed")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "deployed"


def test_list_skills_combined_filters(client, db_session, sample_gateway):
    """Test combining gateway and status filters."""
    gateway2 = AIGateway(
        id="test-gateway-2",
        name="Test Gateway 2",
        gateway_type="openclaw",
        tenant_id="tenant-1",
        status="active",
        configuration={},
        api_key_hash="hash3",
        api_secret_hash="hash4"
    )
    db_session.add(gateway2)
    
    skill1 = AISkill(
        id="skill-1",
        gateway_id=sample_gateway.id,
        name="skill-1",
        version="1.0.0",
        code_path="/app/skills/skill-1",
        configuration={},
        dependencies=[],
        status="deployed"
    )
    skill2 = AISkill(
        id="skill-2",
        gateway_id=sample_gateway.id,
        name="skill-2",
        version="1.0.0",
        code_path="/app/skills/skill-2",
        configuration={},
        dependencies=[],
        status="packaged"
    )
    skill3 = AISkill(
        id="skill-3",
        gateway_id=gateway2.id,
        name="skill-3",
        version="1.0.0",
        code_path="/app/skills/skill-3",
        configuration={},
        dependencies=[],
        status="deployed"
    )
    db_session.add_all([skill1, skill2, skill3])
    db_session.commit()
    
    response = client.get(
        f"/api/v1/ai-integration/skills?gateway_id={sample_gateway.id}&status=deployed"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["gateway_id"] == sample_gateway.id
    assert data[0]["status"] == "deployed"


def test_deploy_skill_gateway_not_found(client, db_session):
    """Test deploying to non-existent gateway."""
    skill = AISkill(
        id="skill-1",
        gateway_id="other-gateway",
        name="test-skill",
        version="1.0.0",
        code_path="/app/skills/test-skill",
        configuration={},
        dependencies=[],
        status="packaged"
    )
    db_session.add(skill)
    db_session.commit()
    
    response = client.post(
        "/api/v1/ai-integration/skills/skill-1/deploy",
        json={"gateway_id": "nonexistent-gateway"}
    )
    
    assert response.status_code == 400


def test_create_skill_package_invalid_timeout(client, valid_skill_request):
    """Test skill creation with invalid timeout."""
    valid_skill_request["configuration"]["timeout_seconds"] = 500  # Exceeds max
    
    response = client.post(
        "/api/v1/ai-integration/skills",
        json=valid_skill_request
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_create_skill_package_negative_timeout(client, valid_skill_request):
    """Test skill creation with negative timeout."""
    valid_skill_request["configuration"]["timeout_seconds"] = -1
    
    response = client.post(
        "/api/v1/ai-integration/skills",
        json=valid_skill_request
    )
    
    assert response.status_code == 422


def test_list_skills_pagination_boundary(client, db_session, sample_gateway):
    """Test pagination at boundary conditions."""
    for i in range(3):
        skill = AISkill(
            id=f"skill-{i}",
            gateway_id=sample_gateway.id,
            name=f"skill-{i}",
            version="1.0.0",
            code_path=f"/app/skills/skill-{i}",
            configuration={},
            dependencies=[],
            status="deployed"
        )
        db_session.add(skill)
    db_session.commit()
    
    # Request more than available
    response = client.get("/api/v1/ai-integration/skills?skip=0&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_deploy_skill_preserves_package_data(client, db_session, sample_gateway):
    """Test that deployment preserves package data."""
    skill = AISkill(
        id="skill-1",
        gateway_id="other-gateway",
        name="test-skill",
        version="2.0.0",
        code_path="/app/skills/test-skill/2.0.0",
        configuration={"timeout": 60},
        dependencies=["axios@1.0.0", "lodash@4.17.21"],
        status="packaged"
    )
    db_session.add(skill)
    db_session.commit()
    
    response = client.post(
        "/api/v1/ai-integration/skills/skill-1/deploy",
        json={"gateway_id": sample_gateway.id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deployed"
    assert "deployed_at" in data


def test_hot_reload_skill_missing_gateway_param(client):
    """Test hot reload without gateway_id parameter."""
    response = client.post("/api/v1/ai-integration/skills/skill-1/reload")
    
    assert response.status_code == 422  # Missing required query parameter
