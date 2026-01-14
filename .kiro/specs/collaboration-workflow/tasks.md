# Implementation Plan: Collaboration Workflow (协作与审核流程)

## Overview

本实现计划将 Collaboration Workflow 模块分解为可执行的编码任务，扩展现有 `src/quality/` 和 `src/label_studio/` 模块，实现完整的协作与审核流程，包括众包标注和第三方平台集成。

## Tasks

- [x] 1. 设置项目结构和核心接口
  - 创建 `src/collaboration/` 目录结构
  - 定义核心接口和类型
  - 设置测试框架配置
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_

- [x] 2. 实现数据库模型
  - [x] 2.1 创建任务分配和协作模型
    - 创建 `src/collaboration/models.py`
    - 实现 TaskAssignment、AnnotationVersion 模型
    - _Requirements: 1.1, 2.1_

  - [x] 2.2 创建审核和冲突模型
    - 实现 ReviewTask、ReviewHistory、Conflict、ConflictResolution 模型
    - _Requirements: 3.1, 4.1_

  - [x] 2.3 创建众包相关模型
    - 实现 CrowdsourceTask、CrowdsourceAnnotator、CrowdsourceSubmission 模型
    - _Requirements: 8.1, 9.1_

  - [x] 2.4 创建第三方平台模型
    - 实现 ThirdPartyPlatform、PlatformConfig 模型
    - _Requirements: 13.1_

  - [x] 2.5 创建数据库迁移
    - 使用 Alembic 创建迁移脚本
    - _Requirements: 1.1_

- [x] 3. 实现 Task Dispatcher
  - [x] 3.1 实现 TaskDispatcher 核心类
    - 创建 `src/collaboration/task_dispatcher.py`
    - 实现 assign_task、_auto_assign、_manual_assign 方法
    - _Requirements: 1.1, 1.2_

  - [x] 3.2 实现技能匹配
    - 实现 _get_skill_matched_annotators 方法
    - _Requirements: 1.1_

  - [x] 3.3 实现负载均衡
    - 实现 _sort_by_workload 方法
    - _Requirements: 1.3_

  - [x] 3.4 实现优先级和截止时间
    - 实现 set_priority、set_deadline 方法
    - _Requirements: 1.4, 1.5_

  - [x] 3.5 编写 TaskDispatcher 属性测试
    - **Property 1: 技能匹配任务分配**
    - **Property 2: 工作负载均衡**
    - **Validates: Requirements 1.1, 1.3**

- [x] 4. 实现 Collaboration Engine
  - [x] 4.1 实现 CollaborationEngine 核心类
    - 创建 `src/collaboration/collaboration_engine.py`
    - 实现任务锁机制
    - _Requirements: 2.3_

  - [x] 4.2 实现进度同步
    - 实现 sync_progress 方法
    - 集成 WebSocket
    - _Requirements: 2.2_

  - [x] 4.3 实现版本管理
    - 实现 save_annotation_version、get_annotation_versions 方法
    - _Requirements: 2.4_

  - [x] 4.4 编写 CollaborationEngine 属性测试
    - **Property 3: 任务重复标注防止**
    - **Property 4: 标注版本保留**
    - **Validates: Requirements 2.3, 2.4**

- [x] 5. 检查点 - 确保所有测试通过
  - 运行所有测试，确保 Task Dispatcher 和 Collaboration Engine 功能正常
  - 如有问题请咨询用户

- [x] 6. 实现 Review Flow Manager
  - [x] 6.1 实现 ReviewFlowManager 核心类
    - 创建 `src/collaboration/review_flow_manager.py`
    - 实现 configure_flow、submit_for_review 方法
    - _Requirements: 3.1, 3.3_

  - [x] 6.2 实现审核操作
    - 实现 approve、reject、batch_approve 方法
    - _Requirements: 3.4, 3.5_

  - [x] 6.3 实现审核历史
    - 实现 get_review_history、_record_history 方法
    - _Requirements: 3.6_

  - [x] 6.4 编写 ReviewFlowManager 属性测试
    - **Property 5: 审核流程正确性**
    - **Property 6: 审核历史完整性**
    - **Validates: Requirements 3.3, 3.5, 3.6**

- [x] 7. 实现 Conflict Resolver
  - [x] 7.1 实现 ConflictResolver 核心类
    - 创建 `src/collaboration/conflict_resolver.py`
    - 实现 detect_conflicts 方法
    - _Requirements: 4.1_

  - [x] 7.2 实现冲突解决
    - 实现 resolve_by_voting、resolve_by_expert 方法
    - _Requirements: 4.2, 4.3_

  - [x] 7.3 实现冲突报告
    - 实现 generate_conflict_report 方法
    - _Requirements: 4.6_

  - [x] 7.4 编写 ConflictResolver 属性测试
    - **Property 7: 冲突检测和解决**
    - **Validates: Requirements 4.1, 4.2**

- [x] 8. 检查点 - 确保所有测试通过
  - 运行所有测试，确保 Review Flow 和 Conflict Resolver 功能正常
  - 如有问题请咨询用户

- [x] 9. 实现 Quality Controller
  - [x] 9.1 实现 QualityController 核心类
    - 创建 `src/collaboration/quality_controller.py`
    - 实现 calculate_accuracy 方法
    - _Requirements: 5.1_

  - [x] 9.2 实现抽样检查
    - 实现 sample_for_review 方法
    - _Requirements: 5.2_

  - [x] 9.3 实现黄金标准测试
    - 实现 run_gold_standard_test 方法
    - _Requirements: 5.3_

  - [x] 9.4 实现质量预警
    - 实现 check_quality_threshold 方法
    - _Requirements: 5.4_

  - [x] 9.5 实现质量排名和报告
    - 实现 get_quality_ranking、generate_quality_report 方法
    - _Requirements: 5.5, 5.6_

  - [x] 9.6 编写 QualityController 属性测试
    - **Property 8: 质量评分准确性**
    - **Property 9: 质量阈值预警**
    - **Validates: Requirements 5.1, 5.4, 5.6**

- [x] 10. 实现 Notification Service
  - [x] 10.1 实现 NotificationService 核心类
    - 创建 `src/collaboration/notification_service.py`
    - 实现多渠道通知（站内、邮件、Webhook）
    - _Requirements: 6.1_

  - [x] 10.2 实现通知偏好
    - 实现通知偏好配置
    - _Requirements: 6.2_

  - [x] 10.3 实现各类通知
    - 实现任务分配、审核结果、截止提醒通知
    - _Requirements: 6.3, 6.4, 6.5_

- [x] 11. 检查点 - 确保所有测试通过
  - 运行所有测试，确保 Quality Controller 和 Notification Service 功能正常
  - 如有问题请咨询用户

- [x] 12. 实现 Crowdsource Manager
  - [x] 12.1 实现 CrowdsourceManager 核心类
    - 创建 `src/collaboration/crowdsource_manager.py`
    - 实现 create_crowdsource_task 方法
    - _Requirements: 8.1_

  - [x] 12.2 实现敏感数据过滤
    - 实现 SensitivityFilter 类
    - _Requirements: 8.2, 8.3_

  - [x] 12.3 实现任务领取和提交
    - 实现 claim_task、submit_annotation 方法
    - _Requirements: 8.1_

  - [x] 12.4 编写 CrowdsourceManager 属性测试
    - **Property 10: 敏感数据过滤**
    - **Validates: Requirements 8.2, 8.3**

- [x] 13. 实现 Crowdsource Annotator Manager
  - [x] 13.1 实现 CrowdsourceAnnotatorManager 核心类
    - 创建 `src/collaboration/crowdsource_annotator_manager.py`
    - 实现 register 方法
    - _Requirements: 9.1_

  - [x] 13.2 实现实名认证
    - 实现 verify_identity 方法
    - 集成身份验证服务
    - _Requirements: 9.2_

  - [x] 13.3 实现能力测试
    - 实现 conduct_ability_test 方法
    - _Requirements: 9.3_

  - [x] 13.4 实现星级评定
    - 实现 update_star_rating、_calculate_initial_star 方法
    - _Requirements: 9.4_

  - [x] 13.5 实现能力标签和状态管理
    - 实现 add_ability_tags、set_status 方法
    - _Requirements: 9.5, 9.6_

  - [x] 13.6 实现定期复评
    - 实现 conduct_periodic_review 方法
    - _Requirements: 10.6_

- [x] 14. 实现 Crowdsource Billing
  - [x] 14.1 实现 CrowdsourceBilling 核心类
    - 创建 `src/collaboration/crowdsource_billing.py`
    - 实现 configure_pricing 方法
    - _Requirements: 11.1_

  - [x] 14.2 实现收益计算
    - 实现 calculate_earnings 方法
    - 包含质量系数和星级系数
    - _Requirements: 11.2, 11.3_

  - [x] 14.3 实现结算报表和发票
    - 实现 generate_settlement_report、generate_invoice 方法
    - _Requirements: 11.5_

  - [x] 14.4 实现提现功能
    - 实现 process_withdrawal 方法
    - 支持银行转账/支付宝/微信
    - _Requirements: 11.6_

  - [x] 14.5 编写 CrowdsourceBilling 属性测试
    - **Property 11: 众包计费准确性**
    - **Validates: Requirements 11.3, 11.4**

- [x] 15. 检查点 - 确保所有测试通过
  - 运行所有测试，确保众包相关功能正常
  - 如有问题请咨询用户

- [x] 16. 实现 Third Party Platform Adapter
  - [x] 16.1 实现 ThirdPartyPlatformAdapter 核心类
    - 创建 `src/collaboration/third_party_platform_adapter.py`
    - 实现 register_platform、sync_task 方法
    - _Requirements: 13.1_

  - [x] 16.2 实现 MTurk 连接器
    - 实现 MTurkConnector 类
    - _Requirements: 13.1_

  - [x] 16.3 实现 Scale AI 连接器
    - 实现 ScaleAIConnector 类
    - _Requirements: 13.2_

  - [x] 16.4 实现自定义 REST 连接器
    - 实现 CustomRESTConnector 类
    - _Requirements: 13.3_

  - [x] 16.5 实现结果回收
    - 实现 fetch_results 方法
    - _Requirements: 13.5_

- [x] 17. 实现 API 路由
  - [x] 17.1 实现任务分配和协作 API
    - 创建 `src/api/collaboration.py`
    - 实现任务分配、锁定、版本查询端点
    - _Requirements: 1.1, 2.1_

  - [x] 17.2 实现审核和冲突 API
    - 实现审核提交、通过、驳回、冲突解决端点
    - _Requirements: 3.1, 4.1_

  - [x] 17.3 实现质量控制 API
    - 实现准确率查询、排名、黄金测试端点
    - _Requirements: 5.1_

  - [x] 17.4 实现众包 API
    - 实现众包任务、标注员、计费端点
    - _Requirements: 8.1, 9.1, 11.1_

  - [x] 17.5 实现第三方平台 API
    - 实现平台配置、同步、状态查询端点
    - _Requirements: 13.1_

- [x] 18. 实现前端界面
  - [x] 18.1 创建协作界面
    - 创建 `frontend/src/pages/Collaboration/index.tsx`
    - 实现任务列表、团队状态、实时聊天
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 18.2 创建审核界面
    - 创建审核队列、快捷操作
    - _Requirements: 7.4, 7.5_

  - [x] 18.3 创建质量仪表盘
    - 实现质量指标、趋势图表
    - _Requirements: 7.6_

  - [x] 18.4 创建众包门户
    - 创建 `frontend/src/pages/Crowdsource/index.tsx`
    - 实现任务领取、收益统计、星级显示
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 18.5 创建众包管理界面
    - 实现标注员管理、任务管理
    - _Requirements: 12.6_

  - [x] 18.6 创建第三方平台配置界面
    - 实现平台连接配置
    - _Requirements: 13.4_

- [x] 19. 集成测试
  - [x] 19.1 编写端到端集成测试
    - 测试完整的任务分配 → 标注 → 审核流程
    - 测试众包标注完整流程
    - _Requirements: 1.1-13.6_

  - [x] 19.2 编写 API 集成测试
    - 测试所有 API 端点
    - _Requirements: 1.1-13.6_

  - [x] 19.3 编写前端 E2E 测试
    - 测试协作界面功能
    - 测试众包门户功能
    - _Requirements: 7.1-12.6_

- [x] 20. 最终检查点 - 确保所有测试通过
  - 运行完整测试套件
  - 验证所有功能正常
  - 如有问题请咨询用户

## Notes

- 所有测试任务都是必需的，不可跳过
- 每个属性测试必须使用 Hypothesis 库，最少 100 次迭代
- 检查点任务用于确保增量验证
- 属性测试验证设计文档中定义的正确性属性
- 第三方平台集成需要配置 API 密钥
