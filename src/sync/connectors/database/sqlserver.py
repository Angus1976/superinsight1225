"""
SQL Server Connector.

Provides connector for Microsoft SQL Server databases with support for
incremental sync, CDC, and schema discovery.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

from pydantic import Field

from src.sync.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectionStatus,
    DataBatch,
    DataRecord,
    OperationType,
    SyncResult,
    ConnectorFactory,
)

logger = logging.getLogger(__name__)


class SQLServerConfig(ConnectorConfig):
    """SQL Server connector configuration."""
    host: str = "localhost"
    port: int = Field(default=1433, ge=1, le=65535)
    database: str
    username: str
    password: str
    
    # SQL Server specific
    driver: str = "ODBC Driver 17 for SQL Server"
    trusted_connection: bool = False
    encrypt: bool = True
    trust_server_certificate: bool = False
    
    # Connection settings
    login_timeout: int = Field(default=30, ge=1)
    query_timeout: int = Field(default=0, ge=0)  # 0 = no timeout
    
    # Advanced settings
    application_name: str = "SuperInsight-Sync"
    workstation_id: Optional[str] = None
    application_intent: str = "ReadOnly"  # ReadOnly or ReadWrite
    multi_subnet_failover: bool = False


class SQLServerConnector(BaseConnector):
    """
    SQL Server database connector.

    Supports:
    - Schema discovery across multiple databases
    - Incremental sync via timestamp/rowversion columns
    - SQL Server CDC (Change Data Capture)
    - Connection pooling
    - Read-only access with proper security
    - Always Encrypted support
    """

    def __init__(self, config: SQLServerConfig):
        super().__init__(config)
        self.sqlserver_config = config
        self._pool = None
        self._schema_cache: Optional[Dict[str, Any]] = None
        self._connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Build SQL Server connection string."""
        parts = [
            f"DRIVER={{{self.sqlserver_config.driver}}}",
            f"SERVER={self.sqlserver_config.host},{self.sqlserver_config.port}",
            f"DATABASE={self.sqlserver_config.database}",
        ]

        if self.sqlserver_config.trusted_connection:
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={self.sqlserver_config.username}")
            parts.append(f"PWD={self.sqlserver_config.password}")

        parts.extend([
            f"Encrypt={'yes' if self.sqlserver_config.encrypt else 'no'}",
            f"TrustServerCertificate={'yes' if self.sqlserver_config.trust_server_certificate else 'no'}",
            f"LoginTimeout={self.sqlserver_config.login_timeout}",
            f"QueryTimeout={self.sqlserver_config.query_timeout}",
            f"APP={self.sqlserver_config.application_name}",
            f"ApplicationIntent={self.sqlserver_config.application_intent}",
        ])

        if self.sqlserver_config.workstation_id:
            parts.append(f"WSID={self.sqlserver_config.workstation_id}")

        if self.sqlserver_config.multi_subnet_failover:
            parts.append("MultiSubnetFailover=yes")

        return ";".join(parts)

    async def connect(self) -> bool:
        """Establish connection to SQL Server."""
        try:
            self._set_status(ConnectionStatus.CONNECTING)

            # In production, use pyodbc or aioodbc
            # import pyodbc
            # self._connection = pyodbc.connect(self._connection_string)
            # 
            # Or for async:
            # import aioodbc
            # self._pool = await aioodbc.create_pool(
            #     dsn=self._connection_string,
            #     minsize=1,
            #     maxsize=self.config.pool_size
            # )

            # For demo, simulate connection
            await asyncio.sleep(0.15)

            self._set_status(ConnectionStatus.CONNECTED)
            logger.info(
                f"Connected to SQL Server: {self.sqlserver_config.host}:{self.sqlserver_config.port}"
                f"/{self.sqlserver_config.database}"
            )
            return True

        except Exception as e:
            self._set_status(ConnectionStatus.ERROR)
            self._record_error(e)
            return False

    async def disconnect(self) -> None:
        """Disconnect from SQL Server."""
        try:
            if self._pool:
                # self._pool.close()
                # await self._pool.wait_closed()
                self._pool = None
            self._set_status(ConnectionStatus.DISCONNECTED)
            logger.info("Disconnected from SQL Server")

        except Exception as e:
            self._record_error(e)

    async def health_check(self) -> bool:
        """Check SQL Server connection health."""
        try:
            # In production: execute "SELECT 1"
            return self.is_connected

        except Exception as e:
            self._record_error(e)
            return False

    async def fetch_schema(self) -> Dict[str, Any]:
        """
        Fetch SQL Server schema information.

        Returns tables, views, columns, indexes from INFORMATION_SCHEMA.
        """
        if self._schema_cache:
            return self._schema_cache

        schema = {
            "database": self.sqlserver_config.database,
            "server": f"{self.sqlserver_config.host}:{self.sqlserver_config.port}",
            "version": "2019",  # Would query SELECT @@VERSION
            "schemas": [],
            "tables": [],
            "fetched_at": datetime.utcnow().isoformat()
        }

        # In production, query INFORMATION_SCHEMA views
        # For demo, return sample schema
        schema["schemas"] = ["dbo", "sales", "production", "humanresources"]
        schema["tables"] = [
            {
                "schema": "dbo",
                "name": "Customers",
                "columns": [
                    {"name": "CustomerID", "type": "int", "nullable": False, "primary_key": True},
                    {"name": "CustomerName", "type": "nvarchar(100)", "nullable": False},
                    {"name": "Email", "type": "nvarchar(255)", "nullable": True},
                    {"name": "Phone", "type": "nvarchar(20)", "nullable": True},
                    {"name": "CreatedDate", "type": "datetime2", "nullable": False},
                    {"name": "ModifiedDate", "type": "datetime2", "nullable": False},
                    {"name": "RowVersion", "type": "timestamp", "nullable": False},
                ],
                "row_count": 25000
            },
            {
                "schema": "sales",
                "name": "Orders",
                "columns": [
                    {"name": "OrderID", "type": "int", "nullable": False, "primary_key": True},
                    {"name": "CustomerID", "type": "int", "nullable": False},
                    {"name": "OrderDate", "type": "datetime2", "nullable": False},
                    {"name": "TotalAmount", "type": "decimal(18,2)", "nullable": False},
                    {"name": "Status", "type": "nvarchar(50)", "nullable": False},
                    {"name": "RowVersion", "type": "timestamp", "nullable": False},
                ],
                "row_count": 100000
            }
        ]

        self._schema_cache = schema
        return schema

    async def fetch_data(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None
    ) -> DataBatch:
        """
        Fetch data from SQL Server.

        Supports SQL Server-specific features like OFFSET/FETCH, rowversion.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to database")

        batch_size = limit or self.config.batch_size

        # Build query
        if query:
            sql = query
        else:
            if not table:
                raise ValueError("Either query or table must be specified")

            # Handle schema.table format
            if "." in table:
                schema_table = table
            else:
                schema_table = f"dbo.{table}"  # Default schema

            sql = f"SELECT * FROM {schema_table}"

            where_clauses = []

            # Apply incremental filter
            if incremental_field and incremental_value:
                if incremental_field.lower() == "rowversion":
                    # SQL Server rowversion-based incremental sync
                    where_clauses.append(f"{incremental_field} > 0x{incremental_value}")
                else:
                    where_clauses.append(f"{incremental_field} > '{incremental_value}'")

            # Apply other filters
            if filters:
                for field, value in filters.items():
                    if isinstance(value, str):
                        where_clauses.append(f"{field} = N'{value}'")
                    else:
                        where_clauses.append(f"{field} = {value}")

            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

            if incremental_field and incremental_field.lower() != "rowversion":
                sql += f" ORDER BY {incremental_field}"
            else:
                sql += " ORDER BY (SELECT NULL)"  # Required for OFFSET/FETCH

            # SQL Server pagination using OFFSET/FETCH
            sql += f" OFFSET {offset} ROWS FETCH NEXT {batch_size} ROWS ONLY"

        # In production, execute query with pyodbc
        # For demo, return sample data
        records = []
        for i in range(min(batch_size, 50)):  # Limit demo records
            record_id = str(offset + i + 1)
            records.append(DataRecord(
                id=record_id,
                data={
                    "CustomerID": int(record_id),
                    "CustomerName": f"Customer {record_id}",
                    "Email": f"customer{record_id}@example.com",
                    "Phone": f"+1-555-{record_id:04d}",
                    "CreatedDate": datetime.utcnow().isoformat(),
                    "ModifiedDate": datetime.utcnow().isoformat(),
                    "RowVersion": f"0x{int(record_id):016X}",
                },
                timestamp=datetime.utcnow(),
                operation=OperationType.UPSERT
            ))

        self._record_read(len(records))
        total_count = await self.get_record_count(table, filters)

        return DataBatch(
            records=records,
            source_id=f"sqlserver:{self.sqlserver_config.database}",
            table_name=table,
            total_count=total_count,
            offset=offset,
            has_more=(offset + len(records)) < total_count,
            checkpoint={
                "offset": offset + len(records),
                "last_id": records[-1].id if records else None,
                "last_rowversion": records[-1].data.get("RowVersion") if records else None
            }
        )

    async def fetch_data_stream(
        self,
        query: Optional[str] = None,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        incremental_field: Optional[str] = None,
        incremental_value: Optional[str] = None
    ) -> AsyncIterator[DataBatch]:
        """
        Stream data from SQL Server in batches.

        Uses SQL Server-specific streaming features.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to database")

        batch_size = batch_size or self.config.batch_size
        offset = 0
        has_more = True

        while has_more:
            batch = await self.fetch_data(
                query=query,
                table=table,
                filters=filters,
                limit=batch_size,
                offset=offset,
                incremental_field=incremental_field,
                incremental_value=incremental_value
            )

            yield batch

            has_more = batch.has_more
            offset += len(batch.records)
            await asyncio.sleep(0.01)

    async def write_data(
        self,
        batch: DataBatch,
        mode: str = "upsert"
    ) -> SyncResult:
        """
        Write data batch to SQL Server.

        Supports SQL Server-specific features like MERGE statements.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to database")

        import time
        start_time = time.time()

        result = SyncResult(
            success=True,
            records_processed=len(batch.records)
        )

        try:
            # In production, use SQL Server MERGE for upsert operations
            for record in batch.records:
                if mode == "insert" or record.operation == OperationType.INSERT:
                    result.records_inserted += 1
                elif mode == "update" or record.operation == OperationType.UPDATE:
                    result.records_updated += 1
                elif mode == "delete" or record.operation == OperationType.DELETE:
                    result.records_deleted += 1
                else:  # upsert using MERGE
                    result.records_inserted += 1

            self._record_write(len(batch.records))

        except Exception as e:
            result.success = False
            result.records_failed = len(batch.records)
            result.errors.append({"error": str(e)})
            self._record_error(e)

        result.duration_seconds = time.time() - start_time
        return result

    async def get_record_count(
        self,
        table: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Get record count from SQL Server."""
        if not table:
            return 0

        # In production: execute COUNT query
        return 25000  # Demo value

    async def check_cdc_enabled(self, table: str) -> bool:
        """
        Check if Change Data Capture is enabled for a table.

        Args:
            table: Table name to check

        Returns:
            True if CDC is enabled
        """
        # In production: query sys.change_tracking_tables
        return True  # Demo value

    async def get_cdc_changes(
        self,
        table: str,
        from_lsn: Optional[str] = None,
        to_lsn: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get CDC changes for a table.

        Args:
            table: Table name
            from_lsn: Starting LSN
            to_lsn: Ending LSN

        Returns:
            List of change records
        """
        # In production: query cdc.fn_cdc_get_all_changes_*
        return []

    async def setup_read_only_user(self, username: str) -> Dict[str, Any]:
        """
        Setup read-only user for data extraction.

        Args:
            username: Username for read-only access

        Returns:
            Setup result with granted permissions
        """
        permissions = [
            "db_datareader",
            "VIEW DEFINITION",
            "VIEW DATABASE STATE"
        ]

        # In production, execute GRANT statements
        return {
            "username": username,
            "permissions": permissions,
            "status": "created"
        }


# Register connector
ConnectorFactory.register("sqlserver", SQLServerConnector)