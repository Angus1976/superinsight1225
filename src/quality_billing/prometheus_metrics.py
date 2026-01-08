"""
Prometheus Metrics Collection for Quality Billing Loop System.

Collects and exports metrics for:
- Work time tracking and quality analysis
- Billing calculations and invoice generation
- Quality assessment and improvement
- Performance evaluation and scoring
"""

import time
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
import json

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Represents a metric value with timestamp and labels."""
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class PrometheusMetricsCollector:
    """
    Collects and manages Prometheus metrics for the quality billing system.
    
    Provides thread-safe metric collection with support for:
    - Counters (monotonically increasing values)
    - Gauges (current values that can go up or down)
    - Histograms (distribution of values)
    - Custom business metrics
    """

    def __init__(self):
        self._lock = threading.RLock()
        
        # Metric storage
        self._counters: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        # Metric metadata
        self._metric_help: Dict[str, str] = {}
        self._metric_types: Dict[str, str] = {}
        
        # Time series data for trend analysis
        self._time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Initialize standard metrics
        self._initialize_standard_metrics()

    def _initialize_standard_metrics(self):
        """Initialize standard quality billing metrics."""
        
        # Work Time Metrics
        self.register_counter(
            "quality_billing_work_time_total_seconds",
            "Total work time in seconds by user and project"
        )
        self.register_counter(
            "quality_billing_effective_work_time_seconds",
            "Effective work time excluding breaks and interruptions"
        )
        self.register_gauge(
            "quality_billing_current_active_users",
            "Number of currently active users"
        )
        
        # Quality Metrics
        self.register_gauge(
            "quality_billing_quality_score",
            "Current quality score by user and task type"
        )
        self.register_counter(
            "quality_billing_quality_assessments_total",
            "Total number of quality assessments performed"
        )
        self.register_histogram(
            "quality_billing_quality_improvement_rate",
            "Distribution of quality improvement rates"
        )
        
        # Billing Metrics
        self.register_counter(
            "quality_billing_invoices_generated_total",
            "Total number of invoices generated"
        )
        self.register_counter(
            "quality_billing_total_amount_cents",
            "Total billing amount in cents"
        )
        self.register_gauge(
            "quality_billing_average_hourly_rate_cents",
            "Average hourly rate in cents by quality level"
        )
        
        # Performance Metrics
        self.register_gauge(
            "quality_billing_performance_score",
            "Current performance score by user"
        )
        self.register_counter(
            "quality_billing_tasks_completed_total",
            "Total number of tasks completed"
        )
        self.register_histogram(
            "quality_billing_task_completion_time_seconds",
            "Distribution of task completion times"
        )
        
        # System Metrics
        self.register_gauge(
            "quality_billing_active_sessions",
            "Number of active user sessions"
        )
        self.register_counter(
            "quality_billing_api_requests_total",
            "Total number of API requests by endpoint"
        )
        self.register_histogram(
            "quality_billing_api_response_time_seconds",
            "API response time distribution"
        )

    def register_counter(self, name: str, help_text: str):
        """Register a counter metric."""
        with self._lock:
            self._metric_help[name] = help_text
            self._metric_types[name] = "counter"

    def register_gauge(self, name: str, help_text: str):
        """Register a gauge metric."""
        with self._lock:
            self._metric_help[name] = help_text
            self._metric_types[name] = "gauge"

    def register_histogram(self, name: str, help_text: str):
        """Register a histogram metric."""
        with self._lock:
            self._metric_help[name] = help_text
            self._metric_types[name] = "histogram"

    def _labels_to_key(self, labels: Optional[Dict[str, str]] = None) -> str:
        """Convert labels dict to a string key."""
        if not labels:
            return ""
        
        # Sort labels for consistent keys
        sorted_items = sorted(labels.items())
        return ",".join(f"{k}={v}" for k, v in sorted_items)

    def _key_to_labels(self, key: str) -> Dict[str, str]:
        """Convert string key back to labels dict."""
        if not key:
            return {}
        
        labels = {}
        for item in key.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                labels[k] = v
        return labels

    # Counter methods
    def inc_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            key = self._labels_to_key(labels)
            self._counters[name][key] += value
            
            # Store time series data
            timestamp = time.time()
            self._time_series[f"{name}:{key}"].append(MetricValue(
                value=self._counters[name][key],
                timestamp=timestamp,
                labels=labels or {}
            ))

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        with self._lock:
            key = self._labels_to_key(labels)
            return self._counters[name].get(key, 0.0)

    # Gauge methods
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        with self._lock:
            key = self._labels_to_key(labels)
            self._gauges[name][key] = value
            
            # Store time series data
            timestamp = time.time()
            self._time_series[f"{name}:{key}"].append(MetricValue(
                value=value,
                timestamp=timestamp,
                labels=labels or {}
            ))

    def inc_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a gauge metric."""
        with self._lock:
            key = self._labels_to_key(labels)
            self._gauges[name][key] = self._gauges[name].get(key, 0.0) + value
            
            # Store time series data
            timestamp = time.time()
            self._time_series[f"{name}:{key}"].append(MetricValue(
                value=self._gauges[name][key],
                timestamp=timestamp,
                labels=labels or {}
            ))

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        with self._lock:
            key = self._labels_to_key(labels)
            return self._gauges[name].get(key, 0.0)

    # Histogram methods
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Add an observation to a histogram."""
        with self._lock:
            key = self._labels_to_key(labels)
            self._histograms[name][key].append(value)
            
            # Keep only recent observations (last 1000)
            if len(self._histograms[name][key]) > 1000:
                self._histograms[name][key] = self._histograms[name][key][-1000:]
            
            # Store time series data
            timestamp = time.time()
            self._time_series[f"{name}:{key}"].append(MetricValue(
                value=value,
                timestamp=timestamp,
                labels=labels or {}
            ))

    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        with self._lock:
            key = self._labels_to_key(labels)
            values = self._histograms[name].get(key, [])
            
            if not values:
                return {"count": 0, "sum": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
            
            sorted_values = sorted(values)
            count = len(sorted_values)
            total = sum(sorted_values)
            
            def percentile(p):
                if count == 0:
                    return 0
                index = int(count * p / 100)
                return sorted_values[min(index, count - 1)]
            
            return {
                "count": count,
                "sum": total,
                "avg": total / count,
                "p50": percentile(50),
                "p95": percentile(95),
                "p99": percentile(99)
            }

    # Business-specific metric methods
    def record_work_session(
        self,
        user_id: str,
        project_id: str,
        duration_seconds: float,
        effective_duration_seconds: float,
        quality_score: float
    ):
        """Record a work session with quality metrics."""
        labels = {"user_id": user_id, "project_id": project_id}
        
        # Work time metrics
        self.inc_counter("quality_billing_work_time_total_seconds", duration_seconds, labels)
        self.inc_counter("quality_billing_effective_work_time_seconds", effective_duration_seconds, labels)
        
        # Quality metrics
        self.set_gauge("quality_billing_quality_score", quality_score, labels)
        self.inc_counter("quality_billing_quality_assessments_total", 1.0, labels)
        
        # Performance metrics
        efficiency = effective_duration_seconds / duration_seconds if duration_seconds > 0 else 0
        self.set_gauge("quality_billing_work_efficiency", efficiency, labels)

    def record_billing_event(
        self,
        user_id: str,
        project_id: str,
        amount_cents: int,
        quality_level: str,
        task_type: str
    ):
        """Record a billing event."""
        labels = {
            "user_id": user_id,
            "project_id": project_id,
            "quality_level": quality_level,
            "task_type": task_type
        }
        
        # Billing metrics
        self.inc_counter("quality_billing_invoices_generated_total", 1.0, labels)
        self.inc_counter("quality_billing_total_amount_cents", amount_cents, labels)
        
        # Calculate hourly rate (assuming 1 hour for simplicity)
        self.set_gauge("quality_billing_average_hourly_rate_cents", amount_cents, labels)

    def record_performance_evaluation(
        self,
        user_id: str,
        performance_score: float,
        tasks_completed: int,
        average_completion_time: float
    ):
        """Record performance evaluation metrics."""
        labels = {"user_id": user_id}
        
        # Performance metrics
        self.set_gauge("quality_billing_performance_score", performance_score, labels)
        self.inc_counter("quality_billing_tasks_completed_total", tasks_completed, labels)
        self.observe_histogram("quality_billing_task_completion_time_seconds", average_completion_time, labels)

    def record_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_seconds: float
    ):
        """Record API request metrics."""
        labels = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        }
        
        # API metrics
        self.inc_counter("quality_billing_api_requests_total", 1.0, labels)
        self.observe_histogram("quality_billing_api_response_time_seconds", response_time_seconds, labels)

    def update_active_sessions(self, count: int):
        """Update active sessions count."""
        self.set_gauge("quality_billing_active_sessions", count)

    def update_active_users(self, count: int):
        """Update active users count."""
        self.set_gauge("quality_billing_current_active_users", count)

    # Data export methods
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metric values."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: {
                        key: self.get_histogram_stats(name, self._key_to_labels(key))
                        for key in label_dict.keys()
                    }
                    for name, label_dict in self._histograms.items()
                }
            }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        with self._lock:
            # Export counters
            for name, label_dict in self._counters.items():
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                    lines.append(f"# TYPE {name} counter")
                
                for key, value in label_dict.items():
                    if key:
                        labels_str = "{" + key.replace("=", '="').replace(",", '", ') + '"}'
                        lines.append(f"{name}{labels_str} {value}")
                    else:
                        lines.append(f"{name} {value}")
            
            # Export gauges
            for name, label_dict in self._gauges.items():
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                    lines.append(f"# TYPE {name} gauge")
                
                for key, value in label_dict.items():
                    if key:
                        labels_str = "{" + key.replace("=", '="').replace(",", '", ') + '"}'
                        lines.append(f"{name}{labels_str} {value}")
                    else:
                        lines.append(f"{name} {value}")
            
            # Export histograms
            for name, label_dict in self._histograms.items():
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                    lines.append(f"# TYPE {name} histogram")
                
                for key in label_dict.keys():
                    stats = self.get_histogram_stats(name, self._key_to_labels(key))
                    
                    if key:
                        base_labels = key.replace("=", '="').replace(",", '", ') + '"'
                        lines.append(f"{name}_count{{{base_labels}}} {stats['count']}")
                        lines.append(f"{name}_sum{{{base_labels}}} {stats['sum']}")
                        lines.append(f"{name}_bucket{{le=\"0.5\", {base_labels}}} {stats['p50']}")
                        lines.append(f"{name}_bucket{{le=\"0.95\", {base_labels}}} {stats['p95']}")
                        lines.append(f"{name}_bucket{{le=\"0.99\", {base_labels}}} {stats['p99']}")
                        lines.append(f"{name}_bucket{{le=\"+Inf\", {base_labels}}} {stats['count']}")
                    else:
                        lines.append(f"{name}_count {stats['count']}")
                        lines.append(f"{name}_sum {stats['sum']}")
                        lines.append(f"{name}_bucket{{le=\"0.5\"}} {stats['p50']}")
                        lines.append(f"{name}_bucket{{le=\"0.95\"}} {stats['p95']}")
                        lines.append(f"{name}_bucket{{le=\"0.99\"}} {stats['p99']}")
                        lines.append(f"{name}_bucket{{le=\"+Inf\"}} {stats['count']}")
        
        return "\n".join(lines) + "\n"

    def get_time_series(
        self,
        metric_name: str,
        labels: Optional[Dict[str, str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[MetricValue]:
        """Get time series data for a metric."""
        key = self._labels_to_key(labels)
        series_key = f"{metric_name}:{key}"
        
        with self._lock:
            series = list(self._time_series.get(series_key, []))
        
        # Filter by time range if specified
        if start_time or end_time:
            start_ts = start_time.timestamp() if start_time else 0
            end_ts = end_time.timestamp() if end_time else float('inf')
            
            series = [
                point for point in series
                if start_ts <= point.timestamp <= end_ts
            ]
        
        return series

    def get_metric_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get a summary of metrics over the specified time period."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        summary = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "work_time": {},
            "quality": {},
            "billing": {},
            "performance": {},
            "system": {}
        }
        
        # Work time summary
        total_work_time = self.get_counter("quality_billing_work_time_total_seconds")
        effective_work_time = self.get_counter("quality_billing_effective_work_time_seconds")
        
        summary["work_time"] = {
            "total_seconds": total_work_time,
            "effective_seconds": effective_work_time,
            "efficiency": effective_work_time / total_work_time if total_work_time > 0 else 0,
            "active_users": self.get_gauge("quality_billing_current_active_users")
        }
        
        # Quality summary
        quality_assessments = self.get_counter("quality_billing_quality_assessments_total")
        
        summary["quality"] = {
            "total_assessments": quality_assessments,
            "improvement_stats": self.get_histogram_stats("quality_billing_quality_improvement_rate")
        }
        
        # Billing summary
        total_invoices = self.get_counter("quality_billing_invoices_generated_total")
        total_amount = self.get_counter("quality_billing_total_amount_cents")
        
        summary["billing"] = {
            "total_invoices": total_invoices,
            "total_amount_cents": total_amount,
            "average_invoice_cents": total_amount / total_invoices if total_invoices > 0 else 0
        }
        
        # Performance summary
        tasks_completed = self.get_counter("quality_billing_tasks_completed_total")
        completion_time_stats = self.get_histogram_stats("quality_billing_task_completion_time_seconds")
        
        summary["performance"] = {
            "tasks_completed": tasks_completed,
            "completion_time_stats": completion_time_stats
        }
        
        # System summary
        api_requests = self.get_counter("quality_billing_api_requests_total")
        response_time_stats = self.get_histogram_stats("quality_billing_api_response_time_seconds")
        
        summary["system"] = {
            "api_requests": api_requests,
            "response_time_stats": response_time_stats,
            "active_sessions": self.get_gauge("quality_billing_active_sessions")
        }
        
        return summary

    def reset_metrics(self):
        """Reset all metrics (use with caution)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._time_series.clear()
            logger.warning("All metrics have been reset")


# Global metrics collector instance
quality_billing_metrics = PrometheusMetricsCollector()


# Convenience functions
def get_metrics_collector() -> PrometheusMetricsCollector:
    """Get the global metrics collector instance."""
    return quality_billing_metrics


def record_work_session(
    user_id: str,
    project_id: str,
    duration_seconds: float,
    effective_duration_seconds: float,
    quality_score: float
):
    """Record a work session."""
    quality_billing_metrics.record_work_session(
        user_id, project_id, duration_seconds, effective_duration_seconds, quality_score
    )


def record_billing_event(
    user_id: str,
    project_id: str,
    amount_cents: int,
    quality_level: str,
    task_type: str
):
    """Record a billing event."""
    quality_billing_metrics.record_billing_event(
        user_id, project_id, amount_cents, quality_level, task_type
    )


def record_performance_evaluation(
    user_id: str,
    performance_score: float,
    tasks_completed: int,
    average_completion_time: float
):
    """Record performance evaluation."""
    quality_billing_metrics.record_performance_evaluation(
        user_id, performance_score, tasks_completed, average_completion_time
    )


def export_prometheus_metrics() -> str:
    """Export all metrics in Prometheus format."""
    return quality_billing_metrics.export_prometheus()