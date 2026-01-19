# 问题分析报告 - 2026-01-19

## 问题 1: 登录页面缺少"组织"选择

### 现状
- ✅ 前端 `LoginForm` 组件已经实现了组织选择功能
- ✅ 代码逻辑：当 `tenants.length > 0` 时显示组织选择下拉框
- ❌ 后端 `/auth/tenants` 端点返回硬编码的单个租户

### 根本原因
后端 `src/api/auth.py` 中的 `get_tenants()` 函数返回硬编码数据：

```python
@router.get("/tenants")
async def get_tenants():
    """Get available tenants for login."""
    # For now, return a default tenant
    # In a real implementation, this would query the database
    return [
        {
            "id": "default_tenant",
            "name": "Default Tenant",
            "logo": None
        }
    ]
```

### 解决方案
需要实现真正的租户查询逻辑：
1. 从数据库查询所有活跃的租户
2. 返回租户列表供用户选择
3. 或者根据用户名/邮箱查询该用户有权限访问的租户

---

## 问题 2: RoleModel 重复定义导致登录失败

### 现状
- ❌ 登录时返回 500 错误
- ❌ 错误信息：`Multiple classes found for path "RoleModel" in the registry`

### 根本原因

**发现了两个 RoleModel 定义：**

1. **`src/sync/rbac/models.py`** (第 67 行)
   ```python
   class RoleModel(Base):
       __tablename__ = "rbac_roles"
       # ... 定义
   ```

2. **`src/security/rbac_models.py`** (第 44 行)
   ```python
   class RoleModel(Base):
       __tablename__ = "rbac_roles"
       # ... 定义
   ```

**两个类的区别：**
- `src/sync/rbac/models.py`: 使用 `UUID(as_uuid=True)` 和 `JSONB`
- `src/security/rbac_models.py`: 使用 `PostgresUUID(as_uuid=True)` 和 `JSON`

**为什么会导致问题：**
1. 两个文件都从同一个 Base 继承（`src.database.connection.Base`）
2. 两个类都使用相同的表名 `"rbac_roles"`
3. 当应用启动时，两个类都被注册到 SQLAlchemy 的 registry
4. SQLAlchemy 检测到同一个表名有两个不同的类定义，抛出错误

### 为什么之前可以登录？

根据您的描述：
- 在已经登录的环境中，一切正常
- 只是在退出登录后，重新登录时出现问题

**可能的原因：**
1. **会话缓存**：已登录时，SQLAlchemy 的 session 已经初始化，模型已经加载
2. **延迟加载**：登录过程可能触发了某些模块的导入，导致两个 RoleModel 同时被加载
3. **导入顺序**：退出登录后重新登录时，模块的导入顺序可能不同

### 解决方案

**方案 1: 删除重复定义（推荐）**
- 保留 `src/security/rbac_models.py` 中的定义（更完整）
- 删除 `src/sync/rbac/models.py` 中的 RoleModel
- 更新所有导入 `src.sync.rbac.models.RoleModel` 的地方

**方案 2: 使用别名**
- 在其中一个文件中使用不同的类名
- 但这会导致代码混乱，不推荐

**方案 3: 合并模型**
- 将两个模型合并为一个
- 放在统一的位置（如 `src/models/rbac.py`）

---

## 时间线分析

根据您的描述：
- 今天主要在开发 `.kiro/specs/api-registration-fix`
- 在已登录环境中，功能和国际化接近完成
- 退出登录后，重新登录无响应

**可能的触发点：**
1. 某个新的 API 端点或功能导入了 `src.sync.rbac.models`
2. 某个中间件或依赖注入在登录时触发了模块加载
3. 容器重启导致模块加载顺序改变

---

## 建议的修复步骤

### 步骤 1: 修复 RoleModel 重复定义
1. 删除 `src/sync/rbac/models.py` 中的 RoleModel 定义
2. 更新所有导入，统一使用 `src.security.rbac_models.RoleModel`
3. 测试登录功能

### 步骤 2: 实现租户选择功能
1. 实现 `get_tenants()` 的数据库查询逻辑
2. 测试租户选择功能
3. 确保租户选择在登录流程中正常工作

---

**分析完成时间**: 2026-01-19 23:00  
**状态**: 等待确认后执行修复
