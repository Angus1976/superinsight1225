# Label Studio Personal Access Token Setup Guide

## Current Status

✅ **Code Updated**: The backend now supports Personal Access Token authentication
❌ **Token Invalid**: The current token in `.env` is not valid for this Label Studio instance

## Problem Analysis

The token provided is returning 401 errors with "Token is invalid" message. This indicates:

1. **Signature Mismatch**: The token was generated with a different SECRET_KEY
2. **Wrong Instance**: The token might be from a different Label Studio installation
3. **Token Revoked**: The token may have been revoked or expired

## Solution: Generate New Personal Access Token

### Step 1: Access Label Studio UI

Open Label Studio in your browser:
```
http://localhost:8080
```

### Step 2: Login

Use your Label Studio credentials to login.

### Step 3: Navigate to Account Settings

1. Click your **user icon** in the upper right corner
2. Select **Account & Settings**

### Step 4: Generate Personal Access Token

1. In the left sidebar, click **Personal Access Token**
2. Click **Create Token** or **Generate Token** button
3. **Copy the token immediately** - it will only be shown once!

### Step 5: Update .env File

Replace the current token in `.env` file:

```bash
# Open .env file
nano .env

# Find this line:
LABEL_STUDIO_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Replace with your new token:
LABEL_STUDIO_API_TOKEN=<YOUR_NEW_TOKEN_HERE>

# Save and exit (Ctrl+X, then Y, then Enter)
```

### Step 6: Restart Backend Container

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose restart app
```

### Step 7: Test Authentication

Run the integration test:

```bash
python3 docker-compose-integration-test.py
```

Expected result: All 9 tests should pass ✅

## Authentication Flow (Technical Details)

### Personal Access Token (Recommended)

Personal Access Tokens are JWT refresh tokens that provide enhanced security:

1. **Generate PAT** from Label Studio UI
2. **Exchange for Access Token**: POST to `/api/token/refresh` with PAT
3. **Use Access Token**: Include in API requests with `Authorization: Bearer <access-token>`
4. **Token Expires**: Access tokens expire after ~5 minutes
5. **Auto-Refresh**: Backend automatically refreshes when needed

**Advantages**:
- More secure (short-lived access tokens)
- Can be revoked from UI
- Supports TTL (Time To Live) in Enterprise edition

### Legacy Token (Alternative)

If Personal Access Token doesn't work, you can use Legacy Token:

1. In Account & Settings, click **Legacy Token** instead
2. Copy the token
3. Update `.env` with the legacy token
4. Backend will automatically detect and use `Token` prefix instead of `Bearer`

**Note**: Legacy tokens don't expire but are less secure.

## Troubleshooting

### Issue: "Token is invalid" (401)

**Cause**: Token signature doesn't match Label Studio's SECRET_KEY

**Solution**:
1. Generate a **new** token from the current Label Studio instance
2. Make sure you're copying the token from http://localhost:8080 (not a different instance)
3. Copy the **entire** token (JWT tokens are long, ~200+ characters)

### Issue: "Authentication credentials were not provided" (401)

**Cause**: Token not being sent correctly or wrong format

**Solution**:
1. Check that token is in `.env` file
2. Restart backend container after updating `.env`
3. Verify token format (should start with `eyJ...`)

### Issue: Token refresh endpoint returns 400

**Cause**: Empty or malformed token

**Solution**:
1. Check `.env` file has the token on a single line
2. No spaces or line breaks in the token
3. Token should be the complete JWT string

### Issue: Cannot find Personal Access Token in UI

**Cause**: Feature not enabled for organization

**Solution**:
1. Go to Organization → Settings → Access Token Settings
2. Enable "Personal Access Token"
3. Or use "Legacy Token" instead

## Verification Steps

After setting up the new token, verify it works:

### 1. Test Token Directly

```bash
python3 test_label_studio_token.py
```

Expected output:
```
Test 3: Refresh Personal Access Token
Status: 200
Response: {"access":"eyJ..."}

Test 4: Using access token from refresh
Status: 200
Response: {"id":1,"username":"admin",...}
```

### 2. Test Integration

```bash
python3 docker-compose-integration-test.py
```

Expected: 9/9 tests passing

### 3. Test Task Sync

Create a task and sync to Label Studio:

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Task",
    "description": "Testing Label Studio sync",
    "priority": "medium",
    "annotation_type": "text_classification"
  }'
```

Then sync:

```bash
curl -X POST http://localhost:8000/api/tasks/<task-id>/sync-label-studio \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json"
```

## Code Changes Made

### 1. Personal Access Token Support

**File**: `src/label_studio/integration.py`

- Added PAT detection (JWT format check)
- Implemented token refresh flow (`_ensure_access_token()`)
- Auto-refresh before expiration (5 minute TTL)
- Proper error handling for token expiration

### 2. Authentication Method Detection

The backend now automatically detects:

1. **JWT Authentication**: If `LABEL_STUDIO_USERNAME` and `LABEL_STUDIO_PASSWORD` are set
2. **Personal Access Token**: If `LABEL_STUDIO_API_TOKEN` is JWT format (3 parts separated by dots)
3. **Legacy Token**: If `LABEL_STUDIO_API_TOKEN` is not JWT format

### 3. Header Format

- **Personal Access Token**: `Authorization: Bearer <access-token>`
- **Legacy Token**: `Authorization: Token <token>`
- **JWT Auth**: `Authorization: Bearer <jwt-token>`

## References

- [Label Studio API Documentation](https://api.labelstud.io/api-reference/introduction/getting-started)
- [Label Studio Access Tokens Guide](https://labelstud.io/guide/access_tokens)
- [Label Studio GitHub](https://github.com/HumanSignal/label-studio)

## Next Steps

1. ✅ Generate new Personal Access Token from Label Studio UI
2. ✅ Update `.env` file with new token
3. ✅ Restart backend container
4. ✅ Run integration tests
5. ✅ Verify task sync works

---

**Last Updated**: 2026-01-27
**Status**: Waiting for user to generate new token
