"""
Unit tests for Transfer Permission Middleware.

Tests the permission check middleware functions for data transfer operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException

from src.middleware.transfer_permission_middleware import (
    check_transfer_permission,
    require_admin_or_data_manager,
    require_admin,
    get_permission_service
)
from src.services.permission_service import (
    PermissionService,
    PermissionResult,
    UserRole
)
from src.security.models import UserModel


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = Mock(spec=UserModel)
    user.id = "user-123"
    user.username = "testuser"
    user.role = UserRole.DATA_ANALYST
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = Mock(spec=UserModel)
    user.id = "admin-123"
    user.username = "admin"
    user.role = UserRole.ADMIN
    return user


@pytest.fixture
def mock_data_manager_user():
    """Create a mock data manager user."""
    user = Mock(spec=UserModel)
    user.id = "manager-123"
    user.username = "manager"
    user.role = UserRole.DATA_MANAGER
    return user


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


class TestCheckTransferPermission:
    """Tests for check_transfer_permission dependency."""
    
    @pytest.mark.asyncio
    async def test_allowed_permission(self, mock_user, mock_db):
        """Test successful permission check."""
        # Data analyst can transfer to temp_stored without approval
        result = await check_transfer_permission(
            target_state="temp_stored",
            record_count=10,
            is_cross_project=False,
            current_user=mock_user,
            db=mock_db
        )
        
        assert result.allowed is True
        assert result.requires_approval is False
        assert result.current_role == UserRole.DATA_ANALYST
    
    @pytest.mark.asyncio
    async def test_requires_approval(self, mock_user, mock_db):
        """Test permission that requires approval."""
        # Data analyst needs approval for sample library
        result = await check_transfer_permission(
            target_state="in_sample_library",
            record_count=10,
            is_cross_project=False,
            current_user=mock_user,
            db=mock_db
        )
        
        assert result.allowed is True
        assert result.requires_approval is True
        assert result.current_role == UserRole.DATA_ANALYST
    
    @pytest.mark.asyncio
    async def test_permission_denied(self, mock_user, mock_db):
        """Test permission denied for batch transfer."""
        # Data analyst cannot do batch transfer (>1000 records)
        with pytest.raises(HTTPException) as exc_info:
            await check_transfer_permission(
                target_state="temp_stored",
                record_count=1500,
                is_cross_project=False,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "PERMISSION_DENIED"
        assert "permission" in exc_info.value.detail["message"].lower()
    
    @pytest.mark.asyncio
    async def test_cross_project_denied(self, mock_user, mock_db):
        """Test cross-project transfer denied for non-admin."""
        # Data analyst cannot do cross-project transfer
        with pytest.raises(HTTPException) as exc_info:
            await check_transfer_permission(
                target_state="temp_stored",
                record_count=10,
                is_cross_project=True,
                current_user=mock_user,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "PERMISSION_DENIED"
    
    @pytest.mark.asyncio
    async def test_admin_full_access(self, mock_admin_user, mock_db):
        """Test admin has full access without approval."""
        # Admin can do everything without approval
        result = await check_transfer_permission(
            target_state="in_sample_library",
            record_count=2000,
            is_cross_project=True,
            current_user=mock_admin_user,
            db=mock_db
        )
        
        assert result.allowed is True
        assert result.requires_approval is False
        assert result.current_role == UserRole.ADMIN


class TestRequireAdminOrDataManager:
    """Tests for require_admin_or_data_manager dependency."""
    
    @pytest.mark.asyncio
    async def test_admin_allowed(self, mock_admin_user):
        """Test admin is allowed."""
        result = await require_admin_or_data_manager(current_user=mock_admin_user)
        assert result == mock_admin_user
    
    @pytest.mark.asyncio
    async def test_data_manager_allowed(self, mock_data_manager_user):
        """Test data manager is allowed."""
        result = await require_admin_or_data_manager(current_user=mock_data_manager_user)
        assert result == mock_data_manager_user
    
    @pytest.mark.asyncio
    async def test_data_analyst_denied(self, mock_user):
        """Test data analyst is denied."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin_or_data_manager(current_user=mock_user)
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "INSUFFICIENT_PRIVILEGES"
        assert "admin" in exc_info.value.detail["message"].lower()


class TestRequireAdmin:
    """Tests for require_admin dependency."""
    
    @pytest.mark.asyncio
    async def test_admin_allowed(self, mock_admin_user):
        """Test admin is allowed."""
        result = await require_admin(current_user=mock_admin_user)
        assert result == mock_admin_user
    
    @pytest.mark.asyncio
    async def test_data_manager_denied(self, mock_data_manager_user):
        """Test data manager is denied."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(current_user=mock_data_manager_user)
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "ADMIN_REQUIRED"
    
    @pytest.mark.asyncio
    async def test_data_analyst_denied(self, mock_user):
        """Test data analyst is denied."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(current_user=mock_user)
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error_code"] == "ADMIN_REQUIRED"


class TestGetPermissionService:
    """Tests for get_permission_service dependency."""
    
    def test_returns_service_instance(self, mock_db):
        """Test that it returns a PermissionService instance."""
        service = get_permission_service(db=mock_db)
        assert isinstance(service, PermissionService)
    
    def test_service_has_permission_matrix(self, mock_db):
        """Test that the service has the permission matrix."""
        service = get_permission_service(db=mock_db)
        assert hasattr(service, 'PERMISSION_MATRIX')
        assert UserRole.ADMIN in service.PERMISSION_MATRIX


class TestErrorMessages:
    """Tests for error message internationalization."""
    
    @pytest.mark.asyncio
    async def test_permission_denied_has_i18n(self, mock_user, mock_db):
        """Test that permission denied errors include i18n messages."""
        with pytest.raises(HTTPException) as exc_info:
            await check_transfer_permission(
                target_state="temp_stored",
                record_count=1500,
                is_cross_project=False,
                current_user=mock_user,
                db=mock_db
            )
        
        detail = exc_info.value.detail
        assert "message" in detail
        assert "message_zh" in detail
        assert detail["message_zh"] == "您没有权限执行此操作"
    
    @pytest.mark.asyncio
    async def test_admin_required_has_i18n(self, mock_user):
        """Test that admin required errors include i18n messages."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(current_user=mock_user)
        
        detail = exc_info.value.detail
        assert "message" in detail
        assert "message_zh" in detail
        assert detail["message_zh"] == "只有管理员可以执行此操作"


class TestPermissionResultDetails:
    """Tests for permission result details."""
    
    @pytest.mark.asyncio
    async def test_result_includes_role_info(self, mock_user, mock_db):
        """Test that permission result includes role information."""
        result = await check_transfer_permission(
            target_state="temp_stored",
            record_count=10,
            is_cross_project=False,
            current_user=mock_user,
            db=mock_db
        )
        
        assert result.current_role == UserRole.DATA_ANALYST
        assert hasattr(result, 'allowed')
        assert hasattr(result, 'requires_approval')
    
    @pytest.mark.asyncio
    async def test_error_includes_context(self, mock_user, mock_db):
        """Test that error includes context information."""
        with pytest.raises(HTTPException) as exc_info:
            await check_transfer_permission(
                target_state="temp_stored",
                record_count=1500,
                is_cross_project=False,
                current_user=mock_user,
                db=mock_db
            )
        
        detail = exc_info.value.detail
        assert detail["current_role"] == UserRole.DATA_ANALYST.value
        assert detail["target_state"] == "temp_stored"
        assert "required_permission" in detail
