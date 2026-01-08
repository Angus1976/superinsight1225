"""
Performance Monitor and Alerting System.

Provides comprehensive performance monitoring, analysis, and alerting
for data pull operations with real-time metrics and trend analysis.
"""

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of performance metrics."""
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    CONNECTION_HEALTH = "connection_health"
    QUEUE_DEPTH = "queue_depth"


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    """Trend direction indicators."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"


@dataclass
class MetricValue:
    """A single metric measurement."""
    metric_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Summary statistics for a metric."""
    metric_id: str
    metric_type: MetricType
    count: int
    min_value: float
    max_value: float
    avg_value: float
    median_value: float
    std_dev: float
    percentile_95: float
    percentile_99: float
    trend_direction: TrendDirection
    last_updated: datetime


@dataclass
class Alert:
    """Performance alert."""
    alert_id: str
    alert_level: AlertLevel
    metric_id: str
    metric_type: MetricType
    title: str
    message: str
    current_value: float
    threshold_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_type: MetricType
    warning_threshold: Optional[float] = None
    error_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    comparison_operator: str = ">"  # >, <, >=, <=, ==, !=
    evaluation_window_minutes: int = 5
    min_samples: int = 3


class PerformanceMonitorConfig(BaseModel):
    """Configuration for performance monitoring."""
    # Collection settings
    collection_interval_seconds: float = Field(default=10.0, ge=0.1)
    metric_retention_hours: int = Field(default=24, ge=1)
    
    # Analysis settings
    trend_analysis_window_minutes: int = Field(default=30, ge=1)
    anomaly_detection_enabled: bool = True
    anomaly_sensitivity: float = Field(default=2.0, ge=0.1)  # Standard deviations
    
    # Alerting settings
    enable_alerting: bool = True
    alert_cooldown_minutes: int = Field(default=15, ge=1)
    max_alerts_per_hour: int = Field(default=10, ge=1)
    
    # Thresholds
    default_thresholds: Dict[str, PerformanceThreshold] = Field(default_factory=dict)
    
    # Notification settings
    notification_channels: List[str] = Field(default_factory=list)


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system.
    
    Features:
    - Real-time metric collection
    - Statistical analysis and trend detection
    - Anomaly detection
    - Configurable alerting
    - Performance optimization recommendations
    """

    def __init__(self, config: PerformanceMonitorConfig):
        self.config = config
        self.monitor_id = str(uuid4())
        
        # Metric storage
        self.metrics: Dict[str, List[MetricValue]] = {}
        self.metric_summaries: Dict[str, MetricSummary] = {}
        
        # Alerting
        self.alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable] = []
        self.alert_counts: Dict[str, int] = {}  # Per hour
        self.last_alert_time: Dict[str, datetime] = {}
        
        # Thresholds
        self.thresholds: Dict[str, PerformanceThreshold] = {}
        self._setup_default_thresholds()
        
        # Monitoring state
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._analysis_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self.stats = {
            "metrics_collected": 0,
            "alerts_generated": 0,
            "anomalies_detected": 0,
            "started_at": None
        }

    def _setup_default_thresholds(self) -> None:
        """Setup default performance thresholds."""
        self.thresholds.update({
            "throughput_rps": PerformanceThreshold(
                metric_type=MetricType.THROUGHPUT,
                warning_threshold=100.0,
                error_threshold=50.0,
                critical_threshold=10.0,
                comparison_operator="<"
            ),
            "latency_ms": PerformanceThreshold(
                metric_type=MetricType.LATENCY,
                warning_threshold=1000.0,
                error_threshold=5000.0,
                critical_threshold=10000.0,
                comparison_operator=">"
            ),
            "error_rate_percent": PerformanceThreshold(
                metric_type=MetricType.ERROR_RATE,
                warning_threshold=1.0,
                error_threshold=5.0,
                critical_threshold=10.0,
                comparison_operator=">"
            ),
            "cpu_usage_percent": PerformanceThreshold(
                metric_type=MetricType.RESOURCE_USAGE,
                warning_threshold=70.0,
                error_threshold=85.0,
                critical_threshold=95.0,
                comparison_operator=">"
            ),
            "memory_usage_percent": PerformanceThreshold(
                metric_type=MetricType.RESOURCE_USAGE,
                warning_threshold=80.0,
                error_threshold=90.0,
                critical_threshold=95.0,
                comparison_operator=">"
            )
        })

    async def start(self) -> None:
        """Start the performance monitor."""
        if self._running:
            return
        
        logger.info("Starting performance monitor")
        self._running = True
        self.stats["started_at"] = datetime.utcnow()
        
        # Start monitoring tasks
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._analysis_task = asyncio.create_task(self._analysis_loop())

    async def stop(self) -> None:
        """Stop the performance monitor."""
        if not self._running:
            return
        
        logger.info("Stopping performance monitor")
        self._running = False
        self._shutdown_event.set()
        
        # Cancel tasks
        if self._monitor_task:
            self._monitor_task.cancel()
        if self._analysis_task:
            self._analysis_task.cancel()
        
        # Wait for tasks to complete
        tasks = [t for t in [self._monitor_task, self._analysis_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def record_metric(
        self,
        metric_id: str,
        metric_type: MetricType,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a performance metric.
        
        Args:
            metric_id: Unique identifier for the metric
            metric_type: Type of metric
            value: Metric value
            labels: Optional labels for the metric
            metadata: Optional metadata
        """
        metric = MetricValue(
            metric_id=metric_id,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels or {},
            metadata=metadata or {}
        )
        
        if metric_id not in self.metrics:
            self.metrics[metric_id] = []
        
        self.metrics[metric_id].append(metric)
        self.stats["metrics_collected"] += 1
        
        # Maintain retention limit
        self._cleanup_old_metrics(metric_id)
        
        # Check thresholds immediately for critical metrics
        asyncio.create_task(self._check_thresholds(metric_id, metric))

    def record_throughput(
        self,
        source: str,
        records_per_second: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record throughput metric."""
        self.record_metric(
            metric_id=f"throughput_{source}",
            metric_type=MetricType.THROUGHPUT,
            value=records_per_second,
            labels=labels,
            metadata={"source": source}
        )

    def record_latency(
        self,
        operation: str,
        latency_ms: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record latency metric."""
        self.record_metric(
            metric_id=f"latency_{operation}",
            metric_type=MetricType.LATENCY,
            value=latency_ms,
            labels=labels,
            metadata={"operation": operation}
        )

    def record_error_rate(
        self,
        source: str,
        error_rate_percent: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record error rate metric."""
        self.record_metric(
            metric_id=f"error_rate_{source}",
            metric_type=MetricType.ERROR_RATE,
            value=error_rate_percent,
            labels=labels,
            metadata={"source": source}
        )

    def record_resource_usage(
        self,
        resource: str,
        usage_percent: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record resource usage metric."""
        self.record_metric(
            metric_id=f"resource_{resource}",
            metric_type=MetricType.RESOURCE_USAGE,
            value=usage_percent,
            labels=labels,
            metadata={"resource": resource}
        )

    def set_threshold(
        self,
        metric_id: str,
        threshold: PerformanceThreshold
    ) -> None:
        """Set performance threshold for a metric."""
        self.thresholds[metric_id] = threshold
        logger.info(f"Set threshold for metric: {metric_id}")

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler."""
        self.alert_handlers.append(handler)

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._collect_system_metrics()
                await self._cleanup_old_data()
                await asyncio.sleep(self.config.collection_interval_seconds)
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(5)

    async def _analysis_loop(self) -> None:
        """Analysis and alerting loop."""
        while self._running:
            try:
                await self._update_metric_summaries()
                await self._detect_anomalies()
                await self._check_all_thresholds()
                await asyncio.sleep(60)  # Run analysis every minute
                
            except Exception as e:
                logger.error(f"Analysis loop error: {e}")
                await asyncio.sleep(10)

    async def _collect_system_metrics(self) -> None:
        """Collect system-level performance metrics."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_resource_usage("cpu", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_resource_usage("memory", memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.record_resource_usage("disk", disk_percent)
            
        except ImportError:
            # psutil not available, skip system metrics
            pass
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")

    async def _update_metric_summaries(self) -> None:
        """Update statistical summaries for all metrics."""
        for metric_id, metric_values in self.metrics.items():
            if not metric_values:
                continue
            
            # Get recent values for analysis
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            recent_values = [
                m.value for m in metric_values
                if m.timestamp > cutoff_time
            ]
            
            if len(recent_values) < 2:
                continue
            
            # Calculate statistics
            summary = MetricSummary(
                metric_id=metric_id,
                metric_type=metric_values[0].metric_type,
                count=len(recent_values),
                min_value=min(recent_values),
                max_value=max(recent_values),
                avg_value=statistics.mean(recent_values),
                median_value=statistics.median(recent_values),
                std_dev=statistics.stdev(recent_values) if len(recent_values) > 1 else 0.0,
                percentile_95=self._percentile(recent_values, 95),
                percentile_99=self._percentile(recent_values, 99),
                trend_direction=self._analyze_trend(recent_values),
                last_updated=datetime.utcnow()
            )
            
            self.metric_summaries[metric_id] = summary

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def _analyze_trend(self, values: List[float]) -> TrendDirection:
        """Analyze trend direction for a series of values."""
        if len(values) < 3:
            return TrendDirection.STABLE
        
        # Calculate linear regression slope
        n = len(values)
        x_values = list(range(n))
        
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return TrendDirection.STABLE
        
        slope = numerator / denominator
        
        # Calculate coefficient of variation for volatility
        std_dev = statistics.stdev(values)
        cv = std_dev / y_mean if y_mean != 0 else 0
        
        # Determine trend
        if cv > 0.3:  # High volatility
            return TrendDirection.VOLATILE
        elif slope > 0.1:
            return TrendDirection.IMPROVING
        elif slope < -0.1:
            return TrendDirection.DEGRADING
        else:
            return TrendDirection.STABLE

    async def _detect_anomalies(self) -> None:
        """Detect anomalies in metric values."""
        if not self.config.anomaly_detection_enabled:
            return
        
        for metric_id, summary in self.metric_summaries.items():
            if summary.count < 10:  # Need sufficient data
                continue
            
            # Get recent values
            recent_metrics = self.metrics.get(metric_id, [])
            if not recent_metrics:
                continue
            
            latest_value = recent_metrics[-1].value
            
            # Check if value is anomalous (outside N standard deviations)
            if summary.std_dev > 0:
                z_score = abs(latest_value - summary.avg_value) / summary.std_dev
                
                if z_score > self.config.anomaly_sensitivity:
                    await self._generate_anomaly_alert(
                        metric_id, latest_value, summary, z_score
                    )
                    self.stats["anomalies_detected"] += 1

    async def _generate_anomaly_alert(
        self,
        metric_id: str,
        value: float,
        summary: MetricSummary,
        z_score: float
    ) -> None:
        """Generate an alert for detected anomaly."""
        alert = Alert(
            alert_id=str(uuid4()),
            alert_level=AlertLevel.WARNING,
            metric_id=metric_id,
            metric_type=summary.metric_type,
            title=f"Anomaly Detected: {metric_id}",
            message=f"Value {value:.2f} is {z_score:.1f} standard deviations from mean {summary.avg_value:.2f}",
            current_value=value,
            threshold_value=summary.avg_value,
            triggered_at=datetime.utcnow(),
            metadata={
                "anomaly_type": "statistical",
                "z_score": z_score,
                "std_dev": summary.std_dev
            }
        )
        
        await self._send_alert(alert)

    async def _check_all_thresholds(self) -> None:
        """Check thresholds for all metrics."""
        for metric_id in self.metrics.keys():
            if metric_id in self.thresholds:
                recent_metrics = self.metrics[metric_id]
                if recent_metrics:
                    await self._check_thresholds(metric_id, recent_metrics[-1])

    async def _check_thresholds(self, metric_id: str, metric: MetricValue) -> None:
        """Check if metric value exceeds thresholds."""
        threshold = self.thresholds.get(metric_id)
        if not threshold:
            return
        
        # Check cooldown
        last_alert = self.last_alert_time.get(metric_id)
        if last_alert:
            cooldown_delta = timedelta(minutes=self.config.alert_cooldown_minutes)
            if datetime.utcnow() - last_alert < cooldown_delta:
                return
        
        # Check rate limiting
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        hour_key = f"{metric_id}_{current_hour}"
        if self.alert_counts.get(hour_key, 0) >= self.config.max_alerts_per_hour:
            return
        
        # Evaluate threshold
        alert_level = self._evaluate_threshold(metric.value, threshold)
        if alert_level:
            alert = Alert(
                alert_id=str(uuid4()),
                alert_level=alert_level,
                metric_id=metric_id,
                metric_type=metric.metric_type,
                title=f"Threshold Exceeded: {metric_id}",
                message=self._format_threshold_message(metric.value, threshold, alert_level),
                current_value=metric.value,
                threshold_value=self._get_threshold_value(threshold, alert_level),
                triggered_at=datetime.utcnow(),
                metadata={
                    "threshold_type": "configured",
                    "comparison_operator": threshold.comparison_operator
                }
            )
            
            await self._send_alert(alert)
            
            # Update rate limiting
            self.alert_counts[hour_key] = self.alert_counts.get(hour_key, 0) + 1
            self.last_alert_time[metric_id] = datetime.utcnow()

    def _evaluate_threshold(
        self,
        value: float,
        threshold: PerformanceThreshold
    ) -> Optional[AlertLevel]:
        """Evaluate if value exceeds threshold and return alert level."""
        op = threshold.comparison_operator
        
        # Check critical threshold first
        if threshold.critical_threshold is not None:
            if self._compare_values(value, threshold.critical_threshold, op):
                return AlertLevel.CRITICAL
        
        # Check error threshold
        if threshold.error_threshold is not None:
            if self._compare_values(value, threshold.error_threshold, op):
                return AlertLevel.ERROR
        
        # Check warning threshold
        if threshold.warning_threshold is not None:
            if self._compare_values(value, threshold.warning_threshold, op):
                return AlertLevel.WARNING
        
        return None

    def _compare_values(self, value: float, threshold: float, operator: str) -> bool:
        """Compare value against threshold using operator."""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        else:
            return False

    def _get_threshold_value(
        self,
        threshold: PerformanceThreshold,
        alert_level: AlertLevel
    ) -> float:
        """Get threshold value for alert level."""
        if alert_level == AlertLevel.CRITICAL and threshold.critical_threshold is not None:
            return threshold.critical_threshold
        elif alert_level == AlertLevel.ERROR and threshold.error_threshold is not None:
            return threshold.error_threshold
        elif alert_level == AlertLevel.WARNING and threshold.warning_threshold is not None:
            return threshold.warning_threshold
        else:
            return 0.0

    def _format_threshold_message(
        self,
        value: float,
        threshold: PerformanceThreshold,
        alert_level: AlertLevel
    ) -> str:
        """Format threshold alert message."""
        threshold_value = self._get_threshold_value(threshold, alert_level)
        return (
            f"Metric value {value:.2f} {threshold.comparison_operator} "
            f"threshold {threshold_value:.2f} ({alert_level.value} level)"
        )

    async def _send_alert(self, alert: Alert) -> None:
        """Send alert to registered handlers."""
        self.alerts[alert.alert_id] = alert
        self.stats["alerts_generated"] += 1
        
        logger.warning(f"Performance alert: {alert.title} - {alert.message}")
        
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def _cleanup_old_metrics(self, metric_id: str) -> None:
        """Clean up old metrics for a specific metric ID."""
        if metric_id not in self.metrics:
            return
        
        cutoff_time = datetime.utcnow() - timedelta(hours=self.config.metric_retention_hours)
        self.metrics[metric_id] = [
            metric for metric in self.metrics[metric_id]
            if metric.timestamp > cutoff_time
        ]

    async def _cleanup_old_data(self) -> None:
        """Clean up old metrics and alerts."""
        # Clean up metrics
        for metric_id in list(self.metrics.keys()):
            self._cleanup_old_metrics(metric_id)
            
            # Remove empty metric lists
            if not self.metrics[metric_id]:
                del self.metrics[metric_id]
        
        # Clean up old alerts
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        old_alerts = [
            alert_id for alert_id, alert in self.alerts.items()
            if alert.triggered_at < cutoff_time
        ]
        
        for alert_id in old_alerts:
            del self.alerts[alert_id]

    def get_metric_summary(self, metric_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for a specific metric."""
        summary = self.metric_summaries.get(metric_id)
        if summary:
            return {
                "metric_id": summary.metric_id,
                "metric_type": summary.metric_type.value,
                "count": summary.count,
                "min_value": summary.min_value,
                "max_value": summary.max_value,
                "avg_value": summary.avg_value,
                "median_value": summary.median_value,
                "std_dev": summary.std_dev,
                "percentile_95": summary.percentile_95,
                "percentile_99": summary.percentile_99,
                "trend_direction": summary.trend_direction.value,
                "last_updated": summary.last_updated.isoformat()
            }
        return None

    def get_recent_metrics(
        self,
        metric_id: str,
        minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get recent metrics for a specific metric ID."""
        if metric_id not in self.metrics:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_metrics = [
            metric for metric in self.metrics[metric_id]
            if metric.timestamp > cutoff_time
        ]
        
        return [
            {
                "value": metric.value,
                "timestamp": metric.timestamp.isoformat(),
                "labels": metric.labels,
                "metadata": metric.metadata
            }
            for metric in recent_metrics
        ]

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active (unresolved) alerts."""
        active_alerts = [
            alert for alert in self.alerts.values()
            if alert.resolved_at is None
        ]
        
        return [
            {
                "alert_id": alert.alert_id,
                "alert_level": alert.alert_level.value,
                "metric_id": alert.metric_id,
                "metric_type": alert.metric_type.value,
                "title": alert.title,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "triggered_at": alert.triggered_at.isoformat(),
                "acknowledged": alert.acknowledged,
                "metadata": alert.metadata
            }
            for alert in sorted(active_alerts, key=lambda a: a.triggered_at, reverse=True)
        ]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        alert = self.alerts.get(alert_id)
        if alert:
            alert.acknowledged = True
            logger.info(f"Alert acknowledged: {alert_id}")
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        alert = self.alerts.get(alert_id)
        if alert:
            alert.resolved_at = datetime.utcnow()
            logger.info(f"Alert resolved: {alert_id}")
            return True
        return False

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        return {
            "monitor_id": self.monitor_id,
            "running": self._running,
            "stats": self.stats,
            "metric_count": len(self.metrics),
            "active_alerts": len([a for a in self.alerts.values() if a.resolved_at is None]),
            "metric_summaries": {
                metric_id: self.get_metric_summary(metric_id)
                for metric_id in self.metric_summaries.keys()
            },
            "recent_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "alert_level": alert.alert_level.value,
                    "title": alert.title,
                    "triggered_at": alert.triggered_at.isoformat()
                }
                for alert in sorted(
                    list(self.alerts.values())[-10:],
                    key=lambda a: a.triggered_at,
                    reverse=True
                )
            ]
        }