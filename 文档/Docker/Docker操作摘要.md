# Docker 操作总结

## 📋 Docker 路径记录

**macOS Docker 路径：**
```
/Applications/Docker.app/Contents/Resources/bin/docker
```

## 🚀 快速开始

### 1. 一键设置 Docker 环境

```bash
chmod +x scripts/docker-setup.sh
./scripts/docker-setup.sh
```

这会：
- ✓ 验证 Docker 安装
- ✓ 创建 `docker` 别名
- ✓ 配置 shell 环境

### 2. 一键重建容器

```bash
chmod +x scripts/rebuild-containers.sh
./scripts/rebuild-containers.sh
```

这会：
- ✓ 检查代码变更
- ✓ 仅重建必要的容器
- ✓ 启动所有服务
- ✓ 等待服务就绪

### 3. 一键测试功能

```bash
chmod +x scripts/test-roles-functionality.sh
./scripts/test-roles-functionality.sh
```

这会：
- ✓ 测试系统健康
- ✓ 测试管理员功能
- ✓ 测试标注员功能
- ✓ 测试专家功能
- ✓ 测试品牌系统
- ✓ 测试管理配置
- ✓ 测试 AI 标注
- ✓ 测试文本转 SQL
- ✓ 测试本体协作
- ✓ 测试前端功能

## 📁 创建的文件

### 脚本文件

| 文件 | 说明 |
|------|------|
| `scripts/rebuild-containers.sh` | 重建容器脚本 |
| `scripts/test-roles-functionality.sh` | 功能测试脚本 |
| `scripts/docker-setup.sh` | Docker 环境设置脚本 |

### 配置文件

| 文件 | 说明 |
|------|------|
| `.env.docker` | Docker 路径配置 |
| `docker-compose.yml` | 已更新，添加前端容器 |

### 文档文件

| 文件 | 说明 |
|------|------|
| `DOCKER_REBUILD_AND_TEST_GUIDE.md` | 详细操作指南 |
| `DOCKER_OPERATIONS_SUMMARY.md` | 本文件 |

## 🔧 常用命令

### 基础命令

```bash
# 查看容器状态
docker compose ps

# 启动容器
docker compose up -d

# 停止容器
docker compose down

# 查看日志
docker compose logs -f

# 重建容器
docker compose build --no-cache
```

### 前端相关

```bash
# 查看前端日志
docker compose logs -f frontend

# 进入前端容器
docker compose exec frontend sh

# 重建前端容器
docker compose build --no-cache frontend
```

### 后端相关

```bash
# 查看后端日志
docker compose logs -f app

# 进入后端容器
docker compose exec app bash

# 运行后端测试
docker compose exec app pytest tests/

# 重建后端容器
docker compose build --no-cache app
```

### 数据库相关

```bash
# 查看数据库日志
docker compose logs -f postgres

# 进入数据库容器
docker compose exec postgres psql -U superinsight -d superinsight

# 备份数据库
docker compose exec postgres pg_dump -U superinsight superinsight > backup.sql

# 恢复数据库
docker compose exec -T postgres psql -U superinsight superinsight < backup.sql
```

## 📊 服务地址

| 服务 | 地址 | 用户名 | 密码 |
|------|------|--------|------|
| 前端 | http://localhost:5173 | - | - |
| 后端 API | http://localhost:8000 | - | - |
| Label Studio | http://localhost:8080 | admin@example.com | admin |
| Argilla | http://localhost:6900 | - | - |
| Prometheus | http://localhost:9090 | - | - |
| Grafana | http://localhost:3001 | admin | admin |

## 🧪 测试场景

### 场景 1: 管理员操作

```bash
# 1. 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# 2. 查看用户列表
curl http://localhost:8000/api/v1/admin/users

# 3. 查看系统配置
curl http://localhost:8000/api/v1/admin/config

# 4. 查看审计日志
curl http://localhost:8000/api/v1/admin/audit-logs
```

### 场景 2: 标注员操作

```bash
# 1. 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"annotator","password":"password"}'

# 2. 获取标注任务
curl http://localhost:8000/api/v1/annotation/tasks

# 3. 获取质量指标
curl http://localhost:8000/api/v1/annotation/quality-metrics
```

### 场景 3: 专家操作

```bash
# 1. 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"expert","password":"password"}'

# 2. 获取本体信息
curl http://localhost:8000/api/v1/ontology/info

# 3. 获取协作请求
curl http://localhost:8000/api/v1/ontology/collaboration/requests
```

## 🐛 故障排除

### 问题：Docker 命令找不到

**解决方案：**
```bash
# 方案 1: 使用完整路径
/Applications/Docker.app/Contents/Resources/bin/docker compose ps

# 方案 2: 运行设置脚本
./scripts/docker-setup.sh

# 方案 3: 手动添加别名
alias docker="/Applications/Docker.app/Contents/Resources/bin/docker"
```

### 问题：容器启动失败

**检查步骤：**
```bash
# 1. 查看容器日志
docker compose logs app
docker compose logs frontend

# 2. 检查容器状态
docker compose ps

# 3. 重启容器
docker compose restart

# 4. 完全重建
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 问题：端口被占用

**查找和杀死进程：**
```bash
# 查找占用端口的进程
lsof -i :5173  # 前端
lsof -i :8000  # 后端
lsof -i :5432  # 数据库

# 杀死进程
kill -9 <PID>
```

### 问题：前端无法连接后端

**检查步骤：**
```bash
# 1. 检查后端是否运行
curl http://localhost:8000/health/live

# 2. 检查前端环境变量
cat frontend/.env.development

# 3. 查看前端日志
docker compose logs -f frontend

# 4. 检查 CORS 配置
docker compose logs app | grep -i cors
```

## 📈 性能优化

### 1. 使用构建缓存

脚本会自动检查代码变更，仅重建必要的容器。

### 2. 并行构建

```bash
docker compose build --parallel
```

### 3. 清理未使用资源

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的卷
docker volume prune

# 清理系统
docker system prune
```

## 📝 工作流程

### 开发流程

1. **修改代码**
   ```bash
   # 编辑代码
   vim src/app.py
   vim frontend/src/App.tsx
   ```

2. **重建容器**
   ```bash
   ./scripts/rebuild-containers.sh
   ```

3. **测试功能**
   ```bash
   ./scripts/test-roles-functionality.sh
   ```

4. **提交代码**
   ```bash
   git add .
   git commit -m "feat: ..."
   git push
   ```

### 部署流程

1. **拉取最新代码**
   ```bash
   git pull origin feature/system-optimization
   ```

2. **重建容器**
   ```bash
   ./scripts/rebuild-containers.sh
   ```

3. **运行测试**
   ```bash
   ./scripts/test-roles-functionality.sh
   ```

4. **监控服务**
   ```bash
   docker compose logs -f
   ```

## 🔐 安全建议

1. **更改默认密码**
   - Grafana: admin/admin
   - Label Studio: admin@example.com/admin

2. **配置防火墙**
   - 仅在本地开发时暴露端口
   - 生产环境使用反向代理

3. **定期备份**
   ```bash
   docker compose exec postgres pg_dump -U superinsight superinsight > backup.sql
   ```

4. **监控日志**
   ```bash
   docker compose logs -f | grep -i error
   ```

## 📚 相关文档

- [DOCKER_REBUILD_AND_TEST_GUIDE.md](./DOCKER_REBUILD_AND_TEST_GUIDE.md) - 详细操作指南
- [docker-compose.yml](./docker-compose.yml) - Docker Compose 配置
- [.env.docker](./.env.docker) - Docker 路径配置

## 🎯 下一步

1. ✅ 运行 `./scripts/docker-setup.sh` 配置 Docker 环境
2. ✅ 运行 `./scripts/rebuild-containers.sh` 重建容器
3. ✅ 运行 `./scripts/test-roles-functionality.sh` 测试功能
4. ✅ 访问 http://localhost:5173 查看前端
5. ✅ 访问 http://localhost:3001 查看 Grafana 监控

---

**最后更新**: 2026-01-25  
**维护者**: SuperInsight 开发团队
