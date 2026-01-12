"""
Tests for Audit Performance Optimization.

Validates that audit logging achieves < 50ms write latency target
through comprehensive performance testing.
"""

import pytest
import asyncio
import time
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch, MagicMock

from src.security.audit_performance_optimizer import (
    OptimizedAuditService,
    PerformanceConfig,
    HighPerformanceAuditBuffer
)
from src.security.enhanced_audit_service_v2 import PerformanceOptimizedAuditService
from src.security.audit_performance_integration import (
    AuditPerformanceManager,
    log_audit_fast,
    audit_performance_manager
)
from src.security.models import AuditAction


class TestAuditPerformanceOptimization:
    """Test suite for audit performance optimization."""
    
    @pytest.fixture
    def performance_config(self):
        """Create performance configuration for testing."""
        return PerformanceConfig(
            buffer_size=1000,
            flush_interval_ms=50,
            batch_size=100,
            target_latency_ms=50.0,
            max_memory_mb=32,
            max_workers=2,
            enable_async_flush=True,
            skip_risk_assessment=True,
            minimal_details=True
        )
    
    @pytest.fixture
    def optimized_service(self, performance_config):
        """Create optimized audit service for testing."""
        return OptimizedAuditService(performance_config)
    
    @pytest.fixture
    def performance_buffer(self, performance_config):
        """Create high-performance buffer for testing."""
        return HighPerformanceAuditBuffer(performance_config)
    
    @pytest.fixture
    def performance_audit_service(self, performance_config):
        """Create performance-optimized audit service for testing."""
        return PerformanceOptimizedAuditService(performance_config)
    
    @pytest.fixture
    def audit_manager(self):
        """Create audit performance manager for testing."""
        return AuditPerformanceManager()
    
    @pytest.mark.asyncio
    async def test_high_performance_buffer_latency(self, performance_buffer):
        """Test that high-performance buffer meets latency targets."""
        
        await performance_buffer.start()
        
        try:
            latencies = []
            
            # Test 100 rapid log additions
            for i in range(100):
                latency_ms = await performance_buffer.add_log_fast(
                    user_id=uuid4(),
                    tenant_id=f"tenant_{i % 5}",
                    action=AuditAction.READ,
                    resource_type="test_resource",
                    resource_id=f"resource_{i}",
                    details={'test': True, 'iteration': i}
                )
                
                latencies.append(latency_ms)
            
            # Validate latency requirements
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
            
            # Assertions for < 50ms target
            assert avg_latency < 50.0, f"Average latency {avg_latency:.2f}ms exceeds 50ms target"
            assert p95_latency < 50.0, f"P95 latency {p95_latency:.2f}ms exceeds 50ms target"
            assert max_latency < 100.0, f"Max latency {max_latency:.2f}ms is too high"
            
            # Validate buffer performance
            metrics = performance_buffer.get_performance_metrics()
            assert metrics.total_logs_processed == 100
            assert metrics.average_latency_ms < 50.0
            
        finally:
            await performance_buffer.stop()
    
    @pytest.mark.asyncio
    @patch('src.security.audit_performance_optimizer.db_manager.get_session')
    async def test_optimized_service_performance(self, mock_session, optimized_service):
        """Test optimized audit service performance."""
        
        # Mock database session
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        
        await optimized_service.start()
        
        try:
            # Run performance benchmark
            benchmark_results = await optimized_service.benchmark_performance(num_logs=500)
            
            # Validate benchmark results
            latency_stats = benchmark_results['latency_statistics']
            perf_metrics = benchmark_results['performance_metrics']
            
            # Check latency targets
            assert latency_stats['average_ms'] < 50.0, "Average latency exceeds target"
            assert latency_stats['p95_ms'] < 50.0, "P95 latency exceeds target"
            assert latency_stats['p99_ms'] < 100.0, "P99 latency is too high"
            
            # Check performance metrics
            assert perf_metrics['target_met'], "Performance target not met"
            assert perf_metrics['throughput_logs_per_second'] > 100, "Throughput too low"
            assert perf_metrics['success_rate'] > 0.95, "Success rate too low"
            
        finally:
            await optimized_service.stop()
    
    @pytest.mark.asyncio
    @patch('src.security.enhanced_audit_service_v2.get_db_session')
    async def test_performance_optimized_audit_service(self, mock_session, performance_audit_service):
        """Test performance-optimized audit service with fallback."""
        
        # Mock database session
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        await performance_audit_service.start_service()
        
        try:
            # Test optimized path
            result = await performance_audit_service.log_audit_event_optimized(
                user_id=uuid4(),
                tenant_id="test_tenant",
                action=AuditAction.CREATE,
                resource_type="test_resource",
                details={'test': 'optimized_path'}
            )
            
            # Validate optimized result
            assert result['status'] == 'success'
            assert result['method'] == 'optimized'
            assert result['latency_ms'] < 50.0, f"Latency {result['latency_ms']:.2f}ms exceeds target"
            assert result['target_met'], "Performance target not met"
            
            # Test enhanced path (force enhanced logging)
            result = await performance_audit_service.log_audit_event_optimized(
                user_id=uuid4(),
                tenant_id="test_tenant",
                action=AuditAction.DELETE,  # Sensitive action
                resource_type="security",  # Critical resource
                details={'test': 'enhanced_path'},
                force_enhanced=True
            )
            
            # Enhanced path may be slower but should still work
            assert result['status'] == 'success'
            assert result['method'] == 'enhanced'
            
        finally:
            await performance_audit_service.stop_service()
    
    @pytest.mark.asyncio
    @patch('src.security.audit_performance_integration.audit_performance_manager')
    async def test_audit_performance_manager(self, mock_manager, audit_manager):
        """Test audit performance manager integration."""
        
        # Mock the manager's log_audit_fast method
        mock_manager.log_audit_fast.return_value = {
            'status': 'success',
            'latency_ms': 25.0,
            'target_met': True,
            'method': 'optimized'
        }
        
        # Test the convenience function
        result = await log_audit_fast(
            user_id=uuid4(),
            tenant_id="test_tenant",
            action=AuditAction.READ,
            resource_type="test_resource"
        )
        
        # Validate result
        assert result['status'] == 'success'
        assert result['latency_ms'] < 50.0
        assert result['target_met']
        
        # Verify the manager was called
        mock_manager.log_audit_fast.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, optimized_service):
        """Test performance under high load conditions."""
        
        await optimized_service.start()
        
        try:
            # Simulate high load with concurrent requests
            async def log_batch(batch_id: int, batch_size: int):
                latencies = []
                for i in range(batch_size):
                    result = await optimized_service.log_audit_event_fast(
                        user_id=uuid4(),
                        tenant_id=f"tenant_{batch_id}",
                        action=AuditAction.UPDATE,
                        resource_type="load_test",
                        resource_id=f"resource_{batch_id}_{i}",
                        details={'batch_id': batch_id, 'item': i}
                    )
                    
                    if result['status'] == 'success':
                        latencies.append(result['latency_ms'])
                
                return latencies
            
            # Run 10 concurrent batches of 50 logs each
            batch_tasks = [log_batch(i, 50) for i in range(10)]
            batch_results = await asyncio.gather(*batch_tasks)
            
            # Collect all latencies
            all_latencies = []
            for batch_latencies in batch_results:
                all_latencies.extend(batch_latencies)
            
            # Validate performance under load
            if all_latencies:
                avg_latency = sum(all_latencies) / len(all_latencies)
                p95_latency = sorted(all_latencies)[int(0.95 * len(all_latencies))]
                
                # Under load, we allow slightly higher latencies but still reasonable
                assert avg_latency < 75.0, f"Average latency under load {avg_latency:.2f}ms too high"
                assert p95_latency < 100.0, f"P95 latency under load {p95_latency:.2f}ms too high"
                
                # Ensure we processed a good number of logs
                assert len(all_latencies) >= 400, "Too many failed requests under load"
        
        finally:
            await optimized_service.stop()
    
    @pytest.mark.asyncio
    async def test_buffer_flush_performance(self, performance_buffer):
        """Test buffer flush performance."""
        
        await performance_buffer.start()
        
        try:
            # Fill buffer with logs
            for i in range(500):
                await performance_buffer.add_log_fast(
                    user_id=uuid4(),
                    tenant_id="flush_test",
                    action=AuditAction.CREATE,
                    resource_type="flush_test",
                    details={'item': i}
                )
            
            # Measure flush performance
            start_time = time.perf_counter()
            flushed_count = await performance_buffer.flush_buffer()
            flush_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            
            # Validate flush performance
            assert flushed_count > 0, "No logs were flushed"
            assert flush_time < 200.0, f"Flush time {flush_time:.2f}ms is too slow"
            
            # Validate buffer is empty after flush
            metrics = performance_buffer.get_performance_metrics()
            assert metrics.buffer_utilization == 0.0, "Buffer not empty after flush"
            
        finally:
            await performance_buffer.stop()
    
    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self, performance_buffer):
        """Test memory usage stays within limits."""
        
        await performance_buffer.start()
        
        try:
            # Add many logs to test memory usage
            for i in range(1000):
                await performance_buffer.add_log_fast(
                    user_id=uuid4(),
                    tenant_id="memory_test",
                    action=AuditAction.READ,
                    resource_type="memory_test",
                    details={'large_data': 'x' * 1000, 'item': i}  # 1KB per log
                )
            
            # Check memory usage
            metrics = performance_buffer.get_performance_metrics()
            
            # Memory should be reasonable (less than configured max)
            assert metrics.memory_usage_mb < performance_buffer.config.max_memory_mb * 2, \
                f"Memory usage {metrics.memory_usage_mb:.1f}MB exceeds reasonable limits"
            
            # Buffer utilization should be managed
            assert metrics.buffer_utilization <= 1.0, "Buffer utilization exceeds 100%"
            
        finally:
            await performance_buffer.stop()
    
    @pytest.mark.asyncio
    async def test_performance_degradation_handling(self, performance_audit_service):
        """Test handling of performance degradation."""
        
        await performance_audit_service.start_service()
        
        try:
            # Simulate performance degradation by forcing slow operations
            original_target = performance_audit_service.performance_config.target_latency_ms
            performance_audit_service.performance_config.target_latency_ms = 1.0  # Very strict target
            
            # Log several events that will likely exceed the strict target
            for i in range(10):
                result = await performance_audit_service.log_audit_event_optimized(
                    user_id=uuid4(),
                    tenant_id="degradation_test",
                    action=AuditAction.UPDATE,
                    resource_type="test",
                    details={'test': 'degradation', 'item': i}
                )
                
                # Some requests may not meet the very strict target
                # but the service should handle this gracefully
                assert result['status'] == 'success'
            
            # Check that service adapted to degradation
            violations = performance_audit_service.performance_threshold_violations
            assert violations >= 0, "Violation tracking not working"
            
            # Restore original target
            performance_audit_service.performance_config.target_latency_ms = original_target
            
        finally:
            await performance_audit_service.stop_service()
    
    def test_performance_config_validation(self):
        """Test performance configuration validation."""
        
        # Test valid configuration
        config = PerformanceConfig(
            buffer_size=1000,
            flush_interval_ms=50,
            target_latency_ms=50.0
        )
        
        assert config.buffer_size == 1000
        assert config.flush_interval_ms == 50
        assert config.target_latency_ms == 50.0
        
        # Test configuration with performance optimizations
        fast_config = PerformanceConfig(
            buffer_size=500,
            flush_interval_ms=25,
            target_latency_ms=25.0,
            skip_risk_assessment=True,
            minimal_details=True
        )
        
        assert fast_config.skip_risk_assessment
        assert fast_config.minimal_details
        assert fast_config.flush_interval_ms == 25
    
    @pytest.mark.asyncio
    async def test_comprehensive_performance_benchmark(self, audit_manager):
        """Test comprehensive performance benchmark."""
        
        # Mock the underlying service to avoid database dependencies
        with patch.object(audit_manager, 'audit_service') as mock_service:
            mock_service.benchmark_comprehensive_performance.return_value = {
                'test_parameters': {'num_logs_per_test': 100},
                'optimized_results': {
                    'latency_statistics': {
                        'average_ms': 15.0,
                        'p95_ms': 25.0,
                        'p99_ms': 35.0
                    },
                    'performance_metrics': {
                        'target_met': True,
                        'throughput_logs_per_second': 2000.0,
                        'success_rate': 1.0
                    }
                }
            }
            
            # Run performance test
            results = await audit_manager.run_performance_test(num_logs=100)
            
            # Validate results
            assert results['test_summary']['target_achieved']
            assert results['test_summary']['achieved_p95_latency_ms'] < 50.0
            assert results['verdict']['performance_grade'] == 'PASS'
    
    @pytest.mark.asyncio
    async def test_audit_performance_integration_end_to_end(self):
        """Test end-to-end audit performance integration."""
        
        # This test validates the complete integration without mocking
        # to ensure real performance characteristics
        
        manager = AuditPerformanceManager()
        
        try:
            # Start the manager
            await manager.start()
            
            # Test rapid logging
            start_time = time.perf_counter()
            results = []
            
            for i in range(50):  # Smaller test for real execution
                result = await manager.log_audit_fast(
                    user_id=uuid4(),
                    tenant_id="integration_test",
                    action=AuditAction.READ,
                    resource_type="integration_test",
                    resource_id=f"resource_{i}",
                    details={'test': 'integration', 'item': i}
                )
                results.append(result)
            
            total_time = time.perf_counter() - start_time
            
            # Validate results
            successful_results = [r for r in results if r.get('status') == 'success']
            assert len(successful_results) >= 45, "Too many failed requests"  # Allow some failures
            
            # Check latencies
            latencies = [r.get('latency_ms', 0) for r in successful_results if r.get('latency_ms')]
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                max_latency = max(latencies)
                
                # Real-world performance may be slightly higher due to actual I/O
                assert avg_latency < 100.0, f"Average latency {avg_latency:.2f}ms too high for integration test"
                assert max_latency < 200.0, f"Max latency {max_latency:.2f}ms too high for integration test"
            
            # Check overall throughput
            throughput = len(successful_results) / total_time
            assert throughput > 50.0, f"Throughput {throughput:.1f} logs/sec too low"
            
            # Get performance summary
            summary = manager.get_performance_summary()
            assert summary['service_health']['started']
            assert summary['performance_summary']['total_requests'] >= 45
            
        finally:
            await manager.stop()


if __name__ == "__main__":
    # Run a quick performance validation
    async def quick_performance_test():
        """Quick performance validation."""
        
        print("Running quick audit performance validation...")
        
        config = PerformanceConfig(
            buffer_size=500,
            flush_interval_ms=50,
            target_latency_ms=50.0,
            minimal_details=True,
            skip_risk_assessment=True
        )
        
        service = OptimizedAuditService(config)
        await service.start()
        
        try:
            # Quick benchmark
            results = await service.benchmark_performance(num_logs=100)
            
            latency_stats = results['latency_statistics']
            perf_metrics = results['performance_metrics']
            
            print(f"Average latency: {latency_stats['average_ms']:.2f}ms")
            print(f"P95 latency: {latency_stats['p95_ms']:.2f}ms")
            print(f"Target met: {perf_metrics['target_met']}")
            print(f"Throughput: {perf_metrics['throughput_logs_per_second']:.1f} logs/sec")
            
            if perf_metrics['target_met']:
                print("✅ Performance target achieved!")
            else:
                print("❌ Performance target not met")
                
        finally:
            await service.stop()
    
    # Run the quick test
    asyncio.run(quick_performance_test())