"""
Property-based tests for Smart Service Engine unified response format.

Tests ServiceResponse and ErrorResponse Pydantic models using Hypothesis.
Covers Properties 16 and 17 from the design document.
"""

from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, strategies as st

from src.service_engine.schemas import (
    ErrorResponse,
    ResponseMetadata,
    ServiceResponse,
)


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 16: 统一成功响应结构
# For any successful response (non-SSE), it should contain success=true,
# request_type (echoed), data, and metadata (with request_id, timestamp,
# processing_time_ms).
# Validates: Requirements 10.2, 10.4
# ---------------------------------------------------------------------------


@given(
    request_type=st.sampled_from(["query", "chat", "decision", "skill"]),
    data=st.fixed_dictionaries({"key": st.text(min_size=1, max_size=50)}),
    request_id=st.uuids().map(str),
    processing_time_ms=st.integers(min_value=0, max_value=10000),
)
@settings(max_examples=100)
def test_unified_success_response_structure(
    request_type, data, request_id, processing_time_ms
):
    """Arbitrary successful response must contain success, request_type, data, metadata."""
    resp = ServiceResponse(
        success=True,
        request_type=request_type,
        data=data,
        metadata=ResponseMetadata(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=processing_time_ms,
        ),
    )
    dumped = resp.model_dump()

    # success must be True
    assert dumped["success"] is True
    # request_type echoed back
    assert dumped["request_type"] == request_type
    # data present and matches input
    assert "data" in dumped
    assert dumped["data"] == data
    # metadata present with all required sub-fields
    assert "metadata" in dumped
    meta = dumped["metadata"]
    assert "request_id" in meta
    assert meta["request_id"] == request_id
    assert "timestamp" in meta
    assert "processing_time_ms" in meta
    assert meta["processing_time_ms"] == processing_time_ms


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 17: 统一错误响应结构
# For any error response, it should contain success=false, error, error_code,
# and details.
# Validates: Requirements 10.3
# ---------------------------------------------------------------------------


@given(
    error=st.text(min_size=1, max_size=200),
    error_code=st.sampled_from([
        "INVALID_REQUEST_TYPE",
        "INSUFFICIENT_SCOPE",
        "INTERNAL_ERROR",
        "LLM_UNAVAILABLE",
        "REQUEST_TIMEOUT",
    ]),
    details=st.one_of(
        st.none(),
        st.fixed_dictionaries({"info": st.text(min_size=1, max_size=50)}),
    ),
)
@settings(max_examples=100)
def test_unified_error_response_structure(error, error_code, details):
    """Arbitrary error response must contain success=false, error, error_code, details."""
    resp = ErrorResponse(error=error, error_code=error_code, details=details)
    dumped = resp.model_dump()

    # success must default to False
    assert dumped["success"] is False
    # error message preserved
    assert dumped["error"] == error
    # error_code preserved
    assert dumped["error_code"] == error_code
    # details field always present in output (None or dict)
    assert "details" in dumped
    if details is not None:
        assert dumped["details"] == details
    else:
        assert dumped["details"] is None
