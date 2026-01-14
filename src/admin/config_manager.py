"""
Config Manager for SuperInsight Platform Admin Configuration.

Provides unified configuration management with:
- CRUD operations for all config types
- Automatic history tracking
- Redis caching for performance
- Validation before save

**Feature: admin-configuration**
**Validates: Requirements 2.4, 3.4**
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from uuid import uuid4

from sqlalchemy import select, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.schemas import (
    ConfigType,
    ValidationResult,
    ConnectionTestResult,
    LLMConfigCreate,
    LLMConfigUpdate,
    LLMConfigResponse,
    DBConfigCreate,
    DBConfigUpdate,
    DBConfigResponse,
    ThirdPartyConfigCreate,
    ThirdPartyConfigUpdate,
    ThirdPartyConfigResponse,
)
from src.admin.credential_encryptor import CredentialEncryptor, get_credential_encryptor
from src.admin.config_validator import ConfigValidator, get_config_validator
from src.admin.history_tracker import HistoryTracker, get_history_tracker

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Unified configuration manager.
    
    Manages all configuration types with validation, encryption,
    history tracking, and caching.
    
    **Feature: admin-configuration**
    **Validates: Requirements 2.4, 3.4**
    """
    
    # Cache TTL in seconds
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        cache: Optional[Any] = None,  # Redis client
        encryptor: Optional[CredentialEncryptor] = None,
        validator: Optional[ConfigValidator] = None,
        history_tracker: Optional[HistoryTracker] = None,
    ):
        """
        Initialize the config manager.
        
        Args:
            db: Async database session
            cache: Redis cache client
            encryptor: Credential encryptor
            validator: Config validator
            history_tracker: History tracker
        """
        self._db = db
        self._cache = cache
        self._encryptor = encryptor or get_credential_encryptor()
        self._validator = validator or get_config_validator()
        self._history_tracker = history_tracker or get_history_tracker()
        
        # In-memory storage for testing without database
        self._in_memory_configs: Dict[str, Dict[str, Any]] = {
            ConfigType.LLM.value: {},
            ConfigType.DATABASE.value: {},
            ConfigType.SYNC_STRATEGY.value: {},
            ConfigType.THIRD_PARTY.value: {},
        }
    
    @property
    def db(self) -> Optional[AsyncSession]:
        """Get the database session."""
        return self._db
    
    @db.setter
    def db(self, session: AsyncSession) -> None:
        """Set the database session."""
        self._db = session
        self._history_tracker.db = session
    
    # ========== LLM Configuration ==========
    
    async def get_llm_config(
        self,
        config_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[LLMConfigResponse]:
        """
        Get LLM configuration by ID.
        
        Args:
            config_id: Configuration ID
            tenant_id: Optional tenant ID for multi-tenant
            
        Returns:
            LLMConfigResponse if found, None otherwise
        """
        # Try cache first
        cache_key = f"llm_config:{config_id}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            return LLMConfigResponse(**cached)
        
        if self._db is not None:
            config = await self._get_llm_from_db(config_id, tenant_id)
        else:
            config = self._in_memory_configs[ConfigType.LLM.value].get(config_id)
        
        if config:
            # Mask sensitive fields
            response = self._to_llm_response(config)
            await self._set_cache(cache_key, response.model_dump())
            return response
        
        return None
    
    async def list_llm_configs(
        self,
        tenant_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[LLMConfigResponse]:
        """
        List all LLM configurations.
        
        Args:
            tenant_id: Optional tenant ID filter
            active_only: Only return active configs
            
        Returns:
            List of LLMConfigResponse
        """
        if self._db is not None:
            configs = await self._list_llm_from_db(tenant_id, active_only)
        else:
            configs = list(self._in_memory_configs[ConfigType.LLM.value].values())
            if active_only:
                configs = [c for c in configs if c.get("is_active", True)]
        
        return [self._to_llm_response(c) for c in configs]
    
    async def save_llm_config(
        self,
        config: Union[LLMConfigCreate, LLMConfigUpdate],
        user_id: str,
        user_name: str = "Unknown",
        config_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> LLMConfigResponse:
        """
        Save LLM configuration (create or update).
        
        Args:
            config: Configuration data
            user_id: User making the change
            user_name: User name for history
            config_id: Existing config ID for update
            tenant_id: Tenant ID for multi-tenant
            
        Returns:
            Saved LLMConfigResponse
        """
        # Validate configuration
        validation = self._validator.validate_llm_config(config)
        if not validation.is_valid:
            raise ValueError(f"Invalid LLM config: {validation.errors}")
        
        # Get old value for history and merging
        old_value = None
        existing_config = None
        if config_id:
            if self._db is not None:
                existing_config = await self._get_llm_from_db(config_id, tenant_id)
            else:
                existing_config = self._in_memory_configs[ConfigType.LLM.value].get(config_id)
            
            if existing_config:
                old_value = existing_config.copy()
        
        # Prepare config data
        config_dict = config.model_dump(exclude_unset=True) if hasattr(config, 'model_dump') else config.dict(exclude_unset=True)
        
        # For updates, merge with existing config
        if config_id and existing_config:
            merged_config = existing_config.copy()
            merged_config.update(config_dict)
            config_dict = merged_config
        
        # Encrypt API key if present
        if "api_key" in config_dict and config_dict["api_key"]:
            config_dict["api_key_encrypted"] = self._encryptor.encrypt(config_dict["api_key"])
            del config_dict["api_key"]
        
        # Set timestamps and IDs
        now = datetime.utcnow()
        if config_id:
            config_dict["id"] = config_id
            config_dict["updated_at"] = now
        else:
            config_dict["id"] = str(uuid4())
            config_dict["created_at"] = now
            config_dict["updated_at"] = now
        
        config_dict["tenant_id"] = tenant_id
        
        # Save to storage
        if self._db is not None:
            saved = await self._save_llm_to_db(config_dict, config_id is not None)
        else:
            self._in_memory_configs[ConfigType.LLM.value][config_dict["id"]] = config_dict
            saved = config_dict
        
        # Record history
        await self._history_tracker.record_change(
            config_type=ConfigType.LLM,
            old_value=old_value,
            new_value=config_dict,
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            config_id=config_dict["id"],
        )
        
        # Invalidate cache
        await self._invalidate_cache(f"llm_config:{config_dict['id']}")
        
        return self._to_llm_response(saved)
    
    async def delete_llm_config(
        self,
        config_id: str,
        user_id: str,
        user_name: str = "Unknown",
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        Delete LLM configuration.
        
        Args:
            config_id: Configuration ID to delete
            user_id: User making the change
            user_name: User name for history
            tenant_id: Tenant ID for multi-tenant
            
        Returns:
            True if deleted, False if not found
        """
        # Get old value for history
        existing = await self.get_llm_config(config_id, tenant_id)
        if not existing:
            return False
        
        old_value = existing.model_dump()
        
        # Delete from storage
        if self._db is not None:
            await self._delete_llm_from_db(config_id, tenant_id)
        else:
            if config_id in self._in_memory_configs[ConfigType.LLM.value]:
                del self._in_memory_configs[ConfigType.LLM.value][config_id]
        
        # Record history (new_value indicates deletion)
        await self._history_tracker.record_change(
            config_type=ConfigType.LLM,
            old_value=old_value,
            new_value={"_deleted": True, "id": config_id},
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            config_id=config_id,
        )
        
        # Invalidate cache
        await self._invalidate_cache(f"llm_config:{config_id}")
        
        return True
    
    # ========== Database Configuration ==========
    
    async def get_db_config(
        self,
        config_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[DBConfigResponse]:
        """Get database configuration by ID."""
        cache_key = f"db_config:{config_id}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            return DBConfigResponse(**cached)
        
        if self._db is not None:
            config = await self._get_db_from_db(config_id, tenant_id)
        else:
            config = self._in_memory_configs[ConfigType.DATABASE.value].get(config_id)
        
        if config:
            response = self._to_db_response(config)
            await self._set_cache(cache_key, response.model_dump())
            return response
        
        return None
    
    async def list_db_configs(
        self,
        tenant_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[DBConfigResponse]:
        """List all database configurations."""
        if self._db is not None:
            configs = await self._list_db_from_db(tenant_id, active_only)
        else:
            configs = list(self._in_memory_configs[ConfigType.DATABASE.value].values())
            if active_only:
                configs = [c for c in configs if c.get("is_active", True)]
        
        return [self._to_db_response(c) for c in configs]
    
    async def save_db_config(
        self,
        config: Union[DBConfigCreate, DBConfigUpdate],
        user_id: str,
        user_name: str = "Unknown",
        config_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> DBConfigResponse:
        """Save database configuration (create or update)."""
        # Validate configuration
        validation = self._validator.validate_db_config(config)
        if not validation.is_valid:
            raise ValueError(f"Invalid DB config: {validation.errors}")
        
        # Get old value for history
        old_value = None
        if config_id:
            existing = await self.get_db_config(config_id, tenant_id)
            if existing:
                old_value = existing.model_dump()
        
        # Prepare config data
        config_dict = config.model_dump(exclude_unset=True) if hasattr(config, 'model_dump') else config.dict(exclude_unset=True)
        
        # Encrypt password if present
        if "password" in config_dict and config_dict["password"]:
            config_dict["password_encrypted"] = self._encryptor.encrypt(config_dict["password"])
            del config_dict["password"]
        
        # Set timestamps and IDs
        now = datetime.utcnow()
        if config_id:
            config_dict["id"] = config_id
            config_dict["updated_at"] = now
        else:
            config_dict["id"] = str(uuid4())
            config_dict["created_at"] = now
            config_dict["updated_at"] = now
        
        config_dict["tenant_id"] = tenant_id
        
        # Save to storage
        if self._db is not None:
            saved = await self._save_db_to_db(config_dict, config_id is not None)
        else:
            self._in_memory_configs[ConfigType.DATABASE.value][config_dict["id"]] = config_dict
            saved = config_dict
        
        # Record history
        await self._history_tracker.record_change(
            config_type=ConfigType.DATABASE,
            old_value=old_value,
            new_value=config_dict,
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            config_id=config_dict["id"],
        )
        
        # Invalidate cache
        await self._invalidate_cache(f"db_config:{config_dict['id']}")
        
        return self._to_db_response(saved)
    
    async def delete_db_config(
        self,
        config_id: str,
        user_id: str,
        user_name: str = "Unknown",
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Delete database configuration."""
        existing = await self.get_db_config(config_id, tenant_id)
        if not existing:
            return False
        
        old_value = existing.model_dump()
        
        if self._db is not None:
            await self._delete_db_from_db(config_id, tenant_id)
        else:
            if config_id in self._in_memory_configs[ConfigType.DATABASE.value]:
                del self._in_memory_configs[ConfigType.DATABASE.value][config_id]
        
        await self._history_tracker.record_change(
            config_type=ConfigType.DATABASE,
            old_value=old_value,
            new_value={"_deleted": True, "id": config_id},
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            config_id=config_id,
        )
        
        await self._invalidate_cache(f"db_config:{config_id}")
        
        return True
    
    async def test_db_connection(
        self,
        config_id: str,
        tenant_id: Optional[str] = None,
    ) -> ConnectionTestResult:
        """
        Test database connection.
        
        Args:
            config_id: Database configuration ID
            tenant_id: Tenant ID for multi-tenant
            
        Returns:
            ConnectionTestResult with test status
        """
        config = await self.get_db_config(config_id, tenant_id)
        if not config:
            return ConnectionTestResult(
                success=False,
                latency_ms=0,
                error_message="Configuration not found",
            )
        
        # Get decrypted password
        password = None
        if self._db is not None:
            raw_config = await self._get_db_from_db(config_id, tenant_id)
            if raw_config and raw_config.get("password_encrypted"):
                password = self._encryptor.decrypt(raw_config["password_encrypted"])
        else:
            raw_config = self._in_memory_configs[ConfigType.DATABASE.value].get(config_id)
            if raw_config and raw_config.get("password_encrypted"):
                password = self._encryptor.decrypt(raw_config["password_encrypted"])
        
        # Test connection
        return await self._validator.test_db_connection(config.model_dump(), password)
    
    # ========== Validation ==========
    
    def validate_config(
        self,
        config_type: ConfigType,
        config: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate configuration without saving.
        
        Args:
            config_type: Type of configuration
            config: Configuration data to validate
            
        Returns:
            ValidationResult with validation status
        """
        if config_type == ConfigType.LLM:
            return self._validator.validate_llm_config(config)
        elif config_type == ConfigType.DATABASE:
            return self._validator.validate_db_config(config)
        elif config_type == ConfigType.SYNC_STRATEGY:
            return self._validator.validate_sync_config(config)
        else:
            return ValidationResult(is_valid=True)
    
    # ========== Cache Operations ==========
    
    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache."""
        if self._cache is None:
            return None
        
        try:
            cached = await self._cache.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        
        return None
    
    async def _set_cache(self, key: str, value: Dict[str, Any]) -> None:
        """Set value in cache."""
        if self._cache is None:
            return
        
        try:
            await self._cache.setex(key, self.CACHE_TTL, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
    
    async def _invalidate_cache(self, key: str) -> None:
        """Invalidate cache key."""
        if self._cache is None:
            return
        
        try:
            await self._cache.delete(key)
        except Exception as e:
            logger.warning(f"Cache invalidate failed: {e}")
    
    # ========== Response Converters ==========
    
    def _to_llm_response(self, config: Dict[str, Any]) -> LLMConfigResponse:
        """Convert config dict to LLMConfigResponse."""
        # Mask API key
        api_key_masked = None
        if config.get("api_key_encrypted"):
            try:
                decrypted = self._encryptor.decrypt(config["api_key_encrypted"])
                api_key_masked = self._encryptor.mask(decrypted)
            except Exception:
                api_key_masked = "****"
        
        return LLMConfigResponse(
            id=str(config.get("id", "")),
            name=config.get("name", ""),
            description=config.get("description"),
            llm_type=config.get("llm_type"),
            model_name=config.get("model_name", ""),
            api_endpoint=config.get("api_endpoint"),
            api_key=None,  # Never return actual key
            api_key_masked=api_key_masked,
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 2048),
            timeout_seconds=config.get("timeout_seconds", 60),
            extra_config=config.get("extra_config", {}),
            is_active=config.get("is_active", True),
            is_default=config.get("is_default", False),
            created_at=config.get("created_at", datetime.utcnow()),
            updated_at=config.get("updated_at", datetime.utcnow()),
        )
    
    def _to_db_response(self, config: Dict[str, Any]) -> DBConfigResponse:
        """Convert config dict to DBConfigResponse."""
        # Mask password
        password_masked = None
        if config.get("password_encrypted"):
            try:
                decrypted = self._encryptor.decrypt(config["password_encrypted"])
                password_masked = self._encryptor.mask(decrypted)
            except Exception:
                password_masked = "****"
        
        return DBConfigResponse(
            id=str(config.get("id", "")),
            name=config.get("name", ""),
            description=config.get("description"),
            db_type=config.get("db_type"),
            host=config.get("host", ""),
            port=config.get("port", 5432),
            database=config.get("database", ""),
            username=config.get("username", ""),
            password_masked=password_masked,
            is_readonly=config.get("is_readonly", True),
            ssl_enabled=config.get("ssl_enabled", False),
            extra_config=config.get("extra_config", {}),
            is_active=config.get("is_active", True),
            created_at=config.get("created_at", datetime.utcnow()),
            updated_at=config.get("updated_at", datetime.utcnow()),
        )
    
    # ========== Database Operations (stubs for now) ==========
    
    async def _get_llm_from_db(self, config_id: str, tenant_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get LLM config from database."""
        from src.models.admin_config import AdminConfiguration
        
        conditions = [
            AdminConfiguration.id == config_id,
            AdminConfiguration.config_type == ConfigType.LLM.value,
        ]
        if tenant_id:
            conditions.append(AdminConfiguration.tenant_id == tenant_id)
        
        query = select(AdminConfiguration).where(and_(*conditions))
        result = await self._db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            return {**record.config_data, "id": str(record.id), "tenant_id": str(record.tenant_id) if record.tenant_id else None}
        return None
    
    async def _list_llm_from_db(self, tenant_id: Optional[str], active_only: bool) -> List[Dict[str, Any]]:
        """List LLM configs from database."""
        from src.models.admin_config import AdminConfiguration
        
        conditions = [AdminConfiguration.config_type == ConfigType.LLM.value]
        if tenant_id:
            conditions.append(AdminConfiguration.tenant_id == tenant_id)
        if active_only:
            conditions.append(AdminConfiguration.is_active == True)
        
        query = select(AdminConfiguration).where(and_(*conditions))
        result = await self._db.execute(query)
        records = result.scalars().all()
        
        return [{**r.config_data, "id": str(r.id)} for r in records]
    
    async def _save_llm_to_db(self, config: Dict[str, Any], is_update: bool) -> Dict[str, Any]:
        """Save LLM config to database."""
        from src.models.admin_config import AdminConfiguration
        
        if is_update:
            query = update(AdminConfiguration).where(
                AdminConfiguration.id == config["id"]
            ).values(
                config_data=config,
                updated_at=datetime.utcnow(),
            )
            await self._db.execute(query)
        else:
            record = AdminConfiguration(
                id=config["id"],
                tenant_id=config.get("tenant_id"),
                config_type=ConfigType.LLM.value,
                name=config.get("name"),
                config_data=config,
            )
            self._db.add(record)
        
        await self._db.commit()
        return config
    
    async def _delete_llm_from_db(self, config_id: str, tenant_id: Optional[str]) -> None:
        """Delete LLM config from database."""
        from src.models.admin_config import AdminConfiguration
        
        conditions = [
            AdminConfiguration.id == config_id,
            AdminConfiguration.config_type == ConfigType.LLM.value,
        ]
        if tenant_id:
            conditions.append(AdminConfiguration.tenant_id == tenant_id)
        
        query = delete(AdminConfiguration).where(and_(*conditions))
        await self._db.execute(query)
        await self._db.commit()
    
    async def _get_db_from_db(self, config_id: str, tenant_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get DB config from database."""
        from src.models.admin_config import DatabaseConnection
        
        conditions = [DatabaseConnection.id == config_id]
        if tenant_id:
            conditions.append(DatabaseConnection.tenant_id == tenant_id)
        
        query = select(DatabaseConnection).where(and_(*conditions))
        result = await self._db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            return record.to_dict(mask_password=False)
        return None
    
    async def _list_db_from_db(self, tenant_id: Optional[str], active_only: bool) -> List[Dict[str, Any]]:
        """List DB configs from database."""
        from src.models.admin_config import DatabaseConnection
        
        conditions = []
        if tenant_id:
            conditions.append(DatabaseConnection.tenant_id == tenant_id)
        if active_only:
            conditions.append(DatabaseConnection.is_active == True)
        
        query = select(DatabaseConnection)
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self._db.execute(query)
        records = result.scalars().all()
        
        return [r.to_dict(mask_password=False) for r in records]
    
    async def _save_db_to_db(self, config: Dict[str, Any], is_update: bool) -> Dict[str, Any]:
        """Save DB config to database."""
        from src.models.admin_config import DatabaseConnection
        
        if is_update:
            query = update(DatabaseConnection).where(
                DatabaseConnection.id == config["id"]
            ).values(**{k: v for k, v in config.items() if k != "id"})
            await self._db.execute(query)
        else:
            record = DatabaseConnection(**config)
            self._db.add(record)
        
        await self._db.commit()
        return config
    
    async def _delete_db_from_db(self, config_id: str, tenant_id: Optional[str]) -> None:
        """Delete DB config from database."""
        from src.models.admin_config import DatabaseConnection
        
        conditions = [DatabaseConnection.id == config_id]
        if tenant_id:
            conditions.append(DatabaseConnection.tenant_id == tenant_id)
        
        query = delete(DatabaseConnection).where(and_(*conditions))
        await self._db.execute(query)
        await self._db.commit()
    
    def clear_in_memory_storage(self) -> None:
        """Clear in-memory storage (for testing)."""
        for key in self._in_memory_configs:
            self._in_memory_configs[key].clear()
        self._history_tracker.clear_in_memory_history()


# Global manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
