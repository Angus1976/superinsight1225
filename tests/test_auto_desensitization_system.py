"""
Comprehensive tests for automatic desensitization system.

Tests the automatic sensitive data detection and masking functionality
including service, middleware, and API components.
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.security.auto_desensitization_service import AutoDesensitizationService
from src.security.auto_desensitization_middleware import AutoDesensitizationMiddleware
from src.api.auto_desensitization import router as auto_desensitization_router
from src.sync.desensitization.models import (
    PIIEntity, PIIEntityType, DesensitizationRule, 
    MaskingStrategy, SensitivityLevel
)


class TestAutoDesensitizationService:
    """Test automatic desensitization service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = AutoDesensitizationService()
        self.mock_db_session = Mock()
        
        # Mock dependencies
        self.service.presidio_engine = Mock()
        self.service.rule_manager = Mock()
        self.service.validator = Mock()
        self.service.quality_monitor = Mock()
        self.service.alert_manager = Mock()
        self.service.audit_service = Mock()
        
        # Configure async mocks
        self.service.audit_service.log_event = AsyncMock()
        self.service.quality_monitor.record_operation = AsyncMock()
        self.service.alert_manager.send_error_alert = AsyncMock()
        self.service.alert_manager.send_high_volume_alert = AsyncMock()
        self.service.alert_manager.send_quality_alert = AsyncMock()
        self.service.alert_manager.send_processing_alert = AsyncMock()
        
    @pytest.mark.asyncio
    async def test_detect_and_mask_text_data(self):
        """Test automatic detection and masking of text data."""
        # Arrange
        test_text = "My name is John Doe and my email is john.doe@example.com"
        tenant_id = "test_tenant"
        user_id = "test_user"
        
        # Mock detected entities
        mock_entities = [
            PIIEntity(
                entity_type=PIIEntityType.PERSON,
                start=11,
                end=19,
                score=0.9,
                text="John Doe"
            ),
            PIIEntity(
                entity_type=PIIEntityType.EMAIL_ADDRESS,
                start=36,
                end=56,
                score=0.95,
                text="john.doe@example.com"
            )
        ]
        
        # Mock desensitization result
        from src.sync.desensitization.models import DesensitizationResult
        mock_result = DesensitizationResult(
            success=True,
            original_text=test_text,
            anonymized_text="My name is [PERSON] and my email is [EMAIL]",
            entities_found=mock_entities,
            rules_applied=["person_rule", "email_rule"],
            processing_time_ms=25.5
        )
        
        # Mock rule manager
        mock_rules = [
            DesensitizationRule(
                id="rule1",
                name="person_rule",
                entity_type=PIIEntityType.PERSON,
                masking_strategy=MaskingStrategy.REPLACE,
                config={"replacement": "[PERSON]"}
            ),
            DesensitizationRule(
                id="rule2", 
                name="email_rule",
                entity_type=PIIEntityType.EMAIL_ADDRESS,
                masking_strategy=MaskingStrategy.REPLACE,
                config={"replacement": "[EMAIL]"}
            )
        ]
        
        self.service._get_active_rules = AsyncMock(return_value=mock_rules)
        self.service.presidio_engine.detect_pii.return_value = mock_entities
        self.service.presidio_engine.anonymize_text.return_value = mock_result
        
        # Act
        result = await self.service.detect_and_mask_automatically(
            data=test_text,
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type="test"
        )
        
        # Assert
        assert result["success"] is True
        assert result["original_data"] == test_text
        assert result["masked_data"] == "My name is [PERSON] and my email is [EMAIL]"
        assert len(result["entities_detected"]) == 2
        assert "person_rule" in result["rules_applied"]
        assert "email_rule" in result["rules_applied"]
        assert result["processing_time_ms"] > 0
        
        # Verify audit logging
        self.service.audit_service.log_event.assert_any_call(
            event_type="data_desensitization_start",
            user_id=user_id,
            resource="sensitive_data",
            action="auto_detect_mask",
            details={
                "operation_id": result["operation_id"],
                "operation_type": "test",
                "data_type": "str",
                "tenant_id": tenant_id
            }
        )
    
    @pytest.mark.asyncio
    async def test_detect_and_mask_dict_data(self):
        """Test automatic detection and masking of dictionary data."""
        # Arrange
        test_data = {
            "name": "Alice Smith",
            "email": "alice@company.com",
            "phone": "555-123-4567",
            "age": 30,
            "notes": "Customer since 2020"
        }
        
        tenant_id = "test_tenant"
        user_id = "test_user"
        
        # Mock rules with field patterns
        mock_rules = [
            DesensitizationRule(
                id="rule1",
                name="name_rule",
                entity_type=PIIEntityType.PERSON,
                field_pattern="name",
                masking_strategy=MaskingStrategy.REPLACE,
                config={"replacement": "[NAME]"}
            ),
            DesensitizationRule(
                id="rule2",
                name="email_rule", 
                entity_type=PIIEntityType.EMAIL_ADDRESS,
                field_pattern="email",
                masking_strategy=MaskingStrategy.REPLACE,
                config={"replacement": "[EMAIL]"}
            )
        ]
        
        self.service._get_active_rules = AsyncMock(return_value=mock_rules)
        
        # Mock field processing
        async def mock_process_text_data(text, rules, tenant_id, user_id, operation_id):
            if "Alice Smith" in text:
                return {
                    "success": True,
                    "masked_data": "[NAME]",
                    "entities_detected": [{"entity_type": "PERSON", "text": "Alice Smith"}],
                    "rules_applied": ["name_rule"],
                    "errors": []
                }
            elif "alice@company.com" in text:
                return {
                    "success": True,
                    "masked_data": "[EMAIL]",
                    "entities_detected": [{"entity_type": "EMAIL_ADDRESS", "text": "alice@company.com"}],
                    "rules_applied": ["email_rule"],
                    "errors": []
                }
            else:
                return {
                    "success": True,
                    "masked_data": text,
                    "entities_detected": [],
                    "rules_applied": [],
                    "errors": []
                }
        
        self.service._process_text_data = AsyncMock(side_effect=mock_process_text_data)
        
        # Act
        result = await self.service.detect_and_mask_automatically(
            data=test_data,
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type="test"
        )
        
        # Assert
        assert result["success"] is True
        assert result["masked_data"]["name"] == "[NAME]"
        assert result["masked_data"]["email"] == "[EMAIL]"
        assert result["masked_data"]["phone"] == "555-123-4567"  # No rule applied
        assert result["masked_data"]["age"] == 30  # Non-string field
        assert len(result["entities_detected"]) == 2
    
    @pytest.mark.asyncio
    async def test_bulk_detect_and_mask(self):
        """Test bulk processing of multiple data items."""
        # Arrange
        test_items = [
            "John Doe - john@example.com",
            "Jane Smith - jane@company.org", 
            {"name": "Bob Wilson", "email": "bob@test.com"},
            "No sensitive data here"
        ]
        
        tenant_id = "test_tenant"
        user_id = "test_user"
        
        # Mock individual processing
        async def mock_detect_and_mask(data, tenant_id, user_id, context, operation_type):
            if isinstance(data, str) and "@" in data:
                return {
                    "success": True,
                    "masked_data": data.replace("@", "@[MASKED]"),
                    "entities_detected": [{"entity_type": "EMAIL_ADDRESS"}],
                    "rules_applied": ["email_rule"],
                    "errors": []
                }
            elif isinstance(data, dict):
                return {
                    "success": True,
                    "masked_data": {k: "[MASKED]" if "@" in str(v) else v for k, v in data.items()},
                    "entities_detected": [{"entity_type": "EMAIL_ADDRESS"}],
                    "rules_applied": ["email_rule"],
                    "errors": []
                }
            else:
                return {
                    "success": True,
                    "masked_data": data,
                    "entities_detected": [],
                    "rules_applied": [],
                    "errors": []
                }
        
        self.service.detect_and_mask_automatically = AsyncMock(side_effect=mock_detect_and_mask)
        
        # Act
        result = await self.service.bulk_detect_and_mask(
            data_items=test_items,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        # Assert
        assert result["success"] is True
        assert result["items_processed"] == 4
        assert result["success_count"] == 4
        assert result["failure_count"] == 0
        assert len(result["results"]) == 4
        
        # Verify audit logging
        self.service.audit_service.log_event.assert_any_call(
            event_type="bulk_desensitization_start",
            user_id=user_id,
            resource="sensitive_data",
            action="bulk_detect_mask",
            details={
                "bulk_operation_id": result["bulk_operation_id"],
                "items_count": 4,
                "tenant_id": tenant_id
            }
        )
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in auto-desensitization."""
        # Arrange
        test_text = "Test data"
        tenant_id = "test_tenant"
        user_id = "test_user"
        
        # Mock error in rule retrieval
        self.service._get_active_rules = AsyncMock(side_effect=Exception("Database error"))
        
        # Act
        result = await self.service.detect_and_mask_automatically(
            data=test_text,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert result["masked_data"] == test_text  # Original data preserved
        
        # Verify error alert
        self.service.alert_manager.send_error_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_configuration_update(self):
        """Test configuration update functionality."""
        # Arrange
        tenant_id = "test_tenant"
        config = {
            "auto_detection_enabled": False,
            "batch_size": 50,
            "max_concurrent_operations": 5
        }
        
        # Act
        result = await self.service.configure_auto_detection(tenant_id, config)
        
        # Assert
        assert result["success"] is True
        assert result["applied_config"] == config
        assert self.service.auto_detection_enabled is False
        assert self.service.batch_size == 50
        assert self.service.max_concurrent_operations == 5
    
    @pytest.mark.asyncio
    async def test_quality_validation_integration(self):
        """Test integration with quality validation."""
        # Arrange
        self.service.quality_validation_enabled = True
        
        test_text = "John Doe"
        tenant_id = "test_tenant"
        user_id = "test_user"
        
        # Mock validation result
        from src.desensitization.validator import ValidationResult
        mock_validation = ValidationResult(
            is_valid=True,
            completeness_score=0.95,
            accuracy_score=0.90,
            issues=[],
            recommendations=[],
            metadata={}
        )
        
        # Mock a rule to ensure processing happens
        from unittest.mock import MagicMock
        mock_rule = MagicMock()
        mock_rule.entity_type.value = "PERSON"
        mock_rule.confidence_threshold = 0.8
        
        self.service.validator.validate_desensitization = AsyncMock(return_value=mock_validation)
        self.service._get_active_rules = AsyncMock(return_value=[mock_rule])
        
        # Mock presidio engine to return some entities
        self.service.presidio_engine.detect_pii = MagicMock(return_value=[])
        self.service.presidio_engine.anonymize_text = MagicMock(return_value=MagicMock(
            success=True,
            anonymized_text="John Doe",
            entities_found=[],
            rules_applied=[],
            errors=[]
        ))
        
        # Act
        result = await self.service.detect_and_mask_automatically(
            data=test_text,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        # Assert
        assert "validation" in result
        assert result["validation"]["is_valid"] is True
        assert result["validation"]["completeness_score"] == 0.95


class TestAutoDesensitizationMiddleware:
    """Test automatic desensitization middleware functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.middleware = AutoDesensitizationMiddleware(
            app=self.app,
            enabled=True,
            mask_requests=True,
            mask_responses=True
        )
        
        # Mock desensitization service
        self.middleware.desensitization_service = Mock()
        self.middleware.desensitization_service.detect_and_mask_automatically = AsyncMock()
    
    @pytest.mark.asyncio
    async def test_middleware_request_processing(self):
        """Test middleware processing of requests."""
        # Arrange
        from fastapi import Request
        from starlette.datastructures import Headers
        
        # Mock request with JSON body containing PII
        request_body = json.dumps({
            "name": "John Doe",
            "email": "john@example.com"
        })
        
        mock_request = Mock(spec=Request)
        mock_request.url.path = "/api/test"
        mock_request.method = "POST"
        mock_request.headers = Headers({"content-type": "application/json", "content-length": str(len(request_body))})
        mock_request.body = AsyncMock(return_value=request_body.encode())
        
        # Mock user context
        async def mock_get_user_context(request):
            return {
                "user_id": "test_user",
                "tenant_id": "test_tenant",
                "username": "testuser",
                "roles": ["user"]
            }
        
        self.middleware._get_user_context = mock_get_user_context
        
        # Mock desensitization result
        self.middleware.desensitization_service.detect_and_mask_automatically.return_value = {
            "success": True,
            "masked_data": {"name": "[NAME]", "email": "[EMAIL]"},
            "entities_detected": [{"entity_type": "PERSON"}, {"entity_type": "EMAIL_ADDRESS"}],
            "rules_applied": ["name_rule", "email_rule"]
        }
        
        # Act
        processed_request = await self.middleware._process_request(mock_request, {
            "user_id": "test_user",
            "tenant_id": "test_tenant",
            "username": "testuser",
            "roles": ["user"]
        })
        
        # Assert
        # Verify desensitization was called
        self.middleware.desensitization_service.detect_and_mask_automatically.assert_called_once()
        
        # Verify request body was updated (in real implementation)
        # Note: This is a simplified test - actual implementation would modify request._body
    
    def test_middleware_path_exclusion(self):
        """Test middleware path exclusion logic."""
        # Test excluded paths
        assert self.middleware._should_exclude_path("/health") is True
        assert self.middleware._should_exclude_path("/metrics") is True
        assert self.middleware._should_exclude_path("/docs") is True
        assert self.middleware._should_exclude_path("/static/css/style.css") is True
        
        # Test included paths
        assert self.middleware._should_exclude_path("/api/users") is False
        assert self.middleware._should_exclude_path("/api/data") is False
    
    def test_middleware_configuration_update(self):
        """Test middleware configuration updates."""
        # Arrange
        config = {
            "enabled": False,
            "mask_requests": False,
            "max_content_size": 5000000
        }
        
        # Act
        result = self.middleware.update_configuration(config)
        
        # Assert
        assert result["success"] is True
        assert self.middleware.enabled is False
        assert self.middleware.mask_requests is False
        assert self.middleware.max_content_size == 5000000
    
    def test_middleware_statistics(self):
        """Test middleware statistics tracking."""
        # Arrange
        self.middleware.processing_stats = {
            "total_requests": 100,
            "processed_requests": 85,
            "skipped_requests": 10,
            "error_count": 5,
            "total_processing_time": 2.5
        }
        
        # Act
        stats = self.middleware.get_processing_stats()
        
        # Assert
        assert stats["total_requests"] == 100
        assert stats["processed_requests"] == 85
        assert stats["processing_rate"] == 0.85
        assert stats["average_processing_time"] == 0.025
        assert stats["configuration"]["mask_requests"] is True


class TestAutoDesensitizationAPI:
    """Test automatic desensitization API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.app.include_router(auto_desensitization_router)
        
        # Mock dependencies
        self.mock_user = Mock()
        self.mock_user.id = "test_user_id"
        self.mock_user.tenant_id = "test_tenant_id"
        self.mock_user.username = "testuser"
        self.mock_user.role = Mock()
        self.mock_user.role.value = "admin"  # Set admin role for configuration tests
        
        # Override the dependency
        from src.api.auto_desensitization import get_current_active_user
        self.app.dependency_overrides[get_current_active_user] = lambda: self.mock_user
        
        self.client = TestClient(self.app)
        
    @patch('src.api.auto_desensitization.auto_desensitization_service')
    def test_auto_detect_endpoint(self, mock_service):
        """Test auto detection API endpoint."""
        # Arrange
        mock_service.detect_and_mask_automatically = AsyncMock(return_value={
            "success": True,
            "operation_id": "test_op_123",
            "original_data": "John Doe",
            "masked_data": "[NAME]",
            "entities_detected": [{"entity_type": "PERSON", "text": "John Doe"}],
            "rules_applied": ["name_rule"],
            "processing_time_ms": 15.5,
            "errors": []
        })
        
        # Act
        response = self.client.post(
            "/api/auto-desensitization/detect",
            json={
                "data": "John Doe",
                "operation_type": "test"
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["operation_id"] == "test_op_123"
        assert data["masked_data"] == "[NAME]"
        assert len(data["entities_detected"]) == 1
    
    @patch('src.api.auto_desensitization.auto_desensitization_service')
    def test_bulk_detect_endpoint(self, mock_service):
        """Test bulk detection API endpoint."""
        # Arrange
        mock_service.bulk_detect_and_mask = AsyncMock(return_value={
            "success": True,
            "bulk_operation_id": "bulk_op_456",
            "items_processed": 3,
            "success_count": 3,
            "failure_count": 0,
            "total_entities_detected": 5,
            "total_rules_applied": ["name_rule", "email_rule"],
            "processing_time_ms": 45.2,
            "results": [
                {"success": True, "masked_data": "[NAME]"},
                {"success": True, "masked_data": "[EMAIL]"},
                {"success": True, "masked_data": "No PII"}
            ],
            "errors": []
        })
        
        # Act
        response = self.client.post(
            "/api/auto-desensitization/bulk-detect",
            json={
                "data_items": ["John Doe", "jane@example.com", "No PII here"]
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["items_processed"] == 3
        assert data["total_entities_detected"] == 5
    
    @patch('src.api.auto_desensitization.auto_desensitization_service')
    def test_configuration_endpoint(self, mock_service):
        """Test configuration API endpoint."""
        # Arrange
        mock_service.configure_auto_detection = AsyncMock(return_value={
            "success": True,
            "message": "Configuration updated successfully",
            "applied_config": {
                "auto_detection_enabled": True,
                "batch_size": 200
            }
        })
        
        # Act
        response = self.client.post(
            "/api/auto-desensitization/config",
            json={
                "auto_detection_enabled": True,
                "batch_size": 200
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["applied_config"]["batch_size"] == 200
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        # Act
        response = self.client.get("/api/auto-desensitization/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data
    
    def test_version_endpoint(self):
        """Test version information endpoint."""
        # Act
        response = self.client.get("/api/auto-desensitization/version")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "auto-desensitization"
        assert "version" in data
        assert "features" in data
        assert "supported_entity_types" in data


class TestIntegrationScenarios:
    """Test integration scenarios for the complete auto-desensitization system."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.service = AutoDesensitizationService()
        
        # Use real components for integration testing
        from src.sync.desensitization import PresidioEngine
        self.service.presidio_engine = PresidioEngine()
        
        # Mock only external dependencies
        self.service.audit_service = Mock()
        self.service.audit_service.log_event = AsyncMock()
        
        self.service.quality_monitor = Mock()
        self.service.quality_monitor.record_operation = AsyncMock()
        
        self.service.alert_manager = Mock()
        self.service.alert_manager.send_error_alert = AsyncMock()
    
    @pytest.mark.asyncio
    async def test_end_to_end_text_processing(self):
        """Test end-to-end text processing with real Presidio engine."""
        # Arrange
        test_text = "Contact John Smith at john.smith@company.com or call 555-123-4567"
        tenant_id = "integration_test_tenant"
        user_id = "integration_test_user"
        
        # Mock rules (would normally come from database)
        from src.sync.desensitization.models import DesensitizationRule
        mock_rules = [
            DesensitizationRule(
                id="rule1",
                name="person_masking",
                entity_type=PIIEntityType.PERSON,
                masking_strategy=MaskingStrategy.REPLACE,
                config={"replacement": "[PERSON]"},
                enabled=True
            ),
            DesensitizationRule(
                id="rule2",
                name="email_masking",
                entity_type=PIIEntityType.EMAIL_ADDRESS,
                masking_strategy=MaskingStrategy.REPLACE,
                config={"replacement": "[EMAIL]"},
                enabled=True
            ),
            DesensitizationRule(
                id="rule3",
                name="phone_masking",
                entity_type=PIIEntityType.PHONE_NUMBER,
                masking_strategy=MaskingStrategy.REPLACE,
                config={"replacement": "[PHONE]"},
                enabled=True
            )
        ]
        
        self.service._get_active_rules = AsyncMock(return_value=mock_rules)
        
        # Act
        result = await self.service.detect_and_mask_automatically(
            data=test_text,
            tenant_id=tenant_id,
            user_id=user_id,
            operation_type="integration_test"
        )
        
        # Assert
        assert result["success"] is True
        assert result["original_data"] == test_text
        
        # Check that sensitive data was detected and masked
        masked_text = result["masked_data"]
        entities_detected = result["entities_detected"]
        
        # Should detect at least email (Presidio fallback should work)
        assert len(entities_detected) > 0
        
        # Masked text should be different from original
        assert masked_text != test_text
        
        # Verify audit logging was called
        self.service.audit_service.log_event.assert_called()
    
    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self):
        """Test performance with larger dataset."""
        # Arrange
        large_dataset = []
        for i in range(50):
            large_dataset.append(f"User {i}: john{i}@example.com, phone: 555-{i:03d}-{i:04d}")
        
        tenant_id = "perf_test_tenant"
        user_id = "perf_test_user"
        
        # Mock minimal rules for performance
        mock_rules = [
            DesensitizationRule(
                id="email_rule",
                name="email_masking",
                entity_type=PIIEntityType.EMAIL_ADDRESS,
                masking_strategy=MaskingStrategy.REPLACE,
                config={"replacement": "[EMAIL]"},
                enabled=True
            )
        ]
        
        self.service._get_active_rules = AsyncMock(return_value=mock_rules)
        
        # Act
        start_time = datetime.utcnow()
        result = await self.service.bulk_detect_and_mask(
            data_items=large_dataset,
            tenant_id=tenant_id,
            user_id=user_id
        )
        end_time = datetime.utcnow()
        
        # Assert
        processing_time = (end_time - start_time).total_seconds()
        
        assert result["success"] is True
        assert result["items_processed"] == 50
        assert processing_time < 30.0  # Should complete within 30 seconds
        
        # Verify performance metrics
        assert result["processing_time_ms"] > 0
        print(f"Processed {result['items_processed']} items in {processing_time:.2f} seconds")
        print(f"Average processing time: {result['processing_time_ms'] / result['items_processed']:.2f} ms per item")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])