# 实施计划：数据湖/数仓集成与可视化

## 概述

基于现有 DataSync 模块的 ConnectorFactory 模式，扩展数据湖/数仓连接器，新增 REST API、RBAC 权限、可视化看板，前端新增管理页面和 Dashboard。

## 任务

- [x] 1. 后端：枚举扩展与基类实现
  - [x] 1.1 在 `src/sync/models.py` 的 DataSourceType 枚举中新增 7 种数据湖/数仓类型（HIVE, CLICKHOUSE, DORIS, SPARK_SQL, PRESTO_TRINO, DELTA_LAKE, ICEBERG），扩展 SyncResourceType 新增 DATALAKE_SOURCE 和 DATALAKE_DASHBOARD
    - _需求: 1.1, 7.1_
  - [x] 1.2 创建 `src/sync/connectors/datalake/` 目录，实现 DatalakeConnectorConfig 和 DatalakeBaseConnector 基类，继承 BaseConnector，提供 fetch_databases、fetch_tables、fetch_table_preview、execute_query、get_query_metrics 抽象方法
    - _需求: 1.4, 4.1, 4.2, 5.1_
  - [x] 1.3 编写属性测试：连接器工厂完整性
    - **Property 1: Connector factory completeness**
    - **验证: 需求 1.1, 1.2, 1.4**
  - [x] 1.4 编写属性测试：无效类型拒绝
    - **Property 2: Invalid type rejection**
    - **验证: 需求 1.3**

- [x] 2. 后端：具体连接器实现与注册
  - [x] 2.1 实现 ClickHouseConnector、HiveConnector、DorisConnector（含 StarRocks 兼容），各自定义 Config 子类，在模块末尾注册到 ConnectorFactory
    - _需求: 1.1, 1.2_
  - [x] 2.2 实现 SparkSQLConnector、PrestoTrinoConnector、DeltaLakeConnector、IcebergConnector，注册到 ConnectorFactory
    - _需求: 1.1, 1.2_
  - [x] 2.3 编写属性测试：行数限制执行
    - **Property 7: Row limit enforcement**
    - **验证: 需求 4.3, 5.3**
  - [x] 2.4 编写属性测试：查询超时保护
    - **Property 8: Query timeout protection**
    - **验证: 需求 5.2**

- [x] 3. 后端：数据模型与 Pydantic Schema
  - [x] 3.1 创建 `src/sync/connectors/datalake/models.py`，实现 DatalakeMetricsModel（含 source_id、tenant_id、metric_type、metric_data、recorded_at），创建 Alembic 迁移
    - _需求: 5.4, 6.1_
  - [x] 3.2 创建 `src/sync/connectors/datalake/schemas.py`，实现 DatalakeSourceCreate、DatalakeSourceResponse、DashboardOverview、SourceHealthStatus、VolumeTrendData、QueryPerformanceData、DataFlowGraph 等 Pydantic 模型
    - _需求: 2.1, 2.2, 6.1, 6.4, 6.5_
  - [x] 3.3 编写属性测试：数据源验证往返一致性
    - **Property 3: Data source validation round-trip**
    - **验证: 需求 2.1, 2.2**

- [x] 4. 检查点 - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 5. 后端：REST API 路由与 RBAC
  - [x] 5.1 创建 `src/sync/connectors/datalake/router.py`，实现数据源 CRUD 端点（POST/GET/PUT/DELETE /sources）、连接测试端点、Schema 浏览端点（databases/tables/schema/preview）
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 4.1, 4.2, 4.3, 4.4_
  - [x] 5.2 实现看板数据端点（dashboard/overview、health、volume-trends、query-performance、data-flow），包含看板数据聚合算法
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x] 5.3 集成 RBAC 权限装饰器：ADMIN/TECHNICAL_EXPERT 完全管理，BUSINESS_EXPERT 只读+看板，VIEWER 仅看板；实现租户隔离；敏感字段加密存储和 API 脱敏
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3_
  - [x] 5.4 在 `src/app.py` 中注册 datalake router
    - _需求: 2.1_
  - [x] 5.5 编写属性测试：租户隔离
    - **Property 4: Tenant isolation**
    - **验证: 需求 2.3, 7.5**
  - [x] 5.6 编写属性测试：级联删除
    - **Property 5: Cascade deletion**
    - **验证: 需求 2.5**
  - [x] 5.7 编写属性测试：连接测试状态一致性
    - **Property 6: Connection test status consistency**
    - **验证: 需求 3.1, 3.2, 3.4**
  - [x] 5.8 编写属性测试：RBAC 权限矩阵
    - **Property 11: RBAC permission matrix**
    - **验证: 需求 7.1, 7.2, 7.3, 7.4**
  - [x] 5.9 编写属性测试：敏感数据保护
    - **Property 12: Sensitive data protection**
    - **验证: 需求 8.1, 8.2**

- [x] 6. 检查点 - 确保后端所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 7. 后端：监控服务与指标记录
  - [x] 7.1 扩展 MonitoringService，实现数据湖/数仓指标采集（健康状态、数据量、查询性能），异步写入 DatalakeMetricsModel
    - _需求: 3.3, 3.4, 5.4, 6.1_
  - [x] 7.2 编写属性测试：看板概览数值不变量
    - **Property 9: Dashboard overview numerical invariant**
    - **验证: 需求 6.1, 6.2**
  - [x] 7.3 编写属性测试：查询性能统计正确性
    - **Property 10: Query performance statistics correctness**
    - **验证: 需求 6.4**
  - [x] 7.4 编写属性测试：指标记录完整性
    - **Property 13: Metrics recording completeness**
    - **验证: 需求 5.4**

- [x] 8. 前端：API 层与状态管理
  - [x] 8.1 创建 `frontend/src/pages/DataSync/Datalake/` 目录结构，实现 datalake API 服务层（React Query hooks），定义 TypeScript 类型接口
    - _需求: 2.1, 6.1_
  - [x] 8.2 添加 i18n 翻译键（中英文）到 dataSync 命名空间
    - _需求: 6.1_

- [x] 9. 前端：数据源管理页面
  - [x] 9.1 实现数据源列表页（Sources/index.tsx），包含 ProTable 列表、创建/编辑/删除操作、连接测试按钮，按角色控制操作按钮显隐
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 7.1, 7.2, 7.3_
  - [x] 9.2 实现 Schema 浏览器页面（SchemaBrowser/index.tsx），支持数据库/表树形浏览、表结构查看、数据预览
    - _需求: 4.1, 4.2, 4.3, 4.4_

- [x] 10. 前端：可视化看板
  - [x] 10.1 实现看板页面（Dashboard/index.tsx），包含概览统计卡片（总数/活跃/异常/数据量/延迟）、数据量趋势图、查询性能图表、数据流向图
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x] 10.2 在 DataSync 主页 index.tsx 中添加数据湖/数仓 Tab 导航，注册路由
    - _需求: 6.1_

- [x] 11. 最终检查点 - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

## 备注

- 标记 `*` 的子任务为可选，可跳过以加速 MVP
- 每个任务引用具体需求条款以确保可追溯性
- 属性测试使用 Hypothesis (Python) 库，验证设计文档中的 13 个正确性属性
- 前端使用 @ant-design/charts 实现看板图表
