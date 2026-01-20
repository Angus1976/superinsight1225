# SuperInsight i18n Configuration Guide

## Overview

This document covers all configuration options for the SuperInsight internationalization (i18n) system, including environment variables, deployment settings, and customization options.

## Environment Configuration

### Required Environment Variables

```bash
# Basic Configuration
I18N_DEFAULT_LANGUAGE=zh          # Default language (zh or en)
I18N_SUPPORTED_LANGUAGES=zh,en    # Comma-separated list of supported languages
I18N_FALLBACK_LANGUAGE=zh         # Fallback language for missing translations

# Performance Settings
I18N_CACHE_ENABLED=true           # Enable translation caching
I18N_CACHE_TTL=300               # Cache TTL in seconds (5 minutes)
I18N_CACHE_MAX_SIZE=1000         # Maximum cache entries

# Logging Configuration
I18N_LOG_LEVEL=INFO              # Log level (DEBUG, INFO, WARN, ERROR)
I18N_LOG_MISSING_KEYS=true       # Log missing translation keys
I18N_LOG_LANGUAGE_CHANGES=false  # Log language change events

# API Configuration
I18N_API_RATE_LIMIT=100          # Requests per minute per client
I18N_API_TIMEOUT=30              # API timeout in seconds
```

### Optional Environment Variables

```bash
# Development Settings
I18N_DEBUG_MODE=false            # Enable debug mode for development
I18N_STRICT_MODE=false           # Strict mode - fail on missing translations
I18N_VALIDATION_ENABLED=true    # Enable translation validation

# External Integration
I18N_EXTERNAL_PROVIDER_URL=      # External translation service URL
I18N_EXTERNAL_PROVIDER_KEY=      # API key for external service
I18N_SYNC_ENABLED=false          # Enable external sync

# Monitoring
I18N_METRICS_ENABLED=true        # Enable metrics collection
I18N_HEALTH_CHECK_ENABLED=true   # Enable health check endpoint
```

## Configuration Files

### Main Configuration File

Create `config/i18n.yaml` for detailed configuration:

```yaml
# config/i18n.yaml
i18n:
  # Language Settings
  default_language: "zh"
  supported_languages:
    - "zh"
    - "en"
  fallback_language: "zh"
  
  # Translation Sources
  translation_sources:
    - type: "internal"
      path: "src/i18n/translations.py"
    - type: "file"
      path: "translations/"
      format: "json"
  
  # Caching Configuration
  cache:
    enabled: true
    ttl: 300  # 5 minutes
    max_size: 1000
    backend: "memory"  # memory, redis, memcached
    
  # Redis Configuration (if using Redis cache)
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: null
    
  # Performance Settings
  performance:
    lazy_loading: true
    preload_languages: ["zh"]
    batch_size: 100
    
  # API Settings
  api:
    rate_limit:
      requests_per_minute: 100
      burst_size: 20
    timeout: 30
    cors_enabled: true
    
  # Logging Configuration
  logging:
    level: "INFO"
    log_missing_keys: true
    log_language_changes: false
    log_performance: false
    
  # Validation Settings
  validation:
    enabled: true
    strict_mode: false
    check_completeness: true
    check_consistency: true
    
  # Development Settings
  development:
    debug_mode: false
    hot_reload: false
    translation_editor: false
    
  # Monitoring
  monitoring:
    metrics_enabled: true
    health_check_enabled: true
    performance_tracking: true
```

### Language-Specific Configuration

Create language-specific configuration files:

```yaml
# config/languages/zh.yaml
language:
  code: "zh"
  name: "中文"
  native_name: "中文"
  direction: "ltr"
  locale: "zh-CN"
  
formatting:
  date_format: "YYYY年MM月DD日"
  time_format: "HH:mm:ss"
  datetime_format: "YYYY年MM月DD日 HH:mm:ss"
  number_format: "###,###.##"
  currency_format: "¥###,###.##"
  
ui:
  text_expansion_factor: 1.0
  line_height_multiplier: 1.2
  font_family: "PingFang SC, Microsoft YaHei, sans-serif"
```

```yaml
# config/languages/en.yaml
language:
  code: "en"
  name: "English"
  native_name: "English"
  direction: "ltr"
  locale: "en-US"
  
formatting:
  date_format: "MM/DD/YYYY"
  time_format: "HH:mm:ss"
  datetime_format: "MM/DD/YYYY HH:mm:ss"
  number_format: "###,###.##"
  currency_format: "$###,###.##"
  
ui:
  text_expansion_factor: 1.3
  line_height_multiplier: 1.0
  font_family: "Arial, Helvetica, sans-serif"
```

## Docker Configuration

### Dockerfile Configuration

```dockerfile
# Dockerfile
FROM python:3.9-slim

# Set environment variables
ENV I18N_DEFAULT_LANGUAGE=zh
ENV I18N_SUPPORTED_LANGUAGES=zh,en
ENV I18N_CACHE_ENABLED=true
ENV I18N_LOG_LEVEL=INFO

# Copy configuration files
COPY config/i18n.yaml /app/config/i18n.yaml
COPY config/languages/ /app/config/languages/

# Install dependencies and copy application
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

COPY src/ /app/src/
WORKDIR /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/i18n || exit 1

# Start application
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  superinsight-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - I18N_DEFAULT_LANGUAGE=zh
      - I18N_SUPPORTED_LANGUAGES=zh,en
      - I18N_CACHE_ENABLED=true
      - I18N_CACHE_TTL=300
      - I18N_LOG_LEVEL=INFO
      - I18N_REDIS_HOST=redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    depends_on:
      - redis
    networks:
      - superinsight-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - superinsight-network

volumes:
  redis_data:

networks:
  superinsight-network:
    driver: bridge
```

## Kubernetes Configuration

### ConfigMap

```yaml
# k8s/i18n-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: i18n-config
  namespace: superinsight
data:
  I18N_DEFAULT_LANGUAGE: "zh"
  I18N_SUPPORTED_LANGUAGES: "zh,en"
  I18N_CACHE_ENABLED: "true"
  I18N_CACHE_TTL: "300"
  I18N_LOG_LEVEL: "INFO"
  I18N_REDIS_HOST: "redis-service"
  
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: i18n-files
  namespace: superinsight
data:
  i18n.yaml: |
    i18n:
      default_language: "zh"
      supported_languages: ["zh", "en"]
      cache:
        enabled: true
        ttl: 300
        backend: "redis"
      redis:
        host: "redis-service"
        port: 6379
```

### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: superinsight-api
  namespace: superinsight
spec:
  replicas: 3
  selector:
    matchLabels:
      app: superinsight-api
  template:
    metadata:
      labels:
        app: superinsight-api
    spec:
      containers:
      - name: api
        image: superinsight/api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: i18n-config
        volumeMounts:
        - name: i18n-config-volume
          mountPath: /app/config/i18n.yaml
          subPath: i18n.yaml
        livenessProbe:
          httpGet:
            path: /health/i18n
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/i18n
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: i18n-config-volume
        configMap:
          name: i18n-files
```

## Application Configuration

### FastAPI Configuration

```python
# src/config/i18n_config.py
from pydantic import BaseSettings
from typing import List, Optional

class I18nSettings(BaseSettings):
    # Basic settings
    default_language: str = "zh"
    supported_languages: List[str] = ["zh", "en"]
    fallback_language: str = "zh"
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl: int = 300
    cache_max_size: int = 1000
    cache_backend: str = "memory"  # memory, redis
    
    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # API settings
    api_rate_limit: int = 100
    api_timeout: int = 30
    
    # Logging settings
    log_level: str = "INFO"
    log_missing_keys: bool = True
    log_language_changes: bool = False
    
    # Development settings
    debug_mode: bool = False
    strict_mode: bool = False
    validation_enabled: bool = True
    
    class Config:
        env_prefix = "I18N_"
        case_sensitive = False

# Global settings instance
i18n_settings = I18nSettings()
```

### Application Initialization

```python
# src/app.py
from fastapi import FastAPI
from src.config.i18n_config import i18n_settings
from src.i18n.middleware import I18nMiddleware
from src.i18n.manager import initialize_i18n
import logging

# Configure logging
logging.basicConfig(level=getattr(logging, i18n_settings.log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SuperInsight API",
    description="SuperInsight Platform with i18n support",
    version="1.0.0"
)

# Initialize i18n system
@app.on_event("startup")
async def startup_event():
    try:
        await initialize_i18n(i18n_settings)
        logger.info("I18n system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize i18n system: {e}")
        raise

# Add i18n middleware
app.add_middleware(I18nMiddleware)

# Health check endpoint
@app.get("/health/i18n")
async def i18n_health_check():
    from src.i18n.manager import get_manager
    
    manager = get_manager()
    supported_languages = manager.get_supported_languages()
    
    return {
        "status": "healthy",
        "default_language": i18n_settings.default_language,
        "supported_languages": supported_languages,
        "cache_enabled": i18n_settings.cache_enabled
    }
```

## Production Configuration

### Load Balancer Configuration

```nginx
# nginx.conf
upstream superinsight_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    server_name api.superinsight.com;
    
    # Add language detection headers
    location / {
        proxy_pass http://superinsight_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Accept-Language $http_accept_language;
        
        # Cache translated responses
        proxy_cache_key "$scheme$request_method$host$request_uri$http_accept_language";
        proxy_cache_valid 200 5m;
    }
    
    # Static assets with language-specific caching
    location /static/ {
        alias /var/www/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
        add_header Vary "Accept-Language";
    }
}
```

### Monitoring Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'superinsight-i18n'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
rule_files:
  - "i18n_alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

```yaml
# monitoring/i18n_alerts.yml
groups:
- name: i18n_alerts
  rules:
  - alert: I18nHighErrorRate
    expr: rate(i18n_translation_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High i18n error rate detected"
      description: "I18n error rate is {{ $value }} errors per second"
      
  - alert: I18nCacheHitRateLow
    expr: i18n_cache_hit_rate < 0.8
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Low i18n cache hit rate"
      description: "I18n cache hit rate is {{ $value }}"
      
  - alert: I18nServiceDown
    expr: up{job="superinsight-i18n"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "I18n service is down"
      description: "I18n service has been down for more than 1 minute"
```

## Security Configuration

### API Security

```python
# src/security/i18n_security.py
from fastapi import HTTPException, Request
from typing import List
import re

class I18nSecurityConfig:
    # Allowed language codes (prevent injection)
    ALLOWED_LANGUAGES = ["zh", "en"]
    
    # Maximum translation key length
    MAX_KEY_LENGTH = 100
    
    # Allowed characters in translation keys
    KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]+$')
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = 100
    RATE_LIMIT_BURST = 20

def validate_language_code(language: str) -> str:
    """Validate and sanitize language code."""
    if not language or language not in I18nSecurityConfig.ALLOWED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language code. Supported: {I18nSecurityConfig.ALLOWED_LANGUAGES}"
        )
    return language

def validate_translation_key(key: str) -> str:
    """Validate translation key format."""
    if not key or len(key) > I18nSecurityConfig.MAX_KEY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail="Invalid translation key length"
        )
    
    if not I18nSecurityConfig.KEY_PATTERN.match(key):
        raise HTTPException(
            status_code=400,
            detail="Invalid translation key format"
        )
    
    return key
```

### Content Security Policy

```python
# src/middleware/security_headers.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers for i18n content
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:;"
        )
        
        return response
```

## Troubleshooting Configuration

### Debug Mode Configuration

```python
# src/config/debug.py
import os
from typing import Dict, Any

class DebugConfig:
    def __init__(self):
        self.debug_mode = os.getenv('I18N_DEBUG_MODE', 'false').lower() == 'true'
        self.log_all_requests = os.getenv('I18N_LOG_ALL_REQUESTS', 'false').lower() == 'true'
        self.translation_debug = os.getenv('I18N_TRANSLATION_DEBUG', 'false').lower() == 'true'
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get current debug configuration."""
        return {
            'debug_mode': self.debug_mode,
            'log_all_requests': self.log_all_requests,
            'translation_debug': self.translation_debug,
            'environment': os.getenv('ENVIRONMENT', 'development')
        }

debug_config = DebugConfig()
```

This configuration guide provides comprehensive setup options for deploying and customizing the SuperInsight i18n system across different environments and use cases.