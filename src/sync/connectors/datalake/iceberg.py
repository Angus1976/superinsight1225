"""
Apache Iceberg Connector Module.

Provides IcebergConnector using the pyiceberg Python package.
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
    from pyiceberg.catalog import load_catalog  # noqa: F401

    HAS_PYICEBERG = True
except ImportError:
    HAS_PYICEBERG = False


class IcebergConfig(DatalakeConnectorConfig):
    """Apache Iceberg 连接器配置。"""

    port: int = Field(default=8181, ge=1, le=65535)
    catalog_name: str = "default"
    catalog_type: str = "rest"  # rest, hive, glue
    warehouse: Optional[str] = None
    catalog_properties: Dict[str, str] = Field(default_factory=dict)


class IcebergConnector(DatalakeBaseConnector):
    """Apache Iceberg 连接器，使用 pyiceberg 包。"""

    def __init__(self, config: IcebergConfig):
        super().__init__(config)
        self.ice_config = config
        self._catalog: Any = None

    # ------------------------------------------------------------------
    # BaseConnector abstract methods
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Load the Iceberg catalog."""
        self._set_status(ConnectionStatus.CONNECTING)
        try:
            self._catalog = await self._load_catalog()
            self._set_status(ConnectionStatus.CONNECTED)
            return True
        except Exception as exc:
            self._record_error(exc)
            self._set_status(ConnectionStatus.ERROR)
            return False

    async def disconnect(self) -> None:
        """Release catalog reference."""
        self._catalog = None
        self._set_status(ConnectionStatus.DISCONNECTED)

    async def health_check(self) -> bool:
        """Verify the Iceberg catalog is accessible."""
        if not self.is_connected or self._catalog is None:
            return False
        try:
            loop = asyncio.get_event_loop()
            namespaces = await loop.run_in_executor(
                None, self._catalog.list_namespaces
            )
            return isinstance(namespaces, (list, tuple))
        except Exception as exc:
            self._record_error(exc)
            return False

    async def fetch_schema(self) -> Dict[str, Any]:
        """Return schema information for the configured database."""
        tables = await self.fetch_tables(self.dl_config.database)
        return {
            "database": self.dl_config.database,
            "tables": tables,
            "connector_type": "iceberg",
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
        """Fetch data from an Iceberg table."""
        if query:
            return await self.execute_query(query)

        target = table or self.dl_config.database
        return await self._read_iceberg_table(
            self.dl_config.database, target, limit=limit
        )

    async def fetch_data_stream(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None,
    ) -> AsyncIterator[DataBatch]:
        """Stream data from Iceberg in batches."""
        batch = await self.fetch_data(
            query=query, table=table, limit=batch_size
        )
        yield batch

    async def write_data(
        self, batch: DataBatch, mode: str = "upsert"
    ) -> SyncResult:
        """Write data to Iceberg (stub)."""
        return SyncResult(success=False, records_failed=len(batch.records))

    async def get_record_count(
        self,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Get record count for an Iceberg table."""
        target = table or self.dl_config.database
        batch = await self._read_iceberg_table(
            self.dl_config.database, target, limit=None
        )
        return batch.total_count

    # ------------------------------------------------------------------
    # DatalakeBaseConnector abstract methods
    # ------------------------------------------------------------------

    async def fetch_databases(self) -> List[str]:
        """List namespaces (databases) in the Iceberg catalog."""
        if self._catalog is None:
            raise ConnectionError("Not connected to Iceberg")

        loop = asyncio.get_event_loop()
        namespaces = await loop.run_in_executor(
            None, self._catalog.list_namespaces
        )
        return [".".join(ns) for ns in namespaces]

    async def fetch_tables(self, database: str) -> List[Dict[str, Any]]:
        """List tables in *database* namespace."""
        if not database:
            raise ValueError("database name must not be empty")
        if self._catalog is None:
            raise ConnectionError("Not connected to Iceberg")

        loop = asyncio.get_event_loop()
        table_ids = await loop.run_in_executor(
            None, lambda: self._catalog.list_tables(database)
        )
        tables: List[Dict[str, Any]] = []
        for tid in table_ids:
            name = tid[-1] if isinstance(tid, tuple) else str(tid)
            tables.append({
                "name": name,
                "row_count": 0,
                "size_bytes": 0,
            })
        return tables

    async def fetch_table_preview(
        self, database: str, table: str, limit: int = 100
    ) -> DataBatch:
        """Preview rows from an Iceberg table."""
        if not database or not table:
            raise ValueError("database and table must not be empty")

        effective_limit = self._clamp_preview_limit(limit)
        return await self._read_iceberg_table(
            database, table, limit=effective_limit
        )

    async def execute_query(self, sql: str) -> DataBatch:
        """Execute a query — reads the referenced table via catalog scan."""
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

    async def _load_catalog(self) -> Any:
        """Load an Iceberg catalog via pyiceberg."""
        if not HAS_PYICEBERG:
            raise ImportError(
                "pyiceberg is required for Iceberg connections. "
                "Install with: pip install pyiceberg"
            )
        properties: Dict[str, str] = {
            "uri": f"http://{self.ice_config.host}:{self.ice_config.port}",
            "type": self.ice_config.catalog_type,
            **self.ice_config.catalog_properties,
        }
        if self.ice_config.warehouse:
            properties["warehouse"] = self.ice_config.warehouse

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: load_catalog(
                self.ice_config.catalog_name, **properties
            ),
        )

    async def _read_iceberg_table(
        self, database: str, table: str, limit: Optional[int] = None
    ) -> DataBatch:
        """Read rows from an Iceberg table as a DataBatch."""
        if self._catalog is None:
            raise ConnectionError("Not connected to Iceberg")

        start = time.time()
        loop = asyncio.get_event_loop()

        def _scan() -> List[Dict[str, Any]]:
            tbl = self._catalog.load_table(f"{database}.{table}")
            scan = tbl.scan()
            if limit and limit > 0:
                scan = scan.limit(limit)
            pa_table = scan.to_arrow()
            return pa_table.to_pylist()

        rows = await loop.run_in_executor(None, _scan)
        rows = rows[: self.dl_config.max_query_rows]
        latency = (time.time() - start) * 1000
        self._record_query_metrics(latency, success=True)
        return self._rows_to_batch(rows)

    async def _run_query(self, sql: str) -> List[Dict[str, Any]]:
        """Best-effort query execution — scans the configured table."""
        if self._catalog is None:
            raise ConnectionError("Not connected to Iceberg")

        loop = asyncio.get_event_loop()

        def _exec() -> List[Dict[str, Any]]:
            tbl = self._catalog.load_table(
                f"{self.dl_config.database}.{self.dl_config.database}"
            )
            pa_table = tbl.scan().to_arrow()
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
ConnectorFactory.register("iceberg", IcebergConnector)
