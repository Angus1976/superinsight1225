# 登录凭证汇总 - 2026-01-19

## SuperInsight 前端 & 后端 API

### 访问地址
- **前端**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

### 测试账号

#### 1. 管理员账号
- **用户名**: `admin_user`
- **密码**: `Admin@123456`
- **角色**: 管理员 (Admin)
- **权限**: 完全访问所有功能

#### 2. 业务专家账号
- **用户名**: `business_expert`
- **密码**: `Business@123456`
- **角色**: 业务专家 (Business Expert)
- **权限**: 业务相关功能访问

#### 3. 技术专家账号
- **用户名**: `tech_expert`
- **密码**: `Tech@123456`
- **角色**: 技术专家 (Technical Expert)
- **权限**: 技术相关功能访问

---

## Label Studio 标注平台

### 访问地址
- **Label Studio**: http://localhost:8080

### 登录凭证
- **邮箱**: `admin@superinsight.com`
- **密码**: `admin123`

### 说明
- Label Studio 是集成的数据标注引擎
- 支持中文界面 (zh-CN)
- 用于数据标注和协作工作流

---

## 数据库连接信息

### PostgreSQL
- **主机**: localhost
- **端口**: 5432
- **数据库**: superinsight
- **用户名**: superinsight
- **密码**: password

### Redis
- **主机**: localhost
- **端口**: 6379
- **数据库**: 0

### Neo4j
- **主机**: localhost
- **HTTP 端口**: 7474
- **Bolt 端口**: 7687
- **用户名**: neo4j
- **密码**: password

---

## 快速测试步骤

### 1. 登录前端
```bash
# 打开浏览器访问
http://localhost:5173

# 使用以下任一账号登录
用户名: admin_user
密码: Admin@123456
```

### 2. 测试 API
```bash
# 获取健康状态
curl http://localhost:8000/health

# 登录获取 Token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}'

# 查看 API 文档
http://localhost:8000/docs
```

### 3. 访问 Label Studio
```bash
# 打开浏览器访问
http://localhost:8080

# 使用以下凭证登录
邮箱: admin@superinsight.com
密码: admin123
```

---

## 容器状态检查

### 查看所有运行中的容器
```bash
docker ps | grep superinsight
```

### 查看容器日志
```bash
# 后端 API 日志
docker logs superinsight-api -f

# 前端日志
docker logs superinsight-frontend -f

# Label Studio 日志
docker logs superinsight-label-studio -f
```

### 检查容器健康状态
```bash
# 后端 API 健康检查
curl http://localhost:8000/health

# 前端健康检查
curl http://localhost:5173

# Label Studio 健康检查
curl http://localhost:8080/health
```

---

## 常见问题

### Q: 忘记密码怎么办？
A: 这些是测试账号，密码固定。如需重置，可以：
1. 停止容器: `docker compose down`
2. 删除数据卷: `docker volume rm superdata_postgres_data`
3. 重新启动: `docker compose up -d`

### Q: 如何创建新用户？
A: 可以通过以下方式：
1. 使用管理员账号登录前端
2. 进入用户管理页面
3. 创建新用户

### Q: API 文档在哪里？
A: 访问 http://localhost:8000/docs (Swagger UI)

### Q: 如何切换语言？
A: 前端支持中文和英文，可在设置中切换

---

## 安全提示

⚠️ **重要**: 这些是开发/测试凭证，仅用于本地开发环境。

- 不要在生产环境使用这些凭证
- 不要将凭证提交到版本控制系统
- 生产环境应使用强密码和安全的密钥管理

---

**最后更新**: 2026-01-19  
**状态**: ✅ 所有服务运行正常
