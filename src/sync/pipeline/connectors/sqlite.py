"""
SQLite Connector for Data Sync Pipeline.
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


class SQLiteConnector(BaseConnector):
    """
    SQLite database connector with read-only access.
    """
    
    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self._connection = None
    
    async def connect(self) -> None:
        """Establish a read-only connection to SQLite."""
        try:
            import aiosqlite
            
            # SQLite uses database field as file path
            db_path = self.config.database
            
            # Open in read-only mode using URI
            uri = f"file:{db_path}?mode=ro"
            self._connection = await aiosqlite.connect(uri, uri=True)
            self._connection.row_factory = aiosqlite.Row
            
            self._is_connected = True
            logger.info(f"Connected to SQLite: {db_path}")
            
        except ImportError:
            raise ConnectionError("aiosqlite package is required for SQLite connections")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQLite: {str(e)}")
    
    async def disconnect(self) -> None:
        """Close the SQLite connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._is_connected = False
            logger.info("Disconnected from SQLite")
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read-only query."""
        self._validate_readonly_query(query)
        
        if not self._connection:
            raise ConnectionError("Not connected to database")
        
        async with self._connection.execute(
            query,
            tuple(params.values()) if params else ()
        ) as cursor:
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    async def execute_query_paginated(
        self,
        query: str,
        page_size: int = 1000,
        params: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[DataPage]:
        """Execute a query with pagination."""
        self._validate_readonly_query(query)
        
        if not self._connection:
            raise ConnectionError("Not connected to database")
        
        offset = 0
        page_number = 0
        
        while True:
            paginated_query = f"{query} LIMIT {page_size} OFFSET {offset}"
            
            async with self._connection.execute(
                paginated_query,
                tuple(params.values()) if params else ()
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
            
            rows_list = [dict(zip(columns, row)) for row in rows]
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
        query = f"PRAGMA table_info('{table_name}')"
        
        async with self._connection.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [row[1] for row in rows]  # Column name is at index 1
    
    async def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        query = f'SELECT COUNT(*) as count FROM "{table_name}"'
        
        async with self._connection.execute(query) as cursor:
            row = await cursor.fetchone()
            return row[0]
    
    async def test_connection(self) -> bool:
        """Test if the connection is valid."""
        try:
            if not self._connection:
                return False
            
            async with self._connection.execute("SELECT 1") as cursor:
                await cursor.fetchone()
            return True
        except Exception:
            return False


# Register the connector
ConnectorFactory.register(DatabaseType.SQLITE, SQLiteConnector)
