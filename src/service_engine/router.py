"""
RequestRouter — Handler 注册表、动态启用/禁用、scope 权限校验。

将 request_type 映射到对应的 BaseHandler 实例，
执行完整的请求处理管线：disabled 检查 → scope 校验 → validate → build_context → execute。
"""

import logging
from typing import Optional

from src.service_engine.base import BaseHandler
from src.service_engine.schemas import ServiceRequest, ServiceResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ServiceEngineError — 统一异常
# ---------------------------------------------------------------------------
class ServiceEngineError(Exception):
    """Unified exception for the service engine layer."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# RequestRouter
# ---------------------------------------------------------------------------
class RequestRouter:
    """Registry-based router that dispatches requests to handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, BaseHandler] = {}
        self._disabled_types: set[str] = set()

    # -- registration --------------------------------------------------------

    def register(self, request_type: str, handler: BaseHandler) -> None:
        """Register a handler for *request_type*."""
        self._handlers[request_type] = handler
        logger.info("Registered handler for request_type=%s", request_type)

    # -- enable / disable ----------------------------------------------------

    def enable(self, request_type: str) -> None:
        """Enable a previously disabled *request_type*."""
        self._disabled_types.discard(request_type)
        logger.info("Enabled request_type=%s", request_type)

    def disable(self, request_type: str) -> None:
        """Disable *request_type* without removing its handler."""
        self._disabled_types.add(request_type)
        logger.info("Disabled request_type=%s", request_type)

    # -- scope checking ------------------------------------------------------

    def check_scope(self, api_key_scopes: dict, request_type: str) -> None:
        """Raise *ServiceEngineError(403)* when the API key lacks the scope."""
        if not api_key_scopes.get(request_type, False):
            available = [k for k, v in api_key_scopes.items() if v]
            raise ServiceEngineError(
                status_code=403,
                error_code="INSUFFICIENT_SCOPE",
                message=(
                    f"API key does not have permission "
                    f"to access {request_type}"
                ),
                details={
                    "required_scope": request_type,
                    "available_scopes": available,
                },
            )

    # -- routing pipeline ----------------------------------------------------

    async def route(
        self,
        request: ServiceRequest,
        api_key_scopes: dict,
        *,
        skill_whitelist: Optional[list] = None,
        user_roles: Optional[list] = None,
    ) -> ServiceResponse:
        """Full pipeline: disabled → scope → whitelist → validate → build_context → execute."""
        rtype = request.request_type

        self._ensure_registered(rtype)
        self._ensure_enabled(rtype)
        self.check_scope(api_key_scopes, rtype)

        # Skill whitelist check (admin bypasses)
        if rtype == "skill" and request.skill_id:
            self._check_skill_whitelist(
                request.skill_id,
                skill_whitelist or [],
                user_roles or [],
            )

        handler = self._handlers[rtype]
        await handler.validate(request)
        context = await handler.build_context(request)
        return await handler.execute(request, context)

    # -- skill whitelist guard -----------------------------------------------

    def _check_skill_whitelist(
        self,
        skill_id: str,
        whitelist: list[str],
        user_roles: list[str],
    ) -> None:
        """Check skill whitelist from API key. Empty whitelist = all allowed."""
        from src.service_engine.handlers.skill import SkillHandler
        SkillHandler.check_whitelist(skill_id, whitelist)

    # -- private guards ------------------------------------------------------

    def _ensure_registered(self, request_type: str) -> None:
        """Guard: request_type must be registered."""
        if request_type not in self._handlers:
            raise ServiceEngineError(
                status_code=400,
                error_code="INVALID_REQUEST_TYPE",
                message=f"Unsupported request_type: {request_type}",
                details={
                    "supported_types": list(self._handlers.keys()),
                },
            )

    def _ensure_enabled(self, request_type: str) -> None:
        """Guard: request_type must not be disabled."""
        if request_type in self._disabled_types:
            raise ServiceEngineError(
                status_code=403,
                error_code="REQUEST_TYPE_DISABLED",
                message=f"request_type '{request_type}' is currently disabled",
            )
