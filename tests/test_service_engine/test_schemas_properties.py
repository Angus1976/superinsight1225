"""
Property-based tests for Smart Service Engine schemas.

Tests ServiceRequest Pydantic model validation using Hypothesis.
Covers Properties 2, 10, and 11 from the design document.
"""

import json

import pytest
from hypothesis import assume, given, settings, strategies as st
from pydantic import ValidationError

from src.service_engine.schemas import ServiceRequest, VALID_REQUEST_TYPES


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 2: Invalid enum rejection
# Any request_type NOT in ("query", "chat", "decision", "skill") must raise
# ValidationError.
# Validates: Requirements 1.7
# ---------------------------------------------------------------------------

@given(invalid_type=st.text(min_size=1))
@settings(max_examples=100)
def test_invalid_request_type_rejected(invalid_type: str):
    """Arbitrary invalid request_type should trigger a ValidationError."""
    assume(invalid_type not in VALID_REQUEST_TYPES)

    with pytest.raises(ValidationError):
        ServiceRequest(
            request_type=invalid_type,
            user_id="test_user",
        )


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 10: user_id required validation
# Missing or empty/whitespace-only user_id must raise ValidationError.
# Validates: Requirements 6.1, 6.4
# ---------------------------------------------------------------------------

@given(blank_id=st.text(alphabet=" \t\n\r", min_size=0, max_size=20))
@settings(max_examples=100)
def test_empty_or_whitespace_user_id_rejected(blank_id: str):
    """Empty or whitespace-only user_id should trigger a ValidationError."""
    with pytest.raises(ValidationError):
        ServiceRequest(
            request_type="query",
            user_id=blank_id,
        )


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 11: business_context size limit
# business_context serialised to >100KB must raise ValidationError.
# Validates: Requirements 6.5
# ---------------------------------------------------------------------------

MAX_CONTEXT_BYTES = 100 * 1024  # 100 KB


@given(padding_size=st.integers(min_value=1, max_value=50))
@settings(max_examples=100)
def test_oversized_business_context_rejected(padding_size: int):
    """business_context exceeding 100KB should trigger a ValidationError."""
    # Build a dict whose JSON serialisation exceeds 100KB.
    # Use a single key with a long string value for efficiency.
    # Account for JSON overhead: {"k": "..."} adds ~7 bytes
    value = "x" * (MAX_CONTEXT_BYTES + padding_size)
    oversized_context = {"k": value}

    with pytest.raises(ValidationError):
        ServiceRequest(
            request_type="query",
            user_id="test_user",
            business_context=oversized_context,
        )
