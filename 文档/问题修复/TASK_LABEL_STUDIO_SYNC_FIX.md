# 任务与 Label Studio 同步修复方案

## 问题分析

### 问题 1: 平台与 Label Studio 认证
- **状态**: ✅ 已配置 API Token 认证
- **配置**: `.env` 文件中已设置 `LABEL_STUDIO_API_TOKEN`
- **认证方法**: API Token (Community Edition 支持)

### 问题 2: 任务与 Label Studio 同步
- **状态**: ❌ 未实现
- **问题**: 创建任务时没有自动在 Label Studio 创建项目
- **需要**: 实现任务创建时自动同步到 Label Studio

## 解决方案

### 1. 认证测试
首先测试 Label Studio 连接和认证是否正常：

```bash
# 测试 Label Studio API 连接
curl -H "Authorization: Token YOUR_LABEL_STUDIO_API_TOKEN_HERE" \
  http://localhost:8080/api/current-user/whoami/
```

### 2. 任务同步实现

#### 2.1 更新任务创建 API
在 `src/api/tasks.py` 的 `create_task` 函数中添加 Label Studio 项目创建逻辑。

#### 2.2 添加同步端点
创建新的 API 端点用于手动同步现有任务到 Label Studio。

#### 2.3 前端集成
更新前端任务创建表单，显示 Label Studio 同步状态。

## 实现步骤

### 步骤 1: 更新后端任务创建逻辑
- 在任务创建时自动创建 Label Studio 项目
- 存储 Label Studio 项目 ID 到任务记录
- 处理创建失败的情况

### 步骤 2: 添加同步状态跟踪
- 添加同步状态字段（pending, syncing, synced, failed）
- 记录同步时间和错误信息
- 提供重试机制

### 步骤 3: 前端显示同步状态
- 在任务列表显示 Label Studio 同步状态
- 提供手动同步按钮
- 显示 Label Studio 项目链接

## 测试计划

### 1. 认证测试
- [ ] 测试 API Token 认证
- [ ] 测试 Label Studio 连接
- [ ] 验证权限正常

### 2. 同步测试
- [ ] 创建新任务，验证自动创建 Label Studio 项目
- [ ] 检查项目 ID 正确存储
- [ ] 验证项目配置正确
- [ ] 测试同步失败重试

### 3. 集成测试
- [ ] 测试"开始标注"按钮
- [ ] 测试"在新窗口打开"按钮
- [ ] 验证语言参数正确传递
- [ ] 测试认证 URL 生成

## 预期结果

1. **认证正常**: 平台可以成功连接 Label Studio API
2. **自动同步**: 创建任务时自动在 Label Studio 创建项目
3. **状态跟踪**: 可以查看同步状态和错误信息
4. **手动重试**: 同步失败时可以手动重试
5. **按钮正常**: "开始标注"和"在新窗口打开"按钮正常工作

## 文件修改清单

- [x] `src/api/tasks.py` - 添加 Label Studio 同步逻辑
- [ ] `src/api/label_studio_sync.py` - 新建同步服务
- [ ] `frontend/src/types/task.ts` - 添加同步状态类型
- [ ] `frontend/src/pages/Tasks/TaskList.tsx` - 显示同步状态
- [ ] `frontend/src/pages/Tasks/TaskDetail.tsx` - 添加同步按钮

## 下一步行动

1. 实现任务创建时的 Label Studio 项目创建
2. 添加同步状态跟踪
3. 更新前端显示同步状态
4. 测试完整流程
