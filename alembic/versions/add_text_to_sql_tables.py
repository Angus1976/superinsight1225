"""Add Text-to-SQL tables

Revision ID: text_to_sql_001
Revises: 
Create Date: 2026-01-14

Creates tables for Text-to-SQL Methods module:
- text_to_sql_configurations: Method configuration storage
- third_party_plugins: Third-party tool plugin management
- sql_generation_logs: Generation logging and analytics
- sql_templates: Template-based SQL generation
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'text_to_sql_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create text_to_sql_configurations table
    op.create_table(
        'text_to_sql_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False, default='default'),
        sa.Column('default_method', sa.String(50), nullable=False, default='hybrid'),
        sa.Column('template_config', postgresql.JSONB, nullable=False, default={}),
        sa.Column('llm_config', postgresql.JSONB, nullable=False, default={}),
        sa.Column('hybrid_config', postgresql.JSONB, nullable=False, default={}),
        sa.Column('auto_select_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('fallback_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('max_retries', sa.Integer, nullable=False, default=3),
        sa.Column('timeout_ms', sa.Integer, nullable=False, default=30000),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    op.create_index('ix_text_to_sql_config_tenant_active', 'text_to_sql_configurations', ['tenant_id', 'is_active'])
    op.create_index('ix_text_to_sql_config_name', 'text_to_sql_configurations', ['name'])
    
    # Create third_party_plugins table
    op.create_table(
        'third_party_plugins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('version', sa.String(50), nullable=False, default='1.0.0'),
        sa.Column('connection_type', sa.String(50), nullable=False),
        sa.Column('endpoint', sa.String(500), nullable=True),
        sa.Column('api_key_encrypted', sa.Text, nullable=True),
        sa.Column('timeout', sa.Integer, nullable=False, default=30),
        sa.Column('enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('supported_db_types', postgresql.JSONB, nullable=False, default=[]),
        sa.Column('config_schema', postgresql.JSONB, nullable=False, default={}),
        sa.Column('extra_config', postgresql.JSONB, nullable=False, default={}),
        sa.Column('is_healthy', sa.Boolean, nullable=False, default=True),
        sa.Column('last_health_check', sa.DateTime, nullable=True),
        sa.Column('health_check_error', sa.Text, nullable=True),
        sa.Column('total_calls', sa.Integer, nullable=False, default=0),
        sa.Column('successful_calls', sa.Integer, nullable=False, default=0),
        sa.Column('failed_calls', sa.Integer, nullable=False, default=0),
        sa.Column('total_response_time_ms', sa.Float, nullable=False, default=0.0),
        sa.Column('last_used', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    op.create_index('ix_third_party_plugin_tenant_name', 'third_party_plugins', ['tenant_id', 'name'], unique=True)
    op.create_index('ix_third_party_plugin_enabled', 'third_party_plugins', ['enabled'])
    op.create_index('ix_third_party_plugin_connection_type', 'third_party_plugins', ['connection_type'])
    
    # Create sql_generation_logs table
    op.create_table(
        'sql_generation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('query', sa.Text, nullable=False),
        sa.Column('requested_method', sa.String(100), nullable=True),
        sa.Column('db_type', sa.String(50), nullable=True),
        sa.Column('schema_context_hash', sa.String(64), nullable=True),
        sa.Column('generated_sql', sa.Text, nullable=False),
        sa.Column('method_used', sa.String(100), nullable=False),
        sa.Column('confidence', sa.Float, nullable=False, default=0.0),
        sa.Column('execution_time_ms', sa.Float, nullable=False, default=0.0),
        sa.Column('success', sa.Boolean, nullable=False, default=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('template_id', sa.String(100), nullable=True),
        sa.Column('template_match_score', sa.Float, nullable=True),
        sa.Column('plugin_name', sa.String(100), nullable=True),
        sa.Column('plugin_response_time_ms', sa.Float, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=False, default={}),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    op.create_index('ix_sql_gen_log_tenant_created', 'sql_generation_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_sql_gen_log_method_created', 'sql_generation_logs', ['method_used', 'created_at'])
    op.create_index('ix_sql_gen_log_success', 'sql_generation_logs', ['success'])
    op.create_index('ix_sql_gen_log_user_created', 'sql_generation_logs', ['user_id', 'created_at'])
    op.create_index('ix_sql_gen_log_created_at', 'sql_generation_logs', ['created_at'])
    
    # Create sql_templates table
    op.create_table(
        'sql_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('template_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('pattern', sa.Text, nullable=False),
        sa.Column('template', sa.Text, nullable=False),
        sa.Column('param_types', postgresql.JSONB, nullable=False, default={}),
        sa.Column('examples', postgresql.JSONB, nullable=False, default=[]),
        sa.Column('priority', sa.Integer, nullable=False, default=0),
        sa.Column('enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('is_system', sa.Boolean, nullable=False, default=False),
        sa.Column('usage_count', sa.Integer, nullable=False, default=0),
        sa.Column('success_count', sa.Integer, nullable=False, default=0),
        sa.Column('last_used', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    op.create_index('ix_sql_template_tenant_id', 'sql_templates', ['tenant_id', 'template_id'], unique=True)
    op.create_index('ix_sql_template_category', 'sql_templates', ['category'])
    op.create_index('ix_sql_template_enabled_priority', 'sql_templates', ['enabled', 'priority'])


def downgrade() -> None:
    op.drop_table('sql_templates')
    op.drop_table('sql_generation_logs')
    op.drop_table('third_party_plugins')
    op.drop_table('text_to_sql_configurations')
