# Migration 016: Add LLMHealthStatus Table

## Overview

This migration adds the `llm_health_status` table for tracking the health status of LLM providers with automatic health checks.

## Migration Details

- **Revision ID**: `016_add_llm_health_status`
- **Down Revision**: `015_add_optimization_indexes`
- **Created**: 2026-01-19

## Table Structure

### llm_health_status

Monitors the health of LLM providers with automatic health checks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier for health status record |
| provider_id | UUID | FOREIGN KEY, NOT NULL, UNIQUE | Reference to llm_configurations.id |
| is_healthy | Boolean | NOT NULL, DEFAULT true | Current health status of the provider |
| last_check_at | DateTime | NOT NULL, DEFAULT now() | Timestamp of last health check |
| last_error | String(500) | NULL | Last error message if health check failed |
| consecutive_failures | Integer | NOT NULL, DEFAULT 0 | Number of consecutive health check failures |
| updated_at | DateTime | NOT NULL, DEFAULT now() | Last update timestamp |

### Foreign Key Constraints

- `provider_id` → `llm_configurations.id` (CASCADE on delete)
  - When an LLM configuration is deleted, its health status is automatically deleted

### Indexes

1. **ix_llm_health_provider** on `provider_id`
   - Enables fast lookup of health status by provider
   - Supports the unique constraint

2. **ix_llm_health_status** on `is_healthy`
   - Enables fast filtering of healthy/unhealthy providers
   - Used by health monitoring queries to find available providers

3. **ix_llm_health_last_check** on `last_check_at`
   - Enables efficient queries for stale health checks
   - Used by health monitor to identify providers needing checks

## Usage Examples

### Query healthy providers

```sql
SELECT p.id, p.name, h.last_check_at
FROM llm_configurations p
JOIN llm_health_status h ON p.id = h.provider_id
WHERE h.is_healthy = true
ORDER BY h.last_check_at DESC;
```

### Find providers with consecutive failures

```sql
SELECT p.id, p.name, h.consecutive_failures, h.last_error
FROM llm_configurations p
JOIN llm_health_status h ON p.id = h.provider_id
WHERE h.consecutive_failures >= 3
ORDER BY h.consecutive_failures DESC;
```

### Find providers needing health checks

```sql
SELECT p.id, p.name, h.last_check_at
FROM llm_configurations p
JOIN llm_health_status h ON p.id = h.provider_id
WHERE h.last_check_at < NOW() - INTERVAL '60 seconds'
ORDER BY h.last_check_at ASC;
```

## Running the Migration

### Upgrade

```bash
# Apply this migration
alembic upgrade 016_add_llm_health_status

# Or upgrade to latest
alembic upgrade head
```

### Downgrade

```bash
# Revert this migration
alembic downgrade 015_add_optimization_indexes
```

## Validation

The migration includes the following validations:

1. **Syntax Check**: Migration file compiles without errors
2. **Structure Check**: All required attributes present (revision, down_revision, upgrade, downgrade)
3. **Consistency Check**: Table structure matches SQLAlchemy model definition

Run validation tests:

```bash
pytest tests/test_llm_health_status_migration.py -v
```

## Related Files

- **Model**: `src/models/llm_configuration.py` - LLMHealthStatus class
- **Design**: `.kiro/specs/llm-integration/design.md` - Section 4.1 Database Schema
- **Requirements**: `.kiro/specs/llm-integration/requirements.md` - Requirements 5.1-5.4
- **Tests**: `tests/test_llm_health_status_migration.py` - Migration structure tests

## Integration with Health Monitor

This table is used by the Health Monitor service (`src/ai/llm/health_monitor.py`) to:

1. **Track Provider Health**: Store current health status for each provider
2. **Monitor Failures**: Count consecutive failures to trigger alerts
3. **Schedule Checks**: Identify providers needing health checks based on `last_check_at`
4. **Route Requests**: Enable the LLM Switcher to route requests only to healthy providers

## Performance Considerations

- **Index Usage**: All three indexes are designed for specific query patterns used by the health monitor
- **Unique Constraint**: Ensures one health status record per provider
- **Cascade Delete**: Automatically cleans up health status when provider is deleted
- **Minimal Columns**: Only essential fields to minimize storage and update overhead

## Troubleshooting

### Migration fails with "relation already exists"

The table may already exist. Check with:

```sql
SELECT * FROM information_schema.tables 
WHERE table_name = 'llm_health_status';
```

If it exists, you can skip this migration or manually drop the table first.

### Foreign key constraint fails

Ensure the `llm_configurations` table exists before running this migration:

```sql
SELECT * FROM information_schema.tables 
WHERE table_name = 'llm_configurations';
```

If missing, run migration `008_add_llm_integration_tables` first.

## Changelog

- **2026-01-19**: Initial creation of migration for LLMHealthStatus table
