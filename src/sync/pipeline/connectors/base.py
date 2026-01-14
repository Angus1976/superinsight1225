"""
Base Connector and Factory for Database Connections.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Type
import logging

from src.sync.pipeline.enums import DatabaseType, ConnectionMethod
from src.sync.pipeline.schemas import DataSourceConfig, DataPage

logger = logging.getLogger(__name__)


class ReadOnlyViolationError(Exception):
    """Raised when a write operation is attempted on a read-only connection."""
    pass


class ConnectionError(Exception):
    """Raised when connection to database fails."""
    pass


class BaseConnector(ABC):
    """
    Abstract base class for database connectors.
    
    All connectors enforce read-only access to customer databases.
    """
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._connection: Optional[Any] = None
        self._is_connected: bool = False
    
    @property
    def is_connected(self) -> bool:
        """Check if connector is connected."""
        return self._is_connected
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish a read-only connection to the database.
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close the database connection."""
        pass
    
    @abstractmethod
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a read-only query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of rows as dictionaries
            
        Raises:
            ReadOnlyViolationError: If query attempts to modify data
        """
        pass
    
    @abstractmethod
    async def execute_query_paginated(
        self,
        query: str,
        page_size: int = 1000,
        params: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[DataPage]:
        """
        Execute a query with pagination.
        
        Args:
            query: SQL query to execute
            page_size: Number of rows per page
            params: Query parameters
            
        Yields:
            DataPage objects containing rows
        """
        pass
    
    @abstractmethod
    async def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get column names for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names
        """
        pass
    
    @abstractmethod
    async def get_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Number of rows
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the connection is valid.
        
        Returns:
            True if connection is valid
        """
        pass
    
    def _validate_readonly_query(self, query: str) -> None:
        """
        Validate that a query is read-only.
        
        Args:
            query: SQL query to validate
            
        Raises:
            ReadOnlyViolationError: If query attempts to modify data
        """
        query_upper = query.strip().upper()
        write_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE'
        ]
        
        for keyword in write_keywords:
            if query_upper.startswith(keyword):
                raise ReadOnlyViolationError(
                    f"Write operation '{keyword}' not allowed on read-only connection"
                )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class ConnectorFactory:
    """
    Factory for creating database connectors.
    """
    
    _connectors: Dict[DatabaseType, Type[BaseConnector]] = {}
    
    @classmethod
    def register(cls, db_type: DatabaseType, connector_class: Type[BaseConnector]) -> None:
        """
        Register a connector class for a database type.
        
        Args:
            db_type: Database type
            connector_class: Connector class to register
        """
        cls._connectors[db_type] = connector_class
        logger.info(f"Registered connector for {db_type.value}: {connector_class.__name__}")
    
    @classmethod
    def create(cls, config: DataSourceConfig) -> BaseConnector:
        """
        Create a connector for the given configuration.
        
        Args:
            config: Data source configuration
            
        Returns:
            Connector instance
            
        Raises:
            ValueError: If no connector is registered for the database type
        """
        connector_class = cls._connectors.get(config.db_type)
        if not connector_class:
            raise ValueError(f"No connector registered for database type: {config.db_type.value}")
        
        return connector_class(config)
    
    @classmethod
    def get_supported_types(cls) -> List[DatabaseType]:
        """
        Get list of supported database types.
        
        Returns:
            List of supported database types
        """
        return list(cls._connectors.keys())
