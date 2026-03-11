# Requirements Document

## Introduction

当前前端向量化和语义化 Tab 直接调用各自独立的 API（`/api/vectorization/jobs`、`/api/semantic/jobs`），完全绕过了后端已有的 5 层 Toolkit 智能路由框架（DataProfiler → StrategyRouter → PipelineExecutor → StorageAbstraction）。本特性将前端上传流程统一接入 Toolkit 路由层，实现"根据数据格式自动选择处理策略和目标存储"，同时保留用户手动选择的能力。

## Glossary

- **Toolkit_Router**: 后端 StrategyRouter，基于规则引擎 + 评分排序选择最优处理策略
- **DataProfiler**: 后端 SimpleProfiler，对上传文件执行 3 阶段分析（Quick → Sampling → Full）
- **Processing_Panel**: 前端统一处理面板组件，展示路由推荐结果并支持手动覆盖
- **Strategy_Selector**: 前端策略选择器组件，展示所有候选策略的评分和说明
- **Storage_Indicator**: 前端存储指示器，显示自动选定或手动指定的目标数据库类型
- **Processing_Mode**: 处理模式枚举，包含 auto（自动）和 manual（手动）两种值

## Requirements

### Requirement 1: 统一上传入口接入 Toolkit 路由

**User Story:** As a 数据处理用户, I want 向量化和语义化 Tab 的文件上传统一走 Toolkit 路由, so that 系统能根据文件类型自动选择最优处理策略和目标存储。

#### Acceptance Criteria

1. WHEN a file is uploaded via the vectorization Tab, THE Toolkit_Router SHALL profile the file and return a ranked list of candidate strategies
2. WHEN a file is uploaded via the semantic Tab, THE Toolkit_Router SHALL profile the file and return a ranked list of candidate strategies
3. THE Toolkit_Router SHALL set `needs_semantic_search=true` in Requirements WHEN the upload originates from the vectorization Tab
4. THE Toolkit_Router SHALL set `needs_graph_traversal=true` in Requirements WHEN the upload originates from the semantic Tab
5. IF the DataProfiler fails to profile the file, THEN THE Toolkit_Router SHALL fall back to the default strategy and display an error notification

### Requirement 2: 自动模式下的策略推荐展示

**User Story:** As a 数据处理用户, I want 上传后看到系统自动推荐的处理策略和目标存储, so that 我能了解系统的决策依据并决定是否接受。

#### Acceptance Criteria

1. WHEN Processing_Mode is set to auto, THE Processing_Panel SHALL display the top-ranked strategy name, explanation, estimated cost, and target storage type
2. WHEN Processing_Mode is set to auto, THE Processing_Panel SHALL display all candidate strategies returned by `evaluate_strategies()` in score-descending order
3. THE Strategy_Selector SHALL display each candidate's name, score, and explanation text
4. THE Storage_Indicator SHALL display the primary_storage type of the selected strategy

### Requirement 3: 手动模式下的策略覆盖

**User Story:** As a 高级用户, I want 手动选择处理策略和目标存储, so that 我能根据业务需求覆盖系统的自动推荐。

#### Acceptance Criteria

1. WHEN the user switches Processing_Mode to manual, THE Strategy_Selector SHALL enable selection of any candidate strategy from the ranked list
2. WHEN the user selects a strategy in manual mode, THE Processing_Panel SHALL update the displayed stages and target storage to match the selected strategy
3. WHEN the user confirms a manually selected strategy, THE Toolkit_Router SHALL execute the pipeline using the user-selected strategy instead of the top-ranked one
4. THE Processing_Panel SHALL default Processing_Mode to auto on initial load

### Requirement 4: 处理执行与进度反馈

**User Story:** As a 数据处理用户, I want 看到处理管道的实时执行进度, so that 我能了解当前处理状态。

#### Acceptance Criteria

1. WHEN the user confirms strategy selection, THE Processing_Panel SHALL call `/api/toolkit/execute/{id}` to start pipeline execution
2. WHILE the pipeline is executing, THE Processing_Panel SHALL display a progress indicator showing the current stage name and completion percentage
3. WHEN the pipeline execution completes successfully, THE Processing_Panel SHALL display a success notification with the storage location
4. IF the pipeline execution fails, THEN THE Processing_Panel SHALL display the error message and offer a retry option

### Requirement 5: 前端国际化支持

**User Story:** As a 多语言用户, I want 所有新增的处理面板文本支持中英文切换, so that 我能使用自己熟悉的语言操作系统。

#### Acceptance Criteria

1. THE Processing_Panel SHALL render all user-visible text using `t()` function from `useTranslation` hook
2. THE Processing_Panel SHALL load translation keys from `aiProcessing` namespace in both `frontend/src/locales/zh/` and `frontend/src/locales/en/` directories
3. THE Strategy_Selector SHALL display strategy names and explanations using translated labels when available, falling back to the raw strategy name

### Requirement 6: 向后兼容与渐进迁移

**User Story:** As a 系统维护者, I want 现有的向量化和语义化独立 API 保持可用, so that 迁移过程中不影响已有功能。

#### Acceptance Criteria

1. THE Toolkit_Router SHALL preserve existing `/api/vectorization/jobs` and `/api/semantic/jobs` endpoints without modification
2. WHEN the Toolkit pipeline completes for a vectorization-origin upload, THE Toolkit_Router SHALL store results in VectorDB via StorageAbstraction
3. WHEN the Toolkit pipeline completes for a semantic-origin upload, THE Toolkit_Router SHALL store results in the storage type selected by StorageAbstraction scoring
4. THE Processing_Panel SHALL reuse existing job list tables and record viewing modals from VectorizationContent and SemanticContent
