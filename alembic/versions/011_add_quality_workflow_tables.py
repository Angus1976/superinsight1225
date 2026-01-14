"""Add quality workflow tables

Revision ID: 011_quality_workflow
Revises: 010_collaboration_workflow
Create Date: 2026-01-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_quality_workflow'
down_revision = '010_collaboration_workflow'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Quality Scores Table
    op.create_table(
        'quality_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('annotator_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('dimension_scores', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('total_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('weights', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('gold_standard_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scoring_method', sa.String(50), server_default='weighted_average'),
        sa.Column('scored_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('scored_by', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index('ix_quality_scores_annotation_id', 'quality_scores', ['annotation_id'])
    op.create_index('ix_quality_scores_project_id', 'quality_scores', ['project_id'])
    op.create_index('ix_quality_scores_annotator_id', 'quality_scores', ['annotator_id'])
    op.create_index('ix_quality_scores_project_scored', 'quality_scores', ['project_id', 'scored_at'])
    op.create_index('ix_quality_scores_annotator_scored', 'quality_scores', ['annotator_id', 'scored_at'])

    # Quality Rules Table
    op.create_table(
        'quality_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('rule_type', sa.String(20), nullable=False, server_default='builtin'),
        sa.Column('config', postgresql.JSONB, server_default='{}'),
        sa.Column('script', sa.Text, nullable=True),
        sa.Column('severity', sa.String(20), server_default='medium'),
        sa.Column('priority', sa.Integer, server_default='0'),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('version', sa.Integer, server_default='1'),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index('ix_quality_rules_project_id', 'quality_rules', ['project_id'])
    op.create_index('ix_quality_rules_project_enabled', 'quality_rules', ['project_id', 'enabled'])
    op.create_index('ix_quality_rules_project_priority', 'quality_rules', ['project_id', 'priority'])

    # Quality Rule Templates Table
    op.create_table(
        'quality_rule_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('rules', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('is_system', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Quality Check Results Table
    op.create_table(
        'quality_check_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('passed', sa.Boolean, nullable=False),
        sa.Column('issues', postgresql.JSONB, server_default='[]'),
        sa.Column('checked_rules', sa.Integer, nullable=False, server_default='0'),
        sa.Column('check_type', sa.String(20), server_default='realtime'),
        sa.Column('checked_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('checked_by', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index('ix_quality_check_results_annotation_id', 'quality_check_results', ['annotation_id'])
    op.create_index('ix_quality_check_results_project_id', 'quality_check_results', ['project_id'])
    op.create_index('ix_quality_check_results_project_checked', 'quality_check_results', ['project_id', 'checked_at'])
    op.create_index('ix_quality_check_results_annotation', 'quality_check_results', ['annotation_id', 'checked_at'])

    # Improvement Tasks Table
    op.create_table(
        'improvement_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issues', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('priority', sa.Integer, server_default='1'),
        sa.Column('improved_data', postgresql.JSONB, nullable=True),
        sa.Column('original_data', postgresql.JSONB, nullable=True),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('review_comments', sa.Text, nullable=True),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('submitted_at', sa.DateTime, nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_improvement_tasks_annotation_id', 'improvement_tasks', ['annotation_id'])
    op.create_index('ix_improvement_tasks_project_id', 'improvement_tasks', ['project_id'])
    op.create_index('ix_improvement_tasks_assignee_id', 'improvement_tasks', ['assignee_id'])
    op.create_index('ix_improvement_tasks_project_status', 'improvement_tasks', ['project_id', 'status'])
    op.create_index('ix_improvement_tasks_assignee_status', 'improvement_tasks', ['assignee_id', 'status'])

    # Improvement History Table
    op.create_table(
        'improvement_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('improvement_tasks.id'), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('from_status', sa.String(20), nullable=True),
        sa.Column('to_status', sa.String(20), nullable=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('comments', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_improvement_history_task_id', 'improvement_history', ['task_id'])

    # Quality Alerts Table
    op.create_table(
        'quality_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('triggered_dimensions', postgresql.ARRAY(sa.String), nullable=False, server_default='{}'),
        sa.Column('scores', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('thresholds', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('escalation_level', sa.Integer, server_default='0'),
        sa.Column('status', sa.String(20), server_default='open'),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime, nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('resolution_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_quality_alerts_project_id', 'quality_alerts', ['project_id'])
    op.create_index('ix_quality_alerts_annotation_id', 'quality_alerts', ['annotation_id'])
    op.create_index('ix_quality_alerts_project_status', 'quality_alerts', ['project_id', 'status'])
    op.create_index('ix_quality_alerts_project_severity', 'quality_alerts', ['project_id', 'severity'])

    # Alert Configs Table
    op.create_table(
        'alert_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('thresholds', postgresql.JSONB, nullable=False, server_default='{"accuracy": 0.8, "completeness": 0.9, "timeliness": 0.7}'),
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('notification_channels', postgresql.JSONB, server_default='["in_app"]'),
        sa.Column('recipients', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default='{}'),
        sa.Column('silence_duration', sa.Integer, server_default='0'),
        sa.Column('silence_until', sa.DateTime, nullable=True),
        sa.Column('escalation_rules', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_alert_configs_project_id', 'alert_configs', ['project_id'])

    # Quality Workflows Table
    op.create_table(
        'quality_workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('stages', postgresql.JSONB, server_default='["identify", "assign", "improve", "review", "verify"]'),
        sa.Column('auto_create_task', sa.Boolean, server_default='true'),
        sa.Column('auto_assign_rules', postgresql.JSONB, server_default='{}'),
        sa.Column('escalation_rules', postgresql.JSONB, server_default='{}'),
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_quality_workflows_project_id', 'quality_workflows', ['project_id'])

    # Quality Project Configs Table
    op.create_table(
        'quality_project_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('score_weights', postgresql.JSONB, server_default='{"accuracy": 0.4, "completeness": 0.3, "timeliness": 0.2, "consistency": 0.1}'),
        sa.Column('required_fields', postgresql.JSONB, server_default='[]'),
        sa.Column('expected_duration', sa.Integer, server_default='300'),
        sa.Column('gold_standard_enabled', sa.Boolean, server_default='false'),
        sa.Column('gold_standard_ratio', sa.Float, server_default='0.1'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_quality_project_configs_project_id', 'quality_project_configs', ['project_id'])

    # Ragas Evaluations Table
    op.create_table(
        'ragas_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('annotation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question', sa.Text, nullable=False),
        sa.Column('answer', sa.Text, nullable=False),
        sa.Column('contexts', postgresql.JSONB, server_default='[]'),
        sa.Column('ground_truth', sa.Text, nullable=True),
        sa.Column('faithfulness', sa.Float, nullable=True),
        sa.Column('answer_relevancy', sa.Float, nullable=True),
        sa.Column('context_precision', sa.Float, nullable=True),
        sa.Column('context_recall', sa.Float, nullable=True),
        sa.Column('overall_score', sa.Float, nullable=True),
        sa.Column('metrics_used', postgresql.JSONB, server_default='[]'),
        sa.Column('evaluation_model', sa.String(100), nullable=True),
        sa.Column('evaluated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_ragas_evaluations_annotation_id', 'ragas_evaluations', ['annotation_id'])
    op.create_index('ix_ragas_evaluations_project_id', 'ragas_evaluations', ['project_id'])
    op.create_index('ix_ragas_evaluations_project_evaluated', 'ragas_evaluations', ['project_id', 'evaluated_at'])

    # Report Schedules Table
    op.create_table(
        'report_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('schedule', sa.String(100), nullable=False),
        sa.Column('parameters', postgresql.JSONB, server_default='{}'),
        sa.Column('recipients', postgresql.JSONB, server_default='[]'),
        sa.Column('export_format', sa.String(20), server_default='pdf'),
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('last_run_at', sa.DateTime, nullable=True),
        sa.Column('next_run_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index('ix_report_schedules_project_id', 'report_schedules', ['project_id'])


def downgrade() -> None:
    op.drop_table('report_schedules')
    op.drop_table('ragas_evaluations')
    op.drop_table('quality_project_configs')
    op.drop_table('quality_workflows')
    op.drop_table('alert_configs')
    op.drop_table('quality_alerts')
    op.drop_table('improvement_history')
    op.drop_table('improvement_tasks')
    op.drop_table('quality_check_results')
    op.drop_table('quality_rule_templates')
    op.drop_table('quality_rules')
    op.drop_table('quality_scores')
