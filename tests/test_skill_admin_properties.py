"""
Property-based tests for SkillAdminRouter.

Uses Hypothesis to verify tenant isolation across arbitrary tenant/skill distributions.

**Feature: openclaw-skill-integration**
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.skill_admin import router
from src.api.auth import get_current_user
from src.database.connection import get_db
from src.models.ai_integration import AIGateway, AISkill, AIAuditLog
from src.security.models import UserModel


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_tenant_id = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=3,
    max_size=20,
)

_skill_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=1,
    max_size=30,
)

_gateway_status = st.sampled_from(["active", "inactive"])

# A tenant config: (tenant_id, gateway_status, list of unique skill names)
_tenant_config = st.tuples(
    _tenant_id,
    _gateway_status,
    st.lists(_skill_name, min_size=0, max_size=8, unique=True),
)

# Generate 2-5 tenants with unique tenant IDs
_multi_tenant_scenario = (
    st.lists(_tenant_config, min_size=2, max_size=5)
    .map(lambda configs: list({c[0]: c for c in configs}.values()))
    .filter(lambda configs: len(configs) >= 2)
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine_and_session():
    """Create a fresh in-memory SQLite engine + session."""
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

    Session = sessionmaker(bind=engine)
    return engine, Session


def _seed_scenario(session, configs: list[tuple]) -> dict:
    """Seed gateways and skills for all tenants.

    Returns {tenant_id: set(skill_ids)} — IDs visible via list_skills.
    """
    tenant_skill_ids: dict[str, set[str]] = {}
    for idx, (tenant_id, gw_status, skill_names) in enumerate(configs):
        gw_id = f"gw-{idx}"
        gw = AIGateway(
            id=gw_id,
            name=f"GW-{tenant_id}",
            gateway_type="openclaw",
            tenant_id=tenant_id,
            status=gw_status,
            configuration={"agent_url": "http://agent:8081"},
            api_key_hash="k",
            api_secret_hash="s",
        )
        session.add(gw)
        session.flush()

        ids_for_tenant: set[str] = set()
        for sk_idx, sk_name in enumerate(skill_names):
            sk_id = f"sk-{idx}-{sk_idx}"
            skill = AISkill(
                id=sk_id,
                gateway_id=gw_id,
                name=sk_name,
                version="1.0.0",
                code_path="/skills/test",
                status="deployed",
                configuration={"description": "test", "category": "test"},
                deployed_at=datetime.now(timezone.utc),
            )
            session.add(skill)
            ids_for_tenant.add(sk_id)

        # Only active gateways' skills should be visible
        tenant_skill_ids[tenant_id] = ids_for_tenant if gw_status == "active" else set()

    session.commit()
    return tenant_skill_ids


def _make_mock_user(tenant_id: str) -> MagicMock:
    user = MagicMock(spec=UserModel)
    user.tenant_id = tenant_id
    user.id = "user-prop"
    user.username = "admin"
    return user


def _make_app(SessionFactory, tenant_id: str) -> FastAPI:
    """Build a FastAPI app with DB and auth overrides for a given tenant."""
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        session = SessionFactory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _make_mock_user(tenant_id)
    return app


# ---------------------------------------------------------------------------
# Property 1: 租户隔离
# ---------------------------------------------------------------------------

class TestTenantIsolationProperty:
    """
    **Property 1: 租户隔离**

    *For any* tenant_id and any skill returned by list_skills(tenant_id),
    that skill's associated gateway must have gateway.tenant_id equal to
    the querying tenant_id. No skill belonging to a different tenant shall
    ever appear in the result.

    **Validates: Requirements 1.1, 2.1, 2.2**
    """

    @given(scenario=_multi_tenant_scenario)
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    def test_list_skills_returns_only_own_tenant_skills(
        self, scenario: list[tuple],
    ):
        """For every tenant, list_skills returns only that tenant's skills."""
        engine, SessionFactory = _make_engine_and_session()
        try:
            session = SessionFactory()
            expected_ids_by_tenant = _seed_scenario(session, scenario)
            session.close()

            for tenant_id, _gw_status, _skill_names in scenario:
                app = _make_app(SessionFactory, tenant_id)
                client = TestClient(app)

                resp = client.get("/api/v1/admin/skills/")
                assert resp.status_code == 200, (
                    f"Tenant '{tenant_id}' got status {resp.status_code}"
                )

                data = resp.json()
                returned_ids = {s["id"] for s in data["skills"]}
                expected_ids = expected_ids_by_tenant.get(tenant_id, set())

                # Returned skill IDs must exactly match expected
                assert returned_ids == expected_ids, (
                    f"Tenant '{tenant_id}': "
                    f"expected IDs {expected_ids}, got {returned_ids}"
                )

                # No skill from another tenant must appear
                other_tenant_ids: set[str] = set()
                for other_tid, other_ids in expected_ids_by_tenant.items():
                    if other_tid != tenant_id:
                        other_tenant_ids.update(other_ids)

                leaked = returned_ids & other_tenant_ids
                assert not leaked, (
                    f"Tenant '{tenant_id}' sees skills from other tenants: {leaked}"
                )
        finally:
            engine.dispose()


# ---------------------------------------------------------------------------
# Strategies (Property 5)
# ---------------------------------------------------------------------------

# Statuses that are NOT "deployed" — mix of known values and arbitrary strings
_non_deployed_status = st.one_of(
    st.sampled_from(["pending", "failed", "removed"]),
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s != "deployed"),
)


# ---------------------------------------------------------------------------
# Property 5: 非 deployed 技能执行拒绝
# ---------------------------------------------------------------------------

class TestNonDeployedSkillExecutionRejection:
    """
    **Property 5: 非 deployed 技能执行拒绝**

    *For any* AISkill where skill.status is not "deployed", calling
    execute_skill on that skill shall be rejected with HTTP 400, and no
    execution request shall be forwarded to the Agent.

    **Validates: Requirement 4.3**
    """

    @given(status=_non_deployed_status)
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    def test_execute_rejects_non_deployed_skill(self, status: str):
        """POST /execute on a skill with any non-deployed status returns 400."""
        engine, SessionFactory = _make_engine_and_session()
        try:
            session = SessionFactory()

            # Seed one active gateway + one skill with the generated status
            tenant_id = "tenant-prop5"
            gw = AIGateway(
                id="gw-prop5",
                name="GW-prop5",
                gateway_type="openclaw",
                tenant_id=tenant_id,
                status="active",
                configuration={"agent_url": "http://agent:8081"},
                api_key_hash="k",
                api_secret_hash="s",
            )
            session.add(gw)
            session.flush()

            skill = AISkill(
                id="sk-prop5",
                gateway_id="gw-prop5",
                name="test-skill",
                version="1.0.0",
                code_path="/skills/test",
                status=status,
                configuration={"description": "test", "category": "test"},
                deployed_at=datetime.now(timezone.utc),
            )
            session.add(skill)
            session.commit()
            session.close()

            app = _make_app(SessionFactory, tenant_id)
            client = TestClient(app)

            resp = client.post(
                "/api/v1/admin/skills/sk-prop5/execute",
                json={"parameters": {}},
            )

            assert resp.status_code == 400, (
                f"Expected 400 for status '{status}', got {resp.status_code}"
            )
        finally:
            engine.dispose()



# ---------------------------------------------------------------------------
# Strategies (Property 7)
# ---------------------------------------------------------------------------

# Any initial skill status (including arbitrary strings)
_any_initial_status = st.one_of(
    st.sampled_from(["pending", "deployed", "failed", "removed"]),
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
        min_size=1,
        max_size=20,
    ),
)

# Valid target statuses for toggle
_target_status = st.sampled_from(["deployed", "pending"])


# ---------------------------------------------------------------------------
# Property 7: 状态切换生效
# ---------------------------------------------------------------------------

class TestStatusToggleProperty:
    """
    **Property 7: 状态切换生效**

    *For any* AISkill and any valid target status ("deployed" or "pending"),
    after toggle_skill_status is called, the AISkill record in the database
    shall have its status equal to the target status. Furthermore, skills
    with status "pending" shall not appear in the AI 助手页面 skill list.

    **Validates: Requirements 5.1, 5.2**
    """

    @given(initial_status=_any_initial_status, target=_target_status)
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    def test_toggle_updates_status_and_filters_pending(
        self, initial_status: str, target: str,
    ):
        """PATCH /status sets the DB status and pending skills are excluded from
        the AI assistant page skill list (which filters status=='deployed')."""
        engine, SessionFactory = _make_engine_and_session()
        try:
            session = SessionFactory()

            tenant_id = "tenant-prop7"
            gw = AIGateway(
                id="gw-prop7",
                name="GW-prop7",
                gateway_type="openclaw",
                tenant_id=tenant_id,
                status="active",
                configuration={"agent_url": "http://agent:8081"},
                api_key_hash="k",
                api_secret_hash="s",
            )
            session.add(gw)
            session.flush()

            skill = AISkill(
                id="sk-prop7",
                gateway_id="gw-prop7",
                name="toggle-skill",
                version="1.0.0",
                code_path="/skills/test",
                status=initial_status,
                configuration={"description": "test", "category": "test"},
                deployed_at=datetime.now(timezone.utc),
            )
            session.add(skill)
            session.commit()
            session.close()

            app = _make_app(SessionFactory, tenant_id)
            client = TestClient(app)

            # 1. Toggle the skill status
            resp = client.patch(
                "/api/v1/admin/skills/sk-prop7/status",
                json={"status": target},
            )
            assert resp.status_code == 200, (
                f"Expected 200 for toggle to '{target}', got {resp.status_code}"
            )

            body = resp.json()

            # 2. Response must reflect the target status
            assert body["status"] == target, (
                f"Response status '{body['status']}' != target '{target}'"
            )

            # 3. DB record must be updated
            verify_session = SessionFactory()
            db_skill = (
                verify_session.query(AISkill)
                .filter(AISkill.id == "sk-prop7")
                .one()
            )
            assert db_skill.status == target, (
                f"DB status '{db_skill.status}' != target '{target}'"
            )

            # 4. Simulate the AI assistant page query (status == "deployed").
            #    Pending skills must NOT appear; deployed skills MUST appear.
            assistant_visible = (
                verify_session.query(AISkill)
                .filter(
                    AISkill.gateway_id == "gw-prop7",
                    AISkill.status == "deployed",
                )
                .all()
            )
            visible_ids = {s.id for s in assistant_visible}
            verify_session.close()

            if target == "pending":
                assert "sk-prop7" not in visible_ids, (
                    "Pending skill must not appear in AI assistant skill list"
                )
            else:
                assert "sk-prop7" in visible_ids, (
                    "Deployed skill must appear in AI assistant skill list"
                )
        finally:
            engine.dispose()

