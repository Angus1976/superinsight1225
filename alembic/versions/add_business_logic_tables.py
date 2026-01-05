"""Add business logic tables

Revision ID: add_business_logic_001
Revises: previous_revision
Create Date: 2026-01-05 12:00:00.000000

实现需求 13: 客户业务逻辑提炼与智能化 - 数据库表结构
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_business_logic_001'
down_revision = None  # 替换为实际的上一个版本ID
branch_labels = None
depends_on = None

def upgrade():
    """创建业务逻辑相关表"""
    
    # 创建业务规则表
    op.create_table(
        'business_rules',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('pattern', sa.Text(), nullable=False),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('frequency', sa.Integer(), default=0),
        sa.Column('examples', postgresql.JSONB(), default=sa.text("'[]'::jsonb")),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # 创建业务规则表索引
    op.create_index('idx_business_rules_project', 'business_rules', ['project_id'])
    op.create_index('idx_business_rules_type', 'business_rules', ['rule_type'])
    op.create_index('idx_business_rules_active', 'business_rules', ['is_active'])
    op.create_index('idx_business_rules_confidence', 'business_rules', ['confidence'])
    op.create_index('idx_business_rules_created', 'business_rules', ['created_at'])
    
    # 创建业务模式表
    op.create_table(
        'business_patterns',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('strength', sa.Float(), default=0.0),
        sa.Column('evidence', postgresql.JSONB(), default=sa.text("'[]'::jsonb")),
        sa.Column('detected_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_seen', sa.DateTime(), server_default=sa.func.now())
    )
    
    # 创建业务模式表索引
    op.create_index('idx_business_patterns_project', 'business_patterns', ['project_id'])
    op.create_index('idx_business_patterns_type', 'business_patterns', ['pattern_type'])
    op.create_index('idx_business_patterns_strength', 'business_patterns', ['strength'])
    op.create_index('idx_business_patterns_detected', 'business_patterns', ['detected_at'])
    op.create_index('idx_business_patterns_last_seen', 'business_patterns', ['last_seen'])
    
    # 创建业务洞察表
    op.create_table(
        'business_insights',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('insight_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('impact_score', sa.Float(), default=0.0),
        sa.Column('recommendations', postgresql.JSONB(), default=sa.text("'[]'::jsonb")),
        sa.Column('data_points', postgresql.JSONB(), default=sa.text("'[]'::jsonb")),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True)
    )
    
    # 创建业务洞察表索引
    op.create_index('idx_business_insights_project', 'business_insights', ['project_id'])
    op.create_index('idx_business_insights_type', 'business_insights', ['insight_type'])
    op.create_index('idx_business_insights_impact', 'business_insights', ['impact_score'])
    op.create_index('idx_business_insights_created', 'business_insights', ['created_at'])
    op.create_index('idx_business_insights_acknowledged', 'business_insights', ['acknowledged_at'])
    
    # 创建业务逻辑分析历史表（用于跟踪分析历史）
    op.create_table(
        'business_logic_analysis_history',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),  # pattern_analysis, rule_extraction
        sa.Column('parameters', postgresql.JSONB(), default=sa.text("'{}'::jsonb")),
        sa.Column('results_summary', postgresql.JSONB(), default=sa.text("'{}'::jsonb")),
        sa.Column('execution_time_ms', sa.Integer(), default=0),
        sa.Column('status', sa.String(20), default='completed'),  # running, completed, failed
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True)
    )
    
    # 创建分析历史表索引
    op.create_index('idx_analysis_history_project', 'business_logic_analysis_history', ['project_id'])
    op.create_index('idx_analysis_history_type', 'business_logic_analysis_history', ['analysis_type'])
    op.create_index('idx_analysis_history_status', 'business_logic_analysis_history', ['status'])
    op.create_index('idx_analysis_history_created', 'business_logic_analysis_history', ['created_at'])
    
    # 创建规则应用历史表（用于跟踪规则应用）
    op.create_table(
        'business_rule_applications',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('source_project_id', sa.String(100), nullable=False),
        sa.Column('target_project_id', sa.String(100), nullable=False),
        sa.Column('rule_id', sa.String(100), nullable=False),
        sa.Column('application_mode', sa.String(20), default='copy'),  # copy, reference, adapt
        sa.Column('original_confidence', sa.Float(), default=0.0),
        sa.Column('applied_confidence', sa.Float(), default=0.0),
        sa.Column('status', sa.String(20), default='active'),  # active, inactive, removed
        sa.Column('applied_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # 创建规则应用历史表索引
    op.create_index('idx_rule_applications_source', 'business_rule_applications', ['source_project_id'])
    op.create_index('idx_rule_applications_target', 'business_rule_applications', ['target_project_id'])
    op.create_index('idx_rule_applications_rule', 'business_rule_applications', ['rule_id'])
    op.create_index('idx_rule_applications_status', 'business_rule_applications', ['status'])
    op.create_index('idx_rule_applications_applied', 'business_rule_applications', ['applied_at'])
    
    # 创建通知偏好表（用于业务洞察通知）
    op.create_table(
        'business_logic_notifications',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('project_id', sa.String(100), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),  # new_pattern, rule_change, insight_generated
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB(), default=sa.text("'{}'::jsonb")),
        sa.Column('status', sa.String(20), default='unread'),  # unread, read, dismissed
        sa.Column('delivery_method', sa.String(20), default='web'),  # web, email, sms, webhook
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('dismissed_at', sa.DateTime(), nullable=True)
    )
    
    # 创建通知表索引
    op.create_index('idx_notifications_user', 'business_logic_notifications', ['user_id'])
    op.create_index('idx_notifications_project', 'business_logic_notifications', ['project_id'])
    op.create_index('idx_notifications_type', 'business_logic_notifications', ['notification_type'])
    op.create_index('idx_notifications_status', 'business_logic_notifications', ['status'])
    op.create_index('idx_notifications_created', 'business_logic_notifications', ['created_at'])

def downgrade():
    """删除业务逻辑相关表"""
    
    # 删除通知表
    op.drop_table('business_logic_notifications')
    
    # 删除规则应用历史表
    op.drop_table('business_rule_applications')
    
    # 删除分析历史表
    op.drop_table('business_logic_analysis_history')
    
    # 删除业务洞察表
    op.drop_table('business_insights')
    
    # 删除业务模式表
    op.drop_table('business_patterns')
    
    # 删除业务规则表
    op.drop_table('business_rules')