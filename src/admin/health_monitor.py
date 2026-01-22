"""
Health Monitor for SuperInsight Platform.

Provides background health monitoring for LLM APIs, database connections,
and sync pipelines. Triggers alerts when connection failures are detected.

This module follows async-first architecture using asyncio.
All I/O operations are non-blocking to prevent event loop blocking.

Validates Requirements: 10.5, 10.6
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============== Health Monitor Models ==============

class ServiceType(str, Enum):
    """Types of services that can be monitored."""
    LLM_API = "llm_api"
    DATABASE = "database"
    SYNC_PIPELINE = "sync_pipeline"
    REDIS = "redis"
    EXTERNAL_API = "external_api"


class HealthStatus(str, Enum):
    """Health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceHealth(BaseModel):
    """Health status of a monitored service."""
    service_id: str = Field(..., description="Service/configuration ID")
    service_name: str = Field(..., description="Service display name")
    service_type: ServiceType = Field(..., description="Type of service")
    tenant_id: str = Field(..., description="Tenant ID")
    status: HealthStatus = Field(default=HealthStatus.UNKNOWN, description="Current health status")
    last_check: Optional[datetime] = Field(default=None, description="Last health check time")
    last_success: Optional[datetime] = Field(default=None, description="Last successful check time")
    last_failure: Optional[datetime] = Field(default=None, description="Last failed check time")
    consecutive_failures: int = Field(default=0, description="Consecutive failure count")
    consecutive_successes: int = Field(default=0, description="Consecutive success count")
    latency_ms: Optional[float] = Field(default=None, description="Last check latency in ms")
    error_message: Optional[str] = Field(default=None, description="Last error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    alert_sent: bool = Field(default=False, description="Whether alert was sent for current failure")


class HealthCheckConfig(BaseModel):
    """Configuration for health checking a service."""
    service_id: str = Field(..., description="Service/configuration ID")
    service_name: str = Field(..., description="Service display name")
    service_type: ServiceType = Field(..., description="Type of service")
    tenant_id: str = Field(..., description="Tenant ID")
    check_interval_seconds: int = Field(default=30, ge=10, description="Check interval in seconds")
    timeout_seconds: int = Field(default=10, ge=1, description="Check timeout in seconds")
    failure_threshold: int = Field(default=3, ge=1, description="Failures before unhealthy")
    success_threshold: int = Field(default=1, ge=1, description="Successes before healthy")
    enabled: bool = Field(default=True, description="Whether monitoring is enabled")
    check_function: Optional[str] = Field(default=None, description="Custom check function name")
    connection_params: Dict[str, Any] = Field(default_factory=dict, description="Connection parameters")


class DashboardStatus(BaseModel):
    """Aggregated status for dashboard display."""
    tenant_id: str = Field(..., description="Tenant ID")
    llm_services: List[ServiceHealth] = Field(default_factory=list)
    database_services: List[ServiceHealth] = Field(default_factory=list)
    sync_pipelines: List[ServiceHealth] = Field(default_factory=list)
    overall_status: HealthStatus = Field(default=HealthStatus.UNKNOWN)
    healthy_count: int = Field(default=0)
    degraded_count: int = Field(default=0)
    unhealthy_count: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ============== Health Monitor ==============

class HealthMonitor:
    """
    Monitors health of LLM APIs, database connections, and sync pipelines.

    Features:
    - Periodic health checks with configurable intervals
    - Connection failure detection within 1 minute
    - Alert triggering on consecutive failures
    - Real-time dashboard status updates
    - Async health checking for non-blocking operation

    Validates Requirements: 10.5, 10.6
    """

    def __init__(self):
        """Initialize the health monitor."""
        self._configs: Dict[str, HealthCheckConfig] = {}
        self._health_status: Dict[str, ServiceHealth] = {}
        self._check_tasks: Dict[str, asyncio.Task] = {}
        self._alert_callbacks: List[Callable[[ServiceHealth], None]] = []
        self._status_callbacks: List[Callable[[ServiceHealth], None]] = []
        self._running: bool = False
        self._lock = asyncio.Lock()
        self._check_functions: Dict[str, Callable] = {}
        self._max_alert_interval_seconds: int = 60  # Alert within 1 minute
        logger.info("HealthMonitor initialized")

    async def register_service(self, config: HealthCheckConfig) -> ServiceHealth:
        """
        Register a service for health monitoring.

        Args:
            config: Health check configuration

        Returns:
            Initial health status

        Validates Requirements: 10.5
        """
        async with self._lock:
            self._configs[config.service_id] = config

            health = ServiceHealth(
                service_id=config.service_id,
                service_name=config.service_name,
                service_type=config.service_type,
                tenant_id=config.tenant_id,
                status=HealthStatus.UNKNOWN
            )
            self._health_status[config.service_id] = health

            logger.info(
                f"Registered service for monitoring: {config.service_name} "
                f"(type: {config.service_type.value}, interval: {config.check_interval_seconds}s)"
            )

            # Start monitoring if already running
            if self._running and config.enabled:
                await self._start_service_monitor(config.service_id)

            return health

    async def unregister_service(self, service_id: str) -> bool:
        """
        Unregister a service from health monitoring.

        Args:
            service_id: Service ID to unregister

        Returns:
            True if unregistered, False if not found
        """
        async with self._lock:
            if service_id not in self._configs:
                return False

            # Stop the check task
            await self._stop_service_monitor(service_id)

            del self._configs[service_id]
            if service_id in self._health_status:
                del self._health_status[service_id]

            logger.info(f"Unregistered service: {service_id}")
            return True

    async def start(self) -> None:
        """
        Start health monitoring for all registered services.

        Validates Requirements: 10.5
        """
        if self._running:
            logger.warning("Health monitor already running")
            return

        self._running = True

        async with self._lock:
            for service_id, config in self._configs.items():
                if config.enabled:
                    await self._start_service_monitor(service_id)

        logger.info(f"Health monitor started with {len(self._check_tasks)} services")

    async def stop(self) -> None:
        """Stop health monitoring for all services."""
        if not self._running:
            return

        self._running = False

        async with self._lock:
            for service_id in list(self._check_tasks.keys()):
                await self._stop_service_monitor(service_id)

        logger.info("Health monitor stopped")

    async def _start_service_monitor(self, service_id: str) -> None:
        """Start monitoring a specific service."""
        if service_id in self._check_tasks:
            return

        config = self._configs.get(service_id)
        if not config:
            return

        task = asyncio.create_task(self._check_loop(service_id))
        self._check_tasks[service_id] = task
        logger.debug(f"Started monitoring for {service_id}")

    async def _stop_service_monitor(self, service_id: str) -> None:
        """Stop monitoring a specific service."""
        if service_id not in self._check_tasks:
            return

        task = self._check_tasks[service_id]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        del self._check_tasks[service_id]
        logger.debug(f"Stopped monitoring for {service_id}")

    async def _check_loop(self, service_id: str) -> None:
        """Health check loop for a service."""
        while self._running:
            try:
                config = self._configs.get(service_id)
                if not config or not config.enabled:
                    break

                await self._perform_health_check(service_id)
                await asyncio.sleep(config.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop for {service_id}: {e}")
                await asyncio.sleep(30)  # Wait before retrying

    async def _perform_health_check(self, service_id: str) -> ServiceHealth:
        """
        Perform a health check for a service.

        Validates Requirements: 10.5
        """
        config = self._configs.get(service_id)
        if not config:
            raise ValueError(f"Service {service_id} not registered")

        health = self._health_status.get(service_id)
        if not health:
            health = ServiceHealth(
                service_id=service_id,
                service_name=config.service_name,
                service_type=config.service_type,
                tenant_id=config.tenant_id
            )
            self._health_status[service_id] = health

        start_time = asyncio.get_event_loop().time()

        try:
            # Perform check with timeout
            success, error_msg, details = await asyncio.wait_for(
                self._execute_health_check(config),
                timeout=config.timeout_seconds
            )

            end_time = asyncio.get_event_loop().time()
            latency_ms = (end_time - start_time) * 1000

            await self._update_health_status(
                health, config, success, latency_ms, error_msg, details
            )

        except asyncio.TimeoutError:
            end_time = asyncio.get_event_loop().time()
            latency_ms = (end_time - start_time) * 1000

            await self._update_health_status(
                health, config, False, latency_ms,
                f"Health check timeout after {config.timeout_seconds}s", {}
            )

        except Exception as e:
            logger.error(f"Health check error for {service_id}: {e}")
            await self._update_health_status(
                health, config, False, None, str(e), {}
            )

        return health

    async def _execute_health_check(
        self,
        config: HealthCheckConfig
    ) -> tuple:
        """
        Execute the actual health check based on service type.

        Returns:
            Tuple of (success, error_message, details)
        """
        if config.service_type == ServiceType.LLM_API:
            return await self._check_llm_api(config)
        elif config.service_type == ServiceType.DATABASE:
            return await self._check_database(config)
        elif config.service_type == ServiceType.SYNC_PIPELINE:
            return await self._check_sync_pipeline(config)
        elif config.service_type == ServiceType.REDIS:
            return await self._check_redis(config)
        elif config.service_type == ServiceType.EXTERNAL_API:
            return await self._check_external_api(config)
        else:
            # Use custom check function if provided
            if config.check_function and config.check_function in self._check_functions:
                check_fn = self._check_functions[config.check_function]
                return await check_fn(config)

            return False, f"Unknown service type: {config.service_type}", {}

    async def _check_llm_api(self, config: HealthCheckConfig) -> tuple:
        """Check LLM API health."""
        try:
            from src.admin.llm_provider_manager import LLMProviderManager

            manager = LLMProviderManager()
            result = await manager.test_connection(
                provider=config.connection_params.get("provider", "openai"),
                api_key=config.connection_params.get("api_key"),
                endpoint=config.connection_params.get("endpoint"),
                timeout=config.timeout_seconds
            )

            if result.success:
                return True, None, {
                    "latency_ms": result.latency_ms,
                    "provider": result.provider
                }
            else:
                return False, result.error_message, {
                    "error_code": result.error_code,
                    "suggestions": result.suggestions
                }

        except ImportError:
            logger.warning("LLMProviderManager not available")
            return False, "LLMProviderManager not available", {}
        except Exception as e:
            return False, str(e), {}

    async def _check_database(self, config: HealthCheckConfig) -> tuple:
        """Check database connection health."""
        try:
            from src.admin.db_connection_manager import DBConnectionManager, DBConfig
            from src.admin.schemas import DatabaseType

            db_type_str = config.connection_params.get("db_type", "postgresql")
            db_type = DatabaseType(db_type_str)

            db_config = DBConfig(
                db_type=db_type,
                host=config.connection_params.get("host", "localhost"),
                port=config.connection_params.get("port", 5432),
                database=config.connection_params.get("database", ""),
                username=config.connection_params.get("username", ""),
                password=config.connection_params.get("password", ""),
                ssl_enabled=config.connection_params.get("ssl_enabled", False),
                read_only=True,
                timeout=config.timeout_seconds
            )

            manager = DBConnectionManager()
            result = await manager.test_connection(db_config)

            if result.success:
                return True, None, {
                    "latency_ms": result.latency_ms,
                    "server_version": result.server_version
                }
            else:
                return False, result.error_message, {
                    "error_code": result.error_code,
                    "suggestions": result.suggestions
                }

        except ImportError:
            logger.warning("DBConnectionManager not available")
            return False, "DBConnectionManager not available", {}
        except Exception as e:
            return False, str(e), {}

    async def _check_sync_pipeline(self, config: HealthCheckConfig) -> tuple:
        """Check sync pipeline health."""
        try:
            # Check if sync is active and last sync was recent
            last_sync_str = config.connection_params.get("last_sync_at")
            if last_sync_str:
                last_sync = datetime.fromisoformat(last_sync_str)
                time_since_sync = (datetime.utcnow() - last_sync).total_seconds()

                expected_interval = config.connection_params.get("sync_interval_seconds", 3600)

                if time_since_sync > expected_interval * 2:
                    return False, f"Sync overdue by {time_since_sync - expected_interval}s", {
                        "last_sync": last_sync_str,
                        "expected_interval": expected_interval
                    }

            # Check sync status
            sync_status = config.connection_params.get("status", "unknown")
            if sync_status == "error":
                return False, config.connection_params.get("error_message", "Sync in error state"), {}
            elif sync_status == "disabled":
                return True, None, {"status": "disabled"}

            return True, None, {"status": sync_status}

        except Exception as e:
            return False, str(e), {}

    async def _check_redis(self, config: HealthCheckConfig) -> tuple:
        """Check Redis connection health."""
        try:
            import aioredis

            redis = await aioredis.from_url(
                config.connection_params.get("url", "redis://localhost:6379"),
                socket_timeout=config.timeout_seconds
            )

            try:
                pong = await redis.ping()
                if pong:
                    return True, None, {"response": "PONG"}
                else:
                    return False, "No response from Redis", {}
            finally:
                await redis.close()

        except ImportError:
            logger.warning("aioredis not available")
            return False, "aioredis not available", {}
        except Exception as e:
            return False, str(e), {}

    async def _check_external_api(self, config: HealthCheckConfig) -> tuple:
        """Check external API health."""
        try:
            import aiohttp

            url = config.connection_params.get("health_url")
            if not url:
                return False, "No health URL configured", {}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=config.timeout_seconds)
                ) as response:
                    if response.status < 400:
                        return True, None, {"status_code": response.status}
                    else:
                        return False, f"HTTP {response.status}", {"status_code": response.status}

        except Exception as e:
            return False, str(e), {}

    async def _update_health_status(
        self,
        health: ServiceHealth,
        config: HealthCheckConfig,
        success: bool,
        latency_ms: Optional[float],
        error_message: Optional[str],
        details: Dict[str, Any]
    ) -> None:
        """
        Update health status and trigger alerts if needed.

        Validates Requirements: 10.5
        """
        now = datetime.utcnow()
        health.last_check = now
        health.latency_ms = latency_ms
        health.details = details

        if success:
            health.last_success = now
            health.error_message = None
            health.consecutive_failures = 0
            health.consecutive_successes += 1
            health.alert_sent = False

            if health.consecutive_successes >= config.success_threshold:
                health.status = HealthStatus.HEALTHY

        else:
            health.last_failure = now
            health.error_message = error_message
            health.consecutive_successes = 0
            health.consecutive_failures += 1

            if health.consecutive_failures >= config.failure_threshold:
                health.status = HealthStatus.UNHEALTHY

                # Check if we need to send alert (within 1 minute of first failure)
                if not health.alert_sent:
                    await self._trigger_alert(health)
                    health.alert_sent = True

            elif health.consecutive_failures >= 1:
                health.status = HealthStatus.DEGRADED

        # Notify status callbacks
        await self._notify_status_change(health)

        logger.debug(
            f"Health check for {health.service_name}: "
            f"status={health.status.value}, "
            f"failures={health.consecutive_failures}, "
            f"latency={latency_ms:.2f}ms" if latency_ms else "latency=N/A"
        )

    async def _trigger_alert(self, health: ServiceHealth) -> None:
        """
        Trigger an alert for service failure.

        Validates Requirements: 10.5 (alert within 1 minute)
        """
        logger.warning(
            f"Service failure alert: {health.service_name} "
            f"(type: {health.service_type.value}, "
            f"consecutive_failures: {health.consecutive_failures}, "
            f"error: {health.error_message})"
        )

        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(health)
                else:
                    callback(health)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    async def _notify_status_change(self, health: ServiceHealth) -> None:
        """Notify status change callbacks."""
        for callback in self._status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(health)
                else:
                    callback(health)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def add_alert_callback(self, callback: Callable[[ServiceHealth], None]) -> None:
        """Add a callback for service failure alerts."""
        self._alert_callbacks.append(callback)
        logger.info(f"Added alert callback: {callback.__name__}")

    def remove_alert_callback(self, callback: Callable[[ServiceHealth], None]) -> None:
        """Remove an alert callback."""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
            logger.info(f"Removed alert callback: {callback.__name__}")

    def add_status_callback(self, callback: Callable[[ServiceHealth], None]) -> None:
        """Add a callback for status changes."""
        self._status_callbacks.append(callback)

    def remove_status_callback(self, callback: Callable[[ServiceHealth], None]) -> None:
        """Remove a status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def register_check_function(
        self,
        name: str,
        func: Callable[[HealthCheckConfig], tuple]
    ) -> None:
        """Register a custom health check function."""
        self._check_functions[name] = func
        logger.info(f"Registered custom check function: {name}")

    async def get_service_health(self, service_id: str) -> Optional[ServiceHealth]:
        """Get health status for a specific service."""
        async with self._lock:
            return self._health_status.get(service_id)

    async def get_tenant_health(self, tenant_id: str) -> List[ServiceHealth]:
        """Get health status for all services of a tenant."""
        async with self._lock:
            return [
                h for h in self._health_status.values()
                if h.tenant_id == tenant_id
            ]

    async def get_dashboard_status(self, tenant_id: str) -> DashboardStatus:
        """
        Get aggregated dashboard status for a tenant.

        Validates Requirements: 10.6
        """
        async with self._lock:
            tenant_services = [
                h for h in self._health_status.values()
                if h.tenant_id == tenant_id
            ]

            llm_services = [h for h in tenant_services if h.service_type == ServiceType.LLM_API]
            database_services = [h for h in tenant_services if h.service_type == ServiceType.DATABASE]
            sync_pipelines = [h for h in tenant_services if h.service_type == ServiceType.SYNC_PIPELINE]

            healthy_count = sum(1 for h in tenant_services if h.status == HealthStatus.HEALTHY)
            degraded_count = sum(1 for h in tenant_services if h.status == HealthStatus.DEGRADED)
            unhealthy_count = sum(1 for h in tenant_services if h.status == HealthStatus.UNHEALTHY)

            # Determine overall status
            if unhealthy_count > 0:
                overall_status = HealthStatus.UNHEALTHY
            elif degraded_count > 0:
                overall_status = HealthStatus.DEGRADED
            elif healthy_count > 0:
                overall_status = HealthStatus.HEALTHY
            else:
                overall_status = HealthStatus.UNKNOWN

            return DashboardStatus(
                tenant_id=tenant_id,
                llm_services=llm_services,
                database_services=database_services,
                sync_pipelines=sync_pipelines,
                overall_status=overall_status,
                healthy_count=healthy_count,
                degraded_count=degraded_count,
                unhealthy_count=unhealthy_count,
                last_updated=datetime.utcnow()
            )

    async def force_check(self, service_id: str) -> Optional[ServiceHealth]:
        """
        Force an immediate health check for a service.

        Returns:
            Updated health status or None if service not found
        """
        if service_id not in self._configs:
            return None

        return await self._perform_health_check(service_id)

    async def force_check_all(self, tenant_id: str) -> List[ServiceHealth]:
        """Force immediate health checks for all services of a tenant."""
        results: List[ServiceHealth] = []

        async with self._lock:
            tenant_services = [
                sid for sid, config in self._configs.items()
                if config.tenant_id == tenant_id
            ]

        for service_id in tenant_services:
            try:
                health = await self._perform_health_check(service_id)
                results.append(health)
            except Exception as e:
                logger.error(f"Error checking {service_id}: {e}")

        return results

    async def update_config(
        self,
        service_id: str,
        updates: Dict[str, Any]
    ) -> Optional[HealthCheckConfig]:
        """Update health check configuration for a service."""
        async with self._lock:
            if service_id not in self._configs:
                return None

            config = self._configs[service_id]

            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            # Restart monitoring if enabled status changed
            if "enabled" in updates:
                if updates["enabled"] and self._running:
                    await self._start_service_monitor(service_id)
                elif not updates["enabled"]:
                    await self._stop_service_monitor(service_id)

            logger.info(f"Updated health check config for {service_id}")
            return config

    async def get_health_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get health monitoring statistics for a tenant."""
        async with self._lock:
            tenant_services = [
                h for h in self._health_status.values()
                if h.tenant_id == tenant_id
            ]

            by_type: Dict[str, Dict[str, int]] = {}
            for service_type in ServiceType:
                type_services = [h for h in tenant_services if h.service_type == service_type]
                by_type[service_type.value] = {
                    "total": len(type_services),
                    "healthy": sum(1 for h in type_services if h.status == HealthStatus.HEALTHY),
                    "degraded": sum(1 for h in type_services if h.status == HealthStatus.DEGRADED),
                    "unhealthy": sum(1 for h in type_services if h.status == HealthStatus.UNHEALTHY),
                }

            # Calculate uptime percentages (if we had historical data)
            now = datetime.utcnow()
            services_with_recent_success = sum(
                1 for h in tenant_services
                if h.last_success and (now - h.last_success).total_seconds() < 3600
            )

            return {
                "total_services": len(tenant_services),
                "healthy": sum(1 for h in tenant_services if h.status == HealthStatus.HEALTHY),
                "degraded": sum(1 for h in tenant_services if h.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for h in tenant_services if h.status == HealthStatus.UNHEALTHY),
                "by_type": by_type,
                "services_with_recent_success": services_with_recent_success,
                "monitoring_active": self._running,
                "active_monitors": len(self._check_tasks)
            }
