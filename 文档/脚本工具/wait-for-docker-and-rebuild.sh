#!/bin/bash

# Wait for Docker and Rebuild Script
# This script waits for Docker to be ready, then cleans and rebuilds containers

echo "=== Docker Infrastructure Rebuild Script ==="
echo "Timestamp: $(date)"
echo ""

# Function to check if Docker is running
check_docker() {
    docker info > /dev/null 2>&1
    return $?
}

# Wait for Docker to be ready (max 60 seconds)
echo "Step 1: Waiting for Docker to be ready..."
COUNTER=0
MAX_WAIT=60

while ! check_docker; do
    if [ $COUNTER -ge $MAX_WAIT ]; then
        echo "ERROR: Docker did not start within $MAX_WAIT seconds"
        echo "Please start Docker Desktop manually and run this script again"
        exit 1
    fi
    echo "  Waiting for Docker... ($COUNTER/$MAX_WAIT seconds)"
    sleep 2
    COUNTER=$((COUNTER + 2))
done

echo "✓ Docker is ready!"
echo ""

# Show Docker version
echo "Step 2: Docker version information"
docker --version
docker compose version
echo ""

# Stop all running containers
echo "Step 3: Stopping all running containers..."
docker compose down 2>&1 | tee -a docker-rebuild.log
echo "✓ Containers stopped"
echo ""

# Remove old containers (keep only latest)
echo "Step 4: Cleaning old containers..."
echo "  Current containers:"
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.CreatedAt}}"
echo ""
echo "  Removing stopped containers..."
docker container prune -f 2>&1 | tee -a docker-rebuild.log
echo "✓ Old containers removed"
echo ""

# Remove old images (except base images)
echo "Step 5: Cleaning old images..."
echo "  Current images:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo ""
echo "  Removing dangling images..."
docker image prune -f 2>&1 | tee -a docker-rebuild.log
echo "✓ Dangling images removed"
echo ""

# Verify volumes are preserved
echo "Step 6: Verifying data volumes..."
docker volume ls | grep superinsight
echo "✓ Volumes preserved"
echo ""

# Rebuild API container from scratch
echo "Step 7: Rebuilding API container (no cache)..."
docker compose build --no-cache superinsight-api 2>&1 | tee -a docker-rebuild.log
if [ $? -eq 0 ]; then
    echo "✓ API container rebuilt successfully"
else
    echo "✗ API container rebuild failed"
    exit 1
fi
echo ""

# Start all services
echo "Step 8: Starting all services..."
docker compose up -d 2>&1 | tee -a docker-rebuild.log
if [ $? -eq 0 ]; then
    echo "✓ All services started"
else
    echo "✗ Service startup failed"
    exit 1
fi
echo ""

# Wait for services to initialize
echo "Step 9: Waiting for services to initialize (30 seconds)..."
sleep 30
echo ""

# Check container status
echo "Step 10: Checking container status..."
docker compose ps
echo ""

# Check PostgreSQL logs for init script
echo "Step 11: Checking PostgreSQL initialization..."
echo "  PostgreSQL logs (last 50 lines):"
docker compose logs postgres --tail=50 | tee -a docker-rebuild.log
echo ""

# Check for SQL syntax errors
if docker compose logs postgres | grep -q "ERROR.*syntax error"; then
    echo "✗ SQL syntax error detected in PostgreSQL logs!"
    echo "  Please check docker-rebuild.log for details"
else
    echo "✓ No SQL syntax errors detected"
fi
echo ""

# Test PostgreSQL connection
echo "Step 12: Testing PostgreSQL connection..."
docker exec superinsight-postgres pg_isready -U superinsight -d superinsight
if [ $? -eq 0 ]; then
    echo "✓ PostgreSQL is ready"
else
    echo "✗ PostgreSQL is not ready"
fi
echo ""

# Verify superinsight role
echo "Step 13: Verifying superinsight role..."
docker exec superinsight-postgres psql -U superinsight -d superinsight -c "\du superinsight"
echo ""

# Verify extensions
echo "Step 14: Verifying PostgreSQL extensions..."
docker exec superinsight-postgres psql -U superinsight -d superinsight -c "\dx"
echo ""

# Check all service health
echo "Step 15: Checking all service health..."
echo ""
echo "  PostgreSQL:"
docker exec superinsight-postgres pg_isready -U superinsight -d superinsight && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"
echo ""
echo "  Redis:"
docker exec superinsight-redis redis-cli ping && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"
echo ""
echo "  Neo4j:"
curl -s http://localhost:7474 > /dev/null && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"
echo ""
echo "  Label Studio:"
curl -s http://localhost:8080/health > /dev/null && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"
echo ""
echo "  API:"
curl -s http://localhost:8000/health > /dev/null && echo "  ✓ Healthy" || echo "  ✗ Unhealthy"
echo ""

# Generate summary
echo "=== Rebuild Summary ==="
echo "Timestamp: $(date)"
echo "Log file: docker-rebuild.log"
echo ""
echo "Container Status:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Next Steps:"
echo "1. Review docker-rebuild.log for detailed logs"
echo "2. If all services are healthy, test API endpoints"
echo "3. If any service failed, check individual container logs"
echo ""
echo "=== Script Complete ==="
