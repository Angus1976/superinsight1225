"""Annotation Engine Health Check Service.

This module provides comprehensive health monitoring for all annotation engines,
including Label Studio, Argilla, and custom LLM engines.

Features:
- Periodic health checks with configurable intervals
- Automatic unhealthy engine disabling
- Exponential backoff retry logic
- Health status persistence
- Alert generation for health degradation

Requirements:
- 6.5: Engine health checks with exponential backoff
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class EngineType(str, Enum):
    """Annotation engine type."""
    LABEL_STUDIO = "label_studio"
    ARGILLA = "argilla"
    CUSTOM_LLM = "custom_llm"
    OLLAMA = "ollama"
    OPENAI = "openai"


class HealthStatus(str, Enum):
    """Engine health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class EngineHealthCheck(BaseModel):
    """Health check result for an engine."""
    engine_id: str
    engine_type: EngineType
    status: HealthStatus
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.now)
    consecutive_failures: int = 0
    last_success_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EngineConfig(BaseModel):
    """Engine configuration for health monitoring."""
    engine_id: str
    engine_type: EngineType
    enabled: bool = True
    health_check_url: Optional[str] = None
    health_check_func: Optional[Callable] = None
    timeout_seconds: float = 5.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class HealthAlert(BaseModel):
    """Health status alert."""
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    engine_id: str
    engine_type: EngineType
    severity: str  # "warning", "critical"
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


# ============================================================================
# Annotation Engine Health Monitor
# ============================================================================

class AnnotationEngineHealthMonitor:
    """Health monitoring service for annotation engines.

    This service periodically checks the health of all registered annotation
    engines and automatically disables unhealthy engines with exponential
    backoff retry logic.

    Attributes:
        check_interval: Health check interval in seconds
        max_failures: Maximum consecutive failures before disabling engine
        backoff_base: Base for exponential backoff (seconds)
        max_backoff: Maximum backoff time (seconds)
    """

    def __init__(
        self,
        check_interval: int = 60,
        max_failures: int = 3,
        backoff_base: float = 2.0,
        max_backoff: int = 300,
    ):
        """Initialize Health Monitor.

        Args:
            check_interval: Health check interval in seconds (default: 60)
            max_failures: Max consecutive failures before disabling (default: 3)
            backoff_base: Base for exponential backoff in seconds (default: 2.0)
            max_backoff: Maximum backoff time in seconds (default: 300)
        """
        self.check_interval = check_interval
        self.max_failures = max_failures
        self.backoff_base = backoff_base
        self.max_backoff = max_backoff

        # Engine registry
        self.engines: Dict[str, EngineConfig] = {}

        # Health status tracking
        self.health_status: Dict[str, EngineHealthCheck] = {}

        # Backoff tracking
        self.backoff_until: Dict[str, datetime] = {}

        # Alert tracking
        self.alerts: Dict[str, HealthAlert] = {}

        # Monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

        # Thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"Initialized Annotation Engine Health Monitor: "
            f"interval={check_interval}s, max_failures={max_failures}"
        )

    # ========================================================================
    # Engine Registration
    # ========================================================================

    async def register_engine(
        self,
        engine_id: str,
        engine_type: EngineType,
        health_check_func: Optional[Callable] = None,
        health_check_url: Optional[str] = None,
        timeout_seconds: float = 5.0,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Register engine for health monitoring.

        Args:
            engine_id: Unique engine identifier
            engine_type: Engine type
            health_check_func: Optional async function to check health
            health_check_url: Optional health check endpoint URL
            timeout_seconds: Health check timeout
            enabled: Whether engine is enabled
            metadata: Optional engine metadata
        """
        async with self._lock:
            config = EngineConfig(
                engine_id=engine_id,
                engine_type=engine_type,
                health_check_func=health_check_func,
                health_check_url=health_check_url,
                timeout_seconds=timeout_seconds,
                enabled=enabled,
                metadata=metadata or {},
            )

            self.engines[engine_id] = config

            # Initialize health status
            self.health_status[engine_id] = EngineHealthCheck(
                engine_id=engine_id,
                engine_type=engine_type,
                status=HealthStatus.UNKNOWN,
            )

        logger.info(f"Registered engine {engine_id} ({engine_type})")

    async def unregister_engine(self, engine_id: str):
        """Unregister engine from health monitoring.

        Args:
            engine_id: Engine identifier
        """
        async with self._lock:
            if engine_id in self.engines:
                del self.engines[engine_id]
                if engine_id in self.health_status:
                    del self.health_status[engine_id]
                if engine_id in self.backoff_until:
                    del self.backoff_until[engine_id]

        logger.info(f"Unregistered engine {engine_id}")

    # ========================================================================
    # Health Monitoring
    # ========================================================================

    async def start(self):
        """Start health monitoring background task."""
        if self._running:
            logger.warning("Health monitor already running")
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started health monitoring")

    async def stop(self):
        """Stop health monitoring background task."""
        if not self._running:
            return

        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped health monitoring")

    async def _monitor_loop(self):
        """Background health monitoring loop."""
        while self._running:
            try:
                await self._check_all_engines()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor loop error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _check_all_engines(self):
        """Check health of all registered engines."""
        engine_ids = list(self.engines.keys())

        for engine_id in engine_ids:
            try:
                await self._check_engine(engine_id)
            except Exception as e:
                logger.error(f"Health check failed for {engine_id}: {e}")

    async def _check_engine(self, engine_id: str):
        """Check health of single engine.

        Args:
            engine_id: Engine identifier
        """
        config = self.engines.get(engine_id)
        if not config:
            return

        # Skip if engine is disabled
        if not config.enabled:
            return

        # Check if engine is in backoff period
        if engine_id in self.backoff_until:
            if datetime.now() < self.backoff_until[engine_id]:
                logger.debug(
                    f"Engine {engine_id} in backoff until "
                    f"{self.backoff_until[engine_id]}"
                )
                return

        # Perform health check
        start_time = datetime.now()

        try:
            # Use custom health check function if provided
            if config.health_check_func:
                is_healthy = await asyncio.wait_for(
                    config.health_check_func(),
                    timeout=config.timeout_seconds,
                )
            elif config.health_check_url:
                # Use HTTP health check
                is_healthy = await self._http_health_check(
                    config.health_check_url,
                    config.timeout_seconds,
                )
            else:
                # No health check configured, assume healthy
                is_healthy = True

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Update health status
            await self._update_health_status(
                engine_id=engine_id,
                engine_type=config.engine_type,
                is_healthy=is_healthy,
                response_time_ms=response_time_ms,
                error=None,
            )

        except asyncio.TimeoutError:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            await self._update_health_status(
                engine_id=engine_id,
                engine_type=config.engine_type,
                is_healthy=False,
                response_time_ms=response_time_ms,
                error=f"Health check timeout after {config.timeout_seconds}s",
            )

        except Exception as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            await self._update_health_status(
                engine_id=engine_id,
                engine_type=config.engine_type,
                is_healthy=False,
                response_time_ms=response_time_ms,
                error=str(e),
            )

    async def _http_health_check(
        self,
        url: str,
        timeout: float,
    ) -> bool:
        """Perform HTTP health check.

        Args:
            url: Health check endpoint URL
            timeout: Request timeout in seconds

        Returns:
            True if healthy (status code 2xx), False otherwise
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                return 200 <= response.status_code < 300
        except Exception as e:
            logger.debug(f"HTTP health check failed for {url}: {e}")
            return False

    async def _update_health_status(
        self,
        engine_id: str,
        engine_type: EngineType,
        is_healthy: bool,
        response_time_ms: float,
        error: Optional[str],
    ):
        """Update engine health status.

        Args:
            engine_id: Engine identifier
            engine_type: Engine type
            is_healthy: Whether health check passed
            response_time_ms: Response time in milliseconds
            error: Error message if failed
        """
        async with self._lock:
            current_status = self.health_status.get(engine_id)

            if is_healthy:
                # Health check passed
                status = HealthStatus.HEALTHY
                consecutive_failures = 0
                last_success_at = datetime.now()

                # Clear backoff
                if engine_id in self.backoff_until:
                    del self.backoff_until[engine_id]

                # Clear critical alerts
                self._clear_alerts(engine_id)

            else:
                # Health check failed
                if current_status:
                    consecutive_failures = current_status.consecutive_failures + 1
                    last_success_at = current_status.last_success_at
                else:
                    consecutive_failures = 1
                    last_success_at = None

                # Determine status based on failure count
                if consecutive_failures >= self.max_failures:
                    status = HealthStatus.UNHEALTHY
                    # Disable engine
                    if engine_id in self.engines:
                        self.engines[engine_id].enabled = False
                    # Set exponential backoff
                    backoff_seconds = min(
                        self.backoff_base ** consecutive_failures,
                        self.max_backoff,
                    )
                    self.backoff_until[engine_id] = datetime.now() + timedelta(
                        seconds=backoff_seconds
                    )
                    # Create critical alert
                    await self._create_alert(
                        engine_id=engine_id,
                        engine_type=engine_type,
                        severity="critical",
                        message=(
                            f"Engine {engine_id} marked unhealthy after "
                            f"{consecutive_failures} consecutive failures. "
                            f"Backoff until {self.backoff_until[engine_id]}"
                        ),
                    )
                elif consecutive_failures >= 1:
                    status = HealthStatus.DEGRADED
                    # Create warning alert on first failure
                    if consecutive_failures == 1:
                        await self._create_alert(
                            engine_id=engine_id,
                            engine_type=engine_type,
                            severity="warning",
                            message=f"Engine {engine_id} health check failed: {error}",
                        )
                else:
                    status = HealthStatus.HEALTHY

            # Update health status
            self.health_status[engine_id] = EngineHealthCheck(
                engine_id=engine_id,
                engine_type=engine_type,
                status=status,
                response_time_ms=response_time_ms,
                error=error,
                checked_at=datetime.now(),
                consecutive_failures=consecutive_failures,
                last_success_at=last_success_at,
            )

        logger.debug(
            f"Engine {engine_id} health: {status}, "
            f"failures={consecutive_failures}, "
            f"response_time={response_time_ms:.1f}ms"
        )

    # ========================================================================
    # Alert Management
    # ========================================================================

    async def _create_alert(
        self,
        engine_id: str,
        engine_type: EngineType,
        severity: str,
        message: str,
    ):
        """Create health alert.

        Args:
            engine_id: Engine identifier
            engine_type: Engine type
            severity: Alert severity ("warning" or "critical")
            message: Alert message
        """
        alert = HealthAlert(
            engine_id=engine_id,
            engine_type=engine_type,
            severity=severity,
            message=message,
        )

        self.alerts[alert.alert_id] = alert

        logger.warning(f"Health alert [{severity}]: {message}")

    def _clear_alerts(self, engine_id: str):
        """Clear all alerts for engine.

        Args:
            engine_id: Engine identifier
        """
        alert_ids_to_remove = [
            alert_id
            for alert_id, alert in self.alerts.items()
            if alert.engine_id == engine_id and alert.severity == "critical"
        ]

        for alert_id in alert_ids_to_remove:
            del self.alerts[alert_id]

    async def get_active_alerts(
        self,
        severity: Optional[str] = None,
        engine_id: Optional[str] = None,
    ) -> List[HealthAlert]:
        """Get active alerts.

        Args:
            severity: Optional filter by severity
            engine_id: Optional filter by engine

        Returns:
            List of active (unacknowledged) alerts
        """
        alerts = [
            alert for alert in self.alerts.values()
            if not alert.acknowledged
        ]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if engine_id:
            alerts = [a for a in alerts if a.engine_id == engine_id]

        return alerts

    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: Optional[str] = None,
    ) -> bool:
        """Acknowledge alert.

        Args:
            alert_id: Alert ID
            acknowledged_by: Optional user who acknowledged

        Returns:
            True if acknowledged, False if not found
        """
        async with self._lock:
            if alert_id not in self.alerts:
                return False

            alert = self.alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_at = datetime.now()
            alert.acknowledged_by = acknowledged_by

        return True

    # ========================================================================
    # Status Queries
    # ========================================================================

    async def get_health_status(self, engine_id: str) -> Optional[EngineHealthCheck]:
        """Get health status for engine.

        Args:
            engine_id: Engine identifier

        Returns:
            Health check result or None if not found
        """
        return self.health_status.get(engine_id)

    async def get_all_health_statuses(self) -> Dict[str, EngineHealthCheck]:
        """Get health status for all engines.

        Returns:
            Dictionary of engine_id -> health status
        """
        return dict(self.health_status)

    async def get_healthy_engines(
        self,
        engine_type: Optional[EngineType] = None,
    ) -> List[str]:
        """Get list of healthy engine IDs.

        Args:
            engine_type: Optional filter by engine type

        Returns:
            List of healthy engine IDs
        """
        healthy = [
            engine_id
            for engine_id, status in self.health_status.items()
            if status.status == HealthStatus.HEALTHY
        ]

        if engine_type:
            healthy = [
                engine_id for engine_id in healthy
                if self.engines[engine_id].engine_type == engine_type
            ]

        return healthy

    async def is_engine_healthy(self, engine_id: str) -> bool:
        """Check if engine is healthy.

        Args:
            engine_id: Engine identifier

        Returns:
            True if healthy, False otherwise
        """
        status = self.health_status.get(engine_id)
        if not status:
            return False

        return status.status == HealthStatus.HEALTHY


# ============================================================================
# Global Instance
# ============================================================================

_health_monitor: Optional[AnnotationEngineHealthMonitor] = None
_monitor_lock = asyncio.Lock()


async def get_health_monitor() -> AnnotationEngineHealthMonitor:
    """Get global health monitor instance.

    Returns:
        AnnotationEngineHealthMonitor instance
    """
    global _health_monitor

    async with _monitor_lock:
        if _health_monitor is None:
            _health_monitor = AnnotationEngineHealthMonitor()

        return _health_monitor


async def reset_health_monitor():
    """Reset global health monitor (for testing)."""
    global _health_monitor

    async with _monitor_lock:
        if _health_monitor:
            await _health_monitor.stop()
            _health_monitor = None
