"""Add Admin Configuration tables

Revision ID: 012_add_admin_config
Revises: 011_add_quality_workflow_tables
Create Date: 2026-01-14

This migration adds tables for admin configuration management:
- admin_configurations: General admin configurations
- database_connections: Customer database connection configs
- config_change_history: Configuration change audit trail
- query_templates: Saved SQL query templates
- sync_strategies: Data synchronization strategies
- sync_history: Sync execution history
- third_party_tool_configs: Third-party tool configurations
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '012_add_admin_config'
down_revision: Union[str, Sequence[str], None] = '011_add_quality_workflow_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create admin configuration tables."""
    
    # Create admin_configurations table
    op.create_table(
        'admin_configurations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('config_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('config_data', JSONB, nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create indexes for admin_configurations
    op.create_index('ix_admin_config_tenant_id', 'admin_configurations', ['tenant_id'])
    op.create_index('ix_admin_config_type', 'admin_configurations', ['config_type'])
    op.create_index('ix_admin_config_tenant_type', 'admin_configurations', ['tenant_id', 'config_type'])
    op.create_index('ix_admin_config_type_active', 'admin_configurations', ['config_type', 'is_active'])
    op.create_index('ix_admin_config_tenant_default', 'admin_configurations', ['tenant_id', 'is_default'])
    
    # Create database_connections table
    op.create_table(
        'database_connections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('db_type', sa.String(50), nullable=False),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer, nullable=False),
        sa.Column('database', sa.String(100), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('password_encrypted', sa.Text, nullable=True),
        sa.Column('is_readonly', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('ssl_enabled', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('extra_config', JSONB, nullable=True, server_default='{}'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('last_test_at', sa.DateTime, nullable=True),
        sa.Column('last_test_status', sa.String(50), nullable=True),
        sa.Column('last_test_latency_ms', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create indexes for database_connections
    op.create_index('ix_db_conn_tenant_id', 'database_connections', ['tenant_id'])
    op.create_index('ix_db_conn_tenant_active', 'database_connections', ['tenant_id', 'is_active'])
    op.create_index('ix_db_conn_type', 'database_connections', ['db_type'])
    op.create_index('ix_db_conn_name', 'database_connections', ['name'])
    
    # Create config_change_history table
    op.create_table(
        'config_change_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('config_type', sa.String(50), nullable=False),
        sa.Column('config_id', UUID(as_uuid=True), nullable=True),
        sa.Column('old_value', JSONB, nullable=True),
        sa.Column('new_value', JSONB, nullable=False),
        sa.Column('change_reason', sa.Text, nullable=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_name', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for config_change_history
    op.create_index('ix_config_history_tenant_id', 'config_change_history', ['tenant_id'])
    op.create_index('ix_config_history_type', 'config_change_history', ['config_type'])
    op.create_index('ix_config_history_tenant_type', 'config_change_history', ['tenant_id', 'config_type'])
    op.create_index('ix_config_history_config_id', 'config_change_history', ['config_id'])
    op.create_index('ix_config_history_user_id', 'config_change_history', ['user_id'])
    op.create_index('ix_config_history_user_created', 'config_change_history', ['user_id', 'created_at'])
    op.create_index('ix_config_history_created', 'config_change_history', ['created_at'])
    
    # Create sync_strategies table
    op.create_table(
        'sync_strategies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('db_config_id', UUID(as_uuid=True), sa.ForeignKey('database_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('mode', sa.String(20), nullable=False, server_default='full'),
        sa.Column('incremental_field', sa.String(100), nullable=True),
        sa.Column('schedule', sa.String(100), nullable=True),
        sa.Column('filter_conditions', JSONB, nullable=True, server_default='[]'),
        sa.Column('batch_size', sa.Integer, nullable=False, server_default='1000'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('last_sync_at', sa.DateTime, nullable=True),
        sa.Column('last_sync_status', sa.String(50), nullable=True),
        sa.Column('last_sync_records', sa.Integer, nullable=True),
        sa.Column('last_sync_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create indexes for sync_strategies
    op.create_index('ix_sync_strategy_tenant_id', 'sync_strategies', ['tenant_id'])
    op.create_index('ix_sync_strategy_db_config', 'sync_strategies', ['db_config_id'])
    op.create_index('ix_sync_strategy_enabled', 'sync_strategies', ['enabled'])
    op.create_index('ix_sync_strategy_mode', 'sync_strategies', ['mode'])
    
    # Create sync_history table
    op.create_table(
        'sync_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', UUID(as_uuid=True), sa.ForeignKey('sync_strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('records_synced', sa.Integer, nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer, nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('details', JSONB, nullable=True),
    )
    
    # Create indexes for sync_history
    op.create_index('ix_sync_history_strategy', 'sync_history', ['strategy_id'])
    op.create_index('ix_sync_history_status', 'sync_history', ['status'])
    op.create_index('ix_sync_history_started', 'sync_history', ['started_at'])
    
    # Create query_templates table
    op.create_table(
        'query_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('db_config_id', UUID(as_uuid=True), sa.ForeignKey('database_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('query_config', JSONB, nullable=False),
        sa.Column('sql', sa.Text, nullable=False),
        sa.Column('is_public', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create indexes for query_templates
    op.create_index('ix_query_template_tenant', 'query_templates', ['tenant_id'])
    op.create_index('ix_query_template_db_config', 'query_templates', ['db_config_id'])
    op.create_index('ix_query_template_name', 'query_templates', ['name'])
    op.create_index('ix_query_template_public', 'query_templates', ['is_public'])
    op.create_index('ix_query_template_created_by', 'query_templates', ['created_by'])
    
    # Create third_party_tool_configs table
    op.create_table(
        'third_party_tool_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tool_type', sa.String(50), nullable=False),
        sa.Column('endpoint', sa.String(500), nullable=False),
        sa.Column('api_key_encrypted', sa.Text, nullable=True),
        sa.Column('timeout_seconds', sa.Integer, nullable=False, server_default='30'),
        sa.Column('extra_config', JSONB, nullable=True, server_default='{}'),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('health_status', sa.String(50), nullable=True),
        sa.Column('last_health_check', sa.DateTime, nullable=True),
        sa.Column('call_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_latency_ms', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Create indexes for third_party_tool_configs
    op.create_index('ix_third_party_tenant', 'third_party_tool_configs', ['tenant_id'])
    op.create_index('ix_third_party_type', 'third_party_tool_configs', ['tool_type'])
    op.create_index('ix_third_party_enabled', 'third_party_tool_configs', ['enabled'])
    op.create_index('ix_third_party_name', 'third_party_tool_configs', ['name'])


def downgrade() -> None:
    """Drop admin configuration tables."""
    
    # Drop third_party_tool_configs
    op.drop_index('ix_third_party_name', table_name='third_party_tool_configs')
    op.drop_index('ix_third_party_enabled', table_name='third_party_tool_configs')
    op.drop_index('ix_third_party_type', table_name='third_party_tool_configs')
    op.drop_index('ix_third_party_tenant', table_name='third_party_tool_configs')
    op.drop_table('third_party_tool_configs')
    
    # Drop query_templates
    op.drop_index('ix_query_template_created_by', table_name='query_templates')
    op.drop_index('ix_query_template_public', table_name='query_templates')
    op.drop_index('ix_query_template_name', table_name='query_templates')
    op.drop_index('ix_query_template_db_config', table_name='query_templates')
    op.drop_index('ix_query_template_tenant', table_name='query_templates')
    op.drop_table('query_templates')
    
    # Drop sync_history
    op.drop_index('ix_sync_history_started', table_name='sync_history')
    op.drop_index('ix_sync_history_status', table_name='sync_history')
    op.drop_index('ix_sync_history_strategy', table_name='sync_history')
    op.drop_table('sync_history')
    
    # Drop sync_strategies
    op.drop_index('ix_sync_strategy_mode', table_name='sync_strategies')
    op.drop_index('ix_sync_strategy_enabled', table_name='sync_strategies')
    op.drop_index('ix_sync_strategy_db_config', table_name='sync_strategies')
    op.drop_index('ix_sync_strategy_tenant_id', table_name='sync_strategies')
    op.drop_table('sync_strategies')
    
    # Drop config_change_history
    op.drop_index('ix_config_history_created', table_name='config_change_history')
    op.drop_index('ix_config_history_user_created', table_name='config_change_history')
    op.drop_index('ix_config_history_user_id', table_name='config_change_history')
    op.drop_index('ix_config_history_config_id', table_name='config_change_history')
    op.drop_index('ix_config_history_tenant_type', table_name='config_change_history')
    op.drop_index('ix_config_history_type', table_name='config_change_history')
    op.drop_index('ix_config_history_tenant_id', table_name='config_change_history')
    op.drop_table('config_change_history')
    
    # Drop database_connections
    op.drop_index('ix_db_conn_name', table_name='database_connections')
    op.drop_index('ix_db_conn_type', table_name='database_connections')
    op.drop_index('ix_db_conn_tenant_active', table_name='database_connections')
    op.drop_index('ix_db_conn_tenant_id', table_name='database_connections')
    op.drop_table('database_connections')
    
    # Drop admin_configurations
    op.drop_index('ix_admin_config_tenant_default', table_name='admin_configurations')
    op.drop_index('ix_admin_config_type_active', table_name='admin_configurations')
    op.drop_index('ix_admin_config_tenant_type', table_name='admin_configurations')
    op.drop_index('ix_admin_config_type', table_name='admin_configurations')
    op.drop_index('ix_admin_config_tenant_id', table_name='admin_configurations')
    op.drop_table('admin_configurations')
