"""
Database Connectors for Data Sync Pipeline.

Provides read-only connections to various database types.
"""

from src.sync.pipeline.connectors.base import BaseConnector, ConnectorFactory
from src.sync.pipeline.connectors.postgresql import PostgreSQLConnector
from src.sync.pipeline.connectors.mysql import MySQLConnector
from src.sync.pipeline.connectors.sqlite import SQLiteConnector
from src.sync.pipeline.connectors.oracle import OracleConnector
from src.sync.pipeline.connectors.sqlserver import SQLServerConnector

__all__ = [
    "BaseConnector",
    "ConnectorFactory",
    "PostgreSQLConnector",
    "MySQLConnector",
    "SQLiteConnector",
    "OracleConnector",
    "SQLServerConnector",
]
