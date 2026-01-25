# Docker Troubleshooting Guide

**SuperInsight Platform - Docker Infrastructure**

This guide provides solutions for common Docker-related issues encountered when running the SuperInsight platform.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Container Startup Issues](#container-startup-issues)
3. [PostgreSQL Issues](#postgresql-issues)
4. [Redis Issues](#redis-issues)
5. [Neo4j Issues](#neo4j-issues)
6. [Label Studio Issues](#label-studio-issues)
7. [API Service Issues](#api-service-issues)
8. [Network and Connectivity Issues](#network-and-connectivity-issues)
9. [Volume and Data Issues](#volume-and-data-issues)
10. [Performance Issues](#performance-issues)
11. [Verification Scripts](#verification-scripts)

---

## Quick Diagnostics

### Check Overall System Status

```bash
# View all container statuses
docker-compose ps

# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# View recent logs for all services
docker-compose logs --tail=100

# Run comprehensive health check
./scripts/verify-health-checks.sh
```

### Quick Health Check Commands

| Service | Health Check Command |
|---------|---------------------|
| PostgreSQL | `docker exec superinsight-postgres pg_isready -U superinsight -d superinsight` |
| Redis | `docker exec superinsight-redis redis-cli ping` |
| Neo4j | `curl http://localhost:7474` |
| Label Studio | `curl http://localhost:8080/health` |
| API | `curl http://localhost:8000/health` |

---

## Container Startup Issues

### Issue: Containers Won't Start

**Symptoms:**
- `docker-compose up` fails
- Containers exit immediately after starting
- Health checks never pass

**Solutions:**

1. **Check Docker daemon is running:**
   ```bash
   docker info
   ```

2. **Check for port conflicts:**
   ```bash
   # Check if ports are already in use
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   lsof -i :7474  # Neo4j HTTP
   lsof -i :7687  # Neo4j Bolt
   lsof -i :8080  # Label Studio
   lsof -i :8000  # API
   ```

3. **Clean up and restart:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Force rebuild containers:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Issue: Container Keeps Restarting

**Symptoms:**
- Container status shows "Restarting"
- Health checks fail repeatedly

**Solutions:**

1. **Check container logs:**
   ```bash
   docker-compose logs <service-name>
   ```

2. **Check for resource constraints:**
   ```bash
   docker stats
   ```

3. **Increase health check timeout:**
   Edit `docker-compose.yml` and increase `timeout` and `retries` values.

---

## PostgreSQL Issues

### Issue: PostgreSQL Init Script Fails

**Symptoms:**
- Error: `syntax error at or near "$"`
- PostgreSQL container unhealthy
- Database connection failures

**Root Cause:**
The init script uses incorrect PL/pgSQL syntax with single `$` instead of `$$` delimiters.

**Solution:**

1. **Verify init script syntax:**
   ```bash
   cat scripts/init-db.sql | grep -E "DO|END"
   ```
   
   Correct syntax should be:
   ```sql
   DO $$
   BEGIN
       -- code here
   END
   $$;
   ```

2. **Fix the init script:**
   Replace `DO $` with `DO $$` and `END $;` with `END $$;`

3. **Rebuild PostgreSQL container:**
   ```bash
   docker-compose down postgres
   docker volume rm superinsight-platform_postgres_data  # WARNING: This deletes data!
   docker-compose up -d postgres
   ```

### Issue: Cannot Connect to PostgreSQL

**Symptoms:**
- Connection refused errors
- Authentication failures
- Database not found

**Solutions:**

1. **Check PostgreSQL is running:**
   ```bash
   docker exec superinsight-postgres pg_isready -U superinsight -d superinsight
   ```

2. **Verify credentials:**
   ```bash
   docker exec superinsight-postgres psql -U superinsight -d superinsight -c "SELECT 1;"
   ```

3. **Check environment variables:**
   ```bash
   docker exec superinsight-api env | grep DATABASE
   ```

4. **Test from API container:**
   ```bash
   docker exec superinsight-api python3 -c "
   import psycopg2
   conn = psycopg2.connect(host='postgres', port=5432, database='superinsight', user='superinsight', password='password')
   print('Connection successful!')
   conn.close()
   "
   ```

### Issue: PostgreSQL Extensions Not Enabled

**Symptoms:**
- UUID generation fails
- Index creation errors

**Solution:**

```bash
# Check extensions
docker exec superinsight-postgres psql -U superinsight -d superinsight -c "\dx"

# Enable extensions manually if needed
docker exec superinsight-postgres psql -U superinsight -d superinsight -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
docker exec superinsight-postgres psql -U superinsight -d superinsight -c "CREATE EXTENSION IF NOT EXISTS \"btree_gin\";"
```

---

## Redis Issues

### Issue: Redis Connection Refused

**Symptoms:**
- Cannot connect to Redis
- Cache operations fail

**Solutions:**

1. **Check Redis is running:**
   ```bash
   docker exec superinsight-redis redis-cli ping
   # Expected: PONG
   ```

2. **Check Redis logs:**
   ```bash
   docker-compose logs redis
   ```

3. **Test Redis operations:**
   ```bash
   docker exec superinsight-redis redis-cli SET test "hello"
   docker exec superinsight-redis redis-cli GET test
   docker exec superinsight-redis redis-cli DEL test
   ```

### Issue: Redis Memory Issues

**Symptoms:**
- Redis OOM errors
- Slow performance

**Solution:**

```bash
# Check Redis memory usage
docker exec superinsight-redis redis-cli INFO memory

# Clear Redis cache if needed (WARNING: Deletes all data)
docker exec superinsight-redis redis-cli FLUSHALL
```

---

## Neo4j Issues

### Issue: Neo4j Won't Start

**Symptoms:**
- Neo4j container unhealthy
- Cannot access Neo4j browser

**Solutions:**

1. **Check Neo4j logs:**
   ```bash
   docker-compose logs neo4j
   ```

2. **Check memory allocation:**
   Neo4j requires significant memory. Ensure Docker has at least 2GB allocated.

3. **Reset Neo4j data:**
   ```bash
   docker-compose down neo4j
   docker volume rm superinsight-platform_neo4j_data  # WARNING: Deletes data!
   docker-compose up -d neo4j
   ```

### Issue: Neo4j Authentication Failure

**Symptoms:**
- "The client is unauthorized" error
- Cannot connect with credentials

**Solution:**

1. **Check default credentials:**
   - Username: `neo4j`
   - Password: Check `NEO4J_AUTH` in docker-compose.yml

2. **Reset password:**
   ```bash
   docker exec superinsight-neo4j neo4j-admin set-initial-password newpassword
   ```

---

## Label Studio Issues

### Issue: Label Studio Won't Start

**Symptoms:**
- Label Studio container unhealthy
- Depends on PostgreSQL but fails

**Solutions:**

1. **Ensure PostgreSQL is healthy first:**
   ```bash
   docker exec superinsight-postgres pg_isready -U superinsight -d superinsight
   ```

2. **Check Label Studio logs:**
   ```bash
   docker-compose logs label-studio
   ```

3. **Restart Label Studio:**
   ```bash
   docker-compose restart label-studio
   ```

### Issue: Label Studio Database Migration Errors

**Symptoms:**
- Migration errors in logs
- Label Studio fails to initialize

**Solution:**

```bash
# Run migrations manually
docker exec superinsight-label-studio label-studio migrate

# Or reset Label Studio (WARNING: Deletes data)
docker-compose down label-studio
docker volume rm superinsight-platform_label_studio_data
docker-compose up -d label-studio
```

---

## API Service Issues

### Issue: API Won't Start

**Symptoms:**
- API container unhealthy
- Cannot access /health endpoint

**Solutions:**

1. **Check all dependencies are healthy:**
   ```bash
   docker-compose ps
   ```

2. **Check API logs:**
   ```bash
   docker-compose logs superinsight-api
   ```

3. **Verify environment variables:**
   ```bash
   docker exec superinsight-api env | grep -E "DATABASE|REDIS|NEO4J|LABEL"
   ```

### Issue: API Cannot Connect to Services

**Symptoms:**
- Database connection errors
- Service unavailable errors

**Solution:**

Run the connectivity verification script:
```bash
./scripts/verify-connectivity.sh
```

---

## Network and Connectivity Issues

### Issue: Containers Cannot Communicate

**Symptoms:**
- Connection refused between containers
- DNS resolution failures

**Solutions:**

1. **Check Docker network:**
   ```bash
   docker network ls
   docker network inspect superinsight-network
   ```

2. **Verify containers are on the same network:**
   ```bash
   docker inspect superinsight-api --format='{{json .NetworkSettings.Networks}}'
   ```

3. **Test inter-container connectivity:**
   ```bash
   docker exec superinsight-api ping -c 3 postgres
   docker exec superinsight-api ping -c 3 redis
   docker exec superinsight-api ping -c 3 neo4j
   docker exec superinsight-api ping -c 3 label-studio
   ```

4. **Recreate network:**
   ```bash
   docker-compose down
   docker network rm superinsight-network
   docker-compose up -d
   ```

### Issue: Port Already in Use

**Symptoms:**
- "Bind for 0.0.0.0:XXXX failed: port is already allocated"

**Solution:**

1. **Find process using the port:**
   ```bash
   lsof -i :8000  # Replace with the conflicting port
   ```

2. **Kill the process or change the port in docker-compose.yml**

---

## Volume and Data Issues

### Issue: Data Not Persisting

**Symptoms:**
- Data lost after container restart
- Database empty after restart

**Solutions:**

1. **Check volumes exist:**
   ```bash
   docker volume ls | grep superinsight
   ```

2. **Inspect volume:**
   ```bash
   docker volume inspect superinsight-platform_postgres_data
   ```

3. **Verify volume mounts in docker-compose.yml**

### Issue: Permission Denied on Volumes

**Symptoms:**
- Cannot write to mounted volumes
- Permission errors in logs

**Solution:**

```bash
# Fix permissions (Linux/Mac)
sudo chown -R $(id -u):$(id -g) ./data

# Or use Docker to fix
docker run --rm -v superinsight-platform_postgres_data:/data alpine chown -R 999:999 /data
```

---

## Performance Issues

### Issue: Slow Container Startup

**Symptoms:**
- Containers take > 60 seconds to become healthy
- Health checks timeout

**Solutions:**

1. **Increase health check timeouts:**
   Edit `docker-compose.yml`:
   ```yaml
   healthcheck:
     interval: 30s
     timeout: 10s
     retries: 10
   ```

2. **Allocate more resources to Docker:**
   - Docker Desktop: Settings > Resources > Increase Memory/CPU

3. **Use SSD storage for Docker volumes**

### Issue: High Memory Usage

**Symptoms:**
- Containers being killed (OOMKilled)
- System slowdown

**Solutions:**

1. **Check container resource usage:**
   ```bash
   docker stats
   ```

2. **Set memory limits in docker-compose.yml:**
   ```yaml
   services:
     neo4j:
       deploy:
         resources:
           limits:
             memory: 1G
   ```

---

## Verification Scripts

The following scripts are available for automated verification:

### PostgreSQL Initialization Verification
```bash
./scripts/verify-postgres-init.sh
```
Validates:
- superinsight role exists
- Extensions are enabled
- Permissions are granted
- alembic_version table exists

### Health Check Verification
```bash
./scripts/verify-health-checks.sh
```
Validates:
- All container health checks pass
- Service endpoints respond correctly
- Health check configuration is correct

### Connectivity Verification
```bash
./scripts/verify-connectivity.sh
```
Validates:
- API can connect to PostgreSQL
- API can connect to Redis
- API can connect to Neo4j
- API can connect to Label Studio

### Generate Test Logs
```bash
./scripts/generate-test-logs.sh
```
Generates:
- Combined container logs
- Health check report (JSON)
- Startup time metrics
- Comprehensive test report

---

## Emergency Recovery

### Complete Reset (WARNING: Deletes All Data)

```bash
# Stop all containers
docker-compose down

# Remove all volumes
docker volume rm $(docker volume ls -q | grep superinsight)

# Remove all images
docker rmi $(docker images | grep superinsight | awk '{print $3}')

# Rebuild and start
docker-compose build --no-cache
docker-compose up -d
```

### Backup Before Reset

```bash
# Backup PostgreSQL
docker exec superinsight-postgres pg_dump -U superinsight superinsight > backup.sql

# Backup Redis
docker exec superinsight-redis redis-cli BGSAVE

# Backup Neo4j
docker exec superinsight-neo4j neo4j-admin dump --database=neo4j --to=/backup/neo4j.dump
```

---

## Getting Help

If you're still experiencing issues:

1. **Collect diagnostic information:**
   ```bash
   ./scripts/generate-test-logs.sh --full-logs
   ```

2. **Check the generated reports in `./docker-logs/`**

3. **Review the comprehensive deployment documentation:**
   - `DOCKER_DEPLOYMENT_COMPLETE.md`
   - `DEPLOYMENT.md`
   - `QUICK_START.md`

4. **Check the spec documentation:**
   - `.kiro/specs/docker-infrastructure/requirements.md`
   - `.kiro/specs/docker-infrastructure/design.md`

---

**Last Updated:** $(date +%Y-%m-%d)
**Spec Reference:** docker-infrastructure
**Validates:** Task 7.4 - Create troubleshooting guide
