"""
Data type persistence tests.

Verifies all data types persist correctly through the API to the database
using the same SQLite in-memory approach as test_integration_api.py.

Requirements: 15.5 - Test persistence for text, number, date, file, select, checkbox fields.
"""

import pytest
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET

from src.database.connection import Base, get_db_session
from src.security.models import UserModel
from src.security.controller import SecurityController
from src.database.models import (
    TaskModel, TaskStatus, TaskPriority,
    AnnotationType, LabelStudioSyncStatus, SyncStatus,
)


# ── SQLite compatibility ────────────────────────────────────────────────────

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


# ── Constants ───────────────────────────────────────────────────────────────

TENANT_ID = "test_tenant"
JWT_SECRET = "test-secret-key-do-not-use-in-production"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _create_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _seed_user(session: Session) -> UserModel:
    sc = SecurityController(secret_key=JWT_SECRET)
    user = UserModel(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        password_hash=sc.hash_password("TestPass123!"),
        full_name="Test User",
        role="admin",
        tenant_id=TENANT_ID,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _build_app(session_factory, current_user_obj):
    from src.api.auth_simple import get_current_user as get_current_user_simple
    from src.api.tasks import router as tasks_router
    from src.api.auth import router as auth_router, get_current_user as get_current_user_auth

    app = FastAPI()
    app.include_router(tasks_router)
    app.include_router(auth_router)

    def _override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    async def _override_user():
        return current_user_obj

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_current_user_simple] = _override_user
    app.dependency_overrides[get_current_user_auth] = _override_user
    return app


# ── Fixture ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def env():
    engine = _create_engine()
    sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with sf() as session:
        user = _seed_user(session)

    from src.api.auth_simple import SimpleUser
    fake_user = SimpleUser(
        user_id=str(user.id),
        email=user.email,
        username=user.username,
        name=user.full_name,
        is_active=True,
        is_superuser=False,
    )
    fake_user.tenant_id = TENANT_ID

    app = _build_app(sf, fake_user)
    client = TestClient(app)

    yield client, sf, user

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ═════════════════════════════════════════════════════════════════════════════
# 1. Text Fields
# ═════════════════════════════════════════════════════════════════════════════

class TestTextFieldPersistence:
    """Verify text (String / Text) columns persist correctly."""

    def test_name_persists(self, env):
        """Task name (String 255) round-trips through API."""
        client, sf, _ = env
        resp = client.post("/api/tasks", json={"name": "Annotate batch 1", "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.name == "Annotate batch 1"

    def test_description_persists(self, env):
        """Task description (Text, nullable) round-trips through API."""
        client, sf, _ = env
        desc = "A longer description with special chars: é, ñ, 中文"
        resp = client.post("/api/tasks", json={"name": "Desc task", "description": desc, "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.description == desc

    def test_empty_description_persists_as_none(self, env):
        """Omitting description stores NULL."""
        client, sf, _ = env
        resp = client.post("/api/tasks", json={"name": "No desc", "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.description is None


# ═════════════════════════════════════════════════════════════════════════════
# 2. Integer Fields
# ═════════════════════════════════════════════════════════════════════════════

class TestIntegerFieldPersistence:
    """Verify Integer columns persist correctly."""

    def test_total_items_persists(self, env):
        """total_items (Integer) round-trips through API."""
        client, sf, _ = env
        resp = client.post("/api/tasks", json={"name": "Int task", "total_items": 500})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.total_items == 500

    def test_completed_items_persists(self, env):
        """completed_items updates persist via direct DB write."""
        _, sf, user = env
        with sf() as s:
            task = TaskModel(
                id=uuid4(), name="Comp task", title="Comp task",
                status=TaskStatus.IN_PROGRESS, priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id, tenant_id=TENANT_ID, project_id="proj_int",
                total_items=100, completed_items=42,
            )
            s.add(task)
            s.commit()
            s.refresh(task)
            assert task.completed_items == 42

    def test_zero_total_items(self, env):
        """Zero is a valid integer value."""
        _, sf, user = env
        with sf() as s:
            task = TaskModel(
                id=uuid4(), name="Zero task", title="Zero task",
                status=TaskStatus.PENDING, priority=TaskPriority.LOW,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id, tenant_id=TENANT_ID, project_id="proj_z",
                total_items=0,
            )
            s.add(task)
            s.commit()
            s.refresh(task)
            assert task.total_items == 0


# ═════════════════════════════════════════════════════════════════════════════
# 3. Enum / Select Fields
# ═════════════════════════════════════════════════════════════════════════════

class TestEnumFieldPersistence:
    """Verify Enum columns persist correctly."""

    def test_status_enum_persists_via_api(self, env):
        """TaskStatus enum round-trips through API create + update."""
        client, sf, _ = env
        resp = client.post("/api/tasks", json={"name": "Enum task", "total_items": 1})
        task_id = resp.json()["id"]

        client.patch(f"/api/tasks/{task_id}", json={"status": "in_progress"})

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.status == TaskStatus.IN_PROGRESS

    def test_priority_enum_persists(self, env):
        """TaskPriority enum round-trips through API."""
        client, sf, _ = env
        resp = client.post(
            "/api/tasks",
            json={"name": "Priority task", "priority": "urgent", "total_items": 1},
        )
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.priority == TaskPriority.URGENT

    def test_annotation_type_enum_persists(self, env):
        """AnnotationType enum round-trips through API."""
        client, sf, _ = env
        resp = client.post(
            "/api/tasks",
            json={"name": "Ann type task", "annotation_type": "ner", "total_items": 1},
        )
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.annotation_type == AnnotationType.NER

    def test_all_status_values_persist(self, env):
        """Every TaskStatus value can be stored and retrieved."""
        _, sf, user = env
        for status in TaskStatus:
            with sf() as s:
                tid = uuid4()
                s.add(TaskModel(
                    id=tid, name=f"S-{status.value}", title=f"S-{status.value}",
                    status=status, priority=TaskPriority.MEDIUM,
                    annotation_type=AnnotationType.CUSTOM,
                    created_by=user.id, tenant_id=TENANT_ID, project_id="proj_enum",
                ))
                s.commit()

            with sf() as s:
                task = s.query(TaskModel).filter_by(id=tid).first()
                assert task.status == status


# ═════════════════════════════════════════════════════════════════════════════
# 4. JSONB Fields
# ═════════════════════════════════════════════════════════════════════════════

class TestJsonbFieldPersistence:
    """Verify JSONB columns persist correctly."""

    def test_annotations_list_persists(self, env):
        """annotations (JSONB list) round-trips."""
        _, sf, user = env
        annotations = [{"label": "pos", "text": "good"}, {"label": "neg", "text": "bad"}]
        with sf() as s:
            tid = uuid4()
            s.add(TaskModel(
                id=tid, name="JSONB ann", title="JSONB ann",
                status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id, tenant_id=TENANT_ID, project_id="proj_jb",
                annotations=annotations,
            ))
            s.commit()

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=tid).first()
            assert task.annotations == annotations

    def test_ai_predictions_persists(self, env):
        """ai_predictions (JSONB list) round-trips."""
        _, sf, user = env
        preds = [{"model": "gpt-4", "confidence": 0.95, "label": "positive"}]
        with sf() as s:
            tid = uuid4()
            s.add(TaskModel(
                id=tid, name="JSONB pred", title="JSONB pred",
                status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id, tenant_id=TENANT_ID, project_id="proj_jp",
                ai_predictions=preds,
            ))
            s.commit()

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=tid).first()
            assert task.ai_predictions[0]["model"] == "gpt-4"
            assert task.ai_predictions[0]["confidence"] == pytest.approx(0.95)

    def test_metadata_dict_persists(self, env):
        """task_metadata (JSONB dict) round-trips with nested structure."""
        _, sf, user = env
        meta = {"source": "upload", "config": {"batch_size": 32, "tags": ["a", "b"]}}
        with sf() as s:
            tid = uuid4()
            s.add(TaskModel(
                id=tid, name="JSONB meta", title="JSONB meta",
                status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id, tenant_id=TENANT_ID, project_id="proj_jm",
                task_metadata=meta,
            ))
            s.commit()

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=tid).first()
            assert task.task_metadata["config"]["batch_size"] == 32
            assert task.task_metadata["config"]["tags"] == ["a", "b"]

    def test_tags_list_persists(self, env):
        """tags (JSONB list of strings) round-trips."""
        _, sf, user = env
        tags = ["urgent", "review-needed", "batch-3"]
        with sf() as s:
            tid = uuid4()
            s.add(TaskModel(
                id=tid, name="JSONB tags", title="JSONB tags",
                status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id, tenant_id=TENANT_ID, project_id="proj_jt",
                tags=tags,
            ))
            s.commit()

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=tid).first()
            assert task.tags == tags


# ═════════════════════════════════════════════════════════════════════════════
# 5. UUID Fields
# ═════════════════════════════════════════════════════════════════════════════

class TestUuidFieldPersistence:
    """Verify UUID columns persist correctly."""

    def test_task_id_is_valid_uuid(self, env):
        """Task id (UUID PK) is a valid UUID after API create."""
        client, sf, _ = env
        resp = client.post("/api/tasks", json={"name": "UUID task", "total_items": 1})
        task_id = resp.json()["id"]

        # Should parse without error
        parsed = PyUUID(task_id)
        with sf() as s:
            task = s.query(TaskModel).filter_by(id=parsed).first()
            assert task is not None

    def test_created_by_uuid_persists(self, env):
        """created_by (UUID FK) matches the seeded user."""
        client, sf, user = env
        resp = client.post("/api/tasks", json={"name": "CB task", "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.created_by == user.id


# ═════════════════════════════════════════════════════════════════════════════
# 6. DateTime Fields
# ═════════════════════════════════════════════════════════════════════════════

class TestDateTimeFieldPersistence:
    """Verify DateTime columns persist correctly."""

    def test_created_at_auto_set(self, env):
        """created_at is automatically populated on insert."""
        client, sf, _ = env
        resp = client.post("/api/tasks", json={"name": "DT task", "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.created_at is not None

    def test_due_date_nullable_persists(self, env):
        """due_date (DateTime, nullable) stores and retrieves correctly."""
        _, sf, user = env
        due = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        with sf() as s:
            tid = uuid4()
            s.add(TaskModel(
                id=tid, name="Due task", title="Due task",
                status=TaskStatus.PENDING, priority=TaskPriority.HIGH,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id, tenant_id=TENANT_ID, project_id="proj_dt",
                due_date=due,
            ))
            s.commit()

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=tid).first()
            assert task.due_date is not None
            assert task.due_date.year == 2025
            assert task.due_date.month == 12

    def test_due_date_none_when_omitted(self, env):
        """due_date defaults to None when not provided."""
        client, sf, _ = env
        resp = client.post("/api/tasks", json={"name": "No due", "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.due_date is None


# ═════════════════════════════════════════════════════════════════════════════
# 7. Float Fields
# ═════════════════════════════════════════════════════════════════════════════

class TestFloatFieldPersistence:
    """Verify Float columns persist correctly."""

    def test_quality_score_persists(self, env):
        """quality_score (Float) round-trips."""
        _, sf, user = env
        with sf() as s:
            tid = uuid4()
            s.add(TaskModel(
                id=tid, name="QS task", title="QS task",
                status=TaskStatus.COMPLETED, priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id, tenant_id=TENANT_ID, project_id="proj_fl",
                quality_score=0.87,
            ))
            s.commit()

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=tid).first()
            assert task.quality_score == pytest.approx(0.87, abs=0.001)

    def test_quality_score_default_zero(self, env):
        """quality_score defaults to 0.0."""
        client, sf, _ = env
        resp = client.post("/api/tasks", json={"name": "QS default", "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.quality_score == pytest.approx(0.0)


# ═════════════════════════════════════════════════════════════════════════════
# 8. Boolean-like Fields (is_active, is_from_sync)
# ═════════════════════════════════════════════════════════════════════════════

class TestBooleanFieldPersistence:
    """Verify Boolean columns persist correctly."""

    def test_user_is_active_true(self, env):
        """UserModel.is_active=True persists."""
        _, sf, user = env
        with sf() as s:
            db_user = s.query(UserModel).filter_by(id=user.id).first()
            assert db_user.is_active is True

    def test_user_is_active_false(self, env):
        """UserModel.is_active=False persists."""
        _, sf, _ = env
        sc = SecurityController(secret_key=JWT_SECRET)
        with sf() as s:
            inactive = UserModel(
                id=uuid4(), username="inactive", email="inactive@example.com",
                password_hash=sc.hash_password("Pass123!"),
                full_name="Inactive User", role="viewer",
                tenant_id=TENANT_ID, is_active=False,
            )
            s.add(inactive)
            s.commit()

        with sf() as s:
            db_user = s.query(UserModel).filter_by(username="inactive").first()
            assert db_user.is_active is False

    def test_is_from_sync_boolean_persists(self, env):
        """TaskModel.is_from_sync (Boolean) round-trips."""
        _, sf, user = env
        with sf() as s:
            tid = uuid4()
            s.add(TaskModel(
                id=tid, name="Sync task", title="Sync task",
                status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id, tenant_id=TENANT_ID, project_id="proj_bool",
                is_from_sync=True,
            ))
            s.commit()

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=tid).first()
            assert task.is_from_sync is True
