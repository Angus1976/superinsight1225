# Docker 启动诊断报告

**生成时间**: 2026-01-16  
**问题**: Docker 命令不可用，导致容器重建流程卡住

## 问题分析

### 根本原因
Docker Desktop 已安装但未运行，导致 `docker` 命令不可用。

### 检测到的状态
1. ✓ Docker Desktop 已安装在 `/Applications/Docker.app`
2. ✗ Docker 守护进程未运行
3. ✗ `docker` 命令在 PATH 中不可用
4. ⏳ Docker Desktop 正在启动中（已执行 `open -a Docker`）

### 为什么会卡住
- Docker Desktop 在 macOS 上启动通常需要 30-60 秒
- 启动过程包括：
  1. 启动 Docker 守护进程
  2. 初始化虚拟机（HyperKit 或 Apple Virtualization）
  3. 配置网络和存储
  4. 将 `docker` 命令添加到 PATH

## 已完成的修复

### 1. 文档更新（遵循 Doc-First 工作流）✅

已创建完整的 Docker 基础设施文档：
- `.kiro/specs/docker-infrastructure/requirements.md` - 需求文档
- `.kiro/specs/docker-infrastructure/design.md` - 设计文档
- `.kiro/specs/docker-infrastructure/tasks.md` - 任务分解
- `CHANGELOG.md` - 更新日志（[Unreleased] 部分）

### 2. SQL 语法错误修复 ✅

**文件**: `scripts/init-db.sql`

**修复内容**:
```sql
# 修复前（错误）:
DO $
BEGIN
    ...
END
$;

# 修复后（正确）:
DO $$
BEGIN
    ...
END
$$;
```

**原因**: PostgreSQL PL/pgSQL 要求使用 `$$` 作为 DO 块的分隔符，单个 `$` 会导致语法错误。

### 3. 自动化脚本创建 ✅

创建了两个脚本来自动化重建流程：

#### `check-docker-status.sh`
- 检查 Docker 是否可用
- 显示容器状态
- 提供下一步指导

#### `wait-for-docker-and-rebuild.sh`
- 等待 Docker 就绪（最多 60 秒）
- 停止并清理旧容器
- 重建 API 容器（无缓存）
- 启动所有服务
- 验证 PostgreSQL 初始化
- 检查所有服务健康状态
- 生成详细日志（`docker-rebuild.log`）

## 下一步操作

### 选项 1: 等待 Docker Desktop 启动（推荐）

```bash
# 1. 等待 1-2 分钟让 Docker Desktop 完全启动
# 2. 检查 Docker 状态
./check-docker-status.sh

# 3. 如果 Docker 就绪，运行重建脚本
./wait-for-docker-and-rebuild.sh
```

### 选项 2: 手动启动 Docker Desktop

1. 打开 Spotlight（Cmd + Space）
2. 搜索 "Docker"
3. 点击 Docker Desktop 图标
4. 等待菜单栏出现 Docker 图标且显示 "Docker Desktop is running"
5. 运行检查脚本：`./check-docker-status.sh`
6. 运行重建脚本：`./wait-for-docker-and-rebuild.sh`

### 选项 3: 检查 Docker Desktop 状态

```bash
# 检查 Docker Desktop 进程
ps aux | grep -i docker

# 检查 Docker Desktop 日志
tail -f ~/Library/Containers/com.docker.docker/Data/log/vm/dockerd.log
```

## 预期结果

重建脚本成功后，您应该看到：

```
=== Rebuild Summary ===
Container Status:
NAME                    STATUS              PORTS
superinsight-postgres   Up (healthy)        5432->5432
superinsight-redis      Up (healthy)        6379->6379
superinsight-neo4j      Up (healthy)        7474->7474, 7687->7687
superinsight-label-studio Up (healthy)      8080->8080
superinsight-api        Up                  8000->8000

✓ PostgreSQL is ready
✓ No SQL syntax errors detected
✓ superinsight role exists
✓ Extensions enabled (uuid-ossp, btree_gin)
✓ All services healthy
```

## 验证步骤

重建完成后，执行以下验证：

```bash
# 1. 检查 PostgreSQL 初始化日志
docker compose logs postgres | grep -i "database system is ready"

# 2. 验证没有 SQL 语法错误
docker compose logs postgres | grep -i "error.*syntax"

# 3. 测试 API 健康检查
curl http://localhost:8000/health

# 4. 测试系统状态
curl http://localhost:8000/system/status

# 5. 查看所有容器状态
docker compose ps
```

## 故障排除

### 如果 Docker Desktop 长时间未启动

```bash
# 1. 强制退出 Docker Desktop
killall Docker

# 2. 清理 Docker 缓存（可选，谨慎使用）
rm -rf ~/Library/Containers/com.docker.docker/Data/vms

# 3. 重新启动 Docker Desktop
open -a Docker
```

### 如果 PostgreSQL 仍然报错

```bash
# 1. 查看完整的 PostgreSQL 日志
docker compose logs postgres > postgres-full.log

# 2. 检查 init 脚本语法
cat scripts/init-db.sql | grep -A 10 "DO"

# 3. 手动测试 SQL 脚本
docker exec -i superinsight-postgres psql -U postgres -d superinsight < scripts/init-db.sql
```

### 如果容器无法启动

```bash
# 1. 检查端口占用
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :7474  # Neo4j
lsof -i :8080  # Label Studio
lsof -i :8000  # API

# 2. 清理所有容器和卷（警告：会删除数据）
docker compose down -v
docker system prune -a --volumes -f

# 3. 重新构建
./wait-for-docker-and-rebuild.sh
```

## 技术细节

### SQL 语法错误详情

**错误消息**:
```
psql:/docker-entrypoint-initdb.d/init-db.sql:14: ERROR: syntax error at or near "$"
```

**原因**:
- PostgreSQL 的 PL/pgSQL 匿名代码块（DO 块）需要使用美元引用（dollar quoting）
- 标准格式是 `$$` 而不是单个 `$`
- 单个 `$` 被解析器误认为是变量引用

**修复**:
- 将 `DO $` 改为 `DO $$`
- 将 `END $;` 改为 `END $$;`
- 这是 PostgreSQL 的标准语法，符合官方文档

### Docker Compose 依赖链

```
PostgreSQL (健康检查) 
    ↓
Label Studio (依赖 PostgreSQL)
    ↓
API (依赖所有服务)
```

使用 `condition: service_healthy` 确保服务按正确顺序启动。

## 相关文档

- [PostgreSQL DO 语句文档](https://www.postgresql.org/docs/current/sql-do.html)
- [Docker Compose 健康检查](https://docs.docker.com/compose/compose-file/compose-file-v3/#healthcheck)
- [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)

## 总结

1. ✅ **问题已识别**: Docker Desktop 未运行
2. ✅ **SQL 错误已修复**: 更新了 `scripts/init-db.sql`
3. ✅ **文档已更新**: 遵循 Doc-First 工作流
4. ✅ **自动化脚本已创建**: 简化重建流程
5. ⏳ **等待 Docker 启动**: 需要 1-2 分钟
6. 📋 **下一步**: 运行 `./wait-for-docker-and-rebuild.sh`

---

**状态**: 等待 Docker Desktop 完全启动  
**预计时间**: 1-2 分钟  
**操作**: 运行 `./check-docker-status.sh` 检查就绪状态
