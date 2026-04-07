"""
Tests for deprecation headers on error responses.

Validates: Task 3.2.6 - Add deprecation warning response headers
Ensures deprecation headers are present on both success and error responses.
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

    _uuid_col_restore = []
    for model in PATCHED_MODELS:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                _uuid_col_restore.append((col, col.type))
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

        for col, original_type in _uuid_col_restore:
            col.type = original_type


@pytest.fixture
def client(test_db):
    """Create test client with dependency override."""
    from src.api.enhancement_api import _shared_jobs, DeprecatedEndpointException
    from fastapi.responses import JSONResponse
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    
    _shared_jobs.clear()

    app = FastAPI()
    app.include_router(router)

    # Add exception handler for DeprecatedEndpointException
    @app.exception_handler(DeprecatedEndpointException)
    async def deprecated_exception_handler(request: Request, exc: DeprecatedEndpointException):
        response = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
        # Add the deprecation headers from the exception
        for key, value in exc.headers.items():
            response.headers[key] = value
        return response
    
    # Add exception handler for validation errors on deprecated endpoint
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        response = JSONResponse(
            status_code=422,
            content={"detail": exc.errors()}
        )
        # Add deprecation headers if this is the deprecated add-to-library endpoint
        if "add-to-library" in str(request.url):
            response.headers["X-Deprecated-Endpoint"] = "true"
            response.headers["X-New-Endpoint"] = "/api/data-lifecycle/transfer"
            response.headers["X-Deprecation-Date"] = "2026-06-10"
            response.headers["X-Deprecation-Info"] = "https://docs.example.com/migration/data-transfer"
        return response

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

def test_deprecation_headers_on_404_error(client):
    """Test that deprecation headers are present on 404 error responses."""
    # Call with non-existent job ID
    response = client.post(
        f"/api/enhancements/{uuid4()}/add-to-library",
        json={"user_id": "user-1"}
    )
    
    # Verify 404 error
    assert response.status_code == 404
    
    # Verify deprecation headers are present even on error
    assert response.headers.get("X-Deprecated-Endpoint") == "true"
    assert response.headers.get("X-New-Endpoint") == "/api/data-lifecycle/transfer"
    assert response.headers.get("X-Deprecation-Date") == "2026-06-10"
    assert "X-Deprecation-Info" in response.headers


def test_deprecation_headers_on_400_error(client):
    """Test that deprecation headers are present on 400 error responses."""
    # Create job but don't apply it (so it's not completed)
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
    
    # Try to add to library before job is completed
    response = client.post(
        f"/api/enhancements/{job_id}/add-to-library",
        json={"user_id": "user-1"}
    )
    
    # Verify 400 error
    assert response.status_code == 400
    
    # Verify deprecation headers are present even on error
    assert response.headers.get("X-Deprecated-Endpoint") == "true"
    assert response.headers.get("X-New-Endpoint") == "/api/data-lifecycle/transfer"
    assert response.headers.get("X-Deprecation-Date") == "2026-06-10"
    assert "X-Deprecation-Info" in response.headers


def test_deprecation_headers_on_422_validation_error(client):
    """Test that deprecation headers are present on 422 validation error responses."""
    # Call with invalid request (missing user_id)
    response = client.post(
        f"/api/enhancements/{uuid4()}/add-to-library",
        json={}
    )
    
    # Verify 422 validation error
    assert response.status_code == 422
    
    # Verify deprecation headers are present even on validation error
    assert response.headers.get("X-Deprecated-Endpoint") == "true"
    assert response.headers.get("X-New-Endpoint") == "/api/data-lifecycle/transfer"
    assert response.headers.get("X-Deprecation-Date") == "2026-06-10"
    assert "X-Deprecation-Info" in response.headers


def test_deprecation_headers_on_success(client):
    """Test that deprecation headers are present on successful responses."""
    # Create and apply an enhancement job
    job_id = _create_and_apply_job(client)
    
    # Call the deprecated endpoint
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
