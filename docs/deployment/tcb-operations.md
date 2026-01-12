# TCB Operations Manual

This manual covers day-to-day operations for TCB deployments.

## Daily Operations

### Health Monitoring

Check system health:
```bash
# Via API
curl https://your-domain.tcb.qcloud.la/health

# Via TCB console
tcb logs --env your-env-id --service superinsight-fullstack
```

### Log Review

Review recent logs:
```bash
# Application logs
tcb logs --env your-env-id --lines 100

# Filter by level
tcb logs --env your-env-id | grep ERROR
```

### Metrics Check

Key metrics to monitor:
- CPU usage: Should be < 70% average
- Memory usage: Should be < 80%
- Response time P95: Should be < 500ms
- Error rate: Should be < 1%

## Scaling Operations

### Manual Scaling

Scale instances up or down:
```python
from src.deployment import get_tcb_auto_scaler

scaler = get_tcb_auto_scaler()

# Scale to specific count
await scaler.manual_scale(5)

# Check current state
state = scaler.get_current_state()
print(f"Current instances: {state['current_instances']}")
```

### Auto-Scaling Configuration

Modify scaling rules:
```python
from src.deployment import ScalingRule, ScalingMetricType

# Add custom rule
rule = ScalingRule(
    name="custom_cpu_rule",
    metric_type=ScalingMetricType.CPU,
    threshold_up=75.0,
    threshold_down=25.0,
    scale_up_increment=2
)
scaler.add_rule(rule)

# Disable a rule
scaler.disable_rule("memory_scaling")
```

## Backup Operations

### Database Backup

Automated backups run daily at 2 AM. Manual backup:
```bash
# Inside container
pg_dump -U postgres superinsight > /app/backups/manual_backup_$(date +%Y%m%d).sql

# Compress
gzip /app/backups/manual_backup_$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
# Stop application
supervisorctl stop superinsight-api

# Restore database
gunzip -c /app/backups/backup_20260112.sql.gz | psql -U postgres superinsight

# Restart application
supervisorctl start superinsight-api
```

### Backup to Cloud Storage

```bash
# Upload to COS
tcb storage:upload /app/backups/backup_20260112.sql.gz backups/
```

## Deployment Operations

### Standard Deployment

```bash
# Deploy new version
./scripts/deploy-tcb.sh production

# Deploy specific version
./scripts/deploy-tcb.sh production --version 2.3.1
```

### Blue-Green Deployment

```python
from src.deployment import BlueGreenDeployer, DeploymentStrategy

deployer = BlueGreenDeployer()

# Deploy with blue-green strategy
result = await deployer.deploy(
    version="2.3.1",
    strategy=DeploymentStrategy.BLUE_GREEN
)

# Check deployment status
state = deployer.get_current_state()
print(f"Active environment: {state['environments']}")
```

### Rollback

```bash
# Automatic rollback
./scripts/deploy-tcb.sh production --rollback

# Manual rollback via API
```
```python
deployer = BlueGreenDeployer()
await deployer.manual_rollback()
```

## Configuration Management

### Environment Variables

Update environment variables:
```bash
# Via TCB CLI
tcb env:var:set LOG_LEVEL=DEBUG --env your-env-id

# Via console
# Navigate to Environment Settings > Environment Variables
```

### Secrets Rotation

Rotate secrets periodically:
```bash
# Generate new secret
NEW_SECRET=$(openssl rand -hex 32)

# Update in TCB
tcb env:var:set SECRET_KEY=$NEW_SECRET --env your-env-id

# Trigger redeployment
./scripts/deploy-tcb.sh production
```

## Maintenance Operations

### Scheduled Maintenance

Before maintenance:
1. Notify users of maintenance window
2. Scale up instances for traffic handling
3. Enable maintenance mode if available

During maintenance:
```bash
# Enable maintenance mode
curl -X POST https://your-domain/api/v1/system/maintenance/enable

# Perform maintenance tasks
# ...

# Disable maintenance mode
curl -X POST https://your-domain/api/v1/system/maintenance/disable
```

### Database Maintenance

```sql
-- Vacuum and analyze
VACUUM ANALYZE;

-- Reindex
REINDEX DATABASE superinsight;

-- Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### Redis Maintenance

```bash
# Check memory usage
redis-cli info memory

# Clear cache if needed (careful in production)
redis-cli FLUSHDB

# Check slow log
redis-cli SLOWLOG GET 10
```

## Incident Response

### High CPU Alert

1. Check current CPU usage:
   ```bash
   tcb logs --env your-env-id | grep cpu
   ```

2. Identify cause:
   - Check for runaway processes
   - Review recent deployments
   - Check for traffic spikes

3. Mitigate:
   ```python
   # Scale up immediately
   scaler = get_tcb_auto_scaler()
   await scaler.manual_scale(scaler.current_instances + 2)
   ```

### Service Unhealthy

1. Check service status:
   ```bash
   curl https://your-domain/health
   ```

2. Review logs:
   ```bash
   tcb logs --env your-env-id --lines 500 | grep ERROR
   ```

3. Restart if needed:
   ```bash
   # Trigger rolling restart
   ./scripts/deploy-tcb.sh production --restart
   ```

### Database Connection Issues

1. Check connection pool:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

2. Kill idle connections:
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'idle' 
   AND query_start < now() - interval '1 hour';
   ```

3. Restart application if needed

## Monitoring Dashboards

### Key Dashboards

1. **System Overview**
   - CPU, Memory, Disk usage
   - Instance count
   - Network I/O

2. **Application Performance**
   - Request rate
   - Response time percentiles
   - Error rate

3. **Business Metrics**
   - Active users
   - Annotation throughput
   - Quality scores

### Alert Configuration

```python
from src.deployment import TCBMonitoringService, AlertRule, AlertSeverity

monitoring = TCBMonitoringService()

# Add custom alert
rule = AlertRule(
    name="high_error_rate",
    metric_name="error_rate",
    condition=">",
    threshold=5.0,
    duration_seconds=300,
    severity=AlertSeverity.CRITICAL
)
monitoring.add_alert_rule(rule)
```

## Runbooks

### Runbook: Deploy New Version

1. Pre-deployment checks:
   - [ ] All tests passing
   - [ ] Changelog updated
   - [ ] Database migrations tested

2. Deployment:
   ```bash
   ./scripts/deploy-tcb.sh production
   ```

3. Post-deployment verification:
   - [ ] Health check passing
   - [ ] Key features working
   - [ ] No error spike in logs

### Runbook: Scale for Traffic

1. Anticipate traffic increase
2. Pre-scale instances:
   ```python
   await scaler.manual_scale(target_instances)
   ```
3. Monitor during event
4. Scale down after event

### Runbook: Emergency Rollback

1. Identify issue requiring rollback
2. Execute rollback:
   ```bash
   ./scripts/deploy-tcb.sh production --rollback
   ```
3. Verify rollback successful
4. Investigate root cause
5. Document incident

## Contact Information

- **On-Call**: Check rotation schedule
- **Escalation**: Team lead → Engineering manager
- **TCB Support**: [console.cloud.tencent.com/workorder](https://console.cloud.tencent.com/workorder)
