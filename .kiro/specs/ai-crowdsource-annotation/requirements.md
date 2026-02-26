# 需求文档：AI 标注执行增强与众包标注优化

## 简介

在现有 AI 标注模块（Dashboard、TaskManagement、QualityDashboard、AnnotationCollaboration、EngineConfiguration）和众包门户（Crowdsource）的基础上，增强前端可视化执行能力，补充缺失的试算、渐进式批量、脱敏分发和节奏控制功能。后端已完整实现（PreAnnotationEngine、BatchCoverage、WebSocket 等），本次重点是前端增强和少量新增页面。

**原则：不重复开发已有功能，只优化和补充缺失部分。**

## 术语表

- **Execution_Dashboard**: 标注执行可视化面板，在现有 AIAnnotation Dashboard 基础上增加实时执行过程展示
- **Trial_Runner**: 试算模块（新增），支持小样本快速试算以预览标注效果
- **Batch_Executor**: 渐进式批量执行器（新增），在现有 `applyBatchCoverage` API 基础上构建前端分批执行 UI
- **Crowdsource_Manager**: 众包管理器，在现有 Crowdsource 页面基础上增强脱敏配置和独立标注界面
- **Rhythm_Controller**: 节奏控制面板（新增），提供速率调整和优先级控制
- **Desensitizer**: 数据脱敏配置器（新增），众包分发前的数据脱敏处理

## 已有功能（不重新开发）

以下功能已完成，本次需求不涉及重建：

- AI 标注 Dashboard 统计卡片（totalTasks、completedTasks、activeAnnotators、aiAccuracy 等）
- TaskManagement 任务管理（任务列表、任务详情、任务分配）
- QualityDashboard 质量监控（AccuracyTrend、ConfidenceDistribution、EnginePerformance）
- AnnotationCollaboration 实时协作
- EngineConfiguration 引擎配置与 AB 测试
- Crowdsource 众包门户（任务列表、标注员管理、平台管理、收益追踪）
- 完整的后端 API（预标注、批量覆盖、冲突解决、质量报告、引擎管理、WebSocket）

## 需求

### 需求 1：AI 标注实时执行可视化（优化现有 Dashboard）

**用户故事：** 作为项目管理员，我希望在现有 Dashboard 上看到 AI 标注任务的实时执行过程，以便掌握标注进度和效果。

**现状：** Dashboard 只有静态统计卡片，没有实时执行过程展示。后端已有 `createAnnotationWebSocket` 和 `getPreAnnotationProgress` API。

#### 验收标准

1. WHEN 用户启动 AI 标注任务，THE Execution_Dashboard SHALL 在现有 Dashboard 中新增执行面板，显示实时进度条、已处理数量、剩余数量和预估完成时间
2. WHILE AI 标注任务执行中，THE Execution_Dashboard SHALL 通过现有 `createAnnotationWebSocket` 接收实时更新，每 3 秒刷新进度百分比、当前处理条目和置信度分布
3. WHEN 标注结果产生，THE Execution_Dashboard SHALL 以图表形式展示标注结果分布（各标签数量柱状图、置信度直方图），复用现有 QualityDashboard 的 ConfidenceDistribution 组件
4. IF 标注任务出现错误，THEN THE Execution_Dashboard SHALL 在执行面板中显示错误详情并提供重试按钮
5. WHEN 用户点击暂停按钮，THE Execution_Dashboard SHALL 暂停当前任务并保留已完成的结果

### 需求 2：小样本试算（新增功能）

**用户故事：** 作为数据管理员，我希望用小样本快速试算标注效果，以便在全量标注前评估 AI 标注质量。

**现状：** 完全没有试算功能。后端已有 `submitPreAnnotation` API 可复用。

#### 验收标准

1. WHEN 用户选择试算模式并指定样本数量（10-100 条），THE Trial_Runner SHALL 调用现有 `submitPreAnnotation` API 对随机抽取的样本进行标注
2. WHEN 试算完成，THE Trial_Runner SHALL 展示试算结果摘要（准确率预估、置信度分布、标签分布、耗时统计）
3. WHEN 用户对试算结果满意并点击"扩展到全量"按钮，THE Trial_Runner SHALL 将试算配置传递给 Batch_Executor 启动全量标注
4. THE Trial_Runner SHALL 支持多次试算对比，以表格形式展示不同配置的试算结果差异
5. WHEN 试算结果的平均置信度低于 0.6，THE Trial_Runner SHALL 显示警告提示并建议调整标注配置

### 需求 3：渐进式批量标注（新增前端，复用后端）

**用户故事：** 作为项目管理员，我希望从小样本逐步扩展到全量标注，以便控制标注质量和成本。

**现状：** 后端已有 `applyBatchCoverage` API，但前端没有分批执行和批次质量监控 UI。

#### 验收标准

1. WHEN 用户启动渐进式标注，THE Batch_Executor SHALL 提供批次配置界面，支持设置批次大小（默认 100 条/批）和批次间隔
2. WHEN 每个批次完成，THE Batch_Executor SHALL 调用现有 `getQualityReport` API 获取质量指标，展示该批次结果并等待用户确认后继续下一批
3. WHILE 批量标注执行中，THE Batch_Executor SHALL 在页面上展示累计进度条和各批次质量趋势折线图
4. WHEN 某批次质量指标（准确率）低于用户设定的阈值，THE Batch_Executor SHALL 自动暂停并以警告通知用户
5. THE Batch_Executor SHALL 支持用户在批次间调整后续批次的大小和标注配置

### 需求 4：众包脱敏分发增强（优化现有 Crowdsource）

**用户故事：** 作为项目管理员，我希望在现有众包页面上配置数据脱敏规则并生成独立标注链接，以便安全地将任务分发给外部标注员。

**现状：** Crowdsource 页面已有任务列表、标注员管理、平台管理和收益追踪。缺少脱敏配置和独立标注界面。

#### 验收标准

1. WHEN 管理员在现有 Crowdsource 页面创建众包任务，THE Crowdsource_Manager SHALL 在任务创建流程中新增脱敏规则配置步骤
2. THE Desensitizer SHALL 支持以下脱敏规则：姓名替换、电话号码掩码、邮箱掩码、地址模糊化、自定义正则替换
3. WHEN 管理员配置脱敏规则，THE Desensitizer SHALL 提供预览功能，展示脱敏前后的数据对比（最多 5 条样例）
4. WHEN 众包任务创建时未配置脱敏规则，THE Desensitizer SHALL 阻止任务创建并提示必须配置脱敏规则
5. WHEN 众包任务创建完成，THE Crowdsource_Manager SHALL 生成独立标注链接，外部标注员通过该链接访问独立标注界面（无需登录主系统）
6. WHEN 众包标注结果提交，THE Crowdsource_Manager SHALL 调用现有 `validateAnnotations` API 对结果进行质量校验

### 需求 5：标注节奏与优先级控制（新增功能）

**用户故事：** 作为项目管理员，我希望实时调整标注的节奏和优先顺序，以便根据业务需求灵活安排标注工作。

**现状：** 没有速率调整、优先级拖拽等控制面板。

#### 验收标准

1. THE Rhythm_Controller SHALL 在 AI 标注页面新增控制面板 Tab，提供标注速率滑块（条/分钟）和并发数配置
2. WHEN 用户拖拽调整任务优先级，THE Rhythm_Controller SHALL 立即重新排列任务队列并通过 WebSocket 通知后端
3. WHEN 用户调整标注速率，THE Rhythm_Controller SHALL 在 5 秒内生效并更新 Execution_Dashboard 的预估完成时间
4. THE Rhythm_Controller SHALL 支持按数据类型、标签类别设置不同的标注优先级规则
5. WHILE 标注执行中，THE Rhythm_Controller SHALL 展示当前速率、队列深度和资源使用情况的实时数值

### 需求 6：脱敏审计与安全（新增功能）

**用户故事：** 作为安全管理员，我希望所有脱敏操作有审计记录，以便满足数据安全合规要求。

**现状：** 无脱敏审计功能。

#### 验收标准

1. THE Desensitizer SHALL 记录所有脱敏操作的审计日志（操作人、时间、规则、影响数据量）
2. WHEN 安全管理员查看审计日志，THE Desensitizer SHALL 以表格形式展示日志列表，支持按时间范围和操作人筛选
3. WHEN 众包结果回收后，THE Desensitizer SHALL 支持将标注结果自动映射回原始未脱敏数据
4. IF 脱敏规则配置不完整（未覆盖所有敏感字段），THEN THE Desensitizer SHALL 阻止任务分发并提示补充规则
