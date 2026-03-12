"""Add ai_data_source_role_permission table for role-based data source access control

Revision ID: 031_add_ai_data_source_role_permission
Revises: 030_add_transfer_audit_logs_table
Create Date: 2026-03-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '031_add_ai_data_source_role_permission'
down_revision = '030_add_transfer_audit_logs_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_data_source_role_permission table."""
    op.create_table(
        'ai_data_source_role_permission',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(100), nullable=False),
        sa.Column('allowed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('role', 'source_id', name='uq_role_source'),
    )

    # Indexes for efficient querying by role or source_id
    op.create_index('idx_role_permission_role', 'ai_data_source_role_permission', ['role'])
    op.create_index('idx_role_permission_source_id', 'ai_data_source_role_permission', ['source_id'])


def downgrade() -> None:
    """Drop ai_data_source_role_permission table."""
    op.drop_index('idx_role_permission_source_id', 'ai_data_source_role_permission')
    op.drop_index('idx_role_permission_role', 'ai_data_source_role_permission')
    op.drop_table('ai_data_source_role_permission')
