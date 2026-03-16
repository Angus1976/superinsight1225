---
inclusion: manual
---

# Python/FastAPI 最佳实践 (Python FastAPI Patterns)

**Version**: 1.0
**Status**: ✅ Active
**Last Updated**: 2026-03-16
**Priority**: HIGH
**来源**: 参考 everything-claude-code python-patterns + backend-patterns，适配本项目
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则

**类型安全 > 显式依赖 > 异步优先 > 防御性编程**

---

## 🎯 FastAPI 路由规范

### 路由组织
```python
# ✅ 按领域组织路由
# src/api/v1/annotation.py
router = APIRouter(prefix="/api/v1/annotations", tags=["annotations"])

@router.get("/{annotation_id}", response_model=AnnotationResponse)
async def get_annotation(
    annotation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnnotationResponse:
    """获取标注详情"""
    ...
```

### 依赖注入
```python
# ✅ 使用 Depends 注入依赖
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    ...

async def require_permission(permission: str):
    async def checker(user: User = Depends(get_current_user)):
        if not user.has_permission(permission):
            raise HTTPException(403, "Permission denied")
        return user
    return checker
```

### 响应模型
```python
# ✅ 统一响应格式
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
```

---

## 🔧 异步模式

### 数据库操作
```python
# ✅ 异步 SQLAlchemy
async with async_session() as session:
    result = await session.execute(
        select(Annotation).where(Annotation.tenant_id == tenant_id)
    )
    annotations = result.scalars().all()

# ❌ 禁止在异步上下文中使用同步操作
# 详见 async-sync-safety-quick-reference.md
```

### 后台任务
```python
# ✅ 轻量任务用 BackgroundTasks
@router.post("/annotations/batch")
async def batch_annotate(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(process_batch, request)
    return {"status": "accepted"}

# ✅ 重量任务用 Celery
@celery_app.task(bind=True, max_retries=3)
def process_large_dataset(self, dataset_id: int):
    try:
        ...
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
```

---

## 📋 错误处理

```python
# ✅ 自定义业务异常
class AnnotationNotFoundError(Exception):
    def __init__(self, annotation_id: int):
        self.annotation_id = annotation_id
        super().__init__(f"Annotation {annotation_id} not found")

# ✅ 全局异常处理器
@app.exception_handler(AnnotationNotFoundError)
async def annotation_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"code": 404, "message": str(exc), "data": None},
    )
```

---

## 🧪 测试模式

```python
# ✅ 使用 pytest + httpx 测试 FastAPI
import pytest
from httpx import AsyncClient

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_get_annotation(client, sample_annotation):
    response = await client.get(f"/api/v1/annotations/{sample_annotation.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
```

---

## ⚠️ 常见陷阱

| 陷阱 | 解决方案 |
|------|----------|
| 可变默认参数 | 使用 `None` + 函数内初始化 |
| 异步中调用同步 IO | 使用 `run_in_executor` 或 Celery |
| 未关闭数据库连接 | 使用 `async with` 上下文管理器 |
| 循环导入 | 延迟导入或重组模块结构 |
| N+1 查询 | 使用 `selectinload` / `joinedload` |

---

## 🔗 相关资源

- **异步安全**: `.kiro/rules/async-sync-safety-quick-reference.md`
- **代码质量**: `.kiro/rules/coding-quality-standards.md`
- **API 设计**: `.kiro/rules/api-design-patterns.md`
