"""
Unit tests for QueryHandler — data_type validation, context building,
provider dispatch, and response format.
"""

import pytest

from src.service_engine.handlers.query import QueryHandler, _DEFAULT_TENANT
from typing import Dict, List, Optional

from src.service_engine.providers import (
    BaseDataProvider,
    PaginatedResult,
    QueryParams,
    VALID_DATA_TYPES,
)
from src.service_engine.router import ServiceEngineError
from src.service_engine.schemas import ServiceRequest


# ---------------------------------------------------------------------------
# Stub provider
# ---------------------------------------------------------------------------
class StubProvider(BaseDataProvider):
    """Returns a canned PaginatedResult and records the params it received."""

    def __init__(self, items: Optional[List[dict]] = None):
        self.last_params: Optional[QueryParams] = None
        self._items = items or []

    async def query(self, params: QueryParams) -> PaginatedResult:
        self.last_params = params
        return PaginatedResult(
            items=self._items,
            total=len(self._items),
            page=params.page,
            page_size=params.page_size,
            total_pages=1 if self._items else 0,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_request(**overrides) -> ServiceRequest:
    defaults = {"request_type": "query", "user_id": "u1", "data_type": "annotations"}
    defaults.update(overrides)
    return ServiceRequest(**defaults)


def _stub_providers(**extra) -> Dict[str, BaseDataProvider]:
    providers = {dt: StubProvider() for dt in VALID_DATA_TYPES}
    providers.update(extra)
    return providers


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class TestValidate:
    @pytest.mark.asyncio
    async def test_missing_data_type_raises_400(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request(data_type=None)
        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.validate(req)
        err = exc_info.value
        assert err.status_code == 400
        assert err.error_code == "INVALID_DATA_TYPE"
        assert "supported_types" in err.details

    @pytest.mark.asyncio
    async def test_invalid_data_type_raises_400(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request(data_type="nonexistent")
        with pytest.raises(ServiceEngineError) as exc_info:
            await handler.validate(req)
        err = exc_info.value
        assert err.status_code == 400
        assert err.error_code == "INVALID_DATA_TYPE"
        assert list(VALID_DATA_TYPES) == err.details["supported_types"]

    @pytest.mark.asyncio
    async def test_valid_data_types_pass(self):
        handler = QueryHandler(providers=_stub_providers())
        for dt in VALID_DATA_TYPES:
            req = _make_request(data_type=dt)
            await handler.validate(req)  # should not raise


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------
class TestBuildContext:
    @pytest.mark.asyncio
    async def test_default_pagination(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request()
        ctx = await handler.build_context(req)
        params = ctx["query_params"]
        assert params.page == 1
        assert params.page_size == 50

    @pytest.mark.asyncio
    async def test_custom_pagination(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request(page=3, page_size=10)
        ctx = await handler.build_context(req)
        params = ctx["query_params"]
        assert params.page == 3
        assert params.page_size == 10

    @pytest.mark.asyncio
    async def test_sort_by_forwarded(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request(sort_by="-created_at")
        ctx = await handler.build_context(req)
        assert ctx["query_params"].sort_by == "-created_at"

    @pytest.mark.asyncio
    async def test_fields_forwarded(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request(fields="id,name")
        ctx = await handler.build_context(req)
        assert ctx["query_params"].fields == "id,name"

    @pytest.mark.asyncio
    async def test_filters_forwarded(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request(filters={"status": "active"})
        ctx = await handler.build_context(req)
        assert ctx["query_params"].filters == {"status": "active"}

    @pytest.mark.asyncio
    async def test_tenant_from_extensions(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request(extensions={"tenant_id": "t-123"})
        ctx = await handler.build_context(req)
        assert ctx["query_params"].tenant_id == "t-123"

    @pytest.mark.asyncio
    async def test_tenant_default_when_no_extensions(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request()
        ctx = await handler.build_context(req)
        assert ctx["query_params"].tenant_id == _DEFAULT_TENANT


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------
class TestExecute:
    @pytest.mark.asyncio
    async def test_returns_paginated_response(self):
        items = [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}]
        stub = StubProvider(items=items)
        providers = _stub_providers(annotations=stub)
        handler = QueryHandler(providers=providers)

        req = _make_request(data_type="annotations")
        ctx = await handler.build_context(req)
        resp = await handler.execute(req, ctx)

        assert resp.success is True
        assert resp.request_type == "query"
        assert resp.data["items"] == items
        assert resp.data["pagination"]["total"] == 2
        assert resp.data["pagination"]["page"] == 1
        assert resp.data["pagination"]["page_size"] == 50

    @pytest.mark.asyncio
    async def test_metadata_fields_present(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request()
        ctx = await handler.build_context(req)
        resp = await handler.execute(req, ctx)

        assert resp.metadata.request_id  # non-empty UUID string
        assert resp.metadata.timestamp   # non-empty ISO timestamp
        assert resp.metadata.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_provider_receives_correct_params(self):
        stub = StubProvider()
        providers = _stub_providers(annotations=stub)
        handler = QueryHandler(providers=providers)

        req = _make_request(
            data_type="annotations",
            page=2,
            page_size=25,
            sort_by="name",
            fields="id,name",
            filters={"status": "done"},
            extensions={"tenant_id": "tenant-x"},
        )
        ctx = await handler.build_context(req)
        await handler.execute(req, ctx)

        p = stub.last_params
        assert p.tenant_id == "tenant-x"
        assert p.page == 2
        assert p.page_size == 25
        assert p.sort_by == "name"
        assert p.fields == "id,name"
        assert p.filters == {"status": "done"}

    @pytest.mark.asyncio
    async def test_empty_result(self):
        handler = QueryHandler(providers=_stub_providers())
        req = _make_request(data_type="tasks")
        ctx = await handler.build_context(req)
        resp = await handler.execute(req, ctx)

        assert resp.data["items"] == []
        assert resp.data["pagination"]["total"] == 0
