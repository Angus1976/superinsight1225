"""
Alert Rule Engine for Multi-Channel Notification System

Provides flexible alert rule configuration, alert level and priority management,
alert aggregation and deduplication, and alert escalation and processing workflows.
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import hashlib

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertPriority(int, Enum):
    """Alert priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    EMERGENCY = 5


class AlertRuleType(str, Enum):
    """Alert rule types."""
    THRESHOLD = "threshold"      # Threshold-based alerts
    TREND = "trend"             # Trend-based alerts
    ANOMALY = "anomaly"         # Anomaly detection alerts
    COMPOSITE = "composite"     # Composite condition alerts
    PATTERN = "pattern"         # Pattern matching alerts
    FREQUENCY = "frequency"     # Frequency-based alerts


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"
    ESCALATED = "escalated"
    SUPPRESSED = "suppressed"


class AlertCategory(str, Enum):
    """Alert categories."""
    SYSTEM = "system"           # System health alerts
    PERFORMANCE = "performance" # Performance alerts
    SECURITY = "security"       # Security alerts
    BUSINESS = "business"       # Business logic alerts
    QUALITY = "quality"         # Data quality alerts
    COST = "cost"              # Cost management alerts


@dataclass
class AlertRule:
    """Alert rule configuration."""
    id: str
    name: str
    description: str
    category: AlertCategory
    rule_type: AlertRuleType
    level: AlertLevel
    priority: AlertPriority
    enabled: bool = True
    
    # Rule conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Threshold configuration
    threshold_config: Optional[Dict[str, Any]] = None
    
    # Trend configuration
    trend_config: Optional[Dict[str, Any]] = None
    
    # Anomaly detection configuration
    anomaly_config: Optional[Dict[str, Any]] = None
    
    # Composite rule configuration
    composite_config: Optional[Dict[str, Any]] = None
    
    # Pattern matching configuration
    pattern_config: Optional[Dict[str, Any]] = None
    
    # Frequency configuration
    frequency_config: Optional[Dict[str, Any]] = None
    
    # Suppression configuration
    suppression_config: Optional[Dict[str, Any]] = None
    
    # Escalation configuration
    escalation_config: Optional[Dict[str, Any]] = None
    
    # Notification configuration
    notification_config: Optional[Dict[str, Any]] = None
    
    # Tags and metadata
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "rule_type": self.rule_type.value,
            "level": self.level.value,
            "priority": self.priority.value,
            "enabled": self.enabled,
            "conditions": self.conditions,
            "threshold_config": self.threshold_config,
            "trend_config": self.trend_config,
            "anomaly_config": self.anomaly_config,
            "composite_config": self.composite_config,
            "pattern_config": self.pattern_config,
            "frequency_config": self.frequency_config,
            "suppression_config": self.suppression_config,
            "escalation_config": self.escalation_config,
            "notification_config": self.notification_config,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by
        }


@dataclass
class Alert:
    """Alert instance."""
    id: UUID
    rule_id: str
    category: AlertCategory
    level: AlertLevel
    priority: AlertPriority
    title: str
    message: str
    source: str
    status: AlertStatus = AlertStatus.ACTIVE
    
    # Context information
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # Metric information
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    
    # Additional context
    context: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    escalated_at: Optional[datetime] = None
    
    # Processing information
    notifications_sent: List[str] = field(default_factory=list)
    escalation_level: int = 0
    suppressed_until: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "rule_id": self.rule_id,
            "category": self.category.value,
            "level": self.level.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "status": self.status.value,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold_value": self.threshold_value,
            "context": self.context,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "escalated_at": self.escalated_at.isoformat() if self.escalated_at else None,
            "notifications_sent": self.notifications_sent,
            "escalation_level": self.escalation_level,
            "suppressed_until": self.suppressed_until.isoformat() if self.suppressed_until else None
        }


class AlertRuleEngine:
    """
    Flexible alert rule engine with comprehensive rule management.
    
    Features:
    - Multiple rule types (threshold, trend, anomaly, composite, pattern, frequency)
    - Alert level and priority management
    - Alert aggregation and deduplication
    - Alert escalation and processing workflows
    """
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[UUID, Alert] = {}
        self.alert_history: List[Alert] = []
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.frequency_counters: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Rule evaluation statistics
        self.evaluation_stats = {
            "total_evaluations": 0,
            "alerts_generated": 0,
            "by_rule_type": defaultdict(int),
            "by_level": defaultdict(int)
        }
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default alert rules."""
        # System health threshold rule
        self.create_threshold_rule(
            name="System CPU Usage High",
            description="Alert when system CPU usage exceeds threshold",
            category=AlertCategory.SYSTEM,
            metric_name="system.cpu.usage",
            threshold=80.0,
            operator="gt",
            level=AlertLevel.WARNING,
            priority=AlertPriority.HIGH
        )
        
        # Memory usage threshold rule
        self.create_threshold_rule(
            name="System Memory Usage Critical",
            description="Alert when system memory usage is critically high",
            category=AlertCategory.SYSTEM,
            metric_name="system.memory.usage",
            threshold=90.0,
            operator="gt",
            level=AlertLevel.CRITICAL,
            priority=AlertPriority.URGENT
        )
        
        # Performance response time rule
        self.create_threshold_rule(
            name="API Response Time High",
            description="Alert when API response time exceeds acceptable threshold",
            category=AlertCategory.PERFORMANCE,
            metric_name="api.response_time",
            threshold=2000.0,  # 2 seconds
            operator="gt",
            level=AlertLevel.WARNING,
            priority=AlertPriority.HIGH
        )
        
        # Error rate frequency rule
        self.create_frequency_rule(
            name="High Error Rate",
            description="Alert when error rate exceeds threshold",
            category=AlertCategory.SYSTEM,
            metric_name="errors.count",
            threshold=10,
            time_window_minutes=5,
            level=AlertLevel.HIGH,
            priority=AlertPriority.URGENT
        )
        
        logger.info("Initialized default alert rules")
    
    def create_threshold_rule(
        self,
        name: str,
        description: str,
        category: AlertCategory,
        metric_name: str,
        threshold: float,
        operator: str = "gt",
        level: AlertLevel = AlertLevel.WARNING,
        priority: AlertPriority = AlertPriority.NORMAL,
        duration_minutes: int = 1,
        tags: Optional[Dict[str, str]] = None
    ) -> AlertRule:
        """Create a threshold-based alert rule."""
        rule_id = f"threshold_{uuid4().hex[:8]}"
        
        rule = AlertRule(
            id=rule_id,
            name=name,
            description=description,
            category=category,
            rule_type=AlertRuleType.THRESHOLD,
            level=level,
            priority=priority,
            conditions={
                "metric_name": metric_name,
                "operator": operator,
                "threshold": threshold
            },
            threshold_config={
                "threshold": threshold,
                "operator": operator,
                "duration_minutes": duration_minutes,
                "comparison": "above" if operator in ["gt", "gte"] else "below"
            },
            escalation_config={
                "escalate_after_minutes": 15,
                "max_escalation_level": 3
            },
            tags=tags or {}
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created threshold rule: {rule_id} - {name}")
        return rule
    
    def create_trend_rule(
        self,
        name: str,
        description: str,
        category: AlertCategory,
        metric_name: str,
        trend_threshold: float,
        window_size: int = 10,
        level: AlertLevel = AlertLevel.WARNING,
        priority: AlertPriority = AlertPriority.NORMAL,
        tags: Optional[Dict[str, str]] = None
    ) -> AlertRule:
        """Create a trend-based alert rule."""
        rule_id = f"trend_{uuid4().hex[:8]}"
        
        rule = AlertRule(
            id=rule_id,
            name=name,
            description=description,
            category=category,
            rule_type=AlertRuleType.TREND,
            level=level,
            priority=priority,
            conditions={
                "metric_name": metric_name,
                "trend_threshold": trend_threshold
            },
            trend_config={
                "window_size": window_size,
                "trend_threshold": trend_threshold,
                "check_interval_minutes": 1
            },
            escalation_config={
                "escalate_after_minutes": 20,
                "max_escalation_level": 2
            },
            tags=tags or {}
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created trend rule: {rule_id} - {name}")
        return rule
    
    def create_composite_rule(
        self,
        name: str,
        description: str,
        category: AlertCategory,
        conditions: List[Dict[str, Any]],
        logic: str = "AND",
        level: AlertLevel = AlertLevel.WARNING,
        priority: AlertPriority = AlertPriority.NORMAL,
        tags: Optional[Dict[str, str]] = None
    ) -> AlertRule:
        """Create a composite alert rule with multiple conditions."""
        rule_id = f"composite_{uuid4().hex[:8]}"
        
        rule = AlertRule(
            id=rule_id,
            name=name,
            description=description,
            category=category,
            rule_type=AlertRuleType.COMPOSITE,
            level=level,
            priority=priority,
            composite_config={
                "conditions": conditions,
                "logic": logic
            },
            escalation_config={
                "escalate_after_minutes": 25,
                "max_escalation_level": 2
            },
            tags=tags or {}
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created composite rule: {rule_id} - {name}")
        return rule
    
    def create_frequency_rule(
        self,
        name: str,
        description: str,
        category: AlertCategory,
        metric_name: str,
        threshold: int,
        time_window_minutes: int = 5,
        level: AlertLevel = AlertLevel.WARNING,
        priority: AlertPriority = AlertPriority.NORMAL,
        tags: Optional[Dict[str, str]] = None
    ) -> AlertRule:
        """Create a frequency-based alert rule."""
        rule_id = f"frequency_{uuid4().hex[:8]}"
        
        rule = AlertRule(
            id=rule_id,
            name=name,
            description=description,
            category=category,
            rule_type=AlertRuleType.FREQUENCY,
            level=level,
            priority=priority,
            conditions={
                "metric_name": metric_name,
                "threshold": threshold
            },
            frequency_config={
                "threshold": threshold,
                "time_window_minutes": time_window_minutes,
                "check_interval_minutes": 1
            },
            escalation_config={
                "escalate_after_minutes": 10,
                "max_escalation_level": 3
            },
            tags=tags or {}
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created frequency rule: {rule_id} - {name}")
        return rule
    
    def create_anomaly_rule(
        self,
        name: str,
        description: str,
        category: AlertCategory,
        metric_name: str,
        sensitivity: float = 2.0,
        algorithm: str = "statistical",
        level: AlertLevel = AlertLevel.WARNING,
        priority: AlertPriority = AlertPriority.NORMAL,
        tags: Optional[Dict[str, str]] = None
    ) -> AlertRule:
        """Create an anomaly detection alert rule."""
        rule_id = f"anomaly_{uuid4().hex[:8]}"
        
        rule = AlertRule(
            id=rule_id,
            name=name,
            description=description,
            category=category,
            rule_type=AlertRuleType.ANOMALY,
            level=level,
            priority=priority,
            conditions={
                "metric_name": metric_name
            },
            anomaly_config={
                "algorithm": algorithm,
                "sensitivity": sensitivity,
                "window_size": 50,
                "min_samples": 10,
                "z_score_threshold": sensitivity
            },
            escalation_config={
                "escalate_after_minutes": 20,
                "max_escalation_level": 2
            },
            tags=tags or {}
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created anomaly rule: {rule_id} - {name}")
        return rule
    
    async def evaluate_rules(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Evaluate all enabled rules against provided metrics."""
        alerts = []
        self.evaluation_stats["total_evaluations"] += 1
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            try:
                alert = await self._evaluate_single_rule(rule, metrics)
                if alert:
                    alerts.append(alert)
                    self.evaluation_stats["alerts_generated"] += 1
                    self.evaluation_stats["by_rule_type"][rule.rule_type.value] += 1
                    self.evaluation_stats["by_level"][rule.level.value] += 1
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")
        
        # Store alerts
        for alert in alerts:
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
        
        return alerts
    
    async def _evaluate_single_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate a single rule against metrics."""
        if rule.rule_type == AlertRuleType.THRESHOLD:
            return await self._evaluate_threshold_rule(rule, metrics)
        elif rule.rule_type == AlertRuleType.TREND:
            return await self._evaluate_trend_rule(rule, metrics)
        elif rule.rule_type == AlertRuleType.COMPOSITE:
            return await self._evaluate_composite_rule(rule, metrics)
        elif rule.rule_type == AlertRuleType.FREQUENCY:
            return await self._evaluate_frequency_rule(rule, metrics)
        elif rule.rule_type == AlertRuleType.ANOMALY:
            return await self._evaluate_anomaly_rule(rule, metrics)
        
        return None
    
    async def _evaluate_threshold_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate threshold-based rule."""
        metric_name = rule.conditions.get("metric_name")
        operator = rule.conditions.get("operator")
        threshold = rule.conditions.get("threshold")
        
        if not all([metric_name, operator, threshold is not None]):
            return None
        
        metric_value = metrics.get(metric_name)
        if metric_value is None:
            return None
        
        # Record metric history
        self.metric_history[metric_name].append({
            "value": metric_value,
            "timestamp": datetime.now()
        })
        
        # Check threshold condition
        triggered = False
        if operator == "gt" and metric_value > threshold:
            triggered = True
        elif operator == "gte" and metric_value >= threshold:
            triggered = True
        elif operator == "lt" and metric_value < threshold:
            triggered = True
        elif operator == "lte" and metric_value <= threshold:
            triggered = True
        elif operator == "eq" and metric_value == threshold:
            triggered = True
        elif operator == "ne" and metric_value != threshold:
            triggered = True
        
        if triggered:
            return Alert(
                id=uuid4(),
                rule_id=rule.id,
                category=rule.category,
                level=rule.level,
                priority=rule.priority,
                title=f"{rule.name}",
                message=f"Metric {metric_name} value {metric_value} {operator} threshold {threshold}",
                source="threshold_monitor",
                metric_name=metric_name,
                metric_value=metric_value,
                threshold_value=threshold,
                context={
                    "rule_type": "threshold",
                    "operator": operator,
                    "rule_description": rule.description
                },
                tags={**rule.tags, "rule_id": rule.id, "category": rule.category.value}
            )
        
        return None
    
    async def _evaluate_trend_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate trend-based rule."""
        metric_name = rule.conditions.get("metric_name")
        trend_threshold = rule.conditions.get("trend_threshold")
        
        if not all([metric_name, trend_threshold is not None]):
            return None
        
        metric_value = metrics.get(metric_name)
        if metric_value is None:
            return None
        
        # Record metric history
        self.metric_history[metric_name].append({
            "value": metric_value,
            "timestamp": datetime.now()
        })
        
        trend_config = rule.trend_config or {}
        window_size = trend_config.get("window_size", 10)
        
        history = list(self.metric_history[metric_name])
        if len(history) < window_size:
            return None
        
        # Calculate trend (simple linear regression slope)
        recent_values = [h["value"] for h in history[-window_size:]]
        if len(recent_values) < 2:
            return None
        
        x = list(range(len(recent_values)))
        y = recent_values
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        if n * sum_x2 - sum_x ** 2 == 0:
            return None
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # Check if trend exceeds threshold
        if abs(slope) > trend_threshold:
            trend_direction = "increasing" if slope > 0 else "decreasing"
            
            return Alert(
                id=uuid4(),
                rule_id=rule.id,
                category=rule.category,
                level=rule.level,
                priority=rule.priority,
                title=f"{rule.name}",
                message=f"Metric {metric_name} shows {trend_direction} trend with slope {slope:.4f}",
                source="trend_monitor",
                metric_name=metric_name,
                metric_value=metric_value,
                context={
                    "rule_type": "trend",
                    "slope": slope,
                    "trend_direction": trend_direction,
                    "window_size": window_size,
                    "rule_description": rule.description
                },
                tags={**rule.tags, "rule_id": rule.id, "category": rule.category.value}
            )
        
        return None
    
    async def _evaluate_composite_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate composite rule with multiple conditions."""
        composite_config = rule.composite_config
        if not composite_config:
            return None
        
        conditions = composite_config.get("conditions", [])
        logic = composite_config.get("logic", "AND")
        
        results = []
        condition_details = []
        
        for condition in conditions:
            metric_name = condition.get("metric_name")
            operator = condition.get("operator")
            threshold = condition.get("threshold")
            
            if not all([metric_name, operator, threshold is not None]):
                results.append(False)
                continue
            
            metric_value = metrics.get(metric_name)
            if metric_value is None:
                results.append(False)
                continue
            
            # Evaluate condition
            condition_result = False
            if operator == "gt":
                condition_result = metric_value > threshold
            elif operator == "gte":
                condition_result = metric_value >= threshold
            elif operator == "lt":
                condition_result = metric_value < threshold
            elif operator == "lte":
                condition_result = metric_value <= threshold
            elif operator == "eq":
                condition_result = metric_value == threshold
            elif operator == "ne":
                condition_result = metric_value != threshold
            
            results.append(condition_result)
            condition_details.append({
                "metric_name": metric_name,
                "value": metric_value,
                "operator": operator,
                "threshold": threshold,
                "result": condition_result
            })
        
        # Apply logic
        if logic == "AND":
            triggered = all(results)
        elif logic == "OR":
            triggered = any(results)
        else:
            triggered = False
        
        if triggered:
            return Alert(
                id=uuid4(),
                rule_id=rule.id,
                category=rule.category,
                level=rule.level,
                priority=rule.priority,
                title=f"{rule.name}",
                message=f"Composite condition triggered with logic: {logic}",
                source="composite_monitor",
                context={
                    "rule_type": "composite",
                    "logic": logic,
                    "conditions": condition_details,
                    "rule_description": rule.description
                },
                tags={**rule.tags, "rule_id": rule.id, "category": rule.category.value}
            )
        
        return None
    
    async def _evaluate_frequency_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate frequency-based rule."""
        metric_name = rule.conditions.get("metric_name")
        threshold = rule.conditions.get("threshold")
        
        if not all([metric_name, threshold is not None]):
            return None
        
        metric_value = metrics.get(metric_name)
        if metric_value is None:
            return None
        
        frequency_config = rule.frequency_config or {}
        time_window_minutes = frequency_config.get("time_window_minutes", 5)
        
        # Record frequency event
        now = datetime.now()
        counter_key = f"{rule.id}:{metric_name}"
        self.frequency_counters[counter_key].append(now)
        
        # Clean old entries
        cutoff = now - timedelta(minutes=time_window_minutes)
        counter = self.frequency_counters[counter_key]
        while counter and counter[0] < cutoff:
            counter.popleft()
        
        # Check frequency threshold
        if len(counter) >= threshold:
            return Alert(
                id=uuid4(),
                rule_id=rule.id,
                category=rule.category,
                level=rule.level,
                priority=rule.priority,
                title=f"{rule.name}",
                message=f"Frequency threshold exceeded: {len(counter)} events in {time_window_minutes} minutes",
                source="frequency_monitor",
                metric_name=metric_name,
                metric_value=len(counter),
                threshold_value=threshold,
                context={
                    "rule_type": "frequency",
                    "event_count": len(counter),
                    "time_window_minutes": time_window_minutes,
                    "rule_description": rule.description
                },
                tags={**rule.tags, "rule_id": rule.id, "category": rule.category.value}
            )
        
        return None
    
    async def _evaluate_anomaly_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate anomaly detection rule."""
        metric_name = rule.conditions.get("metric_name")
        if not metric_name:
            return None
        
        metric_value = metrics.get(metric_name)
        if metric_value is None:
            return None
        
        # Record metric history
        self.metric_history[metric_name].append({
            "value": metric_value,
            "timestamp": datetime.now()
        })
        
        anomaly_config = rule.anomaly_config or {}
        window_size = anomaly_config.get("window_size", 50)
        min_samples = anomaly_config.get("min_samples", 10)
        z_threshold = anomaly_config.get("z_score_threshold", 2.0)
        
        history = list(self.metric_history[metric_name])
        if len(history) < min_samples:
            return None
        
        # Get historical values (excluding current)
        historical_values = [h["value"] for h in history[:-1]]
        if len(historical_values) < min_samples:
            return None
        
        # Calculate statistical measures
        import statistics
        mean_val = statistics.mean(historical_values)
        std_val = statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        
        if std_val == 0:
            return None
        
        # Calculate Z-score
        z_score = abs(metric_value - mean_val) / std_val
        
        if z_score > z_threshold:
            return Alert(
                id=uuid4(),
                rule_id=rule.id,
                category=rule.category,
                level=rule.level,
                priority=rule.priority,
                title=f"{rule.name}",
                message=f"Anomaly detected in {metric_name} with Z-score: {z_score:.2f}",
                source="anomaly_detector",
                metric_name=metric_name,
                metric_value=metric_value,
                context={
                    "rule_type": "anomaly",
                    "z_score": z_score,
                    "mean": mean_val,
                    "std": std_val,
                    "threshold": z_threshold,
                    "rule_description": rule.description
                },
                tags={**rule.tags, "rule_id": rule.id, "category": rule.category.value}
            )
        
        return None
    
    # Rule management methods
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get rule by ID."""
        return self.rules.get(rule_id)
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update rule configuration."""
        rule = self.rules.get(rule_id)
        if not rule:
            return False
        
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.now()
        logger.info(f"Updated alert rule: {rule_id}")
        return True
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Deleted alert rule: {rule_id}")
            return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable rule."""
        rule = self.rules.get(rule_id)
        if rule:
            rule.enabled = True
            rule.updated_at = datetime.now()
            logger.info(f"Enabled alert rule: {rule_id}")
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable rule."""
        rule = self.rules.get(rule_id)
        if rule:
            rule.enabled = False
            rule.updated_at = datetime.now()
            logger.info(f"Disabled alert rule: {rule_id}")
            return True
        return False
    
    def list_rules(
        self,
        category: Optional[AlertCategory] = None,
        rule_type: Optional[AlertRuleType] = None,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """List rules with optional filtering."""
        rules = list(self.rules.values())
        
        if category:
            rules = [r for r in rules if r.category == category]
        
        if rule_type:
            rules = [r for r in rules if r.rule_type == rule_type]
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        return [rule.to_dict() for rule in rules]
    
    # Alert management methods
    
    async def acknowledge_alert(self, alert_id: UUID, acknowledged_by: str) -> bool:
        """Acknowledge alert."""
        alert = self.active_alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = acknowledged_by
        
        logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        return True
    
    async def resolve_alert(self, alert_id: UUID, resolved_by: str, resolution_notes: Optional[str] = None) -> bool:
        """Resolve alert."""
        alert = self.active_alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        alert.resolved_by = resolved_by
        
        if resolution_notes:
            alert.context["resolution_notes"] = resolution_notes
        
        # Remove from active alerts
        del self.active_alerts[alert_id]
        
        logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
        return True
    
    def get_active_alerts(
        self,
        category: Optional[AlertCategory] = None,
        level: Optional[AlertLevel] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get active alerts."""
        alerts = list(self.active_alerts.values())
        
        if category:
            alerts = [a for a in alerts if a.category == category]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        # Sort by priority and creation time
        alerts.sort(key=lambda x: (-x.priority.value, -x.created_at.timestamp()))
        
        return [alert.to_dict() for alert in alerts[:limit]]
    
    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """Get rule evaluation statistics."""
        return {
            "total_evaluations": self.evaluation_stats["total_evaluations"],
            "alerts_generated": self.evaluation_stats["alerts_generated"],
            "by_rule_type": dict(self.evaluation_stats["by_rule_type"]),
            "by_level": dict(self.evaluation_stats["by_level"]),
            "active_alerts_count": len(self.active_alerts),
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
            "generated_at": datetime.now().isoformat()
        }


# Global instance
alert_rule_engine = AlertRuleEngine()