# SuperInsight Local Testing Guide

**Quick Start**: Both services are running and ready for testing!

---

## 🚀 Quick Access

### Frontend Application
- **URL**: http://localhost:3000
- **Status**: ✅ Running
- **Open in Browser**: [Click here](http://localhost:3000)

### Backend API
- **URL**: http://localhost:8000
- **Status**: ✅ Running
- **Health Check**: http://localhost:8000/health

---

## 👤 Test Accounts

Copy and paste these credentials to login:

### Account 1: System Administrator
```
Username: admin_test
Password: admin123
Role: ADMIN
Permissions: Full system access
```

### Account 2: Business Expert
```
Username: expert_test
Password: expert123
Role: BUSINESS_EXPERT
Permissions: Data analysis, quality review
```

### Account 3: Data Annotator
```
Username: annotator_test
Password: annotator123
Role: ANNOTATOR
Permissions: Data annotation, labeling
```

### Account 4: Report Viewer
```
Username: viewer_test
Password: viewer123
Role: VIEWER
Permissions: Report viewing (read-only)
```

---

## 🧪 Testing Workflow

### Step 1: Frontend Login
1. Open http://localhost:3000 in your browser
2. Select a test account from above
3. Enter username and password
4. Click "Login"

### Step 2: Test Each Module

#### Dashboard
- [ ] Dashboard loads successfully
- [ ] System metrics display correctly
- [ ] Language switching works (Chinese ↔ English)

#### Tasks Management
- [ ] View task list
- [ ] Create new task
- [ ] Update task status
- [ ] Delete task

#### Data Extraction
- [ ] Upload data file
- [ ] Start extraction process
- [ ] View extraction results
- [ ] Download extracted data

#### Quality Management
- [ ] View quality metrics
- [ ] Run quality evaluation
- [ ] View quality reports
- [ ] Export quality data

#### AI Annotation
- [ ] View AI models
- [ ] Run preannotation
- [ ] Review AI predictions
- [ ] Adjust predictions

#### Billing Management
- [ ] View usage statistics
- [ ] Check billing history
- [ ] View cost breakdown
- [ ] Download invoices

#### Security Settings
- [ ] Change password
- [ ] View login history
- [ ] Manage API keys
- [ ] Configure 2FA

#### Admin Panel (Admin Only)
- [ ] User management
- [ ] System configuration
- [ ] Audit logs
- [ ] System health

#### Settings
- [ ] Language switching (Chinese ↔ English)
- [ ] Theme settings
- [ ] Notification preferences
- [ ] Export settings

### Step 3: API Testing

#### Test Login API
```bash
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_test","password":"admin123"}'
```

#### Test Health Check
```bash
curl http://localhost:8000/health
```

#### Test Language Settings
```bash
curl http://localhost:8000/api/settings/language
```

#### Test Data Extraction
```bash
curl -X POST http://localhost:8000/api/v1/extraction/extract \
  -H "Content-Type: application/json" \
  -d '{"source_type":"csv"}'
```

#### Test Quality Evaluation
```bash
curl -X POST http://localhost:8000/api/v1/quality/evaluate \
  -H "Content-Type: application/json" \
  -d '{"data":"test"}'
```

#### Test AI Preannotation
```bash
curl -X POST http://localhost:8000/api/ai/preannotate \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'
```

#### Test Billing
```bash
curl http://localhost:8000/api/billing/usage
```

#### Test Knowledge Graph
```bash
curl http://localhost:8000/api/v1/knowledge-graph/entities
```

#### Test Tasks
```bash
curl http://localhost:8000/api/v1/tasks
```

---

## 🌐 Language Testing

### Switch Language in Frontend
1. Look for language selector (usually top-right corner)
2. Select "中文" for Chinese or "English" for English
3. Verify all UI text updates

### Switch Language via API
```bash
# Set to English
curl -X POST http://localhost:8000/api/settings/language \
  -H "Content-Type: application/json" \
  -d '{"language":"en"}'

# Set to Chinese
curl -X POST http://localhost:8000/api/settings/language \
  -H "Content-Type: application/json" \
  -d '{"language":"zh"}'
```

### Get Current Language
```bash
curl http://localhost:8000/api/settings/language
```

---

## 📊 Performance Testing

### Check System Health
```bash
curl http://localhost:8000/health | python3 -m json.tool
```

### Check System Status
```bash
curl http://localhost:8000/system/status | python3 -m json.tool
```

### Check System Metrics
```bash
curl http://localhost:8000/system/metrics | python3 -m json.tool
```

### Check System Services
```bash
curl http://localhost:8000/system/services | python3 -m json.tool
```

---

## 🔍 Troubleshooting

### Frontend Not Loading
```bash
# Check if frontend is running
curl http://localhost:3000

# Check frontend process
ps aux | grep npm

# Restart frontend
cd frontend
npm run dev
```

### Backend Not Responding
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check backend process
ps aux | grep uvicorn

# Restart backend
python3 simple_app.py
```

### Database Connection Issues
```bash
# Check PostgreSQL status
# Ensure Docker Desktop is running
# Verify database credentials in .env file
```

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Find process using port 3000
lsof -i :3000

# Kill process if needed
kill -9 <PID>
```

---

## 📝 Testing Checklist

### Functionality Tests
- [ ] User login with all roles
- [ ] Dashboard displays correctly
- [ ] Language switching works
- [ ] All API endpoints respond
- [ ] Data extraction works
- [ ] Quality evaluation works
- [ ] AI preannotation works
- [ ] Billing data displays
- [ ] Knowledge graph loads
- [ ] Tasks management works

### Permission Tests
- [ ] Admin can access all features
- [ ] Expert can access analysis features
- [ ] Annotator can access annotation features
- [ ] Viewer can only view reports

### i18n Tests
- [ ] Chinese translations display correctly
- [ ] English translations display correctly
- [ ] Language switching is instant
- [ ] All UI elements translate

### Performance Tests
- [ ] API response time < 200ms
- [ ] Frontend loads in < 5 seconds
- [ ] No console errors
- [ ] No network errors

### Error Handling Tests
- [ ] Invalid login shows error
- [ ] Invalid data shows error
- [ ] Network errors handled gracefully
- [ ] Error messages are translated

---

## 📞 Support

### Common Issues

**Q: Frontend shows blank page**
A: Check browser console for errors, ensure backend is running

**Q: Login fails**
A: Verify credentials, check backend logs, ensure database is connected

**Q: Language not switching**
A: Refresh page, check browser cache, verify i18n API is responding

**Q: API returns 500 error**
A: Check backend logs, verify database connection, restart backend

---

## 🎯 Next Steps

1. **Test Frontend**: Open http://localhost:3000 and login
2. **Test Each Module**: Go through each feature systematically
3. **Test API**: Use curl commands to verify endpoints
4. **Test Languages**: Switch between Chinese and English
5. **Test Permissions**: Try different user roles
6. **Document Results**: Record any issues or observations

---

## 📋 Test Results Template

```
Test Date: _______________
Tester: ___________________
Environment: macOS / Docker Desktop / PostgreSQL

Frontend Tests:
- Login: [ ] Pass [ ] Fail
- Dashboard: [ ] Pass [ ] Fail
- Tasks: [ ] Pass [ ] Fail
- Billing: [ ] Pass [ ] Fail
- Quality: [ ] Pass [ ] Fail
- Security: [ ] Pass [ ] Fail
- Settings: [ ] Pass [ ] Fail
- Admin: [ ] Pass [ ] Fail

API Tests:
- Health: [ ] Pass [ ] Fail
- Login: [ ] Pass [ ] Fail
- Users: [ ] Pass [ ] Fail
- Extraction: [ ] Pass [ ] Fail
- Quality: [ ] Pass [ ] Fail
- AI: [ ] Pass [ ] Fail
- Billing: [ ] Pass [ ] Fail
- Knowledge Graph: [ ] Pass [ ] Fail
- Tasks: [ ] Pass [ ] Fail

i18n Tests:
- Chinese: [ ] Pass [ ] Fail
- English: [ ] Pass [ ] Fail
- Switching: [ ] Pass [ ] Fail

Issues Found:
1. ___________________________
2. ___________________________
3. ___________________________

Overall Status: [ ] Pass [ ] Fail
```

---

**Happy Testing! 🎉**

For detailed information, see:
- `LOCAL_VERIFICATION_REPORT.md` - Comprehensive verification results
- `FULLSTACK_INTEGRATION_GUIDE.md` - Complete integration guide
- `FRONTEND_TESTING_GUIDE.md` - Detailed frontend testing procedures
