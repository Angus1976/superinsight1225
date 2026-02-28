"""
Docker container startup tests for SuperInsight Platform.

Tests verify that all Docker containers start successfully and are healthy.
Validates: Requirements 8.1, 8.2, 8.6
"""

import os
import time
import pytest
import subprocess
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ServiceStatus(Enum):
    """Status of a service container."""
    RUNNING = "running"
    STOPPED = "stopped"
    UNHEALTHY = "unhealthy"
    NOT_FOUND = "not_found"


@dataclass
class ContainerInfo:
    """Information about a Docker container."""
    name: str
    status: ServiceStatus
    image: str
    health_check: Optional[str] = None
    ports: Dict[str, str] = None
    uptime_seconds: float = 0.0


class DockerContainerStartupTests:
    """Tests for Docker container startup and health verification."""
    
    # Services to test (matches docker-compose.yml)
    REQUIRED_SERVICES = [
        "superinsight-app",
        "superinsight-frontend",
        "superinsight-postgres",
        "superinsight-redis",
        "superinsight-label-studio",
        "superinsight-argilla",
        "superinsight-elasticsearch",
        "superinsight-ollama",
    ]
    
    OPTIONAL_SERVICES = [
        "superinsight-prometheus",
        "superinsight-grafana",
    ]
    
    @pytest.fixture
    def docker_compose_file(self) -> str:
        """Path to docker-compose.yml file."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "docker-compose.yml"
        )
    
    @pytest.fixture
    def docker_project_name(self) -> str:
        """Docker compose project name."""
        return "superinsight"
    
    def _run_docker_compose_command(
        self,
        command: List[str],
        timeout: int = 60
    ) -> subprocess.CompletedProcess:
        """Run a docker-compose command and return the result."""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.yml", "-p", "superinsight"] + command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            raise AssertionError(f"Command timed out after {timeout} seconds")
        except FileNotFoundError:
            pytest.skip("docker-compose not found - skipping Docker tests")
    
    def _get_container_status(self, container_name: str) -> ContainerInfo:
        """Get the status of a specific container."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", 
                 "{{.State.Status}}|{{.Config.Image}}|{{.State.StartedAt}}", 
                 container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return ContainerInfo(
                    name=container_name,
                    status=ServiceStatus.NOT_FOUND,
                    image="",
                    ports={}
                )
            
            output = result.stdout.strip()
            parts = output.split("|")
            status_str = parts[0] if parts else "unknown"
            image = parts[1] if len(parts) > 1 else ""
            
            # Map status string to enum
            status_map = {
                "running": ServiceStatus.RUNNING,
                "exited": ServiceStatus.STOPPED,
                "created": ServiceStatus.STOPPED,
            }
            status = status_map.get(status_str, ServiceStatus.UNHEALTHY)
            
            return ContainerInfo(
                name=container_name,
                status=status,
                image=image,
                ports={}
            )
        except subprocess.TimeoutExpired:
            return ContainerInfo(
                name=container_name,
                status=ServiceStatus.UNHEALTHY,
                image="",
                ports={}
            )
        except FileNotFoundError:
            pytest.skip("Docker not found - skipping container tests")
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_docker_compose_file_exists(self, docker_compose_file: str):
        """Verify docker-compose.yml configuration file exists."""
        assert os.path.exists(docker_compose_file), \
            f"docker-compose.yml not found at {docker_compose_file}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_docker_compose_file_is_valid(self, docker_compose_file: str):
        """Verify docker-compose.yml is valid YAML."""
        import yaml
        try:
            with open(docker_compose_file, 'r') as f:
                config = yaml.safe_load(f)
            assert config is not None, "docker-compose.yml is empty"
            assert "services" in config, "docker-compose.yml has no services section"
        except yaml.YAMLError as e:
            pytest.fail(f"docker-compose.yml is not valid YAML: {e}")
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_all_required_services_defined(self, docker_compose_file: str):
        """Verify all required services are defined in docker-compose.yml."""
        import yaml
        with open(docker_compose_file, 'r') as f:
            config = yaml.safe_load(f)
        
        services = list(config.get("services", {}).keys())
        
        for service in self.REQUIRED_SERVICES:
            assert service in services, \
                f"Required service '{service}' not defined in docker-compose.yml"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_backend_container_starts(self):
        """Test that backend application container starts successfully."""
        container_info = self._get_container_status("superinsight-app")
        
        assert container_info.status == ServiceStatus.RUNNING, \
            f"Backend container is not running. Status: {container_info.status}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_frontend_container_starts(self):
        """Test that frontend container starts successfully."""
        container_info = self._get_container_status("superinsight-frontend")
        
        assert container_info.status == ServiceStatus.RUNNING, \
            f"Frontend container is not running. Status: {container_info.status}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_database_container_starts(self):
        """Test that PostgreSQL database container starts successfully."""
        container_info = self._get_container_status("superinsight-postgres")
        
        assert container_info.status == ServiceStatus.RUNNING, \
            f"Database container is not running. Status: {container_info.status}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_redis_container_starts(self):
        """Test that Redis container starts successfully."""
        container_info = self._get_container_status("superinsight-redis")
        
        assert container_info.status == ServiceStatus.RUNNING, \
            f"Redis container is not running. Status: {container_info.status}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_label_studio_container_starts(self):
        """Test that Label Studio container starts successfully."""
        container_info = self._get_container_status("superinsight-label-studio")
        
        assert container_info.status == ServiceStatus.RUNNING, \
            f"Label Studio container is not running. Status: {container_info.status}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_argilla_container_starts(self):
        """Test that Argilla container starts successfully."""
        container_info = self._get_container_status("superinsight-argilla")
        
        assert container_info.status == ServiceStatus.RUNNING, \
            f"Argilla container is not running. Status: {container_info.status}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_elasticsearch_container_starts(self):
        """Test that Elasticsearch container starts successfully."""
        container_info = self._get_container_status("superinsight-elasticsearch")
        
        assert container_info.status == ServiceStatus.RUNNING, \
            f"Elasticsearch container is not running. Status: {container_info.status}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_ollama_container_starts(self):
        """Test that Ollama container starts successfully."""
        container_info = self._get_container_status("superinsight-ollama")
        
        assert container_info.status == ServiceStatus.RUNNING, \
            f"Ollama container is not running. Status: {container_info.status}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_all_required_containers_running(self):
        """Test that all required containers are running."""
        failed_containers = []
        
        for service in self.REQUIRED_SERVICES:
            container_info = self._get_container_status(service)
            if container_info.status != ServiceStatus.RUNNING:
                failed_containers.append({
                    "name": service,
                    "status": container_info.status.value
                })
        
        assert len(failed_containers) == 0, \
            f"Containers not running: {failed_containers}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_container_dependencies_satisfied(self):
        """Test that container dependencies are properly configured."""
        import yaml
        
        docker_compose_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "docker-compose.yml"
        )
        
        with open(docker_compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        services = config.get("services", {})
        
        # Check that app depends on postgres and redis
        app_service = services.get("app", {})
        depends_on = app_service.get("depends_on", [])
        
        assert "postgres" in depends_on, \
            "App service should depend on postgres"
        assert "redis" in depends_on, \
            "App service should depend on redis"
        
        # Check that frontend depends on app
        frontend_service = services.get("frontend", {})
        frontend_depends_on = frontend_service.get("depends_on", [])
        
        assert "app" in frontend_depends_on, \
            "Frontend service should depend on app"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    def test_container_ports_configured(self):
        """Test that required ports are configured for services."""
        import yaml
        
        docker_compose_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "docker-compose.yml"
        )
        
        with open(docker_compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        services = config.get("services", {})
        
        # Check app port
        app_ports = services.get("app", {}).get("ports", [])
        assert "8000:8000" in app_ports, \
            "App service should expose port 8000"
        
        # Check frontend port
        frontend_ports = services.get("frontend", {}).get("ports", [])
        assert "5173:5173" in frontend_ports, \
            "Frontend service should expose port 5173"
        
        # Check postgres port
        postgres_ports = services.get("postgres", {}).get("ports", [])
        assert "5432:5432" in postgres_ports, \
            "Postgres service should expose port 5432"
        
        # Check redis port
        redis_ports = services.get("redis", {}).get("ports", [])
        assert "6379:6379" in redis_ports, \
            "Redis service should expose port 6379"


class TestDockerContainerStartup(DockerContainerStartupTests):
    """Pytest-compatible test class for Docker container startup tests."""
    pass