# SuperInsight TCB 云托管部署指南

## 📋 部署方式

SuperInsight 支持通过腾讯云 CloudBase (TCB) 云托管进行部署，有两种方式：

### 方式一：从 GitHub 拉取部署（推荐）

#### 步骤：

1. **登录 TCB 控制台**
   ```
   https://console.cloud.tencent.com/tcb
   ```

2. **进入云托管**
   - 选择环境（需要是按量付费环境）
   - 点击「云托管」→「新建服务」

3. **配置服务**
   - **服务名称**: `superinsight-api`
   - **镜像来源**: 选择「代码仓库」
   - **代码仓库**: 
     - 平台：GitHub
     - 仓库：`Angus1976/superinsight1225`
     - 分支：`main`
     - Dockerfile 路径：`./Dockerfile`

4. **配置资源**
   - **CPU**: 2 核
   - **内存**: 4 GB
   - **最小实例数**: 1
   - **最大实例数**: 5
   - **端口**: 8000

5. **配置环境变量**（可选）
   ```
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   PYTHONUNBUFFERED=1
   ```

6. **点击「部署」**
   - TCB 会自动从 GitHub 拉取代码
   - 使用根目录的 Dockerfile 构建镜像
   - 部署到云托管服务

### 方式二：本地上传部署

#### 步骤：

1. **准备代码**
   ```bash
   # 确保代码是最新的
   git pull origin main
   ```

2. **登录 TCB 控制台**
   ```
   https://console.cloud.tencent.com/tcb
   ```

3. **进入云托管**
   - 选择环境
   - 点击「云托管」→「新建服务」

4. **配置服务**
   - **服务名称**: `superinsight-api`
   - **镜像来源**: 选择「本地代码」
   - **上传方式**: 
     - 选择「上传文件夹」
     - 选择项目根目录
     - Dockerfile 路径：`./Dockerfile`

5. **配置资源**（同方式一）

6. **点击「部署」**
   - TCB 会上传代码到云端
   - 使用 Dockerfile 构建镜像
   - 部署到云托管服务

### 方式三：使用 TCB CLI 部署

#### 前置要求：
```bash
# 安装 TCB CLI
npm install -g @cloudbase/cli

# 登录
tcb login
```

#### 部署命令：
```bash
# 使用 TCB Framework 部署
tcb framework:deploy

# 或使用云托管命令
tcb cloudrun:deploy \
  --service-name superinsight-api \
  --env-id your-env-id \
  --dockerfile ./Dockerfile
```

## 📁 项目结构

```
superinsight1225/
├── Dockerfile              # TCB 部署使用的 Dockerfile（根目录）
├── .dockerignore          # Docker 构建忽略文件
├── cloudbaserc.json       # TCB Framework 配置
├── requirements.txt       # Python 依赖
├── main.py               # 应用入口
├── src/                  # 源代码
│   ├── app.py           # FastAPI 应用
│   ├── api/             # API 路由
│   ├── models/          # 数据模型
│   ├── services/        # 业务逻辑
│   └── ...
├── alembic/             # 数据库迁移
└── alembic.ini          # Alembic 配置
```

## 🔧 Dockerfile 说明

根目录的 `Dockerfile` 包含：

1. **基础镜像**: `python:3.9-slim`
2. **系统依赖**: gcc, g++, libpq-dev, curl 等
3. **Python 依赖**: 从 requirements.txt 安装
4. **应用代码**: 复制 src/, main.py 等
5. **安全配置**: 使用非 root 用户运行
6. **健康检查**: 自动检查服务健康状态
7. **端口暴露**: 8000

## 🌐 环境变量配置

### 必需变量（在 TCB 控制台配置）

```bash
# 数据库配置（如使用外部数据库）
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=5432
POSTGRES_DB=superinsight
POSTGRES_USER=superinsight
POSTGRES_PASSWORD=your_password

# Redis 配置（如使用外部 Redis）
REDIS_HOST=your_redis_host
REDIS_PORT=6379

# 安全配置
JWT_SECRET_KEY=your_jwt_secret_key
SECRET_KEY=your_secret_key

# 应用配置
ENVIRONMENT=production
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

### 可选变量

```bash
# LLM 配置
HUNYUAN_API_KEY=your_api_key
HUNYUAN_SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_key

# COS 存储
COS_REGION=ap-shanghai
COS_BUCKET=your_bucket
COS_SECRET_ID=your_secret_id
COS_SECRET_KEY=your_secret_key
```

## 📊 资源配置建议

### 开发/测试环境
- **CPU**: 1-2 核
- **内存**: 2-4 GB
- **实例数**: 1-2

### 生产环境
- **CPU**: 2-4 核
- **内存**: 4-8 GB
- **实例数**: 2-10（自动扩缩容）

## 🔍 部署后验证

### 1. 检查服务状态

在 TCB 控制台查看：
- 服务是否正常运行
- 实例数量
- CPU 和内存使用率

### 2. 访问健康检查

```bash
curl https://your-service-url/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-20T10:00:00Z"
}
```

### 3. 访问 API 文档

```
https://your-service-url/docs
```

### 4. 查看日志

在 TCB 控制台：
- 点击服务
- 选择「日志」标签
- 查看实时日志

或使用 CLI：
```bash
tcb cloudrun:service:log \
  --service-name superinsight-api \
  --env-id your-env-id \
  --follow
```

## 🚨 常见问题

### 1. 构建失败

**问题**: Dockerfile 构建失败

**解决**:
- 检查 Dockerfile 语法
- 确保 requirements.txt 存在
- 查看构建日志

### 2. 服务无法启动

**问题**: 服务部署成功但无法启动

**解决**:
- 检查环境变量配置
- 查看服务日志
- 确认端口配置正确（8000）

### 3. 健康检查失败

**问题**: 健康检查一直失败

**解决**:
- 确认 `/health` 端点可访问
- 增加启动延迟时间（initialDelaySeconds）
- 检查应用启动日志

### 4. 内存不足

**问题**: 服务因内存不足被杀死

**解决**:
- 增加内存配置（4GB → 8GB）
- 优化代码内存使用
- 检查是否有内存泄漏

## 💰 费用估算

### 基础配置（2核4GB，1实例，24小时运行）

- **CPU**: 0.055元/核·小时 × 2 × 24 × 30 = 79.2元/月
- **内存**: 0.032元/GB·小时 × 4 × 24 × 30 = 92.16元/月
- **流量**: 0.8元/GB（按实际使用）
- **合计**: ~171元/月（不含流量）

### 优化建议

1. **使用自动扩缩容**: 低峰期自动缩容到 0 实例
2. **配置 CDN**: 减少流量费用
3. **使用预留实例**: 长期运行可节省成本

## 📚 相关文档

- [TCB 云托管文档](https://cloud.tencent.com/document/product/1243)
- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [TCB CLI 文档](https://docs.cloudbase.net/cli/intro.html)

## 🆘 获取帮助

- **TCB 控制台**: https://console.cloud.tencent.com/tcb
- **技术支持**: 提交工单
- **GitHub Issues**: https://github.com/Angus1976/superinsight1225/issues

---

**准备好了？开始部署吧！** 🚀
