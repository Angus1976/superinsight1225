#!/bin/bash
# Test Label Studio Integration
# Tests the "开始标注" and "在新窗口打开" functionality

set -e

echo "=== Label Studio Integration Test ==="
echo ""

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
LABEL_STUDIO_URL="${LABEL_STUDIO_URL:-http://localhost:8080}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Test 1: Check Label Studio is running
echo "Test 1: Check Label Studio is running..."
if curl -s -f "${LABEL_STUDIO_URL}/health" > /dev/null 2>&1; then
    print_result 0 "Label Studio is accessible"
else
    print_result 1 "Label Studio is not accessible at ${LABEL_STUDIO_URL}"
fi

# Test 2: Check API server is running
echo ""
echo "Test 2: Check API server is running..."
if curl -s -f "${API_BASE_URL}/health" > /dev/null 2>&1; then
    print_result 0 "API server is accessible"
else
    print_result 1 "API server is not accessible at ${API_BASE_URL}"
fi

# Test 3: Test ensure project endpoint
echo ""
echo "Test 3: Test ensure project endpoint..."
ENSURE_RESPONSE=$(curl -s -X POST "${API_BASE_URL}/api/label-studio/projects/ensure" \
    -H "Content-Type: application/json" \
    -d '{
        "task_id": "test-task-123",
        "task_name": "Test Annotation Project",
        "annotation_type": "text_classification"
    }' 2>&1)

if echo "$ENSURE_RESPONSE" | grep -q "project_id"; then
    PROJECT_ID=$(echo "$ENSURE_RESPONSE" | grep -o '"project_id":"[^"]*"' | cut -d'"' -f4)
    print_result 0 "Ensure project endpoint works (project_id: $PROJECT_ID)"
else
    print_result 1 "Ensure project endpoint failed"
    echo "Response: $ENSURE_RESPONSE"
fi

# Test 4: Test validate project endpoint
if [ -n "$PROJECT_ID" ]; then
    echo ""
    echo "Test 4: Test validate project endpoint..."
    VALIDATE_RESPONSE=$(curl -s "${API_BASE_URL}/api/label-studio/projects/${PROJECT_ID}/validate" 2>&1)
    
    if echo "$VALIDATE_RESPONSE" | grep -q '"exists":true'; then
        print_result 0 "Validate project endpoint works"
    else
        print_result 1 "Validate project endpoint failed"
        echo "Response: $VALIDATE_RESPONSE"
    fi
fi

# Test 5: Test authenticated URL endpoint
if [ -n "$PROJECT_ID" ]; then
    echo ""
    echo "Test 5: Test authenticated URL endpoint (Chinese)..."
    AUTH_URL_RESPONSE=$(curl -s "${API_BASE_URL}/api/label-studio/projects/${PROJECT_ID}/auth-url?language=zh" 2>&1)
    
    if echo "$AUTH_URL_RESPONSE" | grep -q '"url"' && echo "$AUTH_URL_RESPONSE" | grep -q 'lang=zh'; then
        print_result 0 "Authenticated URL endpoint works with Chinese language"
    else
        print_result 1 "Authenticated URL endpoint failed"
        echo "Response: $AUTH_URL_RESPONSE"
    fi
    
    echo ""
    echo "Test 6: Test authenticated URL endpoint (English)..."
    AUTH_URL_RESPONSE=$(curl -s "${API_BASE_URL}/api/label-studio/projects/${PROJECT_ID}/auth-url?language=en" 2>&1)
    
    if echo "$AUTH_URL_RESPONSE" | grep -q '"url"' && echo "$AUTH_URL_RESPONSE" | grep -q 'lang=en'; then
        print_result 0 "Authenticated URL endpoint works with English language"
    else
        print_result 1 "Authenticated URL endpoint failed"
        echo "Response: $AUTH_URL_RESPONSE"
    fi
fi

# Summary
echo ""
echo "=== Test Summary ==="
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi
