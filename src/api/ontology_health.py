"""
本体专家协作健康检查 API

提供健康检查端点：
- /health - 基本健康检查
- /health/db - 数据库连接检查
- /health/redis - Redis 连接检查
- /health/neo4j - Neo4j 连接检查
- /metrics - Prometheus 指标

Validates: Task 29.3 - Add health check endpoints
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel

from src.collaboration.monitoring import (
    get_health_checker,
    get_metrics_collector,
    HealthStatus,
    HealthCheckResult,
    ComponentHealth,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str = "1.0.0"
    components: Optional[list] = None


class MetricsResponse(BaseModel):
    """指标响应"""
    counters: Dict[str, Any]
    gauges: Dict[str, Any]
    histograms: Dict[str, Any]


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    基本健康检查
    
    返回服务的整体健康状态
    """
    checker = get_health_checker()
    result = await checker.check_all()
    
    return HealthResponse(
        status=result.status.value,
        timestamp=result.timestamp.isoformat(),
        version=result.version,
        components=[c.to_dict() for c in result.components],
    )


@router.get("/db", response_model=HealthResponse)
async def database_health_check() -> HealthResponse:
    """
    数据库健康检查
    
    检查 PostgreSQL 数据库连接
    """
    checker = get_health_checker()
    result = await checker.check_component("database")
    
    if result is None:
        raise HTTPException(status_code=500, detail="Database check not configured")
    
    return HealthResponse(
        status=result.status.value,
        timestamp=datetime.now().isoformat(),
        components=[result.to_dict()],
    )


@router.get("/redis", response_model=HealthResponse)
async def redis_health_check() -> HealthResponse:
    """
    Redis 健康检查
    
    检查 Redis 连接
    """
    checker = get_health_checker()
    result = await checker.check_component("redis")
    
    if result is None:
        raise HTTPException(status_code=500, detail="Redis check not configured")
    
    return HealthResponse(
        status=result.status.value,
        timestamp=datetime.now().isoformat(),
        components=[result.to_dict()],
    )


@router.get("/neo4j", response_model=HealthResponse)
async def neo4j_health_check() -> HealthResponse:
    """
    Neo4j 健康检查
    
    检查 Neo4j 图数据库连接
    """
    checker = get_health_checker()
    result = await checker.check_component("neo4j")
    
    if result is None:
        raise HTTPException(status_code=500, detail="Neo4j check not configured")
    
    return HealthResponse(
        status=result.status.value,
        timestamp=datetime.now().isoformat(),
        components=[result.to_dict()],
    )


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    就绪检查
    
    检查服务是否准备好接收请求
    """
    checker = get_health_checker()
    result = await checker.check_all()
    
    if result.status == HealthStatus.UNHEALTHY:
        raise HTTPException(
            status_code=503,
            detail="Service not ready",
        )
    
    return {
        "ready": True,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    存活检查
    
    检查服务是否存活
    """
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat(),
    }


# Prometheus 指标端点
metrics_router = APIRouter(tags=["Metrics"])


@metrics_router.get("/metrics")
async def prometheus_metrics() -> Response:
    """
    Prometheus 指标端点
    
    返回 Prometheus 格式的指标
    """
    collector = get_metrics_collector()
    metrics_text = await collector.export_prometheus_format()
    
    return Response(
        content=metrics_text,
        media_type="text/plain; charset=utf-8",
    )


@metrics_router.get("/metrics/json", response_model=MetricsResponse)
async def json_metrics() -> MetricsResponse:
    """
    JSON 格式指标端点
    
    返回 JSON 格式的指标
    """
    collector = get_metrics_collector()
    metrics = await collector.get_metrics()
    
    return MetricsResponse(**metrics)
