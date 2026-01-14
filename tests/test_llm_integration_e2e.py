"""
End-to-End Integration Tests for LLM Integration Module

Tests the complete LLM integration workflow from configuration to generation.
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from src.ai.llm_schemas import LLMConfig, LLMMethod, GenerateRequest, LLMResponse
from src.ai.llm_config_manager import LLMConfigManager
from src.ai.llm_switcher import LLMSwitcher
from src.models.llm_configuration import LLMConfiguration


class TestLLMIntegrationE2E:
    """End-to-end integration tests for LLM module."""

    @pytest.fixture
    async def config_manager(self):
        """Create a test config manager."""
        manager = LLMConfigManager()
        await manager.initialize()
        return manager

    @pytest.fixture
    async def llm_switcher(self, config_manager):
        """Create a test LLM switcher."""
        switcher = LLMSwitcher(config_manager)
        await switcher.initialize()
        return switcher

    @pytest.fixture
    def sample_config(self) -> LLMConfig:
        """Sample LLM configuration for testing."""
        return LLMConfig(
            default_method="local_ollama",
            enabled_methods=["local_ollama", "cloud_openai"],
            local_config={
                "ollama_url": "http://localhost:11434",
                "default_model": "llama2",
                "timeout": 30,
                "max_retries": 3,
            },
            cloud_config={
                "openai_api_key": "sk-test-key",
                "openai_base_url": "https://api.openai.com/v1",
                "openai_model": "gpt-3.5-turbo",
                "azure_endpoint": "",
                "azure_api_key": "",
                "azure_deployment": "",
                "azure_api_version": "2023-12-01-preview",
                "timeout": 60,
                "max_retries": 3,
            },
            china_config={
                "qwen_api_key": "",
                "qwen_model": "qwen-turbo",
                "zhipu_api_key": "",
                "zhipu_model": "glm-4",
                "baidu_api_key": "",
                "baidu_secret_key": "",
                "baidu_model": "ernie-bot-turbo",
                "hunyuan_secret_id": "",
                "hunyuan_secret_key": "",
                "hunyuan_model": "hunyuan-lite",
                "timeout": 60,
                "max_retries": 3,
            },
        )

    async def test_complete_configuration_workflow(self, config_manager, sample_config):
        """Test complete configuration workflow."""
        # 1. Save configuration
        saved_config = await config_manager.save_config(sample_config)
        assert saved_config.default_method == "local_ollama"
        assert "local_ollama" in saved_config.enabled_methods

        # 2. Retrieve configuration
        retrieved_config = await config_manager.get_config()
        assert retrieved_config.default_method == sample_config.default_method
        assert retrieved_config.local_config["ollama_url"] == sample_config.local_config["ollama_url"]

        # 3. Validate configuration
        validation_result = await config_manager.validate_config(sample_config)
        assert validation_result.valid is True
        assert len(validation_result.errors) == 0

        # 4. Hot reload configuration
        reloaded_config = await config_manager.hot_reload()
        assert reloaded_config.default_method == sample_config.default_method

    async def test_llm_switcher_integration(self, llm_switcher, sample_config):
        """Test LLM switcher integration with configuration."""
        # Mock the config manager
        with patch.object(llm_switcher.config_manager, 'get_config', return_value=sample_config):
            # 1. Test method switching
            await llm_switcher.switch_method("cloud_openai")
            current_method = await llm_switcher.get_current_method()
            assert current_method == "cloud_openai"

            # 2. Test available methods
            methods = await llm_switcher.list_available_methods()
            assert "local_ollama" in [m.method for m in methods]
            assert "cloud_openai" in [m.method for m in methods]

    @patch('src.ai.llm_docker.LocalLLMProvider.generate')
    async def test_local_llm_generation(self, mock_generate, llm_switcher, sample_config):
        """Test local LLM generation workflow."""
        # Mock successful generation
        mock_response = LLMResponse(
            content="Test response from local LLM",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            model="llama2",
            provider="local_ollama",
            latency_ms=150,
            finish_reason="stop"
        )
        mock_generate.return_value = mock_response

        with patch.object(llm_switcher.config_manager, 'get_config', return_value=sample_config):
            # Test generation
            request = GenerateRequest(
                prompt="Test prompt",
                options={"max_tokens": 100, "temperature": 0.7},
                method="local_ollama"
            )
            
            response = await llm_switcher.generate(request)
            
            assert response.content == "Test response from local LLM"
            assert response.provider == "local_ollama"
            assert response.model == "llama2"
            mock_generate.assert_called_once()

    @patch('src.ai.llm_cloud.CloudLLMProvider.generate')
    async def test_cloud_llm_generation(self, mock_generate, llm_switcher, sample_config):
        """Test cloud LLM generation workflow."""
        # Mock successful generation
        mock_response = LLMResponse(
            content="Test response from OpenAI",
            usage={"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
            model="gpt-3.5-turbo",
            provider="cloud_openai",
            latency_ms=200,
            finish_reason="stop"
        )
        mock_generate.return_value = mock_response

        with patch.object(llm_switcher.config_manager, 'get_config', return_value=sample_config):
            # Test generation
            request = GenerateRequest(
                prompt="Test prompt for OpenAI",
                options={"max_tokens": 150, "temperature": 0.8},
                method="cloud_openai"
            )
            
            response = await llm_switcher.generate(request)
            
            assert response.content == "Test response from OpenAI"
            assert response.provider == "cloud_openai"
            assert response.model == "gpt-3.5-turbo"
            mock_generate.assert_called_once()

    async def test_error_handling_workflow(self, llm_switcher, sample_config):
        """Test error handling in the complete workflow."""
        with patch.object(llm_switcher.config_manager, 'get_config', return_value=sample_config):
            # Test with invalid method
            request = GenerateRequest(
                prompt="Test prompt",
                method="invalid_method"
            )
            
            with pytest.raises(ValueError, match="Unsupported LLM method"):
                await llm_switcher.generate(request)

    async def test_multi_tenant_configuration(self, config_manager, sample_config):
        """Test multi-tenant configuration isolation."""
        tenant_id_1 = "tenant_1"
        tenant_id_2 = "tenant_2"

        # Save different configs for different tenants
        config_1 = sample_config.copy()
        config_1.default_method = "local_ollama"
        
        config_2 = sample_config.copy()
        config_2.default_method = "cloud_openai"

        await config_manager.save_config(config_1, tenant_id=tenant_id_1)
        await config_manager.save_config(config_2, tenant_id=tenant_id_2)

        # Verify tenant isolation
        retrieved_1 = await config_manager.get_config(tenant_id=tenant_id_1)
        retrieved_2 = await config_manager.get_config(tenant_id=tenant_id_2)

        assert retrieved_1.default_method == "local_ollama"
        assert retrieved_2.default_method == "cloud_openai"

    async def test_configuration_hot_reload_workflow(self, config_manager, sample_config):
        """Test configuration hot reload workflow."""
        # Initial configuration
        await config_manager.save_config(sample_config)
        
        # Modify configuration
        modified_config = sample_config.copy()
        modified_config.default_method = "cloud_openai"
        modified_config.local_config["timeout"] = 60
        
        await config_manager.save_config(modified_config)
        
        # Hot reload should pick up changes
        reloaded_config = await config_manager.hot_reload()
        
        assert reloaded_config.default_method == "cloud_openai"
        assert reloaded_config.local_config["timeout"] == 60

    @patch('src.ai.llm_docker.LocalLLMProvider.health_check')
    @patch('src.ai.llm_cloud.CloudLLMProvider.health_check')
    async def test_health_check_workflow(self, mock_cloud_health, mock_local_health, llm_switcher, sample_config):
        """Test health check workflow for all providers."""
        # Mock health check responses
        mock_local_health.return_value = {
            "available": True,
            "latency_ms": 150,
            "model": "llama2",
            "error": None
        }
        
        mock_cloud_health.return_value = {
            "available": False,
            "latency_ms": None,
            "model": None,
            "error": "API key not configured"
        }

        with patch.object(llm_switcher.config_manager, 'get_config', return_value=sample_config):
            # Test health checks
            health_status = await llm_switcher.get_health_status()
            
            assert "local_ollama" in health_status
            assert "cloud_openai" in health_status
            
            assert health_status["local_ollama"]["available"] is True
            assert health_status["cloud_openai"]["available"] is False
            assert health_status["cloud_openai"]["error"] == "API key not configured"

    async def test_api_key_masking_workflow(self, config_manager, sample_config):
        """Test API key masking in configuration responses."""
        # Save configuration with API keys
        config_with_keys = sample_config.copy()
        config_with_keys.cloud_config["openai_api_key"] = "sk-1234567890abcdef"
        config_with_keys.china_config["qwen_api_key"] = "qwen-key-123456"
        
        await config_manager.save_config(config_with_keys)
        
        # Retrieve configuration (should be masked)
        retrieved_config = await config_manager.get_config(mask_keys=True)
        
        assert "****" in retrieved_config.cloud_config["openai_api_key"]
        assert "****" in retrieved_config.china_config["qwen_api_key"]
        
        # Retrieve without masking (for internal use)
        unmasked_config = await config_manager.get_config(mask_keys=False)
        
        assert unmasked_config.cloud_config["openai_api_key"] == "sk-1234567890abcdef"
        assert unmasked_config.china_config["qwen_api_key"] == "qwen-key-123456"

    async def test_concurrent_configuration_access(self, config_manager, sample_config):
        """Test concurrent access to configuration."""
        # Simulate concurrent configuration updates
        async def update_config(method: LLMMethod):
            config = sample_config.copy()
            config.default_method = method
            await config_manager.save_config(config)
            return await config_manager.get_config()

        # Run concurrent updates
        tasks = [
            update_config("local_ollama"),
            update_config("cloud_openai"),
            update_config("china_qwen"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should complete successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, LLMConfig)

    async def test_configuration_validation_edge_cases(self, config_manager):
        """Test configuration validation with edge cases."""
        # Test with missing required fields
        invalid_config = LLMConfig(
            default_method="local_ollama",
            enabled_methods=[],  # Empty enabled methods
            local_config={
                "ollama_url": "",  # Empty URL
                "default_model": "llama2",
                "timeout": -1,  # Invalid timeout
                "max_retries": 3,
            },
            cloud_config={
                "openai_api_key": "",
                "openai_base_url": "https://api.openai.com/v1",
                "openai_model": "gpt-3.5-turbo",
                "azure_endpoint": "",
                "azure_api_key": "",
                "azure_deployment": "",
                "azure_api_version": "2023-12-01-preview",
                "timeout": 60,
                "max_retries": 3,
            },
            china_config={
                "qwen_api_key": "",
                "qwen_model": "qwen-turbo",
                "zhipu_api_key": "",
                "zhipu_model": "glm-4",
                "baidu_api_key": "",
                "baidu_secret_key": "",
                "baidu_model": "ernie-bot-turbo",
                "hunyuan_secret_id": "",
                "hunyuan_secret_key": "",
                "hunyuan_model": "hunyuan-lite",
                "timeout": 60,
                "max_retries": 3,
            },
        )

        validation_result = await config_manager.validate_config(invalid_config)
        
        assert validation_result.valid is False
        assert len(validation_result.errors) > 0
        assert any("enabled_methods" in error for error in validation_result.errors)
        assert any("timeout" in error for error in validation_result.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])