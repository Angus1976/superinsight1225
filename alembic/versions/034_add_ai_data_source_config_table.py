"""Add ai_data_source_config table for admin data source management

Revision ID: 034_add_ai_data_source_config
Revises: 033_add_api_key_and_call_log_tables
Create Date: 2026-03-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '034_add_ai_data_source_config'
down_revision = '031_add_ai_data_source_role_permission'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_data_source_config table."""
    op.create_table(
        'ai_data_source_config',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('label', sa.String, nullable=False),
        sa.Column('description', sa.String, server_default=''),
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('access_mode', sa.String, server_default='read'),
        sa.Column('config', sa.JSON, server_default='{}'),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    """Drop ai_data_source_config table."""
    op.drop_table('ai_data_source_config')
