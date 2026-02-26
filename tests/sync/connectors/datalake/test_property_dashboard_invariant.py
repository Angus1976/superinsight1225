"""
Property-based tests for Dashboard Overview Numerical Invariant.

Tests Property 9: Dashboard overview numerical invariant
**Validates: Requirements 6.1, 6.2**

For any DashboardOverview, total_sources should equal active_sources +
error_sources + remaining inactive sources, and avg_query_latency_ms
should be non-negative.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.sync.connectors.datalake.models import DatalakeMetricsModel
from src.sync.connectors.datalake.schemas import DashboardOverview, SourceSummary
from src.sync.models import (
    DATALAKE_TYPES,
    DataSourceModel,
    DataSourceStatus,
)


# SQLite cannot handle JSONB; compile as JSON instead.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


DATALAKE_TYPE_LIST = list(DATALAKE_TYPES)
STATUS_LIST = list(DataSourceStatus)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def datalake_type_strategy():
    return st.sampled_from(DATALAKE_TYPE_LIST)


def status_strategy():
    return st.sampled_from(STATUS_LIST)


def tenant_id_strategy():
    return st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=50,
    )


def non_negative_float_strategy():
    """Non-negative float values for metrics."""
    return st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False)


def source_count_strategy():
    return st.integers(min_value=0, max_value=10)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _create_source(session, tenant_id, source_type, status):
    """Create a DataSourceModel with the given status."""
    source = DataSourceModel(
        id=uuid4(),
        tenant_id=tenant_id,
        name=f"src-{uuid4().hex[:8]}",
        source_type=source_type,
        status=status,
        connection_config={"host": "localhost", "port": 9000},
    )
    session.add(source)
    session.flush()
    return source


def _build_overview_from_db(tenant_id: str, session: Session) -> DashboardOverview:
    """Replicate the dashboard overview aggregation logic from the router.

    This mirrors ``get_dashboard_overview`` in router.py so we can verify
    the numerical invariants hold for any combination of sources/metrics.
    """
    from src.sync.connectors.datalake.router import _get_datalake_sources

    sources = _get_datalake_sources(tenant_id, session)
    if not sources:
        return DashboardOverview(
            total_sources=0,
            active_sources=0,
            error_sources=0,
            total_data_volume_gb=0.0,
            avg_query_latency_ms=0.0,
            sources=[],
        )

    active = sum(1 for s in sources if s.status == DataSourceStatus.ACTIVE)
    error = sum(1 for s in sources if s.status == DataSourceStatus.ERROR)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_metrics = (
        session.query(DatalakeMetricsModel)
        .filter(
            DatalakeMetricsModel.tenant_id == tenant_id,
            DatalakeMetricsModel.recorded_at >= cutoff,
        )
        .all()
    )

    total_volume = sum(
        m.metric_data.get("volume_gb", 0.0)
        for m in recent_metrics
        if m.metric_type == "volume"
    )
    latencies = [
        m.metric_data.get("latency_ms", 0.0)
        for m in recent_metrics
        if m.metric_type == "query_perf"
    ]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return DashboardOverview(
        total_sources=len(sources),
        active_sources=active,
        error_sources=error,
        total_data_volume_gb=round(total_volume, 2),
        avg_query_latency_ms=round(avg_latency, 2),
        sources=[
            SourceSummary(
                source_id=s.id,
                name=s.name,
                source_type=s.source_type,
                status=s.status,
                health_check_status=s.health_check_status,
            )
            for s in sources
        ],
    )


def _add_volume_metric(session, source_id, tenant_id, volume_gb):
    """Insert a volume metric record."""
    metric = DatalakeMetricsModel(
        id=uuid4(),
        source_id=source_id,
        tenant_id=tenant_id,
        metric_type="volume",
        metric_data={"volume_gb": volume_gb},
        recorded_at=datetime.now(timezone.utc),
    )
    session.add(metric)
    session.flush()


def _add_query_perf_metric(session, source_id, tenant_id, latency_ms):
    """Insert a query performance metric record."""
    metric = DatalakeMetricsModel(
        id=uuid4(),
        source_id=source_id,
        tenant_id=tenant_id,
        metric_type="query_perf",
        metric_data={"latency_ms": latency_ms},
        recorded_at=datetime.now(timezone.utc),
    )
    session.add(metric)
    session.flush()


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------

class TestDashboardSourceCountInvariant:
    """total_sources >= active_sources + error_sources for any mix of statuses.

    **Validates: Requirements 6.1, 6.2**
    """

    @settings(max_examples=50)
    @given(
        data=st.data(),
        tenant_id=tenant_id_strategy(),
        num_sources=source_count_strategy(),
    )
    def test_total_sources_gte_active_plus_error(
        self, data, tenant_id, num_sources,
    ):
        """For any generated sources, total_sources >= active_sources + error_sources.

        **Validates: Requirements 6.1, 6.2**
        """
        with _isolated_session() as session:
            for _ in range(num_sources):
                _create_source(
                    session,
                    tenant_id,
                    data.draw(datalake_type_strategy()),
                    data.draw(status_strategy()),
                )

            overview = _build_overview_from_db(tenant_id, session)

            assert overview.total_sources == num_sources
            assert overview.total_sources >= overview.active_sources + overview.error_sources
            assert overview.active_sources >= 0
            assert overview.error_sources >= 0


class TestDashboardLatencyNonNegative:
    """avg_query_latency_ms should always be non-negative.

    **Validates: Requirements 6.1, 6.2**
    """

    @settings(max_examples=50)
    @given(
        data=st.data(),
        tenant_id=tenant_id_strategy(),
        num_sources=st.integers(min_value=1, max_value=5),
        num_metrics=st.integers(min_value=0, max_value=10),
    )
    def test_avg_latency_is_non_negative(
        self, data, tenant_id, num_sources, num_metrics,
    ):
        """For any set of query perf metrics, avg_query_latency_ms >= 0.

        **Validates: Requirements 6.1, 6.2**
        """
        with _isolated_session() as session:
            source_ids = []
            for _ in range(num_sources):
                s = _create_source(
                    session,
                    tenant_id,
                    data.draw(datalake_type_strategy()),
                    DataSourceStatus.ACTIVE,
                )
                source_ids.append(s.id)

            for _ in range(num_metrics):
                sid = data.draw(st.sampled_from(source_ids))
                latency = data.draw(non_negative_float_strategy())
                _add_query_perf_metric(session, sid, tenant_id, latency)

            overview = _build_overview_from_db(tenant_id, session)

            assert overview.avg_query_latency_ms >= 0


class TestDashboardVolumeNonNegative:
    """total_data_volume_gb should always be non-negative.

    **Validates: Requirements 6.1, 6.2**
    """

    @settings(max_examples=50)
    @given(
        data=st.data(),
        tenant_id=tenant_id_strategy(),
        num_sources=st.integers(min_value=1, max_value=5),
        num_metrics=st.integers(min_value=0, max_value=10),
    )
    def test_total_volume_is_non_negative(
        self, data, tenant_id, num_sources, num_metrics,
    ):
        """For any set of volume metrics, total_data_volume_gb >= 0.

        **Validates: Requirements 6.1, 6.2**
        """
        with _isolated_session() as session:
            source_ids = []
            for _ in range(num_sources):
                s = _create_source(
                    session,
                    tenant_id,
                    data.draw(datalake_type_strategy()),
                    DataSourceStatus.ACTIVE,
                )
                source_ids.append(s.id)

            for _ in range(num_metrics):
                sid = data.draw(st.sampled_from(source_ids))
                volume = data.draw(non_negative_float_strategy())
                _add_volume_metric(session, sid, tenant_id, volume)

            overview = _build_overview_from_db(tenant_id, session)

            assert overview.total_data_volume_gb >= 0


class TestDashboardEmptyState:
    """Dashboard with zero sources returns all-zero metrics.

    **Validates: Requirements 6.1, 6.2**
    """

    @settings(max_examples=30)
    @given(tenant_id=tenant_id_strategy())
    def test_empty_dashboard_returns_zeros(self, tenant_id):
        """With no sources, all numerical fields are zero.

        **Validates: Requirements 6.1, 6.2**
        """
        with _isolated_session() as session:
            overview = _build_overview_from_db(tenant_id, session)

            assert overview.total_sources == 0
            assert overview.active_sources == 0
            assert overview.error_sources == 0
            assert overview.total_data_volume_gb == 0.0
            assert overview.avg_query_latency_ms == 0.0
            assert overview.sources == []
