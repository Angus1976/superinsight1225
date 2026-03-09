"""
Middleware / exception handler that converts ConcurrentModificationError
into HTTP 409 Conflict responses.

Validates: Requirements 22.2, 22.3
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.services.concurrent_manager import ConcurrentModificationError

logger = logging.getLogger(__name__)


async def concurrent_modification_handler(
    request: Request,
    exc: ConcurrentModificationError,
) -> JSONResponse:
    """Return a 409 Conflict response with version conflict details."""
    logger.warning(
        "409 Conflict on %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=409,
        content=exc.to_conflict_detail(),
    )


def register_concurrent_error_handler(app: FastAPI) -> None:
    """Register the ConcurrentModificationError handler on *app*."""
    app.add_exception_handler(
        ConcurrentModificationError,
        concurrent_modification_handler,  # type: ignore[arg-type]
    )
