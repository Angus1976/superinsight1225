"""Extend audit tables for enhanced audit functionality

Revision ID: 004_extend_audit_tables
Revises: 003_add_workspace_columns
Create Date: 2026-01-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_extend_audit_tables'
down_revision = '003_add_workspace_columns'
branch_labels = None
depends_on = None


def upgrade():
    """扩展审计表以支持企业级审计功能"""
    
    # 创建审计事件表
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('audit_log_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('audit_logs.id'), nullable=False),
        sa.Column('event_category', sa.String(50), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('risk_score', sa.Integer, nullable=False, default=0),
        sa.Column('processing_status', sa.String(30), nullable=False, default='pending'),
        sa.Column('anomalies_detected', postgresql.JSONB, nullable=True),
        sa.Column('recommendations', postgresql.JSONB, nullable=True),
        sa.Column('processing_metadata', postgresql.JSONB, nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # 创建索引
    op.create_index('idx_audit_events_audit_log_id', 'audit_events', ['audit_log_id'])
    op.create_index('idx_audit_events_category', 'audit_events', ['event_category'])
    op.create_index('idx_audit_events_risk_level', 'audit_events', ['risk_level'])
    op.create_index('idx_audit_events_status', 'audit_events', ['processing_status'])
    op.create_index('idx_audit_events_processed_at', 'audit_events', ['processed_at'])
    
    # 创建安全告警表
    op.create_table(
        'security_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('event_data', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='open'),
        sa.Column('assigned_to', sa.String(36), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # 创建索引
    op.create_index('idx_security_alerts_tenant_id', 'security_alerts', ['tenant_id'])
    op.create_index('idx_security_alerts_type', 'security_alerts', ['alert_type'])
    op.create_index('idx_security_alerts_severity', 'security_alerts', ['severity'])
    op.create_index('idx_security_alerts_status', 'security_alerts', ['status'])
    op.create_index('idx_security_alerts_created_at', 'security_alerts', ['created_at'])
    
    # 创建审计规则表
    op.create_table(
        'audit_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=True),  # NULL表示全局规则
        sa.Column('rule_name', sa.String(100), nullable=False),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('conditions', postgresql.JSONB, nullable=False),
        sa.Column('actions', postgresql.JSONB, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('priority', sa.Integer, nullable=False, default=100),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # 创建索引
    op.create_index('idx_audit_rules_tenant_id', 'audit_rules', ['tenant_id'])
    op.create_index('idx_audit_rules_type', 'audit_rules', ['rule_type'])
    op.create_index('idx_audit_rules_active', 'audit_rules', ['is_active'])
    op.create_index('idx_audit_rules_priority', 'audit_rules', ['priority'])
    
    # 创建合规报告表
    op.create_table(
        'compliance_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('report_name', sa.String(200), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('report_data', postgresql.JSONB, nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='generating'),
        sa.Column('generated_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # 创建索引
    op.create_index('idx_compliance_reports_tenant_id', 'compliance_reports', ['tenant_id'])
    op.create_index('idx_compliance_reports_type', 'compliance_reports', ['report_type'])
    op.create_index('idx_compliance_reports_status', 'compliance_reports', ['status'])
    op.create_index('idx_compliance_reports_period', 'compliance_reports', ['period_start', 'period_end'])
    
    # 扩展现有audit_logs表
    op.add_column('audit_logs', sa.Column('workspace_id', sa.String(36), nullable=True))
    op.add_column('audit_logs', sa.Column('session_id', sa.String(100), nullable=True))
    op.add_column('audit_logs', sa.Column('correlation_id', sa.String(100), nullable=True))
    op.add_column('audit_logs', sa.Column('source_system', sa.String(50), nullable=True))
    op.add_column('audit_logs', sa.Column('event_version', sa.String(10), nullable=False, server_default='1.0'))
    
    # 为新列创建索引
    op.create_index('idx_audit_logs_workspace_id', 'audit_logs', ['workspace_id'])
    op.create_index('idx_audit_logs_session_id', 'audit_logs', ['session_id'])
    op.create_index('idx_audit_logs_correlation_id', 'audit_logs', ['correlation_id'])
    op.create_index('idx_audit_logs_source_system', 'audit_logs', ['source_system'])
    
    # 创建审计统计视图
    op.execute("""
        CREATE OR REPLACE VIEW audit_statistics AS
        SELECT 
            tenant_id,
            DATE(timestamp) as audit_date,
            action,
            resource_type,
            COUNT(*) as event_count,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(DISTINCT ip_address) as unique_ips,
            AVG(CASE WHEN details->>'risk_score' IS NOT NULL 
                THEN (details->>'risk_score')::integer 
                ELSE 0 END) as avg_risk_score
        FROM audit_logs 
        WHERE timestamp >= CURRENT_DATE - interval '30 days'
        GROUP BY tenant_id, DATE(timestamp), action, resource_type;
    """)
    
    # 创建高风险事件视图
    op.execute("""
        CREATE OR REPLACE VIEW high_risk_events AS
        SELECT 
            al.*,
            ae.event_category,
            ae.risk_level,
            ae.risk_score,
            ae.anomalies_detected
        FROM audit_logs al
        LEFT JOIN audit_events ae ON al.id = ae.audit_log_id
        WHERE (al.details->>'risk_level' IN ('high', 'critical'))
           OR (ae.risk_level IN ('high', 'critical'))
        ORDER BY al.timestamp DESC;
    """)


def downgrade():
    """回滚审计表扩展"""
    
    # 删除视图
    op.execute("DROP VIEW IF EXISTS high_risk_events")
    op.execute("DROP VIEW IF EXISTS audit_statistics")
    
    # 删除audit_logs表的新列
    op.drop_index('idx_audit_logs_source_system')
    op.drop_index('idx_audit_logs_correlation_id')
    op.drop_index('idx_audit_logs_session_id')
    op.drop_index('idx_audit_logs_workspace_id')
    
    op.drop_column('audit_logs', 'event_version')
    op.drop_column('audit_logs', 'source_system')
    op.drop_column('audit_logs', 'correlation_id')
    op.drop_column('audit_logs', 'session_id')
    op.drop_column('audit_logs', 'workspace_id')
    
    # 删除合规报告表
    op.drop_index('idx_compliance_reports_period')
    op.drop_index('idx_compliance_reports_status')
    op.drop_index('idx_compliance_reports_type')
    op.drop_index('idx_compliance_reports_tenant_id')
    op.drop_table('compliance_reports')
    
    # 删除审计规则表
    op.drop_index('idx_audit_rules_priority')
    op.drop_index('idx_audit_rules_active')
    op.drop_index('idx_audit_rules_type')
    op.drop_index('idx_audit_rules_tenant_id')
    op.drop_table('audit_rules')
    
    # 删除安全告警表
    op.drop_index('idx_security_alerts_created_at')
    op.drop_index('idx_security_alerts_status')
    op.drop_index('idx_security_alerts_severity')
    op.drop_index('idx_security_alerts_type')
    op.drop_index('idx_security_alerts_tenant_id')
    op.drop_table('security_alerts')
    
    # 删除审计事件表
    op.drop_index('idx_audit_events_processed_at')
    op.drop_index('idx_audit_events_status')
    op.drop_index('idx_audit_events_risk_level')
    op.drop_index('idx_audit_events_category')
    op.drop_index('idx_audit_events_audit_log_id')
    op.drop_table('audit_events')