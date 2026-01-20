# SuperInsight TCB 部署状态

## 📋 当前状态

### ✅ 已完成
- [x] TCB CLI 已安装并登录
- [x] 已选择目标环境：cloud2-3gegxdemf86cb89a
- [x] 部署脚本已创建
- [x] Dockerfile 配置完整

### ⚠️ 待完成
- [ ] Docker 需要安装
- [ ] 构建镜像
- [ ] 推送镜像到 TCB
- [ ] 部署服务

## 🔧 下一步操作

### 1. 安装 Docker

#### macOS
```bash
# 方式一：使用 Homebrew
brew install --cask docker

# 方式二：下载 Docker Desktop
# 访问 https://www.docker.com/products/docker-desktop
# 下载并安装 Docker Desktop for Mac
```

安装后：
1. 启动 Docker Desktop 应用
2. 等待 Docker 完全启动（状态栏图标变绿）
3. 验证安装：`docker --version`

### 2. 部署到 cloud2

安装 Docker 后，运行部署脚本：

```bash
# 一键部署到 cloud2
./deploy-cloud2.sh
```

脚本会自动：
1. ✅ 构建 Docker 镜像
2. ✅ 登录 TCB 容器镜像仓库
3. ✅ 推送镜像到 TCB
4. ✅ 部署服务到 CloudRun

## 📊 部署配置

### 目标环境
- **环境 ID**: cloud2-3gegxdemf86cb89a
- **环境名称**: cloud2
- **地域**: 根据环境配置

### 服务配置
- **服务名称**: superinsight-api
- **镜像**: superinsight-api:latest
- **CPU**: 2 核
- **内存**: 4 GB
- **最小实例**: 1
- **最大实例**: 5
- **容器端口**: 8000

### 镜像配置
- **基础镜像**: python:3.9-slim
- **Dockerfile**: deploy/tcb/Dockerfile.api
- **包含组件**:
  - FastAPI 后端
  - PostgreSQL 客户端
  - 健康检查
  - 非 root 用户运行

## 🚀 快速部署流程

### 完整流程（首次部署）

```bash
# 1. 确保 Docker 已安装并运行
docker --version

# 2. 确保 TCB CLI 已登录
tcb env:list

# 3. 运行部署脚本
./deploy-cloud2.sh

# 4. 等待部署完成（约 5-10 分钟）
# - 构建镜像: 2-3 分钟
# - 推送镜像: 2-3 分钟
# - 部署服务: 2-3 分钟

# 5. 查看服务状态
tcb cloudrun:service:describe \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a

# 6. 查看服务日志
tcb cloudrun:service:log \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a \
  --follow
```

### 更新部署（后续更新）

```bash
# 代码更新后，重新部署
./deploy-cloud2.sh

# 脚本会自动检测服务已存在，执行更新操作
```

## 📝 部署后配置

### 1. 配置环境变量

在 TCB 控制台配置以下环境变量：

```bash
# 数据库配置
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=5432
POSTGRES_DB=superinsight
POSTGRES_USER=superinsight
POSTGRES_PASSWORD=your_password

# Redis 配置
REDIS_HOST=your_redis_host
REDIS_PORT=6379

# 安全配置
JWT_SECRET_KEY=your_jwt_secret
SECRET_KEY=your_secret_key

# LLM 配置（可选）
HUNYUAN_API_KEY=your_api_key
HUNYUAN_SECRET_KEY=your_secret_key
```

### 2. 配置自定义域名

1. 在 TCB 控制台进入 CloudRun 服务
2. 选择 superinsight-api 服务
3. 点击"域名管理"
4. 添加自定义域名
5. 配置 DNS 解析

### 3. 配置 HTTPS

1. 在域名管理中上传 SSL 证书
2. 或使用腾讯云免费证书
3. 启用 HTTPS 访问

### 4. 配置数据库

推荐使用腾讯云数据库：

```bash
# TencentDB for PostgreSQL
# 1. 在腾讯云控制台创建 PostgreSQL 实例
# 2. 配置安全组，允许 CloudRun 访问
# 3. 记录数据库连接信息
# 4. 在 CloudRun 环境变量中配置
```

### 5. 配置对象存储

```bash
# 使用腾讯云 COS
# 1. 创建 COS 存储桶
# 2. 配置访问权限
# 3. 在环境变量中配置 COS 信息
```

## 🔍 验证部署

### 检查服务状态

```bash
# 查看服务列表
tcb cloudrun:service:list --env-id cloud2-3gegxdemf86cb89a

# 查看服务详情
tcb cloudrun:service:describe \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a

# 查看服务指标
tcb cloudrun:service:metrics \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a
```

### 测试 API

```bash
# 获取服务访问地址
SERVICE_URL=$(tcb cloudrun:service:describe \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a \
  | grep -o 'https://[^"]*' | head -1)

# 测试健康检查
curl $SERVICE_URL/health

# 测试 API 文档
curl $SERVICE_URL/docs
```

## 📊 监控和日志

### 实时日志

```bash
# 查看实时日志
tcb cloudrun:service:log \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a \
  --follow

# 查看最近 100 行日志
tcb cloudrun:service:log \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a \
  --tail 100
```

### 性能监控

在 TCB 控制台查看：
- CPU 使用率
- 内存使用率
- 请求量
- 响应时间
- 错误率

## 🔧 故障排查

### 服务无法启动

```bash
# 1. 查看日志
tcb cloudrun:service:log \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a

# 2. 检查镜像
docker pull ccr.ccs.tencentyun.com/tcb_cloud2-3gegxdemf86cb89a/superinsight-api:latest

# 3. 本地测试镜像
docker run -p 8000:8000 superinsight-api:latest
```

### 性能问题

```bash
# 增加实例数量
tcb cloudrun:service:update \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a \
  --min-num 2 \
  --max-num 10

# 升级实例规格
tcb cloudrun:service:update \
  --service-name superinsight-api \
  --env-id cloud2-3gegxdemf86cb89a \
  --cpu 4 \
  --mem 8
```

## 💰 成本估算

### 基础配置（2核4GB，1-5实例）

- **计算资源**: 约 ¥0.5-2.5/小时
- **流量费用**: 约 ¥0.8/GB
- **存储费用**: 根据使用量

### 优化建议

1. 使用按量计费，避免资源浪费
2. 配置合理的自动扩缩容策略
3. 使用 CDN 减少流量成本
4. 定期清理不用的镜像和日志

## 📚 相关资源

- [TCB 控制台](https://console.cloud.tencent.com/tcb)
- [CloudRun 文档](https://cloud.tencent.com/document/product/1243)
- [TCB CLI 文档](https://docs.cloudbase.net/cli/intro.html)
- [Docker 文档](https://docs.docker.com/)

## ✅ 检查清单

### 部署前
- [ ] Docker 已安装并运行
- [ ] TCB CLI 已登录
- [ ] 代码已提交到 Git
- [ ] 环境变量已准备

### 部署中
- [ ] 镜像构建成功
- [ ] 镜像推送成功
- [ ] 服务创建/更新成功

### 部署后
- [ ] 服务正常运行
- [ ] 健康检查通过
- [ ] API 可以访问
- [ ] 日志正常输出
- [ ] 监控指标正常

## 🎯 当前任务

**立即执行**：
1. 安装 Docker Desktop for Mac
2. 启动 Docker
3. 运行 `./deploy-cloud2.sh`

**预计时间**：
- Docker 安装: 5-10 分钟
- 部署过程: 5-10 分钟
- 总计: 10-20 分钟

---

**准备好后，运行部署脚本即可完成部署！** 🚀
