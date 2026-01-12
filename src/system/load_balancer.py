"""
Load Balancer for High Availability System.

Provides intelligent load balancing, health-aware routing,
and traffic distribution for the high availability infrastructure.
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from src.system.service_registry import (
    ServiceRegistry, ServiceInstance, ServiceStatus, ServiceRole,
    get_service_registry
)

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    IP_HASH = "ip_hash"
    WEIGHTED_RANDOM = "weighted_random"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for an instance."""
    instance_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 30.0


@dataclass
class LoadBalancerConfig:
    """Configuration for load balancer."""
    default_strategy: LoadBalancingStrategy = LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
    health_check_interval: float = 10.0
    circuit_breaker_enabled: bool = True
    circuit_failure_threshold: int = 5
    circuit_success_threshold: int = 3
    circuit_timeout_seconds: float = 30.0
    sticky_sessions_enabled: bool = False
    sticky_session_ttl: float = 3600.0


@dataclass
class InstanceMetrics:
    """Metrics for a service instance."""
    instance_id: str
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_request_time: Optional[float] = None


class LoadBalancer:
    """
    Intelligent load balancer with health-aware routing.
    
    Features:
    - Multiple load balancing strategies
    - Circuit breaker pattern
    - Health-based instance selection
    - Connection tracking
    - Sticky sessions support
    """
    
    def __init__(self, config: Optional[LoadBalancerConfig] = None):
        self.config = config or LoadBalancerConfig()
        self.service_registry: Optional[ServiceRegistry] = None
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.instance_metrics: Dict[str, InstanceMetrics] = {}
        self.round_robin_counters: Dict[str, int] = defaultdict(int)
        self.sticky_sessions: Dict[str, str] = {}  # session_id -> instance_id
        self.service_strategies: Dict[str, LoadBalancingStrategy] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info("LoadBalancer initialized")
    
    async def start(self):
        """Start the load balancer."""
        if self._is_running:
            return
        
        self._is_running = True
        self.service_registry = get_service_registry()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("LoadBalancer started")
    
    async def stop(self):
        """Stop the load balancer."""
        self._is_running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("LoadBalancer stopped")
    
    async def _health_check_loop(self):
        """Background loop for health checking."""
        while self._is_running:
            try:
                await self._check_circuit_breakers()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)
    
    async def _check_circuit_breakers(self):
        """Check and update circuit breaker states."""
        current_time = time.time()
        
        for instance_id, breaker in self.circuit_breakers.items():
            if breaker.state == CircuitState.OPEN:
                # Check if timeout has passed
                if current_time - breaker.last_state_change > breaker.timeout_seconds:
                    breaker.state = CircuitState.HALF_OPEN
                    breaker.last_state_change = current_time
                    logger.info(f"Circuit breaker {instance_id}: OPEN -> HALF_OPEN")
    
    def set_strategy(self, service_name: str, strategy: LoadBalancingStrategy):
        """Set load balancing strategy for a service."""
        self.service_strategies[service_name] = strategy
        logger.info(f"Set strategy for {service_name}: {strategy.value}")
    
    def get_strategy(self, service_name: str) -> LoadBalancingStrategy:
        """Get load balancing strategy for a service."""
        return self.service_strategies.get(service_name, self.config.default_strategy)
    
    async def get_instance(
        self,
        service_name: str,
        session_id: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """
        Get a service instance using load balancing.
        
        Args:
            service_name: Name of the service
            session_id: Optional session ID for sticky sessions
            client_ip: Optional client IP for IP hash
        
        Returns:
            Selected ServiceInstance or None
        """
        if not self.service_registry:
            self.service_registry = get_service_registry()
            if not self.service_registry:
                return None
        
        # Check sticky session
        if self.config.sticky_sessions_enabled and session_id:
            sticky_instance_id = self.sticky_sessions.get(session_id)
            if sticky_instance_id:
                instance = self.service_registry.get_instance(sticky_instance_id)
                if instance and instance.status == ServiceStatus.HEALTHY:
                    if self._is_circuit_closed(sticky_instance_id):
                        return instance
        
        # Get healthy instances
        instances = self.service_registry.get_healthy_instances(service_name)
        
        # Filter by circuit breaker
        if self.config.circuit_breaker_enabled:
            instances = [i for i in instances if self._is_circuit_closed(i.instance_id)]
        
        if not instances:
            logger.warning(f"No healthy instances available for {service_name}")
            return None
        
        # Select instance based on strategy
        strategy = self.get_strategy(service_name)
        instance = self._select_instance(instances, strategy, client_ip)
        
        # Update sticky session
        if self.config.sticky_sessions_enabled and session_id and instance:
            self.sticky_sessions[session_id] = instance.instance_id
        
        return instance
    
    def _select_instance(
        self,
        instances: List[ServiceInstance],
        strategy: LoadBalancingStrategy,
        client_ip: Optional[str] = None
    ) -> Optional[ServiceInstance]:
        """Select an instance based on strategy."""
        if not instances:
            return None
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(instances)
        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin(instances)
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(instances)
        elif strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(instances)
        elif strategy == LoadBalancingStrategy.WEIGHTED_RANDOM:
            return self._weighted_random(instances)
        elif strategy == LoadBalancingStrategy.IP_HASH:
            return self._ip_hash(instances, client_ip)
        else:
            return instances[0]
    
    def _round_robin(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Round robin selection."""
        service_name = instances[0].service_name
        counter = self.round_robin_counters[service_name]
        instance = instances[counter % len(instances)]
        self.round_robin_counters[service_name] = counter + 1
        return instance
    
    def _weighted_round_robin(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted round robin selection."""
        # Build weighted list
        weighted_instances = []
        for instance in instances:
            weight = instance.weight // 10  # Normalize weight
            weighted_instances.extend([instance] * max(1, weight))
        
        service_name = instances[0].service_name
        counter = self.round_robin_counters[service_name]
        instance = weighted_instances[counter % len(weighted_instances)]
        self.round_robin_counters[service_name] = counter + 1
        return instance
    
    def _least_connections(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Least connections selection."""
        min_connections = float('inf')
        selected = instances[0]
        
        for instance in instances:
            metrics = self.instance_metrics.get(instance.instance_id)
            connections = metrics.active_connections if metrics else 0
            
            if connections < min_connections:
                min_connections = connections
                selected = instance
        
        return selected
    
    def _weighted_random(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted random selection."""
        total_weight = sum(i.weight for i in instances)
        r = random.uniform(0, total_weight)
        
        cumulative = 0
        for instance in instances:
            cumulative += instance.weight
            if r <= cumulative:
                return instance
        
        return instances[-1]
    
    def _ip_hash(
        self, 
        instances: List[ServiceInstance], 
        client_ip: Optional[str]
    ) -> ServiceInstance:
        """IP hash selection."""
        if not client_ip:
            return random.choice(instances)
        
        hash_value = hash(client_ip)
        index = hash_value % len(instances)
        return instances[index]
    
    def _is_circuit_closed(self, instance_id: str) -> bool:
        """Check if circuit breaker allows requests."""
        breaker = self.circuit_breakers.get(instance_id)
        if not breaker:
            return True
        
        return breaker.state != CircuitState.OPEN
    
    def _get_or_create_breaker(self, instance_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for instance."""
        if instance_id not in self.circuit_breakers:
            self.circuit_breakers[instance_id] = CircuitBreaker(
                instance_id=instance_id,
                failure_threshold=self.config.circuit_failure_threshold,
                success_threshold=self.config.circuit_success_threshold,
                timeout_seconds=self.config.circuit_timeout_seconds
            )
        return self.circuit_breakers[instance_id]
    
    def _get_or_create_metrics(self, instance_id: str) -> InstanceMetrics:
        """Get or create metrics for instance."""
        if instance_id not in self.instance_metrics:
            self.instance_metrics[instance_id] = InstanceMetrics(instance_id=instance_id)
        return self.instance_metrics[instance_id]
    
    async def record_success(self, instance_id: str, response_time: float = 0):
        """Record a successful request."""
        metrics = self._get_or_create_metrics(instance_id)
        metrics.total_requests += 1
        metrics.last_request_time = time.time()
        
        # Update average response time
        if metrics.avg_response_time == 0:
            metrics.avg_response_time = response_time
        else:
            metrics.avg_response_time = (metrics.avg_response_time * 0.9) + (response_time * 0.1)
        
        # Update circuit breaker
        if self.config.circuit_breaker_enabled:
            breaker = self._get_or_create_breaker(instance_id)
            
            if breaker.state == CircuitState.HALF_OPEN:
                breaker.success_count += 1
                if breaker.success_count >= breaker.success_threshold:
                    breaker.state = CircuitState.CLOSED
                    breaker.failure_count = 0
                    breaker.success_count = 0
                    breaker.last_state_change = time.time()
                    logger.info(f"Circuit breaker {instance_id}: HALF_OPEN -> CLOSED")
    
    async def record_failure(self, instance_id: str):
        """Record a failed request."""
        metrics = self._get_or_create_metrics(instance_id)
        metrics.total_requests += 1
        metrics.failed_requests += 1
        metrics.last_request_time = time.time()
        
        # Update circuit breaker
        if self.config.circuit_breaker_enabled:
            breaker = self._get_or_create_breaker(instance_id)
            breaker.failure_count += 1
            breaker.last_failure = time.time()
            
            if breaker.state == CircuitState.HALF_OPEN:
                # Immediate open on failure in half-open state
                breaker.state = CircuitState.OPEN
                breaker.last_state_change = time.time()
                logger.warning(f"Circuit breaker {instance_id}: HALF_OPEN -> OPEN")
            elif breaker.state == CircuitState.CLOSED:
                if breaker.failure_count >= breaker.failure_threshold:
                    breaker.state = CircuitState.OPEN
                    breaker.last_state_change = time.time()
                    logger.warning(f"Circuit breaker {instance_id}: CLOSED -> OPEN")
    
    async def add_healthy_instance(self, instance: ServiceInstance):
        """Add a healthy instance to load balancing."""
        if self.service_registry:
            await self.service_registry.update_status(instance.instance_id, ServiceStatus.HEALTHY)
        
        # Reset circuit breaker
        if instance.instance_id in self.circuit_breakers:
            breaker = self.circuit_breakers[instance.instance_id]
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
            breaker.success_count = 0
        
        logger.info(f"Added healthy instance: {instance.instance_id}")
    
    async def remove_unhealthy_instance(self, service_name: str):
        """Remove an unhealthy instance from load balancing."""
        if not self.service_registry:
            return
        
        instances = self.service_registry.get_instances(service_name)
        for instance in instances:
            if instance.status == ServiceStatus.UNHEALTHY:
                # Open circuit breaker
                breaker = self._get_or_create_breaker(instance.instance_id)
                breaker.state = CircuitState.OPEN
                breaker.last_state_change = time.time()
                
                logger.info(f"Removed unhealthy instance: {instance.instance_id}")
    
    def increment_connections(self, instance_id: str):
        """Increment active connections for an instance."""
        metrics = self._get_or_create_metrics(instance_id)
        metrics.active_connections += 1
    
    def decrement_connections(self, instance_id: str):
        """Decrement active connections for an instance."""
        metrics = self._get_or_create_metrics(instance_id)
        metrics.active_connections = max(0, metrics.active_connections - 1)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        return {
            "total_instances_tracked": len(self.instance_metrics),
            "circuit_breakers": {
                "total": len(self.circuit_breakers),
                "open": len([b for b in self.circuit_breakers.values() if b.state == CircuitState.OPEN]),
                "half_open": len([b for b in self.circuit_breakers.values() if b.state == CircuitState.HALF_OPEN]),
                "closed": len([b for b in self.circuit_breakers.values() if b.state == CircuitState.CLOSED]),
            },
            "sticky_sessions": len(self.sticky_sessions),
            "service_strategies": {k: v.value for k, v in self.service_strategies.items()},
            "instance_metrics": {
                iid: {
                    "active_connections": m.active_connections,
                    "total_requests": m.total_requests,
                    "failed_requests": m.failed_requests,
                    "avg_response_time": m.avg_response_time
                }
                for iid, m in self.instance_metrics.items()
            }
        }


# Global load balancer instance
load_balancer: Optional[LoadBalancer] = None


async def initialize_load_balancer(config: Optional[LoadBalancerConfig] = None) -> LoadBalancer:
    """Initialize the global load balancer."""
    global load_balancer
    
    load_balancer = LoadBalancer(config)
    await load_balancer.start()
    
    return load_balancer


async def shutdown_load_balancer():
    """Shutdown the global load balancer."""
    global load_balancer
    
    if load_balancer:
        await load_balancer.stop()
        load_balancer = None


def get_load_balancer() -> Optional[LoadBalancer]:
    """Get the global load balancer instance."""
    return load_balancer
