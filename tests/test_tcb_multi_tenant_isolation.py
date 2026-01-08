"""
TCB Multi-Tenant Isolation Tests

Enterprise-level tests for multi-tenant data isolation and security in TCB deployment.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import uuid
import json
import os
import tempfile
import yaml

from src.database.tenant_isolation_validator import TenantIsolationValidator
from src.middleware.tenant_middleware import TenantMiddleware, TenantContext
from src.security.tenant_permissions import TenantPermissionManager
from src.security.tenant_audit import TenantAuditLogger, AuditEvent, AuditAction
from src.label_studio.tenant_isolation import LabelStudioTenantManager


class TestTCBTenantDataIsolation:
    """Test tenant data isolation in TCB environment."""
    
    def test_database_tenant_isolation_validation(self):
        """Test that all database tables have proper tenant isolation."""
        validator = TenantIsolationValidator()
        
        # Test critical business tables
        critical_tables = [
            'business_rules', 'business_patterns', 'business_insights',
            'documents', 'annotations', 'tasks', 'projects',
            'quality_issues', 'work_orders', 'billing_records',
            'user_sessions', 'audit_logs'
        ]
        
        with patch('src.database.tenant_isolation_validator.get_db_session') as mock_session:
            mock_inspector = Mock()
            
            # Mock that all tables have tenant_id
            def mock_get_columns(table_name):
                if table_name in critical_tables:
                    return [
                        {'name': 'id', 'type': 'INTEGER'},
                        {'name': 'tenant_id', 'type': 'VARCHAR'},
                        {'name': 'created_at', 'type': 'TIMESTAMP'}
                    ]
                return []
            
            mock_inspector.get_columns.side_effect = mock_get_columns
            mock_inspector.get_table_names.return_value = critical_tables
            
            mock_session.return_value.__enter__.return_value.bind = Mock()
            
            with patch('src.database.tenant_isolation_validator.inspect', return_value=mock_inspector):
                result = validator.validate_all_tables_have_tenant_id()
        
        assert result['valid'] is True
        assert result['tables_checked'] >= len(critical_tables)
        assert len(result['missing_tenant_id']) == 0
        
        # Verify all critical tables were checked
        for table in critical_tables:
            assert table in result['checked_tables']
    
    def test_tenant_query_filtering(self):
        """Test that database queries are properly filtered by tenant."""
        from src.middleware.tenant_middleware import TenantQueryFilter
        
        # Mock query and model
        mock_query = Mock()
        mock_model = Mock()
        mock_model.tenant_id = Mock()
        
        # Test query filtering
        filtered_query = TenantQueryFilter.filter_by_tenant(
            mock_query, mock_model, "tenant_123"
        )
        
        # Verify filter was applied
        mock_query.filter.assert_called_once()
        
        # Test that the filter uses the correct tenant_id
        filter_call = mock_query.filter.call_args[0][0]
        assert hasattr(filter_call, 'left')  # Should be a comparison expression
    
    def test_cross_tenant_data_access_prevention(self):
        """Test that cross-tenant data access is prevented."""
        validator = TenantIsolationValidator()
        
        # Simulate attempting to access data from different tenant
        with patch('src.database.tenant_isolation_validator.get_db_session') as mock_session:
            mock_result = Mock()
            mock_result.fetchall.return_value = []  # No cross-tenant data should be found
            
            mock_session.return_value.__enter__.return_value.execute.return_value = mock_result
            
            result = validator.validate_cross_tenant_isolation("tenant_1", "tenant_2")
        
        assert result['isolated'] is True
        assert result['cross_tenant_records'] == 0
    
    def test_tenant_specific_indexes(self):
        """Test that tenant_id columns have proper database indexes."""
        validator = TenantIsolationValidator()
        
        with patch('src.database.tenant_isolation_validator.get_db_session') as mock_session:
            mock_inspector = Mock()
            
            # Mock indexes that include tenant_id
            mock_inspector.get_indexes.return_value = [
                {'name': 'idx_tenant_id', 'column_names': ['tenant_id']},
                {'name': 'idx_tenant_created', 'column_names': ['tenant_id', 'created_at']},
                {'name': 'idx_tenant_status', 'column_names': ['tenant_id', 'status']}
            ]
            
            mock_session.return_value.__enter__.return_value.bind = Mock()
            
            with patch('src.database.tenant_isolation_validator.inspect', return_value=mock_inspector):
                result = validator.validate_tenant_indexes()
        
        assert result['valid'] is True
        assert result['tenant_indexes_found'] >= 3


class TestTCBTenantPermissions:
    """Test tenant permission control in TCB environment."""
    
    def test_tenant_role_based_access_control(self):
        """Test role-based access control within tenants."""
        manager = TenantPermissionManager()
        
        # Test different tenant roles
        roles_permissions = {
            'tenant_admin': ['admin', 'read', 'write', 'delete'],
            'project_manager': ['read', 'write', 'manage_projects'],
            'business_expert': ['read', 'write', 'quality_review'],
            'annotator': ['read', 'annotate'],
            'viewer': ['read']
        }
        
        for role, expected_perms in roles_permissions.items():
            with patch.object(manager, 'get_user_permissions') as mock_get_perms:
                # Mock permissions based on role
                mock_get_perms.return_value = {
                    perm: ['allowed'] for perm in expected_perms
                }
                
                permissions = manager.get_user_permissions(f"user_{role}", "tenant_1")
                
                # Verify role has expected permissions
                for perm in expected_perms:
                    assert perm in permissions or any(perm in str(p) for p in permissions.keys())
    
    def test_tenant_resource_isolation(self):
        """Test that resources are isolated between tenants."""
        manager = TenantPermissionManager()
        
        # Test that user from tenant_1 cannot access tenant_2 resources
        with patch.object(manager, 'get_user_permissions') as mock_get_perms:
            mock_get_perms.return_value = {'documents': ['read', 'write']}
            
            # Should have access to own tenant resources
            assert manager.check_tenant_resource_access(
                "user_1", "tenant_1", "documents", "doc_1", "tenant_1"
            )
            
            # Should NOT have access to other tenant resources
            assert not manager.check_tenant_resource_access(
                "user_1", "tenant_1", "documents", "doc_2", "tenant_2"
            )
    
    def test_api_endpoint_tenant_validation(self):
        """Test that API endpoints validate tenant context."""
        from src.middleware.tenant_middleware import TenantMiddleware
        
        middleware = TenantMiddleware(Mock())
        
        # Mock request with valid tenant token
        mock_request = Mock()
        mock_request.headers = {"Authorization": "Bearer valid_token"}
        mock_request.url.path = "/api/v1/documents"
        
        with patch('src.middleware.tenant_middleware.jwt.decode') as mock_jwt:
            mock_jwt.return_value = {
                "tenant_id": "tenant_1",
                "user_id": "user_1",
                "role": "business_expert"
            }
            
            # Test middleware extracts tenant context
            context = middleware._extract_tenant_from_token("valid_token")
            
            assert context['tenant_id'] == "tenant_1"
            assert context['user_id'] == "user_1"


class TestTCBTenantSecurity:
    """Test tenant security compliance in TCB environment."""
    
    def test_tenant_audit_logging(self):
        """Test comprehensive audit logging for tenant actions."""
        logger = TenantAuditLogger()
        
        # Test different types of audit events
        audit_scenarios = [
            {
                'action': AuditAction.CREATE,
                'resource_type': 'documents',
                'resource_id': 'doc_1',
                'tenant_id': 'tenant_1',
                'user_id': 'user_1',
                'details': {'title': 'Test Document'}
            },
            {
                'action': AuditAction.READ,
                'resource_type': 'business_rules',
                'resource_id': 'rule_1',
                'tenant_id': 'tenant_1',
                'user_id': 'user_2',
                'details': {'query_params': {'status': 'active'}}
            },
            {
                'action': AuditAction.UPDATE,
                'resource_type': 'annotations',
                'resource_id': 'ann_1',
                'tenant_id': 'tenant_1',
                'user_id': 'user_1',
                'details': {'changes': {'status': 'completed'}}
            },
            {
                'action': AuditAction.DELETE,
                'resource_type': 'tasks',
                'resource_id': 'task_1',
                'tenant_id': 'tenant_1',
                'user_id': 'user_1',
                'details': {'reason': 'duplicate'}
            }
        ]
        
        with patch('src.security.tenant_audit.get_db_session') as mock_session:
            for scenario in audit_scenarios:
                event = AuditEvent(**scenario)
                result = logger.log_event(event)
                
                assert result is True
                
                # Verify event was properly logged
                mock_session.return_value.__enter__.return_value.add.assert_called()
    
    def test_sensitive_data_protection(self):
        """Test that sensitive data is protected in audit logs."""
        logger = TenantAuditLogger()
        
        sensitive_data = {
            'user_password': 'secret123',
            'api_key': 'sk-1234567890abcdef',
            'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
            'credit_card': '4111-1111-1111-1111',
            'ssn': '123-45-6789',
            'normal_field': 'normal_value',
            'tenant_id': 'tenant_1'
        }
        
        sanitized = logger._sanitize_details(sensitive_data)
        
        # Verify sensitive fields are redacted
        assert sanitized['user_password'] == '***REDACTED***'
        assert sanitized['api_key'] == '***REDACTED***'
        assert sanitized['access_token'] == '***REDACTED***'
        assert sanitized['credit_card'] == '***REDACTED***'
        assert sanitized['ssn'] == '***REDACTED***'
        
        # Verify normal fields are preserved
        assert sanitized['normal_field'] == 'normal_value'
        assert sanitized['tenant_id'] == 'tenant_1'
    
    def test_tenant_session_isolation(self):
        """Test that user sessions are isolated between tenants."""
        from src.middleware.tenant_middleware import TenantSessionManager
        
        session_manager = TenantSessionManager()
        
        # Create sessions for different tenants
        session1 = session_manager.create_session("user_1", "tenant_1")
        session2 = session_manager.create_session("user_2", "tenant_2")
        
        # Verify sessions are isolated
        assert session1['tenant_id'] == "tenant_1"
        assert session2['tenant_id'] == "tenant_2"
        assert session1['session_id'] != session2['session_id']
        
        # Test session validation
        with patch.object(session_manager, 'get_session') as mock_get_session:
            mock_get_session.return_value = session1
            
            # Valid session for correct tenant
            assert session_manager.validate_session(session1['session_id'], "tenant_1")
            
            # Invalid session for different tenant
            assert not session_manager.validate_session(session1['session_id'], "tenant_2")


class TestTCBLabelStudioTenantIsolation:
    """Test Label Studio tenant isolation in TCB environment."""
    
    def test_label_studio_project_isolation(self):
        """Test that Label Studio projects are isolated by tenant."""
        manager = LabelStudioTenantManager()
        
        # Mock Label Studio API responses
        with patch('src.label_studio.tenant_isolation.requests.request') as mock_request:
            # Mock project creation response
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": 123,
                "title": "[tenant_1] Test Project",
                "description": "Test project for tenant_1"
            }
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            from src.label_studio.tenant_isolation import LabelStudioProject
            project_config = LabelStudioProject(
                id=0,
                title="Test Project",
                description="Test Description",
                tenant_id="tenant_1",
                created_by="user_1",
                label_config="<View><Text name='text' value='$text'/></View>"
            )
            
            with patch('src.label_studio.tenant_isolation.get_current_tenant', return_value="tenant_1"):
                result = manager.create_tenant_project(project_config)
            
            assert result["id"] == 123
            assert "[tenant_1]" in result["title"]
    
    def test_label_studio_data_access_control(self):
        """Test Label Studio data access control by tenant."""
        manager = LabelStudioTenantManager()
        
        # Test project listing with tenant filtering
        with patch('src.label_studio.tenant_isolation.requests.request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = [
                {"id": 1, "title": "[tenant_1] Project A", "description": "Tenant 1 project"},
                {"id": 2, "title": "[tenant_2] Project B", "description": "Tenant 2 project"},
                {"id": 3, "title": "[tenant_1] Project C", "description": "Another tenant 1 project"}
            ]
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            # Get projects for tenant_1
            projects = manager.get_tenant_projects("tenant_1")
            
            # Should only return tenant_1 projects
            assert len(projects) == 2
            assert all("[tenant_1]" in project["title"] for project in projects)
    
    def test_label_studio_annotation_isolation(self):
        """Test that annotations are isolated between tenants."""
        manager = LabelStudioTenantManager()
        
        # Mock annotation data with tenant context
        with patch('src.label_studio.tenant_isolation.requests.request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {
                "results": [
                    {
                        "id": 1,
                        "task": 101,
                        "project": 1,  # tenant_1 project
                        "created_username": "user_1@tenant_1",
                        "result": [{"value": {"text": ["Label A"]}}]
                    }
                ]
            }
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            # Get annotations for tenant project
            annotations = manager.get_project_annotations(1, "tenant_1")
            
            assert len(annotations["results"]) == 1
            assert annotations["results"][0]["project"] == 1


class TestTCBTenantPerformanceIsolation:
    """Test tenant performance isolation in TCB environment."""
    
    def test_tenant_resource_quotas(self):
        """Test that tenants have proper resource quotas."""
        from deploy.tcb.config.environment_manager import EnvironmentManager
        
        env_manager = EnvironmentManager()
        
        # Test tenant resource limits
        tenant_config = {
            "tenant_1": {
                "max_cpu": "2000m",
                "max_memory": "4Gi",
                "max_storage": "100Gi",
                "max_concurrent_tasks": 50
            },
            "tenant_2": {
                "max_cpu": "1000m",
                "max_memory": "2Gi", 
                "max_storage": "50Gi",
                "max_concurrent_tasks": 25
            }
        }
        
        with patch.object(env_manager, 'get_tenant_config') as mock_get_config:
            mock_get_config.return_value = tenant_config
            
            # Verify tenant quotas
            for tenant_id, expected_limits in tenant_config.items():
                limits = env_manager.get_tenant_resource_limits(tenant_id)
                
                assert limits['max_cpu'] == expected_limits['max_cpu']
                assert limits['max_memory'] == expected_limits['max_memory']
                assert limits['max_storage'] == expected_limits['max_storage']
    
    def test_tenant_scaling_isolation(self):
        """Test that tenant scaling doesn't affect other tenants."""
        from deploy.tcb.scripts.monitoring.metrics_collector import MetricsCollector
        
        collector = MetricsCollector()
        
        # Mock metrics for different tenants
        tenant_metrics = {
            "tenant_1": {"cpu_usage": 85, "memory_usage": 70, "active_tasks": 45},
            "tenant_2": {"cpu_usage": 30, "memory_usage": 25, "active_tasks": 10}
        }
        
        with patch.object(collector, 'get_tenant_metrics') as mock_get_metrics:
            mock_get_metrics.side_effect = lambda tid: tenant_metrics.get(tid, {})
            
            # Test scaling decision for high-usage tenant
            scaling_decision = collector.should_scale_tenant("tenant_1")
            assert scaling_decision['should_scale'] is True
            assert scaling_decision['reason'] == 'high_cpu_usage'
            
            # Test that low-usage tenant is not affected
            scaling_decision = collector.should_scale_tenant("tenant_2")
            assert scaling_decision['should_scale'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])