"""Add ai_workflows table for workflow-driven AI assistant

Revision ID: 037_add_ai_workflows
Revises: 036_add_ai_access_logs
Create Date: 2026-03-20 10:00:00.000000

NOTE: Due to Alembic multi-head issues (009, 011, 033, 036),
prefer running scripts/migrate_add_ai_workflows.py directly.
This file is kept for documentation and reference.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

# revision identifiers, used by Alembic.
revision = '037_add_ai_workflows'
down_revision = '036_add_ai_access_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_workflows table."""
    op.create_table(
        'ai_workflows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='enabled'),
        sa.Column('is_preset', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('skill_ids', JSONB, nullable=False, server_default='[]'),
        sa.Column('data_source_auth', JSONB, nullable=False, server_default='[]'),
        sa.Column('output_modes', JSONB, nullable=False, server_default='[]'),
        sa.Column('visible_roles', JSONB, nullable=False, server_default='[]'),
        sa.Column('preset_prompt', sa.Text, nullable=True),
        sa.Column('name_en', sa.String(255), nullable=True),
        sa.Column('description_en', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.String(100), nullable=True),
    )

    op.create_index('idx_workflow_status', 'ai_workflows', ['status'])
    op.create_index('idx_workflow_name', 'ai_workflows', ['name'])


def downgrade() -> None:
    """Drop ai_workflows table."""
    op.drop_index('idx_workflow_name', table_name='ai_workflows')
    op.drop_index('idx_workflow_status', table_name='ai_workflows')
    op.drop_table('ai_workflows')
