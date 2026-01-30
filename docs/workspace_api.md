# Label Studio Enterprise Workspace API 文档

**版本**: 1.0
**最后更新**: 2026-01-30
**基础路径**: `/api/ls-workspaces`

## 概述

Label Studio Enterprise Workspace API 提供了完整的工作空间管理功能，包括：

- Workspace（工作空间）CRUD 操作
- 成员管理和角色分配
- 项目关联管理
- 基于角色的访问控制 (RBAC)

所有端点都需要 JWT Bearer Token 认证。

## 认证

所有 API 请求需要在 Header 中包含有效的 JWT Token：

```
Authorization: Bearer <your-jwt-token>
```

### 认证错误响应

| 状态码 | 描述 |
|--------|------|
| 401 | 未认证或 Token 无效/过期 |
| 403 | 权限不足 |

---

## 角色和权限

### 角色层级

| 角色 | 描述 | 权限级别 |
|------|------|----------|
| `owner` | 工作空间所有者 | 最高 - 所有权限 |
| `admin` | 管理员 | 高 - 除删除工作空间外的所有权限 |
| `manager` | 经理 | 中 - 项目和任务管理 |
| `reviewer` | 审核员 | 低 - 查看和审核 |
| `annotator` | 标注员 | 最低 - 仅标注 |

### 权限矩阵

| 权限 | Owner | Admin | Manager | Reviewer | Annotator |
|------|-------|-------|---------|----------|-----------|
| `workspace:view` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `workspace:edit` | ✓ | ✓ | - | - | - |
| `workspace:delete` | ✓ | - | - | - | - |
| `workspace:manage_members` | ✓ | ✓ | - | - | - |
| `project:view` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `project:create` | ✓ | ✓ | ✓ | - | - |
| `project:edit` | ✓ | ✓ | ✓ | - | - |
| `project:delete` | ✓ | ✓ | - | - | - |
| `project:manage_members` | ✓ | ✓ | ✓ | - | - |
| `task:view` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `task:annotate` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `task:review` | ✓ | ✓ | ✓ | ✓ | - |
| `task:assign` | ✓ | ✓ | ✓ | - | - |
| `data:export` | ✓ | ✓ | ✓ | ✓ | - |
| `data:import` | ✓ | ✓ | - | - | - |

---

## Workspace 端点

### 创建工作空间

创建新的 Label Studio 工作空间。当前用户自动成为工作空间的 Owner。

```
POST /api/ls-workspaces
```

**请求体**

```json
{
  "name": "研发部门工作空间",
  "description": "用于研发部门的数据标注项目",
  "settings": {
    "max_annotators": 20,
    "auto_assign": true
  }
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `name` | string | 是 | 工作空间名称 (1-255 字符，唯一) |
| `description` | string | 否 | 工作空间描述 (最大 2000 字符) |
| `settings` | object | 否 | 自定义设置 |

**成功响应** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "研发部门工作空间",
  "description": "用于研发部门的数据标注项目",
  "owner_id": "123e4567-e89b-12d3-a456-426614174000",
  "settings": {
    "max_annotators": 20,
    "auto_assign": true
  },
  "is_active": true,
  "is_deleted": false,
  "created_at": "2026-01-30T10:00:00Z",
  "updated_at": "2026-01-30T10:00:00Z",
  "member_count": 1,
  "project_count": 0
}
```

**错误响应**

| 状态码 | 描述 |
|--------|------|
| 400 | 请求参数无效 |
| 409 | 工作空间名称已存在 |

---

### 获取工作空间列表

获取当前用户有权限访问的所有工作空间。

```
GET /api/ls-workspaces
```

**查询参数**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `include_inactive` | boolean | false | 是否包含已停用的工作空间 |

**成功响应** `200 OK`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "研发部门工作空间",
      "description": "用于研发部门的数据标注项目",
      "owner_id": "123e4567-e89b-12d3-a456-426614174000",
      "settings": {},
      "is_active": true,
      "is_deleted": false,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z",
      "member_count": 5,
      "project_count": 3
    }
  ],
  "total": 1
}
```

---

### 获取工作空间详情

获取指定工作空间的详细信息。

```
GET /api/ls-workspaces/{workspace_id}
```

**路径参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| `workspace_id` | UUID | 工作空间 ID |

**成功响应** `200 OK`

返回 `WorkspaceResponse` 对象。

**错误响应**

| 状态码 | 描述 |
|--------|------|
| 403 | 无权访问此工作空间 |
| 404 | 工作空间不存在 |

---

### 更新工作空间

更新工作空间信息。需要 `workspace:edit` 权限。

```
PUT /api/ls-workspaces/{workspace_id}
```

**请求体**

```json
{
  "name": "新名称",
  "description": "更新后的描述",
  "settings": {
    "max_annotators": 30
  },
  "is_active": true
}
```

所有字段都是可选的，只会更新提供的字段。

**成功响应** `200 OK`

返回更新后的 `WorkspaceResponse` 对象。

**错误响应**

| 状态码 | 描述 |
|--------|------|
| 403 | 无编辑权限 |
| 404 | 工作空间不存在 |
| 409 | 新名称已被占用 |

---

### 删除工作空间

删除工作空间（软删除）。需要 `workspace:delete` 权限（仅 Owner）。

```
DELETE /api/ls-workspaces/{workspace_id}
```

**查询参数**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `hard_delete` | boolean | false | 是否物理删除 |

**成功响应** `204 No Content`

**错误响应**

| 状态码 | 描述 |
|--------|------|
| 403 | 无删除权限 |
| 404 | 工作空间不存在 |
| 409 | 工作空间包含项目，无法删除 |

---

### 获取用户权限

获取当前用户在指定工作空间中的权限列表。

```
GET /api/ls-workspaces/{workspace_id}/permissions
```

**成功响应** `200 OK`

```json
{
  "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "role": "admin",
  "permissions": [
    "workspace:view",
    "workspace:edit",
    "workspace:manage_members",
    "project:view",
    "project:create",
    "project:edit",
    "project:delete",
    "project:manage_members",
    "task:view",
    "task:annotate",
    "task:review",
    "task:assign",
    "data:export",
    "data:import"
  ]
}
```

---

## 成员管理端点

### 获取成员列表

获取工作空间的所有成员。需要 `workspace:view` 权限。

```
GET /api/ls-workspaces/{workspace_id}/members
```

**成功响应** `200 OK`

```json
{
  "items": [
    {
      "id": "member-uuid-1",
      "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "123e4567-e89b-12d3-a456-426614174000",
      "role": "owner",
      "is_active": true,
      "joined_at": "2026-01-30T10:00:00Z",
      "user_email": "owner@example.com",
      "user_name": "张三"
    },
    {
      "id": "member-uuid-2",
      "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "456e7890-e89b-12d3-a456-426614174001",
      "role": "annotator",
      "is_active": true,
      "joined_at": "2026-01-30T11:00:00Z",
      "user_email": "annotator@example.com",
      "user_name": "李四"
    }
  ],
  "total": 2
}
```

---

### 添加成员

向工作空间添加新成员。需要 `workspace:manage_members` 权限。

```
POST /api/ls-workspaces/{workspace_id}/members
```

**请求体**

```json
{
  "user_id": "456e7890-e89b-12d3-a456-426614174001",
  "role": "annotator"
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `user_id` | UUID | 是 | 要添加的用户 ID |
| `role` | string | 否 | 角色，默认 `annotator` |

**成功响应** `201 Created`

返回 `MemberResponse` 对象。

**错误响应**

| 状态码 | 描述 |
|--------|------|
| 400 | 无效的角色 |
| 403 | 无管理成员权限 |
| 404 | 用户不存在 |
| 409 | 用户已是成员 |

---

### 更新成员角色

更新成员的角色。需要 `workspace:manage_members` 权限。

```
PUT /api/ls-workspaces/{workspace_id}/members/{user_id}
```

**请求体**

```json
{
  "role": "reviewer"
}
```

**成功响应** `200 OK`

返回更新后的 `MemberResponse` 对象。

**错误响应**

| 状态码 | 描述 |
|--------|------|
| 400 | 无效的角色 |
| 403 | 无权修改此成员角色（如降级 Owner） |
| 404 | 成员不存在 |
| 409 | 不能降级最后一个 Owner |

---

### 移除成员

从工作空间移除成员。需要 `workspace:manage_members` 权限。

```
DELETE /api/ls-workspaces/{workspace_id}/members/{user_id}
```

**成功响应** `204 No Content`

**错误响应**

| 状态码 | 描述 |
|--------|------|
| 403 | 无权移除此成员 |
| 404 | 成员不存在 |
| 409 | 不能移除最后一个 Owner |

---

## 项目关联端点

### 获取关联项目列表

获取工作空间中关联的所有项目。需要 `project:view` 权限。

```
GET /api/ls-workspaces/{workspace_id}/projects
```

**成功响应** `200 OK`

```json
{
  "items": [
    {
      "id": "project-assoc-uuid",
      "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
      "label_studio_project_id": "123",
      "superinsight_project_id": null,
      "metadata": {
        "workspace_name": "研发部门工作空间"
      },
      "created_at": "2026-01-30T12:00:00Z",
      "updated_at": "2026-01-30T12:00:00Z",
      "project_title": "图像分类项目",
      "project_description": "用于产品图像分类"
    }
  ],
  "total": 1
}
```

---

### 关联项目

将 Label Studio 项目关联到工作空间。需要 `project:create` 权限。

```
POST /api/ls-workspaces/{workspace_id}/projects
```

**请求体**

```json
{
  "label_studio_project_id": "123",
  "superinsight_project_id": "optional-uuid",
  "metadata": {
    "custom_field": "custom_value"
  }
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `label_studio_project_id` | string | 是 | Label Studio 项目 ID |
| `superinsight_project_id` | string | 否 | SuperInsight 项目 ID |
| `metadata` | object | 否 | 额外元数据 |

**成功响应** `201 Created`

返回 `WorkspaceProjectResponse` 对象。

**错误响应**

| 状态码 | 描述 |
|--------|------|
| 403 | 无创建项目权限 |
| 404 | Label Studio 项目不存在 |
| 409 | 项目已关联到其他工作空间 |

---

### 获取关联项目详情

获取指定关联项目的详细信息。

```
GET /api/ls-workspaces/{workspace_id}/projects/{project_id}
```

**成功响应** `200 OK`

返回 `WorkspaceProjectResponse` 对象。

---

### 取消项目关联

从工作空间移除项目关联。需要 `project:delete` 权限。

```
DELETE /api/ls-workspaces/{workspace_id}/projects/{project_id}
```

**成功响应** `204 No Content`

**错误响应**

| 状态码 | 描述 |
|--------|------|
| 403 | 无删除项目权限 |
| 404 | 项目关联不存在 |

---

## 数据模型

### WorkspaceResponse

```typescript
interface WorkspaceResponse {
  id: string;              // UUID
  name: string;            // 工作空间名称
  description?: string;    // 描述
  owner_id: string;        // 所有者用户 ID
  settings: object;        // 自定义设置
  is_active: boolean;      // 是否启用
  is_deleted: boolean;     // 是否已删除
  created_at: string;      // ISO 8601 时间戳
  updated_at: string;      // ISO 8601 时间戳
  member_count: number;    // 成员数量
  project_count: number;   // 项目数量
}
```

### MemberResponse

```typescript
interface MemberResponse {
  id: string;              // UUID
  workspace_id: string;    // 工作空间 ID
  user_id: string;         // 用户 ID
  role: string;            // 角色: owner|admin|manager|reviewer|annotator
  is_active: boolean;      // 是否活跃
  joined_at: string;       // 加入时间
  user_email?: string;     // 用户邮箱
  user_name?: string;      // 用户名
}
```

### WorkspaceProjectResponse

```typescript
interface WorkspaceProjectResponse {
  id: string;                       // UUID
  workspace_id: string;             // 工作空间 ID
  label_studio_project_id: string;  // Label Studio 项目 ID
  superinsight_project_id?: string; // SuperInsight 项目 ID
  metadata: object;                 // 额外元数据
  created_at: string;               // 创建时间
  updated_at: string;               // 更新时间
  project_title?: string;           // 项目标题
  project_description?: string;     // 项目描述
}
```

---

## 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "detail": "错误描述信息"
}
```

### 通用错误码

| 状态码 | 描述 |
|--------|------|
| 400 | 请求参数无效 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |

---

## 使用示例

### cURL 示例

**创建工作空间**

```bash
curl -X POST "https://api.example.com/api/ls-workspaces" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "数据标注项目",
    "description": "AI 训练数据标注"
  }'
```

**添加成员**

```bash
curl -X POST "https://api.example.com/api/ls-workspaces/{workspace_id}/members" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "role": "annotator"
  }'
```

**关联项目**

```bash
curl -X POST "https://api.example.com/api/ls-workspaces/{workspace_id}/projects" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "label_studio_project_id": "123"
  }'
```

### JavaScript/TypeScript 示例

```typescript
// 使用 fetch API
const createWorkspace = async (token: string, name: string) => {
  const response = await fetch('/api/ls-workspaces', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name }),
  });

  if (!response.ok) {
    throw new Error(`Error: ${response.status}`);
  }

  return response.json();
};

// 使用示例
const workspace = await createWorkspace(token, '新工作空间');
console.log(`Created workspace: ${workspace.id}`);
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-01-30 | 初始版本 |

---

## 相关文档

- [用户手册](./workspace_user_guide.md)
- [运维手册](./workspace_deployment.md)
- [RBAC 权限详解](./rbac_permissions.md)
