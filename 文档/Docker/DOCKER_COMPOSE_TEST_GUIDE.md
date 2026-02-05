# Docker Compose JWT and Label Studio Authentication Test Guide

This guide explains how to run comprehensive tests for JWT authentication and Label Studio integration using Docker Compose.

## Overview

The test suite includes:

1. **Service Health Checks** - Verify API and Label Studio are running
2. **JWT Authentication Tests** - Test token generation, validation, and access control
3. **Label Studio API Token Authentication** - Test API Token authentication
4. **Project Management Tests** - Test task creation and sync status
5. **Label Studio Project Creation** - Test automatic project creation
6. **Language Parameter Tests** - Test language parameter handling
7. **Error Handling Tests** - Test error scenarios and recovery
8. **Integration Tests** - Test complete workflows

## Prerequisites

- Docker and Docker Compose installed
- SuperInsight platform running with `docker-compose up`
- Label Studio container running
- Backend API accessible at `http://localhost:8000`
- Label Studio accessible at `http://localhost:8080`

## Test Scripts

### 1. Bash Test Script

**File**: `docker-compose-test-auth.sh`

**Features**:
- Pure bash implementation
- No external dependencies
- Detailed output with colors
- HTTP status code validation
- JSON response parsing

**Usage**:

```bash
# Make script executable
chmod +x docker-compose-test-auth.sh

# Run inside Docker container
docker-compose exec app bash docker-compose-test-auth.sh

# Or with docker compose (newer syntax)
docker compose exec app bash docker-compose-test-auth.sh

# Run from host (requires curl)
./docker-compose-test-auth.sh
```

**Output Example**:
```
========================================
Section 1: Service Health Checks
========================================

[TEST 1] SuperInsight API health check
   ✅ PASS: Service ready: http://localhost:8000/health

[TEST 2] Label Studio health check
   ✅ PASS: Service ready: http://localhost:8080/health

========================================
Section 2: JWT Authentication Tests
========================================

[TEST 3] Login with valid credentials
   ✅ PASS: Login successful (HTTP 200)
   ℹ️  INFO: JWT Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. Python Test Script

**File**: `docker-compose-test-auth.py`

**Features**:
- Async HTTP client for better performance
- Comprehensive error handling
- Detailed test results
- JSON parsing and validation
- Structured test output

**Usage**:

```bash
# Make script executable
chmod +x docker-compose-test-auth.py

# Run inside Docker container
docker-compose exec app python docker-compose-test-auth.py

# Or with docker compose (newer syntax)
docker compose exec app python docker-compose-test-auth.py

# Run from host (requires Python 3.8+)
python3 docker-compose-test-auth.py
```

**Output Example**:
```
╔════════════════════════════════════════════════════════════════╗
║  Docker Compose JWT and Label Studio Authentication Test Suite ║
╚════════════════════════════════════════════════════════════════╝

========================================
Section 1: Service Health Checks
========================================

[TEST] SuperInsight API health check... ✅ PASS
  → API is ready

[TEST] Label Studio health check... ✅ PASS
  → Label Studio is ready
```

## Running Tests

### Option 1: Run Inside Docker Container (Recommended)

This is the most reliable way to run tests as it uses the internal Docker network.

```bash
# Using docker-compose (older syntax)
docker-compose exec app bash docker-compose-test-auth.sh

# Using docker compose (newer syntax)
docker compose exec app bash docker-compose-test-auth.sh

# Or with Python
docker-compose exec app python docker-compose-test-auth.py
```

### Option 2: Run from Host

Make sure services are accessible from your host machine.

```bash
# Bash script
./docker-compose-test-auth.sh

# Python script
python3 docker-compose-test-auth.py
```

### Option 3: Run with Custom Configuration

Set environment variables to customize test behavior:

```bash
# Custom API URL
API_BASE_URL=http://192.168.1.100:8000 docker-compose-test-auth.sh

# Custom Label Studio URL
LABEL_STUDIO_URL=http://192.168.1.100:8080 docker-compose-test-auth.sh

# Custom test credentials
TEST_USERNAME=testuser TEST_PASSWORD=testpass docker-compose-test-auth.sh
```

## Test Sections Explained

### Section 1: Service Health Checks

Verifies that both SuperInsight API and Label Studio are running and accessible.

**Tests**:
- SuperInsight API health endpoint
- Label Studio health endpoint

**Expected Results**:
- Both services should respond with HTTP 200
- Services should be ready within 30 seconds

### Section 2: JWT Authentication Tests

Tests JWT token generation, validation, and access control.

**Tests**:
1. Login with valid credentials
2. Validate JWT token format (3 parts separated by dots)
3. Access protected endpoint with valid JWT
4. Reject invalid JWT token
5. Reject missing JWT token

**Expected Results**:
- Login returns HTTP 200 with access_token
- JWT token has valid format
- Protected endpoints accessible with valid JWT
- Invalid/missing tokens return HTTP 401 or 403

### Section 3: Label Studio API Token Authentication

Tests Label Studio API Token authentication.

**Tests**:
1. Test Label Studio API connection
2. List Label Studio projects
3. Reject invalid API Token

**Expected Results**:
- API Token authentication successful
- Can list projects
- Invalid tokens rejected with HTTP 401 or 403

### Section 4: Project Management Tests

Tests task creation and Label Studio sync status.

**Tests**:
1. Create test task
2. Verify task has Label Studio sync status field

**Expected Results**:
- Task created successfully
- Task has `label_studio_sync_status` field
- Sync status is one of: pending, synced, failed

### Section 5: Label Studio Project Creation Tests

Tests automatic project creation and synchronization.

**Tests**:
1. Test Label Studio connection via API
2. Ensure project exists for task
3. Verify project exists in Label Studio

**Expected Results**:
- Connection test successful
- Project created automatically
- Project accessible in Label Studio

### Section 6: Language Parameter Tests

Tests language parameter handling in authenticated URLs.

**Tests**:
1. Get authenticated URL with Chinese language
2. Get authenticated URL with English language

**Expected Results**:
- URLs include language parameter (lang=zh or lang=en)
- URLs are properly formatted with token

### Section 7: Error Handling Tests

Tests error scenarios and recovery mechanisms.

**Tests**:
1. Handle missing project (404)
2. Handle invalid task ID (404)
3. Handle unauthorized access (401/403)

**Expected Results**:
- Missing resources return HTTP 404
- Unauthorized access returns HTTP 401 or 403
- Error messages are clear and helpful

## Interpreting Results

### Successful Test Run

```
========================================
Test Summary
========================================

Total Tests:  35
Passed:       35
Failed:       0

✅ All tests passed!
```

### Failed Test Run

```
========================================
Test Summary
========================================

Total Tests:  35
Passed:       33
Failed:       2

❌ Some tests failed!
```

When tests fail, check:
1. Service logs: `docker-compose logs app` or `docker-compose logs label-studio`
2. Network connectivity: `docker-compose exec app ping label-studio`
3. Environment variables: `docker-compose exec app env | grep LABEL_STUDIO`
4. Database status: Check if database is running and accessible

## Troubleshooting

### Services Not Responding

**Problem**: Tests fail with "Service not responding"

**Solution**:
```bash
# Check if services are running
docker-compose ps

# Check service logs
docker-compose logs app
docker-compose logs label-studio

# Restart services
docker-compose restart app label-studio
```

### JWT Token Issues

**Problem**: Login fails or JWT token is invalid

**Solution**:
```bash
# Check authentication configuration
docker-compose exec app cat /app/.env | grep AUTH

# Verify database has admin user
docker-compose exec app python -c "from src.database import SessionLocal; from src.models import UserModel; db = SessionLocal(); print(db.query(UserModel).first())"

# Reset admin password if needed
docker-compose exec app python reset_admin_password.py
```

### Label Studio Connection Issues

**Problem**: Label Studio tests fail

**Solution**:
```bash
# Check Label Studio is running
docker-compose ps label-studio

# Check Label Studio logs
docker-compose logs label-studio

# Verify API Token is configured
docker-compose exec app grep LABEL_STUDIO_API_TOKEN /app/.env

# Test Label Studio directly
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8080/api/current-user/whoami/
```

### Network Issues

**Problem**: Tests fail with connection errors

**Solution**:
```bash
# Check network connectivity from app container
docker-compose exec app ping label-studio

# Check DNS resolution
docker-compose exec app nslookup label-studio

# Check firewall rules
docker-compose exec app netstat -tlnp | grep 8080
```

## Advanced Usage

### Running Specific Test Sections

To run only specific test sections, modify the test script:

```bash
# Bash - comment out unwanted sections
# Edit docker-compose-test-auth.sh and comment out test functions

# Python - modify main() function
# Edit docker-compose-test-auth.py and remove test calls
```

### Continuous Testing

Run tests periodically to monitor system health:

```bash
# Run tests every 5 minutes
watch -n 300 'docker-compose exec app bash docker-compose-test-auth.sh'

# Or with cron
*/5 * * * * cd /path/to/project && docker-compose exec app bash docker-compose-test-auth.sh >> test-results.log
```

### Integration with CI/CD

Add tests to your CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Run Docker Compose Tests
  run: |
    docker-compose up -d
    docker-compose exec -T app bash docker-compose-test-auth.sh
    docker-compose down
```

### Performance Testing

Measure test execution time:

```bash
# Bash
time docker-compose exec app bash docker-compose-test-auth.sh

# Python
time docker-compose exec app python docker-compose-test-auth.py
```

## Test Data

Tests create temporary data:
- Test tasks with names like "Test Task for Auth"
- Test projects in Label Studio
- Test annotations

This data is not automatically cleaned up. To clean up:

```bash
# Delete test tasks
docker-compose exec app python -c "
from src.database import SessionLocal
from src.models import TaskModel
db = SessionLocal()
db.query(TaskModel).filter(TaskModel.name.like('%Test Task%')).delete()
db.commit()
"

# Delete test projects from Label Studio
# Use Label Studio UI or API
```

## Performance Benchmarks

Expected test execution times:

| Test Section | Time | Notes |
|---|---|---|
| Service Health Checks | 1-5s | Depends on service startup |
| JWT Authentication | 2-3s | 5 tests |
| Label Studio Auth | 2-3s | 3 tests |
| Project Management | 3-5s | Task creation + DB queries |
| Project Creation | 5-10s | Label Studio API calls |
| Language Parameters | 2-3s | 2 tests |
| Error Handling | 2-3s | 3 tests |
| **Total** | **20-35s** | Typical run time |

## Security Considerations

### Test Credentials

Tests use default admin credentials. For production:

1. Change default credentials
2. Create test user with limited permissions
3. Use environment variables for credentials
4. Never commit credentials to version control

### API Token Security

- API Token is read from `.env` file
- Never commit `.env` to version control
- Rotate tokens regularly
- Use different tokens for different environments

### Test Data

- Test data is created in production database
- Clean up test data after testing
- Use separate test database if possible
- Implement data retention policies

## Support

For issues or questions:

1. Check test output for specific error messages
2. Review service logs: `docker-compose logs`
3. Verify configuration: `docker-compose config`
4. Check network connectivity: `docker-compose exec app ping label-studio`
5. Review documentation: See design.md for architecture details

## References

- [JWT Authentication](https://jwt.io/)
- [Label Studio API Documentation](https://labelstud.io/api/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
