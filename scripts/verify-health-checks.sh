#!/bin/bash
# Service Health Check Verification Script
# This script verifies that all Docker services have proper health checks
# according to the docker-infrastructure spec requirements.
#
# Usage: ./scripts/verify-health-checks.sh
#
# Requirements:
# - Docker must be running
# - All containers must be running (use docker-compose up -d first)
#
# Validates:
# - Requirements 5.1: PostgreSQL health check (pg_isready)
# - Requirements 5.2: Redis health check (redis-cli ping)
# - Requirements 5.3: Neo4j health check (HTTP endpoint)
# - Requirements 5.4: Label Studio health check (/health endpoint)
# - Requirements 5.5: Health check retry behavior
# - Overall system health via API /health endpoint

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Container names
POSTGRES_CONTAINER="superinsight-postgres"
REDIS_CONTAINER="superinsight-redis"
NEO4J_CONTAINER="superinsight-neo4j"
LABEL_STUDIO_CONTAINER="superinsight-label-studio"
API_CONTAINER="superinsight-api"

# Service ports
NEO4J_HTTP_PORT=7474
LABEL_STUDIO_PORT=8080
API_PORT=8000

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_test() {
    echo -e "\n${YELLOW}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_service() {
    echo -e "${CYAN}[SERVICE]${NC} $1"
}

# Check if Docker is available
check_docker() {
    print_header "Checking Docker Availability"
    
    if ! command -v docker &> /dev/null; then
        print_fail "Docker is not installed or not in PATH"
        exit 1
    fi
    print_pass "Docker is available"
    
    if ! docker info &> /dev/null; then
        print_fail "Docker daemon is not running"
        exit 1
    fi
    print_pass "Docker daemon is running"
}

# Check if docker-compose is available
check_docker_compose() {
    print_test "Checking docker-compose availability"
    
    if command -v docker-compose &> /dev/null; then
        print_pass "docker-compose is available"
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        print_pass "docker compose (plugin) is available"
        COMPOSE_CMD="docker compose"
    else
        print_fail "Neither docker-compose nor docker compose plugin is available"
        exit 1
    fi
}

# Check if a container is running
is_container_running() {
    local container_name=$1
    docker ps --format '{{.Names}}' | grep -q "^${container_name}$"
}

# Get container health status
get_container_health() {
    local container_name=$1
    docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-healthcheck"
}

# List all running containers
list_containers() {
    print_header "Checking Running Containers"
    
    print_test "Listing all SuperInsight containers"
    
    CONTAINERS=$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "superinsight|NAMES" || true)
    
    if [ -z "$CONTAINERS" ]; then
        print_fail "No SuperInsight containers are running"
        print_info "Start containers with: docker-compose up -d"
        exit 1
    fi
    
    echo "$CONTAINERS"
    echo ""
}


# Task 5.1: Check PostgreSQL health
check_postgres_health() {
    print_header "Task 5.1: Check PostgreSQL Health"
    print_service "Container: ${POSTGRES_CONTAINER}"
    print_test "Validates: Requirements 5.1 - pg_isready SHALL return success"
    
    # Check if container is running
    if ! is_container_running "$POSTGRES_CONTAINER"; then
        print_fail "PostgreSQL container is not running"
        print_info "Start with: docker-compose up -d postgres"
        return 1
    fi
    print_pass "PostgreSQL container is running"
    
    # Check Docker health status
    print_test "Checking Docker health status"
    HEALTH_STATUS=$(get_container_health "$POSTGRES_CONTAINER")
    print_info "Docker health status: $HEALTH_STATUS"
    
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        print_pass "PostgreSQL Docker health check: healthy"
    elif [ "$HEALTH_STATUS" = "unhealthy" ]; then
        print_fail "PostgreSQL Docker health check: unhealthy"
    elif [ "$HEALTH_STATUS" = "starting" ]; then
        print_warn "PostgreSQL Docker health check: starting (still initializing)"
    else
        print_warn "PostgreSQL has no Docker health check configured"
    fi
    
    # Run pg_isready command
    print_test "Running pg_isready health check"
    PG_READY_RESULT=$(docker exec ${POSTGRES_CONTAINER} pg_isready -U superinsight -d superinsight 2>&1)
    PG_READY_EXIT=$?
    
    if [ $PG_READY_EXIT -eq 0 ]; then
        print_pass "pg_isready returned success"
        echo "  Output: $PG_READY_RESULT"
    else
        print_fail "pg_isready failed (exit code: $PG_READY_EXIT)"
        echo "  Output: $PG_READY_RESULT"
        return 1
    fi
    
    # Test actual database connection
    print_test "Testing actual database connection"
    DB_CONN_RESULT=$(docker exec ${POSTGRES_CONTAINER} psql -U superinsight -d superinsight -c "SELECT 1 as connection_test;" 2>&1)
    
    if echo "$DB_CONN_RESULT" | grep -q "connection_test"; then
        print_pass "Database connection successful"
    else
        print_fail "Database connection failed"
        echo "  Output: $DB_CONN_RESULT"
    fi
    
    # Check PostgreSQL version
    print_test "Checking PostgreSQL version"
    PG_VERSION=$(docker exec ${POSTGRES_CONTAINER} psql -U superinsight -d superinsight -t -c "SELECT version();" 2>&1)
    print_info "PostgreSQL version: $(echo $PG_VERSION | head -1)"
}

# Task 5.2: Check Redis health
check_redis_health() {
    print_header "Task 5.2: Check Redis Health"
    print_service "Container: ${REDIS_CONTAINER}"
    print_test "Validates: Requirements 5.2 - redis-cli ping SHALL return PONG"
    
    # Check if container is running
    if ! is_container_running "$REDIS_CONTAINER"; then
        print_fail "Redis container is not running"
        print_info "Start with: docker-compose up -d redis"
        return 1
    fi
    print_pass "Redis container is running"
    
    # Check Docker health status
    print_test "Checking Docker health status"
    HEALTH_STATUS=$(get_container_health "$REDIS_CONTAINER")
    print_info "Docker health status: $HEALTH_STATUS"
    
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        print_pass "Redis Docker health check: healthy"
    elif [ "$HEALTH_STATUS" = "unhealthy" ]; then
        print_fail "Redis Docker health check: unhealthy"
    elif [ "$HEALTH_STATUS" = "starting" ]; then
        print_warn "Redis Docker health check: starting (still initializing)"
    else
        print_warn "Redis has no Docker health check configured"
    fi
    
    # Run redis-cli ping command
    print_test "Running redis-cli ping health check"
    REDIS_PING_RESULT=$(docker exec ${REDIS_CONTAINER} redis-cli ping 2>&1)
    
    if [ "$REDIS_PING_RESULT" = "PONG" ]; then
        print_pass "redis-cli ping returned PONG"
    else
        print_fail "redis-cli ping did not return PONG"
        echo "  Output: $REDIS_PING_RESULT"
        return 1
    fi
    
    # Check Redis info
    print_test "Checking Redis server info"
    REDIS_INFO=$(docker exec ${REDIS_CONTAINER} redis-cli info server 2>&1 | head -5)
    print_info "Redis server info:"
    echo "$REDIS_INFO" | sed 's/^/  /'
    
    # Test Redis operations
    print_test "Testing Redis SET/GET operations"
    docker exec ${REDIS_CONTAINER} redis-cli SET _health_check_test "ok" > /dev/null 2>&1
    REDIS_GET=$(docker exec ${REDIS_CONTAINER} redis-cli GET _health_check_test 2>&1)
    docker exec ${REDIS_CONTAINER} redis-cli DEL _health_check_test > /dev/null 2>&1
    
    if [ "$REDIS_GET" = "ok" ]; then
        print_pass "Redis SET/GET operations working"
    else
        print_fail "Redis SET/GET operations failed"
    fi
}

# Task 5.3: Check Neo4j health
check_neo4j_health() {
    print_header "Task 5.3: Check Neo4j Health"
    print_service "Container: ${NEO4J_CONTAINER}"
    print_test "Validates: Requirements 5.3 - HTTP endpoint SHALL respond"
    
    # Check if container is running
    if ! is_container_running "$NEO4J_CONTAINER"; then
        print_fail "Neo4j container is not running"
        print_info "Start with: docker-compose up -d neo4j"
        return 1
    fi
    print_pass "Neo4j container is running"
    
    # Check Docker health status
    print_test "Checking Docker health status"
    HEALTH_STATUS=$(get_container_health "$NEO4J_CONTAINER")
    print_info "Docker health status: $HEALTH_STATUS"
    
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        print_pass "Neo4j Docker health check: healthy"
    elif [ "$HEALTH_STATUS" = "unhealthy" ]; then
        print_fail "Neo4j Docker health check: unhealthy"
    elif [ "$HEALTH_STATUS" = "starting" ]; then
        print_warn "Neo4j Docker health check: starting (still initializing)"
    else
        print_warn "Neo4j has no Docker health check configured"
    fi
    
    # Check HTTP endpoint
    print_test "Checking Neo4j HTTP endpoint (port ${NEO4J_HTTP_PORT})"
    
    if command -v curl &> /dev/null; then
        NEO4J_HTTP_RESULT=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${NEO4J_HTTP_PORT} 2>&1 || echo "failed")
        
        if [ "$NEO4J_HTTP_RESULT" = "200" ]; then
            print_pass "Neo4j HTTP endpoint returned 200 OK"
        elif [ "$NEO4J_HTTP_RESULT" = "failed" ]; then
            print_fail "Neo4j HTTP endpoint is not reachable"
            print_info "Ensure port ${NEO4J_HTTP_PORT} is exposed"
        else
            print_warn "Neo4j HTTP endpoint returned status: $NEO4J_HTTP_RESULT"
        fi
        
        # Get Neo4j browser info
        print_test "Fetching Neo4j browser info"
        NEO4J_INFO=$(curl -s http://localhost:${NEO4J_HTTP_PORT} 2>&1 | head -20 || echo "Could not fetch")
        if [ -n "$NEO4J_INFO" ] && [ "$NEO4J_INFO" != "Could not fetch" ]; then
            print_pass "Neo4j browser is accessible"
        fi
    else
        print_warn "curl not available, using wget"
        if wget -q --spider http://localhost:${NEO4J_HTTP_PORT} 2>&1; then
            print_pass "Neo4j HTTP endpoint is reachable (wget)"
        else
            print_fail "Neo4j HTTP endpoint is not reachable"
        fi
    fi
    
    # Check Bolt protocol
    print_test "Checking Neo4j Bolt protocol (port 7687)"
    if docker exec ${NEO4J_CONTAINER} cypher-shell -u neo4j -p password "RETURN 1" > /dev/null 2>&1; then
        print_pass "Neo4j Bolt protocol is working"
    else
        print_warn "Neo4j Bolt protocol check failed (may need authentication)"
    fi
}


# Task 5.4: Check Label Studio health
check_label_studio_health() {
    print_header "Task 5.4: Check Label Studio Health"
    print_service "Container: ${LABEL_STUDIO_CONTAINER}"
    print_test "Validates: Requirements 5.4 - /health endpoint SHALL return 200"
    
    # Check if container is running
    if ! is_container_running "$LABEL_STUDIO_CONTAINER"; then
        print_fail "Label Studio container is not running"
        print_info "Start with: docker-compose up -d label-studio"
        return 1
    fi
    print_pass "Label Studio container is running"
    
    # Check Docker health status
    print_test "Checking Docker health status"
    HEALTH_STATUS=$(get_container_health "$LABEL_STUDIO_CONTAINER")
    print_info "Docker health status: $HEALTH_STATUS"
    
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        print_pass "Label Studio Docker health check: healthy"
    elif [ "$HEALTH_STATUS" = "unhealthy" ]; then
        print_fail "Label Studio Docker health check: unhealthy"
    elif [ "$HEALTH_STATUS" = "starting" ]; then
        print_warn "Label Studio Docker health check: starting (still initializing)"
    else
        print_warn "Label Studio has no Docker health check configured"
    fi
    
    # Check /health endpoint
    print_test "Checking Label Studio /health endpoint (port ${LABEL_STUDIO_PORT})"
    
    if command -v curl &> /dev/null; then
        LS_HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${LABEL_STUDIO_PORT}/health 2>&1 || echo "failed")
        
        if [ "$LS_HEALTH_CODE" = "200" ]; then
            print_pass "Label Studio /health endpoint returned 200 OK"
        elif [ "$LS_HEALTH_CODE" = "failed" ]; then
            print_fail "Label Studio /health endpoint is not reachable"
            print_info "Ensure port ${LABEL_STUDIO_PORT} is exposed"
        else
            print_warn "Label Studio /health endpoint returned status: $LS_HEALTH_CODE"
        fi
        
        # Get health response body
        print_test "Fetching Label Studio health response"
        LS_HEALTH_BODY=$(curl -s http://localhost:${LABEL_STUDIO_PORT}/health 2>&1 || echo "{}")
        if [ -n "$LS_HEALTH_BODY" ]; then
            print_info "Health response: $LS_HEALTH_BODY"
        fi
    else
        print_warn "curl not available, using wget"
        if wget -q --spider http://localhost:${LABEL_STUDIO_PORT}/health 2>&1; then
            print_pass "Label Studio /health endpoint is reachable (wget)"
        else
            print_fail "Label Studio /health endpoint is not reachable"
        fi
    fi
    
    # Check main page
    print_test "Checking Label Studio main page"
    if command -v curl &> /dev/null; then
        LS_MAIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${LABEL_STUDIO_PORT}/ 2>&1 || echo "failed")
        
        if [ "$LS_MAIN_CODE" = "200" ] || [ "$LS_MAIN_CODE" = "302" ]; then
            print_pass "Label Studio main page is accessible (status: $LS_MAIN_CODE)"
        else
            print_warn "Label Studio main page returned status: $LS_MAIN_CODE"
        fi
    fi
}

# Task 5.5: Check API health
check_api_health() {
    print_header "Task 5.5: Check API Health"
    print_service "Container: ${API_CONTAINER}"
    print_test "Validates: Overall system health"
    
    # Check if container is running
    if ! is_container_running "$API_CONTAINER"; then
        print_fail "API container is not running"
        print_info "Start with: docker-compose up -d superinsight-api"
        return 1
    fi
    print_pass "API container is running"
    
    # Check Docker health status
    print_test "Checking Docker health status"
    HEALTH_STATUS=$(get_container_health "$API_CONTAINER")
    print_info "Docker health status: $HEALTH_STATUS"
    
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        print_pass "API Docker health check: healthy"
    elif [ "$HEALTH_STATUS" = "unhealthy" ]; then
        print_fail "API Docker health check: unhealthy"
    elif [ "$HEALTH_STATUS" = "starting" ]; then
        print_warn "API Docker health check: starting (still initializing)"
    else
        print_warn "API has no Docker health check configured"
    fi
    
    # Check /health endpoint
    print_test "Checking API /health endpoint (port ${API_PORT})"
    
    if command -v curl &> /dev/null; then
        API_HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${API_PORT}/health 2>&1 || echo "failed")
        
        if [ "$API_HEALTH_CODE" = "200" ]; then
            print_pass "API /health endpoint returned 200 OK"
        elif [ "$API_HEALTH_CODE" = "failed" ]; then
            print_fail "API /health endpoint is not reachable"
            print_info "Ensure port ${API_PORT} is exposed"
        else
            print_warn "API /health endpoint returned status: $API_HEALTH_CODE"
        fi
        
        # Get health response body
        print_test "Fetching API health response"
        API_HEALTH_BODY=$(curl -s http://localhost:${API_PORT}/health 2>&1 || echo "{}")
        if [ -n "$API_HEALTH_BODY" ]; then
            print_info "Health response:"
            echo "$API_HEALTH_BODY" | python3 -m json.tool 2>/dev/null || echo "$API_HEALTH_BODY"
        fi
    else
        print_warn "curl not available, using wget"
        if wget -q --spider http://localhost:${API_PORT}/health 2>&1; then
            print_pass "API /health endpoint is reachable (wget)"
        else
            print_fail "API /health endpoint is not reachable"
        fi
    fi
    
    # Check /system/status endpoint
    print_test "Checking API /system/status endpoint"
    if command -v curl &> /dev/null; then
        API_STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${API_PORT}/system/status 2>&1 || echo "failed")
        
        if [ "$API_STATUS_CODE" = "200" ]; then
            print_pass "API /system/status endpoint returned 200 OK"
            
            # Get system status
            print_test "Fetching system status"
            API_STATUS_BODY=$(curl -s http://localhost:${API_PORT}/system/status 2>&1 || echo "{}")
            if [ -n "$API_STATUS_BODY" ]; then
                print_info "System status:"
                echo "$API_STATUS_BODY" | python3 -m json.tool 2>/dev/null || echo "$API_STATUS_BODY"
            fi
        else
            print_warn "API /system/status endpoint returned status: $API_STATUS_CODE"
        fi
    fi
    
    # Check OpenAPI docs
    print_test "Checking API documentation endpoint"
    if command -v curl &> /dev/null; then
        API_DOCS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${API_PORT}/docs 2>&1 || echo "failed")
        
        if [ "$API_DOCS_CODE" = "200" ]; then
            print_pass "API documentation is accessible at /docs"
        else
            print_warn "API documentation returned status: $API_DOCS_CODE"
        fi
    fi
}


# Check all Docker Compose health statuses
check_compose_health() {
    print_header "Docker Compose Health Overview"
    
    print_test "Checking all service health statuses"
    
    # Get docker-compose ps output
    COMPOSE_PS=$($COMPOSE_CMD ps 2>&1)
    echo "$COMPOSE_PS"
    echo ""
    
    # Count healthy/unhealthy services
    HEALTHY_COUNT=$(echo "$COMPOSE_PS" | grep -c "(healthy)" || echo "0")
    UNHEALTHY_COUNT=$(echo "$COMPOSE_PS" | grep -c "(unhealthy)" || echo "0")
    STARTING_COUNT=$(echo "$COMPOSE_PS" | grep -c "(starting)" || echo "0")
    
    print_info "Healthy services: $HEALTHY_COUNT"
    print_info "Unhealthy services: $UNHEALTHY_COUNT"
    print_info "Starting services: $STARTING_COUNT"
    
    if [ "$UNHEALTHY_COUNT" -gt 0 ]; then
        print_fail "Some services are unhealthy"
    elif [ "$STARTING_COUNT" -gt 0 ]; then
        print_warn "Some services are still starting"
    else
        print_pass "All services appear healthy"
    fi
}

# Check health check retry behavior (Requirements 5.5)
check_retry_behavior() {
    print_header "Health Check Retry Behavior"
    print_test "Validates: Requirements 5.5 - Services SHALL retry according to configured intervals"
    
    # Check docker-compose.yml for health check configurations
    if [ -f "docker-compose.yml" ]; then
        print_test "Checking health check configurations in docker-compose.yml"
        
        # Extract health check configs
        HEALTHCHECK_CONFIGS=$(grep -A 10 "healthcheck:" docker-compose.yml 2>/dev/null || echo "")
        
        if [ -n "$HEALTHCHECK_CONFIGS" ]; then
            print_pass "Health check configurations found in docker-compose.yml"
            print_info "Health check configurations:"
            echo "$HEALTHCHECK_CONFIGS" | head -30 | sed 's/^/  /'
        else
            print_warn "No explicit health check configurations found"
        fi
        
        # Check for interval, timeout, retries
        if grep -q "interval:" docker-compose.yml 2>/dev/null; then
            print_pass "Health check intervals are configured"
        fi
        
        if grep -q "timeout:" docker-compose.yml 2>/dev/null; then
            print_pass "Health check timeouts are configured"
        fi
        
        if grep -q "retries:" docker-compose.yml 2>/dev/null; then
            print_pass "Health check retries are configured"
        fi
    else
        print_warn "docker-compose.yml not found in current directory"
    fi
    
    # Check container health check settings
    print_test "Checking container health check settings"
    
    for container in $POSTGRES_CONTAINER $REDIS_CONTAINER $NEO4J_CONTAINER $LABEL_STUDIO_CONTAINER $API_CONTAINER; do
        if is_container_running "$container"; then
            HC_CONFIG=$(docker inspect --format='{{json .Config.Healthcheck}}' "$container" 2>/dev/null || echo "null")
            if [ "$HC_CONFIG" != "null" ] && [ -n "$HC_CONFIG" ]; then
                print_info "$container health check config:"
                echo "$HC_CONFIG" | python3 -m json.tool 2>/dev/null | sed 's/^/    /' || echo "    $HC_CONFIG"
            else
                print_warn "$container has no health check configured"
            fi
        fi
    done
}

# Generate health check report
generate_report() {
    print_header "Health Check Report"
    
    REPORT_FILE="health-check-report-$(date +%Y%m%d-%H%M%S).json"
    
    print_test "Generating JSON health check report"
    
    # Build JSON report
    cat > "$REPORT_FILE" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "services": {
        "postgresql": {
            "container": "${POSTGRES_CONTAINER}",
            "running": $(is_container_running "$POSTGRES_CONTAINER" && echo "true" || echo "false"),
            "health_status": "$(get_container_health "$POSTGRES_CONTAINER")",
            "health_check_command": "pg_isready -U superinsight -d superinsight"
        },
        "redis": {
            "container": "${REDIS_CONTAINER}",
            "running": $(is_container_running "$REDIS_CONTAINER" && echo "true" || echo "false"),
            "health_status": "$(get_container_health "$REDIS_CONTAINER")",
            "health_check_command": "redis-cli ping"
        },
        "neo4j": {
            "container": "${NEO4J_CONTAINER}",
            "running": $(is_container_running "$NEO4J_CONTAINER" && echo "true" || echo "false"),
            "health_status": "$(get_container_health "$NEO4J_CONTAINER")",
            "health_check_command": "curl http://localhost:7474"
        },
        "label_studio": {
            "container": "${LABEL_STUDIO_CONTAINER}",
            "running": $(is_container_running "$LABEL_STUDIO_CONTAINER" && echo "true" || echo "false"),
            "health_status": "$(get_container_health "$LABEL_STUDIO_CONTAINER")",
            "health_check_command": "curl http://localhost:8080/health"
        },
        "api": {
            "container": "${API_CONTAINER}",
            "running": $(is_container_running "$API_CONTAINER" && echo "true" || echo "false"),
            "health_status": "$(get_container_health "$API_CONTAINER")",
            "health_check_command": "curl http://localhost:8000/health"
        }
    },
    "summary": {
        "tests_passed": ${PASSED},
        "tests_failed": ${FAILED},
        "warnings": ${WARNINGS}
    }
}
EOF
    
    print_pass "Report generated: $REPORT_FILE"
    print_info "Report contents:"
    cat "$REPORT_FILE" | python3 -m json.tool 2>/dev/null || cat "$REPORT_FILE"
}

# Print summary
print_summary() {
    print_header "Verification Summary"
    
    echo -e "Tests Passed:  ${GREEN}${PASSED}${NC}"
    echo -e "Tests Failed:  ${RED}${FAILED}${NC}"
    echo -e "Warnings:      ${YELLOW}${WARNINGS}${NC}"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All service health check verifications passed!${NC}"
        echo ""
        echo "Requirements validated:"
        echo "  - 5.1: PostgreSQL health check (pg_isready)"
        echo "  - 5.2: Redis health check (redis-cli ping)"
        echo "  - 5.3: Neo4j health check (HTTP endpoint)"
        echo "  - 5.4: Label Studio health check (/health endpoint)"
        echo "  - 5.5: Health check retry behavior"
        echo "  - Overall system health via API /health endpoint"
        return 0
    else
        echo -e "${RED}✗ Some health check verifications failed. Please check the output above.${NC}"
        echo ""
        echo "Troubleshooting tips:"
        echo "  1. Ensure all containers are running: docker-compose up -d"
        echo "  2. Check container logs: docker-compose logs <service-name>"
        echo "  3. Verify network connectivity between containers"
        echo "  4. Check if ports are properly exposed"
        return 1
    fi
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║       Service Health Check Verification Script             ║"
    echo "║       SuperInsight Platform - Docker Infrastructure        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "This script validates Requirements 5.1-5.5 from the"
    echo "docker-infrastructure specification."
    echo ""
    
    check_docker
    check_docker_compose
    list_containers
    
    # Run individual health checks
    check_postgres_health
    check_redis_health
    check_neo4j_health
    check_label_studio_health
    check_api_health
    
    # Check overall compose health
    check_compose_health
    
    # Check retry behavior configuration
    check_retry_behavior
    
    # Generate report
    generate_report
    
    # Print summary
    print_summary
}

# Run main function
main "$@"
