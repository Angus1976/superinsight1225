"""
Unit tests for permission models.

Tests the UserRole enum and PermissionResult model to ensure
they work correctly according to the design specification.
"""

import pytest
from pydantic import ValidationError

from src.models.permission import UserRole, PermissionResult


class TestUserRole:
    """Test UserRole enum."""
    
    def test_user_role_values(self):
        """Test that all expected user roles are defined."""
        assert UserRole.ADMIN == "admin"
        assert UserRole.DATA_MANAGER == "data_manager"
        assert UserRole.DATA_ANALYST == "data_analyst"
        assert UserRole.USER == "user"
    
    def test_user_role_value_access(self):
        """Test that UserRole values can be accessed."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.DATA_MANAGER.value == "data_manager"
    
    def test_user_role_from_string(self):
        """Test that UserRole can be created from string."""
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("data_manager") == UserRole.DATA_MANAGER
        assert UserRole("data_analyst") == UserRole.DATA_ANALYST
        assert UserRole("user") == UserRole.USER
    
    def test_user_role_invalid_value(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError):
            UserRole("invalid_role")


class TestPermissionResult:
    """Test PermissionResult model."""
    
    def test_permission_result_allowed(self):
        """Test creating a PermissionResult for allowed operation."""
        result = PermissionResult(
            allowed=True,
            requires_approval=False,
            current_role=UserRole.ADMIN
        )
        
        assert result.allowed is True
        assert result.requires_approval is False
        assert result.current_role == UserRole.ADMIN
        assert result.required_role is None
        assert result.reason is None
    
    def test_permission_result_requires_approval(self):
        """Test creating a PermissionResult that requires approval."""
        result = PermissionResult(
            allowed=True,
            requires_approval=True,
            current_role=UserRole.DATA_ANALYST
        )
        
        assert result.allowed is True
        assert result.requires_approval is True
        assert result.current_role == UserRole.DATA_ANALYST
    
    def test_permission_result_denied(self):
        """Test creating a PermissionResult for denied operation."""
        result = PermissionResult(
            allowed=False,
            requires_approval=False,
            current_role=UserRole.USER,
            required_role=UserRole.DATA_MANAGER,
            reason="Insufficient permissions for batch transfer"
        )
        
        assert result.allowed is False
        assert result.requires_approval is False
        assert result.current_role == UserRole.USER
        assert result.required_role == UserRole.DATA_MANAGER
        assert result.reason == "Insufficient permissions for batch transfer"
    
    def test_permission_result_missing_required_fields(self):
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PermissionResult(
                allowed=True
                # Missing requires_approval and current_role
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 2
        field_names = {error['loc'][0] for error in errors}
        assert 'requires_approval' in field_names
        assert 'current_role' in field_names
    
    def test_permission_result_json_serialization(self):
        """Test that PermissionResult can be serialized to JSON."""
        result = PermissionResult(
            allowed=True,
            requires_approval=False,
            current_role=UserRole.ADMIN
        )
        
        json_data = result.model_dump()
        
        assert json_data['allowed'] is True
        assert json_data['requires_approval'] is False
        assert json_data['current_role'] == 'admin'
        assert json_data['required_role'] is None
        assert json_data['reason'] is None
    
    def test_permission_result_from_dict(self):
        """Test creating PermissionResult from dictionary."""
        data = {
            'allowed': False,
            'requires_approval': False,
            'current_role': 'user',
            'required_role': 'data_manager',
            'reason': 'Operation not allowed'
        }
        
        result = PermissionResult(**data)
        
        assert result.allowed is False
        assert result.requires_approval is False
        assert result.current_role == UserRole.USER
        assert result.required_role == UserRole.DATA_MANAGER
        assert result.reason == 'Operation not allowed'
