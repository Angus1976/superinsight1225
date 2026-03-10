# Requirements Document: AI 数据处理结果转存到数据生命周期

## Introduction

本需求文档定义了"AI 数据处理结果转存到数据生命周期"功能。该功能允许用户在 AI 数据处理页面（/augmentation/ai-processing）完成数据处理后，将处理结果转存到数据生命周期管理系统的指定阶段，形成"数据获取 → 处理 → 验证效果"的完整闭环。

当前 AI 数据处理页面包含 4 个处理方法：结构化（Structuring）、向量化（Vectorization）、语义化（Semantic）和 AI 智能标注（AI Annotation）。用户完成处理后，需要手动将结果复制或重新上传到数据生命周期系统，流程繁琐且容易出错。本功能通过在每个处理方法页面增加"转存至"操作，实现一键转存，提升用户体验和数据流转效率。

## Glossary

- **AI_Processing_System**: AI 数据处理系统，包含结构化、向量化、语义化、AI 智能标注四个处理方法
- **Data_Lifecycle_System**: 数据生命周期管理系统，管理数据从临时数据到样本库、数据源、已标注、已增强等各个阶段的流转
- **Transfer_Operation**: 转存操作，将 AI 处理结果从处理系统转移到数据生命周期系统的指定阶段
- **Processing_Result**: 处理结果，包括结构化数据、向量化记录、语义化记录、AI 标注任务等
- **Target_Stage**: 目标阶段，数据生命周期系统中的某个阶段，如临时数据、样本库、数据源、已标注、已增强等
- **Transfer_Modal**: 转存模态框，用户选择目标阶段并确认转存操作的界面组件
- **Structuring_Method**: 结构化处理方法，将非结构化文件转换为结构化数据
- **Vectorization_Method**: 向量化处理方法，将文本数据转换为向量表示
- **Semantic_Method**: 语义化处理方法，提取文本的语义信息
- **AI_Annotation_Method**: AI 智能标注方法，使用 AI 模型自动标注数据
- **Approval_Workflow**: 审批流程，数据转存操作需要经过审批才能生效
- **Administrator**: 管理员，拥有所有权限，可以直接转存数据无需审批
- **Regular_User**: 普通用户，转存操作需要提交审批申请
- **Approver**: 审批人，负责审核转存申请并决定是否批准

## Requirements

### Requirement 1: 结构化处理结果转存

**User Story:** 作为数据处理人员，我希望在结构化处理完成后，能够将结构化数据直接转存到数据生命周期系统，以便后续进行标注或增强处理。

#### Acceptance Criteria

1. WHEN 用户在结构化处理页面查看处理结果时，THE AI_Processing_System SHALL 显示"转存至数据生命周期"按钮
2. WHEN 用户点击"转存至数据生命周期"按钮时，THE AI_Processing_System SHALL 打开转存模态框
3. THE Transfer_Modal SHALL 显示可选的目标阶段列表（临时数据、样本库）
4. WHEN 用户选择目标阶段并点击确认时，THE AI_Processing_System SHALL 调用数据生命周期 API 创建对应阶段的数据记录
5. WHEN 转存操作成功时，THE AI_Processing_System SHALL 显示成功提示消息，包含目标阶段名称
6. WHEN 转存操作失败时，THE AI_Processing_System SHALL 显示错误提示消息，包含失败原因
7. THE Transfer_Modal SHALL 支持添加备注信息（可选）
8. THE Transfer_Modal SHALL 支持选择数据类型（文本、图像、音频等）

### Requirement 2: 向量化处理结果转存

**User Story:** 作为数据处理人员，我希望在向量化处理完成后，能够将向量记录转存到数据生命周期系统，以便进行向量检索或相似度分析。

#### Acceptance Criteria

1. WHEN 用户在向量化记录列表中选择一条或多条记录时，THE AI_Processing_System SHALL 启用"转存至数据生命周期"批量操作按钮
2. WHEN 用户点击批量转存按钮时，THE AI_Processing_System SHALL 打开转存模态框，显示已选择的记录数量
3. THE Transfer_Modal SHALL 显示可选的目标阶段列表（临时数据、样本库、已增强）
4. WHEN 用户选择目标阶段并点击确认时，THE AI_Processing_System SHALL 批量调用数据生命周期 API 创建数据记录
5. WHEN 批量转存操作完成时，THE AI_Processing_System SHALL 显示转存结果摘要（成功数量、失败数量）
6. WHEN 部分记录转存失败时，THE AI_Processing_System SHALL 显示失败记录列表和失败原因
7. THE Transfer_Modal SHALL 支持为所有记录添加统一的标签（可选）
8. THE Transfer_Modal SHALL 支持预览第一条记录的内容

### Requirement 3: 语义化处理结果转存

**User Story:** 作为数据处理人员，我希望在语义化处理完成后，能够将语义记录转存到数据生命周期系统，以便进行语义分析或知识图谱构建。

#### Acceptance Criteria

1. WHEN 用户在语义化记录列表中选择一条或多条记录时，THE AI_Processing_System SHALL 启用"转存至数据生命周期"批量操作按钮
2. WHEN 用户点击批量转存按钮时，THE AI_Processing_System SHALL 打开转存模态框，显示已选择的记录数量和类型筛选信息
3. THE Transfer_Modal SHALL 显示可选的目标阶段列表（临时数据、样本库、已增强）
4. WHEN 用户选择目标阶段并点击确认时，THE AI_Processing_System SHALL 批量调用数据生命周期 API 创建数据记录，保留语义类型信息
5. WHEN 批量转存操作完成时，THE AI_Processing_System SHALL 显示转存结果摘要（成功数量、失败数量、按类型分组）
6. THE Transfer_Modal SHALL 支持按语义类型（实体、关系、事件等）分组显示记录
7. THE Transfer_Modal SHALL 支持为不同类型的记录设置不同的目标阶段
8. WHEN 转存包含关系的语义记录时，THE AI_Processing_System SHALL 同时转存关联的实体记录

### Requirement 4: AI 智能标注结果转存

**User Story:** 作为数据处理人员，我希望在 AI 智能标注完成后，能够将标注结果转存到数据生命周期系统的已标注阶段，以便进行质量验证或模型训练。

#### Acceptance Criteria

1. WHEN 用户在 AI 标注任务列表中查看已完成的任务时，THE AI_Processing_System SHALL 在任务详情中显示"转存至数据生命周期"按钮
2. WHEN 用户点击转存按钮时，THE AI_Processing_System SHALL 打开转存模态框，显示任务名称和标注数据数量
3. THE Transfer_Modal SHALL 显示可选的目标阶段列表（已标注、样本库）
4. WHEN 用户选择"已标注"阶段并点击确认时，THE AI_Processing_System SHALL 调用数据生命周期 API 创建已标注数据记录，保留标注信息
5. WHEN 用户选择"样本库"阶段并点击确认时，THE AI_Processing_System SHALL 调用数据生命周期 API 创建样本记录，包含标注元数据
6. WHEN 转存操作成功时，THE AI_Processing_System SHALL 在任务详情中显示转存状态和目标阶段链接
7. THE Transfer_Modal SHALL 支持选择标注质量阈值，只转存高于阈值的标注结果
8. THE Transfer_Modal SHALL 显示标注结果的质量分布图表（置信度分布）

### Requirement 5: 转存操作的国际化支持

**User Story:** 作为国际用户，我希望转存功能的所有界面文本都支持多语言，以便我能够使用母语操作系统。

#### Acceptance Criteria

1. THE Transfer_Modal SHALL 使用 t() 函数包裹所有用户可见的文本（标题、标签、按钮、提示消息等）
2. THE AI_Processing_System SHALL 在中文翻译文件（frontend/src/locales/zh/aiProcessing.json）中定义所有转存相关的翻译 key
3. THE AI_Processing_System SHALL 在英文翻译文件（frontend/src/locales/en/aiProcessing.json）中定义所有转存相关的翻译 key
4. WHEN 用户切换系统语言时，THE Transfer_Modal SHALL 自动更新所有文本为对应语言
5. THE AI_Processing_System SHALL 确保中文和英文翻译文件的 key 结构完全一致
6. THE Transfer_Modal SHALL 使用 useTranslation('aiProcessing') hook 获取翻译函数

### Requirement 6: 转存后的数据可见性

**User Story:** 作为数据处理人员，我希望转存后能够在数据生命周期页面看到转存的数据，以便验证转存是否成功。

#### Acceptance Criteria

1. WHEN 转存操作成功时，THE Data_Lifecycle_System SHALL 在目标阶段的数据列表中显示新转存的数据
2. THE Data_Lifecycle_System SHALL 在数据记录的元数据中保留来源信息（来自 AI 处理系统的哪个方法）
3. WHEN 用户在数据生命周期页面查看转存的数据时，THE Data_Lifecycle_System SHALL 显示来源标签（如"来自向量化处理"）
4. THE Data_Lifecycle_System SHALL 支持按来源筛选数据（结构化、向量化、语义化、AI 标注）
5. WHEN 用户点击来源标签时，THE Data_Lifecycle_System SHALL 提供返回原处理页面的链接（可选）

### Requirement 7: 转存操作的权限控制

**User Story:** 作为系统管理员，我希望能够控制哪些用户可以执行转存操作，以便保护数据安全和质量。

#### Acceptance Criteria

1. THE AI_Processing_System SHALL 检查用户是否具有"数据转存"权限
2. WHEN 用户没有转存权限时，THE AI_Processing_System SHALL 隐藏或禁用"转存至数据生命周期"按钮
3. WHEN 用户尝试执行转存操作但没有权限时，THE AI_Processing_System SHALL 返回 403 Forbidden 错误
4. THE AI_Processing_System SHALL 在审计日志中记录所有转存操作（用户、时间、来源、目标、结果）
5. THE Data_Lifecycle_System SHALL 检查用户是否具有目标阶段的写入权限
6. WHEN 用户没有目标阶段的写入权限时，THE Transfer_Modal SHALL 禁用该目标阶段选项并显示权限提示

### Requirement 8: 转存操作的数据验证

**User Story:** 作为数据质量管理员，我希望转存操作能够验证数据的完整性和有效性，以便确保转存的数据符合质量标准。

#### Acceptance Criteria

1. WHEN 用户尝试转存数据时，THE AI_Processing_System SHALL 验证数据是否包含必需字段（ID、内容、元数据）
2. WHEN 数据缺少必需字段时，THE AI_Processing_System SHALL 拒绝转存并显示缺失字段列表
3. THE AI_Processing_System SHALL 验证数据大小是否超过目标阶段的限制
4. WHEN 数据大小超过限制时，THE AI_Processing_System SHALL 显示错误提示并建议分批转存
5. THE AI_Processing_System SHALL 验证数据格式是否与目标阶段兼容
6. WHEN 数据格式不兼容时，THE AI_Processing_System SHALL 提供格式转换选项或拒绝转存
7. THE AI_Processing_System SHALL 检查目标阶段是否已存在相同 ID 的数据
8. WHEN 目标阶段已存在相同 ID 的数据时，THE Transfer_Modal SHALL 提供覆盖或跳过选项

### Requirement 9: 转存操作的进度反馈

**User Story:** 作为数据处理人员，我希望在批量转存大量数据时能够看到实时进度，以便了解操作状态和预计完成时间。

#### Acceptance Criteria

1. WHEN 用户执行批量转存操作时，THE Transfer_Modal SHALL 显示进度条
2. THE Transfer_Modal SHALL 实时更新进度百分比和已完成数量
3. THE Transfer_Modal SHALL 显示预计剩余时间
4. WHEN 转存操作正在进行时，THE Transfer_Modal SHALL 禁用关闭按钮，防止用户意外中断
5. THE Transfer_Modal SHALL 提供"取消转存"按钮，允许用户主动中断操作
6. WHEN 用户点击取消按钮时，THE AI_Processing_System SHALL 停止后续转存，已完成的转存保持有效
7. WHEN 批量转存完成时，THE Transfer_Modal SHALL 显示详细结果报告（成功数量、失败数量、跳过数量）
8. THE Transfer_Modal SHALL 支持下载转存结果报告为 CSV 文件

### Requirement 10: 转存操作的错误处理

**User Story:** 作为数据处理人员，我希望在转存操作失败时能够获得清晰的错误信息和恢复建议，以便快速解决问题。

#### Acceptance Criteria

1. WHEN 转存操作因网络错误失败时，THE AI_Processing_System SHALL 显示"网络连接失败，请检查网络后重试"
2. WHEN 转存操作因服务器错误失败时，THE AI_Processing_System SHALL 显示"服务器错误，请稍后重试或联系管理员"
3. WHEN 转存操作因权限错误失败时，THE AI_Processing_System SHALL 显示"权限不足，请联系管理员申请权限"
4. WHEN 转存操作因数据验证失败时，THE AI_Processing_System SHALL 显示具体的验证错误信息和修复建议
5. THE AI_Processing_System SHALL 在错误提示中提供"重试"按钮
6. WHEN 用户点击重试按钮时，THE AI_Processing_System SHALL 重新执行转存操作
7. THE AI_Processing_System SHALL 在审计日志中记录所有失败的转存操作和错误原因
8. THE Transfer_Modal SHALL 支持导出失败记录列表，包含失败原因和建议操作

### Requirement 11: 转存模态框的用户体验优化

**User Story:** 作为数据处理人员，我希望转存模态框的操作流程简洁直观，以便快速完成转存操作。

#### Acceptance Criteria

1. THE Transfer_Modal SHALL 使用清晰的标题，明确指示当前操作（如"转存向量化结果到数据生命周期"）
2. THE Transfer_Modal SHALL 使用步骤指示器，显示转存流程的当前步骤（选择目标 → 配置选项 → 确认转存）
3. THE Transfer_Modal SHALL 提供"上一步"和"下一步"按钮，支持流程导航
4. THE Transfer_Modal SHALL 在最后一步显示转存摘要，包含来源、目标、数量、配置选项
5. THE Transfer_Modal SHALL 使用合适的表单控件（下拉选择、单选框、复选框、文本输入）
6. THE Transfer_Modal SHALL 为所有表单字段提供清晰的标签和占位符文本
7. THE Transfer_Modal SHALL 在用户输入无效值时显示实时验证错误
8. THE Transfer_Modal SHALL 使用合适的模态框尺寸，避免内容溢出或过度留白

### Requirement 12: 转存操作的性能优化

**User Story:** 作为数据处理人员，我希望转存操作能够快速完成，即使处理大量数据也不会长时间阻塞界面。

#### Acceptance Criteria

1. WHEN 用户执行批量转存操作时，THE AI_Processing_System SHALL 使用异步 API 调用，避免阻塞 UI 线程
2. THE AI_Processing_System SHALL 将大批量转存操作分批处理，每批不超过 100 条记录
3. THE AI_Processing_System SHALL 使用并发请求，同时处理多个批次（最多 3 个并发请求）
4. WHEN 单个批次转存失败时，THE AI_Processing_System SHALL 继续处理其他批次，不中断整个操作
5. THE AI_Processing_System SHALL 在转存完成后刷新数据生命周期页面的数据缓存
6. THE AI_Processing_System SHALL 使用乐观更新，在 API 调用返回前先更新 UI 状态
7. WHEN 转存操作超过 30 秒时，THE AI_Processing_System SHALL 显示"操作正在进行，请耐心等待"提示
8. THE AI_Processing_System SHALL 记录转存操作的性能指标（耗时、数据量、成功率）用于监控和优化



### Requirement 13: 转存操作的审批流程

**User Story:** 作为系统管理员，我希望普通用户的转存操作需要经过审批，而管理员可以直接转存，以便控制数据流转的安全性和合规性。

#### Acceptance Criteria

1. WHEN 普通用户执行转存操作时，THE AI_Processing_System SHALL 创建审批申请而不是直接转存数据
2. WHEN 管理员执行转存操作时，THE AI_Processing_System SHALL 直接转存数据，无需审批
3. THE AI_Processing_System SHALL 在转存模态框中显示用户的权限级别（管理员/普通用户）
4. WHEN 普通用户提交转存申请时，THE AI_Processing_System SHALL 显示"审批申请已提交，等待审批"提示
5. THE AI_Processing_System SHALL 在审批申请中记录转存详情（来源、目标、数据数量、申请人、申请时间、申请理由）
6. THE AI_Processing_System SHALL 提供审批管理页面，显示所有待审批的转存申请
7. WHEN 审批人批准转存申请时，THE AI_Processing_System SHALL 执行转存操作并通知申请人
8. WHEN 审批人拒绝转存申请时，THE AI_Processing_System SHALL 记录拒绝原因并通知申请人
9. THE AI_Processing_System SHALL 支持审批人添加审批意见
10. THE AI_Processing_System SHALL 在审批历史中记录所有审批操作（审批人、审批时间、审批结果、审批意见）

### Requirement 14: 转存权限的细粒度控制

**User Story:** 作为系统管理员，我希望能够为不同用户配置不同的转存权限，以便实现细粒度的权限控制。

#### Acceptance Criteria

1. THE AI_Processing_System SHALL 支持配置用户的转存权限级别（无权限、需审批、直接转存）
2. THE AI_Processing_System SHALL 支持配置用户可以转存到哪些目标阶段
3. THE AI_Processing_System SHALL 支持配置用户可以从哪些处理方法转存数据
4. WHEN 用户没有转存权限时，THE AI_Processing_System SHALL 隐藏转存按钮
5. WHEN 用户只能转存到部分目标阶段时，THE Transfer_Modal SHALL 只显示用户有权限的目标阶段
6. THE AI_Processing_System SHALL 在权限配置页面显示所有用户的转存权限
7. THE AI_Processing_System SHALL 支持批量配置多个用户的转存权限
8. THE AI_Processing_System SHALL 在审计日志中记录所有权限配置变更

### Requirement 15: 审批通知和提醒

**User Story:** 作为数据处理人员，我希望在审批状态变更时能够收到通知，以便及时了解审批进度。

#### Acceptance Criteria

1. WHEN 普通用户提交转存申请时，THE AI_Processing_System SHALL 向审批人发送待审批通知
2. WHEN 审批人批准或拒绝申请时，THE AI_Processing_System SHALL 向申请人发送审批结果通知
3. THE AI_Processing_System SHALL 支持多种通知方式（站内消息、邮件、系统通知）
4. WHEN 审批申请超过 24 小时未处理时，THE AI_Processing_System SHALL 向审批人发送提醒通知
5. THE AI_Processing_System SHALL 在用户界面显示待审批申请数量的徽章
6. THE AI_Processing_System SHALL 提供审批申请的实时状态查询功能
7. WHEN 用户查看审批申请详情时，THE AI_Processing_System SHALL 显示审批进度时间线
8. THE AI_Processing_System SHALL 支持用户订阅审批状态变更通知
