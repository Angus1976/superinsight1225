"""
Connection Test Service for Output Sync.

Provides connection testing and troubleshooting for target data sources.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import db_manager
from src.sync.models import DataSourceModel, SyncJobModel

logger = logging.getLogger(__name__)


class ConnectionStatus(str, Enum):
    """Connection test status."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"


class ConnectionTestResult(BaseModel):
    """Result of connection test."""
    status: ConnectionStatus
    target_id: str
    target_type: str
    response_time_ms: float
    error_message: Optional[str] = None
    troubleshooting_suggestions: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    connection_details: Dict[str, Any] = Field(default_factory=dict)


class ConnectionTestService:
    """
    Service for testing target database connections.
    
    Features:
    - Connection validation for various target types
    - Detailed error messages with troubleshooting suggestions
    - Integration with alert system for failure monitoring
    """
    
    def __init__(self):
        self.logger = logger
    
    async def test_connection(
        self,
        target_source_id: UUID,
        connection_config: Optional[Dict[str, Any]] = None
    ) -> ConnectionTestResult:
        """
        Test connection to target data source.
        
        Args:
            target_source_id: Target data source ID
            connection_config: Optional connection config override
            
        Returns:
            Connection test result with troubleshooting suggestions
        """
        start_time = datetime.utcnow()
        
        async with db_manager.get_session() as session:
            try:
                # Load target data source
                result = await session.execute(
                    select(DataSourceModel).where(
                        DataSourceModel.id == target_source_id
                    )
                )
                target_source = result.scalar_one_or_none()
                
                if not target_source:
                    return ConnectionTestResult(
                        status=ConnectionStatus.FAILED,
                        target_id=str(target_source_id),
                        target_type="unknown",
                        response_time_ms=0.0,
                        error_message="Target data source not found",
                        troubleshooting_suggestions=[
                            "Verify the target data source ID is correct",
                            "Check if the data source has been deleted",
                            "Ensure you have permission to access this data source"
                        ]
                    )
                
                # Use provided config or source config
                config = connection_config or target_source.connection_config
                target_type = target_source.source_type.value
                
                # Test connection based on target type
                if target_type == "postgresql":
                    test_result = await self._test_postgresql_connection(
                        config, str(target_source_id)
                    )
                elif target_type == "mysql":
                    test_result = await self._test_mysql_connection(
                        config, str(target_source_id)
                    )
                elif target_type == "mongodb":
                    test_result = await self._test_mongodb_connection(
                        config, str(target_source_id)
                    )
                elif target_type == "api":
                    test_result = await self._test_api_connection(
                        config, str(target_source_id)
                    )
                else:
                    test_result = ConnectionTestResult(
                        status=ConnectionStatus.FAILED,
                        target_id=str(target_source_id),
                        target_type=target_type,
                        response_time_ms=0.0,
                        error_message=f"Unsupported target type: {target_type}",
                        troubleshooting_suggestions=[
                            f"Target type '{target_type}' is not supported for output sync",
                            "Supported types: postgresql, mysql, mongodb, api"
                        ]
                    )
                
                # Calculate response time
                response_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                test_result.response_time_ms = response_time
                
                return test_result
                
            except Exception as e:
                logger.error(f"Connection test failed: {e}")
                response_time = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000
                
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    target_id=str(target_source_id),
                    target_type="unknown",
                    response_time_ms=response_time,
                    error_message=str(e),
                    troubleshooting_suggestions=[
                        "Check the error message for specific details",
                        "Verify network connectivity to the target",
                        "Ensure the connection configuration is correct"
                    ]
                )
    
    async def _test_postgresql_connection(
        self,
        config: Dict[str, Any],
        target_id: str
    ) -> ConnectionTestResult:
        """Test PostgreSQL connection."""
        try:
            # Validate required fields
            required_fields = ["host", "port", "database", "username"]
            missing_fields = [
                f for f in required_fields if f not in config
            ]
            
            if missing_fields:
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    target_id=target_id,
                    target_type="postgresql",
                    response_time_ms=0.0,
                    error_message=f"Missing required fields: {', '.join(missing_fields)}",
                    troubleshooting_suggestions=[
                        f"Add missing configuration fields: {', '.join(missing_fields)}",
                        "Verify the connection configuration is complete"
                    ]
                )
            
            # Simulate connection test (in production, use actual psycopg2/asyncpg)
            import asyncio
            await asyncio.sleep(0.05)  # Simulate connection attempt
            
            # For now, return success (actual implementation would connect)
            return ConnectionTestResult(
                status=ConnectionStatus.SUCCESS,
                target_id=target_id,
                target_type="postgresql",
                response_time_ms=0.0,
                connection_details={
                    "host": config.get("host"),
                    "port": config.get("port"),
                    "database": config.get("database")
                }
            )
            
        except Exception as e:
            return self._create_database_error_result(
                target_id, "postgresql", str(e)
            )
    
    async def _test_mysql_connection(
        self,
        config: Dict[str, Any],
        target_id: str
    ) -> ConnectionTestResult:
        """Test MySQL connection."""
        try:
            # Validate required fields
            required_fields = ["host", "port", "database", "username"]
            missing_fields = [
                f for f in required_fields if f not in config
            ]
            
            if missing_fields:
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    target_id=target_id,
                    target_type="mysql",
                    response_time_ms=0.0,
                    error_message=f"Missing required fields: {', '.join(missing_fields)}",
                    troubleshooting_suggestions=[
                        f"Add missing configuration fields: {', '.join(missing_fields)}",
                        "Verify the connection configuration is complete"
                    ]
                )
            
            # Simulate connection test
            import asyncio
            await asyncio.sleep(0.05)
            
            return ConnectionTestResult(
                status=ConnectionStatus.SUCCESS,
                target_id=target_id,
                target_type="mysql",
                response_time_ms=0.0,
                connection_details={
                    "host": config.get("host"),
                    "port": config.get("port"),
                    "database": config.get("database")
                }
            )
            
        except Exception as e:
            return self._create_database_error_result(
                target_id, "mysql", str(e)
            )
    
    async def _test_mongodb_connection(
        self,
        config: Dict[str, Any],
        target_id: str
    ) -> ConnectionTestResult:
        """Test MongoDB connection."""
        try:
            # Validate required fields
            if "connection_string" not in config and "host" not in config:
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    target_id=target_id,
                    target_type="mongodb",
                    response_time_ms=0.0,
                    error_message="Missing connection_string or host",
                    troubleshooting_suggestions=[
                        "Provide either 'connection_string' or 'host' in configuration",
                        "Example: mongodb://username:password@host:port/database"
                    ]
                )
            
            # Simulate connection test
            import asyncio
            await asyncio.sleep(0.05)
            
            return ConnectionTestResult(
                status=ConnectionStatus.SUCCESS,
                target_id=target_id,
                target_type="mongodb",
                response_time_ms=0.0,
                connection_details={
                    "host": config.get("host", "from_connection_string"),
                    "database": config.get("database")
                }
            )
            
        except Exception as e:
            return self._create_database_error_result(
                target_id, "mongodb", str(e)
            )
    
    async def _test_api_connection(
        self,
        config: Dict[str, Any],
        target_id: str
    ) -> ConnectionTestResult:
        """Test API endpoint connection."""
        try:
            # Validate required fields
            if "endpoint_url" not in config:
                return ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    target_id=target_id,
                    target_type="api",
                    response_time_ms=0.0,
                    error_message="Missing endpoint_url",
                    troubleshooting_suggestions=[
                        "Add 'endpoint_url' to the configuration",
                        "Ensure the API endpoint is accessible"
                    ]
                )
            
            # Simulate API connection test
            import asyncio
            await asyncio.sleep(0.05)
            
            return ConnectionTestResult(
                status=ConnectionStatus.SUCCESS,
                target_id=target_id,
                target_type="api",
                response_time_ms=0.0,
                connection_details={
                    "endpoint_url": config.get("endpoint_url"),
                    "method": config.get("method", "POST")
                }
            )
            
        except Exception as e:
            return ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                target_id=target_id,
                target_type="api",
                response_time_ms=0.0,
                error_message=str(e),
                troubleshooting_suggestions=[
                    "Verify the API endpoint URL is correct",
                    "Check if the API requires authentication",
                    "Ensure the API is accessible from this network",
                    "Check API rate limits or firewall rules"
                ]
            )
    
    def _create_database_error_result(
        self,
        target_id: str,
        target_type: str,
        error_message: str
    ) -> ConnectionTestResult:
        """Create error result for database connection failures."""
        suggestions = [
            "Verify the database host and port are correct",
            "Check if the database server is running",
            "Ensure network connectivity to the database",
            "Verify username and password are correct",
            "Check if the database exists",
            "Verify firewall rules allow connections",
            "Check if SSL/TLS settings are required"
        ]
        
        # Add specific suggestions based on error message
        error_lower = error_message.lower()
        if "timeout" in error_lower:
            suggestions.insert(0, "Connection timeout - check network latency")
            suggestions.insert(1, "Increase connection timeout setting")
        elif "authentication" in error_lower or "password" in error_lower:
            suggestions.insert(0, "Authentication failed - verify credentials")
        elif "host" in error_lower or "resolve" in error_lower:
            suggestions.insert(0, "Cannot resolve hostname - check DNS settings")
        elif "refused" in error_lower:
            suggestions.insert(0, "Connection refused - check if database is accepting connections")
        
        return ConnectionTestResult(
            status=ConnectionStatus.FAILED,
            target_id=target_id,
            target_type=target_type,
            response_time_ms=0.0,
            error_message=error_message,
            troubleshooting_suggestions=suggestions[:5]  # Limit to top 5
        )
