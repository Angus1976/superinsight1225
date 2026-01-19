# API 注册修复 - 需求文档

## 1. 概述

**目标**: 修复所有未注册的 API 路由，确保前端页面能够正常访问后端服务。

**背景**: 通过全面审计发现，有 35个 API 文件已实现但未在 FastAPI 应用中注册，导致前端页面出现 404 错误或功能不可用。

## 2. 用户故事

### 2.1 License 模块用户

**As a** 系统管理员  
**I want** 能够访问许可证管理功能  
**So that** 我可以激活、监控和管理系统许可证

**Priority**: P0 (紧急)

**Acceptance Criteria** (EARS):
- WHEN 用户访问 `/license` 页面，THEN 应该能够看到许可证概览
- WHEN 用户访问 `/license/activate` 页面，THEN 应该能够激活新许可证
- WHEN 用户访问 `/license/usage` 页面，THEN 应该能够查看许可证使用情况
- WHERE 许可证 API 未注册，THEN 所有许可证功能不可用

### 2.2 Quality 模块用户

**As a** 质量管理员  
**I want** 能够管理质量规则和查看质量报告  
**So that** 我可以监控和改进数据质量

**Priority**: P0 (紧急)

**Acceptance Criteria** (EARS):
- WHEN 用户访问 `/quality/rules` 页面，THEN 应该能够创建和管理质量规则
- WHEN 用户访问 `/quality/reports` 页面，THEN 应该能够查看质量报告
- WHEN 用户访问 `/quality/workflow/tasks` 页面，THEN 应该能够管理质量改进工单
- WHERE 质量子模块 API 未注册，THEN 相关功能不可用

### 2.3 Augmentation 模块用户

**As a** 数据科学家  
**I want** 能够使用数据增强功能  
**So that** 我可以扩充训练数据集

**Priority**: P0 (紧急)

**Acceptance Criteria** (EARS):
- WHEN 用户访问 `/augmentation` 页面，THEN 应该能够配置数据增强策略
- WHEN 用户访问 `/augmentation/samples` 页面，THEN 应该能够查看增强样本
- WHERE 数据增强 API 未注册，THEN 整个模块不可用

### 2.4 Security 子模块用户

**As a** 安全管理员  
**I want** 能够管理会话、SSO、RBAC 和数据权限  
**So that** 我可以确保系统安全性

**Priority**: P1 (高)

**Acceptance Criteria** (EARS):
- WHEN 用户访问安全子模块页面，THEN 应该能够管理相应的安全功能
- WHERE 安全子模块 API 未注册，THEN 高级安全功能不可用

### 2.5 系统开发者

**As a** 系统开发者  
**I want** 有清晰的 API 注册规范和检查流程  
**So that** 我可以避免未来出现类似问题

**Priority**: P1 (高)

**Acceptance Criteria** (EARS):
- WHEN 添加新 API 文件，THEN 应该有明确的注册步骤
- WHEN 部署新版本，THEN 应该有自动化检查确保所有 API 已注册
- WHERE API 注册缺失，THEN 应该在启动时给出明确警告

## 3. 非功能性需求

### 3.1 性能要求
- API 注册不应显著增加应用启动时间（< 2秒增量）
- 失败的 API 注册不应阻塞其他 API 的加载

### 3.2 可靠性要求
- 单个 API 注册失败不应导致整个应用崩溃
- 应该有详细的日志记录每个 API 的注册状态

### 3.3 可维护性要求
- API 注册代码应该易于理解和修改
- 应该有清晰的注释说明每个 API 的用途

### 3.4 兼容性要求
- 新注册的 API 应该与现有 API 路由不冲突
- 应该保持向后兼容性

## 4. 依赖关系

### 4.1 前置依赖
- FastAPI 应用已正常运行
- 所有 API 文件已实现
- 前端路由已配置

### 4.2 后置依赖
- 前端页面需要更新以使用新注册的 API
- 可能需要更新 API 文档

## 5. 约束条件

### 5.1 技术约束
- 必须使用 FastAPI 的 `include_router` 方法
- 必须遵循现有的错误处理模式
- 必须保持现有的日志格式

### 5.2 业务约束
- 修复必须在不影响现有功能的前提下进行
- 必须经过充分测试后才能部署到生产环境

## 6. 风险评估

### 6.1 技术风险
- **风险**: API 路由冲突
  - **影响**: 高
  - **概率**: 低
  - **缓解**: 在注册前检查路由冲突

- **风险**: API 依赖缺失
  - **影响**: 中
  - **概率**: 中
  - **缓解**: 使用 try-except 包装，记录详细错误

### 6.2 业务风险
- **风险**: 新注册的 API 影响现有功能
  - **影响**: 高
  - **概率**: 低
  - **缓解**: 充分测试，分阶段部署

## 7. 成功指标

### 7.1 功能指标
- ✅ 所有高优先级 API（12个）成功注册
- ✅ 所有前端页面能够正常加载数据
- ✅ 无 404 错误

### 7.2 质量指标
- ✅ 所有 API 注册都有错误处理
- ✅ 所有 API 注册都有日志记录
- ✅ 代码通过 TypeScript 和 Python 类型检查

### 7.3 性能指标
- ✅ 应用启动时间增加 < 2秒
- ✅ API 响应时间无显著变化

## 8. 验收标准

### 8.1 License 模块
- [ ] `/api/v1/license` 端点可访问
- [ ] `/api/v1/license/usage` 端点可访问
- [ ] `/api/v1/license/activation` 端点可访问
- [ ] 前端 License 页面正常显示数据

### 8.2 Quality 模块
- [ ] `/api/v1/quality/rules` 端点可访问
- [ ] `/api/v1/quality/reports` 端点可访问
- [ ] `/api/v1/quality/workflow` 端点可访问
- [ ] 前端 Quality 子页面正常显示数据

### 8.3 Augmentation 模块
- [ ] `/api/v1/augmentation` 端点可访问
- [ ] 前端 Augmentation 页面正常显示数据

### 8.4 Security 子模块
- [ ] `/api/v1/security/sessions` 端点可访问
- [ ] `/api/v1/security/sso` 端点可访问
- [ ] `/api/v1/security/rbac` 端点可访问
- [ ] `/api/v1/security/data-permissions` 端点可访问

### 8.5 系统级验收
- [ ] 应用启动无错误
- [ ] 所有 API 注册日志正常
- [ ] `/api/info` 端点返回完整的 API 列表
- [ ] 前端所有页面可访问

---

**文档版本**: 1.0  
**创建日期**: 2026-01-19  
**状态**: 待审批
