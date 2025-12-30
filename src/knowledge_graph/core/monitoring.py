"""
Monitoring and Logging Module for Knowledge Graph.

Provides comprehensive monitoring, metrics collection, health checks,
and structured logging for the knowledge graph system.
"""

import asyncio
import logging
import os
import sys
import time
import traceback
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar
from functools import wraps

# Structured logging setup
logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MetricType(Enum):
    """Metric types for monitoring."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Metric:
    """A single metric value."""
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
        }


@dataclass
class HealthCheck:
    """Health check result."""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class MetricsCollector:
    """
    Collects and manages metrics for the knowledge graph system.

    Supports counters, gauges, histograms, and summaries.
    """

    def __init__(self, max_history_per_metric: int = 1000):
        self.max_history = max_history_per_metric
        self._metrics: Dict[str, List[Metric]] = {}
        self._lock = asyncio.Lock()

    async def record_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
        description: str = "",
    ) -> None:
        """Record a counter metric (incremental)."""
        await self._record(name, value, MetricType.COUNTER, labels, description)

    async def record_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        description: str = "",
    ) -> None:
        """Record a gauge metric (point-in-time value)."""
        await self._record(name, value, MetricType.GAUGE, labels, description)

    async def record_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        description: str = "",
    ) -> None:
        """Record a histogram metric (distribution)."""
        await self._record(name, value, MetricType.HISTOGRAM, labels, description)

    async def _record(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        labels: Optional[Dict[str, str]],
        description: str,
    ) -> None:
        """Record a metric."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            labels=labels or {},
            description=description,
        )

        async with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []

            self._metrics[name].append(metric)

            # Trim history
            if len(self._metrics[name]) > self.max_history:
                self._metrics[name] = self._metrics[name][-self.max_history:]

    async def get_metric(
        self,
        name: str,
        since: Optional[datetime] = None,
    ) -> List[Metric]:
        """Get metrics by name."""
        async with self._lock:
            if name not in self._metrics:
                return []

            metrics = self._metrics[name]
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]

            return metrics

    async def get_all_metrics(
        self,
        since: Optional[datetime] = None,
    ) -> Dict[str, List[Metric]]:
        """Get all metrics."""
        async with self._lock:
            result = {}
            for name, metrics in self._metrics.items():
                if since:
                    result[name] = [m for m in metrics if m.timestamp >= since]
                else:
                    result[name] = list(metrics)
            return result

    async def get_latest(self, name: str) -> Optional[Metric]:
        """Get latest metric value."""
        async with self._lock:
            if name not in self._metrics or not self._metrics[name]:
                return None
            return self._metrics[name][-1]

    async def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        async with self._lock:
            summary = {
                "total_metrics": len(self._metrics),
                "metrics": {},
            }

            for name, metrics in self._metrics.items():
                if not metrics:
                    continue

                values = [m.value for m in metrics]
                summary["metrics"][name] = {
                    "count": len(values),
                    "latest": values[-1],
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "type": metrics[-1].metric_type.value,
                }

            return summary


class HealthChecker:
    """
    Manages health checks for the knowledge graph system.

    Supports synchronous and asynchronous health checks with configurable
    timeouts and intervals.
    """

    def __init__(
        self,
        check_timeout_seconds: float = 10.0,
        check_interval_seconds: float = 30.0,
    ):
        self.check_timeout = check_timeout_seconds
        self.check_interval = check_interval_seconds

        self._checks: Dict[str, Callable] = {}
        self._results: Dict[str, HealthCheck] = {}
        self._lock = asyncio.Lock()
        self._background_task: Optional[asyncio.Task] = None

    def register_check(self, name: str, check_func: Callable) -> None:
        """Register a health check function."""
        self._checks[name] = check_func
        logger.info(f"Registered health check: {name}")

    def unregister_check(self, name: str) -> bool:
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]
            if name in self._results:
                del self._results[name]
            logger.info(f"Unregistered health check: {name}")
            return True
        return False

    async def run_check(self, name: str) -> HealthCheck:
        """Run a single health check."""
        if name not in self._checks:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Health check not found",
            )

        check_func = self._checks[name]
        start_time = time.time()

        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(check_func):
                result = await asyncio.wait_for(
                    check_func(),
                    timeout=self.check_timeout,
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    check_func,
                )

            duration_ms = (time.time() - start_time) * 1000

            # Parse result
            if isinstance(result, HealthCheck):
                result.duration_ms = duration_ms
                return result
            elif isinstance(result, dict):
                return HealthCheck(
                    name=name,
                    status=HealthStatus(result.get("status", "healthy")),
                    message=result.get("message", ""),
                    details=result.get("details", {}),
                    duration_ms=duration_ms,
                )
            elif isinstance(result, bool):
                return HealthCheck(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    duration_ms=duration_ms,
                )
            else:
                return HealthCheck(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message=str(result) if result else "",
                    duration_ms=duration_ms,
                )

        except asyncio.TimeoutError:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.check_timeout}s",
                duration_ms=self.check_timeout * 1000,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e), "traceback": traceback.format_exc()},
                duration_ms=duration_ms,
            )

    async def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks."""
        results = {}

        for name in self._checks:
            result = await self.run_check(name)
            results[name] = result
            self._results[name] = result

        return results

    async def get_overall_status(self) -> HealthCheck:
        """Get overall system health status."""
        results = await self.run_all_checks()

        if not results:
            return HealthCheck(
                name="system",
                status=HealthStatus.UNKNOWN,
                message="No health checks registered",
            )

        # Aggregate status
        statuses = [r.status for r in results.values()]

        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
            message = "All systems operational"
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
            unhealthy = [n for n, r in results.items() if r.status == HealthStatus.UNHEALTHY]
            message = f"Unhealthy components: {', '.join(unhealthy)}"
        else:
            overall_status = HealthStatus.DEGRADED
            degraded = [n for n, r in results.items() if r.status != HealthStatus.HEALTHY]
            message = f"Degraded components: {', '.join(degraded)}"

        return HealthCheck(
            name="system",
            status=overall_status,
            message=message,
            details={name: r.to_dict() for name, r in results.items()},
        )

    async def start_background_checks(self) -> None:
        """Start background health check loop."""
        if self._background_task is None:
            self._background_task = asyncio.create_task(self._check_loop())
            logger.info("Started background health checks")

    async def stop_background_checks(self) -> None:
        """Stop background health check loop."""
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
            logger.info("Stopped background health checks")

    async def _check_loop(self) -> None:
        """Background health check loop."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self.run_all_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background health check error: {e}")


class StructuredLogger:
    """
    Structured logging with context and metadata.

    Provides consistent log formatting with correlation IDs,
    component labels, and structured data.
    """

    def __init__(
        self,
        component: str,
        default_level: LogLevel = LogLevel.INFO,
    ):
        self.component = component
        self.default_level = default_level
        self._context: Dict[str, Any] = {}
        self._logger = logging.getLogger(f"kg.{component}")

    def set_context(self, **kwargs) -> None:
        """Set context values for all subsequent logs."""
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """Clear context values."""
        self._context.clear()

    @asynccontextmanager
    async def context(self, **kwargs):
        """Context manager for temporary context."""
        old_context = dict(self._context)
        self._context.update(kwargs)
        try:
            yield
        finally:
            self._context = old_context

    def _format_message(
        self,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format log message with context."""
        data = {
            "component": self.component,
            "timestamp": datetime.now().isoformat(),
            **self._context,
            **(extra or {}),
        }

        # Format as structured log
        parts = [f"[{self.component}] {message}"]
        if data:
            context_str = " ".join(f"{k}={v}" for k, v in data.items() if k != "component")
            if context_str:
                parts.append(f"({context_str})")

        return " ".join(parts)

    def debug(self, message: str, **extra) -> None:
        """Log debug message."""
        self._logger.debug(self._format_message(message, extra))

    def info(self, message: str, **extra) -> None:
        """Log info message."""
        self._logger.info(self._format_message(message, extra))

    def warning(self, message: str, **extra) -> None:
        """Log warning message."""
        self._logger.warning(self._format_message(message, extra))

    def error(self, message: str, **extra) -> None:
        """Log error message."""
        self._logger.error(self._format_message(message, extra))

    def critical(self, message: str, **extra) -> None:
        """Log critical message."""
        self._logger.critical(self._format_message(message, extra))

    def exception(self, message: str, **extra) -> None:
        """Log exception with traceback."""
        self._logger.exception(self._format_message(message, extra))


class ErrorTracker:
    """
    Tracks and reports errors for the knowledge graph system.

    Provides error aggregation, rate limiting, and alerting.
    """

    def __init__(
        self,
        max_errors: int = 1000,
        alert_threshold: int = 10,
        alert_window_seconds: float = 60.0,
    ):
        self.max_errors = max_errors
        self.alert_threshold = alert_threshold
        self.alert_window = alert_window_seconds

        self._errors: List['ErrorRecord'] = []
        self._lock = asyncio.Lock()
        self._alert_callback: Optional[Callable] = None

    def set_alert_callback(self, callback: Callable) -> None:
        """Set callback for error alerts."""
        self._alert_callback = callback

    async def record_error(
        self,
        error: Exception,
        component: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an error."""
        record = ErrorRecord(
            error_type=type(error).__name__,
            message=str(error),
            component=component,
            operation=operation,
            context=context or {},
            traceback=traceback.format_exc(),
        )

        async with self._lock:
            self._errors.append(record)

            # Trim history
            if len(self._errors) > self.max_errors:
                self._errors = self._errors[-self.max_errors:]

            # Check for alert condition
            await self._check_alert()

        logger.error(
            f"Error recorded: {record.error_type} in {component}.{operation}: {record.message}"
        )

    async def _check_alert(self) -> None:
        """Check if error rate exceeds threshold."""
        cutoff = datetime.now() - timedelta(seconds=self.alert_window)
        recent_errors = [e for e in self._errors if e.timestamp >= cutoff]

        if len(recent_errors) >= self.alert_threshold and self._alert_callback:
            try:
                await self._alert_callback(
                    f"High error rate: {len(recent_errors)} errors in {self.alert_window}s",
                    recent_errors,
                )
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    async def get_errors(
        self,
        component: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List['ErrorRecord']:
        """Get recorded errors."""
        async with self._lock:
            errors = list(self._errors)

        # Filter
        if component:
            errors = [e for e in errors if e.component == component]
        if since:
            errors = [e for e in errors if e.timestamp >= since]

        # Sort by timestamp descending and limit
        errors.sort(key=lambda e: e.timestamp, reverse=True)
        return errors[:limit]

    async def get_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        async with self._lock:
            if not self._errors:
                return {"total_errors": 0, "by_component": {}, "by_type": {}}

            by_component = {}
            by_type = {}

            for error in self._errors:
                by_component[error.component] = by_component.get(error.component, 0) + 1
                by_type[error.error_type] = by_type.get(error.error_type, 0) + 1

            recent = [e for e in self._errors
                     if e.timestamp >= datetime.now() - timedelta(hours=1)]

            return {
                "total_errors": len(self._errors),
                "recent_errors_1h": len(recent),
                "by_component": by_component,
                "by_type": by_type,
                "latest": self._errors[-1].to_dict() if self._errors else None,
            }


@dataclass
class ErrorRecord:
    """Error record."""
    error_type: str
    message: str
    component: str
    operation: str
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "component": self.component,
            "operation": self.operation,
            "context": self.context,
            "traceback": self.traceback,
            "timestamp": self.timestamp.isoformat(),
        }


class SystemMonitor:
    """
    System-level monitoring for the knowledge graph.

    Collects resource usage, performance metrics, and system health.
    """

    def __init__(self):
        self._metrics_collector = MetricsCollector()
        self._health_checker = HealthChecker()
        self._error_tracker = ErrorTracker()
        self._start_time = datetime.now()

    @property
    def metrics(self) -> MetricsCollector:
        """Get metrics collector."""
        return self._metrics_collector

    @property
    def health(self) -> HealthChecker:
        """Get health checker."""
        return self._health_checker

    @property
    def errors(self) -> ErrorTracker:
        """Get error tracker."""
        return self._error_tracker

    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        import platform

        return {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            "start_time": self._start_time.isoformat(),
        }

    async def get_full_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        health = await self._health_checker.get_overall_status()
        metrics = await self._metrics_collector.get_summary()
        errors = await self._error_tracker.get_summary()
        system_info = await self.get_system_info()

        return {
            "status": health.status.value,
            "health": health.to_dict(),
            "metrics": metrics,
            "errors": errors,
            "system": system_info,
        }


# Global instances
_system_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """Get global system monitor instance."""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


def get_logger(component: str) -> StructuredLogger:
    """Get a structured logger for a component."""
    return StructuredLogger(component)


# Decorators for monitoring
T = TypeVar('T')


def monitored(
    component: str,
    operation: str,
    track_errors: bool = True,
    track_duration: bool = True,
):
    """Decorator for monitoring function execution."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitor = get_system_monitor()
            start_time = time.time()
            error_occurred = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error_occurred = e
                if track_errors:
                    await monitor.errors.record_error(
                        error=e,
                        component=component,
                        operation=operation,
                        context={"args": str(args)[:100], "kwargs": str(kwargs)[:100]},
                    )
                raise
            finally:
                if track_duration:
                    duration_ms = (time.time() - start_time) * 1000
                    await monitor.metrics.record_histogram(
                        name=f"{component}.{operation}.duration_ms",
                        value=duration_ms,
                        labels={"status": "error" if error_occurred else "success"},
                    )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.get_event_loop().run_until_complete(
                async_wrapper(*args, **kwargs)
            )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def configure_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """Configure logging for the knowledge graph system."""
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=handlers,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger.info(f"Logging configured at {level} level")
