"""
Integration tests for the monitoring and alerting system.

Tests the complete monitoring pipeline including metrics collection,
alert evaluation, notification processing, and dashboard integration.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.sync.monitoring import (
    sync_metrics,
    sync_alert_manager,
    notification_service,
    monitoring_service,
    AlertSeverity,
    AlertCategory,
    NotificationChannel,
    NotificationPriority,
)
from src.sync.monitoring.config import MonitoringConfig, get_development_config


class TestMonitoringIntegration:
    """Integration tests for monitoring system."""

    @pytest.fixture(autouse=True)
    def setup_monitoring(self):
        """Setup monitoring system for tests."""
        # Reset metrics
        sync_metrics.reset()
        
        # Clear alerts
        sync_alert_manager.active_alerts.clear()
        
        # Clear notifications
        notification_service.pending_notifications.clear()
        notification_service.notification_history.clear()
        
        yield
        
        # Cleanup
        sync_metrics.reset()

    def test_metrics_collection_and_export(self):
        """Test metrics collection and Prometheus export."""
        # Record some sync operations
        sync_metrics.record_sync_operation(
            connector_type="mysql",
            operation="pull",
            records=1000,
            bytes_count=50000,
            duration_seconds=2.5,
            success=True
        )
        
        sync_metrics.record_sync_operation(
            connector_type="postgresql",
            operation="push",
            records=500,
            bytes_count=25000,
            duration_seconds=1.2,
            success=False
        )
        
        # Check metrics were recorded with labels
        mysql_labels = {"connector": "mysql", "operation": "pull"}
        postgres_labels = {"connector": "postgresql", "operation": "push"}
        
        assert sync_metrics.get_counter("sync_operations_total", mysql_labels) == 1
        assert sync_metrics.get_counter("sync_operations_total", postgres_labels) == 1
        assert sync_metrics.get_counter("sync_records_total", mysql_labels) == 1000
        assert sync_metrics.get_counter("sync_records_total", postgres_labels) == 500
        assert sync_metrics.get_counter("sync_bytes_total", mysql_labels) == 50000
        assert sync_metrics.get_counter("sync_bytes_total", postgres_labels) == 25000
        assert sync_metrics.get_counter("sync_errors_total", postgres_labels) == 1
        
        # Test Prometheus export
        prometheus_output = sync_metrics.export_prometheus()
        assert "sync_operations_total" in prometheus_output
        assert "sync_records_total" in prometheus_output
        assert "sync_latency_seconds" in prometheus_output

    def test_alert_rule_evaluation(self):
        """Test alert rule evaluation and firing."""
        # Set up a test alert rule
        from src.sync.monitoring.alert_rules import AlertRule
        
        test_rule = AlertRule(
            name="test_high_latency",
            description="Test high latency alert",
            metric="sync_latency_seconds",
            condition="gt",
            threshold=2.0,
            severity=AlertSeverity.WARNING,
            category=AlertCategory.PERFORMANCE
        )
        
        sync_alert_manager.add_rule(test_rule)
        
        # Record a high latency operation
        sync_metrics.observe_histogram("sync_latency_seconds", 3.0)
        
        # Process the metric through alert manager
        sync_alert_manager.process_metric("sync_latency_seconds", 3.0, datetime.now().timestamp())
        
        # Check that alert was fired
        active_alerts = sync_alert_manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].rule_name == "test_high_latency"
        assert active_alerts[0].severity == AlertSeverity.WARNING

    @pytest.mark.asyncio
    async def test_notification_processing(self):
        """Test notification processing pipeline."""
        # Setup mock handlers for all channels used by default rules
        mock_email_handler = AsyncMock()
        mock_email_handler.send.return_value = True
        
        mock_slack_handler = AsyncMock()
        mock_slack_handler.send.return_value = True
        
        notification_service.add_handler(NotificationChannel.EMAIL, mock_email_handler)
        notification_service.add_handler(NotificationChannel.SLACK, mock_slack_handler)
        
        # Create test alert
        test_alert = {
            "rule_name": "test_alert",
            "severity": "critical",
            "category": "performance",
            "message": "Test alert message",
            "value": 5.0,
            "threshold": 2.0,
            "timestamp": datetime.now().isoformat(),
            "labels": {"connector": "mysql"}
        }
        
        # Process alert
        await notification_service.process_alert(test_alert)
        
        # Check notification was created
        assert len(notification_service.pending_notifications) > 0
        
        # Process pending notifications
        await notification_service.send_pending_notifications()
        
        # Check notifications were sent
        mock_email_handler.send.assert_called()
        mock_slack_handler.send.assert_called()
        assert len(notification_service.pending_notifications) == 0

    def test_notification_aggregation(self):
        """Test notification aggregation functionality."""
        aggregator = notification_service.aggregator
        
        # Create similar alerts
        alert1 = {
            "rule_name": "high_latency",
            "severity": "warning",
            "category": "performance",
            "labels": {"connector": "mysql"}
        }
        
        alert2 = {
            "rule_name": "high_latency",
            "severity": "warning", 
            "category": "performance",
            "labels": {"connector": "mysql"}
        }
        
        # Add alerts to aggregator
        group_key1 = aggregator.add_alert(alert1)
        group_key2 = aggregator.add_alert(alert2)
        
        # Second alert should be aggregated
        assert group_key1 is None  # First alert starts new group
        assert group_key2 is not None  # Second alert is aggregated
        
        # Check aggregated alerts
        aggregated = aggregator.get_aggregated_alerts(group_key2)
        assert len(aggregated) == 2

    def test_notification_deduplication(self):
        """Test notification deduplication."""
        deduplicator = notification_service.deduplicator
        
        # First notification should be allowed
        assert deduplicator.should_send("alert1", "user@test.com", NotificationChannel.EMAIL)
        
        # Mark as sent
        deduplicator.mark_sent("alert1", "user@test.com", NotificationChannel.EMAIL)
        
        # Second identical notification should be blocked
        assert not deduplicator.should_send("alert1", "user@test.com", NotificationChannel.EMAIL)
        
        # Different alert should be allowed
        assert deduplicator.should_send("alert2", "user@test.com", NotificationChannel.EMAIL)

    @pytest.mark.asyncio
    async def test_escalation_processing(self):
        """Test alert escalation functionality."""
        escalator = notification_service.escalator
        
        # Add escalation rule
        escalation_chain = [
            {"delay": 1, "channels": ["email"], "recipients": ["team@test.com"]},
            {"delay": 2, "channels": ["slack"], "recipients": ["#alerts"]}
        ]
        escalator.add_escalation_rule("critical_*", escalation_chain)
        
        # Schedule escalation
        escalator.schedule_escalation("critical_alert", "critical_*")
        
        # Wait for first escalation
        await asyncio.sleep(1.1)
        
        # Check for due escalations
        due_escalations = escalator.get_due_escalations()
        assert len(due_escalations) >= 1
        
        # Acknowledge alert to stop escalation
        escalator.acknowledge_alert("critical_alert")
        
        # Check escalation was stopped
        assert "critical_alert" not in escalator.pending_escalations

    @pytest.mark.asyncio
    async def test_monitoring_service_orchestration(self):
        """Test monitoring service orchestration."""
        # Initialize monitoring service
        await monitoring_service.initialize()
        
        # Record some operations
        monitoring_service.record_sync_operation(
            connector_type="mysql",
            operation="pull",
            records=1000,
            bytes_count=50000,
            duration_seconds=1.5,
            success=True
        )
        
        monitoring_service.update_active_jobs(5)
        monitoring_service.update_queue_depth(100)
        
        # Get health status
        health = monitoring_service.get_health_status()
        
        assert health["status"] in ["healthy", "degraded", "critical"]
        assert "throughput" in health
        assert "latency" in health
        assert "alerts" in health
        assert health["active_jobs"] == 5
        assert health["queue_depth"] == 100

    def test_configuration_loading(self):
        """Test monitoring configuration loading."""
        # Test development config
        dev_config = get_development_config()
        assert dev_config.mode.value == "development"
        assert not dev_config.notifications.email_enabled
        assert not dev_config.grafana.enabled
        
        # Test configuration validation
        from src.sync.monitoring.config import validate_config
        
        issues = validate_config(dev_config)
        assert len(issues) == 0  # Development config should be valid

    @pytest.mark.asyncio
    async def test_grafana_integration(self):
        """Test Grafana integration functionality."""
        with patch('src.sync.monitoring.grafana_integration.aiohttp.ClientSession') as mock_session:
            # Mock successful responses
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"status": "success"}
            
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = mock_response
            
            from src.sync.monitoring.grafana_integration import GrafanaClient
            
            async with GrafanaClient("http://localhost:3000", "test-key") as client:
                # Test health check
                health = await client.get_health()
                assert health["status"] == "success"
                
                # Test dashboard creation
                dashboard = {
                    "dashboard": {"title": "Test Dashboard"},
                    "folderId": None,
                    "overwrite": True
                }
                result = await client.create_dashboard(dashboard)
                assert result["status"] == "success"

    def test_metrics_with_labels(self):
        """Test metrics collection with labels."""
        # Record metrics with different labels
        sync_metrics.inc_counter("test_counter", 1.0, {"service": "sync", "env": "test"})
        sync_metrics.inc_counter("test_counter", 2.0, {"service": "sync", "env": "prod"})
        sync_metrics.inc_counter("test_counter", 3.0, {"service": "api", "env": "test"})
        
        # Check metrics with labels
        assert sync_metrics.get_counter("test_counter", {"service": "sync", "env": "test"}) == 1.0
        assert sync_metrics.get_counter("test_counter", {"service": "sync", "env": "prod"}) == 2.0
        assert sync_metrics.get_counter("test_counter", {"service": "api", "env": "test"}) == 3.0

    def test_histogram_metrics(self):
        """Test histogram metrics functionality."""
        # Record histogram observations
        for value in [0.1, 0.5, 1.0, 2.0, 5.0]:
            sync_metrics.observe_histogram("test_histogram", value)
        
        # Get histogram statistics
        stats = sync_metrics.get_histogram_stats("test_histogram")
        
        assert stats["count"] == 5
        assert stats["sum"] == 8.6
        assert stats["avg"] == 1.72
        assert len(stats["buckets"]) > 0

    def test_throughput_calculation(self):
        """Test throughput statistics calculation."""
        # Record operations over time
        import time
        
        for i in range(10):
            sync_metrics.inc_counter("sync_records_total", 100)
            time.sleep(0.1)  # Small delay to create time series
        
        # Get throughput stats
        throughput = sync_metrics.get_throughput_stats(window_seconds=2)
        
        assert "records_per_second" in throughput
        assert throughput["total_records"] == 1000

    def test_latency_percentiles(self):
        """Test latency percentile calculations."""
        # Record various latency values
        latencies = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]
        
        for latency in latencies:
            sync_metrics.observe_histogram("sync_latency_seconds", latency)
        
        # Get percentiles
        percentiles = sync_metrics.get_latency_percentiles("sync_latency_seconds")
        
        assert "p50" in percentiles
        assert "p90" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        assert percentiles["min"] == 0.1
        assert percentiles["max"] == 10.0

    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_flow(self):
        """Test complete end-to-end monitoring flow."""
        # Setup mock handlers
        mock_email_handler = AsyncMock()
        mock_email_handler.send.return_value = True
        notification_service.add_handler(NotificationChannel.EMAIL, mock_email_handler)
        
        # 1. Record sync operation with high latency
        sync_metrics.record_sync_operation(
            connector_type="mysql",
            operation="pull",
            records=1000,
            bytes_count=50000,
            duration_seconds=6.0,  # High latency
            success=True
        )
        
        # 2. Process metrics through alert manager
        sync_alert_manager.process_metric(
            "sync_latency_seconds", 
            6.0, 
            datetime.now().timestamp()
        )
        
        # 3. Check alert was fired
        active_alerts = sync_alert_manager.get_active_alerts()
        high_latency_alerts = [a for a in active_alerts if "latency" in a.rule_name.lower()]
        
        if high_latency_alerts:
            # 4. Process alert through notification service
            alert_dict = {
                "rule_name": high_latency_alerts[0].rule_name,
                "severity": high_latency_alerts[0].severity.value,
                "category": high_latency_alerts[0].category.value,
                "message": high_latency_alerts[0].message,
                "value": high_latency_alerts[0].value,
                "threshold": high_latency_alerts[0].threshold,
                "timestamp": datetime.now().isoformat(),
                "labels": high_latency_alerts[0].labels
            }
            
            await notification_service.process_alert(alert_dict)
            
            # 5. Process notifications
            await notification_service.send_pending_notifications()
            
            # 6. Verify notification was sent
            if notification_service.handlers.get(NotificationChannel.EMAIL):
                mock_email_handler.send.assert_called()

    def test_alert_acknowledgment(self):
        """Test alert acknowledgment functionality."""
        # Create and fire an alert
        from src.sync.monitoring.alert_rules import AlertRule, Alert
        
        alert = Alert(
            rule_name="test_alert",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.PERFORMANCE,
            message="Test alert",
            value=5.0,
            threshold=2.0,
            timestamp=datetime.now().timestamp()
        )
        
        sync_alert_manager.active_alerts["test_alert"] = alert
        
        # Acknowledge alert
        sync_alert_manager.acknowledge_alert("test_alert")
        notification_service.acknowledge_alert("test_alert")
        
        # Check alert was acknowledged
        assert sync_alert_manager.active_alerts["test_alert"].acknowledged
        assert "test_alert" not in notification_service.escalator.pending_escalations

    def test_monitoring_health_check(self):
        """Test monitoring system health check."""
        # Record some metrics to establish baseline
        sync_metrics.update_active_jobs(3)
        sync_metrics.update_queue_depth(50)
        sync_metrics.update_active_connections(10)
        
        # Get health status
        health = monitoring_service.get_health_status()
        
        # Verify health status structure
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "critical"]
        assert "throughput" in health
        assert "latency" in health
        assert "alerts" in health
        assert "active_jobs" in health
        assert "queue_depth" in health
        assert "timestamp" in health
        
        # Verify values
        assert health["active_jobs"] == 3
        assert health["queue_depth"] == 50


class TestMonitoringConfiguration:
    """Test monitoring configuration functionality."""

    def test_config_validation(self):
        """Test configuration validation."""
        from src.sync.monitoring.config import MonitoringConfig, validate_config
        
        # Valid configuration
        config = MonitoringConfig()
        issues = validate_config(config)
        assert len(issues) == 0
        
        # Invalid configuration - email enabled without SMTP settings
        config.notifications.email_enabled = True
        issues = validate_config(config)
        assert len(issues) > 0
        assert any("SMTP host" in issue for issue in issues)

    def test_environment_config_loading(self):
        """Test loading configuration from environment variables."""
        import os
        from src.sync.monitoring.config import load_config_from_env
        
        # Set test environment variables
        test_env = {
            "MONITORING_MODE": "production",
            "METRICS_COLLECTION_INTERVAL": "5",
            "ALERT_EVALUATION_INTERVAL": "15",
            "EMAIL_NOTIFICATIONS_ENABLED": "true",
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USERNAME": "test@test.com",
            "SMTP_PASSWORD": "password",
            "SMTP_FROM_EMAIL": "noreply@test.com"
        }
        
        # Temporarily set environment variables
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            config = load_config_from_env()
            
            assert config.mode.value == "production"
            assert config.metrics.collection_interval == 5
            assert config.alerts.evaluation_interval == 15
            assert config.notifications.email_enabled
            assert config.notifications.smtp_host == "smtp.test.com"
            
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])