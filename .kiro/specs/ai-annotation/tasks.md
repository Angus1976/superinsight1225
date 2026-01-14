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

## Notes

- 所有任务（包括测试任务）均为必须完成
- 每个任务引用具体需求以确保可追溯性
- Checkpoint 任务用于阶段性验证
- 属性测试使用 Hypothesis 库，每个属性至少运行 100 次
- 复用 llm-integration 模块的 LLM Switcher
- 第三方工具适配器采用插件架构，便于扩展
- 标注界面基于 Label Studio 集成，不重复开发
