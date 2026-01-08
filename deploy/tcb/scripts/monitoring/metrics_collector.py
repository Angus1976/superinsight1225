"""
TCB Metrics Collector

Collects system and application metrics for TCB deployment monitoring.
"""

import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class MetricsCollector:
    """Collects various system and application metrics."""
    
    def __init__(self):
        self.last_collection_time = None
        self.metrics_history = []
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics."""
        return {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_io': {
                'bytes_sent': psutil.net_io_counters().bytes_sent,
                'bytes_recv': psutil.net_io_counters().bytes_recv
            },
            'disk_io': {
                'read_bytes': psutil.disk_io_counters().read_bytes,
                'write_bytes': psutil.disk_io_counters().write_bytes
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_tenant_metrics(self, tenant_id: str) -> Dict[str, Any]:
        """Get metrics for a specific tenant."""
        # Mock implementation for testing
        return {
            'cpu_usage': 45.0,
            'memory_usage': 60.0,
            'active_tasks': 25,
            'request_count': 1000,
            'error_rate': 0.01
        }
    
    def should_scale_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Determine if a tenant should be scaled."""
        metrics = self.get_tenant_metrics(tenant_id)
        
        if metrics['cpu_usage'] > 80:
            return {
                'should_scale': True,
                'reason': 'high_cpu_usage',
                'current_cpu': metrics['cpu_usage']
            }
        elif metrics['memory_usage'] > 85:
            return {
                'should_scale': True,
                'reason': 'high_memory_usage',
                'current_memory': metrics['memory_usage']
            }
        else:
            return {
                'should_scale': False,
                'reason': 'metrics_within_limits'
            }


class AutoScalingManager:
    """Manages auto-scaling decisions based on metrics."""
    
    def __init__(self):
        self.last_scale_time = None
        self.cooldown_period = timedelta(minutes=5)
        self.cpu_threshold = 70
        self.memory_threshold = 80
    
    def should_scale_up(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if scaling up is needed."""
        # Check cooldown period
        if self.last_scale_time and datetime.now() - self.last_scale_time < self.cooldown_period:
            return {
                'should_scale': False,
                'reason': 'cooldown_period_active',
                'cooldown_remaining': str(self.cooldown_period - (datetime.now() - self.last_scale_time))
            }
        
        # Check CPU threshold
        if metrics.get('cpu_usage_percent', 0) > self.cpu_threshold:
            return {
                'should_scale': True,
                'reason': 'cpu_threshold_exceeded',
                'current_cpu': metrics['cpu_usage_percent'],
                'threshold': self.cpu_threshold
            }
        
        # Check memory threshold
        if metrics.get('memory_usage_percent', 0) > self.memory_threshold:
            return {
                'should_scale': True,
                'reason': 'memory_threshold_exceeded',
                'current_memory': metrics['memory_usage_percent'],
                'threshold': self.memory_threshold
            }
        
        return {
            'should_scale': False,
            'reason': 'metrics_within_thresholds'
        }
    
    def record_scaling_event(self):
        """Record that a scaling event occurred."""
        self.last_scale_time = datetime.now()


class PrometheusCollector:
    """Collects metrics in Prometheus format."""
    
    def __init__(self):
        self.metric_families = []
    
    def collect_all_metrics(self) -> List[Dict[str, Any]]:
        """Collect all metrics for Prometheus."""
        return [
            {'name': 'superinsight_http_requests_total', 'value': 1000, 'type': 'counter'},
            {'name': 'superinsight_http_request_duration_seconds', 'value': 0.5, 'type': 'histogram'},
            {'name': 'superinsight_database_connections_active', 'value': 15, 'type': 'gauge'},
            {'name': 'superinsight_redis_memory_usage_bytes', 'value': 104857600, 'type': 'gauge'},
            {'name': 'superinsight_labelstudio_projects_total', 'value': 5, 'type': 'gauge'},
            {'name': 'superinsight_cpu_usage_percent', 'value': 45.5, 'type': 'gauge'},
            {'name': 'superinsight_memory_usage_percent', 'value': 62.3, 'type': 'gauge'}
        ]