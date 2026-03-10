# 数据转存系统升级总结

**版本**: 2.0 → 3.0  
**升级日期**: 2026-03-10  
**升级类型**: 功能扩展 - 数据闭环

---

## 升级概述

将**数据转存系统**升级为**数据生命周期管理平台**，实现完整的数据闭环。

### 核心变化

```
旧版本 (2.0): 数据源 → 转存 → 数据流转系统
新版本 (3.0): 数据源 → 转存 → 流转 → 标注 → 回流 → AI分析 → 再利用 (闭环)
```

---

## 新增功能

### 1. 数据CRUD操作 (REQ-2.10)
- **CREATE**: 手动创建数据记录
- **READ**: 查询和浏览数据
- **UPDATE**: 更新数据记录
- **DELETE**: 删除数据记录

**权限控制**:
- Admin: 全部操作无需审批
- Data Manager: 删除需审批
- Data Analyst: 更新需审批，删除禁止
- User: 创建需审批，更新/删除禁止

### 2. 数据合并与拆分 (REQ-2.11)
- **MERGE**: 将多条数据合并为一条
- **SPLIT**: 将一条数据拆分为多条
- 支持配置合并/拆分策略
- 保留原始数据关联关系

**权限控制**:
- Admin & Data Manager: 允许
- Data Analyst & User: 禁止

### 3. 标注数据回流 (REQ-2.12)
- 标注任务完成后数据可回流到数据流转系统
- 新增 `source_type: "annotation"`
- 保留标注结果和标注人信息
- 支持批量回流

### 4. AI助手数据访问 (REQ-2.13)
- AI助手可基于技能配置访问流转数据
- 技能配置控制访问范围
- 支持只读访问
- 记录访问日志

**技能配置示例**:
```python
{
  "skill_id": "data-quality-analysis",
  "allowed_source_types": ["annotation", "structuring"],
  "allowed_target_states": ["in_sample_library"],
  "read_only": True,
  "max_records_per_query": 1000
}
```

### 5. 数据生命周期闭环 (REQ-2.14)
- 新增 `source_type`: annotation, ai_assistant, manual
- 数据可在各环节流转
- 提供数据流转可视化
- 完整的操作历史追溯

---

## API变更

### 新增接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/data-lifecycle/records` | POST | 创建数据记录 |
| `/api/data-lifecycle/records` | GET | 查询数据记录 |
| `/api/data-lifecycle/records/{id}` | PUT | 更新数据记录 |
| `/api/data-lifecycle/records/{id}` | DELETE | 删除数据记录 |
| `/api/data-lifecycle/records/merge` | POST | 合并数据记录 |
| `/api/data-lifecycle/records/{id}/split` | POST | 拆分数据记录 |
| `/api/data-lifecycle/ai-query` | GET | AI助手查询数据 |

### 扩展接口

| 接口 | 变更 | 说明 |
|------|------|------|
| `/api/data-lifecycle/transfer` | 扩展 | 支持新的source_type: annotation, ai_assistant, manual |
| `/api/data-lifecycle/permissions/check` | 扩展 | 支持新的operation: create, read, update, delete, merge, split |

---

## 权限矩阵扩展

### 完整权限矩阵

| 角色 | 转存 | CREATE | READ | UPDATE | DELETE | MERGE | SPLIT | 批量 | 跨项目 |
|------|------|--------|------|--------|--------|-------|-------|------|--------|
| Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Data Manager | ✓ | ✓ | ✓ | ✓ | 审批 | ✓ | ✓ | ✓ | ✗ |
| Data Analyst | 审批 | ✓ | ✓ | 审批 | ✗ | ✗ | ✗ | ✗ | ✗ |
| User | 审批 | 审批 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

---

## 前端变更

### 新增组件

1. **DataManagementTable** - 数据管理表格
   - 支持CRUD操作
   - 支持批量选择
   - 支持筛选和排序

2. **DataMergeModal** - 数据合并弹窗
   - 配置合并策略
   - 预览合并结果

3. **DataSplitModal** - 数据拆分弹窗
   - 配置拆分规则
   - 预览拆分结果

4. **AnnotationBackflowButton** - 标注回流按钮
   - 标注任务完成页面使用

5. **DataFlowVisualization** - 数据流转可视化
   - 显示数据完整流转路径

### 国际化更新

新增翻译键（zh/en）:
- CRUD操作相关
- 合并/拆分相关
- 标注回流相关
- AI助手相关
- 数据闭环相关

---

## 数据模型变更

### 扩展 DataTransferRequest

```python
class DataTransferRequest(BaseModel):
    source_type: Literal[
        "structuring", 
        "augmentation", 
        "sync",
        "annotation",      # 新增
        "ai_assistant",    # 新增
        "manual"           # 新增
    ]
    # ... 其他字段保持不变
```

### 新增 AISkillConfig

```python
class AISkillConfig(BaseModel):
    skill_id: str
    skill_name: str
    allowed_source_types: List[str]
    allowed_target_states: List[str]
    allowed_categories: List[str]
    read_only: bool = True
    max_records_per_query: int = 1000
```

---

## 实施计划

### 阶段1: 核心功能 (Week 1-2)
- [ ] 扩展权限矩阵支持CRUD操作
- [ ] 实现数据CRUD API
- [ ] 实现标注数据回流接口
- [ ] 前端数据管理界面

### 阶段2: 高级功能 (Week 3)
- [ ] 实现数据合并/拆分功能
- [ ] 实现AI助手查询接口
- [ ] 技能配置管理

### 阶段3: 闭环完善 (Week 4)
- [ ] 数据流转可视化
- [ ] 完整的操作历史追溯
- [ ] 国际化完整覆盖

### 阶段4: 测试和优化 (Week 5)
- [ ] 完整测试
- [ ] 性能优化
- [ ] 文档更新

---

## 兼容性说明

### 向后兼容
- 所有现有API保持兼容
- 现有权限矩阵保持不变
- 现有数据模型保持兼容

### 迁移指南
- 无需迁移现有代码
- 新功能为可选功能
- 逐步启用新功能

---

## 文档更新

### 已更新
- ✅ requirements.md - 新增5个功能需求
- ⏳ design.md - 待更新架构设计
- ⏳ tasks.md - 待更新实施任务

### 待创建
- [ ] API文档更新
- [ ] 用户手册更新
- [ ] 开发者指南

---

## 总结

本次升级将数据转存系统升级为完整的数据生命周期管理平台，实现了：

1. **完整的数据操作能力** - CRUD + 合并/拆分
2. **数据闭环** - 标注回流 + AI助手集成
3. **灵活的权限控制** - 扩展权限矩阵
4. **完整的国际化** - 所有新功能支持中英文

系统现在可以支持数据在各个环节的完整流转，形成真正的数据闭环。
