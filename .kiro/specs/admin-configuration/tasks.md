# Implementation Plan: Admin Configuration (管理员配置)

## Overview

本任务文档将 Admin Configuration 设计分解为可执行的开发任务，实现平台管理员的可视化配置界面，包括仪表盘、LLM 配置、数据库连接、同步策略、SQL 构建器等功能。

## Tasks

- [x] 1. 核心数据模型和基础设施
  - [x] 1.1 创建数据模型
    - 创建 `src/admin/schemas.py`，定义配置相关 Pydantic 模型
    - 创建 `src/models/admin_config.py`，定义 SQLAlchemy 模型
    - _需求 1.1, 2.1, 3.1: 配置数据模型_
  
  - [x] 1.2 创建数据库迁移
    - 创建 Alembic 迁移脚本
    - 添加 `admin_configurations`、`database_connections`、`config_change_history`、`query_templates` 表
    - _需求 6.1: 配置历史存储_
  
  - [x] 1.3 创建目录结构
    - 创建 `src/admin/` 目录
    - 创建 `__init__.py` 和基础模块文件
    - _基础设施_

- [x] 2. Credential Encryptor 实现
  - [x] 2.1 实现凭证加密器
    - 创建 `src/admin/credential_encryptor.py`
    - 实现 `encrypt()` 和 `decrypt()` 方法
    - 实现 `mask()` 脱敏方法
    - _需求 2.6, 3.6: 敏感信息处理_
  
  - [x] 2.2 编写加密器属性测试
    - **Property 1: 敏感信息脱敏**
    - **Validates: Requirements 2.6, 3.6**

- [x] 3. Config Validator 实现
  - [x] 3.1 实现配置验证器
    - 创建 `src/admin/config_validator.py`
    - 实现 `validate_llm_config()` LLM 配置验证
    - 实现 `validate_db_config()` 数据库配置验证
    - 实现 `validate_sync_config()` 同步策略验证
    - _需求 2.3, 3.4, 4.3: 配置验证_
  
  - [x] 3.2 实现连接测试
    - 实现 `test_db_connection()` 数据库连接测试
    - 实现 `verify_readonly_permission()` 只读权限验证
    - _需求 3.5, 3.7: 连接测试和权限验证_
  
  - [x] 3.3 编写验证器属性测试
    - **Property 2: 数据库连接验证**
    - **Validates: Requirements 3.4, 3.7**

- [x] 4. Checkpoint - 确保基础组件完成
  - 验证加密和验证功能
  - 确保所有测试通过，如有问题请询问用户


- [x] 5. History Tracker 实现
  - [x] 5.1 实现历史追踪器
    - 创建 `src/admin/history_tracker.py`
    - 实现 `record_change()` 记录变更
    - 实现 `get_history()` 获取历史
    - 实现 `get_diff()` 获取差异
    - _需求 6.1, 6.2, 6.3: 历史记录_
  
  - [x] 5.2 实现配置回滚
    - 实现 `rollback()` 回滚功能
    - 确保回滚后配置与历史一致
    - _需求 6.4: 配置回滚_
  
  - [x] 5.3 编写历史追踪属性测试
    - **Property 4: 配置回滚一致性**
    - **Property 5: 配置历史完整性**
    - **Validates: Requirements 6.2, 6.4**

- [x] 6. Config Manager 实现
  - [x] 6.1 实现配置管理器
    - 创建 `src/admin/config_manager.py`
    - 实现 `get_config()` 获取配置
    - 实现 `save_config()` 保存配置（集成历史记录）
    - 实现 `validate_config()` 验证配置
    - 实现 `test_connection()` 测试连接
    - _需求 2.4, 3.4: 配置管理_
  
  - [x] 6.2 集成 Redis 缓存
    - 实现配置缓存
    - 实现缓存失效策略
    - _性能优化_

- [x] 7. SQL Builder Service 实现
  - [x] 7.1 实现 SQL 构建服务
    - 创建 `src/admin/sql_builder.py`
    - 实现 `get_schema()` 获取数据库 Schema
    - 实现 `build_sql()` 构建 SQL
    - 实现 `validate_sql()` 验证 SQL
    - _需求 5.1, 5.4, 5.5: SQL 构建_
  
  - [x] 7.2 实现查询执行和模板
    - 实现 `execute_preview()` 执行预览（限制 100 行）
    - 实现 `save_template()` 保存模板
    - 实现 `list_templates()` 列出模板
    - _需求 5.6, 5.7: 执行和模板_
  
  - [x] 7.3 编写 SQL Builder 属性测试
    - **Property 3: SQL 构建正确性**
    - **Validates: Requirements 5.4, 5.5**

- [x] 8. Sync Strategy Service 实现
  - [x] 8.1 实现同步策略服务
    - 创建 `src/admin/sync_strategy.py`
    - 实现 `get_strategy()` 获取策略
    - 实现 `save_strategy()` 保存策略
    - 实现 `validate_strategy()` 验证策略
    - _需求 4.1, 4.2, 4.3: 同步策略_
  
  - [x] 8.2 实现同步触发和历史
    - 实现 `trigger_sync()` 触发同步
    - 实现 `retry_sync()` 重试同步
    - 实现 `get_sync_history()` 获取同步历史
    - _需求 4.6, 4.7: 同步执行_

- [x] 9. Checkpoint - 确保核心服务完成
  - 验证配置管理、SQL 构建、同步策略
  - 确保所有测试通过，如有问题请询问用户

- [x] 10. API 路由实现
  - [x] 10.1 创建仪表盘 API
    - 创建 `src/api/admin.py`
    - 实现 `GET /api/v1/admin/dashboard` 仪表盘数据
    - _需求 1.1, 1.2: 仪表盘_
  
  - [x] 10.2 实现 LLM 配置 API
    - 实现 LLM 配置 CRUD API
    - 实现连接测试 API
    - _需求 2.1, 2.4, 2.5: LLM 配置_
  
  - [x] 10.3 实现数据库配置 API
    - 实现数据库连接 CRUD API
    - 实现连接测试 API
    - _需求 3.1, 3.3, 3.5: 数据库配置_
  
  - [x] 10.4 实现同步策略 API
    - 实现同步策略 CRUD API
    - 实现同步触发和重试 API
    - _需求 4.1, 4.4: 同步策略_
  
  - [x] 10.5 实现 SQL 构建器 API
    - 实现 Schema 获取 API
    - 实现 SQL 构建和执行 API
    - 实现模板 CRUD API
    - _需求 5.1, 5.4, 5.7: SQL 构建器_
  
  - [x] 10.6 实现配置历史 API
    - 实现历史查询 API
    - 实现回滚 API
    - _需求 6.1, 6.4, 6.5: 配置历史_
  
  - [x] 10.7 实现第三方工具配置 API
    - 实现第三方工具 CRUD API
    - 实现健康检查 API
    - _需求 7.1, 7.3, 7.4: 第三方工具_
  
  - [x] 10.8 注册路由到主应用
    - 在 `src/app.py` 和 `src/app_auth.py` 中注册路由
    - 添加管理员权限控制
    - _权限控制_

- [x] 11. 前端实现 - 仪表盘和 LLM 配置
  - [x] 11.1 创建管理员仪表盘
    - 创建 `frontend/src/pages/admin/Dashboard.tsx`
    - 实现系统健康状态概览
    - 实现关键指标展示
    - 实现快捷操作入口
    - _需求 1.1, 1.2, 1.3: 仪表盘_
  
  - [x] 11.2 创建 LLM 配置页面
    - 创建 `frontend/src/pages/admin/LLMConfig.tsx`
    - 实现 LLM 类型选择和配置表单
    - 实现连接测试功能
    - 实现 API Key 脱敏显示
    - _需求 2.1, 2.2, 2.5, 2.6: LLM 配置_

- [x] 12. 前端实现 - 数据库和同步配置
  - [x] 12.1 创建数据库配置页面
    - 创建 `frontend/src/pages/admin/DBConfig.tsx`
    - 实现数据库连接列表
    - 实现添加/编辑连接表单
    - 实现连接测试功能
    - _需求 3.1, 3.2, 3.3, 3.5: 数据库配置_
  
  - [x] 12.2 创建同步策略配置页面
    - 创建 `frontend/src/pages/admin/SyncConfig.tsx`
    - 实现同步模式选择
    - 实现同步频率配置
    - 实现同步历史展示
    - _需求 4.1, 4.2, 4.4, 4.6: 同步策略_

- [x] 13. 前端实现 - SQL 构建器和历史
  - [x] 13.1 创建 SQL 构建器页面
    - 创建 `frontend/src/pages/admin/SQLBuilder.tsx`
    - 实现表和字段选择（拖拽）
    - 实现条件配置
    - 实现 SQL 预览和执行
    - _需求 5.1, 5.2, 5.3, 5.4, 5.6: SQL 构建器_
  
  - [x] 13.2 创建配置历史页面
    - 创建 `frontend/src/pages/admin/ConfigHistory.tsx`
    - 实现历史列表和筛选
    - 实现差异对比展示
    - 实现回滚功能
    - _需求 6.1, 6.2, 6.3, 6.4, 6.5: 配置历史_
  
  - [x] 13.3 创建第三方工具配置页面
    - 创建 `frontend/src/pages/admin/ThirdPartyConfig.tsx`
    - 实现工具列表和状态展示
    - 实现添加/编辑工具表单
    - 实现启用/禁用开关
    - _需求 7.1, 7.2, 7.3, 7.5, 7.6: 第三方工具_

- [x] 14. 前端路由和菜单
  - [x] 14.1 添加路由配置
    - 在 `frontend/src/routes` 中添加管理员路由
    - 配置路由权限
    - _路由配置_
  
  - [x] 14.2 添加管理员菜单
    - 在侧边栏添加管理员菜单项
    - 配置菜单权限
    - _菜单配置_
  
  - [x] 14.3 编写前端单元测试
    - 测试配置表单验证
    - 测试 SQL 构建器逻辑
    - _前端测试_

- [x] 15. Checkpoint - 确保前端功能完成
  - 验证所有配置页面渲染
  - 验证配置保存和加载
  - 确保所有测试通过，如有问题请询问用户

- [x] 16. 集成测试和文档
  - [x] 16.1 编写端到端集成测试
    - 测试完整的配置流程
    - 测试配置历史和回滚
    - 测试 SQL 构建器
    - _集成测试_
  
  - [x] 16.2 编写第三方工具启用/禁用测试
    - **Property 6: 第三方工具启用/禁用即时生效**
    - **Validates: Requirements 7.5**
  
  - [x] 16.3 更新 API 文档
    - 更新 OpenAPI 文档
    - 添加管理员 API 使用示例
    - _文档更新_

- [x] 17. Final Checkpoint - 确保所有功能完成
  - 运行完整测试套件
  - 验证所有需求已实现
  - 确保所有测试通过，如有问题请询问用户

## Notes

- 所有任务（包括测试任务）均为必须完成
- 每个任务引用具体需求以确保可追溯性
- Checkpoint 任务用于阶段性验证
- 属性测试使用 Hypothesis 库，每个属性至少运行 100 次
- 管理员功能需要严格的权限控制
- 敏感信息必须加密存储和脱敏显示
