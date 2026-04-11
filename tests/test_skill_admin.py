"""
Unit tests for SkillAdminRouter.

Mock service layer, verify auth, param validation, and tenant isolation.

**Feature: openclaw-skill-integration**
**Validates: Requirements 1.1, 2.1, 2.2, 4.3, 5.1**
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.skill_admin import router
from src.api.auth import get_current_user
from src.database.connection import get_db
from src.models.ai_integration import AIAuditLog, AIGateway, AISkill, Base
from src.security.models import UserModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"


@pytest.fixture(autouse=True)
def disable_openclaw_auto_bootstrap(monkeypatch):
    """Skill admin tests assume explicit gateway/skill seeds (no auto-bootstrap)."""
    monkeypatch.setenv("OPENCLAW_AUTO_BOOTSTRAP_SKILLS", "0")


@pytest.fixture(scope="function")
def test_engine():
    """In-memory SQLite engine with JSONB→JSON patching."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for col in table.columns:
            if hasattr(col.type, "__class__") and col.type.__class__.__name__ == "JSONB":
                col.type = JSON()

    AIGateway.__table__.create(engine, checkfirst=True)
    AISkill.__table__.create(engine, checkfirst=True)
    AIAuditLog.__table__.create(engine, checkfirst=True)

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def _make_mock_user(tenant_id: str = TENANT_A) -> MagicMock:
    """Create a mock UserModel with the given tenant_id."""
    user = MagicMock(spec=UserModel)
    user.tenant_id = tenant_id
    user.id = "user-1"
    user.username = "admin"
    return user


@pytest.fixture
def app_for_tenant_a(test_engine):
    """FastAPI app with auth overridden to tenant-a."""
    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db():
        Session = sessionmaker(bind=test_engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = lambda: _make_mock_user(TENANT_A)
    return test_app


@pytest.fixture
def app_for_tenant_b(test_engine):
    """FastAPI app with auth overridden to tenant-b."""
    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db():
        Session = sessionmaker(bind=test_engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = lambda: _make_mock_user(TENANT_B)
    return test_app


@pytest.fixture
def client_a(app_for_tenant_a):
    return TestClient(app_for_tenant_a)


@pytest.fixture
def client_b(app_for_tenant_b):
    return TestClient(app_for_tenant_b)


# --- Seed helpers ---

def _seed_gateway(db_session, tenant_id=TENANT_A, gw_id="gw-1", status="active") -> AIGateway:
    gw = AIGateway(
        id=gw_id,
        name=f"GW-{gw_id}",
        gateway_type="openclaw",
        tenant_id=tenant_id,
        status=status,
        configuration={"agent_url": "http://agent:8081"},
        api_key_hash="k",
        api_secret_hash="s",
    )
    db_session.add(gw)
    db_session.commit()
    return gw


def _seed_skill(
    db_session,
    gateway_id="gw-1",
    skill_id="sk-1",
    name="skill-1",
    status="deployed",
    deployed_at=None,
) -> AISkill:
    sk = AISkill(
        id=skill_id,
        gateway_id=gateway_id,
        name=name,
        version="1.0.0",
        code_path="/skills/test",
        status=status,
        configuration={"description": "A test skill", "category": "test"},
        deployed_at=deployed_at or datetime.now(timezone.utc),
    )
    db_session.add(sk)
    db_session.commit()
    return sk


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/admin/skills/ (Req 1.1, 2.1, 2.2)
# ---------------------------------------------------------------------------


class TestListSkills:
    """Validates: Requirements 1.1, 2.1, 2.2"""

    def test_returns_skills_for_tenant(self, client_a, db_session):
        """Skills belonging to tenant-a's active gateway are returned."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A)
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-1", name="alpha")
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-2", name="beta")

        resp = client_a.get("/api/v1/admin/skills/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        names = {s["name"] for s in data["skills"]}
        assert names == {"alpha", "beta"}

    def test_empty_when_no_active_gateway(self, client_a, db_session):
        """No active gateway → empty list with total=0 (Req 1.4)."""
        _seed_gateway(db_session, tenant_id=TENANT_A, status="inactive")

        resp = client_a.get("/api/v1/admin/skills/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["skills"] == []

    def test_tenant_isolation(self, client_b, db_session):
        """Tenant-b cannot see tenant-a's skills (Req 2.1, 2.2)."""
        gw_a = _seed_gateway(db_session, tenant_id=TENANT_A, gw_id="gw-a")
        _seed_skill(db_session, gateway_id=gw_a.id, skill_id="sk-a")

        # client_b is authenticated as tenant-b
        resp = client_b.get("/api/v1/admin/skills/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_excludes_removed_skills(self, client_a, db_session):
        """Skills with status 'removed' are excluded from the list."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A)
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-active", status="deployed")
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-gone", status="removed")

        resp = client_a.get("/api/v1/admin/skills/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["skills"][0]["id"] == "sk-active"


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/admin/skills/sync (Req 1.1)
# ---------------------------------------------------------------------------


class TestSyncSkills:
    """Validates: Requirement 1.1 (sync endpoint exists and calls service)."""

    def test_sync_calls_service(self, client_a, db_session):
        """Sync delegates to SkillSyncService.sync_from_agent."""
        _seed_gateway(db_session, tenant_id=TENANT_A)

        fake_result = {
            "added": 2,
            "updated": 0,
            "removed": 0,
            "skills": [],
        }
        with patch(
            "src.api.skill_admin.SkillSyncService"
        ) as MockSvc:
            instance = MockSvc.return_value
            instance.sync_from_agent = AsyncMock(return_value=fake_result)

            resp = client_a.post("/api/v1/admin/skills/sync")

        assert resp.status_code == 200
        data = resp.json()
        assert data["added"] == 2

    def test_sync_404_when_no_gateway(self, client_a, db_session):
        """No active gateway → 404."""
        resp = client_a.post("/api/v1/admin/skills/sync")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/admin/skills/{skill_id}/execute (Req 4.3)
# ---------------------------------------------------------------------------


class TestExecuteSkill:
    """Validates: Requirement 4.3 — non-deployed skills rejected with 400."""

    def test_rejects_non_deployed_skill(self, client_a, db_session):
        """Skill with status 'pending' → 400."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A)
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-pending", status="pending")

        resp = client_a.post(
            "/api/v1/admin/skills/sk-pending/execute",
            json={"parameters": {}},
        )
        assert resp.status_code == 400
        assert "未部署" in resp.json()["detail"]

    def test_rejects_failed_skill(self, client_a, db_session):
        """Skill with status 'failed' → 400."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A)
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-fail", status="failed")

        resp = client_a.post(
            "/api/v1/admin/skills/sk-fail/execute",
            json={"parameters": {}},
        )
        assert resp.status_code == 400

    def test_execute_deployed_skill_calls_service(self, client_a, db_session):
        """Deployed skill → delegates to SkillSyncService.execute_skill."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A)
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-ok", status="deployed")

        fake_result = {
            "success": True,
            "result": {"answer": "42"},
            "execution_time_ms": 120,
        }
        with patch("src.api.skill_admin.SkillSyncService") as MockSvc:
            instance = MockSvc.return_value
            instance.execute_skill = AsyncMock(return_value=fake_result)

            resp = client_a.post(
                "/api/v1/admin/skills/sk-ok/execute",
                json={"parameters": {"q": "test"}},
            )

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_execute_skill_not_found(self, client_a, db_session):
        """Non-existent skill → 404."""
        resp = client_a.post(
            "/api/v1/admin/skills/nonexistent/execute",
            json={"parameters": {}},
        )
        assert resp.status_code == 404

    def test_execute_skill_wrong_tenant(self, client_b, db_session):
        """Tenant-b cannot execute tenant-a's skill."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A, gw_id="gw-a")
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-a", status="deployed")

        resp = client_b.post(
            "/api/v1/admin/skills/sk-a/execute",
            json={"parameters": {}},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: PATCH /api/v1/admin/skills/{skill_id}/status (Req 5.1)
# ---------------------------------------------------------------------------


class TestToggleSkillStatus:
    """Validates: Requirement 5.1 — status toggle between deployed/pending."""

    def test_toggle_to_pending(self, client_a, db_session):
        """Toggle deployed → pending."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A)
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-1", status="deployed")

        resp = client_a.patch(
            "/api/v1/admin/skills/sk-1/status",
            json={"status": "pending"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    def test_toggle_to_deployed(self, client_a, db_session):
        """Toggle pending → deployed."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A)
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-1", status="pending")

        resp = client_a.patch(
            "/api/v1/admin/skills/sk-1/status",
            json={"status": "deployed"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deployed"

    def test_toggle_invalid_status(self, client_a, db_session):
        """Invalid status value → 422 validation error."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A)
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-1")

        resp = client_a.patch(
            "/api/v1/admin/skills/sk-1/status",
            json={"status": "invalid"},
        )
        assert resp.status_code == 422

    def test_toggle_wrong_tenant(self, client_b, db_session):
        """Tenant-b cannot toggle tenant-a's skill."""
        gw = _seed_gateway(db_session, tenant_id=TENANT_A, gw_id="gw-a")
        _seed_skill(db_session, gateway_id=gw.id, skill_id="sk-a")

        resp = client_b.patch(
            "/api/v1/admin/skills/sk-a/status",
            json={"status": "pending"},
        )
        assert resp.status_code == 404

    def test_toggle_not_found(self, client_a, db_session):
        """Non-existent skill → 404."""
        resp = client_a.patch(
            "/api/v1/admin/skills/nonexistent/status",
            json={"status": "deployed"},
        )
        assert resp.status_code == 404
