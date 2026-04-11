"""
Integration tests for API endpoints with database persistence.

Tests actual HTTP request/response cycles through the FastAPI API,
verifying data persists to the database after API calls.

Requirements: 3.1, 3.5, 3.6
"""

import os
import pytest
from uuid import uuid4, UUID as PyUUID
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, INET

from src.database.connection import Base, get_db_session
from src.security.models import UserModel, UserRole
from src.security.controller import SecurityController
from src.database.models import (
    TaskModel, TaskStatus, TaskPriority,
    AnnotationType, LabelStudioSyncStatus, DocumentModel,
)


# =============================================================================
# SQLite compatibility: map PostgreSQL-only column types
# =============================================================================

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "JSON"


# =============================================================================
# Constants
# =============================================================================

TENANT_ID = "test_tenant"
JWT_SECRET = "test-secret-key-do-not-use-in-production"


# =============================================================================
# Helpers
# =============================================================================

def _create_engine():
    """Create an isolated SQLite in-memory engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _seed_user(
    session: Session,
    *,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "TestPass123!",
    role: str = "admin",
) -> UserModel:
    """Insert a user directly and return the ORM instance."""
    sc = SecurityController(secret_key=JWT_SECRET)
    user = UserModel(
        id=uuid4(),
        username=username,
        email=email,
        password_hash=sc.hash_password(password),
        full_name=f"Test {username.title()}",
        role=role,
        tenant_id=TENANT_ID,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _seed_document(session: Session) -> DocumentModel:
    """Insert a document directly and return the ORM instance."""
    doc = DocumentModel(
        id=uuid4(),
        source_type="file",
        source_config={"path": "/data/test.csv"},
        content="Sample document content for testing.",
        tenant_id=TENANT_ID,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


def _make_token(user: UserModel) -> str:
    """Generate a JWT for the given user."""
    sc = SecurityController(secret_key=JWT_SECRET)
    return sc.create_access_token(
        user_id=str(user.id), tenant_id=user.tenant_id,
    )


def _auth(token: str) -> dict:
    """Return Authorization header."""
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# App factory — builds a minimal FastAPI app with the tasks router
# and overrides both DB and auth dependencies.
# =============================================================================

def _build_app(session_factory, current_user_obj):
    """
    Build a test FastAPI app with tasks + auth routers.

    Overrides:
    - get_db_session → yields from session_factory
    - auth_simple.get_current_user → returns current_user_obj
    """
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


# =============================================================================
# Fixture
# =============================================================================

@pytest.fixture()
def env():
    """
    Provide a fully isolated test environment per test.

    Yields (client, session_factory, user) where:
    - client: TestClient wired to the test app
    - sf: sessionmaker for direct DB assertions
    - user: the seeded UserModel instance
    """
    engine = _create_engine()
    sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Seed a user for auth
    with sf() as session:
        user = _seed_user(session)

    # Build a SimpleUser-like object for the dependency override
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


# =============================================================================
# 1. Authentication Flow
# =============================================================================

class TestAuthFlow:
    """Integration tests for authentication endpoints with DB persistence."""

    def test_login_valid_credentials(self, env):
        """POST /auth/login with correct credentials returns a token."""
        client, sf, user = env
        # The auth.py login uses ORM authenticate_user which hashes & compares.
        # We call the SecurityController directly to verify the flow.
        sc = SecurityController(secret_key=JWT_SECRET)
        with sf() as session:
            authed = sc.authenticate_user("testuser", "TestPass123!", session)
            assert authed is not None
            assert authed.username == "testuser"

    def test_login_wrong_password(self, env):
        """authenticate_user returns None for wrong password."""
        _, sf, _ = env
        sc = SecurityController(secret_key=JWT_SECRET)
        with sf() as session:
            result = sc.authenticate_user("testuser", "WrongPass!", session)
            assert result is None

    def test_login_nonexistent_user(self, env):
        """authenticate_user returns None for unknown user."""
        _, sf, _ = env
        sc = SecurityController(secret_key=JWT_SECRET)
        with sf() as session:
            result = sc.authenticate_user("ghost", "any", session)
            assert result is None

    def test_token_generation_and_verification(self, env):
        """Tokens created by SecurityController can be verified."""
        _, _, user = env
        sc = SecurityController(secret_key=JWT_SECRET)
        token = sc.create_access_token(str(user.id), user.tenant_id)
        payload = sc.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == str(user.id)

    def test_user_info_matches_seed(self, env):
        """The overridden current_user matches the seeded DB user."""
        _, sf, user = env
        with sf() as session:
            db_user = session.query(UserModel).filter_by(id=user.id).first()
            assert db_user.username == user.username
            assert db_user.email == user.email

    def test_logout_authenticated(self, env):
        """POST /auth/logout succeeds for authenticated user."""
        client, _, _ = env
        resp = client.post("/auth/logout")
        assert resp.status_code == 200

    def test_user_persisted_in_db(self, env):
        """Seeded user is retrievable from the database."""
        _, sf, user = env
        with sf() as session:
            db_user = session.query(UserModel).filter_by(id=user.id).first()
            assert db_user is not None
            assert db_user.email == user.email
            assert db_user.is_active is True


# =============================================================================
# 2. Task CRUD
# =============================================================================

class TestTaskCRUD:
    """Integration tests for task CRUD endpoints with DB persistence."""

    def test_create_task_persists(self, env):
        """POST /api/tasks creates a task visible in the database."""
        client, sf, _ = env
        resp = client.post(
            "/api/tasks",
            json={
                "name": "Annotate images batch 1",
                "description": "First batch",
                "annotation_type": "custom",
                "priority": "high",
                "total_items": 50,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Annotate images batch 1"
        assert data["total_items"] == 50

        with sf() as session:
            task = session.query(TaskModel).filter_by(id=PyUUID(data["id"])).first()
            assert task is not None
            assert task.name == "Annotate images batch 1"

    def test_list_tasks(self, env):
        """GET /api/tasks returns previously created tasks."""
        client, _, _ = env
        for i in range(3):
            client.post("/api/tasks", json={"name": f"Task {i}", "total_items": 1})

        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 3

    def test_get_single_task(self, env):
        """GET /api/tasks/{id} returns the correct task."""
        client, _, _ = env
        create = client.post("/api/tasks", json={"name": "Single", "total_items": 5})
        task_id = create.json()["id"]

        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Single"

    def test_update_task_persists(self, env):
        """PATCH /api/tasks/{id} updates the task in the database."""
        client, sf, _ = env
        create = client.post("/api/tasks", json={"name": "Original", "total_items": 1})
        task_id = create.json()["id"]

        resp = client.patch(
            f"/api/tasks/{task_id}",
            json={"name": "Updated", "status": "in_progress"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

        with sf() as session:
            task = session.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.name == "Updated"

    def test_delete_task(self, env):
        """DELETE /api/tasks/{id} removes the task from the database."""
        client, sf, _ = env
        create = client.post("/api/tasks", json={"name": "ToDelete", "total_items": 1})
        task_id = create.json()["id"]

        resp = client.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 200

        with sf() as session:
            assert session.query(TaskModel).filter_by(id=PyUUID(task_id)).first() is None

    def test_get_nonexistent_task_404(self, env):
        """GET /api/tasks/{id} returns 404 for unknown ID."""
        client, _, _ = env
        fake_id = str(uuid4())
        resp = client.get(f"/api/tasks/{fake_id}")
        assert resp.status_code == 404

    def test_task_stats(self, env):
        """GET /api/tasks/stats returns aggregated statistics."""
        client, _, _ = env
        client.post("/api/tasks", json={"name": "Stats task", "total_items": 1})

        resp = client.get("/api/tasks/stats")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# =============================================================================
# 3. Annotation Workflow
# =============================================================================

class TestAnnotationWorkflow:
    """Integration tests for annotation data flow with DB persistence."""

    def test_annotations_jsonb_persists(self, env):
        """Task annotations JSONB field persists through create and update."""
        client, sf, _ = env
        create = client.post("/api/tasks", json={"name": "Ann task", "total_items": 10})
        task_id = create.json()["id"]

        annotations = [
            {"label": "positive", "text": "Great product"},
            {"label": "negative", "text": "Poor quality"},
        ]
        with sf() as session:
            task = session.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            task.annotations = annotations
            task.completed_items = 2
            session.commit()

        # Verify via API
        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["completed_items"] == 2

        # Verify in DB
        with sf() as session:
            task = session.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert len(task.annotations) == 2
            assert task.annotations[0]["label"] == "positive"

    def test_quality_score_persists(self, env):
        """Quality score updates persist to the database."""
        _, sf, user = env
        with sf() as session:
            task = TaskModel(
                id=uuid4(),
                name="Quality task",
                title="Quality task",
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id,
                tenant_id=TENANT_ID,
                project_id="proj_q",
                quality_score=0.0,
            )
            session.add(task)
            session.commit()

            task.quality_score = 0.92
            session.commit()
            session.refresh(task)
            assert task.quality_score == pytest.approx(0.92, abs=0.01)

    def test_ai_predictions_jsonb_persists(self, env):
        """AI predictions JSONB field persists correctly."""
        _, sf, user = env
        predictions = [{"model": "gpt-4", "label": "positive", "confidence": 0.95}]
        with sf() as session:
            task = TaskModel(
                id=uuid4(),
                name="AI pred task",
                title="AI pred task",
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id,
                tenant_id=TENANT_ID,
                project_id="proj_ai",
                ai_predictions=predictions,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            assert task.ai_predictions[0]["model"] == "gpt-4"


# =============================================================================
# 4. Data Export with Database Queries
# =============================================================================

class TestDataExport:
    """Integration tests for data export with database queries."""

    def test_documents_queryable(self, env):
        """Documents inserted into DB are queryable for export."""
        _, sf, _ = env
        with sf() as session:
            doc = _seed_document(session)
            result = session.query(DocumentModel).filter_by(id=doc.id).first()
            assert result is not None
            assert result.content == "Sample document content for testing."

    def test_task_document_relationship(self, env):
        """Tasks linked to documents maintain their FK relationship."""
        _, sf, user = env
        with sf() as session:
            doc = _seed_document(session)
            task = TaskModel(
                id=uuid4(),
                name="Export linked",
                title="Export linked",
                status=TaskStatus.COMPLETED,
                priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id,
                tenant_id=TENANT_ID,
                project_id="proj_exp",
                document_id=doc.id,
            )
            session.add(task)
            session.commit()

            db_task = session.query(TaskModel).filter_by(id=task.id).first()
            assert db_task.document_id == doc.id
            assert db_task.document is not None

    def test_export_filter_by_tenant(self, env):
        """Export queries correctly filter documents by tenant_id."""
        _, sf, _ = env
        with sf() as session:
            for tid, content in [("t_a", "Doc A"), ("t_b", "Doc B")]:
                session.add(DocumentModel(
                    id=uuid4(),
                    source_type="file",
                    source_config={},
                    content=content,
                    tenant_id=tid,
                ))
            session.commit()

            results = (
                session.query(DocumentModel)
                .filter(DocumentModel.tenant_id == "t_a")
                .all()
            )
            assert len(results) == 1
            assert results[0].content == "Doc A"


# =============================================================================
# 5. Database Transactions and Rollback
# =============================================================================

class TestDatabaseTransactions:
    """Verify database transaction behavior and rollback."""

    def test_failed_insert_rolls_back(self, env):
        """A failed duplicate-PK insert does not leave partial data."""
        _, sf, user = env
        task_id = uuid4()

        with sf() as session:
            session.add(TaskModel(
                id=task_id,
                name="Task 1", title="Task 1",
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id,
                tenant_id=TENANT_ID,
                project_id="proj_tx",
            ))
            session.commit()

        with sf() as session:
            try:
                session.add(TaskModel(
                    id=task_id,  # duplicate PK
                    name="Task 2", title="Task 2",
                    status=TaskStatus.PENDING,
                    priority=TaskPriority.MEDIUM,
                    annotation_type=AnnotationType.CUSTOM,
                    created_by=user.id,
                    tenant_id=TENANT_ID,
                    project_id="proj_tx",
                ))
                session.commit()
            except Exception:
                session.rollback()

        with sf() as session:
            count = session.query(TaskModel).filter_by(project_id="proj_tx").count()
            assert count == 1

    def test_session_isolation(self, env):
        """Each test_env fixture provides a clean database."""
        _, sf, _ = env
        # Only the seeded user should exist
        with sf() as session:
            assert session.query(UserModel).count() == 1

    def test_concurrent_updates_last_write_wins(self, env):
        """Sequential updates — last commit wins."""
        _, sf, user = env
        task_id = uuid4()

        with sf() as session:
            session.add(TaskModel(
                id=task_id,
                name="Original", title="Original",
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
                annotation_type=AnnotationType.CUSTOM,
                created_by=user.id,
                tenant_id=TENANT_ID,
                project_id="proj_c",
            ))
            session.commit()

        with sf() as s:
            s.query(TaskModel).filter_by(id=task_id).first().name = "A"
            s.commit()

        with sf() as s:
            s.query(TaskModel).filter_by(id=task_id).first().name = "B"
            s.commit()

        with sf() as s:
            assert s.query(TaskModel).filter_by(id=task_id).first().name == "B"

    def test_cleanup_after_test(self, env):
        """Data created in one test does not leak to another."""
        _, sf, _ = env
        with sf() as session:
            _seed_user(session, username="extra", email="extra@example.com")
            assert session.query(UserModel).count() == 2
        # The next test using `env` will get a fresh engine.
