# SuperInsight i18n Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the SuperInsight i18n system across different environments (development, staging, production).

## Prerequisites

### System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL2
- **Memory**: Minimum 4GB RAM (8GB+ recommended for production)
- **Storage**: Minimum 20GB available disk space
- **Network**: Internet access for pulling Docker images

### Required Tools

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/superinsight.git
cd superinsight
```

### 2. Deploy to Staging

```bash
cd deploy/i18n
./scripts/deploy.sh staging
```

### 3. Verify Deployment

```bash
./scripts/health_check.sh staging --detailed
```

## Environment-Specific Deployments

### Development Environment

**Purpose**: Local development and testing

```bash
# Deploy development environment
./scripts/deploy.sh development

# Access services
echo "API: http://localhost:8000"
echo "Health Check: http://localhost:8000/health/i18n"
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "Prometheus: http://localhost:9090"
```

**Features**:
- Hot reload enabled
- Debug logging
- Development tools included
- Relaxed security settings

### Staging Environment

**Purpose**: Pre-production testing and validation

```bash
# Deploy staging environment
./scripts/deploy.sh staging v1.0.0

# Run comprehensive health checks
./scripts/health_check.sh staging --detailed
```

**Features**:
- Production-like configuration
- Comprehensive monitoring
- Automated testing
- Performance validation

### Production Environment

**Purpose**: Live production deployment

```bash
# Deploy production environment
./scripts/deploy.sh production v1.0.0

# Monitor deployment
./scripts/health_check.sh production --detailed
```

**Features**:
- High availability configuration
- Security hardening
- Performance optimization
- Comprehensive monitoring and alerting

## Manual Deployment Steps

### 1. Prepare Environment

```bash
# Create deployment directory
mkdir -p /opt/superinsight/i18n
cd /opt/superinsight/i18n

# Copy deployment files
cp -r deploy/i18n/* .

# Set up environment file
cp .env.production .env.local
# Edit .env.local with your specific configuration
```

### 2. Configure Services

#### Database Setup

```bash
# Create database initialization script
cat > init-db.sql << 'EOF'
-- Create database
CREATE DATABASE superinsight;

-- Create user
CREATE USER superinsight WITH PASSWORD 'your_secure_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE superinsight TO superinsight;

-- Create i18n-related tables (if needed)
\c superinsight;

CREATE TABLE IF NOT EXISTS translation_audit (
    id SERIAL PRIMARY KEY,
    language_code VARCHAR(10) NOT NULL,
    translation_key VARCHAR(255) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(255)
);

CREATE INDEX idx_translation_audit_language ON translation_audit(language_code);
CREATE INDEX idx_translation_audit_key ON translation_audit(translation_key);
EOF
```

#### SSL Certificate Setup (Production)

```bash
# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=superinsight.com"

# For production, use Let's Encrypt or your certificate authority
```

### 3. Deploy Services

```bash
# Start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f superinsight-api
```

### 4. Verify Deployment

```bash
# Wait for services to be ready
sleep 30

# Test API health
curl -f http://localhost:8000/health/i18n

# Test i18n functionality
curl -s "http://localhost:8000/api/i18n/languages" | jq .

# Test language switching
curl -X POST "http://localhost:8000/api/settings/language" \
    -H "Content-Type: application/json" \
    -d '{"language": "en"}'
```

## Configuration Management

### Environment Variables

Key configuration options:

```bash
# Core i18n settings
I18N_DEFAULT_LANGUAGE=zh
I18N_SUPPORTED_LANGUAGES=zh,en
I18N_FALLBACK_LANGUAGE=zh

# Performance settings
I18N_CACHE_ENABLED=true
I18N_CACHE_TTL=300
I18N_API_RATE_LIMIT=1000

# Security settings
I18N_VALIDATION_ENABLED=true
I18N_STRICT_MODE=false

# Monitoring settings
I18N_METRICS_ENABLED=true
I18N_HEALTH_CHECK_ENABLED=true
```

### Configuration Files

#### Production Configuration

```yaml
# config/i18n.production.yaml
i18n:
  default_language: "zh"
  supported_languages: ["zh", "en"]
  cache:
    enabled: true
    ttl: 300
    backend: "redis"
  performance:
    max_concurrent_requests: 100
    worker_processes: 4
  monitoring:
    metrics_enabled: true
    health_check_enabled: true
```

#### Nginx Configuration

```nginx
# nginx.conf - Key sections
upstream superinsight_api {
    least_conn;
    server superinsight-api:8000;
}

# Cache translated content
proxy_cache_path /var/cache/nginx/i18n levels=1:2 keys_zone=i18n_cache:10m;

location /api/i18n/ {
    proxy_cache i18n_cache;
    proxy_cache_key "$scheme$request_method$host$request_uri$http_accept_language";
    proxy_cache_valid 200 5m;
    proxy_pass http://superinsight_api;
}
```

## Monitoring and Observability

### Health Checks

```bash
# Basic health check
curl -f http://localhost:8000/health/i18n

# Detailed health check
./scripts/health_check.sh production --detailed
```

### Metrics and Monitoring

**Prometheus Metrics**:
- `i18n_translation_requests_total` - Total translation requests
- `i18n_translation_duration_seconds` - Translation response time
- `i18n_cache_hit_rate` - Cache hit rate
- `i18n_missing_keys_total` - Missing translation keys
- `i18n_language_switch_total` - Language switching events

**Grafana Dashboards**:
- I18n Performance Dashboard
- I18n Error Monitoring
- Cache Performance
- Language Usage Statistics

**Access Monitoring**:
```bash
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

### Log Management

```bash
# View application logs
docker-compose logs -f superinsight-api

# View i18n specific logs
docker-compose logs -f superinsight-api | grep i18n

# View nginx access logs
docker-compose logs -f nginx
```

## Scaling and Performance

### Horizontal Scaling

```yaml
# docker-compose.yml - Scale API instances
services:
  superinsight-api:
    deploy:
      replicas: 3
    # ... other configuration
```

### Performance Optimization

#### Redis Optimization

```bash
# redis.conf optimizations
maxmemory 512mb
maxmemory-policy allkeys-lru
tcp-keepalive 300
```

#### Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_translations_language_key 
ON translations(language_code, translation_key);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM translations WHERE language_code = 'zh';
```

#### Nginx Caching

```nginx
# Optimize cache settings
proxy_cache_path /var/cache/nginx/i18n 
    levels=1:2 
    keys_zone=i18n_cache:50m 
    max_size=1g 
    inactive=60m;
```

## Security Considerations

### Network Security

```bash
# Firewall configuration (Ubuntu/Debian)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp  # Block direct database access
sudo ufw deny 6379/tcp  # Block direct Redis access
```

### Application Security

```yaml
# docker-compose.yml - Security settings
services:
  superinsight-api:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache
```

### SSL/TLS Configuration

```nginx
# nginx.conf - SSL settings
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
add_header Strict-Transport-Security "max-age=63072000" always;
```

## Backup and Recovery

### Database Backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/superinsight"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Database backup
docker-compose exec -T postgres pg_dump -U superinsight superinsight > \
    "$BACKUP_DIR/database_$DATE.sql"

# Configuration backup
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" config/

# Cleanup old backups (keep last 30 days)
find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
EOF

chmod +x backup.sh

# Schedule backup (crontab)
echo "0 2 * * * /opt/superinsight/i18n/backup.sh" | crontab -
```

### Recovery Procedures

```bash
# Restore from backup
BACKUP_FILE="/opt/backups/superinsight/database_20240104_020000.sql"

# Stop services
docker-compose down

# Start only database
docker-compose up -d postgres

# Wait for database to be ready
sleep 10

# Restore database
docker-compose exec -T postgres psql -U superinsight -d superinsight < "$BACKUP_FILE"

# Start all services
docker-compose up -d
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose logs superinsight-api

# Check resource usage
docker stats

# Check disk space
df -h
```

#### Database Connection Issues

```bash
# Test database connectivity
docker-compose exec postgres pg_isready -U superinsight

# Check database logs
docker-compose logs postgres
```

#### Redis Connection Issues

```bash
# Test Redis connectivity
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis
```

#### Performance Issues

```bash
# Check system resources
htop
iotop

# Check application metrics
curl -s http://localhost:8000/metrics | grep i18n

# Check cache performance
docker-compose exec redis redis-cli info stats
```

### Debug Mode

```bash
# Enable debug mode
export I18N_DEBUG_MODE=true
export I18N_LOG_LEVEL=DEBUG

# Restart services
docker-compose restart superinsight-api

# View debug logs
docker-compose logs -f superinsight-api | grep DEBUG
```

## Maintenance

### Regular Maintenance Tasks

```bash
# Weekly maintenance script
cat > maintenance.sh << 'EOF'
#!/bin/bash

# Update Docker images
docker-compose pull

# Clean up unused images
docker image prune -f

# Clean up unused volumes
docker volume prune -f

# Restart services with new images
docker-compose up -d

# Run health checks
./scripts/health_check.sh production --detailed
EOF
```

### Updates and Upgrades

```bash
# Update to new version
./scripts/deploy.sh production v1.1.0

# Rollback if needed
docker-compose down
docker tag superinsight/api:v1.0.0 superinsight/api:latest
docker-compose up -d
```

This deployment guide provides comprehensive instructions for deploying and maintaining the SuperInsight i18n system across all environments.