"""
Unit tests for LLM Provider Manager.

Tests specific examples, edge cases, and error conditions for the LLMProviderManager class.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.admin.llm_provider_manager import (
    LLMProviderManager,
    ProviderConfig,
    ProviderType,
    ConnectionTestResult,
    QuotaInfo
)


class TestProviderConfig:
    """Test ProviderConfig class."""
    
    def test_get_openai_config(self):
        """Test getting OpenAI provider configuration."""
        config = ProviderConfig.get_config("openai")
        assert config["default_endpoint"] == "https://api.openai.com/v1"
        assert config["auth_header"] == "Authorization"
        assert config["auth_prefix"] == "Bearer"
    
    def test_get_anthropic_config(self):
        """Test getting Anthropic provider configuration."""
        config = ProviderConfig.get_config("anthropic")
        assert config["default_endpoint"] == "https://api.anthropic.com/v1"
        assert config["auth_header"] == "x-api-key"
    
    def test_get_ollama_config(self):
        """Test getting Ollama provider configuration."""
        config = ProviderConfig.get_config("ollama")
        assert config["default_endpoint"] == "http://localhost:11434"
        assert config["auth_header"] is None
    
    def test_normalize_provider_openai(self):
        """Test normalizing OpenAI provider names."""
        assert ProviderConfig._normalize_provider("openai") == ProviderType.OPENAI
        assert ProviderConfig._normalize_provider("gpt") == ProviderType.OPENAI
        assert ProviderConfig._normalize_provider("OpenAI") == ProviderType.OPENAI
    
    def test_normalize_provider_anthropic(self):
        """Test normalizing Anthropic provider names."""
        assert ProviderConfig._normalize_provider("anthropic") == ProviderType.ANTHROPIC
        assert ProviderConfig._normalize_provider("claude") == ProviderType.ANTHROPIC
    
    def test_normalize_provider_unknown(self):
        """Test normalizing unknown provider names."""
        assert ProviderConfig._normalize_provider("unknown") == ProviderType.CUSTOM


class TestLLMProviderManager:
    """Test LLMProviderManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create LLMProviderManager instance."""
        return LLMProviderManager()
    
    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager is not None
        assert isinstance(manager._quota_cache, dict)
        assert len(manager._quota_cache) == 0
    
    def test_build_auth_headers_with_bearer(self, manager):
        """Test building auth headers with Bearer prefix."""
        provider_config = {
            "auth_header": "Authorization",
            "auth_prefix": "Bearer"
        }
        api_key = "test-key-123"
        
        headers = manager._build_auth_headers(provider_config, api_key)
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key-123"
        assert "User-Agent" in headers
        assert "Accept" in headers
    
    def test_build_auth_headers_without_prefix(self, manager):
        """Test building auth headers without prefix."""
        provider_config = {
            "auth_header": "x-api-key",
            "auth_prefix": ""
        }
        api_key = "test-key-456"
        
        headers = manager._build_auth_headers(provider_config, api_key)
        
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "test-key-456"
    
    def test_build_auth_headers_no_api_key(self, manager):
        """Test building auth headers without API key."""
        provider_config = {
            "auth_header": "Authorization",
            "auth_prefix": "Bearer"
        }
        
        headers = manager._build_auth_headers(provider_config, None)
        
        assert "Authorization" not in headers
        assert "User-Agent" in headers
    
    def test_parse_models_response_openai(self, manager):
        """Test parsing OpenAI models response."""
        data = {
            "data": [
                {"id": "gpt-4"},
                {"id": "gpt-3.5-turbo"},
                {"id": "text-davinci-003"}
            ]
        }
        
        models = manager._parse_models_response("openai", data)
        
        assert len(models) == 3
        assert "gpt-4" in models
        assert "gpt-3.5-turbo" in models
    
    def test_parse_models_response_ollama(self, manager):
        """Test parsing Ollama models response."""
        data = {
            "models": [
                {"name": "llama2"},
                {"name": "mistral"},
                {"name": "codellama"}
            ]
        }
        
        models = manager._parse_models_response("ollama", data)
        
        assert len(models) == 3
        assert "llama2" in models
        assert "mistral" in models
    
    def test_parse_models_response_empty(self, manager):
        """Test parsing empty models response."""
        data = {}
        
        models = manager._parse_models_response("unknown", data)
        
        assert len(models) == 0
    
    def test_parse_models_response_invalid(self, manager):
        """Test parsing invalid models response."""
        data = {"invalid": "format"}
        
        models = manager._parse_models_response("openai", data)
        
        assert len(models) == 0
    
    @pytest.mark.asyncio
    async def test_update_quota_usage_new_config(self, manager):
        """Test updating quota usage for new configuration."""
        config_id = "test-config-1"
        
        await manager.update_quota_usage(
            config_id=config_id,
            provider="openai",
            tokens_used=100,
            success=True
        )
        
        quota = await manager.get_quota_usage(config_id)
        
        assert quota is not None
        assert quota.config_id == config_id
        assert quota.provider == "openai"
        assert quota.total_requests == 1
        assert quota.successful_requests == 1
        assert quota.failed_requests == 0
        assert quota.total_tokens == 100
    
    @pytest.mark.asyncio
    async def test_update_quota_usage_existing_config(self, manager):
        """Test updating quota usage for existing configuration."""
        config_id = "test-config-2"
        
        # First update
        await manager.update_quota_usage(
            config_id=config_id,
            provider="anthropic",
            tokens_used=50,
            success=True
        )
        
        # Second update
        await manager.update_quota_usage(
            config_id=config_id,
            provider="anthropic",
            tokens_used=75,
            success=False
        )
        
        quota = await manager.get_quota_usage(config_id)
        
        assert quota.total_requests == 2
        assert quota.successful_requests == 1
        assert quota.failed_requests == 1
        assert quota.total_tokens == 125
    
    @pytest.mark.asyncio
    async def test_get_quota_usage_nonexistent(self, manager):
        """Test getting quota usage for nonexistent configuration."""
        quota = await manager.get_quota_usage("nonexistent-config")
        
        assert quota is None
    
    @pytest.mark.asyncio
    async def test_check_quota_limits_no_limit(self, manager):
        """Test checking quota limits when no limit is set."""
        config_id = "test-config-3"
        
        await manager.update_quota_usage(
            config_id=config_id,
            provider="openai",
            tokens_used=1000,
            success=True
        )
        
        approaching_limit = await manager.check_quota_limits(config_id)
        
        assert approaching_limit is False
    
    @pytest.mark.asyncio
    async def test_check_quota_limits_below_threshold(self, manager):
        """Test checking quota limits below threshold."""
        config_id = "test-config-4"
        
        await manager.update_quota_usage(
            config_id=config_id,
            provider="openai",
            tokens_used=500,
            success=True
        )
        
        # Manually set quota limit
        quota = await manager.get_quota_usage(config_id)
        quota.quota_limit = 10000
        
        approaching_limit = await manager.check_quota_limits(config_id, threshold_percent=80.0)
        
        assert approaching_limit is False
    
    @pytest.mark.asyncio
    async def test_check_quota_limits_above_threshold(self, manager):
        """Test checking quota limits above threshold."""
        config_id = "test-config-5"
        
        await manager.update_quota_usage(
            config_id=config_id,
            provider="openai",
            tokens_used=8500,
            success=True
        )
        
        # Manually set quota limit
        quota = await manager.get_quota_usage(config_id)
        quota.quota_limit = 10000
        
        approaching_limit = await manager.check_quota_limits(config_id, threshold_percent=80.0)
        
        assert approaching_limit is True
    
    @pytest.mark.asyncio
    async def test_reset_quota_cache_specific(self, manager):
        """Test resetting quota cache for specific configuration."""
        config_id = "test-config-6"
        
        await manager.update_quota_usage(
            config_id=config_id,
            provider="openai",
            tokens_used=100,
            success=True
        )
        
        await manager.reset_quota_cache(config_id)
        
        quota = await manager.get_quota_usage(config_id)
        assert quota is None
    
    @pytest.mark.asyncio
    async def test_reset_quota_cache_all(self, manager):
        """Test resetting all quota caches."""
        # Create multiple quota entries
        await manager.update_quota_usage("config-1", "openai", 100, True)
        await manager.update_quota_usage("config-2", "anthropic", 200, True)
        await manager.update_quota_usage("config-3", "ollama", 300, True)
        
        await manager.reset_quota_cache()
        
        assert await manager.get_quota_usage("config-1") is None
        assert await manager.get_quota_usage("config-2") is None
        assert await manager.get_quota_usage("config-3") is None
    
    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, manager):
        """Test API key validation with successful connection."""
        with patch.object(manager, 'test_connection', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = ConnectionTestResult(
                success=True,
                provider="openai",
                latency_ms=150.0
            )
            
            is_valid = await manager.validate_api_key("openai", "test-key")
            
            assert is_valid is True
            mock_test.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_api_key_failure(self, manager):
        """Test API key validation with failed connection."""
        with patch.object(manager, 'test_connection', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = ConnectionTestResult(
                success=False,
                provider="openai",
                error_message="Invalid API key",
                error_code="AUTH_FAILED"
            )
            
            is_valid = await manager.validate_api_key("openai", "invalid-key")
            
            assert is_valid is False
            mock_test.assert_called_once()


class TestConnectionTestResult:
    """Test ConnectionTestResult model."""
    
    def test_test_result_success(self):
        """Test creating successful test result."""
        result = ConnectionTestResult(
            success=True,
            provider="openai",
            latency_ms=123.45
        )
        
        assert result.success is True
        assert result.provider == "openai"
        assert result.latency_ms == 123.45
        assert result.error_message is None
        assert result.error_code is None
    
    def test_test_result_failure(self):
        """Test creating failed test result."""
        result = ConnectionTestResult(
            success=False,
            provider="anthropic",
            error_message="Connection timeout",
            error_code="TIMEOUT",
            suggestions=["Check network", "Increase timeout"]
        )
        
        assert result.success is False
        assert result.provider == "anthropic"
        assert result.error_message == "Connection timeout"
        assert result.error_code == "TIMEOUT"
        assert len(result.suggestions) == 2


class TestQuotaInfo:
    """Test QuotaInfo model."""
    
    def test_quota_info_creation(self):
        """Test creating quota info."""
        quota = QuotaInfo(
            provider="openai",
            config_id="test-config",
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            total_tokens=50000
        )
        
        assert quota.provider == "openai"
        assert quota.config_id == "test-config"
        assert quota.total_requests == 100
        assert quota.successful_requests == 95
        assert quota.failed_requests == 5
        assert quota.total_tokens == 50000
    
    def test_quota_info_defaults(self):
        """Test quota info default values."""
        quota = QuotaInfo(
            provider="anthropic",
            config_id="test-config"
        )
        
        assert quota.total_requests == 0
        assert quota.successful_requests == 0
        assert quota.failed_requests == 0
        assert quota.total_tokens == 0
        assert quota.quota_limit is None
        assert quota.quota_remaining is None


class TestQuotaMonitoring:
    """Test quota monitoring functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create LLMProviderManager instance."""
        return LLMProviderManager()
    
    @pytest.mark.asyncio
    async def test_add_alert_handler(self, manager):
        """Test adding alert handler."""
        def test_handler(config_id: str, quota: QuotaInfo):
            pass
        
        initial_count = len(manager._alert_handlers)
        manager.add_alert_handler(test_handler)
        
        assert len(manager._alert_handlers) == initial_count + 1
        assert test_handler in manager._alert_handlers
    
    @pytest.mark.asyncio
    async def test_remove_alert_handler(self, manager):
        """Test removing alert handler."""
        def test_handler(config_id: str, quota: QuotaInfo):
            pass
        
        manager.add_alert_handler(test_handler)
        manager.remove_alert_handler(test_handler)
        
        assert test_handler not in manager._alert_handlers
    
    @pytest.mark.asyncio
    async def test_set_quota_limit(self, manager):
        """Test setting quota limit."""
        config_id = "test-config-quota"
        
        # Create quota entry
        await manager.update_quota_usage(config_id, "openai", 100, True)
        
        # Set quota limit
        await manager.set_quota_limit(config_id, 10000, 85.0)
        
        quota = await manager.get_quota_usage(config_id)
        assert quota.quota_limit == 10000
        assert quota.alert_threshold_percent == 85.0
    
    @pytest.mark.asyncio
    async def test_set_quota_limit_invalid_threshold(self, manager):
        """Test setting quota limit with invalid threshold."""
        config_id = "test-config-invalid"
        
        await manager.update_quota_usage(config_id, "openai", 100, True)
        
        with pytest.raises(ValueError, match="Alert threshold must be between 0 and 100"):
            await manager.set_quota_limit(config_id, 10000, 150.0)
    
    @pytest.mark.asyncio
    async def test_get_quota_status(self, manager):
        """Test getting quota status."""
        config_id = "test-config-status"
        
        # Create quota entry with limit
        await manager.update_quota_usage(config_id, "openai", 8000, True)
        await manager.set_quota_limit(config_id, 10000, 80.0)
        
        status = await manager.get_quota_status(config_id)
        
        assert status is not None
        assert status["config_id"] == config_id
        assert status["provider"] == "openai"
        assert status["total_tokens"] == 8000
        assert status["quota_limit"] == 10000
        assert status["usage_percent"] == 80.0
        assert status["alert_triggered"] is True
        assert status["quota_remaining"] == 2000
    
    @pytest.mark.asyncio
    async def test_get_quota_status_no_limit(self, manager):
        """Test getting quota status without limit."""
        config_id = "test-config-no-limit"
        
        await manager.update_quota_usage(config_id, "anthropic", 5000, True)
        
        status = await manager.get_quota_status(config_id)
        
        assert status is not None
        assert status["usage_percent"] is None
        assert status["alert_triggered"] is False
    
    @pytest.mark.asyncio
    async def test_get_quota_status_nonexistent(self, manager):
        """Test getting quota status for nonexistent config."""
        status = await manager.get_quota_status("nonexistent")
        
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_all_quota_statuses(self, manager):
        """Test getting all quota statuses."""
        # Create multiple quota entries
        await manager.update_quota_usage("config-1", "openai", 1000, True)
        await manager.update_quota_usage("config-2", "anthropic", 2000, True)
        await manager.update_quota_usage("config-3", "ollama", 3000, True)
        
        statuses = await manager.get_all_quota_statuses()
        
        assert len(statuses) == 3
        config_ids = [s["config_id"] for s in statuses]
        assert "config-1" in config_ids
        assert "config-2" in config_ids
        assert "config-3" in config_ids
    
    @pytest.mark.asyncio
    async def test_trigger_quota_alert_threshold_reached(self, manager):
        """Test triggering alert when threshold is reached."""
        config_id = "test-config-alert"
        alert_triggered = False
        
        def alert_handler(cid: str, quota: QuotaInfo):
            nonlocal alert_triggered
            alert_triggered = True
            assert cid == config_id
            assert quota.total_tokens >= quota.quota_limit * 0.8
        
        manager.add_alert_handler(alert_handler)
        
        # Create quota entry with limit
        await manager.update_quota_usage(config_id, "openai", 8500, True)
        await manager.set_quota_limit(config_id, 10000, 80.0)
        
        quota = await manager.get_quota_usage(config_id)
        await manager._trigger_quota_alert(config_id, quota)
        
        assert alert_triggered is True
    
    @pytest.mark.asyncio
    async def test_trigger_quota_alert_below_threshold(self, manager):
        """Test not triggering alert when below threshold."""
        config_id = "test-config-no-alert"
        alert_triggered = False
        
        def alert_handler(cid: str, quota: QuotaInfo):
            nonlocal alert_triggered
            alert_triggered = True
        
        manager.add_alert_handler(alert_handler)
        
        # Create quota entry below threshold
        await manager.update_quota_usage(config_id, "openai", 5000, True)
        await manager.set_quota_limit(config_id, 10000, 80.0)
        
        quota = await manager.get_quota_usage(config_id)
        await manager._trigger_quota_alert(config_id, quota)
        
        assert alert_triggered is False
    
    @pytest.mark.asyncio
    async def test_trigger_quota_alert_no_limit(self, manager):
        """Test not triggering alert when no limit is set."""
        config_id = "test-config-no-limit-alert"
        alert_triggered = False
        
        def alert_handler(cid: str, quota: QuotaInfo):
            nonlocal alert_triggered
            alert_triggered = True
        
        manager.add_alert_handler(alert_handler)
        
        # Create quota entry without limit
        await manager.update_quota_usage(config_id, "openai", 9000, True)
        
        quota = await manager.get_quota_usage(config_id)
        await manager._trigger_quota_alert(config_id, quota)
        
        assert alert_triggered is False
    
    @pytest.mark.asyncio
    async def test_trigger_quota_alert_async_handler(self, manager):
        """Test triggering alert with async handler."""
        config_id = "test-config-async-alert"
        alert_triggered = False
        
        async def async_alert_handler(cid: str, quota: QuotaInfo):
            nonlocal alert_triggered
            await asyncio.sleep(0.01)  # Simulate async operation
            alert_triggered = True
        
        manager.add_alert_handler(async_alert_handler)
        
        # Create quota entry above threshold
        await manager.update_quota_usage(config_id, "openai", 9000, True)
        await manager.set_quota_limit(config_id, 10000, 80.0)
        
        quota = await manager.get_quota_usage(config_id)
        await manager._trigger_quota_alert(config_id, quota)
        
        assert alert_triggered is True
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, manager):
        """Test starting and stopping monitoring."""
        await manager.start_monitoring(interval=1)
        
        assert manager._running is True
        assert manager._monitoring_task is not None
        
        await manager.stop_monitoring()
        
        assert manager._running is False
        assert manager._monitoring_task is None
    
    @pytest.mark.asyncio
    async def test_monitoring_loop_checks_quotas(self, manager):
        """Test that monitoring loop checks quotas periodically."""
        config_id = "test-config-monitoring"
        alert_count = 0
        
        def alert_handler(cid: str, quota: QuotaInfo):
            nonlocal alert_count
            alert_count += 1
        
        manager.add_alert_handler(alert_handler)
        
        # Create quota entry above threshold
        await manager.update_quota_usage(config_id, "openai", 9000, True)
        await manager.set_quota_limit(config_id, 10000, 80.0)
        
        # Start monitoring with short interval
        await manager.start_monitoring(interval=0.1)
        
        # Wait for at least one check
        await asyncio.sleep(0.3)
        
        await manager.stop_monitoring()
        
        # Alert should have been triggered at least once
        assert alert_count >= 1
    
    @pytest.mark.asyncio
    async def test_alert_spam_prevention(self, manager):
        """Test that alerts are not sent too frequently."""
        config_id = "test-config-spam"
        alert_count = 0
        
        def alert_handler(cid: str, quota: QuotaInfo):
            nonlocal alert_count
            alert_count += 1
        
        manager.add_alert_handler(alert_handler)
        
        # Create quota entry above threshold
        await manager.update_quota_usage(config_id, "openai", 9000, True)
        await manager.set_quota_limit(config_id, 10000, 80.0)
        
        quota = await manager.get_quota_usage(config_id)
        
        # Trigger alert multiple times in quick succession
        await manager._trigger_quota_alert(config_id, quota)
        await manager._trigger_quota_alert(config_id, quota)
        await manager._trigger_quota_alert(config_id, quota)
        
        # Only one alert should be sent (spam prevention)
        assert alert_count == 1
    
    @pytest.mark.asyncio
    async def test_monitoring_handles_errors_gracefully(self, manager):
        """Test that monitoring continues even if handler raises error."""
        config_id = "test-config-error"
        successful_alerts = 0
        
        def failing_handler(cid: str, quota: QuotaInfo):
            raise RuntimeError("Handler error")
        
        def successful_handler(cid: str, quota: QuotaInfo):
            nonlocal successful_alerts
            successful_alerts += 1
        
        manager.add_alert_handler(failing_handler)
        manager.add_alert_handler(successful_handler)
        
        # Create quota entry above threshold
        await manager.update_quota_usage(config_id, "openai", 9000, True)
        await manager.set_quota_limit(config_id, 10000, 80.0)
        
        quota = await manager.get_quota_usage(config_id)
        await manager._trigger_quota_alert(config_id, quota)
        
        # Successful handler should still be called despite failing handler
        assert successful_alerts == 1
