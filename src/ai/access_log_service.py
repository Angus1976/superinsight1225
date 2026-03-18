"""
AI Access Log Service.

Records and queries skill invocations, data access, and permission changes.
All queries ordered by created_at DESC (newest first).
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models.ai_access_log import AIAccessLog

logger = logging.getLogger(__name__)


class AIAccessLogService:
    """Manages AI access log entries."""

    def __init__(self, db: Session):
        self.db = db

    # -- Write ---------------------------------------------------------------

    def log_skill_invoke(
        self,
        tenant_id: str,
        user_id: str,
        user_role: str,
        skill_ids: list,
        *,
        api_key_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Record a skill invocation (or denial)."""
        event_type = "skill_invoke" if success else "skill_denied"
        self.db.add(AIAccessLog(
            tenant_id=tenant_id,
            user_id=user_id,
            user_role=user_role,
            event_type=event_type,
            resource_id=",".join(skill_ids) if skill_ids else None,
            resource_name=f"{len(skill_ids)} skill(s)",
            api_key_id=api_key_id,
            request_type="skill",
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            details=details or {"skill_ids": skill_ids},
        ))
        self.db.commit()

    def log_data_access(
        self,
        tenant_id: str,
        user_id: str,
        user_role: str,
        source_ids: list,
        *,
        output_mode: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Record a data source access from AI assistant."""
        self.db.add(AIAccessLog(
            tenant_id=tenant_id,
            user_id=user_id,
            user_role=user_role,
            event_type="data_access",
            resource_id=",".join(source_ids) if source_ids else None,
            resource_name=f"{len(source_ids)} source(s)",
            request_type="chat",
            success=True,
            duration_ms=duration_ms,
            details={"source_ids": source_ids, "output_mode": output_mode},
        ))
        self.db.commit()

    def log_permission_change(
        self,
        tenant_id: str,
        user_id: str,
        user_role: str,
        target_type: str,
        changes: list,
    ) -> None:
        """Record a permission change (skill or data source).

        target_type: 'skill_permission' or 'datasource_permission'
        """
        self.db.add(AIAccessLog(
            tenant_id=tenant_id,
            user_id=user_id,
            user_role=user_role,
            event_type="permission_change",
            resource_id=target_type,
            resource_name=f"{len(changes)} change(s)",
            request_type=None,
            success=True,
            details={"target_type": target_type, "changes": changes},
        ))
        self.db.commit()

    # -- Read ----------------------------------------------------------------

    def query_logs(
        self,
        tenant_id: str,
        *,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Query access logs, newest first.

        Returns: {items: [...], total: int, page: int, page_size: int}
        """
        q = self.db.query(AIAccessLog).filter(
            AIAccessLog.tenant_id == tenant_id,
        )
        if event_type:
            q = q.filter(AIAccessLog.event_type == event_type)
        if user_id:
            q = q.filter(AIAccessLog.user_id == user_id)

        total = q.count()
        rows = (
            q.order_by(AIAccessLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": [self._to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def _to_dict(row: AIAccessLog) -> dict:
        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "user_id": row.user_id,
            "user_role": row.user_role,
            "event_type": row.event_type,
            "resource_id": row.resource_id,
            "resource_name": row.resource_name,
            "api_key_id": row.api_key_id,
            "request_type": row.request_type,
            "success": row.success,
            "error_message": row.error_message,
            "details": row.details,
            "duration_ms": row.duration_ms,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
