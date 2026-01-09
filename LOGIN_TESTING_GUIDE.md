# Frontend Login Testing Guide

This guide provides step-by-step instructions for testing the login functionality with different user roles.

## System Architecture

### Frontend
- **Framework**: React 19 with Vite
- **State Management**: Zustand (authStore)
- **UI Components**: Ant Design
- **API Client**: Axios with interceptors
- **Dev Server**: http://localhost:5173

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Authentication**: JWT tokens
- **API Base**: http://localhost:8000

### Services (Docker)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Neo4j**: localhost:7474, 7687
- **Label Studio**: localhost:8080

## Prerequisites

### 1. Start Docker Services
```bash
docker-compose -f docker-compose.local.yml up -d
```

Verify all services are running:
```bash
docker-compose -f docker-compose.local.yml ps
```

Expected output:
```
NAME                COMMAND                  SERVICE             STATUS
postgres            "docker-entrypoint.s…"   postgres            Up (healthy)
redis               "redis-server --appe…"   redis               Up (healthy)
neo4j               "tini -s /sbin/init.…"   neo4j               Up (healthy)
label-studio        "docker-entrypoint.s…"   label-studio        Up (healthy)
```

### 2. Create Test Users
```bash
python create_test_users_for_login.py
```

This creates 5 test users with different roles:
- **admin_user** (Admin) - Full system access
- **business_expert** (Business Expert) - Business operations
- **technical_expert** (Technical Expert) - Technical operations
- **contractor** (Contractor) - Limited access
- **viewer** (Viewer) - Read-only access

### 3. Start Backend API Server
```bash
python main.py
```

The backend will start on http://localhost:8000

### 4. Start Frontend Dev Server
```bash
cd frontend
npm run dev
```

The frontend will start on http://localhost:5173

## Login Testing Scenarios

### Scenario 1: Admin User Login
**Objective**: Test admin user login and verify full system access

**Steps**:
1. Navigate to http://localhost:5173/login
2. Enter credentials:
   - Username: `admin_user`
   - Password: `Admin@123456`
   - Tenant: `default_tenant` (if tenant selection is available)
3. Click "Login"

**Expected Results**:
- ✓ Login succeeds
- ✓ Redirected to dashboard
- ✓ User info displayed in header
- ✓ All menu items visible
- ✓ Admin features accessible (Settings, User Management, etc.)

**Verification**:
- Check browser console for no errors
- Check network tab for successful `/api/security/login` request
- Verify JWT token stored in localStorage
- Check user role is "admin"

### Scenario 2: Business Expert Login
**Objective**: Test business expert user login and verify role-based access

**Steps**:
1. Navigate to http://localhost:5173/login
2. Enter credentials:
   - Username: `business_expert`
   - Password: `Business@123456`
3. Click "Login"

**Expected Results**:
- ✓ Login succeeds
- ✓ Redirected to dashboard
- ✓ Business-specific features visible
- ✓ Admin features hidden/disabled
- ✓ Can access quality and billing modules

**Verification**:
- Verify user role is "business_expert"
- Check that admin-only menu items are not visible
- Verify access to business metrics and reports

### Scenario 3: Technical Expert Login
**Objective**: Test technical expert user login

**Steps**:
1. Navigate to http://localhost:5173/login
2. Enter credentials:
   - Username: `technical_expert`
   - Password: `Technical@123456`
3. Click "Login"

**Expected Results**:
- ✓ Login succeeds
- ✓ Technical features visible (System Monitoring, etc.)
- ✓ Business features may be limited
- ✓ Can access system health and performance metrics

### Scenario 4: Contractor Login
**Objective**: Test contractor user login with limited access

**Steps**:
1. Navigate to http://localhost:5173/login
2. Enter credentials:
   - Username: `contractor`
   - Password: `Contractor@123456`
3. Click "Login"

**Expected Results**:
- ✓ Login succeeds
- ✓ Limited menu items visible
- ✓ Cannot access admin or sensitive features
- ✓ Can access assigned projects/tasks

### Scenario 5: Viewer Login
**Objective**: Test viewer user login with read-only access

**Steps**:
1. Navigate to http://localhost:5173/login
2. Enter credentials:
   - Username: `viewer`
   - Password: `Viewer@123456`
3. Click "Login"

**Expected Results**:
- ✓ Login succeeds
- ✓ Can view dashboards and reports
- ✓ Cannot modify any data
- ✓ Limited to read-only operations

### Scenario 6: Invalid Credentials
**Objective**: Test login failure with invalid credentials

**Steps**:
1. Navigate to http://localhost:5173/login
2. Enter invalid credentials:
   - Username: `admin_user`
   - Password: `WrongPassword123`
3. Click "Login"

**Expected Results**:
- ✓ Login fails
- ✓ Error message displayed: "Invalid username or password"
- ✓ User remains on login page
- ✓ No token stored in localStorage

### Scenario 7: Logout
**Objective**: Test logout functionality

**Steps**:
1. Login with any user
2. Click user menu in header
3. Click "Logout"

**Expected Results**:
- ✓ Logout succeeds
- ✓ Redirected to login page
- ✓ Token cleared from localStorage
- ✓ User state cleared

### Scenario 8: Session Persistence
**Objective**: Test that login session persists across page refreshes

**Steps**:
1. Login with admin_user
2. Verify dashboard loads
3. Refresh the page (F5)
4. Verify user is still logged in

**Expected Results**:
- ✓ User remains logged in after refresh
- ✓ Dashboard loads without re-login
- ✓ User info still displayed

### Scenario 9: Tenant Selection (if multi-tenant)
**Objective**: Test tenant selection during login

**Steps**:
1. Navigate to http://localhost:5173/login
2. If tenant dropdown is visible:
   - Select a tenant from the dropdown
   - Enter credentials
   - Click "Login"

**Expected Results**:
- ✓ Login succeeds with selected tenant
- ✓ User context set to selected tenant
- ✓ Can switch tenants from user menu

### Scenario 10: Remember Me
**Objective**: Test "Remember Me" functionality

**Steps**:
1. Navigate to http://localhost:5173/login
2. Check "Remember Me" checkbox
3. Enter credentials and login
4. Close browser/tab
5. Reopen http://localhost:5173/login

**Expected Results**:
- ✓ Username may be pre-filled (if implemented)
- ✓ User can login faster with saved credentials

## Browser Developer Tools Verification

### Network Tab
1. Open DevTools (F12)
2. Go to Network tab
3. Login with a user
4. Look for POST request to `/api/security/login`
5. Verify response contains:
   - `access_token`: JWT token
   - `user_id`: User UUID
   - `username`: Username
   - `role`: User role
   - `tenant_id`: Tenant ID

### Console Tab
1. Open DevTools (F12)
2. Go to Console tab
3. Check for any errors or warnings
4. Verify no 401/403 errors after login

### Application Tab (Storage)
1. Open DevTools (F12)
2. Go to Application > Local Storage
3. Look for `auth-storage` entry
4. Verify it contains:
   - `token`: JWT token
   - `user`: User object
   - `currentTenant`: Tenant info
   - `isAuthenticated`: true

## API Endpoint Testing

### Login Endpoint
```bash
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin_user",
    "password": "Admin@123456"
  }'
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "admin_user",
  "role": "admin",
  "tenant_id": "default_tenant"
}
```

### Get Current User
```bash
curl -X GET http://localhost:8000/api/security/users/me \
  -H "Authorization: Bearer <access_token>"
```

### Logout Endpoint
```bash
curl -X POST http://localhost:8000/api/security/logout \
  -H "Authorization: Bearer <access_token>"
```

## Troubleshooting

### Issue: "Cannot POST /api/security/login"
**Solution**: 
- Verify backend API is running on http://localhost:8000
- Check that `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env.development`
- Restart backend: `python main.py`

### Issue: "Invalid username or password"
**Solution**:
- Verify test users were created: `python create_test_users_for_login.py`
- Check database connection: `python check_postgres.py`
- Verify credentials match exactly (case-sensitive)

### Issue: "CORS error" in browser console
**Solution**:
- Verify backend has CORS enabled
- Check `src/main.py` for CORS configuration
- Restart backend after CORS changes

### Issue: Token not stored in localStorage
**Solution**:
- Check browser privacy settings
- Verify localStorage is not disabled
- Check browser console for storage errors
- Try incognito/private mode

### Issue: User logged out after page refresh
**Solution**:
- Check that token is stored in localStorage
- Verify token is not expired
- Check that `useAuthStore` is properly initialized
- Clear localStorage and try again

### Issue: Cannot access admin features as admin user
**Solution**:
- Verify user role is "admin" in database
- Check that role-based access control is implemented
- Verify menu items have proper role checks
- Check browser console for permission errors

## Performance Testing

### Login Response Time
1. Open DevTools Network tab
2. Login with a user
3. Check response time for `/api/security/login`
4. Expected: < 500ms

### Token Validation
1. Login and get token
2. Make multiple API requests
3. Verify token is reused (not creating new tokens)
4. Check token expiration handling

## Security Testing

### Password Security
- ✓ Passwords are hashed (not stored in plain text)
- ✓ Passwords are not logged
- ✓ Passwords are not visible in network requests

### Token Security
- ✓ JWT tokens are stored securely
- ✓ Tokens are sent in Authorization header
- ✓ Tokens expire after configured time
- ✓ Refresh token mechanism works

### Session Security
- ✓ Sessions are isolated per user
- ✓ Cannot access other users' data
- ✓ Logout clears all session data
- ✓ CSRF protection is enabled

## Test Results Template

```
Login Testing Results - [Date]
================================

Test User: [username]
Role: [role]
Status: [PASS/FAIL]

Scenarios Tested:
- [ ] Login succeeds
- [ ] Redirected to dashboard
- [ ] User info displayed
- [ ] Role-based features visible
- [ ] Logout works
- [ ] Session persists

Issues Found:
- [List any issues]

Notes:
- [Additional observations]
```

## Next Steps

1. **Automated Testing**: Create Playwright E2E tests for login flows
2. **Performance Testing**: Load test login endpoint with multiple concurrent users
3. **Security Testing**: Penetration test login functionality
4. **Integration Testing**: Test login with other system components
5. **Documentation**: Create user guides for different roles

## References

- Frontend Auth Service: `frontend/src/services/auth.ts`
- Backend Security API: `src/api/security.py`
- Auth Store: `frontend/src/stores/authStore.ts`
- Auth Hook: `frontend/src/hooks/useAuth.ts`
- Security Models: `src/security/models.py`
