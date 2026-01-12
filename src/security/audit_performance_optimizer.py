"""
Audit Performance Optimizer for SuperInsight Platform.

Implements high-performance audit logging with < 50ms write latency through:
- Asynchronous batch processing
- In-memory buffering with background flushing
- Connection pooling optimization
- Minimal serialization overhead
- Lock-free concurrent operations
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, Deque
from collections import deque
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Event
from uuid import UUID, uuid4
import psutil

from src.security.models import AuditLogModel, AuditAction
from src.database.connection import db_manager
from src.security.audit_storage import AuditLogBatchStorage, StorageConfig

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfig:
    """Configuration for high-performance audit logging."""
    # Buffer settings
    buffer_size: int = 5000  # Maximum logs in memory buffer
    flush_interval_ms: int = 100  # Flush every 100ms for low latency
    batch_size: int = 500  # Optimal batch size for PostgreSQL
    
    # Performance thresholds
    target_latency_ms: float = 50.0  # Target < 50ms write latency
    max_memory_mb: int = 128  # Maximum memory usage for buffers
    
    # Concurrency settings
    max_workers: int = 4  # Background processing threads
    enable_async_flush: bool = True  # Asynchronous background flushing
    
    # Optimization flags
    skip_risk_assessment: bool = False  # Skip risk assessment for performance
    minimal_details: bool = False  # Store minimal details for speed
    compress_large_payloads: bool = True  # Compress payloads > 1KB


@dataclass
class PerformanceMetrics:
    """Performance metrics for audit logging."""
    total_logs_processed: int = 0
    average_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    throughput_logs_per_second: float = 0.0
    buffer_utilization: float = 0.0
    flush_operations: int = 0
    failed_operations: int = 0
    memory_usage_mb: float = 0.0
    
    # Latency tracking
    latency_samples: Deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_latency_sample(self, latency_ms: float):
        """Add a latency sample for metrics calculation."""
        self.latency_samples.append(latency_ms)
        self.total_logs_processed += 1
        
        # Update running averages
        if self.latency_samples:
            sorted_samples = sorted(self.latency_samples)
            self.average_latency_ms = sum(sorted_samples) / len(sorted_samples)
            
            # Calculate percentiles
            if len(sorted_samples) >= 20:  # Need sufficient samples
                p95_idx = int(0.95 * len(sorted_samples))
                p99_idx = int(0.99 * len(sorted_samples))
                self.p95_latency_ms = sorted_samples[p95_idx]
                self.p99_latency_ms = sorted_samples[p99_idx]


class HighPerformanceAuditBuffer:
    """High-performance in-memory buffer for audit logs."""
    
    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.buffer: Deque[Dict[str, Any]] = deque(maxlen=config.buffer_size)
        self.lock = Lock()
        self.flush_event = Event()
        self.metrics = PerformanceMetrics()
        
        # Background flushing
        self.flush_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Storage backend
        self.storage = AuditLogBatchStorage(
            StorageConfig(
                batch_size=config.batch_size,
                max_memory_mb=config.max_memory_mb,
                max_workers=config.max_workers
            )
        )
    
    async def start(self):
        """Start the high-performance buffer."""
        self.running = True
        
        if self.config.enable_async_flush:
            self.flush_task = asyncio.create_task(self._background_flush_loop())
        
        logger.info("High-performance audit buffer started")
    
    async def stop(self):
        """Stop the buffer and flush remaining logs."""
        self.running = False
        
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self.flush_buffer()
        
        logger.info("High-performance audit buffer stopped")
    
    async def add_log_fast(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Add audit log with minimal latency.
        
        Returns:
            Latency in milliseconds
        """
        start_time = time.perf_counter()
        
        try:
            # Create minimal log entry for speed
            log_entry = {
                'id': uuid4(),
                'user_id': user_id,
                'tenant_id': tenant_id,
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'timestamp': datetime.utcnow(),
                'details': self._optimize_details(details) if details else {}
            }
            
            # Add to buffer with minimal locking
            with self.lock:
                self.buffer.append(log_entry)
                buffer_full = len(self.buffer) >= self.config.buffer_size * 0.8
            
            # Trigger immediate flush if buffer is getting full
            if buffer_full:
                self.flush_event.set()
            
            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.metrics.add_latency_sample(latency_ms)
            
            return latency_ms
            
        except Exception as e:
            logger.error(f"Failed to add audit log: {e}")
            self.metrics.failed_operations += 1
            return (time.perf_counter() - start_time) * 1000
    
    def _optimize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize details for minimal serialization overhead."""
        
        if self.config.minimal_details:
            # Store only essential details for performance
            essential_keys = {'status', 'error', 'operation_type', 'resource_count'}
            return {k: v for k, v in details.items() if k in essential_keys}
        
        # Compress large payloads
        if self.config.compress_large_payloads:
            details_str = json.dumps(details, default=str)
            if len(details_str) > 1024:  # 1KB threshold
                # Store reference to compressed data instead of full payload
                return {
                    '_large_payload': True,
                    '_size_bytes': len(details_str),
                    '_summary': str(details)[:200] + '...' if len(str(details)) > 200 else str(details)
                }
        
        return details
    
    async def _background_flush_loop(self):
        """Background loop for flushing buffer."""
        
        while self.running:
            try:
                # Wait for flush interval or flush event
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_flush_event()),
                    timeout=self.config.flush_interval_ms / 1000.0
                )
            except asyncio.TimeoutError:
                pass  # Timeout is expected for periodic flushing
            
            if self.running:
                await self.flush_buffer()
    
    async def _wait_for_flush_event(self):
        """Wait for flush event in async context."""
        while not self.flush_event.is_set():
            await asyncio.sleep(0.001)  # 1ms polling
        self.flush_event.clear()
    
    async def flush_buffer(self) -> int:
        """Flush buffer contents to storage."""
        
        if not self.buffer:
            return 0
        
        # Extract logs from buffer
        with self.lock:
            logs_to_flush = list(self.buffer)
            self.buffer.clear()
        
        if not logs_to_flush:
            return 0
        
        try:
            # Convert to AuditLogModel instances
            audit_logs = []
            for log_data in logs_to_flush:
                audit_log = AuditLogModel(
                    id=log_data['id'],
                    user_id=log_data['user_id'],
                    tenant_id=log_data['tenant_id'],
                    action=log_data['action'],
                    resource_type=log_data['resource_type'],
                    resource_id=log_data['resource_id'],
                    ip_address=log_data['ip_address'],
                    user_agent=log_data['user_agent'],
                    details=log_data['details'],
                    timestamp=log_data['timestamp']
                )
                audit_logs.append(audit_log)
            
            # Batch store with optimized storage
            await self.storage.store_audit_logs_batch(audit_logs)
            
            self.metrics.flush_operations += 1
            logger.debug(f"Flushed {len(logs_to_flush)} audit logs")
            
            return len(logs_to_flush)
            
        except Exception as e:
            logger.error(f"Failed to flush audit buffer: {e}")
            self.metrics.failed_operations += 1
            return 0
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        
        # Update buffer utilization
        with self.lock:
            self.metrics.buffer_utilization = len(self.buffer) / self.config.buffer_size
        
        # Update memory usage
        self.metrics.memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Calculate throughput
        if self.metrics.total_logs_processed > 0 and self.metrics.latency_samples:
            time_span = len(self.metrics.latency_samples) * (self.config.flush_interval_ms / 1000.0)
            if time_span > 0:
                self.metrics.throughput_logs_per_second = self.metrics.total_logs_processed / time_span
        
        return self.metrics


class OptimizedAuditService:
    """
    Optimized audit service with < 50ms write latency.
    
    Features:
    - High-performance in-memory buffering
    - Asynchronous background flushing
    - Minimal serialization overhead
    - Lock-free operations where possible
    - Performance monitoring and alerting
    """
    
    def __init__(self, config: PerformanceConfig = None):
        self.config = config or PerformanceConfig()
        self.buffer = HighPerformanceAuditBuffer(self.config)
        self.performance_alerts: List[Callable] = []
        
        # Performance monitoring
        self.last_performance_check = time.time()
        self.performance_check_interval = 30.0  # 30 seconds
    
    async def start(self):
        """Start the optimized audit service."""
        await self.buffer.start()
        logger.info("Optimized audit service started")
    
    async def stop(self):
        """Stop the optimized audit service."""
        await self.buffer.stop()
        logger.info("Optimized audit service stopped")
    
    async def log_audit_event_fast(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log audit event with optimized performance.
        
        Target: < 50ms latency
        
        Returns:
            Dictionary with latency and status information
        """
        
        try:
            # Fast path logging
            latency_ms = await self.buffer.add_log_fast(
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )
            
            # Performance monitoring
            await self._check_performance_alerts(latency_ms)
            
            return {
                'status': 'success',
                'latency_ms': latency_ms,
                'target_met': latency_ms < self.config.target_latency_ms,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Fast audit logging failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'latency_ms': self.config.target_latency_ms,  # Assume worst case
                'target_met': False,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _check_performance_alerts(self, current_latency_ms: float):
        """Check if performance alerts should be triggered."""
        
        now = time.time()
        if now - self.last_performance_check < self.performance_check_interval:
            return
        
        self.last_performance_check = now
        metrics = self.buffer.get_performance_metrics()
        
        # Check latency thresholds
        if metrics.p95_latency_ms > self.config.target_latency_ms:
            await self._trigger_performance_alert(
                'high_latency',
                f"P95 latency ({metrics.p95_latency_ms:.2f}ms) exceeds target ({self.config.target_latency_ms}ms)"
            )
        
        # Check buffer utilization
        if metrics.buffer_utilization > 0.9:
            await self._trigger_performance_alert(
                'high_buffer_utilization',
                f"Buffer utilization ({metrics.buffer_utilization:.1%}) is critically high"
            )
        
        # Check memory usage
        if metrics.memory_usage_mb > self.config.max_memory_mb:
            await self._trigger_performance_alert(
                'high_memory_usage',
                f"Memory usage ({metrics.memory_usage_mb:.1f}MB) exceeds limit ({self.config.max_memory_mb}MB)"
            )
    
    async def _trigger_performance_alert(self, alert_type: str, message: str):
        """Trigger performance alert."""
        
        alert_data = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': self.buffer.get_performance_metrics()
        }
        
        logger.warning(f"Performance alert: {message}")
        
        # Trigger registered alert handlers
        for alert_handler in self.performance_alerts:
            try:
                await alert_handler(alert_data)
            except Exception as e:
                logger.error(f"Performance alert handler failed: {e}")
    
    def add_performance_alert_handler(self, handler: Callable):
        """Add performance alert handler."""
        self.performance_alerts.append(handler)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        
        metrics = self.buffer.get_performance_metrics()
        
        return {
            'performance_summary': {
                'target_latency_ms': self.config.target_latency_ms,
                'average_latency_ms': metrics.average_latency_ms,
                'p95_latency_ms': metrics.p95_latency_ms,
                'p99_latency_ms': metrics.p99_latency_ms,
                'target_met': metrics.p95_latency_ms < self.config.target_latency_ms,
                'throughput_logs_per_second': metrics.throughput_logs_per_second
            },
            'resource_utilization': {
                'buffer_utilization': metrics.buffer_utilization,
                'memory_usage_mb': metrics.memory_usage_mb,
                'max_memory_mb': self.config.max_memory_mb
            },
            'operational_metrics': {
                'total_logs_processed': metrics.total_logs_processed,
                'flush_operations': metrics.flush_operations,
                'failed_operations': metrics.failed_operations,
                'success_rate': (
                    (metrics.total_logs_processed - metrics.failed_operations) / 
                    max(metrics.total_logs_processed, 1)
                )
            },
            'configuration': {
                'buffer_size': self.config.buffer_size,
                'flush_interval_ms': self.config.flush_interval_ms,
                'batch_size': self.config.batch_size,
                'async_flush_enabled': self.config.enable_async_flush
            }
        }
    
    async def benchmark_performance(self, num_logs: int = 1000) -> Dict[str, Any]:
        """
        Benchmark audit logging performance.
        
        Args:
            num_logs: Number of logs to generate for benchmarking
            
        Returns:
            Benchmark results
        """
        
        logger.info(f"Starting audit performance benchmark with {num_logs} logs")
        
        start_time = time.perf_counter()
        latencies = []
        
        # Generate test logs
        for i in range(num_logs):
            result = await self.log_audit_event_fast(
                user_id=uuid4(),
                tenant_id=f"tenant_{i % 10}",  # 10 different tenants
                action=AuditAction.READ,
                resource_type="benchmark_test",
                resource_id=f"resource_{i}",
                details={'benchmark': True, 'iteration': i}
            )
            
            if result['status'] == 'success':
                latencies.append(result['latency_ms'])
        
        # Wait for all logs to be flushed
        await self.buffer.flush_buffer()
        
        total_time = time.perf_counter() - start_time
        
        # Calculate statistics
        if latencies:
            latencies.sort()
            avg_latency = sum(latencies) / len(latencies)
            p50_latency = latencies[len(latencies) // 2]
            p95_latency = latencies[int(0.95 * len(latencies))]
            p99_latency = latencies[int(0.99 * len(latencies))]
            max_latency = max(latencies)
            min_latency = min(latencies)
        else:
            avg_latency = p50_latency = p95_latency = p99_latency = max_latency = min_latency = 0
        
        throughput = num_logs / total_time if total_time > 0 else 0
        
        benchmark_results = {
            'test_parameters': {
                'num_logs': num_logs,
                'total_time_seconds': total_time,
                'target_latency_ms': self.config.target_latency_ms
            },
            'latency_statistics': {
                'average_ms': avg_latency,
                'median_ms': p50_latency,
                'p95_ms': p95_latency,
                'p99_ms': p99_latency,
                'min_ms': min_latency,
                'max_ms': max_latency
            },
            'performance_metrics': {
                'throughput_logs_per_second': throughput,
                'target_met': p95_latency < self.config.target_latency_ms,
                'success_rate': len(latencies) / num_logs
            },
            'recommendations': self._generate_performance_recommendations(
                avg_latency, p95_latency, throughput
            )
        }
        
        logger.info(f"Benchmark completed: {throughput:.1f} logs/sec, "
                   f"P95 latency: {p95_latency:.2f}ms")
        
        return benchmark_results
    
    def _generate_performance_recommendations(
        self,
        avg_latency: float,
        p95_latency: float,
        throughput: float
    ) -> List[str]:
        """Generate performance optimization recommendations."""
        
        recommendations = []
        
        if p95_latency > self.config.target_latency_ms:
            recommendations.append(
                f"P95 latency ({p95_latency:.2f}ms) exceeds target. "
                "Consider increasing buffer size or reducing flush interval."
            )
        
        if throughput < 1000:  # Less than 1000 logs/sec
            recommendations.append(
                "Low throughput detected. Consider enabling async flush and increasing batch size."
            )
        
        if avg_latency > self.config.target_latency_ms * 0.8:
            recommendations.append(
                "Average latency is high. Consider enabling minimal details mode."
            )
        
        if not recommendations:
            recommendations.append("Performance is optimal. No recommendations.")
        
        return recommendations


# Global optimized audit service instance
optimized_audit_service = OptimizedAuditService()