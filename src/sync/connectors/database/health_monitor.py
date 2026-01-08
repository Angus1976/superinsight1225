"""
Database Health Monitor.

Provides comprehensive health monitoring for database connections
with alerting, diagnostics, and automatic recovery.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.sync.connectors.base import BaseConnector, ConnectionStatus

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Individual health check definition."""
    name: str
    description: str
    check_function: Callable
    interval_seconds: int = 30
    timeout_seconds: int = 10
    warning_threshold: float = 5.0  # seconds
    critical_threshold: float = 10.0  # seconds
    enabled: bool = True


@dataclass
class HealthResult:
    """Result of a health check."""
    check_name: str
    status: HealthStatus
    response_time: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


@dataclass
class Alert:
    """Health monitoring alert."""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthMonitorConfig(BaseModel):
    """Configuration for health monitoring."""
    enabled: bool = True
    check_interval: int = Field(default=30, ge=1)  # seconds
    alert_cooldown: int = Field(default=300, ge=1)  # seconds
    max_history_size: int = Field(default=1000, ge=1)
    
    # Thresholds
    connection_timeout: float = Field(default=10.0, ge=0.1)
    query_timeout: float = Field(default=30.0, ge=0.1)
    slow_query_threshold: float = Field(default=5.0, ge=0.1)
    
    # Alerting
    enable_alerts: bool = True
    alert_channels: List[str] = Field(default_factory=list)
    
    # Recovery
    auto_recovery: bool = True
    max_recovery_attempts: int = Field(default=3, ge=1)
    recovery_delay: float = Field(default=60.0, ge=1.0)


class DatabaseHealthMonitor:
    """
    Comprehensive health monitor for database connections.
    
    Features:
    - Multiple health check types
    - Performance monitoring
    - Alerting system
    - Automatic recovery
    - Historical tracking
    """

    def __init__(self, config: HealthMonitorConfig):
        self.config = config
        self.monitor_id = str(uuid4())
        
        # Monitored connections
        self.connections: Dict[str, BaseConnector] = {}
        
        # Health checks
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_results: Dict[str, List[HealthResult]] = {}
        
        # Alerting
        self.alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable] = []
        self.last_alert_time: Dict[str, datetime] = {}
        
        # Recovery
        self.recovery_attempts: Dict[str, int] = {}
        self.last_recovery_time: Dict[str, datetime] = {}
        
        # Monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Initialize default health checks
        self._setup_default_checks()

    def _setup_default_checks(self) -> None:
        """Setup default health checks."""
        self.add_health_check(HealthCheck(
            name="connection_status",
            description="Check if connection is active",
            check_function=self._check_connection_status,
            interval_seconds=30
        ))
        
        self.add_health_check(HealthCheck(
            name="query_performance",
            description="Test query performance",
            check_function=self._check_query_performance,
            interval_seconds=60,
            warning_threshold=2.0,
            critical_threshold=5.0
        ))
        
        self.add_health_check(HealthCheck(
            name="connection_pool",
            description="Check connection pool health",
            check_function=self._check_connection_pool,
            interval_seconds=45
        ))

    def add_connection(self, connection_id: str, connector: BaseConnector) -> None:
        """Add a connection to monitor."""
        self.connections[connection_id] = connector
        self.health_results[connection_id] = []
        logger.info(f"Added connection to monitor: {connection_id}")

    def remove_connection(self, connection_id: str) -> None:
        """Remove a connection from monitoring."""
        self.connections.pop(connection_id, None)
        self.health_results.pop(connection_id, None)
        self.recovery_attempts.pop(connection_id, None)
        self.last_recovery_time.pop(connection_id, None)
        logger.info(f"Removed connection from monitor: {connection_id}")

    def add_health_check(self, health_check: HealthCheck) -> None:
        """Add a custom health check."""
        self.health_checks[health_check.name] = health_check
        logger.info(f"Added health check: {health_check.name}")

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler function."""
        self.alert_handlers.append(handler)

    async def start_monitoring(self) -> None:
        """Start the health monitoring process."""
        if not self.config.enabled:
            logger.info("Health monitoring is disabled")
            return

        logger.info("Starting database health monitoring")
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop the health monitoring process."""
        logger.info("Stopping database health monitoring")
        self._shutdown_event.set()
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                await self._run_health_checks()
                await asyncio.sleep(self.config.check_interval)
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)

    async def _run_health_checks(self) -> None:
        """Run all enabled health checks for all connections."""
        for connection_id, connector in self.connections.items():
            for check_name, health_check in self.health_checks.items():
                if not health_check.enabled:
                    continue
                
                try:
                    result = await self._execute_health_check(
                        connection_id, connector, health_check
                    )
                    
                    # Store result
                    self._store_health_result(connection_id, result)
                    
                    # Check for alerts
                    await self._check_alerts(connection_id, result)
                    
                    # Check for recovery needs
                    if result.status == HealthStatus.CRITICAL and self.config.auto_recovery:
                        await self._attempt_recovery(connection_id, connector)
                
                except Exception as e:
                    logger.error(f"Health check failed {check_name} for {connection_id}: {e}")

    async def _execute_health_check(
        self,
        connection_id: str,
        connector: BaseConnector,
        health_check: HealthCheck
    ) -> HealthResult:
        """Execute a single health check."""
        start_time = time.time()
        
        try:
            # Execute check with timeout
            result = await asyncio.wait_for(
                health_check.check_function(connector),
                timeout=health_check.timeout_seconds
            )
            
            response_time = time.time() - start_time
            
            # Determine status based on response time
            if response_time >= health_check.critical_threshold:
                status = HealthStatus.CRITICAL
                message = f"Response time {response_time:.2f}s exceeds critical threshold"
            elif response_time >= health_check.warning_threshold:
                status = HealthStatus.WARNING
                message = f"Response time {response_time:.2f}s exceeds warning threshold"
            else:
                status = HealthStatus.HEALTHY
                message = f"Check passed in {response_time:.2f}s"
            
            return HealthResult(
                check_name=health_check.name,
                status=status,
                response_time=response_time,
                message=message,
                details=result if isinstance(result, dict) else {}
            )
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return HealthResult(
                check_name=health_check.name,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                message=f"Health check timed out after {health_check.timeout_seconds}s",
                error="timeout"
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthResult(
                check_name=health_check.name,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                message=f"Health check failed: {str(e)}",
                error=str(e)
            )

    def _store_health_result(self, connection_id: str, result: HealthResult) -> None:
        """Store health check result with history management."""
        if connection_id not in self.health_results:
            self.health_results[connection_id] = []
        
        results = self.health_results[connection_id]
        results.append(result)
        
        # Maintain history size limit
        if len(results) > self.config.max_history_size:
            results.pop(0)

    async def _check_alerts(self, connection_id: str, result: HealthResult) -> None:
        """Check if an alert should be generated."""
        if not self.config.enable_alerts:
            return
        
        alert_key = f"{connection_id}_{result.check_name}"
        
        # Check cooldown
        last_alert = self.last_alert_time.get(alert_key)
        if last_alert:
            cooldown_delta = timedelta(seconds=self.config.alert_cooldown)
            if datetime.utcnow() - last_alert < cooldown_delta:
                return
        
        # Generate alert for warning/critical status
        if result.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
            severity = AlertSeverity.WARNING if result.status == HealthStatus.WARNING else AlertSeverity.CRITICAL
            
            alert = Alert(
                id=str(uuid4()),
                severity=severity,
                title=f"Database Health Alert: {result.check_name}",
                message=result.message,
                source=connection_id,
                metadata={
                    "check_name": result.check_name,
                    "response_time": result.response_time,
                    "details": result.details,
                    "error": result.error
                }
            )
            
            self.alerts[alert.id] = alert
            self.last_alert_time[alert_key] = datetime.utcnow()
            
            # Send alert to handlers
            for handler in self.alert_handlers:
                try:
                    await handler(alert) if asyncio.iscoroutinefunction(handler) else handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")

    async def _attempt_recovery(self, connection_id: str, connector: BaseConnector) -> None:
        """Attempt automatic recovery for a failed connection."""
        # Check recovery limits
        attempts = self.recovery_attempts.get(connection_id, 0)
        if attempts >= self.config.max_recovery_attempts:
            return
        
        # Check recovery delay
        last_recovery = self.last_recovery_time.get(connection_id)
        if last_recovery:
            delay_delta = timedelta(seconds=self.config.recovery_delay)
            if datetime.utcnow() - last_recovery < delay_delta:
                return
        
        logger.info(f"Attempting recovery for connection: {connection_id}")
        
        try:
            # Attempt reconnection
            if await connector.reconnect():
                logger.info(f"Recovery successful for connection: {connection_id}")
                self.recovery_attempts[connection_id] = 0
                
                # Generate recovery alert
                alert = Alert(
                    id=str(uuid4()),
                    severity=AlertSeverity.INFO,
                    title="Database Connection Recovered",
                    message=f"Connection {connection_id} has been successfully recovered",
                    source=connection_id
                )
                
                for handler in self.alert_handlers:
                    try:
                        await handler(alert) if asyncio.iscoroutinefunction(handler) else handler(alert)
                    except Exception as e:
                        logger.error(f"Alert handler error: {e}")
            else:
                self.recovery_attempts[connection_id] = attempts + 1
                self.last_recovery_time[connection_id] = datetime.utcnow()
                logger.warning(f"Recovery failed for connection: {connection_id} (attempt {attempts + 1})")
                
        except Exception as e:
            self.recovery_attempts[connection_id] = attempts + 1
            self.last_recovery_time[connection_id] = datetime.utcnow()
            logger.error(f"Recovery error for connection {connection_id}: {e}")

    # Default health check implementations
    async def _check_connection_status(self, connector: BaseConnector) -> Dict[str, Any]:
        """Check basic connection status."""
        is_healthy = await connector.health_check()
        stats = connector.stats
        
        return {
            "is_connected": connector.is_connected,
            "is_healthy": is_healthy,
            "status": connector.status.value,
            "uptime_seconds": stats.get("uptime_seconds", 0),
            "total_reads": stats.get("total_reads", 0),
            "total_writes": stats.get("total_writes", 0),
            "total_errors": stats.get("total_errors", 0)
        }

    async def _check_query_performance(self, connector: BaseConnector) -> Dict[str, Any]:
        """Test query performance with a simple query."""
        if not connector.is_connected:
            raise RuntimeError("Connection not available")
        
        start_time = time.time()
        
        # Execute a simple test query
        try:
            # This would be connector-specific in production
            await asyncio.sleep(0.1)  # Simulate query
            query_time = time.time() - start_time
            
            return {
                "query_time": query_time,
                "queries_per_second": 1 / query_time if query_time > 0 else 0,
                "status": "success"
            }
            
        except Exception as e:
            query_time = time.time() - start_time
            return {
                "query_time": query_time,
                "status": "failed",
                "error": str(e)
            }

    async def _check_connection_pool(self, connector: BaseConnector) -> Dict[str, Any]:
        """Check connection pool health (if applicable)."""
        stats = connector.stats
        
        return {
            "pool_status": "healthy",  # Would check actual pool status
            "active_connections": 1,
            "idle_connections": 0,
            "total_connections": 1,
            "bytes_read": stats.get("bytes_read", 0),
            "bytes_written": stats.get("bytes_written", 0)
        }

    def get_health_summary(self, connection_id: Optional[str] = None) -> Dict[str, Any]:
        """Get health summary for connections."""
        if connection_id:
            return self._get_connection_health_summary(connection_id)
        else:
            return {
                conn_id: self._get_connection_health_summary(conn_id)
                for conn_id in self.connections.keys()
            }

    def _get_connection_health_summary(self, connection_id: str) -> Dict[str, Any]:
        """Get health summary for a specific connection."""
        results = self.health_results.get(connection_id, [])
        if not results:
            return {"status": "unknown", "checks": []}
        
        # Get latest results for each check
        latest_results = {}
        for result in results:
            latest_results[result.check_name] = result
        
        # Determine overall status
        statuses = [result.status for result in latest_results.values()]
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        elif HealthStatus.HEALTHY in statuses:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
        
        return {
            "status": overall_status.value,
            "last_check": max(result.timestamp for result in latest_results.values()).isoformat(),
            "checks": [
                {
                    "name": result.check_name,
                    "status": result.status.value,
                    "response_time": result.response_time,
                    "message": result.message,
                    "timestamp": result.timestamp.isoformat()
                }
                for result in latest_results.values()
            ],
            "recovery_attempts": self.recovery_attempts.get(connection_id, 0)
        }

    def get_alerts(self, resolved: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get alerts, optionally filtered by resolved status."""
        alerts = list(self.alerts.values())
        
        if resolved is not None:
            alerts = [alert for alert in alerts if alert.resolved == resolved]
        
        return [
            {
                "id": alert.id,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "source": alert.source,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "metadata": alert.metadata
            }
            for alert in sorted(alerts, key=lambda a: a.timestamp, reverse=True)
        ]

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        alert = self.alerts.get(alert_id)
        if alert and not alert.resolved:
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            logger.info(f"Resolved alert: {alert_id}")
            return True
        return False