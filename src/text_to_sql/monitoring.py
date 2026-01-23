"""
Text-to-SQL Monitoring and Alerting Module.

Provides comprehensive monitoring capabilities:
- Prometheus metrics export
- Slow query logging
- Performance alerting
- Accuracy monitoring

Implements Task 14 from text-to-sql-methods specification.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class MetricType(str, Enum):
    """Metric type for Prometheus export."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(str, Enum):
    """Alert severity level."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class GenerationMethod(str, Enum):
    """SQL generation method."""
    TEMPLATE = "template"
    LLM = "llm"
    HYBRID = "hybrid"
    THIRD_PARTY = "third_party"


# Default thresholds
DEFAULT_SLOW_QUERY_THRESHOLD_MS = 2000  # 2 seconds
DEFAULT_SUCCESS_RATE_THRESHOLD = 0.90  # 90%
DEFAULT_ACCURACY_THRESHOLD = 0.90  # 90%
DEFAULT_LATENCY_P99_THRESHOLD_MS = 5000  # 5 seconds


# =============================================================================
# Data Models
# =============================================================================

class MetricLabel(BaseModel):
    """Prometheus metric label."""
    name: str
    value: str


class PrometheusMetric(BaseModel):
    """Prometheus metric definition."""
    name: str
    type: MetricType
    help_text: str
    labels: List[str] = Field(default_factory=list)
    value: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HistogramBucket(BaseModel):
    """Histogram bucket for latency metrics."""
    le: float  # Less than or equal
    count: int = 0


class HistogramMetric(BaseModel):
    """Histogram metric with buckets."""
    name: str
    help_text: str
    labels: List[str] = Field(default_factory=list)
    buckets: List[HistogramBucket] = Field(default_factory=list)
    sum: float = 0.0
    count: int = 0


class SlowQueryLog(BaseModel):
    """Slow query log entry."""
    id: UUID = Field(default_factory=uuid4)
    query: str
    generated_sql: str
    method: GenerationMethod
    database_type: str
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Alert(BaseModel):
    """Alert definition."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    message: str
    metric_name: str
    threshold: float
    current_value: float
    labels: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class MethodMetrics(BaseModel):
    """Metrics for a specific generation method."""
    method: GenerationMethod
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_execution_time_ms: float = 0.0
    min_execution_time_ms: float = float('inf')
    max_execution_time_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def average_execution_time_ms(self) -> float:
        """Calculate average execution time."""
        if self.total_requests == 0:
            return 0.0
        return self.total_execution_time_ms / self.total_requests


class AccuracyMetrics(BaseModel):
    """Accuracy metrics for generated SQL."""
    period_start: datetime
    period_end: datetime
    syntax_correct: int = 0
    syntax_incorrect: int = 0
    semantic_correct: int = 0
    semantic_incorrect: int = 0
    execution_success: int = 0
    execution_failure: int = 0

    @property
    def syntax_accuracy(self) -> float:
        """Calculate syntax accuracy."""
        total = self.syntax_correct + self.syntax_incorrect
        if total == 0:
            return 0.0
        return self.syntax_correct / total

    @property
    def semantic_accuracy(self) -> float:
        """Calculate semantic accuracy."""
        total = self.semantic_correct + self.semantic_incorrect
        if total == 0:
            return 0.0
        return self.semantic_correct / total

    @property
    def execution_accuracy(self) -> float:
        """Calculate execution accuracy."""
        total = self.execution_success + self.execution_failure
        if total == 0:
            return 0.0
        return self.execution_success / total

    @property
    def overall_accuracy(self) -> float:
        """Calculate overall accuracy (average of all three)."""
        accuracies = [
            self.syntax_accuracy,
            self.semantic_accuracy,
            self.execution_accuracy,
        ]
        non_zero = [a for a in accuracies if a > 0]
        if not non_zero:
            return 0.0
        return sum(non_zero) / len(non_zero)


class MonitoringConfig(BaseModel):
    """Configuration for monitoring service."""
    slow_query_threshold_ms: float = DEFAULT_SLOW_QUERY_THRESHOLD_MS
    success_rate_threshold: float = DEFAULT_SUCCESS_RATE_THRESHOLD
    accuracy_threshold: float = DEFAULT_ACCURACY_THRESHOLD
    latency_p99_threshold_ms: float = DEFAULT_LATENCY_P99_THRESHOLD_MS
    max_slow_query_logs: int = 1000
    alert_cooldown_seconds: int = 300  # 5 minutes
    accuracy_check_interval_hours: int = 24


# =============================================================================
# Monitoring Service
# =============================================================================

class TextToSQLMonitoringService:
    """
    Comprehensive monitoring service for Text-to-SQL operations.

    Features:
    - Prometheus metrics export (counters, gauges, histograms)
    - Slow query logging and analysis
    - Performance alerting with configurable thresholds
    - Accuracy monitoring with periodic checks
    """

    def __init__(
        self,
        config: Optional[MonitoringConfig] = None,
        alert_callback: Optional[Callable[[Alert], None]] = None,
    ):
        """
        Initialize monitoring service.

        Args:
            config: Monitoring configuration
            alert_callback: Optional callback for alert notifications
        """
        self._config = config or MonitoringConfig()
        self._alert_callback = alert_callback
        self._lock = asyncio.Lock()

        # Metrics storage
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, HistogramMetric] = {}
        self._method_metrics: Dict[GenerationMethod, MethodMetrics] = {}

        # Slow query log (circular buffer)
        self._slow_query_logs: Deque[SlowQueryLog] = deque(
            maxlen=self._config.max_slow_query_logs
        )

        # Alerts
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_cooldowns: Dict[str, datetime] = {}

        # Accuracy tracking
        self._accuracy_metrics: Optional[AccuracyMetrics] = None
        self._accuracy_period_start: datetime = datetime.utcnow()

        # Latency tracking for percentiles
        self._latency_samples: Deque[float] = deque(maxlen=10000)

        # Initialize default metrics
        self._initialize_metrics()

        logger.info("TextToSQLMonitoringService initialized")

    def _initialize_metrics(self) -> None:
        """Initialize default Prometheus metrics."""
        # Counters
        self._counters = {
            "text2sql_requests_total": 0,
            "text2sql_requests_success": 0,
            "text2sql_requests_failure": 0,
            "text2sql_cache_hits": 0,
            "text2sql_cache_misses": 0,
            "text2sql_validation_failures": 0,
            "text2sql_slow_queries_total": 0,
        }

        # Gauges
        self._gauges = {
            "text2sql_active_connections": 0,
            "text2sql_cache_size": 0,
            "text2sql_success_rate": 0.0,
            "text2sql_average_latency_ms": 0.0,
            "text2sql_accuracy_syntax": 0.0,
            "text2sql_accuracy_semantic": 0.0,
            "text2sql_accuracy_execution": 0.0,
            "text2sql_accuracy_overall": 0.0,
        }

        # Histograms with default buckets (in milliseconds)
        default_buckets = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
        self._histograms["text2sql_request_duration_ms"] = HistogramMetric(
            name="text2sql_request_duration_ms",
            help_text="Request duration in milliseconds",
            buckets=[HistogramBucket(le=b) for b in default_buckets],
        )

        # Initialize method metrics
        for method in GenerationMethod:
            self._method_metrics[method] = MethodMetrics(method=method)

        # Initialize accuracy metrics
        self._accuracy_metrics = AccuracyMetrics(
            period_start=self._accuracy_period_start,
            period_end=self._accuracy_period_start + timedelta(hours=24),
        )

    # =========================================================================
    # Metrics Recording
    # =========================================================================

    async def record_request(
        self,
        method: GenerationMethod,
        execution_time_ms: float,
        success: bool,
        query: str,
        generated_sql: str,
        database_type: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a text-to-SQL request for monitoring.

        Args:
            method: Generation method used
            execution_time_ms: Execution time in milliseconds
            success: Whether the request was successful
            query: Original natural language query
            generated_sql: Generated SQL
            database_type: Target database type
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            correlation_id: Optional correlation ID
            metadata: Optional additional metadata
        """
        async with self._lock:
            # Update counters
            self._counters["text2sql_requests_total"] += 1
            if success:
                self._counters["text2sql_requests_success"] += 1
            else:
                self._counters["text2sql_requests_failure"] += 1

            # Update method metrics
            method_metric = self._method_metrics[method]
            method_metric.total_requests += 1
            method_metric.total_execution_time_ms += execution_time_ms
            method_metric.min_execution_time_ms = min(
                method_metric.min_execution_time_ms, execution_time_ms
            )
            method_metric.max_execution_time_ms = max(
                method_metric.max_execution_time_ms, execution_time_ms
            )
            if success:
                method_metric.successful_requests += 1
            else:
                method_metric.failed_requests += 1

            # Update histogram
            self._update_histogram(
                "text2sql_request_duration_ms",
                execution_time_ms,
            )

            # Track latency sample
            self._latency_samples.append(execution_time_ms)

            # Update gauges
            total = self._counters["text2sql_requests_total"]
            success_count = self._counters["text2sql_requests_success"]
            self._gauges["text2sql_success_rate"] = success_count / total if total > 0 else 0.0
            self._gauges["text2sql_average_latency_ms"] = self._calculate_average_latency()

            # Check for slow query
            if execution_time_ms > self._config.slow_query_threshold_ms:
                await self._log_slow_query(
                    query=query,
                    generated_sql=generated_sql,
                    method=method,
                    database_type=database_type,
                    execution_time_ms=execution_time_ms,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                    metadata=metadata or {},
                )

            # Check alerts
            await self._check_performance_alerts()

    async def record_cache_hit(self) -> None:
        """Record a cache hit."""
        async with self._lock:
            self._counters["text2sql_cache_hits"] += 1

    async def record_cache_miss(self) -> None:
        """Record a cache miss."""
        async with self._lock:
            self._counters["text2sql_cache_misses"] += 1

    async def record_validation_failure(self) -> None:
        """Record a validation failure."""
        async with self._lock:
            self._counters["text2sql_validation_failures"] += 1

    async def update_cache_size(self, size: int) -> None:
        """Update cache size gauge."""
        async with self._lock:
            self._gauges["text2sql_cache_size"] = float(size)

    async def update_active_connections(self, count: int) -> None:
        """Update active connections gauge."""
        async with self._lock:
            self._gauges["text2sql_active_connections"] = float(count)

    # =========================================================================
    # Accuracy Tracking
    # =========================================================================

    async def record_accuracy_result(
        self,
        syntax_correct: bool,
        semantic_correct: Optional[bool] = None,
        execution_success: Optional[bool] = None,
    ) -> None:
        """
        Record accuracy result for generated SQL.

        Args:
            syntax_correct: Whether SQL syntax is correct
            semantic_correct: Whether SQL semantically matches query
            execution_success: Whether SQL executed successfully
        """
        async with self._lock:
            if self._accuracy_metrics is None:
                return

            # Check if period has ended
            if datetime.utcnow() > self._accuracy_metrics.period_end:
                await self._rotate_accuracy_period()

            if syntax_correct:
                self._accuracy_metrics.syntax_correct += 1
            else:
                self._accuracy_metrics.syntax_incorrect += 1

            if semantic_correct is not None:
                if semantic_correct:
                    self._accuracy_metrics.semantic_correct += 1
                else:
                    self._accuracy_metrics.semantic_incorrect += 1

            if execution_success is not None:
                if execution_success:
                    self._accuracy_metrics.execution_success += 1
                else:
                    self._accuracy_metrics.execution_failure += 1

            # Update gauges
            self._gauges["text2sql_accuracy_syntax"] = self._accuracy_metrics.syntax_accuracy
            self._gauges["text2sql_accuracy_semantic"] = self._accuracy_metrics.semantic_accuracy
            self._gauges["text2sql_accuracy_execution"] = self._accuracy_metrics.execution_accuracy
            self._gauges["text2sql_accuracy_overall"] = self._accuracy_metrics.overall_accuracy

            # Check accuracy alert
            await self._check_accuracy_alert()

    async def _rotate_accuracy_period(self) -> None:
        """Rotate accuracy metrics to new period."""
        now = datetime.utcnow()
        self._accuracy_metrics = AccuracyMetrics(
            period_start=now,
            period_end=now + timedelta(hours=self._config.accuracy_check_interval_hours),
        )
        self._accuracy_period_start = now
        logger.info("Rotated accuracy metrics period")

    async def get_accuracy_metrics(self) -> Optional[AccuracyMetrics]:
        """Get current accuracy metrics."""
        return self._accuracy_metrics

    # =========================================================================
    # Slow Query Logging
    # =========================================================================

    async def _log_slow_query(
        self,
        query: str,
        generated_sql: str,
        method: GenerationMethod,
        database_type: str,
        execution_time_ms: float,
        user_id: Optional[str],
        tenant_id: Optional[str],
        correlation_id: Optional[str],
        metadata: Dict[str, Any],
    ) -> None:
        """Log a slow query."""
        self._counters["text2sql_slow_queries_total"] += 1

        log_entry = SlowQueryLog(
            query=query,
            generated_sql=generated_sql,
            method=method,
            database_type=database_type,
            execution_time_ms=execution_time_ms,
            user_id=user_id,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            metadata=metadata,
        )

        self._slow_query_logs.append(log_entry)

        logger.warning(
            f"Slow query detected: {execution_time_ms:.2f}ms "
            f"(threshold: {self._config.slow_query_threshold_ms}ms) "
            f"[method={method.value}, correlation_id={correlation_id}]"
        )

    async def get_slow_query_logs(
        self,
        limit: int = 100,
        method: Optional[GenerationMethod] = None,
        min_execution_time_ms: Optional[float] = None,
    ) -> List[SlowQueryLog]:
        """
        Get slow query logs with optional filtering.

        Args:
            limit: Maximum number of logs to return
            method: Filter by generation method
            min_execution_time_ms: Filter by minimum execution time

        Returns:
            List of slow query logs
        """
        logs = list(self._slow_query_logs)

        if method:
            logs = [log for log in logs if log.method == method]

        if min_execution_time_ms:
            logs = [log for log in logs if log.execution_time_ms >= min_execution_time_ms]

        # Sort by timestamp (most recent first)
        logs.sort(key=lambda x: x.timestamp, reverse=True)

        return logs[:limit]

    # =========================================================================
    # Alerting
    # =========================================================================

    async def _check_performance_alerts(self) -> None:
        """Check and trigger performance alerts."""
        # Success rate alert
        success_rate = self._gauges.get("text2sql_success_rate", 1.0)
        if success_rate < self._config.success_rate_threshold:
            await self._trigger_alert(
                name="low_success_rate",
                severity=AlertSeverity.WARNING,
                message=f"Success rate {success_rate:.2%} is below threshold {self._config.success_rate_threshold:.2%}",
                metric_name="text2sql_success_rate",
                threshold=self._config.success_rate_threshold,
                current_value=success_rate,
            )
        else:
            await self._resolve_alert("low_success_rate")

        # Latency P99 alert
        p99_latency = self._calculate_percentile(99)
        if p99_latency > self._config.latency_p99_threshold_ms:
            await self._trigger_alert(
                name="high_latency_p99",
                severity=AlertSeverity.WARNING,
                message=f"P99 latency {p99_latency:.2f}ms exceeds threshold {self._config.latency_p99_threshold_ms}ms",
                metric_name="text2sql_latency_p99_ms",
                threshold=self._config.latency_p99_threshold_ms,
                current_value=p99_latency,
            )
        else:
            await self._resolve_alert("high_latency_p99")

    async def _check_accuracy_alert(self) -> None:
        """Check and trigger accuracy alerts."""
        if self._accuracy_metrics is None:
            return

        overall_accuracy = self._accuracy_metrics.overall_accuracy
        if overall_accuracy > 0 and overall_accuracy < self._config.accuracy_threshold:
            await self._trigger_alert(
                name="low_accuracy",
                severity=AlertSeverity.ERROR,
                message=f"Overall accuracy {overall_accuracy:.2%} is below threshold {self._config.accuracy_threshold:.2%}",
                metric_name="text2sql_accuracy_overall",
                threshold=self._config.accuracy_threshold,
                current_value=overall_accuracy,
            )
        else:
            await self._resolve_alert("low_accuracy")

    async def _trigger_alert(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        metric_name: str,
        threshold: float,
        current_value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Trigger or update an alert."""
        # Check cooldown
        if name in self._alert_cooldowns:
            if datetime.utcnow() < self._alert_cooldowns[name]:
                return

        # Create or update alert
        if name in self._active_alerts:
            alert = self._active_alerts[name]
            alert.current_value = current_value
            alert.message = message
        else:
            alert = Alert(
                name=name,
                severity=severity,
                message=message,
                metric_name=metric_name,
                threshold=threshold,
                current_value=current_value,
                labels=labels or {},
            )
            self._active_alerts[name] = alert

            # Set cooldown
            self._alert_cooldowns[name] = datetime.utcnow() + timedelta(
                seconds=self._config.alert_cooldown_seconds
            )

            logger.warning(f"Alert triggered: {name} - {message}")

            # Call callback if provided
            if self._alert_callback:
                try:
                    self._alert_callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")

    async def _resolve_alert(self, name: str) -> None:
        """Resolve an active alert."""
        if name in self._active_alerts:
            alert = self._active_alerts[name]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()

            logger.info(f"Alert resolved: {name}")

            # Remove from active alerts
            del self._active_alerts[name]

            # Clear cooldown
            if name in self._alert_cooldowns:
                del self._alert_cooldowns[name]

    async def acknowledge_alert(self, alert_name: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an active alert.

        Args:
            alert_name: Name of the alert
            acknowledged_by: User acknowledging the alert

        Returns:
            True if alert was acknowledged
        """
        if alert_name in self._active_alerts:
            alert = self._active_alerts[alert_name]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            logger.info(f"Alert acknowledged: {alert_name} by {acknowledged_by}")
            return True
        return False

    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self._active_alerts.values())

    # =========================================================================
    # Prometheus Export
    # =========================================================================

    async def export_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus text format.

        Returns:
            Metrics in Prometheus exposition format
        """
        lines: List[str] = []

        # Export counters
        for name, value in self._counters.items():
            lines.append(f"# HELP {name} Counter metric")
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
            lines.append("")

        # Export gauges
        for name, value in self._gauges.items():
            lines.append(f"# HELP {name} Gauge metric")
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
            lines.append("")

        # Export histograms
        for name, histogram in self._histograms.items():
            lines.append(f"# HELP {name} {histogram.help_text}")
            lines.append(f"# TYPE {name} histogram")
            for bucket in histogram.buckets:
                lines.append(f'{name}_bucket{{le="{bucket.le}"}} {bucket.count}')
            lines.append(f'{name}_bucket{{le="+Inf"}} {histogram.count}')
            lines.append(f"{name}_sum {histogram.sum}")
            lines.append(f"{name}_count {histogram.count}")
            lines.append("")

        # Export method-specific metrics
        for method, metrics in self._method_metrics.items():
            method_label = method.value
            lines.append(f'text2sql_method_requests_total{{method="{method_label}"}} {metrics.total_requests}')
            lines.append(f'text2sql_method_success_rate{{method="{method_label}"}} {metrics.success_rate}')
            lines.append(f'text2sql_method_avg_latency_ms{{method="{method_label}"}} {metrics.average_execution_time_ms}')

        return "\n".join(lines)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _update_histogram(self, name: str, value: float) -> None:
        """Update histogram metric with new value."""
        if name not in self._histograms:
            return

        histogram = self._histograms[name]
        histogram.sum += value
        histogram.count += 1

        for bucket in histogram.buckets:
            if value <= bucket.le:
                bucket.count += 1

    def _calculate_average_latency(self) -> float:
        """Calculate average latency from samples."""
        if not self._latency_samples:
            return 0.0
        return sum(self._latency_samples) / len(self._latency_samples)

    def _calculate_percentile(self, percentile: int) -> float:
        """Calculate latency percentile from samples."""
        if not self._latency_samples:
            return 0.0

        sorted_samples = sorted(self._latency_samples)
        index = int(len(sorted_samples) * percentile / 100)
        index = min(index, len(sorted_samples) - 1)
        return sorted_samples[index]

    # =========================================================================
    # Statistics and Reports
    # =========================================================================

    async def get_method_statistics(self) -> Dict[str, MethodMetrics]:
        """Get statistics for all generation methods."""
        return {
            method.value: metrics
            for method, metrics in self._method_metrics.items()
        }

    async def get_overall_statistics(self) -> Dict[str, Any]:
        """Get overall monitoring statistics."""
        return {
            "total_requests": self._counters.get("text2sql_requests_total", 0),
            "success_rate": self._gauges.get("text2sql_success_rate", 0.0),
            "average_latency_ms": self._gauges.get("text2sql_average_latency_ms", 0.0),
            "p50_latency_ms": self._calculate_percentile(50),
            "p95_latency_ms": self._calculate_percentile(95),
            "p99_latency_ms": self._calculate_percentile(99),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "slow_queries_count": len(self._slow_query_logs),
            "active_alerts_count": len(self._active_alerts),
            "accuracy": {
                "syntax": self._gauges.get("text2sql_accuracy_syntax", 0.0),
                "semantic": self._gauges.get("text2sql_accuracy_semantic", 0.0),
                "execution": self._gauges.get("text2sql_accuracy_execution", 0.0),
                "overall": self._gauges.get("text2sql_accuracy_overall", 0.0),
            },
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        hits = self._counters.get("text2sql_cache_hits", 0)
        misses = self._counters.get("text2sql_cache_misses", 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return hits / total

    async def generate_performance_report(
        self,
        include_slow_queries: bool = True,
        include_alerts: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.

        Args:
            include_slow_queries: Include slow query details
            include_alerts: Include alert history

        Returns:
            Performance report dictionary
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "overview": await self.get_overall_statistics(),
            "method_breakdown": {
                method.value: {
                    "total_requests": metrics.total_requests,
                    "success_rate": metrics.success_rate,
                    "average_latency_ms": metrics.average_execution_time_ms,
                    "min_latency_ms": metrics.min_execution_time_ms if metrics.min_execution_time_ms != float('inf') else 0,
                    "max_latency_ms": metrics.max_execution_time_ms,
                }
                for method, metrics in self._method_metrics.items()
                if metrics.total_requests > 0
            },
        }

        if include_slow_queries:
            slow_queries = await self.get_slow_query_logs(limit=50)
            report["slow_queries"] = [
                {
                    "query": sq.query[:100],  # Truncate
                    "execution_time_ms": sq.execution_time_ms,
                    "method": sq.method.value,
                    "timestamp": sq.timestamp.isoformat(),
                }
                for sq in slow_queries
            ]

        if include_alerts:
            report["active_alerts"] = [
                {
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat(),
                }
                for alert in self._active_alerts.values()
            ]

        if self._accuracy_metrics:
            report["accuracy_details"] = {
                "period_start": self._accuracy_metrics.period_start.isoformat(),
                "period_end": self._accuracy_metrics.period_end.isoformat(),
                "syntax": {
                    "correct": self._accuracy_metrics.syntax_correct,
                    "incorrect": self._accuracy_metrics.syntax_incorrect,
                    "accuracy": self._accuracy_metrics.syntax_accuracy,
                },
                "semantic": {
                    "correct": self._accuracy_metrics.semantic_correct,
                    "incorrect": self._accuracy_metrics.semantic_incorrect,
                    "accuracy": self._accuracy_metrics.semantic_accuracy,
                },
                "execution": {
                    "success": self._accuracy_metrics.execution_success,
                    "failure": self._accuracy_metrics.execution_failure,
                    "accuracy": self._accuracy_metrics.execution_accuracy,
                },
            }

        return report
