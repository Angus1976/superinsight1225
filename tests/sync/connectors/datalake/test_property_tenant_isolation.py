"""
Property-based tests for Tenant Isolation.

Tests Property 4: Tenant isolation
**Validates: Requirements 2.3, 7.5**

For any two tenants A and B, data sources created by tenant A should never
appear in tenant B's list results, and tenant B should receive 404 when
accessing tenant A's specific source by ID.
"""

from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi import HTTPException
from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.sync.connectors.datalake.router import (
    _get_datalake_sources,
    _get_source_or_404,
)
from src.sync.models import (
    DATALAKE_TYPES,
    DataSourceModel,
    DataSourceStatus,
    DataSourceType,
)


# SQLite cannot handle JSONB; compile as JSON instead.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


DATALAKE_TYPE_LIST = list(DATALAKE_TYPES)


def tenant_id_strategy():
    return st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1, max_size=50,
    )


def distinct_tenant_pair_strategy():
    return st.tuples(tenant_id_strategy(), tenant_id_strategy()).filter(
        lambda p: p[0] != p[1]
    )



def datalake_type_strategy():
    return st.sampled_from(DATALAKE_TYPE_LIST)


def source_count_strategy():
    return st.integers(min_value=1, max_value=5)


@contextmanager
def _isolated_session():
    """Fresh in-memory SQLite DB per call — no cross-example leakage."""
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _create_source(session, tenant_id, source_type):
    source = DataSourceModel(
        id=uuid4(),
        tenant_id=tenant_id,
        name=f"src-{uuid4().hex[:8]}",
        source_type=source_type,
        status=DataSourceStatus.ACTIVE,
        connection_config={"host": "localhost", "port": 9000},
    )
    session.add(source)
    session.flush()
    return source


class TestTenantIsolationListSources:
    """**Validates: Requirements 2.3, 7.5**"""

    @settings(max_examples=50)
    @given(
        data=st.data(),
        tenant_pair=distinct_tenant_pair_strategy(),
        count_a=source_count_strategy(),
        count_b=source_count_strategy(),
    )
    def test_list_sources_isolated_between_tenants(
        self, data, tenant_pair, count_a, count_b
    ):
        """_get_datalake_sources returns only the queried tenant's sources.

        **Validates: Requirements 2.3, 7.5**
        """
        tenant_a, tenant_b = tenant_pair

        with _isolated_session() as session:
            a_ids = set()
            for _ in range(count_a):
                s = _create_source(session, tenant_a, data.draw(datalake_type_strategy()))
                a_ids.add(s.id)

            b_ids = set()
            for _ in range(count_b):
                s = _create_source(session, tenant_b, data.draw(datalake_type_strategy()))
                b_ids.add(s.id)

            result_a_ids = {s.id for s in _get_datalake_sources(tenant_a, session)}
            result_b_ids = {s.id for s in _get_datalake_sources(tenant_b, session)}

            assert result_a_ids == a_ids
            assert result_b_ids == b_ids
            assert result_a_ids.isdisjoint(result_b_ids)


class TestTenantIsolationGetSourceById:
    """**Validates: Requirements 2.3, 7.5**"""

    @settings(max_examples=50)
    @given(
        tenant_pair=distinct_tenant_pair_strategy(),
        src_type=datalake_type_strategy(),
    )
    def test_cross_tenant_access_returns_404(self, tenant_pair, src_type):
        """_get_source_or_404 raises 404 for cross-tenant access.

        **Validates: Requirements 2.3, 7.5**
        """
        tenant_a, tenant_b = tenant_pair

        with _isolated_session() as session:
            source = _create_source(session, tenant_a, src_type)

            found = _get_source_or_404(source.id, tenant_a, session)
            assert found.id == source.id

            with pytest.raises(HTTPException) as exc_info:
                _get_source_or_404(source.id, tenant_b, session)
            assert exc_info.value.status_code == 404
