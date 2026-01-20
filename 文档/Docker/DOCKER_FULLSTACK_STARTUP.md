# Docker 全栈启动指南

**日期**: 2026-01-09  
**版本**: 1.0  
**状态**: 🚀 准备启动

---

## 📋 前置条件

### 系统要求
- Docker Desktop 已安装并运行
- Docker Compose v2.0+
- 至少 8GB 可用内存
- 至少 20GB 可用磁盘空间

### 端口检查
确保以下端口未被占用：
```bash
# 检查端口占用
lsof -i :5173  # 前端
lsof -i :8000  # 后端
lsof -i :8080  # Label Studio
lsof -i :7474  # Neo4j
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
```

---

## 🚀 快速启动 (3 步)

### 步骤 1: 停止旧服务 (如果有)
```bash
# 停止并删除旧容器
docker-compose -f docker-compose.local.yml down -v

# 或者使用新的完整配置
docker-compose -f docker-compose.fullstack.yml down -v
```

### 步骤 2: 启动所有服务
```bash
# 启动完整的全栈应用
docker-compose -f docker-compose.fullstack.yml up -d

# 查看启动进度
docker-compose -f docker-compose.fullstack.yml logs -f
```

### 步骤 3: 验证所有服务
```bash
# 检查所有容器状态
docker-compose -f docker-compose.fullstack.yml ps

# 预期输出:
# NAME                      STATUS
# superinsight-postgres     Up (healthy)
# superinsight-redis        Up (healthy)
# superinsight-neo4j        Up (healthy)
# superinsight-label-studio Up (healthy)
# superinsight-api          Up (healthy)
# superinsight-frontend     Up (healthy)
```

---

## 🔗 服务访问地址

启动完成后，所有服务应该可访问：

| 服务 | URL | 用户名 | 密码 |
|------|-----|--------|------|
| **前端登录** | http://localhost:5173/login | admin_user | Admin@123456 |
| **后端 API** | http://localhost:8000 | - | - |
| **后端文档** | http://localhost:8000/docs | - | - |
| **Neo4j** | http://localhost:7474 | neo4j | password |
| **Label Studio** | http://localhost:8080 | admin@superinsight.com | admin123 |

---

## 📊 详细启动步骤

### 1. 清理旧环境
```bash
# 停止所有容器
docker-compose -f docker-compose.local.yml down -v

# 删除所有相关镜像 (可选)
docker rmi superinsight-api superinsight-frontend

# 清理未使用的资源
docker system prune -f
```

### 2. 构建镜像
```bash
# 构建后端镜像
docker build -f Dockerfile.backend -t superinsight-api .

# 构建前端镜像
docker build -f frontend/Dockerfile -t superinsight-frontend ./frontend

# 或者让 docker-compose 自动构建
docker-compose -f docker-compose.fullstack.yml build
```

### 3. 启动所有服务
```bash
# 启动所有容器 (后台运行)
docker-compose -f docker-compose.fullstack.yml up -d

# 或者前台运行 (查看日志)
docker-compose -f docker-compose.fullstack.yml up
```

### 4. 等待服务就绪
```bash
# 监控启动进度
docker-compose -f docker-compose.fullstack.yml logs -f

# 等待所有服务健康检查通过 (约 1-2 分钟)
```

### 5. 创建测试用户
```bash
# 进入后端容器
docker-compose -f docker-compose.fullstack.yml exec superinsight-api bash

# 创建测试用户
python create_test_users_for_login.py

# 退出容器
exit
```

### 6. 验证服务
```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 检查前端可访问性
curl http://localhost:5173

# 测试登录
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_user","password":"Admin@123456"}'
```

---

## 🧪 测试登录

### 在浏览器中测试

1. 打开 http://localhost:5173/login
2. 输入凭证：
   - 用户名: `admin_user`
   - 密码: `Admin@123456`
3. 点击登录
4. 验证重定向到仪表板

### 测试所有角色

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin_user | Admin@123456 |
| 业务专家 | business_expert | Business@123456 |
| 技术专家 | technical_expert | Technical@123456 |
| 承包商 | contractor | Contractor@123456 |
| 查看者 | viewer | Viewer@123456 |

---

## 📋 常用命令

### 查看日志
```bash
# 查看所有服务日志
docker-compose -f docker-compose.fullstack.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.fullstack.yml logs -f superinsight-api
docker-compose -f docker-compose.fullstack.yml logs -f superinsight-frontend

# 查看最后 100 行日志
docker-compose -f docker-compose.fullstack.yml logs --tail=100
```

### 进入容器
```bash
# 进入后端容器
docker-compose -f docker-compose.fullstack.yml exec superinsight-api bash

# 进入前端容器
docker-compose -f docker-compose.fullstack.yml exec superinsight-frontend sh

# 进入数据库容器
docker-compose -f docker-compose.fullstack.yml exec postgres psql -U superinsight -d superinsight
```

### 重启服务
```bash
# 重启所有服务
docker-compose -f docker-compose.fullstack.yml restart

# 重启特定服务
docker-compose -f docker-compose.fullstack.yml restart superinsight-api
docker-compose -f docker-compose.fullstack.yml restart superinsight-frontend

# 重新构建并启动
docker-compose -f docker-compose.fullstack.yml up -d --build
```

### 停止和清理
```bash
# 停止所有容器
docker-compose -f docker-compose.fullstack.yml stop

# 停止并删除容器
docker-compose -f docker-compose.fullstack.yml down

# 停止、删除容器和卷
docker-compose -f docker-compose.fullstack.yml down -v

# 删除所有镜像
docker-compose -f docker-compose.fullstack.yml down -v --rmi all
```

---

## 🔍 故障排查

### 问题 1: 后端无法启动

**症状**: `superinsight-api` 容器不断重启

**解决方案**:
```bash
# 查看详细日志
docker-compose -f docker-compose.fullstack.yml logs superinsight-api

# 检查数据库连接
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  python -c "from src.database.connection import test_database_connection; print(test_database_connection())"

# 检查依赖
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  pip list | grep -E "fastapi|uvicorn|sqlalchemy"
```

### 问题 2: 前端无法启动

**症状**: `superinsight-frontend` 容器不断重启

**解决方案**:
```bash
# 查看详细日志
docker-compose -f docker-compose.fullstack.yml logs superinsight-frontend

# 检查 npm 依赖
docker-compose -f docker-compose.fullstack.yml exec superinsight-frontend \
  npm list

# 重新安装依赖
docker-compose -f docker-compose.fullstack.yml exec superinsight-frontend \
  npm ci
```

### 问题 3: CORS 错误

**症状**: 浏览器控制台显示 CORS 错误

**解决方案**:
```bash
# 检查后端 CORS 配置
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  grep -r "CORS" src/

# 检查前端 API 基础 URL
docker-compose -f docker-compose.fullstack.yml exec superinsight-frontend \
  grep -r "VITE_API_BASE_URL" .env*
```

### 问题 4: 数据库连接失败

**症状**: 后端日志显示数据库连接错误

**解决方案**:
```bash
# 检查 PostgreSQL 状态
docker-compose -f docker-compose.fullstack.yml ps postgres

# 测试数据库连接
docker-compose -f docker-compose.fullstack.yml exec postgres \
  psql -U superinsight -d superinsight -c "SELECT 1"

# 查看数据库日志
docker-compose -f docker-compose.fullstack.yml logs postgres
```

### 问题 5: 端口已被占用

**症状**: 启动时显示 "Address already in use"

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8000
lsof -i :5173

# 杀死进程
kill -9 <PID>

# 或者修改 docker-compose.fullstack.yml 中的端口映射
# 例如: "8001:8000" 而不是 "8000:8000"
```

### 问题 6: 容器间无法通信

**症状**: 后端无法连接到数据库或其他服务

**解决方案**:
```bash
# 检查网络
docker network ls
docker network inspect superinsight-network

# 测试容器间通信
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  ping postgres

# 检查 DNS 解析
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  nslookup postgres
```

---

## 📊 性能监控

### 查看资源使用情况
```bash
# 实时监控
docker stats

# 查看特定容器
docker stats superinsight-api superinsight-frontend
```

### 查看容器详细信息
```bash
# 查看容器配置
docker inspect superinsight-api

# 查看容器网络
docker inspect superinsight-api | grep -A 20 "Networks"
```

---

## 🔐 安全建议

### 生产环境配置
1. 修改所有默认密码
2. 启用 HTTPS
3. 配置防火墙规则
4. 使用环境变量管理敏感信息
5. 定期备份数据库

### 环境变量管理
```bash
# 创建 .env 文件
cat > .env << EOF
POSTGRES_PASSWORD=your-secure-password
REDIS_PASSWORD=your-secure-password
NEO4J_PASSWORD=your-secure-password
JWT_SECRET_KEY=your-secret-key
EOF

# 在 docker-compose.fullstack.yml 中引用
env_file:
  - .env
```

---

## ✅ 启动验证清单

- [ ] 所有 6 个容器都在运行
- [ ] 后端 API 可访问 (http://localhost:8000)
- [ ] 前端可访问 (http://localhost:5173)
- [ ] 可以登录 (admin_user / Admin@123456)
- [ ] 可以访问所有角色功能
- [ ] 没有 CORS 错误
- [ ] 没有数据库连接错误
- [ ] 没有 npm 依赖错误
- [ ] 所有健康检查都通过

---

## 📞 获取帮助

### 查看日志
```bash
# 查看完整日志
docker-compose -f docker-compose.fullstack.yml logs

# 导出日志到文件
docker-compose -f docker-compose.fullstack.yml logs > docker-logs.txt
```

### 收集诊断信息
```bash
# 创建诊断报告
docker-compose -f docker-compose.fullstack.yml ps > status.txt
docker stats --no-stream >> status.txt
docker network inspect superinsight-network >> status.txt
```

---

## 🎯 下一步

1. ✅ 启动所有服务
2. ✅ 创建测试用户
3. ✅ 测试登录功能
4. ✅ 测试所有角色
5. ✅ 运行自动化测试
6. ✅ 部署到生产环境

---

**最后更新**: 2026-01-09  
**版本**: 1.0

