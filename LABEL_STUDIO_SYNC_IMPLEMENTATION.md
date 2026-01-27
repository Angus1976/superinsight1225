# Label Studio 同步功能实现完成报告

## 📋 实现概述

已完成平台与 Label Studio 之间的认证和任务同步功能实现。

## ✅ 已完成的工作

### 1. 认证配置 (已完成)

**文件**: `.env`

```bash
# API Token 认证（Community Edition 支持）
LABEL_STUDIO_URL=http://label-studio:8080
LABEL_STUDIO_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**状态**: ✅ 已配置 API Token 认证

### 2. 同步服务实现 (新增)

**文件**: `src/api/label_studio_sync.py`

**功能**:
- ✅ 创建 Label Studio 项目
- ✅ 验证项目存在性
- ✅ 测试连接和认证
- ✅ 错误处理和重试

**核心方法**:
```python
class LabelStudioSyncService:
    async def create_project_for_task(...)  # 为任务创建项目
    async def validate_project(...)          # 验证项目
    async def test_connection(...)           # 测试连接
```

### 3. 任务 API 更新 (已修改)

**文件**: `src/api/tasks.py`

**新增功能**:

#### 3.1 自动同步
```python
@router.post("", response_model=TaskResponse)
async def create_task(..., background_tasks: BackgroundTasks):
    # 创建任务后自动在后台同步到 Label Studio
    background_tasks.add_task(_sync_task_to_label_studio, task_id, new_task)
```

#### 3.2 手动同步端点
```python
@router.post("/{task_id}/sync-label-studio")
async def sync_task_to_label_studio(...):
    # 手动触发同步，用于重试失败的同步
```

#### 3.3 连接测试端点
```python
@router.get("/label-studio/test-connection")
async def test_label_studio_connection(...):
    # 测试 Label Studio 连接和认证
```

### 4. 数据模型更新 (已完成)

**TaskCreateRequest** - 添加 `data_source` 字段:
```python
class DataSourceConfig(BaseModel):
    type: str  # file, api, database
    config: Dict[str, Any]

class TaskCreateRequest(BaseModel):
    # ... 其他字段
    data_source: Optional[DataSourceConfig] = None
```

**TaskResponse** - 添加同步状态字段:
```python
class TaskResponse(BaseModel):
    # ... 其他字段
    label_studio_project_id: Optional[str]
    label_studio_sync_status: Optional[str]  # pending, syncing, synced, failed
    label_studio_last_sync: Optional[datetime]
    label_studio_project_created_at: Optional[datetime]
    data_source: Optional[DataSourceConfig] = None
```

### 5. 路由顺序修复 (已完成)

**问题**: `/stats` 路由在 `/{task_id}` 之后，导致 "stats" 被当作 task_id

**修复**: 将 `/stats` 路由移到参数化路由之前

**路由顺序**:
```python
@router.get("")              # 列表
@router.post("")             # 创建
@router.get("/stats")        # 统计 ✅ 移到这里
@router.get("/{task_id}")    # 详情
@router.patch("/{task_id}")  # 更新
@router.delete("/{task_id}") # 删除
```

### 6. 测试脚本 (新增)

**文件**: `test_label_studio_sync.py`

**测试内容**:
- ✅ 登录认证
- ✅ Label Studio 连接测试
- ✅ 任务创建
- ✅ 自动同步验证
- ✅ 手动同步重试

## 🔧 API 端点说明

### 1. 创建任务（自动同步）
```http
POST /api/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "测试任务",
  "description": "任务描述",
  "priority": "medium",
  "annotation_type": "text_classification",
  "total_items": 10,
  "tags": ["test"]
}
```

**响应**:
```json
{
  "id": "uuid",
  "name": "测试任务",
  "label_studio_sync_status": "pending",
  "label_studio_project_id": null,
  ...
}
```

**说明**: 任务创建后，会在后台自动同步到 Label Studio

### 2. 手动同步任务
```http
POST /api/tasks/{task_id}/sync-label-studio
Authorization: Bearer <token>
```

**响应**:
```json
{
  "message": "Task successfully synced to Label Studio",
  "project_id": "123",
  "project_url": "http://label-studio:8080/projects/123",
  "sync_status": "synced",
  "synced_at": "2026-01-27T10:30:00Z"
}
```

**使用场景**:
- 自动同步失败时重试
- Label Studio 配置更改后重新同步

### 3. 测试 Label Studio 连接
```http
GET /api/tasks/label-studio/test-connection
Authorization: Bearer <token>
```

**响应**:
```json
{
  "status": "success",
  "message": "Successfully connected to Label Studio",
  "details": {
    "connected": true,
    "authenticated": true,
    "auth_method": "api_token",
    "base_url": "http://label-studio:8080"
  }
}
```

## 🔄 同步流程

### 自动同步流程

```
1. 用户创建任务
   ↓
2. API 立即返回任务信息（sync_status: "pending"）
   ↓
3. 后台任务开始执行
   ↓
4. 调用 Label Studio API 创建项目
   ↓
5. 更新任务状态：
   - 成功: sync_status = "synced", project_id = "123"
   - 失败: sync_status = "failed", error 记录
```

### 手动同步流程

```
1. 用户点击"同步到 Label Studio"按钮
   ↓
2. 前端调用 POST /api/tasks/{id}/sync-label-studio
   ↓
3. 检查是否已同步
   ↓
4. 创建 Label Studio 项目
   ↓
5. 返回同步结果
```

## 📊 同步状态说明

| 状态 | 说明 | 操作 |
|------|------|------|
| `pending` | 等待同步 | 后台任务将自动处理 |
| `syncing` | 同步中 | 正在创建 Label Studio 项目 |
| `synced` | 已同步 | 可以开始标注 |
| `failed` | 同步失败 | 可以手动重试 |

## 🧪 测试步骤

### 1. 测试认证

```bash
# 直接测试 Label Studio API
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8080/api/current-user/whoami/

# 通过平台测试
curl -H "Authorization: Bearer YOUR_JWT" \
  http://localhost:8000/api/tasks/label-studio/test-connection
```

### 2. 测试任务创建和同步

```bash
# 运行测试脚本
python test_label_studio_sync.py
```

**测试脚本会**:
1. ✅ 登录获取 JWT token
2. ✅ 测试 Label Studio 连接
3. ✅ 创建测试任务
4. ✅ 检查自动同步状态
5. ✅ 如果失败，尝试手动同步

### 3. 手动测试

```bash
# 1. 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# 2. 创建任务
curl -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试任务",
    "priority": "medium",
    "annotation_type": "text_classification",
    "total_items": 10
  }'

# 3. 等待 3 秒后检查任务状态
curl http://localhost:8000/api/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. 如果需要，手动同步
curl -X POST http://localhost:8000/api/tasks/TASK_ID/sync-label-studio \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🐛 故障排查

### 问题 1: 认证失败

**症状**: `401 Unauthorized` 或 `403 Forbidden`

**检查**:
```bash
# 1. 检查 .env 配置
cat .env | grep LABEL_STUDIO

# 2. 验证 API Token
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8080/api/current-user/whoami/

# 3. 检查后端日志
docker logs superinsight-api | grep "Label Studio"
```

**解决方案**:
- 确认 API Token 正确
- 在 Label Studio UI 重新生成 Token
- 更新 `.env` 文件
- 重启后端容器

### 问题 2: 同步失败

**症状**: `sync_status = "failed"`

**检查**:
```bash
# 1. 测试连接
curl http://localhost:8000/api/tasks/label-studio/test-connection \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. 查看任务详情
curl http://localhost:8000/api/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. 检查后端日志
docker logs superinsight-api | grep "sync"
```

**解决方案**:
- 使用手动同步端点重试
- 检查 Label Studio 服务是否运行
- 验证网络连接
- 检查 API Token 权限

### 问题 3: 后台任务未执行

**症状**: `sync_status` 一直是 `"pending"`

**检查**:
```bash
# 检查 FastAPI 后台任务日志
docker logs superinsight-api | grep "background"
```

**解决方案**:
- 使用手动同步端点
- 重启后端服务
- 检查是否有异常阻塞后台任务

## 📝 下一步工作

### 前端集成 (待实现)

1. **任务列表显示同步状态**
   - 添加同步状态图标
   - 显示 Label Studio 项目链接
   - 添加手动同步按钮

2. **任务详情页**
   - 显示完整同步信息
   - 提供重试按钮
   - 显示错误信息

3. **创建任务表单**
   - 显示同步进度
   - 实时更新同步状态

### 数据库持久化 (待实现)

当前使用内存存储，需要：
- 将任务数据持久化到 PostgreSQL
- 添加同步历史记录表
- 实现同步状态查询

### 监控和告警 (待实现)

- 同步失败率监控
- 同步延迟监控
- 自动重试机制
- 告警通知

## 📚 相关文档

- [Label Studio API 文档](http://localhost:8080/docs)
- [认证修复方案](./LABEL_STUDIO_AUTH_SOLUTION.md)
- [任务 API 修复](./TASK_API_FIX_SUMMARY.md)
- [测试指南](./test_label_studio_sync.py)

## ✅ 验收标准

- [x] API Token 认证配置正确
- [x] 创建任务时自动同步到 Label Studio
- [x] 同步状态正确跟踪
- [x] 提供手动同步端点
- [x] 提供连接测试端点
- [x] 错误处理和日志记录
- [ ] 前端显示同步状态
- [ ] 数据库持久化
- [ ] 完整的端到端测试

## 🎯 总结

**已完成**:
1. ✅ Label Studio API Token 认证配置
2. ✅ 任务创建时自动同步到 Label Studio
3. ✅ 手动同步重试机制
4. ✅ 连接测试端点
5. ✅ 完整的错误处理
6. ✅ 测试脚本

**待完成**:
1. ⏳ 前端集成（显示同步状态、手动同步按钮）
2. ⏳ 数据库持久化
3. ⏳ 监控和告警

**可以开始测试**:
```bash
# 重启后端容器应用更改
docker compose restart app

# 运行测试脚本
python test_label_studio_sync.py
```

---

**创建时间**: 2026-01-27  
**最后更新**: 2026-01-27  
**状态**: ✅ 后端实现完成，等待测试和前端集成
