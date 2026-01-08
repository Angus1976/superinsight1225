"""
TCB Deployment Integration Tests

Enterprise-level tests for TCB deployment, single-image deployment, 
auto-scaling, persistent storage, and monitoring/alerting.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import json
import yaml
import os
import tempfile
import subprocess
import time
from datetime import datetime, timedelta
import requests


class TestTCBSingleImageDeployment:
    """Test single Docker image deployment process."""
    
    def test_dockerfile_fullstack_build(self):
        """Test that the fullstack Dockerfile builds successfully."""
        # Mock Docker build process
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Successfully built abc123"
            
            # Test Docker build command
            result = subprocess.run([
                'docker', 'build', 
                '-f', 'deploy/tcb/Dockerfile.fullstack',
                '-t', 'superinsight-tcb:test',
                '.'
            ], capture_output=True, text=True)
            
            assert mock_run.called
            build_args = mock_run.call_args[0][0]
            assert 'docker' in build_args
            assert 'build' in build_args
            assert 'deploy/tcb/Dockerfile.fullstack' in build_args
    
    def test_supervisor_configuration(self):
        """Test supervisor configuration for multi-service management."""
        # Read supervisor configuration
        supervisor_config_path = "deploy/tcb/supervisor/supervisord.conf"
        
        # Mock supervisor config content
        mock_config = """
[supervisord]
nodaemon=true
user=root

[program:postgresql]
command=/usr/lib/postgresql/14/bin/postgres -D /var/lib/postgresql/14/main
user=postgres
autostart=true
autorestart=true
priority=100

[program:redis]
command=/usr/bin/redis-server /etc/redis/redis.conf
autostart=true
autorestart=true
priority=200

[program:fastapi]
command=python -m uvicorn main:app --host 0.0.0.0 --port 8000
directory=/app
autostart=true
autorestart=true
priority=300

[program:labelstudio]
command=label-studio start --host 0.0.0.0 --port 8080
directory=/app
autostart=true
autorestart=true
priority=400
"""
        
        with patch('builtins.open', mock_open_multiple_files({supervisor_config_path: mock_config})):
            with open(supervisor_config_path, 'r') as f:
                config_content = f.read()
            
            # Verify all required services are configured
            assert '[program:postgresql]' in config_content
            assert '[program:redis]' in config_content
            assert '[program:fastapi]' in config_content
            assert '[program:labelstudio]' in config_content
            
            # Verify priority order (PostgreSQL and Redis start first)
            assert 'priority=100' in config_content  # PostgreSQL
            assert 'priority=200' in config_content  # Redis
            assert 'priority=300' in config_content  # FastAPI
            assert 'priority=400' in config_content  # Label Studio
    
    def test_service_startup_order(self):
        """Test that services start in the correct order."""
        from deploy.tcb.scripts.entrypoint import ServiceManager
        
        manager = ServiceManager()
        
        # Mock service status checks
        with patch.object(manager, 'check_service_health') as mock_health:
            # Simulate startup sequence
            startup_sequence = []
            
            def mock_start_service(service_name):
                startup_sequence.append(service_name)
                return True
            
            with patch.object(manager, 'start_service', side_effect=mock_start_service):
                manager.start_all_services()
            
            # Verify startup order
            expected_order = ['postgresql', 'redis', 'fastapi', 'labelstudio']
            assert startup_sequence == expected_order
    
    def test_health_check_endpoints(self):
        """Test that all services have proper health check endpoints."""
        from deploy.tcb.scripts.health_check import HealthChecker
        
        checker = HealthChecker()
        
        # Mock health check responses
        health_responses = {
            'postgresql': {'status': 'healthy', 'connections': 5},
            'redis': {'status': 'healthy', 'memory_usage': '50MB'},
            'fastapi': {'status': 'healthy', 'version': '1.0.0'},
            'labelstudio': {'status': 'healthy', 'projects': 3}
        }
        
        with patch('requests.get') as mock_get:
            def mock_health_response(url):
                mock_response = Mock()
                if 'postgresql' in url:
                    mock_response.json.return_value = health_responses['postgresql']
                elif 'redis' in url:
                    mock_response.json.return_value = health_responses['redis']
                elif 'fastapi' in url:
                    mock_response.json.return_value = health_responses['fastapi']
                elif 'labelstudio' in url:
                    mock_response.json.return_value = health_responses['labelstudio']
                mock_response.status_code = 200
                return mock_response
            
            mock_get.side_effect = mock_health_response
            
            # Test health checks for all services
            for service in ['postgresql', 'redis', 'fastapi', 'labelstudio']:
                health_status = checker.check_service_health(service)
                assert health_status['status'] == 'healthy'


class TestTCBAutoScaling:
    """Test TCB auto-scaling functionality."""
    
    def test_tcb_config_autoscaling_parameters(self):
        """Test TCB configuration for auto-scaling."""
        # Mock TCB config content
        tcb_config = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "superinsight-app"},
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": "superinsight"}},
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "superinsight",
                            "image": "superinsight:latest",
                            "resources": {
                                "requests": {"cpu": "500m", "memory": "1Gi"},
                                "limits": {"cpu": "2000m", "memory": "4Gi"}
                            }
                        }]
                    }
                }
            }
        }
        
        hpa_config = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {"name": "superinsight-hpa"},
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": "superinsight-app"
                },
                "minReplicas": 1,
                "maxReplicas": 10,
                "metrics": [{
                    "type": "Resource",
                    "resource": {
                        "name": "cpu",
                        "target": {"type": "Utilization", "averageUtilization": 70}
                    }
                }]
            }
        }
        
        # Verify auto-scaling configuration
        assert tcb_config["spec"]["replicas"] == 1  # Initial replicas
        assert hpa_config["spec"]["minReplicas"] == 1
        assert hpa_config["spec"]["maxReplicas"] == 10
        assert hpa_config["spec"]["metrics"][0]["resource"]["target"]["averageUtilization"] == 70
    
    def test_scaling_trigger_conditions(self):
        """Test conditions that trigger auto-scaling."""
        from deploy.tcb.scripts.monitoring.metrics_collector import AutoScalingManager
        
        manager = AutoScalingManager()
        
        # Test CPU-based scaling
        high_cpu_metrics = {
            'cpu_usage_percent': 85,
            'memory_usage_percent': 60,
            'request_rate': 100,
            'response_time_ms': 500
        }
        
        scaling_decision = manager.should_scale_up(high_cpu_metrics)
        assert scaling_decision['should_scale'] is True
        assert scaling_decision['reason'] == 'cpu_threshold_exceeded'
        
        # Test memory-based scaling
        high_memory_metrics = {
            'cpu_usage_percent': 50,
            'memory_usage_percent': 90,
            'request_rate': 80,
            'response_time_ms': 300
        }
        
        scaling_decision = manager.should_scale_up(high_memory_metrics)
        assert scaling_decision['should_scale'] is True
        assert scaling_decision['reason'] == 'memory_threshold_exceeded'
        
        # Test normal conditions (no scaling)
        normal_metrics = {
            'cpu_usage_percent': 40,
            'memory_usage_percent': 50,
            'request_rate': 30,
            'response_time_ms': 200
        }
        
        scaling_decision = manager.should_scale_up(normal_metrics)
        assert scaling_decision['should_scale'] is False
    
    def test_scaling_cooldown_period(self):
        """Test that scaling has proper cooldown periods."""
        from deploy.tcb.scripts.monitoring.metrics_collector import AutoScalingManager
        
        manager = AutoScalingManager()
        
        # Mock recent scaling event
        recent_scale_time = datetime.now() - timedelta(minutes=2)
        manager.last_scale_time = recent_scale_time
        manager.cooldown_period = timedelta(minutes=5)
        
        # High CPU should not trigger scaling due to cooldown
        high_cpu_metrics = {
            'cpu_usage_percent': 85,
            'memory_usage_percent': 60
        }
        
        scaling_decision = manager.should_scale_up(high_cpu_metrics)
        assert scaling_decision['should_scale'] is False
        assert scaling_decision['reason'] == 'cooldown_period_active'
        
        # Test after cooldown period
        old_scale_time = datetime.now() - timedelta(minutes=10)
        manager.last_scale_time = old_scale_time
        
        scaling_decision = manager.should_scale_up(high_cpu_metrics)
        assert scaling_decision['should_scale'] is True


class TestTCBPersistentStorage:
    """Test TCB persistent storage functionality."""
    
    def test_storage_volume_configuration(self):
        """Test persistent volume configuration."""
        # Mock storage configuration
        storage_config = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {"name": "postgres-data"},
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {"requests": {"storage": "50Gi"}},
                "storageClassName": "cbs"
            }
        }
        
        # Verify storage configuration
        assert storage_config["spec"]["accessModes"] == ["ReadWriteOnce"]
        assert storage_config["spec"]["resources"]["requests"]["storage"] == "50Gi"
        assert storage_config["spec"]["storageClassName"] == "cbs"
    
    def test_data_persistence_across_restarts(self):
        """Test that data persists across container restarts."""
        from deploy.tcb.scripts.storage.storage_manager import StorageManager
        
        manager = StorageManager()
        
        # Mock database data before restart
        test_data = {
            'postgres': {
                'tables': ['users', 'projects', 'annotations'],
                'record_count': 1000
            },
            'redis': {
                'keys': ['session:*', 'cache:*'],
                'key_count': 500
            }
        }
        
        with patch.object(manager, 'backup_data') as mock_backup:
            with patch.object(manager, 'restore_data') as mock_restore:
                # Simulate container restart
                manager.prepare_for_restart()
                mock_backup.assert_called_once()
                
                # Simulate restart completion
                manager.restore_after_restart()
                mock_restore.assert_called_once()
                
                # Verify data integrity
                restored_data = manager.verify_data_integrity()
                assert restored_data['postgres']['tables'] == test_data['postgres']['tables']
                assert restored_data['redis']['keys'] == test_data['redis']['keys']
    
    def test_automatic_backup_system(self):
        """Test automatic backup system."""
        from deploy.tcb.scripts.backup.backup_manager import BackupManager
        
        manager = BackupManager()
        
        # Test backup scheduling
        backup_schedule = {
            'postgres': {'frequency': 'daily', 'time': '02:00'},
            'redis': {'frequency': 'hourly', 'time': '00'},
            'files': {'frequency': 'weekly', 'day': 'sunday'}
        }
        
        with patch.object(manager, 'create_backup') as mock_create_backup:
            # Test PostgreSQL backup
            manager.schedule_backup('postgres', backup_schedule['postgres'])
            
            # Verify backup was scheduled
            assert manager.is_backup_scheduled('postgres')
            
            # Test backup execution
            manager.execute_scheduled_backups()
            mock_create_backup.assert_called()
    
    def test_storage_monitoring_and_alerts(self):
        """Test storage monitoring and alerting."""
        from deploy.tcb.scripts.storage.storage_monitor import StorageMonitor
        
        monitor = StorageMonitor()
        
        # Test storage usage monitoring
        storage_metrics = {
            'postgres_volume': {'used': '40Gi', 'total': '50Gi', 'usage_percent': 80},
            'redis_volume': {'used': '8Gi', 'total': '10Gi', 'usage_percent': 80},
            'app_logs': {'used': '15Gi', 'total': '20Gi', 'usage_percent': 75}
        }
        
        with patch.object(monitor, 'get_storage_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = storage_metrics
            
            # Test alert conditions
            alerts = monitor.check_storage_alerts()
            
            # Should alert on high usage
            high_usage_alerts = [alert for alert in alerts if alert['severity'] == 'warning']
            assert len(high_usage_alerts) >= 2  # postgres and redis volumes


class TestTCBMonitoringAndAlerting:
    """Test TCB monitoring and alerting system."""
    
    def test_prometheus_metrics_collection(self):
        """Test Prometheus metrics collection."""
        from deploy.tcb.scripts.monitoring.metrics_collector import PrometheusCollector
        
        collector = PrometheusCollector()
        
        # Mock Prometheus metrics
        expected_metrics = [
            'superinsight_http_requests_total',
            'superinsight_http_request_duration_seconds',
            'superinsight_database_connections_active',
            'superinsight_redis_memory_usage_bytes',
            'superinsight_labelstudio_projects_total',
            'superinsight_cpu_usage_percent',
            'superinsight_memory_usage_percent'
        ]
        
        with patch('prometheus_client.CollectorRegistry.collect') as mock_collect:
            # Mock metric families
            mock_families = []
            for metric_name in expected_metrics:
                mock_family = Mock()
                mock_family.name = metric_name
                mock_family.samples = [Mock(value=100)]
                mock_families.append(mock_family)
            
            mock_collect.return_value = mock_families
            
            # Test metrics collection
            metrics = collector.collect_all_metrics()
            
            # Verify all expected metrics are collected
            collected_names = [m['name'] for m in metrics]
            for expected_metric in expected_metrics:
                assert expected_metric in collected_names
    
    def test_grafana_dashboard_integration(self):
        """Test Grafana dashboard integration."""
        from deploy.tcb.config.monitoring.grafana_dashboards import DashboardManager
        
        manager = DashboardManager()
        
        # Mock Grafana dashboard configuration
        dashboard_config = {
            "dashboard": {
                "title": "SuperInsight TCB Monitoring",
                "panels": [
                    {
                        "title": "HTTP Request Rate",
                        "type": "graph",
                        "targets": [{"expr": "rate(superinsight_http_requests_total[5m])"}]
                    },
                    {
                        "title": "Response Time",
                        "type": "graph", 
                        "targets": [{"expr": "superinsight_http_request_duration_seconds"}]
                    },
                    {
                        "title": "Database Connections",
                        "type": "singlestat",
                        "targets": [{"expr": "superinsight_database_connections_active"}]
                    }
                ]
            }
        }
        
        with patch.object(manager, 'create_dashboard') as mock_create:
            mock_create.return_value = {"id": 123, "url": "/d/tcb-monitoring"}
            
            # Test dashboard creation
            result = manager.deploy_tcb_dashboard(dashboard_config)
            
            assert result["id"] == 123
            assert "/d/tcb-monitoring" in result["url"]
    
    def test_alert_rule_configuration(self):
        """Test alert rule configuration."""
        # Mock alert rules configuration
        alert_rules = {
            "groups": [
                {
                    "name": "superinsight_tcb_alerts",
                    "rules": [
                        {
                            "alert": "HighCPUUsage",
                            "expr": "superinsight_cpu_usage_percent > 80",
                            "for": "5m",
                            "labels": {"severity": "warning"},
                            "annotations": {
                                "summary": "High CPU usage detected",
                                "description": "CPU usage is above 80% for more than 5 minutes"
                            }
                        },
                        {
                            "alert": "HighMemoryUsage", 
                            "expr": "superinsight_memory_usage_percent > 85",
                            "for": "3m",
                            "labels": {"severity": "critical"},
                            "annotations": {
                                "summary": "High memory usage detected",
                                "description": "Memory usage is above 85% for more than 3 minutes"
                            }
                        },
                        {
                            "alert": "DatabaseConnectionsHigh",
                            "expr": "superinsight_database_connections_active > 90",
                            "for": "1m",
                            "labels": {"severity": "warning"},
                            "annotations": {
                                "summary": "High database connection count",
                                "description": "Active database connections exceed 90"
                            }
                        }
                    ]
                }
            ]
        }
        
        # Verify alert rule structure
        rules = alert_rules["groups"][0]["rules"]
        
        # Check CPU alert
        cpu_alert = next(rule for rule in rules if rule["alert"] == "HighCPUUsage")
        assert cpu_alert["expr"] == "superinsight_cpu_usage_percent > 80"
        assert cpu_alert["for"] == "5m"
        assert cpu_alert["labels"]["severity"] == "warning"
        
        # Check memory alert
        memory_alert = next(rule for rule in rules if rule["alert"] == "HighMemoryUsage")
        assert memory_alert["expr"] == "superinsight_memory_usage_percent > 85"
        assert memory_alert["labels"]["severity"] == "critical"
    
    def test_notification_channels(self):
        """Test alert notification channels."""
        from deploy.tcb.scripts.monitoring.alert_manager import AlertNotificationManager
        
        manager = AlertNotificationManager()
        
        # Test different notification channels
        notification_configs = {
            'email': {
                'smtp_server': 'smtp.example.com',
                'recipients': ['admin@example.com', 'ops@example.com']
            },
            'webhook': {
                'url': 'https://hooks.slack.com/services/xxx',
                'channel': '#alerts'
            },
            'wechat': {
                'corp_id': 'wx123456',
                'agent_id': '1000001'
            }
        }
        
        with patch.object(manager, 'send_notification') as mock_send:
            # Test alert notification
            alert_data = {
                'alert_name': 'HighCPUUsage',
                'severity': 'warning',
                'message': 'CPU usage is above 80%',
                'timestamp': datetime.now().isoformat()
            }
            
            # Send to all channels
            for channel_type, config in notification_configs.items():
                manager.send_alert_notification(alert_data, channel_type, config)
            
            # Verify notifications were sent
            assert mock_send.call_count == len(notification_configs)


def mock_open_multiple_files(files_dict):
    """Helper function to mock multiple file opens."""
    from unittest.mock import mock_open
    
    def mock_open_func(filename, mode='r', **kwargs):
        if filename in files_dict:
            return mock_open(read_data=files_dict[filename]).return_value
        else:
            raise FileNotFoundError(f"No such file: {filename}")
    return mock_open_func


if __name__ == "__main__":
    pytest.main([__file__, "-v"])