# Label Studio 标注导航修复 - 规范创建总结

**创建日期**: 2026-01-28  
**问题**: "开始标注"和"在新窗口打开"按钮重定向到仪表盘  
**优先级**: P0 (关键)  
**状态**: 规范已创建，待执行

## 问题概述

在任务详情页面，点击以下两个按钮时，页面重定向到仪表盘而不是跳转到 Label Studio 工作台：

1. **"开始标注"按钮** - 应该导航到 iframe 标注页面 (`/tasks/{id}/annotate`)
2. **"在新窗口打开"按钮** - 应该在新窗口打开 Label Studio 认证 URL

## 规范文件位置

所有规范文件已创建在: `.kiro/specs/label-studio-annotation-navigation-fix/`

### 文件清单

| 文件 | 描述 | 大小 |
|------|------|------|
| `README.md` | 规范总结和快速开始指南 | ~5KB |
| `requirements.md` | 需求文档（问题描述、用户故事、验收标准） | ~8KB |
| `design.md` | 设计文档（问题分析、解决方案、测试策略） | ~12KB |
| `tasks.md` | 任务分解（5 个 Phase，17 个任务） | ~10KB |

**总计**: 4 个文件，约 35KB

## 规范内容概览

### 1. README.md - 快速开始

**包含内容**:
- 问题概述
- 规范文件说明
- 快速开始步骤
- 关键代码位置
- 调试技巧
- 常见问题

**适合人群**: 所有开发人员

### 2. requirements.md - 需求文档

**包含内容**:
- 问题描述和预期行为
- 2 个用户故事
  - 标注员开始标注任务
  - 在新窗口打开 Label Studio
- 根本原因分析（4 个可能原因）
- 调查步骤
- 非功能需求
- 验收标准
- 风险评估

**关键指标**:
- 2 个用户故事
- 4 个可能的根本原因
- 6 个验收标准
- 3 个风险项

### 3. design.md - 设计文档

**包含内容**:
- 问题流程图（Mermaid 图表）
- 根本原因分析
- 调查清单
- 前端修复方案
  - 改进错误处理
  - 添加调试日志
  - 验证路由配置
- 后端修复方案
  - 验证 API 端点
  - 改进错误响应
  - 添加健康检查
- 集成测试设计
- 正确性属性（5 个）
- 风险缓解措施

**关键设计**:
- 统一的错误处理函数
- 详细的调试日志
- 改进的 API 错误响应
- 健康检查端点
- 5 个正确性属性

### 4. tasks.md - 任务分解

**包含内容**:
- 5 个 Phase 的任务分解
  - Phase 1: 问题诊断 (2-3h)
  - Phase 2: 前端修复 (4-6h)
  - Phase 3: 后端修复 (4-6h)
  - Phase 4: 集成测试 (3-4h)
  - Phase 5: 验证和文档 (2-3h)
- 17 个具体任务
- 每个任务的子任务和验收标准
- 时间估计（总计 15-22 小时）
- 依赖关系图
- 优先级矩阵
- 风险和缓解措施

**任务统计**:
- 总任务数: 17
- 总子任务数: 40+
- 预计工时: 15-22 小时
- 优先级: P0 (3) + P1 (10) + P2 (4)

## 关键代码位置

### 前端代码

**主要文件**:
- `frontend/src/pages/Tasks/TaskDetail.tsx` (第 90-260 行)
  - `handleStartAnnotation()` - "开始标注"按钮处理
  - `handleOpenInNewWindow()` - "在新窗口打开"按钮处理

- `frontend/src/services/labelStudioService.ts`
  - `ensureProject()` - 创建或获取项目
  - `validateProject()` - 验证项目存在性
  - `getAuthUrl()` - 生成认证 URL

- `frontend/src/constants/api.ts`
  - `LABEL_STUDIO.ENSURE_PROJECT`
  - `LABEL_STUDIO.VALIDATE_PROJECT`
  - `LABEL_STUDIO.AUTH_URL`

### 后端代码

**主要文件**:
- `src/api/label_studio_api.py` (第 400-830 行)
  - `ensure_project_exists()` - POST /api/label-studio/projects/ensure
  - `validate_project()` - GET /api/label-studio/projects/{id}/validate
  - `get_authenticated_url()` - GET /api/label-studio/projects/{id}/auth-url

- `src/label_studio/integration.py`
  - `ensure_project_exists()` - 项目创建/获取逻辑
  - `validate_project()` - 项目验证逻辑
  - `generate_authenticated_url()` - 认证 URL 生成逻辑

## 执行步骤

### 第一步: 诊断问题 (2-3 小时)

1. **收集诊断信息** (1h)
   - 打开浏览器开发者工具 (F12)
   - 点击"开始标注"按钮，查看控制台错误和网络请求
   - 点击"在新窗口打开"按钮，查看控制台错误和网络请求
   - 记录 API 响应状态码和内容
   - 检查后端日志

2. **分析问题根源** (1h)
   - 查看前端代码执行流程
   - 查看后端 API 实现
   - 查看认证中间件
   - 查看路由配置

3. **创建问题报告** (0.5h)
   - 记录问题现象
   - 记录根本原因
   - 记录影响范围

### 第二步: 执行修复 (13-19 小时)

1. **前端修复** (4-6h)
   - 改进错误处理
   - 添加调试日志
   - 验证路由配置
   - 编写单元测试

2. **后端修复** (4-6h)
   - 验证 API 端点
   - 改进错误响应
   - 添加健康检查
   - 编写单元测试

3. **集成测试** (3-4h)
   - 前端集成测试
   - 后端集成测试
   - E2E 测试

4. **验证和文档** (2-3h)
   - 手动测试
   - 更新文档
   - 部署验证

## 调试技巧

### 前端调试

```bash
# 1. 打开浏览器开发者工具
F12

# 2. 查看控制台
- 查看是否有 JavaScript 错误
- 查看日志输出

# 3. 查看网络标签
- 点击"开始标注"按钮
- 查看 /api/label-studio/projects/ensure 请求
- 查看响应状态码（应该是 200）
- 查看响应内容（应该包含 project_id）

# 4. 添加断点
- 在 handleStartAnnotation 中添加断点
- 在 handleOpenInNewWindow 中添加断点
- 逐步执行代码
```

### 后端调试

```bash
# 1. 查看后端日志
docker compose logs -f app

# 2. 测试 API 端点
curl -X POST http://localhost:8000/api/label-studio/projects/ensure \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_name": "Test Project",
    "annotation_type": "text_classification"
  }'

# 3. 检查数据库
# 查看任务是否正确保存了 label_studio_project_id
```

## 预期结果

修复完成后，应该实现以下功能：

1. **"开始标注"按钮**
   - ✅ 点击后导航到 `/tasks/{id}/annotate` 页面
   - ✅ Label Studio iframe 正确加载
   - ✅ 项目不存在时自动创建
   - ✅ 错误时显示清晰的错误提示

2. **"在新窗口打开"按钮**
   - ✅ 点击后在新窗口打开 Label Studio
   - ✅ 用户已自动认证
   - ✅ 界面语言与用户当前语言一致
   - ✅ 项目不存在时自动创建
   - ✅ 错误时显示清晰的错误提示

## 相关文档

- [Label Studio 企业版 Workspace 扩展设计](../../.kiro/specs/label-studio-enterprise-workspace/design.md)
- [Label Studio iframe 集成规范](../../.kiro/specs/label-studio-iframe-integration/design.md)
- [技术常见问题解决日志](./技术常见问题解决日志.md)
- [Admin 子页面导航重定向问题](./技术常见问题解决日志.md#2026-01-28-admin-子页面导航重定向到-dashboard)

## 规范索引

本规范已添加到规范索引中：
- 位置: `.kiro/specs/INDEX.md`
- 分类: 🐛 Bug 修复和优化
- 链接: [Label Studio 标注导航修复](../../.kiro/specs/label-studio-annotation-navigation-fix/README.md)

## 下一步

1. **阅读规范** - 详细阅读 `.kiro/specs/label-studio-annotation-navigation-fix/` 中的所有文档
2. **执行诊断** - 按照 Phase 1 的步骤诊断问题
3. **执行修复** - 按照 Phase 2-5 的步骤执行修复
4. **更新规范** - 记录修复过程和结果

## 联系方式

如有问题或需要帮助，请：
1. 查看规范中的相关部分
2. 查看相关代码文件
3. 查看后端日志和浏览器控制台
4. 参考相关文档

---

**创建者**: Kiro  
**创建日期**: 2026-01-28  
**规范位置**: `.kiro/specs/label-studio-annotation-navigation-fix/`
