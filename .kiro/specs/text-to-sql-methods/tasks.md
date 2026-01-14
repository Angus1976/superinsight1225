# Implementation Plan: Text-to-SQL Methods (Text-to-SQL 方法)

## Overview

本任务文档将 Text-to-SQL Methods 设计分解为可执行的开发任务，实现多种自然语言转 SQL 方法，包括模板填充、LLM 生成、混合方法，以及第三方专业工具对接。

## Tasks

- [x] 1. 核心数据模型和基础设施
  - [x] 1.1 创建数据模型
    - 创建 `src/text-to-sql/schemas.py`，定义 `SQLGenerationResult`、`MethodInfo`、`PluginConfig` 等 Pydantic 模型
    - 创建 `src/models/text_to_sql.py`，定义 `TextToSQLConfiguration`、`ThirdPartyPlugin`、`SQLGenerationLog` SQLAlchemy 模型
    - _需求 4.1, 6.1: 配置模型和插件接口_
  
  - [x] 1.2 创建数据库迁移
    - 创建 Alembic 迁移脚本，添加 `text_to_sql_configurations`、`third_party_plugins`、`sql_generation_logs` 表
    - 添加索引优化查询性能
    - _需求 4.1: 配置持久化_
  
  - [x] 1.3 创建目录结构
    - 创建 `src/text-to-sql/` 目录
    - 创建 `__init__.py` 和基础模块文件
    - _基础设施_

- [x] 2. Schema Analyzer 实现
  - [x] 2.1 实现 Schema 分析器
    - 创建 `src/text-to-sql/schema_analyzer.py`
    - 实现 `analyze()` 方法提取表结构信息
    - 实现 `to_llm_context()` 生成 LLM 友好描述
    - _需求 5.1, 5.2, 5.4: Schema 分析_
  
  - [x] 2.2 实现相关表筛选
    - 实现 `filter_relevant_tables()` 方法
    - 支持表数量超过 50 时的智能筛选
    - 实现增量更新 `incremental_update()`
    - _需求 5.3, 5.5: 增量更新和筛选_
  
  - [x] 2.3 编写 Schema Analyzer 属性测试
    - **Property 6: Schema 信息完整性**
    - **Validates: Requirements 5.2**

- [x] 3. Checkpoint - 确保 Schema 分析基础完成
  - 验证 Schema 提取功能
  - 确保所有测试通过，如有问题请询问用户


- [x] 4. Template Filler 实现
  - [x] 4.1 创建模板填充器
    - 创建 `src/text-to-sql/basic.py`，实现 `TemplateFiller` 类
    - 实现 `match_template()` 模板匹配
    - 实现 `fill_template()` 参数填充
    - _需求 1.1, 1.2: 模板匹配和填充_
  
  - [x] 4.2 创建预定义模板
    - 创建 `src/text-to-sql/templates/` 目录
    - 创建聚合、筛选、排序、分组、连接查询模板
    - 实现模板加载和管理
    - _需求 1.3: 模板类型_
  
  - [x] 4.3 实现参数类型验证
    - 实现 `validate_params()` 方法
    - 支持数字、字符串、日期类型验证
    - 实现匹配失败回退建议
    - _需求 1.4, 1.5: 参数验证和回退_
  
  - [x] 4.4 编写 Template Filler 属性测试
    - **Property 5: 参数类型验证**
    - **Validates: Requirements 1.5**

- [x] 5. LLM SQL Generator 实现
  - [x] 5.1 创建 LLM 生成器
    - 创建 `src/text-to-sql/llm-based.py`，实现 `LLMSQLGenerator` 类
    - 集成 LLM Switcher（复用 llm-integration 模块）
    - 实现 `build_prompt()` 构建 prompt
    - _需求 2.1, 2.2: LLM 生成_
  
  - [x] 5.2 实现 SQL 验证和重试
    - 实现 `validate_sql()` SQL 语法验证
    - 实现 `retry_generate()` 重试机制（最多 3 次）
    - 支持 LangChain 和 SQLCoder 框架
    - _需求 2.3, 2.4, 2.5: 验证和重试_
  
  - [x] 5.3 编写 LLM Generator 属性测试
    - **Property 1: SQL 语法正确性**
    - **Validates: Requirements 1.2, 2.4**

- [x] 6. Hybrid Generator 实现
  - [x] 6.1 创建混合生成器
    - 创建 `src/text-to-sql/hybrid.py`，实现 `HybridGenerator` 类
    - 实现模板优先、LLM 回退逻辑
    - 实现规则后处理优化
    - _需求 3.1, 3.2, 3.3: 混合方法_
  
  - [x] 6.2 实现方法记录和置信度
    - 实现 `log_method_usage()` 方法记录
    - 实现置信度计算和返回
    - _需求 3.4, 3.5: 记录和置信度_
  
  - [x] 6.3 编写 Hybrid Generator 属性测试
    - **Property 3: 混合方法优先级**
    - **Validates: Requirements 3.1, 3.2**

- [x] 7. Checkpoint - 确保内置方法完成
  - 验证模板、LLM、混合方法
  - 确保所有测试通过，如有问题请询问用户

- [x] 8. Plugin Manager 和第三方适配器
  - [x] 8.1 创建插件接口规范
    - 创建 `src/text-to-sql/plugin_interface.py`，定义 `PluginInterface` 抽象类
    - 定义必要的接口方法：`get_info`、`to_native_format`、`call`、`from_native_format`、`health_check`
    - _需求 6.1: 插件接口规范_
  
  - [x] 8.2 实现 Plugin Manager
    - 创建 `src/text-to-sql/plugin_manager.py`，实现 `PluginManager` 类
    - 实现插件注册、注销、启用、禁用
    - 实现接口验证逻辑
    - _需求 6.2: 接口验证_
  
  - [x] 8.3 实现第三方适配器
    - 创建 `src/text-to-sql/third_party_adapter.py`，实现 `ThirdPartyAdapter` 类
    - 实现请求/响应格式转换
    - 实现自动回退机制
    - _需求 6.4, 6.5, 6.7: 格式转换和回退_
  
  - [x] 8.4 实现主流工具适配器
    - 创建 `src/text-to-sql/adapters/` 目录
    - 实现 REST API 适配器基类
    - 实现 Vanna.ai 适配器示例
    - _需求 6.3, 6.6: 对接方式和工具支持_
  
  - [x] 8.5 编写插件管理属性测试
    - **Property 7: 插件接口验证**
    - **Property 8: 自动回退机制**
    - **Validates: Requirements 6.2, 6.7**

- [x] 9. Method Switcher 实现
  - [x] 9.1 创建方法切换器
    - 创建 `src/text-to-sql/switcher.py`，实现 `MethodSwitcher` 类
    - 实现 `generate_sql()` 统一入口
    - 实现方法路由逻辑
    - _需求 4.1, 4.2, 4.3: 方法切换_
  
  - [x] 9.2 实现自动方法选择
    - 实现 `auto_select_method()` 基于场景选择
    - 支持基于数据库类型的选择
    - 确保切换在 500ms 内完成
    - _需求 4.4, 4.5: 自动选择_
  
  - [x] 9.3 编写 Method Switcher 属性测试
    - **Property 2: 方法路由正确性**
    - **Validates: Requirements 4.1, 4.2**

- [x] 10. Checkpoint - 确保核心功能完成
  - 验证所有方法和切换逻辑 ✓
  - 验证第三方工具对接 ✓
  - 确保所有测试通过 ✓ (88 tests passed)

- [x] 11. API 路由实现
  - [x] 11.1 创建 Text-to-SQL API 路由
    - 创建 `src/api/text_to_sql.py`，实现 API 路由
    - 实现 `POST /api/v1/text-to-sql/methods/generate` 生成接口
    - 实现 `GET /api/v1/text-to-sql/methods` 列出方法
    - 实现 `POST /api/v1/text-to-sql/methods/test` 测试生成
    - _需求 7.4, 7.5: 测试功能_
  
  - [x] 11.2 实现配置 API
    - 实现 `GET /api/v1/text-to-sql/config` 获取配置
    - 实现 `PUT /api/v1/text-to-sql/config` 更新配置
    - _需求 7.3: 配置保存_
  
  - [x] 11.3 实现插件管理 API
    - 实现插件 CRUD API
    - 实现插件启用/禁用 API
    - 实现插件健康检查 API
    - _需求 7.6, 7.7, 7.8: 插件管理_
  
  - [x] 11.4 注册路由到主应用
    - 在 `src/app.py` 和 `src/app_auth.py` 中注册路由 (已存在)
    - 添加权限控制
    - _需求 7.1: 页面访问_
  
  - [x] 11.5 编写 API 属性测试
    - **Property 4: 第三方工具格式转换往返**
    - **Validates: Requirements 6.4, 6.5**

- [x] 12. 前端配置页面实现
  - [x] 12.1 创建 Text-to-SQL 配置页面
    - 创建 `frontend/src/pages/admin/TextToSQLConfig.tsx`
    - 实现方法选择器和配置表单
    - 实现方法特点预览
    - _需求 7.1, 7.2: 配置页面_
  
  - [x] 12.2 实现 SQL 测试功能
    - 实现自然语言输入框
    - 实现 SQL 预览和方法显示
    - 实现置信度显示
    - _需求 7.4, 7.5: 测试功能_
  
  - [x] 12.3 实现第三方工具管理界面
    - 实现插件列表展示
    - 实现添加/编辑/删除插件表单
    - 实现启用/禁用开关
    - 实现健康状态和调用统计显示
    - _需求 7.6, 7.7, 7.8: 插件管理界面_
  
  - [x] 12.4 添加路由和菜单
    - 在 `frontend/src/router/routes.tsx` 中添加路由
    - 在管理员菜单中添加入口
    - _需求 7.1: 页面访问_
  
  - [x] 12.5 编写前端单元测试
    - 测试配置表单验证
    - 测试插件管理功能
    - _需求 7.2, 7.6_

- [x] 13. Checkpoint - 确保前端功能完成
  - 验证配置页面渲染 ✓
  - 验证 SQL 测试功能 ✓
  - 验证插件管理界面 ✓
  - 确保所有测试通过 ✓

- [x] 14. 集成测试和文档
  - [x] 14.1 编写端到端集成测试
    - 测试完整的查询 → SQL 生成流程
    - 测试第三方工具对接
    - 测试回退机制
    - _需求 6.7: 回退验证_
  
  - [x] 14.2 更新 API 文档
    - 更新 OpenAPI 文档 (自动生成)
    - 添加 Text-to-SQL API 使用示例
    - _文档更新_
  
  - [x] 14.3 创建插件开发指南
    - 编写第三方工具对接指南 `docs/text-to-sql-plugin-guide.md`
    - 提供插件开发模板
    - _需求 6.1: 插件接口文档_

- [x] 15. Final Checkpoint - 确保所有功能完成
  - 运行完整测试套件 ✓ (110 tests passed)
  - 验证所有需求已实现 ✓
  - 确保所有测试通过 ✓

## Notes

- 所有任务（包括测试任务）均为必须完成
- 每个任务引用具体需求以确保可追溯性
- Checkpoint 任务用于阶段性验证
- 属性测试使用 Hypothesis 库，每个属性至少运行 100 次
- 复用 llm-integration 模块的 LLM Switcher
- 第三方工具适配器采用插件架构，便于扩展
