"""
Pydantic schemas for Datalake/Warehouse connectors.

Provides request/response models for data source CRUD, dashboard overview,
health status, volume trends, query performance, and data flow visualization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from src.sync.models import DataSourceStatus, DataSourceType, DATALAKE_TYPES


# ============================================================================
# Helper Constants
# ============================================================================

_DATALAKE_TYPE_VALUES = {t.value for t in DATALAKE_TYPES}


# ============================================================================
# Data Source CRUD Schemas
# ============================================================================

class DatalakeSourceCreate(BaseModel):
    """Request schema for creating a datalake/warehouse data source."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    source_type: DataSourceType
    connection_config: Dict[str, Any]

    @validator("source_type")
    def source_type_must_be_datalake(cls, v: DataSourceType) -> DataSourceType:
        if v not in DATALAKE_TYPES:
            raise ValueError(
                f"source_type must be a datalake/warehouse type, "
                f"got '{v.value}'. Allowed: {sorted(_DATALAKE_TYPE_VALUES)}"
            )
        return v


class DatalakeSourceUpdate(BaseModel):
    """Request schema for updating a datalake/warehouse data source."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None


class DatalakeSourceResponse(BaseModel):
    """Response schema for a datalake/warehouse data source.

    The connection_config field contains masked sensitive values (Req 8.2).
    """
    id: UUID
    name: str
    source_type: DataSourceType
    status: DataSourceStatus
    health_check_status: Optional[str] = None
    last_health_check: Optional[datetime] = None
    created_at: datetime
    connection_config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ConnectionTestResult(BaseModel):
    """Result of a data source connection test."""
    status: str  # connected, error
    latency_ms: float
    error_message: Optional[str] = None


# ============================================================================
# Dashboard Schemas
# ============================================================================

class SourceSummary(BaseModel):
    """Summary info for a single data source in the dashboard."""
    source_id: UUID
    name: str
    source_type: DataSourceType
    status: DataSourceStatus
    health_check_status: Optional[str] = None


class DashboardOverview(BaseModel):
    """Dashboard overview with aggregated metrics."""
    total_sources: int
    active_sources: int
    error_sources: int
    total_data_volume_gb: float
    avg_query_latency_ms: float
    sources: List[SourceSummary]


class SourceHealthStatus(BaseModel):
    """Health status for a single data source."""
    source_id: UUID
    source_name: str
    source_type: DataSourceType
    status: str  # healthy, degraded, down
    latency_ms: float
    last_check: datetime
    error_message: Optional[str] = None


# ============================================================================
# Volume Trend Schemas
# ============================================================================

class VolumeDataPoint(BaseModel):
    """A single data point in volume trend data."""
    timestamp: datetime
    source_id: UUID
    source_name: str
    volume_gb: float
    row_count: int


class VolumeTrendData(BaseModel):
    """Volume trend data over a time period."""
    period: str
    data_points: List[VolumeDataPoint]


# ============================================================================
# Query Performance Schemas
# ============================================================================

class SourceQueryStats(BaseModel):
    """Query statistics for a single data source."""
    source_id: UUID
    source_name: str
    total_queries: int
    failed_queries: int
    avg_latency_ms: float


class QueryPerformanceData(BaseModel):
    """Aggregated query performance metrics."""
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_queries: int
    failed_queries: int
    queries_by_source: List[SourceQueryStats]


# ============================================================================
# Data Flow Graph Schemas
# ============================================================================

class FlowNode(BaseModel):
    """A node in the data flow graph."""
    id: str
    label: str
    type: str  # source, warehouse, lake
    status: str


class FlowEdge(BaseModel):
    """An edge in the data flow graph."""
    source: str
    target: str
    volume_gb: float
    sync_status: str


class DataFlowGraph(BaseModel):
    """Data flow graph with nodes and edges."""
    nodes: List[FlowNode]
    edges: List[FlowEdge]
