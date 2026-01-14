"""
China LLM Adapter for SuperInsight platform.

Provides unified interface for Chinese LLM providers (Qwen, Zhipu, Baidu, Hunyuan)
with format conversion and exponential backoff retry.
"""

import asyncio
import time
import logging
import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

try:
    from src.ai.llm_schemas import (
        LLMMethod, ChinaLLMConfig, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, TokenUsage, HealthStatus
    )
    from src.ai.llm_switcher import LLMProvider
except ImportError:
    from ai.llm_schemas import (
        LLMMethod, ChinaLLMConfig, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, TokenUsage, HealthStatus
    )
    from ai.llm_switcher import LLMProvider

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for exponential backoff retry."""
    
    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt (0-indexed)."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


class BaseChinaAdapter(ABC):
    """Base class for China LLM adapters."""
    
    def __init__(self, config: ChinaLLMConfig, retry_config: Optional[RetryConfig] = None):
        self._config = config
        self._retry_config = retry_config or RetryConfig(max_retries=config.max_retries)
        self._timeout = config.timeout
    
    @property
    @abstractmethod
    def method(self) -> LLMMethod:
        """Return the LLM method."""
        pass
    
    @property
    @abstractmethod
    def api_base(self) -> str:
        """Return the API base URL."""
        pass
    
    @abstractmethod
    def _to_native_format(
        self,
        prompt: str,
        options: GenerateOptions,
        model: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert to provider-specific format."""
        pass
    
    @abstractmethod
    def _from_native_format(self, response: Dict[str, Any], model: str) -> LLMResponse:
        """Convert from provider-specific format."""
        pass
    
    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        pass
    
    @abstractmethod
    def _get_default_model(self) -> str:
        """Get default model name."""
        pass
    
    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate text with retry logic."""
        model = model or self._get_default_model()
        payload = self._to_native_format(prompt, options, model, system_prompt)
        
        start_time = time.time()
        last_error = None
        
        for attempt in range(self._retry_config.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        self._get_generate_endpoint(),
                        headers=self._get_headers(),
                        json=payload
                    )
                    
                    # Check for rate limiting
                    if response.status_code == 429:
                        delay = self._retry_config.get_delay(attempt)
                        logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                        await asyncio.sleep(delay)
                        continue
                    
                    response.raise_for_status()
                    
                    data = response.json()
                    result = self._from_native_format(data, model)
                    result.latency_ms = (time.time() - start_time) * 1000
                    return result
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    delay = self._retry_config.get_delay(attempt)
                    logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    last_error = e
                    continue
                raise self._handle_error(e)
            except httpx.TimeoutException:
                raise LLMError(
                    error_code=LLMErrorCode.TIMEOUT,
                    message=f"Request timed out after {self._timeout} seconds",
                    provider=self.method.value
                )
            except Exception as e:
                last_error = e
                if attempt < self._retry_config.max_retries - 1:
                    delay = self._retry_config.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                break
        
        raise LLMError(
            error_code=LLMErrorCode.RATE_LIMITED,
            message=f"Max retries exceeded: {last_error}",
            provider=self.method.value,
            retry_after=int(self._retry_config.get_delay(self._retry_config.max_retries))
        )
    
    def _get_generate_endpoint(self) -> str:
        """Get generation endpoint URL."""
        return f"{self.api_base}/chat/completions"
    
    def _handle_error(self, error: httpx.HTTPStatusError) -> LLMError:
        """Convert HTTP error to LLMError."""
        status_code = error.response.status_code
        
        try:
            data = error.response.json()
            message = data.get("error", {}).get("message", str(data))
        except Exception:
            message = error.response.text
        
        if status_code == 401:
            return LLMError(
                error_code=LLMErrorCode.INVALID_API_KEY,
                message=f"Invalid API key: {message}",
                provider=self.method.value
            )
        elif status_code == 429:
            return LLMError(
                error_code=LLMErrorCode.RATE_LIMITED,
                message=f"Rate limited: {message}",
                provider=self.method.value,
                retry_after=60
            )
        else:
            return LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message=f"HTTP {status_code}: {message}",
                provider=self.method.value
            )


class QwenAdapter(BaseChinaAdapter):
    """
    Adapter for Alibaba Cloud DashScope (Qwen) API.
    
    API Documentation: https://help.aliyun.com/document_detail/2712195.html
    """
    
    API_BASE = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation"
    
    MODELS = [
        "qwen-turbo",
        "qwen-plus",
        "qwen-max",
        "qwen-max-longcontext",
    ]
    
    @property
    def method(self) -> LLMMethod:
        return LLMMethod.CHINA_QWEN
    
    @property
    def api_base(self) -> str:
        return self.API_BASE
    
    def _get_default_model(self) -> str:
        return self._config.qwen_model
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.qwen_api_key}",
            "Content-Type": "application/json"
        }
    
    def _get_generate_endpoint(self) -> str:
        return f"{self.api_base}/generation"
    
    def _to_native_format(
        self,
        prompt: str,
        options: GenerateOptions,
        model: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert to DashScope format."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return {
            "model": model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "max_tokens": options.max_tokens,
                "temperature": options.temperature,
                "top_p": options.top_p,
                "result_format": "message"
            }
        }
    
    def _from_native_format(self, response: Dict[str, Any], model: str) -> LLMResponse:
        """Convert from DashScope format."""
        output = response.get("output", {})
        usage = response.get("usage", {})
        
        # Extract content from message format
        choices = output.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            finish_reason = choices[0].get("finish_reason", "stop")
        else:
            content = output.get("text", "")
            finish_reason = output.get("finish_reason", "stop")
        
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("total_tokens", 0)
            ),
            model=model,
            provider=self.method.value,
            latency_ms=0,
            finish_reason=finish_reason,
            metadata={"request_id": response.get("request_id")}
        )


class ZhipuAdapter(BaseChinaAdapter):
    """
    Adapter for Zhipu AI (GLM) API.
    
    API Documentation: https://open.bigmodel.cn/dev/api
    """
    
    API_BASE = "https://open.bigmodel.cn/api/paas/v4"
    
    MODELS = [
        "glm-4",
        "glm-4-plus",
        "glm-4-air",
        "glm-4-airx",
        "glm-4-flash",
        "glm-3-turbo",
    ]
    
    @property
    def method(self) -> LLMMethod:
        return LLMMethod.CHINA_ZHIPU
    
    @property
    def api_base(self) -> str:
        return self.API_BASE
    
    def _get_default_model(self) -> str:
        return self._config.zhipu_model
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.zhipu_api_key}",
            "Content-Type": "application/json"
        }
    
    def _to_native_format(
        self,
        prompt: str,
        options: GenerateOptions,
        model: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert to Zhipu format."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return {
            "model": model,
            "messages": messages,
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
            "top_p": options.top_p
        }
    
    def _from_native_format(self, response: Dict[str, Any], model: str) -> LLMResponse:
        """Convert from Zhipu format."""
        choices = response.get("choices", [{}])
        choice = choices[0] if choices else {}
        
        content = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason", "stop")
        
        usage = response.get("usage", {})
        
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0)
            ),
            model=response.get("model", model),
            provider=self.method.value,
            latency_ms=0,
            finish_reason=finish_reason,
            metadata={"id": response.get("id")}
        )


class BaiduAdapter(BaseChinaAdapter):
    """
    Adapter for Baidu Wenxin (ERNIE) API.
    
    API Documentation: https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html
    """
    
    API_BASE = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat"
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    
    MODELS = [
        "ernie-bot-4",
        "ernie-bot-8k",
        "ernie-bot",
        "ernie-bot-turbo",
    ]
    
    MODEL_ENDPOINTS = {
        "ernie-bot-4": "completions_pro",
        "ernie-bot-8k": "ernie_bot_8k",
        "ernie-bot": "completions",
        "ernie-bot-turbo": "eb-instant",
    }
    
    def __init__(self, config: ChinaLLMConfig, retry_config: Optional[RetryConfig] = None):
        super().__init__(config, retry_config)
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
    
    @property
    def method(self) -> LLMMethod:
        return LLMMethod.CHINA_BAIDU
    
    @property
    def api_base(self) -> str:
        return self.API_BASE
    
    def _get_default_model(self) -> str:
        return self._config.baidu_model
    
    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}
    
    def _get_generate_endpoint(self) -> str:
        model = self._get_default_model()
        endpoint = self.MODEL_ENDPOINTS.get(model, "completions")
        return f"{self.api_base}/{endpoint}"
    
    async def _get_access_token(self) -> str:
        """Get or refresh access token."""
        if self._access_token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._access_token
        
        params = {
            "grant_type": "client_credentials",
            "client_id": self._config.baidu_api_key,
            "client_secret": self._config.baidu_secret_key
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self.TOKEN_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            self._access_token = data["access_token"]
            # Token expires in 30 days, refresh after 29 days
            self._token_expires = datetime.utcnow().replace(day=datetime.utcnow().day + 29)
            
            return self._access_token
    
    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Override to add access token."""
        token = await self._get_access_token()
        
        model = model or self._get_default_model()
        endpoint = self.MODEL_ENDPOINTS.get(model, "completions")
        url = f"{self.api_base}/{endpoint}?access_token={token}"
        
        payload = self._to_native_format(prompt, options, model, system_prompt)
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if "error_code" in data:
                raise LLMError(
                    error_code=LLMErrorCode.GENERATION_FAILED,
                    message=data.get("error_msg", "Unknown error"),
                    provider=self.method.value
                )
            
            result = self._from_native_format(data, model)
            result.latency_ms = (time.time() - start_time) * 1000
            return result
    
    def _to_native_format(
        self,
        prompt: str,
        options: GenerateOptions,
        model: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert to Baidu format."""
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "messages": messages,
            "max_output_tokens": options.max_tokens,
            "temperature": options.temperature,
            "top_p": options.top_p
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        return payload
    
    def _from_native_format(self, response: Dict[str, Any], model: str) -> LLMResponse:
        """Convert from Baidu format."""
        usage = response.get("usage", {})
        
        return LLMResponse(
            content=response.get("result", ""),
            usage=TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0)
            ),
            model=model,
            provider=self.method.value,
            latency_ms=0,
            finish_reason=response.get("finish_reason", "stop"),
            metadata={"id": response.get("id")}
        )


class HunyuanAdapter(BaseChinaAdapter):
    """
    Adapter for Tencent Hunyuan API.
    
    API Documentation: https://cloud.tencent.com/document/product/1729
    """
    
    API_BASE = "https://hunyuan.tencentcloudapi.com"
    
    MODELS = [
        "hunyuan-lite",
        "hunyuan-standard",
        "hunyuan-pro",
    ]
    
    @property
    def method(self) -> LLMMethod:
        return LLMMethod.CHINA_HUNYUAN
    
    @property
    def api_base(self) -> str:
        return self.API_BASE
    
    def _get_default_model(self) -> str:
        return self._config.hunyuan_model
    
    def _get_headers(self) -> Dict[str, str]:
        # Tencent Cloud uses signature-based auth
        return {
            "Content-Type": "application/json",
            "X-TC-Action": "ChatCompletions",
            "X-TC-Version": "2023-09-01",
            "X-TC-Region": "ap-guangzhou"
        }
    
    def _sign_request(self, payload: str) -> Dict[str, str]:
        """Sign request using Tencent Cloud signature v3."""
        import datetime as dt
        
        timestamp = int(time.time())
        date = dt.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        # Simplified signature (full implementation would use TC3-HMAC-SHA256)
        headers = self._get_headers()
        headers["X-TC-Timestamp"] = str(timestamp)
        
        # In production, implement full TC3-HMAC-SHA256 signature
        # For now, use API key directly if available
        if self._config.hunyuan_secret_id and self._config.hunyuan_secret_key:
            headers["Authorization"] = f"TC3-HMAC-SHA256 Credential={self._config.hunyuan_secret_id}"
        
        return headers
    
    def _to_native_format(
        self,
        prompt: str,
        options: GenerateOptions,
        model: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert to Hunyuan format."""
        messages = []
        if system_prompt:
            messages.append({"Role": "system", "Content": system_prompt})
        messages.append({"Role": "user", "Content": prompt})
        
        return {
            "Model": model,
            "Messages": messages,
            "TopP": options.top_p,
            "Temperature": options.temperature
        }
    
    def _from_native_format(self, response: Dict[str, Any], model: str) -> LLMResponse:
        """Convert from Hunyuan format."""
        response_data = response.get("Response", response)
        choices = response_data.get("Choices", [{}])
        choice = choices[0] if choices else {}
        
        content = choice.get("Message", {}).get("Content", "")
        finish_reason = choice.get("FinishReason", "stop")
        
        usage = response_data.get("Usage", {})
        
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=usage.get("PromptTokens", 0),
                completion_tokens=usage.get("CompletionTokens", 0),
                total_tokens=usage.get("TotalTokens", 0)
            ),
            model=model,
            provider=self.method.value,
            latency_ms=0,
            finish_reason=finish_reason,
            metadata={"request_id": response_data.get("RequestId")}
        )


class ChinaLLMProvider(LLMProvider):
    """
    Unified China LLM Provider.
    
    Routes requests to the appropriate adapter based on method.
    """
    
    def __init__(self, config: ChinaLLMConfig, method: LLMMethod):
        """
        Initialize the China LLM Provider.
        
        Args:
            config: China LLM configuration
            method: Specific China LLM method
        """
        self._config = config
        self._method = method
        self._adapter = self._create_adapter(method)
    
    def _create_adapter(self, method: LLMMethod) -> BaseChinaAdapter:
        """Create the appropriate adapter."""
        adapters = {
            LLMMethod.CHINA_QWEN: QwenAdapter,
            LLMMethod.CHINA_ZHIPU: ZhipuAdapter,
            LLMMethod.CHINA_BAIDU: BaiduAdapter,
            LLMMethod.CHINA_HUNYUAN: HunyuanAdapter,
        }
        
        adapter_class = adapters.get(method)
        if not adapter_class:
            raise ValueError(f"Unsupported China LLM method: {method}")
        
        return adapter_class(self._config)
    
    @property
    def method(self) -> LLMMethod:
        return self._method
    
    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate text using the adapter."""
        return await self._adapter.generate(prompt, options, model, system_prompt)
    
    async def stream_generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream generation (not all China LLMs support streaming).
        Falls back to non-streaming for unsupported providers.
        """
        # For now, fall back to non-streaming
        response = await self.generate(prompt, options, model, system_prompt)
        yield response.content
    
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        """
        Generate embedding (limited support in China LLMs).
        """
        raise LLMError(
            error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
            message="Embedding not supported for this provider",
            provider=self.method.value,
            suggestions=["Use OpenAI or local Ollama for embeddings"]
        )
    
    async def health_check(self) -> HealthStatus:
        """Check provider health."""
        start_time = time.time()
        
        try:
            # Make a minimal request to check connectivity
            response = await self._adapter.generate(
                "Hello",
                GenerateOptions(max_tokens=10),
            )
            
            return HealthStatus(
                method=self.method,
                available=True,
                latency_ms=(time.time() - start_time) * 1000,
                model=self._adapter._get_default_model()
            )
            
        except Exception as e:
            return HealthStatus(
                method=self.method,
                available=False,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    def list_models(self) -> List[str]:
        """List available models."""
        model_lists = {
            LLMMethod.CHINA_QWEN: QwenAdapter.MODELS,
            LLMMethod.CHINA_ZHIPU: ZhipuAdapter.MODELS,
            LLMMethod.CHINA_BAIDU: BaiduAdapter.MODELS,
            LLMMethod.CHINA_HUNYUAN: HunyuanAdapter.MODELS,
        }
        return model_lists.get(self._method, [])
