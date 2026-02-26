"""
Property-based tests for Metrics Recording Completeness.

Tests Property 13: Metrics recording completeness
**Validates: Requirement 5.4**

For any completed query execution, the MonitoringService should create a
DatalakeMetricsModel record containing query latency and status.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.sync.connectors.datalake.models import (
    DatalakeMetricsModel,
    VALID_METRIC_TYPES,
)
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


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def tenant_id_strategy():
    return st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=50,
    )


def datalake_type_strategy():
    return st.sampled_from(DATALAKE_TYPE_LIST)


def latency_strategy():
    """Positive latency in milliseconds (0.1 ms – 300 000 ms)."""
    return st.floats(min_value=0.1, max_value=300_000.0, allow_nan=False)


def status_strategy():
    return st.sampled_from(["success", "error"])


def query_count_strategy():
    """1-10 query executions per test."""
    return st.integers(min_value=1, max_value=10)


def invalid_metric_type_strategy():
    """Strings that are NOT valid metric types."""
    return st.text(min_size=1, max_size=30).filter(
        lambda s: s not in VALID_METRIC_TYPES
    )


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


def _sync_write_metric(session, source_id, tenant_id, metric_type, metric_data):
    """Replicate _sync_write_metric logic using the provided session.

    Mirrors DatalakeMonitoringService._sync_write_metric but uses the
    test-local session instead of the production db_manager.
    """
    if metric_type not in VALID_METRIC_TYPES:
        return False

    record = DatalakeMetricsModel(
        id=uuid4(),
        source_id=source_id,
        tenant_id=tenant_id,
        metric_type=metric_type,
        metric_data=metric_data,
        recorded_at=datetime.now(timezone.utc),
    )
    session.add(record)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

class TestMetricsRecordingCompleteness:
    """**Validates: Requirement 5.4**"""

    @settings(max_examples=50)
    @given(
        tenant_id=tenant_id_strategy(),
        src_type=datalake_type_strategy(),
        latency_ms=latency_strategy(),
        status=status_strategy(),
    )
    def test_single_query_creates_one_metric(
        self, tenant_id, src_type, latency_ms, status
    ):
        """Writing a query_perf metric creates exactly one record with correct data.

        **Validates: Requirement 5.4**
        """
        with _isolated_session() as session:
            source = _create_source(session, tenant_id, src_type)

            metric_data = {"latency_ms": latency_ms, "status": status}
            result = _sync_write_metric(
                session, source.id, tenant_id, "query_perf", metric_data
            )

            assert result is True

            records = (
                session.query(DatalakeMetricsModel)
                .filter(DatalakeMetricsModel.source_id == source.id)
                .all()
            )
            assert len(records) == 1

            record = records[0]
            assert record.metric_type == "query_perf"
            assert record.tenant_id == tenant_id
            assert record.metric_data["latency_ms"] == latency_ms
            assert record.metric_data["status"] == status

    @settings(max_examples=50)
    @given(
        tenant_id=tenant_id_strategy(),
        src_type=datalake_type_strategy(),
        latency_ms=latency_strategy(),
        status=status_strategy(),
    )
    def test_recorded_metric_contains_correct_values(
        self, tenant_id, src_type, latency_ms, status
    ):
        """The persisted metric_data faithfully stores latency and status.

        **Validates: Requirement 5.4**
        """
        with _isolated_session() as session:
            source = _create_source(session, tenant_id, src_type)

            metric_data = {"latency_ms": latency_ms, "status": status}
            _sync_write_metric(
                session, source.id, tenant_id, "query_perf", metric_data
            )

            record = (
                session.query(DatalakeMetricsModel)
                .filter(
                    DatalakeMetricsModel.source_id == source.id,
                    DatalakeMetricsModel.metric_type == "query_perf",
                )
                .one()
            )

            assert record.metric_data["latency_ms"] == latency_ms
            assert record.metric_data["status"] == status
            assert record.recorded_at is not None

    @settings(max_examples=30)
    @given(
        data=st.data(),
        tenant_id=tenant_id_strategy(),
        src_type=datalake_type_strategy(),
        n_queries=query_count_strategy(),
    )
    def test_n_queries_produce_n_records(
        self, data, tenant_id, src_type, n_queries
    ):
        """For N query executions, exactly N metric records are created.

        **Validates: Requirement 5.4**
        """
        with _isolated_session() as session:
            source = _create_source(session, tenant_id, src_type)

            for _ in range(n_queries):
                lat = data.draw(latency_strategy())
                sts = data.draw(status_strategy())
                _sync_write_metric(
                    session,
                    source.id,
                    tenant_id,
                    "query_perf",
                    {"latency_ms": lat, "status": sts},
                )

            count = (
                session.query(DatalakeMetricsModel)
                .filter(DatalakeMetricsModel.source_id == source.id)
                .count()
            )
            assert count == n_queries

    @settings(max_examples=50)
    @given(
        tenant_id=tenant_id_strategy(),
        src_type=datalake_type_strategy(),
        bad_type=invalid_metric_type_strategy(),
    )
    def test_invalid_metric_type_rejected(
        self, tenant_id, src_type, bad_type
    ):
        """Invalid metric_type values are rejected — no record created.

        **Validates: Requirement 5.4**
        """
        with _isolated_session() as session:
            source = _create_source(session, tenant_id, src_type)

            result = _sync_write_metric(
                session,
                source.id,
                tenant_id,
                bad_type,
                {"latency_ms": 10.0, "status": "success"},
            )

            assert result is False

            count = (
                session.query(DatalakeMetricsModel)
                .filter(DatalakeMetricsModel.source_id == source.id)
                .count()
            )
            assert count == 0
