"""
Load balancer implementation for high availability.

This module provides load balancing capabilities including:
- Multiple load balancing strategies
- Health-aware routing
- Connection tracking
- Sticky sessions support
"""

import asyncio
import hashlib
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import aiohttp

from .models import (
    ServiceInstance, LoadBalancingStrategy, LoadBalancerConfig,
    ServiceStatus, ServiceMetrics
)
from .service_discovery import ServiceDiscovery


logger = logging.getLogger(__name__)


class LoadBalancer:
    """Load balancer for distributing requests across service instances."""
    
    def __init__(self, service_discovery: ServiceDiscovery, config: LoadBalancerConfig):
        """
        Initialize load balancer.
        
        Args:
            service_discovery: Service discovery instance
            config: Load balancer configuration
        """
        self.discovery = service_discovery
        self.config = config
        self.session_store: Dict[str, str] = {}  # session_id -> instance_id
        self.connection_counts: Dict[str, int] = {}  # instance_id -> connection_count
        self.response_times: Dict[str, List[float]] = {}  # instance_id -> response_times
        self.round_robin_index: Dict[str, int] = {}  # service_name -> index
        self._session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
    
    async def select_instance(self, service_name: str, 
                            session_id: Optional[str] = None,
                            request_hash: Optional[str] = None) -> Optional[ServiceInstance]:
        """
        Select a service instance based on load balancing strategy.
        
        Args:
            service_name: Name of the service
            session_id: Session ID for sticky sessions
            request_hash: Request hash for hash-based routing
            
        Returns:
            Selected service instance or None if none available
        """
        # Check for sticky session
        if session_id and self.config.sticky_sessions:
            instance_id = self.session_store.get(session_id)
            if instance_id:
                instance = await self._get_instance_by_id(service_name, instance_id)
                if instance and instance.is_healthy:
                    return instance
                else:
                    # Remove invalid session
                    del self.session_store[session_id]
        
        # Get available instances
        instances = await self.discovery.discover_services(service_name, healthy_only=True)
        if not instances:
            return None
        
        # Apply load balancing strategy
        selected = await self._apply_strategy(service_name, instances, request_hash)
        
        # Store session if sticky sessions enabled
        if selected and session_id and self.config.sticky_sessions:
            self.session_store[session_id] = selected.id
        
        return selected
    
    async def _apply_strategy(self, service_name: str, instances: List[ServiceInstance],
                            request_hash: Optional[str] = None) -> Optional[ServiceInstance]:
        """Apply the configured load balancing strategy."""
        if not instances:
            return None
        
        strategy = self.config.strategy
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(service_name, instances)
        
        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(instances)
        
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(instances)
        
        elif strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time_select(instances)
        
        elif strategy == LoadBalancingStrategy.HASH_BASED:
            return self._hash_based_select(instances, request_hash or "")
        
        elif strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(instances)
        
        else:
            # Default to round robin
            return self._round_robin_select(service_name, instances)
    
    def _round_robin_select(self, service_name: str, 
                           instances: List[ServiceInstance]) -> ServiceInstance:
        """Round robin selection."""
        if service_name not in self.round_robin_index:
            self.round_robin_index[service_name] = 0
        
        index = self.round_robin_index[service_name]
        selected = instances[index % len(instances)]
        self.round_robin_index[service_name] = (index + 1) % len(instances)
        
        return selected
    
    def _weighted_round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted round robin selection based on instance weights."""
        total_weight = sum(instance.weight for instance in instances)
        if total_weight == 0:
            return random.choice(instances)
        
        # Create weighted list
        weighted_instances = []
        for instance in instances:
            weighted_instances.extend([instance] * instance.weight)
        
        return random.choice(weighted_instances)
    
    def _least_connections_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Select instance with least connections."""
        return min(instances, key=lambda i: self.connection_counts.get(i.id, 0))
    
    def _least_response_time_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Select instance with least average response time."""
        def avg_response_time(instance: ServiceInstance) -> float:
            times = self.response_times.get(instance.id, [])
            return sum(times) / len(times) if times else 0.0
        
        return min(instances, key=avg_response_time)
    
    def _hash_based_select(self, instances: List[ServiceInstance], 
                          hash_key: str) -> ServiceInstance:
        """Hash-based selection for consistent routing."""
        if not hash_key:
            return random.choice(instances)
        
        # Create consistent hash
        hash_value = int(hashlib.md5(hash_key.encode()).hexdigest(), 16)
        index = hash_value % len(instances)
        
        return instances[index]
    
    async def _get_instance_by_id(self, service_name: str, 
                                 instance_id: str) -> Optional[ServiceInstance]:
        """Get service instance by ID."""
        instances = await self.discovery.discover_services(service_name, healthy_only=False)
        for instance in instances:
            if instance.id == instance_id:
                return instance
        return None
    
    async def execute_request(self, service_name: str, path: str = "/",
                            method: str = "GET", **kwargs) -> Optional[aiohttp.ClientResponse]:
        """
        Execute a request with load balancing and retry logic.
        
        Args:
            service_name: Name of the service
            path: Request path
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            Response object or None if all attempts failed
        """
        if not self._session:
            raise RuntimeError("LoadBalancer must be used as async context manager")
        
        session_id = kwargs.pop('session_id', None)
        request_hash = kwargs.pop('request_hash', None)
        
        for attempt in range(self.config.max_retries + 1):
            instance = await self.select_instance(service_name, session_id, request_hash)
            if not instance:
                logger.warning(f"No available instances for service {service_name}")
                return None
            
            try:
                # Track connection
                self._increment_connection(instance.id)
                
                start_time = time.time()
                url = f"{instance.endpoint}{path}"
                
                async with self._session.request(method, url, **kwargs) as response:
                    # Track response time
                    response_time = time.time() - start_time
                    self._record_response_time(instance.id, response_time)
                    
                    # Decrement connection count
                    self._decrement_connection(instance.id)
                    
                    if response.status < 500:  # Don't retry on client errors
                        return response
                    
                    logger.warning(f"Server error {response.status} from {instance.endpoint}")
            
            except Exception as e:
                logger.error(f"Request failed to {instance.endpoint}: {e}")
                self._decrement_connection(instance.id)
                
                # Mark instance as unhealthy if multiple failures
                await self._handle_instance_failure(service_name, instance.id)
            
            # Wait before retry
            if attempt < self.config.max_retries:
                await asyncio.sleep(self.config.retry_timeout * (attempt + 1))
        
        logger.error(f"All retry attempts failed for service {service_name}")
        return None
    
    def _increment_connection(self, instance_id: str) -> None:
        """Increment connection count for instance."""
        self.connection_counts[instance_id] = self.connection_counts.get(instance_id, 0) + 1
    
    def _decrement_connection(self, instance_id: str) -> None:
        """Decrement connection count for instance."""
        if instance_id in self.connection_counts:
            self.connection_counts[instance_id] = max(0, self.connection_counts[instance_id] - 1)
    
    def _record_response_time(self, instance_id: str, response_time: float) -> None:
        """Record response time for instance."""
        if instance_id not in self.response_times:
            self.response_times[instance_id] = []
        
        times = self.response_times[instance_id]
        times.append(response_time)
        
        # Keep only recent response times (last 100)
        if len(times) > 100:
            times.pop(0)
    
    async def _handle_instance_failure(self, service_name: str, instance_id: str) -> None:
        """Handle instance failure by marking it unhealthy."""
        try:
            await self.discovery.registry.update_service_status(
                service_name, instance_id, ServiceStatus.UNHEALTHY
            )
        except Exception as e:
            logger.error(f"Failed to update instance status: {e}")
    
    def get_connection_stats(self) -> Dict[str, int]:
        """Get current connection statistics."""
        return self.connection_counts.copy()
    
    def get_response_time_stats(self) -> Dict[str, Dict[str, float]]:
        """Get response time statistics."""
        stats = {}
        for instance_id, times in self.response_times.items():
            if times:
                stats[instance_id] = {
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "count": len(times)
                }
        return stats
    
    def cleanup_sessions(self, max_age: int = 3600) -> int:
        """
        Clean up expired sessions.
        
        Args:
            max_age: Maximum session age in seconds
            
        Returns:
            Number of sessions cleaned up
        """
        # Note: This is a simplified implementation
        # In production, you'd want to track session timestamps
        cleaned = 0
        if len(self.session_store) > 1000:  # Arbitrary limit
            # Remove oldest sessions (simplified)
            items = list(self.session_store.items())
            to_remove = items[:len(items) // 2]
            for session_id, _ in to_remove:
                del self.session_store[session_id]
                cleaned += 1
        
        return cleaned


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Timeout in seconds before trying to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
        
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.utcnow() - self.last_failure_time).total_seconds() >= self.timeout
    
    def _on_success(self) -> None:
        """Handle successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self) -> None:
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }