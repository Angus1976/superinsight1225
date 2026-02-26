"""
OpenClaw Chat Service - Wraps OpenClawLLMBridge for chat operations.

Provides non-streaming chat, SSE streaming, and gateway status queries.
Handles timeout, connection drops, and gateway unavailable errors.
"""

import json
import logging
import asyncio
from typing import AsyncIterator, Optional

import httpx
from sqlalchemy.orm import Session

from src.ai_integration.openclaw_llm_bridge import OpenClawLLMBridge
from src.ai.llm_schemas import GenerateOptions, LLMResponse
from src.models.ai_integration import AIGateway, AISkill
from src.ai_integration.schemas import SkillInfoResponse, OpenClawStatusResponse

logger = logging.getLogger(__name__)

STREAM_TIMEOUT_SECONDS = 60


class OpenClawUnavailableError(Exception):
    """Raised when OpenClaw gateway is unavailable."""
    pass


class OpenClawChatService:
    """
    Chat service that delegates to OpenClawLLMBridge and OpenClaw Gateway.

    Supports non-streaming chat, SSE streaming, and status queries.
    """

    def __init__(self, bridge: OpenClawLLMBridge, db: Session):
        self.bridge = bridge
        self.db = db

    # ------------------------------------------------------------------
    # Non-streaming chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        gateway_id: str,
        tenant_id: str,
        prompt: str,
        options: GenerateOptions,
        system_prompt: str = "",
        skill_ids: Optional[list[str]] = None,
    ) -> LLMResponse:
        """Send a non-streaming chat request via OpenClawLLMBridge."""
        gateway = self._get_active_gateway(gateway_id, tenant_id)
        if not gateway:
            raise OpenClawUnavailableError(
                f"Gateway {gateway_id} is not available"
            )

        opts = self._build_options_dict(options, skill_ids)

        return await self.bridge.handle_llm_request(
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            prompt=prompt,
            options=opts,
            system_prompt=system_prompt,
        )

    # ------------------------------------------------------------------
    # SSE streaming chat
    # ------------------------------------------------------------------

    async def stream_chat(
        self,
        gateway_id: str,
        tenant_id: str,
        prompt: str,
        options: GenerateOptions,
        system_prompt: str = "",
        skill_ids: Optional[list[str]] = None,
    ) -> AsyncIterator[str]:
        """Yield SSE-formatted JSON chunks from the OpenClaw Gateway."""
        gateway = self._get_active_gateway(gateway_id, tenant_id)
        if not gateway:
            raise OpenClawUnavailableError(
                f"Gateway {gateway_id} is not available"
            )

        chat_url = self._resolve_chat_url(gateway)
        if not chat_url:
            # Fallback: wrap non-streaming response as SSE chunks
            async for chunk in self._fallback_stream(
                gateway_id, tenant_id, prompt, options, system_prompt, skill_ids
            ):
                yield chunk
            return

        try:
            async for chunk in self._call_gateway_as_stream(
                chat_url, prompt, system_prompt
            ):
                yield chunk
        except OpenClawUnavailableError:
            raise
        except asyncio.TimeoutError:
            logger.warning("Stream timeout for gateway %s", gateway_id)
            yield self._sse_chunk(
                error="OpenClaw 网关响应超时", done=True
            )
        except httpx.ConnectError:
            logger.warning("Connection failed for gateway %s", gateway_id)
            yield self._sse_chunk(
                error="OpenClaw 网关连接失败", done=True
            )
        except BaseException as exc:
            # Catch BaseException to handle all exceptions
            logger.error("Stream error for gateway %s: %s (type: %s)", gateway_id, exc, type(exc).__name__)
            error_message = str(exc) if str(exc) else f"Stream error: {type(exc).__name__}"
            yield self._sse_chunk(
                error=f"OpenClaw 网关错误: {error_message}", done=True
            )
            # Re-raise if it's a system exception (SystemExit, KeyboardInterrupt)
            if isinstance(exc, (SystemExit, KeyboardInterrupt)):
                raise

    # ------------------------------------------------------------------
    # Status query
    # ------------------------------------------------------------------

    async def get_status(self, tenant_id: str) -> OpenClawStatusResponse:
        """Return gateway availability and deployed skills for a tenant.

        Never raises — catches all errors internally.
        """
        try:
            return self._query_status(tenant_id)
        except Exception as exc:
            logger.error("Failed to query OpenClaw status: %s", exc)
            return OpenClawStatusResponse(
                available=False, error=f"状态查询失败: {exc}"
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_active_gateway(
        self, gateway_id: str, tenant_id: str
    ) -> Optional[AIGateway]:
        """Return the gateway only if it belongs to the tenant and is active."""
        return (
            self.db.query(AIGateway)
            .filter(
                AIGateway.id == gateway_id,
                AIGateway.tenant_id == tenant_id,
                AIGateway.gateway_type == "openclaw",
                AIGateway.status == "active",
            )
            .first()
        )

    def _query_status(self, tenant_id: str) -> OpenClawStatusResponse:
        """Query DB for the first active openclaw gateway and its deployed skills."""
        gateway = (
            self.db.query(AIGateway)
            .filter(
                AIGateway.tenant_id == tenant_id,
                AIGateway.gateway_type == "openclaw",
                AIGateway.status == "active",
            )
            .first()
        )

        if not gateway:
            return OpenClawStatusResponse(
                available=False, error="无可用的 OpenClaw 网关"
            )

        skills = (
            self.db.query(AISkill)
            .filter(
                AISkill.gateway_id == gateway.id,
                AISkill.status == "deployed",
            )
            .all()
        )

        return OpenClawStatusResponse(
            available=True,
            gateway_id=str(gateway.id),
            gateway_name=gateway.name,
            skills=[
                SkillInfoResponse(
                    id=str(s.id),
                    name=s.name,
                    version=s.version,
                    status=s.status,
                    description=(s.configuration or {}).get("description"),
                )
                for s in skills
            ],
        )

    # --- Streaming internals ---

    def _resolve_chat_url(self, gateway: AIGateway) -> Optional[str]:
        """Extract the chat endpoint URL from gateway configuration."""
        config = gateway.configuration or {}
        network = config.get("network_settings", {})
        base_url = network.get("base_url", "")
        if not base_url:
            return None
        return f"{base_url.rstrip('/')}/api/chat"

    async def _call_gateway_as_stream(
        self, url: str, prompt: str, system_prompt: str
    ) -> AsyncIterator[str]:
        """Call Gateway /api/chat and wrap the response as SSE chunks."""
        payload = {"message": prompt}
        if system_prompt:
            payload["system_prompt"] = system_prompt

        async with httpx.AsyncClient(timeout=STREAM_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise OpenClawUnavailableError(
                    f"Gateway returned status {resp.status_code}"
                )
            data = resp.json()

        if not data.get("success", False):
            error = data.get("error", "Gateway request failed")
            yield self._sse_chunk(error=error, done=True)
            return

        reply = data.get("reply", "")
        yield self._sse_chunk(content=reply, done=False)
        yield self._sse_chunk(content="", done=True)


    async def _fallback_stream(
        self,
        gateway_id: str,
        tenant_id: str,
        prompt: str,
        options: GenerateOptions,
        system_prompt: str,
        skill_ids: Optional[list[str]],
    ) -> AsyncIterator[str]:
        """Wrap a non-streaming response as SSE chunks (fallback)."""
        opts = self._build_options_dict(options, skill_ids)
        response = await self.bridge.handle_llm_request(
            gateway_id=gateway_id,
            tenant_id=tenant_id,
            prompt=prompt,
            options=opts,
            system_prompt=system_prompt,
        )
        yield self._sse_chunk(content=response.content, done=False)
        yield self._sse_chunk(content="", done=True)

    # --- Payload / formatting helpers ---

    @staticmethod
    def _build_options_dict(
        options: GenerateOptions, skill_ids: Optional[list[str]] = None
    ) -> dict:
        """Convert GenerateOptions + skill_ids into a plain dict for the bridge."""
        opts = options.model_dump(exclude_none=True)
        if skill_ids:
            opts["skill_ids"] = skill_ids
        return opts

    @staticmethod
    def _sse_chunk(
        content: str = "",
        done: bool = False,
        error: Optional[str] = None,
    ) -> str:
        """Format a single SSE data line."""
        payload: dict = {"content": content, "done": done}
        if error:
            payload["error"] = error
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
