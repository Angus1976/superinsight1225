"""Add sync pipeline models

Revision ID: sync_pipeline_001
Revises: 
Create Date: 2026-01-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'sync_pipeline_001'
down_revision = None
branch_labels = ('sync_pipeline',)
depends_on = None


def upgrade() -> None:
    # Create sync_data_sources table
    op.create_table(
        'sync_data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('db_type', sa.String(50), nullable=False),
        sa.Column('host', sa.String(500), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('database', sa.String(200), nullable=False),
        sa.Column('username', sa.String(200), nullable=False),
        sa.Column('password_encrypted', sa.Text(), nullable=False),
        sa.Column('connection_method', sa.String(20), server_default='jdbc'),
        sa.Column('extra_params', postgresql.JSONB(), server_default='{}'),
        sa.Column('save_strategy', sa.String(20), server_default='persistent'),
        sa.Column('save_config', postgresql.JSONB(), server_default='{}'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_connected_at', sa.DateTime(), nullable=True),
        sa.Column('connection_status', sa.String(50), server_default='unknown'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_data_sources_tenant_id', 'sync_data_sources', ['tenant_id'])
    
    # Create sync_checkpoints table
    op.create_table(
        'sync_checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('checkpoint_field', sa.String(200), nullable=False),
        sa.Column('last_value', sa.Text(), nullable=True),
        sa.Column('last_value_type', sa.String(50), server_default='string'),
        sa.Column('last_pull_at', sa.DateTime(), nullable=True),
        sa.Column('rows_pulled', sa.Integer(), server_default='0'),
        sa.Column('query_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['source_id'], ['sync_data_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'checkpoint_field', name='uq_checkpoint_source_field')
    )
    op.create_index('ix_sync_checkpoints_source_id', 'sync_checkpoints', ['source_id'])
    
    # Create sync_jobs table
    op.create_table(
        'sync_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('cron_expression', sa.String(100), nullable=False),
        sa.Column('priority', sa.Integer(), server_default='0'),
        sa.Column('enabled', sa.Boolean(), server_default='true'),
        sa.Column('pull_config', postgresql.JSONB(), server_default='{}'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('total_runs', sa.Integer(), server_default='0'),
        sa.Column('successful_runs', sa.Integer(), server_default='0'),
        sa.Column('failed_runs', sa.Integer(), server_default='0'),
        sa.Column('total_rows_synced', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['source_id'], ['sync_data_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_jobs_source_id', 'sync_jobs', ['source_id'])
    
    # Create sync_history table
    op.create_table(
        'sync_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('rows_synced', sa.Integer(), server_default='0'),
        sa.Column('bytes_processed', sa.Integer(), server_default='0'),
        sa.Column('duration_ms', sa.Float(), server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('checkpoint_value', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['sync_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_history_job_id', 'sync_history', ['job_id'])
    
    # Create sync_semantic_cache table
    op.create_table(
        'sync_semantic_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cache_key', sa.String(64), nullable=False),
        sa.Column('refinement_result', postgresql.JSONB(), nullable=False),
        sa.Column('data_hash', sa.String(64), nullable=True),
        sa.Column('config_hash', sa.String(64), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('hit_count', sa.Integer(), server_default='0'),
        sa.Column('last_hit_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key')
    )
    op.create_index('ix_sync_semantic_cache_cache_key', 'sync_semantic_cache', ['cache_key'])
    op.create_index('ix_sync_semantic_cache_expires_at', 'sync_semantic_cache', ['expires_at'])
    
    # Create sync_export_records table
    op.create_table(
        'sync_export_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('export_format', sa.String(20), nullable=False),
        sa.Column('config', postgresql.JSONB(), server_default='{}'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('file_paths', postgresql.JSONB(), server_default='[]'),
        sa.Column('statistics', postgresql.JSONB(), server_default='{}'),
        sa.Column('total_rows', sa.Integer(), server_default='0'),
        sa.Column('total_size_bytes', sa.Integer(), server_default='0'),
        sa.Column('duration_ms', sa.Float(), server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sync_data_sources.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_export_records_source_id', 'sync_export_records', ['source_id'])
    
    # Create sync_idempotency_records table
    op.create_table(
        'sync_idempotency_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('idempotency_key', sa.String(255), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('request_hash', sa.String(64), nullable=True),
        sa.Column('rows_received', sa.Integer(), server_default='0'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('ix_sync_idempotency_records_idempotency_key', 'sync_idempotency_records', ['idempotency_key'])
    op.create_index('ix_sync_idempotency_records_expires_at', 'sync_idempotency_records', ['expires_at'])
    
    # Create sync_synced_data table
    op.create_table(
        'sync_synced_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('batch_id', sa.String(64), nullable=False),
        sa.Column('batch_sequence', sa.Integer(), server_default='0'),
        sa.Column('data', postgresql.JSONB(), nullable=False),
        sa.Column('row_count', sa.Integer(), server_default='0'),
        sa.Column('sync_type', sa.String(20), server_default='pull'),
        sa.Column('checkpoint_value', sa.Text(), nullable=True),
        sa.Column('is_refined', sa.Boolean(), server_default='false'),
        sa.Column('refinement_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['source_id'], ['sync_data_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id', 'batch_sequence', name='uq_synced_data_batch_seq')
    )
    op.create_index('ix_sync_synced_data_source_id', 'sync_synced_data', ['source_id'])
    op.create_index('ix_sync_synced_data_batch_id', 'sync_synced_data', ['batch_id'])


def downgrade() -> None:
    op.drop_table('sync_synced_data')
    op.drop_table('sync_idempotency_records')
    op.drop_table('sync_export_records')
    op.drop_table('sync_semantic_cache')
    op.drop_table('sync_history')
    op.drop_table('sync_jobs')
    op.drop_table('sync_checkpoints')
    op.drop_table('sync_data_sources')
