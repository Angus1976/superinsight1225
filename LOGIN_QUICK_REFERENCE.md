# Login Testing Quick Reference

## Quick Start (5 minutes)

```bash
# 1. Start Docker services
docker-compose -f docker-compose.local.yml up -d

# 2. Create test users
python create_test_users_for_login.py

# 3. Start backend (Terminal 1)
python main.py

# 4. Start frontend (Terminal 2)
cd frontend && npm run dev

# 5. Open browser
# http://localhost:5173/login
```

## Test User Credentials

| Role | Username | Password | Email |
|------|----------|----------|-------|
| Admin | `admin_user` | `Admin@123456` | admin@superinsight.local |
| Business Expert | `business_expert` | `Business@123456` | business@superinsight.local |
| Technical Expert | `technical_expert` | `Technical@123456` | technical@superinsight.local |
| Contractor | `contractor` | `Contractor@123456` | contractor@superinsight.local |
| Viewer | `viewer` | `Viewer@123456` | viewer@superinsight.local |

## Service URLs

| Service | URL | Port |
|---------|-----|------|
| Frontend | http://localhost:5173 | 5173 |
| Backend API | http://localhost:8000 | 8000 |
| PostgreSQL | localhost:5432 | 5432 |
| Redis | localhost:6379 | 6379 |
| Neo4j | http://localhost:7474 | 7474 |
| Label Studio | http://localhost:8080 | 8080 |

## API Endpoints

### Login
```bash
POST /api/security/login
Content-Type: application/json

{
  "username": "admin_user",
  "password": "Admin@123456"
}
```

### Get Current User
```bash
GET /api/security/users/me
Authorization: Bearer <token>
```

### Logout
```bash
POST /api/security/logout
Authorization: Bearer <token>
```

## Testing Checklist

### Basic Login
- [ ] Admin login succeeds
- [ ] Business expert login succeeds
- [ ] Technical expert login succeeds
- [ ] Contractor login succeeds
- [ ] Viewer login succeeds

### Error Handling
- [ ] Invalid username shows error
- [ ] Invalid password shows error
- [ ] Empty fields show error
- [ ] User stays on login page after error

### Session Management
- [ ] Token stored in localStorage
- [ ] User info displayed in header
- [ ] Session persists on page refresh
- [ ] Logout clears session

### Role-Based Access
- [ ] Admin sees all menu items
- [ ] Business expert sees business features
- [ ] Technical expert sees technical features
- [ ] Contractor sees limited features
- [ ] Viewer sees read-only features

### Security
- [ ] Password not visible in network requests
- [ ] Token not exposed in console
- [ ] CORS headers correct
- [ ] No sensitive data in logs

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Cannot POST /api/security/login" | Backend not running. Run `python main.py` |
| "Invalid username or password" | Check credentials. Run `python create_test_users_for_login.py` |
| CORS error | Restart backend. Check CORS config in `src/main.py` |
| Token not stored | Check localStorage in DevTools. Try incognito mode |
| User logged out after refresh | Check token expiration. Clear localStorage and retry |
| Cannot access admin features | Verify user role in database. Check role-based access control |

## Browser DevTools Checks

### Network Tab
1. Look for POST `/api/security/login`
2. Response should contain `access_token`, `user_id`, `role`
3. Response time should be < 500ms

### Console Tab
- No 401/403 errors after login
- No CORS errors
- No undefined variables

### Application Tab (Storage)
- `auth-storage` in localStorage
- Contains: `token`, `user`, `currentTenant`, `isAuthenticated`

## Running Tests

```bash
# Run all login tests
pytest test_login_comprehensive.py -v

# Run specific test class
pytest test_login_comprehensive.py::TestLoginBasic -v

# Run with coverage
pytest test_login_comprehensive.py --cov=src.security --cov-report=html

# Run with detailed output
pytest test_login_comprehensive.py -vv --tb=long
```

## File Locations

| File | Purpose |
|------|---------|
| `create_test_users_for_login.py` | Create test users in database |
| `test_login_comprehensive.py` | Comprehensive login test suite |
| `LOGIN_TESTING_GUIDE.md` | Detailed testing guide |
| `start_login_testing.sh` | Automated setup script |
| `frontend/src/pages/Login/index.tsx` | Login page component |
| `frontend/src/components/Auth/LoginForm.tsx` | Login form component |
| `frontend/src/services/auth.ts` | Auth service |
| `src/api/security.py` | Backend security API |

## Key Files to Monitor

### Frontend
- `frontend/src/stores/authStore.ts` - Auth state management
- `frontend/src/hooks/useAuth.ts` - Auth hook
- `frontend/src/services/api/client.ts` - API client with interceptors

### Backend
- `src/security/controller.py` - Security logic
- `src/security/middleware.py` - Auth middleware
- `src/security/models.py` - Database models

## Performance Targets

| Metric | Target |
|--------|--------|
| Login response time | < 500ms |
| Token generation | < 100ms |
| User info retrieval | < 200ms |
| Logout | < 100ms |

## Security Checklist

- [ ] Passwords hashed (not plain text)
- [ ] JWT tokens used for auth
- [ ] Tokens expire after configured time
- [ ] Refresh token mechanism works
- [ ] HTTPS enforced in production
- [ ] CORS properly configured
- [ ] Rate limiting on login endpoint
- [ ] Failed login attempts logged
- [ ] Session isolation per user

## Next Steps

1. **Manual Testing**: Follow LOGIN_TESTING_GUIDE.md
2. **Automated Testing**: Run `pytest test_login_comprehensive.py -v`
3. **E2E Testing**: Create Playwright tests
4. **Load Testing**: Test with multiple concurrent users
5. **Security Testing**: Penetration test login flow

## Support

- **Documentation**: See LOGIN_TESTING_GUIDE.md
- **Issues**: Check browser console and network tab
- **Logs**: Check `backend.log` for server errors
- **Database**: Use `check_postgres.py` to verify connection

## Useful Commands

```bash
# Check Docker services
docker-compose -f docker-compose.local.yml ps

# View backend logs
tail -f backend.log

# Check database connection
python check_postgres.py

# Create test users
python create_test_users_for_login.py

# Run login tests
pytest test_login_comprehensive.py -v

# Start frontend dev server
cd frontend && npm run dev

# Start backend API
python main.py

# Stop all services
docker-compose -f docker-compose.local.yml down
```

## Environment Variables

### Frontend (.env.development)
```
VITE_APP_TITLE=SuperInsight
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_ENV=development
```

### Backend (.env)
```
DATABASE_URL=postgresql://user:password@localhost:5432/superinsight
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

## Troubleshooting Commands

```bash
# Verify backend is running
curl http://localhost:8000/health

# Test login endpoint
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}'

# Check database
python check_postgres.py

# View Docker logs
docker-compose -f docker-compose.local.yml logs -f postgres

# Restart services
docker-compose -f docker-compose.local.yml restart
```

---

**Last Updated**: 2026-01-09
**Version**: 1.0
