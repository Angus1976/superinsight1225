# Docker 重建和测试指南

**日期**: 2026-01-25  
**目的**: 重建容器并验证翻译修复

---

## 🚀 快速开始

### 步骤 1: 确保 Docker Desktop 运行

```bash
# 检查 Docker 是否运行
/Applications/Docker.app/Contents/Resources/bin/docker info
```

如果显示错误，请：
1. 打开 Finder
2. 进入 Applications 文件夹
3. 双击 Docker.app
4. 等待菜单栏出现 Docker 图标

### 步骤 2: 执行重建脚本

```bash
./rebuild-containers.sh
```

脚本会自动：
- ✅ 检查 Docker 安装和运行状态
- 🛑 停止现有容器
- 🔨 重建前端容器（包含翻译修复）
- 🔨 重建后端容器
- 🚀 启动所有服务
- 📊 显示服务状态和日志

预计时间：5-10 分钟（首次构建可能需要更长时间）

---

## ✅ 验证翻译修复

### 1. 访问管理后台

打开浏览器访问：http://localhost:5173/admin

### 2. 测试所有页面

依次访问并检查翻译：

- [ ] **控制台概览** - http://localhost:5173/admin/console
  - 检查所有统计卡片
  - 检查图表标题和标签
  - 检查按钮和操作文本

- [ ] **计费管理** - http://localhost:5173/admin/billing
  - 检查汇总数据（月收入、已支付、待支付、逾期）
  - 检查表格列标题
  - 检查筛选器和搜索框

- [ ] **权限配置** - http://localhost:5173/admin/permissions
  - 检查权限列表
  - 检查角色配置
  - 检查操作按钮

- [ ] **配额管理** - http://localhost:5173/admin/quotas
  - 检查配额列表
  - 检查使用情况
  - 检查限制设置

- [ ] **租户管理** - http://localhost:5173/admin/tenants
  - 检查租户列表
  - 检查状态标签
  - 检查操作菜单

### 3. 测试语言切换

1. 在页面右上角找到语言切换器
2. 点击切换到 **English (EN)**
3. 验证所有文本正确翻译为英文
4. 点击切换回 **中文 (ZH)**
5. 验证所有文本正确翻译为中文

### 4. 检查浏览器控制台

1. 按 F12 打开开发者工具
2. 切换到 Console 标签
3. 刷新页面
4. 验证：
   - ✅ 无 i18n 相关警告
   - ✅ 无 "Missing translation" 错误
   - ✅ 无原始翻译键（如 "admin.console.title"）显示

---

## 🔍 故障排除

### 问题 1: Docker Desktop 未运行

**症状**: 脚本显示 "Docker Desktop 未运行"

**解决方案**:
```bash
# 启动 Docker Desktop
open -a Docker

# 等待 30 秒让 Docker 完全启动
sleep 30

# 重新运行脚本
./rebuild-containers.sh
```

### 问题 2: 端口被占用

**症状**: 错误信息包含 "port is already allocated"

**解决方案**:
```bash
# 查看占用端口的进程
lsof -i :5173  # 前端
lsof -i :8000  # 后端

# 停止占用端口的进程
kill -9 <PID>

# 或者停止所有 Docker 容器
/Applications/Docker.app/Contents/Resources/bin/docker compose down

# 重新运行脚本
./rebuild-containers.sh
```

### 问题 3: 构建失败

**症状**: 构建过程中出现错误

**解决方案**:
```bash
# 完全清理并重建
/Applications/Docker.app/Contents/Resources/bin/docker compose down -v
/Applications/Docker.app/Contents/Resources/bin/docker system prune -f

# 重新运行脚本
./rebuild-containers.sh
```

### 问题 4: 翻译未更新

**症状**: 页面仍显示旧的翻译或原始键

**解决方案**:
```bash
# 1. 清除浏览器缓存
# Chrome/Edge: Cmd+Shift+Delete
# 选择 "缓存的图片和文件"

# 2. 硬刷新页面
# Cmd+Shift+R

# 3. 如果仍未更新，重建前端容器
/Applications/Docker.app/Contents/Resources/bin/docker compose stop frontend
/Applications/Docker.app/Contents/Resources/bin/docker compose build frontend --no-cache
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d frontend
```

### 问题 5: 服务启动慢

**症状**: 服务启动时间超过 1 分钟

**解决方案**:
```bash
# 查看详细日志
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f

# 等待所有服务完全启动
# 前端通常需要 30-60 秒
# 后端通常需要 20-40 秒
```

---

## 📊 验证清单

完成以下所有项目后，翻译修复验证完成：

### 功能验证
- [ ] Docker Desktop 正在运行
- [ ] 所有容器状态为 "Up"
- [ ] 前端可访问 (http://localhost:5173)
- [ ] 后端可访问 (http://localhost:8000)
- [ ] 管理后台可访问 (http://localhost:5173/admin)

### 翻译验证
- [ ] 控制台页面中文翻译正确
- [ ] 控制台页面英文翻译正确
- [ ] 计费页面中文翻译正确
- [ ] 计费页面英文翻译正确
- [ ] 权限页面中文翻译正确
- [ ] 权限页面英文翻译正确
- [ ] 配额页面中文翻译正确
- [ ] 配额页面英文翻译正确
- [ ] 租户页面中文翻译正确
- [ ] 租户页面英文翻译正确

### 语言切换验证
- [ ] 可以从中文切换到英文
- [ ] 可以从英文切换回中文
- [ ] 切换后所有文本正确更新
- [ ] 刷新页面后语言设置保持

### 控制台验证
- [ ] 浏览器控制台无 i18n 警告
- [ ] 浏览器控制台无翻译错误
- [ ] 页面无原始翻译键显示
- [ ] 所有 UI 元素正确翻译

---

## 📝 常用命令

### 查看服务状态
```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose ps
```

### 查看实时日志
```bash
# 所有服务
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f

# 仅前端
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f frontend

# 仅后端
/Applications/Docker.app/Contents/Resources/bin/docker compose logs -f app
```

### 重启服务
```bash
# 重启前端
/Applications/Docker.app/Contents/Resources/bin/docker compose restart frontend

# 重启后端
/Applications/Docker.app/Contents/Resources/bin/docker compose restart app
```

### 停止服务
```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose down
```

### 查看容器资源使用
```bash
/Applications/Docker.app/Contents/Resources/bin/docker stats
```

---

## 🎯 成功标志

当你看到以下所有内容时，表示重建和验证成功：

1. ✅ 脚本执行无错误
2. ✅ 所有容器状态显示 "Up"
3. ✅ 前端日志显示 "ready in XXXms"
4. ✅ 后端日志显示 "Application startup complete"
5. ✅ 管理后台所有页面可访问
6. ✅ 所有翻译正确显示
7. ✅ 语言切换功能正常
8. ✅ 浏览器控制台无错误

---

## 📚 相关文档

- **重建脚本**: `rebuild-containers.sh`
- **详细指南**: `DOCKER_REBUILD_GUIDE.md`
- **翻译修复总结**: `ADMIN_TRANSLATION_FIX_FINAL_SUMMARY.md`
- **任务列表**: `.kiro/specs/admin-translation-fix/tasks.md`

---

**准备好了吗？执行以下命令开始：**

```bash
./rebuild-containers.sh
```

**预计时间**: 5-10 分钟  
**下一步**: 验证翻译修复（见上方清单）
