"""
TCB Cloud Monitoring Integration.

Provides integration with TCB cloud monitoring services including
metrics collection, alerting, and dashboard integration.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics."""
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"


@dataclass
class MetricDefinition:
    """Definition of a metric."""
    name: str
    metric_type: MetricType
    description: str
    unit: str = ""
    labels: List[str] = field(default_factory=list)


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    metric_name: str
    condition: str  # e.g., "> 80", "< 10"
    threshold: float
    duration_seconds: int = 60
    severity: AlertSeverity = AlertSeverity.WARNING
    description: str = ""
    enabled: bool = True


@dataclass
class Alert:
    """An active alert."""
    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    triggered_at: float
    resolved_at: Optional[float] = None
    message: str = ""


@dataclass
class TCBMonitoringConfig:
    """Configuration for TCB monitoring."""
    collection_interval: float = 30.0
    retention_hours: int = 24
    enable_cloud_push: bool = True
    enable_local_storage: bool = True
    alert_webhook_url: Optional[str] = None
    alert_channels: List[str] = field(default_factory=lambda: ["webhook"])


class TCBMonitoringService:
    """
    TCB Cloud Monitoring integration service.
    
    Features:
    - Container metrics collection
    - Service health monitoring
    - Custom metrics support
    - Alert rule management
    - Cloud monitoring integration
    """
    
    def __init__(self, config: Optional[TCBMonitoringConfig] = None):
        self.config = config or TCBMonitoringConfig()
        self.metrics: Dict[str, MetricDefinition] = {}
        self.metric_values: Dict[str, deque] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self._is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._metrics_callback: Optional[callable] = None
        
        # Register default metrics
        self._register_default_metrics()
        self._register_default_alert_rules()
        
        logger.info("TCBMonitoringService initialized")
    
    def _register_default_metrics(self):
        """Register default container metrics."""
        default_metrics = [
            MetricDefinition(
                name="container_cpu_usage",
                metric_type=MetricType.GAUGE,
                description="Container CPU usage percentage",
                unit="percent"
            ),
            MetricDefinition(
                name="container_memory_usage",
                metric_type=MetricType.GAUGE,
                description="Container memory usage percentage",
                unit="percent"
            ),
            MetricDefinition(
                name="container_memory_bytes",
                metric_type=MetricType.GAUGE,
                description="Container memory usage in bytes",
                unit="bytes"
            ),
            MetricDefinition(
                name="container_disk_usage",
                metric_type=MetricType.GAUGE,
                description="Container disk usage percentage",
                unit="percent"
            ),
            MetricDefinition(
                name="container_network_rx_bytes",
                metric_type=MetricType.COUNTER,
                description="Network bytes received",
                unit="bytes"
            ),
            MetricDefinition(
                name="container_network_tx_bytes",
                metric_type=MetricType.COUNTER,
                description="Network bytes transmitted",
                unit="bytes"
            ),
            MetricDefinition(
                name="service_request_count",
                metric_type=MetricType.COUNTER,
                description="Total service requests",
                unit="requests",
                labels=["service", "status"]
            ),
            MetricDefinition(
                name="service_response_time",
                metric_type=MetricType.HISTOGRAM,
                description="Service response time",
                unit="milliseconds",
                labels=["service"]
            ),
            MetricDefinition(
                name="service_health_status",
                metric_type=MetricType.GAUGE,
                description="Service health status (1=healthy, 0=unhealthy)",
                unit="",
                labels=["service"]
            ),
            MetricDefinition(
                name="database_connections",
                metric_type=MetricType.GAUGE,
                description="Active database connections",
                unit="connections"
            ),
            MetricDefinition(
                name="redis_memory_usage",
                metric_type=MetricType.GAUGE,
                description="Redis memory usage",
                unit="bytes"
            ),
            MetricDefinition(
                name="instance_count",
                metric_type=MetricType.GAUGE,
                description="Current instance count",
                unit="instances"
            )
        ]
        
        for metric in default_metrics:
            self.metrics[metric.name] = metric
            self.metric_values[metric.name] = deque(maxlen=1000)
    
    def _register_default_alert_rules(self):
        """Register default alert rules."""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric_name="container_cpu_usage",
                condition=">",
                threshold=80.0,
                duration_seconds=300,
                severity=AlertSeverity.WARNING,
                description="CPU usage above 80% for 5 minutes"
            ),
            AlertRule(
                name="critical_cpu_usage",
                metric_name="container_cpu_usage",
                condition=">",
                threshold=95.0,
                duration_seconds=60,
                severity=AlertSeverity.CRITICAL,
                description="CPU usage above 95% for 1 minute"
            ),
            AlertRule(
                name="high_memory_usage",
                metric_name="container_memory_usage",
                condition=">",
                threshold=85.0,
                duration_seconds=300,
                severity=AlertSeverity.WARNING,
                description="Memory usage above 85% for 5 minutes"
            ),
            AlertRule(
                name="critical_memory_usage",
                metric_name="container_memory_usage",
                condition=">",
                threshold=95.0,
                duration_seconds=60,
                severity=AlertSeverity.CRITICAL,
                description="Memory usage above 95% for 1 minute"
            ),
            AlertRule(
                name="high_disk_usage",
                metric_name="container_disk_usage",
                condition=">",
                threshold=80.0,
                duration_seconds=600,
                severity=AlertSeverity.WARNING,
                description="Disk usage above 80% for 10 minutes"
            ),
            AlertRule(
                name="service_unhealthy",
                metric_name="service_health_status",
                condition="<",
                threshold=1.0,
                duration_seconds=60,
                severity=AlertSeverity.ERROR,
                description="Service health check failing for 1 minute"
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.name] = rule
    
    def set_metrics_callback(self, callback: callable):
        """Set callback for collecting metrics."""
        self._metrics_callback = callback
    
    def register_metric(self, metric: MetricDefinition):
        """Register a custom metric."""
        self.metrics[metric.name] = metric
        self.metric_values[metric.name] = deque(maxlen=1000)
        logger.info(f"Registered metric: {metric.name}")
    
    def add_alert_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.alert_rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str) -> bool:
        """Remove an alert rule."""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")
            return True
        return False
    
    async def start(self):
        """Start the monitoring service."""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("TCBMonitoringService started")
    
    async def stop(self):
        """Stop the monitoring service."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("TCBMonitoringService stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._is_running:
            try:
                await self._collect_metrics()
                await self._evaluate_alerts()
                await asyncio.sleep(self.config.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _collect_metrics(self):
        """Collect metrics from all sources."""
        timestamp = time.time()
        
        if self._metrics_callback:
            try:
                metrics_data = await self._metrics_callback()
                for metric_name, value in metrics_data.items():
                    if metric_name in self.metric_values:
                        self.metric_values[metric_name].append({
                            "timestamp": timestamp,
                            "value": value
                        })
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
    
    async def _evaluate_alerts(self):
        """Evaluate all alert rules."""
        current_time = time.time()
        
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            if rule.metric_name not in self.metric_values:
                continue
            
            values = list(self.metric_values[rule.metric_name])
            if not values:
                continue
            
            # Get values within the duration window
            window_start = current_time - rule.duration_seconds
            window_values = [v for v in values if v["timestamp"] >= window_start]
            
            if not window_values:
                continue
            
            # Calculate average value
            avg_value = sum(v["value"] for v in window_values) / len(window_values)
            
            # Check condition
            triggered = self._check_condition(avg_value, rule.condition, rule.threshold)
            
            if triggered:
                if rule_name not in self.active_alerts:
                    # New alert
                    alert = Alert(
                        rule_name=rule_name,
                        metric_name=rule.metric_name,
                        current_value=avg_value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        triggered_at=current_time,
                        message=f"{rule.description} (current: {avg_value:.2f}, threshold: {rule.threshold})"
                    )
                    self.active_alerts[rule_name] = alert
                    self.alert_history.append(alert)
                    await self._send_alert(alert)
                    logger.warning(f"Alert triggered: {rule_name}")
            else:
                if rule_name in self.active_alerts:
                    # Resolve alert
                    alert = self.active_alerts[rule_name]
                    alert.resolved_at = current_time
                    del self.active_alerts[rule_name]
                    await self._send_alert_resolved(alert)
                    logger.info(f"Alert resolved: {rule_name}")
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Check if a condition is met."""
        if condition == ">":
            return value > threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<":
            return value < threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return value == threshold
        elif condition == "!=":
            return value != threshold
        return False
    
    async def _send_alert(self, alert: Alert):
        """Send alert notification."""
        if not self.config.alert_webhook_url:
            return
        
        try:
            import aiohttp
            
            payload = {
                "type": "alert",
                "rule_name": alert.rule_name,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "severity": alert.severity.value,
                "message": alert.message,
                "triggered_at": alert.triggered_at
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.alert_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send alert: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def _send_alert_resolved(self, alert: Alert):
        """Send alert resolved notification."""
        if not self.config.alert_webhook_url:
            return
        
        try:
            import aiohttp
            
            payload = {
                "type": "alert_resolved",
                "rule_name": alert.rule_name,
                "metric_name": alert.metric_name,
                "resolved_at": alert.resolved_at
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.alert_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send alert resolved: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error sending alert resolved: {e}")
    
    def record_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        if metric_name not in self.metric_values:
            logger.warning(f"Unknown metric: {metric_name}")
            return
        
        self.metric_values[metric_name].append({
            "timestamp": time.time(),
            "value": value,
            "labels": labels or {}
        })
    
    def get_metric_values(self, metric_name: str, duration_seconds: int = 3600) -> List[Dict[str, Any]]:
        """Get metric values for a time period."""
        if metric_name not in self.metric_values:
            return []
        
        cutoff = time.time() - duration_seconds
        values = list(self.metric_values[metric_name])
        return [v for v in values if v["timestamp"] >= cutoff]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [
            {
                "rule_name": a.rule_name,
                "metric_name": a.metric_name,
                "current_value": a.current_value,
                "threshold": a.threshold,
                "severity": a.severity.value,
                "triggered_at": a.triggered_at,
                "message": a.message
            }
            for a in self.active_alerts.values()
        ]
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history."""
        history = list(self.alert_history)[-limit:]
        return [
            {
                "rule_name": a.rule_name,
                "metric_name": a.metric_name,
                "severity": a.severity.value,
                "triggered_at": a.triggered_at,
                "resolved_at": a.resolved_at,
                "message": a.message
            }
            for a in history
        ]
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metric values."""
        result = {}
        for metric_name, values in self.metric_values.items():
            if values:
                latest = values[-1]
                result[metric_name] = {
                    "value": latest["value"],
                    "timestamp": latest["timestamp"]
                }
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "metrics_count": len(self.metrics),
            "alert_rules_count": len(self.alert_rules),
            "active_alerts_count": len(self.active_alerts),
            "alert_history_count": len(self.alert_history),
            "is_running": self._is_running,
            "collection_interval": self.config.collection_interval
        }


# Global monitoring service
tcb_monitoring_service: Optional[TCBMonitoringService] = None


async def initialize_tcb_monitoring(
    config: Optional[TCBMonitoringConfig] = None
) -> TCBMonitoringService:
    """Initialize the global TCB monitoring service."""
    global tcb_monitoring_service
    tcb_monitoring_service = TCBMonitoringService(config)
    await tcb_monitoring_service.start()
    return tcb_monitoring_service


async def shutdown_tcb_monitoring():
    """Shutdown the global TCB monitoring service."""
    global tcb_monitoring_service
    if tcb_monitoring_service:
        await tcb_monitoring_service.stop()
        tcb_monitoring_service = None


def get_tcb_monitoring_service() -> Optional[TCBMonitoringService]:
    """Get the global TCB monitoring service."""
    return tcb_monitoring_service
