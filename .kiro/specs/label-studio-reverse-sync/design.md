# LS 反向同步 技术设计

## 架构概览

```
用户在 LS 完成标注
       ↓
前端点击"同步标注" / 自动触发
       ↓
POST /api/label-studio/projects/{project_id}/sync-annotations
       ↓
后端调用 export_annotations(project_id)
       ↓
LS API: GET /api/projects/{project_id}/export
       ↓
_sync_annotations_to_db(project_id, data)
       ↓
更新 TaskModel (annotations, progress, counts)
       ↓
返回同步结果给前端
```

## 后端设计

### 1. 新增端点: `POST /api/label-studio/projects/{project_id}/sync-annotations`

文件: `src/api/label_studio_api.py`

```python
class SyncAnnotationsResponse(BaseModel):
    success: bool
    synced_count: int = 0
    total_annotations: int = 0
    errors: List[str] = []
    synced_at: Optional[str] = None

@router.post("/projects/{project_id}/sync-annotations", response_model=SyncAnnotationsResponse)
async def sync_annotations(
    project_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
```

**逻辑流程**:
1. 验证 project_id 对应的 LS 项目存在
2. 调用 `LabelStudioIntegration.export_annotations(project_id)`
3. 已有的 `export_annotations` 内部会调用 `_sync_annotations_to_db`
4. 查询 DB 中 `label_studio_project_id == project_id` 的 TaskModel
5. 更新 `label_studio_annotation_count`、`label_studio_last_sync`、`completed_items`、`progress`
6. 返回同步结果

### 2. 修复 `_sync_annotations_to_db` 的 task_id 匹配逻辑

当前代码依赖 `annotation['meta']['superinsight_task_id']` 或 `annotation['data']['task_id']` 来匹配任务。如果都找不到，则回退到通过 `label_studio_project_id` 查找 TaskModel。

需要增加回退逻辑:
```python
# 回退: 通过 project_id 查找关联的 TaskModel
if not task_id:
    task_model = db.query(TaskModel).filter(
        TaskModel.label_studio_project_id == project_id
    ).first()
```

### 3. 权限处理

- 使用现有的 `get_current_user` 依赖
- 未配置细粒度权限时，只要登录即可调用（默认管理员权限）
- 后续可通过 RBAC 扩展

## 前端设计

### 1. API 常量 (`frontend/src/constants/api.ts`)

```typescript
SYNC_ANNOTATIONS: (projectId: string) => `/api/label-studio/projects/${projectId}/sync-annotations`,
```

### 2. Service 方法 (`frontend/src/services/labelStudioService.ts`)

```typescript
export interface SyncAnnotationsResponse {
  success: boolean;
  synced_count: number;
  total_annotations: number;
  errors: string[];
  synced_at?: string;
}

async syncAnnotations(projectId: string): Promise<SyncAnnotationsResponse> {
  const response = await apiClient.post<SyncAnnotationsResponse>(
    API_ENDPOINTS.LABEL_STUDIO.SYNC_ANNOTATIONS(projectId)
  );
  return response.data;
}
```

### 3. TaskAnnotate.tsx 修改

- 添加"同步标注结果"按钮（在顶部工具栏同步按钮旁）
- 移除 `handleAnnotationCreate` 和 `handleAnnotationUpdate` 中对不存在端点的调用
- 新增 `handleSyncAnnotations` 回调，调用 `labelStudioService.syncAnnotations()`
- 同步成功后刷新页面数据

### 4. i18n 新增键

命名空间: `tasks`（复用现有 tasks.json）

| 键 | 中文 | 英文 |
|----|------|------|
| `annotate.syncAnnotations` | 同步标注结果 | Sync Annotations |
| `annotate.syncAnnotationsSuccess` | 标注结果同步成功 | Annotations synced successfully |
| `annotate.syncAnnotationsFailed` | 标注结果同步失败 | Failed to sync annotations |
| `annotate.syncedCount` | 已同步 {count} 条标注 | Synced {count} annotations |
| `annotate.noAnnotationsToSync` | 暂无标注结果可同步 | No annotations to sync |

## 不改动的部分

- `export_annotations()` 核心逻辑不变（已验证可用）
- `_sync_annotations_to_db()` 核心逻辑不变，仅增加 task_id 回退匹配
- LS 端无需任何改动
- 现有正向同步流程不受影响
- 不新增 webhook 机制（保持轻量）
