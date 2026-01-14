"""
Tests for Config Manager.

Tests the unified configuration management functionality.

**Feature: admin-configuration**
**Validates: Requirements 2.4, 3.4**
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings
from uuid import uuid4

from src.admin.config_manager import ConfigManager, get_config_manager
from src.admin.schemas import (
    ConfigType,
    LLMType,
    DatabaseType,
    LLMConfigCreate,
    DBConfigCreate,
)


# ========== Custom Strategies ==========

def llm_config_create_strategy():
    """Strategy for generating LLM config create requests."""
    return st.builds(
        LLMConfigCreate,
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        llm_type=st.sampled_from(list(LLMType)),
        model_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        api_endpoint=st.just("http://localhost:11434"),
        temperature=st.floats(min_value=0.0, max_value=2.0),
        max_tokens=st.integers(min_value=1, max_value=128000),
        timeout_seconds=st.integers(min_value=1, max_value=600),
    )


def db_config_create_strategy():
    """Strategy for generating DB config create requests."""
    return st.builds(
        DBConfigCreate,
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        db_type=st.sampled_from(list(DatabaseType)),
        host=st.sampled_from(['localhost', '127.0.0.1']),
        port=st.integers(min_value=1, max_value=65535),
        database=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        username=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
        password=st.text(min_size=0, max_size=50),
        is_readonly=st.booleans(),
    )


class TestConfigManagerLLM:
    """Tests for LLM configuration management."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        manager = ConfigManager()
        manager.clear_in_memory_storage()
        return manager
    
    @given(config=llm_config_create_strategy())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_save_and_get_llm_config(self, config: LLMConfigCreate):
        """Saved LLM config should be retrievable."""
        manager = ConfigManager()
        manager.clear_in_memory_storage()
        
        user_id = str(uuid4())
        
        # Save config
        saved = await manager.save_llm_config(
            config=config,
            user_id=user_id,
            user_name="Test User",
        )
        
        assert saved.id is not None
        assert saved.name == config.name
        assert saved.llm_type == config.llm_type
        assert saved.model_name == config.model_name
        
        # Retrieve config
        retrieved = await manager.get_llm_config(saved.id)
        
        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.name == saved.name
    
    @pytest.mark.asyncio
    async def test_save_llm_config_encrypts_api_key(self, manager):
        """API key should be encrypted when saved."""
        config = LLMConfigCreate(
            name="test-llm",
            llm_type=LLMType.OPENAI,
            model_name="gpt-4",
            api_key="sk-test-key-12345",
        )
        
        saved = await manager.save_llm_config(
            config=config,
            user_id="user-1",
        )
        
        # API key should be masked in response
        assert saved.api_key is None
        assert saved.api_key_masked is not None
        assert "****" in saved.api_key_masked
        
        # Raw storage should have encrypted key
        raw = manager._in_memory_configs[ConfigType.LLM.value][saved.id]
        assert "api_key" not in raw
        assert "api_key_encrypted" in raw
    
    @pytest.mark.asyncio
    async def test_list_llm_configs(self, manager):
        """Should list all LLM configs."""
        # Create multiple configs
        for i in range(3):
            config = LLMConfigCreate(
                name=f"llm-{i}",
                llm_type=LLMType.LOCAL_OLLAMA,
                model_name=f"model-{i}",
            )
            await manager.save_llm_config(config=config, user_id="user-1")
        
        configs = await manager.list_llm_configs()
        
        assert len(configs) == 3
    
    @pytest.mark.asyncio
    async def test_delete_llm_config(self, manager):
        """Should delete LLM config."""
        config = LLMConfigCreate(
            name="to-delete",
            llm_type=LLMType.LOCAL_OLLAMA,
            model_name="model",
        )
        
        saved = await manager.save_llm_config(config=config, user_id="user-1")
        
        # Delete
        result = await manager.delete_llm_config(
            config_id=saved.id,
            user_id="user-1",
        )
        
        assert result is True
        
        # Should not be retrievable
        retrieved = await manager.get_llm_config(saved.id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_llm_config(self, manager):
        """Deleting non-existent config should return False."""
        result = await manager.delete_llm_config(
            config_id="nonexistent",
            user_id="user-1",
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_save_llm_config_records_history(self, manager):
        """Saving config should record history."""
        config = LLMConfigCreate(
            name="test-llm",
            llm_type=LLMType.LOCAL_OLLAMA,
            model_name="model",
        )
        
        await manager.save_llm_config(
            config=config,
            user_id="user-1",
            user_name="Test User",
        )
        
        # Check history
        history = await manager._history_tracker.get_history(
            config_type=ConfigType.LLM
        )
        
        assert len(history) == 1
        assert history[0].user_id == "user-1"
        assert history[0].user_name == "Test User"


class TestConfigManagerDB:
    """Tests for database configuration management."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        manager = ConfigManager()
        manager.clear_in_memory_storage()
        return manager
    
    @given(config=db_config_create_strategy())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_save_and_get_db_config(self, config: DBConfigCreate):
        """Saved DB config should be retrievable."""
        manager = ConfigManager()
        manager.clear_in_memory_storage()
        
        user_id = str(uuid4())
        
        # Save config
        saved = await manager.save_db_config(
            config=config,
            user_id=user_id,
            user_name="Test User",
        )
        
        assert saved.id is not None
        assert saved.name == config.name
        assert saved.db_type == config.db_type
        assert saved.host == config.host
        
        # Retrieve config
        retrieved = await manager.get_db_config(saved.id)
        
        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.name == saved.name
    
    @pytest.mark.asyncio
    async def test_save_db_config_encrypts_password(self, manager):
        """Password should be encrypted when saved."""
        config = DBConfigCreate(
            name="test-db",
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="secret123",
        )
        
        saved = await manager.save_db_config(
            config=config,
            user_id="user-1",
        )
        
        # Password should be masked in response
        assert saved.password_masked is not None
        assert "*" in saved.password_masked  # Contains asterisks
        assert saved.password_masked != "secret123"  # Not plaintext
        
        # Raw storage should have encrypted password
        raw = manager._in_memory_configs[ConfigType.DATABASE.value][saved.id]
        assert "password" not in raw
        assert "password_encrypted" in raw
    
    @pytest.mark.asyncio
    async def test_list_db_configs(self, manager):
        """Should list all DB configs."""
        for i in range(3):
            config = DBConfigCreate(
                name=f"db-{i}",
                db_type=DatabaseType.POSTGRESQL,
                host="localhost",
                port=5432 + i,
                database=f"db{i}",
                username="user",
            )
            await manager.save_db_config(config=config, user_id="user-1")
        
        configs = await manager.list_db_configs()
        
        assert len(configs) == 3
    
    @pytest.mark.asyncio
    async def test_delete_db_config(self, manager):
        """Should delete DB config."""
        config = DBConfigCreate(
            name="to-delete",
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
        )
        
        saved = await manager.save_db_config(config=config, user_id="user-1")
        
        result = await manager.delete_db_config(
            config_id=saved.id,
            user_id="user-1",
        )
        
        assert result is True
        
        retrieved = await manager.get_db_config(saved.id)
        assert retrieved is None


class TestConfigManagerValidation:
    """Tests for configuration validation."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        manager = ConfigManager()
        manager.clear_in_memory_storage()
        return manager
    
    def test_validate_llm_config(self, manager):
        """Should validate LLM config."""
        valid_config = {
            "name": "test",
            "llm_type": "local_ollama",
            "model_name": "llama2",
            "temperature": 0.7,
        }
        
        result = manager.validate_config(ConfigType.LLM, valid_config)
        
        assert result.is_valid
    
    def test_validate_llm_config_invalid(self, manager):
        """Should reject invalid LLM config."""
        invalid_config = {
            "name": "test",
            "llm_type": "local_ollama",
            "model_name": "llama2",
            "temperature": 5.0,  # Invalid: > 2.0
        }
        
        result = manager.validate_config(ConfigType.LLM, invalid_config)
        
        assert not result.is_valid
        assert any(e.field == "temperature" for e in result.errors)
    
    def test_validate_db_config(self, manager):
        """Should validate DB config."""
        valid_config = {
            "name": "test",
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "user",
        }
        
        result = manager.validate_config(ConfigType.DATABASE, valid_config)
        
        assert result.is_valid
    
    def test_validate_db_config_invalid(self, manager):
        """Should reject invalid DB config."""
        invalid_config = {
            "name": "test",
            "db_type": "postgresql",
            "host": "localhost",
            "port": 99999,  # Invalid: > 65535
            "database": "testdb",
            "username": "user",
        }
        
        result = manager.validate_config(ConfigType.DATABASE, invalid_config)
        
        assert not result.is_valid
        assert any(e.field == "port" for e in result.errors)
    
    @pytest.mark.asyncio
    async def test_save_invalid_config_raises_error(self, manager):
        """Saving invalid config should raise ValueError."""
        config = LLMConfigCreate(
            name="test",
            llm_type=LLMType.LOCAL_OLLAMA,
            model_name="",  # Invalid: empty
        )
        
        with pytest.raises(ValueError) as exc_info:
            await manager.save_llm_config(config=config, user_id="user-1")
        
        assert "Invalid LLM config" in str(exc_info.value)


class TestConfigManagerSingleton:
    """Tests for singleton behavior."""
    
    def test_get_config_manager_singleton(self):
        """get_config_manager should return the same instance."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2


class TestConfigManagerUpdate:
    """Tests for configuration updates."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        manager = ConfigManager()
        manager.clear_in_memory_storage()
        return manager
    
    @pytest.mark.asyncio
    async def test_update_llm_config(self, manager):
        """Should update existing LLM config."""
        # Create initial config
        config = LLMConfigCreate(
            name="original",
            llm_type=LLMType.LOCAL_OLLAMA,
            model_name="llama2",
            temperature=0.5,
        )
        
        saved = await manager.save_llm_config(config=config, user_id="user-1")
        original_id = saved.id
        
        # Update config
        from src.admin.schemas import LLMConfigUpdate
        update = LLMConfigUpdate(
            name="updated",
            temperature=0.9,
        )
        
        updated = await manager.save_llm_config(
            config=update,
            user_id="user-1",
            config_id=original_id,
        )
        
        assert updated.id == original_id
        assert updated.name == "updated"
        assert updated.temperature == 0.9
        # Unchanged fields should remain
        assert updated.model_name == "llama2"
    
    @pytest.mark.asyncio
    async def test_update_records_history_with_old_value(self, manager):
        """Update should record history with old value."""
        # Create initial config
        config = LLMConfigCreate(
            name="original",
            llm_type=LLMType.LOCAL_OLLAMA,
            model_name="llama2",
        )
        
        saved = await manager.save_llm_config(config=config, user_id="user-1")
        
        # Update config
        from src.admin.schemas import LLMConfigUpdate
        update = LLMConfigUpdate(name="updated")
        
        await manager.save_llm_config(
            config=update,
            user_id="user-2",
            config_id=saved.id,
        )
        
        # Check history
        history = await manager._history_tracker.get_history(
            config_type=ConfigType.LLM
        )
        
        # Should have 2 records: create and update
        assert len(history) == 2
        
        # Most recent (update) should have old_value
        update_history = history[0]
        assert update_history.old_value is not None
        assert update_history.old_value.get("name") == "original"
