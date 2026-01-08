"""
Unit tests for Quality Billing Monitoring Dashboard System.

Tests the Prometheus + Grafana integration including:
- Metrics collection and export
- Dashboard configuration and deployment
- System monitoring capabilities
- API endpoints functionality
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import aiohttp

# Import components to test
from src.quality_billing.prometheus_metrics import (
    PrometheusMetricsCollector,
    quality_billing_metrics
)
from src.quality_billing.prometheus_integration import PrometheusIntegrationService
from src.quality_billing.system_metrics_collector import SystemMetricsCollector
from src.quality_billing.grafana_integration import GrafanaIntegrationService
from src.quality_billing.dashboard_templates import DashboardTemplateGenerator


class TestPrometheusMetricsCollector:
    """Test Prometheus metrics collection functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.collector = PrometheusMetricsCollector()

    def test_counter_operations(self):
        """Test counter metric operations."""
        # Test increment counter
        self.collector.inc_counter("test_counter", 5.0, {"label": "value"})
        assert self.collector.get_counter("test_counter", {"label": "value"}) == 5.0
        
        # Test increment again
        self.collector.inc_counter("test_counter", 3.0, {"label": "value"})
        assert self.collector.get_counter("test_counter", {"label": "value"}) == 8.0
        
        # Test different labels
        self.collector.inc_counter("test_counter", 2.0, {"label": "other"})
        assert self.collector.get_counter("test_counter", {"label": "other"}) == 2.0
        assert self.collector.get_counter("test_counter", {"label": "value"}) == 8.0

    def test_gauge_operations(self):
        """Test gauge metric operations."""
        # Test set gauge
        self.collector.set_gauge("test_gauge", 10.0, {"type": "cpu"})
        assert self.collector.get_gauge("test_gauge", {"type": "cpu"}) == 10.0
        
        # Test increment gauge
        self.collector.inc_gauge("test_gauge", 5.0, {"type": "cpu"})
        assert self.collector.get_gauge("test_gauge", {"type": "cpu"}) == 15.0
        
        # Test decrement gauge
        self.collector.inc_gauge("test_gauge", -3.0, {"type": "cpu"})
        assert self.collector.get_gauge("test_gauge", {"type": "cpu"}) == 12.0

    def test_histogram_operations(self):
        """Test histogram metric operations."""
        # Add observations
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            self.collector.observe_histogram("test_histogram", value, {"service": "api"})
        
        # Get statistics
        stats = self.collector.get_histogram_stats("test_histogram", {"service": "api"})
        
        assert stats["count"] == 5
        assert stats["sum"] == 15.0
        assert stats["avg"] == 3.0
        assert stats["p50"] == 3.0

    def test_business_metrics_recording(self):
        """Test business-specific metric recording."""
        # Test work session recording
        self.collector.record_work_session(
            user_id="user_001",
            project_id="project_alpha",
            duration_seconds=3600.0,
            effective_duration_seconds=3200.0,
            quality_score=0.85
        )
        
        # Verify metrics were recorded
        labels = {"user_id": "user_001", "project_id": "project_alpha"}
        assert self.collector.get_counter("quality_billing_work_time_total_seconds", labels) == 3600.0
        assert self.collector.get_counter("quality_billing_effective_work_time_seconds", labels) == 3200.0
        assert self.collector.get_gauge("quality_billing_quality_score", labels) == 0.85

    def test_billing_event_recording(self):
        """Test billing event recording."""
        self.collector.record_billing_event(
            user_id="user_002",
            project_id="project_beta",
            amount_cents=5000,
            quality_level="excellent",
            task_type="annotation"
        )
        
        # Verify billing metrics
        labels = {
            "user_id": "user_002",
            "project_id": "project_beta",
            "quality_level": "excellent",
            "task_type": "annotation"
        }
        assert self.collector.get_counter("quality_billing_invoices_generated_total", labels) == 1.0
        assert self.collector.get_counter("quality_billing_total_amount_cents", labels) == 5000

    def test_prometheus_export_format(self):
        """Test Prometheus export format."""
        # Register metrics with help text
        self.collector.register_counter("test_requests_total", "Total number of test requests")
        self.collector.register_gauge("test_temperature", "Current temperature reading")
        
        # Add some metrics
        self.collector.inc_counter("test_requests_total", 10, {"method": "GET"})
        self.collector.set_gauge("test_temperature", 23.5, {"location": "server"})
        
        # Export to Prometheus format
        export_data = self.collector.export_prometheus()
        
        # Verify format
        assert "# HELP test_requests_total" in export_data
        assert "# TYPE test_requests_total counter" in export_data
        assert 'test_requests_total{method="GET"} 10' in export_data
        
        assert "# HELP test_temperature" in export_data
        assert "# TYPE test_temperature gauge" in export_data
        assert 'test_temperature{location="server"} 23.5' in export_data

    def test_metrics_summary(self):
        """Test metrics summary generation."""
        # Add sample data
        self.collector.inc_counter("quality_billing_work_time_total_seconds", 7200)
        self.collector.inc_counter("quality_billing_effective_work_time_seconds", 6400)
        self.collector.set_gauge("quality_billing_current_active_users", 5)
        
        # Get summary
        summary = self.collector.get_metric_summary(hours=1)
        
        # Verify summary structure
        assert "work_time" in summary
        assert "quality" in summary
        assert "billing" in summary
        assert "performance" in summary
        assert "system" in summary
        
        # Verify work time calculations
        assert summary["work_time"]["total_seconds"] == 7200
        assert summary["work_time"]["effective_seconds"] == 6400
        assert abs(summary["work_time"]["efficiency"] - (6400/7200)) < 0.001

    def test_time_series_data(self):
        """Test time series data collection."""
        # Record metrics over time
        for i in range(5):
            self.collector.set_gauge("test_metric", i * 10, {"instance": "test"})
        
        # Get time series
        time_series = self.collector.get_time_series("test_metric", {"instance": "test"})
        
        # Verify time series data
        assert len(time_series) == 5
        assert all(hasattr(point, 'value') for point in time_series)
        assert all(hasattr(point, 'timestamp') for point in time_series)
        assert all(hasattr(point, 'labels') for point in time_series)


class TestPrometheusIntegrationService:
    """Test Prometheus integration service."""

    def setup_method(self):
        """Setup test environment."""
        self.service = PrometheusIntegrationService()

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test service initialization."""
        config = {
            "metrics_port": 9092,
            "scrape_interval": "10s"
        }
        
        await self.service.initialize(config)
        
        assert self.service.config["metrics_port"] == 9092
        assert self.service.config["scrape_interval"] == "10s"
        assert self.service.app is not None

    @pytest.mark.asyncio
    async def test_prometheus_config_generation(self):
        """Test Prometheus configuration generation."""
        await self.service.initialize()
        
        config = await self.service._generate_prometheus_config()
        
        # Verify configuration structure
        assert "global" in config
        assert "scrape_configs" in config
        assert "rule_files" in config
        assert "alerting" in config
        
        # Verify scrape configs
        scrape_configs = config["scrape_configs"]
        assert len(scrape_configs) >= 1
        assert any("quality-billing" in sc["job_name"] for sc in scrape_configs)

    def test_alert_rule_management(self):
        """Test alert rule management."""
        # Add alert rule
        self.service.add_alert_rule(
            name="TestAlert",
            expression="test_metric > 100",
            duration="5m",
            severity="warning",
            summary="Test alert summary"
        )
        
        # Verify rule was added
        assert len(self.service.alert_rules) == 1
        rule = self.service.alert_rules[0]
        assert rule["alert"] == "TestAlert"
        assert rule["expr"] == "test_metric > 100"
        assert rule["for"] == "5m"
        assert rule["labels"]["severity"] == "warning"

    def test_service_target_management(self):
        """Test service target management."""
        # Add service target
        self.service.add_service_target(
            target="localhost:8080",
            job_name="test-service",
            labels={"environment": "test"}
        )
        
        # Verify target was added
        assert len(self.service.service_targets) == 1
        target = self.service.service_targets[0]
        assert target["targets"] == ["localhost:8080"]
        assert target["labels"]["job"] == "test-service"
        assert target["labels"]["environment"] == "test"

    def test_default_alerts_setup(self):
        """Test default alert rules setup."""
        self.service.setup_default_alerts()
        
        # Verify default alerts were created
        assert len(self.service.alert_rules) > 0
        
        # Check for specific alerts
        alert_names = [rule["alert"] for rule in self.service.alert_rules]
        assert "QualityBillingHighErrorRate" in alert_names
        assert "QualityBillingLowQualityScore" in alert_names
        assert "QualityBillingSystemDown" in alert_names


class TestSystemMetricsCollector:
    """Test system metrics collector."""

    def setup_method(self):
        """Setup test environment."""
        self.collector = SystemMetricsCollector()

    def test_collection_tasks_initialization(self):
        """Test collection tasks are properly initialized."""
        # Verify tasks were created
        assert len(self.collector.collection_tasks) > 0
        
        # Check for required task types
        task_names = [task.name for task in self.collector.collection_tasks]
        assert "system_resources" in task_names
        assert "work_time_metrics" in task_names
        assert "quality_metrics" in task_names
        assert "billing_metrics" in task_names

    def test_task_enable_disable(self):
        """Test enabling and disabling collection tasks."""
        # Disable a task
        self.collector.disable_task("system_resources")
        
        # Find the task and verify it's disabled
        task = next(t for t in self.collector.collection_tasks if t.name == "system_resources")
        assert not task.enabled
        
        # Enable the task
        self.collector.enable_task("system_resources")
        assert task.enabled

    def test_task_status_reporting(self):
        """Test task status reporting."""
        status = self.collector.get_task_status()
        
        # Verify status structure
        assert isinstance(status, dict)
        assert len(status) > 0
        
        # Check status fields
        for task_name, task_status in status.items():
            assert "enabled" in task_status
            assert "interval_seconds" in task_status
            assert "last_run" in task_status
            assert "next_run" in task_status

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_resources_collection(self, mock_disk, mock_memory, mock_cpu):
        """Test system resources collection."""
        # Mock system data
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(
            total=8589934592,  # 8GB
            available=4294967296,  # 4GB
            used=4294967296,  # 4GB
            percent=50.0
        )
        mock_disk.return_value = Mock(
            total=1099511627776,  # 1TB
            used=549755813888,  # 512GB
            free=549755813888,  # 512GB
        )
        
        # Collect system resources
        self.collector._collect_system_resources()
        
        # Verify metrics were recorded
        assert self.collector.metrics_collector.get_gauge("system_cpu_percent") == 45.5
        assert self.collector.metrics_collector.get_gauge("system_memory_percent") == 50.0
        assert self.collector.metrics_collector.get_gauge("system_memory_total_bytes") == 8589934592

    def test_business_metrics_collection(self):
        """Test business metrics collection methods."""
        # Test work time metrics collection
        self.collector._collect_work_time_metrics()
        
        # Verify some metrics were set (using placeholder values)
        active_sessions = self.collector.metrics_collector.get_gauge("quality_billing_active_work_sessions")
        assert active_sessions >= 0
        
        # Test quality metrics collection
        self.collector._collect_quality_metrics()
        
        # Verify quality metrics
        avg_quality = self.collector.metrics_collector.get_gauge("quality_billing_average_quality_score")
        assert 0 <= avg_quality <= 1


class TestGrafanaIntegrationService:
    """Test Grafana integration service."""

    def setup_method(self):
        """Setup test environment."""
        self.service = GrafanaIntegrationService(
            grafana_url="http://localhost:3000",
            api_key="test_api_key"
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test Grafana service initialization."""
        # Mock HTTP session
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"status": "ok"}
            
            mock_get = AsyncMock()
            mock_get.__aenter__.return_value = mock_response
            
            mock_session_instance = AsyncMock()
            mock_session_instance.get.return_value = mock_get
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            await self.service.initialize()
            
            assert self.service.session is not None

    def test_dashboard_configuration_initialization(self):
        """Test dashboard configurations are initialized."""
        self.service._initialize_dashboard_configs()
        
        # Verify dashboards were created
        assert len(self.service.dashboards) > 0
        assert "overview" in self.service.dashboards
        assert "work_time" in self.service.dashboards
        assert "quality" in self.service.dashboards
        assert "billing" in self.service.dashboards

    def test_overview_dashboard_structure(self):
        """Test overview dashboard structure."""
        dashboard_config = self.service._create_overview_dashboard()
        
        # Verify dashboard structure
        assert "dashboard" in dashboard_config
        dashboard = dashboard_config["dashboard"]
        
        assert dashboard["title"] == "Quality Billing - Overview"
        assert dashboard["uid"] == "quality-billing-overview"
        assert "quality-billing" in dashboard["tags"]
        assert "panels" in dashboard
        assert len(dashboard["panels"]) > 0

    def test_dashboard_panel_configuration(self):
        """Test dashboard panel configurations."""
        dashboard_config = self.service._create_overview_dashboard()
        panels = dashboard_config["dashboard"]["panels"]
        
        # Find a specific panel
        active_users_panel = next(
            (p for p in panels if p.get("title") == "Active Users"),
            None
        )
        
        assert active_users_panel is not None
        assert active_users_panel["type"] == "stat"
        assert "targets" in active_users_panel
        assert len(active_users_panel["targets"]) > 0

    @pytest.mark.asyncio
    async def test_dashboard_deployment_mock(self):
        """Test dashboard deployment with mocked HTTP calls."""
        # Initialize dashboard configs
        self.service._initialize_dashboard_configs()
        
        # Mock successful deployment
        with patch.object(self.service, 'session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"uid": "test-uid", "url": "/d/test-uid"}
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            
            results = await self.service.deploy_dashboards()
            
            # Verify deployment results
            assert len(results) > 0
            for dashboard_name, result in results.items():
                assert "uid" in result or "status" in result

    @pytest.mark.asyncio
    async def test_get_dashboard_urls(self):
        """Test getting dashboard URLs."""
        self.service._initialize_dashboard_configs()
        
        urls = await self.service.get_dashboard_urls()
        
        # Verify URLs structure
        assert isinstance(urls, dict)
        assert len(urls) > 0
        
        for dashboard_name, url in urls.items():
            assert dashboard_name in self.service.dashboards
            assert self.service.grafana_url in url


class TestDashboardTemplateGenerator:
    """Test dashboard template generator."""

    def setup_method(self):
        """Setup test environment."""
        self.generator = DashboardTemplateGenerator()

    def test_executive_dashboard_template(self):
        """Test executive dashboard template generation."""
        dashboard = self.generator.create_executive_dashboard()
        
        # Verify dashboard structure
        assert "dashboard" in dashboard
        config = dashboard["dashboard"]
        
        assert config["title"] == "Quality Billing - Executive Summary"
        assert config["uid"] == "quality-billing-executive"
        assert "executive" in config["tags"]
        assert len(config["panels"]) > 0

    def test_operational_dashboard_template(self):
        """Test operational dashboard template generation."""
        dashboard = self.generator.create_operational_dashboard()
        
        config = dashboard["dashboard"]
        assert config["title"] == "Quality Billing - Operations"
        assert config["uid"] == "quality-billing-operations"
        assert "operations" in config["tags"]

    def test_quality_analytics_dashboard_template(self):
        """Test quality analytics dashboard template generation."""
        dashboard = self.generator.create_quality_analytics_dashboard()
        
        config = dashboard["dashboard"]
        assert config["title"] == "Quality Billing - Quality Analytics"
        assert config["uid"] == "quality-billing-quality-analytics"
        assert "quality" in config["tags"]

    def test_financial_dashboard_template(self):
        """Test financial dashboard template generation."""
        dashboard = self.generator.create_financial_dashboard()
        
        config = dashboard["dashboard"]
        assert config["title"] == "Quality Billing - Financial Analytics"
        assert config["uid"] == "quality-billing-financial"
        assert "financial" in config["tags"]

    def test_custom_dashboard_creation(self):
        """Test custom dashboard creation."""
        panels = [
            {
                "id": 1,
                "title": "Test Panel",
                "type": "stat",
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
            }
        ]
        
        dashboard = self.generator.create_custom_dashboard(
            title="Custom Test Dashboard",
            uid="custom-test",
            panels=panels
        )
        
        config = dashboard["dashboard"]
        assert config["title"] == "Custom Test Dashboard"
        assert config["uid"] == "custom-test"
        assert len(config["panels"]) == 1
        assert config["panels"][0]["title"] == "Test Panel"

    def test_all_dashboard_templates(self):
        """Test getting all dashboard templates."""
        templates = self.generator.get_all_dashboard_templates()
        
        # Verify all expected templates are present
        expected_templates = ["executive", "operational", "quality_analytics", "financial"]
        for template_name in expected_templates:
            assert template_name in templates
            assert "dashboard" in templates[template_name]

    def test_dashboard_panel_structure(self):
        """Test dashboard panel structure consistency."""
        dashboard = self.generator.create_executive_dashboard()
        panels = dashboard["dashboard"]["panels"]
        
        for panel in panels:
            # Skip row panels
            if panel.get("type") == "row":
                continue
            
            # Verify required panel fields
            assert "id" in panel
            assert "title" in panel
            assert "type" in panel
            assert "gridPos" in panel
            
            # Verify gridPos structure
            grid_pos = panel["gridPos"]
            assert "h" in grid_pos
            assert "w" in grid_pos
            assert "x" in grid_pos
            assert "y" in grid_pos

    def test_custom_configuration_override(self):
        """Test custom configuration override."""
        custom_config = {
            "refresh": "10s",
            "time_from": "now-2h",
            "timezone": "UTC"
        }
        
        dashboard = self.generator.create_executive_dashboard(custom_config)
        config = dashboard["dashboard"]
        
        assert config["refresh"] == "10s"
        assert config["time"]["from"] == "now-7d"  # This template uses fixed time range
        assert config["timezone"] == "UTC"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])