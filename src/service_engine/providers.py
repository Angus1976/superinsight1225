"""
DataProvider 注册表 — 每种 data_type 对应一个 Provider 实现。

复用 external_data_router.py 中的 filter_fields / apply_sorting / paginate_query
辅助函数，保持查询逻辑一致。
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select

from src.database.connection import db_manager
from src.models.ai_annotation import AILearningJobModel
from src.models.data_lifecycle import (
    AnnotationTaskModel,
    EnhancedDataModel,
)
from src.models.quality import QualityCheckResultModel
from src.sync.gateway.external_data_router import (
    apply_sorting,
    filter_fields,
    paginate_query,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 公共数据结构
# ---------------------------------------------------------------------------

VALID_DATA_TYPES = (
    "annotations",
    "augmented_data",
    "quality_reports",
    "experiments",
    "data_lifecycle",
    "data_sync",
    "samples",
    "tasks",
)


@dataclass
class QueryParams:
    """Provider 查询参数。"""

    tenant_id: str
    page: int = 1
    page_size: int = 50
    sort_by: Optional[str] = None
    fields: Optional[str] = None
    filters: Optional[dict] = field(default=None)


@dataclass
class PaginatedResult:
    """分页查询结果。"""

    items: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------


class BaseDataProvider(ABC):
    """所有 data_type Provider 的抽象接口。"""

    @abstractmethod
    async def query(self, params: QueryParams) -> PaginatedResult:
        """按 params 查询并返回分页结果。"""


# ---------------------------------------------------------------------------
# 辅助：将 paginate_query 的 PaginationMeta 转为 PaginatedResult
# ---------------------------------------------------------------------------


def _to_paginated_result(
    raw_items: list[dict],
    meta: Any,
    page: int,
    page_size: int,
) -> PaginatedResult:
    return PaginatedResult(
        items=raw_items,
        total=meta.total,
        page=page,
        page_size=page_size,
        total_pages=meta.total_pages,
    )


# ---------------------------------------------------------------------------
# 具体 Provider — annotations
# ---------------------------------------------------------------------------


class AnnotationsProvider(BaseDataProvider):
    """标注结果查询，复用 AnnotationTaskModel。"""

    async def query(self, params: QueryParams) -> PaginatedResult:
        with db_manager.get_session() as session:
            stmt = select(AnnotationTaskModel).where(
                AnnotationTaskModel.created_by == params.tenant_id,
            )
            stmt = apply_sorting(stmt, AnnotationTaskModel, params.sort_by)
            items, meta = paginate_query(
                stmt, params.page, params.page_size, session,
            )
            result_items = [
                filter_fields(self._to_dict(item), params.fields)
                for item in items
            ]
            return _to_paginated_result(
                result_items, meta, params.page, params.page_size,
            )

    @staticmethod
    def _to_dict(item: AnnotationTaskModel) -> dict:
        return {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "annotation_type": item.annotation_type.value,
            "status": item.status.value,
            "created_by": item.created_by,
            "created_at": item.created_at.isoformat(),
            "progress_total": item.progress_total,
            "progress_completed": item.progress_completed,
            "annotations": item.annotations,
            "metadata": item.metadata_,
        }


# ---------------------------------------------------------------------------
# 具体 Provider — augmented_data
# ---------------------------------------------------------------------------


class AugmentedDataProvider(BaseDataProvider):
    """增强数据查询，复用 EnhancedDataModel。"""

    async def query(self, params: QueryParams) -> PaginatedResult:
        with db_manager.get_session() as session:
            stmt = select(EnhancedDataModel)
            stmt = apply_sorting(stmt, EnhancedDataModel, params.sort_by)
            items, meta = paginate_query(
                stmt, params.page, params.page_size, session,
            )
            result_items = [
                filter_fields(self._to_dict(item), params.fields)
                for item in items
            ]
            return _to_paginated_result(
                result_items, meta, params.page, params.page_size,
            )

    @staticmethod
    def _to_dict(item: EnhancedDataModel) -> dict:
        return {
            "id": str(item.id),
            "original_data_id": item.original_data_id,
            "enhancement_job_id": str(item.enhancement_job_id),
            "content": item.content,
            "enhancement_type": item.enhancement_type.value,
            "quality_improvement": item.quality_improvement,
            "quality_overall": item.quality_overall,
            "quality_completeness": item.quality_completeness,
            "quality_accuracy": item.quality_accuracy,
            "quality_consistency": item.quality_consistency,
            "version": item.version,
            "parameters": item.parameters,
            "metadata": item.metadata_,
            "created_at": item.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# 具体 Provider — quality_reports
# ---------------------------------------------------------------------------


class QualityReportsProvider(BaseDataProvider):
    """质量报告查询，复用 QualityCheckResultModel。"""

    async def query(self, params: QueryParams) -> PaginatedResult:
        with db_manager.get_session() as session:
            stmt = select(QualityCheckResultModel).where(
                QualityCheckResultModel.project_id == UUID(params.tenant_id),
            )
            stmt = apply_sorting(
                stmt, QualityCheckResultModel, params.sort_by,
            )
            items, meta = paginate_query(
                stmt, params.page, params.page_size, session,
            )
            result_items = [
                filter_fields(self._to_dict(item), params.fields)
                for item in items
            ]
            return _to_paginated_result(
                result_items, meta, params.page, params.page_size,
            )

    @staticmethod
    def _to_dict(item: QualityCheckResultModel) -> dict:
        return {
            "id": str(item.id),
            "annotation_id": str(item.annotation_id),
            "project_id": str(item.project_id),
            "passed": item.passed,
            "issues": item.issues,
            "checked_rules": item.checked_rules,
            "check_type": item.check_type,
            "checked_at": item.checked_at.isoformat(),
            "checked_by": (
                str(item.checked_by) if item.checked_by else None
            ),
        }


# ---------------------------------------------------------------------------
# 具体 Provider — experiments
# ---------------------------------------------------------------------------


class ExperimentsProvider(BaseDataProvider):
    """AI 试验结果查询，复用 AILearningJobModel。"""

    async def query(self, params: QueryParams) -> PaginatedResult:
        with db_manager.get_session() as session:
            stmt = select(AILearningJobModel).where(
                AILearningJobModel.project_id == params.tenant_id,
            )
            stmt = apply_sorting(
                stmt, AILearningJobModel, params.sort_by,
            )
            items, meta = paginate_query(
                stmt, params.page, params.page_size, session,
            )
            result_items = [
                filter_fields(self._to_dict(item), params.fields)
                for item in items
            ]
            return _to_paginated_result(
                result_items, meta, params.page, params.page_size,
            )

    @staticmethod
    def _to_dict(item: AILearningJobModel) -> dict:
        return {
            "id": item.id,
            "project_id": item.project_id,
            "status": item.status,
            "sample_count": item.sample_count,
            "patterns_identified": item.patterns_identified,
            "average_confidence": item.average_confidence,
            "recommended_method": item.recommended_method,
            "progress_percentage": item.progress_percentage,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
            "completed_at": (
                item.completed_at.isoformat() if item.completed_at else None
            ),
            "error_message": item.error_message,
        }


# ---------------------------------------------------------------------------
# Stub Providers — 暂无对应端点的 data_type
# ---------------------------------------------------------------------------


class _StubProvider(BaseDataProvider):
    """返回空结果的占位 Provider。"""

    def __init__(self, data_type: str) -> None:
        self._data_type = data_type

    async def query(self, params: QueryParams) -> PaginatedResult:
        # TODO: 接入真实数据源后替换此 stub 实现
        logger.debug(
            "Stub provider for %s returning empty result", self._data_type,
        )
        return PaginatedResult(
            items=[], total=0, page=params.page,
            page_size=params.page_size, total_pages=0,
        )


class DataLifecycleProvider(_StubProvider):
    """数据流转统计（待实现）。"""

    def __init__(self) -> None:
        super().__init__("data_lifecycle")


class DataSyncProvider(_StubProvider):
    """数据同步状态（待实现）。"""

    def __init__(self) -> None:
        super().__init__("data_sync")


class SamplesProvider(_StubProvider):
    """样本库数据（待实现）。"""

    def __init__(self) -> None:
        super().__init__("samples")


class TasksProvider(_StubProvider):
    """标注任务（待实现）。"""

    def __init__(self) -> None:
        super().__init__("tasks")


# ---------------------------------------------------------------------------
# Provider 注册表
# ---------------------------------------------------------------------------


def get_data_providers() -> dict[str, BaseDataProvider]:
    """返回 data_type → Provider 实例的映射。"""
    return {
        "annotations": AnnotationsProvider(),
        "augmented_data": AugmentedDataProvider(),
        "quality_reports": QualityReportsProvider(),
        "experiments": ExperimentsProvider(),
        "data_lifecycle": DataLifecycleProvider(),
        "data_sync": DataSyncProvider(),
        "samples": SamplesProvider(),
        "tasks": TasksProvider(),
    }
