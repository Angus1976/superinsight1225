# 实施计划：AI 工作流引擎

## 概述

将 AI 智能助手从"自由对话 + 散落配置"模式升级为"工作流驱动 + 角色权限控制"模式。采用增量实施策略：先建数据模型和核心服务，再扩展 API 端点，然后改造前端，最后做数据迁移和文档更新。项目已 70%，只扩展/修复/优化，不重写。

## 任务

- [x] 1. 后端数据模型与数据库迁移
  - [x] 1.1 创建 AIWorkflow 数据模型
    - 新建 `src/models/ai_workflow.py`，定义 `AIWorkflow` SQLAlchemy 模型
    - 包含字段：id、name、description、status、is_preset、skill_ids(JSONB)、data_source_auth(JSONB)、output_modes(JSONB)、visible_roles(JSONB)、preset_prompt、name_en、description_en、created_at、updated_at、created_by
    - 使用 `Optional[List[str]]` 语法（Python 3.9.6 兼容）
    - 在 `src/models/__init__.py` 中注册新模型
    - _需求: 1.1_

  - [x] 1.2 创建数据库迁移脚本
    - 由于 Alembic 存在多头问题（009, 011, 033, 036），使用直接 SQL 创建 `ai_workflows` 表并 stamp
    - 创建索引：`idx_workflow_status`（status）、`idx_workflow_name`（name）
    - 包含 JSONB 字段的 server_default='[]'
    - _需求: 1.1_

  - [x] 1.3 创建 Pydantic Schema 定义
    - 在 `src/api/ai_assistant.py` 或独立文件中定义：WorkflowCreateRequest、WorkflowUpdateRequest、WorkflowResponse、EffectivePermissions、WorkflowErrorResponse
    - 定义预留结构：AuthorizationRequest、MissingPermissions、AuthorizationCallback
    - 使用 `Optional[List[str]]` 语法
    - _需求: 1.1, 1.2, 1.3, 14.1, 14.5_

- [x] 2. WorkflowService 核心服务
  - [x] 2.1 实现 WorkflowService CRUD 方法
    - 新建 `src/ai/workflow_service.py`
    - 实现 `create_workflow()`：校验名称唯一、skill_ids 存在、data_source_id 存在且启用、角色值合法，持久化并返回完整对象
    - 实现 `update_workflow()`：复用创建相同的校验规则，部分更新
    - 实现 `delete_workflow()`：软删除（status='disabled'），预置工作流禁止删除
    - 实现 `get_workflow()` 和 `list_workflows()`：支持按 status、role 过滤，非管理员自动按角色过滤
    - 复用现有 `AIDataSourceService`、`RolePermissionService`、`SkillPermissionService`
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 7.5_

  - [x] 2.2 编写 Property 1 属性测试：工作流创建后包含所有必需字段
    - **Property 1: 工作流创建后包含所有必需字段**
    - 使用 hypothesis 生成随机有效输入，验证创建后返回对象包含所有必需字段且 status='enabled'
    - **验证: 需求 1.1**

  - [x] 2.3 编写 Property 2 属性测试：创建和更新共享相同的校验规则
    - **Property 2: 创建和更新共享相同的校验规则**
    - 生成随机字段值，验证 create 和 update 的校验结果一致
    - **验证: 需求 1.2, 1.3**

  - [x] 2.4 编写 Property 3 属性测试：软删除保留记录
    - **Property 3: 软删除保留记录**
    - 验证删除后 status='disabled' 且记录仍可查询
    - **验证: 需求 1.4**

  - [x] 2.5 编写 Property 4 属性测试：工作流列表过滤正确性
    - **Property 4: 工作流列表过滤正确性**
    - 生成随机工作流集合和过滤条件，验证返回结果满足所有过滤条件且无遗漏
    - **验证: 需求 1.5**

  - [x] 2.6 实现权限链路校验 check_permission_chain()
    - 实现三层权限校验：角色可见性 → 技能权限 → 数据源权限
    - 权限计算：角色基础权限 ∩ max(工作流配置, API 传参)
    - 任一环节失败返回 403 + 具体权限不足信息
    - 权限不足时在 details 中附加 authorization_request 结构
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 14.1, 14.5_

  - [x] 2.7 编写 Property 5 属性测试：角色可见性控制
    - **Property 5: 角色可见性控制**
    - 生成随机工作流和角色组合，验证管理员始终可见、禁用不可见、角色匹配规则
    - **验证: 需求 2.1, 2.2, 2.4, 7.3**

  - [x] 2.8 编写 Property 6 属性测试：权限链路校验完整性
    - **Property 6: 权限链路校验完整性**
    - 生成随机权限配置，验证链路校验结果为各层交集
    - **验证: 需求 2.3, 2.5, 6.2, 11.5**

  - [x] 2.9 编写 Property 7 属性测试：API 传参权限优先级
    - **Property 7: API 传参权限优先级**
    - 生成随机工作流配置和 API 覆盖参数，验证 API 传参覆盖工作流配置
    - **验证: 需求 2.6, 3.6, 12.4, 12.5**

  - [x] 2.10 编写 Property 26 属性测试：权限不足时包含授权请求结构
    - **Property 26: 权限不足时包含授权请求结构**
    - 验证 403 响应中包含 authorization_request 字段及所有必需子字段
    - **验证: 需求 14.1, 14.5**

- [x] 3. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 4. 数据源授权与权限同步
  - [x] 4.1 实现数据源总分结构授权逻辑
    - 在 WorkflowService 中实现 data_source_auth 的校验和查询过滤
    - 支持 `tables: ["*"]`（全部数据表）和 `tables: ["table_a", "table_b"]`（指定数据表）
    - 校验 source_id 在 AIDataSourceConfigModel 中存在且 enabled=True
    - 不存在的数据表跳过并记录警告
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 4.2 编写 Property 8 属性测试：数据源总分结构序列化往返
    - **Property 8: 数据源总分结构序列化往返**
    - 生成随机 data_source_auth 结构，验证 JSONB 存储后读取一致
    - **验证: 需求 3.1**

  - [x] 4.3 编写 Property 9 属性测试：数据表级别访问控制
    - **Property 9: 数据表级别访问控制**
    - 生成随机授权配置和查询请求，验证实际查询的数据表为授权子集
    - **验证: 需求 3.3**

  - [x] 4.4 编写 Property 10 属性测试：数据源授权不超过启用范围
    - **Property 10: 数据源授权不超过启用范围**
    - 验证引用不存在或已禁用的数据源被校验拒绝
    - **验证: 需求 3.5, 6.1**

  - [x] 4.5 编写 Property 16 属性测试：宽松与严格配置均正确处理
    - **Property 16: 宽松与严格配置均正确处理**
    - 生成 `["*"]` 和具体列表的混合配置，验证访问范围正确
    - **验证: 需求 5.3**

  - [x] 4.6 实现权限同步 sync_permissions()
    - 实现 `POST /workflows/sync-permissions` 的核心逻辑
    - 接受完整权限列表，批量更新相关工作流的 data_source_auth
    - 未提及的工作流不被修改
    - _需求: 3.6, 3.7, 11.7_

  - [x] 4.7 编写 Property 11 属性测试：权限同步批量更新正确性
    - **Property 11: 权限同步批量更新正确性**
    - 验证同步后受影响工作流反映新配置，未提及工作流不变
    - **验证: 需求 3.7**

- [x] 5. 工作流执行引擎
  - [x] 5.1 实现 execute_workflow() 和 stream_execute_workflow()
    - 加载工作流配置 → 权限链路校验 → 提取 skill_ids/data_source_auth/output_modes
    - 有技能时调用 OpenClawChatService.chat()，按 skill_ids 列表顺序执行
    - 无技能时调用 LLMSwitcher 直连
    - 技能失败不阻断后续执行，标注失败技能和错误信息
    - 记录 workflow_execute 日志到 AIAccessLog
    - _需求: 4.3, 4.5, 4.6, 5.1, 5.2_

  - [x] 5.2 编写 Property 12 属性测试：工作流配置参数提取
    - **Property 12: 工作流配置参数提取**
    - 验证带 workflow_id 的请求从工作流配置中提取参数替代手动配置
    - **验证: 需求 4.3**

  - [x] 5.3 编写 Property 13 属性测试：技能按序执行
    - **Property 13: 技能按序执行**
    - 验证多技能工作流的调用顺序与 skill_ids 列表顺序一致
    - **验证: 需求 4.5**

  - [x] 5.4 编写 Property 14 属性测试：技能失败不阻断后续执行
    - **Property 14: 技能失败不阻断后续执行**
    - 验证某技能失败后剩余技能继续执行，响应中标注失败信息
    - **验证: 需求 4.6**

  - [x] 5.5 编写 Property 15 属性测试：无技能工作流走 LLM 直连
    - **Property 15: 无技能工作流走 LLM 直连**
    - 验证 skill_ids 为空时走 LLMSwitcher，且 data_source_auth 和 output_modes 仍被应用
    - **验证: 需求 5.1, 5.2**

  - [x] 5.6 实现统计方法 get_workflow_stats() 和 get_today_stats()
    - 基于 AIAccessLog 聚合统计：chat_count、workflow_count、data_source_count
    - 支持按角色和日期范围查询
    - 非管理员仅返回自身数据，管理员可查看汇总
    - _需求: 8.1, 8.3, 8.4_

  - [x] 5.7 编写 Property 18 属性测试：今日统计聚合正确性
    - **Property 18: 今日统计聚合正确性**
    - 验证统计数值与日志记录数量一致
    - **验证: 需求 8.1, 8.3**

  - [x] 5.8 编写 Property 19 属性测试：统计数据按角色隔离
    - **Property 19: 统计数据按角色隔离**
    - 验证非管理员仅看到自身数据，管理员可看汇总
    - **验证: 需求 8.4**

- [x] 6. 检查点 — 确保所有测试通过
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 7. 后端 API 端点
  - [x] 7.1 扩展 ai_assistant.py 添加工作流 CRUD 端点
    - 在 `src/api/ai_assistant.py` 中新增：
      - `GET /workflows` — 查询列表，非管理员自动按角色过滤
      - `POST /workflows` — 创建（仅管理员）
      - `PUT /workflows/{id}` — 更新（仅管理员）
      - `DELETE /workflows/{id}` — 禁用（仅管理员）
    - 非管理员访问管理端点返回 403
    - 所有操作记录 AIAccessLog
    - _需求: 11.1, 11.5, 11.6_

  - [x] 7.2 扩展现有 chat 端点支持 workflow_id
    - 在 `ChatRequest` 中新增可选字段 `workflow_id: Optional[str] = None`
    - `POST /chat` 和 `POST /chat/stream`：当 workflow_id 存在时调用 WorkflowService.execute_workflow()，不存在时走原有逻辑
    - _需求: 11.2, 13.1, 13.2_

  - [x] 7.3 编写 Property 24 属性测试：向后兼容——无 workflow_id 请求走原有逻辑
    - **Property 24: 向后兼容——无 workflow_id 请求走原有逻辑**
    - 验证不携带 workflow_id 的请求行为与引入工作流前一致
    - **验证: 需求 13.1, 13.2**

  - [x] 7.4 添加统计和权限同步端点
    - `GET /workflows/{id}/stats` — 指定工作流执行统计
    - `GET /stats/today` — 当前用户当日统计
    - `POST /workflows/sync-permissions` — 批量权限同步
    - _需求: 11.3, 11.4, 11.7_

  - [x] 7.5 添加动态授权请求预留端点（返回 501）
    - `POST /workflows/request-authorization` — 返回 501 Not Implemented
    - _需求: 14.2_

  - [x] 7.6 编写 Property 22 属性测试：工作流操作审计日志
    - **Property 22: 工作流操作审计日志**
    - 验证所有工作流 API 请求均创建 AIAccessLog 记录
    - **验证: 需求 11.6, 12.7**

- [x] 8. Service Engine 外部通道扩展
  - [x] 8.1 扩展 ServiceRequest schema 和处理逻辑
    - 在 `src/service_engine/schemas.py` 的 ServiceRequest 中新增 `workflow_id: Optional[str] = None`
    - 在 `src/service_engine/api.py` 中扩展 ChatHandler/QueryHandler：当 workflow_id 存在时委托给 WorkflowService
    - API Key 的 scope 和 skill_whitelist 与工作流配置取交集
    - _需求: 12.2, 12.3, 12.4, 12.5_

  - [x] 8.2 添加外部通道工作流查询端点
    - `GET /api/v1/service/workflows` — API Key 认证，返回有权访问的工作流列表
    - _需求: 12.8_

  - [x] 8.3 添加授权回调预留端点（返回 501）
    - `POST /api/v1/service/authorization-callback` — 返回 501 Not Implemented
    - _需求: 14.3_

  - [x] 8.4 编写 Property 23 属性测试：双通道执行结果一致性
    - **Property 23: 双通道执行结果一致性**
    - 验证相同输入通过两个通道执行的核心结果数据一致
    - **验证: 需求 12.6**

- [x] 9. 检查点 — 确保所有后端测试通过
  - 确保所有测试通过，如有问题请向用户确认。
  - 运行命令：`python3 -m pytest tests/test_workflow_*.py -v`

- [x] 10. 前端类型定义与 API 服务
  - [x] 10.1 添加工作流 TypeScript 类型定义
    - 在 `frontend/src/types/aiAssistant.ts` 中新增：WorkflowItem、DataSourceAuth、TodayStats、StatsDetail 接口
    - _需求: 1.1_

  - [x] 10.2 添加工作流 API 调用方法
    - 在 `frontend/src/services/aiAssistantApi.ts` 中新增：
      - `getWorkflows()` — 获取工作流列表
      - `createWorkflow()` / `updateWorkflow()` / `deleteWorkflow()` — CRUD
      - `getTodayStats()` — 获取当日统计
      - `getWorkflowStats()` — 获取指定工作流统计
      - `syncPermissions()` — 权限同步
    - 扩展现有 chat 请求方法，支持 workflow_id 参数
    - _需求: 11.1, 11.2, 11.3, 11.4_

- [x] 11. 前端 i18n 翻译文件
  - [x] 11.1 创建工作流命名空间翻译文件
    - 新建 `frontend/src/locales/zh/workflow.json` 和 `frontend/src/locales/en/workflow.json`
    - 包含所有工作流相关翻译键：工作流选择器、管理页面、统计面板、错误信息、预置工作流名称/描述
    - 确保中英文翻译键完全一致
    - 在 `frontend/src/locales/config.ts` 中注册新命名空间
    - _需求: 10.1, 10.2, 10.5_

  - [x] 11.2 编写 Property 20 属性测试：翻译键中英文一致性
    - **Property 20: 翻译键中英文一致性**
    - 验证 zh/ 和 en/ 翻译文件中的键完全一致
    - **验证: 需求 10.2**

  - [x] 11.3 编写 Property 21 属性测试：错误响应使用错误码
    - **Property 21: 错误响应使用错误码**
    - 验证所有工作流 API 错误响应包含 error_code 字段
    - **验证: 需求 10.4**

- [x] 12. 前端组件实现
  - [x] 12.1 实现 WorkflowSelector 组件
    - 新建 `frontend/src/pages/AIAssistant/components/WorkflowSelector.tsx`
    - 卡片式展示有权限的工作流列表，支持搜索过滤
    - 选中高亮 + 持久化到 localStorage（key: `ai_last_workflow_id`）
    - 页面加载时恢复上次选择，已禁用/无权限则清除
    - 未选择时显示引导提示
    - 所有可见文本使用 `t()` 函数
    - _需求: 4.1, 4.2, 4.3, 5.4_

  - [x] 12.2 编写 Property 25 属性测试：工作流选择持久化与恢复
    - **Property 25: 工作流选择持久化与恢复**
    - 验证 localStorage 持久化和恢复逻辑正确
    - **验证: 需求 4.2, 4.3**

  - [x] 12.3 改造 AIAssistant/index.tsx 集成 WorkflowSelector
    - 移除旧组件引用：模式切换 Segmented、技能勾选面板
    - 集成 WorkflowSelector，选中后将 workflow_id 附加到聊天请求
    - 显示当前工作流名称和执行状态
    - 预置工作流以快捷操作卡片形式展示，无权限时隐藏
    - 所有可见文本使用 `t()` 函数
    - _需求: 4.1, 4.4, 7.1, 7.2, 7.3_

  - [x] 12.4 增强 StatsPanel 组件
    - 修改 `frontend/src/pages/AIAssistant/components/StatsPanel.tsx`
    - 接入后端 `GET /stats/today` API，替代前端硬编码统计
    - 支持点击展开明细列表
    - 按角色显示不同统计维度
    - 所有可见文本使用 `t()` 函数
    - _需求: 8.1, 8.2, 8.4_

  - [x] 12.5 移除旧组件文件
    - 删除 `frontend/src/pages/AIAssistant/components/ConfigPanel.tsx`
    - 删除 `frontend/src/pages/AIAssistant/components/DataSourceConfigModal.tsx`
    - 删除 `frontend/src/pages/AIAssistant/components/PermissionTableModal.tsx`
    - 删除 `frontend/src/pages/AIAssistant/components/OutputModeModal.tsx`
    - 确保 index.tsx 中无残留引用
    - _需求: 6.5_

- [x] 13. 工作流管理页面
  - [x] 13.1 实现 WorkflowAdmin 管理页面
    - 新建 `frontend/src/pages/Admin/WorkflowAdmin.tsx`
    - 工作流列表：名称、状态、技能数量、可见角色、创建时间，支持筛选和搜索
    - 创建/编辑表单：名称、描述（中英文）、技能多选、数据源总分结构树形选择、输出方式选择、角色多选
    - 前端校验：名称必填、至少一个可见角色
    - 预置工作流禁止删除
    - 所有可见文本使用 `t()` 函数
    - _需求: 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.3_

- [x] 14. 检查点 — 确保前端构建通过
  - 确保前端构建无错误，如有问题请向用户确认。
  - 构建命令：`docker compose build frontend && docker compose up -d frontend`

- [x] 15. 数据迁移与预置工作流
  - [x] 15.1 实现默认工作流生成逻辑 generate_default_workflows()
    - 在 WorkflowService 中实现，基于现有 AISkillRolePermission 和 AIDataSourceRolePermission 为每个角色生成默认工作流
    - 保持与迁移前相同的访问能力
    - _需求: 6.3_

  - [x] 15.2 编写 Property 17 属性测试：默认工作流迁移保持访问能力
    - **Property 17: 默认工作流迁移保持访问能力**
    - 验证迁移后各角色的有效权限与迁移前一致
    - **验证: 需求 6.3**

  - [x] 15.3 创建 4 个系统预置工作流
    - 销售预测分析、数据质量检查、智能标注建议、任务进度追踪
    - 标记 is_preset=True，配置对应技能和数据源
    - 预置工作流名称/描述在翻译文件中预定义
    - _需求: 7.1, 7.2, 10.5_

- [x] 16. 客户 API 文档更新
  - [x] 16.1 更新智能服务引擎 API 接口文档
    - 更新 `文档/系统设计/智能服务引擎API接口文档.md`
    - 补充工作流相关传参说明、请求示例、响应格式、错误码
    - 补充动态授权请求协议说明：授权请求格式、回调格式、时序图、错误码
    - _需求: 12.9, 14.4_

- [x] 17. 最终检查点 — 全面验证
  - 确保所有后端测试通过：`python3 -m pytest tests/test_workflow_*.py -v`
  - 确保前端构建通过
  - 确保后端服务重建：`docker compose build backend && docker compose up -d backend`
  - 如有问题请向用户确认。

## 备注

- 标记 `*` 的任务为可选任务，可跳过以加速 MVP 交付
- 每个任务引用了具体的需求编号，确保可追溯性
- 检查点确保增量验证，及早发现问题
- 属性测试使用 hypothesis 库验证通用正确性属性
- 单元测试验证具体示例和边界情况
- Python 3.9.6 兼容：使用 `Optional[List[str]]` 而非 `list[str] | None`
- Alembic 多头问题：数据库迁移使用直接 SQL + stamp 方式
- 前端所有可见文本必须使用 `t()` 国际化函数
- 翻译文件同步写入 `frontend/src/locales/zh/` 和 `en/`
