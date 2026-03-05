"""
Pydantic schemas for LLM configuration API.

Defines request/response models for LLM configuration, application, and binding management.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class LLMConfigCreate(BaseModel):
    """Request schema for creating LLM configuration."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    provider: str = Field(..., min_length=1, max_length=50, description="Provider type")
    api_key: str = Field(..., min_length=1, description="API key (will be encrypted)")
    base_url: Optional[str] = Field(None, max_length=500, description="API base URL")
    model_name: str = Field(..., min_length=1, max_length=100, description="Model name")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional parameters")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID (None for global)")
    
    @field_validator('base_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        return v


class LLMConfigUpdate(BaseModel):
    """Request schema for updating LLM configuration."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Configuration name")
    provider: Optional[str] = Field(None, min_length=1, max_length=50, description="Provider type")
    api_key: Optional[str] = Field(None, min_length=1, description="API key (will be encrypted)")
    base_url: Optional[str] = Field(None, max_length=500, description="API base URL")
    model_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Model name")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")
    is_active: Optional[bool] = Field(None, description="Active status")
    
    @field_validator('base_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        return v


class LLMConfigResponse(BaseModel):
    """Response schema for LLM configuration."""
    
    id: UUID
    name: str
    provider: str
    base_url: Optional[str]
    model_name: str
    parameters: Dict[str, Any]
    is_active: bool
    tenant_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ApplicationResponse(BaseModel):
    """Response schema for application."""
    
    id: UUID
    code: str
    name: str
    description: Optional[str]
    llm_usage_pattern: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LLMBindingCreate(BaseModel):
    """Request schema for creating LLM binding."""
    
    llm_config_id: UUID = Field(..., description="LLM configuration ID")
    application_id: UUID = Field(..., description="Application ID")
    priority: int = Field(..., ge=1, le=99, description="Priority (1=highest)")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=30, gt=0, description="Request timeout in seconds")


class LLMBindingUpdate(BaseModel):
    """Request schema for updating LLM binding."""
    
    priority: Optional[int] = Field(None, ge=1, le=99, description="Priority (1=highest)")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="Maximum retry attempts")
    timeout_seconds: Optional[int] = Field(None, gt=0, description="Request timeout in seconds")
    is_active: Optional[bool] = Field(None, description="Active status")


class LLMBindingResponse(BaseModel):
    """Response schema for LLM binding."""
    
    id: UUID
    llm_config: LLMConfigResponse
    application: ApplicationResponse
    priority: int
    max_retries: int
    timeout_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TestConnectionRequest(BaseModel):
    """Request schema for testing LLM connection."""
    
    prompt: Optional[str] = Field(default="Hello", description="Test prompt")


class TestConnectionResponse(BaseModel):
    """Response schema for connection test."""
    
    status: str = Field(..., description="Test status (success/failed)")
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
    error: Optional[str] = Field(None, description="Error message if failed")
    model: Optional[str] = Field(None, description="Model used for test")
