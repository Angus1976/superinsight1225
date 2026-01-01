"""
Data Sync System Metrics Module.

Provides comprehensive Prometheus metrics for monitoring data synchronization:
- Sync throughput (records/second)
- Sync latency (milliseconds)
- Error rates and types
- Active connections and jobs
- Connector-specific metrics
- WebSocket metrics
- Conflict resolution metrics
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque
from enum import Enum
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class SyncMetricPoint:
    """A single sync metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HistogramBucket:
    """Histogram bucket for latency metrics."""
    le: float  # Less than or equal
    count: int = 0


class SyncMetrics:
    """
    Comprehensive metrics collection for data synchronization system.

    Collects and exposes metrics in Prometheus-compatible format.
    """

    # Standard histogram buckets for latency (in seconds)
    LATENCY_BUCKETS = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(self, max_points: int = 10000):
        self._lock = threading.Lock()
        self.max_points = max_points

        # Counters
        self._counters: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # Gauges
        self._gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # Histograms
        self._histograms: Dict[str, Dict[str, List[HistogramBucket]]] = defaultdict(dict)
        self._histogram_sums: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._histogram_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Time series for trend analysis
        self._time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))

        # Alert thresholds
        self._alert_thresholds: Dict[str, Dict[str, float]] = {}

        # Alert handlers
        self._alert_handlers: List[Callable] = []

        # Initialize standard metrics
        self._init_standard_metrics()

    def _init_standard_metrics(self):
        """Initialize standard sync system metrics."""
        # Throughput metrics
        self._register_counter("sync_records_total", "Total records synchronized")
        self._register_counter("sync_bytes_total", "Total bytes synchronized")
        self._register_counter("sync_operations_total", "Total sync operations")

        # Error metrics
        self._register_counter("sync_errors_total", "Total sync errors")
        self._register_counter("sync_retries_total", "Total retry attempts")

        # Latency metrics
        self._register_histogram("sync_latency_seconds", "Sync operation latency")
        self._register_histogram("connector_query_seconds", "Connector query latency")
        self._register_histogram("transform_duration_seconds", "Data transformation duration")

        # Active resources
        self._register_gauge("sync_active_jobs", "Number of active sync jobs")
        self._register_gauge("sync_active_connections", "Number of active connections")
        self._register_gauge("sync_queue_depth", "Sync queue depth")

        # Connector metrics
        self._register_gauge("connector_pool_size", "Connection pool size")
        self._register_gauge("connector_pool_available", "Available connections in pool")
        self._register_counter("connector_failures_total", "Total connector failures")

        # WebSocket metrics
        self._register_gauge("websocket_active_connections", "Active WebSocket connections")
        self._register_counter("websocket_messages_total", "Total WebSocket messages")
        self._register_counter("websocket_backpressure_events", "Backpressure events")

        # Conflict resolution metrics
        self._register_counter("conflict_detected_total", "Total conflicts detected")
        self._register_counter("conflict_resolved_total", "Total conflicts resolved")
        self._register_gauge("conflict_resolution_rate", "Conflict resolution success rate")

        # Set default alert thresholds
        self._set_alert_thresholds("sync_latency_seconds", {"warning": 1.0, "critical": 5.0})
        self._set_alert_thresholds("sync_errors_total", {"warning": 10, "critical": 100})
        self._set_alert_thresholds("sync_queue_depth", {"warning": 1000, "critical": 5000})

    def _register_counter(self, name: str, description: str):
        """Register a counter metric."""
        logger.debug(f"Registered counter: {name} - {description}")

    def _register_gauge(self, name: str, description: str):
        """Register a gauge metric."""
        logger.debug(f"Registered gauge: {name} - {description}")

    def _register_histogram(self, name: str, description: str):
        """Register a histogram metric."""
        logger.debug(f"Registered histogram: {name} - {description}")

    def _set_alert_thresholds(self, metric: str, thresholds: Dict[str, float]):
        """Set alert thresholds for a metric."""
        self._alert_thresholds[metric] = thresholds

    def _labels_key(self, labels: Dict[str, str]) -> str:
        """Generate a key from labels dict."""
        if not labels:
            return ""
        return "|".join(f"{k}={v}" for k, v in sorted(labels.items()))

    # Counter methods
    def inc_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter."""
        with self._lock:
            key = self._labels_key(labels or {})
            self._counters[name][key] += value
            self._record_time_series(name, self._counters[name][key], labels)

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value."""
        with self._lock:
            key = self._labels_key(labels or {})
            return self._counters[name].get(key, 0.0)

    # Gauge methods
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge value."""
        with self._lock:
            key = self._labels_key(labels or {})
            self._gauges[name][key] = value
            self._record_time_series(name, value, labels)
            self._check_alerts(name, value)

    def inc_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a gauge."""
        with self._lock:
            key = self._labels_key(labels or {})
            self._gauges[name][key] += value

    def dec_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Decrement a gauge."""
        with self._lock:
            key = self._labels_key(labels or {})
            self._gauges[name][key] -= value

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        with self._lock:
            key = self._labels_key(labels or {})
            return self._gauges[name].get(key, 0.0)

    # Histogram methods
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value for histogram."""
        with self._lock:
            key = self._labels_key(labels or {})

            # Initialize buckets if needed
            if key not in self._histograms[name]:
                self._histograms[name][key] = [
                    HistogramBucket(le=b) for b in self.LATENCY_BUCKETS
                ]
                self._histograms[name][key].append(HistogramBucket(le=float('inf')))

            # Update buckets
            for bucket in self._histograms[name][key]:
                if value <= bucket.le:
                    bucket.count += 1

            # Update sum and count
            self._histogram_sums[name][key] += value
            self._histogram_counts[name][key] += 1

            self._record_time_series(name, value, labels)
            self._check_alerts(name, value)

    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get histogram statistics."""
        with self._lock:
            key = self._labels_key(labels or {})
            count = self._histogram_counts[name].get(key, 0)
            total = self._histogram_sums[name].get(key, 0.0)

            return {
                "count": count,
                "sum": total,
                "avg": total / count if count > 0 else 0.0,
                "buckets": [
                    {"le": b.le, "count": b.count}
                    for b in self._histograms[name].get(key, [])
                ]
            }

    def _record_time_series(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a value in time series for trend analysis."""
        point = SyncMetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels or {}
        )
        self._time_series[name].append(point)

    def _check_alerts(self, name: str, value: float):
        """Check if value triggers any alerts."""
        if name not in self._alert_thresholds:
            return

        thresholds = self._alert_thresholds[name]
        severity = None

        if "critical" in thresholds and value >= thresholds["critical"]:
            severity = "critical"
        elif "warning" in thresholds and value >= thresholds["warning"]:
            severity = "warning"

        if severity and self._alert_handlers:
            alert = {
                "metric": name,
                "value": value,
                "threshold": thresholds.get(severity),
                "severity": severity,
                "timestamp": time.time()
            }
            for handler in self._alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")

    def add_alert_handler(self, handler: Callable):
        """Add an alert handler callback."""
        self._alert_handlers.append(handler)

    # Convenience methods for sync-specific metrics
    def record_sync_operation(
        self,
        connector_type: str,
        operation: str,
        records: int,
        bytes_count: int,
        duration_seconds: float,
        success: bool
    ):
        """Record a complete sync operation."""
        labels = {"connector": connector_type, "operation": operation}

        self.inc_counter("sync_operations_total", labels=labels)
        self.inc_counter("sync_records_total", records, labels=labels)
        self.inc_counter("sync_bytes_total", bytes_count, labels=labels)
        self.observe_histogram("sync_latency_seconds", duration_seconds, labels=labels)

        if not success:
            self.inc_counter("sync_errors_total", labels=labels)

    def record_connector_query(
        self,
        connector_type: str,
        query_type: str,
        duration_seconds: float,
        success: bool
    ):
        """Record a connector query."""
        labels = {"connector": connector_type, "query_type": query_type}

        self.observe_histogram("connector_query_seconds", duration_seconds, labels=labels)

        if not success:
            self.inc_counter("connector_failures_total", labels=labels)

    def record_conflict(
        self,
        conflict_type: str,
        resolution_strategy: str,
        resolved: bool
    ):
        """Record a conflict detection and resolution."""
        labels = {"type": conflict_type, "strategy": resolution_strategy}

        self.inc_counter("conflict_detected_total", labels=labels)

        if resolved:
            self.inc_counter("conflict_resolved_total", labels=labels)

        # Update resolution rate
        detected = self.get_counter("conflict_detected_total", labels=labels)
        resolved_count = self.get_counter("conflict_resolved_total", labels=labels)
        rate = resolved_count / detected if detected > 0 else 1.0
        self.set_gauge("conflict_resolution_rate", rate, labels=labels)

    def record_websocket_message(self, message_type: str, direction: str):
        """Record a WebSocket message."""
        labels = {"type": message_type, "direction": direction}
        self.inc_counter("websocket_messages_total", labels=labels)

    def record_backpressure_event(self, strategy: str):
        """Record a backpressure event."""
        labels = {"strategy": strategy}
        self.inc_counter("websocket_backpressure_events", labels=labels)

    def update_active_jobs(self, count: int):
        """Update active jobs gauge."""
        self.set_gauge("sync_active_jobs", count)

    def update_active_connections(self, count: int):
        """Update active connections gauge."""
        self.set_gauge("sync_active_connections", count)

    def update_queue_depth(self, depth: int):
        """Update queue depth gauge."""
        self.set_gauge("sync_queue_depth", depth)

    def update_connection_pool(self, connector: str, size: int, available: int):
        """Update connection pool metrics."""
        labels = {"connector": connector}
        self.set_gauge("connector_pool_size", size, labels=labels)
        self.set_gauge("connector_pool_available", available, labels=labels)

    def update_websocket_connections(self, count: int):
        """Update WebSocket connections gauge."""
        self.set_gauge("websocket_active_connections", count)

    # Export methods
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in a dictionary format."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: {
                        key: self.get_histogram_stats(name, self._parse_labels_key(key))
                        for key in keys
                    }
                    for name, keys in self._histograms.items()
                }
            }

    def _parse_labels_key(self, key: str) -> Dict[str, str]:
        """Parse labels key back to dict."""
        if not key:
            return {}
        return dict(pair.split("=") for pair in key.split("|"))

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []

        with self._lock:
            # Export counters
            for name, values in self._counters.items():
                for labels_key, value in values.items():
                    labels_str = self._format_labels(labels_key)
                    lines.append(f"{name}{labels_str} {value}")

            # Export gauges
            for name, values in self._gauges.items():
                for labels_key, value in values.items():
                    labels_str = self._format_labels(labels_key)
                    lines.append(f"{name}{labels_str} {value}")

            # Export histograms
            for name, label_buckets in self._histograms.items():
                for labels_key, buckets in label_buckets.items():
                    for bucket in buckets:
                        le_str = "+Inf" if bucket.le == float('inf') else str(bucket.le)
                        labels_str = self._format_labels(labels_key, {"le": le_str})
                        lines.append(f"{name}_bucket{labels_str} {bucket.count}")

                    labels_str = self._format_labels(labels_key)
                    lines.append(f"{name}_sum{labels_str} {self._histogram_sums[name].get(labels_key, 0.0)}")
                    lines.append(f"{name}_count{labels_str} {self._histogram_counts[name].get(labels_key, 0)}")

        return "\n".join(lines)

    def _format_labels(self, labels_key: str, extra: Optional[Dict[str, str]] = None) -> str:
        """Format labels for Prometheus output."""
        labels = self._parse_labels_key(labels_key)
        if extra:
            labels.update(extra)

        if not labels:
            return ""

        pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(pairs) + "}"

    def get_throughput_stats(self, window_seconds: int = 60) -> Dict[str, float]:
        """Calculate throughput statistics for the last window."""
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            records_series = self._time_series.get("sync_records_total", deque())

            # Filter points in window
            points_in_window = [p for p in records_series if p.timestamp >= cutoff]

            if len(points_in_window) < 2:
                return {"records_per_second": 0.0, "bytes_per_second": 0.0}

            # Calculate rate
            first = points_in_window[0]
            last = points_in_window[-1]
            time_diff = last.timestamp - first.timestamp
            value_diff = last.value - first.value

            rate = value_diff / time_diff if time_diff > 0 else 0.0

            return {
                "records_per_second": rate,
                "window_seconds": window_seconds,
                "total_records": last.value
            }

    def get_latency_percentiles(self, name: str = "sync_latency_seconds") -> Dict[str, float]:
        """Calculate latency percentiles from time series."""
        with self._lock:
            series = self._time_series.get(name, deque())

            if not series:
                return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}

            values = sorted([p.value for p in series])
            n = len(values)

            return {
                "p50": values[int(n * 0.5)] if n > 0 else 0.0,
                "p90": values[int(n * 0.9)] if n > 0 else 0.0,
                "p95": values[int(n * 0.95)] if n > 0 else 0.0,
                "p99": values[int(n * 0.99)] if n > 0 else 0.0,
                "min": values[0] if values else 0.0,
                "max": values[-1] if values else 0.0,
                "count": n
            }

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._histogram_sums.clear()
            self._histogram_counts.clear()
            self._time_series.clear()


# Global metrics instance
sync_metrics = SyncMetrics()


# Decorator for timing sync operations
def timed_sync_operation(connector_type: str, operation: str):
    """Decorator to time sync operations."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            success = True
            records = 0
            bytes_count = 0

            try:
                result = await func(*args, **kwargs)
                if isinstance(result, dict):
                    records = result.get("records", 0)
                    bytes_count = result.get("bytes", 0)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start
                sync_metrics.record_sync_operation(
                    connector_type=connector_type,
                    operation=operation,
                    records=records,
                    bytes_count=bytes_count,
                    duration_seconds=duration,
                    success=success
                )

        def sync_wrapper(*args, **kwargs):
            start = time.time()
            success = True
            records = 0
            bytes_count = 0

            try:
                result = func(*args, **kwargs)
                if isinstance(result, dict):
                    records = result.get("records", 0)
                    bytes_count = result.get("bytes", 0)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start
                sync_metrics.record_sync_operation(
                    connector_type=connector_type,
                    operation=operation,
                    records=records,
                    bytes_count=bytes_count,
                    duration_seconds=duration,
                    success=success
                )

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
