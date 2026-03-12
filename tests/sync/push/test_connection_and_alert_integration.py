"""
Integration tests for connection testing and alert logic.

Tests the integration between OutputSyncService, ConnectionTestService,
and OutputSyncAlertService.
"""

import pytest
from uuid import uuid4

from src.sync.push.connection_test_service import (
    ConnectionTestService,
    ConnectionStatus
)
from src.sync.push.output_sync_alert_service import OutputSyncAlertService
from src.sync.monitoring.alert_rules import sync_alert_manager


class TestConnectionTestServiceUnit:
    """Unit tests for connection test service without database."""
    
    @pytest.mark.asyncio
    async def test_postgresql_validation_success(self):
        """Test PostgreSQL connection validation with valid config."""
        service = ConnectionTestService()
        
        result = await service._test_postgresql_connection(
            {
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
                "username": "testuser"
            },
            "test-id"
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_type == "postgresql"
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_postgresql_validation_missing_fields(self):
        """Test PostgreSQL validation with missing fields."""
        service = ConnectionTestService()
        
        result = await service._test_postgresql_connection(
            {"host": "localhost"},  # Missing required fields
            "test-id"
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert "missing required fields" in result.error_message.lower()
        assert len(result.troubleshooting_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_mysql_validation_success(self):
        """Test MySQL connection validation."""
        service = ConnectionTestService()
        
        result = await service._test_mysql_connection(
            {
                "host": "localhost",
                "port": 3306,
                "database": "testdb",
                "username": "testuser"
            },
            "test-id"
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_type == "mysql"
    
    @pytest.mark.asyncio
    async def test_mongodb_validation_with_connection_string(self):
        """Test MongoDB validation with connection string."""
        service = ConnectionTestService()
        
        result = await service._test_mongodb_connection(
            {"connection_string": "mongodb://localhost:27017/testdb"},
            "test-id"
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_type == "mongodb"
    
    @pytest.mark.asyncio
    async def test_mongodb_validation_missing_connection_info(self):
        """Test MongoDB validation without connection info."""
        service = ConnectionTestService()
        
        result = await service._test_mongodb_connection(
            {},  # No connection_string or host
            "test-id"
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert "connection_string" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_api_validation_success(self):
        """Test API endpoint validation."""
        service = ConnectionTestService()
        
        result = await service._test_api_connection(
            {"endpoint_url": "https://api.example.com/data"},
            "test-id"
        )
        
        assert result.status == ConnectionStatus.SUCCESS
        assert result.target_type == "api"
    
    @pytest.mark.asyncio
    async def test_api_validation_missing_endpoint(self):
        """Test API validation without endpoint."""
        service = ConnectionTestService()
        
        result = await service._test_api_connection(
            {},  # No endpoint_url
            "test-id"
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert "endpoint_url" in result.error_message.lower()
    
    def test_error_result_timeout(self):
        """Test error result for timeout errors."""
        service = ConnectionTestService()
        
        result = service._create_database_error_result(
            "test-id",
            "postgresql",
            "Connection timeout after 30 seconds"
        )
        
        assert result.status == ConnectionStatus.FAILED
        assert result.error_message == "Connection timeout after 30 seconds"
        assert len(result.troubleshooting_suggestions) > 0
        
        # Should have timeout-specific suggestions at the top
        suggestions_text = result.troubleshooting_suggestions[0].lower()
        assert "timeout" in suggestions_text
    
    def test_error_result_authentication(self):
        """Test error result for authentication errors."""
        service = ConnectionTestService()
        
        result = service._create_database_error_result(
            "test-id",
            "mysql",
            "Authentication failed for user 'testuser'"
        )
        
        assert result.status == ConnectionStatus.FAILED
        # Should have auth-specific suggestions at the top
        suggestions_text = result.troubleshooting_suggestions[0].lower()
        assert "authentication" in suggestions_text or "credentials" in suggestions_text
    
    def test_error_result_connection_refused(self):
        """Test error result for connection refused."""
        service = ConnectionTestService()
        
        result = service._create_database_error_result(
            "test-id",
            "postgresql",
            "Connection refused by server"
        )
        
        assert result.status == ConnectionStatus.FAILED
        # Should have connection-refused suggestions at the top
        suggestions_text = result.troubleshooting_suggestions[0].lower()
        assert "refused" in suggestions_text or "accepting" in suggestions_text


class TestOutputSyncAlertServiceUnit:
    """Unit tests for alert service without database."""
    
    def test_alert_rules_registered(self):
        """Test that alert rules are properly registered."""
        service = OutputSyncAlertService()
        
        # Check that output sync alert rules exist
        assert "output_sync_high_failure_rate" in sync_alert_manager.rules
        assert "output_sync_critical_failure_rate" in sync_alert_manager.rules
        assert "target_database_unreachable" in sync_alert_manager.rules
    
    def test_warning_threshold_configuration(self):
        """Test warning threshold configuration."""
        service = OutputSyncAlertService()
        
        rule = sync_alert_manager.rules["output_sync_high_failure_rate"]
        assert rule.threshold == 0.20  # 20%
        assert rule.metric == "output_sync_failure_rate"
        assert rule.severity.value == "warning"
    
    def test_critical_threshold_configuration(self):
        """Test critical threshold configuration."""
        service = OutputSyncAlertService()
        
        rule = sync_alert_manager.rules["output_sync_critical_failure_rate"]
        assert rule.threshold == 0.50  # 50%
        assert rule.metric == "output_sync_failure_rate"
        assert rule.severity.value == "critical"
    
    def test_target_unreachable_configuration(self):
        """Test target unreachable alert configuration."""
        service = OutputSyncAlertService()
        
        rule = sync_alert_manager.rules["target_database_unreachable"]
        assert rule.threshold == 3  # 3 consecutive failures
        assert rule.metric == "target_connection_failures"
        assert rule.severity.value == "critical"
    
    def test_default_thresholds(self):
        """Test default threshold values."""
        service = OutputSyncAlertService()
        
        assert service.DEFAULT_FAILURE_RATE_WARNING == 0.20
        assert service.DEFAULT_FAILURE_RATE_CRITICAL == 0.50
        assert service.DEFAULT_EVALUATION_WINDOW_HOURS == 24
        assert service.DEFAULT_MIN_EXECUTIONS == 5


class TestConnectionTestResultModel:
    """Test ConnectionTestResult model."""
    
    def test_result_creation_success(self):
        """Test creating successful result."""
        from src.sync.push.connection_test_service import ConnectionTestResult
        
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
    
    def test_result_creation_with_error(self):
        """Test creating result with error."""
        from src.sync.push.connection_test_service import ConnectionTestResult
        
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
        assert len(result.troubleshooting_suggestions) == 2
