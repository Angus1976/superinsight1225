"""Unit tests for ContextBuilder."""

import pytest

from src.service_engine.context import ContextBuilder, DEFAULT_SYSTEM_PROMPT
from src.service_engine.providers import BaseDataProvider, PaginatedResult, QueryParams
from src.service_engine.schemas import ServiceRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(**overrides) -> ServiceRequest:
    """Build a minimal ServiceRequest with sensible defaults."""
    defaults = {"request_type": "chat", "user_id": "u-1"}
    defaults.update(overrides)
    return ServiceRequest(**defaults)


class FakeProvider(BaseDataProvider):
    """In-memory provider that returns pre-set items."""

    def __init__(self, items: list[dict]) -> None:
        self._items = items

    async def query(self, params: QueryParams) -> PaginatedResult:
        return PaginatedResult(
            items=self._items,
            total=len(self._items),
            page=params.page,
            page_size=params.page_size,
            total_pages=1,
        )


class FailingProvider(BaseDataProvider):
    """Provider that always raises."""

    async def query(self, params: QueryParams) -> PaginatedResult:
        raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# Tests — tenant_id extraction
# ---------------------------------------------------------------------------

class TestExtractTenantId:
    @pytest.mark.asyncio
    async def test_from_extensions(self):
        req = _make_request(extensions={"tenant_id": "t-42"})
        ctx = await ContextBuilder().build(req, [])
        assert ctx["tenant_id"] == "t-42"

    @pytest.mark.asyncio
    async def test_fallback_when_extensions_none(self):
        req = _make_request(extensions=None)
        ctx = await ContextBuilder().build(req, [])
        assert ctx["tenant_id"] == "default-tenant"

    @pytest.mark.asyncio
    async def test_fallback_when_key_missing(self):
        req = _make_request(extensions={"other": "val"})
        ctx = await ContextBuilder().build(req, [])
        assert ctx["tenant_id"] == "default-tenant"


# ---------------------------------------------------------------------------
# Tests — governance data
# ---------------------------------------------------------------------------

class TestGovernanceData:
    @pytest.mark.asyncio
    async def test_empty_when_no_providers(self):
        ctx = await ContextBuilder().build(_make_request(), [])
        assert ctx["governance_data"] == {}

    @pytest.mark.asyncio
    async def test_aggregates_provider_results(self):
        providers = {
            "annotations": FakeProvider([{"id": "a1"}]),
            "samples": FakeProvider([{"id": "s1"}, {"id": "s2"}]),
        }
        ctx = await ContextBuilder(data_providers=providers).build(_make_request(), [])
        assert ctx["governance_data"]["annotations"] == [{"id": "a1"}]
        assert len(ctx["governance_data"]["samples"]) == 2

    @pytest.mark.asyncio
    async def test_failing_provider_returns_empty_list(self):
        providers = {"bad": FailingProvider()}
        ctx = await ContextBuilder(data_providers=providers).build(_make_request(), [])
        assert ctx["governance_data"]["bad"] == []


# ---------------------------------------------------------------------------
# Tests — business_context
# ---------------------------------------------------------------------------

class TestBusinessContext:
    @pytest.mark.asyncio
    async def test_none_becomes_empty_dict(self):
        ctx = await ContextBuilder().build(_make_request(business_context=None), [])
        assert ctx["business_context"] == {}

    @pytest.mark.asyncio
    async def test_passed_through(self):
        bc = {"user_profile": {"age": 30}}
        ctx = await ContextBuilder().build(_make_request(business_context=bc), [])
        assert ctx["business_context"] == bc


# ---------------------------------------------------------------------------
# Tests — memory
# ---------------------------------------------------------------------------

class TestMemory:
    @pytest.mark.asyncio
    async def test_included_when_flag_true(self):
        entries = [{"role": "user", "content": "hi"}]
        ctx = await ContextBuilder().build(
            _make_request(include_memory=True), entries,
        )
        assert ctx["memory"] == entries

    @pytest.mark.asyncio
    async def test_excluded_when_flag_false(self):
        entries = [{"role": "user", "content": "hi"}]
        ctx = await ContextBuilder().build(
            _make_request(include_memory=False), entries,
        )
        assert ctx["memory"] == []


# ---------------------------------------------------------------------------
# Tests — full context shape
# ---------------------------------------------------------------------------

class TestFullContext:
    @pytest.mark.asyncio
    async def test_all_keys_present(self):
        ctx = await ContextBuilder().build(_make_request(), [])
        assert set(ctx.keys()) == {
            "system_prompt", "governance_data", "business_context",
            "memory", "user_id", "tenant_id",
        }

    @pytest.mark.asyncio
    async def test_user_id_echoed(self):
        ctx = await ContextBuilder().build(_make_request(user_id="u-99"), [])
        assert ctx["user_id"] == "u-99"

    @pytest.mark.asyncio
    async def test_default_system_prompt(self):
        ctx = await ContextBuilder().build(_make_request(), [])
        assert ctx["system_prompt"] == DEFAULT_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_custom_system_prompt(self):
        builder = ContextBuilder(system_prompt="custom")
        ctx = await builder.build(_make_request(), [])
        assert ctx["system_prompt"] == "custom"
