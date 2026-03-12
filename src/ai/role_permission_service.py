"""
AI Data Source Role Permission Service.

Manages role-based access permissions for AI assistant data sources.
Provides CRUD operations for role-permission mappings.
"""

import logging
from sqlalchemy.orm import Session

from src.models.ai_data_source_role_permission import AIDataSourceRolePermission

logger = logging.getLogger(__name__)


class RolePermissionService:
    """Manages role-based data source access permissions."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_permissions(self) -> list[dict]:
        """Return all role-permission mappings."""
        rows = self.db.query(AIDataSourceRolePermission).all()
        return [
            {
                "role": row.role,
                "source_id": row.source_id,
                "allowed": row.allowed,
            }
            for row in rows
        ]

    def get_permissions_by_role(self, role: str) -> list[str]:
        """Return list of source_ids that the given role can access."""
        rows = (
            self.db.query(AIDataSourceRolePermission)
            .filter(
                AIDataSourceRolePermission.role == role,
                AIDataSourceRolePermission.allowed.is_(True),
            )
            .all()
        )
        return [row.source_id for row in rows]

    def update_permissions(self, permissions: list[dict]) -> None:
        """
        Batch upsert role-permission mappings.

        Each dict in permissions should have: role, source_id, allowed.
        Uses upsert logic: update existing row if (role, source_id) exists,
        otherwise insert a new row.
        """
        for item in permissions:
            role = item.get("role")
            source_id = item.get("source_id")
            allowed = item.get("allowed", False)

            if not role or not source_id:
                continue

            existing = (
                self.db.query(AIDataSourceRolePermission)
                .filter(
                    AIDataSourceRolePermission.role == role,
                    AIDataSourceRolePermission.source_id == source_id,
                )
                .first()
            )

            if existing:
                existing.allowed = allowed
            else:
                self.db.add(
                    AIDataSourceRolePermission(
                        role=role,
                        source_id=source_id,
                        allowed=allowed,
                    )
                )

        self.db.commit()
