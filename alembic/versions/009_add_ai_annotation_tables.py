"""Add AI annotation tables

Revision ID: 009_ai_annotation
Revises: 008_add_llm_integration
Create Date: 2026-01-14

This migration adds tables for AI annotation features:
- annotation_plugins: Third-party annotation tool configurations
- plugin_call_logs: Plugin call statistics and logs
- review_records: Annotation review history
- pre_annotation_jobs: Batch pre-annotation jobs
- pre_annotation_results: Individual pre-annotation results
- coverage_records: Auto-coverage records
- task_assignments: Task assignment for collaboration
- validation_reports: Post-validation reports
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_ai_annotation'
down_revision = '008_add_llm_integration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    connection_type_enum = postgresql.ENUM(
        'rest_api', 'grpc', 'webhook',
        name='connection_type_enum',
        create_type=False
    )
    
    review_status_enum = postgresql.ENUM(
        'pending', 'in_review', 'approved', 'rejected', 'modification_requested',
        name='review_status_enum',
        create_type=False
    )
    
    review_action_enum = postgresql.ENUM(
        'approve', 'reject', 'modify',
        name='review_action_enum',
        create_type=False
    )
    
    annotation_type_enum = postgresql.ENUM(
        'text_classification', 'ner', 'sentiment', 'relation_extraction',
        'sequence_labeling', 'qa', 'summarization',
        name='annotation_type_enum',
        create_type=False
    )
    
    pre_annotation_status_enum = postgresql.ENUM(
        'pending', 'running', 'completed', 'failed', 'cancelled',
        name='pre_annotation_status_enum',
        create_type=False
    )
    
    user_role_enum = postgresql.ENUM(
        'annotator', 'expert', 'contractor', 'reviewer',
        name='user_role_enum',
        create_type=False
    )
    
    # Create enums
    connection_type_enum.create(op.get_bind(), checkfirst=True)
    review_status_enum.create(op.get_bind(), checkfirst=True)
    review_action_enum.create(op.get_bind(), checkfirst=True)
    annotation_type_enum.create(op.get_bind(), checkfirst=True)
    pre_annotation_status_enum.create(op.get_bind(), checkfirst=True)
    user_role_enum.create(op.get_bind(), checkfirst=True)
    
    # Create annotation_plugins table
    op.create_table(
        'annotation_plugins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('version', sa.String(20), default='1.0.0'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('connection_type', connection_type_enum, nullable=False, server_default='rest_api'),
        sa.Column('endpoint', sa.String(500), nullable=True),
        sa.Column('api_key_encrypted', sa.Text, nullable=True),
        sa.Column('timeout', sa.Integer, default=30),
        sa.Column('enabled', sa.Boolean, default=True),
        sa.Column('priority', sa.Integer, default=0),
        sa.Column('supported_types', postgresql.JSONB, server_default='[]'),
        sa.Column('type_mapping', postgresql.JSONB, server_default='{}'),
        sa.Column('extra_config', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    op.create_index('ix_annotation_plugins_tenant_enabled', 'annotation_plugins', ['tenant_id', 'enabled'])
    op.create_index('ix_annotation_plugins_priority', 'annotation_plugins', ['priority'])
    
    # Create plugin_call_logs table
    op.create_table(
        'plugin_call_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plugin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('annotation_plugins.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_count', sa.Integer, default=0),
        sa.Column('success', sa.Boolean, default=True),
        sa.Column('latency_ms', sa.Float, default=0),
        sa.Column('cost', sa.Float, default=0),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('request_data', postgresql.JSONB, nullable=True),
        sa.Column('response_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    op.create_index('ix_plugin_call_logs_plugin_created', 'plugin_call_logs', ['plugin_id', 'created_at'])
    op.create_index('ix_plugin_call_logs_success', 'plugin_call_logs', ['success'])
    
    # Create review_records table
    op.create_table(
        'review_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('annotator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', review_status_enum, nullable=False, server_default='pending'),
        sa.Column('action', review_action_enum, nullable=True),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('modifications', postgresql.JSONB, nullable=True),
        sa.Column('original_annotation', postgresql.JSONB, nullable=True),
        sa.Column('modified_annotation', postgresql.JSONB, nullable=True),
        sa.Column('review_level', sa.Integer, default=1),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    op.create_index('ix_review_records_annotation_status', 'review_records', ['annotation_id', 'status'])
    op.create_index('ix_review_records_reviewer', 'review_records', ['reviewer_id', 'status'])
    op.create_index('ix_review_records_annotator', 'review_records', ['annotator_id'])
    op.create_index('ix_review_records_task', 'review_records', ['task_id'])
    
    # Create pre_annotation_jobs table
    op.create_table(
        'pre_annotation_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('annotation_type', annotation_type_enum, nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('status', pre_annotation_status_enum, server_default='pending'),
        sa.Column('total_tasks', sa.Integer, default=0),
        sa.Column('completed_tasks', sa.Integer, default=0),
        sa.Column('failed_tasks', sa.Integer, default=0),
        sa.Column('needs_review_count', sa.Integer, default=0),
        sa.Column('method_used', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )
    
    op.create_index('ix_pre_annotation_jobs_project_status', 'pre_annotation_jobs', ['project_id', 'status'])
    op.create_index('ix_pre_annotation_jobs_created_by', 'pre_annotation_jobs', ['created_by'])
    op.create_index('ix_pre_annotation_jobs_tenant', 'pre_annotation_jobs', ['tenant_id'])
    
    # Create pre_annotation_results table
    op.create_table(
        'pre_annotation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pre_annotation_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('annotation_data', postgresql.JSONB, nullable=False),
        sa.Column('confidence', sa.Float, default=0),
        sa.Column('needs_review', sa.Boolean, default=False),
        sa.Column('method_used', sa.String(50), nullable=True),
        sa.Column('processing_time_ms', sa.Float, default=0),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('applied', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    op.create_index('ix_pre_annotation_results_job_task', 'pre_annotation_results', ['job_id', 'task_id'])
    op.create_index('ix_pre_annotation_results_needs_review', 'pre_annotation_results', ['needs_review'])
    op.create_index('ix_pre_annotation_results_task', 'pre_annotation_results', ['task_id'])
    
    # Create coverage_records table
    op.create_table(
        'coverage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_sample_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pattern_id', sa.String(100), nullable=True),
        sa.Column('similarity_score', sa.Float, nullable=False),
        sa.Column('annotation_data', postgresql.JSONB, nullable=False),
        sa.Column('auto_covered', sa.Boolean, default=True),
        sa.Column('reviewed', sa.Boolean, default=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('review_status', review_status_enum, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
    )
    
    op.create_index('ix_coverage_records_project_task', 'coverage_records', ['project_id', 'task_id'])
    op.create_index('ix_coverage_records_reviewed', 'coverage_records', ['reviewed'])
    op.create_unique_constraint('uq_coverage_records_task', 'coverage_records', ['task_id'])
    
    # Create task_assignments table
    op.create_table(
        'task_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('priority', sa.Integer, default=1),
        sa.Column('deadline', sa.DateTime, nullable=True),
        sa.Column('assigned_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
    )
    
    op.create_index('ix_task_assignments_user_status', 'task_assignments', ['user_id', 'status'])
    op.create_index('ix_task_assignments_project', 'task_assignments', ['project_id'])
    op.create_index('ix_task_assignments_task', 'task_assignments', ['task_id'])
    op.create_unique_constraint('uq_task_assignments_task_user', 'task_assignments', ['task_id', 'user_id'])
    
    # Create validation_reports table
    op.create_table(
        'validation_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('overall_score', sa.Float, default=0),
        sa.Column('accuracy', sa.Float, default=0),
        sa.Column('recall', sa.Float, default=0),
        sa.Column('consistency', sa.Float, default=0),
        sa.Column('completeness', sa.Float, default=0),
        sa.Column('dimension_scores', postgresql.JSONB, server_default='{}'),
        sa.Column('issues', postgresql.JSONB, server_default='[]'),
        sa.Column('recommendations', postgresql.JSONB, server_default='[]'),
        sa.Column('total_annotations', sa.Integer, default=0),
        sa.Column('config', postgresql.JSONB, server_default='{}'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    op.create_index('ix_validation_reports_project', 'validation_reports', ['project_id'])
    op.create_index('ix_validation_reports_created_at', 'validation_reports', ['created_at'])
    op.create_index('ix_validation_reports_tenant', 'validation_reports', ['tenant_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('validation_reports')
    op.drop_table('task_assignments')
    op.drop_table('coverage_records')
    op.drop_table('pre_annotation_results')
    op.drop_table('pre_annotation_jobs')
    op.drop_table('review_records')
    op.drop_table('plugin_call_logs')
    op.drop_table('annotation_plugins')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS user_role_enum')
    op.execute('DROP TYPE IF EXISTS pre_annotation_status_enum')
    op.execute('DROP TYPE IF EXISTS annotation_type_enum')
    op.execute('DROP TYPE IF EXISTS review_action_enum')
    op.execute('DROP TYPE IF EXISTS review_status_enum')
    op.execute('DROP TYPE IF EXISTS connection_type_enum')
