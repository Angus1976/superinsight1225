"""Add datalake_metrics table

Revision ID: 024_add_datalake_metrics
Revises: 023_merge_structuring_head
Create Date: 2026-02-04

This migration adds the datalake_metrics table for storing health, volume,
and query performance metrics for datalake/warehouse data sources.
Cascade delete ensures metrics are removed when a data source is deleted.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = "024_add_datalake_metrics"
down_revision: Union[str, Sequence[str], None] = "023_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create datalake_metrics table."""

    op.create_table(
        "datalake_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            sa.ForeignKey("data_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("metric_type", sa.String(50), nullable=False),
        sa.Column("metric_data", JSONB, nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Single-column indexes
    op.create_index(
        "ix_datalake_metrics_tenant_id",
        "datalake_metrics",
        ["tenant_id"],
    )
    op.create_index(
        "ix_datalake_metrics_recorded_at",
        "datalake_metrics",
        ["recorded_at"],
    )

    # Composite indexes
    op.create_index(
        "idx_datalake_metrics_tenant_type",
        "datalake_metrics",
        ["tenant_id", "metric_type"],
    )
    op.create_index(
        "idx_datalake_metrics_source_recorded",
        "datalake_metrics",
        ["source_id", "recorded_at"],
    )


def downgrade() -> None:
    """Drop datalake_metrics table."""

    op.drop_index("idx_datalake_metrics_source_recorded", table_name="datalake_metrics")
    op.drop_index("idx_datalake_metrics_tenant_type", table_name="datalake_metrics")
    op.drop_index("ix_datalake_metrics_recorded_at", table_name="datalake_metrics")
    op.drop_index("ix_datalake_metrics_tenant_id", table_name="datalake_metrics")
    op.drop_table("datalake_metrics")
