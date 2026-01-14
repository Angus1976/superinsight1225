"""
Admin Configuration Pydantic Schemas for SuperInsight Platform.

Defines request/response models for admin configuration APIs including:
- LLM configuration
- Database connections
- Sync strategies
- SQL builder
- Configuration history
- Third-party tools
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ============== Enums ==============

class ConfigType(str, Enum):
    """Configuration type enumeration."""
    LLM = "llm"
    DATABASE = "database"
    SYNC_STRATEGY = "sync_strategy"
    THIRD_PARTY = "third_party"


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"


class SyncMode(str, Enum):
    """Data synchronization modes."""
    FULL = "full"
    INCREMENTAL = "incremental"
    REALTIME = "realtime"


class LLMType(str, Enum):
    """Supported LLM types."""
    LOCAL_OLLAMA = "local_ollama"
    OPENAI = "openai"
    QIANWEN = "qianwen"
    ZHIPU = "zhipu"
    HUNYUAN = "hunyuan"
    CUSTOM = "custom"


class ThirdPartyToolType(str, Enum):
    """Third-party tool types."""
    TEXT_TO_SQL = "text_to_sql"
    AI_ANNOTATION = "ai_annotation"
    DATA_PROCESSING = "data_processing"
    CUSTOM = "custom"


# ============== Validation Results ==============

class ValidationError(BaseModel):
    """Validation error detail."""
    field: str = Field(..., description="Field name with error")
    message: str = Field(..., description="Error message")
    code: str = Field(default="validation_error", description="Error code")


class ValidationResult(BaseModel):
    """Configuration validation result."""
    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[ValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


class ConnectionTestResult(BaseModel):
    """Connection test result."""
    success: bool = Field(..., description="Whether connection succeeded")
    latency_ms: float = Field(default=0.0, description="Connection latency in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")


# ============== LLM Configuration ==============

class LLMConfigBase(BaseModel):
    """Base LLM configuration."""
    llm_type: LLMType = Field(..., description="LLM provider type")
    model_name: str = Field(..., description="Model name/identifier")
    api_endpoint: Optional[str] = Field(default=None, description="API endpoint URL")
    api_key: Optional[str] = Field(default=None, description="API key (will be encrypted)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: int = Field(default=2048, ge=1, le=128000, description="Maximum tokens")
    timeout_seconds: int = Field(default=60, ge=1, le=600, description="Request timeout")
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class LLMConfigCreate(LLMConfigBase):
    """LLM configuration creation request."""
    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    description: Optional[str] = Field(default=None, max_length=500, description="Description")
    is_default: bool = Field(default=False, description="Set as default configuration")


class LLMConfigUpdate(BaseModel):
    """LLM configuration update request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    llm_type: Optional[LLMType] = None
    model_name: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=128000)
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=600)
    extra_config: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class LLMConfigResponse(LLMConfigBase):
    """LLM configuration response."""
    id: str = Field(..., description="Configuration ID")
    name: str = Field(..., description="Configuration name")
    description: Optional[str] = None
    is_active: bool = Field(default=True, description="Whether configuration is active")
    is_default: bool = Field(default=False, description="Whether this is the default")
    api_key_masked: Optional[str] = Field(default=None, description="Masked API key")
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============== Database Connection ==============

class DBConfigBase(BaseModel):
    """Base database connection configuration."""
    db_type: DatabaseType = Field(..., description="Database type")
    host: str = Field(..., min_length=1, max_length=255, description="Database host")
    port: int = Field(..., ge=1, le=65535, description="Database port")
    database: str = Field(..., min_length=1, max_length=100, description="Database name")
    username: str = Field(..., min_length=1, max_length=100, description="Username")
    password: Optional[str] = Field(default=None, description="Password (will be encrypted)")
    is_readonly: bool = Field(default=True, description="Read-only connection")
    ssl_enabled: bool = Field(default=False, description="Enable SSL")
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="Additional config")


class DBConfigCreate(DBConfigBase):
    """Database connection creation request."""
    name: str = Field(..., min_length=1, max_length=100, description="Connection name")
    description: Optional[str] = Field(default=None, max_length=500, description="Description")


class DBConfigUpdate(BaseModel):
    """Database connection update request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    db_type: Optional[DatabaseType] = None
    host: Optional[str] = Field(default=None, min_length=1, max_length=255)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    database: Optional[str] = Field(default=None, min_length=1, max_length=100)
    username: Optional[str] = Field(default=None, min_length=1, max_length=100)
    password: Optional[str] = None
    is_readonly: Optional[bool] = None
    ssl_enabled: Optional[bool] = None
    extra_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DBConfigResponse(BaseModel):
    """Database connection response."""
    id: str = Field(..., description="Connection ID")
    name: str = Field(..., description="Connection name")
    description: Optional[str] = None
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password_masked: Optional[str] = Field(default=None, description="Masked password")
    is_readonly: bool
    ssl_enabled: bool
    extra_config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============== Sync Strategy ==============

class FilterCondition(BaseModel):
    """Data filter condition."""
    field: str = Field(..., description="Field name")
    operator: str = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Comparison value")


class SyncStrategyBase(BaseModel):
    """Base sync strategy configuration."""
    mode: SyncMode = Field(..., description="Synchronization mode")
    incremental_field: Optional[str] = Field(default=None, description="Field for incremental sync")
    schedule: Optional[str] = Field(default=None, description="Cron expression for scheduled sync")
    filter_conditions: List[FilterCondition] = Field(default_factory=list, description="Data filters")
    batch_size: int = Field(default=1000, ge=1, le=100000, description="Batch size")
    enabled: bool = Field(default=True, description="Whether sync is enabled")


class SyncStrategyCreate(SyncStrategyBase):
    """Sync strategy creation request."""
    db_config_id: str = Field(..., description="Database connection ID")
    name: Optional[str] = Field(default=None, max_length=100, description="Strategy name")


class SyncStrategyUpdate(BaseModel):
    """Sync strategy update request."""
    name: Optional[str] = Field(default=None, max_length=100)
    mode: Optional[SyncMode] = None
    incremental_field: Optional[str] = None
    schedule: Optional[str] = None
    filter_conditions: Optional[List[FilterCondition]] = None
    batch_size: Optional[int] = Field(default=None, ge=1, le=100000)
    enabled: Optional[bool] = None


class SyncStrategyResponse(SyncStrategyBase):
    """Sync strategy response."""
    id: str = Field(..., description="Strategy ID")
    db_config_id: str = Field(..., description="Database connection ID")
    name: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class SyncHistoryResponse(BaseModel):
    """Sync history entry response."""
    id: str
    strategy_id: str
    status: str = Field(..., description="Status: success, failed, running")
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_synced: int = 0
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SyncJobResponse(BaseModel):
    """Sync job response."""
    job_id: str
    strategy_id: str
    status: str
    started_at: datetime
    message: str


# ============== SQL Builder ==============

class WhereCondition(BaseModel):
    """SQL WHERE condition."""
    field: str = Field(..., description="Field name")
    operator: str = Field(..., description="SQL operator (=, !=, >, <, LIKE, IN, etc.)")
    value: Any = Field(..., description="Condition value")
    logic: str = Field(default="AND", description="Logic operator (AND/OR)")


class OrderByClause(BaseModel):
    """SQL ORDER BY clause."""
    field: str = Field(..., description="Field name")
    direction: str = Field(default="ASC", description="Sort direction (ASC/DESC)")


class QueryConfig(BaseModel):
    """SQL query configuration."""
    tables: List[str] = Field(..., min_length=1, description="Tables to query")
    columns: List[str] = Field(default_factory=lambda: ["*"], description="Columns to select")
    where_conditions: List[WhereCondition] = Field(default_factory=list, description="WHERE conditions")
    order_by: List[OrderByClause] = Field(default_factory=list, description="ORDER BY clauses")
    group_by: List[str] = Field(default_factory=list, description="GROUP BY fields")
    limit: Optional[int] = Field(default=None, ge=1, le=10000, description="Result limit")
    offset: Optional[int] = Field(default=None, ge=0, description="Result offset")


class QueryTemplateCreate(BaseModel):
    """Query template creation request."""
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(default=None, max_length=500, description="Description")
    query_config: QueryConfig = Field(..., description="Query configuration")
    db_config_id: str = Field(..., description="Database connection ID")


class QueryTemplateResponse(BaseModel):
    """Query template response."""
    id: str
    name: str
    description: Optional[str] = None
    query_config: QueryConfig
    sql: str = Field(..., description="Generated SQL")
    db_config_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class DatabaseSchema(BaseModel):
    """Database schema information."""
    tables: List[Dict[str, Any]] = Field(..., description="Table definitions")
    views: List[Dict[str, Any]] = Field(default_factory=list, description="View definitions")


class TableInfo(BaseModel):
    """Table information."""
    name: str
    schema_name: Optional[str] = None
    columns: List[Dict[str, Any]]
    primary_key: Optional[List[str]] = None
    foreign_keys: List[Dict[str, Any]] = Field(default_factory=list)
    indexes: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: Optional[int] = None


class QueryResult(BaseModel):
    """SQL query execution result."""
    columns: List[str] = Field(..., description="Column names")
    rows: List[List[Any]] = Field(..., description="Result rows")
    row_count: int = Field(..., description="Number of rows returned")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    truncated: bool = Field(default=False, description="Whether results were truncated")


class ExecuteSQLRequest(BaseModel):
    """SQL execution request."""
    db_config_id: str = Field(..., description="Database connection ID")
    sql: str = Field(..., min_length=1, description="SQL query to execute")
    limit: int = Field(default=100, ge=1, le=1000, description="Result limit")


# ============== Configuration History ==============

class ConfigHistoryResponse(BaseModel):
    """Configuration change history response."""
    id: str
    config_type: ConfigType
    old_value: Optional[Dict[str, Any]] = None
    new_value: Dict[str, Any]
    user_id: str
    user_name: str
    tenant_id: Optional[str] = None
    created_at: datetime


class ConfigDiff(BaseModel):
    """Configuration difference."""
    added: Dict[str, Any] = Field(default_factory=dict, description="Added fields")
    removed: Dict[str, Any] = Field(default_factory=dict, description="Removed fields")
    modified: Dict[str, Any] = Field(default_factory=dict, description="Modified fields")


class RollbackRequest(BaseModel):
    """Configuration rollback request."""
    reason: Optional[str] = Field(default=None, max_length=500, description="Rollback reason")


# ============== Third-Party Tools ==============

class ThirdPartyConfigBase(BaseModel):
    """Base third-party tool configuration."""
    tool_type: ThirdPartyToolType = Field(..., description="Tool type")
    endpoint: str = Field(..., min_length=1, max_length=500, description="API endpoint")
    api_key: Optional[str] = Field(default=None, description="API key (will be encrypted)")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout")
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="Additional config")


class ThirdPartyConfigCreate(ThirdPartyConfigBase):
    """Third-party tool creation request."""
    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    description: Optional[str] = Field(default=None, max_length=500, description="Description")


class ThirdPartyConfigUpdate(BaseModel):
    """Third-party tool update request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    tool_type: Optional[ThirdPartyToolType] = None
    endpoint: Optional[str] = Field(default=None, min_length=1, max_length=500)
    api_key: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    extra_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class ThirdPartyConfigResponse(ThirdPartyConfigBase):
    """Third-party tool response."""
    id: str
    name: str
    description: Optional[str] = None
    api_key_masked: Optional[str] = Field(default=None, description="Masked API key")
    enabled: bool = True
    health_status: Optional[str] = Field(default=None, description="Health check status")
    last_health_check: Optional[datetime] = None
    call_count: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============== Dashboard ==============

class DashboardData(BaseModel):
    """Admin dashboard data."""
    system_health: Dict[str, Any] = Field(..., description="System health status")
    key_metrics: Dict[str, Any] = Field(..., description="Key metrics")
    recent_alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Recent alerts")
    quick_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Quick action links")
    config_summary: Dict[str, Any] = Field(default_factory=dict, description="Configuration summary")
