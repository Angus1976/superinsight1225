"""
Data models for high availability components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid


class ServiceStatus(Enum):
    """Service status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class LoadBalancingStrategy(Enum):
    """Load balancing strategy enumeration."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    HASH_BASED = "hash_based"
    RANDOM = "random"


class FailoverStrategy(Enum):
    """Failover strategy enumeration."""
    IMMEDIATE = "immediate"
    GRACEFUL = "graceful"
    MANUAL = "manual"
    CIRCUIT_BREAKER = "circuit_breaker"


class RecoveryAction(Enum):
    """Recovery action enumeration."""
    RESTART_SERVICE = "restart_service"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    REDIRECT_TRAFFIC = "redirect_traffic"
    ALERT_ADMIN = "alert_admin"
    AUTO_HEAL = "auto_heal"


@dataclass
class ServiceInstance:
    """Represents a service instance in the cluster."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    host: str = ""
    port: int = 0
    version: str = "1.0.0"
    status: ServiceStatus = ServiceStatus.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_check_url: str = ""
    weight: int = 1
    max_connections: int = 100
    current_connections: int = 0
    last_health_check: Optional[datetime] = None
    registered_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def endpoint(self) -> str:
        """Get the service endpoint URL."""
        return f"http://{self.host}:{self.port}"

    @property
    def is_healthy(self) -> bool:
        """Check if the service instance is healthy."""
        return self.status == ServiceStatus.HEALTHY

    @property
    def load_factor(self) -> float:
        """Calculate the current load factor (0.0 to 1.0)."""
        if self.max_connections == 0:
            return 0.0
        return min(self.current_connections / self.max_connections, 1.0)


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    interval: int = 30  # seconds
    timeout: int = 5    # seconds
    retries: int = 3
    failure_threshold: int = 3
    success_threshold: int = 2
    path: str = "/health"
    method: str = "GET"
    expected_status: int = 200
    expected_body: Optional[str] = None


@dataclass
class LoadBalancerConfig:
    """Load balancer configuration."""
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    health_check_enabled: bool = True
    health_check_config: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    sticky_sessions: bool = False
    session_timeout: int = 3600  # seconds
    max_retries: int = 3
    retry_timeout: int = 1  # seconds


@dataclass
class FailoverConfig:
    """Failover configuration."""
    strategy: FailoverStrategy = FailoverStrategy.GRACEFUL
    timeout: int = 30  # seconds
    max_attempts: int = 3
    backoff_multiplier: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60  # seconds
    notification_enabled: bool = True


@dataclass
class ClusterConfig:
    """Cluster configuration."""
    name: str = "superinsight-sync-cluster"
    min_instances: int = 2
    max_instances: int = 10
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 80.0
    scale_up_cooldown: int = 300  # seconds
    scale_down_cooldown: int = 600  # seconds
    load_balancer_config: LoadBalancerConfig = field(default_factory=LoadBalancerConfig)
    failover_config: FailoverConfig = field(default_factory=FailoverConfig)


@dataclass
class ServiceMetrics:
    """Service metrics for monitoring and decision making."""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_in: float = 0.0
    network_out: float = 0.0
    request_count: int = 0
    error_count: int = 0
    response_time: float = 0.0
    active_connections: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100.0


@dataclass
class FailoverEvent:
    """Represents a failover event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_instance: str = ""
    target_instance: str = ""
    reason: str = ""
    strategy: FailoverStrategy = FailoverStrategy.GRACEFUL
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Get failover duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class RecoveryPlan:
    """Recovery plan for service failures."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str = ""
    failure_type: str = ""
    actions: List[RecoveryAction] = field(default_factory=list)
    priority: int = 1  # 1 = highest, 10 = lowest
    timeout: int = 300  # seconds
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None