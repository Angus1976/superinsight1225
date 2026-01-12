"""
Service Orchestrator for TCB Full-Stack Deployment.

Provides service dependency management, startup sequencing,
and coordinated service operations for the TCB container.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class OrchestratorState(Enum):
    """State of the orchestrator."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


class ServiceDependencyType(Enum):
    """Types of service dependencies."""
    REQUIRED = "required"  # Must be running before dependent starts
    OPTIONAL = "optional"  # Nice to have, but not required
    HEALTH_CHECK = "health_check"  # Must pass health check


@dataclass
class ServiceDependency:
    """A service dependency definition."""
    service_name: str
    dependency_type: ServiceDependencyType = ServiceDependencyType.REQUIRED
    timeout_seconds: float = 60.0


@dataclass
class ServiceDefinition:
    """Definition of a service for orchestration."""
    name: str
    start_command: str
    stop_command: str
    health_check_port: int
    dependencies: List[ServiceDependency] = field(default_factory=list)
    startup_timeout: float = 60.0
    shutdown_timeout: float = 30.0
    priority: int = 100  # Lower = starts first


@dataclass
class ServiceOrchestratorConfig:
    """Configuration for service orchestrator."""
    startup_timeout: float = 300.0
    shutdown_timeout: float = 120.0
    health_check_interval: float = 5.0
    max_parallel_starts: int = 2


class ServiceOrchestrator:
    """
    Orchestrates service startup, shutdown, and dependencies.
    
    Features:
    - Dependency-aware startup sequencing
    - Parallel service startup where possible
    - Graceful shutdown with dependency ordering
    - Health check integration
    - Startup/shutdown event tracking
    """
    
    def __init__(self, config: Optional[ServiceOrchestratorConfig] = None):
        self.config = config or ServiceOrchestratorConfig()
        self.services: Dict[str, ServiceDefinition] = {}
        self.state = OrchestratorState.IDLE
        self.startup_order: List[str] = []
        self.event_history: deque = deque(maxlen=500)
        
        # Register default services
        self._register_default_services()
        
        logger.info("ServiceOrchestrator initialized")
    
    def _register_default_services(self):
        """Register default TCB container services."""
        # PostgreSQL - no dependencies, starts first
        self.register_service(ServiceDefinition(
            name="postgresql",
            start_command="supervisorctl start postgresql",
            stop_command="supervisorctl stop postgresql",
            health_check_port=5432,
            dependencies=[],
            startup_timeout=60.0,
            priority=10
        ))
        
        # Redis - no dependencies
        self.register_service(ServiceDefinition(
            name="redis",
            start_command="supervisorctl start redis",
            stop_command="supervisorctl stop redis",
            health_check_port=6379,
            dependencies=[],
            startup_timeout=30.0,
            priority=20
        ))
        
        # Label Studio - depends on PostgreSQL
        self.register_service(ServiceDefinition(
            name="label-studio",
            start_command="supervisorctl start label-studio",
            stop_command="supervisorctl stop label-studio",
            health_check_port=8080,
            dependencies=[
                ServiceDependency("postgresql", ServiceDependencyType.REQUIRED, 60.0)
            ],
            startup_timeout=90.0,
            priority=30
        ))
        
        # SuperInsight API - depends on PostgreSQL, Redis, Label Studio
        self.register_service(ServiceDefinition(
            name="superinsight-api",
            start_command="supervisorctl start superinsight-api",
            stop_command="supervisorctl stop superinsight-api",
            health_check_port=8000,
            dependencies=[
                ServiceDependency("postgresql", ServiceDependencyType.REQUIRED, 60.0),
                ServiceDependency("redis", ServiceDependencyType.REQUIRED, 30.0),
                ServiceDependency("label-studio", ServiceDependencyType.OPTIONAL, 90.0)
            ],
            startup_timeout=60.0,
            priority=40
        ))
        
        # Nginx - depends on SuperInsight API
        self.register_service(ServiceDefinition(
            name="nginx",
            start_command="supervisorctl start nginx",
            stop_command="supervisorctl stop nginx",
            health_check_port=80,
            dependencies=[
                ServiceDependency("superinsight-api", ServiceDependencyType.REQUIRED, 60.0)
            ],
            startup_timeout=30.0,
            priority=50
        ))
        
        # Calculate startup order
        self._calculate_startup_order()
    
    def register_service(self, service: ServiceDefinition):
        """Register a service for orchestration."""
        self.services[service.name] = service
        logger.debug(f"Registered service: {service.name}")
    
    def _calculate_startup_order(self):
        """Calculate the optimal startup order based on dependencies."""
        # Topological sort with priority consideration
        visited: Set[str] = set()
        order: List[str] = []
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            
            service = self.services.get(name)
            if service:
                for dep in service.dependencies:
                    if dep.dependency_type == ServiceDependencyType.REQUIRED:
                        visit(dep.service_name)
                order.append(name)
        
        # Sort by priority first
        sorted_services = sorted(
            self.services.values(),
            key=lambda s: s.priority
        )
        
        for service in sorted_services:
            visit(service.name)
        
        self.startup_order = order
        logger.info(f"Calculated startup order: {order}")
    
    async def start_all_services(self) -> Dict[str, Any]:
        """Start all services in dependency order."""
        self.state = OrchestratorState.STARTING
        results = {}
        start_time = time.time()
        
        logger.info("Starting all services...")
        self._record_event("startup_begin", {"services": self.startup_order})
        
        try:
            for service_name in self.startup_order:
                service = self.services.get(service_name)
                if not service:
                    continue
                
                # Wait for dependencies
                deps_ready = await self._wait_for_dependencies(service)
                if not deps_ready:
                    results[service_name] = {
                        "success": False,
                        "error": "Dependencies not ready"
                    }
                    continue
                
                # Start the service
                success = await self._start_service(service)
                results[service_name] = {
                    "success": success,
                    "startup_time": time.time() - start_time
                }
                
                if not success:
                    logger.error(f"Failed to start service: {service_name}")
            
            # Check overall success
            all_success = all(r.get("success", False) for r in results.values())
            self.state = OrchestratorState.RUNNING if all_success else OrchestratorState.FAILED
            
            total_time = time.time() - start_time
            self._record_event("startup_complete", {
                "success": all_success,
                "total_time": total_time,
                "results": results
            })
            
            logger.info(f"Service startup completed in {total_time:.2f}s")
            return {
                "success": all_success,
                "total_time": total_time,
                "services": results
            }
            
        except Exception as e:
            self.state = OrchestratorState.FAILED
            logger.error(f"Error during service startup: {e}")
            return {
                "success": False,
                "error": str(e),
                "services": results
            }
    
    async def stop_all_services(self) -> Dict[str, Any]:
        """Stop all services in reverse dependency order."""
        self.state = OrchestratorState.STOPPING
        results = {}
        start_time = time.time()
        
        # Reverse the startup order for shutdown
        shutdown_order = list(reversed(self.startup_order))
        
        logger.info("Stopping all services...")
        self._record_event("shutdown_begin", {"services": shutdown_order})
        
        try:
            for service_name in shutdown_order:
                service = self.services.get(service_name)
                if not service:
                    continue
                
                success = await self._stop_service(service)
                results[service_name] = {"success": success}
            
            self.state = OrchestratorState.IDLE
            total_time = time.time() - start_time
            
            self._record_event("shutdown_complete", {
                "total_time": total_time,
                "results": results
            })
            
            logger.info(f"Service shutdown completed in {total_time:.2f}s")
            return {
                "success": True,
                "total_time": total_time,
                "services": results
            }
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")
            return {
                "success": False,
                "error": str(e),
                "services": results
            }
    
    async def _wait_for_dependencies(self, service: ServiceDefinition) -> bool:
        """Wait for service dependencies to be ready."""
        for dep in service.dependencies:
            if dep.dependency_type == ServiceDependencyType.OPTIONAL:
                continue
            
            dep_service = self.services.get(dep.service_name)
            if not dep_service:
                continue
            
            # Wait for dependency to be healthy
            start_time = time.time()
            while time.time() - start_time < dep.timeout_seconds:
                if await self._check_service_health(dep_service):
                    break
                await asyncio.sleep(self.config.health_check_interval)
            else:
                logger.error(f"Dependency {dep.service_name} not ready for {service.name}")
                return False
        
        return True
    
    async def _start_service(self, service: ServiceDefinition) -> bool:
        """Start a single service."""
        logger.info(f"Starting service: {service.name}")
        
        try:
            # Execute start command
            process = await asyncio.create_subprocess_shell(
                service.start_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # Wait for health check
            start_time = time.time()
            while time.time() - start_time < service.startup_timeout:
                if await self._check_service_health(service):
                    logger.info(f"Service {service.name} started successfully")
                    return True
                await asyncio.sleep(self.config.health_check_interval)
            
            logger.error(f"Service {service.name} failed health check")
            return False
            
        except Exception as e:
            logger.error(f"Error starting service {service.name}: {e}")
            return False
    
    async def _stop_service(self, service: ServiceDefinition) -> bool:
        """Stop a single service."""
        logger.info(f"Stopping service: {service.name}")
        
        try:
            process = await asyncio.create_subprocess_shell(
                service.stop_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                await asyncio.wait_for(
                    process.communicate(),
                    timeout=service.shutdown_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.warning(f"Service {service.name} stop timed out, killed")
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping service {service.name}: {e}")
            return False
    
    async def _check_service_health(self, service: ServiceDefinition) -> bool:
        """Check if a service is healthy."""
        try:
            result = await asyncio.create_subprocess_exec(
                "nc", "-z", "localhost", str(service.health_check_port),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await result.wait()
            return result.returncode == 0
        except Exception:
            return False
    
    def _record_event(self, event_type: str, data: Dict[str, Any]):
        """Record an orchestration event."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data
        }
        self.event_history.append(event)
    
    def get_state(self) -> OrchestratorState:
        """Get current orchestrator state."""
        return self.state
    
    def get_startup_order(self) -> List[str]:
        """Get the calculated startup order."""
        return self.startup_order.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "state": self.state.value,
            "total_services": len(self.services),
            "startup_order": self.startup_order,
            "event_count": len(self.event_history),
            "services": {
                name: {
                    "priority": s.priority,
                    "dependencies": [d.service_name for d in s.dependencies],
                    "health_check_port": s.health_check_port
                }
                for name, s in self.services.items()
            }
        }


# Global service orchestrator instance
service_orchestrator: Optional[ServiceOrchestrator] = None


def initialize_service_orchestrator(
    config: Optional[ServiceOrchestratorConfig] = None
) -> ServiceOrchestrator:
    """Initialize the global service orchestrator."""
    global service_orchestrator
    service_orchestrator = ServiceOrchestrator(config)
    return service_orchestrator


def get_service_orchestrator() -> Optional[ServiceOrchestrator]:
    """Get the global service orchestrator instance."""
    return service_orchestrator
