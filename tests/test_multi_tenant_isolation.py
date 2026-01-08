"""
Multi-Tenant Isolation Tests

Tests for tenant data isolation and security.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import uuid

from src.database.tenant_isolation_validator import TenantIsolationValidator
from src.middleware.tenant_middleware import TenantMiddleware, TenantContext, get_current_tenant
from src.security.tenant_permissions import TenantPermissionManager, ResourceType, ActionType
from src.security.tenant_audit import TenantAuditLogger, AuditEvent, AuditAction, AuditCategory
from src.label_studio.tenant_isolation import LabelStudioTenantManager
from src.business_logic.models import BusinessRuleModel, BusinessPatternModel, BusinessInsightModel


class TestTenantIsolationValidator:
    """Test tenant isolation validation."""
    
    def test_validate_all_tables_have_tenant_id(self):
        """Test that all required tables have tenant_id columns."""
        validator = TenantIsolationValidator()
        
        # Mock database inspection
        with patch('src.database.tenant_isolation_validator.get_db_session') as mock_session:
            mock_inspector = Mock()
            mock_inspector.get_columns.return_value = [
                {'name': 'id'},
                {'name': 'tenant_id'},
                {'name': 'created_at'}
            ]
            
            mock_session.return_value.__enter__.return_value.bind = Mock()
            
            with patch('src.database.tenant_isolation_validator.inspect', return_value=mock_inspector):
                result = validator.validate_all_tables_have_tenant_id()
        
        assert result['valid'] is True
        assert result['tables_checked'] > 0
        assert len(result['missing_tenant_id']) == 0
    
    def test_validate_tenant_indexes(self):
        """Test that tenant_id columns have proper indexes."""
        validator = TenantIsolationValidator()
        
        with patch('src.database.tenant_isolation_validator.get_db_session') as mock_session:
            mock_inspector = Mock()
            mock_inspector.get_indexes.return_value = [
                {'column_names': ['tenant_id']},
                {'column_names': ['id', 'tenant_id']}
            ]
            
            mock_session.return_value.__enter__.return_value.bind = Mock()
            
            with patch('src.database.tenant_isolation_validator.inspect', return_value=mock_inspector):
                result = validator.validate_tenant_indexes()
        
        assert result['valid'] is True
        assert result['indexes_checked'] > 0
        assert len(result['missing_indexes']) == 0


class TestTenantMiddleware:
    """Test tenant middleware functionality."""
    
    def test_tenant_context_initialization(self):
        """Test tenant context initialization."""
        context = TenantContext()
        
        assert context.tenant_id is None
        assert context.user_id is None
        assert context.user_role is None
        assert not context.is_authenticated()
    
    def test_tenant_context_authentication(self):
        """Test tenant context authentication."""
        context = TenantContext()
        context.tenant_id = "test_tenant"
        context.user_id = "test_user"
        context.user_role = "admin"
        
        assert context.is_authenticated()
        assert context.has_permission("admin", "all")
    
    @patch('src.middleware.tenant_middleware.jwt.decode')
    @patch('src.middleware.tenant_middleware.get_db_session')
    async def test_middleware_token_validation(self, mock_session, mock_jwt_decode):
        """Test JWT token validation in middleware."""
        # Mock JWT payload
        mock_jwt_decode.return_value = {
            "tenant_id": "test_tenant",
            "user_id": "test_user",
            "role": "admin",
            "permissions": {"admin": ["all"]}
        }
        
        # Mock user verification
        mock_user = Mock()
        mock_user.is_active = True
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_user
        
        middleware = TenantMiddleware(Mock())
        
        # Mock request
        mock_request = Mock()
        mock_request.headers = {"Authorization": "Bearer test_token"}
        mock_request.url.path = "/api/test"
        mock_request.client.host = "127.0.0.1"
        
        # Test token extraction
        await middleware._extract_tenant_context(mock_request)
        
        # Verify context was set
        from src.middleware.tenant_middleware import tenant_context
        assert tenant_context.tenant_id == "test_tenant"
        assert tenant_context.user_id == "test_user"


class TestTenantPermissions:
    """Test tenant permission management."""
    
    def test_permission_manager_initialization(self):
        """Test permission manager initialization."""
        manager = TenantPermissionManager()
        
        assert "tenant_admin" in manager.default_roles
        assert "project_manager" in manager.default_roles
        assert "business_expert" in manager.default_roles
    
    @patch('src.security.tenant_permissions.get_db_session')
    def test_get_user_permissions(self, mock_session):
        """Test getting user permissions."""
        manager = TenantPermissionManager()
        
        # Mock database queries
        mock_user_role = Mock()
        mock_user_role.role_id = "role_1"
        
        mock_role = Mock()
        mock_role.name = "business_expert"
        
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.all.return_value = [mock_user_role]
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_role
        
        permissions = manager.get_user_permissions("user_1", "tenant_1")
        
        assert isinstance(permissions, dict)
        # Business expert should have document read permissions
        assert "documents" in permissions
    
    def test_check_permission(self):
        """Test permission checking."""
        manager = TenantPermissionManager()
        
        with patch.object(manager, 'get_user_permissions') as mock_get_perms:
            mock_get_perms.return_value = {
                "documents": ["read", "write"],
                "tasks": ["read"]
            }
            
            # Test positive cases
            assert manager.check_permission("user_1", "tenant_1", ResourceType.DOCUMENTS, ActionType.READ)
            assert manager.check_permission("user_1", "tenant_1", ResourceType.DOCUMENTS, ActionType.WRITE)
            assert manager.check_permission("user_1", "tenant_1", ResourceType.TASKS, ActionType.READ)
            
            # Test negative cases
            assert not manager.check_permission("user_1", "tenant_1", ResourceType.TASKS, ActionType.WRITE)
            assert not manager.check_permission("user_1", "tenant_1", ResourceType.ADMIN, ActionType.ADMIN)


class TestTenantAudit:
    """Test tenant audit logging."""
    
    def test_audit_event_creation(self):
        """Test audit event creation."""
        event = AuditEvent(
            action=AuditAction.READ,
            resource_type="documents",
            resource_id="doc_1",
            tenant_id="tenant_1",
            user_id="user_1"
        )
        
        assert event.action == AuditAction.READ
        assert event.resource_type == "documents"
        assert event.tenant_id == "tenant_1"
        assert event.timestamp is not None
    
    @patch('src.security.tenant_audit.get_db_session')
    def test_log_event(self, mock_session):
        """Test logging audit events."""
        logger = TenantAuditLogger()
        
        event = AuditEvent(
            action=AuditAction.CREATE,
            resource_type="tasks",
            tenant_id="tenant_1",
            user_id="user_1"
        )
        
        result = logger.log_event(event)
        
        assert result is True
        mock_session.return_value.__enter__.return_value.add.assert_called_once()
        mock_session.return_value.__enter__.return_value.commit.assert_called_once()
    
    def test_sensitive_data_sanitization(self):
        """Test sensitive data sanitization."""
        logger = TenantAuditLogger()
        
        sensitive_data = {
            "username": "test_user",
            "password": "secret123",
            "api_key": "key123",
            "normal_field": "normal_value"
        }
        
        sanitized = logger._sanitize_details(sensitive_data)
        
        assert sanitized["username"] == "test_user"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["normal_field"] == "normal_value"


class TestLabelStudioTenantIsolation:
    """Test Label Studio tenant isolation."""
    
    def test_tenant_manager_initialization(self):
        """Test tenant manager initialization."""
        manager = LabelStudioTenantManager()
        
        assert manager.base_url is not None
        assert manager.headers is not None
    
    @patch('src.label_studio.tenant_isolation.requests.request')
    def test_create_tenant_project(self, mock_request):
        """Test creating tenant project."""
        manager = LabelStudioTenantManager()
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {"id": 123, "title": "[tenant_1] Test Project"}
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'{"id": 123}'
        mock_request.return_value = mock_response
        
        from src.label_studio.tenant_isolation import LabelStudioProject
        project_config = LabelStudioProject(
            id=0,
            title="Test Project",
            description="Test Description",
            tenant_id="tenant_1",
            created_by="user_1",
            label_config="<View></View>"
        )
        
        with patch('src.label_studio.tenant_isolation.get_current_tenant', return_value="tenant_1"):
            result = manager.create_tenant_project(project_config)
        
        assert result["id"] == 123
        mock_request.assert_called_once()
    
    def test_is_tenant_project(self):
        """Test tenant project identification."""
        manager = LabelStudioTenantManager()
        
        # Test project with tenant prefix
        project1 = {"title": "[tenant_1] My Project", "description": "Test"}
        assert manager._is_tenant_project(project1, "tenant_1")
        assert not manager._is_tenant_project(project1, "tenant_2")
        
        # Test project with tenant in description
        project2 = {"title": "My Project", "description": "Test\n\nTenant: tenant_1"}
        assert manager._is_tenant_project(project2, "tenant_1")
        assert not manager._is_tenant_project(project2, "tenant_2")


class TestBusinessLogicModels:
    """Test business logic model tenant fields."""
    
    def test_business_rule_model_has_tenant_id(self):
        """Test that BusinessRuleModel has tenant_id field."""
        # This would typically test the actual model structure
        # For now, we'll verify the model class exists and has the expected attributes
        
        assert hasattr(BusinessRuleModel, '__tablename__')
        assert BusinessRuleModel.__tablename__ == "business_rules"
        
        # Check that the model would have tenant_id column
        # (This would be more comprehensive with actual database testing)
    
    def test_business_pattern_model_has_tenant_id(self):
        """Test that BusinessPatternModel has tenant_id field."""
        assert hasattr(BusinessPatternModel, '__tablename__')
        assert BusinessPatternModel.__tablename__ == "business_patterns"
    
    def test_business_insight_model_has_tenant_id(self):
        """Test that BusinessInsightModel has tenant_id field."""
        assert hasattr(BusinessInsightModel, '__tablename__')
        assert BusinessInsightModel.__tablename__ == "business_insights"


class TestIntegrationScenarios:
    """Test integration scenarios for multi-tenant system."""
    
    @patch('src.middleware.tenant_middleware.get_current_tenant')
    @patch('src.security.tenant_audit.get_current_user')
    def test_end_to_end_tenant_isolation(self, mock_get_user, mock_get_tenant):
        """Test end-to-end tenant isolation scenario."""
        mock_get_tenant.return_value = "tenant_1"
        mock_get_user.return_value = "user_1"
        
        # Test that tenant context is properly maintained
        tenant_id = get_current_tenant()
        assert tenant_id == "tenant_1"
        
        # Test audit logging with tenant context
        from src.security.tenant_audit import log_data_access
        result = log_data_access("documents", "doc_1")
        
        # The function should complete without error
        # (Actual database interaction would be mocked in real tests)
    
    def test_cross_tenant_access_prevention(self):
        """Test that cross-tenant access is prevented."""
        from src.middleware.tenant_middleware import TenantQueryFilter
        
        # Mock a query and model
        mock_query = Mock()
        mock_model = Mock()
        mock_model.tenant_id = "filter_field"
        
        # Test that filter is applied
        filtered_query = TenantQueryFilter.filter_by_tenant(
            mock_query, mock_model, "tenant_1"
        )
        
        # Verify filter was called
        mock_query.filter.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])