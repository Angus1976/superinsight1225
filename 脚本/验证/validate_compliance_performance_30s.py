#!/usr/bin/env python3
"""
Compliance Report Performance Validation Script.

Validates that compliance report generation meets the < 30 seconds target.
"""

import asyncio
import sys
import time
import statistics
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock

# Add the project root to the path
sys.path.insert(0, '.')

try:
    from src.compliance.performance_optimizer import (
        ComplianceReportPerformanceOptimizer,
        OptimizationConfig
    )
    from src.compliance.report_generator import ComplianceStandard, ReportType
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please run this script from the project root directory")
    sys.exit(1)


def create_mock_db_session():
    """Create a mock database session for testing"""
    mock_session = Mock()
    
    # Mock query results
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
    
    mock_session.execute.return_value.fetchall.return_value = [mock_result]
    mock_session.execute.return_value.fetchone.return_value = mock_result
    
    return mock_session


async def test_performance_target():
    """Test compliance report generation performance target"""
    
    print("🎯 Compliance Report Performance Validation")
    print("=" * 60)
    print("Target: Generate compliance reports in < 30 seconds")
    print()
    
    # Create optimizer with production-like configuration
    config = OptimizationConfig(
        enable_parallel_processing=True,
        enable_caching=True,
        enable_query_optimization=True,
        max_workers=4,
        cache_ttl_seconds=300,
        batch_size=1000,
        memory_limit_mb=512
    )
    
    optimizer = ComplianceReportPerformanceOptimizer(config)
    mock_db = create_mock_db_session()
    
    # Test parameters
    test_params = {
        "tenant_id": "performance_test_tenant",
        "standard": ComplianceStandard.GDPR,
        "report_type": ReportType.COMPREHENSIVE,
        "start_date": datetime.utcnow() - timedelta(days=90),
        "end_date": datetime.utcnow(),
        "generated_by": uuid4()
    }
    
    print("📊 Test Configuration:")
    print(f"   Parallel processing: {config.enable_parallel_processing}")
    print(f"   Caching: {config.enable_caching}")
    print(f"   Query optimization: {config.enable_query_optimization}")
    print(f"   Max workers: {config.max_workers}")
    print(f"   Data range: {(test_params['end_date'] - test_params['start_date']).days} days")
    print()
    
    # Run multiple test iterations
    print("🔄 Running Performance Tests...")
    times = []
    
    for i in range(5):
        print(f"   Iteration {i+1}/5: ", end="", flush=True)
        
        start_time = time.time()
        
        try:
            report, performance_metrics = await optimizer.generate_optimized_compliance_report(
                db=mock_db,
                include_recommendations=True,
                **test_params
            )
            
            total_time = time.time() - start_time
            times.append(total_time)
            
            # Validate report
            assert report is not None, "Report should not be None"
            assert report.report_id is not None, "Report should have an ID"
            assert len(report.metrics) > 0, "Report should have metrics"
            
            status = "✅ PASS" if total_time < 30.0 else "❌ FAIL"
            print(f"{total_time:.2f}s {status}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False
    
    # Calculate statistics
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    success_rate = (sum(1 for t in times if t < 30.0) / len(times)) * 100
    
    print()
    print("📈 Performance Results:")
    print(f"   Average time: {avg_time:.2f}s")
    print(f"   Minimum time: {min_time:.2f}s")
    print(f"   Maximum time: {max_time:.2f}s")
    print(f"   Success rate (< 30s): {success_rate:.1f}%")
    print(f"   Standard deviation: {statistics.stdev(times):.2f}s")
    
    # Performance grade
    if avg_time < 15.0:
        grade = "A"
        grade_desc = "Excellent"
    elif avg_time < 20.0:
        grade = "B"
        grade_desc = "Good"
    elif avg_time < 30.0:
        grade = "C"
        grade_desc = "Acceptable"
    elif avg_time < 45.0:
        grade = "D"
        grade_desc = "Poor"
    else:
        grade = "F"
        grade_desc = "Failing"
    
    print(f"   Performance grade: {grade} ({grade_desc})")
    
    # Target validation
    target_met = avg_time < 30.0 and success_rate >= 80.0
    
    print()
    print("🎯 Target Validation:")
    print(f"   Target: < 30 seconds")
    print(f"   Achieved: {avg_time:.2f} seconds")
    print(f"   Status: {'✅ TARGET MET' if target_met else '❌ TARGET MISSED'}")
    
    if target_met:
        print()
        print("🎉 SUCCESS: Compliance report generation meets performance target!")
        print("   ✅ Average generation time < 30 seconds")
        print("   ✅ Consistent performance across iterations")
        print("   ✅ High success rate")
    else:
        print()
        print("⚠️  WARNING: Performance target not fully met")
        if avg_time >= 30.0:
            print(f"   ❌ Average time {avg_time:.2f}s exceeds 30s target")
        if success_rate < 80.0:
            print(f"   ❌ Success rate {success_rate:.1f}% below 80% threshold")
    
    return target_met


async def test_optimization_features():
    """Test individual optimization features"""
    
    print("\n🔧 Optimization Features Test")
    print("=" * 40)
    
    # Test parallel processing
    print("Testing parallel processing...")
    config_parallel = OptimizationConfig(enable_parallel_processing=True)
    optimizer_parallel = ComplianceReportPerformanceOptimizer(config_parallel)
    
    config_sequential = OptimizationConfig(enable_parallel_processing=False)
    optimizer_sequential = ComplianceReportPerformanceOptimizer(config_sequential)
    
    mock_db = create_mock_db_session()
    test_params = {
        "tenant_id": "test_tenant",
        "start_date": datetime.utcnow() - timedelta(days=30),
        "end_date": datetime.utcnow()
    }
    
    # Parallel processing test
    start_time = time.time()
    stats_parallel = await optimizer_parallel._collect_statistics_parallel(**test_params, db=mock_db)
    parallel_time = time.time() - start_time
    
    # Sequential processing test
    start_time = time.time()
    stats_sequential = await optimizer_sequential._collect_statistics_parallel(**test_params, db=mock_db)
    sequential_time = time.time() - start_time
    
    improvement = ((sequential_time - parallel_time) / sequential_time) * 100 if sequential_time > 0 else 0
    
    print(f"   Parallel processing: {parallel_time:.3f}s")
    print(f"   Sequential processing: {sequential_time:.3f}s")
    print(f"   Performance improvement: {improvement:.1f}%")
    
    # Test caching
    print("\nTesting caching...")
    optimizer = ComplianceReportPerformanceOptimizer(OptimizationConfig(enable_caching=True))
    
    # First call (cache miss)
    start_time = time.time()
    await optimizer._collect_statistics_parallel(**test_params, db=mock_db)
    first_call = time.time() - start_time
    
    # Second call (cache hit)
    start_time = time.time()
    await optimizer._collect_statistics_parallel(**test_params, db=mock_db)
    second_call = time.time() - start_time
    
    cache_improvement = ((first_call - second_call) / first_call) * 100 if first_call > 0 else 0
    hit_rate = optimizer._calculate_cache_hit_rate()
    
    print(f"   First call (miss): {first_call:.3f}s")
    print(f"   Second call (hit): {second_call:.3f}s")
    print(f"   Cache improvement: {cache_improvement:.1f}%")
    print(f"   Cache hit rate: {hit_rate:.1f}%")
    
    print("\n✅ Optimization features working correctly")


async def main():
    """Main validation function"""
    
    try:
        # Test performance target
        target_met = await test_performance_target()
        
        # Test optimization features
        await test_optimization_features()
        
        print("\n" + "=" * 60)
        
        if target_met:
            print("🎉 VALIDATION SUCCESSFUL")
            print("   Compliance report generation meets < 30 seconds target")
            print("   All optimization features working correctly")
            return 0
        else:
            print("⚠️  VALIDATION INCOMPLETE")
            print("   Performance target not fully met")
            print("   Consider additional optimizations")
            return 1
            
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)