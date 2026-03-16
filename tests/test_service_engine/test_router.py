"""
Unit tests for RequestRouter — handler registry, enable/disable, scope checking,
and the full route() pipeline.
"""

import pytest

from src.service_engine.base import BaseHandler
from src.service_engine.router import RequestRouter, ServiceEngineError
from src.service_engine.schemas import ServiceRequest, ServiceResponse, ResponseMetadata


# ---------------------------------------------------------------------------
# Stub handler for testing
# ---------------------------------------------------------------------------
class StubHandler(BaseHandler):
    """Minimal handler that records calls and returns a canned response."""

    def __init__(self, tag: str = "stub"):
        self.tag = tag
        self.validated = False
        self.built_context = False

    async def validate(self, request: ServiceRequest) -> None:
        self.validated = True

    async def build_context(self, request: ServiceRequest) -> dict:
        self.built_context = True
        return {"source": self.tag}

    async def execute(
        self, request: ServiceRequest, context: dict
    ) -> ServiceResponse:
        return ServiceResponse(
            success=True,
            request_type=request.request_type,
            data={"handler": self.tag, **context},
            metadata=ResponseMetadata(
                request_id="test-id",
                timestamp="2025-01-01T00:00:00Z",
                processing_time_ms=1,
            ),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_request(rtype: str = "query") -> ServiceRequest:
    return ServiceRequest(request_type=rtype, user_id="u1")


def _scopes_for(*types: str) -> dict:
    return {t: True for t in types}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
class TestRegister:
    def test_register_handler(self):
        router = RequestRouter()
        handler = StubHandler("query")
        router.register("query", handler)
        assert router._handlers["query"] is handler

    def test_register_overwrites(self):
        router = RequestRouter()
        router.register("query", StubHandler("old"))
        new = StubHandler("new")
        router.register("query", new)
        assert router._handlers["query"] is new


# ---------------------------------------------------------------------------
# Enable / Disable
# ---------------------------------------------------------------------------
class TestEnableDisable:
    def test_disable_adds_to_set(self):
        router = RequestRouter()
        router.disable("query")
        assert "query" in router._disabled_types

    def test_enable_removes_from_set(self):
        router = RequestRouter()
        router.disable("query")
        router.enable("query")
        assert "query" not in router._disabled_types

    def test_enable_noop_when_not_disabled(self):
        router = RequestRouter()
        router.enable("query")  # should not raise
        assert "query" not in router._disabled_types


# ---------------------------------------------------------------------------
# Scope checking
# ---------------------------------------------------------------------------
class TestCheckScope:
    def test_passes_when_scope_present(self):
        router = RequestRouter()
        router.check_scope({"query": True}, "query")  # no exception

    def test_raises_when_scope_missing(self):
        router = RequestRouter()
        with pytest.raises(ServiceEngineError) as exc_info:
            router.check_scope({"chat": True}, "query")
        err = exc_info.value
        assert err.status_code == 403
        assert err.error_code == "INSUFFICIENT_SCOPE"
        assert "query" in err.message

    def test_raises_when_scope_false(self):
        router = RequestRouter()
        with pytest.raises(ServiceEngineError) as exc_info:
            router.check_scope({"query": False}, "query")
        assert exc_info.value.error_code == "INSUFFICIENT_SCOPE"

    def test_details_contain_available_scopes(self):
        router = RequestRouter()
        with pytest.raises(ServiceEngineError) as exc_info:
            router.check_scope({"chat": True, "query": False}, "query")
        assert exc_info.value.details["available_scopes"] == ["chat"]


# ---------------------------------------------------------------------------
# Route pipeline
# ---------------------------------------------------------------------------
class TestRoute:
    @pytest.mark.asyncio
    async def test_successful_route(self):
        router = RequestRouter()
        handler = StubHandler("query")
        router.register("query", handler)

        resp = await router.route(_make_request("query"), _scopes_for("query"))

        assert resp.success is True
        assert resp.request_type == "query"
        assert resp.data["handler"] == "query"
        assert handler.validated is True
        assert handler.built_context is True

    @pytest.mark.asyncio
    async def test_unregistered_type_raises_400(self):
        router = RequestRouter()
        with pytest.raises(ServiceEngineError) as exc_info:
            await router.route(_make_request("query"), _scopes_for("query"))
        err = exc_info.value
        assert err.status_code == 400
        assert err.error_code == "INVALID_REQUEST_TYPE"

    @pytest.mark.asyncio
    async def test_disabled_type_raises_403(self):
        router = RequestRouter()
        router.register("query", StubHandler())
        router.disable("query")

        with pytest.raises(ServiceEngineError) as exc_info:
            await router.route(_make_request("query"), _scopes_for("query"))
        err = exc_info.value
        assert err.status_code == 403
        assert err.error_code == "REQUEST_TYPE_DISABLED"

    @pytest.mark.asyncio
    async def test_missing_scope_raises_403(self):
        router = RequestRouter()
        router.register("query", StubHandler())

        with pytest.raises(ServiceEngineError) as exc_info:
            await router.route(_make_request("query"), _scopes_for("chat"))
        assert exc_info.value.error_code == "INSUFFICIENT_SCOPE"

    @pytest.mark.asyncio
    async def test_pipeline_order_disabled_before_scope(self):
        """Disabled check runs before scope check — error code should be
        REQUEST_TYPE_DISABLED even when scope is also missing."""
        router = RequestRouter()
        router.register("query", StubHandler())
        router.disable("query")

        with pytest.raises(ServiceEngineError) as exc_info:
            await router.route(_make_request("query"), {})
        assert exc_info.value.error_code == "REQUEST_TYPE_DISABLED"

    @pytest.mark.asyncio
    async def test_re_enable_allows_routing(self):
        router = RequestRouter()
        router.register("query", StubHandler("q"))
        router.disable("query")
        router.enable("query")

        resp = await router.route(_make_request("query"), _scopes_for("query"))
        assert resp.success is True
