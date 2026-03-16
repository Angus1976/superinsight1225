"""
Unit tests for ChatHandler — validation, non-streaming execute,
SSE stream_execute, timeout handling, and LLM error handling.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ai.llm_schemas import LLMError, LLMErrorCode, LLMException, LLMResponse, TokenUsage
from src.service_engine.handlers.chat import ChatHandler, _build_prompt
from src.service_engine.router import ServiceEngineError
from src.service_engine.schemas import ServiceRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_request(**overrides) -> ServiceRequest:
    defaults = {
        "request_type": "chat",
        "user_id": "u1",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    defaults.update(overrides)
    return ServiceRequest(**defaults)


def _make_llm_response(content: str = "Hi there") -> LLMResponse:
    return LLMResponse(
        content=content,
        model="test-model",
        provider="test",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        latency_ms=42.0,
    )


def _mock_llm(content: str = "Hi there"):
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


async def _collect_stream(handler, request, context) -> list[dict]:
    """Collect all chunks from stream_execute into a list."""
    chunks = []
    async for chunk in handler.stream_execute(request, context):
        chunks.append(chunk)
    return chunks


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class TestValidate:
    @pytest.mark.asyncio
    async def test_missing_messages_raises_400(self):
        handler = ChatHandler(llm_switcher=_mock_llm())
        req = _make_request(messages=None)
        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.validate(req)
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "MISSING_MESSAGES"

    @pytest.mark.asyncio
    async def test_empty_messages_raises_400(self):
        handler = ChatHandler(llm_switcher=_mock_llm())
        req = _make_request(messages=[])
        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.validate(req)
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "MISSING_MESSAGES"

    @pytest.mark.asyncio
    async def test_valid_messages_pass(self):
        handler = ChatHandler(llm_switcher=_mock_llm())
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
        handler = ChatHandler(
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
        handler = ChatHandler(
            llm_switcher=_mock_llm(), context_builder=cb, memory_manager=mm,
        )
        req = _make_request(include_memory=False)
        await handler.build_context(req)

        mm.load_memories.assert_not_awaited()
        # build should still be called with empty memories
        cb.build.assert_awaited_once()
        _, call_args = cb.build.call_args
        # positional: (request, memories)
        assert cb.build.call_args[0][1] == []

    @pytest.mark.asyncio
    async def test_no_memory_manager_skips_load(self):
        cb = _mock_context_builder()
        handler = ChatHandler(
            llm_switcher=_mock_llm(), context_builder=cb, memory_manager=None,
        )
        req = _make_request()
        await handler.build_context(req)
        cb.build.assert_awaited_once()


# ---------------------------------------------------------------------------
# execute (non-streaming)
# ---------------------------------------------------------------------------
class TestExecute:
    @pytest.mark.asyncio
    async def test_returns_service_response_with_content(self):
        llm = _mock_llm("Analysis result")
        cb = _mock_context_builder()
        handler = ChatHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)
        resp = await handler.execute(req, ctx)

        assert resp.success is True
        assert resp.request_type == "chat"
        assert resp.data["content"] == "Analysis result"
        assert resp.metadata.request_id
        assert resp.metadata.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_appends_memory_after_execute(self):
        llm = _mock_llm("response text")
        mm = _mock_memory_manager()
        cb = _mock_context_builder()
        handler = ChatHandler(
            llm_switcher=llm, context_builder=cb, memory_manager=mm,
        )
        req = _make_request()
        ctx = await handler.build_context(req)
        await handler.execute(req, ctx)

        mm.append_memory.assert_awaited_once()
        call_kwargs = mm.append_memory.call_args[1]
        assert call_kwargs["user_id"] == "u1"
        assert call_kwargs["content"]["response"] == "response text"

    @pytest.mark.asyncio
    async def test_skips_memory_when_disabled(self):
        llm = _mock_llm()
        mm = _mock_memory_manager()
        cb = _mock_context_builder()
        handler = ChatHandler(
            llm_switcher=llm, context_builder=cb, memory_manager=mm,
        )
        req = _make_request(include_memory=False)
        ctx = await handler.build_context(req)
        await handler.execute(req, ctx)

        mm.append_memory.assert_not_awaited()


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
        handler = ChatHandler(llm_switcher=llm, context_builder=cb)

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
        handler = ChatHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)

        # Patch timeout to 0.01s for fast test
        import src.service_engine.handlers.chat as chat_mod
        original = chat_mod._TIMEOUT_SECONDS
        chat_mod._TIMEOUT_SECONDS = 0.01
        try:
            with pytest.raises(ServiceEngineError) as exc_info:
                await handler.execute(req, ctx)
            assert exc_info.value.status_code == 504
            assert exc_info.value.error_code == "REQUEST_TIMEOUT"
        finally:
            chat_mod._TIMEOUT_SECONDS = original


# ---------------------------------------------------------------------------
# stream_execute (SSE)
# ---------------------------------------------------------------------------
class TestStreamExecute:
    @pytest.mark.asyncio
    async def test_yields_intermediate_and_final_chunks(self):
        async def mock_stream(**kwargs):
            for word in ["Hello", " ", "world"]:
                yield word

        llm = AsyncMock()
        llm.stream_generate = mock_stream
        cb = _mock_context_builder()
        handler = ChatHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)
        chunks = await _collect_stream(handler, req, ctx)

        # 3 intermediate + 1 final
        assert len(chunks) == 4
        assert all(c["done"] is False for c in chunks[:-1])
        assert chunks[-1] == {"content": "", "done": True}
        # Content pieces
        assert chunks[0]["content"] == "Hello"
        assert chunks[1]["content"] == " "
        assert chunks[2]["content"] == "world"

    @pytest.mark.asyncio
    async def test_empty_stream_yields_only_final(self):
        async def mock_stream(**kwargs):
            return
            yield  # make it an async generator

        llm = AsyncMock()
        llm.stream_generate = mock_stream
        cb = _mock_context_builder()
        handler = ChatHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)
        chunks = await _collect_stream(handler, req, ctx)

        assert len(chunks) == 1
        assert chunks[0] == {"content": "", "done": True}

    @pytest.mark.asyncio
    async def test_stream_llm_error_raises_503(self):
        async def failing_stream(**kwargs):
            yield "partial"
            raise LLMException(
                LLMError(
                    error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
                    message="stream failed",
                    provider="test",
                )
            )

        llm = AsyncMock()
        llm.stream_generate = failing_stream
        cb = _mock_context_builder()
        handler = ChatHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)
        with pytest.raises(ServiceEngineError) as exc_info:
            await _collect_stream(handler, req, ctx)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_stream_timeout_raises_504(self):
        async def slow_stream(**kwargs):
            yield "start"
            await asyncio.sleep(120)
            yield "never"

        llm = AsyncMock()
        llm.stream_generate = slow_stream
        cb = _mock_context_builder()
        handler = ChatHandler(llm_switcher=llm, context_builder=cb)

        req = _make_request()
        ctx = await handler.build_context(req)

        import src.service_engine.handlers.chat as chat_mod
        original = chat_mod._TIMEOUT_SECONDS
        chat_mod._TIMEOUT_SECONDS = 0.01
        try:
            with pytest.raises(ServiceEngineError) as exc_info:
                await _collect_stream(handler, req, ctx)
            assert exc_info.value.status_code == 504
        finally:
            chat_mod._TIMEOUT_SECONDS = original


# ---------------------------------------------------------------------------
# _build_prompt helper
# ---------------------------------------------------------------------------
class TestBuildPrompt:
    def test_includes_messages(self):
        ctx = {
            "governance_data": {},
            "business_context": {},
            "memory": [],
        }
        messages = [{"role": "user", "content": "What is the status?"}]
        prompt = _build_prompt(ctx, messages)
        assert "user: What is the status?" in prompt

    def test_includes_governance_data(self):
        ctx = {
            "governance_data": {"annotations": [{"id": "1"}]},
            "business_context": {},
            "memory": [],
        }
        prompt = _build_prompt(ctx, [{"role": "user", "content": "hi"}])
        assert "[Platform Data]" in prompt
        assert "annotations" in prompt

    def test_empty_context_still_works(self):
        ctx = {
            "governance_data": {},
            "business_context": {},
            "memory": [],
        }
        prompt = _build_prompt(ctx, [{"role": "user", "content": "hi"}])
        assert "user: hi" in prompt
