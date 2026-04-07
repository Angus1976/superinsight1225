"""
Pytest configuration and shared fixtures for SuperInsight testing.

This module provides:
- Database session fixtures with transaction isolation
- Redis connection fixtures with keyspace isolation
- Test environment configuration
- Mock service fixtures
- Test data cleanup utilities
"""

import os

# Before any `src` import: ORM modules (e.g. structuring) read DATABASE_URL at import time.
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
if not os.environ.get("APP_ENV"):
    os.environ["APP_ENV"] = "test"

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from redis import Redis
from unittest.mock import MagicMock

from src.database.connection import Base


# =============================================================================
# Peak memory (max RSS) reporting
# =============================================================================
#
# Enable: PYTEST_REPORT_MAXRSS=1 或 ./scripts/run-unit-lowmem.sh --mem
# 使用 resource.getrusage(RUSAGE_SELF).ru_maxrss：与进程同生命周期内的峰值常驻内存。
#


def _ru_maxrss_to_mib(ru_maxrss: int) -> float:
    """将 ru_maxrss 转为 MiB（macOS 为字节，Linux 等一般为千字节）。"""
    import sys

    if ru_maxrss <= 0:
        return 0.0
    if sys.platform == "darwin":
        return float(ru_maxrss) / (1024.0 * 1024.0)
    return float(ru_maxrss) * 1024.0 / (1024.0 * 1024.0)


def pytest_sessionfinish(session, exitstatus):
    if os.environ.get("PYTEST_REPORT_MAXRSS", "").lower() not in ("1", "true", "yes"):
        return
    try:
        import resource
        import sys

        u = resource.getrusage(resource.RUSAGE_SELF)
        mib = _ru_maxrss_to_mib(u.ru_maxrss)
        print(
            f"\n[pytest] Peak resident set size (ru_maxrss): {mib:.1f} MiB\n",
            file=sys.stderr,
            end="",
        )
    except Exception:
        pass


# =============================================================================
# Test Environment Configuration
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configure test environment variables."""
    os.environ["APP_ENV"] = "test"
    os.environ["APP_DEBUG"] = "false"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6380/0"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-do-not-use-in-production"
    os.environ["CORS_ORIGINS"] = "http://localhost:3000"
    
    yield
    
    # Cleanup after all tests
    pass


# =============================================================================
# Database Fixtures
# =============================================================================

# Import database isolation utilities
from tests.database_isolation import (
    TestDatabaseEngineFactory,
    isolated_test_session,
    DatabaseCleanupManager,
    prevent_production_database_access,
    setup_test_database,
    teardown_test_database,
)

# Prevent production database access
prevent_production_database_access()


@pytest.fixture(scope="session")
def test_engine():
    """
    Create a test database engine with in-memory SQLite.
    
    Uses StaticPool to ensure the same connection is reused,
    which is necessary for in-memory SQLite databases.
    """
    engine = TestDatabaseEngineFactory.create_sqlite_engine()
    
    yield engine
    
    # Drop all tables after tests
    teardown_test_database(engine)
    engine.dispose()


@pytest.fixture(scope="session")
def postgres_test_engine():
    """
    Create a PostgreSQL test database engine for integration tests.
    
    Uses QueuePool with connection pooling for better performance.
    Only available if PostgreSQL test database is configured.
    """
    try:
        engine = TestDatabaseEngineFactory.create_postgres_engine()
        
        # Set up schema
        setup_test_database(engine)
        
        yield engine
        
        # Tear down schema
        teardown_test_database(engine)
        engine.dispose()
        
    except Exception as e:
        pytest.skip(f"PostgreSQL test database not available: {e}")


@pytest.fixture(scope="function")
def db_session(request) -> Generator[Session, None, None]:
    """
    Provide a database session with transaction rollback.
    
    Each test gets a fresh session that is rolled back after the test,
    ensuring test isolation. Uses property conftest's fixture if available
    (for property tests), otherwise uses the main test engine.
    """
    # Check if we're in a property test directory - property conftest handles it
    if hasattr(request.node, "fspath"):
        test_path = str(request.node.fspath)
        if "/property/" in test_path or "\\property\\" in test_path.replace("\\", "/"):
            # Property tests have their own db_session fixture in tests/property/conftest.py
            # Skip this fixture to let property conftest handle it
            pytest.skip("Property tests use their own db_session fixture")
    
    # Fall back to main test engine
    from tests.database_isolation import isolated_test_session, ensure_sqlite_test_schema

    engine = request.getfixturevalue("test_engine")
    ensure_sqlite_test_schema(engine)
    with isolated_test_session(engine) as session:
        yield session


@pytest.fixture(scope="function")
def postgres_session(postgres_test_engine) -> Generator[Session, None, None]:
    """
    Provide a PostgreSQL database session with transaction rollback.
    
    Each test gets a fresh session that is rolled back after the test,
    ensuring test isolation.
    """
    with isolated_test_session(postgres_test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def db(db_session):
    """Alias for db_session for backward compatibility."""
    return db_session


# =============================================================================
# Redis Fixtures
# =============================================================================

# Import Redis isolation utilities
from tests.redis_isolation import (
    TestRedisConfig,
    TestRedisClientFactory,
    RedisKeyspaceIsolator,
    RedisTestCleanupManager,
    isolated_redis_session,
    prevent_production_redis_access,
    setup_test_redis,
    teardown_test_redis,
)

# Prevent production Redis access
prevent_production_redis_access()


@pytest.fixture(scope="session")
def redis_client():
    """
    Provide a Redis client for testing.
    
    Uses a separate Redis instance (port 6380) and database (db=15)
    for complete test isolation. Falls back to a mock if Redis is not available.
    """
    try:
        client = TestRedisClientFactory.create_client()
        # Test connection
        client.ping()
        yield client
        # Cleanup: flush test database
        client.flushdb()
        client.close()
    except Exception:
        # If Redis is not available, use a mock
        mock_redis = MagicMock(spec=Redis)
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.flushdb.return_value = True
        mock_redis.keys.return_value = []
        yield mock_redis


@pytest.fixture(scope="function")
def redis(redis_client):
    """
    Provide a Redis client with automatic cleanup.
    
    Clears all keys with test prefix after each test.
    Uses keyspace isolation strategy for complete test isolation.
    """
    yield redis_client
    
    # Cleanup: delete all test keys using the configured prefix
    try:
        prefix = TestRedisConfig.get_key_prefix()
        pattern = f"{prefix}*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except Exception:
        pass


@pytest.fixture(scope="function")
def redis_isolator(redis_client):
    """
    Provide a Redis keyspace isolator for tracking and cleanup.
    
    The isolator automatically prefixes all keys and tracks them
    for easy cleanup after tests.
    """
    isolator = RedisKeyspaceIsolator(redis_client)
    yield isolator
    # Cleanup all tracked keys
    isolator.cleanup_test_keys()


@pytest.fixture(scope="function")
def redis_cleanup_manager(redis_client):
    """
    Provide a Redis cleanup manager for test data.
    
    Usage:
        def test_something(redis_cleanup_manager):
            # Test code that creates Redis data
            redis_cleanup_manager.delete_test_prefix_keys()
            # Or verify clean state
            assert redis_cleanup_manager.verify_clean_state()
    """
    manager = RedisTestCleanupManager(redis_client)
    yield manager


# =============================================================================
# Mock Service Fixtures
# =============================================================================

@pytest.fixture
def mock_label_studio():
    """Mock Label Studio API client."""
    mock = MagicMock()
    mock.get_projects.return_value = []
    mock.create_project.return_value = {"id": 1, "title": "Test Project"}
    mock.get_tasks.return_value = []
    mock.create_task.return_value = {"id": 1}
    return mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for AI annotation tests."""
    mock = MagicMock()
    mock.annotate.return_value = {
        "annotations": [],
        "confidence": 0.95,
        "model": "test-model"
    }
    mock.health_check.return_value = True
    return mock


# =============================================================================
# Async Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for async tests.
    
    This fixture ensures a single event loop is used for the entire
    test session, which is necessary for session-scoped async fixtures.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Test Data Cleanup Utilities
# =============================================================================

@pytest.fixture
def cleanup_test_data(db_session):
    """
    Provide a cleanup utility for test data.
    
    Usage:
        def test_something(cleanup_test_data):
            # Test code that creates data
            cleanup_test_data.register_for_cleanup(User, user_id)
            # Data will be cleaned up automatically
    """
    cleanup_manager = DatabaseCleanupManager(db_session)
    yield cleanup_manager
    cleanup_manager.cleanup_registered_items()


# =============================================================================
# Hypothesis Configuration
# =============================================================================

# Configure Hypothesis for property-based testing
from hypothesis import settings, HealthCheck

# Default profile for fast tests (100 examples as per requirements)
settings.register_profile(
    "default",
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# CI profile with more examples for comprehensive testing
settings.register_profile(
    "ci",
    max_examples=500,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# Fast profile for quick iteration during development
settings.register_profile(
    "fast",
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# Middle ground: faster than default (100) but more coverage than fast (10)
settings.register_profile(
    "dev",
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# Load profile from environment or use default
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


# =============================================================================
# Custom Hypothesis Strategies
# =============================================================================

# Custom strategies for domain models are available in tests/strategies.py
# 
# Usage:
#     from tests.strategies import users, tasks, annotations
#     
#     @given(user=users())
#     def test_user_property(user):
#         assert user.email is not None
#
# Available strategies:
#   - users(): Generate user data with configurable role and active status
#   - tasks(): Generate task data with configurable status
#   - annotations(): Generate annotation data with configurable type
#   - datasets(): Generate dataset data
#   - projects(): Generate project data
#   - json_serializable_data(): Generate JSON-serializable nested structures
#   - valid_email(), invalid_emails(): Email validation testing
#   - valid_uuid(), invalid_uuids(): UUID validation testing
#   - operation_pairs(): Generate operation pairs for metamorphic testing
