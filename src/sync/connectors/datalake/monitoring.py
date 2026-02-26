"""
Datalake/Warehouse Monitoring Service.

Extends the sync monitoring system with datalake-specific metric collection:
- Health check status recording
- Data volume tracking
- Query performance metrics

All metrics are written asynchronously to DatalakeMetricsModel.

Validates: Requirements 3.3, 3.4, 5.4, 6.1
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.database.connection import db_manager
from src.sync.connectors.datalake.models import DatalakeMetricsModel, VALID_METRIC_TYPES
from src.sync.models import (
    DATALAKE_TYPES,
    DataSourceModel,
    DataSourceStatus,
)

logger = logging.getLogger(__name__)

# Retry configuration for connection tests (Req 3.3)
MAX_RETRIES = 3
INITIAL_BACKOFF_S = 1.0


class DatalakeMonitoringService:
    """Datalake/warehouse metric collection and persistence.

    Provides async methods to record health, volume, and query
    performance metrics into DatalakeMetricsModel.  Also exposes
    a bulk ``collect_datalake_metrics`` helper that iterates over
    all datalake sources for a tenant and gathers health/volume data.
    """

    # ------------------------------------------------------------------
    # Async metric writers
    # ------------------------------------------------------------------

    async def record_health_check(
        self,
        source_id: UUID,
        tenant_id: str,
        status: str,
        latency_ms: float,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a health-check metric asynchronously.

        Args:
            source_id: Data source identifier.
            tenant_id: Owning tenant.
            status: Health status (e.g. "connected", "error").
            latency_ms: Round-trip latency in milliseconds.
            error_message: Optional error detail when status is "error".
        """
        metric_data: Dict[str, Any] = {
            "status": status,
            "latency_ms": latency_ms,
        }
        if error_message:
            metric_data["error_message"] = error_message

        await self._write_metric(source_id, tenant_id, "health", metric_data)

    async def record_volume_metric(
        self,
        source_id: UUID,
        tenant_id: str,
        volume_gb: float,
        row_count: int,
    ) -> None:
        """Record a data-volume metric asynchronously.

        Args:
            source_id: Data source identifier.
            tenant_id: Owning tenant.
            volume_gb: Estimated data volume in gigabytes.
            row_count: Estimated total row count.
        """
        metric_data: Dict[str, Any] = {
            "volume_gb": volume_gb,
            "row_count": row_count,
        }
        await self._write_metric(source_id, tenant_id, "volume", metric_data)

    async def record_query_performance(
        self,
        source_id: UUID,
        tenant_id: str,
        latency_ms: float,
        status: str,
    ) -> None:
        """Record a query-performance metric asynchronously.

        Called after each query execution (Req 5.4).

        Args:
            source_id: Data source identifier.
            tenant_id: Owning tenant.
            latency_ms: Query execution time in milliseconds.
            status: Query outcome ("success" or "error").
        """
        metric_data: Dict[str, Any] = {
            "latency_ms": latency_ms,
            "status": status,
        }
        await self._write_metric(source_id, tenant_id, "query_perf", metric_data)

    # ------------------------------------------------------------------
    # Bulk collection
    # ------------------------------------------------------------------

    async def collect_datalake_metrics(
        self,
        tenant_id: str,
        db: Optional[Session] = None,
    ) -> List[Dict[str, Any]]:
        """Iterate over all datalake sources for *tenant_id* and collect
        health and volume metrics.

        For each source a connector is created, a connection test is
        performed (with up to 3 retries / exponential backoff per Req 3.3),
        and the DataSourceModel health fields are updated (Req 3.4).

        Returns a list of per-source result dicts for callers that need
        immediate feedback (e.g. dashboard aggregation).
        """
        close_session = False
        if db is None:
            db = self._get_sync_session()
            close_session = True

        try:
            sources = self._query_datalake_sources(db, tenant_id)
            results: List[Dict[str, Any]] = []

            for source in sources:
                result = await self._collect_single_source(source, tenant_id, db)
                results.append(result)

            db.commit()
            return results
        except Exception:
            db.rollback()
            raise
        finally:
            if close_session:
                db.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _write_metric(
        self,
        source_id: UUID,
        tenant_id: str,
        metric_type: str,
        metric_data: Dict[str, Any],
    ) -> None:
        """Persist a single metric record in a background thread.

        Uses ``asyncio.to_thread`` so the synchronous SQLAlchemy
        session does not block the event loop.
        """
        if metric_type not in VALID_METRIC_TYPES:
            logger.error("Invalid metric_type %r, skipping write", metric_type)
            return

        await asyncio.to_thread(
            self._sync_write_metric, source_id, tenant_id, metric_type, metric_data
        )

    def _sync_write_metric(
        self,
        source_id: UUID,
        tenant_id: str,
        metric_type: str,
        metric_data: Dict[str, Any],
    ) -> None:
        """Synchronous DB write executed inside a worker thread."""
        session = self._get_sync_session()
        try:
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
            logger.debug(
                "Recorded %s metric for source %s", metric_type, source_id
            )
        except Exception as exc:
            session.rollback()
            logger.error(
                "Failed to write %s metric for source %s: %s",
                metric_type,
                source_id,
                exc,
            )
        finally:
            session.close()

    @staticmethod
    def _get_sync_session() -> Session:
        """Obtain a new synchronous SQLAlchemy session."""
        return db_manager.get_session_factory()()

    @staticmethod
    def _query_datalake_sources(
        db: Session, tenant_id: str
    ) -> List[DataSourceModel]:
        """Return all datalake-type sources for *tenant_id*."""
        return (
            db.query(DataSourceModel)
            .filter(
                DataSourceModel.tenant_id == tenant_id,
                DataSourceModel.source_type.in_(DATALAKE_TYPES),
            )
            .all()
        )

    async def _collect_single_source(
        self,
        source: DataSourceModel,
        tenant_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Run health check (with retries) for one source and record metrics."""
        from src.sync.connectors.base import ConnectorFactory

        result: Dict[str, Any] = {
            "source_id": str(source.id),
            "source_name": source.name,
            "source_type": source.source_type.value,
            "status": "error",
            "latency_ms": 0.0,
            "error_message": None,
        }

        connector = None
        try:
            connector = ConnectorFactory.create(
                source.source_type.value, source.connection_config
            )
        except Exception as exc:
            result["error_message"] = f"Failed to create connector: {exc}"
            await self._update_source_health(source, db, "error", result["error_message"])
            await self.record_health_check(
                source.id, tenant_id, "error", 0.0, result["error_message"]
            )
            return result

        # Retry with exponential backoff (Req 3.3)
        last_error: Optional[str] = None
        for attempt in range(MAX_RETRIES):
            try:
                start = time.monotonic()
                test_result = await connector.test_connection()
                elapsed_ms = (time.monotonic() - start) * 1000

                if test_result.get("success"):
                    result["status"] = "connected"
                    result["latency_ms"] = elapsed_ms
                    break
                else:
                    last_error = test_result.get("error", "Unknown error")
            except Exception as exc:
                last_error = str(exc)

            # Exponential backoff before next retry
            if attempt < MAX_RETRIES - 1:
                backoff = INITIAL_BACKOFF_S * (2 ** attempt)
                await asyncio.sleep(backoff)

        if result["status"] != "connected":
            result["status"] = "error"
            result["error_message"] = last_error

        # Disconnect connector
        try:
            await connector.disconnect()
        except Exception:
            pass

        # Update DataSourceModel health fields (Req 3.4)
        await self._update_source_health(
            source, db, result["status"], result.get("error_message")
        )

        # Record health metric
        await self.record_health_check(
            source.id,
            tenant_id,
            result["status"],
            result["latency_ms"],
            result.get("error_message"),
        )

        return result

    @staticmethod
    async def _update_source_health(
        source: DataSourceModel,
        db: Session,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Update health_check_status and last_health_check on the source model."""
        now = datetime.now(timezone.utc)
        source.health_check_status = status
        source.last_health_check = now
        if status == "connected":
            source.status = DataSourceStatus.ACTIVE
        elif status == "error":
            source.status = DataSourceStatus.ERROR


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

datalake_monitoring_service = DatalakeMonitoringService()


def get_datalake_monitoring_service() -> DatalakeMonitoringService:
    """Return the global datalake monitoring service instance."""
    return datalake_monitoring_service
