# Requirements Document: Data Sync Pipeline (数据同步全流程)

## Introduction

本模块优化 `src/extractors/` 和 `src/sync/`，实现客户数据库读取/拉取/接收的完整同步流程，支持保存/不保存策略、业务逻辑提炼（AI 语义增强）和 AI 友好数据输出。

## Glossary

- **Data_Reader**: 数据读取器，支持 JDBC/ODBC 方式读取客户数据库
- **Data_Puller**: 数据拉取器，支持定时轮询拉取数据
- **Data_Receiver**: 数据接收器，支持 Webhook 接收推送数据
- **Save_Strategy_Manager**: 保存策略管理器，管理数据保存/内存策略
- **Semantic_Refiner**: 语义提炼器，使用 AI 增强数据语义可读性
- **AI_Friendly_Exporter**: AI 友好导出器，导出适合 AI 处理的数据格式
- **Sync_Scheduler**: 同步调度器，管理同步任务调度

## Requirements

### Requirement 1: 数据读取

**User Story:** 作为系统管理员，我希望能够从客户数据库读取数据，以便将数据导入标注系统。

#### Acceptance Criteria

1. THE Data_Reader SHALL 支持以下数据库类型：PostgreSQL、MySQL、SQLite、Oracle、SQL Server
2. WHEN 连接数据库 THEN THE Data_Reader SHALL 使用只读权限连接
3. THE Data_Reader SHALL 支持 JDBC 和 ODBC 两种连接方式
4. WHEN 读取数据 THEN THE Data_Reader SHALL 支持 SQL 查询和表名两种方式
5. THE Data_Reader SHALL 支持分页读取，避免内存溢出
6. WHEN 读取完成 THEN THE Data_Reader SHALL 返回数据统计（行数、列数、大小）

### Requirement 2: 数据拉取

**User Story:** 作为系统管理员，我希望系统能够定时拉取客户数据，以便保持数据同步。

#### Acceptance Criteria

1. THE Data_Puller SHALL 支持定时轮询拉取（Cron 表达式）
2. THE Data_Puller SHALL 支持增量拉取，基于时间戳或版本号
3. WHEN 拉取数据 THEN THE Data_Puller SHALL 记录拉取位置，支持断点续传
4. THE Data_Puller SHALL 支持配置拉取频率（最小 1 分钟）
5. WHEN 拉取失败 THEN THE Data_Puller SHALL 自动重试（最多 3 次）
6. THE Data_Puller SHALL 支持并行拉取多个数据源

### Requirement 3: 数据接收

**User Story:** 作为系统管理员，我希望系统能够接收客户推送的数据，以便实现实时数据同步。

#### Acceptance Criteria

1. THE Data_Receiver SHALL 提供 Webhook 端点接收推送数据
2. THE Data_Receiver SHALL 支持 JSON 和 CSV 两种数据格式
3. WHEN 接收数据 THEN THE Data_Receiver SHALL 验证数据格式和签名
4. THE Data_Receiver SHALL 支持批量接收，单次最多 10000 条
5. WHEN 接收成功 THEN THE Data_Receiver SHALL 返回确认响应
6. THE Data_Receiver SHALL 支持幂等处理，避免重复数据

### Requirement 4: 保存策略

**User Story:** 作为系统管理员，我希望配置数据保存策略，以便根据场景选择保存到数据库或仅在内存处理。

#### Acceptance Criteria

1. THE Save_Strategy_Manager SHALL 支持以下策略：持久化保存、内存处理、混合模式
2. WHEN 选择持久化保存 THEN THE Save_Strategy_Manager SHALL 将数据存储到 PostgreSQL
3. WHEN 选择内存处理 THEN THE Save_Strategy_Manager SHALL 仅在内存中处理数据，处理完成后释放
4. WHEN 选择混合模式 THEN THE Save_Strategy_Manager SHALL 根据数据大小自动选择策略
5. THE Save_Strategy_Manager SHALL 支持配置数据保留期限
6. WHEN 数据过期 THEN THE Save_Strategy_Manager SHALL 自动清理过期数据

### Requirement 5: 语义提炼

**User Story:** 作为数据分析师，我希望系统能够提炼数据的业务语义，以便提升数据的可读性和 AI 处理效果。

#### Acceptance Criteria

1. THE Semantic_Refiner SHALL 使用 LLM 分析数据的业务含义
2. THE Semantic_Refiner SHALL 生成字段描述和数据字典
3. THE Semantic_Refiner SHALL 识别数据中的实体和关系
4. WHEN 提炼完成 THEN THE Semantic_Refiner SHALL 生成语义增强后的数据描述
5. THE Semantic_Refiner SHALL 支持自定义提炼规则
6. THE Semantic_Refiner SHALL 缓存提炼结果，避免重复计算

### Requirement 6: AI 友好导出

**User Story:** 作为 AI 工程师，我希望导出 AI 友好的数据格式，以便用于模型训练和推理。

#### Acceptance Criteria

1. THE AI_Friendly_Exporter SHALL 支持以下导出格式：JSON、CSV、JSONL、COCO、Pascal VOC
2. THE AI_Friendly_Exporter SHALL 在导出数据中包含语义增强信息
3. THE AI_Friendly_Exporter SHALL 支持数据分割（训练集/验证集/测试集）
4. WHEN 导出数据 THEN THE AI_Friendly_Exporter SHALL 生成数据统计报告
5. THE AI_Friendly_Exporter SHALL 支持增量导出
6. THE AI_Friendly_Exporter SHALL 支持数据脱敏导出

### Requirement 7: 同步调度

**User Story:** 作为系统管理员，我希望管理同步任务的调度，以便控制数据同步的时机和频率。

#### Acceptance Criteria

1. THE Sync_Scheduler SHALL 支持 Cron 表达式配置调度
2. THE Sync_Scheduler SHALL 支持手动触发同步
3. THE Sync_Scheduler SHALL 显示同步任务状态（等待/运行/完成/失败）
4. WHEN 同步失败 THEN THE Sync_Scheduler SHALL 发送告警通知
5. THE Sync_Scheduler SHALL 支持同步任务优先级
6. THE Sync_Scheduler SHALL 记录完整的同步历史

### Requirement 8: 前端配置界面

**User Story:** 作为系统管理员，我希望通过可视化界面配置数据同步，以便无需修改代码即可管理同步设置。

#### Acceptance Criteria

1. THE Sync_Config_UI SHALL 显示所有数据源和同步状态
2. THE Sync_Config_UI SHALL 支持配置读取/拉取/接收方式
3. THE Sync_Config_UI SHALL 支持配置保存策略
4. THE Sync_Config_UI SHALL 支持配置同步调度
5. THE Sync_Config_UI SHALL 显示同步历史和统计
6. THE Sync_Config_UI SHALL 支持手动触发同步和导出
