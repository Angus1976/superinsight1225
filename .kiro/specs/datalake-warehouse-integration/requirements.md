# 需求文档：数据湖/数仓集成与可视化

## 简介

本文档定义数据同步模块（DataSync）扩展数据湖/数仓连接能力的功能需求，包括连接器管理、Schema 浏览、可视化看板和权限控制。

## 术语表

- **ConnectorFactory**：连接器工厂，负责根据类型创建对应连接器实例
- **DatalakeBaseConnector**：数据湖/数仓连接器基类，提供通用连接、查询和 Schema 浏览能力
- **DataSourceModel**：数据源持久化模型，存储连接配置和状态
- **MonitoringService**：监控服务，负责采集和聚合数据源健康状态与性能指标
- **DashboardOverview**：看板概览数据模型，包含数据源统计和聚合指标
- **DATALAKE_TYPES**：数据湖/数仓类型集合（Hive、ClickHouse、Doris、Spark SQL、Presto/Trino、Delta Lake、Iceberg）

## 需求

### 需求 1：连接器注册与创建

**用户故事：** 作为技术专家，我希望通过统一工厂创建各类数据湖/数仓连接器，以便复用现有连接器架构。

#### 验收标准

1. THE ConnectorFactory SHALL 支持创建 DATALAKE_TYPES 中所有七种连接器类型的实例
2. WHEN 传入有效连接配置时，THE ConnectorFactory SHALL 返回对应类型的连接器实例
3. WHEN 传入未注册的连接器类型时，THE ConnectorFactory SHALL 抛出明确的类型错误
4. THE DatalakeBaseConnector SHALL 提供 test_connection、fetch_databases、fetch_tables、fetch_table_preview 和 execute_query 方法

### 需求 2：数据源 CRUD 管理

**用户故事：** 作为管理员，我希望创建、查看、编辑和删除数据湖/数仓数据源，以便管理所有连接配置。

#### 验收标准

1. WHEN 用户提交有效的数据源配置时，THE API SHALL 创建数据源并返回完整的数据源信息
2. WHEN 用户提交缺少必填字段或格式错误的配置时，THE API SHALL 返回 422 错误并包含具体字段错误信息
3. WHEN 用户请求数据源列表时，THE API SHALL 仅返回当前租户的数据湖/数仓类型数据源
4. WHEN 用户更新数据源配置时，THE API SHALL 验证新配置并持久化更新
5. WHEN 用户删除数据源时，THE API SHALL 移除数据源及其关联的指标记录

### 需求 3：连接测试与健康检查

**用户故事：** 作为技术专家，我希望测试数据源连接并监控健康状态，以便及时发现连接问题。

#### 验收标准

1. WHEN 用户触发连接测试时，THE DatalakeBaseConnector SHALL 执行连接验证并返回连接状态和延迟信息
2. IF 连接测试失败，THEN THE DatalakeBaseConnector SHALL 返回 ERROR 状态并记录错误详情
3. IF 连接失败，THEN THE DatalakeBaseConnector SHALL 自动重试最多 3 次并使用指数退避策略
4. WHEN 连接测试完成时，THE API SHALL 更新 DataSourceModel 的健康检查状态和时间戳

### 需求 4：Schema 浏览与数据预览

**用户故事：** 作为技术专家，我希望浏览数据源的数据库、表结构并预览数据，以便了解数据内容。

#### 验收标准

1. WHEN 用户请求数据库列表时，THE DatalakeBaseConnector SHALL 返回该数据源的所有可用数据库名称
2. WHEN 用户请求表列表时，THE DatalakeBaseConnector SHALL 返回指定数据库的表信息（含行数和大小估算）
3. WHEN 用户预览表数据时，THE API SHALL 返回不超过指定行数的数据（默认 100 行，最大 1000 行）
4. WHEN 用户请求表结构时，THE API SHALL 返回完整的列名、类型和注释信息

### 需求 5：查询执行与超时保护

**用户故事：** 作为技术专家，我希望执行自定义 SQL 查询并受到超时保护，以便安全地探索数据。

#### 验收标准

1. WHEN 用户提交 SQL 查询时，THE DatalakeBaseConnector SHALL 使用参数化方式执行查询并返回结果
2. IF 查询执行时间超过 query_timeout 配置值，THEN THE DatalakeBaseConnector SHALL 自动取消查询并返回超时错误
3. THE DatalakeBaseConnector SHALL 限制单次查询返回行数不超过 max_query_rows 配置值
4. WHEN 查询完成时，THE MonitoringService SHALL 异步记录查询延迟和状态指标

### 需求 6：可视化看板

**用户故事：** 作为业务专家，我希望通过看板查看数据源状态、数据量趋势和查询性能，以便掌握数据资产概况。

#### 验收标准

1. WHEN 用户访问看板时，THE API SHALL 返回数据源总数、活跃数、异常数、总数据量和平均查询延迟
2. THE DashboardOverview SHALL 满足 total_sources 等于 active_sources 加 error_sources 加其余非活跃数据源数量
3. WHEN 用户查询数据量趋势时，THE API SHALL 返回指定时间段内按数据源分组的数据量变化数据
4. WHEN 用户查询查询性能时，THE API SHALL 返回平均延迟、P95 延迟、P99 延迟和失败查询数
5. WHEN 用户查看数据流向时，THE API SHALL 返回包含节点和边的有向图数据

### 需求 7：RBAC 权限控制

**用户故事：** 作为管理员，我希望不同角色有不同的访问权限，以便保障数据安全。

#### 验收标准

1. WHILE 用户角色为 ADMIN 或 TECHNICAL_EXPERT 时，THE API SHALL 允许执行所有数据源管理和查询操作
2. WHILE 用户角色为 BUSINESS_EXPERT 时，THE API SHALL 仅允许只读访问数据源列表和看板数据
3. WHILE 用户角色为 VIEWER 时，THE API SHALL 仅允许访问看板相关端点
4. IF 用户角色无权执行请求的操作，THEN THE API SHALL 返回 403 Forbidden 错误
5. THE API SHALL 对所有数据源操作执行租户隔离校验，确保用户只能访问本租户数据

### 需求 8：安全与数据保护

**用户故事：** 作为管理员，我希望连接配置中的敏感信息得到保护，以便防止数据泄露。

#### 验收标准

1. THE API SHALL 对连接配置中的密码和密钥字段进行加密存储
2. WHEN API 返回数据源信息时，THE API SHALL 对密码和密钥字段进行脱敏处理
3. THE DatalakeBaseConnector SHALL 使用参数化查询防止 SQL 注入