"""
Local LLM Provider (Ollama) for SuperInsight platform.

Manages local Ollama container and model operations with health checks and timeout handling.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime

import httpx

try:
    from src.ai.llm_schemas import (
        LLMMethod, LocalConfig, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, TokenUsage, HealthStatus
    )
    from src.ai.llm_switcher import LLMProvider
except ImportError:
    from ai.llm_schemas import (
        LLMMethod, LocalConfig, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, TokenUsage, HealthStatus
    )
    from ai.llm_switcher import LLMProvider

logger = logging.getLogger(__name__)


class LocalLLMProvider(LLMProvider):
    """
    Local LLM Provider using Ollama.
    
    Features:
    - Ollama API integration
    - Model management (list, pull)
    - Health checks with timeout
    - Streaming support
    - Embedding generation
    """
    
    # Default models available in Ollama
    DEFAULT_MODELS = [
        "qwen:7b",
        "qwen:14b",
        "llama2:7b",
        "llama2:13b",
        "mistral:7b",
        "codellama:7b",
        "yi:6b",
    ]
    
    def __init__(self, config: LocalConfig):
        """
        Initialize the Local LLM Provider.
        
        Args:
            config: Local configuration with Ollama settings
        """
        self._config = config
        self._base_url = config.ollama_url.rstrip('/')
        self._default_model = config.default_model
        self._timeout = config.timeout
        self._max_retries = config.max_retries
        self._available_models: List[str] = []
        self._last_health_check: Optional[datetime] = None
        self._is_healthy: bool = False
    
    @property
    def method(self) -> LLMMethod:
        """Return the LLM method."""
        return LLMMethod.LOCAL_OLLAMA
    
    # ==================== Core Methods ====================
    
    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate text using Ollama.
        
        Args:
            prompt: Input prompt
            options: Generation options
            model: Model name (defaults to config default)
            system_prompt: System prompt for chat
            
        Returns:
            LLMResponse with generated content
        """
        model = model or self._default_model
        
        # Build request payload
        payload = self._build_generate_payload(prompt, options, model, system_prompt)
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                latency_ms = (time.time() - start_time) * 1000
                
                return LLMResponse(
                    content=data.get("response", ""),
                    usage=TokenUsage(
                        prompt_tokens=data.get("prompt_eval_count", 0),
                        completion_tokens=data.get("eval_count", 0),
                        total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                    ),
                    model=model,
                    provider=self.method.value,
                    latency_ms=latency_ms,
                    finish_reason=data.get("done_reason", "stop"),
                    metadata={
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                        "eval_duration": data.get("eval_duration"),
                    }
                )
                
            except httpx.TimeoutException:
                raise LLMError(
                    error_code=LLMErrorCode.TIMEOUT,
                    message=f"Request timed out after {self._timeout} seconds",
                    provider=self.method.value,
                    suggestions=["Increase timeout", "Use a smaller model", "Reduce max_tokens"]
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
        Stream text generation using Ollama.
        
        Args:
            prompt: Input prompt
            options: Generation options
            model: Model name
            system_prompt: System prompt
            
        Yields:
            Text chunks as they are generated
        """
        model = model or self._default_model
        
        payload = self._build_generate_payload(prompt, options, model, system_prompt)
        payload["stream"] = True
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/generate",
                    json=payload
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done"):
                                break
                                
            except httpx.TimeoutException:
                raise LLMError(
                    error_code=LLMErrorCode.TIMEOUT,
                    message=f"Stream timed out after {self._timeout} seconds",
                    provider=self.method.value
                )
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
        Generate text embedding using Ollama.
        
        Args:
            text: Text to embed
            model: Model name (defaults to nomic-embed-text)
            
        Returns:
            EmbeddingResponse with embedding vector
        """
        model = model or "nomic-embed-text"
        
        payload = {
            "model": model,
            "prompt": text
        }
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                embedding = data.get("embedding", [])
                latency_ms = (time.time() - start_time) * 1000
                
                return EmbeddingResponse(
                    embedding=embedding,
                    model=model,
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
            except Exception as e:
                raise LLMError(
                    error_code=LLMErrorCode.GENERATION_FAILED,
                    message=str(e),
                    provider=self.method.value
                )
    
    # ==================== Health & Model Management ====================
    
    async def health_check(self) -> HealthStatus:
        """
        Check Ollama service health.
        
        Returns:
            HealthStatus with availability info
        """
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Update available models
                data = response.json()
                self._available_models = [
                    m.get("name", "") for m in data.get("models", [])
                ]
                
                self._is_healthy = True
                self._last_health_check = datetime.utcnow()
                
                return HealthStatus(
                    method=self.method,
                    available=True,
                    latency_ms=latency_ms,
                    model=self._default_model
                )
                
        except httpx.TimeoutException:
            self._is_healthy = False
            return HealthStatus(
                method=self.method,
                available=False,
                latency_ms=(time.time() - start_time) * 1000,
                error="Connection timed out"
            )
        except httpx.ConnectError:
            self._is_healthy = False
            return HealthStatus(
                method=self.method,
                available=False,
                error=f"Cannot connect to Ollama at {self._base_url}"
            )
        except Exception as e:
            self._is_healthy = False
            return HealthStatus(
                method=self.method,
                available=False,
                error=str(e)
            )
    
    def list_models(self) -> List[str]:
        """
        List available models.
        
        Returns:
            List of model names
        """
        if self._available_models:
            return self._available_models
        return self.DEFAULT_MODELS
    
    async def pull_model(self, model_name: str) -> Dict[str, Any]:
        """
        Pull a model from Ollama registry.
        
        Args:
            model_name: Name of the model to pull
            
        Returns:
            Pull status information
        """
        payload = {"name": model_name}
        
        async with httpx.AsyncClient(timeout=3600) as client:  # Long timeout for model download
            try:
                response = await client.post(
                    f"{self._base_url}/api/pull",
                    json=payload
                )
                response.raise_for_status()
                
                return {
                    "success": True,
                    "model": model_name,
                    "message": "Model pulled successfully"
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "model": model_name,
                    "error": str(e)
                }
    
    async def delete_model(self, model_name: str) -> Dict[str, Any]:
        """
        Delete a model from Ollama.
        
        Args:
            model_name: Name of the model to delete
            
        Returns:
            Delete status information
        """
        payload = {"name": model_name}
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.delete(
                    f"{self._base_url}/api/delete",
                    json=payload
                )
                response.raise_for_status()
                
                return {
                    "success": True,
                    "model": model_name,
                    "message": "Model deleted successfully"
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "model": model_name,
                    "error": str(e)
                }
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get information about a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model information
        """
        payload = {"name": model_name}
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/api/show",
                    json=payload
                )
                response.raise_for_status()
                
                return response.json()
                
            except Exception as e:
                return {"error": str(e)}
    
    # ==================== Service Management ====================
    
    async def start_service(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Ensure Ollama service is running and model is loaded.
        
        Args:
            model_name: Model to preload
            
        Returns:
            Service status
        """
        model = model_name or self._default_model
        
        # Check if service is running
        health = await self.health_check()
        
        if not health.available:
            return {
                "success": False,
                "error": health.error,
                "suggestion": "Start Ollama service with: ollama serve"
            }
        
        # Check if model is available
        if model not in self._available_models:
            logger.info(f"Model {model} not found, pulling...")
            pull_result = await self.pull_model(model)
            if not pull_result.get("success"):
                return pull_result
        
        # Warm up the model with a simple request
        try:
            await self.generate("Hello", GenerateOptions(max_tokens=10), model)
            return {
                "success": True,
                "model": model,
                "message": "Service ready"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop_service(self) -> Dict[str, Any]:
        """
        Note: Ollama service lifecycle is managed externally.
        This method is a no-op for compatibility.
        
        Returns:
            Status message
        """
        return {
            "success": True,
            "message": "Ollama service lifecycle is managed externally"
        }
    
    # ==================== Private Methods ====================
    
    def _build_generate_payload(
        self,
        prompt: str,
        options: GenerateOptions,
        model: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build the request payload for generation."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": options.max_tokens,
                "temperature": options.temperature,
                "top_p": options.top_p,
            }
        }
        
        if options.top_k:
            payload["options"]["top_k"] = options.top_k
        
        if options.stop_sequences:
            payload["options"]["stop"] = options.stop_sequences
        
        if system_prompt:
            payload["system"] = system_prompt
        
        return payload
    
    def _handle_http_error(self, error: httpx.HTTPStatusError) -> LLMError:
        """Convert HTTP error to LLMError."""
        status_code = error.response.status_code
        
        if status_code == 404:
            return LLMError(
                error_code=LLMErrorCode.MODEL_NOT_FOUND,
                message=f"Model not found: {error.response.text}",
                provider=self.method.value,
                suggestions=["Check model name", "Pull the model first"]
            )
        elif status_code == 500:
            return LLMError(
                error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
                message=f"Ollama server error: {error.response.text}",
                provider=self.method.value
            )
        else:
            return LLMError(
                error_code=LLMErrorCode.GENERATION_FAILED,
                message=f"HTTP {status_code}: {error.response.text}",
                provider=self.method.value
            )
