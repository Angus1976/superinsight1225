"""
Unit tests for Concurrent Manager (Optimistic Locking).

Tests version conflict detection, 409 Conflict error generation,
retry logic, and the concurrent middleware error handler.

Validates: Requirements 22.1, 22.2, 22.3, 22.4
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy import create_engine, Table, Column, String, Integer, DateTime, JSON, MetaData
from sqlalchemy.orm import sessionmaker

from src.services.concurrent_manager import (
    ConcurrentModificationError,
    OptimisticLockManager,
    retry_on_conflict,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite session with a simple test table."""
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    Table(
        "samples",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("category", String(100), nullable=False),
        Column("lock_version", Integer, nullable=False, default=1),
        Column("content", JSON, nullable=False, default=dict),
        Column("updated_at", DateTime, nullable=True),
    )
    metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class FakeModel:
    """Lightweight stand-in for a SQLAlchemy model row."""

    def __init__(self, id=None, lock_version=1, category="test"):
        self.id = id or str(uuid4())
        self.lock_version = lock_version
        self.category = category


# ---------------------------------------------------------------------------
# ConcurrentModificationError
# ---------------------------------------------------------------------------

class TestConcurrentModificationError:
    """Tests for the custom exception."""

    def test_attributes(self):
        err = ConcurrentModificationError(
            resource_id="abc",
            resource_type="Sample",
            expected_version=1,
            actual_version=2,
        )
        assert err.resource_id == "abc"
        assert err.resource_type == "Sample"
        assert err.expected_version == 1
        assert err.actual_version == 2

    def test_message_contains_versions(self):
        err = ConcurrentModificationError("id1", "Sample", 1, 3)
        msg = str(err)
        assert "1" in msg
        assert "3" in msg
        assert "Sample" in msg

    def test_to_conflict_detail(self):
        err = ConcurrentModificationError("id1", "Sample", 1, 2)
        detail = err.to_conflict_detail()
        assert detail["error"] == "conflict"
        assert detail["resource_id"] == "id1"
        assert detail["resource_type"] == "Sample"
        assert detail["expected_version"] == 1
        assert detail["actual_version"] == 2
        assert "message" in detail


# ---------------------------------------------------------------------------
# OptimisticLockManager – check_and_increment_version
# ---------------------------------------------------------------------------

class TestCheckAndIncrementVersion:
    """Tests for version checking and incrementing."""

    def test_matching_version_increments(self, db_session):
        mgr = OptimisticLockManager(db_session)
        model = FakeModel(lock_version=1)

        mgr.check_and_increment_version(model, expected_version=1)
        assert model.lock_version == 2

    def test_mismatched_version_raises(self, db_session):
        mgr = OptimisticLockManager(db_session)
        model = FakeModel(lock_version=3)

        with pytest.raises(ConcurrentModificationError) as exc_info:
            mgr.check_and_increment_version(model, expected_version=1)

        assert exc_info.value.expected_version == 1
        assert exc_info.value.actual_version == 3

    def test_missing_version_field_raises_value_error(self, db_session):
        mgr = OptimisticLockManager(db_session)

        class NoVersion:
            id = "x"

        with pytest.raises(ValueError, match="no_such_field"):
            mgr.check_and_increment_version(
                NoVersion(), expected_version=1, version_field="no_such_field"
            )

    def test_custom_version_field(self, db_session):
        mgr = OptimisticLockManager(db_session)

        class CustomModel:
            id = "y"
            my_ver = 5

        mgr.check_and_increment_version(
            CustomModel(), expected_version=5, version_field="my_ver"
        )

    def test_custom_resource_type_in_error(self, db_session):
        mgr = OptimisticLockManager(db_session)
        model = FakeModel(lock_version=2)

        with pytest.raises(ConcurrentModificationError) as exc_info:
            mgr.check_and_increment_version(
                model, expected_version=1, resource_type="AnnotationTask"
            )

        assert exc_info.value.resource_type == "AnnotationTask"


# ---------------------------------------------------------------------------
# OptimisticLockManager – safe_update
# ---------------------------------------------------------------------------

class TestSafeUpdate:
    """Tests for the safe_update convenience method."""

    def test_applies_updates_on_matching_version(self, db_session):
        mgr = OptimisticLockManager(db_session)
        model = FakeModel(lock_version=1, category="old")

        result = mgr.safe_update(
            model, expected_version=1, updates={"category": "new"}
        )

        assert result.category == "new"
        assert result.lock_version == 2

    def test_raises_on_version_mismatch(self, db_session):
        mgr = OptimisticLockManager(db_session)
        model = FakeModel(lock_version=5, category="old")

        with pytest.raises(ConcurrentModificationError):
            mgr.safe_update(
                model, expected_version=2, updates={"category": "new"}
            )

        # Original value unchanged
        assert model.category == "old"
        assert model.lock_version == 5

    def test_ignores_unknown_fields(self, db_session):
        mgr = OptimisticLockManager(db_session)
        model = FakeModel(lock_version=1)

        mgr.safe_update(
            model,
            expected_version=1,
            updates={"nonexistent_field": "value"},
        )
        assert not hasattr(model, "nonexistent_field")

    def test_multiple_fields_updated(self, db_session):
        mgr = OptimisticLockManager(db_session)

        class Multi:
            id = "m1"
            lock_version = 1
            a = "x"
            b = "y"

        obj = Multi()
        mgr.safe_update(obj, expected_version=1, updates={"a": "A", "b": "B"})
        assert obj.a == "A"
        assert obj.b == "B"
        assert obj.lock_version == 2


# ---------------------------------------------------------------------------
# retry_on_conflict
# ---------------------------------------------------------------------------

class TestRetryOnConflict:
    """Tests for the retry utility."""

    def test_succeeds_on_first_try(self):
        result = retry_on_conflict(lambda: 42, max_retries=3, base_delay=0)
        assert result == 42

    def test_retries_then_succeeds(self):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConcurrentModificationError("r1", "T", 1, 2)
            return "ok"

        result = retry_on_conflict(flaky, max_retries=3, base_delay=0)
        assert result == "ok"
        assert call_count == 3

    def test_exhausts_retries_and_raises(self):
        def always_fail():
            raise ConcurrentModificationError("r1", "T", 1, 2)

        with pytest.raises(ConcurrentModificationError) as exc_info:
            retry_on_conflict(always_fail, max_retries=2, base_delay=0)

        assert exc_info.value.resource_id == "r1"

    def test_zero_retries_raises_immediately(self):
        calls = 0

        def fail_once():
            nonlocal calls
            calls += 1
            raise ConcurrentModificationError("r1", "T", 1, 2)

        with pytest.raises(ConcurrentModificationError):
            retry_on_conflict(fail_once, max_retries=0, base_delay=0)

        assert calls == 1

    def test_negative_retries_raises_value_error(self):
        with pytest.raises(ValueError, match="max_retries"):
            retry_on_conflict(lambda: None, max_retries=-1, base_delay=0)

    @patch("src.services.concurrent_manager.time.sleep")
    def test_exponential_backoff(self, mock_sleep):
        call_count = 0

        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConcurrentModificationError("r1", "T", 1, 2)
            return "done"

        retry_on_conflict(fail_twice, max_retries=3, base_delay=0.1)

        assert mock_sleep.call_count == 2
        delays = [c.args[0] for c in mock_sleep.call_args_list]
        assert abs(delays[0] - 0.1) < 1e-9
        assert abs(delays[1] - 0.2) < 1e-9

    def test_passes_args_and_kwargs(self):
        def add(a, b, extra=0):
            return a + b + extra

        result = retry_on_conflict(
            add, max_retries=0, base_delay=0, a=1, b=2, extra=10
        )
        assert result == 13


# ---------------------------------------------------------------------------
# Concurrent Middleware (error handler)
# ---------------------------------------------------------------------------

class TestConcurrentMiddleware:
    """Tests for the 409 error handler."""

    @pytest.mark.asyncio
    async def test_handler_returns_409(self):
        from src.middleware.concurrent_middleware import concurrent_modification_handler

        request = MagicMock()
        request.method = "PUT"
        request.url.path = "/api/samples/123"

        exc = ConcurrentModificationError("123", "Sample", 1, 2)
        response = await concurrent_modification_handler(request, exc)

        assert response.status_code == 409
        import json
        body = json.loads(response.body.decode())
        assert body["error"] == "conflict"
        assert body["expected_version"] == 1
        assert body["actual_version"] == 2

    def test_register_handler(self):
        from src.middleware.concurrent_middleware import register_concurrent_error_handler

        app = MagicMock()
        register_concurrent_error_handler(app)
        app.add_exception_handler.assert_called_once()


# ---------------------------------------------------------------------------
# Model lock_version column existence
# ---------------------------------------------------------------------------

class TestModelLockVersionColumns:
    """Verify that the lock_version column exists on key models."""

    def test_temp_data_model_has_lock_version(self):
        from src.models.data_lifecycle import TempDataModel
        assert hasattr(TempDataModel, "lock_version")

    def test_sample_model_has_lock_version(self):
        from src.models.data_lifecycle import SampleModel
        assert hasattr(SampleModel, "lock_version")

    def test_annotation_task_model_has_lock_version(self):
        from src.models.data_lifecycle import AnnotationTaskModel
        assert hasattr(AnnotationTaskModel, "lock_version")
