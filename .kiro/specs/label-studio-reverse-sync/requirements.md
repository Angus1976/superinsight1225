# LS 反向同步 (Reverse Sync) 需求文档

## 背景

SuperInsight 平台已实现正向同步（SuperInsight → Label Studio）：创建任务时自动在 LS 创建项目并导入数据。但反向同步（LS → SuperInsight）尚未实现——`export_annotations()` 和 `_sync_annotations_to_db()` 是死代码，前端 `TaskAnnotate.tsx` 调用的标注 CRUD 代理端点在后端不存在（会 404）。

## 目标

实现轻量级"拉取同步"机制，让用户在 LS 完成标注后，标注结果能回传到 SuperInsight 数据库，供后续数据处理流程使用。

## 需求列表

### REQ-1: 标注同步 API 端点
- **描述**: 新增 `POST /api/label-studio/projects/{project_id}/sync-annotations` 端点
- **触发**: 前端手动调用（用户点击"同步标注"按钮或标注完成后自动触发）
- **行为**: 调用已有的 `export_annotations()` → `_sync_annotations_to_db()`，将 LS 标注数据写入 TaskModel.annotations JSONB 字段
- **权限**: 需要登录认证；未配置细粒度权限时默认授权给管理员
- **响应**: 返回同步结果（成功数、失败数、错误信息）

### REQ-2: 更新 TaskModel 标注统计
- **描述**: 同步完成后更新 `label_studio_annotation_count`、`label_studio_last_sync`、`completed_items`、`progress` 字段
- **行为**: 根据 LS 返回的标注数据计算完成进度

### REQ-3: 前端同步按钮与状态展示
- **描述**: 在 `TaskAnnotate.tsx` 页面添加"同步标注结果"按钮
- **行为**: 调用 REQ-1 的 API，展示同步状态（同步中/成功/失败）
- **i18n**: 所有新增可见文本使用 `t()`，同步写入 zh/ 和 en/ 翻译文件

### REQ-4: 清理前端死代码调用
- **描述**: `handleAnnotationCreate` 和 `handleAnnotationUpdate` 当前调用不存在的代理端点
- **行为**: 移除对 `/api/label-studio/projects/{id}/tasks/{id}/annotations` 和 `/api/label-studio/annotations/{id}` 的直接调用，改为引导用户在 LS 中完成标注后点击同步

### REQ-5: API 常量注册
- **描述**: 在 `frontend/src/constants/api.ts` 中注册新端点常量
- **行为**: 添加 `SYNC_ANNOTATIONS` 到 `LABEL_STUDIO` 常量组

### REQ-6: labelStudioService 封装
- **描述**: 在 `labelStudioService.ts` 中封装同步 API 调用方法
- **行为**: 添加 `syncAnnotations(projectId: string)` 方法

## 约束

- 项目已完成 85%+，只做小幅修改，不重写现有功能
- LS 仅作为标注工具，权限管理在 SuperInsight 平台
- 未配置授权时默认授权给管理员
- 数据获取、处理、使用都通过 SuperInsight 平台
- 复用已有的 `export_annotations()` 和 `_sync_annotations_to_db()` 代码
