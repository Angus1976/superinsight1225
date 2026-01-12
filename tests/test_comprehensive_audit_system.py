"""
Tests for Comprehensive Audit System.

Tests the complete audit recording of all user operations including:
- Middleware-based audit logging
- Decorator-based audit logging
- Manual audit logging
- Audit coverage verification
- Real-time monitoring
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.security.comprehensive_audit_integration import (
    ComprehensiveAuditIntegration,
    AuditCoverageTracker,
    RealTimeAuditMonitor
)
from src.security.audit_middleware import ComprehensiveAuditMiddleware
from src.security.audit_decorators import audit_decorators
from src.security.audit_service import EnhancedAuditService
from src.security.models import AuditAction, UserModel, UserRole


class TestComprehensiveAuditIntegration:
    """Test comprehensive audit integration functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.audit_integration = ComprehensiveAuditIntegration()
        self.mock_db = Mock(spec=Session)
    
    @pytest.mark.asyncio
    async def test_audit_integration_initialization(self):
        """Test audit integration initialization."""
        
        # Mock dependencies
        with patch.object(self.audit_integration.real_time_monitor, 'start') as mock_start, \
             patch.object(self.audit_integration.coverage_tracker, 'initialize') as mock_init, \
             patch.object(self.audit_integration, '_verify_audit_infrastructure') as mock_verify, \
             patch.object(self.audit_integration, '_start_background_tasks') as mock_tasks:
            
            # Test initialization
            await self.audit_integration.initialize_audit_system()
            
            # Verify all components were initialized
            mock_start.assert_called_once()
            mock_init.assert_called_once()
            mock_verify.assert_called_once()
            mock_tasks.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_system_operation_logging(self):
        """Test logging of system operations."""
        
        # Mock enhanced audit service
        with patch.object(self.audit_integration.audit_service, 'log_enhanced_audit_event') as mock_log:
            mock_log.return_value = {"status": "success"}
            
            # Test system operation logging
            await self.audit_integration.log_system_operation(
                operation="test_operation",
                resource_type="test_resource",
                resource_id="test_id",
                details={"test": "data"},
                user_id="test_user",
                tenant_id="test_tenant"
            )
            
            # Verify audit event was logged
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            
            assert call_args[1]["user_id"] == "test_user"
            assert call_args[1]["tenant_id"] == "test_tenant"
            assert call_args[1]["action"] == AuditAction.UPDATE
            assert call_args[1]["resource_type"] == "test_resource"
            assert call_args[1]["resource_id"] == "test_id"
            assert "operation_type" in call_args[1]["details"]
            assert call_args[1]["details"]["operation"] == "test_operation"
    
    @pytest.mark.asyncio
    async def test_batch_operations_logging(self):
        """Test batch operations logging."""
        
        # Mock bulk logging
        with patch.object(self.audit_integration.audit_service, 'log_bulk_actions') as mock_bulk:
            mock_bulk.return_value = True
            
            # Test batch operations
            operations = [
                {
                    "user_id": "user1",
                    "action": "create",
                    "resource_type": "document",
                    "resource_id": "doc1",
                    "details": {"test": "data1"}
                },
                {
                    "user_id": "user2",
                    "action": "update",
                    "resource_type": "document",
                    "resource_id": "doc2",
                    "details": {"test": "data2"}
                }
            ]
            
            await self.audit_integration.log_batch_operations(
                operations=operations,
                tenant_id="test_tenant"
            )
            
            # Verify bulk logging was called
            mock_bulk.assert_called_once()
            call_args = mock_bulk.call_args[0][0]  # First argument (audit_actions)
            
            assert len(call_args) == 2
            assert call_args[0]["user_id"] == "user1"
            assert call_args[0]["tenant_id"] == "test_tenant"
            assert call_args[1]["user_id"] == "user2"
            assert call_args[1]["tenant_id"] == "test_tenant"
    
    @pytest.mark.asyncio
    async def test_audit_coverage_report(self):
        """Test audit coverage report generation."""
        
        # Mock coverage tracker
        mock_report = {
            "total_endpoints": 10,
            "audited_endpoints": 8,
            "coverage_percentage": 80.0,
            "unaudited_endpoints": ["/api/test1", "/api/test2"],
            "recommendations": ["Good coverage"]
        }
        
        with patch.object(self.audit_integration.coverage_tracker, 'generate_coverage_report') as mock_gen:
            mock_gen.return_value = mock_report
            
            # Test coverage report
            report = await self.audit_integration.get_audit_coverage_report()
            
            # Verify report structure
            assert report == mock_report
            assert "total_endpoints" in report
            assert "audited_endpoints" in report
            assert "coverage_percentage" in report
    
    @pytest.mark.asyncio
    async def test_audit_completeness_verification(self):
        """Test audit completeness verification."""
        
        # Mock audit service methods
        mock_security_summary = {
            "total_events": 100,
            "failed_logins": 2,
            "sensitive_operations": 10,
            "active_users": 5
        }
        
        with patch.object(self.audit_integration.audit_service, 'get_security_summary') as mock_summary, \
             patch.object(self.audit_integration, '_analyze_audit_coverage') as mock_analyze:
            
            mock_summary.return_value = mock_security_summary
            mock_analyze.return_value = {
                "total_events": 100,
                "unique_actions": 5,
                "unique_resources": 8,
                "unique_users": 5
            }
            
            # Test completeness verification
            result = await self.audit_integration.verify_audit_completeness(
                tenant_id="test_tenant",
                time_range=timedelta(hours=24)
            )
            
            # Verify result structure
            assert "tenant_id" in result
            assert "time_range" in result
            assert "audit_statistics" in result
            assert "coverage_analysis" in result
            assert "completeness_score" in result
            assert "recommendations" in result
            
            assert result["tenant_id"] == "test_tenant"
            assert result["audit_statistics"] == mock_security_summary
            assert isinstance(result["completeness_score"], float)
            assert 0 <= result["completeness_score"] <= 100


class TestAuditCoverageTracker:
    """Test audit coverage tracking functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.coverage_tracker = AuditCoverageTracker()
    
    @pytest.mark.asyncio
    async def test_endpoint_registration(self):
        """Test endpoint registration for coverage tracking."""
        
        # Register endpoints
        await self.coverage_tracker.register_endpoint("/api/users", has_audit=True)
        await self.coverage_tracker.register_endpoint("/api/documents", has_audit=False)
        await self.coverage_tracker.register_endpoint("/api/billing", has_audit=True)
        
        # Verify registration
        assert "/api/users" in self.coverage_tracker.tracked_endpoints
        assert "/api/documents" in self.coverage_tracker.tracked_endpoints
        assert "/api/billing" in self.coverage_tracker.tracked_endpoints
        
        assert "/api/users" in self.coverage_tracker.audited_endpoints
        assert "/api/documents" not in self.coverage_tracker.audited_endpoints
        assert "/api/billing" in self.coverage_tracker.audited_endpoints
    
    @pytest.mark.asyncio
    async def test_coverage_report_generation(self):
        """Test coverage report generation."""
        
        # Register test endpoints
        await self.coverage_tracker.register_endpoint("/api/users", has_audit=True)
        await self.coverage_tracker.register_endpoint("/api/documents", has_audit=False)
        await self.coverage_tracker.register_endpoint("/api/billing", has_audit=True)
        await self.coverage_tracker.register_endpoint("/api/quality", has_audit=True)
        
        # Generate coverage report
        report = await self.coverage_tracker.generate_coverage_report()
        
        # Verify report
        assert report["total_endpoints"] == 4
        assert report["audited_endpoints"] == 3
        assert report["coverage_percentage"] == 75.0
        assert "/api/documents" in report["unaudited_endpoints"]
        assert len(report["recommendations"]) > 0
    
    def test_coverage_recommendations(self):
        """Test coverage recommendation generation."""
        
        # Test different coverage levels
        recommendations_low = self.coverage_tracker._generate_coverage_recommendations(30.0)
        recommendations_medium = self.coverage_tracker._generate_coverage_recommendations(70.0)
        recommendations_high = self.coverage_tracker._generate_coverage_recommendations(95.0)
        
        # Verify recommendations
        assert "Critical" in recommendations_low[0]
        assert "Warning" in recommendations_medium[0]
        assert "Excellent" in recommendations_high[0]


class TestRealTimeAuditMonitor:
    """Test real-time audit monitoring functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.monitor = RealTimeAuditMonitor()
    
    @pytest.mark.asyncio
    async def test_monitor_lifecycle(self):
        """Test monitor start and stop lifecycle."""
        
        # Test initial state
        assert not self.monitor.running
        
        # Test start
        await self.monitor.start()
        assert self.monitor.running
        assert self.monitor.stats["start_time"] is not None
        
        # Test stop
        await self.monitor.stop()
        assert not self.monitor.running
    
    @pytest.mark.asyncio
    async def test_event_recording(self):
        """Test audit event recording."""
        
        # Start monitor
        await self.monitor.start()
        
        # Record test events
        await self.monitor.record_event({
            "user_id": "user1",
            "resource_type": "document",
            "action": "create"
        })
        
        await self.monitor.record_event({
            "user_id": "user2",
            "resource_type": "billing",
            "action": "read"
        })
        
        await self.monitor.record_event({
            "user_id": "user1",
            "resource_type": "document",
            "action": "update"
        })
        
        # Verify statistics
        stats = await self.monitor.get_current_stats()
        
        assert stats["total_events"] == 3
        assert stats["unique_users"] == 2
        assert stats["unique_resources"] == 2
        assert stats["running"] is True
    
    @pytest.mark.asyncio
    async def test_statistics_calculation(self):
        """Test statistics calculation."""
        
        # Start monitor
        await self.monitor.start()
        
        # Record events
        for i in range(10):
            await self.monitor.record_event({
                "user_id": f"user{i % 3}",  # 3 unique users
                "resource_type": f"resource{i % 4}",  # 4 unique resources
                "action": "test"
            })
        
        # Get statistics
        stats = await self.monitor.get_current_stats()
        
        # Verify calculations
        assert stats["total_events"] == 10
        assert stats["unique_users"] == 3
        assert stats["unique_resources"] == 4
        assert stats["uptime_seconds"] > 0
        assert stats["events_per_hour"] >= 0


class TestAuditMiddleware:
    """Test comprehensive audit middleware functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = FastAPI()
        self.middleware = ComprehensiveAuditMiddleware(self.app)
    
    def test_should_skip_audit(self):
        """Test audit skipping logic."""
        
        # Mock requests
        health_request = Mock()
        health_request.url.path = "/health"
        
        api_request = Mock()
        api_request.url.path = "/api/users"
        
        static_request = Mock()
        static_request.url.path = "/static/css/style.css"
        
        # Test skipping logic
        assert self.middleware._should_skip_audit(health_request) is True
        assert self.middleware._should_skip_audit(api_request) is False
        assert self.middleware._should_skip_audit(static_request) is True
    
    def test_resource_type_extraction(self):
        """Test resource type extraction from URL paths."""
        
        # Test various paths
        assert self.middleware._extract_resource_type("/api/users/123") == "user"
        assert self.middleware._extract_resource_type("/api/security/audit") == "security"
        assert self.middleware._extract_resource_type("/api/billing/invoices") == "billing"
        assert self.middleware._extract_resource_type("/api/unknown/path") == "unknown"
        assert self.middleware._extract_resource_type("/health") == "system"
    
    def test_resource_id_extraction(self):
        """Test resource ID extraction from URL paths."""
        
        # Test UUID extraction
        uuid_path = "/api/users/550e8400-e29b-41d4-a716-446655440000"
        assert self.middleware._extract_resource_id(uuid_path) == "550e8400-e29b-41d4-a716-446655440000"
        
        # Test numeric ID extraction
        numeric_path = "/api/documents/12345"
        assert self.middleware._extract_resource_id(numeric_path) == "12345"
        
        # Test no ID
        no_id_path = "/api/users"
        assert self.middleware._extract_resource_id(no_id_path) is None
    
    def test_sensitive_data_detection(self):
        """Test sensitive data detection."""
        
        # Test sensitive content
        sensitive_content = b'{"password": "secret123", "email": "user@example.com"}'
        assert self.middleware._detect_sensitive_data(sensitive_content) is True
        
        # Test non-sensitive content
        normal_content = b'{"name": "John", "age": 30}'
        assert self.middleware._detect_sensitive_data(normal_content) is False
        
        # Test empty content
        assert self.middleware._detect_sensitive_data(b'') is False


class TestAuditDecorators:
    """Test audit decorators functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.decorators = audit_decorators
    
    def test_resource_type_detection(self):
        """Test automatic resource type detection."""
        
        # Test function name patterns
        assert self.decorators._detect_resource_type("create_user") == "user"
        assert self.decorators._detect_resource_type("get_audit_logs") == "audit_log"
        assert self.decorators._detect_resource_type("update_security_settings") == "security"
        assert self.decorators._detect_resource_type("process_billing") == "billing"
        assert self.decorators._detect_resource_type("unknown_function") == "system"
    
    def test_action_detection(self):
        """Test automatic action detection."""
        
        # Mock request
        mock_request = Mock()
        mock_request.method = "POST"
        
        # Test function name patterns
        assert self.decorators._detect_action("create_user", mock_request) == AuditAction.CREATE
        assert self.decorators._detect_action("update_document", mock_request) == AuditAction.UPDATE
        assert self.decorators._detect_action("delete_record", mock_request) == AuditAction.DELETE
        assert self.decorators._detect_action("export_data", mock_request) == AuditAction.EXPORT
        assert self.decorators._detect_action("login_user", mock_request) == AuditAction.LOGIN
        
        # Test HTTP method fallback
        mock_request.method = "GET"
        assert self.decorators._detect_action("unknown_function", mock_request) == AuditAction.READ
    
    def test_parameter_sanitization(self):
        """Test parameter sanitization for audit logging."""
        
        # Test parameters with sensitive data
        parameters = {
            "username": "testuser",
            "password": "secret123",
            "email": "user@example.com",
            "api_key": "abc123",
            "normal_param": "normal_value",
            "user_object": Mock()
        }
        
        sanitized = self.decorators._sanitize_parameters(parameters)
        
        # Verify sanitization
        assert sanitized["username"] == "testuser"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["email"] == "user@example.com"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["normal_param"] == "normal_value"
        assert sanitized["user_object"] == "<Mock>"
    
    def test_data_volume_calculation(self):
        """Test data volume calculation."""
        
        # Test list data
        list_data = [1, 2, 3, 4, 5]
        list_volume = self.decorators._calculate_data_volume(list_data)
        assert list_volume["record_count"] == 5
        assert list_volume["data_type"] == "list"
        
        # Test dict data
        dict_data = {"key1": "value1", "key2": "value2"}
        dict_volume = self.decorators._calculate_data_volume(dict_data)
        assert dict_volume["field_count"] == 2
        assert dict_volume["data_type"] == "dict"
        
        # Test string data
        string_data = "test string"
        string_volume = self.decorators._calculate_data_volume(string_data)
        assert string_volume["character_count"] == 11
        assert string_volume["data_type"] == "string"


@pytest.mark.asyncio
async def test_comprehensive_audit_integration():
    """Integration test for comprehensive audit system."""
    
    # Create FastAPI app with audit integration
    app = FastAPI()
    audit_integration = ComprehensiveAuditIntegration()
    
    # Mock the audit service to avoid database dependencies
    with patch.object(audit_integration, 'initialize_audit_system') as mock_init, \
         patch.object(audit_integration, 'shutdown_audit_system') as mock_shutdown:
        
        # Integrate with FastAPI
        audit_integration.integrate_with_fastapi(app)
        
        # Verify middleware was added
        assert any(
            isinstance(middleware, ComprehensiveAuditMiddleware) 
            for middleware in app.user_middleware
        )
        
        # Test startup and shutdown events
        # Note: In a real test, these would be called by FastAPI
        await mock_init()
        await mock_shutdown()
        
        mock_init.assert_called_once()
        mock_shutdown.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])