"""
Unit tests for AI gateway deployment script.

Tests the deployment script functionality including:
- Gateway configuration fetching
- Environment variable building
- Docker compose deployment
- Health check verification
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from deploy_ai_gateway import (
    fetch_gateway_config,
    build_environment_vars,
    write_env_file,
    deploy_with_docker_compose,
    verify_health
)
from src.models.ai_integration import AIGateway


class TestFetchGatewayConfig:
    """Test gateway configuration fetching."""
    
    def test_fetch_existing_gateway(self):
        """Test fetching an existing gateway."""
        # Arrange
        mock_db = Mock()
        gateway = AIGateway(
            id="gateway-123",
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant-456",
            status="active",
            api_key_hash="hashed_key",
            api_secret_hash="hashed_secret",
            configuration={}
        )
        mock_db.query().filter().first.return_value = gateway
        
        # Act
        result = fetch_gateway_config("gateway-123", mock_db)
        
        # Assert
        assert result is not None
        assert result.id == "gateway-123"
        assert result.name == "Test Gateway"
    
    def test_fetch_nonexistent_gateway(self):
        """Test fetching a non-existent gateway."""
        # Arrange
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None
        
        # Act
        result = fetch_gateway_config("nonexistent", mock_db)
        
        # Assert
        assert result is None
    
    def test_fetch_inactive_gateway(self, capsys):
        """Test fetching an inactive gateway shows warning."""
        # Arrange
        mock_db = Mock()
        gateway = AIGateway(
            id="gateway-123",
            name="Inactive Gateway",
            gateway_type="openclaw",
            tenant_id="tenant-456",
            status="inactive",
            api_key_hash="hashed_key",
            api_secret_hash="hashed_secret",
            configuration={}
        )
        mock_db.query().filter().first.return_value = gateway
        
        # Act
        result = fetch_gateway_config("gateway-123", mock_db)
        captured = capsys.readouterr()
        
        # Assert
        assert result is not None
        assert "Warning: Gateway gateway-123 is inactive" in captured.out


class TestBuildEnvironmentVars:
    """Test environment variable building."""
    
    def test_build_minimal_env_vars(self):
        """Test building environment variables with minimal config."""
        # Arrange
        gateway = AIGateway(
            id="gateway-123",
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant-456",
            status="active",
            api_key_hash="hashed_key",
            api_secret_hash="hashed_secret",
            configuration={}
        )
        
        # Act
        env_vars = build_environment_vars(gateway)
        
        # Assert
        assert env_vars["TENANT_ID"] == "tenant-456"
        assert env_vars["OPENCLAW_API_KEY"] == "hashed_key"
        assert len(env_vars) == 2
    
    def test_build_env_vars_with_llm_config(self):
        """Test building environment variables with LLM configuration."""
        # Arrange
        gateway = AIGateway(
            id="gateway-123",
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant-456",
            status="active",
            api_key_hash="hashed_key",
            api_secret_hash="hashed_secret",
            configuration={
                "llm": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "api_key": "sk-123456"
                }
            }
        )
        
        # Act
        env_vars = build_environment_vars(gateway)
        
        # Assert
        assert env_vars["OPENCLAW_LLM_PROVIDER"] == "openai"
        assert env_vars["OPENCLAW_LLM_MODEL"] == "gpt-4"
        assert env_vars["OPENCLAW_LLM_API_KEY"] == "sk-123456"
    
    def test_build_env_vars_with_language_config(self):
        """Test building environment variables with language configuration."""
        # Arrange
        gateway = AIGateway(
            id="gateway-123",
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant-456",
            status="active",
            api_key_hash="hashed_key",
            api_secret_hash="hashed_secret",
            configuration={
                "language": {
                    "user_language": "en-US",
                    "locale": "en-US",
                    "system_prompt": "You are a helpful assistant"
                }
            }
        )
        
        # Act
        env_vars = build_environment_vars(gateway)
        
        # Assert
        assert env_vars["OPENCLAW_USER_LANGUAGE"] == "en-US"
        assert env_vars["OPENCLAW_LOCALE"] == "en-US"
        assert env_vars["OPENCLAW_SYSTEM_PROMPT"] == "You are a helpful assistant"
    
    def test_build_env_vars_with_agent_config(self):
        """Test building environment variables with agent configuration."""
        # Arrange
        gateway = AIGateway(
            id="gateway-123",
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant-456",
            status="active",
            api_key_hash="hashed_key",
            api_secret_hash="hashed_secret",
            configuration={
                "agent": {
                    "name": "Custom Assistant",
                    "description": "Custom description"
                }
            }
        )
        
        # Act
        env_vars = build_environment_vars(gateway)
        
        # Assert
        assert env_vars["OPENCLAW_AGENT_NAME"] == "Custom Assistant"
        assert env_vars["OPENCLAW_AGENT_DESCRIPTION"] == "Custom description"
    
    def test_build_env_vars_with_logging_config(self):
        """Test building environment variables with logging configuration."""
        # Arrange
        gateway = AIGateway(
            id="gateway-123",
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant-456",
            status="active",
            api_key_hash="hashed_key",
            api_secret_hash="hashed_secret",
            configuration={
                "logging": {
                    "level": "debug"
                }
            }
        )
        
        # Act
        env_vars = build_environment_vars(gateway)
        
        # Assert
        assert env_vars["OPENCLAW_LOG_LEVEL"] == "debug"
    
    def test_build_env_vars_with_complete_config(self):
        """Test building environment variables with complete configuration."""
        # Arrange
        gateway = AIGateway(
            id="gateway-123",
            name="Test Gateway",
            gateway_type="openclaw",
            tenant_id="tenant-456",
            status="active",
            api_key_hash="hashed_key",
            api_secret_hash="hashed_secret",
            configuration={
                "llm": {
                    "provider": "qwen",
                    "model": "qwen-turbo",
                    "api_url": "https://api.qwen.com",
                    "api_key": "qwen-key"
                },
                "language": {
                    "user_language": "zh-CN",
                    "locale": "zh-CN"
                },
                "agent": {
                    "name": "数据助手",
                    "description": "智能数据分析助手"
                },
                "logging": {
                    "level": "info"
                }
            }
        )
        
        # Act
        env_vars = build_environment_vars(gateway)
        
        # Assert
        assert env_vars["TENANT_ID"] == "tenant-456"
        assert env_vars["OPENCLAW_API_KEY"] == "hashed_key"
        assert env_vars["OPENCLAW_LLM_PROVIDER"] == "qwen"
        assert env_vars["OPENCLAW_LLM_MODEL"] == "qwen-turbo"
        assert env_vars["OPENCLAW_LLM_API_URL"] == "https://api.qwen.com"
        assert env_vars["OPENCLAW_LLM_API_KEY"] == "qwen-key"
        assert env_vars["OPENCLAW_USER_LANGUAGE"] == "zh-CN"
        assert env_vars["OPENCLAW_LOCALE"] == "zh-CN"
        assert env_vars["OPENCLAW_AGENT_NAME"] == "数据助手"
        assert env_vars["OPENCLAW_AGENT_DESCRIPTION"] == "智能数据分析助手"
        assert env_vars["OPENCLAW_LOG_LEVEL"] == "info"


class TestWriteEnvFile:
    """Test environment file writing."""
    
    def test_write_env_file(self):
        """Test writing environment variables to file."""
        # Arrange
        env_vars = {
            "TENANT_ID": "tenant-123",
            "OPENCLAW_API_KEY": "key-456"
        }
        
        # Act
        with patch("builtins.open", mock_open()) as mock_file:
            write_env_file(env_vars, ".env.test")
            
            # Assert
            mock_file.assert_called_once_with(".env.test", "w")
            handle = mock_file()
            handle.write.assert_any_call("TENANT_ID=tenant-123\n")
            handle.write.assert_any_call("OPENCLAW_API_KEY=key-456\n")


class TestDeployWithDockerCompose:
    """Test docker-compose deployment."""
    
    @patch("os.path.exists")
    @patch("subprocess.run")
    def test_deploy_success(self, mock_run, mock_exists):
        """Test successful deployment."""
        # Arrange
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0, stdout="Success")
        
        # Act
        result = deploy_with_docker_compose(
            "docker-compose.ai-integration.yml",
            ".env"
        )
        
        # Assert
        assert result is True
        mock_run.assert_called_once()
    
    @patch("os.path.exists")
    def test_deploy_missing_compose_file(self, mock_exists):
        """Test deployment with missing compose file."""
        # Arrange
        mock_exists.return_value = False
        
        # Act
        result = deploy_with_docker_compose(
            "nonexistent.yml",
            ".env"
        )
        
        # Assert
        assert result is False
    
    @patch("os.path.exists")
    @patch("subprocess.run")
    def test_deploy_failure(self, mock_run, mock_exists):
        """Test failed deployment."""
        # Arrange
        mock_exists.return_value = True
        mock_run.side_effect = Exception("Deployment failed")
        
        # Act
        result = deploy_with_docker_compose(
            "docker-compose.ai-integration.yml",
            ".env"
        )
        
        # Assert
        assert result is False


class TestVerifyHealth:
    """Test health check verification."""
    
    @patch("subprocess.run")
    @patch("time.sleep")
    def test_verify_health_success(self, mock_sleep, mock_run):
        """Test successful health check."""
        # Arrange
        mock_run.return_value = Mock(returncode=0)
        
        # Act
        result = verify_health(timeout=10)
        
        # Assert
        assert result is True
    
    @patch("subprocess.run")
    @patch("time.sleep")
    def test_verify_health_timeout(self, mock_sleep, mock_run):
        """Test health check timeout."""
        # Arrange
        mock_run.return_value = Mock(returncode=1)
        
        # Act
        result = verify_health(timeout=1)
        
        # Assert
        assert result is False
    
    @patch("subprocess.run")
    @patch("time.sleep")
    @patch("time.time")
    def test_verify_health_partial_success(self, mock_time, mock_sleep, mock_run):
        """Test health check with only gateway healthy."""
        # Arrange
        # Mock time to simulate timeout
        mock_time.side_effect = [0, 0.1, 0.2, 0.3, 2.0]  # Last call exceeds timeout
        # Gateway succeeds, agent fails repeatedly
        mock_run.side_effect = [
            Mock(returncode=0),  # Gateway health check (success)
            Mock(returncode=1),  # Agent health check (fail)
            Mock(returncode=1),  # Agent health check retry (fail)
            Mock(returncode=1),  # Agent health check retry (fail)
        ]
        
        # Act
        result = verify_health(timeout=1)
        
        # Assert
        assert result is False
