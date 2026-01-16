"""Add data version control and lineage tracking tables

Revision ID: version_lineage_001
Revises: sync_001
Create Date: 2026-01-12 10:00:00.000000

This migration creates tables for:
- data_versions: Version history for all data entities
- data_version_tags: Version tagging support
- data_version_branches: Version branching support
- data_lineage_records: Persistent lineage tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'version_lineage_001'
down_revision = 'sync_001'
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================================
    # Create ENUM types for version control
    # ========================================================================
    
    # VersionStatus enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE versionstatus AS ENUM (
            'active', 'archived', 'deleted', 'pending'
        );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # VersionType enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE versiontype AS ENUM (
            'full', 'delta', 'checkpoint'
        );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # LineageRelationType enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE lineagerelationtype AS ENUM (
            'derived_from', 'transformed_to', 'copied_from',
            'aggregated_from', 'filtered_from', 'joined_from', 'enriched_by'
        );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # ========================================================================
    # Create data_version_branches table (must be created first for FK)
    # ========================================================================
    op.create_table('data_version_branches',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, 
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('base_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_merged', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('merged_to_branch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('merged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_branches_entity', 'data_version_branches', 
                    ['entity_type', 'entity_id'])
    op.create_index('idx_branches_tenant', 'data_version_branches', ['tenant_id'])
    op.create_unique_constraint('uq_entity_branch_name', 'data_version_branches',
                               ['entity_type', 'entity_id', 'name', 'tenant_id'])

    # ========================================================================
    # Create data_versions table
    # ========================================================================
    op.create_table('data_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('version_type', postgresql.ENUM('full', 'delta', 'checkpoint',
                  name='versiontype', create_type=False), nullable=True,
                  server_default="'full'"),
        sa.Column('status', postgresql.ENUM('active', 'archived', 'deleted', 'pending',
                  name='versionstatus', create_type=False), nullable=True,
                  server_default="'active'"),
        sa.Column('parent_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version_data', postgresql.JSONB(astext_type=sa.Text()), 
                  nullable=False, server_default='{}'),
        sa.Column('delta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('data_size_bytes', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('version_metadata', postgresql.JSONB(astext_type=sa.Text()), 
                  nullable=True, server_default='{}'),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['parent_version_id'], ['data_versions.id']),
        sa.ForeignKeyConstraint(['branch_id'], ['data_version_branches.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for data_versions
    op.create_index('idx_data_versions_entity', 'data_versions', 
                    ['entity_type', 'entity_id'])
    op.create_index('idx_data_versions_tenant', 'data_versions', 
                    ['tenant_id', 'workspace_id'])
    op.create_index('idx_data_versions_created', 'data_versions', ['created_at'])
    op.create_index('idx_data_versions_entity_version', 'data_versions',
                    ['entity_type', 'entity_id', 'version_number'])
    op.create_unique_constraint('uq_entity_version_branch', 'data_versions',
                               ['entity_type', 'entity_id', 'version_number', 'branch_id'])
    
    # GIN index for JSONB queries
    op.execute("""
        CREATE INDEX idx_data_versions_metadata_gin 
        ON data_versions USING GIN (version_metadata)
    """)
    op.execute("""
        CREATE INDEX idx_data_versions_data_gin 
        ON data_versions USING GIN (version_data)
    """)

    # ========================================================================
    # Create data_version_tags table
    # ========================================================================
    op.create_table('data_version_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['version_id'], ['data_versions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_version_tags_tenant', 'data_version_tags', ['tenant_id'])
    op.create_index('idx_version_tags_name', 'data_version_tags', ['tag_name'])
    op.create_unique_constraint('uq_version_tag', 'data_version_tags',
                               ['version_id', 'tag_name'])

    # ========================================================================
    # Create data_lineage_records table
    # ========================================================================
    op.create_table('data_lineage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_entity_type', sa.String(100), nullable=False),
        sa.Column('source_entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('target_entity_type', sa.String(100), nullable=False),
        sa.Column('target_entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('relationship_type', postgresql.ENUM(
            'derived_from', 'transformed_to', 'copied_from',
            'aggregated_from', 'filtered_from', 'joined_from', 'enriched_by',
            name='lineagerelationtype', create_type=False), nullable=False),
        sa.Column('transformation_info', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True, server_default='{}'),
        sa.Column('source_columns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('target_columns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sync_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['source_version_id'], ['data_versions.id']),
        sa.ForeignKeyConstraint(['target_version_id'], ['data_versions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for lineage queries
    op.create_index('idx_lineage_source', 'data_lineage_records',
                    ['source_entity_type', 'source_entity_id'])
    op.create_index('idx_lineage_target', 'data_lineage_records',
                    ['target_entity_type', 'target_entity_id'])
    op.create_index('idx_lineage_tenant', 'data_lineage_records', ['tenant_id'])
    op.create_index('idx_lineage_created', 'data_lineage_records', ['created_at'])
    op.create_index('idx_lineage_sync_job', 'data_lineage_records', ['sync_job_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('data_lineage_records')
    op.drop_table('data_version_tags')
    op.drop_table('data_versions')
    op.drop_table('data_version_branches')
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS lineagerelationtype")
    op.execute("DROP TYPE IF EXISTS versiontype")
    op.execute("DROP TYPE IF EXISTS versionstatus")
