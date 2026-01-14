# Requirements Document: Collaboration Workflow (协作与审核流程)

## Introduction

本模块扩展现有 `src/quality/` 和 `src/label_studio/`，实现完整的协作与审核流程，包括任务分配、多人协作、审核流程、冲突解决和质量控制。

## Glossary

- **Task_Dispatcher**: 任务分配器，智能分配标注任务给合适的标注员
- **Collaboration_Engine**: 协作引擎，支持多人同时协作标注
- **Review_Flow_Manager**: 审核流管理器，管理多级审核流程
- **Conflict_Resolver**: 冲突解决器，处理标注冲突和分歧
- **Quality_Controller**: 质量控制器，监控和保证标注质量
- **Notification_Service**: 通知服务，发送任务和审核通知

## Requirements

### Requirement 1: 智能任务分配

**User Story:** 作为项目经理，我希望系统能够智能分配任务，以便提高标注效率和质量。

#### Acceptance Criteria

1. THE Task_Dispatcher SHALL 根据标注员技能和历史表现分配任务
2. THE Task_Dispatcher SHALL 支持手动分配和自动分配两种模式
3. WHEN 自动分配 THEN THE Task_Dispatcher SHALL 考虑工作负载均衡
4. THE Task_Dispatcher SHALL 支持任务优先级设置
5. THE Task_Dispatcher SHALL 支持任务截止时间设置
6. WHEN 任务分配 THEN THE Task_Dispatcher SHALL 发送通知给标注员

### Requirement 2: 多人协作

**User Story:** 作为标注团队，我希望能够多人同时协作标注，以便加快项目进度。

#### Acceptance Criteria

1. THE Collaboration_Engine SHALL 支持多人同时标注同一项目
2. THE Collaboration_Engine SHALL 实时同步标注进度
3. THE Collaboration_Engine SHALL 防止同一任务被重复标注
4. WHEN 多人标注同一数据 THEN THE Collaboration_Engine SHALL 记录所有标注版本
5. THE Collaboration_Engine SHALL 支持标注员之间的实时通信
6. THE Collaboration_Engine SHALL 显示团队成员的在线状态

### Requirement 3: 多级审核流程

**User Story:** 作为质量管理员，我希望配置多级审核流程，以便确保标注质量。

#### Acceptance Criteria

1. THE Review_Flow_Manager SHALL 支持配置多级审核（一审、二审、终审）
2. THE Review_Flow_Manager SHALL 支持配置审核通过率阈值
3. WHEN 标注完成 THEN THE Review_Flow_Manager SHALL 自动进入审核队列
4. THE Review_Flow_Manager SHALL 支持审核员批量审核
5. WHEN 审核驳回 THEN THE Review_Flow_Manager SHALL 退回给原标注员修改
6. THE Review_Flow_Manager SHALL 记录完整的审核历史

### Requirement 4: 冲突解决

**User Story:** 作为审核员，我希望系统能够帮助解决标注冲突，以便提高一致性。

#### Acceptance Criteria

1. THE Conflict_Resolver SHALL 自动检测标注冲突
2. THE Conflict_Resolver SHALL 支持投票机制解决冲突
3. THE Conflict_Resolver SHALL 支持专家仲裁解决冲突
4. WHEN 检测到冲突 THEN THE Conflict_Resolver SHALL 通知相关人员
5. THE Conflict_Resolver SHALL 记录冲突解决历史
6. THE Conflict_Resolver SHALL 生成冲突分析报告

### Requirement 5: 质量控制

**User Story:** 作为质量管理员，我希望实时监控标注质量，以便及时发现和解决问题。

#### Acceptance Criteria

1. THE Quality_Controller SHALL 实时计算标注员的准确率
2. THE Quality_Controller SHALL 支持抽样检查机制
3. THE Quality_Controller SHALL 支持黄金标准测试
4. WHEN 质量低于阈值 THEN THE Quality_Controller SHALL 发送预警
5. THE Quality_Controller SHALL 生成质量趋势报告
6. THE Quality_Controller SHALL 支持质量评分和排名

### Requirement 6: 通知和提醒

**User Story:** 作为标注员，我希望及时收到任务和审核通知，以便高效完成工作。

#### Acceptance Criteria

1. THE Notification_Service SHALL 支持多渠道通知（站内、邮件、Webhook）
2. THE Notification_Service SHALL 支持配置通知偏好
3. WHEN 任务分配 THEN THE Notification_Service SHALL 发送任务通知
4. WHEN 审核完成 THEN THE Notification_Service SHALL 发送审核结果通知
5. THE Notification_Service SHALL 支持任务截止提醒
6. THE Notification_Service SHALL 支持批量通知

### Requirement 7: 前端协作界面

**User Story:** 作为标注员，我希望通过直观的界面进行协作，以便高效完成标注工作。

#### Acceptance Criteria

1. THE Collaboration_UI SHALL 显示任务列表和进度
2. THE Collaboration_UI SHALL 显示团队成员状态和工作量
3. THE Collaboration_UI SHALL 支持实时聊天和讨论
4. THE Review_UI SHALL 显示待审核任务队列
5. THE Review_UI SHALL 支持快捷审核操作
6. THE Quality_Dashboard SHALL 显示质量指标和趋势图表

### Requirement 8: 众包标注

**User Story:** 作为项目经理，我希望将非敏感数据开放给社会标注人士，以便扩大标注能力并降低成本。

#### Acceptance Criteria

1. THE Crowdsource_Manager SHALL 支持创建众包标注任务
2. THE Crowdsource_Manager SHALL 支持配置数据敏感级别过滤
3. WHEN 创建众包任务 THEN THE Crowdsource_Manager SHALL 自动过滤敏感数据
4. THE Crowdsource_Manager SHALL 支持对接第三方标注平台（如 Amazon MTurk、Scale AI）
5. THE Crowdsource_Manager SHALL 支持在前端配置第三方平台连接参数
6. THE Crowdsource_Manager SHALL 支持统一管理内部和第三方平台的众包任务

### Requirement 9: 众包标注员管理

**User Story:** 作为平台管理员，我希望完整管理众包标注员的生命周期，以便确保标注质量和合规性。

#### Acceptance Criteria

1. THE Crowdsource_Annotator_Manager SHALL 支持标注员注册和账号创建
2. THE Crowdsource_Annotator_Manager SHALL 支持实名认证（身份证/护照验证）
3. THE Crowdsource_Annotator_Manager SHALL 支持资质审核和能力测试
4. THE Crowdsource_Annotator_Manager SHALL 支持标注员星级评定（1-5星）
5. THE Crowdsource_Annotator_Manager SHALL 支持能力标签管理（如 NLP、图像、音频）
6. THE Crowdsource_Annotator_Manager SHALL 支持标注员状态管理（活跃/暂停/禁用）

### Requirement 10: 众包质量保障

**User Story:** 作为质量管理员，我希望确保众包标注的质量，以便保证数据可用性。

#### Acceptance Criteria

1. THE Crowdsource_Quality_Controller SHALL 支持众包标注员能力测试
2. THE Crowdsource_Quality_Controller SHALL 支持多人标注同一数据取共识
3. THE Crowdsource_Quality_Controller SHALL 支持黄金标准数据混入检测
4. WHEN 众包标注员质量低于阈值 THEN THE Crowdsource_Quality_Controller SHALL 暂停其标注权限
5. THE Crowdsource_Quality_Controller SHALL 生成众包质量报告
6. THE Crowdsource_Quality_Controller SHALL 支持众包标注员评级

### Requirement 10: 众包质量保障

**User Story:** 作为质量管理员，我希望确保众包标注的质量，以便保证数据可用性。

#### Acceptance Criteria

1. THE Crowdsource_Quality_Controller SHALL 支持众包标注员入职能力测试
2. THE Crowdsource_Quality_Controller SHALL 支持多人标注同一数据取共识
3. THE Crowdsource_Quality_Controller SHALL 支持黄金标准数据混入检测
4. WHEN 众包标注员质量低于阈值 THEN THE Crowdsource_Quality_Controller SHALL 降低其星级
5. THE Crowdsource_Quality_Controller SHALL 生成众包质量报告
6. THE Crowdsource_Quality_Controller SHALL 支持定期能力复评

### Requirement 11: 众包计费管理

**User Story:** 作为财务管理员，我希望管理众包标注的计费和结算，以便准确支付标注费用。

#### Acceptance Criteria

1. THE Crowdsource_Billing SHALL 支持配置不同任务类型的单价
2. THE Crowdsource_Billing SHALL 实时统计众包标注员的工作量
3. THE Crowdsource_Billing SHALL 支持质量系数调整计费
4. WHEN 标注通过审核 THEN THE Crowdsource_Billing SHALL 计入有效工作量
5. THE Crowdsource_Billing SHALL 生成结算报表
6. THE Crowdsource_Billing SHALL 支持多种结算周期（日/周/月）

### Requirement 11: 众包计费管理

**User Story:** 作为财务管理员，我希望管理众包标注的计费和结算，以便准确支付标注费用。

#### Acceptance Criteria

1. THE Crowdsource_Billing SHALL 支持配置不同任务类型的单价
2. THE Crowdsource_Billing SHALL 实时统计众包标注员的工作量
3. THE Crowdsource_Billing SHALL 支持质量系数和星级调整计费
4. WHEN 标注通过审核 THEN THE Crowdsource_Billing SHALL 计入有效工作量
5. THE Crowdsource_Billing SHALL 生成结算报表和发票
6. THE Crowdsource_Billing SHALL 支持多种结算方式（银行转账/支付宝/微信）

### Requirement 12: 众包前端界面

**User Story:** 作为众包标注员，我希望通过简洁的界面完成标注任务，以便高效赚取报酬。

#### Acceptance Criteria

1. THE Crowdsource_Portal SHALL 显示可领取的标注任务
2. THE Crowdsource_Portal SHALL 显示个人工作量、收益和星级
3. THE Crowdsource_Portal SHALL 显示个人能力标签和排名
4. THE Crowdsource_Portal SHALL 支持任务领取和提交
5. THE Crowdsource_Portal SHALL 支持查看结算明细和提现
6. THE Crowdsource_Admin_UI SHALL 显示第三方平台配置界面

### Requirement 13: 第三方标注平台集成

**User Story:** 作为项目经理，我希望对接第三方专业标注平台，以便利用外部标注资源。

#### Acceptance Criteria

1. THE Third_Party_Platform_Adapter SHALL 支持对接 Amazon MTurk
2. THE Third_Party_Platform_Adapter SHALL 支持对接 Scale AI
3. THE Third_Party_Platform_Adapter SHALL 支持对接其他自定义平台（通过 REST API）
4. THE Third_Party_Platform_Config_UI SHALL 支持配置平台连接参数（API Key、Endpoint）
5. THE Third_Party_Platform_Adapter SHALL 支持任务同步和结果回收
6. THE Third_Party_Platform_Adapter SHALL 支持统一的质量评估和计费
