"""
Unit tests for task management module.

Tests cover:
- Task creation with valid data
- Task retrieval by ID and filters
- Task update operations
- Task deletion and soft delete
- Task assignment to users
- Task status transitions

Requirements: 1.1
"""

import pytest
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.database.models import (
    TaskModel, TaskStatus, TaskPriority,
    AnnotationType, LabelStudioSyncStatus,
)
from src.security.models import UserModel, UserRole


# =============================================================================
# SQLite compatibility
# =============================================================================

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


# =============================================================================
# Constants
# =============================================================================

TENANT_ID = "test_tenant"
PROJECT_ID = "test_project"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def engine():
    """Create an isolated SQLite in-memory engine."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture(scope="function")
def session(engine) -> Session:
    """Provide a session with transaction rollback per test."""
    connection = engine.connect()
    transaction = connection.begin()
    sf = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    sess = sf()

    yield sess

    sess.close()
    transaction.rollback()
    connection.close()


def _make_user(session: Session, **overrides) -> UserModel:
    """Insert a user and return the ORM instance."""
    defaults = dict(
        id=uuid4(),
        username=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password_hash="hashed_pw",
        full_name="Test User",
        role=UserRole.ADMIN.value,
        tenant_id=TENANT_ID,
        is_active=True,
    )
    defaults.update(overrides)
    user = UserModel(**defaults)
    session.add(user)
    session.flush()
    return user


def _make_task(session: Session, created_by: PyUUID, **overrides) -> TaskModel:
    """Insert a task and return the ORM instance."""
    defaults = dict(
        id=uuid4(),
        title="Test Task",
        name="Test Task",
        description="A test task",
        status=TaskStatus.PENDING,
        priority=TaskPriority.MEDIUM,
        annotation_type=AnnotationType.CUSTOM,
        created_by=created_by,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        total_items=10,
        completed_items=0,
        progress=0,
    )
    defaults.update(overrides)
    task = TaskModel(**defaults)
    session.add(task)
    session.flush()
    return task


# =============================================================================
# 1. Task Creation
# =============================================================================

class TestTaskCreation:
    """Test task creation with valid data."""

    def test_create_task_with_defaults(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id)

        assert task.id is not None
        assert task.name == "Test Task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.tenant_id == TENANT_ID

    def test_create_task_with_all_fields(self, session):
        user = _make_user(session)
        due = datetime.now(timezone.utc) + timedelta(days=7)
        task = _make_task(
            session,
            created_by=user.id,
            name="Full Task",
            description="Detailed description",
            priority=TaskPriority.HIGH,
            annotation_type=AnnotationType.CUSTOM,
            due_date=due,
            total_items=100,
            tags=["nlp", "urgent"],
        )

        assert task.name == "Full Task"
        assert task.description == "Detailed description"
        assert task.priority == TaskPriority.HIGH
        assert task.total_items == 100
        assert task.tags == ["nlp", "urgent"]
        assert task.due_date is not None

    def test_create_task_persists_to_db(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, name="Persisted")
        session.commit()

        fetched = session.query(TaskModel).filter_by(id=task.id).first()
        assert fetched is not None
        assert fetched.name == "Persisted"

    def test_create_task_with_jsonb_fields(self, session):
        user = _make_user(session)
        task = _make_task(
            session,
            created_by=user.id,
            annotations=[{"label": "pos", "text": "good"}],
            ai_predictions=[{"model": "gpt-4", "confidence": 0.9}],
            task_metadata={"source": "upload"},
        )
        session.commit()

        fetched = session.query(TaskModel).filter_by(id=task.id).first()
        assert fetched.annotations[0]["label"] == "pos"
        assert fetched.ai_predictions[0]["model"] == "gpt-4"
        assert fetched.task_metadata["source"] == "upload"

    def test_create_multiple_tasks_same_project(self, session):
        user = _make_user(session)
        t1 = _make_task(session, created_by=user.id, name="Task A")
        t2 = _make_task(session, created_by=user.id, name="Task B")
        session.commit()

        tasks = session.query(TaskModel).filter_by(project_id=PROJECT_ID).all()
        names = {t.name for t in tasks}
        assert {"Task A", "Task B"}.issubset(names)


# =============================================================================
# 2. Task Retrieval
# =============================================================================

class TestTaskRetrieval:
    """Test task retrieval by ID and filters."""

    def test_get_task_by_id(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, name="FindMe")
        session.commit()

        result = session.query(TaskModel).filter_by(id=task.id).first()
        assert result is not None
        assert result.name == "FindMe"

    def test_get_nonexistent_task_returns_none(self, session):
        result = session.query(TaskModel).filter_by(id=uuid4()).first()
        assert result is None

    def test_filter_by_status(self, session):
        user = _make_user(session)
        _make_task(session, created_by=user.id, status=TaskStatus.PENDING)
        _make_task(session, created_by=user.id, status=TaskStatus.IN_PROGRESS)
        _make_task(session, created_by=user.id, status=TaskStatus.COMPLETED)
        session.commit()

        pending = session.query(TaskModel).filter_by(status=TaskStatus.PENDING).all()
        assert len(pending) >= 1
        assert all(t.status == TaskStatus.PENDING for t in pending)

    def test_filter_by_priority(self, session):
        user = _make_user(session)
        _make_task(session, created_by=user.id, priority=TaskPriority.URGENT)
        _make_task(session, created_by=user.id, priority=TaskPriority.LOW)
        session.commit()

        urgent = session.query(TaskModel).filter_by(priority=TaskPriority.URGENT).all()
        assert len(urgent) >= 1
        assert all(t.priority == TaskPriority.URGENT for t in urgent)

    def test_filter_by_tenant(self, session):
        user = _make_user(session)
        _make_task(session, created_by=user.id, tenant_id="tenant_a", name="A")
        _make_task(session, created_by=user.id, tenant_id="tenant_b", name="B")
        session.commit()

        results = session.query(TaskModel).filter_by(tenant_id="tenant_a").all()
        assert all(t.tenant_id == "tenant_a" for t in results)

    def test_filter_by_assignee(self, session):
        user = _make_user(session)
        assignee = _make_user(session)
        _make_task(session, created_by=user.id, assignee_id=assignee.id)
        _make_task(session, created_by=user.id, assignee_id=None)
        session.commit()

        assigned = session.query(TaskModel).filter_by(assignee_id=assignee.id).all()
        assert len(assigned) >= 1
        assert all(t.assignee_id == assignee.id for t in assigned)


# =============================================================================
# 3. Task Update Operations
# =============================================================================

class TestTaskUpdate:
    """Test task update operations."""

    def test_update_name(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, name="Old Name")
        session.commit()

        task.name = "New Name"
        session.commit()
        session.refresh(task)
        assert task.name == "New Name"

    def test_update_description(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, description="Old")
        session.commit()

        task.description = "Updated description"
        session.commit()
        session.refresh(task)
        assert task.description == "Updated description"

    def test_update_priority(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, priority=TaskPriority.LOW)
        session.commit()

        task.priority = TaskPriority.URGENT
        session.commit()
        session.refresh(task)
        assert task.priority == TaskPriority.URGENT

    def test_update_progress(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, total_items=10, completed_items=0)
        session.commit()

        task.completed_items = 5
        task.progress = 50
        session.commit()
        session.refresh(task)
        assert task.completed_items == 5
        assert task.progress == 50

    def test_update_quality_score(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, quality_score=0.0)
        session.commit()

        task.quality_score = 0.95
        session.commit()
        session.refresh(task)
        assert task.quality_score == pytest.approx(0.95, abs=0.01)

    def test_update_tags(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, tags=["old"])
        session.commit()

        task.tags = ["new", "updated"]
        session.commit()
        session.refresh(task)
        assert task.tags == ["new", "updated"]

    def test_update_due_date(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, due_date=None)
        session.commit()

        new_due = datetime.now(timezone.utc) + timedelta(days=14)
        task.due_date = new_due
        session.commit()
        session.refresh(task)
        assert task.due_date is not None


# =============================================================================
# 4. Task Deletion
# =============================================================================

class TestTaskDeletion:
    """Test task deletion and soft delete."""

    def test_hard_delete_removes_from_db(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, name="ToDelete")
        task_id = task.id
        session.commit()

        session.delete(task)
        session.commit()

        assert session.query(TaskModel).filter_by(id=task_id).first() is None

    def test_soft_delete_via_cancelled_status(self, session):
        """Soft delete by setting status to CANCELLED."""
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, name="SoftDelete")
        session.commit()

        task.status = TaskStatus.CANCELLED
        session.commit()
        session.refresh(task)

        assert task.status == TaskStatus.CANCELLED
        # Task still exists in DB
        assert session.query(TaskModel).filter_by(id=task.id).first() is not None

    def test_delete_does_not_affect_other_tasks(self, session):
        user = _make_user(session)
        t1 = _make_task(session, created_by=user.id, name="Keep")
        t2 = _make_task(session, created_by=user.id, name="Remove")
        session.commit()

        session.delete(t2)
        session.commit()

        assert session.query(TaskModel).filter_by(id=t1.id).first() is not None

    def test_filter_excludes_cancelled(self, session):
        """Active task queries can exclude cancelled tasks."""
        user = _make_user(session)
        _make_task(session, created_by=user.id, status=TaskStatus.PENDING)
        _make_task(session, created_by=user.id, status=TaskStatus.CANCELLED)
        session.commit()

        active = (
            session.query(TaskModel)
            .filter(TaskModel.status != TaskStatus.CANCELLED)
            .all()
        )
        assert all(t.status != TaskStatus.CANCELLED for t in active)


# =============================================================================
# 5. Task Assignment
# =============================================================================

class TestTaskAssignment:
    """Test task assignment to users."""

    def test_assign_task_to_user(self, session):
        owner = _make_user(session)
        assignee = _make_user(session)
        task = _make_task(session, created_by=owner.id, assignee_id=assignee.id)
        session.commit()

        session.refresh(task)
        assert task.assignee_id == assignee.id

    def test_reassign_task(self, session):
        owner = _make_user(session)
        user_a = _make_user(session)
        user_b = _make_user(session)
        task = _make_task(session, created_by=owner.id, assignee_id=user_a.id)
        session.commit()

        task.assignee_id = user_b.id
        session.commit()
        session.refresh(task)
        assert task.assignee_id == user_b.id

    def test_unassign_task(self, session):
        owner = _make_user(session)
        assignee = _make_user(session)
        task = _make_task(session, created_by=owner.id, assignee_id=assignee.id)
        session.commit()

        task.assignee_id = None
        session.commit()
        session.refresh(task)
        assert task.assignee_id is None

    def test_assignee_relationship(self, session):
        owner = _make_user(session, username="owner_rel")
        assignee = _make_user(session, username="assignee_rel")
        task = _make_task(session, created_by=owner.id, assignee_id=assignee.id)
        session.commit()

        session.refresh(task)
        assert task.assignee is not None
        assert task.assignee.username == "assignee_rel"

    def test_unassigned_task_has_no_assignee(self, session):
        owner = _make_user(session)
        task = _make_task(session, created_by=owner.id, assignee_id=None)
        session.commit()

        session.refresh(task)
        assert task.assignee is None


# =============================================================================
# 6. Task Status Transitions
# =============================================================================

class TestTaskStatusTransitions:
    """Test task status transitions."""

    def test_pending_to_in_progress(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, status=TaskStatus.PENDING)
        session.commit()

        task.status = TaskStatus.IN_PROGRESS
        session.commit()
        session.refresh(task)
        assert task.status == TaskStatus.IN_PROGRESS

    def test_in_progress_to_completed(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, status=TaskStatus.IN_PROGRESS)
        session.commit()

        task.status = TaskStatus.COMPLETED
        session.commit()
        session.refresh(task)
        assert task.status == TaskStatus.COMPLETED

    def test_completed_to_reviewed(self, session):
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, status=TaskStatus.COMPLETED)
        session.commit()

        task.status = TaskStatus.REVIEWED
        session.commit()
        session.refresh(task)
        assert task.status == TaskStatus.REVIEWED

    def test_any_status_to_cancelled(self, session):
        user = _make_user(session)
        for initial in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]:
            task = _make_task(session, created_by=user.id, status=initial)
            session.commit()

            task.status = TaskStatus.CANCELLED
            session.commit()
            session.refresh(task)
            assert task.status == TaskStatus.CANCELLED

    def test_full_lifecycle(self, session):
        """Test the complete task lifecycle: PENDING → IN_PROGRESS → COMPLETED → REVIEWED."""
        user = _make_user(session)
        task = _make_task(session, created_by=user.id, status=TaskStatus.PENDING)
        session.commit()

        transitions = [
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
            TaskStatus.REVIEWED,
        ]
        for next_status in transitions:
            task.status = next_status
            session.commit()
            session.refresh(task)
            assert task.status == next_status

    def test_all_status_values_are_valid(self, session):
        """Every TaskStatus enum value can be persisted."""
        user = _make_user(session)
        for status_val in TaskStatus:
            task = _make_task(session, created_by=user.id, status=status_val)
            session.commit()
            session.refresh(task)
            assert task.status == status_val
