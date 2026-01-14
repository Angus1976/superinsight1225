"""Add LLM Integration tables

Revision ID: 008_add_llm_integration
Revises: 2f6b0cbeb30c
Create Date: 2026-01-13

This migration adds tables for LLM configuration management and usage logging:
- llm_configurations: Stores LLM provider configurations per tenant
- llm_usage_logs: Tracks API calls, token usage, and performance metrics
- llm_model_registry: Caches available models per provider
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '008_add_llm_integration'
down_revision: Union[str, Sequence[str], None] = '2f6b0cbeb30c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create LLM integration tables."""
    
    # Create llm_configurations table
    op.create_table(
        'llm_configurations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('config_data', JSONB, nullable=False, server_default='{}'),
        sa.Column('default_method', sa.String(50), nullable=False, server_default='local_ollama'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create indexes for llm_configurations
    op.create_index('ix_llm_config_tenant_id', 'llm_configurations', ['tenant_id'])
    op.create_index('ix_llm_config_tenant_active', 'llm_configurations', ['tenant_id', 'is_active'])
    op.create_index('ix_llm_config_tenant_default', 'llm_configurations', ['tenant_id', 'is_default'])
    op.create_index('ix_llm_config_method', 'llm_configurations', ['default_method'])
    
    # Create llm_usage_logs table
    op.create_table(
        'llm_usage_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('method', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('operation', sa.String(50), nullable=False, server_default='generate'),
        sa.Column('prompt_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('success', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('request_metadata', JSONB, nullable=True),
        sa.Column('response_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for llm_usage_logs
    op.create_index('ix_llm_usage_tenant_id', 'llm_usage_logs', ['tenant_id'])
    op.create_index('ix_llm_usage_user_id', 'llm_usage_logs', ['user_id'])
    op.create_index('ix_llm_usage_method', 'llm_usage_logs', ['method'])
    op.create_index('ix_llm_usage_model', 'llm_usage_logs', ['model'])
    op.create_index('ix_llm_usage_created_at', 'llm_usage_logs', ['created_at'])
    op.create_index('ix_llm_usage_tenant_created', 'llm_usage_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_llm_usage_method_created', 'llm_usage_logs', ['method', 'created_at'])
    op.create_index('ix_llm_usage_user_created', 'llm_usage_logs', ['user_id', 'created_at'])
    op.create_index('ix_llm_usage_success', 'llm_usage_logs', ['success', 'created_at'])
    
    # Create llm_model_registry table
    op.create_table(
        'llm_model_registry',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('method', sa.String(50), nullable=False),
        sa.Column('model_id', sa.String(100), nullable=False),
        sa.Column('model_name', sa.String(255), nullable=False),
        sa.Column('supports_chat', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('supports_completion', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('supports_embedding', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('supports_streaming', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('max_tokens', sa.Integer, nullable=True),
        sa.Column('context_window', sa.Integer, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('is_available', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for llm_model_registry
    op.create_index('ix_llm_model_method_id', 'llm_model_registry', ['method', 'model_id'], unique=True)
    op.create_index('ix_llm_model_available', 'llm_model_registry', ['is_available'])


def downgrade() -> None:
    """Drop LLM integration tables."""
    
    # Drop indexes and tables in reverse order
    op.drop_index('ix_llm_model_available', table_name='llm_model_registry')
    op.drop_index('ix_llm_model_method_id', table_name='llm_model_registry')
    op.drop_table('llm_model_registry')
    
    op.drop_index('ix_llm_usage_success', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_user_created', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_method_created', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_tenant_created', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_created_at', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_model', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_method', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_user_id', table_name='llm_usage_logs')
    op.drop_index('ix_llm_usage_tenant_id', table_name='llm_usage_logs')
    op.drop_table('llm_usage_logs')
    
    op.drop_index('ix_llm_config_method', table_name='llm_configurations')
    op.drop_index('ix_llm_config_tenant_default', table_name='llm_configurations')
    op.drop_index('ix_llm_config_tenant_active', table_name='llm_configurations')
    op.drop_index('ix_llm_config_tenant_id', table_name='llm_configurations')
    op.drop_table('llm_configurations')
