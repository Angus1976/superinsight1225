"""
LLM Rate Limiter for SuperInsight platform.

Implements rate limiting for LLM providers to prevent quota exhaustion.
Uses a token bucket algorithm with per-provider configuration.

Features:
- Token bucket rate limiting algorithm
- Per-provider rate limit configuration
- Async-safe implementation using asyncio.Lock
- Integration with LLMSwitcher
- Automatic token replenishment

Requirements Implemented:
- 10.3: When request volume is high, THE System SHALL implement rate limiting
        to prevent provider quota exhaustion

Property 29: Rate Limiting
- For any time window, the number of requests sent to a provider should not
  exceed the configured rate limit for that provider.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from src.ai.llm_schemas import LLMMethod, LLMError, LLMErrorCode
except ImportError:
    from ai.llm_schemas import LLMMethod, LLMError, LLMErrorCode


logger = logging.getLogger(__name__)


class RateLimitExceededError(Exception):
    """
    Exception raised when rate limit is exceeded.
    
    Attributes:
        provider: The provider that was rate limited
        retry_after: Seconds to wait before retrying
        message: Human-readable error message
    """
    
    def __init__(
        self,
        provider: str,
        retry_after: float,
        message: Optional[str] = None
    ):
        self.provider = provider
        self.retry_after = retry_after
        self.message = message or f"Rate limit exceeded for provider {provider}. Retry after {retry_after:.1f}s"
        super().__init__(self.message)


@dataclass
class RateLimitConfig:
    """
    Configuration for rate limiting a specific provider.
    
    Uses token bucket algorithm parameters:
    - max_tokens: Maximum tokens in the bucket (burst capacity)
    - refill_rate: Tokens added per second
    - tokens_per_request: Tokens consumed per request
    
    Attributes:
        max_tokens: Maximum number of tokens in the bucket
        refill_rate: Rate at which tokens are replenished (tokens/second)
        tokens_per_request: Number of tokens consumed per request
        enabled: Whether rate limiting is enabled for this provider
    """
    max_tokens: float = 60.0  # Default: 60 requests burst capacity
    refill_rate: float = 1.0  # Default: 1 request per second
    tokens_per_request: float = 1.0  # Default: 1 token per request
    enabled: bool = True
    
    @property
    def requests_per_minute(self) -> float:
        """Calculate effective requests per minute."""
        return self.refill_rate * 60 / self.tokens_per_request
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_tokens": self.max_tokens,
            "refill_rate": self.refill_rate,
            "tokens_per_request": self.tokens_per_request,
            "enabled": self.enabled,
            "requests_per_minute": self.requests_per_minute,
        }


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting.
    
    Implements the token bucket algorithm:
    - Bucket starts full with max_tokens
    - Tokens are consumed on each request
    - Tokens are replenished at refill_rate per second
    - Requests are rejected when bucket is empty
    
    Attributes:
        config: Rate limit configuration
        tokens: Current number of tokens in the bucket
        last_refill: Timestamp of last token refill
    """
    config: RateLimitConfig
    tokens: float = field(default=0.0)
    last_refill: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Initialize bucket with max tokens."""
        if self.tokens == 0.0:
            self.tokens = self.config.max_tokens
    
    def _refill(self) -> None:
        """
        Refill tokens based on elapsed time.
        
        Calculates tokens to add based on time since last refill
        and the configured refill rate.
        """
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add
        tokens_to_add = elapsed * self.config.refill_rate
        
        # Add tokens up to max
        self.tokens = min(self.config.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def try_acquire(self, tokens: Optional[float] = None) -> bool:
        """
        Try to acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire (default: tokens_per_request)
            
        Returns:
            True if tokens were acquired, False if rate limit exceeded
        """
        if not self.config.enabled:
            return True
        
        # Refill tokens first
        self._refill()
        
        # Determine tokens needed
        tokens_needed = tokens if tokens is not None else self.config.tokens_per_request
        
        # Check if we have enough tokens
        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            return True
        
        return False
    
    def time_until_available(self, tokens: Optional[float] = None) -> float:
        """
        Calculate time until tokens will be available.
        
        Args:
            tokens: Number of tokens needed (default: tokens_per_request)
            
        Returns:
            Seconds until tokens will be available (float('inf') if no refill)
        """
        if not self.config.enabled:
            return 0.0
        
        # Refill tokens first
        self._refill()
        
        # Determine tokens needed
        tokens_needed = tokens if tokens is not None else self.config.tokens_per_request
        
        # If we have enough, return 0
        if self.tokens >= tokens_needed:
            return 0.0
        
        # Calculate time to refill needed tokens
        tokens_deficit = tokens_needed - self.tokens
        
        # Handle zero refill rate (tokens will never be available)
        if self.config.refill_rate <= 0:
            return float('inf')
        
        return tokens_deficit / self.config.refill_rate
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bucket status."""
        self._refill()
        return {
            "tokens": round(self.tokens, 2),
            "max_tokens": self.config.max_tokens,
            "refill_rate": self.config.refill_rate,
            "enabled": self.config.enabled,
            "available": self.tokens >= self.config.tokens_per_request,
        }


# Default rate limit configurations for different providers
DEFAULT_RATE_LIMITS: Dict[LLMMethod, RateLimitConfig] = {
    # Cloud providers - typically have higher rate limits
    LLMMethod.CLOUD_OPENAI: RateLimitConfig(
        max_tokens=60.0,  # 60 requests burst
        refill_rate=1.0,  # 1 request/second = 60 RPM
        tokens_per_request=1.0,
    ),
    LLMMethod.CLOUD_AZURE: RateLimitConfig(
        max_tokens=60.0,
        refill_rate=1.0,
        tokens_per_request=1.0,
    ),
    # Chinese providers - may have different limits
    LLMMethod.CHINA_QWEN: RateLimitConfig(
        max_tokens=30.0,  # 30 requests burst
        refill_rate=0.5,  # 0.5 request/second = 30 RPM
        tokens_per_request=1.0,
    ),
    LLMMethod.CHINA_ZHIPU: RateLimitConfig(
        max_tokens=30.0,
        refill_rate=0.5,
        tokens_per_request=1.0,
    ),
    LLMMethod.CHINA_BAIDU: RateLimitConfig(
        max_tokens=30.0,
        refill_rate=0.5,
        tokens_per_request=1.0,
    ),
    LLMMethod.CHINA_HUNYUAN: RateLimitConfig(
        max_tokens=30.0,
        refill_rate=0.5,
        tokens_per_request=1.0,
    ),
    # Local providers - typically no rate limits needed
    LLMMethod.LOCAL_OLLAMA: RateLimitConfig(
        max_tokens=100.0,  # Higher burst for local
        refill_rate=10.0,  # 10 requests/second
        tokens_per_request=1.0,
        enabled=False,  # Disabled by default for local
    ),
}


class RateLimiter:
    """
    Rate limiter for LLM providers using token bucket algorithm.
    
    Implements per-provider rate limiting to prevent quota exhaustion.
    Uses asyncio.Lock for thread-safe async operations.
    
    Features:
    - Per-provider rate limit configuration
    - Token bucket algorithm with configurable parameters
    - Automatic token replenishment
    - Wait-for-token support for blocking mode
    - Statistics tracking
    
    **Validates: Requirements 10.3**
    """
    
    def __init__(
        self,
        default_config: Optional[RateLimitConfig] = None,
        provider_configs: Optional[Dict[LLMMethod, RateLimitConfig]] = None,
    ):
        """
        Initialize the rate limiter.
        
        Args:
            default_config: Default rate limit config for unconfigured providers
            provider_configs: Per-provider rate limit configurations
        """
        self._default_config = default_config or RateLimitConfig()
        self._provider_configs: Dict[LLMMethod, RateLimitConfig] = {}
        
        # Initialize with default configs
        for method, config in DEFAULT_RATE_LIMITS.items():
            self._provider_configs[method] = config
        
        # Override with provided configs
        if provider_configs:
            for method, config in provider_configs.items():
                self._provider_configs[method] = config
        
        # Token buckets for each provider
        self._buckets: Dict[LLMMethod, TokenBucket] = {}
        
        # Async lock for thread-safe operations (per async-sync-safety.md)
        self._lock = asyncio.Lock()
        
        # Statistics tracking
        self._stats: Dict[str, Dict[str, int]] = {
            "requests": {},  # Total requests per provider
            "allowed": {},   # Allowed requests per provider
            "rejected": {},  # Rejected requests per provider
        }
        
        logger.debug("RateLimiter initialized")
    
    def _get_bucket(self, method: LLMMethod) -> TokenBucket:
        """
        Get or create token bucket for a provider.
        
        Args:
            method: LLM method/provider
            
        Returns:
            TokenBucket for the provider
        """
        if method not in self._buckets:
            config = self._provider_configs.get(method, self._default_config)
            self._buckets[method] = TokenBucket(config=config)
        
        return self._buckets[method]
    
    async def acquire(
        self,
        method: LLMMethod,
        tokens: Optional[float] = None,
        wait: bool = False,
        max_wait: float = 60.0,
    ) -> bool:
        """
        Acquire rate limit tokens for a request.
        
        Args:
            method: LLM method/provider to acquire tokens for
            tokens: Number of tokens to acquire (default: tokens_per_request)
            wait: If True, wait for tokens to become available
            max_wait: Maximum time to wait for tokens (seconds)
            
        Returns:
            True if tokens were acquired
            
        Raises:
            RateLimitExceededError: If rate limit exceeded and wait=False
            
        **Validates: Requirements 10.3**
        """
        async with self._lock:
            bucket = self._get_bucket(method)
            
            # Track request
            method_key = method.value
            self._stats["requests"][method_key] = \
                self._stats["requests"].get(method_key, 0) + 1
            
            # Try to acquire tokens
            if bucket.try_acquire(tokens):
                self._stats["allowed"][method_key] = \
                    self._stats["allowed"].get(method_key, 0) + 1
                return True
            
            # If not waiting, reject immediately
            if not wait:
                self._stats["rejected"][method_key] = \
                    self._stats["rejected"].get(method_key, 0) + 1
                
                retry_after = bucket.time_until_available(tokens)
                raise RateLimitExceededError(
                    provider=method.value,
                    retry_after=retry_after,
                )
        
        # Wait mode: wait for tokens to become available
        start_time = time.time()
        while True:
            async with self._lock:
                bucket = self._get_bucket(method)
                
                if bucket.try_acquire(tokens):
                    self._stats["allowed"][method.value] = \
                        self._stats["allowed"].get(method.value, 0) + 1
                    return True
                
                wait_time = bucket.time_until_available(tokens)
            
            # Check if we've exceeded max wait time
            elapsed = time.time() - start_time
            if elapsed + wait_time > max_wait:
                async with self._lock:
                    self._stats["rejected"][method.value] = \
                        self._stats["rejected"].get(method.value, 0) + 1
                
                raise RateLimitExceededError(
                    provider=method.value,
                    retry_after=wait_time,
                    message=f"Rate limit exceeded for {method.value}. "
                            f"Max wait time ({max_wait}s) would be exceeded.",
                )
            
            # Wait for tokens
            await asyncio.sleep(min(wait_time, max_wait - elapsed))
    
    async def check_available(
        self,
        method: LLMMethod,
        tokens: Optional[float] = None,
    ) -> bool:
        """
        Check if tokens are available without consuming them.
        
        Args:
            method: LLM method/provider to check
            tokens: Number of tokens to check for
            
        Returns:
            True if tokens are available
        """
        async with self._lock:
            bucket = self._get_bucket(method)
            bucket._refill()
            
            tokens_needed = tokens if tokens is not None else bucket.config.tokens_per_request
            return bucket.tokens >= tokens_needed
    
    async def get_wait_time(
        self,
        method: LLMMethod,
        tokens: Optional[float] = None,
    ) -> float:
        """
        Get time until tokens will be available.
        
        Args:
            method: LLM method/provider
            tokens: Number of tokens needed
            
        Returns:
            Seconds until tokens will be available (0 if available now)
        """
        async with self._lock:
            bucket = self._get_bucket(method)
            return bucket.time_until_available(tokens)
    
    def configure_provider(
        self,
        method: LLMMethod,
        config: RateLimitConfig,
    ) -> None:
        """
        Configure rate limit for a specific provider.
        
        Args:
            method: LLM method/provider to configure
            config: Rate limit configuration
        """
        self._provider_configs[method] = config
        
        # Reset bucket with new config
        if method in self._buckets:
            del self._buckets[method]
        
        logger.info(
            f"Configured rate limit for {method.value}: "
            f"{config.requests_per_minute:.1f} RPM"
        )
    
    def enable_provider(self, method: LLMMethod, enabled: bool = True) -> None:
        """
        Enable or disable rate limiting for a provider.
        
        Args:
            method: LLM method/provider
            enabled: Whether to enable rate limiting
        """
        if method in self._provider_configs:
            self._provider_configs[method].enabled = enabled
        else:
            config = RateLimitConfig(enabled=enabled)
            self._provider_configs[method] = config
        
        # Update bucket if exists
        if method in self._buckets:
            self._buckets[method].config.enabled = enabled
        
        logger.info(
            f"Rate limiting {'enabled' if enabled else 'disabled'} "
            f"for {method.value}"
        )
    
    async def get_status(self, method: Optional[LLMMethod] = None) -> Dict[str, Any]:
        """
        Get rate limiter status.
        
        Args:
            method: Specific provider to get status for, or None for all
            
        Returns:
            Status dictionary with bucket states and statistics
        """
        async with self._lock:
            if method:
                bucket = self._get_bucket(method)
                return {
                    "provider": method.value,
                    "bucket": bucket.get_status(),
                    "stats": {
                        "requests": self._stats["requests"].get(method.value, 0),
                        "allowed": self._stats["allowed"].get(method.value, 0),
                        "rejected": self._stats["rejected"].get(method.value, 0),
                    },
                }
            
            # Return status for all providers
            result = {}
            for m in self._provider_configs.keys():
                bucket = self._get_bucket(m)
                result[m.value] = {
                    "bucket": bucket.get_status(),
                    "stats": {
                        "requests": self._stats["requests"].get(m.value, 0),
                        "allowed": self._stats["allowed"].get(m.value, 0),
                        "rejected": self._stats["rejected"].get(m.value, 0),
                    },
                }
            
            return result
    
    async def get_statistics(self) -> Dict[str, Dict[str, int]]:
        """
        Get rate limiting statistics.
        
        Returns:
            Dictionary with requests, allowed, and rejected counts per provider
        """
        async with self._lock:
            return {
                "requests": dict(self._stats["requests"]),
                "allowed": dict(self._stats["allowed"]),
                "rejected": dict(self._stats["rejected"]),
            }
    
    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        self._stats = {
            "requests": {},
            "allowed": {},
            "rejected": {},
        }
        logger.info("Rate limiter statistics reset")
    
    async def reset_bucket(self, method: LLMMethod) -> None:
        """
        Reset token bucket for a provider to full capacity.
        
        Args:
            method: LLM method/provider to reset
        """
        async with self._lock:
            if method in self._buckets:
                bucket = self._buckets[method]
                bucket.tokens = bucket.config.max_tokens
                bucket.last_refill = time.time()
                logger.info(f"Reset token bucket for {method.value}")


# ==================== Singleton Instance ====================

_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    default_config: Optional[RateLimitConfig] = None,
    provider_configs: Optional[Dict[LLMMethod, RateLimitConfig]] = None,
) -> RateLimiter:
    """
    Get or create the global RateLimiter instance.
    
    Args:
        default_config: Default rate limit config for unconfigured providers
        provider_configs: Per-provider rate limit configurations
        
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            default_config=default_config,
            provider_configs=provider_configs,
        )
    
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Reset the global rate limiter instance (for testing)."""
    global _rate_limiter
    _rate_limiter = None
