"""
Container Manager for TCB Full-Stack Deployment.

Provides container lifecycle management, service orchestration,
and health monitoring for the TCB single-container deployment.
"""

import asyncio
import logging
import subprocess
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Status of a container service."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"
    UNKNOWN = "unknown"


class ServiceType(Enum):
    """Types of services in the container."""
    DATABASE = "database"
    CACHE = "cache"
    APPLICATION = "application"
    PROXY = "proxy"
    ANNOTATION = "annotation"


@dataclass
class ServiceInfo:
    """Information about a container service."""
    name: str
    service_type: ServiceType
    port: int
    status: ServiceStatus = ServiceStatus.UNKNOWN
    pid: Optional[int] = None
    uptime_seconds: float = 0.0
    restart_count: int = 0
    last_health_check: Optional[float] = None
    health_check_failures: int = 0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0


@dataclass
class ContainerManagerConfig:
    """Configuration for container manager."""
    health_check_interval: float = 30.0
    max_restart_attempts: int = 3
    restart_delay_seconds: float = 5.0
    startup_timeout_seconds: float = 120.0
    supervisor_socket: str = "/var/run/supervisor.sock"


class ContainerManager:
    """
    Manages services within the TCB full-stack container.
    
    Features:
    - Service lifecycle management
    - Health monitoring
    - Automatic restart on failure
    - Resource monitoring
    - Supervisor integration
    """
    
    def __init__(self, config: Optional[ContainerManagerConfig] = None):
        self.config = config or ContainerManagerConfig()
        self.services: Dict[str, ServiceInfo] = {}
        self.event_history: deque = deque(maxlen=1000)
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Register default services
        self._register_default_services()
        
        logger.info("ContainerManager initialized")
    
    def _register_default_services(self):
        """Register default container services."""
        default_services = [
            ServiceInfo(
                name="postgresql",
                service_type=ServiceType.DATABASE,
                port=5432
            ),
            ServiceInfo(
                name="redis",
                service_type=ServiceType.CACHE,
                port=6379
            ),
            ServiceInfo(
                name="label-studio",
                service_type=ServiceType.ANNOTATION,
                port=8080
            ),
            ServiceInfo(
                name="superinsight-api",
                service_type=ServiceType.APPLICATION,
                port=8000
            ),
            ServiceInfo(
                name="nginx",
                service_type=ServiceType.PROXY,
                port=80
            ),
        ]
        
        for service in default_services:
            self.services[service.name] = service
    
    async def start(self):
        """Start the container manager."""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("ContainerManager started")
    
    async def stop(self):
        """Stop the container manager."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("ContainerManager stopped")
    
    async def _monitor_loop(self):
        """Background monitoring loop."""
        while self._is_running:
            try:
                await self._check_all_services()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in container monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def _check_all_services(self):
        """Check health of all services."""
        for service_name, service in self.services.items():
            try:
                is_healthy = await self._check_service_health(service)
                service.last_health_check = time.time()
                
                if is_healthy:
                    service.status = ServiceStatus.RUNNING
                    service.health_check_failures = 0
                else:
                    service.health_check_failures += 1
                    
                    if service.health_check_failures >= 3:
                        service.status = ServiceStatus.FAILED
                        await self._handle_service_failure(service)
                
            except Exception as e:
                logger.error(f"Error checking service {service_name}: {e}")
                service.status = ServiceStatus.UNKNOWN
    
    async def _check_service_health(self, service: ServiceInfo) -> bool:
        """Check if a service is healthy."""
        try:
            # Check if port is listening
            result = await asyncio.create_subprocess_exec(
                "nc", "-z", "localhost", str(service.port),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await result.wait()
            return result.returncode == 0
        except Exception:
            return False
    
    async def _handle_service_failure(self, service: ServiceInfo):
        """Handle a service failure."""
        if service.restart_count >= self.config.max_restart_attempts:
            logger.error(f"Service {service.name} exceeded max restart attempts")
            self._record_event("service_failure", {
                "service": service.name,
                "reason": "max_restarts_exceeded"
            })
            return
        
        logger.warning(f"Restarting failed service: {service.name}")
        service.status = ServiceStatus.RESTARTING
        
        try:
            await self.restart_service(service.name)
            service.restart_count += 1
            service.health_check_failures = 0
            
            self._record_event("service_restarted", {
                "service": service.name,
                "restart_count": service.restart_count
            })
        except Exception as e:
            logger.error(f"Failed to restart service {service.name}: {e}")
            service.status = ServiceStatus.FAILED
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a service via supervisor."""
        try:
            result = await asyncio.create_subprocess_exec(
                "supervisorctl", "restart", service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                logger.info(f"Service {service_name} restarted successfully")
                return True
            else:
                logger.error(f"Failed to restart {service_name}: {stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"Error restarting service {service_name}: {e}")
            return False
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop a service via supervisor."""
        try:
            result = await asyncio.create_subprocess_exec(
                "supervisorctl", "stop", service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if service_name in self.services:
                self.services[service_name].status = ServiceStatus.STOPPED
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error stopping service {service_name}: {e}")
            return False
    
    async def start_service(self, service_name: str) -> bool:
        """Start a service via supervisor."""
        try:
            result = await asyncio.create_subprocess_exec(
                "supervisorctl", "start", service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if service_name in self.services:
                self.services[service_name].status = ServiceStatus.STARTING
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error starting service {service_name}: {e}")
            return False
    
    async def get_service_status(self, service_name: str) -> Optional[ServiceInfo]:
        """Get status of a specific service."""
        return self.services.get(service_name)
    
    async def get_all_services_status(self) -> Dict[str, ServiceInfo]:
        """Get status of all services."""
        return self.services.copy()
    
    async def get_supervisor_status(self) -> Dict[str, Any]:
        """Get supervisor status for all services."""
        try:
            result = await asyncio.create_subprocess_exec(
                "supervisorctl", "status",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            status = {}
            for line in stdout.decode().strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        state = parts[1]
                        status[name] = {
                            "state": state,
                            "raw": line
                        }
            
            return status
        except Exception as e:
            logger.error(f"Error getting supervisor status: {e}")
            return {}
    
    def _record_event(self, event_type: str, data: Dict[str, Any]):
        """Record an event."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data
        }
        self.event_history.append(event)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get container manager statistics."""
        running = sum(1 for s in self.services.values() if s.status == ServiceStatus.RUNNING)
        failed = sum(1 for s in self.services.values() if s.status == ServiceStatus.FAILED)
        
        return {
            "total_services": len(self.services),
            "running_services": running,
            "failed_services": failed,
            "services": {
                name: {
                    "status": s.status.value,
                    "port": s.port,
                    "restart_count": s.restart_count,
                    "health_check_failures": s.health_check_failures
                }
                for name, s in self.services.items()
            },
            "event_count": len(self.event_history),
            "is_monitoring": self._is_running
        }


# Global container manager instance
container_manager: Optional[ContainerManager] = None


async def initialize_container_manager(
    config: Optional[ContainerManagerConfig] = None
) -> ContainerManager:
    """Initialize the global container manager."""
    global container_manager
    
    container_manager = ContainerManager(config)
    await container_manager.start()
    
    return container_manager


async def shutdown_container_manager():
    """Shutdown the global container manager."""
    global container_manager
    
    if container_manager:
        await container_manager.stop()
        container_manager = None


def get_container_manager() -> Optional[ContainerManager]:
    """Get the global container manager instance."""
    return container_manager
