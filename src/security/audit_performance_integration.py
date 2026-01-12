"""
Audit Performance Integration Module.

Integrates the performance-optimized audit service with existing components
to achieve < 50ms write latency while maintaining compatibility.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from contextlib import asynccontextmanager

from src.security.enhanced_audit_service_v2 import (
    PerformanceOptimizedAuditService,
    PerformanceConfig
)
from src.security.models import AuditAction
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AuditPerformanceManager:
    """
    Manages the performance-optimized audit service integration.
    
    Provides a drop-in replacement for existing audit service calls
    with automatic performance optimization and fallback handling.
    """
    
    def __init__(self):
        # Performance configuration optimized for < 50ms latency
        self.performance_config = PerformanceConfig(
            buffer_size=2000,  # Smaller buffer for lower latency
            flush_interval_ms=50,  # Flush every 50ms
            batch_size=200,  # Smaller batches for faster processing
            target_latency_ms=50.0,  # Target < 50ms
            max_memory_mb=64,  # Conservative memory usage
            max_workers=2,  # Fewer workers to reduce overhead
            enable_async_flush=True,
            skip_risk_assessment=True,  # Skip for performance
            minimal_details=True,  # Minimal details for speed
            compress_large_payloads=False  # Skip compression for speed
        )
        
        self.audit_service = PerformanceOptimizedAuditService(self.performance_config)
        self.started = False
        self.performance_stats = {
            'total_requests': 0,
            'fast_path_requests': 0,
            'fallback_requests': 0,
            'average_latency_ms': 0.0,
            'target_violations': 0
        }
    
    async def start(self):
        """Start the performance audit manager."""
        if not self.started:
            await self.audit_service.start_service()
            self.started = True
            logger.info("Audit performance manager started")
    
    async def stop(self):
        """Stop the performance audit manager."""
        if self.started:
            await self.audit_service.stop_service()
            self.started = False
            logger.info("Audit performance manager stopped")
    
    async def log_audit_fast(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Log audit event with performance optimization.
        
        This is the main entry point for high-performance audit logging.
        
        Returns:
            Result dictionary with performance metrics
        """
        
        if not self.started:
            await self.start()
        
        start_time = datetime.now()
        
        try:
            result = await self.audit_service.log_audit_event_optimized(
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                db=db
            )
            
            # Update performance statistics
            self._update_performance_stats(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Fast audit logging failed: {e}")
            
            # Calculate latency even for failures
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'status': 'error',
                'error': str(e),
                'latency_ms': latency_ms,
                'target_met': False,
                'method': 'error'
            }
    
    def _update_performance_stats(self, result: Dict[str, Any]):
        """Update internal performance statistics."""
        
        self.performance_stats['total_requests'] += 1
        
        # Track method used
        method = result.get('method', 'unknown')
        if method == 'optimized':
            self.performance_stats['fast_path_requests'] += 1
        elif method == 'enhanced':
            self.performance_stats['fallback_requests'] += 1
        
        # Track latency
        latency_ms = result.get('latency_ms', 0)
        if latency_ms > 0:
            # Running average
            total = self.performance_stats['total_requests']
            current_avg = self.performance_stats['average_latency_ms']
            self.performance_stats['average_latency_ms'] = (
                (current_avg * (total - 1) + latency_ms) / total
            )
        
        # Track target violations
        if not result.get('target_met', False):
            self.performance_stats['target_violations'] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        
        total = self.performance_stats['total_requests']
        if total == 0:
            return {
                'status': 'no_data',
                'message': 'No audit requests processed yet'
            }
        
        fast_path_rate = self.performance_stats['fast_path_requests'] / total
        fallback_rate = self.performance_stats['fallback_requests'] / total
        violation_rate = self.performance_stats['target_violations'] / total
        
        return {
            'performance_summary': {
                'total_requests': total,
                'average_latency_ms': self.performance_stats['average_latency_ms'],
                'target_latency_ms': self.performance_config.target_latency_ms,
                'target_achievement_rate': 1.0 - violation_rate,
                'fast_path_usage_rate': fast_path_rate,
                'fallback_usage_rate': fallback_rate
            },
            'service_health': {
                'started': self.started,
                'performance_mode': 'optimized' if fast_path_rate > 0.8 else 'mixed',
                'health_status': 'healthy' if violation_rate < 0.1 else 'degraded'
            },
            'configuration': {
                'buffer_size': self.performance_config.buffer_size,
                'flush_interval_ms': self.performance_config.flush_interval_ms,
                'batch_size': self.performance_config.batch_size,
                'minimal_details': self.performance_config.minimal_details
            }
        }
    
    async def run_performance_test(self, num_logs: int = 100) -> Dict[str, Any]:
        """
        Run a quick performance test to validate < 50ms latency.
        
        Args:
            num_logs: Number of test logs to generate
            
        Returns:
            Performance test results
        """
        
        logger.info(f"Running performance test with {num_logs} logs")
        
        if not self.started:
            await self.start()
        
        test_results = await self.audit_service.benchmark_comprehensive_performance(
            num_logs=num_logs,
            test_enhanced=False  # Only test optimized for speed
        )
        
        # Extract key metrics
        optimized_results = test_results.get('optimized_results', {})
        latency_stats = optimized_results.get('latency_statistics', {})
        perf_metrics = optimized_results.get('performance_metrics', {})
        
        p95_latency = latency_stats.get('p95_ms', 0)
        target_met = perf_metrics.get('target_met', False)
        throughput = perf_metrics.get('throughput_logs_per_second', 0)
        
        return {
            'test_summary': {
                'num_logs_tested': num_logs,
                'target_latency_ms': self.performance_config.target_latency_ms,
                'achieved_p95_latency_ms': p95_latency,
                'target_achieved': target_met,
                'throughput_logs_per_second': throughput
            },
            'detailed_results': optimized_results,
            'verdict': {
                'performance_grade': 'PASS' if target_met else 'FAIL',
                'recommendation': (
                    "Performance target achieved" if target_met else
                    f"Performance target missed by {p95_latency - self.performance_config.target_latency_ms:.1f}ms"
                )
            }
        }


# Global audit performance manager
audit_performance_manager = AuditPerformanceManager()


# Convenience functions for easy integration
async def log_audit_fast(
    user_id: Optional[UUID],
    tenant_id: str,
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    db: Session = None
) -> Dict[str, Any]:
    """
    Convenience function for fast audit logging.
    
    This function provides a drop-in replacement for existing audit logging
    calls with automatic performance optimization.
    """
    return await audit_performance_manager.log_audit_fast(
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
        db=db
    )


@asynccontextmanager
async def audit_performance_context():
    """
    Context manager for audit performance optimization.
    
    Usage:
        async with audit_performance_context():
            # All audit logging within this context will be optimized
            await log_audit_fast(...)
    """
    await audit_performance_manager.start()
    try:
        yield audit_performance_manager
    finally:
        # Don't stop the service here as it might be used elsewhere
        pass


class AuditPerformanceMonitor:
    """
    Monitors audit performance and provides alerts when targets are not met.
    """
    
    def __init__(self, manager: AuditPerformanceManager):
        self.manager = manager
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, check_interval: float = 30.0):
        """Start performance monitoring."""
        
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(check_interval)
        )
        
        logger.info(f"Audit performance monitoring started (interval: {check_interval}s)")
    
    async def stop_monitoring(self):
        """Stop performance monitoring."""
        
        self.monitoring_active = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Audit performance monitoring stopped")
    
    async def _monitoring_loop(self, check_interval: float):
        """Main monitoring loop."""
        
        while self.monitoring_active:
            try:
                await asyncio.sleep(check_interval)
                
                if not self.monitoring_active:
                    break
                
                # Get performance summary
                summary = self.manager.get_performance_summary()
                
                # Check for performance issues
                await self._check_performance_alerts(summary)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
    
    async def _check_performance_alerts(self, summary: Dict[str, Any]):
        """Check for performance alerts."""
        
        if summary.get('status') == 'no_data':
            return
        
        perf_summary = summary.get('performance_summary', {})
        service_health = summary.get('service_health', {})
        
        # Check average latency
        avg_latency = perf_summary.get('average_latency_ms', 0)
        target_latency = perf_summary.get('target_latency_ms', 50)
        
        if avg_latency > target_latency:
            logger.warning(
                f"Average audit latency ({avg_latency:.2f}ms) exceeds target ({target_latency}ms)"
            )
        
        # Check target achievement rate
        achievement_rate = perf_summary.get('target_achievement_rate', 0)
        if achievement_rate < 0.9:  # Less than 90% success rate
            logger.warning(
                f"Audit performance target achievement rate is low: {achievement_rate:.1%}"
            )
        
        # Check service health
        health_status = service_health.get('health_status', 'unknown')
        if health_status == 'degraded':
            logger.warning("Audit service performance is degraded")
        
        # Check fallback usage
        fallback_rate = perf_summary.get('fallback_usage_rate', 0)
        if fallback_rate > 0.2:  # More than 20% fallback usage
            logger.warning(
                f"High fallback usage rate: {fallback_rate:.1%}. "
                "Consider optimizing audit configuration."
            )


# Global performance monitor
audit_performance_monitor = AuditPerformanceMonitor(audit_performance_manager)