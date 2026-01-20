# SuperInsight 本地调试环境设置完成

**完成时间**: 2026-01-20  
**状态**: ✅ 完成  
**版本**: 1.0

---

## 📋 已完成的工作

### 1. ✅ 创建了完整的本地调试指南

**文件**: `LOCAL_DEBUG_GUIDE.md`

包含以下内容：
- 快速启动步骤（3 步启动）
- 模拟数据设置指南
- 多角色账号测试说明
- Label Studio 集成测试步骤
- 完整的功能测试清单
- 常见问题解答
- 性能测试指南

### 2. ✅ 创建了模拟数据生成脚本

**文件**: `scripts/seed_demo_data.py`

功能：
- 自动创建 6 个测试用户（不同角色）
- 创建 3 个演示项目
- 创建 3 个数据集
- 创建 3 个标注任务
- 创建角色和权限配置

**使用方法**：
```bash
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

### 3. ✅ 创建了多角色测试脚本

**文件**: `scripts/test_all_roles.sh`

功能：
- 检查所有服务状态
- 测试所有用户的登录
- 测试 API 端点访问
- 测试权限控制
- 测试标注工作流
- 测试 Label Studio 集成
- 生成测试报告

**使用方法**：
```bash
bash scripts/test_all_roles.sh
```

### 4. ✅ 创建了快速参考指南

**文件**: `DEBUG_QUICK_REFERENCE.md`

包含：
- 快速启动命令（3 步）
- 所有访问地址
- 测试账号信息
- 常用命令速查
- API 测试示例
- Label Studio 测试步骤
- 调试技巧
- 常见问题解决方案

---

## 🚀 快速开始（3 步）

### 第一步：启动所有服务

```bash
./start-superinsight.sh
```

或手动启动：
```bash
docker compose up -d
```

等待所有服务启动完成（约 30-60 秒）。

### 第二步：生成演示数据

```bash
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

这将创建：
- 6 个测试用户（不同角色）
- 3 个演示项目
- 3 个数据集
- 3 个标注任务

### 第三步：运行测试

```bash
bash scripts/test_all_roles.sh
```

这将测试：
- 所有服务状态
- 所有用户的登录
- API 端点访问
- 权限控制
- 标注工作流
- Label Studio 集成

---

## 👤 测试账号

| 用户名 | 密码 | 角色 | 邮箱 |
|--------|------|------|------|
| `admin` | `admin123` | 系统管理员 | admin@superinsight.com |
| `business_expert` | `business123` | 业务专家 | business@superinsight.com |
| `tech_expert` | `tech123` | 技术专家 | tech@superinsight.com |
| `annotator1` | `annotator123` | 标注员 | annotator1@superinsight.com |
| `annotator2` | `annotator123` | 标注员 | annotator2@superinsight.com |
| `reviewer` | `reviewer123` | 质量审核员 | reviewer@superinsight.com |

---

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **API 文档** | http://localhost:8000/docs | Swagger UI，可直接测试 API |
| **API 健康检查** | http://localhost:8000/health | 服务状态检查 |
| **Label Studio** | http://localhost:8080 | 数据标注平台 |
| **Neo4j 浏览器** | http://localhost:7474 | 知识图谱浏览器 |
| **Prometheus** | http://localhost:9090 | 监控指标（可选） |

---

## 📝 测试场景

### 场景 1：系统管理员（Admin）

**账号**: admin / admin123

**可以做的事**：
1. 创建和管理用户
2. 创建和管理项目
3. 创建和管理标注任务
4. 查看系统监控
5. 管理系统设置

**测试步骤**：
```bash
# 1. 登录 API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 2. 使用 Swagger UI 测试
# 访问 http://localhost:8000/docs
# 点击 "Authorize" 按钮
# 输入用户名和密码
```

### 场景 2：业务专家（Business Expert）

**账号**: business_expert / business123

**可以做的事**：
1. 创建项目
2. 创建标注任务
3. 查看数据集
4. 分配任务给标注员

**测试步骤**：
```bash
# 1. 获取项目列表
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "business_expert", "password": "business123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN"

# 2. 获取任务列表
curl -X GET http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN"
```

### 场景 3：标注员（Annotator）

**账号**: annotator1 / annotator123

**可以做的事**：
1. 查看分配的任务
2. 执行标注操作
3. 提交标注结果
4. 查看标注历史

**测试步骤**：
```bash
# 1. 获取分配的任务
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "annotator1", "password": "annotator123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -X GET http://localhost:8000/api/v1/tasks/assigned \
  -H "Authorization: Bearer $TOKEN"

# 2. 获取待标注的数据
curl -X GET http://localhost:8000/api/v1/tasks/1/items \
  -H "Authorization: Bearer $TOKEN"

# 3. 提交标注结果
curl -X POST http://localhost:8000/api/v1/annotations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "1",
    "item_id": "item_001",
    "label": "电子产品",
    "confidence": 0.95
  }'
```

### 场景 4：质量审核员（Reviewer）

**账号**: reviewer / reviewer123

**可以做的事**：
1. 查看待审核的标注
2. 审核标注结果
3. 生成质量报告
4. 识别低质量标注

**测试步骤**：
```bash
# 1. 获取待审核的标注
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "reviewer", "password": "reviewer123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -X GET http://localhost:8000/api/v1/annotations/pending-review \
  -H "Authorization: Bearer $TOKEN"

# 2. 审核标注结果
curl -X POST http://localhost:8000/api/v1/annotations/1/review \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "comment": "标注正确"
  }'
```

### 场景 5：Label Studio 标注工作流

**步骤**：
1. 访问 http://localhost:8080
2. 使用 admin@superinsight.com / 密码登录
3. 创建新项目
4. 导入示例数据
5. 执行标注操作
6. 导出标注结果

---

## 🧪 功能测试清单

### 认证和授权
- [ ] 使用不同角色账号登录
- [ ] 验证 JWT Token 生成
- [ ] 测试权限控制
- [ ] 测试 Token 过期
- [ ] 测试登出功能

### 项目管理
- [ ] 创建新项目
- [ ] 编辑项目信息
- [ ] 删除项目
- [ ] 查看项目列表
- [ ] 分配项目成员

### 数据集管理
- [ ] 上传数据集
- [ ] 查看数据集列表
- [ ] 删除数据集
- [ ] 导出数据集

### 标注任务
- [ ] 创建标注任务
- [ ] 分配任务给标注员
- [ ] 查看任务进度
- [ ] 完成任务

### Label Studio 集成
- [ ] 创建 Label Studio 项目
- [ ] 导入数据
- [ ] 执行标注
- [ ] 导出结果
- [ ] 同步数据

### 质量管理
- [ ] 查看质量指标
- [ ] 生成质量报告
- [ ] 识别低质量标注
- [ ] 触发质量告警

### 计费和统计
- [ ] 查看工作时间统计
- [ ] 查看标注数量统计
- [ ] 生成计费报告
- [ ] 导出统计数据

---

## 🔧 常用命令

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

# 重置数据库
docker compose down -v
docker compose up -d
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

---

## 📚 文档结构

```
.
├── LOCAL_DEBUG_GUIDE.md              # 完整的本地调试指南
├── DEBUG_QUICK_REFERENCE.md          # 快速参考指南
├── LOCAL_DEBUG_SETUP_SUMMARY.md      # 本文件
├── scripts/
│   ├── seed_demo_data.py             # 模拟数据生成脚本
│   └── test_all_roles.sh             # 多角色测试脚本
├── QUICK_START.md                    # 快速启动指南
├── docker-compose.yml                # Docker 配置
└── .env.example                      # 环境变量示例
```

---

## 🎯 下一步

### 立即开始

1. **启动环境**
   ```bash
   ./start-superinsight.sh
   ```

2. **生成演示数据**
   ```bash
   docker compose exec superinsight-api python scripts/seed_demo_data.py
   ```

3. **运行测试**
   ```bash
   bash scripts/test_all_roles.sh
   ```

4. **访问应用**
   - API 文档: http://localhost:8000/docs
   - Label Studio: http://localhost:8080

### 深入学习

1. 阅读 [LOCAL_DEBUG_GUIDE.md](./LOCAL_DEBUG_GUIDE.md) 了解详细步骤
2. 查看 [DEBUG_QUICK_REFERENCE.md](./DEBUG_QUICK_REFERENCE.md) 快速查找命令
3. 使用 Swagger UI 测试 API
4. 在 Label Studio 中创建标注项目

### 常见任务

- **查看日志**: `docker compose logs -f superinsight-api`
- **进入数据库**: `docker compose exec postgres psql -U superinsight -d superinsight`
- **重置数据**: `docker compose down -v && docker compose up -d`
- **测试 API**: 访问 http://localhost:8000/docs

---

## 💡 关键特性

### 多角色支持
- ✅ 系统管理员（Admin）
- ✅ 业务专家（Business Expert）
- ✅ 技术专家（Tech Expert）
- ✅ 标注员（Annotator）
- ✅ 质量审核员（Reviewer）

### 完整的工作流
- ✅ 用户认证和授权
- ✅ 项目和数据集管理
- ✅ 标注任务分配
- ✅ Label Studio 集成
- ✅ 质量管理和审核
- ✅ 计费和统计

### 开发工具
- ✅ Swagger UI API 文档
- ✅ 实时日志查看
- ✅ 数据库直接访问
- ✅ 性能监控
- ✅ 自动化测试脚本

---

## 🆘 获取帮助

### 快速问题解答

**Q: 如何重置数据库？**
```bash
docker compose down -v
docker compose up -d
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

**Q: 如何查看 API 日志？**
```bash
docker compose logs -f superinsight-api
```

**Q: 如何连接到数据库？**
```bash
docker compose exec postgres psql -U superinsight -d superinsight
```

**Q: 如何测试不同角色的权限？**
```bash
bash scripts/test_all_roles.sh
```

### 详细文档

- [完整调试指南](./LOCAL_DEBUG_GUIDE.md)
- [快速参考指南](./DEBUG_QUICK_REFERENCE.md)
- [快速启动指南](./QUICK_START.md)
- [API 文档](http://localhost:8000/docs)

---

## 📊 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 8GB 可用内存
- 至少 20GB 可用磁盘空间

---

## ✅ 验证清单

- [x] 创建了完整的本地调试指南
- [x] 创建了模拟数据生成脚本
- [x] 创建了多角色测试脚本
- [x] 创建了快速参考指南
- [x] 创建了设置总结文档
- [x] 所有脚本都可执行
- [x] 文档结构清晰
- [x] 包含完整的测试场景
- [x] 包含常见问题解答
- [x] 包含快速启动步骤

---

## 📞 支持

如有问题，请：
1. 查看相关文档
2. 检查日志：`docker compose logs -f`
3. 运行测试脚本：`bash scripts/test_all_roles.sh`
4. 提交 Issue

---

**创建时间**: 2026-01-20  
**最后更新**: 2026-01-20  
**版本**: 1.0  
**状态**: ✅ 完成

