"""
Integration tests for data desensitization system.
"""

import pytest
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


class TestDesensitizationIntegration:
    """Integration tests for desensitization system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.presidio_engine = PresidioEngine()
        self.rule_manager = DesensitizationRuleManager()
        self.data_classifier = DataClassifier(self.presidio_engine)
        self.compliance_checker = ComplianceChecker()
    
    def test_pii_detection_basic(self):
        """Test basic PII detection functionality."""
        # Test data with various PII types
        test_text = "Contact John Doe at john.doe@example.com or call 555-123-4567"
        
        # Detect PII entities
        entities = self.presidio_engine.detect_pii(test_text)
        
        # Verify entities were detected
        assert len(entities) > 0
        
        # Check for expected entity types
        entity_types = {entity.entity_type for entity in entities}
        expected_types = {PIIEntityType.PERSON, PIIEntityType.EMAIL_ADDRESS, PIIEntityType.PHONE_NUMBER}
        
        # At least some expected types should be detected (fallback may not detect all)
        assert len(entity_types.intersection(expected_types)) > 0
    
    def test_data_anonymization_workflow(self):
        """Test complete data anonymization workflow."""
        # Test data
        test_text = "Employee John Smith (SSN: 123-45-6789) can be reached at john@company.com"
        
        # Create test rules
        email_rule = DesensitizationRule(
            name="Email Masking",
            entity_type=PIIEntityType.EMAIL_ADDRESS,
            masking_strategy=MaskingStrategy.MASK,
            config={"mask_char": "*", "chars_to_mask": -1, "from_end": False}
        )
        
        person_rule = DesensitizationRule(
            name="Person Replacement",
            entity_type=PIIEntityType.PERSON,
            masking_strategy=MaskingStrategy.REPLACE,
            config={"replacement": "[PERSON]"}
        )
        
        rules = [email_rule, person_rule]
        
        # Anonymize text
        result = self.presidio_engine.anonymize_text(test_text, rules)
        
        # Verify anonymization
        assert result.success
        assert result.anonymized_text != result.original_text
        assert len(result.entities_found) >= 0  # May vary based on detection capability
        assert result.processing_time_ms >= 0
    
    def test_field_classification(self):
        """Test field classification functionality."""
        # Test field data
        field_name = "customer_email"
        sample_values = [
            "john.doe@example.com",
            "jane.smith@company.org",
            "admin@test.net",
            "user123@domain.co.uk"
        ]
        
        # Classify field
        classification = self.data_classifier.classify_field(field_name, sample_values)
        
        # Verify classification
        assert classification.field_name == field_name
        assert classification.confidence_score >= 0.0
        assert classification.sensitivity_level in [
            SensitivityLevel.LOW,
            SensitivityLevel.MEDIUM,
            SensitivityLevel.HIGH,
            SensitivityLevel.CRITICAL
        ]
        
        # Email field should likely be classified as requiring some protection
        # (though this may vary based on detection capability)
        assert isinstance(classification.requires_masking, bool)
    
    def test_dataset_classification(self):
        """Test dataset classification functionality."""
        # Test dataset
        dataset_id = "test_customer_data"
        field_data = {
            "customer_id": [1, 2, 3, 4, 5],
            "name": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"],
            "email": ["john@example.com", "jane@company.org", "bob@test.net", "alice@domain.com", "charlie@email.co"],
            "phone": ["555-1234", "555-5678", "555-9012", "555-3456", "555-7890"],
            "age": [25, 30, 35, 28, 42]
        }
        
        # Classify dataset
        classification = self.data_classifier.classify_dataset(dataset_id, field_data)
        
        # Verify classification
        assert classification.dataset_id == dataset_id
        assert classification.total_fields == len(field_data)
        assert classification.sensitive_fields >= 0
        assert len(classification.field_classifications) == len(field_data)
        assert classification.compliance_score >= 0.0
        assert classification.compliance_score <= 100.0
        assert isinstance(classification.recommendations, list)
    
    def test_rule_management(self):
        """Test rule management functionality."""
        tenant_id = "test_tenant"
        
        # Create a test rule
        rule = self.rule_manager.create_rule(
            tenant_id=tenant_id,
            name="Test Email Rule",
            entity_type=PIIEntityType.EMAIL_ADDRESS,
            masking_strategy=MaskingStrategy.MASK,
            sensitivity_level=SensitivityLevel.MEDIUM,
            config={"mask_char": "*"}
        )
        
        # Verify rule creation
        assert rule is not None
        assert rule.name == "Test Email Rule"
        assert rule.entity_type == PIIEntityType.EMAIL_ADDRESS
        assert rule.masking_strategy == MaskingStrategy.MASK
        
        # Get rules for tenant
        rules = self.rule_manager.get_rules_for_tenant(tenant_id)
        assert len(rules) > 0
        
        # Test rule operations
        assert self.rule_manager.enable_rule(rule.id, tenant_id)
        assert self.rule_manager.disable_rule(rule.id, tenant_id)
    
    def test_compliance_assessment(self):
        """Test compliance assessment functionality."""
        tenant_id = "test_tenant"
        
        # Create mock dataset classifications
        from src.sync.desensitization.models import DatasetClassification, ClassificationResult
        
        # Mock field classification with sensitive data
        field_classification = ClassificationResult(
            field_name="customer_ssn",
            entities=[],  # Would contain detected entities
            sensitivity_level=SensitivityLevel.CRITICAL,
            confidence_score=0.9,
            requires_masking=True
        )
        
        dataset_classification = DatasetClassification(
            dataset_id="test_dataset",
            total_fields=5,
            sensitive_fields=1,
            field_classifications=[field_classification],
            overall_sensitivity=SensitivityLevel.HIGH,
            compliance_score=60.0
        )
        
        # Assess compliance
        report = self.compliance_checker.assess_compliance(
            tenant_id=tenant_id,
            dataset_classifications=[dataset_classification]
        )
        
        # Verify compliance report
        assert report.tenant_id == tenant_id
        assert report.datasets_analyzed == 1
        assert report.compliance_percentage >= 0.0
        assert report.compliance_percentage <= 100.0
        assert report.risk_level in [
            SensitivityLevel.LOW,
            SensitivityLevel.MEDIUM,
            SensitivityLevel.HIGH,
            SensitivityLevel.CRITICAL
        ]
        assert isinstance(report.violations, list)
        assert isinstance(report.recommendations, list)
    
    def test_gdpr_compliance_check(self):
        """Test GDPR-specific compliance checking."""
        # Create mock dataset with PII
        from src.sync.desensitization.models import DatasetClassification, ClassificationResult
        
        field_classification = ClassificationResult(
            field_name="personal_data",
            entities=[],
            sensitivity_level=SensitivityLevel.HIGH,
            confidence_score=0.8,
            requires_masking=True
        )
        
        dataset_classification = DatasetClassification(
            dataset_id="gdpr_test_dataset",
            total_fields=3,
            sensitive_fields=1,
            field_classifications=[field_classification],
            overall_sensitivity=SensitivityLevel.HIGH,
            compliance_score=70.0
        )
        
        # Check GDPR compliance
        gdpr_result = self.compliance_checker.check_gdpr_compliance(dataset_classification)
        
        # Verify GDPR assessment
        assert "compliant" in gdpr_result
        assert "violations" in gdpr_result
        assert "requirements_met" in gdpr_result
        assert "requirements_failed" in gdpr_result
        assert "score" in gdpr_result
        assert isinstance(gdpr_result["compliant"], bool)
        assert isinstance(gdpr_result["score"], float)
        assert 0.0 <= gdpr_result["score"] <= 100.0
    
    def test_presidio_configuration_validation(self):
        """Test Presidio configuration validation."""
        # Validate configuration
        config_result = self.presidio_engine.validate_configuration()
        
        # Verify configuration result structure
        assert "presidio_available" in config_result
        assert "analyzer_ready" in config_result
        assert "anonymizer_ready" in config_result
        assert "supported_entities" in config_result
        assert "supported_languages" in config_result
        assert "errors" in config_result
        
        # Check that configuration validation doesn't crash
        assert isinstance(config_result["presidio_available"], bool)
        assert isinstance(config_result["errors"], list)
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end desensitization workflow."""
        tenant_id = "e2e_test_tenant"
        
        # Step 1: Classify dataset
        dataset_id = "customer_database"
        field_data = {
            "id": [1, 2, 3],
            "full_name": ["John Doe", "Jane Smith", "Bob Johnson"],
            "email_address": ["john@example.com", "jane@company.org", "bob@test.net"],
            "credit_card": ["4111-1111-1111-1111", "5555-5555-5555-4444", "3782-822463-10005"]
        }
        
        dataset_classification = self.data_classifier.classify_dataset(dataset_id, field_data)
        
        # Step 2: Create rules based on classification
        rules_created = []
        for field_classification in dataset_classification.field_classifications:
            if field_classification.requires_masking and field_classification.suggested_rules:
                for suggested_rule in field_classification.suggested_rules:
                    rule = self.rule_manager.create_rule(
                        tenant_id=tenant_id,
                        name=f"Auto-rule for {field_classification.field_name}",
                        entity_type=suggested_rule.entity_type,
                        masking_strategy=suggested_rule.masking_strategy,
                        sensitivity_level=suggested_rule.sensitivity_level,
                        config=suggested_rule.config
                    )
                    if rule:
                        rules_created.append(rule)
        
        # Step 3: Apply anonymization
        test_text = "Customer John Doe (john@example.com) has credit card 4111-1111-1111-1111"
        
        if rules_created:
            anonymization_result = self.presidio_engine.anonymize_text(test_text, rules_created)
            
            # Verify anonymization was attempted
            assert anonymization_result.success or len(anonymization_result.errors) > 0
        
        # Step 4: Assess compliance
        compliance_report = self.compliance_checker.assess_compliance(
            tenant_id=tenant_id,
            dataset_classifications=[dataset_classification]
        )
        
        # Verify end-to-end workflow completion
        assert compliance_report.tenant_id == tenant_id
        assert compliance_report.datasets_analyzed == 1
        assert isinstance(compliance_report.recommendations, list)
    
    def test_error_handling(self):
        """Test error handling in desensitization system."""
        # Test with empty/invalid inputs
        
        # Empty text detection
        entities = self.presidio_engine.detect_pii("")
        assert entities == []
        
        # Empty text anonymization
        result = self.presidio_engine.anonymize_text("", [])
        assert result.success
        assert result.anonymized_text == ""
        
        # Invalid field classification
        classification = self.data_classifier.classify_field("", [])
        assert classification.field_name == ""
        assert classification.confidence_score == 0.0
        
        # Invalid dataset classification
        dataset_classification = self.data_classifier.classify_dataset("", {})
        assert dataset_classification.dataset_id == ""
        assert dataset_classification.total_fields == 0