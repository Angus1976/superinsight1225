"""
ChatHandler — 对话式分析处理器。

校验 messages、组装 LLM 上下文、调用 LLMSwitcher 生成响应。
支持非流式（execute）和 SSE 流式（stream_execute）两种模式。
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from src.ai.llm_schemas import LLMException
from src.service_engine.base import BaseHandler
from src.service_engine.context import ContextBuilder
from src.service_engine.memory import MemoryManager
from src.service_engine.router import ServiceEngineError
from src.service_engine.schemas import (
    ResponseMetadata,
    ServiceRequest,
    ServiceResponse,
)

logger = logging.getLogger(__name__)

_DEFAULT_TENANT = "default-tenant"
_TIMEOUT_SECONDS = 60


class ChatHandler(BaseHandler):
    """Handler for request_type='chat' — conversational analysis via LLM."""

    def __init__(
        self,
        llm_switcher=None,
        context_builder: Optional[ContextBuilder] = None,
        memory_manager: Optional[MemoryManager] = None,
    ) -> None:
        self._llm = llm_switcher
        self._context_builder = context_builder or ContextBuilder()
        self._memory_manager = memory_manager

    # -- validate ------------------------------------------------------------

    async def validate(self, request: ServiceRequest) -> None:
        """Guard: messages must be provided and non-empty."""
        if not request.messages:
            raise ServiceEngineError(
                status_code=400,
                error_code="MISSING_MESSAGES",
                message="messages is required for chat requests",
            )

    # -- build_context -------------------------------------------------------

    async def build_context(self, request: ServiceRequest) -> dict:
        """Load memories (if enabled) and build LLM context."""
        tenant_id = _extract_tenant_id(request)
        memories: list[dict] = []
        if request.include_memory and self._memory_manager:
            memories = await self._memory_manager.load_memories(
                request.user_id, tenant_id,
            )
        return await self._context_builder.build(request, memories)

    # -- execute (non-streaming) ---------------------------------------------

    async def execute(
        self,
        request: ServiceRequest,
        context: dict,
    ) -> ServiceResponse:
        """Non-streaming response: call LLM and return complete result."""
        # Workflow routing: delegate when workflow_id is present
        if request.workflow_id:
            return await self._execute_via_workflow(request, context)

        start = time.monotonic()
        prompt = _build_prompt(context, request.messages)

        try:
            llm_response = await asyncio.wait_for(
                self._llm.generate(
                    prompt=prompt,
                    system_prompt=context["system_prompt"],
                ),
                timeout=_TIMEOUT_SECONDS,
            )
        except LLMException as exc:
            raise ServiceEngineError(
                status_code=503,
                error_code="LLM_UNAVAILABLE",
                message=f"LLM service unavailable: {exc}",
            ) from exc
        except asyncio.TimeoutError:
            raise ServiceEngineError(
                status_code=504,
                error_code="REQUEST_TIMEOUT",
                message="Chat request timed out after 60 seconds",
            )

        # Append memory if enabled
        await self._append_memory(request, context, llm_response.content)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ServiceResponse(
            success=True,
            request_type="chat",
            data={"content": llm_response.content},
            metadata=ResponseMetadata(
                request_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                processing_time_ms=elapsed_ms,
            ),
        )

    # -- stream_execute (SSE) ------------------------------------------------

    async def stream_execute(
        self,
        request: ServiceRequest,
        context: dict,
    ) -> AsyncIterator[dict]:
        """Yield SSE-formatted dicts for streaming responses.

        Intermediate: {"content": "...", "done": false}
        Final:        {"content": "", "done": true}
        Error:        {"error": "...", "done": true}
        """
        # Workflow routing: delegate when workflow_id is present
        if request.workflow_id:
            async for chunk in self._stream_via_workflow(request, context):
                yield chunk
            return

        prompt = _build_prompt(context, request.messages)
        collected_content = ""

        try:
            async for chunk in self._stream_with_timeout(
                prompt, context["system_prompt"],
            ):
                collected_content += chunk
                yield {"content": chunk, "done": False}
            yield {"content": "", "done": True}
        except LLMException as exc:
            raise ServiceEngineError(
                status_code=503,
                error_code="LLM_UNAVAILABLE",
                message=f"LLM service unavailable: {exc}",
            ) from exc
        except asyncio.TimeoutError:
            raise ServiceEngineError(
                status_code=504,
                error_code="REQUEST_TIMEOUT",
                message="Chat request timed out after 60 seconds",
            )

        # Append memory after successful stream
        await self._append_memory(request, context, collected_content)

    # -- workflow delegation --------------------------------------------------

    async def _execute_via_workflow(
        self, request: ServiceRequest, context: dict,
    ) -> ServiceResponse:
        """Delegate to WorkflowService for non-streaming workflow execution."""
        from src.database.connection import get_db_session
        from src.ai.workflow_service import WorkflowService

        skill_whitelist = context.get("_skill_whitelist", [])
        api_overrides = _build_api_overrides(skill_whitelist)
        user = _build_mock_user(request)
        prompt = _build_prompt(context, request.messages)

        start = time.monotonic()
        with next(get_db_session()) as db:
            service = WorkflowService(db)
            result = await service.execute_workflow(
                workflow_id=request.workflow_id,
                user=user,
                prompt=prompt,
                api_overrides=api_overrides,
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ServiceResponse(
            success=True,
            request_type="chat",
            data={"content": result.get("content", ""), **_workflow_extras(result)},
            metadata=ResponseMetadata(
                request_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                processing_time_ms=elapsed_ms,
            ),
        )

    async def _stream_via_workflow(
        self, request: ServiceRequest, context: dict,
    ) -> AsyncIterator[dict]:
        """Delegate to WorkflowService for streaming workflow execution."""
        from src.database.connection import get_db_session
        from src.ai.workflow_service import WorkflowService

        skill_whitelist = context.get("_skill_whitelist", [])
        api_overrides = _build_api_overrides(skill_whitelist)
        user = _build_mock_user(request)
        prompt = _build_prompt(context, request.messages)

        with next(get_db_session()) as db:
            service = WorkflowService(db)
            async for chunk in service.stream_execute_workflow(
                workflow_id=request.workflow_id,
                user=user,
                prompt=prompt,
                api_overrides=api_overrides,
            ):
                yield {"content": chunk, "done": False}
        yield {"content": "", "done": True}

    # -- private helpers -----------------------------------------------------

    async def _stream_with_timeout(
        self, prompt: str, system_prompt: str,
    ) -> AsyncIterator[str]:
        """Wrap stream_generate with a 60-second deadline."""
        deadline = asyncio.get_event_loop().time() + _TIMEOUT_SECONDS
        ait = self._llm.stream_generate(
            prompt=prompt, system_prompt=system_prompt,
        ).__aiter__()
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            try:
                chunk = await asyncio.wait_for(
                    ait.__anext__(), timeout=remaining,
                )
                yield chunk
            except StopAsyncIteration:
                break

    async def _append_memory(
        self,
        request: ServiceRequest,
        context: dict,
        response_content: str,
    ) -> None:
        """Persist interaction to memory if enabled."""
        if not request.include_memory or not self._memory_manager:
            return
        tenant_id = context.get("tenant_id", _DEFAULT_TENANT)
        await self._memory_manager.append_memory(
            user_id=request.user_id,
            tenant_id=tenant_id,
            content={
                "messages": request.messages,
                "response": response_content,
            },
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _extract_tenant_id(request: ServiceRequest) -> str:
    """Extract tenant_id from extensions or fall back to default."""
    if request.extensions and "tenant_id" in request.extensions:
        return str(request.extensions["tenant_id"])
    return _DEFAULT_TENANT


class _MockUser:
    """Lightweight user object for WorkflowService when called from Service Engine."""

    __slots__ = ("user_id", "tenant_id", "role")

    def __init__(self, user_id: str, tenant_id: str, role: str) -> None:
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


def _build_mock_user(request: ServiceRequest) -> "_MockUser":
    """Build a mock user from ServiceRequest fields."""
    tenant_id = _extract_tenant_id(request)
    role = "api"  # External API channel — role resolved by WorkflowService
    if request.extensions and "role" in request.extensions:
        role = str(request.extensions["role"])
    return _MockUser(user_id=request.user_id, tenant_id=tenant_id, role=role)


def _build_api_overrides(skill_whitelist: list) -> Optional[dict]:
    """Build api_overrides dict from API key's skill_whitelist."""
    if not skill_whitelist:
        return None
    return {"skill_ids": list(skill_whitelist)}


def _workflow_extras(result: dict) -> dict:
    """Extract optional workflow metadata from execution result."""
    extras: dict = {}
    if result.get("workflow_id"):
        extras["workflow_id"] = result["workflow_id"]
    if result.get("output_modes"):
        extras["output_modes"] = result["output_modes"]
    if result.get("failed_skills"):
        extras["failed_skills"] = result["failed_skills"]
    return extras


def _build_prompt(context: dict, messages: list) -> str:
    """Assemble the LLM prompt from context and conversation messages."""
    parts: list[str] = []

    # Governance data summary
    gov = context.get("governance_data", {})
    if gov:
        parts.append(f"[Platform Data]\n{json.dumps(gov, ensure_ascii=False, default=str)}")

    # Business context
    biz = context.get("business_context", {})
    if biz:
        parts.append(f"[Business Context]\n{json.dumps(biz, ensure_ascii=False, default=str)}")

    # Memory
    mem = context.get("memory", [])
    if mem:
        parts.append(f"[Conversation History]\n{json.dumps(mem, ensure_ascii=False, default=str)}")

    # Current messages
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"{role}: {content}")

    return "\n\n".join(parts)
