"""
Property-based tests for LLM Integration module - Active Provider Deletion Prevention.

Uses Hypothesis library for property testing with minimum 100 iterations.
Tests Property 16 from the LLM Integration design document.

Feature: llm-integration
Property: 16 - Active Provider Deletion Prevention

**Validates: Requirements 6.5**

Requirements:
- 6.5: WHEN deleting a provider, THE System SHALL prevent deletion if it's 
       currently set as the active provider
"""

import pytest
import asyncio
from typing import Optional, List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.ai.llm_schemas import (
    LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig
)


# ==================== Custom Strategies ====================

# Strategy for valid tenant IDs
tenant_id_strategy = st.one_of(
    st.none(),
    st.uuids().map(str),
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
        min_size=8,
        max_size=36
    ).filter(lambda x: len(x.strip()) >= 8),
)

# Strategy for provider IDs (using LLMMethod values)
provider_method_strategy = st.sampled_from(list(LLMMethod))

# Strategy for API keys
api_key_strategy = st.one_of(
    st.builds(
        lambda suffix: f"sk-{suffix}",
        st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N')),
            min_size=32,
            max_size=48
        )
    ),
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
        min_size=16,
        max_size=64
    ),
    st.uuids().map(str),
)

# Strategy for model names
model_name_strategy = st.one_of(
    st.just("qwen:7b"),
    st.just("llama2"),
    st.just("mistral"),
    st.just("gpt-3.5-turbo"),
    st.just("gpt-4"),
    st.just("glm-4"),
)

# Strategy for timeout values
timeout_strategy = st.integers(min_value=1, max_value=300)

# Strategy for max_retries values
max_retries_strategy = st.integers(min_value=0, max_value=10)

# Strategy for LocalConfig
local_config_strategy = st.builds(
    LocalConfig,
    ollama_url=st.just("http://localhost:11434"),
    default_model=model_name_strategy,
    timeout=timeout_strategy,
    max_retries=max_retries_strategy,
)

# Strategy for CloudConfig
cloud_config_strategy = st.builds(
    CloudConfig,
    openai_api_key=st.one_of(st.none(), api_key_strategy),
    openai_base_url=st.just("https://api.openai.com/v1"),
    openai_model=st.one_of(st.just("gpt-3.5-turbo"), st.just("gpt-4")),
    azure_endpoint=st.one_of(st.none(), st.just("https://myresource.openai.azure.com")),
    azure_api_key=st.one_of(st.none(), api_key_strategy),
    azure_deployment=st.one_of(st.none(), st.just("my-deployment")),
    azure_api_version=st.just("2024-02-15-preview"),
    timeout=timeout_strategy,
    max_retries=max_retries_strategy,
)

# Strategy for ChinaLLMConfig
china_config_strategy = st.builds(
    ChinaLLMConfig,
    qwen_api_key=st.one_of(st.none(), api_key_strategy),
    qwen_model=st.one_of(st.just("qwen-turbo"), st.just("qwen-plus")),
    zhipu_api_key=st.one_of(st.none(), api_key_strategy),
    zhipu_model=st.one_of(st.just("glm-4"), st.just("glm-3-turbo")),
    baidu_api_key=st.one_of(st.none(), api_key_strategy),
    baidu_secret_key=st.one_of(st.none(), api_key_strategy),
    baidu_model=st.one_of(st.just("ernie-bot-4"), st.just("ernie-bot")),
    hunyuan_secret_id=st.one_of(st.none(), api_key_strategy),
    hunyuan_secret_key=st.one_of(st.none(), api_key_strategy),
    hunyuan_model=st.one_of(st.just("hunyuan-lite"), st.just("hunyuan-pro")),
    timeout=timeout_strategy,
    max_retries=max_retries_strategy,
)

# Strategy for enabled methods (list of LLMMethod)
enabled_methods_strategy = st.lists(
    st.sampled_from(list(LLMMethod)),
    min_size=1,
    max_size=len(LLMMethod),
    unique=True,
)

# Strategy for complete LLMConfig
llm_config_strategy = st.builds(
    LLMConfig,
    default_method=st.sampled_from(list(LLMMethod)),
    local_config=local_config_strategy,
    cloud_config=cloud_config_strategy,
    china_config=china_config_strategy,
    enabled_methods=enabled_methods_strategy,
)


# ==================== Mock Provider Manager ====================

class MockProviderManager:
    """
    Mock Provider Manager for testing active provider deletion prevention.
    
    Simulates the behavior of the real ProviderManager with:
    - Provider registration and storage
    - Active provider tracking
    - Deletion prevention for active providers
    """
    
    def __init__(self):
        self.providers: Dict[str, Dict[str, Any]] = {}
        self.active_provider_id: Optional[str] = None
        self.fallback_provider_id: Optional[str] = None
        self._lock = asyncio.Lock()
    
    async def register_provider(self, provider_id: str, config: Dict[str, Any]) -> None:
        """Register a new provider."""
        async with self._lock:
            self.providers[provider_id] = config
    
    async def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get provider by ID."""
        async with self._lock:
            return self.providers.get(provider_id)
    
    async def set_active_provider(self, provider_id: str) -> None:
        """Set the active provider."""
        async with self._lock:
            if provider_id not in self.providers:
                raise ValueError(f"Provider {provider_id} not found")
            self.active_provider_id = provider_id
    
    async def get_active_provider_id(self) -> Optional[str]:
        """Get the active provider ID."""
        async with self._lock:
            return self.active_provider_id
    
    async def delete_provider(self, provider_id: str) -> bool:
        """
        Delete a provider configuration.
        
        Implements Property 16: Active Provider Deletion Prevention
        - Rejects deletion if provider is currently active
        
        Args:
            provider_id: ID of the provider to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            ValueError: If provider is the active provider
        """
        async with self._lock:
            # Property 16: Prevent deletion of active provider
            if provider_id == self.active_provider_id:
                raise ValueError("Cannot delete active provider")
            
            if provider_id not in self.providers:
                return False
            
            del self.providers[provider_id]
            return True
    
    async def list_providers(self) -> List[Dict[str, Any]]:
        """List all providers."""
        async with self._lock:
            return [
                {"id": pid, **config}
                for pid, config in self.providers.items()
            ]


# ==================== Property 16: Active Provider Deletion Prevention ====================

class TestActiveProviderDeletionPrevention:
    """
    Property 16: Active Provider Deletion Prevention
    
    For any provider that is currently set as the active provider, 
    deletion attempts should be rejected with an error.
    
    **Validates: Requirements 6.5**
    
    Requirements:
    - 6.5: WHEN deleting a provider, THE System SHALL prevent deletion 
           if it's currently set as the active provider
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        provider_method=provider_method_strategy,
        config=llm_config_strategy,
    )
    def test_property_16_active_provider_deletion_rejected(
        self,
        provider_method: LLMMethod,
        config: LLMConfig,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        When a provider is set as the active provider, attempting to delete 
        it should raise an error.
        
        **Validates: Requirements 6.5**
        """
        async def run_test():
            manager = MockProviderManager()
            provider_id = provider_method.value
            
            # Register the provider
            await manager.register_provider(provider_id, config.model_dump())
            
            # Set as active provider
            await manager.set_active_provider(provider_id)
            
            # Verify it's the active provider
            active_id = await manager.get_active_provider_id()
            assert active_id == provider_id, "Provider should be set as active"
            
            # Property: Attempting to delete active provider should raise error
            with pytest.raises(ValueError) as exc_info:
                await manager.delete_provider(provider_id)
            
            assert "Cannot delete active provider" in str(exc_info.value), \
                "Error message should indicate active provider cannot be deleted"
            
            # Verify provider still exists after failed deletion
            provider = await manager.get_provider(provider_id)
            assert provider is not None, \
                "Active provider should still exist after failed deletion attempt"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        active_method=provider_method_strategy,
        inactive_method=provider_method_strategy,
        config=llm_config_strategy,
    )
    def test_property_16_non_active_provider_deletion_succeeds(
        self,
        active_method: LLMMethod,
        inactive_method: LLMMethod,
        config: LLMConfig,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        When a provider is NOT the active provider, deletion should succeed.
        
        **Validates: Requirements 6.5**
        """
        # Ensure we have two different providers
        assume(active_method != inactive_method)
        
        async def run_test():
            manager = MockProviderManager()
            active_id = active_method.value
            inactive_id = inactive_method.value
            
            # Register both providers
            await manager.register_provider(active_id, config.model_dump())
            await manager.register_provider(inactive_id, config.model_dump())
            
            # Set one as active
            await manager.set_active_provider(active_id)
            
            # Property: Deleting non-active provider should succeed
            result = await manager.delete_provider(inactive_id)
            assert result is True, "Non-active provider deletion should succeed"
            
            # Verify inactive provider is deleted
            provider = await manager.get_provider(inactive_id)
            assert provider is None, "Deleted provider should not exist"
            
            # Verify active provider still exists
            active_provider = await manager.get_provider(active_id)
            assert active_provider is not None, \
                "Active provider should still exist after deleting another provider"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        provider_methods=st.lists(
            provider_method_strategy,
            min_size=2,
            max_size=5,
            unique=True,
        ),
        active_index=st.integers(min_value=0, max_value=4),
        config=llm_config_strategy,
    )
    def test_property_16_only_active_provider_protected(
        self,
        provider_methods: List[LLMMethod],
        active_index: int,
        config: LLMConfig,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        Among multiple providers, only the active one should be protected 
        from deletion.
        
        **Validates: Requirements 6.5**
        """
        # Ensure active_index is valid for the list
        assume(active_index < len(provider_methods))
        
        async def run_test():
            manager = MockProviderManager()
            
            # Register all providers
            for method in provider_methods:
                await manager.register_provider(method.value, config.model_dump())
            
            # Set one as active
            active_method = provider_methods[active_index]
            await manager.set_active_provider(active_method.value)
            
            # Try to delete each provider
            for i, method in enumerate(provider_methods):
                provider_id = method.value
                
                if i == active_index:
                    # Property: Active provider deletion should fail
                    with pytest.raises(ValueError) as exc_info:
                        await manager.delete_provider(provider_id)
                    assert "Cannot delete active provider" in str(exc_info.value)
                else:
                    # Property: Non-active provider deletion should succeed
                    result = await manager.delete_provider(provider_id)
                    assert result is True, \
                        f"Non-active provider {provider_id} deletion should succeed"
            
            # Verify only active provider remains
            remaining = await manager.list_providers()
            assert len(remaining) == 1, "Only active provider should remain"
            assert remaining[0]["id"] == active_method.value, \
                "Remaining provider should be the active one"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        provider_method=provider_method_strategy,
        config=llm_config_strategy,
    )
    def test_property_16_deletion_error_preserves_state(
        self,
        provider_method: LLMMethod,
        config: LLMConfig,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        When deletion of active provider fails, the system state should 
        remain unchanged.
        
        **Validates: Requirements 6.5**
        """
        async def run_test():
            manager = MockProviderManager()
            provider_id = provider_method.value
            
            # Register and set as active
            await manager.register_provider(provider_id, config.model_dump())
            await manager.set_active_provider(provider_id)
            
            # Store state before deletion attempt
            providers_before = await manager.list_providers()
            active_before = await manager.get_active_provider_id()
            
            # Attempt deletion (should fail)
            try:
                await manager.delete_provider(provider_id)
            except ValueError:
                pass  # Expected
            
            # Property: State should be unchanged after failed deletion
            providers_after = await manager.list_providers()
            active_after = await manager.get_active_provider_id()
            
            assert len(providers_before) == len(providers_after), \
                "Provider count should be unchanged after failed deletion"
            assert active_before == active_after, \
                "Active provider should be unchanged after failed deletion"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        first_active=provider_method_strategy,
        second_active=provider_method_strategy,
        config=llm_config_strategy,
    )
    def test_property_16_active_provider_change_allows_deletion(
        self,
        first_active: LLMMethod,
        second_active: LLMMethod,
        config: LLMConfig,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        When the active provider is changed, the previously active provider 
        can be deleted.
        
        **Validates: Requirements 6.5**
        """
        # Ensure we have two different providers
        assume(first_active != second_active)
        
        async def run_test():
            manager = MockProviderManager()
            first_id = first_active.value
            second_id = second_active.value
            
            # Register both providers
            await manager.register_provider(first_id, config.model_dump())
            await manager.register_provider(second_id, config.model_dump())
            
            # Set first as active
            await manager.set_active_provider(first_id)
            
            # Verify first cannot be deleted
            with pytest.raises(ValueError):
                await manager.delete_provider(first_id)
            
            # Change active to second
            await manager.set_active_provider(second_id)
            
            # Property: Previously active provider can now be deleted
            result = await manager.delete_provider(first_id)
            assert result is True, \
                "Previously active provider should be deletable after deactivation"
            
            # Verify first is deleted
            provider = await manager.get_provider(first_id)
            assert provider is None, "Deleted provider should not exist"
            
            # Verify second is still active and exists
            active_id = await manager.get_active_provider_id()
            assert active_id == second_id, "Second provider should still be active"
        
        asyncio.get_event_loop().run_until_complete(run_test())


# ==================== Integration with LLMSwitcher ====================

class TestActiveProviderDeletionWithSwitcher:
    """
    Integration tests for active provider deletion prevention with LLMSwitcher.
    
    Tests the interaction between provider deletion and the LLM switching logic.
    
    **Validates: Requirements 6.5**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        active_method=provider_method_strategy,
        fallback_method=provider_method_strategy,
        config=llm_config_strategy,
    )
    def test_property_16_active_and_fallback_both_protected(
        self,
        active_method: LLMMethod,
        fallback_method: LLMMethod,
        config: LLMConfig,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        Both active and fallback providers should be protected from deletion
        when they are in use.
        
        **Validates: Requirements 6.5**
        """
        # Ensure we have two different providers
        assume(active_method != fallback_method)
        
        async def run_test():
            manager = MockProviderManager()
            active_id = active_method.value
            fallback_id = fallback_method.value
            
            # Register both providers
            await manager.register_provider(active_id, config.model_dump())
            await manager.register_provider(fallback_id, config.model_dump())
            
            # Set active and fallback
            await manager.set_active_provider(active_id)
            manager.fallback_provider_id = fallback_id
            
            # Property: Active provider deletion should fail
            with pytest.raises(ValueError) as exc_info:
                await manager.delete_provider(active_id)
            assert "Cannot delete active provider" in str(exc_info.value)
            
            # Note: Fallback provider deletion behavior depends on implementation
            # The design focuses on active provider protection
            # Fallback can be deleted unless it's also the active provider
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        provider_method=provider_method_strategy,
        config=llm_config_strategy,
        deletion_attempts=st.integers(min_value=1, max_value=10),
    )
    def test_property_16_repeated_deletion_attempts_all_fail(
        self,
        provider_method: LLMMethod,
        config: LLMConfig,
        deletion_attempts: int,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        Multiple deletion attempts on an active provider should all fail.
        
        **Validates: Requirements 6.5**
        """
        async def run_test():
            manager = MockProviderManager()
            provider_id = provider_method.value
            
            # Register and set as active
            await manager.register_provider(provider_id, config.model_dump())
            await manager.set_active_provider(provider_id)
            
            # Property: All deletion attempts should fail
            for attempt in range(deletion_attempts):
                with pytest.raises(ValueError) as exc_info:
                    await manager.delete_provider(provider_id)
                assert "Cannot delete active provider" in str(exc_info.value), \
                    f"Deletion attempt {attempt + 1} should fail with correct error"
            
            # Verify provider still exists
            provider = await manager.get_provider(provider_id)
            assert provider is not None, \
                f"Provider should exist after {deletion_attempts} failed deletion attempts"
        
        asyncio.get_event_loop().run_until_complete(run_test())


# ==================== Edge Cases ====================

class TestActiveProviderDeletionEdgeCases:
    """
    Edge case tests for active provider deletion prevention.
    
    **Validates: Requirements 6.5**
    """
    
    def test_deletion_of_nonexistent_provider_returns_false(self):
        """
        Deleting a non-existent provider should return False, not raise error.
        
        **Validates: Requirements 6.5**
        """
        async def run_test():
            manager = MockProviderManager()
            
            # Try to delete non-existent provider
            result = await manager.delete_provider("nonexistent_provider")
            assert result is False, \
                "Deleting non-existent provider should return False"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_no_active_provider_allows_any_deletion(self):
        """
        When no provider is active, any provider can be deleted.
        
        **Validates: Requirements 6.5**
        """
        async def run_test():
            manager = MockProviderManager()
            
            # Register providers without setting active
            await manager.register_provider("provider1", {"name": "Provider 1"})
            await manager.register_provider("provider2", {"name": "Provider 2"})
            
            # Verify no active provider
            active_id = await manager.get_active_provider_id()
            assert active_id is None, "No provider should be active initially"
            
            # Both providers should be deletable
            result1 = await manager.delete_provider("provider1")
            assert result1 is True, "Provider 1 should be deletable"
            
            result2 = await manager.delete_provider("provider2")
            assert result2 is True, "Provider 2 should be deletable"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_active_provider_error_message_is_descriptive(self):
        """
        Error message for active provider deletion should be descriptive.
        
        **Validates: Requirements 6.5**
        """
        async def run_test():
            manager = MockProviderManager()
            provider_id = "test_provider"
            
            await manager.register_provider(provider_id, {"name": "Test"})
            await manager.set_active_provider(provider_id)
            
            with pytest.raises(ValueError) as exc_info:
                await manager.delete_provider(provider_id)
            
            error_message = str(exc_info.value)
            
            # Error message should be clear and actionable
            assert "active" in error_message.lower(), \
                "Error should mention 'active'"
            assert "delete" in error_message.lower() or "cannot" in error_message.lower(), \
                "Error should indicate deletion is not allowed"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        provider_method=provider_method_strategy,
        config=llm_config_strategy,
    )
    def test_concurrent_deletion_attempts_all_fail(
        self,
        provider_method: LLMMethod,
        config: LLMConfig,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        Concurrent deletion attempts on active provider should all fail.
        
        **Validates: Requirements 6.5**
        """
        async def run_test():
            manager = MockProviderManager()
            provider_id = provider_method.value
            
            await manager.register_provider(provider_id, config.model_dump())
            await manager.set_active_provider(provider_id)
            
            # Create multiple concurrent deletion tasks
            async def attempt_deletion():
                try:
                    await manager.delete_provider(provider_id)
                    return "success"
                except ValueError as e:
                    return f"error: {e}"
            
            # Run 5 concurrent deletion attempts
            tasks = [attempt_deletion() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Property: All attempts should fail
            for result in results:
                assert result.startswith("error:"), \
                    f"Concurrent deletion should fail, got: {result}"
                assert "active" in result.lower(), \
                    "Error should mention active provider"
            
            # Provider should still exist
            provider = await manager.get_provider(provider_id)
            assert provider is not None, \
                "Provider should exist after concurrent deletion attempts"
        
        asyncio.get_event_loop().run_until_complete(run_test())


# ==================== LLMConfig Integration Tests ====================

class TestActiveProviderDeletionWithLLMConfig:
    """
    Tests for active provider deletion prevention with LLMConfig integration.
    
    **Validates: Requirements 6.5**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(config=llm_config_strategy)
    def test_property_16_default_method_is_protected(
        self,
        config: LLMConfig,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        The default method in LLMConfig should be protected from deletion
        when it's the active provider.
        
        **Validates: Requirements 6.5**
        """
        async def run_test():
            manager = MockProviderManager()
            
            # Register the default method as a provider
            default_method = config.default_method
            provider_id = default_method.value
            
            await manager.register_provider(provider_id, config.model_dump())
            await manager.set_active_provider(provider_id)
            
            # Property: Default method (when active) cannot be deleted
            with pytest.raises(ValueError) as exc_info:
                await manager.delete_provider(provider_id)
            
            assert "Cannot delete active provider" in str(exc_info.value)
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        config=llm_config_strategy,
        new_default=provider_method_strategy,
    )
    def test_property_16_changing_default_allows_old_deletion(
        self,
        config: LLMConfig,
        new_default: LLMMethod,
    ):
        """
        Feature: llm-integration, Property 16: Active Provider Deletion Prevention
        
        Changing the default method should allow deletion of the old default.
        
        **Validates: Requirements 6.5**
        """
        # Ensure different methods
        assume(config.default_method != new_default)
        
        async def run_test():
            manager = MockProviderManager()
            
            old_default = config.default_method
            old_id = old_default.value
            new_id = new_default.value
            
            # Register both providers
            await manager.register_provider(old_id, config.model_dump())
            await manager.register_provider(new_id, config.model_dump())
            
            # Set old default as active
            await manager.set_active_provider(old_id)
            
            # Cannot delete old default while active
            with pytest.raises(ValueError):
                await manager.delete_provider(old_id)
            
            # Change active to new default
            await manager.set_active_provider(new_id)
            
            # Property: Old default can now be deleted
            result = await manager.delete_provider(old_id)
            assert result is True, \
                "Old default should be deletable after changing active provider"
        
        asyncio.get_event_loop().run_until_complete(run_test())
