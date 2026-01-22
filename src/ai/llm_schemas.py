"""
LLM Integration Schemas for SuperInsight platform.

Defines Pydantic models for LLM configuration, requests, responses, and errors.
"""

from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class LLMMethod(str, Enum):
    """Supported LLM methods/providers."""
    LOCAL_OLLAMA = "local_ollama"
    CLOUD_OPENAI = "cloud_openai"
    CLOUD_AZURE = "cloud_azure"
    CHINA_QWEN = "china_qwen"
    CHINA_ZHIPU = "china_zhipu"
    CHINA_BAIDU = "china_baidu"
    CHINA_HUNYUAN = "china_hunyuan"


class LLMErrorCode(str, Enum):
    """LLM error codes for unified error handling."""
    SERVICE_UNAVAILABLE = "LLM_SERVICE_UNAVAILABLE"
    INVALID_API_KEY = "LLM_INVALID_API_KEY"
    TIMEOUT = "LLM_TIMEOUT"
    RATE_LIMITED = "LLM_RATE_LIMITED"
    MODEL_NOT_FOUND = "LLM_MODEL_NOT_FOUND"
    INVALID_CONFIG = "LLM_INVALID_CONFIG"
    NETWORK_ERROR = "LLM_NETWORK_ERROR"
    INVALID_REQUEST = "LLM_INVALID_REQUEST"
    GENERATION_FAILED = "LLM_GENERATION_FAILED"


class GenerateOptions(BaseModel):
    """Options for text generation."""
    
    max_tokens: int = Field(default=1000, ge=1, le=32000, description="Maximum tokens to generate")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling parameter")
    top_k: Optional[int] = Field(default=None, ge=1, description="Top-k sampling parameter")
    stop_sequences: List[str] = Field(default_factory=list, description="Stop sequences")
    stream: bool = Field(default=False, description="Enable streaming response")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    
    model_config = ConfigDict(extra='allow')


class TokenUsage(BaseModel):
    """Token usage statistics."""
    
    prompt_tokens: int = Field(default=0, ge=0, description="Number of prompt tokens")
    completion_tokens: int = Field(default=0, ge=0, description="Number of completion tokens")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens used")
    
    @classmethod
    def from_counts(cls, prompt: int, completion: int) -> "TokenUsage":
        """Create TokenUsage from prompt and completion counts."""
        return cls(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion
        )


class LLMResponse(BaseModel):
    """Unified LLM response format."""
    
    content: str = Field(..., description="Generated text content")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token usage statistics")
    model: str = Field(..., description="Model name used for generation")
    provider: str = Field(..., description="Provider/method used")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Response latency in milliseconds")
    finish_reason: Optional[str] = Field(default=None, description="Reason for completion")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    cached: bool = Field(default=False, description="Whether this response was served from cache")
    
    model_config = ConfigDict(extra='allow')


class EmbeddingResponse(BaseModel):
    """Embedding/vector response format."""
    
    embedding: List[float] = Field(..., description="Embedding vector")
    model: str = Field(..., description="Model name used for embedding")
    provider: str = Field(..., description="Provider/method used")
    dimensions: int = Field(..., ge=1, description="Embedding dimensions")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Response latency in milliseconds")


class LLMError(BaseModel):
    """Unified LLM error format."""
    
    error_code: LLMErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    provider: str = Field(..., description="Provider that raised the error")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    retry_after: Optional[int] = Field(default=None, ge=0, description="Seconds to wait before retry")
    suggestions: List[str] = Field(default_factory=list, description="Suggested actions")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class LocalConfig(BaseModel):
    """Configuration for local LLM (Ollama)."""
    
    ollama_url: str = Field(default="http://localhost:11434", description="Ollama service URL")
    default_model: str = Field(default="qwen:7b", description="Default model name")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    
    @field_validator('ollama_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate Ollama URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('ollama_url must start with http:// or https://')
        return v.rstrip('/')


class CloudConfig(BaseModel):
    """Configuration for cloud LLM providers."""
    
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_base_url: str = Field(default="https://api.openai.com/v1", description="OpenAI base URL")
    openai_model: str = Field(default="gpt-3.5-turbo", description="Default OpenAI model")
    azure_endpoint: Optional[str] = Field(default=None, description="Azure OpenAI endpoint")
    azure_api_key: Optional[str] = Field(default=None, description="Azure OpenAI API key")
    azure_deployment: Optional[str] = Field(default=None, description="Azure deployment name")
    azure_api_version: str = Field(default="2024-02-15-preview", description="Azure API version")
    timeout: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")


class ChinaLLMConfig(BaseModel):
    """Configuration for China LLM providers."""
    
    # Qwen (阿里云通义千问)
    qwen_api_key: Optional[str] = Field(default=None, description="Qwen/DashScope API key")
    qwen_model: str = Field(default="qwen-turbo", description="Default Qwen model")
    
    # Zhipu (智谱 GLM)
    zhipu_api_key: Optional[str] = Field(default=None, description="Zhipu API key")
    zhipu_model: str = Field(default="glm-4", description="Default Zhipu model")
    
    # Baidu (百度文心一言)
    baidu_api_key: Optional[str] = Field(default=None, description="Baidu API key")
    baidu_secret_key: Optional[str] = Field(default=None, description="Baidu secret key")
    baidu_model: str = Field(default="ernie-bot-4", description="Default Baidu model")
    
    # Hunyuan (腾讯混元)
    hunyuan_secret_id: Optional[str] = Field(default=None, description="Tencent secret ID")
    hunyuan_secret_key: Optional[str] = Field(default=None, description="Tencent secret key")
    hunyuan_model: str = Field(default="hunyuan-lite", description="Default Hunyuan model")
    
    timeout: int = Field(default=60, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=5, ge=0, le=10, description="Maximum retry attempts")


class LLMConfig(BaseModel):
    """Complete LLM configuration."""
    
    default_method: LLMMethod = Field(default=LLMMethod.LOCAL_OLLAMA, description="Default LLM method")
    local_config: LocalConfig = Field(default_factory=LocalConfig, description="Local LLM config")
    cloud_config: CloudConfig = Field(default_factory=CloudConfig, description="Cloud LLM config")
    china_config: ChinaLLMConfig = Field(default_factory=ChinaLLMConfig, description="China LLM config")
    enabled_methods: List[LLMMethod] = Field(
        default_factory=lambda: [LLMMethod.LOCAL_OLLAMA],
        description="List of enabled methods"
    )
    
    model_config = ConfigDict(extra='allow')
    
    def get_method_config(self, method: LLMMethod) -> Union[LocalConfig, CloudConfig, ChinaLLMConfig]:
        """Get configuration for a specific method."""
        if method == LLMMethod.LOCAL_OLLAMA:
            return self.local_config
        elif method in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
            return self.cloud_config
        else:
            return self.china_config


class GenerateRequest(BaseModel):
    """API request for text generation."""
    
    prompt: str = Field(..., min_length=1, description="Input prompt")
    options: GenerateOptions = Field(default_factory=GenerateOptions, description="Generation options")
    method: Optional[LLMMethod] = Field(default=None, description="Override default method")
    model: Optional[str] = Field(default=None, description="Override default model")
    system_prompt: Optional[str] = Field(default=None, description="System prompt")
    messages: Optional[List[Dict[str, str]]] = Field(default=None, description="Chat messages format")


class EmbedRequest(BaseModel):
    """API request for text embedding."""
    
    text: str = Field(..., min_length=1, description="Text to embed")
    method: Optional[LLMMethod] = Field(default=None, description="Override default method")
    model: Optional[str] = Field(default=None, description="Override default model")


class HealthStatus(BaseModel):
    """Health status for an LLM provider."""
    
    method: LLMMethod = Field(..., description="LLM method")
    available: bool = Field(..., description="Whether the service is available")
    latency_ms: Optional[float] = Field(default=None, description="Health check latency")
    model: Optional[str] = Field(default=None, description="Model being used")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Last check timestamp")


class MethodInfo(BaseModel):
    """Information about an LLM method."""
    
    method: LLMMethod = Field(..., description="LLM method identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Method description")
    enabled: bool = Field(..., description="Whether the method is enabled")
    configured: bool = Field(..., description="Whether the method is properly configured")
    models: List[str] = Field(default_factory=list, description="Available models")


class ValidationResult(BaseModel):
    """Result of configuration validation."""
    
    valid: bool = Field(..., description="Whether the configuration is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


# Utility functions for API key masking
def mask_api_key(api_key: Optional[str]) -> Optional[str]:
    """
    Mask an API key for display, showing only first 4 and last 4 characters.
    
    Args:
        api_key: The API key to mask
        
    Returns:
        Masked API key or None if input is None
    """
    if not api_key:
        return None
    if len(api_key) <= 8:
        return '*' * len(api_key)
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"


def unmask_api_key(masked: Optional[str], original: Optional[str]) -> Optional[str]:
    """
    Restore original API key if masked version matches pattern.
    
    Args:
        masked: The potentially masked API key from user input
        original: The original API key from storage
        
    Returns:
        Original key if masked matches, otherwise the new value
    """
    if not masked:
        return None
    if not original:
        return masked
    # If the masked value matches the mask pattern of original, keep original
    if mask_api_key(original) == masked:
        return original
    return masked
