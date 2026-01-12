"""
Tests for TCB Environment Configuration Manager.
"""

import pytest
import os
import tempfile
import json
from pathlib import Path

from src.deployment.tcb_env_config import (
    TCBEnvConfigManager,
    EnvironmentConfig,
    Environment,
    ConfigValidationError,
    initialize_tcb_env_config_manager,
    get_tcb_env_config_manager
)


class TestEnvironment:
    """Tests for Environment enum."""
    
    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"


class TestEnvironmentConfig:
    """Tests for EnvironmentConfig."""
    
    def test_config_creation(self):
        """Test environment config creation."""
        config = EnvironmentConfig(
            name=Environment.DEVELOPMENT,
            tcb_env_id="test-env-id"
        )
        
        assert config.name == Environment.DEVELOPMENT
        assert config.tcb_env_id == "test-env-id"
        assert config.tcb_region == "ap-shanghai"
        assert config.min_instances == 1
        assert config.max_instances == 10
    
    def test_config_with_custom_values(self):
        """Test config with custom values."""
        config = EnvironmentConfig(
            name=Environment.PRODUCTION,
            tcb_env_id="prod-env-id",
            min_instances=2,
            max_instances=20,
            cpu=4,
            memory=8192,
            debug=False,
            log_level="WARNING"
        )
        
        assert config.min_instances == 2
        assert config.max_instances == 20
        assert config.cpu == 4
        assert config.memory == 8192
        assert config.debug is False
        assert config.log_level == "WARNING"


class TestTCBEnvConfigManager:
    """Tests for TCBEnvConfigManager."""
    
    def test_initialization(self):
        """Test manager initialization."""
        manager = TCBEnvConfigManager()
        
        assert len(manager.environments) == 4
        assert Environment.DEVELOPMENT in manager.environments
        assert Environment.TESTING in manager.environments
        assert Environment.STAGING in manager.environments
        assert Environment.PRODUCTION in manager.environments
    
    def test_set_environment(self):
        """Test setting current environment."""
        manager = TCBEnvConfigManager()
        
        manager.set_environment(Environment.STAGING)
        
        assert manager.current_environment == Environment.STAGING
    
    def test_set_invalid_environment(self):
        """Test setting invalid environment."""
        manager = TCBEnvConfigManager()
        
        # Remove an environment to test error
        del manager.environments[Environment.DEVELOPMENT]
        
        with pytest.raises(ValueError):
            manager.set_environment(Environment.DEVELOPMENT)
    
    def test_get_environment_config(self):
        """Test getting environment config."""
        manager = TCBEnvConfigManager()
        manager.set_environment(Environment.PRODUCTION)
        
        config = manager.get_environment_config()
        
        assert config.name == Environment.PRODUCTION
        assert config.min_instances == 2
        assert config.enable_backup is True
    
    def test_get_environment_config_specific(self):
        """Test getting specific environment config."""
        manager = TCBEnvConfigManager()
        
        config = manager.get_environment_config(Environment.DEVELOPMENT)
        
        assert config.name == Environment.DEVELOPMENT
        assert config.debug is True
    
    def test_update_environment_config(self):
        """Test updating environment config."""
        manager = TCBEnvConfigManager()
        
        manager.update_environment_config(
            Environment.DEVELOPMENT,
            {"min_instances": 2, "custom_key": "custom_value"}
        )
        
        config = manager.get_environment_config(Environment.DEVELOPMENT)
        assert config.min_instances == 2
        assert config.custom_settings.get("custom_key") == "custom_value"
    
    def test_validate_configuration(self):
        """Test configuration validation."""
        manager = TCBEnvConfigManager()
        manager.set_environment(Environment.DEVELOPMENT)
        
        result = manager.validate_configuration()
        
        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert result["environment"] == "development"
    
    def test_validate_production_debug_error(self):
        """Test production validation catches debug mode."""
        manager = TCBEnvConfigManager()
        
        # Enable debug in production (should cause error)
        manager.environments[Environment.PRODUCTION].debug = True
        
        result = manager.validate_configuration(Environment.PRODUCTION)
        
        assert result["valid"] is False
        assert any("debug" in e.lower() for e in result["errors"])
    
    def test_get_secret(self):
        """Test getting secrets."""
        manager = TCBEnvConfigManager()
        
        # Set environment variable
        os.environ["TEST_SECRET"] = "test_value"
        
        value = manager.get_secret("TEST_SECRET")
        assert value == "test_value"
        
        # Cleanup
        del os.environ["TEST_SECRET"]
    
    def test_set_secret(self):
        """Test setting secrets."""
        manager = TCBEnvConfigManager()
        
        manager.set_secret("NEW_SECRET", "new_value")
        
        assert manager.get_secret("NEW_SECRET") == "new_value"
        assert os.environ.get("NEW_SECRET") == "new_value"
        
        # Cleanup
        del os.environ["NEW_SECRET"]
    
    def test_get_all_secrets_status(self):
        """Test getting secrets status."""
        manager = TCBEnvConfigManager()
        
        status = manager.get_all_secrets_status()
        
        assert "required" in status
        assert "optional" in status
        assert "all_required_configured" in status
    
    def test_generate_env_file(self):
        """Test generating env file."""
        manager = TCBEnvConfigManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, ".env.test")
            
            result = manager.generate_env_file(Environment.DEVELOPMENT, output_path)
            
            assert os.path.exists(result)
            
            with open(result, 'r') as f:
                content = f.read()
            
            assert "TCB_ENV_ID" in content
            assert "ENVIRONMENT=development" in content
            assert "DEBUG=true" in content
    
    def test_export_cloudbaserc(self):
        """Test exporting cloudbaserc.json."""
        manager = TCBEnvConfigManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "cloudbaserc.json")
            
            result = manager.export_cloudbaserc(Environment.STAGING, output_path)
            
            assert os.path.exists(result)
            
            with open(result, 'r') as f:
                config = json.load(f)
            
            assert "framework" in config
            assert "superinsight-staging" in config["framework"]["name"]
    
    def test_get_deployment_config(self):
        """Test getting deployment config."""
        manager = TCBEnvConfigManager()
        manager.set_environment(Environment.PRODUCTION)
        
        config = manager.get_deployment_config()
        
        assert config["environment"] == "production"
        assert "tcb" in config
        assert "scaling" in config
        assert "resources" in config
        assert "application" in config
        assert "features" in config
    
    def test_get_statistics(self):
        """Test getting statistics."""
        manager = TCBEnvConfigManager()
        
        stats = manager.get_statistics()
        
        assert stats["environments_configured"] == 4
        assert "secrets_configured" in stats
        assert "required_secrets_count" in stats


class TestGlobalEnvConfigManager:
    """Tests for global environment config manager functions."""
    
    def test_initialize_and_get(self):
        """Test initializing and getting global manager."""
        manager = initialize_tcb_env_config_manager()
        
        assert manager is not None
        assert get_tcb_env_config_manager() is manager
