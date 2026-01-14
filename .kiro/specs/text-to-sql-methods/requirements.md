# Requirements Document: Text-to-SQL Methods (Text-to-SQL 方法)

## Introduction

本模块实现多种 Text-to-SQL 方法，支持自然语言查询转换为 SQL 语句。核心目标是提供灵活的方法切换机制，根据场景（结构化/非结构化）和数据库类型自动选择最优方法。

## Glossary

- **Text_to_SQL_Engine**: Text-to-SQL 引擎，负责将自然语言转换为 SQL 语句
- **Template_Filler**: 模板填充器，基于预定义 SQL 模板进行槽位填充
- **LLM_SQL_Generator**: LLM SQL 生成器，使用大语言模型生成 SQL
- **Hybrid_Generator**: 混合生成器，结合规则和 LLM 的优势
- **Method_Switcher**: 方法切换器，根据场景自动选择最优方法
- **Schema_Analyzer**: 数据库 Schema 分析器，提取表结构信息
- **Third_Party_Adapter**: 第三方工具适配器，对接外部专业 Text-to-SQL 服务
- **Plugin_Interface**: 插件接口规范，定义第三方工具必须实现的方法

## Requirements

### Requirement 1: 模板填充方法

**User Story:** 作为数据分析师，我希望使用模板填充方法快速生成常见查询，以便在结构化场景下获得稳定可靠的 SQL。

#### Acceptance Criteria

1. WHEN 用户输入匹配预定义模板的查询 THEN THE Template_Filler SHALL 识别模板并填充参数
2. WHEN 模板填充完成 THEN THE Template_Filler SHALL 返回语法正确的 SQL 语句
3. THE Template_Filler SHALL 支持以下模板类型：聚合查询、筛选查询、排序查询、分组查询、连接查询
4. WHEN 用户输入不匹配任何模板 THEN THE Template_Filler SHALL 返回匹配失败状态并建议使用 LLM 方法
5. THE Template_Filler SHALL 支持参数类型验证（数字、字符串、日期）

### Requirement 2: LLM 生成方法

**User Story:** 作为数据分析师，我希望使用 LLM 生成复杂查询，以便处理非结构化的自然语言描述。

#### Acceptance Criteria

1. WHEN 用户输入自然语言查询 THEN THE LLM_SQL_Generator SHALL 调用 LLM 生成 SQL 语句
2. WHEN 生成 SQL THEN THE LLM_SQL_Generator SHALL 将数据库 Schema 作为上下文提供给 LLM
3. THE LLM_SQL_Generator SHALL 支持 LangChain 和 SQLCoder 等开源框架
4. WHEN LLM 返回 SQL THEN THE LLM_SQL_Generator SHALL 验证 SQL 语法正确性
5. IF SQL 语法错误 THEN THE LLM_SQL_Generator SHALL 自动重试生成（最多 3 次）

### Requirement 3: 混合方法

**User Story:** 作为系统管理员，我希望使用混合方法，以便结合规则的稳定性和 LLM 的灵活性。

#### Acceptance Criteria

1. WHEN 用户输入查询 THEN THE Hybrid_Generator SHALL 首先尝试模板匹配
2. IF 模板匹配失败 THEN THE Hybrid_Generator SHALL 回退到 LLM 生成
3. WHEN 使用 LLM 生成 THEN THE Hybrid_Generator SHALL 使用规则对 SQL 进行后处理优化
4. THE Hybrid_Generator SHALL 记录每次查询使用的方法（模板/LLM/混合）
5. WHEN 混合方法生成 SQL THEN THE Hybrid_Generator SHALL 返回置信度分数

### Requirement 4: 方法切换

**User Story:** 作为系统管理员，我希望能够配置和切换 Text-to-SQL 方法，以便根据场景选择最优方案。

#### Acceptance Criteria

1. WHEN 管理员配置默认方法 THEN THE Method_Switcher SHALL 使用该方法处理查询
2. WHEN 调用时指定方法参数 THEN THE Method_Switcher SHALL 临时使用指定方法
3. THE Method_Switcher SHALL 支持以下方法：template、llm、hybrid
4. WHEN 切换方法 THEN THE Method_Switcher SHALL 在 500ms 内完成切换
5. THE Method_Switcher SHALL 支持基于数据库类型的自动方法选择（PostgreSQL/MySQL/SQLite）

### Requirement 5: Schema 分析

**User Story:** 作为开发者，我希望系统能自动分析数据库 Schema，以便为 LLM 提供准确的上下文。

#### Acceptance Criteria

1. WHEN 连接数据库 THEN THE Schema_Analyzer SHALL 自动提取表结构信息
2. THE Schema_Analyzer SHALL 提取以下信息：表名、列名、数据类型、主键、外键、索引
3. WHEN Schema 变更 THEN THE Schema_Analyzer SHALL 支持增量更新
4. THE Schema_Analyzer SHALL 生成 LLM 友好的 Schema 描述文本
5. WHEN 表数量超过 50 THEN THE Schema_Analyzer SHALL 支持相关表筛选以减少上下文长度

### Requirement 6: 第三方工具对接

**User Story:** 作为系统管理员，我希望能够对接第三方专业 Text-to-SQL 工具，以便利用成熟的商业或开源解决方案。

#### Acceptance Criteria

1. THE Third_Party_Adapter SHALL 提供统一的插件接口规范（Plugin Interface）
2. WHEN 注册第三方工具 THEN THE Third_Party_Adapter SHALL 验证工具实现了必要的接口方法
3. THE Third_Party_Adapter SHALL 支持以下对接方式：REST API、gRPC、本地 SDK
4. WHEN 调用第三方工具 THEN THE Third_Party_Adapter SHALL 将请求转换为工具特定格式
5. WHEN 第三方工具返回结果 THEN THE Third_Party_Adapter SHALL 将结果转换为统一格式
6. THE Third_Party_Adapter SHALL 支持以下主流工具：DIN-SQL、DAIL-SQL、C3SQL、Vanna.ai
7. IF 第三方工具不可用 THEN THE Third_Party_Adapter SHALL 自动回退到内置方法

### Requirement 7: 前端配置界面

**User Story:** 作为系统管理员，我希望通过可视化界面配置 Text-to-SQL 和第三方工具，以便无需修改代码即可管理设置。

#### Acceptance Criteria

1. WHEN 管理员访问配置页面 THEN THE Config_UI SHALL 显示当前方法配置和可用选项
2. WHEN 管理员选择方法 THEN THE Config_UI SHALL 实时预览方法特点和适用场景
3. WHEN 管理员保存配置 THEN THE Config_UI SHALL 调用后端 API 持久化配置
4. THE Config_UI SHALL 提供 SQL 生成测试功能，输入自然语言即可预览生成的 SQL
5. WHEN 测试生成 SQL THEN THE Config_UI SHALL 显示使用的方法和置信度
6. THE Config_UI SHALL 提供第三方工具管理界面，支持添加、编辑、删除、启用/禁用工具
7. WHEN 添加第三方工具 THEN THE Config_UI SHALL 提供表单配置工具连接信息（URL、API Key、超时等）
8. THE Config_UI SHALL 显示已注册第三方工具的健康状态和调用统计
