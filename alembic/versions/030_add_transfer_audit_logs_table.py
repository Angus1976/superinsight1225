"""Add transfer_audit_logs table for data transfer operations

Revision ID: 030_add_transfer_audit_logs_table
Revises: 029_add_approval_requests_table
Create Date: 2026-03-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '030_add_transfer_audit_logs_table'
down_revision = '029_add_approval_requests_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create transfer_audit_logs table for tracking all transfer operations"""
    
    # Create transfer_audit_logs table
    op.create_table(
        'transfer_audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('user_role', sa.String(20), nullable=False),
        sa.Column('operation', sa.String(50), nullable=False),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('source_id', sa.String(36), nullable=False),
        sa.Column('target_state', sa.String(30), nullable=False),
        sa.Column('record_count', sa.Integer, nullable=False),
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_transfer_audit_user', 'transfer_audit_logs', ['user_id'])
    op.create_index('idx_transfer_audit_source', 'transfer_audit_logs', ['source_type', 'source_id'])
    op.create_index('idx_transfer_audit_created_at', 'transfer_audit_logs', ['created_at'])


def downgrade() -> None:
    """Drop transfer_audit_logs table"""
    
    # Drop indexes
    op.drop_index('idx_transfer_audit_created_at', 'transfer_audit_logs')
    op.drop_index('idx_transfer_audit_source', 'transfer_audit_logs')
    op.drop_index('idx_transfer_audit_user', 'transfer_audit_logs')
    
    # Drop table
    op.drop_table('transfer_audit_logs')
