# SuperInsight Docker 资源索引

## 📚 文档导航

### 🚀 快速开始
1. **QUICK_DOCKER_STARTUP.sh** - 一键启动所有服务
   ```bash
   bash QUICK_DOCKER_STARTUP.sh
   ```

2. **DOCKER_FULLSTACK_READY.md** - 就绪状态和快速开始
   - 当前状态
   - 访问地址
   - 快速命令
   - 下一步指南

### 📖 详细指南
1. **DOCKER_FULLSTACK_COMPLETE_GUIDE.md** - 完整启动和操作指南
   - 第一步：修复 PostgreSQL
   - 第二步：启动基础服务
   - 第三步：初始化数据库
   - 第四步：启动 API
   - 第五步：验证完整栈
   - 第六步：监控和日志

2. **DOCKER_OPERATIONS_GUIDE.md** - 详细的操作指南
   - 服务管理
   - 日志和监控
   - 数据库操作
   - 故障排查
   - 备份和恢复
   - 性能优化

3. **LOCAL_DOCKER_FULLSTACK_STARTUP.md** - 本地启动指南
   - 当前状态
   - 第一步：修复 PostgreSQL
   - 第二步：启动基础服务
   - 第三步：初始化数据库
   - 第四步：启动 API
   - 第五步：验证完整栈

### 📊 报告和总结
1. **DOCKER_FULLSTACK_STARTUP_SUCCESS.md** - 启动成功详情
   - 启动状态
   - 访问地址
   - 验证服务连接
   - 下一步

2. **DOCKER_STARTUP_COMPLETE_SUMMARY.md** - 启动总结
   - 启动状态
   - 访问地址
   - 快速启动命令
   - 常用命令
   - 下一步

3. **DOCKER_FULLSTACK_COMPLETION_REPORT.md** - 完成报告
   - 执行摘要
   - 启动目标
   - 启动结果
   - 已创建的文件
   - 启动流程
   - 下一步

---

## 🛠️ 工具和脚本

### 启动脚本
1. **QUICK_DOCKER_STARTUP.sh** - 快速启动
   ```bash
   bash QUICK_DOCKER_STARTUP.sh
   ```
   - 清理旧容器
   - 创建数据目录
   - 启动所有服务
   - 验证服务状态

2. **start_fullstack.sh** - 完整启动
   ```bash
   bash start_fullstack.sh
   ```
   - 检查 Docker
   - 清理旧容器
   - 创建目录
   - 启动所有服务
   - 初始化数据库
   - 启动 API

### 诊断和修复
1. **docker_diagnostic.sh** - 诊断和修复工具
   ```bash
   # 运行诊断
   bash docker_diagnostic.sh diagnose
   
   # 修复 PostgreSQL
   bash docker_diagnostic.sh fix-postgres
   
   # 修复所有服务
   bash docker_diagnostic.sh fix-all
   
   # 清理磁盘
   bash docker_diagnostic.sh cleanup
   ```

---

## 🐳 Docker 配置

### 本地开发（推荐）
**docker-compose.local.yml**
- PostgreSQL
- Redis
- Neo4j
- Label Studio
- 用途: 本地开发

### 完整配置
**docker-compose.yml**
- 包含 API 服务
- 用途: 完整部署

### 生产环境
**docker-compose.prod.yml**
- 完整的生产环境配置
- 包含监控和日志
- 用途: 生产部署

---

## 📍 访问地址

### Web 界面
| 服务 | URL | 用户名 | 密码 |
|------|-----|--------|------|
| Label Studio | http://localhost:8080 | admin@superinsight.com | admin123 |
| Neo4j Browser | http://localhost:7474 | neo4j | password |

### 数据库连接
| 服务 | 连接字符串 |
|------|-----------|
| PostgreSQL | postgresql://superinsight:password@localhost:5432/superinsight |
| Redis | redis://localhost:6379 |
| Neo4j | bolt://localhost:7687 |

---

## 🚀 快速命令

### 启动和停止
```bash
# 启动所有服务
docker-compose -f docker-compose.local.yml up -d

# 停止所有服务
docker-compose -f docker-compose.local.yml down

# 重启所有服务
docker-compose -f docker-compose.local.yml restart

# 查看服务状态
docker-compose -f docker-compose.local.yml ps
```

### 日志和监控
```bash
# 查看所有日志
docker-compose -f docker-compose.local.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.local.yml logs -f postgres
docker-compose -f docker-compose.local.yml logs -f redis
docker-compose -f docker-compose.local.yml logs -f neo4j
docker-compose -f docker-compose.local.yml logs -f label-studio

# 查看容器资源使用
docker stats
```

### 数据库操作
```bash
# 进入 PostgreSQL
docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight

# 进入 Redis
docker-compose -f docker-compose.local.yml exec redis redis-cli

# 进入 Neo4j
docker-compose -f docker-compose.local.yml exec neo4j cypher-shell -u neo4j -p password
```

### 备份和恢复
```bash
# 备份 PostgreSQL
docker-compose -f docker-compose.local.yml exec postgres pg_dump -U superinsight superinsight > backup.sql

# 恢复 PostgreSQL
docker-compose -f docker-compose.local.yml exec -T postgres psql -U superinsight superinsight < backup.sql

# 备份 Redis
docker-compose -f docker-compose.local.yml exec redis redis-cli BGSAVE
docker cp superinsight-redis:/data/dump.rdb ./redis_backup.rdb

# 备份所有数据
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/
```

---

## 🔧 故障排查

### 常见问题

#### 容器无法启动
```bash
# 查看日志
docker-compose -f docker-compose.local.yml logs <service>

# 重启容器
docker-compose -f docker-compose.local.yml restart <service>
```

#### 端口被占用
```bash
# 查找占用端口的进程
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :7474  # Neo4j
lsof -i :8080  # Label Studio

# 杀死进程
kill -9 <PID>
```

#### 网络连接问题
```bash
# 检查网络
docker network inspect superinsight-network

# 重新创建网络
docker network rm superinsight-network 2>/dev/null || true
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d
```

#### 内存不足
```bash
# 查看内存使用
docker stats

# 增加 Docker 内存限制
# 在 Docker Desktop 设置中增加内存分配
```

### 诊断工具
```bash
# 运行完整诊断
bash docker_diagnostic.sh diagnose

# 修复 PostgreSQL
bash docker_diagnostic.sh fix-postgres

# 修复所有服务
bash docker_diagnostic.sh fix-all

# 清理磁盘空间
bash docker_diagnostic.sh cleanup
```

---

## 📚 文档结构

```
SuperInsight Docker 资源
├── 快速开始
│   ├── QUICK_DOCKER_STARTUP.sh
│   └── DOCKER_FULLSTACK_READY.md
├── 详细指南
│   ├── DOCKER_FULLSTACK_COMPLETE_GUIDE.md
│   ├── DOCKER_OPERATIONS_GUIDE.md
│   └── LOCAL_DOCKER_FULLSTACK_STARTUP.md
├── 报告和总结
│   ├── DOCKER_FULLSTACK_STARTUP_SUCCESS.md
│   ├── DOCKER_STARTUP_COMPLETE_SUMMARY.md
│   └── DOCKER_FULLSTACK_COMPLETION_REPORT.md
├── 工具和脚本
│   ├── QUICK_DOCKER_STARTUP.sh
│   ├── start_fullstack.sh
│   └── docker_diagnostic.sh
├── Docker 配置
│   ├── docker-compose.local.yml
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
└── 资源索引
    └── DOCKER_RESOURCES_INDEX.md (本文件)
```

---

## 🎯 使用场景

### 场景 1: 快速启动开发环境
1. 运行 `bash QUICK_DOCKER_STARTUP.sh`
2. 访问 http://localhost:8080 (Label Studio)
3. 访问 http://localhost:7474 (Neo4j)
4. 启动 API: `python main.py`

### 场景 2: 故障排查
1. 运行 `bash docker_diagnostic.sh diagnose`
2. 查看诊断结果
3. 根据问题运行修复脚本
4. 查看日志: `docker-compose -f docker-compose.local.yml logs -f`

### 场景 3: 数据库操作
1. 进入 PostgreSQL: `docker-compose -f docker-compose.local.yml exec postgres psql -U superinsight -d superinsight`
2. 执行 SQL 命令
3. 或者使用备份/恢复脚本

### 场景 4: 性能优化
1. 查看资源使用: `docker stats`
2. 查看日志: `docker-compose -f docker-compose.local.yml logs -f`
3. 根据需要调整配置
4. 重启服务: `docker-compose -f docker-compose.local.yml restart`

---

## 📞 获取帮助

### 查看文档
```bash
# 查看完整指南
cat DOCKER_FULLSTACK_COMPLETE_GUIDE.md

# 查看操作指南
cat DOCKER_OPERATIONS_GUIDE.md

# 查看就绪状态
cat DOCKER_FULLSTACK_READY.md
```

### 运行诊断
```bash
bash docker_diagnostic.sh diagnose
```

### 查看日志
```bash
docker-compose -f docker-compose.local.yml logs -f
```

### 查看状态
```bash
docker-compose -f docker-compose.local.yml ps
```

---

## ✨ 功能清单

### ✅ 已完成
- [x] PostgreSQL 数据库启动
- [x] Redis 缓存启动
- [x] Neo4j 知识图谱启动
- [x] Label Studio 标注工具启动
- [x] 所有服务连接验证
- [x] 启动脚本创建
- [x] 诊断工具创建
- [x] 文档编写
- [x] 资源索引创建

### ⏳ 待完成
- [ ] SuperInsight API 启动
- [ ] 数据库初始化
- [ ] 前端应用启动
- [ ] 系统测试
- [ ] 性能优化
- [ ] 生产部署

---

## 🎓 学习资源

### 官方文档
- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [Redis 官方文档](https://redis.io/documentation)
- [Neo4j 官方文档](https://neo4j.com/docs/)
- [Label Studio 官方文档](https://labelstud.io/guide/)

### 本项目文档
- 完整指南: `DOCKER_FULLSTACK_COMPLETE_GUIDE.md`
- 操作指南: `DOCKER_OPERATIONS_GUIDE.md`
- 启动总结: `DOCKER_STARTUP_COMPLETE_SUMMARY.md`

---

## 🎉 总结

✅ **基础服务全部就绪**
- PostgreSQL ✓
- Redis ✓
- Neo4j ✓
- Label Studio ✓

📝 **已创建的资源**
- 启动脚本 ✓
- 诊断工具 ✓
- 完整文档 ✓
- 资源索引 ✓

🚀 **下一步**
1. 启动 SuperInsight API
2. 初始化数据库
3. 配置 Label Studio
4. 配置 Neo4j
5. 运行系统测试

---

**最后更新**: 2026-01-09  
**版本**: 1.0  
**状态**: ✅ 完成

---

## 快速链接

| 资源 | 链接 |
|------|------|
| 快速启动 | `bash QUICK_DOCKER_STARTUP.sh` |
| 完整指南 | `DOCKER_FULLSTACK_COMPLETE_GUIDE.md` |
| 操作指南 | `DOCKER_OPERATIONS_GUIDE.md` |
| 就绪状态 | `DOCKER_FULLSTACK_READY.md` |
| 诊断工具 | `bash docker_diagnostic.sh diagnose` |
| 完成报告 | `DOCKER_FULLSTACK_COMPLETION_REPORT.md` |

---

**祝你使用愉快！** 🎉
