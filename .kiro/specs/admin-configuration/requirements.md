# Requirements Document: Admin Configuration (管理员配置)

## Introduction

本模块实现平台管理员的可视化配置界面，支持 LLM 配置、数据库连接配置、同步策略配置、SQL 构建器等功能。核心目标是让管理员无需修改代码即可完成系统配置，提升运维效率。

## Glossary

- **Admin_Dashboard**: 管理员仪表盘，提供系统概览和快捷操作入口
- **LLM_Config_Panel**: LLM 配置面板，管理 LLM 服务配置
- **DB_Config_Panel**: 数据库配置面板，管理客户数据库连接
- **Sync_Strategy_Panel**: 同步策略面板，配置数据同步规则
- **SQL_Builder**: SQL 构建器，可视化构建 SQL 查询
- **Config_Validator**: 配置验证器，验证配置有效性
- **Config_History**: 配置历史，记录配置变更

## Requirements

### Requirement 1: 管理员仪表盘

**User Story:** 作为系统管理员，我希望有一个统一的仪表盘，以便快速了解系统状态和进行常用操作。

#### Acceptance Criteria

1. WHEN 管理员登录后访问仪表盘 THEN THE Admin_Dashboard SHALL 显示系统健康状态概览
2. THE Admin_Dashboard SHALL 显示以下关键指标：活跃用户数、任务数、标注进度、系统资源使用
3. WHEN 管理员点击快捷操作 THEN THE Admin_Dashboard SHALL 跳转到对应配置页面
4. THE Admin_Dashboard SHALL 显示最近的系统告警和通知
5. WHEN 系统状态异常 THEN THE Admin_Dashboard SHALL 高亮显示异常指标

### Requirement 2: LLM 配置管理

**User Story:** 作为系统管理员，我希望通过可视化界面配置 LLM 服务，以便无需修改配置文件即可管理 AI 能力。

#### Acceptance Criteria

1. WHEN 管理员访问 LLM 配置页面 THEN THE LLM_Config_Panel SHALL 显示当前 LLM 配置状态
2. THE LLM_Config_Panel SHALL 支持配置以下 LLM 类型：本地 Ollama、云端 OpenAI、中国 LLM（千问、智谱）
3. WHEN 管理员修改 LLM 配置 THEN THE Config_Validator SHALL 实时验证配置有效性
4. WHEN 管理员保存配置 THEN THE LLM_Config_Panel SHALL 调用后端 API 持久化配置
5. THE LLM_Config_Panel SHALL 提供连接测试功能，验证 LLM 服务可用性
6. THE LLM_Config_Panel SHALL 对 API Key 等敏感信息进行脱敏显示

### Requirement 3: 数据库连接配置

**User Story:** 作为系统管理员，我希望配置客户数据库连接，以便系统能够读取客户数据进行标注。

#### Acceptance Criteria

1. WHEN 管理员访问数据库配置页面 THEN THE DB_Config_Panel SHALL 显示已配置的数据库连接列表
2. THE DB_Config_Panel SHALL 支持以下数据库类型：PostgreSQL、MySQL、SQLite、Oracle、SQL Server
3. WHEN 管理员添加数据库连接 THEN THE DB_Config_Panel SHALL 提供连接参数表单（主机、端口、用户名、密码、数据库名）
4. WHEN 管理员保存连接配置 THEN THE Config_Validator SHALL 验证连接有效性
5. THE DB_Config_Panel SHALL 提供连接测试功能，显示连接状态和延迟
6. THE DB_Config_Panel SHALL 对密码等敏感信息进行加密存储和脱敏显示
7. WHEN 管理员配置只读连接 THEN THE DB_Config_Panel SHALL 验证连接权限为只读

### Requirement 4: 同步策略配置

**User Story:** 作为系统管理员，我希望配置数据同步策略，以便控制数据如何从客户数据库同步到标注系统。

#### Acceptance Criteria

1. WHEN 管理员访问同步策略页面 THEN THE Sync_Strategy_Panel SHALL 显示当前同步策略配置
2. THE Sync_Strategy_Panel SHALL 支持以下同步模式：全量同步、增量同步、实时同步
3. WHEN 管理员配置增量同步 THEN THE Sync_Strategy_Panel SHALL 要求指定增量字段（时间戳/版本号）
4. THE Sync_Strategy_Panel SHALL 支持配置同步频率：手动、定时（Cron 表达式）、实时（Webhook）
5. WHEN 管理员配置同步策略 THEN THE Sync_Strategy_Panel SHALL 支持数据过滤条件配置
6. THE Sync_Strategy_Panel SHALL 显示同步历史和状态（成功/失败/进行中）
7. WHEN 同步失败 THEN THE Sync_Strategy_Panel SHALL 显示错误详情和重试选项

### Requirement 5: SQL 构建器

**User Story:** 作为系统管理员，我希望使用可视化 SQL 构建器，以便无需编写 SQL 即可定义数据查询。

#### Acceptance Criteria

1. WHEN 管理员访问 SQL 构建器 THEN THE SQL_Builder SHALL 显示可用的表和字段列表
2. THE SQL_Builder SHALL 支持拖拽方式选择表和字段
3. THE SQL_Builder SHALL 支持可视化配置 WHERE 条件、ORDER BY、GROUP BY、LIMIT
4. WHEN 管理员构建查询 THEN THE SQL_Builder SHALL 实时生成对应的 SQL 语句
5. THE SQL_Builder SHALL 提供 SQL 预览和语法高亮
6. WHEN 管理员执行查询 THEN THE SQL_Builder SHALL 显示查询结果预览（限制 100 行）
7. THE SQL_Builder SHALL 支持保存常用查询为模板

### Requirement 6: 配置历史和回滚

**User Story:** 作为系统管理员，我希望查看配置变更历史，以便追踪变更和在需要时回滚。

#### Acceptance Criteria

1. WHEN 管理员访问配置历史页面 THEN THE Config_History SHALL 显示所有配置变更记录
2. THE Config_History SHALL 记录以下信息：变更时间、变更人、变更类型、变更前后值
3. WHEN 管理员查看变更详情 THEN THE Config_History SHALL 显示配置差异对比
4. WHEN 管理员选择回滚 THEN THE Config_History SHALL 恢复到指定版本的配置
5. THE Config_History SHALL 支持按时间范围、配置类型、变更人筛选

### Requirement 7: 第三方工具配置

**User Story:** 作为系统管理员，我希望配置第三方工具集成，以便扩展系统能力。

#### Acceptance Criteria

1. WHEN 管理员访问第三方工具配置页面 THEN THE Config_Panel SHALL 显示已集成的工具列表
2. THE Config_Panel SHALL 支持配置以下工具类型：Text-to-SQL 工具、AI 标注工具、数据处理工具
3. WHEN 管理员添加第三方工具 THEN THE Config_Panel SHALL 提供连接配置表单（端点、API Key、超时等）
4. THE Config_Panel SHALL 提供工具健康检查功能
5. WHEN 管理员启用/禁用工具 THEN THE Config_Panel SHALL 立即生效且不影响其他功能
6. THE Config_Panel SHALL 显示工具调用统计（调用次数、成功率、平均延迟）
