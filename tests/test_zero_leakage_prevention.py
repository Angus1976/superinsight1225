"""
Tests for Zero Sensitive Data Leakage Prevention System

Comprehensive test suite for the zero leakage prevention system,
covering detection, prevention, and response capabilities.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

from src.security.zero_leakage_prevention import (
    ZeroLeakagePreventionSystem,
    LeakageDetectionResult,
    LeakageRiskLevel,
    LeakageDetectionMethod,
    LeakagePreventionPolicy
)


@pytest.fixture
def zero_leakage_system():
    """Create a zero leakage prevention system for testing."""
    system = ZeroLeakagePreventionSystem()
    
    # Mock external dependencies
    system.audit_service = AsyncMock()
    system.alert_manager = AsyncMock()
    system.quality_monitor = AsyncMock()
    
    return system


@pytest.fixture
def sample_sensitive_data():
    """Sample sensitive data for testing."""
    return {
        "credit_card": "4532-1234-5678-9012",
        "ssn": "123-45-6789",
        "email": "john.doe@example.com",
        "phone": "+1-555-123-4567",
        "api_key": "sk-1234567890abcdef1234567890abcdef12345678",
        "mixed_text": "Contact John at john.doe@example.com or call 555-123-4567. CC: 4532123456789012"
    }


@pytest.fixture
def sample_safe_data():
    """Sample safe data for testing."""
    return {
        "name": "John Doe",
        "company": "Example Corp",
        "description": "This is a sample description without sensitive information",
        "numbers": "12345",
        "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
    }


class TestZeroLeakagePreventionSystem:
    """Test cases for the zero leakage prevention system."""
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, zero_leakage_system):
        """Test system initialization and configuration."""
        system = zero_leakage_system
        
        # Check initialization
        assert system.monitoring_enabled is True
        assert system.real_time_blocking is True
        assert system.auto_quarantine is True
        
        # Check pattern initialization
        assert "credit_card" in system.sensitive_patterns
        assert "email" in system.sensitive_patterns
        assert "api_key" in system.sensitive_patterns
        
        # Check entropy thresholds
        assert "high_entropy" in system.entropy_thresholds
        assert system.entropy_thresholds["high_entropy"] > 0
    
    @pytest.mark.asyncio
    async def test_scan_credit_card_detection(self, zero_leakage_system, sample_sensitive_data):
        """Test detection of credit card numbers."""
        system = zero_leakage_system
        
        result = await system.scan_for_leakage(
            data=sample_sensitive_data["credit_card"],
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        assert result.has_leakage is True
        assert result.risk_level in [LeakageRiskLevel.HIGH, LeakageRiskLevel.MEDIUM]
        assert len(result.detected_entities) > 0
        assert any("credit_card" in entity.get("type", "") for entity in result.detected_entities)
        assert result.confidence_score > 0.5
    
    @pytest.mark.asyncio
    async def test_scan_ssn_detection(self, zero_leakage_system, sample_sensitive_data):
        """Test detection of Social Security Numbers."""
        system = zero_leakage_system
        
        result = await system.scan_for_leakage(
            data=sample_sensitive_data["ssn"],
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        assert result.has_leakage is True
        assert result.risk_level in [LeakageRiskLevel.HIGH, LeakageRiskLevel.MEDIUM]
        assert len(result.detected_entities) > 0
        assert any("ssn" in entity.get("type", "") for entity in result.detected_entities)
    
    @pytest.mark.asyncio
    async def test_scan_email_detection(self, zero_leakage_system, sample_sensitive_data):
        """Test detection of email addresses."""
        system = zero_leakage_system
        
        result = await system.scan_for_leakage(
            data=sample_sensitive_data["email"],
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        assert result.has_leakage is True
        assert len(result.detected_entities) > 0
        assert any("email" in entity.get("type", "") for entity in result.detected_entities)
    
    @pytest.mark.asyncio
    async def test_scan_api_key_detection(self, zero_leakage_system, sample_sensitive_data):
        """Test detection of API keys."""
        system = zero_leakage_system
        
        result = await system.scan_for_leakage(
            data=sample_sensitive_data["api_key"],
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        assert result.has_leakage is True
        assert result.risk_level in [LeakageRiskLevel.HIGH, LeakageRiskLevel.CRITICAL]
        assert len(result.detected_entities) > 0
        assert any("api_key" in entity.get("type", "") for entity in result.detected_entities)
    
    @pytest.mark.asyncio
    async def test_scan_mixed_content(self, zero_leakage_system, sample_sensitive_data):
        """Test detection in mixed content with multiple sensitive items."""
        system = zero_leakage_system
        
        result = await system.scan_for_leakage(
            data=sample_sensitive_data["mixed_text"],
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        assert result.has_leakage is True
        assert len(result.detected_entities) >= 2  # Should detect email and phone
        
        # Check for multiple entity types
        entity_types = [entity.get("type", "") for entity in result.detected_entities]
        assert "email" in entity_types or any("email" in t for t in entity_types)
        assert "phone" in entity_types or any("phone" in t for t in entity_types)
    
    @pytest.mark.asyncio
    async def test_scan_safe_data(self, zero_leakage_system, sample_safe_data):
        """Test scanning of safe data without sensitive information."""
        system = zero_leakage_system
        
        result = await system.scan_for_leakage(
            data=sample_safe_data["description"],
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        assert result.has_leakage is False
        assert result.risk_level == LeakageRiskLevel.NONE
        assert len(result.detected_entities) == 0
    
    @pytest.mark.asyncio
    async def test_scan_dictionary_data(self, zero_leakage_system, sample_sensitive_data):
        """Test scanning of dictionary data structures."""
        system = zero_leakage_system
        
        test_dict = {
            "user_email": sample_sensitive_data["email"],
            "user_phone": sample_sensitive_data["phone"],
            "description": "Safe description text"
        }
        
        result = await system.scan_for_leakage(
            data=test_dict,
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        assert result.has_leakage is True
        assert len(result.detected_entities) >= 2  # Email and phone
    
    @pytest.mark.asyncio
    async def test_scan_list_data(self, zero_leakage_system, sample_sensitive_data):
        """Test scanning of list data structures."""
        system = zero_leakage_system
        
        test_list = [
            sample_sensitive_data["email"],
            "Safe text",
            sample_sensitive_data["credit_card"],
            "Another safe text"
        ]
        
        result = await system.scan_for_leakage(
            data=test_list,
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        assert result.has_leakage is True
        assert len(result.detected_entities) >= 2  # Email and credit card
    
    @pytest.mark.asyncio
    async def test_entropy_analysis(self, zero_leakage_system):
        """Test entropy analysis for detecting encrypted/hashed data."""
        system = zero_leakage_system
        
        # High entropy string (simulated encrypted data)
        high_entropy_data = "aB3$kL9#mN2@pQ7&rS5!tU8%vW1^xY4*zA6"
        
        result = await system.scan_for_leakage(
            data=high_entropy_data,
            tenant_id="test_tenant",
            user_id="test_user"
        )
        
        # Should detect high entropy as potential sensitive data
        assert "entropy_analysis" in result.metadata.get("detection_summary", {})
    
    @pytest.mark.asyncio
    async def test_prevention_policy_application(self, zero_leakage_system):
        """Test application of prevention policies."""
        system = zero_leakage_system
        
        # Get default policy
        policy = await system._get_prevention_policy("test_tenant")
        
        assert policy.tenant_id == "test_tenant"
        assert policy.enabled is True
        assert policy.strict_mode is True
        assert policy.auto_block is True
        assert policy.allowed_exposure_ratio == 0.0  # Zero tolerance
    
    @pytest.mark.asyncio
    async def test_export_prevention_blocking(self, zero_leakage_system, sample_sensitive_data):
        """Test export prevention with blocking for high-risk data."""
        system = zero_leakage_system
        
        result = await system.prevent_data_export(
            export_data=sample_sensitive_data["credit_card"],
            tenant_id="test_tenant",
            user_id="test_user",
            export_format="csv"
        )
        
        assert result["blocked"] is True
        assert result["allowed"] is False
        assert result["safe_export_data"] is None
        assert "high" in result["risk_level"].lower() or "critical" in result["risk_level"].lower()
    
    @pytest.mark.asyncio
    async def test_export_prevention_masking(self, zero_leakage_system):
        """Test export prevention with automatic masking for medium-risk data."""
        system = zero_leakage_system
        
        # Mock medium risk detection
        with patch.object(system, 'scan_for_leakage') as mock_scan:
            mock_scan.return_value = LeakageDetectionResult(
                has_leakage=True,
                risk_level=LeakageRiskLevel.MEDIUM,
                confidence_score=0.7,
                detected_entities=[{"type": "email", "confidence": 0.7}],
                leakage_patterns=["email"],
                detection_methods=[LeakageDetectionMethod.PATTERN_MATCHING],
                recommendations=["Apply masking"],
                metadata={}
            )
            
            result = await system.prevent_data_export(
                export_data="Contact: john@example.com",
                tenant_id="test_tenant",
                user_id="test_user",
                export_format="json"
            )
            
            assert result["allowed"] is True
            assert result["masked"] is True
            assert result["safe_export_data"] is not None
    
    @pytest.mark.asyncio
    async def test_export_prevention_safe_data(self, zero_leakage_system, sample_safe_data):
        """Test export prevention with safe data."""
        system = zero_leakage_system
        
        result = await system.prevent_data_export(
            export_data=sample_safe_data["description"],
            tenant_id="test_tenant",
            user_id="test_user",
            export_format="json"
        )
        
        assert result["allowed"] is True
        assert result["blocked"] is False
        assert result["masked"] is False
        assert result["safe_export_data"] == sample_safe_data["description"]
    
    @pytest.mark.asyncio
    async def test_leakage_statistics(self, zero_leakage_system):
        """Test leakage statistics generation."""
        system = zero_leakage_system
        
        # Mock audit service to return sample events
        mock_events = [
            {
                "id": "event1",
                "details": {"has_leakage": True, "risk_level": "high"}
            },
            {
                "id": "event2", 
                "details": {"has_leakage": False, "risk_level": "none"}
            },
            {
                "id": "event3",
                "details": {"has_leakage": True, "risk_level": "medium"}
            }
        ]
        
        system.audit_service.query_audit_events.return_value = mock_events
        
        stats = await system.get_leakage_statistics(
            tenant_id="test_tenant",
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow()
        )
        
        assert stats["total_scans"] == 3
        assert stats["leakage_detected"] == 2
        assert stats["leakage_rate"] == 2/3
        assert stats["zero_leakage_compliance"] == 1/3
    
    @pytest.mark.asyncio
    async def test_error_handling(self, zero_leakage_system):
        """Test error handling in leakage detection."""
        system = zero_leakage_system
        
        # Mock an error in pattern detection
        with patch.object(system, '_detect_patterns', side_effect=Exception("Pattern error")):
            result = await system.scan_for_leakage(
                data="test data",
                tenant_id="test_tenant",
                user_id="test_user"
            )
            
            # Should return error result with high risk (fail-safe)
            assert result.has_leakage is True
            assert result.risk_level == LeakageRiskLevel.HIGH
            assert "error" in result.metadata
    
    @pytest.mark.asyncio
    async def test_whitelist_patterns(self, zero_leakage_system):
        """Test whitelist pattern functionality."""
        system = zero_leakage_system
        
        # Create policy with whitelist
        policy = LeakagePreventionPolicy(
            tenant_id="test_tenant",
            policy_name="test_policy",
            enabled=True,
            strict_mode=False,
            auto_block=False,
            detection_threshold=0.8,
            allowed_exposure_ratio=0.0,
            whitelist_patterns=[r"test@example\.com"],
            blacklist_patterns=[],
            notification_settings={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Cache the policy
        system._policy_cache[f"policy_test_tenant"] = {
            "policy": policy,
            "timestamp": datetime.utcnow()
        }
        
        # Test whitelisted email
        whitelisted_patterns = await system._detect_patterns(
            ["test@example.com"], policy
        )
        
        # Should not detect whitelisted pattern
        assert len(whitelisted_patterns) == 0
    
    @pytest.mark.asyncio
    async def test_blacklist_patterns(self, zero_leakage_system):
        """Test blacklist pattern functionality."""
        system = zero_leakage_system
        
        # Create policy with blacklist
        policy = LeakagePreventionPolicy(
            tenant_id="test_tenant",
            policy_name="test_policy",
            enabled=True,
            strict_mode=True,
            auto_block=True,
            detection_threshold=0.8,
            allowed_exposure_ratio=0.0,
            whitelist_patterns=[],
            blacklist_patterns=[r"secret@.*\.com"],
            notification_settings={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Cache the policy
        system._policy_cache[f"policy_test_tenant"] = {
            "policy": policy,
            "timestamp": datetime.utcnow()
        }
        
        # Test blacklisted email
        blacklisted_patterns = await system._detect_patterns(
            ["secret@company.com"], policy
        )
        
        # Should detect blacklisted pattern with high risk
        assert len(blacklisted_patterns) > 0
        assert blacklisted_patterns[0]["risk_level"] == "high"
    
    @pytest.mark.asyncio
    async def test_risk_level_calculation(self, zero_leakage_system):
        """Test risk level calculation logic."""
        system = zero_leakage_system
        
        policy = LeakagePreventionPolicy(
            tenant_id="test_tenant",
            policy_name="test_policy",
            enabled=True,
            strict_mode=True,
            auto_block=True,
            detection_threshold=0.8,
            allowed_exposure_ratio=0.0,
            whitelist_patterns=[],
            blacklist_patterns=[],
            notification_settings={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Test critical risk
        critical_entities = [{"risk_level": "critical"}]
        risk_level = system._calculate_risk_level(critical_entities, policy)
        assert risk_level == LeakageRiskLevel.CRITICAL
        
        # Test high risk
        high_entities = [{"risk_level": "high"}]
        risk_level = system._calculate_risk_level(high_entities, policy)
        assert risk_level == LeakageRiskLevel.HIGH
        
        # Test no entities
        no_entities = []
        risk_level = system._calculate_risk_level(no_entities, policy)
        assert risk_level == LeakageRiskLevel.NONE
    
    @pytest.mark.asyncio
    async def test_confidence_score_calculation(self, zero_leakage_system):
        """Test confidence score calculation."""
        system = zero_leakage_system
        
        # Test high confidence with multiple methods
        entities = [
            {"confidence": 0.9, "risk_level": "high"},
            {"confidence": 0.8, "risk_level": "high"}
        ]
        methods = [LeakageDetectionMethod.PATTERN_MATCHING, LeakageDetectionMethod.MACHINE_LEARNING]
        
        confidence = system._calculate_confidence_score(entities, methods)
        assert confidence > 0.8
        
        # Test no entities (high confidence in no leakage)
        confidence = system._calculate_confidence_score([], [])
        assert confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_recommendations_generation(self, zero_leakage_system):
        """Test recommendation generation based on detected entities."""
        system = zero_leakage_system
        
        policy = LeakagePreventionPolicy(
            tenant_id="test_tenant",
            policy_name="test_policy",
            enabled=True,
            strict_mode=True,
            auto_block=True,
            detection_threshold=0.8,
            allowed_exposure_ratio=0.0,
            whitelist_patterns=[],
            blacklist_patterns=[],
            notification_settings={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Test critical risk recommendations
        critical_entities = [{"type": "credit_card", "risk_level": "critical"}]
        recommendations = system._generate_recommendations(
            critical_entities, LeakageRiskLevel.CRITICAL, policy
        )
        
        assert any("CRITICAL" in rec for rec in recommendations)
        assert any("credit card" in rec.lower() or "pci dss" in rec.lower() for rec in recommendations)
        
        # Test no leakage recommendations
        no_entities = []
        recommendations = system._generate_recommendations(
            no_entities, LeakageRiskLevel.NONE, policy
        )
        
        assert any("No sensitive data leakage detected" in rec for rec in recommendations)


class TestZeroLeakageAPI:
    """Test cases for the zero leakage API endpoints."""
    
    @pytest.mark.asyncio
    async def test_api_scan_endpoint(self):
        """Test the API scan endpoint functionality."""
        # This would test the actual API endpoints
        # For now, we'll test the core functionality
        
        from src.api.zero_leakage_api import zero_leakage_system
        
        # Mock user and request
        mock_user = Mock()
        mock_user.tenant_id = "test_tenant"
        mock_user.id = "test_user"
        
        # Test data with sensitive information
        test_data = "Contact John at john.doe@example.com"
        
        result = await zero_leakage_system.scan_for_leakage(
            data=test_data,
            tenant_id=mock_user.tenant_id,
            user_id=mock_user.id,
            operation_type="api_test"
        )
        
        assert isinstance(result, LeakageDetectionResult)
        assert result.has_leakage is True
    
    def test_api_models_validation(self):
        """Test API model validation."""
        from src.api.zero_leakage_api import LeakageScanRequest, ExportPreventionRequest
        
        # Test valid scan request
        scan_request = LeakageScanRequest(
            data="test data",
            operation_type="test",
            context={"test": "context"}
        )
        assert scan_request.data == "test data"
        assert scan_request.operation_type == "test"
        
        # Test valid export prevention request
        export_request = ExportPreventionRequest(
            export_data={"key": "value"},
            export_format="json",
            force_export=False
        )
        assert export_request.export_data == {"key": "value"}
        assert export_request.export_format == "json"
        assert export_request.force_export is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])