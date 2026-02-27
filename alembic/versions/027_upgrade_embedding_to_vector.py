"""Upgrade vector_records.embedding from JSONB to vector(1536)

Revision ID: 027_upgrade_embedding
Revises: 026_add_processing_type
Create Date: 2026-02-27

Converts the embedding column from JSONB fallback to native pgvector type.
Only runs if pgvector extension is available; otherwise skips gracefully.
"""

from typing import Sequence, Union
from alembic import op
from sqlalchemy import text


revision: str = "027_upgrade_embedding"
down_revision: Union[str, Sequence[str], None] = "026_add_processing_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pgvector_available(connection) -> bool:
    result = connection.execute(
        text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    )
    return result.fetchone() is not None


def _embedding_is_jsonb(connection) -> bool:
    result = connection.execute(text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = 'vector_records' AND column_name = 'embedding'"
    ))
    row = result.fetchone()
    return row is not None and row[0] == "jsonb"


def upgrade() -> None:
    """Convert embedding JSONB → vector(1536) if pgvector is available."""
    connection = op.get_bind()

    if not _pgvector_available(connection):
        print("  [027] pgvector not available, skipping embedding upgrade.")
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if not _embedding_is_jsonb(connection):
        print("  [027] embedding is already vector type, skipping.")
        return

    # Convert JSONB array → vector(1536)
    # First drop existing data if any (JSONB arrays aren't directly castable)
    result = connection.execute(text("SELECT count(*) FROM vector_records"))
    count = result.scalar()

    if count == 0:
        # No data: just alter the column type
        op.execute(
            "ALTER TABLE vector_records "
            "ALTER COLUMN embedding TYPE vector(1536) "
            "USING NULL"
        )
    else:
        # Has data: convert JSONB array to vector via text cast
        op.execute(
            "ALTER TABLE vector_records "
            "ALTER COLUMN embedding TYPE vector(1536) "
            "USING embedding::text::vector(1536)"
        )

    print(f"  [027] Converted embedding column to vector(1536). Rows: {count}")


def downgrade() -> None:
    """Revert vector(1536) → JSONB."""
    connection = op.get_bind()

    result = connection.execute(text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = 'vector_records' AND column_name = 'embedding'"
    ))
    row = result.fetchone()
    if row is None or row[0] == "jsonb":
        return

    op.execute(
        "ALTER TABLE vector_records "
        "ALTER COLUMN embedding TYPE jsonb "
        "USING to_jsonb(embedding::text::float8[])"
    )
