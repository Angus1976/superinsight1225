# SuperInsight 企业级管理前端 - 需求文档

## 介绍

SuperInsight 企业级管理前端是为 AI 数据治理与标注平台设计的现代化 Web 管理界面，采用 React 18 + Ant Design Pro 技术栈，提供专业、简洁、安全、易用的企业级用户体验。前端通过 iframe 嵌入 Label Studio 标注界面，实现标注与管理的无缝集成。

## 术语表

- **Management_Frontend**: 企业级管理前端系统
- **Label_Studio_Iframe**: 嵌入的 Label Studio 标注界面
- **Tenant_System**: 多租户隔离系统
- **Dashboard**: 管理后台仪表盘
- **Task_Manager**: 标注任务管理模块
- **Billing_Module**: 账单与结算模块
- **Augmentation_Module**: 数据增强管理模块
- **Security_Module**: 安全审计模块
- **Admin_Console**: 系统管理控制台

## 需求

### 需求 1: 用户认证与多租户支持

**用户故事:** 作为企业用户，我希望能够安全登录系统并切换不同的租户环境，以便管理不同项目的数据标注工作。

#### 验收标准

1. THE Management_Frontend SHALL 提供登录和注册页面
2. WHEN 用户登录时，THE Management_Frontend SHALL 支持租户选择下拉菜单
3. THE Management_Frontend SHALL 使用 JWT token 进行身份验证
4. THE Management_Frontend SHALL 支持租户间切换而无需重新登录
5. WHEN 用户忘记密码时，THE Management_Frontend SHALL 提供密码重置功能

### 需求 2: 管理后台仪表盘

**用户故事:** 作为项目管理员，我希望能够在仪表盘中快速了解项目状态和关键指标，以便做出及时的管理决策。

#### 验收标准

1. THE Dashboard SHALL 显示活跃任务数、今日标注量、语料总数、账单总额等关键指标卡片
2. THE Dashboard SHALL 提供标注趋势折线图和质量分布饼图
3. THE Dashboard SHALL 提供任务管理、账单、数据增强等功能的快捷入口
4. THE Dashboard SHALL 支持实时数据更新
5. THE Dashboard SHALL 支持深色/浅色主题切换

### 需求 3: 标注任务管理

**用户故事:** 作为标注管理员，我希望能够创建、分配和跟踪标注任务，以便高效管理标注工作流程。

#### 验收标准

1. THE Task_Manager SHALL 显示任务列表（ID、名称、状态、负责人、进度、工时）
2. THE Task_Manager SHALL 支持创建新任务（名称、描述、数据源、标注类型、分配人员）
3. WHEN 用户点击任务详情时，THE Task_Manager SHALL 通过 iframe 嵌入 Label Studio 标注界面
4. THE Task_Manager SHALL 支持任务分配给业务专家、技术专家或外包人员
5. THE Task_Manager SHALL 提供实时进度跟踪和工时统计

### 需求 4: 账单与结算管理

**用户故事:** 作为财务管理员，我希望能够查看和管理标注工作的账单信息，以便进行准确的成本核算和结算。

#### 验收标准

1. THE Billing_Module SHALL 显示月度账单列表和详情（工时/条数/金额）
2. THE Billing_Module SHALL 支持账单数据导出为 Excel 格式
3. THE Billing_Module SHALL 提供工时排行榜和奖励发放功能
4. THE Billing_Module SHALL 支持多种计费模式（按时、按量、包年）
5. THE Billing_Module SHALL 提供成本分析和趋势图表

### 需求 5: 数据增强管理

**用户故事:** 作为数据工程师，我希望能够管理优质样本和数据增强策略，以便提高标注数据的质量和覆盖率。

#### 验收标准

1. THE Augmentation_Module SHALL 支持优质样本上传（CSV/JSON 格式）
2. THE Augmentation_Module SHALL 提供自动填充和数据放大功能
3. THE Augmentation_Module SHALL 显示数据占比统计图表（饼图/柱状图）
4. THE Augmentation_Module SHALL 提供优质样本与原始数据的对比预览
5. THE Augmentation_Module SHALL 支持批量数据增强操作

### 需求 6: 质量管理与规则配置

**用户故事:** 作为质量管理员，我希望能够配置质量规则和查看质量报表，以便确保标注数据的质量标准。

#### 验收标准

1. THE Management_Frontend SHALL 提供质量规则模板列表和新建/编辑功能
2. THE Management_Frontend SHALL 显示质量报表（问题分布、修复进度、考核分数）
3. THE Management_Frontend SHALL 支持工单创建和派发管理
4. THE Management_Frontend SHALL 提供质量趋势分析图表
5. THE Management_Frontend SHALL 支持质量规则的启用/禁用管理

### 需求 7: 安全审计与权限管理

**用户故事:** 作为安全管理员，我希望能够管理用户权限和查看系统审计日志，以便确保系统安全合规。

#### 验收标准

1. THE Security_Module SHALL 提供权限设置界面（角色矩阵）
2. THE Security_Module SHALL 显示审计日志（操作记录、时间、用户）
3. THE Security_Module SHALL 支持脱敏规则配置和管理
4. THE Security_Module SHALL 提供用户行为分析报表
5. THE Security_Module SHALL 支持 IP 白名单管理

### 需求 8: 系统设置与配置

**用户故事:** 作为系统管理员，我希望能够管理系统配置和租户信息，以便维护系统的正常运行。

#### 验收标准

1. THE Admin_Console SHALL 提供租户管理功能（仅管理员可见）
2. THE Admin_Console SHALL 支持 AI 模型配置（Ollama/HuggingFace 切换）
3. THE Admin_Console SHALL 提供系统监控界面（性能指标、健康状态）
4. THE Admin_Console SHALL 支持国际化配置（中英文切换）
5. THE Admin_Console SHALL 提供系统参数配置和环境变量管理

### 需求 9: 响应式设计与用户体验

**用户故事:** 作为系统用户，我希望界面能够适配不同设备和屏幕尺寸，并提供良好的用户体验。

#### 验收标准

1. THE Management_Frontend SHALL 支持响应式设计（桌面、平板、手机）
2. THE Management_Frontend SHALL 提供流畅的页面切换和加载体验
3. THE Management_Frontend SHALL 支持键盘快捷键操作
4. THE Management_Frontend SHALL 提供友好的错误提示和加载状态
5. THE Management_Frontend SHALL 支持浏览器前进/后退导航

### 需求 10: 数据可视化与报表

**用户故事:** 作为业务分析师，我希望能够通过图表和报表了解业务数据，以便进行数据驱动的决策。

#### 验收标准

1. THE Management_Frontend SHALL 提供多种图表类型（折线图、柱状图、饼图、散点图）
2. THE Management_Frontend SHALL 支持图表数据的实时更新
3. THE Management_Frontend SHALL 提供报表导出功能（PDF、Excel、图片）
4. THE Management_Frontend SHALL 支持自定义时间范围的数据筛选
5. THE Management_Frontend SHALL 提供数据钻取和详情查看功能