# SuperInsight 本地调试文档索引

**最后更新**: 2026-01-20  
**版本**: 1.0  
**状态**: ✅ 完成

---

## 📚 文档导航

### 🚀 快速开始（推荐从这里开始）

| 文档 | 描述 | 适用场景 |
|------|------|---------|
| **[DEBUG_QUICK_REFERENCE.md](./DEBUG_QUICK_REFERENCE.md)** | 快速参考指南，包含所有常用命令 | 需要快速查找命令或地址 |
| **[LOCAL_DEBUG_SETUP_SUMMARY.md](./LOCAL_DEBUG_SETUP_SUMMARY.md)** | 设置总结，包含完成工作和快速开始 | 了解已完成的工作和快速开始 |

### 📖 详细指南

| 文档 | 描述 | 适用场景 |
|------|------|---------|
| **[LOCAL_DEBUG_GUIDE.md](./LOCAL_DEBUG_GUIDE.md)** | 完整的本地调试指南 | 需要详细的步骤和说明 |
| **[TESTING_WORKFLOW.md](./TESTING_WORKFLOW.md)** | 测试工作流和场景 | 需要了解测试流程和工作流 |
| **[QUICK_START.md](./QUICK_START.md)** | 快速启动指南 | 需要启动 Docker 环境 |

### 🛠️ 工具和脚本

| 文件 | 描述 | 使用方法 |
|------|------|---------|
| **[scripts/seed_demo_data.py](./scripts/seed_demo_data.py)** | 模拟数据生成脚本 | `docker compose exec superinsight-api python scripts/seed_demo_data.py` |
| **[scripts/test_all_roles.sh](./scripts/test_all_roles.sh)** | 多角色测试脚本 | `bash scripts/test_all_roles.sh` |

---

## 🎯 按场景选择文档

### 场景 1：我是第一次使用，想快速了解

**推荐阅读顺序**：
1. 本文件（DEBUG_INDEX.md）- 了解文档结构
2. [DEBUG_QUICK_REFERENCE.md](./DEBUG_QUICK_REFERENCE.md) - 快速参考
3. [LOCAL_DEBUG_SETUP_SUMMARY.md](./LOCAL_DEBUG_SETUP_SUMMARY.md) - 了解已完成的工作

**快速启动**：
```bash
./start-superinsight.sh
docker compose exec superinsight-api python scripts/seed_demo_data.py
bash scripts/test_all_roles.sh
```

### 场景 2：我需要详细的步骤说明

**推荐阅读顺序**：
1. [LOCAL_DEBUG_GUIDE.md](./LOCAL_DEBUG_GUIDE.md) - 完整指南
2. [TESTING_WORKFLOW.md](./TESTING_WORKFLOW.md) - 工作流说明
3. [DEBUG_QUICK_REFERENCE.md](./DEBUG_QUICK_REFERENCE.md) - 快速查找

### 场景 3：我需要测试特定的功能

**推荐阅读顺序**：
1. [TESTING_WORKFLOW.md](./TESTING_WORKFLOW.md) - 查找相关的测试流程
2. [LOCAL_DEBUG_GUIDE.md](./LOCAL_DEBUG_GUIDE.md) - 查看功能测试清单
3. [DEBUG_QUICK_REFERENCE.md](./DEBUG_QUICK_REFERENCE.md) - 查找相关命令

### 场景 4：我遇到了问题，需要调试

**推荐阅读顺序**：
1. [DEBUG_QUICK_REFERENCE.md](./DEBUG_QUICK_REFERENCE.md) - 查看常见问题解决方案
2. [LOCAL_DEBUG_GUIDE.md](./LOCAL_DEBUG_GUIDE.md) - 查看常见问题部分
3. 查看日志：`docker compose logs -f`

### 场景 5：我想测试 Label Studio 集成

**推荐阅读顺序**：
1. [LOCAL_DEBUG_GUIDE.md](./LOCAL_DEBUG_GUIDE.md) - Label Studio 集成测试部分
2. [TESTING_WORKFLOW.md](./TESTING_WORKFLOW.md) - Label Studio 测试流程
3. [DEBUG_QUICK_REFERENCE.md](./DEBUG_QUICK_REFERENCE.md) - Label Studio 测试步骤

---

## 📋 文档内容速览

### DEBUG_QUICK_REFERENCE.md
**快速参考指南**

包含内容：
- 🚀 快速启动（3 步）
- 🌐 访问地址
- 👤 测试账号
- 📝 常用命令
- 🧪 API 测试
- 🏷️ Label Studio 测试
- 🔍 调试技巧
- 🐛 常见问题

**何时使用**：需要快速查找命令或地址

### LOCAL_DEBUG_GUIDE.md
**完整的本地调试指南**

包含内容：
- 📋 目录
- 🚀 快速启动
- 📝 模拟数据设置
- 👤 多角色账号测试
- 🏷️ Label Studio 集成测试
- 🧪 功能测试清单
- 🐛 常见问题
- 📊 性能测试

**何时使用**：需要详细的步骤和说明

### LOCAL_DEBUG_SETUP_SUMMARY.md
**设置总结文档**

包含内容：
- 📋 已完成的工作
- 🚀 快速开始
- 👤 测试账号
- 🌐 访问地址
- 📝 测试场景
- 🧪 功能测试清单
- 🔧 常用命令
- 🆘 获取帮助

**何时使用**：了解已完成的工作和快速开始

### TESTING_WORKFLOW.md
**测试工作流文档**

包含内容：
- 📊 完整的测试工作流
- 🔄 多角色测试流程
- 🧪 API 测试流程
- 🏷️ Label Studio 测试流程
- 📊 数据库测试流程
- 🔍 调试技巧
- ✅ 测试检查清单
- 🎯 常见测试场景

**何时使用**：需要了解测试流程和工作流

---

## 🚀 3 步快速启动

### 第一步：启动所有服务

```bash
./start-superinsight.sh
```

或手动启动：
```bash
docker compose up -d
```

### 第二步：生成演示数据

```bash
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

### 第三步：运行测试

```bash
bash scripts/test_all_roles.sh
```

---

## 👤 测试账号速查

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | 系统管理员 |
| `business_expert` | `business123` | 业务专家 |
| `tech_expert` | `tech123` | 技术专家 |
| `annotator1` | `annotator123` | 标注员 |
| `annotator2` | `annotator123` | 标注员 |
| `reviewer` | `reviewer123` | 质量审核员 |

---

## 🌐 访问地址速查

| 服务 | 地址 |
|------|------|
| API 文档 | http://localhost:8000/docs |
| API 健康检查 | http://localhost:8000/health |
| Label Studio | http://localhost:8080 |
| Neo4j 浏览器 | http://localhost:7474 |
| Prometheus | http://localhost:9090 |

---

## 🔧 常用命令速查

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

### 数据库操作

```bash
# 进入 PostgreSQL
docker compose exec postgres psql -U superinsight -d superinsight

# 查看所有表
\dt

# 查看用户表
SELECT * FROM users;

# 退出
\q
```

---

## 📚 文档结构

```
.
├── DEBUG_INDEX.md                    # 本文件 - 文档索引
├── DEBUG_QUICK_REFERENCE.md          # 快速参考指南
├── LOCAL_DEBUG_GUIDE.md              # 完整的本地调试指南
├── LOCAL_DEBUG_SETUP_SUMMARY.md      # 设置总结文档
├── TESTING_WORKFLOW.md               # 测试工作流文档
├── QUICK_START.md                    # 快速启动指南
├── SETUP_COMPLETE.txt                # 设置完成提示
├── scripts/
│   ├── seed_demo_data.py             # 模拟数据生成脚本
│   └── test_all_roles.sh             # 多角色测试脚本
├── docker-compose.yml                # Docker 配置
└── .env.example                      # 环境变量示例
```

---

## 🎯 功能特性

### ✅ 多角色支持
- 系统管理员（Admin）
- 业务专家（Business Expert）
- 技术专家（Tech Expert）
- 标注员（Annotator）
- 质量审核员（Reviewer）

### ✅ 完整的工作流
- 用户认证和授权
- 项目和数据集管理
- 标注任务分配
- Label Studio 集成
- 质量管理和审核
- 计费和统计

### ✅ 开发工具
- Swagger UI API 文档
- 实时日志查看
- 数据库直接访问
- 性能监控
- 自动化测试脚本

---

## 🆘 获取帮助

### 快速问题解答

**Q: 如何快速启动？**
```bash
./start-superinsight.sh
docker compose exec superinsight-api python scripts/seed_demo_data.py
bash scripts/test_all_roles.sh
```

**Q: 如何查看日志？**
```bash
docker compose logs -f superinsight-api
```

**Q: 如何重置数据库？**
```bash
docker compose down -v
docker compose up -d
docker compose exec superinsight-api python scripts/seed_demo_data.py
```

**Q: 如何连接到数据库？**
```bash
docker compose exec postgres psql -U superinsight -d superinsight
```

### 详细文档

- [完整调试指南](./LOCAL_DEBUG_GUIDE.md)
- [快速参考指南](./DEBUG_QUICK_REFERENCE.md)
- [测试工作流](./TESTING_WORKFLOW.md)
- [设置总结](./LOCAL_DEBUG_SETUP_SUMMARY.md)

---

## 📊 文档使用统计

| 文档 | 大小 | 主要内容 | 推荐阅读时间 |
|------|------|---------|-----------|
| DEBUG_QUICK_REFERENCE.md | ~5KB | 快速参考 | 5-10 分钟 |
| LOCAL_DEBUG_SETUP_SUMMARY.md | ~8KB | 设置总结 | 10-15 分钟 |
| LOCAL_DEBUG_GUIDE.md | ~15KB | 完整指南 | 20-30 分钟 |
| TESTING_WORKFLOW.md | ~12KB | 工作流 | 15-25 分钟 |

---

## ✅ 验证清单

- [x] 创建了完整的本地调试指南
- [x] 创建了模拟数据生成脚本
- [x] 创建了多角色测试脚本
- [x] 创建了快速参考指南
- [x] 创建了设置总结文档
- [x] 创建了测试工作流文档
- [x] 创建了文档索引
- [x] 所有脚本都可执行
- [x] 文档结构清晰
- [x] 包含完整的测试场景
- [x] 包含常见问题解答
- [x] 包含快速启动步骤

---

## 🎓 学习路径

### 初级用户（第一次使用）

1. 阅读本文件（DEBUG_INDEX.md）
2. 阅读 [DEBUG_QUICK_REFERENCE.md](./DEBUG_QUICK_REFERENCE.md)
3. 运行快速启动命令
4. 访问 http://localhost:8000/docs 测试 API

**预计时间**: 30 分钟

### 中级用户（需要详细了解）

1. 阅读 [LOCAL_DEBUG_GUIDE.md](./LOCAL_DEBUG_GUIDE.md)
2. 阅读 [TESTING_WORKFLOW.md](./TESTING_WORKFLOW.md)
3. 执行完整的测试流程
4. 测试不同角色的功能

**预计时间**: 1-2 小时

### 高级用户（需要深入调试）

1. 阅读所有文档
2. 查看源代码
3. 修改测试脚本
4. 进行性能测试和优化

**预计时间**: 2-4 小时

---

## 📞 支持

如有问题，请：

1. 查看相关文档
2. 检查日志：`docker compose logs -f`
3. 运行测试脚本：`bash scripts/test_all_roles.sh`
4. 查看 API 文档：http://localhost:8000/docs
5. 提交 Issue

---

## 📝 更新日志

### 版本 1.0 (2026-01-20)
- ✅ 创建了完整的本地调试指南
- ✅ 创建了模拟数据生成脚本
- ✅ 创建了多角色测试脚本
- ✅ 创建了快速参考指南
- ✅ 创建了设置总结文档
- ✅ 创建了测试工作流文档
- ✅ 创建了文档索引

---

**创建时间**: 2026-01-20  
**最后更新**: 2026-01-20  
**版本**: 1.0  
**状态**: ✅ 完成

---

## 🚀 现在就开始吧！

```bash
# 第一步：启动服务
./start-superinsight.sh

# 第二步：生成演示数据
docker compose exec superinsight-api python scripts/seed_demo_data.py

# 第三步：运行测试
bash scripts/test_all_roles.sh

# 第四步：访问应用
# API 文档: http://localhost:8000/docs
# Label Studio: http://localhost:8080
```

祝使用愉快！🎉

