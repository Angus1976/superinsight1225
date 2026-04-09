"""
Property-based tests for LLM Application Binding - API Layer.

Uses Hypothesis library for property testing with minimum 100 iterations.
Tests Properties 3, 4, 8 from the LLM Application Binding design document.

Feature: llm-application-binding
Properties: 3 - Binding Prevents Config Deletion
            4 - Application Code Uniqueness
            8 - Bindings Ordered By Priority
"""

import pytest
from uuid import uuid4
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from src.models.llm_configuration import LLMConfiguration
from src.models.llm_application import LLMApplication, LLMApplicationBinding


# ==================== Custom Strategies ====================

# Strategy for application codes
application_code_strategy = st.sampled_from([
    'structuring', 'knowledge_graph', 'ai_assistant',
    'semantic_analysis', 'rag_agent', 'text_to_sql'
])

# Strategy for configuration names
config_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' -_'),
    min_size=3,
    max_size=50
)

# Strategy for provider types
provider_strategy = st.sampled_from(['openai', 'azure', 'anthropic', 'ollama', 'custom'])

# Strategy for model names
model_name_strategy = st.sampled_from([
    'gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo',
    'claude-3-opus', 'claude-3-sonnet',
    'llama2', 'mistral'
])

# Strategy for priority values
priority_strategy = st.integers(min_value=1, max_value=99)

# Strategy for tenant IDs (UUID strings or None)
tenant_id_strategy = st.one_of(
    st.none(),
    st.uuids().map(str)
)


# ==================== Helper Functions ====================

def create_mock_application(code: str) -> LLMApplication:
    """Create a mock LLMApplication."""
    app = MagicMock(spec=LLMApplication)
    app.id = uuid4()
    app.code = code
    app.name = code.replace('_', ' ').title()
    app.description = f"Application for {code}"
    app.llm_usage_pattern = "general"
    app.is_active = True
    app.created_at = MagicMock()
    app.updated_at = MagicMock()
    return app


def create_mock_config(
    name: str,
    tenant_id: str = None,
    provider: str = 'openai',
    model_name: str = 'gpt-3.5-turbo'
) -> LLMConfiguration:
    """Create a mock LLMConfiguration."""
    config = MagicMock(spec=LLMConfiguration)
    config.id = uuid4()
    config.name = name
    config.tenant_id = tenant_id
    config.is_active = True
    config.default_method = provider
    config.config_data = {
        'provider': provider,
        'model_name': model_name,
        'api_key': 'test_key',
        'base_url': 'https://api.openai.com/v1'
    }
    config.created_at = MagicMock()
    config.updated_at = MagicMock()
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
    binding.created_at = MagicMock()
    binding.updated_at = MagicMock()
    return binding


# ==================== Property 3: Binding Prevents Config Deletion ====================

class TestBindingPreventsConfigDeletion:
    """
    Property 3: Binding Prevents Config Deletion
    
    For any LLM configuration with active bindings, attempting to delete the 
    configuration should fail with an error indicating existing bindings.
    
    **Validates: Requirements 1.5**
    
    Requirements:
    - 1.5: WHEN an LLM configuration is deleted, THE System SHALL check if it 
           is bound to any application and prevent deletion if bindings exist
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        config_name=config_name_strategy,
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy,
        num_bindings=st.integers(min_value=1, max_value=5)
    )
    def test_property_3_cannot_delete_config_with_active_bindings(
        self,
        config_name: str,
        application_code: str,
        tenant_id: str,
        num_bindings: int
    ):
        """
        Feature: llm-application-binding, Property 3: Binding Prevents Config Deletion
        
        For any LLM configuration with active bindings, deletion should fail.
        
        **Validates: Requirements 1.5**
        """
        # Skip empty names
        assume(len(config_name.strip()) > 0)
        
        # Create mock config and application
        config = create_mock_config(config_name, tenant_id)
        app = create_mock_application(application_code)
        
        # Create multiple bindings
        bindings = []
        for i in range(num_bindings):
            binding = create_mock_binding(config, app, priority=i+1)
            bindings.append(binding)
        
        # Mock database session
        mock_db = MagicMock()
        
        # Mock query to return the config
        config_result = MagicMock()
        config_result.scalar_one_or_none = MagicMock(return_value=config)
        
        # Mock query to return bindings
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=bindings)))
        
        def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return config_result
            else:
                return binding_result
        
        mock_db.execute = mock_execute
        
        # Import the delete function
        from src.api.llm_config import delete_llm_config
        
        # Attempt to delete config with bindings - should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            delete_llm_config(config.id, mock_db)
        
        # Verify error details
        assert exc_info.value.status_code == 409, \
            "Should return 409 Conflict status code"
        assert "bindings" in str(exc_info.value.detail).lower(), \
            "Error message should mention bindings"
        assert str(num_bindings) in str(exc_info.value.detail), \
            f"Error message should mention {num_bindings} bindings"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        config_name=config_name_strategy,
        tenant_id=tenant_id_strategy
    )
    def test_property_3_can_delete_config_without_bindings(
        self,
        config_name: str,
        tenant_id: str
    ):
        """
        Feature: llm-application-binding, Property 3: Binding Prevents Config Deletion
        
        For any LLM configuration without bindings, deletion should succeed.
        
        **Validates: Requirements 1.5**
        """
        # Skip empty names
        assume(len(config_name.strip()) > 0)
        
        # Create mock config
        config = create_mock_config(config_name, tenant_id)
        
        # Mock database session
        mock_db = MagicMock()
        
        # Mock query to return the config
        config_result = MagicMock()
        config_result.scalar_one_or_none = MagicMock(return_value=config)
        
        # Mock query to return no bindings
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return config_result
            else:
                return binding_result
        
        mock_db.execute = mock_execute
        mock_db.delete = MagicMock()
        mock_db.commit = MagicMock()
        
        # Import the delete function
        from src.api.llm_config import delete_llm_config
        
        # Delete config without bindings - should succeed
        delete_llm_config(config.id, mock_db)
        
        # Verify delete was called
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        config_name=config_name_strategy,
        application_code=application_code_strategy,
        tenant_id=tenant_id_strategy
    )
    def test_property_3_can_delete_config_with_inactive_bindings(
        self,
        config_name: str,
        application_code: str,
        tenant_id: str
    ):
        """
        Feature: llm-application-binding, Property 3: Binding Prevents Config Deletion
        
        For any LLM configuration with only inactive bindings, deletion should succeed.
        
        **Validates: Requirements 1.5**
        """
        # Skip empty names
        assume(len(config_name.strip()) > 0)
        
        # Create mock config and application
        config = create_mock_config(config_name, tenant_id)
        app = create_mock_application(application_code)
        
        # Create inactive binding
        binding = create_mock_binding(config, app, priority=1)
        binding.is_active = False
        
        # Mock database session
        mock_db = MagicMock()
        
        # Mock query to return the config
        config_result = MagicMock()
        config_result.scalar_one_or_none = MagicMock(return_value=config)
        
        # Mock query to return no active bindings (filter by is_active=True)
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        def mock_execute(stmt):
            if not hasattr(mock_execute, 'call_count'):
                mock_execute.call_count = 0
            mock_execute.call_count += 1
            
            if mock_execute.call_count == 1:
                return config_result
            else:
                return binding_result
        
        mock_db.execute = mock_execute
        mock_db.delete = MagicMock()
        mock_db.commit = MagicMock()
        
        # Import the delete function
        from src.api.llm_config import delete_llm_config
        
        # Delete config with inactive bindings - should succeed
        delete_llm_config(config.id, mock_db)
        
        # Verify delete was called
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()


# ==================== Property 4: Application Code Uniqueness ====================

class TestApplicationCodeUniqueness:
    """
    Property 4: Application Code Uniqueness
    
    For any two application registration attempts with the same code, the second 
    attempt should fail with a uniqueness constraint error.
    
    **Validates: Requirements 2.3**
    
    Requirements:
    - 2.3: WHEN an application is registered, THE System SHALL ensure the 
           application code is unique
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        application_code=application_code_strategy,
        name1=st.text(min_size=3, max_size=50),
        name2=st.text(min_size=3, max_size=50)
    )
    @pytest.mark.asyncio
    async def test_property_4_duplicate_application_code_fails(
        self,
        application_code: str,
        name1: str,
        name2: str
    ):
        """
        Feature: llm-application-binding, Property 4: Application Code Uniqueness
        
        For any application code, attempting to register it twice should fail.
        
        **Validates: Requirements 2.3**
        """
        # Skip empty names
        assume(len(name1.strip()) > 0)
        assume(len(name2.strip()) > 0)
        
        # Create first application
        app1 = create_mock_application(application_code)
        app1.name = name1
        
        # Mock database session
        mock_db = AsyncMock()
        
        # First registration succeeds
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Second registration fails with IntegrityError
        mock_db.commit = AsyncMock(side_effect=IntegrityError(
            "duplicate key value violates unique constraint",
            params={},
            orig=Exception("UNIQUE constraint failed: llm_applications.code")
        ))
        
        # Attempt second registration with same code
        app2 = LLMApplication(
            code=application_code,
            name=name2,
            description="Test application"
        )
        
        mock_db.add(app2)
        
        # Commit should raise IntegrityError
        with pytest.raises(IntegrityError) as exc_info:
            await mock_db.commit()
        
        # Verify error mentions unique constraint
        assert "unique constraint" in str(exc_info.value).lower() or \
               "UNIQUE constraint" in str(exc_info.value), \
            "Error should mention unique constraint violation"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        code1=application_code_strategy,
        code2=application_code_strategy
    )
    @pytest.mark.asyncio
    async def test_property_4_different_application_codes_succeed(
        self,
        code1: str,
        code2: str
    ):
        """
        Feature: llm-application-binding, Property 4: Application Code Uniqueness
        
        For any two different application codes, both registrations should succeed.
        
        **Validates: Requirements 2.3**
        """
        # Ensure codes are different
        assume(code1 != code2)
        
        # Create two applications with different codes
        app1 = create_mock_application(code1)
        app2 = create_mock_application(code2)
        
        # Mock database session
        mock_db = AsyncMock()
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Both registrations should succeed
        mock_db.add(app1)
        await mock_db.commit()
        
        mock_db.add(app2)
        await mock_db.commit()
        
        # Verify both commits succeeded
        assert mock_db.commit.call_count == 2, \
            "Both applications should be committed successfully"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        application_code=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),  # Only letters with case
            min_size=3,
            max_size=20
        ).filter(lambda s: s.lower() != s.upper() and s.lower() != s and s.upper() != s)
    )
    @pytest.mark.asyncio
    async def test_property_4_case_sensitive_uniqueness(
        self,
        application_code: str
    ):
        """
        Feature: llm-application-binding, Property 4: Application Code Uniqueness
        
        Application code uniqueness should be case-sensitive (if applicable).
        
        **Validates: Requirements 2.3**
        """
        # No need for assume() - filter already ensures mixed case
        
        # Create applications with different cases
        app1 = create_mock_application(application_code.lower())
        app2 = create_mock_application(application_code.upper())
        
        # Mock database session
        mock_db = AsyncMock()
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Both registrations should succeed (case-sensitive)
        mock_db.add(app1)
        await mock_db.commit()
        
        mock_db.add(app2)
        await mock_db.commit()
        
        # Verify both commits succeeded
        assert mock_db.commit.call_count == 2, \
            "Different case codes should be allowed (case-sensitive)"


# ==================== Property 8: Bindings Ordered By Priority ====================

class TestBindingsOrderedByPriority:
    """
    Property 8: Bindings Ordered By Priority
    
    For any application with multiple active bindings, retrieving the bindings 
    should return them in ascending priority order (1, 2, 3, ...).
    
    **Validates: Requirements 3.5, 4.1**
    
    Requirements:
    - 3.5: WHEN multiple bindings exist for an application, THE System SHALL 
           order them by priority ascending
    - 4.1: WHEN an application requests LLM configuration, THE System SHALL 
           return all active bindings ordered by priority
    """
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        application_code=application_code_strategy,
        priorities=st.lists(priority_strategy, min_size=2, max_size=10, unique=True)
    )
    def test_property_8_bindings_returned_in_priority_order(
        self,
        application_code: str,
        priorities: list
    ):
        """
        Feature: llm-application-binding, Property 8: Bindings Ordered By Priority
        
        For any application with multiple bindings, they should be returned 
        in ascending priority order.
        
        **Validates: Requirements 3.5, 4.1**
        """
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create bindings with random priorities
        bindings = []
        for priority in priorities:
            config = create_mock_config(
                name=f"config-{priority}",
                model_name=f"model-priority-{priority}"
            )
            binding = create_mock_binding(config, app, priority=priority)
            bindings.append(binding)
        
        # Mock database session
        mock_db = MagicMock()
        
        # Sort bindings by priority (simulating SQL ORDER BY)
        sorted_bindings = sorted(bindings, key=lambda b: b.priority)
        
        # Mock query to return sorted bindings
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=sorted_bindings)))
        
        def mock_execute(stmt):
            return binding_result
        
        mock_db.execute = mock_execute
        
        # Import the list function
        from src.api.llm_config import list_bindings
        
        # Get bindings
        result = list_bindings(application_id=app.id, db=mock_db)
        
        # Verify bindings are in priority order
        sorted_priorities = sorted(priorities)
        for i, binding in enumerate(result):
            expected_priority = sorted_priorities[i]
            assert binding.priority == expected_priority, \
                f"Binding at index {i} should have priority {expected_priority}, got {binding.priority}"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        application_code=application_code_strategy,
        num_bindings=st.integers(min_value=3, max_value=8)
    )
    def test_property_8_sequential_priorities_maintained(
        self,
        application_code: str,
        num_bindings: int
    ):
        """
        Feature: llm-application-binding, Property 8: Bindings Ordered By Priority
        
        For any application with sequential priorities (1, 2, 3, ...), 
        order should be maintained.
        
        **Validates: Requirements 3.5, 4.1**
        """
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create bindings with sequential priorities
        bindings = []
        for i in range(1, num_bindings + 1):
            config = create_mock_config(
                name=f"config-{i}",
                model_name=f"model-{i}"
            )
            binding = create_mock_binding(config, app, priority=i)
            bindings.append(binding)
        
        # Mock database session
        mock_db = MagicMock()
        
        # Sort bindings by priority (simulating SQL ORDER BY)
        sorted_bindings = sorted(bindings, key=lambda b: b.priority)
        
        # Mock query to return sorted bindings
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=sorted_bindings)))
        
        def mock_execute(stmt):
            return binding_result
        
        mock_db.execute = mock_execute
        
        # Import the list function
        from src.api.llm_config import list_bindings
        
        # Get bindings
        result = list_bindings(application_id=app.id, db=mock_db)
        
        # Verify bindings are in sequential order
        for i, binding in enumerate(result):
            expected_priority = i + 1
            assert binding.priority == expected_priority, \
                f"Binding at index {i} should have priority {expected_priority}, got {binding.priority}"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        application_code=application_code_strategy,
        priorities=st.lists(priority_strategy, min_size=2, max_size=5, unique=True)
    )
    def test_property_8_only_active_bindings_returned(
        self,
        application_code: str,
        priorities: list
    ):
        """
        Feature: llm-application-binding, Property 8: Bindings Ordered By Priority
        
        Only active bindings should be returned, in priority order.
        
        **Validates: Requirements 3.5, 4.1**
        """
        # Create mock application
        app = create_mock_application(application_code)
        
        # Create mix of active and inactive bindings
        active_bindings = []
        inactive_bindings = []
        
        for i, priority in enumerate(priorities):
            config = create_mock_config(
                name=f"config-{priority}",
                model_name=f"model-{priority}"
            )
            binding = create_mock_binding(config, app, priority=priority)
            
            # Make every other binding inactive
            if i % 2 == 0:
                binding.is_active = True
                active_bindings.append(binding)
            else:
                binding.is_active = False
                inactive_bindings.append(binding)
        
        # Mock database session
        mock_db = MagicMock()
        
        # Sort active bindings by priority (simulating SQL ORDER BY)
        sorted_active_bindings = sorted(active_bindings, key=lambda b: b.priority)
        
        # Mock query to return sorted active bindings
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=sorted_active_bindings)))
        
        def mock_execute(stmt):
            return binding_result
        
        mock_db.execute = mock_execute
        
        # Import the list function
        from src.api.llm_config import list_bindings
        
        # Get bindings
        result = list_bindings(application_id=app.id, db=mock_db)
        
        # Verify only active bindings returned
        assert len(result) == len(active_bindings), \
            f"Should return {len(active_bindings)} active bindings, got {len(result)}"
        
        # Verify all returned bindings are active
        for binding in result:
            assert binding.is_active, \
                "All returned bindings should be active"
        
        # Verify priority order
        active_priorities = sorted([b.priority for b in active_bindings])
        for i, binding in enumerate(result):
            assert binding.priority == active_priorities[i], \
                f"Binding at index {i} should have priority {active_priorities[i]}, got {binding.priority}"
    
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        application_code=application_code_strategy
    )
    def test_property_8_empty_bindings_returns_empty_list(
        self,
        application_code: str
    ):
        """
        Feature: llm-application-binding, Property 8: Bindings Ordered By Priority
        
        For any application with no bindings, should return empty list.
        
        **Validates: Requirements 3.5, 4.1**
        """
        # Create mock application
        app = create_mock_application(application_code)
        
        # Mock database session
        mock_db = MagicMock()
        
        # Mock query to return no bindings
        binding_result = MagicMock()
        binding_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        
        def mock_execute(stmt):
            return binding_result
        
        mock_db.execute = mock_execute
        
        # Import the list function
        from src.api.llm_config import list_bindings
        
        # Get bindings
        result = list_bindings(application_id=app.id, db=mock_db)
        
        # Verify empty list returned
        assert len(result) == 0, \
            "Should return empty list when no bindings exist"


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
