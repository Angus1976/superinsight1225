"""
Deployment tests for SuperInsight Platform.

This module contains tests for:
- Docker container startup tests (test_docker_container_startup.py)
- Docker health check tests (test_docker_health_check.py)
- Network connectivity tests (test_network_connectivity.py)
- Environment variable injection tests (test_environment_variable_injection.py)
- Database migration tests (test_database_migration.py)
- Deployment performance tests (test_deployment_performance.py)

Validates: Requirements 8.1-8.7
Validates: Properties 21, 22
"""

from .test_docker_container_startup import TestDockerContainerStartup
from .test_docker_health_check import TestDockerHealthCheck
from .test_network_connectivity import TestNetworkConnectivity
from .test_environment_variable_injection import TestEnvironmentVariableInjection
from .test_database_migration import TestDatabaseMigration
from .test_deployment_performance import TestDeploymentPerformance

__all__ = [
    "TestDockerContainerStartup",
    "TestDockerHealthCheck",
    "TestNetworkConnectivity",
    "TestEnvironmentVariableInjection",
    "TestDatabaseMigration",
    "TestDeploymentPerformance",
]
