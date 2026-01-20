# SuperInsight 本地调试快速参考

## 🚀 快速启动（3 步）

```bash
# 1. 启动所有服务
./start-superinsight.sh

# 2. 生成演示数据
docker compose exec superinsight-api python scripts/seed_demo_data.py

# 3. 运行测试
bash scripts/test_all_roles.sh
```

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **API 文档** | http://localhost:8000/docs | Swagger UI |
| **API 健康检查** | http://localhost:8000/health | 服务状态 |
| **Label Studio** | http://localhost:8080 | 标注平台 |
| **Neo4j 浏览器** | http://localhost:7474 | 知识图谱 |
| **Prometheus** | http://localhost:9090 | 监控指标 |

## 👤 测试账号

```
用户名: admin              密码: admin123
用户名: business_expert    密码: business123
用户名: tech_expert        密码: tech123
用户名: annotator1         密码: annotator123
用户名: annotator2         密码: annotator123
用户名: reviewer           密码: reviewer123
```

## 📝 常用命令

### 服务管理

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 查看服务状态
docker compose ps

# 查看实时日志
docker compose logs -f superinsight-api

# 重启特定服务
docker compose restart superinsight-api
```

### 数据库操作

```bash
# 进入 PostgreSQL
docker compose exec postgres psql -U superinsight -d superinsight

# 查看所有表
\dt

# 查看用户表
SELECT * FROM users;

# 查看项目表
SELECT * FROM projects;

# 退出
\q
```

### 数据管理

```bash
# 生成演示数据
docker compose exec superinsight-api python scripts/seed_demo_data.py

# 重置数据库（删除所有数据）
docker compose down -v
docker compose up -d
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

## 🧪 API 测试

### 获取 Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 使用 Token 访问 API

```bash
TOKEN="your_token_here"

# 获取用户信息
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"

# 获取项目列表
curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN"

# 获取任务列表
curl -X GET http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN"
```

## 🏷️ Label Studio 测试

### 登录信息

```
用户名: admin@superinsight.com
密码: 见 .env 文件中的 LABEL_STUDIO_PASSWORD
```

### 创建项目步骤

1. 访问 http://localhost:8080
2. 点击 "Create" 按钮
3. 输入项目名称
4. 选择标注类型（Classification、NER 等）
5. 配置标签
6. 导入数据

### 导入示例数据

```bash
# 创建 CSV 文件
cat > sample_data.csv << 'EOF'
text
iPhone 13 Pro Max 256GB 深空黑色
Adidas 运动鞋 男款 黑色
有机咖啡豆 500g 中度烘焙
宜家 BILLY 书架 白色
小米 10000mAh 移动电源
EOF

# 在 Label Studio UI 中导入
# 1. 进入项目
# 2. 点击 "Import" 按钮
# 3. 选择 CSV 文件
```

## 🔍 调试技巧

### 查看 API 日志

```bash
# 实时查看
docker compose logs -f superinsight-api

# 查看最近 100 行
docker compose logs --tail=100 superinsight-api

# 查看特定时间范围
docker compose logs --since 10m superinsight-api
```

### 查看数据库日志

```bash
docker compose logs -f postgres
```

### 查看 Label Studio 日志

```bash
docker compose logs -f label-studio
```

### 进入容器调试

```bash
# 进入 API 容器
docker compose exec superinsight-api bash

# 进入数据库容器
docker compose exec postgres bash

# 进入 Label Studio 容器
docker compose exec label-studio bash
```

## 🐛 常见问题

### 问题：API 无法连接

```bash
# 检查 API 是否运行
docker compose ps superinsight-api

# 查看 API 日志
docker compose logs superinsight-api

# 检查端口是否被占用
lsof -i :8000

# 重启 API
docker compose restart superinsight-api
```

### 问题：数据库连接失败

```bash
# 检查数据库是否运行
docker compose ps postgres

# 检查数据库日志
docker compose logs postgres

# 测试数据库连接
docker compose exec postgres pg_isready -U superinsight

# 重启数据库
docker compose restart postgres
```

### 问题：Label Studio 无法访问

```bash
# 检查 Label Studio 是否运行
docker compose ps label-studio

# 查看 Label Studio 日志
docker compose logs label-studio

# 检查健康状态
curl http://localhost:8080/health

# 重启 Label Studio
docker compose restart label-studio
```

### 问题：内存不足

```bash
# 查看资源使用
docker stats

# 清理未使用的资源
docker system prune -a

# 限制容器内存（编辑 docker-compose.yml）
```

## 📊 性能监控

### 查看容器资源使用

```bash
# 实时监控
docker stats

# 查看特定容器
docker stats superinsight-api
```

## 🔐 安全测试

### 测试认证

```bash
# 无效的用户名
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "invalid", "password": "password"}'

# 无效的密码
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "wrong"}'

# 无效的 Token
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer invalid_token"
```

### 测试权限控制

```bash
# 以 annotator 身份尝试创建用户（应该被拒绝）
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "annotator1", "password": "annotator123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "email": "test@example.com", "password": "test123"}'
```

## 📚 文档链接

- [完整调试指南](./LOCAL_DEBUG_GUIDE.md)
- [快速启动指南](./QUICK_START.md)
- [API 文档](http://localhost:8000/docs)
- [项目 README](./README.md)

## 💡 提示

1. **使用 Swagger UI 测试 API**：访问 http://localhost:8000/docs，点击 "Authorize" 按钮登录
2. **查看实时日志**：使用 `docker compose logs -f` 查看实时日志
3. **重置数据**：使用 `docker compose down -v` 删除所有数据卷
4. **性能测试**：使用 `docker stats` 监控容器资源使用
5. **数据库查询**：使用 `docker compose exec postgres psql` 直接查询数据库

## 🆘 获取帮助

1. 查看日志：`docker compose logs -f`
2. 检查服务状态：`docker compose ps`
3. 查看健康检查：`curl http://localhost:8000/health`
4. 查看 API 文档：http://localhost:8000/docs
5. 提交 Issue：[GitHub Issues](https://github.com/Angus1976/superinsight1225/issues)

---

**最后更新**: 2026-01-20  
**版本**: 1.0
