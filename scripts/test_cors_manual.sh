#!/bin/bash
# Manual CORS testing script
# Tests CORS configuration for AI Assistant OpenClaw Integration

echo "=== Testing CORS Configuration ==="
echo ""

# Backend URL
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-http://localhost:5173}"

echo "Backend URL: $BACKEND_URL"
echo "Frontend Origin: $FRONTEND_ORIGIN"
echo ""

# Test 1: Preflight request
echo "Test 1: CORS Preflight Request"
echo "--------------------------------"
curl -i -X OPTIONS "$BACKEND_URL/api/chat/stream" \
  -H "Origin: $FRONTEND_ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization"
echo ""
echo ""

# Test 2: Check health endpoint with CORS
echo "Test 2: Health Endpoint with CORS"
echo "-----------------------------------"
curl -i -X GET "$BACKEND_URL/health" \
  -H "Origin: $FRONTEND_ORIGIN"
echo ""
echo ""

# Test 3: Check OpenClaw status endpoint
echo "Test 3: OpenClaw Status Endpoint (requires auth)"
echo "-------------------------------------------------"
curl -i -X GET "$BACKEND_URL/api/chat/openclaw-status" \
  -H "Origin: $FRONTEND_ORIGIN" \
  -H "Content-Type: application/json"
echo ""
echo ""

# Test 4: Verify SSE streaming headers
echo "Test 4: SSE Streaming Endpoint Headers"
echo "---------------------------------------"
echo "Note: This will fail without authentication, but we can check CORS headers"
curl -i -X POST "$BACKEND_URL/api/chat/stream" \
  -H "Origin: $FRONTEND_ORIGIN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}],"mode":"direct"}' \
  --max-time 2 2>&1 | head -20
echo ""
echo ""

echo "=== CORS Configuration Test Complete ==="
echo ""
echo "Expected Results:"
echo "1. Preflight should return 200/204 with Access-Control-Allow-* headers"
echo "2. Health endpoint should return 200 with Access-Control-Allow-Origin"
echo "3. OpenClaw status should return 401 (auth required) with CORS headers"
echo "4. SSE endpoint should return 401 (auth required) with CORS headers"
echo ""
echo "Key Headers to Check:"
echo "- Access-Control-Allow-Origin: $FRONTEND_ORIGIN"
echo "- Access-Control-Allow-Credentials: true (if not using wildcard)"
echo "- Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS"
echo "- Access-Control-Expose-Headers: should include X-Accel-Buffering"
