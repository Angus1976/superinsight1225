# Data Lifecycle Quick Actions 反向更新总结

**日期**: 2026-03-10  
**相关 Spec**: 
- 主 Spec: `.kiro/specs/data-lifecycle-management/`
- Bugfix Spec: `.kiro/specs/data-lifecycle-quick-actions-fix/`

## 更新概述

根据 `data-lifecycle-quick-actions-fix` bugfix spec 的发现，将快速操作功能和灵活数据流的需求反向更新到主 spec `data-lifecycle-management` 中。

## 已完成的更新

### 1. Requirements.md 更新

#### 1.1 Requirement 11 - 数据流可视化界面
**新增内容**:
- 添加快速操作按钮需求（6个按钮）
- 点击按钮打开相应模态框
- 支持灵活数据流，允许直接跳转到任何下游阶段

#### 1.2 Requirement 12 - 临时数据管理界面
**新增内容**:
- 添加创建临时数据快速操作按钮
- 点击按钮打开创建模态框

#### 1.3 Requirement 13 - 样本库搜索界面
**新增内容**:
- 添加"添加到样本库"快速操作按钮
- 支持从任何阶段选择数据添加到样本库
- 支持灵活数据流，不强制顺序流程

#### 1.4 Requirement 14 - 标注任务管理界面
**新增内容**:
- 添加创建标注任务快速操作按钮
- 支持从任何可用阶段选择数据作为任务数据源
- 支持灵活数据源选择

#### 1.5 Requirement 15 - 增强任务监控界面
**新增内容**:
- 添加创建增强任务快速操作按钮
- 支持从任何可用阶段选择数据作为增强源
- 支持灵活数据源选择

#### 1.6 Requirement 16 - AI 试算配置和执行界面
**新增内容**:
- 添加创建 AI 试算快速操作按钮
- 支持从 5 个生命周期阶段中的任何一个选择数据
- 支持灵活数据源选择，不强制顺序流程

#### 1.7 新增 Requirement 26 - 快速操作和灵活数据流
**完整新需求**，包含 13 个验收标准：
1. 提供 6 个快速操作按钮
2. 点击按钮打开相应模态框
3. 支持灵活数据流
4. 添加到样本库时可从任何阶段选择数据
5. 提交审核时可选择任何源阶段和目标阶段
6. 创建标注任务时可从任何阶段选择数据
7. 创建增强任务时可从任何阶段选择数据
8. 创建 AI 试算时可从 5 个阶段中选择数据
9. 审核通过后数据在目标阶段可见
10. 不强制严格顺序流程，允许直接跳转
11. 所有模态框使用国际化标签
12. 操作成功时关闭模态框、刷新仪表板、显示成功消息
13. 操作失败时显示错误消息并保持模态框打开

### 2. Design.md 更新

#### 2.1 Admin Dashboard Overview
**更新内容**:
- 在 Dashboard Layout 中添加 Quick Actions 区域
- 添加完整的 QuickActions 组件设计
- 包含 6 个按钮的实现代码示例
- 包含模态框状态管理逻辑
- 包含 handleAction 函数的完整实现
- 添加国际化翻译键示例

**新增组件**:
```typescript
const QuickActions: React.FC<QuickActionsProps> = ({ onRefresh }) => {
  // 6 个模态框的可见性状态
  // handleAction 函数实现
  // 6 个按钮渲染
  // 6 个模态框组件
}
```

## 待完成的更新

### 3. Tasks.md 更新

需要在 Task 23 (Implement Data Lifecycle Dashboard) 中添加以下子任务：

#### 23.4 实现 QuickActions 组件和模态框状态管理
- 创建 QuickActions 组件
- 添加 6 个快速操作按钮
- 实现模态框可见性状态
- 更新 handleAction 函数打开相应模态框
- 使用 t() 进行国际化
- _Requirements: 26.1, 26.2, 26.11_

#### 23.5 创建 CreateTempDataModal 组件
- 表单字段：Name (required), Content (JSON editor), Metadata (optional)
- 集成 useTempData().createTempData() API
- 表单验证
- 成功和错误处理
- 国际化
- _Requirements: 26.1, 26.2, 26.12, 26.13_

#### 23.6 创建 AddToLibraryModal 组件
- 表单字段：Source Stage, Data Selection, Description, Data Type
- 支持灵活数据流：从任何阶段选择数据
- 集成 useSampleLibrary().addToLibrary() API
- 表单验证
- 成功和错误处理
- 国际化
- _Requirements: 26.2, 26.3, 26.4, 26.12, 26.13_

#### 23.7 创建 SubmitReviewModal 组件
- 表单字段：Source Stage, Data Selection, Target Stage, Comments
- 支持灵活数据流：任何源和目标阶段
- 集成 useReview().submitForReview() API
- 表单验证
- 成功和错误处理
- 国际化
- _Requirements: 26.2, 26.3, 26.5, 26.9, 26.10, 26.12, 26.13_

#### 23.8 更新 CreateTaskModal 组件以支持灵活数据源
- 添加 Source Stage 选择字段
- 支持从任何阶段选择数据
- 更新表单验证
- _Requirements: 26.2, 26.6, 26.10_

#### 23.9 更新 CreateEnhancementModal 组件以支持灵活数据源
- 添加 Source Stage 选择字段
- 支持从任何阶段选择数据
- 更新表单验证
- _Requirements: 26.2, 26.7, 26.10_

#### 23.10 更新 CreateTrialModal 组件以支持灵活阶段选择
- 确保支持从 5 个阶段选择数据
- 更新 Data Stage 选择字段
- 更新表单验证
- _Requirements: 26.2, 26.8, 26.10_

#### 23.11 编写快速操作功能的单元测试
- 测试每个按钮点击打开正确的模态框
- 测试模态框表单验证
- 测试 API 集成
- 测试成功和错误处理
- 测试国际化
- _Requirements: 26.1, 26.2, 26.12, 26.13_

#### 23.12 编写灵活数据流的集成测试
- 测试从不同阶段选择数据
- 测试直接跳转到目标阶段
- 测试审核后数据在目标阶段可见
- 测试不强制顺序流程
- _Requirements: 26.3, 26.4, 26.5, 26.6, 26.7, 26.8, 26.9, 26.10_

### 4. Design.md 进一步更新

需要在 UI Component 部分添加以下模态框组件的详细设计：

#### UI Component 10: CreateTempDataModal
- 目的、表单字段、API 集成、验证规则
- 组件结构代码示例
- 国际化键示例

#### UI Component 11: AddToLibraryModal
- 目的、表单字段、API 集成、验证规则
- 灵活数据流支持说明
- 组件结构代码示例
- 国际化键示例

#### UI Component 12: SubmitReviewModal
- 目的、表单字段、API 集成、验证规则
- 灵活数据流和目标阶段选择说明
- 组件结构代码示例
- 国际化键示例

#### UI Component 13-15: 更新现有模态框组件
- 更新 CreateTaskModal 设计以包含 Source Stage 选择
- 更新 CreateEnhancementModal 设计以包含 Source Stage 选择
- 更新 CreateTrialModal 设计以强调 5 阶段选择支持

## 核心概念：灵活数据流

### 关键原则
1. **非线性流程**: 数据可以直接跳转到任何下游阶段，无需遵循严格的顺序
2. **阶段选择**: 用户可以在模态框中选择源阶段和目标阶段
3. **审核后可见**: 提交审核时选择目标阶段，审核通过后数据在该阶段可见
4. **任意起点**: 可以从任何阶段（临时数据、已标注、已增强等）选择数据进行操作

### 支持的灵活流程示例
- 临时数据 → 直接添加到样本库（跳过审核）
- 已标注数据 → 直接创建增强任务（跳过样本库）
- 任何阶段 → 提交审核 → 选择目标阶段（样本库、标注任务、增强任务等）
- 任何阶段 → 创建 AI 试算（5 个阶段都支持）

## 实施建议

1. **优先级**: 先完成 tasks.md 的更新，确保实施计划完整
2. **测试**: 重点测试灵活数据流的各种路径组合
3. **文档**: 在用户手册中说明灵活数据流的使用方法
4. **国际化**: 确保所有新增的模态框和按钮都有完整的中英文翻译

## 相关文件

- `.kiro/specs/data-lifecycle-management/requirements.md` ✅ 已更新
- `.kiro/specs/data-lifecycle-management/design.md` ✅ 部分更新
- `.kiro/specs/data-lifecycle-management/tasks.md` ⏳ 待更新
- `.kiro/specs/data-lifecycle-quick-actions-fix/bugfix.md` 📖 参考源
- `.kiro/specs/data-lifecycle-quick-actions-fix/design.md` 📖 参考源
- `.kiro/specs/data-lifecycle-quick-actions-fix/tasks.md` 📖 参考源

## 下一步行动

1. 完成 tasks.md 的更新（添加 task 23.4-23.12）
2. 完成 design.md 的更新（添加 UI Component 10-15）
3. 验证所有更新的一致性
4. 更新相关的测试计划
