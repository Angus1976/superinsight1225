"""add ai annotation workflow tables

Revision ID: ai_annotation_001
Revises: merge_all_heads_2026_01_16
Create Date: 2026-03-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'ai_annotation_001'
down_revision = 'merge_all_heads_2026_01_16'
branch_labels = None
depends_on = None


def upgrade():
    """Create AI annotation workflow tables."""
    
    # Create ai_learning_jobs table
    op.create_table(
        'ai_learning_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('sample_count', sa.Integer(), nullable=False),
        sa.Column('patterns_identified', sa.Integer(), server_default='0'),
        sa.Column('average_confidence', sa.Float(), server_default='0.0'),
        sa.Column('recommended_method', sa.String(), nullable=True),
        sa.Column('progress_percentage', sa.Float(), server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for ai_learning_jobs
    op.create_index('idx_ai_learning_jobs_project', 'ai_learning_jobs', ['project_id'])
    op.create_index('idx_ai_learning_jobs_status', 'ai_learning_jobs', ['status'])
    
    # Create batch_annotation_jobs table
    op.create_table(
        'batch_annotation_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('learning_job_id', sa.String(), nullable=True),
        sa.Column('target_dataset_id', sa.String(), nullable=False),
        sa.Column('annotation_type', sa.String(), nullable=False),
        sa.Column('confidence_threshold', sa.Float(), server_default='0.7'),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('total_count', sa.Integer(), server_default='0'),
        sa.Column('annotated_count', sa.Integer(), server_default='0'),
        sa.Column('needs_review_count', sa.Integer(), server_default='0'),
        sa.Column('average_confidence', sa.Float(), server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['learning_job_id'], ['ai_learning_jobs.id'], ondelete='SET NULL')
    )
    
    # Create indexes for batch_annotation_jobs
    op.create_index('idx_batch_annotation_jobs_project', 'batch_annotation_jobs', ['project_id'])
    op.create_index('idx_batch_annotation_jobs_status', 'batch_annotation_jobs', ['status'])
    op.create_index('idx_batch_annotation_jobs_learning', 'batch_annotation_jobs', ['learning_job_id'])
    
    # Create iteration_records table
    op.create_table(
        'iteration_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('iteration_number', sa.Integer(), nullable=False),
        sa.Column('sample_count', sa.Integer(), nullable=False),
        sa.Column('annotation_count', sa.Integer(), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=False),
        sa.Column('recall', sa.Float(), nullable=False),
        sa.Column('f1_score', sa.Float(), nullable=False),
        sa.Column('consistency', sa.Float(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False),
        sa.Column('learning_job_id', sa.String(), nullable=True),
        sa.Column('batch_job_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['learning_job_id'], ['ai_learning_jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['batch_job_id'], ['batch_annotation_jobs.id'], ondelete='SET NULL')
    )
    
    # Create indexes for iteration_records
    op.create_index('idx_iteration_records_project', 'iteration_records', ['project_id'])
    op.create_index('idx_iteration_records_project_number', 'iteration_records', ['project_id', 'iteration_number'])
    op.create_index('idx_iteration_records_learning', 'iteration_records', ['learning_job_id'])
    op.create_index('idx_iteration_records_batch', 'iteration_records', ['batch_job_id'])


def downgrade():
    """Drop AI annotation workflow tables."""
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('iteration_records')
    op.drop_table('batch_annotation_jobs')
    op.drop_table('ai_learning_jobs')
