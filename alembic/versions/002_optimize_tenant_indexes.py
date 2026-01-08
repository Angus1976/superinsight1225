"""Optimize database indexes for multi-tenant queries

Revision ID: 002_optimize_tenant_indexes
Revises: 001_add_tenant_id_fields
Create Date: 2026-01-08 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_optimize_tenant_indexes'
down_revision = '001_add_tenant_id_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Create composite indexes for efficient multi-tenant queries."""
    
    # Composite indexes for common query patterns
    
    # Documents: tenant_id + sync_status for sync operations
    op.create_index('ix_documents_tenant_sync_status', 'documents', 
                   ['tenant_id', 'sync_status'])
    
    # Tasks: tenant_id + status for task management
    op.create_index('ix_tasks_tenant_status', 'tasks', 
                   ['tenant_id', 'status'])
    
    # Tasks: tenant_id + project_id for project-specific queries
    op.create_index('ix_tasks_tenant_project', 'tasks', 
                   ['tenant_id', 'project_id'])
    
    # Quality Issues: tenant_id + status for issue tracking
    op.create_index('ix_quality_issues_tenant_status', 'quality_issues', 
                   ['tenant_id', 'status'])
    
    # Tickets: tenant_id + status for ticket management
    op.create_index('ix_tickets_tenant_status', 'tickets', 
                   ['tenant_id', 'status'])
    
    # Tickets: tenant_id + assigned_to for workload queries
    op.create_index('ix_tickets_tenant_assigned', 'tickets', 
                   ['tenant_id', 'assigned_to'])
    
    # Business Rules: tenant_id + project_id for business logic queries
    op.create_index('ix_business_rules_tenant_project', 'business_rules', 
                   ['tenant_id', 'project_id'])
    
    # Business Rules: tenant_id + rule_type for type-specific queries
    op.create_index('ix_business_rules_tenant_type', 'business_rules', 
                   ['tenant_id', 'rule_type'])
    
    # Business Patterns: tenant_id + project_id
    op.create_index('ix_business_patterns_tenant_project', 'business_patterns', 
                   ['tenant_id', 'project_id'])
    
    # Business Insights: tenant_id + project_id
    op.create_index('ix_business_insights_tenant_project', 'business_insights', 
                   ['tenant_id', 'project_id'])
    
    # Performance Records: tenant_id + user_id for user performance queries
    op.create_index('ix_performance_records_tenant_user', 'performance_records', 
                   ['tenant_id', 'user_id'])
    
    # Audit Logs: tenant_id + action for audit queries
    op.create_index('ix_audit_logs_tenant_action', 'audit_logs', 
                   ['tenant_id', 'action'])
    
    # Sync Jobs: tenant_id + status for sync management
    op.create_index('ix_sync_jobs_tenant_status_updated', 'sync_jobs', 
                   ['tenant_id', 'status', 'updated_at'])
    
    # Billing Records: tenant_id + billing_date for billing queries
    op.create_index('ix_billing_records_tenant_date', 'billing_records', 
                   ['tenant_id', 'billing_date'])


def downgrade():
    """Remove composite indexes."""
    
    op.drop_index('ix_documents_tenant_sync_status', 'documents')
    op.drop_index('ix_tasks_tenant_status', 'tasks')
    op.drop_index('ix_tasks_tenant_project', 'tasks')
    op.drop_index('ix_quality_issues_tenant_status', 'quality_issues')
    op.drop_index('ix_tickets_tenant_status', 'tickets')
    op.drop_index('ix_tickets_tenant_assigned', 'tickets')
    op.drop_index('ix_business_rules_tenant_project', 'business_rules')
    op.drop_index('ix_business_rules_tenant_type', 'business_rules')
    op.drop_index('ix_business_patterns_tenant_project', 'business_patterns')
    op.drop_index('ix_business_insights_tenant_project', 'business_insights')
    op.drop_index('ix_performance_records_tenant_user', 'performance_records')
    op.drop_index('ix_audit_logs_tenant_action', 'audit_logs')
    op.drop_index('ix_sync_jobs_tenant_status_updated', 'sync_jobs')
    op.drop_index('ix_billing_records_tenant_date', 'billing_records')