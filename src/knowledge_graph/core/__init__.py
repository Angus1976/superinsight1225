"""
Core module for Knowledge Graph.

Provides graph database connections, data models, performance optimization,
and monitoring capabilities.
"""

from .models import (
    Entity,
    Relation,
    EntityType,
    RelationType,
    GraphSchema,
    ExtractedEntity,
    ExtractedRelation,
)
from .graph_db import GraphDatabase, get_graph_database
from .performance import (
    QueryCache,
    QueryPerformanceTracker,
    BatchProcessor,
    ConnectionPoolMonitor,
    get_query_cache,
    get_performance_tracker,
    get_batch_processor,
    get_pool_monitor,
    cached_query,
    tracked_query,
    CacheStrategy,
)
from .monitoring import (
    MetricsCollector,
    HealthChecker,
    StructuredLogger,
    ErrorTracker,
    SystemMonitor,
    get_system_monitor,
    get_logger,
    monitored,
    configure_logging,
    HealthStatus,
    MetricType,
)

__all__ = [
    # Models
    "Entity",
    "Relation",
    "EntityType",
    "RelationType",
    "GraphSchema",
    "ExtractedEntity",
    "ExtractedRelation",
    # Database
    "GraphDatabase",
    "get_graph_database",
    # Performance
    "QueryCache",
    "QueryPerformanceTracker",
    "BatchProcessor",
    "ConnectionPoolMonitor",
    "get_query_cache",
    "get_performance_tracker",
    "get_batch_processor",
    "get_pool_monitor",
    "cached_query",
    "tracked_query",
    "CacheStrategy",
    # Monitoring
    "MetricsCollector",
    "HealthChecker",
    "StructuredLogger",
    "ErrorTracker",
    "SystemMonitor",
    "get_system_monitor",
    "get_logger",
    "monitored",
    "configure_logging",
    "HealthStatus",
    "MetricType",
]
