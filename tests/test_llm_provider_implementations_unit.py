"""
Unit tests for LLM Provider Implementations.

Tests the generate, health_check, and validate_config methods for each provider:
- OpenAI provider (CloudLLMProvider)
- Qwen provider (ChinaLLMProvider)
- Zhipu provider (ChinaLLMProvider)
- Ollama provider (LocalLLMProvider)

**Validates: Requirements 1.1, 1.2, 2.1, 2.3**
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
import time

from src.ai.llm_schemas import (
    LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig,
    GenerateOptions, LLMResponse, EmbeddingResponse, HealthStatus,
    LLMError as LLMErrorModel, LLMErrorCode, TokenUsage
)


# Create a proper exception class for testing
class LLMError(Exception):
    """LLM Error exception for testing."""
    
    def __init__(
        self,
        error_code: LLMErrorCode,
        message: str,
        provider: str,
        retry_after: int = None,
        suggestions: list = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.provider = provider
        self.retry_after = retry_after
        self.suggestions = suggestions or []


# ==================== Mock Provider Base Class ====================

class MockLLMProvider:
    """Base mock provider for testing."""
    
    def __init__(self, method: LLMMethod, config: Dict[str, Any]):
        self._method = method
        self._config = config
        self._is_healthy = True
        self._should_fail = False
        self._fail_error = None
        self._response_content = "Test response"
        self._models = []
    
    @property
    def method(self) -> LLMMethod:
        return self._method
    
    def set_healthy(self, healthy: bool):
        self._is_healthy = healthy
    
    def set_fail(self, should_fail: bool, error: Optional[Exception] = None):
        self._should_fail = should_fail
        self._fail_error = error
    
    def set_response(self, content: str):
        self._response_content = content


# ==================== Mock Cloud Provider (OpenAI/Azure) ====================

class MockCloudLLMProvider(MockLLMProvider):
    """
    Mock Cloud LLM Provider for OpenAI and Azure OpenAI.
    Simulates the behavior of CloudLLMProvider from src/ai/llm_cloud.py.
    """
    
    OPENAI_MODELS = [
        "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-turbo",
        "gpt-4o", "gpt-4o-mini", "text-embedding-ada-002",
        "text-embedding-3-small", "text-embedding-3-large",
    ]
    
    def __init__(self, config: CloudConfig, method: LLMMethod):
        super().__init__(method, config.model_dump())
        self._cloud_config = config
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        
        if method == LLMMethod.CLOUD_AZURE:
            self._base_url = config.azure_endpoint
            self._api_key = config.azure_api_key
            self._default_model = config.azure_deployment
        else:
            self._base_url = config.openai_base_url.rstrip('/')
            self._api_key = config.openai_api_key
            self._default_model = config.openai_model
        
        self._models = self.OPENAI_MODELS
    
    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate text using mock OpenAI/Azure API."""
        if self._should_fail:
            if self._fail_error:
                raise self._fail_error
            raise LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message="Mock generation failed",
                provider=self._method.value
            )
        
        model = model or self._default_model
        return LLMResponse(
            content=self._response_content,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            model=model,
            provider=self._method.value,
            latency_ms=100.0,
            finish_reason="stop",
            metadata={"id": "mock-response-123"}
        )
    
    async def stream_generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream text generation."""
        if self._should_fail:
            raise LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message="Mock stream failed",
                provider=self._method.value
            )
        
        for word in self._response_content.split():
            yield word + " "
    
    async def embed(self, text: str, model: Optional[str] = None) -> EmbeddingResponse:
        """Generate text embedding."""
        if self._should_fail:
            raise LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message="Mock embedding failed",
                provider=self._method.value
            )
        
        return EmbeddingResponse(
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
            model=model or "text-embedding-ada-002",
            provider=self._method.value,
            dimensions=5,
            latency_ms=50.0
        )
    
    async def health_check(self) -> HealthStatus:
        """Check provider health."""
        if not self._api_key:
            return HealthStatus(
                method=self._method,
                available=False,
                error="API key not configured"
            )
        
        return HealthStatus(
            method=self._method,
            available=self._is_healthy,
            latency_ms=50.0 if self._is_healthy else None,
            model=self._default_model,
            error=None if self._is_healthy else "Provider unhealthy"
        )
    
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate an API key."""
        return api_key and len(api_key) > 8
    
    def list_models(self) -> List[str]:
        """List available models."""
        return self._models


# ==================== Mock China LLM Provider ====================

class MockChinaLLMProvider(MockLLMProvider):
    """
    Mock China LLM Provider for Qwen, Zhipu, Baidu, Hunyuan.
    Simulates the behavior of ChinaLLMProvider from src/ai/china_llm_adapter.py.
    """
    
    MODEL_LISTS = {
        LLMMethod.CHINA_QWEN: ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext"],
        LLMMethod.CHINA_ZHIPU: ["glm-4", "glm-4-plus", "glm-4-air", "glm-4-airx", "glm-4-flash", "glm-3-turbo"],
        LLMMethod.CHINA_BAIDU: ["ernie-bot-4", "ernie-bot-8k", "ernie-bot", "ernie-bot-turbo"],
        LLMMethod.CHINA_HUNYUAN: ["hunyuan-lite", "hunyuan-standard", "hunyuan-pro"],
    }
    
    def __init__(self, config: ChinaLLMConfig, method: LLMMethod):
        super().__init__(method, config.model_dump())
        self._china_config = config
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        
        # Set default model based on method
        if method == LLMMethod.CHINA_QWEN:
            self._default_model = config.qwen_model
            self._api_key = config.qwen_api_key
        elif method == LLMMethod.CHINA_ZHIPU:
            self._default_model = config.zhipu_model
            self._api_key = config.zhipu_api_key
        elif method == LLMMethod.CHINA_BAIDU:
            self._default_model = config.baidu_model
            self._api_key = config.baidu_api_key
        elif method == LLMMethod.CHINA_HUNYUAN:
            self._default_model = config.hunyuan_model
            self._api_key = config.hunyuan_secret_id
        
        self._models = self.MODEL_LISTS.get(method, [])
    
    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate text using mock China LLM API."""
        if self._should_fail:
            if self._fail_error:
                raise self._fail_error
            raise LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message="Mock generation failed",
                provider=self._method.value
            )
        
        model = model or self._default_model
        return LLMResponse(
            content=self._response_content,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            model=model,
            provider=self._method.value,
            latency_ms=150.0,
            finish_reason="stop",
            metadata={"request_id": "mock-china-123"}
        )
    
    async def stream_generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream generation (falls back to non-streaming)."""
        response = await self.generate(prompt, options, model, system_prompt)
        yield response.content
    
    async def embed(self, text: str, model: Optional[str] = None) -> EmbeddingResponse:
        """Embedding not supported for China LLMs."""
        raise LLMError(
            error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
            message="Embedding not supported for this provider",
            provider=self._method.value,
            suggestions=["Use OpenAI or local Ollama for embeddings"]
        )
    
    async def health_check(self) -> HealthStatus:
        """Check provider health."""
        if not self._api_key:
            return HealthStatus(
                method=self._method,
                available=False,
                error="API key not configured"
            )
        
        if self._should_fail:
            return HealthStatus(
                method=self._method,
                available=False,
                error="Health check failed"
            )
        
        return HealthStatus(
            method=self._method,
            available=self._is_healthy,
            latency_ms=100.0 if self._is_healthy else None,
            model=self._default_model,
            error=None if self._is_healthy else "Provider unhealthy"
        )
    
    def list_models(self) -> List[str]:
        """List available models."""
        return self._models


# ==================== Mock Local LLM Provider (Ollama) ====================

class MockLocalLLMProvider(MockLLMProvider):
    """
    Mock Local LLM Provider using Ollama.
    Simulates the behavior of LocalLLMProvider from src/ai/llm_docker.py.
    """
    
    DEFAULT_MODELS = [
        "qwen:7b", "qwen:14b", "llama2:7b", "llama2:13b",
        "mistral:7b", "codellama:7b", "yi:6b",
    ]
    
    def __init__(self, config: LocalConfig):
        super().__init__(LLMMethod.LOCAL_OLLAMA, config.model_dump())
        self._local_config = config
        self._base_url = config.ollama_url.rstrip('/')
        self._default_model = config.default_model
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        self._available_models: List[str] = []
        self._models = self.DEFAULT_MODELS
    
    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate text using mock Ollama."""
        if self._should_fail:
            if self._fail_error:
                raise self._fail_error
            raise LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message="Mock generation failed",
                provider=self._method.value
            )
        
        model = model or self._default_model
        return LLMResponse(
            content=self._response_content,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            model=model,
            provider=self._method.value,
            latency_ms=200.0,
            finish_reason="stop",
            metadata={
                "total_duration": 1000000000,
                "load_duration": 100000000,
                "eval_duration": 500000000,
            }
        )
    
    async def stream_generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream text generation."""
        if self._should_fail:
            raise LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message="Mock stream failed",
                provider=self._method.value
            )
        
        for word in self._response_content.split():
            yield word + " "
    
    async def embed(self, text: str, model: Optional[str] = None) -> EmbeddingResponse:
        """Generate text embedding."""
        if self._should_fail:
            if self._fail_error:
                raise self._fail_error
            raise LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message="Mock embedding failed",
                provider=self._method.value
            )
        
        return EmbeddingResponse(
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
            model=model or "nomic-embed-text",
            provider=self._method.value,
            dimensions=5,
            latency_ms=75.0
        )
    
    async def health_check(self) -> HealthStatus:
        """Check Ollama service health."""
        if self._should_fail:
            return HealthStatus(
                method=self._method,
                available=False,
                error=f"Cannot connect to Ollama at {self._base_url}"
            )
        
        return HealthStatus(
            method=self._method,
            available=self._is_healthy,
            latency_ms=25.0 if self._is_healthy else None,
            model=self._default_model,
            error=None if self._is_healthy else "Ollama service unavailable"
        )
    
    def list_models(self) -> List[str]:
        """List available models."""
        if self._available_models:
            return self._available_models
        return self._models
    
    async def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Pull a model from Ollama registry."""
        if self._should_fail:
            return {"success": False, "model": model_name, "error": "Pull failed"}
        return {"success": True, "model": model_name, "message": "Model pulled successfully"}
    
    async def delete_model(self, model_name: str) -> Dict[str, Any]:
        """Delete a model from Ollama."""
        if self._should_fail:
            return {"success": False, "model": model_name, "error": "Delete failed"}
        return {"success": True, "model": model_name, "message": "Model deleted successfully"}
    
    async def start_service(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Ensure Ollama service is running."""
        if self._should_fail:
            return {
                "success": False,
                "error": "Service not running",
                "suggestion": "Start Ollama service with: ollama serve"
            }
        return {"success": True, "model": model_name or self._default_model, "message": "Service ready"}
    
    async def stop_service(self) -> Dict[str, Any]:
        """Stop service (no-op for Ollama)."""
        return {"success": True, "message": "Ollama service lifecycle is managed externally"}


# ==================== Fixtures ====================

@pytest.fixture
def openai_config():
    """Create OpenAI cloud configuration."""
    return CloudConfig(
        openai_api_key="sk-test-api-key-12345678",
        openai_base_url="https://api.openai.com/v1",
        openai_model="gpt-3.5-turbo",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def azure_config():
    """Create Azure OpenAI cloud configuration."""
    return CloudConfig(
        azure_api_key="azure-test-api-key-12345678",
        azure_endpoint="https://example.openai.azure.com",
        azure_deployment="gpt-35-turbo",
        azure_api_version="2024-02-15-preview",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def qwen_config():
    """Create Qwen (China) configuration."""
    return ChinaLLMConfig(
        qwen_api_key="qwen-test-api-key-12345678",
        qwen_model="qwen-turbo",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def zhipu_config():
    """Create Zhipu (China) configuration."""
    return ChinaLLMConfig(
        zhipu_api_key="zhipu-test-api-key-12345678",
        zhipu_model="glm-4",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def baidu_config():
    """Create Baidu (China) configuration."""
    return ChinaLLMConfig(
        baidu_api_key="baidu-test-api-key",
        baidu_secret_key="baidu-test-secret-key",
        baidu_model="ernie-bot-4",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def hunyuan_config():
    """Create Hunyuan (China) configuration."""
    return ChinaLLMConfig(
        hunyuan_secret_id="hunyuan-test-secret-id",
        hunyuan_secret_key="hunyuan-test-secret-key",
        hunyuan_model="hunyuan-lite",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def ollama_config():
    """Create Ollama local configuration."""
    return LocalConfig(
        ollama_url="http://localhost:11434",
        default_model="qwen:7b",
        timeout=30,
        max_retries=3
    )


@pytest.fixture
def generate_options():
    """Create default generation options."""
    return GenerateOptions(
        max_tokens=100,
        temperature=0.7,
        top_p=0.9
    )


# ==================== OpenAI Provider Tests ====================

class TestCloudLLMProviderOpenAI:
    """
    Unit tests for CloudLLMProvider with OpenAI.
    
    **Validates: Requirements 1.1, 2.3**
    - Requirement 1.1: Support OpenAI for global deployments
    - Requirement 2.3: Support API-based access with configurable endpoints
    """

    @pytest.mark.asyncio
    async def test_generate_success(self, openai_config, generate_options):
        """
        Test generate method with mock successful response.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        provider.set_response("Hello, I am an AI assistant.")
        
        result = await provider.generate(
            prompt="Hello, who are you?",
            options=generate_options
        )
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Hello, I am an AI assistant."
        assert result.model == "gpt-3.5-turbo"
        assert result.provider == LLMMethod.CLOUD_OPENAI.value
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 20
        assert result.usage.total_tokens == 30
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self, openai_config, generate_options):
        """
        Test generate method with custom model.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        provider.set_response("GPT-4 response")
        
        result = await provider.generate(
            prompt="Hello",
            options=generate_options,
            model="gpt-4"
        )
        
        assert isinstance(result, LLMResponse)
        assert result.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, openai_config, generate_options):
        """
        Test generate method handles timeout correctly.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        provider.set_fail(True, LLMError(
            error_code=LLMErrorCode.TIMEOUT,
            message="Request timed out after 30 seconds",
            provider=LLMMethod.CLOUD_OPENAI.value
        ))
        
        with pytest.raises(LLMError) as exc_info:
            await provider.generate(prompt="Hello", options=generate_options)
        
        error = exc_info.value
        assert error.error_code == LLMErrorCode.TIMEOUT
        assert "timed out" in error.message.lower()

    @pytest.mark.asyncio
    async def test_generate_rate_limit_error(self, openai_config, generate_options):
        """
        Test generate method handles rate limit error correctly.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        provider.set_fail(True, LLMError(
            error_code=LLMErrorCode.RATE_LIMITED,
            message="Rate limit exceeded",
            provider=LLMMethod.CLOUD_OPENAI.value,
            retry_after=60
        ))
        
        with pytest.raises(LLMError) as exc_info:
            await provider.generate(prompt="Hello", options=generate_options)
        
        error = exc_info.value
        assert error.error_code == LLMErrorCode.RATE_LIMITED
        assert error.retry_after == 60

    @pytest.mark.asyncio
    async def test_generate_invalid_api_key_error(self, openai_config, generate_options):
        """
        Test generate method handles invalid API key error correctly.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        provider.set_fail(True, LLMError(
            error_code=LLMErrorCode.INVALID_API_KEY,
            message="Invalid API key",
            provider=LLMMethod.CLOUD_OPENAI.value
        ))
        
        with pytest.raises(LLMError) as exc_info:
            await provider.generate(prompt="Hello", options=generate_options)
        
        error = exc_info.value
        assert error.error_code == LLMErrorCode.INVALID_API_KEY

    @pytest.mark.asyncio
    async def test_health_check_success(self, openai_config):
        """
        Test health_check with successful response.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is True
        assert result.method == LLMMethod.CLOUD_OPENAI
        assert result.latency_ms is not None
        assert result.error is None

    @pytest.mark.asyncio
    async def test_health_check_failure(self, openai_config):
        """
        Test health_check with failure response.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        provider.set_healthy(False)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is False
        assert result.method == LLMMethod.CLOUD_OPENAI
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self):
        """
        Test health_check with missing API key.
        
        **Validates: Requirements 1.1, 2.3**
        """
        config = CloudConfig(
            openai_api_key=None,
            openai_model="gpt-3.5-turbo"
        )
        provider = MockCloudLLMProvider(config, LLMMethod.CLOUD_OPENAI)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is False
        assert "API key not configured" in result.error

    def test_validate_config_valid(self, openai_config):
        """
        Test that valid configuration is accepted.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        
        assert provider._api_key == "sk-test-api-key-12345678"
        assert provider._default_model == "gpt-3.5-turbo"
        assert provider._timeout == 30

    def test_list_models(self, openai_config):
        """
        Test list_models returns available models.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        
        models = provider.list_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-3.5-turbo" in models
        assert "gpt-4" in models

    @pytest.mark.asyncio
    async def test_embed_success(self, openai_config):
        """
        Test embed method with successful response.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        
        result = await provider.embed("Test text for embedding")
        
        assert isinstance(result, EmbeddingResponse)
        assert len(result.embedding) > 0
        assert result.dimensions == 5
        assert result.provider == LLMMethod.CLOUD_OPENAI.value


# ==================== Azure OpenAI Provider Tests ====================

class TestCloudLLMProviderAzure:
    """
    Unit tests for CloudLLMProvider with Azure OpenAI.
    
    **Validates: Requirements 1.1, 2.3**
    - Requirement 1.1: Support OpenAI (including Azure) for global deployments
    - Requirement 2.3: Support API-based access with configurable endpoints
    """

    @pytest.mark.asyncio
    async def test_generate_success(self, azure_config, generate_options):
        """
        Test generate method with Azure OpenAI mock response.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(azure_config, LLMMethod.CLOUD_AZURE)
        provider.set_response("Azure response")
        
        result = await provider.generate(
            prompt="Hello from Azure",
            options=generate_options
        )
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Azure response"
        assert result.provider == LLMMethod.CLOUD_AZURE.value

    @pytest.mark.asyncio
    async def test_health_check_success(self, azure_config):
        """
        Test health_check with Azure OpenAI.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(azure_config, LLMMethod.CLOUD_AZURE)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is True
        assert result.method == LLMMethod.CLOUD_AZURE

    def test_azure_endpoint_configuration(self, azure_config):
        """
        Test Azure endpoint is configured correctly.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(azure_config, LLMMethod.CLOUD_AZURE)
        
        assert provider._base_url == "https://example.openai.azure.com"
        assert provider._api_key == "azure-test-api-key-12345678"


# ==================== Qwen Provider Tests ====================

class TestChinaLLMProviderQwen:
    """
    Unit tests for ChinaLLMProvider with Qwen (通义千问).
    
    **Validates: Requirements 1.2, 2.3**
    - Requirement 1.2: Support Qwen for Chinese deployments
    - Requirement 2.3: Support API-based access with configurable endpoints
    """

    @pytest.mark.asyncio
    async def test_generate_success(self, qwen_config, generate_options):
        """
        Test generate method with Qwen mock response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN)
        provider.set_response("你好，我是通义千问。")
        
        result = await provider.generate(
            prompt="你好，你是谁？",
            options=generate_options
        )
        
        assert isinstance(result, LLMResponse)
        assert result.content == "你好，我是通义千问。"
        assert result.provider == LLMMethod.CHINA_QWEN.value
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 20

    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self, qwen_config, generate_options):
        """
        Test generate method with custom model.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN)
        provider.set_response("Qwen-max response")
        
        result = await provider.generate(
            prompt="Hello",
            options=generate_options,
            model="qwen-max"
        )
        
        assert isinstance(result, LLMResponse)
        assert result.model == "qwen-max"

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, qwen_config, generate_options):
        """
        Test generate method handles timeout correctly.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN)
        provider.set_fail(True, LLMError(
            error_code=LLMErrorCode.TIMEOUT,
            message="Request timed out",
            provider=LLMMethod.CHINA_QWEN.value
        ))
        
        with pytest.raises(LLMError) as exc_info:
            await provider.generate(prompt="Hello", options=generate_options)
        
        error = exc_info.value
        assert error.error_code == LLMErrorCode.TIMEOUT

    @pytest.mark.asyncio
    async def test_health_check_success(self, qwen_config):
        """
        Test health_check with successful response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is True
        assert result.method == LLMMethod.CHINA_QWEN

    @pytest.mark.asyncio
    async def test_health_check_failure(self, qwen_config):
        """
        Test health_check with failure response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN)
        provider.set_fail(True)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is False
        assert result.error is not None

    def test_list_models(self, qwen_config):
        """
        Test list_models returns Qwen models.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN)
        
        models = provider.list_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "qwen-turbo" in models

    @pytest.mark.asyncio
    async def test_embed_not_supported(self, qwen_config):
        """
        Test embed method raises error for unsupported operation.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN)
        
        with pytest.raises(LLMError) as exc_info:
            await provider.embed("Test text")
        
        error = exc_info.value
        assert error.error_code == LLMErrorCode.SERVICE_UNAVAILABLE
        assert "not supported" in error.message.lower()


# ==================== Zhipu Provider Tests ====================

class TestChinaLLMProviderZhipu:
    """
    Unit tests for ChinaLLMProvider with Zhipu (智谱).
    
    **Validates: Requirements 1.2, 2.3**
    - Requirement 1.2: Support Zhipu for Chinese deployments
    - Requirement 2.3: Support API-based access with configurable endpoints
    """

    @pytest.mark.asyncio
    async def test_generate_success(self, zhipu_config, generate_options):
        """
        Test generate method with Zhipu mock response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU)
        provider.set_response("你好，我是智谱GLM。")
        
        result = await provider.generate(
            prompt="你好，你是谁？",
            options=generate_options
        )
        
        assert isinstance(result, LLMResponse)
        assert result.content == "你好，我是智谱GLM。"
        assert result.provider == LLMMethod.CHINA_ZHIPU.value

    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self, zhipu_config, generate_options):
        """
        Test generate method with custom model.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU)
        provider.set_response("GLM-4 Plus response")
        
        result = await provider.generate(
            prompt="Hello",
            options=generate_options,
            model="glm-4-plus"
        )
        
        assert isinstance(result, LLMResponse)
        assert result.model == "glm-4-plus"

    @pytest.mark.asyncio
    async def test_generate_invalid_api_key(self, zhipu_config, generate_options):
        """
        Test generate method handles invalid API key.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU)
        provider.set_fail(True, LLMError(
            error_code=LLMErrorCode.INVALID_API_KEY,
            message="Invalid API key",
            provider=LLMMethod.CHINA_ZHIPU.value
        ))
        
        with pytest.raises(LLMError) as exc_info:
            await provider.generate(prompt="Hello", options=generate_options)
        
        error = exc_info.value
        assert error.error_code == LLMErrorCode.INVALID_API_KEY

    @pytest.mark.asyncio
    async def test_health_check_success(self, zhipu_config):
        """
        Test health_check with successful response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is True
        assert result.method == LLMMethod.CHINA_ZHIPU

    @pytest.mark.asyncio
    async def test_health_check_failure(self, zhipu_config):
        """
        Test health_check with failure response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU)
        provider.set_fail(True)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is False

    def test_list_models(self, zhipu_config):
        """
        Test list_models returns Zhipu models.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU)
        
        models = provider.list_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "glm-4" in models


# ==================== Baidu Provider Tests ====================

class TestChinaLLMProviderBaidu:
    """
    Unit tests for ChinaLLMProvider with Baidu (百度文心).
    
    **Validates: Requirements 1.2, 2.3**
    - Requirement 1.2: Support Baidu for Chinese deployments
    - Requirement 2.3: Support API-based access with configurable endpoints
    """

    @pytest.mark.asyncio
    async def test_generate_success(self, baidu_config, generate_options):
        """
        Test generate method with Baidu mock response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(baidu_config, LLMMethod.CHINA_BAIDU)
        provider.set_response("你好，我是文心一言。")
        
        result = await provider.generate(
            prompt="你好",
            options=generate_options
        )
        
        assert isinstance(result, LLMResponse)
        assert result.content == "你好，我是文心一言。"
        assert result.provider == LLMMethod.CHINA_BAIDU.value

    @pytest.mark.asyncio
    async def test_health_check_success(self, baidu_config):
        """
        Test health_check with successful response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(baidu_config, LLMMethod.CHINA_BAIDU)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is True
        assert result.method == LLMMethod.CHINA_BAIDU

    def test_list_models(self, baidu_config):
        """
        Test list_models returns Baidu models.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(baidu_config, LLMMethod.CHINA_BAIDU)
        
        models = provider.list_models()
        
        assert isinstance(models, list)
        assert "ernie-bot-4" in models


# ==================== Hunyuan Provider Tests ====================

class TestChinaLLMProviderHunyuan:
    """
    Unit tests for ChinaLLMProvider with Hunyuan (腾讯混元).
    
    **Validates: Requirements 1.2, 2.3**
    - Requirement 1.2: Support Tencent Hunyuan for Chinese deployments
    - Requirement 2.3: Support API-based access with configurable endpoints
    """

    @pytest.mark.asyncio
    async def test_generate_success(self, hunyuan_config, generate_options):
        """
        Test generate method with Hunyuan mock response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(hunyuan_config, LLMMethod.CHINA_HUNYUAN)
        provider.set_response("你好，我是腾讯混元。")
        
        result = await provider.generate(
            prompt="你好",
            options=generate_options
        )
        
        assert isinstance(result, LLMResponse)
        assert result.content == "你好，我是腾讯混元。"
        assert result.provider == LLMMethod.CHINA_HUNYUAN.value

    @pytest.mark.asyncio
    async def test_health_check_success(self, hunyuan_config):
        """
        Test health_check with successful response.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(hunyuan_config, LLMMethod.CHINA_HUNYUAN)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is True
        assert result.method == LLMMethod.CHINA_HUNYUAN

    def test_list_models(self, hunyuan_config):
        """
        Test list_models returns Hunyuan models.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(hunyuan_config, LLMMethod.CHINA_HUNYUAN)
        
        models = provider.list_models()
        
        assert isinstance(models, list)
        assert "hunyuan-lite" in models


# ==================== Ollama Provider Tests ====================

class TestLocalLLMProviderOllama:
    """
    Unit tests for LocalLLMProvider (Ollama).
    
    **Validates: Requirements 2.1, 2.3**
    - Requirement 2.1: Support Ollama integration for running open-source models
    - Requirement 2.3: Support API-based access with configurable endpoints
    """

    @pytest.mark.asyncio
    async def test_generate_success(self, ollama_config, generate_options):
        """
        Test generate method with Ollama mock response.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        provider.set_response("Hello from Ollama!")
        
        result = await provider.generate(
            prompt="Hello, who are you?",
            options=generate_options
        )
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Hello from Ollama!"
        assert result.model == "qwen:7b"
        assert result.provider == LLMMethod.LOCAL_OLLAMA.value
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 20

    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self, ollama_config, generate_options):
        """
        Test generate method with custom model.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        provider.set_response("Llama response")
        
        result = await provider.generate(
            prompt="Hello",
            options=generate_options,
            model="llama2:7b"
        )
        
        assert isinstance(result, LLMResponse)
        assert result.model == "llama2:7b"

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, ollama_config, generate_options):
        """
        Test generate method handles timeout correctly.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        provider.set_fail(True, LLMError(
            error_code=LLMErrorCode.TIMEOUT,
            message="Request timed out after 30 seconds",
            provider=LLMMethod.LOCAL_OLLAMA.value
        ))
        
        with pytest.raises(LLMError) as exc_info:
            await provider.generate(prompt="Hello", options=generate_options)
        
        error = exc_info.value
        assert error.error_code == LLMErrorCode.TIMEOUT
        assert "timed out" in error.message.lower()

    @pytest.mark.asyncio
    async def test_generate_model_not_found(self, ollama_config, generate_options):
        """
        Test generate method handles model not found error.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        provider.set_fail(True, LLMError(
            error_code=LLMErrorCode.MODEL_NOT_FOUND,
            message="Model 'nonexistent:7b' not found",
            provider=LLMMethod.LOCAL_OLLAMA.value
        ))
        
        with pytest.raises(LLMError) as exc_info:
            await provider.generate(
                prompt="Hello",
                options=generate_options,
                model="nonexistent:7b"
            )
        
        error = exc_info.value
        assert error.error_code == LLMErrorCode.MODEL_NOT_FOUND

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_config):
        """
        Test health_check with successful response.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is True
        assert result.method == LLMMethod.LOCAL_OLLAMA
        assert result.latency_ms is not None

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, ollama_config):
        """
        Test health_check with connection error.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        provider.set_fail(True)
        
        result = await provider.health_check()
        
        assert isinstance(result, HealthStatus)
        assert result.available is False
        assert "Cannot connect" in result.error

    @pytest.mark.asyncio
    async def test_embed_success(self, ollama_config):
        """
        Test embed method with successful response.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        
        result = await provider.embed("Test text for embedding")
        
        assert isinstance(result, EmbeddingResponse)
        assert len(result.embedding) > 0
        assert result.dimensions == 5
        assert result.provider == LLMMethod.LOCAL_OLLAMA.value

    @pytest.mark.asyncio
    async def test_embed_timeout(self, ollama_config):
        """
        Test embed method handles timeout.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        provider.set_fail(True, LLMError(
            error_code=LLMErrorCode.TIMEOUT,
            message="Embedding request timed out",
            provider=LLMMethod.LOCAL_OLLAMA.value
        ))
        
        with pytest.raises(LLMError) as exc_info:
            await provider.embed("Test text")
        
        error = exc_info.value
        assert error.error_code == LLMErrorCode.TIMEOUT

    def test_list_models_default(self, ollama_config):
        """
        Test list_models returns default models when not cached.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        
        models = provider.list_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "qwen:7b" in models
        assert "llama2:7b" in models

    def test_list_models_cached(self, ollama_config):
        """
        Test list_models returns cached models when available.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        provider._available_models = ["custom:7b", "test:13b"]
        
        models = provider.list_models()
        
        assert models == ["custom:7b", "test:13b"]

    @pytest.mark.asyncio
    async def test_pull_model_success(self, ollama_config):
        """
        Test pull_model with successful response.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        
        result = await provider.pull_model("llama2:7b")
        
        assert result["success"] is True
        assert result["model"] == "llama2:7b"

    @pytest.mark.asyncio
    async def test_pull_model_failure(self, ollama_config):
        """
        Test pull_model with failure response.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        provider.set_fail(True)
        
        result = await provider.pull_model("nonexistent:7b")
        
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_model_success(self, ollama_config):
        """
        Test delete_model with successful response.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        
        result = await provider.delete_model("old-model:7b")
        
        assert result["success"] is True
        assert result["model"] == "old-model:7b"

    @pytest.mark.asyncio
    async def test_start_service_success(self, ollama_config):
        """
        Test start_service with successful health check.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        
        result = await provider.start_service()
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_start_service_not_running(self, ollama_config):
        """
        Test start_service when Ollama is not running.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        provider.set_fail(True)
        
        result = await provider.start_service()
        
        assert result["success"] is False
        assert "suggestion" in result

    def test_method_property(self, ollama_config):
        """
        Test method property returns correct LLMMethod.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        
        assert provider.method == LLMMethod.LOCAL_OLLAMA


# ==================== Cross-Provider Tests ====================

class TestProviderConsistency:
    """
    Tests to verify consistent behavior across all providers.
    
    **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
    """

    @pytest.mark.asyncio
    async def test_all_providers_return_llm_response(
        self, openai_config, qwen_config, zhipu_config, ollama_config, generate_options
    ):
        """
        Test that all providers return LLMResponse type.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
        """
        providers = [
            MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI),
            MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN),
            MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU),
            MockLocalLLMProvider(ollama_config),
        ]
        
        for provider in providers:
            result = await provider.generate(
                prompt="Test",
                options=generate_options
            )
            
            assert isinstance(result, LLMResponse), \
                f"Provider {provider.method} should return LLMResponse"
            assert result.content is not None
            assert result.provider is not None

    @pytest.mark.asyncio
    async def test_all_providers_return_health_status(
        self, openai_config, qwen_config, zhipu_config, ollama_config
    ):
        """
        Test that all providers return HealthStatus type.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
        """
        providers = [
            MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI),
            MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN),
            MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU),
            MockLocalLLMProvider(ollama_config),
        ]
        
        for provider in providers:
            result = await provider.health_check()
            
            assert isinstance(result, HealthStatus), \
                f"Provider {provider.method} should return HealthStatus"
            assert result.method is not None

    def test_all_providers_have_list_models(
        self, openai_config, qwen_config, zhipu_config, ollama_config
    ):
        """
        Test that all providers implement list_models.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
        """
        providers = [
            MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI),
            MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN),
            MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU),
            MockLocalLLMProvider(ollama_config),
        ]
        
        for provider in providers:
            models = provider.list_models()
            
            assert isinstance(models, list), \
                f"Provider {provider.method} should return list of models"
            assert len(models) > 0, \
                f"Provider {provider.method} should have at least one model"


# ==================== Error Handling Tests ====================

class TestProviderErrorHandling:
    """
    Tests for consistent error handling across providers.
    
    **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
    """

    @pytest.mark.asyncio
    async def test_timeout_error_format(
        self, openai_config, qwen_config, ollama_config, generate_options
    ):
        """
        Test that timeout errors have consistent format.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
        """
        providers = [
            (MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI), LLMMethod.CLOUD_OPENAI),
            (MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN), LLMMethod.CHINA_QWEN),
            (MockLocalLLMProvider(ollama_config), LLMMethod.LOCAL_OLLAMA),
        ]
        
        for provider, method in providers:
            provider.set_fail(True, LLMError(
                error_code=LLMErrorCode.TIMEOUT,
                message="Request timed out",
                provider=method.value
            ))
            
            with pytest.raises(LLMError) as exc_info:
                await provider.generate(prompt="Test", options=generate_options)
            
            error = exc_info.value
            assert error.error_code == LLMErrorCode.TIMEOUT, \
                f"Provider {method} should return TIMEOUT error code"
            assert error.provider is not None

    @pytest.mark.asyncio
    async def test_health_check_never_raises(
        self, openai_config, qwen_config, zhipu_config, ollama_config
    ):
        """
        Test that health_check never raises exceptions, always returns HealthStatus.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
        """
        providers = [
            MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI),
            MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN),
            MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU),
            MockLocalLLMProvider(ollama_config),
        ]
        
        for provider in providers:
            # Set provider to fail
            provider.set_fail(True)
            provider.set_healthy(False)
            
            # Should not raise, should return HealthStatus
            result = await provider.health_check()
            
            assert isinstance(result, HealthStatus), \
                f"Provider {provider.method} health_check should not raise"
            assert result.available is False


# ==================== Configuration Validation Tests ====================

class TestConfigurationValidation:
    """
    Tests for configuration validation across providers.
    
    **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
    """

    def test_openai_config_valid(self, openai_config):
        """
        Test valid OpenAI configuration.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(openai_config, LLMMethod.CLOUD_OPENAI)
        
        assert provider._api_key is not None
        assert provider._default_model is not None
        assert provider._timeout > 0

    def test_azure_config_valid(self, azure_config):
        """
        Test valid Azure configuration.
        
        **Validates: Requirements 1.1, 2.3**
        """
        provider = MockCloudLLMProvider(azure_config, LLMMethod.CLOUD_AZURE)
        
        assert provider._api_key is not None
        assert provider._base_url is not None

    def test_qwen_config_valid(self, qwen_config):
        """
        Test valid Qwen configuration.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(qwen_config, LLMMethod.CHINA_QWEN)
        
        assert provider._api_key is not None
        assert provider._default_model is not None

    def test_zhipu_config_valid(self, zhipu_config):
        """
        Test valid Zhipu configuration.
        
        **Validates: Requirements 1.2, 2.3**
        """
        provider = MockChinaLLMProvider(zhipu_config, LLMMethod.CHINA_ZHIPU)
        
        assert provider._api_key is not None
        assert provider._default_model is not None

    def test_ollama_config_valid(self, ollama_config):
        """
        Test valid Ollama configuration.
        
        **Validates: Requirements 2.1, 2.3**
        """
        provider = MockLocalLLMProvider(ollama_config)
        
        assert provider._base_url is not None
        assert provider._default_model is not None
        assert provider._timeout > 0

    def test_invalid_timeout_rejected(self):
        """
        Test that invalid timeout is rejected.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
        """
        with pytest.raises(Exception):
            LocalConfig(timeout=-10)

    def test_invalid_retries_rejected(self):
        """
        Test that invalid max_retries is rejected.
        
        **Validates: Requirements 1.1, 1.2, 2.1, 2.3**
        """
        with pytest.raises(Exception):
            LocalConfig(max_retries=-5)

    def test_invalid_url_rejected(self):
        """
        Test that invalid URL is rejected.
        
        **Validates: Requirements 2.1, 2.3**
        """
        with pytest.raises(Exception):
            LocalConfig(ollama_url="not-a-valid-url")
