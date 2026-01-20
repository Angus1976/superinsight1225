# SuperInsight 完整流程测试检查清单

**版本**: 1.0  
**最后更新**: 2026-01-20

---

## ✅ 环境准备

- [ ] Docker 已安装
- [ ] Docker Compose 已安装
- [ ] 至少 8GB 可用内存
- [ ] 至少 20GB 可用磁盘空间

---

## ✅ 第一步：启动服务

```bash
./start-superinsight.sh
```

- [ ] PostgreSQL 容器运行中
- [ ] Redis 容器运行中
- [ ] Neo4j 容器运行中
- [ ] Label Studio 容器运行中
- [ ] SuperInsight API 容器运行中

**验证命令**：
```bash
docker compose ps
```

---

## ✅ 第二步：生成演示数据

```bash
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

- [ ] 脚本执行成功
- [ ] 显示"演示数据生成完成"
- [ ] 显示 6 个测试账号
- [ ] 显示 3 个演示项目
- [ ] 显示 3 个数据集
- [ ] 显示 3 个标注任务

---

## ✅ 第三步：快速数据检查

```bash
bash scripts/quick_data_check.sh
```

- [ ] 数据库连接成功
- [ ] 用户表中有 6 条记录
- [ ] 项目表中有 3 条记录
- [ ] 任务表中有 3 条记录
- [ ] 数据集表中有 3 条记录
- [ ] 显示"所有数据都已入库，可以开始测试"

---

## ✅ 第四步：运行完整流程测试

```bash
bash scripts/verify_and_test_complete_flow.sh
```

### 服务状态检查
- [ ] API 服务运行正常
- [ ] 数据库连接正常

### 数据库数据验证
- [ ] 用户表中有 6 条记录
- [ ] 项目表中有 3 条记录
- [ ] 任务表中有 3 条记录

### 用户登录测试
- [ ] admin 登录成功
- [ ] business_expert 登录成功
- [ ] tech_expert 登录成功
- [ ] annotator1 登录成功
- [ ] annotator2 登录成功
- [ ] reviewer 登录成功

### API 端点测试
- [ ] GET /api/v1/users/me 成功
- [ ] GET /api/v1/projects 成功
- [ ] GET /api/v1/tasks 成功

### 标注工作流测试
- [ ] 标注员可以获取分配的任务
- [ ] 标注员可以查看待标注的数据

### 权限控制测试
- [ ] Admin 可以创建用户
- [ ] Annotator 被拒绝创建用户

### 测试报告
- [ ] 生成了测试报告
- [ ] 显示数据库统计信息

---

## ✅ 第五步：手动测试

### 访问 API 文档

- [ ] 打开 http://localhost:8000/docs
- [ ] 页面加载成功
- [ ] 显示所有 API 端点

### 使用 Swagger UI 测试

- [ ] 点击 "Authorize" 按钮
- [ ] 输入用户名和密码
- [ ] 点击 "Authorize" 成功
- [ ] 可以测试 API 端点

### 测试用户登录

- [ ] 使用 admin 账号登录成功
- [ ] 使用 business_expert 账号登录成功
- [ ] 使用 annotator1 账号登录成功
- [ ] 使用 reviewer 账号登录成功

### 测试项目管理

- [ ] 可以查看项目列表
- [ ] 可以查看项目详情
- [ ] 可以创建新项目（如果有权限）

### 测试任务管理

- [ ] 可以查看任务列表
- [ ] 可以查看任务详情
- [ ] 可以查看任务进度

### 测试 Label Studio

- [ ] 打开 http://localhost:8080
- [ ] 使用 admin@superinsight.com 登录
- [ ] 可以查看项目列表
- [ ] 可以创建新项目

---

## ✅ 数据库验证

### 进入数据库

```bash
docker compose exec postgres psql -U superinsight -d superinsight
```

### 验证用户表

```sql
SELECT COUNT(*) FROM users;
```
- [ ] 返回 6

```sql
SELECT username FROM users ORDER BY username;
```
- [ ] 显示所有 6 个用户

### 验证项目表

```sql
SELECT COUNT(*) FROM projects;
```
- [ ] 返回 3

```sql
SELECT name FROM projects;
```
- [ ] 显示所有 3 个项目

### 验证任务表

```sql
SELECT COUNT(*) FROM annotation_tasks;
```
- [ ] 返回 3

```sql
SELECT name, status FROM annotation_tasks;
```
- [ ] 显示所有 3 个任务

### 验证数据集表

```sql
SELECT COUNT(*) FROM datasets;
```
- [ ] 返回 3

```sql
SELECT name FROM datasets;
```
- [ ] 显示所有 3 个数据集

---

## ✅ 功能测试

### 认证和授权
- [ ] 正确的凭证可以登录
- [ ] 错误的凭证无法登录
- [ ] 不同角色有不同的权限
- [ ] Token 可以正确验证

### 项目管理
- [ ] 可以创建项目
- [ ] 可以编辑项目
- [ ] 可以删除项目
- [ ] 可以查看项目列表

### 数据集管理
- [ ] 可以上传数据集
- [ ] 可以查看数据集列表
- [ ] 可以删除数据集

### 标注任务
- [ ] 可以创建标注任务
- [ ] 可以分配任务给标注员
- [ ] 标注员可以查看分配的任务
- [ ] 标注员可以执行标注

### 质量管理
- [ ] 可以查看待审核的标注
- [ ] 可以审核标注结果
- [ ] 可以生成质量报告

---

## ✅ 性能检查

### 资源使用

```bash
docker stats
```

- [ ] API 内存使用 < 1GB
- [ ] 数据库内存使用 < 500MB
- [ ] CPU 使用率正常

### 响应时间

- [ ] API 响应时间 < 1 秒
- [ ] 数据库查询时间 < 500ms
- [ ] 页面加载时间 < 3 秒

---

## ✅ 日志检查

### API 日志

```bash
docker compose logs superinsight-api
```

- [ ] 没有错误日志
- [ ] 没有警告日志
- [ ] 请求日志正常

### 数据库日志

```bash
docker compose logs postgres
```

- [ ] 没有错误日志
- [ ] 连接正常

### Label Studio 日志

```bash
docker compose logs label-studio
```

- [ ] 没有错误日志
- [ ] 服务正常运行

---

## ✅ 故障排查

### 如果服务无法启动

- [ ] 检查 Docker 是否运行
- [ ] 检查端口是否被占用
- [ ] 查看容器日志
- [ ] 重启 Docker

### 如果数据库连接失败

- [ ] 检查 PostgreSQL 容器是否运行
- [ ] 检查数据库凭证
- [ ] 查看数据库日志
- [ ] 重启数据库容器

### 如果 API 无法连接

- [ ] 检查 API 容器是否运行
- [ ] 检查端口 8000 是否被占用
- [ ] 查看 API 日志
- [ ] 重启 API 容器

### 如果数据为空

- [ ] 运行数据生成脚本
- [ ] 检查脚本是否执行成功
- [ ] 查看数据库中的数据
- [ ] 重新生成数据

---

## ✅ 最终验证

- [ ] 所有服务都在运行
- [ ] 所有数据都已入库
- [ ] 所有测试都通过
- [ ] 没有错误日志
- [ ] 性能指标正常
- [ ] 可以进行手动测试

---

## 📝 测试结果

### 总体结果

- [ ] ✅ 通过
- [ ] ⚠️ 部分通过
- [ ] ❌ 失败

### 发现的问题

```
[列出任何问题]
```

### 建议

```
[列出任何建议]
```

### 测试人员

```
[名字]
```

### 测试时间

```
[日期和时间]
```

---

## 🎯 下一步

- [ ] 所有检查项都已完成
- [ ] 可以开始功能开发
- [ ] 可以进行性能优化
- [ ] 可以部署到生产环境

---

**创建时间**: 2026-01-20  
**最后更新**: 2026-01-20  
**版本**: 1.0

