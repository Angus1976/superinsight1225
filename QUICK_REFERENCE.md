# 🚀 快速参考卡片

## Docker 路径
```
/Applications/Docker.app/Contents/Resources/bin/docker
```

## 三步启动

### 1️⃣ 设置 Docker 环境
```bash
chmod +x scripts/docker-setup.sh
./scripts/docker-setup.sh
```

### 2️⃣ 重建容器
```bash
chmod +x scripts/rebuild-containers.sh
./scripts/rebuild-containers.sh
```

### 3️⃣ 测试功能
```bash
chmod +x scripts/test-roles-functionality.sh
./scripts/test-roles-functionality.sh
```

## 服务地址

| 服务 | 地址 |
|------|------|
| 🎨 前端 | http://localhost:5173 |
| 🔌 后端 API | http://localhost:8000 |
| 📝 Label Studio | http://localhost:8080 |
| 🏷️ Argilla | http://localhost:6900 |
| 📊 Prometheus | http://localhost:9090 |
| 📈 Grafana | http://localhost:3001 |

## 常用命令

```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f

# 启动容器
docker compose up -d

# 停止容器
docker compose down

# 重建容器
docker compose build --no-cache

# 进入容器
docker compose exec app bash
docker compose exec frontend sh
```

## 测试 API

### 管理员登录
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

### 获取用户列表
```bash
curl http://localhost:8000/api/v1/admin/users
```

### 获取系统状态
```bash
curl http://localhost:8000/health/live
```

## 文档

- 📖 [详细指南](./DOCKER_REBUILD_AND_TEST_GUIDE.md)
- 📋 [操作总结](./DOCKER_OPERATIONS_SUMMARY.md)

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| Docker 命令找不到 | 运行 `./scripts/docker-setup.sh` |
| 容器启动失败 | 查看日志 `docker compose logs app` |
| 端口被占用 | 运行 `lsof -i :PORT` 找到进程并杀死 |
| 前端无法连接后端 | 检查 `frontend/.env.development` |

---

**💡 提示**: 所有脚本都已配置好 Docker 路径，直接运行即可！
