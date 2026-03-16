"""
Property-based tests for QueryHandler.

Tests tenant isolation, pagination defaults, and field filtering correctness
using Hypothesis. Covers Properties 4, 5, and 6 from the design document.
"""

import pytest
from hypothesis import given, settings, strategies as st
from typing import Optional

from src.service_engine.handlers.query import QueryHandler, _DEFAULT_TENANT
from src.service_engine.providers import (
    BaseDataProvider,
    PaginatedResult,
    QueryParams,
    VALID_DATA_TYPES,
)
from src.service_engine.schemas import ServiceRequest
from src.sync.gateway.external_data_router import filter_fields


# ---------------------------------------------------------------------------
# Stub providers
# ---------------------------------------------------------------------------

class RecordingStubProvider(BaseDataProvider):
    """Records the QueryParams it receives and returns empty results."""

    def __init__(self):
        self.last_params: Optional[QueryParams] = None

    async def query(self, params: QueryParams) -> PaginatedResult:
        self.last_params = params
        return PaginatedResult(
            items=[], total=0, page=params.page,
            page_size=params.page_size, total_pages=0,
        )


class FilteringStubProvider(BaseDataProvider):
    """Returns items with known fields, applying filter_fields based on params."""

    FULL_ITEM = {
        "id": "1",
        "name": "test",
        "status": "active",
        "created_at": "2025-01-01",
        "description": "a record",
        "priority": "high",
    }

    def __init__(self):
        self.last_params: Optional[QueryParams] = None

    async def query(self, params: QueryParams) -> PaginatedResult:
        self.last_params = params
        filtered = filter_fields(dict(self.FULL_ITEM), params.fields)
        return PaginatedResult(
            items=[filtered],
            total=1,
            page=params.page,
            page_size=params.page_size,
            total_pages=1,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_FULL_ITEM_FIELDS = list(FilteringStubProvider.FULL_ITEM.keys())


def _make_request(**overrides) -> ServiceRequest:
    defaults = {"request_type": "query", "user_id": "u1", "data_type": "annotations"}
    defaults.update(overrides)
    return ServiceRequest(**defaults)


def _stub_providers(**extra) -> dict[str, BaseDataProvider]:
    providers = {dt: RecordingStubProvider() for dt in VALID_DATA_TYPES}
    providers.update(extra)
    return providers


# Strategies
tenant_id_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Pd")),
    min_size=1,
    max_size=50,
)

# Non-empty subsets of the known fields
fields_subset_st = st.lists(
    st.sampled_from(ALL_FULL_ITEM_FIELDS),
    min_size=1,
    max_size=len(ALL_FULL_ITEM_FIELDS),
    unique=True,
)


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 4: Tenant isolation
# For any tenant_id, the QueryParams passed to the provider should have
# the same tenant_id as provided in the request extensions.
# Validates: Requirements 2.8
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(tid=tenant_id_st)
@settings(max_examples=100)
async def test_tenant_isolation(tid: str):
    """QueryParams.tenant_id matches the tenant_id from request extensions."""
    stub = RecordingStubProvider()
    providers = _stub_providers(annotations=stub)
    handler = QueryHandler(providers=providers)

    req = _make_request(extensions={"tenant_id": tid})
    ctx = await handler.build_context(req)
    await handler.execute(req, ctx)

    assert stub.last_params is not None
    assert stub.last_params.tenant_id == tid


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 5: Pagination defaults
# For any query request that does NOT specify page/page_size, the
# QueryParams should have page=1 and page_size=50.
# Validates: Requirements 2.4
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(tid=tenant_id_st)
@settings(max_examples=100)
async def test_pagination_defaults(tid: str):
    """Unspecified page/page_size default to 1 and 50 respectively."""
    stub = RecordingStubProvider()
    providers = _stub_providers(annotations=stub)
    handler = QueryHandler(providers=providers)

    # Do NOT pass page or page_size — rely on defaults
    req = _make_request(extensions={"tenant_id": tid})
    ctx = await handler.build_context(req)
    await handler.execute(req, ctx)

    assert stub.last_params is not None
    assert stub.last_params.page == 1
    assert stub.last_params.page_size == 50


# ---------------------------------------------------------------------------
# Feature: smart-service-engine, Property 6: Field filtering correctness
# For any set of fields specified, the returned items should only contain
# those fields. Uses a FilteringStubProvider that applies filter_fields.
# Validates: Requirements 2.6
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@given(field_subset=fields_subset_st)
@settings(max_examples=100)
async def test_field_filtering_correctness(field_subset: list[str]):
    """Returned items contain only the specified fields."""
    fields_csv = ",".join(field_subset)

    stub = FilteringStubProvider()
    providers = _stub_providers(annotations=stub)
    handler = QueryHandler(providers=providers)

    req = _make_request(fields=fields_csv)
    ctx = await handler.build_context(req)
    resp = await handler.execute(req, ctx)

    for item in resp.data["items"]:
        item_keys = set(item.keys())
        assert item_keys == set(field_subset), (
            f"Expected fields {set(field_subset)}, got {item_keys}"
        )
