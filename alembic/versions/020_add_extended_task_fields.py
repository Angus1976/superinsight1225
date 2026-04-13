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

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("tasks"):
        return

    task_cols = {c["name"] for c in insp.get_columns("tasks")}

    # Create enum types
    task_priority_enum.create(bind, checkfirst=True)
    annotation_type_enum.create(bind, checkfirst=True)

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'taskstatus') THEN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'taskstatus' AND e.enumlabel = 'cancelled'
                ) THEN
                    ALTER TYPE taskstatus ADD VALUE 'cancelled';
                END IF;
            END IF;
        END
        $$;
    """)

    # 000_core_tables 已含 title/description/assignee_id/priority(int)/due_date/updated_at 等，按列名跳过重复添加
    if "name" not in task_cols:
        op.add_column("tasks", sa.Column("name", sa.String(255), nullable=True))
        if "title" in task_cols:
            op.execute("UPDATE tasks SET name = title WHERE name IS NULL")
        op.execute(
            "UPDATE tasks SET name = COALESCE(name, 'Task ' || SUBSTRING(id::text, 1, 8))"
        )
        task_cols.add("name")

    if "description" not in task_cols:
        op.add_column("tasks", sa.Column("description", sa.Text(), nullable=True))
        task_cols.add("description")

    if "priority" not in task_cols:
        op.add_column("tasks", sa.Column("priority", task_priority_enum, nullable=True))
        task_cols.add("priority")

    if "annotation_type" not in task_cols:
        op.add_column(
            "tasks", sa.Column("annotation_type", annotation_type_enum, nullable=True)
        )
        task_cols.add("annotation_type")

    if "assignee_id" not in task_cols:
        op.add_column(
            "tasks", sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        task_cols.add("assignee_id")

    if "created_by" not in task_cols:
        op.add_column("tasks", sa.Column("created_by", sa.String(100), nullable=True))
        task_cols.add("created_by")

    for col, typ in (
        ("progress", sa.Integer()),
        ("total_items", sa.Integer()),
        ("completed_items", sa.Integer()),
    ):
        if col not in task_cols:
            op.add_column("tasks", sa.Column(col, typ, nullable=True))
            task_cols.add(col)

    if "updated_at" not in task_cols:
        op.add_column(
            "tasks", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
        )
        task_cols.add("updated_at")

    if "due_date" not in task_cols:
        op.add_column(
            "tasks", sa.Column("due_date", sa.DateTime(timezone=True), nullable=True)
        )
        task_cols.add("due_date")

    if "tags" not in task_cols:
        op.add_column("tasks", sa.Column("tags", postgresql.JSONB(), nullable=True))
        task_cols.add("tags")

    if "task_metadata" not in task_cols:
        op.add_column("tasks", sa.Column("task_metadata", postgresql.JSONB(), nullable=True))
        task_cols.add("task_metadata")

    op.alter_column(
        "tasks",
        "document_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.execute("""
        UPDATE tasks SET
            created_by = COALESCE(created_by, 'system'),
            progress = COALESCE(progress, 0),
            total_items = COALESCE(total_items, 1),
            completed_items = COALESCE(completed_items, 0),
            updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP),
            tags = COALESCE(tags, '[]'::jsonb),
            task_metadata = COALESCE(task_metadata, '{}'::jsonb),
            tenant_id = COALESCE(tenant_id, 'default_tenant')
    """)
    op.execute("""
        UPDATE tasks SET annotation_type = 'custom'::annotationtype
        WHERE annotation_type IS NULL
    """)

    insp = sa.inspect(bind)
    fk_names = {fk["name"] for fk in insp.get_foreign_keys("tasks")}
    if "fk_tasks_assignee_id" not in fk_names:
        op.create_foreign_key(
            "fk_tasks_assignee_id",
            "tasks",
            "users",
            ["assignee_id"],
            ["id"],
            ondelete="SET NULL",
        )

    existing_idx = {i["name"] for i in insp.get_indexes("tasks")}
    for idx, cols in (
        ("idx_tasks_name", ["name"]),
        ("idx_tasks_priority", ["priority"]),
        ("idx_tasks_annotation_type", ["annotation_type"]),
        ("idx_tasks_assignee_id", ["assignee_id"]),
        ("idx_tasks_created_by", ["created_by"]),
        ("idx_tasks_due_date", ["due_date"]),
        ("idx_tasks_updated_at", ["updated_at"]),
        ("idx_tasks_status_priority", ["status", "priority"]),
        ("idx_tasks_tenant_status", ["tenant_id", "status"]),
    ):
        if idx not in existing_idx:
            op.create_index(idx, "tasks", cols)

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
            EXECUTE PROCEDURE update_tasks_updated_at_column();
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
