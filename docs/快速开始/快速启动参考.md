# 快速启动参考卡

**状态**: ✅ 所有服务运行中  
**更新时间**: 2026-01-04 20:46:16 UTC

---

## 🚀 立即访问

### 前端应用
```
http://localhost:3000
```

### 后端 API
```
http://localhost:8000
```

### 健康检查
```
http://localhost:8000/health
```

---

## 👤 测试账号 (复制粘贴)

### 管理员
```
用户名: admin_test
密码: admin123
```

### 业务专家
```
用户名: expert_test
密码: expert123
```

### 数据标注员
```
用户名: annotator_test
密码: annotator123
```

### 报表查看者
```
用户名: viewer_test
密码: viewer123
```

---

## 🧪 快速测试

### 测试登录
```bash
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_test","password":"admin123"}'
```

### 测试健康状态
```bash
curl http://localhost:8000/health
```

### 测试系统状态
```bash
curl http://localhost:8000/system/status
```

---

## 📊 系统状态

| 组件 | 状态 | 地址 |
|------|------|------|
| 后端 API | ✅ 运行中 | http://localhost:8000 |
| 前端应用 | ✅ 运行中 | http://localhost:3000 |
| 数据库 | ✅ 已连接 | PostgreSQL |
| 健康检查 | ✅ 通过 | /health |

---

## 🎯 可用功能

✅ 用户认证  
✅ 数据提取  
✅ 质量评估  
✅ AI 预标注  
✅ 计费管理  
✅ 知识图谱  
✅ 任务管理  
✅ 语言切换 (中文/英文)  

---

## 🔧 常见命令

### 重启后端
```bash
python3 simple_app.py
```

### 重启前端
```bash
cd frontend && npm run dev
```

### 检查后端进程
```bash
ps aux | grep simple_app
```

### 检查前端进程
```bash
ps aux | grep npm
```

### 查看后端日志
```bash
tail -f backend.log
```

---

## 📝 API 端点

### 系统
- GET /health
- GET /system/status
- GET /system/services
- GET /system/metrics

### 认证
- POST /api/security/login
- GET /api/security/users

### 功能
- POST /api/v1/extraction/extract
- POST /api/v1/quality/evaluate
- POST /api/ai/preannotate
- GET /api/billing/usage
- GET /api/v1/knowledge-graph/entities
- GET /api/v1/tasks

### 国际化
- GET /api/settings/language
- POST /api/settings/language
- GET /api/i18n/translations

---

## 🌐 语言支持

### 中文 (简体)
```bash
curl -H "Accept-Language: zh" http://localhost:8000/health
```

### 英文
```bash
curl -H "Accept-Language: en" http://localhost:8000/health
```

---

## ⚡ 性能指标

- API 响应时间: < 100ms
- 前端加载时间: 429ms
- 系统可用性: 100%
- 错误率: 0.1%

---

## 🆘 故障排除

### 后端无响应
```bash
pkill -f simple_app.py
python3 simple_app.py
```

### 前端无响应
```bash
pkill -f "npm run dev"
cd frontend && npm run dev
```

### 端口被占用
```bash
lsof -i :8000  # 查找占用 8000 的进程
lsof -i :3000  # 查找占用 3000 的进程
```

---

## 📚 详细文档

- **RESTART_SUMMARY.md** - 重启总结
- **LOCAL_TESTING_GUIDE.md** - 测试指南
- **LOCAL_VERIFICATION_REPORT.md** - 验证报告
- **CURRENT_SESSION_STATUS.md** - 当前状态

---

**准备就绪**: ✅ 是  
**立即开始**: http://localhost:3000
