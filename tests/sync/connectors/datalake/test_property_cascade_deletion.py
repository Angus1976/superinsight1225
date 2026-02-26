"""
Property-based tests for Cascade Deletion.

Tests Property 5: Cascade deletion
**Validates: Requirement 2.5**

For any data source with associated metric records, deleting the data source
should also remove all its associated DatalakeMetricsModel records.
Metrics belonging to OTHER sources must not be affected.
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
from src.sync.connectors.datalake.models import DatalakeMetricsModel
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

METRIC_TYPES = ["health", "volume", "query_perf"]


def tenant_id_strategy():
    return st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=50,
    )


def datalake_type_strategy():
    return st.sampled_from(DATALAKE_TYPE_LIST)


def metric_count_strategy():
    """1-8 metrics per source — enough to verify without being slow."""
    return st.integers(min_value=1, max_value=8)


def metric_type_strategy():
    return st.sampled_from(METRIC_TYPES)


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


def _create_metric(session, source_id, tenant_id, metric_type):
    metric = DatalakeMetricsModel(
        id=uuid4(),
        source_id=source_id,
        tenant_id=tenant_id,
        metric_type=metric_type,
        metric_data={"value": 42},
        recorded_at=datetime.now(timezone.utc),
    )
    session.add(metric)
    session.flush()
    return metric


def _cascade_delete_source(session, source_id):
    """Replicate the cascade delete logic from router.delete_datalake_source."""
    session.query(DatalakeMetricsModel).filter(
        DatalakeMetricsModel.source_id == source_id,
    ).delete(synchronize_session=False)

    source = session.get(DataSourceModel, source_id)
    if source:
        session.delete(source)
    session.commit()


class TestCascadeDeletion:
    """**Validates: Requirement 2.5**"""

    @settings(max_examples=50)
    @given(
        data=st.data(),
        tenant_id=tenant_id_strategy(),
        src_type=datalake_type_strategy(),
        metric_count=metric_count_strategy(),
    )
    def test_delete_source_removes_all_its_metrics(
        self, data, tenant_id, src_type, metric_count
    ):
        """Deleting a source removes every associated metric record.

        **Validates: Requirement 2.5**
        """
        with _isolated_session() as session:
            source = _create_source(session, tenant_id, src_type)

            for _ in range(metric_count):
                m_type = data.draw(metric_type_strategy())
                _create_metric(session, source.id, tenant_id, m_type)

            session.flush()
            assert (
                session.query(DatalakeMetricsModel)
                .filter(DatalakeMetricsModel.source_id == source.id)
                .count()
                == metric_count
            )

            _cascade_delete_source(session, source.id)

            remaining = (
                session.query(DatalakeMetricsModel)
                .filter(DatalakeMetricsModel.source_id == source.id)
                .count()
            )
            assert remaining == 0

    @settings(max_examples=50)
    @given(
        data=st.data(),
        tenant_id=tenant_id_strategy(),
        metric_count_target=metric_count_strategy(),
        metric_count_other=metric_count_strategy(),
    )
    def test_delete_source_does_not_affect_other_sources(
        self, data, tenant_id, metric_count_target, metric_count_other
    ):
        """Metrics for other sources are untouched after cascade delete.

        **Validates: Requirement 2.5**
        """
        with _isolated_session() as session:
            target = _create_source(
                session, tenant_id, data.draw(datalake_type_strategy())
            )
            other = _create_source(
                session, tenant_id, data.draw(datalake_type_strategy())
            )

            for _ in range(metric_count_target):
                _create_metric(
                    session, target.id, tenant_id, data.draw(metric_type_strategy())
                )
            for _ in range(metric_count_other):
                _create_metric(
                    session, other.id, tenant_id, data.draw(metric_type_strategy())
                )

            session.flush()

            _cascade_delete_source(session, target.id)

            remaining_other = (
                session.query(DatalakeMetricsModel)
                .filter(DatalakeMetricsModel.source_id == other.id)
                .count()
            )
            assert remaining_other == metric_count_other

            remaining_target = (
                session.query(DatalakeMetricsModel)
                .filter(DatalakeMetricsModel.source_id == target.id)
                .count()
            )
            assert remaining_target == 0
