"""
Database Connection Manager for SuperInsight Platform.

Manages database connection configurations, connection testing, and connection pooling.
Supports multiple database types including MySQL, PostgreSQL, Oracle, and SQL Server.

This module follows async-first architecture using asyncio and async database drivers.
All I/O operations are non-blocking to prevent event loop blocking.

Validates Requirements: 2.4, 2.6, 2.7
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

import aiohttp
from pydantic import BaseModel, Field

from src.admin.schemas import (
    DatabaseType,
    ConnectionTestResult,
    DBConfigResponse
)


logger = logging.getLogger(__name__)


# ============== Database-Specific Models ==============

class TestResult(BaseModel):
    """Database connection test result with detailed information."""
    success: bool = Field(..., description="Whether test succeeded")
    db_type: str = Field(..., description="Database type")
    latency_ms: float = Field(default=0.0, description="Connection latency in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    tested_at: datetime = Field(default_factory=datetime.utcnow)
    suggestions: List[str] = Field(default_factory=list, description="Troubleshooting suggestions")
    server_version: Optional[str] = Field(default=None, description="Database server version")


class SchemaInfo(BaseModel):
    """Database schema information."""
    tables: List[str] = Field(default_factory=list, description="List of table names")
    views: List[str] = Field(default_factory=list, description="List of view names")
    total_tables: int = Field(default=0, description="Total number of tables")
    total_views: int = Field(default=0, description="Total number of views")
    database_name: str = Field(..., description="Database name")
    schema_name: Optional[str] = Field(default=None, description="Schema name if applicable")


class QueryResult(BaseModel):
    """Query execution result."""
    columns: List[str] = Field(default_factory=list, description="Column names")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Result rows")
    row_count: int = Field(default=0, description="Number of rows returned")
    execution_time_ms: float = Field(default=0.0, description="Execution time in milliseconds")
    truncated: bool = Field(default=False, description="Whether results were truncated")


class DBConfig(BaseModel):
    """Database configuration for connection testing."""
    db_type: DatabaseType = Field(..., description="Database type")
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_cert: Optional[str] = Field(default=None, description="SSL certificate")
    read_only: bool = Field(default=True, description="Read-only mode")
    connection_pool: Optional[Dict[str, Any]] = Field(default=None, description="Connection pool config")
    timeout: int = Field(default=15, description="Connection timeout in seconds")



# ============== Database Configuration ==============

class DatabaseConfig:
    """Database-specific configuration and connection parameters."""
    
    DATABASES = {
        DatabaseType.MYSQL: {
            "default_port": 3306,
            "test_query": "SELECT 1",
            "version_query": "SELECT VERSION()",
            "driver": "aiomysql",
            "ssl_param": "ssl",
        },
        DatabaseType.POSTGRESQL: {
            "default_port": 5432,
            "test_query": "SELECT 1",
            "version_query": "SELECT version()",
            "driver": "asyncpg",
            "ssl_param": "ssl",
        },
        DatabaseType.ORACLE: {
            "default_port": 1521,
            "test_query": "SELECT 1 FROM DUAL",
            "version_query": "SELECT * FROM v$version WHERE banner LIKE 'Oracle%'",
            "driver": "cx_Oracle",
            "ssl_param": "ssl_context",
        },
        DatabaseType.SQLSERVER: {
            "default_port": 1433,
            "test_query": "SELECT 1",
            "version_query": "SELECT @@VERSION",
            "driver": "aioodbc",
            "ssl_param": "TrustServerCertificate",
        },
    }
    
    @classmethod
    def get_config(cls, db_type: DatabaseType) -> Dict[str, Any]:
        """Get configuration for a database type."""
        return cls.DATABASES.get(db_type, {})
    
    @classmethod
    def get_default_port(cls, db_type: DatabaseType) -> int:
        """Get default port for a database type."""
        config = cls.get_config(db_type)
        return config.get("default_port", 5432)



# ============== Database Connection Manager ==============

class DBConnectionManager:
    """
    Manages database connection configurations and operations.
    
    Features:
    - Connection testing with timeout enforcement (15 seconds)
    - Support for MySQL, PostgreSQL, Oracle, SQL Server
    - SSL/TLS support for secure connections
    - Read-only mode enforcement
    - Connection pooling configuration
    - Detailed error reporting with troubleshooting suggestions
    
    All operations are async to prevent blocking the event loop.
    
    Validates Requirements: 2.4, 2.6, 2.7
    """
    
    def __init__(self):
        """Initialize the database connection manager."""
        self._connection_pools: Dict[str, Any] = {}
        self._lock = asyncio.Lock()  # Async lock for thread-safe operations
        logger.info("DBConnectionManager initialized")
    
    async def test_connection(
        self,
        config: DBConfig
    ) -> TestResult:
        """
        Test connection to a database.
        
        Args:
            config: Database configuration
        
        Returns:
            TestResult with success status and details
        
        Validates Requirements: 2.4
        """
        start_time = asyncio.get_event_loop().time()
        db_config = DatabaseConfig.get_config(config.db_type)
        
        try:
            # Enforce timeout using asyncio.wait_for
            result = await asyncio.wait_for(
                self._test_connection_impl(config, db_config),
                timeout=config.timeout
            )
            
            end_time = asyncio.get_event_loop().time()
            result.latency_ms = (end_time - start_time) * 1000
            
            return result
        
        except asyncio.TimeoutError:
            logger.warning(
                f"Connection test timeout for {config.db_type} "
                f"({config.host}:{config.port}) after {config.timeout}s"
            )
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                latency_ms=config.timeout * 1000,
                error_message=f"Connection timeout after {config.timeout} seconds",
                error_code="TIMEOUT",
                suggestions=[
                    "Check network connectivity to database server",
                    "Verify database host and port are correct",
                    "Check if firewall is blocking connection",
                    "Ensure database server is running",
                    "Try increasing timeout value"
                ]
            )
        
        except Exception as e:
            logger.error(f"Unexpected error testing {config.db_type}: {e}", exc_info=True)
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                suggestions=[
                    "Check logs for detailed error information",
                    "Verify configuration is correct",
                    "Contact support if issue persists"
                ]
            )

    
    async def _test_connection_impl(
        self,
        config: DBConfig,
        db_config: Dict[str, Any]
    ) -> TestResult:
        """
        Internal implementation of connection testing.
        
        Args:
            config: Database configuration
            db_config: Database-specific configuration
        
        Returns:
            TestResult with connection status
        """
        if config.db_type == DatabaseType.POSTGRESQL:
            return await self._test_postgresql(config, db_config)
        elif config.db_type == DatabaseType.MYSQL:
            return await self._test_mysql(config, db_config)
        elif config.db_type == DatabaseType.ORACLE:
            return await self._test_oracle(config, db_config)
        elif config.db_type == DatabaseType.SQLSERVER:
            return await self._test_sqlserver(config, db_config)
        else:
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message=f"Unsupported database type: {config.db_type}",
                error_code="UNSUPPORTED_DB_TYPE",
                suggestions=[
                    f"Supported types: {', '.join([t.value for t in DatabaseType])}"
                ]
            )

    
    async def _test_postgresql(
        self,
        config: DBConfig,
        db_config: Dict[str, Any]
    ) -> TestResult:
        """Test PostgreSQL connection."""
        try:
            import asyncpg
        except ImportError:
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message="asyncpg package is not installed",
                error_code="MISSING_DRIVER",
                suggestions=[
                    "Install asyncpg: pip install asyncpg",
                    "Ensure PostgreSQL client libraries are installed"
                ]
            )
        
        try:
            # Build connection parameters
            conn_params = {
                "host": config.host,
                "port": config.port,
                "database": config.database,
                "user": config.username,
                "password": config.password,
                "timeout": config.timeout,
            }
            
            # Add SSL configuration if enabled
            if config.ssl_enabled:
                conn_params["ssl"] = "require"
            
            # Connect to database
            conn = await asyncpg.connect(**conn_params)
            
            try:
                # Set read-only mode if configured
                if config.read_only:
                    await conn.execute("SET default_transaction_read_only = ON")
                
                # Execute test query
                await conn.fetchval(db_config["test_query"])
                
                # Get server version
                version = await conn.fetchval(db_config["version_query"])
                
                logger.info(
                    f"PostgreSQL connection test successful: "
                    f"{config.host}:{config.port}/{config.database}"
                )
                
                return TestResult(
                    success=True,
                    db_type=config.db_type.value,
                    server_version=str(version),
                    details={
                        "host": config.host,
                        "port": config.port,
                        "database": config.database,
                        "ssl_enabled": config.ssl_enabled,
                        "read_only": config.read_only
                    }
                )
            
            finally:
                await conn.close()
        
        except asyncpg.InvalidPasswordError:
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message="Authentication failed - invalid username or password",
                error_code="AUTH_FAILED",
                suggestions=[
                    "Verify username and password are correct",
                    "Check if user has permission to access the database",
                    "Ensure user account is not locked"
                ]
            )
        
        except asyncpg.InvalidCatalogNameError:
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message=f"Database '{config.database}' does not exist",
                error_code="DATABASE_NOT_FOUND",
                suggestions=[
                    "Verify database name is correct",
                    "Check if database has been created",
                    "List available databases on the server"
                ]
            )
        
        except asyncpg.CannotConnectNowError:
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message="Database is not accepting connections",
                error_code="DB_NOT_READY",
                suggestions=[
                    "Check if PostgreSQL server is running",
                    "Verify server is not in recovery mode",
                    "Check server logs for startup issues"
                ]
            )
        
        except asyncpg.PostgresConnectionError as e:
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message=f"Connection failed: {str(e)}",
                error_code="CONNECTION_ERROR",
                suggestions=[
                    "Verify host and port are correct",
                    "Check network connectivity",
                    "Ensure PostgreSQL is listening on the specified port",
                    "Check pg_hba.conf for access restrictions"
                ]
            )
        
        except Exception as e:
            logger.error(f"PostgreSQL connection test error: {e}", exc_info=True)
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message=f"Connection error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                suggestions=[
                    "Check logs for detailed error information",
                    "Verify all connection parameters",
                    "Contact database administrator"
                ]
            )

    
    async def _test_mysql(
        self,
        config: DBConfig,
        db_config: Dict[str, Any]
    ) -> TestResult:
        """Test MySQL connection."""
        try:
            import aiomysql
        except ImportError:
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message="aiomysql package is not installed",
                error_code="MISSING_DRIVER",
                suggestions=[
                    "Install aiomysql: pip install aiomysql",
                    "Ensure MySQL client libraries are installed"
                ]
            )
        
        try:
            # Build connection parameters
            conn_params = {
                "host": config.host,
                "port": config.port,
                "db": config.database,
                "user": config.username,
                "password": config.password,
                "connect_timeout": config.timeout,
            }
            
            # Add SSL configuration if enabled
            if config.ssl_enabled:
                conn_params["ssl"] = {"check_hostname": False}
            
            # Connect to database
            conn = await aiomysql.connect(**conn_params)
            
            try:
                async with conn.cursor() as cursor:
                    # Set read-only mode if configured
                    if config.read_only:
                        await cursor.execute("SET SESSION TRANSACTION READ ONLY")
                    
                    # Execute test query
                    await cursor.execute(db_config["test_query"])
                    await cursor.fetchone()
                    
                    # Get server version
                    await cursor.execute(db_config["version_query"])
                    version_row = await cursor.fetchone()
                    version = version_row[0] if version_row else "Unknown"
                
                logger.info(
                    f"MySQL connection test successful: "
                    f"{config.host}:{config.port}/{config.database}"
                )
                
                return TestResult(
                    success=True,
                    db_type=config.db_type.value,
                    server_version=str(version),
                    details={
                        "host": config.host,
                        "port": config.port,
                        "database": config.database,
                        "ssl_enabled": config.ssl_enabled,
                        "read_only": config.read_only
                    }
                )
            
            finally:
                conn.close()
        
        except aiomysql.OperationalError as e:
            error_code = e.args[0] if e.args else 0
            error_msg = e.args[1] if len(e.args) > 1 else str(e)
            
            if error_code == 1045:  # Access denied
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message="Authentication failed - invalid username or password",
                    error_code="AUTH_FAILED",
                    suggestions=[
                        "Verify username and password are correct",
                        "Check if user has permission to access the database",
                        "Ensure user is allowed to connect from this host"
                    ]
                )
            elif error_code == 1049:  # Unknown database
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message=f"Database '{config.database}' does not exist",
                    error_code="DATABASE_NOT_FOUND",
                    suggestions=[
                        "Verify database name is correct",
                        "Check if database has been created",
                        "List available databases: SHOW DATABASES"
                    ]
                )
            elif error_code == 2003:  # Can't connect
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message=f"Cannot connect to MySQL server: {error_msg}",
                    error_code="CONNECTION_ERROR",
                    suggestions=[
                        "Verify host and port are correct",
                        "Check if MySQL server is running",
                        "Ensure firewall allows connection",
                        "Check bind-address in MySQL configuration"
                    ]
                )
            else:
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message=f"MySQL error {error_code}: {error_msg}",
                    error_code=f"MYSQL_ERROR_{error_code}",
                    suggestions=[
                        "Check MySQL server logs",
                        "Verify connection parameters",
                        "Contact database administrator"
                    ]
                )
        
        except Exception as e:
            logger.error(f"MySQL connection test error: {e}", exc_info=True)
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message=f"Connection error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                suggestions=[
                    "Check logs for detailed error information",
                    "Verify all connection parameters",
                    "Contact database administrator"
                ]
            )

    
    async def _test_oracle(
        self,
        config: DBConfig,
        db_config: Dict[str, Any]
    ) -> TestResult:
        """Test Oracle connection."""
        try:
            import cx_Oracle
        except ImportError:
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message="cx_Oracle package is not installed",
                error_code="MISSING_DRIVER",
                suggestions=[
                    "Install cx_Oracle: pip install cx_Oracle",
                    "Ensure Oracle Instant Client is installed",
                    "Set LD_LIBRARY_PATH to Oracle client libraries"
                ]
            )
        
        try:
            # Build connection string (DSN format)
            dsn = cx_Oracle.makedsn(
                config.host,
                config.port,
                service_name=config.database
            )
            
            # Run connection in executor since cx_Oracle is synchronous
            loop = asyncio.get_event_loop()
            
            def _connect_oracle():
                """Synchronous Oracle connection."""
                conn = cx_Oracle.connect(
                    user=config.username,
                    password=config.password,
                    dsn=dsn,
                    encoding="UTF-8"
                )
                
                try:
                    cursor = conn.cursor()
                    
                    # Set read-only mode if configured
                    if config.read_only:
                        cursor.execute("SET TRANSACTION READ ONLY")
                    
                    # Execute test query
                    cursor.execute(db_config["test_query"])
                    cursor.fetchone()
                    
                    # Get server version
                    cursor.execute(db_config["version_query"])
                    version_row = cursor.fetchone()
                    version = version_row[0] if version_row else "Unknown"
                    
                    cursor.close()
                    return True, version, None
                
                except Exception as e:
                    return False, None, str(e)
                
                finally:
                    conn.close()
            
            # Execute in thread pool to avoid blocking
            success, version, error = await loop.run_in_executor(None, _connect_oracle)
            
            if success:
                logger.info(
                    f"Oracle connection test successful: "
                    f"{config.host}:{config.port}/{config.database}"
                )
                
                return TestResult(
                    success=True,
                    db_type=config.db_type.value,
                    server_version=str(version),
                    details={
                        "host": config.host,
                        "port": config.port,
                        "database": config.database,
                        "ssl_enabled": config.ssl_enabled,
                        "read_only": config.read_only
                    }
                )
            else:
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message=f"Oracle connection failed: {error}",
                    error_code="CONNECTION_ERROR",
                    suggestions=[
                        "Verify connection parameters",
                        "Check Oracle listener status",
                        "Ensure service name is correct",
                        "Check tnsnames.ora configuration"
                    ]
                )
        
        except cx_Oracle.DatabaseError as e:
            error_obj, = e.args
            error_code = error_obj.code
            error_msg = error_obj.message
            
            if error_code == 1017:  # Invalid username/password
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message="Authentication failed - invalid username or password",
                    error_code="AUTH_FAILED",
                    suggestions=[
                        "Verify username and password are correct",
                        "Check if user account is locked",
                        "Ensure user has CREATE SESSION privilege"
                    ]
                )
            elif error_code == 12154:  # TNS:could not resolve
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message=f"Cannot resolve service name: {config.database}",
                    error_code="SERVICE_NOT_FOUND",
                    suggestions=[
                        "Verify service name is correct",
                        "Check tnsnames.ora configuration",
                        "Ensure Oracle listener is running",
                        "Try using SID instead of service name"
                    ]
                )
            elif error_code == 12541:  # TNS:no listener
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message="Oracle listener is not running",
                    error_code="NO_LISTENER",
                    suggestions=[
                        "Start Oracle listener: lsnrctl start",
                        "Verify listener is configured correctly",
                        "Check listener.ora configuration",
                        "Ensure correct port is specified"
                    ]
                )
            else:
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message=f"Oracle error {error_code}: {error_msg}",
                    error_code=f"ORACLE_ERROR_{error_code}",
                    suggestions=[
                        "Check Oracle server logs",
                        "Verify connection parameters",
                        "Contact database administrator"
                    ]
                )
        
        except Exception as e:
            logger.error(f"Oracle connection test error: {e}", exc_info=True)
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message=f"Connection error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                suggestions=[
                    "Check logs for detailed error information",
                    "Verify Oracle client is properly installed",
                    "Contact database administrator"
                ]
            )

    
    async def _test_sqlserver(
        self,
        config: DBConfig,
        db_config: Dict[str, Any]
    ) -> TestResult:
        """Test SQL Server connection."""
        try:
            import aioodbc
        except ImportError:
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message="aioodbc package is not installed",
                error_code="MISSING_DRIVER",
                suggestions=[
                    "Install aioodbc: pip install aioodbc",
                    "Install pyodbc: pip install pyodbc",
                    "Ensure ODBC driver for SQL Server is installed",
                    "On Linux: install unixODBC and msodbcsql17"
                ]
            )
        
        try:
            # Build connection string
            conn_str_parts = [
                f"DRIVER={{ODBC Driver 17 for SQL Server}}",
                f"SERVER={config.host},{config.port}",
                f"DATABASE={config.database}",
                f"UID={config.username}",
                f"PWD={config.password}",
            ]
            
            # Add SSL/TLS configuration
            if config.ssl_enabled:
                conn_str_parts.append("Encrypt=yes")
                conn_str_parts.append("TrustServerCertificate=no")
            else:
                conn_str_parts.append("TrustServerCertificate=yes")
            
            conn_str = ";".join(conn_str_parts)
            
            # Connect to database
            conn = await aioodbc.connect(
                dsn=conn_str,
                timeout=config.timeout
            )
            
            try:
                async with conn.cursor() as cursor:
                    # Execute test query
                    await cursor.execute(db_config["test_query"])
                    await cursor.fetchone()
                    
                    # Get server version
                    await cursor.execute(db_config["version_query"])
                    version_row = await cursor.fetchone()
                    version = version_row[0] if version_row else "Unknown"
                
                logger.info(
                    f"SQL Server connection test successful: "
                    f"{config.host}:{config.port}/{config.database}"
                )
                
                return TestResult(
                    success=True,
                    db_type=config.db_type.value,
                    server_version=str(version).split('\n')[0],  # First line only
                    details={
                        "host": config.host,
                        "port": config.port,
                        "database": config.database,
                        "ssl_enabled": config.ssl_enabled,
                        "read_only": config.read_only
                    }
                )
            
            finally:
                await conn.close()
        
        except aioodbc.Error as e:
            error_msg = str(e)
            
            # Parse common SQL Server errors
            if "Login failed" in error_msg or "18456" in error_msg:
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message="Authentication failed - invalid username or password",
                    error_code="AUTH_FAILED",
                    suggestions=[
                        "Verify username and password are correct",
                        "Check if SQL Server authentication is enabled",
                        "Ensure user has permission to access the database",
                        "Check if user account is locked"
                    ]
                )
            elif "Cannot open database" in error_msg or "4060" in error_msg:
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message=f"Database '{config.database}' does not exist or cannot be accessed",
                    error_code="DATABASE_NOT_FOUND",
                    suggestions=[
                        "Verify database name is correct",
                        "Check if database exists",
                        "Ensure user has permission to access the database",
                        "Check database status (online/offline)"
                    ]
                )
            elif "timeout" in error_msg.lower():
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message="Connection timeout",
                    error_code="TIMEOUT",
                    suggestions=[
                        "Check network connectivity",
                        "Verify SQL Server is running",
                        "Ensure TCP/IP protocol is enabled",
                        "Check firewall settings",
                        "Verify port number is correct (default: 1433)"
                    ]
                )
            elif "Named Pipes Provider" in error_msg or "could not open a connection" in error_msg:
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message=f"Cannot connect to SQL Server: {error_msg}",
                    error_code="CONNECTION_ERROR",
                    suggestions=[
                        "Verify server name and port are correct",
                        "Check if SQL Server is running",
                        "Ensure TCP/IP protocol is enabled in SQL Server Configuration Manager",
                        "Check firewall allows connection on port 1433",
                        "Verify SQL Server Browser service is running (for named instances)"
                    ]
                )
            else:
                return TestResult(
                    success=False,
                    db_type=config.db_type.value,
                    error_message=f"SQL Server error: {error_msg}",
                    error_code="SQLSERVER_ERROR",
                    suggestions=[
                        "Check SQL Server logs",
                        "Verify connection parameters",
                        "Ensure ODBC driver is properly installed",
                        "Contact database administrator"
                    ]
                )
        
        except Exception as e:
            logger.error(f"SQL Server connection test error: {e}", exc_info=True)
            return TestResult(
                success=False,
                db_type=config.db_type.value,
                error_message=f"Connection error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                suggestions=[
                    "Check logs for detailed error information",
                    "Verify ODBC driver is installed",
                    "Ensure all connection parameters are correct",
                    "Contact database administrator"
                ]
            )

    
    async def get_connection(
        self,
        config_id: str
    ) -> Optional[Any]:
        """
        Get a connection from the pool for a configuration.
        
        Args:
            config_id: Configuration ID
        
        Returns:
            Database connection or None if not found
        
        Note: This is a placeholder. In production, this would retrieve
        the configuration from database and create/return a pooled connection.
        """
        async with self._lock:
            return self._connection_pools.get(config_id)
    
    async def execute_test_query(
        self,
        config: DBConfig,
        query: str,
        limit: int = 100
    ) -> QueryResult:
        """
        Execute a test query on a database.
        
        Args:
            config: Database configuration
            query: SQL query to execute
            limit: Maximum number of rows to return
        
        Returns:
            QueryResult with query results
        
        Validates Requirements: 2.6 (read-only enforcement)
        """
        start_time = asyncio.get_event_loop().time()
        
        # Validate query is read-only
        query_upper = query.strip().upper()
        write_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']
        
        if config.read_only:
            for keyword in write_keywords:
                if query_upper.startswith(keyword):
                    raise ValueError(
                        f"Write operation '{keyword}' not allowed in read-only mode. "
                        f"Only SELECT queries are permitted."
                    )
        
        # Add LIMIT clause if not present
        if 'LIMIT' not in query_upper and config.db_type in [DatabaseType.MYSQL, DatabaseType.POSTGRESQL]:
            query = f"{query.rstrip(';')} LIMIT {limit}"
        elif 'TOP' not in query_upper and config.db_type == DatabaseType.SQLSERVER:
            # For SQL Server, add TOP clause
            query = query.replace('SELECT', f'SELECT TOP {limit}', 1)
        
        try:
            # Execute query based on database type
            if config.db_type == DatabaseType.POSTGRESQL:
                result = await self._execute_postgresql_query(config, query)
            elif config.db_type == DatabaseType.MYSQL:
                result = await self._execute_mysql_query(config, query)
            elif config.db_type == DatabaseType.ORACLE:
                result = await self._execute_oracle_query(config, query, limit)
            elif config.db_type == DatabaseType.SQLSERVER:
                result = await self._execute_sqlserver_query(config, query)
            else:
                raise ValueError(f"Unsupported database type: {config.db_type}")
            
            end_time = asyncio.get_event_loop().time()
            result.execution_time_ms = (end_time - start_time) * 1000
            result.truncated = result.row_count >= limit
            
            return result
        
        except Exception as e:
            logger.error(f"Query execution error: {e}", exc_info=True)
            raise

    
    async def _execute_postgresql_query(
        self,
        config: DBConfig,
        query: str
    ) -> QueryResult:
        """Execute query on PostgreSQL."""
        import asyncpg
        
        conn = await asyncpg.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.username,
            password=config.password,
            timeout=config.timeout
        )
        
        try:
            if config.read_only:
                await conn.execute("SET default_transaction_read_only = ON")
            
            rows = await conn.fetch(query)
            
            if rows:
                columns = list(rows[0].keys())
                rows_data = [dict(row) for row in rows]
            else:
                columns = []
                rows_data = []
            
            return QueryResult(
                columns=columns,
                rows=rows_data,
                row_count=len(rows_data)
            )
        
        finally:
            await conn.close()
    
    async def _execute_mysql_query(
        self,
        config: DBConfig,
        query: str
    ) -> QueryResult:
        """Execute query on MySQL."""
        import aiomysql
        
        conn = await aiomysql.connect(
            host=config.host,
            port=config.port,
            db=config.database,
            user=config.username,
            password=config.password,
            connect_timeout=config.timeout
        )
        
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if config.read_only:
                    await cursor.execute("SET SESSION TRANSACTION READ ONLY")
                
                await cursor.execute(query)
                rows = await cursor.fetchall()
                
                if rows:
                    columns = list(rows[0].keys())
                    rows_data = [dict(row) for row in rows]
                else:
                    columns = []
                    rows_data = []
                
                return QueryResult(
                    columns=columns,
                    rows=rows_data,
                    row_count=len(rows_data)
                )
        
        finally:
            conn.close()
    
    async def _execute_oracle_query(
        self,
        config: DBConfig,
        query: str,
        limit: int
    ) -> QueryResult:
        """Execute query on Oracle."""
        import cx_Oracle
        
        # Add ROWNUM limit for Oracle
        if 'ROWNUM' not in query.upper():
            query = f"SELECT * FROM ({query}) WHERE ROWNUM <= {limit}"
        
        loop = asyncio.get_event_loop()
        
        def _execute():
            dsn = cx_Oracle.makedsn(config.host, config.port, service_name=config.database)
            conn = cx_Oracle.connect(user=config.username, password=config.password, dsn=dsn)
            
            try:
                cursor = conn.cursor()
                
                if config.read_only:
                    cursor.execute("SET TRANSACTION READ ONLY")
                
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                rows_data = [dict(zip(columns, row)) for row in rows]
                
                cursor.close()
                return columns, rows_data
            
            finally:
                conn.close()
        
        columns, rows_data = await loop.run_in_executor(None, _execute)
        
        return QueryResult(
            columns=columns,
            rows=rows_data,
            row_count=len(rows_data)
        )
    
    async def _execute_sqlserver_query(
        self,
        config: DBConfig,
        query: str
    ) -> QueryResult:
        """Execute query on SQL Server."""
        import aioodbc
        
        conn_str_parts = [
            f"DRIVER={{ODBC Driver 17 for SQL Server}}",
            f"SERVER={config.host},{config.port}",
            f"DATABASE={config.database}",
            f"UID={config.username}",
            f"PWD={config.password}",
            "TrustServerCertificate=yes"
        ]
        
        conn_str = ";".join(conn_str_parts)
        conn = await aioodbc.connect(dsn=conn_str, timeout=config.timeout)
        
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()
                
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows_data = [dict(zip(columns, row)) for row in rows]
                else:
                    columns = []
                    rows_data = []
                
                return QueryResult(
                    columns=columns,
                    rows=rows_data,
                    row_count=len(rows_data)
                )
        
        finally:
            await conn.close()

    
    async def validate_schema(
        self,
        config: DBConfig
    ) -> SchemaInfo:
        """
        Validate and retrieve schema information from a database.
        
        Args:
            config: Database configuration
        
        Returns:
            SchemaInfo with database schema details
        
        Validates Requirements: 2.4
        """
        try:
            if config.db_type == DatabaseType.POSTGRESQL:
                return await self._validate_postgresql_schema(config)
            elif config.db_type == DatabaseType.MYSQL:
                return await self._validate_mysql_schema(config)
            elif config.db_type == DatabaseType.ORACLE:
                return await self._validate_oracle_schema(config)
            elif config.db_type == DatabaseType.SQLSERVER:
                return await self._validate_sqlserver_schema(config)
            else:
                raise ValueError(f"Unsupported database type: {config.db_type}")
        
        except Exception as e:
            logger.error(f"Schema validation error: {e}", exc_info=True)
            raise
    
    async def _validate_postgresql_schema(self, config: DBConfig) -> SchemaInfo:
        """Get PostgreSQL schema information."""
        import asyncpg
        
        conn = await asyncpg.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.username,
            password=config.password,
            timeout=config.timeout
        )
        
        try:
            # Get tables
            tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            table_rows = await conn.fetch(tables_query)
            tables = [row['table_name'] for row in table_rows]
            
            # Get views
            views_query = """
                SELECT table_name 
                FROM information_schema.views 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            view_rows = await conn.fetch(views_query)
            views = [row['table_name'] for row in view_rows]
            
            return SchemaInfo(
                tables=tables,
                views=views,
                total_tables=len(tables),
                total_views=len(views),
                database_name=config.database,
                schema_name='public'
            )
        
        finally:
            await conn.close()
    
    async def _validate_mysql_schema(self, config: DBConfig) -> SchemaInfo:
        """Get MySQL schema information."""
        import aiomysql
        
        conn = await aiomysql.connect(
            host=config.host,
            port=config.port,
            db=config.database,
            user=config.username,
            password=config.password,
            connect_timeout=config.timeout
        )
        
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # Get tables
                await cursor.execute(f"SHOW TABLES FROM `{config.database}`")
                table_rows = await cursor.fetchall()
                tables = [list(row.values())[0] for row in table_rows]
                
                # Get views
                await cursor.execute(
                    f"SELECT table_name FROM information_schema.views "
                    f"WHERE table_schema = '{config.database}'"
                )
                view_rows = await cursor.fetchall()
                views = [row['table_name'] for row in view_rows]
                
                return SchemaInfo(
                    tables=tables,
                    views=views,
                    total_tables=len(tables),
                    total_views=len(views),
                    database_name=config.database
                )
        
        finally:
            conn.close()
    
    async def _validate_oracle_schema(self, config: DBConfig) -> SchemaInfo:
        """Get Oracle schema information."""
        import cx_Oracle
        
        loop = asyncio.get_event_loop()
        
        def _get_schema():
            dsn = cx_Oracle.makedsn(config.host, config.port, service_name=config.database)
            conn = cx_Oracle.connect(user=config.username, password=config.password, dsn=dsn)
            
            try:
                cursor = conn.cursor()
                
                # Get tables
                cursor.execute(
                    "SELECT table_name FROM user_tables ORDER BY table_name"
                )
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get views
                cursor.execute(
                    "SELECT view_name FROM user_views ORDER BY view_name"
                )
                views = [row[0] for row in cursor.fetchall()]
                
                cursor.close()
                return tables, views
            
            finally:
                conn.close()
        
        tables, views = await loop.run_in_executor(None, _get_schema)
        
        return SchemaInfo(
            tables=tables,
            views=views,
            total_tables=len(tables),
            total_views=len(views),
            database_name=config.database,
            schema_name=config.username.upper()
        )
    
    async def _validate_sqlserver_schema(self, config: DBConfig) -> SchemaInfo:
        """Get SQL Server schema information."""
        import aioodbc
        
        conn_str_parts = [
            f"DRIVER={{ODBC Driver 17 for SQL Server}}",
            f"SERVER={config.host},{config.port}",
            f"DATABASE={config.database}",
            f"UID={config.username}",
            f"PWD={config.password}",
            "TrustServerCertificate=yes"
        ]
        
        conn_str = ";".join(conn_str_parts)
        conn = await aioodbc.connect(dsn=conn_str, timeout=config.timeout)
        
        try:
            async with conn.cursor() as cursor:
                # Get tables
                await cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_type = 'BASE TABLE' ORDER BY table_name"
                )
                table_rows = await cursor.fetchall()
                tables = [row[0] for row in table_rows]
                
                # Get views
                await cursor.execute(
                    "SELECT table_name FROM information_schema.views "
                    "ORDER BY table_name"
                )
                view_rows = await cursor.fetchall()
                views = [row[0] for row in view_rows]
                
                return SchemaInfo(
                    tables=tables,
                    views=views,
                    total_tables=len(tables),
                    total_views=len(views),
                    database_name=config.database,
                    schema_name='dbo'
                )
        
        finally:
            await conn.close()
    
    async def close_all_connections(self) -> None:
        """
        Close all connection pools.
        
        This should be called during application shutdown.
        """
        async with self._lock:
            for config_id, pool in self._connection_pools.items():
                try:
                    if hasattr(pool, 'close'):
                        if asyncio.iscoroutinefunction(pool.close):
                            await pool.close()
                        else:
                            pool.close()
                    logger.info(f"Closed connection pool for config {config_id}")
                except Exception as e:
                    logger.error(f"Error closing connection pool {config_id}: {e}")
            
            self._connection_pools.clear()
            logger.info("All connection pools closed")
