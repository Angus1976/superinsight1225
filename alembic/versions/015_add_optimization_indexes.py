"""Add optimization indexes for database query performance

Revision ID: 015_optimization_indexes
Revises: 014_business_logic_tenant
Create Date: 2026-01-19 16:00:00.000000

Adds database indexes for frequently queried columns to improve query performance.
Implements Requirement 9.1 for database query optimization.

Indexes added:
- Data sources: tenant_id + is_active composite index
- Evaluation results: created_at index for time-range queries
- Business rules: project_id + rule_type + is_active composite index
- Tickets: sla_deadline + status + sla_breached composite index for SLA monitoring
- Annotations: updated_at index for incremental sync queries
- Documents: source_type + created_at composite index
- Tasks: status + priority composite index
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015_optimization_indexes'
down_revision = '014_business_logic_tenant'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add optimization indexes for improved query performance."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    def index_exists(table_name: str, index_name: str) -> bool:
        try:
            indexes = inspector.get_indexes(table_name)
            return any(idx["name"] == index_name for idx in indexes)
        except Exception:
            return False

    def table_cols(table_name: str) -> set:
        if table_name not in existing_tables:
            return set()
        return {c["name"] for c in inspector.get_columns(table_name)}

    def safe_create_index(name: str, table_name: str, columns: list) -> None:
        if table_name not in existing_tables or index_exists(table_name, name):
            return
        colset = table_cols(table_name)
        if not all(c in colset for c in columns):
            return
        op.create_index(name, table_name, columns, unique=False)

    # Data sources table indexes
    safe_create_index(
        "ix_data_sources_tenant_active", "data_sources", ["tenant_id", "is_active"]
    )
    safe_create_index("ix_data_sources_db_type", "data_sources", ["db_type"])
    
    safe_create_index(
        "ix_evaluation_results_created_at",
        "ragas_evaluation_results",
        ["created_at"],
    )
    safe_create_index(
        "ix_evaluation_results_task_id",
        "ragas_evaluation_results",
        ["task_id"],
    )

    safe_create_index(
        "ix_business_rules_project_type_active",
        "business_rules",
        ["project_id", "rule_type", "is_active"],
    )
    safe_create_index(
        "ix_business_rules_confidence", "business_rules", ["confidence"]
    )

    safe_create_index(
        "ix_tickets_sla_status",
        "tickets",
        ["sla_deadline", "status", "sla_breached"],
    )
    safe_create_index(
        "ix_tickets_priority_status", "tickets", ["priority", "status"]
    )
    safe_create_index(
        "ix_tickets_assignee", "tickets", ["assignee_id", "status"]
    )

    safe_create_index(
        "ix_documents_source_created",
        "documents",
        ["source_type", "created_at"],
    )
    safe_create_index("ix_documents_updated_at", "documents", ["updated_at"])
    safe_create_index(
        "ix_documents_sync_status",
        "documents",
        ["sync_status", "last_synced_at"],
    )

    safe_create_index(
        "ix_tasks_status_quality", "tasks", ["status", "quality_score"]
    )
    safe_create_index(
        "ix_tasks_project_status", "tasks", ["project_id", "status"]
    )
    safe_create_index(
        "ix_tasks_sync_status",
        "tasks",
        ["sync_status", "last_synced_at"],
    )

    safe_create_index(
        "ix_quality_issues_severity_status",
        "quality_issues",
        ["severity", "status"],
    )
    safe_create_index(
        "ix_quality_issues_assignee",
        "quality_issues",
        ["assignee_id", "status"],
    )

    safe_create_index(
        "ix_billing_tenant_date",
        "billing_records",
        ["tenant_id", "billing_date"],
    )
    safe_create_index(
        "ix_billing_user_date",
        "billing_records",
        ["user_id", "billing_date"],
    )

    safe_create_index(
        "ix_sync_jobs_status_scheduled",
        "sync_jobs",
        ["status", "scheduled_at"],
    )
    safe_create_index(
        "ix_sync_jobs_source_status", "sync_jobs", ["source_id", "status"]
    )

    safe_create_index(
        "ix_sync_executions_job_started",
        "sync_executions",
        ["job_id", "started_at"],
    )


def downgrade() -> None:
    """Remove optimization indexes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Helper function to safely drop index
    def safe_drop_index(index_name: str, table_name: str):
        try:
            op.drop_index(index_name, table_name=table_name)
        except Exception:
            pass
    
    # Remove sync executions indexes
    if 'sync_executions' in existing_tables:
        safe_drop_index('ix_sync_executions_job_started', 'sync_executions')
    
    # Remove sync jobs indexes
    if 'sync_jobs' in existing_tables:
        safe_drop_index('ix_sync_jobs_source_status', 'sync_jobs')
        safe_drop_index('ix_sync_jobs_status_scheduled', 'sync_jobs')
    
    # Remove billing records indexes
    if 'billing_records' in existing_tables:
        safe_drop_index('ix_billing_user_date', 'billing_records')
        safe_drop_index('ix_billing_tenant_date', 'billing_records')
    
    # Remove quality issues indexes
    if 'quality_issues' in existing_tables:
        safe_drop_index('ix_quality_issues_assignee', 'quality_issues')
        safe_drop_index('ix_quality_issues_severity_status', 'quality_issues')
    
    # Remove tasks indexes
    if 'tasks' in existing_tables:
        safe_drop_index('ix_tasks_sync_status', 'tasks')
        safe_drop_index('ix_tasks_project_status', 'tasks')
        safe_drop_index('ix_tasks_status_quality', 'tasks')
    
    # Remove documents indexes
    if 'documents' in existing_tables:
        safe_drop_index('ix_documents_sync_status', 'documents')
        safe_drop_index('ix_documents_updated_at', 'documents')
        safe_drop_index('ix_documents_source_created', 'documents')
    
    # Remove tickets indexes
    if 'tickets' in existing_tables:
        safe_drop_index('ix_tickets_assignee', 'tickets')
        safe_drop_index('ix_tickets_priority_status', 'tickets')
        safe_drop_index('ix_tickets_sla_status', 'tickets')
    
    # Remove business rules indexes
    if 'business_rules' in existing_tables:
        safe_drop_index('ix_business_rules_confidence', 'business_rules')
        safe_drop_index('ix_business_rules_project_type_active', 'business_rules')
    
    # Remove ragas evaluation results indexes
    if 'ragas_evaluation_results' in existing_tables:
        safe_drop_index('ix_evaluation_results_task_id', 'ragas_evaluation_results')
        safe_drop_index('ix_evaluation_results_created_at', 'ragas_evaluation_results')
    
    # Remove data sources indexes
    if 'data_sources' in existing_tables:
        safe_drop_index('ix_data_sources_db_type', 'data_sources')
        safe_drop_index('ix_data_sources_tenant_active', 'data_sources')
