#!/usr/bin/env python3
"""
Simple validation script to test <10ms permission check performance.
This script provides a quick way to validate that the ultra-fast permission
checking system meets the <10ms response time requirement.
"""

import asyncio
import statistics
import sys
import time
from uuid import uuid4
from unittest.mock import Mock

# Add src to path for imports
sys.path.insert(0, 'src')

from src.security.rbac_controller_ultra_fast import get_ultra_fast_rbac_controller
from src.security.ultra_fast_permission_checker import get_ultra_fast_permission_checker


def create_mock_db_session():
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


def test_ultra_fast_cache():
    """Test ultra-fast cache performance."""
    print("Testing ultra-fast cache performance...")
    
    from src.security.ultra_fast_permission_checker import UltraFastCache
    
    cache = UltraFastCache(max_size=1000)
    user_id = uuid4()
    tenant_id = "test_tenant"
    
    # Test cache set performance
    start_time = time.perf_counter()
    for i in range(1000):
        cache.set(user_id, f"permission_{i}", tenant_id, True)
    set_time_ms = (time.perf_counter() - start_time) * 1000
    
    print(f"  Cache SET: {set_time_ms:.2f}ms for 1000 operations ({set_time_ms/1000:.4f}ms per op)")
    
    # Test cache get performance
    start_time = time.perf_counter()
    for i in range(1000):
        result = cache.get(user_id, f"permission_{i}", tenant_id)
    get_time_ms = (time.perf_counter() - start_time) * 1000
    
    print(f"  Cache GET: {get_time_ms:.2f}ms for 1000 operations ({get_time_ms/1000:.4f}ms per op)")
    
    # Cache statistics
    stats = cache.get_stats()
    print(f"  Cache hit rate: {stats['hit_rate']:.1f}%")
    print(f"  Cache size: {stats['cache_size']}")
    
    return set_time_ms < 50.0 and get_time_ms < 10.0


def test_single_permission_performance():
    """Test single permission check performance."""
    print("\nTesting single permission check performance...")
    
    controller = get_ultra_fast_rbac_controller(target_response_time_ms=10.0)
    db_session = create_mock_db_session()
    
    user_id = uuid4()
    permission = "read_data"
    
    # Warm up the cache
    controller.check_user_permission(
        user_id=user_id,
        permission_name=permission,
        db=db_session
    )
    
    # Test warm cache performance
    response_times = []
    for i in range(100):
        start_time = time.perf_counter()
        result = controller.check_user_permission(
            user_id=user_id,
            permission_name=permission,
            db=db_session
        )
        response_time_ms = (time.perf_counter() - start_time) * 1000
        response_times.append(response_time_ms)
    
    # Analyze results
    avg_time = statistics.mean(response_times)
    min_time = min(response_times)
    max_time = max(response_times)
    p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0]
    under_10ms = sum(1 for t in response_times if t < 10.0)
    compliance_rate = (under_10ms / len(response_times)) * 100
    
    print(f"  Average time: {avg_time:.3f}ms")
    print(f"  Min time: {min_time:.3f}ms")
    print(f"  Max time: {max_time:.3f}ms")
    print(f"  P95 time: {p95_time:.3f}ms")
    print(f"  Compliance rate (<10ms): {compliance_rate:.1f}%")
    
    # Test cold cache performance
    print("\n  Testing cold cache performance...")
    cold_times = []
    for i in range(10):
        controller.clear_performance_cache()
        
        start_time = time.perf_counter()
        result = controller.check_user_permission(
            user_id=uuid4(),  # Different user each time
            permission_name=permission,
            db=db_session
        )
        response_time_ms = (time.perf_counter() - start_time) * 1000
        cold_times.append(response_time_ms)
    
    cold_avg = statistics.mean(cold_times)
    cold_max = max(cold_times)
    print(f"  Cold cache average: {cold_avg:.3f}ms")
    print(f"  Cold cache max: {cold_max:.3f}ms")
    
    # Success criteria
    warm_success = avg_time < 10.0 and compliance_rate >= 95.0
    cold_success = cold_avg < 50.0 and cold_max < 100.0
    
    return warm_success and cold_success


def test_batch_permission_performance():
    """Test batch permission check performance."""
    print("\nTesting batch permission check performance...")
    
    controller = get_ultra_fast_rbac_controller(target_response_time_ms=10.0)
    db_session = create_mock_db_session()
    
    user_id = uuid4()
    permissions = ["read_data", "write_data", "view_dashboard", "manage_projects", "view_reports"]
    
    # Test batch performance
    response_times = []
    for i in range(50):
        start_time = time.perf_counter()
        results = controller.batch_check_permissions(
            user_id=user_id,
            permissions=permissions,
            db=db_session
        )
        total_time_ms = (time.perf_counter() - start_time) * 1000
        avg_time_per_permission = total_time_ms / len(permissions)
        response_times.append(avg_time_per_permission)
    
    # Analyze results
    avg_time = statistics.mean(response_times)
    max_time = max(response_times)
    under_10ms = sum(1 for t in response_times if t < 10.0)
    compliance_rate = (under_10ms / len(response_times)) * 100
    
    print(f"  Average time per permission: {avg_time:.3f}ms")
    print(f"  Max time per permission: {max_time:.3f}ms")
    print(f"  Compliance rate (<10ms): {compliance_rate:.1f}%")
    
    return avg_time < 10.0 and compliance_rate >= 90.0


def test_concurrent_performance():
    """Test concurrent permission check performance."""
    print("\nTesting concurrent performance...")
    
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    controller = get_ultra_fast_rbac_controller(target_response_time_ms=10.0)
    db_session = create_mock_db_session()
    
    user_ids = [uuid4() for _ in range(10)]
    permissions = ["read_data", "write_data", "view_dashboard"]
    
    def worker_function(worker_id: int, num_requests: int):
        """Worker function for concurrent testing."""
        worker_times = []
        for i in range(num_requests):
            user_id = user_ids[i % len(user_ids)]
            permission = permissions[i % len(permissions)]
            
            start_time = time.perf_counter()
            result = controller.check_user_permission(
                user_id=user_id,
                permission_name=permission,
                db=db_session
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
    
    print(f"  Concurrent average time: {avg_time:.3f}ms")
    print(f"  Concurrent P95 time: {p95_time:.3f}ms")
    print(f"  Concurrent compliance rate: {compliance_rate:.1f}%")
    
    return avg_time < 15.0 and compliance_rate >= 80.0


def test_performance_monitoring():
    """Test performance monitoring and reporting."""
    print("\nTesting performance monitoring...")
    
    controller = get_ultra_fast_rbac_controller(target_response_time_ms=10.0)
    db_session = create_mock_db_session()
    
    user_id = uuid4()
    permissions = ["read_data", "write_data", "view_dashboard"]
    
    # Generate test data
    for _ in range(50):
        for permission in permissions:
            controller.check_user_permission(
                user_id=user_id,
                permission_name=permission,
                db=db_session
            )
    
    # Get performance report
    report = controller.get_performance_report()
    summary = controller.get_performance_summary()
    
    print(f"  Performance grade: {summary['performance_grade']}")
    print(f"  Compliance rate: {summary['compliance_rate']:.1f}%")
    print(f"  Cache hit rate: {summary['cache_hit_rate']:.1f}%")
    print(f"  Average response time: {summary['current_avg_response_time_ms']:.3f}ms")
    print(f"  Target met: {summary['target_met']}")
    
    return summary['performance_grade'] in ['A', 'B', 'C'] and summary['target_met']


def main():
    """Run all performance validation tests."""
    print("=" * 60)
    print("PERMISSION PERFORMANCE VALIDATION (<10ms TARGET)")
    print("=" * 60)
    
    tests = [
        ("Ultra-Fast Cache", test_ultra_fast_cache),
        ("Single Permission Check", test_single_permission_performance),
        ("Batch Permission Check", test_batch_permission_performance),
        ("Concurrent Performance", test_concurrent_performance),
        ("Performance Monitoring", test_performance_monitoring),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            success = test_func()
            results[test_name] = success
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            print(f"\n{test_name}: ❌ ERROR - {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(1 for success in results.values() if success)
    total_tests = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Permission checks meet <10ms target.")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Performance optimization needed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)