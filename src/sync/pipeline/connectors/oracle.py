"""
Oracle Connector for Data Sync Pipeline.
"""

from typing import Any, AsyncIterator, Dict, List, Optional
import logging

from src.sync.pipeline.enums import DatabaseType
from src.sync.pipeline.schemas import DataSourceConfig, DataPage
from src.sync.pipeline.connectors.base import (
    BaseConnector,
    ConnectorFactory,
    ConnectionError,
    ReadOnlyViolationError,
)

logger = logging.getLogger(__name__)


class OracleConnector(BaseConnector):
    """
    Oracle database connector with read-only access.
    
    Note: Uses cx_Oracle with asyncio wrapper for async support.
    """
    
    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self._pool = None
    
    async def connect(self) -> None:
        """Establish a read-only connection to Oracle."""
        try:
            import cx_Oracle
            import asyncio
            
            # Build DSN
            dsn = cx_Oracle.makedsn(
                self.config.host,
                self.config.port,
                service_name=self.config.database
            )
            
            # Create connection pool
            self._pool = cx_Oracle.SessionPool(
                user=self.config.username,
                password=self.config.password,
                dsn=dsn,
                min=1,
                max=5,
                increment=1,
                threaded=True,
                **self.config.extra_params
            )
            
            self._is_connected = True
            logger.info(f"Connected to Oracle: {self.config.host}:{self.config.port}/{self.config.database}")
            
        except ImportError:
            raise ConnectionError("cx_Oracle package is required for Oracle connections")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Oracle: {str(e)}")
    
    async def disconnect(self) -> None:
        """Close the Oracle connection pool."""
        if self._pool:
            self._pool.close()
            self._pool = None
            self._is_connected = False
            logger.info("Disconnected from Oracle")
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read-only query."""
        self._validate_readonly_query(query)
        
        if not self._pool:
            raise ConnectionError("Not connected to database")
        
        import asyncio
        
        def _execute():
            conn = self._pool.acquire()
            try:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                columns = [col[0].lower() for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            finally:
                self._pool.release(conn)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
    
    async def execute_query_paginated(
        self,
        query: str,
        page_size: int = 1000,
        params: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[DataPage]:
        """Execute a query with pagination."""
        self._validate_readonly_query(query)
        
        if not self._pool:
            raise ConnectionError("Not connected to database")
        
        import asyncio
        
        offset = 0
        page_number = 0
        
        while True:
            # Oracle uses OFFSET FETCH for pagination (12c+)
            paginated_query = f"""
                {query}
                OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY
            """
            
            def _execute():
                conn = self._pool.acquire()
                try:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(paginated_query, params)
                    else:
                        cursor.execute(paginated_query)
                    
                    columns = [col[0].lower() for col in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                finally:
                    self._pool.release(conn)
            
            loop = asyncio.get_event_loop()
            rows_list = await loop.run_in_executor(None, _execute)
            
            row_count = len(rows_list)
            has_more = row_count == page_size
            
            yield DataPage(
                page_number=page_number,
                rows=rows_list,
                row_count=row_count,
                has_more=has_more
            )
            
            if not has_more:
                break
            
            offset += page_size
            page_number += 1
    
    async def get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table."""
        query = """
            SELECT column_name 
            FROM all_tab_columns 
            WHERE table_name = :table_name
            ORDER BY column_id
        """
        
        rows = await self.execute_query(query, {"table_name": table_name.upper()})
        return [row['column_name'].lower() for row in rows]
    
    async def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        query = f'SELECT COUNT(*) as count FROM "{table_name}"'
        rows = await self.execute_query(query)
        return rows[0]['count']
    
    async def test_connection(self) -> bool:
        """Test if the connection is valid."""
        try:
            if not self._pool:
                return False
            
            await self.execute_query("SELECT 1 FROM DUAL")
            return True
        except Exception:
            return False


# Register the connector
ConnectorFactory.register(DatabaseType.ORACLE, OracleConnector)
