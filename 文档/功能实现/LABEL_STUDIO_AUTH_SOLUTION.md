# Label Studio Authentication Solution

**Date**: 2026-01-27  
**Status**: CRITICAL ISSUE IDENTIFIED  
**Priority**: HIGH

## Problem Summary

The annotation buttons ("开始标注" and "在新窗口打开") are not working because the current implementation attempts to use JWT authentication via the `/api/sessions/` endpoint, which **does not exist in Label Studio Community Edition 1.22.0**.

## Root Cause Analysis

### What We Discovered

1. **Testing Results**:
   - `POST http://localhost:8080/api/sessions/` returns **404 HTML page** (endpoint not found)
   - Label Studio version: **1.22.0 Community Edition**

2. **Documentation Research**:
   - Label Studio Community Edition uses **API Token authentication** (also called "Legacy Tokens")
   - **Personal Access Tokens (PAT)** with JWT refresh are available but require:
     - Organization-level enablement
     - Manual token generation from UI
     - `/api/token/refresh` endpoint (NOT `/api/sessions/`)
   
3. **Current Code Issues**:
   - `src/label_studio/jwt_auth.py` implements JWT authentication using `/api/sessions/` endpoint
   - This endpoint does NOT exist in Community Edition
   - The `.env` file is configured for JWT authentication (username/password)
   - API token is commented out

## Authentication Methods in Label Studio

### Method 1: Legacy API Token (Recommended for Community Edition)

**How it works**:
- Generate a token from Label Studio UI (Account & Settings)
- Token never expires (unless manually revoked)
- Use `Authorization: Token <token>` header
- **This is the standard method for Community Edition**

**Pros**:
- Simple and reliable
- Works out-of-the-box in Community Edition
- No additional configuration needed
- No token refresh logic required

**Cons**:
- Token doesn't expire automatically
- Must be manually revoked if compromised
- Less secure than PAT (but acceptable for internal use)

### Method 2: Personal Access Token (PAT) with JWT

**How it works**:
- Enable PAT at organization level in Label Studio
- Generate PAT from UI (visible only once)
- Use PAT to get short-lived access token via `/api/token/refresh`
- Use access token with `Authorization: Bearer <token>` header
- Refresh access token every ~5 minutes

**Pros**:
- More secure (tokens expire)
- Can set TTL at org level (Enterprise only)
- Can be manually revoked

**Cons**:
- **Requires organization-level enablement** (may not be available in Community Edition)
- More complex implementation
- Requires token refresh logic
- Uses `/api/token/refresh` endpoint (NOT `/api/sessions/`)

### Method 3: Username/Password Login (NOT AVAILABLE)

**Status**: **NOT SUPPORTED** in Label Studio Community Edition API

- The `/api/sessions/` endpoint does NOT exist
- Username/password is only for UI login, not API authentication
- Our current implementation is trying to use this non-existent endpoint

## Recommended Solution

### Immediate Fix: Switch to API Token Authentication

**Step 1: Generate API Token**

1. Open Label Studio UI: http://localhost:8080
2. Login with username: `admin@example.com`, password: `admin`
3. Click user icon (upper right) → "Account & Settings"
4. Go to "Legacy Tokens" or "Access Tokens" page
5. Generate a new token
6. Copy the token (it looks like: `f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17`)

**Step 2: Update `.env` File**

```bash
# Comment out JWT authentication (not supported)
# LABEL_STUDIO_USERNAME=admin@example.com
# LABEL_STUDIO_PASSWORD=admin

# Enable API Token authentication
LABEL_STUDIO_API_TOKEN=<your-generated-token-here>
```

**Step 3: Restart Backend Container**

```bash
docker-compose restart app
```

**Step 4: Test Annotation Buttons**

1. Navigate to task detail page
2. Click "开始标注" button
3. Click "在新窗口打开" button
4. Both should now work correctly

## Code Changes Required

### Option A: Minimal Changes (Recommended)

**No code changes needed!** The existing code already supports API token authentication as a fallback:

```python
# src/label_studio/config.py
def get_auth_method(self) -> str:
    """
    Determine which authentication method to use.
    
    Priority:
    1. JWT (if username and password are configured)
    2. API Token (if api_token is configured)  # ← This will be used
    3. None (raise error)
    """
    if self.username and self.password:
        return 'jwt'
    elif self.api_token:
        return 'api_token'  # ← Will use this
    else:
        raise LabelStudioConfigError(...)
```

The code will automatically detect that JWT credentials are not configured and fall back to API token authentication.

### Option B: Remove JWT Code (Optional, for cleanup)

If we want to remove the unused JWT authentication code:

1. **Remove JWT auth manager initialization** in `src/label_studio/integration.py`
2. **Remove JWT-specific methods** from `src/label_studio/config.py`
3. **Delete** `src/label_studio/jwt_auth.py` (no longer needed)
4. **Update documentation** to reflect API token-only authentication

**However, this is NOT necessary for fixing the immediate issue.**

## Alternative Solution: Enable Personal Access Tokens

If we want to use PAT instead of legacy tokens:

**Step 1: Enable PAT in Label Studio**

1. Login to Label Studio as admin
2. Go to Organization → Settings → Access Token Settings
3. Enable "Personal Access Tokens"

**Step 2: Generate PAT**

1. Go to Account & Settings → Personal Access Tokens
2. Generate new token
3. Copy the token (visible only once)

**Step 3: Update Code to Use `/api/token/refresh`**

```python
# src/label_studio/jwt_auth.py
# Change from:
refresh_url = f"{self.base_url}/api/sessions/refresh/"

# To:
refresh_url = f"{self.base_url}/api/token/refresh/"
```

**Step 4: Update `.env`**

```bash
# Use PAT as the "API token"
LABEL_STUDIO_API_TOKEN=<your-personal-access-token>
```

**Step 5: Modify Integration Code**

The integration code needs to:
1. Use PAT to get access token via `/api/token/refresh`
2. Use access token for API calls
3. Refresh access token when it expires (~5 minutes)

**Note**: This is more complex and may not be necessary for Community Edition.

## Testing Plan

### Test 1: API Token Authentication

```bash
# Test with curl
export LS_TOKEN="your-api-token-here"

# Test project list
curl -H "Authorization: Token $LS_TOKEN" \
     http://localhost:8080/api/projects/

# Should return JSON array of projects
```

### Test 2: Annotation Buttons

1. **Test "开始标注" button**:
   - Navigate to task detail page
   - Click "开始标注"
   - Should navigate to `/tasks/{id}/annotate`
   - Should show Label Studio iframe

2. **Test "在新窗口打开" button**:
   - Navigate to task detail page
   - Click "在新窗口打开"
   - Should open Label Studio in new window
   - Should be authenticated (no login prompt)
   - Should show correct language (zh or en based on user preference)

### Test 3: Language Preference

1. Switch language in SuperInsight UI (zh ↔ en)
2. Click "在新窗口打开"
3. Label Studio should open in the selected language

## Implementation Steps

### Immediate Action (Fix the Issue)

1. ✅ **Generate API token** from Label Studio UI
2. ✅ **Update `.env`** file with token
3. ✅ **Restart backend** container
4. ✅ **Test annotation buttons**

### Follow-up Actions (Optional)

1. **Update documentation** to clarify authentication methods
2. **Add error handling** for missing API token
3. **Add health check** to validate Label Studio connection
4. **Consider removing JWT code** if not needed

## Security Considerations

### API Token Security

1. **Never commit tokens to Git**:
   - `.env` is in `.gitignore` ✅
   - Use `.env.example` for template

2. **Rotate tokens periodically**:
   - Generate new token every 90 days
   - Revoke old token after rotation

3. **Use HTTPS in production**:
   - Current setup uses HTTP (localhost only)
   - Production must use HTTPS for token transmission

4. **Limit token permissions**:
   - Use project-specific tokens if available
   - Avoid using admin tokens for API access

## Conclusion

**The issue is clear**: We're trying to use JWT authentication via `/api/sessions/` endpoint which doesn't exist in Label Studio Community Edition 1.22.0.

**The solution is simple**: Use API Token authentication (Legacy Tokens) which is the standard method for Community Edition.

**No code changes required**: The existing code already supports API token authentication as a fallback. We just need to:
1. Generate an API token from Label Studio UI
2. Update `.env` file with the token
3. Restart the backend container

**Expected result**: Both annotation buttons will work correctly after this change.

---

**Next Steps**: Generate API token and update `.env` file to fix the issue immediately.
