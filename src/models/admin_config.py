"""
Admin Configuration Database Models for SuperInsight Platform.

Defines SQLAlchemy models for admin configuration persistence including:
- Admin configurations (general settings)
- Database connections
- Configuration change history
- Query templates
- Third-party tool configurations
- Sync strategies
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, Boolean, Integer, Float, Text, DateTime,
    ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

try:
    from src.database.connection import Base
except ImportError:
    from database.connection import Base


class AdminConfiguration(Base):
    """
    General admin configuration table.
    
    Stores various configuration types as JSONB for flexibility.
    Supports multi-tenant configuration with tenant isolation.
    """
    __tablename__ = "admin_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Configuration identification
    config_type = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    # Configuration data stored as JSONB
    config_data = Column(JSONB, nullable=False, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    __table_args__ = (
        Index('ix_admin_config_tenant_type', 'tenant_id', 'config_type'),
        Index('ix_admin_config_type_active', 'config_type', 'is_active'),
        Index('ix_admin_config_tenant_default', 'tenant_id', 'is_default'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "config_type": self.config_type,
            "name": self.name,
            "description": self.description,
            "config_data": self.config_data,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DatabaseConnection(Base):
    """
    Database connection configuration table.
    
    Stores customer database connection details with encrypted credentials.
    """
    __tablename__ = "database_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Connection identification
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Database type
    db_type = Column(String(50), nullable=False)  # postgresql, mysql, sqlite, oracle, sqlserver
    
    # Connection parameters
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    password_encrypted = Column(Text, nullable=True)  # Encrypted password
    
    # Connection options
    is_readonly = Column(Boolean, default=True, nullable=False)
    ssl_enabled = Column(Boolean, default=False, nullable=False)
    extra_config = Column(JSONB, default=dict)  # Additional connection parameters
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(50), nullable=True)  # success, failed
    last_test_latency_ms = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    sync_strategies = relationship("SyncStrategy", back_populates="db_connection", cascade="all, delete-orphan")
    query_templates = relationship("QueryTemplate", back_populates="db_connection", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_db_conn_tenant_active', 'tenant_id', 'is_active'),
        Index('ix_db_conn_type', 'db_type'),
        Index('ix_db_conn_name', 'name'),
    )
    
    def to_dict(self, mask_password: bool = True) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "name": self.name,
            "description": self.description,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "password_masked": "****" if self.password_encrypted else None,
            "is_readonly": self.is_readonly,
            "ssl_enabled": self.ssl_enabled,
            "extra_config": self.extra_config,
            "is_active": self.is_active,
            "last_test_at": self.last_test_at.isoformat() if self.last_test_at else None,
            "last_test_status": self.last_test_status,
            "last_test_latency_ms": self.last_test_latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConfigChangeHistory(Base):
    """
    Configuration change history table.
    
    Records all configuration changes for audit and rollback purposes.
    """
    __tablename__ = "config_change_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Change identification
    config_type = Column(String(50), nullable=False, index=True)
    config_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Reference to the changed config
    
    # Change details
    old_value = Column(JSONB, nullable=True)  # Previous configuration
    new_value = Column(JSONB, nullable=False)  # New configuration
    
    # Change metadata
    change_reason = Column(Text, nullable=True)
    
    # User who made the change
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_name = Column(String(100), nullable=True)  # Denormalized for quick access
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('ix_config_history_tenant_type', 'tenant_id', 'config_type'),
        Index('ix_config_history_config_id', 'config_id'),
        Index('ix_config_history_user_created', 'user_id', 'created_at'),
        Index('ix_config_history_created', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "config_type": self.config_type,
            "config_id": str(self.config_id) if self.config_id else None,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "change_reason": self.change_reason,
            "user_id": str(self.user_id) if self.user_id else None,
            "user_name": self.user_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QueryTemplate(Base):
    """
    SQL query template table.
    
    Stores saved SQL queries for reuse.
    """
    __tablename__ = "query_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    db_config_id = Column(UUID(as_uuid=True), ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Template identification
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Query configuration
    query_config = Column(JSONB, nullable=False)  # QueryConfig as JSON
    sql = Column(Text, nullable=False)  # Generated SQL
    
    # Metadata
    is_public = Column(Boolean, default=False, nullable=False)  # Shared with all users
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Relationships
    db_connection = relationship("DatabaseConnection", back_populates="query_templates")
    
    __table_args__ = (
        Index('ix_query_template_tenant', 'tenant_id'),
        Index('ix_query_template_db_config', 'db_config_id'),
        Index('ix_query_template_name', 'name'),
        Index('ix_query_template_public', 'is_public'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "db_config_id": str(self.db_config_id),
            "name": self.name,
            "description": self.description,
            "query_config": self.query_config,
            "sql": self.sql,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
        }


class SyncStrategy(Base):
    """
    Data synchronization strategy table.
    
    Defines how data is synchronized from customer databases.
    """
    __tablename__ = "sync_strategies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    db_config_id = Column(UUID(as_uuid=True), ForeignKey("database_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Strategy identification
    name = Column(String(100), nullable=True)
    
    # Sync configuration
    mode = Column(String(20), nullable=False, default="full")  # full, incremental, realtime
    incremental_field = Column(String(100), nullable=True)  # Field for incremental sync
    schedule = Column(String(100), nullable=True)  # Cron expression
    filter_conditions = Column(JSONB, default=list)  # List of filter conditions
    batch_size = Column(Integer, default=1000, nullable=False)
    
    # Status
    enabled = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)  # success, failed, running
    last_sync_records = Column(Integer, nullable=True)
    last_sync_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    db_connection = relationship("DatabaseConnection", back_populates="sync_strategies")
    sync_history = relationship("SyncHistory", back_populates="strategy", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_sync_strategy_tenant', 'tenant_id'),
        Index('ix_sync_strategy_db_config', 'db_config_id'),
        Index('ix_sync_strategy_enabled', 'enabled'),
        Index('ix_sync_strategy_mode', 'mode'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "db_config_id": str(self.db_config_id),
            "name": self.name,
            "mode": self.mode,
            "incremental_field": self.incremental_field,
            "schedule": self.schedule,
            "filter_conditions": self.filter_conditions,
            "batch_size": self.batch_size,
            "enabled": self.enabled,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_status": self.last_sync_status,
            "last_sync_records": self.last_sync_records,
            "last_sync_error": self.last_sync_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SyncHistory(Base):
    """
    Sync execution history table.
    
    Records each sync execution for monitoring and debugging.
    """
    __tablename__ = "sync_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("sync_strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Execution details
    status = Column(String(50), nullable=False, default="running")  # running, success, failed
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    records_synced = Column(Integer, default=0, nullable=False)
    records_failed = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)  # Additional execution details
    
    # Relationships
    strategy = relationship("SyncStrategy", back_populates="sync_history")
    
    __table_args__ = (
        Index('ix_sync_history_strategy', 'strategy_id'),
        Index('ix_sync_history_status', 'status'),
        Index('ix_sync_history_started', 'started_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "strategy_id": str(self.strategy_id),
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "records_synced": self.records_synced,
            "records_failed": self.records_failed,
            "error_message": self.error_message,
            "details": self.details,
        }


class ThirdPartyToolConfig(Base):
    """
    Third-party tool configuration table.
    
    Stores configurations for external tools and services.
    """
    __tablename__ = "third_party_tool_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Tool identification
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    tool_type = Column(String(50), nullable=False)  # text_to_sql, ai_annotation, data_processing, custom
    
    # Connection configuration
    endpoint = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text, nullable=True)  # Encrypted API key
    timeout_seconds = Column(Integer, default=30, nullable=False)
    extra_config = Column(JSONB, default=dict)
    
    # Status
    enabled = Column(Boolean, default=True, nullable=False)
    health_status = Column(String(50), nullable=True)  # healthy, unhealthy, unknown
    last_health_check = Column(DateTime, nullable=True)
    
    # Usage statistics
    call_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    total_latency_ms = Column(Float, default=0.0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    __table_args__ = (
        Index('ix_third_party_tenant', 'tenant_id'),
        Index('ix_third_party_type', 'tool_type'),
        Index('ix_third_party_enabled', 'enabled'),
        Index('ix_third_party_name', 'name'),
    )
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.call_count == 0:
            return 0.0
        return self.success_count / self.call_count
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.call_count == 0:
            return 0.0
        return self.total_latency_ms / self.call_count
    
    def to_dict(self, mask_api_key: bool = True) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type,
            "endpoint": self.endpoint,
            "api_key_masked": "****" if self.api_key_encrypted else None,
            "timeout_seconds": self.timeout_seconds,
            "extra_config": self.extra_config,
            "enabled": self.enabled,
            "health_status": self.health_status,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "call_count": self.call_count,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
