"""Add comprehensive security tables

Revision ID: 20260113_security
Revises: 
Create Date: 2026-01-13

This migration creates all security-related tables including:
- security_roles: Role definitions with hierarchy support
- security_user_roles: User-role assignments
- security_dynamic_policies: Dynamic access control policies
- security_sso_providers: SSO provider configurations
- security_audit_logs: Tamper-proof audit logs
- security_events: Security incident tracking
- security_sessions: Session management
- security_encryption_keys: Key management
- security_compliance_reports: Compliance report storage
- security_ip_whitelist: IP-based access control
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260113_security'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE permission_scope AS ENUM ('global', 'tenant', 'resource');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE resource_type AS ENUM (
                'project', 'dataset', 'model', 'pipeline', 'report',
                'dashboard', 'user', 'role', 'permission', 'audit_log', 'system_config'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE sso_protocol AS ENUM ('saml', 'oauth2', 'oidc', 'ldap');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE security_event_severity AS ENUM ('low', 'medium', 'high', 'critical');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE security_event_status AS ENUM ('open', 'investigating', 'resolved', 'false_positive');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE policy_type AS ENUM ('time_range', 'ip_whitelist', 'sensitivity_level', 'attribute', 'rate_limit');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create security_roles table
    op.create_table(
        'security_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('parent_role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('security_roles.id'), nullable=True),
        sa.Column('permissions', postgresql.JSONB, default=list),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_system_role', sa.Boolean, default=False),
        sa.Column('role_metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('name', 'tenant_id', name='uq_security_role_name_tenant'),
    )
    op.create_index('idx_security_role_tenant_active', 'security_roles', ['tenant_id', 'is_active'])
    op.create_index('idx_security_role_parent', 'security_roles', ['parent_role_id'])
    
    # Create security_user_roles table
    op.create_table(
        'security_user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('security_roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('conditions', postgresql.JSONB, nullable=True),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_security_user_role'),
    )
    op.create_index('idx_security_user_role_user', 'security_user_roles', ['user_id'])
    op.create_index('idx_security_user_role_role', 'security_user_roles', ['role_id'])
    op.create_index('idx_security_user_role_active', 'security_user_roles', ['is_active'])
    
    # Create security_dynamic_policies table
    op.create_table(
        'security_dynamic_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('policy_type', sa.Enum('time_range', 'ip_whitelist', 'sensitivity_level', 'attribute', 'rate_limit', name='policy_type'), nullable=False),
        sa.Column('resource_pattern', sa.String(200), nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=False),
        sa.Column('enabled', sa.Boolean, default=True),
        sa.Column('priority', sa.Integer, default=0),
        sa.Column('deny_by_default', sa.Boolean, default=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('name', 'tenant_id', name='uq_security_policy_name_tenant'),
    )
    op.create_index('idx_security_policy_tenant_enabled', 'security_dynamic_policies', ['tenant_id', 'enabled'])
    op.create_index('idx_security_policy_type', 'security_dynamic_policies', ['policy_type'])
    op.create_index('idx_security_policy_priority', 'security_dynamic_policies', ['priority'])
    
    # Create security_sso_providers table
    op.create_table(
        'security_sso_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('protocol', sa.Enum('saml', 'oauth2', 'oidc', 'ldap', name='sso_protocol'), nullable=False),
        sa.Column('entity_id', sa.String(500), nullable=True),
        sa.Column('sso_url', sa.String(500), nullable=True),
        sa.Column('slo_url', sa.String(500), nullable=True),
        sa.Column('certificate', sa.Text, nullable=True),
        sa.Column('client_id', sa.String(200), nullable=True),
        sa.Column('client_secret_encrypted', sa.LargeBinary, nullable=True),
        sa.Column('authorization_url', sa.String(500), nullable=True),
        sa.Column('token_url', sa.String(500), nullable=True),
        sa.Column('userinfo_url', sa.String(500), nullable=True),
        sa.Column('scopes', postgresql.JSONB, default=list),
        sa.Column('ldap_url', sa.String(500), nullable=True),
        sa.Column('ldap_base_dn', sa.String(500), nullable=True),
        sa.Column('ldap_bind_dn', sa.String(500), nullable=True),
        sa.Column('ldap_bind_password_encrypted', sa.LargeBinary, nullable=True),
        sa.Column('ldap_user_filter', sa.String(500), nullable=True),
        sa.Column('ldap_group_filter', sa.String(500), nullable=True),
        sa.Column('attribute_mapping', postgresql.JSONB, default=dict),
        sa.Column('enabled', sa.Boolean, default=True),
        sa.Column('supports_slo', sa.Boolean, default=False),
        sa.Column('auto_create_users', sa.Boolean, default=True),
        sa.Column('default_role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('provider_metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('name', 'tenant_id', name='uq_security_sso_provider_name_tenant'),
    )
    op.create_index('idx_security_sso_provider_tenant_enabled', 'security_sso_providers', ['tenant_id', 'enabled'])
    op.create_index('idx_security_sso_provider_protocol', 'security_sso_providers', ['protocol'])
    
    # Create security_audit_logs table
    op.create_table(
        'security_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('resource', sa.String(200), nullable=True),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('result', sa.Boolean, nullable=True),
        sa.Column('details', postgresql.JSONB, default=dict),
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('previous_hash', sa.String(64), nullable=True),
        sa.Column('hash', sa.String(64), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=True),
        sa.Column('risk_score', sa.Integer, nullable=True),
    )
    op.create_index('idx_security_audit_log_tenant_timestamp', 'security_audit_logs', ['tenant_id', 'timestamp'])
    op.create_index('idx_security_audit_log_user', 'security_audit_logs', ['user_id'])
    op.create_index('idx_security_audit_log_event_type', 'security_audit_logs', ['event_type'])
    op.create_index('idx_security_audit_log_resource', 'security_audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_security_audit_log_timestamp', 'security_audit_logs', ['timestamp'])
    op.create_index('idx_security_audit_log_risk', 'security_audit_logs', ['risk_level'])
    
    # Create security_events table
    op.create_table(
        'security_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', sa.String(100), unique=True, nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.Enum('low', 'medium', 'high', 'critical', name='security_event_severity'), nullable=False),
        sa.Column('status', sa.Enum('open', 'investigating', 'resolved', 'false_positive', name='security_event_status'), default='open'),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('details', postgresql.JSONB, default=dict),
        sa.Column('source_audit_log_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('detection_method', sa.String(100), nullable=True),
        sa.Column('confidence_score', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolution_notes', sa.Text, nullable=True),
        sa.Column('response_actions', postgresql.JSONB, default=list),
    )
    op.create_index('idx_security_event_tenant_status', 'security_events', ['tenant_id', 'status'])
    op.create_index('idx_security_event_severity', 'security_events', ['severity'])
    op.create_index('idx_security_event_type', 'security_events', ['event_type'])
    op.create_index('idx_security_event_created', 'security_events', ['created_at'])
    op.create_index('idx_security_event_user', 'security_events', ['user_id'])
    
    # Create security_sessions table
    op.create_table(
        'security_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.String(100), unique=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('device_fingerprint', sa.String(100), nullable=True),
        sa.Column('sso_provider_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sso_session_id', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('terminated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('termination_reason', sa.String(100), nullable=True),
    )
    op.create_index('idx_security_session_user', 'security_sessions', ['user_id'])
    op.create_index('idx_security_session_tenant', 'security_sessions', ['tenant_id'])
    op.create_index('idx_security_session_active', 'security_sessions', ['is_active', 'expires_at'])
    
    # Create security_encryption_keys table
    op.create_table(
        'security_encryption_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key_id', sa.String(100), unique=True, nullable=False),
        sa.Column('algorithm', sa.String(50), nullable=False, default='AES-256-GCM'),
        sa.Column('key_type', sa.String(50), nullable=False, default='data_encryption'),
        sa.Column('encrypted_key', sa.LargeBinary, nullable=False),
        sa.Column('key_version', sa.Integer, default=1),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_security_encryption_key_status', 'security_encryption_keys', ['status'])
    op.create_index('idx_security_encryption_key_type', 'security_encryption_keys', ['key_type'])
    
    # Create security_compliance_reports table
    op.create_table(
        'security_compliance_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('report_data', postgresql.JSONB, nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('export_format', sa.String(20), nullable=True),
        sa.Column('export_path', sa.String(500), nullable=True),
    )
    op.create_index('idx_security_compliance_report_tenant_type', 'security_compliance_reports', ['tenant_id', 'report_type'])
    op.create_index('idx_security_compliance_report_period', 'security_compliance_reports', ['period_start', 'period_end'])
    
    # Create security_ip_whitelist table
    op.create_table(
        'security_ip_whitelist',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False),
        sa.Column('ip_address', postgresql.INET, nullable=False),
        sa.Column('ip_range', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_security_ip_whitelist_tenant', 'security_ip_whitelist', ['tenant_id', 'is_active'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('security_ip_whitelist')
    op.drop_table('security_compliance_reports')
    op.drop_table('security_encryption_keys')
    op.drop_table('security_sessions')
    op.drop_table('security_events')
    op.drop_table('security_audit_logs')
    op.drop_table('security_sso_providers')
    op.drop_table('security_dynamic_policies')
    op.drop_table('security_user_roles')
    op.drop_table('security_roles')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS policy_type")
    op.execute("DROP TYPE IF EXISTS security_event_status")
    op.execute("DROP TYPE IF EXISTS security_event_severity")
    op.execute("DROP TYPE IF EXISTS sso_protocol")
    op.execute("DROP TYPE IF EXISTS resource_type")
    op.execute("DROP TYPE IF EXISTS permission_scope")
