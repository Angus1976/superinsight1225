"""
Pytest configuration for property-based tests.

Provides fixtures for database sessions and other test utilities.
"""

import pytest
from uuid import UUID
from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from src.models.data_lifecycle import (
    Base,
    PermissionModel,
    AuditLogModel,
    TempDataModel,
    SampleModel,
    AnnotationTaskModel,
    EnhancedDataModel,
    VersionModel,
)


# ============================================================================
# SQLite UUID Compatibility
# ============================================================================

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


# Models that need UUID patching
PATCHED_MODELS = [
    PermissionModel,
    AuditLogModel,
    TempDataModel,
    SampleModel,
    AnnotationTaskModel,
    EnhancedDataModel,
    VersionModel,
]


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Create an in-memory SQLite database session for property tests.
    
    This fixture creates only the data lifecycle tables needed for testing,
    with UUID columns patched for SQLite compatibility.
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Patch UUID columns for SQLite compatibility
    for model in PATCHED_MODELS:
        for col in model.__table__.columns:
            if isinstance(col.type, PGUUID):
                col.type = SQLiteUUID()
    
    # Create tables
    for model in PATCHED_MODELS:
        model.__table__.create(bind=engine, checkfirst=True)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
