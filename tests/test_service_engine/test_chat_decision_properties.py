"""
Property-based tests for ChatHandler and DecisionHandler.

Tests SSE stream format consistency and decision response structure
completeness using Hypothesis.
Covers Properties 7 and 8 from the design document.
"""

import json

import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import AsyncMock

from src.service_engine.handlers.chat import ChatHandler
from src.service_engine.handlers.decision import _parse_decision_response
from src.service_engine.schemas import ServiceRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chat_request() -> ServiceRequest:
    return ServiceRequest(
        request_type="chat",
        user_id="u1",
        messages=[{"role": "user", "content": "hello"}],
    )


def _mock_context() -> dict:
    return {
        "system_prompt": "You are a helpful assistant.",
        "governance_data": {},
        "business_context": {},
        "memory": [],
        "user_id": "u1",
        "tenant_id": "default-tenant",
    }


async def _collect_stream(handler: ChatHandler, request, context) -> list[dict]:
    """Collect all chunks from stream_execute."""
    chunks: list[dict] = []
    async for chunk in handler.stream_execute(request, context):
        chunks.append(chunk)
    return chunks


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 7: SSE 流格式一致性
# For any chat request's SSE response stream, all non-terminal chunks
# should contain {"content": "...", "done": false}, and the last chunk
# should be {"content": "", "done": true}.
# Validates: Requirements 3.5, 3.6
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(chunks=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=20))
@settings(max_examples=100)
async def test_sse_stream_format_consistency(chunks: list[str]):
    """All intermediate chunks have done=False; final chunk has done=True and empty content."""

    async def mock_stream_generate(**kwargs):
        for c in chunks:
            yield c

    llm = AsyncMock()
    llm.stream_generate = mock_stream_generate

    cb = AsyncMock()
    cb.build = AsyncMock(return_value=_mock_context())

    handler = ChatHandler(llm_switcher=llm, context_builder=cb)
    request = _make_chat_request()
    context = _mock_context()

    collected = await _collect_stream(handler, request, context)

    # Must have at least len(chunks) intermediate + 1 final
    assert len(collected) == len(chunks) + 1

    # All intermediate chunks: done=False, non-empty content
    for i, c in enumerate(collected[:-1]):
        assert c["done"] is False, f"Chunk {i} should have done=False"
        assert "content" in c, f"Chunk {i} missing 'content' key"
        assert c["content"] == chunks[i]

    # Final chunk: done=True, empty content
    final = collected[-1]
    assert final["done"] is True
    assert final["content"] == ""


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 8: 决策响应结构完整性
# For any successful decision response, data should contain summary,
# analysis, recommendations, confidence. Each recommendation should
# contain action, reason, priority.
# Validates: Requirements 4.4, 4.5
# ---------------------------------------------------------------------------

# Strategies for valid decision structures
_recommendation_st = st.fixed_dictionaries({
    "action": st.text(min_size=1, max_size=50),
    "reason": st.text(min_size=1, max_size=50),
    "priority": st.sampled_from(["high", "medium", "low"]),
})

_decision_st = st.fixed_dictionaries({
    "summary": st.text(min_size=1, max_size=200),
    "analysis": st.text(min_size=1, max_size=500),
    "recommendations": st.lists(_recommendation_st, min_size=0, max_size=5),
    "confidence": st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
})

_REQUIRED_KEYS = {"summary", "analysis", "recommendations", "confidence"}
_REQUIRED_REC_KEYS = {"action", "reason", "priority"}


@given(decision=_decision_st)
@settings(max_examples=100)
def test_decision_response_structure_completeness_valid(decision: dict):
    """Valid decision JSON parsed by _parse_decision_response retains all required keys."""
    raw = json.dumps(decision)
    result = _parse_decision_response(raw)

    # All top-level required keys present
    assert _REQUIRED_KEYS.issubset(result.keys()), (
        f"Missing keys: {_REQUIRED_KEYS - set(result.keys())}"
    )

    # Each recommendation has required sub-keys
    for i, rec in enumerate(result["recommendations"]):
        assert _REQUIRED_REC_KEYS.issubset(rec.keys()), (
            f"Recommendation {i} missing keys: {_REQUIRED_REC_KEYS - set(rec.keys())}"
        )


@given(raw=st.text(min_size=0, max_size=500).filter(lambda s: not _is_valid_decision_json(s)))
@settings(max_examples=100)
def test_decision_response_structure_completeness_degraded(raw: str):
    """Non-JSON or incomplete JSON degrades gracefully: confidence=0, recommendations=[]."""
    result = _parse_decision_response(raw)

    # Degraded response still has all required keys
    assert _REQUIRED_KEYS.issubset(result.keys())
    assert result["confidence"] == 0
    assert result["recommendations"] == []


def _is_valid_decision_json(s: str) -> bool:
    """Check if string is valid JSON with all required decision keys."""
    try:
        parsed = json.loads(s)
        return isinstance(parsed, dict) and _REQUIRED_KEYS.issubset(parsed)
    except (json.JSONDecodeError, TypeError):
        return False
