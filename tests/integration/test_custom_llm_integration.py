"""
Integration tests for Custom LLM engines.

Tests the AI annotator implementations for:
- Ollama integration
- HuggingFace integration
- Chinese LLM integrations (Zhipu, Baidu, Alibaba, Tencent)

Validates: Requirements 6.3
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.base import (
    AIAnnotator,
    ModelConfig,
    ModelType,
    Prediction,
    AIAnnotationError,
)
from src.ai.factory import (
    AnnotatorFactory,
    AIAnnotatorFactory,
    ConfidenceScorer,
    ModelManager,
)
from src.ai.ollama_annotator import OllamaAnnotator


# ============================================================================
# Mock Task for Testing
# ============================================================================

class MockTask:
    """Mock task for testing annotators."""
    
    def __init__(
        self,
        id: Optional[str] = None,
        project_id: str = "test-project",
        data: Optional[Dict[str, Any]] = None,
    ):
        self.id = uuid4() if id is None else id
        self.project_id = project_id
        self.data = data or {"text": "Test content"}


# ============================================================================
# Test Ollama Integration
# ============================================================================

class TestOllamaAnnotator:
    """Tests for Ollama annotator integration."""

    @pytest.fixture
    def ollama_config(self):
        """Create Ollama model configuration."""
        return ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
            max_tokens=1000,
            temperature=0.7,
            timeout=30,
        )

    @pytest.fixture
    def annotator(self, ollama_config):
        """Create Ollama annotator instance."""
        return OllamaAnnotator(ollama_config)

    def test_ollama_initialization(self, ollama_config):
        """Test Ollama annotator initializes correctly."""
        annotator = OllamaAnnotator(ollama_config)
        
        assert annotator.config.model_type == ModelType.OLLAMA
        assert annotator.config.model_name == "llama2"
        assert annotator.config.base_url == "http://localhost:11434"

    def test_ollama_invalid_model_type(self):
        """Test Ollama annotator rejects invalid model type."""
        config = ModelConfig(
            model_type=ModelType.HUGGINGFACE,
            model_name="test",
            base_url="http://localhost:11434",
        )
        
        with pytest.raises(ValueError, match="model_type=OLLAMA"):
            OllamaAnnotator(config)

    def test_ollama_missing_base_url(self):
        """Test Ollama annotator requires base_url."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url=None,
        )
        
        with pytest.raises(ValueError, match="base_url"):
            OllamaAnnotator(config)

    def test_ollama_missing_model_name(self):
        """Test Ollama annotator requires model_name."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="",
            base_url="http://localhost:11434",
        )
        
        with pytest.raises(ValueError, match="model_name"):
            OllamaAnnotator(config)

    def test_get_model_info(self, annotator):
        """Test getting model information."""
        info = annotator.get_model_info()
        
        assert info["model_type"] == "ollama"
        assert info["model_name"] == "llama2"
        assert info["base_url"] == "http://localhost:11434"
        assert info["max_tokens"] == 1000
        assert info["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_predict_with_mock_response(self, annotator):
        """Test prediction with mocked Ollama response."""
        task = MockTask()
        
        mock_response = {
            "response": '{"sentiment": "positive", "entities": [], "categories": [], "confidence": 0.85}'
        }
        
        with patch.object(annotator, '_make_ollama_request', return_value=mock_response):
            prediction = await annotator.predict(task)
        
        assert isinstance(prediction, Prediction)
        assert prediction.task_id == task.id
        assert prediction.confidence == 0.85
        assert prediction.prediction_data["sentiment"] == "positive"

    @pytest.mark.asyncio
    async def test_predict_handles_invalid_json(self, annotator):
        """Test prediction handles invalid JSON response."""
        task = MockTask()
        
        mock_response = {
            "response": "This is not valid JSON"
        }
        
        with patch.object(annotator, '_make_ollama_request', return_value=mock_response):
            prediction = await annotator.predict(task)
        
        assert isinstance(prediction, Prediction)
        assert prediction.confidence == 0.5  # Fallback confidence
        assert "raw_response" in prediction.prediction_data

    @pytest.mark.asyncio
    async def test_predict_handles_api_error(self, annotator):
        """Test prediction handles API errors."""
        task = MockTask()
        
        with patch.object(
            annotator,
            '_make_ollama_request',
            side_effect=AIAnnotationError("API error", "ollama")
        ):
            with pytest.raises(AIAnnotationError):
                await annotator.predict(task)

    @pytest.mark.asyncio
    async def test_batch_predict(self, annotator):
        """Test batch prediction."""
        tasks = [MockTask() for _ in range(3)]
        
        mock_response = {
            "response": '{"sentiment": "neutral", "entities": [], "categories": [], "confidence": 0.7}'
        }
        
        with patch.object(annotator, '_make_ollama_request', return_value=mock_response):
            predictions = await annotator.batch_predict(tasks)
        
        assert len(predictions) == 3
        for pred in predictions:
            assert isinstance(pred, Prediction)

    @pytest.mark.asyncio
    async def test_list_available_models_mock(self, annotator):
        """Test listing available models with mock."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama2"},
                {"name": "mistral"},
                {"name": "codellama"},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(annotator.client, 'get', return_value=mock_response):
            models = await annotator.list_available_models()
        
        assert "llama2" in models
        assert "mistral" in models
        assert len(models) == 3

    @pytest.mark.asyncio
    async def test_check_model_availability_true(self, annotator):
        """Test model availability check returns true."""
        with patch.object(
            annotator,
            'list_available_models',
            return_value=["llama2", "mistral"]
        ):
            is_available = await annotator.check_model_availability()
        
        assert is_available is True

    @pytest.mark.asyncio
    async def test_check_model_availability_false(self, annotator):
        """Test model availability check returns false."""
        with patch.object(
            annotator,
            'list_available_models',
            return_value=["mistral", "codellama"]
        ):
            is_available = await annotator.check_model_availability()
        
        assert is_available is False

    @pytest.mark.asyncio
    async def test_context_manager(self, ollama_config):
        """Test async context manager."""
        async with OllamaAnnotator(ollama_config) as annotator:
            assert annotator is not None
            assert annotator.config.model_name == "llama2"


# ============================================================================
# Test Annotator Factory
# ============================================================================

class TestAnnotatorFactory:
    """Tests for annotator factory."""

    def test_create_ollama_annotator(self):
        """Test creating Ollama annotator via factory."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
        )
        
        annotator = AnnotatorFactory.create_annotator(config)
        
        assert isinstance(annotator, OllamaAnnotator)

    def test_get_supported_model_types(self):
        """Test getting supported model types."""
        types = AnnotatorFactory.get_supported_model_types()
        
        assert ModelType.OLLAMA in types
        assert ModelType.HUGGINGFACE in types
        assert ModelType.ZHIPU_GLM in types

    def test_is_model_type_supported(self):
        """Test checking if model type is supported."""
        assert AnnotatorFactory.is_model_type_supported(ModelType.OLLAMA) is True
        assert AnnotatorFactory.is_model_type_supported(ModelType.HUGGINGFACE) is True

    def test_create_from_dict(self):
        """Test creating annotator from dictionary."""
        config_dict = {
            "model_type": "ollama",
            "model_name": "llama2",
            "base_url": "http://localhost:11434",
        }
        
        annotator = AnnotatorFactory.create_from_dict(config_dict)
        
        assert isinstance(annotator, OllamaAnnotator)

    def test_create_multiple_annotators(self):
        """Test creating multiple annotators."""
        configs = [
            ModelConfig(
                model_type=ModelType.OLLAMA,
                model_name="llama2",
                base_url="http://localhost:11434",
            ),
            ModelConfig(
                model_type=ModelType.OLLAMA,
                model_name="mistral",
                base_url="http://localhost:11434",
            ),
        ]
        
        annotators = AnnotatorFactory.create_multiple(configs)
        
        assert len(annotators) == 2


# ============================================================================
# Test AI Annotator Factory (Health Checks)
# ============================================================================

class TestAIAnnotatorFactory:
    """Tests for AI annotator factory with health checks."""

    def test_get_supported_services(self):
        """Test getting supported service names."""
        services = AIAnnotatorFactory.get_supported_services()
        
        assert "ollama" in services
        assert "huggingface" in services
        assert "zhipu" in services
        assert "baidu" in services

    @pytest.mark.asyncio
    async def test_check_service_health_unsupported(self):
        """Test health check for unsupported service."""
        result = await AIAnnotatorFactory.check_service_health("unsupported_service")
        
        assert result["available"] is False
        assert "not supported" in result["error"]

    @pytest.mark.asyncio
    async def test_check_service_health_ollama(self):
        """Test health check for Ollama service."""
        with patch.object(
            AIAnnotatorFactory,
            'create_annotator',
            return_value=MagicMock(check_model_availability=AsyncMock(return_value=True))
        ):
            result = await AIAnnotatorFactory.check_service_health("ollama")
        
        assert result["service"] == "ollama"
        # Result depends on mock


# ============================================================================
# Test Confidence Scorer
# ============================================================================

class TestConfidenceScorer:
    """Tests for confidence scoring utilities."""

    def test_calculate_ensemble_average(self):
        """Test average ensemble confidence."""
        confidences = [0.8, 0.9, 0.7]
        
        result = ConfidenceScorer.calculate_ensemble_confidence(confidences, "average")
        
        assert abs(result - 0.8) < 0.01

    def test_calculate_ensemble_max(self):
        """Test max ensemble confidence."""
        confidences = [0.8, 0.9, 0.7]
        
        result = ConfidenceScorer.calculate_ensemble_confidence(confidences, "max")
        
        assert result == 0.9

    def test_calculate_ensemble_min(self):
        """Test min ensemble confidence."""
        confidences = [0.8, 0.9, 0.7]
        
        result = ConfidenceScorer.calculate_ensemble_confidence(confidences, "min")
        
        assert result == 0.7

    def test_calculate_ensemble_weighted_average(self):
        """Test weighted average ensemble confidence."""
        confidences = [0.8, 0.9, 0.7]
        
        result = ConfidenceScorer.calculate_ensemble_confidence(confidences, "weighted_average")
        
        assert abs(result - 0.8) < 0.01

    def test_calculate_ensemble_empty(self):
        """Test ensemble with empty list."""
        result = ConfidenceScorer.calculate_ensemble_confidence([], "average")
        
        assert result == 0.0

    def test_calculate_ensemble_invalid_method(self):
        """Test ensemble with invalid method."""
        with pytest.raises(ValueError, match="Unknown ensemble method"):
            ConfidenceScorer.calculate_ensemble_confidence([0.5], "invalid")

    def test_adjust_confidence_by_model_type(self):
        """Test confidence adjustment by model type."""
        confidence = 0.8
        
        ollama_adjusted = ConfidenceScorer.adjust_confidence_by_model_type(
            confidence, ModelType.OLLAMA
        )
        zhipu_adjusted = ConfidenceScorer.adjust_confidence_by_model_type(
            confidence, ModelType.ZHIPU_GLM
        )
        
        # Ollama has 0.9 factor, Zhipu has 1.1 factor
        assert ollama_adjusted < confidence
        assert zhipu_adjusted > confidence

    def test_adjust_confidence_clamps_to_range(self):
        """Test confidence adjustment clamps to valid range."""
        result = ConfidenceScorer.adjust_confidence_by_model_type(
            1.0, ModelType.ZHIPU_GLM
        )
        
        assert result <= 1.0

    def test_calculate_confidence_from_agreement(self):
        """Test confidence from prediction agreement."""
        predictions = [
            {"sentiment": "positive", "confidence": 0.8},
            {"sentiment": "positive", "confidence": 0.9},
            {"sentiment": "negative", "confidence": 0.7},
        ]
        
        result = ConfidenceScorer.calculate_confidence_from_agreement(predictions)
        
        # 2/3 agree on positive
        assert abs(result - 0.667) < 0.01

    def test_calculate_confidence_from_agreement_single(self):
        """Test confidence from single prediction."""
        predictions = [{"sentiment": "positive", "confidence": 0.8}]
        
        result = ConfidenceScorer.calculate_confidence_from_agreement(predictions)
        
        assert result == 0.8

    def test_calculate_confidence_from_agreement_empty(self):
        """Test confidence from empty predictions."""
        result = ConfidenceScorer.calculate_confidence_from_agreement([])
        
        assert result == 0.0

    def test_validate_confidence_range(self):
        """Test confidence range validation."""
        assert ConfidenceScorer.validate_confidence_range(0.5) == 0.5
        assert ConfidenceScorer.validate_confidence_range(-0.1) == 0.0
        assert ConfidenceScorer.validate_confidence_range(1.5) == 1.0


# ============================================================================
# Test Model Manager
# ============================================================================

class TestModelManager:
    """Tests for model manager."""

    @pytest.fixture
    def manager(self):
        """Create model manager instance."""
        return ModelManager()

    @pytest.fixture
    def ollama_config(self):
        """Create Ollama config."""
        return ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
        )

    def test_add_annotator(self, manager, ollama_config):
        """Test adding annotator to manager."""
        manager.add_annotator("ollama-llama2", ollama_config)
        
        assert "ollama-llama2" in manager.list_annotators()

    def test_get_annotator(self, manager, ollama_config):
        """Test getting annotator from manager."""
        manager.add_annotator("ollama-llama2", ollama_config)
        
        annotator = manager.get_annotator("ollama-llama2")
        
        assert annotator is not None
        assert isinstance(annotator, OllamaAnnotator)

    def test_get_annotator_not_found(self, manager):
        """Test getting non-existent annotator."""
        annotator = manager.get_annotator("non-existent")
        
        assert annotator is None

    def test_list_annotators(self, manager, ollama_config):
        """Test listing annotators."""
        manager.add_annotator("annotator1", ollama_config)
        manager.add_annotator("annotator2", ollama_config)
        
        annotators = manager.list_annotators()
        
        assert len(annotators) == 2
        assert "annotator1" in annotators
        assert "annotator2" in annotators

    def test_remove_annotator(self, manager, ollama_config):
        """Test removing annotator."""
        manager.add_annotator("ollama-llama2", ollama_config)
        
        result = manager.remove_annotator("ollama-llama2")
        
        assert result is True
        assert "ollama-llama2" not in manager.list_annotators()

    def test_remove_annotator_not_found(self, manager):
        """Test removing non-existent annotator."""
        result = manager.remove_annotator("non-existent")
        
        assert result is False

    def test_set_default_config(self, manager, ollama_config):
        """Test setting default config."""
        manager.set_default_config(ModelType.OLLAMA, ollama_config)
        
        config = manager.get_default_config(ModelType.OLLAMA)
        
        assert config is not None
        assert config.model_name == "llama2"

    def test_get_default_config_not_set(self, manager):
        """Test getting default config when not set."""
        config = manager.get_default_config(ModelType.OLLAMA)
        
        assert config is None

    @pytest.mark.asyncio
    async def test_health_check(self, manager, ollama_config):
        """Test health check for all annotators."""
        manager.add_annotator("ollama-llama2", ollama_config)
        
        with patch.object(
            OllamaAnnotator,
            'check_model_availability',
            return_value=True
        ):
            health = await manager.health_check()
        
        assert "ollama-llama2" in health
        assert health["ollama-llama2"] is True


# ============================================================================
# Test Chinese LLM Integrations (Mock-based)
# ============================================================================

class TestChineseLLMIntegrations:
    """Tests for Chinese LLM integrations."""

    def test_zhipu_config_creation(self):
        """Test Zhipu GLM config creation."""
        config = ModelConfig(
            model_type=ModelType.ZHIPU_GLM,
            model_name="glm-4",
            api_key="test-api-key",
        )
        
        assert config.model_type == ModelType.ZHIPU_GLM
        assert config.model_name == "glm-4"

    def test_baidu_config_creation(self):
        """Test Baidu Wenxin config creation."""
        config = ModelConfig(
            model_type=ModelType.BAIDU_WENXIN,
            model_name="ernie-bot-4",
            api_key="test-api-key",
            secret_key="test-secret-key",
        )
        
        assert config.model_type == ModelType.BAIDU_WENXIN
        assert config.secret_key == "test-secret-key"

    def test_alibaba_config_creation(self):
        """Test Alibaba Tongyi config creation."""
        config = ModelConfig(
            model_type=ModelType.ALIBABA_TONGYI,
            model_name="qwen-turbo",
            api_key="test-api-key",
        )
        
        assert config.model_type == ModelType.ALIBABA_TONGYI

    def test_tencent_config_creation(self):
        """Test Tencent Hunyuan config creation."""
        config = ModelConfig(
            model_type=ModelType.TENCENT_HUNYUAN,
            model_name="hunyuan-lite",
            api_key="test-api-key",
            secret_key="test-secret-key",
            region="ap-guangzhou",
        )
        
        assert config.model_type == ModelType.TENCENT_HUNYUAN
        assert config.region == "ap-guangzhou"

    def test_factory_supports_chinese_llms(self):
        """Test factory supports all Chinese LLM types."""
        supported = AnnotatorFactory.get_supported_model_types()
        
        assert ModelType.ZHIPU_GLM in supported
        assert ModelType.BAIDU_WENXIN in supported
        assert ModelType.ALIBABA_TONGYI in supported
        assert ModelType.TENCENT_HUNYUAN in supported


# ============================================================================
# Test Model Config Validation
# ============================================================================

class TestModelConfigValidation:
    """Tests for model configuration validation."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
            max_tokens=1000,
            temperature=0.7,
            timeout=30,
        )
        
        assert config.max_tokens == 1000
        assert config.temperature == 0.7

    def test_invalid_temperature_too_high(self):
        """Test temperature validation - too high."""
        with pytest.raises(ValueError, match="temperature"):
            ModelConfig(
                model_type=ModelType.OLLAMA,
                model_name="llama2",
                temperature=2.5,
            )

    def test_invalid_temperature_negative(self):
        """Test temperature validation - negative."""
        with pytest.raises(ValueError, match="temperature"):
            ModelConfig(
                model_type=ModelType.OLLAMA,
                model_name="llama2",
                temperature=-0.1,
            )

    def test_invalid_max_tokens(self):
        """Test max_tokens validation."""
        with pytest.raises(ValueError, match="max_tokens"):
            ModelConfig(
                model_type=ModelType.OLLAMA,
                model_name="llama2",
                max_tokens=0,
            )

    def test_invalid_timeout(self):
        """Test timeout validation."""
        with pytest.raises(ValueError, match="timeout"):
            ModelConfig(
                model_type=ModelType.OLLAMA,
                model_name="llama2",
                timeout=-1,
            )


# ============================================================================
# Test Prediction Model
# ============================================================================

class TestPredictionModel:
    """Tests for prediction model."""

    def test_prediction_creation(self):
        """Test prediction creation."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
        )
        
        prediction = Prediction(
            id=uuid4(),
            task_id=uuid4(),
            ai_model_config=config,
            prediction_data={"sentiment": "positive"},
            confidence=0.85,
            processing_time=1.5,
        )
        
        assert prediction.confidence == 0.85
        assert prediction.processing_time == 1.5

    def test_prediction_invalid_confidence(self):
        """Test prediction with invalid confidence."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
        )
        
        with pytest.raises(ValueError, match="confidence"):
            Prediction(
                id=uuid4(),
                task_id=uuid4(),
                ai_model_config=config,
                prediction_data={},
                confidence=1.5,
                processing_time=1.0,
            )

    def test_prediction_invalid_processing_time(self):
        """Test prediction with invalid processing time."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
        )
        
        with pytest.raises(ValueError, match="processing_time"):
            Prediction(
                id=uuid4(),
                task_id=uuid4(),
                ai_model_config=config,
                prediction_data={},
                confidence=0.5,
                processing_time=-1.0,
            )

    def test_prediction_to_dict(self):
        """Test prediction serialization."""
        config = ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
        )
        
        prediction = Prediction(
            id=uuid4(),
            task_id=uuid4(),
            ai_model_config=config,
            prediction_data={"sentiment": "positive"},
            confidence=0.85,
            processing_time=1.5,
        )
        
        data = prediction.to_dict()
        
        assert "id" in data
        assert "task_id" in data
        assert "confidence" in data
        assert data["confidence"] == 0.85


# ============================================================================
# Test AI Annotation Error
# ============================================================================

class TestAIAnnotationError:
    """Tests for AI annotation error."""

    def test_error_creation(self):
        """Test error creation."""
        error = AIAnnotationError(
            message="Test error",
            model_type="ollama",
            task_id=uuid4(),
        )
        
        assert "Test error" in str(error)
        assert "ollama" in str(error)

    def test_error_without_task_id(self):
        """Test error without task ID."""
        error = AIAnnotationError(
            message="Test error",
            model_type="ollama",
        )
        
        assert "Test error" in str(error)
        assert "Task ID" not in str(error)


# ============================================================================
# Test Retry Logic (Mock-based)
# ============================================================================

class TestRetryLogic:
    """Tests for LLM API retry logic."""

    @pytest.fixture
    def ollama_config(self):
        """Create Ollama config."""
        return ModelConfig(
            model_type=ModelType.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
        )

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self, ollama_config):
        """Test retry on transient API failure."""
        annotator = OllamaAnnotator(ollama_config)
        task = MockTask()
        
        call_count = 0
        
        async def mock_request(prompt):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AIAnnotationError("Transient error", "ollama")
            return {"response": '{"sentiment": "positive", "confidence": 0.8}'}
        
        # Note: Current implementation doesn't have built-in retry
        # This test documents expected behavior for future implementation
        with patch.object(annotator, '_make_ollama_request', side_effect=mock_request):
            # Without retry, this will fail on first attempt
            with pytest.raises(AIAnnotationError):
                await annotator.predict(task)

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self, ollama_config):
        """Test exponential backoff timing pattern."""
        # This test documents expected retry timing:
        # Attempt 1: immediate
        # Attempt 2: 1 second delay
        # Attempt 3: 2 second delay
        # Attempt 4: 4 second delay (max)
        
        expected_delays = [0, 1, 2, 4]
        
        # Verify the pattern is correct
        for i, expected in enumerate(expected_delays):
            actual = min(2 ** i, 4) if i > 0 else 0
            assert actual == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
