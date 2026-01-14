"""Multi-tenant workspace extended models

Revision ID: 20260113_mtw
Revises: 
Create Date: 2026-01-13

This migration adds extended multi-tenant workspace models including:
- Tenant quotas and usage tracking
- Extended workspaces with hierarchy
- Workspace members and custom roles
- Cross-tenant collaboration (share links, whitelist, access logs)
- Tenant audit logs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260113_mtw'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE IF NOT EXISTS extended_tenant_status AS ENUM ('active', 'suspended', 'disabled')")
    op.execute("CREATE TYPE IF NOT EXISTS extended_workspace_status AS ENUM ('active', 'archived', 'deleted')")
    op.execute("CREATE TYPE IF NOT EXISTS member_role AS ENUM ('owner', 'admin', 'member', 'guest')")
    op.execute("CREATE TYPE IF NOT EXISTS share_permission AS ENUM ('read_only', 'edit')")
    op.execute("CREATE TYPE IF NOT EXISTS entity_type AS ENUM ('tenant', 'workspace')")
    
    # Create tenant_quotas table
    op.create_table(
        'tenant_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('storage_bytes', sa.BigInteger(), nullable=False, server_default='10737418240'),
        sa.Column('project_count', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('user_count', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('api_call_count', sa.Integer(), nullable=False, server_default='100000'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.UniqueConstraint('tenant_id')
    )
    op.create_index('ix_tenant_quotas_tenant_id', 'tenant_quotas', ['tenant_id'])
    
    # Create quota_usage table
    op.create_table(
        'quota_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.Enum('tenant', 'workspace', name='entity_type'), nullable=False),
        sa.Column('storage_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('project_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('user_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('api_call_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_id', 'entity_type', name='uq_quota_usage_entity')
    )
    op.create_index('ix_quota_usage_entity', 'quota_usage', ['entity_id', 'entity_type'])
    
    # Create temporary_quotas table
    op.create_table(
        'temporary_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.Enum('tenant', 'workspace', name='entity_type'), nullable=False),
        sa.Column('storage_bytes', sa.BigInteger(), nullable=True),
        sa.Column('project_count', sa.Integer(), nullable=True),
        sa.Column('user_count', sa.Integer(), nullable=True),
        sa.Column('api_call_count', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_temporary_quota_entity', 'temporary_quotas', ['entity_id', 'entity_type'])
    op.create_index('ix_temporary_quota_expires', 'temporary_quotas', ['expires_at'])
    
    # Create extended_workspaces table
    op.create_table(
        'extended_workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('active', 'archived', 'deleted', name='extended_workspace_status'), 
                  nullable=False, server_default='active'),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['parent_id'], ['extended_workspaces.id']),
        sa.UniqueConstraint('tenant_id', 'name', 'parent_id', name='uq_workspace_name_in_parent')
    )
    op.create_index('ix_extended_workspace_tenant', 'extended_workspaces', ['tenant_id'])
    op.create_index('ix_extended_workspace_parent', 'extended_workspaces', ['parent_id'])
    
    # Create custom_roles table
    op.create_table(
        'custom_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['extended_workspaces.id']),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_custom_role_name')
    )
    op.create_index('ix_custom_role_workspace', 'custom_roles', ['workspace_id'])
    
    # Create workspace_members table
    op.create_table(
        'workspace_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', 'guest', name='member_role'), 
                  nullable=False, server_default='member'),
        sa.Column('custom_role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['extended_workspaces.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['custom_role_id'], ['custom_roles.id']),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_member')
    )
    op.create_index('ix_workspace_member_workspace', 'workspace_members', ['workspace_id'])
    op.create_index('ix_workspace_member_user', 'workspace_members', ['user_id'])
    
    # Create workspace_templates table
    op.create_table(
        'workspace_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('default_roles', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'])
    )
    
    # Create workspace_invitations table
    op.create_table(
        'workspace_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', 'guest', name='member_role'), 
                  nullable=False, server_default='member'),
        sa.Column('token', sa.String(64), nullable=False, unique=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['extended_workspaces.id']),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'])
    )
    op.create_index('ix_invitation_workspace', 'workspace_invitations', ['workspace_id'])
    op.create_index('ix_invitation_email', 'workspace_invitations', ['email'])
    op.create_index('ix_invitation_token', 'workspace_invitations', ['token'])
    
    # Create share_links table
    op.create_table(
        'share_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('owner_tenant_id', sa.String(100), nullable=False),
        sa.Column('permission', sa.Enum('read_only', 'edit', name='share_permission'), 
                  nullable=False, server_default='read_only'),
        sa.Column('token', sa.String(64), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['owner_tenant_id'], ['tenants.id'])
    )
    op.create_index('ix_share_link_resource', 'share_links', ['resource_id', 'resource_type'])
    op.create_index('ix_share_link_token', 'share_links', ['token'])
    op.create_index('ix_share_link_owner', 'share_links', ['owner_tenant_id'])
    
    # Create tenant_whitelist table
    op.create_table(
        'tenant_whitelist',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_tenant_id', sa.String(100), nullable=False),
        sa.Column('allowed_tenant_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['owner_tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['allowed_tenant_id'], ['tenants.id']),
        sa.UniqueConstraint('owner_tenant_id', 'allowed_tenant_id', name='uq_tenant_whitelist')
    )
    op.create_index('ix_whitelist_owner', 'tenant_whitelist', ['owner_tenant_id'])
    op.create_index('ix_whitelist_allowed', 'tenant_whitelist', ['allowed_tenant_id'])
    
    # Create cross_tenant_access_logs table
    op.create_table(
        'cross_tenant_access_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('accessor_tenant_id', sa.String(100), nullable=False),
        sa.Column('owner_tenant_id', sa.String(100), nullable=False),
        sa.Column('accessor_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['accessor_tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['owner_tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['accessor_user_id'], ['users.id'])
    )
    op.create_index('ix_cross_tenant_log_accessor', 'cross_tenant_access_logs', ['accessor_tenant_id'])
    op.create_index('ix_cross_tenant_log_owner', 'cross_tenant_access_logs', ['owner_tenant_id'])
    op.create_index('ix_cross_tenant_log_time', 'cross_tenant_access_logs', ['created_at'])
    
    # Create tenant_audit_logs table
    op.create_table(
        'tenant_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )
    op.create_index('ix_tenant_audit_tenant', 'tenant_audit_logs', ['tenant_id'])
    op.create_index('ix_tenant_audit_user', 'tenant_audit_logs', ['user_id'])
    op.create_index('ix_tenant_audit_action', 'tenant_audit_logs', ['action'])
    op.create_index('ix_tenant_audit_time', 'tenant_audit_logs', ['created_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('tenant_audit_logs')
    op.drop_table('cross_tenant_access_logs')
    op.drop_table('tenant_whitelist')
    op.drop_table('share_links')
    op.drop_table('workspace_invitations')
    op.drop_table('workspace_templates')
    op.drop_table('workspace_members')
    op.drop_table('custom_roles')
    op.drop_table('extended_workspaces')
    op.drop_table('temporary_quotas')
    op.drop_table('quota_usage')
    op.drop_table('tenant_quotas')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS entity_type")
    op.execute("DROP TYPE IF EXISTS share_permission")
    op.execute("DROP TYPE IF EXISTS member_role")
    op.execute("DROP TYPE IF EXISTS extended_workspace_status")
    op.execute("DROP TYPE IF EXISTS extended_tenant_status")
