"""
SkillHandler — OpenClaw 技能调用处理器。

校验 skill_id、白名单校验、调用 SkillManager（或可注入的 executor）执行技能。
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from src.service_engine.base import BaseHandler
from src.service_engine.router import ServiceEngineError
from src.service_engine.schemas import (
    ResponseMetadata,
    ServiceRequest,
    ServiceResponse,
)

logger = logging.getLogger(__name__)

_DEFAULT_TENANT = "default-tenant"

# Type alias for the async skill executor callable
SkillExecutor = Callable[[str, dict], dict]


class SkillHandler(BaseHandler):
    """Handler for request_type='skill' — OpenClaw skill execution."""

    def __init__(
        self,
        skill_executor: Optional[SkillExecutor] = None,
    ) -> None:
        self._skill_executor = skill_executor or _default_executor

    # -- validate ------------------------------------------------------------

    async def validate(self, request: ServiceRequest) -> None:
        """Guard: skill_id must be provided and non-empty."""
        if not request.skill_id:
            raise ServiceEngineError(
                status_code=400,
                error_code="MISSING_SKILL_ID",
                message="skill_id is required for skill requests",
            )

    # -- whitelist check -----------------------------------------------------

    @staticmethod
    def check_whitelist(skill_id: str, whitelist: list[str]) -> None:
        """Raise 403 if *skill_id* is not in the allowed whitelist.

        An empty whitelist means all skills are allowed.
        """
        if not whitelist:
            return
        if skill_id not in whitelist:
            raise ServiceEngineError(
                status_code=403,
                error_code="SKILL_NOT_ALLOWED",
                message=f"Skill '{skill_id}' is not in the allowed whitelist",
                details={
                    "skill_id": skill_id,
                    "allowed_skills": whitelist,
                },
            )

    # -- build_context -------------------------------------------------------

    async def build_context(self, request: ServiceRequest) -> dict:
        """Extract tenant_id and return context with skill params."""
        tenant_id = _extract_tenant_id(request)
        return {
            "tenant_id": tenant_id,
            "skill_id": request.skill_id,
            "parameters": request.parameters or {},
        }

    # -- execute -------------------------------------------------------------

    async def execute(
        self,
        request: ServiceRequest,
        context: dict,
    ) -> ServiceResponse:
        """Execute skill via the injected executor and return result."""
        start = time.monotonic()
        skill_id = context["skill_id"]
        parameters = context["parameters"]

        try:
            result = await self._skill_executor(skill_id, parameters)
        except SkillNotFoundException as exc:
            raise ServiceEngineError(
                status_code=404,
                error_code="SKILL_NOT_FOUND",
                message=str(exc),
                details={"skill_id": skill_id},
            ) from exc
        except Exception as exc:
            raise ServiceEngineError(
                status_code=500,
                error_code="SKILL_EXECUTION_ERROR",
                message=f"Skill execution failed: {exc}",
                details={"skill_id": skill_id},
            ) from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ServiceResponse(
            success=True,
            request_type="skill",
            data={
                "skill_id": skill_id,
                "success": True,
                "result": result,
                "execution_time_ms": elapsed_ms,
            },
            metadata=ResponseMetadata(
                request_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                processing_time_ms=elapsed_ms,
            ),
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SkillNotFoundException(Exception):
    """Raised when the requested skill does not exist."""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_tenant_id(request: ServiceRequest) -> str:
    """Extract tenant_id from extensions or fall back to default."""
    if request.extensions and "tenant_id" in request.extensions:
        return str(request.extensions["tenant_id"])
    return _DEFAULT_TENANT


async def _default_executor(skill_id: str, parameters: dict) -> dict:
    """Stub executor — in production, this delegates to SkillManager."""
    return {"skill_id": skill_id, "status": "executed", "result": {}}
