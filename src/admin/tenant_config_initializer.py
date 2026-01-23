"""
Tenant Configuration Initializer for SuperInsight Platform.

Provides default configuration templates for new tenants with support for
configuration inheritance from global defaults.

This module implements Property 22: Tenant Default Initialization
- Creates default LLM configuration templates for new tenants
- Creates default database configuration templates
- Creates default sync strategy templates
- Supports configuration inheritance from global defaults
- Allows tenants to override global defaults

**Feature: admin-configuration**
**Validates: Requirements 7.4, 7.5**
**Property 22: Tenant Default Initialization**
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4, UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.schemas import (
    ConfigType,
    LLMType,
    DatabaseType,
    SyncMode,
)
from src.models.admin_config import (
    AdminConfiguration,
    DatabaseConnection,
    SyncStrategy,
)


logger = logging.getLogger(__name__)


# ============== Default Configuration Templates ==============

class DefaultTemplates:
    """
    Default configuration templates for new tenants.
    
    These templates provide sensible defaults that can be overridden
    by tenant-specific configurations.
    """
    
    # Default LLM configurations
    LLM_TEMPLATES = [
        {
            "name": "Default Local Ollama",
            "description": "Default local Ollama LLM configuration",
            "llm_type": LLMType.LOCAL_OLLAMA.value,
            "model_name": "llama2",
            "api_endpoint": "http://localhost:11434",
            "temperature": 0.7,
            "max_tokens": 2048,
            "timeout_seconds": 60,
            "is_default": True,
            "extra_config": {
                "num_ctx": 2048,
                "num_predict": 512,
            }
        },
        {
            "name": "Default OpenAI GPT-4",
            "description": "Default OpenAI GPT-4 configuration (requires API key)",
            "llm_type": LLMType.OPENAI.value,
            "model_name": "gpt-4",
            "api_endpoint": "https://api.openai.com/v1",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout_seconds": 120,
            "is_default": False,
            "extra_config": {
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            }
        },
        {
            "name": "Default Qianwen",
            "description": "Default Alibaba Qianwen configuration (requires API key)",
            "llm_type": LLMType.QIANWEN.value,
            "model_name": "qwen-turbo",
            "api_endpoint": "https://dashscope.aliyuncs.com/api/v1",
            "temperature": 0.7,
            "max_tokens": 2048,
            "timeout_seconds": 90,
            "is_default": False,
            "extra_config": {
                "top_p": 0.8,
                "enable_search": False,
            }
        },
    ]
    
    # Default database connection templates
    DATABASE_TEMPLATES = [
        {
            "name": "Default PostgreSQL Connection",
            "description": "Template for PostgreSQL database connection",
            "db_type": DatabaseType.POSTGRESQL.value,
            "host": "localhost",
            "port": 5432,
            "database": "your_database",
            "username": "your_username",
            "is_readonly": True,
            "ssl_enabled": False,
            "extra_config": {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
            }
        },
        {
            "name": "Default MySQL Connection",
            "description": "Template for MySQL database connection",
            "db_type": DatabaseType.MYSQL.value,
            "host": "localhost",
            "port": 3306,
            "database": "your_database",
            "username": "your_username",
            "is_readonly": True,
            "ssl_enabled": False,
            "extra_config": {
                "charset": "utf8mb4",
                "pool_size": 5,
                "max_overflow": 10,
            }
        },
    ]
    
    # Default sync strategy templates
    SYNC_STRATEGY_TEMPLATES = [
        {
            "name": "Default Full Sync Strategy",
            "mode": SyncMode.FULL.value,
            "schedule": "0 2 * * *",  # Daily at 2 AM
            "batch_size": 1000,
            "enabled": False,  # Disabled by default until configured
            "filter_conditions": [],
        },
        {
            "name": "Default Incremental Sync Strategy",
            "mode": SyncMode.INCREMENTAL.value,
            "incremental_field": "updated_at",
            "schedule": "0 * * * *",  # Hourly
            "batch_size": 500,
            "enabled": False,  # Disabled by default until configured
            "filter_conditions": [],
        },
    ]


# ============== Tenant Configuration Initializer ==============

class TenantConfigInitializer:
    """
    Initializes default configurations for new tenants.
    
    Features:
    - Creates default LLM configurations from templates
    - Creates default database connection templates
    - Creates default sync strategy templates
    - Supports configuration inheritance from global defaults
    - Allows tenant-specific overrides
    - Uses async-first architecture with asyncio.Lock
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.4, 7.5**
    **Property 22: Tenant Default Initialization**
    """
    
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
    ):
        """
        Initialize the tenant config initializer.
        
        Args:
            db: Async database session
        """
        self._db = db
        self._lock = asyncio.Lock()  # Async lock for thread-safe operations
        logger.info("TenantConfigInitializer initialized")
    
    @property
    def db(self) -> Optional[AsyncSession]:
        """Get the database session."""
        return self._db
    
    @db.setter
    def db(self, session: AsyncSession) -> None:
        """Set the database session."""
        self._db = session
    
    async def initialize_tenant_defaults(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        include_llm: bool = True,
        include_database: bool = True,
        include_sync: bool = True,
        inherit_global: bool = True,
    ) -> Dict[str, Any]:
        """
        Initialize default configurations for a new tenant.
        
        This method creates default configuration templates for:
        - LLM providers (Ollama, OpenAI, Qianwen)
        - Database connections (PostgreSQL, MySQL)
        - Sync strategies (Full, Incremental)
        
        Args:
            tenant_id: Tenant ID to initialize
            user_id: User ID creating the tenant (optional)
            include_llm: Create default LLM configurations
            include_database: Create default database templates
            include_sync: Create default sync strategy templates
            inherit_global: Inherit from global defaults if available
        
        Returns:
            Dictionary with initialization results:
            {
                "tenant_id": str,
                "llm_configs": List[str],  # Created config IDs
                "db_configs": List[str],   # Created config IDs
                "sync_strategies": List[str],  # Created strategy IDs
                "inherited_from_global": bool,
                "created_at": datetime
            }
        
        **Feature: admin-configuration**
        **Validates: Requirements 7.4, 7.5**
        **Property 22: Tenant Default Initialization**
        """
        async with self._lock:
            logger.info(f"Initializing default configurations for tenant {tenant_id}")
            
            if self._db is None:
                raise ValueError("Database session is required for tenant initialization")
            
            result = {
                "tenant_id": tenant_id,
                "llm_configs": [],
                "db_configs": [],
                "sync_strategies": [],
                "inherited_from_global": False,
                "created_at": datetime.utcnow(),
            }
            
            try:
                # Check for global defaults (tenant_id = None)
                global_defaults = None
                if inherit_global:
                    global_defaults = await self._get_global_defaults()
                    if global_defaults:
                        result["inherited_from_global"] = True
                        logger.info(f"Found {len(global_defaults)} global default configurations")
                
                # Create LLM configurations
                if include_llm:
                    llm_ids = await self._create_llm_configs(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        global_defaults=global_defaults,
                    )
                    result["llm_configs"] = llm_ids
                    logger.info(f"Created {len(llm_ids)} LLM configurations for tenant {tenant_id}")
                
                # Create database connection templates
                if include_database:
                    db_ids = await self._create_db_configs(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        global_defaults=global_defaults,
                    )
                    result["db_configs"] = db_ids
                    logger.info(f"Created {len(db_ids)} database templates for tenant {tenant_id}")
                
                # Create sync strategy templates
                if include_sync:
                    sync_ids = await self._create_sync_strategies(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        db_config_ids=result["db_configs"],
                        global_defaults=global_defaults,
                    )
                    result["sync_strategies"] = sync_ids
                    logger.info(f"Created {len(sync_ids)} sync strategies for tenant {tenant_id}")
                
                # Commit all changes
                await self._db.commit()
                
                logger.info(
                    f"Successfully initialized tenant {tenant_id}: "
                    f"{len(result['llm_configs'])} LLM configs, "
                    f"{len(result['db_configs'])} DB configs, "
                    f"{len(result['sync_strategies'])} sync strategies"
                )
                
                return result
            
            except Exception as e:
                logger.error(f"Failed to initialize tenant {tenant_id}: {e}", exc_info=True)
                await self._db.rollback()
                raise
    
    async def _get_global_defaults(self) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        Get global default configurations (tenant_id = None).
        
        Returns:
            Dictionary with global defaults by config type, or None if no globals exist
        
        **Feature: admin-configuration**
        **Validates: Requirements 7.5**
        """
        try:
            # Query global LLM configurations
            llm_query = select(AdminConfiguration).where(
                and_(
                    AdminConfiguration.tenant_id.is_(None),
                    AdminConfiguration.config_type == ConfigType.LLM.value,
                    AdminConfiguration.is_default == True,
                )
            )
            llm_result = await self._db.execute(llm_query)
            llm_configs = llm_result.scalars().all()
            
            # Query global database configurations
            db_query = select(DatabaseConnection).where(
                and_(
                    DatabaseConnection.tenant_id.is_(None),
                )
            )
            db_result = await self._db.execute(db_query)
            db_configs = db_result.scalars().all()
            
            # Query global sync strategies
            sync_query = select(SyncStrategy).where(
                and_(
                    SyncStrategy.tenant_id.is_(None),
                )
            )
            sync_result = await self._db.execute(sync_query)
            sync_configs = sync_result.scalars().all()
            
            if not llm_configs and not db_configs and not sync_configs:
                return None
            
            return {
                "llm": [config.to_dict() for config in llm_configs],
                "database": [config.to_dict(mask_password=False) for config in db_configs],
                "sync": [config.to_dict() for config in sync_configs],
            }
        
        except Exception as e:
            logger.warning(f"Failed to get global defaults: {e}")
            return None
    
    async def _create_llm_configs(
        self,
        tenant_id: str,
        user_id: Optional[str],
        global_defaults: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> List[str]:
        """
        Create default LLM configurations for tenant.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID creating the configs
            global_defaults: Global default configurations to inherit from
        
        Returns:
            List of created configuration IDs
        
        **Feature: admin-configuration**
        **Validates: Requirements 7.4, 7.5**
        """
        created_ids = []
        
        # Use global defaults if available, otherwise use templates
        templates = []
        if global_defaults and global_defaults.get("llm"):
            templates = global_defaults["llm"]
            logger.info(f"Using {len(templates)} global LLM defaults for tenant {tenant_id}")
        else:
            templates = DefaultTemplates.LLM_TEMPLATES
            logger.info(f"Using {len(templates)} LLM templates for tenant {tenant_id}")
        
        for template in templates:
            try:
                config_id = str(uuid4())
                config_data = template.copy()
                
                # Remove fields that shouldn't be in config_data
                config_data.pop("id", None)
                config_data.pop("tenant_id", None)
                config_data.pop("created_at", None)
                config_data.pop("updated_at", None)
                config_data.pop("created_by", None)
                config_data.pop("updated_by", None)
                
                # Create configuration record
                config = AdminConfiguration(
                    id=config_id,
                    tenant_id=UUID(tenant_id) if tenant_id else None,
                    config_type=ConfigType.LLM.value,
                    name=config_data.get("name", "Default LLM"),
                    description=config_data.get("description"),
                    config_data=config_data,
                    is_active=True,
                    is_default=config_data.get("is_default", False),
                    created_by=UUID(user_id) if user_id else None,
                )
                
                self._db.add(config)
                created_ids.append(config_id)
                
                logger.debug(f"Created LLM config {config_id} for tenant {tenant_id}")
            
            except Exception as e:
                logger.error(f"Failed to create LLM config from template: {e}", exc_info=True)
                # Continue with other templates
        
        return created_ids
    
    async def _create_db_configs(
        self,
        tenant_id: str,
        user_id: Optional[str],
        global_defaults: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> List[str]:
        """
        Create default database connection templates for tenant.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID creating the configs
            global_defaults: Global default configurations to inherit from
        
        Returns:
            List of created configuration IDs
        
        **Feature: admin-configuration**
        **Validates: Requirements 7.4, 7.5**
        """
        created_ids = []
        
        # Use global defaults if available, otherwise use templates
        templates = []
        if global_defaults and global_defaults.get("database"):
            templates = global_defaults["database"]
            logger.info(f"Using {len(templates)} global database defaults for tenant {tenant_id}")
        else:
            templates = DefaultTemplates.DATABASE_TEMPLATES
            logger.info(f"Using {len(templates)} database templates for tenant {tenant_id}")
        
        for template in templates:
            try:
                config_id = str(uuid4())
                
                # Create database connection record
                # Note: password_encrypted is not set in templates (tenant must configure)
                config = DatabaseConnection(
                    id=config_id,
                    tenant_id=UUID(tenant_id) if tenant_id else None,
                    name=template.get("name", "Default Database"),
                    description=template.get("description"),
                    db_type=template.get("db_type", DatabaseType.POSTGRESQL.value),
                    host=template.get("host", "localhost"),
                    port=template.get("port", 5432),
                    database=template.get("database", "your_database"),
                    username=template.get("username", "your_username"),
                    password_encrypted=None,  # Must be configured by tenant
                    is_readonly=template.get("is_readonly", True),
                    ssl_enabled=template.get("ssl_enabled", False),
                    extra_config=template.get("extra_config", {}),
                    is_active=False,  # Inactive until configured
                    created_by=UUID(user_id) if user_id else None,
                )
                
                self._db.add(config)
                created_ids.append(config_id)
                
                logger.debug(f"Created database config {config_id} for tenant {tenant_id}")
            
            except Exception as e:
                logger.error(f"Failed to create database config from template: {e}", exc_info=True)
                # Continue with other templates
        
        return created_ids
    
    async def _create_sync_strategies(
        self,
        tenant_id: str,
        user_id: Optional[str],
        db_config_ids: List[str],
        global_defaults: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> List[str]:
        """
        Create default sync strategy templates for tenant.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID creating the strategies
            db_config_ids: List of database config IDs to associate with
            global_defaults: Global default configurations to inherit from
        
        Returns:
            List of created strategy IDs
        
        **Feature: admin-configuration**
        **Validates: Requirements 7.4, 7.5**
        """
        created_ids = []
        
        # Skip if no database configs available
        if not db_config_ids:
            logger.info(f"No database configs available, skipping sync strategy creation for tenant {tenant_id}")
            return created_ids
        
        # Use first database config as default
        default_db_config_id = db_config_ids[0]
        
        # Use global defaults if available, otherwise use templates
        templates = []
        if global_defaults and global_defaults.get("sync"):
            templates = global_defaults["sync"]
            logger.info(f"Using {len(templates)} global sync defaults for tenant {tenant_id}")
        else:
            templates = DefaultTemplates.SYNC_STRATEGY_TEMPLATES
            logger.info(f"Using {len(templates)} sync templates for tenant {tenant_id}")
        
        for template in templates:
            try:
                strategy_id = str(uuid4())
                
                # Create sync strategy record
                strategy = SyncStrategy(
                    id=strategy_id,
                    tenant_id=UUID(tenant_id) if tenant_id else None,
                    db_config_id=UUID(default_db_config_id),
                    name=template.get("name", "Default Sync Strategy"),
                    mode=template.get("mode", SyncMode.FULL.value),
                    incremental_field=template.get("incremental_field"),
                    schedule=template.get("schedule"),
                    filter_conditions=template.get("filter_conditions", []),
                    batch_size=template.get("batch_size", 1000),
                    enabled=template.get("enabled", False),  # Disabled by default
                    created_by=UUID(user_id) if user_id else None,
                )
                
                self._db.add(strategy)
                created_ids.append(strategy_id)
                
                logger.debug(f"Created sync strategy {strategy_id} for tenant {tenant_id}")
            
            except Exception as e:
                logger.error(f"Failed to create sync strategy from template: {e}", exc_info=True)
                # Continue with other templates
        
        return created_ids
    
    async def get_tenant_config_summary(
        self,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """
        Get summary of tenant's configurations.
        
        Args:
            tenant_id: Tenant ID
        
        Returns:
            Dictionary with configuration counts and status
        """
        if self._db is None:
            raise ValueError("Database session is required")
        
        try:
            # Count LLM configurations
            llm_query = select(AdminConfiguration).where(
                and_(
                    AdminConfiguration.tenant_id == UUID(tenant_id),
                    AdminConfiguration.config_type == ConfigType.LLM.value,
                )
            )
            llm_result = await self._db.execute(llm_query)
            llm_configs = llm_result.scalars().all()
            
            # Count database configurations
            db_query = select(DatabaseConnection).where(
                DatabaseConnection.tenant_id == UUID(tenant_id)
            )
            db_result = await self._db.execute(db_query)
            db_configs = db_result.scalars().all()
            
            # Count sync strategies
            sync_query = select(SyncStrategy).where(
                SyncStrategy.tenant_id == UUID(tenant_id)
            )
            sync_result = await self._db.execute(sync_query)
            sync_strategies = sync_result.scalars().all()
            
            return {
                "tenant_id": tenant_id,
                "llm_configs": {
                    "total": len(llm_configs),
                    "active": sum(1 for c in llm_configs if c.is_active),
                    "default": sum(1 for c in llm_configs if c.is_default),
                },
                "db_configs": {
                    "total": len(db_configs),
                    "active": sum(1 for c in db_configs if c.is_active),
                    "configured": sum(1 for c in db_configs if c.password_encrypted),
                },
                "sync_strategies": {
                    "total": len(sync_strategies),
                    "enabled": sum(1 for s in sync_strategies if s.enabled),
                },
            }
        
        except Exception as e:
            logger.error(f"Failed to get tenant config summary: {e}", exc_info=True)
            raise


# ============== Singleton Instance ==============

_tenant_config_initializer: Optional[TenantConfigInitializer] = None


def get_tenant_config_initializer() -> TenantConfigInitializer:
    """
    Get singleton instance of TenantConfigInitializer.
    
    Returns:
        TenantConfigInitializer instance
    """
    global _tenant_config_initializer
    if _tenant_config_initializer is None:
        _tenant_config_initializer = TenantConfigInitializer()
    return _tenant_config_initializer


def set_tenant_config_initializer(initializer: TenantConfigInitializer) -> None:
    """
    Set singleton instance of TenantConfigInitializer.
    
    Args:
        initializer: TenantConfigInitializer instance to set
    """
    global _tenant_config_initializer
    _tenant_config_initializer = initializer
