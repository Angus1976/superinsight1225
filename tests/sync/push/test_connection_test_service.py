"""
Tests for Connection Test Service.

Validates connection testing and troubleshooting functionality.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from src.sync.push.connection_test_service import (
    ConnectionTestService,
    ConnectionStatus,
    ConnectionTestResult
)
from src.sync.models import DataSourceModel, DataSourceType
from src.database.connection import db_manager


@pytest.fixture
async def connection_test_service():
    """Create connection test service."""
    return ConnectionTestService()


@pytest.fixture
async def postgresql_source(db_session):
    """Create PostgreSQL data source."""
    source = DataSourceModel(
        id=uuid4(),
        tenant_id="test-tenant",
        name="Test PostgreSQL",
        source_type=DataSourceType.POSTGRESQL,
        connection_config={
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "testuser",
            "password": "testpass"
        },
        created_at=datetime.utcnow()
    )
    db_session.add(source)
    await db_session.commit()
    return source


@pytest.fixture
async def incomplete_source(db_session):
    """Create data source with incomplete config."""
    source = DataSourceModel(
        id=uuid4(),
        tenant_id="test-tenant",
        name="Incomplete Source",
        source_type=DataSourceType.POSTGRESQL,
        connection_config={
            "host": "localhost"
            # Missing port, database, username
        },
        created_at=datetime.utcnow()
    )
    db_session.add(source)
    await db_session.commit()
    return source


class TestConnectionTestService:
    """Test connection test service."""
    
    @pytest.mark.asyncio
    async def test_test_connection_success(
        self,
        connection_test_service,
        postgresql_source
    ):
        """Test successful connection test."""
        result = await connection_test_service.test_connection(
            postgresql_source.id
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_id == str(postgresql_source.id)
        assert result.target_type == "postgresql"
        assert result.error_message is None
        assert result.response_time_ms >= 0
        assert "host" in result.connection_details
    
    @pytest.mark.asyncio
    async def test_test_connection_not_found(
        self,
        connection_test_service
    ):
        """Test connection test with non-existent source."""
        fake_id = uuid4()
        result = await connection_test_service.test_connection(fake_id)
        
        assert result.status == ConnectionStatus.FAILED
        assert result.error_message == "Target data source not found"
        assert len(result.troubleshooting_suggestions) > 0
        assert any(
            "verify" in s.lower()
            for s in result.troubleshooting_suggestions
        )
    
    @pytest.mark.asyncio
    async def test_test_connection_incomplete_config(
        self,
        connection_test_service,
        incomplete_source
    ):
        """Test connection test with incomplete configuration."""
        result = await connection_test_service.test_connection(
            incomplete_source.id
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert "missing required fields" in result.error_message.lower()
        assert len(result.troubleshooting_suggestions) > 0
        
        # Should suggest adding missing fields
        suggestions_text = " ".join(result.troubleshooting_suggestions).lower()
        assert "configuration" in suggestions_text
    
    @pytest.mark.asyncio
    async def test_postgresql_connection_validation(
        self,
        connection_test_service
    ):
        """Test PostgreSQL connection validation."""
        # Valid config
        result = await connection_test_service._test_postgresql_connection(
            {
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "username": "user"
            },
            "test-id"
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_type == "postgresql"
    
    @pytest.mark.asyncio
    async def test_postgresql_missing_fields(
        self,
        connection_test_service
    ):
        """Test PostgreSQL with missing required fields."""
        result = await connection_test_service._test_postgresql_connection(
            {"host": "localhost"},  # Missing port, database, username
            "test-id"
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert "missing required fields" in result.error_message.lower()
        assert "port" in result.error_message
        assert "database" in result.error_message
    
    @pytest.mark.asyncio
    async def test_mysql_connection_validation(
        self,
        connection_test_service
    ):
        """Test MySQL connection validation."""
        result = await connection_test_service._test_mysql_connection(
            {
                "host": "localhost",
                "port": 3306,
                "database": "testdb",
                "username": "user"
            },
            "test-id"
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_type == "mysql"
    
    @pytest.mark.asyncio
    async def test_mongodb_connection_validation(
        self,
        connection_test_service
    ):
        """Test MongoDB connection validation."""
        # With connection string
        result = await connection_test_service._test_mongodb_connection(
            {"connection_string": "mongodb://localhost:27017/testdb"},
            "test-id"
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_type == "mongodb"
        
        # With host
        result = await connection_test_service._test_mongodb_connection(
            {"host": "localhost", "database": "testdb"},
            "test-id"
        )
        
        assert result.status == ConnectionStatus.SUCCESS
    
    @pytest.mark.asyncio
    async def test_mongodb_missing_connection_info(
        self,
        connection_test_service
    ):
        """Test MongoDB with missing connection info."""
        result = await connection_test_service._test_mongodb_connection(
            {},  # No connection_string or host
            "test-id"
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert "connection_string" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_api_connection_validation(
        self,
        connection_test_service
    ):
        """Test API connection validation."""
        result = await connection_test_service._test_api_connection(
            {
                "endpoint_url": "https://api.example.com/data",
                "method": "POST"
            },
            "test-id"
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_type == "api"
        assert "endpoint_url" in result.connection_details
    
    @pytest.mark.asyncio
    async def test_api_missing_endpoint(
        self,
        connection_test_service
    ):
        """Test API with missing endpoint URL."""
        result = await connection_test_service._test_api_connection(
            {},  # No endpoint_url
            "test-id"
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert "endpoint_url" in result.error_message.lower()
    
    def test_create_database_error_result(
        self,
        connection_test_service
    ):
        """Test database error result creation."""
        result = connection_test_service._create_database_error_result(
            "test-id",
            "postgresql",
            "Connection timeout"
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert result.error_message == "Connection timeout"
        assert len(result.troubleshooting_suggestions) > 0
        
        # Should have timeout-specific suggestions
        suggestions_text = " ".join(result.troubleshooting_suggestions).lower()
        assert "timeout" in suggestions_text
    
    def test_error_result_authentication_failure(
        self,
        connection_test_service
    ):
        """Test error result for authentication failures."""
        result = connection_test_service._create_database_error_result(
            "test-id",
            "postgresql",
            "Authentication failed for user"
        )
        
        assert result.status == ConnectionStatus.FAILED
        suggestions_text = " ".join(result.troubleshooting_suggestions).lower()
        assert "authentication" in suggestions_text or "credentials" in suggestions_text
    
    def test_error_result_connection_refused(
        self,
        connection_test_service
    ):
        """Test error result for connection refused."""
        result = connection_test_service._create_database_error_result(
            "test-id",
            "postgresql",
            "Connection refused"
        )
        
        assert result.status == ConnectionStatus.FAILED
        suggestions_text = " ".join(result.troubleshooting_suggestions).lower()
        assert "refused" in suggestions_text or "accepting" in suggestions_text


class TestConnectionTestResultModel:
    """Test ConnectionTestResult model."""
    
    def test_result_model_creation(self):
        """Test creating connection test result."""
        result = ConnectionTestResult(
            status=ConnectionStatus.SUCCESS,
            target_id="test-id",
            target_type="postgresql",
            response_time_ms=50.0
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_id == "test-id"
        assert result.target_type == "postgresql"
        assert result.response_time_ms == 50.0
        assert result.error_message is None
        assert result.troubleshooting_suggestions == []
        assert isinstance(result.timestamp, datetime)
    
    def test_result_model_with_error(self):
        """Test result model with error information."""
        suggestions = [
            "Check network connectivity",
            "Verify credentials"
        ]
        
        result = ConnectionTestResult(
            status=ConnectionStatus.FAILED,
            target_id="test-id",
            target_type="mysql",
            response_time_ms=100.0,
            error_message="Connection timeout",
            troubleshooting_suggestions=suggestions
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert result.error_message == "Connection timeout"
        assert result.troubleshooting_suggestions == suggestions
