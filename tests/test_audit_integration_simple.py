"""
Simple integration test for comprehensive audit system.

Tests the basic functionality of the audit system without complex mocking.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

from src.security.audit_service import EnhancedAuditService
from src.security.audit_middleware import ComprehensiveAuditMiddleware
from src.security.audit_decorators import audit_decorators
from src.security.models import AuditAction, UserRole
from src.security.comprehensive_audit_integration import ComprehensiveAuditIntegration


class TestAuditSystemBasics:
    """Test basic audit system functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.audit_service = EnhancedAuditService()
        self.audit_integration = ComprehensiveAuditIntegration()
    
    def test_audit_service_initialization(self):
        """Test that audit service initializes correctly."""
        
        # Verify audit service has required components
        assert hasattr(self.audit_service, 'risk_rules')
        assert hasattr(self.audit_service, 'threat_patterns')
        assert hasattr(self.audit_service, 'monitoring_enabled')
        
        # Verify risk rules are initialized
        assert 'failed_login_burst' in self.audit_service.risk_rules
        assert 'sensitive_data_access' in self.audit_service.risk_rules
        assert 'privilege_escalation' in self.audit_service.risk_rules
        
        # Verify threat patterns are initialized
        assert 'sql_injection_attempt' in self.audit_service.threat_patterns
        assert 'unusual_ip_pattern' in self.audit_service.threat_patterns
        assert 'data_exfiltration' in self.audit_service.threat_patterns
    
    def test_audit_middleware_initialization(self):
        """Test that audit middleware initializes correctly."""
        
        # Create mock app
        mock_app = Mock()
        middleware = ComprehensiveAuditMiddleware(mock_app)
        
        # Verify middleware has required components
        assert hasattr(middleware, 'audit_service')
        assert hasattr(middleware, 'security_controller')
        assert hasattr(middleware, 'excluded_paths')
        assert hasattr(middleware, 'sensitive_endpoints')
        assert hasattr(middleware, 'method_to_action')
        
        # Verify excluded paths
        assert '/health' in middleware.excluded_paths
        assert '/metrics' in middleware.excluded_paths
        
        # Verify sensitive endpoints
        assert '/api/security/' in middleware.sensitive_endpoints
        assert '/api/audit/' in middleware.sensitive_endpoints
    
    def test_audit_decorators_initialization(self):
        """Test that audit decorators initialize correctly."""
        
        # Verify decorators have required components
        assert hasattr(audit_decorators, 'audit_service')
        assert hasattr(audit_decorators, 'security_controller')
        
        # Test decorator functions exist
        assert callable(audit_decorators.audit_all_operations)
        assert callable(audit_decorators.audit_sensitive_operation)
        assert callable(audit_decorators.audit_data_access)
    
    def test_comprehensive_audit_integration_initialization(self):
        """Test that comprehensive audit integration initializes correctly."""
        
        # Verify integration has required components
        assert hasattr(self.audit_integration, 'audit_service')
        assert hasattr(self.audit_integration, 'coverage_tracker')
        assert hasattr(self.audit_integration, 'real_time_monitor')
        assert hasattr(self.audit_integration, 'registered_endpoints')
        assert hasattr(self.audit_integration, 'audited_endpoints')
        
        # Verify initial state
        assert self.audit_integration.middleware_enabled is False
        assert isinstance(self.audit_integration.registered_endpoints, set)
        assert isinstance(self.audit_integration.audited_endpoints, set)
    
    def test_action_mapping(self):
        """Test HTTP method to audit action mapping."""
        
        middleware = ComprehensiveAuditMiddleware(Mock())
        
        # Test method mappings
        assert middleware.method_to_action["GET"] == AuditAction.READ
        assert middleware.method_to_action["POST"] == AuditAction.CREATE
        assert middleware.method_to_action["PUT"] == AuditAction.UPDATE
        assert middleware.method_to_action["PATCH"] == AuditAction.UPDATE
        assert middleware.method_to_action["DELETE"] == AuditAction.DELETE
    
    def test_resource_type_detection(self):
        """Test resource type detection from URL paths."""
        
        middleware = ComprehensiveAuditMiddleware(Mock())
        
        # Test various URL patterns
        test_cases = [
            ("/api/users/123", "user"),
            ("/api/security/settings", "security"),
            ("/api/audit/logs", "audit_log"),
            ("/api/billing/invoices", "billing"),
            ("/api/quality/reports", "quality"),
            ("/api/unknown/resource", "unknown"),
            ("/health", "system")
        ]
        
        for url, expected_resource in test_cases:
            result = middleware._extract_resource_type(url)
            assert result == expected_resource, f"URL {url} should map to {expected_resource}, got {result}"
    
    def test_sensitive_data_detection(self):
        """Test sensitive data detection patterns."""
        
        middleware = ComprehensiveAuditMiddleware(Mock())
        
        # Test sensitive content detection
        sensitive_cases = [
            b'{"password": "secret123"}',
            b'{"email": "user@example.com"}',
            b'{"credit_card": "4111-1111-1111-1111"}',
            b'{"phone": "555-123-4567"}',
            b'{"ssn": "123-45-6789"}'
        ]
        
        for content in sensitive_cases:
            assert middleware._detect_sensitive_data(content) is True, f"Should detect sensitive data in {content}"
        
        # Test non-sensitive content
        non_sensitive_cases = [
            b'{"name": "John Doe"}',
            b'{"age": 30}',
            b'{"status": "active"}',
            b'{"count": 100}'
        ]
        
        for content in non_sensitive_cases:
            assert middleware._detect_sensitive_data(content) is False, f"Should not detect sensitive data in {content}"
    
    def test_audit_decorator_resource_detection(self):
        """Test audit decorator resource type detection."""
        
        # Test function name patterns
        test_cases = [
            ("create_user_account", "user"),
            ("get_audit_report", "audit_log"),
            ("update_security_policy", "security"),
            ("process_billing_invoice", "billing"),
            ("analyze_quality_metrics", "quality"),
            ("export_data_file", "export"),
            ("manage_admin_settings", "admin"),
            ("unknown_function_name", "system")
        ]
        
        for function_name, expected_resource in test_cases:
            result = audit_decorators._detect_resource_type(function_name)
            assert result == expected_resource, f"Function {function_name} should map to {expected_resource}, got {result}"
    
    def test_audit_decorator_action_detection(self):
        """Test audit decorator action detection."""
        
        # Mock request
        mock_request = Mock()
        mock_request.method = "POST"
        
        # Test function name patterns
        test_cases = [
            ("create_new_record", AuditAction.CREATE),
            ("update_existing_data", AuditAction.UPDATE),
            ("delete_old_files", AuditAction.DELETE),
            ("export_user_data", AuditAction.EXPORT),
            ("import_csv_file", AuditAction.IMPORT),
            ("login_user_session", AuditAction.LOGIN),
            ("logout_current_user", AuditAction.LOGOUT)
        ]
        
        for function_name, expected_action in test_cases:
            result = audit_decorators._detect_action(function_name, mock_request)
            assert result == expected_action, f"Function {function_name} should map to {expected_action}, got {result}"
    
    def test_parameter_sanitization(self):
        """Test parameter sanitization for security."""
        
        # Test parameters with sensitive and non-sensitive data
        test_params = {
            "username": "testuser",
            "password": "secret123",
            "email": "user@example.com",
            "api_key": "abc123def456",
            "secret_token": "xyz789",
            "normal_field": "normal_value",
            "count": 42,
            "is_active": True,
            "user_object": Mock()
        }
        
        sanitized = audit_decorators._sanitize_parameters(test_params)
        
        # Verify sensitive fields are redacted
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["secret_token"] == "[REDACTED]"
        
        # Verify non-sensitive fields are preserved
        assert sanitized["username"] == "testuser"
        assert sanitized["email"] == "user@example.com"
        assert sanitized["normal_field"] == "normal_value"
        assert sanitized["count"] == 42
        assert sanitized["is_active"] is True
        
        # Verify objects are represented as type names
        assert sanitized["user_object"] == "<Mock>"
    
    def test_client_ip_extraction(self):
        """Test client IP extraction from request headers."""
        
        middleware = ComprehensiveAuditMiddleware(Mock())
        
        # Test with X-Forwarded-For header
        mock_request = Mock()
        mock_request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        mock_request.client.host = "127.0.0.1"
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.100"
        
        # Test with X-Real-IP header
        mock_request.headers = {"x-real-ip": "203.0.113.1"}
        ip = middleware._get_client_ip(mock_request)
        assert ip == "203.0.113.1"
        
        # Test fallback to client.host
        mock_request.headers = {}
        ip = middleware._get_client_ip(mock_request)
        assert ip == "127.0.0.1"
    
    def test_audit_system_components_integration(self):
        """Test that all audit system components work together."""
        
        # Verify all components can be instantiated together
        audit_service = EnhancedAuditService()
        middleware = ComprehensiveAuditMiddleware(Mock())
        integration = ComprehensiveAuditIntegration()
        
        # Verify they all have compatible interfaces
        assert hasattr(audit_service, 'log_enhanced_audit_event')
        assert hasattr(middleware, 'dispatch')
        assert hasattr(integration, 'integrate_with_fastapi')
        
        # Verify audit service is used by other components
        assert isinstance(middleware.audit_service, EnhancedAuditService)
        assert isinstance(integration.audit_service, EnhancedAuditService)
    
    def test_audit_coverage_tracking(self):
        """Test audit coverage tracking functionality."""
        
        coverage_tracker = self.audit_integration.coverage_tracker
        
        # Test initial state
        assert len(coverage_tracker.tracked_endpoints) == 0
        assert len(coverage_tracker.audited_endpoints) == 0
        
        # Test endpoint registration (synchronous version for testing)
        coverage_tracker.tracked_endpoints.add("/api/users")
        coverage_tracker.tracked_endpoints.add("/api/documents")
        coverage_tracker.audited_endpoints.add("/api/users")
        
        # Verify registration
        assert "/api/users" in coverage_tracker.tracked_endpoints
        assert "/api/documents" in coverage_tracker.tracked_endpoints
        assert "/api/users" in coverage_tracker.audited_endpoints
        assert "/api/documents" not in coverage_tracker.audited_endpoints
    
    def test_real_time_monitor_basic_functionality(self):
        """Test real-time monitor basic functionality."""
        
        monitor = self.audit_integration.real_time_monitor
        
        # Test initial state
        assert monitor.running is False
        assert monitor.stats["total_events"] == 0
        assert len(monitor.stats["unique_users"]) == 0
        assert len(monitor.stats["unique_resources"]) == 0
        
        # Test stats structure
        assert "events_per_minute" in monitor.stats
        assert "total_events" in monitor.stats
        assert "unique_users" in monitor.stats
        assert "unique_resources" in monitor.stats
        assert "start_time" in monitor.stats


class TestAuditSystemValidation:
    """Test audit system validation and completeness."""
    
    def test_all_audit_actions_covered(self):
        """Test that all audit actions are properly defined."""
        
        # Verify all expected audit actions exist
        expected_actions = [
            AuditAction.LOGIN,
            AuditAction.LOGOUT,
            AuditAction.CREATE,
            AuditAction.READ,
            AuditAction.UPDATE,
            AuditAction.DELETE,
            AuditAction.EXPORT,
            AuditAction.IMPORT,
            AuditAction.ANNOTATE,
            AuditAction.REVIEW
        ]
        
        for action in expected_actions:
            assert isinstance(action, AuditAction)
            assert isinstance(action.value, str)
    
    def test_user_roles_covered(self):
        """Test that all user roles are properly defined."""
        
        # Verify all expected user roles exist
        expected_roles = [
            UserRole.ADMIN,
            UserRole.BUSINESS_EXPERT,
            UserRole.TECHNICAL_EXPERT,
            UserRole.CONTRACTOR,
            UserRole.VIEWER
        ]
        
        for role in expected_roles:
            assert isinstance(role, UserRole)
            assert isinstance(role.value, str)
    
    def test_audit_system_completeness(self):
        """Test that audit system covers all required functionality."""
        
        # Test that all required components exist
        required_components = [
            'EnhancedAuditService',
            'ComprehensiveAuditMiddleware', 
            'ComprehensiveAuditIntegration',
            'AuditCoverageTracker',
            'RealTimeAuditMonitor'
        ]
        
        # Import and verify each component exists
        from src.security.audit_service import EnhancedAuditService
        from src.security.audit_middleware import ComprehensiveAuditMiddleware
        from src.security.comprehensive_audit_integration import (
            ComprehensiveAuditIntegration,
            AuditCoverageTracker,
            RealTimeAuditMonitor
        )
        
        # Verify components can be instantiated
        audit_service = EnhancedAuditService()
        middleware = ComprehensiveAuditMiddleware(Mock())
        integration = ComprehensiveAuditIntegration()
        coverage_tracker = AuditCoverageTracker()
        monitor = RealTimeAuditMonitor()
        
        # Verify all components have required methods
        assert callable(getattr(audit_service, 'log_enhanced_audit_event'))
        assert callable(getattr(middleware, 'dispatch'))
        assert callable(getattr(integration, 'integrate_with_fastapi'))
        assert callable(getattr(coverage_tracker, 'generate_coverage_report'))
        assert callable(getattr(monitor, 'get_current_stats'))


if __name__ == "__main__":
    pytest.main([__file__])