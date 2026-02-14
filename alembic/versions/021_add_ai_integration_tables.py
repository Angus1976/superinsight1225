"""Add AI Integration tables

Revision ID: 021_add_ai_integration
Revises: merge_all_heads_2026_01_16
Create Date: 2026-02-04

This migration adds tables for AI Application Integration System:
- ai_gateways: Stores AI gateway registrations (OpenClaw, custom gateways)
- ai_skills: Stores skill packages deployed to gateways
- ai_audit_logs: Records all gateway activities for compliance and security

Supports multi-tenant isolation with tenant_id indexes.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '021_add_ai_integration'
down_revision: Union[str, Sequence[str], None] = 'merge_all_heads_2026_01_16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI integration tables."""
    
    # Create ai_gateways table
    op.create_table(
        'ai_gateways',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('gateway_type', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='inactive'),
        sa.Column('configuration', JSONB, nullable=False, server_default='{}'),
        sa.Column('api_key_hash', sa.String(255), nullable=False),
        sa.Column('api_secret_hash', sa.String(255), nullable=False),
        sa.Column('rate_limit_per_minute', sa.Integer, nullable=False, server_default='60'),
        sa.Column('quota_per_day', sa.Integer, nullable=False, server_default='10000'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes for ai_gateways
    op.create_index('ix_ai_gateways_tenant_id', 'ai_gateways', ['tenant_id'])
    op.create_index('ix_ai_gateways_status', 'ai_gateways', ['status'])
    op.create_index('ix_ai_gateways_gateway_type', 'ai_gateways', ['gateway_type'])
    op.create_index('ix_ai_gateways_tenant_status', 'ai_gateways', ['tenant_id', 'status'])
    
    # Create ai_skills table
    op.create_table(
        'ai_skills',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('gateway_id', sa.String(36), sa.ForeignKey('ai_gateways.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('code_path', sa.String(500), nullable=False),
        sa.Column('configuration', JSONB, nullable=False, server_default='{}'),
        sa.Column('dependencies', JSONB, nullable=False, server_default='[]'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for ai_skills
    op.create_index('ix_ai_skills_gateway_id', 'ai_skills', ['gateway_id'])
    op.create_index('ix_ai_skills_status', 'ai_skills', ['status'])
    op.create_index('ix_ai_skills_gateway_status', 'ai_skills', ['gateway_id', 'status'])
    
    # Create ai_audit_logs table
    op.create_table(
        'ai_audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('gateway_id', sa.String(36), sa.ForeignKey('ai_gateways.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('resource', sa.String(255), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('user_identifier', sa.String(255), nullable=True),
        sa.Column('channel', sa.String(50), nullable=True),
        sa.Column('success', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('signature', sa.String(255), nullable=False),
    )
    
    # Create indexes for ai_audit_logs
    op.create_index('ix_ai_audit_logs_gateway_id', 'ai_audit_logs', ['gateway_id'])
    op.create_index('ix_ai_audit_logs_tenant_id', 'ai_audit_logs', ['tenant_id'])
    op.create_index('ix_ai_audit_logs_event_type', 'ai_audit_logs', ['event_type'])
    op.create_index('ix_ai_audit_logs_timestamp', 'ai_audit_logs', ['timestamp'])
    op.create_index('ix_ai_audit_logs_tenant_timestamp', 'ai_audit_logs', ['tenant_id', 'timestamp'])
    op.create_index('ix_ai_audit_logs_gateway_timestamp', 'ai_audit_logs', ['gateway_id', 'timestamp'])
    op.create_index('ix_ai_audit_logs_event_timestamp', 'ai_audit_logs', ['event_type', 'timestamp'])


def downgrade() -> None:
    """Drop AI integration tables."""
    
    # Drop indexes and tables in reverse order
    op.drop_index('ix_ai_audit_logs_event_timestamp', table_name='ai_audit_logs')
    op.drop_index('ix_ai_audit_logs_gateway_timestamp', table_name='ai_audit_logs')
    op.drop_index('ix_ai_audit_logs_tenant_timestamp', table_name='ai_audit_logs')
    op.drop_index('ix_ai_audit_logs_timestamp', table_name='ai_audit_logs')
    op.drop_index('ix_ai_audit_logs_event_type', table_name='ai_audit_logs')
    op.drop_index('ix_ai_audit_logs_tenant_id', table_name='ai_audit_logs')
    op.drop_index('ix_ai_audit_logs_gateway_id', table_name='ai_audit_logs')
    op.drop_table('ai_audit_logs')
    
    op.drop_index('ix_ai_skills_gateway_status', table_name='ai_skills')
    op.drop_index('ix_ai_skills_status', table_name='ai_skills')
    op.drop_index('ix_ai_skills_gateway_id', table_name='ai_skills')
    op.drop_table('ai_skills')
    
    op.drop_index('ix_ai_gateways_tenant_status', table_name='ai_gateways')
    op.drop_index('ix_ai_gateways_gateway_type', table_name='ai_gateways')
    op.drop_index('ix_ai_gateways_status', table_name='ai_gateways')
    op.drop_index('ix_ai_gateways_tenant_id', table_name='ai_gateways')
    op.drop_table('ai_gateways')
