"""
Unit tests for the unified Service Engine API endpoint.

Uses FastAPI TestClient with mocked handlers to avoid real DB/LLM calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.service_engine.api import router, _engine
from src.service_engine.base import BaseHandler
from src.service_engine.router import RequestRouter, ServiceEngineError
from src.service_engine.schemas import (
    ResponseMetadata,
    ServiceRequest,
    ServiceResponse,
)


# ---------------------------------------------------------------------------
# Stub handler
# ---------------------------------------------------------------------------
class StubHandler(BaseHandler):
    """Returns a canned ServiceResponse for any request."""

    def __init__(self, tag: str = "stub"):
        self.tag = tag

    async def validate(self, request: ServiceRequest) -> None:
        pass

    async def build_context(self, request: ServiceRequest) -> dict:
        return {"source": self.tag}

    async def execute(self, request: ServiceRequest, context: dict) -> ServiceResponse:
        return ServiceResponse(
            success=True,
            request_type=request.request_type,
            data={"handler": self.tag},
            metadata=ResponseMetadata(
                request_id="test-req-id",
                timestamp="2025-01-01T00:00:00Z",
                processing_time_ms=1,
            ),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_test_engine() -> RequestRouter:
    """Build a RequestRouter with StubHandlers for all four types."""
    engine = RequestRouter()
    for rtype in ("query", "chat", "decision", "skill"):
        engine.register(rtype, StubHandler(rtype))
    return engine


def _make_app() -> tuple:
    """Create a minimal FastAPI app with the service engine router."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    return app, client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidQueryRequest:
    """POST with a valid query request → 200 with ServiceResponse structure."""

    def test_returns_200_with_service_response(self):
        _, client = _make_app()
        test_engine = _build_test_engine()

        with patch("src.service_engine.api._engine", test_engine):
            resp = client.post(
                "/api/v1/service/request",
                json={
                    "request_type": "query",
                    "user_id": "user-1",
                    "data_type": "annotations",
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["request_type"] == "query"
        assert "data" in body
        assert "metadata" in body
        assert "request_id" in body["metadata"]
        assert "timestamp" in body["metadata"]
        assert "processing_time_ms" in body["metadata"]


class TestInvalidRequestType:
    """POST with invalid request_type → 400 from Pydantic validation."""

    def test_invalid_request_type_returns_422(self):
        _, client = _make_app()

        resp = client.post(
            "/api/v1/service/request",
            json={
                "request_type": "invalid_type",
                "user_id": "user-1",
            },
        )
        # Pydantic Literal validation triggers 422
        assert resp.status_code == 422


class TestMissingUserId:
    """POST with missing user_id → 422 (Pydantic validation)."""

    def test_missing_user_id_returns_422(self):
        _, client = _make_app()

        resp = client.post(
            "/api/v1/service/request",
            json={"request_type": "query"},
        )
        assert resp.status_code == 422


class TestServiceEngineErrorResponse:
    """ServiceEngineError from router → proper error response."""

    def test_service_engine_error_returns_correct_status(self):
        _, client = _make_app()

        failing_engine = RequestRouter()
        # No handlers registered → route() raises INVALID_REQUEST_TYPE (400)
        with patch("src.service_engine.api._engine", failing_engine):
            resp = client.post(
                "/api/v1/service/request",
                json={
                    "request_type": "query",
                    "user_id": "user-1",
                },
            )

        assert resp.status_code == 400
        body = resp.json()
        assert body["success"] is False
        assert body["error_code"] == "INVALID_REQUEST_TYPE"
        assert "error" in body

    def test_scope_error_returns_403(self):
        """API key scopes missing → 403 INSUFFICIENT_SCOPE."""
        _, client = _make_app()

        engine = _build_test_engine()

        # Simulate restricted scopes via a mock api_key on request.state
        mock_api_key = MagicMock()
        mock_api_key.allowed_request_types = ["chat"]  # no "query"

        class _ScopeMiddleware:
            """Inject api_key into request.state before the route runs."""

            def __init__(self, app):
                self.app = app

            async def __call__(self, scope, receive, send):
                if scope["type"] == "http":
                    scope.setdefault("state", {})["api_key"] = mock_api_key
                await self.app(scope, receive, send)

        app = FastAPI()
        app.include_router(router)
        app.add_middleware(_ScopeMiddleware)
        scoped_client = TestClient(app)

        with patch("src.service_engine.api._engine", engine):
            resp = scoped_client.post(
                "/api/v1/service/request",
                json={
                    "request_type": "query",
                    "user_id": "user-1",
                },
            )

        assert resp.status_code == 403
        body = resp.json()
        assert body["error_code"] == "INSUFFICIENT_SCOPE"


class TestInternalError:
    """Unexpected exception → 500 with INTERNAL_ERROR."""

    def test_unexpected_exception_returns_500(self):
        _, client = _make_app()

        broken_engine = MagicMock(spec=RequestRouter)
        broken_engine.route = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("src.service_engine.api._engine", broken_engine):
            resp = client.post(
                "/api/v1/service/request",
                json={
                    "request_type": "query",
                    "user_id": "user-1",
                },
            )

        assert resp.status_code == 500
        body = resp.json()
        assert body["success"] is False
        assert body["error_code"] == "INTERNAL_ERROR"
        assert body["error"] == "Internal server error"


class TestAuditLogging:
    """Audit log is emitted for every request."""

    def test_audit_log_emitted_on_success(self):
        _, client = _make_app()
        test_engine = _build_test_engine()

        with (
            patch("src.service_engine.api._engine", test_engine),
            patch("src.service_engine.api.logger") as mock_logger,
        ):
            client.post(
                "/api/v1/service/request",
                json={"request_type": "query", "user_id": "u1"},
            )

        # Check that info was called with audit pattern
        calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("service_engine_audit" in c for c in calls)

    def test_audit_log_emitted_on_error(self):
        _, client = _make_app()
        failing_engine = RequestRouter()  # no handlers

        with (
            patch("src.service_engine.api._engine", failing_engine),
            patch("src.service_engine.api.logger") as mock_logger,
        ):
            client.post(
                "/api/v1/service/request",
                json={"request_type": "query", "user_id": "u1"},
            )

        calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("service_engine_audit" in c for c in calls)


class TestExtractScopes:
    """_extract_scopes returns correct scope dicts."""

    def test_no_api_key_returns_all_true(self):
        from src.service_engine.api import _extract_scopes

        request = MagicMock()
        request.state = MagicMock(spec=[])  # no api_key attr
        scopes = _extract_scopes(request)
        assert all(scopes.values())

    def test_api_key_with_allowed_types(self):
        from src.service_engine.api import _extract_scopes

        api_key = MagicMock()
        api_key.allowed_request_types = ["query", "chat"]
        request = MagicMock()
        request.state.api_key = api_key

        scopes = _extract_scopes(request)
        assert scopes["query"] is True
        assert scopes["chat"] is True
        assert scopes["decision"] is False
        assert scopes["skill"] is False
