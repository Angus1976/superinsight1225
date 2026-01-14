"""
Pydantic schemas for Data Sync Pipeline.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.sync.pipeline.enums import (
    DatabaseType,
    ConnectionMethod,
    SaveStrategy,
    DataFormat,
    ExportFormat,
    JobStatus,
)


# ============================================================================
# Data Reader Schemas
# ============================================================================

class DataSourceConfig(BaseModel):
    """Configuration for connecting to a data source."""
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str  # Should be encrypted in storage
    connection_method: ConnectionMethod = ConnectionMethod.JDBC
    extra_params: Dict[str, Any] = Field(default_factory=dict)
    readonly: bool = True  # Enforce read-only connections


class DataPage(BaseModel):
    """A page of data from a read operation."""
    page_number: int
    rows: List[Dict[str, Any]]
    row_count: int
    has_more: bool


class ReadStatistics(BaseModel):
    """Statistics from a read operation."""
    total_rows: int
    total_columns: int
    total_size_bytes: int
    read_duration_ms: float


# ============================================================================
# Data Puller Schemas
# ============================================================================

class PullConfig(BaseModel):
    """Configuration for data pulling."""
    cron_expression: str
    incremental: bool = True
    checkpoint_field: str = "updated_at"
    min_interval_minutes: int = Field(default=1, ge=1)  # Minimum 1 minute
    query: Optional[str] = None
    table_name: Optional[str] = None
    page_size: int = Field(default=1000, ge=1, le=10000)


class Checkpoint(BaseModel):
    """Checkpoint for incremental pulling."""
    source_id: str
    last_value: Optional[Any] = None
    last_pull_at: Optional[datetime] = None
    rows_pulled: int = 0


class PullResult(BaseModel):
    """Result of a pull operation."""
    source_id: str
    success: bool
    rows_pulled: int
    checkpoint: Optional[Checkpoint] = None
    error_message: Optional[str] = None
    retries_used: int = 0


# ============================================================================
# Data Receiver Schemas
# ============================================================================

class ReceiveResult(BaseModel):
    """Result of a receive operation."""
    success: bool
    duplicate: bool = False
    rows_received: int
    error_message: Optional[str] = None


# ============================================================================
# Save Strategy Schemas
# ============================================================================

class SaveConfig(BaseModel):
    """Configuration for data saving."""
    strategy: SaveStrategy = SaveStrategy.PERSISTENT
    retention_days: int = Field(default=30, ge=1)
    hybrid_threshold_bytes: int = Field(default=1024 * 1024)  # 1MB
    table_name: Optional[str] = None


class SaveResult(BaseModel):
    """Result of a save operation."""
    success: bool
    strategy_used: SaveStrategy
    rows_saved: int
    storage_location: str  # "database" or "memory"
    error_message: Optional[str] = None


# ============================================================================
# Semantic Refiner Schemas
# ============================================================================

class RefineRule(BaseModel):
    """Custom refinement rule."""
    name: str
    field_pattern: str
    transformation: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class RefineConfig(BaseModel):
    """Configuration for semantic refinement."""
    generate_descriptions: bool = True
    generate_dictionary: bool = True
    extract_entities: bool = True
    extract_relations: bool = True
    custom_rules: List[RefineRule] = Field(default_factory=list)
    cache_ttl: int = Field(default=3600)  # 1 hour


class FieldDefinition(BaseModel):
    """Definition of a field in the data dictionary."""
    name: str
    data_type: str
    description: str
    sample_values: List[Any] = Field(default_factory=list)
    nullable: bool = True
    business_meaning: Optional[str] = None


class DataDictionary(BaseModel):
    """Data dictionary generated from semantic analysis."""
    fields: List[FieldDefinition]
    table_description: str
    business_context: str


class Entity(BaseModel):
    """An entity extracted from data."""
    name: str
    type: str
    source_field: str
    confidence: float = Field(ge=0.0, le=1.0)


class Relation(BaseModel):
    """A relation between entities."""
    source_entity: str
    target_entity: str
    relation_type: str
    confidence: float = Field(ge=0.0, le=1.0)


class RefinementResult(BaseModel):
    """Result of semantic refinement."""
    field_descriptions: Dict[str, str]
    data_dictionary: Optional[DataDictionary] = None
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)
    enhanced_description: str = ""


# ============================================================================
# AI Friendly Exporter Schemas
# ============================================================================

class SplitConfig(BaseModel):
    """Configuration for data splitting."""
    train_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
    val_ratio: float = Field(default=0.1, ge=0.0, le=1.0)
    test_ratio: float = Field(default=0.1, ge=0.0, le=1.0)
    shuffle: bool = True
    seed: int = 42


class ExportedFile(BaseModel):
    """Information about an exported file."""
    filename: str
    filepath: str
    format: ExportFormat
    size_bytes: int
    row_count: int
    split_name: str = "all"  # train/val/test/all


class FieldStats(BaseModel):
    """Statistics for a single field."""
    field_name: str
    data_type: str
    total_count: int = 0
    null_count: int = 0
    unique_count: int = 0
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    avg_value: Optional[float] = None


class StatisticsReport(BaseModel):
    """Statistics report for exported data."""
    total_rows: int
    total_size_bytes: int
    split_counts: Dict[str, int] = Field(default_factory=dict)
    field_statistics: Dict[str, FieldStats] = Field(default_factory=dict)
    export_duration_ms: float


class ExportConfig(BaseModel):
    """Configuration for data export."""
    include_semantics: bool = True
    desensitize: bool = False
    split_config: Optional[SplitConfig] = None
    incremental: bool = False
    last_export_id: Optional[str] = None


class ExportResult(BaseModel):
    """Result of an export operation."""
    export_id: str
    files: List[ExportedFile]
    statistics: StatisticsReport
    format: Optional[ExportFormat] = None
    success: bool = True
    error_message: Optional[str] = None


# ============================================================================
# Sync Scheduler Schemas
# ============================================================================

class ScheduleConfig(BaseModel):
    """Configuration for sync scheduling."""
    cron_expression: str
    priority: int = Field(default=0, ge=0, le=10)
    enabled: bool = True


class ScheduledJob(BaseModel):
    """A scheduled sync job."""
    job_id: str
    source_id: str
    config: ScheduleConfig
    status: JobStatus = JobStatus.PENDING
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SyncHistoryRecord(BaseModel):
    """A record in sync history."""
    job_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: JobStatus
    rows_synced: int = 0
    error_message: Optional[str] = None


class SyncResult(BaseModel):
    """Result of a sync operation."""
    job_id: str
    success: bool
    rows_synced: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
