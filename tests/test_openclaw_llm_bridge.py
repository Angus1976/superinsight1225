"""
Unit tests for OpenClawLLMBridge.

Tests environment variable mapping, provider name conversion,
LLM request handling, and usage monitoring.

**Feature: ai-application-integration**
**Validates: Requirements 17.1, 17.4, 17.5**
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.ai_integration.openclaw_llm_bridge import OpenClawLLMBridge
from src.ai.llm_schemas import (
    LLMConfig, LLMMethod, LocalConfig, CloudConfig, ChinaLLMConfig,
    GenerateOptions, LLMResponse, TokenUsage
)


@pytest.fixture
def mock_config_manager():
    """Create mock LLM config manager."""
    manager = Mock()
    manager.get_config = AsyncMock()
    manager.log_usage = AsyncMock()
    return manager


@pytest.fixture
def mock_llm_switcher():
    """Create mock LLM switcher."""
    switcher = Mock()
    switcher.initialize = AsyncMock()
    switcher.generate = AsyncMock()
    switcher.health_check = AsyncMock()
    return switcher


@pytest.fixture
def llm_bridge(mock_config_manager):
    """Create OpenClawLLMBridge instance."""
    return OpenClawLLMBridge(config_manager=mock_config_manager)


# ============================================================================
# Test Environment Variable Mapping
# ============================================================================

@pytest.mark.asyncio
async def test_get_openclaw_env_vars_ollama(llm_bridge, mock_config_manager):
    """
    Test environment variable mapping for Ollama provider.
    
    **Validates: Requirements 17.1, 17.4**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.LOCAL_OLLAMA,
        local_config=LocalConfig(
            ollama_url="http://ollama:11434",
            default_model="qwen:7b"
        ),
        enabled_methods=[LLMMethod.LOCAL_OLLAMA]
    )
    mock_config_manager.get_config.return_value = config
    
    # Execute
    env_vars = await llm_bridge.get_openclaw_env_vars(
        gateway_id="test-gateway",
        tenant_id="test-tenant"
    )
    
    # Verify
    assert env_vars['LLM_PROVIDER'] == 'ollama'
    assert env_vars['LLM_API_ENDPOINT'] == 'http://ollama:11434'
    assert env_vars['LLM_MODEL'] == 'qwen:7b'
    assert 'LLM_TEMPERATURE' in env_vars
    assert 'LLM_MAX_TOKENS' in env_vars
    mock_config_manager.get_config.assert_called_once_with("test-tenant")


@pytest.mark.asyncio
async def test_get_openclaw_env_vars_openai(llm_bridge, mock_config_manager):
    """
    Test environment variable mapping for OpenAI provider.
    
    **Validates: Requirements 17.1, 17.4**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.CLOUD_OPENAI,
        cloud_config=CloudConfig(
            openai_api_key="sk-test-key-123",
            openai_base_url="https://api.openai.com/v1",
            openai_model="gpt-4"
        ),
        enabled_methods=[LLMMethod.CLOUD_OPENAI]
    )
    mock_config_manager.get_config.return_value = config
    
    # Execute
    env_vars = await llm_bridge.get_openclaw_env_vars(
        gateway_id="test-gateway",
        tenant_id="test-tenant"
    )
    
    # Verify
    assert env_vars['LLM_PROVIDER'] == 'openai'
    assert env_vars['LLM_API_ENDPOINT'] == 'https://api.openai.com/v1'
    assert env_vars['LLM_MODEL'] == 'gpt-4'
    assert env_vars['LLM_API_KEY'] == 'sk-test-key-123'


@pytest.mark.asyncio
async def test_get_openclaw_env_vars_qwen(llm_bridge, mock_config_manager):
    """
    Test environment variable mapping for Qwen provider.
    
    **Validates: Requirements 17.1, 17.2, 17.4**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.CHINA_QWEN,
        china_config=ChinaLLMConfig(
            qwen_api_key="qwen-test-key",
            qwen_model="qwen-turbo"
        ),
        enabled_methods=[LLMMethod.CHINA_QWEN]
    )
    mock_config_manager.get_config.return_value = config
    
    # Execute
    env_vars = await llm_bridge.get_openclaw_env_vars(
        gateway_id="test-gateway",
        tenant_id="test-tenant"
    )
    
    # Verify
    assert env_vars['LLM_PROVIDER'] == 'qwen'
    assert env_vars['LLM_API_ENDPOINT'] == 'https://dashscope.aliyuncs.com/api/v1'
    assert env_vars['LLM_MODEL'] == 'qwen-turbo'
    assert env_vars['LLM_API_KEY'] == 'qwen-test-key'


@pytest.mark.asyncio
async def test_get_openclaw_env_vars_azure(llm_bridge, mock_config_manager):
    """
    Test environment variable mapping for Azure provider with deployment.
    
    **Validates: Requirements 17.1, 17.4**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.CLOUD_AZURE,
        cloud_config=CloudConfig(
            azure_endpoint="https://test.openai.azure.com",
            azure_api_key="azure-test-key",
            azure_deployment="gpt-35-turbo",
            azure_api_version="2024-02-15-preview"
        ),
        enabled_methods=[LLMMethod.CLOUD_AZURE]
    )
    mock_config_manager.get_config.return_value = config
    
    # Execute
    env_vars = await llm_bridge.get_openclaw_env_vars(
        gateway_id="test-gateway",
        tenant_id="test-tenant"
    )
    
    # Verify
    assert env_vars['LLM_PROVIDER'] == 'azure'
    assert env_vars['LLM_API_ENDPOINT'] == 'https://test.openai.azure.com'
    assert env_vars['LLM_MODEL'] == 'gpt-35-turbo'
    assert env_vars['LLM_API_KEY'] == 'azure-test-key'
    assert env_vars['LLM_AZURE_DEPLOYMENT'] == 'gpt-35-turbo'
    assert env_vars['LLM_AZURE_API_VERSION'] == '2024-02-15-preview'


@pytest.mark.asyncio
async def test_get_openclaw_env_vars_fallback_on_error(llm_bridge, mock_config_manager):
    """
    Test fallback to default configuration on error.
    
    **Validates: Requirements 17.1**
    """
    # Setup - simulate error
    mock_config_manager.get_config.side_effect = Exception("Config error")
    
    # Execute
    env_vars = await llm_bridge.get_openclaw_env_vars(
        gateway_id="test-gateway",
        tenant_id="test-tenant"
    )
    
    # Verify fallback to default Ollama config
    assert env_vars['LLM_PROVIDER'] == 'ollama'
    assert env_vars['LLM_API_ENDPOINT'] == 'http://ollama:11434'
    assert env_vars['LLM_MODEL'] == 'qwen:7b'


# ============================================================================
# Test Provider Name Conversion
# ============================================================================

def test_map_provider_ollama(llm_bridge):
    """
    Test provider name mapping for Ollama.
    
    **Validates: Requirements 17.2**
    """
    assert llm_bridge._map_provider(LLMMethod.LOCAL_OLLAMA) == 'ollama'


def test_map_provider_openai(llm_bridge):
    """
    Test provider name mapping for OpenAI.
    
    **Validates: Requirements 17.2**
    """
    assert llm_bridge._map_provider(LLMMethod.CLOUD_OPENAI) == 'openai'


def test_map_provider_azure(llm_bridge):
    """
    Test provider name mapping for Azure.
    
    **Validates: Requirements 17.2**
    """
    assert llm_bridge._map_provider(LLMMethod.CLOUD_AZURE) == 'azure'


def test_map_provider_qwen(llm_bridge):
    """
    Test provider name mapping for Qwen.
    
    **Validates: Requirements 17.2**
    """
    assert llm_bridge._map_provider(LLMMethod.CHINA_QWEN) == 'qwen'


def test_map_provider_zhipu(llm_bridge):
    """
    Test provider name mapping for Zhipu.
    
    **Validates: Requirements 17.2**
    """
    assert llm_bridge._map_provider(LLMMethod.CHINA_ZHIPU) == 'zhipu'


def test_map_provider_baidu(llm_bridge):
    """
    Test provider name mapping for Baidu.
    
    **Validates: Requirements 17.2**
    """
    assert llm_bridge._map_provider(LLMMethod.CHINA_BAIDU) == 'baidu'


def test_map_provider_hunyuan(llm_bridge):
    """
    Test provider name mapping for Hunyuan.
    
    **Validates: Requirements 17.2**
    """
    assert llm_bridge._map_provider(LLMMethod.CHINA_HUNYUAN) == 'hunyuan'


# ============================================================================
# Test LLM Request Handling
# ============================================================================

@pytest.mark.asyncio
async def test_handle_llm_request_success(llm_bridge, mock_config_manager):
    """
    Test successful LLM request handling.
    
    **Validates: Requirements 17.3, 17.5, 18.1**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.LOCAL_OLLAMA,
        enabled_methods=[LLMMethod.LOCAL_OLLAMA]
    )
    mock_config_manager.get_config.return_value = config
    
    mock_response = LLMResponse(
        content="Test response",
        model="qwen:7b",
        provider="ollama",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        latency_ms=150.5
    )
    
    # Mock the switcher creation and response
    with patch.object(llm_bridge, '_get_switcher') as mock_get_switcher:
        mock_switcher = Mock()
        mock_switcher.generate = AsyncMock(return_value=mock_response)
        mock_get_switcher.return_value = mock_switcher
        
        # Execute
        response = await llm_bridge.handle_llm_request(
            gateway_id="test-gateway",
            tenant_id="test-tenant",
            prompt="Test prompt",
            options={'temperature': 0.7, 'max_tokens': 1000}
        )
    
    # Verify
    assert response.content == "Test response"
    assert response.model == "qwen:7b"
    assert response.usage.total_tokens == 30
    mock_config_manager.log_usage.assert_called_once()


@pytest.mark.asyncio
async def test_handle_llm_request_with_overrides(llm_bridge, mock_config_manager):
    """
    Test LLM request with model and system prompt overrides.
    
    **Validates: Requirements 17.3, 17.5**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.CLOUD_OPENAI,
        enabled_methods=[LLMMethod.CLOUD_OPENAI]
    )
    mock_config_manager.get_config.return_value = config
    
    mock_response = LLMResponse(
        content="Custom response",
        model="gpt-4",
        provider="openai",
        usage=TokenUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40),
        latency_ms=200.0
    )
    
    with patch.object(llm_bridge, '_get_switcher') as mock_get_switcher:
        mock_switcher = Mock()
        mock_switcher.generate = AsyncMock(return_value=mock_response)
        mock_get_switcher.return_value = mock_switcher
        
        # Execute
        response = await llm_bridge.handle_llm_request(
            gateway_id="test-gateway",
            tenant_id="test-tenant",
            prompt="Test prompt",
            model="gpt-4",
            system_prompt="You are a helpful assistant"
        )
    
    # Verify
    assert response.model == "gpt-4"
    mock_switcher.generate.assert_called_once()
    call_args = mock_switcher.generate.call_args
    assert call_args.kwargs['model'] == "gpt-4"
    assert call_args.kwargs['system_prompt'] == "You are a helpful assistant"


@pytest.mark.asyncio
async def test_handle_llm_request_error(llm_bridge, mock_config_manager):
    """
    Test LLM request error handling.
    
    **Validates: Requirements 17.3**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.LOCAL_OLLAMA,
        enabled_methods=[LLMMethod.LOCAL_OLLAMA]
    )
    mock_config_manager.get_config.return_value = config
    
    with patch.object(llm_bridge, '_get_switcher') as mock_get_switcher:
        mock_switcher = Mock()
        mock_switcher.generate = AsyncMock(side_effect=Exception("LLM error"))
        mock_get_switcher.return_value = mock_switcher
        
        # Execute and verify exception
        with pytest.raises(Exception) as exc_info:
            await llm_bridge.handle_llm_request(
                gateway_id="test-gateway",
                tenant_id="test-tenant",
                prompt="Test prompt"
            )
        
        assert "LLM error" in str(exc_info.value)


# ============================================================================
# Test Usage Monitoring
# ============================================================================

@pytest.mark.asyncio
async def test_monitor_usage_success(llm_bridge, mock_config_manager):
    """
    Test successful usage monitoring.
    
    **Validates: Requirements 17.6, 19.1**
    """
    # Setup
    response = LLMResponse(
        content="Test response",
        model="qwen:7b",
        provider="ollama",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        latency_ms=150.5
    )
    
    # Execute
    await llm_bridge.monitor_usage(
        gateway_id="test-gateway",
        tenant_id="test-tenant",
        response=response
    )
    
    # Verify
    mock_config_manager.log_usage.assert_called_once_with(
        method="ollama",
        model="qwen:7b",
        operation="generate",
        tenant_id="test-tenant",
        prompt_tokens=10,
        completion_tokens=20,
        latency_ms=150.5,
        success=True
    )


@pytest.mark.asyncio
async def test_monitor_usage_error_handling(llm_bridge, mock_config_manager):
    """
    Test usage monitoring error handling (should not raise).
    
    **Validates: Requirements 17.6**
    """
    # Setup
    mock_config_manager.log_usage.side_effect = Exception("Logging error")
    
    response = LLMResponse(
        content="Test response",
        model="qwen:7b",
        provider="ollama",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        latency_ms=150.5
    )
    
    # Execute - should not raise exception
    await llm_bridge.monitor_usage(
        gateway_id="test-gateway",
        tenant_id="test-tenant",
        response=response
    )
    
    # Verify log_usage was called despite error
    mock_config_manager.log_usage.assert_called_once()


# ============================================================================
# Test LLM Status
# ============================================================================

@pytest.mark.asyncio
async def test_get_llm_status_success(llm_bridge, mock_config_manager):
    """
    Test getting LLM status for gateway.
    
    **Validates: Requirements 17.4, 19.2**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.LOCAL_OLLAMA,
        local_config=LocalConfig(default_model="qwen:7b"),
        enabled_methods=[LLMMethod.LOCAL_OLLAMA, LLMMethod.CLOUD_OPENAI]
    )
    mock_config_manager.get_config.return_value = config
    
    from src.ai.llm_schemas import HealthStatus
    mock_health = {
        LLMMethod.LOCAL_OLLAMA: HealthStatus(
            method=LLMMethod.LOCAL_OLLAMA,
            available=True,
            latency_ms=50.0,
            model="qwen:7b"
        )
    }
    
    with patch.object(llm_bridge, '_get_switcher') as mock_get_switcher:
        mock_switcher = Mock()
        mock_switcher.health_check = AsyncMock(return_value=mock_health)
        mock_get_switcher.return_value = mock_switcher
        
        # Execute
        status = await llm_bridge.get_llm_status(
            gateway_id="test-gateway",
            tenant_id="test-tenant"
        )
    
    # Verify
    assert status['gateway_id'] == "test-gateway"
    assert status['tenant_id'] == "test-tenant"
    assert status['provider'] == 'ollama'
    assert status['model'] == 'qwen:7b'
    assert 'health' in status
    assert 'enabled_methods' in status
    assert 'local_ollama' in status['enabled_methods']
    assert 'cloud_openai' in status['enabled_methods']


@pytest.mark.asyncio
async def test_get_llm_status_error(llm_bridge, mock_config_manager):
    """
    Test LLM status error handling.
    
    **Validates: Requirements 17.4**
    """
    # Setup - simulate error
    mock_config_manager.get_config.side_effect = Exception("Config error")
    
    # Execute
    status = await llm_bridge.get_llm_status(
        gateway_id="test-gateway",
        tenant_id="test-tenant"
    )
    
    # Verify error response
    assert status['gateway_id'] == "test-gateway"
    assert status['tenant_id'] == "test-tenant"
    assert 'error' in status
    assert 'Config error' in status['error']


# ============================================================================
# Test Switcher Caching
# ============================================================================

@pytest.mark.asyncio
async def test_get_switcher_creates_new(llm_bridge, mock_config_manager):
    """
    Test that _get_switcher creates new switcher for tenant.
    
    **Validates: Requirements 17.3**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.LOCAL_OLLAMA,
        enabled_methods=[LLMMethod.LOCAL_OLLAMA]
    )
    mock_config_manager.get_config.return_value = config
    
    with patch('src.ai_integration.openclaw_llm_bridge.LLMSwitcher') as mock_switcher_class:
        mock_switcher = Mock()
        mock_switcher.initialize = AsyncMock()
        mock_switcher_class.return_value = mock_switcher
        
        # Execute
        switcher = await llm_bridge._get_switcher("test-tenant")
    
    # Verify
    assert switcher == mock_switcher
    mock_switcher.initialize.assert_called_once()
    mock_switcher_class.assert_called_once()


@pytest.mark.asyncio
async def test_get_switcher_reuses_cached(llm_bridge, mock_config_manager):
    """
    Test that _get_switcher reuses cached switcher for same tenant.
    
    **Validates: Requirements 17.3**
    """
    # Setup
    config = LLMConfig(
        default_method=LLMMethod.LOCAL_OLLAMA,
        enabled_methods=[LLMMethod.LOCAL_OLLAMA]
    )
    mock_config_manager.get_config.return_value = config
    
    with patch('src.ai_integration.openclaw_llm_bridge.LLMSwitcher') as mock_switcher_class:
        mock_switcher = Mock()
        mock_switcher.initialize = AsyncMock()
        mock_switcher_class.return_value = mock_switcher
        
        # Execute twice
        switcher1 = await llm_bridge._get_switcher("test-tenant")
        switcher2 = await llm_bridge._get_switcher("test-tenant")
    
    # Verify same instance returned and only created once
    assert switcher1 == switcher2
    mock_switcher_class.assert_called_once()
    mock_switcher.initialize.assert_called_once()
