"""Add Label Studio sync tracking fields to tasks table

Revision ID: 018_add_label_studio_sync_fields
Revises: 017_ontology_expert_collab
Create Date: 2026-01-26 10:00:00.000000

This migration adds Label Studio integration fields to the tasks table
for tracking synchronization status between SuperInsight and Label Studio.

Fields added:
- label_studio_project_id: String(50), nullable, indexed - Label Studio project ID
- label_studio_project_created_at: DateTime, nullable - When the LS project was created
- label_studio_sync_status: Enum (pending/synced/failed), default=pending - Sync status
- label_studio_last_sync: DateTime, nullable - Last successful sync timestamp
- label_studio_task_count: Integer, default=0 - Number of tasks in Label Studio
- label_studio_annotation_count: Integer, default=0 - Number of annotations completed

Validates: Requirements 1.4 (Task Data Synchronization)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '018_add_label_studio_sync_fields'
down_revision: Union[str, Sequence[str], None] = '017_ontology_expert_collab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define the enum type for Label Studio sync status
label_studio_sync_status_enum = postgresql.ENUM(
    'pending', 'synced', 'failed',
    name='labelstudiosyncstatus',
    create_type=False
)


def upgrade() -> None:
    """Add Label Studio sync tracking fields to tasks table."""
    
    # Create the enum type first (if it doesn't exist)
    label_studio_sync_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Add label_studio_project_id column with index
    try:
        op.add_column(
            'tasks',
            sa.Column('label_studio_project_id', sa.String(50), nullable=True)
        )
        op.create_index(
            op.f('ix_tasks_label_studio_project_id'),
            'tasks',
            ['label_studio_project_id'],
            unique=False
        )
    except Exception:
        pass  # Column might already exist
    
    # Add label_studio_project_created_at column
    try:
        op.add_column(
            'tasks',
            sa.Column(
                'label_studio_project_created_at',
                sa.DateTime(timezone=True),
                nullable=True
            )
        )
    except Exception:
        pass  # Column might already exist
    
    # Add label_studio_sync_status column with enum type
    try:
        op.add_column(
            'tasks',
            sa.Column(
                'label_studio_sync_status',
                label_studio_sync_status_enum,
                nullable=True,
                server_default='pending'
            )
        )
    except Exception:
        pass  # Column might already exist
    
    # Add label_studio_last_sync column
    try:
        op.add_column(
            'tasks',
            sa.Column(
                'label_studio_last_sync',
                sa.DateTime(timezone=True),
                nullable=True
            )
        )
    except Exception:
        pass  # Column might already exist
    
    # Add label_studio_task_count column
    try:
        op.add_column(
            'tasks',
            sa.Column(
                'label_studio_task_count',
                sa.Integer(),
                nullable=False,
                server_default='0'
            )
        )
    except Exception:
        pass  # Column might already exist
    
    # Add label_studio_annotation_count column
    try:
        op.add_column(
            'tasks',
            sa.Column(
                'label_studio_annotation_count',
                sa.Integer(),
                nullable=False,
                server_default='0'
            )
        )
    except Exception:
        pass  # Column might already exist


def downgrade() -> None:
    """Remove Label Studio sync tracking fields from tasks table."""
    
    # Remove columns in reverse order
    try:
        op.drop_column('tasks', 'label_studio_annotation_count')
    except Exception:
        pass
    
    try:
        op.drop_column('tasks', 'label_studio_task_count')
    except Exception:
        pass
    
    try:
        op.drop_column('tasks', 'label_studio_last_sync')
    except Exception:
        pass
    
    try:
        op.drop_column('tasks', 'label_studio_sync_status')
    except Exception:
        pass
    
    try:
        op.drop_column('tasks', 'label_studio_project_created_at')
    except Exception:
        pass
    
    try:
        op.drop_index(op.f('ix_tasks_label_studio_project_id'), table_name='tasks')
        op.drop_column('tasks', 'label_studio_project_id')
    except Exception:
        pass
    
    # Drop the enum type (only if no other tables use it)
    try:
        label_studio_sync_status_enum.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass  # Enum might be in use by other tables or already dropped
