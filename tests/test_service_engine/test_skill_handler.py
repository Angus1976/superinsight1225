"""
Unit tests for SkillHandler — validation, whitelist checking,
skill execution, and error handling.
"""

from typing import Optional
from unittest.mock import AsyncMock

import pytest

from src.service_engine.handlers.skill import (
    SkillHandler,
    SkillNotFoundException,
)
from src.service_engine.router import ServiceEngineError
from src.service_engine.schemas import ServiceRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_request(**overrides) -> ServiceRequest:
    defaults = {
        "request_type": "skill",
        "user_id": "u1",
        "skill_id": "skill-abc",
        "parameters": {"input": "hello"},
    }
    defaults.update(overrides)
    return ServiceRequest(**defaults)


def _mock_executor(result: Optional[dict] = None):
    """Return an AsyncMock executor that resolves to *result*."""
    executor = AsyncMock()
    executor.return_value = result or {"output": "done"}
    return executor


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class TestValidate:
    @pytest.mark.asyncio
    async def test_missing_skill_id_raises_400(self):
        handler = SkillHandler()
        req = _make_request(skill_id=None)
        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.validate(req)
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "MISSING_SKILL_ID"

    @pytest.mark.asyncio
    async def test_empty_skill_id_raises_400(self):
        handler = SkillHandler()
        req = _make_request(skill_id="")
        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.validate(req)
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "MISSING_SKILL_ID"

    @pytest.mark.asyncio
    async def test_valid_skill_id_passes(self):
        handler = SkillHandler()
        req = _make_request(skill_id="skill-abc")
        await handler.validate(req)  # should not raise


# ---------------------------------------------------------------------------
# Whitelist checking
# ---------------------------------------------------------------------------
class TestCheckWhitelist:
    def test_empty_whitelist_allows_all(self):
        SkillHandler.check_whitelist("any-skill", [])

    def test_skill_in_whitelist_passes(self):
        SkillHandler.check_whitelist("skill-a", ["skill-a", "skill-b"])

    def test_skill_not_in_whitelist_raises_403(self):
        with pytest.raises(ServiceEngineError) as exc_info:
            SkillHandler.check_whitelist("skill-x", ["skill-a", "skill-b"])
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "SKILL_NOT_ALLOWED"
        assert exc_info.value.details["skill_id"] == "skill-x"
        assert exc_info.value.details["allowed_skills"] == ["skill-a", "skill-b"]


# ---------------------------------------------------------------------------
# Build context
# ---------------------------------------------------------------------------
class TestBuildContext:
    @pytest.mark.asyncio
    async def test_returns_skill_context(self):
        handler = SkillHandler()
        req = _make_request(skill_id="s1", parameters={"k": "v"})
        ctx = await handler.build_context(req)
        assert ctx["skill_id"] == "s1"
        assert ctx["parameters"] == {"k": "v"}
        assert ctx["tenant_id"] == "default-tenant"

    @pytest.mark.asyncio
    async def test_extracts_tenant_from_extensions(self):
        handler = SkillHandler()
        req = _make_request(extensions={"tenant_id": "t-123"})
        ctx = await handler.build_context(req)
        assert ctx["tenant_id"] == "t-123"

    @pytest.mark.asyncio
    async def test_defaults_parameters_to_empty_dict(self):
        handler = SkillHandler()
        req = _make_request(parameters=None)
        ctx = await handler.build_context(req)
        assert ctx["parameters"] == {}


# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------
class TestExecute:
    @pytest.mark.asyncio
    async def test_returns_service_response_with_result(self):
        executor = _mock_executor({"output": "done"})
        handler = SkillHandler(skill_executor=executor)
        req = _make_request()
        ctx = await handler.build_context(req)
        resp = await handler.execute(req, ctx)

        assert resp.success is True
        assert resp.request_type == "skill"
        assert resp.data["skill_id"] == "skill-abc"
        assert resp.data["success"] is True
        assert resp.data["result"] == {"output": "done"}
        assert resp.data["execution_time_ms"] >= 0
        assert resp.metadata.request_id
        assert resp.metadata.processing_time_ms >= 0
        executor.assert_awaited_once_with("skill-abc", {"input": "hello"})

    @pytest.mark.asyncio
    async def test_skill_not_found_raises_404(self):
        executor = AsyncMock(side_effect=SkillNotFoundException("Skill xyz not found"))
        handler = SkillHandler(skill_executor=executor)
        req = _make_request(skill_id="xyz")
        ctx = await handler.build_context(req)

        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.execute(req, ctx)
        assert exc_info.value.status_code == 404
        assert exc_info.value.error_code == "SKILL_NOT_FOUND"
        assert exc_info.value.details["skill_id"] == "xyz"

    @pytest.mark.asyncio
    async def test_execution_error_raises_500(self):
        executor = AsyncMock(side_effect=RuntimeError("boom"))
        handler = SkillHandler(skill_executor=executor)
        req = _make_request()
        ctx = await handler.build_context(req)

        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.execute(req, ctx)
        assert exc_info.value.status_code == 500
        assert exc_info.value.error_code == "SKILL_EXECUTION_ERROR"


# ---------------------------------------------------------------------------
# Default executor
# ---------------------------------------------------------------------------
class TestDefaultExecutor:
    @pytest.mark.asyncio
    async def test_default_executor_returns_stub(self):
        handler = SkillHandler()  # uses _default_executor
        req = _make_request()
        ctx = await handler.build_context(req)
        resp = await handler.execute(req, ctx)
        assert resp.success is True
        assert resp.data["result"]["status"] == "executed"
