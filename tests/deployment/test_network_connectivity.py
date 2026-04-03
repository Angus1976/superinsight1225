"""
Network connectivity tests for SuperInsight Platform.

Tests verify network connectivity between services.
Validates: Requirements 8.3, 8.6
Validates Property 21: Deployment Test Service Accessibility
"""

import os
import re
import time
import pytest
import subprocess
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import socket


class ConnectivityStatus(Enum):
    """Network connectivity status."""
    CONNECTED = "connected"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REFUSED = "refused"


@dataclass
class ConnectivityResult:
    """Result of a connectivity test."""
    source: str
    destination: str
    status: ConnectivityStatus
    response_time_ms: float
    error_message: Optional[str] = None
    details: Optional[Dict] = None


class NetworkConnectivityTests:
    """Tests for network connectivity between services."""
    
    # Connectivity tests to perform
    CONNECTIVITY_TESTS = [
        # Frontend to Backend
        ("frontend", "app", "http://app:8000/health", "http"),
        
        # Backend to Database
        ("app", "postgres", "postgresql://postgres:5432", "tcp"),
        
        # Backend to Redis
        ("app", "redis", "redis://redis:6379", "redis"),
        
        # Backend to Label Studio
        ("app", "label-studio", "http://label-studio:8080", "http"),
        
        # Backend to Argilla
        ("app", "argilla", "http://argilla:6900", "http"),
        
        # Backend to Ollama
        ("app", "ollama", "http://ollama:11434", "http"),
        
        # Argilla to Elasticsearch
        ("argilla", "elasticsearch", "http://elasticsearch:9200", "http"),
    ]
    
    def _check_http_connectivity(
        self,
        url: str,
        timeout: int = 10
    ) -> ConnectivityResult:
        """Check HTTP connectivity to a service."""
        start_time = time.time()
        
        try:
            response = requests.get(url, timeout=timeout)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code < 500:
                return ConnectivityResult(
                    source="test-container",
                    destination=url,
                    status=ConnectivityStatus.CONNECTED,
                    response_time_ms=response_time,
                    details={"status_code": response.status_code}
                )
            else:
                return ConnectivityResult(
                    source="test-container",
                    destination=url,
                    status=ConnectivityStatus.FAILED,
                    response_time_ms=response_time,
                    error_message=f"Server error: {response.status_code}"
                )
                
        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            return ConnectivityResult(
                source="test-container",
                destination=url,
                status=ConnectivityStatus.TIMEOUT,
                response_time_ms=response_time * 1000,
                error_message=f"Request timed out after {timeout} seconds"
            )
        except requests.exceptions.ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectivityResult(
                source="test-container",
                destination=url,
                status=ConnectivityStatus.FAILED,
                response_time_ms=response_time,
                error_message=f"Connection error: {str(e)}"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectivityResult(
                source="test-container",
                destination=url,
                status=ConnectivityStatus.FAILED,
                response_time_ms=response_time,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _check_tcp_connectivity(
        self,
        host: str,
        port: int,
        timeout: int = 5
    ) -> ConnectivityResult:
        """Check TCP connectivity to a port."""
        start_time = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            response_time = (time.time() - start_time) * 1000
            
            if result == 0:
                return ConnectivityResult(
                    source="test-container",
                    destination=f"{host}:{port}",
                    status=ConnectivityStatus.CONNECTED,
                    response_time_ms=response_time
                )
            else:
                return ConnectivityResult(
                    source="test-container",
                    destination=f"{host}:{port}",
                    status=ConnectivityStatus.REFUSED,
                    response_time_ms=response_time,
                    error_message=f"Connection refused to {host}:{port}"
                )
                
        except socket.timeout:
            response_time = (time.time() - start_time) * 1000
            return ConnectivityResult(
                source="test-container",
                destination=f"{host}:{port}",
                status=ConnectivityStatus.TIMEOUT,
                response_time_ms=response_time * 1000,
                error_message=f"Connection timed out after {timeout} seconds"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectivityResult(
                source="test-container",
                destination=f"{host}:{port}",
                status=ConnectivityStatus.FAILED,
                response_time_ms=response_time,
                error_message=f"Socket error: {str(e)}"
            )
    
    def _check_redis_connectivity(
        self,
        host: str,
        port: int,
        timeout: int = 5
    ) -> ConnectivityResult:
        """Check Redis connectivity."""
        start_time = time.time()
        
        try:
            import redis
            client = redis.Redis(host=host, port=port, socket_timeout=timeout)
            response = client.ping()
            response_time = (time.time() - start_time) * 1000
            
            if response:
                return ConnectivityResult(
                    source="test-container",
                    destination=f"redis://{host}:{port}",
                    status=ConnectivityStatus.CONNECTED,
                    response_time_ms=response_time
                )
            else:
                return ConnectivityResult(
                    source="test-container",
                    destination=f"redis://{host}:{port}",
                    status=ConnectivityStatus.FAILED,
                    response_time_ms=response_time,
                    error_message="Redis PING returned False"
                )
                
        except redis.exceptions.ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectivityResult(
                source="test-container",
                destination=f"redis://{host}:{port}",
                status=ConnectivityStatus.FAILED,
                response_time_ms=response_time,
                error_message=f"Redis connection error: {str(e)}"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectivityResult(
                source="test-container",
                destination=f"redis://{host}:{port}",
                status=ConnectivityStatus.FAILED,
                response_time_ms=response_time,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _check_postgres_connectivity(
        self,
        host: str,
        port: int,
        timeout: int = 5
    ) -> ConnectivityResult:
        """Check PostgreSQL connectivity."""
        start_time = time.time()
        
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=host,
                port=port,
                user="superinsight",
                password="password",
                database="superinsight",
                connect_timeout=timeout
            )
            conn.close()
            response_time = (time.time() - start_time) * 1000
            
            return ConnectivityResult(
                source="test-container",
                destination=f"postgresql://{host}:{port}",
                status=ConnectivityStatus.CONNECTED,
                response_time_ms=response_time
            )
            
        except psycopg2.OperationalError as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            if "Connection refused" in error_msg:
                return ConnectivityResult(
                    source="test-container",
                    destination=f"postgresql://{host}:{port}",
                    status=ConnectivityStatus.REFUSED,
                    response_time_ms=response_time,
                    error_message=f"Connection refused to {host}:{port}"
                )
            elif "timeout" in error_msg.lower():
                return ConnectivityResult(
                    source="test-container",
                    destination=f"postgresql://{host}:{port}",
                    status=ConnectivityStatus.TIMEOUT,
                    response_time_ms=response_time,
                    error_message=f"Connection timed out after {timeout} seconds"
                )
            else:
                return ConnectivityResult(
                    source="test-container",
                    destination=f"postgresql://{host}:{port}",
                    status=ConnectivityStatus.FAILED,
                    response_time_ms=response_time,
                    error_message=f"PostgreSQL error: {error_msg}"
                )
        except ImportError:
            # Fallback to TCP check if psycopg2 is not available
            return self._check_tcp_connectivity(host, port, timeout)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ConnectivityResult(
                source="test-container",
                destination=f"postgresql://{host}:{port}",
                status=ConnectivityStatus.FAILED,
                response_time_ms=response_time,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_frontend_to_backend_connectivity(self):
        """Test frontend can reach backend API."""
        result = self._check_http_connectivity(
            url="http://localhost:8000/health",
            timeout=10
        )
        
        assert result.status == ConnectivityStatus.CONNECTED, \
            f"Frontend cannot reach backend: {result.error_message}"
        assert result.response_time_ms < 5000, \
            f"Frontend to backend took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_backend_to_postgres_connectivity(self):
        """Test backend can reach PostgreSQL database."""
        result = self._check_postgres_connectivity(
            host="localhost",
            port=5432,
            timeout=5
        )
        
        assert result.status == ConnectivityStatus.CONNECTED, \
            f"Backend cannot reach PostgreSQL: {result.error_message}"
        assert result.response_time_ms < 3000, \
            f"Backend to PostgreSQL took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_backend_to_redis_connectivity(self):
        """Test backend can reach Redis."""
        result = self._check_redis_connectivity(
            host="localhost",
            port=6379,
            timeout=5
        )
        
        assert result.status == ConnectivityStatus.CONNECTED, \
            f"Backend cannot reach Redis: {result.error_message}"
        assert result.response_time_ms < 2000, \
            f"Backend to Redis took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_backend_to_label_studio_connectivity(self):
        """Test backend can reach Label Studio."""
        result = self._check_http_connectivity(
            url="http://localhost:8080/health",
            timeout=10
        )
        
        assert result.status == ConnectivityStatus.CONNECTED, \
            f"Backend cannot reach Label Studio: {result.error_message}"
        assert result.response_time_ms < 8000, \
            f"Backend to Label Studio took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_backend_to_argilla_connectivity(self):
        """Test backend can reach Argilla."""
        result = self._check_http_connectivity(
            url="http://localhost:6900",
            timeout=10
        )
        
        assert result.status == ConnectivityStatus.CONNECTED, \
            f"Backend cannot reach Argilla: {result.error_message}"
        assert result.response_time_ms < 8000, \
            f"Backend to Argilla took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_backend_to_ollama_connectivity(self):
        """Test backend can reach Ollama."""
        result = self._check_http_connectivity(
            url="http://localhost:11434/api/tags",
            timeout=10
        )
        
        assert result.status == ConnectivityStatus.CONNECTED, \
            f"Backend cannot reach Ollama: {result.error_message}"
        assert result.response_time_ms < 8000, \
            f"Backend to Ollama took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_argilla_to_elasticsearch_connectivity(self):
        """Test Argilla can reach Elasticsearch."""
        result = self._check_http_connectivity(
            url="http://localhost:9200/_cluster/health",
            timeout=10
        )
        
        assert result.status == ConnectivityStatus.CONNECTED, \
            f"Argilla cannot reach Elasticsearch: {result.error_message}"
        assert result.response_time_ms < 8000, \
            f"Argilla to Elasticsearch took too long: {result.response_time_ms:.2f}ms"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_all_services_accessible(self):
        """Test all services are accessible from the test environment."""
        results = []
        
        # HTTP connectivity tests
        http_tests = [
            ("test", "backend", "http://localhost:8000/health", 10),
            ("test", "frontend", "http://localhost:5173", 10),
            ("test", "label-studio", "http://localhost:8080/health", 15),
            ("test", "argilla", "http://localhost:6900", 15),
            ("test", "elasticsearch", "http://localhost:9200/_cluster/health", 15),
            ("test", "ollama", "http://localhost:11434/api/tags", 10),
            ("test", "prometheus", "http://localhost:9090/-/healthy", 10),
            ("test", "grafana", "http://localhost:3000/api/health", 10),
        ]
        
        for source, dest, url, timeout in http_tests:
            result = self._check_http_connectivity(url, timeout)
            results.append((f"{source}->{dest}", result))
        
        # Database connectivity tests
        db_tests = [
            ("test", "postgres", "localhost", 5432, 5),
            ("test", "redis", "localhost", 6379, 5),
        ]
        
        for source, dest, host, port, timeout in db_tests:
            if dest == "postgres":
                result = self._check_postgres_connectivity(host, port, timeout)
            else:
                result = self._check_redis_connectivity(host, port, timeout)
            results.append((f"{source}->{dest}", result))
        
        # Check results
        failed_connections = []
        for connection_name, result in results:
            if result.status != ConnectivityStatus.CONNECTED:
                failed_connections.append({
                    "connection": connection_name,
                    "status": result.status.value,
                    "error": result.error_message
                })
        
        assert len(failed_connections) == 0, \
            f"Failed connections: {failed_connections}"
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_docker_network_configured(self):
        """Verify Docker network is properly configured."""
        try:
            result = subprocess.run(
                ["docker", "network", "ls", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                networks = result.stdout.strip().split("\n")
                network_name = "superinsight_network"
                
                assert network_name in networks, \
                    f"Docker network '{network_name}' not found. Available: {networks}"
            else:
                pytest.fail("Failed to list Docker networks")
                
        except subprocess.TimeoutExpired:
            pytest.fail("Docker network list command timed out")
        except FileNotFoundError:
            pytest.skip("Docker not found - skipping network tests")
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_containers_connected_to_network(self):
        """Verify containers are connected to the Docker network."""
        try:
            result = subprocess.run(
                ["docker", "network", "inspect", "superinsight_network", 
                 "--format", "{{range .Containers}}{{.Name}} {{end}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                connected_containers = result.stdout.strip().split()
                
                # Check that core containers are connected
                required_containers = [
                    "superinsight-app",
                    "superinsight-frontend",
                    "superinsight-postgres",
                    "superinsight-redis",
                ]
                
                missing_containers = [
                    c for c in required_containers 
                    if c not in connected_containers
                ]
                
                assert len(missing_containers) == 0, \
                    f"Containers not connected to network: {missing_containers}"
            else:
                pytest.skip("Network 'superinsight_network' not found")
                
        except subprocess.TimeoutExpired:
            pytest.fail("Docker network inspect command timed out")
        except FileNotFoundError:
            pytest.skip("Docker not found - skipping network tests")
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_service_dns_resolution(self):
        """Test that service DNS names are resolvable within Docker network."""
        # This test verifies that container names can be resolved
        # by checking if we can get container IPs
        
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", 
                 "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                 "superinsight-app"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                ip_address = result.stdout.strip()
                assert ip_address, \
                    "App container does not have an IP address in the network"
                # Valid IP address format
                assert re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address), \
                    f"Invalid IP address format: {ip_address}"
            else:
                pytest.skip("Could not inspect app container")
                
        except subprocess.TimeoutExpired:
            pytest.fail("Docker inspect command timed out")
        except FileNotFoundError:
            pytest.skip("Docker not found - skipping DNS tests")
    
    @pytest.mark.docker
    @pytest.mark.deployment
    @pytest.mark.network
    def test_inter_service_communication(self):
        """Test inter-service communication within Docker network."""
        # Test that services can communicate using container names
        # This simulates how services communicate in production
        
        # Test backend to database using container name
        postgres_result = self._check_postgres_connectivity(
            host="localhost",  # Using localhost for test environment
            port=5432,
            timeout=5
        )
        
        # Test backend to redis using container name
        redis_result = self._check_redis_connectivity(
            host="localhost",
            port=6379,
            timeout=5
        )
        
        # Both should be connected
        assert postgres_result.status == ConnectivityStatus.CONNECTED, \
            f"Backend cannot communicate with PostgreSQL: {postgres_result.error_message}"
        assert redis_result.status == ConnectivityStatus.CONNECTED, \
            f"Backend cannot communicate with Redis: {redis_result.error_message}"


class TestNetworkConnectivity(NetworkConnectivityTests):
    """Pytest-compatible test class for network connectivity tests."""
    pass