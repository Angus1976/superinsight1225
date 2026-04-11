"""Add tenant_id fields to all business tables for multi-tenant support

Revision ID: 001_add_tenant_id_fields
Revises: 
Create Date: 2026-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_tenant_id_fields'
down_revision = 'add_business_logic_001'  # Depends on business logic tables
branch_labels = None
depends_on = None


def upgrade():
    """Add tenant_id fields to tables that don't have them yet."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    def _cols(table: str):
        if table not in existing_tables:
            return []
        return [c["name"] for c in inspector.get_columns(table)]

    def _has_column(table: str, col: str) -> bool:
        if table not in inspector.get_table_names():
            return False
        return col in [c["name"] for c in inspector.get_columns(table)]

    # Add tenant_id to business_rules table (idempotent vs parallel migrations / 014)
    if "business_rules" in existing_tables and "tenant_id" not in _cols("business_rules"):
        op.add_column(
            "business_rules",
            sa.Column("tenant_id", sa.String(100), nullable=True),
        )
        op.create_index("ix_business_rules_tenant_id", "business_rules", ["tenant_id"])

    if "business_patterns" in existing_tables and "tenant_id" not in _cols("business_patterns"):
        op.add_column(
            "business_patterns",
            sa.Column("tenant_id", sa.String(100), nullable=True),
        )
        op.create_index("ix_business_patterns_tenant_id", "business_patterns", ["tenant_id"])

    if "business_insights" in existing_tables and "tenant_id" not in _cols("business_insights"):
        op.add_column(
            "business_insights",
            sa.Column("tenant_id", sa.String(100), nullable=True),
        )
        op.create_index("ix_business_insights_tenant_id", "business_insights", ["tenant_id"])
    
    # ticket_history / quality_issues：表可能尚未创建；PG 事务内 DDL 失败会毒化整事务，禁止仅靠 try/except
    if "ticket_history" in existing_tables and "tenant_id" not in _cols("ticket_history"):
        op.add_column(
            "ticket_history",
            sa.Column("tenant_id", sa.String(100), nullable=True),
        )
        op.create_index("ix_ticket_history_tenant_id", "ticket_history", ["tenant_id"])

    if "quality_issues" in existing_tables and "tenant_id" not in _cols("quality_issues"):
        op.add_column(
            "quality_issues",
            sa.Column("tenant_id", sa.String(100), nullable=True),
        )
        op.create_index("ix_quality_issues_tenant_id", "quality_issues", ["tenant_id"])

    # Update / NOT NULL：须重新 introspect（上面可能刚 add_column）
    if _has_column("business_rules", "tenant_id"):
        op.execute("UPDATE business_rules SET tenant_id = 'default' WHERE tenant_id IS NULL")
    if _has_column("business_patterns", "tenant_id"):
        op.execute("UPDATE business_patterns SET tenant_id = 'default' WHERE tenant_id IS NULL")
    if _has_column("business_insights", "tenant_id"):
        op.execute("UPDATE business_insights SET tenant_id = 'default' WHERE tenant_id IS NULL")

    if _has_column("ticket_history", "tenant_id"):
        op.execute("UPDATE ticket_history SET tenant_id = 'default' WHERE tenant_id IS NULL")

    if _has_column("quality_issues", "tenant_id"):
        op.execute("UPDATE quality_issues SET tenant_id = 'default' WHERE tenant_id IS NULL")

    if _has_column("business_rules", "tenant_id"):
        op.alter_column("business_rules", "tenant_id", nullable=False)
    if _has_column("business_patterns", "tenant_id"):
        op.alter_column("business_patterns", "tenant_id", nullable=False)
    if _has_column("business_insights", "tenant_id"):
        op.alter_column("business_insights", "tenant_id", nullable=False)


def downgrade():
    """Remove tenant_id fields."""
    
    # Remove indexes first
    op.drop_index('ix_business_rules_tenant_id', 'business_rules')
    op.drop_index('ix_business_patterns_tenant_id', 'business_patterns')
    op.drop_index('ix_business_insights_tenant_id', 'business_insights')
    
    try:
        op.drop_index('ix_ticket_history_tenant_id', 'ticket_history')
    except Exception:
        pass
        
    try:
        op.drop_index('ix_quality_issues_tenant_id', 'quality_issues')
    except Exception:
        pass
    
    # Remove columns
    op.drop_column('business_rules', 'tenant_id')
    op.drop_column('business_patterns', 'tenant_id')
    op.drop_column('business_insights', 'tenant_id')
    
    try:
        op.drop_column('ticket_history', 'tenant_id')
    except Exception:
        pass
        
    try:
        op.drop_column('quality_issues', 'tenant_id')
    except Exception:
        pass