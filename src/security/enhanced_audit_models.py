"""
Enhanced Audit Models for SuperInsight Platform.

扩展的审计数据库模型，支持企业级审计功能。
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from uuid import uuid4

from src.database.connection import Base


class EventCategory(str, Enum):
    """审计事件分类"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_ADMINISTRATION = "system_administration"
    SECURITY_VIOLATION = "security_violation"
    COMPLIANCE = "compliance"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProcessingStatus(str, Enum):
    """处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_ATTENTION = "requires_attention"


class AlertStatus(str, Enum):
    """告警状态"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class ReportStatus(str, Enum):
    """报告状态"""
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class AuditEventModel(Base):
    """审计事件模型"""
    __tablename__ = "audit_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    audit_log_id = Column(UUID(as_uuid=True), ForeignKey('audit_logs.id'), nullable=False)
    event_category = Column(String(50), nullable=False)
    risk_level = Column(String(20), nullable=False)
    risk_score = Column(Integer, nullable=False, default=0)
    processing_status = Column(String(30), nullable=False, default=ProcessingStatus.PENDING.value)
    anomalies_detected = Column(JSONB, nullable=True)
    recommendations = Column(JSONB, nullable=True)
    processing_metadata = Column(JSONB, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<AuditEvent(id={self.id}, category={self.event_category}, risk={self.risk_level})>"


class SecurityAlertModel(Base):
    """安全告警模型"""
    __tablename__ = "security_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(36), nullable=False)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_data = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, default=AlertStatus.OPEN.value)
    assigned_to = Column(String(36), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SecurityAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"


class AuditRuleModel(Base):
    """审计规则模型"""
    __tablename__ = "audit_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(36), nullable=True)  # NULL表示全局规则
    rule_name = Column(String(100), nullable=False)
    rule_type = Column(String(50), nullable=False)
    conditions = Column(JSONB, nullable=False)
    actions = Column(JSONB, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<AuditRule(id={self.id}, name={self.rule_name}, type={self.rule_type})>"


class ComplianceReportModel(Base):
    """合规报告模型"""
    __tablename__ = "compliance_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(36), nullable=False)
    report_type = Column(String(50), nullable=False)
    report_name = Column(String(200), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    report_data = Column(JSONB, nullable=False)
    file_path = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default=ReportStatus.GENERATING.value)
    generated_by = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<ComplianceReport(id={self.id}, type={self.report_type}, status={self.status})>"


# 扩展现有的AuditLogModel以添加新字段
def extend_audit_log_model():
    """扩展现有的AuditLogModel"""
    from src.security.models import AuditLogModel
    
    # 添加新字段（如果还没有的话）
    if not hasattr(AuditLogModel, 'workspace_id'):
        AuditLogModel.workspace_id = Column(String(36), nullable=True)
    
    if not hasattr(AuditLogModel, 'session_id'):
        AuditLogModel.session_id = Column(String(100), nullable=True)
    
    if not hasattr(AuditLogModel, 'correlation_id'):
        AuditLogModel.correlation_id = Column(String(100), nullable=True)
    
    if not hasattr(AuditLogModel, 'source_system'):
        AuditLogModel.source_system = Column(String(50), nullable=True)
    
    if not hasattr(AuditLogModel, 'event_version'):
        AuditLogModel.event_version = Column(String(10), nullable=False, default='1.0')


# 审计统计数据传输对象
class AuditStatistics:
    """审计统计DTO"""
    
    def __init__(self, data: dict):
        self.tenant_id = data.get('tenant_id')
        self.audit_date = data.get('audit_date')
        self.action = data.get('action')
        self.resource_type = data.get('resource_type')
        self.event_count = data.get('event_count', 0)
        self.unique_users = data.get('unique_users', 0)
        self.unique_ips = data.get('unique_ips', 0)
        self.avg_risk_score = data.get('avg_risk_score', 0.0)
    
    def to_dict(self) -> dict:
        return {
            'tenant_id': self.tenant_id,
            'audit_date': self.audit_date.isoformat() if self.audit_date else None,
            'action': self.action,
            'resource_type': self.resource_type,
            'event_count': self.event_count,
            'unique_users': self.unique_users,
            'unique_ips': self.unique_ips,
            'avg_risk_score': round(float(self.avg_risk_score), 2) if self.avg_risk_score else 0.0
        }


class HighRiskEvent:
    """高风险事件DTO"""
    
    def __init__(self, audit_log_data: dict, audit_event_data: dict = None):
        # 审计日志数据
        self.id = audit_log_data.get('id')
        self.user_id = audit_log_data.get('user_id')
        self.tenant_id = audit_log_data.get('tenant_id')
        self.workspace_id = audit_log_data.get('workspace_id')
        self.action = audit_log_data.get('action')
        self.resource_type = audit_log_data.get('resource_type')
        self.resource_id = audit_log_data.get('resource_id')
        self.ip_address = audit_log_data.get('ip_address')
        self.user_agent = audit_log_data.get('user_agent')
        self.timestamp = audit_log_data.get('timestamp')
        self.details = audit_log_data.get('details', {})
        
        # 审计事件数据
        if audit_event_data:
            self.event_category = audit_event_data.get('event_category')
            self.risk_level = audit_event_data.get('risk_level')
            self.risk_score = audit_event_data.get('risk_score', 0)
            self.anomalies_detected = audit_event_data.get('anomalies_detected', [])
        else:
            # 从details中提取
            self.event_category = self.details.get('event_category')
            self.risk_level = self.details.get('risk_level')
            self.risk_score = self.details.get('risk_score', 0)
            self.anomalies_detected = self.details.get('anomalies_detected', [])
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': str(self.user_id) if self.user_id else None,
            'tenant_id': self.tenant_id,
            'workspace_id': self.workspace_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'event_category': self.event_category,
            'risk_level': self.risk_level,
            'risk_score': self.risk_score,
            'anomalies_detected': self.anomalies_detected,
            'details': self.details
        }