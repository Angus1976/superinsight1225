"""
Cloud LLM Provider for SuperInsight platform.

Supports OpenAI and Azure OpenAI services with streaming, timeout handling, and error parsing.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime

import httpx

try:
    from src.ai.llm_schemas import (
        LLMMethod, CloudConfig, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, TokenUsage, HealthStatus
    )
    from src.ai.llm_switcher import LLMProvider
except ImportError:
    from ai.llm_schemas import (
        LLMMethod, CloudConfig, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, TokenUsage, HealthStatus
    )
    from ai.llm_switcher import LLMProvider

logger = logging.getLogger(__name__)


class CloudLLMProvider(LLMProvider):
    """
    Cloud LLM Provider for OpenAI and Azure OpenAI.
    
    Features:
    - OpenAI API integration
    - Azure OpenAI support
    - Streaming responses
    - API key validation
    - Error code parsing
    """
    
    # Available models
    OPENAI_MODELS = [
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "text-embedding-ada-002",
        "text-embedding-3-small",
        "text-embedding-3-large",
    ]
    
    def __init__(self, config: CloudConfig, method: LLMMethod):
        """
        Initialize the Cloud LLM Provider.
        
        Args:
            config: Cloud configuration
            method: LLM method (CLOUD_OPENAI or CLOUD_AZURE)
        """
        self._config = config
        self._method = method
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        
        # Set up endpoints based on method
        if method == LLMMethod.CLOUD_AZURE:
            self._base_url = config.azure_endpoint
            self._api_key = config.azure_api_key
            self._default_model = config.azure_deployment
            self._api_version = config.azure_api_version
        else:
            self._base_url = config.openai_base_url.rstrip('/')
            self._api_key = config.openai_api_key
            self._default_model = config.openai_model
            self._api_version = None
    
    @property
    def method(self) -> LLMMethod:
        """Return the LLM method."""
        return self._method
    
    # ==================== Core Methods ====================
    
    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate text using OpenAI/Azure API.
        
        Args:
            prompt: Input prompt
            options: Generation options
            model: Model name
            system_prompt: System prompt
            
        Returns:
            LLMResponse with generated content
        """
        model = model or self._default_model
        
        messages = self._build_messages(prompt, system_prompt)
        payload = self._build_chat_payload(messages, options, model)
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    self._get_chat_endpoint(),
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                latency_ms = (time.time() - start_time) * 1000
                
                # Extract response content
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                finish_reason = choice.get("finish_reason", "stop")
                
                # Extract usage
                usage_data = data.get("usage", {})
                
                return LLMResponse(
                    content=content,
                    usage=TokenUsage(
                        prompt_tokens=usage_data.get("prompt_tokens", 0),
                        completion_tokens=usage_data.get("completion_tokens", 0),
                        total_tokens=usage_data.get("total_tokens", 0)
                    ),
                    model=data.get("model", model),
                    provider=self.method.value,
                    latency_ms=latency_ms,
                    finish_reason=finish_reason,
                    metadata={
                        "id": data.get("id"),
                        "created": data.get("created"),
                        "system_fingerprint": data.get("system_fingerprint"),
                    }
                )
                
            except httpx.TimeoutException:
                raise LLMError(
                    error_code=LLMErrorCode.TIMEOUT,
                    message=f"Request timed out after {self._timeout} seconds",
                    provider=self.method.value,
                    suggestions=["Increase timeout", "Reduce max_tokens"]
                )
            except httpx.HTTPStatusError as e:
                raise self._handle_http_error(e)
            except Exception as e:
                raise LLMError(
                    error_code=LLMErrorCode.GENERATION_FAILED,
                    message=str(e),
                    provider=self.method.value
                )
    
    async def stream_generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream text generation using OpenAI/Azure API.
        
        Args:
            prompt: Input prompt
            options: Generation options
            model: Model name
            system_prompt: System prompt
            
        Yields:
            Text chunks as they are generated
        """
        model = model or self._default_model
        
        messages = self._build_messages(prompt, system_prompt)
        payload = self._build_chat_payload(messages, options, model)
        payload["stream"] = True
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    self._get_chat_endpoint(),
                    headers=self._get_headers(),
                    json=payload
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            
                            import json
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                                
            except httpx.TimeoutException:
                raise LLMError(
                    error_code=LLMErrorCode.TIMEOUT,
                    message=f"Stream timed out after {self._timeout} seconds",
                    provider=self.method.value
                )
            except httpx.HTTPStatusError as e:
                raise self._handle_http_error(e)
            except Exception as e:
                raise LLMError(
                    error_code=LLMErrorCode.GENERATION_FAILED,
                    message=str(e),
                    provider=self.method.value
                )
    
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        """
        Generate text embedding using OpenAI/Azure API.
        
        Args:
            text: Text to embed
            model: Embedding model name
            
        Returns:
            EmbeddingResponse with embedding vector
        """
        model = model or "text-embedding-ada-002"
        
        payload = {
            "input": text,
            "model": model
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    self._get_embedding_endpoint(),
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                latency_ms = (time.time() - start_time) * 1000
                
                embedding = data.get("data", [{}])[0].get("embedding", [])
                
                return EmbeddingResponse(
                    embedding=embedding,
                    model=data.get("model", model),
                    provider=self.method.value,
                    dimensions=len(embedding),
                    latency_ms=latency_ms
                )
                
            except httpx.TimeoutException:
                raise LLMError(
                    error_code=LLMErrorCode.TIMEOUT,
                    message=f"Embedding request timed out after {self._timeout} seconds",
                    provider=self.method.value
                )
            except httpx.HTTPStatusError as e:
                raise self._handle_http_error(e)
            except Exception as e:
                raise LLMError(
                    error_code=LLMErrorCode.GENERATION_FAILED,
                    message=str(e),
                    provider=self.method.value
                )
    
    # ==================== Health & Validation ====================
    
    async def health_check(self) -> HealthStatus:
        """
        Check OpenAI/Azure service health.
        
        Returns:
            HealthStatus with availability info
        """
        start_time = time.time()
        
        # Validate API key first
        if not self._api_key:
            return HealthStatus(
                method=self.method,
                available=False,
                error="API key not configured"
            )
        
        try:
            # Make a minimal API call to check connectivity
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._base_url}/models" if self._method == LLMMethod.CLOUD_OPENAI else f"{self._base_url}/openai/models",
                    headers=self._get_headers(),
                    params={"api-version": self._api_version} if self._api_version else None
                )
                response.raise_for_status()
                
                latency_ms = (time.time() - start_time) * 1000
                
                return HealthStatus(
                    method=self.method,
                    available=True,
                    latency_ms=latency_ms,
                    model=self._default_model
                )
                
        except httpx.HTTPStatusError as e:
            error_msg = self._parse_error_message(e)
            return HealthStatus(
                method=self.method,
                available=False,
                latency_ms=(time.time() - start_time) * 1000,
                error=error_msg
            )
        except Exception as e:
            return HealthStatus(
                method=self.method,
                available=False,
                error=str(e)
            )
    
    async def validate_api_key(self, api_key: str) -> bool:
        """
        Validate an API key.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {"Authorization": f"Bearer {api_key}"}
                
                if self._method == LLMMethod.CLOUD_AZURE:
                    headers = {"api-key": api_key}
                
                response = await client.get(
                    f"{self._base_url}/models" if self._method == LLMMethod.CLOUD_OPENAI else f"{self._base_url}/openai/models",
                    headers=headers,
                    params={"api-version": self._api_version} if self._api_version else None
                )
                
                return response.status_code == 200
                
        except Exception:
            return False
    
    def list_models(self) -> List[str]:
        """
        List available models.
        
        Returns:
            List of model names
        """
        return self.OPENAI_MODELS
    
    # ==================== Private Methods ====================
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        if self._method == LLMMethod.CLOUD_AZURE:
            return {
                "api-key": self._api_key,
                "Content-Type": "application/json"
            }
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
    
    def _get_chat_endpoint(self) -> str:
        """Get chat completions endpoint."""
        if self._method == LLMMethod.CLOUD_AZURE:
            return f"{self._base_url}/openai/deployments/{self._default_model}/chat/completions?api-version={self._api_version}"
        return f"{self._base_url}/chat/completions"
    
    def _get_embedding_endpoint(self) -> str:
        """Get embeddings endpoint."""
        if self._method == LLMMethod.CLOUD_AZURE:
            return f"{self._base_url}/openai/deployments/text-embedding-ada-002/embeddings?api-version={self._api_version}"
        return f"{self._base_url}/embeddings"
    
    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build messages array for chat API."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return messages
    
    def _build_chat_payload(
        self,
        messages: List[Dict[str, str]],
        options: GenerateOptions,
        model: str
    ) -> Dict[str, Any]:
        """Build chat completions payload."""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
            "top_p": options.top_p,
            "stream": options.stream,
        }
        
        if options.stop_sequences:
            payload["stop"] = options.stop_sequences
        
        if options.presence_penalty != 0:
            payload["presence_penalty"] = options.presence_penalty
        
        if options.frequency_penalty != 0:
            payload["frequency_penalty"] = options.frequency_penalty
        
        return payload
    
    def _handle_http_error(self, error: httpx.HTTPStatusError) -> LLMError:
        """Convert HTTP error to LLMError with user-friendly message."""
        status_code = error.response.status_code
        error_msg = self._parse_error_message(error)
        
        if status_code == 401:
            return LLMError(
                error_code=LLMErrorCode.INVALID_API_KEY,
                message=f"Invalid API key: {error_msg}",
                provider=self.method.value,
                suggestions=["Check your API key", "Verify API key permissions"]
            )
        elif status_code == 429:
            retry_after = error.response.headers.get("Retry-After", 60)
            return LLMError(
                error_code=LLMErrorCode.RATE_LIMITED,
                message=f"Rate limited: {error_msg}",
                provider=self.method.value,
                retry_after=int(retry_after) if isinstance(retry_after, str) and retry_after.isdigit() else 60,
                suggestions=["Wait before retrying", "Reduce request frequency"]
            )
        elif status_code == 404:
            return LLMError(
                error_code=LLMErrorCode.MODEL_NOT_FOUND,
                message=f"Model not found: {error_msg}",
                provider=self.method.value,
                suggestions=["Check model name", "Verify model availability"]
            )
        elif status_code == 500:
            return LLMError(
                error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
                message=f"Service error: {error_msg}",
                provider=self.method.value,
                suggestions=["Retry later", "Check service status"]
            )
        else:
            return LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message=f"HTTP {status_code}: {error_msg}",
                provider=self.method.value
            )
    
    def _parse_error_message(self, error: httpx.HTTPStatusError) -> str:
        """Parse error message from response."""
        try:
            data = error.response.json()
            if "error" in data:
                return data["error"].get("message", str(data["error"]))
            return str(data)
        except Exception:
            return error.response.text or str(error)
