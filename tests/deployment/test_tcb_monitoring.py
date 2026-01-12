"""
Tests for TCB Monitoring Service.
"""

import pytest
import asyncio
import time

from src.deployment.tcb_monitoring import (
    TCBMonitoringService,
    TCBMonitoringConfig,
    AlertRule,
    AlertSeverity,
    MetricDefinition,
    MetricType,
    initialize_tcb_monitoring,
    shutdown_tcb_monitoring,
    get_tcb_monitoring_service
)


class TestTCBMonitoringConfig:
    """Tests for TCBMonitoringConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = TCBMonitoringConfig()
        
        assert config.collection_interval == 30.0
        assert config.retention_hours == 24
        assert config.enable_cloud_push is True
        assert config.enable_local_storage is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = TCBMonitoringConfig(
            collection_interval=60.0,
            retention_hours=48,
            alert_webhook_url="https://example.com/webhook"
        )
        
        assert config.collection_interval == 60.0
        assert config.retention_hours == 48
        assert config.alert_webhook_url == "https://example.com/webhook"


class TestAlertRule:
    """Tests for AlertRule."""
    
    def test_rule_creation(self):
        """Test alert rule creation."""
        rule = AlertRule(
            name="test_alert",
            metric_name="cpu_usage",
            condition=">",
            threshold=80.0
        )
        
        assert rule.name == "test_alert"
        assert rule.metric_name == "cpu_usage"
        assert rule.condition == ">"
        assert rule.threshold == 80.0
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True
    
    def test_rule_with_custom_severity(self):
        """Test rule with custom severity."""
        rule = AlertRule(
            name="critical_alert",
            metric_name="memory_usage",
            condition=">",
            threshold=95.0,
            severity=AlertSeverity.CRITICAL,
            duration_seconds=120
        )
        
        assert rule.severity == AlertSeverity.CRITICAL
        assert rule.duration_seconds == 120


class TestMetricDefinition:
    """Tests for MetricDefinition."""
    
    def test_metric_creation(self):
        """Test metric definition creation."""
        metric = MetricDefinition(
            name="custom_metric",
            metric_type=MetricType.GAUGE,
            description="A custom metric"
        )
        
        assert metric.name == "custom_metric"
        assert metric.metric_type == MetricType.GAUGE
        assert metric.description == "A custom metric"
    
    def test_metric_with_labels(self):
        """Test metric with labels."""
        metric = MetricDefinition(
            name="labeled_metric",
            metric_type=MetricType.COUNTER,
            description="A labeled metric",
            unit="requests",
            labels=["service", "status"]
        )
        
        assert metric.labels == ["service", "status"]
        assert metric.unit == "requests"


class TestTCBMonitoringService:
    """Tests for TCBMonitoringService."""
    
    def test_initialization(self):
        """Test service initialization."""
        service = TCBMonitoringService()
        
        assert len(service.metrics) > 0
        assert len(service.alert_rules) > 0
        assert "container_cpu_usage" in service.metrics
        assert "high_cpu_usage" in service.alert_rules
    
    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        config = TCBMonitoringConfig(collection_interval=15.0)
        service = TCBMonitoringService(config)
        
        assert service.config.collection_interval == 15.0
    
    def test_register_metric(self):
        """Test registering a custom metric."""
        service = TCBMonitoringService()
        
        metric = MetricDefinition(
            name="custom_metric",
            metric_type=MetricType.GAUGE,
            description="Custom metric"
        )
        
        service.register_metric(metric)
        
        assert "custom_metric" in service.metrics
        assert "custom_metric" in service.metric_values
    
    def test_add_alert_rule(self):
        """Test adding an alert rule."""
        service = TCBMonitoringService()
        
        rule = AlertRule(
            name="custom_alert",
            metric_name="custom_metric",
            condition=">",
            threshold=50.0
        )
        
        service.add_alert_rule(rule)
        
        assert "custom_alert" in service.alert_rules
    
    def test_remove_alert_rule(self):
        """Test removing an alert rule."""
        service = TCBMonitoringService()
        
        assert service.remove_alert_rule("high_cpu_usage") is True
        assert "high_cpu_usage" not in service.alert_rules
        assert service.remove_alert_rule("nonexistent") is False
    
    def test_record_metric(self):
        """Test recording a metric value."""
        service = TCBMonitoringService()
        
        service.record_metric("container_cpu_usage", 75.0)
        
        values = service.get_metric_values("container_cpu_usage")
        assert len(values) > 0
        assert values[-1]["value"] == 75.0
    
    def test_record_unknown_metric(self):
        """Test recording an unknown metric."""
        service = TCBMonitoringService()
        
        # Should not raise, just log warning
        service.record_metric("unknown_metric", 100.0)
    
    def test_get_metric_values(self):
        """Test getting metric values."""
        service = TCBMonitoringService()
        
        # Record some values
        for i in range(5):
            service.record_metric("container_cpu_usage", 50.0 + i)
        
        values = service.get_metric_values("container_cpu_usage")
        
        assert len(values) == 5
    
    def test_get_metric_values_with_duration(self):
        """Test getting metric values with duration filter."""
        service = TCBMonitoringService()
        
        service.record_metric("container_cpu_usage", 50.0)
        
        # Get values from last hour
        values = service.get_metric_values("container_cpu_usage", duration_seconds=3600)
        
        assert len(values) >= 1
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        service = TCBMonitoringService()
        
        alerts = service.get_active_alerts()
        
        assert isinstance(alerts, list)
    
    def test_get_alert_history(self):
        """Test getting alert history."""
        service = TCBMonitoringService()
        
        history = service.get_alert_history()
        
        assert isinstance(history, list)
    
    def test_get_current_metrics(self):
        """Test getting current metrics."""
        service = TCBMonitoringService()
        
        service.record_metric("container_cpu_usage", 60.0)
        service.record_metric("container_memory_usage", 70.0)
        
        current = service.get_current_metrics()
        
        assert "container_cpu_usage" in current
        assert current["container_cpu_usage"]["value"] == 60.0
    
    def test_get_statistics(self):
        """Test getting statistics."""
        service = TCBMonitoringService()
        
        stats = service.get_statistics()
        
        assert "metrics_count" in stats
        assert "alert_rules_count" in stats
        assert "active_alerts_count" in stats
        assert "is_running" in stats
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the service."""
        service = TCBMonitoringService()
        
        await service.start()
        assert service._is_running is True
        
        await service.stop()
        assert service._is_running is False
    
    def test_set_metrics_callback(self):
        """Test setting metrics callback."""
        service = TCBMonitoringService()
        
        async def callback():
            return {"cpu": 50.0}
        
        service.set_metrics_callback(callback)
        
        assert service._metrics_callback is not None


class TestAlertEvaluation:
    """Tests for alert evaluation logic."""
    
    def test_check_condition_greater_than(self):
        """Test greater than condition."""
        service = TCBMonitoringService()
        
        assert service._check_condition(80.0, ">", 70.0) is True
        assert service._check_condition(60.0, ">", 70.0) is False
    
    def test_check_condition_less_than(self):
        """Test less than condition."""
        service = TCBMonitoringService()
        
        assert service._check_condition(50.0, "<", 70.0) is True
        assert service._check_condition(80.0, "<", 70.0) is False
    
    def test_check_condition_equal(self):
        """Test equal condition."""
        service = TCBMonitoringService()
        
        assert service._check_condition(70.0, "==", 70.0) is True
        assert service._check_condition(71.0, "==", 70.0) is False
    
    def test_check_condition_not_equal(self):
        """Test not equal condition."""
        service = TCBMonitoringService()
        
        assert service._check_condition(80.0, "!=", 70.0) is True
        assert service._check_condition(70.0, "!=", 70.0) is False


class TestGlobalMonitoringService:
    """Tests for global monitoring service functions."""
    
    @pytest.mark.asyncio
    async def test_initialize_and_get(self):
        """Test initializing and getting global service."""
        service = await initialize_tcb_monitoring()
        
        assert service is not None
        assert get_tcb_monitoring_service() is service
        
        await shutdown_tcb_monitoring()
        assert get_tcb_monitoring_service() is None
    
    @pytest.mark.asyncio
    async def test_initialize_with_config(self):
        """Test initializing with custom config."""
        config = TCBMonitoringConfig(collection_interval=10.0)
        service = await initialize_tcb_monitoring(config)
        
        assert service.config.collection_interval == 10.0
        
        await shutdown_tcb_monitoring()
