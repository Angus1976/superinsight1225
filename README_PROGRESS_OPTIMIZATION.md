# 结构化进度追踪优化 - 快速指南

## 🎯 优化目标

解决非结构化数据结构化过程卡住的问题，提供实时进度追踪。

## ✅ 已完成的优化

### 1. 降低超时时间
- LLM 超时从 300s → 60s (降低 80%)
- 总重试时间从 15min → 3min

### 2. 优化重试策略
- 不重试 JSON 解析错误
- 不重试格式验证错误
- 未知错误默认不重试（fail fast）

### 3. 添加进度追踪
- 6 个步骤的详细进度
- 实时百分比和消息
- 已用时间和预估剩余时间

## 🚀 快速开始

### 1. 运行数据库迁移

```bash
alembic upgrade head
```

### 2. 测试进度追踪

```bash
python scripts/test_progress_tracking.py
```

### 3. 监控任务进度

```bash
# 监控最新任务
python scripts/watch_structuring_progress.py --latest

# 监控指定任务
python scripts/watch_structuring_progress.py <job_id>
```

## 📊 效果展示

```
======================================================================
  结构化任务进度监控
======================================================================
总体进度: [████████████████░░░░░░░░░░░░░░░░░░░░] 65.5%
已用时间: 2m 15s
预计剩余: 1m 10s

当前步骤: 4/6
──────────────────────────────────────────────────────────────────────
✅ 步骤 1: 文件内容提取 (100.0%) - 12.5s
✅ 步骤 2: Schema 推断 (100.0%) - 45.2s
✅ 步骤 3: Schema 确认 (100.0%) - 0.1s
🔄 步骤 4: 实体提取 (50.0%) - 32.7s
⏳ 步骤 5: 记录存储 (0.0%)
⏳ 步骤 6: 创建标注任务 (0.0%)
```

## 📁 修改的文件

### 核心优化
- `src/ai/llm_schemas.py` - 降低超时时间
- `src/ai/retry.py` - 优化重试策略
- `src/services/progress_tracker.py` - 新增进度追踪器
- `src/services/structuring_pipeline.py` - 集成进度追踪
- `src/models/structuring.py` - 添加 progress_info 字段
- `src/api/structuring.py` - API 返回进度信息

### 工具和文档
- `scripts/watch_structuring_progress.py` - 命令行监控工具
- `scripts/test_progress_tracking.py` - 测试脚本
- `alembic/versions/011_add_progress_info.py` - 数据库迁移
- `文档/功能实现/结构化进度追踪优化.md` - 详细文档

## 🔍 API 使用

```bash
# 查询任务进度
curl -X GET "http://localhost:8000/api/structuring/jobs/{job_id}" \
  -H "Authorization: Bearer <token>"
```

响应包含 `progress_info` 字段：
```json
{
  "job_id": "abc-123",
  "status": "extracting_entities",
  "progress_info": {
    "overall_progress_percent": 65.5,
    "current_step": 4,
    "total_steps": 6,
    "elapsed_seconds": 135.0,
    "estimated_remaining_seconds": 70.0,
    "steps": [...]
  }
}
```

## 📝 详细文档

查看完整文档：`文档/功能实现/结构化进度追踪优化.md`

## 🎉 核心改进

从"黑盒等待"变为"透明可控"：
- ✅ 知道当前在做什么
- ✅ 知道已经完成多少
- ✅ 知道还需要多久
- ✅ 快速定位卡住的步骤
- ✅ 更好的用户体验
