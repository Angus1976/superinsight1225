"""
Oracle Connector.

Provides connector for Oracle databases with support for
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


class OracleConfig(ConnectorConfig):
    """Oracle connector configuration."""
    host: str = "localhost"
    port: int = Field(default=1521, ge=1, le=65535)
    service_name: Optional[str] = None
    sid: Optional[str] = None
    username: str
    password: str
    
    # Oracle specific
    encoding: str = "UTF-8"
    nencoding: str = "UTF-8"
    threaded: bool = True
    
    # Connection pool settings
    min_pool_size: int = Field(default=1, ge=1)
    max_pool_size: int = Field(default=10, ge=1)
    increment: int = Field(default=1, ge=1)
    
    # Security
    wallet_location: Optional[str] = None
    wallet_password: Optional[str] = None


class OracleConnector(BaseConnector):
    """
    Oracle database connector.

    Supports:
    - Schema discovery across multiple schemas
    - Incremental sync via timestamp/SCN columns
    - Oracle-specific data types (CLOB, BLOB, XMLType)
    - Connection pooling with Oracle Connection Manager
    - Read-only access with proper privilege management
    """

    def __init__(self, config: OracleConfig):
        super().__init__(config)
        self.oracle_config = config
        self._pool = None
        self._schema_cache: Optional[Dict[str, Any]] = None
        self._connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Build Oracle connection string."""
        if self.oracle_config.service_name:
            dsn = f"{self.oracle_config.host}:{self.oracle_config.port}/{self.oracle_config.service_name}"
        elif self.oracle_config.sid:
            dsn = f"{self.oracle_config.host}:{self.oracle_config.port}:{self.oracle_config.sid}"
        else:
            raise ValueError("Either service_name or sid must be specified")
        
        return dsn

    async def connect(self) -> bool:
        """Establish connection to Oracle."""
        try:
            self._set_status(ConnectionStatus.CONNECTING)

            # In production, use cx_Oracle or oracledb
            # import oracledb
            # self._pool = oracledb.create_pool(
            #     user=self.oracle_config.username,
            #     password=self.oracle_config.password,
            #     dsn=self._connection_string,
            #     min=self.oracle_config.min_pool_size,
            #     max=self.oracle_config.max_pool_size,
            #     increment=self.oracle_config.increment,
            #     encoding=self.oracle_config.encoding,
            #     nencoding=self.oracle_config.nencoding,
            #     threaded=self.oracle_config.threaded
            # )

            # For demo, simulate connection
            await asyncio.sleep(0.2)  # Oracle connections can be slower

            self._set_status(ConnectionStatus.CONNECTED)
            logger.info(
                f"Connected to Oracle: {self.oracle_config.host}:{self.oracle_config.port}"
            )
            return True

        except Exception as e:
            self._set_status(ConnectionStatus.ERROR)
            self._record_error(e)
            return False

    async def disconnect(self) -> None:
        """Disconnect from Oracle."""
        try:
            if self._pool:
                # self._pool.close()
                self._pool = None
            self._set_status(ConnectionStatus.DISCONNECTED)
            logger.info("Disconnected from Oracle")

        except Exception as e:
            self._record_error(e)

    async def health_check(self) -> bool:
        """Check Oracle connection health."""
        try:
            # In production: execute "SELECT 1 FROM DUAL"
            return self.is_connected

        except Exception as e:
            self._record_error(e)
            return False

    async def fetch_schema(self) -> Dict[str, Any]:
        """
        Fetch Oracle schema information.

        Returns tables, views, columns, indexes, and constraints from ALL_TABLES.
        """
        if self._schema_cache:
            return self._schema_cache

        schema = {
            "database": self._connection_string,
            "version": "19c",  # Would query SELECT * FROM V$VERSION
            "schemas": [],
            "tables": [],
            "fetched_at": datetime.utcnow().isoformat()
        }

        # In production, query ALL_TABLES, ALL_TAB_COLUMNS, etc.
        # For demo, return sample schema
        schema["schemas"] = ["HR", "SALES", "INVENTORY"]
        schema["tables"] = [
            {
                "schema": "HR",
                "name": "EMPLOYEES",
                "columns": [
                    {"name": "EMPLOYEE_ID", "type": "NUMBER", "nullable": False, "primary_key": True},
                    {"name": "FIRST_NAME", "type": "VARCHAR2(20)", "nullable": True},
                    {"name": "LAST_NAME", "type": "VARCHAR2(25)", "nullable": False},
                    {"name": "EMAIL", "type": "VARCHAR2(25)", "nullable": False},
                    {"name": "HIRE_DATE", "type": "DATE", "nullable": False},
                    {"name": "SALARY", "type": "NUMBER(8,2)", "nullable": True},
                ],
                "row_count": 107
            },
            {
                "schema": "SALES",
                "name": "ORDERS",
                "columns": [
                    {"name": "ORDER_ID", "type": "NUMBER", "nullable": False, "primary_key": True},
                    {"name": "CUSTOMER_ID", "type": "NUMBER", "nullable": False},
                    {"name": "ORDER_DATE", "type": "DATE", "nullable": False},
                    {"name": "ORDER_TOTAL", "type": "NUMBER(10,2)", "nullable": False},
                    {"name": "STATUS", "type": "VARCHAR2(20)", "nullable": False},
                ],
                "row_count": 50000
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
        Fetch data from Oracle.

        Supports Oracle-specific features like ROWNUM, SCN-based incremental sync.
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
                schema_table = f"HR.{table}"  # Default schema

            sql = f"SELECT * FROM {schema_table}"

            where_clauses = []

            # Apply incremental filter
            if incremental_field and incremental_value:
                if incremental_field.upper() == "SCN":
                    # Oracle SCN-based incremental sync
                    where_clauses.append(f"ORA_ROWSCN > {incremental_value}")
                else:
                    where_clauses.append(f"{incremental_field} > '{incremental_value}'")

            # Apply other filters
            if filters:
                for field, value in filters.items():
                    if isinstance(value, str):
                        where_clauses.append(f"{field} = '{value}'")
                    else:
                        where_clauses.append(f"{field} = {value}")

            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

            if incremental_field and incremental_field.upper() != "SCN":
                sql += f" ORDER BY {incremental_field}"

            # Oracle pagination using ROWNUM
            if offset > 0:
                sql = f"""
                SELECT * FROM (
                    SELECT a.*, ROWNUM rnum FROM ({sql}) a
                    WHERE ROWNUM <= {offset + batch_size}
                ) WHERE rnum > {offset}
                """
            else:
                sql += f" AND ROWNUM <= {batch_size}"

        # In production, execute query with cx_Oracle
        # For demo, return sample data
        records = []
        for i in range(min(batch_size, 50)):  # Limit demo records
            record_id = str(offset + i + 1)
            records.append(DataRecord(
                id=record_id,
                data={
                    "EMPLOYEE_ID": int(record_id),
                    "FIRST_NAME": f"John{record_id}",
                    "LAST_NAME": f"Doe{record_id}",
                    "EMAIL": f"john.doe{record_id}@company.com",
                    "HIRE_DATE": datetime.utcnow().isoformat(),
                    "SALARY": 50000 + (int(record_id) * 1000),
                },
                timestamp=datetime.utcnow(),
                operation=OperationType.UPSERT
            ))

        self._record_read(len(records))
        total_count = await self.get_record_count(table, filters)

        return DataBatch(
            records=records,
            source_id=f"oracle:{self._connection_string}",
            table_name=table,
            total_count=total_count,
            offset=offset,
            has_more=(offset + len(records)) < total_count,
            checkpoint={
                "offset": offset + len(records),
                "last_id": records[-1].id if records else None,
                "scn": "12345678"  # Oracle SCN for CDC
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
        Stream data from Oracle in batches.

        Uses Oracle-specific cursor features for efficient streaming.
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
        Write data batch to Oracle.

        Supports Oracle-specific features like MERGE statements.
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
            # In production, use Oracle MERGE for upsert operations
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
        """Get record count from Oracle."""
        if not table:
            return 0

        # In production: execute COUNT query
        return 107  # Demo value for HR.EMPLOYEES

    async def get_current_scn(self) -> str:
        """
        Get current Oracle System Change Number (SCN).

        Returns:
            Current SCN as string
        """
        # In production: SELECT CURRENT_SCN FROM V$DATABASE
        return "12345678"

    async def setup_read_only_user(self, username: str) -> Dict[str, Any]:
        """
        Setup read-only user for data extraction.

        Args:
            username: Username for read-only access

        Returns:
            Setup result with granted privileges
        """
        privileges = [
            "CREATE SESSION",
            "SELECT ANY TABLE",
            "SELECT ANY DICTIONARY"
        ]

        # In production, execute GRANT statements
        return {
            "username": username,
            "privileges": privileges,
            "status": "created"
        }


# Register connector
ConnectorFactory.register("oracle", OracleConnector)