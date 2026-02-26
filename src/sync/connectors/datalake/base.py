"""
Datalake/Warehouse Base Connector Module.

Provides abstract base class and common configuration for datalake/warehouse connectors.
Extends BaseConnector with schema browsing, query execution, and metrics capabilities.
"""

import logging
from abc import abstractmethod
from typing import Any, Dict, List

from pydantic import Field

from src.sync.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    DataBatch,
)

logger = logging.getLogger(__name__)

# Preview row limits
DEFAULT_PREVIEW_LIMIT = 100
MAX_PREVIEW_LIMIT = 1000


class DatalakeConnectorConfig(ConnectorConfig):
    """数据湖/数仓连接器通用配置。

    Extends ConnectorConfig with connection credentials and
    query safety limits for datalake/warehouse systems.
    """

    host: str
    port: int = Field(ge=1, le=65535)
    database: str
    username: str
    password: str
    use_ssl: bool = False
    query_timeout: int = Field(default=300, ge=1, description="查询超时（秒）")
    max_query_rows: int = Field(
        default=100000, ge=1, description="单次查询最大行数"
    )


class DatalakeBaseConnector(BaseConnector):
    """数据湖/数仓连接器基类，扩展 BaseConnector。

    Provides abstract interface for:
    - Database/table schema browsing
    - Table data preview with row limits
    - SQL query execution with timeout protection
    - Query performance metrics collection

    Subclasses must implement all abstract methods from both
    BaseConnector and this class.
    """

    def __init__(self, config: DatalakeConnectorConfig):
        super().__init__(config)
        self.dl_config = config
        self._query_metrics: Dict[str, Any] = {
            "total_queries": 0,
            "failed_queries": 0,
            "total_latency_ms": 0.0,
            "last_query_latency_ms": 0.0,
        }

    @abstractmethod
    async def fetch_databases(self) -> List[str]:
        """获取可用数据库列表。

        Returns:
            List of database names available on this connection.

        Raises:
            ConnectionError: If not connected to the data source.
        """
        pass

    @abstractmethod
    async def fetch_tables(self, database: str) -> List[Dict[str, Any]]:
        """获取指定数据库的表列表，含行数和大小估算。

        Args:
            database: Target database name.

        Returns:
            List of table info dicts, each containing at minimum:
            - name (str): Table name
            - row_count (int): Estimated row count
            - size_bytes (int): Estimated size in bytes

        Raises:
            ConnectionError: If not connected to the data source.
            ValueError: If database name is empty.
        """
        pass

    @abstractmethod
    async def fetch_table_preview(
        self, database: str, table: str, limit: int = DEFAULT_PREVIEW_LIMIT
    ) -> DataBatch:
        """预览表数据。

        The effective limit is clamped to min(limit, max_query_rows, MAX_PREVIEW_LIMIT).

        Args:
            database: Target database name.
            table: Target table name.
            limit: Maximum rows to return (default 100, max 1000).

        Returns:
            DataBatch containing preview records.

        Raises:
            ConnectionError: If not connected to the data source.
            ValueError: If database or table name is empty.
        """
        pass

    @abstractmethod
    async def execute_query(self, sql: str) -> DataBatch:
        """执行自定义 SQL 查询。

        Implementations must:
        - Enforce query_timeout from config (cancel on timeout).
        - Limit returned rows to max_query_rows from config.
        - Use parameterized queries where applicable to prevent SQL injection.
        - Record query metrics via _record_query_metrics().

        Args:
            sql: SQL query string to execute.

        Returns:
            DataBatch containing query results.

        Raises:
            ConnectionError: If not connected to the data source.
            TimeoutError: If query exceeds query_timeout.
            ValueError: If sql is empty.
        """
        pass

    @abstractmethod
    async def get_query_metrics(self) -> Dict[str, Any]:
        """获取查询性能指标。

        Returns:
            Dict containing at minimum:
            - total_queries (int): Total queries executed
            - failed_queries (int): Number of failed queries
            - avg_latency_ms (float): Average query latency in ms
            - last_query_latency_ms (float): Last query latency in ms
        """
        pass

    def _clamp_preview_limit(self, limit: int) -> int:
        """Clamp preview limit to safe bounds.

        Args:
            limit: Requested row limit.

        Returns:
            Effective limit, no greater than MAX_PREVIEW_LIMIT
            or max_query_rows from config.
        """
        if limit <= 0:
            return DEFAULT_PREVIEW_LIMIT
        return min(limit, MAX_PREVIEW_LIMIT, self.dl_config.max_query_rows)

    def _record_query_metrics(
        self, latency_ms: float, success: bool = True
    ) -> None:
        """Record metrics for a completed query.

        Args:
            latency_ms: Query execution time in milliseconds.
            success: Whether the query succeeded.
        """
        self._query_metrics["total_queries"] += 1
        self._query_metrics["total_latency_ms"] += latency_ms
        self._query_metrics["last_query_latency_ms"] = latency_ms
        if not success:
            self._query_metrics["failed_queries"] += 1

    def _get_base_query_metrics(self) -> Dict[str, Any]:
        """Build base query metrics dict from accumulated stats.

        Returns:
            Dict with total_queries, failed_queries, avg_latency_ms,
            and last_query_latency_ms.
        """
        total = self._query_metrics["total_queries"]
        avg = (
            self._query_metrics["total_latency_ms"] / total
            if total > 0
            else 0.0
        )
        return {
            "total_queries": total,
            "failed_queries": self._query_metrics["failed_queries"],
            "avg_latency_ms": round(avg, 2),
            "last_query_latency_ms": self._query_metrics[
                "last_query_latency_ms"
            ],
        }
