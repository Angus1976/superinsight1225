# Implementation Plan: Data Sync Pipeline (数据同步全流程)

## Overview

本实现计划将 Data Sync Pipeline 模块分解为可执行的编码任务，扩展现有 `src/extractors/` 和 `src/sync/` 模块，实现完整的数据同步流程。

## Tasks

- [x] 1. 设置项目结构和核心接口
  - 创建 `src/sync/pipeline/` 目录结构
  - 定义核心接口和类型
  - 设置测试框架配置
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1_

- [x] 2. 实现数据库连接器
  - [x] 2.1 实现连接器工厂和基类
    - 创建 `src/sync/pipeline/connectors/base.py`
    - 实现 ConnectorFactory 和 BaseConnector
    - _Requirements: 1.1, 1.3_

  - [x] 2.2 实现 PostgreSQL 连接器
    - 创建 `src/sync/pipeline/connectors/postgresql.py`
    - 实现只读连接和分页查询
    - _Requirements: 1.1, 1.2, 1.5_

  - [x] 2.3 实现 MySQL 连接器
    - 创建 `src/sync/pipeline/connectors/mysql.py`
    - 实现只读连接和分页查询
    - _Requirements: 1.1, 1.2, 1.5_

  - [x] 2.4 实现其他数据库连接器
    - 创建 SQLite、Oracle、SQL Server 连接器
    - _Requirements: 1.1_

  - [x] 2.5 编写连接器属性测试
    - **Property 1: 只读连接验证**
    - **Validates: Requirements 1.2**

- [x] 3. 实现 Data Reader
  - [x] 3.1 实现 DataReader 核心类
    - 创建 `src/sync/pipeline/data_reader.py`
    - 实现 connect、read_by_query、read_by_table 方法
    - _Requirements: 1.2, 1.4_

  - [x] 3.2 实现分页读取逻辑
    - 实现 AsyncIterator 分页返回
    - 实现内存安全的数据流处理
    - _Requirements: 1.5_

  - [x] 3.3 实现读取统计
    - 实现 get_statistics 方法
    - 返回行数、列数、大小统计
    - _Requirements: 1.6_

  - [x] 3.4 编写 DataReader 属性测试
    - **Property 2: 分页读取内存安全**
    - **Property 3: 读取统计完整性**
    - **Validates: Requirements 1.5, 1.6**

- [x] 4. 检查点 - 确保所有测试通过
  - 运行所有测试，确保 Data Reader 功能正常
  - 如有问题请咨询用户

- [x] 5. 实现 Data Puller
  - [x] 5.1 实现检查点存储
    - 创建 `src/sync/pipeline/checkpoint_store.py`
    - 实现检查点保存和恢复
    - _Requirements: 2.3_

  - [x] 5.2 实现 DataPuller 核心类
    - 创建 `src/sync/pipeline/data_puller.py`
    - 实现 pull、pull_incremental 方法
    - _Requirements: 2.1, 2.2_

  - [x] 5.3 实现重试机制
    - 实现 pull_with_retry 方法
    - 最多重试 3 次
    - _Requirements: 2.5_

  - [x] 5.4 实现并行拉取
    - 实现 pull_parallel 方法
    - 支持多数据源并行
    - _Requirements: 2.6_

  - [x] 5.5 实现 Cron 表达式解析
    - 验证 Cron 表达式格式
    - 验证最小间隔 1 分钟
    - _Requirements: 2.1, 2.4_

  - [x] 5.6 编写 DataPuller 属性测试
    - **Property 4: 增量拉取检查点持久化**
    - **Property 5: 拉取重试机制**
    - **Validates: Requirements 2.2, 2.3, 2.5**

- [x] 6. 实现 Data Receiver
  - [x] 6.1 实现幂等存储
    - 创建 `src/sync/pipeline/idempotency_store.py`
    - 实现幂等键存储和检查
    - _Requirements: 3.6_

  - [x] 6.2 实现 DataReceiver 核心类
    - 创建 `src/sync/pipeline/data_receiver.py`
    - 实现 receive 方法
    - _Requirements: 3.1, 3.2_

  - [x] 6.3 实现签名验证
    - 实现 verify_signature 方法
    - 支持 HMAC-SHA256 签名
    - _Requirements: 3.3_

  - [x] 6.4 实现数据解析
    - 实现 JSON 和 CSV 解析
    - 验证批量大小限制
    - _Requirements: 3.2, 3.4_

  - [x] 6.5 编写 DataReceiver 属性测试
    - **Property 6: Webhook 幂等处理**
    - **Property 7: 批量大小限制**
    - **Validates: Requirements 3.4, 3.6**

- [x] 7. 检查点 - 确保所有测试通过
  - 运行所有测试，确保 Data Puller 和 Data Receiver 功能正常
  - 如有问题请咨询用户

- [x] 8. 实现 Save Strategy Manager
  - [x] 8.1 实现 SaveStrategyManager 核心类
    - 创建 `src/sync/pipeline/save_strategy.py`
    - 实现 save、save_to_db、save_to_memory 方法
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 8.2 实现混合模式
    - 实现 save_hybrid 方法
    - 根据数据大小自动选择策略
    - _Requirements: 4.4_

  - [x] 8.3 实现数据清理
    - 实现 cleanup_expired 方法
    - 支持配置保留期限
    - _Requirements: 4.5, 4.6_

  - [x] 8.4 编写 SaveStrategyManager 属性测试
    - **Property 8: 保存策略正确性**
    - **Property 9: 混合模式自动选择**
    - **Validates: Requirements 4.2, 4.3, 4.4**

- [x] 9. 实现 Semantic Refiner
  - [x] 9.1 实现 SemanticRefiner 核心类
    - 创建 `src/sync/pipeline/semantic_refiner.py`
    - 实现 refine 方法
    - _Requirements: 5.1_

  - [x] 9.2 实现字段描述生成
    - 实现 generate_field_descriptions 方法
    - 调用 LLM 生成描述
    - _Requirements: 5.2_

  - [x] 9.3 实现数据字典生成
    - 实现 generate_data_dictionary 方法
    - _Requirements: 5.2_

  - [x] 9.4 实现实体和关系提取
    - 实现 extract_entities、extract_relations 方法
    - _Requirements: 5.3_

  - [x] 9.5 实现缓存机制
    - 实现缓存键生成和缓存存储
    - _Requirements: 5.6_

  - [x] 9.6 实现自定义规则
    - 实现 apply_custom_rules 方法
    - _Requirements: 5.5_

  - [x] 9.7 编写 SemanticRefiner 属性测试
    - **Property 10: 语义提炼缓存命中**
    - **Validates: Requirements 5.6**

- [x] 10. 检查点 - 确保所有测试通过
  - 运行所有测试，确保 Save Strategy 和 Semantic Refiner 功能正常
  - 如有问题请咨询用户

- [x] 11. 实现 AI Friendly Exporter
  - [x] 11.1 实现 AIFriendlyExporter 核心类
    - 创建 `src/sync/pipeline/ai_exporter.py`
    - 实现 export 方法
    - _Requirements: 6.1_

  - [x] 11.2 实现多格式导出
    - 实现 JSON、CSV、JSONL、COCO、Pascal VOC 格式
    - _Requirements: 6.1_

  - [x] 11.3 实现数据分割
    - 实现 split_data 方法
    - 支持训练集/验证集/测试集分割
    - _Requirements: 6.3_

  - [x] 11.4 实现语义增强导出
    - 在导出数据中包含语义信息
    - _Requirements: 6.2_

  - [x] 11.5 实现增量导出
    - 实现 export_incremental 方法
    - _Requirements: 6.5_

  - [x] 11.6 实现脱敏导出
    - 集成 Desensitizer 进行数据脱敏
    - _Requirements: 6.6_

  - [x] 11.7 实现统计报告生成
    - 实现 generate_statistics_report 方法
    - _Requirements: 6.4_

  - [x] 11.8 编写 AIFriendlyExporter 属性测试
    - **Property 11: 导出格式正确性**
    - **Property 12: 数据分割比例准确性**
    - **Validates: Requirements 6.1, 6.3**

- [x] 12. 实现 Sync Scheduler
  - [x] 12.1 实现 SyncScheduler 核心类
    - 创建 `src/sync/pipeline/scheduler.py`
    - 实现 schedule、trigger_manual 方法
    - _Requirements: 7.1, 7.2_

  - [x] 12.2 实现状态管理
    - 实现 get_status、update_status 方法
    - _Requirements: 7.3_

  - [x] 12.3 实现失败告警
    - 实现 on_failure 方法
    - 集成通知服务
    - _Requirements: 7.4_

  - [x] 12.4 实现优先级管理
    - 实现 set_priority 方法
    - _Requirements: 7.5_

  - [x] 12.5 实现历史记录
    - 实现 get_history 方法
    - _Requirements: 7.6_

  - [x] 12.6 编写 SyncScheduler 属性测试
    - **Property 13: 调度任务状态追踪**
    - **Property 14: 同步历史完整性**
    - **Validates: Requirements 7.3, 7.6**

- [x] 13. 检查点 - 确保所有测试通过
  - 运行所有测试，确保 Exporter 和 Scheduler 功能正常
  - 如有问题请咨询用户

- [x] 14. 实现数据库模型
  - [x] 14.1 创建数据库模型
    - 创建 `src/sync/pipeline/models.py`
    - 实现 DataSource、SyncCheckpoint、SyncJob、SyncHistory、SemanticCache、ExportRecord 模型
    - _Requirements: 1.1, 2.3, 7.6_

  - [x] 14.2 创建数据库迁移
    - 使用 Alembic 创建迁移脚本
    - _Requirements: 1.1_

- [x] 15. 实现 API 路由
  - [x] 15.1 实现数据源管理 API
    - 创建 `src/api/sync_pipeline.py`
    - 实现 CRUD 端点
    - _Requirements: 8.1, 8.2_

  - [x] 15.2 实现数据读取 API
    - 实现 read_data、test_connection 端点
    - _Requirements: 1.4, 8.2_

  - [x] 15.3 实现数据拉取 API
    - 实现 pull_data、get_checkpoint 端点
    - _Requirements: 2.1, 8.2_

  - [x] 15.4 实现 Webhook 端点
    - 实现 receive_webhook 端点
    - _Requirements: 3.1, 8.2_

  - [x] 15.5 实现保存策略 API
    - 实现 set_save_strategy 端点
    - _Requirements: 4.1, 8.3_

  - [x] 15.6 实现语义提炼 API
    - 实现 refine_semantics 端点
    - _Requirements: 5.1_

  - [x] 15.7 实现导出 API
    - 实现 export_data、get_export_status、download_export 端点
    - _Requirements: 6.1, 8.6_

  - [x] 15.8 实现调度管理 API
    - 实现 create_schedule、list_schedules、trigger_schedule、get_schedule_history 端点
    - _Requirements: 7.1, 7.2, 8.4, 8.6_

- [x] 16. 实现前端配置界面
  - [x] 16.1 创建数据源配置组件
    - 创建 `frontend/src/pages/sync/DataSourceConfig.tsx`
    - 实现数据源列表和配置表单
    - _Requirements: 8.1, 8.2_

  - [x] 16.2 创建同步调度组件
    - 创建 `frontend/src/pages/sync/SyncScheduler.tsx`
    - 实现调度配置和手动触发
    - _Requirements: 8.4, 8.6_

  - [x] 16.3 创建同步历史组件
    - 创建 `frontend/src/pages/sync/SyncHistory.tsx`
    - 实现历史记录和统计展示
    - _Requirements: 8.5_

  - [x] 16.4 创建导出配置组件
    - 创建 `frontend/src/pages/sync/ExportConfig.tsx`
    - 实现导出配置和下载
    - _Requirements: 8.6_

- [x] 17. 集成测试
  - [x] 17.1 编写端到端集成测试
    - 测试完整的读取 → 保存 → 导出流程
    - 测试定时拉取调度
    - 测试 Webhook 接收流程
    - _Requirements: 1.1-8.6_

  - [x] 17.2 编写 API 集成测试
    - 测试所有 API 端点
    - _Requirements: 8.1-8.6_

- [x] 18. 最终检查点 - 确保所有测试通过
  - 运行完整测试套件
  - 验证所有功能正常
  - 如有问题请咨询用户

## Notes

- 所有测试任务都是必需的，不可跳过
- 每个属性测试必须使用 Hypothesis 库，最少 100 次迭代
- 检查点任务用于确保增量验证
- 属性测试验证设计文档中定义的正确性属性
