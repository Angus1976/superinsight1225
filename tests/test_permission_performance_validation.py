"""
Test suite for permission performance validation system.

Tests the performance validation system to ensure it correctly monitors
and validates the <10ms permission check requirement.
"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch

from src.security.permission_performance_validator import (
    PermissionPerformanceValidator,
    PerformanceThresholds,
    PerformanceValidationResult,
    get_performance_validator
)
from src.security.rbac_controller_optimized import OptimizedRBACController
from src.security.permission_performance_optimizer import OptimizationConfig


class TestPermissionPerformanceValidator:
    """Test the PermissionPerformanceValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.thresholds = PerformanceThresholds(
            target_avg_ms=10.0,
            target_p95_ms=10.0,
            target_p99_ms=15.0,
            min_compliance_rate=95.0
        )
        self.validator = PermissionPerformanceValidator(self.thresholds)
        self.user_id = uuid4()
    
    def test_record_permission_check(self):
        """Test recording permission check metrics."""
        # Record some test metrics
        self.validator.record_permission_check(
            response_time_ms=5.0,
            cache_hit=True,
            user_id=self.user_id,
            permission_name="read_data"
        )
        
        self.validator.record_permission_check(
            response_time_ms=8.5,
            cache_hit=False,
            user_id=self.user_id,
            permission_name="write_data"
        )
        
        # Verify metrics were recorded
        assert len(self.validator.performance_history) == 2
        
        # Check first metric
        first_metric = self.validator.performance_history[0]
        assert first_metric['response_time_ms'] == 5.0
        assert first_metric['cache_hit'] is True
        assert first_metric['user_id'] == str(self.user_id)
        assert first_metric['permission_name'] == "read_data"
        assert isinstance(first_metric['timestamp'], datetime)
    
    def test_validate_current_performance_meets_target(self):
        """Test performance validation when targets are met."""
        # Record metrics that meet the target
        for i in range(100):
            response_time = 3.0 + (i % 5) * 0.5  # 3.0-5.5ms range
            self.validator.record_permission_check(
                response_time_ms=response_time,
                cache_hit=i % 3 == 0,  # 33% cache hit rate
                user_id=self.user_id,
                permission_name=f"permission_{i % 5}"
            )
        
        # Validate performance
        result = self.validator.validate_current_performance()
        
        assert result.meets_target is True
        assert result.avg_response_time_ms < 10.0
        assert result.p95_response_time_ms < 10.0
        assert result.p99_response_time_ms < 15.0
        assert result.compliance_rate >= 95.0
        assert result.total_checks == 100
        assert len(result.issues) == 0
        assert len(result.recommendations) > 0
    
    def test_validate_current_performance_fails_target(self):
        """Test performance validation when targets are not met."""
        # Record metrics that exceed the target
        for i in range(100):
            response_time = 12.0 + (i % 10)  # 12-21ms range (exceeds 10ms target)
            self.validator.record_permission_check(
                response_time_ms=response_time,
                cache_hit=i % 10 == 0,  # 10% cache hit rate
                user_id=self.user_id,
                permission_name=f"permission_{i % 3}"
            )
        
        # Validate performance
        result = self.validator.validate_current_performance()
        
        assert result.meets_target is False
        assert result.avg_response_time_ms >= 10.0
        assert result.total_checks == 100
        assert len(result.issues) > 0
        assert len(result.recommendations) > 0
        
        # Check that issues mention the specific problems
        issues_text = " ".join(result.issues)
        assert "Average response time" in issues_text
        assert "exceeds" in issues_text
    
    def test_validate_current_performance_no_data(self):
        """Test performance validation with no data."""
        result = self.validator.validate_current_performance()
        
        assert result.meets_target is False
        assert result.avg_response_time_ms == 0.0
        assert result.total_checks == 0
        assert len(result.issues) == 1
        assert "No performance data available" in result.issues[0]
    
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        # Record metrics with various patterns
        measurements = []
        
        # Low cache hit rate scenario
        for i in range(50):
            measurements.append({
                'response_time_ms': 8.0,
                'cache_hit': i % 20 == 0,  # 5% cache hit rate
                'user_id': str(self.user_id),
                'permission_name': 'read_data',
                'timestamp': datetime.utcnow()
            })
        
        recommendations = self.validator._generate_recommendations(
            measurements, 8.0, 9.0, 2  # 2 cache hits out of 50
        )
        
        assert len(recommendations) > 0
        recommendations_text = " ".join(recommendations)
        assert "cache hit rate" in recommendations_text.lower()
    
    def test_get_performance_trend(self):
        """Test performance trend analysis."""
        # Record metrics over multiple days
        base_time = datetime.utcnow() - timedelta(days=5)
        
        for day in range(5):
            day_time = base_time + timedelta(days=day)
            
            # Simulate degrading performance over time
            base_response_time = 5.0 + day * 1.0  # 5ms to 9ms over 5 days
            
            for hour in range(24):
                hour_time = day_time + timedelta(hours=hour)
                
                # Record hourly metrics
                self.validator.daily_stats[hour_time.strftime('%Y-%m-%d')].append(base_response_time)
                self.validator.hourly_stats[hour_time.strftime('%Y-%m-%d-%H')].append(base_response_time)
        
        # Get trend analysis
        trend_data = self.validator.get_performance_trend(days=5)
        
        assert 'daily_averages' in trend_data
        assert 'hourly_averages' in trend_data
        assert 'trend_percentage' in trend_data
        assert 'trend_direction' in trend_data
        
        # Should detect degrading trend
        assert trend_data['trend_direction'] in ['degrading', 'stable']
        assert len(trend_data['daily_averages']) > 0
    
    def test_run_performance_stress_test(self):
        """Test performance stress testing."""
        # Create mock RBAC controller
        mock_controller = Mock()
        mock_controller.check_user_permission = Mock(return_value=True)
        mock_controller.get_user_by_id = Mock()
        
        # Mock user
        mock_user = Mock()
        mock_user.tenant_id = "test_tenant"
        mock_user.is_active = True
        mock_controller.get_user_by_id.return_value = mock_user
        
        # Run stress test
        result = self.validator.run_performance_stress_test(
            rbac_controller=mock_controller,
            num_checks=100,
            concurrent_users=5
        )
        
        assert isinstance(result, PerformanceValidationResult)
        assert result.total_checks == 100
        assert result.avg_response_time_ms >= 0
        assert result.compliance_rate >= 0
        
        # Verify controller was called
        assert mock_controller.check_user_permission.call_count == 100
    
    def test_generate_performance_report(self):
        """Test comprehensive performance report generation."""
        # Record some test data
        for i in range(50):
            self.validator.record_permission_check(
                response_time_ms=5.0 + i * 0.1,
                cache_hit=i % 2 == 0,
                user_id=self.user_id,
                permission_name=f"permission_{i % 3}"
            )
        
        # Generate report
        report = self.validator.generate_performance_report()
        
        assert 'current_performance' in report
        assert 'validation_history' in report
        assert 'trend_analysis' in report
        assert 'thresholds' in report
        assert 'issues' in report
        assert 'recommendations' in report
        assert 'optimization_status' in report
        
        # Check current performance data
        current_perf = report['current_performance']
        assert 'meets_target' in current_perf
        assert 'avg_response_time_ms' in current_perf
        assert 'compliance_rate' in current_perf
        
        # Check thresholds
        thresholds = report['thresholds']
        assert thresholds['target_avg_ms'] == 10.0
        assert thresholds['min_compliance_rate'] == 95.0
    
    def test_mark_optimization_applied(self):
        """Test marking optimization as applied."""
        # Initially not applied
        assert self.validator.optimization_applied is False
        assert self.validator.last_optimization_time is None
        
        # Mark as applied
        self.validator.mark_optimization_applied()
        
        assert self.validator.optimization_applied is True
        assert self.validator.last_optimization_time is not None
        assert isinstance(self.validator.last_optimization_time, datetime)


class TestPerformanceValidatorIntegration:
    """Integration tests for performance validator with RBAC controller."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = OptimizationConfig(target_response_time_ms=10.0)
        self.controller = OptimizedRBACController(optimization_config=self.config)
        self.validator = get_performance_validator()
        self.user_id = uuid4()
    
    def test_integration_with_rbac_controller(self):
        """Test integration between validator and RBAC controller."""
        # Mock database and user
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = self.user_id
        mock_user.tenant_id = "test_tenant"
        mock_user.is_active = True
        
        self.controller.get_user_by_id = Mock(return_value=mock_user)
        
        # Perform permission checks and record metrics
        permissions = ["read_data", "write_data", "delete_data"]
        
        for permission in permissions:
            start_time = time.perf_counter()
            result = self.controller.check_user_permission(
                user_id=self.user_id,
                permission_name=permission,
                db=mock_db
            )
            end_time = time.perf_counter()
            
            response_time_ms = (end_time - start_time) * 1000
            
            # Record metric in validator
            self.validator.record_permission_check(
                response_time_ms=response_time_ms,
                cache_hit=True,  # Assume cache hit for fast response
                user_id=self.user_id,
                permission_name=permission
            )
        
        # Validate performance
        validation_result = self.validator.validate_current_performance()
        
        assert validation_result.total_checks >= 3
        assert validation_result.avg_response_time_ms >= 0
        
        # Should meet target with cached responses
        assert validation_result.meets_target is True
        assert validation_result.avg_response_time_ms < 10.0
    
    def test_performance_monitoring_under_load(self):
        """Test performance monitoring under simulated load."""
        # Mock database and user
        mock_db = Mock()
        mock_user = Mock()
        mock_user.tenant_id = "test_tenant"
        mock_user.is_active = True
        
        self.controller.get_user_by_id = Mock(return_value=mock_user)
        
        # Simulate load with multiple permission checks
        num_checks = 200
        permissions = ["read_data", "write_data", "delete_data", "manage_users"]
        
        response_times = []
        
        for i in range(num_checks):
            permission = permissions[i % len(permissions)]
            user_id = uuid4()  # Different users
            
            start_time = time.perf_counter()
            result = self.controller.check_user_permission(
                user_id=user_id,
                permission_name=permission,
                db=mock_db
            )
            end_time = time.perf_counter()
            
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            # Record metric
            self.validator.record_permission_check(
                response_time_ms=response_time_ms,
                cache_hit=i > 50,  # First 50 are cache misses, rest are hits
                user_id=user_id,
                permission_name=permission
            )
        
        # Validate performance under load
        validation_result = self.validator.validate_current_performance()
        
        assert validation_result.total_checks >= num_checks
        
        # Calculate actual performance metrics
        import statistics
        avg_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
        
        print(f"Load test results:")
        print(f"  Checks performed: {num_checks}")
        print(f"  Average time: {avg_time:.2f}ms")
        print(f"  P95 time: {p95_time:.2f}ms")
        print(f"  Validation meets target: {validation_result.meets_target}")
        
        # Performance should still be good with caching
        assert avg_time < 5.0  # Should be very fast with mocked operations
        assert validation_result.meets_target is True


class TestPerformanceThresholds:
    """Test performance threshold management."""
    
    def test_default_thresholds(self):
        """Test default performance thresholds."""
        thresholds = PerformanceThresholds()
        
        assert thresholds.target_avg_ms == 10.0
        assert thresholds.target_p95_ms == 10.0
        assert thresholds.target_p99_ms == 15.0
        assert thresholds.min_compliance_rate == 95.0
        assert thresholds.warning_avg_ms == 8.0
        assert thresholds.warning_p95_ms == 8.0
    
    def test_custom_thresholds(self):
        """Test custom performance thresholds."""
        thresholds = PerformanceThresholds(
            target_avg_ms=5.0,
            target_p95_ms=8.0,
            min_compliance_rate=99.0
        )
        
        assert thresholds.target_avg_ms == 5.0
        assert thresholds.target_p95_ms == 8.0
        assert thresholds.min_compliance_rate == 99.0
    
    def test_validator_with_custom_thresholds(self):
        """Test validator with custom thresholds."""
        strict_thresholds = PerformanceThresholds(
            target_avg_ms=5.0,
            target_p95_ms=5.0,
            min_compliance_rate=99.0
        )
        
        validator = PermissionPerformanceValidator(strict_thresholds)
        
        # Record metrics that would pass normal thresholds but fail strict ones
        for i in range(100):
            validator.record_permission_check(
                response_time_ms=7.0,  # Would pass 10ms target but fail 5ms target
                cache_hit=True,
                user_id=uuid4(),
                permission_name="test_permission"
            )
        
        result = validator.validate_current_performance()
        
        # Should fail strict thresholds
        assert result.meets_target is False
        assert result.avg_response_time_ms > strict_thresholds.target_avg_ms


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])