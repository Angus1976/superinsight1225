"""
Unit tests for API Key and API Call Log models.

Tests validate the basic functionality of APIKeyModel and APICallLogModel
including creation, relationships, and field constraints.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
import hashlib

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

from src.sync.models import (
    APIKeyModel,
    APICallLogModel,
    APIKeyStatus,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@pytest.fixture
def db_session():
    """In-memory SQLite session (no Docker/host DB required)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    APIKeyModel.__table__.create(bind=engine, checkfirst=True)
    APICallLogModel.__table__.create(bind=engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestAPIKeyModel:
    """Test cases for APIKeyModel."""

    def test_create_api_key(self, db_session):
        """Test creating an API key with all required fields."""
        # Arrange
        tenant_id = "test_tenant_001"
        raw_key = "sk_test_1234567890abcdef"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # Act
        api_key = APIKeyModel(
            id=uuid4(),
            tenant_id=tenant_id,
            name="Test API Key",
            description="Test key for integration",
            key_prefix="sk_test_",
            key_hash=key_hash,
            scopes={"annotations": True, "augmented_data": True},
            rate_limit_per_minute=100,
            rate_limit_per_day=5000,
            status=APIKeyStatus.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=30),
            created_by="test_user"
        )
        
        db_session.add(api_key)
        db_session.commit()
        
        # Assert
        assert api_key.id is not None
        assert api_key.tenant_id == tenant_id
        assert api_key.name == "Test API Key"
        assert api_key.key_prefix == "sk_test_"
        assert api_key.key_hash == key_hash
        assert api_key.status == APIKeyStatus.ACTIVE
        assert api_key.total_calls == 0
        assert api_key.last_used_at is None
        assert api_key.created_at is not None

    def test_api_key_default_values(self, db_session):
        """Test API key default values."""
        # Arrange & Act
        raw_key = "sk_default_test"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = APIKeyModel(
            id=uuid4(),
            tenant_id="test_tenant",
            name="Default Test Key",
            key_prefix="sk_default",
            key_hash=key_hash,
            scopes={}
        )
        
        db_session.add(api_key)
        db_session.commit()
        
        # Assert
        assert api_key.rate_limit_per_minute == 60
        assert api_key.rate_limit_per_day == 10000
        assert api_key.status == APIKeyStatus.ACTIVE
        assert api_key.total_calls == 0

    def test_api_key_status_transitions(self, db_session):
        """Test API key status transitions."""
        # Arrange
        raw_key = "sk_status_test"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = APIKeyModel(
            id=uuid4(),
            tenant_id="test_tenant",
            name="Status Test Key",
            key_prefix="sk_status",
            key_hash=key_hash,
            scopes={},
            status=APIKeyStatus.ACTIVE
        )
        
        db_session.add(api_key)
        db_session.commit()
        
        # Act & Assert - Active to Disabled
        api_key.status = APIKeyStatus.DISABLED
        db_session.commit()
        assert api_key.status == APIKeyStatus.DISABLED
        
        # Act & Assert - Disabled to Active
        api_key.status = APIKeyStatus.ACTIVE
        db_session.commit()
        assert api_key.status == APIKeyStatus.ACTIVE
        
        # Act & Assert - Active to Revoked (terminal state)
        api_key.status = APIKeyStatus.REVOKED
        db_session.commit()
        assert api_key.status == APIKeyStatus.REVOKED


class TestAPICallLogModel:
    """Test cases for APICallLogModel."""

    def test_create_call_log(self, db_session):
        """Test creating an API call log."""
        # Arrange - Create API key first
        raw_key = "sk_log_test"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = APIKeyModel(
            id=uuid4(),
            tenant_id="test_tenant",
            name="Log Test Key",
            key_prefix="sk_log",
            key_hash=key_hash,
            scopes={}
        )
        
        db_session.add(api_key)
        db_session.commit()
        
        # Act - Create call log
        call_log = APICallLogModel(
            id=uuid4(),
            key_id=api_key.id,
            endpoint="/api/v1/external/annotations",
            status_code=200,
            response_time_ms=45.5
        )
        
        db_session.add(call_log)
        db_session.commit()
        
        # Assert
        assert call_log.id is not None
        assert call_log.key_id == api_key.id
        assert call_log.endpoint == "/api/v1/external/annotations"
        assert call_log.status_code == 200
        assert call_log.response_time_ms == 45.5
        assert call_log.called_at is not None

    def test_api_key_call_logs_relationship(self, db_session):
        """Test relationship between API key and call logs."""
        # Arrange - Create API key
        raw_key = "sk_relationship_test"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = APIKeyModel(
            id=uuid4(),
            tenant_id="test_tenant",
            name="Relationship Test Key",
            key_prefix="sk_rel",
            key_hash=key_hash,
            scopes={}
        )
        
        db_session.add(api_key)
        db_session.commit()
        
        # Act - Create multiple call logs
        endpoints = [
            "/api/v1/external/annotations",
            "/api/v1/external/augmented-data",
            "/api/v1/external/quality-reports"
        ]
        
        for endpoint in endpoints:
            call_log = APICallLogModel(
                id=uuid4(),
                key_id=api_key.id,
                endpoint=endpoint,
                status_code=200,
                response_time_ms=50.0
            )
            db_session.add(call_log)
        
        db_session.commit()
        
        # Assert
        db_session.refresh(api_key)
        assert len(api_key.call_logs) == 3
        assert all(log.key_id == api_key.id for log in api_key.call_logs)

    def test_call_log_different_status_codes(self, db_session):
        """Test call logs with different status codes."""
        # Arrange
        raw_key = "sk_status_code_test"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = APIKeyModel(
            id=uuid4(),
            tenant_id="test_tenant",
            name="Status Code Test Key",
            key_prefix="sk_status",
            key_hash=key_hash,
            scopes={}
        )
        
        db_session.add(api_key)
        db_session.commit()
        
        # Act - Create logs with different status codes
        status_codes = [200, 401, 403, 429, 500]
        
        for status_code in status_codes:
            call_log = APICallLogModel(
                id=uuid4(),
                key_id=api_key.id,
                endpoint="/api/v1/external/test",
                status_code=status_code,
                response_time_ms=100.0
            )
            db_session.add(call_log)
        
        db_session.commit()
        
        # Assert
        db_session.refresh(api_key)
        assert len(api_key.call_logs) == 5
        logged_status_codes = [log.status_code for log in api_key.call_logs]
        assert set(logged_status_codes) == set(status_codes)
