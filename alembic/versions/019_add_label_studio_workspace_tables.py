"""Add Label Studio Enterprise Workspace tables

Revision ID: 019_add_ls_workspace_tables
Revises: 018_add_label_studio_sync_fields
Create Date: 2026-01-29 10:00:00.000000

This migration adds the Label Studio Enterprise Workspace tables:
- label_studio_workspaces: Workspace management table
- label_studio_workspace_members: Workspace membership with roles
- workspace_projects: Links workspaces to Label Studio projects
- project_members: Project-level member assignments

Tables:
1. label_studio_workspaces
   - Workspace for organizing Label Studio projects
   - Supports soft delete and role-based access control

2. label_studio_workspace_members
   - Links users to workspaces with role assignments
   - Roles: owner, admin, manager, reviewer, annotator

3. workspace_projects
   - Links workspaces to Label Studio projects
   - Stores metadata about the association

4. project_members
   - Project-level member assignments
   - Roles: annotator, reviewer

Validates: Requirements 1, 2, 3 (Workspace Management, Member Management, Project Association)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '019_add_ls_workspace_tables'
down_revision: Union[str, Sequence[str], None] = '018_add_label_studio_sync_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define enum types
workspace_member_role_enum = postgresql.ENUM(
    'owner', 'admin', 'manager', 'reviewer', 'annotator',
    name='workspacememberrole',
    create_type=False
)

project_member_role_enum = postgresql.ENUM(
    'annotator', 'reviewer',
    name='projectmemberrole',
    create_type=False
)


def upgrade() -> None:
    """Create Label Studio Enterprise Workspace tables."""

    # Create enum types
    workspace_member_role_enum.create(op.get_bind(), checkfirst=True)
    project_member_role_enum.create(op.get_bind(), checkfirst=True)

    # 1. Create label_studio_workspaces table
    op.create_table(
        'label_studio_workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('settings', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for label_studio_workspaces
    op.create_index('ix_ls_workspace_name', 'label_studio_workspaces', ['name'], unique=True)
    op.create_index('ix_ls_workspace_owner', 'label_studio_workspaces', ['owner_id'])
    op.create_index('ix_ls_workspace_active', 'label_studio_workspaces', ['is_active', 'is_deleted'])

    # 2. Create label_studio_workspace_members table
    op.create_table(
        'label_studio_workspace_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('label_studio_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', workspace_member_role_enum, nullable=False, server_default='annotator'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create unique constraint and indexes for label_studio_workspace_members
    op.create_unique_constraint('uq_ls_workspace_member', 'label_studio_workspace_members', ['workspace_id', 'user_id'])
    op.create_index('ix_ls_wm_workspace', 'label_studio_workspace_members', ['workspace_id'])
    op.create_index('ix_ls_wm_user', 'label_studio_workspace_members', ['user_id'])
    op.create_index('ix_ls_wm_role', 'label_studio_workspace_members', ['role'])

    # 3. Create workspace_projects table
    op.create_table(
        'workspace_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('label_studio_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('label_studio_project_id', sa.String(100), nullable=False),
        sa.Column('superinsight_project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create unique constraint and indexes for workspace_projects
    op.create_unique_constraint('uq_workspace_ls_project', 'workspace_projects', ['workspace_id', 'label_studio_project_id'])
    op.create_index('ix_wp_workspace', 'workspace_projects', ['workspace_id'])
    op.create_index('ix_wp_ls_project', 'workspace_projects', ['label_studio_project_id'])
    op.create_index('ix_wp_si_project', 'workspace_projects', ['superinsight_project_id'])

    # 4. Create project_members table
    op.create_table(
        'project_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspace_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_role', project_member_role_enum, nullable=False, server_default='annotator'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create unique constraint and indexes for project_members
    op.create_unique_constraint('uq_project_member', 'project_members', ['workspace_project_id', 'user_id'])
    op.create_index('ix_pm_project', 'project_members', ['workspace_project_id'])
    op.create_index('ix_pm_user', 'project_members', ['user_id'])
    op.create_index('ix_pm_role', 'project_members', ['project_role'])


def downgrade() -> None:
    """Drop Label Studio Enterprise Workspace tables."""

    # Drop tables in reverse order (to handle foreign key constraints)

    # 4. Drop project_members table
    op.drop_index('ix_pm_role', table_name='project_members')
    op.drop_index('ix_pm_user', table_name='project_members')
    op.drop_index('ix_pm_project', table_name='project_members')
    op.drop_constraint('uq_project_member', 'project_members', type_='unique')
    op.drop_table('project_members')

    # 3. Drop workspace_projects table
    op.drop_index('ix_wp_si_project', table_name='workspace_projects')
    op.drop_index('ix_wp_ls_project', table_name='workspace_projects')
    op.drop_index('ix_wp_workspace', table_name='workspace_projects')
    op.drop_constraint('uq_workspace_ls_project', 'workspace_projects', type_='unique')
    op.drop_table('workspace_projects')

    # 2. Drop label_studio_workspace_members table
    op.drop_index('ix_ls_wm_role', table_name='label_studio_workspace_members')
    op.drop_index('ix_ls_wm_user', table_name='label_studio_workspace_members')
    op.drop_index('ix_ls_wm_workspace', table_name='label_studio_workspace_members')
    op.drop_constraint('uq_ls_workspace_member', 'label_studio_workspace_members', type_='unique')
    op.drop_table('label_studio_workspace_members')

    # 1. Drop label_studio_workspaces table
    op.drop_index('ix_ls_workspace_active', table_name='label_studio_workspaces')
    op.drop_index('ix_ls_workspace_owner', table_name='label_studio_workspaces')
    op.drop_index('ix_ls_workspace_name', table_name='label_studio_workspaces')
    op.drop_table('label_studio_workspaces')

    # Drop enum types (only if not used by other tables)
    try:
        project_member_role_enum.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass  # Enum might be in use by other tables

    try:
        workspace_member_role_enum.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass  # Enum might be in use by other tables
