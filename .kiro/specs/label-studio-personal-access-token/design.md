# Design Document - Label Studio Personal Access Token Authentication

**Version**: 1.0  
**Status**: ✅ Complete  
**Last Updated**: 2026-01-27

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Label Studio PAT Authentication             │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    SuperInsight Backend                       │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         LabelStudioIntegration Class                   │  │
│  │                                                        │  │
│  │  - _personal_access_token: str (refresh token)        │  │
│  │  - _access_token: str (short-lived)                   │  │
│  │  - _access_token_expires_at: datetime                 │  │
│  │  - _lock: asyncio.Lock()                              │  │
│  │                                                        │  │
│  │  Methods:                                              │  │
│  │  - _is_jwt_token(token) → bool                        │  │
│  │  - _ensure_access_token() → None (async)             │  │
│  │  - _get_headers() → Dict (async)                      │  │
│  │  - create_project() → Dict (async)                    │  │
│  │  - import_tasks() → None (async)                      │  │
│  │  - test_connection() → Dict (async)                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                           ↓                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         LabelStudioConfig Class                        │  │
│  │                                                        │  │
│  │  - api_token: str (from .env)                         │  │
│  │  - base_url: str                                       │  │
│  │                                                        │  │
│  │  Methods:                                              │  │
│  │  - validate() → None                                   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    Label Studio API                           │
│                                                               │
│  1. POST /api/token/refresh                                  │
│     Request: {"refresh": "<personal-access-token>"}          │
│     Response: {"access": "<access-token>"}                   │
│                                                               │
│  2. GET /api/projects/{id}                                   │
│     Header: Authorization: Bearer <access-token>            │
│                                                               │
│  3. POST /api/projects                                       │
│     Header: Authorization: Bearer <access-token>            │
│     Body: {"title": "...", "description": "..."}            │
└──────────────────────────────────────────────────────────────┘
```

## Authentication Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              Personal Access Token Authentication Flow        │
└─────────────────────────────────────────────────────────────┘

1. User generates PAT in Label Studio UI
   ↓
2. PAT stored in .env as LABEL_STUDIO_API_TOKEN
   ↓
3. System startup: LabelStudioIntegration.__init__()
   ├─ Read LABEL_STUDIO_API_TOKEN from config
   ├─ Detect JWT format (3 parts separated by dots)
   ├─ If JWT: Set _personal_access_token = token
   ├─ If not JWT: Use as legacy API token
   ↓
4. First API call: _ensure_access_token()
   ├─ Check if _access_token exists and not expired
   ├─ If expired or missing:
   │  ├─ POST /api/token/refresh with PAT
   │  ├─ Parse response: {"access": "<token>"}
   │  ├─ Decode JWT to get expiration time
   │  ├─ Store _access_token and _access_token_expires_at
   │  └─ Log "Access token refreshed, expires at {time}"
   ├─ Return (token is now valid)
   ↓
5. Make API call: _get_headers()
   ├─ Call _ensure_access_token() (may refresh if needed)
   ├─ Return {"Authorization": "Bearer <access-token>"}
   ↓
6. API call succeeds
   ↓
7. Next API call (within 5 minutes):
   ├─ _ensure_access_token() checks expiration
   ├─ Token still valid (not within 30s of expiration)
   ├─ Return existing token (no refresh needed)
   ↓
8. API call succeeds (fast path)
   ↓
9. Token expires in 30 seconds:
   ├─ Next API call triggers _ensure_access_token()
   ├─ Token is within 30s of expiration
   ├─ Refresh token (same as step 4)
   ↓
10. Loop continues...
```

## Sequence Diagram: Token Refresh

```
Client                 SuperInsight              Label Studio
  │                         │                          │
  ├─ API Call ─────────────>│                          │
  │                         │                          │
  │                         ├─ _ensure_access_token()  │
  │                         │                          │
  │                         ├─ Check expiration        │
  │                         │  (within 30s?)           │
  │                         │                          │
  │                         ├─ YES: POST /api/token/refresh ──>│
  │                         │  {"refresh": "<PAT>"}    │
  │                         │                          │
  │                         │<─ {"access": "<token>"} ─┤
  │                         │                          │
  │                         ├─ Decode JWT              │
  │                         ├─ Extract exp time        │
  │                         ├─ Store _access_token     │
  │                         │                          │
  │                         ├─ _get_headers()          │
  │                         │  Returns Bearer header   │
  │                         │                          │
  │                         ├─ API Call ──────────────>│
  │                         │  Authorization: Bearer   │
  │                         │                          │
  │                         │<─ Response ──────────────┤
  │                         │                          │
  │<─ Response ────────────┤                          │
  │                         │                          │
```

## Sequence Diagram: Concurrent Requests

```
Request 1              Request 2              SuperInsight
  │                      │                         │
  ├─ API Call ──────────>│                         │
  │                      ├─ API Call ────────────>│
  │                      │                         │
  │                      │                    _ensure_access_token()
  │                      │                    Check: token expired?
  │                      │                    YES → Acquire lock
  │                      │                         │
  │                      │                    POST /api/token/refresh
  │                      │                         │
  │                      │                    (Request 2 waits for lock)
  │                      │                         │
  │                      │                    Receive new token
  │                      │                    Release lock
  │                      │                         │
  │                      │                    (Request 2 acquires lock)
  │                      │                    Check: token expired?
  │                      │                    NO → Use existing token
  │                      │                    Release lock
  │                      │                         │
  │<─ Response ──────────┤                         │
  │                      │<─ Response ────────────┤
  │                      │                         │
```

## Component Design

### 1. LabelStudioIntegration Class

**Location**: `src/label_studio/integration.py`

```python
class LabelStudioIntegration:
    """Label Studio integration with Personal Access Token support"""
    
    def __init__(self, config: Optional[LabelStudioConfig] = None):
        self.config = config or LabelStudioConfig()
        self.base_url = self.config.base_url.rstrip('/')
        self.api_token = self.config.api_token
        
        # Personal Access Token support
        self._personal_access_token: Optional[str] = None
        self._access_token: Optional[str] = None
        self._access_token_expires_at: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
        # Detect authentication method
        if self.api_token and self._is_jwt_token(self.api_token):
            logger.info("Detected Personal Access Token (JWT refresh token)")
            self._personal_access_token = self.api_token
            self._auth_method = 'personal_access_token'
        else:
            logger.info("Using legacy API token authentication")
            self._auth_method = 'api_token'
    
    def _is_jwt_token(self, token: str) -> bool:
        """Check if token is in JWT format (3 parts separated by dots)"""
        parts = token.split('.')
        return len(parts) == 3
    
    async def _ensure_access_token(self) -> None:
        """Ensure access token is valid, refresh if needed"""
        async with self._lock:
            # Check if token is still valid (30s buffer)
            if self._access_token and self._access_token_expires_at:
                if datetime.utcnow() < self._access_token_expires_at - timedelta(seconds=30):
                    return
            
            # Refresh access token
            logger.info("[Label Studio] Refreshing Personal Access Token")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/token/refresh",
                    headers={'Content-Type': 'application/json'},
                    json={'refresh': self._personal_access_token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._access_token = data.get('access')
                    
                    # Parse JWT to get expiration time
                    decoded = jwt.decode(
                        self._access_token,
                        options={"verify_signature": False}
                    )
                    exp_timestamp = decoded.get('exp')
                    self._access_token_expires_at = datetime.utcfromtimestamp(exp_timestamp)
                    
                    logger.info(
                        f"[Label Studio] Access token refreshed, "
                        f"expires at {self._access_token_expires_at.isoformat()}"
                    )
                else:
                    raise LabelStudioAuthenticationError(
                        f"Failed to refresh token: {response.status_code}"
                    )
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        if self._auth_method == 'personal_access_token':
            await self._ensure_access_token()
            return {
                'Authorization': f'Bearer {self._access_token}',
                'Content-Type': 'application/json'
            }
        else:
            # Legacy API token
            return {
                'Authorization': f'Token {self.api_token}',
                'Content-Type': 'application/json'
            }
    
    async def create_project(self, name: str, description: str = "") -> Dict:
        """Create a Label Studio project"""
        headers = await self._get_headers()
        
        # Handle project title length limit (50 chars)
        max_title_length = 50
        title_suffix = f" ({name[:8]})"
        available_length = max_title_length - len(title_suffix)
        
        if len(name) > available_length:
            title = f"{name[:available_length-3]}...{title_suffix}"
        else:
            title = f"{name}{title_suffix}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/projects",
                headers=headers,
                json={
                    "title": title,
                    "description": description
                }
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                raise LabelStudioError(f"Failed to create project: {response.status_code}")
```

### 2. Token Refresh Logic

**Key Features**:
- Detects JWT format automatically
- Exchanges refresh token for access token
- Parses JWT to extract expiration time
- Refreshes token 30 seconds before expiration
- Uses `asyncio.Lock()` for thread-safe concurrent access
- Logs all authentication events

### 3. Project Title Truncation

**Location**: `src/api/label_studio_sync.py`

```python
def truncate_project_title(task_name: str, task_id: str) -> str:
    """Truncate project title to 50 character limit"""
    max_title_length = 50
    title_suffix = f" ({task_id[:8]})"
    available_length = max_title_length - len(title_suffix)
    
    if len(task_name) > available_length:
        title_prefix = task_name[:available_length-3] + "..."
    else:
        title_prefix = task_name
    
    return f"{title_prefix}{title_suffix}"
```

**Example**:
- Input: `Integration Test Task`, `6b5805c9-9b11-4cb5-bd73-2f373d26963c`
- Output: `Integration Test Task (6b5805c9)` (38 chars)

## Data Models

### Token Storage

```python
@dataclass
class TokenState:
    """Current token state"""
    access_token: Optional[str] = None
    access_token_expires_at: Optional[datetime] = None
    personal_access_token: Optional[str] = None
    auth_method: str = 'api_token'  # 'api_token' or 'personal_access_token'
    last_refresh_at: Optional[datetime] = None
```

### Configuration

```python
class LabelStudioConfig:
    """Label Studio configuration"""
    base_url: str = "http://localhost:8080"
    api_token: str = ""  # Can be API token or Personal Access Token
    
    def validate(self) -> None:
        """Validate configuration"""
        if not self.api_token:
            raise ValueError("LABEL_STUDIO_API_TOKEN is required")
        
        if not self.base_url:
            raise ValueError("LABEL_STUDIO_URL is required")
```

## Error Handling

### Authentication Errors

```python
class LabelStudioAuthenticationError(Exception):
    """Raised when authentication fails"""
    pass

# Scenarios:
# 1. Invalid token: "Token is invalid"
# 2. Expired token: "Token has expired"
# 3. Malformed request: "Malformed request"
# 4. Network error: Retry with exponential backoff
```

### Recovery Strategy

```
Token Refresh Fails (401)
  ↓
Raise LabelStudioAuthenticationError
  ↓
Log error with status code
  ↓
Suggest: Generate new Personal Access Token
```

## Concurrency Model

### Thread Safety

- Uses `asyncio.Lock()` for async-safe synchronization
- Only one token refresh happens at a time
- Other requests wait for refresh to complete
- No deadlocks (async-safe implementation)

### Lock Acquisition Pattern

```python
async with self._lock:
    # Check if refresh needed
    if token_expired:
        # Refresh token
        # Update state
    # Return token
```

## Integration Points

### 1. API Endpoints

- `POST /api/token/refresh` - Exchange refresh token for access token
- `GET /api/projects/{id}` - Get project info (uses Bearer token)
- `POST /api/projects` - Create project (uses Bearer token)
- `GET /api/tasks` - List tasks (uses Bearer token)

### 2. Existing Features

- Task creation and sync
- Project management
- Annotation export
- Connection testing

## Security Considerations

### Token Storage

- Tokens stored in memory only (not persistent)
- Cleared on application shutdown
- Cleared on authentication failure

### Logging

- Tokens never logged
- Only log "Token refreshed" without token value
- Log authentication method and status

### HTTPS

- Token refresh requires HTTPS in production
- Warning logged if HTTP used with tokens

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Token detection | <1ms | String split operation |
| Token refresh | ~100ms | Network call to Label Studio |
| Token validation | <1ms | Datetime comparison |
| Concurrent request wait | <100ms | Lock acquisition time |

## Backward Compatibility

### Legacy API Token Support

```
If token is NOT in JWT format:
  ├─ Use as legacy API token
  ├─ Use "Authorization: Token <token>" header
  ├─ No token refresh needed
  └─ Works as before
```

### Migration Path

```
Old: LABEL_STUDIO_API_TOKEN=abc123def456
New: LABEL_STUDIO_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

System automatically detects and switches authentication method
No code changes required
```

## Testing Strategy

### Unit Tests

- Token detection (JWT vs legacy)
- Token refresh logic
- Header generation
- Project title truncation

### Integration Tests

- End-to-end authentication flow
- Concurrent request handling
- Error recovery
- Backward compatibility

### Property-Based Tests

- Token refresh always produces valid access token
- Concurrent requests never cause deadlock
- Token expiration always detected correctly

## Deployment Considerations

### Environment Variables

```bash
# .env file
LABEL_STUDIO_URL=http://label-studio:8080
LABEL_STUDIO_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Container Restart

```bash
# Changes to .env require container restart
docker compose down app
docker compose up -d app
```

### Verification

```bash
# Check token is loaded
docker exec superinsight-app printenv LABEL_STUDIO_API_TOKEN

# Check authentication works
curl http://localhost:8000/api/tasks/label-studio/test-connection \
  -H "Authorization: Bearer <jwt-token>"
```

## Correctness Properties

### Property 1: Token Detection Accuracy
**For any** token string, the system should correctly identify whether it's JWT format or legacy format.

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Token Refresh Success
**For any** valid Personal Access Token, calling `/api/token/refresh` should return a valid access token with correct expiration time.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 3: Automatic Renewal
**For any** access token, the system should refresh it before expiration (30s buffer) and use the new token for subsequent requests.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

### Property 4: Bearer Token Format
**For any** API request using Personal Access Token, the Authorization header should be `Bearer <access-token>`.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

### Property 5: Concurrent Request Safety
**For any** number of concurrent API calls, only one token refresh should occur, and all requests should use the same refreshed token.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

### Property 6: Title Length Compliance
**For any** task name and task ID, the generated project title should be ≤50 characters and include the task ID.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

### Property 7: Error Handling
**For any** authentication failure, the system should raise `LabelStudioAuthenticationError` with a clear error message.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

### Property 8: Backward Compatibility
**For any** legacy API token (non-JWT format), the system should use `Authorization: Token <token>` header.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

</content>
