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
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add tenant_id fields to tables that don't have them yet."""
    
    # Add tenant_id to business_rules table
    op.add_column('business_rules', 
                  sa.Column('tenant_id', sa.String(100), nullable=True))
    op.create_index('ix_business_rules_tenant_id', 'business_rules', ['tenant_id'])
    
    # Add tenant_id to business_patterns table
    op.add_column('business_patterns', 
                  sa.Column('tenant_id', sa.String(100), nullable=True))
    op.create_index('ix_business_patterns_tenant_id', 'business_patterns', ['tenant_id'])
    
    # Add tenant_id to business_insights table
    op.add_column('business_insights', 
                  sa.Column('tenant_id', sa.String(100), nullable=True))
    op.create_index('ix_business_insights_tenant_id', 'business_insights', ['tenant_id'])
    
    # Add tenant_id to ticket_history table (if it doesn't have it)
    try:
        op.add_column('ticket_history', 
                      sa.Column('tenant_id', sa.String(100), nullable=True))
        op.create_index('ix_ticket_history_tenant_id', 'ticket_history', ['tenant_id'])
    except Exception:
        # Column might already exist
        pass
    
    # Add tenant_id to quality_issues table (if it doesn't have it)
    try:
        op.add_column('quality_issues', 
                      sa.Column('tenant_id', sa.String(100), nullable=True))
        op.create_index('ix_quality_issues_tenant_id', 'quality_issues', ['tenant_id'])
    except Exception:
        # Column might already exist
        pass
    
    # Update existing records with a default tenant_id
    # This is a placeholder - in production, you'd need to map existing data to appropriate tenants
    try:
        op.execute("UPDATE business_rules SET tenant_id = 'default' WHERE tenant_id IS NULL")
    except Exception:
        pass
    try:
        op.execute("UPDATE business_patterns SET tenant_id = 'default' WHERE tenant_id IS NULL")
    except Exception:
        pass
    try:
        op.execute("UPDATE business_insights SET tenant_id = 'default' WHERE tenant_id IS NULL")
    except Exception:
        pass
    
    try:
        op.execute("UPDATE ticket_history SET tenant_id = 'default' WHERE tenant_id IS NULL")
    except Exception:
        pass
        
    try:
        op.execute("UPDATE quality_issues SET tenant_id = 'default' WHERE tenant_id IS NULL")
    except Exception:
        pass
    
    # Make tenant_id NOT NULL after populating default values
    try:
        op.alter_column('business_rules', 'tenant_id', nullable=False)
    except Exception:
        pass
    try:
        op.alter_column('business_patterns', 'tenant_id', nullable=False)
    except Exception:
        pass
    try:
        op.alter_column('business_insights', 'tenant_id', nullable=False)
    except Exception:
        pass


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