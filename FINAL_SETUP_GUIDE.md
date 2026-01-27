# 🚀 Label Studio 集成最终设置指南

## 📋 问题解决状态

### ✅ 问题 1: 平台与 Label Studio 认证
**状态**: 已解决  
**方案**: 使用 API Token 认证（Community Edition 支持）  
**配置**: `.env` 文件已更新

### ✅ 问题 2: 任务与 Label Studio 同步
**状态**: 已实现  
**功能**: 
- 自动同步：创建任务时后台自动创建 Label Studio 项目
- 手动同步：提供重试端点
- 状态跟踪：记录同步状态和错误

## 🔧 立即开始测试

### 步骤 1: 快速连接测试

```bash
# 运行快速测试脚本
./quick_test_label_studio.sh
```

**这个脚本会测试**:
- ✅ Label Studio 服务是否运行
- ✅ API Token 认证是否正常
- ✅ 项目列表 API 是否可访问
- ✅ .env 配置是否正确

**预期输出**:
```
==========================================
Label Studio 连接测试
==========================================

1️⃣  测试 Label Studio 服务...
   ✅ Label Studio 服务正常运行

2️⃣  测试 API Token 认证...
   ✅ API Token 认证成功
   用户信息: {...}

3️⃣  测试项目列表 API...
   ✅ 项目列表 API 正常
   当前项目数: X

4️⃣  检查 .env 配置...
   ✅ .env 文件存在
   ✅ LABEL_STUDIO_API_TOKEN 已配置
   ✅ LABEL_STUDIO_URL = http://label-studio:8080
```

### 步骤 2: 重启后端容器

```bash
# 应用代码更改
docker compose restart app

# 查看启动日志
docker logs -f superinsight-api
```

**等待看到**:
```
INFO: Application startup complete.
INFO: Using api_token authentication for Label Studio
```

### 步骤 3: 完整功能测试

```bash
# 运行完整测试脚本
python test_label_studio_sync.py
```

**测试流程**:
1. 登录获取 JWT token
2. 测试 Label Studio 连接
3. 创建测试任务
4. 验证自动同步
5. 如果失败，尝试手动同步

**预期输出**:
```
============================================================
Label Studio Synchronization Test
============================================================

🔐 Logging in...
✅ Login successful

📡 Testing Label Studio connection...
✅ Direct Label Studio API connection successful
✅ SuperInsight → Label Studio connection successful

📝 Creating test task...
✅ Task created: <task-id>
   Sync status: pending

🔍 Checking sync status...
   Waiting 3 seconds for background sync...
✅ Task successfully synced to Label Studio
   Project URL: http://label-studio:8080/projects/<project-id>

============================================================
✅ Test completed
============================================================
```

## 🌐 浏览器测试

### 1. 测试任务创建

1. 打开浏览器访问: http://localhost:5173
2. 登录系统
3. 进入"任务管理"页面
4. 点击"创建新任务"
5. 填写表单并提交

**预期结果**:
- ✅ 任务创建成功
- ✅ 任务列表显示新任务
- ✅ 同步状态显示为 "pending" 或 "synced"

### 2. 测试标注按钮

1. 在任务列表中找到已同步的任务
2. 点击"开始标注"按钮

**预期结果**:
- ✅ 打开 Label Studio 标注界面
- ✅ 显示正确的项目
- ✅ 语言设置正确（中文）

### 3. 测试新窗口打开

1. 点击"在新窗口中打开"按钮

**预期结果**:
- ✅ 在新标签页打开 Label Studio
- ✅ 自动认证成功
- ✅ 显示正确的项目

## 🔍 API 测试

### 测试连接

```bash
# 1. 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. 测试 Label Studio 连接
curl -s http://localhost:8000/api/tasks/label-studio/test-connection \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

### 创建任务并同步

```bash
# 创建任务
TASK_ID=$(curl -s -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API 测试任务",
    "description": "通过 API 创建的测试任务",
    "priority": "medium",
    "annotation_type": "text_classification",
    "total_items": 5,
    "tags": ["api-test"]
  }' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "任务 ID: $TASK_ID"

# 等待 3 秒
sleep 3

# 检查同步状态
curl -s http://localhost:8000/api/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"同步状态: {d['label_studio_sync_status']}\"); print(f\"项目 ID: {d.get('label_studio_project_id', 'None')}\")"
```

### 手动同步

```bash
# 如果自动同步失败，手动触发
curl -s -X POST http://localhost:8000/api/tasks/$TASK_ID/sync-label-studio \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

## 🐛 故障排查

### 问题 1: Label Studio 服务无法访问

**检查**:
```bash
# 检查容器状态
docker ps | grep label-studio

# 检查容器日志
docker logs label-studio
```

**解决**:
```bash
# 重启 Label Studio
docker compose restart label-studio

# 或重启所有服务
docker compose restart
```

### 问题 2: API Token 认证失败

**症状**: 
```
❌ API Token 认证失败 (HTTP 401)
```

**解决步骤**:

1. 访问 Label Studio UI: http://localhost:8080
2. 登录（默认: admin@example.com / admin）
3. 进入 Account & Settings
4. 找到 "Legacy Tokens" 部分
5. 点击 "Create Token" 生成新 Token
6. 复制 Token
7. 更新 `.env` 文件:
   ```bash
   LABEL_STUDIO_API_TOKEN=<新的Token>
   ```
8. 重启后端:
   ```bash
   docker compose restart app
   ```

### 问题 3: 同步一直是 pending

**检查**:
```bash
# 查看后端日志
docker logs superinsight-api | grep -i "sync\|label"
```

**可能原因**:
- 后台任务未执行
- Label Studio 连接失败
- 认证问题

**解决**:
```bash
# 使用手动同步
curl -X POST http://localhost:8000/api/tasks/$TASK_ID/sync-label-studio \
  -H "Authorization: Bearer $TOKEN"
```

### 问题 4: 前端按钮无响应

**检查**:
1. 打开浏览器开发者工具 (F12)
2. 查看 Console 标签页的错误
3. 查看 Network 标签页的请求

**常见错误**:
- `401 Unauthorized` → Token 过期，重新登录
- `404 Not Found` → API 路由问题
- `500 Internal Server Error` → 查看后端日志

## 📊 验证清单

### 后端验证
- [ ] Label Studio 服务运行正常
- [ ] API Token 认证成功
- [ ] 连接测试端点返回成功
- [ ] 创建任务返回 200
- [ ] 任务自动同步到 Label Studio
- [ ] 手动同步端点工作正常
- [ ] 后端日志无错误

### 前端验证
- [ ] 可以登录系统
- [ ] 可以创建任务
- [ ] 任务列表显示正常
- [ ] 同步状态显示正确
- [ ] "开始标注"按钮工作
- [ ] "在新窗口打开"按钮工作
- [ ] Label Studio 界面正常显示

### 集成验证
- [ ] 任务创建后自动在 Label Studio 创建项目
- [ ] 项目 ID 正确存储
- [ ] 可以在 Label Studio 中看到项目
- [ ] 标注界面语言正确
- [ ] 标注数据可以保存

## 📝 下一步工作

### 短期 (本周)
1. [ ] 完成前端同步状态显示
2. [ ] 添加手动同步按钮
3. [ ] 完善错误提示
4. [ ] 添加同步进度指示

### 中期 (本月)
1. [ ] 实现数据库持久化
2. [ ] 添加同步历史记录
3. [ ] 实现批量同步
4. [ ] 添加同步监控

### 长期 (下月)
1. [ ] 实现双向同步
2. [ ] 添加冲突解决
3. [ ] 实现增量同步
4. [ ] 性能优化

## 🎯 成功标准

**认证成功**:
- ✅ 可以连接 Label Studio API
- ✅ API Token 认证通过
- ✅ 可以获取用户信息
- ✅ 可以列出项目

**同步成功**:
- ✅ 创建任务时自动同步
- ✅ 同步状态正确更新
- ✅ 项目 ID 正确存储
- ✅ 可以手动重试失败的同步

**用户体验**:
- ✅ 标注按钮正常工作
- ✅ 新窗口打开正常
- ✅ 语言设置正确
- ✅ 错误提示清晰

## 📞 获取帮助

如果遇到问题:

1. **查看日志**:
   ```bash
   # 后端日志
   docker logs superinsight-api
   
   # Label Studio 日志
   docker logs label-studio
   ```

2. **运行诊断**:
   ```bash
   ./quick_test_label_studio.sh
   ```

3. **查看文档**:
   - [实现报告](./LABEL_STUDIO_SYNC_IMPLEMENTATION.md)
   - [认证方案](./LABEL_STUDIO_AUTH_SOLUTION.md)
   - [API 修复](./TASK_API_FIX_SUMMARY.md)

---

**创建时间**: 2026-01-27  
**版本**: 1.0  
**状态**: ✅ 准备测试
