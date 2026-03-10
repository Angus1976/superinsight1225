"""
Tests for add-to-library endpoint deprecation.

Validates: Task 3.2.4 - Mark old add-to-library endpoint as deprecated
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, String, TypeDecorator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET, UUID as PGUUID

from src.database.connection import Base, get_db_session
from src.api.enhancement_api import router
from src.models.data_lifecycle import (
    EnhancedDataModel,
    SampleModel,
    VersionModel,
    AuditLogModel,
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
            from uuid import UUID
            return UUID(value) if not isinstance(value, UUID) else value
        return value


PATCHED_MODELS = [EnhancedDataModel, SampleModel, VersionModel, AuditLogModel]


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_db():
    """Create test database with UUID patching for SQLite."""
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
        for model in PATCHED_MODELS:
            for col in model.__table__.columns:
                if isinstance(col.type, SQLiteUUID):
                    col.type = PGUUID(as_uuid=True)


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
# Tests
# ============================================================================

def test_add_to_library_deprecation_headers(client):
    """Test that add-to-library endpoint returns deprecation headers."""
    # Create and apply an enhancement job first
    job_id = _create_and_apply_job(client)
    
    # Call the deprecated add-to-library endpoint
    response = client.post(
        f"/api/enhancements/{job_id}/add-to-library",
        json={"user_id": "user-1"}
    )
    
    # Verify success
    assert response.status_code == 201
    
    # Verify deprecation headers are present
    assert response.headers.get("X-Deprecated-Endpoint") == "true"
    assert response.headers.get("X-New-Endpoint") == "/api/data-lifecycle/transfer"
    assert response.headers.get("X-Deprecation-Date") == "2026-06-10"
    assert "X-Deprecation-Info" in response.headers


def test_add_to_library_still_functional(client):
    """Test that deprecated endpoint still works correctly."""
    job_id = _create_and_apply_job(client)
    
    response = client.post(
        f"/api/enhancements/{job_id}/add-to-library",
        json={"user_id": "user-1"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify response structure is unchanged
    assert "id" in data
    assert "data_id" in data
    assert "content" in data
    assert "category" in data


def _create_and_apply_job(client):
    """Helper to create and apply an enhancement job."""
    # Create job
    create_resp = client.post(
        "/api/enhancements",
        json={
            "data_id": "data-1",
            "enhancement_type": "quality_improvement",
            "created_by": "user-1",
        },
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]
    
    # Apply enhancement
    apply_resp = client.post(
        f"/api/enhancements/{job_id}/apply",
        json={
            "source_content": {
                "text": "Sample text",
                "metadata": {"source": "test"},
            }
        },
    )
    assert apply_resp.status_code == 200
    
    return job_id
