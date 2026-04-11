"""
Docker health check tests for SuperInsight Platform.

Tests verify that all services have working health checks and are responsive.
Validates: Requirements 8.2, 8.6
"""

import os
import time
import pytest
import subprocess
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import socket


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    service: str
    status: HealthStatus
    response_time_ms: float
    error_message: Optional[str] = None
    details: Optional[Dict] = None


class DockerHealthCheckTests:
    """Tests for Docker container health checks."""
    
    # Service health check endpoints and timeouts
    HEALTH_CHECKS = {
        "app": {
            "url": "http://localhost:18080/health",
            "timeout": 10,
            "expected_status": 200,
        },
        "frontend": {
            "url": "http://localhost:15173",
            "timeout": 10,
            "expected_status": 200,
        },
        "postgres": {
            "type": "tcp",
            "port": 5432,
            "timeout": 5,
        },
        "redis": {
            "type": "redis",
            "port": 6379,
            "timeout": 5,
        },
        "label-studio": {
            "url": "http://localhost:8080/health",
            "timeout": 15,
            "expected_status": 200,
        },
        "argilla": {
            "url": "http://localhost:6900",
            "timeout": 15,
            "expected_status": 200,
        },
        "elasticsearch": {
            "url": "http://localhost:9200/_cluster/health",
            "timeout": 15,
            "expected_status": 200,
        },
        "ollama": {
            "url": "http://localhost:11434/api/tags",
            "timeout": 10,
            "expected_status": 200,
        },
        "prometheus": {
            "url": "http://localhost:9090/-/healthy",
            "timeout": 10,
            "expected_status": 200,
        },
        "grafana": {
            "url": "http://localhost:3000/api/health",
            "timeout": 10,
            "expected_status": 200,
        },
    }
    
    def _check_http_health(
        self,
        url: str,
        timeout: int,
        expected_status: int = 200
    ) -> HealthCheckResult:
        """Check HTTP health endpoint."""
        start_time = time.time()
        
        try:
            response = requests.get(url, timeout=timeout)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == expected_status:
                return HealthCheckResult(
                    service=url,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    details={"status_code": response.status_code}
                )
            else:
                return HealthCheckResult(
                    service=url,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    error_message=f"Expected status {expected_status}, got {response.status_code}"
                )
                
        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service=url,
                status=HealthStatus.TIMEOUT,
                response_time_ms=response_time * 1000,
                error_message=f"Request timed out after {timeout} seconds"
            )
        except requests.exceptions.ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service=url,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=f"Connection error: {str(e)}"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service=url,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _check_tcp_health(
        self,
        host: str,
        port: int,
        timeout: int
    ) -> HealthCheckResult:
        """Check TCP port health."""
        start_time = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            response_time = (time.time() - start_time) * 1000
            
            if result == 0:
                return HealthCheckResult(
                    service=f"{host}:{port}",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    service=f"{host}:{port}",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    error_message=f"Port {port} is not reachable"
                )
                
        except socket.timeout:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service=f"{host}:{port}",
                status=HealthStatus.TIMEOUT,
                response_time_ms=response_time * 1000,
                error_message=f"Connection timed out after {timeout} seconds"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service=f"{host}:{port}",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=f"Socket error: {str(e)}"
            )
    
    def _check_redis_health(
        self,
        host: str,
        port: int,
        timeout: int
    ) -> HealthCheckResult:
        """Check Redis health using PING command."""
        start_time = time.time()
        
        try:
            import redis
            client = redis.Redis(host=host, port=port, socket_timeout=timeout)
            response = client.ping()
            response_time = (time.time() - start_time) * 1000
            
            if response:
                return HealthCheckResult(
                    service=f"redis://{host}:{port}",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    service=f"redis://{host}:{port}",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    error_message="Redis PING returned False"
                )
                
        except redis.exceptions.ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service=f"redis://{host}:{port}",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=f"Redis connection error: {str(e)}"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service=f"redis://{host}:{port}",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    @pytest.fixture
    def docker_compose_file(self) -> str:
        """Path to docker-compose.yml file."""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "docker-compose.yml"
        )
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_backend_health_endpoint(self):
        """Test backend application health endpoint."""
        result = self._check_http_health(
            url="http://localhost:18080/health",
            timeout=10,
            expected_status=200
        )
        
        assert result.status == HealthStatus.HEALTHY, \
            f"Backend health check failed: {result.error_message}"
        assert result.response_time_ms < 5000, \
            f"Backend health check took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_frontend_health_endpoint(self):
        """Test frontend health endpoint."""
        result = self._check_http_health(
            url="http://localhost:15173",
            timeout=10,
            expected_status=200
        )
        
        assert result.status == HealthStatus.HEALTHY, \
            f"Frontend health check failed: {result.error_message}"
        assert result.response_time_ms < 5000, \
            f"Frontend health check took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_postgres_tcp_health(self):
        """Test PostgreSQL TCP port health."""
        result = self._check_tcp_health(
            host="localhost",
            port=5432,
            timeout=5
        )
        
        assert result.status == HealthStatus.HEALTHY, \
            f"PostgreSQL health check failed: {result.error_message}"
        assert result.response_time_ms < 3000, \
            f"PostgreSQL health check took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_redis_health(self):
        """Test Redis health using PING."""
        result = self._check_redis_health(
            host="localhost",
            port=6379,
            timeout=5
        )
        
        assert result.status == HealthStatus.HEALTHY, \
            f"Redis health check failed: {result.error_message}"
        assert result.response_time_ms < 2000, \
            f"Redis health check took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_label_studio_health_endpoint(self):
        """Test Label Studio health endpoint."""
        result = self._check_http_health(
            url="http://localhost:8080/health",
            timeout=15,
            expected_status=200
        )
        
        assert result.status == HealthStatus.HEALTHY, \
            f"Label Studio health check failed: {result.error_message}"
        assert result.response_time_ms < 10000, \
            f"Label Studio health check took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_argilla_health_endpoint(self):
        """Test Argilla health endpoint."""
        result = self._check_http_health(
            url="http://localhost:6900",
            timeout=15,
            expected_status=200
        )
        
        assert result.status == HealthStatus.HEALTHY, \
            f"Argilla health check failed: {result.error_message}"
        assert result.response_time_ms < 10000, \
            f"Argilla health check took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_elasticsearch_health_endpoint(self):
        """Test Elasticsearch cluster health endpoint."""
        result = self._check_http_health(
            url="http://localhost:9200/_cluster/health",
            timeout=15,
            expected_status=200
        )
        
        assert result.status == HealthStatus.HEALTHY, \
            f"Elasticsearch health check failed: {result.error_message}"
        assert result.response_time_ms < 10000, \
            f"Elasticsearch health check took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_ollama_health_endpoint(self):
        """Test Ollama health endpoint."""
        result = self._check_http_health(
            url="http://localhost:11434/api/tags",
            timeout=10,
            expected_status=200
        )
        
        assert result.status == HealthStatus.HEALTHY, \
            f"Ollama health check failed: {result.error_message}"
        assert result.response_time_ms < 8000, \
            f"Ollama health check took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_all_services_health_checks(self):
        """Test all services have passing health checks."""
        results = []
        
        # HTTP health checks
        http_services = [
            ("app", "http://localhost:18080/health", 10, 200),
            ("frontend", "http://localhost:15173", 10, 200),
            ("label-studio", "http://localhost:8080/health", 15, 200),
            ("argilla", "http://localhost:6900", 15, 200),
            ("elasticsearch", "http://localhost:9200/_cluster/health", 15, 200),
            ("ollama", "http://localhost:11434/api/tags", 10, 200),
            ("prometheus", "http://localhost:9090/-/healthy", 10, 200),
            ("grafana", "http://localhost:3000/api/health", 10, 200),
        ]
        
        for service_name, url, timeout, expected_status in http_services:
            result = self._check_http_health(url, timeout, expected_status)
            results.append((service_name, result))
        
        # TCP health checks
        tcp_services = [
            ("postgres", "localhost", 5432, 5),
            ("redis", "localhost", 6379, 5),
        ]
        
        for service_name, host, port, timeout in tcp_services:
            result = self._check_tcp_health(host, port, timeout)
            results.append((service_name, result))
        
        # Check results
        failed_services = []
        for service_name, result in results:
            if result.status != HealthStatus.HEALTHY:
                failed_services.append({
                    "service": service_name,
                    "status": result.status.value,
                    "error": result.error_message
                })
        
        assert len(failed_services) == 0, \
            f"Services with failed health checks: {failed_services}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_health_check_timeouts(self):
        """Test that health checks respect timeout limits."""
        # Test with a very short timeout to verify timeout handling
        result = self._check_http_health(
            url="http://localhost:18080/health",
            timeout=1,  # Very short timeout
            expected_status=200
        )
        
        # Should either succeed quickly or timeout gracefully
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.TIMEOUT], \
            f"Unexpected health check status: {result.status}"
        
        # If it timed out, it should be within reasonable bounds
        if result.status == HealthStatus.TIMEOUT:
            assert result.response_time_ms < 5000, \
                f"Timeout took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_docker_health_check_configured(self, docker_compose_file: str):
        """Verify health checks are configured in docker-compose.yml."""
        import yaml
        
        with open(docker_compose_file, 'r') as f:
            config = yaml.safe_load(f)
        
        services = config.get("services", {})
        
        # Check that services have healthcheck configured
        services_with_healthcheck = []
        for service_name, service_config in services.items():
            if "healthcheck" in service_config:
                services_with_healthcheck.append(service_name)
        
        # At least core services should have health checks
        core_services = ["app", "frontend", "postgres", "redis"]
        missing_healthchecks = [
            s for s in core_services 
            if s not in services_with_healthcheck
        ]
        
        assert len(missing_healthchecks) == 0, \
            f"Core services missing healthcheck: {missing_healthchecks}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.health
    def test_container_health_status_from_docker(self):
        """Verify container health status from Docker inspect."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", 
                 "{{.State.Health.Status}}", "superinsight-app"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                health_status = result.stdout.strip()
                assert health_status in ["healthy", "starting"], \
                    f"Container health status is '{health_status}', expected 'healthy' or 'starting'"
            else:
                # Container might not have a health check configured
                pytest.skip("Container health check not configured")
                
        except subprocess.TimeoutExpired:
            pytest.fail("Docker inspect command timed out")
        except FileNotFoundError:
            pytest.skip("Docker not found - skipping health check tests")


class TestDockerHealthCheck(DockerHealthCheckTests):
    """Pytest-compatible test class for Docker health check tests."""
    pass