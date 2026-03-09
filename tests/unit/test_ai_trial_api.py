"""
Unit tests for AI Trial API endpoints.

Tests all API endpoints for AI trial management including
trial creation, execution, result retrieval, comparison,
cancellation, and listing with filters/pagination.

Validates: Requirements 7.2, 7.3, 7.6, 16.1, 16.2, 16.3, 16.4, 16.5
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, String, TypeDecorator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET

from src.database.connection import Base, get_db_session
from src.api.ai_trial_api import router
from src.models.data_lifecycle import (
    AuditLogModel,
    TrialStatus,
    DataStage,
)
from fastapi import FastAPI


# ============================================================================
# SQLite Compatibility
# ============================================================================

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


class SQLiteUUID(TypeDecorator):
    """UUID type that works with SQLite by storing as string."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return UUID(value) if not isinstance(value, UUID) else value
        return value


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_db():
    """Create test database with UUID patching for SQLite."""
    from sqlalchemy.dialects.postgresql import UUID as PGUUID

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Patch UUID columns for SQLite (AuditLogModel only)
    for col in AuditLogModel.__table__.columns:
        if isinstance(col.type, PGUUID):
            col.type = SQLiteUUID()

    AuditLogModel.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()

        # Restore original UUID types
        from sqlalchemy.dialects.postgresql import UUID as PGUUID_Restore
        for col in AuditLogModel.__table__.columns:
            if isinstance(col.type, SQLiteUUID):
                col.type = PGUUID_Restore(as_uuid=True)


@pytest.fixture
def client(test_db):
    """Create test client with dependency override."""
    from src.api.ai_trial_api import _shared_trials
    _shared_trials.clear()

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    return TestClient(app)


def _create_trial(client, **overrides):
    """Helper to create a trial with defaults."""
    payload = {
        "name": "Test Trial",
        "data_stage": "sample_library",
        "model_name": "test-model-v1",
        "parameters": {"learning_rate": 0.01},
        "sample_size": 100,
        "created_by": "user-1",
    }
    payload.update(overrides)
    return client.post("/api/trials", json=payload)


def _create_and_execute_trial(client, **overrides):
    """Helper to create and execute a trial."""
    resp = _create_trial(client, **overrides)
    trial_id = resp.json()["id"]
    source_data = [
        {"text": "sample 1", "label": "positive"},
        {"text": "sample 2", "label": "negative"},
        {"text": "sample 3", "label": "positive"},
    ]
    exec_resp = client.post(
        f"/api/trials/{trial_id}/execute",
        json={"source_data": source_data},
    )
    return trial_id, exec_resp


# ============================================================================
# Test Create Trial
# ============================================================================

def test_create_trial_success(client):
    """Test successful trial creation."""
    response = _create_trial(client)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "created"
    assert data["name"] == "Test Trial"
    assert data["data_stage"] == "sample_library"
    assert data["model_name"] == "test-model-v1"
    assert data["created_by"] == "user-1"
    assert data["id"] is not None


def test_create_trial_minimal(client):
    """Test trial creation with minimal required fields."""
    response = _create_trial(
        client, parameters=None, sample_size=None
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sample_size"] is None


def test_create_trial_all_stages(client):
    """Test trial creation with all data stages."""
    for stage in DataStage:
        response = _create_trial(client, data_stage=stage.value)
        assert response.status_code == 201
        assert response.json()["data_stage"] == stage.value


def test_create_trial_empty_name(client):
    """Test trial creation with empty name fails validation."""
    response = _create_trial(client, name="")
    assert response.status_code == 422


def test_create_trial_empty_model_name(client):
    """Test trial creation with empty model_name fails validation."""
    response = _create_trial(client, model_name="")
    assert response.status_code == 422


def test_create_trial_empty_created_by(client):
    """Test trial creation with empty created_by fails validation."""
    response = _create_trial(client, created_by="")
    assert response.status_code == 422


def test_create_trial_invalid_stage(client):
    """Test trial creation with invalid data stage."""
    response = _create_trial(client, data_stage="invalid_stage")
    assert response.status_code == 422


def test_create_trial_invalid_sample_size(client):
    """Test trial creation with sample_size < 1."""
    response = _create_trial(client, sample_size=0)
    assert response.status_code == 422


# ============================================================================
# Test Execute Trial
# ============================================================================

def test_execute_trial_success(client):
    """Test successful trial execution."""
    trial_id, exec_resp = _create_and_execute_trial(client)
    assert exec_resp.status_code == 200
    data = exec_resp.json()
    assert data["trial_id"] == trial_id
    assert data["execution_time"] >= 0
    assert data["data_quality_score"] > 0
    assert "accuracy" in data["metrics"]
    assert "precision" in data["metrics"]
    assert "recall" in data["metrics"]
    assert "f1_score" in data["metrics"]
    assert len(data["predictions"]) == 3


def test_execute_trial_not_found(client):
    """Test executing non-existent trial returns 404."""
    response = client.post(
        f"/api/trials/{uuid4()}/execute",
        json={"source_data": [{"text": "test"}]},
    )
    assert response.status_code == 404


def test_execute_trial_already_completed(client):
    """Test executing already-completed trial returns 400."""
    trial_id, _ = _create_and_execute_trial(client)
    response = client.post(
        f"/api/trials/{trial_id}/execute",
        json={"source_data": [{"text": "test"}]},
    )
    assert response.status_code == 400


# ============================================================================
# Test Get Trial Results
# ============================================================================

def test_get_results_success(client):
    """Test getting results of a completed trial."""
    trial_id, _ = _create_and_execute_trial(client)
    response = client.get(f"/api/trials/{trial_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["trial_id"] == trial_id
    assert data["execution_time"] >= 0
    assert data["data_quality_score"] > 0
    assert "accuracy" in data["metrics"]


def test_get_results_not_found(client):
    """Test getting results of non-existent trial returns 404."""
    response = client.get(f"/api/trials/{uuid4()}/results")
    assert response.status_code == 404


def test_get_results_not_completed(client):
    """Test getting results of non-completed trial returns 400."""
    resp = _create_trial(client)
    trial_id = resp.json()["id"]
    response = client.get(f"/api/trials/{trial_id}/results")
    assert response.status_code == 400


# ============================================================================
# Test Compare Trials
# ============================================================================

def test_compare_trials_success(client):
    """Test comparing two completed trials."""
    tid1, _ = _create_and_execute_trial(client, name="Trial A")
    tid2, _ = _create_and_execute_trial(client, name="Trial B")

    response = client.post("/api/trials/compare", json={
        "trial_ids": [tid1, tid2],
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["trial_ids"]) == 2
    assert len(data["metrics_comparison"]) == 2
    assert data["best_trial_id"] is not None
    assert "accuracy" in data["summary"]


def test_compare_trials_single_id(client):
    """Test comparing with less than 2 IDs fails validation."""
    tid, _ = _create_and_execute_trial(client)
    response = client.post("/api/trials/compare", json={
        "trial_ids": [tid],
    })
    assert response.status_code == 422


def test_compare_trials_not_completed(client):
    """Test comparing with non-completed trial returns 400."""
    tid1, _ = _create_and_execute_trial(client, name="Trial A")
    resp = _create_trial(client, name="Trial B")
    tid2 = resp.json()["id"]

    response = client.post("/api/trials/compare", json={
        "trial_ids": [tid1, tid2],
    })
    assert response.status_code == 400


def test_compare_trials_not_found(client):
    """Test comparing with non-existent trial returns 404."""
    tid, _ = _create_and_execute_trial(client)
    response = client.post("/api/trials/compare", json={
        "trial_ids": [tid, str(uuid4())],
    })
    assert response.status_code == 404


# ============================================================================
# Test Cancel Trial
# ============================================================================

def test_cancel_created_trial(client):
    """Test cancelling a created trial."""
    resp = _create_trial(client)
    trial_id = resp.json()["id"]

    response = client.post(f"/api/trials/{trial_id}/cancel")
    assert response.status_code == 200
    assert "cancelled" in response.json()["message"].lower()


def test_cancel_not_found(client):
    """Test cancelling non-existent trial returns 404."""
    response = client.post(f"/api/trials/{uuid4()}/cancel")
    assert response.status_code == 404


def test_cancel_completed_trial(client):
    """Test cancelling a completed trial returns 400."""
    trial_id, _ = _create_and_execute_trial(client)
    response = client.post(f"/api/trials/{trial_id}/cancel")
    assert response.status_code == 400


def test_cancel_already_cancelled(client):
    """Test cancelling an already-cancelled trial returns 400."""
    resp = _create_trial(client)
    trial_id = resp.json()["id"]
    client.post(f"/api/trials/{trial_id}/cancel")
    response = client.post(f"/api/trials/{trial_id}/cancel")
    assert response.status_code == 400


# ============================================================================
# Test List Trials
# ============================================================================

def test_list_trials_empty(client):
    """Test listing when no trials exist."""
    response = client.get("/api/trials")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_list_trials_success(client):
    """Test listing multiple trials."""
    for i in range(3):
        _create_trial(client, name=f"Trial {i}")

    response = client.get("/api/trials")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_trials_pagination(client):
    """Test pagination of trial listing."""
    for i in range(5):
        _create_trial(client, name=f"Trial {i}")

    response = client.get("/api/trials?page=1&page_size=2")
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["total_pages"] == 3

    response2 = client.get("/api/trials?page=3&page_size=2")
    data2 = response2.json()
    assert len(data2["items"]) == 1


def test_list_trials_filter_by_status(client):
    """Test filtering trials by status."""
    # Create a trial (status: created)
    _create_trial(client, name="Created Trial")

    # Create and execute a trial (status: completed)
    _create_and_execute_trial(client, name="Completed Trial")

    response = client.get("/api/trials?status_filter=created")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "created"

    response2 = client.get("/api/trials?status_filter=completed")
    data2 = response2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["status"] == "completed"


def test_list_trials_filter_by_data_stage(client):
    """Test filtering trials by data stage."""
    _create_trial(client, name="T1", data_stage="sample_library")
    _create_trial(client, name="T2", data_stage="annotated")

    response = client.get("/api/trials?data_stage=sample_library")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["data_stage"] == "sample_library"


def test_list_trials_filter_by_model_name(client):
    """Test filtering trials by model name."""
    _create_trial(client, name="T1", model_name="model-a")
    _create_trial(client, name="T2", model_name="model-b")

    response = client.get("/api/trials?model_name=model-a")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["model_name"] == "model-a"
