# SuperInsight TCB 部署状态报告

## 📅 部署时间


## 🎯 目标环境
- **环境 ID**: cloud2-3gegxdemf86cb89a
- **地域**: ap-shanghai
- **服务名称**: superinsight-api

## ⚠️ 部署状态：需要操作

### 问题描述
```
Error: 云托管当前只能部署到按量付费的环境下，请先在控制台切换计费方式
```

### 原因分析
TCB 云托管（CloudRun）服务只能部署到**按量付费**的环境中，而 cloud2 环境当前是**个人版**（免费版）。

## 🔧 解决方案

### 方案一：切换 cloud2 到按量付费（推荐）

#### 步骤：
1. **访问 TCB 控制台**
   ```
   https://console.cloud.tencent.com/tcb/env/index?envId=cloud2-3gegxdemf86cb89a
   ```

2. **切换计费方式**
   - 点击「环境设置」
   - 找到「计费方式」
   - 点击「切换为按量付费」
   - 确认切换

3. **重新部署**
   ```bash
   tcb framework:deploy
   ```

#### 费用说明：
- **云托管费用**：按实际使用量计费
  - CPU: ~0.055元/核·小时
  - 内存: ~0.032元/GB·小时
  - 流量: ~0.8元/GB
  
- **预估月费用**（2核4GB，1个实例，24小时运行）：
  - CPU: 0.055 × 2 × 24 × 30 = 79.2元
  - 内存: 0.032 × 4 × 24 × 30 = 92.16元
  - 合计: ~171元/月（不含流量）

### 方案二：使用 cloud1 环境

如果 cloud1 已经是按量付费，可以直接部署到 cloud1：

```bash
# 修改 cloudbaserc.json
{
  "envId": "cloud1-7galmfiu70af91a6",
  ...
}

# 部署
tcb framework:deploy
```

### 方案三：创建新的按量付费环境

```bash
# 创建新环境（按量付费）
tcb env:create \
  --name superinsight-prod \
  --region ap-shanghai \
  --pay-mode postpay

# 获取新环境 ID
tcb env:list

# 更新配置并部署
```

## 📋 已完成的工作

### ✅ 配置文件
- [x] cloudbaserc.json - TCB Framework 配置
- [x] deploy/tcb/Dockerfile.api - API 服务 Dockerfile
- [x] deploy-cloud2.sh - 部署脚本
- [x] TCB_DEPLOYMENT_GUIDE.md - 部署指南

### ✅ 验证通过
- [x] TCB CLI 已安登录
- [x] 环境 cloud2 可访问
- [x] 配置文件格式正确
- [x] Dockerfile 路径正确

### ⏳ 待完成
- [ ] 切换环境到按量付费
- [ ] 重新执行部署
- [ ] 验证服务运行
- [ ] 配置访问域名

## 🚀 下一步操作

### 立即操作（推荐）

1. **访问控制台切换计费方式**
   ```
   https://console.cloud.tencent.com/tcb/env/index?envId=cloud2-3gegxdemf86cb89a
   ```

2. **切换完成后，运行部署命令**
   ```bash
   tcb framework:deploy --verbose
   ```

3. **查看部署进度**
   ```bash
   # 查看服务状态
   tcb cloudrun:service:list --env-id cloud2-3gegxdemf86cb89a
   
   # 查看服务详情
   tcb cloudrun:service:describe \
     --service-name superinsight-api \
     --env-id cloud2-3gegxdemf86cb89a
   
   # 查看日志
   tcb cloudrun:service:log \
     --service-name superinsight-api \
     --env-id cloud2-3gegxdemf86cb89a \
     --follow
   ```

## 📊 置

### 服务配置
```json
{
  "serviceName": "superinsight-api",
  "cpu": 2,
  "mem": 4,
  "minNum": 1,
  "maxNum": 5,
  "containerPort": 8000,
  "policyType": "cpu",
  "policyThreshold": 70
}
```

### 环境变量
```json
{
  "ENVIRONMENT": "production",
  "LOG_LEVEL": "INFO",
  "PYTHONUNBUFFERED": "1"
}
```

## 🔍 故障排查

### 如果切换计费方式后仍然失败

1. **检查账户余额**
   ```
   确保腾讯云账户有足够余额
   ```

2. **检查权限**
   ```
   确保账号有云托管服务的权限
   ```

3. **查看详细日志**
   ```bash
   cat /Users/angusl0_18-52-31.log
   ```

4. **联系技术支持**
   ```
   提交工单或联系腾讯云客服
   ```

## 📝 备注

- 部署日志保存在: `/Users/angusliu/cloudbase-framework/logs/2026-01-20_18-52-31.log`
- 配置文件: `cloudbaserc.json`
- Dockerfile: `deploy/tcb/Dockerfile.api`

## 🎯 预期结果

切换到按量付费并成功部署后，你将获得：

1. **API 服务地址**
   - 自动分配的域名
   - 支持 HTTPS
   - 自动扩缩容

2. **访问方式**
   ```
   https://your-service-id.ap-shanghai.app.tcloudbase.com
   ```

3. **管理功能**
   - 实时日志查看
   - 性能监控
   - 自动重启
   - 版本管理

---

**需要帮助？**
/tcb
- 文档: https://cloud.tencent.com/document/product/876
- 工单: https://console.cloud.tencent.com/workorder
