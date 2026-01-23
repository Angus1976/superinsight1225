# SuperInsight 完整流程测试 - 快速开始

**版本**: 1.0  
**最后更新**: 2026-01-20  
**目的**: 确保数据已入库并测试完整的工作流

---

## ⚡ 3 步快速测试

### 第一步：启动服务并生成数据

```bash
# 1. 启动所有服务
./start-superinsight.sh

# 2. 生成演示数据
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

### 第二步：快速检查数据

```bash
# 检查数据是否已入库
bash scripts/quick_data_check.sh
```

**预期输出**：
```
✅ 数据库连接成功
✅ 用户表中有 6 条记录
✅ 项目表中有 3 条记录
✅ 标注任务表中有 3 条记录
✅ 数据集表中有 3 条记录
✅ 所有数据都已入库，可以开始测试
```

### 第三步：运行完整流程测试

```bash
# 运行完整的自动化测试
bash scripts/verify_and_test_complete_flow.sh
```

**测试内容**：
- ✅ 检查所有服务状态
- ✅ 验证数据库中的数据
- ✅ 测试用户登录
- ✅ 测试 API 端点
- ✅ 测试完整的标注工作流
- ✅ 测试权限控制
- ✅ 生成测试报告

---

## 📊 数据验证

### 快速查看数据库中的数据

```bash
# 进入数据库
docker compose exec postgres psql -U superinsight -d superinsight

# 查看用户
SELECT username, email FROM users;

# 查看项目
SELECT name, status FROM projects;

# 查看任务
SELECT name, status, total_items, completed_items FROM annotation_tasks;

# 退出
\q
```

### 预期的数据

**用户（6 个）**：
```
admin
business_expert
tech_expert
annotator1
annotator2
reviewer
```

**项目（3 个）**：
```
电商商品分类
客服对话质量评估
医疗文本挖掘
```

**任务（3 个）**：
```
商品分类标注 - 第一批
商品分类标注 - 第二批
客服对话质量评估
```

---

## 🧪 手动测试

### 测试 1：用户登录

```bash
# Admin 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 预期响应：返回 access_token
```

### 测试 2：获取项目列表

```bash
# 使用 Token 获取项目列表
TOKEN="your_token_here"
curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN"

# 预期响应：返回 3 个项目
```

### 测试 3：获取任务列表

```bash
# 获取任务列表
curl -X GET http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN"

# 预期响应：返回 3 个任务
```

### 测试 4：使用 Swagger UI

1. 打开 http://localhost:8000/docs
2. 点击 "Authorize" 按钮
3. 输入用户名和密码
4. 点击 "Authorize"
5. 现在可以直接测试所有 API 端点

---

## 📋 完整工作流

### 工作流步骤

```
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

运行以下命令自动执行所有步骤：

```bash
bash scripts/verify_and_test_complete_flow.sh
```

---

## 👤 测试账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 系统管理员 |
| business_expert | business123 | 业务专家 |
| tech_expert | tech123 | 技术专家 |
| annotator1 | annotator123 | 标注员 |
| annotator2 | annotator123 | 标注员 |
| reviewer | reviewer123 | 质量审核员 |

---

## 🌐 访问地址

| 服务 | 地址 |
|------|------|
| API 文档 | http://localhost:8000/docs |
| API 健康检查 | http://localhost:8000/health |
| Label Studio | http://localhost:8080 |
| Neo4j 浏览器 | http://localhost:7474 |

---

## 🔧 常用命令

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

# 快速检查数据
bash scripts/quick_data_check.sh

# 运行完整测试
bash scripts/verify_and_test_complete_flow.sh

# 重置数据库
docker compose down -v
docker compose up -d
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

### 数据库操作

```bash
# 进入数据库
docker compose exec postgres psql -U superinsight -d superinsight

# 查看所有表
\dt

# 查看用户
SELECT * FROM users;

# 查看项目
SELECT * FROM projects;

# 查看任务
SELECT * FROM annotation_tasks;

# 退出
\q
```

---

## ✅ 测试检查清单

### 基础检查
- [ ] 所有服务都在运行（docker compose ps）
- [ ] 数据库连接正常
- [ ] 数据已成功入库（bash scripts/quick_data_check.sh）

### 功能检查
- [ ] 用户可以登录
- [ ] 可以获取项目列表
- [ ] 可以获取任务列表
- [ ] 可以创建新项目
- [ ] 可以分配任务

### 工作流检查
- [ ] 业务专家可以创建项目
- [ ] 标注员可以查看分配的任务
- [ ] 标注员可以执行标注
- [ ] 质量审核员可以审核标注
- [ ] 权限控制正常工作

### 自动化测试
- [ ] 运行 verify_and_test_complete_flow.sh 通过
- [ ] 所有测试项目都通过
- [ ] 生成了测试报告

---

## 🐛 常见问题

### Q: 数据库中没有数据

**A**: 运行以下命令生成演示数据：
```bash
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

### Q: API 无法连接

**A**: 检查 API 是否运行：
```bash
docker compose ps superinsight-api
docker compose logs superinsight-api
```

### Q: 登录失败

**A**: 检查用户是否存在：
```bash
docker compose exec postgres psql -U superinsight -d superinsight -c "SELECT * FROM users WHERE username='admin';"
```

### Q: 如何重置所有数据

**A**: 运行以下命令：
```bash
docker compose down -v
docker compose up -d
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

---

## 📚 详细文档

- [完整流程测试指南](./COMPLETE_FLOW_TEST_GUIDE.md) - 详细的测试步骤和说明
- [本地调试指南](./LOCAL_DEBUG_GUIDE.md) - 完整的调试指南
- [快速参考](./DEBUG_QUICK_REFERENCE.md) - 快速命令参考
- [工作流文档](./TESTING_WORKFLOW.md) - 工作流说明

---

## 🎯 下一步

1. **启动环境**
   ```bash
   ./start-superinsight.sh
   ```

2. **生成数据**
   ```bash
   docker compose exec superinsight-api python scripts/seed_demo_data.py
   ```

3. **检查数据**
   ```bash
   bash scripts/quick_data_check.sh
   ```

4. **运行测试**
   ```bash
   bash scripts/verify_and_test_complete_flow.sh
   ```

5. **手动测试**
   - 访问 http://localhost:8000/docs
   - 使用测试账号登录
   - 测试各项功能

---

## 📞 获取帮助

### 查看日志

```bash
# API 日志
docker compose logs -f superinsight-api

# 数据库日志
docker compose logs -f postgres

# Label Studio 日志
docker compose logs -f label-studio
```

### 检查服务

```bash
# 查看所有服务状态
docker compose ps

# 检查 API 健康状态
curl http://localhost:8000/health

# 检查数据库连接
docker compose exec postgres pg_isready -U superinsight
```

### 运行测试

```bash
# 快速数据检查
bash scripts/quick_data_check.sh

# 完整流程测试
bash scripts/verify_and_test_complete_flow.sh
```

---

**创建时间**: 2026-01-20  
**最后更新**: 2026-01-20  
**版本**: 1.0  
**状态**: ✅ 完成

