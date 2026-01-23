"""
Property-based tests for LLM Integration module - Deployment Mode Preservation.

Uses Hypothesis library for property testing with minimum 100 iterations.
Tests Property 5 from the LLM Integration design document.

Feature: llm-integration
Property: 5 - Deployment Mode Preservation
"""

import pytest
import copy
from typing import Optional, List, Dict, Any
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.ai.llm_schemas import (
    LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig
)


# ==================== Custom Strategies ====================

# Strategy for valid Ollama URLs
ollama_url_strategy = st.one_of(
    st.just("http://localhost:11434"),
    st.just("http://127.0.0.1:11434"),
    st.builds(
        lambda port: f"http://localhost:{port}",
        st.integers(min_value=1024, max_value=65535)
    ),
    st.builds(
        lambda host, port: f"http://{host}:{port}",
        st.from_regex(r"[a-z][a-z0-9\-]{0,20}", fullmatch=True),
        st.integers(min_value=1024, max_value=65535)
    ),
)

# Strategy for model names
model_name_strategy = st.one_of(
    st.just("qwen:7b"),
    st.just("llama2"),
    st.just("mistral"),
    st.just("gpt-3.5-turbo"),
    st.just("gpt-4"),
    st.just("glm-4"),
    st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_:.'),
        min_size=2,
        max_size=50
    ).filter(lambda x: len(x.strip()) >= 2),
)


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

# Strategy for timeout values
timeout_strategy = st.integers(min_value=1, max_value=300)

# Strategy for max_retries values
max_retries_strategy = st.integers(min_value=0, max_value=10)

# Strategy for LocalConfig
local_config_strategy = st.builds(
    LocalConfig,
    ollama_url=ollama_url_strategy,
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

# Strategy for deployment mode (local vs cloud methods)
local_methods = [LLMMethod.LOCAL_OLLAMA]
cloud_methods = [LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE]
china_methods = [LLMMethod.CHINA_QWEN, LLMMethod.CHINA_ZHIPU, 
                 LLMMethod.CHINA_BAIDU, LLMMethod.CHINA_HUNYUAN]


# ==================== Property 5: Deployment Mode Preservation ====================

class TestDeploymentModePreservation:
    """
    Property 5: Deployment Mode Preservation
    
    For any provider configuration, switching deployment modes should preserve 
    all other configuration fields unchanged.
    
    **Validates: Requirements 2.4**
    
    Requirements:
    - 2.4: WHEN switching deployment modes, THE System SHALL preserve existing 
           provider configurations
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(config=llm_config_strategy)
    def test_property_5_switching_to_local_preserves_cloud_config(
        self,
        config: LLMConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        When switching from cloud to local deployment mode, all cloud 
        configuration fields should remain unchanged.
        
        **Validates: Requirements 2.4**
        """
        # Store original cloud config
        original_cloud_config = copy.deepcopy(config.cloud_config)
        original_china_config = copy.deepcopy(config.china_config)
        
        # Switch to local deployment mode
        config.default_method = LLMMethod.LOCAL_OLLAMA
        if LLMMethod.LOCAL_OLLAMA not in config.enabled_methods:
            config.enabled_methods.append(LLMMethod.LOCAL_OLLAMA)
        
        # Property: Cloud config should be preserved after switching to local
        assert config.cloud_config.openai_api_key == original_cloud_config.openai_api_key, \
            "OpenAI API key should be preserved when switching to local mode"
        assert config.cloud_config.openai_base_url == original_cloud_config.openai_base_url, \
            "OpenAI base URL should be preserved when switching to local mode"
        assert config.cloud_config.openai_model == original_cloud_config.openai_model, \
            "OpenAI model should be preserved when switching to local mode"
        assert config.cloud_config.azure_endpoint == original_cloud_config.azure_endpoint, \
            "Azure endpoint should be preserved when switching to local mode"
        assert config.cloud_config.azure_api_key == original_cloud_config.azure_api_key, \
            "Azure API key should be preserved when switching to local mode"
        assert config.cloud_config.timeout == original_cloud_config.timeout, \
            "Cloud timeout should be preserved when switching to local mode"
        assert config.cloud_config.max_retries == original_cloud_config.max_retries, \
            "Cloud max_retries should be preserved when switching to local mode"
        
        # Property: China config should also be preserved
        assert config.china_config.qwen_api_key == original_china_config.qwen_api_key, \
            "Qwen API key should be preserved when switching to local mode"
        assert config.china_config.zhipu_api_key == original_china_config.zhipu_api_key, \
            "Zhipu API key should be preserved when switching to local mode"

    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(config=llm_config_strategy)
    def test_property_5_switching_to_cloud_preserves_local_config(
        self,
        config: LLMConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        When switching from local to cloud deployment mode, all local 
        configuration fields should remain unchanged.
        
        **Validates: Requirements 2.4**
        """
        # Store original local config
        original_local_config = copy.deepcopy(config.local_config)
        original_china_config = copy.deepcopy(config.china_config)
        
        # Switch to cloud deployment mode (OpenAI)
        config.default_method = LLMMethod.CLOUD_OPENAI
        if LLMMethod.CLOUD_OPENAI not in config.enabled_methods:
            config.enabled_methods.append(LLMMethod.CLOUD_OPENAI)
        
        # Property: Local config should be preserved after switching to cloud
        assert config.local_config.ollama_url == original_local_config.ollama_url, \
            "Ollama URL should be preserved when switching to cloud mode"
        assert config.local_config.default_model == original_local_config.default_model, \
            "Local default model should be preserved when switching to cloud mode"
        assert config.local_config.timeout == original_local_config.timeout, \
            "Local timeout should be preserved when switching to cloud mode"
        assert config.local_config.max_retries == original_local_config.max_retries, \
            "Local max_retries should be preserved when switching to cloud mode"
        
        # Property: China config should also be preserved
        assert config.china_config.qwen_api_key == original_china_config.qwen_api_key, \
            "Qwen API key should be preserved when switching to cloud mode"
        assert config.china_config.zhipu_api_key == original_china_config.zhipu_api_key, \
            "Zhipu API key should be preserved when switching to cloud mode"

    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(config=llm_config_strategy)
    def test_property_5_switching_to_china_preserves_other_configs(
        self,
        config: LLMConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        When switching to China LLM deployment mode, all local and cloud 
        configuration fields should remain unchanged.
        
        **Validates: Requirements 2.4**
        """
        # Store original configs
        original_local_config = copy.deepcopy(config.local_config)
        original_cloud_config = copy.deepcopy(config.cloud_config)
        
        # Switch to China deployment mode (Qwen)
        config.default_method = LLMMethod.CHINA_QWEN
        if LLMMethod.CHINA_QWEN not in config.enabled_methods:
            config.enabled_methods.append(LLMMethod.CHINA_QWEN)
        
        # Property: Local config should be preserved
        assert config.local_config.ollama_url == original_local_config.ollama_url, \
            "Ollama URL should be preserved when switching to China mode"
        assert config.local_config.default_model == original_local_config.default_model, \
            "Local default model should be preserved when switching to China mode"
        assert config.local_config.timeout == original_local_config.timeout, \
            "Local timeout should be preserved when switching to China mode"
        
        # Property: Cloud config should be preserved
        assert config.cloud_config.openai_api_key == original_cloud_config.openai_api_key, \
            "OpenAI API key should be preserved when switching to China mode"
        assert config.cloud_config.azure_endpoint == original_cloud_config.azure_endpoint, \
            "Azure endpoint should be preserved when switching to China mode"
        assert config.cloud_config.timeout == original_cloud_config.timeout, \
            "Cloud timeout should be preserved when switching to China mode"

    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        config=llm_config_strategy,
        new_method=st.sampled_from(list(LLMMethod))
    )
    def test_property_5_any_mode_switch_preserves_all_configs(
        self,
        config: LLMConfig,
        new_method: LLMMethod
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        For any deployment mode switch, all configuration fields for all 
        deployment modes should remain unchanged.
        
        **Validates: Requirements 2.4**
        """
        # Store deep copies of all original configs
        original_local = config.local_config.model_dump()
        original_cloud = config.cloud_config.model_dump()
        original_china = config.china_config.model_dump()
        original_enabled = list(config.enabled_methods)
        
        # Switch deployment mode
        old_method = config.default_method
        config.default_method = new_method
        
        # Add new method to enabled if not present
        if new_method not in config.enabled_methods:
            config.enabled_methods.append(new_method)
        
        # Property: All config sections should be preserved
        assert config.local_config.model_dump() == original_local, \
            f"Local config should be preserved when switching from {old_method} to {new_method}"
        assert config.cloud_config.model_dump() == original_cloud, \
            f"Cloud config should be preserved when switching from {old_method} to {new_method}"
        assert config.china_config.model_dump() == original_china, \
            f"China config should be preserved when switching from {old_method} to {new_method}"
        
        # Property: Previously enabled methods should still be enabled
        for method in original_enabled:
            assert method in config.enabled_methods, \
                f"Previously enabled method {method} should remain enabled after mode switch"

    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(config=llm_config_strategy)
    def test_property_5_multiple_mode_switches_preserve_configs(
        self,
        config: LLMConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        Multiple consecutive deployment mode switches should preserve all 
        configuration fields unchanged.
        
        **Validates: Requirements 2.4**
        """
        # Store original configs
        original_local = config.local_config.model_dump()
        original_cloud = config.cloud_config.model_dump()
        original_china = config.china_config.model_dump()
        
        # Perform multiple mode switches
        mode_sequence = [
            LLMMethod.LOCAL_OLLAMA,
            LLMMethod.CLOUD_OPENAI,
            LLMMethod.CHINA_QWEN,
            LLMMethod.CLOUD_AZURE,
            LLMMethod.CHINA_ZHIPU,
            LLMMethod.LOCAL_OLLAMA,
        ]
        
        for new_method in mode_sequence:
            config.default_method = new_method
            if new_method not in config.enabled_methods:
                config.enabled_methods.append(new_method)
        
        # Property: All configs should be preserved after multiple switches
        assert config.local_config.model_dump() == original_local, \
            "Local config should be preserved after multiple mode switches"
        assert config.cloud_config.model_dump() == original_cloud, \
            "Cloud config should be preserved after multiple mode switches"
        assert config.china_config.model_dump() == original_china, \
            "China config should be preserved after multiple mode switches"

    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        config=llm_config_strategy,
        new_local_config=local_config_strategy
    )
    def test_property_5_updating_local_config_preserves_cloud_config(
        self,
        config: LLMConfig,
        new_local_config: LocalConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        When updating local configuration, cloud and China configurations 
        should remain unchanged.
        
        **Validates: Requirements 2.4**
        """
        # Store original cloud and china configs
        original_cloud = config.cloud_config.model_dump()
        original_china = config.china_config.model_dump()
        
        # Update local config
        config.local_config = new_local_config
        
        # Property: Cloud and China configs should be preserved
        assert config.cloud_config.model_dump() == original_cloud, \
            "Cloud config should be preserved when updating local config"
        assert config.china_config.model_dump() == original_china, \
            "China config should be preserved when updating local config"

    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        config=llm_config_strategy,
        new_cloud_config=cloud_config_strategy
    )
    def test_property_5_updating_cloud_config_preserves_local_config(
        self,
        config: LLMConfig,
        new_cloud_config: CloudConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        When updating cloud configuration, local and China configurations 
        should remain unchanged.
        
        **Validates: Requirements 2.4**
        """
        # Store original local and china configs
        original_local = config.local_config.model_dump()
        original_china = config.china_config.model_dump()
        
        # Update cloud config
        config.cloud_config = new_cloud_config
        
        # Property: Local and China configs should be preserved
        assert config.local_config.model_dump() == original_local, \
            "Local config should be preserved when updating cloud config"
        assert config.china_config.model_dump() == original_china, \
            "China config should be preserved when updating cloud config"

    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        config=llm_config_strategy,
        new_china_config=china_config_strategy
    )
    def test_property_5_updating_china_config_preserves_other_configs(
        self,
        config: LLMConfig,
        new_china_config: ChinaLLMConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        When updating China LLM configuration, local and cloud configurations 
        should remain unchanged.
        
        **Validates: Requirements 2.4**
        """
        # Store original local and cloud configs
        original_local = config.local_config.model_dump()
        original_cloud = config.cloud_config.model_dump()
        
        # Update china config
        config.china_config = new_china_config
        
        # Property: Local and Cloud configs should be preserved
        assert config.local_config.model_dump() == original_local, \
            "Local config should be preserved when updating China config"
        assert config.cloud_config.model_dump() == original_cloud, \
            "Cloud config should be preserved when updating China config"


# ==================== Config Serialization Preservation ====================

class TestConfigSerializationPreservation:
    """
    Tests that configuration serialization/deserialization preserves 
    deployment mode settings.
    
    **Validates: Requirements 2.4**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(config=llm_config_strategy)
    def test_property_5_serialization_roundtrip_preserves_all_configs(
        self,
        config: LLMConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        Serializing and deserializing a configuration should preserve all 
        deployment mode settings and configurations.
        
        **Validates: Requirements 2.4**
        """
        # Serialize to dict
        config_dict = config.model_dump()
        
        # Deserialize back to LLMConfig
        restored_config = LLMConfig(**config_dict)
        
        # Property: All fields should be preserved
        assert restored_config.default_method == config.default_method, \
            "Default method should be preserved after serialization roundtrip"
        assert restored_config.local_config.model_dump() == config.local_config.model_dump(), \
            "Local config should be preserved after serialization roundtrip"
        assert restored_config.cloud_config.model_dump() == config.cloud_config.model_dump(), \
            "Cloud config should be preserved after serialization roundtrip"
        assert restored_config.china_config.model_dump() == config.china_config.model_dump(), \
            "China config should be preserved after serialization roundtrip"
        assert set(restored_config.enabled_methods) == set(config.enabled_methods), \
            "Enabled methods should be preserved after serialization roundtrip"

    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(
        config=llm_config_strategy,
        new_method=st.sampled_from(list(LLMMethod))
    )
    def test_property_5_mode_switch_then_serialize_preserves_configs(
        self,
        config: LLMConfig,
        new_method: LLMMethod
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        Switching deployment mode and then serializing should preserve all 
        configuration fields.
        
        **Validates: Requirements 2.4**
        """
        # Store original configs
        original_local = config.local_config.model_dump()
        original_cloud = config.cloud_config.model_dump()
        original_china = config.china_config.model_dump()
        
        # Switch mode
        config.default_method = new_method
        if new_method not in config.enabled_methods:
            config.enabled_methods.append(new_method)
        
        # Serialize and deserialize
        config_dict = config.model_dump()
        restored_config = LLMConfig(**config_dict)
        
        # Property: All configs should be preserved
        assert restored_config.local_config.model_dump() == original_local, \
            "Local config should be preserved after mode switch and serialization"
        assert restored_config.cloud_config.model_dump() == original_cloud, \
            "Cloud config should be preserved after mode switch and serialization"
        assert restored_config.china_config.model_dump() == original_china, \
            "China config should be preserved after mode switch and serialization"
        assert restored_config.default_method == new_method, \
            "New default method should be preserved after serialization"


# ==================== get_method_config Preservation ====================

class TestGetMethodConfigPreservation:
    """
    Tests that get_method_config returns the correct config without 
    modifying other configs.
    
    **Validates: Requirements 2.4**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(config=llm_config_strategy)
    def test_property_5_get_method_config_does_not_modify_configs(
        self,
        config: LLMConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        Calling get_method_config for any method should not modify any 
        configuration fields.
        
        **Validates: Requirements 2.4**
        """
        # Store original configs
        original_local = config.local_config.model_dump()
        original_cloud = config.cloud_config.model_dump()
        original_china = config.china_config.model_dump()
        original_default = config.default_method
        original_enabled = list(config.enabled_methods)
        
        # Call get_method_config for all methods
        for method in LLMMethod:
            _ = config.get_method_config(method)
        
        # Property: No configs should be modified
        assert config.local_config.model_dump() == original_local, \
            "Local config should not be modified by get_method_config"
        assert config.cloud_config.model_dump() == original_cloud, \
            "Cloud config should not be modified by get_method_config"
        assert config.china_config.model_dump() == original_china, \
            "China config should not be modified by get_method_config"
        assert config.default_method == original_default, \
            "Default method should not be modified by get_method_config"
        assert config.enabled_methods == original_enabled, \
            "Enabled methods should not be modified by get_method_config"

    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @given(config=llm_config_strategy)
    def test_property_5_get_method_config_returns_correct_config_type(
        self,
        config: LLMConfig
    ):
        """
        Feature: llm-integration, Property 5: Deployment Mode Preservation
        
        get_method_config should return the correct config type for each 
        deployment mode.
        
        **Validates: Requirements 2.4**
        """
        # Local method should return LocalConfig
        local_result = config.get_method_config(LLMMethod.LOCAL_OLLAMA)
        assert isinstance(local_result, LocalConfig), \
            "LOCAL_OLLAMA should return LocalConfig"
        
        # Cloud methods should return CloudConfig
        for method in [LLMMethod.CLOUD_OPENAI, LLMMethod.CLOUD_AZURE]:
            cloud_result = config.get_method_config(method)
            assert isinstance(cloud_result, CloudConfig), \
                f"{method} should return CloudConfig"
        
        # China methods should return ChinaLLMConfig
        for method in [LLMMethod.CHINA_QWEN, LLMMethod.CHINA_ZHIPU, 
                       LLMMethod.CHINA_BAIDU, LLMMethod.CHINA_HUNYUAN]:
            china_result = config.get_method_config(method)
            assert isinstance(china_result, ChinaLLMConfig), \
                f"{method} should return ChinaLLMConfig"


# ==================== Edge Cases ====================

class TestDeploymentModePreservationEdgeCases:
    """
    Edge case tests for deployment mode preservation.
    
    **Validates: Requirements 2.4**
    """
    
    def test_default_config_preserves_all_sections(self):
        """
        Default LLMConfig should have all config sections initialized.
        
        **Validates: Requirements 2.4**
        """
        config = LLMConfig()
        
        # All config sections should exist
        assert config.local_config is not None
        assert config.cloud_config is not None
        assert config.china_config is not None
        
        # Default method should be set
        assert config.default_method == LLMMethod.LOCAL_OLLAMA
        
        # Enabled methods should have at least one entry
        assert len(config.enabled_methods) >= 1
    
    def test_switching_to_same_mode_preserves_configs(self):
        """
        Switching to the same deployment mode should preserve all configs.
        
        **Validates: Requirements 2.4**
        """
        config = LLMConfig(
            default_method=LLMMethod.CLOUD_OPENAI,
            local_config=LocalConfig(ollama_url="http://custom:11434"),
            cloud_config=CloudConfig(openai_api_key="sk-test123"),
            china_config=ChinaLLMConfig(qwen_api_key="sk-qwen123"),
        )
        
        # Store original configs
        original_local = config.local_config.model_dump()
        original_cloud = config.cloud_config.model_dump()
        original_china = config.china_config.model_dump()
        
        # Switch to same mode
        config.default_method = LLMMethod.CLOUD_OPENAI
        
        # All configs should be preserved
        assert config.local_config.model_dump() == original_local
        assert config.cloud_config.model_dump() == original_cloud
        assert config.china_config.model_dump() == original_china

    
    def test_empty_enabled_methods_after_mode_switch(self):
        """
        Switching modes should not clear enabled_methods list.
        
        **Validates: Requirements 2.4**
        """
        config = LLMConfig(
            default_method=LLMMethod.LOCAL_OLLAMA,
            enabled_methods=[LLMMethod.LOCAL_OLLAMA, LLMMethod.CLOUD_OPENAI],
        )
        
        original_enabled = list(config.enabled_methods)
        
        # Switch mode
        config.default_method = LLMMethod.CLOUD_OPENAI
        
        # Original enabled methods should still be present
        for method in original_enabled:
            assert method in config.enabled_methods
    
    def test_all_china_providers_preserve_configs(self):
        """
        Switching between different China providers should preserve all configs.
        
        **Validates: Requirements 2.4**
        """
        config = LLMConfig(
            default_method=LLMMethod.CHINA_QWEN,
            china_config=ChinaLLMConfig(
                qwen_api_key="sk-qwen",
                zhipu_api_key="sk-zhipu",
                baidu_api_key="sk-baidu",
                baidu_secret_key="sk-baidu-secret",
                hunyuan_secret_id="id-hunyuan",
                hunyuan_secret_key="sk-hunyuan",
            ),
        )
        
        original_china = config.china_config.model_dump()
        
        # Switch between all China providers
        for method in [LLMMethod.CHINA_ZHIPU, LLMMethod.CHINA_BAIDU, 
                       LLMMethod.CHINA_HUNYUAN, LLMMethod.CHINA_QWEN]:
            config.default_method = method
            assert config.china_config.model_dump() == original_china, \
                f"China config should be preserved when switching to {method}"
    
    def test_config_with_none_api_keys_preserves_structure(self):
        """
        Config with None API keys should preserve structure after mode switch.
        
        **Validates: Requirements 2.4**
        """
        config = LLMConfig(
            default_method=LLMMethod.LOCAL_OLLAMA,
            cloud_config=CloudConfig(
                openai_api_key=None,
                azure_api_key=None,
            ),
            china_config=ChinaLLMConfig(
                qwen_api_key=None,
                zhipu_api_key=None,
            ),
        )
        
        original_cloud = config.cloud_config.model_dump()
        original_china = config.china_config.model_dump()
        
        # Switch to cloud mode
        config.default_method = LLMMethod.CLOUD_OPENAI
        
        # None values should be preserved
        assert config.cloud_config.model_dump() == original_cloud
        assert config.china_config.model_dump() == original_china


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
