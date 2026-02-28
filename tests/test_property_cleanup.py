"""
Property-based tests for test data cleanup.

**Feature: comprehensive-testing-qa-system, Property 11: Test Data Cleanup**
**Validates: Requirements 3.6, 11.7**

Verifies that after test data is created and cleanup runs, no test data
remains in the database or cache. Uses Hypothesis to generate diverse
entity combinations and confirms that cleanup mechanisms (transaction
rollback for DB, key deletion for Redis) leave the environment clean.
"""

from uuid import uuid4

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock

from src.database.connection import Base
from src.database.models import (
    DocumentModel,
    TaskModel,
    TaskStatus,
    TaskPriority,
    AnnotationType,
    BillingRecordModel,
    QualityIssueModel,
    IssueSeverity,
    IssueStatus,
)
from src.security.models import (
    UserModel,
    UserRole,
    ProjectPermissionModel,
    PermissionType,
)
from tests.database_isolation import DatabaseCleanupManager


# =============================================================================
# SQLite Compatibility
# =============================================================================

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


# =============================================================================
# Engine / Session Helpers
# =============================================================================

def _create_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


_ENGINE = _create_engine()
_SessionFactory = sessionmaker(bind=_ENGINE, autoflush=False)


@pytest.fixture()
def session():
    """Provide a transactional session that rolls back after each test."""
    connection = _ENGINE.connect()
    transaction = connection.begin()
    sess = _SessionFactory(bind=connection)

    yield sess

    sess.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def mock_redis():
    """Provide a dict-backed mock Redis for cache cleanup tests."""
    store = {}

    mock = MagicMock()
    mock.set.side_effect = lambda k, v, *a, **kw: store.update({k: v}) or True
    mock.get.side_effect = lambda k, *a, **kw: store.get(k)
    mock.delete.side_effect = lambda *keys, **kw: sum(1 for k in keys if store.pop(k, None) is not None)
    mock.keys.side_effect = lambda pattern="*", **kw: [
        k for k in store
        if pattern == "*" or k.startswith(pattern.rstrip("*"))
    ]
    mock.flushdb.side_effect = lambda **kw: store.clear() or True
    mock.exists.side_effect = lambda *keys, **kw: sum(1 for k in keys if k in store)
    mock.ping.return_value = True

    # Expose the backing store for assertions
    mock._store = store
    return mock


# =============================================================================
# Factory Helpers (same as test_property_factory_relationships.py)
# =============================================================================

def create_user(session, **overrides):
    defaults = {
        "id": uuid4(),
        "username": f"user_{uuid4().hex[:8]}",
        "email": f"test_{uuid4().hex[:8]}@example.com",
        "password_hash": "hashed_pw_placeholder",
        "full_name": "Test User",
        "role": UserRole.VIEWER.value,
        "tenant_id": "test_tenant",
        "is_active": True,
    }
    defaults.update(overrides)
    user = UserModel(**defaults)
    session.add(user)
    session.flush()
    return user


def create_document(session, **overrides):
    defaults = {
        "id": uuid4(),
        "source_type": "test",
        "source_config": {"type": "test"},
        "content": "Test document content",
        "document_metadata": {},
    }
    defaults.update(overrides)
    doc = DocumentModel(**defaults)
    session.add(doc)
    session.flush()
    return doc


def create_task(session, *, created_by, document_id=None, **overrides):
    defaults = {
        "id": uuid4(),
        "title": f"Task {uuid4().hex[:6]}",
        "name": f"Task {uuid4().hex[:6]}",
        "project_id": "test_project",
        "created_by": created_by,
        "document_id": document_id,
        "status": TaskStatus.PENDING,
        "priority": TaskPriority.MEDIUM,
        "annotation_type": AnnotationType.CUSTOM,
        "tenant_id": "test_tenant",
    }
    defaults.update(overrides)
    task = TaskModel(**defaults)
    session.add(task)
    session.flush()
    return task


# =============================================================================
# Hypothesis Strategies
# =============================================================================

entity_count = st.integers(min_value=1, max_value=5)

cache_key_count = st.integers(min_value=1, max_value=10)

cache_keys = st.lists(
    st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
        min_size=3,
        max_size=20,
    ),
    min_size=1,
    max_size=10,
    unique=True,
)

cache_values = st.text(min_size=1, max_size=50)

REDIS_TEST_PREFIX = "superinsight:test:"


# =============================================================================
# Property Tests
# =============================================================================

class TestDataCleanup:
    """
    Property 11: Test Data Cleanup

    For any test execution that creates test data, the test environment
    SHALL be in a clean state (no test data remaining) after the test
    completes.
    """

    # -----------------------------------------------------------------
    # Database cleanup via transaction rollback
    # -----------------------------------------------------------------

    @given(num_users=entity_count, num_tasks=entity_count)
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_db_transaction_rollback_leaves_no_data(
        self, session, num_users, num_tasks
    ):
        """
        After creating arbitrary numbers of users, documents, and tasks
        inside a transaction, rolling back leaves all tables empty.

        **Validates: Requirements 3.6, 11.7**
        """
        # --- Arrange: create data inside the transactional session ---
        users = [create_user(session) for _ in range(num_users)]
        doc = create_document(session)
        for _ in range(num_tasks):
            create_task(session, created_by=users[0].id, document_id=doc.id)

        # Verify data exists before cleanup
        user_count = session.query(UserModel).count()
        task_count = session.query(TaskModel).count()
        assert user_count >= num_users
        assert task_count >= num_tasks

        # --- Act: rollback the transaction (simulating test teardown) ---
        session.rollback()

        # --- Assert: all tables are empty after rollback ---
        assert session.query(UserModel).count() == 0
        assert session.query(DocumentModel).count() == 0
        assert session.query(TaskModel).count() == 0

    @given(num_entities=entity_count)
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_db_cleanup_manager_verifies_clean_state(
        self, session, num_entities
    ):
        """
        After creating entities and deleting them in FK-safe order,
        DatabaseCleanupManager.verify_clean_state confirms no data remains.

        **Validates: Requirements 3.6, 11.7**
        """
        # --- Arrange ---
        users_created = []
        for _ in range(num_entities):
            user = create_user(session)
            doc = create_document(session)
            create_task(session, created_by=user.id, document_id=doc.id)
            users_created.append(user)
        session.flush()

        # Verify data exists
        assert session.query(UserModel).count() > 0
        assert session.query(TaskModel).count() > 0

        # --- Act: delete in FK-safe order (children first) ---
        # SQLite enforces FK constraints, so we must respect dependency order
        for model in [TaskModel, DocumentModel, ProjectPermissionModel, UserModel]:
            session.query(model).delete()
        session.flush()

        # --- Assert ---
        cleanup = DatabaseCleanupManager(session)
        assert cleanup.verify_clean_state() is True

    # -----------------------------------------------------------------
    # Redis / cache cleanup
    # -----------------------------------------------------------------

    @given(keys=cache_keys, value=cache_values)
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_redis_prefix_cleanup_removes_all_test_keys(
        self, mock_redis, keys, value
    ):
        """
        After inserting arbitrary test-prefixed keys into Redis,
        deleting by prefix leaves no test keys remaining.

        **Validates: Requirements 3.6, 11.7**
        """
        # --- Arrange: insert keys with test prefix ---
        prefixed_keys = [f"{REDIS_TEST_PREFIX}{k}" for k in keys]
        for pk in prefixed_keys:
            mock_redis.set(pk, value)

        # Verify keys exist
        found = mock_redis.keys(f"{REDIS_TEST_PREFIX}*")
        assert len(found) == len(keys)

        # --- Act: cleanup by prefix ---
        matching = mock_redis.keys(f"{REDIS_TEST_PREFIX}*")
        if matching:
            mock_redis.delete(*matching)

        # --- Assert: no test keys remain ---
        remaining = mock_redis.keys(f"{REDIS_TEST_PREFIX}*")
        assert len(remaining) == 0

    @given(keys=cache_keys, value=cache_values)
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_redis_flushdb_removes_all_keys(
        self, mock_redis, keys, value
    ):
        """
        flushdb() removes every key in the test database, leaving
        a completely clean cache state.

        **Validates: Requirements 3.6, 11.7**
        """
        # --- Arrange ---
        for k in keys:
            mock_redis.set(k, value)
        assert len(mock_redis.keys("*")) == len(keys)

        # --- Act ---
        mock_redis.flushdb()

        # --- Assert ---
        assert len(mock_redis.keys("*")) == 0

    # -----------------------------------------------------------------
    # Combined DB + cache cleanup
    # -----------------------------------------------------------------

    @given(num_entities=entity_count, cache_key_list=cache_keys, value=cache_values)
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_combined_db_and_cache_cleanup(
        self, session, mock_redis, num_entities, cache_key_list, value
    ):
        """
        After creating data in both database and cache, running cleanup
        on both leaves the entire test environment clean.

        **Validates: Requirements 3.6, 11.7**
        """
        # --- Arrange: populate DB ---
        for _ in range(num_entities):
            user = create_user(session)
            create_task(session, created_by=user.id)

        # --- Arrange: populate cache ---
        prefixed = [f"{REDIS_TEST_PREFIX}{k}" for k in cache_key_list]
        for pk in prefixed:
            mock_redis.set(pk, value)

        # Verify both have data
        assert session.query(UserModel).count() > 0
        assert len(mock_redis.keys(f"{REDIS_TEST_PREFIX}*")) > 0

        # --- Act: cleanup DB via rollback ---
        session.rollback()

        # --- Act: cleanup cache via prefix deletion ---
        remaining_keys = mock_redis.keys(f"{REDIS_TEST_PREFIX}*")
        if remaining_keys:
            mock_redis.delete(*remaining_keys)

        # --- Assert: both are clean ---
        assert session.query(UserModel).count() == 0
        assert session.query(TaskModel).count() == 0
        assert len(mock_redis.keys(f"{REDIS_TEST_PREFIX}*")) == 0
