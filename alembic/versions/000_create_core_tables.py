"""Create core tables for SuperInsight

Revision ID: 000_core_tables
Revises: None
Create Date: 2026-01-16

This migration creates the essential tables needed for the application to start.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000_core_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create core tables."""
    
    # Create audit_logs table (required by the application)
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=True, server_default='system'),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(200), nullable=True),
        sa.Column('role', sa.String(50), nullable=True, server_default='user'),
        sa.Column('tenant_id', sa.String(100), nullable=True, server_default='default'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('idx_users_email', 'users', ['email'])
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('source', sa.String(200), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=True, server_default='default'),
        sa.Column('status', sa.String(50), nullable=True, server_default='pending'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('idx_documents_tenant_id', 'documents', ['tenant_id'])
    op.create_index('idx_documents_status', 'documents', ['status'])
    
    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=True, server_default='default'),
        sa.Column('status', sa.String(50), nullable=True, server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id']),
    )
    op.create_index('idx_tasks_tenant_id', 'tasks', ['tenant_id'])
    op.create_index('idx_tasks_status', 'tasks', ['status'])
    op.create_index('idx_tasks_assignee_id', 'tasks', ['assignee_id'])
    
    # Create billing_records table
    op.create_table(
        'billing_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(100), nullable=True, server_default='default'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('currency', sa.String(10), nullable=True, server_default='CNY'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
    )
    op.create_index('idx_billing_records_tenant_id', 'billing_records', ['tenant_id'])
    
    # Create quality_issues table
    op.create_table(
        'quality_issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(100), nullable=True, server_default='default'),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('issue_type', sa.String(100), nullable=True),
        sa.Column('severity', sa.String(50), nullable=True, server_default='medium'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True, server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
    )
    op.create_index('idx_quality_issues_tenant_id', 'quality_issues', ['tenant_id'])
    op.create_index('idx_quality_issues_status', 'quality_issues', ['status'])


def downgrade() -> None:
    """Drop core tables."""
    op.drop_table('quality_issues')
    op.drop_table('billing_records')
    op.drop_table('tasks')
    op.drop_table('documents')
    op.drop_table('users')
    op.drop_table('audit_logs')
