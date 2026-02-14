# Docker Integration Tests

## Overview

The Docker integration tests (`test_docker_deployment_integration.py`) verify the complete Docker deployment flow for the AI Application Integration system, including OpenClaw gateway and agent containers.

## Prerequisites

### Required Software
- Docker (version 20.10+)
- docker-compose (version 1.29+)
- curl (for health checks)
- nc (netcat, for network connectivity tests)

### Required Services
Before running the integration tests, ensure the main SuperInsight services are running:

```bash
# Start main services
docker-compose up -d

# Verify network exists
docker network ls | grep superinsight_network
```

### Environment Setup
The tests use a temporary environment file, but you can also test with a real `.env` file:

```bash
# Copy example environment file
cp .env.ai-integration.example .env

# Edit with your values
OPENCLAW_API_KEY=your-api-key-here
TENANT_ID=your-tenant-id-here
```

## Running the Tests

### Run All Integration Tests
```bash
pytest tests/test_docker_deployment_integration.py -v
```

### Run Specific Test
```bash
pytest tests/test_docker_deployment_integration.py::TestDockerDeployment::test_container_startup -v
```

### Skip Integration Tests
```bash
# Run all tests except integration tests
pytest tests/ -v -m "not integration"
```

### Run Only Docker Tests
```bash
pytest tests/ -v -m "docker"
```

## Test Coverage

### Test 1: Container Startup
**Requirement**: 1.1

Tests that OpenClaw gateway and agent containers start successfully:
- Containers are created
- Containers reach "running" status
- No immediate crashes

### Test 2: Container Health Checks
**Requirement**: 1.1

Tests that containers pass their health checks:
- Gateway health endpoint responds
- Agent health endpoint responds
- Health checks complete within timeout (60s)

### Test 3: Network Connectivity
**Requirement**: 1.2

Tests network connectivity between services:
- Agent can reach gateway on port 3000
- Gateway can reach backend on port 8000
- Agent can reach backend on port 8000

### Test 4: Environment Variable Injection
**Requirement**: 1.3

Tests that environment variables are injected correctly:
- Gateway receives API key and tenant ID
- Agent receives API key, tenant ID, and LLM config
- Language settings are configured
- Logging level is set

### Test 5: Gateway API Endpoint
**Requirements**: 1.1, 1.2

Tests that gateway API is accessible:
- Health endpoint responds on localhost:3000
- HTTP status is 200

### Test 6: Agent-Gateway Communication
**Requirement**: 1.2

Tests that agent can communicate with gateway:
- Agent logs show gateway connection
- No connection errors in logs

## Troubleshooting

### Docker Not Running
```
Error: Cannot connect to the Docker daemon
```

**Solution**: Start Docker Desktop or Docker daemon

### Network Not Found
```
Error: network superinsight_network not found
```

**Solution**: Create the network or start main services
```bash
docker network create superinsight_network
# OR
docker-compose up -d
```

### Port Already in Use
```
Error: port 3000 is already allocated
```

**Solution**: Stop conflicting services or change port in docker-compose.ai-integration.yml

### Health Check Timeout
```
AssertionError: Gateway health check failed after 60s
```

**Possible causes**:
- Container is still starting (increase timeout)
- Container crashed (check logs: `docker logs superinsight-openclaw-gateway`)
- Health endpoint not implemented in image
- Network connectivity issues

**Debug**:
```bash
# Check container status
docker ps -a | grep openclaw

# Check container logs
docker logs superinsight-openclaw-gateway
docker logs superinsight-openclaw-agent

# Check health status
docker inspect superinsight-openclaw-gateway | grep -A 10 Health
```

### Environment Variables Not Set
```
AssertionError: Gateway API key mismatch: None
```

**Solution**: Verify environment file is being used
```bash
# Check environment variables in container
docker exec superinsight-openclaw-gateway printenv | grep SUPERINSIGHT
```

## Cleanup

The tests automatically clean up containers after running. To manually clean up:

```bash
# Stop and remove containers
docker-compose -f docker-compose.yml -f docker-compose.ai-integration.yml down -v

# Remove volumes
docker volume rm openclaw_config openclaw_skills openclaw_memory openclaw_logs
```

## CI/CD Integration

For CI/CD pipelines, you may want to skip integration tests by default:

```yaml
# .github/workflows/test.yml
- name: Run unit tests
  run: pytest tests/ -v -m "not integration"

- name: Run integration tests
  run: pytest tests/ -v -m "integration"
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

## Notes

- Integration tests take 60-90 seconds to complete
- Tests require actual Docker infrastructure (not mocked)
- Tests are marked with `@pytest.mark.integration` and `@pytest.mark.docker`
- Tests use temporary environment files to avoid conflicts
- Containers are automatically cleaned up after tests
