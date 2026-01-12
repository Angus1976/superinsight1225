"""
Tests for TCB Client.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import sys
sys.path.insert(0, '.')

from src.deployment.tcb_client import (
    TCBClient, TCBConfig, ServiceConfig,
    TCBServiceType, DeploymentStatus, DeploymentResult
)


class TestTCBConfig:
    """Tests for TCBConfig."""
    
    def test_config_creation(self):
        """Test creating TCB config."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-secret-id",
            secret_key="test-secret-key"
        )
        
        assert config.env_id == "test-env"
        assert config.secret_id == "test-secret-id"
        assert config.secret_key == "test-secret-key"
        assert config.region == "ap-shanghai"  # default
    
    def test_config_with_custom_region(self):
        """Test config with custom region."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-id",
            secret_key="test-key",
            region="ap-guangzhou"
        )
        
        assert config.region == "ap-guangzhou"


class TestServiceConfig:
    """Tests for ServiceConfig."""
    
    def test_service_config_defaults(self):
        """Test service config default values."""
        config = ServiceConfig(
            service_name="test-service",
            service_type=TCBServiceType.CLOUD_RUN
        )
        
        assert config.service_name == "test-service"
        assert config.cpu == 2
        assert config.memory == 4096
        assert config.min_instances == 1
        assert config.max_instances == 10
        assert config.port == 8000
    
    def test_service_config_custom(self):
        """Test service config with custom values."""
        config = ServiceConfig(
            service_name="custom-service",
            service_type=TCBServiceType.CLOUD_RUN,
            cpu=4,
            memory=8192,
            min_instances=2,
            max_instances=20,
            port=3000,
            env_variables={"KEY": "value"}
        )
        
        assert config.cpu == 4
        assert config.memory == 8192
        assert config.min_instances == 2
        assert config.max_instances == 20
        assert config.port == 3000
        assert config.env_variables == {"KEY": "value"}


class TestTCBClient:
    """Tests for TCBClient."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-id",
            secret_key="test-key"
        )
        
        client = TCBClient(config)
        
        assert client.config.env_id == "test-env"
        assert client.deployments == {}
    
    @pytest.mark.asyncio
    async def test_client_close(self):
        """Test client close."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-id",
            secret_key="test-key"
        )
        
        client = TCBClient(config)
        await client.close()
        
        # Should not raise
        assert True
    
    def test_generate_signature(self):
        """Test signature generation."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-id",
            secret_key="test-key"
        )
        
        client = TCBClient(config)
        
        signature = client._generate_signature(
            "POST",
            "TestAction",
            {"param": "value"},
            1234567890
        )
        
        assert signature is not None
        assert len(signature) > 0
    
    @pytest.mark.asyncio
    async def test_deploy_container_mock(self):
        """Test container deployment with mock."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-id",
            secret_key="test-key"
        )
        
        client = TCBClient(config)
        
        service_config = ServiceConfig(
            service_name="test-service",
            service_type=TCBServiceType.CLOUD_RUN
        )
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {"RequestId": "test-request-id"}
            
            result = await client.deploy_container(
                service_config,
                "test-image:latest"
            )
            
            assert result.deployment_id is not None
            assert result.status in [DeploymentStatus.RUNNING, DeploymentStatus.FAILED]
    
    @pytest.mark.asyncio
    async def test_get_deployment_status_mock(self):
        """Test getting deployment status with mock."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-id",
            secret_key="test-key"
        )
        
        client = TCBClient(config)
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {
                "ServerName": "test-service",
                "Status": "running"
            }
            
            status = await client.get_deployment_status("test-service")
            
            assert "ServerName" in status
    
    @pytest.mark.asyncio
    async def test_scale_service_mock(self):
        """Test scaling service with mock."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-id",
            secret_key="test-key"
        )
        
        client = TCBClient(config)
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {"RequestId": "test-request-id"}
            
            result = await client.scale_service("test-service", 2, 10)
            
            assert result is True
    
    def test_get_deployment_history(self):
        """Test getting deployment history."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-id",
            secret_key="test-key"
        )
        
        client = TCBClient(config)
        
        # Add a mock deployment
        client.deployments["test-deploy"] = DeploymentResult(
            success=True,
            deployment_id="test-deploy",
            status=DeploymentStatus.RUNNING
        )
        
        history = client.get_deployment_history()
        
        assert len(history) == 1
        assert history[0].deployment_id == "test-deploy"
    
    def test_get_statistics(self):
        """Test getting statistics."""
        config = TCBConfig(
            env_id="test-env",
            secret_id="test-id",
            secret_key="test-key"
        )
        
        client = TCBClient(config)
        
        stats = client.get_statistics()
        
        assert "env_id" in stats
        assert "region" in stats
        assert "total_deployments" in stats
        assert "success_rate" in stats


class TestDeploymentResult:
    """Tests for DeploymentResult."""
    
    def test_deployment_result_creation(self):
        """Test creating deployment result."""
        result = DeploymentResult(
            success=True,
            deployment_id="test-deploy",
            status=DeploymentStatus.RUNNING
        )
        
        assert result.success is True
        assert result.deployment_id == "test-deploy"
        assert result.status == DeploymentStatus.RUNNING
    
    def test_deployment_result_with_error(self):
        """Test deployment result with error."""
        result = DeploymentResult(
            success=False,
            deployment_id="test-deploy",
            status=DeploymentStatus.FAILED,
            error_message="Deployment failed"
        )
        
        assert result.success is False
        assert result.error_message == "Deployment failed"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
