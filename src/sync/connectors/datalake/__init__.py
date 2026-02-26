"""
Datalake/Warehouse Connectors Module.

Provides connectors for datalake and data warehouse systems including
Hive, ClickHouse, Doris/StarRocks, Spark SQL, Presto/Trino, Delta Lake, and Iceberg.
"""

from src.sync.connectors.datalake.base import (
    DatalakeConnectorConfig,
    DatalakeBaseConnector,
)
from src.sync.connectors.datalake.models import (
    DatalakeMetricsModel,
    VALID_METRIC_TYPES,
)
from src.sync.connectors.datalake.monitoring import (
    DatalakeMonitoringService,
    datalake_monitoring_service,
    get_datalake_monitoring_service,
)
from src.sync.connectors.datalake.schemas import (
    DatalakeSourceCreate,
    DatalakeSourceUpdate,
    DatalakeSourceResponse,
    ConnectionTestResult,
    SourceSummary,
    DashboardOverview,
    SourceHealthStatus,
    VolumeDataPoint,
    VolumeTrendData,
    SourceQueryStats,
    QueryPerformanceData,
    FlowNode,
    FlowEdge,
    DataFlowGraph,
)
from src.sync.connectors.datalake.clickhouse import (
    ClickHouseConfig,
    ClickHouseConnector,
)
from src.sync.connectors.datalake.delta_lake import (
    DeltaLakeConfig,
    DeltaLakeConnector,
)
from src.sync.connectors.datalake.doris import (
    DorisConfig,
    DorisConnector,
)
from src.sync.connectors.datalake.hive import (
    HiveConfig,
    HiveConnector,
)
from src.sync.connectors.datalake.iceberg import (
    IcebergConfig,
    IcebergConnector,
)
from src.sync.connectors.datalake.presto_trino import (
    PrestoTrinoConfig,
    PrestoTrinoConnector,
)
from src.sync.connectors.datalake.spark_sql import (
    SparkSQLConfig,
    SparkSQLConnector,
)

__all__ = [
    "DatalakeConnectorConfig",
    "DatalakeBaseConnector",
    "DatalakeMetricsModel",
    "VALID_METRIC_TYPES",
    # Monitoring
    "DatalakeMonitoringService",
    "datalake_monitoring_service",
    "get_datalake_monitoring_service",
    # Schemas
    "DatalakeSourceCreate",
    "DatalakeSourceUpdate",
    "DatalakeSourceResponse",
    "ConnectionTestResult",
    "SourceSummary",
    "DashboardOverview",
    "SourceHealthStatus",
    "VolumeDataPoint",
    "VolumeTrendData",
    "SourceQueryStats",
    "QueryPerformanceData",
    "FlowNode",
    "FlowEdge",
    "DataFlowGraph",
    # Connectors
    "ClickHouseConfig",
    "ClickHouseConnector",
    "DeltaLakeConfig",
    "DeltaLakeConnector",
    "DorisConfig",
    "DorisConnector",
    "HiveConfig",
    "HiveConnector",
    "IcebergConfig",
    "IcebergConnector",
    "PrestoTrinoConfig",
    "PrestoTrinoConnector",
    "SparkSQLConfig",
    "SparkSQLConnector",
]
