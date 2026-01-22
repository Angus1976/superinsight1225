"""
Admin Configuration History Property Tests

Tests configuration history tracking properties for all config types.

**Feature: admin-configuration**
**Validates: Requirements 6.1, 6.5, 4.6, 5.6**
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, Optional

# Import the configuration manager and history tracker
from src.admin.config_manager import ConfigManager
from src.admin.history_tracker import HistoryTracker
from src.admin.schemas import (
    ConfigType,
    LLMConfigCreate,
    LLMType,
    DBConfigCreate,
    DatabaseType,
)


# ============================================================================
# Test Strategies (Hypothesis Generators)
# ============================================================================

def llm_config_strategy():
    """Generate valid LLM configurations."""
    return st.builds(
        LLMConfigCreate,
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            min_codepoint=97,
            max_codepoint=122
        )),
        description=st.one_of(st.none(), st.text(max_size=200)),
        llm_type=st.sampled_from([LLMType.OPENAI, LLMType.QIANWEN, LLMType.ZHIPU, LLMType.LOCAL_OLLAMA]),
        model_name=st.text(min_size=3, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P'),
            min_codepoint=45,
            max_codepoint=122
        )),
        api_endpoint=st.one_of(
            st.none(),
            st.from_regex(r'https?://[a-z0-9\-\.]+\.[a-z]{2,}(/[a-z0-9\-]*)?', fullmatch=True)
        ),
        api_key=st.text(min_size=20, max_size=100, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            min_codepoint=48,
            max_codepoint=122
        )),
        temperature=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        max_tokens=st.integers(min_value=100, max_value=8000),
        timeout_seconds=st.integers(min_value=10, max_value=300),
        extra_config=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',))),
            values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            max_size=3
        ),
        is_default=st.booleans()
    )


def db_config_strategy():
    """Generate valid database configurations."""
    return st.builds(
        DBConfigCreate,
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            min_codepoint=97,
            max_codepoint=122
        )),
        description=st.one_of(st.none(), st.text(max_size=200)),
        db_type=st.sampled_from([DatabaseType.POSTGRESQL, DatabaseType.MYSQL, DatabaseType.SQLITE]),
        host=st.text(min_size=5, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            min_codepoint=97,
            max_codepoint=122
        )),
        port=st.integers(min_value=1024, max_value=65535),
        database=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            min_codepoint=97,
            max_codepoint=122
        )),
        username=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            min_codepoint=97,
            max_codepoint=122
        )),
        password=st.text(min_size=8, max_size=64, alphabet=st.characters(
            whitelist_categories=('L', 'N', 'P'),
            min_codepoint=33,
            max_codepoint=126
        )),
        is_readonly=st.booleans(),
        ssl_enabled=st.booleans(),
        extra_config=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',))),
            values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            max_size=3
        )
    )


def user_info_strategy():
    """Generate user ID and name."""
    return st.tuples(
        st.text(min_size=10, max_size=36, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            min_codepoint=97,
            max_codepoint=122
        )),
        st.text(min_size=3, max_size=50, alphabet=st.characters(
            whitelist_categories=('L',),
            min_codepoint=97,
            max_codepoint=122
        ))
    )


# ============================================================================
# Property 18: Configuration History Completeness
# ============================================================================

class TestConfigurationHistoryCompleteness:
    """
    Property 18: Configuration History Completeness
    
    For any configuration change (create, update, delete, rollback), a history 
    entry should be created with timestamp, author, change type, and full 
    configuration data.
    
    **Feature: admin-configuration**
    **Validates: Requirements 6.1, 6.5, 4.6, 5.6**
    """
    
    @given(
        config=llm_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_create_operation_creates_history_entry(self, config, user_info):
        """
        Creating a configuration creates a history entry.
        
        For any configuration creation, a history entry should be created
        with timestamp, author (user_id and user_name), and full data.
        """
        # Skip configs with empty names or API keys
        assume(len(config.name.strip()) > 0)
        assume(len(config.api_key.strip()) >= 20)
        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)
        
        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker
        
        async def run_test():
            # Save the configuration (create operation)
            saved_config = await config_manager.save_llm_config(
                config=config,
                user_id=user_id,
                user_name=user_name
            )
            
            # Get history for this config type
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                limit=10
            )
            
            # Verify history entry was created
            assert len(history) > 0, "History entry should be created for create operation"
            
            # Get the most recent history entry
            latest_history = history[0]
            
            # Verify timestamp is present and recent
            assert latest_history.created_at is not None, "History entry should have timestamp"
            time_diff = datetime.utcnow() - latest_history.created_at
            assert time_diff.total_seconds() < 5, "History timestamp should be recent"
            
            # Verify author information
            assert latest_history.user_id == user_id, "History should record user_id"
            assert latest_history.user_name == user_name, "History should record user_name"
            
            # Verify config type
            assert latest_history.config_type == ConfigType.LLM, "History should record config type"
            
            # Verify old_value is None for create operation
            assert latest_history.old_value is None, "Create operation should have None as old_value"
            
            # Verify new_value contains configuration data
            assert latest_history.new_value is not None, "History should contain new_value"
            assert latest_history.new_value.get("name") == config.name, \
                "History new_value should contain config name"
            assert latest_history.new_value.get("model_name") == config.model_name, \
                "History new_value should contain model_name"
            
            # Verify sensitive fields are sanitized in history
            assert "[REDACTED]" in str(latest_history.new_value.get("api_key_encrypted", "")), \
                "Sensitive fields should be sanitized in history"
        
        asyncio.run(run_test())
    
    @given(
        initial_config=llm_config_strategy(),
        updated_config=llm_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_update_operation_creates_history_entry(self, initial_config, updated_config, user_info):
        """
        Updating a configuration creates a history entry with old and new values.
        
        For any configuration update, a history entry should be created
        with both old_value and new_value, timestamp, and author.
        """
        # Skip configs with empty names or API keys
        assume(len(initial_config.name.strip()) > 0)
        assume(len(initial_config.api_key.strip()) >= 20)
        assume(len(updated_config.name.strip()) > 0)
        assume(len(updated_config.api_key.strip()) >= 20)
        # Ensure configs are different
        assume(initial_config.name != updated_config.name or 
               initial_config.model_name != updated_config.model_name)
        
        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)
        
        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker
        
        async def run_test():
            # Create initial configuration
            saved_config = await config_manager.save_llm_config(
                config=initial_config,
                user_id=user_id,
                user_name=user_name
            )
            config_id = saved_config.id
            
            # Clear history to focus on update operation
            history_tracker.clear_in_memory_history()
            
            # Update the configuration
            updated_saved = await config_manager.save_llm_config(
                config=updated_config,
                user_id=user_id,
                user_name=user_name,
                config_id=config_id
            )
            
            # Get history for this config
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                config_id=config_id,
                limit=10
            )
            
            # Verify history entry was created for update
            assert len(history) > 0, "History entry should be created for update operation"
            
            # Get the most recent history entry
            latest_history = history[0]
            
            # Verify timestamp is present and recent
            assert latest_history.created_at is not None, "History entry should have timestamp"
            time_diff = datetime.utcnow() - latest_history.created_at
            assert time_diff.total_seconds() < 5, "History timestamp should be recent"
            
            # Verify author information
            assert latest_history.user_id == user_id, "History should record user_id"
            assert latest_history.user_name == user_name, "History should record user_name"
            
            # Verify both old_value and new_value are present
            assert latest_history.old_value is not None, "Update operation should have old_value"
            assert latest_history.new_value is not None, "Update operation should have new_value"
            
            # Verify old_value contains initial config data
            assert latest_history.old_value.get("name") == initial_config.name, \
                "History old_value should contain initial config name"
            
            # Verify new_value contains updated config data
            assert latest_history.new_value.get("name") == updated_config.name, \
                "History new_value should contain updated config name"
        
        asyncio.run(run_test())
    
    @given(
        config=db_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_delete_operation_creates_history_entry(self, config, user_info):
        """
        Deleting a configuration creates a history entry.
        
        For any configuration deletion, a history entry should be created
        with the deleted configuration data, timestamp, and author.
        """
        # Skip configs with empty names or passwords
        assume(len(config.name.strip()) > 0)
        assume(len(config.password.strip()) >= 8)
        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)
        
        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker
        
        async def run_test():
            # Create configuration
            saved_config = await config_manager.save_db_config(
                config=config,
                user_id=user_id,
                user_name=user_name
            )
            config_id = saved_config.id
            
            # Clear history to focus on delete operation
            history_tracker.clear_in_memory_history()
            
            # Delete the configuration
            deleted = await config_manager.delete_db_config(
                config_id=config_id,
                user_id=user_id,
                user_name=user_name
            )
            
            assert deleted is True, "Configuration should be deleted"
            
            # Get history for this config
            history = await history_tracker.get_history(
                config_type=ConfigType.DATABASE,
                config_id=config_id,
                limit=10
            )
            
            # Verify history entry was created for delete
            assert len(history) > 0, "History entry should be created for delete operation"
            
            # Get the most recent history entry
            latest_history = history[0]
            
            # Verify timestamp is present and recent
            assert latest_history.created_at is not None, "History entry should have timestamp"
            time_diff = datetime.utcnow() - latest_history.created_at
            assert time_diff.total_seconds() < 5, "History timestamp should be recent"
            
            # Verify author information
            assert latest_history.user_id == user_id, "History should record user_id"
            assert latest_history.user_name == user_name, "History should record user_name"
            
            # Verify old_value contains deleted config data
            assert latest_history.old_value is not None, "Delete operation should have old_value"
            assert latest_history.old_value.get("name") == config.name, \
                "History old_value should contain deleted config name"
            
            # Verify new_value indicates deletion
            assert latest_history.new_value is not None, "Delete operation should have new_value"
            assert latest_history.new_value.get("_deleted") is True, \
                "History new_value should indicate deletion"
        
        asyncio.run(run_test())
    
    @given(
        initial_config=llm_config_strategy(),
        updated_config=llm_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=50, deadline=None)
    def test_rollback_operation_creates_history_entry(self, initial_config, updated_config, user_info):
        """
        Rolling back a configuration creates a history entry.
        
        For any configuration rollback, a history entry should be created
        documenting the rollback operation with timestamp and author.
        """
        # Skip configs with empty names or API keys
        assume(len(initial_config.name.strip()) > 0)
        assume(len(initial_config.api_key.strip()) >= 20)
        assume(len(updated_config.name.strip()) > 0)
        assume(len(updated_config.api_key.strip()) >= 20)
        # Ensure configs are different
        assume(initial_config.name != updated_config.name or 
               initial_config.model_name != updated_config.model_name)
        
        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)
        
        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker
        
        async def run_test():
            # Create initial configuration
            saved_config = await config_manager.save_llm_config(
                config=initial_config,
                user_id=user_id,
                user_name=user_name
            )
            config_id = saved_config.id
            
            # Update the configuration (this creates a history entry with old_value)
            updated_saved = await config_manager.save_llm_config(
                config=updated_config,
                user_id=user_id,
                user_name=user_name,
                config_id=config_id
            )
            
            # Get the history entry for the update operation
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                config_id=config_id,
                limit=10
            )
            
            # Find a history entry with non-None old_value (the update operation)
            update_history = None
            for h in history:
                if h.old_value is not None:
                    update_history = h
                    break
            
            assert update_history is not None, "Should have history entry with old_value"
            history_id = update_history.id
            
            # Clear history to focus on rollback operation
            history_tracker.clear_in_memory_history()
            
            # Restore the history entry we want to rollback to
            await history_tracker.record_change(
                config_type=ConfigType.LLM,
                old_value=update_history.old_value,
                new_value=update_history.new_value,
                user_id=user_id,
                user_name=user_name,
                config_id=config_id
            )
            
            # Get the restored history entry
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                limit=1
            )
            history_id = history[0].id
            
            # Perform rollback
            rollback_user_id = str(uuid4())
            rollback_user_name = "rollback_user"
            
            rolled_back_value = await history_tracker.rollback(
                history_id=history_id,
                user_id=rollback_user_id,
                user_name=rollback_user_name
            )
            
            # Verify rollback returned a value
            assert rolled_back_value is not None, "Rollback should return the rolled-back value"
            
            # Get history after rollback
            history_after_rollback = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                limit=10
            )
            
            # Verify rollback created a new history entry
            assert len(history_after_rollback) >= 2, \
                "Rollback should create a new history entry"
            
            # Get the most recent history entry (the rollback)
            rollback_history = history_after_rollback[0]
            
            # Verify timestamp is present and recent
            assert rollback_history.created_at is not None, \
                "Rollback history entry should have timestamp"
            time_diff = datetime.utcnow() - rollback_history.created_at
            assert time_diff.total_seconds() < 5, \
                "Rollback history timestamp should be recent"
            
            # Verify rollback author information
            assert rollback_history.user_id == rollback_user_id, \
                "Rollback history should record rollback user_id"
            assert rollback_history.user_name == rollback_user_name, \
                "Rollback history should record rollback user_name"
            
            # Verify rollback new_value matches the rolled-back configuration
            assert rollback_history.new_value is not None, \
                "Rollback history should have new_value"
            
            # Verify the rolled-back value matches the old_value from the history entry
            assert rollback_history.new_value == update_history.old_value, \
                "Rollback new_value should match the old_value from history"
        
        asyncio.run(run_test())
    
    @given(
        config=llm_config_strategy(),
        user_info=user_info_strategy(),
        tenant_id=st.text(min_size=10, max_size=36, alphabet=st.characters(
            whitelist_categories=('L', 'N'),
            min_codepoint=97,
            max_codepoint=122
        ))
    )
    @settings(max_examples=50, deadline=None)
    def test_history_includes_tenant_id(self, config, user_info, tenant_id):
        """
        History entries include tenant_id for multi-tenant isolation.
        
        For any configuration change in a multi-tenant environment,
        the history entry should include the tenant_id.
        """
        # Skip configs with empty names or API keys
        assume(len(config.name.strip()) > 0)
        assume(len(config.api_key.strip()) >= 20)
        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)
        assume(len(tenant_id.strip()) >= 10)
        
        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker
        
        async def run_test():
            # Save configuration with tenant_id
            saved_config = await config_manager.save_llm_config(
                config=config,
                user_id=user_id,
                user_name=user_name,
                tenant_id=tenant_id
            )
            
            # Get history for this tenant
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                tenant_id=tenant_id,
                limit=10
            )
            
            # Verify history entry exists
            assert len(history) > 0, "History entry should exist for tenant"
            
            # Verify tenant_id is recorded
            latest_history = history[0]
            assert latest_history.tenant_id == tenant_id, \
                "History should record tenant_id"
        
        asyncio.run(run_test())
    
    @given(
        config=db_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=50, deadline=None)
    def test_history_sanitizes_sensitive_fields(self, config, user_info):
        """
        History entries sanitize sensitive fields.
        
        For any configuration change, sensitive fields (passwords, API keys)
        should be sanitized in the history entry to prevent exposure.
        """
        # Skip configs with empty names or passwords
        assume(len(config.name.strip()) > 0)
        assume(len(config.password.strip()) >= 8)
        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)
        
        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker
        
        async def run_test():
            # Save configuration
            saved_config = await config_manager.save_db_config(
                config=config,
                user_id=user_id,
                user_name=user_name
            )
            
            # Get history
            history = await history_tracker.get_history(
                config_type=ConfigType.DATABASE,
                limit=10
            )
            
            # Verify history entry exists
            assert len(history) > 0, "History entry should exist"
            
            # Verify sensitive fields are sanitized
            latest_history = history[0]
            new_value = latest_history.new_value
            
            # Check that password is redacted
            if "password" in new_value:
                assert new_value["password"] == "[REDACTED]", \
                    "Password should be redacted in history"
            
            if "password_encrypted" in new_value:
                assert new_value["password_encrypted"] == "[REDACTED]", \
                    "Encrypted password should be redacted in history"
            
            # Verify plaintext password is not in password-related fields
            # Note: password might appear in other fields like username, which is acceptable
            password_fields = ["password", "password_encrypted"]
            for field in password_fields:
                if field in new_value and new_value[field] != "[REDACTED]":
                    assert config.password not in str(new_value[field]), \
                        f"Plaintext password should not appear in {field} field"
        
        asyncio.run(run_test())
    
    @given(
        configs=st.lists(llm_config_strategy(), min_size=2, max_size=5),
        user_info=user_info_strategy()
    )
    @settings(max_examples=30, deadline=None)
    def test_multiple_changes_create_multiple_history_entries(self, configs, user_info):
        """
        Multiple configuration changes create multiple history entries.
        
        For any sequence of configuration changes, each change should
        create a separate history entry in chronological order.
        """
        # Skip configs with empty names or API keys
        for config in configs:
            assume(len(config.name.strip()) > 0)
            assume(len(config.api_key.strip()) >= 20)
        
        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)
        
        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker
        
        async def run_test():
            # Save multiple configurations
            for config in configs:
                await config_manager.save_llm_config(
                    config=config,
                    user_id=user_id,
                    user_name=user_name
                )
            
            # Get all history entries
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                limit=100
            )
            
            # Verify we have at least as many history entries as configs
            assert len(history) >= len(configs), \
                "Each configuration change should create a history entry"
            
            # Verify history entries are in chronological order (most recent first)
            for i in range(len(history) - 1):
                assert history[i].created_at >= history[i + 1].created_at, \
                    "History entries should be in chronological order"
        
        asyncio.run(run_test())
    
    @given(
        config=llm_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=50, deadline=None)
    def test_history_entry_has_all_required_fields(self, config, user_info):
        """
        History entries contain all required fields.
        
        For any configuration change, the history entry should contain:
        - id (unique identifier)
        - config_type
        - old_value
        - new_value
        - user_id
        - user_name
        - created_at
        - tenant_id (optional)
        - config_id (optional)
        """
        # Skip configs with empty names or API keys
        assume(len(config.name.strip()) > 0)
        assume(len(config.api_key.strip()) >= 20)
        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)
        
        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker
        
        async def run_test():
            # Save configuration
            saved_config = await config_manager.save_llm_config(
                config=config,
                user_id=user_id,
                user_name=user_name
            )
            
            # Get history
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                limit=1
            )
            
            # Verify history entry exists
            assert len(history) > 0, "History entry should exist"
            
            # Verify all required fields are present
            latest_history = history[0]
            
            assert latest_history.id is not None, "History should have id"
            assert latest_history.config_type is not None, "History should have config_type"
            assert latest_history.new_value is not None, "History should have new_value"
            assert latest_history.user_id is not None, "History should have user_id"
            assert latest_history.user_name is not None, "History should have user_name"
            assert latest_history.created_at is not None, "History should have created_at"
            
            # Verify field types
            assert isinstance(latest_history.id, str), "History id should be string"
            assert isinstance(latest_history.config_type, ConfigType), \
                "History config_type should be ConfigType enum"
            assert isinstance(latest_history.new_value, dict), \
                "History new_value should be dict"
            assert isinstance(latest_history.user_id, str), "History user_id should be string"
            assert isinstance(latest_history.user_name, str), \
                "History user_name should be string"
            assert isinstance(latest_history.created_at, datetime), \
                "History created_at should be datetime"
        
        asyncio.run(run_test())


# ============================================================================
# Property 19: Configuration Rollback Round-Trip
# ============================================================================

class TestConfigurationRollbackRoundTrip:
    """
    Property 19: Configuration Rollback Round-Trip

    For any configuration rollback operation, the rolled-back configuration
    should exactly match the previous state that was targeted for rollback,
    and a new history entry should be created documenting the rollback.

    **Feature: admin-configuration**
    **Validates: Requirements 6.3**
    """

    @given(
        initial_config=llm_config_strategy(),
        updated_config=llm_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_rollback_restores_exact_previous_state(self, initial_config, updated_config, user_info):
        """
        Rolling back a configuration restores the exact previous state.

        For any configuration that was updated, rolling back to a previous
        version should restore the configuration to that exact state.
        """
        # Skip configs with empty names or API keys
        assume(len(initial_config.name.strip()) > 0)
        assume(len(initial_config.api_key.strip()) >= 20)
        assume(len(updated_config.name.strip()) > 0)
        assume(len(updated_config.api_key.strip()) >= 20)
        # Ensure configs are different
        assume(initial_config.name != updated_config.name or
               initial_config.model_name != updated_config.model_name)

        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)

        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker

        async def run_test():
            # Create initial configuration
            saved_config = await config_manager.save_llm_config(
                config=initial_config,
                user_id=user_id,
                user_name=user_name
            )
            config_id = saved_config.id

            # Update the configuration
            await config_manager.save_llm_config(
                config=updated_config,
                user_id=user_id,
                user_name=user_name,
                config_id=config_id
            )

            # Get history to find the update entry
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                config_id=config_id,
                limit=10
            )

            # Find history entry with old_value (the update operation)
            update_history = None
            for h in history:
                if h.old_value is not None:
                    update_history = h
                    break

            assert update_history is not None, "Should have history entry with old_value"

            # Store the old_value for comparison
            expected_rollback_state = update_history.old_value

            # Perform rollback
            rollback_user_id = str(uuid4())
            rollback_user_name = "rollback_test_user"

            rolled_back_value = await history_tracker.rollback(
                history_id=update_history.id,
                user_id=rollback_user_id,
                user_name=rollback_user_name
            )

            # Verify rollback restores exact previous state
            assert rolled_back_value is not None, "Rollback should return a value"

            # Compare key fields (excluding timestamps and generated IDs)
            assert rolled_back_value.get("name") == expected_rollback_state.get("name"), \
                "Rollback should restore exact name"
            assert rolled_back_value.get("model_name") == expected_rollback_state.get("model_name"), \
                "Rollback should restore exact model_name"
            assert rolled_back_value.get("llm_type") == expected_rollback_state.get("llm_type"), \
                "Rollback should restore exact llm_type"

            # Optional fields should also match
            if "temperature" in expected_rollback_state:
                assert rolled_back_value.get("temperature") == expected_rollback_state.get("temperature"), \
                    "Rollback should restore exact temperature"
            if "max_tokens" in expected_rollback_state:
                assert rolled_back_value.get("max_tokens") == expected_rollback_state.get("max_tokens"), \
                    "Rollback should restore exact max_tokens"

        asyncio.run(run_test())

    @given(
        initial_config=llm_config_strategy(),
        updated_config=llm_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_rollback_creates_new_history_entry(self, initial_config, updated_config, user_info):
        """
        Rolling back creates a new history entry documenting the rollback.

        For any rollback operation, a new history entry should be created
        with the rollback details, timestamp, and user information.
        """
        # Skip configs with empty names or API keys
        assume(len(initial_config.name.strip()) > 0)
        assume(len(initial_config.api_key.strip()) >= 20)
        assume(len(updated_config.name.strip()) > 0)
        assume(len(updated_config.api_key.strip()) >= 20)
        # Ensure configs are different
        assume(initial_config.name != updated_config.name)

        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)

        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker

        async def run_test():
            # Create and update configuration
            saved_config = await config_manager.save_llm_config(
                config=initial_config,
                user_id=user_id,
                user_name=user_name
            )
            config_id = saved_config.id

            await config_manager.save_llm_config(
                config=updated_config,
                user_id=user_id,
                user_name=user_name,
                config_id=config_id
            )

            # Get history to find the update entry
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                config_id=config_id,
                limit=10
            )

            update_history = None
            for h in history:
                if h.old_value is not None:
                    update_history = h
                    break

            assert update_history is not None, "Should have history entry with old_value"

            history_count_before = len(history)

            # Perform rollback
            rollback_user_id = str(uuid4())
            rollback_user_name = "rollback_entry_test_user"

            await history_tracker.rollback(
                history_id=update_history.id,
                user_id=rollback_user_id,
                user_name=rollback_user_name
            )

            # Get history after rollback
            history_after = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                limit=20
            )

            # Should have more history entries
            assert len(history_after) > history_count_before, \
                "Rollback should create new history entry"

            # Most recent entry should be the rollback
            rollback_entry = history_after[0]

            # Verify rollback entry has correct user info
            assert rollback_entry.user_id == rollback_user_id, \
                "Rollback entry should have rollback user_id"
            assert rollback_entry.user_name == rollback_user_name, \
                "Rollback entry should have rollback user_name"

            # Verify timestamp is recent
            time_diff = datetime.utcnow() - rollback_entry.created_at
            assert time_diff.total_seconds() < 5, \
                "Rollback entry timestamp should be recent"

            # Verify new_value matches the rolled-back state
            assert rollback_entry.new_value is not None, \
                "Rollback entry should have new_value"

        asyncio.run(run_test())

    @given(
        config=llm_config_strategy(),
        updates=st.lists(llm_config_strategy(), min_size=2, max_size=4),
        user_info=user_info_strategy()
    )
    @settings(max_examples=50, deadline=None)
    def test_multiple_rollbacks_to_different_versions(self, config, updates, user_info):
        """
        Multiple rollbacks to different versions work correctly.

        For any sequence of configuration changes, rolling back to
        any specific version should restore that exact version.
        """
        # Skip configs with empty names or API keys
        assume(len(config.name.strip()) > 0)
        assume(len(config.api_key.strip()) >= 20)
        for update in updates:
            assume(len(update.name.strip()) > 0)
            assume(len(update.api_key.strip()) >= 20)

        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)

        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker

        async def run_test():
            # Create initial configuration
            saved_config = await config_manager.save_llm_config(
                config=config,
                user_id=user_id,
                user_name=user_name
            )
            config_id = saved_config.id

            # Apply all updates
            for update in updates:
                await config_manager.save_llm_config(
                    config=update,
                    user_id=user_id,
                    user_name=user_name,
                    config_id=config_id
                )

            # Get full history
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                config_id=config_id,
                limit=20
            )

            # Find entries with old_value (these are updates we can roll back)
            rollbackable_entries = [h for h in history if h.old_value is not None]

            if len(rollbackable_entries) >= 2:
                # Pick a random entry to roll back to
                target_entry = rollbackable_entries[1]  # Not the most recent
                expected_state = target_entry.old_value

                # Perform rollback
                rollback_user_id = str(uuid4())
                rolled_back = await history_tracker.rollback(
                    history_id=target_entry.id,
                    user_id=rollback_user_id,
                    user_name="multi_rollback_user"
                )

                # Verify rolled back to correct version
                assert rolled_back is not None, "Rollback should return value"
                assert rolled_back.get("name") == expected_state.get("name"), \
                    "Multi-rollback should restore correct version"

        asyncio.run(run_test())

    @given(
        config=db_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=50, deadline=None)
    def test_rollback_works_for_database_configs(self, config, user_info):
        """
        Rollback works correctly for database configurations.

        For any database configuration, rollback should restore
        the exact previous state including connection parameters.
        """
        # Skip configs with empty names or passwords
        assume(len(config.name.strip()) > 0)
        assume(len(config.password.strip()) >= 8)

        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)

        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker

        async def run_test():
            # Create initial configuration
            saved_config = await config_manager.save_db_config(
                config=config,
                user_id=user_id,
                user_name=user_name
            )
            config_id = saved_config.id
            original_name = config.name

            # Update the configuration
            updated_config = DBConfigCreate(
                name=f"{config.name}_updated",
                db_type=config.db_type,
                host=config.host,
                port=config.port + 1,  # Change port
                database=config.database,
                username=config.username,
                password=config.password,
                is_readonly=not config.is_readonly,  # Toggle readonly
                ssl_enabled=config.ssl_enabled
            )

            await config_manager.save_db_config(
                config=updated_config,
                user_id=user_id,
                user_name=user_name,
                config_id=config_id
            )

            # Get history
            history = await history_tracker.get_history(
                config_type=ConfigType.DATABASE,
                config_id=config_id,
                limit=10
            )

            # Find update entry
            update_history = None
            for h in history:
                if h.old_value is not None:
                    update_history = h
                    break

            if update_history:
                expected_state = update_history.old_value

                # Perform rollback
                rolled_back = await history_tracker.rollback(
                    history_id=update_history.id,
                    user_id=str(uuid4()),
                    user_name="db_rollback_user"
                )

                # Verify database-specific fields are restored
                assert rolled_back is not None, "Rollback should return value"
                assert rolled_back.get("name") == expected_state.get("name"), \
                    "Database config name should be restored"
                assert rolled_back.get("port") == expected_state.get("port"), \
                    "Database config port should be restored"
                assert rolled_back.get("is_readonly") == expected_state.get("is_readonly"), \
                    "Database config is_readonly should be restored"

        asyncio.run(run_test())

    @given(
        config=llm_config_strategy(),
        updated_config=llm_config_strategy(),
        user_info=user_info_strategy()
    )
    @settings(max_examples=50, deadline=None)
    def test_rollback_preserves_sensitive_field_security(self, config, updated_config, user_info):
        """
        Rollback preserves security of sensitive fields.

        When rolling back a configuration, sensitive fields like API keys
        should remain properly encrypted/protected in the restored state.
        """
        # Skip configs with empty names or API keys
        assume(len(config.name.strip()) > 0)
        assume(len(config.api_key.strip()) >= 20)
        assume(len(updated_config.name.strip()) > 0)
        assume(len(updated_config.api_key.strip()) >= 20)
        assume(config.api_key != updated_config.api_key)  # Different API keys

        user_id, user_name = user_info
        assume(len(user_id.strip()) >= 10)
        assume(len(user_name.strip()) >= 3)

        # Create fresh instances for this test
        config_manager = ConfigManager()
        config_manager.clear_in_memory_storage()
        history_tracker = config_manager._history_tracker

        async def run_test():
            # Create initial configuration
            saved_config = await config_manager.save_llm_config(
                config=config,
                user_id=user_id,
                user_name=user_name
            )
            config_id = saved_config.id

            # Update with different API key
            await config_manager.save_llm_config(
                config=updated_config,
                user_id=user_id,
                user_name=user_name,
                config_id=config_id
            )

            # Get history
            history = await history_tracker.get_history(
                config_type=ConfigType.LLM,
                config_id=config_id,
                limit=10
            )

            # Find update entry
            update_history = None
            for h in history:
                if h.old_value is not None:
                    update_history = h
                    break

            if update_history:
                # Check that API key is redacted in history
                old_value = update_history.old_value
                new_value = update_history.new_value

                # API key should be redacted in history
                if "api_key" in old_value:
                    assert old_value["api_key"] == "[REDACTED]" or \
                           "encrypted" in str(old_value.get("api_key_encrypted", "")), \
                        "API key should be redacted in history old_value"

                if "api_key" in new_value:
                    assert new_value["api_key"] == "[REDACTED]" or \
                           "encrypted" in str(new_value.get("api_key_encrypted", "")), \
                        "API key should be redacted in history new_value"

                # Perform rollback
                rolled_back = await history_tracker.rollback(
                    history_id=update_history.id,
                    user_id=str(uuid4()),
                    user_name="security_test_user"
                )

                # Rolled back state should also have API key protected
                if rolled_back and "api_key" in rolled_back:
                    # Should not be plaintext original API key
                    assert rolled_back["api_key"] == "[REDACTED]" or \
                           rolled_back["api_key"] != config.api_key, \
                        "Rolled back API key should be protected"

        asyncio.run(run_test())


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
