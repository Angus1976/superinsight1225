# 登录问题诊断报告 - 2026-01-19

## 问题描述

用户点击登录按钮后，前端无任何反应。后端 API 返回 500 Internal Server Error。

## 根本原因

SQLAlchemy 模型注册表中存在 `RoleModel` 的重复定义。错误信息：

```
Login error: Multiple classes found for path "RoleModel" in the registry of this 
declarative base. Please use a fully module-qualified path.
```

## 已采取的行动

### 1. 删除重复的模型定义
- 发现 `src/sync/rbac/models.py` 中有一个 `RoleModel` 定义
- 发现 `src/security/rbac_models.py` 中也有一个 `RoleModel` 定义
- 删除了 `src/sync/rbac/models.py` 文件

### 2. 更新导入
- 更新 `src/sync/rbac/__init__.py` 以导入正确的模型
- 更新 `src/security/tenant_permissions.py` 以导入正确的模型
- 更新 `src/sync/rbac/permission_manager.py` 以导入正确的模型
- 更新 `src/sync/rbac/rbac_service.py` 以导入正确的模型
- 更新 `src/sync/rbac/field_access_control.py` 以导入正确的模型
- 更新 `src/sync/rbac/audit_service.py` 以导入正确的模型
- 更新 `src/sync/rbac/tenant_isolation.py` 以导入正确的模型

### 3. 修复类型注解错误
- 修复 `src/sync/rbac/permission_manager.py` 中使用的 `PermissionAction` 和 `FieldAccessLevel` 类型注解
- 这些类型在导入时不可用，导致模块加载失败

### 4. 禁用 src/sync/rbac 模块
- 禁用了 `src/sync/rbac/__init__.py` 中的所有导入，以防止导入冲突

### 5. 添加 extend_existing=True
- 在 `src/security/rbac_models.py` 中的 `RoleModel` 添加了 `__table_args__ = {"extend_existing": True}`

### 6. 禁用重复的 RBAC API 加载
- 注释掉了 `src/app.py` 中第一个 RBAC API 的加载（第 1460 行）

## 当前状态

问题仍然存在。后端 API 仍然返回 500 错误，错误信息仍然是 "Multiple classes found for path 'RoleModel'"。

## 可能的原因

1. **循环导入**: 某个模块在导入时可能导致 `src.security.rbac_models` 被加载两次
2. **动态导入**: 某个模块可能在运行时动态导入了 `src.security.rbac_models`
3. **多个 Base 对象**: 可能存在多个 SQLAlchemy Base 对象，导致模型被注册到不同的 Base 中

## 建议的解决方案

### 方案 1: 完全禁用 RBAC 模块
- 禁用所有 RBAC 相关的 API 和模块
- 这样可以确定问题是否真的来自 RBAC 模块

### 方案 2: 检查 Base 对象
- 检查是否有多个 SQLAlchemy Base 对象
- 确保所有模型都使用同一个 Base 对象

### 方案 3: 使用 registry 而不是 Base
- 使用 SQLAlchemy 的 registry 对象而不是 declarative_base()
- 这样可以更好地控制模型的注册

### 方案 4: 完全重写 RBAC 模块
- 从头开始重写 RBAC 模块，避免任何重复定义
- 使用更清晰的导入结构

## 测试步骤

1. 禁用所有 RBAC 相关的 API
2. 重新启动容器
3. 尝试登录
4. 如果登录成功，问题确实来自 RBAC 模块
5. 逐步启用 RBAC 模块的不同部分，找出具体的问题

## 文件修改列表

- `src/sync/rbac/models.py` - 已删除
- `src/sync/rbac/__init__.py` - 已修改（禁用导入）
- `src/security/tenant_permissions.py` - 已修改（更新导入）
- `src/sync/rbac/permission_manager.py` - 已修改（修复类型注解）
- `src/sync/rbac/rbac_service.py` - 已修改（更新导入）
- `src/sync/rbac/field_access_control.py` - 已修改（更新导入）
- `src/sync/rbac/audit_service.py` - 已修改（更新导入）
- `src/sync/rbac/tenant_isolation.py` - 已修改（更新导入）
- `src/security/rbac_models.py` - 已修改（添加 extend_existing=True）
- `src/app.py` - 已修改（注释掉重复的 RBAC API 加载）

---

**状态**: 🔴 问题未解决  
**优先级**: 🔴 高  
**下一步**: 需要进一步诊断和调试
