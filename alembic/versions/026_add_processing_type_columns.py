"""Add processing_type and chunk_count columns to structuring_jobs

Revision ID: 026_add_processing_type
Revises: 025_add_vector_semantic
Create Date: 2026-02-27

Adds processing_type (structuring/vectorization/semantic) and chunk_count
to structuring_jobs table for multi-pipeline support.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "026_add_processing_type"
down_revision: Union[str, Sequence[str], None] = "025_add_vector_semantic"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add processing_type and chunk_count to structuring_jobs."""
    op.add_column(
        "structuring_jobs",
        sa.Column(
            "processing_type",
            sa.String(20),
            nullable=False,
            server_default="structuring",
        ),
    )
    op.add_column(
        "structuring_jobs",
        sa.Column("chunk_count", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    """Remove processing_type and chunk_count from structuring_jobs."""
    op.drop_column("structuring_jobs", "chunk_count")
    op.drop_column("structuring_jobs", "processing_type")
