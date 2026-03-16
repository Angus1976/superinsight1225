"""
DecisionHandler — 辅助决策处理器。

校验 question、组装 LLM 上下文、调用 LLMSwitcher 生成结构化 JSON 决策报告。
支持 LLM 降级处理：当 LLM 返回非结构化内容时，confidence 设为 0。
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

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

_DECISION_SYSTEM_PROMPT_SUFFIX = (
    "\n\nYou MUST respond with a valid JSON object containing exactly these keys:\n"
    '- "summary": a brief summary of the decision analysis\n'
    '- "analysis": detailed analysis text\n'
    '- "recommendations": array of objects, each with "action", "reason", "priority" '
    '(one of "high", "medium", "low")\n'
    '- "confidence": a float between 0 and 1 indicating confidence level\n'
    "Respond ONLY with the JSON object, no extra text."
)


class DecisionHandler(BaseHandler):
    """Handler for request_type='decision' — structured decision analysis via LLM."""

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
        """Guard: question must be provided and non-empty."""
        if not request.question:
            raise ServiceEngineError(
                status_code=400,
                error_code="MISSING_QUESTION",
                message="question is required for decision requests",
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

    # -- execute -------------------------------------------------------------

    async def execute(
        self,
        request: ServiceRequest,
        context: dict,
    ) -> ServiceResponse:
        """Call LLM for structured decision analysis and return result."""
        start = time.monotonic()
        prompt = _build_decision_prompt(context, request)
        system_prompt = context["system_prompt"] + _DECISION_SYSTEM_PROMPT_SUFFIX

        try:
            llm_response = await asyncio.wait_for(
                self._llm.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
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
                message="Decision request timed out after 60 seconds",
            )

        decision_data = _parse_decision_response(llm_response.content)

        # Append memory if enabled
        await self._append_memory(request, context, decision_data)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ServiceResponse(
            success=True,
            request_type="decision",
            data=decision_data,
            metadata=ResponseMetadata(
                request_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                processing_time_ms=elapsed_ms,
            ),
        )

    # -- private helpers -----------------------------------------------------

    async def _append_memory(
        self,
        request: ServiceRequest,
        context: dict,
        decision_data: dict,
    ) -> None:
        """Persist interaction to memory if enabled."""
        if not request.include_memory or not self._memory_manager:
            return
        tenant_id = context.get("tenant_id", _DEFAULT_TENANT)
        await self._memory_manager.append_memory(
            user_id=request.user_id,
            tenant_id=tenant_id,
            content={
                "question": request.question,
                "decision": decision_data,
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


def _build_decision_prompt(context: dict, request: ServiceRequest) -> str:
    """Assemble the LLM prompt from context and decision question."""
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

    # Context data from request
    if request.context_data:
        parts.append(f"[Context Data]\n{json.dumps(request.context_data, ensure_ascii=False, default=str)}")

    # Decision question
    parts.append(f"[Decision Question]\n{request.question}")

    return "\n\n".join(parts)


_REQUIRED_KEYS = {"summary", "analysis", "recommendations", "confidence"}


def _parse_decision_response(raw: str) -> dict:
    """Parse LLM output as structured decision JSON.

    If parsing fails or required keys are missing, degrade gracefully:
    confidence=0 and raw text wrapped in summary/analysis.
    """
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and _REQUIRED_KEYS.issubset(parsed):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    # Degradation: wrap raw text with confidence=0
    return {
        "summary": raw[:500] if raw else "",
        "analysis": raw or "",
        "recommendations": [],
        "confidence": 0,
    }
