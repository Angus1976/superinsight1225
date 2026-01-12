"""
Service Registry for High Availability System.

Provides service registration, discovery, and health tracking
for the high availability infrastructure.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service instance status."""
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    STOPPED = "stopped"


class ServiceRole(Enum):
    """Service role in HA setup."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BACKUP = "backup"
    READONLY = "readonly"


@dataclass
class ServiceInstance:
    """Represents a service instance."""
    instance_id: str
    service_name: str
    host: str
    port: int
    status: ServiceStatus = ServiceStatus.STARTING
    role: ServiceRole = ServiceRole.PRIMARY
    weight: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    health_check_url: Optional[str] = None
    version: str = "1.0.0"
    tags: Set[str] = field(default_factory=set)


@dataclass
class ServiceDefinition:
    """Definition of a service type."""
    service_name: str
    description: str
    health_check_path: str = "/health"
    health_check_interval: float = 30.0
    health_check_timeout: float = 10.0
    deregister_critical_after: float = 300.0
    min_instances: int = 1
    max_instances: int = 10


@dataclass
class ServiceRegistryConfig:
    """Configuration for service registry."""
    heartbeat_interval: float = 15.0
    heartbeat_timeout: float = 45.0
    cleanup_interval: float = 60.0
    enable_health_checks: bool = True


class ServiceRegistry:
    """
    Service registry for service discovery and management.
    
    Features:
    - Service registration and deregistration
    - Health-based instance management
    - Service discovery with filtering
    - Heartbeat monitoring
    - Automatic cleanup of stale instances
    """
    
    def __init__(self, config: Optional[ServiceRegistryConfig] = None):
        self.config = config or ServiceRegistryConfig()
        self.services: Dict[str, ServiceDefinition] = {}
        self.instances: Dict[str, ServiceInstance] = {}
        self.service_instances: Dict[str, Set[str]] = defaultdict(set)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Register default services
        self._register_default_services()
        
        logger.info("ServiceRegistry initialized")
    
    def _register_default_services(self):
        """Register default service definitions."""
        default_services = [
            ServiceDefinition(
                service_name="api_server",
                description="Main API server",
                health_check_path="/health",
                min_instances=1,
                max_instances=5
            ),
            ServiceDefinition(
                service_name="database",
                description="PostgreSQL database",
                health_check_path="/health",
                min_instances=1,
                max_instances=3
            ),
            ServiceDefinition(
                service_name="redis",
                description="Redis cache",
                health_check_path="/health",
                min_instances=1,
                max_instances=3
            ),
            ServiceDefinition(
                service_name="label_studio",
                description="Label Studio annotation engine",
                health_check_path="/health",
                min_instances=1,
                max_instances=3
            ),
            ServiceDefinition(
                service_name="ai_service",
                description="AI annotation service",
                health_check_path="/health",
                min_instances=1,
                max_instances=5
            ),
            ServiceDefinition(
                service_name="quality_service",
                description="Quality assessment service",
                health_check_path="/health",
                min_instances=1,
                max_instances=3
            ),
        ]
        
        for service in default_services:
            self.services[service.service_name] = service
    
    async def start(self):
        """Start the service registry."""
        if self._is_running:
            return
        
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("ServiceRegistry started")
    
    async def stop(self):
        """Stop the service registry."""
        self._is_running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("ServiceRegistry stopped")
    
    async def _cleanup_loop(self):
        """Background loop for cleaning up stale instances."""
        while self._is_running:
            try:
                await self._cleanup_stale_instances()
                await asyncio.sleep(self.config.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_stale_instances(self):
        """Remove instances that haven't sent heartbeat."""
        current_time = time.time()
        stale_instances = []
        
        for instance_id, instance in self.instances.items():
            if current_time - instance.last_heartbeat > self.config.heartbeat_timeout:
                stale_instances.append(instance_id)
        
        for instance_id in stale_instances:
            await self.deregister(instance_id)
            logger.warning(f"Removed stale instance: {instance_id}")
    
    def register_service(self, service: ServiceDefinition):
        """Register a service definition."""
        self.services[service.service_name] = service
        logger.info(f"Registered service definition: {service.service_name}")
    
    async def register(
        self,
        service_name: str,
        host: str,
        port: int,
        role: ServiceRole = ServiceRole.PRIMARY,
        weight: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None,
        version: str = "1.0.0"
    ) -> ServiceInstance:
        """
        Register a service instance.
        
        Args:
            service_name: Name of the service
            host: Host address
            port: Port number
            role: Service role
            weight: Load balancing weight
            metadata: Additional metadata
            tags: Service tags
            version: Service version
        
        Returns:
            Registered ServiceInstance
        """
        instance_id = str(uuid.uuid4())[:8]
        
        # Get service definition
        service_def = self.services.get(service_name)
        health_check_url = None
        if service_def:
            health_check_url = f"http://{host}:{port}{service_def.health_check_path}"
        
        instance = ServiceInstance(
            instance_id=instance_id,
            service_name=service_name,
            host=host,
            port=port,
            role=role,
            weight=weight,
            metadata=metadata or {},
            tags=tags or set(),
            version=version,
            health_check_url=health_check_url
        )
        
        self.instances[instance_id] = instance
        self.service_instances[service_name].add(instance_id)
        
        logger.info(f"Registered instance: {service_name}/{instance_id} at {host}:{port}")
        return instance
    
    async def deregister(self, instance_id: str) -> bool:
        """Deregister a service instance."""
        instance = self.instances.get(instance_id)
        if not instance:
            return False
        
        # Remove from instances
        del self.instances[instance_id]
        
        # Remove from service instances
        if instance.service_name in self.service_instances:
            self.service_instances[instance.service_name].discard(instance_id)
        
        logger.info(f"Deregistered instance: {instance.service_name}/{instance_id}")
        return True
    
    async def heartbeat(self, instance_id: str) -> bool:
        """Update heartbeat for an instance."""
        instance = self.instances.get(instance_id)
        if not instance:
            return False
        
        instance.last_heartbeat = time.time()
        return True
    
    async def update_status(self, instance_id: str, status: ServiceStatus) -> bool:
        """Update status of an instance."""
        instance = self.instances.get(instance_id)
        if not instance:
            return False
        
        old_status = instance.status
        instance.status = status
        
        logger.info(f"Instance {instance_id} status: {old_status.value} -> {status.value}")
        return True
    
    def get_instance(self, instance_id: str) -> Optional[ServiceInstance]:
        """Get an instance by ID."""
        return self.instances.get(instance_id)
    
    def get_instances(
        self,
        service_name: str,
        status: Optional[ServiceStatus] = None,
        role: Optional[ServiceRole] = None,
        tags: Optional[Set[str]] = None
    ) -> List[ServiceInstance]:
        """
        Get instances for a service with optional filtering.
        
        Args:
            service_name: Service name
            status: Filter by status
            role: Filter by role
            tags: Filter by tags (must have all)
        
        Returns:
            List of matching ServiceInstance
        """
        instance_ids = self.service_instances.get(service_name, set())
        instances = [self.instances[iid] for iid in instance_ids if iid in self.instances]
        
        if status:
            instances = [i for i in instances if i.status == status]
        
        if role:
            instances = [i for i in instances if i.role == role]
        
        if tags:
            instances = [i for i in instances if tags.issubset(i.tags)]
        
        return instances
    
    def get_healthy_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get healthy instances for a service."""
        return self.get_instances(service_name, status=ServiceStatus.HEALTHY)
    
    def get_primary_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """Get the primary instance for a service."""
        instances = self.get_instances(
            service_name, 
            status=ServiceStatus.HEALTHY, 
            role=ServiceRole.PRIMARY
        )
        return instances[0] if instances else None
    
    def get_backup_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """Get a backup instance for a service."""
        # Try secondary first
        instances = self.get_instances(
            service_name,
            status=ServiceStatus.HEALTHY,
            role=ServiceRole.SECONDARY
        )
        if instances:
            return instances[0]
        
        # Then try backup
        instances = self.get_instances(
            service_name,
            status=ServiceStatus.HEALTHY,
            role=ServiceRole.BACKUP
        )
        return instances[0] if instances else None
    
    def list_services(self) -> List[str]:
        """List all registered service names."""
        return list(self.service_instances.keys())
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get status summary for a service."""
        instances = self.get_instances(service_name)
        healthy = [i for i in instances if i.status == ServiceStatus.HEALTHY]
        
        service_def = self.services.get(service_name)
        
        return {
            "service_name": service_name,
            "total_instances": len(instances),
            "healthy_instances": len(healthy),
            "min_instances": service_def.min_instances if service_def else 1,
            "max_instances": service_def.max_instances if service_def else 10,
            "is_healthy": len(healthy) >= (service_def.min_instances if service_def else 1),
            "instances": [
                {
                    "instance_id": i.instance_id,
                    "host": i.host,
                    "port": i.port,
                    "status": i.status.value,
                    "role": i.role.value,
                    "weight": i.weight
                }
                for i in instances
            ]
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        all_instances = list(self.instances.values())
        
        return {
            "total_services": len(self.service_instances),
            "total_instances": len(all_instances),
            "by_status": {
                s.value: len([i for i in all_instances if i.status == s])
                for s in ServiceStatus
            },
            "by_role": {
                r.value: len([i for i in all_instances if i.role == r])
                for r in ServiceRole
            },
            "services": {
                name: len(ids) for name, ids in self.service_instances.items()
            }
        }


# Global service registry instance
service_registry: Optional[ServiceRegistry] = None


async def initialize_service_registry(
    config: Optional[ServiceRegistryConfig] = None
) -> ServiceRegistry:
    """Initialize the global service registry."""
    global service_registry
    
    service_registry = ServiceRegistry(config)
    await service_registry.start()
    
    return service_registry


async def shutdown_service_registry():
    """Shutdown the global service registry."""
    global service_registry
    
    if service_registry:
        await service_registry.stop()
        service_registry = None


def get_service_registry() -> Optional[ServiceRegistry]:
    """Get the global service registry instance."""
    return service_registry
