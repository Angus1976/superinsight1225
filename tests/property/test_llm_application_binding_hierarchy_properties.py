"""
Property-based tests for LLM Application Binding - Configuration Loading Hierarchy.

Uses Hypothesis library for property testing with minimum 100 iterations.
Tests Property 9 from the LLM Application Binding design document.

Feature: llm-application-binding
Property: 9 - Configuration Loading Hierarchy
"""

import pytest
import os
from uuid import uuid4
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import MagicMock, patch

from src.ai.application_llm_manager import ApplicationLLMManager
from src.ai.cache_manager import CacheManager
from src.ai.encryption_service import EncryptionService
from src.ai.llm_schemas import CloudConfig
from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding


# ==================== Custom Strategies ====================

# Strategy for application codes
application_code_strategy = st.sampled_from([
    'structuring', 'knowledge_graph', 'ai_assistant',
    'semantic_analysis', 'rag_agent', 'text_to_sql'
])

# Strategy for tenant IDs (UUID strings or None)
tenant_id_strategy = st.one_of(
    st.none(),
    st.uuids().map(str)
)

# Strategy for provider types
provider_strategy = st.sampled_from(['openai', 'azure', 'anthropic', 'ollama', 'custom'])

# Strategy for model names
model_name_strategy = st.sampled_from([
    'gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo',
    'claude-3-opus', 'claude-3-sonnet',
    'llama2', 'mistral'
])

# Strategy for API keys
api_key_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N')),
    min_size=20,
    max_size=50
)

# Strategy for base URLs
base_url_strategy = st.sampled_from([
    'https://api.openai.com/v1',
    'https://api.anthropic.com/v1',
    'http://localhost:11434',
    'https://custom-api.example.com/v1'
])

# Strategy for priority values
priority_strategy = st.integers(min_value=1, max_value=99)


# ==================== Fixtures ====================

@pytest.fixture
def mock_db_session():
    """Sync session mock — ``ApplicationLLMManager._execute`` uses sync ``execute`` unless ``AsyncSession``."""
    session = MagicMock()

    def mock_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        scalars = MagicMock()
        scalars.all.return_value = []
        result.scalars.return_value = scalars
        return result

    session.execute = mock_execute
    return session


@pytest.fixture
def cache_manager():
    """Create a CacheManager instance without Redis."""
    return CacheManager(redis_client=None, local_ttl=300, max_memory_mb=100)


@pytest.fixture
def encryption_service():
    """Create an EncryptionService instance."""
    # Set a test encryption key (32 bytes base64 encoded)
    test_key = "5QoEylTqwm1/eHusi1j8tWRV3dexqXB50c/AKPyyefE="  # base64 encoded 32 bytes
    with patch.dict(os.environ, {'LLM_ENCRYPTION_KEY': test_key}):
        return EncryptionService()


@pytest.fixture
def app_llm_manager(mock_db_session, cache_manager, encryption_service):
    """Create an ApplicationLLMManager instance."""
    manager = ApplicationLLMManager(
        db_session=mock_db_session,
        cache_manager=cache_manager,
        encryption_service=encryption_service
    )
    
    # Mock the encryption service decrypt method to return the input as-is
    encryption_service.decrypt = MagicMock(side_effect=lambda x: x)
    
    return manager


# ==================== Helper Functions ====================

def create_mock_application(code: str) -> LLMApplication:
    """Create a mock LLMApplication."""
    app = MagicMock(spec=LLMApplication)
    app.id = uuid4()
    app.code = code
    app.name = code.replace('_', ' ').title()
    app.is_active = True
    return app


def create_mock_config(
    tenant_id: str = None,
    provider: str = 'openai',
    model_name: str = 'gpt-3.5-turbo',
    api_key: str = 'test_key',
    base_url: str = 'https://api.openai.com/v1'
) -> LLMConfiguration:
    """Create a mock LLMConfiguration."""
    config = MagicMock(spec=LLMConfiguration)
    config.id = uuid4()
    config.tenant_id = tenant_id
    config.is_active = True
    config.default_method = provider
    config.name = f"{provider}-{model_name}"
    
    # Set config_data as a plain dict (not a MagicMock)
    config.config_data = {
        'provider': provider,
        'model_name': model_name,
        'api_key_encrypted': api_key,
        'base_url': base_url,
        'parameters': {}
    }
    
    return config


def create_mock_binding(
    llm_config: LLMConfiguration,
    application: LLMApplication,
    priority: int = 1
) -> LLMApplicationBinding:
    """Create a mock LLMApplicationBinding."""
    binding = MagicMock(spec=LLMApplicationBinding)
    binding.id = uuid4()
    binding.llm_config_id = llm_config.id
    binding.application_id = application.id
    binding.priority = priority
    binding.max_retries = 3
    binding.timeout_seconds = 30
    binding.is_active = True
    binding.llm_config = llm_config
    binding.application = application
    return binding


# ==================== Property 9: Configuration Loading Hierarchy ====================

class TestConfigurationLoadingHierarchy:
    """
    Property 9: Configuration Loading Hierarchy
    
    For any application and tenant, when loading LLM configuration, the system 
    should return application-specific bindings if they exist, otherwise 
    tenant-level configurations if they exist, otherwise global configurations, 
    otherwise environment variable configuration.
    
    **Validates: Requirements 4.2, 7.1, 7.3, 7.5, 17.1, 18.4**
    
    Requirements:
    - 4.2: WHEN no bindings exist for an application, THE System SHALL fall back 
           to environment variable configuration
    - 7.1: WHEN an application has no database bindings, THE System SHALL load 
           configuration from environment variables
    - 7.3: WHEN Structuring_Pipeline calls _load_cloud_config(), THE System SHALL 
           check database bindings first, then fall back to environment variables
    - 7.5: WHEN both database bindings and environment variables exist, THE System 
           SHALL prioritize database bindings
    - 17.1: WHEN loading LLM configuration, THE System SHALL prioritize database 
            bindings over environment variables
    - 18.4: WHEN resolving LLM configuration for an application, THE System SHALL 
            apply override priority: application binding > tenant configuration > 
            global configuration
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy,
        provider=provider_strategy,
        model_name=model_name_strategy
    )
    @pytest.mark.asyncio
    async def test_property_9_application_binding_takes_precedence(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        provider: str,
        model_name: str
    ):
        """
        Feature: llm-application-binding, Property 9: Configuration Loading Hierarchy
        
        When application-specific bindings exist, they should be returned
        regardless of tenant or global configurations.
        
        **Validates: Requirements 4.2, 7.5, 17.1, 18.4**
        """
        # Clear cache before each test example
        await app_llm_manager.cache.invalidate("*")
        
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create application-specific binding
        app_config = create_mock_config(tenant_id=tenant_id, provider=provider, model_name=model_name)
        app_binding = create_mock_binding(app_config, app, priority=1)
        
        # Mock database queries
        app_result = MagicMock()
        app_result.scalar_one_or_none = MagicMock(return_value=app)
        
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[app_binding])))
        
        def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return app_result
            else:
                return binding_result
        
        app_llm_manager.db.execute = mock_execute
        
        # Load configuration
        configs = await app_llm_manager.get_llm_config(application_code, tenant_id)
        
        # Verify application binding was returned
        assert len(configs) > 0, "Should return application-specific binding"
        assert configs[0].openai_model == model_name, \
            "Should return model from application binding"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=st.uuids().map(str),  # Always use tenant ID for this test
        provider=provider_strategy,
        model_name=model_name_strategy
    )
    @pytest.mark.asyncio
    async def test_property_9_tenant_config_fallback_when_no_app_binding(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        provider: str,
        model_name: str
    ):
        """
        Feature: llm-application-binding, Property 9: Configuration Loading Hierarchy
        
        When no application-specific binding exists but tenant configuration exists,
        tenant configuration should be returned.
        
        **Validates: Requirements 18.4**
        """
        await app_llm_manager.cache.invalidate("*")
        
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create tenant-level configuration
        tenant_config = create_mock_config(tenant_id=tenant_id, provider=provider, model_name=model_name)
        tenant_binding = create_mock_binding(tenant_config, app, priority=1)
        
        # Mock database queries
        app_result = MagicMock()
        app_result.scalar_one_or_none = MagicMock(return_value=app)
        
        tenant_result = MagicMock()
        tenant_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[tenant_binding])))
        
        def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return app_result
            else:
                return tenant_result
        
        app_llm_manager.db.execute = mock_execute
        
        with patch.dict(os.environ, {}, clear=True):
            configs = await app_llm_manager.get_llm_config(application_code, tenant_id)
        
        # Verify tenant configuration was returned
        assert len(configs) > 0, "Should return tenant-level configuration"
        assert configs[0].openai_model == model_name, \
            "Should return model from tenant configuration"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=st.uuids().map(str),
        provider=provider_strategy,
        model_name=model_name_strategy
    )
    @pytest.mark.asyncio
    async def test_property_9_global_config_fallback_when_no_tenant_config(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        provider: str,
        model_name: str
    ):
        """
        Feature: llm-application-binding, Property 9: Configuration Loading Hierarchy
        
        When no tenant configuration exists, global configuration should be returned.
        
        **Validates: Requirements 18.4**
        """
        await app_llm_manager.cache.invalidate("*")
        
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create global configuration (tenant_id=None)
        global_config = create_mock_config(tenant_id=None, provider=provider, model_name=model_name)
        global_binding = create_mock_binding(global_config, app, priority=1)
        
        # Mock database queries
        app_result = MagicMock()
        app_result.scalar_one_or_none = MagicMock(return_value=app)
        
        # With tenant_id set, ``_load_from_database`` uses one merged query (tenant ∪ global), not two steps.
        merged_result = MagicMock()
        merged_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[global_binding]))
        )
        
        def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return app_result
            return merged_result
        
        app_llm_manager.db.execute = mock_execute
        
        # Avoid env fallback masking DB result when developer has OPENAI_* set
        with patch.dict(os.environ, {}, clear=True):
            # Load configuration
            configs = await app_llm_manager.get_llm_config(application_code, tenant_id)
        
        # Verify global configuration was returned
        assert len(configs) > 0, "Should return global configuration"
        assert configs[0].openai_model == model_name, \
            "Should return model from global configuration"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy
    )
    @pytest.mark.asyncio
    async def test_property_9_env_var_fallback_when_no_database_config(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str
    ):
        """
        Feature: llm-application-binding, Property 9: Configuration Loading Hierarchy
        
        When no database configuration exists, environment variables should be used.
        
        **Validates: Requirements 4.2, 7.1, 7.3**
        """
        # Create mock application
        app = create_mock_application(application_code)
        
        # Mock database queries to return empty results
        app_result = MagicMock()
        app_result.scalar_one_or_none = MagicMock(return_value=app)
        
        empty_result = MagicMock()
        empty_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        def mock_execute(stmt):
            # First call returns app, subsequent calls return empty
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return app_result
            else:
                return empty_result
        
        app_llm_manager.db.execute = mock_execute
        
        # Set environment variables
        env_vars = {
            'OPENAI_API_KEY': 'test_env_key',
            'OPENAI_BASE_URL': 'https://api.openai.com/v1',
            'OPENAI_MODEL': 'gpt-4'
        }
        
        with patch.dict(os.environ, env_vars):
            # Load configuration
            configs = await app_llm_manager.get_llm_config(application_code, tenant_id)
            
            # Verify environment variable configuration was returned
            assert len(configs) > 0, "Should return environment variable configuration"
            assert configs[0].openai_api_key == 'test_env_key', \
                "Should use API key from environment"
            assert configs[0].openai_model == 'gpt-4', \
                "Should use model from environment"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy,
        db_model=model_name_strategy,
        env_model=model_name_strategy
    )
    @pytest.mark.asyncio
    async def test_property_9_database_binding_overrides_env_vars(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        db_model: str,
        env_model: str
    ):
        """
        Feature: llm-application-binding, Property 9: Configuration Loading Hierarchy
        
        When both database bindings and environment variables exist,
        database bindings should take precedence.
        
        **Validates: Requirements 7.5, 17.1**
        """
        # Ensure models are different to verify precedence
        assume(db_model != env_model)
        
        # Clear cache before each test example
        await app_llm_manager.cache.invalidate("*")
        
        # Create mock application and binding
        app = create_mock_application(application_code)
        db_config = create_mock_config(tenant_id=None, model_name=db_model)
        db_binding = create_mock_binding(db_config, app, priority=1)
        
        # Mock database queries
        app_result = MagicMock()
        app_result.scalar_one_or_none = MagicMock(return_value=app)
        
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[db_binding])))
        
        def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return app_result
            else:
                return binding_result
        
        app_llm_manager.db.execute = mock_execute
        
        # Set environment variables
        env_vars = {
            'OPENAI_API_KEY': 'test_env_key',
            'OPENAI_BASE_URL': 'https://api.openai.com/v1',
            'OPENAI_MODEL': env_model
        }
        
        with patch.dict(os.environ, env_vars):
            # Load configuration
            configs = await app_llm_manager.get_llm_config(application_code, tenant_id)
            
            # Verify database binding was used, not environment variables
            assert len(configs) > 0, "Should return database configuration"
            assert configs[0].openai_model == db_model, \
                f"Should use model from database ({db_model}), not environment ({env_model})"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=st.uuids().map(str),
        priorities=st.lists(priority_strategy, min_size=2, max_size=5, unique=True)
    )
    @pytest.mark.asyncio
    async def test_property_9_multiple_bindings_ordered_by_priority(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        priorities: list
    ):
        """
        Feature: llm-application-binding, Property 9: Configuration Loading Hierarchy
        
        When multiple bindings exist, they should be returned in priority order.
        
        **Validates: Requirements 18.4**
        """
        # Sort priorities to ensure correct order
        priorities = sorted(priorities)
        
        # Clear cache before each test example
        await app_llm_manager.cache.invalidate("*")
        
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create multiple bindings with different priorities
        bindings = []
        for priority in priorities:
            config = create_mock_config(
                tenant_id=tenant_id,
                model_name=f"model-priority-{priority}"
            )
            binding = create_mock_binding(config, app, priority=priority)
            bindings.append(binding)
        
        # Mock database queries
        app_result = MagicMock()
        app_result.scalar_one_or_none = MagicMock(return_value=app)
        
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=bindings)))
        
        def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return app_result
            else:
                return binding_result
        
        app_llm_manager.db.execute = mock_execute
        
        # Load configuration
        configs = await app_llm_manager.get_llm_config(application_code, tenant_id)
        
        # Verify bindings are returned in priority order
        assert len(configs) == len(priorities), \
            f"Should return all {len(priorities)} bindings"
        
        for i, priority in enumerate(priorities):
            assert configs[i].openai_model == f"model-priority-{priority}", \
                f"Binding at index {i} should have priority {priority}"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy
    )
    @pytest.mark.asyncio
    async def test_property_9_nonexistent_application_returns_empty(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str
    ):
        """
        Feature: llm-application-binding, Property 9: Configuration Loading Hierarchy
        
        When application doesn't exist in database, should return empty list
        and fall back to environment variables.
        
        **Validates: Requirements 4.2, 7.1**
        """
        # Mock database query to return None (application not found)
        app_result = MagicMock()
        app_result.scalar_one_or_none = MagicMock(return_value=None)
        
        def mock_execute(stmt):
            return app_result
        
        app_llm_manager.db.execute = mock_execute
        
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Load configuration
            configs = await app_llm_manager.get_llm_config(application_code, tenant_id)
            
            # Should return empty list when no app and no env vars
            assert len(configs) == 0, \
                "Should return empty list when application not found and no env vars"
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy
    )
    @pytest.mark.asyncio
    async def test_property_9_ollama_env_var_fallback(
        self,
        app_llm_manager,
        application_code: str
    ):
        """
        Feature: llm-application-binding, Property 9: Configuration Loading Hierarchy
        
        When using Ollama with no API key, should still create configuration.
        
        **Validates: Requirements 4.2, 7.1**
        """
        # Create mock application
        app = create_mock_application(application_code)
        
        # Mock database queries to return empty results
        app_result = MagicMock()
        app_result.scalar_one_or_none = MagicMock(return_value=app)
        
        empty_result = MagicMock()
        empty_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return app_result
            else:
                return empty_result
        
        app_llm_manager.db.execute = mock_execute
        
        # Set Ollama environment variables (no API key, but base_url contains "ollama")
        env_vars = {
            'OPENAI_BASE_URL': 'http://localhost:11434/ollama',
            'OPENAI_MODEL': 'llama2'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # Load configuration
            configs = await app_llm_manager.get_llm_config(application_code, None)
            
            # Verify Ollama configuration was created
            assert len(configs) > 0, "Should return Ollama configuration"
            assert configs[0].openai_api_key == 'ollama', \
                "Should use 'ollama' as API key for Ollama"
            assert configs[0].openai_model == 'llama2', \
                "Should use model from environment"


# ==================== Cache Integration Tests ====================

class TestConfigurationHierarchyWithCache:
    """
    Tests for configuration hierarchy with caching behavior.
    
    **Validates: Requirements 4.2, 17.1, 18.4**
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy,
        model_name=model_name_strategy
    )
    @pytest.mark.asyncio
    async def test_hierarchy_result_cached_correctly(
        self,
        app_llm_manager,
        application_code: str,
        tenant_id: str,
        model_name: str
    ):
        """
        Feature: llm-application-binding, Property 9: Configuration Loading Hierarchy
        
        Configuration hierarchy resolution result should be cached.
        
        **Validates: Requirements 4.2, 17.1**
        """
        # Clear cache before test
        await app_llm_manager.cache.invalidate("*")
        
        # Create mock application and binding
        app = create_mock_application(application_code)
        config = create_mock_config(tenant_id=tenant_id, model_name=model_name)
        binding = create_mock_binding(config, app, priority=1)
        
        # Mock database queries
        app_result = MagicMock()
        app_result.scalar_one_or_none = MagicMock(return_value=app)
        
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[binding])))
        
        call_count = [0]
        
        def mock_execute(stmt):
            call_count[0] += 1
            if call_count[0] == 1:
                return app_result
            else:
                return binding_result
        
        app_llm_manager.db.execute = mock_execute
        
        # First call - should hit database
        configs1 = await app_llm_manager.get_llm_config(application_code, tenant_id)
        first_call_count = call_count[0]
        
        # Second call - should hit cache
        configs2 = await app_llm_manager.get_llm_config(application_code, tenant_id)
        second_call_count = call_count[0]
        
        # Verify both calls return same configuration
        assert len(configs1) == len(configs2), "Both calls should return same number of configs"
        assert configs1[0].openai_model == configs2[0].openai_model, \
            "Both calls should return same model"
        
        # Verify database was only called once (second call used cache)
        assert second_call_count == first_call_count, \
            "Database should only be queried once (cached on second call)"


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
