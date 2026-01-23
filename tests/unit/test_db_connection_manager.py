"""
Unit tests for DBConnectionManager.

Tests basic functionality, error handling, and timeout enforcement.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.admin.db_connection_manager import (
    DBConnectionManager,
    DBConfig,
    TestResult,
    SchemaInfo,
    QueryResult,
    DatabaseConfig
)
from src.admin.schemas import DatabaseType


class TestDatabaseConfig:
    """Test DatabaseConfig class."""
    
    def test_get_config_postgresql(self):
        """Test getting PostgreSQL configuration."""
        config = DatabaseConfig.get_config(DatabaseType.POSTGRESQL)
        assert config["default_port"] == 5432
        assert config["test_query"] == "SELECT 1"
        assert config["driver"] == "asyncpg"
    
    def test_get_config_mysql(self):
        """Test getting MySQL configuration."""
        config = DatabaseConfig.get_config(DatabaseType.MYSQL)
        assert config["default_port"] == 3306
        assert config["test_query"] == "SELECT 1"
        assert config["driver"] == "aiomysql"
    
    def test_get_default_port(self):
        """Test getting default port."""
        assert DatabaseConfig.get_default_port(DatabaseType.POSTGRESQL) == 5432
        assert DatabaseConfig.get_default_port(DatabaseType.MYSQL) == 3306
        assert DatabaseConfig.get_default_port(DatabaseType.ORACLE) == 1521
        assert DatabaseConfig.get_default_port(DatabaseType.SQLSERVER) == 1433


class TestDBConnectionManager:
    """Test DBConnectionManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a DBConnectionManager instance."""
        return DBConnectionManager()
    
    @pytest.fixture
    def pg_config(self):
        """Create a PostgreSQL test configuration."""
        return DBConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
            ssl_enabled=False,
            read_only=True,
            timeout=15
        )
    
    @pytest.fixture
    def mysql_config(self):
        """Create a MySQL test configuration."""
        return DBConfig(
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            database="testdb",
            username="testuser",
            password="testpass",
            ssl_enabled=False,
            read_only=True,
            timeout=15
        )

    
    @pytest.mark.asyncio
    async def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager is not None
        assert manager._connection_pools == {}
        assert manager._lock is not None
    
    @pytest.mark.asyncio
    async def test_timeout_enforcement(self, manager, pg_config):
        """Test that connection test respects timeout."""
        # Set a very short timeout
        pg_config.timeout = 1
        
        # Mock the internal implementation to simulate a slow connection
        async def slow_test(config, db_config):
            await asyncio.sleep(2)  # Longer than timeout
            return TestResult(success=True, db_type="postgresql")
        
        with patch.object(manager, '_test_connection_impl', side_effect=slow_test):
            result = await manager.test_connection(pg_config)
            
            assert result.success is False
            assert result.error_code == "TIMEOUT"
            assert "timeout" in result.error_message.lower()
            assert len(result.suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_missing_driver_postgresql(self, manager, pg_config):
        """Test handling of missing asyncpg driver."""
        # Mock the _test_postgresql method to simulate missing driver
        async def mock_test_pg(config, db_config):
            return TestResult(
                success=False,
                db_type="postgresql",
                error_message="asyncpg package is not installed",
                error_code="MISSING_DRIVER"
            )
        
        with patch.object(manager, '_test_postgresql', side_effect=mock_test_pg):
            result = await manager.test_connection(pg_config)
            
            assert result.success is False
            assert result.error_code == "MISSING_DRIVER"
            assert "asyncpg" in result.error_message
    
    @pytest.mark.asyncio
    async def test_missing_driver_mysql(self, manager, mysql_config):
        """Test handling of missing aiomysql driver."""
        # Mock the _test_mysql method to simulate missing driver
        async def mock_test_mysql(config, db_config):
            return TestResult(
                success=False,
                db_type="mysql",
                error_message="aiomysql package is not installed",
                error_code="MISSING_DRIVER"
            )
        
        with patch.object(manager, '_test_mysql', side_effect=mock_test_mysql):
            result = await manager.test_connection(mysql_config)
            
            assert result.success is False
            assert result.error_code == "MISSING_DRIVER"
            assert "aiomysql" in result.error_message
    
    @pytest.mark.asyncio
    async def test_unsupported_database_type(self, manager):
        """Test handling of unsupported database type."""
        # Create a config with SQLite (not fully supported in this implementation)
        config = DBConfig(
            db_type=DatabaseType.SQLITE,
            host="localhost",
            port=0,
            database="test.db",
            username="",
            password="",
            timeout=15
        )
        
        result = await manager.test_connection(config)
        
        assert result.success is False
        assert result.error_code == "UNSUPPORTED_DB_TYPE"
    
    @pytest.mark.asyncio
    async def test_read_only_query_validation(self, manager, pg_config):
        """Test that write queries are rejected in read-only mode."""
        # Test INSERT
        with pytest.raises(ValueError, match="Write operation.*not allowed"):
            await manager.execute_test_query(pg_config, "INSERT INTO users VALUES (1, 'test')")
        
        # Test UPDATE
        with pytest.raises(ValueError, match="Write operation.*not allowed"):
            await manager.execute_test_query(pg_config, "UPDATE users SET name='test'")
        
        # Test DELETE
        with pytest.raises(ValueError, match="Write operation.*not allowed"):
            await manager.execute_test_query(pg_config, "DELETE FROM users")
        
        # Test DROP
        with pytest.raises(ValueError, match="Write operation.*not allowed"):
            await manager.execute_test_query(pg_config, "DROP TABLE users")
    
    @pytest.mark.asyncio
    async def test_query_limit_addition(self, manager, pg_config):
        """Test that LIMIT clause is added to queries."""
        query = "SELECT * FROM users"
        
        # Mock the actual execution
        with patch.object(manager, '_execute_postgresql_query') as mock_exec:
            mock_exec.return_value = QueryResult(
                columns=['id', 'name'],
                rows=[],
                row_count=0
            )
            
            await manager.execute_test_query(pg_config, query, limit=50)
            
            # Verify LIMIT was added
            called_query = mock_exec.call_args[0][1]
            assert 'LIMIT 50' in called_query
    
    @pytest.mark.asyncio
    async def test_get_connection(self, manager):
        """Test getting connection from pool."""
        # Initially empty
        conn = await manager.get_connection("test-config-id")
        assert conn is None
        
        # Add a mock connection
        mock_conn = Mock()
        manager._connection_pools["test-config-id"] = mock_conn
        
        conn = await manager.get_connection("test-config-id")
        assert conn == mock_conn
    
    @pytest.mark.asyncio
    async def test_close_all_connections(self, manager):
        """Test closing all connection pools."""
        # Add mock connections
        mock_conn1 = AsyncMock()
        mock_conn2 = Mock()
        mock_conn2.close = Mock()
        
        manager._connection_pools["config1"] = mock_conn1
        manager._connection_pools["config2"] = mock_conn2
        
        await manager.close_all_connections()
        
        # Verify all connections closed
        assert len(manager._connection_pools) == 0
        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()


class TestTestResult:
    """Test TestResult model."""
    
    def test_test_result_creation(self):
        """Test creating a TestResult."""
        result = TestResult(
            success=True,
            db_type="postgresql",
            latency_ms=123.45,
            server_version="PostgreSQL 15.0"
        )
        
        assert result.success is True
        assert result.db_type == "postgresql"
        assert result.latency_ms == 123.45
        assert result.server_version == "PostgreSQL 15.0"
        assert result.error_message is None
        assert result.error_code is None
        assert result.suggestions == []
    
    def test_test_result_with_error(self):
        """Test creating a TestResult with error."""
        result = TestResult(
            success=False,
            db_type="mysql",
            error_message="Connection failed",
            error_code="CONNECTION_ERROR",
            suggestions=["Check network", "Verify credentials"]
        )
        
        assert result.success is False
        assert result.error_message == "Connection failed"
        assert result.error_code == "CONNECTION_ERROR"
        assert len(result.suggestions) == 2


class TestSchemaInfo:
    """Test SchemaInfo model."""
    
    def test_schema_info_creation(self):
        """Test creating SchemaInfo."""
        schema = SchemaInfo(
            tables=["users", "posts", "comments"],
            views=["user_stats"],
            total_tables=3,
            total_views=1,
            database_name="testdb",
            schema_name="public"
        )
        
        assert len(schema.tables) == 3
        assert len(schema.views) == 1
        assert schema.total_tables == 3
        assert schema.total_views == 1
        assert schema.database_name == "testdb"
        assert schema.schema_name == "public"


class TestQueryResult:
    """Test QueryResult model."""
    
    def test_query_result_creation(self):
        """Test creating QueryResult."""
        result = QueryResult(
            columns=["id", "name", "email"],
            rows=[
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"}
            ],
            row_count=2,
            execution_time_ms=45.67,
            truncated=False
        )
        
        assert len(result.columns) == 3
        assert len(result.rows) == 2
        assert result.row_count == 2
        assert result.execution_time_ms == 45.67
        assert result.truncated is False
