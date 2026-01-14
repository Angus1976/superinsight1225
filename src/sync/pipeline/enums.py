"""
Enumerations for Data Sync Pipeline.
"""

from enum import Enum


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"


class ConnectionMethod(str, Enum):
    """Database connection methods."""
    JDBC = "jdbc"
    ODBC = "odbc"


class SaveStrategy(str, Enum):
    """Data save strategies."""
    PERSISTENT = "persistent"
    MEMORY = "memory"
    HYBRID = "hybrid"


class DataFormat(str, Enum):
    """Supported data formats for receiving."""
    JSON = "json"
    CSV = "csv"


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"
    COCO = "coco"
    PASCAL_VOC = "pascal_voc"


class JobStatus(str, Enum):
    """Sync job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
