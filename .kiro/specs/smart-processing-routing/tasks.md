# Implementation Plan: Smart Processing Routing

## Overview

将前端向量化/语义化 Tab 的上传流程统一接入后端 Toolkit 智能路由框架。后端扩展 `/api/toolkit/route` 和 `/execute` 端点，前端新增 ProcessingPanel 组件体系和 toolkitStore，实现自动策略推荐、手动覆盖、执行进度反馈。

## Tasks

- [x] 1. 后端 API 扩展与数据模型
  - [x] 1.1 扩展 route 端点，增加 origin 和 candidates 返回
    - 修改 `src/toolkit/api/router.py` 的 `route_file` 函数
    - 增加 `origin` 参数（vectorization / semantic），映射为 Requirements
    - 增加 `strategy_name` 可选参数用于手动模式
    - 调用 `evaluate_strategies()` 返回候选策略列表
    - DataProfiler 异常时返回 default fallback plan
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 1.2 扩展 execute 端点，支持 strategy_name 覆盖
    - 修改 `src/toolkit/api/router.py` 的 `execute_pipeline` 函数
    - 增加 `strategy_name` 可选参数，非空时使用用户选择的策略
    - 校验 strategy_name 在候选列表中，否则返回 400
    - _Requirements: 3.3, 4.1_

  - [x] 1.3 新增 DTO 模型 RouteResponse 和 StrategyCandidateDTO
    - 在 `src/toolkit/models/` 下新增或扩展 Pydantic 模型
    - RouteResponse 包含 plan + candidates 列表
    - StrategyCandidateDTO 包含 name, score, explanation, primary_storage
    - _Requirements: 2.1, 2.3, 2.4_

  - [ ]* 1.4 Property tests for origin-to-requirements mapping and route response
    - **Property 1: Origin produces non-empty ranked candidates**
    - **Property 2: Origin-to-Requirements mapping correctness**
    - **Property 3: Profiler failure triggers default fallback**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

  - [ ]* 1.5 Property tests for candidate ordering and field completeness
    - **Property 4: Candidates are score-descending ordered**
    - **Property 5: Strategy display contains all required fields**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

  - [ ]* 1.6 Property test for manual strategy selection honored in execution
    - **Property 6: Manual strategy selection is honored in execution**
    - **Validates: Requirements 3.3**

- [x] 2. Checkpoint - 后端 API 验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. 前端 TypeScript 类型与 toolkitStore
  - [x] 3.1 定义前端 TypeScript 类型
    - 在 `frontend/src/types/` 或 store 文件中定义 StrategyCandidate, ExecutionStatus, ProcessingMode 类型
    - _Requirements: 2.1, 4.2_

  - [x] 3.2 创建 toolkitStore (zustand)
    - 新建 `frontend/src/stores/toolkitStore.ts`
    - 参照 vectorizationStore 模式，使用 `create` + `devtools` middleware
    - 实现 state: fileId, profile, plan, candidates, mode, selectedStrategy, executionStatus
    - 实现 actions: uploadFile, routeFile, selectStrategy, executePipeline, setMode
    - API 调用使用 apiClient，路径 `/api/toolkit/`
    - _Requirements: 1.1, 1.2, 3.1, 3.2, 3.4, 4.1_

- [x] 4. 前端组件实现
  - [x] 4.1 实现 StrategySelector 组件
    - 新建 `frontend/src/pages/AIProcessing/components/StrategySelector.tsx`
    - 展示候选策略列表（name, score, explanation），按 score 降序
    - auto 模式高亮 top-ranked，manual 模式允许点选
    - 所有文本使用 `t()` 包裹，namespace `aiProcessing`
    - _Requirements: 2.2, 2.3, 3.1, 3.2, 5.1_

  - [x] 4.2 实现 StorageIndicator 组件
    - 新建 `frontend/src/pages/AIProcessing/components/StorageIndicator.tsx`
    - 展示选中策略的 primary_storage 类型
    - 所有文本使用 `t()` 包裹
    - _Requirements: 2.4, 5.1_

  - [x] 4.3 实现 ProcessingPanel 组件
    - 新建 `frontend/src/pages/AIProcessing/components/ProcessingPanel.tsx`
    - Props: `origin: 'vectorization' | 'semantic'`
    - 集成 StrategySelector + StorageIndicator
    - 实现 auto/manual 模式切换，默认 auto
    - 展示执行进度（stage name + percentage）和成功/失败状态
    - 失败时显示 error + retry 按钮
    - 所有文本使用 `t()` 包裹
    - _Requirements: 2.1, 3.2, 3.4, 4.1, 4.2, 4.3, 4.4, 5.1_

  - [ ]* 4.4 Property test for storage type matching
    - **Property 7: Storage type matches StorageAbstraction selection**
    - **Validates: Requirements 6.2, 6.3**

  - [ ]* 4.5 Property test for progress events
    - **Property 8: Progress events contain stage name and percentage**
    - **Validates: Requirements 4.2**

- [x] 5. i18n 翻译文件
  - [x] 5.1 添加 aiProcessing 命名空间翻译 key
    - 在 `frontend/src/locales/zh/common.json` 的 aiProcessing 下新增所有 ProcessingPanel 相关 key
    - 在 `frontend/src/locales/en/common.json` 同步新增对应英文翻译
    - 包含：策略名称、模式切换、进度提示、错误信息、存储类型等
    - _Requirements: 5.1, 5.2_

  - [ ]* 5.2 Property test for translation fallback
    - **Property 9: Translation fallback for strategy names**
    - **Validates: Requirements 5.3**

- [x] 6. Checkpoint - 前端组件验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. 集成到现有 Tab 并保持向后兼容
  - [x] 7.1 在 VectorizationContent 中嵌入 ProcessingPanel
    - 修改 `frontend/src/pages/AIProcessing/VectorizationContent.tsx`
    - 在上传区域下方嵌入 `<ProcessingPanel origin="vectorization" />`
    - 保留现有 job list 表格和 record viewing modal 不变
    - _Requirements: 1.1, 6.1, 6.4_

  - [x] 7.2 在 SemanticContent 中嵌入 ProcessingPanel
    - 修改 `frontend/src/pages/AIProcessing/SemanticContent.tsx`
    - 在上传区域下方嵌入 `<ProcessingPanel origin="semantic" />`
    - 保留现有 job list 表格和 record viewing modal 不变
    - _Requirements: 1.2, 6.1, 6.4_

  - [ ]* 7.3 编写前端组件测试 (vitest)
    - ProcessingPanel 渲染测试（auto/manual 模式）
    - StrategySelector 候选列表展示和选择交互
    - _Requirements: 2.2, 3.1, 3.2_

- [x] 8. Final checkpoint - 全量验证
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 后端使用 Python (FastAPI + Pydantic)，前端使用 TypeScript (React + Zustand)
- Property tests 使用 hypothesis 库，前端测试使用 vitest
- 现有 `/api/vectorization/jobs` 和 `/api/semantic/jobs` 端点不做任何修改
