# 需求文档：数据生命周期管理平台（数据闭环）

**版本**: 3.0  
**创建日期**: 2026-03-10  
**更新日期**: 2026-03-10  
**状态**: 草稿

---

## 1. 需求概述

### 1.1 背景
当前系统中，数据结构化、数据增强、数据源同步等模块各自实现了独立的转存逻辑（如 `add-to-library` 接口），导致代码重复、维护困难。同时，系统缺乏完整的数据生命周期管理能力，数据在标注完成后无法回流，AI助手无法访问流转数据，数据无法进行合并、拆分等操作，导致数据流转不完整。

需要将数据转存系统升级为完整的**数据生命周期管理平台**，实现数据的完整闭环：数据源 → 转存 → 流转 → 标注 → 回流 → AI分析 → 再利用。

### 1.2 目标
- **统一接口**：用一个通用的 API 替代现有的各模块独立转存逻辑
- **数据闭环**：实现完整的数据生命周期管理，支持数据在各个环节的流转
- **CRUD操作**：支持数据的增删改查、合并、拆分等完整操作
- **权限控制**：实现基于角色的数据操作权限管理
- **审批流程**：支持数据操作审批机制（可选）
- **标注回流**：标注任务完成的数据可通过统一接口回流到数据流转系统
- **AI助手集成**：AI助手可基于技能配置访问流转数据进行分析
- **国际化支持**：所有用户界面文本支持中英文切换

### 1.3 范围
- 统一数据操作 API 设计与实现（转存、CRUD、合并、拆分）
- 替代现有转存逻辑（如 `POST /api/enhancements/{job_id}/add-to-library`）
- 权限和审批系统设计（扩展支持CRUD操作）
- 标注任务数据回流接口
- AI助手数据访问接口（基于技能配置）
- 前端国际化完整覆盖
- 数据结构化、数据增强、数据源同步、标注任务、AI助手模块集成

### 1.4 数据闭环架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据生命周期闭环                            │
└─────────────────────────────────────────────────────────────────┘

数据源模块                统一数据操作平台              数据消费模块
┌──────────┐            ┌──────────────┐            ┌──────────┐
│数据结构化 │───转存────→│              │            │          │
│数据增强  │───转存────→│  数据流转    │←───查询────│ AI助手   │
│数据源同步│───转存────→│  (CRUD)      │            │(技能配置)│
└──────────┘            │              │            └──────────┘
                        │  • 临时存储   │
     ┌──────回流────────│  • 样本库     │
     │                  │  • 待标注     │
     │                  └──────────────┘
     │                         │
     │                    转存/查询
     │                         ↓
┌──────────┐            ┌──────────────┐
│标注任务  │←───创建────│  标注管理    │
│(完成)   │            │              │
└──────────┘            └──────────────┘

数据操作：增(CREATE) 删(DELETE) 改(UPDATE) 查(READ) 合并(MERGE) 拆分(SPLIT)
```

---

## 2. 功能需求

### 2.1 统一转存接口

**需求 ID**: REQ-2.1  
**优先级**: 高

**描述**: 设计并实现统一的数据转存 API，替代现有的分散转存逻辑

**现有逻辑（需替代）**:
- `POST /api/enhancements/{job_id}/add-to-library` - 数据增强转样本库
- 其他模块的独立转存实现

**新统一接口**:
- `POST /api/data-lifecycle/transfer` - 统一转存接口
- `POST /api/data-lifecycle/batch-transfer` - 批量转存接口

**验收标准**:
- 统一接口支持所有源类型（structuring, augmentation, sync）
- 统一接口支持所有目标状态（temp_stored, in_sample_library, annotation_pending）
- 现有转存逻辑迁移到新接口，旧接口标记为废弃
- 保持向后兼容性（旧接口在过渡期内仍可用）
- API 文档完整，包含所有参数说明和示例

### 2.2 权限控制系统

**需求 ID**: REQ-2.2  
**优先级**: 高

**描述**: 实现基于角色的数据转存权限控制

**角色定义**:
- **管理员（Admin）**: 拥有所有权限，无需审批
- **数据管理员（Data Manager）**: 可以转存数据到任何状态，无需审批
- **数据分析师（Data Analyst）**: 可以转存到临时存储，转存到样本库需审批
- **普通用户（User）**: 只能转存到临时存储，其他操作需审批

**权限矩阵**:

| 角色 | 转存到临时存储 | 转存到样本库 | 转存到待标注 | 批量转存 | 跨项目转存 |
|------|--------------|------------|------------|---------|----------|
| 管理员 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 数据管理员 | ✓ | ✓ | ✓ | ✓ | ✗ |
| 数据分析师 | ✓ | 需审批 | 需审批 | ✗ | ✗ |
| 普通用户 | ✓ | 需审批 | 需审批 | ✗ | ✗ |

**验收标准**:
- 实现角色权限检查中间件
- 转存操作前验证用户权限
- 无权限时返回 403 错误，提示需要的权限级别
- 管理员可以查看和管理所有转存操作
- 权限配置可通过管理后台调整

### 2.3 审批流程系统

**需求 ID**: REQ-2.3  
**优先级**: 中

**描述**: 为需要审批的转存操作提供审批流程

**审批触发条件**:
- 数据分析师转存到样本库或待标注
- 普通用户转存到样本库或待标注
- 批量转存超过 1000 条记录（可配置）
- 跨项目转存操作

**审批流程**:
1. 用户提交转存请求
2. 系统创建审批工单
3. 通知审批人（数据管理员或管理员）
4. 审批人审核并批准/拒绝
5. 系统执行转存或通知用户拒绝原因

**验收标准**:
- 需要审批的操作创建审批工单
- 审批人收到通知（站内消息 + 邮件）
- 审批人可以查看转存详情（数据摘要、目标状态等）
- 审批人可以批准、拒绝或要求修改
- 用户可以查看审批状态和历史
- 审批超时自动拒绝（默认 7 天）

### 2.4 数据结构化转存功能

**需求 ID**: REQ-2.4  
**优先级**: 高

**描述**: 在数据结构化完成页面，添加"转存到数据流转"按钮

**验收标准**:
- 在结构化结果预览页面显示"转存到数据流转"按钮
- 按钮文本支持国际化（中文：转存到数据流转，英文：Transfer to Data Flow）
- 点击按钮打开转存配置弹窗
- 弹窗显示当前数据摘要（记录数、字段信息）
- 用户可以选择目标状态（根据权限显示可用选项）
- 用户可以填写数据属性（分类、标签、质量评分等）
- 转存成功后跳转到数据流转页面

### 2.5 数据增强转存功能

**需求 ID**: REQ-2.5  
**优先级**: 高

**描述**: 在数据增强完成后，提供转存到数据流转的选项，替代现有 `add-to-library` 接口

**验收标准**:
- 在增强结果页面显示"转存到数据流转"按钮
- 支持选择增强后的数据转入样本库或待标注状态
- 保留增强前后的关联关系
- 记录增强方法和参数
- 旧的 `add-to-library` 接口标记为废弃，但保持兼容

### 2.6 数据源同步转存功能

**需求 ID**: REQ-2.6  
**优先级**: 中

**描述**: 在数据源同步完成后，提供转存到数据流转的选项

**验收标准**:
- 在同步任务完成页面显示"转存到数据流转"按钮
- 支持批量转存同步的数据
- 保留数据源信息和同步时间
- 大批量转存（>1000条）需要审批

### 2.7 转存配置弹窗

**需求 ID**: REQ-2.7  
**优先级**: 高

**描述**: 统一的转存配置界面，完整国际化支持

**验收标准**:
- 显示数据摘要（来源、记录数、字段列表）
- 目标状态选择（下拉框）：
  - 临时存储 (temp_stored) - 中文：临时存储，英文：Temporary Storage
  - 样本库 (in_sample_library) - 中文：样本库，英文：Sample Library
  - 待标注 (annotation_pending) - 中文：待标注，英文：Pending Annotation
- 根据用户权限显示可用选项（灰显无权限选项并提示）
- 数据属性配置：
  - 分类（category）：文本输入，占位符国际化
  - 标签（tags）：多标签输入，占位符国际化
  - 质量评分（quality_score）：0-1 滑块，标签国际化
  - 描述（description）：文本域，占位符国际化
- 确认和取消按钮文本国际化
- 需要审批时显示提示信息

### 2.8 转存后导航

**需求 ID**: REQ-2.8  
**优先级**: 中

**描述**: 转存成功后的用户引导

**验收标准**:
- 显示成功提示消息（国际化）
- 提供"查看数据流转"链接（国际化）
- 提供"创建标注任务"快捷入口（如果转存到待标注状态，国际化）
- 可以选择继续处理其他数据或查看转存的数据
- 如果进入审批流程，显示审批状态和预计时间

### 2.9 国际化完整覆盖

**需求 ID**: REQ-2.9  
**优先级**: 高

**描述**: 所有用户界面文本支持中英文切换

**国际化范围**:
- 按钮文本：转存到数据流转、确认、取消等
- 表单标签：分类、标签、质量评分、描述等
- 占位符文本：输入分类、添加标签等
- 状态名称：临时存储、样本库、待标注等
- 提示消息：成功、失败、权限不足、需要审批等
- 错误消息：所有 API 错误响应
- 审批相关：审批中、已批准、已拒绝等

**验收标准**:
- 所有用户可见文本使用 `t()` 函数包裹
- 翻译键同步写入 `frontend/src/locales/zh/dataLifecycle.json` 和 `frontend/src/locales/en/dataLifecycle.json`
- 使用 `useTranslation('dataLifecycle')` hook
- 动态内容（如记录数）使用插值：`t('key', { count: 15 })`
- 切换语言后所有文本立即更新

---

## 2.10 数据CRUD操作功能

**需求 ID**: REQ-2.10  
**优先级**: 高

**描述**: 支持对流转数据进行完整的增删改查操作

**操作类型**:
- **CREATE**: 手动创建新数据记录
- **READ**: 查询和浏览流转数据
- **UPDATE**: 更新现有数据记录
- **DELETE**: 删除数据记录

**权限矩阵扩展**:

| 角色 | CREATE | READ | UPDATE | DELETE |
|------|--------|------|--------|--------|
| 管理员 | ✓ | ✓ | ✓ | ✓ |
| 数据管理员 | ✓ | ✓ | ✓ | 需审批 |
| 数据分析师 | ✓ | ✓ | 需审批 | ✗ |
| 普通用户 | 需审批 | ✓ | ✗ | ✗ |

**验收标准**:
- 提供统一的CRUD API接口
- 所有操作遵循权限控制
- 操作记录审计日志
- 前端提供数据管理界面（表格、表单、详情页）
- 支持批量操作（批量删除、批量更新）
- 所有界面文本支持国际化

---

## 2.11 数据合并与拆分功能

**需求 ID**: REQ-2.11  
**优先级**: 中

**描述**: 支持将多条数据合并为一条，或将一条数据拆分为多条

**合并操作**:
- 选择多条数据记录
- 配置合并策略（字段合并规则）
- 生成新的合并后数据
- 保留原始数据关联关系

**拆分操作**:
- 选择一条数据记录
- 配置拆分规则（按字段、按条件）
- 生成多条拆分后数据
- 保留原始数据关联关系

**权限矩阵**:

| 角色 | MERGE | SPLIT |
|------|-------|-------|
| 管理员 | ✓ | ✓ |
| 数据管理员 | ✓ | ✓ |
| 数据分析师 | ✗ | ✗ |
| 普通用户 | ✗ | ✗ |

**验收标准**:
- 提供合并和拆分API接口
- 前端提供合并/拆分配置界面
- 支持预览合并/拆分结果
- 操作可撤销（保留原始数据）
- 记录操作历史和关联关系
- 所有界面文本支持国际化

---

## 2.12 标注任务数据回流

**需求 ID**: REQ-2.12  
**优先级**: 高

**描述**: 标注任务完成后，数据可通过统一接口回流到数据流转系统

**数据流向**:
```
标注任务(完成) → 统一转存接口 → 数据流转系统
```

**新增source_type**:
- `annotation`: 标注任务完成的数据

**验收标准**:
- 标注任务完成页面显示"回流到数据流转"按钮
- 支持选择回流目标状态（样本库、临时存储）
- 保留标注结果和标注人信息
- 记录标注任务ID和完成时间
- 支持批量回流
- 所有界面文本支持国际化

---

## 2.13 AI助手数据访问接口

**需求 ID**: REQ-2.13  
**优先级**: 高

**描述**: AI助手可基于技能配置访问流转数据进行分析

**技能配置模型**:
```python
class AISkillConfig:
    skill_id: str                      # 技能ID
    skill_name: str                    # 技能名称
    allowed_source_types: List[str]    # 可访问的数据源类型
    allowed_target_states: List[str]   # 可访问的目标状态
    allowed_categories: List[str]      # 可访问的数据分类
    read_only: bool = True             # 是否只读（默认只读）
    max_records_per_query: int = 1000  # 单次查询最大记录数
```

**技能配置示例**:
- **数据质量分析**: 可访问所有已标注数据
- **文本摘要生成**: 可访问样本库中的文本数据
- **数据增强建议**: 可访问临时存储和样本库数据

**验收标准**:
- 提供AI助手查询接口 `GET /api/data-lifecycle/ai-query`
- 支持基于技能ID的访问控制
- 支持多种查询条件（source_type, target_state, category等）
- 返回数据符合技能配置限制
- 记录AI助手访问日志
- API文档完整

---

## 2.14 数据生命周期闭环

**需求 ID**: REQ-2.14  
**优先级**: 高

**描述**: 实现完整的数据生命周期闭环，数据可在各个环节流转

**完整闭环流程**:
```
1. 数据源 (结构化/增强/同步) → 转存 → 数据流转系统
2. 数据流转系统 → 创建标注任务 → 标注管理
3. 标注完成 → 回流 → 数据流转系统
4. AI助手 → 查询 → 数据流转系统 → 分析结果
5. 分析结果 → 转存 → 数据流转系统 (新数据源)
```

**新增source_type**:
- `annotation`: 标注任务完成的数据
- `ai_assistant`: AI助手处理的数据
- `manual`: 手动创建/编辑的数据

**验收标准**:
- 所有数据源都可通过统一接口转存
- 标注完成的数据可回流
- AI助手可访问和分析数据
- AI助手分析结果可作为新数据源
- 数据在各环节的流转可追溯
- 提供数据流转可视化界面

---

## 3. 非功能需求

### 3.1 性能要求
- 转存操作响应时间 < 3 秒（1000 条记录以内）
- 支持批量转存最多 10000 条记录
- 权限检查响应时间 < 100ms
- 审批工单创建时间 < 1 秒

### 3.2 可用性要求
- 转存配置界面简洁直观
- 提供字段映射预览
- 错误提示清晰明确，支持国际化
- 权限不足时提示所需权限级别
- 审批状态实时更新

### 3.3 兼容性要求
- 兼容现有数据结构化、数据增强、数据源同步模块
- 不影响现有数据流转系统功能
- 旧接口保持向后兼容（过渡期 3 个月）
- 支持主流浏览器（Chrome, Firefox, Safari, Edge）

### 3.4 安全性要求
- 所有转存操作记录审计日志
- 敏感数据转存需要额外验证
- 防止未授权的批量数据导出
- API 接口需要身份认证和权限验证
- 审批流程防止绕过攻击

### 3.5 可维护性要求
- 权限配置可通过配置文件或数据库调整
- 审批规则可配置（阈值、超时时间等）
- 统一的错误处理和日志记录
- 代码遵循项目编码规范

---

## 4. 数据流转状态说明

### 4.1 可选目标状态

| 状态代码 | 状态名称 | 说明 | 适用场景 |
|---------|---------|------|---------|
| temp_stored | 临时存储 | 数据暂存，待审核 | 需要人工审核的数据 |
| in_sample_library | 样本库 | 高质量样本 | 已验证的优质数据 |
| annotation_pending | 待标注 | 等待标注 | 需要人工标注的数据 |

### 4.2 状态转换规则
- 数据结构化 → 临时存储 → 审核 → 样本库/待标注
- 数据增强 → 样本库/待标注
- 数据源同步 → 临时存储/样本库

---

## 5. 接口需求

### 5.1 统一转存接口

**接口**: POST /api/data-lifecycle/transfer  
**描述**: 将数据转存到数据流转系统（替代现有分散接口）

**权限要求**: 需要身份认证，根据角色和目标状态检查权限

**请求头**:
```
Authorization: Bearer <token>
Content-Type: application/json
Accept-Language: zh-CN | en-US
```

**请求参数**:
```json
{
  "source_type": "structuring|augmentation|sync",
  "source_id": "uuid",
  "target_state": "temp_stored|in_sample_library|annotation_pending",
  "data_attributes": {
    "category": "string",
    "tags": ["string"],
    "quality_score": 0.95,
    "description": "string"
  },
  "records": [
    {
      "id": "uuid",
      "content": {...},
      "metadata": {...}
    }
  ],
  "request_approval": false
}
```

**成功响应** (200):
```json
{
  "success": true,
  "transferred_count": 15,
  "lifecycle_ids": ["uuid"],
  "message": "数据已成功转存到数据流转系统",
  "navigation_url": "/data-lifecycle/temp-data"
}
```

**需要审批响应** (202):
```json
{
  "success": true,
  "approval_required": true,
  "approval_id": "approval-uuid",
  "message": "转存请求已提交，等待审批",
  "estimated_approval_time": "2-3 个工作日"
}
```

**权限不足响应** (403):
```json
{
  "success": false,
  "error_code": "PERMISSION_DENIED",
  "message": "您没有权限执行此操作",
  "required_permission": "data_manager",
  "current_role": "user"
}
```

**错误响应** (400/404/500):
```json
{
  "success": false,
  "error_code": "INVALID_SOURCE|SOURCE_NOT_FOUND|INTERNAL_ERROR",
  "message": "错误描述（国际化）",
  "details": {...}
}
```

### 5.2 批量转存接口

**接口**: POST /api/data-lifecycle/batch-transfer  
**描述**: 批量转存多个数据源

**权限要求**: 需要 data_manager 或 admin 角色

**请求参数**:
```json
{
  "transfers": [
    {
      "source_type": "sync",
      "source_id": "sync-job-1",
      "target_state": "temp_stored",
      "data_attributes": {...},
      "records": [...]
    }
  ]
}
```

**响应**:
```json
{
  "success": true,
  "total_transfers": 2,
  "successful_transfers": 2,
  "failed_transfers": 0,
  "results": [...]
}
```

### 5.3 审批接口

**接口**: POST /api/data-lifecycle/approvals/{approval_id}/approve  
**描述**: 批准转存请求

**权限要求**: 需要 data_manager 或 admin 角色

**请求参数**:
```json
{
  "approved": true,
  "comment": "审批意见"
}
```

**接口**: GET /api/data-lifecycle/approvals  
**描述**: 查询审批列表

**查询参数**:
- status: pending | approved | rejected
- user_id: 申请人 ID
- page, page_size: 分页参数

### 5.4 权限检查接口

**接口**: GET /api/data-lifecycle/permissions/check  
**描述**: 检查用户对特定操作的权限

**查询参数**:
- operation: transfer_to_temp | transfer_to_library | transfer_to_annotation | batch_transfer | create | read | update | delete | merge | split
- source_type: structuring | augmentation | sync | annotation | ai_assistant | manual

**响应**:
```json
{
  "has_permission": true,
  "requires_approval": false,
  "role": "data_analyst"
}
```

---

### 5.5 数据CRUD接口

**接口**: POST /api/data-lifecycle/records  
**描述**: 创建新数据记录

**请求参数**:
```json
{
  "source_type": "manual",
  "target_state": "temp_stored",
  "data_attributes": {...},
  "content": {...},
  "metadata": {...}
}
```

**接口**: GET /api/data-lifecycle/records  
**描述**: 查询数据记录

**查询参数**:
- source_type: 数据源类型
- target_state: 目标状态
- category: 数据分类
- tags: 标签（多个）
- page, page_size: 分页参数

**接口**: PUT /api/data-lifecycle/records/{record_id}  
**描述**: 更新数据记录

**接口**: DELETE /api/data-lifecycle/records/{record_id}  
**描述**: 删除数据记录

---

### 5.6 数据合并与拆分接口

**接口**: POST /api/data-lifecycle/records/merge  
**描述**: 合并多条数据记录

**请求参数**:
```json
{
  "record_ids": ["id1", "id2", "id3"],
  "merge_strategy": {
    "field1": "concat",
    "field2": "first",
    "field3": "last"
  },
  "target_state": "temp_stored",
  "data_attributes": {...}
}
```

**接口**: POST /api/data-lifecycle/records/{record_id}/split  
**描述**: 拆分单条数据记录

**请求参数**:
```json
{
  "split_rules": [
    {
      "condition": "field1 == 'value1'",
      "target_state": "temp_stored"
    },
    {
      "condition": "field1 == 'value2'",
      "target_state": "in_sample_library"
    }
  ]
}
```

---

### 5.7 AI助手查询接口

**接口**: GET /api/data-lifecycle/ai-query  
**描述**: AI助手查询流转数据

**请求头**:
```
X-AI-Skill-ID: skill-123
Authorization: Bearer <token>
```

**查询参数**:
- source_type: 数据源类型
- target_state: 目标状态
- category: 数据分类
- limit: 返回记录数（受技能配置限制）

**响应**:
```json
{
  "success": true,
  "records": [...],
  "total": 100,
  "skill_id": "skill-123",
  "skill_name": "数据质量分析"
}
```

---

### 5.8 标注数据回流接口

**接口**: POST /api/data-lifecycle/transfer  
**描述**: 标注任务完成后数据回流（复用统一转存接口）

**请求参数**:
```json
{
  "source_type": "annotation",
  "source_id": "annotation-task-123",
  "target_state": "in_sample_library",
  "data_attributes": {
    "category": "annotated_data",
    "tags": ["annotated", "quality_checked"],
    "quality_score": 0.95
  },
  "records": [
    {
      "id": "record-1",
      "content": {...},
      "metadata": {
        "annotation_task_id": "task-123",
        "annotator_id": "user-456",
        "annotation_result": {...},
        "completed_at": "2026-03-10T10:00:00Z"
      }
    }
  ]
}
```

---

## 6. 用户故事

### 6.1 数据结构化转存（普通用户）
**作为** 数据分析师  
**我想要** 在数据结构化完成后直接转存到临时存储  
**以便** 进行后续的审核工作  
**验收标准**: 点击转存按钮，选择临时存储，无需审批即可完成转存

### 6.2 数据增强转存到样本库（需审批）
**作为** 数据分析师  
**我想要** 将增强后的高质量数据转入样本库  
**以便** 用于模型训练  
**验收标准**: 提交转存请求后进入审批流程，收到审批通知，审批通过后数据转入样本库

### 6.3 管理员批量转存（无需审批）
**作为** 管理员  
**我想要** 批量转存同步的数据到样本库  
**以便** 快速构建训练数据集  
**验收标准**: 选择多个数据源，批量转存到样本库，无需审批，立即完成

### 6.4 审批转存请求
**作为** 数据管理员  
**我想要** 审核其他用户的转存请求  
**以便** 确保数据质量和合规性  
**验收标准**: 收到审批通知，查看转存详情，批准或拒绝请求，申请人收到结果通知

### 6.5 查看权限和审批状态
**作为** 普通用户  
**我想要** 了解我对不同操作的权限  
**以便** 知道哪些操作需要审批  
**验收标准**: 界面显示我的权限级别，无权限的选项灰显并提示，可以查看审批历史

### 6.6 国际化体验
**作为** 英文用户  
**我想要** 使用英文界面进行数据转存  
**以便** 更好地理解和操作系统  
**验收标准**: 切换到英文后，所有按钮、标签、提示信息都显示英文，操作流程与中文一致

### 6.7 数据管理操作
**作为** 数据管理员  
**我想要** 对流转数据进行增删改查操作  
**以便** 维护数据质量和完整性  
**验收标准**: 可以创建、查询、更新、删除数据记录，删除操作需要审批，所有操作记录审计日志

### 6.8 数据合并
**作为** 数据管理员  
**我想要** 将多条重复或相关的数据合并为一条  
**以便** 减少数据冗余，提高数据质量  
**验收标准**: 选择多条数据，配置合并策略，预览合并结果，确认后生成新数据，保留原始数据关联

### 6.9 标注数据回流
**作为** 标注管理员  
**我想要** 将标注完成的数据回流到样本库  
**以便** 用于模型训练和数据分析  
**验收标准**: 标注任务完成后，点击回流按钮，选择目标状态，数据成功转存并保留标注结果

### 6.10 AI助手数据分析
**作为** AI助手（数据质量分析技能）  
**我想要** 访问样本库中的已标注数据  
**以便** 进行数据质量分析并生成报告  
**验收标准**: 通过技能ID访问数据，只能读取配置允许的数据类型和状态，单次查询不超过配置限制

### 6.11 数据闭环流转
**作为** 系统管理员  
**我想要** 查看数据在各个环节的完整流转路径  
**以便** 了解数据生命周期和追溯数据来源  
**验收标准**: 提供数据流转可视化界面，显示数据从源头到当前状态的完整路径，包括所有操作历史

---

## 7. 约束条件

### 7.1 技术约束
- 必须保持数据完整性
- 转存操作必须是原子性的（全部成功或全部失败）
- 必须记录转存操作的审计日志
- 统一接口必须兼容现有数据模型
- 国际化文本必须使用 `t()` 函数，不允许硬编码

### 7.2 业务约束
- 只有完成状态的数据才能转存
- 转存后原数据保持不变（复制而非移动）
- 用户必须有相应权限才能执行转存操作
- 审批流程不可绕过（除管理员外）
- 敏感数据转存需要额外审批

### 7.3 迁移约束
- 现有 `add-to-library` 接口保持 3 个月兼容期
- 兼容期内新旧接口并存
- 兼容期后旧接口返回 410 Gone 状态码
- 提供迁移指南和示例代码

---

## 8. 验收标准

### 8.1 功能验收
- [ ] 统一转存接口正常工作
- [ ] 数据结构化页面显示转存按钮
- [ ] 数据增强页面显示转存按钮
- [ ] 数据源同步页面显示转存按钮
- [ ] 转存配置弹窗正常工作
- [ ] 数据成功转存到数据流转系统
- [ ] 转存后可以在数据流转页面查看
- [ ] 权限检查正常工作
- [ ] 审批流程正常工作
- [ ] 管理员拥有所有权限

### 8.2 性能验收
- [ ] 1000 条记录转存时间 < 3 秒
- [ ] 10000 条记录转存时间 < 30 秒
- [ ] 权限检查响应时间 < 100ms
- [ ] 审批工单创建时间 < 1 秒

### 8.3 国际化验收
- [ ] 所有用户界面文本支持中英文
- [ ] 切换语言后所有文本立即更新
- [ ] 错误消息根据语言显示
- [ ] API 响应消息支持国际化
- [ ] 翻译文件完整无遗漏

### 8.4 安全性验收
- [ ] 未授权访问返回 401
- [ ] 权限不足返回 403
- [ ] 所有操作记录审计日志
- [ ] 敏感数据转存需要审批
- [ ] 防止批量数据泄露

### 8.5 用户体验验收
- [ ] 操作流程顺畅，无卡顿
- [ ] 错误提示清晰
- [ ] 成功后有明确的反馈
- [ ] 权限不足时提示所需权限
- [ ] 审批状态实时显示

---

## 9. 风险和依赖

### 9.1 风险
- **迁移风险**: 现有代码依赖旧接口，需要逐步迁移
- **性能风险**: 数据量大时转存可能超时
- **权限风险**: 权限配置错误可能导致安全问题
- **审批风险**: 审批流程可能影响用户体验
- **国际化风险**: 翻译不准确可能导致误解

### 9.2 依赖
- 依赖数据流转系统 API
- 依赖数据结构化、数据增强、数据源同步模块的完成状态
- 依赖用户认证和角色管理系统
- 依赖审批工作流系统
- 依赖国际化框架（react-i18next）

### 9.3 风险缓解措施
- 提供详细的迁移文档和示例代码
- 实现分页和流式处理支持大数据量
- 权限配置提供默认安全策略
- 审批流程支持快速通道（管理员）
- 翻译由专业人员审核

---

## 10. 后续规划

### 10.1 第一阶段（当前 - MVP）
- 实现统一转存接口
- 实现基本权限控制
- 实现审批流程
- 完整国际化支持
- 替代现有 `add-to-library` 接口

### 10.2 第二阶段（优化）
- 支持自定义字段映射
- 支持转存规则配置
- 支持自动转存（满足条件自动触发）
- 审批流程优化（多级审批、委托审批）
- 权限细粒度控制（字段级权限）

### 10.3 第三阶段（高级功能）
- 支持转存历史查询和统计
- 支持转存回滚
- 支持转存数据质量分析
- 支持跨租户数据转存
- AI 辅助审批决策

---

## 11. 附录

### 11.1 术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| 数据生命周期 | Data Lifecycle | 数据从创建到归档的完整流程 |
| 数据闭环 | Data Loop | 数据在各环节流转并形成完整循环 |
| 数据流转 | Data Flow | 数据生命周期管理系统 |
| 临时存储 | Temporary Storage | 数据暂存状态 |
| 样本库 | Sample Library | 高质量样本存储 |
| 待标注 | Pending Annotation | 等待人工标注状态 |
| 数据结构化 | Data Structuring | 从非结构化数据提取结构化信息 |
| 数据增强 | Data Augmentation | 提升数据质量和丰富度 |
| 数据源同步 | Data Sync | 从外部数据源同步数据 |
| 数据回流 | Data Backflow | 标注完成的数据返回流转系统 |
| AI技能 | AI Skill | AI助手的特定能力配置 |
| 数据合并 | Data Merge | 将多条数据合并为一条 |
| 数据拆分 | Data Split | 将一条数据拆分为多条 |

### 11.2 相关文档
- 数据流转系统设计文档：`.kiro/specs/data-lifecycle-management/design.md`
- 权限系统设计文档：`.kiro/specs/data-permission-control/design.md`
- 国际化规范：`.kiro/rules/i18n-translation-rules.md`
- API 设计规范：`文档/API设计规范.md`

### 11.3 示例代码

**前端转存按钮使用示例**:
```tsx
import { useTranslation } from 'react-i18next';
import { TransferToLifecycleButton } from '@/components/DataLifecycle/Transfer';

const StructuringResultPage = () => {
  const { t } = useTranslation('dataLifecycle');
  
  return (
    <TransferToLifecycleButton
      sourceType="structuring"
      sourceId={taskId}
      records={structuredRecords}
      onSuccess={(result) => {
        message.success(t('transfer.successMessage', { 
          count: result.transferred_count,
          state: t(`transfer.states.${result.target_state}`)
        }));
      }}
    />
  );
};
```

**后端权限检查示例**:
```python
from src.services.permission_service import PermissionService

async def transfer_data(
    request: TransferRequest,
    current_user: User = Depends(get_current_user)
):
    # 检查权限
    permission_service = PermissionService()
    has_permission = await permission_service.check_transfer_permission(
        user=current_user,
        target_state=request.target_state,
        record_count=len(request.records)
    )
    
    if not has_permission.allowed:
        if has_permission.requires_approval:
            # 创建审批工单
            approval = await create_approval_request(request, current_user)
            return ApprovalResponse(approval_id=approval.id)
        else:
            raise HTTPException(
                status_code=403,
                detail=i18n.t('errors.permission_denied', 
                            required_role=has_permission.required_role)
            )
    
    # 执行转存
    result = await transfer_service.transfer(request)
    return result
```
