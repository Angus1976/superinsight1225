"""
Pytest fixtures for AI Integration audit service tests.

Provides database session fixtures for testing.
"""

import pytest
from typing import Generator
from sqlalchemy import create_engine, Table, Column, String, Boolean, Text, DateTime, JSON, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql import func


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
    
    # Create audit log table manually for SQLite (using JSON instead of JSONB)
    metadata = MetaData()
    ai_audit_logs = Table(
        'ai_audit_logs',
        metadata,
        Column('id', String(36), primary_key=True),
        Column('gateway_id', String(36), nullable=False, index=True),
        Column('tenant_id', String(36), nullable=False, index=True),
        Column('event_type', String(50), nullable=False, index=True),
        Column('resource', String(255), nullable=False),
        Column('action', String(50), nullable=False),
        Column('metadata', JSON, nullable=False, default={}),
        Column('user_identifier', String(255), nullable=True),
        Column('channel', String(50), nullable=True),
        Column('success', Boolean, nullable=False, default=True),
        Column('error_message', Text, nullable=True),
        Column('timestamp', DateTime(timezone=True), server_default=func.now(), index=True),
        Column('signature', String(255), nullable=False),
    )
    
    metadata.create_all(bind=engine)
    
    yield engine
    
    metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
