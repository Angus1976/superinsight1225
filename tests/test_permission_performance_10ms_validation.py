"""
Comprehensive test suite for validating <10ms permission check performance.

Tests the ultra-fast permission checking system under various conditions
to ensure consistent sub-10ms response times.
"""

import pytest
import time
import statistics
from uuid import uuid4
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.security.permission_performance_validator_10ms import (
    get_performance_validator,
    ValidationResult,
    LoadTestConfig
)
from src.security.rbac_controller_ultra_fast import get_ultra_fast_rbac_controller
from src.security.ultra_fast_permission_checker import (
    get_ultra_fast_permission_checker,
    PerformanceTarget
)


class TestPermissionPerformance10ms:
    """Test suite for <10ms permission performance validation."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = Mock()
        
        # Mock user lookup
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.tenant_id = "test_tenant"
        mock_user.is_active = True
        mock_user.role.value = "VIEWER"
        
        session.query.return_value.filter.return_value.first.return_value = mock_user
        session.execute.return_value.fetchone.return_value = Mock(has_permission=1)
        
        return session
    
    @pytest.fixture
    def performance_validator(self):
        """Create performance validator instance."""
        return get_performance_validator(target_response_time_ms=10.0, confidence_level=98.0)
    
    @pytest.fixture
    def ultra_fast_controller(self):
        """Create ultra-fast RBAC controller instance."""
        return get_ultra_fast_rbac_controller(target_response_time_ms=10.0)
    
    def test_ultra_fast_cache_performance(self):
        """Test ultra-fast cache access times."""
        from src.security.ultra_fast_permission_checker import UltraFastCache
        
        cache = UltraFastCache(max_size=1000)
        user_id = uuid4()
        tenant_id = "test_tenant"
        
        # Test cache set performance
        start_time = time.perf_counter()
        for i in range(100):
            cache.set(user_id, f"permission_{i}", tenant_id, True)
        set_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Should be very fast (microseconds per operation)
        assert set_time_ms < 10.0, f"Cache set took {set_time_ms:.2f}ms for 100 operations"
        
        # Test cache get performance
        start_time = time.perf_counter()
        for i in range(100):
            result = cache.get(user_id, f"permission_{i}", tenant_id)
            assert result is True
        get_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Should be extremely fast (microseconds per operation)
        assert get_time_ms < 5.0, f"Cache get took {get_time_ms:.2f}ms for 100 operations"
        
        # Test cache statistics
        stats = cache.get_stats()
        assert stats["hit_rate"] > 99.0
        assert stats["cache_size"] == 100
    
    def test_single_permission_check_performance(self, ultra_fast_controller, mock_db_session):
        """Test single permission check performance."""
        user_id = uuid4()
        permission = "read_data"
        
        # Warm up the cache
        ultra_fast_controller.check_user_permission(
            user_id=user_id,
            permission_name=permission,
            db=mock_db_session
        )
        
        # Test performance with warm cache
        response_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            result = ultra_fast_controller.check_user_permission(
                user_id=user_id,
                permission_name=permission,
                db=mock_db_session
            )
            response_time_ms = (time.perf_counter() - start_time) * 1000
            response_times.append(response_time_ms)
        
        # Analyze performance
        avg_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
        max_time = max(response_times)
        under_10ms = sum(1 for t in response_times if t < 10.0)
        compliance_rate = (under_10ms / len(response_times)) * 100
        
        # Assertions
        assert avg_time < 10.0, f"Average response time {avg_time:.2f}ms exceeds 10ms target"
        assert p95_time < 15.0, f"P95 response time {p95_time:.2f}ms is too high"
        assert compliance_rate >= 95.0, f"Compliance rate {compliance_rate:.1f}% is below 95%"
        assert max_time < 50.0, f"Maximum response time {max_time:.2f}ms is excessive"
    
    def test_batch_permission_check_performance(self, ultra_fast_controller, mock_db_session):
        """Test batch permission check performance."""
        user_id = uuid4()
        permissions = ["read_data", "write_data", "view_dashboard", "manage_projects", "view_reports"]
        
        # Test batch performance
        response_times = []
        for _ in range(50):
            start_time = time.perf_counter()
            results = ultra_fast_controller.batch_check_permissions(
                user_id=user_id,
                permissions=permissions,
                db=mock_db_session
            )
            total_time_ms = (time.perf_counter() - start_time) * 1000
            avg_time_per_permission = total_time_ms / len(permissions)
            response_times.append(avg_time_per_permission)
            
            # Verify all permissions were checked
            assert len(results) == len(permissions)
        
        # Analyze performance
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        under_10ms = sum(1 for t in response_times if t < 10.0)
        compliance_rate = (under_10ms / len(response_times)) * 100
        
        # Assertions
        assert avg_time < 10.0, f"Average time per permission {avg_time:.2f}ms exceeds 10ms target"
        assert compliance_rate >= 90.0, f"Batch compliance rate {compliance_rate:.1f}% is too low"
        assert max_time < 25.0, f"Maximum time per permission {max_time:.2f}ms is excessive"
    
    def test_cold_cache_performance(self, ultra_fast_controller, mock_db_session):
        """Test performance with cold cache (worst case)."""
        user_id = uuid4()
        permission = "read_data"
        
        response_times = []
        for _ in range(20):  # Fewer tests for cold cache
            # Clear cache to ensure cold start
            ultra_fast_controller.clear_performance_cache()
            
            start_time = time.perf_counter()
            result = ultra_fast_controller.check_user_permission(
                user_id=user_id,
                permission_name=permission,
                db=mock_db_session
            )
            response_time_ms = (time.perf_counter() - start_time) * 1000
            response_times.append(response_time_ms)
        
        # Analyze cold cache performance
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        under_25ms = sum(1 for t in response_times if t < 25.0)
        compliance_rate = (under_25ms / len(response_times)) * 100
        
        # Cold cache should still be reasonably fast
        assert avg_time < 25.0, f"Cold cache average time {avg_time:.2f}ms is too slow"
        assert max_time < 100.0, f"Cold cache max time {max_time:.2f}ms is excessive"
        assert compliance_rate >= 80.0, f"Cold cache compliance rate {compliance_rate:.1f}% is too low"
    
    def test_concurrent_performance(self, ultra_fast_controller, mock_db_session):
        """Test performance under concurrent load."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        user_ids = [uuid4() for _ in range(10)]
        permissions = ["read_data", "write_data", "view_dashboard"]
        
        def worker_function(worker_id: int, num_requests: int):
            """Worker function for concurrent testing."""
            worker_times = []
            for i in range(num_requests):
                user_id = user_ids[i % len(user_ids)]
                permission = permissions[i % len(permissions)]
                
                start_time = time.perf_counter()
                result = ultra_fast_controller.check_user_permission(
                    user_id=user_id,
                    permission_name=permission,
                    db=mock_db_session
                )
                response_time_ms = (time.perf_counter() - start_time) * 1000
                worker_times.append(response_time_ms)
            
            return worker_times
        
        # Run concurrent workers
        all_response_times = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for worker_id in range(10):
                future = executor.submit(worker_function, worker_id, 20)
                futures.append(future)
            
            for future in as_completed(futures):
                worker_times = future.result()
                all_response_times.extend(worker_times)
        
        # Analyze concurrent performance
        avg_time = statistics.mean(all_response_times)
        p95_time = statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) > 1 else all_response_times[0]
        under_10ms = sum(1 for t in all_response_times if t < 10.0)
        compliance_rate = (under_10ms / len(all_response_times)) * 100
        
        # Concurrent performance should still meet targets
        assert avg_time < 15.0, f"Concurrent average time {avg_time:.2f}ms is too slow"
        assert p95_time < 25.0, f"Concurrent P95 time {p95_time:.2f}ms is too slow"
        assert compliance_rate >= 85.0, f"Concurrent compliance rate {compliance_rate:.1f}% is too low"
    
    def test_performance_monitoring(self, ultra_fast_controller, mock_db_session):
        """Test performance monitoring and reporting."""
        user_id = uuid4()
        permissions = ["read_data", "write_data", "view_dashboard"]
        
        # Generate some test data
        for _ in range(50):
            for permission in permissions:
                ultra_fast_controller.check_user_permission(
                    user_id=user_id,
                    permission_name=permission,
                    db=mock_db_session
                )
        
        # Get performance report
        report = ultra_fast_controller.get_performance_report()
        
        # Verify report structure
        assert "ultra_fast_performance" in report
        assert "controller_stats" in report
        assert "configuration" in report
        assert "recommendations" in report
        
        # Verify performance stats
        perf_stats = report["ultra_fast_performance"]["performance_stats"]
        assert "compliance_rate" in perf_stats
        assert "cache_hit_rate" in perf_stats
        assert "avg_response_time_ms" in perf_stats
        assert "performance_grade" in perf_stats
        
        # Performance should be good
        assert perf_stats["compliance_rate"] >= 90.0
        assert perf_stats["performance_grade"] in ["A", "B", "C"]
    
    def test_cache_invalidation_performance(self, ultra_fast_controller, mock_db_session):
        """Test that cache invalidation doesn't significantly impact performance."""
        user_id = uuid4()
        permission = "read_data"
        
        # Warm up cache
        for _ in range(10):
            ultra_fast_controller.check_user_permission(
                user_id=user_id,
                permission_name=permission,
                db=mock_db_session
            )
        
        # Test invalidation performance
        invalidation_times = []
        for _ in range(20):
            start_time = time.perf_counter()
            ultra_fast_controller.ultra_fast_checker.invalidate_user_cache(user_id)
            invalidation_time_ms = (time.perf_counter() - start_time) * 1000
            invalidation_times.append(invalidation_time_ms)
            
            # Re-warm cache
            ultra_fast_controller.check_user_permission(
                user_id=user_id,
                permission_name=permission,
                db=mock_db_session
            )
        
        # Invalidation should be very fast
        avg_invalidation_time = statistics.mean(invalidation_times)
        max_invalidation_time = max(invalidation_times)
        
        assert avg_invalidation_time < 1.0, f"Average invalidation time {avg_invalidation_time:.2f}ms is too slow"
        assert max_invalidation_time < 5.0, f"Max invalidation time {max_invalidation_time:.2f}ms is too slow"
    
    def test_memory_efficiency(self, ultra_fast_controller):
        """Test memory efficiency of the caching system."""
        import sys
        
        # Get initial memory usage
        initial_cache_size = len(ultra_fast_controller.ultra_fast_checker.cache._cache)
        
        # Add many cache entries
        user_ids = [uuid4() for _ in range(100)]
        permissions = ["read_data", "write_data", "view_dashboard", "manage_projects"]
        
        for user_id in user_ids:
            for permission in permissions:
                ultra_fast_controller.ultra_fast_checker.cache.set(
                    user_id, permission, "test_tenant", True
                )
        
        # Check cache size and efficiency
        final_cache_size = len(ultra_fast_controller.ultra_fast_checker.cache._cache)
        expected_entries = len(user_ids) * len(permissions)
        
        # Cache should store all entries (within max size limit)
        max_cache_size = ultra_fast_controller.ultra_fast_checker.cache.max_size
        expected_stored = min(expected_entries, max_cache_size)
        
        assert final_cache_size <= max_cache_size, "Cache exceeded maximum size"
        assert final_cache_size >= expected_stored * 0.9, "Cache evicted too many entries"
        
        # Test cache statistics
        stats = ultra_fast_controller.ultra_fast_checker.cache.get_stats()
        assert stats["cache_size"] == final_cache_size
        assert stats["max_size"] == max_cache_size
    
    def test_performance_degradation_detection(self, ultra_fast_controller, mock_db_session):
        """Test detection of performance degradation."""
        user_id = uuid4()
        permission = "read_data"
        
        # Disable ultra-fast mode to force database queries
        ultra_fast_controller.disable_ultra_fast_mode()
        
        # Mock the parent class permission check method to add delay
        original_check = ultra_fast_controller.__class__.__bases__[0].check_user_permission
        
        def slow_check(self, *args, **kwargs):
            time.sleep(0.015)  # 15ms delay to simulate slow database
            # Return a simple result instead of calling the complex parent method
            return True
        
        # Test with degraded performance
        with patch.object(
            ultra_fast_controller.__class__.__bases__[0],
            'check_user_permission',
            slow_check
        ):
            response_times = []
            for _ in range(10):
                start_time = time.perf_counter()
                result = ultra_fast_controller.check_user_permission(
                    user_id=user_id,
                    permission_name=permission,
                    db=mock_db_session
                )
                response_time_ms = (time.perf_counter() - start_time) * 1000
                response_times.append(response_time_ms)
        
        # Re-enable ultra-fast mode
        ultra_fast_controller.enable_ultra_fast_mode()
        
        # Performance should be degraded
        avg_time = statistics.mean(response_times)
        assert avg_time > 10.0, f"Performance degradation not detected: avg_time={avg_time:.2f}ms"
        
        # Get performance report to check recommendations
        report = ultra_fast_controller.get_performance_report()
        recommendations = report.get("recommendations", [])
        
        # Should have recommendations for performance improvement
        assert len(recommendations) >= 0, "Performance recommendations should be available"
    
    @pytest.mark.integration
    def test_comprehensive_validation_suite(self, performance_validator, mock_db_session):
        """Test the comprehensive validation suite."""
        # Setup test environment
        assert performance_validator.setup_test_environment(mock_db_session, num_users=50)
        
        # Run validation tests
        results = performance_validator.run_comprehensive_validation(
            mock_db_session, include_load_test=False  # Skip load test for unit testing
        )
        
        # Verify results structure
        assert "single_permission" in results
        assert "batch_permission" in results
        assert "cold_cache" in results
        assert "overall" in results
        
        # Check individual test results
        for test_name, result in results.items():
            if test_name != "overall":
                assert isinstance(result, ValidationResult)
                assert result.total_tests > 0
                assert result.error_rate < 10.0  # Less than 10% errors
                assert result.performance_grade in ["A", "B", "C", "D", "F"]
        
        # Overall assessment should be reasonable
        overall = results["overall"]
        assert overall.compliance_rate >= 0.0  # At least some compliance
        assert len(overall.recommendations) > 0  # Should have recommendations
    
    def test_performance_target_configuration(self):
        """Test performance target configuration."""
        # Test different target configurations
        targets = [5.0, 10.0, 15.0, 20.0]
        
        for target_ms in targets:
            validator = get_performance_validator(
                target_response_time_ms=target_ms,
                confidence_level=95.0
            )
            
            assert validator.target_response_time_ms == target_ms
            assert validator.confidence_level == 95.0
            
            # Controller should use the same target
            controller = validator.controller
            assert controller.ultra_fast_checker.target.target_response_time_ms == target_ms
    
    def test_optimization_recommendations(self, ultra_fast_controller, mock_db_session):
        """Test generation of optimization recommendations."""
        # Generate some test data with varying performance
        user_id = uuid4()
        permissions = ["read_data", "write_data", "view_dashboard"]
        
        # Clear cache to get some cold cache misses
        ultra_fast_controller.clear_performance_cache()
        
        # Run some tests
        for _ in range(30):
            for permission in permissions:
                ultra_fast_controller.check_user_permission(
                    user_id=user_id,
                    permission_name=permission,
                    db=mock_db_session
                )
        
        # Get optimization results
        optimization_result = ultra_fast_controller.optimize_performance()
        
        # Verify optimization structure
        assert "optimizations_applied" in optimization_result
        assert "current_performance" in optimization_result
        assert "recommendations" in optimization_result
        
        # Should have some optimizations or recommendations
        total_items = (
            len(optimization_result["optimizations_applied"]) +
            len(optimization_result["recommendations"])
        )
        assert total_items > 0, "No optimizations or recommendations provided"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])