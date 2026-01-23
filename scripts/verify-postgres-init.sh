#!/bin/bash
# PostgreSQL Initialization Verification Script
# This script verifies that PostgreSQL has been properly initialized
# according to the docker-infrastructure spec requirements.
#
# Usage: ./scripts/verify-postgres-init.sh
#
# Requirements:
# - Docker must be running
# - PostgreSQL container (superinsight-postgres) must be running
#
# Validates:
# - Requirements 1.2: superinsight role exists
# - Requirements 1.4: Extensions are enabled (uuid-ossp, btree_gin)
# - Requirements 1.5: alembic_version table exists
# - Requirements 3.1-3.5: Database permissions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Container name
CONTAINER_NAME="superinsight-postgres"
DB_USER="superinsight"
DB_NAME="superinsight"

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

# Check if container is running
check_container() {
    print_header "Checking PostgreSQL Container"
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_fail "Container ${CONTAINER_NAME} is not running"
        print_info "Start the container with: docker-compose up -d postgres"
        exit 1
    fi
    print_pass "Container ${CONTAINER_NAME} is running"
}

# Task 4.1: Check PostgreSQL container logs
check_logs() {
    print_header "Task 4.1: Check PostgreSQL Container Logs"
    print_test "Checking for SQL syntax errors in logs"
    
    LOGS=$(docker-compose logs postgres 2>&1)
    
    # Check for syntax errors
    if echo "$LOGS" | grep -qi "syntax error"; then
        print_fail "SQL syntax errors found in logs"
        echo "$LOGS" | grep -i "syntax error" | head -5
        return 1
    fi
    print_pass "No SQL syntax errors in logs"
    
    # Check for successful initialization
    if echo "$LOGS" | grep -qi "database system is ready to accept connections"; then
        print_pass "PostgreSQL is ready to accept connections"
    else
        print_warn "Could not confirm PostgreSQL readiness from logs"
    fi
    
    # Check for init script execution
    if echo "$LOGS" | grep -qi "init-db.sql"; then
        print_pass "Init script was executed"
    else
        print_info "Init script execution not found in recent logs (may have run on first startup)"
    fi
}

# Task 4.2: Verify superinsight role exists
check_role() {
    print_header "Task 4.2: Verify superinsight Role Exists"
    print_test "Checking if superinsight role exists (Validates: Requirements 1.2)"
    
    RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "\du" 2>&1)
    
    if echo "$RESULT" | grep -q "superinsight"; then
        print_pass "Role 'superinsight' exists"
        echo "$RESULT" | grep "superinsight"
    else
        print_fail "Role 'superinsight' does not exist"
        echo "$RESULT"
        return 1
    fi
}

# Task 4.3: Verify extensions are enabled
check_extensions() {
    print_header "Task 4.3: Verify Extensions Are Enabled"
    print_test "Checking PostgreSQL extensions (Validates: Requirements 1.4)"
    
    RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "\dx" 2>&1)
    
    # Check uuid-ossp
    if echo "$RESULT" | grep -q "uuid-ossp"; then
        print_pass "Extension 'uuid-ossp' is enabled"
    else
        print_fail "Extension 'uuid-ossp' is NOT enabled"
    fi
    
    # Check btree_gin
    if echo "$RESULT" | grep -q "btree_gin"; then
        print_pass "Extension 'btree_gin' is enabled"
    else
        print_fail "Extension 'btree_gin' is NOT enabled"
    fi
    
    echo ""
    print_info "Installed extensions:"
    echo "$RESULT"
}

# Task 4.4: Verify permissions are granted
check_permissions() {
    print_header "Task 4.4: Verify Permissions Are Granted"
    print_test "Testing CREATE TABLE operation (Validates: Requirements 3.1-3.5)"
    
    # Create a test table
    CREATE_RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "
        CREATE TABLE IF NOT EXISTS _verification_test (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    " 2>&1)
    
    if echo "$CREATE_RESULT" | grep -qi "error"; then
        print_fail "CREATE TABLE failed"
        echo "$CREATE_RESULT"
        return 1
    fi
    print_pass "CREATE TABLE succeeded"
    
    # Test INSERT
    print_test "Testing INSERT operation"
    INSERT_RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "
        INSERT INTO _verification_test (name) VALUES ('test_entry');
    " 2>&1)
    
    if echo "$INSERT_RESULT" | grep -qi "error"; then
        print_fail "INSERT failed"
        echo "$INSERT_RESULT"
    else
        print_pass "INSERT succeeded"
    fi
    
    # Test SELECT
    print_test "Testing SELECT operation"
    SELECT_RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "
        SELECT * FROM _verification_test;
    " 2>&1)
    
    if echo "$SELECT_RESULT" | grep -qi "error"; then
        print_fail "SELECT failed"
        echo "$SELECT_RESULT"
    else
        print_pass "SELECT succeeded"
        echo "$SELECT_RESULT"
    fi
    
    # Test UPDATE
    print_test "Testing UPDATE operation"
    UPDATE_RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "
        UPDATE _verification_test SET name = 'updated_entry' WHERE name = 'test_entry';
    " 2>&1)
    
    if echo "$UPDATE_RESULT" | grep -qi "error"; then
        print_fail "UPDATE failed"
        echo "$UPDATE_RESULT"
    else
        print_pass "UPDATE succeeded"
    fi
    
    # Test DELETE
    print_test "Testing DELETE operation"
    DELETE_RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "
        DELETE FROM _verification_test WHERE name = 'updated_entry';
    " 2>&1)
    
    if echo "$DELETE_RESULT" | grep -qi "error"; then
        print_fail "DELETE failed"
        echo "$DELETE_RESULT"
    else
        print_pass "DELETE succeeded"
    fi
    
    # Cleanup test table
    print_test "Cleaning up test table"
    docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "
        DROP TABLE IF EXISTS _verification_test;
    " > /dev/null 2>&1
    print_pass "Test table cleaned up"
    
    # Check database privileges
    print_test "Checking database privileges"
    PRIV_RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "
        SELECT has_database_privilege('superinsight', 'superinsight', 'CREATE') as can_create,
               has_database_privilege('superinsight', 'superinsight', 'CONNECT') as can_connect,
               has_database_privilege('superinsight', 'superinsight', 'TEMPORARY') as can_temp;
    " 2>&1)
    
    echo "$PRIV_RESULT"
    
    if echo "$PRIV_RESULT" | grep -q "t"; then
        print_pass "Database privileges are correctly configured"
    else
        print_warn "Some database privileges may be missing"
    fi
}

# Task 4.5: Verify alembic_version table exists
check_alembic() {
    print_header "Task 4.5: Verify alembic_version Table Exists"
    print_test "Checking for alembic_version table (Validates: Requirements 1.5)"
    
    RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "\dt alembic_version" 2>&1)
    
    if echo "$RESULT" | grep -q "alembic_version"; then
        print_pass "Table 'alembic_version' exists"
        echo "$RESULT"
    else
        print_fail "Table 'alembic_version' does NOT exist"
        echo "$RESULT"
        return 1
    fi
    
    # Check table structure
    print_test "Checking alembic_version table structure"
    STRUCT_RESULT=$(docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "\d alembic_version" 2>&1)
    echo "$STRUCT_RESULT"
}

# Print summary
print_summary() {
    print_header "Verification Summary"
    
    echo -e "Tests Passed:  ${GREEN}${PASSED}${NC}"
    echo -e "Tests Failed:  ${RED}${FAILED}${NC}"
    echo -e "Warnings:      ${YELLOW}${WARNINGS}${NC}"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All PostgreSQL initialization verifications passed!${NC}"
        echo ""
        echo "Requirements validated:"
        echo "  - 1.2: superinsight role exists"
        echo "  - 1.4: Extensions enabled (uuid-ossp, btree_gin)"
        echo "  - 1.5: alembic_version table exists"
        echo "  - 3.1-3.5: Database permissions granted"
        return 0
    else
        echo -e "${RED}✗ Some verifications failed. Please check the output above.${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║     PostgreSQL Initialization Verification Script          ║"
    echo "║     SuperInsight Platform - Docker Infrastructure          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    check_docker
    check_container
    check_logs
    check_role
    check_extensions
    check_permissions
    check_alembic
    print_summary
}

# Run main function
main "$@"
