# 🚀 SuperInsight 全栈应用 - 快速启动指南

**状态**: ✅ 所有服务已启动并运行

---

## 🎯 立即访问

### 前端应用
👉 **http://localhost:5173/login**

### 后端 API
👉 **http://localhost:8000**

### API 文档
👉 **http://localhost:8000/docs**

---

## 🔐 登录凭证

选择任意一个用户登录：

```
用户名: admin_user
密码: Admin@123456
```

或其他用户：
- `business_expert` / `Business@123456`
- `technical_expert` / `Technical@123456`
- `contractor` / `Contractor@123456`
- `viewer` / `Viewer@123456`

---

## 📊 其他服务

| 服务 | URL |
|------|-----|
| Label Studio | http://localhost:8080 |
| Neo4j | http://localhost:7474 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## 🛠️ 常用命令

### 查看所有容器状态
```bash
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
docker compose -f docker-compose.fullstack.yml ps
```

### 查看后端日志
```bash
docker compose -f docker-compose.fullstack.yml logs -f superinsight-api
```

### 查看前端日志
```bash
docker compose -f docker-compose.fullstack.yml logs -f superinsight-frontend
```

### 重启所有服务
```bash
docker compose -f docker-compose.fullstack.yml restart
```

### 停止所有服务
```bash
docker compose -f docker-compose.fullstack.yml stop
```

---

## ✅ 验证清单

- [ ] 访问 http://localhost:5173/login
- [ ] 使用 admin_user 登录
- [ ] 看到仪表板
- [ ] 访问 http://localhost:8000/health 看到 `{"status":"healthy"}`
- [ ] 访问 http://localhost:8080 看到 Label Studio
- [ ] 访问 http://localhost:7474 看到 Neo4j

---

## 🎉 完成！

所有服务已启动并运行。开始使用 SuperInsight 吧！

---

**最后更新**: 2026-01-09  
**版本**: 1.0
