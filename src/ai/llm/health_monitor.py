"""
LLM Health Monitor for SuperInsight platform.

Monitors the health of LLM providers with automatic health checks,
status management, alerting, and Prometheus metrics integration.

Features:
- Background health check loop (60-second interval)
- Health status persistence in database
- Automatic alert triggering on status changes
- Prometheus metrics integration
- Async-safe implementation using asyncio.Lock

Requirements Implemented:
- 5.1: Perform health checks on all configured providers every 60 seconds
- 5.2: When health check fails, mark provider as unhealthy and trigger alerts
- 5.3: When provider becomes unhealthy, automatically route requests to healthy providers
- 5.4: When provider recovers, mark it as healthy and resume routing requests
- 5.5: Expose health metrics via Prometheus endpoints
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

if TYPE_CHECKING:
    from src.ai.llm_switcher import LLMSwitcher

try:
    from src.ai.llm_schemas import LLMMethod, HealthStatus
    from src.models.llm_configuration import LLMHealthStatus, LLMConfiguration
except ImportError:
    from ai.llm_schemas import LLMMethod, HealthStatus
    from models.llm_configuration import LLMHealthStatus, LLMConfiguration


logger = logging.getLogger(__name__)

# Health check interval in seconds (Requirement 5.1)
HEALTH_CHECK_INTERVAL_SECONDS = 60

# Maximum consecutive failures before triggering alert
MAX_CONSECUTIVE_FAILURES_FOR_ALERT = 3


class HealthMonitor:
    """
    Monitors LLM provider health with automatic health checks.
    
    Implements Requirements 5.1-5.5:
    - Performs health checks every 60 seconds
    - Marks providers as unhealthy on failure and triggers alerts
    - Tracks healthy providers for request routing
    - Exposes health metrics via Prometheus
    
    Uses asyncio.Lock for thread-safe async operations (per async-sync-safety.md).
    """
    
    def __init__(
        self,
        switcher: "LLMSwitcher",
        db_session: Optional[AsyncSession] = None,
        metrics_collector: Optional[Any] = None,
    ):
        """
        Initialize the Health Monitor.
        
        Args:
            switcher: LLMSwitcher instance for provider access
            db_session: Optional database session for persistence
            metrics_collector: Optional Prometheus metrics collector
        """
        self._switcher = switcher
        self._db = db_session
        self._metrics = metrics_collector
        
        # Health status cache (provider_id -> is_healthy)
        self._health_status: Dict[str, bool] = {}
        
        # Consecutive failure tracking (provider_id -> count)
        self._consecutive_failures: Dict[str, int] = {}
        
        # Last error messages (provider_id -> error)
        self._last_errors: Dict[str, Optional[str]] = {}
        
        # Async lock for thread-safe operations (per async-sync-safety.md)
        self._lock = asyncio.Lock()
        
        # Background monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Alert callbacks
        self._alert_callbacks: List[Any] = []
        
        logger.debug("HealthMonitor initialized")
    
    async def _get_db(self) -> Optional[AsyncSession]:
        """Get database session."""
        if self._db:
            return self._db
        # Database session is optional - health monitoring can work without persistence
        return None
    
    # ==================== Lifecycle Methods ====================
    
    async def start(self) -> None:
        """
        Start health monitoring background task.
        
        Creates an asyncio task that runs the health check loop
        every 60 seconds (Requirement 5.1).
        """
        if self._running:
            logger.warning("Health monitor is already running")
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")
    
    async def stop(self) -> None:
        """
        Stop health monitoring background task.
        
        Cancels the background task and waits for it to complete.
        """
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        logger.info("Health monitor stopped")
    
    # ==================== Health Check Loop ====================
    
    async def _monitor_loop(self) -> None:
        """
        Background health check loop.
        
        Performs health checks on all configured providers every 60 seconds
        (Requirement 5.1). Handles errors gracefully to ensure the loop
        continues running.
        """
        logger.info(f"Starting health check loop with {HEALTH_CHECK_INTERVAL_SECONDS}s interval")
        
        while self._running:
            try:
                await self._perform_health_checks()
                
            except asyncio.CancelledError:
                logger.debug("Health check loop cancelled")
                break
                
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}", exc_info=True)
            
            # Wait for next check interval
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
        
        logger.info("Health check loop ended")
    
    async def _perform_health_checks(self) -> None:
        """
        Perform health checks on all configured providers.
        
        Iterates through all providers from the switcher and checks
        their health status, updating the database and metrics.
        """
        # Ensure switcher is initialized
        await self._switcher._ensure_initialized()
        
        # Get all configured providers
        providers = self._switcher._providers
        
        if not providers:
            logger.debug("No providers configured for health check")
            return
        
        logger.debug(f"Performing health checks on {len(providers)} providers")
        
        for method, provider in providers.items():
            try:
                # Perform health check
                health_status = await provider.health_check()
                is_healthy = health_status.available
                error_message = health_status.error if not is_healthy else None
                
                # Get provider ID from configuration
                provider_id = await self._get_provider_id(method)
                
                if provider_id:
                    # Update health status
                    await self._update_health_status(
                        provider_id=provider_id,
                        method=method,
                        is_healthy=is_healthy,
                        error_message=error_message
                    )
                    
                    # Update Prometheus metrics (Requirement 5.5)
                    self._update_prometheus_metrics(method, is_healthy)
                
            except Exception as e:
                logger.error(f"Health check failed for {method}: {e}")
                
                # Mark as unhealthy on exception
                provider_id = await self._get_provider_id(method)
                if provider_id:
                    await self._update_health_status(
                        provider_id=provider_id,
                        method=method,
                        is_healthy=False,
                        error_message=str(e)
                    )
                    self._update_prometheus_metrics(method, False)
    
    async def _get_provider_id(self, method: LLMMethod) -> Optional[str]:
        """
        Get provider ID from database for a given method.
        
        Args:
            method: LLM method to look up
            
        Returns:
            Provider ID as string, or None if not found
        """
        db = await self._get_db()
        if db is None:
            # Use method value as a fallback ID when no database
            return f"provider_{method.value}"
        
        try:
            # Query for the configuration with this method
            stmt = select(LLMConfiguration).where(
                LLMConfiguration.default_method == method.value,
                LLMConfiguration.is_active == True
            )
            result = await db.execute(stmt)
            config = result.scalar_one_or_none()
            
            if config:
                return str(config.id)
            
            # If no exact match, try to find any active configuration
            # This handles cases where multiple methods share a configuration
            stmt = select(LLMConfiguration).where(
                LLMConfiguration.is_active == True
            ).limit(1)
            result = await db.execute(stmt)
            config = result.scalar_one_or_none()
            
            return str(config.id) if config else f"provider_{method.value}"
            
        except Exception as e:
            logger.warning(f"Failed to get provider ID for {method}: {e}")
            return f"provider_{method.value}"
    
    # ==================== Health Status Management ====================
    
    async def _update_health_status(
        self,
        provider_id: str,
        method: LLMMethod,
        is_healthy: bool,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update provider health status and trigger alerts on status change.
        
        Implements Requirements 5.2, 5.3, 5.4:
        - Marks provider as unhealthy on failure
        - Triggers alerts on status change
        - Marks provider as healthy on recovery
        
        Args:
            provider_id: Provider UUID as string
            method: LLM method
            is_healthy: Current health status
            error_message: Error message if unhealthy
        """
        async with self._lock:
            # Get previous status
            previous_status = self._health_status.get(provider_id)
            
            # Update in-memory cache
            self._health_status[provider_id] = is_healthy
            self._last_errors[provider_id] = error_message
            
            # Update consecutive failures counter
            if is_healthy:
                self._consecutive_failures[provider_id] = 0
            else:
                self._consecutive_failures[provider_id] = \
                    self._consecutive_failures.get(provider_id, 0) + 1
            
            consecutive_failures = self._consecutive_failures[provider_id]
        
        # Persist to database
        await self._persist_health_status(
            provider_id=provider_id,
            is_healthy=is_healthy,
            error_message=error_message,
            consecutive_failures=consecutive_failures
        )
        
        # Trigger alerts on status change (Requirement 5.2)
        if previous_status is not None and previous_status != is_healthy:
            if is_healthy:
                # Provider recovered (Requirement 5.4)
                logger.info(f"Provider {method.value} ({provider_id}) recovered")
                await self._send_alert(
                    provider_id=provider_id,
                    method=method,
                    alert_type="recovered",
                    message=f"LLM provider {method.value} has recovered and is now healthy"
                )
            else:
                # Provider became unhealthy (Requirement 5.2)
                logger.warning(
                    f"Provider {method.value} ({provider_id}) became unhealthy: {error_message}"
                )
                await self._send_alert(
                    provider_id=provider_id,
                    method=method,
                    alert_type="unhealthy",
                    message=f"LLM provider {method.value} is unhealthy: {error_message}"
                )
    
    async def _persist_health_status(
        self,
        provider_id: str,
        is_healthy: bool,
        error_message: Optional[str],
        consecutive_failures: int
    ) -> None:
        """
        Persist health status to database.
        
        Uses upsert to create or update the health status record.
        
        Args:
            provider_id: Provider UUID as string
            is_healthy: Current health status
            error_message: Error message if unhealthy
            consecutive_failures: Number of consecutive failures
        """
        db = await self._get_db()
        if db is None:
            # Skip persistence when no database available
            logger.debug(f"Skipping health status persistence (no database): {provider_id}")
            return
        
        try:
            now = datetime.utcnow()
            
            # Use PostgreSQL upsert (INSERT ... ON CONFLICT UPDATE)
            stmt = pg_insert(LLMHealthStatus).values(
                provider_id=UUID(provider_id),
                is_healthy=is_healthy,
                last_check_at=now,
                last_error=error_message[:500] if error_message else None,
                consecutive_failures=consecutive_failures,
                updated_at=now
            ).on_conflict_do_update(
                index_elements=['provider_id'],
                set_={
                    'is_healthy': is_healthy,
                    'last_check_at': now,
                    'last_error': error_message[:500] if error_message else None,
                    'consecutive_failures': consecutive_failures,
                    'updated_at': now
                }
            )
            
            await db.execute(stmt)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to persist health status for {provider_id}: {e}")
    
    async def _send_alert(
        self,
        provider_id: str,
        method: LLMMethod,
        alert_type: str,
        message: str
    ) -> None:
        """
        Send alert for health status change.
        
        Triggers registered alert callbacks and logs the event.
        
        Args:
            provider_id: Provider UUID as string
            method: LLM method
            alert_type: Type of alert ("unhealthy" or "recovered")
            message: Alert message
        """
        alert_data = {
            "provider_id": provider_id,
            "method": method.value,
            "alert_type": alert_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log the alert
        if alert_type == "unhealthy":
            logger.warning(f"ALERT: {message}")
        else:
            logger.info(f"ALERT: {message}")
        
        # Call registered alert callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def register_alert_callback(self, callback) -> None:
        """
        Register a callback for health alerts.
        
        Args:
            callback: Function to call when alert is triggered
        """
        self._alert_callbacks.append(callback)
    
    def unregister_alert_callback(self, callback) -> None:
        """
        Unregister an alert callback.
        
        Args:
            callback: Callback to remove
        """
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    # ==================== Prometheus Metrics ====================
    
    def _update_prometheus_metrics(self, method: LLMMethod, is_healthy: bool) -> None:
        """
        Update Prometheus metrics for provider health.
        
        Implements Requirement 5.5: Expose health metrics via Prometheus endpoints.
        
        Args:
            method: LLM method
            is_healthy: Current health status
        """
        if self._metrics is None:
            # Try to get the global prometheus exporter
            try:
                from src.system.prometheus_exporter import prometheus_exporter
                self._metrics = prometheus_exporter
            except ImportError:
                logger.debug("Prometheus exporter not available")
                return
        
        try:
            # Track AI inference health as a gauge
            # Using the existing ai_confidence_score gauge with a special label
            # or we can add a custom metric
            if hasattr(self._metrics, 'track_ai_inference'):
                # Record a health check as an inference
                self._metrics.track_ai_inference(
                    model_name=f"health_check_{method.value}",
                    success=is_healthy,
                    duration=0.0
                )
        except Exception as e:
            logger.debug(f"Failed to update Prometheus metrics: {e}")
    
    # ==================== Public Query Methods ====================
    
    async def get_health_status(self, provider_id: str) -> bool:
        """
        Get current health status of a provider.
        
        Args:
            provider_id: Provider UUID as string
            
        Returns:
            True if provider is healthy, False otherwise
        """
        async with self._lock:
            return self._health_status.get(provider_id, False)
    
    async def get_healthy_providers(self) -> List[str]:
        """
        Get list of healthy provider IDs.
        
        Used for request routing (Requirement 5.3).
        
        Returns:
            List of provider IDs that are currently healthy
        """
        async with self._lock:
            return [
                provider_id
                for provider_id, is_healthy in self._health_status.items()
                if is_healthy
            ]
    
    async def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status for all providers.
        
        Returns:
            Dictionary mapping provider IDs to their health information
        """
        async with self._lock:
            return {
                provider_id: {
                    "is_healthy": is_healthy,
                    "consecutive_failures": self._consecutive_failures.get(provider_id, 0),
                    "last_error": self._last_errors.get(provider_id)
                }
                for provider_id, is_healthy in self._health_status.items()
            }
    
    async def get_health_status_from_db(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        Get health status from database.
        
        Args:
            provider_id: Provider UUID as string
            
        Returns:
            Health status dictionary or None if not found
        """
        db = await self._get_db()
        if db is None:
            # Return from in-memory cache when no database
            async with self._lock:
                if provider_id in self._health_status:
                    return {
                        "provider_id": provider_id,
                        "is_healthy": self._health_status[provider_id],
                        "consecutive_failures": self._consecutive_failures.get(provider_id, 0),
                        "last_error": self._last_errors.get(provider_id)
                    }
            return None
        
        try:
            stmt = select(LLMHealthStatus).where(
                LLMHealthStatus.provider_id == UUID(provider_id)
            )
            result = await db.execute(stmt)
            status = result.scalar_one_or_none()
            
            if status:
                return status.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get health status from DB: {e}")
            return None
    
    async def force_health_check(self, method: Optional[LLMMethod] = None) -> Dict[str, bool]:
        """
        Force an immediate health check.
        
        Args:
            method: Specific method to check, or None for all
            
        Returns:
            Dictionary mapping method values to health status
        """
        results = {}
        
        await self._switcher._ensure_initialized()
        providers = self._switcher._providers
        
        methods_to_check = [method] if method else list(providers.keys())
        
        for m in methods_to_check:
            if m in providers:
                try:
                    health_status = await providers[m].health_check()
                    is_healthy = health_status.available
                    results[m.value] = is_healthy
                    
                    # Update status
                    provider_id = await self._get_provider_id(m)
                    if provider_id:
                        await self._update_health_status(
                            provider_id=provider_id,
                            method=m,
                            is_healthy=is_healthy,
                            error_message=health_status.error
                        )
                        self._update_prometheus_metrics(m, is_healthy)
                        
                except Exception as e:
                    logger.error(f"Force health check failed for {m}: {e}")
                    results[m.value] = False
        
        return results
    
    @property
    def is_running(self) -> bool:
        """Check if the health monitor is running."""
        return self._running


# ==================== Singleton Instance ====================

_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor(
    switcher: Optional["LLMSwitcher"] = None,
    db_session: Optional[AsyncSession] = None,
    metrics_collector: Optional[Any] = None,
) -> HealthMonitor:
    """
    Get or create the global Health Monitor instance.
    
    Args:
        switcher: LLMSwitcher instance (required for first call)
        db_session: Optional database session
        metrics_collector: Optional Prometheus metrics collector
        
    Returns:
        HealthMonitor instance
    """
    global _health_monitor
    
    if _health_monitor is None:
        if switcher is None:
            raise ValueError("switcher is required for first initialization")
        _health_monitor = HealthMonitor(
            switcher=switcher,
            db_session=db_session,
            metrics_collector=metrics_collector
        )
    
    return _health_monitor


async def get_initialized_health_monitor(
    switcher: Optional["LLMSwitcher"] = None,
    db_session: Optional[AsyncSession] = None,
    metrics_collector: Optional[Any] = None,
) -> HealthMonitor:
    """
    Get an initialized and running Health Monitor instance.
    
    Args:
        switcher: LLMSwitcher instance (required for first call)
        db_session: Optional database session
        metrics_collector: Optional Prometheus metrics collector
        
    Returns:
        Running HealthMonitor instance
    """
    monitor = get_health_monitor(switcher, db_session, metrics_collector)
    
    if not monitor.is_running:
        await monitor.start()
    
    return monitor
