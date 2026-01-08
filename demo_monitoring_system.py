#!/usr/bin/env python3
"""
Demo script for the Data Sync System Monitoring and Alerting System.

This script demonstrates the comprehensive monitoring capabilities including:
- Metrics collection and export
- Alert rule evaluation and firing
- Intelligent notification processing
- Grafana dashboard integration
- Real-time monitoring orchestration

Usage:
    python3 demo_monitoring_system.py
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import monitoring components
from src.sync.monitoring import (
    sync_metrics,
    sync_alert_manager,
    notification_service,
    monitoring_service,
    AlertSeverity,
    AlertCategory,
    NotificationChannel,
    setup_email_notifications,
    setup_slack_notifications,
)
from src.sync.monitoring.config import get_development_config, validate_config


class MonitoringSystemDemo:
    """Demonstration of the monitoring system capabilities."""

    def __init__(self):
        self.config = get_development_config()
        self.demo_data = {
            "connectors": ["mysql", "postgresql", "mongodb", "s3"],
            "operations": ["pull", "push", "sync", "transform"],
            "sync_jobs": []
        }

    async def run_demo(self):
        """Run the complete monitoring system demonstration."""
        print("🚀 Starting Data Sync System Monitoring Demo")
        print("=" * 60)
        
        # 1. Configuration Demo
        await self.demo_configuration()
        
        # 2. Metrics Collection Demo
        await self.demo_metrics_collection()
        
        # 3. Alert System Demo
        await self.demo_alert_system()
        
        # 4. Notification System Demo
        await self.demo_notification_system()
        
        # 5. Monitoring Service Orchestration Demo
        await self.demo_monitoring_orchestration()
        
        # 6. Dashboard Integration Demo
        await self.demo_dashboard_integration()
        
        # 7. Real-time Monitoring Demo
        await self.demo_realtime_monitoring()
        
        print("\n✅ Monitoring System Demo Complete!")
        print("=" * 60)

    async def demo_configuration(self):
        """Demonstrate configuration management."""
        print("\n📋 1. Configuration Management Demo")
        print("-" * 40)
        
        # Validate configuration
        issues = validate_config(self.config)
        print(f"Configuration validation: {'✅ Valid' if not issues else '❌ Issues found'}")
        
        if issues:
            for issue in issues:
                print(f"  - {issue}")
        
        # Show key configuration settings
        print(f"Mode: {self.config.mode.value}")
        print(f"Metrics collection interval: {self.config.metrics.collection_interval}s")
        print(f"Alert evaluation interval: {self.config.alerts.evaluation_interval}s")
        print(f"Email notifications: {'✅ Enabled' if self.config.notifications.email_enabled else '❌ Disabled'}")
        print(f"Slack notifications: {'✅ Enabled' if self.config.notifications.slack_enabled else '❌ Disabled'}")
        print(f"Grafana integration: {'✅ Enabled' if self.config.grafana.enabled else '❌ Disabled'}")

    async def demo_metrics_collection(self):
        """Demonstrate metrics collection capabilities."""
        print("\n📊 2. Metrics Collection Demo")
        print("-" * 40)
        
        # Reset metrics for clean demo
        sync_metrics.reset()
        
        # Simulate sync operations
        operations = [
            ("mysql", "pull", 1000, 50000, 1.2, True),
            ("postgresql", "push", 500, 25000, 0.8, True),
            ("mongodb", "sync", 2000, 100000, 2.5, False),  # Failed operation
            ("s3", "pull", 1500, 75000, 1.8, True),
            ("mysql", "transform", 800, 40000, 3.2, True),  # High latency
        ]
        
        print("Simulating sync operations...")
        for connector, operation, records, bytes_count, duration, success in operations:
            sync_metrics.record_sync_operation(
                connector_type=connector,
                operation=operation,
                records=records,
                bytes_count=bytes_count,
                duration_seconds=duration,
                success=success
            )
            print(f"  📈 {connector} {operation}: {records} records, {duration}s, {'✅' if success else '❌'}")
        
        # Update system metrics
        sync_metrics.update_active_jobs(5)
        sync_metrics.update_queue_depth(150)
        sync_metrics.update_active_connections(12)
        
        # Show collected metrics
        print("\nCollected Metrics:")
        print(f"  Active Jobs: {sync_metrics.get_gauge('sync_active_jobs')}")
        print(f"  Queue Depth: {sync_metrics.get_gauge('sync_queue_depth')}")
        print(f"  Active Connections: {sync_metrics.get_gauge('sync_active_connections')}")
        
        # Show throughput stats
        throughput = sync_metrics.get_throughput_stats(60)
        print(f"  Throughput: {throughput.get('records_per_second', 0):.2f} records/sec")
        
        # Show latency percentiles
        latency = sync_metrics.get_latency_percentiles()
        print(f"  Latency P95: {latency.get('p95', 0):.2f}s")
        
        # Export Prometheus metrics
        prometheus_output = sync_metrics.export_prometheus()
        print(f"  Prometheus metrics: {len(prometheus_output.split())} lines exported")

    async def demo_alert_system(self):
        """Demonstrate alert system capabilities."""
        print("\n🚨 3. Alert System Demo")
        print("-" * 40)
        
        # Add custom alert rule
        from src.sync.monitoring.alert_rules import AlertRule
        
        custom_rule = AlertRule(
            name="demo_high_latency",
            description="Demo: High sync latency detected",
            metric="sync_latency_seconds",
            condition="gt",
            threshold=3.0,
            severity=AlertSeverity.WARNING,
            category=AlertCategory.PERFORMANCE,
            annotations={"summary": "Sync latency exceeded 3 seconds"}
        )
        
        sync_alert_manager.add_rule(custom_rule)
        print(f"Added custom alert rule: {custom_rule.name}")
        
        # Simulate high latency metric
        high_latency_value = 3.5
        sync_alert_manager.process_metric(
            "sync_latency_seconds",
            high_latency_value,
            datetime.now().timestamp()
        )
        
        print(f"Processed high latency metric: {high_latency_value}s")
        
        # Check for fired alerts
        active_alerts = sync_alert_manager.get_active_alerts()
        print(f"Active alerts: {len(active_alerts)}")
        
        for alert in active_alerts:
            print(f"  🚨 {alert.rule_name}: {alert.severity.value} - {alert.message}")
        
        # Show alert summary
        alert_summary = sync_alert_manager.get_alert_summary()
        print(f"Alert summary: {alert_summary}")

    async def demo_notification_system(self):
        """Demonstrate notification system capabilities."""
        print("\n📧 4. Notification System Demo")
        print("-" * 40)
        
        # Setup mock notification handlers for demo
        class MockEmailHandler:
            async def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
                print(f"  📧 Email sent to {recipient}: {subject}")
                return True
        
        class MockSlackHandler:
            async def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
                print(f"  💬 Slack message sent to {recipient}: {subject}")
                return True
        
        # Add handlers
        notification_service.add_handler(NotificationChannel.EMAIL, MockEmailHandler())
        notification_service.add_handler(NotificationChannel.SLACK, MockSlackHandler())
        
        # Create test alert
        test_alert = {
            "rule_name": "demo_critical_alert",
            "severity": "critical",
            "category": "performance",
            "message": "Demo: Critical performance issue detected",
            "value": 10.0,
            "threshold": 5.0,
            "timestamp": datetime.now().isoformat(),
            "labels": {"connector": "mysql", "operation": "pull"}
        }
        
        print("Processing test alert...")
        await notification_service.process_alert(test_alert)
        
        print(f"Pending notifications: {len(notification_service.pending_notifications)}")
        
        # Process notifications
        print("Sending notifications...")
        await notification_service.send_pending_notifications()
        
        # Show notification stats
        stats = notification_service.get_notification_stats()
        print(f"Notification stats: {stats}")

    async def demo_monitoring_orchestration(self):
        """Demonstrate monitoring service orchestration."""
        print("\n🎯 5. Monitoring Service Orchestration Demo")
        print("-" * 40)
        
        # Initialize monitoring service
        await monitoring_service.initialize()
        print("Monitoring service initialized")
        
        # Record operations through orchestrator
        monitoring_service.record_sync_operation(
            connector_type="demo_connector",
            operation="demo_operation",
            records=5000,
            bytes_count=250000,
            duration_seconds=2.1,
            success=True
        )
        
        monitoring_service.update_active_jobs(8)
        monitoring_service.update_queue_depth(200)
        
        print("Recorded operations through monitoring service")
        
        # Get health status
        health = monitoring_service.get_health_status()
        print(f"System health: {health['status']}")
        print(f"  Active jobs: {health['active_jobs']}")
        print(f"  Queue depth: {health['queue_depth']}")
        print(f"  Throughput: {health['throughput'].get('records_per_second', 0):.2f} records/sec")

    async def demo_dashboard_integration(self):
        """Demonstrate Grafana dashboard integration."""
        print("\n📊 6. Dashboard Integration Demo")
        print("-" * 40)
        
        # Note: This would require actual Grafana instance
        print("Dashboard integration capabilities:")
        print("  ✅ Grafana client for API communication")
        print("  ✅ Automatic dashboard deployment")
        print("  ✅ Pre-built dashboard templates:")
        print("    - Sync System Overview")
        print("    - Performance Monitoring")
        print("    - Conflict Analysis")
        print("  ✅ Prometheus datasource configuration")
        print("  ✅ Custom dashboard creation")
        
        # Show what would be deployed
        print("\nDashboard URLs (would be available with Grafana):")
        print("  - http://grafana:3000/d/sync-system-overview")
        print("  - http://grafana:3000/d/sync-system-performance")
        print("  - http://grafana:3000/d/sync-system-conflicts")

    async def demo_realtime_monitoring(self):
        """Demonstrate real-time monitoring capabilities."""
        print("\n⚡ 7. Real-time Monitoring Demo")
        print("-" * 40)
        
        print("Simulating real-time sync operations...")
        
        # Simulate continuous operations
        for i in range(5):
            # Random operation
            import random
            connector = random.choice(self.demo_data["connectors"])
            operation = random.choice(self.demo_data["operations"])
            records = random.randint(100, 2000)
            duration = random.uniform(0.5, 4.0)
            success = random.random() > 0.1  # 90% success rate
            
            # Record operation
            sync_metrics.record_sync_operation(
                connector_type=connector,
                operation=operation,
                records=records,
                bytes_count=records * 50,
                duration_seconds=duration,
                success=success
            )
            
            # Update system state
            active_jobs = random.randint(3, 10)
            queue_depth = random.randint(50, 500)
            
            sync_metrics.update_active_jobs(active_jobs)
            sync_metrics.update_queue_depth(queue_depth)
            
            # Show current state
            print(f"  [{i+1}/5] {connector} {operation}: {records} records, "
                  f"{duration:.2f}s, {'✅' if success else '❌'}")
            print(f"        Jobs: {active_jobs}, Queue: {queue_depth}")
            
            # Check for alerts
            if duration > 3.0:
                sync_alert_manager.process_metric(
                    "sync_latency_seconds",
                    duration,
                    datetime.now().timestamp()
                )
            
            await asyncio.sleep(0.5)  # Simulate time between operations
        
        # Final status
        health = monitoring_service.get_health_status()
        print(f"\nFinal system status: {health['status']}")
        
        active_alerts = sync_alert_manager.get_active_alerts()
        if active_alerts:
            print(f"Active alerts: {len(active_alerts)}")
            for alert in active_alerts[:3]:  # Show first 3
                print(f"  🚨 {alert.rule_name}: {alert.severity.value}")

    def show_feature_summary(self):
        """Show summary of implemented features."""
        print("\n🎉 Monitoring System Features Summary")
        print("=" * 60)
        
        features = [
            "✅ Comprehensive Metrics Collection",
            "  - Sync operations (throughput, latency, errors)",
            "  - System metrics (CPU, memory, disk)",
            "  - Connection pool metrics",
            "  - WebSocket metrics",
            "  - Conflict resolution metrics",
            "",
            "✅ Intelligent Alert System",
            "  - Configurable alert rules",
            "  - Multiple severity levels",
            "  - Duration-based alerting",
            "  - Alert acknowledgment",
            "",
            "✅ Multi-Channel Notifications",
            "  - Email notifications",
            "  - Slack integration",
            "  - Webhook notifications",
            "  - Notification aggregation",
            "  - Deduplication",
            "  - Escalation policies",
            "",
            "✅ Grafana Integration",
            "  - Automatic dashboard deployment",
            "  - Pre-built dashboard templates",
            "  - Prometheus datasource setup",
            "  - Custom dashboard creation",
            "",
            "✅ Monitoring Orchestration",
            "  - Centralized monitoring service",
            "  - Background processing loops",
            "  - Health status monitoring",
            "  - Configuration management",
            "",
            "✅ Production-Ready Features",
            "  - Prometheus metrics export",
            "  - Configurable thresholds",
            "  - Environment-based configuration",
            "  - Comprehensive testing",
        ]
        
        for feature in features:
            print(feature)


async def main():
    """Main demo function."""
    demo = MonitoringSystemDemo()
    
    try:
        await demo.run_demo()
        demo.show_feature_summary()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        logger.exception("Demo failed")
    finally:
        # Cleanup
        await monitoring_service.stop()


if __name__ == "__main__":
    asyncio.run(main())