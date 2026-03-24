# LS 反向同步 实施任务

## 任务列表

### Task 1: 后端 - 新增同步端点
- [x] 在 `src/api/label_studio_api.py` 添加 `SyncAnnotationsResponse` 模型
- [x] 添加 `POST /projects/{project_id}/sync-annotations` 端点
- [x] 端点调用 `export_annotations()` 获取 LS 标注数据
- [x] 同步后更新 TaskModel 的 `label_studio_annotation_count`、`label_studio_last_sync`、`completed_items`、`progress`
- 文件: `src/api/label_studio_api.py`

### Task 2: 后端 - 修复 _sync_annotations_to_db 回退逻辑
- [x] 在 `_sync_annotations_to_db` 中增加通过 `project_id` 查找 TaskModel 的回退逻辑
- [x] 当 `meta.superinsight_task_id` 和 `data.task_id` 都不存在时，用 `label_studio_project_id` 匹配
- 文件: `src/label_studio/integration.py`

### Task 3: 前端 - API 常量与 Service
- [x] 在 `frontend/src/constants/api.ts` 的 `LABEL_STUDIO` 中添加 `SYNC_ANNOTATIONS`
- [x] 在 `frontend/src/services/labelStudioService.ts` 添加 `SyncAnnotationsResponse` 类型和 `syncAnnotations()` 方法
- 文件: `frontend/src/constants/api.ts`, `frontend/src/services/labelStudioService.ts`

### Task 4: 前端 - TaskAnnotate 页面修改
- [x] 添加 `handleSyncAnnotations` 回调
- [x] 在工具栏添加"同步标注结果"按钮
- [x] 移除 `handleAnnotationCreate` 中对不存在代理端点的调用，改为提示用户在 LS 中标注后同步
- [x] 移除 `handleAnnotationUpdate` 中对不存在代理端点的调用
- [x] 同步成功后刷新页面数据和进度
- 文件: `frontend/src/pages/Tasks/TaskAnnotate.tsx`

### Task 5: i18n 翻译
- [x] 在 `frontend/src/locales/zh/tasks.json` 添加同步相关翻译键
- [x] 在 `frontend/src/locales/en/tasks.json` 添加对应英文翻译
- 文件: `frontend/src/locales/zh/tasks.json`, `frontend/src/locales/en/tasks.json`

## 依赖关系

```
Task 1 (后端端点) ← Task 2 (回退逻辑) 可并行
Task 3 (前端常量/Service) ← 依赖 Task 1 的 API 定义
Task 4 (页面修改) ← 依赖 Task 3
Task 5 (i18n) ← 与 Task 4 并行
```

## 验证方式

1. 在 LS 中完成标注
2. 回到 SuperInsight 标注页面，点击"同步标注结果"
3. 验证 TaskModel.annotations 已更新
4. 验证进度统计已更新
5. 验证中英文翻译正确显示
