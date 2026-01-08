#!/usr/bin/env python3
"""
Multi-Channel Alert Notification System Demo

Demonstrates the comprehensive multi-channel alert notification system including:
- Alert rule engine with flexible rule configuration
- Multi-channel notification system (email, WeChat Work, DingTalk, SMS, webhook)
- Intelligent alert analysis with pattern recognition and root cause analysis
- Alert prediction and prevention capabilities
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the multi-channel alert system components
from src.monitoring.alert_rule_engine import (
    alert_rule_engine, AlertLevel, AlertCategory, AlertRuleType, AlertPriority
)
from src.monitoring.multi_channel_notification import (
    multi_channel_notification_system, NotificationChannel
)
from src.monitoring.intelligent_alert_analysis import intelligent_alert_analysis_system


class MultiChannelAlertSystemDemo:
    """Comprehensive demo of the multi-channel alert notification system."""
    
    def __init__(self):
        self.demo_metrics = {}
        self.demo_alerts = []
        
    async def run_complete_demo(self):
        """Run the complete multi-channel alert system demo."""
        print("=" * 80)
        print("🚨 MULTI-CHANNEL ALERT NOTIFICATION SYSTEM DEMO")
        print("=" * 80)
        
        # 1. Configure notification handlers
        await self.demo_configure_handlers()
        
        # 2. Create alert rules
        await self.demo_create_alert_rules()
        
        # 3. Configure notification settings
        await self.demo_configure_notifications()
        
        # 4. Simulate metrics and trigger alerts
        await self.demo_trigger_alerts()
        
        # 5. Demonstrate intelligent analysis
        await self.demo_intelligent_analysis()
        
        # 6. Show statistics and insights
        await self.demo_statistics()
        
        print("\n" + "=" * 80)
        print("✅ MULTI-CHANNEL ALERT SYSTEM DEMO COMPLETED")
        print("=" * 80)
    
    async def demo_configure_handlers(self):
        """Demo: Configure notification handlers."""
        print("\n📡 CONFIGURING NOTIFICATION HANDLERS")
        print("-" * 50)
        
        # Configure email handler
        email_config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "alerts@superinsight.com",
            "password": "demo_password",
            "use_tls": True,
            "from_email": "alerts@superinsight.com",
            "from_name": "SuperInsight Alert System"
        }
        multi_channel_notification_system.configure_email_handler(email_config)
        print("✅ Email handler configured")
        
        # Configure WeChat Work handler
        wechat_config = {
            "webhook_key": "demo_webhook_key_12345",
            "corp_id": "demo_corp_id",
            "corp_secret": "demo_corp_secret",
            "agent_id": "demo_agent_id"
        }
        multi_channel_notification_system.configure_wechat_work_handler(wechat_config)
        print("✅ WeChat Work handler configured")
        
        # Configure DingTalk handler
        dingtalk_config = {
            "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=demo_token",
            "secret": "demo_secret_key"
        }
        multi_channel_notification_system.configure_dingtalk_handler(dingtalk_config)
        print("✅ DingTalk handler configured")
        
        # Configure SMS handler
        sms_config = {
            "provider": "aliyun",
            "access_key": "demo_access_key",
            "secret_key": "demo_secret_key",
            "sign_name": "SuperInsight",
            "template_code": "SMS_123456"
        }
        multi_channel_notification_system.configure_sms_handler(sms_config)
        print("✅ SMS handler configured")
        
        # Configure webhook handler
        webhook_config = {
            "url": "https://api.example.com/webhooks/alerts",
            "headers": {"Authorization": "Bearer demo_token"},
            "timeout": 30
        }
        multi_channel_notification_system.configure_webhook_handler(webhook_config)
        print("✅ Webhook handler configured")
        
        # Configure phone handler for emergency alerts
        phone_config = {
            "provider": "aliyun",
            "access_key": "demo_access_key",
            "secret_key": "demo_secret_key",
            "tts_template": "紧急告警通知模板"
        }
        multi_channel_notification_system.configure_phone_handler(phone_config)
        print("✅ Phone handler configured")
    
    async def demo_create_alert_rules(self):
        """Demo: Create various types of alert rules."""
        print("\n📋 CREATING ALERT RULES")
        print("-" * 50)
        
        # 1. System CPU threshold rule
        cpu_rule = alert_rule_engine.create_threshold_rule(
            name="High CPU Usage Alert",
            description="Alert when CPU usage exceeds 80%",
            category=AlertCategory.SYSTEM,
            metric_name="system.cpu.usage",
            threshold=80.0,
            operator="gt",
            level=AlertLevel.WARNING,
            priority=AlertPriority.HIGH,
            tags={"component": "system", "type": "performance"}
        )
        print(f"✅ Created CPU threshold rule: {cpu_rule.id}")
        
        # 2. Memory usage critical rule
        memory_rule = alert_rule_engine.create_threshold_rule(
            name="Critical Memory Usage",
            description="Alert when memory usage exceeds 90%",
            category=AlertCategory.SYSTEM,
            metric_name="system.memory.usage",
            threshold=90.0,
            operator="gt",
            level=AlertLevel.CRITICAL,
            priority=AlertPriority.URGENT,
            tags={"component": "system", "type": "resource"}
        )
        print(f"✅ Created memory threshold rule: {memory_rule.id}")
        
        # 3. API response time trend rule
        api_trend_rule = alert_rule_engine.create_trend_rule(
            name="API Response Time Degradation",
            description="Alert when API response time shows increasing trend",
            category=AlertCategory.PERFORMANCE,
            metric_name="api.response_time",
            trend_threshold=0.5,
            window_size=10,
            level=AlertLevel.WARNING,
            priority=AlertPriority.HIGH,
            tags={"component": "api", "type": "performance"}
        )
        print(f"✅ Created API trend rule: {api_trend_rule.id}")
        
        # 4. Error rate frequency rule
        error_freq_rule = alert_rule_engine.create_frequency_rule(
            name="High Error Rate",
            description="Alert when error count exceeds threshold in time window",
            category=AlertCategory.SYSTEM,
            metric_name="errors.count",
            threshold=10,
            time_window_minutes=5,
            level=AlertLevel.HIGH,
            priority=AlertPriority.URGENT,
            tags={"component": "application", "type": "errors"}
        )
        print(f"✅ Created error frequency rule: {error_freq_rule.id}")
        
        # 5. Composite system health rule
        composite_rule = alert_rule_engine.create_composite_rule(
            name="System Health Degradation",
            description="Alert when multiple system metrics indicate problems",
            category=AlertCategory.SYSTEM,
            conditions=[
                {
                    "metric_name": "system.cpu.usage",
                    "operator": "gt",
                    "threshold": 70.0
                },
                {
                    "metric_name": "system.memory.usage",
                    "operator": "gt",
                    "threshold": 75.0
                }
            ],
            logic="AND",
            level=AlertLevel.HIGH,
            priority=AlertPriority.URGENT,
            tags={"component": "system", "type": "composite"}
        )
        print(f"✅ Created composite system rule: {composite_rule.id}")
        
        # 6. Anomaly detection rule
        anomaly_rule = alert_rule_engine.create_anomaly_rule(
            name="Database Connection Anomaly",
            description="Detect anomalous database connection patterns",
            category=AlertCategory.PERFORMANCE,
            metric_name="database.connections",
            sensitivity=2.5,
            algorithm="statistical",
            level=AlertLevel.WARNING,
            priority=AlertPriority.NORMAL,
            tags={"component": "database", "type": "anomaly"}
        )
        print(f"✅ Created anomaly detection rule: {anomaly_rule.id}")
        
        print(f"\n📊 Total rules created: {len(alert_rule_engine.rules)}")
    
    async def demo_configure_notifications(self):
        """Demo: Configure notification settings."""
        print("\n📢 CONFIGURING NOTIFICATION SETTINGS")
        print("-" * 50)
        
        # Configure email notifications for critical alerts
        multi_channel_notification_system.add_notification_config(
            config_name="critical_email_alerts",
            channel=NotificationChannel.EMAIL,
            recipients=["admin@superinsight.com", "ops@superinsight.com"],
            alert_levels=[AlertLevel.CRITICAL, AlertLevel.EMERGENCY],
            alert_categories=[AlertCategory.SYSTEM, AlertCategory.SECURITY],
            enabled=True
        )
        print("✅ Configured email notifications for critical alerts")
        
        # Configure WeChat Work for all system alerts
        multi_channel_notification_system.add_notification_config(
            config_name="wechat_system_alerts",
            channel=NotificationChannel.WECHAT_WORK,
            recipients=["ops_group"],
            alert_levels=[AlertLevel.WARNING, AlertLevel.HIGH, AlertLevel.CRITICAL],
            alert_categories=[AlertCategory.SYSTEM, AlertCategory.PERFORMANCE],
            enabled=True
        )
        print("✅ Configured WeChat Work notifications for system alerts")
        
        # Configure DingTalk for high priority alerts
        multi_channel_notification_system.add_notification_config(
            config_name="dingtalk_high_priority",
            channel=NotificationChannel.DINGTALK,
            recipients=["dev_team", "ops_team"],
            alert_levels=[AlertLevel.HIGH, AlertLevel.CRITICAL, AlertLevel.EMERGENCY],
            enabled=True
        )
        print("✅ Configured DingTalk notifications for high priority alerts")
        
        # Configure SMS for emergency alerts
        multi_channel_notification_system.add_notification_config(
            config_name="sms_emergency",
            channel=NotificationChannel.SMS,
            recipients=["+86138****1234", "+86139****5678"],
            alert_levels=[AlertLevel.EMERGENCY],
            enabled=True
        )
        print("✅ Configured SMS notifications for emergency alerts")
        
        # Configure webhook for all alerts (external system integration)
        multi_channel_notification_system.add_notification_config(
            config_name="webhook_all_alerts",
            channel=NotificationChannel.WEBHOOK,
            recipients=["external_system"],
            alert_levels=list(AlertLevel),
            enabled=True
        )
        print("✅ Configured webhook notifications for all alerts")
        
        # Set rate limits
        multi_channel_notification_system.set_rate_limit(
            NotificationChannel.EMAIL, max_notifications=20, time_window_minutes=10
        )
        multi_channel_notification_system.set_rate_limit(
            NotificationChannel.SMS, max_notifications=5, time_window_minutes=60
        )
        print("✅ Configured rate limits for channels")
    
    async def demo_trigger_alerts(self):
        """Demo: Simulate metrics and trigger alerts."""
        print("\n🔥 TRIGGERING ALERTS WITH SIMULATED METRICS")
        print("-" * 50)
        
        # Scenario 1: High CPU usage
        print("\n📈 Scenario 1: High CPU Usage")
        cpu_metrics = {"system.cpu.usage": 85.2}
        alerts = await alert_rule_engine.evaluate_rules(cpu_metrics)
        if alerts:
            print(f"  🚨 Triggered {len(alerts)} CPU alerts")
            for alert in alerts:
                print(f"    - {alert.title}: {alert.message}")
                await multi_channel_notification_system.send_alert_notifications(alert)
            self.demo_alerts.extend(alerts)
        
        # Scenario 2: Critical memory usage
        print("\n📈 Scenario 2: Critical Memory Usage")
        memory_metrics = {"system.memory.usage": 92.5}
        alerts = await alert_rule_engine.evaluate_rules(memory_metrics)
        if alerts:
            print(f"  🚨 Triggered {len(alerts)} memory alerts")
            for alert in alerts:
                print(f"    - {alert.title}: {alert.message}")
                await multi_channel_notification_system.send_alert_notifications(alert)
            self.demo_alerts.extend(alerts)
        
        # Scenario 3: API response time trend
        print("\n📈 Scenario 3: API Response Time Degradation")
        # Simulate increasing response times
        for i in range(12):
            response_time = 500 + (i * 50)  # Increasing from 500ms to 1050ms
            api_metrics = {"api.response_time": response_time}
            alerts = await alert_rule_engine.evaluate_rules(api_metrics)
            if alerts:
                print(f"  🚨 Triggered {len(alerts)} API trend alerts at {response_time}ms")
                for alert in alerts:
                    print(f"    - {alert.title}: {alert.message}")
                    await multi_channel_notification_system.send_alert_notifications(alert)
                self.demo_alerts.extend(alerts)
        
        # Scenario 4: Error frequency burst
        print("\n📈 Scenario 4: Error Rate Burst")
        for i in range(15):
            error_metrics = {"errors.count": 1}
            alerts = await alert_rule_engine.evaluate_rules(error_metrics)
            if alerts:
                print(f"  🚨 Triggered {len(alerts)} error frequency alerts")
                for alert in alerts:
                    print(f"    - {alert.title}: {alert.message}")
                    await multi_channel_notification_system.send_alert_notifications(alert)
                self.demo_alerts.extend(alerts)
        
        # Scenario 5: Composite system degradation
        print("\n📈 Scenario 5: System Health Degradation")
        composite_metrics = {
            "system.cpu.usage": 75.0,
            "system.memory.usage": 80.0
        }
        alerts = await alert_rule_engine.evaluate_rules(composite_metrics)
        if alerts:
            print(f"  🚨 Triggered {len(alerts)} composite alerts")
            for alert in alerts:
                print(f"    - {alert.title}: {alert.message}")
                await multi_channel_notification_system.send_alert_notifications(alert)
            self.demo_alerts.extend(alerts)
        
        # Scenario 6: Database connection anomaly
        print("\n📈 Scenario 6: Database Connection Anomaly")
        # Simulate normal then anomalous connection counts
        normal_connections = [50, 52, 48, 51, 49, 53, 47, 50, 52, 48]
        for conn_count in normal_connections:
            db_metrics = {"database.connections": conn_count}
            await alert_rule_engine.evaluate_rules(db_metrics)
        
        # Now simulate anomalous spike
        anomalous_connections = [150, 180, 200]
        for conn_count in anomalous_connections:
            db_metrics = {"database.connections": conn_count}
            alerts = await alert_rule_engine.evaluate_rules(db_metrics)
            if alerts:
                print(f"  🚨 Triggered {len(alerts)} anomaly alerts at {conn_count} connections")
                for alert in alerts:
                    print(f"    - {alert.title}: {alert.message}")
                    await multi_channel_notification_system.send_alert_notifications(alert)
                self.demo_alerts.extend(alerts)
        
        print(f"\n📊 Total alerts generated: {len(self.demo_alerts)}")
    
    async def demo_intelligent_analysis(self):
        """Demo: Intelligent alert analysis capabilities."""
        print("\n🧠 INTELLIGENT ALERT ANALYSIS")
        print("-" * 50)
        
        if not self.demo_alerts:
            print("⚠️  No alerts to analyze")
            return
        
        # Prepare current metrics for analysis
        current_metrics = {
            "system.cpu.usage": 85.2,
            "system.memory.usage": 92.5,
            "api.response_time": 1050.0,
            "errors.count": 15,
            "database.connections": 200
        }
        
        # Perform comprehensive analysis
        analysis_result = await intelligent_alert_analysis_system.analyze_alerts(
            alerts=self.demo_alerts,
            current_metrics=current_metrics,
            context={
                "deployment": "recent_deployment_at_14:30",
                "maintenance": "scheduled_maintenance_window"
            },
            prediction_horizon_hours=4
        )
        
        print("\n📊 ANALYSIS SUMMARY")
        summary = analysis_result["analysis_summary"]
        print(f"  • Total alerts analyzed: {summary['total_alerts']}")
        print(f"  • Patterns detected: {summary['patterns_detected']}")
        print(f"  • Root causes identified: {summary['root_causes_identified']}")
        print(f"  • Predictions made: {summary['predictions_made']}")
        
        # Display detected patterns
        if analysis_result["patterns"]:
            print("\n🔍 DETECTED PATTERNS")
            for pattern in analysis_result["patterns"]:
                print(f"  • {pattern['pattern_type'].upper()}: {pattern['confidence']:.2f} confidence")
                print(f"    - Alerts: {len(pattern['alerts'])}")
                print(f"    - Characteristics: {json.dumps(pattern['characteristics'], indent=4)}")
        
        # Display root cause analyses
        if analysis_result["root_causes"]:
            print("\n🎯 ROOT CAUSE ANALYSIS")
            for rca in analysis_result["root_causes"]:
                print(f"  • Category: {rca['root_cause_category'].upper()}")
                print(f"    - Confidence: {rca['confidence']:.2f}")
                print(f"    - Description: {rca['description']}")
                print(f"    - Evidence: {len(rca['evidence'])} pieces")
                if rca['recommendations']:
                    print(f"    - Top recommendation: {rca['recommendations'][0]}")
        
        # Display predictions
        if analysis_result["predictions"]:
            print("\n🔮 ALERT PREDICTIONS")
            for pred in analysis_result["predictions"]:
                print(f"  • Type: {pred['predicted_alert_type']}")
                print(f"    - Level: {pred['predicted_level']}")
                print(f"    - Confidence: {pred['confidence']}")
                print(f"    - Probability: {pred['probability']:.2f}")
                if pred['prevention_actions']:
                    print(f"    - Prevention: {pred['prevention_actions'][0]}")
        
        # Display insights
        if analysis_result["insights"]:
            print("\n💡 KEY INSIGHTS")
            for insight in analysis_result["insights"]:
                print(f"  • {insight['type'].upper()}: {insight['message']}")
                print(f"    - Severity: {insight['severity']}")
                print(f"    - Recommendation: {insight['recommendation']}")
        
        # Display recommendations
        if analysis_result["recommendations"]:
            print("\n📋 ACTIONABLE RECOMMENDATIONS")
            for i, rec in enumerate(analysis_result["recommendations"][:5], 1):
                print(f"  {i}. {rec}")
    
    async def demo_statistics(self):
        """Demo: Show system statistics and insights."""
        print("\n📈 SYSTEM STATISTICS AND INSIGHTS")
        print("-" * 50)
        
        # Rule evaluation statistics
        rule_stats = alert_rule_engine.get_evaluation_statistics()
        print("\n📊 RULE EVALUATION STATISTICS")
        print(f"  • Total evaluations: {rule_stats['total_evaluations']}")
        print(f"  • Alerts generated: {rule_stats['alerts_generated']}")
        print(f"  • Active alerts: {rule_stats['active_alerts_count']}")
        print(f"  • Total rules: {rule_stats['total_rules']}")
        print(f"  • Enabled rules: {rule_stats['enabled_rules']}")
        
        if rule_stats['by_rule_type']:
            print("  • By rule type:")
            for rule_type, count in rule_stats['by_rule_type'].items():
                print(f"    - {rule_type}: {count}")
        
        if rule_stats['by_level']:
            print("  • By alert level:")
            for level, count in rule_stats['by_level'].items():
                print(f"    - {level}: {count}")
        
        # Notification statistics
        notification_stats = multi_channel_notification_system.get_notification_statistics(days=1)
        print("\n📢 NOTIFICATION STATISTICS")
        print(f"  • Total notifications: {notification_stats['total_notifications']}")
        print(f"  • Success rate: {notification_stats['success_rate']}%")
        print(f"  • Average delivery time: {notification_stats['avg_delivery_time_seconds']:.2f}s")
        
        if notification_stats['by_channel']:
            print("  • By channel:")
            for channel, count in notification_stats['by_channel'].items():
                print(f"    - {channel}: {count}")
        
        if notification_stats['by_status']:
            print("  • By status:")
            for status, count in notification_stats['by_status'].items():
                print(f"    - {status}: {count}")
        
        # Analysis system statistics
        analysis_stats = intelligent_alert_analysis_system.get_analysis_statistics()
        print("\n🧠 ANALYSIS SYSTEM STATISTICS")
        print(f"  • Total analyses: {analysis_stats['total_analyses']}")
        print(f"  • Patterns detected: {analysis_stats['patterns_detected']}")
        print(f"  • Root causes identified: {analysis_stats['root_causes_identified']}")
        print(f"  • Predictions made: {analysis_stats['predictions_made']}")
        print(f"  • Pattern history count: {analysis_stats['pattern_history_count']}")
        print(f"  • Root cause history count: {analysis_stats['root_cause_history_count']}")
        print(f"  • Prediction history count: {analysis_stats['prediction_history_count']}")
        
        # Prediction accuracy (simulated)
        prediction_accuracy = intelligent_alert_analysis_system.alert_predictor.get_prediction_accuracy(days=7)
        print("\n🎯 PREDICTION ACCURACY")
        print(f"  • Total predictions: {prediction_accuracy['total_predictions']}")
        print(f"  • Overall accuracy: {prediction_accuracy['accuracy_rate']}%")
        
        if prediction_accuracy['by_confidence']:
            print("  • By confidence level:")
            for confidence, data in prediction_accuracy['by_confidence'].items():
                print(f"    - {confidence}: {data['accuracy']}% ({data['count']} predictions)")
    
    async def demo_alert_management(self):
        """Demo: Alert acknowledgment and resolution."""
        print("\n🔧 ALERT MANAGEMENT OPERATIONS")
        print("-" * 50)
        
        if not self.demo_alerts:
            print("⚠️  No alerts to manage")
            return
        
        # Acknowledge some alerts
        for i, alert in enumerate(self.demo_alerts[:3]):
            success = await alert_rule_engine.acknowledge_alert(alert.id, f"operator_{i+1}")
            if success:
                print(f"✅ Acknowledged alert: {alert.title}")
        
        # Resolve some alerts
        for i, alert in enumerate(self.demo_alerts[:2]):
            success = await alert_rule_engine.resolve_alert(
                alert.id, 
                f"engineer_{i+1}", 
                f"Resolved by scaling resources and optimizing configuration"
            )
            if success:
                print(f"✅ Resolved alert: {alert.title}")
        
        # Show remaining active alerts
        active_alerts = alert_rule_engine.get_active_alerts(limit=10)
        print(f"\n📊 Remaining active alerts: {len(active_alerts)}")
        for alert in active_alerts[:3]:
            print(f"  • {alert['title']} ({alert['level']}) - {alert['status']}")


async def main():
    """Main demo function."""
    demo = MultiChannelAlertSystemDemo()
    
    try:
        await demo.run_complete_demo()
        
        # Optional: Demo alert management
        print("\n" + "=" * 80)
        print("🔧 ALERT MANAGEMENT DEMO")
        print("=" * 80)
        await demo.demo_alert_management()
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    print("🚀 Starting Multi-Channel Alert Notification System Demo...")
    asyncio.run(main())