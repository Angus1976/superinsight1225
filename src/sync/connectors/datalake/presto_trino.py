"""
Presto/Trino Connector Module.

Provides PrestoTrinoConnector using the trino Python package.
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
    import trino as trino_lib  # noqa: F401

    HAS_TRINO = True
except ImportError:
    HAS_TRINO = False


class PrestoTrinoConfig(DatalakeConnectorConfig):
    """Presto/Trino 连接器配置。"""

    port: int = Field(default=8080, ge=1, le=65535)
    catalog: str = "hive"
    schema_name: Optional[str] = None
    source: str = "datasync"
    http_scheme: str = "http"


class PrestoTrinoConnector(DatalakeBaseConnector):
    """Presto/Trino 连接器，使用 trino Python 包。"""

    def __init__(self, config: PrestoTrinoConfig):
        super().__init__(config)
        self.pt_config = config
        self._connection: Any = None
        self._cursor: Any = None

    # ------------------------------------------------------------------
    # BaseConnector abstract methods
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish connection to Presto/Trino."""
        self._set_status(ConnectionStatus.CONNECTING)
        try:
            self._connection = await self._create_connection()
            self._cursor = self._connection.cursor()
            self._set_status(ConnectionStatus.CONNECTED)
            return True
        except Exception as exc:
            self._record_error(exc)
            self._set_status(ConnectionStatus.ERROR)
            return False

    async def disconnect(self) -> None:
        """Close Presto/Trino connection."""
        try:
            if self._cursor is not None:
                self._cursor.close()
            if self._connection is not None:
                self._connection.close()
        except Exception as exc:
            logger.warning("Error closing Presto/Trino connection: %s", exc)
        finally:
            self._cursor = None
            self._connection = None
        self._set_status(ConnectionStatus.DISCONNECTED)

    async def health_check(self) -> bool:
        """Verify Presto/Trino connection is alive."""
        if not self.is_connected or self._cursor is None:
            return False
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self._cursor.execute("SELECT 1")
            )
            result = await loop.run_in_executor(None, self._cursor.fetchall)
            return len(result) > 0
        except Exception as exc:
            self._record_error(exc)
            return False

    async def fetch_schema(self) -> Dict[str, Any]:
        """Return schema information for the configured database."""
        tables = await self.fetch_tables(self.dl_config.database)
        return {
            "database": self.dl_config.database,
            "tables": tables,
            "connector_type": "presto_trino",
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
        """Fetch data from Presto/Trino."""
        if query:
            return await self.execute_query(query)

        sql = self._build_select_sql(
            table or self.dl_config.database,
            filters=filters,
            limit=limit,
            offset=offset,
        )
        return await self.execute_query(sql)

    async def fetch_data_stream(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None,
    ) -> AsyncIterator[DataBatch]:
        """Stream data from Presto/Trino in batches."""
        batch = await self.fetch_data(
            query=query, table=table, filters=filters, limit=batch_size
        )
        yield batch

    async def write_data(
        self, batch: DataBatch, mode: str = "upsert"
    ) -> SyncResult:
        """Write data to Presto/Trino (stub)."""
        return SyncResult(success=False, records_failed=len(batch.records))

    async def get_record_count(
        self,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Get record count for a table."""
        target = table or self.dl_config.database
        sql = f"SELECT count(*) FROM {target}"
        batch = await self.execute_query(sql)
        if batch.records:
            return int(list(batch.records[0].data.values())[0])
        return 0

    # ------------------------------------------------------------------
    # DatalakeBaseConnector abstract methods
    # ------------------------------------------------------------------

    async def fetch_databases(self) -> List[str]:
        """List schemas (databases) available in the configured catalog."""
        sql = f"SHOW SCHEMAS FROM {self.pt_config.catalog}"
        batch = await self.execute_query(sql)
        return [list(r.data.values())[0] for r in batch.records]

    async def fetch_tables(self, database: str) -> List[Dict[str, Any]]:
        """List tables in *database* with estimated row count and size."""
        if not database:
            raise ValueError("database name must not be empty")

        sql = (
            f"SHOW TABLES FROM {self.pt_config.catalog}.{database}"
        )
        batch = await self.execute_query(sql)
        tables: List[Dict[str, Any]] = []
        for r in batch.records:
            tables.append({
                "name": list(r.data.values())[0],
                "row_count": 0,
                "size_bytes": 0,
            })
        return tables

    async def fetch_table_preview(
        self, database: str, table: str, limit: int = 100
    ) -> DataBatch:
        """Preview rows from *catalog*.*database*.*table*."""
        if not database or not table:
            raise ValueError("database and table must not be empty")

        effective_limit = self._clamp_preview_limit(limit)
        fqn = f"{self.pt_config.catalog}.{database}.{table}"
        sql = f"SELECT * FROM {fqn} LIMIT {effective_limit}"
        return await self.execute_query(sql)

    async def execute_query(self, sql: str) -> DataBatch:
        """Execute a SQL query with timeout and row-limit protection."""
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

    async def _create_connection(self) -> Any:
        """Create a trino connection."""
        if not HAS_TRINO:
            raise ImportError(
                "trino is required for Presto/Trino connections. "
                "Install with: pip install trino"
            )
        http_scheme = "https" if self.pt_config.use_ssl else "http"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: trino_lib.dbapi.connect(
                host=self.pt_config.host,
                port=self.pt_config.port,
                user=self.pt_config.username,
                catalog=self.pt_config.catalog,
                schema=self.pt_config.schema_name or self.pt_config.database,
                http_scheme=http_scheme,
                source=self.pt_config.source,
            ),
        )

    async def _run_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute *sql* and return rows as list of dicts."""
        if self._cursor is None:
            raise ConnectionError("Not connected to Presto/Trino")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._cursor.execute(sql))
        columns = [desc[0] for desc in self._cursor.description or []]
        raw_rows = await loop.run_in_executor(None, self._cursor.fetchall)
        return [dict(zip(columns, row)) for row in raw_rows]

    @staticmethod
    def _rows_to_batch(rows: List[Dict[str, Any]]) -> DataBatch:
        """Convert raw row dicts to a DataBatch."""
        records = [
            DataRecord(id=str(i), data=row) for i, row in enumerate(rows)
        ]
        return DataBatch(records=records, total_count=len(records))

    @staticmethod
    def _build_select_sql(
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> str:
        """Build a simple SELECT statement."""
        sql = f"SELECT * FROM {table}"
        if filters:
            clauses = [f"{k} = '{v}'" for k, v in filters.items()]
            sql += " WHERE " + " AND ".join(clauses)
        if limit:
            sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"
        return sql


# Register with ConnectorFactory
ConnectorFactory.register("presto_trino", PrestoTrinoConnector)
