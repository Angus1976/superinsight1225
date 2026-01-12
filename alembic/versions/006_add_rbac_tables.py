"""Add RBAC tables for enhanced role-based access control

Revision ID: 006_add_rbac_tables
Revises: 005_audit_storage_optimization
Create Date: 2026-01-10 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_rbac_tables'
down_revision = '005_audit_storage_optimization'
branch_labels = None
depends_on = None


def upgrade():
    """Add RBAC tables for enhanced role-based access control."""
    
    # Create enum types
    permission_scope_enum = postgresql.ENUM(
        'global', 'tenant', 'resource', 
        name='permissionscope'
    )
    permission_scope_enum.create(op.get_bind())
    
    resource_type_enum = postgresql.ENUM(
        'project', 'dataset', 'model', 'pipeline', 'report', 
        'dashboard', 'user', 'role', 'permission', 'audit_log', 'system_config',
        name='resourcetype'
    )
    resource_type_enum.create(op.get_bind())
    
    # Create rbac_roles table
    op.create_table(
        'rbac_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('parent_role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_system_role', sa.Boolean, default=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['parent_role_id'], ['rbac_roles.id']),
        
        # Constraints
        sa.UniqueConstraint('name', 'tenant_id', name='uq_role_name_tenant'),
    )
    
    # Create indexes for rbac_roles
    op.create_index('idx_role_tenant_active', 'rbac_roles', ['tenant_id', 'is_active'])
    op.create_index('idx_role_parent', 'rbac_roles', ['parent_role_id'])
    
    # Create rbac_permissions table
    op.create_table(
        'rbac_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('scope', permission_scope_enum, nullable=False),
        sa.Column('resource_type', resource_type_enum, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_system_permission', sa.Boolean, default=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create indexes for rbac_permissions
    op.create_index('idx_permission_scope_resource', 'rbac_permissions', ['scope', 'resource_type'])
    op.create_index('idx_permission_active', 'rbac_permissions', ['is_active'])
    
    # Create rbac_role_permissions table
    op.create_table(
        'rbac_role_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('conditions', sa.JSON, nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['role_id'], ['rbac_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['rbac_permissions.id'], ondelete='CASCADE'),
        
        # Constraints
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )
    
    # Create indexes for rbac_role_permissions
    op.create_index('idx_role_permission_role', 'rbac_role_permissions', ['role_id'])
    op.create_index('idx_role_permission_permission', 'rbac_role_permissions', ['permission_id'])
    
    # Create rbac_user_roles table
    op.create_table(
        'rbac_user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('conditions', sa.JSON, nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['rbac_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id']),
        
        # Constraints
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )
    
    # Create indexes for rbac_user_roles
    op.create_index('idx_user_role_user', 'rbac_user_roles', ['user_id'])
    op.create_index('idx_user_role_role', 'rbac_user_roles', ['role_id'])
    op.create_index('idx_user_role_active', 'rbac_user_roles', ['is_active'])
    
    # Create rbac_resources table
    op.create_table(
        'rbac_resources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', sa.String(255), nullable=False),
        sa.Column('resource_type', resource_type_enum, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('parent_resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['parent_resource_id'], ['rbac_resources.id']),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        
        # Constraints
        sa.UniqueConstraint('resource_id', 'resource_type', 'tenant_id', name='uq_resource_tenant'),
    )
    
    # Create indexes for rbac_resources
    op.create_index('idx_resource_type_tenant', 'rbac_resources', ['resource_type', 'tenant_id'])
    op.create_index('idx_resource_owner', 'rbac_resources', ['owner_id'])
    op.create_index('idx_resource_parent', 'rbac_resources', ['parent_resource_id'])
    
    # Create rbac_resource_permissions table
    op.create_table(
        'rbac_resource_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=False),
        sa.Column('resource_type', resource_type_enum, nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('conditions', sa.JSON, nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['rbac_permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id']),
        
        # Constraints
        sa.UniqueConstraint('user_id', 'resource_id', 'resource_type', 'permission_id', name='uq_user_resource_permission'),
    )
    
    # Create indexes for rbac_resource_permissions
    op.create_index('idx_resource_permission_user', 'rbac_resource_permissions', ['user_id'])
    op.create_index('idx_resource_permission_resource', 'rbac_resource_permissions', ['resource_id', 'resource_type'])
    op.create_index('idx_resource_permission_permission', 'rbac_resource_permissions', ['permission_id'])
    op.create_index('idx_resource_permission_active', 'rbac_resource_permissions', ['is_active'])
    
    # Create rbac_permission_groups table
    op.create_table(
        'rbac_permission_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_system_group', sa.Boolean, default=False),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create indexes for rbac_permission_groups
    op.create_index('idx_permission_group_active', 'rbac_permission_groups', ['is_active'])
    
    # Create rbac_permission_group_members table
    op.create_table(
        'rbac_permission_group_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('added_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['group_id'], ['rbac_permission_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['rbac_permissions.id'], ondelete='CASCADE'),
        
        # Constraints
        sa.UniqueConstraint('group_id', 'permission_id', name='uq_group_permission'),
    )
    
    # Create indexes for rbac_permission_group_members
    op.create_index('idx_group_member_group', 'rbac_permission_group_members', ['group_id'])
    op.create_index('idx_group_member_permission', 'rbac_permission_group_members', ['permission_id'])
    
    # Insert default system permissions
    op.execute("""
        INSERT INTO rbac_permissions (id, name, description, scope, resource_type, is_system_permission) VALUES
        (gen_random_uuid(), 'system.admin', 'Full system administration access', 'global', NULL, true),
        (gen_random_uuid(), 'user.read', 'Read user information', 'tenant', 'user', true),
        (gen_random_uuid(), 'user.write', 'Create and modify users', 'tenant', 'user', true),
        (gen_random_uuid(), 'user.delete', 'Delete users', 'tenant', 'user', true),
        (gen_random_uuid(), 'role.read', 'Read role information', 'tenant', 'role', true),
        (gen_random_uuid(), 'role.write', 'Create and modify roles', 'tenant', 'role', true),
        (gen_random_uuid(), 'role.delete', 'Delete roles', 'tenant', 'role', true),
        (gen_random_uuid(), 'project.read', 'Read project data', 'resource', 'project', true),
        (gen_random_uuid(), 'project.write', 'Modify project data', 'resource', 'project', true),
        (gen_random_uuid(), 'project.delete', 'Delete projects', 'resource', 'project', true),
        (gen_random_uuid(), 'dataset.read', 'Read dataset data', 'resource', 'dataset', true),
        (gen_random_uuid(), 'dataset.write', 'Modify dataset data', 'resource', 'dataset', true),
        (gen_random_uuid(), 'dataset.delete', 'Delete datasets', 'resource', 'dataset', true),
        (gen_random_uuid(), 'audit.read', 'Read audit logs', 'tenant', 'audit_log', true),
        (gen_random_uuid(), 'audit.export', 'Export audit logs', 'tenant', 'audit_log', true),
        (gen_random_uuid(), 'desensitization.read', 'Read desensitization rules', 'tenant', NULL, true),
        (gen_random_uuid(), 'desensitization.write', 'Manage desensitization rules', 'tenant', NULL, true)
    """)


def downgrade():
    """Remove RBAC tables."""
    
    # Drop tables in reverse order
    op.drop_table('rbac_permission_group_members')
    op.drop_table('rbac_permission_groups')
    op.drop_table('rbac_resource_permissions')
    op.drop_table('rbac_resources')
    op.drop_table('rbac_user_roles')
    op.drop_table('rbac_role_permissions')
    op.drop_table('rbac_permissions')
    op.drop_table('rbac_roles')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS resourcetype')
    op.execute('DROP TYPE IF EXISTS permissionscope')