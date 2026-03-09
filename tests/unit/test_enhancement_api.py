"""
Unit tests for Enhancement API endpoints.

Tests all API endpoints for enhancement job management including
job creation, status retrieval, applying enhancements, rollback,
cancellation, and listing with filters/pagination.

Validates: Requirements 6.1, 6.2, 6.3, 6.5, 15.1, 15.3
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
from src.api.enhancement_api import router
from src.models.data_lifecycle import (
    EnhancedDataModel,
    EnhancementType,
    JobStatus,
    SampleModel,
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


# Models that need UUID patching for SQLite
from src.models.data_lifecycle import (
    EnhancedDataModel,
    SampleModel,
    VersionModel,
    AuditLogModel,
)

PATCHED_MODELS = [EnhancedDataModel, SampleModel, VersionModel, AuditLogModel]


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

    # Patch UUID columns for SQLite
    for model in PATCHED_MODELS:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                col.type = SQLiteUUID()

    for model in PATCHED_MODELS:
        model.__table__.create(bind=engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()

        # Restore original UUID types
        from sqlalchemy.dialects.postgresql import UUID as PGUUID_Restore
        for model in PATCHED_MODELS:
            for col in model.__table__.columns:
                if isinstance(col.type, SQLiteUUID):
                    col.type = PGUUID_Restore(as_uuid=True)


@pytest.fixture
def client(test_db):
    """Create test client with dependency override."""
    from src.api.enhancement_api import _shared_jobs
    _shared_jobs.clear()

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    return TestClient(app)


# ============================================================================
# Test Create Enhancement Job
# ============================================================================

def test_create_job_success(client):
    """Test successful enhancement job creation."""
    response = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "quality_improvement",
        "parameters": {"threshold": 0.8},
        "target_quality": 0.9,
        "created_by": "user-1",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "queued"
    assert data["enhancement_type"] == "quality_improvement"
    assert data["created_by"] == "user-1"
    assert data["id"] is not None


def test_create_job_minimal(client):
    """Test job creation with minimal required fields."""
    response = client.post("/api/enhancements", json={
        "data_id": "some-data-id",
        "enhancement_type": "normalization",
        "created_by": "user-2",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["enhancement_type"] == "normalization"
    assert data["target_quality"] is None


def test_create_job_all_types(client):
    """Test job creation with all enhancement types."""
    for etype in EnhancementType:
        response = client.post("/api/enhancements", json={
            "data_id": str(uuid4()),
            "enhancement_type": etype.value,
            "created_by": "user-1",
        })
        assert response.status_code == 201
        assert response.json()["enhancement_type"] == etype.value


def test_create_job_empty_data_id(client):
    """Test job creation with empty data_id fails validation."""
    response = client.post("/api/enhancements", json={
        "data_id": "",
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    assert response.status_code == 422


def test_create_job_empty_created_by(client):
    """Test job creation with empty created_by fails validation."""
    response = client.post("/api/enhancements", json={
        "data_id": "data-1",
        "enhancement_type": "normalization",
        "created_by": "",
    })
    assert response.status_code == 422


def test_create_job_invalid_target_quality(client):
    """Test job creation with out-of-range target_quality."""
    response = client.post("/api/enhancements", json={
        "data_id": "data-1",
        "enhancement_type": "normalization",
        "created_by": "user-1",
        "target_quality": 1.5,
    })
    assert response.status_code == 422


def test_create_job_invalid_type(client):
    """Test job creation with invalid enhancement type."""
    response = client.post("/api/enhancements", json={
        "data_id": "data-1",
        "enhancement_type": "invalid_type",
        "created_by": "user-1",
    })
    assert response.status_code == 422


# ============================================================================
# Test Get Enhancement Job
# ============================================================================

def test_get_job_success(client):
    """Test getting an existing job."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": "data-1",
        "enhancement_type": "noise_reduction",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]

    response = client.get(f"/api/enhancements/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["status"] == "queued"


def test_get_job_not_found(client):
    """Test getting a non-existent job returns 404."""
    response = client.get(f"/api/enhancements/{uuid4()}")
    assert response.status_code == 404


# ============================================================================
# Test Apply Enhancement
# ============================================================================

def test_apply_enhancement_success(client, test_db):
    """Test successful enhancement application."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "quality_improvement",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]

    response = client.post(f"/api/enhancements/{job_id}/apply", json={
        "source_content": {"title": "Test", "body": "  Some text  "},
    })
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["enhancement_type"] == "quality_improvement"
    assert data["quality_overall"] > 0
    assert data["version"] == 1


def test_apply_enhancement_not_found(client):
    """Test applying to non-existent job returns 404."""
    response = client.post(f"/api/enhancements/{uuid4()}/apply", json={
        "source_content": {"title": "Test"},
    })
    assert response.status_code == 404


def test_apply_enhancement_already_completed(client, test_db):
    """Test applying to already-completed job returns 400."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]

    # Apply once
    client.post(f"/api/enhancements/{job_id}/apply", json={
        "source_content": {"title": "Test"},
    })

    # Apply again should fail
    response = client.post(f"/api/enhancements/{job_id}/apply", json={
        "source_content": {"title": "Test"},
    })
    assert response.status_code == 400


# ============================================================================
# Test Rollback Enhancement
# ============================================================================

def test_rollback_success(client, test_db):
    """Test successful rollback of a completed enhancement."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "data_augmentation",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]

    # Apply first
    client.post(f"/api/enhancements/{job_id}/apply", json={
        "source_content": {"title": "Original"},
    })

    # Rollback
    response = client.post(f"/api/enhancements/{job_id}/rollback")
    assert response.status_code == 200
    assert "rolled back" in response.json()["message"].lower()


def test_rollback_not_found(client):
    """Test rollback of non-existent job returns 404."""
    response = client.post(f"/api/enhancements/{uuid4()}/rollback")
    assert response.status_code == 404


def test_rollback_not_completed(client):
    """Test rollback of non-completed job returns 400."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]

    response = client.post(f"/api/enhancements/{job_id}/rollback")
    assert response.status_code == 400


# ============================================================================
# Test Cancel Enhancement Job
# ============================================================================

def test_cancel_queued_job(client):
    """Test cancelling a queued job."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]

    response = client.post(f"/api/enhancements/{job_id}/cancel")
    assert response.status_code == 200
    assert "cancelled" in response.json()["message"].lower()

    # Verify status changed
    get_resp = client.get(f"/api/enhancements/{job_id}")
    assert get_resp.json()["status"] == "cancelled"


def test_cancel_not_found(client):
    """Test cancelling non-existent job returns 404."""
    response = client.post(f"/api/enhancements/{uuid4()}/cancel")
    assert response.status_code == 404


def test_cancel_completed_job(client, test_db):
    """Test cancelling a completed job returns 400."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]

    # Complete it first
    client.post(f"/api/enhancements/{job_id}/apply", json={
        "source_content": {"title": "Test"},
    })

    response = client.post(f"/api/enhancements/{job_id}/cancel")
    assert response.status_code == 400


def test_cancel_already_cancelled(client):
    """Test cancelling an already-cancelled job returns 400."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]

    client.post(f"/api/enhancements/{job_id}/cancel")
    response = client.post(f"/api/enhancements/{job_id}/cancel")
    assert response.status_code == 400


# ============================================================================
# Test List Enhancement Jobs
# ============================================================================

def test_list_jobs_empty(client):
    """Test listing when no jobs exist."""
    response = client.get("/api/enhancements")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_list_jobs_success(client):
    """Test listing multiple jobs."""
    for i in range(3):
        client.post("/api/enhancements", json={
            "data_id": f"data-{i}",
            "enhancement_type": "normalization",
            "created_by": "user-1",
        })

    response = client.get("/api/enhancements")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_jobs_pagination(client):
    """Test pagination of job listing."""
    for i in range(5):
        client.post("/api/enhancements", json={
            "data_id": f"data-{i}",
            "enhancement_type": "normalization",
            "created_by": "user-1",
        })

    response = client.get("/api/enhancements?page=1&page_size=2")
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["total_pages"] == 3

    response2 = client.get("/api/enhancements?page=3&page_size=2")
    data2 = response2.json()
    assert len(data2["items"]) == 1


def test_list_jobs_filter_by_status(client, test_db):
    """Test filtering jobs by status."""
    # Create a queued job
    client.post("/api/enhancements", json={
        "data_id": "data-q",
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })

    # Create and complete a job
    resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    job_id = resp.json()["id"]
    client.post(f"/api/enhancements/{job_id}/apply", json={
        "source_content": {"title": "Test"},
    })

    # Filter by queued
    response = client.get("/api/enhancements?status_filter=queued")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "queued"

    # Filter by completed
    response2 = client.get("/api/enhancements?status_filter=completed")
    data2 = response2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["status"] == "completed"


def test_list_jobs_filter_by_type(client):
    """Test filtering jobs by enhancement type."""
    client.post("/api/enhancements", json={
        "data_id": "data-1",
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    client.post("/api/enhancements", json={
        "data_id": "data-2",
        "enhancement_type": "noise_reduction",
        "created_by": "user-1",
    })

    response = client.get("/api/enhancements?enhancement_type=normalization")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["enhancement_type"] == "normalization"


def test_list_jobs_filter_by_data_id(client):
    """Test filtering jobs by data_id."""
    target_id = "target-data-id"
    client.post("/api/enhancements", json={
        "data_id": target_id,
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    client.post("/api/enhancements", json={
        "data_id": "other-data-id",
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })

    response = client.get(f"/api/enhancements?data_id={target_id}")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["data_id"] == target_id


# ============================================================================
# Test Add to Library
# ============================================================================

def _create_and_apply_job(client):
    """Helper: create a job, apply it, return job_id."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "quality_improvement",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]
    client.post(f"/api/enhancements/{job_id}/apply", json={
        "source_content": {"title": "Test", "body": "Some content"},
    })
    return job_id


def test_add_to_library_success(client, test_db):
    """Test successfully adding enhanced data to sample library."""
    job_id = _create_and_apply_job(client)

    response = client.post(f"/api/enhancements/{job_id}/add-to-library", json={
        "user_id": "user-1",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["category"] == "enhanced"
    assert "enhanced" in data["tags"]
    assert data["version"] == 1
    assert data["quality_overall"] > 0
    assert data["metadata"]["enhancement_job_id"] is not None
    assert data["metadata"]["iteration_count"] >= 1


def test_add_to_library_not_found(client):
    """Test adding from non-existent job returns 404."""
    response = client.post(f"/api/enhancements/{uuid4()}/add-to-library", json={
        "user_id": "user-1",
    })
    assert response.status_code == 404


def test_add_to_library_not_completed(client):
    """Test adding from non-completed job returns 400."""
    create_resp = client.post("/api/enhancements", json={
        "data_id": str(uuid4()),
        "enhancement_type": "normalization",
        "created_by": "user-1",
    })
    job_id = create_resp.json()["id"]

    response = client.post(f"/api/enhancements/{job_id}/add-to-library", json={
        "user_id": "user-1",
    })
    assert response.status_code == 400
    assert "expected completed" in response.json()["detail"].lower()


def test_add_to_library_empty_user_id(client):
    """Test adding with empty user_id fails validation."""
    response = client.post(f"/api/enhancements/{uuid4()}/add-to-library", json={
        "user_id": "",
    })
    assert response.status_code == 422


def test_add_to_library_missing_user_id(client):
    """Test adding without user_id fails validation."""
    response = client.post(f"/api/enhancements/{uuid4()}/add-to-library", json={})
    assert response.status_code == 422
