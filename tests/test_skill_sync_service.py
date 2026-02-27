"""
Unit tests for SkillSyncService.

Tests sync upsert logic, error handling, and audit log writing.

**Feature: openclaw-skill-integration**
**Validates: Requirements 3.2, 3.3, 3.4, 3.6, 3.7, 4.6**
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
from fastapi import HTTPException
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.ai_integration.skill_sync_service import SkillSyncService
from src.models.ai_integration import AIAuditLog, AIGateway, AISkill, Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
    """Scoped DB session, rolled back after each test."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def gateway(db_session) -> AIGateway:
    """Active gateway with a valid agent_url."""
    gw = AIGateway(
        id="gw-1",
        name="Test Gateway",
        gateway_type="openclaw",
        tenant_id="tenant-1",
        status="active",
        configuration={"agent_url": "http://agent:8081"},
        api_key_hash="k",
        api_secret_hash="s",
    )
    db_session.add(gw)
    db_session.commit()
    return gw


@pytest.fixture
def gateway_no_url(db_session) -> AIGateway:
    """Gateway without agent_url in configuration."""
    gw = AIGateway(
        id="gw-no-url",
        name="No URL Gateway",
        gateway_type="openclaw",
        tenant_id="tenant-1",
        status="active",
        configuration={},
        api_key_hash="k",
        api_secret_hash="s",
    )
    db_session.add(gw)
    db_session.commit()
    return gw


@pytest.fixture
def service(db_session) -> SkillSyncService:
    return SkillSyncService(db_session)


def _make_agent_skill(name: str, version: str = "1.0.0") -> dict:
    """Helper to build an Agent skill payload."""
    return {"name": name, "version": version, "code_path": f"/skills/{name}"}


# ---------------------------------------------------------------------------
# Sync — upsert logic (Req 3.2, 3.3, 3.4)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_inserts_new_skills(service, gateway, db_session):
    """New skills from Agent are inserted with status 'deployed'. (Req 3.2)"""
    agent_skills = [_make_agent_skill("skill-a"), _make_agent_skill("skill-b")]

    with patch.object(service, "_fetch_agent_skills", new_callable=AsyncMock, return_value=agent_skills):
        result = await service.sync_from_agent(gateway)

    assert result["added"] == 2
    assert result["updated"] == 0
    assert result["removed"] == 0

    rows = db_session.query(AISkill).filter_by(gateway_id=gateway.id).all()
    assert len(rows) == 2
    assert all(r.status == "deployed" for r in rows)


@pytest.mark.asyncio
async def test_sync_updates_existing_skills(service, gateway, db_session):
    """Existing skills are updated with new version. (Req 3.3)"""
    # Pre-populate a skill
    existing = AISkill(
        id="sk-1", gateway_id=gateway.id, name="skill-a",
        version="0.9.0", code_path="/old", status="deployed",
    )
    db_session.add(existing)
    db_session.commit()

    agent_skills = [_make_agent_skill("skill-a", "1.0.0")]

    with patch.object(service, "_fetch_agent_skills", new_callable=AsyncMock, return_value=agent_skills):
        result = await service.sync_from_agent(gateway)

    assert result["updated"] == 1
    assert result["added"] == 0

    refreshed = db_session.query(AISkill).get("sk-1")
    assert refreshed.version == "1.0.0"
    assert refreshed.status == "deployed"


@pytest.mark.asyncio
async def test_sync_marks_removed_skills(service, gateway, db_session):
    """DB skills not in Agent response are marked 'removed'. (Req 3.4)"""
    old_skill = AISkill(
        id="sk-old", gateway_id=gateway.id, name="obsolete",
        version="1.0.0", code_path="/x", status="deployed",
    )
    db_session.add(old_skill)
    db_session.commit()

    # Agent returns empty list → old skill should be removed
    with patch.object(service, "_fetch_agent_skills", new_callable=AsyncMock, return_value=[]):
        result = await service.sync_from_agent(gateway)

    assert result["removed"] == 1
    refreshed = db_session.query(AISkill).get("sk-old")
    assert refreshed.status == "removed"


@pytest.mark.asyncio
async def test_sync_mixed_upsert(service, gateway, db_session):
    """Combined insert + update + remove in a single sync. (Req 3.2, 3.3, 3.4)"""
    existing = AISkill(
        id="sk-exist", gateway_id=gateway.id, name="keep-me",
        version="0.1.0", code_path="/a", status="deployed",
    )
    stale = AISkill(
        id="sk-stale", gateway_id=gateway.id, name="drop-me",
        version="1.0.0", code_path="/b", status="deployed",
    )
    db_session.add_all([existing, stale])
    db_session.commit()

    agent_skills = [
        _make_agent_skill("keep-me", "0.2.0"),
        _make_agent_skill("brand-new"),
    ]

    with patch.object(service, "_fetch_agent_skills", new_callable=AsyncMock, return_value=agent_skills):
        result = await service.sync_from_agent(gateway)

    assert result["added"] == 1
    assert result["updated"] == 1
    assert result["removed"] == 1


# ---------------------------------------------------------------------------
# Error handling (Req 3.6, 3.7)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_agent_unreachable_returns_503(service, gateway):
    """Agent unreachable → HTTPException 503. (Req 3.6)"""
    with patch.object(
        service, "_fetch_agent_skills",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=503, detail="Agent 服务不可达"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await service.sync_from_agent(gateway)
        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_sync_missing_agent_url_returns_400(service, gateway_no_url):
    """Missing agent_url → HTTPException 400. (Req 3.7)"""
    with pytest.raises(HTTPException) as exc_info:
        await service.sync_from_agent(gateway_no_url)
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Execute — error handling (Req 3.6 / 504 timeout)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_non_deployed_skill_returns_400(service, gateway, db_session):
    """Executing a non-deployed skill raises 400."""
    skill = AISkill(
        id="sk-pending", gateway_id=gateway.id, name="pending-skill",
        version="1.0.0", code_path="/x", status="pending",
    )
    db_session.add(skill)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await service.execute_skill(skill, gateway, {})
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_execute_agent_unreachable_returns_503(service, gateway, db_session):
    """Agent unreachable during execute → 503. (Req 3.6)"""
    skill = AISkill(
        id="sk-exec", gateway_id=gateway.id, name="exec-skill",
        version="1.0.0", code_path="/x", status="deployed",
    )
    db_session.add(skill)
    db_session.commit()

    with patch.object(
        service, "_call_agent_execute",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=503, detail="Agent 服务不可达"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await service.execute_skill(skill, gateway, {"q": "test"})
        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_execute_timeout_returns_504(service, gateway, db_session):
    """Agent execution timeout → 504."""
    skill = AISkill(
        id="sk-timeout", gateway_id=gateway.id, name="slow-skill",
        version="1.0.0", code_path="/x", status="deployed",
    )
    db_session.add(skill)
    db_session.commit()

    with patch.object(
        service, "_call_agent_execute",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=504, detail="技能执行超时（30s）"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await service.execute_skill(skill, gateway, {})
        assert exc_info.value.status_code == 504


# ---------------------------------------------------------------------------
# Audit log writing (Req 4.6)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_success_writes_audit_log(service, gateway, db_session):
    """Successful execution writes an audit log with event_type 'skill_execution'. (Req 4.6)"""
    skill = AISkill(
        id="sk-audit", gateway_id=gateway.id, name="audit-skill",
        version="1.0.0", code_path="/x", status="deployed",
    )
    db_session.add(skill)
    db_session.commit()

    with patch.object(
        service, "_call_agent_execute",
        new_callable=AsyncMock,
        return_value={"answer": "ok"},
    ):
        result = await service.execute_skill(skill, gateway, {"q": "hi"})

    assert result["success"] is True

    logs = db_session.query(AIAuditLog).filter_by(gateway_id=gateway.id).all()
    assert len(logs) == 1
    log = logs[0]
    assert log.event_type == "skill_execution"
    assert log.tenant_id == gateway.tenant_id
    assert log.success is True
    assert log.error_message is None


@pytest.mark.asyncio
async def test_execute_failure_writes_audit_log(service, gateway, db_session):
    """Failed execution still writes an audit log. (Req 4.6)"""
    skill = AISkill(
        id="sk-fail-audit", gateway_id=gateway.id, name="fail-skill",
        version="1.0.0", code_path="/x", status="deployed",
    )
    db_session.add(skill)
    db_session.commit()

    with patch.object(
        service, "_call_agent_execute",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=503, detail="Agent down"),
    ):
        with pytest.raises(HTTPException):
            await service.execute_skill(skill, gateway, {})

    logs = db_session.query(AIAuditLog).filter_by(gateway_id=gateway.id).all()
    assert len(logs) == 1
    log = logs[0]
    assert log.event_type == "skill_execution"
    assert log.success is False
