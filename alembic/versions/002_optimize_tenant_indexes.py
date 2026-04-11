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
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    def _cols(t: str) -> set:
        if t not in tables:
            return set()
        return {c["name"] for c in insp.get_columns(t)}

    def _safe_index(name: str, table: str, columns: list[str]) -> None:
        if table not in tables:
            return
        colset = _cols(table)
        if not all(c in colset for c in columns):
            return
        op.create_index(name, table, columns)

    # 各表可能分属不同迁移分支，缺表或缺列时跳过（避免 PG 事务被单条 DDL 失败毒化）
    _safe_index("ix_documents_tenant_sync_status", "documents", ["tenant_id", "sync_status"])
    _safe_index("ix_tasks_tenant_status", "tasks", ["tenant_id", "status"])
    _safe_index("ix_tasks_tenant_project", "tasks", ["tenant_id", "project_id"])
    _safe_index("ix_quality_issues_tenant_status", "quality_issues", ["tenant_id", "status"])
    _safe_index("ix_tickets_tenant_status", "tickets", ["tenant_id", "status"])
    _safe_index("ix_tickets_tenant_assigned", "tickets", ["tenant_id", "assigned_to"])
    _safe_index("ix_business_rules_tenant_project", "business_rules", ["tenant_id", "project_id"])
    _safe_index("ix_business_rules_tenant_type", "business_rules", ["tenant_id", "rule_type"])
    _safe_index("ix_business_patterns_tenant_project", "business_patterns", ["tenant_id", "project_id"])
    _safe_index("ix_business_insights_tenant_project", "business_insights", ["tenant_id", "project_id"])
    _safe_index("ix_performance_records_tenant_user", "performance_records", ["tenant_id", "user_id"])
    _safe_index("ix_audit_logs_tenant_action", "audit_logs", ["tenant_id", "action"])
    _safe_index("ix_sync_jobs_tenant_status_updated", "sync_jobs", ["tenant_id", "status", "updated_at"])
    _safe_index("ix_billing_records_tenant_date", "billing_records", ["tenant_id", "billing_date"])


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