"""
Database Connectors Module.

Provides connectors for various database systems with enterprise-grade features.
"""

from src.sync.connectors.database.postgresql import PostgreSQLConnector
from src.sync.connectors.database.mysql import MySQLConnector
from src.sync.connectors.database.oracle import OracleConnector
from src.sync.connectors.database.sqlserver import SQLServerConnector
from src.sync.connectors.database.pool_manager import (
    DatabaseConnectionPool,
    PoolManager,
    PoolConfig,
    FailoverStrategy,
    pool_manager
)
from src.sync.connectors.database.health_monitor import (
    DatabaseHealthMonitor,
    HealthMonitorConfig,
    HealthStatus,
    AlertSeverity
)

__all__ = [
    "PostgreSQLConnector",
    "MySQLConnector", 
    "OracleConnector",
    "SQLServerConnector",
    "DatabaseConnectionPool",
    "PoolManager",
    "PoolConfig",
    "FailoverStrategy",
    "pool_manager",
    "DatabaseHealthMonitor",
    "HealthMonitorConfig",
    "HealthStatus",
    "AlertSeverity",
]
