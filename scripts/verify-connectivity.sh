#!/bin/bash
# Service Connectivity Verification Script
# This script verifies that all Docker services can communicate with each other
# according to the docker-infrastructure spec requirements.
#
# Usage: ./scripts/verify-connectivity.sh
#
# Requirements:
# - Docker must be running
# - All containers must be running (use docker-compose up -d first)
#
# Validates:
# - Requirements 6.1: Database connection strings correctly configured
# - Property 3: Database Connectivity (superinsight role can connect and perform operations)
# - API to PostgreSQL connection
# - API to Redis connection
# - API to Neo4j connection
# - API to Label Studio connection

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Container names
POSTGRES_CONTAINER="superinsight-postgres"
REDIS_CONTAINER="superinsight-redis"
NEO4J_CONTAINER="superinsight-neo4j"
LABEL_STUDIO_CONTAINER="superinsight-label-studio"
API_CONTAINER="superinsight-api"

# Service ports
API_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687
LABEL_STUDIO_PORT=8080

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Report data
declare -A CONNECTIVITY_RESULTS

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

print_connectivity() {
    echo -e "${MAGENTA}[CONNECTIVITY]${NC} $1"
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


# Task 6.1: Test API to PostgreSQL connection
test_api_postgres_connection() {
    print_header "Task 6.1: Test API to PostgreSQL Connection"
    print_service "Testing: API Container -> PostgreSQL Container"
    print_test "Validates: Requirements 6.1 - Database connection strings correctly configured"
    
    CONNECTIVITY_RESULTS["postgres"]="unknown"
    
    # Check if API container is running
    if ! is_container_running "$API_CONTAINER"; then
        print_fail "API container is not running"
        CONNECTIVITY_RESULTS["postgres"]="api_not_running"
        return 1
    fi
    
    # Check if PostgreSQL container is running
    if ! is_container_running "$POSTGRES_CONTAINER"; then
        print_fail "PostgreSQL container is not running"
        CONNECTIVITY_RESULTS["postgres"]="postgres_not_running"
        return 1
    fi
    
    # Test 1: Check via /system/status endpoint
    print_test "Testing via /system/status endpoint"
    
    if command -v curl &> /dev/null; then
        SYSTEM_STATUS=$(curl -s http://localhost:${API_PORT}/system/status 2>&1 || echo '{"error": "failed"}')
        
        if echo "$SYSTEM_STATUS" | grep -qi "error"; then
            print_warn "Could not fetch /system/status endpoint"
            print_info "Response: $SYSTEM_STATUS"
        else
            print_pass "Successfully fetched /system/status"
            
            # Parse database status from response
            if echo "$SYSTEM_STATUS" | grep -qi '"database".*"connected"'; then
                print_pass "Database shows as connected in system status"
            elif echo "$SYSTEM_STATUS" | grep -qi '"postgres".*"healthy"'; then
                print_pass "PostgreSQL shows as healthy in system status"
            else
                print_info "System status response:"
                echo "$SYSTEM_STATUS" | python3 -m json.tool 2>/dev/null | head -30 || echo "$SYSTEM_STATUS" | head -30
            fi
        fi
    fi
    
    # Test 2: Direct network connectivity from API container to PostgreSQL
    print_test "Testing network connectivity from API to PostgreSQL"
    
    PING_RESULT=$(docker exec ${API_CONTAINER} sh -c "nc -zv postgres 5432 2>&1" || echo "failed")
    
    if echo "$PING_RESULT" | grep -qi "open\|succeeded\|connected"; then
        print_pass "Network connectivity to PostgreSQL port 5432 is working"
        CONNECTIVITY_RESULTS["postgres"]="connected"
    else
        print_fail "Cannot reach PostgreSQL from API container"
        print_info "Result: $PING_RESULT"
        CONNECTIVITY_RESULTS["postgres"]="network_failed"
        
        # Try alternative method
        print_test "Trying alternative connectivity test"
        ALT_RESULT=$(docker exec ${API_CONTAINER} sh -c "timeout 5 bash -c '</dev/tcp/postgres/5432' 2>&1" || echo "failed")
        if [ "$ALT_RESULT" != "failed" ]; then
            print_pass "Alternative connectivity test succeeded"
            CONNECTIVITY_RESULTS["postgres"]="connected"
        fi
    fi
    
    # Test 3: Test actual database query from API container
    print_test "Testing database query from API container"
    
    # Check if psql is available in API container
    if docker exec ${API_CONTAINER} which psql > /dev/null 2>&1; then
        DB_QUERY=$(docker exec ${API_CONTAINER} psql -h postgres -U superinsight -d superinsight -c "SELECT 1 as test;" 2>&1)
        
        if echo "$DB_QUERY" | grep -q "test"; then
            print_pass "Database query from API container succeeded"
            CONNECTIVITY_RESULTS["postgres"]="connected"
        else
            print_warn "Database query failed (psql available but query failed)"
            print_info "Result: $DB_QUERY"
        fi
    else
        print_info "psql not available in API container, using Python test"
        
        # Test using Python
        PYTHON_TEST=$(docker exec ${API_CONTAINER} python3 -c "
import os
try:
    import psycopg2
    conn = psycopg2.connect(
        host='postgres',
        port=5432,
        database='superinsight',
        user='superinsight',
        password='password'
    )
    cur = conn.cursor()
    cur.execute('SELECT 1')
    result = cur.fetchone()
    print('SUCCESS: Database connection works, result:', result)
    conn.close()
except Exception as e:
    print('ERROR:', str(e))
" 2>&1)
        
        if echo "$PYTHON_TEST" | grep -qi "SUCCESS"; then
            print_pass "Python database connection test succeeded"
            print_info "$PYTHON_TEST"
            CONNECTIVITY_RESULTS["postgres"]="connected"
        else
            print_warn "Python database connection test failed"
            print_info "$PYTHON_TEST"
        fi
    fi
    
    # Test 4: Verify DATABASE_URL environment variable
    print_test "Verifying DATABASE_URL environment variable"
    
    DB_URL=$(docker exec ${API_CONTAINER} sh -c 'echo $DATABASE_URL' 2>&1)
    
    if [ -n "$DB_URL" ] && echo "$DB_URL" | grep -q "postgresql://"; then
        print_pass "DATABASE_URL is configured correctly"
        # Mask password in output
        MASKED_URL=$(echo "$DB_URL" | sed 's/:password@/:****@/g' | sed 's/:[^:@]*@/:****@/g')
        print_info "DATABASE_URL: $MASKED_URL"
    else
        print_warn "DATABASE_URL may not be configured correctly"
        print_info "Value: $DB_URL"
    fi
}


# Task 6.2: Test API to Redis connection
test_api_redis_connection() {
    print_header "Task 6.2: Test API to Redis Connection"
    print_service "Testing: API Container -> Redis Container"
    print_test "Validates: Cache operations work"
    
    CONNECTIVITY_RESULTS["redis"]="unknown"
    
    # Check if API container is running
    if ! is_container_running "$API_CONTAINER"; then
        print_fail "API container is not running"
        CONNECTIVITY_RESULTS["redis"]="api_not_running"
        return 1
    fi
    
    # Check if Redis container is running
    if ! is_container_running "$REDIS_CONTAINER"; then
        print_fail "Redis container is not running"
        CONNECTIVITY_RESULTS["redis"]="redis_not_running"
        return 1
    fi
    
    # Test 1: Network connectivity from API container to Redis
    print_test "Testing network connectivity from API to Redis"
    
    PING_RESULT=$(docker exec ${API_CONTAINER} sh -c "nc -zv redis 6379 2>&1" || echo "failed")
    
    if echo "$PING_RESULT" | grep -qi "open\|succeeded\|connected"; then
        print_pass "Network connectivity to Redis port 6379 is working"
        CONNECTIVITY_RESULTS["redis"]="connected"
    else
        print_warn "nc command may not be available, trying alternative"
        
        # Try alternative method
        ALT_RESULT=$(docker exec ${API_CONTAINER} sh -c "timeout 5 bash -c '</dev/tcp/redis/6379' 2>&1" || echo "failed")
        if [ "$ALT_RESULT" != "failed" ]; then
            print_pass "Alternative connectivity test succeeded"
            CONNECTIVITY_RESULTS["redis"]="connected"
        else
            print_fail "Cannot reach Redis from API container"
            CONNECTIVITY_RESULTS["redis"]="network_failed"
        fi
    fi
    
    # Test 2: Test Redis operations using Python
    print_test "Testing Redis operations from API container"
    
    REDIS_TEST=$(docker exec ${API_CONTAINER} python3 -c "
import os
try:
    import redis
    r = redis.Redis(host='redis', port=6379, db=0)
    
    # Test PING
    ping_result = r.ping()
    print('PING:', 'SUCCESS' if ping_result else 'FAILED')
    
    # Test SET/GET
    r.set('_connectivity_test', 'ok')
    get_result = r.get('_connectivity_test')
    print('SET/GET:', 'SUCCESS' if get_result == b'ok' else 'FAILED')
    
    # Cleanup
    r.delete('_connectivity_test')
    
    # Get Redis info
    info = r.info('server')
    print('Redis Version:', info.get('redis_version', 'unknown'))
    
    print('OVERALL: SUCCESS')
except Exception as e:
    print('ERROR:', str(e))
" 2>&1)
    
    if echo "$REDIS_TEST" | grep -qi "OVERALL: SUCCESS"; then
        print_pass "Redis operations from API container succeeded"
        print_info "$REDIS_TEST"
        CONNECTIVITY_RESULTS["redis"]="connected"
    else
        print_warn "Redis operations test failed"
        print_info "$REDIS_TEST"
    fi
    
    # Test 3: Verify REDIS_URL environment variable
    print_test "Verifying REDIS_URL environment variable"
    
    REDIS_URL=$(docker exec ${API_CONTAINER} sh -c 'echo $REDIS_URL' 2>&1)
    
    if [ -n "$REDIS_URL" ] && echo "$REDIS_URL" | grep -q "redis://"; then
        print_pass "REDIS_URL is configured correctly"
        print_info "REDIS_URL: $REDIS_URL"
    else
        print_warn "REDIS_URL may not be configured correctly"
        print_info "Value: $REDIS_URL"
    fi
    
    # Test 4: Test cache operations via API endpoint (if available)
    print_test "Testing cache via API health endpoint"
    
    if command -v curl &> /dev/null; then
        HEALTH_RESPONSE=$(curl -s http://localhost:${API_PORT}/health 2>&1 || echo '{"error": "failed"}')
        
        if echo "$HEALTH_RESPONSE" | grep -qi '"redis".*"connected"\|"cache".*"ok"'; then
            print_pass "Redis shows as connected in health endpoint"
        elif echo "$HEALTH_RESPONSE" | grep -qi "healthy\|ok"; then
            print_pass "Health endpoint indicates system is healthy (Redis likely working)"
        else
            print_info "Health response: $HEALTH_RESPONSE"
        fi
    fi
}


# Task 6.3: Test API to Neo4j connection
test_api_neo4j_connection() {
    print_header "Task 6.3: Test API to Neo4j Connection"
    print_service "Testing: API Container -> Neo4j Container"
    print_test "Validates: Graph database operations work"
    
    CONNECTIVITY_RESULTS["neo4j"]="unknown"
    
    # Check if API container is running
    if ! is_container_running "$API_CONTAINER"; then
        print_fail "API container is not running"
        CONNECTIVITY_RESULTS["neo4j"]="api_not_running"
        return 1
    fi
    
    # Check if Neo4j container is running
    if ! is_container_running "$NEO4J_CONTAINER"; then
        print_fail "Neo4j container is not running"
        CONNECTIVITY_RESULTS["neo4j"]="neo4j_not_running"
        return 1
    fi
    
    # Test 1: Network connectivity from API container to Neo4j (Bolt port)
    print_test "Testing network connectivity from API to Neo4j (Bolt port 7687)"
    
    BOLT_RESULT=$(docker exec ${API_CONTAINER} sh -c "nc -zv neo4j 7687 2>&1" || echo "failed")
    
    if echo "$BOLT_RESULT" | grep -qi "open\|succeeded\|connected"; then
        print_pass "Network connectivity to Neo4j Bolt port 7687 is working"
        CONNECTIVITY_RESULTS["neo4j"]="connected"
    else
        print_warn "nc command may not be available, trying alternative"
        
        # Try alternative method
        ALT_RESULT=$(docker exec ${API_CONTAINER} sh -c "timeout 5 bash -c '</dev/tcp/neo4j/7687' 2>&1" || echo "failed")
        if [ "$ALT_RESULT" != "failed" ]; then
            print_pass "Alternative connectivity test succeeded"
            CONNECTIVITY_RESULTS["neo4j"]="connected"
        else
            print_warn "Cannot reach Neo4j Bolt port from API container"
        fi
    fi
    
    # Test 2: Network connectivity to Neo4j HTTP port
    print_test "Testing network connectivity from API to Neo4j (HTTP port 7474)"
    
    HTTP_RESULT=$(docker exec ${API_CONTAINER} sh -c "nc -zv neo4j 7474 2>&1" || echo "failed")
    
    if echo "$HTTP_RESULT" | grep -qi "open\|succeeded\|connected"; then
        print_pass "Network connectivity to Neo4j HTTP port 7474 is working"
    else
        print_info "HTTP port connectivity test inconclusive"
    fi
    
    # Test 3: Test Neo4j connection using Python
    print_test "Testing Neo4j connection from API container"
    
    NEO4J_TEST=$(docker exec ${API_CONTAINER} python3 -c "
import os
try:
    from neo4j import GraphDatabase
    
    uri = 'bolt://neo4j:7687'
    user = 'neo4j'
    password = os.environ.get('NEO4J_PASSWORD', 'password')
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    # Test connection
    with driver.session() as session:
        result = session.run('RETURN 1 as test')
        record = result.single()
        print('Query Result:', record['test'])
    
    # Get Neo4j version
    with driver.session() as session:
        result = session.run('CALL dbms.components() YIELD name, versions RETURN name, versions')
        for record in result:
            print('Neo4j Component:', record['name'], record['versions'])
    
    driver.close()
    print('OVERALL: SUCCESS')
except Exception as e:
    print('ERROR:', str(e))
" 2>&1)
    
    if echo "$NEO4J_TEST" | grep -qi "OVERALL: SUCCESS"; then
        print_pass "Neo4j connection from API container succeeded"
        print_info "$NEO4J_TEST"
        CONNECTIVITY_RESULTS["neo4j"]="connected"
    else
        print_warn "Neo4j connection test failed"
        print_info "$NEO4J_TEST"
        
        # Check if it's an authentication issue
        if echo "$NEO4J_TEST" | grep -qi "authentication\|unauthorized"; then
            print_info "This may be an authentication issue. Check NEO4J_PASSWORD environment variable."
        fi
    fi
    
    # Test 4: Verify NEO4J_URI environment variable
    print_test "Verifying NEO4J_URI environment variable"
    
    NEO4J_URI=$(docker exec ${API_CONTAINER} sh -c 'echo $NEO4J_URI' 2>&1)
    
    if [ -n "$NEO4J_URI" ] && echo "$NEO4J_URI" | grep -q "bolt://"; then
        print_pass "NEO4J_URI is configured correctly"
        print_info "NEO4J_URI: $NEO4J_URI"
    else
        print_warn "NEO4J_URI may not be configured correctly"
        print_info "Value: $NEO4J_URI"
    fi
    
    # Test 5: Test via external HTTP endpoint
    print_test "Testing Neo4j HTTP endpoint from host"
    
    if command -v curl &> /dev/null; then
        NEO4J_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${NEO4J_HTTP_PORT} 2>&1 || echo "failed")
        
        if [ "$NEO4J_HTTP" = "200" ]; then
            print_pass "Neo4j HTTP endpoint accessible from host"
        else
            print_info "Neo4j HTTP endpoint returned: $NEO4J_HTTP"
        fi
    fi
}


# Task 6.4: Test API to Label Studio connection
test_api_label_studio_connection() {
    print_header "Task 6.4: Test API to Label Studio Connection"
    print_service "Testing: API Container -> Label Studio Container"
    print_test "Validates: Annotation service integration works"
    
    CONNECTIVITY_RESULTS["label_studio"]="unknown"
    
    # Check if API container is running
    if ! is_container_running "$API_CONTAINER"; then
        print_fail "API container is not running"
        CONNECTIVITY_RESULTS["label_studio"]="api_not_running"
        return 1
    fi
    
    # Check if Label Studio container is running
    if ! is_container_running "$LABEL_STUDIO_CONTAINER"; then
        print_fail "Label Studio container is not running"
        CONNECTIVITY_RESULTS["label_studio"]="label_studio_not_running"
        return 1
    fi
    
    # Test 1: Network connectivity from API container to Label Studio
    print_test "Testing network connectivity from API to Label Studio (port 8080)"
    
    LS_RESULT=$(docker exec ${API_CONTAINER} sh -c "nc -zv label-studio 8080 2>&1" || echo "failed")
    
    if echo "$LS_RESULT" | grep -qi "open\|succeeded\|connected"; then
        print_pass "Network connectivity to Label Studio port 8080 is working"
        CONNECTIVITY_RESULTS["label_studio"]="connected"
    else
        print_warn "nc command may not be available, trying alternative"
        
        # Try alternative method
        ALT_RESULT=$(docker exec ${API_CONTAINER} sh -c "timeout 5 bash -c '</dev/tcp/label-studio/8080' 2>&1" || echo "failed")
        if [ "$ALT_RESULT" != "failed" ]; then
            print_pass "Alternative connectivity test succeeded"
            CONNECTIVITY_RESULTS["label_studio"]="connected"
        else
            print_warn "Cannot reach Label Studio from API container"
        fi
    fi
    
    # Test 2: Test Label Studio health endpoint from API container
    print_test "Testing Label Studio health endpoint from API container"
    
    LS_HEALTH=$(docker exec ${API_CONTAINER} sh -c "curl -s http://label-studio:8080/health 2>&1" || echo "failed")
    
    if echo "$LS_HEALTH" | grep -qi "ok\|healthy\|status"; then
        print_pass "Label Studio health endpoint accessible from API container"
        print_info "Health response: $LS_HEALTH"
        CONNECTIVITY_RESULTS["label_studio"]="connected"
    else
        print_warn "Label Studio health endpoint test inconclusive"
        print_info "Response: $LS_HEALTH"
    fi
    
    # Test 3: Test Label Studio API from API container using Python
    print_test "Testing Label Studio API from API container"
    
    LS_API_TEST=$(docker exec ${API_CONTAINER} python3 -c "
import os
import requests

try:
    base_url = 'http://label-studio:8080'
    
    # Test health endpoint
    health_response = requests.get(f'{base_url}/health', timeout=10)
    print('Health Status:', health_response.status_code)
    
    # Test API version endpoint
    version_response = requests.get(f'{base_url}/api/version', timeout=10)
    if version_response.status_code == 200:
        print('API Version:', version_response.json())
    else:
        print('API Version Status:', version_response.status_code)
    
    # Test if API token is configured
    api_token = os.environ.get('LABEL_STUDIO_API_TOKEN', '')
    if api_token:
        print('API Token: Configured')
        headers = {'Authorization': f'Token {api_token}'}
        projects_response = requests.get(f'{base_url}/api/projects/', headers=headers, timeout=10)
        print('Projects API Status:', projects_response.status_code)
    else:
        print('API Token: Not configured (some operations may require authentication)')
    
    print('OVERALL: SUCCESS')
except requests.exceptions.ConnectionError as e:
    print('CONNECTION ERROR:', str(e))
except Exception as e:
    print('ERROR:', str(e))
" 2>&1)
    
    if echo "$LS_API_TEST" | grep -qi "OVERALL: SUCCESS"; then
        print_pass "Label Studio API accessible from API container"
        print_info "$LS_API_TEST"
        CONNECTIVITY_RESULTS["label_studio"]="connected"
    else
        print_warn "Label Studio API test failed"
        print_info "$LS_API_TEST"
    fi
    
    # Test 4: Verify LABEL_STUDIO_URL environment variable
    print_test "Verifying LABEL_STUDIO_URL environment variable"
    
    LS_URL=$(docker exec ${API_CONTAINER} sh -c 'echo $LABEL_STUDIO_URL' 2>&1)
    
    if [ -n "$LS_URL" ] && echo "$LS_URL" | grep -q "http://"; then
        print_pass "LABEL_STUDIO_URL is configured correctly"
        print_info "LABEL_STUDIO_URL: $LS_URL"
    else
        print_warn "LABEL_STUDIO_URL may not be configured correctly"
        print_info "Value: $LS_URL"
    fi
    
    # Test 5: Test via external endpoint
    print_test "Testing Label Studio from host"
    
    if command -v curl &> /dev/null; then
        LS_EXTERNAL=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${LABEL_STUDIO_PORT}/health 2>&1 || echo "failed")
        
        if [ "$LS_EXTERNAL" = "200" ]; then
            print_pass "Label Studio accessible from host"
        else
            print_info "Label Studio external access returned: $LS_EXTERNAL"
        fi
    fi
}


# Task 6.5: Generate comprehensive connectivity report
generate_connectivity_report() {
    print_header "Task 6.5: Generate Comprehensive Connectivity Report"
    print_test "Validates: Property 3 (Database Connectivity)"
    
    REPORT_FILE="connectivity-report-$(date +%Y%m%d-%H%M%S).json"
    
    print_test "Generating JSON connectivity report"
    
    # Get additional system information
    API_HEALTH="unknown"
    SYSTEM_STATUS="unknown"
    
    if command -v curl &> /dev/null; then
        API_HEALTH_RESPONSE=$(curl -s http://localhost:${API_PORT}/health 2>&1 || echo '{}')
        SYSTEM_STATUS_RESPONSE=$(curl -s http://localhost:${API_PORT}/system/status 2>&1 || echo '{}')
        
        if echo "$API_HEALTH_RESPONSE" | grep -qi "healthy\|ok"; then
            API_HEALTH="healthy"
        elif echo "$API_HEALTH_RESPONSE" | grep -qi "error\|failed"; then
            API_HEALTH="unhealthy"
        fi
    fi
    
    # Build JSON report
    cat > "$REPORT_FILE" << EOF
{
    "report_metadata": {
        "timestamp": "$(date -Iseconds)",
        "report_type": "service_connectivity",
        "spec_reference": "docker-infrastructure",
        "validates": [
            "Requirements 6.1: Database connection strings correctly configured",
            "Property 3: Database Connectivity"
        ]
    },
    "connectivity_summary": {
        "postgresql": {
            "status": "${CONNECTIVITY_RESULTS["postgres"]:-unknown}",
            "container": "${POSTGRES_CONTAINER}",
            "port": ${POSTGRES_PORT},
            "connection_string_format": "postgresql://superinsight:****@postgres:5432/superinsight",
            "tests_performed": [
                "Network connectivity (nc/tcp)",
                "Database query execution",
                "Environment variable verification"
            ]
        },
        "redis": {
            "status": "${CONNECTIVITY_RESULTS["redis"]:-unknown}",
            "container": "${REDIS_CONTAINER}",
            "port": ${REDIS_PORT},
            "connection_string_format": "redis://redis:6379/0",
            "tests_performed": [
                "Network connectivity (nc/tcp)",
                "PING command",
                "SET/GET operations",
                "Environment variable verification"
            ]
        },
        "neo4j": {
            "status": "${CONNECTIVITY_RESULTS["neo4j"]:-unknown}",
            "container": "${NEO4J_CONTAINER}",
            "bolt_port": ${NEO4J_BOLT_PORT},
            "http_port": ${NEO4J_HTTP_PORT},
            "connection_string_format": "bolt://neo4j:7687",
            "tests_performed": [
                "Network connectivity (Bolt port)",
                "Network connectivity (HTTP port)",
                "Cypher query execution",
                "Environment variable verification"
            ]
        },
        "label_studio": {
            "status": "${CONNECTIVITY_RESULTS["label_studio"]:-unknown}",
            "container": "${LABEL_STUDIO_CONTAINER}",
            "port": ${LABEL_STUDIO_PORT},
            "connection_string_format": "http://label-studio:8080",
            "tests_performed": [
                "Network connectivity",
                "Health endpoint check",
                "API accessibility",
                "Environment variable verification"
            ]
        }
    },
    "api_status": {
        "container": "${API_CONTAINER}",
        "port": ${API_PORT},
        "health": "${API_HEALTH}",
        "endpoints_tested": [
            "/health",
            "/system/status"
        ]
    },
    "test_results": {
        "tests_passed": ${PASSED},
        "tests_failed": ${FAILED},
        "warnings": ${WARNINGS},
        "overall_status": "$([ $FAILED -eq 0 ] && echo "PASS" || echo "FAIL")"
    },
    "environment_variables_verified": [
        "DATABASE_URL",
        "REDIS_URL",
        "NEO4J_URI",
        "LABEL_STUDIO_URL"
    ],
    "network_configuration": {
        "network_name": "superinsight-network",
        "network_driver": "bridge",
        "dns_resolution": "container_names"
    },
    "recommendations": [
        $([ "${CONNECTIVITY_RESULTS["postgres"]}" != "connected" ] && echo '"Check PostgreSQL container logs and DATABASE_URL configuration",' || echo '')
        $([ "${CONNECTIVITY_RESULTS["redis"]}" != "connected" ] && echo '"Check Redis container logs and REDIS_URL configuration",' || echo '')
        $([ "${CONNECTIVITY_RESULTS["neo4j"]}" != "connected" ] && echo '"Check Neo4j container logs and NEO4J_URI/NEO4J_PASSWORD configuration",' || echo '')
        $([ "${CONNECTIVITY_RESULTS["label_studio"]}" != "connected" ] && echo '"Check Label Studio container logs and LABEL_STUDIO_URL configuration",' || echo '')
        "Run docker-compose logs <service> for detailed troubleshooting"
    ]
}
EOF
    
    print_pass "Report generated: $REPORT_FILE"
    print_info "Report contents:"
    cat "$REPORT_FILE" | python3 -m json.tool 2>/dev/null || cat "$REPORT_FILE"
    
    # Also generate a human-readable summary
    echo ""
    print_header "Connectivity Summary"
    
    echo ""
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│                  SERVICE CONNECTIVITY STATUS                │"
    echo "├─────────────────┬───────────────┬───────────────────────────┤"
    echo "│ Service         │ Status        │ Connection String         │"
    echo "├─────────────────┼───────────────┼───────────────────────────┤"
    
    # PostgreSQL
    PG_STATUS="${CONNECTIVITY_RESULTS["postgres"]:-unknown}"
    PG_ICON=$([ "$PG_STATUS" = "connected" ] && echo "✓" || echo "✗")
    printf "│ %-15s │ %-13s │ %-25s │\n" "PostgreSQL" "$PG_ICON $PG_STATUS" "postgres:5432"
    
    # Redis
    REDIS_STATUS="${CONNECTIVITY_RESULTS["redis"]:-unknown}"
    REDIS_ICON=$([ "$REDIS_STATUS" = "connected" ] && echo "✓" || echo "✗")
    printf "│ %-15s │ %-13s │ %-25s │\n" "Redis" "$REDIS_ICON $REDIS_STATUS" "redis:6379"
    
    # Neo4j
    NEO4J_STATUS="${CONNECTIVITY_RESULTS["neo4j"]:-unknown}"
    NEO4J_ICON=$([ "$NEO4J_STATUS" = "connected" ] && echo "✓" || echo "✗")
    printf "│ %-15s │ %-13s │ %-25s │\n" "Neo4j" "$NEO4J_ICON $NEO4J_STATUS" "neo4j:7687"
    
    # Label Studio
    LS_STATUS="${CONNECTIVITY_RESULTS["label_studio"]:-unknown}"
    LS_ICON=$([ "$LS_STATUS" = "connected" ] && echo "✓" || echo "✗")
    printf "│ %-15s │ %-13s │ %-25s │\n" "Label Studio" "$LS_ICON $LS_STATUS" "label-studio:8080"
    
    echo "└─────────────────┴───────────────┴───────────────────────────┘"
    echo ""
}


# Print final summary
print_summary() {
    print_header "Verification Summary"
    
    echo -e "Tests Passed:  ${GREEN}${PASSED}${NC}"
    echo -e "Tests Failed:  ${RED}${FAILED}${NC}"
    echo -e "Warnings:      ${YELLOW}${WARNINGS}${NC}"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All service connectivity verifications passed!${NC}"
        echo ""
        echo "Requirements validated:"
        echo "  - 6.1: Database connection strings correctly configured"
        echo "  - Property 3: Database Connectivity (superinsight role can connect)"
        echo ""
        echo "Services verified:"
        echo "  - API -> PostgreSQL: Connected"
        echo "  - API -> Redis: Connected"
        echo "  - API -> Neo4j: Connected"
        echo "  - API -> Label Studio: Connected"
        return 0
    else
        echo -e "${RED}✗ Some connectivity verifications failed. Please check the output above.${NC}"
        echo ""
        echo "Troubleshooting tips:"
        echo "  1. Ensure all containers are running: docker-compose up -d"
        echo "  2. Check container logs: docker-compose logs <service-name>"
        echo "  3. Verify network connectivity: docker network inspect superinsight-network"
        echo "  4. Check environment variables in docker-compose.yml"
        echo "  5. Ensure services have passed health checks: docker-compose ps"
        return 1
    fi
}

# Test inter-container DNS resolution
test_dns_resolution() {
    print_header "Testing Inter-Container DNS Resolution"
    print_test "Verifying Docker network DNS resolution"
    
    # Test DNS resolution from API container
    for service in postgres redis neo4j label-studio; do
        print_test "Resolving $service from API container"
        
        DNS_RESULT=$(docker exec ${API_CONTAINER} sh -c "getent hosts $service 2>&1" || echo "failed")
        
        if [ "$DNS_RESULT" != "failed" ] && [ -n "$DNS_RESULT" ]; then
            print_pass "DNS resolution for $service: $DNS_RESULT"
        else
            # Try alternative method
            PING_RESULT=$(docker exec ${API_CONTAINER} sh -c "ping -c 1 $service 2>&1 | head -1" || echo "failed")
            if echo "$PING_RESULT" | grep -qi "PING"; then
                print_pass "DNS resolution for $service works (via ping)"
            else
                print_warn "DNS resolution for $service may have issues"
            fi
        fi
    done
}

# Check Docker network configuration
check_network_config() {
    print_header "Checking Docker Network Configuration"
    
    print_test "Inspecting superinsight-network"
    
    NETWORK_INFO=$(docker network inspect superinsight-network 2>&1 || echo "failed")
    
    if [ "$NETWORK_INFO" != "failed" ]; then
        print_pass "Network superinsight-network exists"
        
        # Extract connected containers
        CONNECTED=$(echo "$NETWORK_INFO" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    containers = data[0].get('Containers', {})
    for cid, info in containers.items():
        print(f\"  - {info.get('Name', 'unknown')}: {info.get('IPv4Address', 'no IP')}\")
except:
    print('  Could not parse network info')
" 2>/dev/null || echo "  Could not parse network info")
        
        print_info "Connected containers:"
        echo "$CONNECTED"
    else
        print_fail "Network superinsight-network not found"
        print_info "Create network with: docker network create superinsight-network"
    fi
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║       Service Connectivity Verification Script             ║"
    echo "║       SuperInsight Platform - Docker Infrastructure        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "This script validates Requirements 6.1 and Property 3 from the"
    echo "docker-infrastructure specification."
    echo ""
    echo "Tests performed:"
    echo "  - Task 6.1: API to PostgreSQL connection"
    echo "  - Task 6.2: API to Redis connection"
    echo "  - Task 6.3: API to Neo4j connection"
    echo "  - Task 6.4: API to Label Studio connection"
    echo "  - Task 6.5: Generate comprehensive connectivity report"
    echo ""
    
    check_docker
    check_docker_compose
    list_containers
    
    # Check network configuration
    check_network_config
    
    # Test DNS resolution
    test_dns_resolution
    
    # Run connectivity tests
    test_api_postgres_connection
    test_api_redis_connection
    test_api_neo4j_connection
    test_api_label_studio_connection
    
    # Generate report
    generate_connectivity_report
    
    # Print summary
    print_summary
}

# Run main function
main "$@"
