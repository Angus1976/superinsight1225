"""Add extended task management fields

Revision ID: 020_add_extended_task_fields
Revises: 019_add_ls_workspace_tables
Create Date: 2026-01-30 10:00:00.000000

This migration extends the tasks table with comprehensive task management fields:
- name, description: Basic task information
- priority, annotation_type: Task categorization
- assignee_id, created_by: Assignment and ownership
- progress, total_items, completed_items: Progress tracking
- updated_at, due_date: Timestamp management
- tags, task_metadata: Additional metadata

Validates: Requirements 1.1, 1.2, 1.3 (Task Persistence, Task Management, Unified Data Model)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '020_add_extended_task_fields'
down_revision: Union[str, Sequence[str], None] = '019_add_ls_workspace_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define enum types
task_priority_enum = postgresql.ENUM(
    'low', 'medium', 'high', 'urgent',
    name='taskpriority',
    create_type=False
)

annotation_type_enum = postgresql.ENUM(
    'text_classification', 'ner', 'sentiment', 'qa', 'custom',
    name='annotationtype',
    create_type=False
)


def upgrade() -> None:
    """Add extended task management fields to tasks table."""

    # Create enum types
    task_priority_enum.create(op.get_bind(), checkfirst=True)
    annotation_type_enum.create(op.get_bind(), checkfirst=True)

    # Add 'cancelled' to taskstatus enum if not exists
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'cancelled'
                           AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'taskstatus')) THEN
                ALTER TYPE taskstatus ADD VALUE 'cancelled';
            END IF;
        END
        $$;
    """)

    # Add new columns to tasks table (all nullable initially for migration safety)

    # Basic task information
    op.add_column('tasks', sa.Column('name', sa.String(255), nullable=True))
    op.add_column('tasks', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('tasks', sa.Column('priority', task_priority_enum, nullable=True))
    op.add_column('tasks', sa.Column('annotation_type', annotation_type_enum, nullable=True))

    # Assignment and ownership
    op.add_column('tasks', sa.Column('assignee_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('tasks', sa.Column('created_by', sa.String(100), nullable=True))

    # Progress tracking
    op.add_column('tasks', sa.Column('progress', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('total_items', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('completed_items', sa.Integer(), nullable=True))

    # Timestamps
    op.add_column('tasks', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tasks', sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))

    # Additional metadata
    op.add_column('tasks', sa.Column('tags', postgresql.JSONB(), nullable=True))
    op.add_column('tasks', sa.Column('task_metadata', postgresql.JSONB(), nullable=True))

    # Make document_id nullable (not all tasks need a document)
    op.alter_column('tasks', 'document_id', existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    # Fill default values for existing rows
    op.execute("""
        UPDATE tasks SET
            name = COALESCE(name, 'Task ' || SUBSTRING(id::text, 1, 8)),
            description = COALESCE(description, ''),
            priority = COALESCE(priority, 'medium'),
            annotation_type = COALESCE(annotation_type, 'custom'),
            created_by = COALESCE(created_by, 'system'),
            progress = COALESCE(progress, 0),
            total_items = COALESCE(total_items, 1),
            completed_items = COALESCE(completed_items, 0),
            updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP),
            tags = COALESCE(tags, '[]'::jsonb),
            task_metadata = COALESCE(task_metadata, '{}'::jsonb),
            tenant_id = COALESCE(tenant_id, 'default_tenant')
        WHERE name IS NULL OR priority IS NULL OR annotation_type IS NULL
    """)

    # Set NOT NULL constraints after data population
    op.alter_column('tasks', 'name', existing_type=sa.String(255), nullable=False)
    op.alter_column('tasks', 'created_by', existing_type=sa.String(100), nullable=False)
    op.alter_column('tasks', 'tenant_id', existing_type=sa.String(100), nullable=False)

    # Set default values
    op.alter_column('tasks', 'priority', server_default='medium')
    op.alter_column('tasks', 'annotation_type', server_default='custom')
    op.alter_column('tasks', 'progress', server_default='0')
    op.alter_column('tasks', 'total_items', server_default='1')
    op.alter_column('tasks', 'completed_items', server_default='0')
    op.alter_column('tasks', 'tags', server_default='[]')
    op.alter_column('tasks', 'task_metadata', server_default='{}')

    # Create foreign key for assignee_id
    op.create_foreign_key(
        'fk_tasks_assignee_id',
        'tasks', 'users',
        ['assignee_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create indexes for better query performance
    op.create_index('idx_tasks_name', 'tasks', ['name'])
    op.create_index('idx_tasks_priority', 'tasks', ['priority'])
    op.create_index('idx_tasks_annotation_type', 'tasks', ['annotation_type'])
    op.create_index('idx_tasks_assignee_id', 'tasks', ['assignee_id'])
    op.create_index('idx_tasks_created_by', 'tasks', ['created_by'])
    op.create_index('idx_tasks_due_date', 'tasks', ['due_date'])
    op.create_index('idx_tasks_updated_at', 'tasks', ['updated_at'])
    op.create_index('idx_tasks_status_priority', 'tasks', ['status', 'priority'])
    op.create_index('idx_tasks_tenant_status', 'tasks', ['tenant_id', 'status'])

    # Create trigger for automatic updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_tasks_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
        CREATE TRIGGER update_tasks_updated_at
            BEFORE UPDATE ON tasks
            FOR EACH ROW
            EXECUTE FUNCTION update_tasks_updated_at_column();
    """)


def downgrade() -> None:
    """Remove extended task management fields from tasks table."""

    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks")
    op.execute("DROP FUNCTION IF EXISTS update_tasks_updated_at_column()")

    # Drop indexes
    op.drop_index('idx_tasks_tenant_status', table_name='tasks')
    op.drop_index('idx_tasks_status_priority', table_name='tasks')
    op.drop_index('idx_tasks_updated_at', table_name='tasks')
    op.drop_index('idx_tasks_due_date', table_name='tasks')
    op.drop_index('idx_tasks_created_by', table_name='tasks')
    op.drop_index('idx_tasks_assignee_id', table_name='tasks')
    op.drop_index('idx_tasks_annotation_type', table_name='tasks')
    op.drop_index('idx_tasks_priority', table_name='tasks')
    op.drop_index('idx_tasks_name', table_name='tasks')

    # Drop foreign key
    op.drop_constraint('fk_tasks_assignee_id', 'tasks', type_='foreignkey')

    # Drop columns
    op.drop_column('tasks', 'task_metadata')
    op.drop_column('tasks', 'tags')
    op.drop_column('tasks', 'due_date')
    op.drop_column('tasks', 'updated_at')
    op.drop_column('tasks', 'completed_items')
    op.drop_column('tasks', 'total_items')
    op.drop_column('tasks', 'progress')
    op.drop_column('tasks', 'created_by')
    op.drop_column('tasks', 'assignee_id')
    op.drop_column('tasks', 'annotation_type')
    op.drop_column('tasks', 'priority')
    op.drop_column('tasks', 'description')
    op.drop_column('tasks', 'name')

    # Make document_id required again
    op.alter_column('tasks', 'document_id', existing_type=postgresql.UUID(as_uuid=True), nullable=False)

    # Drop enum types
    try:
        annotation_type_enum.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass

    try:
        task_priority_enum.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass
