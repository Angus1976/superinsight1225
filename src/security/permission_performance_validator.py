"""
Permission Performance Validator for SuperInsight Platform.

Validates that permission checks consistently meet the <10ms performance requirement
and provides optimization recommendations when performance degrades.
"""

import asyncio
import logging
import time
import statistics
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class PerformanceValidationResult:
    """Result of performance validation."""
    meets_target: bool
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    compliance_rate: float
    total_checks: int
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PerformanceThresholds:
    """Performance thresholds for validation."""
    target_avg_ms: float = 10.0
    target_p95_ms: float = 10.0
    target_p99_ms: float = 15.0
    min_compliance_rate: float = 95.0
    warning_avg_ms: float = 8.0
    warning_p95_ms: float = 8.0


class PermissionPerformanceValidator:
    """
    Validates permission check performance against strict requirements.
    
    Ensures that permission checks consistently meet the <10ms target
    and provides actionable recommendations for optimization.
    """
    
    def __init__(self, thresholds: Optional[PerformanceThresholds] = None):
        self.thresholds = thresholds or PerformanceThresholds()
        self.performance_history = deque(maxlen=10000)  # Keep last 10k measurements
        self.validation_history = deque(maxlen=100)  # Keep last 100 validation results
        self._lock = threading.Lock()
        
        # Performance tracking
        self.daily_stats = defaultdict(list)
        self.hourly_stats = defaultdict(list)
        
        # Optimization tracking
        self.optimization_applied = False
        self.last_optimization_time = None
    
    def record_permission_check(
        self,
        response_time_ms: float,
        cache_hit: bool = False,
        user_id: Optional[UUID] = None,
        permission_name: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """Record a permission check for performance validation."""
        timestamp = timestamp or datetime.utcnow()
        
        measurement = {
            'response_time_ms': response_time_ms,
            'cache_hit': cache_hit,
            'user_id': str(user_id) if user_id else None,
            'permission_name': permission_name,
            'timestamp': timestamp
        }
        
        with self._lock:
            self.performance_history.append(measurement)
            
            # Track daily and hourly stats
            day_key = timestamp.strftime('%Y-%m-%d')
            hour_key = timestamp.strftime('%Y-%m-%d-%H')
            
            self.daily_stats[day_key].append(response_time_ms)
            self.hourly_stats[hour_key].append(response_time_ms)
    
    def validate_current_performance(
        self,
        time_window_minutes: int = 60
    ) -> PerformanceValidationResult:
        """
        Validate current performance against thresholds.
        
        Args:
            time_window_minutes: Time window for analysis
            
        Returns:
            Performance validation result
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        with self._lock:
            # Filter recent measurements
            recent_measurements = [
                m for m in self.performance_history
                if m['timestamp'] >= cutoff_time
            ]
        
        if not recent_measurements:
            return PerformanceValidationResult(
                meets_target=False,
                avg_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                compliance_rate=0.0,
                total_checks=0,
                issues=["No performance data available"],
                recommendations=["Ensure permission checks are being recorded"]
            )
        
        # Calculate performance metrics
        response_times = [m['response_time_ms'] for m in recent_measurements]
        cache_hits = sum(1 for m in recent_measurements if m['cache_hit'])
        
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 1 else response_times[0]
        
        under_target = sum(1 for t in response_times if t < self.thresholds.target_avg_ms)
        compliance_rate = (under_target / len(response_times)) * 100
        
        # Check if performance meets targets
        meets_target = (
            avg_response_time < self.thresholds.target_avg_ms and
            p95_response_time < self.thresholds.target_p95_ms and
            p99_response_time < self.thresholds.target_p99_ms and
            compliance_rate >= self.thresholds.min_compliance_rate
        )
        
        # Identify issues
        issues = []
        if avg_response_time >= self.thresholds.target_avg_ms:
            issues.append(f"Average response time {avg_response_time:.2f}ms exceeds {self.thresholds.target_avg_ms}ms target")
        
        if p95_response_time >= self.thresholds.target_p95_ms:
            issues.append(f"P95 response time {p95_response_time:.2f}ms exceeds {self.thresholds.target_p95_ms}ms target")
        
        if p99_response_time >= self.thresholds.target_p99_ms:
            issues.append(f"P99 response time {p99_response_time:.2f}ms exceeds {self.thresholds.target_p99_ms}ms target")
        
        if compliance_rate < self.thresholds.min_compliance_rate:
            issues.append(f"Compliance rate {compliance_rate:.1f}% below {self.thresholds.min_compliance_rate}% target")
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            recent_measurements, avg_response_time, p95_response_time, cache_hits
        )
        
        result = PerformanceValidationResult(
            meets_target=meets_target,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            compliance_rate=compliance_rate,
            total_checks=len(recent_measurements),
            issues=issues,
            recommendations=recommendations
        )
        
        # Store validation result
        with self._lock:
            self.validation_history.append(result)
        
        return result
    
    def _generate_recommendations(
        self,
        measurements: List[Dict],
        avg_response_time: float,
        p95_response_time: float,
        cache_hits: int
    ) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        total_measurements = len(measurements)
        cache_hit_rate = (cache_hits / total_measurements) * 100 if total_measurements > 0 else 0
        
        # Cache optimization recommendations
        if cache_hit_rate < 90.0:
            recommendations.append(
                f"Cache hit rate is {cache_hit_rate:.1f}%. Consider enabling permission preloading "
                f"or increasing cache TTL to improve performance."
            )
        
        # Response time recommendations
        if avg_response_time > self.thresholds.warning_avg_ms:
            recommendations.append(
                f"Average response time {avg_response_time:.2f}ms approaching target. "
                f"Consider enabling query optimization or increasing memory cache size."
            )
        
        if p95_response_time > self.thresholds.warning_p95_ms:
            recommendations.append(
                f"P95 response time {p95_response_time:.2f}ms approaching target. "
                f"Consider database index optimization or connection pooling."
            )
        
        # Pattern analysis recommendations
        non_cached_times = [
            m['response_time_ms'] for m in measurements 
            if not m['cache_hit']
        ]
        
        if non_cached_times:
            avg_non_cached = statistics.mean(non_cached_times)
            if avg_non_cached > 5.0:
                recommendations.append(
                    f"Non-cached queries average {avg_non_cached:.2f}ms. "
                    f"Consider database query optimization or prepared statements."
                )
        
        # User pattern recommendations
        user_counts = defaultdict(int)
        for m in measurements:
            if m['user_id']:
                user_counts[m['user_id']] += 1
        
        if user_counts:
            max_user_checks = max(user_counts.values())
            if max_user_checks > 50:  # High-frequency user
                recommendations.append(
                    f"High-frequency users detected (max {max_user_checks} checks). "
                    f"Consider implementing user-specific cache warming."
                )
        
        # Permission pattern recommendations
        permission_counts = defaultdict(int)
        for m in measurements:
            if m['permission_name']:
                permission_counts[m['permission_name']] += 1
        
        if permission_counts:
            # Find most common permissions
            sorted_permissions = sorted(
                permission_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            if len(sorted_permissions) > 0:
                top_permission_count = sorted_permissions[0][1]
                if top_permission_count > total_measurements * 0.3:  # >30% of checks
                    recommendations.append(
                        f"Permission '{sorted_permissions[0][0]}' accounts for "
                        f"{(top_permission_count/total_measurements)*100:.1f}% of checks. "
                        f"Consider aggressive caching for common permissions."
                    )
        
        if not recommendations:
            recommendations.append("Performance is optimal. No specific optimizations needed.")
        
        return recommendations
    
    def get_performance_trend(self, days: int = 7) -> Dict[str, Any]:
        """Get performance trend analysis over specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with self._lock:
            # Get daily averages
            daily_averages = {}
            for day_key, times in self.daily_stats.items():
                day_date = datetime.strptime(day_key, '%Y-%m-%d')
                if day_date >= cutoff_date and times:
                    daily_averages[day_key] = statistics.mean(times)
            
            # Get hourly averages for last 24 hours
            hourly_averages = {}
            last_24h = datetime.utcnow() - timedelta(hours=24)
            for hour_key, times in self.hourly_stats.items():
                hour_date = datetime.strptime(hour_key, '%Y-%m-%d-%H')
                if hour_date >= last_24h and times:
                    hourly_averages[hour_key] = statistics.mean(times)
        
        # Calculate trend
        if len(daily_averages) >= 2:
            sorted_days = sorted(daily_averages.items())
            recent_avg = statistics.mean([avg for _, avg in sorted_days[-3:]])  # Last 3 days
            older_avg = statistics.mean([avg for _, avg in sorted_days[:-3]])   # Older days
            
            if older_avg > 0:
                trend_percentage = ((recent_avg - older_avg) / older_avg) * 100
            else:
                trend_percentage = 0
        else:
            trend_percentage = 0
        
        return {
            'daily_averages': daily_averages,
            'hourly_averages': hourly_averages,
            'trend_percentage': trend_percentage,
            'trend_direction': 'improving' if trend_percentage < -5 else 'degrading' if trend_percentage > 5 else 'stable'
        }
    
    def run_performance_stress_test(
        self,
        rbac_controller,
        num_checks: int = 1000,
        concurrent_users: int = 10
    ) -> PerformanceValidationResult:
        """
        Run a stress test to validate performance under load.
        
        Args:
            rbac_controller: RBAC controller to test
            num_checks: Number of permission checks to perform
            concurrent_users: Number of concurrent users to simulate
            
        Returns:
            Performance validation result
        """
        from uuid import uuid4
        from unittest.mock import Mock
        
        print(f"Running performance stress test: {num_checks} checks, {concurrent_users} concurrent users")
        
        # Create test users and permissions
        test_users = [uuid4() for _ in range(concurrent_users)]
        test_permissions = ["read_data", "write_data", "delete_data", "manage_users", "view_reports"]
        
        # Mock database and users
        mock_db = Mock()
        mock_user = Mock()
        mock_user.tenant_id = "stress_test_tenant"
        mock_user.is_active = True
        
        # Mock the get_user_by_id method
        rbac_controller.get_user_by_id = Mock(return_value=mock_user)
        
        def perform_permission_check(user_id, permission_name):
            """Perform a single permission check and measure time."""
            start_time = time.perf_counter()
            result = rbac_controller.check_user_permission(
                user_id=user_id,
                permission_name=permission_name,
                db=mock_db
            )
            end_time = time.perf_counter()
            
            response_time_ms = (end_time - start_time) * 1000
            return response_time_ms, result
        
        # Run concurrent stress test
        response_times = []
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            
            for i in range(num_checks):
                user_id = test_users[i % len(test_users)]
                permission = test_permissions[i % len(test_permissions)]
                
                future = executor.submit(perform_permission_check, user_id, permission)
                futures.append(future)
            
            # Collect results
            for future in futures:
                response_time_ms, result = future.result()
                response_times.append(response_time_ms)
                
                # Record for validation
                self.record_permission_check(response_time_ms, cache_hit=True)
        
        # Analyze stress test results
        if response_times:
            avg_time = statistics.mean(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
            p99_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 1 else response_times[0]
            
            under_target = sum(1 for t in response_times if t < self.thresholds.target_avg_ms)
            compliance_rate = (under_target / len(response_times)) * 100
            
            meets_target = (
                avg_time < self.thresholds.target_avg_ms and
                p95_time < self.thresholds.target_p95_ms and
                compliance_rate >= self.thresholds.min_compliance_rate
            )
            
            issues = []
            if not meets_target:
                if avg_time >= self.thresholds.target_avg_ms:
                    issues.append(f"Stress test average time {avg_time:.2f}ms exceeds target")
                if p95_time >= self.thresholds.target_p95_ms:
                    issues.append(f"Stress test P95 time {p95_time:.2f}ms exceeds target")
                if compliance_rate < self.thresholds.min_compliance_rate:
                    issues.append(f"Stress test compliance {compliance_rate:.1f}% below target")
            
            recommendations = []
            if not meets_target:
                recommendations.extend([
                    "Performance degrades under load. Consider:",
                    "- Increasing memory cache size",
                    "- Enabling connection pooling",
                    "- Optimizing database queries",
                    "- Implementing request rate limiting"
                ])
            
            result = PerformanceValidationResult(
                meets_target=meets_target,
                avg_response_time_ms=avg_time,
                p95_response_time_ms=p95_time,
                p99_response_time_ms=p99_time,
                compliance_rate=compliance_rate,
                total_checks=len(response_times),
                issues=issues,
                recommendations=recommendations
            )
            
            print(f"Stress test completed:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  P95: {p95_time:.2f}ms")
            print(f"  P99: {p99_time:.2f}ms")
            print(f"  Compliance: {compliance_rate:.1f}%")
            print(f"  Target met: {'✅' if meets_target else '❌'}")
            
            return result
        
        else:
            return PerformanceValidationResult(
                meets_target=False,
                avg_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                compliance_rate=0.0,
                total_checks=0,
                issues=["Stress test failed to complete"],
                recommendations=["Check system configuration and try again"]
            )
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        current_validation = self.validate_current_performance()
        trend_analysis = self.get_performance_trend()
        
        with self._lock:
            recent_validations = list(self.validation_history)[-10:]  # Last 10 validations
        
        # Calculate validation success rate
        if recent_validations:
            success_rate = (sum(1 for v in recent_validations if v.meets_target) / len(recent_validations)) * 100
        else:
            success_rate = 0.0
        
        return {
            'current_performance': {
                'meets_target': current_validation.meets_target,
                'avg_response_time_ms': current_validation.avg_response_time_ms,
                'p95_response_time_ms': current_validation.p95_response_time_ms,
                'p99_response_time_ms': current_validation.p99_response_time_ms,
                'compliance_rate': current_validation.compliance_rate,
                'total_checks': current_validation.total_checks
            },
            'validation_history': {
                'success_rate': success_rate,
                'recent_validations': len(recent_validations),
                'total_validations': len(self.validation_history)
            },
            'trend_analysis': trend_analysis,
            'thresholds': {
                'target_avg_ms': self.thresholds.target_avg_ms,
                'target_p95_ms': self.thresholds.target_p95_ms,
                'target_p99_ms': self.thresholds.target_p99_ms,
                'min_compliance_rate': self.thresholds.min_compliance_rate
            },
            'issues': current_validation.issues,
            'recommendations': current_validation.recommendations,
            'optimization_status': {
                'applied': self.optimization_applied,
                'last_applied': self.last_optimization_time.isoformat() if self.last_optimization_time else None
            }
        }
    
    def mark_optimization_applied(self):
        """Mark that performance optimization has been applied."""
        self.optimization_applied = True
        self.last_optimization_time = datetime.utcnow()
        logger.info("Performance optimization marked as applied")


# Global validator instance
_performance_validator = None


def get_performance_validator() -> PermissionPerformanceValidator:
    """Get the global performance validator instance."""
    global _performance_validator
    if _performance_validator is None:
        _performance_validator = PermissionPerformanceValidator()
    return _performance_validator