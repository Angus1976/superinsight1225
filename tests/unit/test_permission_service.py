"""
Unit tests for PermissionService.

Tests the permission matrix and permission checking logic for both
transfer operations and CRUD operations.
"""

import pytest
from src.services.permission_service import (
    PermissionService,
    UserRole,
    PermissionResult
)


class TestPermissionService:
    """Test suite for PermissionService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = PermissionService()

    # =========================================================================
    # Transfer permissions: Admin
    # =========================================================================

    def test_admin_temp_stored(self):
        """Admin: temp_stored allowed, no approval."""
        result = self.service.check_permission(UserRole.ADMIN, "temp_stored")
        assert result.allowed is True
        assert result.requires_approval is False
        assert result.current_role == UserRole.ADMIN

    def test_admin_sample_library(self):
        """Admin: in_sample_library allowed, no approval."""
        result = self.service.check_permission(UserRole.ADMIN, "in_sample_library")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_admin_annotation_pending(self):
        """Admin: annotation_pending allowed, no approval."""
        result = self.service.check_permission(UserRole.ADMIN, "annotation_pending")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_admin_batch_transfer(self):
        """Admin: batch transfer (>1000 records) allowed."""
        result = self.service.check_permission(
            UserRole.ADMIN, "temp_stored", record_count=2000
        )
        assert result.allowed is True
        assert result.requires_approval is False

    def test_admin_cross_project(self):
        """Admin: cross-project transfer allowed."""
        result = self.service.check_permission(
            UserRole.ADMIN, "temp_stored", is_cross_project=True
        )
        assert result.allowed is True
        assert result.requires_approval is False

    # =========================================================================
    # Transfer permissions: Data Manager
    # =========================================================================

    def test_data_manager_temp_stored(self):
        """Data Manager: temp_stored allowed, no approval."""
        result = self.service.check_permission(UserRole.DATA_MANAGER, "temp_stored")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_manager_sample_library(self):
        """Data Manager: in_sample_library allowed, no approval."""
        result = self.service.check_permission(UserRole.DATA_MANAGER, "in_sample_library")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_manager_annotation_pending(self):
        """Data Manager: annotation_pending allowed, no approval."""
        result = self.service.check_permission(UserRole.DATA_MANAGER, "annotation_pending")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_manager_batch_transfer(self):
        """Data Manager: batch transfer allowed."""
        result = self.service.check_permission(
            UserRole.DATA_MANAGER, "temp_stored", record_count=2000
        )
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_manager_cross_project_denied(self):
        """Data Manager: cross-project transfer denied."""
        result = self.service.check_permission(
            UserRole.DATA_MANAGER, "temp_stored", is_cross_project=True
        )
        assert result.allowed is False

    # =========================================================================
    # Transfer permissions: Data Analyst
    # =========================================================================

    def test_data_analyst_temp_stored(self):
        """Data Analyst: temp_stored allowed, no approval."""
        result = self.service.check_permission(UserRole.DATA_ANALYST, "temp_stored")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_analyst_sample_library_needs_approval(self):
        """Data Analyst: in_sample_library allowed but needs approval."""
        result = self.service.check_permission(UserRole.DATA_ANALYST, "in_sample_library")
        assert result.allowed is True
        assert result.requires_approval is True

    def test_data_analyst_annotation_pending_needs_approval(self):
        """Data Analyst: annotation_pending allowed but needs approval."""
        result = self.service.check_permission(UserRole.DATA_ANALYST, "annotation_pending")
        assert result.allowed is True
        assert result.requires_approval is True

    def test_data_analyst_batch_transfer_denied(self):
        """Data Analyst: batch transfer denied."""
        result = self.service.check_permission(
            UserRole.DATA_ANALYST, "temp_stored", record_count=2000
        )
        assert result.allowed is False

    def test_data_analyst_cross_project_denied(self):
        """Data Analyst: cross-project transfer denied."""
        result = self.service.check_permission(
            UserRole.DATA_ANALYST, "temp_stored", is_cross_project=True
        )
        assert result.allowed is False

    # =========================================================================
    # Transfer permissions: User
    # =========================================================================

    def test_user_temp_stored(self):
        """User: temp_stored allowed, no approval."""
        result = self.service.check_permission(UserRole.USER, "temp_stored")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_user_sample_library_needs_approval(self):
        """User: in_sample_library allowed but needs approval."""
        result = self.service.check_permission(UserRole.USER, "in_sample_library")
        assert result.allowed is True
        assert result.requires_approval is True

    def test_user_annotation_pending_needs_approval(self):
        """User: annotation_pending allowed but needs approval."""
        result = self.service.check_permission(UserRole.USER, "annotation_pending")
        assert result.allowed is True
        assert result.requires_approval is True

    def test_user_batch_transfer_denied(self):
        """User: batch transfer denied."""
        result = self.service.check_permission(
            UserRole.USER, "temp_stored", record_count=2000
        )
        assert result.allowed is False

    def test_user_cross_project_denied(self):
        """User: cross-project transfer denied."""
        result = self.service.check_permission(
            UserRole.USER, "temp_stored", is_cross_project=True
        )
        assert result.allowed is False

    # =========================================================================
    # Batch transfer threshold edge cases
    # =========================================================================

    def test_batch_threshold_at_1000_not_triggered(self):
        """Exactly 1000 records should NOT trigger batch_transfer check."""
        result = self.service.check_permission(
            UserRole.DATA_ANALYST, "temp_stored", record_count=1000
        )
        assert result.allowed is True
        assert result.requires_approval is False

    def test_batch_threshold_at_1001_triggered(self):
        """1001 records should trigger batch_transfer check."""
        result = self.service.check_permission(
            UserRole.DATA_ANALYST, "temp_stored", record_count=1001
        )
        assert result.allowed is False

    def test_cross_project_precedence_over_batch(self):
        """Cross-project flag should take precedence when both conditions met."""
        # Admin: both batch and cross_project allowed
        result = self.service.check_permission(
            UserRole.ADMIN, "temp_stored", record_count=2000, is_cross_project=True
        )
        assert result.allowed is True

    # =========================================================================
    # Transfer edge cases
    # =========================================================================

    def test_unknown_target_state(self):
        """Unknown target state returns not allowed with reason."""
        result = self.service.check_permission(UserRole.ADMIN, "nonexistent_state")
        assert result.allowed is False
        assert result.requires_approval is False
        assert result.reason == "Operation not defined for this role"

    def test_permission_result_includes_current_role(self):
        """PermissionResult always includes the current_role."""
        for role in UserRole:
            result = self.service.check_permission(role, "temp_stored")
            assert result.current_role == role

    # =========================================================================
    # CRUD permissions: Admin
    # =========================================================================

    def test_admin_crud_create(self):
        """Admin: create allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.ADMIN, "create")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_admin_crud_read(self):
        """Admin: read allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.ADMIN, "read")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_admin_crud_update(self):
        """Admin: update allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.ADMIN, "update")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_admin_crud_delete(self):
        """Admin: delete allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.ADMIN, "delete")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_admin_crud_merge(self):
        """Admin: merge allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.ADMIN, "merge")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_admin_crud_split(self):
        """Admin: split allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.ADMIN, "split")
        assert result.allowed is True
        assert result.requires_approval is False

    # =========================================================================
    # CRUD permissions: Data Manager
    # =========================================================================

    def test_data_manager_crud_create(self):
        """Data Manager: create allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.DATA_MANAGER, "create")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_manager_crud_read(self):
        """Data Manager: read allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.DATA_MANAGER, "read")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_manager_crud_update(self):
        """Data Manager: update allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.DATA_MANAGER, "update")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_manager_crud_delete_needs_approval(self):
        """Data Manager: delete allowed but needs approval."""
        result = self.service.check_crud_permission(UserRole.DATA_MANAGER, "delete")
        assert result.allowed is True
        assert result.requires_approval is True

    def test_data_manager_crud_merge(self):
        """Data Manager: merge allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.DATA_MANAGER, "merge")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_manager_crud_split(self):
        """Data Manager: split allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.DATA_MANAGER, "split")
        assert result.allowed is True
        assert result.requires_approval is False

    # =========================================================================
    # CRUD permissions: Data Analyst
    # =========================================================================

    def test_data_analyst_crud_create(self):
        """Data Analyst: create allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.DATA_ANALYST, "create")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_analyst_crud_read(self):
        """Data Analyst: read allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.DATA_ANALYST, "read")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_data_analyst_crud_update_needs_approval(self):
        """Data Analyst: update allowed but needs approval."""
        result = self.service.check_crud_permission(UserRole.DATA_ANALYST, "update")
        assert result.allowed is True
        assert result.requires_approval is True

    def test_data_analyst_crud_delete_denied(self):
        """Data Analyst: delete denied."""
        result = self.service.check_crud_permission(UserRole.DATA_ANALYST, "delete")
        assert result.allowed is False

    def test_data_analyst_crud_merge_denied(self):
        """Data Analyst: merge denied."""
        result = self.service.check_crud_permission(UserRole.DATA_ANALYST, "merge")
        assert result.allowed is False

    def test_data_analyst_crud_split_denied(self):
        """Data Analyst: split denied."""
        result = self.service.check_crud_permission(UserRole.DATA_ANALYST, "split")
        assert result.allowed is False

    # =========================================================================
    # CRUD permissions: User
    # =========================================================================

    def test_user_crud_create_needs_approval(self):
        """User: create allowed but needs approval."""
        result = self.service.check_crud_permission(UserRole.USER, "create")
        assert result.allowed is True
        assert result.requires_approval is True

    def test_user_crud_read(self):
        """User: read allowed, no approval."""
        result = self.service.check_crud_permission(UserRole.USER, "read")
        assert result.allowed is True
        assert result.requires_approval is False

    def test_user_crud_update_denied(self):
        """User: update denied."""
        result = self.service.check_crud_permission(UserRole.USER, "update")
        assert result.allowed is False

    def test_user_crud_delete_denied(self):
        """User: delete denied."""
        result = self.service.check_crud_permission(UserRole.USER, "delete")
        assert result.allowed is False

    def test_user_crud_merge_denied(self):
        """User: merge denied."""
        result = self.service.check_crud_permission(UserRole.USER, "merge")
        assert result.allowed is False

    def test_user_crud_split_denied(self):
        """User: split denied."""
        result = self.service.check_crud_permission(UserRole.USER, "split")
        assert result.allowed is False

    # =========================================================================
    # CRUD edge cases
    # =========================================================================

    def test_crud_unknown_operation(self):
        """Unknown CRUD operation returns not allowed with reason."""
        result = self.service.check_crud_permission(UserRole.ADMIN, "unknown_op")
        assert result.allowed is False
        assert result.requires_approval is False
        assert result.reason == "Operation not defined for this role"

    def test_crud_result_includes_current_role(self):
        """CRUD PermissionResult always includes the current_role."""
        for role in UserRole:
            result = self.service.check_crud_permission(role, "read")
            assert result.current_role == role

    # =========================================================================
    # All roles x all read = allowed (read is universal)
    # =========================================================================

    @pytest.mark.parametrize("role", list(UserRole))
    def test_all_roles_can_read(self, role):
        """Every role should have read permission without approval."""
        result = self.service.check_crud_permission(role, "read")
        assert result.allowed is True
        assert result.requires_approval is False

    # =========================================================================
    # All roles x temp_stored = allowed (temp_stored is universal)
    # =========================================================================

    @pytest.mark.parametrize("role", list(UserRole))
    def test_all_roles_can_transfer_temp_stored(self, role):
        """Every role should be able to transfer to temp_stored without approval."""
        result = self.service.check_permission(role, "temp_stored")
        assert result.allowed is True
        assert result.requires_approval is False
