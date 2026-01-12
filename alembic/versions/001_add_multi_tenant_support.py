"""Add multi-tenant support

Revision ID: 001_add_multi_tenant_support
Revises: 
Create Date: 2026-01-10 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_multi_tenant_support'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add multi-tenant support to the database."""
    
    # Create tenant status enum
    tenant_status_enum = postgresql.ENUM(
        'ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING',
        name='tenantstatus',
        create_type=False
    )
    tenant_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create workspace status enum
    workspace_status_enum = postgresql.ENUM(
        'ACTIVE', 'INACTIVE', 'ARCHIVED',
        name='workspacestatus',
        create_type=False
    )
    workspace_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create tenant role enum
    tenant_role_enum = postgresql.ENUM(
        'OWNER', 'ADMIN', 'MEMBER', 'VIEWER',
        name='tenantrole',
        create_type=False
    )
    tenant_role_enum.create(op.get_bind(), checkfirst=True)
    
    # Create workspace role enum
    workspace_role_enum = postgresql.ENUM(
        'ADMIN', 'ANNOTATOR', 'REVIEWER', 'VIEWER',
        name='workspacerole',
        create_type=False
    )
    workspace_role_enum.create(op.get_bind(), checkfirst=True)
    
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', tenant_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('label_studio_org_id', sa.String(length=100), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('max_workspaces', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_storage_gb', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('max_api_calls_per_hour', sa.Integer(), nullable=False, server_default='10000'),
        sa.Column('current_users', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_workspaces', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_storage_gb', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('billing_email', sa.String(length=255), nullable=True),
        sa.Column('billing_plan', sa.String(length=50), nullable=False, server_default='basic'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create workspaces table
    op.create_table('workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', workspace_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('label_studio_project_id', sa.String(length=100), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspaces_tenant_id'), 'workspaces', ['tenant_id'], unique=False)
    
    # Create user_tenant_associations table
    op.create_table('user_tenant_associations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('role', tenant_role_enum, nullable=False, server_default='MEMBER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default_tenant', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'tenant_id', name='uq_user_tenant')
    )
    op.create_index(op.f('ix_user_tenant_associations_tenant_id'), 'user_tenant_associations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_user_tenant_associations_user_id'), 'user_tenant_associations', ['user_id'], unique=False)
    
    # Create user_workspace_associations table
    op.create_table('user_workspace_associations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', workspace_role_enum, nullable=False, server_default='ANNOTATOR'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'workspace_id', name='uq_user_workspace')
    )
    op.create_index(op.f('ix_user_workspace_associations_user_id'), 'user_workspace_associations', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_workspace_associations_workspace_id'), 'user_workspace_associations', ['workspace_id'], unique=False)
    
    # Create tenant_resource_usage table
    op.create_table('tenant_resource_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=100), nullable=False),
        sa.Column('api_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('storage_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('annotation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('user_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('workspace_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_date', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_DATE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenant_resource_usage_tenant_id'), 'tenant_resource_usage', ['tenant_id'], unique=False)
    
    # Add workspace_id column to existing tables
    op.add_column('documents', sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_documents_workspace_id'), 'documents', ['workspace_id'], unique=False)
    op.create_foreign_key('fk_documents_workspace_id', 'documents', 'workspaces', ['workspace_id'], ['id'])
    
    op.add_column('tasks', sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_tasks_workspace_id'), 'tasks', ['workspace_id'], unique=False)
    op.create_foreign_key('fk_tasks_workspace_id', 'tasks', 'workspaces', ['workspace_id'], ['id'])
    
    op.add_column('quality_issues', sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_quality_issues_workspace_id'), 'quality_issues', ['workspace_id'], unique=False)
    op.create_foreign_key('fk_quality_issues_workspace_id', 'quality_issues', 'workspaces', ['workspace_id'], ['id'])
    
    op.add_column('billing_records', sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_billing_records_workspace_id'), 'billing_records', ['workspace_id'], unique=False)
    op.create_foreign_key('fk_billing_records_workspace_id', 'billing_records', 'workspaces', ['workspace_id'], ['id'])
    
    # Create default tenant and workspace for existing data
    op.execute("""
        INSERT INTO tenants (id, name, display_name, description, status)
        VALUES ('default', 'default', 'Default Tenant', 'Default tenant for existing data', 'ACTIVE')
        ON CONFLICT (id) DO NOTHING;
    """)
    
    # Create default workspace
    op.execute("""
        INSERT INTO workspaces (id, tenant_id, name, display_name, description, is_default)
        SELECT gen_random_uuid(), 'default', 'default', 'Default Workspace', 'Default workspace for existing data', true
        WHERE NOT EXISTS (SELECT 1 FROM workspaces WHERE tenant_id = 'default' AND name = 'default');
    """)
    
    # Update existing records to use default workspace
    op.execute("""
        UPDATE documents 
        SET workspace_id = (SELECT id FROM workspaces WHERE tenant_id = 'default' AND name = 'default' LIMIT 1)
        WHERE workspace_id IS NULL;
    """)
    
    op.execute("""
        UPDATE tasks 
        SET workspace_id = (SELECT id FROM workspaces WHERE tenant_id = 'default' AND name = 'default' LIMIT 1)
        WHERE workspace_id IS NULL;
    """)
    
    op.execute("""
        UPDATE quality_issues 
        SET workspace_id = (SELECT id FROM workspaces WHERE tenant_id = 'default' AND name = 'default' LIMIT 1)
        WHERE workspace_id IS NULL;
    """)
    
    op.execute("""
        UPDATE billing_records 
        SET workspace_id = (SELECT id FROM workspaces WHERE tenant_id = 'default' AND name = 'default' LIMIT 1)
        WHERE workspace_id IS NULL;
    """)
    
    # Associate existing users with default tenant
    op.execute("""
        INSERT INTO user_tenant_associations (id, user_id, tenant_id, role, is_active, is_default_tenant, accepted_at)
        SELECT gen_random_uuid(), id, 'default', 'ADMIN', true, true, now()
        FROM users
        WHERE NOT EXISTS (
            SELECT 1 FROM user_tenant_associations 
            WHERE user_tenant_associations.user_id = users.id 
            AND user_tenant_associations.tenant_id = 'default'
        );
    """)
    
    # Associate existing users with default workspace
    op.execute("""
        INSERT INTO user_workspace_associations (id, user_id, workspace_id, role, is_active)
        SELECT gen_random_uuid(), u.id, w.id, 'ADMIN', true
        FROM users u
        CROSS JOIN workspaces w
        WHERE w.tenant_id = 'default' AND w.name = 'default'
        AND NOT EXISTS (
            SELECT 1 FROM user_workspace_associations uwa
            WHERE uwa.user_id = u.id AND uwa.workspace_id = w.id
        );
    """)


def downgrade() -> None:
    """Remove multi-tenant support from the database."""
    
    # Remove foreign key constraints and columns from existing tables
    op.drop_constraint('fk_billing_records_workspace_id', 'billing_records', type_='foreignkey')
    op.drop_index(op.f('ix_billing_records_workspace_id'), table_name='billing_records')
    op.drop_column('billing_records', 'workspace_id')
    
    op.drop_constraint('fk_quality_issues_workspace_id', 'quality_issues', type_='foreignkey')
    op.drop_index(op.f('ix_quality_issues_workspace_id'), table_name='quality_issues')
    op.drop_column('quality_issues', 'workspace_id')
    
    op.drop_constraint('fk_tasks_workspace_id', 'tasks', type_='foreignkey')
    op.drop_index(op.f('ix_tasks_workspace_id'), table_name='tasks')
    op.drop_column('tasks', 'workspace_id')
    
    op.drop_constraint('fk_documents_workspace_id', 'documents', type_='foreignkey')
    op.drop_index(op.f('ix_documents_workspace_id'), table_name='documents')
    op.drop_column('documents', 'workspace_id')
    
    # Drop multi-tenant tables
    op.drop_index(op.f('ix_tenant_resource_usage_tenant_id'), table_name='tenant_resource_usage')
    op.drop_table('tenant_resource_usage')
    
    op.drop_index(op.f('ix_user_workspace_associations_workspace_id'), table_name='user_workspace_associations')
    op.drop_index(op.f('ix_user_workspace_associations_user_id'), table_name='user_workspace_associations')
    op.drop_table('user_workspace_associations')
    
    op.drop_index(op.f('ix_user_tenant_associations_user_id'), table_name='user_tenant_associations')
    op.drop_index(op.f('ix_user_tenant_associations_tenant_id'), table_name='user_tenant_associations')
    op.drop_table('user_tenant_associations')
    
    op.drop_index(op.f('ix_workspaces_tenant_id'), table_name='workspaces')
    op.drop_table('workspaces')
    
    op.drop_table('tenants')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS workspacerole')
    op.execute('DROP TYPE IF EXISTS tenantrole')
    op.execute('DROP TYPE IF EXISTS workspacestatus')
    op.execute('DROP TYPE IF EXISTS tenantstatus')