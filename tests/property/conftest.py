"""
Pytest configuration for property-based tests.

Provides fixtures for database sessions and other test utilities.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.models.data_lifecycle import (
    PermissionModel,
    AuditLogModel,
    TempDataModel,
    SampleModel,
    AnnotationTaskModel,
    EnhancedDataModel,
    VersionModel,
)

from tests.property.sqlite_uuid_compat import (
    snapshot_uuid_columns,
    patch_models_to_sqlite_uuid,
    restore_uuid_columns,
)

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

# Captured at import time (before any test mutates mapped column types).
_UUID_COLUMN_SNAPSHOT = snapshot_uuid_columns(PATCHED_MODELS)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Create an in-memory SQLite database session for property tests.

    This fixture creates only the data lifecycle tables needed for testing,
    with UUID columns patched for SQLite compatibility.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    restore = patch_models_to_sqlite_uuid(PATCHED_MODELS, _UUID_COLUMN_SNAPSHOT)

    try:
        for model in PATCHED_MODELS:
            model.__table__.create(bind=engine, checkfirst=True)

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()
    finally:
        restore_uuid_columns(restore)
