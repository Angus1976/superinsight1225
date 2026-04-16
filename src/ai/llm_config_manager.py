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
from sqlalchemy import select, update, delete, or_
from sqlalchemy.orm import Session, selectinload

try:
    from src.ai.llm_schemas import (
        LLMConfig,
        LLMMethod,
        LocalConfig,
        CloudConfig,
        ChinaLLMConfig,
        ValidationResult,
        mask_api_key,
        extra_headers_from_llm_config_data,
    )
    from src.models.llm_configuration import LLMConfiguration, LLMUsageLog
    from src.ai.llm_env_merge import merge_llm_config_with_env_defaults
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from ai.llm_schemas import (
        LLMConfig,
        LLMMethod,
        LocalConfig,
        CloudConfig,
        ChinaLLMConfig,
        ValidationResult,
        mask_api_key,
        extra_headers_from_llm_config_data,
    )
    from models.llm_configuration import LLMConfiguration, LLMUsageLog
    from ai.llm_env_merge import merge_llm_config_with_env_defaults

# Async session is optional - only needed if using database persistence
get_async_session = None
try:
    from src.database.connection import get_db as get_async_session
except ImportError:
    try:
        from database.connection import get_db as get_async_session
    except ImportError:
        pass  # Database not available, will use in-memory config only

logger = logging.getLogger(__name__)


def _looks_like_full_llm_config_dump(data: Dict[str, Any]) -> bool:
    """``config_data`` 已存成完整 ``LLMConfig.model_dump()`` 形态。"""
    if not isinstance(data, dict) or not data:
        return False
    if "default_method" not in data:
        return False
    return any(k in data for k in ("local_config", "cloud_config", "china_config"))


def _provider_str_to_method(provider: str) -> Optional[LLMMethod]:
    """与 ``LLMSwitcher._provider_to_method`` 保持一致。"""
    if not provider:
        return None
    p = provider.strip().lower()
    mapping = {
        "ollama": LLMMethod.LOCAL_OLLAMA,
        "local_ollama": LLMMethod.LOCAL_OLLAMA,
        "openai": LLMMethod.CLOUD_OPENAI,
        "cloud_openai": LLMMethod.CLOUD_OPENAI,
        "deepseek": LLMMethod.CLOUD_OPENAI,
        "azure": LLMMethod.CLOUD_AZURE,
        "cloud_azure": LLMMethod.CLOUD_AZURE,
        "china_qwen": LLMMethod.CHINA_QWEN,
        "china_zhipu": LLMMethod.CHINA_ZHIPU,
        "china_baidu": LLMMethod.CHINA_BAIDU,
        "baidu": LLMMethod.CHINA_BAIDU,
        "baidu_qianfan": LLMMethod.CLOUD_OPENAI,
        "china_hunyuan": LLMMethod.CHINA_HUNYUAN,
    }
    return mapping.get(p)


def configuration_row_to_llm_config(row: LLMConfiguration) -> LLMConfig:
    """
    将 ``llm_configurations`` 行转为 ``LLMConfig``（支持管理端写入的扁平 config_data）。

    供异步 ``get_config_by_id`` 与 **同步 Session（OpenClaw 网关路由）** 共用。
    """
    data = row.config_data or {}
    if _looks_like_full_llm_config_dump(data):
        try:
            return LLMConfig.model_validate(data)
        except Exception as e:
            logger.warning(
                "LLMConfig.model_validate failed for row %s, trying API-shaped parse: %s",
                row.id,
                e,
            )

    try:
        from src.ai.encryption_service import get_encryption_service
    except ImportError:
        from ai.encryption_service import get_encryption_service  # type: ignore

    enc = get_encryption_service()
    config_data = dict(data) if isinstance(data, dict) else {}
    prov = (row.provider or config_data.get("provider") or row.default_method or "").strip()
    method = _provider_str_to_method(prov)
    if not method:
        raise ValueError(f"Unknown LLM provider string: {prov!r}")

    timeout = 60
    max_retries = 3

    if method == LLMMethod.LOCAL_OLLAMA:
        base_url = config_data.get("base_url", "http://localhost:11434")
        ollama_url = base_url.rstrip("/").removesuffix("/v1")
        return LLMConfig(
            default_method=method,
            local_config=LocalConfig(
                ollama_url=ollama_url,
                default_model=config_data.get("model_name", "qwen2.5:7b"),
                timeout=timeout,
                max_retries=max_retries,
            ),
            enabled_methods=[method],
        )

    if method not in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
        raise ValueError(
            f"LLM row {row.id} provider {prov!r} maps to {method}; "
            "use full LLMConfig JSON in config_data or an OpenAI-compatible provider row."
        )

    api_key = ""
    enc_blob = config_data.get("api_key_encrypted")
    if enc_blob:
        try:
            api_key = enc.decrypt(enc_blob)
        except Exception as e:
            logger.warning("API key decrypt failed for LLM row %s: %s", row.id, e)
            api_key = config_data.get("api_key", "")
    else:
        api_key = config_data.get("api_key", "")

    if not api_key and "ollama" in (config_data.get("base_url") or "").lower():
        api_key = "ollama"
    if not api_key:
        raise ValueError(f"No API key for LLM configuration {row.id}")

    cloud_config = CloudConfig(
        openai_api_key=api_key,
        openai_base_url=config_data.get("base_url", "https://api.openai.com/v1"),
        openai_model=config_data.get("model_name", "gpt-3.5-turbo"),
        timeout=timeout,
        max_retries=max_retries,
        extra_headers=extra_headers_from_llm_config_data(config_data),
    )
    return LLMConfig(
        default_method=method,
        cloud_config=cloud_config,
        enabled_methods=[method],
    )


def resolve_llm_config_for_openclaw_sync(
    db: Session,
    tenant_id: str,
    llm_configuration_id: Optional[str],
) -> LLMConfig:
    """
    使用 **同步** ``Session`` 解析网关所需的 ``LLMConfig``。

    OpenClaw 桥接使用的全局 ``LLMConfigManager`` 往往未注入 ``AsyncSession``，
    ``get_config_by_id`` 会退化为空配置 → 环境变量始终为本地 Ollama；网关 API 必须走此路径。

    当 ``llm_configuration_id`` 为空时，优先采用 LLM 应用 ``openclaw`` 的绑定（priority 最小），
    再回退到租户单条 ``llm_configurations`` 行（与历史行为兼容）。
    """
    if llm_configuration_id:
        try:
            uid = UUID(llm_configuration_id)
        except ValueError as e:
            raise ValueError(f"Invalid LLM configuration id: {llm_configuration_id}") from e
        stmt = select(LLMConfiguration).where(
            LLMConfiguration.id == uid,
            LLMConfiguration.is_active == True,  # noqa: E712
        )
        stmt = stmt.where(
            or_(
                LLMConfiguration.tenant_id == tenant_id,
                LLMConfiguration.tenant_id.is_(None),
            )
        )
        row = db.execute(stmt).scalar_one_or_none()
        if not row or not row.config_data:
            raise ValueError(f"LLM configuration not found for id={llm_configuration_id}")
        cfg = configuration_row_to_llm_config(row)
    else:
        # 未固定配置行时：优先使用 LLM 应用「openclaw」的绑定（与网关/OpenClaw 通道对齐）
        from src.ai.llm_application_channels import get_openclaw_primary_llm_configuration_row

        oc_row = get_openclaw_primary_llm_configuration_row(db, tenant_id)
        if oc_row and oc_row.config_data:
            cfg = configuration_row_to_llm_config(oc_row)
        else:
            stmt = select(LLMConfiguration).where(
                LLMConfiguration.tenant_id == (tenant_id if tenant_id else None),
                LLMConfiguration.is_active == True,  # noqa: E712
            )
            row = db.execute(stmt).scalar_one_or_none()
            if not row or not row.config_data:
                cfg = LLMConfig()
            else:
                cfg = configuration_row_to_llm_config(row)
    return merge_llm_config_with_env_defaults(cfg)


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
    
    async def get_db(self) -> Optional[AsyncSession]:
        """Get database session. Returns None if database not available."""
        if self._db:
            return self._db
        # Database persistence not available - will use in-memory config only
        return None
    
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
        
        # Load from database, then fill missing optional fields from environment
        config = await self._load_from_db(tenant_id)
        config = merge_llm_config_with_env_defaults(config)

        # Update caches
        await self._update_caches(cache_key, config)
        
        return self._mask_config(config) if mask_keys else config

    async def get_config_by_id(
        self,
        tenant_id: Optional[str],
        config_id: str,
        mask_keys: bool = False,
    ) -> LLMConfig:
        """
        Load a specific ``llm_configurations`` row by UUID.

        Used when an OpenClaw gateway (or other consumer) pins to one platform
        LLM row instead of the tenant's single active default.
        """
        db = await self.get_db()
        if db is None:
            return LLMConfig()

        try:
            uid = UUID(config_id)
        except ValueError as e:
            raise ValueError(f"Invalid LLM configuration id: {config_id}") from e

        stmt = select(LLMConfiguration).where(
            LLMConfiguration.id == uid,
            LLMConfiguration.is_active == True,  # noqa: E712
        )
        if tenant_id:
            stmt = stmt.where(
                or_(
                    LLMConfiguration.tenant_id == tenant_id,
                    LLMConfiguration.tenant_id.is_(None),
                )
            )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if not row or not row.config_data:
            raise ValueError(f"LLM configuration not found for id={config_id}")

        config = configuration_row_to_llm_config(row)
        config = merge_llm_config_with_env_defaults(config)
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
        if db is None:
            # Database not available, only update cache
            cache_key = self._get_cache_key(tenant_id)
            self._local_cache[cache_key] = config
            self._cache_timestamps[cache_key] = datetime.utcnow()
            if self._redis:
                try:
                    await self._redis.set(
                        cache_key,
                        config.model_dump_json(),
                        ex=self._cache_ttl
                    )
                except Exception as e:
                    logger.warning(f"Failed to update Redis cache: {e}")
            return config
        
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
                tenant_id=tenant_id if tenant_id else None,
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
        if db is None:
            # Database not available, only clear cache
            cache_key = self._get_cache_key(tenant_id)
            await self._clear_cache(cache_key)
            return True
        
        cache_key = self._get_cache_key(tenant_id)
        
        stmt = delete(LLMConfiguration).where(
            LLMConfiguration.tenant_id == (tenant_id if tenant_id else None)
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
            if db is None:
                # Database not available, skip logging
                logger.debug("Skipping usage logging - database not available")
                return
            
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
        if db is None:
            # Database not available, return default config
            return LLMConfig()
        
        db_config = await self._get_db_config(db, tenant_id)
        
        if db_config and db_config.config_data:
            try:
                return configuration_row_to_llm_config(db_config)
            except Exception as e:
                logger.warning(
                    "Failed to parse LLM configuration row for tenant %s: %s",
                    tenant_id,
                    e,
                )
                return LLMConfig()
        
        # Return default config if not found
        return LLMConfig()
    
    async def _get_db_config(
        self,
        db: AsyncSession,
        tenant_id: Optional[str]
    ) -> Optional[LLMConfiguration]:
        """Get configuration from database."""
        stmt = select(LLMConfiguration).where(
            LLMConfiguration.tenant_id == (tenant_id if tenant_id else None),
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
