"""
LLM Configuration Database Models for SuperInsight platform.

Defines SQLAlchemy models for LLM configuration persistence and usage logging.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, Boolean, Integer, Float, Text, DateTime, 
    ForeignKey, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

try:
    from src.database.base import Base
except ImportError:
    from database.base import Base


class LLMConfiguration(Base):
    """
    LLM Configuration table for storing provider configurations.
    
    Supports multi-tenant configuration with tenant isolation.
    """
    __tablename__ = "llm_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE", use_alter=True, name="fk_llm_config_tenant"), nullable=True, index=True)
    
    # Configuration data stored as JSONB for flexibility
    config_data = Column(JSONB, nullable=False, default=dict)
    
    # Provider type (openai, azure, anthropic, ollama, custom)
    provider = Column(String(50), nullable=False)
    
    # Default method for this configuration
    default_method = Column(String(50), nullable=False, default="local_ollama")
    
    # Status flags
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_llm_config_created_by"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_llm_config_updated_by"), nullable=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_llm_config_tenant_active', 'tenant_id', 'is_active'),
        Index('ix_llm_config_tenant_default', 'tenant_id', 'is_default'),
        Index('ix_llm_config_method', 'default_method'),
        {'extend_existing': True}
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "config_data": self.config_data,
            "default_method": self.default_method,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class LLMUsageLog(Base):
    """
    LLM Usage Log table for tracking API calls and token usage.
    
    Used for billing, analytics, and monitoring.
    """
    __tablename__ = "llm_usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(String(100), ForeignKey("tenants.id", ondelete="CASCADE", use_alter=True, name="fk_llm_usage_tenant"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_llm_usage_user"), nullable=True, index=True)
    
    # Request details
    method = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    operation = Column(String(50), nullable=False, default="generate")  # generate, embed, stream
    
    # Token usage
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    
    # Performance metrics
    latency_ms = Column(Float, default=0.0, nullable=False)
    
    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Request/Response metadata (optional, for debugging)
    request_metadata = Column(JSONB, nullable=True)
    response_metadata = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Indexes for analytics queries
    __table_args__ = (
        Index('ix_llm_usage_tenant_created', 'tenant_id', 'created_at'),
        Index('ix_llm_usage_method_created', 'method', 'created_at'),
        Index('ix_llm_usage_user_created', 'user_id', 'created_at'),
        Index('ix_llm_usage_success', 'success', 'created_at'),
        {'extend_existing': True}
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "method": self.method,
            "model": self.model,
            "operation": self.operation,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def create_log(
        cls,
        method: str,
        model: str,
        operation: str = "generate",
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
        response_metadata: Optional[Dict[str, Any]] = None,
    ) -> "LLMUsageLog":
        """Factory method to create a usage log entry."""
        return cls(
            tenant_id=tenant_id,
            user_id=user_id,
            method=method,
            model=model,
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            success=success,
            error_code=error_code,
            error_message=error_message,
            request_metadata=request_metadata,
            response_metadata=response_metadata,
        )


class LLMModelRegistry(Base):
    """
    LLM Model Registry for tracking available models per provider.
    
    Caches model information to avoid repeated API calls.
    """
    __tablename__ = "llm_model_registry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Model identification
    method = Column(String(50), nullable=False)
    model_id = Column(String(100), nullable=False)
    model_name = Column(String(255), nullable=False)
    
    # Model capabilities
    supports_chat = Column(Boolean, default=True, nullable=False)
    supports_completion = Column(Boolean, default=True, nullable=False)
    supports_embedding = Column(Boolean, default=False, nullable=False)
    supports_streaming = Column(Boolean, default=True, nullable=False)
    
    # Model limits
    max_tokens = Column(Integer, nullable=True)
    context_window = Column(Integer, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    model_metadata = Column(JSONB, nullable=True)
    
    # Status
    is_available = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('ix_llm_model_method_id', 'method', 'model_id', unique=True),
        Index('ix_llm_model_available', 'is_available'),
        {'extend_existing': True}
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "method": self.method,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "supports_chat": self.supports_chat,
            "supports_completion": self.supports_completion,
            "supports_embedding": self.supports_embedding,
            "supports_streaming": self.supports_streaming,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
            "description": self.description,
            "is_available": self.is_available,
        }


class LLMHealthStatus(Base):
    """
    LLM Health Status table for tracking provider health.
    
    Monitors the health of LLM providers with automatic health checks.
    """
    __tablename__ = "llm_health_status"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("llm_configurations.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Health status
    is_healthy = Column(Boolean, nullable=False, default=True)
    last_check_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_error = Column(String(500), nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes for health monitoring queries
    __table_args__ = (
        Index('ix_llm_health_provider', 'provider_id'),
        Index('ix_llm_health_status', 'is_healthy'),
        Index('ix_llm_health_last_check', 'last_check_at'),
        {'extend_existing': True}
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "provider_id": str(self.provider_id),
            "is_healthy": self.is_healthy,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
