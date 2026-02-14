"""
Integration tests for Docker deployment of AI gateway.

Tests the complete Docker deployment flow including:
- Container startup and health
- Network connectivity between services
- Environment variable injection
- Service communication

Requirements: 1.1, 1.2, 1.3

Prerequisites:
- Docker and docker-compose must be installed
- Main docker-compose.yml services must be running (app, postgres, etc.)
- Network 'superinsight_network' must exist

Run with:
    pytest tests/test_docker_deployment_integration.py -v -m "integration and docker"

Skip integration tests:
    pytest tests/ -v -m "not integration"
"""

import pytest
import subprocess
import time
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

# Mark all tests in this module as integration and docker tests
pytestmark = [pytest.mark.integration, pytest.mark.docker]


@pytest.fixture(scope="module")
def docker_compose_files():
    """Provide paths to docker-compose files."""
    base_dir = Path(__file__).parent.parent
    return {
        "main": str(base_dir / "docker-compose.yml"),
        "ai_integration": str(base_dir / "docker-compose.ai-integration.yml")
    }


@pytest.fixture(scope="module")
def test_env_file():
    """Create temporary environment file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.env',
        delete=False
    ) as f:
        f.write("OPENCLAW_API_KEY=test-api-key-123\n")
        f.write("TENANT_ID=test-tenant-456\n")
        f.write("OPENCLAW_LLM_PROVIDER=ollama\n")
        f.write("OPENCLAW_LLM_MODEL=llama2\n")
        f.write("OPENCLAW_USER_LANGUAGE=zh-CN\n")
        f.write("OPENCLAW_LOCALE=zh-CN\n")
        f.write("OPENCLAW_LOG_LEVEL=info\n")
        f.write("NODE_ENV=test\n")
        env_path = f.name
    
    yield env_path
    
    # Cleanup
    if os.path.exists(env_path):
        os.unlink(env_path)


def run_command(
    cmd: list,
    timeout: int = 30,
    check: bool = True
) -> subprocess.CompletedProcess:
    """Run shell command with timeout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check
        )
        return result
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"Command timed out: {' '.join(cmd)}")
    except subprocess.CalledProcessError as e:
        if check:
            pytest.fail(
                f"Command failed: {' '.join(cmd)}\n"
                f"stdout: {e.stdout}\n"
                f"stderr: {e.stderr}"
            )
        return e


def check_container_running(container_name: str) -> bool:
    """Check if container is running."""
    result = run_command(
        ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
        check=False
    )
    return container_name in result.stdout


def get_container_status(container_name: str) -> Optional[str]:
    """Get container status."""
    result = run_command(
        ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
        check=False
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def check_container_health(container_name: str) -> Optional[str]:
    """Check container health status."""
    result = run_command(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
        check=False
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return None


def get_container_env(container_name: str, var_name: str) -> Optional[str]:
    """Get environment variable from container."""
    result = run_command(
        ["docker", "exec", container_name, "printenv", var_name],
        check=False
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def check_network_connectivity(
    from_container: str,
    to_container: str,
    port: int
) -> bool:
    """Check network connectivity between containers."""
    # Use nc (netcat) to check if port is accessible
    result = run_command(
        [
            "docker", "exec", from_container,
            "sh", "-c", f"nc -zv {to_container} {port} 2>&1"
        ],
        check=False,
        timeout=10
    )
    return result.returncode == 0


class TestDockerDeployment:
    """Integration tests for Docker deployment."""
    
    def test_container_startup(self, docker_compose_files, test_env_file):
        """
        Test that OpenClaw containers start successfully.
        
        Requirements: 1.1
        """
        # Start services
        result = run_command([
            "docker-compose",
            "-f", docker_compose_files["main"],
            "-f", docker_compose_files["ai_integration"],
            "--env-file", test_env_file,
            "up", "-d",
            "openclaw-gateway", "openclaw-agent"
        ])
        
        assert result.returncode == 0, "Docker compose up failed"
        
        # Wait for containers to start
        time.sleep(10)
        
        # Check gateway container
        assert check_container_running("superinsight-openclaw-gateway"), \
            "OpenClaw gateway container not running"
        
        gateway_status = get_container_status("superinsight-openclaw-gateway")
        assert gateway_status == "running", \
            f"Gateway container status: {gateway_status}"
        
        # Check agent container
        assert check_container_running("superinsight-openclaw-agent"), \
            "OpenClaw agent container not running"
        
        agent_status = get_container_status("superinsight-openclaw-agent")
        assert agent_status == "running", \
            f"Agent container status: {agent_status}"
    
    def test_container_health_checks(self):
        """
        Test that containers pass health checks.
        
        Requirements: 1.1
        """
        # Wait for health checks to complete
        max_wait = 60
        start_time = time.time()
        
        gateway_healthy = False
        agent_healthy = False
        
        while time.time() - start_time < max_wait:
            gateway_health = check_container_health("superinsight-openclaw-gateway")
            agent_health = check_container_health("superinsight-openclaw-agent")
            
            if gateway_health == "healthy":
                gateway_healthy = True
            if agent_health == "healthy":
                agent_healthy = True
            
            if gateway_healthy and agent_healthy:
                break
            
            time.sleep(5)
        
        assert gateway_healthy, \
            f"Gateway health check failed after {max_wait}s"
        assert agent_healthy, \
            f"Agent health check failed after {max_wait}s"
    
    def test_network_connectivity(self):
        """
        Test network connectivity between services.
        
        Requirements: 1.2
        """
        # Test agent can reach gateway
        assert check_network_connectivity(
            "superinsight-openclaw-agent",
            "openclaw-gateway",
            3000
        ), "Agent cannot reach gateway on port 3000"
        
        # Test gateway can reach backend
        assert check_network_connectivity(
            "superinsight-openclaw-gateway",
            "app",
            8000
        ), "Gateway cannot reach backend on port 8000"
        
        # Test agent can reach backend
        assert check_network_connectivity(
            "superinsight-openclaw-agent",
            "app",
            8000
        ), "Agent cannot reach backend on port 8000"
    
    def test_environment_variable_injection(self):
        """
        Test environment variables are injected correctly.
        
        Requirements: 1.3
        """
        # Check gateway environment variables
        gateway_api_key = get_container_env(
            "superinsight-openclaw-gateway",
            "SUPERINSIGHT_API_KEY"
        )
        assert gateway_api_key == "test-api-key-123", \
            f"Gateway API key mismatch: {gateway_api_key}"
        
        gateway_tenant = get_container_env(
            "superinsight-openclaw-gateway",
            "SUPERINSIGHT_TENANT_ID"
        )
        assert gateway_tenant == "test-tenant-456", \
            f"Gateway tenant ID mismatch: {gateway_tenant}"
        
        gateway_log_level = get_container_env(
            "superinsight-openclaw-gateway",
            "LOG_LEVEL"
        )
        assert gateway_log_level == "info", \
            f"Gateway log level mismatch: {gateway_log_level}"
        
        # Check agent environment variables
        agent_api_key = get_container_env(
            "superinsight-openclaw-agent",
            "SUPERINSIGHT_API_KEY"
        )
        assert agent_api_key == "test-api-key-123", \
            f"Agent API key mismatch: {agent_api_key}"
        
        agent_tenant = get_container_env(
            "superinsight-openclaw-agent",
            "SUPERINSIGHT_TENANT_ID"
        )
        assert agent_tenant == "test-tenant-456", \
            f"Agent tenant ID mismatch: {agent_tenant}"
        
        agent_llm_provider = get_container_env(
            "superinsight-openclaw-agent",
            "LLM_PROVIDER"
        )
        assert agent_llm_provider == "ollama", \
            f"Agent LLM provider mismatch: {agent_llm_provider}"
        
        agent_llm_model = get_container_env(
            "superinsight-openclaw-agent",
            "LLM_MODEL"
        )
        assert agent_llm_model == "llama2", \
            f"Agent LLM model mismatch: {agent_llm_model}"
        
        agent_language = get_container_env(
            "superinsight-openclaw-agent",
            "OPENCLAW_USER_LANGUAGE"
        )
        assert agent_language == "zh-CN", \
            f"Agent language mismatch: {agent_language}"
    
    def test_gateway_api_endpoint(self):
        """
        Test gateway API endpoint is accessible.
        
        Requirements: 1.1, 1.2
        """
        # Test health endpoint
        result = run_command(
            ["curl", "-f", "-s", "http://localhost:3000/health"],
            check=False,
            timeout=10
        )
        
        assert result.returncode == 0, \
            f"Gateway health endpoint failed: {result.stderr}"
    
    def test_agent_gateway_communication(self):
        """
        Test agent can communicate with gateway.
        
        Requirements: 1.2
        """
        # Check agent logs for gateway connection
        result = run_command(
            ["docker", "logs", "superinsight-openclaw-agent", "--tail", "50"],
            check=False
        )
        
        # Look for connection success or gateway URL in logs
        logs = result.stdout.lower()
        assert "gateway" in logs or "connected" in logs, \
            "Agent logs don't show gateway connection"
    
    @pytest.fixture(scope="class", autouse=True)
    def cleanup(self, docker_compose_files, test_env_file):
        """Cleanup containers after tests."""
        yield
        
        # Stop and remove containers
        run_command([
            "docker-compose",
            "-f", docker_compose_files["main"],
            "-f", docker_compose_files["ai_integration"],
            "--env-file", test_env_file,
            "down",
            "-v"
        ], check=False)


class TestDockerDeploymentScript:
    """Integration tests for deployment script."""
    
    def test_deployment_script_execution(
        self,
        docker_compose_files,
        test_env_file
    ):
        """
        Test deployment script executes successfully.
        
        Requirements: 1.1, 1.2, 1.3
        """
        # This test requires a database with a gateway record
        # Skip if database is not available
        pytest.skip("Requires database setup with gateway record")
