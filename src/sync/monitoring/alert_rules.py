"""
Sync System Alert Rules Configuration.

Defines alerting rules and thresholds for the data synchronization system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertCategory(str, Enum):
    """Alert categories."""
    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    SECURITY = "security"
    CAPACITY = "capacity"
    QUALITY = "quality"


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    description: str
    metric: str
    condition: str  # gt, lt, eq, gte, lte
    threshold: float
    severity: AlertSeverity
    category: AlertCategory
    duration_seconds: int = 0  # How long condition must be true
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class Alert:
    """An active alert."""
    rule_name: str
    severity: AlertSeverity
    category: AlertCategory
    message: str
    value: float
    threshold: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False


class SyncAlertManager:
    """
    Alert manager for sync system.

    Evaluates alert rules and manages active alerts.
    """

    # Default alert rules for sync system
    DEFAULT_RULES = [
        # Performance alerts
        AlertRule(
            name="sync_high_latency",
            description="Sync operation latency is too high",
            metric="sync_latency_seconds",
            condition="gt",
            threshold=5.0,
            severity=AlertSeverity.WARNING,
            category=AlertCategory.PERFORMANCE,
            duration_seconds=60,
            annotations={"summary": "Sync latency > 5s for 1 minute"}
        ),
        AlertRule(
            name="sync_critical_latency",
            description="Sync operation latency is critically high",
            metric="sync_latency_seconds",
            condition="gt",
            threshold=10.0,
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.PERFORMANCE,
            annotations={"summary": "Sync latency > 10s"}
        ),
        AlertRule(
            name="sync_low_throughput",
            description="Sync throughput is below expected",
            metric="sync_records_per_second",
            condition="lt",
            threshold=100.0,
            severity=AlertSeverity.WARNING,
            category=AlertCategory.PERFORMANCE,
            duration_seconds=300,
            annotations={"summary": "Throughput < 100 records/s for 5 minutes"}
        ),

        # Error alerts
        AlertRule(
            name="sync_high_error_rate",
            description="Sync error rate is too high",
            metric="sync_error_rate",
            condition="gt",
            threshold=0.05,  # 5%
            severity=AlertSeverity.WARNING,
            category=AlertCategory.QUALITY,
            annotations={"summary": "Error rate > 5%"}
        ),
        AlertRule(
            name="sync_critical_error_rate",
            description="Sync error rate is critically high",
            metric="sync_error_rate",
            condition="gt",
            threshold=0.20,  # 20%
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.QUALITY,
            annotations={"summary": "Error rate > 20%"}
        ),

        # Capacity alerts
        AlertRule(
            name="sync_queue_high",
            description="Sync queue depth is high",
            metric="sync_queue_depth",
            condition="gt",
            threshold=1000,
            severity=AlertSeverity.WARNING,
            category=AlertCategory.CAPACITY,
            annotations={"summary": "Queue depth > 1000"}
        ),
        AlertRule(
            name="sync_queue_critical",
            description="Sync queue depth is critically high",
            metric="sync_queue_depth",
            condition="gt",
            threshold=5000,
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.CAPACITY,
            annotations={"summary": "Queue depth > 5000"}
        ),

        # Connector alerts
        AlertRule(
            name="connector_pool_exhausted",
            description="Connection pool is nearly exhausted",
            metric="connector_pool_available_ratio",
            condition="lt",
            threshold=0.10,  # 10%
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.CAPACITY,
            annotations={"summary": "Available connections < 10%"}
        ),
        AlertRule(
            name="connector_high_failure_rate",
            description="Connector failure rate is high",
            metric="connector_failure_rate",
            condition="gt",
            threshold=0.10,  # 10%
            severity=AlertSeverity.WARNING,
            category=AlertCategory.AVAILABILITY,
            annotations={"summary": "Connector failure rate > 10%"}
        ),

        # WebSocket alerts
        AlertRule(
            name="websocket_high_backpressure",
            description="WebSocket backpressure events are high",
            metric="websocket_backpressure_rate",
            condition="gt",
            threshold=10.0,  # per minute
            severity=AlertSeverity.WARNING,
            category=AlertCategory.PERFORMANCE,
            annotations={"summary": "Backpressure events > 10/min"}
        ),

        # Conflict alerts
        AlertRule(
            name="conflict_low_resolution_rate",
            description="Conflict resolution rate is low",
            metric="conflict_resolution_rate",
            condition="lt",
            threshold=0.90,  # 90%
            severity=AlertSeverity.WARNING,
            category=AlertCategory.QUALITY,
            annotations={"summary": "Conflict resolution rate < 90%"}
        ),
    ]

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self._condition_start_times: Dict[str, float] = {}

        # Load default rules
        for rule in self.DEFAULT_RULES:
            self.add_rule(rule)

    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.name] = rule
        logger.debug(f"Added alert rule: {rule.name}")

    def remove_rule(self, name: str):
        """Remove an alert rule."""
        if name in self.rules:
            del self.rules[name]
            logger.debug(f"Removed alert rule: {name}")

    def enable_rule(self, name: str):
        """Enable an alert rule."""
        if name in self.rules:
            self.rules[name].enabled = True

    def disable_rule(self, name: str):
        """Disable an alert rule."""
        if name in self.rules:
            self.rules[name].enabled = False

    def add_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler callback."""
        self.alert_handlers.append(handler)

    def evaluate_rule(self, rule: AlertRule, value: float, timestamp: float) -> Optional[Alert]:
        """Evaluate a single rule against a metric value."""
        if not rule.enabled:
            return None

        # Check condition
        triggered = False
        if rule.condition == "gt":
            triggered = value > rule.threshold
        elif rule.condition == "lt":
            triggered = value < rule.threshold
        elif rule.condition == "gte":
            triggered = value >= rule.threshold
        elif rule.condition == "lte":
            triggered = value <= rule.threshold
        elif rule.condition == "eq":
            triggered = value == rule.threshold

        if not triggered:
            # Clear condition start time if condition is no longer true
            if rule.name in self._condition_start_times:
                del self._condition_start_times[rule.name]
            return None

        # Check duration requirement
        if rule.duration_seconds > 0:
            if rule.name not in self._condition_start_times:
                self._condition_start_times[rule.name] = timestamp
                return None

            elapsed = timestamp - self._condition_start_times[rule.name]
            if elapsed < rule.duration_seconds:
                return None

        # Create alert
        message = rule.annotations.get("summary", rule.description)
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            category=rule.category,
            message=f"{message} (current: {value}, threshold: {rule.threshold})",
            value=value,
            threshold=rule.threshold,
            timestamp=timestamp,
            labels=rule.labels.copy()
        )

        return alert

    def process_metric(self, metric_name: str, value: float, timestamp: float, labels: Optional[Dict[str, str]] = None):
        """Process a metric value and evaluate relevant rules."""
        import time
        timestamp = timestamp or time.time()

        for rule in self.rules.values():
            if rule.metric != metric_name:
                continue

            # Check label match if rule has labels
            if rule.labels:
                if not labels:
                    continue
                if not all(labels.get(k) == v for k, v in rule.labels.items()):
                    continue

            alert = self.evaluate_rule(rule, value, timestamp)

            if alert:
                if rule.name not in self.active_alerts:
                    # New alert
                    self.active_alerts[rule.name] = alert
                    self._fire_alert(alert)
                    logger.warning(f"Alert fired: {rule.name} - {alert.message}")
            else:
                # Check if we should resolve existing alert
                if rule.name in self.active_alerts:
                    self._resolve_alert(rule.name)

    def _fire_alert(self, alert: Alert):
        """Fire an alert to all handlers."""
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def _resolve_alert(self, rule_name: str):
        """Resolve an active alert."""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.resolved = True
            logger.info(f"Alert resolved: {rule_name}")
            del self.active_alerts[rule_name]

    def acknowledge_alert(self, rule_name: str):
        """Acknowledge an active alert."""
        if rule_name in self.active_alerts:
            self.active_alerts[rule_name].acknowledged = True
            logger.info(f"Alert acknowledged: {rule_name}")

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get all active alerts, optionally filtered by severity."""
        alerts = list(self.active_alerts.values())
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return sorted(alerts, key=lambda a: (a.severity.value, a.timestamp), reverse=True)

    def get_alert_summary(self) -> Dict[str, int]:
        """Get a summary of active alerts by severity."""
        summary = {s.value: 0 for s in AlertSeverity}
        for alert in self.active_alerts.values():
            summary[alert.severity.value] += 1
        return summary


# Global alert manager instance
sync_alert_manager = SyncAlertManager()
