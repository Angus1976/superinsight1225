"""
Property-based tests for RequestRouter.

Tests routing correctness, scope enforcement, and dynamic enable/disable
using Hypothesis. Covers Properties 1, 3, and 18 from the design document.
"""

import pytest
from hypothesis import given, settings, strategies as st

from src.service_engine.base import BaseHandler
from src.service_engine.router import RequestRouter, ServiceEngineError
from src.service_engine.schemas import (
    ServiceRequest,
    ServiceResponse,
    ResponseMetadata,
    VALID_REQUEST_TYPES,
)


# ---------------------------------------------------------------------------
# Stub handler — records which handler was invoked via a tag
# ---------------------------------------------------------------------------
class StubHandler(BaseHandler):
    """Minimal handler that returns a tagged response for dispatch verification."""

    def __init__(self, tag: str = "stub"):
        self.tag = tag

    async def validate(self, request: ServiceRequest) -> None:
        pass

    async def build_context(self, request: ServiceRequest) -> dict:
        return {"source": self.tag}

    async def execute(
        self, request: ServiceRequest, context: dict
    ) -> ServiceResponse:
        return ServiceResponse(
            success=True,
            request_type=request.request_type,
            data={"handler": self.tag, **context},
            metadata=ResponseMetadata(
                request_id="prop-test",
                timestamp="2025-01-01T00:00:00Z",
                processing_time_ms=0,
            ),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_TYPES_LIST = list(VALID_REQUEST_TYPES)

valid_request_type = st.sampled_from(VALID_TYPES_LIST)


def _make_request(rtype: str) -> ServiceRequest:
    return ServiceRequest(request_type=rtype, user_id="u1")


def _scopes_for(*types: str) -> dict:
    return {t: True for t in types}


def _router_with_all_handlers() -> RequestRouter:
    """Create a router with a uniquely-tagged StubHandler for each valid type."""
    router = RequestRouter()
    for rtype in VALID_TYPES_LIST:
        router.register(rtype, StubHandler(tag=rtype))
    return router


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 1: Routing correctness
# For any valid request_type, route() dispatches to the handler registered
# for that type (verified by checking the handler tag in response data).
# Validates: Requirements 1.3, 1.4, 1.5, 1.6
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(rtype=valid_request_type)
@settings(max_examples=100)
async def test_route_dispatches_to_correct_handler(rtype: str):
    """Valid request_type is routed to its registered handler."""
    router = _router_with_all_handlers()
    request = _make_request(rtype)
    scopes = _scopes_for(rtype)

    resp = await router.route(request, scopes)

    assert resp.success is True
    assert resp.request_type == rtype
    assert resp.data["handler"] == rtype


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 3: Scope enforcement
# For any request_type, if the API key scopes do NOT include that type,
# route() raises ServiceEngineError with status_code=403 and
# error_code="INSUFFICIENT_SCOPE".
# Validates: Requirements 2.3, 11.2, 11.3
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(rtype=valid_request_type)
@settings(max_examples=100)
async def test_missing_scope_returns_403(rtype: str):
    """Request without the required scope is rejected with 403."""
    router = _router_with_all_handlers()
    request = _make_request(rtype)

    # Build scopes that include every type EXCEPT the requested one
    other_types = [t for t in VALID_TYPES_LIST if t != rtype]
    scopes = _scopes_for(*other_types)

    with pytest.raises(ServiceEngineError) as exc_info:
        await router.route(request, scopes)

    err = exc_info.value
    assert err.status_code == 403
    assert err.error_code == "INSUFFICIENT_SCOPE"


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 18: Dynamic enable/disable
# For any request_type, after calling disable(), route() raises
# ServiceEngineError with error_code="REQUEST_TYPE_DISABLED" even when
# the API key has the correct scope.
# Validates: Requirements 12.4
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(rtype=valid_request_type)
@settings(max_examples=100)
async def test_disabled_type_rejected_despite_valid_scope(rtype: str):
    """Disabled request_type is rejected even with correct scope."""
    router = _router_with_all_handlers()
    router.disable(rtype)

    request = _make_request(rtype)
    scopes = _scopes_for(rtype)

    with pytest.raises(ServiceEngineError) as exc_info:
        await router.route(request, scopes)

    err = exc_info.value
    assert err.status_code == 403
    assert err.error_code == "REQUEST_TYPE_DISABLED"
