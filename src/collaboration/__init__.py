"""
Collaboration Workflow Module (协作与审核流程)

This module provides comprehensive collaboration and review workflow functionality:
- Task Dispatcher: Intelligent task assignment based on skills and workload
- Collaboration Engine: Multi-user collaboration with real-time sync
- Review Flow Manager: Multi-level review process management
- Conflict Resolver: Annotation conflict detection and resolution
- Quality Controller: Quality monitoring and control
- Notification Service: Multi-channel notifications
- Crowdsource Manager: Crowdsourcing task management
- Crowdsource Billing: Crowdsourcing billing and settlement
- Third Party Platform Adapter: Integration with external platforms
"""

from .task_dispatcher import TaskDispatcher, AssignmentMode
from .collaboration_engine import CollaborationEngine
from .review_flow_manager import ReviewFlowManager, ReviewStatus
from .conflict_resolver import ConflictResolver
from .quality_controller import QualityController
from .notification_service import NotificationService
from .crowdsource_manager import CrowdsourceManager
from .crowdsource_annotator_manager import CrowdsourceAnnotatorManager, AnnotatorStatus
from .crowdsource_billing import CrowdsourceBilling
from .third_party_platform_adapter import ThirdPartyPlatformAdapter

# Redis cache schemas
from .redis_schemas import (
    CacheKeyPrefix,
    CacheTTL,
    RedisKeyBuilder,
    SessionCacheData,
    PresenceCacheData,
    ElementLockCacheData,
    BroadcastMessage as RedisBroadcastMessage,
    get_redis_scripts,
)

# Performance optimization modules
from .performance_cache import (
    CollaborationCacheService,
    get_collaboration_cache_service,
    CacheType,
    cached,
)
from .query_optimizer import (
    QueryOptimizer,
    get_query_optimizer,
    PaginationParams,
    PaginatedResult,
    ConnectionPoolConfig,
)
from .graph_query_optimizer import (
    GraphQueryOptimizer,
    get_graph_query_optimizer,
)
from .websocket_optimizer import (
    WebSocketBroadcastOptimizer,
    get_websocket_broadcast_optimizer,
    BroadcastMessage,
    MessageType,
    MessagePriority,
)

# Monitoring modules
from .monitoring import (
    PrometheusMetricsCollector,
    get_metrics_collector,
    StructuredLogger,
    get_structured_logger,
    HealthChecker,
    get_health_checker,
    HealthStatus,
    HealthCheckResult,
    track_request,
    track_websocket_message,
    track_collaboration_session,
)

__all__ = [
    "TaskDispatcher",
    "AssignmentMode",
    "CollaborationEngine",
    "ReviewFlowManager",
    "ReviewStatus",
    "ConflictResolver",
    "QualityController",
    "NotificationService",
    "CrowdsourceManager",
    "CrowdsourceAnnotatorManager",
    "AnnotatorStatus",
    "CrowdsourceBilling",
    "ThirdPartyPlatformAdapter",
    # Redis cache schemas
    "CacheKeyPrefix",
    "CacheTTL",
    "RedisKeyBuilder",
    "SessionCacheData",
    "PresenceCacheData",
    "ElementLockCacheData",
    "RedisBroadcastMessage",
    "get_redis_scripts",
    # Performance optimization
    "CollaborationCacheService",
    "get_collaboration_cache_service",
    "CacheType",
    "cached",
    "QueryOptimizer",
    "get_query_optimizer",
    "PaginationParams",
    "PaginatedResult",
    "ConnectionPoolConfig",
    "GraphQueryOptimizer",
    "get_graph_query_optimizer",
    "WebSocketBroadcastOptimizer",
    "get_websocket_broadcast_optimizer",
    "BroadcastMessage",
    "MessageType",
    "MessagePriority",
    # Monitoring
    "PrometheusMetricsCollector",
    "get_metrics_collector",
    "StructuredLogger",
    "get_structured_logger",
    "HealthChecker",
    "get_health_checker",
    "HealthStatus",
    "HealthCheckResult",
    "track_request",
    "track_websocket_message",
    "track_collaboration_session",
]
