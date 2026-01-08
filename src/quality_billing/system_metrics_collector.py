"""
System Metrics Collector for Quality Billing Loop.

Collects business and system performance metrics including:
- Work time and quality analysis metrics
- Billing and invoice generation metrics  
- Performance evaluation metrics
- System health and resource usage metrics
"""

import asyncio
import logging
import psutil
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import threading
from concurrent.futures import ThreadPoolExecutor

from .prometheus_metrics import quality_billing_metrics, PrometheusMetricsCollector

logger = logging.getLogger(__name__)


@dataclass
class MetricCollectionTask:
    """Represents a metric collection task."""
    name: str
    collector_func: Callable
    interval_seconds: float
    last_run: float = 0.0
    enabled: bool = True


class SystemMetricsCollector:
    """
    Collects system and business metrics for the quality billing system.
    
    Runs periodic collection tasks to gather:
    - System resource metrics (CPU, memory, disk, network)
    - Application performance metrics
    - Business logic metrics (work time, quality, billing)
    - Database and external service metrics
    """

    def __init__(self, metrics_collector: Optional[PrometheusMetricsCollector] = None):
        self.metrics_collector = metrics_collector or quality_billing_metrics
        
        # Collection state
        self.running = False
        self.collection_tasks: List[MetricCollectionTask] = []
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="metrics-collector")
        
        # Configuration
        self.config = {
            "collection_interval": 15.0,  # seconds
            "system_metrics_interval": 30.0,
            "business_metrics_interval": 60.0,
            "database_metrics_interval": 120.0,
            "cleanup_interval": 3600.0,  # 1 hour
        }
        
        # Cached data for rate calculations
        self._last_network_stats = None
        self._last_disk_stats = None
        self._last_cpu_times = None
        
        # Initialize collection tasks
        self._setup_collection_tasks()

    def _setup_collection_tasks(self):
        """Setup all metric collection tasks."""
        
        # System metrics
        self.collection_tasks.extend([
            MetricCollectionTask(
                "system_resources",
                self._collect_system_resources,
                self.config["system_metrics_interval"]
            ),
            MetricCollectionTask(
                "process_metrics",
                self._collect_process_metrics,
                self.config["system_metrics_interval"]
            ),
            MetricCollectionTask(
                "network_metrics",
                self._collect_network_metrics,
                self.config["system_metrics_interval"]
            ),
            MetricCollectionTask(
                "disk_metrics",
                self._collect_disk_metrics,
                self.config["system_metrics_interval"]
            )
        ])
        
        # Business metrics
        self.collection_tasks.extend([
            MetricCollectionTask(
                "work_time_metrics",
                self._collect_work_time_metrics,
                self.config["business_metrics_interval"]
            ),
            MetricCollectionTask(
                "quality_metrics",
                self._collect_quality_metrics,
                self.config["business_metrics_interval"]
            ),
            MetricCollectionTask(
                "billing_metrics",
                self._collect_billing_metrics,
                self.config["business_metrics_interval"]
            ),
            MetricCollectionTask(
                "performance_metrics",
                self._collect_performance_metrics,
                self.config["business_metrics_interval"]
            )
        ])
        
        # Database and external services
        self.collection_tasks.extend([
            MetricCollectionTask(
                "database_metrics",
                self._collect_database_metrics,
                self.config["database_metrics_interval"]
            ),
            MetricCollectionTask(
                "external_service_metrics",
                self._collect_external_service_metrics,
                self.config["database_metrics_interval"]
            )
        ])
        
        # Cleanup task
        self.collection_tasks.append(
            MetricCollectionTask(
                "cleanup",
                self._cleanup_old_metrics,
                self.config["cleanup_interval"]
            )
        )

    async def start(self):
        """Start the metrics collection service."""
        if self.running:
            logger.warning("Metrics collector already running")
            return
        
        logger.info("Starting system metrics collector")
        self.running = True
        
        # Start collection loop
        asyncio.create_task(self._collection_loop())
        
        logger.info("System metrics collector started")

    async def stop(self):
        """Stop the metrics collection service."""
        if not self.running:
            return
        
        logger.info("Stopping system metrics collector")
        self.running = False
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("System metrics collector stopped")

    async def _collection_loop(self):
        """Main collection loop."""
        logger.info("Starting metrics collection loop")
        
        while self.running:
            try:
                current_time = time.time()
                
                # Run due collection tasks
                for task in self.collection_tasks:
                    if not task.enabled:
                        continue
                    
                    if current_time - task.last_run >= task.interval_seconds:
                        try:
                            # Run collection task in executor
                            await asyncio.get_event_loop().run_in_executor(
                                self.executor,
                                task.collector_func
                            )
                            task.last_run = current_time
                            
                        except Exception as e:
                            logger.error(f"Error in collection task {task.name}: {e}")
                
                # Sleep until next collection cycle
                await asyncio.sleep(self.config["collection_interval"])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    def _collect_system_resources(self):
        """Collect system resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            self.metrics_collector.set_gauge("system_cpu_percent", cpu_percent)
            self.metrics_collector.set_gauge("system_cpu_count", cpu_count)
            self.metrics_collector.set_gauge("system_load_1m", load_avg[0])
            self.metrics_collector.set_gauge("system_load_5m", load_avg[1])
            self.metrics_collector.set_gauge("system_load_15m", load_avg[2])
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            self.metrics_collector.set_gauge("system_memory_total_bytes", memory.total)
            self.metrics_collector.set_gauge("system_memory_available_bytes", memory.available)
            self.metrics_collector.set_gauge("system_memory_used_bytes", memory.used)
            self.metrics_collector.set_gauge("system_memory_percent", memory.percent)
            self.metrics_collector.set_gauge("system_swap_total_bytes", swap.total)
            self.metrics_collector.set_gauge("system_swap_used_bytes", swap.used)
            self.metrics_collector.set_gauge("system_swap_percent", swap.percent)
            
            # Disk metrics for root filesystem
            disk = psutil.disk_usage('/')
            self.metrics_collector.set_gauge("system_disk_total_bytes", disk.total)
            self.metrics_collector.set_gauge("system_disk_used_bytes", disk.used)
            self.metrics_collector.set_gauge("system_disk_free_bytes", disk.free)
            self.metrics_collector.set_gauge("system_disk_percent", (disk.used / disk.total) * 100)
            
        except Exception as e:
            logger.error(f"Error collecting system resources: {e}")

    def _collect_process_metrics(self):
        """Collect current process metrics."""
        try:
            process = psutil.Process()
            
            # Process CPU and memory
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            self.metrics_collector.set_gauge("process_cpu_percent", cpu_percent)
            self.metrics_collector.set_gauge("process_memory_rss_bytes", memory_info.rss)
            self.metrics_collector.set_gauge("process_memory_vms_bytes", memory_info.vms)
            self.metrics_collector.set_gauge("process_memory_percent", memory_percent)
            
            # Process threads and file descriptors
            num_threads = process.num_threads()
            try:
                num_fds = process.num_fds()
                self.metrics_collector.set_gauge("process_open_fds", num_fds)
            except (AttributeError, psutil.AccessDenied):
                pass  # Not available on all platforms
            
            self.metrics_collector.set_gauge("process_threads", num_threads)
            
            # Process connections
            try:
                connections = process.connections()
                self.metrics_collector.set_gauge("process_connections", len(connections))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            
        except Exception as e:
            logger.error(f"Error collecting process metrics: {e}")

    def _collect_network_metrics(self):
        """Collect network I/O metrics."""
        try:
            net_io = psutil.net_io_counters()
            
            if self._last_network_stats:
                # Calculate rates
                time_delta = time.time() - self._last_network_stats['timestamp']
                if time_delta > 0:
                    bytes_sent_rate = (net_io.bytes_sent - self._last_network_stats['bytes_sent']) / time_delta
                    bytes_recv_rate = (net_io.bytes_recv - self._last_network_stats['bytes_recv']) / time_delta
                    packets_sent_rate = (net_io.packets_sent - self._last_network_stats['packets_sent']) / time_delta
                    packets_recv_rate = (net_io.packets_recv - self._last_network_stats['packets_recv']) / time_delta
                    
                    self.metrics_collector.set_gauge("system_network_bytes_sent_per_sec", bytes_sent_rate)
                    self.metrics_collector.set_gauge("system_network_bytes_recv_per_sec", bytes_recv_rate)
                    self.metrics_collector.set_gauge("system_network_packets_sent_per_sec", packets_sent_rate)
                    self.metrics_collector.set_gauge("system_network_packets_recv_per_sec", packets_recv_rate)
            
            # Update totals
            self.metrics_collector.set_gauge("system_network_bytes_sent_total", net_io.bytes_sent)
            self.metrics_collector.set_gauge("system_network_bytes_recv_total", net_io.bytes_recv)
            self.metrics_collector.set_gauge("system_network_packets_sent_total", net_io.packets_sent)
            self.metrics_collector.set_gauge("system_network_packets_recv_total", net_io.packets_recv)
            
            # Store for next calculation
            self._last_network_stats = {
                'timestamp': time.time(),
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
            
        except Exception as e:
            logger.error(f"Error collecting network metrics: {e}")

    def _collect_disk_metrics(self):
        """Collect disk I/O metrics."""
        try:
            disk_io = psutil.disk_io_counters()
            
            if disk_io and self._last_disk_stats:
                # Calculate rates
                time_delta = time.time() - self._last_disk_stats['timestamp']
                if time_delta > 0:
                    read_bytes_rate = (disk_io.read_bytes - self._last_disk_stats['read_bytes']) / time_delta
                    write_bytes_rate = (disk_io.write_bytes - self._last_disk_stats['write_bytes']) / time_delta
                    read_count_rate = (disk_io.read_count - self._last_disk_stats['read_count']) / time_delta
                    write_count_rate = (disk_io.write_count - self._last_disk_stats['write_count']) / time_delta
                    
                    self.metrics_collector.set_gauge("system_disk_read_bytes_per_sec", read_bytes_rate)
                    self.metrics_collector.set_gauge("system_disk_write_bytes_per_sec", write_bytes_rate)
                    self.metrics_collector.set_gauge("system_disk_read_ops_per_sec", read_count_rate)
                    self.metrics_collector.set_gauge("system_disk_write_ops_per_sec", write_count_rate)
            
            if disk_io:
                # Update totals
                self.metrics_collector.set_gauge("system_disk_read_bytes_total", disk_io.read_bytes)
                self.metrics_collector.set_gauge("system_disk_write_bytes_total", disk_io.write_bytes)
                self.metrics_collector.set_gauge("system_disk_read_ops_total", disk_io.read_count)
                self.metrics_collector.set_gauge("system_disk_write_ops_total", disk_io.write_count)
                
                # Store for next calculation
                self._last_disk_stats = {
                    'timestamp': time.time(),
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes,
                    'read_count': disk_io.read_count,
                    'write_count': disk_io.write_count
                }
            
        except Exception as e:
            logger.error(f"Error collecting disk metrics: {e}")

    def _collect_work_time_metrics(self):
        """Collect work time related business metrics."""
        try:
            # These would typically query the database for current statistics
            # For now, we'll simulate some metrics
            
            # Active work sessions
            active_sessions = self._get_active_work_sessions_count()
            self.metrics_collector.set_gauge("quality_billing_active_work_sessions", active_sessions)
            
            # Today's work time statistics
            today_stats = self._get_today_work_time_stats()
            self.metrics_collector.set_gauge("quality_billing_today_total_work_hours", today_stats.get('total_hours', 0))
            self.metrics_collector.set_gauge("quality_billing_today_effective_work_hours", today_stats.get('effective_hours', 0))
            self.metrics_collector.set_gauge("quality_billing_today_break_hours", today_stats.get('break_hours', 0))
            
            # Work efficiency metrics
            efficiency = today_stats.get('efficiency', 0)
            self.metrics_collector.set_gauge("quality_billing_overall_work_efficiency", efficiency)
            
        except Exception as e:
            logger.error(f"Error collecting work time metrics: {e}")

    def _collect_quality_metrics(self):
        """Collect quality assessment metrics."""
        try:
            # Quality score statistics
            quality_stats = self._get_quality_statistics()
            self.metrics_collector.set_gauge("quality_billing_average_quality_score", quality_stats.get('average', 0))
            self.metrics_collector.set_gauge("quality_billing_min_quality_score", quality_stats.get('min', 0))
            self.metrics_collector.set_gauge("quality_billing_max_quality_score", quality_stats.get('max', 0))
            
            # Quality assessments today
            assessments_today = self._get_assessments_count_today()
            self.metrics_collector.set_gauge("quality_billing_assessments_today", assessments_today)
            
            # Quality improvement trends
            improvement_rate = self._get_quality_improvement_rate()
            self.metrics_collector.set_gauge("quality_billing_quality_improvement_rate", improvement_rate)
            
        except Exception as e:
            logger.error(f"Error collecting quality metrics: {e}")

    def _collect_billing_metrics(self):
        """Collect billing and invoice metrics."""
        try:
            # Today's billing statistics
            billing_stats = self._get_today_billing_stats()
            self.metrics_collector.set_gauge("quality_billing_today_invoices_count", billing_stats.get('invoice_count', 0))
            self.metrics_collector.set_gauge("quality_billing_today_total_amount_cents", billing_stats.get('total_amount', 0))
            self.metrics_collector.set_gauge("quality_billing_today_average_invoice_cents", billing_stats.get('average_amount', 0))
            
            # Pending invoices
            pending_invoices = self._get_pending_invoices_count()
            self.metrics_collector.set_gauge("quality_billing_pending_invoices", pending_invoices)
            
            # Revenue metrics
            monthly_revenue = self._get_monthly_revenue()
            self.metrics_collector.set_gauge("quality_billing_monthly_revenue_cents", monthly_revenue)
            
        except Exception as e:
            logger.error(f"Error collecting billing metrics: {e}")

    def _collect_performance_metrics(self):
        """Collect performance evaluation metrics."""
        try:
            # Performance score statistics
            perf_stats = self._get_performance_statistics()
            self.metrics_collector.set_gauge("quality_billing_average_performance_score", perf_stats.get('average', 0))
            self.metrics_collector.set_gauge("quality_billing_top_performer_score", perf_stats.get('max', 0))
            
            # Task completion metrics
            completion_stats = self._get_task_completion_stats()
            self.metrics_collector.set_gauge("quality_billing_tasks_completed_today", completion_stats.get('completed_today', 0))
            self.metrics_collector.set_gauge("quality_billing_average_task_completion_time", completion_stats.get('avg_time', 0))
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")

    def _collect_database_metrics(self):
        """Collect database performance metrics."""
        try:
            # Database connection pool metrics
            db_stats = self._get_database_stats()
            self.metrics_collector.set_gauge("quality_billing_db_connections_active", db_stats.get('active_connections', 0))
            self.metrics_collector.set_gauge("quality_billing_db_connections_idle", db_stats.get('idle_connections', 0))
            self.metrics_collector.set_gauge("quality_billing_db_query_avg_time_ms", db_stats.get('avg_query_time', 0))
            
            # Database size metrics
            self.metrics_collector.set_gauge("quality_billing_db_size_bytes", db_stats.get('db_size', 0))
            self.metrics_collector.set_gauge("quality_billing_db_table_count", db_stats.get('table_count', 0))
            
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")

    def _collect_external_service_metrics(self):
        """Collect external service health metrics."""
        try:
            # Check external service health
            services = ['redis', 'elasticsearch', 'email_service']
            
            for service in services:
                health_status = self._check_service_health(service)
                self.metrics_collector.set_gauge(
                    "quality_billing_external_service_health",
                    1.0 if health_status else 0.0,
                    {"service": service}
                )
            
        except Exception as e:
            logger.error(f"Error collecting external service metrics: {e}")

    def _cleanup_old_metrics(self):
        """Clean up old metric data."""
        try:
            # This would typically clean up old time series data
            logger.info("Running metrics cleanup")
            
            # Reset network and disk rate calculation caches if they're too old
            current_time = time.time()
            
            if (self._last_network_stats and 
                current_time - self._last_network_stats['timestamp'] > 3600):
                self._last_network_stats = None
            
            if (self._last_disk_stats and 
                current_time - self._last_disk_stats['timestamp'] > 3600):
                self._last_disk_stats = None
            
        except Exception as e:
            logger.error(f"Error in metrics cleanup: {e}")

    # Helper methods for business metrics (these would query actual data sources)
    def _get_active_work_sessions_count(self) -> int:
        """Get count of currently active work sessions."""
        # This would query the database for active sessions
        return 5  # Placeholder

    def _get_today_work_time_stats(self) -> Dict[str, float]:
        """Get today's work time statistics."""
        # This would query the database for today's work time data
        return {
            'total_hours': 40.5,
            'effective_hours': 35.2,
            'break_hours': 5.3,
            'efficiency': 0.87
        }

    def _get_quality_statistics(self) -> Dict[str, float]:
        """Get quality score statistics."""
        # This would query the database for quality metrics
        return {
            'average': 0.85,
            'min': 0.65,
            'max': 0.98
        }

    def _get_assessments_count_today(self) -> int:
        """Get count of quality assessments performed today."""
        return 25  # Placeholder

    def _get_quality_improvement_rate(self) -> float:
        """Get quality improvement rate."""
        return 0.05  # 5% improvement rate

    def _get_today_billing_stats(self) -> Dict[str, float]:
        """Get today's billing statistics."""
        return {
            'invoice_count': 12,
            'total_amount': 125000,  # cents
            'average_amount': 10416   # cents
        }

    def _get_pending_invoices_count(self) -> int:
        """Get count of pending invoices."""
        return 3  # Placeholder

    def _get_monthly_revenue(self) -> int:
        """Get monthly revenue in cents."""
        return 2500000  # $25,000

    def _get_performance_statistics(self) -> Dict[str, float]:
        """Get performance score statistics."""
        return {
            'average': 0.82,
            'max': 0.95
        }

    def _get_task_completion_stats(self) -> Dict[str, float]:
        """Get task completion statistics."""
        return {
            'completed_today': 45,
            'avg_time': 1800.0  # 30 minutes in seconds
        }

    def _get_database_stats(self) -> Dict[str, float]:
        """Get database statistics."""
        return {
            'active_connections': 8,
            'idle_connections': 12,
            'avg_query_time': 25.5,  # milliseconds
            'db_size': 1024 * 1024 * 1024,  # 1GB
            'table_count': 25
        }

    def _check_service_health(self, service_name: str) -> bool:
        """Check if an external service is healthy."""
        # This would actually check service health
        return True  # Placeholder

    def enable_task(self, task_name: str):
        """Enable a specific collection task."""
        for task in self.collection_tasks:
            if task.name == task_name:
                task.enabled = True
                logger.info(f"Enabled collection task: {task_name}")
                return
        logger.warning(f"Collection task not found: {task_name}")

    def disable_task(self, task_name: str):
        """Disable a specific collection task."""
        for task in self.collection_tasks:
            if task.name == task_name:
                task.enabled = False
                logger.info(f"Disabled collection task: {task_name}")
                return
        logger.warning(f"Collection task not found: {task_name}")

    def get_task_status(self) -> Dict[str, Any]:
        """Get status of all collection tasks."""
        return {
            task.name: {
                "enabled": task.enabled,
                "interval_seconds": task.interval_seconds,
                "last_run": task.last_run,
                "next_run": task.last_run + task.interval_seconds
            }
            for task in self.collection_tasks
        }


# Global system metrics collector
system_metrics_collector = SystemMetricsCollector()


# Convenience functions
async def start_system_metrics_collection():
    """Start the system metrics collection service."""
    await system_metrics_collector.start()


async def stop_system_metrics_collection():
    """Stop the system metrics collection service."""
    await system_metrics_collector.stop()


def get_system_metrics_collector() -> SystemMetricsCollector:
    """Get the global system metrics collector instance."""
    return system_metrics_collector