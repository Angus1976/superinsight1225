"""Add ontology expert collaboration tables

Revision ID: 017_ontology_expert_collab
Revises: 016_llm_health_status
Create Date: 2026-01-24

This migration creates tables for the Ontology Expert Collaboration feature:
- Expert profiles and expertise management
- Ontology templates with versioning
- Change requests and approval workflows
- Validation rules and compliance
- Knowledge contributions and i18n
- Audit logging with integrity verification
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017_ontology_expert_collab'
down_revision = '016_llm_health_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Expert Profiles Tables
    # ============================================
    op.create_table(
        'ontology_expert_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('expertise_areas', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('certifications', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('languages', postgresql.JSONB(), nullable=False, default=['zh-CN']),
        sa.Column('availability_status', sa.String(20), default='available'),
        sa.Column('max_concurrent_tasks', sa.Integer(), default=5),
        sa.Column('current_task_count', sa.Integer(), default=0),
        sa.Column('contribution_count', sa.Integer(), default=0),
        sa.Column('accepted_count', sa.Integer(), default=0),
        sa.Column('rejected_count', sa.Integer(), default=0),
        sa.Column('quality_score', sa.Float(), default=0.0),
        sa.Column('acceptance_rate', sa.Float(), default=0.0),
        sa.Column('contribution_score', sa.Float(), default=0.0),
        sa.Column('last_contribution_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_expert_tenant_email')
    )
    
    # Index for expertise area search (GIN index for JSONB)
    op.create_index(
        'ix_expert_expertise_areas',
        'ontology_expert_profiles',
        [sa.text("expertise_areas jsonb_path_ops")],
        postgresql_using='gin'
    )
    
    # ============================================
    # Ontology Templates Tables
    # ============================================
    op.create_table(
        'ontology_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(50), nullable=False, index=True),
        sa.Column('version', sa.String(20), nullable=False, default='1.0.0'),
        sa.Column('parent_template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('lineage', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('entity_types', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('relation_types', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('validation_rules', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('customization_log', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['parent_template_id'], ['ontology_templates.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'name', 'version', name='uq_template_tenant_name_version')
    )
    
    # ============================================
    # Change Requests Tables
    # ============================================
    op.create_table(
        'ontology_change_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_area', sa.String(100), nullable=False, index=True),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('change_type', sa.String(20), nullable=False),  # add, modify, delete
        sa.Column('target_element_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('target_element_type', sa.String(50), nullable=True),
        sa.Column('before_state', postgresql.JSONB(), nullable=True),
        sa.Column('after_state', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(30), default='draft'),  # draft, submitted, in_review, approved, rejected
        sa.Column('current_level', sa.Integer(), default=0),
        sa.Column('approval_chain_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('is_escalated', sa.Boolean(), default=False),
        sa.Column('impact_report', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # ============================================
    # Approval Chains Tables
    # ============================================
    op.create_table(
        'ontology_approval_chains',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ontology_area', sa.String(100), nullable=False, index=True),
        sa.Column('levels', sa.Integer(), nullable=False, default=1),
        sa.Column('approval_type', sa.String(20), default='sequential'),  # sequential, parallel
        sa.Column('level_configs', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_approval_chain_tenant_name')
    )
    
    # Add foreign key for change_requests -> approval_chains
    op.create_foreign_key(
        'fk_change_request_approval_chain',
        'ontology_change_requests',
        'ontology_approval_chains',
        ['approval_chain_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_table(
        'ontology_approval_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('change_request_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('approver_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),  # approve, reject, request_changes
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['change_request_id'], ['ontology_change_requests.id'], ondelete='CASCADE')
    )

    
    # ============================================
    # Validation Rules Tables
    # ============================================
    op.create_table(
        'ontology_validation_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(50), nullable=False),  # format, range, reference, custom
        sa.Column('region', sa.String(10), nullable=False, default='INTL'),  # CN, HK, TW, INTL
        sa.Column('industry', sa.String(50), nullable=False, default='GENERAL'),
        sa.Column('target_field', sa.String(100), nullable=True),
        sa.Column('validation_logic', sa.Text(), nullable=False),  # regex or Python expression
        sa.Column('error_message_key', sa.String(200), nullable=False),
        sa.Column('severity', sa.String(20), default='error'),  # error, warning, info
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Index for region and industry filtering
    op.create_index(
        'ix_validation_rules_region_industry',
        'ontology_validation_rules',
        ['tenant_id', 'region', 'industry']
    )
    
    # ============================================
    # Knowledge Contributions Tables
    # ============================================
    op.create_table(
        'ontology_knowledge_contributions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('element_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('expert_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('contribution_type', sa.String(30), nullable=False),  # comment, entity_suggestion, relation_suggestion, document
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),  # For threaded comments
        sa.Column('content', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(20), default='pending'),  # pending, accepted, rejected
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['parent_id'], ['ontology_knowledge_contributions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['expert_id'], ['ontology_expert_profiles.id'], ondelete='CASCADE')
    )
    
    op.create_table(
        'ontology_document_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('contribution_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('document_type', sa.String(20), nullable=False),  # pdf, image, link, word, excel
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('url', sa.String(2000), nullable=True),
        sa.Column('file_path', sa.String(1000), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['contribution_id'], ['ontology_knowledge_contributions.id'], ondelete='CASCADE')
    )
    
    # ============================================
    # I18n Translations Tables
    # ============================================
    op.create_table(
        'ontology_i18n_translations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('element_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('element_type', sa.String(50), nullable=False),  # entity_type, relation_type, attribute
        sa.Column('field_name', sa.String(100), nullable=False),  # name, description, etc.
        sa.Column('language', sa.String(10), nullable=False),  # zh-CN, en-US, zh-TW, ja-JP, ko-KR
        sa.Column('translation', sa.Text(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('tenant_id', 'element_id', 'field_name', 'language', name='uq_translation_element_field_lang')
    )
    
    # Index for language-based queries
    op.create_index(
        'ix_i18n_translations_lang',
        'ontology_i18n_translations',
        ['tenant_id', 'ontology_id', 'language']
    )
    
    # ============================================
    # Collaboration Sessions Tables
    # ============================================
    op.create_table(
        'ontology_collaboration_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), default='active'),  # active, closed
        sa.Column('participants', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('closed_at', sa.DateTime(), nullable=True)
    )
    
    op.create_table(
        'ontology_element_locks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('element_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('locked_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('locked_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['ontology_collaboration_sessions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('session_id', 'element_id', name='uq_session_element_lock')
    )
    
    op.create_table(
        'ontology_version_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('ontology_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('element_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('change_type', sa.String(20), nullable=False),  # create, update, delete
        sa.Column('before_state', postgresql.JSONB(), nullable=True),
        sa.Column('after_state', postgresql.JSONB(), nullable=True),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Index for version history queries
    op.create_index(
        'ix_version_history_element',
        'ontology_version_history',
        ['tenant_id', 'ontology_id', 'element_id', 'version']
    )

    
    # ============================================
    # Audit Logs Tables
    # ============================================
    op.create_table(
        'ontology_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_area', sa.String(100), nullable=True, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('change_type', sa.String(30), nullable=False),  # create, update, delete, rollback
        sa.Column('affected_element_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('affected_element_type', sa.String(50), nullable=True),
        sa.Column('before_state', postgresql.JSONB(), nullable=True),
        sa.Column('after_state', postgresql.JSONB(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('integrity_signature', sa.String(128), nullable=False),  # HMAC-SHA256
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), index=True)
    )
    
    # Index for audit log filtering
    op.create_index(
        'ix_audit_logs_user_date',
        'ontology_audit_logs',
        ['tenant_id', 'user_id', 'created_at']
    )
    
    op.create_table(
        'ontology_rollback_operations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('target_version', sa.Integer(), nullable=False),
        sa.Column('performed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('affected_users', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('changes_rolled_back', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('audit_log_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['audit_log_id'], ['ontology_audit_logs.id'], ondelete='SET NULL')
    )
    
    # ============================================
    # Best Practices Tables
    # ============================================
    op.create_table(
        'ontology_best_practices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),  # NULL for global practices
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('industry', sa.String(50), nullable=False, index=True),
        sa.Column('use_case', sa.String(100), nullable=False, index=True),
        sa.Column('content', postgresql.JSONB(), nullable=False),  # steps, examples, benefits
        sa.Column('configuration_steps', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), default='draft'),  # draft, under_review, approved, rejected
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('is_promoted', sa.Boolean(), default=False),
        sa.Column('rating_sum', sa.Float(), default=0.0),
        sa.Column('rating_count', sa.Integer(), default=0),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    op.create_table(
        'ontology_best_practice_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('best_practice_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('applied_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_step', sa.Integer(), default=0),
        sa.Column('total_steps', sa.Integer(), nullable=False),
        sa.Column('completed_steps', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('status', sa.String(20), default='in_progress'),  # in_progress, completed, abandoned
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['best_practice_id'], ['ontology_best_practices.id'], ondelete='CASCADE')
    )
    
    # ============================================
    # Compliance Templates Tables
    # ============================================
    op.create_table(
        'ontology_compliance_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),  # NULL for built-in
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('regulation_code', sa.String(50), nullable=False, index=True),  # DSL, PIPL, CSL
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('classification_rules', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('validation_rules', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('is_built_in', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    op.create_table(
        'ontology_entity_classifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('compliance_template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('classification', sa.String(50), nullable=False),  # CORE, IMPORTANT, GENERAL
        sa.Column('matched_rules', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('recommendations', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('article_references', postgresql.JSONB(), nullable=True, default=[]),
        sa.Column('classified_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['compliance_template_id'], ['ontology_compliance_templates.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('entity_id', 'compliance_template_id', name='uq_entity_compliance_template')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('ontology_entity_classifications')
    op.drop_table('ontology_compliance_templates')
    op.drop_table('ontology_best_practice_applications')
    op.drop_table('ontology_best_practices')
    op.drop_table('ontology_rollback_operations')
    op.drop_table('ontology_audit_logs')
    op.drop_index('ix_version_history_element', table_name='ontology_version_history')
    op.drop_table('ontology_version_history')
    op.drop_table('ontology_element_locks')
    op.drop_table('ontology_collaboration_sessions')
    op.drop_index('ix_i18n_translations_lang', table_name='ontology_i18n_translations')
    op.drop_table('ontology_i18n_translations')
    op.drop_table('ontology_document_attachments')
    op.drop_table('ontology_knowledge_contributions')
    op.drop_index('ix_validation_rules_region_industry', table_name='ontology_validation_rules')
    op.drop_table('ontology_validation_rules')
    op.drop_table('ontology_approval_records')
    op.drop_constraint('fk_change_request_approval_chain', 'ontology_change_requests', type_='foreignkey')
    op.drop_table('ontology_approval_chains')
    op.drop_table('ontology_change_requests')
    op.drop_table('ontology_templates')
    op.drop_index('ix_expert_expertise_areas', table_name='ontology_expert_profiles')
    op.drop_table('ontology_expert_profiles')
