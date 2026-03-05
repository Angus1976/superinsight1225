"""add progress_info to structuring_jobs

Revision ID: 011_add_progress_info
Revises: merge_2026_01_16
Create Date: 2026-03-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_add_progress_info'
down_revision = 'merge_2026_01_16'
branch_labels = None
depends_on = None


def upgrade():
    """Add progress_info JSONB column to structuring_jobs table."""
    op.add_column(
        'structuring_jobs',
        sa.Column('progress_info', postgresql.JSONB(), nullable=True)
    )


def downgrade():
    """Remove progress_info column from structuring_jobs table."""
    op.drop_column('structuring_jobs', 'progress_info')
