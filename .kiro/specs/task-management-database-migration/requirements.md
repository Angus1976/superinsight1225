# 任务管理数据库迁移 - 需求文档

**功能名称**: task-management-database-migration  
**创建日期**: 2026-01-28  
**优先级**: P0 (高优先级)  
**状态**: 规划中

## 1. 用户故事

### 1.1 作为系统管理员，我需要完整的任务数据持久化

**As a** 系统管理员  
**I want** 任务数据能够持久化到数据库  
**So that** 系统重启后任务数据不会丢失

**Priority**: P0  
**Acceptance Criteria** (EARS):
- WHEN 创建新任务时，THEN 任务数据应保存到数据库
- WHEN 系统重启后，THEN 之前创建的任务仍然可以访问
- WHEN 查询任务列表时，THEN 应从数据库读取而不是 mock 数据
- WHERE 数据库连接失败时，THEN 系统应返回明确的错误信息

### 1.2 作为标注管理员，我需要创建和管理任务

**As a** 标注管理员  
**I want** 通过 UI 创建和编辑任务  
**So that** 可以为标注团队分配工作

**Priority**: P0  
**Acceptance Criteria** (EARS):
- WHEN 填写任务表单并提交时，THEN 任务应创建并保存到数据库
- WHEN 编辑任务信息时，THEN 更改应立即保存到数据库
- WHEN 删除任务时，THEN 任务应从数据库中移除
- IF 任务有关联的 Label Studio 项目，THEN 删除时应提示确认

### 1.3 作为开发人员，我需要统一的数据模型

**As a** 开发人员  
**I want** 统一的任务数据模型  
**So that** API 和数据库架构保持一致

**Priority**: P0  
**Acceptance Criteria** (EARS):
- WHEN 查询任务时，THEN 返回的字段应与 API 响应模型一致
- WHEN 数据库架构更新时，THEN 应有自动迁移脚本
- WHERE 存在旧数据时，THEN 迁移应保留所有现有数据
- IF 迁移失败，THEN 应能够回滚到之前的状态

### 1.4 作为系统用户，我需要任务数据的完整性

**As a** 系统用户  
**I want** 任务数据完整且一致  
**So that** 可以准确跟踪任务进度和状态

**Priority**: P1  
**Acceptance Criteria** (EARS):
- WHEN 任务状态更新时，THEN 相关的进度字段应自动更新
- WHEN 任务完成时，THEN completed_items 应等于 total_items
- WHERE 任务有截止日期，THEN 过期任务应被标记
- IF 任务被分配，THEN assignee_id 应引用有效的用户

## 2. 功能需求

### 2.1 数据库架构扩展

**需求**: 扩展现有 `tasks` 表以支持完整的任务管理功能

**必需字段**:
- `name` (varchar 255) - 任务名称
- `description` (text) - 任务描述
- `priority` (enum) - 优先级: low, medium, high, urgent
- `annotation_type` (enum) - 标注类型: text_classification, ner, sentiment, qa, custom
- `assignee_id` (uuid) - 分配给的用户 ID (FK to users)
- `created_by` (varchar 100) - 创建者
- `updated_at` (timestamp) - 更新时间
- `due_date` (timestamp) - 截止日期
- `progress` (integer) - 进度百分比 (0-100)
- `total_items` (integer) - 总项目数
- `completed_items` (integer) - 完成项目数
- `tags` (jsonb) - 标签数组
- `task_metadata` (jsonb) - 额外元数据

**约束**:
- `name` 不能为空
- `priority` 默认为 'medium'
- `annotation_type` 默认为 'custom'
- `progress` 范围 0-100
- `total_items` >= 1
- `completed_items` <= `total_items`

### 2.2 数据迁移

**需求**: 安全地迁移现有数据到新架构

**迁移步骤**:
1. 创建备份
2. 添加新字段（允许 NULL）
3. 填充默认值
4. 设置 NOT NULL 约束
5. 创建索引
6. 验证数据完整性

**回滚策略**:
- 保留迁移前的数据库快照
- 提供回滚脚本
- 记录所有迁移操作

### 2.3 API 更新

**需求**: 更新 API 端点以使用真实数据库

**影响的端点**:
- `GET /api/tasks` - 从数据库读取任务列表
- `GET /api/tasks/{id}` - 从数据库读取单个任务
- `POST /api/tasks` - 创建任务并保存到数据库
- `PATCH /api/tasks/{id}` - 更新数据库中的任务
- `DELETE /api/tasks/{id}` - 从数据库删除任务
- `GET /api/tasks/stats` - 从数据库计算统计数据

**移除**:
- 内存存储 `_tasks_storage`
- Mock 数据生成逻辑（保留用于测试）

### 2.4 前端集成

**需求**: 前端无缝切换到真实数据

**要求**:
- API 响应格式保持不变
- 错误处理更加完善
- 加载状态显示
- 数据验证

## 3. 非功能需求

### 3.1 性能

- 任务列表查询 < 200ms (1000 条记录)
- 单个任务查询 < 50ms
- 任务创建 < 100ms
- 支持分页和过滤

### 3.2 可靠性

- 数据库事务保证 ACID 特性
- 迁移失败自动回滚
- 数据完整性约束
- 定期备份

### 3.3 可维护性

- 清晰的迁移脚本
- 完整的文档
- 日志记录
- 错误追踪

### 3.4 安全性

- 租户隔离
- 权限验证
- SQL 注入防护
- 敏感数据加密

## 4. 依赖关系

### 4.1 技术依赖

- PostgreSQL 15+
- SQLAlchemy 2.0+
- Alembic (数据库迁移工具)
- FastAPI
- Pydantic

### 4.2 功能依赖

- 用户认证系统
- 租户管理系统
- Label Studio 集成

### 4.3 数据依赖

- `users` 表 (用于 assignee_id 外键)
- `documents` 表 (用于 document_id 外键)

## 5. 约束和限制

### 5.1 技术约束

- 必须保持向后兼容
- 不能影响现有的 Label Studio 集成
- 迁移过程中系统可能短暂不可用

### 5.2 业务约束

- 不能丢失任何现有数据
- 迁移必须可回滚
- 必须在非高峰时段执行

### 5.3 时间约束

- 迁移脚本执行时间 < 5 分钟
- 系统停机时间 < 10 分钟

## 6. 验收标准

### 6.1 数据库迁移

- [ ] 所有新字段已添加
- [ ] 数据类型正确
- [ ] 约束已设置
- [ ] 索引已创建
- [ ] 外键关系正确

### 6.2 API 功能

- [ ] 创建任务成功保存到数据库
- [ ] 查询任务从数据库读取
- [ ] 更新任务正确保存
- [ ] 删除任务从数据库移除
- [ ] 统计数据准确

### 6.3 数据完整性

- [ ] 所有必需字段有值
- [ ] 枚举值有效
- [ ] 外键引用存在
- [ ] 约束条件满足

### 6.4 性能

- [ ] 查询响应时间符合要求
- [ ] 并发操作正常
- [ ] 数据库连接池稳定

### 6.5 测试

- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 端到端测试通过
- [ ] 性能测试通过

## 7. 风险评估

### 7.1 高风险

- **数据丢失**: 迁移过程中可能丢失数据
  - **缓解**: 完整备份 + 回滚脚本
  
- **系统停机**: 迁移期间服务不可用
  - **缓解**: 选择低峰时段 + 快速迁移

### 7.2 中风险

- **性能下降**: 新架构可能影响性能
  - **缓解**: 性能测试 + 索引优化
  
- **兼容性问题**: 现有功能可能受影响
  - **缓解**: 完整的回归测试

### 7.3 低风险

- **用户体验**: 用户可能注意到变化
  - **缓解**: 保持 API 响应格式一致

## 8. 成功指标

- 100% 任务数据持久化到数据库
- 0 数据丢失
- API 响应时间 < 200ms
- 系统停机时间 < 10 分钟
- 0 回滚操作
- 所有测试通过

## 9. 时间线

- **第 1 天**: 创建迁移脚本
- **第 2 天**: 更新 API 代码
- **第 3 天**: 测试和验证
- **第 4 天**: 执行迁移
- **第 5 天**: 监控和优化

## 10. 相关文档

- `文档/问题修复/任务数据库架构不匹配-诊断.md`
- `文档/问题修复/任务加载失败-最终解决方案.md`
- `src/database/models.py`
- `src/database/task_extensions.py`
- `src/api/tasks.py`
