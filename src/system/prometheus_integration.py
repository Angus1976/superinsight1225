"""
Enhanced Prometheus Integration for System Health Monitoring.

Provides comprehensive Prometheus metrics collection and integration
for the SuperInsight platform system health monitoring.
"""

import asyncio
import logging
import time
import psutil
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from prometheus_client import (
    Counter, Gauge, Histogram, Summary, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from prometheus_client.core import REGISTRY
import threading

from src.system.monitoring import metrics_collector, performance_monitor, health_monitor
from src.system.business_metrics import business_metrics_collector

logger = logging.getLogger(__name__)


@dataclass
class PrometheusConfig:
    """Configuration for Prometheus integration."""
    metrics_port: int = 9090
    metrics_path: str = "/metrics"
    collection_interval: float = 15.0
    enable_system_metrics: bool = True
    enable_business_metrics: bool = True
    enable_performance_metrics: bool = True
    custom_labels: Dict[str, str] = field(default_factory=dict)


class PrometheusMetricsExporter:
    """
    Enhanced Prometheus metrics exporter for system health monitoring.
    
    Exports comprehensive metrics including:
    - System resource metrics (CPU, memory, disk, network)
    - Application performance metrics
    - Business metrics (annotation efficiency, user activity)
    - Custom health indicators
    """
    
    def __init__(self, config: Optional[PrometheusConfig] = None):
        self.config = config or PrometheusConfig()
        self.registry = CollectorRegistry()
        self.is_collecting = False
        self._collection_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        
        # Prometheus metric instances
        self.system_metrics = {}
        self.business_metrics = {}
        self.performance_metrics = {}
        self.custom_metrics = {}
        
        # Initialize metrics
        self._initialize_system_metrics()
        self._initialize_business_metrics()
        self._initialize_performance_metrics()
        
        logger.info("Prometheus metrics exporter initialized")
    
    def _initialize_system_metrics(self):
        """Initialize system-level Prometheus metrics."""
        if not self.config.enable_system_metrics:
            return
        
        # CPU metrics
        self.system_metrics.update({
            'cpu_usage_percent': Gauge(
                'system_cpu_usage_percent',
                'CPU usage percentage',
                labelnames=['core'],
                registry=self.registry
            ),
            'cpu_load_1m': Gauge(
                'system_cpu_load_1m',
                '1-minute load average',
                registry=self.registry
            ),
            'cpu_load_5m': Gauge(
                'system_cpu_load_5m',
                '5-minute load average',
                registry=self.registry
            ),
            'cpu_load_15m': Gauge(
                'system_cpu_load_15m',
                '15-minute load average',
                registry=self.registry
            ),
        })
        
        # Memory metrics
        self.system_metrics.update({
            'memory_usage_percent': Gauge(
                'system_memory_usage_percent',
                'Memory usage percentage',
                registry=self.registry
            ),
            'memory_available_bytes': Gauge(
                'system_memory_available_bytes',
                'Available memory in bytes',
                registry=self.registry
            ),
            'memory_used_bytes': Gauge(
                'system_memory_used_bytes',
                'Used memory in bytes',
                registry=self.registry
            ),
            'memory_cached_bytes': Gauge(
                'system_memory_cached_bytes',
                'Cached memory in bytes',
                registry=self.registry
            ),
            'swap_usage_percent': Gauge(
                'system_swap_usage_percent',
                'Swap usage percentage',
                registry=self.registry
            ),
        })
        
        # Disk metrics
        self.system_metrics.update({
            'disk_usage_percent': Gauge(
                'system_disk_usage_percent',
                'Disk usage percentage',
                labelnames=['device'],
                registry=self.registry
            ),
            'disk_free_bytes': Gauge(
                'system_disk_free_bytes',
                'Free disk space in bytes',
                labelnames=['device'],
                registry=self.registry
            ),
            'disk_read_bytes_total': Counter(
                'system_disk_read_bytes_total',
                'Total bytes read from disk',
                registry=self.registry
            ),
            'disk_write_bytes_total': Counter(
                'system_disk_write_bytes_total',
                'Total bytes written to disk',
                registry=self.registry
            ),
        })
        
        # Network metrics
        self.system_metrics.update({
            'network_bytes_sent_total': Counter(
                'system_network_bytes_sent_total',
                'Total bytes sent over network',
                registry=self.registry
            ),
            'network_bytes_recv_total': Counter(
                'system_network_bytes_recv_total',
                'Total bytes received over network',
                registry=self.registry
            ),
            'network_packets_sent_total': Counter(
                'system_network_packets_sent_total',
                'Total packets sent over network',
                registry=self.registry
            ),
            'network_packets_recv_total': Counter(
                'system_network_packets_recv_total',
                'Total packets received over network',
                registry=self.registry
            ),
        })
        
        # Process metrics
        self.system_metrics.update({
            'process_cpu_percent': Gauge(
                'system_process_cpu_percent',
                'Process CPU usage percentage',
                registry=self.registry
            ),
            'process_memory_rss_bytes': Gauge(
                'system_process_memory_rss_bytes',
                'Process RSS memory in bytes',
                registry=self.registry
            ),
            'process_threads_count': Gauge(
                'system_process_threads_count',
                'Number of process threads',
                registry=self.registry
            ),
            'process_fds_count': Gauge(
                'system_process_fds_count',
                'Number of open file descriptors',
                registry=self.registry
            ),
        })
    
    def _initialize_business_metrics(self):
        """Initialize business-level Prometheus metrics."""
        if not self.config.enable_business_metrics:
            return
        
        # Annotation efficiency metrics
        self.business_metrics.update({
            'annotation_efficiency_per_hour': Gauge(
                'business_annotation_efficiency_per_hour',
                'Annotations completed per hour',
                labelnames=['project', 'user'],
                registry=self.registry
            ),
            'annotation_quality_score': Gauge(
                'business_annotation_quality_score',
                'Average annotation quality score',
                labelnames=['project', 'user'],
                registry=self.registry
            ),
            'annotation_completion_rate': Gauge(
                'business_annotation_completion_rate',
                'Task completion rate',
                labelnames=['project'],
                registry=self.registry
            ),
            'annotation_revision_rate': Gauge(
                'business_annotation_revision_rate',
                'Task revision rate',
                labelnames=['project'],
                registry=self.registry
            ),
        })
        
        # User activity metrics
        self.business_metrics.update({
            'users_active_count': Gauge(
                'business_users_active_count',
                'Number of currently active users',
                registry=self.registry
            ),
            'users_new_count': Gauge(
                'business_users_new_count',
                'Number of new users today',
                registry=self.registry
            ),
            'users_session_duration_avg': Gauge(
                'business_users_session_duration_avg_seconds',
                'Average user session duration in seconds',
                registry=self.registry
            ),
            'users_actions_per_session': Gauge(
                'business_users_actions_per_session',
                'Average actions per user session',
                registry=self.registry
            ),
        })
        
        # AI model metrics
        self.business_metrics.update({
            'ai_inference_count_total': Counter(
                'business_ai_inference_count_total',
                'Total AI inferences performed',
                labelnames=['model', 'success'],
                registry=self.registry
            ),
            'ai_inference_duration_seconds': Histogram(
                'business_ai_inference_duration_seconds',
                'AI inference duration in seconds',
                labelnames=['model'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
                registry=self.registry
            ),
            'ai_confidence_score': Gauge(
                'business_ai_confidence_score',
                'AI model confidence score',
                labelnames=['model'],
                registry=self.registry
            ),
            'ai_accuracy_score': Gauge(
                'business_ai_accuracy_score',
                'AI model accuracy score',
                labelnames=['model'],
                registry=self.registry
            ),
        })
        
        # Project progress metrics
        self.business_metrics.update({
            'project_completion_percentage': Gauge(
                'business_project_completion_percentage',
                'Project completion percentage',
                labelnames=['project'],
                registry=self.registry
            ),
            'project_tasks_total': Gauge(
                'business_project_tasks_total',
                'Total tasks in project',
                labelnames=['project'],
                registry=self.registry
            ),
            'project_tasks_completed': Gauge(
                'business_project_tasks_completed',
                'Completed tasks in project',
                labelnames=['project'],
                registry=self.registry
            ),
        })
    
    def _initialize_performance_metrics(self):
        """Initialize performance-level Prometheus metrics."""
        if not self.config.enable_performance_metrics:
            return
        
        # Request metrics
        self.performance_metrics.update({
            'http_requests_total': Counter(
                'http_requests_total',
                'Total HTTP requests',
                labelnames=['method', 'endpoint', 'status'],
                registry=self.registry
            ),
            'http_request_duration_seconds': Histogram(
                'http_request_duration_seconds',
                'HTTP request duration in seconds',
                labelnames=['method', 'endpoint'],
                buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                registry=self.registry
            ),
            'http_requests_active': Gauge(
                'http_requests_active',
                'Number of active HTTP requests',
                registry=self.registry
            ),
        })
        
        # Database metrics
        self.performance_metrics.update({
            'database_queries_total': Counter(
                'database_queries_total',
                'Total database queries',
                labelnames=['type', 'success'],
                registry=self.registry
            ),
            'database_query_duration_seconds': Histogram(
                'database_query_duration_seconds',
                'Database query duration in seconds',
                labelnames=['type'],
                buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
                registry=self.registry
            ),
            'database_connections_active': Gauge(
                'database_connections_active',
                'Number of active database connections',
                registry=self.registry
            ),
        })
        
        # Health metrics
        self.performance_metrics.update({
            'health_check_status': Gauge(
                'health_check_status',
                'Health check status (1=healthy, 0=unhealthy)',
                labelnames=['check_name'],
                registry=self.registry
            ),
            'health_check_duration_seconds': Histogram(
                'health_check_duration_seconds',
                'Health check duration in seconds',
                labelnames=['check_name'],
                buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
                registry=self.registry
            ),
        })
    
    async def start_collection(self):
        """Start automatic metrics collection."""
        if self.is_collecting:
            logger.warning("Prometheus metrics collection is already running")
            return
        
        self.is_collecting = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Started Prometheus metrics collection")
    
    async def stop_collection(self):
        """Stop automatic metrics collection."""
        self.is_collecting = False
        
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped Prometheus metrics collection")
    
    async def _collection_loop(self):
        """Main metrics collection loop."""
        while self.is_collecting:
            try:
                await self._collect_all_metrics()
                await asyncio.sleep(self.config.collection_interval)
            except Exception as e:
                logger.error(f"Error in Prometheus metrics collection: {e}")
                await asyncio.sleep(5)  # Short delay before retrying
    
    async def _collect_all_metrics(self):
        """Collect all metrics from various sources."""
        with self._lock:
            if self.config.enable_system_metrics:
                await self._collect_system_metrics()
            
            if self.config.enable_business_metrics:
                await self._collect_business_metrics()
            
            if self.config.enable_performance_metrics:
                await self._collect_performance_metrics()
    
    async def _collect_system_metrics(self):
        """Collect system metrics and update Prometheus gauges."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
            
            self.system_metrics['cpu_usage_percent'].labels(core='total').set(cpu_percent)
            for i, core_usage in enumerate(cpu_per_core):
                self.system_metrics['cpu_usage_percent'].labels(core=f'core_{i}').set(core_usage)
            
            # Load averages (if available)
            try:
                load_avg = psutil.getloadavg()
                self.system_metrics['cpu_load_1m'].set(load_avg[0])
                self.system_metrics['cpu_load_5m'].set(load_avg[1])
                self.system_metrics['cpu_load_15m'].set(load_avg[2])
            except AttributeError:
                pass  # Not available on all platforms
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.system_metrics['memory_usage_percent'].set(memory.percent)
            self.system_metrics['memory_available_bytes'].set(memory.available)
            self.system_metrics['memory_used_bytes'].set(memory.used)
            self.system_metrics['memory_cached_bytes'].set(getattr(memory, 'cached', 0))
            
            swap = psutil.swap_memory()
            self.system_metrics['swap_usage_percent'].set(swap.percent)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            self.system_metrics['disk_usage_percent'].labels(device='root').set(disk_usage_percent)
            self.system_metrics['disk_free_bytes'].labels(device='root').set(disk.free)
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                # Use _value to set counter to absolute value
                self.system_metrics['disk_read_bytes_total']._value._value = disk_io.read_bytes
                self.system_metrics['disk_write_bytes_total']._value._value = disk_io.write_bytes
            
            # Network metrics
            network = psutil.net_io_counters()
            if network:
                self.system_metrics['network_bytes_sent_total']._value._value = network.bytes_sent
                self.system_metrics['network_bytes_recv_total']._value._value = network.bytes_recv
                self.system_metrics['network_packets_sent_total']._value._value = network.packets_sent
                self.system_metrics['network_packets_recv_total']._value._value = network.packets_recv
            
            # Process metrics
            current_process = psutil.Process()
            process_memory = current_process.memory_info()
            
            self.system_metrics['process_cpu_percent'].set(current_process.cpu_percent())
            self.system_metrics['process_memory_rss_bytes'].set(process_memory.rss)
            self.system_metrics['process_threads_count'].set(current_process.num_threads())
            
            try:
                self.system_metrics['process_fds_count'].set(current_process.num_fds())
            except (AttributeError, psutil.AccessDenied):
                pass  # Not available on all platforms
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    async def _collect_business_metrics(self):
        """Collect business metrics from business metrics collector."""
        try:
            # Get business summary
            business_summary = business_metrics_collector.get_business_summary()
            
            # Annotation efficiency metrics
            annotation_data = business_summary.get('annotation_efficiency', {})
            if annotation_data:
                self.business_metrics['annotation_efficiency_per_hour'].labels(
                    project='all', user='all'
                ).set(annotation_data.get('annotations_per_hour', 0))
                
                self.business_metrics['annotation_quality_score'].labels(
                    project='all', user='all'
                ).set(annotation_data.get('quality_score', 0))
                
                self.business_metrics['annotation_completion_rate'].labels(
                    project='all'
                ).set(annotation_data.get('completion_rate', 0))
            
            # User activity metrics
            user_data = business_summary.get('user_activity', {})
            if user_data:
                self.business_metrics['users_active_count'].set(user_data.get('active_users', 0))
                self.business_metrics['users_new_count'].set(user_data.get('new_users', 0))
            
            # AI model metrics
            ai_models = business_summary.get('ai_models', {})
            for model_name, model_data in ai_models.items():
                self.business_metrics['ai_confidence_score'].labels(
                    model=model_name
                ).set(model_data.get('confidence_avg', 0))
                
                self.business_metrics['ai_accuracy_score'].labels(
                    model=model_name
                ).set(model_data.get('success_rate', 0))
            
            # Project metrics
            projects = business_summary.get('projects', {})
            for project_id, project_data in projects.items():
                self.business_metrics['project_completion_percentage'].labels(
                    project=project_id
                ).set(project_data.get('completion_percentage', 0))
                
                self.business_metrics['project_tasks_total'].labels(
                    project=project_id
                ).set(project_data.get('total_tasks', 0))
                
                self.business_metrics['project_tasks_completed'].labels(
                    project=project_id
                ).set(project_data.get('completed_tasks', 0))
            
        except Exception as e:
            logger.error(f"Failed to collect business metrics: {e}")
    
    async def _collect_performance_metrics(self):
        """Collect performance metrics from performance monitor."""
        try:
            # Get performance summary
            perf_summary = performance_monitor.get_performance_summary()
            
            # Active requests
            active_requests = perf_summary.get('active_requests', 0)
            self.performance_metrics['http_requests_active'].set(active_requests)
            
            # Health check status
            health_status = await health_monitor.check_system_health()
            
            for check_name, check_result in health_status.get('checks', {}).items():
                status_value = 1.0 if check_result.get('status') == 'healthy' else 0.0
                self.performance_metrics['health_check_status'].labels(
                    check_name=check_name
                ).set(status_value)
            
        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        if not self.config.enable_performance_metrics:
            return
        
        try:
            self.performance_metrics['http_requests_total'].labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code)
            ).inc()
            
            self.performance_metrics['http_request_duration_seconds'].labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        except Exception as e:
            logger.error(f"Failed to record HTTP request metric: {e}")
    
    def record_database_query(self, query_type: str, success: bool, duration: float):
        """Record database query metrics."""
        if not self.config.enable_performance_metrics:
            return
        
        try:
            self.performance_metrics['database_queries_total'].labels(
                type=query_type,
                success=str(success)
            ).inc()
            
            self.performance_metrics['database_query_duration_seconds'].labels(
                type=query_type
            ).observe(duration)
        except Exception as e:
            logger.error(f"Failed to record database query metric: {e}")
    
    def record_ai_inference(self, model_name: str, success: bool, duration: float, confidence: Optional[float] = None):
        """Record AI inference metrics."""
        if not self.config.enable_business_metrics:
            return
        
        try:
            self.business_metrics['ai_inference_count_total'].labels(
                model=model_name,
                success=str(success)
            ).inc()
            
            self.business_metrics['ai_inference_duration_seconds'].labels(
                model=model_name
            ).observe(duration)
            
            if confidence is not None:
                self.business_metrics['ai_confidence_score'].labels(
                    model=model_name
                ).set(confidence)
        except Exception as e:
            logger.error(f"Failed to record AI inference metric: {e}")
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get Prometheus content type."""
        return CONTENT_TYPE_LATEST
    
    def add_custom_metric(self, name: str, metric_type: str, description: str, labelnames: Optional[List[str]] = None):
        """Add a custom metric."""
        labelnames = labelnames or []
        
        if metric_type == 'counter':
            metric = Counter(name, description, labelnames=labelnames, registry=self.registry)
        elif metric_type == 'gauge':
            metric = Gauge(name, description, labelnames=labelnames, registry=self.registry)
        elif metric_type == 'histogram':
            metric = Histogram(name, description, labelnames=labelnames, registry=self.registry)
        elif metric_type == 'summary':
            metric = Summary(name, description, labelnames=labelnames, registry=self.registry)
        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")
        
        self.custom_metrics[name] = metric
        logger.info(f"Added custom metric: {name} ({metric_type})")
        
        return metric


# Global Prometheus exporter instance
prometheus_exporter = PrometheusMetricsExporter()


# Convenience functions
async def start_prometheus_collection(config: Optional[PrometheusConfig] = None):
    """Start Prometheus metrics collection."""
    global prometheus_exporter
    if config:
        prometheus_exporter = PrometheusMetricsExporter(config)
    
    await prometheus_exporter.start_collection()


async def stop_prometheus_collection():
    """Stop Prometheus metrics collection."""
    await prometheus_exporter.stop_collection()


def get_prometheus_metrics() -> str:
    """Get metrics in Prometheus format."""
    return prometheus_exporter.get_metrics()


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record HTTP request metrics."""
    prometheus_exporter.record_http_request(method, endpoint, status_code, duration)


def record_database_query(query_type: str, success: bool, duration: float):
    """Record database query metrics."""
    prometheus_exporter.record_database_query(query_type, success, duration)


def record_ai_inference(model_name: str, success: bool, duration: float, confidence: Optional[float] = None):
    """Record AI inference metrics."""
    prometheus_exporter.record_ai_inference(model_name, success, duration, confidence)