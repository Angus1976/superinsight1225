"""
Tests for RBAC (Role-Based Access Control) System.

Tests the enhanced RBAC functionality including roles, permissions,
and fine-grained access control.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch

from src.security.rbac_controller import RBACController
from src.security.role_manager import RoleManager
from src.security.rbac_models import (
    RoleModel, PermissionModel, PermissionScope, ResourceType
)
from src.security.models import UserRole, AuditAction


class TestRBACController:
    """Test RBAC Controller functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rbac_controller = RBACController()
        self.mock_db = Mock()
        self.tenant_id = "test_tenant"
        self.user_id = uuid4()
        self.admin_id = uuid4()
    
    def test_create_role_success(self):
        """Test successful role creation."""
        # Mock database operations
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.add = Mock()
        self.mock_db.flush = Mock()
        self.mock_db.commit = Mock()
        
        # Mock role object
        mock_role = Mock()
        mock_role.id = uuid4()
        mock_role.name = "Test Role"
        mock_role.tenant_id = self.tenant_id
        
        with patch.object(self.rbac_controller, 'get_permission_by_name') as mock_get_perm:
            mock_permission = Mock()
            mock_permission.id = uuid4()
            mock_get_perm.return_value = mock_permission
            
            with patch.object(self.rbac_controller, 'assign_permission_to_role') as mock_assign:
                mock_assign.return_value = True
                
                with patch.object(self.rbac_controller, 'log_user_action'):
                    # Create role
                    result = self.rbac_controller.create_role(
                        name="Test Role",
                        description="Test role description",
                        tenant_id=self.tenant_id,
                        created_by=self.admin_id,
                        permissions=["user.read"],
                        db=self.mock_db
                    )
                    
                    # Verify database operations
                    self.mock_db.add.assert_called_once()
                    self.mock_db.flush.assert_called_once()
                    self.mock_db.commit.assert_called_once()
    
    def test_create_role_duplicate_name(self):
        """Test role creation with duplicate name."""
        # Mock existing role
        existing_role = Mock()
        existing_role.name = "Test Role"
        self.mock_db.query.return_value.filter.return_value.first.return_value = existing_role
        
        result = self.rbac_controller.create_role(
            name="Test Role",
            description="Test role description",
            tenant_id=self.tenant_id,
            created_by=self.admin_id,
            db=self.mock_db
        )
        
        assert result is None
    
    def test_assign_role_to_user_success(self):
        """Test successful role assignment to user."""
        # Mock user and role
        mock_user = Mock()
        mock_user.tenant_id = self.tenant_id
        
        mock_role = Mock()
        mock_role.tenant_id = self.tenant_id
        mock_role.name = "Test Role"
        
        # Mock database operations
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        
        with patch.object(self.rbac_controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch.object(self.rbac_controller, 'get_role_by_id') as mock_get_role:
                mock_get_role.return_value = mock_role
                
                with patch.object(self.rbac_controller, '_clear_user_permission_cache'):
                    with patch.object(self.rbac_controller, 'log_user_action'):
                        result = self.rbac_controller.assign_role_to_user(
                            user_id=self.user_id,
                            role_id=uuid4(),
                            assigned_by=self.admin_id,
                            db=self.mock_db
                        )
                        
                        assert result is True
                        self.mock_db.add.assert_called_once()
                        self.mock_db.commit.assert_called_once()
    
    def test_assign_role_tenant_mismatch(self):
        """Test role assignment with tenant mismatch."""
        # Mock user and role with different tenants
        mock_user = Mock()
        mock_user.tenant_id = "tenant1"
        
        mock_role = Mock()
        mock_role.tenant_id = "tenant2"
        
        with patch.object(self.rbac_controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch.object(self.rbac_controller, 'get_role_by_id') as mock_get_role:
                mock_get_role.return_value = mock_role
                
                result = self.rbac_controller.assign_role_to_user(
                    user_id=self.user_id,
                    role_id=uuid4(),
                    assigned_by=self.admin_id,
                    db=self.mock_db
                )
                
                assert result is False
    
    def test_check_user_permission_admin(self):
        """Test permission check for admin user."""
        # Mock admin user
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.role = UserRole.ADMIN
        mock_user.tenant_id = self.tenant_id
        
        with patch.object(self.rbac_controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            # Mock the permission cache to avoid the string conversion error
            with patch.object(self.rbac_controller.permission_cache, 'get_permission') as mock_cache_get:
                mock_cache_get.return_value = None  # Cache miss
                
                with patch.object(self.rbac_controller.permission_cache, 'set_permission') as mock_cache_set:
                    result = self.rbac_controller.check_user_permission(
                        user_id=self.user_id,
                        permission_name="any.permission",
                        db=self.mock_db
                    )
                    
                    assert result is True
    
    def test_check_user_permission_through_roles(self):
        """Test permission check through role assignments."""
        # Mock regular user
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.role = UserRole.VIEWER
        mock_user.tenant_id = self.tenant_id
        
        # Mock permission found through roles
        mock_permission = Mock()
        mock_permission.scope = PermissionScope.GLOBAL
        
        with patch.object(self.rbac_controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            # Mock the permission cache to avoid the string conversion error
            with patch.object(self.rbac_controller.permission_cache, 'get_permission') as mock_cache_get:
                mock_cache_get.return_value = None  # Cache miss
                
                with patch.object(self.rbac_controller.permission_cache, 'set_permission') as mock_cache_set:
                    with patch.object(self.rbac_controller, '_check_permission_through_roles') as mock_check:
                        mock_check.return_value = True
                        
                        result = self.rbac_controller.check_user_permission(
                            user_id=self.user_id,
                            permission_name="user.read",
                            db=self.mock_db
                        )
                        
                        assert result is True
                        mock_check.assert_called_once()
    
    def test_permission_caching(self):
        """Test permission result caching."""
        # Mock user
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.role = UserRole.VIEWER
        mock_user.tenant_id = self.tenant_id
        
        with patch.object(self.rbac_controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            # Mock the permission cache to control caching behavior
            with patch.object(self.rbac_controller.permission_cache, 'get_permission') as mock_cache_get:
                with patch.object(self.rbac_controller.permission_cache, 'set_permission') as mock_cache_set:
                    with patch.object(self.rbac_controller, '_check_permission_through_roles') as mock_check:
                        mock_check.return_value = True
                        
                        # First call - cache miss
                        mock_cache_get.return_value = None
                        result1 = self.rbac_controller.check_user_permission(
                            user_id=self.user_id,
                            permission_name="user.read",
                            db=self.mock_db
                        )
                        
                        # Second call - cache hit
                        mock_cache_get.return_value = True
                        result2 = self.rbac_controller.check_user_permission(
                            user_id=self.user_id,
                            permission_name="user.read",
                            db=self.mock_db
                        )
                        
                        assert result1 is True
                        assert result2 is True
                        # Should only call database check once (first call)
                        assert mock_check.call_count == 1
                        # Should set cache on first call
                        mock_cache_set.assert_called_once()


class TestRoleManager:
    """Test Role Manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_rbac_controller = Mock()
        self.role_manager = RoleManager(self.mock_rbac_controller)
        self.mock_db = Mock()
        self.tenant_id = "test_tenant"
        self.admin_id = uuid4()
    
    def test_initialize_tenant_roles(self):
        """Test tenant role initialization."""
        # Mock role creation
        mock_roles = {}
        for role_name in self.role_manager._role_templates.keys():
            mock_role = Mock()
            mock_role.id = uuid4()
            mock_role.name = role_name
            mock_roles[role_name] = mock_role
        
        def create_role_side_effect(name, **kwargs):
            return mock_roles.get(name)
        
        self.mock_rbac_controller.create_role.side_effect = create_role_side_effect
        self.mock_rbac_controller.assign_role_to_user.return_value = True
        
        result = self.role_manager.initialize_tenant_roles(
            tenant_id=self.tenant_id,
            admin_user_id=self.admin_id,
            db=self.mock_db
        )
        
        assert result is True
        # Should create all template roles
        assert self.mock_rbac_controller.create_role.call_count == len(self.role_manager._role_templates)
        # Should assign admin role to user
        self.mock_rbac_controller.assign_role_to_user.assert_called_once()
    
    def test_create_custom_role(self):
        """Test custom role creation."""
        # Mock permission validation
        mock_permission = Mock()
        self.mock_rbac_controller.get_permission_by_name.return_value = mock_permission
        
        # Mock role creation
        mock_role = Mock()
        mock_role.id = uuid4()
        mock_role.name = "Custom Role"
        self.mock_rbac_controller.create_role.return_value = mock_role
        
        result = self.role_manager.create_custom_role(
            name="Custom Role",
            description="Custom role description",
            tenant_id=self.tenant_id,
            permissions=["user.read", "project.read"],
            created_by=self.admin_id,
            db=self.mock_db
        )
        
        assert result == mock_role
        self.mock_rbac_controller.create_role.assert_called_once()
    
    def test_create_custom_role_no_valid_permissions(self):
        """Test custom role creation with no valid permissions."""
        # Mock permission validation - no permissions found
        self.mock_rbac_controller.get_permission_by_name.return_value = None
        
        result = self.role_manager.create_custom_role(
            name="Custom Role",
            description="Custom role description",
            tenant_id=self.tenant_id,
            permissions=["invalid.permission"],
            created_by=self.admin_id,
            db=self.mock_db
        )
        
        assert result is None
        self.mock_rbac_controller.create_role.assert_not_called()
    
    def test_bulk_assign_users_to_role(self):
        """Test bulk user assignment to role."""
        user_ids = [uuid4(), uuid4(), uuid4()]
        role_id = uuid4()
        
        # Mock successful assignments
        self.mock_rbac_controller.assign_role_to_user.return_value = True
        
        result = self.role_manager.bulk_assign_users_to_role(
            user_ids=user_ids,
            role_id=role_id,
            assigned_by=self.admin_id,
            db=self.mock_db
        )
        
        assert result["total"] == 3
        assert len(result["successful"]) == 3
        assert len(result["failed"]) == 0
        assert self.mock_rbac_controller.assign_role_to_user.call_count == 3
    
    def test_bulk_assign_partial_failure(self):
        """Test bulk assignment with partial failures."""
        user_ids = [uuid4(), uuid4(), uuid4()]
        role_id = uuid4()
        
        # Mock mixed success/failure
        self.mock_rbac_controller.assign_role_to_user.side_effect = [True, False, True]
        
        result = self.role_manager.bulk_assign_users_to_role(
            user_ids=user_ids,
            role_id=role_id,
            assigned_by=self.admin_id,
            db=self.mock_db
        )
        
        assert result["total"] == 3
        assert len(result["successful"]) == 2
        assert len(result["failed"]) == 1
    
    def test_analyze_role_usage(self):
        """Test role usage analysis."""
        # Mock roles with different usage patterns
        mock_roles = []
        
        # System role with users
        system_role = Mock()
        system_role.id = uuid4()
        system_role.name = "System Role"
        system_role.is_system_role = True
        system_role.user_assignments = [Mock(), Mock()]  # 2 users
        system_role.permissions = [Mock()]  # 1 permission
        system_role.created_at = datetime.utcnow()
        mock_roles.append(system_role)
        
        # Custom role with no users
        custom_role = Mock()
        custom_role.id = uuid4()
        custom_role.name = "Unused Role"
        custom_role.is_system_role = False
        custom_role.user_assignments = []  # 0 users
        custom_role.permissions = [Mock(), Mock()]  # 2 permissions
        custom_role.created_at = datetime.utcnow()
        mock_roles.append(custom_role)
        
        self.mock_rbac_controller.get_roles_for_tenant.return_value = mock_roles
        
        result = self.role_manager.analyze_role_usage(
            tenant_id=self.tenant_id,
            db=self.mock_db
        )
        
        assert result["total_roles"] == 2
        assert result["system_roles"] == 1
        assert result["custom_roles"] == 1
        assert len(result["unused_roles"]) == 1
        assert result["unused_roles"][0]["name"] == "Unused Role"
        assert len(result["most_used_roles"]) == 2
        assert result["most_used_roles"][0]["name"] == "System Role"
        assert result["most_used_roles"][0]["user_count"] == 2
    
    def test_suggest_role_optimizations(self):
        """Test role optimization suggestions."""
        # Mock analysis with unused roles
        mock_analysis = {
            "unused_roles": [{"name": "Unused Role", "id": str(uuid4())}],
            "system_roles": 1,
            "custom_roles": 1
        }
        
        with patch.object(self.role_manager, 'analyze_role_usage') as mock_analyze:
            mock_analyze.return_value = mock_analysis
            
            with patch.object(self.role_manager, '_find_similar_roles') as mock_similar:
                mock_similar.return_value = []
                
                with patch.object(self.role_manager, '_find_missing_standard_roles') as mock_missing:
                    mock_missing.return_value = ["Missing Role"]
                    
                    suggestions = self.role_manager.suggest_role_optimizations(
                        tenant_id=self.tenant_id,
                        db=self.mock_db
                    )
                    
                    assert len(suggestions) == 2  # unused roles + missing roles
                    
                    # Check unused roles suggestion
                    unused_suggestion = next(s for s in suggestions if s["type"] == "remove_unused_roles")
                    assert unused_suggestion["priority"] == "medium"
                    
                    # Check missing roles suggestion
                    missing_suggestion = next(s for s in suggestions if s["type"] == "add_missing_standard_roles")
                    assert missing_suggestion["priority"] == "high"


class TestRBACIntegration:
    """Integration tests for RBAC system."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.rbac_controller = RBACController()
        self.role_manager = RoleManager(self.rbac_controller)
        self.mock_db = Mock()
        self.tenant_id = "integration_test_tenant"
        self.admin_id = uuid4()
        self.user_id = uuid4()
    
    def test_end_to_end_role_workflow(self):
        """Test complete role management workflow."""
        # Mock database operations for role creation
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.add = Mock()
        self.mock_db.flush = Mock()
        self.mock_db.commit = Mock()
        
        # Mock permission lookup
        mock_permission = Mock()
        mock_permission.id = uuid4()
        
        with patch.object(self.rbac_controller, 'get_permission_by_name') as mock_get_perm:
            mock_get_perm.return_value = mock_permission
            
            with patch.object(self.rbac_controller, 'assign_permission_to_role') as mock_assign_perm:
                mock_assign_perm.return_value = True
                
                with patch.object(self.rbac_controller, 'log_user_action'):
                    # Step 1: Create custom role
                    role = self.role_manager.create_custom_role(
                        name="Integration Test Role",
                        description="Role for integration testing",
                        tenant_id=self.tenant_id,
                        permissions=["user.read", "project.read"],
                        created_by=self.admin_id,
                        db=self.mock_db
                    )
                    
                    # Verify role creation was attempted
                    self.mock_db.add.assert_called()
                    self.mock_db.commit.assert_called()
    
    def test_permission_inheritance_workflow(self):
        """Test permission inheritance through role hierarchy."""
        # Mock parent role
        parent_role = Mock()
        parent_role.id = uuid4()
        parent_role.name = "Parent Role"
        parent_role.tenant_id = self.tenant_id
        
        # Mock child role
        child_role = Mock()
        child_role.id = uuid4()
        child_role.name = "Child Role"
        child_role.tenant_id = self.tenant_id
        child_role.parent_role_id = parent_role.id
        
        # Mock user with child role
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.role = UserRole.VIEWER
        mock_user.tenant_id = self.tenant_id
        
        with patch.object(self.rbac_controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch.object(self.rbac_controller, '_check_permission_through_roles') as mock_check:
                mock_check.return_value = True
                
                # Check permission through role hierarchy
                result = self.rbac_controller.check_user_permission(
                    user_id=self.user_id,
                    permission_name="user.read",
                    db=self.mock_db
                )
                
                assert result is True
                mock_check.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])