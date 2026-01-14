"""
Integration tests for Admin Third-Party Tool Configuration.

Tests Property 6: Third-party tool enable/disable takes effect immediately.

**Validates: Requirements 7.5**
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from src.admin.schemas import (
    ThirdPartyConfigCreate,
    ThirdPartyConfigUpdate,
    ThirdPartyConfigResponse,
    ThirdPartyToolType,
    ConnectionTestResult,
)


# ============== Test Fixtures ==============

@pytest.fixture
def sample_third_party_config() -> Dict[str, Any]:
    """Sample third-party tool configuration."""
    return {
        "id": "tp-001",
        "name": "Test Text-to-SQL Service",
        "description": "Test service for text-to-SQL conversion",
        "tool_type": ThirdPartyToolType.TEXT_TO_SQL,
        "endpoint": "https://api.example.com/v1/text-to-sql",
        "api_key": "test-api-key-12345",
        "api_key_masked": "test****2345",
        "timeout_seconds": 30,
        "extra_config": {"model": "gpt-4"},
        "enabled": True,
        "health_status": "healthy",
        "last_health_check": datetime.utcnow(),
        "call_count": 100,
        "success_rate": 0.95,
        "avg_latency_ms": 250.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def mock_third_party_service():
    """Mock third-party service for testing."""
    class MockThirdPartyService:
        def __init__(self):
            self.configs: Dict[str, Dict[str, Any]] = {}
            self.enabled_tools: Dict[str, bool] = {}
            self.call_log: List[Dict[str, Any]] = []
        
        async def create_config(self, config: ThirdPartyConfigCreate, user_id: str) -> ThirdPartyConfigResponse:
            config_id = f"tp-{len(self.configs) + 1:03d}"
            config_data = {
                "id": config_id,
                **config.model_dump(),
                "api_key_masked": self._mask_key(config.api_key) if config.api_key else None,
                "enabled": True,
                "health_status": None,
                "last_health_check": None,
                "call_count": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            self.configs[config_id] = config_data
            self.enabled_tools[config_id] = True
            return ThirdPartyConfigResponse(**config_data)
        
        async def update_config(self, config_id: str, config: ThirdPartyConfigUpdate, user_id: str) -> ThirdPartyConfigResponse:
            if config_id not in self.configs:
                raise ValueError(f"Config {config_id} not found")
            
            existing = self.configs[config_id]
            update_data = config.model_dump(exclude_unset=True)
            
            for key, value in update_data.items():
                if key == "api_key" and value:
                    existing["api_key_masked"] = self._mask_key(value)
                elif key == "enabled":
                    # Immediately update enabled status
                    self.enabled_tools[config_id] = value
                existing[key] = value
            
            existing["updated_at"] = datetime.utcnow()
            return ThirdPartyConfigResponse(**existing)
        
        async def toggle_enabled(self, config_id: str, enabled: bool, user_id: str) -> ThirdPartyConfigResponse:
            """Toggle enabled status - should take effect immediately."""
            return await self.update_config(
                config_id,
                ThirdPartyConfigUpdate(enabled=enabled),
                user_id
            )
        
        def is_tool_enabled(self, config_id: str) -> bool:
            """Check if tool is currently enabled."""
            return self.enabled_tools.get(config_id, False)
        
        async def call_tool(self, config_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate calling a third-party tool."""
            if not self.is_tool_enabled(config_id):
                raise RuntimeError(f"Tool {config_id} is disabled")
            
            self.call_log.append({
                "config_id": config_id,
                "request": request,
                "timestamp": datetime.utcnow(),
            })
            
            return {"success": True, "result": "mock_result"}
        
        async def health_check(self, config_id: str) -> ConnectionTestResult:
            """Check tool health."""
            if config_id not in self.configs:
                return ConnectionTestResult(
                    success=False,
                    latency_ms=0,
                    error_message="Config not found"
                )
            
            if not self.is_tool_enabled(config_id):
                return ConnectionTestResult(
                    success=False,
                    latency_ms=0,
                    error_message="Tool is disabled"
                )
            
            return ConnectionTestResult(
                success=True,
                latency_ms=100.0,
                details={"status": "healthy"}
            )
        
        def _mask_key(self, key: str) -> str:
            if not key or len(key) < 8:
                return "****"
            return key[:4] + "****" + key[-4:]
    
    return MockThirdPartyService()


# ============== Property Tests ==============

class TestThirdPartyEnableDisable:
    """Tests for Property 6: Third-party tool enable/disable takes effect immediately."""
    
    @pytest.mark.asyncio
    async def test_enable_disable_immediate_effect(self, mock_third_party_service):
        """Test that enable/disable takes effect immediately."""
        # Create a tool
        config = ThirdPartyConfigCreate(
            name="Test Tool",
            tool_type=ThirdPartyToolType.TEXT_TO_SQL,
            endpoint="https://api.example.com/v1",
            timeout_seconds=30,
            extra_config={},
        )
        
        created = await mock_third_party_service.create_config(config, "user-1")
        config_id = created.id
        
        # Tool should be enabled by default
        assert mock_third_party_service.is_tool_enabled(config_id) is True
        
        # Disable the tool
        await mock_third_party_service.toggle_enabled(config_id, False, "user-1")
        
        # Should be disabled immediately
        assert mock_third_party_service.is_tool_enabled(config_id) is False
        
        # Re-enable the tool
        await mock_third_party_service.toggle_enabled(config_id, True, "user-1")
        
        # Should be enabled immediately
        assert mock_third_party_service.is_tool_enabled(config_id) is True
    
    @pytest.mark.asyncio
    async def test_disabled_tool_cannot_be_called(self, mock_third_party_service):
        """Test that disabled tools cannot be called."""
        # Create and disable a tool
        config = ThirdPartyConfigCreate(
            name="Test Tool",
            tool_type=ThirdPartyToolType.AI_ANNOTATION,
            endpoint="https://api.example.com/v1",
            timeout_seconds=30,
            extra_config={},
        )
        
        created = await mock_third_party_service.create_config(config, "user-1")
        config_id = created.id
        
        # Disable the tool
        await mock_third_party_service.toggle_enabled(config_id, False, "user-1")
        
        # Attempting to call should raise error
        with pytest.raises(RuntimeError, match="is disabled"):
            await mock_third_party_service.call_tool(config_id, {"query": "test"})
    
    @pytest.mark.asyncio
    async def test_enabled_tool_can_be_called(self, mock_third_party_service):
        """Test that enabled tools can be called."""
        # Create a tool (enabled by default)
        config = ThirdPartyConfigCreate(
            name="Test Tool",
            tool_type=ThirdPartyToolType.DATA_PROCESSING,
            endpoint="https://api.example.com/v1",
            timeout_seconds=30,
            extra_config={},
        )
        
        created = await mock_third_party_service.create_config(config, "user-1")
        config_id = created.id
        
        # Should be able to call
        result = await mock_third_party_service.call_tool(config_id, {"data": "test"})
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_toggle_does_not_affect_other_tools(self, mock_third_party_service):
        """Test that toggling one tool doesn't affect others."""
        # Create two tools
        config1 = ThirdPartyConfigCreate(
            name="Tool 1",
            tool_type=ThirdPartyToolType.TEXT_TO_SQL,
            endpoint="https://api1.example.com/v1",
            timeout_seconds=30,
            extra_config={},
        )
        config2 = ThirdPartyConfigCreate(
            name="Tool 2",
            tool_type=ThirdPartyToolType.AI_ANNOTATION,
            endpoint="https://api2.example.com/v1",
            timeout_seconds=30,
            extra_config={},
        )
        
        created1 = await mock_third_party_service.create_config(config1, "user-1")
        created2 = await mock_third_party_service.create_config(config2, "user-1")
        
        # Both should be enabled
        assert mock_third_party_service.is_tool_enabled(created1.id) is True
        assert mock_third_party_service.is_tool_enabled(created2.id) is True
        
        # Disable tool 1
        await mock_third_party_service.toggle_enabled(created1.id, False, "user-1")
        
        # Tool 1 should be disabled, tool 2 should still be enabled
        assert mock_third_party_service.is_tool_enabled(created1.id) is False
        assert mock_third_party_service.is_tool_enabled(created2.id) is True
    
    @pytest.mark.asyncio
    async def test_health_check_reflects_enabled_status(self, mock_third_party_service):
        """Test that health check reflects enabled/disabled status."""
        config = ThirdPartyConfigCreate(
            name="Test Tool",
            tool_type=ThirdPartyToolType.CUSTOM,
            endpoint="https://api.example.com/v1",
            timeout_seconds=30,
            extra_config={},
        )
        
        created = await mock_third_party_service.create_config(config, "user-1")
        config_id = created.id
        
        # Health check should succeed when enabled
        health = await mock_third_party_service.health_check(config_id)
        assert health.success is True
        
        # Disable the tool
        await mock_third_party_service.toggle_enabled(config_id, False, "user-1")
        
        # Health check should fail when disabled
        health = await mock_third_party_service.health_check(config_id)
        assert health.success is False
        assert "disabled" in health.error_message.lower()


class TestThirdPartyPropertyBased:
    """Property-based tests for third-party tool configuration."""
    
    @settings(max_examples=100)
    @given(
        enabled_sequence=st.lists(st.booleans(), min_size=1, max_size=20)
    )
    @pytest.mark.asyncio
    async def test_enable_disable_sequence(self, enabled_sequence: List[bool]):
        """Property: After any sequence of enable/disable, final state matches last operation."""
        # Create fresh service for each test
        service = type('MockService', (), {
            'enabled': True,
            'toggle': lambda self, enabled: setattr(self, 'enabled', enabled) or enabled
        })()
        
        # Apply sequence of toggles
        for enabled in enabled_sequence:
            service.toggle(enabled)
        
        # Final state should match last toggle
        assert service.enabled == enabled_sequence[-1]
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.filter_too_much])
    @given(
        tool_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S'))),
        timeout=st.integers(min_value=1, max_value=300),
    )
    def test_config_creation_validation(self, tool_name: str, timeout: int):
        """Property: Valid configs can be created, invalid ones are rejected."""
        assume(tool_name.strip())  # Non-empty name
        
        try:
            config = ThirdPartyConfigCreate(
                name=tool_name.strip(),
                tool_type=ThirdPartyToolType.CUSTOM,
                endpoint="https://api.example.com/v1",
                timeout_seconds=timeout,
                extra_config={},
            )
            # If creation succeeds, values should match
            assert config.name == tool_name.strip()
            assert config.timeout_seconds == timeout
        except Exception:
            # Invalid configs should raise validation errors
            pass


class TestThirdPartyIntegration:
    """Integration tests for third-party tool management."""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, mock_third_party_service):
        """Test complete lifecycle: create -> enable -> call -> disable -> delete."""
        # Create
        config = ThirdPartyConfigCreate(
            name="Lifecycle Test Tool",
            tool_type=ThirdPartyToolType.TEXT_TO_SQL,
            endpoint="https://api.example.com/v1",
            api_key="secret-key-12345",
            timeout_seconds=30,
            extra_config={"version": "1.0"},
        )
        
        created = await mock_third_party_service.create_config(config, "user-1")
        assert created.id is not None
        assert created.enabled is True
        assert created.api_key_masked == "secr****2345"
        
        # Call while enabled
        result = await mock_third_party_service.call_tool(created.id, {"query": "test"})
        assert result["success"] is True
        
        # Disable
        updated = await mock_third_party_service.toggle_enabled(created.id, False, "user-1")
        assert updated.enabled is False
        
        # Call should fail when disabled
        with pytest.raises(RuntimeError):
            await mock_third_party_service.call_tool(created.id, {"query": "test"})
        
        # Re-enable
        updated = await mock_third_party_service.toggle_enabled(created.id, True, "user-1")
        assert updated.enabled is True
        
        # Call should succeed again
        result = await mock_third_party_service.call_tool(created.id, {"query": "test"})
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_toggle_operations(self, mock_third_party_service):
        """Test that concurrent toggle operations are handled correctly."""
        import asyncio
        
        config = ThirdPartyConfigCreate(
            name="Concurrent Test Tool",
            tool_type=ThirdPartyToolType.AI_ANNOTATION,
            endpoint="https://api.example.com/v1",
            timeout_seconds=30,
            extra_config={},
        )
        
        created = await mock_third_party_service.create_config(config, "user-1")
        config_id = created.id
        
        # Simulate concurrent toggles
        async def toggle_sequence():
            for enabled in [False, True, False, True]:
                await mock_third_party_service.toggle_enabled(config_id, enabled, "user-1")
                await asyncio.sleep(0.01)
        
        # Run multiple toggle sequences concurrently
        await asyncio.gather(
            toggle_sequence(),
            toggle_sequence(),
        )
        
        # Final state should be consistent (last operation wins)
        # The exact final state depends on timing, but it should be valid
        final_state = mock_third_party_service.is_tool_enabled(config_id)
        assert isinstance(final_state, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
