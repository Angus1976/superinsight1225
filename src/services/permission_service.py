"""
Permission Service for Data Transfer Integration.

Implements role-based permission control for data transfer operations.
Permission matrices are loaded from src.config.permission_defaults, which
supports environment variable and JSON config file overrides.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel

from src.config.permission_defaults import get_permission_settings


class UserRole(str, Enum):
    """User roles for data transfer operations."""
    ADMIN = "admin"
    DATA_MANAGER = "data_manager"
    DATA_ANALYST = "data_analyst"
    USER = "user"


class PermissionResult(BaseModel):
    """Permission check result."""
    allowed: bool
    requires_approval: bool
    current_role: UserRole
    required_role: Optional[UserRole] = None
    reason: Optional[str] = None


class PermissionService:
    """
    Permission service for data transfer operations.

    Implements role-based access control with approval requirements.
    Permission matrices are loaded from configuration (see
    src.config.permission_defaults) so they can be customised per
    deployment without code changes.
    """

    def __init__(self) -> None:
        settings = get_permission_settings()
        self._batch_threshold = settings.batch_threshold

        # Build UserRole-keyed matrices from the string-keyed config
        self.PERMISSION_MATRIX = {
            UserRole(role): ops
            for role, ops in settings.transfer_matrix.items()
        }
        self.CRUD_PERMISSION_MATRIX = {
            UserRole(role): ops
            for role, ops in settings.crud_matrix.items()
        }

    def check_permission(
        self,
        user_role: UserRole,
        target_state: str,
        record_count: int = 1,
        is_cross_project: bool = False
    ) -> PermissionResult:
        """
        Check user permission for data transfer operation.

        Args:
            user_role: User's role
            target_state: Target state for data transfer
            record_count: Number of records to transfer
            is_cross_project: Whether this is a cross-project transfer

        Returns:
            PermissionResult with permission details
        """
        # Determine operation type
        if record_count > self._batch_threshold:
            operation = "batch_transfer"
        elif is_cross_project:
            operation = "cross_project"
        else:
            operation = target_state

        # Get permission from matrix
        permission = self.PERMISSION_MATRIX.get(user_role, {}).get(operation)

        if not permission:
            return PermissionResult(
                allowed=False,
                requires_approval=False,
                current_role=user_role,
                reason="Operation not defined for this role"
            )

        return PermissionResult(
            allowed=permission["allowed"],
            requires_approval=permission["requires_approval"],
            current_role=user_role
        )

    def check_crud_permission(
        self,
        user_role: UserRole,
        operation: str
    ) -> PermissionResult:
        """
        Check user permission for CRUD operations.

        Args:
            user_role: User's role
            operation: CRUD operation (create, read, update, delete, merge, split)

        Returns:
            PermissionResult with permission details
        """
        permission = self.CRUD_PERMISSION_MATRIX.get(user_role, {}).get(operation)

        if not permission:
            return PermissionResult(
                allowed=False,
                requires_approval=False,
                current_role=user_role,
                reason="Operation not defined for this role"
            )

        return PermissionResult(
            allowed=permission["allowed"],
            requires_approval=permission["requires_approval"],
            current_role=user_role
        )

