"""
Custom Metrics Registry for High Availability Monitoring.

Provides custom metric registration and collection for high availability
monitoring, extending the existing Prometheus integration.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    """Definition of a custom metric."""
    name: str
    metric_type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms
    unit: str = ""


@dataclass
class MetricValue:
    """Current value of a metric."""
    value: float
    labels: Dict[str, str]
    timestamp: float = field(default_factory=time.time)


class CustomMetricsRegistry:
    """
    Registry for custom high availability metrics.
    
    Features:
    - Custom metric registration
    - Label support
    - Thread-safe operations
    - Metric aggregation
    - Export to Prometheus format
    """
    
    def __init__(self):
        self.metrics: Dict[str, MetricDefinition] = {}
        self.values: Dict[str, List[MetricValue]] = defaultdict(list)
        self.counters: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.histograms: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._lock = threading.Lock()
        
        # Register default HA metrics
        self._register_default_metrics()
        
        logger.info("CustomMetricsRegistry initialized")
    
    def _register_default_metrics(self):
        """Register default high availability metrics."""
        # System availability metrics
        self.register_gauge(
            "ha_system_availability_percentage",
            "System availability percentage",
            labels=["node"]
        )
        
        self.register_gauge(
            "ha_service_health_score",
            "Service health score (0-100)",
            labels=["service_name"]
        )
        
        # Recovery metrics
        self.register_counter(
            "ha_recovery_attempts_total",
            "Total recovery attempts",
            labels=["recovery_type", "status"]
        )
        
        self.register_histogram(
            "ha_recovery_duration_seconds",
            "Recovery operation duration in seconds",
            labels=["recovery_type"],
            buckets=[1, 5, 10, 30, 60, 120, 300, 600]
        )
        
        # Failover metrics
        self.register_counter(
            "ha_failover_total",
            "Total failover operations",
            labels=["from_node", "to_node", "status"]
        )
        
        self.register_gauge(
            "ha_failover_time_seconds",
            "Time since last failover",
            labels=["node"]
        )
        
        # Backup metrics
        self.register_counter(
            "ha_backup_operations_total",
            "Total backup operations",
            labels=["backup_type", "status"]
        )
        
        self.register_gauge(
            "ha_backup_size_bytes",
            "Size of last backup in bytes",
            labels=["backup_type"]
        )
        
        self.register_histogram(
            "ha_backup_duration_seconds",
            "Backup operation duration in seconds",
            labels=["backup_type"],
            buckets=[10, 30, 60, 120, 300, 600, 1800, 3600]
        )
        
        # Health check metrics
        self.register_gauge(
            "ha_health_check_status",
            "Health check status (1=healthy, 0=unhealthy)",
            labels=["check_name", "service"]
        )
        
        self.register_histogram(
            "ha_health_check_duration_seconds",
            "Health check duration in seconds",
            labels=["check_name"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1, 5, 10]
        )
        
        # Data integrity metrics
        self.register_gauge(
            "ha_data_integrity_score",
            "Data integrity verification score",
            labels=["component"]
        )
        
        # Node status metrics
        self.register_gauge(
            "ha_node_status",
            "Node status (1=active, 0=standby, -1=failed)",
            labels=["node", "role"]
        )
        
        self.register_gauge(
            "ha_active_nodes_count",
            "Number of active nodes"
        )
        
        self.register_gauge(
            "ha_standby_nodes_count",
            "Number of standby nodes"
        )
    
    def register_counter(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> MetricDefinition:
        """Register a counter metric."""
        metric = MetricDefinition(
            name=name,
            metric_type=MetricType.COUNTER,
            description=description,
            labels=labels or []
        )
        
        with self._lock:
            self.metrics[name] = metric
        
        logger.debug(f"Registered counter metric: {name}")
        return metric
    
    def register_gauge(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        unit: str = ""
    ) -> MetricDefinition:
        """Register a gauge metric."""
        metric = MetricDefinition(
            name=name,
            metric_type=MetricType.GAUGE,
            description=description,
            labels=labels or [],
            unit=unit
        )
        
        with self._lock:
            self.metrics[name] = metric
        
        logger.debug(f"Registered gauge metric: {name}")
        return metric
    
    def register_histogram(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None
    ) -> MetricDefinition:
        """Register a histogram metric."""
        if buckets is None:
            buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        
        metric = MetricDefinition(
            name=name,
            metric_type=MetricType.HISTOGRAM,
            description=description,
            labels=labels or [],
            buckets=buckets
        )
        
        with self._lock:
            self.metrics[name] = metric
        
        logger.debug(f"Registered histogram metric: {name}")
        return metric
    
    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to a string key."""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    
    def inc_counter(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        
        with self._lock:
            self.counters[name][key] += value
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        
        with self._lock:
            self.gauges[name][key] = value
    
    def inc_gauge(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a gauge metric."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        
        with self._lock:
            self.gauges[name][key] += value
    
    def dec_gauge(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None):
        """Decrement a gauge metric."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        
        with self._lock:
            self.gauges[name][key] -= value
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value for a histogram metric."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        
        with self._lock:
            self.histograms[name][key].append(value)
            # Keep only last 1000 observations per label set
            if len(self.histograms[name][key]) > 1000:
                self.histograms[name][key] = self.histograms[name][key][-1000:]
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        
        with self._lock:
            return self.counters[name].get(key, 0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        
        with self._lock:
            return self.gauges[name].get(key, 0)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        
        with self._lock:
            values = self.histograms[name].get(key, [])
            
            if not values:
                return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
            
            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metric values."""
        with self._lock:
            result = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {}
            }
            
            for name, label_values in self.histograms.items():
                result["histograms"][name] = {}
                for key, values in label_values.items():
                    if values:
                        result["histograms"][name][key] = {
                            "count": len(values),
                            "sum": sum(values),
                            "avg": sum(values) / len(values)
                        }
            
            return result
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        
        with self._lock:
            # Export counters
            for name, label_values in self.counters.items():
                metric_def = self.metrics.get(name)
                if metric_def:
                    lines.append(f"# HELP {name} {metric_def.description}")
                    lines.append(f"# TYPE {name} counter")
                
                for key, value in label_values.items():
                    if key:
                        lines.append(f"{name}{{{key}}} {value}")
                    else:
                        lines.append(f"{name} {value}")
            
            # Export gauges
            for name, label_values in self.gauges.items():
                metric_def = self.metrics.get(name)
                if metric_def:
                    lines.append(f"# HELP {name} {metric_def.description}")
                    lines.append(f"# TYPE {name} gauge")
                
                for key, value in label_values.items():
                    if key:
                        lines.append(f"{name}{{{key}}} {value}")
                    else:
                        lines.append(f"{name} {value}")
            
            # Export histograms
            for name, label_values in self.histograms.items():
                metric_def = self.metrics.get(name)
                if metric_def:
                    lines.append(f"# HELP {name} {metric_def.description}")
                    lines.append(f"# TYPE {name} histogram")
                
                for key, values in label_values.items():
                    if not values:
                        continue
                    
                    buckets = metric_def.buckets if metric_def else [0.1, 0.5, 1, 5, 10]
                    
                    # Calculate bucket counts
                    for bucket in buckets:
                        count = sum(1 for v in values if v <= bucket)
                        bucket_key = f'{key},le="{bucket}"' if key else f'le="{bucket}"'
                        lines.append(f"{name}_bucket{{{bucket_key}}} {count}")
                    
                    # +Inf bucket
                    inf_key = f'{key},le="+Inf"' if key else 'le="+Inf"'
                    lines.append(f"{name}_bucket{{{inf_key}}} {len(values)}")
                    
                    # Sum and count
                    if key:
                        lines.append(f"{name}_sum{{{key}}} {sum(values)}")
                        lines.append(f"{name}_count{{{key}}} {len(values)}")
                    else:
                        lines.append(f"{name}_sum {sum(values)}")
                        lines.append(f"{name}_count {len(values)}")
        
        return "\n".join(lines)
    
    def reset_metric(self, name: str):
        """Reset a metric to zero."""
        with self._lock:
            if name in self.counters:
                self.counters[name].clear()
            if name in self.gauges:
                self.gauges[name].clear()
            if name in self.histograms:
                self.histograms[name].clear()
    
    def reset_all(self):
        """Reset all metrics."""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()


# Global custom metrics registry
custom_metrics = CustomMetricsRegistry()


# Convenience functions
def record_recovery_attempt(recovery_type: str, success: bool, duration: float):
    """Record a recovery attempt."""
    status = "success" if success else "failure"
    custom_metrics.inc_counter(
        "ha_recovery_attempts_total",
        labels={"recovery_type": recovery_type, "status": status}
    )
    custom_metrics.observe_histogram(
        "ha_recovery_duration_seconds",
        duration,
        labels={"recovery_type": recovery_type}
    )


def record_failover(from_node: str, to_node: str, success: bool):
    """Record a failover operation."""
    status = "success" if success else "failure"
    custom_metrics.inc_counter(
        "ha_failover_total",
        labels={"from_node": from_node, "to_node": to_node, "status": status}
    )


def record_backup(backup_type: str, success: bool, size_bytes: int, duration: float):
    """Record a backup operation."""
    status = "success" if success else "failure"
    custom_metrics.inc_counter(
        "ha_backup_operations_total",
        labels={"backup_type": backup_type, "status": status}
    )
    custom_metrics.set_gauge(
        "ha_backup_size_bytes",
        size_bytes,
        labels={"backup_type": backup_type}
    )
    custom_metrics.observe_histogram(
        "ha_backup_duration_seconds",
        duration,
        labels={"backup_type": backup_type}
    )


def update_service_health(service_name: str, health_score: float):
    """Update service health score."""
    custom_metrics.set_gauge(
        "ha_service_health_score",
        health_score,
        labels={"service_name": service_name}
    )


def update_system_availability(node: str, availability: float):
    """Update system availability percentage."""
    custom_metrics.set_gauge(
        "ha_system_availability_percentage",
        availability,
        labels={"node": node}
    )
