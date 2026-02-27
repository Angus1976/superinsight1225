"""Add vector_records and semantic_records tables with pgvector extension

Revision ID: 025_add_vector_semantic
Revises: 024_add_datalake_metrics
Create Date: 2026-02-04

This migration:
- Enables the pgvector extension for vector similarity search (if available)
- Creates vector_records table for storing text chunk embeddings
- Creates semantic_records table for storing LLM-extracted entities/relationships/summaries

Note: If pgvector is not installed, embedding column uses JSONB as fallback.
Migration 027 will convert JSONB→vector(1536) once pgvector is available.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = "025_add_vector_semantic"
down_revision: Union[str, Sequence[str], None] = "024_add_datalake_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pgvector_available(connection) -> bool:
    """Check if pgvector extension is available on this PostgreSQL instance."""
    result = connection.execute(
        text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    )
    return result.fetchone() is not None


def upgrade() -> None:
    """Enable pgvector (if available) and create vector/semantic tables."""
    connection = op.get_bind()
    has_pgvector = _pgvector_available(connection)

    if has_pgvector:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create vector_records table
    columns = [
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("structuring_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]

    if has_pgvector:
        from pgvector.sqlalchemy import Vector
        columns.insert(4, sa.Column("embedding", Vector(1536), nullable=False))
    else:
        # Fallback: store as JSONB until pgvector is installed
        columns.insert(4, sa.Column("embedding", JSONB, nullable=False))

    op.create_table("vector_records", *columns)
    op.create_index("idx_vector_records_job_id", "vector_records", ["job_id"])

    # Create semantic_records table
    op.create_table(
        "semantic_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("structuring_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("record_type", sa.String(20), nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_semantic_records_job_id", "semantic_records", ["job_id"])


def downgrade() -> None:
    """Drop vector/semantic tables and pgvector extension."""
    op.drop_index("idx_semantic_records_job_id", table_name="semantic_records")
    op.drop_table("semantic_records")

    op.drop_index("idx_vector_records_job_id", table_name="vector_records")
    op.drop_table("vector_records")

    op.execute("DROP EXTENSION IF EXISTS vector")
