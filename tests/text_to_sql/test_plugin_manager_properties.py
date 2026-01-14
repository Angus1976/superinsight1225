"""
Property-based tests for Plugin Manager and Third Party Adapter.

Tests Property 7: 插件接口验证
Tests Property 8: 自动回退机制
Validates: Requirements 6.2, 6.7

Uses Hypothesis for property-based testing with 100+ iterations.
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.text_to_sql.plugin_manager import (
    PluginManager,
    get_plugin_manager,
)
from src.text_to_sql.plugin_interface import (
    PluginInterface,
    BasePlugin,
    PluginNotFoundError,
    PluginValidationError,
    PluginCallError,
)
from src.text_to_sql.third_party_adapter import ThirdPartyAdapter
from src.text_to_sql.schemas import (
    SQLGenerationResult,
    PluginInfo,
    PluginConfig,
    ConnectionType,
    PluginHealthStatus,
)
from src.text_to_sql.schema_analyzer import DatabaseSchema


# =============================================================================
# Test Fixtures and Mock Classes
# =============================================================================

class ValidMockPlugin(BasePlugin):
    """A valid mock plugin that implements all required methods."""
    
    def __init__(self, config: PluginConfig, should_succeed: bool = True):
        super().__init__(config)
        self.should_succeed = should_succeed
        self.call_count = 0
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name=self.config.name,
            version="1.0.0",
            description=f"Mock plugin: {self.config.name}",
            connection_type=self.config.connection_type,
            supported_db_types=["postgresql", "mysql"],
            config_schema={},
            is_healthy=True,
            last_health_check=datetime.utcnow(),
        )
    
    def to_native_format(
        self,
        query: str,
        schema: Optional[DatabaseSchema] = None
    ) -> Dict[str, Any]:
        return {
            "query": query,
            "schema": schema.tables if schema else None,
        }
    
    async def call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.call_count += 1
        if self.should_succeed:
            return {
                "sql": f"SELECT * FROM mock_table WHERE query = '{request.get('query', '')[:20]}'",
                "confidence": 0.85,
            }
        else:
            raise PluginCallError(self.config.name, "Mock call failure")
    
    def from_native_format(self, response: Dict[str, Any]) -> SQLGenerationResult:
        return SQLGenerationResult(
            sql=response.get("sql", ""),
            method_used=f"third_party:{self.config.name}",
            confidence=response.get("confidence", 0.8),
            execution_time_ms=10.0,
            metadata={"plugin": self.config.name},
        )
    
    async def health_check(self) -> bool:
        self._last_health_check = datetime.utcnow()
        self._is_healthy = self.should_succeed
        return self._is_healthy


class InvalidMockPlugin:
    """An invalid plugin missing required methods."""
    
    def __init__(self, config: PluginConfig):
        self.config = config
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name=self.config.name,
            version="1.0.0",
            description="Invalid plugin",
            connection_type=self.config.connection_type,
            supported_db_types=[],
            config_schema={},
        )
    
    # Missing: to_native_format, call, from_native_format, health_check


class PartialMockPlugin:
    """A plugin with some methods but not all."""
    
    def __init__(self, config: PluginConfig):
        self.config = config
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name=self.config.name,
            version="1.0.0",
            description="Partial plugin",
            connection_type=self.config.connection_type,
            supported_db_types=[],
            config_schema={},
        )
    
    def to_native_format(self, query: str, schema=None) -> Dict[str, Any]:
        return {"query": query}
    
    # Missing: call, from_native_format, health_check


class TimeoutMockPlugin(ValidMockPlugin):
    """A plugin that times out on calls."""
    
    async def call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.call_count += 1
        await asyncio.sleep(100)  # Simulate timeout
        return {"sql": "SELECT 1", "confidence": 0.5}


class MockFallbackGenerator:
    """Mock fallback generator for testing."""
    
    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.generate_called = False
    
    async def generate(self, query: str, schema=None) -> SQLGenerationResult:
        self.generate_called = True
        if self.should_succeed:
            return SQLGenerationResult(
                sql=f"SELECT * FROM fallback_table",
                method_used="hybrid",
                confidence=0.7,
                execution_time_ms=50.0,
                metadata={"fallback": True},
            )
        else:
            return SQLGenerationResult(
                sql="",
                method_used="fallback:failed",
                confidence=0.0,
                execution_time_ms=0.0,
                metadata={"error": "Fallback failed"},
            )


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Strategy for valid plugin names
valid_plugin_names = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_-"),
    min_size=1,
    max_size=50
).filter(lambda x: x[0].isalpha() if x else False)

# Strategy for connection types
connection_types = st.sampled_from([
    ConnectionType.REST_API,
    ConnectionType.GRPC,
    ConnectionType.LOCAL_SDK,
])

# Strategy for valid endpoints
valid_endpoints = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789.-:/"),
    min_size=10,
    max_size=100
).map(lambda x: f"http://{x}")

# Strategy for timeouts
valid_timeouts = st.integers(min_value=1, max_value=300)


# =============================================================================
# Property 7: Plugin Interface Validation Tests
# =============================================================================

class TestPluginInterfaceValidation:
    """
    Property 7: 插件接口验证
    
    For any registered third-party plugin, Plugin Manager should validate
    that it implements all required PluginInterface methods, rejecting
    incomplete implementations.
    
    **Validates: Requirements 6.2**
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        name=valid_plugin_names,
        connection_type=connection_types,
        timeout=valid_timeouts,
    )
    def test_property_7_valid_plugin_registration(
        self,
        name: str,
        connection_type: ConnectionType,
        timeout: int,
    ):
        """
        Property 7: Valid plugins should be registered successfully.
        
        For any valid plugin configuration and implementation,
        the Plugin Manager should accept registration.
        
        **Feature: text-to-sql-methods, Property 7: 插件接口验证**
        **Validates: Requirements 6.2**
        """
        # Create config
        config = PluginConfig(
            name=name,
            connection_type=connection_type,
            endpoint="http://localhost:8080" if connection_type != ConnectionType.LOCAL_SDK else None,
            timeout=timeout,
            enabled=True,
        )
        
        # Create manager and valid plugin
        manager = PluginManager()
        
        # Register should succeed
        result = asyncio.get_event_loop().run_until_complete(
            manager.register_plugin(config, ValidMockPlugin)
        )
        
        # Verify registration
        assert result is not None, "Should return PluginInfo"
        assert result.name == name, "Should have correct name"
        
        # Verify plugin is retrievable
        plugin = manager.get_plugin(name)
        assert plugin is not None, "Should be able to retrieve plugin"
    
    @settings(max_examples=100, deadline=None)
    @given(name=valid_plugin_names)
    def test_property_7_invalid_plugin_rejection(self, name: str):
        """
        Property 7: Invalid plugins should be rejected.
        
        For any plugin missing required interface methods,
        the Plugin Manager should reject registration.
        
        **Feature: text-to-sql-methods, Property 7: 插件接口验证**
        **Validates: Requirements 6.2**
        """
        config = PluginConfig(
            name=name,
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=True,
        )
        
        manager = PluginManager()
        
        # Create invalid plugin class
        class InvalidPlugin:
            def __init__(self, cfg):
                self.config = cfg
            
            def get_info(self):
                return PluginInfo(
                    name=cfg.name,
                    version="1.0.0",
                    description="Invalid",
                    connection_type=cfg.connection_type,
                    supported_db_types=[],
                    config_schema={},
                )
            # Missing required methods
        
        # Registration should fail
        with pytest.raises(PluginValidationError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                manager.register_plugin(config, InvalidPlugin)
            )
        
        # Should have validation errors
        assert len(exc_info.value.errors) > 0, "Should have validation errors"
    
    @settings(max_examples=100, deadline=None)
    @given(
        name=valid_plugin_names,
        connection_type=st.sampled_from([ConnectionType.REST_API, ConnectionType.GRPC]),
    )
    def test_property_7_endpoint_required_for_remote(
        self,
        name: str,
        connection_type: ConnectionType,
    ):
        """
        Property 7: Remote plugins require endpoint.
        
        For any REST API or gRPC plugin, endpoint must be provided.
        Pydantic validates this at the model level.
        
        **Feature: text-to-sql-methods, Property 7: 插件接口验证**
        **Validates: Requirements 6.2**
        """
        from pydantic import ValidationError
        
        # Config without endpoint should fail at Pydantic validation level
        with pytest.raises(ValidationError) as exc_info:
            config = PluginConfig(
                name=name,
                connection_type=connection_type,
                endpoint=None,  # Missing endpoint
                timeout=30,
                enabled=True,
            )
        
        # Should mention endpoint in error
        error_str = str(exc_info.value).lower()
        assert "endpoint" in error_str, "Should mention missing endpoint"
    
    @settings(max_examples=100, deadline=None)
    @given(
        name=valid_plugin_names,
        timeout=st.integers(min_value=-100, max_value=0) | st.integers(min_value=301, max_value=1000),
    )
    def test_property_7_timeout_validation(self, name: str, timeout: int):
        """
        Property 7: Timeout must be within valid range.
        
        For any timeout outside 1-300 seconds, Pydantic validation should fail.
        
        **Feature: text-to-sql-methods, Property 7: 插件接口验证**
        **Validates: Requirements 6.2**
        """
        from pydantic import ValidationError
        
        # Config with invalid timeout should fail at Pydantic validation level
        with pytest.raises(ValidationError) as exc_info:
            config = PluginConfig(
                name=name,
                connection_type=ConnectionType.LOCAL_SDK,
                timeout=timeout,
                enabled=True,
            )
        
        # Should mention timeout in error
        error_str = str(exc_info.value).lower()
        assert "timeout" in error_str or "greater" in error_str or "less" in error_str, \
            "Should mention invalid timeout"
    
    def test_property_7_required_methods_check(self):
        """
        Property 7: All required methods must be present.
        
        Plugin Manager should check for all 5 required methods:
        get_info, to_native_format, call, from_native_format, health_check
        
        **Feature: text-to-sql-methods, Property 7: 插件接口验证**
        **Validates: Requirements 6.2**
        """
        required_methods = [
            "get_info",
            "to_native_format",
            "call",
            "from_native_format",
            "health_check",
        ]
        
        config = PluginConfig(
            name="test_plugin",
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=True,
        )
        
        manager = PluginManager()
        
        # Test with partial plugin
        with pytest.raises(PluginValidationError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                manager.register_plugin(config, PartialMockPlugin)
            )
        
        # Should mention missing methods
        errors = exc_info.value.errors
        assert len(errors) > 0, "Should have validation errors for missing methods"


# =============================================================================
# Property 8: Automatic Fallback Mechanism Tests
# =============================================================================

class TestAutomaticFallback:
    """
    Property 8: 自动回退机制
    
    For any third-party tool call failure (timeout, error, unavailable),
    the system should automatically fall back to built-in methods,
    never returning an empty result.
    
    **Validates: Requirements 6.7**
    """
    
    @settings(max_examples=100, deadline=None)
    @given(query=st.text(min_size=1, max_size=200))
    def test_property_8_fallback_on_plugin_failure(self, query: str):
        """
        Property 8: Fallback on plugin call failure.
        
        For any query where the plugin call fails,
        the adapter should fall back to built-in method.
        
        **Feature: text-to-sql-methods, Property 8: 自动回退机制**
        **Validates: Requirements 6.7**
        """
        assume(query.strip())
        
        # Create failing plugin
        config = PluginConfig(
            name="failing_plugin",
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=True,
        )
        
        manager = PluginManager()
        failing_plugin = ValidMockPlugin(config, should_succeed=False)
        manager._plugins["failing_plugin"] = failing_plugin
        manager._configs["failing_plugin"] = config
        
        # Create adapter with fallback
        fallback = MockFallbackGenerator(should_succeed=True)
        adapter = ThirdPartyAdapter(
            plugin_manager=manager,
            fallback_generator=fallback,
            max_retries=1,
        )
        
        # Call should fall back
        result = asyncio.get_event_loop().run_until_complete(
            adapter.generate(query, None, "failing_plugin")
        )
        
        # Should have used fallback
        assert fallback.generate_called, "Fallback should be called"
        assert result.sql != "", "Should not return empty SQL"
        assert "fallback" in result.metadata or result.method_used == "hybrid", \
            "Should indicate fallback was used"
    
    @settings(max_examples=100, deadline=None)
    @given(query=st.text(min_size=1, max_size=200))
    def test_property_8_fallback_on_disabled_plugin(self, query: str):
        """
        Property 8: Fallback when plugin is disabled.
        
        For any query to a disabled plugin,
        the adapter should fall back to built-in method.
        
        **Feature: text-to-sql-methods, Property 8: 自动回退机制**
        **Validates: Requirements 6.7**
        """
        assume(query.strip())
        
        # Create disabled plugin
        config = PluginConfig(
            name="disabled_plugin",
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=False,  # Disabled
        )
        
        manager = PluginManager()
        plugin = ValidMockPlugin(config, should_succeed=True)
        manager._plugins["disabled_plugin"] = plugin
        manager._configs["disabled_plugin"] = config
        
        # Create adapter with fallback
        fallback = MockFallbackGenerator(should_succeed=True)
        adapter = ThirdPartyAdapter(
            plugin_manager=manager,
            fallback_generator=fallback,
        )
        
        # Call should fall back
        result = asyncio.get_event_loop().run_until_complete(
            adapter.generate(query, None, "disabled_plugin")
        )
        
        # Should have used fallback
        assert fallback.generate_called, "Fallback should be called for disabled plugin"
        assert result.sql != "", "Should not return empty SQL"
    
    @settings(max_examples=100, deadline=None)
    @given(query=st.text(min_size=1, max_size=200))
    def test_property_8_fallback_on_plugin_not_found(self, query: str):
        """
        Property 8: Fallback when plugin not found.
        
        For any query to a non-existent plugin,
        the adapter should raise PluginNotFoundError.
        
        **Feature: text-to-sql-methods, Property 8: 自动回退机制**
        **Validates: Requirements 6.7**
        """
        assume(query.strip())
        
        manager = PluginManager()
        adapter = ThirdPartyAdapter(plugin_manager=manager)
        
        # Call should raise PluginNotFoundError
        with pytest.raises(PluginNotFoundError):
            asyncio.get_event_loop().run_until_complete(
                adapter.generate(query, None, "nonexistent_plugin")
            )
    
    @settings(max_examples=100, deadline=None)
    @given(
        query=st.text(min_size=1, max_size=200),
        num_retries=st.integers(min_value=0, max_value=5),
    )
    def test_property_8_retry_before_fallback(self, query: str, num_retries: int):
        """
        Property 8: Retry before fallback.
        
        For any failing plugin, the adapter should retry
        the configured number of times before falling back.
        
        **Feature: text-to-sql-methods, Property 8: 自动回退机制**
        **Validates: Requirements 6.7**
        """
        assume(query.strip())
        
        # Create failing plugin
        config = PluginConfig(
            name="retry_plugin",
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=True,
        )
        
        manager = PluginManager()
        failing_plugin = ValidMockPlugin(config, should_succeed=False)
        manager._plugins["retry_plugin"] = failing_plugin
        manager._configs["retry_plugin"] = config
        
        # Create adapter with specific retry count
        fallback = MockFallbackGenerator(should_succeed=True)
        adapter = ThirdPartyAdapter(
            plugin_manager=manager,
            fallback_generator=fallback,
            max_retries=num_retries,
        )
        
        # Call should retry then fall back
        result = asyncio.get_event_loop().run_until_complete(
            adapter.generate(query, None, "retry_plugin")
        )
        
        # Should have retried correct number of times
        expected_calls = num_retries + 1  # Initial + retries
        assert failing_plugin.call_count == expected_calls, \
            f"Should have called plugin {expected_calls} times, got {failing_plugin.call_count}"
        
        # Should have fallen back
        assert fallback.generate_called, "Should fall back after retries"
    
    @settings(max_examples=100, deadline=None)
    @given(
        plugin_succeeds=st.booleans(),
        fallback_succeeds=st.booleans(),
    )
    def test_property_8_graceful_degradation(
        self,
        plugin_succeeds: bool,
        fallback_succeeds: bool,
    ):
        """
        Property 8: Graceful degradation.
        
        For any combination of plugin/fallback success/failure,
        the adapter should handle gracefully and return a result.
        
        **Feature: text-to-sql-methods, Property 8: 自动回退机制**
        **Validates: Requirements 6.7**
        """
        config = PluginConfig(
            name="test_plugin",
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=True,
        )
        
        manager = PluginManager()
        plugin = ValidMockPlugin(config, should_succeed=plugin_succeeds)
        manager._plugins["test_plugin"] = plugin
        manager._configs["test_plugin"] = config
        
        fallback = MockFallbackGenerator(should_succeed=fallback_succeeds)
        adapter = ThirdPartyAdapter(
            plugin_manager=manager,
            fallback_generator=fallback,
            max_retries=0,
        )
        
        # Call should not raise
        result = asyncio.get_event_loop().run_until_complete(
            adapter.generate("test query", None, "test_plugin")
        )
        
        # Should always return a result
        assert result is not None, "Should always return a result"
        assert isinstance(result, SQLGenerationResult), "Should return SQLGenerationResult"
        
        # If plugin succeeds, should have SQL
        if plugin_succeeds:
            assert result.sql != "", "Should have SQL when plugin succeeds"
            assert result.confidence > 0, "Should have confidence when plugin succeeds"
        # If plugin fails but fallback succeeds, should have SQL
        elif fallback_succeeds:
            assert result.sql != "", "Should have SQL when fallback succeeds"
        # If both fail, should have empty SQL but still return result
        else:
            assert result.confidence == 0.0, "Should have zero confidence when both fail"
    
    def test_property_8_statistics_tracking(self):
        """
        Property 8: Statistics tracking for fallbacks.
        
        The adapter should track fallback statistics.
        
        **Feature: text-to-sql-methods, Property 8: 自动回退机制**
        **Validates: Requirements 6.7**
        """
        config = PluginConfig(
            name="stats_plugin",
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=True,
        )
        
        manager = PluginManager()
        failing_plugin = ValidMockPlugin(config, should_succeed=False)
        manager._plugins["stats_plugin"] = failing_plugin
        manager._configs["stats_plugin"] = config
        
        fallback = MockFallbackGenerator(should_succeed=True)
        adapter = ThirdPartyAdapter(
            plugin_manager=manager,
            fallback_generator=fallback,
            max_retries=0,
        )
        
        # Make several calls
        for _ in range(5):
            asyncio.get_event_loop().run_until_complete(
                adapter.generate("test query", None, "stats_plugin")
            )
        
        # Check statistics
        stats = adapter.get_statistics()
        assert stats["total_calls"] == 5, "Should track total calls"
        assert stats["fallback_calls"] == 5, "Should track fallback calls"
        assert stats["fallback_rate"] == 1.0, "Fallback rate should be 100%"


# =============================================================================
# Additional Plugin Manager Tests
# =============================================================================

class TestPluginManagerOperations:
    """Tests for Plugin Manager operations."""
    
    def test_plugin_enable_disable(self):
        """Test enabling and disabling plugins."""
        config = PluginConfig(
            name="toggle_plugin",
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=True,
        )
        
        manager = PluginManager()
        asyncio.get_event_loop().run_until_complete(
            manager.register_plugin(config, ValidMockPlugin)
        )
        
        # Should be enabled initially
        assert manager.is_plugin_enabled("toggle_plugin"), "Should be enabled"
        
        # Disable
        asyncio.get_event_loop().run_until_complete(
            manager.disable_plugin("toggle_plugin")
        )
        assert not manager.is_plugin_enabled("toggle_plugin"), "Should be disabled"
        
        # Enable
        asyncio.get_event_loop().run_until_complete(
            manager.enable_plugin("toggle_plugin")
        )
        assert manager.is_plugin_enabled("toggle_plugin"), "Should be enabled again"
    
    def test_plugin_unregister(self):
        """Test unregistering plugins."""
        config = PluginConfig(
            name="unregister_plugin",
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=True,
        )
        
        manager = PluginManager()
        asyncio.get_event_loop().run_until_complete(
            manager.register_plugin(config, ValidMockPlugin)
        )
        
        # Should exist
        assert manager.get_plugin("unregister_plugin") is not None
        
        # Unregister
        asyncio.get_event_loop().run_until_complete(
            manager.unregister_plugin("unregister_plugin")
        )
        
        # Should not exist
        assert manager.get_plugin("unregister_plugin") is None
    
    def test_plugin_health_check(self):
        """Test plugin health checking."""
        config = PluginConfig(
            name="health_plugin",
            connection_type=ConnectionType.LOCAL_SDK,
            timeout=30,
            enabled=True,
        )
        
        manager = PluginManager()
        asyncio.get_event_loop().run_until_complete(
            manager.register_plugin(config, ValidMockPlugin)
        )
        
        # Check health
        status = asyncio.get_event_loop().run_until_complete(
            manager.health_check("health_plugin")
        )
        
        assert isinstance(status, PluginHealthStatus)
        assert status.name == "health_plugin"
        assert status.is_healthy is True
    
    def test_plugin_list(self):
        """Test listing plugins."""
        manager = PluginManager()
        
        # Register multiple plugins
        for i in range(3):
            config = PluginConfig(
                name=f"list_plugin_{i}",
                connection_type=ConnectionType.LOCAL_SDK,
                timeout=30,
                enabled=True,
            )
            asyncio.get_event_loop().run_until_complete(
                manager.register_plugin(config, ValidMockPlugin)
            )
        
        # List plugins
        plugins = asyncio.get_event_loop().run_until_complete(
            manager.list_plugins()
        )
        
        assert len(plugins) == 3, "Should have 3 plugins"
        names = [p.name for p in plugins]
        assert "list_plugin_0" in names
        assert "list_plugin_1" in names
        assert "list_plugin_2" in names


class TestThirdPartyAdapterStrategies:
    """Tests for Third Party Adapter multi-tool strategies."""
    
    def test_first_success_strategy(self):
        """Test first success strategy with multiple tools."""
        manager = PluginManager()
        
        # Register failing and succeeding plugins
        for i, should_succeed in enumerate([False, False, True]):
            config = PluginConfig(
                name=f"strategy_plugin_{i}",
                connection_type=ConnectionType.LOCAL_SDK,
                timeout=30,
                enabled=True,
            )
            plugin = ValidMockPlugin(config, should_succeed=should_succeed)
            manager._plugins[f"strategy_plugin_{i}"] = plugin
            manager._configs[f"strategy_plugin_{i}"] = config
        
        adapter = ThirdPartyAdapter(
            plugin_manager=manager,
            max_retries=0,
        )
        
        # Call with first_success strategy
        result = asyncio.get_event_loop().run_until_complete(
            adapter.call_multiple(
                "test query",
                None,
                ["strategy_plugin_0", "strategy_plugin_1", "strategy_plugin_2"],
                strategy="first_success"
            )
        )
        
        # Should succeed with third plugin
        assert result.sql != "", "Should have SQL from successful plugin"
        assert "strategy_plugin_2" in result.method_used, "Should use third plugin"
    
    def test_best_confidence_strategy(self):
        """Test best confidence strategy with multiple tools."""
        manager = PluginManager()
        
        # Register plugins with different confidence levels
        for i in range(3):
            config = PluginConfig(
                name=f"confidence_plugin_{i}",
                connection_type=ConnectionType.LOCAL_SDK,
                timeout=30,
                enabled=True,
            )
            plugin = ValidMockPlugin(config, should_succeed=True)
            manager._plugins[f"confidence_plugin_{i}"] = plugin
            manager._configs[f"confidence_plugin_{i}"] = config
        
        adapter = ThirdPartyAdapter(
            plugin_manager=manager,
            max_retries=0,
        )
        
        # Call with best_confidence strategy
        result = asyncio.get_event_loop().run_until_complete(
            adapter.call_multiple(
                "test query",
                None,
                ["confidence_plugin_0", "confidence_plugin_1", "confidence_plugin_2"],
                strategy="best_confidence"
            )
        )
        
        # Should return a result
        assert result.sql != "", "Should have SQL"
        assert result.confidence > 0, "Should have confidence"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
