"""
Failover manager implementation for high availability.

This module provides failover capabilities including:
- Automatic failover detection and execution
- Multiple failover strategies
- Graceful service migration
- Rollback capabilities
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

from .models import (
    ServiceInstance, FailoverStrategy, FailoverConfig,
    FailoverEvent, ServiceStatus
)
from .service_discovery import ServiceDiscovery, ServiceRegistry
from .health_checker import HealthChecker
from .load_balancer import LoadBalancer


logger = logging.getLogger(__name__)


class FailoverState(Enum):
    """Failover state enumeration."""
    IDLE = "idle"
    DETECTING = "detecting"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"


class FailoverManager:
    """Failover manager for handling service failures and recovery."""
    
    def __init__(self, service_discovery: ServiceDiscovery,
                 health_checker: HealthChecker,
                 load_balancer: LoadBalancer,
                 config: FailoverConfig):
        """
        Initialize failover manager.
        
        Args:
            service_discovery: Service discovery instance
            health_checker: Health checker instance
            load_balancer: Load balancer instance
            config: Failover configuration
        """
        self.discovery = service_discovery
        self.health_checker = health_checker
        self.load_balancer = load_balancer
        self.config = config
        
        self.state = FailoverState.IDLE
        self.active_failovers: Dict[str, FailoverEvent] = {}
        self.failover_history: List[FailoverEvent] = []
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[FailoverEvent], None]] = []
    
    async def start(self) -> None:
        """Start failover monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("Failover manager started")
    
    async def stop(self) -> None:
        """Stop failover monitoring."""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Failover manager stopped")
    
    def add_failover_callback(self, callback: Callable[[FailoverEvent], None]) -> None:
        """
        Add callback for failover events.
        
        Args:
            callback: Callback function to call on failover events
        """
        self._callbacks.append(callback)
    
    def remove_failover_callback(self, callback: Callable[[FailoverEvent], None]) -> None:
        """
        Remove failover callback.
        
        Args:
            callback: Callback function to remove
        """
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass
    
    async def trigger_failover(self, service_name: str, failed_instance_id: str,
                             reason: str = "Manual trigger") -> Optional[FailoverEvent]:
        """
        Manually trigger failover for a service instance.
        
        Args:
            service_name: Name of the service
            failed_instance_id: ID of the failed instance
            reason: Reason for failover
            
        Returns:
            Failover event or None if failover not possible
        """
        # Check if failover already in progress
        failover_key = f"{service_name}:{failed_instance_id}"
        if failover_key in self.active_failovers:
            logger.warning(f"Failover already in progress for {failover_key}")
            return self.active_failovers[failover_key]
        
        # Find target instance
        target_instance = await self._find_failover_target(service_name, failed_instance_id)
        if not target_instance:
            logger.error(f"No suitable failover target found for {service_name}")
            return None
        
        # Create failover event
        failover_event = FailoverEvent(
            source_instance=failed_instance_id,
            target_instance=target_instance.id,
            reason=reason,
            strategy=self.config.strategy
        )
        
        # Execute failover
        success = await self._execute_failover(service_name, failover_event)
        
        # Update event
        failover_event.completed_at = datetime.utcnow()
        failover_event.success = success
        
        # Store in history
        self.failover_history.append(failover_event)
        
        # Remove from active failovers
        if failover_key in self.active_failovers:
            del self.active_failovers[failover_key]
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(failover_event)
            except Exception as e:
                logger.error(f"Error in failover callback: {e}")
        
        return failover_event
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop for detecting failures."""
        while self._running:
            try:
                await self._check_for_failures()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in failover monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def _check_for_failures(self) -> None:
        """Check for service failures that require failover."""
        # Get all health summaries
        health_summaries = self.health_checker.get_all_health_summaries()
        
        for service_key, summary in health_summaries.items():
            try:
                parts = service_key.split(':', 1)
                if len(parts) != 2:
                    continue
                
                service_name, service_id = parts
                
                # Check if instance needs failover
                if await self._should_trigger_failover(service_name, service_id, summary):
                    await self.trigger_failover(
                        service_name, service_id,
                        f"Automatic failover: {summary['latest_status']['message']}"
                    )
            
            except Exception as e:
                logger.error(f"Error checking failure for {service_key}: {e}")
    
    async def _should_trigger_failover(self, service_name: str, service_id: str,
                                     health_summary: Dict[str, Any]) -> bool:
        """
        Determine if failover should be triggered for a service instance.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
            health_summary: Health summary from health checker
            
        Returns:
            True if failover should be triggered
        """
        # Check if already in failover
        failover_key = f"{service_name}:{service_id}"
        if failover_key in self.active_failovers:
            return False
        
        # Check failure threshold
        failure_count = health_summary.get('failure_count', 0)
        if failure_count < self.config.circuit_breaker_threshold:
            return False
        
        # Check recent health rate
        recent_health_rate = health_summary.get('recent_health_rate', 1.0)
        if recent_health_rate > 0.2:  # Still some success
            return False
        
        # Check circuit breaker
        if self._is_circuit_breaker_open(service_name, service_id):
            return False
        
        return True
    
    def _is_circuit_breaker_open(self, service_name: str, service_id: str) -> bool:
        """Check if circuit breaker is open for a service."""
        cb_key = f"{service_name}:{service_id}"
        
        if cb_key not in self.circuit_breakers:
            return False
        
        cb_info = self.circuit_breakers[cb_key]
        opened_at = cb_info.get('opened_at')
        
        if not opened_at:
            return False
        
        # Check if timeout has passed
        timeout_passed = (
            datetime.utcnow() - opened_at
        ).total_seconds() >= self.config.circuit_breaker_timeout
        
        if timeout_passed:
            # Reset circuit breaker
            del self.circuit_breakers[cb_key]
            return False
        
        return True
    
    def _open_circuit_breaker(self, service_name: str, service_id: str) -> None:
        """Open circuit breaker for a service."""
        cb_key = f"{service_name}:{service_id}"
        self.circuit_breakers[cb_key] = {
            'opened_at': datetime.utcnow(),
            'failure_count': 0
        }
        
        logger.info(f"Opened circuit breaker for {cb_key}")
    
    async def _find_failover_target(self, service_name: str,
                                  failed_instance_id: str) -> Optional[ServiceInstance]:
        """
        Find a suitable failover target instance.
        
        Args:
            service_name: Name of the service
            failed_instance_id: ID of the failed instance
            
        Returns:
            Target instance or None if none available
        """
        # Get all healthy instances
        instances = await self.discovery.discover_services(service_name, healthy_only=True)
        
        # Filter out the failed instance
        available_instances = [i for i in instances if i.id != failed_instance_id]
        
        if not available_instances:
            return None
        
        # Select best instance based on load
        return min(available_instances, key=lambda i: i.load_factor)
    
    async def _execute_failover(self, service_name: str,
                              failover_event: FailoverEvent) -> bool:
        """
        Execute the actual failover process.
        
        Args:
            service_name: Name of the service
            failover_event: Failover event details
            
        Returns:
            True if failover successful
        """
        try:
            self.state = FailoverState.EXECUTING
            
            # Add to active failovers
            failover_key = f"{service_name}:{failover_event.source_instance}"
            self.active_failovers[failover_key] = failover_event
            
            strategy = failover_event.strategy
            
            if strategy == FailoverStrategy.IMMEDIATE:
                return await self._immediate_failover(service_name, failover_event)
            
            elif strategy == FailoverStrategy.GRACEFUL:
                return await self._graceful_failover(service_name, failover_event)
            
            elif strategy == FailoverStrategy.CIRCUIT_BREAKER:
                return await self._circuit_breaker_failover(service_name, failover_event)
            
            else:
                logger.error(f"Unknown failover strategy: {strategy}")
                return False
        
        except Exception as e:
            logger.error(f"Failover execution failed: {e}")
            failover_event.error_message = str(e)
            return False
        
        finally:
            self.state = FailoverState.IDLE
    
    async def _immediate_failover(self, service_name: str,
                                failover_event: FailoverEvent) -> bool:
        """Execute immediate failover."""
        try:
            # Mark source instance as unhealthy
            await self.discovery.registry.update_service_status(
                service_name, failover_event.source_instance, ServiceStatus.UNHEALTHY
            )
            
            # Ensure target instance is healthy
            target_instance = await self.discovery.registry.get_service(
                service_name, failover_event.target_instance
            )
            
            if not target_instance or not target_instance.is_healthy:
                return False
            
            logger.info(
                f"Immediate failover completed: {failover_event.source_instance} -> "
                f"{failover_event.target_instance}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Immediate failover failed: {e}")
            return False
    
    async def _graceful_failover(self, service_name: str,
                               failover_event: FailoverEvent) -> bool:
        """Execute graceful failover with connection draining."""
        try:
            # Mark source instance as degraded first
            await self.discovery.registry.update_service_status(
                service_name, failover_event.source_instance, ServiceStatus.DEGRADED
            )
            
            # Wait for connections to drain
            max_wait = self.config.timeout
            wait_interval = 5
            waited = 0
            
            while waited < max_wait:
                # Check connection count
                connection_stats = self.load_balancer.get_connection_stats()
                current_connections = connection_stats.get(failover_event.source_instance, 0)
                
                if current_connections == 0:
                    break
                
                logger.info(
                    f"Waiting for connections to drain: {current_connections} remaining"
                )
                
                await asyncio.sleep(wait_interval)
                waited += wait_interval
            
            # Mark as unhealthy
            await self.discovery.registry.update_service_status(
                service_name, failover_event.source_instance, ServiceStatus.UNHEALTHY
            )
            
            logger.info(
                f"Graceful failover completed: {failover_event.source_instance} -> "
                f"{failover_event.target_instance}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Graceful failover failed: {e}")
            return False
    
    async def _circuit_breaker_failover(self, service_name: str,
                                      failover_event: FailoverEvent) -> bool:
        """Execute circuit breaker failover."""
        try:
            # Open circuit breaker
            self._open_circuit_breaker(service_name, failover_event.source_instance)
            
            # Mark instance as unhealthy
            await self.discovery.registry.update_service_status(
                service_name, failover_event.source_instance, ServiceStatus.UNHEALTHY
            )
            
            logger.info(
                f"Circuit breaker failover completed: {failover_event.source_instance} -> "
                f"{failover_event.target_instance}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Circuit breaker failover failed: {e}")
            return False
    
    async def rollback_failover(self, failover_event_id: str) -> bool:
        """
        Rollback a previous failover.
        
        Args:
            failover_event_id: ID of the failover event to rollback
            
        Returns:
            True if rollback successful
        """
        try:
            # Find failover event
            failover_event = None
            for event in self.failover_history:
                if event.id == failover_event_id:
                    failover_event = event
                    break
            
            if not failover_event:
                logger.error(f"Failover event not found: {failover_event_id}")
                return False
            
            if not failover_event.success:
                logger.error(f"Cannot rollback failed failover: {failover_event_id}")
                return False
            
            self.state = FailoverState.ROLLING_BACK
            
            # Extract service name from history or metadata
            service_name = failover_event.metadata.get('service_name')
            if not service_name:
                logger.error(f"Service name not found in failover event: {failover_event_id}")
                return False
            
            # Restore original instance
            await self.discovery.registry.update_service_status(
                service_name, failover_event.source_instance, ServiceStatus.HEALTHY
            )
            
            logger.info(f"Rollback completed for failover {failover_event_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failover rollback failed: {e}")
            return False
        
        finally:
            self.state = FailoverState.IDLE
    
    def get_failover_statistics(self) -> Dict[str, Any]:
        """Get failover statistics."""
        total_failovers = len(self.failover_history)
        successful_failovers = sum(1 for f in self.failover_history if f.success)
        
        if total_failovers == 0:
            return {
                "total_failovers": 0,
                "success_rate": 0.0,
                "avg_failover_time": 0.0,
                "active_failovers": len(self.active_failovers),
                "circuit_breakers_open": len(self.circuit_breakers)
            }
        
        # Calculate average failover time
        completed_failovers = [f for f in self.failover_history if f.duration is not None]
        avg_time = 0.0
        if completed_failovers:
            avg_time = sum(f.duration for f in completed_failovers) / len(completed_failovers)
        
        return {
            "total_failovers": total_failovers,
            "successful_failovers": successful_failovers,
            "success_rate": successful_failovers / total_failovers,
            "avg_failover_time": avg_time,
            "active_failovers": len(self.active_failovers),
            "circuit_breakers_open": len(self.circuit_breakers),
            "recent_failovers": [
                {
                    "id": f.id,
                    "source": f.source_instance,
                    "target": f.target_instance,
                    "reason": f.reason,
                    "success": f.success,
                    "duration": f.duration,
                    "started_at": f.started_at.isoformat()
                }
                for f in self.failover_history[-10:]  # Last 10 failovers
            ]
        }