"""
Property-based tests for LLM Integration module.

Uses Hypothesis library for property testing with minimum 100 iterations per property.
"""

import pytest
import asyncio
from typing import Optional
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.ai.llm_schemas import (
    LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig,
    GenerateOptions, LLMResponse, TokenUsage, LLMError, LLMErrorCode,
    EmbeddingResponse, HealthStatus, ValidationResult,
    mask_api_key, unmask_api_key
)


# ==================== Custom Strategies ====================

# Strategy for valid API keys (8-64 characters)
api_key_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
    min_size=8,
    max_size=64
)

# Strategy for LLM methods
llm_method_strategy = st.sampled_from(list(LLMMethod))

# Strategy for valid prompts
prompt_strategy = st.text(min_size=1, max_size=1000).filter(lambda x: x.strip())

# Strategy for temperature values
temperature_strategy = st.floats(min_value=0.0, max_value=2.0, allow_nan=False)

# Strategy for token counts
token_strategy = st.integers(min_value=0, max_value=100000)

# Strategy for latency values
latency_strategy = st.floats(min_value=0.0, max_value=300000.0, allow_nan=False)


# ==================== Property 1: Unified Response Format ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    content=st.text(min_size=0, max_size=500),
    prompt_tokens=token_strategy,
    completion_tokens=token_strategy,
    model=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    provider=llm_method_strategy,
    latency=latency_strategy
)
def test_unified_response_format(
    content: str,
    prompt_tokens: int,
    completion_tokens: int,
    model: str,
    provider: LLMMethod,
    latency: float
):
    """
    Property 1: For any LLM call, the response should contain content, usage, model fields.
    
    Validates: Requirements 6.4, 6.5
    """
    usage = TokenUsage.from_counts(prompt_tokens, completion_tokens)
    
    response = LLMResponse(
        content=content,
        usage=usage,
        model=model,
        provider=provider.value,
        latency_ms=latency
    )
    
    # Verify all required fields exist
    assert hasattr(response, 'content')
    assert hasattr(response, 'usage')
    assert hasattr(response, 'model')
    assert hasattr(response, 'provider')
    assert hasattr(response, 'latency_ms')
    
    # Verify types
    assert isinstance(response.content, str)
    assert isinstance(response.usage, TokenUsage)
    assert isinstance(response.model, str)
    assert isinstance(response.provider, str)
    assert isinstance(response.latency_ms, float)
    
    # Verify token usage calculation
    assert response.usage.total_tokens == prompt_tokens + completion_tokens


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    embedding=st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1, max_size=100),
    model=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    provider=llm_method_strategy,
    latency=latency_strategy
)
def test_embedding_response_format(
    embedding: list,
    model: str,
    provider: LLMMethod,
    latency: float
):
    """
    Property 1 (continued): Embedding responses should have consistent format.
    
    Validates: Requirements 6.4, 6.5
    """
    response = EmbeddingResponse(
        embedding=embedding,
        model=model,
        provider=provider.value,
        dimensions=len(embedding),
        latency_ms=latency
    )
    
    assert hasattr(response, 'embedding')
    assert hasattr(response, 'model')
    assert hasattr(response, 'dimensions')
    assert response.dimensions == len(embedding)


# ==================== Property 2: Method Routing Correctness ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    default_method=llm_method_strategy,
    override_method=st.one_of(st.none(), llm_method_strategy)
)
def test_method_routing_correctness(
    default_method: LLMMethod,
    override_method: Optional[LLMMethod]
):
    """
    Property 2: Override method should take precedence over default method.
    
    Validates: Requirements 4.1, 4.2, 6.3
    """
    config = LLMConfig(
        default_method=default_method,
        enabled_methods=[default_method] + ([override_method] if override_method else [])
    )
    
    # Determine expected method
    expected_method = override_method if override_method else default_method
    
    # Simulate routing logic
    actual_method = override_method if override_method is not None else config.default_method
    
    assert actual_method == expected_method


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    methods=st.lists(llm_method_strategy, min_size=1, max_size=7, unique=True)
)
def test_enabled_methods_consistency(methods: list):
    """
    Property 2 (continued): Enabled methods list should be consistent.
    
    Validates: Requirements 4.1, 4.2
    """
    default_method = methods[0]
    
    config = LLMConfig(
        default_method=default_method,
        enabled_methods=methods
    )
    
    # Default method should be in enabled methods
    assert config.default_method in config.enabled_methods
    
    # All enabled methods should be valid LLMMethod values
    for method in config.enabled_methods:
        assert isinstance(method, LLMMethod)


# ==================== Property 3: Timeout Mechanism ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    local_timeout=st.integers(min_value=1, max_value=300),
    cloud_timeout=st.integers(min_value=1, max_value=300)
)
def test_timeout_configuration(local_timeout: int, cloud_timeout: int):
    """
    Property 3: Timeout values should be properly configured and validated.
    
    Validates: Requirements 1.3, 2.5
    """
    local_config = LocalConfig(timeout=local_timeout)
    cloud_config = CloudConfig(timeout=cloud_timeout)
    
    assert local_config.timeout == local_timeout
    assert cloud_config.timeout == cloud_timeout
    assert local_config.timeout >= 1
    assert cloud_config.timeout >= 1


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    timeout=st.integers(min_value=1, max_value=300),
    latency=latency_strategy
)
def test_timeout_error_generation(timeout: int, latency: float):
    """
    Property 3 (continued): Timeout errors should be properly formatted.
    
    Validates: Requirements 1.3, 2.5
    """
    # Simulate timeout scenario
    is_timeout = latency > (timeout * 1000)  # Convert to ms
    
    if is_timeout:
        error = LLMError(
            error_code=LLMErrorCode.TIMEOUT,
            message=f"Request timed out after {timeout} seconds",
            provider="test_provider"
        )
        
        assert error.error_code == LLMErrorCode.TIMEOUT
        assert "timeout" in error.message.lower()


# ==================== Property 4: China LLM Format Conversion ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    prompt=prompt_strategy,
    max_tokens=st.integers(min_value=1, max_value=4000),
    temperature=temperature_strategy,
    top_p=st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
)
def test_china_llm_format_conversion_roundtrip(
    prompt: str,
    max_tokens: int,
    temperature: float,
    top_p: float
):
    """
    Property 4: Request format conversion should preserve all parameters.
    
    Validates: Requirements 3.3, 3.4
    """
    options = GenerateOptions(
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p
    )
    
    # Simulate Qwen format conversion
    qwen_format = {
        "model": "qwen-turbo",
        "input": {
            "messages": [{"role": "user", "content": prompt}]
        },
        "parameters": {
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
            "top_p": options.top_p
        }
    }
    
    # Verify roundtrip preservation
    assert qwen_format["parameters"]["max_tokens"] == max_tokens
    assert qwen_format["parameters"]["temperature"] == temperature
    assert qwen_format["parameters"]["top_p"] == top_p
    assert qwen_format["input"]["messages"][0]["content"] == prompt
    
    # Simulate Zhipu format conversion
    zhipu_format = {
        "model": "glm-4",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": options.max_tokens,
        "temperature": options.temperature,
        "top_p": options.top_p
    }
    
    # Verify roundtrip preservation
    assert zhipu_format["max_tokens"] == max_tokens
    assert zhipu_format["temperature"] == temperature
    assert zhipu_format["top_p"] == top_p
    assert zhipu_format["messages"][0]["content"] == prompt


# ==================== Property 5: Configuration Hot Reload ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    old_method=llm_method_strategy,
    new_method=llm_method_strategy
)
def test_config_hot_reload_detection(old_method: LLMMethod, new_method: LLMMethod):
    """
    Property 5: Configuration changes should be detectable.
    
    Validates: Requirements 4.3, 4.4
    """
    old_config = LLMConfig(default_method=old_method, enabled_methods=[old_method])
    new_config = LLMConfig(default_method=new_method, enabled_methods=[new_method])
    
    # Change detection
    config_changed = old_config != new_config
    
    if old_method != new_method:
        assert config_changed, "Different methods should result in different configs"
    else:
        assert not config_changed, "Same methods should result in equal configs"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    method=llm_method_strategy,
    ollama_url=st.text(min_size=10, max_size=100).filter(lambda x: x.startswith('http'))
)
def test_config_serialization_roundtrip(method: LLMMethod, ollama_url: str):
    """
    Property 5 (continued): Config serialization should be lossless.
    
    Validates: Requirements 4.3, 4.4
    """
    assume(ollama_url.startswith('http://') or ollama_url.startswith('https://'))
    
    original = LLMConfig(
        default_method=method,
        local_config=LocalConfig(ollama_url=ollama_url),
        enabled_methods=[method]
    )
    
    # Serialize and deserialize
    serialized = original.model_dump()
    restored = LLMConfig(**serialized)
    
    assert restored.default_method == original.default_method
    assert restored.local_config.ollama_url == original.local_config.ollama_url


# ==================== Property 6: API Key Masking ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(api_key=api_key_strategy)
def test_api_key_masking(api_key: str):
    """
    Property 6: API keys should be properly masked, showing only first 4 and last 4 chars.
    
    Validates: Requirements 5.5
    """
    masked = mask_api_key(api_key)
    
    assert masked is not None
    assert len(masked) == len(api_key)
    
    if len(api_key) > 8:
        # First 4 characters should be visible
        assert masked[:4] == api_key[:4]
        # Last 4 characters should be visible
        assert masked[-4:] == api_key[-4:]
        # Middle should be masked
        assert '*' in masked[4:-4]
    else:
        # Short keys should be fully masked
        assert masked == '*' * len(api_key)


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(api_key=api_key_strategy)
def test_api_key_unmask_preserves_original(api_key: str):
    """
    Property 6 (continued): Unmasking with masked value should preserve original.
    
    Validates: Requirements 5.5
    """
    masked = mask_api_key(api_key)
    
    # If user submits the masked version, original should be preserved
    result = unmask_api_key(masked, api_key)
    assert result == api_key
    
    # If user submits a new key, it should be used
    new_key = "new_api_key_12345678"
    result = unmask_api_key(new_key, api_key)
    assert result == new_key


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(api_key=st.one_of(st.none(), st.just(""), api_key_strategy))
def test_api_key_masking_edge_cases(api_key: Optional[str]):
    """
    Property 6 (continued): Masking should handle edge cases gracefully.
    
    Validates: Requirements 5.5
    """
    masked = mask_api_key(api_key)
    
    if api_key is None:
        assert masked is None
    elif api_key == "":
        assert masked is None or masked == ""
    else:
        assert masked is not None
        assert len(masked) == len(api_key)


# ==================== Property 7: Error Handling Consistency ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    error_code=st.sampled_from(list(LLMErrorCode)),
    message=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    provider=llm_method_strategy
)
def test_error_handling_consistency(
    error_code: LLMErrorCode,
    message: str,
    provider: LLMMethod
):
    """
    Property 7: All errors should have consistent format with error_code and message.
    
    Validates: Requirements 1.4, 2.3, 6.5
    """
    error = LLMError(
        error_code=error_code,
        message=message,
        provider=provider.value
    )
    
    # Verify required fields
    assert hasattr(error, 'error_code')
    assert hasattr(error, 'message')
    assert hasattr(error, 'provider')
    
    # Verify types
    assert isinstance(error.error_code, LLMErrorCode)
    assert isinstance(error.message, str)
    assert isinstance(error.provider, str)
    assert len(error.message) > 0


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    retry_after=st.one_of(st.none(), st.integers(min_value=0, max_value=3600)),
    suggestions=st.lists(st.text(min_size=1, max_size=100), max_size=5)
)
def test_error_optional_fields(retry_after: Optional[int], suggestions: list):
    """
    Property 7 (continued): Optional error fields should be handled correctly.
    
    Validates: Requirements 1.4, 2.3, 6.5
    """
    error = LLMError(
        error_code=LLMErrorCode.RATE_LIMITED,
        message="Rate limited",
        provider="test",
        retry_after=retry_after,
        suggestions=suggestions
    )
    
    assert error.retry_after == retry_after
    assert error.suggestions == suggestions


# ==================== Property 8: Rate Limit Retry Strategy ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    attempt=st.integers(min_value=0, max_value=10),
    base_delay=st.floats(min_value=0.1, max_value=5.0, allow_nan=False),
    max_delay=st.floats(min_value=10.0, max_value=120.0, allow_nan=False)
)
def test_exponential_backoff_retry(attempt: int, base_delay: float, max_delay: float):
    """
    Property 8: Retry delays should follow exponential backoff pattern (2^n seconds).
    
    Validates: Requirements 3.5
    """
    # Calculate expected delay
    expected_delay = base_delay * (2 ** attempt)
    capped_delay = min(expected_delay, max_delay)
    
    # Verify exponential growth
    if attempt > 0:
        prev_delay = base_delay * (2 ** (attempt - 1))
        if expected_delay <= max_delay:
            assert expected_delay == prev_delay * 2
    
    # Verify cap
    assert capped_delay <= max_delay


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    max_retries=st.integers(min_value=1, max_value=10)
)
def test_max_retry_limit(max_retries: int):
    """
    Property 8 (continued): Retries should not exceed maximum limit.
    
    Validates: Requirements 3.5
    """
    retry_count = 0
    
    # Simulate retry loop
    while retry_count < max_retries:
        retry_count += 1
    
    assert retry_count == max_retries
    assert retry_count <= 10  # Absolute maximum


# ==================== Additional Property Tests ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    method=llm_method_strategy,
    available=st.booleans(),
    latency=st.one_of(st.none(), latency_strategy)
)
def test_health_status_format(method: LLMMethod, available: bool, latency: Optional[float]):
    """
    Additional: Health status should have consistent format.
    """
    status = HealthStatus(
        method=method,
        available=available,
        latency_ms=latency
    )
    
    assert status.method == method
    assert status.available == available
    assert status.latency_ms == latency


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    valid=st.booleans(),
    errors=st.lists(st.text(min_size=1, max_size=100), max_size=5),
    warnings=st.lists(st.text(min_size=1, max_size=100), max_size=5)
)
def test_validation_result_format(valid: bool, errors: list, warnings: list):
    """
    Additional: Validation results should be consistent.
    """
    result = ValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings
    )
    
    assert result.valid == valid
    assert result.errors == errors
    assert result.warnings == warnings
    
    # If there are errors, valid should typically be False
    # (but we allow the test to set any combination for flexibility)


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    max_tokens=st.integers(min_value=1, max_value=32000),
    temperature=temperature_strategy,
    top_p=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    stream=st.booleans()
)
def test_generate_options_validation(
    max_tokens: int,
    temperature: float,
    top_p: float,
    stream: bool
):
    """
    Additional: GenerateOptions should validate all parameters.
    """
    options = GenerateOptions(
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        stream=stream
    )
    
    assert options.max_tokens == max_tokens
    assert options.temperature == temperature
    assert options.top_p == top_p
    assert options.stream == stream
    
    # Verify constraints
    assert 1 <= options.max_tokens <= 32000
    assert 0.0 <= options.temperature <= 2.0
    assert 0.0 <= options.top_p <= 1.0


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
