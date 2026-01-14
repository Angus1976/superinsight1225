"""
MySQL Connector for Data Sync Pipeline.
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


class MySQLConnector(BaseConnector):
    """
    MySQL database connector with read-only access.
    """
    
    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self._pool = None
    
    async def connect(self) -> None:
        """Establish a read-only connection to MySQL."""
        try:
            import aiomysql
            
            self._pool = await aiomysql.create_pool(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                db=self.config.database,
                minsize=1,
                maxsize=5,
                autocommit=True,
                **self.config.extra_params
            )
            
            # Set read-only mode
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SET SESSION TRANSACTION READ ONLY")
            
            self._is_connected = True
            logger.info(f"Connected to MySQL: {self.config.host}:{self.config.port}/{self.config.database}")
            
        except ImportError:
            raise ConnectionError("aiomysql package is required for MySQL connections")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MySQL: {str(e)}")
    
    async def disconnect(self) -> None:
        """Close the MySQL connection pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            self._is_connected = False
            logger.info("Disconnected from MySQL")
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read-only query."""
        self._validate_readonly_query(query)
        
        if not self._pool:
            raise ConnectionError("Not connected to database")
        
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if params:
                    await cursor.execute(query, tuple(params.values()))
                else:
                    await cursor.execute(query)
                
                rows = await cursor.fetchall()
                return list(rows)
    
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
        
        import aiomysql
        
        offset = 0
        page_number = 0
        
        while True:
            paginated_query = f"{query} LIMIT {page_size} OFFSET {offset}"
            
            async with self._pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    if params:
                        await cursor.execute(paginated_query, tuple(params.values()))
                    else:
                        await cursor.execute(paginated_query)
                    
                    rows = await cursor.fetchall()
            
            rows_list = list(rows)
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
            FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = %s
            ORDER BY ordinal_position
        """
        
        import aiomysql
        
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, (table_name, self.config.database))
                rows = await cursor.fetchall()
                return [row['column_name'] for row in rows]
    
    async def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        query = f"SELECT COUNT(*) as count FROM `{table_name}`"
        
        import aiomysql
        
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query)
                row = await cursor.fetchone()
                return row['count']
    
    async def test_connection(self) -> bool:
        """Test if the connection is valid."""
        try:
            if not self._pool:
                return False
            
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
            return True
        except Exception:
            return False


# Register the connector
ConnectorFactory.register(DatabaseType.MYSQL, MySQLConnector)
