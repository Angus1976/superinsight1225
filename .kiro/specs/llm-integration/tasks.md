# Implementation Plan: LLM Integration (LLM 基础能力)

## Overview

本任务文档将 LLM Integration 设计分解为可执行的开发任务，按照增量开发原则，每个任务构建在前一个任务之上，最终实现完整的 LLM 统一调用能力。

## Tasks

- [x] 1. 核心数据模型和配置管理
  - [x] 1.1 创建 LLM 配置数据模型
    - 创建 `src/ai/llm_schemas.py`，定义 `LLMConfig`、`GenerateOptions`、`LLMResponse`、`LLMError` 等 Pydantic 模型
    - 创建 `src/models/llm_configuration.py`，定义 `LLMConfiguration`、`LLMUsageLog` SQLAlchemy 模型
    - _需求 4.1, 6.4: 配置模型和统一响应格式_
  
  - [x] 1.2 创建数据库迁移
    - 创建 Alembic 迁移脚本，添加 `llm_configurations` 和 `llm_usage_logs` 表
    - 添加索引优化查询性能
    - _需求 4.1: 配置持久化_
  
  - [x] 1.3 实现配置管理器
    - 创建 `src/ai/llm_config_manager.py`，实现 `LLMConfigManager` 类
    - 实现配置的 CRUD 操作（get_config, save_config, validate_config）
    - 实现 Redis 缓存层
    - 实现配置变更监听和热加载
    - _需求 4.4: 热加载配置_
  
  - [x] 1.4 编写配置管理器属性测试
    - **Property 5: 配置热加载**
    - **Validates: Requirements 4.3, 4.4**

- [x] 2. Checkpoint - 确保配置管理基础完成
  - 运行数据库迁移
  - 验证配置 CRUD 操作
  - 确保所有测试通过，如有问题请询问用户

- [x] 3. LLM Switcher 核心实现
  - [x] 3.1 创建 LLM Switcher 基础框架
    - 创建 `src/ai/llm_switcher.py`，实现 `LLMSwitcher` 类
    - 实现 `generate(prompt, options, method)` 统一接口
    - 实现 `embed(text, method)` 向量化接口
    - 实现方法路由逻辑（根据配置或参数选择 Provider）
    - _需求 6.1, 6.2, 6.3: 统一调用接口_
  
  - [x] 3.2 实现方法切换逻辑
    - 实现 `switch_method(method)` 切换默认方法
    - 实现 `get_current_method()` 获取当前方法
    - 实现 `list_available_methods()` 列出可用方法
    - 确保切换不中断正在进行的请求
    - _需求 4.2, 4.3, 4.5: 方法切换_
  
  - [x] 3.3 编写 LLM Switcher 属性测试
    - **Property 2: 方法路由正确性**
    - **Validates: Requirements 4.1, 4.2, 6.3**

- [x] 4. Local Provider 实现 (Ollama)
  - [x] 4.1 扩展现有 Ollama 集成
    - 创建 `src/ai/llm_docker.py`，实现 `LocalLLMProvider` 类
    - 复用现有 `OllamaAnnotator` 的连接逻辑
    - 实现 `start_service(model_name)` 启动服务
    - 实现 `generate(prompt, options)` 生成接口
    - 实现 `list_models()` 列出可用模型
    - _需求 1.1, 1.2, 1.5: 本地 LLM 部署_
  
  - [x] 4.2 实现健康检查和超时机制
    - 实现 `health_check()` 健康检查
    - 实现 30 秒超时机制
    - 实现服务不可用时的错误处理
    - _需求 1.3, 1.4: 超时和错误处理_
  
  - [x] 4.3 编写 Local Provider 属性测试
    - **Property 3: 超时机制**
    - **Property 7: 错误处理一致性**
    - **Validates: Requirements 1.3, 1.4, 2.5**

- [x] 5. Checkpoint - 确保本地 LLM 功能完成
  - 验证 Ollama 连接和生成
  - 验证超时机制
  - 确保所有测试通过，如有问题请询问用户

- [x] 6. Cloud Provider 实现
  - [x] 6.1 实现云端 LLM Provider
    - 创建 `src/ai/llm_cloud.py`，实现 `CloudLLMProvider` 类
    - 实现 OpenAI API 调用
    - 实现 `validate_api_key(api_key)` API Key 验证
    - 实现 `generate(prompt, options)` 生成接口
    - _需求 2.1, 2.2: 云端 LLM 调用_
  
  - [x] 6.2 实现流式响应和超时
    - 实现 `stream_generate(prompt, options)` 流式生成
    - 实现 60 秒超时机制
    - 实现错误码解析和用户友好错误信息
    - _需求 2.3, 2.4, 2.5: 流式响应和错误处理_
  
  - [x] 6.3 编写 Cloud Provider 单元测试
    - 测试 API Key 验证逻辑
    - 测试错误码解析
    - _需求 2.1, 2.3_

- [x] 7. China LLM Adapter 实现
  - [x] 7.1 创建中国 LLM 适配器框架
    - 创建 `src/ai/china_llm_adapter.py`，实现 `ChinaLLMAdapter` 基类
    - 定义统一的请求/响应转换接口
    - _需求 3.3, 3.4: 格式转换_
  
  - [x] 7.2 实现千问 (Qwen) 适配器
    - 实现 `QwenAdapter` 类
    - 调用阿里云 DashScope API
    - 实现请求格式转换（统一格式 → DashScope 格式）
    - 实现响应格式转换（DashScope 格式 → 统一格式）
    - _需求 3.1: 千问适配_
  
  - [x] 7.3 实现智谱 (Zhipu) 适配器
    - 实现 `ZhipuAdapter` 类，扩展现有 `ZhipuAnnotator`
    - 调用智谱 AI 开放平台 API
    - 实现请求/响应格式转换
    - _需求 3.2: 智谱适配_
  
  - [x] 7.4 实现限流重试策略
    - 实现指数退避重试逻辑
    - 重试间隔：1s, 2s, 4s, 8s...
    - 最大重试次数：5 次
    - _需求 3.5: 限流重试_
  
  - [x] 7.5 编写 China LLM Adapter 属性测试
    - **Property 4: 中国 LLM 格式转换往返**
    - **Property 8: 限流重试策略**
    - **Validates: Requirements 3.3, 3.4, 3.5**

- [x] 8. Checkpoint - 确保所有 Provider 完成
  - 验证本地、云端、中国 LLM 调用
  - 验证格式转换正确性
  - 确保所有测试通过，如有问题请询问用户

- [x] 9. API 路由实现
  - [x] 9.1 创建 LLM API 路由
    - 创建 `src/api/llm.py`，实现 API 路由
    - 实现 `POST /api/v1/llm/generate` 生成接口
    - 实现 `POST /api/v1/llm/embed` 向量化接口
    - 实现 `GET /api/v1/llm/methods` 列出方法
    - _需求 6.1, 6.2: 统一接口_
  
  - [x] 9.2 实现配置 API
    - 实现 `GET /api/v1/llm/config` 获取配置
    - 实现 `PUT /api/v1/llm/config` 更新配置
    - 实现 `POST /api/v1/llm/config/test` 测试连接
    - 实现 API Key 脱敏响应
    - _需求 5.3, 5.4, 5.5: 配置管理_
  
  - [x] 9.3 实现健康检查 API
    - 实现 `GET /api/v1/llm/health` 健康检查
    - 返回所有 Provider 的健康状态
    - _需求 1.2: 健康状态_
  
  - [x] 9.4 注册路由到主应用
    - 在 `src/app.py` 和 `src/app_auth.py` 中注册 LLM 路由
    - 添加权限控制（管理员可配置，用户可调用）
    - _需求 5.1: 配置页面访问_
  
  - [x] 9.5 编写 API 属性测试
    - **Property 1: 统一响应格式**
    - **Property 6: API Key 脱敏**
    - **Validates: Requirements 5.5, 6.4, 6.5**

- [x] 10. 前端配置页面实现
  - [x] 10.1 创建 LLM 配置页面
    - 创建 `frontend/src/pages/Admin/LLMConfig.tsx`
    - 实现配置表单（本地、云端、中国 LLM）
    - 实现方法选择器
    - _需求 5.1: 配置页面_
  
  - [x] 10.2 实现配置验证和保存
    - 实现实时配置验证
    - 实现配置保存功能
    - 实现 API Key 脱敏显示
    - _需求 5.2, 5.3, 5.5: 验证和保存_
  
  - [x] 10.3 实现连接测试功能
    - 实现测试连接按钮
    - 显示连接状态和错误信息
    - _需求 5.4: 测试连接_
  
  - [x] 10.4 添加路由和菜单
    - 在 `frontend/src/router/routes.tsx` 中添加路由
    - 在管理员菜单中添加入口
    - _需求 5.1: 页面访问_
  
  - [x] 10.5 编写前端单元测试
    - 测试配置表单验证
    - 测试 API Key 脱敏显示
    - _需求 5.2, 5.5_

- [x] 11. Checkpoint - 确保前端功能完成
  - 验证配置页面渲染
  - 验证配置保存和加载
  - 验证连接测试功能
  - 确保所有测试通过，如有问题请询问用户

- [x] 12. 集成测试和文档
  - [x] 12.1 编写端到端集成测试
    - 测试完整的配置 → 调用 → 响应流程
    - 测试多租户配置隔离
    - 测试热加载功能
    - _需求 4.4, 6.3: 集成验证_
  
  - [x] 12.2 更新 API 文档
    - 更新 OpenAPI 文档
    - 添加 LLM API 使用示例
    - _文档更新_
  
  - [x] 12.3 更新用户指南
    - 添加 LLM 配置指南
    - 添加中国 LLM 接入指南
    - _文档更新_

- [x] 13. Final Checkpoint - 确保所有功能完成
  - 运行完整测试套件
  - 验证所有需求已实现
  - 确保所有测试通过，如有问题请询问用户

## Notes

- 所有任务（包括测试任务）均为必须完成
- 每个任务引用具体需求以确保可追溯性
- Checkpoint 任务用于阶段性验证
- 属性测试使用 Hypothesis 库，每个属性至少运行 100 次
- 优先复用现有 `src/ai/` 代码，避免重复开发
