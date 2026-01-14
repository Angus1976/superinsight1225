# Requirements Document: AI Annotation (AI 标注)

## Introduction

本模块优化 `src/ai/` 和 `src/label_studio/`，实现事前预标/事中覆盖/事后验证的完整 AI 标注流程，支持方法切换和人机协作。核心目标是提升标注效率和质量，同时保持灵活的方法选择能力。

## Glossary

- **Pre_Annotation_Engine**: 事前预标引擎，使用 LLM 和样本学习进行批量预标注
- **Mid_Coverage_Engine**: 事中覆盖引擎，基于人类样本进行批量覆盖标注
- **Post_Validation_Engine**: 事后验证引擎，使用 Ragas/DeepEval 进行多维验证
- **Method_Switcher**: 方法切换器，支持 ML Backend/Argilla/Custom LLM 切换
- **Collaboration_Manager**: 人机协作管理器，管理标注员/专家/外包角色分工
- **Review_Flow_Engine**: 审核流引擎，管理标注审核流程
- **Third_Party_Adapter**: 第三方工具适配器，对接外部专业 AI 标注服务
- **Plugin_Manager**: 插件管理器，管理第三方工具的注册和配置

## Requirements

### Requirement 1: 事前批量预标注

**User Story:** 作为项目管理员，我希望使用 AI 进行批量预标注，以便减少人工标注工作量。

#### Acceptance Criteria

1. WHEN 管理员启动预标注任务 THEN THE Pre_Annotation_Engine SHALL 调用配置的 LLM 进行批量预标注
2. THE Pre_Annotation_Engine SHALL 支持以下预标注类型：文本分类、命名实体识别、情感分析、关系抽取
3. WHEN 预标注完成 THEN THE Pre_Annotation_Engine SHALL 为每个标注结果生成置信度分数
4. THE Pre_Annotation_Engine SHALL 支持样本学习，基于已标注样本提升预标注质量
5. WHEN 置信度低于阈值 THEN THE Pre_Annotation_Engine SHALL 标记该任务需要人工审核
6. THE Pre_Annotation_Engine SHALL 支持批量处理，单次最多处理 1000 条数据

### Requirement 2: 事中批量覆盖

**User Story:** 作为标注员，我希望系统能基于我的标注样本自动覆盖相似数据，以便提升标注效率。

#### Acceptance Criteria

1. WHEN 标注员完成一定数量的标注 THEN THE Mid_Coverage_Engine SHALL 分析标注模式
2. THE Mid_Coverage_Engine SHALL 识别与已标注样本相似的未标注数据
3. WHEN 相似度超过阈值 THEN THE Mid_Coverage_Engine SHALL 自动应用相同标注
4. THE Mid_Coverage_Engine SHALL 记录自动覆盖的数据，便于后续审核
5. WHEN 自动覆盖完成 THEN THE Mid_Coverage_Engine SHALL 通知标注员审核覆盖结果
6. THE Mid_Coverage_Engine SHALL 支持配置相似度阈值（默认 0.85）

### Requirement 3: 事后多维验证

**User Story:** 作为质量管理员，我希望对标注结果进行多维验证，以便确保标注质量。

#### Acceptance Criteria

1. WHEN 标注任务完成 THEN THE Post_Validation_Engine SHALL 自动触发质量验证
2. THE Post_Validation_Engine SHALL 支持以下验证维度：准确率、召回率、一致性、完整性
3. THE Post_Validation_Engine SHALL 集成 Ragas 框架进行语义质量评估
4. THE Post_Validation_Engine SHALL 集成 DeepEval 框架进行深度评估
5. WHEN 验证发现问题 THEN THE Post_Validation_Engine SHALL 生成详细的问题报告
6. THE Post_Validation_Engine SHALL 支持自定义验证规则

### Requirement 4: 方法切换

**User Story:** 作为系统管理员，我希望能够切换 AI 标注方法，以便根据场景选择最优方案。

#### Acceptance Criteria

1. THE Method_Switcher SHALL 支持以下方法：Label Studio ML Backend、Argilla、Custom LLM
2. WHEN 管理员配置默认方法 THEN THE Method_Switcher SHALL 使用该方法进行标注
3. WHEN 调用时指定方法参数 THEN THE Method_Switcher SHALL 临时使用指定方法
4. THE Method_Switcher SHALL 支持方法热切换，不中断正在进行的任务
5. WHEN 切换方法 THEN THE Method_Switcher SHALL 记录切换日志
6. THE Method_Switcher SHALL 提供方法性能对比报告

### Requirement 5: 人机协作

**User Story:** 作为项目管理员，我希望管理标注团队的角色分工，以便实现高效的人机协作。

#### Acceptance Criteria

1. THE Collaboration_Manager SHALL 支持以下角色：标注员、专家、外包、审核员
2. WHEN 分配任务 THEN THE Collaboration_Manager SHALL 根据角色权限分配合适的任务
3. THE Collaboration_Manager SHALL 支持任务优先级配置
4. WHEN 标注员完成任务 THEN THE Collaboration_Manager SHALL 自动分配给审核员
5. THE Collaboration_Manager SHALL 支持实时协作，多人可同时标注不同数据
6. THE Collaboration_Manager SHALL 记录每个角色的工作量统计

### Requirement 6: 审核流程

**User Story:** 作为审核员，我希望有清晰的审核流程，以便高效完成标注审核。

#### Acceptance Criteria

1. THE Review_Flow_Engine SHALL 支持配置审核流程（单级/多级审核）
2. WHEN 标注提交审核 THEN THE Review_Flow_Engine SHALL 分配给配置的审核员
3. THE Review_Flow_Engine SHALL 支持审核通过、驳回、修改三种操作
4. WHEN 审核驳回 THEN THE Review_Flow_Engine SHALL 将任务退回给标注员并附带驳回原因
5. THE Review_Flow_Engine SHALL 记录完整的审核历史
6. THE Review_Flow_Engine SHALL 支持批量审核操作

### Requirement 7: 前端标注界面

**User Story:** 作为标注员，我希望有友好的标注界面，以便高效完成标注工作。

#### Acceptance Criteria

1. THE Annotation_UI SHALL 集成 Label Studio 标注界面
2. THE Annotation_UI SHALL 显示 AI 预标注结果和置信度
3. WHEN 标注员修改预标注 THEN THE Annotation_UI SHALL 记录修改历史
4. THE Annotation_UI SHALL 支持快捷键操作提升效率
5. THE Annotation_UI SHALL 显示当前任务进度和统计
6. THE Annotation_UI SHALL 支持标注结果实时同步


### Requirement 8: 第三方 AI 标注工具对接

**User Story:** 作为系统管理员，我希望能够对接第三方专业 AI 标注工具，以便利用成熟的商业或开源解决方案。

#### Acceptance Criteria

1. THE Third_Party_Adapter SHALL 提供统一的插件接口规范（Annotation Plugin Interface）
2. WHEN 注册第三方工具 THEN THE Plugin_Manager SHALL 验证工具实现了必要的接口方法
3. THE Third_Party_Adapter SHALL 支持以下对接方式：REST API、gRPC、Webhook
4. WHEN 调用第三方工具 THEN THE Third_Party_Adapter SHALL 将标注任务转换为工具特定格式
5. WHEN 第三方工具返回结果 THEN THE Third_Party_Adapter SHALL 将结果转换为 Label Studio 兼容格式
6. THE Third_Party_Adapter SHALL 支持以下主流工具：Prodigy、Doccano、CVAT、Labelbox、Scale AI
7. IF 第三方工具不可用 THEN THE Third_Party_Adapter SHALL 自动回退到内置方法
8. THE Third_Party_Adapter SHALL 记录每次调用的性能指标（延迟、成功率）

### Requirement 9: 第三方工具前端配置

**User Story:** 作为系统管理员，我希望通过可视化界面配置第三方 AI 标注工具，以便无需修改代码即可管理工具集成。

#### Acceptance Criteria

1. THE Plugin_Config_UI SHALL 显示已注册的第三方工具列表和状态
2. WHEN 管理员添加第三方工具 THEN THE Plugin_Config_UI SHALL 提供配置表单（端点、API Key、超时、标注类型映射）
3. THE Plugin_Config_UI SHALL 支持工具连接测试功能
4. WHEN 管理员启用/禁用工具 THEN THE Plugin_Config_UI SHALL 立即生效且不影响正在进行的任务
5. THE Plugin_Config_UI SHALL 显示工具调用统计（调用次数、成功率、平均延迟、成本）
6. THE Plugin_Config_UI SHALL 支持配置工具优先级，用于自动选择最优工具
7. WHEN 配置标注类型映射 THEN THE Plugin_Config_UI SHALL 支持将内部标注类型映射到工具特定类型
