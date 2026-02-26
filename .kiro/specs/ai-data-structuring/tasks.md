# 任务列表：AI 驱动的结构化数据分析

## 任务 1: 后端数据模型与基础设施

- [x] 1.1 创建 `src/models/structuring.py`，定义 StructuringJob 和 StructuredRecord SQLAlchemy 模型
- [x] 1.2 创建数据库迁移脚本，生成 structuring_jobs 和 structured_records 表
- [x] 1.3 在 `src/extractors/tabular.py` 实现 TabularParser，支持 CSV（pandas.read_csv）和 Excel（pandas.read_excel）解析

## 任务 2: AI 分析核心模块

- [x] 2.1 创建 `src/ai/schema_inferrer.py`，实现 SchemaInferrer（instructor + OpenAI），支持从文本和表格数据推断 Schema
- [x] 2.2 创建 `src/ai/entity_extractor.py`，实现 EntityExtractor，按 Schema 从内容中提取结构化记录
- [x] 2.3 实现 LLM 调用重试机制（指数退避，max_retries=3）和错误处理

## 任务 3: Pipeline 编排与 API

- [x] 3.1 创建 `src/services/structuring_pipeline.py`，实现 Celery 任务编排（提取 → 推断 → 确认 → 提取实体 → 存储 → 创建任务）
- [x] 3.2 实现 Job 状态机（pending → extracting → inferring → confirming → extracting_entities → completed/failed）
- [x] 3.3 创建 `src/api/structuring.py`，实现 6 个 FastAPI 端点（创建 Job、查询状态、确认 Schema、执行提取、获取记录、创建标注任务）

## 任务 4: 前端页面与状态管理

- [x] 4.1 创建 `frontend/src/stores/structuringStore.ts`（Zustand），管理 Job、Schema、Records 状态
- [x] 4.2 创建 `frontend/src/services/api/structuringApi.ts`，封装 6 个 API 调用
- [x] 4.3 创建文件上传页面 `frontend/src/pages/DataStructuring/Upload.tsx`（拖拽上传、格式校验、进度显示）
- [x] 4.4 创建内容预览页面 `frontend/src/pages/DataStructuring/Preview.tsx`（文本预览 500 字符 / 表格预览 20 行）
- [x] 4.5 创建 Schema 编辑器 `frontend/src/pages/DataStructuring/SchemaEditor.tsx`（字段增删改、类型选择、置信度显示）
- [x] 4.6 创建结果展示页面 `frontend/src/pages/DataStructuring/Results.tsx`（记录表格、分页、创建标注任务按钮）
- [x] 4.7 添加 i18n 翻译 key（zh + en）

## 任务 5: 属性测试

- [x] 5.1 Property Test: 表格解析行数一致性（row_count == len(rows)，每行 key 数 == headers 数）
  - **Validates**: 需求 1.3, Property 3
  - **Library**: fast-check, **Min Iterations**: 100
- [x] 5.2 Property Test: 置信度范围约束（0.0 ≤ confidence ≤ 1.0）
  - **Validates**: 需求 2.2, Property 5
  - **Library**: fast-check, **Min Iterations**: 100
- [x] 5.3 Property Test: Job 状态机合法转换（只允许合法状态路径或转为 failed）
  - **Validates**: 需求 5.1, Property 4
  - **Library**: fast-check, **Min Iterations**: 100
- [x] 5.4 Property Test: Schema 字段名唯一性（推断结果中 field.name 互不相同）
  - **Validates**: 需求 2.2, Property 1
  - **Library**: fast-check, **Min Iterations**: 100
- [x] 5.5 Property Test: 文件类型路由正确性（csv/excel → TabularParser，pdf/docx/txt/html → FileExtractor）
  - **Validates**: 需求 1.2, 1.3, Property 7
  - **Library**: fast-check, **Min Iterations**: 100
