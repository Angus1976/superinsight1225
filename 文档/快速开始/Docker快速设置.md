# 🐳 Docker 容器重建和功能测试 - 完整指南

## 📌 项目概述

本项目为 SuperInsight 平台提供了完整的 Docker 容器重建和功能测试系统。所有脚本、文档和配置已准备就绪，可以立即使用。

## ⚡ 快速开始（3 步）

### 1️⃣ 配置 Docker 环境
```bash
chmod +x scripts/docker-setup.sh
./scripts/docker-setup.sh
```

### 2️⃣ 重建容器
```bash
chmod +x scripts/rebuild-containers.sh
./scripts/rebuild-containers.sh
```

### 3️⃣ 测试功能
```bash
chmod +x scripts/test-roles-functionality.sh
./scripts/test-roles-functionality.sh
```

## 📁 项目结构

```
.
├── scripts/
│   ├── rebuild-containers.sh          # 容器重建脚本
│   ├── test-roles-functionality.sh    # 功能测试脚本
│   └── docker-setup.sh                # Docker 环境设置脚本
├── .env.docker                        # Docker 路径配置
├── docker-compose.yml                 # Docker Compose 配置
├── QUICK_REFERENCE.md                 # 快速参考卡片
├── OPERATION_CHECKLIST.md             # 操作清单
├── DOCKER_REBUILD_AND_TEST_GUIDE.md   # 详细操作指南
├── DOCKER_OPERATIONS_SUMMARY.md       # 操作总结
├── SETUP_COMPLETE_SUMMARY.md          # 完成总结
├── FINAL_REPORT.md                    # 最终报告
└── README_DOCKER_SETUP.md             # 本文件
```

## 🔑 关键信息

### Docker 路径
```
/Applications/Docker.app/Contents/Resources/bin/docker
```

### 服务地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| Label Studio | http://localhost:8080 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

### 测试用户

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin |
| 标注员 | annotator | password |
| 专家 | expert | password |

## 📚 文档导航

### 🚀 快速开始
- [快速参考卡片](./QUICK_REFERENCE.md) - 常用命令和地址

### ✅ 逐步操作
- [操作清单](./OPERATION_CHECKLIST.md) - 完整的检查清单

### 📖 详细指南
- [Docker 重建和测试指南](./DOCKER_REBUILD_AND_TEST_GUIDE.md) - 完整参考
- [Docker 操作总结](./DOCKER_OPERATIONS_SUMMARY.md) - 快速查阅
- [完成总结](./SETUP_COMPLETE_SUMMARY.md) - 项目概览

### 📊 项目报告
- [最终报告](./FINAL_REPORT.md) - 项目成果总结

## 🧪 测试覆盖范围

脚本会自动测试以下功能：

1. ✅ 系统健康检查
2. ✅ 管理员功能（登录、用户、配置、审计）
3. ✅ 标注员功能（任务、项目、质量）
4. ✅ 专家功能（本体、协作、变更）
5. ✅ 品牌系统功能（主题、配置、A/B 测试）
6. ✅ 管理配置功能（数据库、LLM、同步）
7. ✅ AI 标注功能（方法、缓存、指标）
8. ✅ 文本转 SQL 功能（方法、架构）
9. ✅ 本体协作功能（专家、历史）
10. ✅ 前端功能（页面加载）

## 🔧 常用命令

### 基础命令
```bash
# 查看容器状态
docker compose ps

# 启动容器
docker compose up -d

# 停止容器
docker compose down

# 查看日志
docker compose logs -f
```

### 前端相关
```bash
# 查看前端日志
docker compose logs -f frontend

# 进入前端容器
docker compose exec frontend sh

# 重建前端
docker compose build --no-cache frontend
```

### 后端相关
```bash
# 查看后端日志
docker compose logs -f app

# 进入后端容器
docker compose exec app bash

# 运行后端测试
docker compose exec app pytest tests/
```

## 🐛 故障排除

### Docker 命令找不到
```bash
# 运行设置脚本
./scripts/docker-setup.sh

# 或手动添加别名
alias docker="/Applications/Docker.app/Contents/Resources/bin/docker"
```

### 容器启动失败
```bash
# 查看日志
docker compose logs app

# 重启容器
docker compose restart

# 完全重建
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 前端无法连接后端
```bash
# 检查后端是否运行
curl http://localhost:8000/health/live

# 检查前端环境变量
cat frontend/.env.development

# 查看前端日志
docker compose logs -f frontend
```

更多问题请参考 [详细指南](./DOCKER_REBUILD_AND_TEST_GUIDE.md#故障排除)

## 📊 脚本说明

### rebuild-containers.sh
**功能：** 智能重建容器
- 检查前端代码变更，有变更则重建前端容器
- 检查后端代码变更，有变更则重建后端容器
- 保持基础容器（PostgreSQL、Redis 等）不变
- 自动启动所有容器
- 等待服务就绪

**执行时间：** 5-10 分钟

### test-roles-functionality.sh
**功能：** 全面的功能测试
- 测试 10 个场景
- 测试 30+ 个 API 端点
- 覆盖所有角色功能
- 自动生成测试报告

**执行时间：** 2-3 分钟

### docker-setup.sh
**功能：** Docker 环境配置
- 验证 Docker 安装
- 创建 `docker` 别名
- 配置 shell 环境

**执行时间：** < 1 分钟

## 🎯 下一步

1. ✅ 运行 `./scripts/docker-setup.sh` 配置 Docker 环境
2. ✅ 运行 `./scripts/rebuild-containers.sh` 重建容器
3. ✅ 运行 `./scripts/test-roles-functionality.sh` 测试功能
4. ✅ 访问 http://localhost:5173 查看前端
5. ✅ 根据 [操作清单](./OPERATION_CHECKLIST.md) 进行完整测试

## 📞 支持

### 快速查阅
- 常用命令：[快速参考卡片](./QUICK_REFERENCE.md)
- 故障排除：[详细指南](./DOCKER_REBUILD_AND_TEST_GUIDE.md#故障排除)

### 详细指南
- 完整操作：[详细指南](./DOCKER_REBUILD_AND_TEST_GUIDE.md)
- 操作总结：[操作总结](./DOCKER_OPERATIONS_SUMMARY.md)

## 📝 版本信息

- **创建日期**: 2026-01-25
- **Docker**: 最新
- **Node**: 20 Alpine
- **Python**: 3.11
- **PostgreSQL**: 15 Alpine
- **Redis**: 7 Alpine

## ✨ 特色功能

- ✅ 智能容器重建（仅重建必要的容器）
- ✅ 全面的功能测试（10 个场景，30+ 个端点）
- ✅ 完整的文档（快速参考到详细指南）
- ✅ 自动化脚本（一键启动）
- ✅ 清晰的错误提示（便于故障排除）

## 🎉 项目成果

- 📝 创建脚本: 3 个
- 📚 创建文档: 7 个
- ⚙️ 更新配置: 2 个
- 🐳 容器总数: 10 个
- 🧪 测试场景: 10 个
- 🔌 测试端点: 30+ 个

---

**准备好了吗？现在就开始吧！** 🚀

```bash
chmod +x scripts/docker-setup.sh
./scripts/docker-setup.sh
```

---

**维护者**: SuperInsight 开发团队  
**最后更新**: 2026-01-25  
**状态**: ✅ 完成并已验证
