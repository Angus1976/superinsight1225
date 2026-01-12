"""
Test suite for compliance report performance optimization.

Tests the < 30 seconds target for compliance report generation.
"""

import asyncio
import pytest
import time
import statistics
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock

from src.compliance.performance_optimizer import (
    ComplianceReportPerformanceOptimizer,
    OptimizationConfig,
    PerformanceMetrics
)
from src.compliance.report_generator import ComplianceStandard, ReportType
from src.database.connection import get_db_session


class TestCompliancePerformanceOptimization:
    """Test compliance report performance optimization"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        mock_session = Mock()
        
        # Mock query results
        mock_result = Mock()
        mock_result.total_events = 1000
        mock_result.high_risk_events = 50
        mock_result.failed_logins = 10
        mock_result.active_users = 100
        mock_result.action = "LOGIN"
        mock_result.action_count = 500
        mock_result.security_events = 25
        mock_result.threat_events = 5
        mock_result.unique_ips = 50
        mock_result.export_events = 20
        mock_result.delete_events = 5
        mock_result.desensitization_events = 15
        mock_result.permission_checks = 2000
        mock_result.role_assignments = 50
        mock_result.permission_violations = 10
        
        mock_session.execute.return_value.fetchall.return_value = [mock_result]
        mock_session.execute.return_value.fetchone.return_value = mock_result
        
        return mock_session
    
    @pytest.fixture
    def optimizer(self):
        """Create optimizer with test configuration"""
        config = OptimizationConfig(
            enable_parallel_processing=True,
            enable_caching=True,
            enable_query_optimization=True,
            max_workers=4,
            cache_ttl_seconds=300,
            batch_size=1000,
            memory_limit_mb=512
        )
        return ComplianceReportPerformanceOptimizer(config)
    
    @pytest.fixture
    def test_parameters(self):
        """Common test parameters"""
        return {
            "tenant_id": "test_tenant",
            "standard": ComplianceStandard.GDPR,
            "report_type": ReportType.COMPREHENSIVE,
            "start_date": datetime.utcnow() - timedelta(days=30),
            "end_date": datetime.utcnow(),
            "generated_by": uuid4()
        }
    
    @pytest.mark.asyncio
    async def test_optimized_report_generation_performance(self, optimizer, mock_db_session, test_parameters):
        """Test that optimized report generation meets < 30 seconds target"""
        
        start_time = time.time()
        
        report, performance_metrics = await optimizer.generate_optimized_compliance_report(
            db=mock_db_session,
            include_recommendations=True,
            **test_parameters
        )
        
        total_time = time.time() - start_time
        
        # Assertions
        assert total_time < 30.0, f"Report generation took {total_time:.2f}s, exceeds 30s target"
        assert performance_metrics.total_time < 30.0
        assert performance_metrics.total_time > 0
        assert report is not None
        assert report.report_id is not None
        assert report.tenant_id == test_parameters["tenant_id"]
        assert report.standard == test_parameters["standard"]
        
        print(f"✅ Report generated in {total_time:.2f}s (target: 30s)")
        print(f"   Data collection: {performance_metrics.data_collection_time:.2f}s")
        print(f"   Metrics generation: {performance_metrics.metrics_generation_time:.2f}s")
        print(f"   Violations detection: {performance_metrics.violations_detection_time:.2f}s")
        print(f"   Report assembly: {performance_metrics.report_assembly_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_parallel_data_collection_performance(self, optimizer, mock_db_session, test_parameters):
        """Test parallel data collection performance"""
        
        start_time = time.time()
        
        statistics = await optimizer._collect_statistics_parallel(
            tenant_id=test_parameters["tenant_id"],
            start_date=test_parameters["start_date"],
            end_date=test_parameters["end_date"],
            db=mock_db_session
        )
        
        collection_time = time.time() - start_time
        
        # Assertions
        assert collection_time < 10.0, f"Data collection took {collection_time:.2f}s, exceeds 10s target"
        assert statistics is not None
        assert "audit_statistics" in statistics
        assert "security_statistics" in statistics
        assert "data_protection_statistics" in statistics
        assert "access_control_statistics" in statistics
        
        print(f"✅ Parallel data collection completed in {collection_time:.2f}s (target: 10s)")
    
    @pytest.mark.asyncio
    async def test_caching_performance(self, optimizer, mock_db_session, test_parameters):
        """Test caching performance and hit rate"""
        
        # First call (cache miss)
        start_time = time.time()
        statistics1 = await optimizer._collect_statistics_parallel(
            tenant_id=test_parameters["tenant_id"],
            start_date=test_parameters["start_date"],
            end_date=test_parameters["end_date"],
            db=mock_db_session
        )
        first_call_time = time.time() - start_time
        
        # Second call (cache hit)
        start_time = time.time()
        statistics2 = await optimizer._collect_statistics_parallel(
            tenant_id=test_parameters["tenant_id"],
            start_date=test_parameters["start_date"],
            end_date=test_parameters["end_date"],
            db=mock_db_session
        )
        second_call_time = time.time() - start_time
        
        # Assertions
        assert second_call_time < first_call_time, "Cache should improve performance"
        assert statistics1 == statistics2, "Cached results should be identical"
        
        cache_hit_rate = optimizer._calculate_cache_hit_rate()
        assert cache_hit_rate > 0, "Should have cache hits"
        
        print(f"✅ Cache performance:")
        print(f"   First call (miss): {first_call_time:.3f}s")
        print(f"   Second call (hit): {second_call_time:.3f}s")
        print(f"   Cache hit rate: {cache_hit_rate:.1f}%")
        print(f"   Performance improvement: {((first_call_time - second_call_time) / first_call_time * 100):.1f}%")
    
    @pytest.mark.asyncio
    async def test_concurrent_report_generation(self, optimizer, mock_db_session, test_parameters):
        """Test concurrent report generation performance"""
        
        async def generate_report():
            report, metrics = await optimizer.generate_optimized_compliance_report(
                db=mock_db_session,
                include_recommendations=True,
                **test_parameters
            )
            return metrics.total_time
        
        # Generate multiple reports concurrently
        start_time = time.time()
        
        tasks = [generate_report() for _ in range(3)]
        generation_times = await asyncio.gather(*tasks)
        
        total_concurrent_time = time.time() - start_time
        
        # Assertions
        assert all(t < 30.0 for t in generation_times), "All reports should meet 30s target"
        assert total_concurrent_time < 45.0, "Concurrent generation should be efficient"
        
        avg_time = statistics.mean(generation_times)
        max_time = max(generation_times)
        
        print(f"✅ Concurrent generation performance:")
        print(f"   Total time for 3 reports: {total_concurrent_time:.2f}s")
        print(f"   Average per report: {avg_time:.2f}s")
        print(f"   Maximum time: {max_time:.2f}s")
        print(f"   All reports < 30s: {all(t < 30.0 for t in generation_times)}")
    
    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self, optimizer, mock_db_session, test_parameters):
        """Test memory usage during report generation"""
        
        initial_memory = optimizer._get_memory_usage()
        
        report, performance_metrics = await optimizer.generate_optimized_compliance_report(
            db=mock_db_session,
            include_recommendations=True,
            **test_parameters
        )
        
        final_memory = optimizer._get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        # Assertions
        assert performance_metrics.memory_usage_mb < 512, "Memory usage should be under limit"
        assert memory_increase < 100, "Memory increase should be reasonable"
        
        print(f"✅ Memory usage optimization:")
        print(f"   Initial memory: {initial_memory:.1f} MB")
        print(f"   Final memory: {final_memory:.1f} MB")
        print(f"   Memory increase: {memory_increase:.1f} MB")
        print(f"   Peak usage: {performance_metrics.memory_usage_mb:.1f} MB")
    
    def test_optimization_config_validation(self):
        """Test optimization configuration validation"""
        
        # Valid config
        config = OptimizationConfig(
            enable_parallel_processing=True,
            enable_caching=True,
            max_workers=4,
            cache_ttl_seconds=300
        )
        
        optimizer = ComplianceReportPerformanceOptimizer(config)
        
        assert optimizer.config.enable_parallel_processing is True
        assert optimizer.config.enable_caching is True
        assert optimizer.config.max_workers == 4
        assert optimizer.config.cache_ttl_seconds == 300
        
        print("✅ Optimization configuration validation passed")
    
    @pytest.mark.asyncio
    async def test_query_optimization_performance(self, optimizer, mock_db_session, test_parameters):
        """Test optimized SQL query performance"""
        
        # Test with query optimization enabled
        optimizer.config.enable_query_optimization = True
        
        start_time = time.time()
        audit_stats = optimizer._execute_audit_summary_query(
            tenant_id=test_parameters["tenant_id"],
            start_date=test_parameters["start_date"],
            end_date=test_parameters["end_date"],
            db=mock_db_session
        )
        optimized_time = time.time() - start_time
        
        # Test with query optimization disabled
        optimizer.config.enable_query_optimization = False
        
        start_time = time.time()
        audit_stats_fallback = optimizer._execute_audit_summary_query(
            tenant_id=test_parameters["tenant_id"],
            start_date=test_parameters["start_date"],
            end_date=test_parameters["end_date"],
            db=mock_db_session
        )
        fallback_time = time.time() - start_time
        
        # Assertions
        assert audit_stats is not None
        assert audit_stats_fallback is not None
        assert optimized_time < 1.0, "Optimized query should be fast"
        
        print(f"✅ Query optimization performance:")
        print(f"   Optimized query: {optimized_time:.3f}s")
        print(f"   Fallback query: {fallback_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_performance_degradation_handling(self, optimizer, mock_db_session, test_parameters):
        """Test handling of performance degradation scenarios"""
        
        # Simulate slow database
        def slow_execute(*args, **kwargs):
            time.sleep(0.1)  # Simulate 100ms delay
            mock_result = Mock()
            mock_result.total_events = 1000
            mock_result.fetchall.return_value = [mock_result]
            mock_result.fetchone.return_value = mock_result
            return mock_result
        
        mock_db_session.execute.side_effect = slow_execute
        
        start_time = time.time()
        
        report, performance_metrics = await optimizer.generate_optimized_compliance_report(
            db=mock_db_session,
            include_recommendations=True,
            **test_parameters
        )
        
        total_time = time.time() - start_time
        
        # Even with slow database, should still meet target due to optimizations
        assert total_time < 35.0, "Should handle performance degradation gracefully"
        assert report is not None
        
        print(f"✅ Performance degradation handling:")
        print(f"   Generation time with slow DB: {total_time:.2f}s")
        print(f"   Still within acceptable range: {total_time < 35.0}")
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_performance(self, optimizer):
        """Test cache cleanup performance"""
        
        # Fill cache with test data
        for i in range(100):
            cache_key = f"test_key_{i}"
            optimizer.query_cache[cache_key] = {
                "data": {"test": f"data_{i}"},
                "timestamp": time.time() - (i * 10)  # Varying ages
            }
        
        initial_cache_size = len(optimizer.query_cache)
        
        # Set short TTL for testing
        optimizer.config.cache_ttl_seconds = 50
        
        start_time = time.time()
        optimizer._cleanup_cache()
        cleanup_time = time.time() - start_time
        
        final_cache_size = len(optimizer.query_cache)
        
        # Assertions
        assert cleanup_time < 0.1, "Cache cleanup should be fast"
        assert final_cache_size < initial_cache_size, "Should remove expired entries"
        
        print(f"✅ Cache cleanup performance:")
        print(f"   Cleanup time: {cleanup_time:.3f}s")
        print(f"   Initial cache size: {initial_cache_size}")
        print(f"   Final cache size: {final_cache_size}")
        print(f"   Entries cleaned: {initial_cache_size - final_cache_size}")
    
    def test_performance_summary_generation(self, optimizer):
        """Test performance summary generation"""
        
        summary = optimizer.get_performance_summary()
        
        # Assertions
        assert "config" in summary
        assert "cache_stats" in summary
        assert "optimization_features" in summary
        
        assert "parallel_processing" in summary["config"]
        assert "caching" in summary["config"]
        assert "query_optimization" in summary["config"]
        
        assert "hit_rate" in summary["cache_stats"]
        assert "total_hits" in summary["cache_stats"]
        assert "total_misses" in summary["cache_stats"]
        
        assert len(summary["optimization_features"]) > 0
        
        print("✅ Performance summary generation:")
        print(f"   Config keys: {list(summary['config'].keys())}")
        print(f"   Cache stats keys: {list(summary['cache_stats'].keys())}")
        print(f"   Optimization features: {len(summary['optimization_features'])}")
    
    @pytest.mark.asyncio
    async def test_end_to_end_performance_target(self, optimizer, mock_db_session, test_parameters):
        """End-to-end test of 30-second performance target"""
        
        print("\n🎯 End-to-End Performance Target Test")
        print("=" * 50)
        
        # Run multiple iterations to ensure consistency
        times = []
        
        for i in range(5):
            start_time = time.time()
            
            report, performance_metrics = await optimizer.generate_optimized_compliance_report(
                db=mock_db_session,
                include_recommendations=True,
                **test_parameters
            )
            
            total_time = time.time() - start_time
            times.append(total_time)
            
            print(f"Iteration {i+1}: {total_time:.2f}s")
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        success_rate = (sum(1 for t in times if t < 30.0) / len(times)) * 100
        
        # Assertions
        assert avg_time < 30.0, f"Average time {avg_time:.2f}s exceeds 30s target"
        assert success_rate >= 80.0, f"Success rate {success_rate:.1f}% below 80% threshold"
        assert max_time < 45.0, f"Maximum time {max_time:.2f}s too high"
        
        print("\n📊 Performance Summary:")
        print(f"   Average time: {avg_time:.2f}s")
        print(f"   Minimum time: {min_time:.2f}s")
        print(f"   Maximum time: {max_time:.2f}s")
        print(f"   Success rate (< 30s): {success_rate:.1f}%")
        print(f"   Target met: {'✅ YES' if avg_time < 30.0 else '❌ NO'}")
        
        # Performance grade
        if avg_time < 15.0:
            grade = "A"
        elif avg_time < 20.0:
            grade = "B"
        elif avg_time < 30.0:
            grade = "C"
        else:
            grade = "F"
        
        print(f"   Performance grade: {grade}")
        
        return {
            "average_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "success_rate": success_rate,
            "grade": grade,
            "target_met": avg_time < 30.0
        }


# Integration test
@pytest.mark.asyncio
async def test_compliance_performance_integration():
    """Integration test for compliance performance optimization"""
    
    print("\n🔧 Compliance Performance Integration Test")
    print("=" * 50)
    
    # Create optimizer
    config = OptimizationConfig(
        enable_parallel_processing=True,
        enable_caching=True,
        enable_query_optimization=True,
        max_workers=4
    )
    
    optimizer = ComplianceReportPerformanceOptimizer(config)
    
    # Mock database session
    mock_db = Mock()
    mock_result = Mock()
    mock_result.total_events = 5000
    mock_result.high_risk_events = 250
    mock_result.failed_logins = 50
    mock_result.active_users = 500
    mock_result.action = "LOGIN"
    mock_result.action_count = 2500
    mock_result.security_events = 125
    mock_result.threat_events = 25
    mock_result.unique_ips = 250
    mock_result.export_events = 100
    mock_result.delete_events = 25
    mock_result.desensitization_events = 75
    mock_result.permission_checks = 10000
    mock_result.role_assignments = 250
    mock_result.permission_violations = 50
    
    mock_db.execute.return_value.fetchall.return_value = [mock_result]
    mock_db.execute.return_value.fetchone.return_value = mock_result
    
    # Test parameters
    test_params = {
        "tenant_id": "integration_test_tenant",
        "standard": ComplianceStandard.GDPR,
        "report_type": ReportType.COMPREHENSIVE,
        "start_date": datetime.utcnow() - timedelta(days=90),
        "end_date": datetime.utcnow(),
        "generated_by": uuid4()
    }
    
    # Generate report
    start_time = time.time()
    
    report, performance_metrics = await optimizer.generate_optimized_compliance_report(
        db=mock_db,
        include_recommendations=True,
        **test_params
    )
    
    total_time = time.time() - start_time
    
    # Validate results
    assert total_time < 30.0, f"Integration test failed: {total_time:.2f}s > 30s"
    assert report is not None
    assert len(report.metrics) > 0
    assert report.overall_compliance_score >= 0
    
    print(f"✅ Integration test passed:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Metrics generated: {len(report.metrics)}")
    print(f"   Violations detected: {len(report.violations)}")
    print(f"   Compliance score: {report.overall_compliance_score:.1f}%")
    print(f"   Cache hit rate: {performance_metrics.cache_hit_rate:.1f}%")
    print(f"   Memory usage: {performance_metrics.memory_usage_mb:.1f} MB")
    
    return True


if __name__ == "__main__":
    # Run integration test
    asyncio.run(test_compliance_performance_integration())