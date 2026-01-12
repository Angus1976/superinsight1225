"""
Tests for Blue-Green Deployer.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, '.')

from src.deployment.blue_green_deployer import (
    BlueGreenDeployer, BlueGreenConfig,
    DeploymentStrategy, DeploymentPhase, EnvironmentColor,
    DeploymentEnvironment, DeploymentResult
)


class TestBlueGreenConfig:
    """Tests for BlueGreenConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = BlueGreenConfig()
        
        assert config.health_check_timeout == 300.0
        assert config.health_check_interval == 10.0
        assert config.rollback_on_failure is True
        assert len(config.traffic_shift_steps) > 0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = BlueGreenConfig(
            health_check_timeout=600.0,
            traffic_shift_steps=[25, 50, 100],
            rollback_on_failure=False
        )
        
        assert config.health_check_timeout == 600.0
        assert config.traffic_shift_steps == [25, 50, 100]
        assert config.rollback_on_failure is False


class TestDeploymentEnvironment:
    """Tests for DeploymentEnvironment."""
    
    def test_environment_creation(self):
        """Test creating deployment environment."""
        env = DeploymentEnvironment(
            color=EnvironmentColor.BLUE,
            version="1.0.0"
        )
        
        assert env.color == EnvironmentColor.BLUE
        assert env.version == "1.0.0"
        assert env.is_active is False
        assert env.traffic_percentage == 0


class TestBlueGreenDeployer:
    """Tests for BlueGreenDeployer."""
    
    def test_initialization(self):
        """Test deployer initialization."""
        deployer = BlueGreenDeployer()
        
        assert deployer is not None
        assert len(deployer.environments) == 2
        assert EnvironmentColor.BLUE in deployer.environments
        assert EnvironmentColor.GREEN in deployer.environments
    
    def test_get_active_environment(self):
        """Test getting active environment."""
        deployer = BlueGreenDeployer()
        
        active = deployer.get_active_environment()
        
        assert active is not None
        assert active.color == EnvironmentColor.BLUE  # Default active
    
    def test_get_inactive_environment(self):
        """Test getting inactive environment."""
        deployer = BlueGreenDeployer()
        
        inactive = deployer.get_inactive_environment()
        
        assert inactive is not None
        assert inactive.color == EnvironmentColor.GREEN  # Opposite of active
    
    def test_set_callbacks(self):
        """Test setting callbacks."""
        deployer = BlueGreenDeployer()
        
        async def health_check(env):
            return True
        
        async def deploy(env, version, metadata):
            return True
        
        deployer.set_health_check_callback(health_check)
        deployer.set_deploy_callback(deploy)
        
        assert deployer._health_check_callback is not None
        assert deployer._deploy_callback is not None
    
    @pytest.mark.asyncio
    async def test_deploy_blue_green(self):
        """Test blue-green deployment."""
        deployer = BlueGreenDeployer()
        
        # Set mock callbacks
        deployer.set_health_check_callback(AsyncMock(return_value=True))
        deployer.set_deploy_callback(AsyncMock(return_value=True))
        
        # Use immediate strategy for faster test
        result = await deployer.deploy(
            version="1.0.0",
            strategy=DeploymentStrategy.IMMEDIATE
        )
        
        assert result.deployment_id is not None
        assert result.version == "1.0.0"
        assert result.strategy == DeploymentStrategy.IMMEDIATE
    
    @pytest.mark.asyncio
    async def test_deploy_with_failure(self):
        """Test deployment with failure."""
        config = BlueGreenConfig(rollback_on_failure=True)
        deployer = BlueGreenDeployer(config)
        
        # Set mock callbacks - deploy fails
        deployer.set_health_check_callback(AsyncMock(return_value=True))
        deployer.set_deploy_callback(AsyncMock(side_effect=Exception("Deploy failed")))
        
        result = await deployer.deploy(
            version="1.0.0",
            strategy=DeploymentStrategy.IMMEDIATE
        )
        
        assert result.success is False
        assert result.phase == DeploymentPhase.ROLLING_BACK
    
    @pytest.mark.asyncio
    async def test_manual_rollback(self):
        """Test manual rollback."""
        deployer = BlueGreenDeployer()
        
        # Set up environments
        deployer.environments[EnvironmentColor.BLUE].version = "1.0.0"
        deployer.environments[EnvironmentColor.BLUE].is_active = True
        deployer.environments[EnvironmentColor.BLUE].traffic_percentage = 100
        
        deployer.environments[EnvironmentColor.GREEN].version = "0.9.0"
        deployer.environments[EnvironmentColor.GREEN].is_active = False
        deployer.environments[EnvironmentColor.GREEN].traffic_percentage = 0
        
        result = await deployer.manual_rollback()
        
        assert result is True
        assert deployer.environments[EnvironmentColor.GREEN].is_active is True
        assert deployer.environments[EnvironmentColor.GREEN].traffic_percentage == 100
    
    def test_get_current_state(self):
        """Test getting current state."""
        deployer = BlueGreenDeployer()
        
        state = deployer.get_current_state()
        
        assert "environments" in state
        assert "blue" in state["environments"]
        assert "green" in state["environments"]
    
    def test_get_deployment_history(self):
        """Test getting deployment history."""
        deployer = BlueGreenDeployer()
        
        history = deployer.get_deployment_history()
        
        assert isinstance(history, list)
    
    def test_get_statistics(self):
        """Test getting statistics."""
        deployer = BlueGreenDeployer()
        
        stats = deployer.get_statistics()
        
        assert "total_deployments" in stats
        assert "successful_deployments" in stats
        assert "success_rate" in stats
        assert "current_active_environment" in stats


class TestDeploymentStrategies:
    """Tests for different deployment strategies."""
    
    @pytest.mark.asyncio
    async def test_immediate_strategy(self):
        """Test immediate deployment strategy."""
        deployer = BlueGreenDeployer()
        deployer.set_health_check_callback(AsyncMock(return_value=True))
        deployer.set_deploy_callback(AsyncMock(return_value=True))
        
        result = await deployer.deploy(
            version="1.0.0",
            strategy=DeploymentStrategy.IMMEDIATE
        )
        
        assert result.strategy == DeploymentStrategy.IMMEDIATE
    
    @pytest.mark.asyncio
    async def test_rolling_strategy(self):
        """Test rolling deployment strategy."""
        deployer = BlueGreenDeployer()
        deployer.set_health_check_callback(AsyncMock(return_value=True))
        deployer.set_deploy_callback(AsyncMock(return_value=True))
        
        result = await deployer.deploy(
            version="1.0.0",
            strategy=DeploymentStrategy.ROLLING
        )
        
        assert result.strategy == DeploymentStrategy.ROLLING


class TestDeploymentEvents:
    """Tests for deployment events."""
    
    @pytest.mark.asyncio
    async def test_events_recorded(self):
        """Test that events are recorded during deployment."""
        deployer = BlueGreenDeployer()
        deployer.set_health_check_callback(AsyncMock(return_value=True))
        deployer.set_deploy_callback(AsyncMock(return_value=True))
        
        result = await deployer.deploy(
            version="1.0.0",
            strategy=DeploymentStrategy.IMMEDIATE
        )
        
        assert len(result.events) > 0
        assert result.events[0].event_type == "deployment_started"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
