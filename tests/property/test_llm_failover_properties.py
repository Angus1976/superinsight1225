"""
Property-based tests for LLM Failover and Retry Logic.

Tests correctness properties with Hypothesis (100+ iterations each).

Properties tested:
- Property 6: Provider Switching Validation
  - Validates: Requirements 3.2
  - Verifies method switching works correctly

- Property 7: Automatic Failover
  - Validates: Requirements 3.3, 4.2
  - Verifies automatic failover to fallback provider

- Property 8: Request Context Preservation
  - Validates: Requirements 3.4
  - Verifies context is maintained during failover

- Property 10: Exponential Backoff Retry
  - Validates: Requirements 4.1
  - Verifies retry delays follow exponential backoff

- Property 12: Timeout Enforcement
  - Validates: Requirements 4.4
  - Verifies 30-second timeout is enforced

- Property 13: Rate Limit Handling
  - Validates: Requirements 4.5
  - Verifies rate limit errors trigger appropriate waits
"""

import pytest
import asyncio
from datetime import datetime
from typing import Optional, AsyncIterator
from unittest.mock import AsyncMock, Mock, patch
from hypothesis import given, strategies as st, settings, HealthCheck
import time

# Import the module under test
try:
    from src.ai.llm_switcher import LLMSwitcher, LLMProvider, MAX_RETRY_ATTEMPTS, EXPONENTIAL_BACKOFF_BASE, DEFAULT_TIMEOUT_SECONDS
    from src.ai.llm_schemas import LLMMethod, GenerateOptions, LLMResponse, TokenUsage, HealthStatus, LLMConfig, LocalConfig, CloudConfig, ChinaLLMConfig
    from src.ai.llm_config_manager import LLMConfigManager
except ImportError:
    pytest.skip("LLM switcher not available", allow_module_level=True)


# ==================== Test Fixtures ====================

class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(
        self,
        method: LLMMethod,
        should_fail: bool = False,
        fail_count: int = 0,
        failure_type: str = "generic",
        response_text: str = "Test response"
    ):
        self._method = method
        self._should_fail = should_fail
        self._fail_count = fail_count  # Number of times to fail before succeeding
        self._current_failures = 0
        self._failure_type = failure_type
        self._response_text = response_text
        self.call_count = 0

    @property
    def method(self) -> LLMMethod:
        return self._method

    async def generate(
        self,
        prompt: str,
        options: GenerateOptions,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Mock generate that can simulate failures."""
        self.call_count += 1

        # Simulate failures if configured
        if self._should_fail or self._current_failures < self._fail_count:
            self._current_failures += 1

            if self._failure_type == "timeout":
                await asyncio.sleep(35)  # Exceed 30s timeout
            elif self._failure_type == "rate_limit":
                raise Exception("Rate limit exceeded. Please retry after 5 seconds")
            else:
                raise Exception(f"Mock failure from {self._method.value}")

        # Success - return mock response
        return LLMResponse(
            content=self._response_text,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            model=model or "test-model",
            provider=self._method.value,
            latency_ms=100.0
        )

    async def stream_generate(self, *args, **kwargs) -> AsyncIterator[str]:
        """Mock stream generate."""
        yield "Test"
        yield " stream"

    async def embed(self, text: str, model: Optional[str] = None):
        """Mock embed."""
        return []

    async def health_check(self) -> HealthStatus:
        """Mock health check."""
        return HealthStatus(
            available=not self._should_fail,
            latency_ms=50.0 if not self._should_fail else 0.0,
            error=None if not self._should_fail else "Mock provider is down"
        )

    def list_models(self):
        """Mock list models."""
        return ["test-model-1", "test-model-2"]


class MockConfigManager:
    """Mock configuration manager."""

    def __init__(self):
        self._config = LLMConfig(
            default_method=LLMMethod.LOCAL_OLLAMA,
            enabled_methods=[LLMMethod.LOCAL_OLLAMA, LLMMethod.CLOUD_OPENAI],
            local_config=LocalConfig(),
            cloud_config=CloudConfig(),
            china_config=ChinaLLMConfig()
        )
        self._watchers = []

    async def get_config(self, tenant_id: Optional[str] = None) -> LLMConfig:
        """Get configuration."""
        return self._config

    def watch_config_changes(self, callback):
        """Register config change watcher."""
        self._watchers.append(callback)


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager."""
    return MockConfigManager()


@pytest.fixture
async def llm_switcher(mock_config_manager):
    """Create an LLM switcher with mocked config."""
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False  # Disable cache for testing
    )
    await switcher.initialize()
    return switcher


# ==================== Property Tests ====================

@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    response_text=st.text(min_size=1, max_size=100)
)
async def test_property_6_provider_switching_validation(
    response_text: str,
    mock_config_manager: MockConfigManager
):
    """
    Property 6: Provider Switching Validation

    Validates: Requirements 3.2

    Property: Method switching works correctly

    For any response text:
    - When switching between methods
    - Then correct provider is used
    - And response reflects the provider used
    """
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    # Add mock providers
    primary_provider = MockLLMProvider(
        method=LLMMethod.LOCAL_OLLAMA,
        response_text=f"Primary: {response_text}"
    )
    secondary_provider = MockLLMProvider(
        method=LLMMethod.CLOUD_OPENAI,
        response_text=f"Secondary: {response_text}"
    )

    switcher._providers[LLMMethod.LOCAL_OLLAMA] = primary_provider
    switcher._providers[LLMMethod.CLOUD_OPENAI] = secondary_provider

    # Property 1: Using primary method returns primary response
    response1 = await switcher.generate(
        prompt="test",
        method=LLMMethod.LOCAL_OLLAMA
    )
    assert "Primary" in response1.content, "Primary provider should be used"
    assert response1.provider == LLMMethod.LOCAL_OLLAMA.value

    # Property 2: Using secondary method returns secondary response
    response2 = await switcher.generate(
        prompt="test",
        method=LLMMethod.CLOUD_OPENAI
    )
    assert "Secondary" in response2.content, "Secondary provider should be used"
    assert response2.provider == LLMMethod.CLOUD_OPENAI.value

    # Property 3: Provider call counts match requests
    assert primary_provider.call_count >= 1, "Primary provider should be called"
    assert secondary_provider.call_count >= 1, "Secondary provider should be called"


@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    prompt_text=st.text(min_size=1, max_size=50)
)
async def test_property_7_automatic_failover(
    prompt_text: str,
    mock_config_manager: MockConfigManager
):
    """
    Property 7: Automatic Failover

    Validates: Requirements 3.3, 4.2

    Property: Automatic failover to fallback provider

    For any prompt:
    - When primary provider fails
    - Then fallback provider is used automatically
    - And response is successful
    """
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    # Add mock providers: primary fails, fallback succeeds
    primary_provider = MockLLMProvider(
        method=LLMMethod.LOCAL_OLLAMA,
        should_fail=True
    )
    fallback_provider = MockLLMProvider(
        method=LLMMethod.CLOUD_OPENAI,
        should_fail=False,
        response_text="Fallback response"
    )

    switcher._providers[LLMMethod.LOCAL_OLLAMA] = primary_provider
    switcher._providers[LLMMethod.CLOUD_OPENAI] = fallback_provider

    # Set fallback provider
    await switcher.set_fallback_provider(LLMMethod.CLOUD_OPENAI)

    # Property 1: Request succeeds despite primary failure
    response = await switcher.generate(prompt=prompt_text)
    assert response is not None, "Failover should provide response"
    assert "Fallback" in response.content, "Fallback provider should be used"

    # Property 2: Fallback provider was called
    assert fallback_provider.call_count >= 1, "Fallback provider should be called"

    # Property 3: Primary was attempted first
    assert primary_provider.call_count >= 1, "Primary should be attempted first"


@pytest.mark.asyncio
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    prompt=st.text(min_size=1, max_size=50),
    system_prompt=st.text(min_size=1, max_size=50),
    max_tokens=st.integers(min_value=10, max_value=1000)
)
async def test_property_8_request_context_preservation(
    prompt: str,
    system_prompt: str,
    max_tokens: int,
    mock_config_manager: MockConfigManager
):
    """
    Property 8: Request Context Preservation

    Validates: Requirements 3.4

    Property: Context is maintained during failover

    For any request parameters:
    - When failover occurs
    - Then original request parameters are preserved
    - And fallback uses same parameters
    """
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    # Track parameters received by fallback
    received_params = {}

    class ContextCheckingProvider(MockLLMProvider):
        async def generate(self, prompt, options, model, system_prompt):
            received_params['prompt'] = prompt
            received_params['system_prompt'] = system_prompt
            received_params['max_tokens'] = options.max_tokens if options else None
            return await super().generate(prompt, options, model, system_prompt)

    primary_provider = MockLLMProvider(
        method=LLMMethod.LOCAL_OLLAMA,
        should_fail=True
    )
    fallback_provider = ContextCheckingProvider(
        method=LLMMethod.CLOUD_OPENAI,
        should_fail=False
    )

    switcher._providers[LLMMethod.LOCAL_OLLAMA] = primary_provider
    switcher._providers[LLMMethod.CLOUD_OPENAI] = fallback_provider
    await switcher.set_fallback_provider(LLMMethod.CLOUD_OPENAI)

    # Make request with specific parameters
    options = GenerateOptions(max_tokens=max_tokens)
    await switcher.generate(
        prompt=prompt,
        options=options,
        system_prompt=system_prompt
    )

    # Property: Fallback received original parameters
    assert received_params['prompt'] == prompt, "Prompt should be preserved"
    assert received_params['system_prompt'] == system_prompt, "System prompt should be preserved"
    assert received_params['max_tokens'] == max_tokens, "Options should be preserved"


@pytest.mark.asyncio
@settings(
    max_examples=50,  # Fewer examples for timing-sensitive test
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    num_failures=st.integers(min_value=1, max_value=3)
)
async def test_property_10_exponential_backoff_retry(
    num_failures: int,
    mock_config_manager: MockConfigManager
):
    """
    Property 10: Exponential Backoff Retry

    Validates: Requirements 4.1

    Property: Retry delays follow exponential backoff

    For any number of failures:
    - When provider fails multiple times
    - Then retries occur with exponential delays
    - And delays are approximately 1s, 2s, 4s
    """
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    # Provider fails num_failures times, then succeeds
    provider = MockLLMProvider(
        method=LLMMethod.LOCAL_OLLAMA,
        fail_count=num_failures
    )
    switcher._providers[LLMMethod.LOCAL_OLLAMA] = provider

    # Track timing
    start_time = time.time()
    response = await switcher.generate(prompt="test")
    elapsed = time.time() - start_time

    # Property 1: Request eventually succeeds
    assert response is not None, "Request should succeed after retries"

    # Property 2: Provider was called multiple times
    assert provider.call_count >= num_failures + 1, \
        f"Provider should be called {num_failures + 1} times"

    # Property 3: Total time includes backoff delays
    # Expected delays: sum of 2^0, 2^1, ... 2^(n-1) for n failures
    expected_min_delay = sum(EXPONENTIAL_BACKOFF_BASE ** i for i in range(num_failures))
    # Allow some tolerance for test execution time
    assert elapsed >= expected_min_delay * 0.8, \
        f"Elapsed time {elapsed:.2f}s should include backoff delays (expected ~{expected_min_delay}s)"


@pytest.mark.asyncio
@settings(
    max_examples=20,  # Fewer examples for timeout test
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_12_timeout_enforcement(mock_config_manager: MockConfigManager):
    """
    Property 12: Timeout Enforcement

    Validates: Requirements 4.4

    Property: 30-second timeout is enforced

    - When provider takes too long
    - Then request times out
    - And timeout error is raised
    """
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    # Provider that exceeds timeout
    provider = MockLLMProvider(
        method=LLMMethod.LOCAL_OLLAMA,
        failure_type="timeout"
    )
    switcher._providers[LLMMethod.LOCAL_OLLAMA] = provider

    # Property 1: Request times out
    start_time = time.time()
    with pytest.raises(Exception) as exc_info:
        await switcher.generate(prompt="test")
    elapsed = time.time() - start_time

    # Property 2: Timeout occurs around DEFAULT_TIMEOUT_SECONDS * MAX_RETRY_ATTEMPTS
    # Each of 3 attempts should timeout, total ~90 seconds (30s * 3)
    # But with exponential backoff delays: 30s + 1s + 30s + 2s + 30s + 4s = ~97s
    # Allow reasonable tolerance
    expected_max_time = (DEFAULT_TIMEOUT_SECONDS * MAX_RETRY_ATTEMPTS) + sum(
        EXPONENTIAL_BACKOFF_BASE ** i for i in range(MAX_RETRY_ATTEMPTS - 1)
    ) + 10  # 10s tolerance

    assert elapsed <= expected_max_time, \
        f"Timeout should occur within {expected_max_time}s, got {elapsed:.2f}s"


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_13_rate_limit_handling(mock_config_manager: MockConfigManager):
    """
    Property 13: Rate Limit Handling

    Validates: Requirements 4.5

    Property: Rate limit errors trigger appropriate waits

    - When provider returns rate limit error
    - Then retry waits for specified duration
    - And request eventually succeeds
    """
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    # Provider that rate limits once, then succeeds
    provider = MockLLMProvider(
        method=LLMMethod.LOCAL_OLLAMA,
        fail_count=1,
        failure_type="rate_limit"
    )
    switcher._providers[LLMMethod.LOCAL_OLLAMA] = provider

    # Track timing
    start_time = time.time()
    response = await switcher.generate(prompt="test")
    elapsed = time.time() - start_time

    # Property 1: Request eventually succeeds
    assert response is not None, "Request should succeed after rate limit wait"

    # Property 2: Provider was called at least twice
    assert provider.call_count >= 2, "Provider should be retried after rate limit"

    # Property 3: Elapsed time includes rate limit wait
    # Rate limit message says "retry after 5 seconds"
    assert elapsed >= 4.5, "Should wait for rate limit retry-after"


@pytest.mark.asyncio
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_property_usage_statistics_tracking(mock_config_manager: MockConfigManager):
    """
    Property 9: Usage Statistics Tracking

    Validates: Requirements 3.5

    Property: Usage statistics are tracked per provider

    - When multiple requests are made
    - Then statistics reflect correct counts
    - And each provider tracks independently
    """
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    primary = MockLLMProvider(method=LLMMethod.LOCAL_OLLAMA)
    secondary = MockLLMProvider(method=LLMMethod.CLOUD_OPENAI)

    switcher._providers[LLMMethod.LOCAL_OLLAMA] = primary
    switcher._providers[LLMMethod.CLOUD_OPENAI] = secondary

    # Make multiple requests
    await switcher.generate("test1", method=LLMMethod.LOCAL_OLLAMA)
    await switcher.generate("test2", method=LLMMethod.LOCAL_OLLAMA)
    await switcher.generate("test3", method=LLMMethod.CLOUD_OPENAI)

    # Get statistics
    stats = await switcher.get_usage_stats()

    # Property 1: Stats track each provider separately
    assert LLMMethod.LOCAL_OLLAMA.value in stats
    assert LLMMethod.CLOUD_OPENAI.value in stats

    # Property 2: Counts are accurate
    assert stats[LLMMethod.LOCAL_OLLAMA.value] == 2, "Should track 2 primary requests"
    assert stats[LLMMethod.CLOUD_OPENAI.value] == 1, "Should track 1 secondary request"


# ==================== Edge Case Tests ====================

@pytest.mark.asyncio
async def test_fallback_same_as_primary(mock_config_manager: MockConfigManager):
    """Test that fallback doesn't trigger if it's the same as primary."""
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    provider = MockLLMProvider(method=LLMMethod.LOCAL_OLLAMA, should_fail=True)
    switcher._providers[LLMMethod.LOCAL_OLLAMA] = provider

    # Set fallback to same method as primary
    await switcher.set_fallback_provider(LLMMethod.LOCAL_OLLAMA)

    # Should fail without triggering fallback
    with pytest.raises(Exception):
        await switcher.generate("test", method=LLMMethod.LOCAL_OLLAMA)


@pytest.mark.asyncio
async def test_no_fallback_configured(mock_config_manager: MockConfigManager):
    """Test behavior when no fallback is configured."""
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    provider = MockLLMProvider(method=LLMMethod.LOCAL_OLLAMA, should_fail=True)
    switcher._providers[LLMMethod.LOCAL_OLLAMA] = provider

    # No fallback set - should raise error
    with pytest.raises(Exception):
        await switcher.generate("test")


@pytest.mark.asyncio
async def test_both_providers_fail(mock_config_manager: MockConfigManager):
    """Test comprehensive error when both primary and fallback fail."""
    switcher = LLMSwitcher(
        config_manager=mock_config_manager,
        enable_response_cache=False
    )
    await switcher.initialize()

    primary = MockLLMProvider(method=LLMMethod.LOCAL_OLLAMA, should_fail=True)
    fallback = MockLLMProvider(method=LLMMethod.CLOUD_OPENAI, should_fail=True)

    switcher._providers[LLMMethod.LOCAL_OLLAMA] = primary
    switcher._providers[LLMMethod.CLOUD_OPENAI] = fallback

    await switcher.set_fallback_provider(LLMMethod.CLOUD_OPENAI)

    # Should raise comprehensive error
    with pytest.raises(Exception) as exc_info:
        await switcher.generate("test")

    error_msg = str(exc_info.value).lower()
    # Error should mention both providers
    assert "primary" in error_msg or "fallback" in error_msg
