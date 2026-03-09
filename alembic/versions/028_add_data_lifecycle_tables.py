"""Add data lifecycle management tables

Revision ID: 028_add_data_lifecycle_tables
Revises: 027_upgrade_embedding_to_vector
Create Date: 2026-02-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '028_add_data_lifecycle_tables'
down_revision = '027_upgrade_embedding_to_vector'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create data lifecycle management tables"""
    
    # Create enums
    op.execute("""
        CREATE TYPE datastate AS ENUM (
            'raw', 'structured', 'temp_stored', 'under_review', 'rejected', 
            'approved', 'in_sample_library', 'annotation_pending', 'annotating', 
            'annotated', 'enhancing', 'enhanced', 'trial_calculation', 'archived'
        )
    """)
    
    op.execute("""
        CREATE TYPE reviewstatus AS ENUM ('pending', 'in_progress', 'approved', 'rejected')
    """)
    
    op.execute("""
        CREATE TYPE taskstatus AS ENUM ('created', 'in_progress', 'completed', 'cancelled')
    """)
    
    op.execute("""
        CREATE TYPE annotationtype AS ENUM (
            'classification', 'entity_recognition', 'relation_extraction', 
            'sentiment_analysis', 'custom'
        )
    """)
    
    op.execute("""
        CREATE TYPE enhancementtype AS ENUM (
            'data_augmentation', 'quality_improvement', 'noise_reduction', 
            'feature_extraction', 'normalization'
        )
    """)
    
    op.execute("""
        CREATE TYPE jobstatus AS ENUM ('queued', 'running', 'completed', 'failed', 'cancelled')
    """)
    
    op.execute("""
        CREATE TYPE trialstatus AS ENUM ('created', 'running', 'completed', 'failed')
    """)
    
    op.execute("""
        CREATE TYPE datastage AS ENUM (
            'temp_table', 'sample_library', 'data_source', 'annotated', 'enhanced'
        )
    """)
    
    op.execute("""
        CREATE TYPE changetype AS ENUM ('initial', 'annotation', 'enhancement', 'correction', 'merge')
    """)
    
    op.execute("""
        CREATE TYPE resourcetype AS ENUM (
            'temp_data', 'sample', 'annotation_task', 'annotated_data', 'enhanced_data', 'trial'
        )
    """)
    
    op.execute("""
        CREATE TYPE action AS ENUM (
            'view', 'edit', 'delete', 'transfer', 'review', 'annotate', 'enhance', 'trial'
        )
    """)
    
    op.execute("""
        CREATE TYPE operationtype AS ENUM (
            'create', 'read', 'update', 'delete', 'transfer', 'state_change'
        )
    """)
    
    op.execute("""
        CREATE TYPE operationresult AS ENUM ('success', 'failure', 'partial')
    """)
    
    # Create temp_data table
    op.create_table(
        'temp_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_document_id', sa.String(255), nullable=False),
        sa.Column('content', postgresql.JSONB, nullable=False),
        sa.Column('state', postgresql.ENUM(name='datastate'), nullable=False),
        sa.Column('uploaded_by', sa.String(255), nullable=False),
        sa.Column('uploaded_at', sa.DateTime, nullable=False),
        sa.Column('review_status', postgresql.ENUM(name='reviewstatus'), nullable=True),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Create indexes for temp_data
    op.create_index('idx_temp_data_state', 'temp_data', ['state'])
    op.create_index('idx_temp_data_uploaded_by', 'temp_data', ['uploaded_by'])
    op.create_index('idx_temp_data_state_user', 'temp_data', ['state', 'uploaded_by'])
    op.create_index('idx_temp_data_created_at', 'temp_data', ['created_at'])
    
    # Create samples table
    op.create_table(
        'samples',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('data_id', sa.String(255), nullable=False),
        sa.Column('content', postgresql.JSONB, nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('quality_overall', sa.Float, nullable=False),
        sa.Column('quality_completeness', sa.Float, nullable=False),
        sa.Column('quality_accuracy', sa.Float, nullable=False),
        sa.Column('quality_consistency', sa.Float, nullable=False),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('usage_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint('quality_overall >= 0 AND quality_overall <= 1', name='check_quality_overall_range'),
        sa.CheckConstraint('quality_completeness >= 0 AND quality_completeness <= 1', name='check_quality_completeness_range'),
        sa.CheckConstraint('quality_accuracy >= 0 AND quality_accuracy <= 1', name='check_quality_accuracy_range'),
        sa.CheckConstraint('quality_consistency >= 0 AND quality_consistency <= 1', name='check_quality_consistency_range'),
        sa.CheckConstraint('version > 0', name='check_version_positive')
    )
    
    # Create indexes for samples
    op.create_index('idx_samples_category', 'samples', ['category'])
    op.create_index('idx_samples_category_quality', 'samples', ['category', 'quality_overall'])
    op.create_index('idx_samples_created_at', 'samples', ['created_at'])
    
    # Create annotation_tasks table
    op.create_table(
        'annotation_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('sample_ids', postgresql.JSONB, nullable=False),
        sa.Column('annotation_type', postgresql.ENUM(name='annotationtype'), nullable=False),
        sa.Column('instructions', sa.Text, nullable=False),
        sa.Column('status', postgresql.ENUM(name='taskstatus'), nullable=False, server_default='created'),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('assigned_to', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('deadline', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('progress_total', sa.Integer, nullable=False, server_default='0'),
        sa.Column('progress_completed', sa.Integer, nullable=False, server_default='0'),
        sa.Column('progress_in_progress', sa.Integer, nullable=False, server_default='0'),
        sa.Column('annotations', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.CheckConstraint('progress_completed >= 0', name='check_progress_completed_positive'),
        sa.CheckConstraint('progress_in_progress >= 0', name='check_progress_in_progress_positive'),
        sa.CheckConstraint('progress_total >= 0', name='check_progress_total_positive')
    )
    
    # Create indexes for annotation_tasks
    op.create_index('idx_annotation_tasks_status', 'annotation_tasks', ['status'])
    op.create_index('idx_annotation_tasks_created_by', 'annotation_tasks', ['created_by'])
    op.create_index('idx_annotation_tasks_status_created', 'annotation_tasks', ['status', 'created_by'])
    op.create_index('idx_annotation_tasks_created_at', 'annotation_tasks', ['created_at'])
    
    # Create enhanced_data table
    op.create_table(
        'enhanced_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('original_data_id', sa.String(255), nullable=False),
        sa.Column('enhancement_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', postgresql.JSONB, nullable=False),
        sa.Column('enhancement_type', postgresql.ENUM(name='enhancementtype'), nullable=False),
        sa.Column('quality_improvement', sa.Float, nullable=False),
        sa.Column('quality_overall', sa.Float, nullable=False),
        sa.Column('quality_completeness', sa.Float, nullable=False),
        sa.Column('quality_accuracy', sa.Float, nullable=False),
        sa.Column('quality_consistency', sa.Float, nullable=False),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('parameters', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint('quality_overall >= 0 AND quality_overall <= 1', name='check_enhanced_quality_overall_range'),
        sa.CheckConstraint('quality_completeness >= 0 AND quality_completeness <= 1', name='check_enhanced_quality_completeness_range'),
        sa.CheckConstraint('quality_accuracy >= 0 AND quality_accuracy <= 1', name='check_enhanced_quality_accuracy_range'),
        sa.CheckConstraint('quality_consistency >= 0 AND quality_consistency <= 1', name='check_enhanced_quality_consistency_range'),
        sa.CheckConstraint('version > 0', name='check_enhanced_version_positive')
    )
    
    # Create indexes for enhanced_data
    op.create_index('idx_enhanced_data_original_id', 'enhanced_data', ['original_data_id'])
    op.create_index('idx_enhanced_data_created_at', 'enhanced_data', ['created_at'])
    
    # Create versions table
    op.create_table(
        'versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('data_id', sa.String(255), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('content', postgresql.JSONB, nullable=False),
        sa.Column('change_type', postgresql.ENUM(name='changetype'), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('parent_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('tags', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.CheckConstraint('version_number > 0', name='check_version_number_positive')
    )
    
    # Create indexes for versions
    op.create_index('idx_versions_data_id', 'versions', ['data_id'])
    op.create_index('idx_versions_data_id_version', 'versions', ['data_id', 'version_number'])
    op.create_index('idx_versions_created_at', 'versions', ['created_at'])
    
    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('resource_type', postgresql.ENUM(name='resourcetype'), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=False),
        sa.Column('actions', postgresql.JSONB, nullable=False),
        sa.Column('granted_by', sa.String(255), nullable=False),
        sa.Column('granted_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}')
    )
    
    # Create indexes for permissions
    op.create_index('idx_permissions_user_id', 'permissions', ['user_id'])
    op.create_index('idx_permissions_user_resource', 'permissions', ['user_id', 'resource_type', 'resource_id'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('operation_type', postgresql.ENUM(name='operationtype'), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('resource_type', postgresql.ENUM(name='resourcetype'), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=False),
        sa.Column('action', postgresql.ENUM(name='action'), nullable=False),
        sa.Column('result', postgresql.ENUM(name='operationresult'), nullable=False),
        sa.Column('duration', sa.Integer, nullable=False),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('details', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Create indexes for audit_logs
    op.create_index('idx_audit_logs_operation_type', 'audit_logs', ['operation_type'])
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('idx_audit_logs_result', 'audit_logs', ['result'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_user_timestamp', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_logs_resource_timestamp', 'audit_logs', ['resource_type', 'timestamp'])


def downgrade() -> None:
    """Drop data lifecycle management tables"""
    
    # Drop tables
    op.drop_table('audit_logs')
    op.drop_table('permissions')
    op.drop_table('versions')
    op.drop_table('enhanced_data')
    op.drop_table('annotation_tasks')
    op.drop_table('samples')
    op.drop_table('temp_data')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS operationresult')
    op.execute('DROP TYPE IF EXISTS operationtype')
    op.execute('DROP TYPE IF EXISTS action')
    op.execute('DROP TYPE IF EXISTS resourcetype')
    op.execute('DROP TYPE IF EXISTS changetype')
    op.execute('DROP TYPE IF EXISTS datastage')
    op.execute('DROP TYPE IF EXISTS trialstatus')
    op.execute('DROP TYPE IF EXISTS jobstatus')
    op.execute('DROP TYPE IF EXISTS enhancementtype')
    op.execute('DROP TYPE IF EXISTS annotationtype')
    op.execute('DROP TYPE IF EXISTS taskstatus')
    op.execute('DROP TYPE IF EXISTS reviewstatus')
    op.execute('DROP TYPE IF EXISTS datastate')
