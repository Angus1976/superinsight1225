"""
ClickHouse Connector Module.

Provides ClickHouseConnector supporting HTTP and Native protocols.
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

# Optional driver imports
try:
    import clickhouse_connect  # noqa: F401

    HAS_CLICKHOUSE_HTTP = True
except ImportError:
    HAS_CLICKHOUSE_HTTP = False

try:
    from clickhouse_driver import Client as NativeClient  # noqa: F401

    HAS_CLICKHOUSE_NATIVE = True
except ImportError:
    HAS_CLICKHOUSE_NATIVE = False


class ClickHouseConfig(DatalakeConnectorConfig):
    """ClickHouse 连接器配置。"""

    port: int = Field(default=9000, ge=1, le=65535)
    http_port: int = Field(default=8123, ge=1, le=65535)
    use_http: bool = True
    cluster: Optional[str] = None


class ClickHouseConnector(DatalakeBaseConnector):
    """ClickHouse 连接器，支持 HTTP 和 Native 协议。"""

    def __init__(self, config: ClickHouseConfig):
        super().__init__(config)
        self.ck_config = config
        self._client: Any = None

    # ------------------------------------------------------------------
    # BaseConnector abstract methods
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish connection to ClickHouse."""
        self._set_status(ConnectionStatus.CONNECTING)
        try:
            if self.ck_config.use_http:
                self._client = await self._connect_http()
            else:
                self._client = await self._connect_native()
            self._set_status(ConnectionStatus.CONNECTED)
            return True
        except Exception as exc:
            self._record_error(exc)
            self._set_status(ConnectionStatus.ERROR)
            return False

    async def disconnect(self) -> None:
        """Close ClickHouse connection."""
        if self._client is not None:
            try:
                if hasattr(self._client, "close"):
                    self._client.close()
            except Exception as exc:
                logger.warning("Error closing ClickHouse connection: %s", exc)
            finally:
                self._client = None
        self._set_status(ConnectionStatus.DISCONNECTED)

    async def health_check(self) -> bool:
        """Ping ClickHouse to verify connection health."""
        if not self.is_connected or self._client is None:
            return False
        try:
            if self.ck_config.use_http and HAS_CLICKHOUSE_HTTP:
                result = self._client.query("SELECT 1")
                return result is not None
            if HAS_CLICKHOUSE_NATIVE:
                result = self._client.execute("SELECT 1")
                return result is not None
            return False
        except Exception as exc:
            self._record_error(exc)
            return False

    async def fetch_schema(self) -> Dict[str, Any]:
        """Return schema information for the configured database."""
        tables = await self.fetch_tables(self.dl_config.database)
        return {
            "database": self.dl_config.database,
            "tables": tables,
            "connector_type": "clickhouse",
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
        """Fetch data from ClickHouse."""
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
        """Stream data from ClickHouse in batches."""
        batch = await self.fetch_data(query=query, table=table, filters=filters, limit=batch_size)
        yield batch

    async def write_data(self, batch: DataBatch, mode: str = "upsert") -> SyncResult:
        """Write data to ClickHouse (stub)."""
        return SyncResult(success=False, records_failed=len(batch.records))

    async def get_record_count(
        self, table: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Get record count for a table."""
        target = table or self.dl_config.database
        sql = f"SELECT count() FROM {target}"
        batch = await self.execute_query(sql)
        if batch.records:
            count_val = list(batch.records[0].data.values())[0]
            return int(count_val)
        return 0

    # ------------------------------------------------------------------
    # DatalakeBaseConnector abstract methods
    # ------------------------------------------------------------------

    async def fetch_databases(self) -> List[str]:
        """List databases available on the ClickHouse server."""
        batch = await self.execute_query("SHOW DATABASES")
        return [list(r.data.values())[0] for r in batch.records]

    async def fetch_tables(self, database: str) -> List[Dict[str, Any]]:
        """List tables in *database* with estimated row count and size."""
        if not database:
            raise ValueError("database name must not be empty")

        sql = (
            "SELECT name, total_rows, total_bytes "
            "FROM system.tables "
            f"WHERE database = '{database}'"
        )
        batch = await self.execute_query(sql)
        return [
            {
                "name": r.data.get("name", ""),
                "row_count": int(r.data.get("total_rows", 0) or 0),
                "size_bytes": int(r.data.get("total_bytes", 0) or 0),
            }
            for r in batch.records
        ]

    async def fetch_table_preview(
        self, database: str, table: str, limit: int = 100
    ) -> DataBatch:
        """Preview rows from *database*.*table*."""
        if not database or not table:
            raise ValueError("database and table must not be empty")

        effective_limit = self._clamp_preview_limit(limit)
        sql = f"SELECT * FROM {database}.{table} LIMIT {effective_limit}"
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

    async def _connect_http(self) -> Any:
        """Create an HTTP client via clickhouse-connect."""
        if not HAS_CLICKHOUSE_HTTP:
            raise ImportError(
                "clickhouse-connect is required for HTTP mode. "
                "Install with: pip install clickhouse-connect"
            )
        client = clickhouse_connect.get_client(
            host=self.ck_config.host,
            port=self.ck_config.http_port,
            username=self.ck_config.username,
            password=self.ck_config.password,
            database=self.ck_config.database,
            secure=self.ck_config.use_ssl,
            connect_timeout=self.config.connection_timeout,
            send_receive_timeout=self.config.read_timeout,
        )
        return client

    async def _connect_native(self) -> Any:
        """Create a Native-protocol client via clickhouse-driver."""
        if not HAS_CLICKHOUSE_NATIVE:
            raise ImportError(
                "clickhouse-driver is required for Native mode. "
                "Install with: pip install clickhouse-driver"
            )
        client = NativeClient(
            host=self.ck_config.host,
            port=self.ck_config.port,
            user=self.ck_config.username,
            password=self.ck_config.password,
            database=self.ck_config.database,
            secure=self.ck_config.use_ssl,
            connect_timeout=self.config.connection_timeout,
        )
        return client

    async def _run_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute *sql* and return rows as list of dicts."""
        if self._client is None:
            raise ConnectionError("Not connected to ClickHouse")

        loop = asyncio.get_event_loop()

        if self.ck_config.use_http and HAS_CLICKHOUSE_HTTP:
            result = await loop.run_in_executor(
                None, lambda: self._client.query(sql)
            )
            columns = result.column_names
            return [dict(zip(columns, row)) for row in result.result_rows]

        if HAS_CLICKHOUSE_NATIVE:
            result = await loop.run_in_executor(
                None,
                lambda: self._client.execute(sql, with_column_types=True),
            )
            rows_data, col_types = result
            columns = [c[0] for c in col_types]
            return [dict(zip(columns, row)) for row in rows_data]

        raise ConnectionError("No ClickHouse driver available")

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
ConnectorFactory.register("clickhouse", ClickHouseConnector)
