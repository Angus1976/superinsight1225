# 故障排除指南

**最后更新**: 2026-01-04 21:05:35 UTC

---

## 🔍 常见问题与解决方案

### 问题 1: 前端页面仍然无法加载

#### 症状
- 访问 http://localhost:3000/login 时页面空白
- 浏览器控制台显示 JavaScript 错误

#### 解决步骤

**步骤 1: 清理浏览器缓存**
1. 打开浏览器开发者工具 (F12)
2. 右键点击刷新按钮
3. 选择 "清空缓存并硬性重新加载"
4. 等待页面重新加载

**步骤 2: 检查前端服务**
```bash
# 检查前端是否运行
curl http://localhost:3000

# 如果无响应，重启前端
pkill -f "npm run dev"
cd frontend
npm run dev
```

**步骤 3: 完全重新安装**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
npm run dev
```

**步骤 4: 检查 npm 版本**
```bash
npm --version  # 应该是 10.x 或更高
node --version # 应该是 18.x 或更高
```

---

### 问题 2: 登录失败

#### 症状
- 输入账号密码后点击登录无反应
- 浏览器控制台显示网络错误

#### 解决步骤

**步骤 1: 检查后端服务**
```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 如果无响应，重启后端
pkill -f simple_app.py
python3 simple_app.py
```

**步骤 2: 验证账号信息**
```bash
# 测试登录 API
curl -X POST http://localhost:8000/api/security/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_test","password":"admin123"}'
```

**步骤 3: 检查网络连接**
- 确保后端运行在 http://localhost:8000
- 确保前端运行在 http://localhost:3000
- 检查防火墙设置

---

### 问题 3: 后端无响应

#### 症状
- 访问 http://localhost:8000/health 无响应
- 后端进程已停止

#### 解决步骤

**步骤 1: 检查进程**
```bash
# 查看是否有 Python 进程运行
ps aux | grep simple_app.py

# 如果没有，启动后端
python3 simple_app.py
```

**步骤 2: 检查端口占用**
```bash
# 检查 8000 端口是否被占用
lsof -i :8000

# 如果被占用，杀死进程
kill -9 <PID>

# 重新启动后端
python3 simple_app.py
```

**步骤 3: 检查依赖**
```bash
# 检查 Python 依赖是否安装
pip list | grep fastapi

# 如果缺少依赖，安装
pip install -r requirements.txt
```

---

### 问题 4: 数据库连接失败

#### 症状
- 后端启动时显示数据库连接错误
- 健康检查显示数据库不健康

#### 解决步骤

**步骤 1: 检查 PostgreSQL**
```bash
# 检查 PostgreSQL 是否运行
# macOS 使用 Homebrew
brew services list | grep postgres

# 如果未运行，启动
brew services start postgresql
```

**步骤 2: 检查连接字符串**
```bash
# 检查 .env 文件中的数据库配置
cat .env | grep DATABASE

# 确保连接字符串正确
# 格式: postgresql://user:password@localhost:5432/dbname
```

**步骤 3: 重启数据库**
```bash
# macOS
brew services restart postgresql

# 或使用 Docker
docker-compose restart postgres
```

---

### 问题 5: 语言切换不工作

#### 症状
- 切换语言后界面文本不更新
- 语言设置未保存

#### 解决步骤

**步骤 1: 检查 i18n 端点**
```bash
# 获取当前语言设置
curl http://localhost:8000/api/settings/language

# 设置语言为英文
curl -X POST http://localhost:8000/api/settings/language?language=en

# 获取翻译
curl http://localhost:8000/api/i18n/translations
```

**步骤 2: 清理浏览器存储**
1. 打开浏览器开发者工具 (F12)
2. 进入 Application 标签
3. 清理 LocalStorage 和 SessionStorage
4. 刷新页面

**步骤 3: 检查前端代码**
```bash
# 检查 i18n 配置
cat frontend/src/i18n/config.ts

# 确保语言切换逻辑正确
```

---

### 问题 6: 应用加载缓慢

#### 症状
- 页面加载时间超过 5 秒
- 浏览器显示加载中

#### 解决步骤

**步骤 1: 检查网络**
1. 打开浏览器开发者工具 (F12)
2. 进入 Network 标签
3. 刷新页面
4. 查看哪些资源加载缓慢

**步骤 2: 检查系统资源**
```bash
# 检查 CPU 使用率
top -l 1 | grep "CPU usage"

# 检查内存使用率
vm_stat

# 如果资源不足，关闭其他应用
```

**步骤 3: 清理缓存**
```bash
# 清理 npm 缓存
npm cache clean --force

# 清理 Vite 缓存
rm -rf frontend/.vite

# 重新启动前端
cd frontend
npm run dev
```

---

### 问题 7: 权限错误

#### 症状
- 某些功能无法访问
- 显示 "权限不足" 错误

#### 解决步骤

**步骤 1: 检查用户角色**
```bash
# 获取用户列表
curl http://localhost:8000/api/security/users

# 确保使用的账号有正确的角色
```

**步骤 2: 使用管理员账号**
```
用户名: admin_test
密码: admin123
角色: ADMIN (拥有所有权限)
```

**步骤 3: 检查权限配置**
```bash
# 查看后端权限配置
cat src/api/admin.py | grep -A 5 "permission"
```

---

## 🔧 高级故障排除

### 查看后端日志
```bash
# 查看实时日志
tail -f backend.log

# 查看最后 100 行
tail -100 backend.log

# 搜索错误
grep "ERROR" backend.log
```

### 查看前端日志
```bash
# 打开浏览器开发者工具 (F12)
# 进入 Console 标签
# 查看所有错误和警告
```

### 重置整个系统
```bash
# 停止所有服务
pkill -f "npm run dev"
pkill -f simple_app.py

# 清理前端
cd frontend
rm -rf node_modules package-lock.json .vite

# 重新安装和启动
npm install --legacy-peer-deps
npm run dev

# 在另一个终端启动后端
python3 simple_app.py
```

---

## 📞 获取帮助

### 检查清单
- [ ] 后端运行在 http://localhost:8000
- [ ] 前端运行在 http://localhost:3000
- [ ] 数据库已连接
- [ ] 浏览器缓存已清理
- [ ] npm 版本 >= 10.x
- [ ] Node.js 版本 >= 18.x

### 常用命令
```bash
# 检查后端
curl http://localhost:8000/health

# 检查前端
curl http://localhost:3000

# 检查数据库
psql -U postgres -d superinsight -c "SELECT 1"

# 查看进程
ps aux | grep -E "simple_app|npm run dev"

# 查看端口占用
lsof -i :8000
lsof -i :3000
```

---

## 🎯 快速修复

### 最常见的解决方案
```bash
# 1. 清理浏览器缓存 (F12 -> 右键刷新 -> 清空缓存并硬性重新加载)

# 2. 重启前端
pkill -f "npm run dev"
cd frontend && npm run dev

# 3. 重启后端
pkill -f simple_app.py
python3 simple_app.py

# 4. 完全重新安装前端
cd frontend
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
npm run dev
```

---

**最后更新**: 2026-01-04 21:05:35 UTC  
**状态**: ✅ 所有问题已解决
