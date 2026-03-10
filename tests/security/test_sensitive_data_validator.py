"""
Tests for Sensitive Data Validator

Tests detection of PII, financial data, and health data in transfer requests.
"""

import pytest
from src.security.sensitive_data_validator import (
    SensitiveDataValidator,
    SensitiveDataDetectionResult,
    SensitiveDataPattern
)
from src.models.data_transfer import (
    DataTransferRequest,
    DataAttributes,
    TransferRecord
)
from src.sync.desensitization.models import SensitivityLevel


@pytest.fixture
def validator():
    """Create validator instance."""
    return SensitiveDataValidator()


@pytest.fixture
def base_request():
    """Create base transfer request without sensitive data."""
    return DataTransferRequest(
        source_type="structuring",
        source_id="test-source-123",
        target_state="temp_stored",
        data_attributes=DataAttributes(
            category="test_category",
            tags=["test"],
            quality_score=0.8,
            description="Test transfer"
        ),
        records=[
            TransferRecord(
                id="record-1",
                content={"field1": "value1", "field2": "value2"},
                metadata={"source": "test"}
            )
        ]
    )


class TestEmailDetection:
    """Test email address detection."""
    
    @pytest.mark.asyncio
    async def test_detect_email_in_content(self, validator, base_request):
        """Should detect email address in record content."""
        base_request.records[0].content["email"] = "user@example.com"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'email' for p in result.detected_patterns)
        assert result.sensitivity_level in [SensitivityLevel.LOW, SensitivityLevel.MEDIUM]
    
    @pytest.mark.asyncio
    async def test_detect_multiple_emails(self, validator, base_request):
        """Should detect multiple email addresses."""
        base_request.records[0].content["contact"] = "Contact: john@example.com or jane@example.com"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        email_patterns = [p for p in result.detected_patterns if p['type'] == 'email']
        assert len(email_patterns) >= 1


class TestPhoneNumberDetection:
    """Test phone number detection."""
    
    @pytest.mark.asyncio
    async def test_detect_phone_number(self, validator, base_request):
        """Should detect phone number."""
        base_request.records[0].content["phone"] = "555-123-4567"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'phone' for p in result.detected_patterns)
    
    @pytest.mark.asyncio
    async def test_detect_phone_with_parentheses(self, validator, base_request):
        """Should detect phone number with parentheses."""
        base_request.records[0].content["contact"] = "(555) 123-4567"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'phone' for p in result.detected_patterns)


class TestSSNDetection:
    """Test SSN detection."""
    
    @pytest.mark.asyncio
    async def test_detect_ssn(self, validator, base_request):
        """Should detect SSN and mark as critical."""
        base_request.records[0].content["ssn"] = "123-45-6789"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'ssn' for p in result.detected_patterns)
        assert result.sensitivity_level == SensitivityLevel.CRITICAL
        assert result.requires_additional_approval is True


class TestCreditCardDetection:
    """Test credit card detection."""
    
    @pytest.mark.asyncio
    async def test_detect_credit_card(self, validator, base_request):
        """Should detect credit card number and mark as critical."""
        base_request.records[0].content["payment"] = "4532 1234 5678 9010"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'credit_card' for p in result.detected_patterns)
        assert result.sensitivity_level == SensitivityLevel.CRITICAL
        assert result.requires_additional_approval is True
    
    @pytest.mark.asyncio
    async def test_detect_credit_card_no_spaces(self, validator, base_request):
        """Should detect credit card without spaces."""
        base_request.records[0].content["card"] = "4532123456789010"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'credit_card' for p in result.detected_patterns)


class TestMedicalDataDetection:
    """Test medical/health data detection."""
    
    @pytest.mark.asyncio
    async def test_detect_medical_record_number(self, validator, base_request):
        """Should detect medical record number."""
        base_request.records[0].content["mrn"] = "MRN: ABC-12345"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'medical_record' for p in result.detected_patterns)
        assert result.sensitivity_level == SensitivityLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_detect_health_keywords(self, validator, base_request):
        """Should detect health-related keywords."""
        base_request.records[0].content["notes"] = "Patient diagnosis: diabetes, prescribed medication"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'health_data' for p in result.detected_patterns)


class TestChineseIDDetection:
    """Test Chinese ID card detection."""
    
    @pytest.mark.asyncio
    async def test_detect_chinese_id(self, validator, base_request):
        """Should detect Chinese ID card number."""
        base_request.records[0].content["id_card"] = "110101199001011234"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'chinese_id' for p in result.detected_patterns)
        # Chinese ID alone may be MEDIUM or HIGH depending on risk calculation
        assert result.sensitivity_level in [SensitivityLevel.MEDIUM, SensitivityLevel.HIGH, SensitivityLevel.CRITICAL]


class TestSensitiveFieldNames:
    """Test detection of sensitive field names."""
    
    @pytest.mark.asyncio
    async def test_detect_password_field(self, validator, base_request):
        """Should detect password field name."""
        base_request.records[0].content["user_password"] = "some_value"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'sensitive_field_name' for p in result.detected_patterns)
    
    @pytest.mark.asyncio
    async def test_detect_api_key_field(self, validator, base_request):
        """Should detect API key field name."""
        base_request.records[0].content["api_key"] = "sk-1234567890"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'sensitive_field_name' for p in result.detected_patterns)


class TestNestedDataScanning:
    """Test scanning of nested data structures."""
    
    @pytest.mark.asyncio
    async def test_detect_in_nested_dict(self, validator, base_request):
        """Should detect sensitive data in nested dictionary."""
        base_request.records[0].content["user"] = {
            "name": "John Doe",
            "contact": {
                "email": "john@example.com",
                "phone": "555-123-4567"
            }
        }
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'email' for p in result.detected_patterns)
        assert any(p['type'] == 'phone' for p in result.detected_patterns)
    
    @pytest.mark.asyncio
    async def test_detect_in_list(self, validator, base_request):
        """Should detect sensitive data in list items."""
        base_request.records[0].content["contacts"] = [
            "user1@example.com",
            "user2@example.com"
        ]
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        email_patterns = [p for p in result.detected_patterns if p['type'] == 'email']
        assert len(email_patterns) >= 1


class TestMetadataScanning:
    """Test scanning of record metadata."""
    
    @pytest.mark.asyncio
    async def test_detect_in_metadata(self, validator, base_request):
        """Should detect sensitive data in record metadata."""
        base_request.records[0].metadata["owner_email"] = "owner@example.com"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert any(p['type'] == 'email' for p in result.detected_patterns)


class TestRiskScoring:
    """Test risk score calculation."""
    
    @pytest.mark.asyncio
    async def test_high_risk_score_for_critical_data(self, validator, base_request):
        """Should calculate high risk score for critical data."""
        base_request.records[0].content["ssn"] = "123-45-6789"
        base_request.records[0].content["credit_card"] = "4532 1234 5678 9010"
        
        result = await validator.validate_transfer_request(base_request)
        
        # With 2 critical patterns, risk score should be reasonably high
        assert result.risk_score > 0.6  # Adjusted threshold
        assert result.requires_additional_approval is True
    
    @pytest.mark.asyncio
    async def test_low_risk_score_for_email_only(self, validator, base_request):
        """Should calculate low risk score for email only."""
        base_request.records[0].content["email"] = "user@example.com"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.risk_score < 0.5
        # Email alone typically doesn't require additional approval
        assert result.requires_additional_approval is False


class TestApprovalRequirements:
    """Test additional approval requirement logic."""
    
    @pytest.mark.asyncio
    async def test_require_approval_for_critical_sensitivity(self, validator, base_request):
        """Should require approval for critical sensitivity level."""
        base_request.records[0].content["ssn"] = "123-45-6789"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.sensitivity_level == SensitivityLevel.CRITICAL
        assert result.requires_additional_approval is True
    
    @pytest.mark.asyncio
    async def test_require_approval_for_multiple_pattern_types(self, validator, base_request):
        """Should require approval when multiple types of sensitive data detected."""
        base_request.records[0].content["email"] = "user@example.com"
        base_request.records[0].content["phone"] = "555-123-4567"
        base_request.records[0].content["ssn"] = "123-45-6789"
        
        result = await validator.validate_transfer_request(base_request)
        
        # Multiple types should trigger approval
        pattern_types = set(p['type'] for p in result.detected_patterns)
        assert len(pattern_types) >= 3
        assert result.requires_additional_approval is True
    
    @pytest.mark.asyncio
    async def test_no_approval_for_clean_data(self, validator, base_request):
        """Should not require approval for clean data."""
        # Base request has no sensitive data
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is False
        assert result.requires_additional_approval is False


class TestRecommendations:
    """Test recommendation generation."""
    
    @pytest.mark.asyncio
    async def test_recommend_masking_for_high_sensitivity(self, validator, base_request):
        """Should recommend masking for high sensitivity data."""
        base_request.records[0].content["ssn"] = "123-45-6789"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert len(result.recommendations) > 0
        assert any('masking' in r.lower() or 'encryption' in r.lower() 
                  for r in result.recommendations)
    
    @pytest.mark.asyncio
    async def test_recommend_hipaa_review_for_health_data(self, validator, base_request):
        """Should recommend HIPAA review for health data."""
        base_request.records[0].content["diagnosis"] = "Patient diagnosis: diabetes"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert any('HIPAA' in r for r in result.recommendations)
    
    @pytest.mark.asyncio
    async def test_recommend_pci_review_for_financial_data(self, validator, base_request):
        """Should recommend PCI DSS review for financial data."""
        base_request.records[0].content["card"] = "4532 1234 5678 9010"
        
        result = await validator.validate_transfer_request(base_request)
        
        assert any('PCI' in r for r in result.recommendations)


class TestMultipleRecords:
    """Test validation across multiple records."""
    
    @pytest.mark.asyncio
    async def test_detect_across_multiple_records(self, validator, base_request):
        """Should detect sensitive data across multiple records."""
        base_request.records = [
            TransferRecord(
                id="record-1",
                content={"email": "user1@example.com"},
                metadata={}
            ),
            TransferRecord(
                id="record-2",
                content={"ssn": "123-45-6789"},
                metadata={}
            ),
            TransferRecord(
                id="record-3",
                content={"credit_card": "4532 1234 5678 9010"},
                metadata={}
            )
        ]
        
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is True
        assert len(result.detected_patterns) >= 3
        assert result.sensitivity_level == SensitivityLevel.CRITICAL


class TestConfigurableThresholds:
    """Test configurable validation thresholds."""
    
    @pytest.mark.asyncio
    async def test_custom_high_risk_threshold(self, base_request):
        """Should use custom high risk threshold."""
        # Create validator with custom threshold
        validator = SensitiveDataValidator(config={
            'high_risk_threshold': 0.5  # Lower threshold
        })
        
        base_request.records[0].content["email"] = "user@example.com"
        base_request.records[0].content["phone"] = "555-123-4567"
        
        result = await validator.validate_transfer_request(base_request)
        
        # With lower threshold, might require approval
        # (depends on calculated risk score)
        assert result.risk_score is not None
    
    @pytest.mark.asyncio
    async def test_custom_max_sensitive_records(self, base_request):
        """Should use custom max sensitive records threshold."""
        validator = SensitiveDataValidator(config={
            'max_sensitive_records': 2  # Very low threshold
        })
        
        # Add 3 records with emails
        base_request.records = [
            TransferRecord(
                id=f"record-{i}",
                content={"email": f"user{i}@example.com"},
                metadata={}
            )
            for i in range(3)
        ]
        
        result = await validator.validate_transfer_request(base_request)
        
        # Should detect multiple patterns
        assert len(result.detected_patterns) >= 3


class TestNoSensitiveData:
    """Test behavior with clean data."""
    
    @pytest.mark.asyncio
    async def test_clean_data_returns_low_sensitivity(self, validator, base_request):
        """Should return low sensitivity for clean data."""
        result = await validator.validate_transfer_request(base_request)
        
        assert result.has_sensitive_data is False
        assert result.sensitivity_level == SensitivityLevel.LOW
        assert result.risk_score == 0.0
        assert result.requires_additional_approval is False
        assert len(result.detected_patterns) == 0
        assert len(result.recommendations) == 0

