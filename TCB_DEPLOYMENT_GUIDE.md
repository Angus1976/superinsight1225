# SuperInsight 腾讯云 TCB 部署指南

## 📋 前置要求

### 1. 腾讯云账号
- 已注册腾讯云账号
- 已开通云开发 CloudBase 服务
- 已完成实名认证

### 2. 本地环境
- Node.js 14+ 
- Docker 20.10+
- TCB CLI 已安装

### 3. 安装 TCB CLI

```bash
# 使用 npm 安装
npm install -g @cloudbase/cli

# 验证安装
tcb --version
```

## 🚀 快速部署

### 方式一：使用自动化脚本（推荐）

```bash
# 1. 赋予执行权限
chmod +x deploy-to-tcb.sh

# 2. 运行部署脚本
./deploy-to-tcb.sh
```

脚本会自动：
- ✅ 检查 TCB CLI 安装
- ✅ 登录腾讯云账号
- ✅ 选择或创建环境
- ✅ 配置环境变量
- ✅ 构建 Docker 镜像
- ✅ 推送镜像到 TCB
- ✅ 部署服务到 CloudRun
- ✅ 配置数据库和存储

### 方式二：手动部署

#### 步骤 1: 登录 TCB

```bash
# 登录腾讯云
tcb login

# 查看环境列表
tcb env:list
```

#### 步骤 2: 创建或选择环境

```bash
# 创建新环境
tcb env:create --name superinsight-prod --region ap-shanghai

# 或使用现有环境
export TCB_ENV_ID=your-env-id
```

#### 步骤 3: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env.tcb

# 编辑配置文件
nano .env.tcb
```

必须配置的变量：
```bash
TCB_ENV_ID=your_env_id
TCB_REGION=ap-shanghai
POSTGRES_PASSWORD=strong_password
JWT_SECRET_KEY=random_secret_key
HUNYUAN_API_KEY=your_api_key
COS_BUCKET=your_bucket_name
```

#### 步骤 4: 构建 Docker 镜像

```bash
# 构建 API 服务镜像
docker build -t superinsight-api:latest -f deploy/tcb/Dockerfile.api .

# 或构建完整栈镜像
docker build -t superinsight-fullstack:latest -f deploy/tcb/Dockerfile.fullstack .
```

#### 步骤 5: 推送镜像到 TCB

```bash
# 登录到 TCB 容器镜像仓库
tcb cloudrun:login

# 标记镜像
docker tag superinsight-api:latest ccr.ccs.tencentyun.com/tcb_${TCB_ENV_ID}/superinsight-api:latest

# 推送镜像
docker push ccr.ccs.tencentyun.com/tcb_${TCB_ENV_ID}/superinsight-api:latest
```

#### 步骤 6: 部署服务

```bash
# 创建 CloudRun 服务
tcb cloudrun:service:create \
  --env-id $TCB_ENV_ID \
  --service-name superinsight-api \
  --image ccr.ccs.tencentyun.com/tcb_${TCB_ENV_ID}/superinsight-api:latest \
  --cpu 2 \
  --mem 4 \
  --min-num 1 \
  --max-num 10 \
  --container-port 8000
```

## 🔧 配置说明

### 服务配置

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| CPU | CPU 核数 | 2-4 核 |
| 内存 | 内存大小 | 4-8 GB |
| 最小实例数 | 最少运行实例 | 1 |
| 最大实例数 | 最多运行实例 | 10 |
| 容器端口 | 服务监听端口 | 8000 |

### 环境变量

#### 必需变量

```bash
# TCB 配置
TCB_ENV_ID=your_env_id
TCB_REGION=ap-shanghai

# 数据库配置
POSTGRES_USER=superinsight
POSTGRES_PASSWORD=strong_password
POSTGRES_DB=superinsight

# 安全配置
SECRET_KEY=random_secret_key
JWT_SECRET_KEY=jwt_secret_key

# 腾讯云服务
HUNYUAN_API_KEY=your_api_key
HUNYUAN_SECRET_KEY=your_secret_key

# COS 存储
COS_REGION=ap-shanghai
COS_BUCKET=your_bucket_name
COS_SECRET_ID=your_secret_id
COS_SECRET_KEY=your_secret_key
```

#### 可选变量

```bash
# Label Studio
LABEL_STUDIO_USERNAME=admin@superinsight.com
LABEL_STUDIO_PASSWORD=admin_password

# 日志级别
LOG_LEVEL=INFO

# 性能配置
APP_WORKERS=4
```

## 📊 资源配置

### 数据库

推荐使用腾讯云数据库 TencentDB for PostgreSQL：

1. 在腾讯云控制台创建 PostgreSQL 实例
2. 选择规格：2核4GB 起步
3. 配置白名单，允许 CloudRun 访问
4. 记录数据库连接信息

### 对象存储

使用腾讯云对象存储 COS：

```bash
# 创建存储桶
tcb storage:create-bucket \
  --env-id $TCB_ENV_ID \
  --bucket superinsight-data \
  --region ap-shanghai

# 配置 CORS
tcb storage:set-cors \
  --env-id $TCB_ENV_ID \
  --bucket superinsight-data
```

### CDN 加速（可选）

为静态资源配置 CDN：

1. 在腾讯云控制台开通 CDN
2. 添加加速域名
3. 配置源站为 COS 存储桶
4. 配置 HTTPS 证书

## 🔐 安全配置

### 1. 网络安全

```bash
# 配置安全组规则
# 仅允许必要的端口访问
- 80/443 (HTTP/HTTPS)
- 8000 (API)
- 8080 (Label Studio)
```

### 2. 访问控制

```bash
# 配置 IAM 角色和权限
# 最小权限原则
```

### 3. 数据加密

```bash
# 启用数据库加密
# 启用 COS 服务端加密
# 配置 HTTPS 证书
```

### 4. 密钥管理

```bash
# 使用腾讯云密钥管理系统 KMS
# 定期轮换密钥
# 不在代码中硬编码密钥
```

## 📈 监控和日志

### 查看服务状态

```bash
# 查看服务列表
tcb cloudrun:service:list --env-id $TCB_ENV_ID

# 查看服务详情
tcb cloudrun:service:describe \
  --service-name superinsight-api \
  --env-id $TCB_ENV_ID

# 查看服务指标
tcb cloudrun:service:metrics \
  --service-name superinsight-api \
  --env-id $TCB_ENV_ID
```

### 查看日志

```bash
# 实时查看日志
tcb cloudrun:service:log \
  --service-name superinsight-api \
  --env-id $TCB_ENV_ID \
  --follow

# 查看历史日志
tcb cloudrun:service:log \
  --service-name superinsight-api \
  --env-id $TCB_ENV_ID \
  --start-time "2026-01-20 00:00:00" \
  --end-time "2026-01-20 23:59:59"
```

### 配置告警

在腾讯云控制台配置告警策略：

1. CPU 使用率 > 80%
2. 内存使用率 > 80%
3. 请求错误率 > 5%
4. 响应时间 > 3s

## 🔄 更新和回滚

### 更新服务

```bash
# 1. 构建新镜像
docker build -t superinsight-api:v2 -f deploy/tcb/Dockerfile.api .

# 2. 推送新镜像
docker tag superinsight-api:v2 ccr.ccs.tencentyun.com/tcb_${TCB_ENV_ID}/superinsight-api:v2
docker push ccr.ccs.tencentyun.com/tcb_${TCB_ENV_ID}/superinsight-api:v2

# 3. 更新服务
tcb cloudrun:service:update \
  --service-name superinsight-api \
  --env-id $TCB_ENV_ID \
  --image ccr.ccs.tencentyun.com/tcb_${TCB_ENV_ID}/superinsight-api:v2
```

### 回滚服务

```bash
# 回滚到上一个版本
tcb cloudrun:service:rollback \
  --service-name superinsight-api \
  --env-id $TCB_ENV_ID \
  --version previous
```

## 💰 成本优化

### 1. 按需扩缩容

```bash
# 配置自动扩缩容策略
- 最小实例数: 1（低峰期）
- 最大实例数: 10（高峰期）
- CPU 阈值: 70%
```

### 2. 使用预留实例

对于稳定流量，购买预留实例可节省成本。

### 3. 优化镜像大小

```bash
# 使用多阶段构建
# 清理不必要的文件
# 使用 alpine 基础镜像
```

### 4. 配置 CDN

静态资源使用 CDN 加速，减少源站流量。

## 🔍 故障排查

### 服务无法启动

```bash
# 1. 查看服务日志
tcb cloudrun:service:log --service-name superinsight-api --env-id $TCB_ENV_ID

# 2. 检查环境变量配置
tcb cloudrun:service:describe --service-name superinsight-api --env-id $TCB_ENV_ID

# 3. 检查镜像是否正确
docker pull ccr.ccs.tencentyun.com/tcb_${TCB_ENV_ID}/superinsight-api:latest
```

### 数据库连接失败

```bash
# 1. 检查数据库实例状态
# 2. 检查安全组配置
# 3. 检查数据库连接字符串
# 4. 测试网络连通性
```

### 性能问题

```bash
# 1. 查看服务指标
tcb cloudrun:service:metrics --service-name superinsight-api --env-id $TCB_ENV_ID

# 2. 增加实例数量
tcb cloudrun:service:update \
  --service-name superinsight-api \
  --env-id $TCB_ENV_ID \
  --min-num 2 \
  --max-num 20

# 3. 升级实例规格
tcb cloudrun:service:update \
  --service-name superinsight-api \
  --env-id $TCB_ENV_ID \
  --cpu 4 \
  --mem 8
```

## 📚 相关资源

- [腾讯云 CloudBase 文档](https://cloud.tencent.com/document/product/876)
- [TCB CLI 文档](https://docs.cloudbase.net/cli/intro.html)
- [CloudRun 文档](https://cloud.tencent.com/document/product/1243)
- [TencentDB for PostgreSQL](https://cloud.tencent.com/document/product/409)
- [对象存储 COS](https://cloud.tencent.com/document/product/436)

## 🆘 获取帮助

- **TCB 控制台**: https://console.cloud.tencent.com/tcb
- **技术支持**: 提交工单
- **社区论坛**: https://cloud.tencent.com/developer/ask

## ✅ 部署检查清单

部署前检查：
- [ ] TCB CLI 已安装并登录
- [ ] 环境变量已配置
- [ ] Docker 镜像已构建
- [ ] 数据库实例已创建
- [ ] COS 存储桶已创建
- [ ] 安全组规则已配置

部署后验证：
- [ ] 服务正常运行
- [ ] 健康检查通过
- [ ] API 可以访问
- [ ] 数据库连接正常
- [ ] 日志正常输出
- [ ] 监控指标正常

## 🎉 完成！

现在你可以通过 TCB 部署 SuperInsight 平台了！

祝部署顺利！🚀
