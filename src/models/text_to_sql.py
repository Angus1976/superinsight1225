"""
SQLAlchemy models for Text-to-SQL Methods module.

Defines database models for configuration persistence,
plugin management, and generation logging.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.database.base import Base


class TextToSQLConfiguration(Base):
    """Text-to-SQL configuration table."""
    __tablename__ = "text_to_sql_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(100), nullable=False, default="default")
    default_method = Column(String(50), nullable=False, default="hybrid")
    template_config = Column(JSONB, nullable=False, default=dict)
    llm_config = Column(JSONB, nullable=False, default=dict)
    hybrid_config = Column(JSONB, nullable=False, default=dict)
    auto_select_enabled = Column(Boolean, nullable=False, default=True)
    fallback_enabled = Column(Boolean, nullable=False, default=True)
    max_retries = Column(Integer, nullable=False, default=3)
    timeout_ms = Column(Integer, nullable=False, default=30000)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_text_to_sql_config_tenant_active', 'tenant_id', 'is_active'),
        Index('ix_text_to_sql_config_name', 'name'),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "name": self.name,
            "default_method": self.default_method,
            "template_config": self.template_config,
            "llm_config": self.llm_config,
            "hybrid_config": self.hybrid_config,
            "auto_select_enabled": self.auto_select_enabled,
            "fallback_enabled": self.fallback_enabled,
            "max_retries": self.max_retries,
            "timeout_ms": self.timeout_ms,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ThirdPartyPlugin(Base):
    """Third-party Text-to-SQL plugin table."""
    __tablename__ = "third_party_plugins"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="1.0.0")
    connection_type = Column(String(50), nullable=False)  # rest_api, grpc, local_sdk
    endpoint = Column(String(500), nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    timeout = Column(Integer, nullable=False, default=30)
    enabled = Column(Boolean, nullable=False, default=True)
    supported_db_types = Column(JSONB, nullable=False, default=list)
    config_schema = Column(JSONB, nullable=False, default=dict)
    extra_config = Column(JSONB, nullable=False, default=dict)
    
    # Health tracking
    is_healthy = Column(Boolean, nullable=False, default=True)
    last_health_check = Column(DateTime, nullable=True)
    health_check_error = Column(Text, nullable=True)
    
    # Statistics
    total_calls = Column(Integer, nullable=False, default=0)
    successful_calls = Column(Integer, nullable=False, default=0)
    failed_calls = Column(Integer, nullable=False, default=0)
    total_response_time_ms = Column(Float, nullable=False, default=0.0)
    last_used = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_third_party_plugin_tenant_name', 'tenant_id', 'name', unique=True),
        Index('ix_third_party_plugin_enabled', 'enabled'),
        Index('ix_third_party_plugin_connection_type', 'connection_type'),
    )
    
    @property
    def average_response_time_ms(self):
        if self.total_calls > 0:
            return self.total_response_time_ms / self.total_calls
        return 0.0
    
    @property
    def success_rate(self):
        if self.total_calls > 0:
            return self.successful_calls / self.total_calls
        return 0.0
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "connection_type": self.connection_type,
            "endpoint": self.endpoint,
            "timeout": self.timeout,
            "enabled": self.enabled,
            "supported_db_types": self.supported_db_types,
            "config_schema": self.config_schema,
            "extra_config": self.extra_config,
            "is_healthy": self.is_healthy,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "average_response_time_ms": self.average_response_time_ms,
            "success_rate": self.success_rate,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SQLGenerationLog(Base):
    """SQL generation log table for tracking and analytics."""
    __tablename__ = "sql_generation_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Request info
    query = Column(Text, nullable=False)
    requested_method = Column(String(100), nullable=True)
    db_type = Column(String(50), nullable=True)
    schema_context_hash = Column(String(64), nullable=True)  # SHA-256 hash of schema context
    
    # Result info
    generated_sql = Column(Text, nullable=False)
    method_used = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    execution_time_ms = Column(Float, nullable=False, default=0.0)
    
    # Status
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Template info (if template method used)
    template_id = Column(String(100), nullable=True)
    template_match_score = Column(Float, nullable=True)
    
    # Plugin info (if third-party method used)
    plugin_name = Column(String(100), nullable=True)
    plugin_response_time_ms = Column(Float, nullable=True)
    
    # Metadata
    metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Indexes for analytics
    __table_args__ = (
        Index('ix_sql_gen_log_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_sql_gen_log_method_created', 'method_used', 'created_at'),
        Index('ix_sql_gen_log_success', 'success'),
        Index('ix_sql_gen_log_user_created', 'user_id', 'created_at'),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "query": self.query,
            "requested_method": self.requested_method,
            "db_type": self.db_type,
            "generated_sql": self.generated_sql,
            "method_used": self.method_used,
            "confidence": self.confidence,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error_message": self.error_message,
            "template_id": self.template_id,
            "plugin_name": self.plugin_name,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SQLTemplate(Base):
    """SQL template table for template-based generation."""
    __tablename__ = "sql_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    
    template_id = Column(String(100), nullable=False)  # Human-readable ID
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)  # aggregate, filter, sort, group, join
    
    # Template definition
    pattern = Column(Text, nullable=False)  # Regex pattern
    template = Column(Text, nullable=False)  # SQL template with placeholders
    param_types = Column(JSONB, nullable=False, default=dict)
    examples = Column(JSONB, nullable=False, default=list)
    
    # Configuration
    priority = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True)
    is_system = Column(Boolean, nullable=False, default=False)  # System templates can't be deleted
    
    # Statistics
    usage_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('ix_sql_template_tenant_id', 'tenant_id', 'template_id', unique=True),
        Index('ix_sql_template_category', 'category'),
        Index('ix_sql_template_enabled_priority', 'enabled', 'priority'),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "pattern": self.pattern,
            "template": self.template,
            "param_types": self.param_types,
            "examples": self.examples,
            "priority": self.priority,
            "enabled": self.enabled,
            "is_system": self.is_system,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
