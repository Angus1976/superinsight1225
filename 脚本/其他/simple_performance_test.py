#!/usr/bin/env python3
"""
Simple performance test to measure permission check optimization.
"""

import time
import statistics
import sys
import os
from uuid import uuid4
from unittest.mock import Mock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.security.rbac_controller_optimized import OptimizedRBACController
from src.security.permission_performance_optimizer import OptimizationConfig
from src.security.models import UserRole


def test_permission_performance():
    """Test permission check performance with mocked database."""
    print("Testing Permission Check Performance")
    print("=" * 50)
    
    # Setup optimized controller
    config = OptimizationConfig(
        target_response_time_ms=10.0,
        cache_preload_enabled=True,
        query_optimization_enabled=True,
        batch_processing_enabled=True,
        memory_cache_size=1000
    )
    
    controller = OptimizedRBACController(optimization_config=config)
    
    # Mock database and user
    mock_db = Mock()
    user_id = uuid4()
    tenant_id = "test_tenant"
    
    mock_user = Mock()
    mock_user.id = user_id
    mock_user.tenant_id = tenant_id
    mock_user.is_active = True
    mock_user.role = UserRole.VIEWER
    
    # Mock the get_user_by_id method
    controller.get_user_by_id = Mock(return_value=mock_user)
    
    # Mock database query to simulate fast database response
    mock_result = Mock()
    mock_result.fetchone.return_value = Mock(has_permission=True)
    mock_db.execute.return_value = mock_result
    
    print("1. Testing cold cache performance (database queries)...")
    
    # Test cold cache (first-time checks that hit database)
    cold_times = []
    permissions = ["read_data", "write_data", "delete_data", "manage_users", "view_reports"]
    
    for i in range(10):
        # Clear cache to ensure cold start
        controller.clear_all_permission_cache()
        
        permission = permissions[i % len(permissions)]
        
        start_time = time.perf_counter()
        result = controller.check_user_permission(
            user_id=user_id,
            permission_name=permission,
            db=mock_db
        )
        end_time = time.perf_counter()
        
        response_time_ms = (end_time - start_time) * 1000
        cold_times.append(response_time_ms)
        print(f"  Cold check {i+1} ({permission}): {response_time_ms:.3f}ms")
    
    avg_cold_time = statistics.mean(cold_times)
    print(f"  Average cold time: {avg_cold_time:.3f}ms")
    
    print("\n2. Testing warm cache performance (cached responses)...")
    
    # Test warm cache (subsequent checks that hit cache)
    warm_times = []
    
    for i in range(100):
        permission = permissions[i % len(permissions)]
        
        start_time = time.perf_counter()
        result = controller.check_user_permission(
            user_id=user_id,
            permission_name=permission,
            db=mock_db
        )
        end_time = time.perf_counter()
        
        response_time_ms = (end_time - start_time) * 1000
        warm_times.append(response_time_ms)
        
        if i < 10:  # Show first 10 for visibility
            print(f"  Warm check {i+1} ({permission}): {response_time_ms:.3f}ms")
    
    avg_warm_time = statistics.mean(warm_times)
    p95_warm_time = statistics.quantiles(warm_times, n=20)[18] if len(warm_times) > 1 else warm_times[0]
    p99_warm_time = statistics.quantiles(warm_times, n=100)[98] if len(warm_times) > 1 else warm_times[0]
    max_warm_time = max(warm_times)
    min_warm_time = min(warm_times)
    
    under_10ms = sum(1 for t in warm_times if t < 10.0)
    under_5ms = sum(1 for t in warm_times if t < 5.0)
    under_1ms = sum(1 for t in warm_times if t < 1.0)
    
    compliance_10ms = (under_10ms / len(warm_times)) * 100
    compliance_5ms = (under_5ms / len(warm_times)) * 100
    compliance_1ms = (under_1ms / len(warm_times)) * 100
    
    print(f"  Average warm time: {avg_warm_time:.3f}ms")
    print(f"  P95 warm time: {p95_warm_time:.3f}ms")
    print(f"  P99 warm time: {p99_warm_time:.3f}ms")
    print(f"  Min warm time: {min_warm_time:.3f}ms")
    print(f"  Max warm time: {max_warm_time:.3f}ms")
    
    print("\n3. Testing batch performance...")
    
    # Test batch performance
    batch_times = []
    batch_permissions = permissions[:3]  # Test with 3 permissions
    
    for i in range(20):
        start_time = time.perf_counter()
        results = controller.batch_check_permissions(
            user_id=user_id,
            permissions=batch_permissions,
            db=mock_db
        )
        end_time = time.perf_counter()
        
        total_time_ms = (end_time - start_time) * 1000
        avg_time_per_perm = total_time_ms / len(batch_permissions)
        batch_times.append(avg_time_per_perm)
        
        if i < 5:  # Show first 5 for visibility
            print(f"  Batch {i+1}: {total_time_ms:.3f}ms total, {avg_time_per_perm:.3f}ms per permission")
    
    avg_batch_time = statistics.mean(batch_times)
    
    print(f"  Average time per permission in batch: {avg_batch_time:.3f}ms")
    
    print("\n4. Cache statistics...")
    cache_stats = controller.get_cache_statistics()
    print(f"  Cache system: {cache_stats.get('cache_system', 'unknown')}")
    print(f"  Memory cache size: {cache_stats.get('memory_cache_size', 0)}")
    print(f"  Legacy cache size: {cache_stats.get('legacy_cache_size', 0)}")
    
    # Performance summary
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    print(f"Cold cache average: {avg_cold_time:.3f}ms")
    print(f"Warm cache average: {avg_warm_time:.3f}ms")
    print(f"Warm cache P95: {p95_warm_time:.3f}ms")
    print(f"Warm cache P99: {p99_warm_time:.3f}ms")
    print(f"Batch average per permission: {avg_batch_time:.3f}ms")
    print()
    print("Compliance Rates:")
    print(f"  <10ms: {compliance_10ms:.1f}% ({under_10ms}/{len(warm_times)})")
    print(f"  <5ms:  {compliance_5ms:.1f}% ({under_5ms}/{len(warm_times)})")
    print(f"  <1ms:  {compliance_1ms:.1f}% ({under_1ms}/{len(warm_times)})")
    
    # Check if we meet the <10ms requirement
    target_met = (
        avg_warm_time < 10.0 and 
        p95_warm_time < 10.0 and 
        compliance_10ms >= 95.0
    )
    
    print("\n" + "="*60)
    if target_met:
        print("✅ PERFORMANCE TARGET MET!")
        print("   - Average warm cache time < 10ms")
        print("   - P95 time < 10ms")
        print("   - ≥95% compliance rate")
    else:
        print("❌ PERFORMANCE TARGET NOT MET")
        issues = []
        if avg_warm_time >= 10.0:
            issues.append(f"Average time {avg_warm_time:.3f}ms ≥ 10ms target")
        if p95_warm_time >= 10.0:
            issues.append(f"P95 time {p95_warm_time:.3f}ms ≥ 10ms target")
        if compliance_10ms < 95.0:
            issues.append(f"Compliance rate {compliance_10ms:.1f}% < 95% target")
        
        for issue in issues:
            print(f"   - {issue}")
    
    print("="*60)
    
    return target_met


if __name__ == "__main__":
    result = test_permission_performance()
    sys.exit(0 if result else 1)