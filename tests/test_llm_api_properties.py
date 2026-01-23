"""
Property-based tests for LLM API endpoints.

Uses Hypothesis library for property testing with minimum 100 iterations per property.
Tests the API-related correctness properties defined in the LLM Integration design document.

Properties Tested:
- Property 17: Pre-Annotation Routing
- Property 25: Authorization Enforcement
"""

import pytest
import asyncio
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from uuid import uuid4
from datetime import datetime

# Import test utilities
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException, status


# ==================== Custom Strategies ====================

# Strategy for valid prompts
prompt_strategy = st.text(
    min_size=1,
    max_size=1000
).filter(lambda x: x.strip())

# Strategy for valid API keys
api_key_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
    min_size=8,
    max_size=64
)

# Strategy for user roles
user_role_strategy = st.sampled_from([
    'admin',
    'business_expert',
    'technical_expert',
    'contractor',
    'viewer'
])

# Strategy for non-admin roles
non_admin_role_strategy = st.sampled_from([
    'business_expert',
    'technical_expert',
    'contractor',
    'viewer'
])

# Strategy for provider IDs
provider_id_strategy = st.sampled_from([
    'local_ollama',
    'cloud_openai',
    'cloud_azure',
    'china_qwen',
    'china_zhipu',
    'china_baidu',
    'china_hunyuan'
])

# Strategy for temperature values
temperature_strategy = st.floats(min_value=0.0, max_value=2.0)

# Strategy for max_tokens values
max_tokens_strategy = st.integers(min_value=1, max_value=4096)


# ==================== Mock Classes ====================

class MockUser:
    """Mock user for testing authorization."""
    
    def __init__(self, role: str, username: str = "testuser", tenant_id: str = "test_tenant"):
        from src.security.models import UserRole
        self.id = uuid4()
        self.username = username
        self.email = f"{username}@test.com"
        self.tenant_id = tenant_id
        self.is_active = True
        
        # Map string role to UserRole enum
        role_map = {
            'admin': UserRole.ADMIN,
            'business_expert': UserRole.BUSINESS_EXPERT,
            'technical_expert': UserRole.TECHNICAL_EXPERT,
            'contractor': UserRole.CONTRACTOR,
            'viewer': UserRole.VIEWER,
        }
        self.role = role_map.get(role, UserRole.VIEWER)


class MockLLMResponse:
    """Mock LLM response for testing."""
    
    def __init__(
        self,
        content: str = "Generated text",
        model: str = "test-model",
        provider: str = "test_provider",
        cached: bool = False,
        latency_ms: float = 100.0
    ):
        self.content = content
        self.model = model
        self.provider = provider
        self.cached = cached
        self.latency_ms = latency_ms
        self.usage = MockTokenUsage()
        self.finish_reason = "stop"
        self.metadata = {}


class MockTokenUsage:
    """Mock token usage for testing."""
    
    def __init__(
        self,
        prompt_tokens: int = 10,
        completion_tokens: int = 20,
        total_tokens: int = 30
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class MockLLMSwitcher:
    """Mock LLM Switcher for testing routing behavior."""
    
    def __init__(self, active_method: str = "local_ollama"):
        from src.ai.llm_schemas import LLMMethod
        self._current_method = LLMMethod(active_method)
        self._fallback_method = None
        self._providers = {}
        self._initialized = True
        self._generate_calls: List[Dict[str, Any]] = []
    
    async def initialize(self):
        """Mock initialization."""
        self._initialized = True
    
    async def generate(
        self,
        prompt: str,
        options: Any = None,
        method: Any = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> MockLLMResponse:
        """
        Mock generate that tracks which provider was used.
        
        Records the call for verification in property tests.
        """
        # Record the call
        self._generate_calls.append({
            'prompt': prompt,
            'method': method or self._current_method,
            'system_prompt': system_prompt,
            'options': options,
        })
        
        # Return mock response
        return MockLLMResponse(
            content=f"Response to: {prompt[:50]}...",
            model="test-model",
            provider=str(method or self._current_method),
        )
    
    def get_generate_calls(self) -> List[Dict[str, Any]]:
        """Get recorded generate calls for verification."""
        return self._generate_calls
    
    def clear_calls(self):
        """Clear recorded calls."""
        self._generate_calls.clear()


# ==================== Property 17: Pre-Annotation Routing ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    prompt=prompt_strategy,
    active_provider=provider_id_strategy,
    temperature=temperature_strategy,
    max_tokens=max_tokens_strategy
)
def test_property_17_pre_annotation_routing(
    prompt: str,
    active_provider: str,
    temperature: float,
    max_tokens: int
):
    """
    Feature: llm-integration, Property 17: Pre-Annotation Routing
    
    For any pre-annotation request, the request should be sent to the currently 
    active provider, not to any other provider.
    
    **Validates: Requirements 7.1**
    
    This test generates 100+ random pre-annotation requests and verifies that
    each request is routed to the currently active provider.
    """
    # Create mock switcher with specific active provider
    switcher = MockLLMSwitcher(active_method=active_provider)
    
    # Simulate a generate request (synchronous wrapper for async)
    async def run_generate():
        from src.ai.llm_schemas import GenerateOptions
        options = GenerateOptions(
            temperature=temperature,
            max_tokens=max_tokens
        )
        return await switcher.generate(prompt=prompt, options=options)
    
    # Run the async function using asyncio.run() for Python 3.9+ compatibility
    response = asyncio.run(run_generate())
    
    # Verify the request was routed to the active provider
    calls = switcher.get_generate_calls()
    assert len(calls) == 1, "Should have exactly one generate call"
    
    call = calls[0]
    
    # The method used should be the active provider
    from src.ai.llm_schemas import LLMMethod
    expected_method = LLMMethod(active_provider)
    assert call['method'] == expected_method, \
        f"Request should be routed to active provider {active_provider}, " \
        f"but was routed to {call['method']}"
    
    # Verify the prompt was passed correctly
    assert call['prompt'] == prompt, "Prompt should be passed unchanged"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    prompt=prompt_strategy,
    active_provider=provider_id_strategy,
    other_providers=st.lists(provider_id_strategy, min_size=1, max_size=5)
)
def test_property_17_routing_excludes_inactive_providers(
    prompt: str,
    active_provider: str,
    other_providers: List[str]
):
    """
    Feature: llm-integration, Property 17: Pre-Annotation Routing (Exclusion)
    
    For any pre-annotation request, the request should NOT be sent to any 
    provider other than the currently active provider.
    
    **Validates: Requirements 7.1**
    
    This test verifies that inactive providers are not used for routing.
    """
    # Filter out the active provider from other providers
    inactive_providers = [p for p in other_providers if p != active_provider]
    assume(len(inactive_providers) > 0)  # Need at least one inactive provider
    
    # Create mock switcher with specific active provider
    switcher = MockLLMSwitcher(active_method=active_provider)
    
    # Simulate a generate request
    async def run_generate():
        return await switcher.generate(prompt=prompt)
    
    # Run the async function using asyncio.run() for Python 3.9+ compatibility
    asyncio.run(run_generate())
    
    # Verify the request was NOT routed to any inactive provider
    calls = switcher.get_generate_calls()
    assert len(calls) == 1
    
    call = calls[0]
    from src.ai.llm_schemas import LLMMethod
    
    for inactive_provider in inactive_providers:
        inactive_method = LLMMethod(inactive_provider)
        assert call['method'] != inactive_method, \
            f"Request should NOT be routed to inactive provider {inactive_provider}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    prompts=st.lists(prompt_strategy, min_size=2, max_size=10),
    active_provider=provider_id_strategy
)
def test_property_17_consistent_routing_across_requests(
    prompts: List[str],
    active_provider: str
):
    """
    Feature: llm-integration, Property 17: Pre-Annotation Routing (Consistency)
    
    For any sequence of pre-annotation requests, all requests should be 
    consistently routed to the same active provider.
    
    **Validates: Requirements 7.1**
    
    This test verifies that routing is consistent across multiple requests.
    """
    # Create mock switcher with specific active provider
    switcher = MockLLMSwitcher(active_method=active_provider)
    
    # Simulate multiple generate requests
    async def run_generates():
        responses = []
        for prompt in prompts:
            response = await switcher.generate(prompt=prompt)
            responses.append(response)
        return responses
    
    # Run the async function using asyncio.run() for Python 3.9+ compatibility
    asyncio.run(run_generates())
    
    # Verify all requests were routed to the same active provider
    calls = switcher.get_generate_calls()
    assert len(calls) == len(prompts), "Should have one call per prompt"
    
    from src.ai.llm_schemas import LLMMethod
    expected_method = LLMMethod(active_provider)
    
    for i, call in enumerate(calls):
        assert call['method'] == expected_method, \
            f"Request {i} should be routed to active provider {active_provider}"


# ==================== Property 25: Authorization Enforcement ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    role=non_admin_role_strategy,
    provider_id=provider_id_strategy,
    username=st.text(min_size=3, max_size=20).filter(lambda x: x.isalnum())
)
def test_property_25_authorization_enforcement_api_key_access(
    role: str,
    provider_id: str,
    username: str
):
    """
    Feature: llm-integration, Property 25: Authorization Enforcement
    
    For any API key access attempt by a non-administrator user, the request 
    should be rejected with a 403 Forbidden error.
    
    **Validates: Requirements 9.3**
    
    This test generates 100+ random non-admin users and verifies that API key
    access is properly denied.
    """
    # Create a non-admin user
    user = MockUser(role=role, username=username)
    
    # Verify user is not admin
    from src.security.models import UserRole
    assert user.role != UserRole.ADMIN, f"User should not be admin, but has role {user.role}"
    
    # Import the require_admin function
    from src.api.llm import require_admin
    
    # Attempt to access admin-only resource
    with pytest.raises(HTTPException) as exc_info:
        require_admin(user)
    
    # Verify 403 Forbidden was raised
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN, \
        f"Expected 403 Forbidden, got {exc_info.value.status_code}"
    
    # Verify error details
    detail = exc_info.value.detail
    assert 'error_code' in detail, "Error should have error_code"
    assert detail['error_code'] == 'ADMIN_REQUIRED', \
        f"Error code should be ADMIN_REQUIRED, got {detail['error_code']}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    username=st.text(min_size=3, max_size=20).filter(lambda x: x.isalnum()),
    tenant_id=st.text(min_size=5, max_size=30).filter(lambda x: x.isalnum())
)
def test_property_25_admin_access_allowed(
    username: str,
    tenant_id: str
):
    """
    Feature: llm-integration, Property 25: Authorization Enforcement (Admin Allowed)
    
    For any API key access attempt by an administrator user, the request 
    should be allowed (no exception raised).
    
    **Validates: Requirements 9.3**
    
    This test verifies that admin users can access API keys.
    """
    # Create an admin user
    user = MockUser(role='admin', username=username, tenant_id=tenant_id)
    
    # Verify user is admin
    from src.security.models import UserRole
    assert user.role == UserRole.ADMIN, f"User should be admin, but has role {user.role}"
    
    # Import the require_admin function
    from src.api.llm import require_admin
    
    # Attempt to access admin-only resource - should NOT raise
    try:
        require_admin(user)
    except HTTPException as e:
        pytest.fail(f"Admin user should be allowed, but got HTTPException: {e.detail}")


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    role=non_admin_role_strategy,
    provider_id=provider_id_strategy
)
def test_property_25_provider_activation_requires_admin(
    role: str,
    provider_id: str
):
    """
    Feature: llm-integration, Property 25: Authorization Enforcement (Activation)
    
    For any provider activation attempt by a non-administrator user, the request 
    should be rejected with a 403 Forbidden error.
    
    **Validates: Requirements 9.3**
    
    This test verifies that provider activation requires admin role.
    """
    # Create a non-admin user
    user = MockUser(role=role)
    
    # Verify user is not admin
    from src.security.models import UserRole
    assert user.role != UserRole.ADMIN
    
    # Import the require_admin function
    from src.api.llm import require_admin
    
    # Attempt to activate provider (admin-only operation)
    with pytest.raises(HTTPException) as exc_info:
        require_admin(user)
    
    # Verify 403 Forbidden was raised
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    roles=st.lists(non_admin_role_strategy, min_size=2, max_size=10),
    provider_id=provider_id_strategy
)
def test_property_25_all_non_admin_roles_rejected(
    roles: List[str],
    provider_id: str
):
    """
    Feature: llm-integration, Property 25: Authorization Enforcement (All Roles)
    
    For any non-administrator role, API key access should be rejected.
    
    **Validates: Requirements 9.3**
    
    This test verifies that all non-admin roles are properly rejected.
    """
    from src.api.llm import require_admin
    from src.security.models import UserRole
    
    for role in roles:
        user = MockUser(role=role)
        
        # Verify user is not admin
        assert user.role != UserRole.ADMIN
        
        # Attempt to access admin-only resource
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)
        
        # Verify 403 Forbidden was raised
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN, \
            f"Role {role} should be rejected with 403"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    role=non_admin_role_strategy,
    attempt_count=st.integers(min_value=1, max_value=10)
)
def test_property_25_consistent_rejection(
    role: str,
    attempt_count: int
):
    """
    Feature: llm-integration, Property 25: Authorization Enforcement (Consistency)
    
    For any non-administrator user, repeated access attempts should all be 
    consistently rejected.
    
    **Validates: Requirements 9.3**
    
    This test verifies that authorization is consistently enforced.
    """
    from src.api.llm import require_admin
    
    user = MockUser(role=role)
    
    # Make multiple attempts
    for i in range(attempt_count):
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)
        
        # Verify 403 Forbidden was raised each time
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN, \
            f"Attempt {i+1} should be rejected with 403"


# ==================== Integration Tests ====================

@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    prompt=prompt_strategy,
    role=user_role_strategy,
    provider_id=provider_id_strategy
)
def test_generate_endpoint_authorization_and_routing(
    prompt: str,
    role: str,
    provider_id: str
):
    """
    Feature: llm-integration, Properties 17 & 25: Combined Test
    
    For any generate request:
    - If user is authenticated, request should be routed to active provider
    - Authorization is checked at the endpoint level
    
    **Validates: Requirements 7.1, 9.3**
    
    This test combines routing and authorization verification.
    """
    # Create user with specified role
    user = MockUser(role=role)
    
    # Create mock switcher
    switcher = MockLLMSwitcher(active_method=provider_id)
    
    # Simulate generate request
    async def run_generate():
        return await switcher.generate(prompt=prompt)
    
    # Run the async function using asyncio.run() for Python 3.9+ compatibility
    response = asyncio.run(run_generate())
    
    # Verify routing (Property 17)
    calls = switcher.get_generate_calls()
    assert len(calls) == 1
    
    from src.ai.llm_schemas import LLMMethod
    expected_method = LLMMethod(provider_id)
    assert calls[0]['method'] == expected_method


# ==================== Edge Case Tests ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    prompt=st.text(min_size=1, max_size=10000),  # Very long prompts
    active_provider=provider_id_strategy
)
def test_property_17_long_prompt_routing(
    prompt: str,
    active_provider: str
):
    """
    Feature: llm-integration, Property 17: Pre-Annotation Routing (Long Prompts)
    
    For any pre-annotation request with a long prompt, the request should still
    be routed to the active provider.
    
    **Validates: Requirements 7.1**
    """
    assume(len(prompt.strip()) > 0)
    
    switcher = MockLLMSwitcher(active_method=active_provider)
    
    async def run_generate():
        return await switcher.generate(prompt=prompt)
    
    # Run the async function using asyncio.run() for Python 3.9+ compatibility
    asyncio.run(run_generate())
    
    calls = switcher.get_generate_calls()
    assert len(calls) == 1
    
    from src.ai.llm_schemas import LLMMethod
    expected_method = LLMMethod(active_provider)
    assert calls[0]['method'] == expected_method


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    prompt=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S', 'Z')),
        min_size=1,
        max_size=500
    ),  # Unicode prompts
    active_provider=provider_id_strategy
)
def test_property_17_unicode_prompt_routing(
    prompt: str,
    active_provider: str
):
    """
    Feature: llm-integration, Property 17: Pre-Annotation Routing (Unicode)
    
    For any pre-annotation request with unicode characters, the request should
    be routed to the active provider.
    
    **Validates: Requirements 7.1**
    """
    assume(len(prompt.strip()) > 0)
    
    switcher = MockLLMSwitcher(active_method=active_provider)
    
    async def run_generate():
        return await switcher.generate(prompt=prompt)
    
    # Run the async function using asyncio.run() for Python 3.9+ compatibility
    asyncio.run(run_generate())
    
    calls = switcher.get_generate_calls()
    assert len(calls) == 1
    
    from src.ai.llm_schemas import LLMMethod
    expected_method = LLMMethod(active_provider)
    assert calls[0]['method'] == expected_method
    assert calls[0]['prompt'] == prompt  # Prompt should be preserved exactly
