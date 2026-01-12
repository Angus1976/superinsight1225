"""Add sensitivity policies tables

Revision ID: 006_add_sensitivity_policies
Revises: 005_audit_storage_optimization
Create Date: 2026-01-11 09:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_sensitivity_policies'
down_revision = '005_audit_storage_optimization'
branch_labels = None
depends_on = None

def upgrade():
    # 创建敏感数据策略表
    op.create_table(
        'sensitivity_policies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('patterns', postgresql.JSON(astext_type=sa.Text()), nullable=False, default='[]'),
        sa.Column('masking_rules', postgresql.JSON(astext_type=sa.Text()), nullable=False, default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_sensitivity_policies_tenant_name')
    )
    
    # 创建策略审计日志表
    op.create_table(
        'policy_audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('policy_id', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('old_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['sensitivity_policies.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('idx_sensitivity_policies_tenant_id', 'sensitivity_policies', ['tenant_id'])
    op.create_index('idx_sensitivity_policies_is_active', 'sensitivity_policies', ['is_active'])
    op.create_index('idx_policy_audit_logs_policy_id', 'policy_audit_logs', ['policy_id'])
    op.create_index('idx_policy_audit_logs_tenant_id', 'policy_audit_logs', ['tenant_id'])
    op.create_index('idx_policy_audit_logs_timestamp', 'policy_audit_logs', ['timestamp'])

def downgrade():
    # 删除索引
    op.drop_index('idx_policy_audit_logs_timestamp', table_name='policy_audit_logs')
    op.drop_index('idx_policy_audit_logs_tenant_id', table_name='policy_audit_logs')
    op.drop_index('idx_policy_audit_logs_policy_id', table_name='policy_audit_logs')
    op.drop_index('idx_sensitivity_policies_is_active', table_name='sensitivity_policies')
    op.drop_index('idx_sensitivity_policies_tenant_id', table_name='sensitivity_policies')
    
    # 删除表
    op.drop_table('policy_audit_logs')
    op.drop_table('sensitivity_policies')