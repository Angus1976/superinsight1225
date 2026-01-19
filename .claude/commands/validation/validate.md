Run comprehensive validation of the SuperInsight AI platform.

Execute the following commands in sequence and report results:

## 1. Backend Linting and Formatting

```bash
# Check formatting
black --check src/ tests/

# Check import sorting
isort --check src/ tests/

# Type checking
mypy src/
```

**Expected:** No formatting issues, all type checks pass

## 2. Backend Tests

```bash
pytest tests/ -v
```

**Expected:** All tests pass

## 3. Backend Tests with Coverage

```bash
pytest tests/ --cov=src --cov-report=term-missing
```

**Expected:** Coverage >= 80%

## 4. Frontend Type Checking

```bash
cd frontend && npx tsc --noEmit
```

**Expected:** No TypeScript errors (0 errors)

## 5. Frontend Tests

```bash
cd frontend && npm run test
```

**Expected:** All Vitest tests pass

## 6. Frontend Linting

```bash
cd frontend && npm run lint
```

**Expected:** No linting errors

## 7. Frontend Build

```bash
cd frontend && npm run build
```

**Expected:** Build completes successfully, outputs to `dist/` directory

## 8. Local Server Validation (Optional)

If backend is not already running, start it:

```bash
uvicorn src.app:app --port 8000 &
```

Wait 2 seconds for startup, then test:

```bash
# Test health endpoint
curl -s http://localhost:8000/health

# Test system status
curl -s http://localhost:8000/system/status

# Check API docs
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/docs
```

**Expected:** JSON response from endpoints, HTTP 200 from docs

Stop the server if started:

```bash
# Linux/Mac
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Or use pkill
pkill -f "uvicorn src.app:app"
```

## 9. Summary Report

After all validations complete, provide a summary report with:

### Backend Validation
- ✅/❌ Formatting (black, isort)
- ✅/❌ Type checking (mypy)
- ✅/❌ Tests passed/failed
- ✅/❌ Coverage percentage (target: >= 80%)

### Frontend Validation
- ✅/❌ TypeScript compilation (0 errors)
- ✅/❌ Tests passed/failed
- ✅/❌ Linting status
- ✅/❌ Build status

### Overall Status
- 🟢 PASS - All validations successful
- 🟡 PARTIAL - Some warnings but no failures
- 🔴 FAIL - Critical issues found

**Format the report clearly with sections and status indicators**

## Notes

- Run this command before committing code
- Fix all issues before proceeding
- Refer to .kiro/steering/typescript-export-rules.md for TypeScript guidelines
- Refer to .kiro/steering/async-sync-safety.md for async/await patterns
