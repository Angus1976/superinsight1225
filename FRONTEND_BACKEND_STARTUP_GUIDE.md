# 前后端服务启动与集成验证指南

**日期**: 2026-01-09  
**状态**: 🔧 需要手动启动服务

---

## 📋 当前系统状态

### ✅ 已就绪
- Docker 服务: **运行正常** ✓
  - PostgreSQL (5432) - 健康
  - Redis (6379) - 健康
  - Neo4j (7474, 7687) - 健康
  - Label Studio (8080) - 健康
- 前端 API 配置: **正确** ✓
  - `VITE_API_BASE_URL=http://localhost:8000`
- 测试用户: **已创建** ✓

### ⏳ 需要启动
- 后端 API 服务 (8000)
- 前端开发服务器 (5173)

---

## 🚀 快速启动步骤

### 步骤 1: 创建测试用户（如果还未创建）

```bash
python3 create_test_users_for_login.py
```

**预期输出**:
```
Creating test users for login testing...
────────────────────────────────────────────────────────────
✓ Created: admin_user (admin)
✓ Created: business_expert (business_expert)
✓ Created: technical_expert (technical_expert)
✓ Created: contractor (contractor)
✓ Created: viewer (viewer)
────────────────────────────────────────────────────────────
Summary: 5 created, 0 skipped
```

### 步骤 2: 启动后端 API（终端 1）

```bash
python3 main.py
```

**预期输出**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**验证后端**:
```bash
curl http://localhost:8000/health
```

### 步骤 3: 启动前端开发服务器（终端 2）

```bash
cd frontend
npm run dev
```

**预期输出**:
```
  VITE v7.2.4  ready in 234 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

**验证前端**:
在浏览器中访问 http://localhost:5173

---

## 🔐 登录凭证

| 角色 | 用户名 | 密码 | 权限 |
|------|--------|------|------|
| 管理员 | `admin_user` | `Admin@123456` | 完全访问 |
| 业务专家 | `business_expert` | `Business@123456` | 业务模块 |
| 技术专家 | `technical_expert` | `Technical@123456` | 技术模块 |
| 承包商 | `contractor` | `Contractor@123456` | 受限访问 |
| 查看者 | `viewer` | `Viewer@123456` | 只读访问 |

---

## 🔗 服务 URL

| 服务 | URL | 状态 |
|------|-----|------|
| 前端登录 | http://localhost:5173/login | ⏳ 需启动 |
| 后端 API | http://localhost:8000 | ⏳ 需启动 |
| 后端健康检查 | http://localhost:8000/health | ⏳ 需启动 |
| PostgreSQL | localhost:5432 | ✅ 运行中 |
| Redis | localhost:6379 | ✅ 运行中 |
| Neo4j | http://localhost:7474 | ✅ 运行中 |
| Label Studio | http://localhost:8080 | ✅ 运行中 |

---

## 🧪 集成验证清单

### 后端 API 验证

#### 1. 健康检查
```bash
curl http://localhost:8000/health
```
**预期**: 返回 200 OK

#### 2. 登录测试
```bash
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}'
```
**预期**: 返回包含 `access_token` 的 JSON

#### 3. 获取当前用户
```bash
curl -X GET http://localhost:8000/api/security/users/me \
  -H "Authorization: Bearer <access_token>"
```
**预期**: 返回用户信息

### 前端验证

#### 1. 页面加载
- 访问 http://localhost:5173/login
- **预期**: 登录页面正常显示

#### 2. 登录表单
- 输入用户名: `admin_user`
- 输入密码: `Admin@123456`
- 点击登录
- **预期**: 成功登录，重定向到仪表板

#### 3. 浏览器开发者工具验证
- 打开 DevTools (F12)
- 检查 Network 标签
  - POST `/api/security/login` 返回 200
  - 响应包含 `access_token`
- 检查 Application 标签
  - LocalStorage 中有 `auth-storage`
  - 包含 token、user、currentTenant

---

## 🔍 故障排查

### 问题 1: 后端无法启动

**症状**: `python3 main.py` 报错

**解决方案**:
```bash
# 检查依赖
pip3 install -r requirements.txt

# 检查数据库连接
python3 check_postgres.py

# 查看详细错误
python3 main.py --log-level debug
```

### 问题 2: 前端无法启动

**症状**: `npm run dev` 报错

**解决方案**:
```bash
# 清理依赖
cd frontend
rm -rf node_modules package-lock.json

# 重新安装
npm install

# 启动
npm run dev
```

### 问题 3: 登录失败

**症状**: 登录时显示 "Invalid username or password"

**解决方案**:
```bash
# 重新创建测试用户
python3 create_test_users_for_login.py

# 检查数据库
python3 check_postgres.py
```

### 问题 4: CORS 错误

**症状**: 浏览器控制台显示 CORS 错误

**解决方案**:
- 确保后端运行在 http://localhost:8000
- 确保前端 `.env.development` 中 `VITE_API_BASE_URL=http://localhost:8000`
- 重启后端服务

### 问题 5: Token 无法存储

**症状**: 登录后 localStorage 中没有 token

**解决方案**:
- 检查浏览器隐私设置
- 尝试无痕模式
- 清除浏览器缓存

---

## 📊 集成测试流程

### 1. 基础连接测试
```bash
# 后端健康检查
curl http://localhost:8000/health

# 前端可访问性
curl http://localhost:5173
```

### 2. 认证流程测试
```bash
# 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}' | jq -r '.access_token')

# 使用 token 获取用户信息
curl -X GET http://localhost:8000/api/security/users/me \
  -H "Authorization: Bearer $TOKEN"
```

### 3. 前端登录测试
1. 打开 http://localhost:5173/login
2. 输入凭证
3. 验证重定向到仪表板
4. 检查 localStorage 中的 token

### 4. 角色权限测试
- 用不同角色登录
- 验证菜单项可见性
- 验证功能访问权限

---

## 📝 启动命令速查表

```bash
# 创建测试用户
python3 create_test_users_for_login.py

# 启动后端（终端 1）
python3 main.py

# 启动前端（终端 2）
cd frontend && npm run dev

# 验证后端
curl http://localhost:8000/health

# 验证前端
curl http://localhost:5173

# 测试登录
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}'

# 查看 Docker 状态
docker-compose -f docker-compose.local.yml ps

# 查看后端日志
tail -f backend.log

# 查看前端日志
# 在前端终端中查看输出
```

---

## 🎯 验证成功标志

✅ **后端就绪**:
- `curl http://localhost:8000/health` 返回 200
- 登录端点可访问
- 数据库连接正常

✅ **前端就绪**:
- `http://localhost:5173` 可访问
- 登录页面正常显示
- API 基础 URL 配置正确

✅ **集成就绪**:
- 可以成功登录
- Token 存储在 localStorage
- 可以访问受保护的页面
- 不同角色有不同的权限

---

## 📚 相关文档

- [登录测试指南](LOGIN_TESTING_GUIDE.md)
- [快速参考](LOGIN_QUICK_REFERENCE.md)
- [测试清单](LOGIN_TESTING_CHECKLIST.md)
- [Docker 操作指南](DOCKER_OPERATIONS_GUIDE.md)

---

## 💡 建议

1. **使用多个终端**: 后端和前端需要在不同的终端中运行
2. **检查端口**: 确保 8000 和 5173 端口未被占用
3. **查看日志**: 遇到问题时查看终端输出和浏览器控制台
4. **清除缓存**: 如果遇到奇怪问题，尝试清除浏览器缓存
5. **重启服务**: 修改代码后需要重启相应的服务

---

**最后更新**: 2026-01-09  
**状态**: 🔧 等待手动启动
