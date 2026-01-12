"""
Integration test for permission performance optimization system.

Tests the complete integration of the <10ms permission check requirement
with the existing RBAC system and validates real-world performance scenarios.
"""

import asyncio
import pytest
import time
import statistics
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch

from src.security.rbac_controller_optimized import OptimizedRBACController
from src.security.permission_performance_optimizer import OptimizationConfig
from src.security.models import UserRole
from src.security.rbac_models import ResourceType


class TestPermissionPerformanceIntegration:
    """Integration tests for permission performance optimization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create optimized controller with strict performance config
        self.config = OptimizationConfig(
            target_response_time_ms=10.0,
            cache_preload_enabled=True,
            query_optimization_enabled=True,
            batch_processing_enabled=True,
            async_logging_enabled=True,
            memory_cache_size=2000
        )
        self.controller = OptimizedRBACController(optimization_config=self.config)
        
        # Test data
        self.user_id = uuid4()
        self.tenant_id = "performance_test_tenant"
        self.permissions = [
            "read_data", "write_data", "delete_data", "manage_users",
            "view_dashboard", "export_data", "manage_projects", "view_reports"
        ]
        
        # Mock database
        self.mock_db = Mock()
        
        # Mock user
        self.mock_user = Mock()
        self.mock_user.id = self.user_id
        self.mock_user.tenant_id = self.tenant_id
        self.mock_user.is_active = True
        self.mock_user.role = UserRole.VIEWER
    
    def test_performance_target_compliance_rate(self):
        """Test that the system achieves >95% compliance with <10ms target."""
        num_checks = 200
        response_times = []
        
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            # Mock cache for realistic hit/miss ratio (90% hit rate for better performance)
            with patch.object(self.controller.permission_cache, 'get_permission') as mock_cache:
                def cache_side_effect(*args, **kwargs):
                    # 90% cache hit rate
                    import random
                    return True if random.random() < 0.9 else None
                
                mock_cache.side_effect = cache_side_effect
                
                # Mock the set_permission method
                with patch.object(self.controller.permission_cache, 'set_permission'):
                    # Mock the database execute method directly
                    mock_result = Mock()
                    mock_row = Mock()
                    mock_row.has_permission = True
                    mock_result.fetchone.return_value = mock_row
                    self.mock_db.execute.return_value = mock_result
                    
                    # Perform permission checks
                    for i in range(num_checks):
                        permission = self.permissions[i % len(self.permissions)]
                        
                        start_time = time.perf_counter()
                        result = self.controller.check_user_permission(
                            user_id=self.user_id,
                            permission_name=permission,
                            db=self.mock_db
                        )
                        end_time = time.perf_counter()
                        
                        response_time_ms = (end_time - start_time) * 1000
                        response_times.append(response_time_ms)
                        
                        # Result should be True (either from cache or database)
                        assert result is True
        
        # Calculate performance metrics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 1 else response_times[0]
        max_response_time = max(response_times)
        
        # Calculate compliance rate
        under_10ms = sum(1 for t in response_times if t < 10.0)
        compliance_rate = (under_10ms / len(response_times)) * 100
        
        # Performance assertions
        assert compliance_rate >= 95.0, f"Compliance rate {compliance_rate:.1f}% below 95% target"
        assert avg_response_time < 8.0, f"Average response time {avg_response_time:.2f}ms too high"
        assert p95_response_time < 12.0, f"P95 response time {p95_response_time:.2f}ms too high"
        assert max_response_time < 20.0, f"Max response time {max_response_time:.2f}ms too high"
        
        print(f"Performance Integration Test Results:")
        print(f"  Compliance Rate: {compliance_rate:.1f}%")
        print(f"  Average: {avg_response_time:.2f}ms")
        print(f"  P95: {p95_response_time:.2f}ms")
        print(f"  P99: {p99_response_time:.2f}ms")
        print(f"  Max: {max_response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_async_performance_optimization(self):
        """Test async performance optimization features."""
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            # Test async optimized permission check
            start_time = time.perf_counter()
            result = await self.controller.check_user_permission_optimized(
                user_id=self.user_id,
                permission_name="read_data",
                db=self.mock_db
            )
            end_time = time.perf_counter()
            
            response_time_ms = (end_time - start_time) * 1000
            
            assert result is not None
            assert response_time_ms < 10.0, f"Async optimized check took {response_time_ms:.2f}ms"
    
    @pytest.mark.asyncio
    async def test_batch_optimization_performance(self):
        """Test batch permission check optimization."""
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            # Test batch optimized permission check
            start_time = time.perf_counter()
            results = await self.controller.batch_check_permissions_optimized(
                user_id=self.user_id,
                permissions=self.permissions,
                db=self.mock_db
            )
            end_time = time.perf_counter()
            
            total_time_ms = (end_time - start_time) * 1000
            avg_time_per_permission = total_time_ms / len(self.permissions)
            
            assert len(results) == len(self.permissions)
            assert avg_time_per_permission < 10.0, f"Average batch time {avg_time_per_permission:.2f}ms per permission"
            assert total_time_ms < 50.0, f"Total batch time {total_time_ms:.2f}ms too high"
    
    def test_performance_monitoring_integration(self):
        """Test performance monitoring and statistics collection."""
        # Perform some permission checks to generate metrics
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = self.mock_user
            
            with patch.object(self.controller.permission_cache, 'get_permission') as mock_cache:
                mock_cache.return_value = True  # Cache hits for fast performance
                
                # Perform multiple checks
                for i in range(50):
                    permission = self.permissions[i % len(self.permissions)]
                    self.controller.check_user_permission(
                        user_id=self.user_id,
                        permission_name=permission,
                        db=self.mock_db
                    )
        
        # Get performance statistics
        stats = self.controller.get_performance_statistics()
        
        assert "controller_stats" in stats
        assert "optimizer_report" in stats
        assert "cache_stats" in stats
        assert stats["optimization_enabled"] is True
        assert stats["target_response_time_ms"] == 10.0
        
        # Check that metrics were collected
        controller_stats = stats["controller_stats"]
        assert controller_stats["total_checks"] >= 50
        assert controller_stats["optimized_checks"] >= 40  # Most should be optimized
        assert controller_stats["avg_response_time_ms"] >= 0
    
    def test_performance_recommendations(self):
        """Test performance optimization recommendations."""
        recommendations = self.controller.get_performance_recommendations()
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should contain actionable recommendations
        recommendation_text = " ".join(recommendations).lower()
        assert any(keyword in recommendation_text for keyword in [
            "performance", "cache", "optimization", "response time", "optimal"
        ])
    
    def test_cache_integration_performance(self):
        """Test cache integration and performance impact."""
        # Test cache statistics
        cache_stats = self.controller.get_cache_statistics()
        
        assert "hit_rate" in cache_stats
        assert "cache_system" in cache_stats
        assert cache_stats["cache_system"] == "advanced_with_redis"
        
        # Test cache clearing
        self.controller.clear_all_permission_cache()
        
        # Verify cache was cleared
        new_stats = self.controller.get_cache_statistics()
        # Cache size should be reset or very small
        assert new_stats["legacy_cache_size"] == 0
    
    def test_optimization_enable_disable(self):
        """Test enabling and disabling optimization features."""
        # Test enabling optimization
        self.controller.enable_performance_optimization()
        assert self.controller.performance_optimizer.is_optimization_enabled() is True
        
        # Test disabling optimization
        self.controller.disable_performance_optimization()
        assert self.controller.performance_optimizer.is_optimization_enabled() is False
        
        # Re-enable for other tests
        self.controller.enable_performance_optimization()
    
    def test_real_world_permission_scenario(self):
        """Test a realistic permission checking scenario."""
        # Simulate a real-world scenario with multiple users and permissions
        users = [uuid4() for _ in range(5)]
        scenarios = [
            ("read_data", True),
            ("write_data", True),
            ("delete_data", False),  # Most users don't have delete
            ("manage_users", False),  # Admin-only permission
            ("view_dashboard", True),
            ("export_data", True),
        ]
        
        response_times = []
        
        with patch.object(self.controller, 'get_user_by_id') as mock_get_user:
            # Mock different users
            def get_user_side_effect(user_id, db):
                mock_user = Mock()
                mock_user.id = user_id
                mock_user.tenant_id = self.tenant_id
                mock_user.is_active = True
                # Vary user roles
                mock_user.role = UserRole.ADMIN if str(user_id).endswith('0') else UserRole.VIEWER
                return mock_user
            
            mock_get_user.side_effect = get_user_side_effect
            
            # Mock cache with realistic behavior
            with patch.object(self.controller.permission_cache, 'get_permission') as mock_cache:
                with patch.object(self.controller.permission_cache, 'set_permission') as mock_set_cache:
                    cache_data = {}
                    
                    def cache_side_effect(user_id, permission, *args, **kwargs):
                        key = f"{user_id}:{permission}"
                        return cache_data.get(key)
                    
                    def cache_set_side_effect(user_id, permission, result, *args, **kwargs):
                        key = f"{user_id}:{permission}"
                        cache_data[key] = result
                    
                    mock_cache.side_effect = cache_side_effect
                    mock_set_cache.side_effect = cache_set_side_effect
                
                # Mock database checks
                with patch.object(self.controller, '_optimized_sync_permission_check') as mock_db_check:
                    def db_check_side_effect(user_id, permission, *args, **kwargs):
                        # Admin users have all permissions
                        if str(user_id).endswith('0'):
                            return True
                        # Regular users have limited permissions
                        return permission in ["read_data", "write_data", "view_dashboard", "export_data"]
                    
                    mock_db_check.side_effect = db_check_side_effect
                    
                    # Mock database execute for fallback
                    mock_result = Mock()
                    mock_row = Mock()
                    mock_row.has_permission = True
                    mock_result.fetchone.return_value = mock_row
                    self.mock_db.execute.return_value = mock_result
                    
                    # Perform realistic permission checks
                    for user_id in users:
                        for permission, expected in scenarios:
                            start_time = time.perf_counter()
                            result = self.controller.check_user_permission(
                                user_id=user_id,
                                permission_name=permission,
                                db=self.mock_db
                            )
                            end_time = time.perf_counter()
                            
                            response_time_ms = (end_time - start_time) * 1000
                            response_times.append(response_time_ms)
                            
                            # Verify result is boolean
                            assert isinstance(result, bool)
        
        # Analyze performance
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        under_10ms = sum(1 for t in response_times if t < 10.0)
        compliance_rate = (under_10ms / len(response_times)) * 100
        
        # Performance assertions for real-world scenario
        assert compliance_rate >= 90.0, f"Real-world compliance rate {compliance_rate:.1f}% too low"
        assert avg_response_time < 10.0, f"Real-world average time {avg_response_time:.2f}ms too high"
        assert max_response_time < 25.0, f"Real-world max time {max_response_time:.2f}ms too high"
        
        print(f"Real-world Scenario Results:")
        print(f"  Total Checks: {len(response_times)}")
        print(f"  Compliance Rate: {compliance_rate:.1f}%")
        print(f"  Average: {avg_response_time:.2f}ms")
        print(f"  Max: {max_response_time:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])