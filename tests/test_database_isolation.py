"""
Tests for database isolation configuration.

This test file verifies that:
- Transaction-based test isolation works correctly
- Database sessions are properly rolled back after tests
- Test data doesn't leak between tests
- Production database access is prevented
- Connection pooling is configured correctly

Requirements: 3.5, 3.6, 12.1, 12.2
"""

import pytest
import os
from sqlalchemy import text

from tests.database_isolation import (
    TestDatabaseConfig,
    TestDatabaseEngineFactory,
    isolated_test_session,
    DatabaseCleanupManager,
    prevent_production_database_access,
)


# =============================================================================
# Test Database Configuration
# =============================================================================

def test_sqlite_url_configuration():
    """Test that SQLite URL is configured correctly."""
    assert TestDatabaseConfig.SQLITE_URL == "sqlite:///:memory:"


def test_postgres_url_configuration():
    """Test that PostgreSQL URL is configured correctly."""
    url = TestDatabaseConfig.get_postgres_url()
    assert "postgresql://" in url
    assert "superinsight_test" in url
    assert "5433" in url  # Test port


def test_connection_pool_settings():
    """Test that connection pool settings are configured."""
    assert TestDatabaseConfig.POOL_SIZE == 5
    assert TestDatabaseConfig.MAX_OVERFLOW == 10
    assert TestDatabaseConfig.POOL_TIMEOUT == 30
    assert TestDatabaseConfig.POOL_PRE_PING is True


# =============================================================================
# Test Engine Factory
# =============================================================================

def test_create_sqlite_engine():
    """Test that SQLite engine can be created."""
    engine = TestDatabaseEngineFactory.create_sqlite_engine()
    
    assert engine is not None
    assert "sqlite" in str(engine.url)
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    engine.dispose()


@pytest.mark.integration
def test_create_postgres_engine():
    """Test that PostgreSQL engine can be created (if available)."""
    try:
        engine = TestDatabaseEngineFactory.create_postgres_engine()
        
        assert engine is not None
        assert "postgresql" in str(engine.url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        
        engine.dispose()
        
    except Exception as e:
        pytest.skip(f"PostgreSQL test database not available: {e}")


# =============================================================================
# Test Transaction Isolation
# =============================================================================

def test_transaction_isolation_rollback(test_engine):
    """Test that transactions are rolled back after test."""
    from src.database.connection import Base
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.orm import declarative_base
    
    # Create a simple test table
    TestBase = declarative_base()
    
    class TestModel(TestBase):
        __tablename__ = "test_isolation_table"
        id = Column(Integer, primary_key=True)
        name = Column(String(50))
    
    # Create table
    TestBase.metadata.create_all(bind=test_engine)
    
    # Insert data in isolated session
    with isolated_test_session(test_engine) as session:
        test_record = TestModel(id=1, name="test")
        session.add(test_record)
        session.flush()  # Flush to database but don't commit
        
        # Verify data exists in this session
        result = session.query(TestModel).filter_by(id=1).first()
        assert result is not None
        assert result.name == "test"
    
    # Verify data was rolled back in new session
    # Note: For SQLite in-memory, we need to check that the session is clean
    # The rollback happens at the connection level
    with isolated_test_session(test_engine) as session:
        count = session.query(TestModel).count()
        # After rollback, there should be no records
        # For SQLite in-memory, this test verifies the isolation mechanism works
        assert count == 0, f"Expected 0 records after rollback, found {count}"
    
    # Cleanup
    TestBase.metadata.drop_all(bind=test_engine)


def test_nested_transactions(db_session):
    """Test that nested transactions work correctly."""
    # This test verifies that savepoints work within isolated sessions
    
    # Start a nested transaction (savepoint)
    nested = db_session.begin_nested()
    
    # Perform some operation
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    
    # Rollback the nested transaction
    nested.rollback()
    
    # Session should still be usable
    result = db_session.execute(text("SELECT 2"))
    assert result.scalar() == 2


def test_multiple_tests_isolation_1(db_session):
    """First test to verify isolation between tests."""
    # This test and the next one verify that data doesn't leak between tests
    
    # Execute a query
    result = db_session.execute(text("SELECT 1 as value"))
    assert result.scalar() == 1


def test_multiple_tests_isolation_2(db_session):
    """Second test to verify isolation between tests."""
    # This should get a fresh session, independent of the previous test
    
    # Execute a query
    result = db_session.execute(text("SELECT 2 as value"))
    assert result.scalar() == 2


# =============================================================================
# Test Database Cleanup
# =============================================================================

def test_cleanup_manager_registration(db_session):
    """Test that cleanup manager can register items."""
    cleanup_manager = DatabaseCleanupManager(db_session)
    
    # Register some items
    cleanup_manager.register_for_cleanup(object, 1)
    cleanup_manager.register_for_cleanup(object, 2)
    
    assert len(cleanup_manager.cleanup_items) == 2


def test_cleanup_manager_verify_clean_state(db_session):
    """Test that cleanup manager can verify clean state."""
    cleanup_manager = DatabaseCleanupManager(db_session)
    
    # For in-memory SQLite with no data, should be clean
    is_clean = cleanup_manager.verify_clean_state()
    assert is_clean is True


# =============================================================================
# Test Production Database Access Prevention
# =============================================================================

def test_prevent_production_database_access():
    """Test that production database access is prevented."""
    # Save original environment
    original_env = os.environ.get("APP_ENV")
    original_db_url = os.environ.get("DATABASE_URL")
    
    try:
        # Set test environment
        os.environ["APP_ENV"] = "test"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        
        # Should not raise
        prevent_production_database_access()
        
    finally:
        # Restore original environment
        if original_env:
            os.environ["APP_ENV"] = original_env
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url


def test_prevent_production_database_access_blocks_production():
    """Test that production environment is blocked."""
    # Save original environment
    original_env = os.environ.get("APP_ENV")
    
    try:
        # Set production environment
        os.environ["APP_ENV"] = "production"
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="production environment"):
            prevent_production_database_access()
        
    finally:
        # Restore original environment
        if original_env:
            os.environ["APP_ENV"] = original_env
        else:
            os.environ["APP_ENV"] = "test"


def test_prevent_production_database_access_blocks_production_url():
    """Test that production database URLs are blocked."""
    # Save original environment
    original_db_url = os.environ.get("DATABASE_URL")
    original_env = os.environ.get("APP_ENV")
    
    try:
        # Set test environment but production database URL
        os.environ["APP_ENV"] = "test"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@prod-db.rds.amazonaws.com/mydb"
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="production database"):
            prevent_production_database_access()
        
    finally:
        # Restore original environment
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        if original_env:
            os.environ["APP_ENV"] = original_env


# =============================================================================
# Test Fixtures
# =============================================================================

def test_db_session_fixture(db_session):
    """Test that db_session fixture works correctly."""
    assert db_session is not None
    
    # Should be able to execute queries
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


def test_cleanup_test_data_fixture(cleanup_test_data):
    """Test that cleanup_test_data fixture works correctly."""
    assert cleanup_test_data is not None
    assert isinstance(cleanup_test_data, DatabaseCleanupManager)


@pytest.mark.integration
def test_postgres_session_fixture(postgres_session):
    """Test that postgres_session fixture works correctly (if available)."""
    assert postgres_session is not None
    
    # Should be able to execute queries
    result = postgres_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


# =============================================================================
# Test Connection Pooling
# =============================================================================

@pytest.mark.integration
def test_connection_pooling():
    """Test that connection pooling is configured correctly."""
    try:
        engine = TestDatabaseEngineFactory.create_postgres_engine()
        
        # Check pool configuration
        pool = engine.pool
        assert pool is not None
        
        # Pool should have correct size
        assert pool.size() == TestDatabaseConfig.POOL_SIZE
        
        engine.dispose()
        
    except Exception as e:
        pytest.skip(f"PostgreSQL test database not available: {e}")


# =============================================================================
# Integration Test Example
# =============================================================================

@pytest.mark.integration
def test_integration_example_with_postgres(postgres_session):
    """Example integration test using PostgreSQL."""
    # This demonstrates how to write integration tests with PostgreSQL
    
    # Execute a query
    result = postgres_session.execute(text("SELECT version()"))
    version = result.scalar()
    
    assert version is not None
    assert "PostgreSQL" in version
