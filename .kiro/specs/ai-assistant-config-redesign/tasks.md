# 实施计划：AI 智能助手配置方式重构

## 概述

按后端→前端→集成的顺序实施。先建数据模型和服务，再构建前端组件，最后串联集成。

## 任务

- [x] 1. 后端：数据模型与角色权限服务
  - [x] 1.1 新增 `ai_data_source_role_permission` 数据库模型和迁移脚本
    - 在 `src/models/` 中创建 SQLAlchemy 模型，含 id/role/source_id/allowed/updated_at 字段
    - 添加 `(role, source_id)` 唯一约束
    - 生成 Alembic 迁移脚本
    - _需求: 6.5_

  - [x] 1.2 实现 `RolePermissionService`（`src/ai/role_permission_service.py`）
    - 实现 `get_all_permissions()`、`get_permissions_by_role(role)`、`update_permissions(permissions)` 方法
    - `update_permissions` 使用 upsert 逻辑（按 role+source_id 更新或插入）
    - _需求: 6.1, 6.2_

  - [x] 1.3 属性测试：角色权限映射持久化往返（Property 3）
    - **属性 3：角色权限映射持久化往返**
    - 用 hypothesis 生成随机角色权限组合，验证 save→get 往返一致性
    - **验证: 需求 4.4**

  - [x] 1.4 新增角色权限 API 端点（`src/api/ai_assistant.py`）
    - `GET /api/v1/ai-assistant/data-sources/role-permissions`：返回所有权限映射
    - `POST /api/v1/ai-assistant/data-sources/role-permissions`：批量更新权限（admin only）
    - 非 admin 用户调用返回 403
    - _需求: 6.1, 6.2, 6.4_

  - [x] 1.5 属性测试：非管理员访问权限接口返回 403（Property 5）
    - **属性 5：非管理员访问权限接口返回 403**
    - 用 hypothesis 生成非 admin 角色，验证调用权限接口返回 403
    - **验证: 需求 6.4**

  - [x] 1.6 修改 `GET /data-sources/available` 端点，增加角色权限过滤
    - 在 `AIDataSourceService.get_available_sources()` 中查询权限表，返回「已启用 ∩ 角色授权」的数据源
    - _需求: 6.3_

  - [x] 1.7 属性测试：可用数据源等于已启用与角色授权的交集（Property 4）
    - **属性 4：可用数据源 = 已启用 ∩ 角色授权**
    - 用 hypothesis 生成随机配置和权限组合，验证返回结果为交集
    - **验证: 需求 5.2, 6.3**

- [x] 2. 检查点 - 后端验证
  - 确保所有后端测试通过，如有问题请向用户确认。

- [x] 3. 前端：i18n 翻译文件
  - [x] 3.1 更新 `frontend/src/locales/zh/aiAssistant.json` 和 `en/aiAssistant.json`
    - 添加 ConfigPanel、三个 Modal、角色名称、错误提示等所有新增文本的中英文翻译 key
    - _需求: 7.1, 7.2, 7.3, 7.4_

- [x] 4. 前端：ConfigPanel 与 Modal 组件
  - [x] 4.1 实现 ConfigPanel 组件（`frontend/src/pages/AIAssistant/components/ConfigPanel.tsx`）
    - 根据 userRole 渲染按钮：admin 显示 3 个，非 admin 显示 1 个
    - 所有文本使用 `t()` 包裹
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 4.2 属性测试：角色决定配置按钮可见性（Property 1）
    - **属性 1：角色决定配置按钮可见性**
    - 用 fast-check 生成随机角色，渲染 ConfigPanel，断言 admin=3 按钮，非 admin=1 按钮
    - **验证: 需求 2.3, 2.4**

  - [x] 4.3 实现 DataSourceConfigModal（`components/DataSourceConfigModal.tsx`）
    - 展示所有已注册数据源列表，每项含启用/禁用 Switch 和访问模式 Select
    - 调用 `GET/POST /data-sources/config` 接口
    - 保存失败显示 `message.error`
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 4.4 实现 PermissionTableModal（`components/PermissionTableModal.tsx`）
    - 表格形式：行=角色，列=已启用数据源，单元格=Checkbox
    - 调用 `GET/POST /data-sources/role-permissions` 接口
    - 保存失败显示 `message.error`
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 4.5 实现 OutputModeModal（`components/OutputModeModal.tsx`）
    - 数据源多选列表（调用 `GET /data-sources/available`，仅显示有权数据源）
    - 输出方式选择：merge / compare
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.7_

  - [-] 4.6 单元测试：三个 Modal 组件
    - 测试打开/关闭、表单提交、错误提示渲染
    - _需求: 3.5, 4.5_

- [x] 5. 前端：页面集成
  - [x] 5.1 修改 `frontend/src/pages/AIAssistant/index.tsx`
    - 移除聊天区域的数据源 Popover 和输出模式 Segmented 控件
    - 在 Right_Sidebar 底部引入 ConfigPanel 组件
    - 将 OutputModeModal 的选择结果（数据源 IDs + 输出模式）传递给对话逻辑
    - _需求: 1.1, 1.2, 2.1, 5.5, 5.6_

- [x] 6. 最终检查点 - 全量验证
  - 确保所有前后端测试通过，如有问题请向用户确认。

## 备注

- 标记 `*` 的子任务为可选，可跳过以加速 MVP
- 每个任务引用了对应的需求编号，确保可追溯
- 属性测试验证系统核心正确性属性
