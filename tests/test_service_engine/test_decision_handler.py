"""
Unit tests for DecisionHandler — validation, structured JSON response,
LLM degradation handling, timeout, and error handling.
"""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from src.ai.llm_schemas import LLMError, LLMErrorCode, LLMException, LLMResponse, TokenUsage
from src.service_engine.handlers.decision import (
    DecisionHandler,
    _build_decision_prompt,
    _parse_decision_response,
)
from src.service_engine.router import ServiceEngineError
from src.service_engine.schemas import ServiceRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_request(**overrides) -> ServiceRequest:
    defaults = {
        "request_type": "decision",
        "user_id": "u1",
        "question": "Should we increase inventory?",
    }
    defaults.update(overrides)
    return ServiceRequest(**defaults)


def _valid_decision_json() -> dict:
    return {
        "summary": "Inventory analysis complete",
        "analysis": "Based on current trends, demand is rising.",
        "recommendations": [
            {"action": "Increase stock by 20%", "reason": "Rising demand", "priority": "high"},
        ],
        "confidence": 0.85,
    }


def _make_llm_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="test-model",
        provider="test",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        latency_ms=50.0,
    )


def _mock_llm(content: str = None):
    if content is None:
        content = json.dumps(_valid_decision_json())
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=_make_llm_response(content))
    return llm


def _mock_context_builder():
    cb = AsyncMock()
    cb.build = AsyncMock(return_value={
        "system_prompt": "You are a helpful assistant.",
        "governance_data": {},
        "business_context": {},
        "memory": [],
        "user_id": "u1",
        "tenant_id": "default-tenant",
    })
    return cb


def _mock_memory_manager():
    mm = AsyncMock()
    mm.load_memories = AsyncMock(return_value=[])
    mm.append_memory = AsyncMock()
    return mm


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class TestValidate:
    @pytest.mark.asyncio
    async def test_missing_question_raises_400(self):
        handler = DecisionHandler(llm_switcher=_mock_llm())
        req = _make_request(question=None)
        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.validate(req)
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "MISSING_QUESTION"

    @pytest.mark.asyncio
    async def test_empty_question_raises_400(self):
        handler = DecisionHandler(llm_switcher=_mock_llm())
        req = _make_request(question="")
        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.validate(req)
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "MISSING_QUESTION"

    @pytest.mark.asyncio
    async def test_valid_question_passes(self):
        handler = DecisionHandler(llm_switcher=_mock_llm())
        req = _make_request()
        await handler.validate(req)  # should not raise


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------
class TestBuildContext:
    @pytest.mark.asyncio
    async def test_loads_memories_when_enabled(self):
        mm = _mock_memory_manager()
        cb = _mock_context_builder()
        handler = DecisionHandler(
            llm_switcher=_mock_llm(), context_builder=cb, memory_manager=mm,
        )
        req = _make_request(extensions={"tenant_id": "t-1"})
        await handler.build_context(req)

        mm.load_memories.assert_awaited_once_with("u1", "t-1")
        cb.build.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_memories_when_disabled(self):
        mm = _mock_memory_manager()
        cb = _mock_context_builder()
        handler = DecisionHandler(
            llm_switcher=_mock_llm(), context_builder=cb, memory_manager=mm,
        )
        req = _make_request(include_memory=False)
        await handler.build_context(req)

        mm.load_memories.assert_not_awaited()
        cb.build.assert_awaited_once()
        assert cb.build.call_args[0][1] == []

    @pytest.mark.asyncio
    async def test_no_memory_manager_skips_load(self):
        cb = _mock_context_builder()
        handler = DecisionHandler(
            llm_switcher=_mock_llm(), context_builder=cb, memory_manager=None,
        )
        req = _make_request()
        await handler.build_context(req)
        cb.build.assert_awaited_once()


# ---------------------------------------------------------------------------
# execute — structured response
# ---------------------------------------------------------------------------
class TestExecute:
    @pytest.mark.asyncio
    async def test_returns_structured_decision_response(self):
        llm = _mock_llm()
        cb = _mock_context_builder()
        handler = DecisionHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)
        resp = await handler.execute(req, ctx)

        assert resp.success is True
        assert resp.request_type == "decision"
        assert resp.data["summary"] == "Inventory analysis complete"
        assert resp.data["confidence"] == 0.85
        assert len(resp.data["recommendations"]) == 1
        rec = resp.data["recommendations"][0]
        assert rec["action"] == "Increase stock by 20%"
        assert rec["reason"] == "Rising demand"
        assert rec["priority"] == "high"
        assert resp.metadata.request_id
        assert resp.metadata.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_appends_memory_after_execute(self):
        llm = _mock_llm()
        mm = _mock_memory_manager()
        cb = _mock_context_builder()
        handler = DecisionHandler(
            llm_switcher=llm, context_builder=cb, memory_manager=mm,
        )
        req = _make_request()
        ctx = await handler.build_context(req)
        await handler.execute(req, ctx)

        mm.append_memory.assert_awaited_once()
        call_kwargs = mm.append_memory.call_args[1]
        assert call_kwargs["user_id"] == "u1"
        assert call_kwargs["content"]["question"] == "Should we increase inventory?"
        assert "decision" in call_kwargs["content"]

    @pytest.mark.asyncio
    async def test_skips_memory_when_disabled(self):
        llm = _mock_llm()
        mm = _mock_memory_manager()
        cb = _mock_context_builder()
        handler = DecisionHandler(
            llm_switcher=llm, context_builder=cb, memory_manager=mm,
        )
        req = _make_request(include_memory=False)
        ctx = await handler.build_context(req)
        await handler.execute(req, ctx)

        mm.append_memory.assert_not_awaited()


# ---------------------------------------------------------------------------
# execute — LLM degradation
# ---------------------------------------------------------------------------
class TestDegradation:
    @pytest.mark.asyncio
    async def test_non_json_response_degrades_with_confidence_zero(self):
        raw_text = "I think you should increase inventory based on trends."
        llm = _mock_llm(raw_text)
        cb = _mock_context_builder()
        handler = DecisionHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)
        resp = await handler.execute(req, ctx)

        assert resp.success is True
        assert resp.data["confidence"] == 0
        assert resp.data["analysis"] == raw_text
        assert resp.data["recommendations"] == []

    @pytest.mark.asyncio
    async def test_partial_json_missing_keys_degrades(self):
        partial = json.dumps({"summary": "ok", "analysis": "some text"})
        llm = _mock_llm(partial)
        cb = _mock_context_builder()
        handler = DecisionHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)
        resp = await handler.execute(req, ctx)

        assert resp.data["confidence"] == 0
        assert resp.data["recommendations"] == []


# ---------------------------------------------------------------------------
# execute — error handling
# ---------------------------------------------------------------------------
class TestExecuteErrors:
    @pytest.mark.asyncio
    async def test_llm_unavailable_raises_503(self):
        llm = AsyncMock()
        llm.generate = AsyncMock(
            side_effect=LLMException(
                LLMError(
                    error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
                    message="LLM down",
                    provider="test",
                )
            )
        )
        cb = _mock_context_builder()
        handler = DecisionHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)
        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.execute(req, ctx)
        assert exc_info.value.status_code == 503
        assert exc_info.value.error_code == "LLM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_timeout_raises_504(self):
        async def slow_generate(**kwargs):
            await asyncio.sleep(120)

        llm = AsyncMock()
        llm.generate = slow_generate
        cb = _mock_context_builder()
        handler = DecisionHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)

        import src.service_engine.handlers.decision as decision_mod
        original = decision_mod._TIMEOUT_SECONDS
        decision_mod._TIMEOUT_SECONDS = 0.01
        try:
            with pytest.raises(ServiceEngineError) as exc_info:
                await handler.execute(req, ctx)
            assert exc_info.value.status_code == 504
            assert exc_info.value.error_code == "REQUEST_TIMEOUT"
        finally:
            decision_mod._TIMEOUT_SECONDS = original


# ---------------------------------------------------------------------------
# _parse_decision_response
# ---------------------------------------------------------------------------
class TestParseDecisionResponse:
    def test_valid_json_returns_parsed(self):
        data = _valid_decision_json()
        result = _parse_decision_response(json.dumps(data))
        assert result["summary"] == data["summary"]
        assert result["confidence"] == 0.85
        assert len(result["recommendations"]) == 1

    def test_invalid_json_returns_degraded(self):
        result = _parse_decision_response("not json at all")
        assert result["confidence"] == 0
        assert result["analysis"] == "not json at all"
        assert result["recommendations"] == []

    def test_missing_required_keys_returns_degraded(self):
        partial = json.dumps({"summary": "ok"})
        result = _parse_decision_response(partial)
        assert result["confidence"] == 0

    def test_empty_string_returns_degraded(self):
        result = _parse_decision_response("")
        assert result["confidence"] == 0
        assert result["summary"] == ""
        assert result["analysis"] == ""

    def test_long_raw_text_truncates_summary(self):
        long_text = "x" * 1000
        result = _parse_decision_response(long_text)
        assert len(result["summary"]) == 500
        assert len(result["analysis"]) == 1000


# ---------------------------------------------------------------------------
# _build_decision_prompt
# ---------------------------------------------------------------------------
class TestBuildDecisionPrompt:
    def test_includes_question(self):
        ctx = {
            "governance_data": {},
            "business_context": {},
            "memory": [],
        }
        req = _make_request()
        prompt = _build_decision_prompt(ctx, req)
        assert "[Decision Question]" in prompt
        assert "Should we increase inventory?" in prompt

    def test_includes_context_data(self):
        ctx = {
            "governance_data": {},
            "business_context": {},
            "memory": [],
        }
        req = _make_request(context_data={"sales": [100, 200, 300]})
        prompt = _build_decision_prompt(ctx, req)
        assert "[Context Data]" in prompt
        assert "sales" in prompt

    def test_includes_governance_data(self):
        ctx = {
            "governance_data": {"annotations": [{"id": "1"}]},
            "business_context": {},
            "memory": [],
        }
        req = _make_request()
        prompt = _build_decision_prompt(ctx, req)
        assert "[Platform Data]" in prompt
        assert "annotations" in prompt
