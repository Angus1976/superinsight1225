#!/bin/bash

# Test Label Studio Connection Script
# This script tests the Label Studio integration to diagnose button redirect issues

echo "========================================="
echo "Label Studio Connection Test"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check Label Studio container status
echo "Test 1: Checking Label Studio container status..."
if docker ps | grep "label-studio" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Label Studio container is running and healthy${NC}"
else
    echo -e "${RED}✗ Label Studio container is not healthy${NC}"
    docker ps | grep label-studio
    exit 1
fi
echo ""

# Test 2: Check Label Studio accessibility from host
echo "Test 2: Checking Label Studio accessibility from host..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 | grep -q "200\|302"; then
    echo -e "${GREEN}✓ Label Studio is accessible from host (http://localhost:8080)${NC}"
else
    echo -e "${RED}✗ Label Studio is not accessible from host${NC}"
    exit 1
fi
echo ""

# Test 3: Check Label Studio API from backend container
echo "Test 3: Checking Label Studio API from backend container..."
API_RESPONSE=$(docker exec superinsight-app curl -s -o /dev/null -w "%{http_code}" http://label-studio:8080/api/projects)
if [ "$API_RESPONSE" = "200" ] || [ "$API_RESPONSE" = "401" ]; then
    echo -e "${GREEN}✓ Label Studio API is accessible from backend (status: $API_RESPONSE)${NC}"
else
    echo -e "${RED}✗ Label Studio API is not accessible from backend (status: $API_RESPONSE)${NC}"
    exit 1
fi
echo ""

# Test 4: Check environment variables
echo "Test 4: Checking environment variables..."
if grep -q "LABEL_STUDIO_URL" .env && grep -q "LABEL_STUDIO_API_TOKEN" .env; then
    echo -e "${GREEN}✓ Label Studio environment variables are configured${NC}"
    echo "   LABEL_STUDIO_URL: $(grep LABEL_STUDIO_URL .env | cut -d'=' -f2)"
    echo "   LABEL_STUDIO_API_TOKEN: $(grep LABEL_STUDIO_API_TOKEN .env | cut -d'=' -f2 | cut -c1-20)..."
else
    echo -e "${RED}✗ Label Studio environment variables are missing${NC}"
    exit 1
fi
echo ""

# Test 5: Test backend API endpoint
echo "Test 5: Testing backend API endpoint..."
echo "   Testing: GET /api/label-studio/health"

# Get auth token (you may need to adjust this based on your setup)
# For now, we'll test without auth to see if the endpoint exists
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/label-studio/health)

if [ "$HEALTH_RESPONSE" = "200" ] || [ "$HEALTH_RESPONSE" = "401" ]; then
    echo -e "${GREEN}✓ Backend Label Studio API endpoint exists (status: $HEALTH_RESPONSE)${NC}"
    if [ "$HEALTH_RESPONSE" = "401" ]; then
        echo -e "${YELLOW}   Note: 401 means authentication is required (expected)${NC}"
    fi
else
    echo -e "${RED}✗ Backend Label Studio API endpoint not accessible (status: $HEALTH_RESPONSE)${NC}"
fi
echo ""

# Test 6: Check backend logs for errors
echo "Test 6: Checking backend logs for Label Studio errors..."
ERROR_COUNT=$(docker logs superinsight-app --tail 200 2>&1 | grep -i "label.*studio.*error" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ No Label Studio errors in recent backend logs${NC}"
else
    echo -e "${YELLOW}⚠ Found $ERROR_COUNT Label Studio errors in recent logs:${NC}"
    docker logs superinsight-app --tail 200 2>&1 | grep -i "label.*studio.*error" | tail -5
fi
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""
echo "All basic connectivity tests passed!"
echo ""
echo "Next steps for debugging button redirect issue:"
echo ""
echo "1. Open browser DevTools (F12)"
echo "2. Go to Console tab"
echo "3. Click '开始标注' button"
echo "4. Look for error messages starting with:"
echo "   - [handleStartAnnotation]"
echo "   - [handleOpenInNewWindow]"
echo ""
echo "5. Go to Network tab"
echo "6. Click the button again"
echo "7. Check these API calls:"
echo "   - GET /api/label-studio/projects/{id}/validate"
echo "   - POST /api/label-studio/projects/ensure"
echo "   - GET /api/label-studio/projects/{id}/auth-url"
echo ""
echo "8. Report the following:"
echo "   - HTTP status codes"
echo "   - Response bodies"
echo "   - Any error messages in Console"
echo ""
echo "========================================="
