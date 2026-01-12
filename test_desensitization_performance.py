#!/usr/bin/env python3
"""
Desensitization Performance Test - Measure and optimize data processing speed.
Target: > 1MB/s processing speed for data desensitization.
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

from src.sync.desensitization.presidio_engine import PresidioEngine
from src.sync.desensitization.data_classifier import DataClassifier
from src.sync.desensitization.models import (
    DesensitizationRule, 
    PIIEntityType, 
    MaskingStrategy, 
    SensitivityLevel
)


class PerformanceTestData:
    """Generate test data for performance testing."""
    
    @staticmethod
    def generate_text_with_pii(size_kb: int) -> str:
        """Generate text with embedded PII for testing."""
        # Calculate approximate characters needed (1KB ≈ 1024 chars)
        target_chars = size_kb * 1024
        
        # PII patterns to embed
        pii_patterns = [
            "john.doe@example.com",
            "jane.smith@company.org", 
            "555-123-4567",
            "(555) 987-6543",
            "4532-1234-5678-9012",
            "123-45-6789",
            "987-65-4321",
            "192.168.1.100",
            "10.0.0.1"
        ]
        
        # Generate base text
        words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog", 
                "data", "processing", "system", "user", "information", "security",
                "privacy", "protection", "analysis", "report", "document", "file"]
        
        text_parts = []
        current_length = 0
        
        while current_length < target_chars:
            # Add some regular text
            sentence_length = random.randint(10, 30)
            sentence = " ".join(random.choices(words, k=sentence_length)) + ". "
            text_parts.append(sentence)
            current_length += len(sentence)
            
            # Occasionally add PII
            if random.random() < 0.1:  # 10% chance to add PII
                pii = random.choice(pii_patterns)
                text_parts.append(f"Contact: {pii}. ")
                current_length += len(f"Contact: {pii}. ")
        
        return "".join(text_parts)[:target_chars]
    
    @staticmethod
    def generate_dataset(num_fields: int, samples_per_field: int) -> Dict[str, List[Any]]:
        """Generate a dataset for classification testing."""
        field_data = {}
        
        field_types = [
            ("email", ["user@example.com", "admin@company.org", "test@domain.net"]),
            ("phone", ["555-1234", "(555) 987-6543", "1-800-555-0199"]),
            ("name", ["John Doe", "Jane Smith", "Bob Johnson"]),
            ("address", ["123 Main St", "456 Oak Ave", "789 Pine Rd"]),
            ("id", ["12345", "67890", "54321"]),
            ("description", ["Product description", "User notes", "System info"])
        ]
        
        for i in range(num_fields):
            field_type, sample_values = random.choice(field_types)
            field_name = f"{field_type}_{i}"
            
            # Generate samples with some variation
            field_samples = []
            for j in range(samples_per_field):
                base_value = random.choice(sample_values)
                # Add some variation
                if field_type in ["email", "phone"]:
                    field_samples.append(base_value)
                else:
                    field_samples.append(f"{base_value}_{j}")
            
            field_data[field_name] = field_samples
        
        return field_data


def test_pii_detection_performance():
    """Test PII detection performance."""
    print("Testing PII Detection Performance")
    print("=" * 50)
    
    engine = PresidioEngine()
    
    # Test different text sizes
    test_sizes = [1, 5, 10, 50, 100]  # KB
    
    for size_kb in test_sizes:
        print(f"\nTesting {size_kb}KB text...")
        
        # Generate test text
        test_text = PerformanceTestData.generate_text_with_pii(size_kb)
        text_size_bytes = len(test_text.encode('utf-8'))
        
        # Run multiple iterations
        times = []
        for i in range(5):
            start_time = time.perf_counter()
            entities = engine.detect_pii(test_text)
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            times.append(processing_time)
            
            if i == 0:  # Show results for first iteration
                print(f"  Found {len(entities)} PII entities")
        
        avg_time = statistics.mean(times)
        throughput_mbps = (text_size_bytes / (1024 * 1024)) / avg_time
        
        print(f"  Text size: {text_size_bytes:,} bytes ({size_kb}KB)")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Throughput: {throughput_mbps:.2f} MB/s")


def test_anonymization_performance():
    """Test anonymization performance."""
    print("\nTesting Anonymization Performance")
    print("=" * 50)
    
    engine = PresidioEngine()
    
    # Create test rules
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
        )
    ]
    
    # Test different text sizes
    test_sizes = [1, 5, 10, 50, 100]  # KB
    
    for size_kb in test_sizes:
        print(f"\nTesting {size_kb}KB text anonymization...")
        
        # Generate test text
        test_text = PerformanceTestData.generate_text_with_pii(size_kb)
        text_size_bytes = len(test_text.encode('utf-8'))
        
        # Run multiple iterations
        times = []
        for i in range(5):
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


def test_classification_performance():
    """Test data classification performance."""
    print("\nTesting Data Classification Performance")
    print("=" * 50)
    
    classifier = DataClassifier()
    
    # Test different dataset sizes
    test_configs = [
        (10, 50),   # 10 fields, 50 samples each
        (50, 100),  # 50 fields, 100 samples each
        (100, 200), # 100 fields, 200 samples each
    ]
    
    for num_fields, samples_per_field in test_configs:
        print(f"\nTesting {num_fields} fields with {samples_per_field} samples each...")
        
        # Generate test dataset
        field_data = PerformanceTestData.generate_dataset(num_fields, samples_per_field)
        
        # Calculate approximate data size
        total_samples = num_fields * samples_per_field
        avg_sample_size = 20  # Approximate bytes per sample
        data_size_bytes = total_samples * avg_sample_size
        
        # Run classification
        times = []
        for i in range(3):  # Fewer iterations for larger datasets
            start_time = time.perf_counter()
            result = classifier.classify_dataset(
                dataset_id=f"test_dataset_{i}",
                field_data=field_data,
                max_samples_per_field=min(samples_per_field, 100)
            )
            end_time = time.perf_counter()
            
            processing_time = end_time - start_time
            times.append(processing_time)
            
            if i == 0:  # Show results for first iteration
                print(f"  Total fields: {result.total_fields}")
                print(f"  Sensitive fields: {result.sensitive_fields}")
                print(f"  Overall sensitivity: {result.overall_sensitivity.value}")
        
        avg_time = statistics.mean(times)
        throughput_mbps = (data_size_bytes / (1024 * 1024)) / avg_time
        
        print(f"  Data size: ~{data_size_bytes:,} bytes")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Throughput: {throughput_mbps:.2f} MB/s")


def test_overall_performance():
    """Test overall desensitization pipeline performance."""
    print("\nTesting Overall Pipeline Performance")
    print("=" * 50)
    
    # Test with 1MB of text data
    target_size_mb = 1.0
    target_size_kb = int(target_size_mb * 1024)
    
    print(f"Testing {target_size_mb}MB text processing...")
    
    engine = PresidioEngine()
    
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
    
    # Generate 1MB test text
    test_text = PerformanceTestData.generate_text_with_pii(target_size_kb)
    text_size_bytes = len(test_text.encode('utf-8'))
    text_size_mb = text_size_bytes / (1024 * 1024)
    
    print(f"Generated text: {text_size_bytes:,} bytes ({text_size_mb:.2f}MB)")
    
    # Test full pipeline
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
    
    print(f"\nFinal Results:")
    print(f"  Average processing time: {avg_time:.3f}s")
    print(f"  Average throughput: {avg_throughput:.2f} MB/s")
    
    # Check if we meet the >1MB/s target
    target_met = avg_throughput > 1.0
    
    print("\n" + "="*60)
    if target_met:
        print("✅ PERFORMANCE TARGET MET!")
        print(f"   Throughput {avg_throughput:.2f} MB/s > 1.0 MB/s target")
    else:
        print("❌ PERFORMANCE TARGET NOT MET")
        print(f"   Throughput {avg_throughput:.2f} MB/s < 1.0 MB/s target")
        print("   Optimization needed!")
    
    print("="*60)
    
    return target_met, avg_throughput


def main():
    """Run all performance tests."""
    print("DESENSITIZATION PERFORMANCE TESTING")
    print("="*60)
    
    # Run individual component tests
    test_pii_detection_performance()
    test_anonymization_performance()
    test_classification_performance()
    
    # Run overall performance test
    target_met, throughput = test_overall_performance()
    
    print(f"\nFINAL SUMMARY:")
    print(f"Target: > 1.0 MB/s")
    print(f"Achieved: {throughput:.2f} MB/s")
    print(f"Status: {'✅ PASS' if target_met else '❌ FAIL'}")
    
    return target_met


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)