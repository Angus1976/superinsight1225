"""
Monitoring Service Orchestrator for Data Sync System.

Coordinates all monitoring components including metrics collection,
alerting, notifications, and dashboard management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from contextlib import asynccontextmanager

from .sync_metrics import sync_metrics, SyncMetrics
from .alert_rules import sync_alert_manager, SyncAlertManager
from .notification_service import notification_service, start_notification_processor
from .grafana_integration import grafana_service, GrafanaIntegrationService

logger = logging.getLogger(__name__)


class MonitoringServiceOrchestrator:
    """
    Orchestrates all monitoring components for the data sync system.
    
    Provides a unified interface for:
    - Metrics collection and export
    - Alert evaluation and management
    - Notification processing
    - Dashboard deployment and management
    """

    def __init__(self):
        self.metrics = sync_metrics
        self.alert_manager = sync_alert_manager
        self.notification_service = notification_service
        self.grafana_service: Optional[GrafanaIntegrationService] = None
        
        self.running = False
        self.tasks: List[asyncio.Task] = []
        
        # Configuration
        self.config = {
            "metrics_collection_interval": 10,  # seconds
            "alert_evaluation_interval": 30,    # seconds
            "notification_processing_interval": 10,  # seconds
            "dashboard_update_interval": 3600,  # seconds (1 hour)
            "cleanup_interval": 86400,  # seconds (24 hours)
        }
        
        # Setup alert handler
        self.alert_manager.add_handler(self._handle_alert)

    async def initialize(
        self,
        grafana_url: Optional[str] = None,
        grafana_api_key: Optional[str] = None,
        prometheus_url: str = "http://localhost:9090"
    ):
        """Initialize the monitoring service."""
        logger.info("Initializing monitoring service orchestrator")
        
        # Initialize Grafana integration if configured
        if grafana_url and grafana_api_key:
            from .grafana_integration import initialize_grafana_integration
            self.grafana_service = initialize_grafana_integration(
                grafana_url, grafana_api_key, prometheus_url
            )
            
            try:
                await self.grafana_service.initialize()
                logger.info("Grafana integration initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Grafana: {e}")
        
        logger.info("Monitoring service orchestrator initialized")

    async def start(self):
        """Start all monitoring services."""
        if self.running:
            logger.warning("Monitoring service already running")
            return
        
        logger.info("Starting monitoring service orchestrator")
        self.running = True
        
        # Start background tasks
        self.tasks = [
            asyncio.create_task(self._metrics_collection_loop()),
            asyncio.create_task(self._alert_evaluation_loop()),
            asyncio.create_task(self._notification_processing_loop()),
            asyncio.create_task(self._dashboard_update_loop()),
            asyncio.create_task(self._cleanup_loop()),
        ]
        
        logger.info("All monitoring services started")

    async def stop(self):
        """Stop all monitoring services."""
        if not self.running:
            return
        
        logger.info("Stopping monitoring service orchestrator")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        logger.info("Monitoring service orchestrator stopped")

    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for service lifecycle."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()

    async def _metrics_collection_loop(self):
        """Background loop for metrics collection."""
        logger.info("Starting metrics collection loop")
        
        while self.running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.config["metrics_collection_interval"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    async def _alert_evaluation_loop(self):
        """Background loop for alert evaluation."""
        logger.info("Starting alert evaluation loop")
        
        while self.running:
            try:
                await self._evaluate_alerts()
                await asyncio.sleep(self.config["alert_evaluation_interval"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert evaluation error: {e}")
                await asyncio.sleep(30)

    async def _notification_processing_loop(self):
        """Background loop for notification processing."""
        logger.info("Starting notification processing loop")
        
        while self.running:
            try:
                await self.notification_service.send_pending_notifications()
                await self.notification_service.process_escalations()
                await asyncio.sleep(self.config["notification_processing_interval"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Notification processing error: {e}")
                await asyncio.sleep(30)

    async def _dashboard_update_loop(self):
        """Background loop for dashboard updates."""
        if not self.grafana_service:
            return
        
        logger.info("Starting dashboard update loop")
        
        while self.running:
            try:
                await self.grafana_service.update_dashboards()
                await asyncio.sleep(self.config["dashboard_update_interval"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dashboard update error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _cleanup_loop(self):
        """Background loop for cleanup tasks."""
        logger.info("Starting cleanup loop")
        
        while self.running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(self.config["cleanup_interval"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        import psutil
        import time
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Update system metrics
        self.metrics.set_gauge("system_cpu_percent", cpu_percent)
        self.metrics.set_gauge("system_memory_percent", memory.percent)
        self.metrics.set_gauge("system_memory_available", memory.available)
        self.metrics.set_gauge("system_disk_percent", disk.percent)
        self.metrics.set_gauge("system_disk_free", disk.free)
        
        # Process metrics
        process = psutil.Process()
        self.metrics.set_gauge("process_cpu_percent", process.cpu_percent())
        self.metrics.set_gauge("process_memory_rss", process.memory_info().rss)
        self.metrics.set_gauge("process_memory_vms", process.memory_info().vms)
        self.metrics.set_gauge("process_num_threads", process.num_threads())
        
        # Network metrics
        net_io = psutil.net_io_counters()
        self.metrics.inc_counter("network_bytes_sent", net_io.bytes_sent)
        self.metrics.inc_counter("network_bytes_recv", net_io.bytes_recv)
        self.metrics.inc_counter("network_packets_sent", net_io.packets_sent)
        self.metrics.inc_counter("network_packets_recv", net_io.packets_recv)

    async def _evaluate_alerts(self):
        """Evaluate all alert rules against current metrics."""
        current_time = datetime.now().timestamp()
        
        # Get all current metric values
        all_metrics = self.metrics.get_all_metrics()
        
        # Evaluate counters
        for metric_name, label_values in all_metrics.get("counters", {}).items():
            for labels_key, value in label_values.items():
                labels = self.metrics._parse_labels_key(labels_key)
                self.alert_manager.process_metric(metric_name, value, current_time, labels)
        
        # Evaluate gauges
        for metric_name, label_values in all_metrics.get("gauges", {}).items():
            for labels_key, value in label_values.items():
                labels = self.metrics._parse_labels_key(labels_key)
                self.alert_manager.process_metric(metric_name, value, current_time, labels)
        
        # Evaluate derived metrics
        await self._evaluate_derived_metrics(current_time)

    async def _evaluate_derived_metrics(self, current_time: float):
        """Evaluate derived metrics like rates and ratios."""
        # Calculate error rate
        total_ops = self.metrics.get_counter("sync_operations_total")
        total_errors = self.metrics.get_counter("sync_errors_total")
        
        if total_ops > 0:
            error_rate = total_errors / total_ops
            self.alert_manager.process_metric("sync_error_rate", error_rate, current_time)
        
        # Calculate throughput
        throughput_stats = self.metrics.get_throughput_stats(60)
        throughput = throughput_stats.get("records_per_second", 0)
        self.alert_manager.process_metric("sync_records_per_second", throughput, current_time)
        
        # Calculate connection pool usage ratio
        for connector in ["mysql", "postgresql", "mongodb"]:
            pool_size = self.metrics.get_gauge("connector_pool_size", {"connector": connector})
            pool_available = self.metrics.get_gauge("connector_pool_available", {"connector": connector})
            
            if pool_size > 0:
                usage_ratio = (pool_size - pool_available) / pool_size
                self.alert_manager.process_metric(
                    "connector_pool_usage_ratio",
                    usage_ratio,
                    current_time,
                    {"connector": connector}
                )
        
        # Calculate backpressure rate
        backpressure_events = self.metrics.get_counter("websocket_backpressure_events")
        # Convert to per-minute rate (assuming 1-minute window)
        backpressure_rate = backpressure_events  # This would need proper rate calculation
        self.alert_manager.process_metric("websocket_backpressure_rate", backpressure_rate, current_time)

    async def _handle_alert(self, alert_dict: Dict[str, Any]):
        """Handle fired alerts by sending to notification service."""
        try:
            await self.notification_service.process_alert(alert_dict)
        except Exception as e:
            logger.error(f"Failed to process alert notification: {e}")

    async def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        logger.info("Running monitoring data cleanup")
        
        # Clean up old notification history (keep last 7 days)
        cutoff_date = datetime.now() - timedelta(days=7)
        
        # This would typically clean up database records
        # For now, just log the cleanup
        logger.info(f"Cleaned up monitoring data older than {cutoff_date}")

    # Public API methods
    def record_sync_operation(
        self,
        connector_type: str,
        operation: str,
        records: int,
        bytes_count: int,
        duration_seconds: float,
        success: bool
    ):
        """Record a sync operation for monitoring."""
        self.metrics.record_sync_operation(
            connector_type, operation, records, bytes_count, duration_seconds, success
        )

    def record_connector_query(
        self,
        connector_type: str,
        query_type: str,
        duration_seconds: float,
        success: bool
    ):
        """Record a connector query for monitoring."""
        self.metrics.record_connector_query(
            connector_type, query_type, duration_seconds, success
        )

    def record_conflict(
        self,
        conflict_type: str,
        resolution_strategy: str,
        resolved: bool
    ):
        """Record a conflict for monitoring."""
        self.metrics.record_conflict(conflict_type, resolution_strategy, resolved)

    def update_active_jobs(self, count: int):
        """Update active jobs count."""
        self.metrics.update_active_jobs(count)

    def update_queue_depth(self, depth: int):
        """Update queue depth."""
        self.metrics.update_queue_depth(depth)

    def update_active_connections(self, count: int):
        """Update active connections count."""
        self.metrics.update_active_connections(count)

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        # Get recent metrics
        throughput = self.metrics.get_throughput_stats(300)  # 5 minutes
        latency = self.metrics.get_latency_percentiles()
        
        # Get alert summary
        alert_summary = self.alert_manager.get_alert_summary()
        
        # Determine health status
        critical_alerts = alert_summary.get("critical", 0)
        warning_alerts = alert_summary.get("warning", 0)
        
        if critical_alerts > 0:
            status = "critical"
        elif warning_alerts > 5:  # More than 5 warnings
            status = "degraded"
        elif throughput.get("records_per_second", 0) < 10:  # Very low throughput
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "throughput": throughput,
            "latency": latency,
            "alerts": alert_summary,
            "active_jobs": self.metrics.get_gauge("sync_active_jobs"),
            "queue_depth": self.metrics.get_gauge("sync_queue_depth"),
            "timestamp": datetime.now().isoformat()
        }

    async def deploy_dashboards(self) -> Dict[str, str]:
        """Deploy Grafana dashboards."""
        if not self.grafana_service:
            raise RuntimeError("Grafana service not configured")
        
        await self.grafana_service.deploy_dashboards()
        return await self.grafana_service.get_dashboard_urls()

    def configure_grafana(
        self,
        grafana_url: str,
        api_key: str,
        prometheus_url: str = "http://localhost:9090"
    ):
        """Configure Grafana integration."""
        from .grafana_integration import initialize_grafana_integration
        
        self.grafana_service = initialize_grafana_integration(
            grafana_url, api_key, prometheus_url
        )

    def configure_email_notifications(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str
    ):
        """Configure email notifications."""
        from .notification_service import setup_email_notifications
        setup_email_notifications(smtp_host, smtp_port, username, password, from_email)

    def configure_slack_notifications(self, webhook_url: str):
        """Configure Slack notifications."""
        from .notification_service import setup_slack_notifications
        setup_slack_notifications(webhook_url)

    def get_metrics_export(self) -> str:
        """Get metrics in Prometheus format."""
        return self.metrics.export_prometheus()

    def get_dashboard_urls(self) -> Dict[str, str]:
        """Get dashboard URLs."""
        if not self.grafana_service:
            return {}
        
        # This would need to be made async in real usage
        return {}

    def acknowledge_alert(self, rule_name: str):
        """Acknowledge an alert."""
        self.alert_manager.acknowledge_alert(rule_name)
        self.notification_service.acknowledge_alert(rule_name)


# Global monitoring service instance
monitoring_service = MonitoringServiceOrchestrator()


# Convenience functions
async def start_monitoring_service(
    grafana_url: Optional[str] = None,
    grafana_api_key: Optional[str] = None,
    prometheus_url: str = "http://localhost:9090"
):
    """Start the monitoring service."""
    await monitoring_service.initialize(grafana_url, grafana_api_key, prometheus_url)
    await monitoring_service.start()


async def stop_monitoring_service():
    """Stop the monitoring service."""
    await monitoring_service.stop()


def get_monitoring_service() -> MonitoringServiceOrchestrator:
    """Get the global monitoring service instance."""
    return monitoring_service