"""
Pytest fixtures for multi-tenant workspace tests.

Provides common test fixtures including:
- Database session fixtures
- Test tenant and workspace fixtures
- Mock services
"""

import pytest
from datetime import datetime
from uuid import uuid4
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.database.connection import Base


# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_audit_logger():
    """Create a mock audit logger."""
    logger = MagicMock()
    logger.log = AsyncMock()
    logger.log_cross_tenant_attempt = AsyncMock()
    logger.log_cross_tenant_access = AsyncMock()
    return logger


@pytest.fixture
def mock_notification_service():
    """Create a mock notification service."""
    service = MagicMock()
    service.send_warning = AsyncMock()
    service.send_alert = AsyncMock()
    return service


@pytest.fixture
def mock_permission_checker():
    """Create a mock permission checker."""
    checker = MagicMock()
    checker.revoke_all_permissions = AsyncMock()
    checker.check_permission = AsyncMock(return_value=True)
    return checker


@pytest.fixture
def mock_encryptor():
    """Create a mock data encryptor."""
    encryptor = MagicMock()
    encryptor.encrypt = MagicMock(side_effect=lambda data, key: b"encrypted_" + data)
    encryptor.decrypt = MagicMock(side_effect=lambda data, key: data.replace(b"encrypted_", b""))
    return encryptor


@pytest.fixture
def sample_tenant_config() -> Dict[str, Any]:
    """Sample tenant configuration for testing."""
    return {
        "name": "Test Tenant",
        "description": "A test tenant for unit tests",
        "admin_email": "admin@test.com",
        "plan": "professional",
    }


@pytest.fixture
def sample_workspace_config() -> Dict[str, Any]:
    """Sample workspace configuration for testing."""
    return {
        "name": "Test Workspace",
        "description": "A test workspace for unit tests",
    }


@pytest.fixture
def sample_member_config() -> Dict[str, Any]:
    """Sample member configuration for testing."""
    return {
        "user_id": str(uuid4()),
        "role": "member",
    }


@pytest.fixture
def sample_quota_config() -> Dict[str, Any]:
    """Sample quota configuration for testing."""
    return {
        "storage_bytes": 10 * 1024 * 1024 * 1024,  # 10GB
        "project_count": 100,
        "user_count": 50,
        "api_call_count": 100000,
    }


# Hypothesis settings for property-based tests
from hypothesis import settings as hypothesis_settings

hypothesis_settings.register_profile(
    "ci",
    max_examples=100,
    deadline=None,
)

hypothesis_settings.register_profile(
    "dev",
    max_examples=50,
    deadline=None,
)

hypothesis_settings.load_profile("ci")
