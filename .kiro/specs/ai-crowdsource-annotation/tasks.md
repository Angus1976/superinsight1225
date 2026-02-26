# 实施计划：AI 标注执行增强与众包标注优化

## 概述

在现有前端代码基础上增量扩展，新增 4 个 Zustand Store、10 个 API 函数、7 个组件。所有组件以 Tab/面板形式嵌入现有页面，不重建已有功能。测试使用 vitest + fast-check。

## 任务

- [x] 1. 新增 API 函数和类型定义
  - [x] 1.1 在 `aiAnnotationApi.ts` 中新增 10 个 API 函数和相关类型
    - 新增类型：`DesensitizationRule`、`DesensitizationPreview`、`AuditLogEntry`、`AuditFilter`、`RhythmConfig`、`PriorityRule`、`RhythmStatus`、`ExecutionError`
    - 新增函数：`getDesensitizationRules`、`saveDesensitizationRules`、`previewDesensitization`、`getAuditLogs`、`generateExternalLink`、`getExternalTask`、`submitExternalAnnotation`、`updateRhythmConfig`、`getRhythmStatus`、`mapBackAnnotations`
    - _需求: 4.1, 4.2, 4.3, 4.5, 5.1, 5.2, 6.1, 6.2, 6.3_

- [x] 2. 创建 Zustand Store
  - [x] 2.1 创建 `executionStore.ts`（ExecutionState 管理、WebSocket 更新、暂停/恢复）
    - 参考 `languageStore.ts` 的 Zustand 模式
    - 实现 `startExecution`、`pauseExecution`、`updateProgress` 方法
    - _需求: 1.1, 1.2, 1.4, 1.5_
  - [x] 2.2 创建 `trialStore.ts`（试算结果列表管理、多次对比）
    - 实现 `addTrial`、`clearTrials` 方法
    - _需求: 2.2, 2.4_
  - [x] 2.3 创建 `batchStore.ts`（批次配置、进度跟踪、质量阈值暂停）
    - 实现 `setConfig`、`addBatchResult` 方法和自动暂停逻辑
    - _需求: 3.1, 3.2, 3.4_
  - [x] 2.4 创建 `rhythmStore.ts`（速率配置、优先级规则、实时状态）
    - 实现 `updateRate`、`updatePriority` 方法
    - _需求: 5.1, 5.2, 5.4_

- [x] 3. 实现核心工具函数
  - [x] 3.1 实现 `clampSampleSize`、`checkBatchQuality`、`calculateEstimatedTime`、`sortByPriority`、`applyDesensitizationRule`、`filterAuditLogs` 纯函数
    - 文件：`frontend/src/utils/annotationHelpers.ts`
    - _需求: 2.1, 2.5, 3.4, 4.2, 5.2, 5.3, 6.2_
  - [x] 3.2 属性测试：试算样本数约束
    - **Property 4: 试算样本数约束** — clampSampleSize 输出始终在 [10, 100]
    - **验证: 需求 2.1**
  - [x] 3.3 属性测试：低置信度警告
    - **Property 6: 低置信度警告** — avgConfidence < 0.6 时触发警告
    - **验证: 需求 2.5**
  - [x] 3.4 属性测试：批次质量自动暂停
    - **Property 7: 批次质量自动暂停** — accuracy < threshold 时暂停
    - **验证: 需求 3.2, 3.4**
  - [x] 3.5 属性测试：速率变更更新预估时间
    - **Property 13: 速率变更更新预估时间** — remaining / ratePerMinute 计算正确
    - **验证: 需求 5.3**
  - [x] 3.6 属性测试：优先级排序正确性
    - **Property 12: 优先级排序正确性** — 高优先级在前，相同优先级保持稳定排序
    - **验证: 需求 5.2, 5.4**
  - [x] 3.7 属性测试：脱敏规则正确应用
    - **Property 9: 脱敏规则正确应用** — 输出不含原始敏感信息
    - **验证: 需求 4.2**
  - [x] 3.8 属性测试：审计日志筛选正确性
    - **Property 15: 审计日志筛选正确性** — 筛选结果均满足 filter 条件
    - **验证: 需求 6.2**

- [x] 4. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 5. 实现 ExecutionPanel 和 TrialRunner 组件
  - [x] 5.1 实现 `ExecutionPanel.tsx`（实时进度、WebSocket 集成、图表展示、暂停/重试）
    - 复用 `QualityDashboard` 的 `ConfidenceDistribution` 组件
    - 连接 `executionStore`，通过 `createAnnotationWebSocket` 接收实时数据
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [x] 5.2 属性测试：执行状态渲染完整性
    - **Property 1: 执行状态渲染完整性** — 渲染后包含所有必要元素
    - **验证: 需求 1.1, 1.3**
  - [x] 5.3 属性测试：WebSocket 消息正确更新状态
    - **Property 2: WebSocket 消息正确更新状态** — progress 单调递增
    - **验证: 需求 1.2**
  - [x] 5.4 属性测试：暂停保留已完成结果
    - **Property 3: 暂停保留已完成结果** — 暂停后 processed 不变
    - **验证: 需求 1.5**
  - [x] 5.5 实现 `TrialRunner.tsx`（样本配置、试算执行、结果对比表、低置信度警告）
    - 调用 `submitPreAnnotation` API，连接 `trialStore`
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [x] 5.6 属性测试：多次试算对比表完整性
    - **Property 5: 多次试算对比表完整性** — 对比表行数等于试算次数
    - **验证: 需求 2.2, 2.4**

- [x] 6. 实现 BatchExecutor 和 RhythmController 组件
  - [x] 6.1 实现 `BatchExecutor.tsx`（批次配置、分批执行、质量趋势图、自动暂停、批间调整）
    - 调用 `applyBatchCoverage` + `getQualityReport` API，连接 `batchStore`
    - 支持从 TrialRunner "扩展到全量" 传入配置
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x] 6.2 属性测试：累计批次进度计算
    - **Property 8: 累计批次进度计算** — 进度百分比和趋势数据点数正确
    - **验证: 需求 3.3**
  - [x] 6.3 实现 `RhythmController.tsx`（速率滑块、并发配置、优先级拖拽、实时状态展示）
    - 通过 WebSocket 发送调整指令，连接 `rhythmStore`
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 7. 实现众包脱敏和审计组件
  - [x] 7.1 实现 `DesensitizerConfig.tsx`（脱敏规则配置、预览、完整性校验、阻止未配置任务）
    - 嵌入 Crowdsource 任务创建流程
    - _需求: 4.1, 4.2, 4.3, 4.4_
  - [x] 7.2 属性测试：脱敏预览最多 5 条
    - **Property 10: 脱敏预览最多 5 条** — 预览长度 ≤ min(5, 数据集长度)
    - **验证: 需求 4.3**
  - [x] 7.3 属性测试：脱敏规则完整性校验
    - **Property 11: 脱敏规则完整性校验** — 未覆盖敏感字段时阻止分发
    - **验证: 需求 4.4, 6.4**
  - [x] 7.4 实现 `DesensitizationAudit.tsx`（审计日志表格、时间/操作人筛选）
    - _需求: 6.1, 6.2_
  - [x] 7.5 属性测试：审计日志字段完整性
    - **Property 14: 审计日志字段完整性** — 每条记录包含所有必填字段
    - **验证: 需求 6.1**

- [x] 8. 实现 ExternalAnnotationView 和页面集成
  - [x] 8.1 实现 `ExternalAnnotationView`（独立路由 `/external-annotation/:token`、标注提交、质量校验）
    - 调用 `getExternalTask`、`submitExternalAnnotation`、`validateAnnotations` API
    - _需求: 4.5, 4.6_
  - [x] 8.2 属性测试：脱敏标注映射往返
    - **Property 16: 脱敏标注映射往返** — mapBack 后 id 正确关联
    - **验证: 需求 6.3**
  - [x] 8.3 集成到现有页面
    - 在 AIAnnotation Dashboard 新增 Tab：执行面板、试算、批量执行、节奏控制
    - 在 Crowdsource 页面新增脱敏配置步骤和审计日志 Tab
    - 注册 `/external-annotation/:token` 路由
    - _需求: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_

- [x] 9. 最终检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

## 备注

- 标记 `*` 的任务为可选，可跳过以加速 MVP
- 每个任务引用具体需求编号以确保可追溯性
- 属性测试使用 vitest + fast-check，每个属性至少 100 次迭代
- 测试文件放在 `frontend/src/test/ai-crowdsource-annotation/` 目录
