# 实现计划: 系统优化

## 概述

本实现计划将系统优化设计分解为可执行的编码任务。任务按模块组织，每个任务包含具体的实现步骤和验证标准。

## 任务列表

- [x] 1. 完成同步管理器数据库操作
  - [x] 1.1 实现 `_update_annotation_in_db` 方法
    - 在 `src/hybrid/sync_manager.py` 中添加数据库更新逻辑
    - 使用 SQLAlchemy ORM 更新 Annotation 记录
    - 处理更新失败的异常情况
    - _需求: 1.1_
  
  - [x] 1.2 实现 `_insert_annotation_to_db` 方法
    - 在 `src/hybrid/sync_manager.py` 中添加数据库插入逻辑
    - 检查记录是否已存在，避免重复插入
    - _需求: 1.2_
  
  - [x] 1.3 实现 `_batch_insert_annotations` 方法
    - 使用 SQLAlchemy bulk_insert_mappings 进行批量插入
    - 实现 10 条记录的阈值判断逻辑
    - _需求: 1.5_
  
  - [x] 1.4 实现 `_download_and_save_model` 方法
    - 从云端下载模型文件
    - 保存到配置的存储路径
    - 验证文件完整性
    - _需求: 1.3_
  
  - [x] 1.5 添加错误处理和日志记录
    - 捕获数据库操作异常
    - 记录错误但继续处理剩余项目
    - _需求: 1.4_
  
  - [x] 1.6 编写属性测试
    - **Property 1: 同步管理器数据库操作往返**
    - **Property 2: 同步管理器批量操作阈值**
    - **Property 3: 同步管理器错误恢复**
    - **验证: 需求 1.1, 1.2, 1.4, 1.5**

- [x] 2. 完成报告服务邮件发送
  - [x] 2.1 创建 EmailSender 类
    - 在 `src/monitoring/report_service.py` 中添加 EmailSender 类
    - 实现 SMTP 连接和发送逻辑
    - 支持 HTML 和纯文本格式
    - _需求: 2.1, 2.2_
  
  - [x] 2.2 实现重试逻辑
    - 添加指数退避重试机制 (1s, 2s, 4s)
    - 最多重试 3 次
    - _需求: 2.3_
  
  - [x] 2.3 实现并发发送
    - 使用 asyncio.gather 并发发送给多个收件人
    - 收集所有发送结果
    - _需求: 2.5_
  
  - [x] 2.4 添加发送日志记录
    - 记录每次发送尝试的详细信息
    - 包含收件人、状态、时间戳
    - _需求: 2.4_
  
  - [x] 2.5 编写单元测试
    - **Property 4: 报告服务邮件格式**
    - **Property 5: 报告服务发送日志**
    - **验证: 需求 2.2, 2.4**

- [x] 3. 检查点 - 确保所有测试通过
  - 运行 `pytest tests/unit/test_sync_manager.py tests/unit/test_report_service.py -v`
  - 如有问题请询问用户

- [x] 4. 完成同步管道 API 实现
  - [x] 4.1 创建 DataSourceService 类
    - 在 `src/api/sync_pipeline.py` 中添加服务类
    - 实现数据源的 CRUD 操作
    - _需求: 3.1, 3.2, 3.8_
  
  - [x] 4.2 实现凭据加密
    - 使用 AES-256 加密数据源密码
    - 存储加密后的凭据
    - _需求: 3.1_
  
  - [x] 4.3 实现连接测试
    - 尝试连接数据源
    - 返回连接延迟指标
    - _需求: 3.3_
  
  - [x] 4.4 实现检查点增量同步
    - 创建 CheckpointStore 类
    - 实现检查点的保存和读取
    - 在拉取时使用检查点过滤数据
    - _需求: 3.4_
  
  - [x] 4.5 实现 webhook 签名验证和幂等性
    - 验证 X-Signature 头
    - 使用 X-Idempotency-Key 处理重复请求
    - _需求: 3.5_
  
  - [x] 4.6 创建 SyncSchedulerService 类
    - 集成 APScheduler
    - 实现调度的 CRUD 操作
    - 实现手动触发功能
    - _需求: 3.6, 3.7_
  
  - [x] 4.7 编写属性测试
    - **Property 6: 同步管道 API 数据源 CRUD 往返**
    - **Property 7: 同步管道 API 凭据加密**
    - **Property 8: 同步管道 API 分页过滤**
    - **Property 9: 同步管道 API 签名验证和幂等性**
    - **Property 10: 同步管道 API 检查点增量同步**
    - **验证: 需求 3.1-3.8**

- [x] 5. 完成 Ragas API 存储实现
  - [x] 5.1 创建 EvaluationResultModel 数据库模型
    - 在 `src/models/` 中添加模型定义
    - 创建 Alembic 迁移脚本
    - _需求: 4.1_
  
  - [x] 5.2 创建 EvaluationResultRepository 类
    - 实现 save、get_by_id、list 方法
    - 支持分页和日期过滤
    - _需求: 4.1, 4.2, 4.3_
  
  - [x] 5.3 更新 API 端点
    - 修改 `/evaluate` 端点保存结果
    - 修改 `/evaluate/{evaluation_id}` 端点检索结果
    - _需求: 4.1, 4.2_
  
  - [x] 5.4 编写属性测试
    - **Property 11: Ragas API 评估结果往返**
    - **Property 12: Ragas API 分页日期过滤**
    - **验证: 需求 4.1, 4.2, 4.3**

- [x] 6. 检查点 - 确保所有测试通过
  - 运行 `pytest tests/unit/test_sync_pipeline.py tests/unit/test_ragas_api.py -v`
  - 如有问题请询问用户

- [x] 7. 完成业务逻辑服务数据库操作
  - [x] 7.1 创建业务逻辑数据库模型
    - 在 `src/models/` 中添加 BusinessRuleModel、BusinessPatternModel、BusinessInsightModel
    - 创建 Alembic 迁移脚本
    - _需求: 5.1-5.9_
  
  - [x] 7.2 创建 Repository 类
    - 实现 BusinessRuleRepository
    - 实现 BusinessPatternRepository
    - 实现 BusinessInsightRepository
    - _需求: 5.1-5.9_
  
  - [x] 7.3 更新 BusinessLogicService
    - 替换示例数据为数据库查询
    - 实现所有 CRUD 操作
    - _需求: 5.1-5.9_
  
  - [x] 7.4 编写属性测试
    - **Property 13: 业务逻辑服务 CRUD 往返**
    - **验证: 需求 5.1-5.9**

- [x] 8. 完成 SLA 监控通知集成
  - [x] 8.1 创建 NotificationService 抽象基类
    - 定义通知服务接口
    - _需求: 6.1-6.4_
  
  - [x] 8.2 实现 EmailNotificationService
    - 集成 SMTP 邮件发送
    - 实现重试逻辑
    - _需求: 6.1_
  
  - [x] 8.3 实现 WeChatWorkNotificationService
    - 集成企业微信 API
    - 支持 webhook 和应用消息
    - _需求: 6.2_
  
  - [x] 8.4 创建 NotificationManager
    - 管理多个通知服务
    - 实现优先级渠道配置
    - _需求: 6.3_
  
  - [x] 8.5 更新 SLA_Monitor
    - 替换占位符实现
    - 集成 NotificationManager
    - _需求: 6.1-6.4_
  
  - [x] 8.6 编写属性测试
    - **Property 14: SLA 监控优先级渠道配置**
    - **验证: 需求 6.3**

- [x] 9. 完成合规报告调度器集成
  - [x] 9.1 创建 ComplianceScheduler 类
    - 集成 APScheduler
    - 实现 cron 表达式解析
    - _需求: 7.1, 7.2_
  
  - [x] 9.2 更新 Compliance_Reporter
    - 替换 TODO 占位符
    - 集成 ComplianceScheduler
    - _需求: 7.1, 7.3_
  
  - [x] 9.3 编写属性测试
    - **Property 15: 合规报告 cron 表达式解析**
    - **验证: 需求 7.2**

- [x] 10. 检查点 - 确保所有测试通过
  - 运行 `pytest tests/unit/test_business_logic.py tests/unit/test_sla_monitor.py tests/unit/test_compliance_reporter.py -v`
  - 如有问题请询问用户

- [x] 11. 实现 Redis 缓存策略
  - [x] 11.1 创建 CacheStrategy 类
    - 在 `src/utils/cache_strategy.py` 中创建新文件
    - 实现 cache-aside 模式
    - 配置不同数据类型的 TTL
    - _需求: 8.1, 8.2_
  
  - [x] 11.2 实现缓存失效
    - 在数据更新时自动失效相关缓存
    - 支持模式匹配批量失效
    - _需求: 8.3_
  
  - [x] 11.3 实现缓存预热
    - 启动时加载关键数据到缓存
    - _需求: 8.4_
  
  - [x] 11.4 实现命中率监控
    - 跟踪缓存命中和未命中
    - 低于 80% 时记录警告
    - _需求: 8.5_
  
  - [x] 11.5 编写属性测试
    - **Property 16: 缓存一致性**
    - **Property 17: 缓存命中率监控**
    - **验证: 需求 8.1, 8.3, 8.5**

- [x] 12. 实现数据库查询优化
  - [x] 12.1 创建索引迁移脚本
    - 创建 Alembic 迁移添加优化索引
    - _需求: 9.1_
  
  - [x] 12.2 创建 BatchOperations 工具类
    - 实现 bulk_insert 和 bulk_update
    - _需求: 9.2_
  
  - [x] 12.3 实现分页查询工具
    - 创建通用分页查询函数
    - _需求: 9.3_
  
  - [x] 12.4 实现慢查询监控
    - 创建 QueryMonitor 类
    - 记录超过 1 秒的查询
    - _需求: 9.5_
  
  - [x] 12.5 编写属性测试
    - **Property 18: 批量数据库操作**
    - **Property 19: 分页查询**
    - **Property 20: 慢查询监控**
    - **验证: 需求 9.2, 9.3, 9.5**

- [x] 13. 检查点 - 确保所有测试通过
  - 运行 `pytest tests/unit/test_cache_strategy.py tests/unit/test_batch_operations.py -v`
  - 如有问题请询问用户

- [x] 14. 增强错误处理和日志记录
  - [x] 14.1 创建标准错误响应模型
    - 定义 ErrorResponse 模型
    - 创建错误码枚举
    - _需求: 10.5_
  
  - [x] 14.2 创建全局异常处理器
    - 捕获未处理异常
    - 返回标准化错误响应
    - _需求: 10.5_
  
  - [x] 14.3 增强日志配置
    - 配置结构化日志格式
    - 添加关联 ID 中间件
    - _需求: 10.1, 10.2_
  
  - [x] 14.4 增强错误日志记录
    - 记录完整堆栈跟踪
    - 包含请求上下文
    - _需求: 10.3, 10.4_
  
  - [x] 14.5 编写属性测试
    - **Property 21: 结构化日志格式**
    - **Property 22: API 错误响应标准化**
    - **验证: 需求 10.1, 10.2, 10.5**

- [x] 15. 确保国际化覆盖
  - [x] 15.1 审计新增代码的 i18n 覆盖
    - 检查所有新增的用户面向消息
    - 确保使用 i18n 键
    - _需求: 12.2_
  
  - [x] 15.2 添加翻译键
    - 更新 `frontend/src/locales/zh/` 翻译文件
    - 更新 `frontend/src/locales/en/` 翻译文件
    - _需求: 12.3_
  
  - [x] 15.3 验证默认语言
    - 确保未设置语言时默认中文
    - _需求: 12.4_

- [x] 16. 增强监控和告警
  - [x] 16.1 添加 Prometheus 指标
    - 为关键操作添加计数器和直方图
    - _需求: 13.1_
  
  - [x] 16.2 实现可配置告警阈值
    - 创建告警配置模型
    - 支持动态更新阈值
    - _需求: 13.2_
  
  - [x] 16.3 增强健康检查
    - 为所有服务添加健康检查端点
    - _需求: 13.3_
  
  - [x] 16.4 实现服务不健康告警
    - 检测服务状态变化
    - 触发告警通知
    - _需求: 13.4_
  
  - [x] 16.5 编写属性测试
    - **Property 13.4: 服务不健康告警**
    - **验证: 需求 13.4**

- [x] 17. 加强安全控制
  - [x] 17.1 实现 AES-256 加密工具
    - 创建加密/解密函数
    - 用于敏感数据存储
    - _需求: 14.1_
  
  - [x] 17.2 增强 API 输入验证
    - 确保所有端点使用 Pydantic 验证
    - 添加自定义验证器
    - _需求: 14.2_
  
  - [x] 17.3 实现速率限制
    - 使用 slowapi 或自定义实现
    - 配置不同端点的限制
    - _需求: 14.3_
  
  - [x] 17.4 增强审计日志
    - 记录所有安全相关事件
    - 包含认证失败和源 IP
    - _需求: 14.4, 14.5_
  
  - [x] 17.5 编写属性测试
    - **Property 23: AES-256 加密往返**
    - **Property 24: API 输入验证**
    - **Property 25: 速率限制**
    - **Property 26: 审计日志完整性**
    - **验证: 需求 14.1-14.5**

- [x] 18. 实现企业本体模型
  - [x] 18.1 创建本体模型模块
    - 创建 `src/ontology/` 目录结构
    - 实现 `OntologyEntity` 和 `OntologyRelation` 类
    - 扩展现有知识图谱 Entity/Relation 模型
    - _设计: 本体模型设计_
  
  - [x] 18.2 实现中国企业特色实体类型
    - 添加 `ChineseEntityType` 枚举
    - 包含部门、业务单元、法规、合同、审批、印章、发票、资质等类型
    - _设计: 本体模型设计_
  
  - [x] 18.3 实现中国企业特色关系类型
    - 添加 `ChineseRelationType` 枚举
    - 包含汇报、审批、用印、合规、监管、授权等关系
    - _设计: 本体模型设计_
  
  - [x] 18.4 实现 EnterpriseOntologyManager
    - 集成知识图谱数据库 (Neo4j)
    - 集成数据血缘追踪器 (EnhancedLineageTracker)
    - 实现实体和关系的 CRUD 操作
    - _设计: 本体模型设计_
  
  - [x] 18.5 实现合规验证功能
    - 数据分类检查
    - 跨境传输检查
    - 个人信息保护检查
    - _设计: 本体模型设计_
  
  - [x] 18.6 实现 AI 数据转换器
    - 创建 `AIDataConverter` 类
    - 支持 Alpaca、ShareGPT、OpenAI、LLaMA-Factory 格式
    - 包含数据血缘元数据
    - _设计: AI 友好型数据转换_
  
  - [x] 18.7 编写本体模型单元测试
    - 测试实体创建和转换
    - 测试关系创建和验证
    - 测试合规检查逻辑
    - 测试 AI 数据格式转换

- [x] 19. 最终检查点 - 确保所有测试通过
  - 运行完整测试套件 `pytest tests/ -v --cov=src`
  - 验证代码覆盖率 >= 80%
  - 如有问题请询问用户

## 注意事项

- 所有任务都是必需的，包括测试任务
- 每个任务引用具体的需求以确保可追溯性
- 检查点任务确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证具体示例和边界情况
