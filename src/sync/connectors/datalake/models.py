"""
SQLAlchemy ORM models for Datalake/Warehouse metrics.

Stores health, volume, and query performance metrics for datalake data sources.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database.connection import Base
from src.database.json_types import get_json_type

# Valid metric types for DatalakeMetricsModel
VALID_METRIC_TYPES = ("health", "volume", "query_perf")


class DatalakeMetricsModel(Base):
    """数据湖/数仓指标记录表"""

    __tablename__ = "datalake_metrics"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # 指标数据
    metric_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # health, volume, query_perf
    metric_data: Mapped[dict] = mapped_column(get_json_type(), nullable=False)

    # 时间戳
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("idx_datalake_metrics_tenant_type", "tenant_id", "metric_type"),
        Index("idx_datalake_metrics_source_recorded", "source_id", "recorded_at"),
    )
