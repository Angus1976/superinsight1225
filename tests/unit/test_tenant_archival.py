"""
Unit tests for tenant configuration archival functionality.

Tests the archive_tenant_configs method in ConfigManager to ensure
proper archival of all tenant configurations on deletion.

**Feature: admin-configuration**
**Validates: Requirements 7.6**
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.admin.config_manager import ConfigManager
from src.admin.schemas import (
    LLMConfigCreate,
    DBConfigCreate,
    ConfigType,
)


@pytest.fixture
def config_manager():
    """Create a ConfigManager instance for testing."""
    return ConfigManager(require_tenant_id=False)


@pytest.fixture
def tenant_id():
    """Generate a test tenant ID."""
    return str(uuid4())


@pytest.fixture
def user_id():
    """Generate a test user ID."""
    return str(uuid4())


@pytest.mark.asyncio
async def test_archive_tenant_configs_empty_tenant(config_manager, tenant_id, user_id):
    """
    Test archiving configurations for a tenant with no configurations.
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.6**
    """
    # Archive configurations for empty tenant
    result = await config_manager.archive_tenant_configs(
        tenant_id=tenant_id,
        user_id=user_id,
        user_name="Test User",
        reason="Test archival",
    )
    
    # Should return zero counts
    assert result["llm"] == 0
    assert result["database"] == 0
    assert result["sync_strategy"] == 0
    assert result["third_party"] == 0
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_archive_tenant_configs_with_llm_configs(config_manager, tenant_id, user_id):
    """
    Test archiving LLM configurations for a tenant.
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.6**
    """
    # Create LLM configurations
    llm_config1 = LLMConfigCreate(
        name="OpenAI Config",
        llm_type="openai",
        model_name="gpt-4",
        api_key="test-key-1",
        api_endpoint="https://api.openai.com/v1",
    )
    
    llm_config2 = LLMConfigCreate(
        name="Qianwen Config",
        llm_type="qianwen",
        model_name="qwen-turbo",
        api_key="test-key-2",
        api_endpoint="https://dashscope.aliyuncs.com/api/v1",
    )
    
    # Save configurations
    saved1 = await config_manager.save_llm_config(
        config=llm_config1,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant_id,
    )
    
    saved2 = await config_manager.save_llm_config(
        config=llm_config2,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant_id,
    )
    
    # Verify configurations exist
    configs = await config_manager.list_llm_configs(tenant_id=tenant_id, active_only=False)
    assert len(configs) == 2
    
    # Archive tenant configurations
    result = await config_manager.archive_tenant_configs(
        tenant_id=tenant_id,
        user_id=user_id,
        user_name="Test User",
        reason="Tenant deletion",
    )
    
    # Verify archival counts
    assert result["llm"] == 2
    assert result["total"] == 2
    
    # Verify configurations are deleted
    configs_after = await config_manager.list_llm_configs(tenant_id=tenant_id, active_only=False)
    assert len(configs_after) == 0
    
    # Verify configurations cannot be retrieved
    config1_after = await config_manager.get_llm_config(saved1.id, tenant_id=tenant_id)
    config2_after = await config_manager.get_llm_config(saved2.id, tenant_id=tenant_id)
    assert config1_after is None
    assert config2_after is None


@pytest.mark.asyncio
async def test_archive_tenant_configs_with_db_configs(config_manager, tenant_id, user_id):
    """
    Test archiving database configurations for a tenant.
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.6**
    """
    # Create database configurations
    db_config1 = DBConfigCreate(
        name="PostgreSQL DB",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser",
        password="testpass",
    )
    
    db_config2 = DBConfigCreate(
        name="MySQL DB",
        db_type="mysql",
        host="localhost",
        port=3306,
        database="testdb",
        username="testuser",
        password="testpass",
    )
    
    # Save configurations
    saved1 = await config_manager.save_db_config(
        config=db_config1,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant_id,
    )
    
    saved2 = await config_manager.save_db_config(
        config=db_config2,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant_id,
    )
    
    # Verify configurations exist
    configs = await config_manager.list_db_configs(tenant_id=tenant_id, active_only=False)
    assert len(configs) == 2
    
    # Archive tenant configurations
    result = await config_manager.archive_tenant_configs(
        tenant_id=tenant_id,
        user_id=user_id,
        user_name="Test User",
        reason="Tenant deletion",
    )
    
    # Verify archival counts
    assert result["database"] == 2
    assert result["total"] == 2
    
    # Verify configurations are deleted
    configs_after = await config_manager.list_db_configs(tenant_id=tenant_id, active_only=False)
    assert len(configs_after) == 0


@pytest.mark.asyncio
async def test_archive_tenant_configs_mixed_types(config_manager, tenant_id, user_id):
    """
    Test archiving multiple configuration types for a tenant.
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.6**
    """
    # Create LLM configuration
    llm_config = LLMConfigCreate(
        name="OpenAI Config",
        llm_type="openai",
        model_name="gpt-4",
        api_key="test-key",
        api_endpoint="https://api.openai.com/v1",
    )
    
    # Create database configuration
    db_config = DBConfigCreate(
        name="PostgreSQL DB",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser",
        password="testpass",
    )
    
    # Save configurations
    await config_manager.save_llm_config(
        config=llm_config,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant_id,
    )
    
    await config_manager.save_db_config(
        config=db_config,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant_id,
    )
    
    # Archive tenant configurations
    result = await config_manager.archive_tenant_configs(
        tenant_id=tenant_id,
        user_id=user_id,
        user_name="Test User",
        reason="Tenant deletion",
    )
    
    # Verify archival counts
    assert result["llm"] == 1
    assert result["database"] == 1
    assert result["total"] == 2
    
    # Verify all configurations are deleted
    llm_configs = await config_manager.list_llm_configs(tenant_id=tenant_id, active_only=False)
    db_configs = await config_manager.list_db_configs(tenant_id=tenant_id, active_only=False)
    assert len(llm_configs) == 0
    assert len(db_configs) == 0


@pytest.mark.asyncio
async def test_archive_tenant_configs_requires_tenant_id(config_manager, user_id):
    """
    Test that archival requires a tenant_id.
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.6**
    """
    # Attempt to archive without tenant_id
    with pytest.raises(ValueError, match="tenant_id is required"):
        await config_manager.archive_tenant_configs(
            tenant_id=None,
            user_id=user_id,
            user_name="Test User",
        )
    
    # Attempt to archive with empty tenant_id
    with pytest.raises(ValueError, match="tenant_id is required"):
        await config_manager.archive_tenant_configs(
            tenant_id="",
            user_id=user_id,
            user_name="Test User",
        )


@pytest.mark.asyncio
async def test_archive_tenant_configs_preserves_other_tenants(config_manager, user_id):
    """
    Test that archiving one tenant doesn't affect other tenants.
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.1, 7.2, 7.3, 7.6**
    """
    tenant1_id = str(uuid4())
    tenant2_id = str(uuid4())
    
    # Create configurations for tenant 1
    llm_config1 = LLMConfigCreate(
        name="Tenant 1 Config",
        llm_type="openai",
        model_name="gpt-4",
        api_key="test-key-1",
        api_endpoint="https://api.openai.com/v1",
    )
    
    await config_manager.save_llm_config(
        config=llm_config1,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant1_id,
    )
    
    # Create configurations for tenant 2
    llm_config2 = LLMConfigCreate(
        name="Tenant 2 Config",
        llm_type="zhipu",
        model_name="glm-4",
        api_key="test-key-2",
        api_endpoint="https://open.bigmodel.cn/api/paas/v4",
    )
    
    await config_manager.save_llm_config(
        config=llm_config2,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant2_id,
    )
    
    # Archive tenant 1 configurations
    result = await config_manager.archive_tenant_configs(
        tenant_id=tenant1_id,
        user_id=user_id,
        user_name="Test User",
        reason="Tenant 1 deletion",
    )
    
    # Verify tenant 1 configurations are deleted
    tenant1_configs = await config_manager.list_llm_configs(tenant_id=tenant1_id, active_only=False)
    assert len(tenant1_configs) == 0
    
    # Verify tenant 2 configurations are preserved
    tenant2_configs = await config_manager.list_llm_configs(tenant_id=tenant2_id, active_only=False)
    assert len(tenant2_configs) == 1
    assert tenant2_configs[0].name == "Tenant 2 Config"


@pytest.mark.asyncio
async def test_archive_tenant_configs_records_history(config_manager, tenant_id, user_id):
    """
    Test that archival records configuration history for compliance.
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.6, 6.1**
    """
    # Create LLM configuration
    llm_config = LLMConfigCreate(
        name="Test Config",
        llm_type="openai",
        model_name="gpt-4",
        api_key="test-key",
        api_endpoint="https://api.openai.com/v1",
    )
    
    saved = await config_manager.save_llm_config(
        config=llm_config,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant_id,
    )
    
    # Archive tenant configurations
    await config_manager.archive_tenant_configs(
        tenant_id=tenant_id,
        user_id=user_id,
        user_name="Archive User",
        reason="Compliance archival",
    )
    
    # Verify history was recorded
    history = await config_manager._history_tracker.get_history(
        tenant_id=tenant_id,
        config_type=ConfigType.LLM,
    )
    
    # Should have 2 entries: 1 for creation, 1 for deletion
    assert len(history) >= 2
    
    # Find the deletion entry
    deletion_entries = [
        h for h in history
        if h.new_value.get("_deleted") is True
        and h.new_value.get("id") == saved.id
    ]
    
    assert len(deletion_entries) == 1
    deletion_entry = deletion_entries[0]
    
    # Verify deletion entry details
    assert deletion_entry.config_type == ConfigType.LLM
    assert deletion_entry.user_name == "Archive User"
    assert deletion_entry.tenant_id == tenant_id
    assert deletion_entry.old_value is not None  # Should have old configuration
    assert deletion_entry.new_value["_deleted"] is True


@pytest.mark.asyncio
async def test_archive_tenant_configs_custom_reason(config_manager, tenant_id, user_id):
    """
    Test that archival accepts custom reason for compliance tracking.
    
    **Feature: admin-configuration**
    **Validates: Requirements 7.6**
    """
    # Create configuration
    llm_config = LLMConfigCreate(
        name="Test Config",
        llm_type="openai",
        model_name="gpt-4",
        api_key="test-key",
        api_endpoint="https://api.openai.com/v1",
    )
    
    await config_manager.save_llm_config(
        config=llm_config,
        user_id=user_id,
        user_name="Test User",
        tenant_id=tenant_id,
    )
    
    # Archive with custom reason
    custom_reason = "GDPR compliance - user requested data deletion"
    result = await config_manager.archive_tenant_configs(
        tenant_id=tenant_id,
        user_id=user_id,
        user_name="Compliance Officer",
        reason=custom_reason,
    )
    
    # Verify archival succeeded
    assert result["total"] == 1
    
    # Note: In a full implementation with database, we would verify
    # the reason is stored in the history record
