"""
Pydantic schemas for Text-to-SQL Methods module.

Defines request/response models for SQL generation methods,
plugin configuration, and method switching.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator


class MethodType(str, Enum):
    """Text-to-SQL method types."""
    TEMPLATE = "template"
    LLM = "llm"
    HYBRID = "hybrid"
    THIRD_PARTY = "third_party"


class ConnectionType(str, Enum):
    """Third-party tool connection types."""
    REST_API = "rest_api"
    GRPC = "grpc"
    LOCAL_SDK = "local_sdk"


class TemplateCategory(str, Enum):
    """SQL template categories."""
    AGGREGATE = "aggregate"
    FILTER = "filter"
    SORT = "sort"
    GROUP = "group"
    JOIN = "join"
    SUBQUERY = "subquery"
    WINDOW = "window"


class ParamType(str, Enum):
    """Template parameter types."""
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    LIST = "list"


class SQLGenerationResult(BaseModel):
    """SQL generation result from any method."""
    id: UUID = Field(default_factory=uuid4, description="Result ID")
    sql: str = Field(..., description="Generated SQL query")
    method_used: str = Field(..., description="Method used: template/llm/hybrid/third_party:{name}")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
    execution_time_ms: float = Field(default=0.0, description="Execution time in milliseconds")
    formatted_sql: Optional[str] = Field(None, description="Formatted SQL for display")
    explanation: Optional[str] = Field(None, description="Natural language explanation")
    template_id: Optional[str] = Field(None, description="Template ID if template method used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v


class MethodInfo(BaseModel):
    """Information about a Text-to-SQL method."""
    name: str = Field(..., description="Method name")
    type: MethodType = Field(..., description="Method type")
    description: str = Field(..., description="Method description")
    supported_db_types: List[str] = Field(default_factory=list, description="Supported database types")
    is_available: bool = Field(default=True, description="Whether method is available")
    is_enabled: bool = Field(default=True, description="Whether method is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Method configuration")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Usage statistics")


class PluginInfo(BaseModel):
    """Third-party plugin information."""
    name: str = Field(..., description="Plugin name")
    version: str = Field(default="1.0.0", description="Plugin version")
    description: str = Field(..., description="Plugin description")
    connection_type: ConnectionType = Field(..., description="Connection type")
    supported_db_types: List[str] = Field(default_factory=list, description="Supported database types")
    config_schema: Dict[str, Any] = Field(default_factory=dict, description="Configuration JSON schema")
    is_healthy: bool = Field(default=True, description="Health status")
    last_health_check: Optional[datetime] = Field(None, description="Last health check time")


class PluginConfig(BaseModel):
    """Plugin configuration."""
    name: str = Field(..., min_length=1, max_length=100, description="Plugin name")
    connection_type: ConnectionType = Field(..., description="Connection type")
    endpoint: Optional[str] = Field(None, description="REST API/gRPC endpoint")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    enabled: bool = Field(default=True, description="Whether plugin is enabled")
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")
    
    @field_validator('endpoint')
    @classmethod
    def validate_endpoint(cls, v, info):
        if info.data.get('connection_type') in [ConnectionType.REST_API, ConnectionType.GRPC]:
            if not v:
                raise ValueError('Endpoint is required for REST API and gRPC connections')
        return v


class SQLTemplate(BaseModel):
    """SQL template definition."""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    pattern: str = Field(..., description="Regex pattern for matching")
    template: str = Field(..., description="SQL template with placeholders")
    param_types: Dict[str, ParamType] = Field(default_factory=dict, description="Parameter type definitions")
    category: TemplateCategory = Field(..., description="Template category")
    description: Optional[str] = Field(None, description="Template description")
    examples: List[str] = Field(default_factory=list, description="Example queries")
    priority: int = Field(default=0, description="Matching priority (higher = first)")
    enabled: bool = Field(default=True, description="Whether template is enabled")


class TemplateMatch(BaseModel):
    """Template matching result."""
    template: SQLTemplate = Field(..., description="Matched template")
    params: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters")
    match_score: float = Field(default=1.0, description="Match confidence score")
    groups: Dict[str, str] = Field(default_factory=dict, description="Regex match groups")


class ValidationResult(BaseModel):
    """Parameter validation result."""
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    coerced_params: Dict[str, Any] = Field(default_factory=dict, description="Type-coerced parameters")


class TextToSQLConfig(BaseModel):
    """Text-to-SQL configuration."""
    default_method: MethodType = Field(default=MethodType.HYBRID, description="Default generation method")
    template_config: Dict[str, Any] = Field(default_factory=dict, description="Template method config")
    llm_config: Dict[str, Any] = Field(default_factory=dict, description="LLM method config")
    hybrid_config: Dict[str, Any] = Field(default_factory=dict, description="Hybrid method config")
    auto_select_enabled: bool = Field(default=True, description="Enable auto method selection")
    fallback_enabled: bool = Field(default=True, description="Enable fallback on failure")
    max_retries: int = Field(default=3, ge=1, le=10, description="Max retries on failure")
    timeout_ms: int = Field(default=30000, ge=1000, le=300000, description="Generation timeout")


class GenerateSQLRequest(BaseModel):
    """Request for SQL generation."""
    query: str = Field(..., min_length=1, description="Natural language query")
    method: Optional[MethodType] = Field(None, description="Override default method")
    db_type: Optional[str] = Field(None, description="Database type for auto-selection")
    schema_context: Optional[str] = Field(None, description="Database schema context")
    connection_string: Optional[str] = Field(None, description="Database connection string")
    include_explanation: bool = Field(default=True, description="Include explanation")
    validate_sql: bool = Field(default=True, description="Validate generated SQL")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class TestGenerateRequest(BaseModel):
    """Request for testing SQL generation."""
    query: str = Field(..., min_length=1, description="Natural language query")
    method: Optional[MethodType] = Field(None, description="Method to test")
    schema_context: Optional[str] = Field(None, description="Schema context for testing")


class PluginHealthStatus(BaseModel):
    """Plugin health check status."""
    name: str = Field(..., description="Plugin name")
    is_healthy: bool = Field(..., description="Health status")
    response_time_ms: Optional[float] = Field(None, description="Response time")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    last_check: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")


class PluginStatistics(BaseModel):
    """Plugin usage statistics."""
    name: str = Field(..., description="Plugin name")
    total_calls: int = Field(default=0, description="Total API calls")
    successful_calls: int = Field(default=0, description="Successful calls")
    failed_calls: int = Field(default=0, description="Failed calls")
    average_response_time_ms: float = Field(default=0.0, description="Average response time")
    last_used: Optional[datetime] = Field(None, description="Last usage time")
