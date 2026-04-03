"""
Application LLM Manager for SuperInsight platform.

Central service for LLM configuration management with priority-based failover,
hot reload, and multi-tenant support.
"""

import os
import asyncio
import logging
from typing import List, Optional, Callable, Awaitable, TypeVar, Union
from fnmatch import fnmatch
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from src.ai.llm_schemas import CloudConfig
from src.ai.encryption_service import EncryptionService
from src.ai.cache_manager import CacheManager
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding

logger = logging.getLogger(__name__)

T = TypeVar('T')


def _coerce_uuid(value: Optional[str]) -> Optional[UUID]:
    """Bind UUID columns consistently (SQLite + Postgres) when tenant_id is passed as str."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class ApplicationLLMManager:
    """
    Central service for LLM configuration management and failover.
    
    Features:
    - Priority-based configuration loading (app → tenant → global → env)
    - Automatic failover with retry and timeout
    - Two-tier caching with hot reload
    - Multi-tenant isolation
    """
    
    def __init__(
        self,
        db_session: Union[AsyncSession, Session],
        cache_manager: CacheManager,
        encryption_service: EncryptionService
    ):
        """
        Initialize the ApplicationLLMManager.
        
        Args:
            db_session: Async or sync SQLAlchemy session (integration tests use sync Session).
            cache_manager: Cache manager instance.
            encryption_service: Encryption service for API keys.
        """
        self.db = db_session
        self.cache = cache_manager
        self.encryption = encryption_service
    
    async def get_llm_config(
        self,
        application_code: str,
        tenant_id: Optional[str] = None
    ) -> List[CloudConfig]:
        """
        Retrieve LLM configurations for an application, ordered by priority.
        
        Priority order:
        1. Application-specific bindings (highest priority)
        2. Tenant-level configurations
        3. Global default configurations
        4. Environment variables (fallback)
        
        Args:
            application_code: Application code (e.g., "structuring").
            tenant_id: Optional tenant ID for multi-tenant isolation.
        
        Returns:
            List of CloudConfig objects ordered by priority (ascending).
        """
        # Build cache key
        cache_key = self._build_cache_key(application_code, tenant_id)
        
        # Try cache first
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for {cache_key}")
            return [CloudConfig(**cfg) for cfg in cached]
        
        # Load from database
        configs = await self._load_from_database(application_code, tenant_id)
        
        # Fallback to environment variables if no database configs
        if not configs:
            env_config = self._load_from_env()
            if env_config:
                configs = [env_config]
        
        # Cache the result
        if configs:
            await self.cache.set(cache_key, [cfg.model_dump() for cfg in configs])
        
        return configs
    
    async def execute_with_failover(
        self,
        application_code: str,
        operation: Callable[[CloudConfig], Awaitable[T]],
        tenant_id: Optional[str] = None
    ) -> T:
        """
        Execute an operation with automatic failover across LLM configurations.
        
        Retry logic:
        - Retry each LLM up to max_retries times with exponential backoff
        - On timeout or failure, move to next LLM in priority order
        - Log all failover events
        - Raise exception if all LLMs fail
        
        Args:
            application_code: Application code.
            operation: Async function that takes CloudConfig and returns result.
            tenant_id: Optional tenant ID.
        
        Returns:
            Result from the operation.
        
        Raises:
            RuntimeError: If all LLMs fail.
        """
        configs = await self.get_llm_config(application_code, tenant_id)
        
        if not configs:
            raise RuntimeError(
                f"No LLM configuration found for application '{application_code}'"
            )
        
        # Get bindings for retry/timeout settings
        bindings = await self._get_bindings(application_code, tenant_id)
        
        last_error = None
        for idx, config in enumerate(configs):
            # Get binding settings (default if not found)
            binding = bindings[idx] if idx < len(bindings) else None
            max_retries = binding.max_retries if binding else 3
            timeout_seconds = binding.timeout_seconds if binding else 30
            
            try:
                result = await self._execute_with_retry(
                    config,
                    operation,
                    max_retries,
                    timeout_seconds
                )
                
                # Log success
                logger.info(
                    f"LLM request succeeded for {application_code} "
                    f"(provider: {config.openai_base_url}, priority: {idx + 1})"
                )
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM failover triggered for {application_code} "
                    f"(provider: {config.openai_base_url}, priority: {idx + 1}): {e}"
                )
                
                # Continue to next LLM
                continue
        
        # All LLMs failed
        raise RuntimeError(
            f"All LLMs failed for application '{application_code}': {last_error}"
        )
    
    async def invalidate_cache(
        self,
        application_code: Optional[str] = None,
        broadcast: bool = True
    ) -> None:
        """
        Invalidate configuration cache.
        
        Args:
            application_code: If provided, invalidate only this application's cache.
            broadcast: If True and Redis available, broadcast invalidation to other instances.
        """
        if application_code:
            pattern = f"llm:config:{application_code}:*"
        else:
            pattern = "llm:config:*"
        
        await self.cache.invalidate(pattern, broadcast=broadcast)
        logger.info(f"Invalidated cache for pattern: {pattern}")
    
    # Private methods
    
    def _build_cache_key(self, application_code: str, tenant_id: Optional[str]) -> str:
        """Build cache key for configuration."""
        if tenant_id:
            return f"llm:config:{application_code}:{tenant_id}"
        return f"llm:config:{application_code}:global"

    async def _execute(self, stmt):
        """Run execute on async or sync session (integration tests use sync Session)."""
        if isinstance(self.db, AsyncSession):
            return await self.db.execute(stmt)
        return self.db.execute(stmt)
    
    async def _load_from_database(
        self,
        application_code: str,
        tenant_id: Optional[str]
    ) -> List[CloudConfig]:
        """Load configurations from database with hierarchy resolution."""
        # Step 1: Get application
        stmt = select(LLMApplication).where(LLMApplication.code == application_code)
        result = await self._execute(stmt)
        app = result.scalar_one_or_none()
        
        if not app:
            logger.debug(f"Application not found: {application_code}")
            return []
        
        # Step 2: Get bindings ordered by priority
        stmt = (
            select(LLMApplicationBinding)
            .options(selectinload(LLMApplicationBinding.llm_config))
            .where(
                LLMApplicationBinding.application_id == app.id,
                LLMApplicationBinding.is_active == True
            )
            .join(LLMConfiguration)
            .where(LLMConfiguration.is_active == True)
            .order_by(LLMApplicationBinding.priority.asc())
        )
        
        # Step 3: Tenant scope merges tenant-scoped configs with global (tenant_id NULL)
        # so failover lists stay ordered by binding priority across both (Req. 18.8).
        if tenant_id:
            tid = _coerce_uuid(tenant_id)
            merged_stmt = stmt.where(
                or_(
                    LLMConfiguration.tenant_id == tid,
                    LLMConfiguration.tenant_id.is_(None),
                )
            )
            result = await self._execute(merged_stmt)
            bindings = result.scalars().all()
            return [self._to_cloud_config(b.llm_config) for b in bindings]
        
        # Step 4: No tenant context — only global configurations
        global_stmt = stmt.where(LLMConfiguration.tenant_id.is_(None))
        result = await self._execute(global_stmt)
        global_bindings = result.scalars().all()
        
        return [self._to_cloud_config(b.llm_config) for b in global_bindings]
    
    async def _get_bindings(
        self,
        application_code: str,
        tenant_id: Optional[str]
    ) -> List[LLMApplicationBinding]:
        """Get bindings for retry/timeout settings."""
        stmt = select(LLMApplication).where(LLMApplication.code == application_code)
        result = await self._execute(stmt)
        app = result.scalar_one_or_none()
        
        if not app:
            return []
        
        stmt = (
            select(LLMApplicationBinding)
            .where(
                LLMApplicationBinding.application_id == app.id,
                LLMApplicationBinding.is_active == True
            )
            .join(LLMConfiguration)
            .where(LLMConfiguration.is_active == True)
            .order_by(LLMApplicationBinding.priority.asc())
        )
        
        if tenant_id:
            tid = _coerce_uuid(tenant_id)
            merged_stmt = stmt.where(
                or_(
                    LLMConfiguration.tenant_id == tid,
                    LLMConfiguration.tenant_id.is_(None),
                )
            )
            result = await self._execute(merged_stmt)
            return result.scalars().all()
        
        global_stmt = stmt.where(LLMConfiguration.tenant_id.is_(None))
        result = await self._execute(global_stmt)
        return result.scalars().all()
    
    def _to_cloud_config(self, llm_config: LLMConfiguration) -> CloudConfig:
        """Convert LLMConfiguration to CloudConfig with decryption."""
        # Decrypt API key from config_data
        config_data = llm_config.config_data or {}
        api_key_encrypted = config_data.get("api_key_encrypted")
        
        if api_key_encrypted:
            api_key = self.encryption.decrypt(api_key_encrypted)
        else:
            api_key = config_data.get("api_key", "")
        
        # Extract provider-specific fields
        provider = config_data.get("provider", llm_config.default_method)
        base_url = config_data.get("base_url", "https://api.openai.com/v1")
        model_name = config_data.get("model_name", "gpt-3.5-turbo")
        
        return CloudConfig(
            openai_api_key=api_key,
            openai_base_url=base_url,
            openai_model=model_name,
        )
    
    def _load_from_env(self) -> Optional[CloudConfig]:
        """Fallback to environment variables for backward compatibility."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Check for Ollama
            base_url = os.getenv("OPENAI_BASE_URL", "")
            if "ollama" in base_url.lower():
                api_key = "ollama"
            else:
                return None
        
        return CloudConfig(
            openai_api_key=api_key,
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        )
    
    async def _execute_with_retry(
        self,
        config: CloudConfig,
        operation: Callable[[CloudConfig], Awaitable[T]],
        max_retries: int,
        timeout_seconds: int
    ) -> T:
        """Execute operation with retry and timeout."""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    operation(config),
                    timeout=timeout_seconds
                )
                return result
                
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"LLM request timeout (attempt {attempt + 1}/{max_retries + 1})",
                    extra={"config": config.openai_model, "timeout": timeout_seconds}
                )
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM request failed (attempt {attempt + 1}/{max_retries + 1}): {e}",
                    extra={"config": config.openai_model}
                )
            
            # Exponential backoff
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
        
        raise last_error


# Global singleton instance
_app_llm_manager: Optional[ApplicationLLMManager] = None


def get_app_llm_manager(
    db_session: Union[AsyncSession, Session],
    cache_manager: Optional[CacheManager] = None,
    encryption_service: Optional[EncryptionService] = None
) -> ApplicationLLMManager:
    """
    Get or create the global ApplicationLLMManager instance.
    
    Args:
        db_session: Async database session.
        cache_manager: Optional cache manager.
        encryption_service: Optional encryption service.
    
    Returns:
        ApplicationLLMManager instance.
    """
    global _app_llm_manager
    
    if _app_llm_manager is None:
        from src.ai.cache_manager import get_cache_manager
        from src.ai.encryption_service import get_encryption_service
        
        cache_manager = cache_manager or get_cache_manager()
        encryption_service = encryption_service or get_encryption_service()
        
        _app_llm_manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption_service
        )
    
    return _app_llm_manager
