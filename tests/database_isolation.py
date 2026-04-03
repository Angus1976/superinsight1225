"""
Test database isolation utilities for SuperInsight testing.

This module provides:
- Separate test database configuration for PostgreSQL
- Connection pooling management for tests
- Transaction-based test isolation
- Automatic rollback after tests
- Database cleanup utilities
- Support for both SQLite (unit tests) and PostgreSQL (integration tests)

Requirements: 3.5, 3.6, 12.1, 12.2
"""

import os
import logging
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, NullPool, QueuePool
from sqlalchemy.engine import Engine

from src.database.connection import Base

logger = logging.getLogger(__name__)


def ensure_sqlite_test_schema(engine: Engine) -> None:
    """
    Ensure all ORM tables exist on a SQLite test engine (idempotent).

    Shared session-scoped in-memory engines can end up without some tables if an
    early ``create_all`` aborted mid-metadata, or if stray DDL ran against the
    same metadata. Integration tests that rely on ``temp_data`` / ``samples`` /
    ``llm_applications`` call this via the root ``db_session`` fixture.

    We only ``CREATE`` the few tables integration tests need. A full
    ``metadata.create_all`` here can raise duplicate *index* errors on SQLite
    (``checkfirst`` applies to tables, not indexes) even when canary tables are
    missing, so we avoid blanket ``create_all`` in this repair path.
    """
    if engine.dialect.name != "sqlite":
        return

    from sqlalchemy import inspect

    try:
        names = set(inspect(engine).get_table_names())
    except Exception:
        names = set()

    required = ("temp_data", "samples", "llm_applications")
    if names and all(t in names for t in required):
        return

    import src.database.models  # noqa: F401 — register models on Base.metadata

    from src.models.data_lifecycle import TempDataModel, SampleModel
    from src.models.llm_configuration import LLMConfiguration
    from src.models.llm_application import LLMApplication, LLMApplicationBinding

    for table in (
        TempDataModel.__table__,
        SampleModel.__table__,
        LLMConfiguration.__table__,
        LLMApplication.__table__,
        LLMApplicationBinding.__table__,
    ):
        try:
            table.create(bind=engine, checkfirst=True)
        except Exception as exc:
            msg = str(exc).lower()
            if "already exists" not in msg:
                raise


# =============================================================================
# Test Database Configuration
# =============================================================================

class TestDatabaseConfig:
    """Configuration for test database isolation."""
    
    # SQLite configuration for unit tests (fast, in-memory)
    SQLITE_URL = "sqlite:///:memory:"
    
    # PostgreSQL configuration for integration tests (separate test database)
    POSTGRES_HOST = os.getenv("TEST_POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("TEST_POSTGRES_PORT", "5433"))
    POSTGRES_USER = os.getenv("TEST_POSTGRES_USER", "superinsight_test")
    POSTGRES_PASSWORD = os.getenv("TEST_POSTGRES_PASSWORD", "test_password")
    POSTGRES_DB = os.getenv("TEST_POSTGRES_DB", "superinsight_test")
    
    @classmethod
    def get_postgres_url(cls) -> str:
        """Get PostgreSQL test database URL."""
        return (
            f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
            f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        )
    
    @classmethod
    def get_postgres_async_url(cls) -> str:
        """Get PostgreSQL async test database URL."""
        return (
            f"postgresql+asyncpg://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}"
            f"@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        )
    
    # Connection pool settings for tests
    POOL_SIZE = 5
    MAX_OVERFLOW = 10
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 3600  # Recycle connections after 1 hour
    POOL_PRE_PING = True  # Validate connections before use


# =============================================================================
# Test Database Engine Factory
# =============================================================================

class TestDatabaseEngineFactory:
    """Factory for creating test database engines with proper isolation."""
    
    @staticmethod
    def create_sqlite_engine() -> Engine:
        """
        Create SQLite in-memory engine for unit tests.
        
        Uses StaticPool to ensure the same connection is reused,
        which is necessary for in-memory SQLite databases.
        """
        engine = create_engine(
            TestDatabaseConfig.SQLITE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        # SQLite cannot create tables that use PostgreSQL JSONB unless compiled to JSON.
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy.ext.compiler import compiles

        @compiles(JSONB, "sqlite")
        def _compile_jsonb_sqlite(type_, compiler, **kw):
            return "JSON"

        # Register all ORM models on Base.metadata (connection.Base alone is not enough).
        import src.database.models  # noqa: F401

        # Create all tables. When test modules are imported in different orders within
        # the same Python process, some indexes can be registered on Base.metadata
        # more than once (e.g. structuring_jobs tenant/status index). SQLite does not
        # support "IF NOT EXISTS" on CREATE INDEX in this path, so we defensively
        # ignore "already exists" errors during metadata.create_all for the in‑memory
        # test engine.
        from sqlalchemy.exc import OperationalError

        try:
            Base.metadata.create_all(bind=engine)
        except OperationalError as exc:
            msg = str(exc).lower()
            if "already exists" not in msg:
                raise

        # Some integration tests (e.g. approval notifications) use raw SQL
        # against the ``users`` and ``approval_requests`` tables. In rare import
        # orders, these models can be registered on Base.metadata later than the
        # main create_all call above; ensure the core tables exist explicitly.
        from src.security.models import UserModel
        from src.models.approval_request_db import ApprovalRequestRow
        from src.models.notification_db import InternalMessageRow

        UserModel.__table__.create(bind=engine, checkfirst=True)
        ApprovalRequestRow.__table__.create(bind=engine, checkfirst=True)
        InternalMessageRow.__table__.create(bind=engine, checkfirst=True)
        
        logger.info("Created SQLite in-memory test database engine")
        return engine
    
    @staticmethod
    def create_postgres_engine() -> Engine:
        """
        Create PostgreSQL engine for integration tests.
        
        Uses QueuePool with connection pooling for better performance
        and resource management.
        """
        engine = create_engine(
            TestDatabaseConfig.get_postgres_url(),
            poolclass=QueuePool,
            pool_size=TestDatabaseConfig.POOL_SIZE,
            max_overflow=TestDatabaseConfig.MAX_OVERFLOW,
            pool_timeout=TestDatabaseConfig.POOL_TIMEOUT,
            pool_recycle=TestDatabaseConfig.POOL_RECYCLE,
            pool_pre_ping=TestDatabaseConfig.POOL_PRE_PING,
            echo=False,
        )
        
        logger.info("Created PostgreSQL test database engine")
        return engine
    
    @staticmethod
    def create_engine_for_test_type(test_type: str = "unit") -> Engine:
        """
        Create appropriate engine based on test type.
        
        Args:
            test_type: "unit" for SQLite, "integration" for PostgreSQL
        
        Returns:
            Configured database engine
        """
        if test_type == "integration":
            return TestDatabaseEngineFactory.create_postgres_engine()
        else:
            return TestDatabaseEngineFactory.create_sqlite_engine()


# =============================================================================
# Transaction-Based Test Isolation
# =============================================================================

class TransactionIsolatedSession:
    """
    Provides transaction-based test isolation with automatic rollback.
    
    Each test gets a fresh session that is rolled back after the test,
    ensuring complete isolation between tests.
    """
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.connection = None
        self.transaction = None
        self.session = None
        self.session_factory = None
    
    def __enter__(self) -> Session:
        """Start a new transaction and return a session."""
        # Create a connection
        self.connection = self.engine.connect()
        
        # Begin a transaction
        self.transaction = self.connection.begin()
        
        # Create a session factory bound to this connection
        self.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.connection
        )
        
        # Create a session
        self.session = self.session_factory()
        
        # Enable nested transactions for savepoints
        # This allows tests to use transactions internally
        @event.listens_for(self.session, "after_transaction_end")
        def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                session.begin_nested()
        
        # Start a savepoint
        self.session.begin_nested()
        
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Rollback transaction and cleanup."""
        try:
            if self.session:
                self.session.close()
        finally:
            if self.transaction:
                self.transaction.rollback()
            if self.connection:
                self.connection.close()
        
        # Don't suppress exceptions
        return False


@contextmanager
def isolated_test_session(engine: Engine) -> Generator[Session, None, None]:
    """
    Context manager for transaction-isolated test sessions.
    
    Usage:
        with isolated_test_session(engine) as session:
            # Test code here
            # All changes will be rolled back automatically
    
    Args:
        engine: Database engine to use
    
    Yields:
        Isolated database session
    """
    with TransactionIsolatedSession(engine) as session:
        yield session


# =============================================================================
# Database Cleanup Utilities
# =============================================================================

class DatabaseCleanupManager:
    """
    Manages cleanup of test data from database.
    
    Provides utilities for:
    - Truncating all tables
    - Deleting specific records
    - Resetting sequences
    - Verifying clean state
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.cleanup_items = []
    
    def register_for_cleanup(self, model_class, record_id):
        """
        Register a model instance for cleanup.
        
        Args:
            model_class: SQLAlchemy model class
            record_id: Primary key of the record to delete
        """
        self.cleanup_items.append((model_class, record_id))
    
    def cleanup_registered_items(self):
        """Delete all registered items in reverse order."""
        for model_class, record_id in reversed(self.cleanup_items):
            try:
                instance = self.session.query(model_class).get(record_id)
                if instance:
                    self.session.delete(instance)
                self.session.commit()
            except Exception as e:
                logger.error(f"Failed to cleanup {model_class.__name__} {record_id}: {e}")
                self.session.rollback()
    
    def truncate_all_tables(self):
        """
        Truncate all tables in the database.
        
        Warning: This is a destructive operation. Only use in test environments.
        """
        # Ensure we're in a test environment
        if os.getenv("APP_ENV") != "test":
            raise RuntimeError("truncate_all_tables can only be used in test environment")
        
        try:
            # Get all table names
            tables = Base.metadata.tables.keys()
            
            # Disable foreign key checks (PostgreSQL)
            if self.session.bind.dialect.name == "postgresql":
                self.session.execute(text("SET session_replication_role = 'replica';"))
            
            # Truncate each table
            for table_name in tables:
                try:
                    if self.session.bind.dialect.name == "postgresql":
                        self.session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE;"))
                    elif self.session.bind.dialect.name == "sqlite":
                        self.session.execute(text(f"DELETE FROM {table_name};"))
                except Exception as e:
                    logger.warning(f"Failed to truncate table {table_name}: {e}")
            
            # Re-enable foreign key checks (PostgreSQL)
            if self.session.bind.dialect.name == "postgresql":
                self.session.execute(text("SET session_replication_role = 'origin';"))
            
            self.session.commit()
            logger.info(f"Truncated {len(tables)} tables")
            
        except Exception as e:
            logger.error(f"Failed to truncate tables: {e}")
            self.session.rollback()
            raise
    
    def reset_sequences(self):
        """
        Reset all sequences to 1.
        
        Only applicable for PostgreSQL.
        """
        if self.session.bind.dialect.name != "postgresql":
            return
        
        try:
            # Get all sequences
            result = self.session.execute(text(
                "SELECT sequence_name FROM information_schema.sequences "
                "WHERE sequence_schema = 'public'"
            ))
            sequences = [row[0] for row in result]
            
            # Reset each sequence
            for sequence_name in sequences:
                self.session.execute(text(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1;"))
            
            self.session.commit()
            logger.info(f"Reset {len(sequences)} sequences")
            
        except Exception as e:
            logger.error(f"Failed to reset sequences: {e}")
            self.session.rollback()
            raise
    
    def verify_clean_state(self) -> bool:
        """
        Verify that the database is in a clean state (no data).
        
        Returns:
            True if database is clean, False otherwise
        """
        try:
            tables = Base.metadata.tables.keys()
            
            for table_name in tables:
                result = self.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                
                if count > 0:
                    logger.warning(f"Table {table_name} has {count} rows")
                    return False
            
            logger.info("Database is in clean state")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify clean state: {e}")
            return False


# =============================================================================
# Production Database Access Prevention
# =============================================================================

def prevent_production_database_access():
    """
    Verify that tests are not accessing production database.
    
    Raises:
        RuntimeError: If production database access is detected
    """
    # Check environment
    app_env = os.getenv("APP_ENV", "development")
    if app_env == "production":
        raise RuntimeError(
            "Tests cannot run in production environment. "
            "Set APP_ENV=test to run tests."
        )
    
    # Check database URL
    database_url = os.getenv("DATABASE_URL", "")
    
    # List of patterns that indicate production database
    production_patterns = [
        "prod",
        "production",
        "rds.amazonaws.com",  # AWS RDS
        "cloudsql.com",  # Google Cloud SQL
        "database.azure.com",  # Azure Database
    ]
    
    for pattern in production_patterns:
        if pattern in database_url.lower():
            raise RuntimeError(
                f"Tests cannot access production database. "
                f"Database URL contains '{pattern}'. "
                f"Use a separate test database."
            )
    
    logger.info("Production database access prevention check passed")


# =============================================================================
# Test Database Setup and Teardown
# =============================================================================

def setup_test_database(engine: Engine):
    """
    Set up test database schema.
    
    Args:
        engine: Database engine to use
    """
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Test database schema created")
    except Exception as e:
        logger.error(f"Failed to create test database schema: {e}")
        raise


def teardown_test_database(engine: Engine):
    """
    Tear down test database schema.
    
    Args:
        engine: Database engine to use
    """
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("Test database schema dropped")
    except Exception as e:
        logger.error(f"Failed to drop test database schema: {e}")
        raise


def cleanup_test_database(session: Session):
    """
    Clean up test database by truncating all tables.
    
    Args:
        session: Database session to use
    """
    cleanup_manager = DatabaseCleanupManager(session)
    cleanup_manager.truncate_all_tables()
    cleanup_manager.reset_sequences()
