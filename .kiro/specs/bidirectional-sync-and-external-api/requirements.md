# 需求文档：双向同步与外部 API 访问

## 介绍

在现有数据同步模块基础上，扩展两项核心能力：（A）支持将系统内已处理的 AI 友好型数据推送回客户源数据库，实现真正的双向同步；（B）提供外部 API 接口密钥管理和数据读取端点，允许外部应用程序直接通过 API 调用本系统的 AI 友好型数据。

## 术语表

- **Sync_Engine**: 数据同步引擎，已有的核心同步服务（`src/sync/`）
- **Output_Sync_Service**: 输出同步服务，负责将数据推送到客户目标数据库
- **API_Gateway**: 外部 API 网关，管理外部应用的 API 访问
- **API_Key_Manager**: 接口密钥管理器，负责密钥的生成、吊销和权限控制
- **Rate_Limiter**: 速率限制器，控制外部 API 的调用频率（复用 `src/sync/gateway/rate_limiter.py`）
- **Field_Mapper**: 字段映射器，处理双向同步中的字段映射关系
- **Target_Database**: 客户目标数据库，接收输出数据的外部数据库
- **AI_Data**: AI 友好型数据，包括标注结果、增强数据、质量报告、AI 试验结果

## 需求

### 需求 1: 输出同步任务创建

**用户故事:** 作为数据管理员，我希望在创建同步任务时能选择同步方向（输入/输出/双向），以便将处理完成的数据推送回客户数据库。

#### 验收标准

1. WHEN 创建同步任务时，THE Sync_Engine SHALL 提供同步方向选择（输入、输出、双向）
2. WHEN 选择输出方向时，THE Sync_Engine SHALL 允许用户选择目标数据源和源数据集
3. THE Field_Mapper SHALL 支持输出方向的字段映射配置，包括字段名映射和类型转换
4. WHEN 配置双向同步时，THE Sync_Engine SHALL 分别配置输入和输出的字段映射规则
5. IF 目标数据源连接失败，THEN THE Sync_Engine SHALL 返回明确的连接错误信息和排查建议

### 需求 2: 输出同步执行与调度

**用户故事:** 作为数据管理员，我希望输出同步支持定时调度和手动触发，以便按业务节奏将数据推送到客户系统。

#### 验收标准

1. THE Output_Sync_Service SHALL 支持手动触发和 Cron 定时调度两种执行模式
2. WHEN 执行输出同步时，THE Output_Sync_Service SHALL 支持全量和增量两种同步策略
3. THE Output_Sync_Service SHALL 在写入目标数据库前进行数据格式验证
4. WHEN 输出同步过程中发生错误，THE Output_Sync_Service SHALL 记录失败记录并支持断点续传
5. THE Output_Sync_Service SHALL 在同步历史中记录输出任务的执行详情（行数、耗时、状态）

### 需求 3: 输出同步监控与告警

**用户故事:** 作为运维人员，我希望能监控输出同步任务的运行状态，以便及时发现和处理异常。

#### 验收标准

1. THE Sync_Engine SHALL 在同步概览页面展示输出同步任务的状态统计
2. WHEN 输出同步任务失败率超过阈值时，THE Sync_Engine SHALL 发送告警通知
3. THE Sync_Engine SHALL 记录每次输出同步的数据量、耗时和错误详情
4. WHEN 目标数据库不可达时，THE Sync_Engine SHALL 自动暂停相关输出任务并通知管理员

### 需求 4: API 密钥管理

**用户故事:** 作为系统管理员，我希望能为外部应用生成和管理 API 密钥，以便控制外部系统对 AI 数据的访问权限。

#### 验收标准

1. THE API_Key_Manager SHALL 提供 API 密钥的创建界面，支持设置名称、描述和过期时间
2. THE API_Key_Manager SHALL 在创建时仅展示一次完整密钥，之后只显示前缀标识
3. WHEN 创建密钥时，THE API_Key_Manager SHALL 允许配置可访问的数据范围（标注结果、增强数据、质量报告、AI 试验结果）
4. THE API_Key_Manager SHALL 支持密钥的启用、禁用和吊销操作
5. THE API_Key_Manager SHALL 为每个密钥记录最近调用时间和累计调用次数
6. IF API 密钥已过期或被吊销，THEN THE API_Gateway SHALL 拒绝该密钥的所有请求并返回 401 状态码

### 需求 5: 外部 API 数据读取端点

**用户故事:** 作为外部应用开发者，我希望通过 REST API 直接读取 SuperInsight 平台的 AI 友好型数据，以便集成到自己的应用中。

#### 验收标准

1. THE API_Gateway SHALL 提供 REST API 端点，支持读取标注结果、增强数据、质量报告和 AI 试验结果
2. THE API_Gateway SHALL 通过请求头中的 API Key 进行身份验证（`X-API-Key` 头）
3. THE API_Gateway SHALL 支持分页查询、字段筛选和排序参数
4. THE API_Gateway SHALL 返回 JSON 格式的响应数据，包含标准的分页元信息
5. IF 请求的数据范围超出密钥权限，THEN THE API_Gateway SHALL 返回 403 状态码和权限不足说明

### 需求 6: API 速率限制与用量追踪

**用户故事:** 作为系统管理员，我希望能对外部 API 设置速率限制并追踪用量，以便保护系统资源和进行用量计费。

#### 验收标准

1. THE Rate_Limiter SHALL 支持按密钥设置每分钟和每日的请求配额
2. WHEN 请求超过速率限制时，THE Rate_Limiter SHALL 返回 429 状态码和重试等待时间（`Retry-After` 头）
3. THE API_Gateway SHALL 记录每个密钥的调用日志（时间、端点、响应状态、耗时）
4. THE API_Gateway SHALL 在管理界面展示各密钥的用量统计图表（按日/周/月）

### 需求 7: 外部 API 管理界面

**用户故事:** 作为系统管理员，我希望在数据同步模块中有一个 API 管理标签页，以便集中管理所有外部 API 访问配置。

#### 验收标准

1. THE API_Gateway SHALL 在数据同步模块中新增「API 管理」标签页
2. THE API_Gateway SHALL 在标签页中展示密钥列表、用量概览和 API 文档入口
3. THE API_Gateway SHALL 提供 API 端点的在线测试功能（输入参数、查看响应）
4. WHEN 用户访问 API 管理页面时，THE API_Gateway SHALL 根据 RBAC 权限控制可见内容
