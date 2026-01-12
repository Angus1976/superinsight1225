# TCB Deployment Troubleshooting Guide

This guide helps diagnose and resolve common issues with TCB deployments.

## Container Startup Issues

### Container Fails to Start

**Symptoms:**
- Container status shows "Failed" or "Error"
- No logs available

**Solutions:**

1. **Check resource allocation:**
   ```bash
   # Ensure sufficient CPU and memory
   # Minimum: 1 CPU, 2GB memory
   # Recommended: 2 CPU, 4GB memory
   ```

2. **Verify environment variables:**
   ```bash
   # Required variables
   TCB_ENV_ID
   POSTGRES_PASSWORD
   SECRET_KEY
   JWT_SECRET_KEY
   ```

3. **Check Dockerfile syntax:**
   ```bash
   docker build -f deploy/tcb/Dockerfile.fullstack . --no-cache
   ```

### Services Not Starting

**Symptoms:**
- Container starts but services are unhealthy
- Specific service logs show errors

**Solutions:**

1. **Check supervisor status:**
   ```bash
   # Inside container
   supervisorctl status
   ```

2. **Review service logs:**
   ```bash
   # PostgreSQL
   cat /var/log/supervisor/postgresql.log
   
   # Redis
   cat /var/log/supervisor/redis.log
   
   # SuperInsight API
   cat /var/log/supervisor/superinsight-api.log
   ```

3. **Verify port availability:**
   ```bash
   netstat -tlnp | grep -E '5432|6379|8000|8080'
   ```

## Database Issues

### PostgreSQL Connection Errors

**Symptoms:**
- "Connection refused" errors
- "Database does not exist" errors

**Solutions:**

1. **Check PostgreSQL is running:**
   ```bash
   pg_isready -h localhost -p 5432
   ```

2. **Verify database exists:**
   ```bash
   psql -U postgres -c "\l"
   ```

3. **Check connection string:**
   ```bash
   # Format: postgresql://user:password@localhost:5432/dbname
   echo $DATABASE_URL
   ```

4. **Initialize database if needed:**
   ```bash
   alembic upgrade head
   ```

### Database Migration Failures

**Symptoms:**
- Alembic errors during startup
- Schema mismatch errors

**Solutions:**

1. **Check migration status:**
   ```bash
   alembic current
   alembic history
   ```

2. **Reset migrations (development only):**
   ```bash
   alembic downgrade base
   alembic upgrade head
   ```

## Redis Issues

### Redis Connection Errors

**Symptoms:**
- "Connection refused" to Redis
- Cache operations failing

**Solutions:**

1. **Check Redis is running:**
   ```bash
   redis-cli ping
   ```

2. **Verify Redis configuration:**
   ```bash
   cat /etc/redis/redis.conf | grep -E 'bind|port|maxmemory'
   ```

3. **Check memory usage:**
   ```bash
   redis-cli info memory
   ```

## Label Studio Issues

### Label Studio Not Accessible

**Symptoms:**
- Port 8080 not responding
- Label Studio UI not loading

**Solutions:**

1. **Check Label Studio process:**
   ```bash
   supervisorctl status label-studio
   ```

2. **Verify data directory:**
   ```bash
   ls -la /app/label-studio-data
   ```

3. **Check Label Studio logs:**
   ```bash
   cat /var/log/supervisor/label-studio.log
   ```

## Network Issues

### Service Communication Failures

**Symptoms:**
- Services can't communicate internally
- Nginx proxy errors

**Solutions:**

1. **Check Nginx configuration:**
   ```bash
   nginx -t
   cat /etc/nginx/nginx.conf
   ```

2. **Verify internal DNS:**
   ```bash
   # Services should be accessible via localhost
   curl http://localhost:8000/health
   curl http://localhost:8080/health
   ```

3. **Check firewall rules:**
   ```bash
   iptables -L -n
   ```

### External Access Issues

**Symptoms:**
- Can't access service from outside
- SSL/TLS errors

**Solutions:**

1. **Verify TCB domain configuration:**
   - Check TCB console for assigned domain
   - Verify DNS propagation

2. **Check HTTPS configuration:**
   ```json
   {
     "security": {
       "enableHttps": true,
       "httpsRedirect": true
     }
   }
   ```

## Performance Issues

### High CPU Usage

**Symptoms:**
- CPU consistently above 80%
- Slow response times

**Solutions:**

1. **Identify CPU-intensive processes:**
   ```bash
   top -c
   ```

2. **Check for runaway queries:**
   ```sql
   SELECT * FROM pg_stat_activity WHERE state = 'active';
   ```

3. **Scale up instances:**
   ```python
   from src.deployment import get_tcb_auto_scaler
   scaler = get_tcb_auto_scaler()
   await scaler.manual_scale(5)
   ```

### High Memory Usage

**Symptoms:**
- Memory above 85%
- OOM kills

**Solutions:**

1. **Check memory consumers:**
   ```bash
   ps aux --sort=-%mem | head -10
   ```

2. **Adjust PostgreSQL memory:**
   ```bash
   # In postgresql.conf
   shared_buffers = 256MB
   work_mem = 16MB
   ```

3. **Adjust Redis memory:**
   ```bash
   # In redis.conf
   maxmemory 256mb
   maxmemory-policy allkeys-lru
   ```

### Slow Response Times

**Symptoms:**
- API latency above 500ms
- Timeouts

**Solutions:**

1. **Check database query performance:**
   ```sql
   SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
   ```

2. **Enable query logging:**
   ```bash
   # In postgresql.conf
   log_min_duration_statement = 1000
   ```

3. **Check Redis cache hit rate:**
   ```bash
   redis-cli info stats | grep keyspace
   ```

## Deployment Issues

### Deployment Fails

**Symptoms:**
- `tcb framework deploy` fails
- Build errors

**Solutions:**

1. **Check TCB CLI version:**
   ```bash
   tcb -v
   npm update -g @cloudbase/cli
   ```

2. **Verify cloudbaserc.json:**
   ```bash
   cat cloudbaserc.json | python -m json.tool
   ```

3. **Check build logs:**
   ```bash
   tcb logs --env your-env-id
   ```

### Rollback Issues

**Symptoms:**
- Rollback fails
- Previous version not available

**Solutions:**

1. **Check deployment history:**
   ```python
   from src.deployment import get_blue_green_deployer
   deployer = get_blue_green_deployer()
   history = deployer.get_deployment_history()
   ```

2. **Manual rollback:**
   ```bash
   ./scripts/deploy-tcb.sh production --version previous-version
   ```

## Logging Issues

### Missing Logs

**Symptoms:**
- Logs not appearing in TCB console
- Log files empty

**Solutions:**

1. **Check log configuration:**
   ```bash
   echo $LOG_LEVEL
   ```

2. **Verify log directory permissions:**
   ```bash
   ls -la /app/logs
   ```

3. **Check log rotation:**
   ```bash
   cat /etc/logrotate.d/superinsight
   ```

## Getting Help

If issues persist:

1. **Collect diagnostic information:**
   ```bash
   ./docker_diagnostic.sh > diagnostic.log
   ```

2. **Include in support request:**
   - Deployment ID
   - Environment (dev/staging/prod)
   - Error messages
   - Diagnostic log
   - Steps to reproduce

3. **Contact channels:**
   - TCB Support: [console.cloud.tencent.com/workorder](https://console.cloud.tencent.com/workorder)
   - SuperInsight Issues: GitHub Issues
