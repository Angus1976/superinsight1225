"""
AI Assistant Data Source Configuration.

Manages which data sources the AI assistant can access,
and provides data querying capabilities for selected sources.
"""

import logging
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, JSON, func
from sqlalchemy.orm import Session

from src.database.connection import Base

logger = logging.getLogger(__name__)


# --- Database Model ---

class AIDataSourceConfigModel(Base):
    """Admin-configured AI data source access permissions."""
    __tablename__ = "ai_data_source_config"

    id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    description = Column(String, default="")
    enabled = Column(Boolean, default=True)
    access_mode = Column(String, default="read")  # read | read_write
    config = Column(JSON, default=dict)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# --- Predefined Data Source Registry ---

DATA_SOURCE_REGISTRY = [
    {
        "id": "tasks",
        "label": "标注任务",
        "description": "标注任务管理数据（任务列表、状态统计）",
        "category": "core",
        "tables": [
            {"id": "task_list", "label": "任务列表", "fields": ["task_id", "task_name", "project", "assignee", "deadline"]},
            {"id": "task_status", "label": "任务状态", "fields": ["status", "progress", "updated_at"]},
            {"id": "task_stats", "label": "任务统计", "fields": ["total", "completed", "pending", "overdue"]},
        ],
    },
    {
        "id": "annotation_efficiency",
        "label": "标注效率",
        "description": "标注效率趋势数据（完成率、质量分、修订率）",
        "category": "analytics",
        "tables": [
            {"id": "completion_rate", "label": "完成率", "fields": ["daily_rate", "weekly_rate", "trend"]},
            {"id": "quality_score", "label": "质量分", "fields": ["accuracy", "consistency", "avg_score"]},
            {"id": "revision_rate", "label": "修订率", "fields": ["revision_count", "revision_ratio"]},
        ],
    },
    {
        "id": "user_activity",
        "label": "用户活跃度",
        "description": "用户活跃度数据（登录、操作、在线时长）",
        "category": "analytics",
        "tables": [
            {"id": "login_records", "label": "登录记录", "fields": ["user_id", "login_time", "ip_address", "device"]},
            {"id": "operations", "label": "操作记录", "fields": ["action", "target", "timestamp"]},
            {"id": "online_duration", "label": "在线时长", "fields": ["daily_hours", "weekly_hours", "avg_session"]},
        ],
    },
    {
        "id": "data_sync",
        "label": "数据同步",
        "description": "数据同步源和同步任务数据",
        "category": "data",
        "tables": [
            {"id": "sync_sources", "label": "同步源", "fields": ["source_name", "source_type", "connection_status"]},
            {"id": "sync_jobs", "label": "同步任务", "fields": ["job_id", "schedule", "last_run", "status"]},
            {"id": "sync_history", "label": "同步历史", "fields": ["run_id", "records_synced", "errors", "duration"]},
        ],
    },
    {
        "id": "data_lifecycle",
        "label": "数据流转",
        "description": "数据流转模块（临时数据、样本库、标注、增强、AI试验）",
        "category": "data",
        "tables": [
            {"id": "temp_data", "label": "临时数据", "fields": ["file_name", "size", "upload_time", "expiry"]},
            {"id": "samples", "label": "样本库", "fields": ["sample_id", "dataset", "label", "split"]},
            {"id": "annotation", "label": "标注数据", "fields": ["annotation_id", "annotator", "label", "confidence"]},
            {"id": "enhancement", "label": "增强数据", "fields": ["method", "source_count", "output_count"]},
            {"id": "ai_trial", "label": "AI试验", "fields": ["model", "accuracy", "f1_score", "run_date"]},
        ],
    },
    {
        "id": "augmentation",
        "label": "数据增强",
        "description": "数据增强任务和样本数据",
        "category": "data",
        "tables": [
            {"id": "augmentation_tasks", "label": "增强任务", "fields": ["task_id", "method", "status", "created_at"]},
            {"id": "augmentation_samples", "label": "增强样本", "fields": ["sample_id", "original_id", "transform_type"]},
        ],
    },
    {
        "id": "quality",
        "label": "质量报表",
        "description": "数据质量评分和质量报表数据",
        "category": "analytics",
        "tables": [
            {"id": "quality_scores", "label": "质量评分", "fields": ["dataset", "overall_score", "completeness", "accuracy"]},
            {"id": "quality_reports", "label": "质量报表", "fields": ["report_id", "generated_at", "summary", "issues"]},
        ],
    },
]


def get_default_sources() -> list[dict]:
    """Return the predefined data source list."""
    return DATA_SOURCE_REGISTRY


# --- Service Layer ---

class AIDataSourceService:
    """Manages AI data source configuration and data querying."""

    def __init__(self, db: Session):
        self.db = db

    def get_config(self) -> list[dict]:
        """Get all data source configs (merge DB overrides with registry)."""
        registry = {s["id"]: {**s, "enabled": True, "access_mode": "read"}
                    for s in DATA_SOURCE_REGISTRY}

        rows = self.db.query(AIDataSourceConfigModel).all()
        for row in rows:
            if row.id in registry:
                registry[row.id]["enabled"] = row.enabled
                registry[row.id]["access_mode"] = row.access_mode

        return list(registry.values())

    def get_available_sources(self, role: Optional[str] = None) -> list[dict]:
        """Get enabled data sources, optionally filtered by role permissions.

        If role is provided, returns the intersection of enabled sources and
        role-authorized sources. If no permissions are configured for the role
        (empty result), returns all enabled sources as fallback.
        """
        enabled = [s for s in self.get_config() if s.get("enabled")]

        if not role:
            return enabled

        from src.ai.role_permission_service import RolePermissionService
        perm_service = RolePermissionService(self.db)
        allowed_ids = perm_service.get_permissions_by_role(role)

        # Fallback: no permissions configured → return all enabled
        if not allowed_ids:
            return enabled

        return [s for s in enabled if s["id"] in allowed_ids]

    def update_config(self, sources: list[dict]) -> list[dict]:
        """Admin updates data source enable/disable and access mode."""
        for item in sources:
            src_id = item.get("id")
            if not src_id:
                continue
            row = self.db.query(AIDataSourceConfigModel).get(src_id)
            if row:
                row.enabled = item.get("enabled", row.enabled)
                row.access_mode = item.get("access_mode", row.access_mode)
            else:
                row = AIDataSourceConfigModel(
                    id=src_id,
                    label=item.get("label", src_id),
                    enabled=item.get("enabled", True),
                    access_mode=item.get("access_mode", "read"),
                )
                self.db.add(row)

        self.db.commit()
        return self.get_config()


    def query_source_data(self, source_id: str) -> dict:
        """Query summary data from a specific data source for LLM context."""
        handlers = {
            "tasks": self._query_tasks,
            "annotation_efficiency": self._query_annotation_efficiency,
            "user_activity": self._query_user_activity,
            "data_sync": self._query_data_sync,
            "data_lifecycle": self._query_data_lifecycle,
            "augmentation": self._query_augmentation,
            "quality": self._query_quality,
        }
        handler = handlers.get(source_id)
        if not handler:
            return {"error": f"Unknown data source: {source_id}"}
        try:
            return handler()
        except Exception as e:
            logger.error("Failed to query data source %s: %s", source_id, e)
            return {"error": str(e), "source": source_id}

    def _query_tasks(self) -> dict:
        from src.database.models import TaskModel
        from sqlalchemy import func as sqlfunc
        total = self.db.query(sqlfunc.count(TaskModel.id)).scalar() or 0
        by_status = dict(
            self.db.query(TaskModel.status, sqlfunc.count(TaskModel.id))
            .group_by(TaskModel.status).all()
        )
        return {"source": "tasks", "total": total, "by_status": by_status}

    def _query_annotation_efficiency(self) -> dict:
        from src.database.models import TaskModel
        from sqlalchemy import func as sqlfunc
        completed = self.db.query(sqlfunc.count(TaskModel.id)).filter(
            TaskModel.status == "completed"
        ).scalar() or 0
        total = self.db.query(sqlfunc.count(TaskModel.id)).scalar() or 0
        rate = round(completed / total * 100, 1) if total else 0
        return {"source": "annotation_efficiency", "completed": completed,
                "total": total, "completion_rate": rate}

    def _query_user_activity(self) -> dict:
        from src.security.models import UserModel
        from sqlalchemy import func as sqlfunc
        total_users = self.db.query(sqlfunc.count(UserModel.id)).scalar() or 0
        active = self.db.query(sqlfunc.count(UserModel.id)).filter(
            UserModel.is_active.is_(True)
        ).scalar() or 0
        return {"source": "user_activity", "total_users": total_users,
                "active_users": active}

    def _query_data_sync(self) -> dict:
        try:
            from src.sync.models import DataSourceModel, SyncJobModel
            from sqlalchemy import func as sqlfunc
            sources = self.db.query(sqlfunc.count(DataSourceModel.id)).scalar() or 0
            jobs = self.db.query(sqlfunc.count(SyncJobModel.id)).scalar() or 0
            return {"source": "data_sync", "total_sources": sources,
                    "total_jobs": jobs}
        except Exception:
            return {"source": "data_sync", "total_sources": 0, "total_jobs": 0}

    def _query_data_lifecycle(self) -> dict:
        return {"source": "data_lifecycle", "note": "Data lifecycle summary",
                "modules": ["temp_data", "samples", "annotation", "enhancement",
                            "ai_trial"]}

    def _query_augmentation(self) -> dict:
        return {"source": "augmentation", "note": "Augmentation data summary"}

    def _query_quality(self) -> dict:
        try:
            from src.sync.models import DataQualityScoreModel
            from sqlalchemy import func as sqlfunc
            avg_score = self.db.query(
                sqlfunc.avg(DataQualityScoreModel.overall_score)
            ).scalar()
            return {"source": "quality",
                    "average_score": round(float(avg_score), 2) if avg_score else 0}
        except Exception:
            return {"source": "quality", "average_score": 0}
