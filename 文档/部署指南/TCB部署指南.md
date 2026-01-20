# TCB Full-Stack Deployment Guide

This guide covers deploying SuperInsight to Tencent Cloud Base (TCB) using the full-stack container approach.

## Overview

The TCB deployment packages all SuperInsight components into a single container:
- FastAPI backend (SuperInsight API)
- PostgreSQL database
- Redis cache
- Label Studio annotation engine
- Nginx reverse proxy

## Prerequisites

### Required Tools
- Docker 20.10+
- TCB CLI (`npm install -g @cloudbase/cli`)
- Python 3.9+
- Node.js 18+

### TCB Account Setup
1. Create a TCB environment at [console.cloud.tencent.com/tcb](https://console.cloud.tencent.com/tcb)
2. Note your `ENV_ID` from the environment overview
3. Generate API credentials (SecretId and SecretKey)

## Quick Start

### 1. Configure Environment

```bash
# Copy environment template
cp .env.example .env.tcb

# Edit with your TCB credentials
vim .env.tcb
```

Required environment variables:
```bash
TCB_ENV_ID=your-env-id
TCB_SECRET_ID=your-secret-id
TCB_SECRET_KEY=your-secret-key
TCB_REGION=ap-shanghai

POSTGRES_PASSWORD=secure-password
SECRET_KEY=your-app-secret
JWT_SECRET_KEY=your-jwt-secret
```

### 2. Build Container

```bash
# Build the full-stack container
docker build -f deploy/tcb/Dockerfile.fullstack -t superinsight-fullstack:latest .

# Test locally
docker run -p 8000:8000 -p 8080:8080 superinsight-fullstack:latest
```

### 3. Deploy to TCB

```bash
# Login to TCB
tcb login

# Deploy using the script
./scripts/deploy-tcb.sh production

# Or deploy manually
tcb framework deploy -e your-env-id
```

## Configuration

### Environment-Specific Settings

The deployment supports multiple environments:

| Environment | Min Instances | Max Instances | CPU | Memory |
|-------------|---------------|---------------|-----|--------|
| development | 1 | 2 | 1 | 2GB |
| testing | 1 | 3 | 1 | 2GB |
| staging | 1 | 5 | 2 | 4GB |
| production | 2 | 10 | 2 | 4GB |

### Auto-Scaling Configuration

Auto-scaling is configured based on:
- CPU usage (scale up at 70%, scale down at 30%)
- Memory usage (scale up at 80%, scale down at 40%)
- Request rate thresholds

Configure in `cloudbaserc.json`:
```json
{
  "policyType": "cpu",
  "policyThreshold": 70,
  "minNum": 1,
  "maxNum": 10
}
```

### Persistent Storage

Data volumes are automatically provisioned:
- `/var/lib/postgresql/14/main` - PostgreSQL data (50GB default)
- `/var/lib/redis` - Redis data (10GB default)
- `/app/label-studio-data` - Label Studio data (100GB default)
- `/app/uploads` - User uploads (50GB default)
- `/app/logs` - Application logs (20GB default)
- `/app/backups` - Backup storage (100GB default)

## Deployment Strategies

### Blue-Green Deployment

Zero-downtime deployments using blue-green strategy:

```python
from src.deployment import BlueGreenDeployer, DeploymentStrategy

deployer = BlueGreenDeployer()
result = await deployer.deploy(
    version="2.3.0",
    strategy=DeploymentStrategy.BLUE_GREEN
)
```

Traffic is gradually shifted:
1. Deploy to inactive environment
2. Validate health checks
3. Shift traffic: 10% → 25% → 50% → 75% → 100%
4. Monitor for issues
5. Cleanup old environment

### Rollback

If issues are detected:
```bash
# Automatic rollback on failure
./scripts/deploy-tcb.sh production --rollback-on-failure

# Manual rollback
./scripts/deploy-tcb.sh production --rollback
```

## Monitoring

### Health Checks

The container exposes health endpoints:
- `/health` - Overall health status
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe

### Metrics

Prometheus metrics are available at `/metrics`:
- Container CPU/memory usage
- Service health status
- Request latency and throughput
- Database connection pool status

### Alerts

Default alert rules:
- High CPU usage (>80% for 5 minutes)
- High memory usage (>85% for 5 minutes)
- Service unhealthy (>1 minute)
- High disk usage (>80%)

Configure alert webhook:
```bash
ALERT_WEBHOOK_URL=https://your-webhook-url
```

## Logging

### Log Format

Logs are output in JSON format for easy parsing:
```json
{
  "timestamp": "2026-01-12T10:30:00Z",
  "level": "INFO",
  "message": "Request completed",
  "service": "superinsight",
  "request_id": "req-123",
  "duration_ms": 45
}
```

### Log Levels

Configure via environment:
```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Log Rotation

Logs are automatically rotated:
- Max file size: 100MB
- Max files: 10
- Retention: 7 days (configurable)

## Security

### Secrets Management

Sensitive values should be stored in TCB secrets:
```bash
# Set secrets via TCB console or CLI
tcb env:var:set SECRET_KEY=your-secret --env your-env-id
```

### Network Security

- HTTPS is enforced by default
- WAF protection available
- DDoS protection enabled

### Access Control

Configure in `cloudbaserc.json`:
```json
{
  "security": {
    "enableHttps": true,
    "httpsRedirect": true,
    "enableWaf": true,
    "enableDdosProtection": true
  }
}
```

## Troubleshooting

### Common Issues

**Container fails to start:**
- Check logs: `tcb logs --env your-env-id`
- Verify environment variables are set
- Ensure sufficient resources allocated

**Database connection errors:**
- Verify PostgreSQL is running inside container
- Check connection string format
- Ensure data volume is mounted

**Service unhealthy:**
- Check individual service status via supervisor
- Review service-specific logs
- Verify port configurations

### Debug Mode

Enable debug logging:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

### Support

For issues:
1. Check the [troubleshooting guide](./tcb-troubleshooting.md)
2. Review TCB documentation
3. Contact support with deployment ID and logs

## API Reference

### Deployment Module

```python
from src.deployment import (
    TCBClient,
    BlueGreenDeployer,
    TCBAutoScaler,
    TCBEnvConfigManager,
    TCBMonitoringService,
    TCBLogManager
)

# Initialize TCB client
client = TCBClient(config)
await client.deploy_container(service_config, image_url)

# Configure auto-scaling
scaler = TCBAutoScaler()
await scaler.manual_scale(5)

# Environment configuration
env_manager = TCBEnvConfigManager()
env_manager.set_environment(Environment.PRODUCTION)
config = env_manager.get_deployment_config()
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.3.0 | 2026-01-12 | Initial TCB full-stack deployment |
