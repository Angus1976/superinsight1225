# 实现计划：智能服务引擎（Smart Service Engine）

## 概述

按模块分层实现：数据模型 → 核心引擎（BaseHandler + RequestRouter）→ 各 Handler → 前端扩展 → 集成联调。新增代码集中在 `src/service_engine/`，最大化复用现有模块。

## 任务

- [x] 1. 数据模型与 Schema
  - [x] 1.1 创建 `src/service_engine/schemas.py`，定义 ServiceRequest、ServiceResponse、ErrorResponse、ResponseMetadata 等 Pydantic 模型
    - 包含 request_type 枚举校验、business_context 100KB 大小校验、user_id 必传校验
    - _需求: 1.2, 6.1, 6.2, 6.5, 10.1, 10.2, 10.3, 10.4, 12.6_
  - [x] 1.2 创建 Alembic 迁移：新增 user_memories 表、webhook_configs 表，扩展 APIKeyModel（allowed_request_types、skill_whitelist、webhook_config 字段）
    - _需求: 7.1, 8.1, 8.4, 11.4, 11.5_
  - [x] 1.3 为 Schema 编写属性测试
    - **属性 2: 无效枚举值拒绝** — 任意无效 request_type 应触发校验错误
    - **属性 10: user_id 必传校验** — 缺少 user_id 应触发校验错误
    - **属性 11: business_context 大小限制** — 超过 100KB 应触发校验错误
    - **验证需求: 1.7, 6.1, 6.4, 6.5**

- [x] 2. 核心引擎：BaseHandler + RequestRouter
  - [x] 2.1 创建 `src/service_engine/base.py`，定义 BaseHandler 抽象基类（validate / build_context / execute）
    - _需求: 12.1, 12.2, 12.3_
  - [x] 2.2 创建 `src/service_engine/router.py`，实现 RequestRouter（Handler 注册表、动态启用/禁用、scope 权限校验）
    - _需求: 1.3, 1.4, 1.5, 1.6, 1.7, 11.2, 11.3, 12.1, 12.4_
  - [x] 2.3 为 RequestRouter 编写属性测试
    - **属性 1: 路由正确性** — 有效 request_type 分发到对应 Handler
    - **属性 3: Scope 权限强制执行** — 无权限时返回 403
    - **属性 18: 动态启用/禁用** — 被禁用的类型即使有权限也应拒绝
    - **验证需求: 1.3–1.6, 2.3, 11.2, 11.3, 12.4**

- [x] 3. DataProvider 注册表与 QueryHandler
  - [x] 3.1 创建 `src/service_engine/providers.py`，定义 BaseDataProvider 接口和 8 种 data_type 的 Provider 实现，复用 external_data_router.py 中的查询逻辑
    - _需求: 2.1, 2.2, 12.5_
  - [x] 3.2 创建 `src/service_engine/handlers/query.py`，实现 QueryHandler（data_type 校验、scope 校验、分页/排序/字段筛选/过滤/租户隔离）
    - _需求: 2.1–2.10_
  - [x] 3.3 为 QueryHandler 编写属性测试
    - **属性 4: 租户隔离** — 返回结果 tenant_id 与请求一致
    - **属性 5: 分页默认值** — 未指定时 page=1, page_size=50
    - **属性 6: 字段筛选正确性** — 返回字段仅包含指定字段
    - **验证需求: 2.4, 2.6, 2.8**

- [x] 4. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 5. ContextBuilder 与 UserMemory
  - [x] 5.1 创建 `src/service_engine/context.py`，实现 ContextBuilder（组装治理数据 + business_context + UserMemory）
    - _需求: 3.3, 4.3, 6.3_
  - [x] 5.2 创建 `src/service_engine/memory.py`，实现 UserMemory（CRUD、50 条阈值压缩、include_memory 开关）
    - _需求: 7.1–7.6_
  - [x] 5.3 为 UserMemory 编写属性测试
    - **属性 12: 记忆持久化往返** — 交互后 user_memories 表新增记录
    - **属性 13: 记忆压缩阈值** — 超过 50 条触发压缩
    - **属性 14: include_memory 开关** — false 时不加载也不追加记忆
    - **验证需求: 7.1, 7.3, 7.4, 7.5, 7.6**

- [x] 6. ChatHandler 与 DecisionHandler
  - [x] 6.1 创建 `src/service_engine/handlers/chat.py`，实现 ChatHandler（SSE 流式返回、LLMSwitcher 集成、超时控制、错误处理）
    - _需求: 3.1–3.9_
  - [x] 6.2 创建 `src/service_engine/handlers/decision.py`，实现 DecisionHandler（结构化 JSON 报告、LLM 降级处理）
    - _需求: 4.1–4.7_
  - [x] 6.3 为 ChatHandler 和 DecisionHandler 编写属性测试
    - **属性 7: SSE 流格式一致性** — 中间 chunk done=false，最后 done=true
    - **属性 8: 决策响应结构完整性** — 包含 summary/analysis/recommendations/confidence
    - **验证需求: 3.5, 3.6, 4.4, 4.5**

- [x] 7. SkillHandler 与 Webhook CRUD
  - [x] 7.1 创建 `src/service_engine/handlers/skill.py`，实现 SkillHandler（白名单校验、SkillManager 集成）
    - _需求: 5.1–5.7_
  - [x] 7.2 创建 `src/service_engine/webhook.py`，实现 Webhook 配置 CRUD 接口（仅数据存储）
    - _需求: 8.1–8.4_
  - [x] 7.3 为 SkillHandler 和 Webhook 编写属性测试
    - **属性 9: 技能白名单强制执行** — skill_id 不在白名单返回 403
    - **属性 15: Webhook 配置 CRUD 往返** — 创建后读取数据一致
    - **验证需求: 5.2, 5.3, 8.2**

- [x] 8. 统一入口路由与错误处理
  - [x] 8.1 创建 `src/service_engine/api.py`，注册 `POST /api/v1/service/request` 路由，集成 APIKeyAuthMiddleware、RateLimiter，全局异常处理器
    - 包含审计日志、统一错误响应格式
    - _需求: 1.1, 1.8, 1.9, 1.10, 10.5, 11.6_
  - [x] 8.2 为统一响应格式编写属性测试
    - **属性 16: 统一成功响应结构** — 包含 success/request_type/data/metadata
    - **属性 17: 统一错误响应结构** — 包含 success=false/error/error_code/details
    - **验证需求: 10.2, 10.3, 10.4**

- [x] 9. 检查点 — 确保所有后端测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 10. 前端管理界面扩展
  - [x] 10.1 在 API 管理页面扩展 request_type 多选配置组件、Skill 白名单选择组件、Webhook 配置表单（标记"即将推出"）
    - 所有用户可见文本使用 i18n（`useTranslation`），同步更新 zh/en 翻译 JSON
    - _需求: 9.1–9.8_
  - [x] 10.2 为前端组件编写单元测试
    - 测试配置变更同步、白名单展示、i18n 切换
    - _需求: 9.6, 9.7, 9.8_

- [x] 11. 最终检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

## 备注

- 标记 `*` 的子任务为可选，可跳过以加速 MVP
- 属性测试使用 Hypothesis，配置 `@settings(max_examples=100)`
- 每个属性测试标注格式：`# Feature: smart-service-engine, Property N: 属性描述`
