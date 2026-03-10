"""
Integration tests for permission matrix - all role and operation combinations.

Covers PERMISSION_MATRIX (transfer operations) and CRUD_PERMISSION_MATRIX
with parametrized tests for every role × operation combination.
"""

import pytest
from src.services.permission_service import (
    PermissionService,
    UserRole,
    PermissionResult,
)


ALL_ROLES = [UserRole.ADMIN, UserRole.DATA_MANAGER, UserRole.DATA_ANALYST, UserRole.USER]

TRANSFER_OPERATIONS = [
    "temp_stored",
    "in_sample_library",
    "annotation_pending",
    "batch_transfer",
    "cross_project",
]

CRUD_OPERATIONS = ["create", "read", "update", "delete", "merge", "split"]


# =========================================================================
# Expected permission data — mirrors the two matrices in PermissionService
# =========================================================================

# (role, operation) -> (allowed, requires_approval)
EXPECTED_TRANSFER = {
    (UserRole.ADMIN, "temp_stored"): (True, False),
    (UserRole.ADMIN, "in_sample_library"): (True, False),
    (UserRole.ADMIN, "annotation_pending"): (True, False),
    (UserRole.ADMIN, "batch_transfer"): (True, False),
    (UserRole.ADMIN, "cross_project"): (True, False),
    (UserRole.DATA_MANAGER, "temp_stored"): (True, False),
    (UserRole.DATA_MANAGER, "in_sample_library"): (True, False),
    (UserRole.DATA_MANAGER, "annotation_pending"): (True, False),
    (UserRole.DATA_MANAGER, "batch_transfer"): (True, False),
    (UserRole.DATA_MANAGER, "cross_project"): (False, False),
    (UserRole.DATA_ANALYST, "temp_stored"): (True, False),
    (UserRole.DATA_ANALYST, "in_sample_library"): (True, True),
    (UserRole.DATA_ANALYST, "annotation_pending"): (True, True),
    (UserRole.DATA_ANALYST, "batch_transfer"): (False, False),
    (UserRole.DATA_ANALYST, "cross_project"): (False, False),
    (UserRole.USER, "temp_stored"): (True, False),
    (UserRole.USER, "in_sample_library"): (True, True),
    (UserRole.USER, "annotation_pending"): (True, True),
    (UserRole.USER, "batch_transfer"): (False, False),
    (UserRole.USER, "cross_project"): (False, False),
}

EXPECTED_CRUD = {
    (UserRole.ADMIN, "create"): (True, False),
    (UserRole.ADMIN, "read"): (True, False),
    (UserRole.ADMIN, "update"): (True, False),
    (UserRole.ADMIN, "delete"): (True, False),
    (UserRole.ADMIN, "merge"): (True, False),
    (UserRole.ADMIN, "split"): (True, False),
    (UserRole.DATA_MANAGER, "create"): (True, False),
    (UserRole.DATA_MANAGER, "read"): (True, False),
    (UserRole.DATA_MANAGER, "update"): (True, False),
    (UserRole.DATA_MANAGER, "delete"): (True, True),
    (UserRole.DATA_MANAGER, "merge"): (True, False),
    (UserRole.DATA_MANAGER, "split"): (True, False),
    (UserRole.DATA_ANALYST, "create"): (True, False),
    (UserRole.DATA_ANALYST, "read"): (True, False),
    (UserRole.DATA_ANALYST, "update"): (True, True),
    (UserRole.DATA_ANALYST, "delete"): (False, False),
    (UserRole.DATA_ANALYST, "merge"): (False, False),
    (UserRole.DATA_ANALYST, "split"): (False, False),
    (UserRole.USER, "create"): (True, True),
    (UserRole.USER, "read"): (True, False),
    (UserRole.USER, "update"): (False, False),
    (UserRole.USER, "delete"): (False, False),
    (UserRole.USER, "merge"): (False, False),
    (UserRole.USER, "split"): (False, False),
}


# =========================================================================
# Helper to build parametrize ids
# =========================================================================

def _id(role: UserRole, op: str) -> str:
    return f"{role.value}-{op}"


# =========================================================================
# Transfer permission matrix — 4 roles × 5 operations = 20 combinations
# =========================================================================

class TestTransferPermissionMatrix:
    """Parametrized tests covering every role × transfer operation."""

    def setup_method(self):
        self.service = PermissionService()

    @pytest.mark.parametrize(
        "role, operation",
        [
            (role, op)
            for role in ALL_ROLES
            for op in TRANSFER_OPERATIONS
        ],
        ids=[
            _id(role, op)
            for role in ALL_ROLES
            for op in TRANSFER_OPERATIONS
        ],
    )
    def test_transfer_permission_matrix(self, role, operation):
        """Verify allowed and requires_approval for every role × transfer op."""
        expected_allowed, expected_approval = EXPECTED_TRANSFER[(role, operation)]

        # batch_transfer and cross_project are triggered via flags, not target_state
        if operation == "batch_transfer":
            result = self.service.check_permission(
                role, "temp_stored", record_count=2000
            )
        elif operation == "cross_project":
            result = self.service.check_permission(
                role, "temp_stored", is_cross_project=True
            )
        else:
            result = self.service.check_permission(role, operation)

        assert result.allowed is expected_allowed, (
            f"{role.value} + {operation}: expected allowed={expected_allowed}, "
            f"got {result.allowed}"
        )
        assert result.requires_approval is expected_approval, (
            f"{role.value} + {operation}: expected requires_approval={expected_approval}, "
            f"got {result.requires_approval}"
        )
        assert result.current_role == role


# =========================================================================
# CRUD permission matrix — 4 roles × 6 operations = 24 combinations
# =========================================================================

class TestCrudPermissionMatrix:
    """Parametrized tests covering every role × CRUD operation."""

    def setup_method(self):
        self.service = PermissionService()

    @pytest.mark.parametrize(
        "role, operation",
        [
            (role, op)
            for role in ALL_ROLES
            for op in CRUD_OPERATIONS
        ],
        ids=[
            _id(role, op)
            for role in ALL_ROLES
            for op in CRUD_OPERATIONS
        ],
    )
    def test_crud_permission_matrix(self, role, operation):
        """Verify allowed and requires_approval for every role × CRUD op."""
        expected_allowed, expected_approval = EXPECTED_CRUD[(role, operation)]

        result = self.service.check_crud_permission(role, operation)

        assert result.allowed is expected_allowed, (
            f"{role.value} + {operation}: expected allowed={expected_allowed}, "
            f"got {result.allowed}"
        )
        assert result.requires_approval is expected_approval, (
            f"{role.value} + {operation}: expected requires_approval={expected_approval}, "
            f"got {result.requires_approval}"
        )
        assert result.current_role == role


# =========================================================================
# Edge cases: undefined operations and invalid roles
# =========================================================================

class TestPermissionMatrixEdgeCases:
    """Edge cases for permission checks."""

    def setup_method(self):
        self.service = PermissionService()

    # --- Undefined transfer operations ---

    @pytest.mark.parametrize("role", ALL_ROLES, ids=[r.value for r in ALL_ROLES])
    def test_undefined_transfer_operation_denied(self, role):
        """Undefined target_state should be denied for all roles."""
        result = self.service.check_permission(role, "nonexistent_state")
        assert result.allowed is False
        assert result.requires_approval is False
        assert result.reason is not None

    # --- Undefined CRUD operations ---

    @pytest.mark.parametrize("role", ALL_ROLES, ids=[r.value for r in ALL_ROLES])
    def test_undefined_crud_operation_denied(self, role):
        """Undefined CRUD operation should be denied for all roles."""
        result = self.service.check_crud_permission(role, "nonexistent_op")
        assert result.allowed is False
        assert result.requires_approval is False
        assert result.reason is not None

    # --- PermissionResult always carries current_role ---

    @pytest.mark.parametrize("role", ALL_ROLES, ids=[r.value for r in ALL_ROLES])
    def test_transfer_result_carries_role(self, role):
        """PermissionResult.current_role matches the queried role."""
        result = self.service.check_permission(role, "temp_stored")
        assert result.current_role == role

    @pytest.mark.parametrize("role", ALL_ROLES, ids=[r.value for r in ALL_ROLES])
    def test_crud_result_carries_role(self, role):
        """PermissionResult.current_role matches the queried role."""
        result = self.service.check_crud_permission(role, "read")
        assert result.current_role == role

    # --- Batch threshold boundary ---

    def test_batch_threshold_1000_not_triggered(self):
        """Exactly 1000 records should NOT trigger batch_transfer check."""
        result = self.service.check_permission(
            UserRole.DATA_ANALYST, "temp_stored", record_count=1000
        )
        assert result.allowed is True

    def test_batch_threshold_1001_triggers(self):
        """1001 records should trigger batch_transfer check."""
        result = self.service.check_permission(
            UserRole.DATA_ANALYST, "temp_stored", record_count=1001
        )
        assert result.allowed is False

    # --- Cross-project takes precedence over target_state ---

    def test_cross_project_precedence(self):
        """Cross-project flag overrides target_state for permission lookup."""
        result = self.service.check_permission(
            UserRole.DATA_MANAGER, "temp_stored", is_cross_project=True
        )
        # DATA_MANAGER cannot do cross_project
        assert result.allowed is False
