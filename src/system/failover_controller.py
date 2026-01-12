"""
Failover Controller for High Availability System.

Provides automatic failover management, failover strategies,
and failback capabilities for the high availability infrastructure.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from src.system.service_registry import (
    ServiceRegistry, ServiceInstance, ServiceStatus, ServiceRole,
    get_service_registry
)
from src.system.load_balancer import LoadBalancer, get_load_balancer
from src.system.custom_metrics import record_failover

logger = logging.getLogger(__name__)


class FailoverStrategy(Enum):
    """Failover strategies."""
    IMMEDIATE = "immediate"
    GRACEFUL = "graceful"
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"


class FailoverStatus(Enum):
    """Failover operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class FailoverTrigger(Enum):
    """What triggered the failover."""
    HEALTH_CHECK = "health_check"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    ALERT = "alert"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class FailoverEvent:
    """Represents a failover event."""
    event_id: str
    service_name: str
    from_instance: str
    to_instance: str
    strategy: FailoverStrategy
    trigger: FailoverTrigger
    status: FailoverStatus = FailoverStatus.PENDING
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_seconds: float = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailoverPolicy:
    """Policy for automatic failover."""
    policy_id: str
    service_name: str
    strategy: FailoverStrategy
    enabled: bool = True
    max_failovers_per_hour: int = 3
    cooldown_seconds: float = 300.0
    health_check_failures_threshold: int = 3
    auto_failback: bool = True
    failback_delay_seconds: float = 600.0


@dataclass
class FailoverConfig:
    """Configuration for failover controller."""
    default_strategy: FailoverStrategy = FailoverStrategy.GRACEFUL
    failover_timeout_seconds: float = 60.0
    health_check_interval: float = 10.0
    max_concurrent_failovers: int = 2
    enable_auto_failover: bool = True
    enable_auto_failback: bool = True


class FailoverController:
    """
    Automatic failover controller for high availability.
    
    Features:
    - Multiple failover strategies
    - Automatic failover on health check failures
    - Failback capabilities
    - Failover policies per service
    - Rate limiting and cooldowns
    - Failover history tracking
    """
    
    def __init__(self, config: Optional[FailoverConfig] = None):
        self.config = config or FailoverConfig()
        self.service_registry: Optional[ServiceRegistry] = None
        self.load_balancer: Optional[LoadBalancer] = None
        self.policies: Dict[str, FailoverPolicy] = {}
        self.active_failovers: Dict[str, FailoverEvent] = {}
        self.failover_history: deque = deque(maxlen=1000)
        self.failover_counts: Dict[str, List[float]] = {}  # service -> timestamps
        self.last_failover: Dict[str, float] = {}  # service -> timestamp
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Setup default policies
        self._setup_default_policies()
        
        logger.info("FailoverController initialized")
    
    def _setup_default_policies(self):
        """Setup default failover policies."""
        default_services = [
            "api_server", "database", "redis", 
            "label_studio", "ai_service", "quality_service"
        ]
        
        for service in default_services:
            policy = FailoverPolicy(
                policy_id=f"policy_{service}",
                service_name=service,
                strategy=self.config.default_strategy
            )
            self.policies[service] = policy
    
    async def start(self):
        """Start the failover controller."""
        if self._is_running:
            return
        
        self._is_running = True
        self.service_registry = get_service_registry()
        self.load_balancer = get_load_balancer()
        
        if self.config.enable_auto_failover:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("FailoverController started")
    
    async def stop(self):
        """Stop the failover controller."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("FailoverController stopped")
    
    async def _monitor_loop(self):
        """Background loop for monitoring and auto-failover."""
        while self._is_running:
            try:
                await self._check_services_health()
                await self._check_failback_opportunities()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in failover monitor loop: {e}")
                await asyncio.sleep(5)
    
    async def _check_services_health(self):
        """Check health of all services and trigger failover if needed."""
        if not self.service_registry:
            return
        
        for service_name, policy in self.policies.items():
            if not policy.enabled:
                continue
            
            # Get primary instance
            primary = self.service_registry.get_primary_instance(service_name)
            if not primary:
                continue
            
            # Check if primary is unhealthy
            if primary.status != ServiceStatus.HEALTHY:
                # Check if we should failover
                if self._should_failover(service_name, policy):
                    backup = self.service_registry.get_backup_instance(service_name)
                    if backup:
                        await self.failover(
                            service_name,
                            primary.instance_id,
                            backup.instance_id,
                            trigger=FailoverTrigger.HEALTH_CHECK
                        )
    
    async def _check_failback_opportunities(self):
        """Check if any services can failback to primary."""
        if not self.config.enable_auto_failback:
            return
        
        if not self.service_registry:
            return
        
        for service_name, policy in self.policies.items():
            if not policy.enabled or not policy.auto_failback:
                continue
            
            # Check if we recently failed over
            last_failover_time = self.last_failover.get(service_name, 0)
            if time.time() - last_failover_time < policy.failback_delay_seconds:
                continue
            
            # Check if original primary is healthy again
            instances = self.service_registry.get_instances(service_name)
            
            # Find original primary that's now secondary/backup but healthy
            for instance in instances:
                if instance.role in [ServiceRole.SECONDARY, ServiceRole.BACKUP]:
                    if instance.status == ServiceStatus.HEALTHY:
                        # Check if current primary exists
                        current_primary = self.service_registry.get_primary_instance(service_name)
                        if current_primary and current_primary.instance_id != instance.instance_id:
                            # Consider failback
                            logger.info(f"Failback opportunity detected for {service_name}")
    
    def _should_failover(self, service_name: str, policy: FailoverPolicy) -> bool:
        """Determine if failover should be triggered."""
        current_time = time.time()
        
        # Check cooldown
        last_failover_time = self.last_failover.get(service_name, 0)
        if current_time - last_failover_time < policy.cooldown_seconds:
            return False
        
        # Check rate limit
        if service_name not in self.failover_counts:
            self.failover_counts[service_name] = []
        
        # Clean old timestamps
        hour_ago = current_time - 3600
        self.failover_counts[service_name] = [
            t for t in self.failover_counts[service_name] if t > hour_ago
        ]
        
        if len(self.failover_counts[service_name]) >= policy.max_failovers_per_hour:
            logger.warning(f"Failover rate limit reached for {service_name}")
            return False
        
        # Check concurrent failovers
        if len(self.active_failovers) >= self.config.max_concurrent_failovers:
            return False
        
        return True
    
    async def failover(
        self,
        service_name: str,
        from_instance_id: str,
        to_instance_id: str,
        strategy: Optional[FailoverStrategy] = None,
        trigger: FailoverTrigger = FailoverTrigger.MANUAL
    ) -> FailoverEvent:
        """
        Perform a failover operation.
        
        Args:
            service_name: Name of the service
            from_instance_id: Instance to failover from
            to_instance_id: Instance to failover to
            strategy: Failover strategy (uses policy default if not specified)
            trigger: What triggered the failover
        
        Returns:
            FailoverEvent with operation details
        """
        event_id = str(uuid.uuid4())[:8]
        
        # Get strategy from policy if not specified
        if strategy is None:
            policy = self.policies.get(service_name)
            strategy = policy.strategy if policy else self.config.default_strategy
        
        event = FailoverEvent(
            event_id=event_id,
            service_name=service_name,
            from_instance=from_instance_id,
            to_instance=to_instance_id,
            strategy=strategy,
            trigger=trigger
        )
        
        self.active_failovers[event_id] = event
        
        logger.info(f"Starting failover {event_id}: {service_name} {from_instance_id} -> {to_instance_id}")
        
        try:
            event.status = FailoverStatus.IN_PROGRESS
            
            # Execute failover based on strategy
            if strategy == FailoverStrategy.IMMEDIATE:
                await self._immediate_failover(event)
            elif strategy == FailoverStrategy.GRACEFUL:
                await self._graceful_failover(event)
            elif strategy == FailoverStrategy.ROLLING:
                await self._rolling_failover(event)
            elif strategy == FailoverStrategy.BLUE_GREEN:
                await self._blue_green_failover(event)
            
            event.status = FailoverStatus.COMPLETED
            event.completed_at = time.time()
            event.duration_seconds = event.completed_at - event.started_at
            
            # Update tracking
            self.last_failover[service_name] = time.time()
            if service_name not in self.failover_counts:
                self.failover_counts[service_name] = []
            self.failover_counts[service_name].append(time.time())
            
            # Record metrics
            record_failover(from_instance_id, to_instance_id, True)
            
            logger.info(f"Failover {event_id} completed in {event.duration_seconds:.2f}s")
            
        except Exception as e:
            event.status = FailoverStatus.FAILED
            event.error = str(e)
            event.completed_at = time.time()
            event.duration_seconds = event.completed_at - event.started_at
            
            # Record metrics
            record_failover(from_instance_id, to_instance_id, False)
            
            logger.error(f"Failover {event_id} failed: {e}")
        
        finally:
            # Move to history
            del self.active_failovers[event_id]
            self.failover_history.append(event)
        
        return event
    
    async def _immediate_failover(self, event: FailoverEvent):
        """Immediate failover - switch traffic instantly."""
        logger.info(f"Executing immediate failover for {event.service_name}")
        
        if not self.service_registry:
            raise RuntimeError("Service registry not available")
        
        # Update instance roles
        await self.service_registry.update_status(event.from_instance, ServiceStatus.UNHEALTHY)
        
        from_instance = self.service_registry.get_instance(event.from_instance)
        to_instance = self.service_registry.get_instance(event.to_instance)
        
        if from_instance:
            from_instance.role = ServiceRole.BACKUP
        
        if to_instance:
            to_instance.role = ServiceRole.PRIMARY
            await self.service_registry.update_status(event.to_instance, ServiceStatus.HEALTHY)
        
        # Update load balancer
        if self.load_balancer and to_instance:
            await self.load_balancer.add_healthy_instance(to_instance)
    
    async def _graceful_failover(self, event: FailoverEvent):
        """Graceful failover - drain connections before switching."""
        logger.info(f"Executing graceful failover for {event.service_name}")
        
        if not self.service_registry:
            raise RuntimeError("Service registry not available")
        
        # Mark old instance as draining
        await self.service_registry.update_status(event.from_instance, ServiceStatus.DRAINING)
        
        # Wait for connections to drain (simplified)
        await asyncio.sleep(5)
        
        # Complete the failover
        await self._immediate_failover(event)
    
    async def _rolling_failover(self, event: FailoverEvent):
        """Rolling failover - gradual traffic shift."""
        logger.info(f"Executing rolling failover for {event.service_name}")
        
        # Gradually shift traffic (simplified)
        for percentage in [25, 50, 75, 100]:
            logger.info(f"Rolling failover: {percentage}% traffic to new instance")
            await asyncio.sleep(2)
        
        await self._immediate_failover(event)
    
    async def _blue_green_failover(self, event: FailoverEvent):
        """Blue-green failover - switch between environments."""
        logger.info(f"Executing blue-green failover for {event.service_name}")
        
        # Verify new instance is ready
        if self.service_registry:
            to_instance = self.service_registry.get_instance(event.to_instance)
            if not to_instance or to_instance.status != ServiceStatus.HEALTHY:
                raise RuntimeError("Target instance not healthy")
        
        # Switch traffic
        await self._immediate_failover(event)
    
    async def failback(
        self,
        service_name: str,
        to_instance_id: str
    ) -> FailoverEvent:
        """
        Failback to original primary.
        
        Args:
            service_name: Name of the service
            to_instance_id: Instance to failback to
        
        Returns:
            FailoverEvent with operation details
        """
        if not self.service_registry:
            raise RuntimeError("Service registry not available")
        
        # Get current primary
        current_primary = self.service_registry.get_primary_instance(service_name)
        if not current_primary:
            raise RuntimeError(f"No current primary for {service_name}")
        
        return await self.failover(
            service_name,
            current_primary.instance_id,
            to_instance_id,
            trigger=FailoverTrigger.MANUAL
        )
    
    def add_policy(self, policy: FailoverPolicy):
        """Add or update a failover policy."""
        self.policies[policy.service_name] = policy
        logger.info(f"Added failover policy for {policy.service_name}")
    
    def remove_policy(self, service_name: str) -> bool:
        """Remove a failover policy."""
        if service_name in self.policies:
            del self.policies[service_name]
            logger.info(f"Removed failover policy for {service_name}")
            return True
        return False
    
    def enable_policy(self, service_name: str) -> bool:
        """Enable a failover policy."""
        if service_name in self.policies:
            self.policies[service_name].enabled = True
            return True
        return False
    
    def disable_policy(self, service_name: str) -> bool:
        """Disable a failover policy."""
        if service_name in self.policies:
            self.policies[service_name].enabled = False
            return True
        return False
    
    def get_failover_history(
        self,
        service_name: Optional[str] = None,
        limit: int = 50
    ) -> List[FailoverEvent]:
        """Get failover history."""
        history = list(self.failover_history)
        
        if service_name:
            history = [e for e in history if e.service_name == service_name]
        
        return history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get failover statistics."""
        history = list(self.failover_history)
        successful = [e for e in history if e.status == FailoverStatus.COMPLETED]
        failed = [e for e in history if e.status == FailoverStatus.FAILED]
        
        return {
            "total_failovers": len(history),
            "successful_failovers": len(successful),
            "failed_failovers": len(failed),
            "success_rate": len(successful) / len(history) if history else 0,
            "active_failovers": len(self.active_failovers),
            "policies": len(self.policies),
            "enabled_policies": len([p for p in self.policies.values() if p.enabled]),
            "by_trigger": {
                t.value: len([e for e in history if e.trigger == t])
                for t in FailoverTrigger
            },
            "by_strategy": {
                s.value: len([e for e in history if e.strategy == s])
                for s in FailoverStrategy
            },
            "avg_duration_seconds": (
                sum(e.duration_seconds for e in successful) / len(successful)
                if successful else 0
            )
        }


# Global failover controller instance
failover_controller: Optional[FailoverController] = None


async def initialize_failover_controller(
    config: Optional[FailoverConfig] = None
) -> FailoverController:
    """Initialize the global failover controller."""
    global failover_controller
    
    failover_controller = FailoverController(config)
    await failover_controller.start()
    
    return failover_controller


async def shutdown_failover_controller():
    """Shutdown the global failover controller."""
    global failover_controller
    
    if failover_controller:
        await failover_controller.stop()
        failover_controller = None


def get_failover_controller() -> Optional[FailoverController]:
    """Get the global failover controller instance."""
    return failover_controller
