# Docker 全栈完整设置指南

**日期**: 2026-01-09  
**版本**: 2.0  
**状态**: ✅ 完成

---

## 📋 问题分析总结

### 原始问题
- ❌ http://localhost:5173/login - 无法打开
- ❌ http://localhost:8000 - 无法打开
- ✅ http://localhost:8080 - 可以打开 (Label Studio)
- ✅ http://localhost:7474 - 可以打开 (Neo4j)

### 根本原因

#### 1. 后端 (8000) 无法访问
**原因**:
- `docker-compose.local.yml` 中没有定义 `superinsight-api` 服务
- 后端需要单独的 Docker 容器来运行 FastAPI 应用
- `main.py` 只是初始化脚本，不是应用启动脚本

**解决方案**:
- 创建 `Dockerfile.backend` 来构建后端镜像
- 在 `docker-compose.fullstack.yml` 中定义后端服务
- 使用 `uvicorn` 启动 FastAPI 应用

#### 2. 前端 (5173) 无法访问
**原因**:
- `docker-compose.local.yml` 中没有定义前端服务
- 前端需要单独的 Docker 容器来运行 Vite 开发服务器
- `vite.config.ts` 中端口配置为 3000，不是 5173

**解决方案**:
- 创建 `frontend/Dockerfile` 来构建前端镜像
- 在 `docker-compose.fullstack.yml` 中定义前端服务
- 修改 `vite.config.ts` 中的端口为 5173

---

## 📦 创建的文件

### 1. Docker Compose 配置
**文件**: `docker-compose.fullstack.yml`
- 定义 6 个服务: PostgreSQL, Redis, Neo4j, Label Studio, Backend API, Frontend
- 配置网络和卷
- 设置健康检查
- 配置依赖关系

### 2. 后端 Dockerfile
**文件**: `Dockerfile.backend`
- 基于 Python 3.11
- 安装依赖
- 启动 FastAPI 应用 (uvicorn)
- 端口: 8000

### 3. 前端 Dockerfile
**文件**: `frontend/Dockerfile`
- 基于 Node.js 20
- 安装 npm 依赖
- 启动 Vite 开发服务器
- 端口: 5173

### 4. 启动脚本
**文件**: `start-fullstack.sh`
- 自动化启动流程
- 检查 Docker 和端口
- 构建镜像
- 启动容器
- 等待服务就绪
- 创建测试用户
- 验证服务

### 5. 文档
**文件**: 
- `DOCKER_FULLSTACK_ANALYSIS.md` - 问题分析
- `DOCKER_FULLSTACK_STARTUP.md` - 详细启动指南
- `DOCKER_FULLSTACK_COMPLETE_SETUP.md` - 本文件

### 6. 修改的文件
**文件**: `frontend/vite.config.ts`
- 修改开发服务器端口: 3000 → 5173
- 添加 host: 0.0.0.0 (允许容器外访问)

---

## 🚀 快速启动

### 方式 1: 使用启动脚本 (推荐)

```bash
# 给脚本添加执行权限
chmod +x start-fullstack.sh

# 运行启动脚本
./start-fullstack.sh
```

**脚本会自动**:
1. ✅ 检查 Docker 状态
2. ✅ 检查端口可用性
3. ✅ 停止旧容器
4. ✅ 构建镜像
5. ✅ 启动所有服务
6. ✅ 等待服务就绪
7. ✅ 创建测试用户
8. ✅ 验证服务
9. ✅ 显示访问地址

### 方式 2: 手动启动

```bash
# 1. 停止旧服务
docker-compose -f docker-compose.local.yml down -v

# 2. 构建镜像
docker-compose -f docker-compose.fullstack.yml build

# 3. 启动所有服务
docker-compose -f docker-compose.fullstack.yml up -d

# 4. 查看启动进度
docker-compose -f docker-compose.fullstack.yml logs -f

# 5. 创建测试用户
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  python create_test_users_for_login.py

# 6. 验证服务
curl http://localhost:8000/health
curl http://localhost:5173
```

---

## 🔗 服务访问地址

启动完成后，所有服务应该可访问：

| 服务 | URL | 用户名 | 密码 | 状态 |
|------|-----|--------|------|------|
| **前端登录** | http://localhost:5173/login | admin_user | Admin@123456 | ✅ |
| **后端 API** | http://localhost:8000 | - | - | ✅ |
| **API 文档** | http://localhost:8000/docs | - | - | ✅ |
| **Neo4j** | http://localhost:7474 | neo4j | password | ✅ |
| **Label Studio** | http://localhost:8080 | admin@superinsight.com | admin123 | ✅ |
| **PostgreSQL** | localhost:5432 | superinsight | password | ✅ |
| **Redis** | localhost:6379 | - | - | ✅ |

---

## 🧪 测试所有角色

### 测试凭证

| 角色 | 用户名 | 密码 | 权限 |
|------|--------|------|------|
| 管理员 | admin_user | Admin@123456 | 完全访问 |
| 业务专家 | business_expert | Business@123456 | 业务模块 |
| 技术专家 | technical_expert | Technical@123456 | 技术模块 |
| 承包商 | contractor | Contractor@123456 | 受限访问 |
| 查看者 | viewer | Viewer@123456 | 只读访问 |

### 测试步骤

1. 打开 http://localhost:5173/login
2. 输入上表中的任意凭证
3. 点击登录
4. 验证重定向到仪表板
5. 检查菜单项和功能可见性
6. 验证角色权限

---

## 📊 容器架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                            │
│              (superinsight-network)                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Frontend    │  │   Backend    │  │  Label       │       │
│  │  (5173)      │  │   API        │  │  Studio      │       │
│  │              │  │   (8000)     │  │  (8080)      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │               │
│         └──────────────────┼──────────────────┘               │
│                            │                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  PostgreSQL  │  │    Redis     │  │    Neo4j     │       │
│  │  (5432)      │  │   (6379)     │  │  (7474)      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 常用命令

### 查看状态
```bash
# 查看所有容器状态
docker-compose -f docker-compose.fullstack.yml ps

# 查看实时日志
docker-compose -f docker-compose.fullstack.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.fullstack.yml logs -f superinsight-api
docker-compose -f docker-compose.fullstack.yml logs -f superinsight-frontend
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

### 后端无法启动

```bash
# 查看详细日志
docker-compose -f docker-compose.fullstack.yml logs superinsight-api

# 检查数据库连接
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  python -c "from src.database.connection import test_database_connection; print(test_database_connection())"

# 检查依赖
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  pip list | grep -E "fastapi|uvicorn"
```

### 前端无法启动

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

### CORS 错误

```bash
# 检查后端 CORS 配置
docker-compose -f docker-compose.fullstack.yml exec superinsight-api \
  grep -r "CORS" src/

# 检查前端 API 基础 URL
docker-compose -f docker-compose.fullstack.yml exec superinsight-frontend \
  cat .env.development
```

### 端口已被占用

```bash
# 查找占用端口的进程
lsof -i :8000
lsof -i :5173

# 杀死进程
kill -9 <PID>
```

---

## ✅ 验证清单

启动完成后，请验证以下项目：

- [ ] 所有 6 个容器都在运行
  ```bash
  docker-compose -f docker-compose.fullstack.yml ps
  ```

- [ ] 后端 API 可访问
  ```bash
  curl http://localhost:8000/health
  ```

- [ ] 前端可访问
  ```bash
  curl http://localhost:5173
  ```

- [ ] 可以登录
  - 打开 http://localhost:5173/login
  - 输入 admin_user / Admin@123456
  - 验证重定向到仪表板

- [ ] 可以访问所有角色功能
  - 用不同角色登录
  - 验证菜单项可见性
  - 验证功能访问权限

- [ ] 没有 CORS 错误
  - 打开浏览器开发者工具
  - 检查 Console 标签
  - 确认没有 CORS 错误

- [ ] 没有数据库连接错误
  - 查看后端日志
  - 确认数据库连接成功

- [ ] 没有 npm 依赖错误
  - 查看前端日志
  - 确认所有依赖已安装

---

## 📚 相关文档

- [Docker Fullstack 分析](DOCKER_FULLSTACK_ANALYSIS.md)
- [Docker Fullstack 启动指南](DOCKER_FULLSTACK_STARTUP.md)
- [登录测试指南](LOGIN_TESTING_GUIDE.md)
- [快速参考](LOGIN_QUICK_REFERENCE.md)

---

## 🎯 下一步

1. ✅ 运行启动脚本或手动启动
2. ✅ 验证所有服务可访问
3. ✅ 创建测试用户
4. ✅ 测试登录功能
5. ✅ 测试所有角色
6. ✅ 运行自动化测试
7. ✅ 部署到生产环境

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

**最后更新**: 2026-01-09  
**版本**: 2.0  
**状态**: ✅ 完成

