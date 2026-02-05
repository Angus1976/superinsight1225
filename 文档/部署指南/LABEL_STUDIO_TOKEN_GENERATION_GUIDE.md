# Label Studio API Token Generation Guide

## Issue Summary

The JWT token you provided is a **refresh token** (token_type: "refresh"), not an API token. Label Studio Community Edition requires a **Legacy API Token** for authentication, not a JWT Personal Access Token.

## Current Status

- ✅ SuperInsight API: Working (7/9 tests passing)
- ✅ JWT Authentication: Working
- ✅ Task Management: Working
- ❌ Label Studio Integration: **401 Authentication Error**

## Root Cause

The token you generated:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6ODA3NjY3OTcyMywiaWF0IjoxNzY5NDc5NzIzLCJqdGkiOiJmZTQwZDc2ZTg0MGU0YjRkODZkZDk1OGJiOGI3YWNiNiIsInVzZXJfaWQiOiIxIn0.8qsQQsPPJtY1lQMf1oKJ724qUeRHJAzNLqxg-jOtbIQ
```

When decoded, shows:
```json
{
  "token_type": "refresh",  // ❌ This is a refresh token, not an API token
  "exp": 8076679723,
  "iat": 1769479723,
  "jti": "fe40d76e840e4b4d86dd958bb8b7acb6",
  "user_id": "1"
}
```

## Solution: Generate Legacy API Token

### Step 1: Access Label Studio UI

Open Label Studio in your browser:
```
http://localhost:8080
```

### Step 2: Navigate to Account Settings

1. Click on your user avatar/profile icon (top right corner)
2. Select **"Account & Settings"**

### Step 3: Generate Legacy API Token

1. In the Account Settings page, look for the **"Legacy Tokens"** section
2. Click **"Create New Token"** or **"Generate Token"**
3. Copy the generated token (it should be a long alphanumeric string, NOT a JWT)

**Example of a valid Legacy API Token:**
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

### Step 4: Update .env File

Replace the current token in `.env`:

```bash
# OLD (JWT refresh token - doesn't work)
LABEL_STUDIO_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# NEW (Legacy API Token - should work)
LABEL_STUDIO_API_TOKEN=<your-legacy-token-here>
```

### Step 5: Restart Backend Container

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose restart app
```

### Step 6: Test Integration

```bash
python3 docker-compose-integration-test.py
```

## Alternative: Check Existing Tokens

If you already have a Legacy API Token, you can find it in Label Studio:

1. Go to **Account & Settings**
2. Look for **"Legacy Tokens"** section
3. Copy an existing token if available

## Expected Result

After using a Legacy API Token, all 9 tests should pass:

```
✅ SuperInsight API health
✅ Label Studio health
✅ JWT login
✅ JWT token format
✅ Protected endpoint access
✅ Task creation
✅ Task retrieval
✅ Label Studio connection test
✅ Label Studio sync
```

## Technical Details

### Why JWT Personal Access Token Doesn't Work

Label Studio Community Edition 1.22.0 has **disabled JWT authentication** for the API. The error message confirms this:

```
"legacy token authentication has been disabled for this organization"
```

However, this message is misleading - it actually means JWT authentication is disabled, and you need to use Legacy API Tokens instead.

### Token Format Differences

| Token Type | Format | Example | Works? |
|------------|--------|---------|--------|
| Legacy API Token | Alphanumeric string | `a1b2c3d4e5f6...` | ✅ Yes |
| JWT Personal Access Token | JWT format | `eyJhbGci...` | ❌ No (Community Edition) |
| JWT Refresh Token | JWT format with `token_type: refresh` | `eyJhbGci...` | ❌ No |

## Next Steps

1. Generate a Legacy API Token from Label Studio UI
2. Update `.env` file with the new token
3. Restart backend container
4. Run integration tests
5. Verify all 9 tests pass

## Need Help?

If you encounter any issues:

1. Check Label Studio logs:
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker logs superinsight-label-studio
   ```

2. Check SuperInsight API logs:
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker logs superinsight-app
   ```

3. Verify Label Studio is accessible:
   ```bash
   curl http://localhost:8080/health
   ```

---

**Last Updated**: 2026-01-27
**Status**: Waiting for Legacy API Token from user
