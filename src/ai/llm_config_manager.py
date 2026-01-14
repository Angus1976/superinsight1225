"""
LLM Configuration Manager for SuperInsight platform.

Manages LLM configuration persistence, caching, and hot reload functionality.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

try:
    from src.ai.llm_schemas import (
        LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig,
        ValidationResult, mask_api_key
    )
    from src.models.llm_configuration import LLMConfiguration, LLMUsageLog
    from src.database.session import get_async_session
except ImportError:
    from ai.llm_schemas import (
        LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig,
        ValidationResult, mask_api_key
    )
    from models.llm_configuration import LLMConfiguration, LLMUsageLog
    from database.session import get_async_session

logger = logging.getLogger(__name__)


class LLMConfigManager:
    """
    LLM Configuration Manager with Redis caching and hot reload support.
    
    Features:
    - CRUD operations for LLM configurations
    - Redis-based caching for fast access
    - Configuration change detection and hot reload
    - Multi-tenant configuration isolation
    - API key masking for security
    """
    
    # Cache key patterns
    CACHE_KEY_CONFIG = "llm:config:{tenant_id}"
    CACHE_KEY_HEALTH = "llm:health:{method}"
    CACHE_KEY_RATE_LIMIT = "llm:rate_limit:{tenant_id}:{method}"
    
    # Cache TTL in seconds
    CONFIG_CACHE_TTL = 300  # 5 minutes
    HEALTH_CACHE_TTL = 60   # 1 minute
    
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        redis_client: Optional[Any] = None,
    ):
        """
        Initialize the LLM Config Manager.
        
        Args:
            db: SQLAlchemy async session
            redis_client: Redis client for caching
        """
        self._db = db
        self._redis = redis_client
        self._config_watchers: List[Callable[[LLMConfig], Awaitable[None]]] = []
        self._local_cache: Dict[str, LLMConfig] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._hot_reload_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def get_db(self) -> AsyncSession:
        """Get database session."""
        if self._db:
            return self._db
        async for session in get_async_session():
            return session
        raise RuntimeError("Failed to get database session")
    
    # ==================== CRUD Operations ====================
    
    async def get_config(
        self,
        tenant_id: Optional[str] = None,
        use_cache: bool = True,
        mask_keys: bool = False,
    ) -> LLMConfig:
        """
        Get LLM configuration for a tenant.
        
        Args:
            tenant_id: Tenant ID (None for global config)
            use_cache: Whether to use cached config
            mask_keys: Whether to mask API keys in response
            
        Returns:
            LLMConfig object
        """
        cache_key = self._get_cache_key(tenant_id)
        
        # Try local cache first
        if use_cache and cache_key in self._local_cache:
            if self._is_cache_valid(cache_key):
                config = self._local_cache[cache_key]
                return self._mask_config(config) if mask_keys else config
        
        # Try Redis cache
        if use_cache and self._redis:
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    config_data = json.loads(cached)
                    config = LLMConfig(**config_data)
                    self._update_local_cache(cache_key, config)
                    return self._mask_config(config) if mask_keys else config
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Load from database
        config = await self._load_from_db(tenant_id)
        
        # Update caches
        await self._update_caches(cache_key, config)
        
        return self._mask_config(config) if mask_keys else config
    
    async def save_config(
        self,
        config: LLMConfig,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> LLMConfig:
        """
        Save LLM configuration.
        
        Args:
            config: LLMConfig to save
            tenant_id: Tenant ID (None for global config)
            user_id: User ID making the change
            name: Configuration name
            description: Configuration description
            
        Returns:
            Saved LLMConfig
        """
        db = await self.get_db()
        cache_key = self._get_cache_key(tenant_id)
        
        # Check for existing config
        existing = await self._get_db_config(db, tenant_id)
        
        config_data = config.model_dump()
        
        if existing:
            # Update existing config
            existing.config_data = config_data
            existing.default_method = config.default_method.value
            existing.updated_at = datetime.utcnow()
            if user_id:
                existing.updated_by = UUID(user_id)
            if name:
                existing.name = name
            if description:
                existing.description = description
            
            await db.commit()
            await db.refresh(existing)
        else:
            # Create new config
            new_config = LLMConfiguration(
                id=uuid4(),
                tenant_id=UUID(tenant_id) if tenant_id else None,
                config_data=config_data,
                default_method=config.default_method.value,
                is_active=True,
                is_default=tenant_id is None,
                name=name,
                description=description,
                created_by=UUID(user_id) if user_id else None,
                updated_by=UUID(user_id) if user_id else None,
            )
            db.add(new_config)
            await db.commit()
        
        # Update caches
        await self._update_caches(cache_key, config)
        
        # Notify watchers
        await self._notify_watchers(config)
        
        logger.info(f"LLM config saved for tenant: {tenant_id}")
        return config
    
    async def delete_config(self, tenant_id: Optional[str] = None) -> bool:
        """
        Delete LLM configuration.
        
        Args:
            tenant_id: Tenant ID (None for global config)
            
        Returns:
            True if deleted, False if not found
        """
        db = await self.get_db()
        cache_key = self._get_cache_key(tenant_id)
        
        stmt = delete(LLMConfiguration).where(
            LLMConfiguration.tenant_id == (UUID(tenant_id) if tenant_id else None)
        )
        result = await db.execute(stmt)
        await db.commit()
        
        # Clear caches
        await self._clear_cache(cache_key)
        
        return result.rowcount > 0
    
    async def validate_config(self, config: LLMConfig) -> ValidationResult:
        """
        Validate LLM configuration.
        
        Args:
            config: LLMConfig to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        
        # Validate default method is enabled
        if config.default_method not in config.enabled_methods:
            errors.append(f"Default method '{config.default_method}' is not in enabled methods")
        
        # Validate local config
        if LLMMethod.LOCAL_OLLAMA in config.enabled_methods:
            if not config.local_config.ollama_url:
                errors.append("Ollama URL is required for local LLM")
        
        # Validate cloud config
        if LLMMethod.CLOUD_OPENAI in config.enabled_methods:
            if not config.cloud_config.openai_api_key:
                errors.append("OpenAI API key is required for cloud LLM")
        
        if LLMMethod.CLOUD_AZURE in config.enabled_methods:
            if not config.cloud_config.azure_api_key:
                errors.append("Azure API key is required")
            if not config.cloud_config.azure_endpoint:
                errors.append("Azure endpoint is required")
        
        # Validate China LLM config
        china_methods = [
            LLMMethod.CHINA_QWEN, LLMMethod.CHINA_ZHIPU,
            LLMMethod.CHINA_BAIDU, LLMMethod.CHINA_HUNYUAN
        ]
        
        for method in china_methods:
            if method in config.enabled_methods:
                if method == LLMMethod.CHINA_QWEN and not config.china_config.qwen_api_key:
                    errors.append("Qwen API key is required")
                elif method == LLMMethod.CHINA_ZHIPU and not config.china_config.zhipu_api_key:
                    errors.append("Zhipu API key is required")
                elif method == LLMMethod.CHINA_BAIDU:
                    if not config.china_config.baidu_api_key:
                        errors.append("Baidu API key is required")
                    if not config.china_config.baidu_secret_key:
                        errors.append("Baidu secret key is required")
                elif method == LLMMethod.CHINA_HUNYUAN:
                    if not config.china_config.hunyuan_secret_id:
                        errors.append("Hunyuan secret ID is required")
                    if not config.china_config.hunyuan_secret_key:
                        errors.append("Hunyuan secret key is required")
        
        # Add warnings for best practices
        if config.local_config.timeout < 10:
            warnings.append("Local timeout is very short, may cause frequent timeouts")
        
        if len(config.enabled_methods) == 0:
            warnings.append("No LLM methods are enabled")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    # ==================== Hot Reload ====================
    
    def watch_config_changes(
        self,
        callback: Callable[[LLMConfig], Awaitable[None]]
    ) -> None:
        """
        Register a callback for configuration changes.
        
        Args:
            callback: Async function to call when config changes
        """
        self._config_watchers.append(callback)
        logger.debug(f"Registered config watcher, total: {len(self._config_watchers)}")
    
    def unwatch_config_changes(
        self,
        callback: Callable[[LLMConfig], Awaitable[None]]
    ) -> None:
        """
        Unregister a configuration change callback.
        
        Args:
            callback: Callback to remove
        """
        if callback in self._config_watchers:
            self._config_watchers.remove(callback)
    
    async def hot_reload(self, tenant_id: Optional[str] = None) -> LLMConfig:
        """
        Force reload configuration from database.
        
        Args:
            tenant_id: Tenant ID to reload
            
        Returns:
            Reloaded LLMConfig
        """
        cache_key = self._get_cache_key(tenant_id)
        
        # Clear caches
        await self._clear_cache(cache_key)
        
        # Reload from database
        config = await self.get_config(tenant_id, use_cache=False)
        
        # Notify watchers
        await self._notify_watchers(config)
        
        logger.info(f"Hot reloaded LLM config for tenant: {tenant_id}")
        return config
    
    async def start_hot_reload_watcher(
        self,
        interval_seconds: float = 1.0,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Start background task to watch for config changes.
        
        Args:
            interval_seconds: Check interval in seconds
            tenant_id: Tenant ID to watch
        """
        if self._running:
            return
        
        self._running = True
        self._hot_reload_task = asyncio.create_task(
            self._watch_loop(interval_seconds, tenant_id)
        )
        logger.info("Started hot reload watcher")
    
    async def stop_hot_reload_watcher(self) -> None:
        """Stop the hot reload watcher."""
        self._running = False
        if self._hot_reload_task:
            self._hot_reload_task.cancel()
            try:
                await self._hot_reload_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped hot reload watcher")
    
    async def _watch_loop(
        self,
        interval: float,
        tenant_id: Optional[str]
    ) -> None:
        """Background loop to check for config changes."""
        last_config: Optional[LLMConfig] = None
        
        while self._running:
            try:
                current_config = await self.get_config(tenant_id, use_cache=False)
                
                if last_config and current_config != last_config:
                    logger.info("Config change detected, notifying watchers")
                    await self._notify_watchers(current_config)
                
                last_config = current_config
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in hot reload watcher: {e}")
                await asyncio.sleep(interval)
    
    # ==================== Usage Logging ====================
    
    async def log_usage(
        self,
        method: str,
        model: str,
        operation: str = "generate",
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log LLM usage for billing and analytics.
        
        Args:
            method: LLM method used
            model: Model name
            operation: Operation type (generate, embed, stream)
            tenant_id: Tenant ID
            user_id: User ID
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            latency_ms: Response latency in milliseconds
            success: Whether the call succeeded
            error_code: Error code if failed
            error_message: Error message if failed
        """
        try:
            db = await self.get_db()
            
            log_entry = LLMUsageLog.create_log(
                method=method,
                model=model,
                operation=operation,
                tenant_id=tenant_id,
                user_id=user_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                success=success,
                error_code=error_code,
                error_message=error_message,
            )
            
            db.add(log_entry)
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log LLM usage: {e}")
    
    # ==================== Private Methods ====================
    
    def _get_cache_key(self, tenant_id: Optional[str]) -> str:
        """Generate cache key for tenant."""
        return self.CACHE_KEY_CONFIG.format(tenant_id=tenant_id or "global")
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if local cache entry is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        age = datetime.utcnow() - self._cache_timestamps[cache_key]
        return age.total_seconds() < self.CONFIG_CACHE_TTL
    
    def _update_local_cache(self, cache_key: str, config: LLMConfig) -> None:
        """Update local cache."""
        self._local_cache[cache_key] = config
        self._cache_timestamps[cache_key] = datetime.utcnow()
    
    async def _update_caches(self, cache_key: str, config: LLMConfig) -> None:
        """Update both local and Redis caches."""
        self._update_local_cache(cache_key, config)
        
        if self._redis:
            try:
                await self._redis.setex(
                    cache_key,
                    self.CONFIG_CACHE_TTL,
                    json.dumps(config.model_dump())
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
    
    async def _clear_cache(self, cache_key: str) -> None:
        """Clear cache entry."""
        if cache_key in self._local_cache:
            del self._local_cache[cache_key]
        if cache_key in self._cache_timestamps:
            del self._cache_timestamps[cache_key]
        
        if self._redis:
            try:
                await self._redis.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis cache delete failed: {e}")
    
    async def _load_from_db(self, tenant_id: Optional[str]) -> LLMConfig:
        """Load configuration from database."""
        db = await self.get_db()
        db_config = await self._get_db_config(db, tenant_id)
        
        if db_config and db_config.config_data:
            return LLMConfig(**db_config.config_data)
        
        # Return default config if not found
        return LLMConfig()
    
    async def _get_db_config(
        self,
        db: AsyncSession,
        tenant_id: Optional[str]
    ) -> Optional[LLMConfiguration]:
        """Get configuration from database."""
        stmt = select(LLMConfiguration).where(
            LLMConfiguration.tenant_id == (UUID(tenant_id) if tenant_id else None),
            LLMConfiguration.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _notify_watchers(self, config: LLMConfig) -> None:
        """Notify all registered watchers of config change."""
        for watcher in self._config_watchers:
            try:
                await watcher(config)
            except Exception as e:
                logger.error(f"Config watcher error: {e}")
    
    def _mask_config(self, config: LLMConfig) -> LLMConfig:
        """Create a copy of config with masked API keys."""
        config_dict = config.model_dump()
        
        # Mask cloud config keys
        if config_dict.get('cloud_config'):
            cloud = config_dict['cloud_config']
            cloud['openai_api_key'] = mask_api_key(cloud.get('openai_api_key'))
            cloud['azure_api_key'] = mask_api_key(cloud.get('azure_api_key'))
        
        # Mask China LLM config keys
        if config_dict.get('china_config'):
            china = config_dict['china_config']
            china['qwen_api_key'] = mask_api_key(china.get('qwen_api_key'))
            china['zhipu_api_key'] = mask_api_key(china.get('zhipu_api_key'))
            china['baidu_api_key'] = mask_api_key(china.get('baidu_api_key'))
            china['baidu_secret_key'] = mask_api_key(china.get('baidu_secret_key'))
            china['hunyuan_secret_id'] = mask_api_key(china.get('hunyuan_secret_id'))
            china['hunyuan_secret_key'] = mask_api_key(china.get('hunyuan_secret_key'))
        
        return LLMConfig(**config_dict)


# Singleton instance for global access
_config_manager: Optional[LLMConfigManager] = None


def get_config_manager(
    db: Optional[AsyncSession] = None,
    redis_client: Optional[Any] = None,
) -> LLMConfigManager:
    """
    Get or create the global LLM Config Manager instance.
    
    Args:
        db: SQLAlchemy async session
        redis_client: Redis client
        
    Returns:
        LLMConfigManager instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = LLMConfigManager(db, redis_client)
    elif db is not None:
        _config_manager._db = db
    elif redis_client is not None:
        _config_manager._redis = redis_client
    
    return _config_manager
