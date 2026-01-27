# Label Studio Authentication Flow Diagram

## Current (Broken) Flow - JWT Authentication Attempt

```
┌─────────────────────────────────────────────────────────────────┐
│                     Current Flow (BROKEN)                        │
└─────────────────────────────────────────────────────────────────┘

User clicks "开始标注" or "在新窗口打开"
    │
    ├─► Frontend: TaskDetail.tsx
    │       │
    │       └─► API Call: POST /api/label-studio/auth-url
    │               │
    │               └─► Backend: src/label_studio/integration.py
    │                       │
    │                       └─► JWT Auth Manager: src/label_studio/jwt_auth.py
    │                               │
    │                               └─► POST http://label-studio:8080/api/sessions/
    │                                       │
    │                                       └─► ❌ 404 NOT FOUND
    │                                           (Endpoint doesn't exist in Community Edition)
    │
    └─► Result: Button doesn't work, no response

```

## Fixed Flow - API Token Authentication

```
┌─────────────────────────────────────────────────────────────────┐
│                     Fixed Flow (WORKING)                         │
└─────────────────────────────────────────────────────────────────┘

Step 1: Generate API Token (One-time setup)
    │
    ├─► User: Login to Label Studio UI
    │       │
    │       └─► http://localhost:8080
    │               │
    │               └─► Account & Settings → Legacy Tokens
    │                       │
    │                       └─► Generate Token
    │                               │
    │                               └─► Copy Token: f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17
    │
    └─► Update .env file:
            LABEL_STUDIO_API_TOKEN=f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17

Step 2: Runtime Flow (After restart)
    │
    ├─► User clicks "开始标注" or "在新窗口打开"
    │       │
    │       └─► Frontend: TaskDetail.tsx
    │               │
    │               └─► API Call: POST /api/label-studio/auth-url
    │                       │
    │                       └─► Backend: src/label_studio/integration.py
    │                               │
    │                               ├─► Config: src/label_studio/config.py
    │                               │       │
    │                               │       └─► get_auth_method() → 'api_token' ✅
    │                               │
    │                               └─► _get_headers()
    │                                       │
    │                                       └─► Return: {'Authorization': 'Token f6d8ca85...'}
    │                                               │
    │                                               └─► API Call to Label Studio
    │                                                       │
    │                                                       └─► ✅ 200 OK
    │                                                           (Authentication successful)
    │
    └─► Result: Button works! User can annotate.

```

## Authentication Method Comparison

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    JWT Authentication (NOT AVAILABLE)                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Endpoint: POST /api/sessions/                                           │
│  Request:  {"email": "admin@example.com", "password": "admin"}           │
│  Response: ❌ 404 NOT FOUND                                              │
│                                                                           │
│  Why it fails:                                                           │
│  - Endpoint doesn't exist in Community Edition 1.22.0                    │
│  - May be Enterprise-only feature                                        │
│  - Or available in newer versions only                                   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                  API Token Authentication (WORKING)                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Header:   Authorization: Token f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17│
│  Request:  GET /api/projects/                                            │
│  Response: ✅ 200 OK                                                     │
│            [{"id": 1, "title": "Project 1", ...}]                        │
│                                                                           │
│  Why it works:                                                           │
│  - Standard authentication method for Community Edition                  │
│  - Token generated from UI (Account & Settings)                          │
│  - Token never expires (unless manually revoked)                         │
│  - Simple and reliable                                                   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│            Personal Access Token (PAT) - Alternative Option               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Step 1: Get Access Token                                                │
│    Endpoint: POST /api/token/refresh/                                    │
│    Request:  {"refresh": "your-personal-access-token"}                   │
│    Response: {"access": "short-lived-access-token"}                      │
│                                                                           │
│  Step 2: Use Access Token                                                │
│    Header:   Authorization: Bearer <access-token>                        │
│    Request:  GET /api/projects/                                          │
│    Response: ✅ 200 OK                                                   │
│                                                                           │
│  Notes:                                                                  │
│  - Requires organization-level enablement                                │
│  - Access token expires in ~5 minutes                                    │
│  - Need to refresh token periodically                                    │
│  - More complex than API Token                                           │
│  - May not be available in Community Edition                             │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

## Code Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│              Backend Authentication Flow                         │
└─────────────────────────────────────────────────────────────────┘

LabelStudioIntegration.__init__()
    │
    ├─► LabelStudioConfig()
    │       │
    │       ├─► Read from .env:
    │       │   - LABEL_STUDIO_URL
    │       │   - LABEL_STUDIO_USERNAME (commented out)
    │       │   - LABEL_STUDIO_PASSWORD (commented out)
    │       │   - LABEL_STUDIO_API_TOKEN ✅
    │       │
    │       └─► get_auth_method()
    │               │
    │               ├─► if username and password:
    │               │       return 'jwt'  ❌ (not configured)
    │               │
    │               ├─► elif api_token:
    │               │       return 'api_token'  ✅ (configured)
    │               │
    │               └─► else:
    │                       raise Error
    │
    └─► Set auth_method = 'api_token' ✅

API Request Flow:
    │
    ├─► _get_headers()
    │       │
    │       ├─► if auth_method == 'jwt':
    │       │       await jwt_auth_manager._ensure_authenticated()
    │       │       return jwt_auth_manager.get_auth_header()
    │       │
    │       └─► else:  # api_token
    │               return {'Authorization': f'Token {self.api_token}'}  ✅
    │
    └─► Make API call with headers
            │
            └─► Label Studio validates token
                    │
                    └─► ✅ Success!

```

## Configuration Comparison

### Before (Broken)

```bash
# .env file
LABEL_STUDIO_URL=http://label-studio:8080
LABEL_STUDIO_USERNAME=admin@example.com  # ❌ Not supported
LABEL_STUDIO_PASSWORD=admin              # ❌ Not supported
# LABEL_STUDIO_API_TOKEN=...             # ❌ Commented out
```

**Result**: JWT authentication fails → 404 error → Buttons don't work

### After (Fixed)

```bash
# .env file
LABEL_STUDIO_URL=http://label-studio:8080
# LABEL_STUDIO_USERNAME=admin@example.com  # ✅ Commented out
# LABEL_STUDIO_PASSWORD=admin              # ✅ Commented out
LABEL_STUDIO_API_TOKEN=f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17  # ✅ Enabled
```

**Result**: API Token authentication works → 200 OK → Buttons work!

## Security Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Token Security Flow                           │
└─────────────────────────────────────────────────────────────────┘

Token Generation (One-time):
    │
    ├─► User logs into Label Studio UI
    │       │
    │       └─► Authenticated session established
    │               │
    │               └─► Navigate to Account & Settings
    │                       │
    │                       └─► Generate API Token
    │                               │
    │                               ├─► Token stored in Label Studio database
    │                               │
    │                               └─► Token displayed to user (once)
    │                                       │
    │                                       └─► User copies token
    │
    └─► Token stored in .env file (not in Git)

Token Usage (Runtime):
    │
    ├─► Backend reads token from .env
    │       │
    │       └─► Token stored in memory (not logged)
    │               │
    │               └─► Token included in API request headers
    │                       │
    │                       └─► Label Studio validates token
    │                               │
    │                               ├─► Check if token exists in database
    │                               ├─► Check if token is revoked
    │                               └─► Check token permissions
    │                                       │
    │                                       └─► ✅ Grant access

Token Rotation (Periodic):
    │
    ├─► Generate new token
    │       │
    │       └─► Update .env file
    │               │
    │               └─► Restart backend
    │                       │
    │                       └─► Revoke old token
    │                               │
    │                               └─► Old token no longer works

```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Error Handling Flow                           │
└─────────────────────────────────────────────────────────────────┘

API Request:
    │
    ├─► 200 OK
    │       └─► ✅ Success! Process response
    │
    ├─► 401 Unauthorized
    │       │
    │       ├─► Check error message:
    │       │   - "Invalid token" → Token is wrong
    │       │   - "Token expired" → Token was revoked
    │       │   - "Token not found" → Token doesn't exist
    │       │
    │       └─► Action: Generate new token and update .env
    │
    ├─► 403 Forbidden
    │       │
    │       └─► Token is valid but lacks permissions
    │               │
    │               └─► Action: Use admin token or grant permissions
    │
    ├─► 404 Not Found
    │       │
    │       └─► Endpoint doesn't exist (like /api/sessions/)
    │               │
    │               └─► Action: Use correct endpoint or authentication method
    │
    └─► 503 Service Unavailable
            │
            └─► Label Studio is down or not responding
                    │
                    └─► Action: Check Label Studio container status

```

## Summary

### Problem
```
JWT Auth (/api/sessions/) → 404 NOT FOUND → Buttons don't work
```

### Solution
```
API Token Auth (Token header) → 200 OK → Buttons work!
```

### Implementation
```
1. Generate token from Label Studio UI
2. Update .env: LABEL_STUDIO_API_TOKEN=<token>
3. Restart backend: docker-compose restart app
4. Test buttons: Should work now!
```

---

**Visual Summary**: The fix is simple - switch from JWT authentication (which doesn't exist) to API Token authentication (which is the standard method for Community Edition).
