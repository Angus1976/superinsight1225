"""
Data Reader for Data Sync Pipeline.

Supports JDBC/ODBC style reading from customer databases with read-only access.
"""

import time
import sys
from typing import Any, AsyncIterator, Dict, List, Optional
import logging

from src.sync.pipeline.enums import DatabaseType, ConnectionMethod
from src.sync.pipeline.schemas import DataSourceConfig, DataPage, ReadStatistics
from src.sync.pipeline.connectors.base import BaseConnector, ConnectorFactory

logger = logging.getLogger(__name__)


class DataReader:
    """
    Data Reader for reading data from customer databases.
    
    Features:
    - Read-only connections (enforced by connectors)
    - Support for multiple database types
    - Paginated reading to avoid memory overflow
    - Statistics collection
    """
    
    def __init__(self, connector_factory: Optional[ConnectorFactory] = None):
        """
        Initialize the Data Reader.
        
        Args:
            connector_factory: Factory for creating database connectors.
                             Uses default ConnectorFactory if not provided.
        """
        self.connector_factory = connector_factory or ConnectorFactory
        self._connector: Optional[BaseConnector] = None
        self._config: Optional[DataSourceConfig] = None
    
    async def connect(
        self,
        config: DataSourceConfig,
        connection_method: ConnectionMethod = ConnectionMethod.JDBC
    ) -> BaseConnector:
        """
        Establish a read-only connection to the database.
        
        Args:
            config: Data source configuration
            connection_method: Connection method (JDBC/ODBC)
            
        Returns:
            Connected database connector
        """
        # Update config with connection method
        config_dict = config.model_dump()
        config_dict['connection_method'] = connection_method
        self._config = DataSourceConfig(**config_dict)
        
        # Create and connect
        self._connector = self.connector_factory.create(self._config)
        await self._connector.connect()
        
        logger.info(f"Connected to {config.db_type.value} database at {config.host}:{config.port}")
        return self._connector
    
    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._connector:
            await self._connector.disconnect()
            self._connector = None
            self._config = None
            logger.info("Disconnected from database")
    
    async def read_by_query(
        self,
        query: str,
        page_size: int = 1000,
        params: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[DataPage]:
        """
        Read data using a SQL query with pagination.
        
        Args:
            query: SQL SELECT query
            page_size: Number of rows per page (default 1000)
            params: Query parameters
            
        Yields:
            DataPage objects containing rows
            
        Raises:
            ConnectionError: If not connected
            ReadOnlyViolationError: If query attempts to modify data
        """
        if not self._connector:
            raise ConnectionError("Not connected to database. Call connect() first.")
        
        async for page in self._connector.execute_query_paginated(
            query, page_size, params
        ):
            yield page
    
    async def read_by_table(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        page_size: int = 1000,
        where_clause: Optional[str] = None
    ) -> AsyncIterator[DataPage]:
        """
        Read data from a table with pagination.
        
        Args:
            table_name: Name of the table to read
            columns: List of columns to select (None for all)
            page_size: Number of rows per page (default 1000)
            where_clause: Optional WHERE clause (without 'WHERE' keyword)
            
        Yields:
            DataPage objects containing rows
        """
        if not self._connector:
            raise ConnectionError("Not connected to database. Call connect() first.")
        
        # Build column list
        if columns:
            column_str = ", ".join(columns)
        else:
            column_str = "*"
        
        # Build query
        query = f"SELECT {column_str} FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        async for page in self._connector.execute_query_paginated(
            query, page_size
        ):
            yield page
    
    async def read_all(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Read all data from a query (use with caution for large datasets).
        
        Args:
            query: SQL SELECT query
            params: Query parameters
            
        Returns:
            List of all rows
        """
        if not self._connector:
            raise ConnectionError("Not connected to database. Call connect() first.")
        
        return await self._connector.execute_query(query, params)
    
    def get_statistics(self, pages: List[DataPage]) -> ReadStatistics:
        """
        Calculate statistics from read pages.
        
        Args:
            pages: List of DataPage objects
            
        Returns:
            ReadStatistics with row count, column count, and size
        """
        total_rows = sum(page.row_count for page in pages)
        total_columns = 0
        total_size_bytes = 0
        
        for page in pages:
            if page.rows:
                # Get column count from first row
                if total_columns == 0:
                    total_columns = len(page.rows[0])
                
                # Estimate size
                for row in page.rows:
                    total_size_bytes += self._estimate_row_size(row)
        
        return ReadStatistics(
            total_rows=total_rows,
            total_columns=total_columns,
            total_size_bytes=total_size_bytes,
            read_duration_ms=0.0  # Will be set by caller
        )
    
    def _estimate_row_size(self, row: Dict[str, Any]) -> int:
        """
        Estimate the size of a row in bytes.
        
        Args:
            row: Row data as dictionary
            
        Returns:
            Estimated size in bytes
        """
        size = 0
        for key, value in row.items():
            # Key size
            size += len(key.encode('utf-8'))
            
            # Value size
            if value is None:
                size += 0
            elif isinstance(value, str):
                size += len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                size += 8
            elif isinstance(value, bytes):
                size += len(value)
            else:
                # Fallback: use string representation
                size += len(str(value).encode('utf-8'))
        
        return size
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get information about a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
        """
        if not self._connector:
            raise ConnectionError("Not connected to database. Call connect() first.")
        
        columns = await self._connector.get_table_columns(table_name)
        row_count = await self._connector.get_row_count(table_name)
        
        return {
            "table_name": table_name,
            "columns": columns,
            "column_count": len(columns),
            "row_count": row_count
        }
    
    async def test_connection(self) -> bool:
        """
        Test if the current connection is valid.
        
        Returns:
            True if connection is valid
        """
        if not self._connector:
            return False
        
        return await self._connector.test_connection()
    
    @property
    def is_connected(self) -> bool:
        """Check if reader is connected."""
        return self._connector is not None and self._connector.is_connected
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class DataReaderWithStats(DataReader):
    """
    Data Reader with automatic statistics collection.
    """
    
    def __init__(self, connector_factory: Optional[ConnectorFactory] = None):
        super().__init__(connector_factory)
        self._last_statistics: Optional[ReadStatistics] = None
    
    async def read_by_query_with_stats(
        self,
        query: str,
        page_size: int = 1000,
        params: Optional[Dict[str, Any]] = None
    ) -> tuple[List[DataPage], ReadStatistics]:
        """
        Read data with automatic statistics collection.
        
        Args:
            query: SQL SELECT query
            page_size: Number of rows per page
            params: Query parameters
            
        Returns:
            Tuple of (pages, statistics)
        """
        start_time = time.time()
        pages = []
        
        async for page in self.read_by_query(query, page_size, params):
            pages.append(page)
        
        duration_ms = (time.time() - start_time) * 1000
        
        stats = self.get_statistics(pages)
        stats.read_duration_ms = duration_ms
        self._last_statistics = stats
        
        return pages, stats
    
    @property
    def last_statistics(self) -> Optional[ReadStatistics]:
        """Get the last collected statistics."""
        return self._last_statistics
