"""
Service discovery and registration system for high availability.

This module provides service discovery capabilities including:
- Service registration and deregistration
- Service lookup and discovery
- Health status tracking
- Metadata management
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
import redis.asyncio as redis
from redis.asyncio import Redis

from .models import ServiceInstance, ServiceStatus, ServiceMetrics
from ..monitoring.sync_metrics import SyncMetrics


logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Service registry for managing service instances."""
    
    def __init__(self, redis_client: Redis, ttl: int = 60):
        """
        Initialize service registry.
        
        Args:
            redis_client: Redis client for storage
            ttl: Time-to-live for service registrations in seconds
        """
        self.redis = redis_client
        self.ttl = ttl
        self.services_key = "sync:services"
        self.metrics_key = "sync:service_metrics"
        
    async def register_service(self, service: ServiceInstance) -> bool:
        """
        Register a service instance.
        
        Args:
            service: Service instance to register
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            service_key = f"{self.services_key}:{service.name}:{service.id}"
            service_data = {
                "id": service.id,
                "name": service.name,
                "host": service.host,
                "port": service.port,
                "version": service.version,
                "status": service.status.value,
                "metadata": json.dumps(service.metadata),
                "health_check_url": service.health_check_url,
                "weight": service.weight,
                "max_connections": service.max_connections,
                "current_connections": service.current_connections,
                "registered_at": service.registered_at.isoformat(),
                "updated_at": service.updated_at.isoformat()
            }
            
            # Store service data with TTL
            await self.redis.hset(service_key, mapping=service_data)
            await self.redis.expire(service_key, self.ttl)
            
            # Add to service list
            await self.redis.sadd(f"{self.services_key}:{service.name}", service.id)
            
            logger.info(f"Registered service {service.name}:{service.id} at {service.endpoint}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service.name}:{service.id}: {e}")
            return False
    
    async def deregister_service(self, service_name: str, service_id: str) -> bool:
        """
        Deregister a service instance.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
            
        Returns:
            True if deregistration successful, False otherwise
        """
        try:
            service_key = f"{self.services_key}:{service_name}:{service_id}"
            
            # Remove service data
            await self.redis.delete(service_key)
            
            # Remove from service list
            await self.redis.srem(f"{self.services_key}:{service_name}", service_id)
            
            logger.info(f"Deregistered service {service_name}:{service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deregister service {service_name}:{service_id}: {e}")
            return False
    
    async def get_service(self, service_name: str, service_id: str) -> Optional[ServiceInstance]:
        """
        Get a specific service instance.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
            
        Returns:
            Service instance if found, None otherwise
        """
        try:
            service_key = f"{self.services_key}:{service_name}:{service_id}"
            service_data = await self.redis.hgetall(service_key)
            
            if not service_data:
                return None
            
            return ServiceInstance(
                id=service_data["id"],
                name=service_data["name"],
                host=service_data["host"],
                port=int(service_data["port"]),
                version=service_data["version"],
                status=ServiceStatus(service_data["status"]),
                metadata=json.loads(service_data["metadata"]),
                health_check_url=service_data["health_check_url"],
                weight=int(service_data["weight"]),
                max_connections=int(service_data["max_connections"]),
                current_connections=int(service_data["current_connections"]),
                registered_at=datetime.fromisoformat(service_data["registered_at"]),
                updated_at=datetime.fromisoformat(service_data["updated_at"])
            )
            
        except Exception as e:
            logger.error(f"Failed to get service {service_name}:{service_id}: {e}")
            return None
    
    async def list_services(self, service_name: str) -> List[ServiceInstance]:
        """
        List all instances of a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of service instances
        """
        try:
            service_ids = await self.redis.smembers(f"{self.services_key}:{service_name}")
            services = []
            
            for service_id in service_ids:
                service = await self.get_service(service_name, service_id)
                if service:
                    services.append(service)
            
            return services
            
        except Exception as e:
            logger.error(f"Failed to list services for {service_name}: {e}")
            return []
    
    async def update_service_status(self, service_name: str, service_id: str, 
                                  status: ServiceStatus) -> bool:
        """
        Update service status.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
            status: New status
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            service_key = f"{self.services_key}:{service_name}:{service_id}"
            
            # Check if service exists
            exists = await self.redis.exists(service_key)
            if not exists:
                return False
            
            # Update status and timestamp
            await self.redis.hset(service_key, mapping={
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update service status {service_name}:{service_id}: {e}")
            return False
    
    async def update_service_metrics(self, service_name: str, service_id: str,
                                   metrics: ServiceMetrics) -> bool:
        """
        Update service metrics.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
            metrics: Service metrics
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            metrics_key = f"{self.metrics_key}:{service_name}:{service_id}"
            metrics_data = {
                "cpu_usage": metrics.cpu_usage,
                "memory_usage": metrics.memory_usage,
                "disk_usage": metrics.disk_usage,
                "network_in": metrics.network_in,
                "network_out": metrics.network_out,
                "request_count": metrics.request_count,
                "error_count": metrics.error_count,
                "response_time": metrics.response_time,
                "active_connections": metrics.active_connections,
                "timestamp": metrics.timestamp.isoformat()
            }
            
            # Store metrics with TTL
            await self.redis.hset(metrics_key, mapping=metrics_data)
            await self.redis.expire(metrics_key, self.ttl * 2)  # Keep metrics longer
            
            # Update current connections in service data
            service_key = f"{self.services_key}:{service_name}:{service_id}"
            await self.redis.hset(service_key, "current_connections", metrics.active_connections)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update service metrics {service_name}:{service_id}: {e}")
            return False
    
    async def cleanup_expired_services(self) -> int:
        """
        Clean up expired service registrations.
        
        Returns:
            Number of services cleaned up
        """
        try:
            cleaned_count = 0
            
            # Get all service names
            pattern = f"{self.services_key}:*"
            keys = await self.redis.keys(pattern)
            
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                
                # Skip service list keys
                if key_str.count(':') != 3:
                    continue
                
                # Check if key exists (not expired)
                exists = await self.redis.exists(key_str)
                if not exists:
                    # Extract service name and ID from key
                    parts = key_str.split(':')
                    if len(parts) >= 4:
                        service_name = parts[2]
                        service_id = parts[3]
                        
                        # Remove from service list
                        await self.redis.srem(f"{self.services_key}:{service_name}", service_id)
                        cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired service registrations")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired services: {e}")
            return 0


class ServiceDiscovery:
    """Service discovery client for finding and monitoring services."""
    
    def __init__(self, registry: ServiceRegistry):
        """
        Initialize service discovery.
        
        Args:
            registry: Service registry instance
        """
        self.registry = registry
        self._watchers: Dict[str, List[Callable]] = {}
        self._running = False
        self._watch_task: Optional[asyncio.Task] = None
    
    async def discover_services(self, service_name: str, 
                              healthy_only: bool = True) -> List[ServiceInstance]:
        """
        Discover available service instances.
        
        Args:
            service_name: Name of the service to discover
            healthy_only: Whether to return only healthy instances
            
        Returns:
            List of available service instances
        """
        services = await self.registry.list_services(service_name)
        
        if healthy_only:
            services = [s for s in services if s.is_healthy]
        
        return services
    
    async def find_best_instance(self, service_name: str,
                               criteria: str = "least_loaded") -> Optional[ServiceInstance]:
        """
        Find the best service instance based on criteria.
        
        Args:
            service_name: Name of the service
            criteria: Selection criteria (least_loaded, least_connections, random)
            
        Returns:
            Best service instance or None if none available
        """
        services = await self.discover_services(service_name, healthy_only=True)
        
        if not services:
            return None
        
        if criteria == "least_loaded":
            return min(services, key=lambda s: s.load_factor)
        elif criteria == "least_connections":
            return min(services, key=lambda s: s.current_connections)
        elif criteria == "random":
            import random
            return random.choice(services)
        else:
            # Default to first available
            return services[0]
    
    def add_service_watcher(self, service_name: str, 
                           callback: Callable[[List[ServiceInstance]], None]) -> None:
        """
        Add a watcher for service changes.
        
        Args:
            service_name: Name of the service to watch
            callback: Callback function to call when services change
        """
        if service_name not in self._watchers:
            self._watchers[service_name] = []
        
        self._watchers[service_name].append(callback)
    
    def remove_service_watcher(self, service_name: str,
                              callback: Callable[[List[ServiceInstance]], None]) -> None:
        """
        Remove a service watcher.
        
        Args:
            service_name: Name of the service
            callback: Callback function to remove
        """
        if service_name in self._watchers:
            try:
                self._watchers[service_name].remove(callback)
                if not self._watchers[service_name]:
                    del self._watchers[service_name]
            except ValueError:
                pass
    
    async def start_watching(self, interval: int = 10) -> None:
        """
        Start watching for service changes.
        
        Args:
            interval: Watch interval in seconds
        """
        if self._running:
            return
        
        self._running = True
        self._watch_task = asyncio.create_task(self._watch_loop(interval))
    
    async def stop_watching(self) -> None:
        """Stop watching for service changes."""
        self._running = False
        
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
    
    async def _watch_loop(self, interval: int) -> None:
        """Internal watch loop for monitoring service changes."""
        previous_services: Dict[str, List[ServiceInstance]] = {}
        
        while self._running:
            try:
                for service_name in list(self._watchers.keys()):
                    current_services = await self.discover_services(service_name, healthy_only=False)
                    
                    # Check if services changed
                    prev_services = previous_services.get(service_name, [])
                    if self._services_changed(prev_services, current_services):
                        # Notify watchers
                        for callback in self._watchers.get(service_name, []):
                            try:
                                callback(current_services)
                            except Exception as e:
                                logger.error(f"Error in service watcher callback: {e}")
                        
                        previous_services[service_name] = current_services
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in service watch loop: {e}")
                await asyncio.sleep(interval)
    
    def _services_changed(self, prev: List[ServiceInstance], 
                         current: List[ServiceInstance]) -> bool:
        """Check if service list has changed."""
        if len(prev) != len(current):
            return True
        
        prev_ids = {s.id for s in prev}
        current_ids = {s.id for s in current}
        
        if prev_ids != current_ids:
            return True
        
        # Check status changes
        prev_status = {s.id: s.status for s in prev}
        current_status = {s.id: s.status for s in current}
        
        return prev_status != current_status