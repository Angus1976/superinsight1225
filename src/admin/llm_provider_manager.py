"""
LLM Provider Manager for SuperInsight Platform.

Manages LLM provider configurations, connection testing, and quota monitoring.
Supports multiple providers including OpenAI, Anthropic, Alibaba Cloud, and others.

This module follows async-first architecture using asyncio and aiohttp.
All I/O operations are non-blocking to prevent event loop blocking.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

import aiohttp
from pydantic import BaseModel, Field

from src.admin.schemas import (
    LLMType,
    ConnectionTestResult,
    LLMConfigResponse
)


logger = logging.getLogger(__name__)


# ============== Provider-Specific Models ==============

class ProviderType(str, Enum):
    """LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    ALIBABA_QIANWEN = "qianwen"
    ZHIPU = "zhipu"
    TENCENT_HUNYUAN = "hunyuan"
    LOCAL_OLLAMA = "local_ollama"
    CUSTOM = "custom"


class QuotaInfo(BaseModel):
    """API quota usage information."""
    provider: str = Field(..., description="Provider name")
    config_id: str = Field(..., description="Configuration ID")
    total_requests: int = Field(default=0, description="Total requests made")
    successful_requests: int = Field(default=0, description="Successful requests")
    failed_requests: int = Field(default=0, description="Failed requests")
    total_tokens: int = Field(default=0, description="Total tokens used")
    quota_limit: Optional[int] = Field(default=None, description="Quota limit if known")
    quota_remaining: Optional[int] = Field(default=None, description="Remaining quota")
    reset_at: Optional[datetime] = Field(default=None, description="Quota reset time")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    alert_threshold_percent: float = Field(default=80.0, description="Alert threshold percentage")
    last_alert_sent: Optional[datetime] = Field(default=None, description="Last alert timestamp")


class ConnectionTestResult(BaseModel):
    """Connection test result with detailed information."""
    success: bool = Field(..., description="Whether test succeeded")
    provider: str = Field(..., description="Provider name")
    latency_ms: float = Field(default=0.0, description="Response latency in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    tested_at: datetime = Field(default_factory=datetime.utcnow)
    suggestions: List[str] = Field(default_factory=list, description="Troubleshooting suggestions")


# ============== Provider Configuration ==============

class ProviderConfig:
    """Provider-specific configuration and endpoints."""
    
    PROVIDERS = {
        ProviderType.OPENAI: {
            "default_endpoint": "https://api.openai.com/v1",
            "test_endpoint": "/models",
            "auth_header": "Authorization",
            "auth_prefix": "Bearer",
            "timeout": 10,
            "models_endpoint": "/models",
        },
        ProviderType.ANTHROPIC: {
            "default_endpoint": "https://api.anthropic.com/v1",
            "test_endpoint": "/messages",
            "auth_header": "x-api-key",
            "auth_prefix": "",
            "timeout": 10,
            "models_endpoint": "/models",
        },
        ProviderType.ALIBABA_QIANWEN: {
            "default_endpoint": "https://dashscope.aliyuncs.com/api/v1",
            "test_endpoint": "/services/aigc/text-generation/generation",
            "auth_header": "Authorization",
            "auth_prefix": "Bearer",
            "timeout": 10,
            "models_endpoint": "/models",
        },
        ProviderType.ZHIPU: {
            "default_endpoint": "https://open.bigmodel.cn/api/paas/v4",
            "test_endpoint": "/chat/completions",
            "auth_header": "Authorization",
            "auth_prefix": "Bearer",
            "timeout": 10,
            "models_endpoint": "/models",
        },
        ProviderType.TENCENT_HUNYUAN: {
            "default_endpoint": "https://hunyuan.tencentcloudapi.com",
            "test_endpoint": "/",
            "auth_header": "Authorization",
            "auth_prefix": "",
            "timeout": 10,
            "models_endpoint": "/models",
        },
        ProviderType.LOCAL_OLLAMA: {
            "default_endpoint": "http://localhost:11434",
            "test_endpoint": "/api/tags",
            "auth_header": None,
            "auth_prefix": "",
            "timeout": 10,
            "models_endpoint": "/api/tags",
        },
        ProviderType.CUSTOM: {
            "default_endpoint": "",
            "test_endpoint": "/",
            "auth_header": "Authorization",
            "auth_prefix": "Bearer",
            "timeout": 10,
            "models_endpoint": "/models",
        },
    }
    
    @classmethod
    def get_config(cls, provider: str) -> Dict[str, Any]:
        """Get configuration for a provider."""
        provider_type = cls._normalize_provider(provider)
        return cls.PROVIDERS.get(provider_type, cls.PROVIDERS[ProviderType.CUSTOM])
    
    @classmethod
    def _normalize_provider(cls, provider: str) -> ProviderType:
        """Normalize provider name to ProviderType."""
        provider_lower = provider.lower()
        
        if provider_lower in ["openai", "gpt"]:
            return ProviderType.OPENAI
        elif provider_lower in ["anthropic", "claude"]:
            return ProviderType.ANTHROPIC
        elif provider_lower in ["qianwen", "alibaba", "tongyi"]:
            return ProviderType.ALIBABA_QIANWEN
        elif provider_lower in ["zhipu", "glm"]:
            return ProviderType.ZHIPU
        elif provider_lower in ["hunyuan", "tencent"]:
            return ProviderType.TENCENT_HUNYUAN
        elif provider_lower in ["ollama", "local"]:
            return ProviderType.LOCAL_OLLAMA
        else:
            return ProviderType.CUSTOM


# ============== LLM Provider Manager ==============

class LLMProviderManager:
    """
    Manages LLM provider configurations and operations.
    
    Features:
    - Connection testing with timeout enforcement
    - Provider-specific authentication handling
    - Quota monitoring and tracking
    - Available models retrieval
    - API key validation
    
    All operations are async to prevent blocking the event loop.
    """
    
    def __init__(self):
        """Initialize the LLM provider manager."""
        self._quota_cache: Dict[str, QuotaInfo] = {}
        self._lock = asyncio.Lock()  # Async lock for thread-safe operations
        self._alert_handlers: List[Callable[[str, QuotaInfo], None]] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval: int = 60  # Check every 60 seconds
        self._running: bool = False
        logger.info("LLMProviderManager initialized")
    
    async def test_connection(
        self,
        provider: str,
        api_key: Optional[str],
        endpoint: Optional[str] = None,
        timeout: int = 10
    ) -> ConnectionTestResult:
        """
        Test connection to an LLM provider.
        
        Args:
            provider: Provider name (openai, anthropic, qianwen, etc.)
            api_key: API key for authentication
            endpoint: Custom endpoint URL (optional)
            timeout: Timeout in seconds (default: 10)
        
        Returns:
            ConnectionTestResult with success status and details
        
        Validates Requirements: 1.3, 1.5
        """
        start_time = asyncio.get_event_loop().time()
        provider_config = ProviderConfig.get_config(provider)
        
        # Use custom endpoint or default
        base_url = endpoint or provider_config["default_endpoint"]
        test_path = provider_config["test_endpoint"]
        test_url = f"{base_url.rstrip('/')}{test_path}"
        
        # Prepare authentication headers
        headers = self._build_auth_headers(provider_config, api_key)
        
        try:
            # Enforce timeout using asyncio.wait_for (compatible with Python 3.7+)
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        test_url,
                        headers=headers,
                        ssl=True,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                            end_time = asyncio.get_event_loop().time()
                            latency_ms = (end_time - start_time) * 1000
                            
                            if response.status == 200:
                                logger.info(
                                    f"Connection test successful for {provider}: "
                                    f"{latency_ms:.2f}ms"
                                )
                                return ConnectionTestResult(
                                    success=True,
                                    provider=provider,
                                    latency_ms=latency_ms,
                                    details={
                                        "status_code": response.status,
                                        "endpoint": test_url
                                    }
                                )
                            elif response.status == 401:
                                error_msg = "Authentication failed - invalid API key"
                                return ConnectionTestResult(
                                    success=False,
                                    provider=provider,
                                    latency_ms=latency_ms,
                                    error_message=error_msg,
                                    error_code="AUTH_FAILED",
                                    suggestions=[
                                        "Verify API key is correct",
                                        "Check if API key has expired",
                                        "Ensure API key has necessary permissions"
                                    ]
                                )
                            elif response.status == 403:
                                error_msg = "Access forbidden - insufficient permissions"
                                return ConnectionTestResult(
                                    success=False,
                                    provider=provider,
                                    latency_ms=latency_ms,
                                    error_message=error_msg,
                                    error_code="FORBIDDEN",
                                    suggestions=[
                                        "Check API key permissions",
                                        "Verify account is active",
                                        "Contact provider support"
                                    ]
                                )
                            elif response.status == 429:
                                error_msg = "Rate limit exceeded"
                                return ConnectionTestResult(
                                    success=False,
                                    provider=provider,
                                    latency_ms=latency_ms,
                                    error_message=error_msg,
                                    error_code="RATE_LIMIT",
                                    suggestions=[
                                        "Wait before retrying",
                                        "Check quota limits",
                                        "Consider upgrading plan"
                                    ]
                                )
                            else:
                                error_text = await response.text()
                                error_msg = f"HTTP {response.status}: {error_text[:200]}"
                                return ConnectionTestResult(
                                    success=False,
                                    provider=provider,
                                    latency_ms=latency_ms,
                                    error_message=error_msg,
                                    error_code=f"HTTP_{response.status}",
                                    details={"status_code": response.status}
                                )
                
                except asyncio.TimeoutError:
                    logger.warning(f"Connection test timeout for {provider} after {timeout}s")
                    return ConnectionTestResult(
                        success=False,
                        provider=provider,
                        latency_ms=timeout * 1000,
                        error_message=f"Connection timeout after {timeout} seconds",
                        error_code="TIMEOUT",
                        suggestions=[
                            "Check network connectivity",
                            "Verify endpoint URL is correct",
                            "Check if firewall is blocking connection",
                            "Try increasing timeout value"
                        ]
                    )
        
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error for {provider}: {e}")
            return ConnectionTestResult(
                success=False,
                provider=provider,
                error_message=f"Connection failed: {str(e)}",
                error_code="CONNECTION_ERROR",
                suggestions=[
                    "Verify endpoint URL is correct",
                    "Check network connectivity",
                    "Ensure DNS resolution works",
                    "Check if service is available"
                ]
            )
        
        except aiohttp.ClientSSLError as e:
            logger.error(f"SSL error for {provider}: {e}")
            return ConnectionTestResult(
                success=False,
                provider=provider,
                error_message=f"SSL/TLS error: {str(e)}",
                error_code="SSL_ERROR",
                suggestions=[
                    "Check SSL certificate validity",
                    "Verify system time is correct",
                    "Update SSL certificates",
                    "Try disabling SSL verification (not recommended for production)"
                ]
            )
        
        except Exception as e:
            logger.error(f"Unexpected error testing {provider}: {e}", exc_info=True)
            return ConnectionTestResult(
                success=False,
                provider=provider,
                error_message=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                suggestions=[
                    "Check logs for detailed error information",
                    "Verify configuration is correct",
                    "Contact support if issue persists"
                ]
            )
    
    def _build_auth_headers(
        self,
        provider_config: Dict[str, Any],
        api_key: Optional[str]
    ) -> Dict[str, str]:
        """
        Build authentication headers for a provider.
        
        Args:
            provider_config: Provider configuration
            api_key: API key
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "User-Agent": "SuperInsight-Platform/1.0",
            "Accept": "application/json"
        }
        
        if api_key and provider_config.get("auth_header"):
            auth_header = provider_config["auth_header"]
            auth_prefix = provider_config.get("auth_prefix", "")
            
            if auth_prefix:
                headers[auth_header] = f"{auth_prefix} {api_key}"
            else:
                headers[auth_header] = api_key
        
        return headers
    
    async def get_available_models(
        self,
        provider: str,
        api_key: Optional[str],
        endpoint: Optional[str] = None
    ) -> List[str]:
        """
        Get list of available models from a provider.
        
        Args:
            provider: Provider name
            api_key: API key for authentication
            endpoint: Custom endpoint URL (optional)
        
        Returns:
            List of model names/identifiers
        
        Validates Requirements: 1.3
        """
        provider_config = ProviderConfig.get_config(provider)
        base_url = endpoint or provider_config["default_endpoint"]
        models_path = provider_config.get("models_endpoint", "/models")
        models_url = f"{base_url.rstrip('/')}{models_path}"
        
        headers = self._build_auth_headers(provider_config, api_key)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    models_url,
                    headers=headers,
                    ssl=True,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Parse response based on provider
                            models = self._parse_models_response(provider, data)
                            logger.info(f"Retrieved {len(models)} models from {provider}")
                            return models
                        else:
                            logger.warning(
                                f"Failed to get models from {provider}: "
                                f"HTTP {response.status}"
                            )
                            return []
        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout getting models from {provider}")
            return []
        
        except Exception as e:
            logger.error(f"Error getting models from {provider}: {e}")
            return []
    
    def _parse_models_response(
        self,
        provider: str,
        data: Dict[str, Any]
    ) -> List[str]:
        """
        Parse models list from provider-specific response format.
        
        Args:
            provider: Provider name
            data: Response data
        
        Returns:
            List of model names
        """
        provider_lower = provider.lower()
        
        try:
            if provider_lower in ["openai", "gpt"]:
                # OpenAI format: {"data": [{"id": "model-name"}, ...]}
                return [model["id"] for model in data.get("data", [])]
            
            elif provider_lower in ["anthropic", "claude"]:
                # Anthropic format may vary
                return data.get("models", [])
            
            elif provider_lower in ["ollama", "local"]:
                # Ollama format: {"models": [{"name": "model-name"}, ...]}
                return [model["name"] for model in data.get("models", [])]
            
            elif provider_lower in ["qianwen", "alibaba"]:
                # Alibaba Cloud format
                return data.get("data", {}).get("models", [])
            
            else:
                # Generic format - try common patterns
                if "data" in data and isinstance(data["data"], list):
                    return [
                        item.get("id") or item.get("name") or str(item)
                        for item in data["data"]
                    ]
                elif "models" in data and isinstance(data["models"], list):
                    return [
                        item.get("id") or item.get("name") or str(item)
                        for item in data["models"]
                    ]
                else:
                    return []
        
        except (KeyError, TypeError, AttributeError) as e:
            logger.warning(f"Error parsing models response for {provider}: {e}")
            return []
    
    async def validate_api_key(
        self,
        provider: str,
        api_key: str,
        endpoint: Optional[str] = None
    ) -> bool:
        """
        Validate an API key for a provider.
        
        Args:
            provider: Provider name
            api_key: API key to validate
            endpoint: Custom endpoint URL (optional)
        
        Returns:
            True if API key is valid, False otherwise
        
        Validates Requirements: 1.5
        """
        result = await self.test_connection(provider, api_key, endpoint)
        return result.success
    
    async def get_quota_usage(self, config_id: str) -> Optional[QuotaInfo]:
        """
        Get quota usage information for a configuration.
        
        Args:
            config_id: Configuration ID
        
        Returns:
            QuotaInfo if available, None otherwise
        
        Validates Requirements: 10.4
        """
        async with self._lock:
            return self._quota_cache.get(config_id)
    
    async def update_quota_usage(
        self,
        config_id: str,
        provider: str,
        tokens_used: int = 0,
        success: bool = True
    ) -> None:
        """
        Update quota usage for a configuration.
        
        Args:
            config_id: Configuration ID
            provider: Provider name
            tokens_used: Number of tokens used
            success: Whether the request was successful
        """
        async with self._lock:
            if config_id not in self._quota_cache:
                self._quota_cache[config_id] = QuotaInfo(
                    provider=provider,
                    config_id=config_id
                )
            
            quota = self._quota_cache[config_id]
            quota.total_requests += 1
            
            if success:
                quota.successful_requests += 1
            else:
                quota.failed_requests += 1
            
            quota.total_tokens += tokens_used
            quota.last_updated = datetime.utcnow()
    
    async def check_quota_limits(
        self,
        config_id: str,
        threshold_percent: float = 80.0
    ) -> bool:
        """
        Check if quota usage is approaching limits.
        
        Args:
            config_id: Configuration ID
            threshold_percent: Alert threshold percentage (default: 80%)
        
        Returns:
            True if approaching limit, False otherwise
        """
        quota = await self.get_quota_usage(config_id)
        
        if not quota or not quota.quota_limit:
            return False
        
        usage_percent = (quota.total_tokens / quota.quota_limit) * 100
        return usage_percent >= threshold_percent
    
    async def reset_quota_cache(self, config_id: Optional[str] = None) -> None:
        """
        Reset quota cache for a configuration or all configurations.
        
        Args:
            config_id: Configuration ID (optional, resets all if None)
        """
        async with self._lock:
            if config_id:
                self._quota_cache.pop(config_id, None)
                logger.info(f"Reset quota cache for config {config_id}")
            else:
                self._quota_cache.clear()
                logger.info("Reset all quota caches")

    def add_alert_handler(self, handler: Callable[[str, QuotaInfo], None]) -> None:
        """
        Add a callback handler for quota alerts.
        
        Args:
            handler: Callback function that receives (config_id, quota_info)
        
        Validates Requirements: 10.4
        """
        self._alert_handlers.append(handler)
        logger.info(f"Added quota alert handler: {handler.__name__}")
    
    def remove_alert_handler(self, handler: Callable[[str, QuotaInfo], None]) -> None:
        """
        Remove a callback handler for quota alerts.
        
        Args:
            handler: Callback function to remove
        """
        if handler in self._alert_handlers:
            self._alert_handlers.remove(handler)
            logger.info(f"Removed quota alert handler: {handler.__name__}")
    
    async def _trigger_quota_alert(self, config_id: str, quota: QuotaInfo) -> None:
        """
        Trigger quota alert to all registered handlers.
        
        Args:
            config_id: Configuration ID
            quota: Quota information
        
        Validates Requirements: 10.4
        """
        if not quota.quota_limit:
            return
        
        usage_percent = (quota.total_tokens / quota.quota_limit) * 100
        
        # Check if we should send alert (threshold reached and not sent recently)
        should_alert = usage_percent >= quota.alert_threshold_percent
        
        # Prevent alert spam - only send once per hour
        if quota.last_alert_sent:
            time_since_last_alert = datetime.utcnow() - quota.last_alert_sent
            if time_since_last_alert.total_seconds() < 3600:  # 1 hour
                should_alert = False
        
        if should_alert:
            logger.warning(
                f"Quota alert for config {config_id}: {usage_percent:.1f}% used "
                f"({quota.total_tokens}/{quota.quota_limit} tokens)"
            )
            
            # Update last alert time
            quota.last_alert_sent = datetime.utcnow()
            
            # Call all registered handlers
            for handler in self._alert_handlers:
                try:
                    # Support both sync and async handlers
                    if asyncio.iscoroutinefunction(handler):
                        await handler(config_id, quota)
                    else:
                        handler(config_id, quota)
                except Exception as e:
                    logger.error(f"Error in quota alert handler {handler.__name__}: {e}")
    
    async def start_monitoring(self, interval: int = 60) -> None:
        """
        Start background quota monitoring task.
        
        Args:
            interval: Monitoring interval in seconds (default: 60)
        
        Validates Requirements: 10.4
        """
        if self._running:
            logger.warning("Quota monitoring already running")
            return
        
        self._monitoring_interval = interval
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started quota monitoring with {interval}s interval")
    
    async def stop_monitoring(self) -> None:
        """
        Stop background quota monitoring task.
        
        Validates Requirements: 10.4
        """
        if not self._running:
            return
        
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        logger.info("Stopped quota monitoring")
    
    async def _monitoring_loop(self) -> None:
        """
        Background loop for quota monitoring.
        
        Periodically checks all configurations for quota threshold violations
        and triggers alerts when necessary.
        
        Validates Requirements: 10.4
        """
        logger.info("Quota monitoring loop started")
        
        while self._running:
            try:
                await self._check_all_quotas()
                await asyncio.sleep(self._monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in quota monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self._monitoring_interval)
        
        logger.info("Quota monitoring loop stopped")
    
    async def _check_all_quotas(self) -> None:
        """
        Check all quota configurations for threshold violations.
        
        Validates Requirements: 10.4
        """
        async with self._lock:
            configs_to_check = list(self._quota_cache.items())
        
        for config_id, quota in configs_to_check:
            try:
                await self._trigger_quota_alert(config_id, quota)
            except Exception as e:
                logger.error(f"Error checking quota for config {config_id}: {e}")
    
    async def set_quota_limit(
        self,
        config_id: str,
        quota_limit: int,
        alert_threshold_percent: float = 80.0
    ) -> None:
        """
        Set quota limit and alert threshold for a configuration.
        
        Args:
            config_id: Configuration ID
            quota_limit: Maximum quota limit (tokens)
            alert_threshold_percent: Alert threshold percentage (default: 80%)
        
        Validates Requirements: 10.4
        """
        if alert_threshold_percent < 0 or alert_threshold_percent > 100:
            raise ValueError("Alert threshold must be between 0 and 100")
        
        async with self._lock:
            if config_id in self._quota_cache:
                quota = self._quota_cache[config_id]
                quota.quota_limit = quota_limit
                quota.alert_threshold_percent = alert_threshold_percent
                logger.info(
                    f"Updated quota limit for config {config_id}: "
                    f"{quota_limit} tokens, {alert_threshold_percent}% threshold"
                )
            else:
                logger.warning(f"Config {config_id} not found in quota cache")
    
    async def get_quota_status(self, config_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed quota status for a configuration.
        
        Args:
            config_id: Configuration ID
        
        Returns:
            Dictionary with quota status details or None if not found
        
        Validates Requirements: 10.4
        """
        quota = await self.get_quota_usage(config_id)
        
        if not quota:
            return None
        
        status = {
            "config_id": config_id,
            "provider": quota.provider,
            "total_requests": quota.total_requests,
            "successful_requests": quota.successful_requests,
            "failed_requests": quota.failed_requests,
            "total_tokens": quota.total_tokens,
            "quota_limit": quota.quota_limit,
            "quota_remaining": quota.quota_remaining,
            "usage_percent": None,
            "alert_threshold_percent": quota.alert_threshold_percent,
            "alert_triggered": False,
            "reset_at": quota.reset_at.isoformat() if quota.reset_at else None,
            "last_updated": quota.last_updated.isoformat(),
            "last_alert_sent": quota.last_alert_sent.isoformat() if quota.last_alert_sent else None,
        }
        
        if quota.quota_limit:
            usage_percent = (quota.total_tokens / quota.quota_limit) * 100
            status["usage_percent"] = round(usage_percent, 2)
            status["alert_triggered"] = usage_percent >= quota.alert_threshold_percent
            
            if quota.quota_limit > 0:
                status["quota_remaining"] = max(0, quota.quota_limit - quota.total_tokens)
        
        return status
    
    async def get_all_quota_statuses(self) -> List[Dict[str, Any]]:
        """
        Get quota status for all configurations.
        
        Returns:
            List of quota status dictionaries
        
        Validates Requirements: 10.4
        """
        async with self._lock:
            config_ids = list(self._quota_cache.keys())
        
        statuses = []
        for config_id in config_ids:
            status = await self.get_quota_status(config_id)
            if status:
                statuses.append(status)
        
        return statuses
