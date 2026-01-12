"""
Tests for Container Manager.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, '.')

from src.system.container_manager import (
    ContainerManager, ContainerManagerConfig,
    ServiceStatus, ServiceType, ServiceInfo
)


class TestContainerManager:
    """Tests for ContainerManager."""
    
    def test_initialization(self):
        """Test container manager initialization."""
        manager = ContainerManager()
        
        assert manager is not None
        assert len(manager.services) > 0
        assert "postgresql" in manager.services
        assert "redis" in manager.services
        assert "superinsight-api" in manager.services
    
    def test_default_services_registered(self):
        """Test that default services are registered."""
        manager = ContainerManager()
        
        expected_services = ["postgresql", "redis", "label-studio", "superinsight-api", "nginx"]
        for service_name in expected_services:
            assert service_name in manager.services
    
    def test_service_info_structure(self):
        """Test service info structure."""
        manager = ContainerManager()
        
        postgres = manager.services.get("postgresql")
        assert postgres is not None
        assert postgres.name == "postgresql"
        assert postgres.service_type == ServiceType.DATABASE
        assert postgres.port == 5432
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = ContainerManagerConfig(
            health_check_interval=60.0,
            max_restart_attempts=5,
            restart_delay_seconds=10.0
        )
        
        manager = ContainerManager(config)
        
        assert manager.config.health_check_interval == 60.0
        assert manager.config.max_restart_attempts == 5
        assert manager.config.restart_delay_seconds == 10.0
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop."""
        manager = ContainerManager()
        
        await manager.start()
        assert manager._is_running is True
        
        await manager.stop()
        assert manager._is_running is False
    
    @pytest.mark.asyncio
    async def test_get_service_status(self):
        """Test getting service status."""
        manager = ContainerManager()
        
        status = await manager.get_service_status("postgresql")
        
        assert status is not None
        assert status.name == "postgresql"
    
    @pytest.mark.asyncio
    async def test_get_all_services_status(self):
        """Test getting all services status."""
        manager = ContainerManager()
        
        all_status = await manager.get_all_services_status()
        
        assert len(all_status) > 0
        assert "postgresql" in all_status
    
    def test_get_statistics(self):
        """Test getting statistics."""
        manager = ContainerManager()
        
        stats = manager.get_statistics()
        
        assert "total_services" in stats
        assert "running_services" in stats
        assert "failed_services" in stats
        assert "services" in stats
    
    @pytest.mark.asyncio
    async def test_restart_service_mock(self):
        """Test restart service with mock."""
        manager = ContainerManager()
        
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_process
            
            result = await manager.restart_service("postgresql")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_check_service_health_mock(self):
        """Test service health check with mock."""
        manager = ContainerManager()
        service = manager.services["postgresql"]
        
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process
            
            is_healthy = await manager._check_service_health(service)
            
            assert is_healthy is True


class TestServiceInfo:
    """Tests for ServiceInfo dataclass."""
    
    def test_service_info_creation(self):
        """Test creating ServiceInfo."""
        info = ServiceInfo(
            name="test_service",
            service_type=ServiceType.APPLICATION,
            port=8000
        )
        
        assert info.name == "test_service"
        assert info.service_type == ServiceType.APPLICATION
        assert info.port == 8000
        assert info.status == ServiceStatus.UNKNOWN
        assert info.restart_count == 0
    
    def test_service_info_with_all_fields(self):
        """Test ServiceInfo with all fields."""
        info = ServiceInfo(
            name="test_service",
            service_type=ServiceType.DATABASE,
            port=5432,
            status=ServiceStatus.RUNNING,
            pid=12345,
            uptime_seconds=3600.0,
            restart_count=2,
            memory_mb=256.0,
            cpu_percent=15.5
        )
        
        assert info.pid == 12345
        assert info.uptime_seconds == 3600.0
        assert info.restart_count == 2
        assert info.memory_mb == 256.0
        assert info.cpu_percent == 15.5


class TestContainerManagerConfig:
    """Tests for ContainerManagerConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ContainerManagerConfig()
        
        assert config.health_check_interval == 30.0
        assert config.max_restart_attempts == 3
        assert config.restart_delay_seconds == 5.0
        assert config.startup_timeout_seconds == 120.0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = ContainerManagerConfig(
            health_check_interval=15.0,
            max_restart_attempts=5
        )
        
        assert config.health_check_interval == 15.0
        assert config.max_restart_attempts == 5


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
