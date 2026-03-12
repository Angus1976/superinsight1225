"""Extend sync models for bidirectional sync support

Revision ID: 032_extend_sync_models_for_bidirectional_sync
Revises: 031_add_ai_data_source_role_permission
Create Date: 2026-03-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '032_extend_sync_models_for_bidirectional_sync'
down_revision = '031_add_ai_data_source_role_permission'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add bidirectional sync fields to sync_jobs and sync_executions tables."""
    
    # Extend sync_jobs table
    op.add_column('sync_jobs', sa.Column('target_source_id', UUID(as_uuid=True), nullable=True))
    op.add_column('sync_jobs', sa.Column('field_mapping_rules', JSONB, nullable=True))
    op.add_column('sync_jobs', sa.Column('output_sync_strategy', sa.String(50), nullable=True))
    op.add_column('sync_jobs', sa.Column('output_checkpoint', JSONB, nullable=True))
    
    # Add foreign key constraint for target_source_id
    op.create_foreign_key(
        'fk_sync_jobs_target_source_id',
        'sync_jobs',
        'data_sources',
        ['target_source_id'],
        ['id']
    )
    
    # Extend sync_executions table
    op.add_column('sync_executions', sa.Column('sync_direction', sa.String(50), nullable=True))
    op.add_column('sync_executions', sa.Column('rows_written', sa.BigInteger, nullable=True, server_default='0'))
    op.add_column('sync_executions', sa.Column('write_errors', JSONB, nullable=True))


def downgrade() -> None:
    """Remove bidirectional sync fields from sync_jobs and sync_executions tables."""
    
    # Remove columns from sync_executions
    op.drop_column('sync_executions', 'write_errors')
    op.drop_column('sync_executions', 'rows_written')
    op.drop_column('sync_executions', 'sync_direction')
    
    # Remove foreign key constraint and columns from sync_jobs
    op.drop_constraint('fk_sync_jobs_target_source_id', 'sync_jobs', type_='foreignkey')
    op.drop_column('sync_jobs', 'output_checkpoint')
    op.drop_column('sync_jobs', 'output_sync_strategy')
    op.drop_column('sync_jobs', 'field_mapping_rules')
    op.drop_column('sync_jobs', 'target_source_id')
