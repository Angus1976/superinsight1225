"""
Integration test for LLM Application Binding multi-tenant configuration.

This module tests multi-tenant configuration hierarchy:
- Global default configurations (tenant_id = NULL)
- Tenant-specific configurations
- Application-specific bindings
- Correct hierarchy resolution: application > tenant > global
- Override behavior at each level

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.9, 18.10
"""

import pytest
from uuid import uuid4

from src.ai.llm_schemas import CloudConfig
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding
from src.ai.application_llm_manager import ApplicationLLMManager
from src.ai.cache_manager import CacheManager
from src.ai.encryption_service import get_encryption_service


@pytest.fixture
def setup_multi_tenant_configs(db_session):
    """
    Create multi-tenant test setup with global, tenant, and application configs.
    
    Sets up:
    - 2 applications: "app1" and "app2"
    - Global LLM config (tenant_id = NULL)
    - Tenant A LLM config
    - Tenant B LLM config
    - Application-specific binding for app1 in Tenant A
    """
    encryption = get_encryption_service()
    
    # Create applications
    app1 = LLMApplication(
        id=uuid4(),
        code="app1",
        name="Application 1",
        is_active=True
    )
    app2 = LLMApplication(
        id=uuid4(),
        code="app2",
        name="Application 2",
        is_active=True
    )
    db_session.add_all([app1, app2])
    db_session.flush()
    
    # Create global LLM config (tenant_id = NULL)
    global_api_key = encryption.encrypt("global-api-key")
    global_config = LLMConfiguration(
        id=uuid4(),
        name="Global Default",
        default_method="openai",
        is_active=True,
        tenant_id=None,  # Global
        created_by=None,
        updated_by=None,
        config_data={
            "provider": "openai",
            "api_key_encrypted": global_api_key,
            "base_url": "https://api.global.example.com/v1",
            "model_name": "gpt-4-global"
        }
    )
    db_session.add(global_config)
    db_session.flush()
    
    # Create tenant A config
    tenant_a_id = uuid4()
    tenant_a_api_key = encryption.encrypt("tenant-a-api-key")
    tenant_a_config = LLMConfiguration(
        id=uuid4(),
        name="Tenant A Config",
        default_method="openai",
        is_active=True,
        tenant_id=tenant_a_id,
        created_by=None,
        updated_by=None,
        config_data={
            "provider": "openai",
            "api_key_encrypted": tenant_a_api_key,
            "base_url": "https://api.tenant-a.example.com/v1",
            "model_name": "gpt-4-tenant-a"
        }
    )
    db_session.add(tenant_a_config)
    db_session.flush()
    
    # Create tenant B config
    tenant_b_id = uuid4()
    tenant_b_api_key = encryption.encrypt("tenant-b-api-key")
    tenant_b_config = LLMConfiguration(
        id=uuid4(),
        name="Tenant B Config",
        default_method="openai",
        is_active=True,
        tenant_id=tenant_b_id,
        created_by=None,
        updated_by=None,
        config_data={
            "provider": "openai",
            "api_key_encrypted": tenant_b_api_key,
            "base_url": "https://api.tenant-b.example.com/v1",
            "model_name": "gpt-4-tenant-b"
        }
    )
    db_session.add(tenant_b_config)
    db_session.flush()
    
    # Create application-specific binding for app1 in Tenant A
    app_specific_api_key = encryption.encrypt("app1-tenant-a-api-key")
    app_specific_config = LLMConfiguration(
        id=uuid4(),
        name="App1 Tenant A Config",
        default_method="openai",
        is_active=True,
        tenant_id=tenant_a_id,
        created_by=None,
        updated_by=None,
        config_data={
            "provider": "openai",
            "api_key_encrypted": app_specific_api_key,
            "base_url": "https://api.app1-tenant-a.example.com/v1",
            "model_name": "gpt-4-app1-tenant-a"
        }
    )
    db_session.add(app_specific_config)
    db_session.flush()
    
    app1_binding = LLMApplicationBinding(
        id=uuid4(),
        llm_config_id=app_specific_config.id,
        application_id=app1.id,
        priority=1,
        max_retries=3,
        timeout_seconds=30,
        is_active=True
    )
    db_session.add(app1_binding)
    
    # Create global bindings for both apps
    global_binding_app1 = LLMApplicationBinding(
        id=uuid4(),
        llm_config_id=global_config.id,
        application_id=app1.id,
        priority=2,  # Lower priority than app-specific
        max_retries=3,
        timeout_seconds=30,
        is_active=True
    )
    global_binding_app2 = LLMApplicationBinding(
        id=uuid4(),
        llm_config_id=global_config.id,
        application_id=app2.id,
        priority=1,
        max_retries=3,
        timeout_seconds=30,
        is_active=True
    )
    db_session.add_all([global_binding_app1, global_binding_app2])
    
    # Create tenant-level bindings
    tenant_a_binding_app2 = LLMApplicationBinding(
        id=uuid4(),
        llm_config_id=tenant_a_config.id,
        application_id=app2.id,
        priority=1,
        max_retries=3,
        timeout_seconds=30,
        is_active=True
    )
    tenant_b_binding_app2 = LLMApplicationBinding(
        id=uuid4(),
        llm_config_id=tenant_b_config.id,
        application_id=app2.id,
        priority=1,
        max_retries=3,
        timeout_seconds=30,
        is_active=True
    )
    db_session.add_all([tenant_a_binding_app2, tenant_b_binding_app2])
    
    db_session.commit()
    
    return {
        "app1": app1,
        "app2": app2,
        "global_config": global_config,
        "tenant_a_id": tenant_a_id,
        "tenant_a_config": tenant_a_config,
        "tenant_b_id": tenant_b_id,
        "tenant_b_config": tenant_b_config,
        "app_specific_config": app_specific_config
    }


@pytest.mark.asyncio
class TestConfigurationHierarchy:
    """Test configuration hierarchy resolution."""
    
    async def test_application_binding_overrides_tenant(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that application-specific binding takes priority over tenant config.
        
        Validates: Requirements 18.4
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        tenant_a_id = str(setup_multi_tenant_configs["tenant_a_id"])
        
        # Load config for app1 in Tenant A
        configs = await manager.get_llm_config(
            application_code="app1",
            tenant_id=tenant_a_id
        )
        
        # Should get application-specific config (highest priority)
        assert len(configs) >= 1
        assert configs[0].openai_api_key == "app1-tenant-a-api-key"
        assert configs[0].openai_model == "gpt-4-app1-tenant-a"
    
    async def test_tenant_config_overrides_global(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that tenant-specific config takes priority over global config.
        
        Validates: Requirements 18.4, 18.6
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        tenant_a_id = str(setup_multi_tenant_configs["tenant_a_id"])
        
        # Load config for app2 in Tenant A (no app-specific binding)
        configs = await manager.get_llm_config(
            application_code="app2",
            tenant_id=tenant_a_id
        )
        
        # Should get tenant-specific config
        assert len(configs) >= 1
        assert configs[0].openai_api_key == "tenant-a-api-key"
        assert configs[0].openai_model == "gpt-4-tenant-a"
    
    async def test_global_config_as_fallback(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that global config is used when no tenant/app config exists.
        
        Validates: Requirements 18.7
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Load config for app2 with no tenant (should use global)
        configs = await manager.get_llm_config(
            application_code="app2",
            tenant_id=None
        )
        
        # Should get global config
        assert len(configs) >= 1
        assert configs[0].openai_api_key == "global-api-key"
        assert configs[0].openai_model == "gpt-4-global"
    
    async def test_complete_hierarchy_resolution(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test complete hierarchy: application > tenant > global.
        
        Validates: Requirements 18.1, 18.2, 18.3, 18.4
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        tenant_a_id = str(setup_multi_tenant_configs["tenant_a_id"])
        
        # Test app1 in Tenant A (has app-specific binding)
        configs_app1_a = await manager.get_llm_config(
            application_code="app1",
            tenant_id=tenant_a_id
        )
        assert configs_app1_a[0].openai_api_key == "app1-tenant-a-api-key"
        
        # Test app2 in Tenant A (has tenant-level binding)
        configs_app2_a = await manager.get_llm_config(
            application_code="app2",
            tenant_id=tenant_a_id
        )
        assert configs_app2_a[0].openai_api_key == "tenant-a-api-key"
        
        # Test app2 with no tenant (uses global)
        configs_app2_global = await manager.get_llm_config(
            application_code="app2",
            tenant_id=None
        )
        assert configs_app2_global[0].openai_api_key == "global-api-key"


@pytest.mark.asyncio
class TestTenantIsolation:
    """Test tenant isolation in configuration."""
    
    async def test_tenant_a_cannot_see_tenant_b_config(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that Tenant A cannot access Tenant B's configuration.
        
        Validates: Requirements 18.9
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        tenant_a_id = str(setup_multi_tenant_configs["tenant_a_id"])
        
        # Load config for app2 in Tenant A
        configs = await manager.get_llm_config(
            application_code="app2",
            tenant_id=tenant_a_id
        )
        
        # Should get Tenant A config, not Tenant B
        assert len(configs) >= 1
        assert configs[0].openai_api_key == "tenant-a-api-key"
        assert configs[0].openai_api_key != "tenant-b-api-key"
    
    async def test_tenant_b_has_own_config(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that Tenant B has its own isolated configuration.
        
        Validates: Requirements 18.9
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        tenant_b_id = str(setup_multi_tenant_configs["tenant_b_id"])
        
        # Load config for app2 in Tenant B
        configs = await manager.get_llm_config(
            application_code="app2",
            tenant_id=tenant_b_id
        )
        
        # Should get Tenant B config
        assert len(configs) >= 1
        assert configs[0].openai_api_key == "tenant-b-api-key"
        assert configs[0].openai_model == "gpt-4-tenant-b"
    
    async def test_different_tenants_different_configs(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that different tenants get different configurations.
        
        Validates: Requirements 18.9
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        tenant_a_id = str(setup_multi_tenant_configs["tenant_a_id"])
        tenant_b_id = str(setup_multi_tenant_configs["tenant_b_id"])
        
        # Load config for same app in different tenants
        configs_a = await manager.get_llm_config(
            application_code="app2",
            tenant_id=tenant_a_id
        )
        configs_b = await manager.get_llm_config(
            application_code="app2",
            tenant_id=tenant_b_id
        )
        
        # Should be different
        assert configs_a[0].openai_api_key != configs_b[0].openai_api_key
        assert configs_a[0].openai_model != configs_b[0].openai_model


@pytest.mark.asyncio
class TestOverrideBehavior:
    """Test override behavior at different levels."""
    
    async def test_tenant_override_does_not_affect_other_tenants(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that tenant-level override doesn't affect other tenants.
        
        Validates: Requirements 18.9
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        tenant_a_id = str(setup_multi_tenant_configs["tenant_a_id"])
        tenant_b_id = str(setup_multi_tenant_configs["tenant_b_id"])
        
        # Update Tenant A config
        tenant_a_config = setup_multi_tenant_configs["tenant_a_config"]
        new_api_key = encryption.encrypt("tenant-a-updated-key")
        tenant_a_config.config_data = {
            "provider": "openai",
            "api_key_encrypted": new_api_key,
            "base_url": "https://api.tenant-a-updated.example.com/v1",
            "model_name": "gpt-4-tenant-a-updated"
        }
        db_session.commit()
        
        # Invalidate cache
        await manager.invalidate_cache(application_code="app2", broadcast=False)
        
        # Tenant A should see updated config
        configs_a = await manager.get_llm_config(
            application_code="app2",
            tenant_id=tenant_a_id
        )
        assert configs_a[0].openai_api_key == "tenant-a-updated-key"
        
        # Tenant B should still see original config
        configs_b = await manager.get_llm_config(
            application_code="app2",
            tenant_id=tenant_b_id
        )
        assert configs_b[0].openai_api_key == "tenant-b-api-key"
    
    async def test_application_override_does_not_affect_other_apps(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that application-level override doesn't affect other applications.
        
        Validates: Requirements 18.10
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        tenant_a_id = str(setup_multi_tenant_configs["tenant_a_id"])
        
        # Update app1-specific config
        app_config = setup_multi_tenant_configs["app_specific_config"]
        new_api_key = encryption.encrypt("app1-updated-key")
        app_config.config_data = {
            "provider": "openai",
            "api_key_encrypted": new_api_key,
            "base_url": "https://api.app1-updated.example.com/v1",
            "model_name": "gpt-4-app1-updated"
        }
        db_session.commit()
        
        # Invalidate cache
        await manager.invalidate_cache(application_code="app1", broadcast=False)
        
        # App1 should see updated config
        configs_app1 = await manager.get_llm_config(
            application_code="app1",
            tenant_id=tenant_a_id
        )
        assert configs_app1[0].openai_api_key == "app1-updated-key"
        
        # App2 should still see tenant config
        configs_app2 = await manager.get_llm_config(
            application_code="app2",
            tenant_id=tenant_a_id
        )
        assert configs_app2[0].openai_api_key == "tenant-a-api-key"
    
    async def test_global_update_affects_all_without_overrides(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that global config update affects all tenants without overrides.
        
        Validates: Requirements 18.1
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Update global config
        global_config = setup_multi_tenant_configs["global_config"]
        new_api_key = encryption.encrypt("global-updated-key")
        global_config.config_data = {
            "provider": "openai",
            "api_key_encrypted": new_api_key,
            "base_url": "https://api.global-updated.example.com/v1",
            "model_name": "gpt-4-global-updated"
        }
        db_session.commit()
        
        # Invalidate cache
        await manager.invalidate_cache(application_code=None, broadcast=False)
        
        # App2 with no tenant should see updated global config
        configs = await manager.get_llm_config(
            application_code="app2",
            tenant_id=None
        )
        assert configs[0].openai_api_key == "global-updated-key"


@pytest.mark.asyncio
class TestMultiTenantEdgeCases:
    """Test edge cases in multi-tenant configuration."""
    
    async def test_nonexistent_tenant_uses_global(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that nonexistent tenant falls back to global config.
        
        Validates: Requirements 18.7
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        # Use nonexistent tenant ID
        nonexistent_tenant_id = str(uuid4())
        
        # Should fall back to global config
        configs = await manager.get_llm_config(
            application_code="app2",
            tenant_id=nonexistent_tenant_id
        )
        
        assert len(configs) >= 1
        assert configs[0].openai_api_key == "global-api-key"
    
    async def test_multiple_bindings_with_priorities(
        self, db_session, setup_multi_tenant_configs
    ):
        """
        Test that multiple bindings are ordered by priority.
        
        Validates: Requirements 18.8
        """
        encryption = get_encryption_service()
        cache_manager = CacheManager(redis_client=None, local_ttl=300)
        manager = ApplicationLLMManager(
            db_session=db_session,
            cache_manager=cache_manager,
            encryption_service=encryption
        )
        
        tenant_a_id = str(setup_multi_tenant_configs["tenant_a_id"])
        
        # App1 in Tenant A has both app-specific (priority 1) and global (priority 2)
        configs = await manager.get_llm_config(
            application_code="app1",
            tenant_id=tenant_a_id
        )
        
        # Should have multiple configs in priority order
        assert len(configs) >= 2
        assert configs[0].openai_api_key == "app1-tenant-a-api-key"  # Priority 1
        assert configs[1].openai_api_key == "global-api-key"  # Priority 2
