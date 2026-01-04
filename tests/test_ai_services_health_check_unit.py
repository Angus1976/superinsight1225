"""
Unit tests for AI Services Health Check.

Tests for Task 2.2: Write unit tests for AI services health check
- Test AI service availability checks
- Test graceful handling of missing configurations
- Mock AI provider API responses
- Requirements: 2.1, 2.2, 2.3
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, Optional
from uuid import uuid4

from src.ai.factory import AIAnnotatorFactory, AnnotatorFactory
from src.ai.base import ModelConfig, ModelType, AIAnnotationError
from src.ai.ollama_annotator import OllamaAnnotator
from src.ai.huggingface_annotator import HuggingFaceAnnotator
from src.ai.zhipu_annotator import ZhipuAnnotator
from src.ai.baidu_annotator import BaiduAnnotator


class TestAIAnnotatorFactoryHealthCheck:
    """Tests for AIAnnotatorFactory health check functionality."""

    def test_factory_supported_services(self):
        """Test that factory returns list of supported services."""
        services = AIAnnotatorFactory.get_supported_services()

        assert isinstance(services, list)
        assert len(services) > 0
        assert "ollama" in services
        assert "huggingface" in services
        assert "zhipu" in services
        assert "baidu" in services

    def test_factory_create_annotator_ollama(self):
        """Test creating Ollama annotator for health check."""
        with patch.object(AnnotatorFactory, 'create_annotator') as mock_create:
            mock_annotator = Mock()
            mock_create.return_value = mock_annotator

            annotator = AIAnnotatorFactory.create_annotator("ollama")

            assert annotator is not None
            mock_create.assert_called_once()

    def test_factory_create_annotator_huggingface(self):
        """Test creating HuggingFace annotator for health check."""
        with patch.object(AnnotatorFactory, 'create_annotator') as mock_create:
            mock_annotator = Mock()
            mock_create.return_value = mock_annotator

            annotator = AIAnnotatorFactory.create_annotator("huggingface")

            assert annotator is not None
            mock_create.assert_called_once()

    def test_factory_create_annotator_unsupported_service(self):
        """Test creating annotator for unsupported service returns None."""
        annotator = AIAnnotatorFactory.create_annotator("unsupported_service")

        assert annotator is None

    def test_factory_create_annotator_case_insensitive(self):
        """Test service name is case-insensitive."""
        with patch.object(AnnotatorFactory, 'create_annotator') as mock_create:
            mock_annotator = Mock()
            mock_create.return_value = mock_annotator

            # Test uppercase
            annotator1 = AIAnnotatorFactory.create_annotator("OLLAMA")
            assert annotator1 is not None

            # Test mixed case
            annotator2 = AIAnnotatorFactory.create_annotator("HuggingFace")
            assert annotator2 is not None

    def test_factory_create_annotator_with_exception(self):
        """Test graceful handling when annotator creation fails."""
        with patch.object(AnnotatorFactory, 'create_annotator', side_effect=Exception("Creation failed")):
            annotator = AIAnnotatorFactory.create_annotator("ollama")

            assert annotator is None

    @pytest.mark.asyncio
    async def test_check_service_health_ollama_available(self):
        """Test health check for available Ollama service."""
        mock_annotator = AsyncMock()
        mock_annotator.check_model_availability = AsyncMock(return_value=True)

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            result = await AIAnnotatorFactory.check_service_health("ollama")

            assert result["service"] == "ollama"
            assert result["available"] is True
            assert "model_type" in result

    @pytest.mark.asyncio
    async def test_check_service_health_ollama_unavailable(self):
        """Test health check for unavailable Ollama service."""
        mock_annotator = AsyncMock()
        mock_annotator.check_model_availability = AsyncMock(return_value=False)

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            result = await AIAnnotatorFactory.check_service_health("ollama")

            assert result["service"] == "ollama"
            assert result["available"] is False

    @pytest.mark.asyncio
    async def test_check_service_health_huggingface_available(self):
        """Test health check for available HuggingFace service."""
        mock_annotator = AsyncMock()
        mock_annotator.check_model_availability = AsyncMock(return_value=True)

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            result = await AIAnnotatorFactory.check_service_health("huggingface")

            assert result["service"] == "huggingface"
            assert result["available"] is True

    @pytest.mark.asyncio
    async def test_check_service_health_zhipu_available(self):
        """Test health check for available Zhipu service."""
        mock_annotator = AsyncMock()
        mock_annotator.check_model_availability = AsyncMock(return_value=True)

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            result = await AIAnnotatorFactory.check_service_health("zhipu")

            assert result["service"] == "zhipu"
            assert result["available"] is True

    @pytest.mark.asyncio
    async def test_check_service_health_baidu_available(self):
        """Test health check for available Baidu service."""
        mock_annotator = AsyncMock()
        mock_annotator.check_model_availability = AsyncMock(return_value=True)

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            result = await AIAnnotatorFactory.check_service_health("baidu")

            assert result["service"] == "baidu"
            assert result["available"] is True

    @pytest.mark.asyncio
    async def test_check_service_health_unsupported_service(self):
        """Test health check for unsupported service."""
        result = await AIAnnotatorFactory.check_service_health("unsupported")

        assert result["service"] == "unsupported"
        assert result["available"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_check_service_health_creation_failure(self):
        """Test health check when annotator creation fails."""
        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=None):
            result = await AIAnnotatorFactory.check_service_health("ollama")

            assert result["service"] == "ollama"
            assert result["available"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_check_service_health_exception_handling(self):
        """Test health check handles exceptions gracefully."""
        mock_annotator = AsyncMock()
        mock_annotator.check_model_availability = AsyncMock(side_effect=Exception("Connection error"))

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            result = await AIAnnotatorFactory.check_service_health("ollama")

            assert result["service"] == "ollama"
            assert result["available"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_check_service_health_with_test_connection_method(self):
        """Test health check uses test_connection method if available."""
        mock_annotator = AsyncMock()
        mock_annotator.test_connection = AsyncMock(return_value=True)
        # Remove check_model_availability to test fallback
        del mock_annotator.check_model_availability

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            result = await AIAnnotatorFactory.check_service_health("ollama")

            assert result["service"] == "ollama"
            assert result["available"] is True

    @pytest.mark.asyncio
    async def test_check_service_health_no_check_method(self):
        """Test health check assumes available when no check method exists."""
        mock_annotator = Mock(spec=[])  # Empty spec means no methods
        # Explicitly set hasattr to return False for both methods
        mock_annotator.check_model_availability = None
        mock_annotator.test_connection = None

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            with patch('builtins.hasattr', return_value=False):
                result = await AIAnnotatorFactory.check_service_health("ollama")

                assert result["service"] == "ollama"
                assert result["available"] is True


class TestAIServiceAvailabilityChecks:
    """Tests for AI service availability checks."""

    @pytest.mark.asyncio
    async def test_ollama_availability_check_success(self):
        """Test Ollama service availability check success."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
            timeout=5
        )

        annotator = OllamaAnnotator(config)

        # Mock successful model list response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "models": [{"name": "llama2"}]
        }

        with patch.object(annotator.client, 'get', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is True

    @pytest.mark.asyncio
    async def test_ollama_availability_check_failure(self):
        """Test Ollama service availability check failure."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
            timeout=5
        )

        annotator = OllamaAnnotator(config)

        # Mock failed response
        with patch.object(annotator.client, 'get', side_effect=Exception("Connection refused")):
            is_available = await annotator.check_model_availability()

            assert is_available is False

    @pytest.mark.asyncio
    async def test_huggingface_availability_check_success(self):
        """Test HuggingFace service availability check success."""
        config = ModelConfig(
            model_type=ModelType.HUGGINGFACE,
            model_name="bert-base-uncased",
            api_key="test_key",
            timeout=5
        )

        annotator = HuggingFaceAnnotator(config)

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        with patch.object(annotator.client, 'get', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is True

    @pytest.mark.asyncio
    async def test_huggingface_availability_check_failure(self):
        """Test HuggingFace service availability check failure."""
        config = ModelConfig(
            model_type=ModelType.HUGGINGFACE,
            model_name="bert-base-uncased",
            api_key="invalid_key",
            timeout=5
        )

        annotator = HuggingFaceAnnotator(config)

        # Mock failed response
        with patch.object(annotator.client, 'get', side_effect=Exception("Unauthorized")):
            is_available = await annotator.check_model_availability()

            assert is_available is False

    @pytest.mark.asyncio
    async def test_zhipu_availability_check_success(self):
        """Test Zhipu service availability check success."""
        config = ModelConfig(
            model_type=ModelType.ZHIPU_GLM,
            model_name="glm-4",
            api_key="test_key",
            timeout=5
        )

        annotator = ZhipuAnnotator(config)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200

        with patch.object(annotator.client, 'post', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is True

    @pytest.mark.asyncio
    async def test_zhipu_availability_check_failure(self):
        """Test Zhipu service availability check failure."""
        config = ModelConfig(
            model_type=ModelType.ZHIPU_GLM,
            model_name="glm-4",
            api_key="invalid_key",
            timeout=5
        )

        annotator = ZhipuAnnotator(config)

        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401

        with patch.object(annotator.client, 'post', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is False

    @pytest.mark.asyncio
    async def test_baidu_availability_check_success(self):
        """Test Baidu service availability check success."""
        config = ModelConfig(
            model_type=ModelType.BAIDU_WENXIN,
            model_name="ernie-bot",
            api_key="test_key",
            base_url="test_secret",
            timeout=5
        )

        annotator = BaiduAnnotator(config)

        # Mock successful access token response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "expires_in": 3600
        }

        with patch.object(annotator.client, 'post', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is True

    @pytest.mark.asyncio
    async def test_baidu_availability_check_failure(self):
        """Test Baidu service availability check failure."""
        config = ModelConfig(
            model_type=ModelType.BAIDU_WENXIN,
            model_name="ernie-bot",
            api_key="invalid_key",
            base_url="invalid_secret",
            timeout=5
        )

        annotator = BaiduAnnotator(config)

        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401

        with patch.object(annotator.client, 'post', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is False


class TestGracefulHandlingOfMissingConfigurations:
    """Tests for graceful handling of missing configurations."""

    def test_factory_handles_missing_api_key(self):
        """Test factory handles missing API key gracefully."""
        config = ModelConfig(
            model_type=ModelType.HUGGINGFACE,
            model_name="bert-base-uncased",
            # api_key is missing
            timeout=5
        )

        # Should not raise exception
        annotator = HuggingFaceAnnotator(config)
        assert annotator is not None

    def test_factory_handles_missing_base_url_for_ollama(self):
        """Test factory handles missing base_url for Ollama."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            # base_url is missing
            timeout=5
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="base_url is required"):
            OllamaAnnotator(config)

    def test_factory_handles_missing_api_key_for_zhipu(self):
        """Test factory handles missing API key for Zhipu."""
        config = ModelConfig(
            model_type=ModelType.ZHIPU_GLM,
            model_name="glm-4",
            # api_key is missing
            timeout=5
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="api_key is required"):
            ZhipuAnnotator(config)

    def test_factory_handles_missing_credentials_for_baidu(self):
        """Test factory handles missing credentials for Baidu."""
        config = ModelConfig(
            model_type=ModelType.BAIDU_WENXIN,
            model_name="ernie-bot",
            # api_key is missing
            timeout=5
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="api_key"):
            BaiduAnnotator(config)

    @pytest.mark.asyncio
    async def test_health_check_with_missing_configuration(self):
        """Test health check handles missing configuration gracefully."""
        # Try to check health of service with missing config
        result = await AIAnnotatorFactory.check_service_health("ollama")

        # Should return error status, not crash
        assert result["available"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_check_with_invalid_service_name(self):
        """Test health check handles invalid service name gracefully."""
        result = await AIAnnotatorFactory.check_service_health("invalid_service_xyz")

        assert result["available"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_check_with_empty_service_name(self):
        """Test health check handles empty service name gracefully."""
        result = await AIAnnotatorFactory.check_service_health("")

        assert result["available"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_check_with_none_service_name(self):
        """Test health check handles None service name gracefully."""
        # Should not crash
        try:
            result = await AIAnnotatorFactory.check_service_health(None)
            assert result["available"] is False
        except (TypeError, AttributeError):
            # Acceptable to raise for None input
            pass


class TestMockAIProviderAPIResponses:
    """Tests for mocking AI provider API responses."""

    @pytest.mark.asyncio
    async def test_mock_ollama_api_response_success(self):
        """Test mocking successful Ollama API response."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
            timeout=5
        )

        annotator = OllamaAnnotator(config)

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "models": [
                {"name": "llama2", "size": "3.8GB"},
                {"name": "mistral", "size": "4.1GB"}
            ]
        }

        with patch.object(annotator.client, 'get', return_value=mock_response) as mock_get:
            is_available = await annotator.check_model_availability()

            assert is_available is True
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_mock_ollama_api_response_timeout(self):
        """Test mocking Ollama API timeout response."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
            timeout=5
        )

        annotator = OllamaAnnotator(config)

        # Mock timeout
        with patch.object(annotator.client, 'get', side_effect=asyncio.TimeoutError("Request timeout")):
            is_available = await annotator.check_model_availability()

            assert is_available is False

    @pytest.mark.asyncio
    async def test_mock_huggingface_api_response_success(self):
        """Test mocking successful HuggingFace API response."""
        config = ModelConfig(
            model_type=ModelType.HUGGINGFACE,
            model_name="bert-base-uncased",
            api_key="test_key",
            timeout=5
        )

        annotator = HuggingFaceAnnotator(config)

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200

        with patch.object(annotator.client, 'get', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is True

    @pytest.mark.asyncio
    async def test_mock_huggingface_api_response_unauthorized(self):
        """Test mocking HuggingFace API unauthorized response."""
        config = ModelConfig(
            model_type=ModelType.HUGGINGFACE,
            model_name="bert-base-uncased",
            api_key="invalid_key",
            timeout=5
        )

        annotator = HuggingFaceAnnotator(config)

        # Mock unauthorized response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")

        with patch.object(annotator.client, 'get', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is False

    @pytest.mark.asyncio
    async def test_mock_zhipu_api_response_success(self):
        """Test mocking successful Zhipu API response."""
        config = ModelConfig(
            model_type=ModelType.ZHIPU_GLM,
            model_name="glm-4",
            api_key="test_key",
            timeout=5
        )

        annotator = ZhipuAnnotator(config)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200

        with patch.object(annotator.client, 'post', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is True

    @pytest.mark.asyncio
    async def test_mock_zhipu_api_response_error(self):
        """Test mocking Zhipu API error response."""
        config = ModelConfig(
            model_type=ModelType.ZHIPU_GLM,
            model_name="glm-4",
            api_key="test_key",
            timeout=5
        )

        annotator = ZhipuAnnotator(config)

        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500

        with patch.object(annotator.client, 'post', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is False

    @pytest.mark.asyncio
    async def test_mock_baidu_api_response_success(self):
        """Test mocking successful Baidu API response."""
        config = ModelConfig(
            model_type=ModelType.BAIDU_WENXIN,
            model_name="ernie-bot",
            api_key="test_key",
            base_url="test_secret",
            timeout=5
        )

        annotator = BaiduAnnotator(config)

        # Mock successful access token response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "expires_in": 3600
        }

        with patch.object(annotator.client, 'post', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is True

    @pytest.mark.asyncio
    async def test_mock_baidu_api_response_rate_limit(self):
        """Test mocking Baidu API rate limit response."""
        config = ModelConfig(
            model_type=ModelType.BAIDU_WENXIN,
            model_name="ernie-bot",
            api_key="test_key",
            base_url="test_secret",
            timeout=5
        )

        annotator = BaiduAnnotator(config)

        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429

        with patch.object(annotator.client, 'post', return_value=mock_response):
            is_available = await annotator.check_model_availability()

            assert is_available is False


class TestAIServiceHealthCheckIntegration:
    """Integration tests for AI service health checks."""

    @pytest.mark.asyncio
    async def test_check_multiple_services_concurrently(self):
        """Test checking multiple AI services concurrently."""
        services = ["ollama", "huggingface", "zhipu", "baidu"]

        mock_annotator = AsyncMock()
        mock_annotator.check_model_availability = AsyncMock(return_value=True)

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            # Check all services concurrently
            results = await asyncio.gather(
                *[AIAnnotatorFactory.check_service_health(service) for service in services]
            )

            assert len(results) == 4
            for result in results:
                assert result["available"] is True

    @pytest.mark.asyncio
    async def test_check_services_with_mixed_availability(self):
        """Test checking services with mixed availability."""
        # Create different mock responses
        available_annotator = AsyncMock()
        available_annotator.check_model_availability = AsyncMock(return_value=True)

        unavailable_annotator = AsyncMock()
        unavailable_annotator.check_model_availability = AsyncMock(return_value=False)

        def create_annotator_side_effect(service_name):
            if service_name.lower() in ["ollama", "huggingface"]:
                return available_annotator
            else:
                return unavailable_annotator

        with patch.object(AIAnnotatorFactory, 'create_annotator', side_effect=create_annotator_side_effect):
            results = {
                "ollama": await AIAnnotatorFactory.check_service_health("ollama"),
                "huggingface": await AIAnnotatorFactory.check_service_health("huggingface"),
                "zhipu": await AIAnnotatorFactory.check_service_health("zhipu"),
                "baidu": await AIAnnotatorFactory.check_service_health("baidu"),
            }

            assert results["ollama"]["available"] is True
            assert results["huggingface"]["available"] is True
            assert results["zhipu"]["available"] is False
            assert results["baidu"]["available"] is False

    @pytest.mark.asyncio
    async def test_health_check_response_format(self):
        """Test health check response has correct format."""
        mock_annotator = AsyncMock()
        mock_annotator.check_model_availability = AsyncMock(return_value=True)

        with patch.object(AIAnnotatorFactory, 'create_annotator', return_value=mock_annotator):
            result = await AIAnnotatorFactory.check_service_health("ollama")

            # Verify response structure
            assert isinstance(result, dict)
            assert "service" in result
            assert "available" in result
            assert isinstance(result["service"], str)
            assert isinstance(result["available"], bool)

    @pytest.mark.asyncio
    async def test_health_check_error_response_format(self):
        """Test health check error response has correct format."""
        result = await AIAnnotatorFactory.check_service_health("invalid_service")

        # Verify error response structure
        assert isinstance(result, dict)
        assert "service" in result
        assert "available" in result
        assert result["available"] is False
        assert "error" in result
        assert isinstance(result["error"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
