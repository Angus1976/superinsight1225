"""
Datalake/Warehouse REST API Router.

Provides CRUD endpoints for data source management, connection testing,
schema browsing, and dashboard visualization with RBAC permission control.

Validates: Requirements 2.1-2.5, 3.1-3.2, 4.1-4.4, 6.1-6.5, 7.1-7.5, 8.1-8.3
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.sync.connectors.base import ConnectorFactory
from src.sync.connectors.datalake.base import (
    DatalakeBaseConnector,
    MAX_PREVIEW_LIMIT,
)
from src.sync.connectors.datalake.models import DatalakeMetricsModel
from src.sync.connectors.datalake.schemas import (
    ConnectionTestResult,
    DashboardOverview,
    DataFlowGraph,
    DatalakeSourceCreate,
    DatalakeSourceResponse,
    DatalakeSourceUpdate,
    FlowEdge,
    FlowNode,
    QueryPerformanceData,
    SourceHealthStatus,
    SourceQueryStats,
    SourceSummary,
    VolumeDataPoint,
    VolumeTrendData,
)
from src.sync.gateway.auth import (
    AuthToken,
    Permission,
    PermissionLevel,
    ResourceType,
    sync_auth_handler,
)
from src.sync.models import (
    DATALAKE_TYPES,
    DataSourceModel,
    DataSourceStatus,
    DataSourceType,
)
from src.utils.encryption import encrypt_sensitive_data, mask_sensitive_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/datalake", tags=["datalake"])

# Sensitive field names in connection_config that require encryption/masking
SENSITIVE_CONFIG_KEYS = {"password", "secret", "api_key", "token", "private_key"}


# ============================================================================
# Auth Dependencies
# ============================================================================

# ADMIN/TECHNICAL_EXPERT: full CRUD + query execution (WRITE on DATALAKE_SOURCE)
_require_datalake_write = sync_auth_handler.require_permission(
    ResourceType.DATALAKE_SOURCE, PermissionLevel.WRITE
)

# BUSINESS_EXPERT: read-only data source list (READ on DATALAKE_SOURCE)
_require_datalake_read = sync_auth_handler.require_permission(
    ResourceType.DATALAKE_SOURCE, PermissionLevel.READ
)

# All authenticated users with dashboard access (READ on DATALAKE_DASHBOARD)
_require_dashboard_read = sync_auth_handler.require_permission(
    ResourceType.DATALAKE_DASHBOARD, PermissionLevel.READ
)


# ============================================================================
# Encryption / Masking Helpers
# ============================================================================


def _encrypt_config_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """Encrypt sensitive fields in connection_config before storage.

    Validates: Requirement 8.1
    """
    encrypted = config.copy()
    for key in SENSITIVE_CONFIG_KEYS:
        if key in encrypted and encrypted[key]:
            encrypted[key] = encrypt_sensitive_data(str(encrypted[key]))
    return encrypted


def _mask_config_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive fields in connection_config for API responses.

    Validates: Requirement 8.2
    """
    masked = config.copy()
    for key in SENSITIVE_CONFIG_KEYS:
        if key in masked and masked[key]:
            masked[key] = mask_sensitive_data(str(masked[key]))
    return masked


# ============================================================================
# Helper Functions
# ============================================================================


def _get_source_or_404(
    source_id: UUID, tenant_id: str, db: Session
) -> DataSourceModel:
    """Fetch a datalake source by ID with tenant isolation.

    Validates: Requirement 7.5
    Raises HTTPException 404 if not found or not a datalake type.
    """
    source = (
        db.query(DataSourceModel)
        .filter(
            DataSourceModel.id == source_id,
            DataSourceModel.tenant_id == tenant_id,
            DataSourceModel.source_type.in_(DATALAKE_TYPES),
        )
        .first()
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datalake source {source_id} not found",
        )
    return source


def _create_connector(source: DataSourceModel) -> DatalakeBaseConnector:
    """Create a datalake connector from a DataSourceModel.

    Raises HTTPException 422 if connector creation fails.
    """
    try:
        connector = ConnectorFactory.create(
            source.source_type.value, source.connection_config
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to create connector: {exc}",
        )
    if not isinstance(connector, DatalakeBaseConnector):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Connector type {source.source_type.value} is not a datalake connector",
        )
    return connector


def _to_response(source: DataSourceModel) -> DatalakeSourceResponse:
    """Convert a DataSourceModel to DatalakeSourceResponse with masked secrets.

    Validates: Requirement 8.2
    """
    return DatalakeSourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        health_check_status=source.health_check_status,
        last_health_check=source.last_health_check,
        created_at=source.created_at,
        connection_config=_mask_config_secrets(source.connection_config or {}),
    )


# ============================================================================
# Data Source CRUD Endpoints
# ============================================================================


@router.post("/sources", response_model=DatalakeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_datalake_source(
    payload: DatalakeSourceCreate,
    auth: AuthToken = Depends(_require_datalake_write),
    db: Session = Depends(get_db),
) -> DatalakeSourceResponse:
    """创建数据湖/数仓数据源。

    Requires: ADMIN or TECHNICAL_EXPERT role (WRITE on DATALAKE_SOURCE).
    Validates: Requirements 2.1, 2.2, 7.1, 8.1
    """
    encrypted_config = _encrypt_config_secrets(payload.connection_config)
    source = DataSourceModel(
        tenant_id=auth.tenant_id,
        name=payload.name,
        description=payload.description,
        source_type=payload.source_type,
        connection_config=encrypted_config,
        status=DataSourceStatus.INACTIVE,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    logger.info("Created datalake source %s for tenant %s", source.id, auth.tenant_id)
    return _to_response(source)


@router.get("/sources", response_model=List[DatalakeSourceResponse])
async def list_datalake_sources(
    auth: AuthToken = Depends(_require_datalake_read),
    db: Session = Depends(get_db),
) -> List[DatalakeSourceResponse]:
    """列出当前租户的所有数据湖/数仓数据源。

    Requires: ADMIN, TECHNICAL_EXPERT, or BUSINESS_EXPERT role (READ on DATALAKE_SOURCE).
    Validates: Requirements 2.3, 7.1, 7.2, 7.5
    """
    sources = (
        db.query(DataSourceModel)
        .filter(
            DataSourceModel.tenant_id == auth.tenant_id,
            DataSourceModel.source_type.in_(DATALAKE_TYPES),
        )
        .order_by(DataSourceModel.created_at.desc())
        .all()
    )
    return [_to_response(s) for s in sources]


@router.get("/sources/{source_id}", response_model=DatalakeSourceResponse)
async def get_datalake_source(
    source_id: UUID,
    auth: AuthToken = Depends(_require_datalake_read),
    db: Session = Depends(get_db),
) -> DatalakeSourceResponse:
    """获取单个数据源详情。

    Requires: READ on DATALAKE_SOURCE.
    Validates: Requirements 2.3, 7.5
    """
    source = _get_source_or_404(source_id, auth.tenant_id, db)
    return _to_response(source)


@router.put("/sources/{source_id}", response_model=DatalakeSourceResponse)
async def update_datalake_source(
    source_id: UUID,
    payload: DatalakeSourceUpdate,
    auth: AuthToken = Depends(_require_datalake_write),
    db: Session = Depends(get_db),
) -> DatalakeSourceResponse:
    """更新数据源配置。

    Requires: ADMIN or TECHNICAL_EXPERT role (WRITE on DATALAKE_SOURCE).
    Validates: Requirements 2.4, 7.1, 8.1
    """
    source = _get_source_or_404(source_id, auth.tenant_id, db)

    if payload.name is not None:
        source.name = payload.name
    if payload.description is not None:
        source.description = payload.description
    if payload.connection_config is not None:
        source.connection_config = _encrypt_config_secrets(payload.connection_config)

    db.commit()
    db.refresh(source)
    logger.info("Updated datalake source %s", source_id)
    return _to_response(source)


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datalake_source(
    source_id: UUID,
    auth: AuthToken = Depends(_require_datalake_write),
    db: Session = Depends(get_db),
) -> None:
    """删除数据源及其关联的指标记录。

    Requires: ADMIN or TECHNICAL_EXPERT role (WRITE on DATALAKE_SOURCE).
    Validates: Requirements 2.5, 7.1
    """
    source = _get_source_or_404(source_id, auth.tenant_id, db)

    # Cascade delete metrics (also handled by DB FK ondelete=CASCADE)
    db.query(DatalakeMetricsModel).filter(
        DatalakeMetricsModel.source_id == source_id,
    ).delete(synchronize_session=False)

    db.delete(source)
    db.commit()
    logger.info("Deleted datalake source %s and its metrics", source_id)


# ============================================================================
# Connection Test Endpoint
# ============================================================================


@router.post("/sources/{source_id}/test", response_model=ConnectionTestResult)
async def test_datalake_connection(
    source_id: UUID,
    auth: AuthToken = Depends(_require_datalake_write),
    db: Session = Depends(get_db),
) -> ConnectionTestResult:
    """测试数据源连接并更新健康检查状态。

    Requires: ADMIN or TECHNICAL_EXPERT role (WRITE on DATALAKE_SOURCE).
    Validates: Requirements 3.1, 3.2, 3.4, 7.1
    """
    source = _get_source_or_404(source_id, auth.tenant_id, db)
    connector = _create_connector(source)

    try:
        result = await connector.test_connection()
    except Exception as exc:
        logger.warning("Connection test failed for source %s: %s", source_id, exc)
        result = {"success": False, "latency_ms": 0, "error": str(exc)}
    finally:
        try:
            await connector.disconnect()
        except Exception:
            pass

    # Update health check fields on the source
    now = datetime.now(timezone.utc)
    source.health_check_status = "connected" if result.get("success") else "error"
    source.last_health_check = now
    if result.get("success"):
        source.status = DataSourceStatus.ACTIVE
    db.commit()

    return ConnectionTestResult(
        status="connected" if result.get("success") else "error",
        latency_ms=result.get("latency_ms", 0),
        error_message=result.get("error"),
    )


# ============================================================================
# Schema Browsing Endpoints
# ============================================================================


@router.get("/sources/{source_id}/databases", response_model=List[str])
async def list_databases(
    source_id: UUID,
    auth: AuthToken = Depends(_require_datalake_read),
    db: Session = Depends(get_db),
) -> List[str]:
    """获取数据库列表。

    Requires: READ on DATALAKE_SOURCE.
    Validates: Requirements 4.1, 7.1, 7.2
    """
    source = _get_source_or_404(source_id, auth.tenant_id, db)
    connector = _create_connector(source)

    try:
        await connector.connect()
        databases = await connector.fetch_databases()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch databases: {exc}",
        )
    finally:
        try:
            await connector.disconnect()
        except Exception:
            pass

    return databases


@router.get("/sources/{source_id}/tables", response_model=List[Dict[str, Any]])
async def list_tables(
    source_id: UUID,
    database: str = Query(..., description="Database name"),
    auth: AuthToken = Depends(_require_datalake_read),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """获取指定数据库的表列表（含行数和大小估算）。

    Requires: READ on DATALAKE_SOURCE.
    Validates: Requirements 4.2, 7.1, 7.2
    """
    source = _get_source_or_404(source_id, auth.tenant_id, db)
    connector = _create_connector(source)

    try:
        await connector.connect()
        tables = await connector.fetch_tables(database)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch tables: {exc}",
        )
    finally:
        try:
            await connector.disconnect()
        except Exception:
            pass

    return tables


@router.get("/sources/{source_id}/schema")
async def get_table_schema(
    source_id: UUID,
    database: str = Query(..., description="Database name"),
    table: str = Query(..., description="Table name"),
    auth: AuthToken = Depends(_require_datalake_read),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """获取表结构（列名、类型、注释）。

    Requires: READ on DATALAKE_SOURCE.
    Validates: Requirements 4.4, 7.1, 7.2
    """
    source = _get_source_or_404(source_id, auth.tenant_id, db)
    connector = _create_connector(source)

    try:
        await connector.connect()
        schema = await connector.fetch_schema()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch schema: {exc}",
        )
    finally:
        try:
            await connector.disconnect()
        except Exception:
            pass

    return {"database": database, "table": table, "schema": schema}


@router.get("/sources/{source_id}/preview")
async def preview_table_data(
    source_id: UUID,
    database: str = Query(..., description="Database name"),
    table: str = Query(..., description="Table name"),
    limit: int = Query(default=100, ge=1, le=MAX_PREVIEW_LIMIT, description="Max rows"),
    auth: AuthToken = Depends(_require_datalake_read),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """预览表数据（默认 100 行，最大 1000 行）。

    Requires: READ on DATALAKE_SOURCE.
    Validates: Requirements 4.3, 7.1, 7.2
    """
    source = _get_source_or_404(source_id, auth.tenant_id, db)
    connector = _create_connector(source)

    try:
        await connector.connect()
        data_batch = await connector.fetch_table_preview(database, table, limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to preview table data: {exc}",
        )
    finally:
        try:
            await connector.disconnect()
        except Exception:
            pass

    return {
        "database": database,
        "table": table,
        "row_count": len(data_batch.records) if data_batch.records else 0,
        "records": [r.data for r in data_batch.records] if data_batch.records else [],
    }


# ============================================================================
# Dashboard Helper Functions
# ============================================================================

# Period string to timedelta mapping
_PERIOD_MAP: Dict[str, timedelta] = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}


def _parse_period(period: str) -> timedelta:
    """Parse a period string (e.g. '7d') into a timedelta.

    Raises HTTPException 400 for invalid period values.
    """
    delta = _PERIOD_MAP.get(period)
    if delta is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period '{period}'. Allowed: {sorted(_PERIOD_MAP.keys())}",
        )
    return delta


def _get_datalake_sources(tenant_id: str, db: Session) -> List[DataSourceModel]:
    """Query all datalake/warehouse sources for a tenant.

    Validates: Requirement 7.5 (tenant isolation)
    """
    return (
        db.query(DataSourceModel)
        .filter(
            DataSourceModel.tenant_id == tenant_id,
            DataSourceModel.source_type.in_(DATALAKE_TYPES),
        )
        .all()
    )


def _build_source_summary(source: DataSourceModel) -> SourceSummary:
    """Build a SourceSummary from a DataSourceModel."""
    return SourceSummary(
        source_id=source.id,
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        health_check_status=source.health_check_status,
    )


def _compute_percentile(sorted_values: List[float], percentile: float) -> float:
    """Compute a percentile from a pre-sorted list of values.

    Uses linear interpolation between closest ranks.
    Returns 0.0 for empty input.
    """
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    # Rank index (0-based)
    rank = (percentile / 100.0) * (n - 1)
    lower = int(rank)
    upper = min(lower + 1, n - 1)
    fraction = rank - lower
    return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])


# ============================================================================
# Dashboard Endpoints (VIEWER and above)
# ============================================================================


@router.get("/dashboard/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    auth: AuthToken = Depends(_require_dashboard_read),
    db: Session = Depends(get_db),
) -> DashboardOverview:
    """获取看板概览数据：数据源统计、总数据量、平均查询延迟。

    Requires: READ on DATALAKE_DASHBOARD (all authenticated roles).
    Validates: Requirements 6.1, 6.2, 7.2, 7.3
    """
    sources = _get_datalake_sources(auth.tenant_id, db)
    if not sources:
        return DashboardOverview(
            total_sources=0,
            active_sources=0,
            error_sources=0,
            total_data_volume_gb=0.0,
            avg_query_latency_ms=0.0,
            sources=[],
        )

    active = sum(1 for s in sources if s.status == DataSourceStatus.ACTIVE)
    error = sum(1 for s in sources if s.status == DataSourceStatus.ERROR)

    # Aggregate metrics from last 24 hours
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_metrics = (
        db.query(DatalakeMetricsModel)
        .filter(
            DatalakeMetricsModel.tenant_id == auth.tenant_id,
            DatalakeMetricsModel.recorded_at >= cutoff,
        )
        .all()
    )

    total_volume = sum(
        m.metric_data.get("volume_gb", 0.0)
        for m in recent_metrics
        if m.metric_type == "volume"
    )
    latencies = [
        m.metric_data.get("latency_ms", 0.0)
        for m in recent_metrics
        if m.metric_type == "query_perf"
    ]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return DashboardOverview(
        total_sources=len(sources),
        active_sources=active,
        error_sources=error,
        total_data_volume_gb=round(total_volume, 2),
        avg_query_latency_ms=round(avg_latency, 2),
        sources=[_build_source_summary(s) for s in sources],
    )


@router.get("/dashboard/health", response_model=List[SourceHealthStatus])
async def get_health_status(
    auth: AuthToken = Depends(_require_dashboard_read),
    db: Session = Depends(get_db),
) -> List[SourceHealthStatus]:
    """获取所有数据源的健康状态。

    Requires: READ on DATALAKE_DASHBOARD.
    Validates: Requirements 6.1, 7.2, 7.3
    """
    sources = _get_datalake_sources(auth.tenant_id, db)
    now = datetime.now(timezone.utc)

    results: List[SourceHealthStatus] = []
    for source in sources:
        # Derive health status from model fields
        hc_status = source.health_check_status or "unknown"
        if hc_status == "connected":
            display_status = "healthy"
        elif hc_status == "error":
            display_status = "down"
        else:
            display_status = "degraded"

        # Get latest health metric for latency
        latest_metric = (
            db.query(DatalakeMetricsModel)
            .filter(
                DatalakeMetricsModel.source_id == source.id,
                DatalakeMetricsModel.metric_type == "health",
            )
            .order_by(DatalakeMetricsModel.recorded_at.desc())
            .first()
        )
        latency = 0.0
        error_msg = None
        if latest_metric and latest_metric.metric_data:
            latency = latest_metric.metric_data.get("latency_ms", 0.0)
            error_msg = latest_metric.metric_data.get("error_message")

        results.append(SourceHealthStatus(
            source_id=source.id,
            source_name=source.name,
            source_type=source.source_type,
            status=display_status,
            latency_ms=latency,
            last_check=source.last_health_check or now,
            error_message=error_msg,
        ))

    return results


@router.get("/dashboard/volume-trends", response_model=VolumeTrendData)
async def get_volume_trends(
    period: str = Query(default="7d", description="Time period: 1d, 7d, 30d, 90d"),
    auth: AuthToken = Depends(_require_dashboard_read),
    db: Session = Depends(get_db),
) -> VolumeTrendData:
    """获取指定时间段内按数据源分组的数据量趋势。

    Requires: READ on DATALAKE_DASHBOARD.
    Validates: Requirements 6.3, 7.2, 7.3
    """
    delta = _parse_period(period)
    cutoff = datetime.now(timezone.utc) - delta

    # Build source name lookup
    sources = _get_datalake_sources(auth.tenant_id, db)
    source_names: Dict[str, str] = {str(s.id): s.name for s in sources}

    volume_metrics = (
        db.query(DatalakeMetricsModel)
        .filter(
            DatalakeMetricsModel.tenant_id == auth.tenant_id,
            DatalakeMetricsModel.metric_type == "volume",
            DatalakeMetricsModel.recorded_at >= cutoff,
        )
        .order_by(DatalakeMetricsModel.recorded_at.asc())
        .all()
    )

    data_points = [
        VolumeDataPoint(
            timestamp=m.recorded_at,
            source_id=m.source_id,
            source_name=source_names.get(str(m.source_id), "Unknown"),
            volume_gb=m.metric_data.get("volume_gb", 0.0),
            row_count=m.metric_data.get("row_count", 0),
        )
        for m in volume_metrics
    ]

    return VolumeTrendData(period=period, data_points=data_points)


@router.get("/dashboard/query-performance", response_model=QueryPerformanceData)
async def get_query_performance(
    source_id: Optional[UUID] = Query(default=None, description="Filter by source ID"),
    auth: AuthToken = Depends(_require_dashboard_read),
    db: Session = Depends(get_db),
) -> QueryPerformanceData:
    """获取查询性能指标：平均延迟、P95、P99、失败数。

    Requires: READ on DATALAKE_DASHBOARD.
    Validates: Requirements 6.4, 7.2, 7.3
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    query = db.query(DatalakeMetricsModel).filter(
        DatalakeMetricsModel.tenant_id == auth.tenant_id,
        DatalakeMetricsModel.metric_type == "query_perf",
        DatalakeMetricsModel.recorded_at >= cutoff,
    )
    if source_id is not None:
        query = query.filter(DatalakeMetricsModel.source_id == source_id)

    perf_metrics = query.all()

    # Collect all latencies and failure counts
    all_latencies: List[float] = []
    total_failed = 0
    per_source: Dict[str, Dict[str, Any]] = {}

    for m in perf_metrics:
        sid = str(m.source_id)
        latency = m.metric_data.get("latency_ms", 0.0)
        failed = 1 if m.metric_data.get("status") == "failed" else 0

        all_latencies.append(latency)
        total_failed += failed

        if sid not in per_source:
            per_source[sid] = {
                "total": 0, "failed": 0, "latency_sum": 0.0, "source_id": m.source_id,
            }
        per_source[sid]["total"] += 1
        per_source[sid]["failed"] += failed
        per_source[sid]["latency_sum"] += latency

    # Compute global stats
    sorted_latencies = sorted(all_latencies)
    avg_lat = sum(sorted_latencies) / len(sorted_latencies) if sorted_latencies else 0.0
    p95 = _compute_percentile(sorted_latencies, 95)
    p99 = _compute_percentile(sorted_latencies, 99)

    # Build source name lookup
    sources = _get_datalake_sources(auth.tenant_id, db)
    source_names: Dict[str, str] = {str(s.id): s.name for s in sources}

    queries_by_source = [
        SourceQueryStats(
            source_id=info["source_id"],
            source_name=source_names.get(sid, "Unknown"),
            total_queries=info["total"],
            failed_queries=info["failed"],
            avg_latency_ms=round(info["latency_sum"] / info["total"], 2) if info["total"] else 0.0,
        )
        for sid, info in per_source.items()
    ]

    return QueryPerformanceData(
        avg_latency_ms=round(avg_lat, 2),
        p95_latency_ms=round(p95, 2),
        p99_latency_ms=round(p99, 2),
        total_queries=len(perf_metrics),
        failed_queries=total_failed,
        queries_by_source=queries_by_source,
    )


@router.get("/dashboard/data-flow", response_model=DataFlowGraph)
async def get_data_flow(
    auth: AuthToken = Depends(_require_dashboard_read),
    db: Session = Depends(get_db),
) -> DataFlowGraph:
    """获取数据流向图（节点和边的有向图）。

    Requires: READ on DATALAKE_DASHBOARD.
    Validates: Requirements 6.5, 7.2, 7.3
    """
    sources = _get_datalake_sources(auth.tenant_id, db)
    if not sources:
        return DataFlowGraph(nodes=[], edges=[])

    # Build nodes from data sources
    nodes: List[FlowNode] = []
    for source in sources:
        node_type = _classify_source_type(source.source_type)
        nodes.append(FlowNode(
            id=str(source.id),
            label=source.name,
            type=node_type,
            status=source.status.value,
        ))

    # Add a central platform node
    platform_id = "platform"
    nodes.append(FlowNode(
        id=platform_id,
        label="DataSync Platform",
        type="warehouse",
        status="active",
    ))

    # Build edges: each source connects to the platform
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    edges: List[FlowEdge] = []
    for source in sources:
        latest_volume = (
            db.query(DatalakeMetricsModel)
            .filter(
                DatalakeMetricsModel.source_id == source.id,
                DatalakeMetricsModel.metric_type == "volume",
                DatalakeMetricsModel.recorded_at >= cutoff,
            )
            .order_by(DatalakeMetricsModel.recorded_at.desc())
            .first()
        )
        volume_gb = 0.0
        if latest_volume and latest_volume.metric_data:
            volume_gb = latest_volume.metric_data.get("volume_gb", 0.0)

        sync_status = "active" if source.status == DataSourceStatus.ACTIVE else "inactive"
        edges.append(FlowEdge(
            source=str(source.id),
            target=platform_id,
            volume_gb=round(volume_gb, 2),
            sync_status=sync_status,
        ))

    return DataFlowGraph(nodes=nodes, edges=edges)


def _classify_source_type(source_type: DataSourceType) -> str:
    """Classify a DataSourceType into a flow graph node type."""
    lake_types = {DataSourceType.DELTA_LAKE, DataSourceType.ICEBERG, DataSourceType.HIVE}
    if source_type in lake_types:
        return "lake"
    return "source"
