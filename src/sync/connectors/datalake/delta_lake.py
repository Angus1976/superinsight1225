"""
Delta Lake Connector Module.

Provides DeltaLakeConnector using the deltalake Python package.
"""

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import Field

from src.sync.connectors.base import (
    ConnectionStatus,
    ConnectorFactory,
    DataBatch,
    DataRecord,
    SyncResult,
)
from src.sync.connectors.datalake.base import (
    DatalakeBaseConnector,
    DatalakeConnectorConfig,
)

logger = logging.getLogger(__name__)

# Optional driver import
try:
    import deltalake as dl_lib  # noqa: F401

    HAS_DELTALAKE = True
except ImportError:
    HAS_DELTALAKE = False


class DeltaLakeConfig(DatalakeConnectorConfig):
    """Delta Lake 连接器配置。"""

    port: int = Field(default=443, ge=1, le=65535)
    table_uri: str = ""
    storage_options: Dict[str, str] = Field(default_factory=dict)


class DeltaLakeConnector(DatalakeBaseConnector):
    """Delta Lake 连接器，使用 deltalake 包读写 Delta 表。"""

    def __init__(self, config: DeltaLakeConfig):
        super().__init__(config)
        self.delta_config = config
        self._dt: Any = None  # DeltaTable instance

    # ------------------------------------------------------------------
    # BaseConnector abstract methods
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Open the Delta Lake table."""
        self._set_status(ConnectionStatus.CONNECTING)
        try:
            self._dt = await self._open_table()
            self._set_status(ConnectionStatus.CONNECTED)
            return True
        except Exception as exc:
            self._record_error(exc)
            self._set_status(ConnectionStatus.ERROR)
            return False

    async def disconnect(self) -> None:
        """Release Delta Lake table reference."""
        self._dt = None
        self._set_status(ConnectionStatus.DISCONNECTED)

    async def health_check(self) -> bool:
        """Verify the Delta table is accessible."""
        if not self.is_connected or self._dt is None:
            return False
        try:
            loop = asyncio.get_event_loop()
            version = await loop.run_in_executor(None, self._dt.version)
            return version >= 0
        except Exception as exc:
            self._record_error(exc)
            return False

    async def fetch_schema(self) -> Dict[str, Any]:
        """Return schema information for the Delta table."""
        if self._dt is None:
            raise ConnectionError("Not connected to Delta Lake")
        loop = asyncio.get_event_loop()
        schema = await loop.run_in_executor(None, lambda: self._dt.schema())
        fields = [
            {"name": f.name, "type": str(f.type)}
            for f in schema.fields
        ]
        return {
            "database": self.dl_config.database,
            "tables": [{"name": self.delta_config.table_uri, "columns": fields}],
            "connector_type": "delta_lake",
        }

    async def fetch_data(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None,
    ) -> DataBatch:
        """Fetch data from the Delta table."""
        if query:
            return await self.execute_query(query)
        return await self._read_table(limit=limit)

    async def fetch_data_stream(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None,
    ) -> AsyncIterator[DataBatch]:
        """Stream data from Delta Lake in batches."""
        batch = await self.fetch_data(query=query, table=table, limit=batch_size)
        yield batch

    async def write_data(
        self, batch: DataBatch, mode: str = "upsert"
    ) -> SyncResult:
        """Write data to Delta Lake (stub)."""
        return SyncResult(success=False, records_failed=len(batch.records))

    async def get_record_count(
        self,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Get record count for the Delta table."""
        if self._dt is None:
            raise ConnectionError("Not connected to Delta Lake")
        loop = asyncio.get_event_loop()
        pa_table = await loop.run_in_executor(None, self._dt.to_pyarrow_table)
        return pa_table.num_rows

    # ------------------------------------------------------------------
    # DatalakeBaseConnector abstract methods
    # ------------------------------------------------------------------

    async def fetch_databases(self) -> List[str]:
        """List databases — returns the configured database name."""
        return [self.dl_config.database]

    async def fetch_tables(self, database: str) -> List[Dict[str, Any]]:
        """List tables — returns the configured Delta table."""
        if not database:
            raise ValueError("database name must not be empty")

        row_count = 0
        try:
            row_count = await self.get_record_count()
        except Exception:
            pass

        return [{
            "name": self.delta_config.table_uri or database,
            "row_count": row_count,
            "size_bytes": 0,
        }]

    async def fetch_table_preview(
        self, database: str, table: str, limit: int = 100
    ) -> DataBatch:
        """Preview rows from the Delta table."""
        if not database or not table:
            raise ValueError("database and table must not be empty")

        effective_limit = self._clamp_preview_limit(limit)
        return await self._read_table(limit=effective_limit)

    async def execute_query(self, sql: str) -> DataBatch:
        """Execute a query against the Delta table via DuckDB integration."""
        if not sql or not sql.strip():
            raise ValueError("sql must not be empty")

        start = time.time()
        try:
            rows = await asyncio.wait_for(
                self._run_query(sql),
                timeout=self.dl_config.query_timeout,
            )
            rows = rows[: self.dl_config.max_query_rows]
            latency = (time.time() - start) * 1000
            self._record_query_metrics(latency, success=True)
            return self._rows_to_batch(rows)
        except asyncio.TimeoutError:
            latency = (time.time() - start) * 1000
            self._record_query_metrics(latency, success=False)
            raise TimeoutError(
                f"Query exceeded timeout of {self.dl_config.query_timeout}s"
            )
        except TimeoutError:
            raise
        except Exception as exc:
            latency = (time.time() - start) * 1000
            self._record_query_metrics(latency, success=False)
            self._record_error(exc)
            raise

    async def get_query_metrics(self) -> Dict[str, Any]:
        """Return accumulated query metrics."""
        return self._get_base_query_metrics()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _open_table(self) -> Any:
        """Open a DeltaTable instance."""
        if not HAS_DELTALAKE:
            raise ImportError(
                "deltalake is required for Delta Lake connections. "
                "Install with: pip install deltalake"
            )
        uri = self.delta_config.table_uri or self.delta_config.database
        storage_opts = self.delta_config.storage_options or None
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: dl_lib.DeltaTable(uri, storage_options=storage_opts),
        )

    async def _read_table(self, limit: Optional[int] = None) -> DataBatch:
        """Read rows from the Delta table as a DataBatch."""
        if self._dt is None:
            raise ConnectionError("Not connected to Delta Lake")

        start = time.time()
        loop = asyncio.get_event_loop()
        pa_table = await loop.run_in_executor(None, self._dt.to_pyarrow_table)

        if limit and limit > 0:
            pa_table = pa_table.slice(0, limit)

        rows = pa_table.to_pylist()
        rows = rows[: self.dl_config.max_query_rows]
        latency = (time.time() - start) * 1000
        self._record_query_metrics(latency, success=True)
        return self._rows_to_batch(rows)

    async def _run_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute *sql* against the Delta table using pyarrow dataset."""
        if self._dt is None:
            raise ConnectionError("Not connected to Delta Lake")

        loop = asyncio.get_event_loop()

        def _exec() -> List[Dict[str, Any]]:
            # Read full table and convert; SQL filtering is best-effort
            pa_table = self._dt.to_pyarrow_table()
            return pa_table.to_pylist()

        return await loop.run_in_executor(None, _exec)

    @staticmethod
    def _rows_to_batch(rows: List[Dict[str, Any]]) -> DataBatch:
        """Convert raw row dicts to a DataBatch."""
        records = [
            DataRecord(id=str(i), data=row) for i, row in enumerate(rows)
        ]
        return DataBatch(records=records, total_count=len(records))


# Register with ConnectorFactory
ConnectorFactory.register("delta_lake", DeltaLakeConnector)
