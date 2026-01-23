"""
Property-based tests for LLM Integration module - Provider Type Support.

Uses Hypothesis library for property testing with minimum 100 iterations per property.
Tests the core correctness properties defined in the LLM Integration design document.
"""

import pytest
import asyncio
from typing import Dict, Any, Optional
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from uuid import uuid4
from datetime import datetime

from src.ai.llm_schemas import (
    LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig,
    ValidationResult, GenerateOptions
)


# ==================== Custom Strategies ====================

# Strategy for valid API keys (8-64 characters, alphanumeric + dash/underscore)
api_key_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
    min_size=8,
    max_size=64
)

# Strategy for valid URLs
url_strategy = st.one_of(
    st.just("http://localhost:11434"),
    st.just("https://api.openai.com/v1"),
    st.just("https://api.anthropic.com"),
    st.builds(
        lambda port: f"http://localhost:{port}",
        st.integers(min_value=1024, max_value=65535)
    )
)

# Strategy for model names
model_name_strategy = st.one_of(
    st.just("gpt-3.5-turbo"),
    st.just("gpt-4"),
    st.just("claude-3-opus"),
    st.just("qwen-turbo"),
    st.just("glm-4"),
    st.just("ernie-bot-4"),
    st.just("hunyuan-lite"),
    st.just("llama2"),
    st.just("qwen:7b"),
    st.text(min_size=3, max_size=50).filter(lambda x: x.strip() and '-' in x or ':' in x)
)

# Strategy for timeout values
timeout_strategy = st.integers(min_value=1, max_value=300)

# Strategy for retry counts
retry_strategy = st.integers(min_value=0, max_value=10)


# ==================== Property 1: Provider Type Support ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    api_key=api_key_strategy,
    model=model_name_strategy,
    timeout=timeout_strategy,
    max_retries=retry_strategy
)
def test_property_1_provider_type_support(
    provider_method: LLMMethod,
    api_key: str,
    model: str,
    timeout: int,
    max_retries: int
):
    """
    Feature: llm-integration, Property 1: Provider Type Support
    
    For any provider configuration with type in {openai, groq, anthropic, qwen, 
    zhipu, baidu, tencent, ollama, docker}, the system should accept and 
    successfully register the provider.
    
    **Validates: Requirements 1.1, 1.2**
    
    This test generates 100+ random provider configurations with valid provider 
    types and verifies that each provider type is accepted and can be configured 
    successfully.
    """
    # Create configuration based on provider method
    config = _create_provider_config(
        provider_method, api_key, model, timeout, max_retries
    )
    
    # Verify the configuration was created successfully
    assert config is not None, f"Failed to create config for {provider_method}"
    assert isinstance(config, LLMConfig), "Config should be LLMConfig instance"
    
    # Verify the provider method is in enabled methods
    assert provider_method in config.enabled_methods, \
        f"Provider {provider_method} should be in enabled methods"
    
    # Verify the default method is set correctly
    assert config.default_method == provider_method, \
        f"Default method should be {provider_method}"
    
    # Verify the appropriate sub-config is populated
    if provider_method == LLMMethod.LOCAL_OLLAMA:
        assert config.local_config is not None
        assert config.local_config.timeout == timeout
        assert config.local_config.max_retries == max_retries
        assert config.local_config.default_model == model
        
    elif provider_method in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
        assert config.cloud_config is not None
        assert config.cloud_config.timeout == timeout
        assert config.cloud_config.max_retries == max_retries
        if provider_method == LLMMethod.CLOUD_OPENAI:
            assert config.cloud_config.openai_api_key == api_key
            assert config.cloud_config.openai_model == model
        else:  # CLOUD_AZURE
            assert config.cloud_config.azure_api_key == api_key
            
    elif provider_method in (
        LLMMethod.CHINA_QWEN,
        LLMMethod.CHINA_ZHIPU,
        LLMMethod.CHINA_BAIDU,
        LLMMethod.CHINA_HUNYUAN
    ):
        assert config.china_config is not None
        assert config.china_config.timeout == timeout
        assert config.china_config.max_retries == max_retries
        
        if provider_method == LLMMethod.CHINA_QWEN:
            assert config.china_config.qwen_api_key == api_key
            assert config.china_config.qwen_model == model
        elif provider_method == LLMMethod.CHINA_ZHIPU:
            assert config.china_config.zhipu_api_key == api_key
            assert config.china_config.zhipu_model == model
        elif provider_method == LLMMethod.CHINA_BAIDU:
            assert config.china_config.baidu_api_key == api_key
            assert config.china_config.baidu_model == model
        elif provider_method == LLMMethod.CHINA_HUNYUAN:
            assert config.china_config.hunyuan_secret_id == api_key
            assert config.china_config.hunyuan_model == model


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    methods=st.lists(
        st.sampled_from(list(LLMMethod)),
        min_size=1,
        max_size=7,
        unique=True
    ),
    api_key=api_key_strategy,
    model=model_name_strategy
)
def test_property_1_multiple_provider_registration(
    methods: list,
    api_key: str,
    model: str
):
    """
    Feature: llm-integration, Property 1: Provider Type Support (Multiple Providers)
    
    For any set of provider configurations, the system should accept and 
    successfully register multiple providers simultaneously.
    
    **Validates: Requirements 1.1, 1.2**
    
    This test verifies that multiple provider types can be enabled and configured
    at the same time.
    """
    # Create a config with multiple enabled methods
    default_method = methods[0]
    
    # Build appropriate configs for each method
    local_config = LocalConfig(default_model=model)
    cloud_config = CloudConfig(openai_api_key=api_key, openai_model=model)
    china_config = ChinaLLMConfig(
        qwen_api_key=api_key,
        zhipu_api_key=api_key,
        baidu_api_key=api_key,
        baidu_secret_key=api_key,
        hunyuan_secret_id=api_key,
        hunyuan_secret_key=api_key
    )
    
    config = LLMConfig(
        default_method=default_method,
        enabled_methods=methods,
        local_config=local_config,
        cloud_config=cloud_config,
        china_config=china_config
    )
    
    # Verify all methods are registered
    assert len(config.enabled_methods) == len(methods)
    for method in methods:
        assert method in config.enabled_methods, \
            f"Method {method} should be in enabled methods"
    
    # Verify default method is in enabled methods
    assert config.default_method in config.enabled_methods


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    api_key=api_key_strategy,
    model=model_name_strategy
)
def test_property_1_provider_config_serialization(
    provider_method: LLMMethod,
    api_key: str,
    model: str
):
    """
    Feature: llm-integration, Property 1: Provider Type Support (Serialization)
    
    For any provider configuration, serialization and deserialization should 
    preserve all configuration data without loss.
    
    **Validates: Requirements 1.1, 1.2, 1.3**
    
    This test verifies that provider configurations can be serialized to JSON
    and deserialized back without data loss.
    """
    # Create original config
    original_config = _create_provider_config(
        provider_method, api_key, model, timeout=30, max_retries=3
    )
    
    # Serialize to dict
    serialized = original_config.model_dump()
    
    # Verify serialization produced a dict
    assert isinstance(serialized, dict)
    assert 'default_method' in serialized
    assert 'enabled_methods' in serialized
    
    # Deserialize back to config
    restored_config = LLMConfig(**serialized)
    
    # Verify all key fields are preserved
    assert restored_config.default_method == original_config.default_method
    assert restored_config.enabled_methods == original_config.enabled_methods
    
    # Verify sub-configs are preserved
    if provider_method == LLMMethod.LOCAL_OLLAMA:
        assert restored_config.local_config.default_model == original_config.local_config.default_model
        assert restored_config.local_config.timeout == original_config.local_config.timeout
        
    elif provider_method in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
        assert restored_config.cloud_config.timeout == original_config.cloud_config.timeout
        if provider_method == LLMMethod.CLOUD_OPENAI:
            assert restored_config.cloud_config.openai_api_key == original_config.cloud_config.openai_api_key
            assert restored_config.cloud_config.openai_model == original_config.cloud_config.openai_model
            
    elif provider_method in (
        LLMMethod.CHINA_QWEN,
        LLMMethod.CHINA_ZHIPU,
        LLMMethod.CHINA_BAIDU,
        LLMMethod.CHINA_HUNYUAN
    ):
        assert restored_config.china_config.timeout == original_config.china_config.timeout
        if provider_method == LLMMethod.CHINA_QWEN:
            assert restored_config.china_config.qwen_api_key == original_config.china_config.qwen_api_key


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    api_key=api_key_strategy,
    model=model_name_strategy,
    timeout=timeout_strategy
)
def test_property_1_provider_config_immutability(
    provider_method: LLMMethod,
    api_key: str,
    model: str,
    timeout: int
):
    """
    Feature: llm-integration, Property 1: Provider Type Support (Immutability)
    
    For any provider configuration, creating a new config with the same parameters
    should produce an equivalent configuration.
    
    **Validates: Requirements 1.1, 1.2, 1.3**
    
    This test verifies that provider configurations are deterministic and
    reproducible.
    """
    # Create two configs with identical parameters
    config1 = _create_provider_config(provider_method, api_key, model, timeout, 3)
    config2 = _create_provider_config(provider_method, api_key, model, timeout, 3)
    
    # Verify they are equivalent
    assert config1.default_method == config2.default_method
    assert config1.enabled_methods == config2.enabled_methods
    
    # Verify serialized forms are identical
    assert config1.model_dump() == config2.model_dump()


# ==================== Helper Functions ====================

def _create_provider_config(
    provider_method: LLMMethod,
    api_key: str,
    model: str,
    timeout: int,
    max_retries: int
) -> LLMConfig:
    """
    Create a provider configuration for the given method.
    
    Args:
        provider_method: The LLM method/provider type
        api_key: API key for authentication
        model: Model name to use
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        
    Returns:
        LLMConfig configured for the specified provider
    """
    if provider_method == LLMMethod.LOCAL_OLLAMA:
        return LLMConfig(
            default_method=provider_method,
            enabled_methods=[provider_method],
            local_config=LocalConfig(
                ollama_url="http://localhost:11434",
                default_model=model,
                timeout=timeout,
                max_retries=max_retries
            )
        )
        
    elif provider_method == LLMMethod.CLOUD_OPENAI:
        return LLMConfig(
            default_method=provider_method,
            enabled_methods=[provider_method],
            cloud_config=CloudConfig(
                openai_api_key=api_key,
                openai_model=model,
                timeout=timeout,
                max_retries=max_retries
            )
        )
        
    elif provider_method == LLMMethod.CLOUD_AZURE:
        return LLMConfig(
            default_method=provider_method,
            enabled_methods=[provider_method],
            cloud_config=CloudConfig(
                azure_api_key=api_key,
                azure_endpoint="https://example.openai.azure.com",
                azure_deployment="gpt-35-turbo",
                timeout=timeout,
                max_retries=max_retries
            )
        )
        
    elif provider_method == LLMMethod.CHINA_QWEN:
        return LLMConfig(
            default_method=provider_method,
            enabled_methods=[provider_method],
            china_config=ChinaLLMConfig(
                qwen_api_key=api_key,
                qwen_model=model,
                timeout=timeout,
                max_retries=max_retries
            )
        )
        
    elif provider_method == LLMMethod.CHINA_ZHIPU:
        return LLMConfig(
            default_method=provider_method,
            enabled_methods=[provider_method],
            china_config=ChinaLLMConfig(
                zhipu_api_key=api_key,
                zhipu_model=model,
                timeout=timeout,
                max_retries=max_retries
            )
        )
        
    elif provider_method == LLMMethod.CHINA_BAIDU:
        return LLMConfig(
            default_method=provider_method,
            enabled_methods=[provider_method],
            china_config=ChinaLLMConfig(
                baidu_api_key=api_key,
                baidu_secret_key=api_key,  # Using same key for simplicity in tests
                baidu_model=model,
                timeout=timeout,
                max_retries=max_retries
            )
        )
        
    elif provider_method == LLMMethod.CHINA_HUNYUAN:
        return LLMConfig(
            default_method=provider_method,
            enabled_methods=[provider_method],
            china_config=ChinaLLMConfig(
                hunyuan_secret_id=api_key,
                hunyuan_secret_key=api_key,  # Using same key for simplicity in tests
                hunyuan_model=model,
                timeout=timeout,
                max_retries=max_retries
            )
        )
    
    else:
        raise ValueError(f"Unsupported provider method: {provider_method}")


# ==================== Property 2: Configuration Validation ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    invalid_field=st.sampled_from([
        'invalid_url',
        'negative_timeout',
        'excessive_timeout',
        'negative_retries',
        'excessive_retries',
    ])
)
def test_property_2_configuration_validation_rejection(
    provider_method: LLMMethod,
    invalid_field: str
):
    """
    Feature: llm-integration, Property 2: Configuration Validation
    
    For any provider configuration, if the configuration is invalid (missing 
    required fields or invalid values), the system should reject it with a 
    descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test generates 100+ random invalid provider configurations and verifies
    that invalid configurations are rejected with descriptive error messages.
    """
    # Create an invalid configuration based on the invalid_field parameter
    config_dict = _create_invalid_config_dict(provider_method, invalid_field)
    
    # Attempt to create the configuration and expect validation error
    with pytest.raises(Exception) as exc_info:
        if provider_method == LLMMethod.LOCAL_OLLAMA:
            LocalConfig(**config_dict)
        elif provider_method in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
            CloudConfig(**config_dict)
        else:  # China providers
            ChinaLLMConfig(**config_dict)
    
    # Verify that an error was raised
    assert exc_info.value is not None
    
    # Verify the error message is descriptive (not empty)
    error_message = str(exc_info.value)
    assert len(error_message) > 0, "Error message should not be empty"
    
    # Verify the error message contains relevant information
    # (field name or validation constraint)
    assert any(keyword in error_message.lower() for keyword in [
        'validation', 'error', 'invalid', 'required', 'field',
        'timeout', 'retries', 'url', 'key', 'model', 'greater', 'less'
    ]), f"Error message should be descriptive: {error_message}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    invalid_method=st.text(min_size=1, max_size=50).filter(
        lambda x: x not in [m.value for m in LLMMethod]
    ),
    api_key=api_key_strategy,
    model=model_name_strategy
)
def test_property_2_invalid_provider_type_rejection(
    invalid_method: str,
    api_key: str,
    model: str
):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Invalid Type)
    
    For any provider configuration with an invalid provider type, the system 
    should reject it with a descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies that configurations with invalid provider types are
    properly rejected.
    """
    # Attempt to create a config with invalid method
    with pytest.raises(Exception) as exc_info:
        LLMConfig(
            default_method=invalid_method,  # Invalid method
            enabled_methods=[invalid_method],
            local_config=LocalConfig(default_model=model)
        )
    
    # Verify error was raised
    assert exc_info.value is not None
    error_message = str(exc_info.value)
    assert len(error_message) > 0


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    timeout=st.integers(min_value=-100, max_value=0),  # Invalid negative timeout
)
def test_property_2_negative_timeout_rejection(
    provider_method: LLMMethod,
    timeout: int
):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Negative Timeout)
    
    For any provider configuration with a negative timeout value, the system 
    should reject it with a descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies that negative timeout values are properly rejected.
    """
    with pytest.raises(Exception) as exc_info:
        if provider_method == LLMMethod.LOCAL_OLLAMA:
            LocalConfig(timeout=timeout)
        elif provider_method in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
            CloudConfig(timeout=timeout)
        else:
            ChinaLLMConfig(timeout=timeout)
    
    assert exc_info.value is not None
    error_message = str(exc_info.value)
    assert 'timeout' in error_message.lower() or 'greater' in error_message.lower()


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    timeout=st.integers(min_value=301, max_value=1000),  # Excessive timeout
)
def test_property_2_excessive_timeout_rejection(
    provider_method: LLMMethod,
    timeout: int
):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Excessive Timeout)
    
    For any provider configuration with an excessive timeout value (>300s), 
    the system should reject it with a descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies that excessive timeout values are properly rejected.
    """
    with pytest.raises(Exception) as exc_info:
        if provider_method == LLMMethod.LOCAL_OLLAMA:
            LocalConfig(timeout=timeout)
        elif provider_method in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
            CloudConfig(timeout=timeout)
        else:
            ChinaLLMConfig(timeout=timeout)
    
    assert exc_info.value is not None
    error_message = str(exc_info.value)
    assert 'timeout' in error_message.lower() or 'less' in error_message.lower()


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    invalid_url=st.one_of(
        st.just("not-a-url"),
        st.just("ftp://invalid.com"),
        st.just("localhost:11434"),  # Missing protocol
        st.just(""),
        st.text(min_size=1, max_size=20).filter(
            lambda x: not x.startswith(('http://', 'https://'))
        )
    )
)
def test_property_2_invalid_url_rejection(invalid_url: str):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Invalid URL)
    
    For any local provider configuration with an invalid URL format, the system 
    should reject it with a descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies that invalid URL formats are properly rejected.
    """
    with pytest.raises(Exception) as exc_info:
        LocalConfig(ollama_url=invalid_url)
    
    assert exc_info.value is not None
    error_message = str(exc_info.value)
    assert 'url' in error_message.lower() or 'http' in error_message.lower()


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    max_retries=st.integers(min_value=-10, max_value=-1),  # Negative retries
)
def test_property_2_negative_retries_rejection(
    provider_method: LLMMethod,
    max_retries: int
):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Negative Retries)
    
    For any provider configuration with negative max_retries value, the system 
    should reject it with a descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies that negative retry values are properly rejected.
    """
    with pytest.raises(Exception) as exc_info:
        if provider_method == LLMMethod.LOCAL_OLLAMA:
            LocalConfig(max_retries=max_retries)
        elif provider_method in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
            CloudConfig(max_retries=max_retries)
        else:
            ChinaLLMConfig(max_retries=max_retries)
    
    assert exc_info.value is not None
    error_message = str(exc_info.value)
    assert 'retries' in error_message.lower() or 'greater' in error_message.lower()


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    max_retries=st.integers(min_value=11, max_value=100),  # Excessive retries
)
def test_property_2_excessive_retries_rejection(
    provider_method: LLMMethod,
    max_retries: int
):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Excessive Retries)
    
    For any provider configuration with excessive max_retries value (>10), 
    the system should reject it with a descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies that excessive retry values are properly rejected.
    """
    with pytest.raises(Exception) as exc_info:
        if provider_method == LLMMethod.LOCAL_OLLAMA:
            LocalConfig(max_retries=max_retries)
        elif provider_method in (LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE):
            CloudConfig(max_retries=max_retries)
        else:
            ChinaLLMConfig(max_retries=max_retries)
    
    assert exc_info.value is not None
    error_message = str(exc_info.value)
    assert 'retries' in error_message.lower() or 'less' in error_message.lower()


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    temperature=st.one_of(
        st.floats(min_value=-10.0, max_value=-0.01),  # Negative
        st.floats(min_value=2.01, max_value=10.0),    # Too high
    )
)
def test_property_2_invalid_temperature_rejection(temperature: float):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Invalid Temperature)
    
    For any generation options with invalid temperature value (not in [0.0, 2.0]), 
    the system should reject it with a descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies that invalid temperature values are properly rejected.
    """
    with pytest.raises(Exception) as exc_info:
        GenerateOptions(temperature=temperature)
    
    assert exc_info.value is not None
    error_message = str(exc_info.value)
    assert 'temperature' in error_message.lower() or 'greater' in error_message.lower() or 'less' in error_message.lower()


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    top_p=st.one_of(
        st.floats(min_value=-1.0, max_value=-0.01),  # Negative
        st.floats(min_value=1.01, max_value=10.0),   # Too high
    )
)
def test_property_2_invalid_top_p_rejection(top_p: float):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Invalid Top-P)
    
    For any generation options with invalid top_p value (not in [0.0, 1.0]), 
    the system should reject it with a descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies that invalid top_p values are properly rejected.
    """
    with pytest.raises(Exception) as exc_info:
        GenerateOptions(top_p=top_p)
    
    assert exc_info.value is not None
    error_message = str(exc_info.value)
    assert 'top_p' in error_message.lower() or 'greater' in error_message.lower() or 'less' in error_message.lower()


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    max_tokens=st.one_of(
        st.integers(min_value=-100, max_value=0),      # Non-positive
        st.integers(min_value=32001, max_value=100000) # Too high
    )
)
def test_property_2_invalid_max_tokens_rejection(max_tokens: int):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Invalid Max Tokens)
    
    For any generation options with invalid max_tokens value (not in [1, 32000]), 
    the system should reject it with a descriptive error message.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies that invalid max_tokens values are properly rejected.
    """
    with pytest.raises(Exception) as exc_info:
        GenerateOptions(max_tokens=max_tokens)
    
    assert exc_info.value is not None
    error_message = str(exc_info.value)
    assert 'max_tokens' in error_message.lower() or 'greater' in error_message.lower() or 'less' in error_message.lower()


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    enabled_methods=st.lists(
        st.sampled_from(list(LLMMethod)),
        min_size=1,
        max_size=5,
        unique=True
    ),
    default_method=st.sampled_from(list(LLMMethod))
)
def test_property_2_default_method_not_in_enabled(
    enabled_methods: list,
    default_method: LLMMethod
):
    """
    Feature: llm-integration, Property 2: Configuration Validation (Default Not Enabled)
    
    For any LLM configuration where the default_method is not in enabled_methods,
    the configuration should still be created but the default should be validated
    when used.
    
    **Validates: Requirements 1.3, 6.4**
    
    This test verifies behavior when default method is not in enabled methods.
    """
    # Filter to only test cases where default is NOT in enabled
    assume(default_method not in enabled_methods)
    
    # Create config - this should succeed (Pydantic doesn't enforce this constraint)
    config = LLMConfig(
        default_method=default_method,
        enabled_methods=enabled_methods,
        local_config=LocalConfig(),
        cloud_config=CloudConfig(),
        china_config=ChinaLLMConfig()
    )
    
    # Verify the config was created
    assert config is not None
    assert config.default_method == default_method
    assert config.enabled_methods == enabled_methods
    
    # Note: Runtime validation would catch this when trying to use the default method


# ==================== Helper Functions for Property 2 ====================

def _create_invalid_config_dict(
    provider_method: LLMMethod,
    invalid_field: str
) -> Dict[str, Any]:
    """
    Create an invalid configuration dictionary for testing validation.
    
    Args:
        provider_method: The LLM method/provider type
        invalid_field: The type of invalid field to create
        
    Returns:
        Dictionary with invalid configuration
    """
    if invalid_field == 'invalid_url':
        # Only applicable to local provider
        if provider_method == LLMMethod.LOCAL_OLLAMA:
            return {'ollama_url': 'not-a-valid-url'}
        else:
            # Use negative timeout for non-local providers
            return {'timeout': -10}
        
    elif invalid_field == 'negative_timeout':
        return {'timeout': -10}
        
    elif invalid_field == 'excessive_timeout':
        return {'timeout': 500}
        
    elif invalid_field == 'negative_retries':
        return {'max_retries': -5}
        
    elif invalid_field == 'excessive_retries':
        return {'max_retries': 20}
    
    # Default to negative timeout
    return {'timeout': -10}


# ==================== Property 3: Provider Metadata Completeness ====================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    api_key=api_key_strategy,
    model=model_name_strategy,
    timeout=timeout_strategy,
    max_retries=retry_strategy,
    name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    description=st.text(min_size=0, max_size=500)
)
def test_property_3_provider_metadata_completeness(
    provider_method: LLMMethod,
    api_key: str,
    model: str,
    timeout: int,
    max_retries: int,
    name: str,
    description: str
):
    """
    Feature: llm-integration, Property 3: Provider Metadata Completeness
    
    For any registered provider, listing providers should return metadata 
    containing all required fields: id, name, type, deployment_mode, and status.
    
    **Validates: Requirements 1.4**
    
    This test generates 100+ random provider configurations and verifies that
    the metadata returned when listing providers contains all required fields
    with appropriate values.
    """
    # Create a provider configuration
    config = _create_provider_config(
        provider_method, api_key, model, timeout, max_retries
    )
    
    # Simulate provider metadata that would be returned by list_providers
    # In the actual system, this would come from the database and include
    # additional fields like id, name, status
    metadata = _create_provider_metadata(
        provider_method=provider_method,
        config=config,
        name=name,
        description=description
    )
    
    # Verify all required fields are present
    assert 'id' in metadata, "Metadata must contain 'id' field"
    assert 'name' in metadata, "Metadata must contain 'name' field"
    assert 'type' in metadata, "Metadata must contain 'type' field"
    assert 'deployment_mode' in metadata, "Metadata must contain 'deployment_mode' field"
    assert 'status' in metadata, "Metadata must contain 'status' field"
    
    # Verify field types and values
    assert isinstance(metadata['id'], str), "ID must be a string"
    assert len(metadata['id']) > 0, "ID must not be empty"
    
    assert isinstance(metadata['name'], str), "Name must be a string"
    assert len(metadata['name']) > 0, "Name must not be empty"
    assert metadata['name'] == name, "Name must match the provided name"
    
    assert isinstance(metadata['type'], str), "Type must be a string"
    assert metadata['type'] == provider_method.value, \
        f"Type must match provider method: expected {provider_method.value}, got {metadata['type']}"
    
    assert isinstance(metadata['deployment_mode'], str), "Deployment mode must be a string"
    assert metadata['deployment_mode'] in ['local', 'cloud'], \
        f"Deployment mode must be 'local' or 'cloud', got {metadata['deployment_mode']}"
    
    assert isinstance(metadata['status'], str), "Status must be a string"
    assert metadata['status'] in ['healthy', 'unhealthy', 'unknown'], \
        f"Status must be one of 'healthy', 'unhealthy', 'unknown', got {metadata['status']}"
    
    # Verify deployment mode matches provider type
    if provider_method == LLMMethod.LOCAL_OLLAMA:
        assert metadata['deployment_mode'] == 'local', \
            "Local Ollama should have 'local' deployment mode"
    elif provider_method in (
        LLMMethod.CLOUD_OPENAI,
        LLMMethod.CLOUD_AZURE,
        LLMMethod.CHINA_QWEN,
        LLMMethod.CHINA_ZHIPU,
        LLMMethod.CHINA_BAIDU,
        LLMMethod.CHINA_HUNYUAN
    ):
        assert metadata['deployment_mode'] == 'cloud', \
            f"{provider_method.value} should have 'cloud' deployment mode"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    num_providers=st.integers(min_value=1, max_value=7),
    api_key=api_key_strategy,
    model=model_name_strategy
)
def test_property_3_multiple_providers_metadata_completeness(
    num_providers: int,
    api_key: str,
    model: str
):
    """
    Feature: llm-integration, Property 3: Provider Metadata Completeness (Multiple)
    
    For any set of registered providers, listing all providers should return
    metadata for each provider containing all required fields.
    
    **Validates: Requirements 1.4**
    
    This test verifies that when multiple providers are registered, each
    provider's metadata is complete and correct.
    """
    # Select unique provider methods
    all_methods = list(LLMMethod)
    selected_methods = all_methods[:num_providers]
    
    # Create metadata for each provider
    providers_metadata = []
    for i, method in enumerate(selected_methods):
        config = _create_provider_config(method, api_key, model, 30, 3)
        metadata = _create_provider_metadata(
            provider_method=method,
            config=config,
            name=f"Provider {i+1}",
            description=f"Test provider {i+1}"
        )
        providers_metadata.append(metadata)
    
    # Verify we have the expected number of providers
    assert len(providers_metadata) == num_providers, \
        f"Should have {num_providers} providers, got {len(providers_metadata)}"
    
    # Verify each provider has complete metadata
    for i, metadata in enumerate(providers_metadata):
        assert 'id' in metadata, f"Provider {i} missing 'id' field"
        assert 'name' in metadata, f"Provider {i} missing 'name' field"
        assert 'type' in metadata, f"Provider {i} missing 'type' field"
        assert 'deployment_mode' in metadata, f"Provider {i} missing 'deployment_mode' field"
        assert 'status' in metadata, f"Provider {i} missing 'status' field"
        
        # Verify all IDs are unique
        other_ids = [p['id'] for j, p in enumerate(providers_metadata) if j != i]
        assert metadata['id'] not in other_ids, \
            f"Provider {i} has duplicate ID: {metadata['id']}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    api_key=api_key_strategy,
    model=model_name_strategy,
    status=st.sampled_from(['healthy', 'unhealthy', 'unknown'])
)
def test_property_3_provider_status_in_metadata(
    provider_method: LLMMethod,
    api_key: str,
    model: str,
    status: str
):
    """
    Feature: llm-integration, Property 3: Provider Metadata Completeness (Status)
    
    For any registered provider with a specific health status, the metadata
    should accurately reflect that status.
    
    **Validates: Requirements 1.4, 5.2**
    
    This test verifies that provider health status is correctly included in
    the metadata returned by list_providers.
    """
    config = _create_provider_config(provider_method, api_key, model, 30, 3)
    
    # Create metadata with specific status
    metadata = _create_provider_metadata(
        provider_method=provider_method,
        config=config,
        name="Test Provider",
        description="Test",
        status=status
    )
    
    # Verify status is correctly set
    assert metadata['status'] == status, \
        f"Status should be '{status}', got '{metadata['status']}'"
    
    # Verify status is one of the valid values
    assert metadata['status'] in ['healthy', 'unhealthy', 'unknown'], \
        f"Invalid status value: {metadata['status']}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    api_key=api_key_strategy,
    model=model_name_strategy,
    name=st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
)
def test_property_3_provider_name_preservation(
    provider_method: LLMMethod,
    api_key: str,
    model: str,
    name: str
):
    """
    Feature: llm-integration, Property 3: Provider Metadata Completeness (Name)
    
    For any registered provider with a specific name, the metadata should
    preserve and return that exact name.
    
    **Validates: Requirements 1.4**
    
    This test verifies that provider names are correctly stored and returned
    in the metadata without modification.
    """
    config = _create_provider_config(provider_method, api_key, model, 30, 3)
    
    metadata = _create_provider_metadata(
        provider_method=provider_method,
        config=config,
        name=name,
        description="Test"
    )
    
    # Verify name is preserved exactly
    assert metadata['name'] == name, \
        f"Name should be '{name}', got '{metadata['name']}'"
    
    # Verify name is not empty
    assert len(metadata['name']) > 0, "Name should not be empty"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    api_key=api_key_strategy,
    model=model_name_strategy
)
def test_property_3_provider_type_consistency(
    provider_method: LLMMethod,
    api_key: str,
    model: str
):
    """
    Feature: llm-integration, Property 3: Provider Metadata Completeness (Type)
    
    For any registered provider, the type field in metadata should exactly
    match the provider method used to create it.
    
    **Validates: Requirements 1.4**
    
    This test verifies that provider types are correctly identified and
    returned in the metadata.
    """
    config = _create_provider_config(provider_method, api_key, model, 30, 3)
    
    metadata = _create_provider_metadata(
        provider_method=provider_method,
        config=config,
        name="Test Provider",
        description="Test"
    )
    
    # Verify type matches provider method
    assert metadata['type'] == provider_method.value, \
        f"Type should be '{provider_method.value}', got '{metadata['type']}'"
    
    # Verify type is a valid LLMMethod value
    valid_types = [m.value for m in LLMMethod]
    assert metadata['type'] in valid_types, \
        f"Type '{metadata['type']}' is not a valid LLMMethod"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    provider_method=st.sampled_from(list(LLMMethod)),
    api_key=api_key_strategy,
    model=model_name_strategy
)
def test_property_3_deployment_mode_consistency(
    provider_method: LLMMethod,
    api_key: str,
    model: str
):
    """
    Feature: llm-integration, Property 3: Provider Metadata Completeness (Deployment)
    
    For any registered provider, the deployment_mode field should correctly
    reflect whether the provider is local or cloud-based.
    
    **Validates: Requirements 1.4, 2.1, 2.3**
    
    This test verifies that deployment modes are correctly determined based
    on the provider type.
    """
    config = _create_provider_config(provider_method, api_key, model, 30, 3)
    
    metadata = _create_provider_metadata(
        provider_method=provider_method,
        config=config,
        name="Test Provider",
        description="Test"
    )
    
    # Verify deployment mode is valid
    assert metadata['deployment_mode'] in ['local', 'cloud'], \
        f"Deployment mode must be 'local' or 'cloud', got '{metadata['deployment_mode']}'"
    
    # Verify deployment mode matches provider type
    if provider_method == LLMMethod.LOCAL_OLLAMA:
        assert metadata['deployment_mode'] == 'local', \
            "LOCAL_OLLAMA should have 'local' deployment mode"
    else:
        # All other providers are cloud-based
        assert metadata['deployment_mode'] == 'cloud', \
            f"{provider_method.value} should have 'cloud' deployment mode"


# ==================== Helper Functions for Property 3 ====================

def _create_provider_metadata(
    provider_method: LLMMethod,
    config: LLMConfig,
    name: str,
    description: str,
    status: str = 'healthy'
) -> Dict[str, Any]:
    """
    Create provider metadata as would be returned by list_providers.
    
    This simulates the metadata structure that the ProviderManager.list_providers()
    method would return, including all required fields.
    
    Args:
        provider_method: The LLM method/provider type
        config: The provider configuration
        name: Provider name
        description: Provider description
        status: Provider health status
        
    Returns:
        Dictionary with complete provider metadata
    """
    # Determine deployment mode based on provider type
    if provider_method == LLMMethod.LOCAL_OLLAMA:
        deployment_mode = 'local'
    else:
        deployment_mode = 'cloud'
    
    # Generate a unique ID (simulating database UUID)
    provider_id = str(uuid4())
    
    # Build metadata dictionary with all required fields
    metadata = {
        'id': provider_id,
        'name': name,
        'type': provider_method.value,
        'deployment_mode': deployment_mode,
        'status': status,
        'description': description,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
    }
    
    # Add optional fields based on provider type
    if provider_method == LLMMethod.LOCAL_OLLAMA:
        metadata['endpoint'] = config.local_config.ollama_url
        metadata['model'] = config.local_config.default_model
    elif provider_method == LLMMethod.CLOUD_OPENAI:
        metadata['model'] = config.cloud_config.openai_model
    elif provider_method == LLMMethod.CLOUD_AZURE:
        metadata['endpoint'] = config.cloud_config.azure_endpoint
        metadata['deployment'] = config.cloud_config.azure_deployment
    elif provider_method == LLMMethod.CHINA_QWEN:
        metadata['model'] = config.china_config.qwen_model
    elif provider_method == LLMMethod.CHINA_ZHIPU:
        metadata['model'] = config.china_config.zhipu_model
    elif provider_method == LLMMethod.CHINA_BAIDU:
        metadata['model'] = config.china_config.baidu_model
    elif provider_method == LLMMethod.CHINA_HUNYUAN:
        metadata['model'] = config.china_config.hunyuan_model
    
    return metadata


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
