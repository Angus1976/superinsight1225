"""
Alert Rules Manager for High Availability Monitoring.

Manages alert rules for Prometheus/Alertmanager integration,
providing dynamic rule configuration and management.
"""

import logging
import time
import json
import yaml
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertState(Enum):
    """Alert states."""
    INACTIVE = "inactive"
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    """Definition of an alert rule."""
    rule_id: str
    name: str
    expression: str
    duration: str  # e.g., "5m", "1h"
    severity: AlertSeverity
    summary: str
    description: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    group: str = "default"


@dataclass
class AlertInstance:
    """An instance of a firing alert."""
    alert_id: str
    rule: AlertRule
    state: AlertState
    started_at: float
    resolved_at: Optional[float] = None
    labels: Dict[str, str] = field(default_factory=dict)
    value: Optional[float] = None


@dataclass
class AlertRulesConfig:
    """Configuration for alert rules manager."""
    rules_file: str = "config/alert_rules.yml"
    prometheus_rules_file: str = "prometheus_rules.yml"
    auto_reload: bool = True
    reload_interval: int = 60


class AlertRulesManager:
    """
    Manages alert rules for high availability monitoring.
    
    Features:
    - Dynamic alert rule management
    - Prometheus rule file generation
    - Alert state tracking
    - Rule validation
    - Group management
    """
    
    def __init__(self, config: Optional[AlertRulesConfig] = None):
        self.config = config or AlertRulesConfig()
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, AlertInstance] = {}
        self.alert_history: List[AlertInstance] = []
        self.rule_groups: Dict[str, List[str]] = {}
        
        # Load default HA alert rules
        self._load_default_rules()
        
        logger.info("AlertRulesManager initialized")
    
    def _load_default_rules(self):
        """Load default high availability alert rules."""
        default_rules = [
            # System availability alerts
            AlertRule(
                rule_id="ha_low_availability",
                name="SystemAvailabilityLow",
                expression="ha_system_availability_percentage < 99.9",
                duration="5m",
                severity=AlertSeverity.CRITICAL,
                summary="System availability below SLA threshold",
                description="System availability is {{ $value }}%, below the 99.9% SLA threshold",
                labels={"component": "system", "team": "platform"},
                group="high_availability"
            ),
            AlertRule(
                rule_id="ha_service_unhealthy",
                name="ServiceHealthDegraded",
                expression="ha_service_health_score < 80",
                duration="2m",
                severity=AlertSeverity.WARNING,
                summary="Service health degraded",
                description="Service {{ $labels.service_name }} health score is {{ $value }}",
                labels={"component": "service"},
                group="high_availability"
            ),
            AlertRule(
                rule_id="ha_service_critical",
                name="ServiceHealthCritical",
                expression="ha_service_health_score < 50",
                duration="1m",
                severity=AlertSeverity.CRITICAL,
                summary="Service health critical",
                description="Service {{ $labels.service_name }} health score is critically low at {{ $value }}",
                labels={"component": "service"},
                group="high_availability"
            ),
            
            # Recovery alerts
            AlertRule(
                rule_id="ha_recovery_failed",
                name="RecoveryOperationFailed",
                expression='increase(ha_recovery_attempts_total{status="failure"}[10m]) > 2',
                duration="1m",
                severity=AlertSeverity.CRITICAL,
                summary="Multiple recovery failures detected",
                description="More than 2 recovery failures in the last 10 minutes",
                labels={"component": "recovery"},
                group="high_availability"
            ),
            AlertRule(
                rule_id="ha_recovery_slow",
                name="RecoveryOperationSlow",
                expression="histogram_quantile(0.95, rate(ha_recovery_duration_seconds_bucket[5m])) > 300",
                duration="5m",
                severity=AlertSeverity.WARNING,
                summary="Recovery operations are slow",
                description="95th percentile recovery time exceeds 5 minutes",
                labels={"component": "recovery"},
                group="high_availability"
            ),
            
            # Failover alerts
            AlertRule(
                rule_id="ha_failover_occurred",
                name="FailoverOccurred",
                expression='increase(ha_failover_total{status="success"}[5m]) > 0',
                duration="0m",
                severity=AlertSeverity.WARNING,
                summary="Failover operation occurred",
                description="A failover operation was performed from {{ $labels.from_node }} to {{ $labels.to_node }}",
                labels={"component": "failover"},
                group="high_availability"
            ),
            AlertRule(
                rule_id="ha_failover_failed",
                name="FailoverFailed",
                expression='increase(ha_failover_total{status="failure"}[5m]) > 0',
                duration="0m",
                severity=AlertSeverity.EMERGENCY,
                summary="Failover operation failed",
                description="A failover operation failed from {{ $labels.from_node }} to {{ $labels.to_node }}",
                labels={"component": "failover"},
                group="high_availability"
            ),
            
            # Backup alerts
            AlertRule(
                rule_id="ha_backup_failed",
                name="BackupOperationFailed",
                expression='increase(ha_backup_operations_total{status="failure"}[1h]) > 0',
                duration="0m",
                severity=AlertSeverity.CRITICAL,
                summary="Backup operation failed",
                description="A {{ $labels.backup_type }} backup operation failed",
                labels={"component": "backup"},
                group="high_availability"
            ),
            AlertRule(
                rule_id="ha_backup_stale",
                name="BackupStale",
                expression="time() - ha_backup_last_success_timestamp > 86400",
                duration="1h",
                severity=AlertSeverity.WARNING,
                summary="No successful backup in 24 hours",
                description="No successful backup has been completed in the last 24 hours",
                labels={"component": "backup"},
                group="high_availability"
            ),
            
            # Node status alerts
            AlertRule(
                rule_id="ha_node_down",
                name="NodeDown",
                expression="ha_node_status == -1",
                duration="1m",
                severity=AlertSeverity.CRITICAL,
                summary="Node is down",
                description="Node {{ $labels.node }} is in failed state",
                labels={"component": "node"},
                group="high_availability"
            ),
            AlertRule(
                rule_id="ha_no_standby",
                name="NoStandbyNodes",
                expression="ha_standby_nodes_count == 0",
                duration="5m",
                severity=AlertSeverity.WARNING,
                summary="No standby nodes available",
                description="There are no standby nodes available for failover",
                labels={"component": "node"},
                group="high_availability"
            ),
            
            # Health check alerts
            AlertRule(
                rule_id="ha_health_check_failed",
                name="HealthCheckFailed",
                expression="ha_health_check_status == 0",
                duration="2m",
                severity=AlertSeverity.WARNING,
                summary="Health check failing",
                description="Health check {{ $labels.check_name }} is failing for service {{ $labels.service }}",
                labels={"component": "health"},
                group="high_availability"
            ),
            AlertRule(
                rule_id="ha_health_check_slow",
                name="HealthCheckSlow",
                expression="histogram_quantile(0.95, rate(ha_health_check_duration_seconds_bucket[5m])) > 5",
                duration="5m",
                severity=AlertSeverity.INFO,
                summary="Health checks are slow",
                description="95th percentile health check duration exceeds 5 seconds",
                labels={"component": "health"},
                group="high_availability"
            ),
            
            # Data integrity alerts
            AlertRule(
                rule_id="ha_data_integrity_low",
                name="DataIntegrityLow",
                expression="ha_data_integrity_score < 0.95",
                duration="5m",
                severity=AlertSeverity.CRITICAL,
                summary="Data integrity score low",
                description="Data integrity score for {{ $labels.component }} is {{ $value }}",
                labels={"component": "data"},
                group="high_availability"
            ),
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: AlertRule) -> bool:
        """Add an alert rule."""
        if rule.rule_id in self.rules:
            logger.warning(f"Rule {rule.rule_id} already exists, updating")
        
        self.rules[rule.rule_id] = rule
        
        # Add to group
        if rule.group not in self.rule_groups:
            self.rule_groups[rule.group] = []
        if rule.rule_id not in self.rule_groups[rule.group]:
            self.rule_groups[rule.group].append(rule.rule_id)
        
        logger.info(f"Added alert rule: {rule.name}")
        return True
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        
        # Remove from group
        if rule.group in self.rule_groups:
            if rule_id in self.rule_groups[rule.group]:
                self.rule_groups[rule.group].remove(rule_id)
        
        del self.rules[rule_id]
        logger.info(f"Removed alert rule: {rule_id}")
        return True
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable an alert rule."""
        if rule_id not in self.rules:
            return False
        
        self.rules[rule_id].enabled = True
        logger.info(f"Enabled alert rule: {rule_id}")
        return True
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable an alert rule."""
        if rule_id not in self.rules:
            return False
        
        self.rules[rule_id].enabled = False
        logger.info(f"Disabled alert rule: {rule_id}")
        return True
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get an alert rule by ID."""
        return self.rules.get(rule_id)
    
    def list_rules(
        self,
        group: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        enabled_only: bool = False
    ) -> List[AlertRule]:
        """List alert rules with optional filtering."""
        rules = list(self.rules.values())
        
        if group:
            rules = [r for r in rules if r.group == group]
        
        if severity:
            rules = [r for r in rules if r.severity == severity]
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        return rules
    
    def list_groups(self) -> List[str]:
        """List all rule groups."""
        return list(self.rule_groups.keys())
    
    def generate_prometheus_rules(self) -> str:
        """Generate Prometheus alerting rules in YAML format."""
        groups = {}
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            if rule.group not in groups:
                groups[rule.group] = []
            
            rule_config = {
                "alert": rule.name,
                "expr": rule.expression,
                "for": rule.duration,
                "labels": {
                    "severity": rule.severity.value,
                    **rule.labels
                },
                "annotations": {
                    "summary": rule.summary,
                    "description": rule.description,
                    **rule.annotations
                }
            }
            
            groups[rule.group].append(rule_config)
        
        prometheus_config = {
            "groups": [
                {
                    "name": group_name,
                    "rules": rules
                }
                for group_name, rules in groups.items()
            ]
        }
        
        return yaml.dump(prometheus_config, default_flow_style=False)
    
    def save_prometheus_rules(self, file_path: Optional[str] = None) -> bool:
        """Save Prometheus rules to file."""
        file_path = file_path or self.config.prometheus_rules_file
        
        try:
            rules_yaml = self.generate_prometheus_rules()
            
            with open(file_path, 'w') as f:
                f.write(rules_yaml)
            
            logger.info(f"Saved Prometheus rules to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save Prometheus rules: {e}")
            return False
    
    def fire_alert(
        self,
        rule_id: str,
        labels: Optional[Dict[str, str]] = None,
        value: Optional[float] = None
    ) -> Optional[AlertInstance]:
        """Fire an alert for a rule."""
        rule = self.rules.get(rule_id)
        if not rule or not rule.enabled:
            return None
        
        alert_id = f"{rule_id}_{int(time.time())}"
        
        alert = AlertInstance(
            alert_id=alert_id,
            rule=rule,
            state=AlertState.FIRING,
            started_at=time.time(),
            labels=labels or {},
            value=value
        )
        
        self.active_alerts[alert_id] = alert
        
        logger.warning(f"Alert fired: {rule.name} ({alert_id})")
        return alert
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.state = AlertState.RESOLVED
        alert.resolved_at = time.time()
        
        # Move to history
        self.alert_history.append(alert)
        del self.active_alerts[alert_id]
        
        # Keep history limited
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        logger.info(f"Alert resolved: {alert.rule.name} ({alert_id})")
        return True
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None
    ) -> List[AlertInstance]:
        """Get active alerts."""
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.rule.severity == severity]
        
        return alerts
    
    def get_alert_history(
        self,
        limit: int = 100,
        rule_id: Optional[str] = None
    ) -> List[AlertInstance]:
        """Get alert history."""
        history = self.alert_history
        
        if rule_id:
            history = [a for a in history if a.rule.rule_id == rule_id]
        
        return history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        active = list(self.active_alerts.values())
        history = self.alert_history
        
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
            "active_alerts": len(active),
            "active_by_severity": {
                s.value: len([a for a in active if a.rule.severity == s])
                for s in AlertSeverity
            },
            "total_alerts_fired": len(history) + len(active),
            "rule_groups": len(self.rule_groups),
        }


# Global alert rules manager
alert_rules_manager = AlertRulesManager()


def get_alert_rules_manager() -> AlertRulesManager:
    """Get the global alert rules manager."""
    return alert_rules_manager
