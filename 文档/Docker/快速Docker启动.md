# 🚀 Docker 全栈快速启动

**最快的启动方式 - 只需 3 步！**

---

## ⚡ 3 步快速启动

### 步骤 1️⃣: 运行启动脚本
```bash
chmod +x start-fullstack.sh
./start-fullstack.sh
```

**脚本会自动**:
- ✅ 检查 Docker 状态
- ✅ 停止旧容器
- ✅ 构建镜像
- ✅ 启动所有服务
- ✅ 创建测试用户
- ✅ 验证服务

### 步骤 2️⃣: 等待完成
脚本运行约 2-3 分钟，显示所有服务就绪

### 步骤 3️⃣: 打开浏览器
访问 http://localhost:5173/login

---

## 🔐 登录凭证

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 👨‍💼 管理员 | `admin_user` | `Admin@123456` |
| 📊 业务专家 | `business_expert` | `Business@123456` |
| 🔧 技术专家 | `technical_expert` | `Technical@123456` |
| 👷 承包商 | `contractor` | `Contractor@123456` |
| 👁️ 查看者 | `viewer` | `Viewer@123456` |

---

## 🔗 所有服务地址

| 服务 | URL |
|------|-----|
| 🌐 **前端** | http://localhost:5173 |
| 🔌 **后端 API** | http://localhost:8000 |
| 📖 **API 文档** | http://localhost:8000/docs |
| 🏷️ **Label Studio** | http://localhost:8080 |
| 📊 **Neo4j** | http://localhost:7474 |
| 🗄️ **PostgreSQL** | localhost:5432 |
| 💾 **Redis** | localhost:6379 |

---

## 📋 常用命令

### 查看状态
```bash
# 查看所有容器
docker-compose -f docker-compose.fullstack.yml ps

# 查看日志
docker-compose -f docker-compose.fullstack.yml logs -f
```

### 进入容器
```bash
# 进入后端
docker-compose -f docker-compose.fullstack.yml exec superinsight-api bash

# 进入前端
docker-compose -f docker-compose.fullstack.yml exec superinsight-frontend sh
```

### 重启服务
```bash
# 重启所有
docker-compose -f docker-compose.fullstack.yml restart

# 重新构建
docker-compose -f docker-compose.fullstack.yml up -d --build
```

### 停止服务
```bash
# 停止
docker-compose -f docker-compose.fullstack.yml stop

# 停止并删除
docker-compose -f docker-compose.fullstack.yml down -v
```

---

## ❌ 如果出现问题

### 后端无法启动
```bash
docker-compose -f docker-compose.fullstack.yml logs superinsight-api
```

### 前端无法启动
```bash
docker-compose -f docker-compose.fullstack.yml logs superinsight-frontend
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

- [ ] 脚本运行完成
- [ ] 所有 6 个容器都在运行
- [ ] 可以打开 http://localhost:5173/login
- [ ] 可以用 admin_user 登录
- [ ] 可以看到仪表板

---

## 📚 详细文档

- 📖 [完整设置指南](DOCKER_FULLSTACK_COMPLETE_SETUP.md)
- 🔍 [问题分析](DOCKER_FULLSTACK_ANALYSIS.md)
- 🛠️ [启动指南](DOCKER_FULLSTACK_STARTUP.md)
- 🧪 [登录测试](LOGIN_TESTING_GUIDE.md)

---

**就这么简单！🎉**

