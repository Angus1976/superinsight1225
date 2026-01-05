# SuperInsight AI 数据治理与标注平台 - 需求文档

## 介绍

SuperInsight 是一款专为 AI 时代设计的企业级语料治理与智能标注平台，深度借鉴龙石数据成熟的"理采存管用"方法论，同时针对大模型（LLM）和生成式 AI（GenAI）应用场景进行全面升级。平台以安全只读提取 + 人机协同标注 + 业务规则智能注入为核心，帮助企业快速构建高质量、AI 友好的语料数据集。

## 术语表

- **SuperInsight_Platform**: 整个 AI 数据治理与标注平台系统
- **Annotation_Engine**: 原生标注引擎，提供完整的标注功能
- **PostgreSQL_Database**: 统一数据存储系统，使用 JSONB 格式
- **TCB_Cloud**: 腾讯云 TCB 云托管服务
- **Data_Extractor**: 安全只读数据提取模块
- **AI_Annotator**: AI 预标注服务
- **Quality_Manager**: 语义质量评估与管理模块
- **Billing_System**: 计费结算系统
- **Security_Controller**: 安全控制与权限管理模块
- **Permission_System**: 基于角色的权限控制系统
- **Role_Manager**: 角色管理器，支持管理员、业务专家、标注员、查看者四种角色
- **Business_Logic_Extractor**: 业务逻辑提炼器，从标注数据中自动识别和提炼业务规则

## 需求

### 需求 1: 安全数据提取

**用户故事:** 作为数据管理员，我希望能够安全地从各种数据源提取语料数据，以便为 AI 标注做准备。

#### 验收标准

1. WHEN 连接到客户数据库时，THE Data_Extractor SHALL 使用只读权限进行连接
2. WHEN 提取结构化数据时，THE Data_Extractor SHALL 支持 MySQL、PostgreSQL、Oracle 等主流数据库
3. WHEN 提取非结构化数据时，THE Data_Extractor SHALL 支持 PDF、Word、Notion、网页等格式
4. WHEN 数据传输过程中，THE Data_Extractor SHALL 使用加密传输协议
5. WHEN 提取完成后，THE Data_Extractor SHALL 在 PostgreSQL_Database 中创建原始数据副本

### 需求 2: 语料存储与管理

**用户故事:** 作为系统架构师，我希望有一个统一的存储系统来管理所有语料数据，以便支持高效的查询和扩展。

#### 验收标准

1. THE PostgreSQL_Database SHALL 使用 JSONB 格式存储原始语料数据
2. THE PostgreSQL_Database SHALL 使用 JSONB 格式存储标注结果和标签
3. THE PostgreSQL_Database SHALL 使用 JSONB 格式存储优质增强数据
4. THE PostgreSQL_Database SHALL 创建 GIN 索引以支持高效查询
5. WHEN 存储元数据时，THE PostgreSQL_Database SHALL 记录数据血缘和审计日志

### 需求 3: 原生标注功能

**用户故事:** 作为标注专家，我希望能够使用完整的原生标注界面进行数据标注，以便提高标注效率和质量。

#### 验收标准

1. THE Annotation_Engine SHALL 提供原生的标注界面，无需依赖外部iframe
2. WHEN 开始标注任务时，THE Annotation_Engine SHALL 支持情感分类、文本标注、评分等多种标注类型
3. WHEN 进行标注时，THE Annotation_Engine SHALL 提供快速标注按钮以提高效率
4. WHEN 标注过程中，THE Annotation_Engine SHALL 支持撤销/重做功能
5. THE Annotation_Engine SHALL 实时保存标注进度和结果
6. WHEN 标注完成时，THE Annotation_Engine SHALL 自动跳转到下一个未标注任务

### 需求 4: 基于角色的权限控制

**用户故事:** 作为系统管理员，我希望能够基于用户角色控制标注功能的访问权限，以便确保数据安全和工作流程的规范性。

#### 验收标准

1. THE Permission_System SHALL 支持四种用户角色：系统管理员、业务专家、数据标注员、报表查看者
2. WHEN 系统管理员登录时，THE Permission_System SHALL 授予所有标注和管理权限
3. WHEN 业务专家登录时，THE Permission_System SHALL 授予查看、创建、编辑标注的权限，但不能删除标注
4. WHEN 数据标注员登录时，THE Permission_System SHALL 授予查看、创建、编辑标注的权限，专注于标注工作
5. WHEN 报表查看者登录时，THE Permission_System SHALL 仅授予查看标注结果的权限
6. THE Permission_System SHALL 在界面上显示用户角色和权限状态
7. WHEN 用户权限不足时，THE Permission_System SHALL 显示友好的权限不足提示

### 需求 5: 人机协同标注

**用户故事:** 作为标注专家，我希望能够与 AI 协同进行数据标注，以便提高标注效率和质量。

#### 验收标准

1. WHEN 开始标注任务时，THE AI_Annotator SHALL 提供预标注结果
2. WHEN 人工标注时，THE Annotation_Engine SHALL 支持业务专家、技术专家和外包人员协作
3. WHEN 标注完成时，THE Annotation_Engine SHALL 通过 API 触发质量检查
4. THE Annotation_Engine SHALL 支持实时标注进度跟踪
5. THE AI_Annotator SHALL 提供置信度评分以辅助人工决策

### 需求 6: 业务规则与质量治理

**用户故事:** 作为质量管理员，我希望能够定义和执行业务规则，以便确保标注数据的质量。

#### 验收标准

1. THE Quality_Manager SHALL 提供内置的质量规则模板
2. WHEN 质量问题被发现时，THE Quality_Manager SHALL 创建质量工单
3. WHEN 质量工单被创建时，THE Quality_Manager SHALL 自动派发给相关专家
4. THE Quality_Manager SHALL 使用 Ragas 框架进行语义质量评估
5. WHEN 质量问题修复后，THE Quality_Manager SHALL 支持源头数据修复

### 需求 7: 数据增强与重构

**用户故事:** 作为 AI 工程师，我希望能够增强和重构语料数据，以便提高 AI 模型的训练效果。

#### 验收标准

1. THE SuperInsight_Platform SHALL 支持填充优质样本数据
2. WHEN 进行数据增强时，THE SuperInsight_Platform SHALL 放大正向激励数据占比
3. THE SuperInsight_Platform SHALL 提供数据重构接口
4. WHEN 数据增强完成时，THE SuperInsight_Platform SHALL 更新数据质量评分
5. THE SuperInsight_Platform SHALL 支持批量数据增强操作

### 需求 8: AI 友好数据集输出

**用户故事:** 作为 AI 开发者，我希望能够导出标准格式的数据集，以便用于 RAG、Agent 等 AI 应用。

#### 验收标准

1. THE SuperInsight_Platform SHALL 支持导出 JSON 格式数据集
2. THE SuperInsight_Platform SHALL 支持导出 CSV 格式数据集
3. THE SuperInsight_Platform SHALL 支持导出 COCO 格式数据集
4. THE SuperInsight_Platform SHALL 提供 RAG 测试接口
5. THE SuperInsight_Platform SHALL 提供 Agent 测试接口

### 需求 9: 计费结算系统

**用户故事:** 作为业务管理员，我希望能够跟踪标注工时和成本，以便进行准确的计费结算。

#### 验收标准

1. THE Billing_System SHALL 统计标注工时
2. THE Billing_System SHALL 统计标注条数
3. WHEN 月度结束时，THE Billing_System SHALL 生成月度账单
4. THE Billing_System SHALL 支持多租户隔离计费
5. THE Billing_System SHALL 提供计费报表和分析

### 需求 10: 安全合规管理

**用户故事:** 作为安全管理员，我希望平台能够满足企业级安全合规要求，以便保护敏感数据。

#### 验收标准

1. THE Security_Controller SHALL 提供项目级别的数据隔离
2. WHEN 处理敏感数据时，THE Security_Controller SHALL 执行数据脱敏
3. THE Security_Controller SHALL 记录所有操作的审计日志
4. THE Security_Controller SHALL 支持 IP 白名单访问控制
5. WHEN 用户访问系统时，THE Security_Controller SHALL 验证用户权限

### 需求 11: 多部署方式支持

**用户故事:** 作为运维工程师，我希望平台能够支持多种部署方式，以便满足不同客户的需求。

#### 验收标准

1. THE SuperInsight_Platform SHALL 支持腾讯云 TCB 云托管部署
2. THE SuperInsight_Platform SHALL 支持 Docker Compose 私有化部署
3. THE SuperInsight_Platform SHALL 支持混合云部署模式
4. WHEN 使用 TCB 部署时，THE SuperInsight_Platform SHALL 支持自动扩缩容
5. WHEN 使用私有化部署时，THE SuperInsight_Platform SHALL 确保数据不出客户环境

### 需求 12: AI 预标注集成

**用户故事:** 作为标注管理员，我希望集成 AI 预标注功能，以便提高标注效率。

#### 验收标准

1. THE AI_Annotator SHALL 集成 Ollama 本地模型
2. THE AI_Annotator SHALL 集成 HuggingFace 模型
3. WHEN 启动标注任务时，THE AI_Annotator SHALL 自动生成预标注结果
4. THE AI_Annotator SHALL 支持自定义模型配置
5. WHEN AI 预标注完成时，THE AI_Annotator SHALL 提供置信度评分

### 需求 13: 客户业务逻辑提炼与智能化

**用户故事:** 作为业务分析师，我希望系统能够从标注数据中自动提炼客户业务逻辑和规则，以便为客户提供智能化的业务洞察和决策支持。

#### 验收标准

1. THE Business_Logic_Extractor SHALL 分析标注数据中的业务模式和规律
2. WHEN 标注数据达到一定规模时，THE Business_Logic_Extractor SHALL 自动识别业务规则
3. THE Business_Logic_Extractor SHALL 生成可视化的业务逻辑图表和报告
4. WHEN 发现新的业务模式时，THE Business_Logic_Extractor SHALL 通知相关业务专家
5. THE Business_Logic_Extractor SHALL 支持业务规则的导出和应用
6. THE Business_Logic_Extractor SHALL 提供业务逻辑的置信度评分
7. WHEN 业务逻辑发生变化时，THE Business_Logic_Extractor SHALL 跟踪和记录变化趋势