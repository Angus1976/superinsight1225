"""Add AI data structuring tables

Revision ID: 022_add_structuring
Revises: 021_add_ai_integration
Create Date: 2026-02-04

This migration adds tables for AI Data Structuring system:
- structuring_jobs: Tracks file structuring pipeline lifecycle
- structured_records: Stores extracted structured records per job

Supports multi-tenant isolation with tenant_id indexes.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = '022_add_structuring'
down_revision: Union[str, Sequence[str], None] = '021_add_ai_integration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create structuring tables."""

    # Create structuring_jobs table
    op.create_table(
        'structuring_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('raw_content', sa.Text, nullable=True),
        sa.Column('inferred_schema', JSONB, nullable=True),
        sa.Column('confirmed_schema', JSONB, nullable=True),
        sa.Column('record_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for structuring_jobs
    op.create_index('ix_structuring_jobs_tenant_id', 'structuring_jobs', ['tenant_id'])
    op.create_index(
        'idx_structuring_jobs_tenant_status',
        'structuring_jobs',
        ['tenant_id', 'status'],
    )

    # Create structured_records table
    op.create_table(
        'structured_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'job_id',
            UUID(as_uuid=True),
            sa.ForeignKey('structuring_jobs.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('fields', JSONB, nullable=False, server_default='{}'),
        sa.Column('confidence', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('source_span', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for structured_records
    op.create_index('idx_structured_records_job_id', 'structured_records', ['job_id'])


def downgrade() -> None:
    """Drop structuring tables."""

    # Drop indexes and tables in reverse order
    op.drop_index('idx_structured_records_job_id', table_name='structured_records')
    op.drop_table('structured_records')

    op.drop_index('idx_structuring_jobs_tenant_status', table_name='structuring_jobs')
    op.drop_index('ix_structuring_jobs_tenant_id', table_name='structuring_jobs')
    op.drop_table('structuring_jobs')
