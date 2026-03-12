# 实施计划：双向同步与外部 API 访问

## 概述

基于现有同步引擎扩展输出同步和外部 API 网关能力，按数据模型→后端服务→API 端点→前端界面的顺序递进实现。

## 任务

- [x] 1. 数据库模型与迁移
  - [x] 1.1 扩展 SyncJobModel 和 SyncExecutionModel
    - 新增 direction、target_source_id、field_mapping_rules、output_sync_strategy、output_checkpoint 字段
    - SyncExecutionModel 新增 sync_direction、rows_written、write_errors 字段
    - 创建 Alembic 迁移脚本
    - _需求: 1.1, 1.2, 2.5_
  - [x] 1.2 创建 APIKeyModel 和 APICallLogModel
    - api_keys 表：含 key_prefix、key_hash、scopes、rate_limit、status、expires_at 等
    - api_call_logs 表：含 key_id、endpoint、status_code、response_time_ms
    - 创建 Alembic 迁移脚本
    - _需求: 4.1, 4.5, 6.3_
  - [x] 1.3 属性测试：输出/双向任务配置不变量
    - **Property 2: 输出/双向任务配置不变量**
    - **验证: 需求 1.2, 1.4**

- [x] 2. 输出同步后端服务
  - [x] 2.1 实现 FieldMapper
    - `apply_mapping(data, rules)` 字段名映射 + 类型转换
    - `validate_mapping(source_schema, target_schema, rules)` 映射规则校验
    - _需求: 1.3, 1.4_
  - [x] 2.2 属性测试：字段映射往返一致性
    - **Property 1: 字段映射往返一致性**
    - **验证: 需求 1.3**
  - [x] 2.3 实现 OutputSyncService
    - `execute_output_sync(job_id)` 支持全量/增量策略
    - `validate_output_data(data, mapping)` 写入前格式验证
    - `resume_from_checkpoint(job_id)` 断点续传
    - 复用 IncrementalPushService 的推送和重试逻辑
    - _需求: 2.1, 2.2, 2.3, 2.4_
  - [x] 2.4 属性测试：输出同步核心属性
    - **Property 4: 增量同步仅含新记录**
    - **Property 5: 写入前数据验证拦截**
    - **Property 6: 断点续传完整性**
    - **Property 7: 执行历史记录完整性**
    - **验证: 需求 2.2, 2.3, 2.4, 2.5**
  - [x] 2.5 实现连接测试与告警逻辑
    - 目标数据源连接失败返回错误信息 + 排查建议
    - 失败率超阈值触发告警通知
    - _需求: 1.5, 3.2, 3.4_
  - [x] 2.6 属性测试：连接失败与告警
    - **Property 3: 连接失败错误信息完整性**
    - **Property 8: 失败率告警触发**
    - **验证: 需求 1.5, 3.2**

- [x] 3. 检查点 - 确保输出同步测试通过
  - 确保所有测试通过，如有疑问请询问用户。

- [x] 4. API 密钥管理与网关
  - [x] 4.1 实现 APIKeyService
    - `create_key(config)` 生成密钥，哈希存储，仅返回一次完整值
    - `revoke_key`、`enable_key`、`disable_key` 状态管理
    - `validate_key(raw_key)` 验证并检查权限范围和过期
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.6_
  - [x] 4.2 属性测试：API 密钥核心属性
    - **Property 9: API 密钥创建仅一次可见**
    - **Property 10: API 密钥状态机正确性**
    - **Property 11: 过期/吊销密钥拒绝访问**
    - **Property 12: API 密钥调用计数递增**
    - **验证: 需求 4.2, 4.4, 4.5, 4.6**
  - [x] 4.3 实现 APIKeyAuthMiddleware 和速率限制扩展
    - X-API-Key 请求头认证中间件
    - 扩展现有 RateLimiter 支持按密钥的分钟/日配额
    - 调用日志记录
    - _需求: 5.2, 6.1, 6.2, 6.3_
  - [x] 4.4 属性测试：认证与速率限制
    - **Property 13: API 认证强制执行**
    - **Property 16: 速率限制强制执行**
    - **Property 17: API 调用日志完整性**
    - **验证: 需求 5.2, 6.1, 6.2, 6.3**
  - [x] 4.5 实现 ExternalDataRouter
    - 四个 GET 端点：annotations、augmented-data、quality-reports、experiments
    - 统一分页、字段筛选、排序参数
    - 权限范围校验（scopes）
    - _需求: 5.1, 5.3, 5.4, 5.5_
  - [x] 4.6 属性测试：API 响应与权限
    - **Property 14: API 响应分页正确性**
    - **Property 15: 权限范围强制执行**
    - **验证: 需求 5.3, 5.4, 5.5**

- [x] 5. 检查点 - 确保后端 API 测试通过
  - 确保所有测试通过，如有疑问请询问用户。

- [x] 6. 前端界面与集成
  - [x] 6.1 输出同步配置界面
    - 同步方向选择器（输入/输出/双向）
    - 目标数据源选择 + 字段映射配置
    - 复用现有 SyncTaskConfig 调度配置
    - i18n：zh/en 翻译文件同步更新
    - _需求: 1.1, 1.2, 1.3, 1.4_
  - [x] 6.2 API 管理标签页
    - 密钥列表（创建、启用/禁用、吊销）+ 创建时一次性展示完整密钥
    - 用量统计图表（Ant Design Charts，按日/周/月）
    - API 在线测试面板
    - RBAC 权限控制
    - i18n：zh/en 翻译文件同步更新
    - _需求: 4.1, 4.2, 6.4, 7.1, 7.2, 7.3, 7.4_
  - [x] 6.3 同步概览页面扩展
    - 展示输出同步任务状态统计
    - 输出同步历史记录展示
    - _需求: 3.1, 3.3_

- [x] 7. 最终检查点 - 确保所有测试通过
  - 确保所有测试通过，如有疑问请询问用户。

## 备注

- 标记 `*` 的子任务为可选，可跳过以加速 MVP
- 每个任务引用具体需求编号，确保可追溯
- 属性测试使用 hypothesis 库，每个属性至少 100 次迭代
- 所有前端用户可见文本必须使用 i18n（`t()` 包裹）
