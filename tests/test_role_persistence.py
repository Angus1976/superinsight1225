"""
Role-based data persistence tests.

Verifies data persistence works correctly for different user roles
(admin, business_expert, viewer) and that the created_by field
correctly tracks which user created each task.

Requirements: 15.6 - Test data persistence for admin, annotator, reviewer
roles and permission-based access.
"""

import pytest
from uuid import uuid4, UUID as PyUUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, INET

from src.database.connection import Base, get_db_session
from src.security.models import UserModel, UserRole
from src.security.controller import SecurityController
from src.database.models import (
    TaskModel, TaskStatus, TaskPriority, AnnotationType,
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


def _seed_user(
    session: Session,
    *,
    username: str,
    email: str,
    role: str,
) -> UserModel:
    """Insert a user with the given role and return the ORM instance."""
    sc = SecurityController(secret_key=JWT_SECRET)
    user = UserModel(
        id=uuid4(),
        username=username,
        email=email,
        password_hash=sc.hash_password("TestPass123!"),
        full_name=f"Test {username.title()}",
        role=role,
        tenant_id=TENANT_ID,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_simple_user(user: UserModel):
    """Build a SimpleUser-like object for dependency override."""
    from src.api.auth_simple import SimpleUser
    fake = SimpleUser(
        user_id=str(user.id),
        email=user.email,
        username=user.username,
        name=user.full_name,
        is_active=True,
        is_superuser=(user.role == UserRole.ADMIN.value),
    )
    fake.tenant_id = TENANT_ID
    return fake


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


# ── Fixtures ────────────────────────────────────────────────────────────────

ROLES = [
    ("admin", "admin@example.com", UserRole.ADMIN.value),
    ("annotator", "annotator@example.com", UserRole.BUSINESS_EXPERT.value),
    ("reviewer", "reviewer@example.com", UserRole.VIEWER.value),
]


@pytest.fixture()
def shared_env():
    """
    Provide a shared DB with three users (admin, annotator, reviewer).

    Yields (session_factory, users_dict) where users_dict maps
    role-label → (user_id: UUID, role: str, TestClient).
    """
    engine = _create_engine()
    sf = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    users = {}
    with sf() as session:
        for username, email, role in ROLES:
            user = _seed_user(session, username=username, email=email, role=role)
            # Eagerly capture scalar values before session closes
            user_id = user.id
            user_role = user.role
            fake = _make_simple_user(user)
            app = _build_app(sf, fake)
            client = TestClient(app)
            users[username] = (user_id, user_role, client)

    yield sf, users

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ═════════════════════════════════════════════════════════════════════════════
# 1. Each role can create tasks via API
# ═════════════════════════════════════════════════════════════════════════════

class TestRoleTaskCreation:
    """Verify each role can create tasks and data persists correctly."""

    @pytest.mark.parametrize("role_label", ["admin", "annotator", "reviewer"])
    def test_role_can_create_task(self, shared_env, role_label):
        """Each role can POST /api/tasks and the task persists in DB."""
        sf, users = shared_env
        _, _, client = users[role_label]

        resp = client.post(
            "/api/tasks",
            json={"name": f"Task by {role_label}", "total_items": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == f"Task by {role_label}"

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(data["id"])).first()
            assert task is not None
            assert task.name == f"Task by {role_label}"

    @pytest.mark.parametrize("role_label", ["admin", "annotator", "reviewer"])
    def test_role_can_read_own_task(self, shared_env, role_label):
        """Each role can GET a task it created."""
        _, users = shared_env
        _, _, client = users[role_label]

        create_resp = client.post(
            "/api/tasks",
            json={"name": f"Read test {role_label}", "total_items": 5},
        )
        task_id = create_resp.json()["id"]

        get_resp = client.get(f"/api/tasks/{task_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == f"Read test {role_label}"


# ═════════════════════════════════════════════════════════════════════════════
# 2. created_by tracking
# ═════════════════════════════════════════════════════════════════════════════

class TestCreatedByTracking:
    """Verify created_by correctly records which user created each task."""

    def test_created_by_matches_admin(self, shared_env):
        """Admin-created task has admin's user ID in created_by."""
        sf, users = shared_env
        admin_id, _, client = users["admin"]

        resp = client.post("/api/tasks", json={"name": "Admin task", "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.created_by == admin_id

    def test_created_by_matches_annotator(self, shared_env):
        """Annotator-created task has annotator's user ID in created_by."""
        sf, users = shared_env
        ann_id, _, client = users["annotator"]

        resp = client.post("/api/tasks", json={"name": "Annotator task", "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.created_by == ann_id

    def test_created_by_matches_reviewer(self, shared_env):
        """Reviewer-created task has reviewer's user ID in created_by."""
        sf, users = shared_env
        rev_id, _, client = users["reviewer"]

        resp = client.post("/api/tasks", json={"name": "Reviewer task", "total_items": 1})
        task_id = resp.json()["id"]

        with sf() as s:
            task = s.query(TaskModel).filter_by(id=PyUUID(task_id)).first()
            assert task.created_by == rev_id

    def test_multiple_users_distinct_created_by(self, shared_env):
        """Tasks from different roles have distinct created_by values."""
        sf, users = shared_env
        task_ids = {}

        for role_label in ["admin", "annotator", "reviewer"]:
            _, _, client = users[role_label]
            resp = client.post(
                "/api/tasks",
                json={"name": f"Distinct {role_label}", "total_items": 1},
            )
            task_ids[role_label] = resp.json()["id"]

        with sf() as s:
            creators = set()
            for role_label, tid in task_ids.items():
                task = s.query(TaskModel).filter_by(id=PyUUID(tid)).first()
                creators.add(task.created_by)

            assert len(creators) == 3, "Each role should have a unique created_by"


# ═════════════════════════════════════════════════════════════════════════════
# 3. Tenant-based data access (permission-based)
# ═════════════════════════════════════════════════════════════════════════════

class TestTenantBasedAccess:
    """Verify tenant isolation acts as the permission boundary."""

    def test_same_tenant_users_see_each_others_tasks(self, shared_env):
        """Users in the same tenant can list tasks created by other roles."""
        _, users = shared_env
        _, _, admin_client = users["admin"]
        _, _, ann_client = users["annotator"]

        # Admin creates a task
        admin_client.post("/api/tasks", json={"name": "Shared task", "total_items": 1})

        # Annotator can see it via list
        resp = ann_client.get("/api/tasks")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()["items"]]
        assert "Shared task" in names

    def test_cross_tenant_isolation(self, shared_env):
        """A user in a different tenant cannot see tasks from TENANT_ID."""
        sf, users = shared_env
        _, _, admin_client = users["admin"]

        # Admin creates a task in TENANT_ID
        admin_client.post("/api/tasks", json={"name": "Tenant A task", "total_items": 1})

        # Create a user in a different tenant
        with sf() as session:
            other_user = _seed_user(
                session,
                username="other_tenant_user",
                email="other@example.com",
                role=UserRole.ADMIN.value,
            )

        other_fake = _make_simple_user(other_user)
        other_fake.tenant_id = "other_tenant"
        other_app = _build_app(sf, other_fake)
        other_client = TestClient(other_app)

        resp = other_client.get("/api/tasks")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()["items"]]
        assert "Tenant A task" not in names


# ═════════════════════════════════════════════════════════════════════════════
# 4. Role persistence in user model
# ═════════════════════════════════════════════════════════════════════════════

class TestRolePersistence:
    """Verify user role values persist correctly in the database."""

    def test_admin_role_persists(self, shared_env):
        """Admin user has role='admin' in DB."""
        sf, users = shared_env
        admin_id, _, _ = users["admin"]
        with sf() as s:
            db_user = s.query(UserModel).filter_by(id=admin_id).first()
            assert db_user.role == UserRole.ADMIN.value

    def test_annotator_role_persists(self, shared_env):
        """Annotator (business_expert) user has correct role in DB."""
        sf, users = shared_env
        ann_id, _, _ = users["annotator"]
        with sf() as s:
            db_user = s.query(UserModel).filter_by(id=ann_id).first()
            assert db_user.role == UserRole.BUSINESS_EXPERT.value

    def test_reviewer_role_persists(self, shared_env):
        """Reviewer (viewer) user has correct role in DB."""
        sf, users = shared_env
        rev_id, _, _ = users["reviewer"]
        with sf() as s:
            db_user = s.query(UserModel).filter_by(id=rev_id).first()
            assert db_user.role == UserRole.VIEWER.value

    def test_all_roles_stored_and_retrievable(self, shared_env):
        """All seeded roles are queryable from the users table."""
        sf, _ = shared_env
        with sf() as s:
            roles = {u.role for u in s.query(UserModel).all()}
            assert UserRole.ADMIN.value in roles
            assert UserRole.BUSINESS_EXPERT.value in roles
            assert UserRole.VIEWER.value in roles
