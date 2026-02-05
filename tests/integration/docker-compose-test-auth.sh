#!/bin/bash

################################################################################
# Docker Compose JWT and Label Studio Authentication Test Suite
# 
# This script tests:
# 1. JWT token generation and validation
# 2. Label Studio API Token authentication
# 3. Project creation and management
# 4. Task synchronization
# 5. Annotation sync
# 6. Language parameter handling
# 7. Error handling and recovery
#
# Usage: docker-compose exec app bash docker-compose-test-auth.sh
# Or:    docker compose exec app bash docker-compose-test-auth.sh
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="http://localhost:8000"
LABEL_STUDIO_URL="http://label-studio:8080"
TEST_USERNAME="admin"
TEST_PASSWORD="admin"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

################################################################################
# Utility Functions
################################################################################

log_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

log_test() {
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "${YELLOW}[TEST $TESTS_TOTAL]${NC} $1"
}

log_success() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo -e "${GREEN}✅ PASS${NC}: $1"
}

log_failure() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "${RED}❌ FAIL${NC}: $1"
}

log_info() {
    echo -e "${BLUE}ℹ️  INFO${NC}: $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

# Extract JSON value
extract_json() {
    echo "$1" | python3 -c "import sys, json; print(json.load(sys.stdin).get('$2', ''))" 2>/dev/null || echo ""
}

# Extract nested JSON value
extract_nested_json() {
    echo "$1" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('$2', {}).get('$3', ''))" 2>/dev/null || echo ""
}

# Check HTTP status code
check_status() {
    local response="$1"
    local expected="$2"
    local description="$3"
    
    local status=$(echo "$response" | tail -n1)
    
    if [ "$status" = "$expected" ]; then
        log_success "$description (HTTP $status)"
        return 0
    else
        log_failure "$description (Expected HTTP $expected, got HTTP $status)"
        return 1
    fi
}

# Wait for service to be ready
wait_for_service() {
    local url="$1"
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log_success "Service ready: $url"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    log_failure "Service not ready after ${max_attempts}s: $url"
    return 1
}

################################################################################
# Section 1: Service Health Checks
################################################################################

test_service_health() {
    log_header "Section 1: Service Health Checks"
    
    # Test SuperInsight API
    log_test "SuperInsight API health check"
    if wait_for_service "$API_BASE_URL/health"; then
        :
    else
        log_failure "SuperInsight API not responding"
        return 1
    fi
    
    # Test Label Studio
    log_test "Label Studio health check"
    if wait_for_service "$LABEL_STUDIO_URL/health"; then
        :
    else
        log_failure "Label Studio not responding"
        return 1
    fi
}

################################################################################
# Section 2: JWT Authentication Tests
################################################################################

test_jwt_authentication() {
    log_header "Section 2: JWT Authentication Tests"
    
    # Test 2.1: Login and get JWT token
    log_test "Login with valid credentials"
    local login_response=$(curl -s -w "\n%{http_code}" -X POST \
        "$API_BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$TEST_USERNAME\", \"password\": \"$TEST_PASSWORD\"}")
    
    local login_body=$(echo "$login_response" | sed '$d')
    local login_status=$(echo "$login_response" | tail -n1)
    
    if [ "$login_status" = "200" ]; then
        log_success "Login successful (HTTP 200)"
        JWT_TOKEN=$(extract_json "$login_body" "access_token")
        
        if [ -z "$JWT_TOKEN" ]; then
            log_failure "JWT token not found in response"
            return 1
        fi
        
        log_info "JWT Token: ${JWT_TOKEN:0:50}..."
    else
        log_failure "Login failed (HTTP $login_status)"
        log_info "Response: $login_body"
        return 1
    fi
    
    # Test 2.2: Validate JWT token format
    log_test "Validate JWT token format"
    local token_parts=$(echo "$JWT_TOKEN" | tr '.' '\n' | wc -l)
    
    if [ "$token_parts" = "3" ]; then
        log_success "JWT token has valid format (3 parts)"
    else
        log_failure "JWT token has invalid format (expected 3 parts, got $token_parts)"
        return 1
    fi
    
    # Test 2.3: Use JWT token to access protected endpoint
    log_test "Access protected endpoint with JWT token"
    local protected_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/users/me" \
        -H "Authorization: Bearer $JWT_TOKEN")
    
    local protected_body=$(echo "$protected_response" | sed '$d')
    local protected_status=$(echo "$protected_response" | tail -n1)
    
    if [ "$protected_status" = "200" ]; then
        log_success "Protected endpoint accessible with JWT (HTTP 200)"
        local user_id=$(extract_json "$protected_body" "id")
        log_info "User ID: $user_id"
    else
        log_failure "Protected endpoint not accessible (HTTP $protected_status)"
        log_info "Response: $protected_body"
        return 1
    fi
    
    # Test 2.4: Reject invalid JWT token
    log_test "Reject invalid JWT token"
    local invalid_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/users/me" \
        -H "Authorization: Bearer invalid.token.here")
    
    local invalid_status=$(echo "$invalid_response" | tail -n1)
    
    if [ "$invalid_status" = "401" ] || [ "$invalid_status" = "403" ]; then
        log_success "Invalid JWT token rejected (HTTP $invalid_status)"
    else
        log_failure "Invalid JWT token not rejected (HTTP $invalid_status)"
        return 1
    fi
    
    # Test 2.5: Reject missing JWT token
    log_test "Reject missing JWT token"
    local missing_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/users/me")
    
    local missing_status=$(echo "$missing_response" | tail -n1)
    
    if [ "$missing_status" = "401" ] || [ "$missing_status" = "403" ]; then
        log_success "Missing JWT token rejected (HTTP $missing_status)"
    else
        log_failure "Missing JWT token not rejected (HTTP $missing_status)"
        return 1
    fi
}

################################################################################
# Section 3: Label Studio API Token Authentication
################################################################################

test_label_studio_authentication() {
    log_header "Section 3: Label Studio API Token Authentication"
    
    # Get API Token from environment
    local api_token=$(grep "LABEL_STUDIO_API_TOKEN=" /app/.env 2>/dev/null | cut -d'=' -f2 | tr -d ' ')
    
    if [ -z "$api_token" ]; then
        log_warning "LABEL_STUDIO_API_TOKEN not found in .env, skipping Label Studio tests"
        return 0
    fi
    
    log_info "Using API Token: ${api_token:0:50}..."
    
    # Test 3.1: Test Label Studio connection
    log_test "Test Label Studio API connection"
    local ls_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$LABEL_STUDIO_URL/api/current-user/whoami/" \
        -H "Authorization: Token $api_token")
    
    local ls_body=$(echo "$ls_response" | sed '$d')
    local ls_status=$(echo "$ls_response" | tail -n1)
    
    if [ "$ls_status" = "200" ]; then
        log_success "Label Studio API connection successful (HTTP 200)"
        local user_email=$(extract_json "$ls_body" "email")
        log_info "Label Studio User: $user_email"
    else
        log_failure "Label Studio API connection failed (HTTP $ls_status)"
        log_info "Response: $ls_body"
        return 1
    fi
    
    # Test 3.2: List projects
    log_test "List Label Studio projects"
    local projects_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$LABEL_STUDIO_URL/api/projects/" \
        -H "Authorization: Token $api_token")
    
    local projects_body=$(echo "$projects_response" | sed '$d')
    local projects_status=$(echo "$projects_response" | tail -n1)
    
    if [ "$projects_status" = "200" ]; then
        log_success "List projects successful (HTTP 200)"
        local project_count=$(echo "$projects_body" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('results', [])))" 2>/dev/null || echo "0")
        log_info "Project count: $project_count"
    else
        log_failure "List projects failed (HTTP $projects_status)"
        return 1
    fi
    
    # Test 3.3: Reject invalid API Token
    log_test "Reject invalid API Token"
    local invalid_token_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$LABEL_STUDIO_URL/api/current-user/whoami/" \
        -H "Authorization: Token invalid_token_12345")
    
    local invalid_token_status=$(echo "$invalid_token_response" | tail -n1)
    
    if [ "$invalid_token_status" = "401" ] || [ "$invalid_token_status" = "403" ]; then
        log_success "Invalid API Token rejected (HTTP $invalid_token_status)"
    else
        log_failure "Invalid API Token not rejected (HTTP $invalid_token_status)"
        return 1
    fi
}

################################################################################
# Section 4: Project Management Tests
################################################################################

test_project_management() {
    log_header "Section 4: Project Management Tests"
    
    if [ -z "$JWT_TOKEN" ]; then
        log_warning "JWT token not available, skipping project management tests"
        return 0
    fi
    
    # Test 4.1: Create a test task
    log_test "Create test task"
    local task_response=$(curl -s -w "\n%{http_code}" -X POST \
        "$API_BASE_URL/api/tasks" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Test Task for Auth",
            "description": "Testing JWT and Label Studio auth",
            "priority": "medium",
            "annotation_type": "text_classification",
            "total_items": 10,
            "tags": ["test", "auth"]
        }')
    
    local task_body=$(echo "$task_response" | sed '$d')
    local task_status=$(echo "$task_response" | tail -n1)
    
    if [ "$task_status" = "200" ]; then
        log_success "Task created successfully (HTTP 200)"
        TASK_ID=$(extract_json "$task_body" "id")
        log_info "Task ID: $TASK_ID"
    else
        log_failure "Task creation failed (HTTP $task_status)"
        log_info "Response: $task_body"
        return 1
    fi
    
    # Test 4.2: Verify task has sync status
    log_test "Verify task has Label Studio sync status"
    local task_detail_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/tasks/$TASK_ID" \
        -H "Authorization: Bearer $JWT_TOKEN")
    
    local task_detail_body=$(echo "$task_detail_response" | sed '$d')
    local task_detail_status=$(echo "$task_detail_response" | tail -n1)
    
    if [ "$task_detail_status" = "200" ]; then
        log_success "Task detail retrieved (HTTP 200)"
        local sync_status=$(extract_json "$task_detail_body" "label_studio_sync_status")
        log_info "Sync status: $sync_status"
        
        if [ -n "$sync_status" ]; then
            log_success "Task has Label Studio sync status field"
        else
            log_warning "Task missing Label Studio sync status field"
        fi
    else
        log_failure "Task detail retrieval failed (HTTP $task_detail_status)"
        return 1
    fi
}

################################################################################
# Section 5: Label Studio Project Creation Tests
################################################################################

test_label_studio_project_creation() {
    log_header "Section 5: Label Studio Project Creation Tests"
    
    if [ -z "$JWT_TOKEN" ] || [ -z "$TASK_ID" ]; then
        log_warning "JWT token or Task ID not available, skipping project creation tests"
        return 0
    fi
    
    # Test 5.1: Test Label Studio connection endpoint
    log_test "Test Label Studio connection via API"
    local connection_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/tasks/label-studio/test-connection" \
        -H "Authorization: Bearer $JWT_TOKEN")
    
    local connection_body=$(echo "$connection_response" | sed '$d')
    local connection_status=$(echo "$connection_response" | tail -n1)
    
    if [ "$connection_status" = "200" ]; then
        log_success "Label Studio connection test successful (HTTP 200)"
        local connection_result=$(extract_json "$connection_body" "status")
        log_info "Connection status: $connection_result"
    else
        log_failure "Label Studio connection test failed (HTTP $connection_status)"
        log_info "Response: $connection_body"
        return 1
    fi
    
    # Test 5.2: Ensure project exists
    log_test "Ensure Label Studio project exists for task"
    local ensure_response=$(curl -s -w "\n%{http_code}" -X POST \
        "$API_BASE_URL/api/tasks/$TASK_ID/sync-label-studio" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{}')
    
    local ensure_body=$(echo "$ensure_response" | sed '$d')
    local ensure_status=$(echo "$ensure_response" | tail -n1)
    
    if [ "$ensure_status" = "200" ]; then
        log_success "Project sync initiated (HTTP 200)"
        LABEL_STUDIO_PROJECT_ID=$(extract_json "$ensure_body" "project_id")
        log_info "Label Studio Project ID: $LABEL_STUDIO_PROJECT_ID"
    else
        log_failure "Project sync failed (HTTP $ensure_status)"
        log_info "Response: $ensure_body"
        return 1
    fi
    
    # Test 5.3: Verify project exists in Label Studio
    if [ -n "$LABEL_STUDIO_PROJECT_ID" ]; then
        log_test "Verify project exists in Label Studio"
        
        local api_token=$(grep "LABEL_STUDIO_API_TOKEN=" /app/.env 2>/dev/null | cut -d'=' -f2 | tr -d ' ')
        
        if [ -n "$api_token" ]; then
            local verify_response=$(curl -s -w "\n%{http_code}" -X GET \
                "$LABEL_STUDIO_URL/api/projects/$LABEL_STUDIO_PROJECT_ID/" \
                -H "Authorization: Token $api_token")
            
            local verify_body=$(echo "$verify_response" | sed '$d')
            local verify_status=$(echo "$verify_response" | tail -n1)
            
            if [ "$verify_status" = "200" ]; then
                log_success "Project verified in Label Studio (HTTP 200)"
                local project_title=$(extract_json "$verify_body" "title")
                log_info "Project title: $project_title"
            else
                log_failure "Project verification failed (HTTP $verify_status)"
            fi
        fi
    fi
}

################################################################################
# Section 6: Language Parameter Tests
################################################################################

test_language_parameters() {
    log_header "Section 6: Language Parameter Tests"
    
    if [ -z "$JWT_TOKEN" ] || [ -z "$LABEL_STUDIO_PROJECT_ID" ]; then
        log_warning "JWT token or Project ID not available, skipping language tests"
        return 0
    fi
    
    # Test 6.1: Get authenticated URL with Chinese language
    log_test "Get authenticated URL with Chinese language"
    local auth_url_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/label-studio/projects/$LABEL_STUDIO_PROJECT_ID/auth-url?language=zh" \
        -H "Authorization: Bearer $JWT_TOKEN")
    
    local auth_url_body=$(echo "$auth_url_response" | sed '$d')
    local auth_url_status=$(echo "$auth_url_response" | tail -n1)
    
    if [ "$auth_url_status" = "200" ]; then
        log_success "Authenticated URL generated (HTTP 200)"
        local auth_url=$(extract_json "$auth_url_body" "url")
        
        if echo "$auth_url" | grep -q "lang=zh"; then
            log_success "Chinese language parameter included in URL"
        else
            log_warning "Chinese language parameter not found in URL"
        fi
        
        log_info "URL: ${auth_url:0:80}..."
    else
        log_failure "Authenticated URL generation failed (HTTP $auth_url_status)"
        return 1
    fi
    
    # Test 6.2: Get authenticated URL with English language
    log_test "Get authenticated URL with English language"
    local auth_url_en_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/label-studio/projects/$LABEL_STUDIO_PROJECT_ID/auth-url?language=en" \
        -H "Authorization: Bearer $JWT_TOKEN")
    
    local auth_url_en_body=$(echo "$auth_url_en_response" | sed '$d')
    local auth_url_en_status=$(echo "$auth_url_en_response" | tail -n1)
    
    if [ "$auth_url_en_status" = "200" ]; then
        log_success "Authenticated URL generated for English (HTTP 200)"
        local auth_url_en=$(extract_json "$auth_url_en_body" "url")
        
        if echo "$auth_url_en" | grep -q "lang=en"; then
            log_success "English language parameter included in URL"
        else
            log_warning "English language parameter not found in URL"
        fi
    else
        log_failure "English authenticated URL generation failed (HTTP $auth_url_en_status)"
        return 1
    fi
}

################################################################################
# Section 7: Error Handling Tests
################################################################################

test_error_handling() {
    log_header "Section 7: Error Handling Tests"
    
    if [ -z "$JWT_TOKEN" ]; then
        log_warning "JWT token not available, skipping error handling tests"
        return 0
    fi
    
    # Test 7.1: Handle missing project
    log_test "Handle missing Label Studio project"
    local missing_project_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/label-studio/projects/99999/validate" \
        -H "Authorization: Bearer $JWT_TOKEN")
    
    local missing_project_status=$(echo "$missing_project_response" | tail -n1)
    
    if [ "$missing_project_status" = "404" ] || [ "$missing_project_status" = "400" ]; then
        log_success "Missing project handled correctly (HTTP $missing_project_status)"
    else
        log_warning "Missing project returned unexpected status (HTTP $missing_project_status)"
    fi
    
    # Test 7.2: Handle invalid task ID
    log_test "Handle invalid task ID"
    local invalid_task_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/tasks/invalid-task-id" \
        -H "Authorization: Bearer $JWT_TOKEN")
    
    local invalid_task_status=$(echo "$invalid_task_response" | tail -n1)
    
    if [ "$invalid_task_status" = "404" ] || [ "$invalid_task_status" = "400" ]; then
        log_success "Invalid task ID handled correctly (HTTP $invalid_task_status)"
    else
        log_warning "Invalid task ID returned unexpected status (HTTP $invalid_task_status)"
    fi
    
    # Test 7.3: Handle unauthorized access
    log_test "Handle unauthorized access to task"
    local unauthorized_response=$(curl -s -w "\n%{http_code}" -X GET \
        "$API_BASE_URL/api/tasks/$TASK_ID")
    
    local unauthorized_status=$(echo "$unauthorized_response" | tail -n1)
    
    if [ "$unauthorized_status" = "401" ] || [ "$unauthorized_status" = "403" ]; then
        log_success "Unauthorized access rejected (HTTP $unauthorized_status)"
    else
        log_warning "Unauthorized access returned unexpected status (HTTP $unauthorized_status)"
    fi
}

################################################################################
# Section 8: Integration Tests
################################################################################

test_integration() {
    log_header "Section 8: Integration Tests"
    
    if [ -z "$JWT_TOKEN" ] || [ -z "$TASK_ID" ]; then
        log_warning "JWT token or Task ID not available, skipping integration tests"
        return 0
    fi
    
    # Test 8.1: Complete workflow - Create task and sync to Label Studio
    log_test "Complete workflow: Create task and sync to Label Studio"
    
    # Create task
    local workflow_task_response=$(curl -s -w "\n%{http_code}" -X POST \
        "$API_BASE_URL/api/tasks" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Integration Test Task",
            "description": "Testing complete workflow",
            "priority": "high",
            "annotation_type": "text_classification",
            "total_items": 5,
            "tags": ["integration", "test"]
        }')
    
    local workflow_task_body=$(echo "$workflow_task_response" | sed '$d')
    local workflow_task_status=$(echo "$workflow_task_response" | tail -n1)
    
    if [ "$workflow_task_status" = "200" ]; then
        local workflow_task_id=$(extract_json "$workflow_task_body" "id")
        log_info "Workflow task created: $workflow_task_id"
        
        # Wait for background sync
        log_info "Waiting 3 seconds for background sync..."
        sleep 3
        
        # Check sync status
        local workflow_check_response=$(curl -s -w "\n%{http_code}" -X GET \
            "$API_BASE_URL/api/tasks/$workflow_task_id" \
            -H "Authorization: Bearer $JWT_TOKEN")
        
        local workflow_check_body=$(echo "$workflow_check_response" | sed '$d')
        local workflow_check_status=$(echo "$workflow_check_response" | tail -n1)
        
        if [ "$workflow_check_status" = "200" ]; then
            local sync_status=$(extract_json "$workflow_check_body" "label_studio_sync_status")
            local project_id=$(extract_json "$workflow_check_body" "label_studio_project_id")
            
            log_info "Sync status: $sync_status"
            log_info "Project ID: $project_id"
            
            if [ "$sync_status" = "synced" ] && [ -n "$project_id" ]; then
                log_success "Complete workflow successful - task synced to Label Studio"
            else
                log_warning "Task created but sync status is $sync_status"
            fi
        fi
    else
        log_failure "Workflow task creation failed (HTTP $workflow_task_status)"
    fi
}

################################################################################
# Main Test Execution
################################################################################

main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  Docker Compose JWT and Label Studio Authentication Test Suite ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Run all test sections
    test_service_health || true
    test_jwt_authentication || true
    test_label_studio_authentication || true
    test_project_management || true
    test_label_studio_project_creation || true
    test_language_parameters || true
    test_error_handling || true
    test_integration || true
    
    # Print summary
    log_header "Test Summary"
    
    echo -e "Total Tests:  ${BLUE}$TESTS_TOTAL${NC}"
    echo -e "Passed:       ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed:       ${RED}$TESTS_FAILED${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}✅ All tests passed!${NC}\n"
        return 0
    else
        echo -e "\n${RED}❌ Some tests failed!${NC}\n"
        return 1
    fi
}

# Run main function
main
