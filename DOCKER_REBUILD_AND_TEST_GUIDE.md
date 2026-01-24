# Docker 容器重建和功能测试指南

## 概述

本指南说明如何重建和更新本地 Docker 容器，以及如何进行各角色功能测试。

## 前置条件

- Docker 已安装在 `/Applications/Docker.app/Contents/Resources/bin/docker`
- Git 已配置
- 本地代码已推送到 GitHub

## 快速开始

### 1. 重建容器

```bash
# 使脚本可执行
chmod +x scripts/rebuild-containers.sh

# 运行重建脚本
./scripts/rebuild-containers.sh
```

**脚本功能：**
- ✓ 检查当前容器状态
- ✓ 停止运行中的容器
- ✓ 检查前端代码变更，有变更则重建前端容器
- ✓ 检查后端代码变更，有变更则重建后端容器
- ✓ 启动所有容器
- ✓ 等待服务就绪
- ✓ 显示最终容器状态

### 2. 进行功能测试

```bash
# 使脚本可执行
chmod +x scripts/test-roles-functionality.sh

# 运行测试脚本
./scripts/test-roles-functionality.sh
```

**测试覆盖范围：**
- ✓ 系统健康检查
- ✓ 管理员功能
- ✓ 标注员功能
- ✓ 专家功能
- ✓ 品牌系统功能
- ✓ 管理配置功能
- ✓ AI 标注功能
- ✓ 文本转 SQL 功能
- ✓ 本体协作功能
- ✓ 前端功能

## 详细步骤

### 步骤 1: 重建容器

#### 1.1 自动重建（推荐）

```bash
./scripts/rebuild-containers.sh
```

这个脚本会：
1. 检查前端和后端代码变更
2. 仅重建有变更的容器
3. 保持基础容器（PostgreSQL、Redis 等）不变
4. 自动启动所有容器
5. 等待服务就绪

#### 1.2 手动重建

如果需要完全重建所有容器：

```bash
# 停止所有容器
/Applications/Docker.app/Contents/Resources/bin/docker compose down

# 删除所有容器和卷（谨慎操作）
/Applications/Docker.app/Contents/Resources/bin/docker compose down -v

# 重建所有容器
/Applications/Docker.app/Contents/Resources/bin/docker compose build --no-cache

# 启动所有容器
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d
```

#### 1.3 仅重建特定容器

```bash
# 重建前端容器
/Applications/Docker.app/Contents/Resources/bin/docker compose build --no-cache frontend

# 重建后端容器
/Applications/Docker.app/Contents/Resources/bin/docker compose build --no-cache app

# 启动容器
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d
```

### 步骤 2: 验证容器状态

```bash
# 查看所有容器状态
/Applications/Docker.app/Contents/Resources/bin/docker compose ps

# 查看容器日志
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f app
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f frontend

# 查看特定容器日志
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f postgres
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f redis
```

### 步骤 3: 进行功能测试

#### 3.1 自动测试

```bash
./scripts/test-roles-functionality.sh
```

#### 3.2 手动测试

**系统健康检查：**
```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/system/status
```

**管理员功能：**
```bash
# 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# 获取用户列表
curl http://localhost:8000/api/v1/admin/users

# 获取系统配置
curl http://localhost:8000/api/v1/admin/config
```

**标注员功能：**
```bash
# 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"annotator","password":"password"}'

# 获取标注任务
curl http://localhost:8000/api/v1/annotation/tasks

# 获取质量指标
curl http://localhost:8000/api/v1/annotation/quality-metrics
```

**专家功能：**
```bash
# 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"expert","password":"password"}'

# 获取本体信息
curl http://localhost:8000/api/v1/ontology/info

# 获取协作请求
curl http://localhost:8000/api/v1/ontology/collaboration/requests
```

## 服务地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:5173 | React 应用 |
| 后端 API | http://localhost:8000 | FastAPI 服务 |
| Label Studio | http://localhost:8080 | 标注工具 |
| Argilla | http://localhost:6900 | 数据标注平台 |
| PostgreSQL | localhost:5432 | 数据库 |
| Redis | localhost:6379 | 缓存 |
| Prometheus | http://localhost:9090 | 指标收集 |
| Grafana | http://localhost:3001 | 监控仪表板 |

## 容器说明

### 前端容器 (frontend)
- **镜像**: Node 20 Alpine
- **端口**: 5173
- **用途**: React 应用服务
- **变更检测**: 检查 `frontend/` 目录

### 后端容器 (app)
- **镜像**: Python 3.11
- **端口**: 8000
- **用途**: FastAPI 服务
- **变更检测**: 检查 `src/` 目录

### 基础容器（无需重建）
- **PostgreSQL**: 数据库
- **Redis**: 缓存
- **Label Studio**: 标注工具
- **Argilla**: 数据标注平台
- **Elasticsearch**: 搜索引擎
- **Ollama**: 本地 LLM
- **Prometheus**: 指标收集
- **Grafana**: 监控仪表板

## 故障排除

### 问题 1: Docker 命令找不到

**解决方案：**
```bash
# 添加 Docker 到 PATH
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

# 或创建别名
alias docker="/Applications/Docker.app/Contents/Resources/bin/docker"
```

### 问题 2: 容器启动失败

**检查日志：**
```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose logs app
/Applications/Docker.app/Contents/Resources/bin/docker compose logs frontend
```

**重启容器：**
```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose restart
```

### 问题 3: 端口被占用

**查找占用端口的进程：**
```bash
lsof -i :5173  # 前端
lsof -i :8000  # 后端
lsof -i :5432  # PostgreSQL
```

**杀死进程：**
```bash
kill -9 <PID>
```

### 问题 4: 数据库连接失败

**检查 PostgreSQL 状态：**
```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose logs postgres
```

**重建数据库：**
```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose down -v
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d postgres
```

### 问题 5: 前端无法连接后端

**检查 API 配置：**
```bash
# 检查前端环境变量
cat frontend/.env.development

# 应该包含
VITE_API_BASE_URL=http://localhost:8000
```

**检查后端 CORS 配置：**
```bash
# 查看后端日志
/Applications/Docker.app/Contents/Resources/bin/docker compose logs app | grep -i cors
```

## 性能优化

### 1. 使用构建缓存

脚本会自动检查代码变更，仅重建必要的容器。

### 2. 并行构建

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose build --parallel
```

### 3. 清理未使用的镜像

```bash
/Applications/Docker.app/Contents/Resources/bin/docker image prune -a
```

## 监控和日志

### 实时日志

```bash
# 查看所有容器日志
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f

# 查看特定容器日志
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f app
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f frontend
```

### 性能监控

访问 Grafana 仪表板：
```
http://localhost:3001
用户名: admin
密码: admin
```

### 指标查询

访问 Prometheus：
```
http://localhost:9090
```

## 最佳实践

1. **定期更新镜像**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose pull
   ```

2. **备份数据库**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose exec postgres pg_dump -U superinsight superinsight > backup.sql
   ```

3. **监控容器资源**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker stats
   ```

4. **定期清理**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker system prune
   ```

## 常用命令速查表

```bash
# 启动容器
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d

# 停止容器
/Applications/Docker.app/Contents/Resources/bin/docker compose down

# 查看状态
/Applications/Docker.app/Contents/Resources/bin/docker compose ps

# 查看日志
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f

# 重建容器
/Applications/Docker.app/Contents/Resources/bin/docker compose build --no-cache

# 进入容器
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app bash

# 执行命令
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app python -m pytest

# 查看资源使用
/Applications/Docker.app/Contents/Resources/bin/docker stats
```

## 相关文档

- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [FastAPI 部署指南](https://fastapi.tiangolo.com/deployment/)
- [React 开发指南](https://react.dev/)

---

**最后更新**: 2026-01-25  
**维护者**: SuperInsight 开发团队
