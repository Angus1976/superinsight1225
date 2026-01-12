"""
Permission Performance Validator for <10ms Target.

Comprehensive validation system to ensure permission checks consistently
meet the <10ms response time requirement with high confidence.
"""

import asyncio
import logging
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID, uuid4
import threading

from sqlalchemy.orm import Session

from src.security.rbac_controller_ultra_fast import get_ultra_fast_rbac_controller
from src.security.ultra_fast_permission_checker import PerformanceTarget

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Results from performance validation."""
    passed: bool
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    compliance_rate: float
    cache_hit_rate: float
    total_tests: int
    failed_tests: int
    error_rate: float
    performance_grade: str
    recommendations: List[str]


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    concurrent_users: int = 50
    requests_per_user: int = 100
    test_duration_seconds: int = 60
    ramp_up_seconds: int = 10
    permissions_per_request: int = 5
    cache_warm_up: bool = True


class PermissionPerformanceValidator:
    """
    Comprehensive performance validator for permission checking system.
    
    Validates that permission checks consistently meet <10ms target under
    various load conditions and usage patterns.
    """
    
    def __init__(
        self,
        target_response_time_ms: float = 10.0,
        confidence_level: float = 98.0
    ):
        self.target_response_time_ms = target_response_time_ms
        self.confidence_level = confidence_level
        
        # Get ultra-fast controller
        self.controller = get_ultra_fast_rbac_controller(
            target_response_time_ms=target_response_time_ms
        )
        
        # Test data
        self.test_users = []
        self.test_permissions = [
            "read_data", "write_data", "view_dashboard", "manage_projects",
            "view_reports", "export_data", "manage_users", "view_analytics",
            "create_annotations", "edit_annotations", "delete_annotations",
            "manage_datasets", "view_billing", "manage_billing", "admin_access"
        ]
        
        # Results tracking
        self._results_lock = threading.Lock()
        self._test_results = []
    
    def setup_test_environment(self, db: Session, num_users: int = 100) -> bool:
        """
        Set up test environment with users, roles, and permissions.
        
        Args:
            db: Database session
            num_users: Number of test users to create
            
        Returns:
            True if setup successful
        """
        try:
            logger.info(f"Setting up test environment with {num_users} users...")
            
            # Create test tenant
            test_tenant_id = "perf_test_tenant"
            
            # Create test users (simplified for performance testing)
            self.test_users = []
            for i in range(num_users):
                user_id = uuid4()
                self.test_users.append({
                    "id": user_id,
                    "tenant_id": test_tenant_id,
                    "username": f"test_user_{i}",
                    "permissions": self.test_permissions[:5 + (i % 10)]  # Varying permissions
                })
            
            logger.info(f"Created {len(self.test_users)} test users")
            
            # Pre-warm cache for some users
            for i, user in enumerate(self.test_users[:20]):  # Pre-warm first 20 users
                self.controller.pre_warm_user_permissions(
                    user["id"], db, user["permissions"]
                )
            
            logger.info("Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            return False
    
    def validate_single_permission_performance(
        self,
        db: Session,
        num_tests: int = 1000
    ) -> ValidationResult:
        """
        Validate single permission check performance.
        
        Args:
            db: Database session
            num_tests: Number of tests to run
            
        Returns:
            Validation results
        """
        logger.info(f"Running {num_tests} single permission performance tests...")
        
        response_times = []
        cache_hits = 0
        errors = 0
        
        for i in range(num_tests):
            try:
                # Select random user and permission
                user = self.test_users[i % len(self.test_users)]
                permission = self.test_permissions[i % len(self.test_permissions)]
                
                # Measure response time
                start_time = time.perf_counter()
                
                result = self.controller.check_user_permission(
                    user_id=user["id"],
                    permission_name=permission,
                    db=db
                )
                
                response_time_ms = (time.perf_counter() - start_time) * 1000
                response_times.append(response_time_ms)
                
                # Check if this was likely a cache hit (very fast response)
                if response_time_ms < 1.0:
                    cache_hits += 1
                
            except Exception as e:
                errors += 1
                logger.error(f"Test {i} failed: {e}")
        
        return self._calculate_validation_result(
            response_times, cache_hits, errors, num_tests
        )
    
    def validate_batch_permission_performance(
        self,
        db: Session,
        num_tests: int = 500,
        batch_size: int = 5
    ) -> ValidationResult:
        """
        Validate batch permission check performance.
        
        Args:
            db: Database session
            num_tests: Number of batch tests to run
            batch_size: Number of permissions per batch
            
        Returns:
            Validation results
        """
        logger.info(f"Running {num_tests} batch permission tests (batch size: {batch_size})...")
        
        response_times = []
        cache_hits = 0
        errors = 0
        
        for i in range(num_tests):
            try:
                # Select random user and permissions
                user = self.test_users[i % len(self.test_users)]
                permissions = self.test_permissions[:batch_size]
                
                # Measure response time
                start_time = time.perf_counter()
                
                results = self.controller.batch_check_permissions(
                    user_id=user["id"],
                    permissions=permissions,
                    db=db
                )
                
                total_time_ms = (time.perf_counter() - start_time) * 1000
                avg_time_per_permission = total_time_ms / batch_size
                response_times.append(avg_time_per_permission)
                
                # Check if this was likely a cache hit
                if avg_time_per_permission < 1.0:
                    cache_hits += 1
                
            except Exception as e:
                errors += 1
                logger.error(f"Batch test {i} failed: {e}")
        
        return self._calculate_validation_result(
            response_times, cache_hits, errors, num_tests
        )
    
    def validate_concurrent_performance(
        self,
        db: Session,
        config: LoadTestConfig
    ) -> ValidationResult:
        """
        Validate performance under concurrent load.
        
        Args:
            db: Database session
            config: Load test configuration
            
        Returns:
            Validation results
        """
        logger.info(f"Running concurrent load test with {config.concurrent_users} users...")
        
        self._test_results = []
        
        def worker_thread(worker_id: int, requests_count: int) -> List[float]:
            """Worker thread for concurrent testing."""
            thread_results = []
            
            for i in range(requests_count):
                try:
                    # Select random user and permissions
                    user = self.test_users[worker_id % len(self.test_users)]
                    permissions = self.test_permissions[:config.permissions_per_request]
                    
                    # Measure response time
                    start_time = time.perf_counter()
                    
                    if len(permissions) == 1:
                        result = self.controller.check_user_permission(
                            user_id=user["id"],
                            permission_name=permissions[0],
                            db=db
                        )
                    else:
                        results = self.controller.batch_check_permissions(
                            user_id=user["id"],
                            permissions=permissions,
                            db=db
                        )
                    
                    response_time_ms = (time.perf_counter() - start_time) * 1000
                    if len(permissions) > 1:
                        response_time_ms /= len(permissions)  # Average per permission
                    
                    thread_results.append(response_time_ms)
                    
                    # Small delay to simulate realistic usage
                    time.sleep(0.001)  # 1ms delay
                    
                except Exception as e:
                    logger.error(f"Worker {worker_id} request {i} failed: {e}")
                    thread_results.append(float('inf'))  # Mark as error
            
            return thread_results
        
        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
            futures = []
            
            for worker_id in range(config.concurrent_users):
                future = executor.submit(
                    worker_thread, 
                    worker_id, 
                    config.requests_per_user
                )
                futures.append(future)
            
            # Collect results
            all_response_times = []
            errors = 0
            
            for future in as_completed(futures):
                try:
                    worker_results = future.result()
                    for response_time in worker_results:
                        if response_time == float('inf'):
                            errors += 1
                        else:
                            all_response_times.append(response_time)
                except Exception as e:
                    logger.error(f"Worker thread failed: {e}")
                    errors += config.requests_per_user
        
        # Calculate cache hits (approximate)
        cache_hits = sum(1 for t in all_response_times if t < 1.0)
        total_tests = len(all_response_times) + errors
        
        return self._calculate_validation_result(
            all_response_times, cache_hits, errors, total_tests
        )
    
    def validate_cold_cache_performance(
        self,
        db: Session,
        num_tests: int = 100
    ) -> ValidationResult:
        """
        Validate performance with cold cache (worst-case scenario).
        
        Args:
            db: Database session
            num_tests: Number of tests to run
            
        Returns:
            Validation results
        """
        logger.info(f"Running {num_tests} cold cache performance tests...")
        
        response_times = []
        errors = 0
        
        for i in range(num_tests):
            try:
                # Clear cache before each test
                self.controller.clear_performance_cache()
                
                # Select random user and permission
                user = self.test_users[i % len(self.test_users)]
                permission = self.test_permissions[i % len(self.test_permissions)]
                
                # Measure response time
                start_time = time.perf_counter()
                
                result = self.controller.check_user_permission(
                    user_id=user["id"],
                    permission_name=permission,
                    db=db
                )
                
                response_time_ms = (time.perf_counter() - start_time) * 1000
                response_times.append(response_time_ms)
                
            except Exception as e:
                errors += 1
                logger.error(f"Cold cache test {i} failed: {e}")
        
        return self._calculate_validation_result(
            response_times, 0, errors, num_tests  # No cache hits in cold cache test
        )
    
    def run_comprehensive_validation(
        self,
        db: Session,
        include_load_test: bool = True
    ) -> Dict[str, ValidationResult]:
        """
        Run comprehensive performance validation suite.
        
        Args:
            db: Database session
            include_load_test: Whether to include concurrent load testing
            
        Returns:
            Dictionary of validation results by test type
        """
        logger.info("Starting comprehensive performance validation...")
        
        results = {}
        
        # Setup test environment
        if not self.setup_test_environment(db):
            raise RuntimeError("Failed to setup test environment")
        
        # Test 1: Single permission performance
        results["single_permission"] = self.validate_single_permission_performance(db)
        
        # Test 2: Batch permission performance
        results["batch_permission"] = self.validate_batch_permission_performance(db)
        
        # Test 3: Cold cache performance
        results["cold_cache"] = self.validate_cold_cache_performance(db)
        
        # Test 4: Concurrent load test (optional)
        if include_load_test:
            load_config = LoadTestConfig(
                concurrent_users=20,
                requests_per_user=50,
                permissions_per_request=3
            )
            results["concurrent_load"] = self.validate_concurrent_performance(db, load_config)
        
        # Generate overall assessment
        results["overall"] = self._generate_overall_assessment(results)
        
        logger.info("Comprehensive validation complete")
        return results
    
    def _calculate_validation_result(
        self,
        response_times: List[float],
        cache_hits: int,
        errors: int,
        total_tests: int
    ) -> ValidationResult:
        """Calculate validation result from test data."""
        if not response_times:
            return ValidationResult(
                passed=False,
                avg_response_time_ms=float('inf'),
                p95_response_time_ms=float('inf'),
                p99_response_time_ms=float('inf'),
                max_response_time_ms=float('inf'),
                compliance_rate=0.0,
                cache_hit_rate=0.0,
                total_tests=total_tests,
                failed_tests=errors,
                error_rate=100.0,
                performance_grade="F",
                recommendations=["All tests failed - check system configuration"]
            )
        
        # Calculate statistics
        response_times.sort()
        avg_time = statistics.mean(response_times)
        p95_time = response_times[int(len(response_times) * 0.95)] if response_times else 0
        p99_time = response_times[int(len(response_times) * 0.99)] if response_times else 0
        max_time = max(response_times) if response_times else 0
        
        # Calculate compliance rate
        under_target = sum(1 for t in response_times if t < self.target_response_time_ms)
        compliance_rate = (under_target / len(response_times)) * 100
        
        # Calculate cache hit rate
        cache_hit_rate = (cache_hits / total_tests) * 100 if total_tests > 0 else 0
        
        # Calculate error rate
        error_rate = (errors / total_tests) * 100 if total_tests > 0 else 0
        
        # Determine if validation passed
        passed = (
            compliance_rate >= self.confidence_level and
            avg_time < self.target_response_time_ms and
            p95_time < self.target_response_time_ms * 1.5 and
            error_rate < 1.0
        )
        
        # Calculate performance grade
        grade = self._calculate_performance_grade(
            compliance_rate, cache_hit_rate, avg_time, error_rate
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            compliance_rate, cache_hit_rate, avg_time, p95_time, error_rate
        )
        
        return ValidationResult(
            passed=passed,
            avg_response_time_ms=avg_time,
            p95_response_time_ms=p95_time,
            p99_response_time_ms=p99_time,
            max_response_time_ms=max_time,
            compliance_rate=compliance_rate,
            cache_hit_rate=cache_hit_rate,
            total_tests=total_tests,
            failed_tests=errors,
            error_rate=error_rate,
            performance_grade=grade,
            recommendations=recommendations
        )
    
    def _calculate_performance_grade(
        self,
        compliance_rate: float,
        cache_hit_rate: float,
        avg_time: float,
        error_rate: float
    ) -> str:
        """Calculate performance grade A-F."""
        score = 0
        
        # Compliance rate (40% of score)
        if compliance_rate >= 99:
            score += 40
        elif compliance_rate >= 95:
            score += 35
        elif compliance_rate >= 90:
            score += 25
        elif compliance_rate >= 80:
            score += 15
        else:
            score += 5
        
        # Cache hit rate (25% of score)
        if cache_hit_rate >= 95:
            score += 25
        elif cache_hit_rate >= 90:
            score += 20
        elif cache_hit_rate >= 80:
            score += 15
        else:
            score += 5
        
        # Average response time (25% of score)
        if avg_time < 1.0:
            score += 25
        elif avg_time < 3.0:
            score += 20
        elif avg_time < 5.0:
            score += 15
        elif avg_time < 10.0:
            score += 10
        else:
            score += 0
        
        # Error rate (10% of score)
        if error_rate < 0.1:
            score += 10
        elif error_rate < 1.0:
            score += 8
        elif error_rate < 5.0:
            score += 5
        else:
            score += 0
        
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _generate_recommendations(
        self,
        compliance_rate: float,
        cache_hit_rate: float,
        avg_time: float,
        p95_time: float,
        error_rate: float
    ) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        if compliance_rate < self.confidence_level:
            recommendations.append(
                f"Compliance rate {compliance_rate:.1f}% is below target {self.confidence_level}%. "
                "Consider increasing cache size or optimizing database queries."
            )
        
        if cache_hit_rate < 90:
            recommendations.append(
                f"Cache hit rate {cache_hit_rate:.1f}% is low. "
                "Enable aggressive cache pre-warming for active users."
            )
        
        if avg_time > self.target_response_time_ms * 0.7:
            recommendations.append(
                f"Average response time {avg_time:.2f}ms is approaching target. "
                "Consider query optimization or increasing cache TTL."
            )
        
        if p95_time > self.target_response_time_ms:
            recommendations.append(
                f"P95 response time {p95_time:.2f}ms exceeds target. "
                "Investigate database performance and indexing."
            )
        
        if error_rate > 1.0:
            recommendations.append(
                f"Error rate {error_rate:.1f}% is high. "
                "Check database connectivity and query reliability."
            )
        
        if not recommendations:
            recommendations.append("Performance is excellent. All targets are being met.")
        
        return recommendations
    
    def _generate_overall_assessment(
        self,
        results: Dict[str, ValidationResult]
    ) -> ValidationResult:
        """Generate overall assessment from individual test results."""
        # Calculate weighted averages
        weights = {
            "single_permission": 0.4,
            "batch_permission": 0.3,
            "cold_cache": 0.2,
            "concurrent_load": 0.1
        }
        
        total_weight = 0
        weighted_compliance = 0
        weighted_avg_time = 0
        all_passed = True
        all_recommendations = []
        
        for test_name, result in results.items():
            if test_name in weights:
                weight = weights[test_name]
                total_weight += weight
                weighted_compliance += result.compliance_rate * weight
                weighted_avg_time += result.avg_response_time_ms * weight
                
                if not result.passed:
                    all_passed = False
                
                all_recommendations.extend(result.recommendations)
        
        # Normalize by actual weight (in case some tests were skipped)
        if total_weight > 0:
            weighted_compliance /= total_weight
            weighted_avg_time /= total_weight
        
        # Create overall result
        return ValidationResult(
            passed=all_passed and weighted_compliance >= self.confidence_level,
            avg_response_time_ms=weighted_avg_time,
            p95_response_time_ms=0,  # Not meaningful for overall
            p99_response_time_ms=0,  # Not meaningful for overall
            max_response_time_ms=0,  # Not meaningful for overall
            compliance_rate=weighted_compliance,
            cache_hit_rate=0,  # Not meaningful for overall
            total_tests=sum(r.total_tests for r in results.values()),
            failed_tests=sum(r.failed_tests for r in results.values()),
            error_rate=0,  # Not meaningful for overall
            performance_grade=self._calculate_performance_grade(
                weighted_compliance, 90, weighted_avg_time, 0
            ),
            recommendations=list(set(all_recommendations))  # Remove duplicates
        )


# Global validator instances by configuration
_performance_validators = {}


def get_performance_validator(
    target_response_time_ms: float = 10.0,
    confidence_level: float = 98.0
) -> PermissionPerformanceValidator:
    """Get a performance validator instance for the given configuration."""
    global _performance_validators
    
    # Create a key based on configuration
    config_key = f"{target_response_time_ms}_{confidence_level}"
    
    if config_key not in _performance_validators:
        _performance_validators[config_key] = PermissionPerformanceValidator(
            target_response_time_ms, confidence_level
        )
    
    return _performance_validators[config_key]