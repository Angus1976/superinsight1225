# Docker Fullstack 分析与问题诊断

**日期**: 2026-01-09  
**状态**: 🔍 问题分析完成

---

## 📊 当前系统状态分析

### ✅ 正常运行的服务
- **Label Studio** (8080): ✅ 可访问
- **Neo4j** (7474): ✅ 可访问
- **PostgreSQL** (5432): ✅ 运行中
- **Redis** (6379): ✅ 运行中

### ❌ 无法访问的服务
- **Backend API** (8000): ❌ 无法访问
- **Frontend** (5173): ❌ 无法访问

---

## 🔍 问题根本原因分析

### 问题 1: 后端 API (8000) 无法访问

**根本原因**:
1. `docker-compose.local.yml` 中**没有定义** `superinsight-api` 服务
2. `docker-compose.yml` 中虽然定义了 `superinsight-api` 服务，但需要构建 Docker 镜像
3. `main.py` 只是初始化脚本，不是 FastAPI 应用启动脚本
4. 实际的 FastAPI 应用应该在 `src/app.py` 中

**当前配置问题**:
```yaml
# docker-compose.local.yml - 缺少后端服务定义
# 只有: postgres, redis, neo4j, label-studio
# 缺少: superinsight-api
```

### 问题 2: 前端 (5173) 无法访问

**根本原因**:
1. `docker-compose.local.yml` 中**没有定义** `superinsight-frontend` 服务
2. `docker-compose.yml` 中也**没有定义** 前端服务
3. 前端需要单独的 Docker 镜像和容器
4. Vite 开发服务器配置中端口是 3000，但文档说 5173

**当前配置问题**:
```yaml
# vite.config.ts
server: {
  port: 3000,  # ← 这里配置的是 3000，不是 5173
  ...
}
```

---

## 🛠️ 解决方案

### 方案概述
创建完整的 Docker Compose 配置，包含所有 7 个服务：

1. **PostgreSQL** (5432) - 数据库
2. **Redis** (6379) - 缓存
3. **Neo4j** (7474, 7687) - 图数据库
4. **Label Studio** (8080) - 标注平台
5. **Backend API** (8000) - FastAPI 后端
6. **Frontend** (5173) - React 前端
7. **Prometheus** (9090) - 监控（可选）

### 需要创建的文件

1. **docker-compose.fullstack.yml** - 完整的 Docker Compose 配置
2. **Dockerfile.backend** - 后端 Docker 镜像
3. **Dockerfile.frontend** - 前端 Docker 镜像
4. **frontend/Dockerfile** - 前端 Docker 镜像（备选）
5. **docker-entrypoint.sh** - 后端启动脚本

### 需要修改的文件

1. **frontend/vite.config.ts** - 修改开发服务器端口为 5173
2. **src/app.py** - 确保 FastAPI 应用正确配置

---

## 📋 实施步骤

### 步骤 1: 创建后端 Dockerfile
- 基于 Python 3.11
- 安装依赖
- 配置 FastAPI 应用启动

### 步骤 2: 创建前端 Dockerfile
- 基于 Node.js 20
- 安装依赖
- 配置 Vite 开发服务器

### 步骤 3: 创建完整的 Docker Compose 配置
- 定义所有 7 个服务
- 配置网络和卷
- 设置健康检查
- 配置依赖关系

### 步骤 4: 启动所有服务
```bash
docker-compose -f docker-compose.fullstack.yml up -d
```

### 步骤 5: 验证所有服务
```bash
# 检查所有容器状态
docker-compose -f docker-compose.fullstack.yml ps

# 检查后端健康状态
curl http://localhost:8000/health

# 检查前端可访问性
curl http://localhost:5173
```

---

## 🎯 预期结果

启动完成后，所有服务应该可访问：

| 服务 | URL | 状态 |
|------|-----|------|
| Frontend | http://localhost:5173 | ✅ 可访问 |
| Backend API | http://localhost:8000 | ✅ 可访问 |
| PostgreSQL | localhost:5432 | ✅ 运行中 |
| Redis | localhost:6379 | ✅ 运行中 |
| Neo4j | http://localhost:7474 | ✅ 可访问 |
| Label Studio | http://localhost:8080 | ✅ 可访问 |

---

## 🔧 故障排查

### 如果后端无法启动
```bash
# 查看后端日志
docker-compose -f docker-compose.fullstack.yml logs superinsight-api

# 检查数据库连接
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  python -c "from src.database.connection import test_database_connection; print(test_database_connection())"
```

### 如果前端无法启动
```bash
# 查看前端日志
docker-compose -f docker-compose.fullstack.yml logs superinsight-frontend

# 检查 npm 依赖
docker-compose -f docker-compose.fullstack.yml exec superinsight-frontend \
  npm list
```

### 如果容器无法通信
```bash
# 检查网络
docker network ls
docker network inspect superinsight-network

# 测试容器间通信
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  curl http://postgres:5432
```

---

## 📝 关键配置

### 后端环境变量
```
DATABASE_URL=postgresql://superinsight:password@postgres:5432/superinsight
REDIS_URL=redis://redis:6379/0
LABEL_STUDIO_URL=http://label-studio:8080
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 前端环境变量
```
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_ENV=development
```

---

## ✅ 验证清单

- [ ] 所有 7 个容器都在运行
- [ ] 后端 API 可访问 (http://localhost:8000)
- [ ] 前端可访问 (http://localhost:5173)
- [ ] 可以登录 (admin_user / Admin@123456)
- [ ] 可以访问所有角色功能
- [ ] 没有 CORS 错误
- [ ] 没有数据库连接错误

---

**下一步**: 执行实施步骤创建完整的 Docker Compose 配置

