"""
Monitoring and Alerting System Integration Tests

Tests monitoring metrics collection, alert rule evaluation, and notification systems,
verifying system performance monitoring and stability.

Task 9.3: 监控告警系统测试
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from decimal import Decimal
from uuid import uuid4
from enum import Enum
import asyncio
import time


# =============================================================================
# Test Data Models for Monitoring and Alerting
# =============================================================================

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"


class AlertForTest:
    """Test alert for monitoring system testing"""
    
    def __init__(self, rule_name: str, severity: AlertSeverity, 
                 message: str, metric_value: float):
        self.id = str(uuid4())
        self.rule_name = rule_name
        self.severity = severity
        self.message = message
        self.metric_value = metric_value
        self.status = AlertStatus.ACTIVE
        self.created_at = datetime.now()
        self.acknowledged_at = None
        self.resolved_at = None
        self.metadata = {}


class MetricForTest:
    """Test metric for monitoring system testing"""
    
    def __init__(self, name: str, metric_type: MetricType, 
                 value: float, labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.type = metric_type
        self.value = value
        self.labels = labels or {}
        self.timestamp = datetime.now()
        self.samples = []  # For histogram/summary types


class AlertRuleForTest:
    """Test alert rule for monitoring system testing"""
    
    def __init__(self, name: str, metric_name: str, condition: str, 
                 threshold: float, severity: AlertSeverity):
        self.name = name
        self.metric_name = metric_name
        self.condition = condition  # "gt", "lt", "eq", "gte", "lte"
        self.threshold = threshold
        self.severity = severity
        self.enabled = True
        self.evaluation_interval = 30  # seconds
        self.for_duration = 60  # seconds - how long condition must be true
        self.labels = {}
        self.annotations = {}


# =============================================================================
# Mock Services for Monitoring and Alerting
# =============================================================================

class MockMetricsCollector:
    """Mock metrics collector for testing"""
    
    def __init__(self):
        self.metrics = {}
        self.metric_history = []
        self.collection_interval = 10  # seconds
        self.is_collecting = False
        
    def register_metric(self, metric: MetricForTest):
        """Register a metric for collection"""
        self.metrics[metric.name] = metric
        
    def collect_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Collect a metric value"""
        if name not in self.metrics:
            return False
            
        metric = self.metrics[name]
        metric.value = value
        metric.timestamp = datetime.now()
        if labels:
            metric.labels.update(labels)
            
        # Store in history
        self.metric_history.append({
            "name": name,
            "value": value,
            "timestamp": metric.timestamp,
            "labels": metric.labels.copy()
        })
        
        return True
    
    def get_metric_value(self, name: str) -> Optional[float]:
        """Get current metric value"""
        if name in self.metrics:
            return self.metrics[name].value
        return None
    
    def get_metric_history(self, name: str, duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metric history for specified duration"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        return [
            entry for entry in self.metric_history
            if entry["name"] == name and entry["timestamp"] >= cutoff_time
        ]
    
    def start_collection(self):
        """Start metrics collection"""
        self.is_collecting = True
        
    def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
    
    def simulate_system_metrics(self):
        """Simulate system metrics collection"""
        import random
        
        # Simulate CPU usage
        cpu_usage = 20 + random.uniform(0, 60)  # 20-80%
        self.collect_metric("system_cpu_usage_percent", cpu_usage)
        
        # Simulate memory usage
        memory_usage = 30 + random.uniform(0, 50)  # 30-80%
        self.collect_metric("system_memory_usage_percent", memory_usage)
        
        # Simulate response time
        response_time = 100 + random.uniform(0, 400)  # 100-500ms
        self.collect_metric("api_response_time_ms", response_time)
        
        # Simulate error rate
        error_rate = random.uniform(0, 5)  # 0-5%
        self.collect_metric("api_error_rate_percent", error_rate)


class MockAlertManager:
    """Mock alert manager for testing"""
    
    def __init__(self):
        self.rules = {}
        self.active_alerts = {}
        self.alert_history = []
        self.notification_handlers = []
        self.evaluation_interval = 30
        self.is_evaluating = False
        
    def add_rule(self, rule: AlertRuleForTest):
        """Add alert rule"""
        self.rules[rule.name] = rule
        
    def remove_rule(self, rule_name: str) -> bool:
        """Remove alert rule"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            return True
        return False
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable alert rule"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
            return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable alert rule"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
            return True
        return False
    
    def evaluate_rules(self, metrics_collector: MockMetricsCollector):
        """Evaluate all alert rules against current metrics"""
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
                
            metric_value = metrics_collector.get_metric_value(rule.metric_name)
            if metric_value is None:
                continue
                
            should_alert = self._evaluate_condition(rule, metric_value)
            
            if should_alert and rule_name not in self.active_alerts:
                # Fire new alert
                alert = AlertForTest(
                    rule_name=rule_name,
                    severity=rule.severity,
                    message=f"{rule.metric_name} {rule.condition} {rule.threshold} (current: {metric_value})",
                    metric_value=metric_value
                )
                self._fire_alert(alert)
                
            elif not should_alert and rule_name in self.active_alerts:
                # Resolve existing alert
                self._resolve_alert(rule_name)
    
    def _evaluate_condition(self, rule: AlertRuleForTest, value: float) -> bool:
        """Evaluate alert condition"""
        if rule.condition == "gt":
            return value > rule.threshold
        elif rule.condition == "lt":
            return value < rule.threshold
        elif rule.condition == "gte":
            return value >= rule.threshold
        elif rule.condition == "lte":
            return value <= rule.threshold
        elif rule.condition == "eq":
            return abs(value - rule.threshold) < 0.001
        return False
    
    def _fire_alert(self, alert: AlertForTest):
        """Fire an alert"""
        self.active_alerts[alert.rule_name] = alert
        self.alert_history.append(alert)
        
        # Send notifications
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                print(f"Notification handler error: {e}")
    
    def _resolve_alert(self, rule_name: str):
        """Resolve an alert"""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            del self.active_alerts[rule_name]
    
    def acknowledge_alert(self, rule_name: str) -> bool:
        """Acknowledge an alert"""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now()
            return True
        return False
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[AlertForTest]:
        """Get active alerts"""
        alerts = list(self.active_alerts.values())
        
        if severity_filter:
            alerts = [a for a in alerts if a.severity == severity_filter]
            
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    def get_alert_summary(self) -> Dict[str, int]:
        """Get alert summary by severity"""
        summary = {severity.value: 0 for severity in AlertSeverity}
        
        for alert in self.active_alerts.values():
            summary[alert.severity.value] += 1
            
        return summary
    
    def add_notification_handler(self, handler: Callable[[AlertForTest], None]):
        """Add notification handler"""
        self.notification_handlers.append(handler)


class MockNotificationService:
    """Mock notification service for testing"""
    
    def __init__(self):
        self.sent_notifications = []
        self.channels = {}
        self.delivery_success_rate = 0.95  # 95% success rate
        
    def configure_channel(self, channel: NotificationChannel, config: Dict[str, Any]):
        """Configure notification channel"""
        self.channels[channel] = config
        
    def send_notification(self, alert: AlertForTest, channels: List[NotificationChannel]) -> Dict[str, bool]:
        """Send notification through specified channels"""
        results = {}
        
        for channel in channels:
            if channel not in self.channels:
                results[channel.value] = False
                continue
                
            # Simulate delivery
            import random
            success = random.random() < self.delivery_success_rate
            results[channel.value] = success
            
            if success:
                notification = {
                    "id": str(uuid4()),
                    "alert_id": alert.id,
                    "channel": channel.value,
                    "message": alert.message,
                    "sent_at": datetime.now(),
                    "delivered": True
                }
                self.sent_notifications.append(notification)
        
        return results
    
    def get_notification_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get notification history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            notif for notif in self.sent_notifications
            if notif["sent_at"] >= cutoff_time
        ]


class MockDashboardService:
    """Mock dashboard service for testing"""
    
    def __init__(self):
        self.dashboards = {}
        self.dashboard_views = []
        
    def create_dashboard(self, name: str, metrics: List[str]) -> str:
        """Create monitoring dashboard"""
        dashboard_id = str(uuid4())
        
        dashboard = {
            "id": dashboard_id,
            "name": name,
            "metrics": metrics,
            "created_at": datetime.now(),
            "panels": [],
            "refresh_interval": 30
        }
        
        self.dashboards[dashboard_id] = dashboard
        return dashboard_id
    
    def add_panel(self, dashboard_id: str, panel_config: Dict[str, Any]) -> bool:
        """Add panel to dashboard"""
        if dashboard_id not in self.dashboards:
            return False
            
        panel = {
            "id": str(uuid4()),
            "type": panel_config.get("type", "graph"),
            "title": panel_config.get("title", "Untitled Panel"),
            "metrics": panel_config.get("metrics", []),
            "time_range": panel_config.get("time_range", "1h")
        }
        
        self.dashboards[dashboard_id]["panels"].append(panel)
        return True
    
    def view_dashboard(self, dashboard_id: str, metrics_collector: MockMetricsCollector) -> Dict[str, Any]:
        """View dashboard with current data"""
        if dashboard_id not in self.dashboards:
            return {"error": "Dashboard not found"}
            
        dashboard = self.dashboards[dashboard_id]
        
        # Collect current metric values
        current_data = {}
        for metric_name in dashboard["metrics"]:
            current_data[metric_name] = metrics_collector.get_metric_value(metric_name)
        
        view_data = {
            "dashboard_id": dashboard_id,
            "name": dashboard["name"],
            "viewed_at": datetime.now(),
            "current_data": current_data,
            "panels_count": len(dashboard["panels"])
        }
        
        self.dashboard_views.append(view_data)
        return view_data


# =============================================================================
# Integration Test Fixtures
# =============================================================================

@pytest.fixture
def metrics_collector():
    collector = MockMetricsCollector()
    
    # Register common system metrics
    collector.register_metric(MetricForTest("system_cpu_usage_percent", MetricType.GAUGE, 0.0))
    collector.register_metric(MetricForTest("system_memory_usage_percent", MetricType.GAUGE, 0.0))
    collector.register_metric(MetricForTest("api_response_time_ms", MetricType.HISTOGRAM, 0.0))
    collector.register_metric(MetricForTest("api_error_rate_percent", MetricType.GAUGE, 0.0))
    collector.register_metric(MetricForTest("quality_score_average", MetricType.GAUGE, 0.0))
    collector.register_metric(MetricForTest("billing_amount_total", MetricType.COUNTER, 0.0))
    
    return collector

@pytest.fixture
def alert_manager():
    return MockAlertManager()

@pytest.fixture
def notification_service():
    service = MockNotificationService()
    
    # Configure notification channels
    service.configure_channel(NotificationChannel.EMAIL, {
        "smtp_server": "smtp.example.com",
        "recipients": ["admin@example.com", "ops@example.com"]
    })
    service.configure_channel(NotificationChannel.SLACK, {
        "webhook_url": "https://hooks.slack.com/services/...",
        "channel": "#alerts"
    })
    
    return service

@pytest.fixture
def dashboard_service():
    return MockDashboardService()


# =============================================================================
# Monitoring System Integration Tests
# =============================================================================

class TestMonitoringSystemIntegration:
    """Test complete monitoring system integration"""
    
    def test_metrics_collection_and_alerting_workflow(self, metrics_collector, alert_manager, notification_service):
        """Test complete workflow from metrics collection to alerting"""
        
        # Phase 1: Setup alert rules
        rules = [
            AlertRuleForTest("high_cpu_usage", "system_cpu_usage_percent", "gt", 80.0, AlertSeverity.WARNING),
            AlertRuleForTest("critical_cpu_usage", "system_cpu_usage_percent", "gt", 95.0, AlertSeverity.CRITICAL),
            AlertRuleForTest("high_response_time", "api_response_time_ms", "gt", 1000.0, AlertSeverity.WARNING),
            AlertRuleForTest("low_quality_score", "quality_score_average", "lt", 0.7, AlertSeverity.CRITICAL)
        ]
        
        for rule in rules:
            alert_manager.add_rule(rule)
        
        # Setup notification handler
        notifications_sent = []
        def notification_handler(alert: AlertForTest):
            result = notification_service.send_notification(alert, [NotificationChannel.EMAIL, NotificationChannel.SLACK])
            notifications_sent.append({"alert": alert, "result": result})
        
        alert_manager.add_notification_handler(notification_handler)
        
        # Phase 2: Collect normal metrics (should not trigger alerts)
        metrics_collector.collect_metric("system_cpu_usage_percent", 45.0)
        metrics_collector.collect_metric("api_response_time_ms", 250.0)
        metrics_collector.collect_metric("quality_score_average", 0.85)
        
        alert_manager.evaluate_rules(metrics_collector)
        
        # Should have no active alerts
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 0
        
        # Phase 3: Collect metrics that trigger alerts
        metrics_collector.collect_metric("system_cpu_usage_percent", 85.0)  # Triggers high_cpu_usage
        metrics_collector.collect_metric("api_response_time_ms", 1200.0)    # Triggers high_response_time
        metrics_collector.collect_metric("quality_score_average", 0.65)     # Triggers low_quality_score
        
        alert_manager.evaluate_rules(metrics_collector)
        
        # Should have 3 active alerts
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 3
        
        # Verify alert severities
        warning_alerts = alert_manager.get_active_alerts(AlertSeverity.WARNING)
        critical_alerts = alert_manager.get_active_alerts(AlertSeverity.CRITICAL)
        
        assert len(warning_alerts) == 2  # high_cpu_usage, high_response_time
        assert len(critical_alerts) == 1  # low_quality_score
        
        # Verify notifications were sent
        assert len(notifications_sent) == 3
        
        # Phase 4: Resolve some alerts
        metrics_collector.collect_metric("system_cpu_usage_percent", 70.0)  # Below threshold
        metrics_collector.collect_metric("api_response_time_ms", 800.0)     # Below threshold
        
        alert_manager.evaluate_rules(metrics_collector)
        
        # Should have 1 active alert remaining
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].rule_name == "low_quality_score"
        
        # Phase 5: Test alert acknowledgment
        success = alert_manager.acknowledge_alert("low_quality_score")
        assert success is True
        
        acknowledged_alert = alert_manager.active_alerts["low_quality_score"]
        assert acknowledged_alert.status == AlertStatus.ACKNOWLEDGED
        
        return {
            "active_alerts": active_alerts,
            "notifications_sent": notifications_sent,
            "alert_summary": alert_manager.get_alert_summary()
        }
    
    def test_dashboard_integration_with_metrics(self, metrics_collector, dashboard_service):
        """Test dashboard integration with metrics collection"""
        
        # Create monitoring dashboard
        dashboard_id = dashboard_service.create_dashboard(
            "System Monitoring",
            ["system_cpu_usage_percent", "system_memory_usage_percent", "api_response_time_ms"]
        )
        
        # Add panels to dashboard
        panels = [
            {
                "type": "graph",
                "title": "CPU Usage",
                "metrics": ["system_cpu_usage_percent"],
                "time_range": "1h"
            },
            {
                "type": "graph", 
                "title": "Memory Usage",
                "metrics": ["system_memory_usage_percent"],
                "time_range": "1h"
            },
            {
                "type": "histogram",
                "title": "API Response Time",
                "metrics": ["api_response_time_ms"],
                "time_range": "30m"
            }
        ]
        
        for panel in panels:
            success = dashboard_service.add_panel(dashboard_id, panel)
            assert success is True
        
        # Collect some metrics
        metrics_collector.collect_metric("system_cpu_usage_percent", 65.0)
        metrics_collector.collect_metric("system_memory_usage_percent", 72.0)
        metrics_collector.collect_metric("api_response_time_ms", 350.0)
        
        # View dashboard
        dashboard_view = dashboard_service.view_dashboard(dashboard_id, metrics_collector)
        
        # Verify dashboard data
        assert dashboard_view["dashboard_id"] == dashboard_id
        assert dashboard_view["name"] == "System Monitoring"
        assert dashboard_view["panels_count"] == 3
        
        current_data = dashboard_view["current_data"]
        assert current_data["system_cpu_usage_percent"] == 65.0
        assert current_data["system_memory_usage_percent"] == 72.0
        assert current_data["api_response_time_ms"] == 350.0
    
    def test_alert_rule_management(self, alert_manager):
        """Test alert rule management operations"""
        
        # Add rules
        rules = [
            AlertRuleForTest("test_rule_1", "metric_1", "gt", 100.0, AlertSeverity.WARNING),
            AlertRuleForTest("test_rule_2", "metric_2", "lt", 50.0, AlertSeverity.CRITICAL)
        ]
        
        for rule in rules:
            alert_manager.add_rule(rule)
        
        assert len(alert_manager.rules) == 2
        
        # Test rule enabling/disabling
        success = alert_manager.disable_rule("test_rule_1")
        assert success is True
        assert alert_manager.rules["test_rule_1"].enabled is False
        
        success = alert_manager.enable_rule("test_rule_1")
        assert success is True
        assert alert_manager.rules["test_rule_1"].enabled is True
        
        # Test rule removal
        success = alert_manager.remove_rule("test_rule_2")
        assert success is True
        assert "test_rule_2" not in alert_manager.rules
        
        # Test operations on non-existent rules
        assert alert_manager.disable_rule("non_existent") is False
        assert alert_manager.enable_rule("non_existent") is False
        assert alert_manager.remove_rule("non_existent") is False
    
    def test_notification_system_reliability(self, notification_service):
        """Test notification system reliability and delivery"""
        
        # Create test alert
        alert = AlertForTest(
            rule_name="test_alert",
            severity=AlertSeverity.CRITICAL,
            message="Test critical alert",
            metric_value=95.0
        )
        
        # Test single channel notification
        result = notification_service.send_notification(alert, [NotificationChannel.EMAIL])
        assert NotificationChannel.EMAIL.value in result
        
        # Test multi-channel notification
        result = notification_service.send_notification(
            alert, 
            [NotificationChannel.EMAIL, NotificationChannel.SLACK]
        )
        
        assert len(result) == 2
        assert NotificationChannel.EMAIL.value in result
        assert NotificationChannel.SLACK.value in result
        
        # Test notification history
        history = notification_service.get_notification_history(1)  # Last 1 hour
        assert len(history) >= 1  # At least one successful notification
        
        # Verify notification content
        successful_notifications = [n for n in history if n["delivered"]]
        assert len(successful_notifications) > 0
        
        for notification in successful_notifications:
            assert notification["alert_id"] == alert.id
            assert notification["message"] == alert.message


class TestMonitoringPerformance:
    """Test monitoring system performance"""
    
    def test_high_volume_metrics_collection(self, metrics_collector):
        """Test metrics collection performance with high volume"""
        
        # Register test metrics first
        for i in range(10):
            metrics_collector.register_metric(MetricForTest(f"test_metric_{i}", MetricType.GAUGE, 0.0))
        
        # Collect large number of metrics
        start_time = time.time()
        
        for i in range(1000):
            metrics_collector.collect_metric(f"test_metric_{i % 10}", float(i), {"instance": f"server_{i % 5}"})
        
        end_time = time.time()
        collection_time = end_time - start_time
        
        # Should collect 1000 metrics quickly
        assert collection_time < 1.0, f"Collection took {collection_time:.2f}s, expected < 1s"
        
        # Verify metrics were collected
        assert len(metrics_collector.metric_history) >= 1000
    
    def test_alert_evaluation_performance(self, metrics_collector, alert_manager):
        """Test alert evaluation performance with many rules"""
        
        # Create many alert rules
        for i in range(100):
            rule = AlertRuleForTest(
                f"rule_{i}",
                f"metric_{i % 10}",
                "gt",
                50.0,
                AlertSeverity.WARNING
            )
            alert_manager.add_rule(rule)
        
        # Register corresponding metrics
        for i in range(10):
            metrics_collector.register_metric(MetricForTest(f"metric_{i}", MetricType.GAUGE, 0.0))
            metrics_collector.collect_metric(f"metric_{i}", 60.0)  # Above threshold
        
        # Measure evaluation time
        start_time = time.time()
        alert_manager.evaluate_rules(metrics_collector)
        end_time = time.time()
        
        evaluation_time = end_time - start_time
        
        # Should evaluate 100 rules quickly
        assert evaluation_time < 0.5, f"Evaluation took {evaluation_time:.2f}s, expected < 0.5s"
        
        # Verify alerts were generated
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) > 0


class TestMonitoringErrorHandling:
    """Test monitoring system error handling"""
    
    def test_missing_metrics_handling(self, alert_manager):
        """Test handling of missing metrics in alert evaluation"""
        
        # Create rule for non-existent metric
        rule = AlertRuleForTest("missing_metric_rule", "non_existent_metric", "gt", 50.0, AlertSeverity.WARNING)
        alert_manager.add_rule(rule)
        
        # Create empty metrics collector
        empty_collector = MockMetricsCollector()
        
        # Should not crash when evaluating rules with missing metrics
        alert_manager.evaluate_rules(empty_collector)
        
        # Should have no active alerts
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 0
    
    def test_notification_failure_handling(self, notification_service):
        """Test handling of notification failures"""
        
        # Set low success rate to simulate failures
        notification_service.delivery_success_rate = 0.3  # 30% success rate
        
        alert = AlertForTest("test_alert", AlertSeverity.WARNING, "Test alert", 75.0)
        
        # Send multiple notifications
        results = []
        for _ in range(10):
            result = notification_service.send_notification(alert, [NotificationChannel.EMAIL])
            results.append(result)
        
        # Should handle failures gracefully
        successful_sends = sum(1 for r in results if r.get(NotificationChannel.EMAIL.value, False))
        failed_sends = len(results) - successful_sends
        
        # Should have some failures due to low success rate
        assert failed_sends > 0
        assert successful_sends > 0  # But some should succeed
    
    def test_dashboard_error_handling(self, dashboard_service, metrics_collector):
        """Test dashboard error handling"""
        
        # Try to view non-existent dashboard
        result = dashboard_service.view_dashboard("non_existent_id", metrics_collector)
        assert "error" in result
        
        # Try to add panel to non-existent dashboard
        success = dashboard_service.add_panel("non_existent_id", {"type": "graph"})
        assert success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])