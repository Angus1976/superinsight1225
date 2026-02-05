# Label Studio JWT Authentication Migration Guide

**Version**: 1.0  
**Date**: 2026-01-27  
**Target**: SuperInsight Platform Administrators and DevOps Teams

## Overview

This guide provides step-by-step instructions for migrating from Label Studio API Token authentication to JWT-based authentication. JWT authentication is the recommended method for Label Studio 1.22.0+ and provides enhanced security with automatic token management.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Migration Benefits](#migration-benefits)
3. [Pre-Migration Checklist](#pre-migration-checklist)
4. [Migration Steps](#migration-steps)
5. [Verification](#verification)
6. [Rollback Procedure](#rollback-procedure)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Prerequisites

### System Requirements

- **Label Studio Version**: 1.22.0 or later
  - JWT authentication is not available in earlier versions
  - Check version: `docker compose exec label-studio label-studio --version`

- **SuperInsight Platform**: Latest version with JWT support
  - Verify JWT auth module exists: `ls src/label_studio/jwt_auth.py`

- **Access Requirements**:
  - Label Studio admin credentials (username and password)
  - Access to `.env` file
  - Permission to restart Docker containers

### Verify Label Studio Version

```bash
# Check Label Studio version
docker compose exec label-studio label-studio --version

# Expected output: 1.22.0 or higher
```

If your version is below 1.22.0, you must either:
- Upgrade Label Studio to 1.22.0+, OR
- Continue using API Token authentication

---

## Migration Benefits

### Why Migrate to JWT?

| Feature | API Token | JWT Authentication |
|---------|-----------|-------------------|
| **Token Expiration** | Never expires | Expires after 1 hour |
| **Token Refresh** | Manual | Automatic |
| **Security** | Static token | Rotating tokens |
| **Credential Management** | Token only | Username + Password |
| **Concurrent Requests** | No special handling | Thread-safe with locks |
| **Token Storage** | May be persisted | Memory only |
| **Recovery** | Manual token regeneration | Automatic re-authentication |

### Security Improvements

1. **Automatic Token Rotation**: Access tokens expire and refresh automatically
2. **Reduced Token Exposure**: Tokens are short-lived (1 hour vs. permanent)
3. **Memory-Only Storage**: Tokens never persisted to disk
4. **Secure Logging**: Tokens and passwords never appear in logs
5. **HTTPS Enforcement**: Warnings for non-HTTPS URLs in production

---

## Pre-Migration Checklist

Before starting the migration, complete this checklist:

- [ ] **Backup Current Configuration**
  ```bash
  cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
  ```

- [ ] **Verify Label Studio Version**
  ```bash
  docker compose exec label-studio label-studio --version
  # Must be 1.22.0 or higher
  ```

- [ ] **Test Label Studio Access**
  ```bash
  curl -X GET http://localhost:8080/api/projects/ \
    -H "Authorization: Token ${LABEL_STUDIO_API_TOKEN}"
  # Should return 200 OK
  ```

- [ ] **Obtain Admin Credentials**
  - Username (typically: `admin` or `admin@example.com`)
  - Password (set during Label Studio setup)

- [ ] **Schedule Maintenance Window**
  - Estimated downtime: 5-10 minutes
  - Notify users of the maintenance window

- [ ] **Review Current API Token Usage**
  ```bash
  grep -r "LABEL_STUDIO_API_TOKEN" .env
  ```

---

## Migration Steps

### Step 1: Verify Current Configuration

Check your current authentication setup:

```bash
# View current Label Studio configuration
grep "LABEL_STUDIO" .env

# Expected output:
# LABEL_STUDIO_URL=http://localhost:8080
# LABEL_STUDIO_API_TOKEN=your_current_token
```

### Step 2: Test JWT Authentication Credentials

Before modifying the configuration, verify your JWT credentials work:

```bash
# Test JWT login
curl -X POST http://localhost:8080/api/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin",
    "password": "your_password"
  }'

# Expected output:
# {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "token_type": "Bearer"
# }
```

If this fails with 401 Unauthorized:
- Verify username and password are correct
- Check Label Studio version is 1.22.0+
- Review Label Studio logs: `docker compose logs label-studio --tail=50`

### Step 3: Update Environment Configuration

Edit your `.env` file to add JWT credentials:

```bash
nano .env
```

Add the following lines (keep the existing API token for now):

```bash
# Label Studio Authentication
LABEL_STUDIO_URL=http://localhost:8080

# JWT Authentication (Label Studio 1.22.0+) - PREFERRED
LABEL_STUDIO_USERNAME=admin
LABEL_STUDIO_PASSWORD=your_secure_password

# API Token Authentication (Legacy) - BACKUP
LABEL_STUDIO_API_TOKEN=your_current_token
```

**Important Notes**:
- Keep both JWT credentials AND API token during migration
- JWT will be used automatically when both are present
- API token serves as a backup if JWT fails

### Step 4: Restart Application

Restart the SuperInsight application to apply the new configuration:

```bash
# Restart the application container
docker compose restart app

# Wait for the container to be healthy
docker compose ps app

# Check logs for authentication method
docker compose logs app --tail=50 | grep "authentication"

# Expected output:
# "Using jwt authentication for Label Studio"
```

### Step 5: Verify JWT Authentication

Test that JWT authentication is working:

```bash
# Test JWT authentication from within the container
docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
import asyncio

async def test():
    ls = LabelStudioIntegration()
    print(f'Authentication method: {ls._auth_method}')
    
    if ls._auth_method == 'jwt':
        print('Testing JWT authentication...')
        await ls._jwt_auth_manager.login()
        print(f'Authenticated: {ls._jwt_auth_manager.is_authenticated}')
        print(f'Has access token: {ls._jwt_auth_manager._access_token is not None}')
        print(f'Has refresh token: {ls._jwt_auth_manager._refresh_token is not None}')
    
    # Test API connection
    result = await ls.test_connection()
    print(f'Connection test: {\"SUCCESS\" if result else \"FAILED\"}')

asyncio.run(test())
"

# Expected output:
# Authentication method: jwt
# Testing JWT authentication...
# Authenticated: True
# Has access token: True
# Has refresh token: True
# Connection test: SUCCESS
```

### Step 6: Test Application Functionality

Verify that all Label Studio features work with JWT authentication:

1. **Test Project Creation**:
   ```bash
   # Access the SuperInsight UI
   # Navigate to annotation projects
   # Create a new project
   # Verify project appears in Label Studio
   ```

2. **Test Task Import**:
   ```bash
   # Import tasks into a project
   # Verify tasks appear in Label Studio
   ```

3. **Test Annotation Workflow**:
   ```bash
   # Click "Start Annotation" button
   # Verify Label Studio iframe loads
   # Complete an annotation
   # Verify annotation is saved
   ```

4. **Test Token Refresh** (optional):
   ```bash
   # Wait 1 hour for token to expire
   # OR manually expire token in database
   # Make an API call
   # Verify token is automatically refreshed
   ```

### Step 7: Monitor for Issues

Monitor the application for 24-48 hours after migration:

```bash
# Monitor application logs
docker compose logs -f app | grep -i "label.*studio\|jwt\|auth"

# Watch for errors
docker compose logs app --tail=100 | grep -i "error\|fail"

# Check authentication state periodically
docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
ls = LabelStudioIntegration()
if ls._jwt_auth_manager:
    print(ls._jwt_auth_manager.get_auth_state())
"
```

### Step 8: Remove API Token (Optional)

After confirming JWT authentication works for 1-2 weeks, you can optionally remove the API token:

```bash
# Edit .env file
nano .env

# Comment out or remove the API token line
# LABEL_STUDIO_API_TOKEN=your_current_token

# Restart application
docker compose restart app
```

**Recommendation**: Keep the API token as a backup for at least 2 weeks.

---

## Verification

### Verification Checklist

After migration, verify the following:

- [ ] **Authentication Method**
  ```bash
  docker compose logs app --tail=50 | grep "Using jwt authentication"
  ```

- [ ] **JWT Login Success**
  ```bash
  docker compose logs app --tail=50 | grep "JWT authentication successful"
  ```

- [ ] **No Authentication Errors**
  ```bash
  docker compose logs app --tail=50 | grep -i "authentication.*fail"
  # Should return no results
  ```

- [ ] **Token Refresh Works**
  ```bash
  docker compose logs app --tail=100 | grep "Token refresh successful"
  # May not appear immediately - wait for token to expire
  ```

- [ ] **API Calls Succeed**
  ```bash
  # Test from UI or API
  curl -X GET http://localhost:8000/api/label-studio/projects
  # Should return 200 OK
  ```

- [ ] **No Token Leaks in Logs**
  ```bash
  docker compose logs app --tail=1000 | grep -i "eyJ"
  # Should return no results (no JWT tokens in logs)
  ```

### Performance Verification

Monitor performance metrics:

```bash
# Check authentication latency
docker compose logs app | grep "JWT authentication successful" | tail -10

# Check token refresh latency
docker compose logs app | grep "Token refresh successful" | tail -10

# Verify < 5 seconds for auth, < 2 seconds for refresh
```

---

## Rollback Procedure

If you encounter issues with JWT authentication, you can quickly rollback to API Token authentication.

### When to Rollback

Consider rollback if:
- JWT authentication consistently fails
- Label Studio version is incompatible
- Performance issues occur
- Critical bugs are discovered

### Rollback Steps

#### Option 1: Quick Rollback (Keep JWT Config)

Simply remove JWT credentials from `.env`:

```bash
# Edit .env file
nano .env

# Comment out JWT credentials
# LABEL_STUDIO_USERNAME=admin
# LABEL_STUDIO_PASSWORD=your_password

# Keep API token active
LABEL_STUDIO_API_TOKEN=your_current_token

# Restart application
docker compose restart app

# Verify API token authentication
docker compose logs app --tail=50 | grep "Using api_token authentication"
```

#### Option 2: Full Rollback (Restore Backup)

Restore the backup configuration:

```bash
# List available backups
ls -la .env.backup.*

# Restore the backup
cp .env.backup.YYYYMMDD_HHMMSS .env

# Restart application
docker compose restart app

# Verify configuration
docker compose logs app --tail=50 | grep "authentication"
```

### Post-Rollback Verification

After rollback, verify:

```bash
# Check authentication method
docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
ls = LabelStudioIntegration()
print(f'Auth method: {ls._auth_method}')
"

# Expected output: Auth method: api_token

# Test API connection
docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
import asyncio

async def test():
    ls = LabelStudioIntegration()
    result = await ls.test_connection()
    print(f'Connection test: {\"SUCCESS\" if result else \"FAILED\"}')

asyncio.run(test())
"

# Expected output: Connection test: SUCCESS
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Authentication failed" Error

**Symptoms**:
```
[Label Studio] JWT authentication failed: Invalid credentials (status_code=401)
```

**Possible Causes**:
1. Incorrect username or password
2. Label Studio version < 1.22.0
3. Label Studio service not running

**Solutions**:

1. **Verify Credentials**:
   ```bash
   # Test credentials manually
   curl -X POST http://localhost:8080/api/sessions/ \
     -H "Content-Type: application/json" \
     -d '{"email":"admin","password":"your_password"}'
   ```

2. **Check Label Studio Version**:
   ```bash
   docker compose exec label-studio label-studio --version
   # Must be 1.22.0 or higher
   ```

3. **Check Label Studio Status**:
   ```bash
   docker compose ps label-studio
   docker compose logs label-studio --tail=50
   ```

4. **Reset Label Studio Password**:
   ```bash
   docker compose exec label-studio python manage.py changepassword admin
   ```

#### Issue 2: "Token expired" Errors

**Symptoms**:
```
[Label Studio] Token expired or expiring soon
```

**Expected Behavior**: This is normal! The system should automatically refresh the token.

**If Refresh Fails**:

1. **Check Refresh Token**:
   ```bash
   docker compose logs app | grep "Token refresh"
   ```

2. **Verify Re-authentication**:
   ```bash
   docker compose logs app | grep "falling back to login"
   ```

3. **Check Credentials**:
   ```bash
   docker compose exec app printenv | grep LABEL_STUDIO
   ```

#### Issue 3: Authentication Method Not Switching

**Symptoms**:
```
Auth method: api_token
# Expected: Auth method: jwt
```

**Solutions**:

1. **Verify Environment Variables**:
   ```bash
   docker compose exec app printenv | grep LABEL_STUDIO
   # Should show USERNAME and PASSWORD
   ```

2. **Restart Container**:
   ```bash
   docker compose restart app
   ```

3. **Rebuild Container** (if needed):
   ```bash
   docker compose up -d --build app
   ```

4. **Check Configuration**:
   ```bash
   docker compose exec app python3 -c "
   from src.label_studio.config import LabelStudioConfig
   config = LabelStudioConfig()
   print(f'Has username: {config.username is not None}')
   print(f'Has password: {config.password is not None}')
   print(f'Auth method: {config.get_auth_method()}')
   "
   ```

#### Issue 4: Concurrent Request Deadlocks

**Symptoms**:
- API requests hang or timeout
- Multiple requests waiting indefinitely

**Cause**: This should NOT happen with JWT auth (uses asyncio.Lock)

**Solutions**:

1. **Check for threading.Lock Usage**:
   ```bash
   grep -r "threading.Lock" src/label_studio/
   # Should return no results
   ```

2. **Verify asyncio.Lock**:
   ```bash
   grep -r "asyncio.Lock" src/label_studio/jwt_auth.py
   # Should find the lock implementation
   ```

3. **Restart Application**:
   ```bash
   docker compose restart app
   ```

#### Issue 5: HTTPS Security Warnings

**Symptoms**:
```
[Label Studio] SECURITY WARNING: Label Studio URL does not use HTTPS
```

**Solutions**:

1. **For Production**: Update to HTTPS URL
   ```bash
   # Edit .env
   LABEL_STUDIO_URL=https://label-studio.yourdomain.com
   ```

2. **For Development**: Ignore warning (safe for localhost)
   ```bash
   # Warning is expected for localhost/127.0.0.1
   # No action needed
   ```

#### Issue 6: Token Not Refreshing Automatically

**Symptoms**:
- Token expires and API calls fail
- No automatic refresh occurs

**Solutions**:

1. **Check Token Expiration Detection**:
   ```bash
   docker compose logs app | grep "Token expired"
   ```

2. **Verify Refresh Logic**:
   ```bash
   docker compose logs app | grep "Refreshing access token"
   ```

3. **Test Manual Refresh**:
   ```bash
   docker compose exec app python3 -c "
   from src.label_studio.integration import LabelStudioIntegration
   import asyncio
   
   async def test():
       ls = LabelStudioIntegration()
       if ls._jwt_auth_manager:
           await ls._jwt_auth_manager.login()
           print('Logged in')
           await ls._jwt_auth_manager.refresh_token()
           print('Token refreshed')
   
   asyncio.run(test())
   "
   ```

---

## FAQ

### General Questions

**Q: Do I need to migrate to JWT authentication?**

A: No, API Token authentication is still supported for backward compatibility. However, JWT is recommended for:
- Label Studio 1.22.0+
- Enhanced security requirements
- Automatic token management

**Q: Can I use both JWT and API Token simultaneously?**

A: Yes! If both are configured, JWT will be used automatically. The API Token serves as a backup.

**Q: What happens if JWT authentication fails?**

A: The system will:
1. Attempt to refresh the token
2. If refresh fails, re-authenticate with username/password
3. If re-authentication fails, raise an error
4. If API Token is configured, you can manually rollback

**Q: How long does migration take?**

A: Typically 5-10 minutes including:
- Configuration update: 2 minutes
- Container restart: 1-2 minutes
- Verification: 2-5 minutes

### Technical Questions

**Q: How often do JWT tokens expire?**

A: 
- Access Token: 1 hour (automatically refreshed)
- Refresh Token: 7 days (automatically renewed)

**Q: Are tokens stored in the database?**

A: No. Tokens are stored in memory only for security. They are cleared when:
- Application restarts
- Authentication fails
- Tokens are refreshed

**Q: What happens during token refresh?**

A: 
1. System detects token will expire soon (60 seconds buffer)
2. Acquires lock to prevent concurrent refreshes
3. Calls `/api/sessions/refresh/` endpoint
4. Updates access and refresh tokens
5. Releases lock
6. All waiting requests use the new token

**Q: Is JWT authentication thread-safe?**

A: Yes. The implementation uses `asyncio.Lock()` to ensure:
- Only one refresh operation at a time
- Concurrent requests wait for refresh to complete
- No race conditions or deadlocks

**Q: Can I customize token expiration times?**

A: Token expiration is controlled by Label Studio server configuration, not the client. The default is:
- Access Token: 1 hour
- Refresh Token: 7 days

**Q: What if Label Studio is upgraded/downgraded?**

A: 
- **Upgrade to 1.22.0+**: JWT authentication becomes available
- **Downgrade below 1.22.0**: JWT authentication stops working, falls back to API Token
- **Recommendation**: Keep API Token configured during version changes

### Security Questions

**Q: Are passwords stored securely?**

A: 
- Passwords are read from environment variables only
- Never logged or persisted to disk
- Only used for authentication requests
- Transmitted over HTTPS (recommended)

**Q: Are tokens logged?**

A: No. The implementation ensures:
- Tokens never appear in logs
- Passwords never appear in logs
- Only authentication status is logged

**Q: What if tokens are compromised?**

A: 
- Access tokens expire after 1 hour
- Refresh tokens expire after 7 days
- Change password to invalidate all tokens
- Restart application to clear memory

**Q: Should I use HTTPS?**

A: 
- **Production**: Yes, always use HTTPS
- **Development**: HTTP is acceptable for localhost
- **Warning**: System logs warning if HTTP is used in production

---

## Additional Resources

### Documentation

- [Label Studio JWT Authentication Requirements](../.kiro/specs/label-studio-jwt-authentication/requirements.md)
- [Label Studio JWT Authentication Design](../.kiro/specs/label-studio-jwt-authentication/design.md)
- [Label Studio Setup Guide](../LABEL_STUDIO_SETUP.md)
- [Environment Configuration](.env.example)

### Label Studio Documentation

- [Label Studio Official Documentation](https://labelstud.io/guide/)
- [Label Studio API Documentation](https://labelstud.io/api)
- [Label Studio Authentication](https://labelstud.io/guide/auth.html)

### Support

If you encounter issues not covered in this guide:

1. **Check Logs**:
   ```bash
   docker compose logs app --tail=100 | grep -i "label.*studio\|jwt\|auth"
   ```

2. **Review Requirements**: See `requirements.md` for detailed specifications

3. **Check Design Document**: See `design.md` for architecture details

4. **Contact Support**: Provide:
   - Error messages from logs
   - Steps to reproduce
   - Label Studio version
   - SuperInsight version

---

## Changelog

### Version 1.0 (2026-01-27)
- Initial migration guide
- Covers migration from API Token to JWT
- Includes rollback procedures
- Comprehensive troubleshooting section

---

**Document Status**: ✅ Complete  
**Last Updated**: 2026-01-27  
**Maintained By**: SuperInsight Platform Team
