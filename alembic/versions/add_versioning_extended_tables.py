"""Add extended versioning tables for change tracking and snapshots

Revision ID: version_lineage_002
Revises: version_lineage_001
Create Date: 2026-01-14 10:00:00.000000

This migration creates additional tables for:
- change_records: Change tracking with before/after snapshots
- snapshots: Point-in-time data snapshots
- snapshot_schedules: Scheduled snapshot configuration

Also adds missing columns to data_versions table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'version_lineage_002'
down_revision = 'version_lineage_001'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================================
    # Create ENUM types for extended versioning
    # ========================================================================
    
    # ChangeType enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE changetype AS ENUM ('create', 'update', 'delete');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # SnapshotType enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE snapshottype AS ENUM ('full', 'incremental');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # ========================================================================
    # Add missing columns to data_versions table
    # ========================================================================
    
    # Add version column (semantic version string)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE data_versions ADD COLUMN IF NOT EXISTS version VARCHAR(20) DEFAULT '1.0.0';
        EXCEPTION
            WHEN duplicate_column THEN null;
        END $$;
    """)
    
    # Add data column (alias for version_data)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE data_versions ADD COLUMN IF NOT EXISTS data JSONB DEFAULT '{}';
        EXCEPTION
            WHEN duplicate_column THEN null;
        END $$;
    """)
    
    # Add message column
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE data_versions ADD COLUMN IF NOT EXISTS message TEXT;
        EXCEPTION
            WHEN duplicate_column THEN null;
        END $$;
    """)
    
    # Add tags column
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE data_versions ADD COLUMN IF NOT EXISTS tags VARCHAR(100)[] DEFAULT '{}';
        EXCEPTION
            WHEN duplicate_column THEN null;
        END $$;
    """)

    # ========================================================================
    # Create change_records table
    # ========================================================================
    op.create_table('change_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('change_type', postgresql.ENUM('create', 'update', 'delete',
                  name='changetype', create_type=False), nullable=False),
        sa.Column('old_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('diff', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True, server_default='{}'),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for change_records
    op.create_index('idx_change_records_entity', 'change_records',
                    ['entity_type', 'entity_id'])
    op.create_index('idx_change_records_user', 'change_records', ['user_id'])
    op.create_index('idx_change_records_tenant', 'change_records', ['tenant_id'])
    op.create_index('idx_change_records_created', 'change_records', ['created_at'])
    op.create_index('idx_change_records_type', 'change_records', ['change_type'])

    # ========================================================================
    # Create snapshots table
    # ========================================================================
    op.create_table('snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('snapshot_type', postgresql.ENUM('full', 'incremental',
                  name='snapshottype', create_type=False), 
                  nullable=True, server_default="'full'"),
        sa.Column('storage_key', sa.String(500), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('parent_snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True, server_default='{}'),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['parent_snapshot_id'], ['snapshots.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for snapshots
    op.create_index('idx_snapshots_entity', 'snapshots',
                    ['entity_type', 'entity_id'])
    op.create_index('idx_snapshots_tenant', 'snapshots', ['tenant_id'])
    op.create_index('idx_snapshots_created', 'snapshots', ['created_at'])
    op.create_index('idx_snapshots_expires', 'snapshots', ['expires_at'])

    # ========================================================================
    # Create snapshot_schedules table
    # ========================================================================
    op.create_table('snapshot_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('schedule', sa.String(100), nullable=False),
        sa.Column('snapshot_type', postgresql.ENUM('full', 'incremental',
                  name='snapshottype', create_type=False),
                  nullable=True, server_default="'full'"),
        sa.Column('enabled', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('retention_days', sa.Integer(), nullable=True, server_default='90'),
        sa.Column('max_snapshots', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for snapshot_schedules
    op.create_index('idx_snapshot_schedules_entity', 'snapshot_schedules',
                    ['entity_type', 'entity_id'])
    op.create_index('idx_snapshot_schedules_next_run', 'snapshot_schedules',
                    ['next_run_at'])
    op.create_index('idx_snapshot_schedules_tenant', 'snapshot_schedules',
                    ['tenant_id'])
    op.create_unique_constraint('uq_snapshot_schedule_entity', 'snapshot_schedules',
                               ['entity_type', 'entity_id', 'tenant_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('snapshot_schedules')
    op.drop_table('snapshots')
    op.drop_table('change_records')
    
    # Remove added columns from data_versions
    op.execute("ALTER TABLE data_versions DROP COLUMN IF EXISTS version")
    op.execute("ALTER TABLE data_versions DROP COLUMN IF EXISTS data")
    op.execute("ALTER TABLE data_versions DROP COLUMN IF EXISTS message")
    op.execute("ALTER TABLE data_versions DROP COLUMN IF EXISTS tags")
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS snapshottype")
    op.execute("DROP TYPE IF EXISTS changetype")
