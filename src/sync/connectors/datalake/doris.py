"""
Doris/StarRocks Connector Module.

Provides DorisConnector supporting MySQL-compatible protocol
with Doris and StarRocks compatibility modes.
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
    import aiomysql  # noqa: F401

    HAS_AIOMYSQL = True
except ImportError:
    HAS_AIOMYSQL = False

try:
    import pymysql  # noqa: F401

    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False


class DorisConfig(DatalakeConnectorConfig):
    """Doris/StarRocks 连接器配置。"""

    port: int = Field(default=9030, ge=1, le=65535)
    http_port: int = Field(default=8030, ge=1, le=65535)
    backend_port: int = Field(default=8040, ge=1, le=65535)
    compatible_mode: str = "doris"  # doris | starrocks


class DorisConnector(DatalakeBaseConnector):
    """Doris/StarRocks 连接器，兼容 MySQL 协议。"""

    def __init__(self, config: DorisConfig):
        super().__init__(config)
        self.doris_config = config
        self._connection: Any = None
        self._pool: Any = None

    @property
    def _is_starrocks(self) -> bool:
        return self.doris_config.compatible_mode == "starrocks"

    # ------------------------------------------------------------------
    # BaseConnector abstract methods
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish MySQL-protocol connection to Doris/StarRocks."""
        self._set_status(ConnectionStatus.CONNECTING)
        try:
            self._connection = await self._create_connection()
            self._set_status(ConnectionStatus.CONNECTED)
            return True
        except Exception as exc:
            self._record_error(exc)
            self._set_status(ConnectionStatus.ERROR)
            return False

    async def disconnect(self) -> None:
        """Close Doris/StarRocks connection."""
        try:
            if self._pool is not None:
                self._pool.close()
                await self._pool.wait_closed()
            elif self._connection is not None:
                if hasattr(self._connection, "close"):
                    self._connection.close()
        except Exception as exc:
            logger.warning("Error closing Doris connection: %s", exc)
        finally:
            self._connection = None
            self._pool = None
        self._set_status(ConnectionStatus.DISCONNECTED)

    async def health_check(self) -> bool:
        """Verify Doris/StarRocks connection is alive."""
        if not self.is_connected:
            return False
        try:
            batch = await self.execute_query("SELECT 1")
            return len(batch.records) > 0
        except Exception as exc:
            self._record_error(exc)
            return False

    async def fetch_schema(self) -> Dict[str, Any]:
        """Return schema information for the configured database."""
        tables = await self.fetch_tables(self.dl_config.database)
        mode = self.doris_config.compatible_mode
        return {
            "database": self.dl_config.database,
            "tables": tables,
            "connector_type": f"doris ({mode})",
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
        """Fetch data from Doris/StarRocks."""
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
        """Stream data from Doris/StarRocks in batches."""
        batch = await self.fetch_data(
            query=query, table=table, filters=filters, limit=batch_size
        )
        yield batch

    async def write_data(
        self, batch: DataBatch, mode: str = "upsert"
    ) -> SyncResult:
        """Write data to Doris/StarRocks (stub)."""
        return SyncResult(success=False, records_failed=len(batch.records))

    async def get_record_count(
        self,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Get record count for a table."""
        target = table or self.dl_config.database
        sql = f"SELECT count(*) AS cnt FROM {target}"
        batch = await self.execute_query(sql)
        if batch.records:
            return int(list(batch.records[0].data.values())[0])
        return 0

    # ------------------------------------------------------------------
    # DatalakeBaseConnector abstract methods
    # ------------------------------------------------------------------

    async def fetch_databases(self) -> List[str]:
        """List databases available on the Doris/StarRocks server."""
        batch = await self.execute_query("SHOW DATABASES")
        return [list(r.data.values())[0] for r in batch.records]

    async def fetch_tables(self, database: str) -> List[Dict[str, Any]]:
        """List tables in *database* with estimated row count and size."""
        if not database:
            raise ValueError("database name must not be empty")

        sql = (
            "SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH "
            "FROM information_schema.TABLES "
            f"WHERE TABLE_SCHEMA = '{database}'"
        )
        batch = await self.execute_query(sql)
        return [
            {
                "name": r.data.get("TABLE_NAME", ""),
                "row_count": int(r.data.get("TABLE_ROWS", 0) or 0),
                "size_bytes": int(r.data.get("DATA_LENGTH", 0) or 0),
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

    async def _create_connection(self) -> Any:
        """Create a MySQL-protocol connection to Doris/StarRocks."""
        if HAS_AIOMYSQL:
            return await self._create_async_connection()
        if HAS_PYMYSQL:
            return self._create_sync_connection()
        raise ImportError(
            "aiomysql or pymysql is required for Doris/StarRocks. "
            "Install with: pip install aiomysql  or  pip install pymysql"
        )

    async def _create_async_connection(self) -> Any:
        """Create an aiomysql connection pool."""
        self._pool = await aiomysql.create_pool(
            host=self.doris_config.host,
            port=self.doris_config.port,
            user=self.doris_config.username,
            password=self.doris_config.password,
            db=self.doris_config.database,
            connect_timeout=self.config.connection_timeout,
            minsize=1,
            maxsize=self.config.pool_size,
        )
        return self._pool

    def _create_sync_connection(self) -> Any:
        """Create a pymysql connection (sync fallback)."""
        return pymysql.connect(
            host=self.doris_config.host,
            port=self.doris_config.port,
            user=self.doris_config.username,
            password=self.doris_config.password,
            database=self.doris_config.database,
            connect_timeout=self.config.connection_timeout,
            cursorclass=pymysql.cursors.DictCursor,
        )

    async def _run_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute *sql* and return rows as list of dicts."""
        if self._pool is not None and HAS_AIOMYSQL:
            return await self._run_query_async(sql)
        if self._connection is not None and HAS_PYMYSQL:
            return await self._run_query_sync(sql)
        raise ConnectionError("Not connected to Doris/StarRocks")

    async def _run_query_async(self, sql: str) -> List[Dict[str, Any]]:
        """Execute via aiomysql pool."""
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                return await cur.fetchall()

    async def _run_query_sync(self, sql: str) -> List[Dict[str, Any]]:
        """Execute via pymysql (sync, run in executor)."""
        loop = asyncio.get_event_loop()

        def _exec() -> List[Dict[str, Any]]:
            with self._connection.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()

        return await loop.run_in_executor(None, _exec)

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
ConnectorFactory.register("doris", DorisConnector)
