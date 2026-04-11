"""Add workspace columns to existing tables

Revision ID: 003_add_workspace_columns
Revises: 2f6b0cbeb30c
Create Date: 2026-01-10 22:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_workspace_columns'
down_revision = '2f6b0cbeb30c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add workspace_id columns to existing tables."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    def _add_workspace(table: str) -> None:
        if table not in tables:
            return
        cols = {c["name"] for c in insp.get_columns(table)}
        if "workspace_id" in cols:
            return
        op.add_column(
            table,
            sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_index(op.f(f"ix_{table}_workspace_id"), table, ["workspace_id"], unique=False)

    _add_workspace("documents")
    _add_workspace("tasks")
    _add_workspace("quality_issues")
    _add_workspace("billing_records")


def downgrade() -> None:
    """Remove workspace_id columns from existing tables."""
    
    # Remove workspace_id columns
    try:
        op.drop_index(op.f('ix_billing_records_workspace_id'), table_name='billing_records')
        op.drop_column('billing_records', 'workspace_id')
    except Exception:
        pass
    
    try:
        op.drop_index(op.f('ix_quality_issues_workspace_id'), table_name='quality_issues')
        op.drop_column('quality_issues', 'workspace_id')
    except Exception:
        pass
    
    try:
        op.drop_index(op.f('ix_tasks_workspace_id'), table_name='tasks')
        op.drop_column('tasks', 'workspace_id')
    except Exception:
        pass
    
    try:
        op.drop_index(op.f('ix_documents_workspace_id'), table_name='documents')
        op.drop_column('documents', 'workspace_id')
    except Exception:
        pass