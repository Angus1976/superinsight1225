"""
Property-based tests for SkillSyncService.

Uses Hypothesis to verify sync invariants across arbitrary inputs.

**Feature: openclaw-skill-integration**
"""

import pytest
from datetime import datetime, timezone

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.ai_integration.skill_sync_service import SkillSyncService
from src.models.ai_integration import AIGateway, AISkill, AIAuditLog, Base


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_skill_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Pd"), whitelist_characters="_-"),
    min_size=1,
    max_size=30,
)

_version = st.from_regex(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", fullmatch=True)

_agent_skill = st.fixed_dictionaries(
    {"name": _skill_name, "version": _version, "code_path": st.just("/skills/x")},
)

# A list of agent skills with unique names
agent_skills_strategy = (
    st.lists(_agent_skill, max_size=15)
    .map(lambda skills: list({s["name"]: s for s in skills}.values()))
)

# Pre-existing DB skill names (unique) — these will be seeded before sync
pre_existing_names_strategy = st.lists(
    _skill_name, max_size=15, unique=True
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
    # Patch JSONB → JSON for SQLite
    for table in [AIGateway.__table__, AISkill.__table__, AIAuditLog.__table__]:
        for col in table.columns:
            if hasattr(col.type, "__class__") and col.type.__class__.__name__ == "JSONB":
                col.type = JSON()

    AIGateway.__table__.create(engine, checkfirst=True)
    AISkill.__table__.create(engine, checkfirst=True)
    AIAuditLog.__table__.create(engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    return engine, Session()


def _seed_gateway(session) -> AIGateway:
    """Insert a gateway and return it."""
    gw = AIGateway(
        id="gw-prop",
        name="Prop Gateway",
        gateway_type="openclaw",
        tenant_id="t-prop",
        status="active",
        configuration={"agent_url": "http://agent:8081"},
        api_key_hash="k",
        api_secret_hash="s",
    )
    session.add(gw)
    session.commit()
    return gw


def _seed_db_skills(session, gateway: AIGateway, names: list[str]) -> None:
    """Insert pre-existing skills into the DB."""
    for name in names:
        skill = AISkill(
            gateway_id=gateway.id,
            name=name,
            version="0.0.1",
            code_path="/old",
            status="deployed",
        )
        session.add(skill)
    session.commit()


# ---------------------------------------------------------------------------
# Property 3: 同步后数据库与 Agent 一致
# ---------------------------------------------------------------------------

class TestSyncConsistencyProperty:
    """
    **Property 3: 同步后数据库与 Agent 一致**

    *For any* set of skills returned by the Agent and any set of skills
    in the database before sync, after sync_from_agent completes:
      (a) every Agent skill exists in the database with status "deployed"
          and matching version,
      (b) every database skill not in the Agent response has status "removed".

    **Validates: Requirements 3.2, 3.3, 3.4**
    """

    @given(
        agent_skills=agent_skills_strategy,
        pre_existing=pre_existing_names_strategy,
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    def test_sync_postconditions(self, agent_skills: list[dict], pre_existing: list[str]):
        """After _upsert_skills, DB state matches the Agent response."""
        engine, session = _make_engine_and_session()
        try:
            gateway = _seed_gateway(session)
            _seed_db_skills(session, gateway, pre_existing)

            svc = SkillSyncService(session)
            svc._upsert_skills(gateway, agent_skills)

            # Reload all skills for this gateway
            db_skills = (
                session.query(AISkill)
                .filter(AISkill.gateway_id == gateway.id)
                .all()
            )
            db_by_name = {s.name: s for s in db_skills}
            agent_names = {s["name"] for s in agent_skills}

            # (a) Every Agent skill exists in DB with status "deployed" and matching version
            for agent_skill in agent_skills:
                name = agent_skill["name"]
                assert name in db_by_name, f"Agent skill '{name}' missing from DB"
                db_skill = db_by_name[name]
                assert db_skill.status == "deployed", (
                    f"Skill '{name}' should be deployed, got '{db_skill.status}'"
                )
                assert db_skill.version == agent_skill["version"], (
                    f"Skill '{name}' version mismatch: "
                    f"DB={db_skill.version}, Agent={agent_skill['version']}"
                )

            # (b) Every DB skill NOT in Agent response has status "removed"
            for db_skill in db_skills:
                if db_skill.name not in agent_names:
                    assert db_skill.status == "removed", (
                        f"Skill '{db_skill.name}' not in Agent but status is "
                        f"'{db_skill.status}', expected 'removed'"
                    )
        finally:
            session.close()
            engine.dispose()


# ---------------------------------------------------------------------------
# Property 4: 同步计数准确性
# ---------------------------------------------------------------------------

class TestSyncCountAccuracyProperty:
    """
    **Property 4: 同步计数准确性**

    *For any* sync operation, the returned SyncResult counts must satisfy:
      - added equals the number of newly inserted records,
      - updated equals the number of modified existing records,
      - removed equals the number of records marked as "removed".
      - All counts must be non-negative.

    **Validates: Requirement 3.5**
    """

    @given(
        agent_skills=agent_skills_strategy,
        pre_existing=pre_existing_names_strategy,
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    def test_sync_counts_match_actual_changes(
        self, agent_skills: list[dict], pre_existing: list[str]
    ):
        """Returned added/updated/removed counts match actual DB mutations."""
        engine, session = _make_engine_and_session()
        try:
            gateway = _seed_gateway(session)
            _seed_db_skills(session, gateway, pre_existing)

            pre_existing_set = set(pre_existing)
            agent_name_set = {s["name"] for s in agent_skills}

            # Expected counts based on set arithmetic
            expected_added = len(agent_name_set - pre_existing_set)
            expected_updated = len(agent_name_set & pre_existing_set)
            expected_removed = len(pre_existing_set - agent_name_set)

            svc = SkillSyncService(session)
            result = svc._upsert_skills(gateway, agent_skills)

            # All counts must be non-negative
            assert result["added"] >= 0, f"added is negative: {result['added']}"
            assert result["updated"] >= 0, f"updated is negative: {result['updated']}"
            assert result["removed"] >= 0, f"removed is negative: {result['removed']}"

            # Counts must match expected values
            assert result["added"] == expected_added, (
                f"added mismatch: got {result['added']}, expected {expected_added}"
            )
            assert result["updated"] == expected_updated, (
                f"updated mismatch: got {result['updated']}, expected {expected_updated}"
            )
            assert result["removed"] == expected_removed, (
                f"removed mismatch: got {result['removed']}, expected {expected_removed}"
            )

            # Cross-check: verify counts against actual DB state
            db_skills = (
                session.query(AISkill)
                .filter(AISkill.gateway_id == gateway.id)
                .all()
            )
            actual_removed = sum(1 for s in db_skills if s.status == "removed")
            actual_deployed = sum(1 for s in db_skills if s.status == "deployed")

            assert actual_removed == expected_removed, (
                f"DB removed count mismatch: got {actual_removed}, expected {expected_removed}"
            )
            assert actual_deployed == len(agent_name_set), (
                f"DB deployed count mismatch: got {actual_deployed}, expected {len(agent_name_set)}"
            )
        finally:
            session.close()
            engine.dispose()



# ---------------------------------------------------------------------------
# Property 6: 技能执行审计日志
# ---------------------------------------------------------------------------

class TestSkillExecutionAuditLogProperty:
    """
    **Property 6: 技能执行审计日志**

    *For any* skill execution attempt (success or failure), an AIAuditLog
    record with event_type "skill_execution" shall be created in the
    database, referencing the correct gateway_id and tenant_id.

    **Validates: Requirement 4.6**
    """

    @given(
        params=st.fixed_dictionaries(
            {"query": st.text(min_size=0, max_size=50)},
        ),
        execution_succeeds=st.booleans(),
    )
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    def test_audit_log_written_on_success_and_failure(
        self, params: dict, execution_succeeds: bool
    ):
        """An AIAuditLog with event_type='skill_execution' is always written."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        engine, session = _make_engine_and_session()
        try:
            gateway = _seed_gateway(session)

            # Insert a deployed skill to execute against
            skill = AISkill(
                id="skill-audit-test",
                gateway_id=gateway.id,
                name="audit-test-skill",
                version="1.0.0",
                code_path="/skills/audit",
                status="deployed",
            )
            session.add(skill)
            session.commit()

            svc = SkillSyncService(session)

            if execution_succeeds:
                mock_return = {"output": "ok"}
            else:
                mock_return = None  # will raise

            async def _run():
                with patch.object(svc, "_call_agent_execute", new_callable=AsyncMock) as mock_exec:
                    if execution_succeeds:
                        mock_exec.return_value = mock_return
                    else:
                        mock_exec.side_effect = Exception("agent error")

                    try:
                        await svc.execute_skill(skill, gateway, params)
                    except Exception:
                        pass  # failure path — we still expect audit log

            asyncio.get_event_loop().run_until_complete(_run())

            # Verify audit log exists
            logs = (
                session.query(AIAuditLog)
                .filter(AIAuditLog.event_type == "skill_execution")
                .all()
            )

            assert len(logs) == 1, (
                f"Expected exactly 1 audit log, got {len(logs)}"
            )

            log = logs[0]
            assert log.gateway_id == gateway.id, (
                f"gateway_id mismatch: {log.gateway_id} != {gateway.id}"
            )
            assert log.tenant_id == gateway.tenant_id, (
                f"tenant_id mismatch: {log.tenant_id} != {gateway.tenant_id}"
            )
            assert log.event_type == "skill_execution"

        finally:
            session.close()
            engine.dispose()
