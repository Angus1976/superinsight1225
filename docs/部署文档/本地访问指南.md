# 🎉 SuperInsight 平台 - 本地访问指南

## ✅ 服务已启动

**状态**: ✅ 应用正在运行
**地址**: http://localhost:8000
**API 文档**: http://localhost:8000/docs

---

## 🔐 登录凭证

### 系统管理员
```
用户名: admin_test
密码: admin123
角色: ADMIN
权限: 完全访问所有功能
```

### 业务专家
```
用户名: expert_test
密码: expert123
角色: BUSINESS_EXPERT
权限: 数据处理、质量评估、工单管理
```

### 数据标注员
```
用户名: annotator_test
密码: annotator123
角色: ANNOTATOR
权限: 数据标注、任务查看
```

### 报表查看者
```
用户名: viewer_test
密码: viewer123
角色: VIEWER
权限: 只读访问、报表查看
```

---

## 🌐 访问方式

### 方式 1: 使用 API 文档（推荐）

1. 打开浏览器访问: **http://localhost:8000/docs**
2. 点击 "Authorize" 按钮
3. 输入用户名和密码登录
4. 在 Swagger UI 中直接测试所有 API

### 方式 2: 使用 cURL 命令

#### 登录获取 Token

```bash
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin_test",
    "password": "admin123"
  }'
```

**响应示例:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "admin_test",
    "email": "admin@test.com",
    "full_name": "系统管理员",
    "role": "ADMIN"
  }
}
```

#### 使用 Token 调用 API

```bash
# 保存 Token
TOKEN="your_access_token_here"

# 查看系统状态
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/system/status

# 查看所有服务
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/system/services

# 查看系统指标
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/system/metrics
```

### 方式 3: 使用 Python 脚本

```python
import requests
import json

# API 基础 URL
BASE_URL = "http://localhost:8000"

# 登录
login_response = requests.post(
    f"{BASE_URL}/api/security/login",
    json={
        "username": "admin_test",
        "password": "admin123"
    }
)

data = login_response.json()
token = data["access_token"]

# 使用 Token 调用 API
headers = {"Authorization": f"Bearer {token}"}

# 获取系统状态
response = requests.get(
    f"{BASE_URL}/system/status",
    headers=headers
)

print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

---

## 📋 主要 API 端点

### 系统管理
- `GET /health` - 健康检查
- `GET /system/status` - 系统状态
- `GET /system/services` - 所有服务状态
- `GET /system/metrics` - 系统指标
- `GET /api/info` - API 信息

### 安全和用户
- `POST /api/security/login` - 用户登录
- `POST /api/security/users` - 创建用户
- `GET /api/security/users` - 获取用户列表

### 数据处理
- `POST /api/v1/extraction/extract` - 提取数据
- `POST /api/v1/quality/evaluate` - 评估质量
- `POST /api/ai/preannotate` - AI 预标注

### 任务和计费
- `GET /api/v1/tasks` - 获取任务列表
- `GET /api/billing/usage` - 获取使用统计

### 知识图谱
- `GET /api/v1/knowledge-graph/entities` - 获取实体列表

---

## 🧪 测试场景

### 场景 1: 管理员操作

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_test","password":"admin123"}' | jq -r '.access_token')

# 2. 查看系统状态
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/system/status | jq

# 3. 查看所有服务
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/system/services | jq

# 4. 创建新用户
curl -X POST http://localhost:8000/api/security/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "full_name": "New User",
    "role": "VIEWER"
  }' | jq
```

### 场景 2: 业务专家操作

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"expert_test","password":"expert123"}' | jq -r '.access_token')

# 2. 提取数据
curl -X POST http://localhost:8000/api/v1/extraction/extract \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "database",
    "query": "SELECT * FROM users LIMIT 100"
  }' | jq

# 3. 评估质量
curl -X POST http://localhost:8000/api/v1/quality/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"text": "测试数据1", "label": "正常"},
      {"text": "测试数据2", "label": "正常"}
    ],
    "metrics": ["completeness", "accuracy"]
  }' | jq
```

### 场景 3: 标注员操作

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"annotator_test","password":"annotator123"}' | jq -r '.access_token')

# 2. 查看任务
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/tasks | jq

# 3. AI 预标注
curl -X POST http://localhost:8000/api/ai/preannotate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["这是一条需要标注的文本"],
    "model": "bert-base-chinese",
    "task_type": "classification"
  }' | jq
```

### 场景 4: 查看者操作

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"viewer_test","password":"viewer123"}' | jq -r '.access_token')

# 2. 查看计费信息
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/billing/usage | jq

# 3. 查看知识图谱实体
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/knowledge-graph/entities | jq
```

---

## 📊 快速测试

### 1. 检查应用是否运行

```bash
curl http://localhost:8000/
```

### 2. 检查健康状态

```bash
curl http://localhost:8000/health
```

### 3. 查看 API 信息

```bash
curl http://localhost:8000/api/info
```

### 4. 查看系统状态

```bash
curl http://localhost:8000/system/status
```

### 5. 查看所有用户

```bash
curl http://localhost:8000/api/security/users
```

---

## 🛠️ 常用命令

### 查看应用日志

```bash
# 查看应用进程
ps aux | grep simple_app

# 查看应用输出
tail -f /tmp/superinsight.log
```

### 停止应用

```bash
# 停止应用
pkill -f "python3 simple_app"

# 或者使用 kill 命令
kill -9 <process_id>
```

### 重启应用

```bash
# 停止应用
pkill -f "python3 simple_app"

# 等待 2 秒
sleep 2

# 重新启动
nohup python3 simple_app.py > /tmp/superinsight.log 2>&1 &
```

---

## 📚 API 文档

### 完整 API 文档
访问: **http://localhost:8000/docs**

在 Swagger UI 中，你可以：
- 查看所有可用的 API 端点
- 查看请求和响应的数据结构
- 直接在浏览器中测试 API
- 查看详细的参数说明

### 快速参考

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 根端点 |
| `/health` | GET | 健康检查 |
| `/system/status` | GET | 系统状态 |
| `/system/services` | GET | 服务列表 |
| `/system/metrics` | GET | 系统指标 |
| `/api/info` | GET | API 信息 |
| `/api/security/login` | POST | 用户登录 |
| `/api/security/users` | POST | 创建用户 |
| `/api/security/users` | GET | 获取用户列表 |
| `/api/v1/extraction/extract` | POST | 提取数据 |
| `/api/v1/quality/evaluate` | POST | 评估质量 |
| `/api/ai/preannotate` | POST | AI 预标注 |
| `/api/v1/tasks` | GET | 获取任务 |
| `/api/billing/usage` | GET | 获取计费 |
| `/api/v1/knowledge-graph/entities` | GET | 获取实体 |

---

## 🔍 故障排除

### 问题 1: 无法连接到 API

```bash
# 检查应用是否运行
ps aux | grep simple_app

# 检查端口是否被占用
lsof -i :8000

# 查看应用日志
tail -50 /tmp/superinsight.log
```

### 问题 2: 登录失败

```bash
# 确保使用正确的凭证
# 用户名: admin_test
# 密码: admin123

# 测试登录
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_test","password":"admin123"}'
```

### 问题 3: API 返回错误

```bash
# 检查请求格式
# 确保使用正确的 HTTP 方法（GET/POST）
# 确保 Content-Type 是 application/json
# 确保 JSON 格式正确

# 查看详细错误信息
curl -v http://localhost:8000/api/info
```

---

## 📞 需要帮助？

1. 查看 API 文档: http://localhost:8000/docs
2. 查看系统状态: http://localhost:8000/system/status
3. 查看健康检查: http://localhost:8000/health
4. 查看应用日志: `tail -f /tmp/superinsight.log`

---

## 🎯 下一步

1. ✅ 使用 API 文档测试各个端点
2. ✅ 用不同的用户角色登录
3. ✅ 测试各个功能模块
4. ✅ 查看系统监控和指标
5. ✅ 开始使用平台

---

**祝你使用愉快！** 🚀

---

**应用状态**: ✅ 正在运行
**地址**: http://localhost:8000
**API 文档**: http://localhost:8000/docs
**最后更新**: 2025-01-04
