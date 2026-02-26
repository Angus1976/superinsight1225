"""
Unit tests for DatalakeMonitoringService.

Validates: Requirements 3.3, 3.4, 5.4, 6.1
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.connection import Base
from src.sync.connectors.datalake.models import DatalakeMetricsModel
from src.sync.connectors.datalake.monitoring import (
    DatalakeMonitoringService,
    MAX_RETRIES,
)
from src.sync.models import (
    DataSourceModel,
    DataSourceStatus,
    DataSourceType,
)


# SQLite cannot handle JSONB; compile as JSON instead.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@contextmanager
def _isolated_session():
    """Fresh in-memory SQLite DB per call."""
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


def _create_source(session, tenant_id="t1", source_type=DataSourceType.CLICKHOUSE):
    source = DataSourceModel(
        id=uuid4(),
        tenant_id=tenant_id,
        name=f"src-{uuid4().hex[:8]}",
        source_type=source_type,
        status=DataSourceStatus.INACTIVE,
        connection_config={"host": "localhost", "port": 9000},
    )
    session.add(source)
    session.flush()
    return source


class TestRecordHealthCheck:
    """Tests for record_health_check — Validates: Req 3.4, 5.4"""

    @pytest.mark.asyncio
    async def test_writes_health_metric(self):
        """A health metric record is persisted with correct fields."""
        svc = DatalakeMonitoringService()
        source_id = uuid4()

        with _isolated_session() as session:
            # Create a source first so FK is satisfied
            source = DataSourceModel(
                id=source_id,
                tenant_id="t1",
                name="test",
                source_type=DataSourceType.CLICKHOUSE,
                status=DataSourceStatus.ACTIVE,
                connection_config={},
            )
            session.add(source)
            session.commit()

            # Patch _get_sync_session to return our test session
            with patch.object(
                DatalakeMonitoringService,
                "_get_sync_session",
                return_value=session,
            ):
                # Call synchronous writer directly (avoids asyncio.to_thread)
                svc._sync_write_metric(
                    source_id, "t1", "health",
                    {"status": "connected", "latency_ms": 42.5},
                )

            metrics = session.query(DatalakeMetricsModel).all()
            assert len(metrics) == 1
            m = metrics[0]
            assert m.source_id == source_id
            assert m.tenant_id == "t1"
            assert m.metric_type == "health"
            assert m.metric_data["status"] == "connected"
            assert m.metric_data["latency_ms"] == 42.5

    @pytest.mark.asyncio
    async def test_health_error_includes_error_message(self):
        """Error health checks include the error_message field."""
        svc = DatalakeMonitoringService()
        source_id = uuid4()

        with _isolated_session() as session:
            source = DataSourceModel(
                id=source_id,
                tenant_id="t1",
                name="test",
                source_type=DataSourceType.HIVE,
                status=DataSourceStatus.ACTIVE,
                connection_config={},
            )
            session.add(source)
            session.commit()

            with patch.object(
                DatalakeMonitoringService,
                "_get_sync_session",
                return_value=session,
            ):
                svc._sync_write_metric(
                    source_id, "t1", "health",
                    {"status": "error", "latency_ms": 0, "error_message": "timeout"},
                )

            m = session.query(DatalakeMetricsModel).first()
            assert m.metric_data["error_message"] == "timeout"


class TestRecordVolumeMetric:
    """Tests for record_volume_metric — Validates: Req 6.1"""

    @pytest.mark.asyncio
    async def test_writes_volume_metric(self):
        svc = DatalakeMonitoringService()
        source_id = uuid4()

        with _isolated_session() as session:
            source = DataSourceModel(
                id=source_id,
                tenant_id="t1",
                name="test",
                source_type=DataSourceType.DORIS,
                status=DataSourceStatus.ACTIVE,
                connection_config={},
            )
            session.add(source)
            session.commit()

            with patch.object(
                DatalakeMonitoringService,
                "_get_sync_session",
                return_value=session,
            ):
                svc._sync_write_metric(
                    source_id, "t1", "volume",
                    {"volume_gb": 123.4, "row_count": 1_000_000},
                )

            m = session.query(DatalakeMetricsModel).first()
            assert m.metric_type == "volume"
            assert m.metric_data["volume_gb"] == 123.4
            assert m.metric_data["row_count"] == 1_000_000


class TestRecordQueryPerformance:
    """Tests for record_query_performance — Validates: Req 5.4"""

    @pytest.mark.asyncio
    async def test_writes_query_perf_metric(self):
        svc = DatalakeMonitoringService()
        source_id = uuid4()

        with _isolated_session() as session:
            source = DataSourceModel(
                id=source_id,
                tenant_id="t1",
                name="test",
                source_type=DataSourceType.SPARK_SQL,
                status=DataSourceStatus.ACTIVE,
                connection_config={},
            )
            session.add(source)
            session.commit()

            with patch.object(
                DatalakeMonitoringService,
                "_get_sync_session",
                return_value=session,
            ):
                svc._sync_write_metric(
                    source_id, "t1", "query_perf",
                    {"latency_ms": 250.0, "status": "success"},
                )

            m = session.query(DatalakeMetricsModel).first()
            assert m.metric_type == "query_perf"
            assert m.metric_data["latency_ms"] == 250.0
            assert m.metric_data["status"] == "success"


class TestInvalidMetricType:
    """Invalid metric_type should be rejected."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_metric_type(self):
        svc = DatalakeMonitoringService()
        source_id = uuid4()

        with _isolated_session() as session:
            source = DataSourceModel(
                id=source_id,
                tenant_id="t1",
                name="test",
                source_type=DataSourceType.CLICKHOUSE,
                status=DataSourceStatus.ACTIVE,
                connection_config={},
            )
            session.add(source)
            session.commit()

            # _write_metric is async and validates metric_type before writing
            await svc._write_metric(source_id, "t1", "invalid_type", {"x": 1})

            # No record should have been written
            with patch.object(
                DatalakeMonitoringService,
                "_get_sync_session",
                return_value=session,
            ):
                count = session.query(DatalakeMetricsModel).count()
                assert count == 0


class TestCollectDatalakeMetrics:
    """Tests for collect_datalake_metrics — Validates: Req 3.3, 3.4"""

    @pytest.mark.asyncio
    async def test_successful_collection_updates_source_health(self):
        """Successful health check updates DataSourceModel fields."""
        svc = DatalakeMonitoringService()

        with _isolated_session() as session:
            source = _create_source(session, "t1", DataSourceType.CLICKHOUSE)
            source_id = source.id
            session.commit()

            mock_connector = AsyncMock()
            mock_connector.test_connection.return_value = {
                "success": True,
                "latency_ms": 15.0,
            }
            mock_connector.disconnect = AsyncMock()

            with patch(
                "src.sync.connectors.base.ConnectorFactory.create",
                return_value=mock_connector,
            ) as _mock_create, patch.object(
                DatalakeMonitoringService,
                "_get_sync_session",
                return_value=session,
            ):
                results = await svc.collect_datalake_metrics("t1", db=session)

            assert len(results) == 1
            assert results[0]["status"] == "connected"

            # Re-query source to verify health fields (Req 3.4)
            updated = session.query(DataSourceModel).get(source_id)
            assert updated.health_check_status == "connected"
            assert updated.last_health_check is not None
            assert updated.status == DataSourceStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_failed_connection_retries_with_backoff(self):
        """Failed connections retry up to MAX_RETRIES times (Req 3.3)."""
        svc = DatalakeMonitoringService()

        with _isolated_session() as session:
            source = _create_source(session, "t1", DataSourceType.HIVE)
            source_id = source.id
            session.commit()

            mock_connector = AsyncMock()
            mock_connector.test_connection.side_effect = ConnectionError("refused")
            mock_connector.disconnect = AsyncMock()

            with patch(
                "src.sync.connectors.base.ConnectorFactory.create",
                return_value=mock_connector,
            ), patch.object(
                DatalakeMonitoringService,
                "_get_sync_session",
                return_value=session,
            ), patch(
                "src.sync.connectors.datalake.monitoring.asyncio.sleep",
                new_callable=AsyncMock,
            ) as mock_sleep:
                results = await svc.collect_datalake_metrics("t1", db=session)

            assert results[0]["status"] == "error"
            assert "refused" in results[0]["error_message"]

            # Should have been called MAX_RETRIES times
            assert mock_connector.test_connection.call_count == MAX_RETRIES

            # Exponential backoff sleeps: 1s, 2s (before 2nd and 3rd attempts)
            assert mock_sleep.call_count == MAX_RETRIES - 1

            # Source should be marked as ERROR (Req 3.4)
            updated = session.query(DataSourceModel).get(source_id)
            assert updated.health_check_status == "error"
            assert updated.status == DataSourceStatus.ERROR

    @pytest.mark.asyncio
    async def test_connector_creation_failure(self):
        """If connector creation fails, source is marked error."""
        svc = DatalakeMonitoringService()

        with _isolated_session() as session:
            source = _create_source(session, "t1", DataSourceType.DORIS)
            session.commit()

            with patch(
                "src.sync.connectors.base.ConnectorFactory.create",
                side_effect=ValueError("bad config"),
            ), patch.object(
                DatalakeMonitoringService,
                "_get_sync_session",
                return_value=session,
            ):
                results = await svc.collect_datalake_metrics("t1", db=session)

            assert results[0]["status"] == "error"
            assert "bad config" in results[0]["error_message"]
