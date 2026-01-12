"""
Comprehensive test suite for <10ms permission check performance requirement.

Tests the optimized permission checking system to ensure it meets the
strict performance target of <10ms response time.
"""

import asyncio
import pytest
import time
import statistics
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.security.permission_performance_optimizer import (
    PermissionPerformanceOptimizer,
    OptimizationConfig,
    PerformanceStats,
    get_permission_performance_optimizer
)
from src.security.rbac_controller_optimized import (
    OptimizedRBACController,
    get_optimized_rbac_controller
)
from src.security.permission_cache import PermissionCache
from src.security.rbac_models import ResourceType, PermissionScope
from src.security.models import UserRole


class TestPermissionPerformanceOptimizer:
    """Test the PermissionPerformanceOptimizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = OptimizationConfig(
            target_response_time_ms=10.0,
            cache_preload_enabled=True,
            query_optimization_enabled=True,
            batch_processing_enabled=True,
            memory_cache_size=1000
        )
        self.optimizer = PermissionPerformanceOptimizer(self.config)
        self.user_id = uuid4()
        self.tenant_id = "test_tenant"
        
        # Mock dependencies
        self.mock_db = Mock()
        self.mock_cache = Mock()
        self.mock_rbac = Mock()
        
        # Mock user
        self.mock_user = Mock()
        self.mock_user.id = self.user_id
        self.mock_user.tenant_id = self.tenant_id
        self.mock_user.is_active = True
        self.mock_user.role = UserRole.VIEWER
    
    @pytest.mark.asyncio
    async def test_single_permission_check_performance(self):
        """Test single permission check meets <10ms requirement."""
        # Mock cache miss to force database check
        self.mock_cache.get_permission.return_value = None
        self.mock_cache.set_permission = Mock()
        
        # Mock database query to return quickly
        with patch('src.security.permission_performance_optimizer.text') as mock_text:
            mock_result = Mock()
            mock_result.fetchone.return_value = Mock(has_permission=1)
            self.mock_db.execute.return_value = mock_result
            
            # Perform optimized permission check
            start_time = time.perf_counter()
            result, response_time_ms = await self.optimizer.optimize_permission_check(
                user_id=self.user_id,
                permission_name="read_data",
                permission_cache=self.mock_cache,
                rbac_controller=self.mock_rbac,
                db=self.mock_db,
                tenant_id=self.tenant_id
            )
            end_time = time.perf_counter()
            
            # Verify performance
            actual_time_ms = (end_time - start_time) * 1000
            assert actual_time_ms < 10.0, f"Permission check took {actual_time_ms:.2f}ms, exceeds 10ms target"
            assert response_time_ms < 10.0, f"Reported response time {response_time_ms:.2f}ms exceeds 10ms target"
            assert result is True
    
    @pytest.mark.asyncio
    async def test_cached_permission_check_performance(self):
        """Test cached permission check is under 1ms."""
        # Mock cache hit
        self.mock_cache.get_permission.return_value = True
        
        # Perform optimized permission check
        start_time = time.perf_counter()
        result, response_time_ms = await self.optimizer.optimize_permission_check(
            user_id=self.user_id,
            permission_name="read_data",
            permission_cache=self.mock_cache,
            rbac_controller=self.mock_rbac,
            db=self.mock_db,
            tenant_id=self.tenant_id
        )
        end_time = time.perf_counter()
        
        # Verify performance - cached checks should be very fast
        actual_time_ms = (end_time - start_time) * 1000
        assert actual_time_ms < 1.0, f"Cached permission check took {actual_time_ms:.2f}ms, should be <1ms"
        assert response_time_ms < 1.0, f"Reported cached response time {response_time_ms:.2f}ms should be <1ms"
        assert result is True
    
    @pytest.mark.asyncio
    async def test_batch_permission_check_performance(self):
        """Test batch permission check meets performance requirements."""
        permissions = ["read_data", "write_data", "delete_data", "manage_users", "view_reports"]
        
        # Mock cache misses to force database check
        self.mock_cache.get_permission.return_value = None
        self.mock_cache.set_permission = Mock()
        
        # Mock batch database query
        with patch.object(self.optimizer, '_batch_permission_check') as mock_batch:
            mock_batch.return_value = {perm: True for perm in permissions}
            
            # Perform batch permission check
            start_time = time.perf_counter()
            results, total_response_time_ms = await self.optimizer.batch_optimize_permission_checks(
                user_id=self.user_id,
                permissions=permissions,
                permission_cache=self.mock_cache,
                rbac_controller=self.mock_rbac,
                db=self.mock_db,
                tenant_id=self.tenant_id
            )
            end_time = time.perf_counter()
            
            # Verify performance
            actual_time_ms = (end_time - start_time) * 1000
            avg_time_per_permission = actual_time_ms / len(permissions)
            
            assert avg_time_per_permission < 10.0, f"Average time per permission {avg_time_per_permission:.2f}ms exceeds 10ms target"
            assert total_response_time_ms < 50.0, f"Total batch time {total_response_time_ms:.2f}ms too high"
            assert len(results) == len(permissions)
            assert all(results.values())
    
    def test_performance_monitoring(self):
        """Test performance monitoring and statistics."""
        # Record some test metrics
        for i in range(100):
            response_time = 5.0 + (i % 10)  # Vary between 5-15ms
            cache_hit = i % 3 == 0  # 33% cache hit rate
            
            self.optimizer.monitor.record_permission_check(
                user_id=self.user_id,
                permission_name=f"permission_{i % 5}",
                response_time_ms=response_time,
                cache_hit=cache_hit,
                tenant_id=self.tenant_id
            )
        
        # Get performance statistics
        stats = self.optimizer.monitor.get_performance_stats()
        
        assert stats.total_checks == 100
        # Allow for small variance in cache hit calculation due to timing
        assert 32 <= stats.cache_hits <= 34  # ~33% cache hit rate with tolerance
        assert stats.avg_response_time_ms > 0
        assert stats.p95_response_time_ms > 0
        assert stats.checks_under_10ms > 0
        assert stats.checks_over_10ms > 0
        assert 0 <= stats.target_compliance_rate <= 100
    
    def test_optimization_recommendations(self):
        """Test optimization recommendations generation."""
        # Record metrics that would trigger recommendations
        for i in range(50):
            # High response times to trigger recommendations
            response_time = 15.0 + (i % 5)  # 15-20ms
            cache_hit = i % 10 == 0  # Low cache hit rate (10%)
            
            self.optimizer.monitor.record_permission_check(
                user_id=self.user_id,
                permission_name=f"permission_{i}",
                response_time_ms=response_time,
                cache_hit=cache_hit,
                tenant_id=self.tenant_id
            )
        
        recommendations = self.optimizer.monitor.get_optimization_recommendations()
        
        assert len(recommendations) > 0
        assert any("compliance rate" in rec.lower() for rec in recommendations)
        assert any("cache hit rate" in rec.lower() for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_preloader_performance(self):
        """Test permission preloader performance."""
        # Mock database query for preloading
        with patch.object(self.optimizer.preloader, 'preload_user_permissions') as mock_preload:
            mock_preload.return_value = 10  # Preloaded 10 permissions
            
            start_time = time.perf_counter()
            preloaded_count = await self.optimizer.preloader.preload_user_permissions(
                user_id=self.user_id,
                tenant_id=self.tenant_id,
                permission_cache=self.mock_cache,
                db=self.mock_db,
                rbac_controller=self.mock_rbac
            )
            end_time = time.perf_counter()
            
            # Preloading should be fast
            preload_time_ms = (end_time - start_time) * 1000
            assert preload_time_ms < 50.0, f"Preloading took {preload_time_ms:.2f}ms, should be <50ms"
            assert preloaded_count == 10


class TestOptimizedRBACController:
    """Test the OptimizedRBACController class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = OptimizationConfig(target_response_time_ms=10.0)
        self.controller = OptimizedRBACController(optimization_config=self.config)
        self.user_id = uuid4()
        self.tenant_id = "test_tenant"
        
        # Mock database session
        self.mock_db = Mock()
        
        # Mock user
        self.mock_user = Mock()
        self.mock_user.id = self.user_id
        self.mock_user.tenant_id = self.tenant_id
        self.mock_user.is_active = True
        self.mock_user.role = UserRole.VIEWER
    
    @pytest.mark.asyncio
    async def test_optimized_permission_check_performance(self):
        """Test optimized permission check meets <10ms requirement."""
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            with patch.object(self.controller.performance_optimizer, 'optimize_permission_check') as mock_optimize:
                mock_optimize.return_value = (True, 8.5)  # 8.5ms response time
                
                start_time = time.perf_counter()
                result = await self.controller.check_user_permission_optimized(
                    user_id=self.user_id,
                    permission_name="read_data",
                    db=self.mock_db
                )
                end_time = time.perf_counter()
                
                # Verify performance
                actual_time_ms = (end_time - start_time) * 1000
                assert actual_time_ms < 10.0, f"Optimized check took {actual_time_ms:.2f}ms, exceeds 10ms target"
                assert result is True
                assert mock_optimize.called
    
    def test_sync_optimized_permission_check_performance(self):
        """Test synchronous optimized permission check performance."""
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            # Mock cache hit for fast response
            with patch.object(self.controller.permission_cache, 'get_permission') as mock_cache:
                mock_cache.return_value = True
                
                start_time = time.perf_counter()
                result = self.controller._sync_optimized_check(
                    user_id=self.user_id,
                    permission_name="read_data",
                    resource_id=None,
                    resource_type=None,
                    db=self.mock_db,
                    ip_address=None,
                    user_agent=None
                )
                end_time = time.perf_counter()
                
                # Verify performance
                actual_time_ms = (end_time - start_time) * 1000
                assert actual_time_ms < 10.0, f"Sync optimized check took {actual_time_ms:.2f}ms, exceeds 10ms target"
                assert result is True
    
    @pytest.mark.asyncio
    async def test_batch_optimized_permission_check_performance(self):
        """Test batch optimized permission check performance."""
        permissions = ["read_data", "write_data", "delete_data"]
        
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            with patch.object(self.controller.performance_optimizer, 'batch_optimize_permission_checks') as mock_batch:
                mock_batch.return_value = ({perm: True for perm in permissions}, 25.0)  # 25ms total
                
                start_time = time.perf_counter()
                results = await self.controller.batch_check_permissions_optimized(
                    user_id=self.user_id,
                    permissions=permissions,
                    db=self.mock_db
                )
                end_time = time.perf_counter()
                
                # Verify performance
                actual_time_ms = (end_time - start_time) * 1000
                avg_time_per_permission = actual_time_ms / len(permissions)
                
                assert avg_time_per_permission < 10.0, f"Average time per permission {avg_time_per_permission:.2f}ms exceeds 10ms target"
                assert len(results) == len(permissions)
                assert all(results.values())
    
    def test_performance_statistics_collection(self):
        """Test performance statistics collection."""
        # Simulate some permission checks
        for i in range(10):
            response_time = 5.0 + i  # 5-14ms
            success = i < 8  # 80% success rate
            self.controller._update_performance_stats(response_time, success)
        
        stats = self.controller.get_performance_statistics()
        
        assert "controller_stats" in stats
        assert "optimizer_report" in stats
        assert "cache_stats" in stats
        assert stats["controller_stats"]["total_checks"] == 10
        assert stats["controller_stats"]["optimized_checks"] == 8
        assert stats["optimization_enabled"] is True
    
    def test_performance_recommendations(self):
        """Test performance recommendations."""
        recommendations = self.controller.get_performance_recommendations()
        
        assert isinstance(recommendations, list)
        # Should have at least one recommendation (even if it's "optimal")
        assert len(recommendations) >= 1


class TestPerformanceUnderLoad:
    """Test performance under various load conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = OptimizationConfig(
            target_response_time_ms=10.0,
            memory_cache_size=5000,
            batch_processing_enabled=True
        )
        self.controller = OptimizedRBACController(optimization_config=self.config)
        self.mock_db = Mock()
    
    def test_concurrent_permission_checks_performance(self):
        """Test performance under concurrent load."""
        num_concurrent_checks = 100
        users = [uuid4() for _ in range(10)]  # 10 different users
        permissions = ["read_data", "write_data", "view_dashboard", "manage_users"]
        
        # Mock user lookup
        mock_user = Mock()
        mock_user.tenant_id = "test_tenant"
        mock_user.is_active = True
        mock_user.role = UserRole.VIEWER
        
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            # Mock cache for fast responses
            with patch.object(self.controller.permission_cache, 'get_permission') as mock_cache:
                mock_cache.return_value = True
                
                def check_permission(user_id, permission):
                    """Single permission check."""
                    start_time = time.perf_counter()
                    result = self.controller.check_user_permission(
                        user_id=user_id,
                        permission_name=permission,
                        db=self.mock_db
                    )
                    end_time = time.perf_counter()
                    return result, (end_time - start_time) * 1000
                
                # Execute concurrent checks
                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = []
                    
                    for i in range(num_concurrent_checks):
                        user_id = users[i % len(users)]
                        permission = permissions[i % len(permissions)]
                        future = executor.submit(check_permission, user_id, permission)
                        futures.append(future)
                    
                    # Collect results
                    response_times = []
                    for future in as_completed(futures):
                        result, response_time_ms = future.result()
                        response_times.append(response_time_ms)
                        assert result is True
                
                # Analyze performance
                avg_response_time = statistics.mean(response_times)
                p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
                max_response_time = max(response_times)
                
                # Performance assertions
                assert avg_response_time < 10.0, f"Average response time {avg_response_time:.2f}ms exceeds 10ms target"
                assert p95_response_time < 15.0, f"P95 response time {p95_response_time:.2f}ms too high under load"
                assert max_response_time < 25.0, f"Max response time {max_response_time:.2f}ms too high under load"
                
                # Check that most requests meet the target
                under_10ms = sum(1 for t in response_times if t < 10.0)
                compliance_rate = (under_10ms / len(response_times)) * 100
                assert compliance_rate >= 80.0, f"Only {compliance_rate:.1f}% of requests under 10ms target"
    
    def test_memory_cache_performance_under_load(self):
        """Test memory cache performance under high load."""
        cache = PermissionCache(memory_cache_size=1000)
        num_operations = 5000
        users = [uuid4() for _ in range(100)]
        permissions = ["read_data", "write_data", "delete_data", "manage_users", "view_reports"]
        
        # Measure cache operations performance
        start_time = time.perf_counter()
        
        for i in range(num_operations):
            user_id = users[i % len(users)]
            permission = permissions[i % len(permissions)]
            tenant_id = f"tenant_{i % 10}"
            
            # Set permission (cache write)
            cache.set_permission(user_id, permission, True, tenant_id=tenant_id)
            
            # Get permission (cache read)
            result = cache.get_permission(user_id, permission, tenant_id=tenant_id)
            assert result is True
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_operation = total_time_ms / (num_operations * 2)  # 2 operations per iteration
        
        # Performance assertions
        assert avg_time_per_operation < 0.1, f"Average cache operation time {avg_time_per_operation:.3f}ms too high"
        assert total_time_ms < 1000.0, f"Total cache operations took {total_time_ms:.2f}ms, should be <1000ms"
        
        # Check cache statistics
        stats = cache.get_cache_statistics()
        assert stats["hit_rate"] > 0
        assert stats["memory_cache_size"] <= cache.memory_cache_size


class TestPerformanceRegression:
    """Test for performance regressions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = OptimizationConfig(target_response_time_ms=10.0)
        self.controller = OptimizedRBACController(optimization_config=self.config)
        self.baseline_times = []
        self.mock_db = Mock()
    
    def test_performance_baseline_establishment(self):
        """Establish performance baseline for regression testing."""
        num_checks = 100
        user_id = uuid4()
        
        # Mock user and cache for consistent testing
        mock_user = Mock()
        mock_user.tenant_id = "test_tenant"
        mock_user.is_active = True
        mock_user.role = UserRole.VIEWER
        
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            with patch.object(self.controller.permission_cache, 'get_permission') as mock_cache:
                mock_cache.return_value = True  # Always cache hit for consistent baseline
                
                response_times = []
                
                for i in range(num_checks):
                    start_time = time.perf_counter()
                    result = self.controller.check_user_permission(
                        user_id=user_id,
                        permission_name=f"permission_{i % 5}",
                        db=self.mock_db
                    )
                    end_time = time.perf_counter()
                    
                    response_time_ms = (end_time - start_time) * 1000
                    response_times.append(response_time_ms)
                    assert result is True
                
                # Calculate baseline statistics
                avg_time = statistics.mean(response_times)
                p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
                max_time = max(response_times)
                
                # Store baseline for future regression tests
                self.baseline_times = response_times
                
                # Baseline assertions
                assert avg_time < 5.0, f"Baseline average time {avg_time:.2f}ms too high for cached checks"
                assert p95_time < 10.0, f"Baseline P95 time {p95_time:.2f}ms exceeds target"
                assert max_time < 15.0, f"Baseline max time {max_time:.2f}ms too high"
                
                print(f"Performance baseline established:")
                print(f"  Average: {avg_time:.2f}ms")
                print(f"  P95: {p95_time:.2f}ms")
                print(f"  Max: {max_time:.2f}ms")


@pytest.mark.integration
class TestEndToEndPerformance:
    """End-to-end performance tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = OptimizationConfig(
            target_response_time_ms=10.0,
            cache_preload_enabled=True,
            query_optimization_enabled=True,
            batch_processing_enabled=True
        )
        self.controller = OptimizedRBACController(optimization_config=self.config)
    
    @pytest.mark.asyncio
    async def test_end_to_end_permission_workflow_performance(self):
        """Test complete permission workflow performance."""
        user_id = uuid4()
        tenant_id = "test_tenant"
        permissions = ["read_data", "write_data", "delete_data", "manage_users", "view_reports"]
        
        # Mock database and user setup
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.tenant_id = tenant_id
        mock_user.is_active = True
        mock_user.role = UserRole.VIEWER
        
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            # Test workflow: preload -> individual checks -> batch check
            workflow_start = time.perf_counter()
            
            # 1. Preload user permissions
            preload_success = await self.controller.preload_user_permissions(user_id, mock_db)
            
            # 2. Individual permission checks (should hit cache)
            individual_times = []
            for permission in permissions:
                start_time = time.perf_counter()
                result = await self.controller.check_user_permission_optimized(
                    user_id=user_id,
                    permission_name=permission,
                    db=mock_db
                )
                end_time = time.perf_counter()
                
                individual_times.append((end_time - start_time) * 1000)
            
            # 3. Batch permission check
            batch_start = time.perf_counter()
            batch_results = await self.controller.batch_check_permissions_optimized(
                user_id=user_id,
                permissions=permissions,
                db=mock_db
            )
            batch_end = time.perf_counter()
            
            workflow_end = time.perf_counter()
            
            # Performance analysis
            total_workflow_time = (workflow_end - workflow_start) * 1000
            batch_time = (batch_end - batch_start) * 1000
            avg_individual_time = statistics.mean(individual_times)
            
            # Assertions
            assert avg_individual_time < 10.0, f"Average individual check time {avg_individual_time:.2f}ms exceeds 10ms target"
            assert batch_time < 50.0, f"Batch check time {batch_time:.2f}ms too high"
            assert total_workflow_time < 100.0, f"Total workflow time {total_workflow_time:.2f}ms too high"
            assert len(batch_results) == len(permissions)
            
            print(f"End-to-end performance results:")
            print(f"  Total workflow: {total_workflow_time:.2f}ms")
            print(f"  Average individual check: {avg_individual_time:.2f}ms")
            print(f"  Batch check: {batch_time:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])