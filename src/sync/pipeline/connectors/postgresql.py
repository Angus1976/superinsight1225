"""
PostgreSQL Connector for Data Sync Pipeline.
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


class PostgreSQLConnector(BaseConnector):
    """
    PostgreSQL database connector with read-only access.
    """
    
    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self._pool = None
    
    async def connect(self) -> None:
        """Establish a read-only connection to PostgreSQL."""
        try:
            import asyncpg
            
            # Build connection string with read-only settings
            dsn = (
                f"postgresql://{self.config.username}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
            )
            
            # Create connection pool
            self._pool = await asyncpg.create_pool(
                dsn,
                min_size=1,
                max_size=5,
                command_timeout=60,
                **self.config.extra_params
            )
            
            # Set read-only mode for all connections
            async with self._pool.acquire() as conn:
                await conn.execute("SET default_transaction_read_only = ON")
            
            self._is_connected = True
            logger.info(f"Connected to PostgreSQL: {self.config.host}:{self.config.port}/{self.config.database}")
            
        except ImportError:
            raise ConnectionError("asyncpg package is required for PostgreSQL connections")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL: {str(e)}")
    
    async def disconnect(self) -> None:
        """Close the PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._is_connected = False
            logger.info("Disconnected from PostgreSQL")
    
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
            # Convert dict params to positional if needed
            if params:
                # asyncpg uses $1, $2, etc. for parameters
                rows = await conn.fetch(query, *params.values())
            else:
                rows = await conn.fetch(query)
            
            return [dict(row) for row in rows]
    
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
        
        offset = 0
        page_number = 0
        
        while True:
            paginated_query = f"{query} LIMIT {page_size} OFFSET {offset}"
            
            async with self._pool.acquire() as conn:
                if params:
                    rows = await conn.fetch(paginated_query, *params.values())
                else:
                    rows = await conn.fetch(paginated_query)
            
            rows_list = [dict(row) for row in rows]
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
            WHERE table_name = $1
            ORDER BY ordinal_position
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, table_name)
            return [row['column_name'] for row in rows]
    
    async def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        # Use safe table name (prevent SQL injection)
        query = f'SELECT COUNT(*) as count FROM "{table_name}"'
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query)
            return row['count']
    
    async def test_connection(self) -> bool:
        """Test if the connection is valid."""
        try:
            if not self._pool:
                return False
            
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False


# Register the connector
ConnectorFactory.register(DatabaseType.POSTGRESQL, PostgreSQLConnector)
