"""Add tenant_id to business logic tables

Revision ID: 014_business_logic_tenant
Revises: 013_ragas_eval
Create Date: 2026-01-19 14:00:00.000000

Adds tenant_id column to business_rules, business_patterns, and business_insights tables
for multi-tenant support. Also adds composite indexes for optimized queries.

Implements Requirements 5.1-5.9 for business logic service database operations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014_business_logic_tenant'
down_revision = None  # Will be set during migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add tenant_id column and indexes to business logic tables."""
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    # Check if tables exist before modifying
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Add tenant_id to business_rules if table exists
    if 'business_rules' in existing_tables:
        # Check if tenant_id column already exists
        columns = [col['name'] for col in inspector.get_columns('business_rules')]
        if 'tenant_id' not in columns:
            op.add_column(
                'business_rules',
                sa.Column('tenant_id', sa.String(100), nullable=True)
            )
            # Update existing rows with default tenant_id
            op.execute("UPDATE business_rules SET tenant_id = 'default' WHERE tenant_id IS NULL")
            # Make column non-nullable
            op.alter_column('business_rules', 'tenant_id', nullable=False)
            # Add index
            op.create_index(
                'ix_business_rules_tenant_id',
                'business_rules',
                ['tenant_id']
            )
            # Add composite index for common queries
            op.create_index(
                'ix_business_rules_tenant_project_type_active',
                'business_rules',
                ['tenant_id', 'project_id', 'rule_type', 'is_active']
            )
    
    # Add tenant_id to business_patterns if table exists
    if 'business_patterns' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('business_patterns')]
        if 'tenant_id' not in columns:
            op.add_column(
                'business_patterns',
                sa.Column('tenant_id', sa.String(100), nullable=True)
            )
            op.execute("UPDATE business_patterns SET tenant_id = 'default' WHERE tenant_id IS NULL")
            op.alter_column('business_patterns', 'tenant_id', nullable=False)
            op.create_index(
                'ix_business_patterns_tenant_id',
                'business_patterns',
                ['tenant_id']
            )
            op.create_index(
                'ix_business_patterns_tenant_project_type_strength',
                'business_patterns',
                ['tenant_id', 'project_id', 'pattern_type', 'strength']
            )
    
    # Add tenant_id to business_insights if table exists
    if 'business_insights' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('business_insights')]
        if 'tenant_id' not in columns:
            op.add_column(
                'business_insights',
                sa.Column('tenant_id', sa.String(100), nullable=True)
            )
            op.execute("UPDATE business_insights SET tenant_id = 'default' WHERE tenant_id IS NULL")
            op.alter_column('business_insights', 'tenant_id', nullable=False)
            op.create_index(
                'ix_business_insights_tenant_id',
                'business_insights',
                ['tenant_id']
            )
            op.create_index(
                'ix_business_insights_tenant_project_type_ack',
                'business_insights',
                ['tenant_id', 'project_id', 'insight_type', 'acknowledged_at']
            )


def downgrade() -> None:
    """Remove tenant_id column and indexes from business logic tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Remove from business_insights
    if 'business_insights' in existing_tables:
        try:
            op.drop_index('ix_business_insights_tenant_project_type_ack', table_name='business_insights')
        except Exception:
            pass
        try:
            op.drop_index('ix_business_insights_tenant_id', table_name='business_insights')
        except Exception:
            pass
        try:
            op.drop_column('business_insights', 'tenant_id')
        except Exception:
            pass
    
    # Remove from business_patterns
    if 'business_patterns' in existing_tables:
        try:
            op.drop_index('ix_business_patterns_tenant_project_type_strength', table_name='business_patterns')
        except Exception:
            pass
        try:
            op.drop_index('ix_business_patterns_tenant_id', table_name='business_patterns')
        except Exception:
            pass
        try:
            op.drop_column('business_patterns', 'tenant_id')
        except Exception:
            pass
    
    # Remove from business_rules
    if 'business_rules' in existing_tables:
        try:
            op.drop_index('ix_business_rules_tenant_project_type_active', table_name='business_rules')
        except Exception:
            pass
        try:
            op.drop_index('ix_business_rules_tenant_id', table_name='business_rules')
        except Exception:
            pass
        try:
            op.drop_column('business_rules', 'tenant_id')
        except Exception:
            pass
