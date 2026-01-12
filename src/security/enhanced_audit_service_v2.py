"""
Enhanced Audit Service V2 with Performance Optimization.

Integrates high-performance audit logging with existing enhanced features
while maintaining < 50ms write latency target.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from src.security.audit_service import EnhancedAuditService, RiskLevel
from src.security.audit_performance_optimizer import (
    OptimizedAuditService, 
    PerformanceConfig,
    PerformanceMetrics
)
from src.security.models import AuditAction, AuditLogModel
from src.database.connection import get_db_session
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PerformanceOptimizedAuditService(EnhancedAuditService):
    """
    Performance-optimized audit service that combines enhanced features
    with high-performance logging to achieve < 50ms write latency.
    """
    
    def __init__(self, performance_config: PerformanceConfig = None):
        super().__init__()
        
        # Performance optimization
        self.performance_config = performance_config or PerformanceConfig()
        self.optimized_service = OptimizedAuditService(self.performance_config)
        
        # Performance mode flags
        self.high_performance_mode = True
        self.fallback_to_enhanced = False
        
        # Performance monitoring
        self.performance_threshold_violations = 0
        self.max_threshold_violations = 5  # Switch to fallback after 5 violations
        
    async def start_service(self):
        """Start the performance-optimized audit service."""
        await self.optimized_service.start()
        
        # Add performance alert handler
        self.optimized_service.add_performance_alert_handler(
            self._handle_performance_alert
        )
        
        logger.info("Performance-optimized audit service started")
    
    async def stop_service(self):
        """Stop the performance-optimized audit service."""
        await self.optimized_service.stop()
        logger.info("Performance-optimized audit service stopped")
    
    async def log_audit_event_optimized(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db: Session = None,
        force_enhanced: bool = False
    ) -> Dict[str, Any]:
        """
        Log audit event with performance optimization.
        
        Args:
            force_enhanced: Force use of enhanced logging (slower but more features)
            
        Returns:
            Result with performance metrics
        """
        
        # Determine which logging method to use
        use_enhanced = (
            force_enhanced or 
            self.fallback_to_enhanced or 
            not self.high_performance_mode or
            self._requires_enhanced_logging(action, resource_type, details)
        )
        
        if use_enhanced:
            return await self._log_enhanced_with_fallback(
                user_id, tenant_id, action, resource_type, resource_id,
                ip_address, user_agent, details, db
            )
        else:
            return await self._log_optimized_with_monitoring(
                user_id, tenant_id, action, resource_type, resource_id,
                ip_address, user_agent, details
            )
    
    async def _log_optimized_with_monitoring(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        details: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Log using optimized service with performance monitoring."""
        
        try:
            result = await self.optimized_service.log_audit_event_fast(
                user_id=user_id,
                tenant_id=tenant_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )
            
            # Monitor performance
            if not result.get('target_met', False):
                self.performance_threshold_violations += 1
                
                # Switch to fallback if too many violations
                if self.performance_threshold_violations >= self.max_threshold_violations:
                    self.fallback_to_enhanced = True
                    logger.warning(
                        f"Switching to enhanced logging due to {self.performance_threshold_violations} "
                        "performance threshold violations"
                    )
            else:
                # Reset violation counter on success
                self.performance_threshold_violations = max(0, self.performance_threshold_violations - 1)
            
            return {
                **result,
                'method': 'optimized',
                'performance_violations': self.performance_threshold_violations
            }
            
        except Exception as e:
            logger.error(f"Optimized audit logging failed: {e}")
            
            # Fallback to enhanced logging
            return await self._log_enhanced_with_fallback(
                user_id, tenant_id, action, resource_type, resource_id,
                ip_address, user_agent, details, None
            )
    
    async def _log_enhanced_with_fallback(
        self,
        user_id: Optional[UUID],
        tenant_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        details: Optional[Dict[str, Any]],
        db: Session
    ) -> Dict[str, Any]:
        """Log using enhanced service as fallback."""
        
        start_time = datetime.now()
        
        try:
            if not db:
                db = get_db_session()
                close_db = True
            else:
                close_db = False
            
            try:
                result = await self.log_enhanced_audit_event(
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
                
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                return {
                    **result,
                    'method': 'enhanced',
                    'latency_ms': latency_ms,
                    'target_met': latency_ms < self.performance_config.target_latency_ms
                }
                
            finally:
                if close_db:
                    db.close()
                    
        except Exception as e:
            logger.error(f"Enhanced audit logging failed: {e}")
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'status': 'error',
                'error': str(e),
                'method': 'enhanced',
                'latency_ms': latency_ms,
                'target_met': False
            }
    
    def _requires_enhanced_logging(
        self,
        action: AuditAction,
        resource_type: str,
        details: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if enhanced logging features are required."""
        
        # High-risk operations require enhanced logging
        if action in self.sensitive_actions:
            return True
        
        # Critical resources require enhanced logging
        if resource_type in self.critical_resources:
            return True
        
        # Security-related operations require enhanced logging
        if resource_type in ['security', 'audit', 'permission', 'role']:
            return True
        
        # Large payloads might benefit from enhanced compression
        if details and len(str(details)) > 5000:  # 5KB threshold
            return True
        
        return False
    
    async def _handle_performance_alert(self, alert_data: Dict[str, Any]):
        """Handle performance alerts from optimized service."""
        
        alert_type = alert_data.get('type')
        message = alert_data.get('message')
        
        logger.warning(f"Performance alert [{alert_type}]: {message}")
        
        # Take corrective actions based on alert type
        if alert_type == 'high_latency':
            # Temporarily switch to minimal details mode
            self.performance_config.minimal_details = True
            logger.info("Enabled minimal details mode due to high latency")
            
        elif alert_type == 'high_buffer_utilization':
            # Force immediate flush
            await self.optimized_service.buffer.flush_buffer()
            logger.info("Forced buffer flush due to high utilization")
            
        elif alert_type == 'high_memory_usage':
            # Reduce buffer size temporarily
            original_size = self.performance_config.buffer_size
            self.performance_config.buffer_size = int(original_size * 0.7)
            logger.info(f"Reduced buffer size from {original_size} to {self.performance_config.buffer_size}")
    
    async def get_comprehensive_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report including both services."""
        
        optimized_report = self.optimized_service.get_performance_report()
        
        return {
            'service_status': {
                'high_performance_mode': self.high_performance_mode,
                'fallback_to_enhanced': self.fallback_to_enhanced,
                'performance_violations': self.performance_threshold_violations,
                'max_violations_threshold': self.max_threshold_violations
            },
            'optimized_service': optimized_report,
            'configuration': {
                'target_latency_ms': self.performance_config.target_latency_ms,
                'buffer_size': self.performance_config.buffer_size,
                'flush_interval_ms': self.performance_config.flush_interval_ms,
                'minimal_details': self.performance_config.minimal_details,
                'skip_risk_assessment': self.performance_config.skip_risk_assessment
            },
            'recommendations': self._generate_service_recommendations(optimized_report)
        }
    
    def _generate_service_recommendations(self, optimized_report: Dict[str, Any]) -> List[str]:
        """Generate service-level recommendations."""
        
        recommendations = []
        
        perf_summary = optimized_report.get('performance_summary', {})
        resource_util = optimized_report.get('resource_utilization', {})
        
        # Check if target is being met
        if not perf_summary.get('target_met', False):
            recommendations.append(
                "Performance target not being met consistently. "
                "Consider enabling minimal details mode or increasing buffer size."
            )
        
        # Check fallback usage
        if self.fallback_to_enhanced:
            recommendations.append(
                "Service is using enhanced logging fallback. "
                "Review performance alerts and optimize configuration."
            )
        
        # Check buffer utilization
        buffer_util = resource_util.get('buffer_utilization', 0)
        if buffer_util > 0.8:
            recommendations.append(
                f"High buffer utilization ({buffer_util:.1%}). "
                "Consider reducing flush interval or increasing buffer size."
            )
        
        # Check throughput
        throughput = perf_summary.get('throughput_logs_per_second', 0)
        if throughput < 500:  # Less than 500 logs/sec
            recommendations.append(
                "Low throughput detected. Consider enabling async flush and optimizing batch size."
            )
        
        if not recommendations:
            recommendations.append("Performance is optimal across all metrics.")
        
        return recommendations
    
    async def benchmark_comprehensive_performance(
        self,
        num_logs: int = 1000,
        test_enhanced: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive performance benchmark comparing optimized vs enhanced logging.
        
        Args:
            num_logs: Number of logs for each test
            test_enhanced: Whether to test enhanced logging as well
            
        Returns:
            Comprehensive benchmark results
        """
        
        logger.info(f"Starting comprehensive audit performance benchmark")
        
        results = {
            'test_parameters': {
                'num_logs_per_test': num_logs,
                'test_enhanced': test_enhanced,
                'target_latency_ms': self.performance_config.target_latency_ms
            },
            'optimized_results': {},
            'enhanced_results': {},
            'comparison': {}
        }
        
        # Test optimized service
        logger.info("Benchmarking optimized audit service...")
        results['optimized_results'] = await self.optimized_service.benchmark_performance(num_logs)
        
        # Test enhanced service if requested
        if test_enhanced:
            logger.info("Benchmarking enhanced audit service...")
            results['enhanced_results'] = await self._benchmark_enhanced_service(num_logs)
            
            # Generate comparison
            results['comparison'] = self._compare_benchmark_results(
                results['optimized_results'],
                results['enhanced_results']
            )
        
        logger.info("Comprehensive benchmark completed")
        return results
    
    async def _benchmark_enhanced_service(self, num_logs: int) -> Dict[str, Any]:
        """Benchmark the enhanced audit service."""
        
        import time
        from uuid import uuid4
        
        start_time = time.perf_counter()
        latencies = []
        
        db = get_db_session()
        try:
            for i in range(num_logs):
                log_start = time.perf_counter()
                
                await self.log_enhanced_audit_event(
                    user_id=uuid4(),
                    tenant_id=f"tenant_{i % 10}",
                    action=AuditAction.READ,
                    resource_type="benchmark_test",
                    resource_id=f"resource_{i}",
                    details={'benchmark': True, 'iteration': i, 'enhanced': True},
                    db=db
                )
                
                latency_ms = (time.perf_counter() - log_start) * 1000
                latencies.append(latency_ms)
        finally:
            db.close()
        
        total_time = time.perf_counter() - start_time
        
        # Calculate statistics
        if latencies:
            latencies.sort()
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = latencies[int(0.95 * len(latencies))]
            p99_latency = latencies[int(0.99 * len(latencies))]
        else:
            avg_latency = p95_latency = p99_latency = 0
        
        throughput = num_logs / total_time if total_time > 0 else 0
        
        return {
            'test_parameters': {
                'num_logs': num_logs,
                'total_time_seconds': total_time
            },
            'latency_statistics': {
                'average_ms': avg_latency,
                'p95_ms': p95_latency,
                'p99_ms': p99_latency
            },
            'performance_metrics': {
                'throughput_logs_per_second': throughput,
                'target_met': p95_latency < self.performance_config.target_latency_ms
            }
        }
    
    def _compare_benchmark_results(
        self,
        optimized_results: Dict[str, Any],
        enhanced_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare benchmark results between optimized and enhanced services."""
        
        opt_latency = optimized_results['latency_statistics']
        enh_latency = enhanced_results['latency_statistics']
        
        opt_perf = optimized_results['performance_metrics']
        enh_perf = enhanced_results['performance_metrics']
        
        return {
            'latency_improvement': {
                'average_improvement_percent': (
                    (enh_latency['average_ms'] - opt_latency['average_ms']) / 
                    max(enh_latency['average_ms'], 1) * 100
                ),
                'p95_improvement_percent': (
                    (enh_latency['p95_ms'] - opt_latency['p95_ms']) / 
                    max(enh_latency['p95_ms'], 1) * 100
                )
            },
            'throughput_improvement': {
                'improvement_percent': (
                    (opt_perf['throughput_logs_per_second'] - enh_perf['throughput_logs_per_second']) / 
                    max(enh_perf['throughput_logs_per_second'], 1) * 100
                )
            },
            'target_achievement': {
                'optimized_meets_target': opt_perf['target_met'],
                'enhanced_meets_target': enh_perf['target_met']
            },
            'recommendation': (
                "Use optimized service for high-volume, low-latency requirements. "
                "Use enhanced service for security-critical operations requiring full audit features."
            )
        }


# Global performance-optimized audit service
performance_audit_service = PerformanceOptimizedAuditService()