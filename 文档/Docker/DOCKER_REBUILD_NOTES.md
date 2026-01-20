# Docker 容器重建说明 - 2026-01-14

## 完成的工作

### 1. 代码修复

#### 1.1 修复 AuditLogModel 导入问题
**问题**: 系统中多个文件引用 `AuditLogModel`，但实际类名为 `SecurityAuditLogModel`

**解决方案**: 在 `src/security/models.py` 中添加了向后兼容别名：
```python
# Backward compatibility alias
AuditLogModel = SecurityAuditLogModel
```

**影响的文件**:
- `src/database/models.py` - 已更新导入
- `src/security/audit_*.py` - 多个审计相关文件
- `src/compliance/*.py` - 合规性检查文件
- `tests/test_*.py` - 测试文件

**注释位置**: `src/security/models.py` 文件末尾，包含详细的问题背景、解决方案和使用示例

#### 1.2 修复 main.py 导入错误
**问题**: `main.py` 试图导入不存在的 `ServiceType`

**解决方案**: 
- 移除了 `ServiceType` 导入
- 简化了系统初始化逻辑
- 使用 `initialize_service_registry()` 函数

#### 1.3 修复 Dockerfile 和 docker-compose.yml
**问题**: 容器启动后立即退出

**解决方案**:
- 修改 `Dockerfile.dev` 的 CMD 为启动 uvicorn
- 修改 `docker-compose.yml` 的 command 为启动 uvicorn
- 命令: `python -m uvicorn src.app:app --host 0.0.0.0 --port 8000`

### 2. Oracle 数据库支持

#### 2.1 配置说明
**问题**: `cx-Oracle` 需要 Oracle Instant Client，构建时可能失败

**解决方案**: 
- 将 Oracle 支持设为可选依赖
- 在 `requirements.txt` 中添加了详细的安装说明
- 创建了单独的 `requirements-oracle.txt` 文件
- 创建了完整的配置文档 `docs/ORACLE_SETUP.md`

#### 2.2 启用 Oracle 支持的步骤

**本地开发**:
1. 下载并安装 Oracle Instant Client
2. 设置环境变量 (`LD_LIBRARY_PATH`, `ORACLE_HOME`)
3. 运行: `pip install -r requirements-oracle.txt`

**Docker 环境**:
1. 修改 `Dockerfile.dev` 添加 Instant Client 安装
2. 或使用卷挂载本地 Instant Client
3. 重新构建镜像: `docker-compose build superinsight-api`

详细步骤请参考: `docs/ORACLE_SETUP.md`

### 3. 容器清理

- 删除了所有停止的容器
- 清理了未使用的镜像（回收 426.8KB）
- 清理了未使用的卷（回收 492.6MB）

### 4. 容器重建

所有容器已基于最新代码重新创建：
- ✅ PostgreSQL (superinsight-postgres)
- ✅ Redis (superinsight-redis)
- ✅ Neo4j (superinsight-neo4j)
- ✅ Label Studio (superinsight-label-studio)
- ✅ SuperInsight API (superinsight-api)

## 当前状态

### 运行中的服务
```bash
$ docker ps
CONTAINER ID   IMAGE                             STATUS
c0dfe7dea644   superdata-superinsight-api        Up (healthy)
06820a230e19   heartexlabs/label-studio:latest   Up (healthy)
7a1b22fc41c2   postgres:15-alpine                Up (healthy)
c9e201ec4e19   redis:7-alpine                    Up (healthy)
ae5209f18382   neo4j:5-community                 Up (healthy)
```

### 端口映射
- API Server: http://localhost:8000
- Label Studio: http://localhost:8080
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Neo4j HTTP: http://localhost:7474
- Neo4j Bolt: bolt://localhost:7687

## 后续步骤

### 如果需要启用 Oracle 支持

1. **查看配置文档**:
   ```bash
   cat docs/ORACLE_SETUP.md
   ```

2. **本地开发环境**:
   - 下载 Oracle Instant Client
   - 设置环境变量
   - 安装: `pip install -r requirements-oracle.txt`

3. **Docker 环境**:
   - 参考 `docs/ORACLE_SETUP.md` 中的 Docker 配置方法
   - 选择方法 1（构建时安装）或方法 2（卷挂载）
   - 重新构建镜像

### 验证系统运行

```bash
# 检查 API 健康状态
curl http://localhost:8000/health

# 检查所有容器状态
docker-compose ps

# 查看 API 日志
docker-compose logs -f superinsight-api
```

## 重要文件

- `src/security/models.py` - 包含 AuditLogModel 别名和详细注释
- `requirements.txt` - 主依赖文件（不包含 Oracle）
- `requirements-oracle.txt` - Oracle 可选依赖
- `docs/ORACLE_SETUP.md` - Oracle 配置完整指南
- `Dockerfile.dev` - 开发环境 Docker 配置
- `docker-compose.yml` - 容器编排配置

## 故障排除

### API 容器无法启动
1. 检查日志: `docker-compose logs superinsight-api`
2. 验证数据库连接: 确保 PostgreSQL 容器正常运行
3. 检查环境变量: 查看 `docker-compose.yml` 中的环境配置

### Oracle 连接问题
1. 确认 Instant Client 已正确安装
2. 检查环境变量设置
3. 参考 `docs/ORACLE_SETUP.md` 的故障排除部分

### 容器健康检查失败
1. 等待更长时间（初次启动可能需要 1-2 分钟）
2. 检查数据库是否已完成初始化
3. 查看容器日志排查具体错误

## 联系信息

如有问题，请查看:
- 项目文档: `docs/`
- 技术栈说明: `.kiro/steering/tech.md`
- 项目结构: `.kiro/steering/structure.md`
