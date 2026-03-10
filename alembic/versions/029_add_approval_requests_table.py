"""Add approval_requests table for data transfer approval workflow

Revision ID: 029_add_approval_requests_table
Revises: 028_add_data_lifecycle_tables
Create Date: 2026-02-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '029_add_approval_requests_table'
down_revision = '028_add_data_lifecycle_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create approval_requests table for data transfer approval workflow"""
    
    # Create approval_requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('transfer_request', postgresql.JSONB, nullable=False),
        sa.Column('requester_id', sa.String(36), nullable=False),
        sa.Column('requester_role', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('approver_id', sa.String(36), nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('comment', sa.Text, nullable=True),
    )
    
    # Create indexes for approval_requests
    op.create_index('idx_approval_requests_status', 'approval_requests', ['status'])
    op.create_index('idx_approval_requests_requester', 'approval_requests', ['requester_id'])
    op.create_index('idx_approval_requests_created_at', 'approval_requests', ['created_at'])


def downgrade() -> None:
    """Drop approval_requests table"""
    
    # Drop indexes
    op.drop_index('idx_approval_requests_created_at', 'approval_requests')
    op.drop_index('idx_approval_requests_requester', 'approval_requests')
    op.drop_index('idx_approval_requests_status', 'approval_requests')
    
    # Drop table
    op.drop_table('approval_requests')
