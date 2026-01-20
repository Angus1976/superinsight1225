#!/usr/bin/env python3
"""
Demo script for SuperInsight Data Desensitization System.

Demonstrates PII detection, data classification, and anonymization capabilities.
"""

import json
from typing import Dict, List, Any

from src.sync.desensitization import (
    PresidioEngine,
    DesensitizationRuleManager,
    DataClassifier,
    DesensitizationRule,
    PIIEntityType,
    MaskingStrategy,
    SensitivityLevel
)
from src.sync.desensitization.compliance_checker import ComplianceChecker


def demo_pii_detection():
    """Demonstrate PII detection capabilities."""
    print("=" * 60)
    print("PII DETECTION DEMO")
    print("=" * 60)
    
    engine = PresidioEngine()
    
    # Test data with various PII types
    test_texts = [
        "Contact John Doe at john.doe@example.com or call 555-123-4567",
        "Employee SSN: 123-45-6789, Credit Card: 4111-1111-1111-1111",
        "Visit us at 123 Main Street, New York, NY 10001",
        "IP Address: 192.168.1.1, Website: https://example.com"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        entities = engine.detect_pii(text)
        
        if entities:
            print("  Detected PII:")
            for entity in entities:
                print(f"    - {entity.entity_type.value}: '{entity.text}' (confidence: {entity.score:.2f})")
        else:
            print("  No PII detected")


def demo_data_anonymization():
    """Demonstrate data anonymization capabilities."""
    print("\n" + "=" * 60)
    print("DATA ANONYMIZATION DEMO")
    print("=" * 60)
    
    engine = PresidioEngine()
    
    # Create sample rules
    rules = [
        DesensitizationRule(
            name="Email Masking",
            entity_type=PIIEntityType.EMAIL_ADDRESS,
            masking_strategy=MaskingStrategy.MASK,
            config={"mask_char": "*", "chars_to_mask": -1, "from_end": False}
        ),
        DesensitizationRule(
            name="Person Replacement",
            entity_type=PIIEntityType.PERSON,
            masking_strategy=MaskingStrategy.REPLACE,
            config={"replacement": "[PERSON]"}
        ),
        DesensitizationRule(
            name="Phone Masking",
            entity_type=PIIEntityType.PHONE_NUMBER,
            masking_strategy=MaskingStrategy.MASK,
            config={"mask_char": "X", "chars_to_mask": 6, "from_end": True}
        ),
        DesensitizationRule(
            name="Credit Card Redaction",
            entity_type=PIIEntityType.CREDIT_CARD,
            masking_strategy=MaskingStrategy.REDACT
        )
    ]
    
    # Test data
    test_texts = [
        "Employee John Smith can be reached at john.smith@company.com or 555-123-4567",
        "Customer payment: Credit Card 4111-1111-1111-1111, expires 12/25",
        "Contact information: Jane Doe (jane@example.org), Phone: 555-987-6543"
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}:")
        print(f"  Original: {text}")
        
        result = engine.anonymize_text(text, rules)
        
        if result.success:
            print(f"  Anonymized: {result.anonymized_text}")
            print(f"  Rules applied: {', '.join(result.rules_applied)}")
            print(f"  Processing time: {result.processing_time_ms:.2f}ms")
        else:
            print(f"  Anonymization failed: {', '.join(result.errors)}")


def demo_field_classification():
    """Demonstrate field classification capabilities."""
    print("\n" + "=" * 60)
    print("FIELD CLASSIFICATION DEMO")
    print("=" * 60)
    
    classifier = DataClassifier()
    
    # Test fields with different types of data
    test_fields = {
        "customer_email": [
            "john.doe@example.com",
            "jane.smith@company.org", 
            "admin@test.net",
            "user123@domain.co.uk"
        ],
        "phone_number": [
            "555-123-4567",
            "555-987-6543",
            "555-555-1234",
            "555-111-2222"
        ],
        "customer_name": [
            "John Doe",
            "Jane Smith",
            "Bob Johnson",
            "Alice Brown"
        ],
        "product_id": [
            "PROD-001",
            "PROD-002", 
            "PROD-003",
            "PROD-004"
        ],
        "age": [25, 30, 35, 28]
    }
    
    for field_name, sample_values in test_fields.items():
        print(f"\nField: {field_name}")
        print(f"  Sample values: {sample_values[:3]}...")
        
        classification = classifier.classify_field(field_name, sample_values)
        
        print(f"  Sensitivity: {classification.sensitivity_level.value}")
        print(f"  Confidence: {classification.confidence_score:.2f}")
        print(f"  Requires masking: {classification.requires_masking}")
        
        if classification.entities:
            print(f"  Detected entities: {[e.entity_type.value for e in classification.entities]}")


def demo_dataset_classification():
    """Demonstrate dataset classification capabilities."""
    print("\n" + "=" * 60)
    print("DATASET CLASSIFICATION DEMO")
    print("=" * 60)
    
    classifier = DataClassifier()
    
    # Sample customer dataset
    dataset_id = "customer_database"
    field_data = {
        "customer_id": [1, 2, 3, 4, 5],
        "full_name": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"],
        "email_address": ["john@example.com", "jane@company.org", "bob@test.net", "alice@domain.com", "charlie@email.co"],
        "phone_number": ["555-1234", "555-5678", "555-9012", "555-3456", "555-7890"],
        "date_of_birth": ["1990-01-15", "1985-03-22", "1992-07-08", "1988-11-30", "1995-05-12"],
        "credit_score": [750, 680, 720, 800, 650],
        "account_balance": [1500.50, 2300.75, 890.25, 4200.00, 1750.80]
    }
    
    print(f"Dataset: {dataset_id}")
    print(f"Fields: {list(field_data.keys())}")
    
    classification = classifier.classify_dataset(dataset_id, field_data)
    
    print(f"\nDataset Analysis:")
    print(f"  Total fields: {classification.total_fields}")
    print(f"  Sensitive fields: {classification.sensitive_fields}")
    print(f"  Overall sensitivity: {classification.overall_sensitivity.value}")
    print(f"  Compliance score: {classification.compliance_score:.1f}%")
    
    print(f"\nField-by-field analysis:")
    for field_classification in classification.field_classifications:
        print(f"  {field_classification.field_name}:")
        print(f"    Sensitivity: {field_classification.sensitivity_level.value}")
        print(f"    Requires masking: {field_classification.requires_masking}")
    
    if classification.recommendations:
        print(f"\nRecommendations:")
        for rec in classification.recommendations:
            print(f"  - {rec}")


def demo_compliance_assessment():
    """Demonstrate compliance assessment capabilities."""
    print("\n" + "=" * 60)
    print("COMPLIANCE ASSESSMENT DEMO")
    print("=" * 60)
    
    compliance_checker = ComplianceChecker()
    
    # Create mock dataset classification for demo
    from src.sync.desensitization.models import DatasetClassification, ClassificationResult
    
    # Mock sensitive field
    sensitive_field = ClassificationResult(
        field_name="customer_ssn",
        entities=[],
        sensitivity_level=SensitivityLevel.CRITICAL,
        confidence_score=0.9,
        requires_masking=True
    )
    
    # Mock regular field
    regular_field = ClassificationResult(
        field_name="product_category",
        entities=[],
        sensitivity_level=SensitivityLevel.LOW,
        confidence_score=0.1,
        requires_masking=False
    )
    
    dataset_classification = DatasetClassification(
        dataset_id="compliance_test_dataset",
        total_fields=10,
        sensitive_fields=3,
        field_classifications=[sensitive_field, regular_field],
        overall_sensitivity=SensitivityLevel.HIGH,
        compliance_score=65.0
    )
    
    # Assess compliance
    tenant_id = "demo_tenant"
    report = compliance_checker.assess_compliance(
        tenant_id=tenant_id,
        dataset_classifications=[dataset_classification],
        regulation="GDPR"
    )
    
    print(f"Compliance Report for {tenant_id}:")
    print(f"  Regulation: GDPR")
    print(f"  Datasets analyzed: {report.datasets_analyzed}")
    print(f"  Total PII entities: {report.total_pii_entities}")
    print(f"  Compliance percentage: {report.compliance_percentage:.1f}%")
    print(f"  Risk level: {report.risk_level.value}")
    
    if report.violations:
        print(f"\nViolations found:")
        for violation in report.violations[:3]:  # Show first 3
            print(f"  - {violation.get('violation_type', 'Unknown')}: {violation.get('field_name', 'N/A')}")
    
    if report.recommendations:
        print(f"\nRecommendations:")
        for rec in report.recommendations[:3]:  # Show first 3
            print(f"  - {rec}")


def demo_presidio_configuration():
    """Demonstrate Presidio configuration validation."""
    print("\n" + "=" * 60)
    print("PRESIDIO CONFIGURATION DEMO")
    print("=" * 60)
    
    engine = PresidioEngine()
    
    config_result = engine.validate_configuration()
    
    print("Presidio Configuration Status:")
    print(f"  Presidio available: {config_result['presidio_available']}")
    print(f"  Analyzer ready: {config_result['analyzer_ready']}")
    print(f"  Anonymizer ready: {config_result['anonymizer_ready']}")
    
    if config_result['supported_entities']:
        print(f"  Supported entities: {len(config_result['supported_entities'])}")
        print(f"    Examples: {config_result['supported_entities'][:5]}")
    
    if config_result['supported_languages']:
        print(f"  Supported languages: {config_result['supported_languages']}")
    
    if config_result['errors']:
        print(f"  Errors: {len(config_result['errors'])}")
        for error in config_result['errors']:
            print(f"    - {error}")


def main():
    """Run all demos."""
    print("SuperInsight Data Desensitization System Demo")
    print("=" * 60)
    
    try:
        demo_presidio_configuration()
        demo_pii_detection()
        demo_data_anonymization()
        demo_field_classification()
        demo_dataset_classification()
        demo_compliance_assessment()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nKey Features Demonstrated:")
        print("✓ PII Detection with multiple entity types")
        print("✓ Data Anonymization with configurable strategies")
        print("✓ Intelligent Field Classification")
        print("✓ Dataset-level Compliance Assessment")
        print("✓ GDPR/CCPA/HIPAA Compliance Checking")
        print("✓ Fallback Implementation (works without Presidio)")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()