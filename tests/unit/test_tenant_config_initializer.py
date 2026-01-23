"""
Unit tests for Tenant Configuration Initializer.

Tests the initialization of default configurations for new tenants including:
- LLM configuration templates
- Database connection templates
- Sync strategy templates
- Configuration inheritance from global defaults

**Feature: admin-configuration**
**Validates: Requirements 7.4, 7.5**
**Property 22: Tenant Default Initialization**
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.admin.tenant_config_initializer import (
    TenantConfigInitializer,
    DefaultTemplates,
    get_tenant_config_initializer,
    set_tenant_config_initializer,
)
from src.admin.schemas import ConfigType, LLMType, DatabaseType, SyncMode


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def initializer(mock_db_session):
    """Create a TenantConfigInitializer instance with mock database."""
    return TenantConfigInitializer(db=mock_db_session)


@pytest.fixture
def tenant_id():
    """Generate a test tenant ID."""
    return str(uuid4())


@pytest.fixture
def user_id():
    """Generate a test user ID."""
    return str(uuid4())


class TestDefaultTemplates:
    """Test default configuration templates."""
    
    def test_llm_templates_exist(self):
        """Test that LLM templates are defined."""
        assert len(DefaultTemplates.LLM_TEMPLATES) > 0
        assert any(t["llm_type"] == LLMType.LOCAL_OLLAMA.value for t in DefaultTemplates.LLM_TEMPLATES)
        assert any(t["llm_type"] == LLMType.OPENAI.value for t in DefaultTemplates.LLM_TEMPLATES)
        assert any(t["llm_type"] == LLMType.QIANWEN.value for t in DefaultTemplates.LLM_TEMPLATES)
    
    def test_llm_template_structure(self):
        """Test that LLM templates have required fields."""
        for template in DefaultTemplates.LLM_TEMPLATES:
            assert "name" in template
            assert "llm_type" in template
            assert "model_name" in template
            assert "temperature" in template
            assert "max_tokens" in template
            assert "timeout_seconds" in template
    
    def test_database_templates_exist(self):
        """Test that database templates are defined."""
        assert len(DefaultTemplates.DATABASE_TEMPLATES) > 0
        assert any(t["db_type"] == DatabaseType.POSTGRESQL.value for t in DefaultTemplates.DATABASE_TEMPLATES)
        assert any(t["db_type"] == DatabaseType.MYSQL.value for t in DefaultTemplates.DATABASE_TEMPLATES)
    
    def test_database_template_structure(self):
        """Test that database templates have required fields."""
        for template in DefaultTemplates.DATABASE_TEMPLATES:
            assert "name" in template
            assert "db_type" in template
            assert "host" in template
            assert "port" in template
            assert "database" in template
            assert "username" in template
            assert "is_readonly" in template
    
    def test_sync_strategy_templates_exist(self):
        """Test that sync strategy templates are defined."""
        assert len(DefaultTemplates.SYNC_STRATEGY_TEMPLATES) > 0
        assert any(t["mode"] == SyncMode.FULL.value for t in DefaultTemplates.SYNC_STRATEGY_TEMPLATES)
        assert any(t["mode"] == SyncMode.INCREMENTAL.value for t in DefaultTemplates.SYNC_STRATEGY_TEMPLATES)
    
    def test_sync_strategy_template_structure(self):
        """Test that sync strategy templates have required fields."""
        for template in DefaultTemplates.SYNC_STRATEGY_TEMPLATES:
            assert "name" in template
            assert "mode" in template
            assert "batch_size" in template
            assert "enabled" in template


class TestTenantConfigInitializer:
    """Test TenantConfigInitializer class."""
    
    def test_initialization(self, mock_db_session):
        """Test initializer creation."""
        initializer = TenantConfigInitializer(db=mock_db_session)
        assert initializer.db == mock_db_session
    
    def test_db_property_setter(self, initializer, mock_db_session):
        """Test database session property setter."""
        new_session = AsyncMock()
        initializer.db = new_session
        assert initializer.db == new_session
    
    @pytest.mark.asyncio
    async def test_initialize_tenant_defaults_requires_db(self, tenant_id):
        """Test that initialization requires database session."""
        initializer = TenantConfigInitializer(db=None)
        
        with pytest.raises(ValueError, match="Database session is required"):
            await initializer.initialize_tenant_defaults(tenant_id)
    
    @pytest.mark.asyncio
    async def test_initialize_tenant_defaults_all_types(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test initialization with all configuration types."""
        # Mock database queries to return no global defaults
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        result = await initializer.initialize_tenant_defaults(
            tenant_id=tenant_id,
            user_id=user_id,
            include_llm=True,
            include_database=True,
            include_sync=True,
            inherit_global=False,
        )
        
        # Verify result structure
        assert result["tenant_id"] == tenant_id
        assert isinstance(result["llm_configs"], list)
        assert isinstance(result["db_configs"], list)
        assert isinstance(result["sync_strategies"], list)
        assert "created_at" in result
        
        # Verify configurations were created
        assert len(result["llm_configs"]) == len(DefaultTemplates.LLM_TEMPLATES)
        assert len(result["db_configs"]) == len(DefaultTemplates.DATABASE_TEMPLATES)
        # Sync strategies should be created (one per template)
        assert len(result["sync_strategies"]) == len(DefaultTemplates.SYNC_STRATEGY_TEMPLATES)
        
        # Verify database operations
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_tenant_defaults_llm_only(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test initialization with LLM configurations only."""
        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        result = await initializer.initialize_tenant_defaults(
            tenant_id=tenant_id,
            user_id=user_id,
            include_llm=True,
            include_database=False,
            include_sync=False,
            inherit_global=False,
        )
        
        assert len(result["llm_configs"]) > 0
        assert len(result["db_configs"]) == 0
        assert len(result["sync_strategies"]) == 0
    
    @pytest.mark.asyncio
    async def test_initialize_tenant_defaults_database_only(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test initialization with database configurations only."""
        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        result = await initializer.initialize_tenant_defaults(
            tenant_id=tenant_id,
            user_id=user_id,
            include_llm=False,
            include_database=True,
            include_sync=False,
            inherit_global=False,
        )
        
        assert len(result["llm_configs"]) == 0
        assert len(result["db_configs"]) > 0
        assert len(result["sync_strategies"]) == 0
    
    @pytest.mark.asyncio
    async def test_initialize_tenant_defaults_rollback_on_error(
        self, initializer, mock_db_session, tenant_id
    ):
        """Test that initialization rolls back on error during commit."""
        # Mock execute to return empty results (no global defaults)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        # Mock commit to raise error
        mock_db_session.commit.side_effect = Exception("Commit failed")
        
        with pytest.raises(Exception, match="Commit failed"):
            await initializer.initialize_tenant_defaults(
                tenant_id=tenant_id,
                inherit_global=False,
            )
        
        # Verify rollback was called
        mock_db_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_global_defaults_no_defaults(
        self, initializer, mock_db_session
    ):
        """Test getting global defaults when none exist."""
        # Mock database queries to return empty results
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        result = await initializer._get_global_defaults()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_global_defaults_with_configs(
        self, initializer, mock_db_session
    ):
        """Test getting global defaults when they exist."""
        # Mock LLM config
        mock_llm_config = MagicMock()
        mock_llm_config.to_dict.return_value = {
            "id": str(uuid4()),
            "name": "Global LLM",
            "llm_type": LLMType.OPENAI.value,
        }
        
        # Mock database config
        mock_db_config = MagicMock()
        mock_db_config.to_dict.return_value = {
            "id": str(uuid4()),
            "name": "Global DB",
            "db_type": DatabaseType.POSTGRESQL.value,
        }
        
        # Mock sync config
        mock_sync_config = MagicMock()
        mock_sync_config.to_dict.return_value = {
            "id": str(uuid4()),
            "name": "Global Sync",
            "mode": SyncMode.FULL.value,
        }
        
        # Setup mock to return different results for each query
        call_count = [0]  # Use list to avoid closure issues
        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:  # LLM query
                mock_result.scalars.return_value.all.return_value = [mock_llm_config]
            elif call_count[0] == 2:  # DB query
                mock_result.scalars.return_value.all.return_value = [mock_db_config]
            else:  # Sync query
                mock_result.scalars.return_value.all.return_value = [mock_sync_config]
            return mock_result
        
        mock_db_session.execute = mock_execute
        
        result = await initializer._get_global_defaults()
        
        assert result is not None
        assert "llm" in result
        assert "database" in result
        assert "sync" in result
        assert len(result["llm"]) == 1
        assert len(result["database"]) == 1
        assert len(result["sync"]) == 1
    
    @pytest.mark.asyncio
    async def test_create_llm_configs(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test creating LLM configurations."""
        result = await initializer._create_llm_configs(
            tenant_id=tenant_id,
            user_id=user_id,
            global_defaults=None,
        )
        
        # Verify configs were created
        assert len(result) == len(DefaultTemplates.LLM_TEMPLATES)
        assert all(isinstance(config_id, str) for config_id in result)
        
        # Verify database add was called for each config
        assert mock_db_session.add.call_count == len(DefaultTemplates.LLM_TEMPLATES)
    
    @pytest.mark.asyncio
    async def test_create_llm_configs_with_global_defaults(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test creating LLM configurations with global defaults."""
        global_defaults = {
            "llm": [
                {
                    "name": "Global LLM",
                    "llm_type": LLMType.OPENAI.value,
                    "model_name": "gpt-4",
                    "temperature": 0.5,
                    "max_tokens": 4096,
                    "timeout_seconds": 120,
                }
            ]
        }
        
        result = await initializer._create_llm_configs(
            tenant_id=tenant_id,
            user_id=user_id,
            global_defaults=global_defaults,
        )
        
        # Should use global defaults instead of templates
        assert len(result) == 1
        mock_db_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_db_configs(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test creating database configurations."""
        result = await initializer._create_db_configs(
            tenant_id=tenant_id,
            user_id=user_id,
            global_defaults=None,
        )
        
        # Verify configs were created
        assert len(result) == len(DefaultTemplates.DATABASE_TEMPLATES)
        assert all(isinstance(config_id, str) for config_id in result)
        
        # Verify database add was called for each config
        assert mock_db_session.add.call_count == len(DefaultTemplates.DATABASE_TEMPLATES)
    
    @pytest.mark.asyncio
    async def test_create_sync_strategies(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test creating sync strategies."""
        db_config_ids = [str(uuid4()), str(uuid4())]
        
        result = await initializer._create_sync_strategies(
            tenant_id=tenant_id,
            user_id=user_id,
            db_config_ids=db_config_ids,
            global_defaults=None,
        )
        
        # Verify strategies were created
        assert len(result) == len(DefaultTemplates.SYNC_STRATEGY_TEMPLATES)
        assert all(isinstance(strategy_id, str) for strategy_id in result)
        
        # Verify database add was called for each strategy
        assert mock_db_session.add.call_count == len(DefaultTemplates.SYNC_STRATEGY_TEMPLATES)
    
    @pytest.mark.asyncio
    async def test_create_sync_strategies_no_db_configs(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test creating sync strategies with no database configs."""
        result = await initializer._create_sync_strategies(
            tenant_id=tenant_id,
            user_id=user_id,
            db_config_ids=[],
            global_defaults=None,
        )
        
        # Should not create any strategies without database configs
        assert len(result) == 0
        mock_db_session.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_tenant_config_summary(
        self, initializer, mock_db_session, tenant_id
    ):
        """Test getting tenant configuration summary."""
        # Mock LLM configs
        mock_llm_config1 = MagicMock()
        mock_llm_config1.is_active = True
        mock_llm_config1.is_default = True
        
        mock_llm_config2 = MagicMock()
        mock_llm_config2.is_active = False
        mock_llm_config2.is_default = False
        
        # Mock DB configs
        mock_db_config = MagicMock()
        mock_db_config.is_active = True
        mock_db_config.password_encrypted = "encrypted"
        
        # Mock sync strategies
        mock_sync_strategy = MagicMock()
        mock_sync_strategy.enabled = True
        
        # Setup mock to return different results for each query
        call_count = [0]  # Use list to avoid closure issues
        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:  # LLM query
                mock_result.scalars.return_value.all.return_value = [mock_llm_config1, mock_llm_config2]
            elif call_count[0] == 2:  # DB query
                mock_result.scalars.return_value.all.return_value = [mock_db_config]
            else:  # Sync query
                mock_result.scalars.return_value.all.return_value = [mock_sync_strategy]
            return mock_result
        
        mock_db_session.execute = mock_execute
        
        result = await initializer.get_tenant_config_summary(tenant_id)
        
        assert result["tenant_id"] == tenant_id
        assert result["llm_configs"]["total"] == 2
        assert result["llm_configs"]["active"] == 1
        assert result["llm_configs"]["default"] == 1
        assert result["db_configs"]["total"] == 1
        assert result["db_configs"]["active"] == 1
        assert result["db_configs"]["configured"] == 1
        assert result["sync_strategies"]["total"] == 1
        assert result["sync_strategies"]["enabled"] == 1
    
    @pytest.mark.asyncio
    async def test_get_tenant_config_summary_requires_db(self, tenant_id):
        """Test that summary requires database session."""
        initializer = TenantConfigInitializer(db=None)
        
        with pytest.raises(ValueError, match="Database session is required"):
            await initializer.get_tenant_config_summary(tenant_id)


class TestSingletonFunctions:
    """Test singleton getter and setter functions."""
    
    def test_get_tenant_config_initializer(self):
        """Test getting singleton instance."""
        initializer = get_tenant_config_initializer()
        assert isinstance(initializer, TenantConfigInitializer)
        
        # Should return same instance
        initializer2 = get_tenant_config_initializer()
        assert initializer is initializer2
    
    def test_set_tenant_config_initializer(self, mock_db_session):
        """Test setting singleton instance."""
        custom_initializer = TenantConfigInitializer(db=mock_db_session)
        set_tenant_config_initializer(custom_initializer)
        
        retrieved = get_tenant_config_initializer()
        assert retrieved is custom_initializer
        
        # Reset for other tests
        set_tenant_config_initializer(None)


class TestConfigurationInheritance:
    """Test configuration inheritance from global defaults."""
    
    @pytest.mark.asyncio
    async def test_inheritance_enabled(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test that inheritance is enabled by default."""
        # Mock global defaults
        mock_llm_config = MagicMock()
        mock_llm_config.to_dict.return_value = {
            "name": "Global LLM",
            "llm_type": LLMType.OPENAI.value,
            "model_name": "gpt-4",
            "temperature": 0.5,
            "max_tokens": 4096,
            "timeout_seconds": 120,
        }
        
        call_count = [0]  # Use list to avoid closure issues
        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:  # LLM query for global defaults
                mock_result.scalars.return_value.all.return_value = [mock_llm_config]
            else:  # Other queries
                mock_result.scalars.return_value.all.return_value = []
            return mock_result
        
        mock_db_session.execute = mock_execute
        
        result = await initializer.initialize_tenant_defaults(
            tenant_id=tenant_id,
            user_id=user_id,
            include_llm=True,
            include_database=False,
            include_sync=False,
            inherit_global=True,
        )
        
        # Should inherit from global defaults
        assert result["inherited_from_global"] is True
    
    @pytest.mark.asyncio
    async def test_inheritance_disabled(
        self, initializer, mock_db_session, tenant_id, user_id
    ):
        """Test that inheritance can be disabled."""
        # Mock database queries
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        result = await initializer.initialize_tenant_defaults(
            tenant_id=tenant_id,
            user_id=user_id,
            include_llm=True,
            include_database=False,
            include_sync=False,
            inherit_global=False,
        )
        
        # Should not inherit from global defaults
        assert result["inherited_from_global"] is False
        # Should use templates instead
        assert len(result["llm_configs"]) == len(DefaultTemplates.LLM_TEMPLATES)
