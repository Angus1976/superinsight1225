---
inclusion: manual
---

# API 设计规范 (API Design Patterns)

**Version**: 1.0
**Status**: ✅ Active
**Last Updated**: 2026-03-16
**Priority**: HIGH
**来源**: 参考 everything-claude-code api-design skill，适配本项目
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则

**一致性 > 可发现性 > 向后兼容 > 简洁性**

---

## 🎯 URL 设计

### 规范
```
GET    /api/v1/annotations          # 列表
POST   /api/v1/annotations          # 创建
GET    /api/v1/annotations/{id}     # 详情
PUT    /api/v1/annotations/{id}     # 全量更新
PATCH  /api/v1/annotations/{id}     # 部分更新
DELETE /api/v1/annotations/{id}     # 删除
```

### 规则
- 使用复数名词：`/annotations` 而非 `/annotation`
- 嵌套不超过 2 层：`/projects/{id}/annotations`
- 动作用动词子资源：`POST /annotations/{id}/approve`
- 版本号在 URL 中：`/api/v1/`

---

## 📄 分页

```python
# ✅ 标准分页参数
@router.get("/annotations", response_model=PaginatedResponse[AnnotationResponse])
async def list_annotations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    ...
```

### 响应格式
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "total": 150,
    "page": 1,
    "page_size": 20
  }
}
```

---

## ❌ 错误响应

### 统一错误格式
```json
{
  "code": 422,
  "message": "Validation failed",
  "data": null,
  "errors": [
    {"field": "email", "message": "Invalid email format"}
  ]
}
```

### HTTP 状态码使用
| 状态码 | 场景 |
|--------|------|
| 200 | 成功（GET/PUT/PATCH/DELETE） |
| 201 | 创建成功（POST） |
| 204 | 删除成功（无返回体） |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 验证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

---

## 🔍 过滤和搜索

```python
# ✅ 查询参数过滤
@router.get("/annotations")
async def list_annotations(
    status: Optional[str] = Query(None, description="状态过滤"),
    annotator_id: Optional[int] = Query(None, description="标注员过滤"),
    created_after: Optional[datetime] = Query(None, description="创建时间起"),
    created_before: Optional[datetime] = Query(None, description="创建时间止"),
    q: Optional[str] = Query(None, description="全文搜索"),
):
    ...
```

---

## 🔒 安全要求

- 所有端点需要 JWT 认证（除 `/health`、`/login`）
- 写操作需要 RBAC 权限检查
- 列表查询必须包含 `tenant_id` 过滤
- 批量操作限制数量（如 max 100 条/次）
- Rate limiting：普通用户 60 req/min，管理员 200 req/min

---

## 🔗 相关资源

- **Python/FastAPI 模式**: `.kiro/rules/python-fastapi-patterns.md`
- **安全审查**: `.kiro/rules/security-review-checklist.md`
