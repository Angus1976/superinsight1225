"""
Health checker implementation for monitoring service health.

This module provides health checking capabilities including:
- HTTP health checks
- Custom health check protocols
- Health status tracking
- Automatic recovery detection
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import aiohttp

from .models import (
    ServiceInstance, ServiceStatus, HealthCheckConfig,
    ServiceMetrics
)
from .service_discovery import ServiceRegistry


logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status information."""
    
    def __init__(self, healthy: bool, response_time: float = 0.0,
                 status_code: Optional[int] = None, message: str = ""):
        self.healthy = healthy
        self.response_time = response_time
        self.status_code = status_code
        self.message = message
        self.timestamp = datetime.utcnow()


class HealthChecker:
    """Health checker for monitoring service instances."""
    
    def __init__(self, registry: ServiceRegistry, config: HealthCheckConfig):
        """
        Initialize health checker.
        
        Args:
            registry: Service registry instance
            config: Health check configuration
        """
        self.registry = registry
        self.config = config
        self.health_history: Dict[str, List[HealthStatus]] = {}
        self.failure_counts: Dict[str, int] = {}
        self.success_counts: Dict[str, int] = {}
        self._running = False
        self._check_tasks: Dict[str, asyncio.Task] = {}
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def start(self) -> None:
        """Start health checking."""
        if self._running:
            return
        
        self._running = True
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        
        logger.info("Health checker started")
    
    async def stop(self) -> None:
        """Stop health checking."""
        self._running = False
        
        # Cancel all check tasks
        for task in self._check_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self._check_tasks:
            await asyncio.gather(*self._check_tasks.values(), return_exceptions=True)
        
        self._check_tasks.clear()
        
        # Close HTTP session
        if self._session:
            await self._session.close()
            self._session = None
        
        logger.info("Health checker stopped")
    
    async def add_service(self, service: ServiceInstance) -> None:
        """
        Add a service for health checking.
        
        Args:
            service: Service instance to monitor
        """
        if not self._running:
            await self.start()
        
        service_key = f"{service.name}:{service.id}"
        
        if service_key in self._check_tasks:
            # Cancel existing task
            self._check_tasks[service_key].cancel()
        
        # Start new health check task
        self._check_tasks[service_key] = asyncio.create_task(
            self._health_check_loop(service)
        )
        
        logger.info(f"Added health checking for service {service_key}")
    
    async def remove_service(self, service_name: str, service_id: str) -> None:
        """
        Remove a service from health checking.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
        """
        service_key = f"{service_name}:{service_id}"
        
        if service_key in self._check_tasks:
            self._check_tasks[service_key].cancel()
            del self._check_tasks[service_key]
        
        # Clean up history
        if service_key in self.health_history:
            del self.health_history[service_key]
        
        if service_key in self.failure_counts:
            del self.failure_counts[service_key]
        
        if service_key in self.success_counts:
            del self.success_counts[service_key]
        
        logger.info(f"Removed health checking for service {service_key}")
    
    async def check_service_health(self, service: ServiceInstance) -> HealthStatus:
        """
        Perform a single health check on a service.
        
        Args:
            service: Service instance to check
            
        Returns:
            Health status result
        """
        if not self._session:
            return HealthStatus(False, message="Health checker not started")
        
        try:
            start_time = time.time()
            
            # Construct health check URL
            health_url = service.health_check_url
            if not health_url:
                health_url = f"{service.endpoint}{self.config.path}"
            
            # Perform health check request
            async with self._session.request(
                self.config.method,
                health_url
            ) as response:
                response_time = time.time() - start_time
                
                # Check response status
                if response.status == self.config.expected_status:
                    # Check response body if specified
                    if self.config.expected_body:
                        body = await response.text()
                        if self.config.expected_body not in body:
                            return HealthStatus(
                                False, response_time, response.status,
                                f"Expected body content not found: {self.config.expected_body}"
                            )
                    
                    return HealthStatus(True, response_time, response.status, "OK")
                else:
                    return HealthStatus(
                        False, response_time, response.status,
                        f"Unexpected status code: {response.status}"
                    )
        
        except asyncio.TimeoutError:
            return HealthStatus(False, self.config.timeout, message="Health check timeout")
        
        except Exception as e:
            return HealthStatus(False, message=f"Health check error: {str(e)}")
    
    async def _health_check_loop(self, service: ServiceInstance) -> None:
        """Health check loop for a specific service."""
        service_key = f"{service.name}:{service.id}"
        
        try:
            while self._running:
                # Perform health check
                health_status = await self.check_service_health(service)
                
                # Record health status
                self._record_health_status(service_key, health_status)
                
                # Determine service status based on health check results
                new_status = self._determine_service_status(service_key, health_status)
                
                # Update service status if changed
                current_service = await self.registry.get_service(service.name, service.id)
                if current_service and current_service.status != new_status:
                    await self.registry.update_service_status(
                        service.name, service.id, new_status
                    )
                    
                    logger.info(
                        f"Service {service_key} status changed: "
                        f"{current_service.status.value} -> {new_status.value}"
                    )
                
                # Wait for next check
                await asyncio.sleep(self.config.interval)
        
        except asyncio.CancelledError:
            logger.debug(f"Health check cancelled for service {service_key}")
        
        except Exception as e:
            logger.error(f"Health check loop error for service {service_key}: {e}")
    
    def _record_health_status(self, service_key: str, health_status: HealthStatus) -> None:
        """Record health status in history."""
        if service_key not in self.health_history:
            self.health_history[service_key] = []
        
        history = self.health_history[service_key]
        history.append(health_status)
        
        # Keep only recent history (last 100 checks)
        if len(history) > 100:
            history.pop(0)
        
        # Update counters
        if health_status.healthy:
            self.success_counts[service_key] = self.success_counts.get(service_key, 0) + 1
            self.failure_counts[service_key] = 0  # Reset failure count on success
        else:
            self.failure_counts[service_key] = self.failure_counts.get(service_key, 0) + 1
    
    def _determine_service_status(self, service_key: str, 
                                health_status: HealthStatus) -> ServiceStatus:
        """Determine service status based on health check results."""
        failure_count = self.failure_counts.get(service_key, 0)
        success_count = self.success_counts.get(service_key, 0)
        
        if health_status.healthy:
            # Service is healthy if we have enough successful checks
            if success_count >= self.config.success_threshold:
                return ServiceStatus.HEALTHY
            else:
                return ServiceStatus.DEGRADED
        else:
            # Service is unhealthy if we have too many failures
            if failure_count >= self.config.failure_threshold:
                return ServiceStatus.UNHEALTHY
            else:
                return ServiceStatus.DEGRADED
    
    def get_health_summary(self, service_name: str, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Get health summary for a service.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
            
        Returns:
            Health summary or None if not found
        """
        service_key = f"{service_name}:{service_id}"
        
        if service_key not in self.health_history:
            return None
        
        history = self.health_history[service_key]
        if not history:
            return None
        
        recent_checks = history[-10:]  # Last 10 checks
        healthy_count = sum(1 for h in recent_checks if h.healthy)
        
        latest = history[-1]
        response_times = [h.response_time for h in recent_checks if h.response_time > 0]
        
        return {
            "service_key": service_key,
            "latest_status": {
                "healthy": latest.healthy,
                "response_time": latest.response_time,
                "status_code": latest.status_code,
                "message": latest.message,
                "timestamp": latest.timestamp.isoformat()
            },
            "recent_health_rate": healthy_count / len(recent_checks),
            "total_checks": len(history),
            "failure_count": self.failure_counts.get(service_key, 0),
            "success_count": self.success_counts.get(service_key, 0),
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0.0,
            "min_response_time": min(response_times) if response_times else 0.0,
            "max_response_time": max(response_times) if response_times else 0.0
        }
    
    def get_all_health_summaries(self) -> Dict[str, Dict[str, Any]]:
        """Get health summaries for all monitored services."""
        summaries = {}
        
        for service_key in self.health_history:
            parts = service_key.split(':', 1)
            if len(parts) == 2:
                service_name, service_id = parts
                summary = self.get_health_summary(service_name, service_id)
                if summary:
                    summaries[service_key] = summary
        
        return summaries
    
    async def force_health_check(self, service_name: str, service_id: str) -> Optional[HealthStatus]:
        """
        Force an immediate health check for a service.
        
        Args:
            service_name: Name of the service
            service_id: ID of the service instance
            
        Returns:
            Health status or None if service not found
        """
        service = await self.registry.get_service(service_name, service_id)
        if not service:
            return None
        
        return await self.check_service_health(service)


class CustomHealthChecker:
    """Custom health checker for non-HTTP protocols."""
    
    def __init__(self):
        self.checkers: Dict[str, Callable] = {}
    
    def register_checker(self, protocol: str, checker: Callable) -> None:
        """
        Register a custom health checker.
        
        Args:
            protocol: Protocol name (e.g., 'tcp', 'redis', 'postgres')
            checker: Async function that returns HealthStatus
        """
        self.checkers[protocol] = checker
    
    async def check_health(self, protocol: str, **kwargs) -> HealthStatus:
        """
        Perform health check using custom checker.
        
        Args:
            protocol: Protocol to use
            **kwargs: Protocol-specific parameters
            
        Returns:
            Health status
        """
        if protocol not in self.checkers:
            return HealthStatus(False, message=f"Unknown protocol: {protocol}")
        
        try:
            return await self.checkers[protocol](**kwargs)
        except Exception as e:
            return HealthStatus(False, message=f"Health check error: {str(e)}")


# Built-in custom health checkers

async def tcp_health_check(host: str, port: int, timeout: float = 5.0) -> HealthStatus:
    """TCP connection health check."""
    try:
        start_time = time.time()
        
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        
        response_time = time.time() - start_time
        writer.close()
        await writer.wait_closed()
        
        return HealthStatus(True, response_time, message="TCP connection successful")
    
    except asyncio.TimeoutError:
        return HealthStatus(False, timeout, message="TCP connection timeout")
    
    except Exception as e:
        return HealthStatus(False, message=f"TCP connection failed: {str(e)}")


async def redis_health_check(host: str, port: int = 6379, 
                           password: Optional[str] = None,
                           timeout: float = 5.0) -> HealthStatus:
    """Redis health check."""
    try:
        import redis.asyncio as redis
        
        start_time = time.time()
        
        client = redis.Redis(
            host=host, port=port, password=password,
            socket_timeout=timeout, socket_connect_timeout=timeout
        )
        
        await client.ping()
        response_time = time.time() - start_time
        
        await client.close()
        
        return HealthStatus(True, response_time, message="Redis ping successful")
    
    except Exception as e:
        return HealthStatus(False, message=f"Redis health check failed: {str(e)}")


async def postgres_health_check(host: str, port: int = 5432,
                               database: str = "postgres",
                               user: str = "postgres",
                               password: str = "",
                               timeout: float = 5.0) -> HealthStatus:
    """PostgreSQL health check."""
    try:
        import asyncpg
        
        start_time = time.time()
        
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=host, port=port, database=database,
                user=user, password=password
            ),
            timeout=timeout
        )
        
        await conn.execute("SELECT 1")
        response_time = time.time() - start_time
        
        await conn.close()
        
        return HealthStatus(True, response_time, message="PostgreSQL query successful")
    
    except Exception as e:
        return HealthStatus(False, message=f"PostgreSQL health check failed: {str(e)}")