"""Add ai_access_logs table for skill invocation and data access audit trail

Revision ID: 036_add_ai_access_logs
Revises: 035_add_ai_skill_role_permission
Create Date: 2026-03-18 14:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

# revision identifiers, used by Alembic.
revision = '036_add_ai_access_logs'
down_revision = '035_add_ai_skill_role_permission'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_access_logs table."""
    op.create_table(
        'ai_access_logs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('user_role', sa.String(50), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(200), nullable=True),
        sa.Column('resource_name', sa.String(255), nullable=True),
        sa.Column('api_key_id', sa.String(100), nullable=True),
        sa.Column('request_type', sa.String(50), nullable=True),
        sa.Column('success', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('details', JSONB, nullable=False, server_default='{}'),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index('idx_access_log_tenant_time', 'ai_access_logs', ['tenant_id', 'created_at'])
    op.create_index('idx_access_log_event_type', 'ai_access_logs', ['event_type'])
    op.create_index('idx_access_log_user', 'ai_access_logs', ['user_id'])
    op.create_index('idx_access_log_created_at', 'ai_access_logs', ['created_at'])


def downgrade() -> None:
    """Drop ai_access_logs table."""
    op.drop_index('idx_access_log_created_at', table_name='ai_access_logs')
    op.drop_index('idx_access_log_user', table_name='ai_access_logs')
    op.drop_index('idx_access_log_event_type', table_name='ai_access_logs')
    op.drop_index('idx_access_log_tenant_time', table_name='ai_access_logs')
    op.drop_table('ai_access_logs')
