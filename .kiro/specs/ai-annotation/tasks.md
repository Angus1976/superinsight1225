# Implementation Plan: AI Annotation (AI 标注)

## Overview

本任务文档将 AI Annotation 设计分解为可执行的开发任务，实现事前预标/事中覆盖/事后验证的完整 AI 标注流程，支持第三方工具对接和人机协作。

## Tasks

- [x] 1. 核心数据模型和基础设施
  - [x] 1.1 创建数据模型
    - 创建 `src/ai/annotation_schemas.py`，定义标注相关 Pydantic 模型
    - 创建 `src/models/annotation_plugin.py`，定义 SQLAlchemy 模型
    - _需求 8.1, 8.2: 插件数据模型_
  
  - [x] 1.2 创建数据库迁移
    - 创建 Alembic 迁移脚本
    - 添加 `annotation_plugins`、`plugin_call_logs`、`review_records` 表
    - _需求 6.5, 8.8: 历史记录存储_
  
  - [x] 1.3 创建目录结构
    - 扩展 `src/ai/` 目录
    - 创建新模块文件
    - _基础设施_

- [x] 2. Pre-Annotation Engine 实现
  - [x] 2.1 创建事前预标引擎
    - 创建 `src/ai/pre_annotation.py`
    - 实现 `pre_annotate()` 批量预标注
    - 实现 `calculate_confidence()` 置信度计算
    - 集成 LLM Switcher
    - _需求 1.1, 1.3: 预标注和置信度_
  
  - [x] 2.2 实现样本学习
    - 实现 `pre_annotate_with_samples()` 基于样本的预标注
    - 实现样本特征提取和匹配
    - _需求 1.4: 样本学习_
  
  - [x] 2.3 实现阈值标记和批量限制
    - 实现 `mark_for_review()` 阈值标记
    - 实现批量处理限制（最多 1000 条）
    - _需求 1.5, 1.6: 阈值标记和批量限制_
  
  - [x] 2.4 编写 Pre-Annotation 属性测试
    - **Property 1: 置信度阈值标记**
    - **Validates: Requirements 1.3, 1.5**

- [x] 3. Mid-Coverage Engine 实现
  - [x] 3.1 创建事中覆盖引擎
    - 创建 `src/ai/mid_coverage.py`
    - 实现 `analyze_patterns()` 模式分析
    - 实现 `find_similar_tasks()` 相似任务查找
    - _需求 2.1, 2.2: 模式分析和相似查找_
  
  - [x] 3.2 实现自动覆盖
    - 实现 `auto_cover()` 自动覆盖标注
    - 实现相似度阈值配置
    - 实现覆盖记录
    - _需求 2.3, 2.4, 2.6: 自动覆盖_
  
  - [x] 3.3 实现通知功能
    - 实现 `notify_annotator()` 通知标注员
    - _需求 2.5: 通知审核_
  
  - [x] 3.4 编写 Mid-Coverage 属性测试
    - **Property 5: 自动覆盖记录**
    - **Validates: Requirements 2.4**

- [x] 4. Checkpoint - 确保预标注和覆盖功能完成
  - 验证预标注流程
  - 验证自动覆盖功能
  - 确保所有测试通过，如有问题请询问用户


- [x] 5. Post-Validation Engine 实现
  - [x] 5.1 创建事后验证引擎
    - 创建 `src/ai/post_validation.py`
    - 实现 `validate()` 多维验证
    - 实现 `validate_accuracy()` 准确率验证
    - 实现 `validate_consistency()` 一致性验证
    - _需求 3.1, 3.2: 多维验证_
  
  - [x] 5.2 集成 Ragas 和 DeepEval
    - 集成 Ragas 框架进行语义评估
    - 集成 DeepEval 框架进行深度评估
    - _需求 3.3, 3.4: 框架集成_
  
  - [x] 5.3 实现报告生成
    - 实现 `generate_report()` 报告生成
    - 实现自定义验证规则
    - _需求 3.5, 3.6: 报告和自定义规则_
  
  - [x] 5.4 编写 Post-Validation 属性测试
    - **Property 8: 验证报告完整性**
    - **Validates: Requirements 3.2**

- [x] 6. Plugin Manager 和第三方适配器
  - [x] 6.1 创建插件接口规范
    - 创建 `src/ai/annotation_plugin_interface.py`
    - 定义 `AnnotationPluginInterface` 抽象类
    - 定义必要的接口方法
    - _需求 8.1: 插件接口规范_
  
  - [x] 6.2 实现 Plugin Manager
    - 创建 `src/ai/annotation_plugin_manager.py`
    - 实现插件注册、注销、启用、禁用
    - 实现接口验证逻辑
    - 实现优先级管理
    - _需求 8.2, 9.6: 插件管理_
  
  - [x] 6.3 实现第三方适配器
    - 创建 `src/ai/third_party_adapter.py`
    - 实现请求/响应格式转换
    - 实现 Label Studio 格式转换
    - 实现自动回退机制
    - _需求 8.4, 8.5, 8.7: 格式转换和回退_
  
  - [x] 6.4 实现主流工具适配器
    - 创建 `src/ai/adapters/` 目录
    - 实现 REST API 适配器基类
    - 实现 Prodigy 适配器示例
    - _需求 8.3, 8.6: 对接方式和工具支持_
  
  - [x] 6.5 实现调用统计
    - 实现调用日志记录
    - 实现统计计算（成功率、延迟、成本）
    - _需求 8.8, 9.5: 调用统计_
  
  - [x] 6.6 编写插件管理属性测试
    - **Property 6: 插件接口验证**
    - **Property 7: 自动回退机制**
    - **Validates: Requirements 8.2, 8.7**

- [x] 7. Method Switcher 实现
  - [x] 7.1 创建方法切换器
    - 创建 `src/ai/annotation_switcher.py`
    - 实现 `annotate()` 统一入口
    - 实现方法路由逻辑
    - _需求 4.1, 4.2, 4.3: 方法切换_
  
  - [x] 7.2 实现热切换和对比
    - 实现方法热切换
    - 实现 `compare_methods()` 方法对比
    - 实现切换日志记录
    - _需求 4.4, 4.5, 4.6: 热切换和对比_
  
  - [x] 7.3 编写 Method Switcher 属性测试
    - **Property 2: 方法路由正确性**
    - **Validates: Requirements 4.2, 4.3**

- [x] 8. Checkpoint - 确保核心 AI 功能完成
  - 验证验证引擎
  - 验证第三方工具对接
  - 验证方法切换
  - 确保所有测试通过，如有问题请询问用户

- [x] 9. Collaboration Manager 实现
  - [x] 9.1 创建协作管理器
    - 创建 `src/ai/collaboration_manager.py`
    - 实现 `assign_task()` 任务分配
    - 实现角色权限检查
    - _需求 5.1, 5.2, 5.3: 角色和分配_
  
  - [x] 9.2 实现自动分配和统计
    - 实现 `auto_assign_to_reviewer()` 自动分配
    - 实现 `get_workload()` 工作量统计
    - 实现 `get_team_statistics()` 团队统计
    - _需求 5.4, 5.5, 5.6: 自动分配和统计_

- [x] 10. Review Flow Engine 实现
  - [x] 10.1 创建审核流引擎
    - 创建 `src/ai/review_flow.py`
    - 实现审核流程配置
    - 实现 `submit_for_review()` 提交审核
    - _需求 6.1, 6.2: 审核流程_
  
  - [x] 10.2 实现审核操作
    - 实现 `approve()` 审核通过
    - 实现 `reject()` 审核驳回
    - 实现 `modify()` 审核修改
    - _需求 6.3: 审核操作_
  
  - [x] 10.3 实现批量审核和历史
    - 实现 `batch_approve()` 批量审核
    - 实现 `get_review_history()` 审核历史
    - _需求 6.5, 6.6: 历史和批量_
  
  - [x] 10.4 编写 Review Flow 属性测试
    - **Property 4: 审核驳回退回**
    - **Validates: Requirements 6.4**

- [x] 11. API 路由实现
  - [x] 11.1 创建标注任务 API
    - 创建 `src/api/annotation.py`
    - 实现预标注、覆盖、验证 API
    - _需求 1.1, 2.1, 3.1: 标注 API_
  
  - [x] 11.2 实现审核 API
    - 实现审核提交、通过、驳回 API
    - 实现审核历史 API
    - _需求 6.2, 6.3, 6.5: 审核 API_
  
  - [x] 11.3 实现协作 API
    - 实现任务分配 API
    - 实现工作量统计 API
    - _需求 5.2, 5.6: 协作 API_
  
  - [x] 11.4 实现插件管理 API
    - 实现插件 CRUD API
    - 实现插件启用/禁用 API
    - 实现插件统计 API
    - _需求 9.1, 9.4, 9.5: 插件 API_
  
  - [x] 11.5 编写 API 属性测试
    - **Property 3: 第三方工具格式转换往返**
    - **Validates: Requirements 8.4, 8.5**

- [x] 12. 前端实现 - 标注界面
  - [x] 12.1 增强标注界面
    - 扩展 `frontend/src/pages/annotation/` 目录
    - 集成 Label Studio 标注界面
    - 显示 AI 预标注结果和置信度
    - _需求 7.1, 7.2: 标注界面_
  
  - [x] 12.2 实现标注交互
    - 实现修改历史记录
    - 实现快捷键操作
    - 实现进度和统计显示
    - _需求 7.3, 7.4, 7.5: 标注交互_

- [x] 13. 前端实现 - 审核和插件配置
  - [x] 13.1 创建审核界面
    - 创建 `frontend/src/pages/annotation/Review.tsx`
    - 实现审核列表和操作
    - 实现批量审核功能
    - _需求 6.2, 6.6: 审核界面_
  
  - [x] 13.2 创建插件配置界面
    - 创建 `frontend/src/pages/admin/AnnotationPlugins.tsx`
    - 实现插件列表和状态展示
    - 实现添加/编辑/删除插件表单
    - 实现连接测试功能
    - _需求 9.1, 9.2, 9.3: 插件配置_
  
  - [x] 13.3 实现插件高级配置
    - 实现启用/禁用开关
    - 实现优先级配置
    - 实现标注类型映射配置
    - 实现调用统计展示
    - _需求 9.4, 9.5, 9.6, 9.7: 高级配置_
  
  - [x] 13.4 编写前端单元测试
    - 测试标注界面交互
    - 测试插件配置表单
    - _前端测试_

- [x] 14. Checkpoint - 确保前端功能完成
  - 验证标注界面
  - 验证审核界面
  - 验证插件配置界面
  - 确保所有测试通过，如有问题请询问用户

- [x] 15. 集成测试和文档
  - [x] 15.1 编写端到端集成测试
    - 测试完整的预标注 → 审核 → 验证流程
    - 测试第三方工具对接
    - 测试人机协作场景
    - _集成测试_
  
  - [x] 15.2 更新 API 文档
    - 更新 OpenAPI 文档
    - 添加标注 API 使用示例
    - _文档更新_
  
  - [x] 15.3 创建插件开发指南
    - 编写第三方标注工具对接指南
    - 提供插件开发模板
    - _需求 8.1: 插件接口文档_

- [x] 16. Final Checkpoint - 确保所有功能完成
  - 运行完整测试套件
  - 验证所有需求已实现
  - 确保所有测试通过，如有问题请询问用户

- [x] 17. AI 学习引擎实现
  - [x] 17.1 创建 AI 学习引擎
    - 创建 `src/ai/ai_learning_engine.py`
    - 实现 `start_learning()` 方法，接受项目 ID 和样本 ID 列表
    - 实现样本数量验证（最少 10 个样本）
    - 实现模式识别和特征提取
    - _需求 10.3, 11.3: AI 学习触发和样本数量验证_
  
  - [x] 17.2 实现学习进度跟踪
    - 实现 `get_learning_progress()` 方法
    - 实时计算识别的模式数量
    - 实时计算平均置信度
    - 推荐最优标注方法
    - _需求 10.5, 11.4: 学习进度显示_
  
  - [x] 17.3 实现学习结果存储
    - 创建 AILearningJob 数据库模型
    - 存储学习任务状态和结果
    - 存储识别的标注模式
    - _需求 11.3, 11.4: 学习任务管理_
  
  - [x] 17.4 编写 AI 学习属性测试
    - **Property 9: 学习样本数量要求**
    - **Validates: Requirements 10.3**

- [x] 18. 批量标注任务管理
  - [x] 18.1 创建批量标注引擎
    - 创建 `src/ai/batch_annotation_engine.py`
    - 实现 `start_batch_annotation()` 方法
    - 接受项目 ID、学习任务 ID、目标数据集 ID、标注类型、置信度阈值
    - 集成 Pre-Annotation Engine
    - _需求 10.7, 11.5: 批量标注启动_
  
  - [x] 18.2 实现批量标注进度跟踪
    - 实现 `get_batch_progress()` 方法
    - 实时统计已标注数量、需要审核数量
    - 实时计算平均置信度
    - 返回最近标注结果
    - _需求 10.6, 11.6: 批量标注进度_
  
  - [x] 18.3 实现批量标注结果存储
    - 创建 BatchAnnotationJob 数据库模型
    - 存储批量任务状态和统计信息
    - 关联学习任务和标注结果
    - _需求 11.5, 11.6: 批量任务管理_
  
  - [x] 18.4 编写批量标注属性测试
    - **Property 10: 批量标注进度一致性**
    - **Validates: Requirements 10.6**

- [x] 19. 效果验证引擎
  - [x] 19.1 扩展 Post-Validation Engine
    - 扩展 `src/ai/post_validation.py`
    - 实现 `validate_ai_effect()` 方法
    - 接受项目 ID、批量任务 ID、测试样本数、测试方式
    - 支持三种测试方式：随机、低置信度优先、多样性采样
    - _需求 10.9, 11.7: 效果验证_
  
  - [x] 19.2 实现质量指标计算
    - 计算准确率、召回率、F1 分数、一致性
    - 生成混淆矩阵
    - 识别错误案例
    - 生成改进建议
    - _需求 10.8, 11.7: 验证结果_
  
  - [x] 19.3 编写效果验证属性测试
    - **Property 12: 效果验证指标完整性**
    - **Validates: Requirements 10.8**

- [x] 20. 迭代管理
  - [x] 20.1 创建迭代管理器
    - 创建 `src/ai/iteration_manager.py`
    - 实现 `record_iteration()` 方法
    - 自动记录样本数、标注数、质量指标、耗时
    - 关联学习任务和批量任务
    - _需求 10.11, 11.10: 迭代记录_
  
  - [x] 20.2 实现迭代历史查询
    - 实现 `get_iteration_history()` 方法
    - 返回项目的所有迭代记录
    - 支持按时间排序
    - _需求 10.10, 11.8: 迭代历史_
  
  - [x] 20.3 实现新迭代启动
    - 实现 `start_new_iteration()` 方法
    - 接受项目 ID、数据源 ID、迭代配置
    - 初始化新的迭代记录
    - _需求 10.12, 11.9: 新迭代_
  
  - [x] 20.4 创建迭代记录数据库模型
    - 创建 IterationRecord 数据库模型
    - 存储迭代编号、样本数、标注数、质量指标
    - 关联学习任务和批量任务
    - _需求 11.10: 迭代数据存储_
  
  - [x] 20.5 编写迭代管理属性测试
    - **Property 11: 迭代记录完整性**
    - **Validates: Requirements 10.11**

- [x] 21. Checkpoint - 确保 AI 工作流核心功能完成
  - 验证 AI 学习引擎
  - 验证批量标注引擎
  - 验证效果验证引擎
  - 验证迭代管理
  - 确保所有测试通过，如有问题请询问用户

- [x] 22. 工作流 API 实现
  - [x] 22.1 实现数据源 API
    - 扩展 `src/api/annotation.py`
    - 实现 `GET /workflow/data-sources` 端点
    - 返回非结构化处理后数据和原始数据列表
    - _需求 10.2, 11.1: 数据源列表_
  
  - [x] 22.2 实现已标注样本 API
    - 实现 `GET /workflow/annotated-samples` 端点
    - 返回总数、平均质量、标注类型、覆盖率、质量分布
    - _需求 10.3, 11.2: 样本信息_
  
  - [x] 22.3 实现 AI 学习 API
    - 实现 `POST /workflow/ai-learn` 端点
    - 实现 `GET /workflow/ai-learn/{job_id}` 端点
    - 触发学习和查询进度
    - _需求 10.3, 10.5, 11.3, 11.4: AI 学习 API_
  
  - [x] 22.4 实现批量标注 API
    - 实现 `POST /workflow/batch-annotate` 端点
    - 实现 `GET /workflow/batch-annotate/{job_id}` 端点
    - 启动批量标注和查询进度
    - _需求 10.6, 10.7, 11.5, 11.6: 批量标注 API_
  
  - [x] 22.5 实现效果验证 API
    - 实现 `POST /workflow/validate-effect` 端点
    - 触发效果验证并返回结果
    - _需求 10.8, 10.9, 11.7: 效果验证 API_
  
  - [x] 22.6 实现迭代管理 API
    - 实现 `GET /workflow/iterations` 端点
    - 实现 `POST /workflow/iterations/start` 端点
    - 查询迭代历史和启动新迭代
    - _需求 10.10, 10.12, 11.8, 11.9: 迭代 API_
  
  - [x] 22.7 编写工作流 API 属性测试
    - **Property 8: 工作流步骤顺序**
    - **Validates: Requirements 11.11**

- [x] 23. 数据库迁移 - AI 工作流表
  - [x] 23.1 创建 AI 工作流数据库迁移
    - 创建 Alembic 迁移脚本
    - 添加 `ai_learning_jobs` 表
    - 添加 `batch_annotation_jobs` 表
    - 添加 `iteration_records` 表
    - _需求 11.3, 11.5, 11.10: 数据库表_

- [x] 24. 前端实现 - AIProcessingPage
  - [x] 24.1 创建 AIProcessingPage 主页面
    - 创建 `frontend/src/pages/Augmentation/AIProcessing.tsx`
    - 实现页面状态管理
    - 实现步骤导航
    - 配置路由 `/augmentation/ai-processing`
    - _需求 10.1: 主页面_
  
  - [x] 24.2 实现 WorkflowVisualization 组件
    - 创建 `frontend/src/components/AIWorkflow/WorkflowVisualization.tsx`
    - 使用流程图展示工作流（数据来源 → 人工样本 → AI 学习 → 批量标注 → 效果验证 → 循环迭代）
    - 高亮当前步骤
    - _需求 10.1: 工作流可视化_
  
  - [x] 24.3 实现 DataSourceSelector 组件
    - 创建 `frontend/src/components/AIWorkflow/DataSourceSelector.tsx`
    - 支持选择非结构化处理后数据或原始数据
    - 显示数据预览和统计信息
    - _需求 10.2: 数据来源选择_
  
  - [x] 24.4 实现 AnnotatedSamplesPanel 组件
    - 创建 `frontend/src/components/AIWorkflow/AnnotatedSamplesPanel.tsx`
    - 显示样本数量、平均质量、标注类型、覆盖率
    - 显示质量分布图表
    - 显示样本列表
    - 实现触发 AI 学习按钮（样本数 >= 10）
    - _需求 10.3, 10.4: 样本面板_
  
  - [x] 24.5 实现 AILearningPanel 组件
    - 创建 `frontend/src/components/AIWorkflow/AILearningPanel.tsx`
    - 显示学习进度条
    - 显示识别的模式数量、平均置信度、推荐方法
    - 显示模式可视化和置信度分布图
    - _需求 10.5: AI 学习面板_
  
  - [x] 24.6 实现 BatchAnnotationPanel 组件
    - 创建 `frontend/src/components/AIWorkflow/BatchAnnotationPanel.tsx`
    - 实现配置表单（目标数据集、标注类型、置信度阈值）
    - 实时显示已标注数量、平均置信度、需要审核数量
    - 显示标注结果流
    - _需求 10.6, 10.7: 批量标注面板_
  
  - [x] 24.7 实现 EffectValidationPanel 组件
    - 创建 `frontend/src/components/AIWorkflow/EffectValidationPanel.tsx`
    - 实现测试配置表单（测试样本数、测试方式）
    - 显示验证结果（准确率、召回率、F1 分数、一致性）
    - 显示混淆矩阵和错误案例
    - 显示改进建议
    - _需求 10.8, 10.9: 效果验证面板_
  
  - [x] 24.8 实现 IterationComparison 组件
    - 创建 `frontend/src/components/AIWorkflow/IterationComparison.tsx`
    - 表格展示历史迭代（迭代编号、样本数、标注数、准确率、F1 分数、耗时、时间）
    - 显示质量趋势图（准确率和 F1 分数变化）
    - 支持启动新迭代
    - _需求 10.10, 10.11, 10.12: 迭代对比_
  
  - [x] 24.9 编写前端单元测试
    - 测试 AIProcessingPage 组件渲染
    - 测试工作流步骤切换
    - 测试数据来源选择
    - 测试 AI 学习进度更新
    - 测试批量标注进度显示
    - 测试效果验证结果展示
    - 测试迭代对比图表
    - _前端测试_

- [x] 25. Checkpoint - 确保 AI 工作流前端完成
  - 验证 AIProcessingPage 页面
  - 验证所有子组件
  - 验证工作流步骤流转
  - 确保所有测试通过，如有问题请询问用户

- [x] 26. 集成测试 - AI 工作流
  - [x] 26.1 编写完整工作流集成测试
    - 测试数据来源 → AI 学习 → 批量标注 → 效果验证 → 新迭代的完整流程
    - 测试工作流步骤顺序验证
    - 测试样本数量不足时的错误提示
    - 测试批量标注进度一致性
    - 测试迭代记录自动生成
    - _需求 10.1-10.12, 11.1-11.11: 完整工作流_
  
  - [x] 26.2 更新 API 文档
    - 更新 OpenAPI 文档
    - 添加 9 个新的工作流 API 端点文档
    - 添加 API 使用示例
    - _文档更新_

- [x] 27. Final Checkpoint - 确保 AI 工作流功能完成
  - 运行完整测试套件
  - 验证所有新需求已实现（需求 10 和 11）
  - 验证所有新属性测试通过（Property 8-12）
  - 确保所有测试通过，如有问题请询问用户

## Notes

- 所有任务（包括测试任务）均为必须完成
- 每个任务引用具体需求以确保可追溯性
- Checkpoint 任务用于阶段性验证
- 属性测试使用 Hypothesis 库，每个属性至少运行 100 次
- 复用 llm-integration 模块的 LLM Switcher
- 第三方工具适配器采用插件架构，便于扩展
- 标注界面基于 Label Studio 集成，不重复开发
- 任务标记 `*` 的为可选测试任务，可跳过以加快 MVP 开发
- 新增任务 17-27 实现 AI 标注工作流可视化和循环迭代功能
- AI 学习要求最少 10 个已标注样本
- 工作流步骤必须按顺序执行：数据来源 → AI 学习 → 批量标注 → 效果验证
- 每次完整迭代自动记录质量指标和耗时
