"""
ContextBuilder — 组装 LLM 上下文。

将平台治理数据（DataProvider）、客户 business_context 和 UserMemory
合并为统一的上下文字典，供 ChatHandler / DecisionHandler 使用。
"""

import logging
from typing import Optional

from src.service_engine.providers import BaseDataProvider, QueryParams
from src.service_engine.schemas import ServiceRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 默认系统提示词
# ---------------------------------------------------------------------------
DEFAULT_SYSTEM_PROMPT = (
    "You are an intelligent data analysis assistant for the SuperInsight platform. "
    "Use the provided governance data and business context to deliver accurate, "
    "actionable insights."
)


# ---------------------------------------------------------------------------
# ContextBuilder
# ---------------------------------------------------------------------------
class ContextBuilder:
    """Assembles governance data + business_context + UserMemory into LLM context."""

    def __init__(
        self,
        data_providers: Optional[dict[str, BaseDataProvider]] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self._data_providers = data_providers or {}
        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    # -- public API ----------------------------------------------------------

    async def build(
        self,
        request: ServiceRequest,
        memory_entries: list[dict],
    ) -> dict:
        """Build the full LLM context dict from *request* and *memory_entries*."""
        tenant_id = self._extract_tenant_id(request)
        governance_data = await self._fetch_governance_data(tenant_id)
        business_context = self._extract_business_context(request)
        memory = self._resolve_memory(request, memory_entries)

        return {
            "system_prompt": self._system_prompt,
            "governance_data": governance_data,
            "business_context": business_context,
            "memory": memory,
            "user_id": request.user_id,
            "tenant_id": tenant_id,
        }

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _extract_tenant_id(request: ServiceRequest) -> str:
        """Extract tenant_id from extensions with fallback to 'default-tenant'."""
        if not request.extensions:
            return "default-tenant"
        return request.extensions.get("tenant_id", "default-tenant")

    async def _fetch_governance_data(self, tenant_id: str) -> dict:
        """Query every registered DataProvider and return aggregated results."""
        if not self._data_providers:
            return {}

        result: dict[str, list[dict]] = {}
        for data_type, provider in self._data_providers.items():
            try:
                params = QueryParams(tenant_id=tenant_id, page=1, page_size=10)
                paginated = await provider.query(params)
                result[data_type] = paginated.items
            except Exception:
                logger.warning(
                    "Failed to fetch governance data for %s", data_type, exc_info=True,
                )
                result[data_type] = []
        return result

    @staticmethod
    def _extract_business_context(request: ServiceRequest) -> dict:
        """Return business_context from the request, defaulting to empty dict."""
        if request.business_context is None:
            return {}
        return request.business_context

    @staticmethod
    def _resolve_memory(
        request: ServiceRequest,
        memory_entries: list[dict],
    ) -> list[dict]:
        """Return memory entries only when include_memory is True."""
        if not request.include_memory:
            return []
        return memory_entries
