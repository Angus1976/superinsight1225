"""Add ai_skill_role_permission table for role-based skill access control

Revision ID: 035_add_ai_skill_role_permission
Revises: 034_add_ai_data_source_config
Create Date: 2026-03-18 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '035_add_ai_skill_role_permission'
down_revision = '034_add_ai_data_source_config'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_skill_role_permission table."""
    op.create_table(
        'ai_skill_role_permission',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('skill_id', sa.String(100), nullable=False),
        sa.Column('allowed', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('role', 'skill_id', name='uq_role_skill'),
    )

    op.create_index('idx_skill_perm_role', 'ai_skill_role_permission', ['role'])
    op.create_index('idx_skill_perm_skill_id', 'ai_skill_role_permission', ['skill_id'])


def downgrade() -> None:
    """Drop ai_skill_role_permission table."""
    op.drop_index('idx_skill_perm_skill_id', table_name='ai_skill_role_permission')
    op.drop_index('idx_skill_perm_role', table_name='ai_skill_role_permission')
    op.drop_table('ai_skill_role_permission')
