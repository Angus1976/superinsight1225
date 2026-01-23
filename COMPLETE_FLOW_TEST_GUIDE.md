# SuperInsight 完整流程测试指南

**版本**: 1.0  
**最后更新**: 2026-01-20  
**目的**: 验证数据已入库并测试完整的工作流

---

## 📋 目录

1. [快速开始](#快速开始)
2. [数据验证](#数据验证)
3. [完整工作流测试](#完整工作流测试)
4. [手动测试步骤](#手动测试步骤)
5. [常见问题](#常见问题)

---

## 🚀 快速开始

### 第一步：启动所有服务

```bash
# 启动所有服务
./start-superinsight.sh

# 或手动启动
docker compose up -d

# 等待所有服务启动完成（约 30-60 秒）
docker compose ps
```

### 第二步：生成演示数据

```bash
# 生成演示数据（创建用户、项目、任务等）
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

### 第三步：运行完整流程测试

```bash
# 运行完整的测试脚本
bash scripts/verify_and_test_complete_flow.sh
```

这个脚本会：
- ✅ 检查所有服务状态
- ✅ 验证数据库中的数据
- ✅ 测试用户登录
- ✅ 测试 API 端点
- ✅ 测试完整的标注工作流
- ✅ 测试权限控制
- ✅ 生成测试报告

---

## 📊 数据验证

### 验证数据库中的数据

```bash
# 进入数据库
docker compose exec postgres psql -U superinsight -d superinsight

# 查看用户表
SELECT username, email, role_id FROM users;

# 查看项目表
SELECT name, status FROM projects;

# 查看任务表
SELECT name, status, total_items, completed_items FROM annotation_tasks;

# 查看数据集表
SELECT name, size FROM datasets;

# 退出
\q
```

### 预期的数据

运行 `seed_demo_data.py` 后，应该有以下数据：

**用户（6 个）**：
- admin (系统管理员)
- business_expert (业务专家)
- tech_expert (技术专家)
- annotator1 (标注员)
- annotator2 (标注员)
- reviewer (质量审核员)

**项目（3 个）**：
- 电商商品分类
- 客服对话质量评估
- 医疗文本挖掘

**数据集（3 个）**：
- 商品标题数据集 v1
- 商品描述数据集 v1
- 客服对话数据集 v1

**任务（3 个）**：
- 商品分类标注 - 第一批
- 商品分类标注 - 第二批
- 客服对话质量评估

---

## 🔄 完整工作流测试

### 工作流概述

```
┌─────────────────────────────────────────────────────────┐
│                   完整的标注工作流                        │
└─────────────────────────────────────────────────────────┘

1. 业务专家创建项目
   ↓
2. 业务专家上传数据集
   ↓
3. 业务专家创建标注任务
   ↓
4. 业务专家分配任务给标注员
   ↓
5. 标注员查看分配的任务
   ↓
6. 标注员执行标注操作
   ↓
7. 质量审核员审核标注结果
   ↓
8. 生成质量报告
```

### 自动化测试

运行以下命令进行自动化测试：

```bash
bash scripts/verify_and_test_complete_flow.sh
```

这个脚本会自动执行所有测试步骤。

---

## 👥 手动测试步骤

### 场景 1：业务专家创建项目

**步骤**：

1. 获取 Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "business_expert", "password": "business123"}'
```

2. 创建新项目
```bash
TOKEN="your_token_here"
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "新项目 - '$(date +%s)'",
    "description": "测试项目"
  }'
```

3. 查看项目列表
```bash
curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN"
```

### 场景 2：标注员执行标注

**步骤**：

1. 获取 Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "annotator1", "password": "annotator123"}'
```

2. 查看分配的任务
```bash
TOKEN="your_token_here"
curl -X GET http://localhost:8000/api/v1/tasks/assigned \
  -H "Authorization: Bearer $TOKEN"
```

3. 获取待标注的数据
```bash
curl -X GET http://localhost:8000/api/v1/tasks/1/items \
  -H "Authorization: Bearer $TOKEN"
```

4. 提交标注结果
```bash
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

### 场景 3：质量审核员审核标注

**步骤**：

1. 获取 Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "reviewer", "password": "reviewer123"}'
```

2. 查看待审核的标注
```bash
TOKEN="your_token_here"
curl -X GET http://localhost:8000/api/v1/annotations/pending-review \
  -H "Authorization: Bearer $TOKEN"
```

3. 审核标注结果
```bash
curl -X POST http://localhost:8000/api/v1/annotations/1/review \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "comment": "标注正确"
  }'
```

### 场景 4：使用 Swagger UI 测试

1. 打开浏览器访问 http://localhost:8000/docs
2. 点击右上角 "Authorize" 按钮
3. 输入用户名和密码
4. 点击 "Authorize" 按钮
5. 现在可以直接在 Swagger UI 中测试所有 API 端点

---

## 🧪 测试检查清单

### 基础功能
- [ ] 所有服务都在运行
- [ ] API 可以访问
- [ ] 数据库可以连接
- [ ] 数据已成功入库

### 认证和授权
- [ ] 可以使用正确的凭证登录
- [ ] 无法使用错误的凭证登录
- [ ] 不同角色有不同的权限
- [ ] Token 可以正确验证

### 项目管理
- [ ] 可以创建项目
- [ ] 可以编辑项目
- [ ] 可以删除项目
- [ ] 可以查看项目列表

### 标注工作流
- [ ] 可以创建标注任务
- [ ] 可以分配任务给标注员
- [ ] 标注员可以查看分配的任务
- [ ] 标注员可以执行标注
- [ ] 可以查看标注进度

### 质量管理
- [ ] 可以查看待审核的标注
- [ ] 可以审核标注结果
- [ ] 可以生成质量报告

### 权限控制
- [ ] Admin 可以创建用户
- [ ] Annotator 无法创建用户
- [ ] 不同角色只能访问自己的资源

---

## 📊 数据库查询示例

### 查看所有用户

```sql
SELECT id, username, email, role_id FROM users;
```

### 查看所有项目

```sql
SELECT id, name, owner_id, status FROM projects;
```

### 查看所有任务

```sql
SELECT id, name, project_id, status, total_items, completed_items FROM annotation_tasks;
```

### 查看用户和项目的关系

```sql
SELECT u.username, p.name 
FROM users u 
JOIN projects p ON u.id = p.owner_id;
```

### 查看任务分配情况

```sql
SELECT t.name, u.username, t.status, t.completed_items, t.total_items
FROM annotation_tasks t
JOIN users u ON t.assigned_to_id = u.id;
```

### 统计标注进度

```sql
SELECT 
  t.name,
  t.total_items,
  t.completed_items,
  ROUND(100.0 * t.completed_items / t.total_items, 2) as progress_percentage
FROM annotation_tasks t;
```

---

## 🔍 故障排查

### 问题：数据库中没有数据

**症状**：运行查询时返回空结果

**解决方案**：
```bash
# 1. 检查数据库是否运行
docker compose ps postgres

# 2. 生成演示数据
docker compose exec superinsight-api python scripts/seed_demo_data.py

# 3. 验证数据
docker compose exec postgres psql -U superinsight -d superinsight -c "SELECT COUNT(*) FROM users;"
```

### 问题：API 无法连接

**症状**：curl 命令返回连接错误

**解决方案**：
```bash
# 1. 检查 API 是否运行
docker compose ps superinsight-api

# 2. 查看 API 日志
docker compose logs superinsight-api

# 3. 检查端口是否被占用
lsof -i :8000

# 4. 重启 API
docker compose restart superinsight-api
```

### 问题：登录失败

**症状**：登录返回错误

**解决方案**：
```bash
# 1. 检查用户是否存在
docker compose exec postgres psql -U superinsight -d superinsight -c "SELECT * FROM users WHERE username='admin';"

# 2. 检查密码是否正确
# 默认密码: admin123

# 3. 重新生成演示数据
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

---

## 📈 性能测试

### 负载测试

```bash
# 安装 locust
pip install locust

# 创建 locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class SuperInsightUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_projects(self):
        self.client.get("/api/v1/projects")
    
    @task
    def get_tasks(self):
        self.client.get("/api/v1/tasks")
EOF

# 运行负载测试
locust -f locustfile.py --host=http://localhost:8000
```

### 资源监控

```bash
# 实时监控容器资源使用
docker stats

# 查看特定容器的详细信息
docker stats superinsight-api
```

---

## 📚 常用命令

### 启动和停止

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 查看服务状态
docker compose ps

# 查看实时日志
docker compose logs -f superinsight-api
```

### 数据管理

```bash
# 生成演示数据
docker compose exec superinsight-api python scripts/seed_demo_data.py

# 重置数据库
docker compose down -v
docker compose up -d
docker compose exec superinsight-api python scripts/seed_demo_data.py

# 备份数据库
docker compose exec postgres pg_dump -U superinsight superinsight > backup.sql

# 恢复数据库
docker compose exec -T postgres psql -U superinsight superinsight < backup.sql
```

### 数据库操作

```bash
# 进入数据库
docker compose exec postgres psql -U superinsight -d superinsight

# 查看所有表
\dt

# 查看表结构
\d table_name

# 查询数据
SELECT * FROM users;

# 退出
\q
```

---

## 🎯 测试场景总结

| 场景 | 用户 | 操作 | 预期结果 |
|------|------|------|---------|
| 创建项目 | business_expert | POST /projects | 201 Created |
| 查看项目 | annotator1 | GET /projects | 200 OK |
| 创建用户 | admin | POST /users | 201 Created |
| 创建用户 | annotator1 | POST /users | 403 Forbidden |
| 查看任务 | annotator1 | GET /tasks/assigned | 200 OK |
| 提交标注 | annotator1 | POST /annotations | 201 Created |
| 审核标注 | reviewer | POST /annotations/review | 200 OK |

---

## 🆘 获取帮助

### 查看日志

```bash
docker compose logs -f superinsight-api
docker compose logs -f postgres
docker compose logs -f label-studio
```

### 检查配置

```bash
# 查看 API 配置
docker compose exec superinsight-api env | grep -E "DATABASE|REDIS|NEO4J"

# 查看数据库配置
docker compose exec postgres psql -U superinsight -d superinsight -c "\conninfo"
```

### 测试连接

```bash
# 测试 API 连接
curl http://localhost:8000/health

# 测试数据库连接
docker compose exec postgres pg_isready -U superinsight

# 测试 Redis 连接
docker compose exec redis redis-cli ping
```

---

## 📝 测试报告模板

```
测试时间: [日期和时间]
测试人员: [名字]
测试环境: [环境描述]

测试结果:
- 服务状态: ✅ 通过
- 数据验证: ✅ 通过
- 用户登录: ✅ 通过
- API 端点: ✅ 通过
- 工作流测试: ✅ 通过
- 权限控制: ✅ 通过

发现的问题:
[列出任何问题]

建议:
[列出任何建议]
```

---

**创建时间**: 2026-01-20  
**最后更新**: 2026-01-20  
**版本**: 1.0  
**状态**: ✅ 完成

