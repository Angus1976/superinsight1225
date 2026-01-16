"""Add collaboration workflow tables

Revision ID: 010_collab_workflow
Revises: 009_ai_annotation
Create Date: 2026-01-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_collab_workflow'
down_revision = '009_ai_annotation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Task Assignment Tables
    op.create_table(
        'collab_task_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('annotator_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('priority', sa.Integer(), default=0),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), default='assigned'),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('task_id', 'annotator_id', name='uq_task_annotator')
    )
    
    op.create_table(
        'collab_annotation_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('annotator_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('annotation', postgresql.JSONB(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('task_id', 'version', name='uq_task_version')
    )
    
    op.create_table(
        'collab_task_locks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column('locked_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('locked_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False)
    )
    
    # Review Flow Tables
    op.create_table(
        'collab_review_flows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column('levels', sa.Integer(), default=2),
        sa.Column('pass_threshold', sa.Float(), default=0.8),
        sa.Column('auto_approve', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    op.create_table(
        'collab_review_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('current_level', sa.Integer(), default=1),
        sa.Column('max_level', sa.Integer(), default=2),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    op.create_table(
        'collab_review_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('review_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_review_tasks.id'), nullable=False, index=True),
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Conflict Resolution Tables
    op.create_table(
        'collab_conflicts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('version1_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_annotation_versions.id'), nullable=False),
        sa.Column('version2_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_annotation_versions.id'), nullable=False),
        sa.Column('conflict_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), default='unresolved'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    op.create_table(
        'collab_conflict_votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conflict_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_conflicts.id'), nullable=False, index=True),
        sa.Column('voter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('choice', sa.String(50), nullable=False),
        sa.Column('voted_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('conflict_id', 'voter_id', name='uq_conflict_voter')
    )
    
    op.create_table(
        'collab_conflict_resolutions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conflict_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_conflicts.id'), nullable=False, unique=True),
        sa.Column('method', sa.String(20), nullable=False),
        sa.Column('result', postgresql.JSONB(), nullable=False),
        sa.Column('vote_counts', postgresql.JSONB(), nullable=True),
        sa.Column('expert_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Crowdsource Tables
    op.create_table(
        'collab_crowdsource_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('data_ids', postgresql.JSONB(), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('platform', sa.String(50), default='internal'),
        sa.Column('status', sa.String(20), default='open'),
        sa.Column('external_task_id', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    op.create_table(
        'collab_crowdsource_annotators',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(200), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('password_hash', sa.String(200), nullable=True),
        sa.Column('real_name', sa.String(100), nullable=True),
        sa.Column('identity_verified', sa.Boolean(), default=False),
        sa.Column('identity_doc_type', sa.String(20), nullable=True),
        sa.Column('identity_doc_number', sa.String(50), nullable=True),
        sa.Column('status', sa.String(30), default='pending_verification'),
        sa.Column('star_rating', sa.Integer(), default=0),
        sa.Column('ability_tags', postgresql.JSONB(), default=[]),
        sa.Column('total_tasks', sa.Integer(), default=0),
        sa.Column('total_earnings', sa.Float(), default=0.0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    op.create_table(
        'collab_crowdsource_task_claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_crowdsource_tasks.id'), nullable=False, index=True),
        sa.Column('annotator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_crowdsource_annotators.id'), nullable=False, index=True),
        sa.Column('claimed_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), default='active'),
        sa.UniqueConstraint('task_id', 'annotator_id', name='uq_crowdsource_task_annotator')
    )
    
    op.create_table(
        'collab_crowdsource_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_crowdsource_tasks.id'), nullable=False, index=True),
        sa.Column('annotator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_crowdsource_annotators.id'), nullable=False, index=True),
        sa.Column('annotation', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True)
    )
    
    op.create_table(
        'collab_crowdsource_ability_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_crowdsource_annotators.id'), nullable=False, index=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('tested_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Third Party Platform Tables
    op.create_table(
        'collab_third_party_platforms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('platform_type', sa.String(20), nullable=False),
        sa.Column('api_key', sa.String(500), nullable=True),
        sa.Column('api_secret', sa.String(500), nullable=True),
        sa.Column('endpoint', sa.String(500), nullable=True),
        sa.Column('extra_config', postgresql.JSONB(), default={}),
        sa.Column('status', sa.String(20), default='disconnected'),
        sa.Column('connected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    op.create_table(
        'collab_platform_sync_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('platform_name', sa.String(100), nullable=False, index=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('external_task_id', sa.String(200), nullable=True),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('synced_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Billing Tables
    op.create_table(
        'collab_crowdsource_pricing_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column('base_price', sa.Float(), default=0.1),
        sa.Column('task_type_prices', postgresql.JSONB(), default={}),
        sa.Column('quality_bonus_enabled', sa.Boolean(), default=True),
        sa.Column('star_bonus_enabled', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    op.create_table(
        'collab_crowdsource_withdrawals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_crowdsource_annotators.id'), nullable=False, index=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('method', sa.String(20), nullable=False),
        sa.Column('account_info', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('transaction_id', sa.String(100), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    op.create_table(
        'collab_crowdsource_invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collab_crowdsource_annotators.id'), nullable=False, index=True),
        sa.Column('period', sa.String(20), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('task_count', sa.Integer(), default=0),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Notification Tables
    op.create_table(
        'collab_notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column('channels', postgresql.JSONB(), default=['in_app']),
        sa.Column('task_assigned', sa.Boolean(), default=True),
        sa.Column('review_completed', sa.Boolean(), default=True),
        sa.Column('deadline_reminder', sa.Boolean(), default=True),
        sa.Column('quality_warning', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    op.create_table(
        'collab_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        sa.Column('read', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('collab_notifications')
    op.drop_table('collab_notification_preferences')
    op.drop_table('collab_crowdsource_invoices')
    op.drop_table('collab_crowdsource_withdrawals')
    op.drop_table('collab_crowdsource_pricing_configs')
    op.drop_table('collab_platform_sync_logs')
    op.drop_table('collab_third_party_platforms')
    op.drop_table('collab_crowdsource_ability_tests')
    op.drop_table('collab_crowdsource_submissions')
    op.drop_table('collab_crowdsource_task_claims')
    op.drop_table('collab_crowdsource_annotators')
    op.drop_table('collab_crowdsource_tasks')
    op.drop_table('collab_conflict_resolutions')
    op.drop_table('collab_conflict_votes')
    op.drop_table('collab_conflicts')
    op.drop_table('collab_review_history')
    op.drop_table('collab_review_tasks')
    op.drop_table('collab_review_flows')
    op.drop_table('collab_task_locks')
    op.drop_table('collab_annotation_versions')
    op.drop_table('collab_task_assignments')
