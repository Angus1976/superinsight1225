#!/bin/bash

# OpenClaw Integration Test Script
# 测试 OpenClaw 与 SuperInsight 的集成功能

set -e

echo "=========================================="
echo "OpenClaw Integration Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Testing $name... "
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$status" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $status)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Expected HTTP $expected_status, got $status)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Helper function to test JSON response
test_json_endpoint() {
    local name=$1
    local url=$2
    local jq_filter=$3
    local expected_value=$4
    
    echo -n "Testing $name... "
    
    response=$(curl -s "$url")
    actual_value=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data$jq_filter)" 2>/dev/null || echo "ERROR")
    
    if [ "$actual_value" = "$expected_value" ]; then
        echo -e "${GREEN}✓ PASSED${NC} ($actual_value)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Expected: $expected_value, Got: $actual_value)"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "1. Testing OpenClaw Core (official)"
echo "-------------------------------------"
test_endpoint "OpenClaw Core Health (healthz)" "http://localhost:18789/healthz"
echo ""

echo "2. Testing OpenClaw Gateway (compat)"
echo "----------------------------"
test_endpoint "Gateway Health Check" "http://localhost:3000/health"
test_json_endpoint "Gateway Service Name" "http://localhost:3000/health" "['service']" "openclaw-gateway"
test_json_endpoint "Gateway API URL" "http://localhost:3000/api/info" "['superinsight_api']" "http://app:8000"
test_json_endpoint "Gateway Tenant ID" "http://localhost:3000/api/info" "['tenant_id']" "default-tenant"
test_endpoint "Gateway Channels" "http://localhost:3000/api/channels"
echo ""

echo "3. Testing OpenClaw Agent"
echo "-------------------------"
test_endpoint "Agent Health Check" "http://localhost:8081/health"
test_json_endpoint "Agent Service Name" "http://localhost:8081/health" "['service']" "openclaw-agent"
test_json_endpoint "Agent LLM Provider" "http://localhost:8081/health" "['llm_provider']" "ollama"
test_json_endpoint "Agent Name" "http://localhost:8081/api/info" "['name']" "SuperInsight Assistant"
test_json_endpoint "Agent Language" "http://localhost:8081/api/info" "['language']['user_language']" "zh-CN"
test_endpoint "Agent Skills List" "http://localhost:8081/api/skills"
echo ""

echo "4. Testing Skill Execution"
echo "--------------------------"
echo -n "Testing SuperInsight Data Query Skill... "
response=$(curl -s -X POST http://localhost:8081/api/skills/execute \
  -H "Content-Type: application/json" \
  -d '{"skill_name": "superinsight-data-query", "parameters": {"query": "测试查询"}}')

success=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['success'])" 2>/dev/null || echo "false")

if [ "$success" = "True" ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}"
    ((TESTS_FAILED++))
fi
echo ""

echo "5. Testing Container Health"
echo "---------------------------"
echo -n "Checking OpenClaw Gateway container... "
gateway_status=$(docker inspect -f '{{.State.Health.Status}}' superinsight-openclaw-gateway 2>/dev/null || echo "unknown")
if [ "$gateway_status" = "healthy" ]; then
    echo -e "${GREEN}✓ HEALTHY${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ UNHEALTHY${NC} (Status: $gateway_status)"
    ((TESTS_FAILED++))
fi

echo -n "Checking OpenClaw Agent container... "
agent_status=$(docker inspect -f '{{.State.Health.Status}}' superinsight-openclaw-agent 2>/dev/null || echo "unknown")
if [ "$agent_status" = "healthy" ]; then
    echo -e "${GREEN}✓ HEALTHY${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ UNHEALTHY${NC} (Status: $agent_status)"
    ((TESTS_FAILED++))
fi
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed! ✗${NC}"
    exit 1
fi
