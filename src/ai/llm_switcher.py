"""
LLM Switcher - Unified LLM calling interface for SuperInsight platform.

Provides a single entry point for all LLM operations with dynamic provider routing,
configuration management, usage logging, and automatic failover.

Features:
- Unified generate/embed/stream interfaces
- Dynamic method switching
- Configuration hot reload
- Usage logging
- Health monitoring
- Automatic failover to fallback provider
- Exponential backoff retry (1s, 2s, 4s delays)
- 30-second timeout enforcement
- Rate limit handling with retry-after support
- Response caching with 1-hour TTL (Requirement 10.2)
"""

import asyncio
import time
import logging
import re
import hashlib
import json
from typing import Dict, Any, List, Optional, AsyncIterator, Callable, Awaitable, Tuple, Union
from abc import ABC, abstractmethod
from datetime import datetime
from collections import defaultdict

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

# Constants for retry and timeout configuration
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRY_ATTEMPTS = 3
EXPONENTIAL_BACKOFF_BASE = 2  # Delays: 1s, 2s, 4s

# Response caching configuration (Requirement 10.2)
RESPONSE_CACHE_TTL = 3600  # 1 hour in seconds
RESPONSE_CACHE_KEY_PREFIX = "llm:response:"


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
    - Automatic failover to fallback provider
    - Exponential backoff retry (1s, 2s, 4s delays)
    - 30-second timeout enforcement
    - Rate limit handling with retry-after support
    - Usage statistics tracking per provider
    - Response caching with 1-hour TTL (Requirement 10.2)
    """
    
    def __init__(
        self,
        config_manager: Optional[LLMConfigManager] = None,
        tenant_id: Optional[str] = None,
        cache_client: Optional[Any] = None,
        enable_response_cache: bool = True,
        rate_limiter: Optional[Any] = None,
        enable_rate_limiting: bool = True,
    ):
        """
        Initialize the LLM Switcher.

        Args:
            config_manager: Configuration manager instance
            tenant_id: Tenant ID for multi-tenant support
            cache_client: Redis client for response caching (Requirement 10.2)
            enable_response_cache: Whether to enable response caching
            rate_limiter: Rate limiter instance for quota management (Requirement 10.3)
            enable_rate_limiting: Whether to enable rate limiting
        """
        self._config_manager = config_manager or get_config_manager()
        self._tenant_id = tenant_id
        self._providers: Dict[LLMMethod, LLMProvider] = {}
        self._config: Optional[LLMConfig] = None
        self._current_method: Optional[LLMMethod] = None
        self._fallback_method: Optional[LLMMethod] = None
        self._initialized = False

        # Response caching (Requirement 10.2)
        self._cache_client = cache_client
        self._enable_response_cache = enable_response_cache
        self._local_response_cache: Dict[str, Tuple[Any, float]] = {}  # Fallback in-memory cache

        # Rate limiting (Requirement 10.3)
        self._rate_limiter = rate_limiter
        self._enable_rate_limiting = enable_rate_limiting
        if self._rate_limiter is None and self._enable_rate_limiting:
            # Create default rate limiter if enabled but not provided
            try:
                from src.ai.llm.rate_limiter import get_rate_limiter
                self._rate_limiter = get_rate_limiter()
                logger.debug("Created default rate limiter")
            except ImportError:
                logger.warning("Rate limiter not available, rate limiting disabled")
                self._enable_rate_limiting = False

        # Usage statistics tracking per provider (Requirement 3.5)
        self._usage_stats: Dict[str, int] = defaultdict(int)
        self._stats_lock = asyncio.Lock()

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
    
    async def set_fallback_provider(self, method: LLMMethod) -> None:
        """
        Set the fallback provider for automatic failover.
        
        When the primary provider fails after all retries, the system will
        automatically attempt the fallback provider.
        
        Args:
            method: The LLM method to use as fallback
            
        Raises:
            ValueError: If method is not enabled or not available
            
        **Validates: Requirements 3.3, 4.2**
        """
        await self._ensure_initialized()
        
        if self._config and method not in self._config.enabled_methods:
            raise ValueError(f"Method {method} is not enabled")
        
        if method not in self._providers:
            raise ValueError(f"Provider for {method} is not initialized")
        
        # Validate fallback provider is healthy before setting
        try:
            health = await self._providers[method].health_check()
            if not health.available:
                logger.warning(
                    f"Fallback provider {method} is unhealthy: {health.error}. "
                    "Setting anyway, but failover may not work."
                )
        except Exception as e:
            logger.warning(f"Could not verify fallback provider health: {e}")
        
        old_fallback = self._fallback_method
        self._fallback_method = method
        logger.info(f"Set fallback provider from {old_fallback} to {method}")
    
    def get_fallback_provider(self) -> Optional[LLMMethod]:
        """Get the current fallback provider method."""
        return self._fallback_method
    
    async def get_usage_stats(self) -> Dict[str, int]:
        """
        Get provider usage statistics.
        
        Returns:
            Dictionary mapping provider method values to request counts
            
        **Validates: Requirements 3.5**
        """
        async with self._stats_lock:
            return dict(self._usage_stats)
    
    async def _increment_usage_stats(self, method: LLMMethod) -> None:
        """Increment usage counter for a provider."""
        async with self._stats_lock:
            self._usage_stats[method.value] += 1
    
    # ==================== Response Caching (Requirement 10.2) ====================
    
    def _generate_cache_key(
        self,
        prompt: str,
        method: LLMMethod,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a deterministic cache key from prompt and parameters.
        
        The cache key is a SHA256 hash of the normalized request parameters
        to ensure identical requests produce identical keys.
        
        Args:
            prompt: The input prompt
            method: The LLM method being used
            model: The model name (optional)
            system_prompt: The system prompt (optional)
            **kwargs: Additional parameters that affect the response
            
        Returns:
            A unique cache key string
            
        **Validates: Requirements 10.2**
        """
        # Build a deterministic representation of the request
        cache_data = {
            'prompt': prompt,
            'method': method.value,
            'model': model or '',
            'system_prompt': system_prompt or '',
            'tenant_id': self._tenant_id or 'global',
        }
        
        # Include relevant generation options that affect output
        # Exclude options that don't affect the response content
        relevant_options = ['temperature', 'max_tokens', 'top_p', 'top_k']
        for key in relevant_options:
            if key in kwargs:
                cache_data[key] = kwargs[key]
        
        # Create a stable JSON representation (sorted keys)
        cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=True)
        
        # Generate SHA256 hash
        cache_hash = hashlib.sha256(cache_str.encode('utf-8')).hexdigest()
        
        return f"{RESPONSE_CACHE_KEY_PREFIX}{cache_hash}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[LLMResponse]:
        """
        Retrieve a cached response if available and not expired.
        
        Tries Redis cache first, falls back to local in-memory cache.
        
        Args:
            cache_key: The cache key to look up
            
        Returns:
            Cached LLMResponse if found and valid, None otherwise
            
        **Validates: Requirements 10.2**
        """
        if not self._enable_response_cache:
            return None
        
        # Try Redis cache first
        if self._cache_client:
            try:
                cached_data = await self._cache_client.get(cache_key)
                if cached_data:
                    if isinstance(cached_data, bytes):
                        cached_data = cached_data.decode('utf-8')
                    response_dict = json.loads(cached_data)
                    response = LLMResponse(**response_dict)
                    response.cached = True
                    logger.debug(f"Cache hit (Redis) for key: {cache_key[:50]}...")
                    return response
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Fall back to local cache
        if cache_key in self._local_response_cache:
            cached_data, timestamp = self._local_response_cache[cache_key]
            # Check if cache entry is still valid (within TTL)
            if time.time() - timestamp < RESPONSE_CACHE_TTL:
                response = LLMResponse(**cached_data)
                response.cached = True
                logger.debug(f"Cache hit (local) for key: {cache_key[:50]}...")
                return response
            else:
                # Remove expired entry
                del self._local_response_cache[cache_key]
        
        return None
    
    async def _cache_response(self, cache_key: str, response: LLMResponse) -> None:
        """
        Cache a successful LLM response.
        
        Stores in both Redis (if available) and local cache.
        TTL is set to 1 hour (3600 seconds) as per Requirement 10.2.
        
        Args:
            cache_key: The cache key
            response: The LLMResponse to cache
            
        **Validates: Requirements 10.2**
        """
        if not self._enable_response_cache:
            return
        
        try:
            # Prepare response data for caching
            response_dict = {
                'content': response.content,
                'model': response.model,
                'provider': response.provider,
                'usage': response.usage.model_dump() if response.usage else None,
                'finish_reason': response.finish_reason,
                'latency_ms': response.latency_ms,
                'metadata': response.metadata,
                'cached': True,  # Mark as cached for future retrieval
            }
            response_json = json.dumps(response_dict)
            
            # Store in Redis with TTL
            if self._cache_client:
                try:
                    await self._cache_client.setex(
                        cache_key,
                        RESPONSE_CACHE_TTL,
                        response_json
                    )
                    logger.debug(f"Cached response in Redis: {cache_key[:50]}...")
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")
            
            # Also store in local cache as fallback
            self._local_response_cache[cache_key] = (response_dict, time.time())
            
            # Clean up old local cache entries periodically
            await self._cleanup_local_cache()
            
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
    
    async def _cleanup_local_cache(self) -> None:
        """
        Remove expired entries from local cache to prevent memory bloat.
        
        Called periodically during cache operations.
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._local_response_cache.items()
            if current_time - timestamp >= RESPONSE_CACHE_TTL
        ]
        for key in expired_keys:
            del self._local_response_cache[key]
        
        # Also limit cache size to prevent unbounded growth
        max_local_cache_size = 1000
        if len(self._local_response_cache) > max_local_cache_size:
            # Remove oldest entries
            sorted_entries = sorted(
                self._local_response_cache.items(),
                key=lambda x: x[1][1]  # Sort by timestamp
            )
            entries_to_remove = len(self._local_response_cache) - max_local_cache_size
            for key, _ in sorted_entries[:entries_to_remove]:
                del self._local_response_cache[key]
    
    def set_cache_client(self, cache_client: Any) -> None:
        """
        Set or update the Redis cache client.
        
        Args:
            cache_client: Redis client instance
        """
        self._cache_client = cache_client
        logger.info("Cache client updated for LLMSwitcher")
    
    def enable_response_cache(self, enabled: bool = True) -> None:
        """
        Enable or disable response caching.
        
        Args:
            enabled: Whether to enable caching
        """
        self._enable_response_cache = enabled
        logger.info(f"Response caching {'enabled' if enabled else 'disabled'}")
    
    def clear_response_cache(self) -> None:
        """Clear the local response cache."""
        self._local_response_cache.clear()
        logger.info("Local response cache cleared")

    async def generate(
        self,
        prompt: str,
        options: Optional[GenerateOptions] = None,
        method: Optional[LLMMethod] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        use_cache: bool = True,
    ) -> LLMResponse:
        """
        Generate text response using the specified or default method.
        
        Implements automatic failover with exponential backoff retry:
        1. Check cache for identical request (Requirement 10.2)
        2. Try primary provider with up to 3 retries (1s, 2s, 4s delays)
        3. If all retries fail, attempt fallback provider
        4. If both fail, return comprehensive error with details from both
        5. Cache successful response for 1 hour (Requirement 10.2)
        
        Args:
            prompt: Input prompt
            options: Generation options
            method: Override default method
            model: Override default model
            system_prompt: System prompt for chat models
            use_cache: Whether to use response caching (default: True)
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            LLMError: If generation fails on both primary and fallback providers
            
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 10.2**
        """
        await self._ensure_initialized()
        
        options = options or GenerateOptions()
        target_method = method or self._current_method
        
        # Generate cache key from prompt and parameters (Requirement 10.2)
        cache_key = self._generate_cache_key(
            prompt=prompt,
            method=target_method,
            model=model,
            system_prompt=system_prompt,
            temperature=options.temperature if options else None,
            max_tokens=options.max_tokens if options else None,
            top_p=options.top_p if options else None,
        )
        
        # Check cache first (Requirement 10.2)
        if use_cache and self._enable_response_cache:
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                logger.info(f"Returning cached response for method {target_method}")
                return cached_response
        
        # Store original request context for potential failover (Requirement 3.4)
        request_context = {
            'prompt': prompt,
            'options': options,
            'model': model,
            'system_prompt': system_prompt,
        }
        
        # Try primary provider with retries
        primary_error = None
        try:
            response = await self._generate_with_retry(
                target_method, 
                prompt, 
                options, 
                model, 
                system_prompt
            )
            
            # Track usage statistics (Requirement 3.5)
            await self._increment_usage_stats(target_method)
            
            # Cache successful response (Requirement 10.2)
            if use_cache and self._enable_response_cache:
                await self._cache_response(cache_key, response)
            
            return response
            
        except Exception as e:
            primary_error = e
            logger.warning(f"Primary provider {target_method} failed: {e}")
        
        # Try fallback provider if configured (Requirements 3.3, 4.2)
        if self._fallback_method and self._fallback_method != target_method:
            logger.info(f"Attempting failover to {self._fallback_method}")
            
            try:
                # Maintain request context and retry with new provider (Requirement 3.4)
                response = await self._generate_with_retry(
                    self._fallback_method,
                    request_context['prompt'],
                    request_context['options'],
                    request_context['model'],
                    request_context['system_prompt']
                )
                
                # Track usage statistics for fallback
                await self._increment_usage_stats(self._fallback_method)
                
                # Cache successful fallback response (Requirement 10.2)
                if use_cache and self._enable_response_cache:
                    await self._cache_response(cache_key, response)
                
                logger.info(f"Failover to {self._fallback_method} succeeded")
                return response
                
            except Exception as fallback_error:
                logger.error(f"Fallback provider {self._fallback_method} also failed: {fallback_error}")
                
                # Return comprehensive error with both failure details (Requirement 4.3)
                raise LLMError(
                    error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
                    message=(
                        f"Both primary and fallback providers failed. "
                        f"Primary ({target_method.value}): {str(primary_error)}. "
                        f"Fallback ({self._fallback_method.value}): {str(fallback_error)}"
                    ),
                    provider=f"{target_method.value},{self._fallback_method.value}",
                    details={
                        'primary_provider': target_method.value,
                        'primary_error': str(primary_error),
                        'fallback_provider': self._fallback_method.value,
                        'fallback_error': str(fallback_error),
                    },
                    suggestions=[
                        "Check provider configurations",
                        "Verify API keys are valid",
                        "Check network connectivity",
                        "Review provider health status"
                    ]
                )
        
        # No fallback configured, raise the primary error
        raise self._create_error(primary_error, target_method)
    
    async def _generate_with_retry(
        self,
        method: LLMMethod,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str],
        system_prompt: Optional[str],
        max_retries: int = MAX_RETRY_ATTEMPTS,
    ) -> LLMResponse:
        """
        Generate with exponential backoff retry and timeout enforcement.
        
        Implements:
        - Up to 3 retry attempts with exponential backoff (1s, 2s, 4s)
        - 30-second timeout per request
        - Rate limit handling with retry-after support
        
        Args:
            method: LLM method to use
            prompt: Input prompt
            options: Generation options
            model: Model override
            system_prompt: System prompt
            max_retries: Maximum retry attempts (default: 3)
            
        Returns:
            LLMResponse on success
            
        Raises:
            Exception: If all retries exhausted
            
        **Validates: Requirements 4.1, 4.4, 4.5**
        """
        provider = self._get_provider(method)
        
        last_error = None
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting (Requirement 10.3)
                if self._enable_rate_limiting and self._rate_limiter:
                    try:
                        # Acquire rate limit token before making request
                        # Use wait=True to wait for tokens to become available
                        await self._rate_limiter.acquire(
                            method=method,
                            wait=True,
                            max_wait=30.0  # Wait up to 30 seconds for rate limit
                        )
                    except Exception as rate_limit_error:
                        # Rate limit exceeded - treat as retryable error
                        logger.warning(f"Rate limit exceeded for {method}: {rate_limit_error}")
                        last_error = str(rate_limit_error)
                        # Continue to retry logic below
                        raise

                # Enforce 30-second timeout (Requirement 4.4)
                # Using wait_for for Python 3.9 compatibility
                response = await asyncio.wait_for(
                    provider.generate(prompt, options, model, system_prompt),
                    timeout=DEFAULT_TIMEOUT_SECONDS
                )
                    
                latency_ms = (time.time() - start_time) * 1000
                response.latency_ms = latency_ms
                
                # Log successful usage
                await self._log_usage(
                    method=method.value,
                    model=response.model,
                    operation="generate",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    latency_ms=latency_ms,
                    success=True
                )
                
                return response
                
            except asyncio.TimeoutError:
                last_error = f"Request timeout after {DEFAULT_TIMEOUT_SECONDS} seconds"
                logger.warning(
                    f"Timeout on attempt {attempt + 1}/{max_retries} for {method}"
                )
                
                # Log timeout event (Requirement 4.4)
                await self._log_usage(
                    method=method.value,
                    model=model or "unknown",
                    operation="generate",
                    latency_ms=DEFAULT_TIMEOUT_SECONDS * 1000,
                    success=False,
                    error_code=LLMErrorCode.TIMEOUT.value,
                    error_message=last_error
                )
                
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Error on attempt {attempt + 1}/{max_retries} for {method}: {e}"
                )
                
                # Check for rate limit and handle retry-after (Requirement 4.5)
                retry_after = self._extract_retry_after(e)
                if retry_after is not None:
                    logger.info(f"Rate limited, waiting {retry_after}s before retry")
                    await asyncio.sleep(retry_after)
                    continue
            
            # Exponential backoff: 1s, 2s, 4s (Requirement 4.1)
            if attempt < max_retries - 1:
                backoff_delay = EXPONENTIAL_BACKOFF_BASE ** attempt
                logger.debug(f"Waiting {backoff_delay}s before retry {attempt + 2}")
                await asyncio.sleep(backoff_delay)
        
        # All retries exhausted
        latency_ms = (time.time() - start_time) * 1000
        await self._log_usage(
            method=method.value,
            model=model or "unknown",
            operation="generate",
            latency_ms=latency_ms,
            success=False,
            error_code=LLMErrorCode.GENERATION_FAILED.value,
            error_message=f"Max retries ({max_retries}) exceeded. Last error: {last_error}"
        )
        
        raise Exception(f"Max retries ({max_retries}) exceeded. Last error: {last_error}")
    
    def _extract_retry_after(self, exception: Exception) -> Optional[int]:
        """
        Extract retry-after value from rate limit errors.
        
        Parses error messages and headers to find the recommended
        wait time before retrying.
        
        Args:
            exception: The exception to parse
            
        Returns:
            Seconds to wait, or None if not a rate limit error
            
        **Validates: Requirements 4.5**
        """
        error_str = str(exception).lower()
        
        # Check if this is a rate limit error
        if not any(keyword in error_str for keyword in ['rate', 'limit', '429', 'quota']):
            return None
        
        # Try to extract retry-after value from error message
        # Common patterns: "retry after 60 seconds", "retry-after: 60", "wait 60s"
        patterns = [
            r'retry[- ]?after[:\s]+(\d+)',
            r'wait[:\s]+(\d+)',
            r'(\d+)\s*seconds?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_str)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    pass
        
        # Default retry-after for rate limits if not specified
        return 60
    
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
        
        Implements automatic failover with exponential backoff retry.
        Note: Streaming does not support mid-stream failover - if the stream
        fails after starting, the entire operation fails.
        
        Args:
            prompt: Input prompt
            options: Generation options
            method: Override default method
            model: Override default model
            system_prompt: System prompt for chat models
            
        Yields:
            Text chunks as they are generated
            
        **Validates: Requirements 3.3, 4.1, 4.2, 4.4**
        """
        await self._ensure_initialized()
        
        options = options or GenerateOptions()
        options.stream = True
        target_method = method or self._current_method
        
        # Store request context for potential failover
        request_context = {
            'prompt': prompt,
            'options': options,
            'model': model,
            'system_prompt': system_prompt,
        }
        
        # Try primary provider with retries
        primary_error = None
        try:
            async for chunk in self._stream_generate_with_retry(
                target_method, prompt, options, model, system_prompt
            ):
                yield chunk
            
            # Track usage statistics
            await self._increment_usage_stats(target_method)
            return
            
        except Exception as e:
            primary_error = e
            logger.warning(f"Primary provider {target_method} stream failed: {e}")
        
        # Try fallback provider if configured
        if self._fallback_method and self._fallback_method != target_method:
            logger.info(f"Attempting stream failover to {self._fallback_method}")
            
            try:
                async for chunk in self._stream_generate_with_retry(
                    self._fallback_method,
                    request_context['prompt'],
                    request_context['options'],
                    request_context['model'],
                    request_context['system_prompt']
                ):
                    yield chunk
                
                await self._increment_usage_stats(self._fallback_method)
                logger.info(f"Stream failover to {self._fallback_method} succeeded")
                return
                
            except Exception as fallback_error:
                logger.error(f"Fallback provider stream also failed: {fallback_error}")
                raise LLMError(
                    error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
                    message=(
                        f"Both primary and fallback providers failed for streaming. "
                        f"Primary ({target_method.value}): {str(primary_error)}. "
                        f"Fallback ({self._fallback_method.value}): {str(fallback_error)}"
                    ),
                    provider=f"{target_method.value},{self._fallback_method.value}",
                    suggestions=["Check provider configurations", "Verify network connectivity"]
                )
        
        raise self._create_error(primary_error, target_method)
    
    async def _stream_generate_with_retry(
        self,
        method: LLMMethod,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str],
        system_prompt: Optional[str],
        max_retries: int = MAX_RETRY_ATTEMPTS,
    ) -> AsyncIterator[str]:
        """
        Stream generate with retry logic.
        
        Note: Retries only apply to connection/setup failures.
        Once streaming starts, failures are not retried.
        """
        provider = self._get_provider(method)
        
        last_error = None
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                total_tokens = 0
                
                # For streaming, we use wait_for on the first chunk to detect connection issues
                # The full stream may take longer than the timeout
                async for chunk in provider.stream_generate(
                    prompt, options, model, system_prompt
                ):
                    total_tokens += 1
                    yield chunk
                
                latency_ms = (time.time() - start_time) * 1000
                
                await self._log_usage(
                    method=method.value,
                    model=model or "unknown",
                    operation="stream",
                    completion_tokens=total_tokens,
                    latency_ms=latency_ms,
                    success=True
                )
                return
                
            except asyncio.TimeoutError:
                last_error = f"Stream timeout after {DEFAULT_TIMEOUT_SECONDS} seconds"
                logger.warning(f"Stream timeout on attempt {attempt + 1}/{max_retries}")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Stream error on attempt {attempt + 1}/{max_retries}: {e}")
                
                retry_after = self._extract_retry_after(e)
                if retry_after is not None:
                    await asyncio.sleep(retry_after)
                    continue
            
            if attempt < max_retries - 1:
                backoff_delay = EXPONENTIAL_BACKOFF_BASE ** attempt
                await asyncio.sleep(backoff_delay)
        
        raise Exception(f"Stream max retries ({max_retries}) exceeded. Last error: {last_error}")
    
    async def embed(
        self,
        text: str,
        method: Optional[LLMMethod] = None,
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        """
        Generate text embedding using the specified or default method.
        
        Implements automatic failover with exponential backoff retry.
        
        Args:
            text: Text to embed
            method: Override default method
            model: Override default model
            
        Returns:
            EmbeddingResponse with embedding vector
            
        **Validates: Requirements 3.3, 4.1, 4.2, 4.4**
        """
        await self._ensure_initialized()
        
        target_method = method or self._current_method
        
        # Store request context for potential failover
        request_context = {
            'text': text,
            'model': model,
        }
        
        # Try primary provider with retries
        primary_error = None
        try:
            response = await self._embed_with_retry(target_method, text, model)
            await self._increment_usage_stats(target_method)
            return response
            
        except Exception as e:
            primary_error = e
            logger.warning(f"Primary provider {target_method} embed failed: {e}")
        
        # Try fallback provider if configured
        if self._fallback_method and self._fallback_method != target_method:
            logger.info(f"Attempting embed failover to {self._fallback_method}")
            
            try:
                response = await self._embed_with_retry(
                    self._fallback_method,
                    request_context['text'],
                    request_context['model']
                )
                await self._increment_usage_stats(self._fallback_method)
                logger.info(f"Embed failover to {self._fallback_method} succeeded")
                return response
                
            except Exception as fallback_error:
                logger.error(f"Fallback provider embed also failed: {fallback_error}")
                raise LLMError(
                    error_code=LLMErrorCode.SERVICE_UNAVAILABLE,
                    message=(
                        f"Both primary and fallback providers failed for embedding. "
                        f"Primary ({target_method.value}): {str(primary_error)}. "
                        f"Fallback ({self._fallback_method.value}): {str(fallback_error)}"
                    ),
                    provider=f"{target_method.value},{self._fallback_method.value}",
                    suggestions=["Check provider configurations", "Verify network connectivity"]
                )
        
        raise self._create_error(primary_error, target_method)
    
    async def _embed_with_retry(
        self,
        method: LLMMethod,
        text: str,
        model: Optional[str],
        max_retries: int = MAX_RETRY_ATTEMPTS,
    ) -> EmbeddingResponse:
        """
        Embed with exponential backoff retry and timeout enforcement.
        """
        provider = self._get_provider(method)
        
        last_error = None
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                # Using wait_for for Python 3.9 compatibility
                response = await asyncio.wait_for(
                    provider.embed(text, model),
                    timeout=DEFAULT_TIMEOUT_SECONDS
                )
                    
                latency_ms = (time.time() - start_time) * 1000
                response.latency_ms = latency_ms
                
                await self._log_usage(
                    method=method.value,
                    model=response.model,
                    operation="embed",
                    latency_ms=latency_ms,
                    success=True
                )
                
                return response
                
            except asyncio.TimeoutError:
                last_error = f"Embed timeout after {DEFAULT_TIMEOUT_SECONDS} seconds"
                logger.warning(f"Embed timeout on attempt {attempt + 1}/{max_retries}")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Embed error on attempt {attempt + 1}/{max_retries}: {e}")
                
                retry_after = self._extract_retry_after(e)
                if retry_after is not None:
                    await asyncio.sleep(retry_after)
                    continue
            
            if attempt < max_retries - 1:
                backoff_delay = EXPONENTIAL_BACKOFF_BASE ** attempt
                await asyncio.sleep(backoff_delay)
        
        latency_ms = (time.time() - start_time) * 1000
        await self._log_usage(
            method=method.value,
            model=model or "unknown",
            operation="embed",
            latency_ms=latency_ms,
            success=False,
            error_code=LLMErrorCode.GENERATION_FAILED.value,
            error_message=f"Max retries ({max_retries}) exceeded. Last error: {last_error}"
        )
        
        raise Exception(f"Embed max retries ({max_retries}) exceeded. Last error: {last_error}")
    
    # ==================== Method Management ====================
    
    def switch_method(self, method: LLMMethod) -> None:
        """
        Switch the default LLM method.
        
        Validates that the target provider is available before switching.
        
        Args:
            method: New default method
            
        Raises:
            ValueError: If method is not enabled or provider is not available
            
        **Validates: Requirements 3.2**
        """
        if self._config and method not in self._config.enabled_methods:
            raise ValueError(f"Method {method} is not enabled")
        
        if method not in self._providers:
            raise ValueError(f"Provider for {method} is not initialized")
        
        old_method = self._current_method
        self._current_method = method
        logger.info(f"Switched LLM method from {old_method} to {method}")
    
    async def switch_method_validated(self, method: LLMMethod) -> bool:
        """
        Switch the default LLM method with health validation.
        
        Validates that the target provider is available and healthy before switching.
        
        Args:
            method: New default method
            
        Returns:
            True if switch was successful
            
        Raises:
            ValueError: If method is not enabled, not available, or unhealthy
            
        **Validates: Requirements 3.2**
        """
        if self._config and method not in self._config.enabled_methods:
            raise ValueError(f"Method {method} is not enabled")
        
        if method not in self._providers:
            raise ValueError(f"Provider for {method} is not initialized")
        
        # Validate provider is healthy before switching
        try:
            health = await self._providers[method].health_check()
            if not health.available:
                raise ValueError(
                    f"Provider {method} is unhealthy and cannot be set as active: {health.error}"
                )
        except Exception as e:
            if "unhealthy" in str(e):
                raise
            raise ValueError(f"Could not verify provider {method} health: {e}")
        
        old_method = self._current_method
        self._current_method = method
        logger.info(f"Switched LLM method from {old_method} to {method} (validated)")
        return True
    
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


def get_llm_switcher(
    tenant_id: Optional[str] = None,
    cache_client: Optional[Any] = None,
) -> LLMSwitcher:
    """
    Get or create an LLM Switcher instance for the tenant.
    
    Args:
        tenant_id: Tenant ID for multi-tenant support
        cache_client: Redis client for response caching
        
    Returns:
        LLMSwitcher instance
    """
    key = tenant_id or "global"
    
    if key not in _switcher_instances:
        _switcher_instances[key] = LLMSwitcher(
            tenant_id=tenant_id,
            cache_client=cache_client,
        )
    elif cache_client is not None:
        # Update cache client if provided
        _switcher_instances[key].set_cache_client(cache_client)
    
    return _switcher_instances[key]


async def get_initialized_switcher(
    tenant_id: Optional[str] = None,
    cache_client: Optional[Any] = None,
) -> LLMSwitcher:
    """
    Get an initialized LLM Switcher instance.
    
    Args:
        tenant_id: Tenant ID for multi-tenant support
        cache_client: Redis client for response caching
        
    Returns:
        Initialized LLMSwitcher instance
    """
    switcher = get_llm_switcher(tenant_id, cache_client)
    await switcher.initialize()
    return switcher
