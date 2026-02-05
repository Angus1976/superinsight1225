# Docker 容器重建指南

**日期**: 2026-01-25  
**目的**: 重建前后端容器以应用管理后台翻译修复

---

## 📋 前提条件

### 1. 安装 Docker

**macOS (推荐使用 Homebrew):**
```bash
brew install --cask docker
```

**或者从官网下载:**
- 访问: https://www.docker.com/products/docker-desktop/
- 下载 Docker Desktop for Mac
- 安装并启动应用程序

**验证安装:**
```bash
docker --version
docker compose version
```

### 2. 启动 Docker Desktop

确保 Docker Desktop 应用程序正在运行（菜单栏会显示 Docker 图标）。

---

## 🚀 快速重建（推荐）

使用提供的自动化脚本：

```bash
./rebuild-containers.sh
```

这个脚本会：
1. ✅ 检查 Docker 是否安装和运行
2. 🛑 停止现有容器
3. 🔨 重建前端容器（包含翻译修复）
4. 🔨 重建后端容器
5. 🚀 启动所有服务
6. 📊 显示服务状态和日志

---

## 🔧 手动重建步骤

如果你想手动控制每个步骤：

### 步骤 1: 停止现有容器

```bash
docker compose down
```

### 步骤 2: 重建前端容器

```bash
# 重建前端（包含翻译修复）
docker compose build frontend --no-cache

# 或者只重建前端
docker compose up -d --build frontend
```

### 步骤 3: 重建后端容器

```bash
# 重建后端
docker compose build app --no-cache

# 或者只重建后端
docker compose up -d --build app
```

### 步骤 4: 启动所有服务

```bash
# 启动所有服务
docker compose up -d

# 或者启动特定服务
docker compose up -d frontend app
```

### 步骤 5: 验证服务状态

```bash
# 查看所有容器状态
docker compose ps

# 查看前端日志
docker compose logs -f frontend

# 查看后端日志
docker compose logs -f app
```

---

## 🎯 仅重建前端（翻译修复）

如果只需要应用翻译修复，只重建前端即可：

```bash
# 停止前端
docker compose stop frontend

# 重建前端
docker compose build frontend --no-cache

# 启动前端
docker compose up -d frontend

# 查看日志
docker compose logs -f frontend
```

---

## 📊 验证翻译修复

### 1. 访问管理后台

```bash
# 前端地址
open http://localhost:5173

# 或直接访问管理后台
open http://localhost:5173/admin
```

### 2. 检查翻译

访问以下页面确认翻译正确显示：

- ✅ 控制台概览: http://localhost:5173/admin/console
- ✅ 计费管理: http://localhost:5173/admin/billing
- ✅ 权限配置: http://localhost:5173/admin/permissions
- ✅ 配额管理: http://localhost:5173/admin/quotas

### 3. 测试语言切换

1. 在页面右上角找到语言切换器
2. 切换到英文 (EN)
3. 验证所有文本正确翻译
4. 切换回中文 (ZH)
5. 验证所有文本正确翻译

### 4. 检查浏览器控制台

打开浏览器开发者工具 (F12)，检查控制台：
- ✅ 无 i18n 警告
- ✅ 无翻译键缺失错误
- ✅ 无原始翻译键显示

---

## 🔍 故障排除

### 问题 1: Docker 命令未找到

**错误**: `command not found: docker`

**解决方案**:
1. 安装 Docker Desktop
2. 启动 Docker Desktop 应用程序
3. 重新打开终端

### 问题 2: Docker 未运行

**错误**: `Cannot connect to the Docker daemon`

**解决方案**:
1. 启动 Docker Desktop 应用程序
2. 等待 Docker 完全启动（菜单栏图标不再旋转）
3. 重试命令

### 问题 3: 端口已被占用

**错误**: `port is already allocated`

**解决方案**:
```bash
# 查看占用端口的进程
lsof -i :5173  # 前端端口
lsof -i :8000  # 后端端口

# 停止占用端口的进程
kill -9 <PID>

# 或者修改 docker-compose.yml 中的端口映射
```

### 问题 4: 容器启动失败

**解决方案**:
```bash
# 查看详细日志
docker compose logs frontend
docker compose logs app

# 重新构建（清除缓存）
docker compose build --no-cache

# 清理并重新启动
docker compose down -v
docker compose up -d
```

### 问题 5: 翻译未更新

**解决方案**:
```bash
# 确保使用 --no-cache 重建
docker compose build frontend --no-cache

# 清除浏览器缓存
# Chrome/Edge: Ctrl+Shift+Delete (Windows) 或 Cmd+Shift+Delete (Mac)
# 选择"缓存的图片和文件"
# 清除数据

# 硬刷新页面
# Ctrl+Shift+R (Windows) 或 Cmd+Shift+R (Mac)
```

---

## 📝 常用命令

### 查看服务状态
```bash
docker compose ps
```

### 查看日志
```bash
# 所有服务
docker compose logs -f

# 特定服务
docker compose logs -f frontend
docker compose logs -f app

# 最近 100 行
docker compose logs --tail=100 frontend
```

### 重启服务
```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart frontend
docker compose restart app
```

### 停止服务
```bash
# 停止所有服务
docker compose stop

# 停止特定服务
docker compose stop frontend
docker compose stop app
```

### 完全清理
```bash
# 停止并删除容器、网络
docker compose down

# 停止并删除容器、网络、卷
docker compose down -v

# 删除所有未使用的镜像
docker image prune -a
```

---

## 🎉 成功标志

重建成功后，你应该看到：

1. ✅ 所有容器状态为 "Up"
2. ✅ 前端可访问: http://localhost:5173
3. ✅ 后端可访问: http://localhost:8000
4. ✅ API 文档可访问: http://localhost:8000/docs
5. ✅ 管理后台所有页面翻译正确
6. ✅ 语言切换功能正常
7. ✅ 浏览器控制台无错误

---

## 📚 相关文档

- **翻译修复总结**: `ADMIN_TRANSLATION_FIX_FINAL_SUMMARY.md`
- **任务列表**: `.kiro/specs/admin-translation-fix/tasks.md`
- **Docker Compose 配置**: `docker-compose.yml`
- **前端 Dockerfile**: `frontend/Dockerfile`
- **后端 Dockerfile**: `Dockerfile`

---

## 💡 提示

1. **首次构建**: 首次构建可能需要 10-20 分钟，因为需要下载所有依赖
2. **增量构建**: 后续重建会快很多，因为 Docker 会使用缓存
3. **开发模式**: 如果频繁修改代码，考虑使用本地开发模式而不是 Docker
4. **资源使用**: Docker Desktop 会占用较多内存，建议分配至少 4GB RAM

---

**最后更新**: 2026-01-25  
**状态**: ✅ 所有翻译修复已完成，准备重建容器
