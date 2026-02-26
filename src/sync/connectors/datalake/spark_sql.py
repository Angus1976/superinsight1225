"""
Spark SQL Connector Module.

Provides SparkSQLConnector supporting Spark Thrift Server (HiveServer2 protocol).
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
    from pyhive import hive as pyhive_hive  # noqa: F401

    HAS_PYHIVE = True
except ImportError:
    HAS_PYHIVE = False

try:
    from pyspark.sql import SparkSession  # noqa: F401

    HAS_PYSPARK = True
except ImportError:
    HAS_PYSPARK = False


class SparkSQLConfig(DatalakeConnectorConfig):
    """Spark SQL 连接器配置。"""

    port: int = Field(default=10000, ge=1, le=65535)
    use_thrift: bool = True
    spark_master: Optional[str] = None
    app_name: str = "DataSync-SparkSQL"


class SparkSQLConnector(DatalakeBaseConnector):
    """Spark SQL 连接器，支持 Thrift Server 和 PySpark 模式。"""

    def __init__(self, config: SparkSQLConfig):
        super().__init__(config)
        self.spark_config = config
        self._cursor: Any = None
        self._connection: Any = None
        self._spark: Any = None

    # ------------------------------------------------------------------
    # BaseConnector abstract methods
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish connection to Spark SQL."""
        self._set_status(ConnectionStatus.CONNECTING)
        try:
            if self.spark_config.use_thrift:
                self._connection = await self._connect_thrift()
                self._cursor = self._connection.cursor()
            else:
                self._spark = await self._connect_pyspark()
            self._set_status(ConnectionStatus.CONNECTED)
            return True
        except Exception as exc:
            self._record_error(exc)
            self._set_status(ConnectionStatus.ERROR)
            return False

    async def disconnect(self) -> None:
        """Close Spark SQL connection."""
        try:
            if self._cursor is not None:
                self._cursor.close()
            if self._connection is not None:
                self._connection.close()
            if self._spark is not None:
                self._spark.stop()
        except Exception as exc:
            logger.warning("Error closing Spark SQL connection: %s", exc)
        finally:
            self._cursor = None
            self._connection = None
            self._spark = None
        self._set_status(ConnectionStatus.DISCONNECTED)

    async def health_check(self) -> bool:
        """Verify Spark SQL connection is alive."""
        if not self.is_connected:
            return False
        try:
            if self._cursor is not None:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, lambda: self._cursor.execute("SELECT 1")
                )
                return True
            if self._spark is not None:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: self._spark.sql("SELECT 1").collect()
                )
                return len(result) > 0
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
            "connector_type": "spark_sql",
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
        """Fetch data from Spark SQL."""
        if query:
            return await self.execute_query(query)

        sql = self._build_select_sql(
            table or self.dl_config.database,
            filters=filters,
            limit=limit,
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
        """Stream data from Spark SQL in batches."""
        batch = await self.fetch_data(
            query=query, table=table, filters=filters, limit=batch_size
        )
        yield batch

    async def write_data(
        self, batch: DataBatch, mode: str = "upsert"
    ) -> SyncResult:
        """Write data to Spark SQL (stub)."""
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
        """List databases available on the Spark SQL server."""
        batch = await self.execute_query("SHOW DATABASES")
        return [list(r.data.values())[0] for r in batch.records]

    async def fetch_tables(self, database: str) -> List[Dict[str, Any]]:
        """List tables in *database* with estimated row count and size."""
        if not database:
            raise ValueError("database name must not be empty")

        batch = await self.execute_query(f"SHOW TABLES IN {database}")
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

    async def _connect_thrift(self) -> Any:
        """Create a Thrift connection via pyhive."""
        if not HAS_PYHIVE:
            raise ImportError(
                "pyhive is required for Spark SQL Thrift mode. "
                "Install with: pip install pyhive[hive]"
            )
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: pyhive_hive.Connection(
                host=self.spark_config.host,
                port=self.spark_config.port,
                username=self.spark_config.username,
                password=self.spark_config.password,
                database=self.spark_config.database,
            ),
        )

    async def _connect_pyspark(self) -> Any:
        """Create a PySpark SparkSession."""
        if not HAS_PYSPARK:
            raise ImportError(
                "pyspark is required for PySpark mode. "
                "Install with: pip install pyspark"
            )
        loop = asyncio.get_event_loop()

        def _build_session() -> Any:
            builder = SparkSession.builder.appName(
                self.spark_config.app_name
            )
            if self.spark_config.spark_master:
                builder = builder.master(self.spark_config.spark_master)
            return builder.enableHiveSupport().getOrCreate()

        return await loop.run_in_executor(None, _build_session)

    async def _run_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute *sql* and return rows as list of dicts."""
        if self._cursor is not None:
            return await self._run_query_thrift(sql)
        if self._spark is not None:
            return await self._run_query_pyspark(sql)
        raise ConnectionError("Not connected to Spark SQL")

    async def _run_query_thrift(self, sql: str) -> List[Dict[str, Any]]:
        """Execute via Thrift cursor."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._cursor.execute(sql))
        columns = [desc[0] for desc in self._cursor.description or []]
        raw_rows = await loop.run_in_executor(None, self._cursor.fetchall)
        return [dict(zip(columns, row)) for row in raw_rows]

    async def _run_query_pyspark(self, sql: str) -> List[Dict[str, Any]]:
        """Execute via PySpark SparkSession."""
        loop = asyncio.get_event_loop()

        def _exec() -> List[Dict[str, Any]]:
            df = self._spark.sql(sql)
            columns = df.columns
            rows = df.collect()
            return [dict(zip(columns, row)) for row in rows]

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
    ) -> str:
        """Build a simple SELECT statement."""
        sql = f"SELECT * FROM {table}"
        if filters:
            clauses = [f"{k} = '{v}'" for k, v in filters.items()]
            sql += " WHERE " + " AND ".join(clauses)
        if limit:
            sql += f" LIMIT {limit}"
        return sql


# Register with ConnectorFactory
ConnectorFactory.register("spark_sql", SparkSQLConnector)
