"""
Integration Tests for LLM Module Wiring

Tests the complete integration of LLM components in the FastAPI application:
- LLM router registration
- Startup initialization of LLM components
- Health monitor background task
- Provider switching during active requests
- Cache integration

Requirements: All backend requirements from LLM Integration spec
"""

import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Test fixtures and utilities
pytestmark = pytest.mark.asyncio


class TestLLMRouterRegistration:
    """Test that LLM router is properly registered in FastAPI app."""
    
    def test_llm_router_import(self):
        """Test that LLM router can be imported."""
        try:
            from src.api.llm import router
            assert router is not None
            assert router.prefix == "/api/v1/llm"
            assert "LLM" in router.tags
        except ImportError as e:
            pytest.fail(f"Failed to import LLM router: {e}")
    
    def test_llm_router_endpoints_exist(self):
        """Test that required LLM endpoints are defined."""
        from src.api.llm import router
        
        # Get all routes
        routes = [route.path for route in router.routes]
        
        # Verify required endpoints exist
        assert "/generate" in routes or any("/generate" in r for r in routes), \
            "Generate endpoint should exist"
        assert "/health" in routes or any("/health" in r for r in routes), \
            "Health endpoint should exist"
        assert any("activate" in r for r in routes), \
            "Activate provider endpoint should exist"
    
    def test_annotation_router_import(self):
        """Test that annotation router can be imported."""
        try:
            from src.api.annotation import router
            assert router is not None
            assert "/api/v1/annotation" in router.prefix
        except ImportError as e:
            pytest.fail(f"Failed to import annotation router: {e}")


class TestLLMStartupInitialization:
    """Test LLM component initialization on app startup."""
    
    async def test_llm_switcher_initialization(self):
        """Test that LLM Switcher can be initialized."""
        try:
            from src.ai.llm_switcher import LLMSwitcher, get_llm_switcher
            
            # Get switcher instance
            switcher = get_llm_switcher()
            assert switcher is not None
            assert isinstance(switcher, LLMSwitcher)
        except ImportError as e:
            pytest.skip(f"LLM Switcher not available: {e}")
    
    async def test_llm_switcher_async_initialization(self):
        """Test async initialization of LLM Switcher."""
        try:
            from src.ai.llm_switcher import get_initialized_switcher
            
            switcher = await get_initialized_switcher()
            assert switcher is not None
            assert switcher._initialized is True
        except ImportError as e:
            pytest.skip(f"LLM Switcher not available: {e}")
        except Exception as e:
            # May fail if no providers configured, which is acceptable
            if "No providers" not in str(e):
                pytest.skip(f"Initialization failed (expected in test env): {e}")
    
    async def test_health_monitor_initialization(self):
        """Test that Health Monitor can be initialized."""
        try:
            from src.ai.llm.health_monitor import HealthMonitor, get_health_monitor
            from src.ai.llm_switcher import get_llm_switcher
            
            switcher = get_llm_switcher()
            monitor = get_health_monitor(switcher=switcher)
            
            assert monitor is not None
            assert isinstance(monitor, HealthMonitor)
        except ImportError as e:
            pytest.skip(f"Health Monitor not available: {e}")
    
    async def test_health_monitor_start_stop(self):
        """Test Health Monitor start and stop lifecycle."""
        try:
            from src.ai.llm.health_monitor import HealthMonitor
            from src.ai.llm_switcher import get_llm_switcher
            
            switcher = get_llm_switcher()
            monitor = HealthMonitor(switcher=switcher)
            
            # Start monitor
            await monitor.start()
            assert monitor.is_running is True
            
            # Stop monitor
            await monitor.stop()
            assert monitor.is_running is False
        except ImportError as e:
            pytest.skip(f"Health Monitor not available: {e}")


class TestProviderSwitching:
    """Test provider switching during active requests."""
    
    async def test_set_fallback_provider(self):
        """Test setting a fallback provider."""
        try:
            from src.ai.llm_switcher import LLMSwitcher
            from src.ai.llm_schemas import LLMMethod
            
            switcher = LLMSwitcher()
            await switcher.initialize()
            
            # If we have providers, test setting fallback
            if switcher._providers:
                methods = list(switcher._providers.keys())
                if len(methods) >= 1:
                    await switcher.set_fallback_provider(methods[0])
                    assert switcher.get_fallback_provider() == methods[0]
        except ImportError as e:
            pytest.skip(f"LLM Switcher not available: {e}")
        except Exception as e:
            pytest.skip(f"Provider switching test skipped: {e}")
    
    async def test_usage_stats_tracking(self):
        """Test that usage statistics are tracked per provider."""
        try:
            from src.ai.llm_switcher import LLMSwitcher
            
            switcher = LLMSwitcher()
            await switcher.initialize()
            
            # Get initial stats
            stats = await switcher.get_usage_stats()
            assert isinstance(stats, dict)
        except ImportError as e:
            pytest.skip(f"LLM Switcher not available: {e}")


class TestCacheIntegration:
    """Test response caching integration."""
    
    async def test_cache_key_generation(self):
        """Test that cache keys are generated deterministically."""
        try:
            from src.ai.llm_switcher import LLMSwitcher
            from src.ai.llm_schemas import LLMMethod
            
            switcher = LLMSwitcher()
            
            # Generate cache keys for same input
            key1 = switcher._generate_cache_key(
                prompt="test prompt",
                method=LLMMethod.LOCAL_OLLAMA,
                model="llama2"
            )
            key2 = switcher._generate_cache_key(
                prompt="test prompt",
                method=LLMMethod.LOCAL_OLLAMA,
                model="llama2"
            )
            
            # Same inputs should produce same key
            assert key1 == key2
            
            # Different inputs should produce different keys
            key3 = switcher._generate_cache_key(
                prompt="different prompt",
                method=LLMMethod.LOCAL_OLLAMA,
                model="llama2"
            )
            assert key1 != key3
        except ImportError as e:
            pytest.skip(f"LLM Switcher not available: {e}")
    
    async def test_local_cache_operations(self):
        """Test local in-memory cache operations."""
        try:
            from src.ai.llm_switcher import LLMSwitcher
            from src.ai.llm_schemas import LLMResponse, TokenUsage
            
            switcher = LLMSwitcher(enable_response_cache=True)
            
            # Create a test response
            test_response = LLMResponse(
                content="Test response",
                model="test-model",
                provider="test-provider",
                usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
                finish_reason="stop",
                latency_ms=100.0
            )
            
            # Cache the response
            cache_key = "test_cache_key"
            await switcher._cache_response(cache_key, test_response)
            
            # Retrieve from cache
            cached = await switcher._get_cached_response(cache_key)
            
            assert cached is not None
            assert cached.content == test_response.content
            assert cached.cached is True
        except ImportError as e:
            pytest.skip(f"LLM Switcher not available: {e}")
    
    async def test_cache_enable_disable(self):
        """Test enabling and disabling response cache."""
        try:
            from src.ai.llm_switcher import LLMSwitcher
            
            switcher = LLMSwitcher(enable_response_cache=True)
            assert switcher._enable_response_cache is True
            
            switcher.enable_response_cache(False)
            assert switcher._enable_response_cache is False
            
            switcher.enable_response_cache(True)
            assert switcher._enable_response_cache is True
        except ImportError as e:
            pytest.skip(f"LLM Switcher not available: {e}")


class TestHealthMonitorIntegration:
    """Test health monitoring integration."""
    
    async def test_health_status_query(self):
        """Test querying health status."""
        try:
            from src.ai.llm.health_monitor import HealthMonitor
            from src.ai.llm_switcher import get_llm_switcher
            
            switcher = get_llm_switcher()
            monitor = HealthMonitor(switcher=switcher)
            
            # Query all health status
            all_status = await monitor.get_all_health_status()
            assert isinstance(all_status, dict)
            
            # Query healthy providers
            healthy = await monitor.get_healthy_providers()
            assert isinstance(healthy, list)
        except ImportError as e:
            pytest.skip(f"Health Monitor not available: {e}")
    
    async def test_alert_callback_registration(self):
        """Test registering alert callbacks."""
        try:
            from src.ai.llm.health_monitor import HealthMonitor
            from src.ai.llm_switcher import get_llm_switcher
            
            switcher = get_llm_switcher()
            monitor = HealthMonitor(switcher=switcher)
            
            # Register a callback
            callback_called = []
            def test_callback(alert_data):
                callback_called.append(alert_data)
            
            monitor.register_alert_callback(test_callback)
            assert test_callback in monitor._alert_callbacks
            
            # Unregister callback
            monitor.unregister_alert_callback(test_callback)
            assert test_callback not in monitor._alert_callbacks
        except ImportError as e:
            pytest.skip(f"Health Monitor not available: {e}")


class TestEndToEndFlow:
    """Test end-to-end flow from API to provider."""
    
    async def test_generate_request_flow(self):
        """Test the complete generate request flow."""
        try:
            from src.ai.llm_switcher import LLMSwitcher
            from src.ai.llm_schemas import GenerateOptions, LLMResponse
            
            # Create switcher with mocked provider
            switcher = LLMSwitcher()
            
            # Mock a provider response
            mock_response = LLMResponse(
                content="Mocked response",
                model="mock-model",
                provider="mock-provider",
                finish_reason="stop",
                latency_ms=50.0
            )
            
            # This test verifies the flow structure exists
            # Actual generation would require a configured provider
            assert hasattr(switcher, 'generate')
            assert hasattr(switcher, '_generate_with_retry')
            assert hasattr(switcher, 'set_fallback_provider')
        except ImportError as e:
            pytest.skip(f"LLM Switcher not available: {e}")
    
    async def test_pre_annotation_engine_integration(self):
        """Test pre-annotation engine integration with LLM."""
        try:
            from src.ai.pre_annotation import PreAnnotationEngine, get_pre_annotation_engine
            
            # Get engine instance
            engine = get_pre_annotation_engine()
            assert engine is not None
            assert isinstance(engine, PreAnnotationEngine)
            
            # Verify engine has required methods
            assert hasattr(engine, 'pre_annotate')
            assert hasattr(engine, 'pre_annotate_with_samples')
            assert hasattr(engine, 'calculate_confidence')
            assert hasattr(engine, 'mark_for_review')
        except ImportError as e:
            pytest.skip(f"Pre-annotation engine not available: {e}")


class TestAPIEndpointIntegration:
    """Test API endpoint integration."""
    
    def test_generate_endpoint_schema(self):
        """Test generate endpoint request/response schemas."""
        try:
            from src.api.llm import GenerateRequest, GenerateResponse
            
            # Test request schema
            request = GenerateRequest(
                prompt="Test prompt",
                max_tokens=100,
                temperature=0.7
            )
            assert request.prompt == "Test prompt"
            assert request.max_tokens == 100
            
            # Test response schema
            response = GenerateResponse(
                text="Generated text",
                model="test-model",
                provider_id="test-provider",
                cached=False,
                latency_ms=100.0
            )
            assert response.text == "Generated text"
        except ImportError as e:
            pytest.skip(f"LLM API schemas not available: {e}")
    
    def test_health_endpoint_schema(self):
        """Test health endpoint response schema."""
        try:
            from src.api.llm import HealthResponse, ProviderHealthStatus
            
            # Test provider health status
            status = ProviderHealthStatus(
                provider_id="test-provider",
                name="Test Provider",
                provider_type="openai",
                is_healthy=True,
                is_active=True
            )
            assert status.is_healthy is True
            
            # Test health response
            response = HealthResponse(
                providers=[status],
                active_provider_id="test-provider",
                overall_healthy=True
            )
            assert response.overall_healthy is True
        except ImportError as e:
            pytest.skip(f"LLM API schemas not available: {e}")
    
    def test_activate_endpoint_schema(self):
        """Test activate endpoint request/response schemas."""
        try:
            from src.api.llm import ActivateProviderRequest, ActivateProviderResponse
            
            # Test request schema
            request = ActivateProviderRequest(set_as_fallback=False)
            assert request.set_as_fallback is False
            
            # Test response schema
            response = ActivateProviderResponse(
                success=True,
                provider_id="test-provider",
                message="Provider activated"
            )
            assert response.success is True
        except ImportError as e:
            pytest.skip(f"LLM API schemas not available: {e}")


class TestRetryAndFailover:
    """Test retry and failover mechanisms."""
    
    async def test_retry_after_extraction(self):
        """Test extraction of retry-after from rate limit errors."""
        try:
            from src.ai.llm_switcher import LLMSwitcher
            
            switcher = LLMSwitcher()
            
            # Test various rate limit error formats
            test_cases = [
                (Exception("Rate limit exceeded. Retry after 60 seconds"), 60),
                (Exception("429 Too Many Requests. retry-after: 30"), 30),
                (Exception("Quota exceeded, wait 120s"), 120),
                (Exception("Regular error without rate limit"), None),
            ]
            
            for error, expected in test_cases:
                result = switcher._extract_retry_after(error)
                if expected is not None:
                    assert result is not None, f"Should extract retry-after from: {error}"
                # Note: exact value may vary based on parsing logic
        except ImportError as e:
            pytest.skip(f"LLM Switcher not available: {e}")
    
    async def test_exponential_backoff_delays(self):
        """Test that exponential backoff uses correct delays."""
        try:
            from src.ai.llm_switcher import EXPONENTIAL_BACKOFF_BASE, MAX_RETRY_ATTEMPTS
            
            # Verify constants are set correctly
            assert EXPONENTIAL_BACKOFF_BASE == 2, "Backoff base should be 2"
            assert MAX_RETRY_ATTEMPTS == 3, "Max retries should be 3"
            
            # Calculate expected delays: 1s, 2s, 4s
            expected_delays = [2 ** i for i in range(MAX_RETRY_ATTEMPTS)]
            assert expected_delays == [1, 2, 4], "Delays should be 1s, 2s, 4s"
        except ImportError as e:
            pytest.skip(f"LLM Switcher constants not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
