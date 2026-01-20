# SuperInsight 前端访问指南

## 🌐 前端访问信息

### 本地开发环境

**前端地址**: http://localhost:5173  
**登录页面**: http://localhost:5173/login

### Docker 环境

**前端地址**: http://localhost:5173  
**登录页面**: http://localhost:5173/login

---

## 👤 测试账号

### 管理员账号（推荐）
```
用户名: admin_user
密码: Admin@123456
邮箱: admin@superinsight.local
角色: 系统管理员
```

### 业务专家账号
```
用户名: business_expert
密码: Business@123456
邮箱: business@superinsight.local
角色: 业务专家
```

### 技术专家账号
```
用户名: technical_expert
密码: Technical@123456
邮箱: technical@superinsight.local
角色: 技术专家
```

### 外包人员账号
```
用户名: contractor
密码: Contractor@123456
邮箱: contractor@superinsight.local
角色: 外包标注员
```

### 查看者账号
```
用户名: viewer
密码: Viewer@123456
邮箱: viewer@superinsight.local
角色: 只读查看者
```

---

## 🚀 快速启动

### 方法 1: Docker Compose（推荐）

```bash
# 启动完整栈（包括前端）
docker-compose -f docker-compose.fullstack.yml up -d

# 创建测试账号
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  python create_test_users_for_login.py

# 访问前端
open http://localhost:5173/login
```

### 方法 2: 本地开发

```bash
# 1. 启动后端服务
docker-compose up -d  # 启动数据库等基础服务
python main.py        # 启动 API 服务器

# 2. 创建测试账号
python create_test_users_for_login.py

# 3. 启动前端（新终端）
cd frontend
npm install  # 首次运行需要
npm run dev

# 4. 访问前端
open http://localhost:5173/login
```

---

## 🔗 所有服务地址

| 服务 | 地址 | 端口 | 说明 |
|------|------|------|------|
| **前端应用** | http://localhost:5173 | 5173 | React + Vite |
| **后端 API** | http://localhost:8000 | 8000 | FastAPI |
| **API 文档** | http://localhost:8000/docs | 8000 | Swagger UI |
| **Label Studio** | http://localhost:8080 | 8080 | 标注引擎 |
| **Neo4j 浏览器** | http://localhost:7474 | 7474 | 图数据库 |
| PostgreSQL | localhost:5432 | 5432 | 关系数据库 |
| Redis | localhost:6379 | 6379 | 缓存 |
| Neo4j Bolt | bolt://localhost:7687 | 7687 | 图数据库协议 |

---

## 🔐 其他服务凭证

### Label Studio
```
用户名: admin@superinsight.com
密码: admin123
```

### Neo4j
```
用户名: neo4j
密码: password
```

### PostgreSQL
```
数据库: superinsight
用户名: superinsight
密码: password
```

---

## 📱 登录步骤

1. **打开浏览器**，访问 http://localhost:5173/login

2. **输入账号**（推荐使用管理员账号）:
   ```
   用户名: admin_user
   密码: Admin@123456
   ```

3. **点击登录按钮**

4. **登录成功后**，您将看到主控制台界面

---

## ❓ 常见问题

### Q: 前端无法访问？
**A**: 检查前端容器是否运行
```bash
docker ps | grep frontend
# 或
cd frontend && npm run dev
```

### Q: 登录失败？
**A**: 确保测试账号已创建
```bash
python create_test_users_for_login.py
```

### Q: 页面显示 "Cannot connect to API"？
**A**: 检查后端 API 是否运行
```bash
curl http://localhost:8000/health
```

### Q: 忘记密码？
**A**: 使用上面列出的测试账号，或重新创建：
```bash
python create_test_users_for_login.py
```

### Q: 前端端口被占用？
**A**: 修改 `frontend/vite.config.ts` 中的端口配置，或停止占用 5173 端口的进程

---

## 🛠️ 开发工具

### 浏览器开发者工具
- **F12** 或 **右键 → 检查** 打开开发者工具
- **Console** 标签查看日志
- **Network** 标签查看 API 请求
- **Application** 标签查看 LocalStorage（JWT Token）

### API 测试
```bash
# 测试登录 API
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}'

# 测试健康检查
curl http://localhost:8000/health
```

---

## 📚 相关文档

- **完整登录指南**: `LOGIN_QUICK_REFERENCE.md`
- **前端测试指南**: `FRONTEND_TESTING_GUIDE.md`
- **Docker 部署**: `DOCKER_FULLSTACK_COMPLETE_GUIDE.md`
- **故障排除**: `TROUBLESHOOTING_GUIDE.md`

---

## 🎯 快速复制（管理员账号）

```
地址: http://localhost:5173/login
用户名: admin_user
密码: Admin@123456
```

**祝您使用愉快！** 🎉
