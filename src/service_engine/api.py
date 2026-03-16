"""
Unified Service Engine API — POST /api/v1/service/request

Ties together RequestRouter, all Handlers, middleware integration,
and global error handling.
"""

import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.service_engine.router import RequestRouter, ServiceEngineError
from src.service_engine.schemas import ServiceRequest, ErrorResponse
from src.service_engine.handlers.query import QueryHandler
from src.service_engine.handlers.chat import ChatHandler
from src.service_engine.handlers.decision import DecisionHandler
from src.service_engine.handlers.skill import SkillHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/service", tags=["Service Engine"])

# -- Initialize engine -------------------------------------------------------


def _create_engine() -> RequestRouter:
    """Create and configure the RequestRouter with all handlers."""
    engine = RequestRouter()
    engine.register("query", QueryHandler())
    engine.register("chat", ChatHandler())
    engine.register("decision", DecisionHandler())
    engine.register("skill", SkillHandler())
    return engine


_engine = _create_engine()

# -- Route -------------------------------------------------------------------


@router.post("/request")
async def handle_service_request(request: Request, body: ServiceRequest):
    """Unified service engine endpoint.

    Validates scopes via APIKeyAuthMiddleware state, delegates to
    RequestRouter, and converts all exceptions to ErrorResponse JSON.
    """
    start = time.monotonic()
    api_key_scopes = _extract_scopes(request)

    try:
        response = await _engine.route(body, api_key_scopes)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        _audit_log(body, 200, elapsed_ms)
        return response.model_dump()

    except ServiceEngineError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        _audit_log(body, exc.status_code, elapsed_ms)
        return _error_response(exc)

    except ValidationError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        _audit_log(body, 400, elapsed_ms)
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=str(exc),
                error_code="VALIDATION_ERROR",
            ).model_dump(),
        )

    except Exception:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        _audit_log(body, 500, elapsed_ms)
        logger.exception("Unexpected error in service engine")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error",
                error_code="INTERNAL_ERROR",
            ).model_dump(),
        )


# -- Helpers -----------------------------------------------------------------


def _extract_scopes(request: Request) -> dict:
    """Extract API key scopes from request state set by APIKeyAuthMiddleware."""
    api_key = getattr(request.state, "api_key", None)
    if not api_key:
        return {"query": True, "chat": True, "decision": True, "skill": True}

    allowed = getattr(api_key, "allowed_request_types", None)
    if not allowed:
        return {"query": True, "chat": True, "decision": True, "skill": True}

    return {rt: rt in allowed for rt in ["query", "chat", "decision", "skill"]}


def _error_response(exc: ServiceEngineError) -> JSONResponse:
    """Convert ServiceEngineError to JSONResponse with ErrorResponse body."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.message,
            error_code=exc.error_code,
            details=exc.details,
        ).model_dump(),
    )


def _audit_log(body: ServiceRequest, status_code: int, elapsed_ms: int) -> None:
    """Log audit entry for every request (Req 1.10)."""
    logger.info(
        "service_engine_audit request_type=%s user_id=%s status=%d time_ms=%d",
        body.request_type,
        body.user_id,
        status_code,
        elapsed_ms,
    )
