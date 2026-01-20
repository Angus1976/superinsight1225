#!/usr/bin/env python3
"""
Optimized Desensitization Performance Test - Measure enhanced performance.
Target: > 1MB/s processing speed with optimizations.
"""

import time
import statistics
import sys
import os
import random
import string
from typing import List, Dict, Any
from uuid import uuid4

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sync.desensitization.optimized_presidio_engine import OptimizedPresidioEngine
from src.sync.desensitization.data_classifier import DataClassifier
from src.sync.desensitization.models import (
    DesensitizationRule, 
    PIIEntityType, 
    MaskingStrategy, 
    SensitivityLevel
)


class OptimizedPerformanceTestData:
    """Generate test data for optimized performance testing."""
    
    @staticmethod
    def generate_text_with_pii(size_kb: int, pii_density: float = 0.1) -> str:
        """Generate text with embedded PII for testing."""
        # Calculate approximate characters needed (1KB ≈ 1024 chars)
        target_chars = size_kb * 1024
        
        # PII patterns to embed
        pii_patterns = [
            "john.doe@example.com",
            "jane.smith@company.org", 
            "admin@test.net",
            "user123@domain.com",
            "555-123-4567",
            "(555) 987-6543",
            "1-800-555-0199",
            "4532-1234-5678-9012",
            "5555-4444-3333-2222",
            "123-45-6789",
            "987-65-4321",
            "192.168.1.100",
            "10.0.0.1",
            "172.16.0.1"
        ]
        
        # Generate base text
        words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog", 
                "data", "processing", "system", "user", "information", "security",
                "privacy", "protection", "analysis", "report", "document", "file",
                "customer", "account", "service", "support", "business", "company",
                "organization", "department", "team", "project", "task", "work"]
        
        text_parts = []
        current_length = 0
        
        while current_length < target_chars:
            # Add some regular text
            sentence_length = random.randint(8, 25)
            sentence = " ".join(random.choices(words, k=sentence_length)) + ". "
            text_parts.append(sentence)
            current_length += len(sentence)
            
            # Add PII based on density
            if random.random() < pii_density:
                pii = random.choice(pii_patterns)
                pii_text = f"Contact: {pii}. "
                text_parts.append(pii_text)
                current_length += len(pii_text)
        
        return "".join(text_parts)[:target_chars]
    
    @staticmethod
    def generate_batch_texts(num_texts: int, size_kb_each: int) -> List[str]:
        """Generate a batch of texts for batch processing tests."""
        return [
            OptimizedPerformanceTestData.generate_text_with_pii(size_kb_each)
            for _ in range(num_texts)
        ]


def test_optimized_pii_detection():
    """Test optimized PII detection performance."""
    print("Testing Optimized PII Detection Performance")
    print("=" * 60)
    
    # Test both parallel and sequential modes
    for parallel_mode in [True, False]:
        mode_name = "Parallel" if parallel_mode else "Sequential"
        print(f"\n{mode_name} Processing Mode:")
        
        engine = OptimizedPresidioEngine(enable_parallel=parallel_mode)
        
        # Test different text sizes
        test_sizes = [1, 10, 50, 100, 500]  # KB
        
        for size_kb in test_sizes:
            print(f"\n  Testing {size_kb}KB text...")
            
            # Generate test text
            test_text = OptimizedPerformanceTestData.generate_text_with_pii(size_kb)
            text_size_bytes = len(test_text.encode('utf-8'))
            
            # Run multiple iterations
            times = []
            entity_counts = []
            for i in range(3):
                start_time = time.perf_counter()
                entities = engine.detect_pii(test_text)
                end_time = time.perf_counter()
                
                processing_time = end_time - start_time
                times.append(processing_time)
                entity_counts.append(len(entities))
            
            avg_time = statistics.mean(times)
            throughput_mbps = (text_size_bytes / (1024 * 1024)) / avg_time
            avg_entities = statistics.mean(entity_counts)
            
            print(f"    Text size: {text_size_bytes:,} bytes ({size_kb}KB)")
            print(f"    Average time: {avg_time:.3f}s")
            print(f"    Throughput: {throughput_mbps:.2f} MB/s")
            print(f"    Entities found: {avg_entities:.0f}")


def test_batch_processing():
    """Test batch processing performance."""
    print("\nTesting Batch Processing Performance")
    print("=" * 60)
    
    engine = OptimizedPresidioEngine(enable_parallel=True)
    
    # Test different batch configurations
    batch_configs = [
        (5, 10),    # 5 texts, 10KB each
        (10, 5),    # 10 texts, 5KB each
        (20, 2),    # 20 texts, 2KB each
    ]
    
    for num_texts, size_kb_each in batch_configs:
        print(f"\nTesting {num_texts} texts of {size_kb_each}KB each...")
        
        # Generate batch texts
        texts = OptimizedPerformanceTestData.generate_batch_texts(num_texts, size_kb_each)
        total_size_bytes = sum(len(text.encode('utf-8')) for text in texts)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        # Test batch detection
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            results = engine.batch_detect_pii(texts)
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            times.append(processing_time)
            
            if i == 0:  # Show results for first iteration
                total_entities = sum(len(entities) for entities in results)
                print(f"  Total entities found: {total_entities}")
        
        avg_time = statistics.mean(times)
        throughput_mbps = total_size_mb / avg_time
        
        print(f"  Total size: {total_size_bytes:,} bytes ({total_size_mb:.2f}MB)")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Throughput: {throughput_mbps:.2f} MB/s")


def test_optimized_anonymization():
    """Test optimized anonymization performance."""
    print("\nTesting Optimized Anonymization Performance")
    print("=" * 60)
    
    engine = OptimizedPresidioEngine(enable_parallel=True)
    
    # Create comprehensive rules
    rules = [
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
            name="Credit Card Hash",
            entity_type=PIIEntityType.CREDIT_CARD,
            masking_strategy=MaskingStrategy.HASH,
            sensitivity_level=SensitivityLevel.CRITICAL,
            confidence_threshold=0.9,
            config={"hash_type": "sha256"},
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
        )
    ]
    
    # Test different text sizes
    test_sizes = [10, 50, 100, 500]  # KB
    
    for size_kb in test_sizes:
        print(f"\nTesting {size_kb}KB text anonymization...")
        
        # Generate test text with higher PII density for anonymization testing
        test_text = OptimizedPerformanceTestData.generate_text_with_pii(size_kb, pii_density=0.15)
        text_size_bytes = len(test_text.encode('utf-8'))
        
        # Run multiple iterations
        times = []
        for i in range(3):
            start_time = time.perf_counter()
            result = engine.anonymize_text(test_text, rules)
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            times.append(processing_time)
            
            if i == 0:  # Show results for first iteration
                print(f"  Success: {result.success}")
                print(f"  Entities found: {len(result.entities_found)}")
                print(f"  Rules applied: {len(result.rules_applied)}")
        
        avg_time = statistics.mean(times)
        throughput_mbps = (text_size_bytes / (1024 * 1024)) / avg_time
        
        print(f"  Text size: {text_size_bytes:,} bytes ({size_kb}KB)")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Throughput: {throughput_mbps:.2f} MB/s")


def test_cache_performance():
    """Test cache performance with repeated patterns."""
    print("\nTesting Cache Performance")
    print("=" * 60)
    
    engine = OptimizedPresidioEngine(enable_parallel=True)
    
    # Generate text with repeated patterns
    base_text = "Contact john.doe@example.com or call 555-123-4567. "
    repeated_text = base_text * 1000  # Repeat pattern 1000 times
    text_size_bytes = len(repeated_text.encode('utf-8'))
    text_size_mb = text_size_bytes / (1024 * 1024)
    
    print(f"Testing repeated patterns ({text_size_mb:.2f}MB)...")
    
    # First run (cold cache)
    print("\nCold cache run:")
    start_time = time.perf_counter()
    entities_cold = engine.detect_pii(repeated_text)
    cold_time = time.perf_counter() - start_time
    cold_throughput = text_size_mb / cold_time
    
    print(f"  Time: {cold_time:.3f}s")
    print(f"  Throughput: {cold_throughput:.2f} MB/s")
    print(f"  Entities found: {len(entities_cold)}")
    
    # Subsequent runs (warm cache)
    print("\nWarm cache runs:")
    warm_times = []
    for i in range(5):
        start_time = time.perf_counter()
        entities_warm = engine.detect_pii(repeated_text)
        warm_time = time.perf_counter() - start_time
        warm_times.append(warm_time)
        
        warm_throughput = text_size_mb / warm_time
        print(f"  Run {i+1}: {warm_time:.3f}s, {warm_throughput:.2f} MB/s")
    
    avg_warm_time = statistics.mean(warm_times)
    avg_warm_throughput = text_size_mb / avg_warm_time
    speedup = cold_time / avg_warm_time
    
    print(f"\nCache Performance Summary:")
    print(f"  Cold cache: {cold_throughput:.2f} MB/s")
    print(f"  Warm cache: {avg_warm_throughput:.2f} MB/s")
    print(f"  Speedup: {speedup:.2f}x")
    
    # Show cache statistics
    stats = engine.get_performance_stats()
    print(f"\nCache Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def test_ultimate_performance():
    """Test ultimate performance with all optimizations."""
    print("\nTesting Ultimate Performance (All Optimizations)")
    print("=" * 60)
    
    engine = OptimizedPresidioEngine(enable_parallel=True)
    
    # Create comprehensive rules
    rules = [
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
        )
    ]
    
    # Test with large text (2MB)
    target_size_mb = 2.0
    target_size_kb = int(target_size_mb * 1024)
    
    print(f"Testing {target_size_mb}MB text processing with all optimizations...")
    
    # Generate large test text
    test_text = OptimizedPerformanceTestData.generate_text_with_pii(target_size_kb, pii_density=0.12)
    text_size_bytes = len(test_text.encode('utf-8'))
    text_size_mb = text_size_bytes / (1024 * 1024)
    
    print(f"Generated text: {text_size_bytes:,} bytes ({text_size_mb:.2f}MB)")
    
    # Test full pipeline multiple times
    times = []
    for i in range(3):
        print(f"\nRun {i+1}:")
        
        start_time = time.perf_counter()
        
        # Step 1: PII Detection
        detection_start = time.perf_counter()
        entities = engine.detect_pii(test_text)
        detection_time = time.perf_counter() - detection_start
        
        # Step 2: Anonymization
        anonymization_start = time.perf_counter()
        result = engine.anonymize_text(test_text, rules, entities)
        anonymization_time = time.perf_counter() - anonymization_start
        
        total_time = time.perf_counter() - start_time
        times.append(total_time)
        
        throughput_mbps = text_size_mb / total_time
        
        print(f"  Detection time: {detection_time:.3f}s")
        print(f"  Anonymization time: {anonymization_time:.3f}s")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Throughput: {throughput_mbps:.2f} MB/s")
        print(f"  Entities found: {len(entities)}")
        print(f"  Success: {result.success}")
    
    # Calculate final metrics
    avg_time = statistics.mean(times)
    avg_throughput = text_size_mb / avg_time
    
    print(f"\nUltimate Performance Results:")
    print(f"  Average processing time: {avg_time:.3f}s")
    print(f"  Average throughput: {avg_throughput:.2f} MB/s")
    
    # Check if we exceed the target significantly
    target_met = avg_throughput > 1.0
    performance_multiplier = avg_throughput / 1.0
    
    print("\n" + "="*60)
    if target_met:
        print("✅ ULTIMATE PERFORMANCE TARGET MET!")
        print(f"   Throughput {avg_throughput:.2f} MB/s > 1.0 MB/s target")
        print(f"   Performance multiplier: {performance_multiplier:.1f}x")
    else:
        print("❌ PERFORMANCE TARGET NOT MET")
        print(f"   Throughput {avg_throughput:.2f} MB/s < 1.0 MB/s target")
    
    print("="*60)
    
    return target_met, avg_throughput


def main():
    """Run all optimized performance tests."""
    print("OPTIMIZED DESENSITIZATION PERFORMANCE TESTING")
    print("="*60)
    
    # Run individual optimization tests
    test_optimized_pii_detection()
    test_batch_processing()
    test_optimized_anonymization()
    test_cache_performance()
    
    # Run ultimate performance test
    target_met, throughput = test_ultimate_performance()
    
    print(f"\nFINAL OPTIMIZED SUMMARY:")
    print(f"Target: > 1.0 MB/s")
    print(f"Achieved: {throughput:.2f} MB/s")
    print(f"Status: {'✅ PASS' if target_met else '❌ FAIL'}")
    print(f"Optimization Level: {'EXCELLENT' if throughput > 10 else 'GOOD' if throughput > 5 else 'BASIC'}")
    
    return target_met


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)