#!/usr/bin/env python3
"""
Final Desensitization Performance Test - Comprehensive validation of > 1MB/s target.

This test validates that the desensitization system achieves the performance requirement
of processing data at speeds greater than 1MB/s consistently across different scenarios.
"""

import time
import statistics
import sys
import os
from typing import List, Dict, Any
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sync.desensitization.performance_optimizer import (
    DesensitizationPerformanceOptimizer,
    PerformanceConfig
)
from src.sync.desensitization.models import (
    DesensitizationRule, 
    PIIEntityType, 
    MaskingStrategy, 
    SensitivityLevel
)


def create_test_rules() -> List[DesensitizationRule]:
    """Create comprehensive test rules for performance testing."""
    return [
        DesensitizationRule(
            id=str(uuid4()),
            name="Email Masking",
            entity_type=PIIEntityType.EMAIL_ADDRESS,
            masking_strategy=MaskingStrategy.MASK,
            sensitivity_level=SensitivityLevel.MEDIUM,
            confidence_threshold=0.7,
            config={"mask_char": "*", "chars_to_mask": -1},
            enabled=True
        ),
        DesensitizationRule(
            id=str(uuid4()),
            name="Phone Redaction",
            entity_type=PIIEntityType.PHONE_NUMBER,
            masking_strategy=MaskingStrategy.REDACT,
            sensitivity_level=SensitivityLevel.HIGH,
            confidence_threshold=0.8,
            config={},
            enabled=True
        ),
        DesensitizationRule(
            id=str(uuid4()),
            name="IP Address Replace",
            entity_type=PIIEntityType.IP_ADDRESS,
            masking_strategy=MaskingStrategy.REPLACE,
            sensitivity_level=SensitivityLevel.MEDIUM,
            confidence_threshold=0.8,
            config={"replacement": "[IP_ADDRESS]"},
            enabled=True
        ),
        DesensitizationRule(
            id=str(uuid4()),
            name="SSN Hash",
            entity_type=PIIEntityType.US_SSN,
            masking_strategy=MaskingStrategy.HASH,
            sensitivity_level=SensitivityLevel.CRITICAL,
            confidence_threshold=0.9,
            config={"hash_type": "sha256"},
            enabled=True
        )
    ]


def generate_realistic_text(size_mb: float, pii_density: float = 0.08) -> str:
    """
    Generate realistic text with embedded PII for performance testing.
    
    Args:
        size_mb: Target size in MB
        pii_density: Density of PII in the text (0.0 to 1.0)
        
    Returns:
        Generated text with PII
    """
    target_chars = int(size_mb * 1024 * 1024)
    
    # Realistic text patterns
    sentences = [
        "The customer service team processed the request efficiently.",
        "Data analysis shows significant improvement in user engagement.",
        "Security protocols have been updated to meet compliance requirements.",
        "The system administrator reviewed the access logs carefully.",
        "Business intelligence reports indicate positive growth trends.",
        "User feedback has been collected and analyzed for improvements.",
        "The development team implemented new features successfully.",
        "Quality assurance testing confirmed system reliability.",
        "Performance metrics demonstrate optimal system operation.",
        "Documentation has been updated to reflect recent changes."
    ]
    
    # PII patterns to embed
    pii_patterns = [
        "john.doe@company.com",
        "jane.smith@example.org",
        "admin@system.net",
        "support@business.com",
        "555-0123",
        "(555) 987-6543",
        "1-800-555-0199",
        "+1-555-123-4567",
        "192.168.1.100",
        "10.0.0.1",
        "172.16.0.50",
        "203.0.113.1",
        "123-45-6789",
        "987-65-4321",
        "456-78-9012"
    ]
    
    text_parts = []
    current_length = 0
    pii_counter = 0
    
    while current_length < target_chars:
        # Add regular sentence
        sentence = sentences[current_length % len(sentences)] + " "
        text_parts.append(sentence)
        current_length += len(sentence)
        
        # Add PII based on density
        if (pii_counter / max(1, len(text_parts))) < pii_density:
            pii = pii_patterns[pii_counter % len(pii_patterns)]
            pii_text = f"Contact information: {pii}. "
            text_parts.append(pii_text)
            current_length += len(pii_text)
            pii_counter += 1
    
    return "".join(text_parts)[:target_chars]


def test_baseline_performance():
    """Test baseline performance with standard configuration."""
    print("Testing Baseline Performance")
    print("=" * 50)
    
    config = PerformanceConfig(
        enable_parallel_processing=True,
        max_worker_threads=4,
        batch_size=10,
        chunk_size_kb=64
    )
    
    optimizer = DesensitizationPerformanceOptimizer(config)
    rules = create_test_rules()
    
    # Test different sizes
    test_sizes = [0.5, 1.0, 2.0, 5.0]  # MB
    
    results = []
    for size_mb in test_sizes:
        print(f"\nTesting {size_mb}MB text...")
        
        # Generate test text
        test_text = generate_realistic_text(size_mb)
        text_size_bytes = len(test_text.encode('utf-8'))
        
        # Run test multiple times
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            result = optimizer.process_large_text(test_text, rules)
            processing_time = time.perf_counter() - start_time
            times.append(processing_time)
            
            if i == 0:  # Show results for first run
                print(f"  Success: {result.success}")
                print(f"  Entities found: {len(result.entities_found)}")
                print(f"  Rules applied: {len(result.rules_applied)}")
        
        avg_time = statistics.mean(times)
        throughput_mbps = (text_size_bytes / (1024 * 1024)) / avg_time
        
        print(f"  Size: {text_size_bytes:,} bytes ({size_mb}MB)")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Throughput: {throughput_mbps:.2f} MB/s")
        print(f"  Target met: {'✅' if throughput_mbps > 1.0 else '❌'}")
        
        results.append({
            'size_mb': size_mb,
            'throughput_mbps': throughput_mbps,
            'target_met': throughput_mbps > 1.0
        })
    
    return results


def test_batch_performance():
    """Test batch processing performance."""
    print("\nTesting Batch Processing Performance")
    print("=" * 50)
    
    config = PerformanceConfig(
        enable_parallel_processing=True,
        max_worker_threads=6,
        batch_size=20
    )
    
    optimizer = DesensitizationPerformanceOptimizer(config)
    rules = create_test_rules()
    
    # Test different batch configurations
    batch_configs = [
        (10, 0.1),  # 10 texts, 0.1MB each = 1MB total
        (5, 0.4),   # 5 texts, 0.4MB each = 2MB total
        (20, 0.05), # 20 texts, 0.05MB each = 1MB total
    ]
    
    results = []
    for num_texts, size_mb_each in batch_configs:
        total_size_mb = num_texts * size_mb_each
        print(f"\nTesting {num_texts} texts of {size_mb_each}MB each (total: {total_size_mb}MB)...")
        
        # Generate batch texts
        texts = [generate_realistic_text(size_mb_each) for _ in range(num_texts)]
        total_bytes = sum(len(text.encode('utf-8')) for text in texts)
        
        # Run batch processing
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            batch_results = optimizer.process_text_batch(texts, rules)
            processing_time = time.perf_counter() - start_time
            times.append(processing_time)
            
            if i == 0:  # Show results for first run
                successful = sum(1 for r in batch_results if r.success)
                total_entities = sum(len(r.entities_found) for r in batch_results)
                print(f"  Successful: {successful}/{len(batch_results)}")
                print(f"  Total entities: {total_entities}")
        
        avg_time = statistics.mean(times)
        throughput_mbps = (total_bytes / (1024 * 1024)) / avg_time
        
        print(f"  Total size: {total_bytes:,} bytes ({total_size_mb}MB)")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Throughput: {throughput_mbps:.2f} MB/s")
        print(f"  Target met: {'✅' if throughput_mbps > 1.0 else '❌'}")
        
        results.append({
            'config': f"{num_texts}x{size_mb_each}MB",
            'total_size_mb': total_size_mb,
            'throughput_mbps': throughput_mbps,
            'target_met': throughput_mbps > 1.0
        })
    
    return results


def test_optimized_performance():
    """Test performance with optimized configuration."""
    print("\nTesting Optimized Performance")
    print("=" * 50)
    
    # Create optimized configuration
    optimizer = DesensitizationPerformanceOptimizer()
    optimized_config = optimizer.optimize_for_throughput()
    
    print(f"Optimized configuration:")
    print(f"  Parallel processing: {optimized_config.enable_parallel_processing}")
    print(f"  Max workers: {optimized_config.max_worker_threads}")
    print(f"  Batch size: {optimized_config.batch_size}")
    print(f"  Chunk size: {optimized_config.chunk_size_kb}KB")
    
    # Create optimizer with optimized config
    optimizer = DesensitizationPerformanceOptimizer(optimized_config)
    rules = create_test_rules()
    
    # Test with large text
    test_size_mb = 3.0
    print(f"\nTesting {test_size_mb}MB text with optimized settings...")
    
    test_text = generate_realistic_text(test_size_mb, pii_density=0.1)
    text_size_bytes = len(test_text.encode('utf-8'))
    
    # Run optimized test
    times = []
    for i in range(5):  # More iterations for better average
        start_time = time.perf_counter()
        result = optimizer.process_large_text(test_text, rules)
        processing_time = time.perf_counter() - start_time
        times.append(processing_time)
        
        if i == 0:
            print(f"  Success: {result.success}")
            print(f"  Entities found: {len(result.entities_found)}")
            print(f"  Rules applied: {len(result.rules_applied)}")
    
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    throughput_avg = (text_size_bytes / (1024 * 1024)) / avg_time
    throughput_best = (text_size_bytes / (1024 * 1024)) / min_time
    
    print(f"  Size: {text_size_bytes:,} bytes ({test_size_mb}MB)")
    print(f"  Average time: {avg_time:.3f}s")
    print(f"  Best time: {min_time:.3f}s")
    print(f"  Worst time: {max_time:.3f}s")
    print(f"  Average throughput: {throughput_avg:.2f} MB/s")
    print(f"  Best throughput: {throughput_best:.2f} MB/s")
    print(f"  Target met: {'✅' if throughput_avg > 1.0 else '❌'}")
    
    # Get performance metrics
    metrics = optimizer.get_performance_metrics()
    print(f"\nPerformance Metrics:")
    print(f"  Total processed: {metrics.total_bytes_processed / (1024*1024):.2f} MB")
    print(f"  Overall throughput: {metrics.throughput_mbps:.2f} MB/s")
    print(f"  Cache hit rate: {metrics.cache_hit_rate:.1%}")
    
    return {
        'throughput_avg': throughput_avg,
        'throughput_best': throughput_best,
        'target_met': throughput_avg > 1.0
    }


def test_stress_performance():
    """Test performance under stress conditions."""
    print("\nTesting Stress Performance")
    print("=" * 50)
    
    config = PerformanceConfig(
        enable_parallel_processing=True,
        max_worker_threads=8,
        batch_size=50,
        chunk_size_kb=256
    )
    
    optimizer = DesensitizationPerformanceOptimizer(config)
    rules = create_test_rules()
    
    # Stress test with very large text
    stress_size_mb = 10.0
    print(f"Stress testing with {stress_size_mb}MB text...")
    
    test_text = generate_realistic_text(stress_size_mb, pii_density=0.15)
    text_size_bytes = len(test_text.encode('utf-8'))
    
    # Single large processing test
    start_time = time.perf_counter()
    result = optimizer.process_large_text(test_text, rules)
    processing_time = time.perf_counter() - start_time
    
    throughput_mbps = (text_size_bytes / (1024 * 1024)) / processing_time
    
    print(f"  Size: {text_size_bytes:,} bytes ({stress_size_mb}MB)")
    print(f"  Processing time: {processing_time:.3f}s")
    print(f"  Throughput: {throughput_mbps:.2f} MB/s")
    print(f"  Success: {result.success}")
    print(f"  Entities found: {len(result.entities_found)}")
    print(f"  Target met: {'✅' if throughput_mbps > 1.0 else '❌'}")
    
    return {
        'throughput_mbps': throughput_mbps,
        'target_met': throughput_mbps > 1.0
    }


def run_comprehensive_benchmark():
    """Run comprehensive benchmark suite."""
    print("\nRunning Comprehensive Benchmark Suite")
    print("=" * 60)
    
    optimizer = DesensitizationPerformanceOptimizer()
    rules = create_test_rules()
    
    # Run built-in benchmark
    benchmark_results = optimizer.benchmark_performance(
        test_sizes_mb=[0.5, 1.0, 2.0, 5.0],
        rules=rules
    )
    
    print("Benchmark Results:")
    print(f"Configuration: {benchmark_results['test_configuration']}")
    print()
    
    all_passed = True
    for result in benchmark_results['results']:
        size_mb = result['size_mb']
        throughput = result['throughput_mbps']
        target_met = result['target_met']
        
        print(f"  {size_mb}MB: {throughput:.2f} MB/s {'✅' if target_met else '❌'}")
        
        if not target_met:
            all_passed = False
    
    return all_passed, benchmark_results


def main():
    """Run all performance tests and validate > 1MB/s target."""
    print("FINAL DESENSITIZATION PERFORMANCE VALIDATION")
    print("=" * 60)
    print("Target: Achieve > 1.0 MB/s processing speed consistently")
    print("=" * 60)
    
    # Run all test suites
    baseline_results = test_baseline_performance()
    batch_results = test_batch_performance()
    optimized_result = test_optimized_performance()
    stress_result = test_stress_performance()
    benchmark_passed, benchmark_results = run_comprehensive_benchmark()
    
    # Analyze results
    print("\n" + "=" * 60)
    print("FINAL PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    # Check baseline results
    baseline_passed = all(r['target_met'] for r in baseline_results)
    baseline_avg_throughput = statistics.mean([r['throughput_mbps'] for r in baseline_results])
    
    # Check batch results
    batch_passed = all(r['target_met'] for r in batch_results)
    batch_avg_throughput = statistics.mean([r['throughput_mbps'] for r in batch_results])
    
    # Overall assessment
    all_tests_passed = (
        baseline_passed and
        batch_passed and
        optimized_result['target_met'] and
        stress_result['target_met'] and
        benchmark_passed
    )
    
    print(f"Baseline Performance: {'✅ PASS' if baseline_passed else '❌ FAIL'}")
    print(f"  Average throughput: {baseline_avg_throughput:.2f} MB/s")
    
    print(f"Batch Performance: {'✅ PASS' if batch_passed else '❌ FAIL'}")
    print(f"  Average throughput: {batch_avg_throughput:.2f} MB/s")
    
    print(f"Optimized Performance: {'✅ PASS' if optimized_result['target_met'] else '❌ FAIL'}")
    print(f"  Average throughput: {optimized_result['throughput_avg']:.2f} MB/s")
    print(f"  Best throughput: {optimized_result['throughput_best']:.2f} MB/s")
    
    print(f"Stress Performance: {'✅ PASS' if stress_result['target_met'] else '❌ FAIL'}")
    print(f"  Throughput: {stress_result['throughput_mbps']:.2f} MB/s")
    
    print(f"Comprehensive Benchmark: {'✅ PASS' if benchmark_passed else '❌ FAIL'}")
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 SUCCESS: ALL PERFORMANCE TARGETS MET!")
        print("✅ Desensitization processing speed > 1.0 MB/s achieved")
        print("✅ Performance validated across multiple scenarios")
        print("✅ System ready for production workloads")
        
        # Calculate overall performance multiplier
        all_throughputs = (
            [r['throughput_mbps'] for r in baseline_results] +
            [r['throughput_mbps'] for r in batch_results] +
            [optimized_result['throughput_avg']] +
            [stress_result['throughput_mbps']]
        )
        avg_overall_throughput = statistics.mean(all_throughputs)
        performance_multiplier = avg_overall_throughput / 1.0
        
        print(f"📊 Overall average throughput: {avg_overall_throughput:.2f} MB/s")
        print(f"📈 Performance multiplier: {performance_multiplier:.1f}x target")
        
    else:
        print("❌ FAILURE: Performance targets not consistently met")
        print("⚠️  Additional optimization required")
    
    print("=" * 60)
    
    return all_tests_passed


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)