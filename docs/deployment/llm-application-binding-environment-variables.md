# LLM Application Binding System - Environment Variables

**Version**: 1.0  
**Last Updated**: 2026-03-03  
**Related Spec**: `.kiro/specs/llm-application-binding/`

---

## Overview

This document describes the environment variables required for the LLM Application Binding System. The system supports both database-driven configuration (recommended) and environment variable fallback for backward compatibility.

---

## Required Environment Variables

### LLM_ENCRYPTION_KEY

**Purpose**: Encryption key for protecting LLM API keys in the database

**Format**: Base64-encoded 32-byte key

**Required**: Yes (when using database configuration)

**Example**:
```bash
LLM_ENCRYPTION_KEY="dGhpc2lzYTMyYnl0ZWtleWZvcmFlczI1Ng=="
```

**Generation**:
```bash
# Generate a secure 32-byte key and encode it
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

**Security Notes**:
- Store this key securely (use secrets management systems in production)
- Never commit this key to version control
- Rotate the key periodically (requires re-encrypting all API keys)
- If the key is lost, all encrypted API keys become unrecoverable

---

## Optional Environment Variables

### Redis Configuration (Recommended for Multi-Instance Deployments)

#### REDIS_HOST

**Purpose**: Redis server hostname for cache synchronization

**Default**: `localhost`

**Example**:
```bash
REDIS_HOST="redis.example.com"
```

#### REDIS_PORT

**Purpose**: Redis server port

**Default**: `6379`

**Example**:
```bash
REDIS_PORT="6379"
```

#### REDIS_PASSWORD

**Purpose**: Redis authentication password

**Default**: None (no authentication)

**Example**:
```bash
REDIS_PASSWORD="your-redis-password"
```

#### REDIS_DB

**Purpose**: Redis database number

**Default**: `0`

**Example**:
```bash
REDIS_DB="1"
```

**Benefits of Redis**:
- Cache synchronization across multiple application instances
- Faster cache invalidation propagation
- Reduced database load in multi-instance deployments

---

## Backward-Compatible Environment Variables

These variables provide fallback configuration when no database bindings exist for an application. They maintain compatibility with existing deployments.

### OPENAI_API_KEY

**Purpose**: OpenAI API key for backward compatibility

**Required**: No (only if no database configuration exists)

**Example**:
```bash
OPENAI_API_KEY="sk-proj-..."
```

### OPENAI_BASE_URL

**Purpose**: OpenAI API base URL

**Default**: `https://api.openai.com/v1`

**Example**:
```bash
# For Azure OpenAI
OPENAI_BASE_URL="https://your-resource.openai.azure.com/"

# For custom proxy
OPENAI_BASE_URL="https://api-proxy.example.com/v1"
```

### OPENAI_MODEL

**Purpose**: Default OpenAI model name

**Default**: `gpt-3.5-turbo`

**Example**:
```bash
OPENAI_MODEL="gpt-4"
```

**Fallback Behavior**:
1. System checks for database bindings first
2. If no bindings exist, falls back to these environment variables
3. If neither exists, raises configuration error

---

## Configuration Priority

The system resolves LLM configuration in the following priority order:

1. **Application-specific bindings** (highest priority)
   - Configured via database for specific application
   
2. **Tenant-level configurations**
   - Configured via database for specific tenant
   
3. **Global default configurations**
   - Configured via database with `tenant_id = NULL`
   
4. **Environment variables** (lowest priority, fallback)
   - `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`

---

## Deployment Scenarios

### Scenario 1: New Deployment with Database Configuration

**Recommended approach for new deployments**

```bash
# Required
export LLM_ENCRYPTION_KEY="$(python3 -c 'import os, base64; print(base64.b64encode(os.urandom(32)).decode())')"

# Optional (recommended for production)
export REDIS_HOST="redis.example.com"
export REDIS_PORT="6379"
export REDIS_PASSWORD="your-redis-password"
```

**Steps**:
1. Set `LLM_ENCRYPTION_KEY`
2. Run database migration: `alembic upgrade head`
3. Create LLM configurations via API or UI
4. Create bindings for applications
5. System is ready

### Scenario 2: Existing Deployment (Backward Compatible)

**For deployments currently using environment variables**

```bash
# Existing variables (continue to work)
export OPENAI_API_KEY="sk-proj-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-3.5-turbo"

# New required variable
export LLM_ENCRYPTION_KEY="$(python3 -c 'import os, base64; print(base64.b64encode(os.urandom(32)).decode())')"
```

**Migration Path**:
1. Add `LLM_ENCRYPTION_KEY` to environment
2. Run database migration: `alembic upgrade head`
3. System continues using environment variables (no disruption)
4. Gradually migrate to database configuration via UI
5. Once all configs in database, optionally remove environment variables

### Scenario 3: Multi-Instance Production Deployment

**For high-availability deployments with multiple instances**

```bash
# Required
export LLM_ENCRYPTION_KEY="your-shared-encryption-key"

# Redis for cache synchronization (required for multi-instance)
export REDIS_HOST="redis-cluster.example.com"
export REDIS_PORT="6379"
export REDIS_PASSWORD="your-redis-password"
export REDIS_DB="0"

# Optional fallback
export OPENAI_API_KEY="sk-proj-..."
```

**Benefits**:
- Cache invalidation propagates across all instances
- Configuration changes take effect immediately on all instances
- No service restart required for configuration updates

---

## Environment Variable Validation

The system validates environment variables at startup:

**Validation Checks**:
- `LLM_ENCRYPTION_KEY` is exactly 32 bytes when base64-decoded
- `REDIS_PORT` is a valid integer
- `REDIS_DB` is a non-negative integer
- `OPENAI_BASE_URL` is a valid URL format (if provided)

**Startup Errors**:
```
ValueError: LLM_ENCRYPTION_KEY must be a base64-encoded 32-byte key
ValueError: REDIS_PORT must be an integer
ValueError: OPENAI_BASE_URL must be a valid URL
```

---

## Security Best Practices

### 1. Use Secrets Management

**Production deployments should use secrets management systems**:

- **AWS**: AWS Secrets Manager or Parameter Store
- **Azure**: Azure Key Vault
- **GCP**: Google Secret Manager
- **Kubernetes**: Kubernetes Secrets
- **HashiCorp**: Vault

**Example (AWS Secrets Manager)**:
```bash
# Retrieve secret at runtime
export LLM_ENCRYPTION_KEY=$(aws secretsmanager get-secret-value \
  --secret-id llm-encryption-key \
  --query SecretString \
  --output text)
```

### 2. Rotate Encryption Keys

**Key rotation procedure**:
1. Generate new encryption key
2. Decrypt all API keys with old key
3. Re-encrypt all API keys with new key
4. Update `LLM_ENCRYPTION_KEY` environment variable
5. Restart application instances

**Rotation script** (to be implemented):
```bash
python scripts/rotate_encryption_key.py \
  --old-key "$OLD_KEY" \
  --new-key "$NEW_KEY"
```

### 3. Restrict Access

- Limit access to environment variables to authorized personnel only
- Use role-based access control (RBAC) for secrets
- Audit all access to encryption keys
- Never log or display encryption keys

### 4. Monitor for Exposure

- Scan logs for accidentally exposed keys
- Use secret scanning tools (e.g., GitGuardian, TruffleHog)
- Rotate keys immediately if exposure is suspected

---

## Troubleshooting

### Error: "LLM_ENCRYPTION_KEY not set"

**Cause**: Required encryption key is missing

**Solution**:
```bash
export LLM_ENCRYPTION_KEY="$(python3 -c 'import os, base64; print(base64.b64encode(os.urandom(32)).decode())')"
```

### Error: "Invalid encryption key length"

**Cause**: Key is not exactly 32 bytes when decoded

**Solution**: Generate a new key using the command above

### Error: "No LLM configuration found"

**Cause**: No database bindings and no environment variables

**Solution**: Either:
1. Create LLM configuration via UI/API, or
2. Set `OPENAI_API_KEY` environment variable

### Warning: "Redis connection failed, using local cache only"

**Cause**: Redis is configured but unreachable

**Impact**: Cache invalidation won't propagate across instances

**Solution**:
- Verify Redis host and port
- Check Redis authentication credentials
- Ensure network connectivity to Redis

---

## Monitoring Environment Variables

### Health Check Endpoint

**GET /api/health/config**

Returns configuration status:
```json
{
  "encryption_key_configured": true,
  "redis_configured": true,
  "redis_connected": true,
  "fallback_env_vars_configured": true,
  "database_configs_count": 5,
  "active_bindings_count": 12
}
```

### Metrics

Monitor these metrics for configuration health:

- `llm_config_source{source="database"}` - Configs loaded from database
- `llm_config_source{source="environment"}` - Configs loaded from env vars
- `redis_connection_status` - Redis connection status (0=down, 1=up)
- `cache_invalidation_events_total` - Cache invalidation event count

---

## References

- **Spec**: `.kiro/specs/llm-application-binding/`
- **Design Document**: `.kiro/specs/llm-application-binding/design.md`
- **Requirements**: Requirements 12.2 (Security and Access Control)
- **Migration Script**: `alembic/versions/009_add_llm_application_binding.py`

---

**Document Status**: Complete  
**Maintained By**: System Administrator Team
