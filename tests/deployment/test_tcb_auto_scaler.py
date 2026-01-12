"""
Tests for TCB Auto-Scaler.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.deployment.tcb_auto_scaler import (
    TCBAutoScaler,
    TCBAutoScalerConfig,
    ScalingRule,
    ScalingMetricType,
    ScalingDirection,
    initialize_tcb_auto_scaler,
    get_tcb_auto_scaler
)


class TestTCBAutoScalerConfig:
    """Tests for TCBAutoScalerConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = TCBAutoScalerConfig()
        
        assert config.min_instances == 1
        assert config.max_instances == 10
        assert config.evaluation_interval == 60.0
        assert config.scale_up_cooldown == 300.0
        assert config.scale_down_cooldown == 600.0
        assert config.default_cpu_threshold_up == 70.0
        assert config.default_cpu_threshold_down == 30.0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = TCBAutoScalerConfig(
            min_instances=2,
            max_instances=20,
            evaluation_interval=30.0
        )
        
        assert config.min_instances == 2
        assert config.max_instances == 20
        assert config.evaluation_interval == 30.0


class TestScalingRule:
    """Tests for ScalingRule."""
    
    def test_rule_creation(self):
        """Test scaling rule creation."""
        rule = ScalingRule(
            name="test_rule",
            metric_type=ScalingMetricType.CPU,
            threshold_up=80.0,
            threshold_down=20.0
        )
        
        assert rule.name == "test_rule"
        assert rule.metric_type == ScalingMetricType.CPU
        assert rule.threshold_up == 80.0
        assert rule.threshold_down == 20.0
        assert rule.enabled is True
    
    def test_rule_with_custom_increments(self):
        """Test rule with custom scale increments."""
        rule = ScalingRule(
            name="custom_rule",
            metric_type=ScalingMetricType.REQUEST_RATE,
            threshold_up=100.0,
            threshold_down=10.0,
            scale_up_increment=3,
            scale_down_increment=2
        )
        
        assert rule.scale_up_increment == 3
        assert rule.scale_down_increment == 2


class TestTCBAutoScaler:
    """Tests for TCBAutoScaler."""
    
    def test_initialization(self):
        """Test auto-scaler initialization."""
        scaler = TCBAutoScaler()
        
        assert scaler.current_instances == 1
        assert len(scaler.rules) == 3  # Default rules
        assert "cpu_scaling" in scaler.rules
        assert "memory_scaling" in scaler.rules
        assert "request_rate_scaling" in scaler.rules
    
    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        config = TCBAutoScalerConfig(min_instances=2, max_instances=5)
        scaler = TCBAutoScaler(config)
        
        assert scaler.config.min_instances == 2
        assert scaler.config.max_instances == 5
        assert scaler.current_instances == 2
    
    def test_add_rule(self):
        """Test adding a scaling rule."""
        scaler = TCBAutoScaler()
        
        rule = ScalingRule(
            name="custom_rule",
            metric_type=ScalingMetricType.RESPONSE_TIME,
            threshold_up=500.0,
            threshold_down=100.0
        )
        
        scaler.add_rule(rule)
        
        assert "custom_rule" in scaler.rules
        assert scaler.rules["custom_rule"].metric_type == ScalingMetricType.RESPONSE_TIME
    
    def test_remove_rule(self):
        """Test removing a scaling rule."""
        scaler = TCBAutoScaler()
        
        assert scaler.remove_rule("cpu_scaling") is True
        assert "cpu_scaling" not in scaler.rules
        assert scaler.remove_rule("nonexistent") is False
    
    def test_enable_disable_rule(self):
        """Test enabling and disabling rules."""
        scaler = TCBAutoScaler()
        
        scaler.disable_rule("cpu_scaling")
        assert scaler.rules["cpu_scaling"].enabled is False
        
        scaler.enable_rule("cpu_scaling")
        assert scaler.rules["cpu_scaling"].enabled is True
    
    @pytest.mark.asyncio
    async def test_manual_scale(self):
        """Test manual scaling."""
        scaler = TCBAutoScaler()
        
        result = await scaler.manual_scale(5)
        
        assert result is True
        assert scaler.current_instances == 5
        assert len(scaler.scaling_history) == 1
    
    @pytest.mark.asyncio
    async def test_manual_scale_out_of_range(self):
        """Test manual scaling with out of range value."""
        scaler = TCBAutoScaler()
        
        result = await scaler.manual_scale(100)  # Above max
        assert result is False
        
        result = await scaler.manual_scale(0)  # Below min
        assert result is False
    
    def test_get_current_state(self):
        """Test getting current state."""
        scaler = TCBAutoScaler()
        state = scaler.get_current_state()
        
        assert "current_instances" in state
        assert "min_instances" in state
        assert "max_instances" in state
        assert "is_running" in state
        assert "rules" in state
    
    def test_get_scaling_history(self):
        """Test getting scaling history."""
        scaler = TCBAutoScaler()
        history = scaler.get_scaling_history()
        
        assert isinstance(history, list)
    
    def test_get_statistics(self):
        """Test getting statistics."""
        scaler = TCBAutoScaler()
        stats = scaler.get_statistics()
        
        assert "total_scaling_events" in stats
        assert "scale_up_events" in stats
        assert "scale_down_events" in stats
        assert "current_instances" in stats
        assert "active_rules" in stats
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the scaler."""
        scaler = TCBAutoScaler()
        
        await scaler.start()
        assert scaler._is_running is True
        
        await scaler.stop()
        assert scaler._is_running is False
    
    def test_set_callbacks(self):
        """Test setting callbacks."""
        scaler = TCBAutoScaler()
        
        async def metrics_callback():
            return {"cpu_usage_percent": 50.0}
        
        async def scale_callback(instances):
            return True
        
        scaler.set_metrics_callback(metrics_callback)
        scaler.set_scale_callback(scale_callback)
        
        assert scaler._metrics_callback is not None
        assert scaler._scale_callback is not None


class TestGlobalAutoScaler:
    """Tests for global auto-scaler functions."""
    
    def test_initialize_and_get(self):
        """Test initializing and getting global auto-scaler."""
        scaler = initialize_tcb_auto_scaler()
        
        assert scaler is not None
        assert get_tcb_auto_scaler() is scaler
    
    def test_initialize_with_config(self):
        """Test initializing with custom config."""
        config = TCBAutoScalerConfig(min_instances=3)
        scaler = initialize_tcb_auto_scaler(config)
        
        assert scaler.config.min_instances == 3
