# SuperInsight Testing Documentation

This document provides comprehensive guidance for the SuperInsight testing infrastructure, covering setup, execution, data management, and reporting.

## 1. Test Infrastructure Setup

### 1.1 Local Development Test Setup

**Prerequisites:**
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (optional, for integration tests)
- Redis 7+ (optional, for cache tests)

**Backend Setup:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: .\venv\Scripts\activate  # Windows

# Install test dependencies
pip install -r requirements.txt

# Verify installation
pytest --version
hypothesis --version
```

**Frontend Setup:**
```bash
cd frontend
npm install
npm install -D vitest @testing-library/react @testing-library/jest-dom @playwright/test
npx playwright install chromium
```

**Environment Configuration:**
```bash
# Copy test environment file
cp .env.test .env

# Key settings in .env.test:
# - DATABASE_URL=sqlite:///:memory:  (unit tests)
# - REDIS_URL=redis://localhost:6380/15  (isolated Redis)
# - APP_ENV=test
```

### 1.2 CI Environment Configuration

**GitHub Actions Workflows (backend / Hypothesis):**
- `.github/workflows/commit-tests.yml` — Push to `main` / `develop` (unit + property tests; Hypothesis profile 见下)
- `.github/workflows/pr-tests.yml` — Pull requests to `main` / `develop`（复用 `commit-tests`，并对集成测试设置 profile）
- `.github/workflows/main-branch-tests.yml` — Push to `main`（复用 `pr-tests` 并传入更严的 Hypothesis 配置）

**HYPOTHESIS_PROFILE in CI（与 workflow 一致）：**
- **Pull request**：子工作流 `commit-tests` 使用 **`dev`**（约 25 例）；`pr-tests` 内集成测试步骤同样设为 **`dev`**。
- **Push 到 `main`**：`commit-tests` 单独由 push 触发时，在 `main` 分支上使用 **`ci`**；**手动 `workflow_dispatch` 且当前 ref 为 `main`** 时同样使用 **`ci`**（其余分支手动运行为 **`default`**）。`main-branch-tests` 调用 `pr-tests` 时传入 **`ci`**，集成测试与复用的 commit 测试均走更严采样。
- **其他分支 push**：`commit-tests` 默认 **`default`**（若未显式传入 `hypothesis_profile`）。

**CI Environment Variables:**
```yaml
env:
  APP_ENV: test
  DATABASE_URL: postgresql://user:pass@localhost:5433/superinsight_test
  REDIS_URL: redis://localhost:6380/15
  # HYPOTHESIS_PROFILE 由各 workflow 步骤注入，勿在全局写死为单一值
  COVERAGE_THRESHOLD: 80
```

**CI Test Execution:**
```bash
# Run with CI profile (500 Hypothesis examples)
HYPOTHESIS_PROFILE=ci pytest

# Run all tests with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov-fail-under=80
```

**Hypothesis profiles (property / `@given` tests):**

| Profile | `max_examples` | When to use |
|---------|------------------|-------------|
| `default` | 100 | Full local/PR rigor (default if `HYPOTHESIS_PROFILE` unset) |
| `ci` | 500 | Scheduled / merge validation (`HYPOTHESIS_PROFILE=ci`) |
| `dev` | 25 | Balance speed vs coverage (e.g. `HYPOTHESIS_PROFILE=dev pytest`) |
| `fast` | 10 | Fast iteration while editing property tests |

Quick local regression (unit + API, no coverage, `fast` Hypothesis profile):

```bash
./scripts/run-tests-fast.sh
# or explicitly:
HYPOTHESIS_PROFILE=fast pytest tests/unit tests/api --no-cov -q
```

Property-heavy directories (`tests/property/`, many `*_properties.py`) scale roughly with `max_examples × number of @given tests`; use `fast`/`dev` during development and reserve `default`/`ci` for pre-merge or nightly runs.

### 1.3 Test Database Setup

**Database Configuration:**
```python
# In .env.test
DATABASE_URL=sqlite:///:memory:  # Unit tests (fast)
# For integration tests:
TEST_POSTGRES_HOST=localhost
TEST_POSTGRES_PORT=5433
TEST_POSTGRES_USER=superinsight_test
TEST_POSTGRES_PASSWORD=test_password
TEST_POSTGRES_DB=superinsight_test
```

**Database Fixtures:**
```python
# tests/conftest.py provides:
@pytest.fixture(scope="function")
def db_session(test_engine):
    """SQLite in-memory session with automatic rollback."""
    with isolated_test_session(test_engine) as session:
        yield session

@pytest.fixture(scope="function")
def postgres_session(postgres_test_engine):
    """PostgreSQL session with transaction rollback."""
    with isolated_test_session(postgres_test_engine) as session:
        yield session
```

**Database Isolation Features:**
- Transaction-based rollback ensures test isolation
- Separate test database prevents production data contamination
- Automatic cleanup after each test
- Production database access is blocked

### 1.4 Test Redis Setup

**Redis Configuration:**
```python
# In .env.test
REDIS_URL=redis://localhost:6380/15  # Separate port and database
REDIS_MAX_CONNECTIONS=10
```

**Redis Fixtures:**
```python
@pytest.fixture(scope="function")
def redis(redis_client):
    """Redis client with automatic key cleanup."""
    yield redis_client
    # Cleanup: delete all test keys
    prefix = TestRedisConfig.get_key_prefix()
    keys = redis_client.keys(f"{prefix}*")
    if keys:
        redis_client.delete(*keys)
```

**Redis Isolation Strategy:**
- Separate Redis instance on port 6380
- Isolated database (db=15)
- Key prefix for easy identification
- Automatic cleanup after each test

### 1.5 Playwright E2E Setup

**Installation:**
```bash
cd frontend
npm install -D @playwright/test
npx playwright install chromium
npx playwright install-deps
```

**Configuration (playwright.config.ts):**
```typescript
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',  // Requirement 4.5
    headless: true,  // Requirement 4.6
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
})
```

**E2E Test Fixtures:**
```typescript
// frontend/e2e/fixtures.ts
export const test = base.extend({
  page: async ({ browser }, use) => {
    const context = await browser.newContext()
    const page = await context.newPage()
    await use(page)
    await context.close()
  },
})
```

## 2. Test Execution Procedures

### 2.1 Running Unit Tests

**Backend Unit Tests:**
```bash
# Run all unit tests
pytest -m unit

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test function
pytest tests/unit/test_models.py::test_user_creation

# Run with verbose output
pytest -m unit -v

# Run with coverage
pytest -m unit --cov=src --cov-report=html
```

**Frontend Unit Tests:**
```bash
cd frontend
npm run test          # Run all tests
npm run test:unit     # Run unit tests only
npm run test:watch    # Watch mode for development
npm run test:coverage # With coverage report
```

**Test Categories (pytest markers):**
```python
@pytest.mark.unit      # Fast, isolated tests
@pytest.mark.integration  # Database/Redis tests
@pytest.mark.property     # Hypothesis property tests
@pytest.mark.slow         # Long-running tests
```

### 2.2 Running Integration Tests

**Prerequisites:**
- PostgreSQL running on port 5433
- Redis running on port 6380

**Execution:**
```bash
# Run integration tests
pytest -m integration

# Run with PostgreSQL (full features)
pytest -m integration --postgres

# Run specific integration test suite
pytest tests/integration/test_api_endpoints.py

# Run with verbose output
pytest -m integration -v
```

**Integration Test Example:**
```python
@pytest.mark.integration
def test_user_workflow(postgres_session, redis):
    """Test complete user workflow with real database."""
    # Create user
    user = User(username="test", email="test@example.com")
    postgres_session.add(user)
    postgres_session.commit()
    
    # Verify in Redis cache
    cached = redis.get(f"user:{user.id}")
    assert cached is not None
```

### 2.3 Running E2E Tests

**Prerequisites:**
- Backend server running
- Frontend server running

**Execution:**
```bash
cd frontend

# Run all E2E tests
npm run test:e2e

# Run specific E2E test file
npx playwright test e2e/auth.spec.ts

# Run with UI (debug mode)
npx playwright test --ui

# Run with headed browser
npx playwright test --headed

# Run specific test
npx playwright test e2e/auth.spec.ts -g "login"
```

**E2E Test Categories:**
```typescript
// frontend/e2e/auth.spec.ts
test.describe('Registration workflow', () => {
  test('successful registration', async ({ page }) => {
    // Test implementation
  })
})

test.describe('Login workflow', () => {
  test('valid login', async ({ page }) => {
    // Test implementation
  })
})
```

### 2.4 Running Performance Tests

**Prerequisites:**
- Backend server running
- Locust installed: `pip install locust`

**Execution:**
```bash
# Run load test with 100 concurrent users
locust -f tests/performance/locustfile.py --users 100 --spawn-rate 10

# Headless mode
locust -f tests/performance/locustfile.py --users 100 --spawn-rate 10 --headless

# Run specific test class
locust -f tests/performance/locustfile.py --users 100 --class-name UserBehavior
```

**Performance Test Configuration:**
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def view_dashboard(self):
        self.client.get("/api/dashboard")
    
    @task(1)
    def create_task(self):
        self.client.post("/api/tasks", json={"title": "Test"})
```

**Performance Thresholds (Requirement 5.6):**
- p95 response time < 500ms for critical endpoints
- Test fails if threshold exceeded

### 2.5 Running Security Scans

**SQL Injection Tests:**
```bash
# Run SQL injection scan
pytest tests/security/test_sql_injection.py -v
```

**XSS Tests:**
```bash
# Run XSS vulnerability scan
pytest tests/security/test_xss.py -v
```

**Dependency Vulnerability Scan:**
```bash
# Python dependencies
safety check -r requirements.txt

# JavaScript dependencies
cd frontend
npm audit
```

**OWASP ZAP Scan:**
```bash
# Run full security scan
python tests/security/zap_scan.py --target http://localhost:8000

# Generate report
python tests/security/zap_scan.py --target http://localhost:8000 --report html
```

## 3. Test Data Management

### 3.1 Test Data Factory Usage

**Available Factories (tests/strategies.py):**
```python
from tests.strategies import users, tasks, annotations, datasets

# Generate user data
user = {
    "id": "uuid-string",
    "username": "valid_username",
    "email": "user@example.com",
    "role": "admin",  # or annotator, reviewer, viewer
    "is_active": True,
}

# Generate task data
task = {
    "id": "uuid-string",
    "title": "Task title",
    "status": "pending",  # or in_progress, completed, rejected
    "priority": 1-5,
}

# Generate annotation data
annotation = {
    "id": "uuid-string",
    "annotation_type": "text",  # or entity, relation, classification
    "data": {"key": "value"},
    "confidence": 0.0-1.0,
}
```

**Using with Hypothesis:**
```python
from hypothesis import given
from tests.strategies import users, tasks

@given(user=users())
def test_user_property(user):
    assert user.email is not None
    assert user.role in ["admin", "annotator", "reviewer", "viewer"]

@given(task=tasks(status="pending"))
def test_pending_task(task):
    assert task["status"] == "pending"
```

### 3.2 Test Data Cleanup Procedures

**Automatic Cleanup:**
```python
# Database - transaction rollback (automatic)
@pytest.fixture(scope="function")
def db_session(test_engine):
    with isolated_test_session(test_engine) as session:
        yield session  # Rollback happens automatically

# Redis - key cleanup (automatic)
@pytest.fixture(scope="function")
def redis(redis_client):
    yield redis_client
    # Cleanup happens automatically via fixture
```

**Manual Cleanup Registration:**
```python
def test_with_manual_cleanup(db_session, cleanup_test_data):
    user = User(username="test")
    db_session.add(user)
    db_session.commit()
    
    # Register for cleanup
    cleanup_test_data.register_for_cleanup(User, user.id)
    
    # Test code here
    # User deleted automatically after test
```

**Cleanup Manager API:**
```python
class DatabaseCleanupManager:
    def register_for_cleanup(self, model, id): ...
    def cleanup_registered_items(self): ...
    def cleanup_all_by_model(self, model): ...
```

### 3.3 Creating Custom Test Data

**Custom Factory:**
```python
from tests.strategies import st
from hypothesis import given

@given(
    name=st.text(min_size=1, max_size=50),
    status=st.sampled_from(["active", "inactive", "pending"]),
    priority=st.integers(min_value=1, max_value=10)
)
def test_custom_data(name, status, priority):
    data = {
        "name": name,
        "status": status,
        "priority": priority,
    }
    assert len(data["name"]) <= 50
    assert data["status"] in ["active", "inactive", "pending"]
```

**Invalid State Generation:**
```python
from tests.strategies import invalid_emails, invalid_uuids

@given(email=invalid_emails())
def test_invalid_email_rejection(email):
    # Email should be rejected by validation
    assert validate_email(email) is False
```

### 3.4 Test Environment Isolation

**Isolation Levels:**
1. **Unit Tests**: In-memory SQLite, no external dependencies
2. **Integration Tests**: PostgreSQL on port 5433, transaction rollback
3. **E2E Tests**: Mocked API responses, isolated browser context
4. **Performance Tests**: Dedicated test environment

**Isolation Verification:**
```python
# Verify no production database access
from tests.database_isolation import prevent_production_database_access
prevent_production_database_access()

# Verify Redis isolation
from tests.redis_isolation import prevent_production_redis_access
prevent_production_redis_access()
```

## 4. Test Reporting

### 4.1 Generating Test Reports

**HTML Report:**
```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html
```

**JSON Report:**
```bash
pytest --cov=src --cov-report=json -o json_report_file=true
```

**Allure Report:**
```bash
pytest --alluredir=allure-results
allure serve allure-results
```

**Combined Report:**
```bash
pytest --cov=src --cov-report=html --cov-report=json --html=report.html
```

### 4.2 Interpreting Coverage Reports

**Coverage Metrics:**
- **Statement Coverage**: % of code statements executed
- **Branch Coverage**: % of conditional branches taken
- **Function Coverage**: % of functions called
- **Line Coverage**: % of lines executed

**Coverage Thresholds (Requirement 7.6):**
- Overall: ≥ 80%
- Core logic: ≥ 90%
- API endpoints: ≥ 85%
- Data models: ≥ 80%

**Reading Coverage Report:**
```
Name                    Stmts   Miss  Cover   Missing
------------------------------------------------------
src/models/user.py         50      2    96%   123, 145
src/api/auth.py           100     15   85%   45-50, 78-82
------------------------------------------------------
TOTAL                    1000    150   85%
```

**Coverage by Module:**
```bash
pytest --cov=src --cov-report=term-missing --cov-report=term
```

### 4.3 Interpreting Performance Reports

**Performance Metrics:**
- **Response Time**: p50, p95, p99 percentiles
- **Throughput**: Requests per second
- **Error Rate**: % of failed requests
- **Database Queries**: Query execution time

**Performance Report Example:**
```
Performance Report
==================
Endpoint: /api/tasks
- Requests: 1000
- p50: 45ms
- p95: 120ms  (FAIL if > 500ms)
- p99: 250ms
- Throughput: 150 req/s
- Error Rate: 0.1%
```

**Baseline Comparison (Requirement 13.5):**
```python
# Performance degradation > 20% fails test
assert current_p95 <= baseline_p95 * 1.2
```

### 4.4 Interpreting Security Reports

**Vulnerability Severity (Requirement 6.6):**
- **Critical**: Immediate action required
- **High**: Fix within 1 week
- **Medium**: Fix within 1 month
- **Low**: Address in next release

**Security Report Example:**
```
Security Scan Results
=====================
SQL Injection: 0 found
XSS: 2 found (Medium)
Authentication Bypass: 0 found
Sensitive Data Exposure: 1 found (High)
Dependency Vulnerabilities: 5 found (2 High, 3 Medium)

Total: 8 vulnerabilities
```

**Vulnerability Details:**
```python
@dataclass
class Vulnerability:
    id: str
    title: str
    severity: str  # critical, high, medium, low
    category: str  # sql_injection, xss, auth_bypass, etc.
    remediation: str
    cve_id: Optional[str]
```

## Quick Reference

### Common Commands

```bash
# All tests
pytest

# By category
pytest -m unit
pytest -m integration
pytest -m property
pytest -m e2e

# With coverage
pytest --cov=src --cov-report=html

# Performance
locust -f tests/performance/locustfile.py --users 100 --headless

# Security
safety check -r requirements.txt
npm audit

# Frontend
cd frontend && npm run test
cd frontend && npm run test:e2e
```

### Test Configuration Files

| File | Purpose |
|------|---------|
| `pytest.ini` | pytest configuration |
| `conftest.py` | Shared fixtures |
| `.env.test` | Test environment variables |
| `playwright.config.ts` | E2E test configuration |
| `vitest.config.ts` | Frontend test configuration |

### Coverage Requirements

| Component | Minimum |
|-----------|---------|
| Overall | 80% |
| Core logic | 90% |
| API endpoints | 85% |
| Data models | 80% |

### Performance Thresholds

| Metric | Threshold |
|--------|-----------|
| Critical endpoint p95 | < 500ms |
| Performance degradation | < 20% |
| Unit test execution | < 5 min |
| Deployment test execution | < 2 min |

### Support

- **pytest**: https://docs.pytest.org/
- **Hypothesis**: https://hypothesis.readthedocs.io/
- **Playwright**: https://playwright.dev/
- **Locust**: https://locust.io/
- **Coverage.py**: https://coverage.readthedocs.io/