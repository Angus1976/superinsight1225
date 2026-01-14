"""
LLM Switcher - Unified LLM calling interface for SuperInsight platform.

Provides a single entry point for all LLM operations with dynamic provider routing,
configuration management, and usage logging.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, AsyncIterator, Callable, Awaitable
from abc import ABC, abstractmethod
from datetime import datetime

try:
    from src.ai.llm_schemas import (
        LLMConfig, LLMMethod, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, TokenUsage, HealthStatus, MethodInfo
    )
    from src.ai.llm_config_manager import LLMConfigManager, get_config_manager
except ImportError:
    from ai.llm_schemas import (
        LLMConfig, LLMMethod, GenerateOptions, LLMResponse, EmbeddingResponse,
        LLMError, LLMErrorCode, TokenUsage, HealthStatus, MethodInfo
    )
    from ai.llm_config_manager import LLMConfigManager, get_config_manager

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @property
    @abstractmethod
    def method(self) -> LLMMethod:
        """Return the LLM method this provider handles."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate text response."""
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream text response."""
        pass
    
    @abstractmethod
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        """Generate text embedding."""
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check provider health."""
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models."""
        pass


class LLMSwitcher:
    """
    Unified LLM calling interface with dynamic provider routing.
    
    Features:
    - Unified generate/embed/stream interfaces
    - Dynamic method switching
    - Configuration hot reload
    - Usage logging
    - Health monitoring
    """
    
    def __init__(
        self,
        config_manager: Optional[LLMConfigManager] = None,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize the LLM Switcher.
        
        Args:
            config_manager: Configuration manager instance
            tenant_id: Tenant ID for multi-tenant support
        """
        self._config_manager = config_manager or get_config_manager()
        self._tenant_id = tenant_id
        self._providers: Dict[LLMMethod, LLMProvider] = {}
        self._config: Optional[LLMConfig] = None
        self._current_method: Optional[LLMMethod] = None
        self._initialized = False
        
        # Register for config changes
        self._config_manager.watch_config_changes(self._on_config_change)
    
    async def initialize(self) -> None:
        """Initialize the switcher with current configuration."""
        if self._initialized:
            return
        
        self._config = await self._config_manager.get_config(self._tenant_id)
        self._current_method = self._config.default_method
        await self._initialize_providers()
        self._initialized = True
        logger.info(f"LLM Switcher initialized with method: {self._current_method}")
    
    async def _initialize_providers(self) -> None:
        """Initialize all enabled providers."""
        if not self._config:
            return
        
        for method in self._config.enabled_methods:
            try:
                provider = await self._create_provider(method)
                if provider:
                    self._providers[method] = provider
                    logger.debug(f"Initialized provider: {method}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {method}: {e}")
    
    async def _create_provider(self, method: LLMMethod) -> Optional[LLMProvider]:
        """Create a provider instance for the given method."""
        # Import providers lazily to avoid circular imports
        try:
            if method == LLMMethod.LOCAL_OLLAMA:
                from src.ai.llm_docker import LocalLLMProvider
                return LocalLLMProvider(self._config.local_config)
            
            elif method in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
                from src.ai.llm_cloud import CloudLLMProvider
                return CloudLLMProvider(self._config.cloud_config, method)
            
            elif method in (LLMMethod.CHINA_QWEN, LLMMethod.CHINA_ZHIPU,
                           LLMMethod.CHINA_BAIDU, LLMMethod.CHINA_HUNYUAN):
                from src.ai.china_llm_adapter import ChinaLLMProvider
                return ChinaLLMProvider(self._config.china_config, method)
            
        except ImportError as e:
            logger.warning(f"Provider module not available for {method}: {e}")
        except Exception as e:
            logger.error(f"Error creating provider {method}: {e}")
        
        return None
    
    async def _on_config_change(self, new_config: LLMConfig) -> None:
        """Handle configuration changes."""
        logger.info("Configuration change detected, reloading providers")
        self._config = new_config
        
        # Reinitialize providers if enabled methods changed
        await self._initialize_providers()
        
        # Update current method if it's no longer enabled
        if self._current_method not in new_config.enabled_methods:
            self._current_method = new_config.default_method
            logger.info(f"Switched to default method: {self._current_method}")
    
    # ==================== Core Methods ====================
    
    async def generate(
        self,
        prompt: str,
        options: Optional[GenerateOptions] = None,
        method: Optional[LLMMethod] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate text response using the specified or default method.
        
        Args:
            prompt: Input prompt
            options: Generation options
            method: Override default method
            model: Override default model
            system_prompt: System prompt for chat models
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            LLMError: If generation fails
        """
        await self._ensure_initialized()
        
        options = options or GenerateOptions()
        target_method = method or self._current_method
        
        provider = self._get_provider(target_method)
        
        start_time = time.time()
        try:
            response = await provider.generate(prompt, options, model, system_prompt)
            latency_ms = (time.time() - start_time) * 1000
            response.latency_ms = latency_ms
            
            # Log usage
            await self._log_usage(
                method=target_method.value,
                model=response.model,
                operation="generate",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                latency_ms=latency_ms,
                success=True
            )
            
            return response
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error = self._create_error(e, target_method)
            
            # Log failure
            await self._log_usage(
                method=target_method.value,
                model=model or "unknown",
                operation="generate",
                latency_ms=latency_ms,
                success=False,
                error_code=error.error_code.value,
                error_message=str(e)
            )
            
            raise error
    
    async def stream_generate(
        self,
        prompt: str,
        options: Optional[GenerateOptions] = None,
        method: Optional[LLMMethod] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream text response using the specified or default method.
        
        Args:
            prompt: Input prompt
            options: Generation options
            method: Override default method
            model: Override default model
            system_prompt: System prompt for chat models
            
        Yields:
            Text chunks as they are generated
        """
        await self._ensure_initialized()
        
        options = options or GenerateOptions()
        options.stream = True
        target_method = method or self._current_method
        
        provider = self._get_provider(target_method)
        
        start_time = time.time()
        total_tokens = 0
        
        try:
            async for chunk in provider.stream_generate(prompt, options, model, system_prompt):
                total_tokens += 1  # Approximate token count
                yield chunk
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Log usage
            await self._log_usage(
                method=target_method.value,
                model=model or "unknown",
                operation="stream",
                completion_tokens=total_tokens,
                latency_ms=latency_ms,
                success=True
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error = self._create_error(e, target_method)
            
            await self._log_usage(
                method=target_method.value,
                model=model or "unknown",
                operation="stream",
                latency_ms=latency_ms,
                success=False,
                error_code=error.error_code.value,
                error_message=str(e)
            )
            
            raise error
    
    async def embed(
        self,
        text: str,
        method: Optional[LLMMethod] = None,
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        """
        Generate text embedding using the specified or default method.
        
        Args:
            text: Text to embed
            method: Override default method
            model: Override default model
            
        Returns:
            EmbeddingResponse with embedding vector
        """
        await self._ensure_initialized()
        
        target_method = method or self._current_method
        provider = self._get_provider(target_method)
        
        start_time = time.time()
        try:
            response = await provider.embed(text, model)
            latency_ms = (time.time() - start_time) * 1000
            response.latency_ms = latency_ms
            
            await self._log_usage(
                method=target_method.value,
                model=response.model,
                operation="embed",
                latency_ms=latency_ms,
                success=True
            )
            
            return response
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error = self._create_error(e, target_method)
            
            await self._log_usage(
                method=target_method.value,
                model=model or "unknown",
                operation="embed",
                latency_ms=latency_ms,
                success=False,
                error_code=error.error_code.value,
                error_message=str(e)
            )
            
            raise error
    
    # ==================== Method Management ====================
    
    def switch_method(self, method: LLMMethod) -> None:
        """
        Switch the default LLM method.
        
        Args:
            method: New default method
            
        Raises:
            ValueError: If method is not enabled
        """
        if self._config and method not in self._config.enabled_methods:
            raise ValueError(f"Method {method} is not enabled")
        
        if method not in self._providers:
            raise ValueError(f"Provider for {method} is not initialized")
        
        old_method = self._current_method
        self._current_method = method
        logger.info(f"Switched LLM method from {old_method} to {method}")
    
    def get_current_method(self) -> LLMMethod:
        """Get the current default method."""
        return self._current_method
    
    def list_available_methods(self) -> List[MethodInfo]:
        """
        List all available LLM methods with their status.
        
        Returns:
            List of MethodInfo objects
        """
        methods = []
        
        for method in LLMMethod:
            info = MethodInfo(
                method=method,
                name=self._get_method_name(method),
                description=self._get_method_description(method),
                enabled=self._config and method in self._config.enabled_methods,
                configured=method in self._providers,
                models=self._get_method_models(method)
            )
            methods.append(info)
        
        return methods
    
    # ==================== Health Checks ====================
    
    async def health_check(self, method: Optional[LLMMethod] = None) -> Dict[LLMMethod, HealthStatus]:
        """
        Check health of LLM providers.
        
        Args:
            method: Specific method to check, or None for all
            
        Returns:
            Dictionary mapping methods to health status
        """
        await self._ensure_initialized()
        
        results = {}
        
        methods_to_check = [method] if method else list(self._providers.keys())
        
        for m in methods_to_check:
            if m in self._providers:
                try:
                    status = await self._providers[m].health_check()
                    results[m] = status
                except Exception as e:
                    results[m] = HealthStatus(
                        method=m,
                        available=False,
                        error=str(e)
                    )
            else:
                results[m] = HealthStatus(
                    method=m,
                    available=False,
                    error="Provider not initialized"
                )
        
        return results
    
    async def test_connection(self, method: LLMMethod) -> HealthStatus:
        """
        Test connection to a specific LLM provider.
        
        Args:
            method: Method to test
            
        Returns:
            HealthStatus with connection result
        """
        await self._ensure_initialized()
        
        if method not in self._providers:
            return HealthStatus(
                method=method,
                available=False,
                error="Provider not configured"
            )
        
        start_time = time.time()
        try:
            status = await self._providers[method].health_check()
            status.latency_ms = (time.time() - start_time) * 1000
            return status
        except Exception as e:
            return HealthStatus(
                method=method,
                available=False,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    # ==================== Private Methods ====================
    
    async def _ensure_initialized(self) -> None:
        """Ensure the switcher is initialized."""
        if not self._initialized:
            await self.initialize()
    
    def _get_provider(self, method: LLMMethod) -> LLMProvider:
        """Get provider for the specified method."""
        if method not in self._providers:
            raise LLMError(
                error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
                message=f"Provider for {method} is not available",
                provider=method.value,
                suggestions=["Check if the method is enabled", "Verify provider configuration"]
            )
        return self._providers[method]
    
    def _create_error(self, exception: Exception, method: LLMMethod) -> LLMError:
        """Create an LLMError from an exception."""
        error_code = LLMErrorCode.GENERATION_FAILED
        message = str(exception)
        retry_after = None
        suggestions = []
        
        # Classify error
        error_str = str(exception).lower()
        
        if "timeout" in error_str:
            error_code = LLMErrorCode.TIMEOUT
            suggestions = ["Increase timeout setting", "Try a smaller prompt"]
        elif "rate" in error_str or "429" in error_str:
            error_code = LLMErrorCode.RATE_LIMITED
            retry_after = 60
            suggestions = ["Wait before retrying", "Reduce request frequency"]
        elif "api key" in error_str or "unauthorized" in error_str or "401" in error_str:
            error_code = LLMErrorCode.INVALID_API_KEY
            suggestions = ["Check API key configuration", "Verify API key is valid"]
        elif "model" in error_str and "not found" in error_str:
            error_code = LLMErrorCode.MODEL_NOT_FOUND
            suggestions = ["Check model name", "List available models"]
        elif "network" in error_str or "connection" in error_str:
            error_code = LLMErrorCode.NETWORK_ERROR
            suggestions = ["Check network connectivity", "Verify service URL"]
        
        return LLMError(
            error_code=error_code,
            message=message,
            provider=method.value,
            retry_after=retry_after,
            suggestions=suggestions
        )
    
    async def _log_usage(
        self,
        method: str,
        model: str,
        operation: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Log LLM usage."""
        try:
            await self._config_manager.log_usage(
                method=method,
                model=model,
                operation=operation,
                tenant_id=self._tenant_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                success=success,
                error_code=error_code,
                error_message=error_message,
            )
        except Exception as e:
            logger.warning(f"Failed to log usage: {e}")
    
    def _get_method_name(self, method: LLMMethod) -> str:
        """Get human-readable name for method."""
        names = {
            LLMMethod.LOCAL_OLLAMA: "Local Ollama",
            LLMMethod.CLOUD_OPENAI: "OpenAI",
            LLMMethod.CLOUD_AZURE: "Azure OpenAI",
            LLMMethod.CHINA_QWEN: "通义千问 (Qwen)",
            LLMMethod.CHINA_ZHIPU: "智谱 GLM",
            LLMMethod.CHINA_BAIDU: "文心一言",
            LLMMethod.CHINA_HUNYUAN: "腾讯混元",
        }
        return names.get(method, method.value)
    
    def _get_method_description(self, method: LLMMethod) -> str:
        """Get description for method."""
        descriptions = {
            LLMMethod.LOCAL_OLLAMA: "本地部署的 Ollama 服务，支持多种开源模型",
            LLMMethod.CLOUD_OPENAI: "OpenAI API，支持 GPT-3.5/4 系列模型",
            LLMMethod.CLOUD_AZURE: "Azure OpenAI 服务，企业级部署",
            LLMMethod.CHINA_QWEN: "阿里云通义千问，中文优化",
            LLMMethod.CHINA_ZHIPU: "智谱 AI GLM 系列，中文理解能力强",
            LLMMethod.CHINA_BAIDU: "百度文心一言，多模态能力",
            LLMMethod.CHINA_HUNYUAN: "腾讯混元大模型，企业级服务",
        }
        return descriptions.get(method, "")
    
    def _get_method_models(self, method: LLMMethod) -> List[str]:
        """Get available models for method."""
        if method in self._providers:
            return self._providers[method].list_models()
        return []


# ==================== Singleton Instance ====================

_switcher_instances: Dict[str, LLMSwitcher] = {}


def get_llm_switcher(tenant_id: Optional[str] = None) -> LLMSwitcher:
    """
    Get or create an LLM Switcher instance for the tenant.
    
    Args:
        tenant_id: Tenant ID for multi-tenant support
        
    Returns:
        LLMSwitcher instance
    """
    key = tenant_id or "global"
    
    if key not in _switcher_instances:
        _switcher_instances[key] = LLMSwitcher(tenant_id=tenant_id)
    
    return _switcher_instances[key]


async def get_initialized_switcher(tenant_id: Optional[str] = None) -> LLMSwitcher:
    """
    Get an initialized LLM Switcher instance.
    
    Args:
        tenant_id: Tenant ID for multi-tenant support
        
    Returns:
        Initialized LLMSwitcher instance
    """
    switcher = get_llm_switcher(tenant_id)
    await switcher.initialize()
    return switcher
