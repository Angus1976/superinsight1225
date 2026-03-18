"""
AI Skill Role Permission Service.

Manages role-based access permissions for OpenClaw skills.
Admin role has all skills allowed by default (configurable via frontend).
"""

import logging
from typing import List

from sqlalchemy.orm import Session

from src.models.ai_skill_role_permission import AISkillRolePermission
from src.models.ai_integration import AISkill

logger = logging.getLogger(__name__)

# Admin role gets all skills by default
ADMIN_ROLE = "admin"


class SkillPermissionService:
    """Manages role-based skill access permissions."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_permissions(self) -> list:
        """Return all role-skill permission mappings."""
        rows = self.db.query(AISkillRolePermission).all()
        return [
            {
                "role": row.role,
                "skill_id": row.skill_id,
                "allowed": row.allowed,
            }
            for row in rows
        ]

    def get_allowed_skill_ids(self, role: str) -> List[str]:
        """Return list of skill_ids that the given role can access.

        Admin role: if no explicit permissions exist, returns ALL deployed
        skill IDs (default full access). If explicit permissions exist,
        respects them (allows frontend override).
        """
        rows = (
            self.db.query(AISkillRolePermission)
            .filter(
                AISkillRolePermission.role == role,
            )
            .all()
        )

        # Admin with no explicit config → all deployed skills
        if role == ADMIN_ROLE and not rows:
            return self._all_deployed_skill_ids()

        return [row.skill_id for row in rows if row.allowed]

    def check_skill_allowed(self, role: str, skill_id: str) -> bool:
        """Check if a role is allowed to use a specific skill."""
        row = (
            self.db.query(AISkillRolePermission)
            .filter(
                AISkillRolePermission.role == role,
                AISkillRolePermission.skill_id == skill_id,
            )
            .first()
        )

        # Admin with no explicit config → allowed
        if role == ADMIN_ROLE and row is None:
            return True

        return row.allowed if row else False

    def update_permissions(self, permissions: list) -> None:
        """Batch upsert role-skill permission mappings.

        Each dict: {role, skill_id, allowed}.
        """
        for item in permissions:
            role = item.get("role")
            skill_id = item.get("skill_id")
            allowed = item.get("allowed", False)

            if not role or not skill_id:
                continue

            existing = (
                self.db.query(AISkillRolePermission)
                .filter(
                    AISkillRolePermission.role == role,
                    AISkillRolePermission.skill_id == skill_id,
                )
                .first()
            )

            if existing:
                existing.allowed = allowed
            else:
                self.db.add(
                    AISkillRolePermission(
                        role=role,
                        skill_id=skill_id,
                        allowed=allowed,
                    )
                )

        self.db.commit()

    def init_admin_all_skills(self) -> int:
        """Initialize admin role with all deployed skills allowed.

        Idempotent: skips skills that already have a permission row.
        Returns count of newly added permissions.
        """
        deployed_ids = self._all_deployed_skill_ids()
        added = 0

        for skill_id in deployed_ids:
            exists = (
                self.db.query(AISkillRolePermission)
                .filter(
                    AISkillRolePermission.role == ADMIN_ROLE,
                    AISkillRolePermission.skill_id == skill_id,
                )
                .first()
            )
            if not exists:
                self.db.add(
                    AISkillRolePermission(
                        role=ADMIN_ROLE,
                        skill_id=skill_id,
                        allowed=True,
                    )
                )
                added += 1

        if added:
            self.db.commit()
        return added

    def _all_deployed_skill_ids(self) -> List[str]:
        """Return IDs of all deployed (non-removed) skills."""
        skills = (
            self.db.query(AISkill.id)
            .filter(AISkill.status != "removed")
            .all()
        )
        return [s.id for s in skills]
